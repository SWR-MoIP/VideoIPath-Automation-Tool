# ADR-0002: Loading & state model

> Status: **Proposed**
> Date: 2026-06-15 · Deciders: Paul Winterstein, Jonas Scholl

## Context

This ADR is about **how data is fetched from the VideoIPath API** — eager vs.
lazy, how much is pulled per call, and whether anything is cached client-side.
It is **not** about app-object construction; the lazy `app.inspect` property
(built on first access, like the other apps) is a separate, settled detail and
out of scope here.

Existing apps are **stateless** and **fetch-on-demand**: each call re-reads from
the server and rebuilds objects. A single read can be chatty — e.g.
`topology.get_device` issues several `GET`s and reassembles the aggregate every
time.

**Usage context matters:** this package is used for **automations, pipelines and
bulk operations** — typically short-lived, scripted, do-and-exit runs — not
long-lived dashboards or applications. That favours **predictability and
freshness** over client-side caching, and makes **efficient bulk reads** the
real performance concern.

Two sub-questions follow:

1. **Per read** — fetch the full aggregate eagerly, or lazily/narrowly?
2. **Across reads** — stay stateless, or cache client-side?

## Options

1. **Stateless, eager per-entity (status quo).** Each call fetches the full
   aggregate for the requested entity.
   - Pros: predictable, always fresh, no cache-invalidation, easy to test,
     matches existing apps; yields one coherent object.
   - Cons: chatty; pulls more than a bulk job often needs; N+1 when iterating
     many entities.

2. **Stateless + field/section projection & bulk helpers.** Default to eager per
   entity, but let callers request only the fields/sections they need and offer
   list-with-projection helpers. (REST v2 already supports projections, e.g.
   `/id,rev,vid`, `/maps/0/x,y`.)
   - Pros: keeps statelessness & freshness; cuts payload and request count for
     pipelines/bulk ops; still simple to test.
   - Cons: more method surface (projection params); caller must know which
     sections it needs.

3. **Client-side cache / long-lived snapshot.** Hydrate once and serve
   subsequent reads locally (optionally refreshed via WebSocket).
   - Pros: cheap repeated reads for a long-running process.
   - Cons: stateful; staleness & cache-invalidation risk; consistency issues vs.
     concurrent writers; little benefit for short-lived automations; harder to
     test.

## Decision

_To be decided._
