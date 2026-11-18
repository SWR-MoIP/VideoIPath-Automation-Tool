from __future__ import annotations

from videoipath_automation_tool.apps.inspect.model.alarms import InspectApiAlarmItem
from videoipath_automation_tool.apps.inspect.model.common import (
    InspectApiDescriptor,
    InspectFrozenModel,
    InspectSeverity,
    format_repr,
)

_ALARM_MESSAGE_REPR_LIMIT = 60


class InspectAlarm(InspectFrozenModel):
    """One active alarm from ``status/alarms/current``, correlated onto a topology resource."""

    item: InspectApiAlarmItem

    @property
    def id(self) -> str | None:
        return self.item.id_field

    @property
    def title(self) -> str | None:
        """Alarm title (``desc.alertId.label``). ``None`` when missing or empty."""
        return _text(self._alert.label if self._alert is not None else None)

    @property
    def details(self) -> str | None:
        """Alarm details (``info.details``). ``None`` when missing or empty."""
        info = self.item.info
        return _text(info.details if info is not None else None)

    @property
    def description(self) -> str | None:
        """Longer alarm description (``desc.alertId.desc``). ``None`` when missing or empty."""
        return _text(self._alert.desc if self._alert is not None else None)

    @property
    def message(self) -> str | None:
        """The alarm text the GUI shows: the non-empty parts of :attr:`title` and :attr:`details`,
        joined with ``": "``. ``None`` when both are empty."""
        parts = [part for part in (self.title, self.details) if part]
        return ": ".join(parts) or None

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

    def __repr__(self) -> str:
        message = self.message
        if message is not None and len(message) > _ALARM_MESSAGE_REPR_LIMIT:
            message = message[:_ALARM_MESSAGE_REPR_LIMIT] + "…"
        return format_repr(self, id=self.id, severity=self.severity, message=message)

    __str__ = __repr__

    @property
    def _alert(self) -> InspectApiDescriptor | None:
        desc = self.item.desc
        return desc.alertId if desc is not None else None


def _text(value: str | None) -> str | None:
    return value or None


__all__ = ["InspectAlarm"]
