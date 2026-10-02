# ADR-002: Plan, then apply, without a spanning transaction

> Status: **Accepted**
>
> Field ownership: [ADR-003](./003-managed-fields.md). Gateways:
> [ADR-005](./005-app-gateways.md).

## Context

Callers need to review driver settings, names, and vertex edits before anything
is written. Inventory creates and Inspect commits are different server
operations. Driver discovery after an Inventory write is not available in the
same response.

## Options

- Write immediately inside `apply()`, with no stored preview.
- One client-side transaction that rolls every phase back on failure.
- A frozen plan, then a phased apply that reports how far it got.

## Decision

`engine.plan(...)` is read-only and returns an immutable `BlueprintPlan`.
`plan.apply()` takes no configuration. It re-checks the captured baselines and
executes that plan. `engine.apply(...)` is plan plus apply.

Phases run in order: inventory, discovery, topology sync, topology commit,
module tags, verification. Absent or unchanged phases are skipped. Inventory
and Inspect writes are separate. Nothing rolls back an earlier phase.

When topology edits depend on earlier work, the plan marks those phases
`deferred` and sets `fully_resolved` to `False`. During apply the engine waits
for discovery, then computes the edits from the blueprint, parameters, naming,
and target captured on the plan. A dry run does not invent those edits. It
reports the phases as `deferred`.

`dry_run=True` runs the stale-plan, conflict, and pending-edit checks and
performs no write.

## Consequences

- A reviewed plan cannot be silently retargeted. Changing options or variants
  means a new plan.
- A plan holds private captured state, including credentials, and the executor
  bound to the app. It is not a serializable job description.
- A failure after Inventory create is `partial`. The result carries
  `inventory_id` so the caller can bind it and retry without creating a second
  record.
- A write that raises, when the client cannot prove the server rejected it, is
  `unknown`. The caller reads the server back (a new plan does that) before
  retrying.
- There is no automatic undo. Callers that need a single all-or-nothing change
  have to split scopes themselves: apply inventory, add the device, then review
  a fully resolved topology plan.
