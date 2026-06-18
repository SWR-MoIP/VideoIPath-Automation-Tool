# Inspect App — Architecture & Concept Docs

Planning and architecture-decision documents for adding the VideoIPath **Inspect**
app to the package. In the VideoIPath product, Inspect is the newer app that
**replaces the Topology app** — building topologies and connecting devices — and
adds service monitoring with live (WebSocket-based) updates. It does **not**
replace **Inventory**: devices are still onboarded in Inventory first, then placed
and connected in Inspect. Inspect also uses a **commit-style** write model, where
create/edit/delete actions are gathered into a change set and committed together.

In **this package**, `app.inspect` is **purely additive**: it is added alongside
the existing apps. `app.topology` and `app.inventory` keep working **unchanged** —
there is **no deprecation and no migration** planned.

These docs are **living documents** — meant to be edited and refined as the
design firms up and as the real Inspect API is reverse-engineered. The official
[VideoIPath Public API 2025 LTS](https://documenter.getpostman.com/view/11222813/2sBXihpCS8#intro)
reference is now a primary source. Nothing here is implemented yet; this is the plan.

## Reading order

1. **[concepts.md](./concepts.md)** — what Inspect is, its domain model, how it
   maps onto the existing package, and the endpoint/WebSocket discovery template
   (the `[VERIFY]` items to confirm against a real server). Cross-references the
   [Public API 2025 LTS](https://documenter.getpostman.com/view/11222813/2sBXihpCS8#intro)
   reference.
2. **[decisions/](./decisions/)** — the architecture decisions (ADRs), one per
   topic. Start with [the index](./decisions/README.md).
3. **[implementation-plan.md](./implementation-plan.md)** — phased, non-breaking
   rollout, target package layout, milestones, and risks.

> **Wider context:** the package-wide re-think that grew out of this Inspect
> work — one unified `Device` / `Connection` domain model that hides the
> Inventory / Topology / Inspect split entirely — lives in
> [`../domain-architecture.md`](../domain-architecture.md).

## Decision log

| Question (from the brief)                          | Decision record                                              | Status   |
| -------------------------------------------------- | ------------------------------------------------------------ | -------- |
| Data-driven vs. event/action-driven API?           | [ADR-0001](./decisions/0001-api-paradigm.md)                 | Open     |
| Always sync/load vs. lazy load vs. cached state?    | [ADR-0002](./decisions/0002-loading-and-state.md)            | Open     |
| Use WebSockets for event subscriptions?             | [ADR-0003](./decisions/0003-websocket-subscriptions.md)      | Open     |
| Make the package async-ready? Support non-async?    | [ADR-0004](./decisions/0004-async-strategy.md)               | Open     |
| How to test E2E (low-effort, stable, trustworthy)?  | [ADR-0005](./decisions/0005-e2e-testing.md)                  | Open     |
| How are config writes applied (immediate vs. commit)? | [ADR-0006](./decisions/0006-commit-write-model.md)        | Open     |

## Status legend

- **Draft** — concept/plan being shaped.
- **Proposed / Accepted / Superseded** — for ADRs, see
  [the decisions index](./decisions/README.md).

> ADRs currently capture **context and options only** — decisions are open.
> Promote an ADR to **Accepted** once agreed, and tick off `[VERIFY]` items in
> [concepts.md](./concepts.md) as they are confirmed.
