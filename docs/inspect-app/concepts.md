# Inspect App — Concepts & Technical Model

> Status: **Draft** · Last updated: 2026-07-08
>
> This document captures what the *Inspect* app is, how it maps onto the
> existing package, and which technical details still need to be verified
> against a real server. Anything not yet confirmed is marked **[VERIFY]**.
> The official
> [VideoIPath Public API 2025 LTS](https://documenter.getpostman.com/view/11222813/2sBXihpCS8#intro)
> reference is a primary source for the wire format.

## 1. What Inspect is

Nevion describes Inspect as an *"advanced monitoring application that allows
the operator to perform high-level monitoring of services combined with the
ability to drill-down and inspect details to pinpoint service-affecting
problems."*

In recent VideoIPath releases the Inspect app **replaces the Topology app** in
the product UI: it becomes the entry point for building the network connectivity
model (vertices, edges, device placement), connecting devices, and watching
operational status. The server exposes live update capabilities, but this
package deliberately stays request/response only (see
[ADR-0001](./decisions/0001-api-paradigm.md) and
[ADR-0003](./decisions/0003-websocket-subscriptions.md)). Inspect applies
configuration changes with a **commit-style** model: create/edit/delete actions
are gathered into a client-side change set and committed together (see
[ADR-0006](./decisions/0006-commit-write-model.md)).

Inspect does **not** replace the **Inventory** app. Devices are still onboarded
in Inventory first; only then can they be placed and connected in Inspect. So
Inventory remains a separate, required prerequisite.

In **this package**, `app.inspect` is added **additively** — `app.topology` and
`app.inventory` keep working unchanged, with no deprecation planned.

## 2. Architecture: the `collector` facade

Inspect is built around a server-side **`collector` facade** — a distinct REST
v2 API surface under the `status` namespace. The server composes reads from
(and applies writes to) the underlying VideoIPath data store; the **API
contract is mostly net-new** relative to what `app.topology` and
`app.inventory` use today.

**Reads** — scoped queries against the collector tree
([ADR-0007](./decisions/0007-lazy-snapshot-loading.md)):

- The collector sub-paths accept `* where <expr>` filters, `limit N`, and deep
  field projections — confirmed by a WebSocket capture of the Inspect UI, which
  never loads the full tree (see
  [endpoints.md — Collector Scoped Queries](./endpoints.md#collector-scoped-queries-captured-from-the-inspect-ui)).
- Default loading model: a **skeleton** read (all devices without modules/ports
  + all edges with a lean projection) followed by **lazy per-device hydration**
  and section-level loads for services.
- `GET /rest/v2/data/status/collector/**` → `data.status.collector` (§3.1)
  remains the eager/fallback mode: the whole tree — topology nodes,
  inter-device edges, services/paths, status, and security context — in a
  single response with `_items[]` collections.

**Writes** — one bulk action per commit:

- `POST /rest/v2/actions/status/collector/updateTopology`
  ([ADR-0006](./decisions/0006-commit-write-model.md))
- Sends a client-assembled delta: `replaceDevices`, `replaceVertices`,
  `replaceEdges`, `replaceResourceTransforms`, `addExternalEdges`, `remove`,
  `force`.
- Validation runs at commit time; success/failure is determined by
  `data.res.ok` / `data.validation.result.ok`, not `header.ok`.

**Namespace** — the `collector` API entry points live under `status`
(`data/status/collector` for reads, `actions/status/collector` for writes), but
the **underlying store is the existing config plane**: `updateTopology` mutations
land in `config/network/nGraphElements`. Confirmed by capture — an anonymized
edge updated via `updateTopology` appeared in
`GET …/data/config/network/nGraphElements/**` with the changed value and a
bumped `_rev`. So the collector is a **facade**: a status-namespace read/action
surface in front of the revisioned `nGraphElements` config store (§3.3).

**Shared with existing apps** — the underlying store and wire conventions, not
model classes:

- The config store `nGraphElements` is **the same one `app.topology` already
  reads and models**. Inspect edits land there, revisioned with `_rev` (§3.3),
  but the Inspect package keeps its own `InspectApi*` DTOs and does **not** import
  or subclass topology/inventory model classes.
- REST v2 envelope, session/XSRF auth, pid/id formats
- Vertex ids (`device-a.module-1.port-out-1.out`), edge keys (`fromId::toId`)
- `descriptor` / `fDescriptor` objects, `sa` / `severity` status semantics
- Device positions as float coordinates — `meta.coordinates` in the collector
  aggregate, `maps[].x/y` in `nGraphElements`, same *Inspect Topology* format as
  `inspect_app_format` in the topology app

**Net-new for `app.inspect`:**

| Layer | Responsibility |
| ----- | -------------- |
| Collector read/parse | Parse `data.status.collector` with `InspectApi*` transport DTOs, then expose user-facing `InspectDevice` / `InspectService` objects via `InspectSnapshot` |
| Change-set / commit write | Assemble `updateTopology` payloads with `InspectApi*` DTOs, handle validation responses |
| Lookup / network actions | Model captured lookup, add-device, and sync-device action envelopes with `InspectApi*` DTOs |

Inventory onboarding stays on the existing path (`config/devman/devices`,
`/api/updateDevices`). `app.topology` and `app.inventory` remain unchanged;
`app.inspect` is additive.

## 3. Domain model

How Inspect concepts map onto existing package concepts:

| Inspect concept        | Inspect API (collector)                                | Existing model / app                          |
| ---------------------- | ------------------------------------------------------ | --------------------------------------------- |
| Device (inventory)     | Prerequisite — not part of collector; onboard via `config/devman/devices` | `InventoryDevice` (`apps/inventory`) |
| Device (topology node) | Read: `collector.inspect.nodeStatus`; stored as `baseDevice` in `nGraphElements` | Store shape overlaps with Topology, but Inspect uses `InspectApiBaseDevice` |
| Vertices / Edges       | Read: `nodeStatus` `vertexInfo` / `externalEdgesByDeviceKey`; stored as `ipVertex` / `codecVertex` / `unidirectionalEdge` in `nGraphElements` | Store shape overlaps with Topology, but Inspect uses `InspectApi*` nGraph DTOs |
| Vertex tags            | Read: per-port `tagsInfo` on hydrated `nodeStatus`; editable form via `lookupInspectVertexByIds` (`assignedTags`, `fields.tags`, `fields.localAssignedTags`) | **Not in `nGraphElements`** — `app.topology` has no vertex-tag concept; server-side bindings live in `videoipath_docs.device_tags`, not the `ngraph` table (§3.4) |
| Change set / commit    | `POST …/actions/status/collector/updateTopology` → writes `nGraphElements` ([ADR-0006](./decisions/0006-commit-write-model.md)) | _commit flow net-new; target store is existing `nGraphElements`_ |
| Services / paths       | `collector.inspect.paths`, `pathDescriptions` on nodes/edges | _none — net-new_ |
| Device / edge status   | Embedded in collector (`status`, `sa`/`severity`, bandwidth, PTP) | `inventory.model.device_status`, `status/network/*` — partial overlap |
| Sync status            | `syncSeverity` on nodeStatus items                     | `TopologySynchronize` via `status/network/nGraphSyncStatus` |
| Lookup / network actions | `lookupInspectDevice`, `lookupInspectEdgesByIds`, `lookupInspectVertexByIds`, `lookupSyncInfo`, `addDevices`, `syncDevices` | request/response envelopes captured and modelled |
| Connections / Partial connections | `collector.inspect.paths` + `conman.services`; linked via `serviceFields.bid` / `bookingId` in `pathDescriptions` ([endpoints.md](./endpoints.md#get-restv2datastatuscollectorinspectpaths)) | _read via collector + conman; no separate Connections REST on this instance_ |

### 3.1 Collector aggregate — primary read surface

Inspect reads a single server-built aggregate under the `collector` namespace
— the same namespace used for writes
(`actions/status/collector/updateTopology`, [ADR-0006](./decisions/0006-commit-write-model.md)):

| Item | Value |
| ---- | ----- |
| Method / path | `GET /rest/v2/data/status/collector/**` |
| Root | `data.status.collector` |
| List shape | Collections use `_items[]` entries with `_id` / `_vid` |

Top-level sections under `data.status.collector`:

| Section | Purpose |
| ------- | ------- |
| `inspect.nodeStatus` | Topology nodes: devices → modules → ports, with live status, `meta.coordinates`, `vertexInfo`, and embedded `pathDescriptions` |
| `inspect.paths` | Service/path list: booking segments, endpoint labels, aggregated `serviceFields` |
| `externalEdgesByDeviceKey` | Inter-device link status grouped by device pair; `primary` / `secondary` each hold edges keyed by `"fromId::toId"` |
| `maintenanceBookings` | Maintenance bookings (empty in capture) |
| `security` | Security context for devices, profiles, matrices, … |
| `superProfiles` | Routing profiles |
| `tagInfo` | Tag → profile mappings |

**ID conventions** (consistent across read and write):

| Concept | Example | Notes |
| ------- | ------- | ----- |
| Device | `device-a` | `deviceId`, `pid`, `_id` on nodeStatus items |
| Module pid | `device-a.dev.module-1` | Nested under `modules` |
| Port pid | `device-a.dev.module-1.port-out-1` | Nested under `ports` |
| Vertex id | `device-a.module-1.port-out-1.out` | Shorter form in `vertexInfo`; used in edge keys |
| Edge id | `device-a.module-1.port-out-1.out::device-b.module-1.port-in-1.in` | Same key as `replaceEdges` in `updateTopology` |
| Device pair | `device-a::device-b` | Key for `externalEdgesByDeviceKey` items |
| Service / path | `booking-1001::main` | `bookingId` + path role; appears in `pathDescriptions` and `inspect.paths` |
| Resource id | `device:device-a.dev.module-1.port-out-1` | Prefixed resource references |
| Topo endpoint ref | `topo:device-a.module-1.port-out-1` | Used in `serviceFields.from` / `.to` |

**`vertexInfo`** on ports describes topology vertices:

- `type: "single"` — one vertex (`id`, `vertexType`: `"In"` / `"Out"`, `fields`:
  `isActive`, `isControlled`, `isEndpoint`)
- `type: "double"` — bidirectional port with separate `in` / `out` ids and labels

**Drill-down / service linkage:** `pathDescriptions` on ports and edges embed
both `deviceLevel` (local hop: input → output within a device) and
`serviceLevel` (end-to-end service: `bookingId`, `serviceLabel`, `fromStatus` /
`toStatus`, `isMain`, `serviceStatus`). This is how the UI connects topology
elements to booked services.

**Edge live status** (`externalEdgesByDeviceKey`): each edge carries
`bandwidth`, `fromStatus` / `toStatus`, `pathDescriptions`, and aggregate
`status` (`alarm`, `bandwidth`, `maintenance`, `ptp` severities).

**Node live status** (`inspect.nodeStatus`): hierarchical `status` with
`sa` / `severity` at device, module, port; plus `ptpDeviceStatus`, `syncSeverity`,
`hasEndpoints`, domains, and tags. Device-level tags appear on the node itself
(`tags`, `meta.tags`, `tagsInfo`); **vertex-level tag bindings** appear on
hydrated ports (`tagsInfo` with `assigned` / `inherited` / `local` / `custom`
subtrees — see §3.4). The skeleton projection only carries device-level tagging;
port `tagsInfo` requires per-device hydration (`modules/*`).

**Package implications:**

- `app.inspect` reads the collector through **scoped queries**
  ([ADR-0007](./decisions/0007-lazy-snapshot-loading.md)): skeleton first
  (`inspect/nodeStatus` with `modules/"_noId"`, `externalEdgesByDeviceKey`
  with a lean projection), then per-device hydration (`modules/*` detail
  projection) and section-level loads (`inspect/paths`). The full
  `GET …/data/status/collector/**` fetch is the eager/fallback mode.
- The collector query language is confirmed via UI capture: `* where <expr>`
  (with `and`/`or`, `contains()`, `lower()`), `limit N`, field projections
  with `/.../` up-navigation, `**` subtrees, and the `"_noId"`
  expansion-suppressor (see
  [endpoints.md](./endpoints.md#collector-scoped-queries-captured-from-the-inspect-ui)).
- Edge keys and vertex ids from reads map directly onto `updateTopology` write
  payloads.
- Commit validation references the same `bookingId`s visible in
  `pathDescriptions` (e.g. failed delete for an anonymized booking / main path
  edge).
- Scoped collector queries work as REST GETs when the URL fits within the server
  URI limit ([endpoints.md](./endpoints.md#collector-scoped-queries-captured-from-the-inspect-ui)). The full UI
  projection hits **HTTP 414**; use a trimmed skeleton projection or `/**`
  fallback. Both `nodeStatus/<device-id>/…` and
  `* where deviceId='…' limit 1/…` work for single-device hydration. Omitting
  `where` does **not** require `limit`.

### 3.2 API planes — existing apps vs. Inspect

The VideoIPath backend separates **config** (mutable, revisioned) and
**status** (read-only, subscription-friendly)
([Public API 2025 LTS](https://documenter.getpostman.com/view/11222813/2sBXihpCS8#intro)).
Inspect's `collector` API entry points sit under `status`, but its topology
edits resolve to the **config** plane (`nGraphElements`). Network action
endpoints under `actions/status/network/*` are also relevant for device add/sync
workflows:

| Plane | Used by | Read | Write |
| ----- | ------- | ---- | ----- |
| Config | `app.topology`, `app.inventory`, **Inspect (effective store)** | `GET …/data/config/…` | `PATCH …/data/config/…` (revisioned) or RPC |
| Status | Inventory status reads, Inspect status reads | `GET …/data/status/…` | — |
| Collector (facade) | `app.inspect` | Scoped queries on `…/data/status/collector/…` (skeleton + hydration, ADR-0007); `GET …/**` as eager/fallback | `POST …/actions/status/collector/updateTopology` → `nGraphElements` |
| Network actions | `app.inspect` device topology workflows | — | `POST …/actions/status/network/addDevices`, `POST …/actions/status/network/syncDevices` |

So Inspect's read aggregate is status-namespace and net-new in shape, but its
writes are commit-time-validated bulk actions that land in the revisioned
`config/network/nGraphElements` store (§3.3). The client gathers edits locally
until commit; ADR-0006 accepts that there is no separate server-side change-set
id for the verified `updateTopology` flow.

**Endpoint policy** ([ADR-0008](./decisions/0008-collector-only-endpoints.md)):
the Inspect package calls **only** the Inspect surface — collector data reads,
collector actions, and the `addDevices`/`syncDevices` network actions. The
config-plane row above is context, not a call path: the package never issues
`GET`/`PATCH …/config/network/nGraphElements` (that stays `app.topology`'s
surface). Consequence: no `_rev` is available to Inspect, and since
`updateTopology` ignores revisions anyway (last-writer-wins, verified),
concurrent-write detection is client-side compare-and-commit
([ADR-0009](./decisions/0009-write-consistency.md)); after a commit the
snapshot catches up via targeted scoped re-reads
([ADR-0010](./decisions/0010-post-commit-snapshot-refresh.md)).

The server can expose status-plane subscriptions, but WebSockets are out of
scope for this package. Fresh status is obtained by explicit re-fetches
([ADR-0001](./decisions/0001-api-paradigm.md),
[ADR-0003](./decisions/0003-websocket-subscriptions.md)).

This framing underpins the API-paradigm and loading decisions
([ADR-0001](./decisions/0001-api-paradigm.md),
[ADR-0002](./decisions/0002-loading-and-state.md)).

### 3.3 Config store — `nGraphElements` (write target)

`GET /rest/v2/data/config/network/nGraphElements/**` →
`data.config.network.nGraphElements._items[]`. This is the **revisioned source
of truth** for topology that Inspect's `updateTopology` writes into. Its wire
shape overlaps with the Topology app, but the Inspect package models it with
standalone `InspectApi*` DTOs.

> Documented here as store/background knowledge only — the package does **not**
> read or write this endpoint at runtime
> ([ADR-0008](./decisions/0008-collector-only-endpoints.md)). The persisted
> element *shape* still matters: `updateTopology` `replace*` payloads carry it.

| Field | Notes |
| ----- | ----- |
| `_id` / `_vid` | Element id; edges use the `fromId::toId` key (same as collector and `replaceEdges`) |
| `_rev` | CouchDB-style revision `N-<timestamp>` for optimistic concurrency |
| `type` | Element kind (see below) |
| `descriptor` / `fDescriptor` | User label/desc vs. fallback (device-reported) label/desc |

Element `type` values seen in capture:

| `type` | Represents | Key fields |
| ------ | ---------- | ---------- |
| `baseDevice` | Topology device node | `maps[]` (`cType: "Topology"`, integer `x`/`y`), `iconType`, `sdpStrategy`, `isVirtual`, `tags` (device-level only) |
| `ipVertex` | Ethernet/IP port vertex (`.in` / `.out`) | `vertexType`, `gpid.pointId`, `supports*Cfg` capability flags — **not** vertex tag bindings (§3.4) |
| `codecVertex` | Codec/SDI endpoint vertex | `vertexType` (`In`/`Out`), `codecFormat`, `useAsEndpoint`, `control`, SIPS/SDP fields — **not** vertex tag bindings (§3.4) |
| `unidirectionalEdge` | Directed link/route between vertices | `fromId`, `toId`, `weight`, `capacity`, `bandwidth`, `redundancyMode`, `weightFactors`, `conflictPri` |

**Write round-trip confirmed:** an anonymized edge edited via `updateTopology`
is present here with the changed value and a bumped `_rev`, and inter-device
links appear as paired unidirectional edges (one in each direction, typically
with `capacity: 65535`). Internal fan-out edges (vertex→vertex within a device)
use `capacity: 1`.

**Implication:** Inspect's underlying topology store is `nGraphElements`, but
the package keeps a separate Inspect model namespace (`InspectApiBaseDevice`,
`InspectApiIpVertex`, `InspectApiUnidirectionalEdge`, …). Do not reuse topology app
model classes in Inspect DTOs. `updateTopology` is **last-writer-wins** — a
stale `_rev` in the payload is ignored ([endpoints.md](./endpoints.md#post-restv2actionsstatuscollectorupdatetopology)).

### 3.4 Tagging — device vs. vertex (Inspect vs. Topology)

Inspect distinguishes two tag scopes. This is a **key difference from
`app.topology`**, which only models tags on topology **devices** (`baseDevice`
entries in `nGraphElements`).

| Scope | What is tagged | Topology / `nGraphElements` | Inspect read surface | Server storage |
| ----- | -------------- | --------------------------- | -------------------- | -------------- |
| **Device** | Topology node (`baseDevice`) | `tags` on the `baseDevice` item | `nodeStatus` `tags` / `meta.tags` / `tagsInfo`; `lookupInspectDevice` | `ngraph` / `nGraphElements` |
| **Vertex** | Individual port vertex (`ipVertex`, `codecVertex`, …) | **Not present** — no vertex-tag field on persisted graph elements | Hydrated port `tagsInfo`; editable form in `lookupInspectVertexByIds` | `videoipath_docs.device_tags` (separate from `ngraph`) |

**Implications for the package:**

- `app.topology` reads/writes device tags via `nGraphElements` only. It has no
  API for binding tags to a vertex id such as
  `device-a.module-1.port-out-1.out`.
- `app.inspect` must treat vertex tags as a **separate concern** from the
  persisted graph element shape. Do not assume a vertex's `tags` array in an
  `nGraphElements` `ipVertex` / `codecVertex` item (if present at all) is the
  source of truth for tag bindings — confirmed empty in captures while
  `lookupInspectVertexByIds` carries `assignedTags` and `fields.tags`.
- Stage-time baselines and compare-and-commit for vertex edits must use
  `lookupInspectVertexByIds` for tag fields ([ADR-0009](./decisions/0009-write-consistency.md)),
  not `nGraphElements` or the collector skeleton.
- Collector `tagInfo` provides tag → profile metadata for the aggregate; it does
  not replace per-vertex `assignedTags` on the lookup response.

## 4. How the transport works today (recap)

So the new layer fits the existing patterns rather than reinventing them:

- `connector/` is a thin sync HTTP client built on `requests`, with two
  sub-connectors: REST v2 (`GET`/`PATCH`/`POST`) and RPC (`POST /api/*`). Basic
  auth, gzip, per-method timeouts.
- Each connector enforces an **allow-list of URL prefixes** (`ALLOWED_URLS` /
  `ALLOWED_EXACT_MATCHES`). New Inspect endpoints must be added there — but
  only Inspect-surface prefixes; `config/network/nGraphElements` is not added
  for the Inspect app ([ADR-0008](./decisions/0008-collector-only-endpoints.md)).
- Responses are wrapped in a common envelope (`ResponseV2Get`/`…Patch`/`…Post`)
  with a `header` (`code`, `auth`, …) and a `data`/`result` body, validated by
  Pydantic.
- Apps are **lazy-loaded** off `VideoIPathApp` and are **stateless**: every call
  re-fetches from the server (e.g. `topology.get_device` issues several `GET`s
  and rebuilds the aggregate each time). Inspect deviates deliberately: state
  is **snapshot-scoped** — a skeleton is loaded up front, detail is lazily
  hydrated into the same snapshot, and freshness means building a new snapshot
  ([ADR-0007](./decisions/0007-lazy-snapshot-loading.md)). There is still no
  cache across snapshots.
- Inspect models live in two layers:
  - `apps/inspect/model` — `InspectApi*` transport DTOs for HTTP payloads
  - `apps/inspect/domain` and `apps/inspect/snapshot.py` — user-facing read
    models backed by a collector snapshot and internal indexes
- App/API methods should own fetching, staging, committing, and error handling.

## 5. Endpoint discovery — how to fill in the **[VERIFY]** gaps

Two complementary sources: the **official reference** (authoritative for the
documented surface) and **browser capture** (authoritative for what the Inspect
GUI actually does, including undocumented calls). WebSocket *subscriptions*
stay out of scope for the package per ADR-0003, but captured WS frames are a
first-class **discovery source**: the subscription `path`s address the same
data tree as REST v2 and revealed the collector's query language and the UI's
skeleton-first load strategy (see
[endpoints.md — Collector Scoped Queries](./endpoints.md#collector-scoped-queries-captured-from-the-inspect-ui),
[ADR-0007](./decisions/0007-lazy-snapshot-loading.md)).

0. **Start from the official reference.** The
   [VideoIPath Public API 2025 LTS](https://documenter.getpostman.com/view/11222813/2sBXihpCS8#intro)
   collection documents `Connections`, `Partial Connections`, and
   `Import and Export (preview)`, plus the `config` / `status` / `experimental`
   top-level split. Use it as the primary map of the documented surface.
   > Inspect uses `/rest/v2/` for collector read/write. Other resources may
   > still use v1 paths documented in the public reference — **[VERIFY]** per
   > resource during capture.
1. **Capture browser traffic.** Open the Inspect app in the VideoIPath web UI
   with the browser DevTools → Network tab. Record a full session (HAR export):
   open a device, add/sync devices, connect two devices, **commit a change set**,
   and drill into a service. Note REST calls and payloads.
2. **Replay through the package logger.** The connector logs every response at
   `DEBUG` (`_log_response`). Set `log_level="DEBUG"` and call candidate
   endpoints to confirm payload shapes.
3. **Diff against known resources.** Compare captured paths to the prefixes the
   package already allows. New prefixes ⇒ new Inspect resources.
4. **Save representative payloads as fixtures.** Store sanitised JSON under
   `tests/fixtures/inspect/<version>/…`. These feed the offline tests in
   [ADR-0005](./decisions/0005-e2e-testing.md) and double as living
   documentation of the wire format.

### 5.1 Discovery checklist (fill in as confirmed)

REST:

- [x] Base path: Inspect uses `/rest/v2/` for collector read/write (`data/status/collector/**`, `actions/status/collector/updateTopology`)
- [x] Service / monitoring aggregate: `GET /rest/v2/data/status/collector/**` → `data.status.collector` with `inspect.nodeStatus`, `inspect.paths`, `externalEdgesByDeviceKey`, `security`, `superProfiles`, `tagInfo` (§3.1)
- [x] Drill-down: services linked via `pathDescriptions` on ports/edges (`deviceLevel` + `serviceLevel`) and `inspect.paths._items[]` (`bookingId`, path segments, `serviceFields`)
- [x] Collector sub-paths & query language: confirmed via Inspect UI WebSocket capture — `* where <expr>`, `limit N`, deep projections with `/.../` up-navigation, `**`, `"_noId"` expansion-suppressor; UI loads skeleton-first (`modules/"_noId"`) — decoded queries in [endpoints.md](./endpoints.md#collector-scoped-queries-captured-from-the-inspect-ui) ([ADR-0007](./decisions/0007-lazy-snapshot-loading.md))
- [x] Scoped-query REST GET equivalence: confirmed for practical query lengths; full UI projection → HTTP 414 ([endpoints.md](./endpoints.md#collector-scoped-queries-captured-from-the-inspect-ui))
- [x] Single-device hydration form: both `nodeStatus/<device-id>/…` and `* where deviceId='…' limit 1/…` work; prefer direct id
- [x] Exact `"_noId"` semantics: subtree expansion suppressor → `modules: {}` at collection level, key omitted on single-device queries
- [x] Populated `modules/*` detail payload: confirmed on synced devices; `syncSeverity=2` devices return empty modules until synced
- [x] Skeleton vs. full aggregate: ~92 KB skeleton (27 devices + 40 edges) vs ~19 MB `/**` on this instance; `limit` not required when `where` is omitted
- [x] Connections / Partial Connections: services via `collector.inspect.paths` + `conman.services`; `bid` ↔ `connection.id`
- [x] Change set / commit endpoint: `POST /rest/v2/actions/status/collector/updateTopology` — bulk delta with `replaceDevices`, `replaceVertices`, `replaceEdges` (key `"fromId::toId"`), `replaceResourceTransforms`, `addExternalEdges`, `remove`, `force` ([ADR-0006](./decisions/0006-commit-write-model.md))
- [x] Change set staging: client-side gather until `updateTopology`; no separate server-side change-set id for the verified flow (ADR-0006)
- [x] Commit failure response: check `data.res.ok` / `data.validation.result.ok` (not `header.ok`); `validation.details[id]` carries `status`, `rev`, `resolvable`, `type`; failed delete example: `"A required edge was not found. (main)"`, `items: []` ([ADR-0006](./decisions/0006-commit-write-model.md))
- [x] Commit success response for no-op: `data.items: []`, `data.res.ok: true`, `data.validation.result.ok: true` ([endpoints.md](./endpoints.md#post-restv2actionsstatuscollectorupdatetopology))
- [x] Commit success response with real applied changes: `data.items[]` with `{id, idx, res.ok}` per applied entity ([endpoints.md](./endpoints.md#post-restv2actionsstatuscollectorupdatetopology))
- [x] Commit semantics: reject-before-apply; invalid ops return `items: []`; client-side staging only (no server change-set id)
- [x] Import / Export (preview): **unregistered** on 2025.4.9 — empty data namespaces; GET action schema empty; POST → `No action node in request`
- [x] Write/action endpoint: `/rest/v2/actions/status/collector/updateTopology`
- [x] Collector action payloads captured and modelled: `/rest/v2/actions/status/collector/lookupInspectDevice`, `/rest/v2/actions/status/collector/lookupSyncInfo`
- [x] Network action request shapes, normal action responses, and validation-error responses captured: `/rest/v2/actions/status/network/addDevices`, `/rest/v2/actions/status/network/syncDevices`
- [x] Config store / write target: `updateTopology` lands in `GET /rest/v2/data/config/network/nGraphElements/**` (`_items[]`, `_rev`, `type` ∈ `baseDevice` / `codecVertex` / `ipVertex` / `unidirectionalEdge`); model with standalone `InspectApi*` DTOs (§3.3)
- [x] `_rev` handling on commit: last-writer-wins; `_rev` in `replaceEdges` payload is ignored
- [x] Version gating: collector read/write and `updateTopology` verified on **2025.4.9**
- [x] DTO coverage: add typed request/response models for captured lookup, action result, and validation-error endpoint payloads in [endpoints.md](./endpoints.md)

Write consistency & post-commit refresh ([ADR-0009](./decisions/0009-write-consistency.md), [ADR-0010](./decisions/0010-post-commit-snapshot-refresh.md)) — verified live on 2025.4.9 (2026-07-08):

- [x] Persisted-element lookups: `lookupInspectEdgesByIds` returns the **full persisted edge form** (batched); `lookupInspectVertexById`/`…ByIds` and `lookupInspectDevice` return editable forms; **no `_rev` in any lookup response**; `lookupGraphElement` does **not** exist; `lookupNodeInfo`/`lookupEdgeInfo`/`lookupDeviceVertices` are display-oriented ([endpoints.md](./endpoints.md#post-restv2actionsstatuscollectorlookupinspectedgesbyids))
- [x] Vertex tag bindings: separate from `nGraphElements` — stored server-side in `videoipath_docs.device_tags`; surfaced on `lookupInspectVertexByIds` (`assignedTags`, `fields.tags`, `fields.localAssignedTags`) and hydrated port `tagsInfo` in `nodeStatus`; not modelled by `app.topology` (§3.4)
- [x] UI edit/commit flows avoid `nGraphElements`: the Inspect UI bundle contains zero references; the edge edit flow calls `lookupInspectEdgesByIds` with both pair directions ([ADR-0008](./decisions/0008-collector-only-endpoints.md))
- [x] Batched lookups for compare-and-commit baselines: `…ByIds` actions take id lists natively
- [x] Direct edge-pair addressing for targeted refresh: `externalEdgesByDeviceKey/<deviceA::deviceB>/<projection>` returns the single pair item
- [x] Collector propagation delay: measured via device coordinate commit + revert (three samples) — change visible on the **first poll ~25 ms after the POST returned**; no post-commit retry window needed ([ADR-0010](./decisions/0010-post-commit-snapshot-refresh.md))
- [x] `replaceDevices` payload shape: the **edit form** (`lookupInspectDevice.fields`; `coordinates`/`localAssignedTags` mandatory) — the raw persisted `baseDevice` element is rejected with HTTP 400; round-trip verified byte-identical except `_rev` ([endpoints.md](./endpoints.md#post-restv2actionsstatuscollectorupdatetopology))
- [x] `replaceVertices` payload shape: the **vertex edit form** (`lookupInspectVertexById.fields`) — verified via desc round-trip on a live vertex (byte-identical revert). **Update-only**: an unknown vertex id fails validation with *"Vertex with id … was not found in graph"* — standalone vertices cannot be created via `updateTopology` (they originate from device sync / virtual-device definitions) ([endpoints.md](./endpoints.md#post-restv2actionsstatuscollectorupdatetopology))
- [ ] Re-check on every server upgrade: does `updateTopology` gain `_rev` enforcement (would allow replacing client-side compare-and-commit)

## 6. Open questions

_All VERIFY items are resolved (results merged into
[endpoints.md](./endpoints.md) and the §5.1 checklist) or documented as
confirmed limitations / unregistered stubs._

Remaining follow-up (only if a future server version registers new actions):

- Re-run `GET /rest/v2/actions/status/collector/<actionName>` schema check after
  upgrade; probe POST only for newly registered actions — and re-check whether
  `updateTopology` gains `_rev` enforcement (ADR-0009 would be revisited).
- Capture a `resolvable: true` validation case if one appears in the UI during
  normal operator workflows.
