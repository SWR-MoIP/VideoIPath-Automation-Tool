"""Device lifecycle in the topology (Topology app): add, configure, remove.

Description
-----------
Once a device exists in the inventory it can be placed into the topology graph, given display metadata
(label, description, tags, icon, coordinates), and later removed. This is the classic Topology-app
variant; the paired ``01_device_lifecycle_inspect.py`` implements the same scenario with the
forward-looking Inspect app.

With the Topology app you fetch a ``TopologyDevice``, mutate its nested ``configuration`` object, and
push the whole device with ``update_device`` (which diffs and writes only the changed graph elements).

Prerequisites
-------------
- A reachable VideoIPath server; a device named ``device-a`` in the inventory.
- NOTE: the Topology app is deprecated on VideoIPath 2025.x and unsupported on 2026.x, where its
  constructor raises ``TopologyUnsupportedError``. On modern servers prefer the paired
  ``01_device_lifecycle_inspect.py``.

Related examples
----------------
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

    device_id = app.inventory.find_device_id_by_label("device-a", label_search_mode="user_defined_label_only")
    assert isinstance(device_id, str)

    # --- 2. Fetch the device's driver-generated graph -------------------------
    # get_device synthesizes the device from the driver if it is not yet placed in the topology.
    device = app.topology.get_device(device_id=device_id)

    # --- 3. Apply base configuration via the configuration object -------------
    config = device.configuration
    config.label = "leaf-1"
    config.description = "Top-of-rack leaf switch"
    config.tags = ["site-a", "leaf"]
    config.icon_type = "ipSwitchRouter"
    config.position_x = 1000
    config.position_y = 500

    # update_device places the device if new, and writes only the changed graph elements.
    updated = app.topology.update_device(device)
    print("Configured", updated.configuration.label)
    # > Configured leaf-1

    # --- 4. Remove the device from the topology (guarded) ---------------------
    affected = app.topology.list_services_affected_by_device_remove(device)
    if affected:
        print(f"Skipping removal: {len(affected)} service(s) still use this device.")
        # > Skipping removal: 2 service(s) still use this device.
    else:
        app.topology.remove_device_by_id(device_id=device_id)
        print("Removed from topology.")
        # > Removed from topology.


if __name__ == "__main__":
    main()
