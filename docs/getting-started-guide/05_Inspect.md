# Inspect App

## 1. Introduction

The **Inspect App** (`app.inspect`) is the read/write interface to VideoIPath's newer *Inspect*
surface: it builds a live view of the topology (devices, ports, edges, and services) and applies
topology changes with a **commit-style** write model.

It is **purely additive** — `app.topology` and `app.inventory` keep working unchanged. Devices are
still onboarded in Inventory first; Inspect then places, connects, and monitors them.

Two ideas shape the API:

- **Skeleton-first snapshots** — a snapshot loads only the minimal topology (all devices and edges,
  without per-port detail) up front, then *lazily hydrates* detail the first time you touch it. This
  keeps the initial read fast even in large environments. A snapshot is never a single point in
  time; each device and section carries its own fetch timestamp.
- **Commit-style writes** — changes are staged and applied atomically. Before sending, the change
  set re-checks that nobody else modified the affected entities (compare-and-commit); after a
  successful commit it refreshes only the touched entities.

> Inspect is verified against VideoIPath **2025.4** and newer. Against older servers the app logs a
> warning; behaviour is unverified.

The app keeps a single topology view internally — you never handle a "snapshot" object. It loads on
your first read and stays current across writes; call `app.inspect.refresh()` to reload it.

## 2. Reading the topology

### 2.1. Devices, ports, and edges

Everything is read straight off `app.inspect`. Skeleton fields are available without any per-device
I/O:

```python
device = app.inspect.get_device("device10")
device = app.inspect.find_device_by_label("BORDERLEAF-26B")

print(device.label, device.coordinates, device.status, device.sync_severity, device.tags)

for device in app.inspect.devices:     # all devices
    print(device.id, device.label)
```

The first access to a device's **ports** hydrates that one device (a single scoped read), then
serves from local state:

```python
for port in device.ports:              # triggers one hydration fetch for this device
    print(port.label, port.vertex_id, port.status, port.tags)
    edge = port.edge                # local edge-skeleton lookup, no I/O
    if edge:
        print("connected to", edge.to_device.label)

for edge in device.edges:              # local, no hydration
    print(edge.from_port, "->", edge.to_port, edge.status)

for other in device.linked_devices:    # local graph walk
    print(other.label)

for edge in app.inspect.edges:      # all external edges
    print(edge.id, edge.status)
```

Hydrate many devices at once (parallel) to avoid N+1 reads:

```python
app.inspect.preload()                            # all devices
app.inspect.preload(["device10", "device11"])    # a subset
```

### 2.2. Services

Services load once as a section, on first access:

```python
for service in app.inspect.services:             # loads the paths section on first touch
    print(service.booking_id)
```

### 2.3. Refreshing

The view updates itself after your own writes. To pick up external changes, reload it:

```python
app.inspect.refresh()                # reload (skeleton; lazy detail)
app.inspect.refresh(load="full")     # reload eagerly in one request
```

## 3. Writing to the topology

### 3.1. Direct writes (auto-commit)

Each direct method opens a one-change transaction and commits it immediately. If the internal view
is already loaded, the change is reflected into it via targeted refresh:

```python
app.inspect.place_device("device12", x=1600, y=9050)
app.inspect.update_device("device12", label="BU-LEAF-A", icon_type="ipSwitchRouter")
app.inspect.update_vertex("device12.1.Ethernet1.out", use_as_endpoint=True)
app.inspect.update_edge(edge_id, weight=10)

# Assign catalog tags to a port (an Inspect-only capability). Tags are referenced by their
# "Category~~name" id; read them back with port.tags.
app.inspect.update_vertex("device12.1.Ethernet1.out", tags=["Video~~1080p50"])

# Module tags use the same setter / update() pattern (backed by assignTag / unassignTag).
module = device.get_module("device12.dev.0")
module.tags = ["Format~~V_720p60"]
app.inspect.update(module)
# or: app.inspect.update_module("device12.dev.0", tags=["Format~~V_720p60"])

app.inspect.connect(
    "device12.1.Ethernet1.out",
    "device7.0.swp1.in",
    bidirectional=True,     # also stages the reverse edge
    capacity=65535,
)
app.inspect.disconnect("device12.1.Ethernet1.out", "device7.0.swp1.in")
app.inspect.remove_device_from_topology("device12")
```

### 3.2. Batched, atomic changes (transaction)

Use a transaction to stage several changes and commit them together:

```python
with app.inspect.transaction() as tx:
    tx.place_device("device12", x=100, y=200)
    tx.connect(a_out, b_in, bidirectional=True)
    tx.remove(edge_id)
    result = tx.commit()          # conflict check → POST → targeted refresh of the internal view

print(result.ok, result.applied_ids)
```

Exiting the `with` block **without** committing discards the staged changes (and logs a warning).

### 3.3. Handling concurrent changes

If another user changed a staged entity since you staged it, `commit()` raises
`InspectCommitConflictError` and sends nothing:

```python
from videoipath_automation_tool.apps.inspect import InspectCommitConflictError

try:
    tx.commit()
except InspectCommitConflictError as exc:
    for conflict in exc.conflicts:
        print(conflict.entity_id, conflict.field_diffs)
    tx.rebase()      # re-fetch baselines, keep your intents
    tx.commit()

# or explicitly force last-writer-wins:
tx.commit(check_conflicts=False)
```

A server-rejected commit (validation or apply gate) raises `InspectCommitError`, which carries the
typed `validation` details.

## 4. Onboarding devices into the topology

```python
from videoipath_automation_tool.apps.inspect import ConflictStrategy

app.inspect.add_devices_to_topology([("device12", 100, 200), "device13"])
info = app.inspect.get_sync_info(["device12"])
app.inspect.sync_devices(["device12"], add_only=True, conflict_strategy=ConflictStrategy.STRICT)
```

## 5. Notes

- Inspect uses **only** the collector API surface at runtime; it never calls the legacy
  `nGraphElements` / `edgesByDevice` endpoints.
- The topology view is loaded lazily and kept internal to `app.inspect`; a pure-write workflow never
  triggers a read. Reads and hydration are internally consistent under concurrent access, but a
  single `VideoIPathApp` is otherwise intended for single-owner use.
- For the design rationale, see the architecture docs under
  [`docs/architecture/inspect-app/`](../architecture/inspect-app/README.md).
