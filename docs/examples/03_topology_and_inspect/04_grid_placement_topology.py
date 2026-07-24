"""Lay out devices in a grid (Topology app).

Description
-----------
Automated topology builds usually arrange devices on the map programmatically. This example reads the
current positions with ``placement.get_all_device_positions``, computes a tidy grid, and moves only the
devices whose position changed. The paired ``04_grid_placement_inspect.py`` does the same with the
Inspect app.

Prerequisites
-------------
- A reachable VideoIPath server with the devices below present in the topology.
- NOTE: the Topology app is deprecated on VideoIPath 2025.x and unsupported on 2026.x (its
  constructor raises ``TopologyUnsupportedError``). On modern servers prefer the paired
  ``04_grid_placement_inspect.py``.

Related examples
----------------
- 03_topology_and_inspect/04_grid_placement_inspect.py
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

    # --- 2. Read the current positions of all devices -------------------------
    current_positions = app.topology.placement.get_all_device_positions()

    # --- 3. Move only the devices whose position changed ----------------------
    moved = 0
    for index, label in enumerate(DEVICE_LABELS):
        device_id = app.topology.find_device_id_by_label(label, label_search_mode="user_defined_label_only")
        if not isinstance(device_id, str):
            continue

        row, col = divmod(index, COLUMNS)
        x, y = ORIGIN_X + col * SPACING, ORIGIN_Y + row * SPACING

        current = current_positions.get(device_id, {})
        if (current.get("x"), current.get("y")) == (x, y):
            continue  # already in place — skip the write

        # fetch_device=False keeps bulk repositioning fast (no re-fetch after each move).
        app.topology.placement.set_device_position(device_id, x=x, y=y, fetch_device=False)
        moved += 1

    print(f"Repositioned {moved} device(s).")
    # > Repositioned 6 device(s).


if __name__ == "__main__":
    main()
