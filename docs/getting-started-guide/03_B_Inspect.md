# 03-B — Inspect App

> **Paired stage:** this page and [03-A Topology](03_A_Topology.md) cover the same
> topology workflows with different implementations. This page is the recommended
> path on VideoIPath **2025.4+**.

**⚠️ BETA ⚠️**: The Inspect App is still in beta. The API and behaviour may change
in future releases. Accessing `app.inspect` emits a `UserWarning` and a log warning.

### Compatibility & deprecation

| Server version | Status |
|---|---|
| VideoIPath **≥ 2025.4** | Supported and recommended (verified) |
| VideoIPath **&lt; 2025.4** | Unverified — the app logs a warning; behaviour is not guaranteed |
| Relation to Topology | Inspect **replaces** `app.topology` going forward |

## 1. Introduction

The **Inspect App** (`app.inspect`) is the read/write interface to VideoIPath's
newer *Inspect* surface: it builds a live view of the topology (devices, ports,
edges, and services) and applies topology changes with a **commit-style** write
model.

Two ideas shape the API:

- **Skeleton-first snapshots** — a snapshot loads only the minimal topology (all
  devices and edges, without per-port detail) up front, then *lazily hydrates*
  detail the first time you touch it. This keeps the initial read fast even in
  large environments. A snapshot is never a single point in time; each device and
  section carries its own fetch timestamp.
- **Commit-style writes** — changes are staged and applied atomically. Before
  sending, the change set re-checks that nobody else modified the affected
  entities (compare-and-commit); after a successful commit it refreshes only the
  touched entities.

The app keeps a single topology view internally — you never handle a "snapshot"
object. It loads on your first read and stays current across writes; call
`app.inspect.refresh()` to reload it.

## 2. Reading the topology

### 2.1. Devices, ports, and edges

Everything is read straight off `app.inspect`. Skeleton fields are available
without any per-device I/O:

```python
device = app.inspect.get_device("device10")
device = app.inspect.find_device_by_label("BORDERLEAF-26B")

print(device.label, device.coordinates, device.tags)
print(device.status.severity if device.status else None, device.sync_severity)
# InspectSeverity is an IntEnum: str(...) → "OK" / "Notice" / …; int(...) / == N still work.
print(device.status_message)           # worst active alarm text, if any
for alarm in device.alarms:            # lazy section load of status/alarms/current
    print(alarm.severity, alarm.message)

for device in app.inspect.devices:     # all devices
    print(device.id, device.label)
```

The first access to a device's **ports** hydrates that one device (a single
scoped read), then serves from local state:

```python
for port in device.ports:              # triggers one hydration fetch for this device
    print(port.label, port.vertex_id, port.status, port.tags)
    edge = port.edge                # local edge-skeleton lookup, no I/O
    if edge:
        print("connected to", edge.to_device.label)

for edge in device.edges:              # local, no hydration
    print(edge.from_port, "->", edge.to_port, edge.status)
    if edge.status:
        print(edge.status.alarm, edge.status.ptp)  # InspectSeverity labels

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

The view updates itself after your own writes and network actions (targeted
scoped re-fetch of touched devices/edges) — you do **not** need to call
`refresh()` after `connect`, `update`, `add_devices_to_topology`, and similar.
Use `refresh()` only to pick up **external** changes (another user/session, or
server-side work outside this app):

```python
app.inspect.refresh()                # reload (skeleton; lazy detail)
app.inspect.refresh(load="full")     # reload eagerly in one request
```

## 3. Writing to the topology

### 3.1. Direct writes (auto-commit)

Each direct method opens a one-change transaction and commits it immediately. If
the internal view is already loaded, the change is reflected into it via targeted
refresh:

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
    device.description = "Rack A leaf"
    tx.update(device)             # stage setter edits into the transaction
    tx.place_device("device12", x=100, y=200)
    tx.connect(a_out, b_in, bidirectional=True)
    tx.remove(edge_id)
    result = tx.commit()          # conflict check → POST → targeted refresh of the internal view

print(result.ok, result.applied_ids)
```

Exiting the `with` block **without** committing discards the staged changes (and
logs a warning).

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

A server-rejected commit (validation or apply gate) raises `InspectCommitError`,
which carries the typed `validation` details.

## 4. Onboarding devices into the topology

`add_devices_to_topology` places devices and, by default, syncs their
driver-reported ports/vertices in one call:

```python
from videoipath_automation_tool.apps.inspect import ConflictStrategy

app.inspect.add_devices_to_topology([("device12", 100, 200), "device13"])
# Pass sync=False to place only; or override sync options:
# app.inspect.add_devices_to_topology(
#     ["device12"], sync=True, add_only=True, conflict_strategy=ConflictStrategy.STRICT
# )

# Preview what a later re-sync would change, then re-sync existing devices:
info = app.inspect.get_sync_info(["device12"])
app.inspect.sync_devices(["device12"], add_only=True, conflict_strategy=ConflictStrategy.STRICT)
```

## 5. Maintenance bookings

Maintenance methods execute immediately, independently of `transaction()` and
`commit()`. These examples use an existing `app` instance and a dedicated test
device named `device-a`.

### Prepare a one-time booking

Describe the selected resources, the time window, and the booking metadata.
Creating these Python objects does not change anything on the server.

```python
from datetime import UTC, datetime, timedelta

from videoipath_automation_tool.apps.inspect import (
    MaintenanceBookingSpec,
    MaintenanceOnceSchedule,
    MaintenanceTargets,
)

# Select the resources that the maintenance will affect.
device = app.inspect.get_device("device-a")

if device is None:
    raise ValueError("Create or select a test device before running this example.")

targets = MaintenanceTargets(devices=[device])


# Define one future window using timezone-aware datetimes.
now = datetime.now(UTC)

schedule = MaintenanceOnceSchedule(
    start=now + timedelta(days=1),
    end=now + timedelta(days=1, hours=2),
)


# Combine the metadata, resources, and schedule into a complete specification.
spec = MaintenanceBookingSpec(
    label="maintenance-a",
    tags=["maintenance-example"],
    targets=targets,
    schedule=schedule,
)
```

Targets accept canonical resource IDs or matching Inspect domain objects. String
module/port IDs must be globally qualified PIDs, not display labels or local keys.

Defaults match the UI: no overlap, `action="nothing"`, `trigger="create"`, and no
format switching. Supported actions are `nothing`, `invalidate`, `reroute`, and
`rerouteSA`; triggers are `create` and `active`.

### Preview and create

Previewing is read-only. Call the creation method separately when ready to write.

```python
# Preview groups reports by affected service ID, with one report per affected window.
preview = app.inspect.validate_maintenance_booking(spec)
print("Preview:", preview)


# Create immediately and keep the IDs returned by the server.
created = app.inspect.create_maintenance_booking(spec)
booking_ids = list(created.details)

# Do not infer booking IDs from labels or success messages.
if not booking_ids:
    raise RuntimeError("No booking IDs returned; inspect server state before retrying.")
```

### Read and filter

```python
# Fetch one booking by its server ID.
booking = app.inspect.get_maintenance_booking(booking_ids[0])

if booking is None:
    raise RuntimeError("The booking is not visible; refresh before continuing.")

print(booking.label, booking.state, booking.starts_at, booking.ends_at)


# Search labels and tags, optionally limiting the state.
scheduled = app.inspect.find_maintenance_bookings(
    state="scheduled",
    search="maintenance-example",
)


# Current impact is grouped by booking ID, then by affected service ID.
impact = app.inspect.get_maintenance_impact(booking_ids)
print("Current impact:", impact)
```

`maintenance_bookings` reads all bookings. `find_maintenance_bookings(state="all",
search="")` supports `all`, `active`, and `scheduled`, with case-insensitive label/tag
search. `get_maintenance_booking(id)` returns `None` when absent. The collection is
loaded once per snapshot without device hydration; full snapshots reuse their
existing maintenance data. Call `refresh()` to observe changes from other clients.

Bookings expose `rev`, `label`, `description`, `tags`, `state`, `locked`, action
settings, `starts_at`/`ends_at`, and selected `devices`, `modules`, `ports`, and `edges`.
Unknown numeric states remain available as integers. `raw` retains unresolved
resource contexts and PID segments, even if the corresponding topology object is
missing.

Resource objects expose `.maintenance_bookings`; device/module relationships
also include explicitly selected descendants and edge endpoints. Ancestor bookings
are available on that ancestor rather than repeated on every descendant.

### Update, lock, start, and delete

Updates require the complete specification and an explicit one-time schedule for
the booking ID. They fetch the current booking revision before posting.

`locked=None` preserves its fresh lock state; booleans change it. `expected_rev`
raises `InspectMaintenanceConflictError` before writing if the revision differs.

```python
# Lock the booking only if its revision still matches the one we read.
app.inspect.update_maintenance_booking(
    booking.id,
    spec,
    locked=True,
    expected_rev=booking.rev,
)


# Reuse the complete specification, changing only the intended schedule.
# An omitted start means "now" on the server; end is an explicit timestamp.
immediate_schedule = MaintenanceOnceSchedule(
    end=datetime.now(UTC) + timedelta(hours=1),
)

start_now = spec.model_copy(update={"schedule": immediate_schedule})

app.inspect.update_maintenance_booking(
    booking.id,
    start_now,
    locked=False,
)


# Delete the explicit IDs created by this example.
app.inspect.delete_maintenance_bookings(booking_ids)
```

`MaintenanceOnceSchedule(start=None, end=...)` starts now; `end=None` is open-ended.
Supply timezone-aware datetimes; the SDK converts them to epoch milliseconds.

### Recurring schedules

```python
from datetime import time

from videoipath_automation_tool.apps.inspect import MaintenanceRecurringSchedule

# Define a finite rule. Other supported frequencies are "daily" and "monthly".
rule = MaintenanceRecurringSchedule(
    frequency="weekly",

    # Only complete windows within these bounds will be included.
    start=datetime(2030, 1, 1, tzinfo=UTC),
    end=datetime(2030, 2, 1, tzinfo=UTC),

    # Repeat the local window every Monday and Friday in this timezone.
    timezone="Europe/Berlin",
    local_start=time(4),
    local_end=time(5),
    weekdays=[1, 5],  # ISO Monday=1; use weekdays only for weekly rules.
)

recurring_spec = spec.model_copy(update={"schedule": rule})


# Inspect the individual dates before contacting the server.
windows = rule.expand()

for window in windows:
    print(window.start, window.end)


# Preview each window, then create all dated bookings in one write action.
preview = app.inspect.validate_maintenance_booking(recurring_spec)
print("Recurring preview:", preview)

created = app.inspect.create_maintenance_booking(recurring_spec)
recurring_ids = list(created.details)


# Each occurrence has its own ID. Remove the example occurrences when finished.
if recurring_ids:
    app.inspect.delete_maintenance_bookings(recurring_ids)
```

On the verified server, native recurring maintenance requests created a broad window
that could not subsequently be updated. The SDK therefore expands rules into dated
one-time bookings and creates them in one action. Each has an independent server ID
in `created.details`. Preview makes one read-only request per window. Keep the rule
in your application if needed: collector windows do not preserve recurrence intent.

Update, lock, start, and delete individual IDs; there is no series-management API.

The expansion rules are:

- **Bounds:** include only complete windows within the finite range, up to 1,000.
- **Monthly dates:** use the local start date's day and skip months without that day.
- **Overnight windows:** an end time earlier than the start time crosses midnight.
- **Daylight saving time:** reject missing local times; use the first occurrence
  when a local time is ambiguous.
- **Iteration filters:** raw transport models preserve `iterationFilter`, but
  expansion rejects nonempty filters because their server-specific semantics
  are unverified.

### Errors and cached reads

`InspectMaintenanceError` includes `operation`, `booking_ids`, `detail`, and
`response`. Both envelope and operation failures are checked. Writes are never
automatically retried after an uncertain transport failure.

A successful write invalidates maintenance/status/service caches without clearing staged topology
edits or making follow-up reads; a later refresh failure cannot hide that success.

See the [complete maintenance example](../examples/04_inspect/04_maintenance_bookings.py).

## 6. Notes

- Inspect uses the Inspect API surface, including its maintenance actions; it never calls the
  legacy `nGraphElements` / `edgesByDevice` endpoints.
- The topology view is loaded lazily and kept internal to `app.inspect`; a
  pure-write workflow never triggers a read. Reads and hydration are internally
  consistent under concurrent access, but a single `VideoIPathApp` is otherwise
  intended for single-owner use.
- Runnable paired scripts (Inspect vs Topology) live under
  [`docs/examples/03_topology_and_inspect/`](../examples/03_topology_and_inspect/).
- For the design rationale, see the architecture docs under
  [`docs/architecture/inspect-app/`](../architecture/inspect-app/README.md).
