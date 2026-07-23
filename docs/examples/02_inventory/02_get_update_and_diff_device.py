"""Fetch, diff, and update a device (idempotent writes).

Description
-----------
This example shows the read-modify-write cycle for an inventory device and the "diff before write"
pattern that makes automation idempotent: stage the desired configuration, compare it against what is
already on the server, and only call ``update_device`` when something actually changed. Re-running the
same script is then a no-op.

It also covers fetching a device by id, label, or address, and refreshing its live status.

Prerequisites
-------------
- A reachable VideoIPath server; a device named ``device-a`` already in the inventory
  (see 02_inventory/01_create_and_add_device.py).

Related examples
----------------
- 02_inventory/01_create_and_add_device.py
- 06_workflows/01_full_onboarding_pipeline.py
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

    # --- 2. Fetch a device (by label, id, or address) -------------------------
    # Passing `custom_settings_type` gives typed access to the driver settings.
    device = app.inventory.get_device(
        label="device-a",
        label_search_mode="user_defined_label_only",
        custom_settings_type=DRIVER,
    )
    print(device.configuration.device_id, device.configuration.address)
    # > device34 192.0.2.20

    # Equivalent lookups:
    #   app.inventory.get_device(device_id="device34")
    #   app.inventory.get_device(address="192.0.2.20")

    # --- 3. Stage the desired configuration -----------------------------------
    reference = app.inventory.get_device(device_id=device.configuration.device_id)
    device.configuration.description = "Primary media node"
    device.configuration.custom_settings.port = 8080

    # --- 4. Diff, then write only when there is a change -----------------------
    diff = app.inventory.diff_device_configuration(reference_device=reference, staged_device=device)
    changes = diff.configuration_diff
    if changes.added or changes.changed or changes.removed:
        app.inventory.update_device(device=device)
        print("Updated device (changes applied).")
        # > Updated device (changes applied).
    else:
        print("No changes — nothing to write.")
        # > No changes — nothing to write.

    # --- 5. Refresh the live status -------------------------------------------
    # Device status is not updated automatically; refresh it explicitly.
    app.inventory.refresh_device_status(device=device)
    if device.status:
        print("Reachable:", device.status.reachable)
        # > Reachable: True


if __name__ == "__main__":
    main()
