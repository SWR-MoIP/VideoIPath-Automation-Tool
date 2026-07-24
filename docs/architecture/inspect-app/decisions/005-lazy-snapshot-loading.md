# ADR-005: Skeleton-first snapshot loading with lazy hydration

> Status: **Accepted**

## Decision

**Skeleton-first snapshot with transparent per-entity lazy hydration.** The
`InspectSnapshot` state is allowed to be partially populated and accretes as
details are fetched. There is **no client-side cache across snapshots** —
fresh data means building a new snapshot.

- **Skeleton load.** Two parallel scoped GETs (queries in
  [endpoints.md](../endpoints.md#collector-scoped-queries-captured-from-the-inspect-ui)):
  - *Device skeleton*: `inspect/nodeStatus` with `modules/"_noId"` — identity,
    descriptor, coordinates, status, syncSeverity, tags; no modules/ports.
  - *Edge skeleton*: `externalEdgesByDeviceKey` lean projection — device pair,
    edge ids, endpoint labels/context, status severities.
- **Per-entity hydration.** First access to an unloaded device property
  (`ports`, …) fetches that device's `nodeStatus` subtree (`modules/*`).
  Hydration is idempotent and cached.
- **Section-level lazy loads.** Services (`inspect/paths`) and alarms
  (`status/alarms/current`) load as whole sections on first touch.
- **Eager mode.** `load="full"` → one `GET …/collector/**` for small
  environments or point-in-time consistency. Fixture-built snapshots are fully
  hydrated with lazy loading inert.

## Consequences

- **Hidden HTTP on property access.** Domain getters may perform one hydration
  request and can therefore raise connector errors and add latency. Documented,
  deliberate behaviour ([models.md](../models.md)).
- **No single point in time.** Skeleton and hydrated subtrees are fetched at
  different moments; the snapshot records a fetch timestamp per entity/section.
- **N+1 for detail iteration.** Mitigation: bulk preload helpers
  (`app.inspect.preload([...])`, `get_devices(detail=True)`) that parallelize
  hydration ([ADR-002](./002-async-strategy.md)); the skeleton alone answers
  most bulk questions.
- Scoped queries verified on 2025.4.9; the untrimmed UI projection hits
  HTTP 414 — use a trimmed skeleton projection.
