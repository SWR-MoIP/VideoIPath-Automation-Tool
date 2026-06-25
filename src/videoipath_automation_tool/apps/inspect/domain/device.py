from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from videoipath_automation_tool.apps.inspect.model.common import InspectApiStatusSummary
from videoipath_automation_tool.apps.inspect.snapshot import _DeviceRecord

if TYPE_CHECKING:
    from videoipath_automation_tool.apps.inspect.domain.edge import InspectEdge
    from videoipath_automation_tool.apps.inspect.domain.port import InspectPort
    from videoipath_automation_tool.apps.inspect.domain.service import InspectService
    from videoipath_automation_tool.apps.inspect.snapshot import InspectSnapshot


@dataclass(frozen=True, slots=True)
class InspectDevice:
    snapshot: InspectSnapshot
    record: _DeviceRecord

    @property
    def id(self) -> str:
        return self.record.device_id

    @property
    def label(self) -> str | None:
        return self.record.label

    @property
    def pid(self) -> str | None:
        return self.record.pid

    @property
    def status(self) -> InspectApiStatusSummary | None:
        if self.record.node is None:
            return None
        return self.record.node.status

    @property
    def sync_severity(self) -> int | str | None:
        if self.record.node is None:
            return None
        return self.record.node.syncSeverity

    @property
    def tags(self) -> tuple[str, ...]:
        if self.record.node is None:
            return ()
        return tuple(self.record.node.tags)

    @property
    def coordinates(self) -> dict[str, float | int | str | None] | None:
        if self.record.node is None or self.record.node.meta is None:
            return None
        return self.record.node.meta.coordinates

    @property
    def ports(self) -> list[InspectPort]:
        return self.snapshot.get_ports_for_device(self.id)

    @property
    def edges(self) -> list[InspectEdge]:
        return self.snapshot.get_edges_for_device(self.id)

    @property
    def services(self) -> list[InspectService]:
        return self.snapshot.get_services_for_device(self.id)

    @property
    def linked_devices(self) -> list[InspectDevice]:
        return self.snapshot.get_linked_devices(self.id)
