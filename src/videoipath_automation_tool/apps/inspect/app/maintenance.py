"""Immediate maintenance lifecycle methods; never part of a topology commit."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from ..errors import InspectEntityNotFoundError, InspectMaintenanceConflictError
from ..maintenance import MaintenanceBookingSpec, MaintenanceOnceSchedule, MaintenanceRecurringSchedule
from ..model.maintenance import (
    InspectApiMaintenanceInheritable,
    InspectApiMaintenanceUpdate,
    InspectApiUpdateMaintenanceData,
    InspectApiValidateMaintenanceData,
    MaintenanceImpact,
    MaintenanceResult,
    MaintenanceState,
)

if TYPE_CHECKING:
    from ..api import InspectAPI
    from ..domain.maintenance import InspectMaintenanceBooking
    from ..snapshot import InspectSnapshot


class InspectMaintenanceMixin:
    _inspect_api: InspectAPI
    _snapshot: InspectSnapshot | None

    @property
    def maintenance_bookings(self) -> list[InspectMaintenanceBooking]:
        """All server bookings (lazy snapshot section). Call refresh() for external changes."""
        return self._get_snapshot().maintenance_bookings

    def get_maintenance_booking(self, booking_id: str) -> InspectMaintenanceBooking | None:
        return self._get_snapshot().get_maintenance_booking(booking_id)

    def find_maintenance_bookings(
        self, state: Literal["all", "active", "scheduled"] = "all", search: str = ""
    ) -> list[InspectMaintenanceBooking]:
        """Filter the snapshot by state and case-insensitive label/tag substring."""
        if state not in ("all", "active", "scheduled"):
            raise ValueError("state must be all, active, or scheduled.")
        code = {"active": MaintenanceState.ACTIVE, "scheduled": MaintenanceState.SCHEDULED}.get(state)
        needle = search.casefold()
        return [
            booking
            for booking in self.maintenance_bookings
            if (code is None or booking.state == code)
            and (needle in booking.label.casefold() or any(needle in tag.casefold() for tag in booking.tags))
        ]

    def validate_maintenance_booking(
        self, spec: MaintenanceBookingSpec, booking_id: str | None = None
    ) -> dict[str, list[MaintenanceImpact]]:
        """Read-only impacts keyed by service ID, with separate reports for each window."""
        spec = _validated_spec(spec)
        if booking_id is not None:
            _ids([booking_id])
            _require_once_update(spec)
        result: dict[str, list[MaintenanceImpact]] = {}
        for schedule in _windows(spec):
            impacts = self._inspect_api.validate_maintenance(
                InspectApiValidateMaintenanceData(
                    pids=spec.targets.pids,
                    edgeIds=spec.targets.edges,
                    label=spec.label.strip(),
                    scheduleInfo=schedule.to_wire(),
                    id=booking_id,
                )
            )
            for service_id, impact in impacts.items():
                result.setdefault(service_id, []).append(impact)
        return result

    def get_maintenance_impact(self, booking_ids: list[str]) -> dict[str, dict[str, MaintenanceImpact]]:
        """Current impact, keyed first by booking ID, then by affected service ID."""
        return self._inspect_api.fetch_maintenance_impact(_ids(booking_ids))

    def create_maintenance_booking(self, spec: MaintenanceBookingSpec) -> MaintenanceResult:
        """Create immediately, expanding recurrence into one batch of dated bookings.

        Preview separately. Result details carry server-returned IDs when available.
        """
        spec = _validated_spec(spec)
        result = self._inspect_api.update_maintenance(
            InspectApiUpdateMaintenanceData(create=[spec.to_create(window) for window in _windows(spec)]),
            operation="create",
        )
        self._maintenance_written()
        return result

    def update_maintenance_booking(
        self,
        booking_id: str,
        spec: MaintenanceBookingSpec,
        *,
        locked: bool | None = None,
        expected_rev: str | None = None,
    ) -> MaintenanceResult:
        """Replace the specification using a fresh revision, optionally changing the lock.

        Supply a one-time schedule for this explicit booking ID. Recurring creation
        produces individual bookings; this method does not modify their siblings. For
        start-now, supply a one-time schedule with start=None and the desired end.
        Omitted locked preserves the fresh server value. No automatic write retry.
        """
        _ids([booking_id])
        spec = _validated_spec(spec)
        _require_once_update(spec)
        current = next((b for b in self._inspect_api.get_maintenance_section() if b.id == booking_id), None)
        if current is None:
            raise InspectEntityNotFoundError(booking_id, "maintenance booking")
        if expected_rev is not None and current.rev != expected_rev:
            raise InspectMaintenanceConflictError(booking_id, expected_rev, current.rev)
        result = self._inspect_api.update_maintenance(
            InspectApiUpdateMaintenanceData(
                update=[
                    InspectApiMaintenanceUpdate(
                        id=booking_id,
                        rev=current.rev,
                        inheritable=InspectApiMaintenanceInheritable(
                            scheduleInfo=spec.schedule.to_wire(),
                            locked=current.generic.locked if locked is None else locked,
                        ),
                        updater=spec.to_updater(),
                    )
                ]
            ),
            operation="update",
        )
        self._maintenance_written()
        return result

    def delete_maintenance_bookings(self, booking_ids: list[str]) -> MaintenanceResult:
        """Cancel/delete explicit server IDs. The server decides whether locked IDs may be deleted."""
        result = self._inspect_api.update_maintenance(
            InspectApiUpdateMaintenanceData(delete=_ids(booking_ids)), operation="delete"
        )
        self._maintenance_written()
        return result

    def _maintenance_written(self) -> None:
        if self._snapshot is not None:
            self._snapshot.invalidate_maintenance()


def _validated_spec(spec: MaintenanceBookingSpec) -> MaintenanceBookingSpec:
    # Recheck nested mutable lists / model_copy(update=...) before issuing I/O.
    return MaintenanceBookingSpec.model_validate(spec.model_dump())


def _windows(spec: MaintenanceBookingSpec) -> list[MaintenanceOnceSchedule]:
    return spec.schedule.expand() if isinstance(spec.schedule, MaintenanceRecurringSchedule) else [spec.schedule]


def _require_once_update(spec: MaintenanceBookingSpec) -> None:
    if spec.schedule.type != "once":
        raise ValueError("Updating an explicit booking ID requires a one-time schedule; create recurrence separately.")


def _ids(values: list[str]) -> list[str]:
    if not isinstance(values, (list, tuple)) or not values:
        raise ValueError("booking_ids must be a nonempty list of IDs.")
    if any(not isinstance(v, str) or not v.strip() or v != v.strip() for v in values):
        raise ValueError("booking IDs must be nonempty strings without surrounding whitespace.")
    return list(dict.fromkeys(values))
