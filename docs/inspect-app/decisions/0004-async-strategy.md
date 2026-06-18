# ADR-0004: Async readiness & migration

> Status: **Proposed**
> Date: 2026-06-15 · Deciders: Paul Winterstein, Jonas Scholl

## Context

The package is **sync**, built on `requests`. Two issues forces push toward async:

1. **WebSocket subscriptions** ([ADR-0003](./0003-websocket-subscriptions.md))
   are naturally async.
2. **Bulk/concurrent I/O** (Inspect's combined data set, large topologies) is
   far more efficient with concurrency.

But there is an **existing sync user base and sync test suite**, and a published
PyPI package (`0.8.x`). We must not break sync users, and we should avoid a
risky big-bang rewrite. Python is `>=3.11`, so modern async primitives
(`TaskGroup`, `asyncio.timeout`) are available.

Key structural fact in our favour: the **Pydantic models and the diff/patch
logic are I/O-agnostic**. Only the connector and the api/app methods are
I/O-bound. So async-ification is mostly a transport + method-coloring problem,
not a domain-logic rewrite.

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

_To be decided._
