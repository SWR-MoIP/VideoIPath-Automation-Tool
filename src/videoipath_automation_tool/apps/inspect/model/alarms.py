from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator

from videoipath_automation_tool.apps.inspect.model.common import (
    InspectApiBaseModel,
    InspectApiDescriptor,
    InspectSeverity,
    map_severity,
)


class InspectApiAlarmId(InspectApiBaseModel):
    alertId: str | None = None
    component: int | None = None
    pointId: list[str] = Field(default_factory=list)


class InspectApiAlarmDesc(InspectApiBaseModel):
    alertId: InspectApiDescriptor | None = None
    pointId: list[InspectApiDescriptor] = Field(default_factory=list)


class InspectApiAlarmInfo(InspectApiBaseModel):
    details: str | None = None
    evtType: int | None = None
    headId: str | None = None
    headSeverity: InspectSeverity | int | str | None = None
    headTime: int | None = None
    id: str | None = None
    links: Any = None
    oTime: int | None = None
    origin: Any = None
    relations: list[Any] = Field(default_factory=list)
    sa: InspectSeverity | int | str | None = None
    seqno: int | None = None
    severity: InspectSeverity | int | str | None = None
    time: int | None = None

    @field_validator("headSeverity", "sa", "severity", mode="before")
    @classmethod
    def _map_severity_fields(cls, value: Any) -> Any:
        return map_severity(value)


class InspectApiAlarmItem(InspectApiBaseModel):
    id_field: str | None = Field(default=None, alias="_id")
    vid: str | None = Field(default=None, alias="_vid")
    acked: bool | None = None
    desc: InspectApiAlarmDesc | None = None
    hidden: bool | None = None
    history: list[Any] = Field(default_factory=list)
    id: InspectApiAlarmId | None = None
    info: InspectApiAlarmInfo | None = None


__all__ = [
    "InspectApiAlarmDesc",
    "InspectApiAlarmId",
    "InspectApiAlarmInfo",
    "InspectApiAlarmItem",
]
