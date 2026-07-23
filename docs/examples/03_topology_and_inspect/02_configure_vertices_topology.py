"""Configure device vertices (Topology app): endpoints, SIPS, media tags.

Description
-----------
A device's vertices describe its media inputs/outputs (codec vertices) and network interfaces (IP
vertices). This example marks the codec vertices as usable endpoints, sets their SIPS mode, and tags
them with media profiles pulled from the profile app. The paired ``02_configure_vertices_inspect.py``
does the same with the Inspect app.

With the Topology app you mutate the vertex objects held inside ``device.configuration`` and then push
the whole device once with ``update_device`` — a single write covers all the vertex changes.

Prerequisites
-------------
- A reachable VideoIPath server; a device named ``leaf-1`` in the topology.
- NOTE: the Topology app is deprecated on VideoIPath 2025.x and unsupported on 2026.x (its
  constructor raises ``TopologyUnsupportedError``). On modern servers prefer the paired
  ``02_configure_vertices_inspect.py``.

Related examples
----------------
- 03_topology_and_inspect/02_configure_vertices_inspect.py
- 05_administration/02_profiles.py
"""

from __future__ import annotations

from videoipath_automation_tool import VideoIPathApp

SERVER_ADDRESS = "<your-videoipath-ip-or-domain>"
USERNAME = "<your-videoipath-api-user>"
PASSWORD = "<your-videoipath-api-password>"


def main() -> None:
    # --- 1. Connect -----------------------------------------------------------
    app = VideoIPathApp(server_address=SERVER_ADDRESS, username=USERNAME, password=PASSWORD, use_https=False)

    device_id = app.topology.find_device_id_by_label("leaf-1", label_search_mode="user_defined_label_only")
    assert isinstance(device_id, str)
    device = app.topology.get_device(device_id=device_id)

    profile_tags = app.profile.list_profile_names() or ["V_1080i50", "V_1080p50"]

    # --- 2. Configure every codec vertex in the configuration object ----------
    for vertex in device.configuration.codec_vertices:
        vertex.use_as_endpoint = True
        vertex.sips_mode = "SIPSAuto"
        vertex.sdp_support = True
        vertex.tags = profile_tags

    # --- 3. Target a single vertex by its factory label -----------------------
    uplink = device.configuration.get_vertex_by_label("port-out-1", label_type="factory")
    if uplink is not None:
        uplink.label = "Uplink to spine-1"

    # --- 4. Push the whole device once ----------------------------------------
    # update_device diffs against the server and writes only the changed graph elements.
    app.topology.update_device(device=device)
    print(f"Configured vertices on {device.configuration.label}.")
    # > Configured vertices on leaf-1.


if __name__ == "__main__":
    main()
