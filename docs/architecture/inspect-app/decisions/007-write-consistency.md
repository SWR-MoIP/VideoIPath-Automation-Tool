# ADR-007: Write consistency — client-side compare-and-commit

> Status: **Accepted** — complements [ADR-004](./004-commit-write-model.md)
> under the [ADR-006](./006-collector-only-endpoints.md) endpoint policy

## Decision

**Compare-and-commit, built into the change-set lifecycle** (transaction and
direct-write paths both get it).

1. **Baseline at staging time.** When an entity is first staged, the change set
   fetches and stores its current form via Inspect-surface lookups (verified
   2025.4.9; none exposes a `_rev`):
   - edges: `lookupInspectEdgesByIds` — full persisted edge form, batched
   - vertices: `lookupInspectVertexByIds` — editable form (incl. tag bindings;
     see [concepts.md §3.4](../concepts.md#34-tagging--device-vs-vertex-vs-module-inspect-vs-topology))
   - devices: `lookupInspectDevice` — editable form

   The lookup forms **are** the write shapes — no client-side mapping.
   Caller mutations are applied on top of the baseline.

2. **Pre-commit conflict check.** `commit()` re-fetches the same entities and
   deep-compares against the baselines. Any mismatch aborts the whole commit
   and raises `InspectCommitConflictError` (entity ids + field diffs).

3. **Override is explicit.** `commit(check_conflicts=False)` skips the check —
   deliberate last-writer-wins. The server's `force` flag is unrelated.

4. **Commit result still rules.** Compare-and-commit runs *before* the POST;
   `data.res.ok` / `data.validation.result.ok` evaluation after the POST is
   unchanged (ADR-004).

## Consequences

- **Honest guarantee: detection, not enforcement.** The re-read→POST window
  (TOCTOU) cannot be closed with the current server. Re-check per server
  version whether `updateTopology` gains rev enforcement.
- One extra lookup round per stage and per commit — bounded by change-set size,
  batchable via the `…ByIds` actions.
- Snapshot data is **not** used as the baseline; baselines always come from
  fresh lookups at stage time.
- Lookups return the **effective** label (persisted `descriptor` merged with
  `fDescriptor` fallback). Round-tripping without an explicit label change pins
  the fallback into `descriptor` — don't touch label fields unless the caller
  set them.
