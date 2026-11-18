# ADR-009: Object lifetime after refresh()

> Status: **Accepted** — records the decision for issue #153. Extends
> [ADR-005](./005-lazy-snapshot-loading.md) and leaves
> [ADR-008](./008-post-commit-snapshot-refresh.md) unchanged.

## Decision

`app.inspect.refresh()` builds a new snapshot and marks the previous one replaced.
Held domain objects keep that previous snapshot.

- **Reads stay a point-in-time view** of the snapshot the object was fetched from,
  including whatever that snapshot had already hydrated.
- **Writes are rejected.** A setter calls `stage_edit` on the object's snapshot and
  raises `InspectSnapshotReplacedError` ("re-fetch the object after refresh()").
  `update()` and `InspectTransaction.update()` raise the same error when the object's
  snapshot is not the one they are bound to. A transaction whose snapshot was replaced
  raises it on staging and on commit.
- **Pending edits block refresh.** `refresh()` raises `InspectPendingEditsError` and
  lists the staged `(kind, entity_id)` keys. `refresh(discard_pending=True)` drops those
  edits, then replaces the snapshot. A failed reload does not mark the current snapshot
  replaced.
- **Post-commit refresh is not this path.** ADR-008 updates the same snapshot in place.
  Objects fetched before a commit stay writable.

`ValueError: No pending edits to flush.` is only raised when the object belongs to the
current snapshot and really has nothing staged.

## Open questions

1. **Does ADR-005 allow object identity to survive a refresh?** ADR-005 forbids reusing
   snapshot data across snapshots. It does not require destroying the Python objects.
   Resolving a held object against the app's new snapshot (option B) would couple object
   identity to a snapshot it was not built from. This decision keeps the snapshots
   independent: the new one shares nothing with the old one, and the old one remains
   readable.
2. **Pending edits.** Refuse, unless the caller passes `discard_pending=True`.
3. **Entity gone after refresh.** The held object still reads the old snapshot. A
   re-fetch returns `None` (or not found) when the id is absent. A write on the held
   object raises `InspectSnapshotReplacedError`, not a not-found error.
4. **Lazy hydration.** Hydration state belongs to the snapshot. A held object does not
   see devices hydrated only on the new snapshot, and the new snapshot does not inherit
   the old one's cache. A later lazy load on the old snapshot still uses that snapshot's
   fetcher; it does not become the app's current view.
5. **Point-in-time reads.** Yes. Holding the object is how a caller keeps the view from
   before `refresh()`. Writes are not part of that view.

## Consequences

- Callers re-fetch by id after `refresh()` before they change an object. After a commit
  they do not.
- A staged edit cannot be committed against a snapshot the app has already replaced, and
  it cannot be dropped by `refresh()` without `discard_pending=True`.
