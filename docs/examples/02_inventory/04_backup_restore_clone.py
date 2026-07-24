"""Back up, restore, and clone device configurations.

Description
-----------
A device configuration can be dumped to a plain dict (easily serialized to JSON) for backup, then
parsed back into a device object to restore or compare it. The same mechanism clones a device: strip
its device id and add it again — either on the same server (a copy) or on a second server (migration).

Prerequisites
-------------
- A reachable VideoIPath server; a device named ``device-a`` in the inventory.
- For the cross-server clone: a second reachable server.

Related examples
----------------
- 02_inventory/02_get_update_and_diff_device.py
"""

from __future__ import annotations

import json
from pathlib import Path

from videoipath_automation_tool import VideoIPathApp

SERVER_ADDRESS = "<your-videoipath-ip-or-domain>"
USERNAME = "<your-videoipath-api-user>"
PASSWORD = "<your-videoipath-api-password>"

DRIVER = "com.nevion.NMOS_multidevice-0.1.0"
BACKUP_FILE = Path("device-a.backup.json")


def main() -> None:
    # --- 1. Connect -----------------------------------------------------------
    app = VideoIPathApp(server_address=SERVER_ADDRESS, username=USERNAME, password=PASSWORD, use_https=False)

    device = app.inventory.get_device(
        label="device-a", label_search_mode="user_defined_label_only", custom_settings_type=DRIVER
    )

    # --- 2. Back up the configuration to a JSON file --------------------------
    config_dump = app.inventory.dump_configuration(device)
    BACKUP_FILE.write_text(json.dumps(config_dump, indent=4))
    print("Backed up to", BACKUP_FILE)
    # > Backed up to device-a.backup.json

    # --- 3. Restore: load the backup and diff against the live config ---------
    restored = app.inventory.parse_configuration(json.loads(BACKUP_FILE.read_text()))
    live = app.inventory.get_device(device_id=restored.configuration.device_id)
    diff = app.inventory.diff_device_configuration(reference_device=restored, staged_device=live)
    if diff.configuration_diff.changed:
        print("Live config drifted from the backup; run update_device(restored) to restore it.")
        # > Live config drifted from the backup; run update_device(restored) to restore it.

    # --- 4. Clone on the same server ------------------------------------------
    # Removing the device id turns the object into a fresh "staged" device.
    clone = app.inventory.parse_configuration(config_dump)
    clone.configuration.label = "device-a-clone"
    clone.configuration.address = "192.0.2.21"
    clone.remove_device_id()
    cloned_device = app.inventory.add_device(clone)
    print("Cloned as", cloned_device.configuration.device_id)
    # > Cloned as device36

    # --- 5. Clone onto a second server (migration) ----------------------------
    # migration = app.inventory.parse_configuration(config_dump)
    # migration.remove_device_id()
    # prod_app = VideoIPathApp(server_address="198.51.100.10", username=USERNAME, password=PASSWORD, use_https=False)
    # prod_app.inventory.add_device(migration)


if __name__ == "__main__":
    main()
