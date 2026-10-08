"""Snapshot-backed maintenance bookings and their resolved topology resources."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from ..errors import InspectEntityNotFoundError
from ..model.common import InspectFrozenModel, format_repr
from ..model.maintenance import InspectApiMaintenanceBookingItem, InspectApiMaintenanceWindow, MaintenanceState
from ..snapshot import InspectSnapshot

if TYPE_CHECKING:
    from .device import InspectDevice
    from .edge import InspectEdge
    from .module import InspectModule
    from .port import InspectPort


class InspectMaintenanceBooking(InspectFrozenModel):
    """Read-only view; write through app.inspect's explicit maintenance methods.

    ``raw`` retains all IDs and contexts, even when topology objects are absent.
    Resource properties resolve explicitly selected resources, not expanded descendants.
    """

    snapshot: InspectSnapshot
    id: str

    @property
    def raw(self) -> InspectApiMaintenanceBookingItem:
        item = self.snapshot.get_maintenance_record(self.id)
        if item is None:
            raise InspectEntityNotFoundError(self.id, "maintenance booking")
        return item

    @property
    def rev(self) -> str:
        return self.raw.rev

    @property
    def label(self) -> str:
        return self.raw.generic.descriptor.label

    @property
    def description(self) -> str:
        return self.raw.generic.descriptor.desc

    @property
    def tags(self) -> list[str]:
        return list(self.raw.tags)

    @property
    def state(self) -> MaintenanceState | int:
        return self.raw.generic.state

    @property
    def locked(self) -> bool:
        return self.raw.generic.locked

    @property
    def schedule(self) -> InspectApiMaintenanceWindow:
        """Resolved window, not the recurrence rule originally submitted."""
        return self.raw.scheduleInfo

    @property
    def starts_at(self) -> datetime:
        return datetime.fromtimestamp(self.schedule.startTimestamp / 1000, UTC)

    @property
    def ends_at(self) -> datetime | None:
        return None if self.schedule.infinite else datetime.fromtimestamp(self.schedule.endTimestamp / 1000, UTC)

    @property
    def action(self) -> str:
        return self.raw.action

    @property
    def trigger(self) -> str:
        return self.raw.trigger

    @property
    def allow_overlap(self) -> bool:
        return self.raw.allowOverlap

    @property
    def switch_format_state_on_reroute(self) -> bool:
        return self.raw.switchFormatStateOnReroute

    @property
    def device_ids(self) -> list[str]:
        return [r.context.devicePid for r in self.raw.devices if r.context.devicePid]

    @property
    def module_ids(self) -> list[str]:
        return [r.context.modulePid for r in self.raw.modules if r.context.modulePid]

    @property
    def port_ids(self) -> list[str]:
        return [r.context.portPid for r in self.raw.ports if r.context.portPid]

    @property
    def edge_ids(self) -> list[str]:
        return [r.id for r in self.raw.edges]

    @property
    def devices(self) -> list[InspectDevice]:
        return [
            d
            for pid in self.device_ids
            if (d := self.snapshot.get_device(self.snapshot._resolve_device_id(pid))) is not None
        ]

    @property
    def modules(self) -> list[InspectModule]:
        result = []
        for resource in self.raw.modules:
            context = resource.context
            device_id = self.snapshot._resolve_device_id(context.devicePid)
            if device_id and context.modulePid:
                for module in self.snapshot.get_modules_for_device(device_id):
                    status = module._status()
                    pid = (
                        (status.context.modulePid if status and status.context else None)
                        or (status.pid if status else None)
                        or module.id
                    )
                    if pid == context.modulePid:
                        result.append(module)
        return result

    @property
    def ports(self) -> list[InspectPort]:
        result = []
        for resource in self.raw.ports:
            context = resource.context
            device_id = self.snapshot._resolve_device_id(context.devicePid)
            if device_id and context.portPid:
                port = self.snapshot.get_port(device_id, context.portPid)
                if port is not None:
                    result.append(port)
        return result

    @property
    def edges(self) -> list[InspectEdge]:
        ids = set(self.edge_ids)
        return [edge for edge in self.snapshot.edges if edge.id in ids]

    def __repr__(self) -> str:
        return format_repr(self, id=self.id, label=lambda: self.label)

    __str__ = __repr__


__all__ = ["InspectMaintenanceBooking"]
