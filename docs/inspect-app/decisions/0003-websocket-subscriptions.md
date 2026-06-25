# ADR-0003: WebSocket event subscriptions

> Status: **Deprecated**
> Date: 2026-06-15 · Deciders: Paul Winterstein, Jonas Scholl

## Context

The VideoIPath server exposes a **WebSocket channel** for live status/event
updates. This ADR originally explored how the Python package might consume
those subscriptions.

The package has no WebSocket client today; the connector layer is sync
`requests`. [ADR-0001](./0001-api-paradigm.md) now accepts a fully
data-driven, request/response model for deterministic pipeline automations,
which makes WebSocket support unnecessary for the package's scope.

The [Public API 2025 LTS](https://documenter.getpostman.com/view/11222813/2sBXihpCS8#intro)
reference **confirms** the high-level model: the `status` plane is "frequently
updated and a good candidate for subscriptions", and subscription handling uses
**event-based (delta) change reporting** from server to client. So the *shape*
(deltas over a persistent channel on the status plane) is settled; the **exact
protocol details** (URL, auth handshake, subscribe message, concrete frame
format, heartbeat, reconnect) remain **[VERIFY]** — capture them per
[concepts.md §5](../concepts.md#5-endpoint-discovery--how-to-fill-in-the-verify-gaps).

## Options

1. **Skip WebSocket; poll status endpoints.**
   - Pros: no new dependency or concurrency; trivial.
   - Cons: laggy, chatty, misses the feature's point; doesn't scale to many
     watched entities.

2. **Async-native WebSocket only** (e.g. `websockets`/`httpx-ws`), exposed via
   `async`/`await` + async iterators.
   - Pros: idiomatic, efficient, composes with other async I/O.
   - Cons: forces asyncio on all consumers unless wrapped; bigger change now.

3. **Sync-friendly WebSocket with a background thread** (e.g.
   `websocket-client`) exposing callbacks / a blocking iterator / a `queue`.
   - Pros: no asyncio required by users; drops into existing sync scripts.
   - Cons: thread lifecycle management; not as clean for high-concurrency.

4. **Both, behind one façade:** a transport-agnostic subscription API with a
   sync default (thread-backed) and an async implementation, sharing typed event
   models.

## Decision

**Option 1: skip WebSocket; no live subscriptions in the package.**

WebSocket event subscriptions are **out of scope**. The package does not
implement a subscription API, background listener thread, or async event stream.
Callers that need updated status re-fetch via the normal read methods.

This ADR is **deprecated** — kept for historical context on the server
capability, not as an active design direction.

## Consequences

- No new WebSocket dependency or concurrency machinery.
- Removes the primary driver for an async public API surface.
- Server-side subscription capability remains documented in
  [concepts.md](../concepts.md) for reference; a future ADR would be needed to
  revisit this if long-lived monitoring clients become a package goal.
