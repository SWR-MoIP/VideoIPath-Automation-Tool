"""Pure port resolution and managed edge diffs. All server I/O stays in InspectGateway."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

from videoipath_automation_tool.apps.inspect.model.actions import InspectApiEdgeForm
from videoipath_automation_tool.apps.inspect.model.common import CONFLICT_PRIORITY_TO_INT
from videoipath_automation_tool.provisioning.errors import (
    ProvisioningTargetError,
    ProvisioningValidationError,
    TopologyNotReadyError,
    UndirectedPortError,
)
from videoipath_automation_tool.provisioning.models import (
    EdgePatch,
    EdgeState,
    FieldChange,
    PlannedOperation,
    PortBinding,
    PortSelector,
    ProvisioningEdge,
    TagDelta,
)

if TYPE_CHECKING:
    from videoipath_automation_tool.provisioning.inspect import ScopeData


class EdgeWork(BaseModel):
    model_config = ConfigDict(frozen=True)

    from_vertex: str
    to_vertex: str
    fields: EdgePatch
    baseline: InspectApiEdgeForm | None = None
    intents: dict[str, Any] = Field(default_factory=dict)
    expected: dict[str, Any] = Field(default_factory=dict)
    operation: PlannedOperation | None = None


class EdgeBatchWork(BaseModel):
    model_config = ConfigDict(frozen=True)

    states: list[EdgeState] = Field(default_factory=list)
    edges: dict[str, EdgeWork] = Field(default_factory=dict)

    @property
    def pending(self) -> bool:
        return any(state.status == "deferred" for state in self.states)

    @property
    def operations(self) -> list[PlannedOperation]:
        return [edge.operation for edge in self.edges.values() if edge.operation is not None]

    def touched_keys(self) -> set[tuple[str, str]]:
        keys = {("edge", edge_id) for edge_id in self.edges}
        for state in self.states:
            for binding in (state.local, state.peer):
                if binding is None:
                    continue
                keys.add(("device", binding.device_id))
                if binding.module_id is not None:
                    keys.add(("module", binding.module_id))
                keys.update(("vertex", vid) for vid in (binding.in_vertex_id, binding.out_vertex_id) if vid)
        return keys


def resolve_port(scope: ScopeData, candidates: list[PortSelector], *, key: str) -> PortBinding:
    """First matching candidate wins; ambiguity never falls through to another candidate."""
    if not scope.ports:
        raise TopologyNotReadyError(f"No ports discovered for '{scope.module_id or scope.device_id}'.")
    for candidate in candidates:
        ports = [
            port
            for port in scope.ports
            if (
                port.id == candidate.port_id
                if candidate.port_id is not None
                else port.factory_label == candidate.factory_label
            )
            and (
                candidate.kind is None or any(v.port_id == port.id and v.kind == candidate.kind for v in scope.vertices)
            )
        ]
        if len(ports) > 1:
            raise ProvisioningTargetError(
                f"Port '{key}' matches multiple ports in '{scope.module_id or scope.device_id}'."
            )
        if not ports:
            continue
        port = ports[0]
        vertices = [
            vertex
            for vertex in scope.vertices
            if vertex.port_id == port.id and (candidate.kind is None or vertex.kind == candidate.kind)
        ]
        directions: dict[str, str | None] = {}
        for direction in ("In", "Out"):
            matches = [v.id for v in vertices if v.vertex_type == direction]
            if len(matches) > 1:
                raise ProvisioningTargetError(f"Port '{port.id}' has multiple '{direction}' vertices.")
            directions[direction] = matches[0] if matches else None
        if not any(directions.values()):
            raise UndirectedPortError(f"Port '{port.id}' has no directed In/Out vertex.")
        return PortBinding(
            key=key,
            candidate=candidate.port_id or candidate.factory_label or "",
            port_id=port.id,
            device_id=scope.device_id,
            module_id=port.module_id,
            in_vertex_id=directions["In"],
            out_vertex_id=directions["Out"],
        )
    raise ProvisioningTargetError(f"Port '{key}' has no match in '{scope.module_id or scope.device_id}'.")


def resolve_edges(
    edges: list[ProvisioningEdge],
    scope: ScopeData,
    peers: dict[int, ScopeData | None],
    bindings: list[PortBinding],
) -> EdgeBatchWork:
    """Resolve concrete endpoints; an absent peer stays deferred until a new plan."""
    by_key = {binding.key: binding for binding in bindings}
    states: list[EdgeState] = []
    directed_edges: dict[str, EdgeWork] = {}
    for index, edge in enumerate(edges):
        if edge.peer.target.device_id == scope.device_id:
            raise ProvisioningTargetError("Edges must target another device; internal topology is driver-owned.")
        if isinstance(edge.local, str):
            if edge.local not in by_key:
                raise ProvisioningValidationError(f"Unknown local port mapping '{edge.local}'.")
            local = by_key[edge.local]
        else:
            local = resolve_port(scope, [edge.local], key=f"edges.{index}.local")
        peer_scope = peers[index]
        if peer_scope is None or not peer_scope.ports:
            states.append(
                EdgeState(
                    index=index,
                    edge=edge,
                    local=local,
                    status="deferred",
                    reason=(
                        "Peer device, module, ports, or directed vertices are not available in topology; "
                        "create a new plan when available."
                    ),
                )
            )
            continue
        peer = resolve_port(peer_scope, [edge.peer.port], key=f"edges.{index}.peer")
        pairs = _directed_pairs(local, peer, edge.direction)
        edge_ids: list[str] = []
        for from_vertex, to_vertex in pairs:
            edge_id = f"{from_vertex}::{to_vertex}"
            edge_ids.append(edge_id)
            fields = edge.fields
            if edge_id in directed_edges:
                managed = directed_edges[edge_id].fields.managed()
                for name, value in fields.managed().items():
                    if name in managed and managed[name] != value:
                        raise ProvisioningValidationError(f"Conflicting '{name}' requirements for edge '{edge_id}'.")
                    managed[name] = value
                fields = EdgePatch.model_validate(managed)
            directed_edges[edge_id] = EdgeWork(from_vertex=from_vertex, to_vertex=to_vertex, fields=fields)
        states.append(
            EdgeState(
                index=index,
                edge=edge,
                local=local,
                peer=peer,
                edge_ids=edge_ids,
                status="planned",
            )
        )
    return EdgeBatchWork(states=states, edges=directed_edges)


def compare_edges(work: EdgeBatchWork, current: dict[str, InspectApiEdgeForm]) -> EdgeBatchWork:
    """Compare only managed fields while keeping full baselines for conflict checks."""
    edges: dict[str, EdgeWork] = {}
    for edge_id, edge in work.edges.items():
        baseline = current.get(edge_id)
        form = baseline or InspectApiEdgeForm(fromId=edge.from_vertex, toId=edge.to_vertex)
        expected: dict[str, Any] = {"fromId": edge.from_vertex, "toId": edge.to_vertex}
        intents: dict[str, Any] = {}
        changes: list[FieldChange] = []
        for name, value in edge.fields.managed().items():
            path = _EDGE_PATHS.get(name, name)
            before = edge_value(form, path)
            if name == "tags":
                if isinstance(value, TagDelta):
                    value = [tag for tag in form.tags if tag not in value.remove] + [
                        tag for tag in dict.fromkeys(value.add) if tag not in form.tags
                    ]
                else:
                    value = list(dict.fromkeys(value))
            elif name == "conflict_priority" and isinstance(value, str):
                value = CONFLICT_PRIORITY_TO_INT[value]
            expected[path] = value
            if not same_edge_value(path, before, value):
                intents[path] = value
                changes.append(FieldChange(field=name, before=before, after=value, source="instance"))
        operation = None
        if baseline is None or intents:
            if baseline is None:
                changes = [
                    FieldChange(field="from_vertex", after=edge.from_vertex, source="instance"),
                    FieldChange(field="to_vertex", after=edge.to_vertex, source="instance"),
                    *changes,
                ]
            operation = PlannedOperation(
                action="create" if baseline is None else "update",
                entity_kind="edge",
                entity_id=edge_id,
                changes=changes,
            )
        edges[edge_id] = edge.model_copy(
            update={
                "baseline": baseline.model_copy(deep=True) if baseline is not None else None,
                "intents": intents,
                "expected": expected,
                "operation": operation,
            }
        )
    states = [
        state
        if state.status == "deferred"
        else state.model_copy(
            update={
                "status": "planned" if any(edges[eid].operation is not None for eid in state.edge_ids) else "no_change",
            }
        )
        for state in work.states
    ]
    return EdgeBatchWork(states=states, edges=edges)


def edge_value(form: InspectApiEdgeForm, path: str) -> Any:
    value: Any = form
    for part in path.split("."):
        value = value.get(part) if isinstance(value, dict) else getattr(value, part, None)
    if path == "conflictPri":
        if isinstance(value, str) and value in CONFLICT_PRIORITY_TO_INT:
            return CONFLICT_PRIORITY_TO_INT[value]
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return value


def same_edge_value(path: str, before: Any, after: Any) -> bool:
    return set(before or []) == set(after or []) if path == "tags" else before == after


def _directed_pairs(local: PortBinding, peer: PortBinding, direction: str) -> list[tuple[str, str]]:
    outgoing = (local.out_vertex_id, peer.in_vertex_id)
    incoming = (peer.out_vertex_id, local.in_vertex_id)
    required = (
        [outgoing, incoming]
        if direction in ("auto", "bidirectional")
        else [outgoing if direction == "outgoing" else incoming]
    )
    pairs = [(source, target) for source, target in required if source is not None and target is not None]
    if not pairs or (direction != "auto" and len(pairs) != len(required)):
        raise ProvisioningTargetError(
            f"Ports '{local.port_id}' and '{peer.port_id}' cannot satisfy direction '{direction}'."
        )
    return pairs


_EDGE_PATHS = {
    "label": "descriptor.label",
    "description": "descriptor.desc",
    "redundancy_mode": "redundancyMode",
    "conflict_priority": "conflictPri",
    "include_formats": "includeFormats",
    "exclude_formats": "excludeFormats",
    "bandwidth_weight_factor": "weightFactors.bandwidth.weight",
    "weight_per_service": "weightFactors.service.weight",
}
