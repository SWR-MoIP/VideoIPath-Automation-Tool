# Architecture Decision Records — Inspect App

Each ADR captures the **context, research, and options** for one architectural
question. Once a choice is made, the **Decision** and **Consequences** sections
are filled in and the status moves to **Accepted**. ADRs are immutable once
accepted — to change a decision, add a new ADR that supersedes the old one
(update the `Status` line of both).

## Status legend

- **Proposed** — context and options documented; decision not yet made.
- **Accepted** — agreed; implement accordingly.
- **Superseded by ADR-XXXX** — replaced; kept for history.
- **Deprecated** — no longer relevant.

## Index

| ADR                                                   | Title                                | Status     |
| ----------------------------------------------------- | ------------------------------------ | ---------- |
| [0001](./0001-api-paradigm.md)                        | API paradigm: data-driven            | Accepted   |
| [0002](./0002-loading-and-state.md)                   | Loading & state model                | Superseded by ADR-0007 |
| [0003](./0003-websocket-subscriptions.md)             | WebSocket event subscriptions        | Deprecated |
| [0004](./0004-async-strategy.md)                      | Async readiness & migration          | Accepted   |
| [0005](./0005-e2e-testing.md)                         | E2E testing strategy                 | Accepted   |
| [0006](./0006-commit-write-model.md)                  | Commit-style write model (change sets) | Accepted   |
| [0007](./0007-lazy-snapshot-loading.md)               | Skeleton-first loading & lazy hydration | Accepted   |
| [0008](./0008-collector-only-endpoints.md)            | Collector-only endpoint policy       | Accepted   |
| [0009](./0009-write-consistency.md)                   | Write consistency (compare-and-commit) | Accepted   |
| [0010](./0010-post-commit-snapshot-refresh.md)        | Post-commit snapshot refresh         | Accepted   |

## Template

```markdown
# ADR-XXXX: <short title>

> Status: Proposed | Accepted | Superseded by ADR-YYYY
> Date: YYYY-MM-DD · Deciders: <names>

## Context
What problem are we solving? What constraints apply (existing code, users,
versions)?

## Options
1. Option A — pros / cons
2. Option B — pros / cons
3. ...

## Decision
_To be decided._ (fill in once a choice is made)

## Consequences
_Add once a decision is made._
```
