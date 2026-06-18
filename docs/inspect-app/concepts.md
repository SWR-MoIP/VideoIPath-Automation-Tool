# Inspect App — Concepts & Technical Model

> Status: **Draft** · Last updated: 2026-06-18
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

In recent VideoIPath releases the Inspect app **replaces the Topology app**: it
becomes the entry point for building the network connectivity model (vertices,
edges, device placement), connecting devices, and watching their live
operational status — including **WebSocket event subscriptions** for live
updates. Inspect applies configuration changes with a **commit-style** model:
create/edit/delete actions are gathered into a change set and committed together
(see [ADR-0006](./decisions/0006-commit-write-model.md)).

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

**Reads** — one server-built aggregate:

- `GET /rest/v2/data/status/collector/**` → `data.status.collector` (§3.1)
- Bundles topology nodes, inter-device edges, services/paths, live status, and
  security context in a single tree with `_items[]` collections.

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
land in `config/network/nGraphElements`. Confirmed by capture — the edge
`device0.1.10.out::device1.1.11.in` set to `weight: 1` via `updateTopology`
appears in `GET …/data/config/network/nGraphElements/**` with `weight: 1` and a
bumped `_rev`. So the collector is a **facade**: a status-namespace read/action
surface in front of the revisioned `nGraphElements` config store (§3.3).

**Shared with existing apps** — the underlying store and its models, not the
collector wire shape:

- The config store `nGraphElements` is **the same one `app.topology` already
  reads and models** (`BaseDevice`, `IpVertex`, `UnidirectionalEdge`,
  `codecVertex`). Inspect edits land there, revisioned with `_rev` (§3.3).
- REST v2 envelope, session/XSRF auth, pid/id formats
- Vertex ids (`device0.1.10.out`), edge keys (`fromId::toId`)
- `descriptor` / `fDescriptor` objects, `sa` / `severity` status semantics
- Device positions as float coordinates — `meta.coordinates` in the collector
  aggregate, `maps[].x/y` in `nGraphElements`, same *Inspect Topology* format as
  `inspect_app_format` in the topology app

**Net-new for `app.inspect`:**

| Layer | Responsibility |
| ----- | -------------- |
| Collector read/parse | Model and parse `data.status.collector` |
| Change-set / commit write | Assemble `updateTopology` payloads, handle validation responses |
| Live / events | WebSocket subscriptions for status deltas |

Inventory onboarding stays on the existing path (`config/devman/devices`,
`/api/updateDevices`). `app.topology` and `app.inventory` remain unchanged;
`app.inspect` is additive.

## 3. Domain model

How Inspect concepts map onto existing package concepts:

| Inspect concept        | Inspect API (collector)                                | Existing model / app                          |
| ---------------------- | ------------------------------------------------------ | --------------------------------------------- |
| Device (inventory)     | Prerequisite — not part of collector; onboard via `config/devman/devices` | `InventoryDevice` (`apps/inventory`) |
| Device (topology node) | Read: `collector.inspect.nodeStatus`; stored as `baseDevice` in `nGraphElements` | `TopologyDevice` (`apps/topology`) — store reuses existing model |
| Vertices / Edges       | Read: `nodeStatus` `vertexInfo` / `externalEdgesByDeviceKey`; stored as `ipVertex` / `codecVertex` / `unidirectionalEdge` in `nGraphElements` | `BaseDevice`, `IpVertex`, `UnidirectionalEdge` — store reuses existing models |
| Change set / commit    | `POST …/actions/status/collector/updateTopology` → writes `nGraphElements` ([ADR-0006](./decisions/0006-commit-write-model.md)) | _commit flow net-new; target store is existing `nGraphElements`_ |
| Services / paths       | `collector.inspect.paths`, `pathDescriptions` on nodes/edges | _none — net-new_ |
| Device / edge status   | Embedded in collector (`status`, `sa`/`severity`, bandwidth, PTP) | `inventory.model.device_status`, `status/network/*` — partial overlap |
| Sync status            | `syncSeverity` on nodeStatus items                     | `TopologySynchronize` via `status/network/nGraphSyncStatus` |
| Live events            | WebSocket delta subscriptions                          | _none — net-new_ |
| Connections / Partial connections | **[VERIFY]** — may relate to `pathDescriptions` / bookings | _none yet_ |

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
| Device | `device0` | `deviceId`, `pid`, `_id` on nodeStatus items |
| Module pid | `device0.dev.1` | Nested under `modules` |
| Port pid | `device0.dev.1.10` | Nested under `ports` |
| Vertex id | `device0.1.10.out` | Shorter form in `vertexInfo`; used in edge keys |
| Edge id | `device0.1.10.out::device1.1.11.in` | Same key as `replaceEdges` in `updateTopology` |
| Device pair | `device0::device1` | Key for `externalEdgesByDeviceKey` items |
| Service / path | `100001::main` | `bookingId` + path role; appears in `pathDescriptions` and `inspect.paths` |
| Resource id | `device:device0.dev.1.1` | Prefixed resource references |
| Topo endpoint ref | `topo:device0.1.1` | Used in `serviceFields.from` / `.to` |

**`vertexInfo`** on ports describes topology vertices:

- `type: "single"` — one vertex (`id`, `vertexType`: `"In"` / `"Out"`, `fields`:
  `isActive`, `isControlled`, `isEndpoint`)
- `type: "double"` — bidirectional port with separate `in` / `out` ids and labels

**Drill-down / service linkage:** `pathDescriptions` on ports and edges embed
both `deviceLevel` (local hop: input → output within a device) and
`serviceLevel` (end-to-end service: `bookingId`, `serviceLabel`, `fromStatus` /
`toStatus`, `isMain`, `serviceStatus`). This is how the UI connects topology
elements to booked services — e.g. booking `100001` `"Encoder 1.1 -> Decoder 1.5"`
traverses `device0.1.10.out::device1.1.11.in`.

**Edge live status** (`externalEdgesByDeviceKey`): each edge carries
`bandwidth`, `fromStatus` / `toStatus`, `pathDescriptions`, and aggregate
`status` (`alarm`, `bandwidth`, `maintenance`, `ptp` severities).

**Node live status** (`inspect.nodeStatus`): hierarchical `status` with
`sa` / `severity` at device, module, port; plus `ptpDeviceStatus`, `syncSeverity`,
`hasEndpoints`, domains, tags.

**Package implications:**

- `app.inspect` uses `GET …/data/status/collector/**` as its canonical read
  entry point.
- Edge keys and vertex ids from reads map directly onto `updateTopology` write
  payloads.
- Commit validation references the same `bookingId`s visible in
  `pathDescriptions` (e.g. failed delete for booking `100001` / main path edge).
- **[VERIFY]** exact sub-paths behind the `/**` wildcard, projection/filter
  support, and pagination for large topologies.

### 3.2 API planes — existing apps vs. Inspect

The VideoIPath backend separates **config** (mutable, revisioned) and
**status** (read-only, subscription-friendly)
([Public API 2025 LTS](https://documenter.getpostman.com/view/11222813/2sBXihpCS8#intro)).
Inspect's `collector` API entry points sit under `status`, but its topology
edits resolve to the **config** plane (`nGraphElements`):

| Plane | Used by | Read | Write |
| ----- | ------- | ---- | ----- |
| Config | `app.topology`, `app.inventory`, **Inspect (effective store)** | `GET …/data/config/…` | `PATCH …/data/config/…` (revisioned) or RPC |
| Status | Inventory status reads | `GET …/data/status/…` | — |
| Collector (facade) | `app.inspect` | `GET …/data/status/collector/**` (composed aggregate) | `POST …/actions/status/collector/updateTopology` → `nGraphElements` |

So Inspect's read aggregate is status-namespace and net-new in shape, but its
writes are commit-time-validated bulk actions that land in the revisioned
`config/network/nGraphElements` store (§3.3). The client gathers edits locally
until commit; server-side staging / change-set ids are **[VERIFY]**
([ADR-0006](./decisions/0006-commit-write-model.md)).

Status-plane **WebSocket subscriptions** deliver event-based deltas — the live
update channel for Inspect ([ADR-0003](./decisions/0003-websocket-subscriptions.md)).

This framing underpins the API-paradigm and loading decisions
([ADR-0001](./decisions/0001-api-paradigm.md),
[ADR-0002](./decisions/0002-loading-and-state.md)).

### 3.3 Config store — `nGraphElements` (write target)

`GET /rest/v2/data/config/network/nGraphElements/**` →
`data.config.network.nGraphElements._items[]`. This is the **revisioned source
of truth** for topology that Inspect's `updateTopology` writes into, and it is
already modelled by `app.topology`.

| Field | Notes |
| ----- | ----- |
| `_id` / `_vid` | Element id; edges use the `fromId::toId` key (same as collector and `replaceEdges`) |
| `_rev` | CouchDB-style revision `N-<timestamp>` for optimistic concurrency |
| `type` | Element kind (see below) |
| `descriptor` / `fDescriptor` | User label/desc vs. fallback (device-reported) label/desc |

Element `type` values seen in capture:

| `type` | Represents | Key fields |
| ------ | ---------- | ---------- |
| `baseDevice` | Topology device node | `maps[]` (`cType: "Topology"`, integer `x`/`y`), `iconType`, `sdpStrategy`, `isVirtual` |
| `codecVertex` | Codec/SDI endpoint vertex | `vertexType` (`In`/`Out`), `codecFormat`, `useAsEndpoint`, `control`, SIPS/SDP fields |
| `ipVertex` | Ethernet/IP port vertex (`.in` / `.out`) | `vertexType`, `gpid.pointId`, `supports*Cfg` capability flags |
| `unidirectionalEdge` | Directed link/route between vertices | `fromId`, `toId`, `weight`, `capacity`, `bandwidth`, `redundancyMode`, `weightFactors`, `conflictPri` |

**Write round-trip confirmed:** the edge `device0.1.10.out::device1.1.11.in`
edited via `updateTopology` (ADR-0006 example, `weight: 1`) is present here with
`weight: 1` and `_rev: "3-…"`, and inter-device links appear as paired
unidirectional edges (`device0.1.10.out::device1.1.11.in` and
`device1.1.11.out::device0.1.10.in`, each `capacity: 65535`). Internal
fan-out edges (vertex→vertex within a device) use `capacity: 1`.

**Implication:** Inspect's underlying topology model is the existing
`nGraphElements`, so the package's `BaseDevice` / `IpVertex` /
`UnidirectionalEdge` / codec-vertex models are reusable for the **store**, even
though the **collector read aggregate** (§3.1) has its own status-oriented
shape. **[VERIFY]** whether `updateTopology` performs `_rev` checks server-side
or last-writer-wins.

## 4. How the transport works today (recap)

So the new layer fits the existing patterns rather than reinventing them:

- `connector/` is a thin sync HTTP client built on `requests`, with two
  sub-connectors: REST v2 (`GET`/`PATCH`/`POST`) and RPC (`POST /api/*`). Basic
  auth, gzip, per-method timeouts.
- Each connector enforces an **allow-list of URL prefixes** (`ALLOWED_URLS` /
  `ALLOWED_EXACT_MATCHES`). New Inspect endpoints must be added there.
- Responses are wrapped in a common envelope (`ResponseV2Get`/`…Patch`/`…Post`)
  with a `header` (`code`, `auth`, …) and a `data`/`result` body, validated by
  Pydantic.
- Apps are **lazy-loaded** off `VideoIPathApp` and are **stateless**: every call
  re-fetches from the server (e.g. `topology.get_device` issues several `GET`s
  and rebuilds the aggregate each time).

## 5. Endpoint discovery — how to fill in the **[VERIFY]** gaps

Two complementary sources: the **official reference** (authoritative for the
documented surface) and **browser capture** (authoritative for what the Inspect
GUI actually does, including undocumented calls and WebSocket frames).

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
   open a device, connect two devices, **commit a change set**, drill into a
   service, watch live updates. Note REST calls *and* the WebSocket (`WS`
   filter) frames.
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
- [ ] Collector sub-paths: exact URLs behind the `/**` wildcard; projection/filter/pagination support
- [ ] Connections / Partial Connections: resource paths, shapes, lifecycle
- [x] Change set / commit endpoint: `POST /rest/v2/actions/status/collector/updateTopology` — bulk delta with `replaceDevices`, `replaceVertices`, `replaceEdges` (key `"fromId::toId"`), `replaceResourceTransforms`, `addExternalEdges`, `remove`, `force` ([ADR-0006](./decisions/0006-commit-write-model.md))
- [ ] Change set staging: server-side change-set id vs. client-only gather until commit
- [x] Commit failure response: check `data.res.ok` / `data.validation.result.ok` (not `header.ok`); `validation.details[id]` carries `status`, `rev`, `resolvable`, `type`; failed delete example: `"A required edge was not found. (main)"`, `items: []` ([ADR-0006](./decisions/0006-commit-write-model.md))
- [ ] Commit success response: `data.items` shape when validation passes
- [ ] Commit semantics: partial apply after validation pass, discard/rollback of abandoned client-side change sets
- [ ] Import / Export (preview): scope and payload format
- [x] Write/action endpoint: `/rest/v2/actions/status/collector/updateTopology` (others under `…/actions/status/collector/*` still **[VERIFY]**)
- [x] Config store / write target: `updateTopology` lands in `GET /rest/v2/data/config/network/nGraphElements/**` (`_items[]`, `_rev`, `type` ∈ `baseDevice` / `codecVertex` / `ipVertex` / `unidirectionalEdge`); reuses existing topology models (§3.3)
- [ ] `_rev` handling on commit: does `updateTopology` enforce optimistic concurrency or last-writer-wins?
- [ ] Version gating: first VideoIPath version that exposes each endpoint

WebSocket (see [ADR-0003](./decisions/0003-websocket-subscriptions.md)):

- [ ] URL / scheme (`ws://` vs `wss://`, path, port)
- [ ] Auth handshake (Basic header, cookie/session, query token?)
- [ ] Subscribe / unsubscribe message format (which resources can be watched?)
- [ ] Event/patch frame format (full snapshot vs. delta/patch; ids & revisions)
- [ ] Heartbeat / keep-alive, server-side timeouts, reconnect & resync semantics
- [ ] Back-pressure / message ordering / dropped-update guarantees

## 6. Open questions

- **Collector sub-paths and scaling** — exact URLs behind `/**`; projection,
  filtering, and pagination for large topologies
  ([ADR-0002](./decisions/0002-loading-and-state.md)).
- **WebSocket scope** — generic subscription to any `status/...` path, or
  Inspect-specific streams? ([ADR-0003](./decisions/0003-websocket-subscriptions.md))
- **Commit model** ([ADR-0006](./decisions/0006-commit-write-model.md)) —
  server-side change-set id vs. client-only gather; successful response shape
  (`data.items`); all-or-nothing apply after validation; meaning of validation
  `status` codes and `resolvable: true` cases.
- **Commit concurrency** — `updateTopology` writes bump `nGraphElements` `_rev`
  (§3.3); does the action enforce `_rev` checks or last-writer-wins?
- **Connections / Partial Connections** — relationship to `pathDescriptions`,
  bookings, and the Public API `Connections` resources.
