"""InspectSnapshot: skeleton-first, lazily-hydrated, accreting read state ([ADR-0007]).

A snapshot is built from two scoped skeleton reads (all devices without module/port detail, all
external-edge pairs). Detail is hydrated on demand — the first access to a device's ports fetches
that one device's full nodeStatus sub-tree and merges it into the same internal indexes; services
load once as a section. The snapshot is never a single point in time: each device and section
carries its own fetch timestamp. ``refresh()`` builds a *new* snapshot; state is never reused
across snapshots.

After a successful commit the transaction calls the post-commit hooks here to update only the
touched entities via targeted scoped re-reads ([ADR-0010]) instead of a full reload.
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Iterator, Optional

from pydantic import Field

from videoipath_automation_tool.apps.inspect.model.alarms import InspectApiAlarmItem
from videoipath_automation_tool.apps.inspect.model.collector import (
    InspectApiCollectorResponse,
    InspectApiExternalEdgeLiveStatus,
    InspectApiExternalEdgesByDeviceKeyItem,
    InspectApiExternalEdgeStatus,
    InspectApiModuleStatus,
    InspectApiNodeStatusItem,
    InspectApiPathItem,
    InspectApiSingleVertexInfo,
    InspectPortStatus,
)
from videoipath_automation_tool.apps.inspect.model.common import (
    InspectFrozenModel,
    InspectInternalModel,
    InspectSeverity,
    _STAGED_MISSING,
    format_repr,
)

if TYPE_CHECKING:
    from videoipath_automation_tool.apps.inspect.domain.alarm import InspectAlarm
    from videoipath_automation_tool.apps.inspect.domain.device import InspectDevice
    from videoipath_automation_tool.apps.inspect.domain.edge import InspectEdge
    from videoipath_automation_tool.apps.inspect.domain.module import InspectModule
    from videoipath_automation_tool.apps.inspect.domain.port import InspectPort
    from videoipath_automation_tool.apps.inspect.domain.service import InspectService
    from videoipath_automation_tool.apps.inspect.domain.vertex import InspectVertex
    from videoipath_automation_tool.apps.inspect.api import InspectAPI
    from videoipath_automation_tool.apps.inspect.model.actions import (
        InspectApiEdgeForm,
        InspectApiLookupVertexResponseData,
    )


class HydrationLevel(str, Enum):
    SKELETON = "skeleton"
    FULL = "full"


class InspectSnapshot:
    def __init__(
        self,
        fetcher: Optional["InspectAPI"] = None,
        device_items: Optional[list[InspectApiNodeStatusItem]] = None,
        edge_items: Optional[list[InspectApiExternalEdgesByDeviceKeyItem]] = None,
        *,
        device_level: HydrationLevel = HydrationLevel.SKELETON,
        path_items: Optional[list[InspectApiPathItem]] = None,
        alarm_items: Optional[list[InspectApiAlarmItem]] = None,
    ) -> None:
        self._fetcher = fetcher
        self._lock = threading.RLock()
        self._created_at = _now()

        # Core indexes
        self._devices_by_id: dict[str, _DeviceRecord] = {}
        self._devices_by_label: dict[str, list[str]] = {}
        self._edge_pairs: dict[str, InspectApiExternalEdgesByDeviceKeyItem] = {}
        self._edges_by_device_id: dict[str, list[_IndexedEdge]] = {}
        self._edge_by_port_key: dict[tuple[str, str], _IndexedEdge] = {}

        # Per-device port + module indexes (populated on hydration)
        self._ports_by_device_id: dict[str, list[_IndexedPort]] = {}
        self._port_by_key: dict[tuple[str, str], _IndexedPort] = {}
        self._ports_by_pid: dict[str, list[_IndexedPort]] = {}
        self._modules_by_device_id: dict[str, dict[str, InspectApiModuleStatus]] = {}

        # Vertex edit-form details, fetched lazily per vertex ([ADR-0007]) and invalidated when the
        # owning device's ports are rebuilt after a refresh/commit.
        self._vertex_details: dict[str, "InspectApiLookupVertexResponseData"] = {}

        # Edge edit-form details, fetched lazily per edge ([ADR-0007]) and invalidated when the
        # owning edge pair is dropped/re-indexed after a refresh/commit.
        self._edge_details: dict[str, "InspectApiEdgeForm"] = {}

        # Section: services / paths
        self._paths_by_booking_id: dict[str, InspectApiPathItem] = {}
        self._services_by_device_id: dict[str, list[str]] = {}
        self._section_loaded: dict[str, bool] = {"paths": False, "alarms": False}
        self._section_fetched_at: dict[str, datetime] = {}

        # Section: current alarms (status/alarms/current), indexed by resource key
        self._alarms: list[InspectApiAlarmItem] = []
        self._alarms_by_device_id: dict[str, list[InspectApiAlarmItem]] = {}
        self._alarms_by_resource_key: dict[str, list[InspectApiAlarmItem]] = {}

        # Domain-object caches
        self._device_cache: dict[str, "InspectDevice"] = {}
        self._module_cache: dict[tuple[str, str], "InspectModule"] = {}
        self._edge_cache: dict[str, "InspectEdge"] = {}
        self._service_cache: dict[str, "InspectService"] = {}

        # Entities whose post-write re-fetch failed; re-fetched lazily on next access ([ADR-0010]).
        self._stale_devices: set[str] = set()
        self._stale_pairs: set[str] = set()

        # Pending domain-object edits (wire-field intents) staged by setters before update()/commit.
        # Keyed by (kind, entity_id) where kind is "device" / "vertex" / "edge".
        self._pending_edits: dict[tuple[str, str], dict[str, Any]] = {}

        for node in device_items or []:
            self._index_device(node, device_level)
        for pair in edge_items or []:
            self._index_edge_pair(pair)
        if path_items is not None:
            self._index_paths(path_items)
            self._section_loaded["paths"] = True
            self._section_fetched_at["paths"] = self._created_at
        if alarm_items is not None:
            self._index_alarms(alarm_items)
            self._section_loaded["alarms"] = True
            self._section_fetched_at["alarms"] = self._created_at

    def __repr__(self) -> str:
        return format_repr(
            self,
            devices=len(self._devices_by_id),
            edge_pairs=len(self._edge_pairs),
        )

    __str__ = __repr__

    # --- Construction ---

    @classmethod
    def from_full_response(
        cls, response: InspectApiCollectorResponse, fetcher: Optional["InspectAPI"] = None
    ) -> "InspectSnapshot":
        """Build a fully-hydrated snapshot from one full collector aggregate (eager / fallback mode)."""
        collector = response.data.status.collector
        return cls(
            fetcher=fetcher,
            device_items=collector.inspect.node_status_items,
            edge_items=collector.external_edges_by_device_key_items,
            device_level=HydrationLevel.FULL,
            path_items=collector.inspect.path_items,
        )

    # Backwards-compatible alias for the original draft API.
    from_response = from_full_response

    # --- Freshness / introspection ---

    @property
    def created_at(self) -> datetime:
        return self._created_at

    def fetched_at(self, device_id: str) -> datetime | None:
        record = self._devices_by_id.get(device_id)
        return record.fetched_at if record else None

    def section_fetched_at(self, section: str = "paths") -> datetime | None:
        return self._section_fetched_at.get(section)

    def is_device_hydrated(self, device_id: str) -> bool:
        record = self._devices_by_id.get(device_id)
        return record is not None and record.level is HydrationLevel.FULL

    # --- Device reads ---

    def get_device(self, device_id: str) -> Optional["InspectDevice"]:
        self._reconcile_stale_device(device_id)
        if device_id not in self._devices_by_id:
            return None
        return self._wrap_device(device_id)

    # Backwards-compatible alias.
    get_device_by_id = get_device

    def find_device_by_label(self, label: str) -> Optional["InspectDevice"]:
        ids = self._devices_by_label.get(label, [])
        return self._wrap_device(ids[0]) if ids else None

    def find_devices_by_label(self, label: str) -> list["InspectDevice"]:
        return [self._wrap_device(device_id) for device_id in self._devices_by_label.get(label, [])]

    # Backwards-compatible alias.
    find_devices_by_name = find_devices_by_label

    @property
    def devices(self) -> list["InspectDevice"]:
        return [self._wrap_device(device_id) for device_id in self._devices_by_id]

    def get_devices(self, detail: bool = False) -> list["InspectDevice"]:
        if detail:
            self.preload()
        return self.devices

    def get_device_record(self, device_id: str) -> Optional[_DeviceRecord]:
        """Internal: return the (possibly hydrated) record for a device; used by domain objects."""
        self._reconcile_stale_device(device_id)
        return self._devices_by_id.get(device_id)

    # --- Module + port reads (trigger hydration) ---

    def get_modules_for_device(self, device_id: str) -> list["InspectModule"]:
        self._ensure_device_detail(device_id)
        return [self._wrap_module(device_id, module_id) for module_id in self._modules_by_device_id.get(device_id, {})]

    def get_module(self, device_id: str, module_id: str) -> Optional["InspectModule"]:
        self._ensure_device_detail(device_id)
        if module_id not in self._modules_by_device_id.get(device_id, {}):
            return None
        return self._wrap_module(device_id, module_id)

    def get_module_status(self, device_id: str, module_id: str) -> Optional[InspectApiModuleStatus]:
        """The raw module status (for domain objects to resolve live); None if the module is gone."""
        return self._modules_by_device_id.get(device_id, {}).get(module_id)

    def get_ports_for_device(self, device_id: str) -> list["InspectPort"]:
        self._ensure_device_detail(device_id)
        return [self._wrap_port(indexed) for indexed in self._ports_by_device_id.get(device_id, [])]

    def get_ports_for_module(self, device_id: str, module_id: str) -> list["InspectPort"]:
        self._ensure_device_detail(device_id)
        return [
            self._wrap_port(indexed)
            for indexed in self._ports_by_device_id.get(device_id, [])
            if indexed.module_id == module_id
        ]

    def get_port(self, device_id: str, port_id: str) -> Optional["InspectPort"]:
        self._ensure_device_detail(device_id)
        indexed = self._port_by_key.get((device_id, port_id))
        return self._wrap_port(indexed) if indexed else None

    def find_port_by_id(self, port_id: str) -> Optional["InspectPort"]:
        indexed = self._ports_by_pid.get(port_id)
        return self._wrap_port(indexed[0]) if indexed else None

    # --- Vertex detail reads (trigger lookup) ---

    def get_vertex_details(self, vertex_id: str) -> Optional["InspectApiLookupVertexResponseData"]:
        return self.get_vertex_details_many([vertex_id]).get(vertex_id)

    def get_vertex_details_many(self, vertex_ids: list[str]) -> dict[str, "InspectApiLookupVertexResponseData"]:
        """Batched, cached vertex edit-form lookup (``lookupInspectVertexByIds``). Only uncached ids
        are fetched, in a single call; without a fetcher only cached entries are returned."""
        missing = [vertex_id for vertex_id in vertex_ids if vertex_id not in self._vertex_details]
        if missing and self._fetcher is not None:
            response = self._fetcher.lookup_vertices(missing)
            with self._lock:
                self._vertex_details.update(response.data)
        return {
            vertex_id: detail for vertex_id in vertex_ids if (detail := self._vertex_details.get(vertex_id)) is not None
        }

    def get_vertex(
        self,
        vertex_id: str,
        vertex_info: Optional["InspectApiSingleVertexInfo"] = None,
        *,
        port_factory_label: str | None = None,
    ) -> Optional["InspectVertex"]:
        """Typed vertex view for ``vertex_id`` (triggers a cached ``lookupInspectVertexById``); the
        concrete subclass is chosen from the edit form's ``typeFields.type``. ``vertex_info`` (the
        owning port's offline ``vertexInfo`` side) supplies the direction/status flags: when it is
        given a base vertex is still returned even if the edit form is unavailable; without it, an
        unknown vertex returns None. ``port_factory_label`` (when built via a port) is exposed as
        :attr:`InspectVertex.factory_label`."""
        lookup = self.get_vertex_details(vertex_id)
        if lookup is None and vertex_info is None:
            return None
        type_fields = lookup.fields.typeFields if lookup is not None else None
        kind = type_fields.type if type_fields is not None else None
        from videoipath_automation_tool.apps.inspect.domain.vertex import build_vertex

        return build_vertex(self, vertex_id, kind, vertex_info, port_factory_label=port_factory_label)

    # --- Edge reads (no hydration) ---

    @property
    def edges(self) -> list["InspectEdge"]:
        self._reconcile_stale_pairs()
        seen: set[str] = set()
        result: list["InspectEdge"] = []
        for indexed_edges in self._edges_by_device_id.values():
            for indexed in indexed_edges:
                if indexed.edge_id in seen:
                    continue
                seen.add(indexed.edge_id)
                result.append(self._wrap_edge(indexed))
        return result

    def get_edges(self) -> list["InspectEdge"]:
        return self.edges

    def get_edges_for_device(self, device_id: str) -> list["InspectEdge"]:
        self._reconcile_stale_pairs()
        seen: set[str] = set()
        result: list["InspectEdge"] = []
        for indexed in self._edges_by_device_id.get(device_id, []):
            if indexed.edge_id in seen:
                continue
            seen.add(indexed.edge_id)
            result.append(self._wrap_edge(indexed))
        return result

    def get_edges_for_port(self, device_id: str, port_id: str) -> list["InspectEdge"]:
        """All edges incident on a port. The read view (``externalEdgesByDeviceKey``) keys edge
        endpoints by *port* (not vertex), so edges are grouped at the port level."""
        self._reconcile_stale_pairs()
        seen: set[str] = set()
        result: list["InspectEdge"] = []
        for indexed in self._edges_by_device_id.get(device_id, []):
            on_port = (indexed.from_device_id == device_id and indexed.from_port_id == port_id) or (
                indexed.to_device_id == device_id and indexed.to_port_id == port_id
            )
            if not on_port or indexed.edge_id in seen:
                continue
            seen.add(indexed.edge_id)
            result.append(self._wrap_edge(indexed))
        return result

    def get_edge_for_port(self, device_id: str, port_id: str) -> Optional["InspectEdge"]:
        self._reconcile_stale_pairs()
        indexed = self._edge_by_port_key.get((device_id, port_id))
        return self._wrap_edge(indexed) if indexed else None

    def get_edge_details(self, edge_id: str) -> Optional["InspectApiEdgeForm"]:
        return self.get_edge_details_many([edge_id]).get(edge_id)

    def get_edge_details_many(self, edge_ids: list[str]) -> dict[str, "InspectApiEdgeForm"]:
        """Batched, cached edge edit-form lookup (``lookupInspectEdgesByIds``). Only uncached ids are
        fetched, in a single call; without a fetcher only cached entries are returned."""
        missing = [edge_id for edge_id in edge_ids if edge_id not in self._edge_details]
        if missing and self._fetcher is not None:
            response = self._fetcher.lookup_edges(missing)
            with self._lock:
                for edge_id, item in response.data.items():
                    self._edge_details[edge_id] = item.edge
        return {edge_id: detail for edge_id in edge_ids if (detail := self._edge_details.get(edge_id)) is not None}

    def get_linked_devices(self, device_id: str) -> list["InspectDevice"]:
        self._reconcile_stale_pairs()
        linked: set[str] = set()
        for indexed in self._edges_by_device_id.get(device_id, []):
            for candidate in (indexed.from_device_id, indexed.to_device_id):
                if candidate and candidate != device_id:
                    linked.add(candidate)
        return [d for lid in sorted(linked) if (d := self.get_device(lid)) is not None]

    # --- Service reads (section, trigger section load) ---

    @property
    def services(self) -> list["InspectService"]:
        self._ensure_section_paths()
        return [self._wrap_service(item) for item in self._paths_by_booking_id.values()]

    def get_services(self) -> list["InspectService"]:
        return self.services

    def get_service_by_booking_id(self, booking_id: str) -> Optional["InspectService"]:
        self._ensure_section_paths()
        item = self._paths_by_booking_id.get(booking_id)
        return self._wrap_service(item) if item else None

    def get_services_for_device(self, device_id: str) -> list["InspectService"]:
        self._ensure_section_paths()
        result: list["InspectService"] = []
        for booking_id in self._services_by_device_id.get(device_id, []):
            item = self._paths_by_booking_id.get(booking_id)
            if item is not None:
                result.append(self._wrap_service(item))
        return result

    # --- Alarm reads (section, trigger section load) ---

    def get_alarms_for_device(self, device_id: str) -> list["InspectAlarm"]:
        self._ensure_section_alarms()
        return _sorted_alarms(self._alarms_by_device_id.get(device_id, []))

    def get_alarms_for_resource(self, resource_key: str) -> list["InspectAlarm"]:
        """Alarms whose joined ``pointId`` equals ``resource_key`` (module/port pid, edge id, …)."""
        self._ensure_section_alarms()
        return _sorted_alarms(self._alarms_by_resource_key.get(resource_key, []))

    def get_alarms_for_module(self, device_id: str, module_id: str) -> list["InspectAlarm"]:
        """Alarms whose joined ``pointId`` equals the module pid (device_id reserved for callers)."""
        _ = device_id
        return self.get_alarms_for_resource(module_id)

    def get_alarms_for_port(self, port_id: str | None, *, device_id: str | None = None) -> list["InspectAlarm"]:
        _ = device_id
        if not port_id:
            return []
        return self.get_alarms_for_resource(port_id)

    def get_alarms_for_edge(self, edge_id: str, *, pair_id: str | None = None) -> list["InspectAlarm"]:
        self._ensure_section_alarms()
        items = list(self._alarms_by_resource_key.get(edge_id, []))
        if pair_id and pair_id != edge_id:
            items.extend(self._alarms_by_resource_key.get(pair_id, []))
        return _sorted_alarms(items)

    def get_alarms_for_service(self, booking_id: str) -> list["InspectAlarm"]:
        return self.get_alarms_for_resource(booking_id)

    # --- Bulk preload (ADR-0004) ---

    def preload(self, devices: Optional[list[str]] = None) -> None:
        """Hydrate multiple devices in parallel to avoid N+1 when detail is needed for many."""
        target = devices if devices is not None else list(self._devices_by_id)
        pending = [d for d in target if not self.is_device_hydrated(d)]
        if not pending or self._fetcher is None:
            for device_id in pending:
                self._ensure_device_detail(device_id)
            return
        with ThreadPoolExecutor(max_workers=min(_PRELOAD_WORKERS, len(pending))) as pool:
            list(pool.map(self._ensure_device_detail, pending))

    # --- Pending domain edits (setters → update()) ---

    def stage_edit(self, kind: str, entity_id: str, field: str, value: Any) -> None:
        """Record a pending wire-field intent for ``entity_id`` (``kind``: device/vertex/edge/module)."""
        with self._lock:
            self._pending_edits.setdefault((kind, entity_id), {})[field] = value

    def get_staged_edits(self, kind: str, entity_id: str) -> dict[str, Any]:
        """Return a copy of the pending intents for ``entity_id``, or an empty dict."""
        with self._lock:
            return dict(self._pending_edits.get((kind, entity_id), {}))

    def get_staged_value(self, kind: str, entity_id: str, field: str) -> Any:
        """Return the staged value for ``field``, or ``_STAGED_MISSING`` if none."""
        with self._lock:
            edits = self._pending_edits.get((kind, entity_id))
            if edits is None or field not in edits:
                return _STAGED_MISSING
            return edits[field]

    def iter_staged_edits(self, kind: str | None = None) -> list[tuple[str, str, dict[str, Any]]]:
        """All pending edits as ``(kind, entity_id, intents)``. Optionally filter by ``kind``."""
        with self._lock:
            return [
                (k, eid, dict(intents))
                for (k, eid), intents in self._pending_edits.items()
                if kind is None or k == kind
            ]

    def clear_staged(
        self,
        *,
        kind: str | None = None,
        entity_id: str | None = None,
        entity_ids: Optional[list[str]] = None,
    ) -> None:
        """Clear pending edits. With ``entity_id``/``entity_ids``, clear those keys (optionally
        scoped by ``kind``); with only ``kind``, clear every entity of that kind; with neither,
        clear all."""
        with self._lock:
            if entity_id is not None:
                ids = [entity_id]
            elif entity_ids is not None:
                ids = list(entity_ids)
            else:
                ids = None
            if ids is None and kind is None:
                self._pending_edits.clear()
                return
            for key in list(self._pending_edits):
                k, eid = key
                if kind is not None and k != kind:
                    continue
                if ids is not None and eid not in ids:
                    continue
                self._pending_edits.pop(key, None)

    # --- Refresh ---

    def refresh(self) -> "InspectSnapshot":
        """Return a *new* snapshot from a fresh skeleton read (never mutates this one)."""
        if self._fetcher is None:
            raise RuntimeError("This snapshot has no fetcher and cannot be refreshed; build a new snapshot instead.")
        return InspectSnapshot(
            fetcher=self._fetcher,
            device_items=self._fetcher.get_device_skeleton(),
            edge_items=self._fetcher.get_edge_skeleton(),
        )

    # --- Post-commit hooks (ADR-0010) ---

    def apply_post_commit(
        self,
        removed_ids: Optional[list[str]] = None,
        device_ids: Optional[list[str]] = None,
        pair_ids: Optional[list[str]] = None,
        mark_paths_stale: bool = True,
    ) -> None:
        """Targeted refresh after a successful commit: drop removed entities locally, re-fetch the
        affected devices and edge pairs, and mark the services section stale.

        Never raises: a failed re-fetch marks the entity stale (re-fetched lazily on next access)
        and logs, so a post-commit hook cannot lose the caller's already-successful commit result.
        """
        self._apply_removals(removed_ids or [])
        if self._fetcher is not None:
            for device_id in device_ids or []:
                if device_id in self._devices_by_id:
                    self._try_refresh_device(device_id)
            for pair_id in pair_ids or []:
                self._try_refresh_edge_pair(pair_id)
        if mark_paths_stale:
            self._mark_paths_stale()
            self._mark_alarms_stale()

    def apply_network_refresh(self, device_ids: list[str]) -> None:
        """Targeted refresh after a network action (addDevices / syncDevices): upsert the named
        devices (new or restructured) and reconcile the edge pairs touching them, then mark the
        services section stale. Never raises (same contract as :meth:`apply_post_commit`).

        Unlike a commit, a network action does not report the exact touched entities and can create
        pairs to previously-unconnected devices, so edges are reconciled from one cheap edge-skeleton
        read scoped to pairs touching an affected device (per-device detail stays targeted)."""
        if self._fetcher is None or not device_ids:
            return
        affected = set(device_ids)
        for device_id in device_ids:
            self._try_refresh_device(device_id)
        self._reconcile_pairs_for_devices(affected)
        self._mark_paths_stale()
        self._mark_alarms_stale()

    def upsert_devices_from_skeleton(self, device_ids: list[str]) -> None:
        """Insert or refresh named devices from one device-skeleton read.

        Used after creating virtual devices: per-device detail fetches often miss brand-new
        ``virtual.N`` nodes (detail-less / dash-vs-dot id form), while the skeleton indexes them
        under the public ``deviceId`` (``virtual.N``) that ``addedDeviceLabels`` returns.
        Never raises (same contract as :meth:`apply_network_refresh`).
        """
        if self._fetcher is None or not device_ids:
            return
        wanted = set(device_ids)
        try:
            nodes = self._fetcher.get_device_skeleton()
        except Exception as exc:
            for device_id in device_ids:
                self._stale_devices.add(device_id)
            _logger.warning(
                "Inspect snapshot: skeleton upsert for %s failed: %s",
                sorted(wanted),
                exc,
            )
            return
        with self._lock:
            for node in nodes:
                device_id = node.deviceId or node.id
                if device_id not in wanted:
                    continue
                self._index_device(node, HydrationLevel.SKELETON)
                self._stale_devices.discard(device_id)

    # --- Internal: hydration ---

    def _ensure_device_detail(self, device_id: str) -> None:
        self._reconcile_stale_device(device_id)
        record = self._devices_by_id.get(device_id)
        if record is None or record.level is HydrationLevel.FULL or self._fetcher is None:
            return
        # The collector keys nodeStatus by the item's own id (dash form for virtual devices,
        # e.g. 'virtual-2'), which differs from the public device id ('virtual.2'). Use it here.
        detail = self._fetcher.get_device_detail(record.node.id or device_id)
        if detail is None:
            # No further detail to load (e.g. virtual devices expose no modules); mark hydrated
            # so we honour the at-most-one-fetch contract instead of re-fetching on every access.
            with self._lock:
                current = self._devices_by_id.get(device_id)
                if current is not None and current.level is not HydrationLevel.FULL:
                    current.level = HydrationLevel.FULL
            return
        with self._lock:
            current = self._devices_by_id.get(device_id)
            if current is None or current.level is HydrationLevel.FULL:
                return
            self._upsert_device(device_id, detail)

    def _refresh_device(self, device_id: str) -> None:
        """Re-fetch one device's full detail and upsert it (adds it if newly present). May raise."""
        if self._fetcher is None:
            return
        record = self._devices_by_id.get(device_id)
        detail = self._fetcher.get_device_detail(record.node.id if record else device_id)
        if detail is None:
            # Keep any existing record untouched (e.g. detail-less virtual devices); just clear stale.
            self._stale_devices.discard(device_id)
            return
        with self._lock:
            self._upsert_device(device_id, detail)

    def _refresh_edge_pair(self, pair_id: str) -> None:
        """Re-fetch and re-index one external-edge device pair. May raise."""
        if self._fetcher is None:
            return
        pair = self._fetcher.get_edge_pair(pair_id)
        with self._lock:
            self._drop_edge_pair(pair_id)
            if pair is not None:
                self._index_edge_pair(pair)
            self._stale_pairs.discard(pair_id)

    # --- Internal: resilient refresh + lazy-stale self-heal (ADR-0010) ---

    def _try_refresh_device(self, device_id: str) -> None:
        """Re-fetch a device; on failure mark it stale (lazy self-heal on next access) and log."""
        try:
            self._refresh_device(device_id)
        except Exception as exc:
            self._stale_devices.add(device_id)
            _logger.warning("Inspect snapshot: post-write re-fetch of device '%s' failed: %s", device_id, exc)

    def _try_refresh_edge_pair(self, pair_id: str) -> None:
        """Re-fetch an edge pair; on failure mark it stale (lazy self-heal on next access) and log."""
        try:
            self._refresh_edge_pair(pair_id)
        except Exception as exc:
            self._stale_pairs.add(pair_id)
            _logger.warning("Inspect snapshot: post-write re-fetch of edge pair '%s' failed: %s", pair_id, exc)

    def _reconcile_stale_device(self, device_id: str) -> None:
        if device_id not in self._stale_devices:
            return
        try:
            self._refresh_device(device_id)
            self._stale_devices.discard(device_id)
        except Exception as exc:
            _logger.warning("Inspect snapshot: lazy re-fetch of stale device '%s' failed: %s", device_id, exc)

    def _reconcile_stale_pairs(self) -> None:
        for pair_id in list(self._stale_pairs):
            try:
                self._refresh_edge_pair(pair_id)
            except Exception as exc:
                _logger.warning("Inspect snapshot: lazy re-fetch of stale edge pair '%s' failed: %s", pair_id, exc)

    def _reconcile_pairs_for_devices(self, device_ids: set[str]) -> None:
        """Reconcile every edge pair touching an affected device from one fresh edge-skeleton read."""
        if self._fetcher is None or not device_ids:
            return
        try:
            pairs = self._fetcher.get_edge_skeleton()
        except Exception as exc:
            self._stale_pairs.update(
                indexed.pair_id for d in device_ids for indexed in self._edges_by_device_id.get(d, [])
            )
            _logger.warning("Inspect snapshot: edge reconcile after network action failed: %s", exc)
            return
        with self._lock:
            for pair_id in {indexed.pair_id for d in device_ids for indexed in self._edges_by_device_id.get(d, [])}:
                self._drop_edge_pair(pair_id)
            for pair in pairs:
                if self._pair_touches(pair, device_ids):
                    self._drop_edge_pair(pair.id)
                    self._index_edge_pair(pair)

    def _pair_touches(self, pair: InspectApiExternalEdgesByDeviceKeyItem, device_ids: set[str]) -> bool:
        primary = self._resolve_device_id(pair.primary.devicePid)
        secondary = self._resolve_device_id(pair.secondary.devicePid)
        return primary in device_ids or secondary in device_ids

    def _mark_paths_stale(self) -> None:
        with self._lock:
            self._section_loaded["paths"] = False
            self._paths_by_booking_id.clear()
            self._services_by_device_id.clear()

    def _mark_alarms_stale(self) -> None:
        with self._lock:
            self._section_loaded["alarms"] = False
            self._alarms.clear()
            self._alarms_by_device_id.clear()
            self._alarms_by_resource_key.clear()

    def _upsert_device(self, device_id: str, detail: InspectApiNodeStatusItem) -> None:
        """Insert or replace a device record (FULL), keeping the label index and caches consistent."""
        old = self._devices_by_id.get(device_id)
        old_label = old.label if old is not None else None
        record = _DeviceRecord(device_id=device_id, node=detail, level=HydrationLevel.FULL)
        new_label = record.label
        if old_label and old_label != new_label:
            remaining = [d for d in self._devices_by_label.get(old_label, []) if d != device_id]
            if remaining:
                self._devices_by_label[old_label] = remaining
            else:
                self._devices_by_label.pop(old_label, None)
        self._devices_by_id[device_id] = record
        if new_label:
            ids = self._devices_by_label.setdefault(new_label, [])
            if device_id not in ids:
                ids.append(device_id)
        self._device_cache.pop(device_id, None)
        self._rebuild_device_ports(device_id, detail)
        self._stale_devices.discard(device_id)

    def _ensure_section_paths(self) -> None:
        if self._section_loaded.get("paths") or self._fetcher is None:
            return
        items = self._fetcher.get_paths_section()
        with self._lock:
            if self._section_loaded.get("paths"):
                return
            self._index_paths(items)
            self._section_loaded["paths"] = True
            self._section_fetched_at["paths"] = _now()
            self._service_cache.clear()

    def _ensure_section_alarms(self) -> None:
        if self._section_loaded.get("alarms") or self._fetcher is None:
            return
        items = self._fetcher.get_alarms_section()
        with self._lock:
            if self._section_loaded.get("alarms"):
                return
            self._index_alarms(items)
            self._section_loaded["alarms"] = True
            self._section_fetched_at["alarms"] = _now()

    # --- Internal: indexing ---

    def _index_device(self, node: InspectApiNodeStatusItem, level: HydrationLevel) -> None:
        device_id = node.deviceId or node.id
        if not device_id:
            return
        record = _DeviceRecord(device_id=device_id, node=node, level=level)
        self._devices_by_id[device_id] = record
        label = record.label
        if label:
            ids = self._devices_by_label.setdefault(label, [])
            if device_id not in ids:
                ids.append(device_id)
        if level is HydrationLevel.FULL:
            self._rebuild_device_ports(device_id, node)

    def _rebuild_device_ports(self, device_id: str, node: InspectApiNodeStatusItem) -> None:
        # Drop existing port index entries for this device
        old = self._ports_by_device_id.pop(device_id, [])
        for indexed in old:
            for vertex_id in _vertex_ids_from_status(indexed.port):
                self._vertex_details.pop(vertex_id, None)
            port_id = _port_id_from_status(indexed.port)
            if port_id is not None:
                self._port_by_key.pop((device_id, port_id), None)
                remaining = [p for p in self._ports_by_pid.get(port_id, []) if p.device_id != device_id]
                if remaining:
                    self._ports_by_pid[port_id] = remaining
                else:
                    self._ports_by_pid.pop(port_id, None)
        # Drop the device's module index + wrappers
        for module_id in self._modules_by_device_id.pop(device_id, {}):
            self._module_cache.pop((device_id, module_id), None)
        # Rebuild
        entries: list[_IndexedPort] = []
        modules: dict[str, InspectApiModuleStatus] = {}
        for module in _iter_modules(node.modules):
            module_id = module.pid or module.id
            if module_id is not None:
                modules[module_id] = module
            for port in _iter_ports(module.ports):
                indexed = _IndexedPort(device_id=device_id, module_id=module_id, port=port)
                entries.append(indexed)
                port_id = _port_id_from_status(port)
                if port_id is None:
                    continue
                self._port_by_key[(device_id, port_id)] = indexed
                self._ports_by_pid.setdefault(port_id, []).append(indexed)
        self._ports_by_device_id[device_id] = entries
        self._modules_by_device_id[device_id] = modules

    def _resolve_device_id(self, pid: str | None) -> str | None:
        """Map an edge ``devicePid`` to the canonical device id.

        For physical devices the pid equals the device id. For virtual devices the collector reports
        the pid in dash-encoded form (``virtual-2``) while the device id is dot form (``virtual.2``);
        reconcile the two so edges index under the same key the device is stored under.
        """
        if not pid or pid in self._devices_by_id:
            return pid
        dotted = pid.replace("-", ".")
        return dotted if dotted in self._devices_by_id else pid

    def _index_edge_pair(self, pair_item: InspectApiExternalEdgesByDeviceKeyItem) -> None:
        self._edge_pairs[pair_item.id] = pair_item
        primary_device_id = self._resolve_device_id(pair_item.primary.devicePid)
        secondary_device_id = self._resolve_device_id(pair_item.secondary.devicePid)
        for side, device_id in (
            (pair_item.primary, primary_device_id),
            (pair_item.secondary, secondary_device_id),
        ):
            if not device_id:
                continue
            for edge in side.data.values():
                from_device_id = (
                    self._resolve_device_id(
                        _device_id_from_context(edge.fromStatus.context if edge.fromStatus else None)
                    )
                    or primary_device_id
                )
                from_port_id = _port_id_from_endpoint(edge.fromStatus)
                to_device_id = (
                    self._resolve_device_id(_device_id_from_context(edge.toStatus.context if edge.toStatus else None))
                    or secondary_device_id
                )
                to_port_id = _port_id_from_endpoint(edge.toStatus)
                indexed = _IndexedEdge(
                    edge_id=edge.id,
                    pair_id=pair_item.id,
                    edge=edge,
                    pair_status=pair_item.status,
                    primary_device_id=primary_device_id,
                    secondary_device_id=secondary_device_id,
                    from_device_id=from_device_id,
                    from_port_id=from_port_id,
                    to_device_id=to_device_id,
                    to_port_id=to_port_id,
                )
                self._edges_by_device_id.setdefault(device_id, []).append(indexed)
                for endpoint_device_id, port_id in (
                    (from_device_id, from_port_id),
                    (to_device_id, to_port_id),
                ):
                    if endpoint_device_id and port_id:
                        self._edge_by_port_key[(endpoint_device_id, port_id)] = indexed

    def _drop_edge_pair(self, pair_id: str) -> None:
        self._edge_pairs.pop(pair_id, None)
        for edges in self._edges_by_device_id.values():
            for edge in edges:
                if edge.pair_id == pair_id:
                    self._edge_details.pop(edge.edge_id, None)
        for device_id, edges in list(self._edges_by_device_id.items()):
            kept = [e for e in edges if e.pair_id != pair_id]
            if kept:
                self._edges_by_device_id[device_id] = kept
            else:
                self._edges_by_device_id.pop(device_id, None)
        for key, indexed in list(self._edge_by_port_key.items()):
            if indexed.pair_id == pair_id:
                self._edge_by_port_key.pop(key, None)
        for edge_id, edge in list(self._edge_cache.items()):
            if edge.pair_id == pair_id:
                self._edge_cache.pop(edge_id, None)

    def _index_paths(self, path_items: list[InspectApiPathItem]) -> None:
        for item in path_items:
            booking_id = item.serviceFields.bid
            self._paths_by_booking_id[booking_id] = item
            device_ids: set[str] = set()
            for segment in item.path:
                structure = segment.structure
                if structure and structure.deviceId:
                    device_ids.add(structure.deviceId)
            for device_id in device_ids:
                ids = self._services_by_device_id.setdefault(device_id, [])
                if booking_id not in ids:
                    ids.append(booking_id)

    def _index_alarms(self, alarm_items: list[InspectApiAlarmItem]) -> None:
        self._alarms = list(alarm_items)
        self._alarms_by_device_id.clear()
        self._alarms_by_resource_key.clear()
        for item in alarm_items:
            point_id = list(item.id.pointId) if item.id is not None else []
            if not point_id:
                continue
            device_id = point_id[0]
            self._alarms_by_device_id.setdefault(device_id, []).append(item)
            resource_key = ".".join(point_id)
            self._alarms_by_resource_key.setdefault(resource_key, []).append(item)
            # Edge pair / directed edge keys appear as a single pointId element containing "::".
            for part in point_id:
                if "::" in part:
                    self._alarms_by_resource_key.setdefault(part, []).append(item)

    def _apply_removals(self, removed_ids: list[str]) -> None:
        if not removed_ids:
            return
        with self._lock:
            for removed in removed_ids:
                # Device removal
                record = self._devices_by_id.pop(removed, None)
                if record is not None:
                    label = record.label
                    if label and label in self._devices_by_label:
                        self._devices_by_label[label] = [d for d in self._devices_by_label[label] if d != removed]
                        if not self._devices_by_label[label]:
                            self._devices_by_label.pop(label, None)
                    self._device_cache.pop(removed, None)
                    for indexed in self._ports_by_device_id.pop(removed, []):
                        for vertex_id in _vertex_ids_from_status(indexed.port):
                            self._vertex_details.pop(vertex_id, None)
                    for module_id in self._modules_by_device_id.pop(removed, {}):
                        self._module_cache.pop((removed, module_id), None)
                    self._edges_by_device_id.pop(removed, None)
                # Edge removal by edge id or pair id
                if "::" in removed:
                    self._drop_edge_id(removed)

    def _drop_edge_id(self, edge_or_pair_id: str) -> None:
        for device_id, edges in list(self._edges_by_device_id.items()):
            kept = [e for e in edges if e.edge_id != edge_or_pair_id and e.pair_id != edge_or_pair_id]
            if kept != edges:
                if kept:
                    self._edges_by_device_id[device_id] = kept
                else:
                    self._edges_by_device_id.pop(device_id, None)
        for key, indexed in list(self._edge_by_port_key.items()):
            if indexed.edge_id == edge_or_pair_id or indexed.pair_id == edge_or_pair_id:
                self._edge_by_port_key.pop(key, None)
        self._edge_cache.pop(edge_or_pair_id, None)
        self._edge_details.pop(edge_or_pair_id, None)

    # --- Internal: domain wrappers (cached) ---

    def _wrap_device(self, device_id: str) -> "InspectDevice":
        from videoipath_automation_tool.apps.inspect.domain.device import InspectDevice

        cached = self._device_cache.get(device_id)
        if cached is not None:
            return cached
        device = InspectDevice(snapshot=self, id=device_id)
        self._device_cache[device_id] = device
        return device

    def _wrap_module(self, device_id: str, module_id: str) -> "InspectModule":
        from videoipath_automation_tool.apps.inspect.domain.module import InspectModule

        cached = self._module_cache.get((device_id, module_id))
        if cached is not None:
            return cached
        module = InspectModule(snapshot=self, device_id=device_id, module_id=module_id)
        self._module_cache[(device_id, module_id)] = module
        return module

    def _wrap_port(self, indexed: _IndexedPort) -> "InspectPort":
        from videoipath_automation_tool.apps.inspect.domain.port import InspectPort

        return InspectPort(snapshot=self, indexed=indexed)

    def _wrap_edge(self, indexed: _IndexedEdge) -> "InspectEdge":
        from videoipath_automation_tool.apps.inspect.domain.edge import InspectEdge

        cached = self._edge_cache.get(indexed.edge_id)
        if cached is not None:
            return cached
        edge = InspectEdge(snapshot=self, indexed=indexed)
        self._edge_cache[indexed.edge_id] = edge
        return edge

    def _wrap_service(self, path_item: InspectApiPathItem) -> "InspectService":
        from videoipath_automation_tool.apps.inspect.domain.service import InspectService

        booking_id = path_item.serviceFields.bid
        cached = self._service_cache.get(booking_id)
        if cached is not None:
            return cached
        service = InspectService(snapshot=self, path_item=path_item)
        self._service_cache[booking_id] = service
        return service


# --- Internal ---

_PRELOAD_WORKERS = 8

_logger = logging.getLogger("videoipath_automation_tool_inspect_snapshot")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _severity_rank(value: Any) -> int:
    """Sort key: higher severity first; unknown / missing treated as lowest."""
    if isinstance(value, InspectSeverity):
        return int(value)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return -1


def _sorted_alarms(items: list[InspectApiAlarmItem]) -> list["InspectAlarm"]:
    from videoipath_automation_tool.apps.inspect.domain.alarm import InspectAlarm

    ordered = sorted(
        items,
        key=lambda item: _severity_rank(item.info.severity if item.info is not None else None),
        reverse=True,
    )
    return [InspectAlarm(item=item) for item in ordered]


class _DeviceRecord(InspectInternalModel):
    device_id: str
    node: InspectApiNodeStatusItem
    level: HydrationLevel
    fetched_at: datetime = Field(default_factory=_now)

    @property
    def label(self) -> str | None:
        return self.node.effective_label

    @property
    def pid(self) -> str | None:
        return self.node.pid or self.node.deviceId

    def __repr__(self) -> str:
        return format_repr(self, device_id=self.device_id, level=self.level)

    __str__ = __repr__


class _IndexedPort(InspectFrozenModel):
    device_id: str
    module_id: str | None
    port: InspectPortStatus

    def __repr__(self) -> str:
        return format_repr(
            self,
            device_id=self.device_id,
            module_id=self.module_id,
            port_id=_port_id_from_status(self.port),
        )

    __str__ = __repr__


class _IndexedEdge(InspectFrozenModel):
    edge_id: str
    pair_id: str
    edge: InspectApiExternalEdgeStatus
    pair_status: InspectApiExternalEdgeLiveStatus | None
    primary_device_id: str | None
    secondary_device_id: str | None
    from_device_id: str | None
    from_port_id: str | None
    to_device_id: str | None
    to_port_id: str | None

    def __repr__(self) -> str:
        return format_repr(
            self,
            edge_id=self.edge_id,
            from_device_id=self.from_device_id,
            to_device_id=self.to_device_id,
        )

    __str__ = __repr__


# --- Module-level helpers (kept stable for the domain layer) ---


def _device_id_from_context(context: Any) -> str | None:
    if context is None:
        return None
    device_pid = getattr(context, "devicePid", None)
    if device_pid:
        return device_pid
    if isinstance(context, dict):
        value = context.get("devicePid")
        return value if isinstance(value, str) else None
    return None


def _port_id_from_endpoint(endpoint: Any) -> str | None:
    if endpoint is None:
        return None
    pid = getattr(endpoint, "pid", None)
    if isinstance(pid, str) and pid:
        return pid
    context = getattr(endpoint, "context", None)
    if context is not None:
        if isinstance(context, dict):
            port_pid = context.get("portPid")
        else:
            port_pid = getattr(context, "portPid", None)
        if isinstance(port_pid, str) and port_pid:
            return port_pid
    return None


def _port_id_from_status(port: InspectPortStatus) -> str | None:
    port_id = port.pid or port.id
    return port_id if port_id else None


def _vertex_ids_from_status(port: InspectPortStatus) -> tuple[str, ...]:
    """All vertex ids carried by a port's ``vertexInfo`` (one for single, out+in for double)."""
    info = port.parsed_vertex_info
    if info is None:
        return ()
    if isinstance(info, InspectApiSingleVertexInfo):
        return (info.id,) if info.id else ()
    return tuple(side.id for side in (info.out, info.in_) if side is not None and side.id)


def _iter_modules(
    modules: dict[str, InspectApiModuleStatus] | list[InspectApiModuleStatus] | None,
) -> Iterator[InspectApiModuleStatus]:
    if not modules:
        return
    if isinstance(modules, dict):
        yield from modules.values()
        return
    yield from modules


def _iter_ports(
    ports: dict[str, InspectPortStatus] | list[InspectPortStatus] | None,
) -> Iterator[InspectPortStatus]:
    if not ports:
        return
    if isinstance(ports, dict):
        yield from ports.values()
        return
    yield from ports


__all__ = ["InspectSnapshot", "HydrationLevel", "_STAGED_MISSING"]
