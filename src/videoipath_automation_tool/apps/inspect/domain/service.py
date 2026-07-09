from __future__ import annotations

from typing import TYPE_CHECKING

from videoipath_automation_tool.apps.inspect.model.collector import InspectApiPathItem, InspectServiceStatus
from videoipath_automation_tool.apps.inspect.model.common import InspectFrozenModel
from videoipath_automation_tool.apps.inspect.snapshot import InspectSnapshot, _port_id_from_endpoint

if TYPE_CHECKING:
    from videoipath_automation_tool.apps.inspect.domain.device import InspectDevice
    from videoipath_automation_tool.apps.inspect.domain.port import InspectPort


class InspectService(InspectFrozenModel):
    snapshot: InspectSnapshot
    path_item: InspectApiPathItem

    @property
    def booking_id(self) -> str:
        return self.path_item.serviceFields.bid

    @property
    def label(self) -> str | None:
        generic = self.path_item.serviceFields.generic
        if generic is not None and generic.descriptor is not None:
            return generic.descriptor.label or None
        return self.path_item.serviceFields.fromLabel or self.path_item.serviceFields.toLabel

    @property
    def source(self) -> str | None:
        return self.path_item.serviceFields.fromLabel

    @property
    def destination(self) -> str | None:
        return self.path_item.serviceFields.toLabel

    @property
    def source_port(self) -> InspectPort | None:
        return self._resolve_endpoint_port(self.path_item.serviceFields.fromPid)

    @property
    def destination_port(self) -> InspectPort | None:
        return self._resolve_endpoint_port(self.path_item.serviceFields.toPid)

    @property
    def source_device(self) -> InspectDevice | None:
        port = self.source_port
        if port is not None:
            return port.device
        devices = self.path_devices
        return devices[0] if devices else None

    @property
    def destination_device(self) -> InspectDevice | None:
        port = self.destination_port
        if port is not None:
            return port.device
        devices = self.path_devices
        return devices[-1] if devices else None

    @property
    def is_main(self) -> bool | None:
        return self.path_item.serviceFields.isMain

    @property
    def status(self) -> InspectServiceStatus | None:
        return self.path_item.serviceFields.serviceStatus

    @property
    def path_devices(self) -> list[InspectDevice]:
        devices: list[InspectDevice] = []
        seen: set[str] = set()
        for segment in self.path_item.path:
            structure = segment.structure
            if structure is None or not structure.deviceId or structure.deviceId in seen:
                continue
            device = self.snapshot.get_device_by_id(structure.deviceId)
            if device is not None:
                devices.append(device)
                seen.add(structure.deviceId)
        return devices

    @property
    def path_ports(self) -> list[InspectPort]:
        ports: list[InspectPort] = []
        seen: set[tuple[str, str]] = set()
        for segment in self.path_item.path:
            structure = segment.structure
            if structure is None or not structure.deviceId:
                continue
            for endpoint in (structure.inputStatus, structure.outputStatus):
                port_id = _port_id_from_endpoint(endpoint)
                if not port_id:
                    continue
                key = (structure.deviceId, port_id)
                if key in seen:
                    continue
                port = self.snapshot.get_port(structure.deviceId, port_id)
                if port is not None:
                    ports.append(port)
                    seen.add(key)
        return ports

    def _resolve_endpoint_port(self, port_id: str | None) -> InspectPort | None:
        if not port_id:
            return None
        for device in self.path_devices:
            port = self.snapshot.get_port(device.id, port_id)
            if port is not None:
                return port
        return self.snapshot.find_port_by_id(port_id)
