"""User-facing maintenance specifications. Writes require an explicit schedule."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from typing import Annotated, Any, Literal, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AwareDatetime, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from .model.common import InspectApiDescriptor, InspectFrozenModel
from .model.maintenance import (
    InspectApiMaintenanceCreate,
    InspectApiMaintenanceCreateDefinition,
    InspectApiMaintenanceInstance,
    InspectApiMaintenanceOnce,
    InspectApiMaintenancePattern,
    InspectApiMaintenanceRecurring,
    InspectApiMaintenanceUpdater,
    MaintenanceAction,
    MaintenanceTrigger,
)


class MaintenanceOnceSchedule(InspectFrozenModel):
    """One window: ``start=None`` means now, ``end=None`` means never ends."""

    model_config = ConfigDict(extra="forbid")
    type: Literal["once"] = "once"
    start: AwareDatetime | None = None
    end: AwareDatetime | None = None

    def to_wire(self) -> InspectApiMaintenanceOnce:
        return InspectApiMaintenanceOnce(startTimestamp=_milliseconds(self.start), endTimestamp=_milliseconds(self.end))

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if self.start is not None and self.end is not None and self.end.astimezone(UTC) <= self.start.astimezone(UTC):
            raise ValueError("end must be after start.")
        return self


class MaintenanceRecurringSchedule(InspectFrozenModel):
    """A daily/weekly/monthly rule expanded into dated one-time bookings by the SDK.

    Weekdays use ISO numbering (Monday=1). Monthly rules use the start date's day.
    Local times use ``timezone``. Nonexistent DST times are rejected; ambiguous
    times use the first occurrence. Missing monthly days are skipped. Only complete
    windows inside [start, end] are included, at most 1000 per request. Raw iteration
    filters can be serialized by to_wire(), but cannot be expanded by this SDK.
    """

    model_config = ConfigDict(extra="forbid")
    type: Literal["recurring"] = "recurring"
    frequency: Literal["daily", "weekly", "monthly"]
    start: AwareDatetime
    end: AwareDatetime
    timezone: str
    local_start: time
    local_end: time
    weekdays: list[int] = Field(default_factory=list)
    pattern_iteration_filter: list[int] = Field(default_factory=list)
    instance_iteration_filter: list[int] = Field(default_factory=list)

    def expand(self) -> list[MaintenanceOnceSchedule]:
        """Expand the finite rule before any I/O; no local scheduler is installed."""
        if self.pattern_iteration_filter or self.instance_iteration_filter:
            raise ValueError("Client expansion does not support server-specific iteration filters.")
        zone = ZoneInfo(self.timezone)
        date = self.start.astimezone(zone).date()
        last = self.end.astimezone(zone).date()
        anchor_day = date.day
        windows: list[MaintenanceOnceSchedule] = []
        while date <= last:
            matches = (
                self.frequency == "daily"
                or self.frequency == "weekly"
                and date.isoweekday() in self.weekdays
                or self.frequency == "monthly"
                and date.day == anchor_day
            )
            if matches:
                start = _local_datetime(datetime.combine(date, self.local_start), zone)
                end_date = date + timedelta(days=self.local_end < self.local_start)
                end = _local_datetime(datetime.combine(end_date, self.local_end), zone)
                if start >= self.start and end <= self.end:
                    windows.append(MaintenanceOnceSchedule(start=start, end=end))
                    if len(windows) > 1000:
                        raise ValueError("Recurrence exceeds 1000 windows; use a shorter recurrence range.")
            if date == last:
                break
            date += timedelta(days=1)
        if not windows:
            raise ValueError("Recurrence range contains no complete maintenance windows.")
        return windows

    def to_wire(self) -> InspectApiMaintenanceRecurring:
        return InspectApiMaintenanceRecurring(
            pattern=InspectApiMaintenancePattern(
                pattern={"daily": 0, "weekly": 1, "monthly": 2}[self.frequency],
                startTime=_milliseconds(self.start),
                endTime=_milliseconds(self.end),
                timeZoneId=self.timezone,
                weekDays=self.weekdays,
                iterationFilter=self.pattern_iteration_filter,
            ),
            instance=InspectApiMaintenanceInstance(
                localStartTime=_seconds(self.local_start),
                localEndTime=_seconds(self.local_end),
                iterationFilter=self.instance_iteration_filter,
            ),
        )

    @model_validator(mode="after")
    def _valid_rule(self) -> Self:
        if self.end.astimezone(UTC) <= self.start.astimezone(UTC):
            raise ValueError("end must be after start.")
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("timezone must be a valid IANA timezone.") from exc
        if any(t.tzinfo is not None or t.microsecond for t in (self.local_start, self.local_end)):
            raise ValueError("local times must have whole seconds and no timezone; use the timezone field.")
        if self.local_start == self.local_end:
            raise ValueError("local_start and local_end must differ.")
        if any(day not in range(1, 8) for day in self.weekdays) or len(set(self.weekdays)) != len(self.weekdays):
            raise ValueError("weekdays must contain unique ISO weekday numbers (1–7).")
        if self.frequency == "weekly" and not self.weekdays:
            raise ValueError("weekly recurrence requires weekdays.")
        if self.frequency != "weekly" and self.weekdays:
            raise ValueError("weekdays apply only to weekly recurrence.")
        return self


MaintenanceSchedule = Annotated[MaintenanceOnceSchedule | MaintenanceRecurringSchedule, Field(discriminator="type")]


class MaintenanceTargets(InspectFrozenModel):
    """Canonical PIDs/edge IDs, or matching Inspect objects, selected for maintenance.

    String module/port IDs must be globally qualified PIDs, not display labels or
    module-local keys. Device objects handle the virtual device ID/PID distinction.
    """

    model_config = ConfigDict(extra="forbid")
    devices: list[str] = Field(default_factory=list)
    modules: list[str] = Field(default_factory=list)
    ports: list[str] = Field(default_factory=list)
    edges: list[str] = Field(default_factory=list)

    @property
    def pids(self) -> list[str]:
        return list(dict.fromkeys([*self.devices, *self.modules, *self.ports]))

    @field_validator("devices", "modules", "ports", "edges", mode="before")
    @classmethod
    def _normalize(cls, values: Any, info: ValidationInfo) -> list[str]:
        from .domain.device import InspectDevice
        from .domain.edge import InspectEdge
        from .domain.module import InspectModule
        from .domain.port import InspectPort

        kinds = {"devices": InspectDevice, "modules": InspectModule, "ports": InspectPort, "edges": InspectEdge}
        if not isinstance(values, (list, tuple)):
            raise ValueError("targets must be a list or tuple.")  # noqa: TRY004 — Pydantic validation error
        ids: list[str] = []
        for value in values:
            if isinstance(value, str):
                pid = value
            elif not isinstance(value, kinds[info.field_name]):
                raise ValueError(f"{info.field_name} requires IDs or matching Inspect objects.")  # noqa: TRY004
            elif isinstance(value, InspectDevice):
                record = value.snapshot.get_device_record(value.id)
                pid = (
                    (record.node.context.devicePid if record and record.node.context else None)
                    or (record.pid if record else None)
                    or value.id
                )
            elif isinstance(value, InspectModule):
                status = value._status()
                pid = (
                    (status.context.modulePid if status and status.context else None)
                    or (status.pid if status else None)
                    or value.id
                )
            else:
                pid = value.id
            if not pid or not pid.strip() or pid != pid.strip():
                raise ValueError("Every maintenance target must have a nonempty canonical identifier.")
            ids.append(pid)
        return list(dict.fromkeys(ids))


class MaintenanceBookingSpec(InspectFrozenModel):
    """Complete create/update intent. Previewing and writing are separate calls."""

    model_config = ConfigDict(extra="forbid")
    label: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    targets: MaintenanceTargets
    schedule: MaintenanceSchedule
    action: MaintenanceAction = "nothing"
    trigger: MaintenanceTrigger = "create"
    allow_overlap: bool = False
    switch_format_state_on_reroute: bool = False

    def to_create(self, schedule: MaintenanceOnceSchedule | None = None) -> InspectApiMaintenanceCreate:
        return InspectApiMaintenanceCreate(
            scheduleInfo=(schedule or self.schedule).to_wire(),
            serviceDefinition=InspectApiMaintenanceCreateDefinition(
                **self.to_updater().model_dump(exclude={"pids"}), devicePids=self.targets.pids
            ),
        )

    def to_updater(self) -> InspectApiMaintenanceUpdater:
        return InspectApiMaintenanceUpdater(
            descriptor=InspectApiDescriptor(label=self.label.strip(), desc=self.description.strip()),
            pids=self.targets.pids,
            edgeIds=self.targets.edges,
            tags=self.tags,
            action=self.action,
            trigger=self.trigger,
            allowOverlap=self.allow_overlap,
            switchFormatStateOnReroute=self.switch_format_state_on_reroute,
        )

    @model_validator(mode="after")
    def _required(self) -> Self:
        if not self.label.strip():
            raise ValueError("label must not be empty.")
        if not self.targets.pids and not self.targets.edges:
            raise ValueError("Select at least one maintenance target.")
        return self


def _milliseconds(value: datetime | None) -> int | None:
    return int(value.timestamp() * 1000) if value is not None else None


def _seconds(value: time) -> int:
    return value.hour * 3600 + value.minute * 60 + value.second


def _local_datetime(value: datetime, zone: ZoneInfo) -> datetime:
    aware = value.replace(tzinfo=zone, fold=0)
    utc = aware.astimezone(UTC)
    if utc.astimezone(zone).replace(tzinfo=None) != value:
        raise ValueError(f"Nonexistent local maintenance time {value.isoformat()} in {zone.key}.")
    return utc


__all__ = [
    "MaintenanceBookingSpec",
    "MaintenanceOnceSchedule",
    "MaintenanceRecurringSchedule",
    "MaintenanceSchedule",
    "MaintenanceTargets",
]
