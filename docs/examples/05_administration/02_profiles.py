"""Manage profiles.

Description
-----------
Profiles describe media formats and are referenced as vertex tags when configuring endpoints. This
example lists profile names, fetches one, creates a new profile, clones an existing one as a template,
and cleans up the clone.

Prerequisites
-------------
- A reachable VideoIPath server and credentials with profile-management access.

Related examples
----------------
- 03_topology_and_inspect/02_configure_vertices_inspect.py
"""

from __future__ import annotations

from videoipath_automation_tool import VideoIPathApp

SERVER_ADDRESS = "<your-videoipath-ip-or-domain>"
USERNAME = "<your-videoipath-api-user>"
PASSWORD = "<your-videoipath-api-password>"


def main() -> None:
    # --- 1. Connect -----------------------------------------------------------
    app = VideoIPathApp(server_address=SERVER_ADDRESS, username=USERNAME, password=PASSWORD, use_https=False)

    # --- 2. List existing profiles --------------------------------------------
    names = app.profile.list_profile_names() or []
    print(f"{len(names)} profile(s): {names[:5]}")
    # > 12 profile(s): ['V_1080i50', 'V_1080p50', 'A_2CH_LR', ...]

    # --- 3. Create a new profile ----------------------------------------------
    profile = app.profile.create_profile(name="profile-a")
    app.profile.add_profile(profile)
    print("Created profile-a")
    # > Created profile-a

    # --- 4. Clone an existing profile as a template ---------------------------
    if names:
        source = app.profile.get_profile_by_name(names[0])
        if source is not None and not isinstance(source, list):
            clone = app.profile.clone_profile(source)
            app.profile.add_profile(clone)
            print("Cloned", names[0], "->", clone.name)
            # > Cloned V_1080i50 -> V_1080i50 (clone)

            # --- 5. Clean up the clone --------------------------------------------
            app.profile.remove_profile(profile=clone)
            print("Removed the clone.")
            # > Removed the clone.


if __name__ == "__main__":
    main()
