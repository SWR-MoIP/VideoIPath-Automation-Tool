"""Maintenance transport models (VideoIPath 2026.2).

Collector schedules describe resolved windows; action schedules describe intent.
They deliberately use different types so a recurring rule cannot be lost on edit.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Annotated, Any, Literal

from pydantic import Field, field_validator

from .common import (
    InspectApiBaseModel,
    InspectApiDescriptor,
    InspectApiPostRequestHeader,
    InspectApiRestV2Header,
    InspectApiSimpleActionResult,
    InspectApiStatusContext,
)

MaintenanceAction = Literal["nothing", "invalidate", "reroute", "rerouteSA"]
MaintenanceTrigger = Literal["create", "active"]


class MaintenanceState(IntEnum):
    SCHEDULED = 0
    ACTIVE = 1


class InspectApiMaintenanceWindow(InspectApiBaseModel):
    startTimestamp: int
    endTimestamp: int
    infinite: bool = False


class InspectApiMaintenanceResource(InspectApiBaseModel):
    label: str = ""
    context: InspectApiStatusContext = Field(default_factory=InspectApiStatusContext)
    pid: list[str] = Field(default_factory=list)
    deviceId: str | None = None


class InspectApiMaintenanceEdge(InspectApiBaseModel):
    id: str
    from_: InspectApiMaintenanceResource = Field(alias="from")
    to: InspectApiMaintenanceResource


class InspectApiMaintenanceGeneric(InspectApiBaseModel):
    descriptor: InspectApiDescriptor = Field(default_factory=InspectApiDescriptor)
    locked: bool = False
    state: MaintenanceState | int

    @field_validator("state", mode="before")
    @classmethod
    def _state(cls, value: Any) -> Any:
        return MaintenanceState(value) if type(value) is int and value in (0, 1) else value


class InspectApiMaintenanceBookingItem(InspectApiBaseModel):
    id: str = Field(alias="_id")
    vid: str | None = Field(default=None, alias="_vid")
    rev: str
    generic: InspectApiMaintenanceGeneric
    scheduleInfo: InspectApiMaintenanceWindow
    action: MaintenanceAction | str = "nothing"
    trigger: MaintenanceTrigger | str = "create"
    allowOverlap: bool = False
    switchFormatStateOnReroute: bool = False
    tags: list[str] = Field(default_factory=list)
    devices: list[InspectApiMaintenanceResource] = Field(default_factory=list)
    modules: list[InspectApiMaintenanceResource] = Field(default_factory=list)
    ports: list[InspectApiMaintenanceResource] = Field(default_factory=list)
    edges: list[InspectApiMaintenanceEdge] = Field(default_factory=list)


class InspectApiMaintenanceOnce(InspectApiBaseModel):
    type: Literal["once"] = "once"
    startTimestamp: int | None = None
    endTimestamp: int | None = None


class InspectApiMaintenancePattern(InspectApiBaseModel):
    pattern: Literal[0, 1, 2]
    startTime: int
    endTime: int
    timeZoneId: str
    weekDays: list[int] = Field(default_factory=list)
    iterationFilter: list[int] = Field(default_factory=list)


class InspectApiMaintenanceInstance(InspectApiBaseModel):
    localStartTime: int
    localEndTime: int
    iterationFilter: list[int] = Field(default_factory=list)


class InspectApiMaintenanceRecurring(InspectApiBaseModel):
    type: Literal["recurring"] = "recurring"
    pattern: InspectApiMaintenancePattern
    instance: InspectApiMaintenanceInstance


InspectApiMaintenanceSchedule = Annotated[
    InspectApiMaintenanceOnce | InspectApiMaintenanceRecurring, Field(discriminator="type")
]


class InspectApiMaintenanceDefinition(InspectApiBaseModel):
    descriptor: InspectApiDescriptor
    action: MaintenanceAction = "nothing"
    trigger: MaintenanceTrigger = "create"
    allowOverlap: bool = False
    switchFormatStateOnReroute: bool = False
    tags: list[str] = Field(default_factory=list)
    edgeIds: list[str] = Field(default_factory=list)


class InspectApiMaintenanceCreateDefinition(InspectApiMaintenanceDefinition):
    devicePids: list[str] = Field(default_factory=list)


class InspectApiMaintenanceUpdater(InspectApiMaintenanceDefinition):
    pids: list[str] = Field(default_factory=list)


class InspectApiMaintenanceCreate(InspectApiBaseModel):
    scheduleInfo: InspectApiMaintenanceSchedule
    serviceDefinition: InspectApiMaintenanceCreateDefinition


class InspectApiMaintenanceInheritable(InspectApiBaseModel):
    scheduleInfo: InspectApiMaintenanceSchedule
    locked: bool


class InspectApiMaintenanceUpdate(InspectApiBaseModel):
    id: str
    rev: str
    inheritable: InspectApiMaintenanceInheritable
    updater: InspectApiMaintenanceUpdater


class InspectApiUpdateMaintenanceData(InspectApiBaseModel):
    create: list[InspectApiMaintenanceCreate] = Field(default_factory=list)
    update: list[InspectApiMaintenanceUpdate] = Field(default_factory=list)
    delete: list[str] = Field(default_factory=list)


class InspectApiUpdateMaintenanceRequest(InspectApiBaseModel):
    header: InspectApiPostRequestHeader = Field(default_factory=InspectApiPostRequestHeader)
    data: InspectApiUpdateMaintenanceData


class MaintenanceChange(InspectApiBaseModel):
    """Server-confirmed booking change; its dictionary key is the authoritative ID."""

    rev: str
    isCancel: bool
    status: int
    type: str
    resolvable: bool | None = None


class MaintenanceResult(InspectApiSimpleActionResult):
    """Server result and optional per-booking details; never IDs parsed from messages."""

    details: dict[str, MaintenanceChange] = Field(default_factory=dict)


class InspectApiUpdateMaintenanceResult(InspectApiBaseModel):
    result: MaintenanceResult
    details: dict[str, MaintenanceChange] = Field(default_factory=dict)


class InspectApiUpdateMaintenanceResponse(InspectApiBaseModel):
    header: InspectApiRestV2Header
    data: InspectApiUpdateMaintenanceResult


class InspectApiValidateMaintenanceData(InspectApiBaseModel):
    edgeIds: list[str] = Field(default_factory=list)
    pids: list[str] = Field(default_factory=list)
    scheduleInfo: InspectApiMaintenanceSchedule
    label: str
    id: str | None = None


class InspectApiValidateMaintenanceRequest(InspectApiBaseModel):
    header: InspectApiPostRequestHeader = Field(default_factory=InspectApiPostRequestHeader)
    data: InspectApiValidateMaintenanceData


class InspectApiFetchMaintenanceImpactData(InspectApiBaseModel):
    ids: list[str]


class InspectApiFetchMaintenanceImpactRequest(InspectApiBaseModel):
    header: InspectApiPostRequestHeader = Field(default_factory=InspectApiPostRequestHeader)
    data: InspectApiFetchMaintenanceImpactData


class MaintenanceImpactContributor(InspectApiBaseModel):
    label: str


class MaintenanceImpactEntry(InspectApiBaseModel):
    start: int
    end: int
    saBefore: int | str
    saAfter: int | str
    contributors: dict[str, MaintenanceImpactContributor] = Field(default_factory=dict)


class MaintenanceImpact(InspectApiBaseModel):
    """One affected service; maps returned by the API are keyed by service ID.

    Timestamps are raw epoch milliseconds, including the server's infinite sentinel.
    """

    label: str
    start: int
    end: int
    protection: str
    maxSaBefore: int | str
    maxSaAfter: int | str
    entries: list[MaintenanceImpactEntry] = Field(default_factory=list)


__all__ = [
    "InspectApiFetchMaintenanceImpactData",
    "InspectApiFetchMaintenanceImpactRequest",
    "InspectApiMaintenanceBookingItem",
    "InspectApiMaintenanceCreate",
    "InspectApiMaintenanceCreateDefinition",
    "InspectApiMaintenanceDefinition",
    "InspectApiMaintenanceEdge",
    "InspectApiMaintenanceGeneric",
    "InspectApiMaintenanceInheritable",
    "InspectApiMaintenanceInstance",
    "InspectApiMaintenanceOnce",
    "InspectApiMaintenancePattern",
    "InspectApiMaintenanceRecurring",
    "InspectApiMaintenanceResource",
    "InspectApiMaintenanceSchedule",
    "InspectApiMaintenanceUpdate",
    "InspectApiMaintenanceUpdater",
    "InspectApiMaintenanceWindow",
    "InspectApiUpdateMaintenanceData",
    "InspectApiUpdateMaintenanceRequest",
    "InspectApiUpdateMaintenanceResponse",
    "InspectApiUpdateMaintenanceResult",
    "InspectApiValidateMaintenanceData",
    "InspectApiValidateMaintenanceRequest",
    "MaintenanceAction",
    "MaintenanceChange",
    "MaintenanceImpact",
    "MaintenanceImpactContributor",
    "MaintenanceImpactEntry",
    "MaintenanceResult",
    "MaintenanceState",
    "MaintenanceTrigger",
]
