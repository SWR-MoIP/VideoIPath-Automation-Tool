# ADR-004: Commit-style write model (change sets)

> Status: **Accepted**
>
> Concurrency: [ADR-007](./007-write-consistency.md). Post-commit refresh:
> [ADR-008](./008-post-commit-snapshot-refresh.md).

## Decision

**Hybrid: explicit transaction via context manager, plus direct write
operations on the app.**

- **Data-only DTOs** — models represent server payloads; no behaviour methods.
- **App-level direct writes** — `place_device` / `update_*` / `connect` /
  `disconnect` / `remove_*` on the inspect app each open a single-change
  transaction and commit immediately.
- **Optional transaction** — `with app.inspect.transaction() as tx:` stages
  multiple actions; call `tx.commit()` explicitly. Exit without commit
  discards.

Staging is **client-side** until `POST …/updateTopology`. There is no separate
server-side change-set id.

Wire facts (verified 2025.4.9):

| Field | Shape |
| ----- | ----- |
| `replaceDevices` | `lookupInspectDevice.fields` (`coordinates`, `localAssignedTags` mandatory) |
| `replaceVertices` | `lookupInspectVertexById.fields` — **update-only** |
| `replaceEdges` | Raw persisted edge form, keyed `"fromId::toId"` |
| `remove` / `addExternalEdges` / `force` | id list / edge list / boolean |

Commit success requires `header.ok and data.res.ok and data.validation.result.ok`.
Apply is reject-before-apply (all-or-nothing). `updateTopology` is
last-writer-wins (ignores `_rev`).

## Consequences

- Two usage styles, both mapping to the same `updateTopology` payload.
- Context manager: commit explicitly; exit without commit discards.
- DTOs stay portable; business logic lives in the app/transaction layer.
- Single-change scripts stay ergonomic; multi-element pipeline edits use the
  transaction path for atomicity.
