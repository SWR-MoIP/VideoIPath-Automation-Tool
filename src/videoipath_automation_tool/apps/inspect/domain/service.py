from __future__ import annotations

from typing import TYPE_CHECKING

from videoipath_automation_tool.apps.inspect.model.collector import InspectApiPathItem, InspectServiceStatus
from videoipath_automation_tool.apps.inspect.model.common import InspectFrozenModel, format_repr
from videoipath_automation_tool.apps.inspect.snapshot import InspectSnapshot, _path_is_main, _port_id_from_endpoint

if TYPE_CHECKING:
    from videoipath_automation_tool.apps.inspect.domain.alarm import InspectAlarm
    from videoipath_automation_tool.apps.inspect.domain.device import InspectDevice
    from videoipath_automation_tool.apps.inspect.domain.port import InspectPort


class InspectService(InspectFrozenModel):
    """One booking. A redundant booking keeps its main and spare path; the accessors without a
    path qualifier (``path_devices``, ``status``, ``source_port``, …) read the main path, or the
    spare path when the booking has no main item."""

    snapshot: InspectSnapshot
    main_item: InspectApiPathItem | None = None
    spare_item: InspectApiPathItem | None = None

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
        return self._primary_path.source_port

    @property
    def destination_port(self) -> InspectPort | None:
        return self._primary_path.destination_port

    @property
    def source_device(self) -> InspectDevice | None:
        return self._primary_path.source_device

    @property
    def destination_device(self) -> InspectDevice | None:
        return self._primary_path.destination_device

    @property
    def is_main(self) -> bool:
        """Whether :attr:`path_item` is the main path. ``True`` for a redundant booking."""
        return _path_is_main(self.path_item)

    @property
    def is_redundant(self) -> bool:
        """True when the booking has both a main and a spare path."""
        return self.main_item is not None and self.spare_item is not None

    @property
    def status(self) -> InspectServiceStatus | None:
        return self.path_item.serviceFields.serviceStatus

    @property
    def alarms(self) -> list[InspectAlarm]:
        """Active service alarms of this booking (worst severity first): the alarms whose
        ``pointId`` is ``["book", <booking id>]`` (GUI: Events → Current, category Service).
        Configuration alarms that merely reference the booking are not included."""
        return self.snapshot.get_alarms_for_service(self.booking_id)

    @property
    def path_item(self) -> InspectApiPathItem:
        """The main path item, or the spare item when the booking has no main path."""
        item = self.main_item if self.main_item is not None else self.spare_item
        if item is None:
            raise ValueError("Service has no path item.")
        return item

    @property
    def spare_path_item(self) -> InspectApiPathItem | None:
        """The spare path item of a redundant booking; ``None`` otherwise."""
        return self.spare_item

    @property
    def main_path(self) -> InspectServicePath | None:
        """The main path, or ``None`` when the booking only has a spare item."""
        if self.main_item is None:
            return None
        return InspectServicePath(snapshot=self.snapshot, path_item=self.main_item)

    @property
    def spare_path(self) -> InspectServicePath | None:
        """The spare path of a redundant booking; ``None`` when there is no spare item."""
        if self.spare_item is None:
            return None
        return InspectServicePath(snapshot=self.snapshot, path_item=self.spare_item)

    @property
    def path_devices(self) -> list[InspectDevice]:
        return self._primary_path.devices

    @property
    def path_ports(self) -> list[InspectPort]:
        return self._primary_path.ports

    def __repr__(self) -> str:
        return format_repr(self, booking_id=self.booking_id, label=self.label, redundant=self.is_redundant)

    __str__ = __repr__

    @property
    def _primary_path(self) -> InspectServicePath:
        return InspectServicePath(snapshot=self.snapshot, path_item=self.path_item)


class InspectServicePath(InspectFrozenModel):
    """One directed path of a booking (main or spare): its hops, endpoints and status."""

    snapshot: InspectSnapshot
    path_item: InspectApiPathItem

    @property
    def is_main(self) -> bool:
        return _path_is_main(self.path_item)

    @property
    def status(self) -> InspectServiceStatus | None:
        return self.path_item.serviceFields.serviceStatus

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
        devices = self.devices
        return devices[0] if devices else None

    @property
    def destination_device(self) -> InspectDevice | None:
        port = self.destination_port
        if port is not None:
            return port.device
        devices = self.devices
        return devices[-1] if devices else None

    @property
    def devices(self) -> list[InspectDevice]:
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
    def ports(self) -> list[InspectPort]:
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

    def __repr__(self) -> str:
        return format_repr(self, booking_id=self.path_item.serviceFields.bid, is_main=self.is_main)

    __str__ = __repr__

    def _resolve_endpoint_port(self, port_id: str | None) -> InspectPort | None:
        if not port_id:
            return None
        for device in self.devices:
            port = self.snapshot.get_port(device.id, port_id)
            if port is not None:
                return port
        return self.snapshot.find_port_by_id(port_id)
