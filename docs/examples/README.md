# Examples

Runnable, task-oriented example scripts for the VideoIPath Automation Tool. Each file is a
self-contained Python script with a module docstring (title, description, prerequisites, related
examples) and numbered sections, showing how to solve one realistic automation scenario.

Where the [Getting Started Guide](../getting-started-guide/README.md) explains concepts, these
examples show complete workflows you can copy and adapt.

## Running an example

```bash
pip install videoipath-automation-tool
python docs/examples/01_setup/01_connect_and_check.py
```

Each script has a small block of placeholder constants near the top (`SERVER_ADDRESS`, `USERNAME`,
`PASSWORD`, device labels, …) — edit these for your environment. Alternatively, set the `VIPAT_*`
environment variables (or a `.env` file) and connect with a bare `VideoIPathApp()`; see
[01_connect_and_check.py](01_setup/01_connect_and_check.py).

All identifiers in these examples are anonymized placeholders (`device-a`, `leaf-1`, `192.0.2.x`,
`site-a`, …). **The examples write to the server — run them against a test system first.** The
read-only scripts ([04_inspect/01](04_inspect/01_explore_topology_read_only.py),
[06_workflows/02](06_workflows/02_network_audit_report.py)) are safe starting points.

## Compatibility and conventions

- **Inspect app** (`app.inspect`) is the forward-looking read/write interface and requires
  **VideoIPath 2025.4 or newer**.
- **Topology app** (`app.topology`) is **deprecated on VideoIPath 2025.x** and **unsupported on
  2026.x**, where its constructor raises `TopologyUnsupportedError`. Prefer the Inspect variant of a
  scenario on modern servers.
- **Recommended write style (Inspect):** edit a domain object's properties and flush with
  `app.inspect.update(obj)`. The keyword-argument methods (`app.inspect.update_device(...)`,
  `update_vertex(...)`, …) do the same in one call and are shown as an alternative where relevant.

## Contents

### 01 — Setup

- [01_connect_and_check.py](01_setup/01_connect_and_check.py) — connect (constructor args or `VIPAT_*`
  env vars), verify the connection, read the server version.

### 02 — Inventory

- [01_create_and_add_device.py](02_inventory/01_create_and_add_device.py) — create a device from a
  driver, set typed `custom_settings`, add it.
- [02_get_update_and_diff_device.py](02_inventory/02_get_update_and_diff_device.py) — fetch, diff, and
  update a device; idempotent "write only on change".
- [03_discovery_onboarding.py](02_inventory/03_discovery_onboarding.py) — onboard auto-discovered
  devices; enable/disable.
- [04_backup_restore_clone.py](02_inventory/04_backup_restore_clone.py) — dump/parse a configuration to
  back up, restore, or clone a device (same or second server).
- [05_driver_settings_and_queries.py](02_inventory/05_driver_settings_and_queries.py) — typed driver
  settings, inventory queries, global SNMP configuration.

### 03 — Topology and Inspect (paired examples)

Each scenario is implemented twice — once with the modern **Inspect** app, once with the classic
**Topology** app — using identical data, so you can compare the two approaches side by side.

| Scenario | Inspect | Topology |
|---|---|---|
| Device lifecycle: add, configure, remove | [01_device_lifecycle_inspect.py](03_topology_and_inspect/01_device_lifecycle_inspect.py) | [01_device_lifecycle_topology.py](03_topology_and_inspect/01_device_lifecycle_topology.py) |
| Configure vertices (endpoints, SIPS, tags) | [02_configure_vertices_inspect.py](03_topology_and_inspect/02_configure_vertices_inspect.py) | [02_configure_vertices_topology.py](03_topology_and_inspect/02_configure_vertices_topology.py) |
| Connect two devices with edges | [03_connect_devices_with_edges_inspect.py](03_topology_and_inspect/03_connect_devices_with_edges_inspect.py) | [03_connect_devices_with_edges_topology.py](03_topology_and_inspect/03_connect_devices_with_edges_topology.py) |
| Lay out devices in a grid | [04_grid_placement_inspect.py](03_topology_and_inspect/04_grid_placement_inspect.py) | [04_grid_placement_topology.py](03_topology_and_inspect/04_grid_placement_topology.py) |
| Create a virtual (driverless) device | [05_virtual_device_inspect.py](03_topology_and_inspect/05_virtual_device_inspect.py) | [05_virtual_device_topology.py](03_topology_and_inspect/05_virtual_device_topology.py) |

### 04 — Inspect (app-specific strengths)

- [01_explore_topology_read_only.py](04_inspect/01_explore_topology_read_only.py) — read-only tour:
  devices, edges, ports, neighbours; skeleton vs. full loading, `preload`.
- [02_transactions_and_conflicts.py](04_inspect/02_transactions_and_conflicts.py) — atomic batched
  changes; detect concurrent edits and `rebase` + retry.
- [03_services_and_paths.py](04_inspect/03_services_and_paths.py) — inspect services, their paths, and
  the service-impact guard.

### 05 — Administration

- [01_security_domains_and_memberships.py](05_administration/01_security_domains_and_memberships.py) —
  reconcile security domains and a device's domain memberships.
- [02_profiles.py](05_administration/02_profiles.py) — list, create, clone, and remove profiles.
- [03_multicast_pools.py](05_administration/03_multicast_pools.py) — read, create, extend, and remove
  multicast allocation pools.

### 06 — Workflows (composite, real-world)

- [01_full_onboarding_pipeline.py](06_workflows/01_full_onboarding_pipeline.py) — end-to-end sync from
  an external source of truth: inventory → reachability → topology → edges → domains, with a dry-run
  flag and diff-before-write.
- [02_network_audit_report.py](06_workflows/02_network_audit_report.py) — read-only cross-app audit
  report (safe to run against production).
- [03_bulk_retag_and_relabel.py](06_workflows/03_bulk_retag_and_relabel.py) — apply a naming/tagging
  policy across a fleet with a dry-run report and a single batched commit.
