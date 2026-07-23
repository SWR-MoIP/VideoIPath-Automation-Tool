from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from videoipath_automation_tool.apps.inspect.model.collector import InspectApiExternalEdgeLiveStatus
from videoipath_automation_tool.apps.inspect.model.common import (
    CONFLICT_PRIORITY_BY_INT,
    CONFLICT_PRIORITY_TO_INT,
    InspectConfigPriority,
    InspectEditableModel,
    InspectRedundancyMode,
)
from videoipath_automation_tool.apps.inspect.snapshot import InspectSnapshot, _IndexedEdge

if TYPE_CHECKING:
    from videoipath_automation_tool.apps.inspect.domain.alarm import InspectAlarm
    from videoipath_automation_tool.apps.inspect.domain.device import InspectDevice
    from videoipath_automation_tool.apps.inspect.domain.port import InspectPort
    from videoipath_automation_tool.apps.inspect.domain.service import InspectService
    from videoipath_automation_tool.apps.inspect.model.actions import InspectApiEdgeForm


class InspectEdge(InspectEditableModel):
    """A directed external edge. Live status fields come from the collector skeleton; Edit Edge
    dialog fields resolve from the lazily-fetched edit form, with pending setter edits taking
    precedence (read-your-writes). Flush with ``app.inspect.update(edge)`` or ``tx.update(edge)``
    inside a transaction."""

    snapshot: InspectSnapshot
    indexed: _IndexedEdge

    @property
    def _edit_kind(self) -> Literal["edge"]:
        return "edge"

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
        """Live bandwidth status. For the configured capacity use :attr:`bandwidth_capacity`."""
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
    def alarms(self) -> list[InspectAlarm]:
        """Active alarms correlated to this edge or its pair (worst severity first)."""
        return self.snapshot.get_alarms_for_edge(self.id, pair_id=self.pair_id)

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
        return self._staged_or(
            "descriptor.label",
            lambda: f.descriptor.label if (f := self._edit_form()) else None,
        )

    @label.setter
    def label(self, value: str) -> None:
        self._stage("descriptor.label", value)

    @property
    def description(self) -> str | None:
        """Edge description ("Description" in the Edit Edge dialog)."""
        return self._staged_or(
            "descriptor.desc",
            lambda: f.descriptor.desc if (f := self._edit_form()) else None,
        )

    @description.setter
    def description(self, value: str) -> None:
        self._stage("descriptor.desc", value)

    @property
    def tags(self) -> list[str]:
        return self._staged_or("tags", lambda: list(self._form_get("tags") or []), adapt=list)

    @tags.setter
    def tags(self, value: list[str]) -> None:
        self._stage("tags", list(value))

    @property
    def active(self) -> bool | None:
        return self._staged_or("active", lambda: self._form_get("active"))

    @active.setter
    def active(self, value: bool) -> None:
        self._stage("active", value)

    @property
    def include_formats(self) -> list[str]:
        return self._staged_or(
            "includeFormats",
            lambda: list(self._form_get("includeFormats") or []),
            adapt=list,
        )

    @include_formats.setter
    def include_formats(self, value: list[str]) -> None:
        self._stage("includeFormats", list(value))

    @property
    def exclude_formats(self) -> list[str]:
        return self._staged_or(
            "excludeFormats",
            lambda: list(self._form_get("excludeFormats") or []),
            adapt=list,
        )

    @exclude_formats.setter
    def exclude_formats(self, value: list[str]) -> None:
        self._stage("excludeFormats", list(value))

    @property
    def conflict_priority(self) -> InspectConfigPriority | int | str | None:
        """Conflict priority ("Conflict priority" in the UI): ``"off"`` / ``"high"`` / ``"normal"`` /
        ``"low"`` (mapped from the on-wire int), or the raw value if unrecognized."""
        return self._staged_or(
            "conflictPri",
            lambda: self._map_conflict_priority(self._form_get("conflictPri")),
            adapt=self._map_conflict_priority,
        )

    @conflict_priority.setter
    def conflict_priority(self, value: InspectConfigPriority | int | str) -> None:
        wire = CONFLICT_PRIORITY_TO_INT.get(value, value) if isinstance(value, str) else value
        self._stage("conflictPri", wire)

    @property
    def redundancy_mode(self) -> InspectRedundancyMode | str | None:
        return self._staged_or("redundancyMode", lambda: self._form_get("redundancyMode"))

    @redundancy_mode.setter
    def redundancy_mode(self, value: InspectRedundancyMode | str) -> None:
        self._stage("redundancyMode", value)

    @property
    def fixed_weight(self) -> int | None:
        """Fixed routing weight/cost ("Fixed weight" in the UI)."""
        return self._staged_or("weight", lambda: self._form_get("weight"))

    @fixed_weight.setter
    def fixed_weight(self, value: int) -> None:
        self._stage("weight", value)

    @property
    def weight(self) -> int | None:
        return self.fixed_weight

    @weight.setter
    def weight(self, value: int) -> None:
        self.fixed_weight = value

    @property
    def bandwidth_capacity(self) -> float | int | None:
        """Configured max bandwidth in Mbit/s ("Bandwidth capacity" in the UI); ``-1.0`` = disabled.
        Distinct from the live status bandwidth when no edit is staged."""
        return self._staged_or("bandwidth", lambda: self._form_get("bandwidth"))

    @bandwidth_capacity.setter
    def bandwidth_capacity(self, value: float | int) -> None:
        self._stage("bandwidth", value)

    @property
    def services_capacity(self) -> int | None:
        """Max number of simultaneous services ("Services capacity" in the UI); ``65535`` = unlimited."""
        return self._staged_or("capacity", lambda: self._form_get("capacity"))

    @services_capacity.setter
    def services_capacity(self, value: int) -> None:
        self._stage("capacity", value)

    @property
    def capacity(self) -> int | None:
        return self.services_capacity

    @capacity.setter
    def capacity(self, value: int) -> None:
        self.services_capacity = value

    @property
    def bandwidth_weight_factor(self) -> int | None:
        """Bandwidth-based weight factor ("Bandwidth weight factor" in the UI)."""
        return self._staged_or(
            "weightFactors.bandwidth.weight",
            lambda: self._weight_factor("bandwidth"),
        )

    @bandwidth_weight_factor.setter
    def bandwidth_weight_factor(self, value: int) -> None:
        self._stage("weightFactors.bandwidth.weight", value)

    @property
    def weight_per_service(self) -> int | None:
        """Service-based weight factor ("Weight per service" in the UI)."""
        return self._staged_or(
            "weightFactors.service.weight",
            lambda: self._weight_factor("service"),
        )

    @weight_per_service.setter
    def weight_per_service(self, value: int) -> None:
        self._stage("weightFactors.service.weight", value)

    def _edit_form(self) -> InspectApiEdgeForm | None:
        return self.snapshot.get_edge_details(self.id)

    def _form_get(self, attr: str, default: Any = None) -> Any:
        form = self._edit_form()
        return getattr(form, attr, default) if form is not None else default

    def _weight_factor(self, key: str) -> int | None:
        form = self._edit_form()
        if form is None:
            return None
        return (form.weightFactors.get(key) or {}).get("weight")

    @staticmethod
    def _map_conflict_priority(raw: Any) -> InspectConfigPriority | int | str | None:
        if raw is None:
            return None
        return CONFLICT_PRIORITY_BY_INT.get(raw, raw) if isinstance(raw, int) else raw


__all__ = ["InspectEdge"]
