# ADR-001: API paradigm — data-driven, request/response

> Status: **Accepted**

## Decision

The package stays fully **data-driven and request/response**. Reads fetch
aggregates from the server; writes apply changes via explicit API calls. No
WebSocket subscriptions, no live update layer, no event-driven observation API.

Status reads use the same request/response model as configuration CRUD. If
freshness is needed, the caller re-fetches explicitly.

Primary consumers are deterministic pipeline automations — short-lived, scripted
runs that load state, apply changes, and exit.

## Consequences

- Consistent with existing apps and the automation/pipeline usage model.
- No WebSocket client, subscription machinery, or dual interaction styles.
- Live monitoring UX (as in the Inspect UI) is out of scope; automations get
  predictable, reproducible runs instead.
- See [ADR-002](./002-async-strategy.md) for the related async decision.
