"""Inspect integration: exact device/module scoping, fresh detached reads, interface bindings,
topology work computation, and the existing Inspect write paths.

Planning never touches the live snapshot's domain objects: scope data is built from fresh collector
and lookup reads, so pending (uncommitted) user edits on the shared snapshot are neither read as
server truth nor flushed. Writes stage exactly the planned id/field intents in one
``InspectTransaction`` (with its conflict check); module tags use the separate ``assignTag`` /
``unassignTag`` actions and are tracked as their own phase. Module tag baselines come from the
module's *local* assignments — inherited/effective tags are never used as a removal baseline.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from videoipath_automation_tool.apps.inspect.model.collector import (
    InspectApiDoubleVertexInfo,
    InspectApiNodeStatusItem,
    InspectApiSingleVertexInfo,
)
from videoipath_automation_tool.apps.inspect.model.tags import module_resource_id
from videoipath_automation_tool.blueprints.errors import (
    BlueprintCapabilityError,
    BlueprintError,
    BlueprintTargetError,
    BlueprintValidationError,
    ProcessorInputError,
    TopologyNotReadyError,
    ValidationIssue,
)
from videoipath_automation_tool.blueprints.models import (
    Coordinates,
    Diagnostic,
    EndpointIdentity,
    FieldChange,
    InterfaceBinding,
    ModuleTarget,
    PlannedOperation,
    ProcessorResult,
    TagDelta,
    TopologyTarget,
)
from videoipath_automation_tool.blueprints.naming import NameContext, NamingScheme, render_name
from videoipath_automation_tool.blueprints.processors import (
    DeviceRecord,
    DriverContext,
    ModuleRecord,
    PortRecord,
    ProcessingContext,
    SourceFacts,
    VertexRecord,
)
from videoipath_automation_tool.blueprints.resolution import ResolvedTopology


class ScopeData(BaseModel):
    """Fresh, detached read of one device/module scope."""

    model_config = ConfigDict(frozen=True)

    device_id: str
    module_id: str | None = None
    device: DeviceRecord
    modules: tuple[ModuleRecord, ...] = ()
    ports: tuple[PortRecord, ...] = ()
    vertices: tuple[VertexRecord, ...] = ()
    external_endpoint_labels: dict[str, str] = Field(default_factory=dict)
    """Labels of endpoint vertices of the same device outside the scope (collision checks)."""
    without_form: frozenset[str] = frozenset()

    @property
    def fingerprint(self) -> str:
        document = self.model_dump(
            mode="json",
            include={
                "device_id",
                "module_id",
                "device",
                "modules",
                "ports",
                "vertices",
                "external_endpoint_labels",
            },
        )
        return hashlib.sha256(json.dumps(document, sort_keys=True).encode()).hexdigest()

    def vertex(self, vertex_id: str) -> VertexRecord | None:
        return next((vertex for vertex in self.vertices if vertex.id == vertex_id), None)

    def module(self) -> ModuleRecord | None:
        return next((module for module in self.modules if module.id == self.module_id), None)


class TopologyWork(BaseModel):
    """Exact topology edits for one scope (internal; unredacted values are never secrets here)."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    device_id: str
    module_id: str | None = None
    fingerprint: str
    device_intents: dict[str, Any] = Field(default_factory=dict)
    vertex_intents: dict[str, dict[str, Any]] = Field(default_factory=dict)
    module_tag_baseline: tuple[str, ...] | None = None
    tags_to_assign: list[str] = Field(default_factory=list)
    tags_to_unassign: list[str] = Field(default_factory=list)
    expected_device: dict[str, Any] = Field(default_factory=dict)
    expected_vertices: dict[str, dict[str, Any]] = Field(default_factory=dict)
    expected_module_tags: list[str] | None = None
    bindings: list[InterfaceBinding] = Field(default_factory=list)
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    topology_operations: list[PlannedOperation] = Field(default_factory=list)
    module_operations: list[PlannedOperation] = Field(default_factory=list)

    @property
    def has_topology_writes(self) -> bool:
        return bool(self.device_intents or self.vertex_intents)

    @property
    def has_module_writes(self) -> bool:
        return bool(self.tags_to_assign or self.tags_to_unassign)

    def touched_keys(self) -> set[tuple[str, str]]:
        keys = {("vertex", vertex_id) for vertex_id in self.vertex_intents}
        if self.device_intents:
            keys.add(("device", self.device_id))
        if self.has_module_writes and self.module_id is not None:
            keys.add(("module", self.module_id))
        return keys


class InspectGateway:
    """The only place that talks to ``app.inspect`` (public methods plus one internal API handle)."""

    def __init__(self, inspect_app: Any) -> None:
        self._app = inspect_app

    @property
    def _api(self) -> Any:
        return self._app._inspect_api

    # --- Reads ---

    def in_topology(self, device_id: str) -> bool:
        if self._detail(device_id) is not None:
            return True
        return device_id.startswith("virtual.") and self._device_form(device_id, required=False) is not None

    def sync_info(self, device_id: str) -> Any | None:
        """Pending sync for ``device_id``, or ``None`` when the server reports no sync record.

        A failed lookup is an error. Treating it as "nothing pending" would let apply commit topology
        edits while a synchronization that updates or removes elements is still outstanding.
        """
        try:
            return self._app.get_sync_info([device_id]).get(device_id)
        except BlueprintError:
            raise
        except Exception as exc:
            raise BlueprintError(
                f"Could not read synchronization status for '{device_id}': {type(exc).__name__}: {exc}"
            ) from exc

    def read_scope(self, target: TopologyTarget) -> ScopeData:
        device_id = target.device_id
        module_id = target.module_id if isinstance(target, ModuleTarget) else None
        node = self._detail(device_id)
        form = self._device_form(device_id, required=node is not None)
        if node is None and form is None:
            raise BlueprintTargetError(f"Inspect device '{device_id}' is not in the topology.")

        modules = _modules_of(node)
        if module_id is not None and module_id not in modules:
            known = ", ".join(sorted(modules)[:10]) or "none"
            raise BlueprintTargetError(
                f"Module '{module_id}' does not belong to Inspect device '{device_id}' (modules: {known})."
            )

        ports: list[tuple[PortRecord, list[tuple[str, InspectApiSingleVertexInfo]]]] = []
        for mod_id, module in modules.items():
            for key, port in _items(module.ports):
                port_id = port.pid or port.id or key
                sides = _vertex_sides(port.parsed_vertex_info)
                record = PortRecord(
                    id=port_id,
                    module_id=mod_id,
                    factory_label=port.label,
                    label=port.effective_label,
                    vertex_ids=tuple(vid for vid, _ in sides),
                )
                ports.append((record, sides))

        in_scope = [(p, sides) for p, sides in ports if module_id is None or p.module_id == module_id]
        scope_ids = [vid for _, sides in in_scope for vid, _ in sides]
        external_ids = [
            vid
            for p, sides in ports
            if module_id is not None and p.module_id != module_id
            for vid, side in sides
            if side.fields is not None and side.fields.isEndpoint
        ]
        forms = self._vertex_forms(scope_ids + external_ids)

        vertices = sorted(
            (_vertex_record(vid, side, port, forms.get(vid)) for port, sides in in_scope for vid, side in sides),
            key=lambda record: record.id,
        )
        external = {vid: forms[vid].fields.label for vid in external_ids if vid in forms and forms[vid].fields.label}
        module_records = tuple(
            _module_record(mod_id, module) for mod_id, module in sorted(modules.items()) if module_id in (None, mod_id)
        )
        return ScopeData(
            device_id=device_id,
            module_id=module_id,
            device=_device_record(device_id, node, form),
            modules=module_records,
            ports=tuple(sorted((p for p, _ in in_scope), key=lambda record: record.id)),
            vertices=tuple(vertices),
            external_endpoint_labels=external,
            without_form=frozenset(vid for vid in scope_ids if vid not in forms),
        )

    def module_local_tags(self, device_id: str, module_id: str) -> tuple[str, ...] | None:
        node = self._detail(device_id)
        module = _modules_of(node).get(module_id)
        if module is None:
            raise BlueprintTargetError(f"Module '{module_id}' of '{device_id}' is no longer in the topology.")
        return _local_tags(module)

    def staged_edit_keys(self) -> set[tuple[str, str]]:
        """Entities with pending (uncommitted) domain-object edits on the shared app snapshot."""
        snapshot = getattr(self._app, "_snapshot", None)
        if snapshot is None:
            return set()
        return {(kind, entity_id) for kind, entity_id, intents in snapshot.iter_staged_edits() if intents}

    # --- Writes ---

    def add_to_topology(self, device_id: str) -> None:
        if not self._app.add_devices_to_topology([device_id], sync=False):
            raise TopologyNotReadyError(f"addDevices reported failure for '{device_id}' (not discovered yet?).")

    def sync(self, device_id: str, *, add_only: bool) -> None:
        if not self._app.sync_devices([device_id], add_only=add_only):
            raise BlueprintError(f"syncDevices failed for '{device_id}'; see the server log / Inspect sync dialog.")

    def commit(self, work: TopologyWork) -> Any:
        with self._app.transaction() as tx:
            if work.device_intents:
                tx.update_device(work.device_id, intents=dict(work.device_intents))
            for vertex_id, intents in sorted(work.vertex_intents.items()):
                tx.update_vertex(vertex_id, intents=dict(intents))
            return tx.commit()

    def assign_tag(self, tag_id: str, module_id: str) -> None:
        _check_action(self._api.assign_tag(tag_id, [module_resource_id(module_id)]), "assignTag", tag_id)

    def unassign_tag(self, tag_id: str, module_id: str) -> None:
        _check_action(self._api.unassign_tag(tag_id, [module_resource_id(module_id)]), "unassignTag", tag_id)

    def refresh_device(self, device_id: str) -> None:
        snapshot = getattr(self._app, "_snapshot", None)
        if snapshot is not None:
            snapshot.apply_post_commit(device_ids=[device_id])

    # --- Internal ---

    def _detail(self, device_id: str) -> InspectApiNodeStatusItem | None:
        node = self._api.get_device_detail(device_id)
        if node is None and device_id.startswith("virtual."):
            node = self._api.get_device_detail(device_id.replace(".", "-"))
        return node

    def _device_form(self, device_id: str, *, required: bool) -> Any | None:
        try:
            return self._api.lookup_inspect_device(device_id).data.fields
        except Exception as exc:
            if not required:
                return None
            raise BlueprintError(
                f"Could not read the Inspect edit form of device '{device_id}': {type(exc).__name__}: {exc}"
            ) from exc

    def _vertex_forms(self, vertex_ids: list[str]) -> dict[str, Any]:
        if not vertex_ids:
            return {}
        return dict(self._api.lookup_vertices(vertex_ids).data)


def resolve_interfaces(
    mapping: dict[str, list[str]] | None, scope: ScopeData, module_position: str | None
) -> list[InterfaceBinding]:
    """Resolve caller interface keys to exact ports (with IP vertices) in scope, in fallback order."""
    if not mapping:
        return []
    by_id = {vertex.id: vertex for vertex in scope.vertices}
    bindings: list[InterfaceBinding] = []
    for key, candidates in mapping.items():
        attempted: list[str] = []
        for raw in candidates:
            label = _substitute_position(raw, module_position, key)
            attempted.append(label)
            ports = [
                port
                for port in scope.ports
                if port.factory_label == label and any(by_id[v].kind == "ip" for v in port.vertex_ids if v in by_id)
            ]
            if len(ports) > 1:
                raise BlueprintTargetError(
                    f"Interface '{key}': factory label '{label}' matches {len(ports)} ports "
                    f"({', '.join(p.id for p in ports)}) in {_scope_label(scope)}."
                )
            if ports:
                port = ports[0]
                vertices = [by_id[v] for v in port.vertex_ids if v in by_id]
                bindings.append(
                    InterfaceBinding(
                        key=key,
                        candidate=label,
                        port_id=port.id,
                        in_vertex_id=next((v.id for v in vertices if v.vertex_type == "In"), None),
                        out_vertex_id=next((v.id for v in vertices if v.vertex_type == "Out"), None),
                    )
                )
                break
        else:
            # No ports at all means discovery has not produced them yet; a miss among ports is final.
            error = TopologyNotReadyError if not scope.ports else BlueprintTargetError
            raise error(
                f"Interface '{key}': no IP port in {_scope_label(scope)} matches {', '.join(map(repr, attempted))}."
            )
    return bindings


def build_context(
    scope: ScopeData,
    source: SourceFacts,
    bindings: list[InterfaceBinding],
    owner: DriverContext | None,
    inventory: DriverContext | None,
) -> ProcessingContext:
    return ProcessingContext(
        source=source,
        scope="module" if scope.module_id else "device",
        device_id=scope.device_id,
        module_id=scope.module_id,
        device=scope.device,
        modules=scope.modules,
        ports=scope.ports,
        vertices=scope.vertices,
        interfaces=tuple(bindings),
        owner=owner,
        inventory=inventory
        if inventory is None or owner is None or inventory.inventory_id != owner.inventory_id
        else None,
        capabilities=frozenset(),
    )


def compute_topology_work(
    *,
    scope: ScopeData,
    resolved: ResolvedTopology,
    naming: NamingScheme,
    source: SourceFacts,
    owner: DriverContext | None,
    inventory: DriverContext | None,
    allow_label_collisions: bool,
) -> TopologyWork:
    """Run the processor on the detached scope and turn proposals into exact, compared edits."""
    config = resolved.config
    bindings = resolve_interfaces(config.ip_vertex_mapping, scope, source.module_position)
    context = build_context(scope, source, bindings, owner, inventory)
    result = _run_processor(resolved, context)
    is_module = scope.module_id is not None
    processor_source = f"processor:{resolved.processor_id}"

    if is_module and result.device is not None and result.device.managed():
        raise BlueprintTargetError(
            f"Processor '{resolved.processor_id}' proposed device-wide changes for a module target."
        )
    if not is_module and result.module is not None and result.module.managed():
        raise BlueprintTargetError(f"Processor '{resolved.processor_id}' proposed module changes for a device target.")
    if is_module and config.device is not None and config.device.managed():
        raise BlueprintTargetError(
            "'topology.device' settings cannot be applied to a module target; use a device target."
        )
    if not is_module and config.module is not None and config.module.managed():
        raise BlueprintTargetError("'topology.module' settings require a module target.")

    # Vertex proposals: processor < naming < explicit overrides.
    vertex_desired: dict[str, dict[str, tuple[Any, str]]] = defaultdict(dict)
    endpoints: dict[str, EndpointIdentity] = {}
    for edit in result.vertices:
        if scope.vertex(edit.vertex_id) is None:
            raise BlueprintTargetError(
                f"Processor '{resolved.processor_id}' proposed vertex '{edit.vertex_id}' outside {_scope_label(scope)}."
            )
        for field, value in edit.fields.managed().items():
            existing = vertex_desired[edit.vertex_id].get(field)
            if existing is not None and existing[0] != value:
                raise ProcessorInputError(
                    f"Processor '{resolved.processor_id}' proposed conflicting '{field}' values for '{edit.vertex_id}'."
                )
            vertex_desired[edit.vertex_id][field] = (value, processor_source)
        if edit.endpoint is not None:
            if edit.vertex_id in endpoints and endpoints[edit.vertex_id] != edit.endpoint:
                raise ProcessorInputError(
                    f"Processor '{resolved.processor_id}' proposed conflicting endpoint identities for '{edit.vertex_id}'."
                )
            endpoints[edit.vertex_id] = edit.endpoint

    for vertex_id, endpoint in endpoints.items():
        record = scope.vertex(vertex_id)
        assert record is not None
        facts = name_context(source, endpoint=endpoint, vertex=record)
        for entry, field in (("endpoint_label", "label"), ("endpoint_description", "description")):
            expression = getattr(naming, entry)
            if expression is not None:
                vertex_desired[vertex_id][field] = (render_name(entry, expression, facts), "naming")

    for index, override in enumerate(config.vertices or []):
        vertex_id = _select_override(override, scope, source.module_position, index)
        override_source = resolved.provenance.get("vertices", "blueprint")
        for field, value in override.fields.managed().items():
            vertex_desired[vertex_id][field] = (value, f"override:{override_source}")

    for vertex_id, fields in vertex_desired.items():
        record = scope.vertex(vertex_id)
        assert record is not None
        if vertex_id in scope.without_form:
            raise BlueprintTargetError(f"Vertex '{vertex_id}' has no edit form on the server; it cannot be configured.")
        for field, kind in _KIND_SPECIFIC_FIELDS.items():
            if field in fields and record.kind != kind:
                raise BlueprintCapabilityError(
                    f"'{field}' is only supported on {kind} vertices ('{vertex_id}' is '{record.kind}')."
                )

    # Device and module proposals: processor defaults < explicit blueprint < naming (device label).
    device_desired: dict[str, tuple[Any, str]] = {}
    module_tags: tuple[Any, str] | None = None
    if not is_module:
        if result.device is not None:
            device_desired.update({k: (v, processor_source) for k, v in result.device.managed().items()})
        if config.device is not None:
            device_desired.update(
                {
                    k: (v, resolved.provenance.get(f"device.{k}", "blueprint"))
                    for k, v in config.device.managed().items()
                }
            )
        facts = name_context(source)
        for entry, field in (("device_label", "label"), ("device_description", "description")):
            expression = getattr(naming, entry)
            if expression is not None:
                device_desired[field] = (render_name(entry, expression, facts), "naming")
    else:
        if result.module is not None and result.module.tags is not None:
            module_tags = (result.module.tags, processor_source)
        if config.module is not None and config.module.tags is not None:
            module_tags = (config.module.tags, resolved.provenance.get("module.tags", "blueprint"))

    work = _compare(scope, vertex_desired, endpoints, device_desired, module_tags)
    _check_label_collisions(scope, work, allow=allow_label_collisions)
    return work.model_copy(
        update={"bindings": bindings, "diagnostics": list(result.diagnostics), "fingerprint": scope.fingerprint}
    )


def verify_topology(scope: ScopeData, work: TopologyWork) -> list[str]:
    """Managed fields whose fresh read-back differs from the desired value."""
    mismatches: list[str] = []
    for field, value in work.expected_device.items():
        if not _same(field, _device_value(scope.device, field), value):
            mismatches.append(f"device.{field}")
    for vertex_id, fields in work.expected_vertices.items():
        record = scope.vertex(vertex_id)
        for field, value in fields.items():
            if record is None or not _same(field, getattr(record, field), value):
                mismatches.append(f"{vertex_id}.{field}")
    if work.expected_module_tags is not None:
        module = scope.module()
        if module is None or module.local_tags is None or set(module.local_tags) != set(work.expected_module_tags):
            mismatches.append(f"{work.module_id}.tags")
    return mismatches


def name_context(
    source: SourceFacts, *, endpoint: EndpointIdentity | None = None, vertex: VertexRecord | None = None
) -> NameContext:
    """Naming facts for a source entity (and optionally one endpoint vertex)."""
    return NameContext(
        device={"key": source.key, "label": source.label, "description": source.description},
        module={"position": source.module_position},
        endpoint=endpoint.model_dump() if endpoint is not None else {},
        vertex={"factory_label": vertex.factory_label, "id": vertex.id} if vertex is not None else {},
        attributes=source.attributes,
    )


# --- Internal ---

_DEVICE_WIRE = {
    "label": "descriptor.label",
    "description": "descriptor.desc",
    "icon_type": "iconType",
    "icon_size": "iconSize",
    "sdp_strategy": "sdpStrategy",
    "site_id": "siteId",
    "coordinates": "coordinates",
    "tags": "localAssignedTags",
}
_VERTEX_WIRE = {
    "use_as_endpoint": "useAsEndpoint",
    "label": "label",
    "description": "desc",
    "active": "active",
    "sips_mode": "sipsMode",
    "tags": "localAssignedTags",
    "sdp_support": "typeFields.specific.sdpSupport",
    "main_destination_port": "typeFields.generic.mainDstInfo.port",
    "spare_destination_port": "typeFields.generic.spareDstInfo.port",
    "supports_static_igmp": "typeFields.supportsStaticIgmpCfg",
}
_KIND_SPECIFIC_FIELDS = {
    "sdp_support": "codec",
    "main_destination_port": "codec",
    "spare_destination_port": "codec",
    "supports_static_igmp": "ip",
}
_POSITION_TOKEN = re.compile(r"\{([^{}]*)\}")


def _run_processor(resolved: ResolvedTopology, context: ProcessingContext) -> ProcessorResult:
    if resolved.processor_cls is None:
        return ProcessorResult()
    try:
        raw = resolved.processor_cls().process(context, resolved.params)
    except BlueprintError:
        raise
    except Exception as exc:
        raise ProcessorInputError(f"Processor '{resolved.processor_id}' failed: {type(exc).__name__}: {exc}") from exc
    if not isinstance(raw, ProcessorResult):
        raise ProcessorInputError(f"Processor '{resolved.processor_id}' must return a ProcessorResult.")
    try:  # re-validate even if a plugin bypassed normal construction
        return ProcessorResult.model_validate(raw.model_dump(mode="python", exclude_unset=True, warnings=False))
    except Exception as exc:  # noqa: BLE001
        raise ProcessorInputError(f"Processor '{resolved.processor_id}' returned an invalid result: {exc}") from None


def _compare(
    scope: ScopeData,
    vertex_desired: dict[str, dict[str, tuple[Any, str]]],
    endpoints: dict[str, EndpointIdentity],
    device_desired: dict[str, tuple[Any, str]],
    module_tags: tuple[Any, str] | None,
) -> TopologyWork:
    device_intents: dict[str, Any] = {}
    expected_device: dict[str, Any] = {}
    device_changes: list[FieldChange] = []
    for field, (value, source) in sorted(device_desired.items()):
        current = _device_value(scope.device, field)
        desired = _resolve_tags(value, current, f"device '{scope.device_id}'") if field == "tags" else _plain(value)
        expected_device[field] = desired
        if not _same(field, current, desired):
            device_intents[_DEVICE_WIRE[field]] = _wire(field, desired)
            device_changes.append(FieldChange(field=field, before=_json(current), after=_json(desired), source=source))

    vertex_intents: dict[str, dict[str, Any]] = {}
    expected_vertices: dict[str, dict[str, Any]] = {}
    operations: list[PlannedOperation] = []
    if device_changes:
        operations.append(
            PlannedOperation(action="update", entity_kind="device", entity_id=scope.device_id, changes=device_changes)
        )
    for vertex_id in sorted(vertex_desired):
        record = scope.vertex(vertex_id)
        assert record is not None
        changes: list[FieldChange] = []
        for field, (value, source) in sorted(vertex_desired[vertex_id].items()):
            current = getattr(record, field)
            desired = _resolve_tags(value, current, f"vertex '{vertex_id}'") if field == "tags" else value
            expected_vertices.setdefault(vertex_id, {})[field] = desired
            if not _same(field, current, desired):
                vertex_intents.setdefault(vertex_id, {})[_VERTEX_WIRE[field]] = _wire(field, desired)
                changes.append(FieldChange(field=field, before=_json(current), after=_json(desired), source=source))
        if changes:
            operations.append(
                PlannedOperation(
                    action="update",
                    entity_kind="vertex",
                    entity_id=vertex_id,
                    changes=changes,
                    endpoint=endpoints.get(vertex_id),
                )
            )

    module_operations: list[PlannedOperation] = []
    baseline: tuple[str, ...] | None = None
    assign: list[str] = []
    unassign: list[str] = []
    expected_tags: list[str] | None = None
    if module_tags is not None and scope.module_id is not None:
        spec, source = module_tags
        module = scope.module()
        baseline = module.local_tags if module is not None else None
        if baseline is None:
            if not isinstance(spec, TagDelta) or spec.remove:
                raise BlueprintCapabilityError(
                    f"Local tags of module '{scope.module_id}' cannot be distinguished from inherited tags on this "
                    "server; only additive tag changes ({add: [...]}) are supported for it."
                )
            assign = list(dict.fromkeys(spec.add))
        else:
            desired = _resolve_tags(spec, baseline, f"module '{scope.module_id}'")
            expected_tags = desired
            assign = [tag for tag in desired if tag not in baseline]
            unassign = [tag for tag in baseline if tag not in desired]
        for action, tags in (("assign_tag", assign), ("unassign_tag", unassign)):
            for tag in tags:
                module_operations.append(
                    PlannedOperation(
                        action=action,  # type: ignore[arg-type]
                        entity_kind="module",
                        entity_id=scope.module_id,
                        changes=[FieldChange(field="tags", after=tag, source=source)],
                    )
                )

    return TopologyWork(
        device_id=scope.device_id,
        module_id=scope.module_id,
        fingerprint=scope.fingerprint,
        device_intents=device_intents,
        vertex_intents=vertex_intents,
        module_tag_baseline=baseline,
        tags_to_assign=assign,
        tags_to_unassign=unassign,
        expected_device=expected_device,
        expected_vertices=expected_vertices,
        expected_module_tags=expected_tags,
        topology_operations=operations,
        module_operations=module_operations,
    )


def _check_label_collisions(scope: ScopeData, work: TopologyWork, *, allow: bool) -> None:
    changed = {vid for vid, intents in work.vertex_intents.items() if "label" in intents or "useAsEndpoint" in intents}
    if allow or not changed:
        return
    labels: dict[str, list[str]] = defaultdict(list)
    for record in scope.vertices:
        expected = work.expected_vertices.get(record.id, {})
        if expected.get("use_as_endpoint", record.use_as_endpoint):
            label = expected.get("label", record.label)
            if label:
                labels[label].append(record.id)
    for vertex_id, label in scope.external_endpoint_labels.items():
        labels[label].append(vertex_id)
    collisions = {label: ids for label, ids in labels.items() if len(ids) > 1 and changed.intersection(ids)}
    if collisions:
        detail = "; ".join(f"'{label}' on {', '.join(sorted(ids))}" for label, ids in sorted(collisions.items()))
        raise BlueprintValidationError(
            ValidationIssue(
                path="naming.endpoint_label",
                message=f"Endpoint label collision in device '{scope.device_id}': {detail}. Adjust the naming rule "
                "or allow duplicates with ApplyOptions(naming_collisions='allow').",
                code="naming.collision",
            )
        )


def _select_override(override: Any, scope: ScopeData, module_position: str | None, index: int) -> str:
    if override.vertex_id is not None:
        if scope.vertex(override.vertex_id) is None:
            raise BlueprintTargetError(
                f"Vertex override #{index}: '{override.vertex_id}' is not in {_scope_label(scope)}."
            )
        return override.vertex_id
    label = _substitute_position(override.factory_label, module_position, f"vertices[{index}]")
    matches = [
        vertex
        for vertex in scope.vertices
        if vertex.factory_label == label
        and (override.kind is None or vertex.kind == override.kind)
        and (override.direction is None or vertex.vertex_type == override.direction)
    ]
    if len(matches) != 1:
        found = ", ".join(v.id for v in matches) or "none"
        raise BlueprintTargetError(
            f"Vertex override #{index}: factory label '{label}' must match exactly one vertex in "
            f"{_scope_label(scope)}; matched {found}. Add 'kind'/'direction' or use 'vertex_id'."
        )
    return matches[0].id


def _substitute_position(template: str, module_position: str | None, owner: str) -> str:
    def replace(match: re.Match[str]) -> str:
        if match.group(1) != "module.position":
            raise BlueprintValidationError(
                ValidationIssue(
                    path=owner,
                    message=f"Unsupported placeholder '{{{match.group(1)}}}' (only '{{module.position}}').",
                    code="mapping.placeholder",
                )
            )
        if module_position is None:
            raise BlueprintValidationError(
                ValidationIssue(
                    path=owner,
                    message="'{module.position}' requires BlueprintDevice.module_position.",
                    code="mapping.missing",
                )
            )
        return module_position

    escaped = template.replace("{{", "\x00").replace("}}", "\x01")
    return _POSITION_TOKEN.sub(replace, escaped).replace("\x00", "{").replace("\x01", "}")


def _resolve_tags(spec: Any, current: Any, owner: str) -> list[str]:
    current_list = list(current or [])
    if isinstance(spec, TagDelta):
        kept = [tag for tag in current_list if tag not in spec.remove]
        return kept + [tag for tag in dict.fromkeys(spec.add) if tag not in kept]
    if isinstance(spec, (list, tuple)):
        return list(dict.fromkeys(spec))
    raise BlueprintValidationError(f"Invalid tag specification for {owner}.")


def _same(field: str, current: Any, desired: Any) -> bool:
    if field == "tags":
        return set(current or ()) == set(desired or ())
    return _plain(current) == _plain(desired)


def _device_value(device: DeviceRecord, field: str) -> Any:
    return getattr(device, field)


def _wire(field: str, value: Any) -> Any:
    if field == "coordinates":
        return {"x": value[0], "y": value[1]}
    if field == "tags":
        return list(value)
    return value


def _plain(value: Any) -> Any:
    if isinstance(value, Coordinates):
        return (float(value.x), float(value.y))
    if isinstance(value, tuple):
        return tuple(_plain(item) for item in value)
    return value


def _json(value: Any) -> Any:
    value = _plain(value)
    return list(value) if isinstance(value, tuple) else value


def _scope_label(scope: ScopeData) -> str:
    return (
        f"module '{scope.module_id}' of device '{scope.device_id}'"
        if scope.module_id
        else f"device '{scope.device_id}'"
    )


def _items(collection: Any) -> list[tuple[str | None, Any]]:
    if not collection:
        return []
    if isinstance(collection, dict):
        return list(collection.items())
    return [(None, item) for item in collection]


def _modules_of(node: InspectApiNodeStatusItem | None) -> dict[str, Any]:
    if node is None:
        return {}
    modules: dict[str, Any] = {}
    for key, module in _items(node.modules):
        module_id = module.pid or module.id or key
        if module_id:
            modules[module_id] = module
    return modules


def _vertex_sides(info: Any) -> list[tuple[str, InspectApiSingleVertexInfo]]:
    if isinstance(info, InspectApiSingleVertexInfo):
        return [(info.id, info)] if info.id else []
    if isinstance(info, InspectApiDoubleVertexInfo):
        return [(side.id, side) for side in (info.out, info.in_) if side is not None and side.id]
    return []


def _local_tags(module: Any) -> tuple[str, ...] | None:
    info = module.tagsInfo
    assigned = info.get("assigned") if isinstance(info, dict) else None
    local = assigned.get("local") if isinstance(assigned, dict) else None
    return tuple(local.keys()) if isinstance(local, dict) else None


def _module_record(module_id: str, module: Any) -> ModuleRecord:
    return ModuleRecord(id=module_id, label=module.effective_label, local_tags=_local_tags(module))


def _device_record(device_id: str, node: InspectApiNodeStatusItem | None, form: Any) -> DeviceRecord:
    factory = node.fDescriptor.label if node is not None and node.fDescriptor is not None else None
    if form is None:
        return DeviceRecord(id=device_id, factory_label=factory)
    coordinates = form.coordinates
    return DeviceRecord(
        id=device_id,
        label=form.descriptor.label,
        description=form.descriptor.desc,
        factory_label=factory,
        icon_type=form.iconType,
        icon_size=form.iconSize,
        sdp_strategy=form.sdpStrategy,
        site_id=form.siteId,
        coordinates=(float(coordinates["x"]), float(coordinates["y"]))
        if isinstance(coordinates, dict) and "x" in coordinates and "y" in coordinates
        else None,
        tags=tuple(form.localAssignedTags),
    )


def _vertex_record(vertex_id: str, side: InspectApiSingleVertexInfo, port: PortRecord, lookup: Any) -> VertexRecord:
    base = {
        "id": vertex_id,
        "port_id": port.id,
        "module_id": port.module_id,
        "factory_label": port.factory_label,
        "port_label": port.label,
        "vertex_type": side.vertexType,
    }
    if lookup is None:
        return VertexRecord(**base)
    form = lookup.fields
    type_fields = form.typeFields
    generic = getattr(type_fields, "generic", None) if type_fields is not None else None
    specific = getattr(type_fields, "specific", None) if type_fields is not None else None
    return VertexRecord(
        **base,
        kind=type_fields.type if type_fields is not None else None,
        label=form.label,
        description=form.desc,
        use_as_endpoint=form.useAsEndpoint,
        active=form.active,
        sips_mode=form.sipsMode,
        tags=tuple(form.localAssignedTags),
        codec_format=generic.get("codecFormat") if isinstance(generic, dict) else None,
        media_type=specific.get("type") if isinstance(specific, dict) else None,
        sdp_support=specific.get("sdpSupport") if isinstance(specific, dict) else None,
        main_destination_port=_endpoint_port(generic, "mainDstInfo"),
        spare_destination_port=_endpoint_port(generic, "spareDstInfo"),
        supports_static_igmp=type_fields.supportsStaticIgmpCfg if type_fields is not None else None,
    )


def _endpoint_port(generic: Any, block: str) -> int | None:
    info = generic.get(block) if isinstance(generic, dict) else None
    port = info.get("port") if isinstance(info, dict) else None
    return int(port) if isinstance(port, (int, float)) and not isinstance(port, bool) else None


def _check_action(response: Any, action: str, tag_id: str) -> None:
    if response.header.ok and response.data.ok:
        return
    detail = "; ".join(m for m in list(response.data.msg) + list(response.header.msg) if m) or "rejected"
    raise BlueprintError(f"{action} failed for tag '{tag_id}': {detail}")


__all__ = [
    "InspectGateway",
    "ScopeData",
    "TopologyWork",
    "build_context",
    "compute_topology_work",
    "name_context",
    "resolve_interfaces",
    "verify_topology",
]
