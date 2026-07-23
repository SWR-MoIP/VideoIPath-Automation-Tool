"""Bulk re-labeling and re-tagging.

Description
-----------
Applies a naming/tagging policy across a fleet of devices: select devices by a label prefix, compute
the change set, print a dry-run report, then apply every change in a single Inspect transaction. The
matching inventory labels are updated too, so both views stay consistent.

This demonstrates the change-set + dry-run + batch-commit pattern on a realistic bulk edit.

Prerequisites
-------------
- A reachable VideoIPath server, VideoIPath >= 2025.4.

Related examples
----------------
- 06_workflows/02_network_audit_report.py
- 03_topology_and_inspect/02_configure_vertices_inspect.py
"""

from __future__ import annotations

from videoipath_automation_tool import VideoIPathApp

SERVER_ADDRESS = "<your-videoipath-ip-or-domain>"
USERNAME = "<your-videoipath-api-user>"
PASSWORD = "<your-videoipath-api-password>"

DRY_RUN = True  # set to False to apply the changes
OLD_PREFIX = "cam-"
NEW_PREFIX = "camera-"
ADD_TAG = "camera"


def main() -> None:
    # --- 1. Connect -----------------------------------------------------------
    app = VideoIPathApp(server_address=SERVER_ADDRESS, username=USERNAME, password=PASSWORD, use_https=False)

    # --- 2. Compute the change set --------------------------------------------
    changes: list[tuple[str, str, str]] = []  # (device_id, old_label, new_label)
    for device in app.inspect.devices:
        label = device.label or ""
        if not label.startswith(OLD_PREFIX):
            continue
        new_label = NEW_PREFIX + label[len(OLD_PREFIX) :]
        if new_label != label or ADD_TAG not in device.tags:
            changes.append((device.id, label, new_label))

    # --- 3. Dry-run report ----------------------------------------------------
    print(f"{len(changes)} device(s) to update:")
    for _, old_label, new_label in changes:
        print(f"  {old_label} -> {new_label} (+tag '{ADD_TAG}')")
        # >   cam-1 -> camera-1 (+tag 'camera')

    if DRY_RUN:
        print("Dry run — no changes written. Set DRY_RUN = False to apply.")
        return

    # --- 4. Apply topology changes in one transaction -------------------------
    with app.inspect.transaction() as tx:
        for device_id, _, new_label in changes:
            device = app.inspect.get_device(device_id)
            if device is None:
                continue
            device.label = new_label
            device.tags = sorted(set(device.tags) | {ADD_TAG})
            app.inspect.update(device, tx=tx)
        tx.commit()

    # --- 5. Keep the inventory labels in sync ---------------------------------
    for device_id, _, new_label in changes:
        inventory_device = app.inventory.get_device(device_id=device_id)
        inventory_device.configuration.label = new_label
        app.inventory.update_device(device=inventory_device)

    print(f"Updated {len(changes)} device(s).")


if __name__ == "__main__":
    main()
