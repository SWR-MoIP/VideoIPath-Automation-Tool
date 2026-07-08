# ADR-0007: Skeleton-first snapshot loading with lazy hydration

> Status: **Accepted** — supersedes the per-read decision of
> [ADR-0002](./0002-loading-and-state.md)
> Date: 2026-07-08 · Deciders: Jonas Scholl

## Context

[ADR-0002](./0002-loading-and-state.md) decided "stateless, eager per-entity —
always load the full aggregate." For the Inspect snapshot this means
`GET /rest/v2/data/status/collector/**`: one request whose payload is
O(entire network) and dominated by module/port subtrees and the heavily
denormalized `pathDescriptions`. On large environments (thousands of nodes)
this is too slow for the common automation case, which typically touches the
graph structure of all devices but the *detail* of only a few.

Two facts changed since ADR-0002 was accepted (see
[endpoints.md — Collector Scoped Queries](../endpoints.md#collector-scoped-queries-captured-from-the-inspect-ui)):

1. A WebSocket capture of the Inspect UI proves the collector supports
   **scoped queries** on its sub-paths: `* where <expr>` filters, `limit N`,
   `order by`, and deep field projections — the `[VERIFY]` item from
   ADR-0002/concepts §6 is resolved.
2. The **vendor UI itself loads skeleton-first**: its main topology query
   suppresses the module subtree (`modules/"_noId"` → `modules: {}`) and its
   edge query projects only ids, labels, and status severities. Full module/
   port detail is fetched by separate, narrower queries.

The usage context from ADR-0002 still holds: short-lived automation runs that
favour predictability and freshness — but the "efficient bulk reads" concern
now outweighs "one request returns everything."

## Options

1. **Eager full aggregate (status quo, ADR-0002).** One `/**` fetch per
   snapshot.
   - Pros: single request; point-in-time consistent; simplest.
   - Cons: O(network) payload; seconds–minutes on large plants; most of the
     data is never touched.

2. **Skeleton + transparent per-entity lazy hydration into one accreting
   snapshot state.**
   - Pros: initial load ~proportional to device/edge count, not port count;
     detail cost paid only for entities actually inspected; mirrors the vendor
     UI's own strategy; domain surface unchanged (property access just works).
   - Cons: hidden HTTP on property access; snapshot no longer single-point-in-
     time; N+1 risk when iterating details; more bookkeeping.

3. **Skeleton + explicit `load_details()` calls.**
   - Pros: no hidden I/O; explicit cost model.
   - Cons: leaks the loading mechanics into every user workflow; unloaded
     property access needs error or `None` semantics — worse ergonomics.

4. **Per-field projections on every access.**
   - Pros: minimal bytes per read.
   - Cons: extremely chatty; complex merge bookkeeping; no coherent entity
     objects.

## Decision

**Option 2: skeleton-first snapshot with transparent per-entity lazy
hydration.** The internal-state concept of `InspectSnapshot` is unchanged —
one snapshot, one set of indexes, domain objects resolve through it — but the
state is allowed to be **partially populated** and accretes as details are
fetched.

- **Skeleton load.** A snapshot is built from two parallel scoped GETs,
  using the queries captured from the UI (endpoints.md):
  - *Device skeleton*: `inspect/nodeStatus` with the UI's projection and
    `modules/"_noId"` — identity, descriptor, `meta`/coordinates, `status`,
    `syncSeverity`, tags, `ptpDeviceStatus`; no modules/ports.
  - *Edge skeleton*: `externalEdgesByDeviceKey` with the lean projection —
    device pair, edge ids, endpoint port `context`/labels, status severities;
    no `pathDescriptions`, no bandwidth values.

  The graph structure (all devices, all edges) is therefore complete from the
  start; module/port detail and services are not.

- **Per-entity hydration.** First access to an unloaded device property
  (`ports`, port status, path drill-down, …) fetches that one device's
  `nodeStatus` subtree using the UI's detail projection (`modules/*`) scoped
  to the device. The parsed item replaces the skeleton record; port indexes
  for that device are built incrementally. Hydration is idempotent and cached
  — repeated access is local.

- **Section-level lazy loads.** Services are cross-device, so `inspect/paths`
  loads as a whole section (UI service-list projection) on first touch of
  `get_services()` / `device.services`. `maintenanceBookings`,
  `superProfiles`, and `tagInfo` load the same way if and when exposed.

- **Snapshot construction.** The snapshot holds a reference to the inspect
  API layer to perform hydration fetches. Fixture-built snapshots
  ([ADR-0005](./0005-e2e-testing.md)) are constructed from a full collector
  response with lazy loading inert. An eager mode
  (e.g. `get_snapshot(load="full")` → `/**` fetch) is retained for small
  environments and for callers needing point-in-time consistency. Scoped
  queries are verified to work as REST GETs on 2025.4.9; only the full
  UI-length projection hits HTTP 414 — use a trimmed skeleton projection
  ([endpoints.md](../endpoints.md#collector-scoped-queries-captured-from-the-inspect-ui)).

What ADR-0002 got right still stands: **no client-side cache across
snapshots**. All accreted state lives inside one snapshot's lifetime; fresh
data means building a new snapshot.

## Consequences

- **Hidden HTTP on property access.** Domain getters may perform one
  hydration request and can therefore raise connector errors and add latency.
  This is documented, deliberate behaviour (models.md).
- **No single point in time.** Skeleton and hydrated subtrees are fetched at
  different moments. The snapshot records a fetch timestamp per entity/
  section; `refresh()` still means "build a new snapshot," never
  re-fetch-and-diff.
- **N+1 returns for detail iteration.** Touching detail on every device in a
  loop degenerates to one request per device. Mitigation: bulk preload
  helpers (e.g. `snapshot.preload_devices([...])`, `get_devices(detail=True)`)
  that batch or parallelize hydration
  ([ADR-0004](./0004-async-strategy.md)); the skeleton alone answers most
  bulk questions (inventory of nodes, connectivity, sync/status severities).
- **Verification status**: all core loading items are confirmed on 2025.4.9 —
  GET equivalence, `"_noId"` semantics, single-device hydration forms,
  populated `modules/*`, payload sizes (~92 KB skeleton vs ~19 MB full). The
  only accepted limitation is HTTP 414 for the untrimmed UI projection. See
  [endpoints.md](../endpoints.md#collector-scoped-queries-captured-from-the-inspect-ui)
  and the checklist in
  [concepts.md §5.1](../concepts.md#51-discovery-checklist-fill-in-as-confirmed).
