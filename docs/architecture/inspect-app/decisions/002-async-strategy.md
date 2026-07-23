# ADR-002: Async readiness & migration

> Status: **Accepted**

## Decision

**Stay sync at the package boundary; use internal parallelism only where a
single action needs multiple API requests.**

The public API remains synchronous — no `async`/`await` surface, no dual-stack
codegen, no migration to `httpx` async clients. When one high-level operation
(e.g. skeleton load of devices + edges, or bulk device preload) requires several
independent `GET`s, those requests may be issued **in parallel internally**
(e.g. thread pool). This is an implementation detail, not a new interaction
model for callers.

## Consequences

- Zero breaking change for existing sync users and scripts.
- No async test matrix, no `unasync` tooling, no sync-over-async footguns.
- Performance gains are limited to multi-request reads/writes inside the
  library; callers do not manage concurrency themselves.
- A future async public API would require a new ADR; it is not planned now.
