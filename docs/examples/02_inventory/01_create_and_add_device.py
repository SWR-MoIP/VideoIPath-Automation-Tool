"""Create a device and add it to the inventory.

Description
-----------
Onboarding a device into VideoIPath starts in the inventory: you create a staged device from a
driver id, fill in its address, label, and driver-specific ``custom_settings``, then add it. The
server assigns the device id, which is only known after ``add_device`` returns.

The ``custom_settings`` object is a typed model chosen by the driver id, so your editor offers
completion for exactly the fields that driver supports.

Prerequisites
-------------
- A reachable VideoIPath server and credentials with inventory write access.

Related examples
----------------
- 02_inventory/02_get_update_and_diff_device.py
- 02_inventory/05_driver_settings_and_queries.py
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

    # --- 2. Create a staged device from a driver ------------------------------
    device = app.inventory.create_device(driver=DRIVER)
    device.configuration.label = "device-a"
    device.configuration.address = "192.0.2.20"
    device.configuration.description = "Example media node"

    # Driver-specific settings are typed for the chosen driver (IntelliSense-friendly).
    device.configuration.custom_settings.port = 8080
    device.configuration.custom_settings.indices_in_ids = False

    # --- 3. Add it to the inventory -------------------------------------------
    # `label_check`/`address_check` (both True by default) raise if a duplicate already exists.
    online_device = app.inventory.add_device(device=device)

    print(f"Added '{online_device.configuration.label}' as {online_device.configuration.device_id}")
    # > Added 'device-a' as device34

    # --- 4. Re-adding the same label raises -----------------------------------
    try:
        app.inventory.add_device(device=device)
    except ValueError as error:
        print("Rejected:", error)
        # > Rejected: Device with label 'device-a' already exists in Inventory: ['device34']


if __name__ == "__main__":
    main()
