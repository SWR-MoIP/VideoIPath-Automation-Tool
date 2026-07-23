# Inspect App — Concepts & Technical Model

Design record for the shipped Inspect app. Wire shapes and endpoint details live
in [endpoints.md](./endpoints.md); the official
[VideoIPath Public API 2025 LTS](https://documenter.getpostman.com/view/11222813/2sBXihpCS8#intro)
is a secondary reference for the documented surface.

## 1. What Inspect is

Nevion describes Inspect as an *"advanced monitoring application that allows
the operator to perform high-level monitoring of services combined with the
ability to drill-down and inspect details to pinpoint service-affecting
problems."*

In recent VideoIPath releases the Inspect app **replaces the Topology app** in
the product UI: it becomes the entry point for building the network connectivity
model (vertices, edges, device placement), connecting devices, and watching
operational status. The server exposes live update capabilities, but this
package stays request/response only (see
[ADR-001](./decisions/001-api-paradigm.md)). Inspect applies configuration
changes with a **commit-style** model: create/edit/delete actions are gathered
into a client-side change set and committed together (see
[ADR-004](./decisions/004-commit-write-model.md)).

Inspect does **not** replace the **Inventory** app. Devices are still onboarded
in Inventory first; only then can they be placed and connected in Inspect.

In **this package**, `app.inspect` replaces `app.topology`: `TopologyApp` is
deprecated on VideoIPath 2025.x and unsupported on 2026.x+. `app.inventory`
remains unchanged and required for device onboarding.

## 2. Architecture: the `collector` facade

Inspect is built around a server-side **`collector` facade** — a distinct REST
v2 API surface under the `status` namespace. The server composes reads from
(and applies writes to) the underlying VideoIPath data store; the **API
contract is mostly net-new** relative to what `app.topology` and
`app.inventory` use today.

**Reads** — scoped queries against the collector tree
([ADR-005](./decisions/005-lazy-snapshot-loading.md)):

- The collector sub-paths accept `* where <expr>` filters, `limit N`, and deep
  field projections (see
  [endpoints.md — Collector Scoped Queries](./endpoints.md#collector-scoped-queries-captured-from-the-inspect-ui)).
- Default loading model: a **skeleton** read (all devices without modules/ports
  + all edges with a lean projection) followed by **lazy per-device hydration**
  and section-level loads for services.
- `GET /rest/v2/data/status/collector/**` → `data.status.collector` (§3.1)
  remains the eager/fallback mode: the whole tree in a single response with
  `_items[]` collections.

**Writes** — one bulk action per commit:

- `POST /rest/v2/actions/status/collector/updateTopology`
  ([ADR-004](./decisions/004-commit-write-model.md))
- Sends a client-assembled delta: `replaceDevices`, `replaceVertices`,
  `replaceEdges`, `replaceResourceTransforms`, `addExternalEdges`, `remove`,
  `force`.
- Validation runs at commit time; success/failure is determined by
  `data.res.ok` / `data.validation.result.ok`, not `header.ok`.

**Namespace** — the `collector` API entry points live under `status`
(`data/status/collector` for reads, `actions/status/collector` for writes), but
the **underlying store is the existing config plane**: `updateTopology` mutations
land in `config/network/nGraphElements`. The collector is a **facade**: a
status-namespace read/action surface in front of the revisioned `nGraphElements`
config store (§3.3).

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
  aggregate, `maps[].x/y` in `nGraphElements`

**Net-new for `app.inspect`:**

| Layer | Responsibility |
| ----- | -------------- |
| Collector read/parse | Parse `data.status.collector` with `InspectApi*` transport DTOs, then expose user-facing `InspectDevice` / `InspectService` objects via `InspectSnapshot` |
| Change-set / commit write | Assemble `updateTopology` payloads with `InspectApi*` DTOs, handle validation responses |
| Lookup / network actions | Model lookup, add-device, and sync-device action envelopes with `InspectApi*` DTOs |

Inventory onboarding stays on the existing path (`config/devman/devices`,
`/api/updateDevices`). `app.topology` and `app.inventory` remain unchanged;
`app.inspect` is additive.

## 3. Domain model

| Inspect concept        | Inspect API (collector)                                | Existing model / app                          |
| ---------------------- | ------------------------------------------------------ | --------------------------------------------- |
| Device (inventory)     | Prerequisite — not part of collector; onboard via `config/devman/devices` | `InventoryDevice` (`apps/inventory`) |
| Device (topology node) | Read: `collector.inspect.nodeStatus`; stored as `baseDevice` in `nGraphElements` | Store shape overlaps with Topology, but Inspect uses `InspectApiBaseDevice` |
| Vertices / Edges       | Read: `nodeStatus` `vertexInfo` / `externalEdgesByDeviceKey`; stored as `ipVertex` / `codecVertex` / `unidirectionalEdge` in `nGraphElements` | Store shape overlaps with Topology, but Inspect uses `InspectApi*` nGraph DTOs |
| Vertex tags            | Read: per-port `tagsInfo` on hydrated `nodeStatus`; editable form via `lookupInspectVertexByIds` (`assignedTags`, `fields.tags`, `fields.localAssignedTags`) | **Not in `nGraphElements`** — `app.topology` has no vertex-tag concept; server-side bindings live in `videoipath_docs.device_tags`, not the `ngraph` table (§3.4) |
| Change set / commit    | `POST …/actions/status/collector/updateTopology` → writes `nGraphElements` ([ADR-004](./decisions/004-commit-write-model.md)) | _commit flow net-new; target store is existing `nGraphElements`_ |
| Services / paths       | `collector.inspect.paths`, `pathDescriptions` on nodes/edges | _none — net-new_ |
| Device / edge status   | Embedded in collector (`status`, `sa`/`severity`, bandwidth, PTP) | `inventory.model.device_status`, `status/network/*` — partial overlap |
| Sync status            | `syncSeverity` on nodeStatus items                     | `TopologySynchronize` via `status/network/nGraphSyncStatus` |
| Lookup / network actions | `lookupInspectDevice`, `lookupInspectEdgesByIds`, `lookupInspectVertexByIds`, `lookupSyncInfo`, `addDevices`, `syncDevices` | request/response envelopes modelled |
| Connections / Partial connections | `collector.inspect.paths` + `conman.services`; linked via `serviceFields.bid` / `bookingId` in `pathDescriptions` ([endpoints.md](./endpoints.md#get-restv2datastatuscollectorinspectpaths)) | _read via collector + conman; no separate Connections REST on this instance_ |

### 3.1 Collector aggregate — primary read surface

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
| `maintenanceBookings` | Maintenance bookings |
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
`toStatus`, `isMain`, `serviceStatus`).

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
  ([ADR-005](./decisions/005-lazy-snapshot-loading.md)): skeleton first
  (`inspect/nodeStatus` with `modules/"_noId"`, `externalEdgesByDeviceKey`
  with a lean projection), then per-device hydration (`modules/*` detail
  projection) and section-level loads (`inspect/paths`). The full
  `GET …/data/status/collector/**` fetch is the eager/fallback mode.
- The collector query language: `* where <expr>` (with `and`/`or`,
  `contains()`, `lower()`), `limit N`, field projections with `/.../`
  up-navigation, `**` subtrees, and the `"_noId"` expansion-suppressor (see
  [endpoints.md](./endpoints.md#collector-scoped-queries-captured-from-the-inspect-ui)).
- Edge keys and vertex ids from reads map directly onto `updateTopology` write
  payloads.
- Scoped collector queries work as REST GETs when the URL fits within the server
  URI limit. The full UI projection hits **HTTP 414**; use a trimmed skeleton
  projection or `/**` fallback. Both `nodeStatus/<device-id>/…` and
  `* where deviceId='…' limit 1/…` work for single-device hydration. Omitting
  `where` does **not** require `limit`.

### 3.2 API planes — existing apps vs. Inspect

The VideoIPath backend separates **config** (mutable, revisioned) and
**status** (read-only, subscription-friendly). Inspect's `collector` API entry
points sit under `status`, but its topology edits resolve to the **config**
plane (`nGraphElements`). Network action endpoints under
`actions/status/network/*` are also relevant for device add/sync workflows:

| Plane | Used by | Read | Write |
| ----- | ------- | ---- | ----- |
| Config | `app.topology`, `app.inventory`, **Inspect (effective store)** | `GET …/data/config/…` | `PATCH …/data/config/…` (revisioned) or RPC |
| Status | Inventory status reads, Inspect status reads | `GET …/data/status/…` | — |
| Collector (facade) | `app.inspect` | Scoped queries on `…/data/status/collector/…` (skeleton + hydration, ADR-005); `GET …/**` as eager/fallback | `POST …/actions/status/collector/updateTopology` → `nGraphElements` |
| Network actions | `app.inspect` device topology workflows | `GET …/data/status/network/virtualDevices/**`, `…/virtualTemplates/**` | `POST …/actions/status/network/addDevices`, `…/syncDevices`, `…/updateVirtualInstances` (**create** virtual devices), `…/updateVirtualTemplates`, `…/addVirtualTopology`. After create, virtual devices use the same `updateTopology` / write methods as physical devices (`InspectDevice.is_virtual`). |

So Inspect's read aggregate is status-namespace and net-new in shape, but its
writes are commit-time-validated bulk actions that land in the revisioned
`config/network/nGraphElements` store (§3.3). Staging is client-side until
commit; there is no separate server-side change-set id for the verified
`updateTopology` flow (ADR-004).

**Endpoint policy** ([ADR-006](./decisions/006-collector-only-endpoints.md)):
the Inspect package calls **only** the Inspect surface — collector data reads,
collector actions, and the network actions (`addDevices`, `syncDevices`,
virtual-device / port-template actions). The config-plane row above is context,
not a call path: the package never issues
`GET`/`PATCH …/config/network/nGraphElements` (that stays `app.topology`'s
surface). Consequence: no `_rev` is available to Inspect, and since
`updateTopology` ignores revisions anyway (last-writer-wins, verified),
concurrent-write detection is client-side compare-and-commit
([ADR-007](./decisions/007-write-consistency.md)); after a commit the
snapshot catches up via targeted scoped re-reads
([ADR-008](./decisions/008-post-commit-snapshot-refresh.md)).

Fresh status is obtained by explicit re-fetches
([ADR-001](./decisions/001-api-paradigm.md)). WebSocket subscriptions are out
of scope for this package.

### 3.3 Config store — `nGraphElements` (write target)

`GET /rest/v2/data/config/network/nGraphElements/**` →
`data.config.network.nGraphElements._items[]`. This is the **revisioned source
of truth** for topology that Inspect's `updateTopology` writes into. Its wire
shape overlaps with the Topology app, but the Inspect package models it with
standalone `InspectApi*` DTOs.

> Documented here as store/background knowledge only — the package does **not**
> read or write this endpoint at runtime
> ([ADR-006](./decisions/006-collector-only-endpoints.md)). The persisted
> element *shape* still matters: `updateTopology` `replace*` payloads carry it.

| Field | Notes |
| ----- | ----- |
| `_id` / `_vid` | Element id; edges use the `fromId::toId` key (same as collector and `replaceEdges`) |
| `_rev` | CouchDB-style revision `N-<timestamp>` for optimistic concurrency |
| `type` | Element kind (see below) |
| `descriptor` / `fDescriptor` | User label/desc vs. fallback (device-reported) label/desc |

Element `type` values:

| `type` | Represents | Key fields |
| ------ | ---------- | ---------- |
| `baseDevice` | Topology device node | `maps[]` (`cType: "Topology"`, integer `x`/`y`), `iconType`, `sdpStrategy`, `isVirtual`, `tags` (device-level only) |
| `ipVertex` | Ethernet/IP port vertex (`.in` / `.out`) | `vertexType`, `gpid.pointId`, `supports*Cfg` capability flags — **not** vertex tag bindings (§3.4) |
| `codecVertex` | Codec/SDI endpoint vertex | `vertexType` (`In`/`Out`), `codecFormat`, `useAsEndpoint`, `control`, SIPS/SDP fields — **not** vertex tag bindings (§3.4) |
| `unidirectionalEdge` | Directed link/route between vertices | `fromId`, `toId`, `weight`, `capacity`, `bandwidth`, `redundancyMode`, `weightFactors`, `conflictPri` |

**Implication:** Inspect's underlying topology store is `nGraphElements`, but
the package keeps a separate Inspect model namespace (`InspectApiBaseDevice`,
`InspectApiIpVertex`, `InspectApiUnidirectionalEdge`, …). Do not reuse topology
app model classes in Inspect DTOs. `updateTopology` is **last-writer-wins** — a
stale `_rev` in the payload is ignored
([endpoints.md](./endpoints.md#post-restv2actionsstatuscollectorupdatetopology)).

### 3.4 Tagging — device vs. vertex vs. module (Inspect vs. Topology)

Inspect distinguishes three tag scopes. This is a **key difference from
`app.topology`**, which only models tags on topology **devices** (`baseDevice`
entries in `nGraphElements`).

| Scope | What is tagged | Topology / `nGraphElements` | Inspect read surface | Write path |
| ----- | -------------- | --------------------------- | -------------------- | ---------- |
| **Device** | Topology node (`baseDevice`) | `tags` on the `baseDevice` item | `nodeStatus` `tags` / `meta.tags` / `tagsInfo`; `lookupInspectDevice` | `updateTopology` `replaceDevices` |
| **Vertex** | Individual port vertex (`ipVertex`, `codecVertex`, …) | **Not present** — no vertex-tag field on persisted graph elements | Hydrated port `tagsInfo`; editable form in `lookupInspectVertexByIds` | `updateTopology` `replaceVertices` (`localAssignedTags`) |
| **Module** | Device module / slot | **Not present** | Hydrated module `tagsInfo` on `nodeStatus` | `assignTag` / `unassignTag` with `elementIds: ["device:{modulePid}"]` |

**Implications for the package:**

- `app.topology` reads/writes device tags via `nGraphElements` only. It has no
  API for binding tags to a vertex id such as
  `device-a.module-1.port-out-1.out`, nor for module resource ids such as
  `device:device-a.dev.0`.
- `app.inspect` must treat vertex tags as a **separate concern** from the
  persisted graph element shape. Do not assume a vertex's `tags` array in an
  `nGraphElements` `ipVertex` / `codecVertex` item (if present at all) is the
  source of truth for tag bindings — confirmed empty in captures while
  `lookupInspectVertexByIds` carries `assignedTags` and `fields.tags`.
- Stage-time baselines and compare-and-commit for vertex edits must use
  `lookupInspectVertexByIds` for tag fields ([ADR-007](./decisions/007-write-consistency.md)),
  not `nGraphElements` or the collector skeleton.
- Module tags are **not** written via `updateTopology`. The Inspect UI uses
  `POST …/actions/status/tags/assignTag` and `…/unassignTag` with a single
  `tagId` plus `elementIds`. The package diffs the desired local tag list
  against `tagsInfo.assigned.local` and issues one call per added/removed tag.
  These RPCs are separate from the topology commit (not one atomic server
  transaction).
- Collector `tagInfo` provides tag → profile metadata for the aggregate; it does
  not replace per-vertex `assignedTags` on the lookup response.

## 4. How the transport works

- `connector/` is a thin sync HTTP client built on `requests`, with two
  sub-connectors: REST v2 (`GET`/`PATCH`/`POST`) and RPC (`POST /api/*`). Basic
  auth, gzip, per-method timeouts.
- Each connector enforces an **allow-list of URL prefixes** (`ALLOWED_URLS` /
  `ALLOWED_EXACT_MATCHES`). New Inspect endpoints must be added there — but
  only Inspect-surface prefixes; `config/network/nGraphElements` is not added
  for the Inspect app ([ADR-006](./decisions/006-collector-only-endpoints.md)).
- Responses are wrapped in a common envelope (`ResponseV2Get`/`…Patch`/`…Post`)
  with a `header` (`code`, `auth`, …) and a `data`/`result` body, validated by
  Pydantic.
- Apps are **lazy-loaded** off `VideoIPathApp` and are **stateless**: every call
  re-fetches from the server (e.g. `topology.get_device` issues several `GET`s
  and rebuilds the aggregate each time). Inspect deviates deliberately: state
  is **snapshot-scoped** — a skeleton is loaded up front, detail is lazily
  hydrated into the same snapshot, and freshness means building a new snapshot
  ([ADR-005](./decisions/005-lazy-snapshot-loading.md)). There is still no
  cache across snapshots.
- Inspect models live in two layers:
  - `apps/inspect/model` — `InspectApi*` transport DTOs for HTTP payloads
  - `apps/inspect/domain` and `apps/inspect/snapshot.py` — user-facing read
    models backed by a collector snapshot and internal indexes
- App/API methods own fetching, staging, committing, and error handling.
