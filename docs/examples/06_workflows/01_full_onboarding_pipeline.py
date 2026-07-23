"""Full onboarding pipeline: external source of truth to a running topology.

Description
-----------
This is the flagship example — it stitches the individual operations into one end-to-end pipeline,
modeled on a real "sync from an external source of truth" workflow (e.g. an IPAM/DCIM system). Given a
small inline description of the desired network, it:

1. creates or updates each device in the inventory (diff before write),
2. waits until the devices are reachable,
3. adds them to the topology at computed grid coordinates,
4. applies base configuration and endpoint settings in one transaction,
5. connects the devices per the cabling data (reserving bandwidth headroom),
6. assigns each device to its site's security domain.

A ``DRY_RUN`` flag runs the whole thing without writing, and because every step is diff-based, running
it twice is a no-op.

Prerequisites
-------------
- A reachable VideoIPath server, VideoIPath >= 2025.4, with inventory + security write access.

Related examples
----------------
- 02_inventory/02_get_update_and_diff_device.py
- 03_topology_and_inspect/03_connect_devices_with_edges_inspect.py
- 05_administration/01_security_domains_and_memberships.py
"""

from __future__ import annotations

import time

from videoipath_automation_tool import VideoIPathApp

SERVER_ADDRESS = "<your-videoipath-ip-or-domain>"
USERNAME = "<your-videoipath-api-user>"
PASSWORD = "<your-videoipath-api-password>"

DRIVER = "com.nevion.NMOS_multidevice-0.1.0"
DRY_RUN = True  # set to False to actually write to the server
BANDWIDTH_HEADROOM = 0.9  # use 90% of the nominal link bandwidth

# The desired network, as it might come from an external source of truth.
DESIRED_DEVICES = [
    {"label": "leaf-1", "address": "192.0.2.21", "site": "site-a"},
    {"label": "leaf-2", "address": "192.0.2.22", "site": "site-a"},
    {"label": "spine-1", "address": "192.0.2.31", "site": "site-a"},
]
DESIRED_LINKS = [
    {"a": "leaf-1", "b": "spine-1", "bandwidth": 10000},
    {"a": "leaf-2", "b": "spine-1", "bandwidth": 10000},
]


def main() -> None:
    # --- 1. Connect -----------------------------------------------------------
    app = VideoIPathApp(server_address=SERVER_ADDRESS, username=USERNAME, password=PASSWORD, use_https=False)
    print(f"{'DRY RUN — ' if DRY_RUN else ''}syncing {len(DESIRED_DEVICES)} device(s)")

    # --- 2. Inventory: create or update each device (diff before write) -------
    device_ids: dict[str, str] = {}
    for spec in DESIRED_DEVICES:
        device_ids[spec["label"]] = sync_inventory_device(app, spec)

    if DRY_RUN:
        print("Dry run complete — no changes written.")
        return

    # --- 3. Wait until the devices are reachable ------------------------------
    for label, device_id in device_ids.items():
        if wait_until_reachable(app, device_id):
            print(f"{label} is reachable.")

    # --- 4. Topology: add devices at a grid position --------------------------
    # add_devices_to_topology syncs driver-reported ports/vertices by default.
    app.inspect.add_devices_to_topology(
        [(device_id, 1000 + i * 300, 500) for i, device_id in enumerate(device_ids.values())]
    )

    # --- 5. Base configuration + endpoints in one transaction -----------------
    with app.inspect.transaction() as tx:
        for spec in DESIRED_DEVICES:
            device = app.inspect.get_device(device_ids[spec["label"]])
            if device is None:
                continue
            device.label = spec["label"]
            device.tags = [spec["site"]]
            for vertex in device.codec_vertices:
                vertex.use_as_endpoint = True
                vertex.sips_mode = "SIPSAuto"
            app.inspect.update(device, tx=tx)  # cascades the device + its dirty vertices
        tx.commit()

    # --- 6. Connect devices per the cabling data ------------------------------
    for link in DESIRED_LINKS:
        connect_devices(app, device_ids[link["a"]], device_ids[link["b"]], link["bandwidth"])

    # --- 7. Assign each device to its site's security domain ------------------
    domain_names = set(app.security.domains.list_domain_names())
    for spec in DESIRED_DEVICES:
        if spec["site"] not in domain_names:
            app.security.domains.create_domain(name=spec["site"], description=f"Devices at {spec['site']}")
            domain_names.add(spec["site"])
        assign_domain(app, device_ids[spec["label"]], spec["site"])

    print("Onboarding complete.")


def sync_inventory_device(app: VideoIPathApp, spec: dict[str, str]) -> str:
    """Create the device, or update it when its configuration drifted. Returns the device id."""
    existing_id = app.inventory.find_device_id_by_label(spec["label"], label_search_mode="user_defined_label_only")

    if not isinstance(existing_id, str):
        staged = app.inventory.create_device(driver=DRIVER)
        staged.configuration.label = spec["label"]
        staged.configuration.address = spec["address"]
        print(f"  + create {spec['label']} ({spec['address']})")
        if DRY_RUN:
            return "<new>"
        return app.inventory.add_device(staged).configuration.device_id

    reference = app.inventory.get_device(device_id=existing_id, custom_settings_type=DRIVER)
    staged = app.inventory.get_device(device_id=existing_id, custom_settings_type=DRIVER)
    staged.configuration.address = spec["address"]

    diff = app.inventory.diff_device_configuration(reference_device=reference, staged_device=staged)
    if diff.configuration_diff.changed:
        print(f"  ~ update {spec['label']}")
        if not DRY_RUN:
            app.inventory.update_device(device=staged)
    return existing_id


def wait_until_reachable(app: VideoIPathApp, device_id: str, *, attempts: int = 10, delay: int = 3) -> bool:
    """Poll the device status until it reports reachable (bounded retry)."""
    device = app.inventory.get_device(device_id=device_id)
    for _ in range(attempts):
        app.inventory.refresh_device_status(device=device)
        if device.status and device.status.reachable:
            return True
        time.sleep(delay)
    return False


def connect_devices(app: VideoIPathApp, id_a: str, id_b: str, bandwidth: int) -> None:
    """Connect the first free port of each device bidirectionally."""
    device_a, device_b = app.inspect.get_device(id_a), app.inspect.get_device(id_b)
    if device_a is None or device_b is None:
        return
    out_a = next((p.vertex_out for p in device_a.ports if p.vertex_out), None)
    in_b = next((p.vertex_in for p in device_b.ports if p.vertex_in), None)
    if out_a is None or in_b is None:
        return
    app.inspect.connect(out_a.id, in_b.id, bidirectional=True, bandwidth=int(bandwidth * BANDWIDTH_HEADROOM))


def assign_domain(app: VideoIPathApp, device_id: str, domain_name: str) -> None:
    """Ensure the device belongs to exactly the given domain (write only on change)."""
    memberships = app.security.resources.get_device_memberships(device_id=device_id)
    current = set(app.security.resources.convert_domain_ids_to_names(memberships.domains))
    if current != {domain_name}:
        memberships.domains = app.security.resources.convert_domain_names_to_ids([domain_name])
        app.security.resources.update_memberships(memberships=memberships)


if __name__ == "__main__":
    main()
