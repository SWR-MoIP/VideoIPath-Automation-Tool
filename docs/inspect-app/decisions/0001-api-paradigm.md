# ADR-0001: API paradigm — data-driven, request/response

> Status: **Accepted**
> Date: 2026-06-15 · Deciders: Paul Winterstein, Jonas Scholl

## Context

The package today is **data-driven**: the user fetches a configuration
aggregate (`InventoryDevice`, `TopologyDevice`), mutates the object locally, and
calls `update_*`, which diffs against the server state and `PATCH`es only the
changed elements (revision-checked). It is stateless and request/response based.

Inspect adds a **monitoring** dimension (services, status, drill-down). The
primary consumers are **deterministic pipeline automations** — short-lived,
scripted runs that load state, apply changes, and exit. For that usage model,
live event streams and WebSocket subscriptions add complexity without clear
benefit: each run should start from an explicit server read and produce a known
outcome.

The question was whether to keep everything data-driven, move to an
event/action-driven model, or combine the two. This maps onto the config-plane
vs. status-plane split described in
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

**Option 1: data-driven only (request/response).**

The package stays fully data-driven. Reads fetch aggregates from the server;
writes apply changes via explicit API calls. No WebSocket subscriptions, no live
update layer, no event-driven observation API.

Status reads use the same request/response model as configuration CRUD. If
freshness is needed, the caller re-fetches explicitly.

## Consequences

- Consistent with existing apps and the automation/pipeline usage model.
- No WebSocket client, subscription machinery, or dual interaction styles to
  build or document.
- Live monitoring UX (as in the Inspect UI) is out of scope for the package;
  automations get predictable, reproducible runs instead.
- See [ADR-0003](./0003-websocket-subscriptions.md) (deprecated) and
  [ADR-0004](./0004-async-strategy.md) for related decisions.
