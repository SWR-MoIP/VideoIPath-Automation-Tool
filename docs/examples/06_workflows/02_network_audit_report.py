"""Read-only network audit report.

Description
-----------
A strictly read-only, cross-app audit you can run against production safely. It reports devices in the
inventory that are missing from the topology, unreachable devices, endpoint vertices without media
tags, edges left at the default weight, services per device, and multicast pool utilization.

Because it never writes, this is a good first script to point at any environment.

Prerequisites
-------------
- A reachable VideoIPath server, VideoIPath >= 2025.4.

Related examples
----------------
- 04_inspect/01_explore_topology_read_only.py
- 06_workflows/03_bulk_retag_and_relabel.py
"""

from __future__ import annotations

from videoipath_automation_tool import VideoIPathApp

SERVER_ADDRESS = "<your-videoipath-ip-or-domain>"
USERNAME = "<your-videoipath-api-user>"
PASSWORD = "<your-videoipath-api-password>"

DRIVER = "com.nevion.NMOS_multidevice-0.1.0"


def main() -> None:
    # --- 1. Connect -----------------------------------------------------------
    app = VideoIPathApp(server_address=SERVER_ADDRESS, username=USERNAME, password=PASSWORD, use_https=False)
    print(f"Audit of {SERVER_ADDRESS} (VideoIPath {app.get_server_version()})")

    # --- 2. Inventory vs. topology coverage -----------------------------------
    topology_ids = {device.id for device in app.inspect.devices}
    inventory_ids = app.inventory.list_device_ids_by_driver(DRIVER)
    missing = [device_id for device_id in inventory_ids if device_id not in topology_ids]
    print(f"\nInventory devices not in the topology: {len(missing)}")
    for device_id in missing:
        print("  -", device_id)

    # --- 3. Unreachable devices -----------------------------------------------
    print("\nUnreachable devices:")
    for device_id in inventory_ids:
        device = app.inventory.get_device(device_id=device_id)
        app.inventory.refresh_device_status(device=device)
        if device.status and not device.status.reachable:
            print("  -", device.configuration.label)

    # --- 4. Endpoints without media tags --------------------------------------
    app.inspect.preload()
    print("\nEndpoint vertices without tags:")
    for device in app.inspect.devices:
        untagged = [v for v in device.codec_vertices if v.is_endpoint and not v.tags]
        if untagged:
            print(f"  - {device.label}: {len(untagged)} untagged endpoint(s)")

    # --- 5. Edges left at the default weight ----------------------------------
    default_weight_edges = [edge for edge in app.inspect.edges if not edge.weight]
    print(f"\nEdges at default weight: {len(default_weight_edges)}")

    # --- 6. Services per device -----------------------------------------------
    print("\nServices per device:")
    for device in app.inspect.devices:
        services = app.inspect.get_services_for_device(device.id)
        if services:
            print(f"  - {device.label}: {len(services)} service(s)")

    # --- 7. Multicast pool utilization ----------------------------------------
    allocation_pools = app.preferences.system_configuration.allocation_pools
    print("\nMulticast pool utilization:")
    for name in allocation_pools.get_multicast_ranges().available_ranges:
        pool = allocation_pools.get_multicast_range_by_name(name)
        print(f"  - {name}: {pool.utilization.percentage}%")


if __name__ == "__main__":
    main()
