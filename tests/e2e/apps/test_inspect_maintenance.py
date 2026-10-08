"""Maintenance contracts on test-owned mocks, with booking-before-resource cleanup.

Run: poetry run test-e2e tests/e2e/apps/test_inspect_maintenance.py
Requires the normal .env configuration and VideoIPath 2026.2.x. No global sweep.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, time, timedelta
from time import monotonic, sleep
from typing import Literal
from zoneinfo import ZoneInfo

import pytest

from videoipath_automation_tool.apps.inspect import (
    InspectEntityNotFoundError,
    InspectMaintenanceBooking,
    InspectMaintenanceConflictError,
    MaintenanceBookingSpec,
    MaintenanceOnceSchedule,
    MaintenanceRecurringSchedule,
    MaintenanceState,
    MaintenanceTargets,
)
from videoipath_automation_tool.apps.videoipath_app import VideoIPathApp

from ..helpers import E2E_TAG, TopologyBuilder, edges_between, remove_devices, unique_label

pytestmark = pytest.mark.e2e


@pytest.fixture(scope="session")
def e2e_sweep() -> None:
    """Focused lifecycle tests clean their own resources, without sweeping other runs."""


@pytest.fixture
def maintenance_label(app: VideoIPathApp, topology_builder: TopologyBuilder) -> Iterator[str]:
    """Own every booking via a unique label/tag; verify cleanup even after test failure."""
    if not app._videoipath_connector.videoipath_version.startswith("2026.2."):
        pytest.skip("Maintenance E2E targets the verified VideoIPath 2026.2 API.")
    label = unique_label("MAINTENANCE")
    try:
        yield label
    finally:
        # Also finds a successful creation whose response was lost. Label updates
        # retain the unique tag, so cleanup does not depend on the original title.
        app.inspect.refresh(load="skeleton")
        leftovers = _owned_bookings(app, label)
        for booking in leftovers:
            if booking.locked:
                spec = MaintenanceBookingSpec(
                    label=booking.label,
                    description=booking.description,
                    tags=booking.tags,
                    targets=MaintenanceTargets(
                        devices=booking.device_ids,
                        modules=booking.module_ids,
                        ports=booking.port_ids,
                        edges=booking.edge_ids,
                    ),
                    schedule=MaintenanceOnceSchedule(start=booking.starts_at, end=booking.ends_at),
                    action=booking.action,
                    trigger=booking.trigger,
                    allow_overlap=booking.allow_overlap,
                    switch_format_state_on_reroute=booking.switch_format_state_on_reroute,
                )
                app.inspect.update_maintenance_booking(booking.id, spec, locked=False)
        if leftovers:
            app.inspect.delete_maintenance_bookings([b.id for b in leftovers])
        _wait_bookings(app, label, expected_ids=set())
        # Do not remove resources if booking cleanup failed above.
        owned_devices = set(topology_builder.device_ids)
        remove_devices(app, owned_devices)
        app.inspect.refresh(load="skeleton")
        assert owned_devices.isdisjoint(d.id for d in app.inspect.devices), "Test topology cleanup failed"
        for device_id in owned_devices:
            with pytest.raises(ValueError, match="No device with id"):
                app.inventory.get_device(device_id=device_id, config_only=True)


@pytest.mark.parametrize("frequency", ["once", "daily", "weekly", "monthly"])
def test_maintenance_lifecycle(
    app: VideoIPathApp,
    topology_builder: TopologyBuilder,
    maintenance_label: str,
    frequency: Literal["once", "daily", "weekly", "monthly"],
) -> None:
    """Persist dates/metadata, protect revisions, preserve locks, and isolate sibling bookings."""
    (device_id,) = topology_builder.add_devices([("MAINTENANCE-A", 2)])
    device = app.inspect.get_device(device_id)
    assert device is not None
    now = datetime.now(UTC).replace(microsecond=0)
    schedule = _schedule(frequency, now)
    windows = schedule.expand() if isinstance(schedule, MaintenanceRecurringSchedule) else [schedule]
    spec = MaintenanceBookingSpec(
        label=maintenance_label,
        description="E2E original maintenance",
        tags=[E2E_TAG, maintenance_label],
        targets=MaintenanceTargets(devices=[device]),
        schedule=schedule,
    )
    # Isolated mocks have no services. Preview must not create any booking.
    assert app.inspect.validate_maintenance_booking(spec) == {}
    app.inspect.refresh()
    assert _owned_bookings(app, maintenance_label) == []
    created = app.inspect.create_maintenance_booking(spec)
    assert created.ok and len(created.details) == len(windows)
    ids = set(created.details)
    bookings = _wait_bookings(app, maintenance_label, ids, states=dict.fromkeys(ids, MaintenanceState.SCHEDULED))
    assert sorted((b.starts_at, b.ends_at) for b in bookings) == sorted((w.start, w.end) for w in windows)
    assert all(b.rev == created.details[b.id].rev and not created.details[b.id].isCancel for b in bookings)
    for booking in bookings:
        assert booking.label == maintenance_label and booking.description == spec.description
        assert set(booking.tags) == set(spec.tags)
        assert booking.device_ids == spec.targets.devices
        assert [d.id for d in booking.devices] == [device_id]
        assert not booking.locked and not booking.allow_overlap and not booking.switch_format_state_on_reroute
        assert booking.action == "nothing" and booking.trigger == "create"
    assert ids <= {b.id for b in app.inspect.get_device(device_id).maintenance_bookings}
    assert {b.id for b in app.inspect.find_maintenance_bookings("all", maintenance_label.lower())} == ids
    assert {b.id for b in app.inspect.find_maintenance_bookings("scheduled", maintenance_label)} == ids
    assert app.inspect.find_maintenance_bookings("active", maintenance_label) == []
    impact = app.inspect.get_maintenance_impact(sorted(ids))
    assert set(impact) <= ids and all(not services for services in impact.values())

    booking = min(bookings, key=lambda b: b.starts_at)
    original_rev = booking.rev
    siblings = {b.id: b.raw.model_dump() for b in bookings if b.id != booking.id}
    window_spec = spec.model_copy(
        update={"schedule": MaintenanceOnceSchedule(start=booking.starts_at, end=booking.ends_at)}
    )
    assert app.inspect.validate_maintenance_booking(window_spec, booking_id=booking.id) == {}
    assert app.inspect.update_maintenance_booking(booking.id, window_spec, locked=True, expected_rev=original_rev).ok
    locked = app.inspect.get_maintenance_booking(booking.id)
    assert locked is not None and locked.locked and locked.rev != original_rev
    locked_rev = locked.rev
    revised = window_spec.model_copy(
        update={"label": unique_label("MAINTENANCE-RENAMED"), "description": "E2E revised maintenance"}
    )
    with pytest.raises(InspectMaintenanceConflictError) as conflict:
        app.inspect.update_maintenance_booking(booking.id, revised, expected_rev=original_rev)
    assert conflict.value.booking_ids == [booking.id]
    assert conflict.value.expected_rev == original_rev and conflict.value.actual_rev == locked_rev
    app.inspect.refresh()
    unchanged = app.inspect.get_maintenance_booking(booking.id)
    assert unchanged.rev == locked_rev and unchanged.label == maintenance_label

    # A real metadata edit with locked omitted must preserve the lock.
    assert app.inspect.update_maintenance_booking(booking.id, revised).ok
    updated = app.inspect.get_maintenance_booking(booking.id)
    assert updated.locked and updated.label == revised.label and updated.description == revised.description
    assert updated.starts_at == window_spec.schedule.start and updated.ends_at == window_spec.schedule.end
    assert set(updated.tags) == set(spec.tags)
    assert maintenance_label not in updated.label  # Subsequent searches must find this ID through its unique tag.
    assert app.inspect.update_maintenance_booking(booking.id, revised, locked=False).ok
    assert not app.inspect.get_maintenance_booking(booking.id).locked

    # Start one explicit ID, including an occurrence created by recurrence.
    active_end = datetime.now(UTC).replace(microsecond=0) + timedelta(hours=1)
    active_spec = revised.model_copy(update={"schedule": MaintenanceOnceSchedule(end=active_end)})
    assert app.inspect.update_maintenance_booking(booking.id, active_spec).ok
    states = dict.fromkeys(ids, MaintenanceState.SCHEDULED) | {booking.id: MaintenanceState.ACTIVE}
    current = _wait_bookings(app, maintenance_label, ids, states=states)
    active = next(b for b in current if b.id == booking.id)
    # Start-now uses the server clock, which need not match the test runner's clock.
    assert active.starts_at < window_spec.schedule.start
    assert active.ends_at == active_end
    assert {b.id for b in app.inspect.find_maintenance_bookings("active", maintenance_label)} == {booking.id}
    assert {b.id for b in app.inspect.find_maintenance_bookings("scheduled", maintenance_label)} == ids - {booking.id}
    assert {b.id: b.raw.model_dump() for b in current if b.id != booking.id} == siblings

    deleted = app.inspect.delete_maintenance_bookings(sorted(ids))
    assert deleted.ok and set(deleted.details) == ids
    assert all(change.isCancel for change in deleted.details.values())
    assert _owned_bookings(app, maintenance_label) == []  # Successful writes invalidate cached reads.
    _wait_bookings(app, maintenance_label, expected_ids=set())
    assert app.inspect.get_maintenance_booking(booking.id) is None
    with pytest.raises(InspectEntityNotFoundError):
        app.inspect.update_maintenance_booking(booking.id, window_spec)


@pytest.mark.parametrize("kind", ["module", "port", "edge"])
def test_maintenance_resource_targets(
    app: VideoIPathApp,
    topology_builder: TopologyBuilder,
    maintenance_label: str,
    kind: Literal["module", "port", "edge"],
) -> None:
    """Domain targets round-trip as selected resources with inverse booking relationships."""
    id_a, id_b = topology_builder.add_devices([("MAINTENANCE-A", 2), ("MAINTENANCE-B", 2)])
    topology_builder.link(id_a, id_b)
    device = app.inspect.get_device(id_a)
    assert device is not None
    port = next(p for p in device.ports if p.vertex_out is not None)
    resource = {"module": port.module, "port": port, "edge": edges_between(app, id_a, id_b)[0]}[kind]
    targets = MaintenanceTargets(**{f"{kind}s": [resource]})
    start = datetime.now(UTC).replace(microsecond=0) + timedelta(days=1)
    spec = MaintenanceBookingSpec(
        label=maintenance_label,
        tags=[E2E_TAG, maintenance_label],
        targets=targets,
        schedule=MaintenanceOnceSchedule(start=start, end=start + timedelta(hours=1)),
    )
    assert app.inspect.validate_maintenance_booking(spec) == {}
    result = app.inspect.create_maintenance_booking(spec)
    assert result.ok and len(result.details) == 1
    (booking,) = _wait_bookings(app, maintenance_label, set(result.details))
    assert getattr(booking, f"{kind}_ids") == getattr(targets, f"{kind}s")
    assert [r.id for r in getattr(booking, f"{kind}s")] == [resource.id]
    assert booking.id in {b.id for b in resource.maintenance_bookings}
    assert booking.id in {b.id for b in app.inspect.get_device(id_a).maintenance_bookings}
    app.inspect.refresh(load="full")
    loaded = app.inspect.get_maintenance_booking(booking.id)
    assert loaded is not None and loaded.raw == booking.raw
    # Fixture also verifies cleanup for bookings left on the server by the test.


def test_immediate_open_ended_and_staged_topology_edits(
    app: VideoIPathApp, topology_builder: TopologyBuilder, maintenance_label: str
) -> None:
    """Immediate/open-ended timestamps round-trip; maintenance cannot flush or discard topology edits."""
    (device_id,) = topology_builder.add_devices([("MAINTENANCE-OPEN", 2)])
    device = app.inspect.get_device(device_id)
    assert device is not None
    pending_label = f"{maintenance_label}-PENDING-DEVICE"
    device.label = pending_label
    spec = MaintenanceBookingSpec(
        label=maintenance_label,
        tags=[E2E_TAG, maintenance_label],
        targets=MaintenanceTargets(devices=[device]),
        schedule=MaintenanceOnceSchedule(),
    )
    assert app.inspect.validate_maintenance_booking(spec) == {}
    created = app.inspect.create_maintenance_booking(spec)
    assert created.ok and len(created.details) == 1
    assert device.label == pending_label
    assert app.inspect.get_device(device_id).label == pending_label
    # A fresh view ignores uncommitted edits, proving the maintenance action did not commit them.
    (booking,) = _wait_bookings(
        app, maintenance_label, set(created.details), states=dict.fromkeys(created.details, MaintenanceState.ACTIVE)
    )
    assert app.inspect.get_device(device_id).label == topology_builder.labels[device_id]
    assert booking.ends_at is None and booking.schedule.infinite
    assert booking.starts_at.tzinfo is not None
    end = datetime.now(UTC).replace(microsecond=0) + timedelta(hours=1)
    finite = spec.model_copy(update={"schedule": MaintenanceOnceSchedule(start=booking.starts_at, end=end)})
    assert app.inspect.update_maintenance_booking(booking.id, finite, locked=True).ok
    current = app.inspect.get_maintenance_booking(booking.id)
    assert current.ends_at == end and not current.schedule.infinite and current.locked
    # Teardown must unlock this remaining booking, delete it, then remove its mock device.


def _schedule(
    frequency: Literal["once", "daily", "weekly", "monthly"], now: datetime
) -> MaintenanceOnceSchedule | MaintenanceRecurringSchedule:
    if frequency == "once":
        return MaintenanceOnceSchedule(start=now + timedelta(days=1), end=now + timedelta(days=2))
    zone = ZoneInfo("Europe/Berlin")
    start = (now.astimezone(zone) + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    if frequency == "monthly":
        # Anchor on day 1, ensuring at least two independent occurrences in every month.
        start = (start + timedelta(days=32)).replace(day=1)
    days = {"daily": 3, "weekly": 14, "monthly": 65}[frequency]
    return MaintenanceRecurringSchedule(
        frequency=frequency,
        start=start,
        end=start + timedelta(days=days),
        timezone=zone.key,
        local_start=time(4),
        local_end=time(5),
        weekdays=[1, 3] if frequency == "weekly" else [],
    )


def _owned_bookings(app: VideoIPathApp, label: str) -> list[InspectMaintenanceBooking]:
    return [
        b
        for b in app.inspect.find_maintenance_bookings(search=label)
        if b.label == label or b.label.startswith(f"{label}-") or label in b.tags
    ]


def _wait_bookings(
    app: VideoIPathApp,
    label: str,
    expected_ids: set[str],
    *,
    states: dict[str, MaintenanceState] | None = None,
) -> list[InspectMaintenanceBooking]:
    deadline = monotonic() + 10
    while True:
        app.inspect.refresh(load="skeleton")
        bookings = _owned_bookings(app, label)
        observed = {b.id: b.state for b in bookings}
        if set(observed) == expected_ids and (states is None or observed == states):
            return bookings
        if monotonic() >= deadline:
            pytest.fail(
                f"Maintenance collector did not converge: expected IDs {expected_ids}, states {states}; got {observed}"
            )
        sleep(0.2)
