from __future__ import annotations

from typing import TYPE_CHECKING

from videoipath_automation_tool.apps.inspect.model.collector import InspectApiExternalEdgeLiveStatus
from videoipath_automation_tool.apps.inspect.model.common import (
    CONFLICT_PRIORITY_BY_INT,
    InspectConfigPriority,
    InspectFrozenModel,
    InspectRedundancyMode,
)
from videoipath_automation_tool.apps.inspect.snapshot import InspectSnapshot, _IndexedEdge

if TYPE_CHECKING:
    from videoipath_automation_tool.apps.inspect.domain.device import InspectDevice
    from videoipath_automation_tool.apps.inspect.domain.port import InspectPort
    from videoipath_automation_tool.apps.inspect.domain.service import InspectService
    from videoipath_automation_tool.apps.inspect.model.actions import InspectApiEdgeForm


class InspectEdge(InspectFrozenModel):
    snapshot: InspectSnapshot
    indexed: _IndexedEdge

    @property
    def id(self) -> str:
        return self.indexed.edge_id

    @property
    def pair_id(self) -> str:
        return self.indexed.pair_id

    @property
    def from_device(self) -> InspectDevice | None:
        if self.indexed.from_device_id is None:
            return None
        return self.snapshot.get_device_by_id(self.indexed.from_device_id)

    @property
    def from_port(self) -> InspectPort | None:
        if self.indexed.from_device_id is None or self.indexed.from_port_id is None:
            return None
        return self.snapshot.get_port(self.indexed.from_device_id, self.indexed.from_port_id)

    @property
    def to_device(self) -> InspectDevice | None:
        if self.indexed.to_device_id is None:
            return None
        return self.snapshot.get_device_by_id(self.indexed.to_device_id)

    @property
    def to_port(self) -> InspectPort | None:
        if self.indexed.to_device_id is None or self.indexed.to_port_id is None:
            return None
        return self.snapshot.get_port(self.indexed.to_device_id, self.indexed.to_port_id)

    @property
    def bandwidth(self) -> float | int | None:
        return self.indexed.edge.bandwidth

    @property
    def max_bandwidth(self) -> float | int | None:
        return self.indexed.edge.maxBandwidth

    @property
    def status(self) -> InspectApiExternalEdgeLiveStatus | None:
        """Live status for this edge. In the lean skeleton only the pair-level status is present;
        the per-edge status (per direction) appears in the full edge shape."""
        return self.indexed.edge.status or self.indexed.pair_status

    @property
    def services(self) -> list[InspectService]:
        services: list[InspectService] = []
        seen_booking_ids: set[str] = set()
        for device in (self.from_device, self.to_device):
            if device is None:
                continue
            for service in self.snapshot.get_services_for_device(device.id):
                if service.booking_id in seen_booking_ids:
                    continue
                seen_booking_ids.add(service.booking_id)
                services.append(service)
        return services

    # --- Config (the "Edit Edge" dialog fields; lazily fetched via lookupInspectEdgesByIds) ---

    @property
    def label(self) -> str | None:
        """Manual edge label ("Label" in the Edit Edge dialog)."""
        form = self._edit_form()
        return form.descriptor.label if form else None

    @property
    def description(self) -> str | None:
        """Edge description ("Description" in the Edit Edge dialog)."""
        form = self._edit_form()
        return form.descriptor.desc if form else None

    @property
    def tags(self) -> list[str]:
        form = self._edit_form()
        return list(form.tags) if form else []

    @property
    def active(self) -> bool | None:
        form = self._edit_form()
        return form.active if form else None

    @property
    def include_formats(self) -> list[str]:
        form = self._edit_form()
        return list(form.includeFormats) if form else []

    @property
    def exclude_formats(self) -> list[str]:
        form = self._edit_form()
        return list(form.excludeFormats) if form else []

    @property
    def conflict_priority(self) -> InspectConfigPriority | int | str | None:
        """Conflict priority ("Conflict priority" in the UI): ``"off"`` / ``"high"`` / ``"normal"`` /
        ``"low"`` (mapped from the on-wire int), or the raw value if unrecognized."""
        form = self._edit_form()
        if form is None:
            return None
        raw = form.conflictPri
        return CONFLICT_PRIORITY_BY_INT.get(raw, raw) if isinstance(raw, int) else raw

    @property
    def redundancy_mode(self) -> InspectRedundancyMode | str | None:
        form = self._edit_form()
        return form.redundancyMode if form else None

    @property
    def fixed_weight(self) -> int | None:
        """Fixed routing weight/cost ("Fixed weight" in the UI)."""
        form = self._edit_form()
        return form.weight if form else None

    @property
    def bandwidth_capacity(self) -> float | int | None:
        """Configured max bandwidth in Mbit/s ("Bandwidth capacity" in the UI); ``-1.0`` = disabled.
        Distinct from :attr:`bandwidth`, which is the live status value."""
        form = self._edit_form()
        return form.bandwidth if form else None

    @property
    def services_capacity(self) -> int | None:
        """Max number of simultaneous services ("Services capacity" in the UI); ``65535`` = unlimited."""
        form = self._edit_form()
        return form.capacity if form else None

    @property
    def bandwidth_weight_factor(self) -> int | None:
        """Bandwidth-based weight factor ("Bandwidth weight factor" in the UI)."""
        form = self._edit_form()
        if form is None:
            return None
        return (form.weightFactors.get("bandwidth") or {}).get("weight")

    @property
    def weight_per_service(self) -> int | None:
        """Service-based weight factor ("Weight per service" in the UI)."""
        form = self._edit_form()
        if form is None:
            return None
        return (form.weightFactors.get("service") or {}).get("weight")

    def _edit_form(self) -> InspectApiEdgeForm | None:
        return self.snapshot.get_edge_details(self.id)
