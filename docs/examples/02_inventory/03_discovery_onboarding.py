"""Onboard auto-discovered devices.

Description
-----------
VideoIPath discovers devices on the network before they are added to the inventory. This example
lists the discovered devices, builds an inventory device from a discovery entry's suggested
configuration, adds it, and shows how to enable/disable a device afterward.

Prerequisites
-------------
- A reachable VideoIPath server with at least one discovered (but not yet onboarded) device.

Related examples
----------------
- 02_inventory/01_create_and_add_device.py
"""

from __future__ import annotations

from videoipath_automation_tool import VideoIPathApp

SERVER_ADDRESS = "<your-videoipath-ip-or-domain>"
USERNAME = "<your-videoipath-api-user>"
PASSWORD = "<your-videoipath-api-password>"


def main() -> None:
    # --- 1. Connect -----------------------------------------------------------
    app = VideoIPathApp(server_address=SERVER_ADDRESS, username=USERNAME, password=PASSWORD, use_https=False)

    # --- 2. List discovered devices -------------------------------------------
    discovered = app.inventory.get_discovered_devices()
    for entry in discovered:
        suggested_driver = entry.suggestedConfigs[0].driver if entry.suggestedConfigs else None
        print(f"{entry.id} | already onboarded as: {entry.exists} | driver: {suggested_driver}")
        # > OF-00:00:00:00:00:01 | already onboarded as: [] | driver: name='openflow' organization='com.nevion' ...

    # --- 3. Onboard the first not-yet-existing discovered device --------------
    candidate = next((entry for entry in discovered if not entry.exists), None)
    if candidate is None:
        print("Nothing new to onboard.")
        # > Nothing new to onboard.
        return

    device = app.inventory.create_device_from_discovered_device(
        discovered_device_id=candidate.id,
        driver="com.nevion.openflow-0.0.1",
    )
    device.configuration.label = "device-b"

    online_device = app.inventory.add_device(device)
    device_id = online_device.configuration.device_id
    print(f"Onboarded {candidate.id} as {device_id}")
    # > Onboarded OF-00:00:00:00:00:01 as device35

    # --- 4. Enable / disable a device -----------------------------------------
    disabled = app.inventory.disable_device(device_id)
    print("Active after disable:", disabled.configuration.active)
    # > Active after disable: False

    enabled = app.inventory.enable_device(device_id)
    print("Active after enable:", enabled.configuration.active)
    # > Active after enable: True


if __name__ == "__main__":
    main()
