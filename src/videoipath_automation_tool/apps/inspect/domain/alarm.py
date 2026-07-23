from __future__ import annotations

from videoipath_automation_tool.apps.inspect.model.alarms import InspectApiAlarmItem
from videoipath_automation_tool.apps.inspect.model.common import InspectFrozenModel, InspectSeverity


class InspectAlarm(InspectFrozenModel):
    """One active alarm from ``status/alarms/current``, correlated onto a topology resource."""

    item: InspectApiAlarmItem

    @property
    def id(self) -> str | None:
        return self.item.id_field

    @property
    def message(self) -> str | None:
        info = self.item.info
        return info.details if info is not None else None

    @property
    def severity(self) -> InspectSeverity | int | str | None:
        info = self.item.info
        return info.severity if info is not None else None

    @property
    def sa(self) -> InspectSeverity | int | str | None:
        """Service-affecting severity of this alarm (``info.sa``)."""
        info = self.item.info
        return info.sa if info is not None else None

    @property
    def service_affecting(self) -> InspectSeverity | int | str | None:
        return self.sa

    @property
    def acknowledged(self) -> bool | None:
        return self.item.acked

    @property
    def hidden(self) -> bool | None:
        return self.item.hidden

    @property
    def time(self) -> int | None:
        info = self.item.info
        return info.time if info is not None else None

    @property
    def alert_id(self) -> str | None:
        alarm_id = self.item.id
        return alarm_id.alertId if alarm_id is not None else None

    @property
    def component(self) -> int | None:
        alarm_id = self.item.id
        return alarm_id.component if alarm_id is not None else None

    @property
    def point_id(self) -> list[str]:
        alarm_id = self.item.id
        return list(alarm_id.pointId) if alarm_id is not None else []

    @property
    def point_labels(self) -> list[str]:
        desc = self.item.desc
        if desc is None:
            return []
        return [entry.label for entry in desc.pointId if entry.label]


__all__ = ["InspectAlarm"]
