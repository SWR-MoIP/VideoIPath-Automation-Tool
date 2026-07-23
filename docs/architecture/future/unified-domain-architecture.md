# Unified Domain Architecture (proposed)

> Status: **Draft / Vision** · Last updated: 2026-06-18
>
> This document proposes a **package-wide** re-think: present **one unified
> domain model** in which the user simply **creates devices, configures them,
> and connects them** — without ever needing to know about the `inventory`,
> `topology`, or `inspect` apps, which VideoIPath (VIP) store or endpoint is
> involved, or how the work is split across planes.
>
> It stands in deliberate contrast to the current
> [`python-module-architecture.md`](../python-module-architecture.md), whose
> stated goal is to *"maintain a structure similar to VideoIPath."* That goal is
> exactly what this proposal revisits. The VIP wire format and per-app research
> this builds on lives in [`inspect-app/`](../inspect-app/README.md)
> (`concepts.md` and the ADRs); those documents remain the **faithful map of the
> server**, while this one is the **map we want to present to users**.
>
> Nothing here is implemented yet. This is the target picture and the decisions
> required to get there.

## 1. The idea in one sentence

> The user works with a **network of devices and connections**. *Where* that
> lives in VideoIPath — Inventory onboarding, Topology placement, Inspect
> monitoring, which REST/RPC endpoint, which store — is an **implementation
> detail** the package owns, not the user.

Today the user must learn the VIP product structure and drive it step by step:

```python
# Today: the user orchestrates VIP's app/plane split by hand
staged = app.inventory.create_device(driver="com.nevion.NMOS_multidevice-0.1.0")
staged.configuration.address = "10.100.100.1"
device = app.inventory.add_device(staged)              # plane 1: Inventory (RPC)

topo = app.topology.get_device(device.device_id)       # plane 2: Topology (nGraphElements)
topo.configuration.position_x = 100
app.topology.update_device(topo)

edges = app.topology.create_edges(...)                 # plane 2/3: edges
# ... monitor via the collector aggregate ...          # plane 3: Inspect
```

The proposed surface:

```python
# Proposed: one domain, the package orchestrates the planes
dev = app.add_device(driver="...", address="10.100.100.1", label="Cam-1", position=Position(x=100, y=200))
app.connect_devices(dev.port("Eth 1.10"), other.port("Eth 1.11"), bandwidth=Gbps(10))
```

## 2. Why a unified domain

The package today is a **transparent client**: its public surface speaks VIP's
own vocabulary — `BaseDevice`, `IpVertex`, `UnidirectionalEdge`,
`nGraphElements`, `_rev`, `fromId::toId` — and exposes VIP's **app split**
(`inventory` / `topology` / `inspect`). The user must know *which VIP app does
what*: onboard in Inventory → place/connect in Topology → monitor in Inspect,
while Inspect writes land back in `nGraphElements`.

This is awkward for reasons confirmed against a real server (see
[`inspect-app/concepts.md`](../inspect-app/concepts.md) and the captured
`collector` payload):

1. **The app split is VIP's internal structure, not the user's mental model.**
   "Onboard, then place, then connect, then monitor" is a property of VIP's
   architecture. Users think "I have devices and I want to connect them."
2. **VIP already hides its own stores behind facades.** The `collector`
   aggregate composes the raw stores server-side. Mirroring the raw stores in
   Python re-exposes a detail the vendor themselves chose to hide.
3. **The wire format is unstable and version-gated** (the package version-gates
   endpoints and carries many `[VERIFY]` items). A transparent client passes
   that instability straight through to users; one domain surface absorbs it in
   a single place.
4. **One real device is fragmented across three models today** —
   `InventoryDevice`, `TopologyDevice`, and the Inspect node — each a partial
   view. A unified `Device` re-assembles the whole.
5. **The same entity has three+ wire representations** — the `collector` read
   shape, the `updateTopology` delta, and the `nGraphElements` store. A
   user-facing model that picks **one** domain representation and translates
   internally is strictly simpler.

This is a textbook case for an **anti-corruption layer (ACL)**: a stable domain
model with a hard boundary, behind which all VIP-specific translation lives.

## 3. Verdict & guiding principle

**Abstract VIP away — but as an explicit layered ACL, not a thin rename.** The
discipline:

- The **domain layer never imports or returns a wire/app type.** Translation
  lives only in the ACL.
- The domain model is **stable**; version churn is absorbed by ACL adapters,
  selected by the existing version-check machinery — never by branching in user
  code or in the domain types.
- We deliberately decide, per concept, **what to hide vs. what to expose** (§13).
  Some semantics (commit, validation, conflict) are first-class domain
  behaviour; others (edge pairing, key formats, namespaces, the app split) are
  hidden.
- The existing apps remain the documented **escape hatch** for raw access —
  keeping the change **additive and non-breaking**.

> **What an ACL can and cannot hide.** Renaming fields (`unidirectionalEdge` →
> `Connection`) is trivial. Hiding *semantics* is the hard part and must be a
> conscious choice: a connection being two paired unidirectional edges (hide),
> commit validation that can fail after HTTP success (expose), optimistic
> concurrency via revisions (expose, but as an opaque token), driver-specific
> configuration schemas (cannot be hidden — see §12). A good ACL chooses; it
> does not pretend the semantics don't exist.

## 4. Target architecture

```text
┌────────────────────────────────────────────────────────────────┐
│  Unified Domain API (NEW default surface)                        │  ← what users touch
│  app.network: Device, Port, Connection, Service, Status          │     one model, one vocabulary
│  lifecycle: discover → onboard → place → connect → monitor       │     stable, version-independent
├────────────────────────────────────────────────────────────────┤
│  Orchestration + Anti-corruption layer                           │  ← sequences plane operations,
│  domain ⇄ {inventory RPC, topology PATCH, collector/updateTopo}  │     translates & maps ids; no I/O state
├────────────────────────────────────────────────────────────────┤
│  Existing apps (now the LOW-LEVEL layer / escape hatch)          │  ← unchanged, still public
│  app.inventory · app.topology · app.inspect · app.profile · …    │     faithful to VIP
├────────────────────────────────────────────────────────────────┤
│  Connector (REST v2 + RPC)                                        │
└────────────────────────────────────────────────────────────────┘
```

Key properties:

- **`app.network` is the new default**; the per-app surfaces are demoted to a
  documented **low-level layer / escape hatch**, not removed.
- **Orchestration is a core responsibility**: a single domain call may fan out
  to **several planes in sequence** (e.g. `add_device` = Inventory RPC add →
  optional Topology placement).
- The ACL is **pure translation** — no I/O, no transport state. It maps between
  domain objects and wire DTOs, so the wire models can change shape without
  touching the domain types.

## 5. The device lifecycle

The hardest part of a package-wide abstraction is owning the **onboarding
lifecycle**, which today is an explicit, ordered prerequisite chain (devices are
onboarded in Inventory first, only then placed/connected).

Model the lifecycle explicitly on the domain `Device` so the user can reason
about *where* a device is without knowing *which app*:

| Domain state | Meaning | VIP reality (hidden) |
| ------------ | ------- | -------------------- |
| `Discovered` | Auto-found, not yet managed | Inventory discovered devices |
| `Onboarded` | Known/credentialed, driver bound | Inventory `config/devman/devices` (RPC `/api/updateDevices`) |
| `Placed` | Positioned in the network graph | Topology `baseDevice` in `nGraphElements` |
| `Connected` | Has connections to other devices | `unidirectionalEdge` / `updateTopology` |
| `Monitored` | Live status/services available | `collector` aggregate + WebSocket |

`add_device(...)` advances a device from nothing → `Onboarded` (and optionally
→ `Placed` in the same call). `connect(...)` advances to `Connected`. The user
sees one object moving through states; the package picks the endpoints.

> **This is also where the abstraction is hardest** — see §12 (limits). Some
> lifecycle inputs (driver choice, credentials, per-driver custom settings) are
> genuinely device-specific and cannot be fully hidden.

## 6. The unified domain model

One `Device` re-assembles what is today three partial models. The whole
vertex/edge/element taxonomy collapses into a handful of nouns. These are
**proposals**, not final signatures:

```python
# Domain model — intentionally NOT mirroring nGraphElements / collector DTOs.

class Device:
    id: DeviceId                 # opaque; internally "device34" / "virtual.3"
    label: str
    driver: DriverRef            # required for onboarding (see §12)
    connection: ConnectionInfo   # address(es), credentials, driver custom settings
    state: LifecycleState        # §5
    position: Point | None       # placement; hides maps[]/meta.coordinates/inspect_app_format
    ports: list[Port]            # capabilities (merges vertices + collector ports)
    status: DeviceStatus         # merges inventory status + collector node status
    sync: SyncState              # from nodeStatus.syncSeverity
    tags: list[str]

class Port:                      # hides ipVertex/codecVertex/genericVertex + vertexInfo single|double
    id: PortId
    label: str
    direction: Direction         # IN | OUT | BIDIRECTIONAL (hides .in/.out vertex split)
    kind: PortKind               # IP | CODEC | GENERIC
    is_endpoint: bool
    status: PortStatus

class Connection:                # ONE user-facing connection == the paired unidirectional edges
    id: ConnectionId             # "deviceA::deviceB" pair identity
    a: PortRef
    b: PortRef
    forward: DirectionState      # primary: bandwidth, status
    reverse: DirectionState      # secondary: bandwidth, status (may differ!)
    redundancy: Redundancy
    status: ConnectionStatus     # rolled up from alarm/bandwidth/maintenance/ptp

class Service:                   # a booking/path (collector inspect.paths)
    id: ServiceId                # "100001"
    label: str                   # "Encoder 1.1 -> Decoder 1.5"
    endpoints: tuple[Endpoint, Endpoint]
    is_main: bool
    status: ServiceStatus
```

Design principles:

- **Opaque ids** (`DeviceId`, `PortId`, `ConnectionId`) are value objects, not
  raw strings. They internally carry every wire form (§7). Users never construct
  ids by string-mangling.
- **A `Connection` is singular** — the single most valuable abstraction. Hide
  that an inter-device connection is two `unidirectionalEdge`s plus internal
  fan-out. Carry **per-direction state** because the two directions are
  genuinely asymmetric (the capture shows forward `bandwidth: 20.0`, reverse
  `0.0`).
- **Status is a first-class, read-only projection**, separate from config. This
  matches the config-plane vs. status-plane split
  ([ADR-001](../inspect-app/decisions/001-api-paradigm.md)) and keeps the live
  story clean.
- **Make illegal states unrepresentable** where cheap (enums for `Direction`,
  `PortKind`, `Redundancy`, `LifecycleState`, `SyncState`).

## 7. Identifiers — the "id zoo" and why ids must be opaque

A single physical port appears under **four to five** id schemes, all visible in
one collector payload (and inventory adds its own device-id assignment on top).
For device0's "Eth 1.10":

| Form | Example | Where it appears |
| ---- | ------- | ---------------- |
| Port pid | `device0.dev.1.10` | `nodeStatus` module/port keys, `context.portPid` (note the `.dev.` infix) |
| Vertex id (in/out) | `device0.1.10.in` / `device0.1.10.out` | `vertexInfo.in/out.id`, edge keys (**no** `.dev.`) |
| Resource id | `device:device0.dev.1.10` | `resourceId`, `security.*` |
| Topo endpoint ref | `topo:device0.1.1` | `serviceFields.from` / `.to` |
| Connection pair key | `device0::device1` | `externalEdgesByDeviceKey._id` |
| Edge key | `device0.1.10.out::device1.1.11.in` | edge ids, `replaceEdges` |
| Service id | `100001::main` | `inspect.paths`, `pathDescriptions` keys |

Translating "the port a user names" → "the vertex id an edge key needs" is a
non-trivial, lossy-if-sloppy transform (`device0.dev.1.10` →
`device0.1.10.{in|out}`). **Therefore ids are value objects that hold all
forms.** String-mangling these in user code — especially the `.dev.` infix —
is the most likely source of subtle bugs.

## 8. Reads — the collector snapshot as the aggregate root

The `collector` tree is the aggregate root for reads. Loading follows
[ADR-005](../inspect-app/decisions/005-lazy-snapshot-loading.md):
a **skeleton** query pair fetches the whole graph structure (all devices
without module/port detail + all edges with a lean projection) in one
consistent round, and per-device subtrees are **lazily hydrated** on demand.
The rule: never rebuild the *graph structure* from N per-device fetches — the
skeleton delivers it at once; per-device fetches are only for drill-down
detail. The full `GET …/data/status/collector/**` aggregate remains the eager
mode when a point-in-time view of everything is needed. For onboarding-only
attributes not in the collector (driver, credentials, custom settings), the
ACL supplements with an Inventory read.

The cost is **heavy denormalization**. A single service (`100001::main`)
appears in at least six places in the snapshot, each with full status
sub-objects:

- `inspect.paths._items[]` (canonical path + `serviceFields`)
- `externalEdgesByDeviceKey[].primary.data[…].pathDescriptions`
- `nodeStatus` source-endpoint port (`device0.dev.1.1`)
- `nodeStatus` egress port (`device0.dev.1.10`)
- `nodeStatus` ingress port (`device1.dev.1.11`)
- `nodeStatus` sink-endpoint port (`device1.dev.1.5`)

**Rule:** pick **one canonical source per domain object**; treat the rest as
drill-down breadcrumbs. Building a domain object from each occurrence yields
divergent copies.

| Domain object | Canonical source |
| ------------- | ---------------- |
| `Device` / `Port` | `inspect.nodeStatus._items[]` → `modules.*.ports.*` (+ inventory for onboarding fields) |
| `Connection` | `externalEdgesByDeviceKey._items[]` |
| `Service` | `inspect.paths._items[]` (+ `serviceFields`) |
| port ↔ service drill-down | `ports.*.pathDescriptions` (reference only — do not re-model) |

### 8.1 Connections are pre-paired by the server

`externalEdgesByDeviceKey._items[]` already groups the two unidirectional edges
under one bidirectional key:

- `_id: "device0::device1"` — the connection identity
- `primary` → `device0.1.10.out::device1.1.11.in` (forward direction)
- `secondary` → `device1.1.11.out::device0.1.10.in` (reverse direction)

So the `Connection` deduplication problem is solved on the read side: the `a::b`
key is the identity, and `primary` / `secondary` are the two `DirectionState`s.
The directions carry **independent** `bandwidth` / `fromStatus` / `toStatus` /
`status`, so the domain `Connection` must keep both, plus the top-level
aggregate `status` the collector provides.

## 9. Operation → plane mapping (orchestration)

Each domain operation expands to an ordered sequence of existing wire
operations. The ACL owns this table; the user never sees it.

| Domain operation | Orchestrated VIP sequence |
| ---------------- | ------------------------- |
| `network.discover()` | Inventory discovered-devices read |
| `network.add_device(driver, connection, …)` | Inventory RPC `/api/updateDevices` (assigns `deviceN`) → optional placement via `addDevices` network action / `updateTopology` `replaceDevices` |
| `device.configure(...)` | Inventory custom-settings update (RPC) and/or `updateTopology` `replaceVertices` — by field |
| `device.place(x, y)` | `updateTopology` `replaceDevices` (coordinates) |
| `network.connect(a, b, …)` | Resolve port→vertex ids → `updateTopology` `replaceEdges` / `addExternalEdges` (paired edges) |
| `network.get(...)` / `list_*()` | `collector` snapshot read (+ inventory status where needed) |
| `network.disconnect(...)` / `remove_device(...)` | `updateTopology` `remove` and/or Inventory RPC remove |
| `device.refresh()` / `network.refresh()` | Re-fetch `collector` snapshot (§11.3); after own commits: targeted refresh ([ADR-008](../inspect-app/decisions/008-post-commit-snapshot-refresh.md)) |

All topology-plane operations go through the **Inspect surface only**
(`updateTopology`, collector reads, `addDevices`/`syncDevices`) — never through
`PATCH nGraphElements`
([ADR-006](../inspect-app/decisions/006-collector-only-endpoints.md)). The
legacy Topology path remains available solely via the `app.topology` escape
hatch.

## 10. The configuration / write interface

Make the **change set the unit of work** — this is genuinely how the server
behaves for topology/connection edits
([ADR-004](../inspect-app/decisions/004-commit-write-model.md)), so it is a
semantic to **expose**, not hide. Adopt ADR-004 option 3 (explicit change set +
convenience auto-commit), with a context manager as the ergonomic default.
Proposed shape:

```python
# Batched, atomic — the primary path
with app.network.change_set() as cs:
    cs.place(device_id, at=Point(x, y))
    conn = cs.connect(port_a, port_b, bandwidth=Gbps(10), redundancy=Redundancy.ANY)
    cs.remove(old_connection_id)
    result = cs.validate()          # client-side conflict check (ADR-007); server validation runs at commit
    if result.ok:
        cs.commit()                 # conflict re-check → one updateTopology POST → targeted refresh (ADR-008)
# on exception → auto-discard; on clean exit without commit → configurable

# Convenience — single change auto-commits
app.network.connect(port_a, port_b, bandwidth=Gbps(10))
```

What the domain layer owns (and the ACL translates):

- **Commit ≠ HTTP success.** A captured failed delete returned `header.ok: true`
  but `data.res.ok: false` / `data.validation.result.ok: false` (ADR-004).
  This must surface as a typed `CommitResult` / `CommitFailed` carrying the
  per-entity validation details (`status`, `rev`, `resolvable`, message) —
  never a raw envelope.
- **Affected-services check** — already a precedent in
  `TopologyApp.list_services_affected_by_device_update`. In the domain model it
  becomes `change_set.validate()` returning structured impact.
- **Diffing stays internal.** Users describe *intent* (`connect`, `remove`);
  the ACL computes the delta. The existing diff logic becomes an implementation
  detail of staging.

## 11. Writes & freshness across planes

The Inspect-era findings hold and become **more pronounced** because three
planes are now in play.

### 11.1 Writes span three concurrency models

The three planes do **not** share a write/consistency model:

| Plane | Write mechanism | Concurrency control |
| ----- | --------------- | ------------------- |
| Inventory | RPC `/api/updateDevices` | No revision/strict mode (RPC semantics) |
| Topology (escape hatch only, [ADR-006](../inspect-app/decisions/006-collector-only-endpoints.md)) | `PATCH nGraphElements` | `_rev` optimistic locking, `mode: strict` |
| Inspect | `updateTopology` action | Commit-time validation; **last-writer-wins** (verified 2025.4.9 — `_rev` ignored); client-side compare-and-commit ([ADR-007](../inspect-app/decisions/007-write-consistency.md)) |

So a single domain write that touches multiple planes has **no single
transaction and no uniform conflict story**. The ACL must define, per
orchestrated operation: ordering, what happens on partial failure midway through
the sequence, and how each plane's conflict surfaces as **one** domain error.
Lean on the change-set/commit model for the topology/inspect portion; onboarding
(Inventory RPC) is a separate step that must be sequenced and compensated
explicitly if a later step fails.

### 11.2 The collector carries no `_rev`

Every collector `_items[]` entry has `_id` / `_vid` and **no `_rev`** — it is a
pure status-plane projection. The revisioned source of truth lives only in the
config plane (`nGraphElements`). Consequences:

1. **Status changes move no token.** Alarms, `ptp` severity, `bandwidth`,
   `syncSeverity` are not backed by any revision. There is **no cheap "did
   anything change?" probe** for status — the only ways to learn current status
   are to re-fetch the collector (whole or subtree) or subscribe via WebSocket
   ([ADR-001](../inspect-app/decisions/001-api-paradigm.md)).
2. **Config-plane rev-polling is off the table anyway.** Polling
   `nGraphElements .../id,rev` could catch "someone re-wired" (never "a
   connection went into alarm"), but the package does not call that surface
   ([ADR-006](../inspect-app/decisions/006-collector-only-endpoints.md)) —
   and it would still miss the status changes that matter for monitoring.
3. **There is no write token at all on the Inspect surface.** The collector
   read is rev-less and `updateTopology` ignores `_rev` (last-writer-wins,
   verified 2025.4.9) — so revision-based optimistic writes are impossible,
   not merely inconvenient. A domain object built from the collector **cannot
   support an optimistic write**; concurrent-edit detection is the change
   set's job via stage-time baselines + pre-commit compare
   ([ADR-007](../inspect-app/decisions/007-write-consistency.md)).

### 11.3 Freshness strategy — re-snapshot, not rev-diff

The collector deliberately trades per-entity revisioning for a single
globally-consistent snapshot — excellent for **read correctness** (no torn
graph), poor for **incremental freshness**. Therefore:

- The collector snapshot is **replaced wholesale on `refresh()`** — never
  patched by diffing. Within its lifetime it *accretes*: skeleton-first, with
  lazily hydrated subtrees merged in
  ([ADR-005](../inspect-app/decisions/005-lazy-snapshot-loading.md)).
- `refresh()` means "fetch a new snapshot," not "diff revisions." Stamp each
  entity/section with a **client-side fetch time** as the freshness marker,
  since the server provides no token.
- Projection/filtering on collector sub-paths is **proven** (Inspect UI
  WebSocket capture — see
  [endpoints.md](../inspect-app/endpoints.md#collector-scoped-queries-captured-from-the-inspect-ui)):
  scoped re-snapshots of a subtree are the freshness optimisation — still a
  re-snapshot, not a diff.
- **After the package's own commits**, freshness is cheaper: the change set
  knows what it touched, so the snapshot is updated by targeted invalidation +
  scoped re-fetch instead of a full re-snapshot
  ([ADR-008](../inspect-app/decisions/008-post-commit-snapshot-refresh.md)).
- This is the strongest argument for making **WebSocket the real freshness
  channel for status**, while config edits keep the rev-based path
  ([ADR-001](../inspect-app/decisions/001-api-paradigm.md),
  [ADR-005](../inspect-app/decisions/005-lazy-snapshot-loading.md)).

### 11.4 Separate the read snapshot from the write handle

Because the snapshot has no revisions (and the write path enforces none), a
domain mutation (`connect`, `remove`) must not pretend a read object can
optimistically write. The clean split:

- **Read snapshot** — rev-less, replace wholesale on refresh; accretes lazily
  hydrated detail within its lifetime (ADR-005); after own commits it is
  updated by targeted scoped re-reads
  ([ADR-008](../inspect-app/decisions/008-post-commit-snapshot-refresh.md)).
- **Write handle / change set** — fetches stage-time baselines via
  Inspect-surface lookups, re-checks them immediately before the
  `updateTopology` POST, and owns the commit/validate/discard/conflict
  lifecycle ([ADR-007](../inspect-app/decisions/007-write-consistency.md)).

## 12. Limits of the abstraction

A package-wide abstraction hits boundaries that a thin rename cannot erase. Name
them explicitly so the abstraction stays trustworthy:

- **Driver selection is irreducible.** A device *is* a specific driver with a
  specific capability/custom-settings schema (NMOS port, "indices in IDs", SNMP
  config, …). The package even **generates per-driver models**. The domain can
  unify the *lifecycle, identity, connection, and status model*, but
  `configure(...)` of driver-specific settings is inherently driver-shaped.
  Proposed: a generic `Device.settings` entry point typed by driver, surfaced via
  the existing per-driver model generation — abstracted *entry point*, not
  abstracted *schema*.
- **Onboarding inputs are real.** Address(es), credentials, and driver choice
  must be supplied at `add_device`; they cannot be inferred.
- **Virtual vs. physical devices** differ (virtual id allocation, no driver
  contact). The lifecycle must accommodate both.
- **Capabilities come from the driver**, not the user. Ports/vertices are
  largely driver-defined; the user configures and connects them but does not
  invent them.
- **The escape hatch must stay first-class.** Power users will need raw
  `nGraphElement` / `InventoryDevice` access; the low-level apps remain public
  and documented for exactly this.

The honest framing: **unify the lifecycle, identity, connection, and status
model; do not pretend driver-specific configuration is uniform.**

## 13. Hide vs. expose — the key design ledger

The single most important artifact of this approach. Proposed starting point
(to be ratified as an ADR):

| Concept | Decision | Rationale |
| ------- | -------- | --------- |
| VIP app/namespace split (inventory/topology/collector planes) | **Hide** | The whole point of the abstraction |
| Edge pairing (two unidirectional edges → one `Connection`) | **Hide** | Server already groups via `externalEdgesByDeviceKey` |
| Id/key formats (`.dev.` infix, `a::b`, `topo:`/`device:` prefixes) | **Hide** behind opaque id value objects | Pure mechanical detail; error-prone in user code |
| Internal fan-out edges (`capacity: 1`) | **Hide** | Implementation detail of a device's internal wiring |
| Device lifecycle (onboard → place → connect → monitor) | **Expose** as `LifecycleState` | Users must reason about *where* a device is, not *which app* |
| Change set / commit | **Expose** (first-class) | Genuine server semantic; enables atomic multi-edits |
| Commit validation result & affected services | **Expose** (typed result) | `header.ok` lies; users must see real outcome |
| Concurrent-write conflicts | **Expose** as explicit conflict check + typed conflict error ([ADR-007](../inspect-app/decisions/007-write-consistency.md)) | No rev token exists on the Inspect surface (`updateTopology` is last-writer-wins); pretending otherwise would fake a guarantee |
| Multi-dimensional status (`alarm`/`bandwidth`/`maintenance`/`ptp`, `sa`/`severity`) | **Expose** (preserve dimensions + provide rollup) | Lossy to collapse; monitoring users need the detail |
| Snapshot freshness (no `_rev`) | **Expose** via explicit `refresh()` + fetch-time stamp | Honest about the lack of a server token |
| Lazy hydration on property access ([ADR-005](../inspect-app/decisions/005-lazy-snapshot-loading.md)) | **Expose** (documented behaviour) | Getters may perform one fetch and raise connector errors; hiding it would misrepresent cost and failure modes |
| Driver-specific custom settings | **Cannot hide** — abstract the entry point only | A device *is* its driver schema (§12) |

## 14. Migration & coexistence

The change can be **additive and non-breaking**:

1. **Build `app.network` on top of the existing apps.** No removal; the domain
   facade calls the current `inventory` / `topology` / `inspect` APIs
   internally. Reuse the existing wire models as the ACL's persisted form — e.g.
   domain `Connection` → ACL → existing `UnidirectionalEdge` → `updateTopology`
   (one wire model, not two).
2. **Ship read-first.** `app.network.get/list_*` over the `collector` snapshot
   (+ inventory supplements), returning unified `Device` / `Connection` objects.
3. **Add lifecycle writes incrementally** — `add_device` (onboard [+ place]),
   `place`, `connect`/`disconnect`, `configure` — each backed by the
   orchestration table (§9) and the change-set commit model.
4. **Keep the low-level apps public** as the escape hatch; document them as such.
5. **Optionally** add async + WebSocket per the existing ADRs once the sync
   surface settles.

Replacing the existing apps outright (a breaking, single-surface package) is the
alternative to the additive approach — see §15.

## 15. Open decisions

| Decision | Options | Note |
| -------- | ------- | ---- |
| Anti-corruption layer vs. transparent client | ACL (this doc) **vs.** keep mirroring VIP | The overarching decision; ratify as an ADR |
| Migration style | **Additive `app.network` facade** vs. breaking replacement of the apps | Recommend additive; lowest risk |
| Entry-point name | `app.network` · `app.fabric` · `app` (top-level) | Neutral, non-vendor name preferred |
| Driver-config abstraction | Generic `settings` entry point with per-driver typed schema **vs.** explicit per-driver objects | §12: entry point can unify; schema cannot |
| Multi-plane write semantics | Best-effort sequence + compensation **vs.** topology/inspect change-set only, inventory separate | §11.1; define partial-failure behaviour |
| Lifecycle model surface | Explicit `LifecycleState` enum **vs.** implicit (methods just work) | §5; explicit aids reasoning & errors |
| Completeness bar for v1 | Full coverage **vs.** 80% happy path + escape hatch for the rest | Recommend the latter; lowest cost |
| Hide-vs-expose ledger (§13) | Ratify explicitly | The most consequential artifact |
| Snapshot vs. WS for status freshness | re-snapshot now, WS as the real channel | §11.3; ties into ADR-001 / ADR-005 |
| Read-snapshot ↔ write-handle bridge | ~~How the change set resolves `_rev` at commit~~ **Decided**: stage-time baselines + pre-commit compare ([ADR-007](../inspect-app/decisions/007-write-consistency.md)); post-commit targeted refresh ([ADR-008](../inspect-app/decisions/008-post-commit-snapshot-refresh.md)) | §11.4 |
| Relationship to existing docs | Supersede `python-module-architecture.md` design goal **vs.** coexist as "current vs. target" | Currently coexists as the target picture |

## 16. Field-mapping reference (wire → domain)

Indicative mapping from the captured `collector` payload (and Inventory, for
onboarding fields) to the proposed domain types. To be completed during
discovery and turned into fixtures.

| Domain field | Source | Notes |
| ------------ | ------ | ----- |
| `Device.id` | `nodeStatus._items[]._id` | e.g. `device0` |
| `Device.label` | `nodeStatus[].descriptor.label` | fallback `fDescriptor` if empty |
| `Device.driver` / `Device.connection` | Inventory `config/devman/devices` | onboarding fields, not in collector |
| `Device.state` | derived | from presence across inventory / topology / collector (§5) |
| `Device.position` | `nodeStatus[].meta.coordinates.{x,y}` | float; hides `maps[]`/`inspect_app_format` |
| `Device.sync` | `nodeStatus[].syncSeverity` | map severity → `SyncState` |
| `Device.status` | `nodeStatus[].status.{sa,severity}` + `ptpDeviceStatus` (+ inventory status) | multi-dimensional |
| `Port.id` | module/port key `device0.dev.1.10` | translate to vertex id for edges |
| `Port.label` | `ports.*.descriptor.label` | |
| `Port.direction` | `ports.*.vertexInfo.type/vertexType` | `single`+`In/Out` or `double` → `BIDIRECTIONAL` |
| `Port.is_endpoint` | `ports.*.vertexInfo.fields.isEndpoint` | |
| `Port.status` | `ports.*.status` + `ptpPortStatus` | |
| `Connection.id` | `externalEdgesByDeviceKey[]._id` | `device0::device1` |
| `Connection.forward` | `…primary.data[edgeKey].{bandwidth,status,fromStatus,toStatus}` | |
| `Connection.reverse` | `…secondary.data[edgeKey].{…}` | may differ from forward |
| `Connection.status` | `externalEdgesByDeviceKey[].status` | `{alarm,bandwidth,maintenance,ptp}` |
| `Service.id` | `inspect.paths._items[]._id` | `100001::main` |
| `Service.label` | `…serviceFields.generic.descriptor.label` | |
| `Service.endpoints` | `…serviceFields.{from,fromLabel}` / `{to,toLabel}` | `topo:` refs |
| `Service.status` | `…serviceFields.serviceStatus.{config,total}` | |
| `Service.is_main` | `…serviceFields.isMain` | |

## 17. Relationship to existing documents

- [`python-module-architecture.md`](../python-module-architecture.md) — describes
  the **current** mirror-VIP architecture. This document proposes the **target**.
- [`inspect-app/`](../inspect-app/README.md) — `concepts.md` (the VIP wire-format
  research, including the `collector` aggregate and `nGraphElements` store) and
  the ADRs (API paradigm, loading, WebSocket, async, testing, commit model). The
  decisions there apply package-wide and are referenced throughout this document.
