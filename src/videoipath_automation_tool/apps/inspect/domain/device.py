from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from videoipath_automation_tool.apps.inspect.model.common import InspectApiStatusSummary, InspectFrozenModel
from videoipath_automation_tool.apps.inspect.snapshot import InspectSnapshot

if TYPE_CHECKING:
    from videoipath_automation_tool.apps.inspect.domain.edge import InspectEdge
    from videoipath_automation_tool.apps.inspect.domain.port import InspectPort
    from videoipath_automation_tool.apps.inspect.domain.service import InspectService
    from videoipath_automation_tool.apps.inspect.snapshot import _DeviceRecord


class InspectDevice(InspectFrozenModel):
    """A topology device/node. Skeleton fields (id, label, coordinates, status, sync, tags) are
    available immediately; ``ports`` and ``services`` lazily hydrate from the server on first
    access ([ADR-0007]). The record is resolved live from the snapshot, so a held reference sees
    hydrated/refreshed data transparently."""

    snapshot: InspectSnapshot
    id: str

    @property
    def label(self) -> str | None:
        return self._record().label

    @property
    def pid(self) -> str | None:
        return self._record().pid

    @property
    def is_virtual(self) -> bool | None:
        meta = self._record().node.meta
        return meta.isVirtual if meta is not None else None

    @property
    def icon_type(self) -> str | None:
        meta = self._record().node.meta
        return meta.iconType if meta is not None else None

    @property
    def status(self) -> InspectApiStatusSummary | None:
        return self._record().node.status

    @property
    def sync_severity(self) -> int | str | None:
        return self._record().node.syncSeverity

    @property
    def tags(self) -> tuple[str, ...]:
        return tuple(self._record().node.tags)

    @property
    def coordinates(self) -> dict[str, float | int | str | None] | None:
        return self._record().node.coordinates

    @property
    def is_hydrated(self) -> bool:
        return self.snapshot.is_device_hydrated(self.id)

    @property
    def fetched_at(self) -> datetime | None:
        return self.snapshot.fetched_at(self.id)

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

    def _record(self) -> "_DeviceRecord":
        record = self.snapshot.get_device_record(self.id)
        if record is None:
            raise KeyError(f"Device '{self.id}' is no longer present in the snapshot.")
        return record
