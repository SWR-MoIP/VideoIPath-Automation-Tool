# ADR-0001: API paradigm — data-driven core + event layer

> Status: **Proposed**
> Date: 2026-06-15 · Deciders: Paul Winterstein, Jonas Scholl

## Context

The package today is **data-driven**: the user fetches a configuration
aggregate (`InventoryDevice`, `TopologyDevice`), mutates the object locally, and
calls `update_*`, which diffs against the server state and `PATCH`es only the
changed elements (revision-checked). It is stateless and request/response based.

Inspect adds a **monitoring** dimension (services, live status, drill-down) and
a **WebSocket** channel. Monitoring is naturally **event/observation-driven**:
the client reacts to changes it did not initiate. So the question is whether to:

- keep everything data-driven (poll for status), or
- move to an event/action-driven model, or
- combine the two.

This maps cleanly onto the config-plane vs. status-plane split described in
[concepts.md](../concepts.md#3-domain-model).

## Options

1. **Data-driven only (status via polling).**
   - Pros: zero conceptual change; consistent with existing apps; trivial to
     test; no new dependencies.
   - Cons: polling is chatty and laggy for live monitoring; ignores the new
     WebSocket capability that motivated the work.

2. **Event/action-driven only.**
   - Pros: best fit for live monitoring; matches Inspect's UX.
   - Cons: poor fit for configuration CRUD (which is inherently
     request/response + revisioned); large departure from existing apps; high
     migration cost; harder to reason about for simple scripts.

3. **Hybrid: data-driven CRUD for the config plane, event-driven observation for the status plane.**
   - Pros: each plane uses the model that fits it; preserves the existing CRUD
     surface and tests; isolates the new event machinery; lets users opt into
     live features only when needed.
   - Cons: two interaction styles in one app; must document clearly which
     methods are "read/modify/write" vs. "subscribe/observe".

## Decision

_To be decided._
