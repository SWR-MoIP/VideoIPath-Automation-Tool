"""Transaction for Inspect topology writes ([ADR-0006]/[ADR-0009]/[ADR-0010]).

A transaction stages topology changes, captures a per-entity baseline via the lookup endpoints
(the lookup forms *are* the ``updateTopology`` write shapes — [ADR-0009]), and applies them
atomically on ``commit()``. Commit runs a client-side compare-and-commit conflict check against
freshly re-fetched baselines, then a single ``updateTopology`` POST, then a three-flag success
evaluation ([ADR-0006]). On success it drives a targeted snapshot refresh ([ADR-0010]) instead of
a full reload.

Caller mutations are field-level *intents* recorded against the staged baseline and applied at
commit-build time, so ``rebase()`` can re-fetch baselines and re-apply the same intents.

Verified server facts encoded here (2025.4.9):
- ``replaceDevices`` / ``replaceVertices`` take the lookup *edit form*; ``replaceVertices`` is
  update-only (vertices cannot be created via ``updateTopology``).
- ``descriptor`` is *mandatory* in the device edit form, so it is always round-tripped from the
  baseline; ``descriptor.label`` is only changed when the caller sets a label explicitly (the
  Inspect UI has the same behaviour — the persisted descriptor is not distinguishable from the
  effective one on the collector surface).
- ``replaceEdges`` takes the raw persisted edge form; there is no ``_rev`` anywhere (last-writer-wins).
- Apply is reject-before-apply (all-or-nothing), so a detected conflict aborts the whole commit.
"""

from __future__ import annotations

import copy
import logging
from typing import TYPE_CHECKING, Any, Optional

from pydantic import Field

from videoipath_automation_tool.apps.inspect.errors import (
    InspectCommitConflictError,
    InspectCommitError,
    InspectConflict,
    InspectEntityNotFoundError,
)
from videoipath_automation_tool.apps.inspect.model.actions import (
    InspectApiEdgeForm,
    InspectApiLookupInspectDeviceFields,
    InspectApiVertexControlProps,
    InspectApiVertexEditForm,
)
from videoipath_automation_tool.apps.inspect.model.common import (
    CONFLICT_PRIORITY_TO_INT,
    InspectConfigPriority,
    InspectFrozenModel,
    InspectIconSize,
    InspectIconType,
    InspectInternalModel,
    InspectRedundancyMode,
    InspectSdpStrategy,
)
from videoipath_automation_tool.apps.inspect.model.update_topology import (
    InspectApiUpdateTopologyData,
    InspectApiUpdateTopologyResponse,
)

if TYPE_CHECKING:
    from videoipath_automation_tool.apps.inspect.api import InspectAPI
    from videoipath_automation_tool.apps.inspect.snapshot import InspectSnapshot


class CommitResult(InspectFrozenModel):
    """Outcome of a successful commit ([ADR-0006]); a failed commit raises ``InspectCommitError``."""

    applied_ids: list[str]
    created_ids: list[str]
    response: InspectApiUpdateTopologyResponse

    @property
    def ok(self) -> bool:
        return True

    @property
    def validation(self) -> Any:
        return self.response.data.validation


class InspectTransaction:
    """Single-use, atomic batch of Inspect topology changes.

    Stage changes with the ``place_device`` / ``update_*`` / ``connect`` / ``disconnect`` / ``remove``
    methods, then call ``commit()``. The transaction cannot be reused after commit or discard; use
    it as a context manager to guarantee cleanup (exit without commit discards and logs a warning).
    """

    def __init__(
        self,
        api: "InspectAPI",
        snapshot: Optional["InspectSnapshot"] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._api = api
        self._snapshot = snapshot
        self._logger = logger or logging.getLogger("videoipath_automation_tool_inspect_txn")
        self._entries: dict[tuple[str, str], _Staged] = {}
        self._committed = False
        self._discarded = False

    # --- Context manager ---

    def __enter__(self) -> "InspectTransaction":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if exc_type is not None:
            self.discard()
            return
        if not self._committed and not self._discarded:
            if self._entries:
                self._logger.warning(
                    "Inspect transaction exited with %d staged change(s) and no commit(); discarding.",
                    len(self._entries),
                )
            self.discard()

    # --- Introspection ---

    @property
    def staged(self) -> list[tuple[str, str]]:
        return list(self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    # --- Staging: devices ---

    def place_device(self, device_id: str, x: float, y: float) -> "InspectTransaction":
        """Move a device to grid coordinates (``replaceDevices``)."""
        entry = self._stage_device(device_id)
        entry.intents["coordinates"] = {"x": x, "y": y}
        return self

    def update_device(
        self,
        device_id: str,
        *,
        label: Optional[str] = None,
        description: Optional[str] = None,
        icon_type: Optional[InspectIconType | str] = None,
        icon_size: Optional[InspectIconSize | str] = None,
        sdp_strategy: Optional[InspectSdpStrategy | str] = None,
        site_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
        coordinates: Optional[dict[str, float]] = None,
    ) -> "InspectTransaction":
        """Edit a device's edit-dialog fields (``replaceDevices``).

        Covers the Inspect UI "Edit Device" dialog: ``label`` / ``description`` (the persisted
        ``descriptor``), ``tags``, ``site_id``, ``icon_size``, ``icon_type`` and ``sdp_strategy``,
        plus ``coordinates`` for placement. ``descriptor`` is always round-tripped from the baseline
        (it is mandatory server-side); ``label`` / ``description`` are applied to it only when set here.
        """
        entry = self._stage_device(device_id)
        if label is not None:
            entry.intents["descriptor.label"] = label
        if description is not None:
            entry.intents["descriptor.desc"] = description
        if icon_type is not None:
            entry.intents["iconType"] = icon_type
        if icon_size is not None:
            entry.intents["iconSize"] = icon_size
        if sdp_strategy is not None:
            entry.intents["sdpStrategy"] = sdp_strategy
        if site_id is not None:
            entry.intents["siteId"] = site_id
        if tags is not None:
            entry.intents["tags"] = list(tags)
        if coordinates is not None:
            entry.intents["coordinates"] = dict(coordinates)
        return self

    # --- Staging: vertices ---

    def update_vertex(
        self,
        vertex_id: str,
        *,
        use_as_endpoint: Optional[bool] = None,
        label: Optional[str] = None,
        tags: Optional[list[str]] = None,
        description: Optional[str] = None,
        active: Optional[bool] = None,
        sips_mode: Optional[str] = None,
        control_props: Optional[Any] = None,
        extra_alert_filters: Optional[list[Any]] = None,
        custom: Optional[dict[str, Any]] = None,
        park_port: Optional[int] = None,
        # IP-vertex ``typeFields`` (only meaningful on IP vertices):
        ip_address: Optional[str] = None,
        ip_netmask: Optional[str] = None,
        public: Optional[bool] = None,
        vlan_id: Optional[str] = None,
        vrf_id: Optional[str] = None,
        supports_cpipe: Optional[bool] = None,
        supports_igmp: Optional[bool] = None,
        supports_mac_forwarding: Optional[bool] = None,
        supports_nso: Optional[bool] = None,
        supports_openflow: Optional[bool] = None,
        supports_static_igmp: Optional[bool] = None,
        supports_vlan: Optional[bool] = None,
        supports_vpls: Optional[bool] = None,
    ) -> "InspectTransaction":
        """Edit a vertex/port (``replaceVertices``; update-only — vertices cannot be created here).

        Covers the "Edit vertex" / bulk-edit dialogs: base fields plus the IP-vertex ``typeFields``
        (address, netmask, VLAN, VRF, public, and the "Config supports" flags). ``tags`` assigns
        catalog tags to the port (as ``Category~~name`` ids), written to the vertex
        ``localAssignedTags``.
        """
        entry = self._stage_vertex(vertex_id)
        if use_as_endpoint is not None:
            entry.intents["useAsEndpoint"] = use_as_endpoint
        if label is not None:
            entry.intents["label"] = label
        if tags is not None:
            # Port tag assignment is the vertex's localAssignedTags (verified 2025.4.9); the
            # separate ``fields.tags`` list does not register as an assigned tag.
            entry.intents["localAssignedTags"] = list(tags)
        if description is not None:
            entry.intents["desc"] = description
        if active is not None:
            entry.intents["active"] = active
        if sips_mode is not None:
            entry.intents["sipsMode"] = sips_mode
        if control_props is not None:
            if isinstance(control_props, dict):
                entry.intents["controlProps"] = InspectApiVertexControlProps.model_validate(control_props)
            else:
                entry.intents["controlProps"] = control_props
        if extra_alert_filters is not None:
            entry.intents["extraAlertFilters"] = list(extra_alert_filters)
        if custom is not None:
            entry.intents["custom"] = dict(custom)

        # IP-vertex typeFields, applied as one-level dotted intents (require a populated typeFields
        # baseline, which IP/router/codec vertices have from the lookup edit form).
        for value, wire_field in (
            (park_port, "parkPort"),
            (ip_address, "ipAddress"),
            (ip_netmask, "ipNetmask"),
            (public, "public"),
            (vlan_id, "vlanId"),
            (vrf_id, "vrfId"),
            (supports_cpipe, "supportsCpipeCfg"),
            (supports_igmp, "supportsIgmpCfg"),
            (supports_mac_forwarding, "supportsMacForwardingCfg"),
            (supports_nso, "supportsNsoCfg"),
            (supports_openflow, "supportsOpenflowCfg"),
            (supports_static_igmp, "supportsStaticIgmpCfg"),
            (supports_vlan, "supportsVlanCfg"),
            (supports_vpls, "supportsVplsCfg"),
        ):
            if value is not None:
                entry.intents[f"typeFields.{wire_field}"] = value
        return self

    # --- Staging: edges ---

    def update_edge(
        self,
        edge_id: str,
        *,
        label: Optional[str] = None,
        description: Optional[str] = None,
        weight: Optional[int] = None,
        capacity: Optional[int] = None,
        bandwidth: Optional[float] = None,
        redundancy_mode: Optional[InspectRedundancyMode | str] = None,
        conflict_priority: Optional[InspectConfigPriority | int | str] = None,
        include_formats: Optional[list[str]] = None,
        exclude_formats: Optional[list[str]] = None,
        bandwidth_weight_factor: Optional[int] = None,
        weight_per_service: Optional[int] = None,
        active: Optional[bool] = None,
        tags: Optional[list[str]] = None,
        also_opposite: bool = False,
    ) -> "InspectTransaction":
        """Edit an existing edge's "Edit Edge" dialog fields (``replaceEdges``).

        With ``also_opposite`` the same changes are staged on the opposite directed edge (the reverse
        ``.out`` <-> ``.in`` edge, as the Inspect UI's "apply changes to opposite directed edge"
        option does); raises ``InspectEntityNotFoundError`` if that opposite edge does not exist.
        """
        fields = dict(
            label=label,
            description=description,
            weight=weight,
            capacity=capacity,
            bandwidth=bandwidth,
            redundancy_mode=redundancy_mode,
            conflict_priority=conflict_priority,
            include_formats=include_formats,
            exclude_formats=exclude_formats,
            bandwidth_weight_factor=bandwidth_weight_factor,
            weight_per_service=weight_per_service,
            active=active,
            tags=tags,
        )
        self._apply_edge_update(edge_id, fields)
        if also_opposite:
            opposite_id = _opposite_edge_id(edge_id)
            if self._lookup_edge_form(opposite_id) is None:
                raise InspectEntityNotFoundError(opposite_id, kind="edge")
            self._apply_edge_update(opposite_id, fields)
        return self

    def _apply_edge_update(self, edge_id: str, fields: dict[str, Any]) -> None:
        entry = self._stage_edge(edge_id)
        if fields["label"] is not None:
            entry.intents["descriptor.label"] = fields["label"]
        if fields["description"] is not None:
            entry.intents["descriptor.desc"] = fields["description"]
        if fields["weight"] is not None:
            entry.intents["weight"] = fields["weight"]
        if fields["capacity"] is not None:
            entry.intents["capacity"] = fields["capacity"]
        if fields["bandwidth"] is not None:
            entry.intents["bandwidth"] = fields["bandwidth"]
        if fields["redundancy_mode"] is not None:
            entry.intents["redundancyMode"] = fields["redundancy_mode"]
        if fields["conflict_priority"] is not None:
            entry.intents["conflictPri"] = _conflict_priority_to_wire(fields["conflict_priority"])
        if fields["include_formats"] is not None:
            entry.intents["includeFormats"] = list(fields["include_formats"])
        if fields["exclude_formats"] is not None:
            entry.intents["excludeFormats"] = list(fields["exclude_formats"])
        if fields["active"] is not None:
            entry.intents["active"] = fields["active"]
        if fields["tags"] is not None:
            entry.intents["tags"] = list(fields["tags"])
        if fields["bandwidth_weight_factor"] is not None or fields["weight_per_service"] is not None:
            entry.intents["weightFactors"] = _merged_weight_factors(
                entry.baseline_form.weightFactors,
                fields["bandwidth_weight_factor"],
                fields["weight_per_service"],
            )

    def connect(
        self,
        from_vertex: str,
        to_vertex: str,
        *,
        bidirectional: bool = True,
        overwrite: bool = False,
        **edge_fields: Any,
    ) -> "InspectTransaction":
        """Create an edge from an out-vertex to an in-vertex (``replaceEdges``).

        With ``bidirectional`` (default) the reverse edge (``to``'s out -> ``from``'s in) is staged
        too. Set ``overwrite=True`` to replace an edge that already exists. ``edge_fields`` override
        the persisted-edge defaults (e.g. ``weight``, ``capacity``, ``bandwidth``, ``redundancyMode``).
        """
        self._stage_new_edge(from_vertex, to_vertex, overwrite=overwrite, edge_fields=edge_fields)
        if bidirectional:
            self._stage_new_edge(
                _reverse_vertex(to_vertex), _reverse_vertex(from_vertex), overwrite=overwrite, edge_fields=edge_fields
            )
        return self

    def disconnect(self, from_vertex: str, to_vertex: str, *, bidirectional: bool = True) -> "InspectTransaction":
        """Remove the edge from ``from_vertex`` to ``to_vertex`` (and its reverse if bidirectional)."""
        self.remove(_edge_key(from_vertex, to_vertex))
        if bidirectional:
            self.remove(_edge_key(_reverse_vertex(to_vertex), _reverse_vertex(from_vertex)))
        return self

    # --- Staging: removals ---

    def remove(self, entity_id: str) -> "InspectTransaction":
        """Remove any entity by id (device / vertex / edge key). Last-writer-wins (no conflict check)."""
        self._ensure_open()
        kind = _entity_kind(entity_id)
        self._entries[(kind, entity_id)] = _Staged(kind=kind, entity_id=entity_id, remove=True)
        return self

    def remove_device(self, device_id: str) -> "InspectTransaction":
        """Remove a device (its baseDevice element) from the topology graph."""
        return self.remove(device_id)

    # --- Commit lifecycle ---

    def commit(self, check_conflicts: bool = True) -> CommitResult:
        """Validate, send, and (on success) refresh. Raises on conflict or server rejection.

        Raises:
            InspectCommitConflictError: a staged entity changed on the server since staging.
            InspectCommitError: the server rejected the commit (validation or apply gate).
        """
        self._ensure_open()
        if not self._entries:
            raise ValueError("Nothing staged; commit aborted.")

        if check_conflicts:
            self._check_conflicts()

        delta = self._build_delta()
        response = self._api.update_topology(delta)
        if not response.committed:
            raise InspectCommitError(response)

        self._committed = True
        applied_ids = [e.entity_id for e in self._entries.values()]
        result = CommitResult(
            applied_ids=applied_ids,
            created_ids=list(response.data.validation.createIds),
            response=response,
        )
        self._refresh_snapshot()
        self._logger.debug("Inspect commit applied %d change(s): %s", len(applied_ids), applied_ids)
        return result

    def rebase(self) -> "InspectTransaction":
        """Re-fetch baselines for all staged entities, keeping the recorded intents.

        Use after ``InspectCommitConflictError`` to move the staged changes onto current server
        state; then ``commit()`` again. Intents that themselves target a concurrently-changed field
        will overwrite that change (last-writer-wins for the intent).
        """
        self._ensure_open()
        for entry in self._entries.values():
            if entry.remove or entry.is_new or entry.baseline_form is None:
                continue
            fresh = self._fetch_baseline(entry.kind, entry.entity_id)
            entry.baseline_form = fresh
            entry.baseline_dump = fresh.model_dump(mode="json")
        return self

    def discard(self) -> None:
        """Drop all staged changes; the transaction can no longer be committed."""
        self._entries.clear()
        self._discarded = True

    # --- Internal: staging helpers ---

    def _ensure_open(self) -> None:
        if self._committed:
            raise RuntimeError("This transaction was already committed; open a new one.")
        if self._discarded:
            raise RuntimeError("This transaction was discarded; open a new one.")

    def _stage_device(self, device_id: str) -> _Staged:
        return self._stage(_DEVICE, device_id)

    def _stage_vertex(self, vertex_id: str) -> _Staged:
        return self._stage(_VERTEX, vertex_id)

    def _stage_edge(self, edge_id: str) -> _Staged:
        return self._stage(_EDGE, edge_id)

    def _stage(self, kind: str, entity_id: str) -> _Staged:
        self._ensure_open()
        key = (kind, entity_id)
        existing = self._entries.get(key)
        if existing is not None and not existing.remove:
            return existing
        baseline = self._fetch_baseline(kind, entity_id)
        entry = _Staged(
            kind=kind,
            entity_id=entity_id,
            baseline_form=baseline,
            baseline_dump=baseline.model_dump(mode="json"),
        )
        self._entries[key] = entry
        return entry

    def _stage_new_edge(
        self, from_vertex: str, to_vertex: str, *, overwrite: bool, edge_fields: dict[str, Any]
    ) -> None:
        self._ensure_open()
        edge_id = _edge_key(from_vertex, to_vertex)
        existing = self._lookup_edge_form(edge_id)
        if existing is not None and not overwrite:
            raise ValueError(f"Edge '{edge_id}' already exists; pass overwrite=True to replace it.")
        form = (
            existing.model_copy(deep=True)
            if existing is not None
            else InspectApiEdgeForm(fromId=from_vertex, toId=to_vertex)
        )
        form.fromId = from_vertex
        form.toId = to_vertex
        entry = _Staged(
            kind=_EDGE,
            entity_id=edge_id,
            baseline_form=form,
            baseline_dump=None if existing is None else existing.model_dump(mode="json"),
            intents=dict(edge_fields),
            is_new=existing is None,
        )
        self._entries[(_EDGE, edge_id)] = entry

    # --- Internal: baselines ---

    def _fetch_baseline(self, kind: str, entity_id: str) -> Any:
        if kind == _DEVICE:
            return self._lookup_device_form(entity_id, required=True)
        if kind == _VERTEX:
            return self._lookup_vertex_form(entity_id, required=True)
        form = self._lookup_edge_form(entity_id)
        if form is None:
            raise InspectEntityNotFoundError(entity_id, kind="edge")
        return form

    def _lookup_device_form(self, device_id: str, required: bool) -> Optional[InspectApiLookupInspectDeviceFields]:
        try:
            response = self._api.lookup_inspect_device(device_id)
        except Exception as exc:  # connector-level miss
            if required:
                raise InspectEntityNotFoundError(device_id, kind="device") from exc
            return None
        return response.data.fields

    def _lookup_vertex_form(self, vertex_id: str, required: bool) -> Optional[InspectApiVertexEditForm]:
        response = self._api.lookup_vertices([vertex_id])
        item = response.data.get(vertex_id)
        if item is None:
            if required:
                raise InspectEntityNotFoundError(vertex_id, kind="vertex")
            return None
        return item.fields

    def _lookup_edge_form(self, edge_id: str) -> Optional[InspectApiEdgeForm]:
        response = self._api.lookup_edges([edge_id])
        item = response.data.get(edge_id)
        return item.edge if item is not None else None

    # --- Internal: conflict check (compare-and-commit, ADR-0009) ---

    def _check_conflicts(self) -> None:
        current = self._refetch_baselines()
        conflicts: list[InspectConflict] = []
        for entry in self._entries.values():
            if entry.remove or entry.is_new or entry.baseline_dump is None:
                continue
            key = (entry.kind, entry.entity_id)
            server_form = current.get(key)
            if server_form is None:
                conflicts.append(InspectConflict(entry.entity_id, entry.kind, {"__exists__": (True, False)}))
                continue
            server_dump = server_form.model_dump(mode="json")
            if server_dump != entry.baseline_dump:
                diffs = _field_diffs(entry.baseline_dump, server_dump)
                conflicts.append(InspectConflict(entry.entity_id, entry.kind, diffs))
        if conflicts:
            raise InspectCommitConflictError(conflicts)

    def _refetch_baselines(self) -> dict[tuple[str, str], Any]:
        """Batched re-fetch of every conflict-checkable staged entity's current server form."""
        vertex_ids = [e.entity_id for e in self._entries.values() if e.kind == _VERTEX and _checkable(e)]
        edge_ids = [e.entity_id for e in self._entries.values() if e.kind == _EDGE and _checkable(e)]
        device_ids = [e.entity_id for e in self._entries.values() if e.kind == _DEVICE and _checkable(e)]

        current: dict[tuple[str, str], Any] = {}
        if vertex_ids:
            data = self._api.lookup_vertices(vertex_ids).data
            for vid in vertex_ids:
                item = data.get(vid)
                if item is not None:
                    current[(_VERTEX, vid)] = item.fields
        if edge_ids:
            data = self._api.lookup_edges(edge_ids).data
            for eid in edge_ids:
                item = data.get(eid)
                if item is not None:
                    current[(_EDGE, eid)] = item.edge
        for did in device_ids:
            form = self._lookup_device_form(did, required=False)
            if form is not None:
                current[(_DEVICE, did)] = form
        return current

    # --- Internal: payload build ---

    def _build_delta(self) -> InspectApiUpdateTopologyData:
        delta = InspectApiUpdateTopologyData()
        for entry in self._entries.values():
            if entry.remove:
                delta.remove.append(entry.entity_id)
                continue
            form = entry.baseline_form.model_copy(deep=True)
            _apply_intents(form, entry.intents)
            if entry.kind == _DEVICE:
                delta.replaceDevices[entry.entity_id] = form
            elif entry.kind == _VERTEX:
                delta.replaceVertices[entry.entity_id] = form
            else:
                delta.replaceEdges[entry.entity_id] = form
        return delta

    # --- Internal: post-commit targeted refresh (ADR-0010) ---

    def _refresh_snapshot(self) -> None:
        if self._snapshot is None:
            return
        removed_ids: list[str] = []
        device_ids: set[str] = set()
        pair_ids: set[str] = set()
        for entry in self._entries.values():
            if entry.remove:
                removed_ids.append(entry.entity_id)
                if entry.kind == _EDGE:
                    pair_ids.update(_pair_ids_for_edge(entry.entity_id))
                continue
            if entry.kind == _DEVICE:
                device_ids.add(entry.entity_id)
            elif entry.kind == _VERTEX:
                device_ids.add(_device_of(entry.entity_id))
            else:
                pair_ids.update(_pair_ids_for_edge(entry.entity_id))
        self._snapshot.apply_post_commit(
            removed_ids=removed_ids,
            device_ids=list(device_ids),
            pair_ids=list(pair_ids),
            mark_paths_stale=True,
        )


# --- Internal ---

# Staged-entry kinds.
_DEVICE = "device"
_VERTEX = "vertex"
_EDGE = "edge"


class _Staged(InspectInternalModel):
    kind: str
    entity_id: str
    # The write-shape baseline (edit/edge form) as fetched at stage time; None for a raw remove.
    baseline_form: Any | None = None
    # JSON dump of the baseline at stage time, used for the compare-and-commit conflict check.
    baseline_dump: dict[str, Any] | None = None
    # Field-level intents (wire field names; dotted for one level of nesting, e.g. "descriptor.label").
    intents: dict[str, Any] = Field(default_factory=dict)
    remove: bool = False
    is_new: bool = False


def _device_of(entity_id: str) -> str:
    """Owning device id of a vertex/port id (``device12.1.Ethernet1.out`` -> ``device12``,
    ``virtual.2.0.1`` -> ``virtual.2``)."""
    if entity_id.startswith("virtual."):
        parts = entity_id.split(".")
        if len(parts) >= 2:
            return f"{parts[0]}.{parts[1]}"
    return entity_id.split(".", 1)[0]


def _entity_kind(entity_id: str) -> str:
    """Classify an entity id as device, vertex, or edge for staging."""
    if "::" in entity_id:
        return _EDGE
    if "." not in entity_id:
        return _DEVICE
    # ``virtual.N`` is a device id (dotted); ``virtual.N.module.vertex`` is a vertex.
    if entity_id.startswith("virtual."):
        parts = entity_id.split(".")
        if len(parts) == 2 and parts[1].isdigit():
            return _DEVICE
    return _VERTEX


def _reverse_vertex(vertex_id: str) -> str:
    """Flip the trailing direction of an IP vertex id (``.out`` <-> ``.in``)."""
    if vertex_id.endswith(".out"):
        return vertex_id[: -len(".out")] + ".in"
    if vertex_id.endswith(".in"):
        return vertex_id[: -len(".in")] + ".out"
    return vertex_id


def _edge_key(from_id: str, to_id: str) -> str:
    return f"{from_id}::{to_id}"


def _opposite_edge_id(edge_id: str) -> str:
    """The opposite directed edge of ``fromId::toId`` — ``reverse(toId)::reverse(fromId)`` with the
    trailing ``.out`` <-> ``.in`` direction flipped on each vertex."""
    from_id, to_id = edge_id.split("::", 1)
    return _edge_key(_reverse_vertex(to_id), _reverse_vertex(from_id))


def _conflict_priority_to_wire(value: InspectConfigPriority | int | str) -> int | str:
    """Map a friendly conflict-priority name (off/high/normal/low) to the on-wire int; pass ints and
    unknown values through unchanged."""
    if isinstance(value, str):
        return CONFLICT_PRIORITY_TO_INT.get(value, value)
    return value


def _merged_weight_factors(
    baseline: Any, bandwidth_weight_factor: Optional[int], weight_per_service: Optional[int]
) -> dict[str, Any]:
    """Merge the requested weight-factor changes onto a deep copy of the baseline ``weightFactors``
    (a nested dict), preserving untouched sub-values (e.g. ``service.max``)."""
    merged: dict[str, Any] = copy.deepcopy(baseline) if isinstance(baseline, dict) else {}
    merged.setdefault("bandwidth", {})
    merged.setdefault("service", {})
    if bandwidth_weight_factor is not None:
        merged["bandwidth"]["weight"] = bandwidth_weight_factor
    if weight_per_service is not None:
        merged["service"]["weight"] = weight_per_service
    return merged


def _apply_intents(form: Any, intents: dict[str, Any]) -> None:
    for key, value in intents.items():
        if "." in key:
            head, tail = key.split(".", 1)
            setattr(getattr(form, head), tail, value)
        else:
            setattr(form, key, value)


def _checkable(entry: _Staged) -> bool:
    return not entry.remove and not entry.is_new and entry.baseline_dump is not None


def _field_diffs(baseline: dict[str, Any], current: dict[str, Any]) -> dict[str, tuple[object, object]]:
    diffs: dict[str, tuple[object, object]] = {}
    for key in set(baseline) | set(current):
        before = baseline.get(key)
        after = current.get(key)
        if before != after:
            diffs[key] = (before, after)
    return diffs


def _pair_ids_for_edge(edge_id: str) -> tuple[str, ...]:
    """Both possible collector pair-key orderings for an edge (one is a no-op on refresh)."""
    if "::" not in edge_id:
        return ()
    from_id, to_id = edge_id.split("::", 1)
    dev_a, dev_b = _device_of(from_id), _device_of(to_id)
    if dev_a == dev_b:
        return (f"{dev_a}::{dev_b}",)
    return (f"{dev_a}::{dev_b}", f"{dev_b}::{dev_a}")


__all__ = ["InspectTransaction", "CommitResult"]
