# Inspect App — Architecture

Design record for the VideoIPath **Inspect** app in this package
(`src/videoipath_automation_tool/apps/inspect/`).

In the VideoIPath product, Inspect replaces the Topology app for building
topologies and connecting devices, and adds service monitoring. It does **not**
replace **Inventory**: devices are still onboarded in Inventory first, then
placed and connected in Inspect. Writes use a **commit-style** model — create /
edit / delete actions are gathered into a change set and committed together.

In this package, `app.inspect` replaces `app.topology`: `TopologyApp` emits a
deprecation warning on VideoIPath 2025.x and raises on 2026.x+.
`app.inventory` remains unchanged. Offline unit tests live under
`tests/inspect/`; live E2E under `tests/e2e/inspect/`. For usage, see the
[Inspect getting-started page](../../getting-started-guide/03_B_Inspect.md).

## Reading order

1. **[concepts.md](./concepts.md)** — what Inspect is, the collector facade,
   domain model (including the Inspect-vs-Topology tagging split), and how it
   maps onto the package.
2. **[models.md](./models.md)** — transport `InspectApi*` DTOs, `InspectSnapshot`,
   and user-facing domain objects (`InspectDevice`, `InspectPort`, …).
3. **[endpoints.md](./endpoints.md)** — anonymized endpoint reference with
   concrete request/response shapes (verified on VideoIPath 2025.4.9).
4. **[decisions/](./decisions/)** — architecture decisions. Start with
   [the index](./decisions/README.md).

> **Wider context:** a package-wide re-think that grew out of this work — one
> unified `Device` / `Connection` domain model — lives in
> [`../future/unified-domain-architecture.md`](../future/unified-domain-architecture.md).

## Decision log

| Question | Decision | Status |
| -------- | -------- | ------ |
| Data-driven vs. event/action-driven API? | [ADR-001](./decisions/001-api-paradigm.md) | Accepted |
| Make the package async-ready? | [ADR-002](./decisions/002-async-strategy.md) | Accepted |
| How to test E2E? | [ADR-003](./decisions/003-e2e-testing.md) | Accepted |
| How are config writes applied? | [ADR-004](./decisions/004-commit-write-model.md) | Accepted |
| Always sync/load vs. lazy load vs. cached state? | [ADR-005](./decisions/005-lazy-snapshot-loading.md) | Accepted |
| Which API surface may the package call? | [ADR-006](./decisions/006-collector-only-endpoints.md) | Accepted |
| How are concurrent writes detected? | [ADR-007](./decisions/007-write-consistency.md) | Accepted |
| How does the snapshot catch up after a commit? | [ADR-008](./decisions/008-post-commit-snapshot-refresh.md) | Accepted |
