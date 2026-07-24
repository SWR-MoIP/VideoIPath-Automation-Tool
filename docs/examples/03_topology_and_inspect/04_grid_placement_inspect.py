"""Lay out devices in a grid (Inspect app).

Description
-----------
Automated topology builds usually arrange devices on the map programmatically. This example computes a
tidy grid for a set of leaf/spine devices and moves them there — but only writes the positions that
actually changed, so re-running it is a no-op. The paired ``04_grid_placement_topology.py`` does the
same with the Topology app.

Prerequisites
-------------
- A reachable VideoIPath server, VideoIPath >= 2025.4.
- The devices below present in the topology.

Related examples
----------------
- 03_topology_and_inspect/04_grid_placement_topology.py
"""

from __future__ import annotations

from videoipath_automation_tool import VideoIPathApp

SERVER_ADDRESS = "<your-videoipath-ip-or-domain>"
USERNAME = "<your-videoipath-api-user>"
PASSWORD = "<your-videoipath-api-password>"

DEVICE_LABELS = ["leaf-1", "leaf-2", "leaf-3", "leaf-4", "spine-1", "spine-2"]

ORIGIN_X, ORIGIN_Y = 1000, 500
COLUMNS = 3
SPACING = 300


def main() -> None:
    # --- 1. Connect -----------------------------------------------------------
    app = VideoIPathApp(server_address=SERVER_ADDRESS, username=USERNAME, password=PASSWORD, use_https=False)

    # --- 2. Compute the target grid coordinates -------------------------------
    targets: dict[str, tuple[int, int]] = {}
    for index, label in enumerate(DEVICE_LABELS):
        row, col = divmod(index, COLUMNS)
        targets[label] = (ORIGIN_X + col * SPACING, ORIGIN_Y + row * SPACING)

    # --- 3. Move only the devices whose position changed ----------------------
    moved = 0
    with app.inspect.transaction() as tx:
        for label, (x, y) in targets.items():
            device = app.inspect.find_device_by_label(label)
            if device is None:
                continue
            current = device.coordinates or {}
            if (current.get("x"), current.get("y")) == (x, y):
                continue  # already in place — skip the write
            tx.place_device(device.id, x, y)
            moved += 1
        tx.commit()

    print(f"Repositioned {moved} device(s).")
    # > Repositioned 6 device(s).


if __name__ == "__main__":
    main()
