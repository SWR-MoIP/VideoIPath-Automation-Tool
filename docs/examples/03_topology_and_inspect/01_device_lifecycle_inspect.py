"""Device lifecycle in the topology (Inspect app): add, configure, remove.

Description
-----------
Once a device exists in the inventory it can be placed into the topology graph, given display metadata
(label, description, tags, icon, coordinates), and later removed. This is the Inspect-app variant; the
paired ``01_device_lifecycle_topology.py`` implements the same scenario with the classic Topology app.

The recommended write style is: edit the domain object's properties and flush them with
``app.inspect.update(obj)`` (a unit of work that commits all pending edits). The keyword-argument
methods (``app.inspect.update_device(...)``) do the same thing in one call and are shown at the end as
an alternative.

Prerequisites
-------------
- A reachable VideoIPath server, VideoIPath >= 2025.4.
- A device named ``device-a`` already in the inventory (see 02_inventory/01_create_and_add_device.py).

Related examples
----------------
- 03_topology_and_inspect/01_device_lifecycle_topology.py
- 04_inspect/01_explore_topology_read_only.py
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

    # --- 2. Add the device to the topology graph ------------------------------
    # Places at (x, y) and syncs driver-reported ports/vertices (sync=True by default).
    app.inspect.add_devices_to_topology([(device_id, 1000, 500)])

    # --- 3. Apply base configuration via property setters (recommended) -------
    device = app.inspect.get_device(device_id)
    assert device is not None
    device.label = "leaf-1"
    device.description = "Top-of-rack leaf switch"
    device.tags = ["site-a", "leaf"]
    device.icon_type = "ipSwitchRouter"
    device.coordinates = {"x": 1000, "y": 500}
    app.inspect.update(device)  # commits every pending edit on the device in one transaction
    print("Configured", device.label)
    # > Configured leaf-1

    # --- 4. Remove the device from the topology (guarded) ---------------------
    # Refuse to remove a device that still carries booked services.
    affected = app.inspect.get_services_for_device(device_id)
    if affected:
        print(f"Skipping removal: {len(affected)} service(s) still use this device.")
        # > Skipping removal: 2 service(s) still use this device.
    else:
        app.inspect.remove_device_from_topology(device_id)
        print("Removed from topology.")
        # > Removed from topology.

    # --- 5. Alternative: keyword-style update in a single call ----------------
    # Equivalent to the setter block in step 3, without holding a domain object:
    #
    #     app.inspect.update_device(
    #         device_id,
    #         label="leaf-1",
    #         description="Top-of-rack leaf switch",
    #         tags=["site-a", "leaf"],
    #         icon_type="ipSwitchRouter",
    #         coordinates={"x": 1000, "y": 500},
    #     )


if __name__ == "__main__":
    main()
