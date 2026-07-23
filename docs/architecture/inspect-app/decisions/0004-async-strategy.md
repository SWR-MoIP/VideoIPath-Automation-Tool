# ADR-0004: Async readiness & migration

> Status: **Accepted**
> Date: 2026-06-15 · Deciders: Paul Winterstein, Jonas Scholl

## Context

The package is **sync**, built on `requests`. Bulk reads (e.g. assembling a full
device aggregate) can benefit from **concurrent I/O** when a single high-level
action requires multiple API requests.

There is an **existing sync user base and sync test suite**, and a published
PyPI package (`0.8.x`). We must not break sync users, and we should avoid a
risky big-bang rewrite. WebSocket subscriptions ([ADR-0003](./0003-websocket-subscriptions.md))
are out of scope, removing the main reason for an async public API.

Key structural fact: the **Pydantic models and diff/patch logic are
I/O-agnostic**. Only the connector and api/app methods are I/O-bound.

## Options

1. **Stay sync-only; thread the WebSocket.**
   - Pros: lowest risk; no breaking changes; ships now.
   - Cons: no concurrency for bulk ops; doesn't future-proof.

2. **Async-first, sync as a thin shim** (`asyncio.run` / run-in-thread wrappers).
   - Pros: one source of truth (async); future-proof.
   - Cons: breaking for current sync users; sync-over-async shims have real
     footguns (event-loop reentrancy, nested loops in notebooks, thread-pool
     surprises); large immediate change.

3. **Dual-stack on a shared core:** migrate the transport to
   `httpx` (one library, sync **and** async clients with the same API), keep the
   Pydantic models + diff logic shared, and provide both a sync and an async API
   surface. Maintain the two surfaces from one source using a code transform
   (e.g. [`unasync`](https://github.com/python-trio/unasync)) rather than by
   hand.
   - Pros: sync users keep working; async users get first-class support;
     WebSocket fits the async side; minimal duplicated logic.
   - Cons: build-time codegen/tooling to set up; both surfaces must be tested.

## Decision

**Stay sync at the package boundary; use internal parallelism only where a
single action needs multiple API requests.**

The public API remains synchronous — no `async`/`await` surface, no dual-stack
codegen, no migration to `httpx` async clients. When one high-level operation
(e.g. loading a full device aggregate) requires several independent `GET`s,
those requests may be issued **in parallel internally** (e.g. thread pool) to
reduce latency. This is an implementation detail of the connector/read path, not
a new interaction model for callers.

## Consequences

- Zero breaking change for existing sync users and scripts.
- No async test matrix, no `unasync` tooling, no sync-over-async footguns.
- Performance gains are limited to multi-request reads/writes inside the
  library; callers do not manage concurrency themselves.
- A future async public API would require a new ADR; it is not planned now.
