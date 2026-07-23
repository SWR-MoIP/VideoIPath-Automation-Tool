"""Sync security domains and device memberships.

Description
-----------
Security domains partition resources (devices, profiles) for access control. This example reconciles a
desired set of domains against the server — creating what is missing, updating descriptions, and
removing what is stale — while always protecting the built-in ``Default`` domain. It then reconciles a
single device's domain memberships with a read → compare → write-only-on-change pattern.

This mirrors how an external source of truth (e.g. site/tenant data) drives domain management.

Prerequisites
-------------
- A reachable VideoIPath server and credentials with security-administration access.
- A device named ``device-a`` in the inventory.

Related examples
----------------
- 06_workflows/01_full_onboarding_pipeline.py
"""

from __future__ import annotations

from videoipath_automation_tool import VideoIPathApp

SERVER_ADDRESS = "<your-videoipath-ip-or-domain>"
USERNAME = "<your-videoipath-api-user>"
PASSWORD = "<your-videoipath-api-password>"

PROTECTED_DOMAIN = "Default"
DESIRED_DOMAINS = {
    "site-a": "Devices at site A",
    "site-b": "Devices at site B",
    "site-c": "Devices at site C",
}


def main() -> None:
    # --- 1. Connect -----------------------------------------------------------
    app = VideoIPathApp(server_address=SERVER_ADDRESS, username=USERNAME, password=PASSWORD, use_https=False)

    # --- 2. Reconcile the set of domains --------------------------------------
    existing = set(app.security.domains.list_domain_names())

    # Create missing domains.
    for name, description in DESIRED_DOMAINS.items():
        if name not in existing:
            app.security.domains.create_domain(name=name, description=description)
            print("Created domain", name)
            # > Created domain site-a

    # Update descriptions that drifted.
    for name, description in DESIRED_DOMAINS.items():
        if name in existing:
            domain = app.security.domains.get_domain_by_name(domain_name=name)
            if domain.description != description:
                domain.description = description
                app.security.domains.update_domain(domain)
                print("Updated domain", name)

    # Remove stale domains (never the protected one).
    for name in existing - set(DESIRED_DOMAINS) - {PROTECTED_DOMAIN}:
        app.security.domains.remove_domain(app.security.domains.get_domain_by_name(domain_name=name))
        print("Removed domain", name)

    # --- 3. Reconcile one device's domain memberships -------------------------
    device_id = app.inventory.find_device_id_by_label("device-a", label_search_mode="user_defined_label_only")
    assert isinstance(device_id, str)

    memberships = app.security.resources.get_device_memberships(device_id=device_id)
    current = set(app.security.resources.convert_domain_ids_to_names(memberships.domains))
    desired = {"site-a"}

    if current != desired:
        memberships.domains = app.security.resources.convert_domain_names_to_ids(sorted(desired))
        app.security.resources.update_memberships(memberships=memberships)
        print(f"Set {device_id} memberships to {sorted(desired)}")
        # > Set device34 memberships to ['site-a']
    else:
        print("Memberships already correct.")
        # > Memberships already correct.


if __name__ == "__main__":
    main()
