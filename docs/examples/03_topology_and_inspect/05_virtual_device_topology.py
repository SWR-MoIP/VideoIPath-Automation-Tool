"""Create a virtual (driverless) device (Topology app).

Description
-----------
Virtual devices model endpoints that have no real driver — patch panels, tie-line groups, or external
switches. This example builds one by adding a virtual switching-core module and codec vertices, then
adds it to the topology (which assigns the next free ``virtual.N`` id). The paired
``05_virtual_device_inspect.py`` does the same with the Inspect app.

Prerequisites
-------------
- A reachable VideoIPath server.
- NOTE: the Topology app is deprecated on VideoIPath 2025.x and unsupported on 2026.x (its
  constructor raises ``TopologyUnsupportedError``). Virtual-device editing here is experimental. On
  modern servers prefer the paired ``05_virtual_device_inspect.py``.

Related examples
----------------
- 03_topology_and_inspect/05_virtual_device_inspect.py
"""

from __future__ import annotations

from videoipath_automation_tool import VideoIPathApp

SERVER_ADDRESS = "<your-videoipath-ip-or-domain>"
USERNAME = "<your-videoipath-api-user>"
PASSWORD = "<your-videoipath-api-password>"


def main() -> None:
    # --- 1. Connect -----------------------------------------------------------
    app = VideoIPathApp(server_address=SERVER_ADDRESS, username=USERNAME, password=PASSWORD, use_https=False)

    # --- 2. Build the virtual device ------------------------------------------
    device = app.topology.create_virtual_device()
    device.configuration.label = "tieline-a"
    device.configuration.tags = ["virtual", "tieline"]

    # Add a switching core, then attach codec vertices to it.
    device.add_virtual_module()
    device.add_virtual_codec_vertex(vertex_direction="In", codec_format="Video", module_number=0)
    device.add_virtual_codec_vertex(vertex_direction="Out", codec_format="Video", module_number=0)

    # --- 3. Add it to the topology --------------------------------------------
    # add_device_initially assigns the next free virtual.N id automatically.
    app.topology.add_device_initially(device)
    print("Created virtual device", device.configuration.base_device.id)
    # > Created virtual device virtual.1


if __name__ == "__main__":
    main()
