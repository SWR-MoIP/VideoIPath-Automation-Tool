"""Inspect services and their paths.

Description
-----------
Services are the booked media connections routed across the topology. This example lists them, looks
one up by booking id, prints its source, destination, and the devices its path traverses, and shows
the "service-impact guard": before changing or removing a device, check which services still depend on
it.

This is read-only except for the illustrative guard at the end.

Prerequisites
-------------
- A reachable VideoIPath server, VideoIPath >= 2025.4, with at least one booked service.

Related examples
----------------
- 04_inspect/01_explore_topology_read_only.py
- 03_topology_and_inspect/01_device_lifecycle_inspect.py
"""

from __future__ import annotations

from videoipath_automation_tool import VideoIPathApp

SERVER_ADDRESS = "<your-videoipath-ip-or-domain>"
USERNAME = "<your-videoipath-api-user>"
PASSWORD = "<your-videoipath-api-password>"


def main() -> None:
    # --- 1. Connect -----------------------------------------------------------
    app = VideoIPathApp(server_address=SERVER_ADDRESS, username=USERNAME, password=PASSWORD, use_https=False)

    # --- 2. List services -----------------------------------------------------
    services = app.inspect.services
    print(f"{len(services)} service(s) booked.")
    # > 4 service(s) booked.

    for service in services:
        print(f"{service.booking_id}: {service.source} -> {service.destination} [{service.status}]")
        # > booking-1: leaf-1 -> spine-1 [<status>]

    if not services:
        return

    # --- 3. Resolve one service and print its path ----------------------------
    service = app.inspect.get_service_by_booking_id(services[0].booking_id)
    assert service is not None
    print("Source device:", service.source_device.label if service.source_device else "-")
    # > Source device: leaf-1
    path = " -> ".join(device.label or device.id for device in service.path_devices)
    print("Path:", path)
    # > Path: leaf-1 -> spine-1 -> leaf-2

    # --- 4. Service-impact guard before touching a device ---------------------
    device = app.inspect.find_device_by_label("leaf-1")
    if device is not None:
        affected = app.inspect.get_services_for_device(device.id)
        if affected:
            print(f"leaf-1 carries {len(affected)} service(s); change it with care.")
            # > leaf-1 carries 2 service(s); change it with care.
        else:
            print("leaf-1 carries no services; safe to change.")
            # > leaf-1 carries no services; safe to change.


if __name__ == "__main__":
    main()
