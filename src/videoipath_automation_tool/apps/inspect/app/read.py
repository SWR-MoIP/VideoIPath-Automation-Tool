"""Read-side user methods for the Inspect app.

The Inspect app owns a single internal :class:`InspectSnapshot`; users never handle it
directly. It is built lazily on the first read and reused (skeleton-first, then hydrated on demand).
Writes update it in place; :meth:`refresh` rebuilds it from the server.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import TYPE_CHECKING, Literal, Protocol

from videoipath_automation_tool.apps.inspect.api import InspectAPI
from videoipath_automation_tool.apps.inspect.errors import InspectPendingEditsError
from videoipath_automation_tool.apps.inspect.snapshot import InspectSnapshot

if TYPE_CHECKING:
    from videoipath_automation_tool.apps.inspect.domain.device import InspectDevice
    from videoipath_automation_tool.apps.inspect.domain.edge import InspectEdge
    from videoipath_automation_tool.apps.inspect.domain.service import InspectService

LoadMode = Literal["skeleton", "full"]


class _HasInspectState(Protocol):
    _inspect_api: InspectAPI
    _logger: logging.Logger
    _snapshot: InspectSnapshot | None
    _load_mode: LoadMode


class InspectReadMixin:
    _inspect_api: InspectAPI
    _logger: logging.Logger
    _snapshot: InspectSnapshot | None
    _load_mode: LoadMode

    def refresh(self: _HasInspectState, load: LoadMode | None = None, *, discard_pending: bool = False) -> None:
        """Reload the topology from the server, discarding the current internal view.

        Objects already fetched keep reading the previous snapshot. Writes on those objects
        raise ``InspectSnapshotReplacedError``; re-fetch them from the app. Pending edits block
        the reload unless ``discard_pending`` is true.

        Args:
            load: ``"skeleton"`` (fast; lazy detail) or ``"full"`` (eager, point-in-time). Defaults
                to the mode the app was last using.
            discard_pending: Drop staged edits instead of refusing the reload.
        """
        current = self._snapshot
        if current is not None and not discard_pending:
            keys = current.pending_edit_keys()
            if keys:
                raise InspectPendingEditsError(keys)
        mode = load if load is not None else self._load_mode
        loaded = self._load_snapshot(mode)
        if current is not None:
            current.mark_replaced(discard_pending=discard_pending)
        self._snapshot = loaded
        self._load_mode = mode

    # --- Devices ---

    @property
    def devices(self: _HasInspectState) -> list[InspectDevice]:
        """All devices in the topology (skeleton-backed; no per-device detail I/O)."""
        return self._get_snapshot().devices

    def get_device(self: _HasInspectState, device_id: str) -> InspectDevice | None:
        """A device by id, or ``None`` if it is not in the topology."""
        return self._get_snapshot().get_device(device_id)

    # Backwards-compatible alias.
    get_device_by_id = get_device

    def find_device_by_label(self: _HasInspectState, label: str) -> InspectDevice | None:
        """The first device whose (effective) label matches exactly, or ``None``."""
        return self._get_snapshot().find_device_by_label(label)

    def find_devices_by_label(self: _HasInspectState, label: str) -> list[InspectDevice]:
        """All devices whose (effective) label matches exactly."""
        return self._get_snapshot().find_devices_by_label(label)

    def find_device_id_by_label(self: _HasInspectState, label: str) -> str | None:
        """Resolve a device id from its display label."""
        device = self._get_snapshot().find_device_by_label(label)
        return device.id if device is not None else None

    def preload(self: _HasInspectState, devices: list[str] | None = None) -> None:
        """Hydrate device detail for many devices in parallel (avoids N+1 on bulk detail access)."""
        self._get_snapshot().preload(devices)

    def is_device_hydrated(self: _HasInspectState, device_id: str) -> bool:
        """Whether a device's full detail (modules/ports) has been loaded."""
        return self._get_snapshot().is_device_hydrated(device_id)

    def fetched_at(self: _HasInspectState, device_id: str) -> datetime | None:
        """When the given device's current data was fetched (freshness introspection)."""
        return self._get_snapshot().fetched_at(device_id)

    # --- Edges ---

    @property
    def edges(self: _HasInspectState) -> list[InspectEdge]:
        """All external edges (device-pair connectivity)."""
        return self._get_snapshot().edges

    # --- Services ---

    @property
    def services(self: _HasInspectState) -> list[InspectService]:
        """All services/paths (loads the services section on first access)."""
        return self._get_snapshot().services

    def get_service_by_booking_id(self: _HasInspectState, booking_id: str) -> InspectService | None:
        """A service by its booking id, or ``None``."""
        return self._get_snapshot().get_service_by_booking_id(booking_id)

    def get_services_for_device(self: _HasInspectState, device_id: str) -> list[InspectService]:
        """All services whose path traverses the given device."""
        return self._get_snapshot().get_services_for_device(device_id)

    # --- Internal snapshot lifecycle ---

    def _get_snapshot(self: _HasInspectState) -> InspectSnapshot:
        """Return the internal snapshot, building it on first access."""
        if self._snapshot is None:
            self._snapshot = self._load_snapshot(self._load_mode)
        return self._snapshot

    def _load_snapshot(self: _HasInspectState, load: LoadMode) -> InspectSnapshot:
        if load == "full":
            self._logger.debug("Loading full (eager) Inspect snapshot.")
            return InspectSnapshot.from_full_response(self._inspect_api.get_collector_full(), fetcher=self._inspect_api)
        self._logger.debug("Loading skeleton Inspect snapshot (devices + edges in parallel).")
        with ThreadPoolExecutor(max_workers=2) as pool:
            devices_future = pool.submit(self._inspect_api.get_device_skeleton)
            edges_future = pool.submit(self._inspect_api.get_edge_skeleton)
            devices = devices_future.result()
            edges = edges_future.result()
        return InspectSnapshot(fetcher=self._inspect_api, device_items=devices, edge_items=edges)


__all__ = ["InspectReadMixin", "LoadMode"]
