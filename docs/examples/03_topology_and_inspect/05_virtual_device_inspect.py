"""Create a virtual (driverless) device (Inspect app).

Description
-----------
Virtual devices model endpoints that have no real driver — patch panels, tie-line groups, or external
switches. This example builds one from a port-template spec and places it on the map. The paired
``05_virtual_device_topology.py`` does the same with the Topology app.

A virtual device is created unplaced; afterward it behaves like any other device (``place_device``,
metadata edits via setters, ``remove_device_from_topology``).

Prerequisites
-------------
- A reachable VideoIPath server, VideoIPath >= 2025.4.

Related examples
----------------
- 03_topology_and_inspect/05_virtual_device_topology.py
"""

from __future__ import annotations

from videoipath_automation_tool import VideoIPathApp
from videoipath_automation_tool.apps.inspect import VirtualDeviceSpec

SERVER_ADDRESS = "<your-videoipath-ip-or-domain>"
USERNAME = "<your-videoipath-api-user>"
PASSWORD = "<your-videoipath-api-password>"


def main() -> None:
    # --- 1. Connect -----------------------------------------------------------
    app = VideoIPathApp(server_address=SERVER_ADDRESS, username=USERNAME, password=PASSWORD, use_https=False)

    # --- 2. Inspect the available port templates ------------------------------
    templates = app.inspect.list_port_templates()
    for template in templates:
        print(f"{template.id}: {template.label} ({template.direction})")
        # > ip_in: IP input (In)
        # > ip_out: IP output (Out)

    # --- 3. Build a virtual-device spec ---------------------------------------
    # from_ports takes template ids (optionally as (template_id, count) tuples).
    spec = VirtualDeviceSpec.from_ports(("ip_in", 2), ("ip_out", 2))

    # --- 4. Create and place the device ---------------------------------------
    device = app.inspect.create_virtual_device(spec)
    print("Created virtual device", device.id)
    # > Created virtual device virtual.1

    device.label = "tieline-a"
    device.tags = ["virtual", "tieline"]
    app.inspect.update(device)
    app.inspect.place_device(device.id, x=1500, y=900)
    print("Placed", device.label)
    # > Placed tieline-a


if __name__ == "__main__":
    main()
