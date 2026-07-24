"""Explore the network topology (read-only).

Description
-----------
A safe, read-only tour of the Inspect app: list devices, edges, and services, walk from a device to
its ports, vertices, and neighbours, and look devices up by label. It also explains skeleton vs. full
loading and the ``preload`` call that avoids N+1 fetches when you need detail for many devices.

Nothing here writes to the server, so it is a good first script to run against any environment.

Prerequisites
-------------
- A reachable VideoIPath server, VideoIPath >= 2025.4.

Related examples
----------------
- 04_inspect/03_services_and_paths.py
- 06_workflows/02_network_audit_report.py
"""

from __future__ import annotations

from videoipath_automation_tool import VideoIPathApp

SERVER_ADDRESS = "<your-videoipath-ip-or-domain>"
USERNAME = "<your-videoipath-api-user>"
PASSWORD = "<your-videoipath-api-password>"


def main() -> None:
    # --- 1. Connect -----------------------------------------------------------
    app = VideoIPathApp(server_address=SERVER_ADDRESS, username=USERNAME, password=PASSWORD, use_https=False)

    # --- 2. Skeleton reads (no per-device detail I/O) -------------------------
    # The first read builds a fast "skeleton" view: all devices and edges, no port detail.
    print(f"{len(app.inspect.devices)} devices, {len(app.inspect.edges)} edges")
    # > 12 devices, 20 edges

    for device in app.inspect.devices:
        print(device.id, device.label, device.status)
        # > device34 leaf-1 <status summary>

    # --- 3. Look up a device and walk its detail ------------------------------
    device = app.inspect.find_device_by_label("leaf-1")
    assert device is not None

    # The first access to .ports hydrates this one device (a single scoped fetch), then caches it.
    for port in device.ports:
        out_vertex = port.vertex_out.id if port.vertex_out else "-"
        in_vertex = port.vertex_in.id if port.vertex_in else "-"
        print(f"{port.label}: out={out_vertex} in={in_vertex}")
        # > Router Out 1: out=device34.1.0 in=-

    for neighbour in device.linked_devices:  # local graph walk, no I/O
        print("linked to", neighbour.label)
        # > linked to spine-1

    # --- 4. Preload many devices in parallel ----------------------------------
    # Hydrate everything up front to avoid one fetch per device in a loop.
    app.inspect.preload()
    hydrated = sum(1 for d in app.inspect.devices if app.inspect.is_device_hydrated(d.id))
    print(f"{hydrated} device(s) hydrated.")
    # > 12 device(s) hydrated.

    # --- 5. Skeleton vs. full loading -----------------------------------------
    # "full" loads the entire topology eagerly in one request (a point-in-time snapshot).
    app.inspect.refresh(load="full")
    print("Reloaded eagerly.")
    # > Reloaded eagerly.


if __name__ == "__main__":
    main()
