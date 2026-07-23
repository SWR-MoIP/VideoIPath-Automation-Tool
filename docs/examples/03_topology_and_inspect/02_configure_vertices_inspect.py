"""Configure device vertices (Inspect app): endpoints, SIPS, media tags.

Description
-----------
A device's vertices describe its media inputs/outputs (codec vertices) and network interfaces (IP
vertices). This example marks the codec vertices as usable endpoints, sets their SIPS mode, and tags
them with media profiles pulled from the profile app — the same pattern a vendor "vertex processor"
uses. The paired ``02_configure_vertices_topology.py`` does the same with the Topology app.

The recommended write style edits each vertex's properties, collects the dirty objects, and flushes
them together with a single ``app.inspect.update([...])`` call.

Prerequisites
-------------
- A reachable VideoIPath server, VideoIPath >= 2025.4.
- A device named ``leaf-1`` in the topology whose ports/vertices are synced.

Related examples
----------------
- 03_topology_and_inspect/02_configure_vertices_topology.py
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

    device = app.inspect.find_device_by_label("leaf-1")
    assert device is not None

    # Media profile tags to assign to endpoints (falls back to a fixed list if none are defined).
    profile_tags = app.profile.list_profile_names() or ["V_1080i50", "V_1080p50"]

    # --- 2. Configure every codec vertex via property setters -----------------
    edited = []
    for vertex in device.codec_vertices:
        vertex.use_as_endpoint = True
        vertex.sips_mode = "SIPSAuto"
        vertex.active = True
        vertex.tags = profile_tags
        edited.append(vertex)

    # --- 3. Flush all edits in a single unit of work --------------------------
    if edited:
        app.inspect.update(edited)
        print(f"Configured {len(edited)} codec vertices.")
        # > Configured 8 codec vertices.

    # --- 4. Target a single vertex by its factory label -----------------------
    uplink = device.find_vertex_by_factory_label("port-out-1")
    if uplink is not None:
        uplink.label = "Uplink to spine-1"
        app.inspect.update(uplink)
        print("Labeled uplink vertex", uplink.id)
        # > Labeled uplink vertex device34.1.3000000

    # --- 5. Alternative: keyword-style update ---------------------------------
    # A single vertex can also be edited without holding the object:
    #
    #     app.inspect.update_vertex(uplink.id, use_as_endpoint=True, sips_mode="SIPSAuto", tags=profile_tags)


if __name__ == "__main__":
    main()
