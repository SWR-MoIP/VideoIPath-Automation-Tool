from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from videoipath_automation_tool.apps.inspect.model.collector import InspectApiExternalEdgeLiveStatus
from videoipath_automation_tool.apps.inspect.snapshot import _IndexedEdge

if TYPE_CHECKING:
    from videoipath_automation_tool.apps.inspect.domain.device import InspectDevice
    from videoipath_automation_tool.apps.inspect.domain.port import InspectPort
    from videoipath_automation_tool.apps.inspect.domain.service import InspectService
    from videoipath_automation_tool.apps.inspect.snapshot import InspectSnapshot


@dataclass(frozen=True, slots=True)
class InspectEdge:
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
        return self.indexed.edge.status

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
