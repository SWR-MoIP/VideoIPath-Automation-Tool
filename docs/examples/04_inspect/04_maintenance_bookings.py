"""Maintenance examples for VideoIPath 2026.2.0; use a dedicated test device.

Configuration comes from the usual VIPAT_* environment variables. Running this
script writes maintenance bookings and deletes them afterward. Adapt DEVICE_ID.
No topology transaction is required. Older server versions have not been tested.
"""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta

from videoipath_automation_tool.apps.inspect import (
    MaintenanceBookingSpec,
    MaintenanceOnceSchedule,
    MaintenanceRecurringSchedule,
    MaintenanceTargets,
)
from videoipath_automation_tool.apps.videoipath_app import VideoIPathApp

DEVICE_ID = "device-a"


def main() -> None:
    # --- Connect and select a dedicated test device ---

    app = VideoIPathApp()
    device = app.inspect.get_device(DEVICE_ID)

    if device is None:
        raise ValueError("Set DEVICE_ID to a dedicated test device in Inspect.")

    # --- Describe a one-time window ---
    # Keep the target, schedule, and booking description separate so each is easy
    # to adapt. All datetime values must include a timezone.

    now = datetime.now(UTC)
    targets = MaintenanceTargets(devices=[device])

    schedule = MaintenanceOnceSchedule(
        start=now + timedelta(days=1),
        end=now + timedelta(days=1, hours=2),
    )

    spec = MaintenanceBookingSpec(
        label="E2E-maintenance-example",
        description="Example maintenance window",
        tags=["vipat-e2e"],
        targets=targets,
        schedule=schedule,
    )

    # --- Preview, then create ---
    # Preview is read-only. Creation is a separate, immediate server action.

    preview = app.inspect.validate_maintenance_booking(spec)
    print("Preview:", preview)

    created = app.inspect.create_maintenance_booking(spec)

    # Only the server's result identifies the new bookings. Do not infer IDs
    # from the label or from a human-readable success message.
    booking_ids = list(created.details)

    try:
        # --- Inspect, lock, and start the booking ---

        for booking_id in booking_ids:
            booking = app.inspect.get_maintenance_booking(booking_id)

            if booking is None:
                raise RuntimeError("Created booking is not visible; inspect server state before retrying.")

            print(booking.label, booking.state, booking.devices)

            # Updates always need the complete specification. The expected
            # revision prevents overwriting a booking that changed since reading.
            app.inspect.update_maintenance_booking(
                booking_id,
                spec,
                locked=True,
                expected_rev=booking.rev,
            )

            # An omitted start means "now" on the server. Keep the other fields
            # by copying the spec, and explicitly unlock the booking here.
            immediate_schedule = MaintenanceOnceSchedule(end=now + timedelta(hours=1))
            start_now = spec.model_copy(update={"schedule": immediate_schedule})

            app.inspect.update_maintenance_booking(booking_id, start_now, locked=False)

        if booking_ids:
            impact = app.inspect.get_maintenance_impact(booking_ids)
            print("Impact:", impact)

    finally:
        # --- Remove the example bookings, even if an earlier step fails ---
        # Explicitly unlock before deleting; omitted locked preserves its value.
        # This example reuses the original complete spec when unlocking.

        for booking_id in booking_ids:
            app.inspect.update_maintenance_booking(booking_id, spec, locked=False)

        if booking_ids:
            app.inspect.delete_maintenance_bookings(booking_ids)

    # --- Describe a recurring rule ---
    # Daily rules need no weekdays. Monthly rules use the local start date's day.

    rule = MaintenanceRecurringSchedule(
        frequency="weekly",
        # Finite bounds limit which dated windows will be created.
        start=now + timedelta(days=1),
        end=now + timedelta(days=32),
        # The local window repeats in this timezone on Monday and Friday.
        timezone="Europe/Berlin",
        local_start=time(4),
        local_end=time(5),
        weekdays=[1, 5],  # ISO numbering: Monday=1, Sunday=7.
    )

    recurring = spec.model_copy(update={"schedule": rule})

    # --- Inspect the expanded dates, preview their impact, then create ---

    windows = rule.expand()
    print("Dated windows:", windows)

    recurring_preview = app.inspect.validate_maintenance_booking(recurring)
    print("Recurring preview:", recurring_preview)

    result = app.inspect.create_maintenance_booking(recurring)

    # Each dated booking has its own ID. Manage IDs individually with one-time
    # schedules; collector windows cannot reconstruct the original recurrence rule.
    recurring_ids = list(result.details)

    # Remove every dated booking created by this example.
    if recurring_ids:
        app.inspect.delete_maintenance_bookings(recurring_ids)


if __name__ == "__main__":
    main()
