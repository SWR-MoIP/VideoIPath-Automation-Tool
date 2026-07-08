# ADR-0010: Post-commit snapshot maintenance — targeted invalidation + scoped re-fetch

> Status: **Accepted** — extends [ADR-0007](./0007-lazy-snapshot-loading.md)
> to the write path ([ADR-0006](./0006-commit-write-model.md) commit model)
> Date: 2026-07-08 · Deciders: Jonas Scholl

## Context

After a successful `updateTopology` commit, the caller's `InspectSnapshot` is
stale exactly where the commit touched it. Automation flows typically continue
working with the snapshot right after a write ("connect, then assert the edge
exists"), so the state must catch up — efficiently:

- A full re-snapshot costs ~19 MB (`/**`) on the 30-device test instance
  (measured sizes in
  [endpoints.md](../endpoints.md#observed-subscription-transport-reference-only--out-of-package-scope))
  and scales with network size — unacceptable per write.
- Scoped reads are cheap: one device subtree ≈ 21 KB, the complete edge
  skeleton ≈ 84 KB.
- The change set knows precisely which entities it touched, and the commit
  response confirms them (`data.items[]` with per-item `res.ok`).
- The collector is a **status-plane projection** of the config store the
  commit writes to; the change may become visible only after a propagation
  delay (**[VERIFY]** below).

## Options

1. **Full re-snapshot after every commit.** Correct but O(network) per write —
   defeats ADR-0007.

2. **Optimistic local apply.** Translate the committed write DTOs into the
   snapshot's read shapes and patch the indexes locally, no re-read.
   - Pros: zero extra requests.
   - Cons: write shapes (`nGraphElements` element form) ≠ collector read shapes
     (status projection with `vertexInfo`, live status, `pathDescriptions`);
     the translation re-implements server logic and cannot produce the
     server-derived fields — the snapshot would hold fabricated entries.

3. **Targeted invalidation + scoped re-fetch of affected entities.** Reuse the
   ADR-0007 hydration machinery: mark what the commit touched as stale, re-read
   only that.

4. **Invalidate-only (fully lazy).** Like 3, but never re-fetch eagerly; next
   property access re-hydrates.
   - Pros: cheapest when the caller never looks again.
   - Cons: "commit, then assert" — the common automation pattern — hits the
     propagation delay unmanaged, on an access that looks local.

## Decision

**Option 3, with lazy fallback (option 4) for sections.** After a commit whose
result is success (`res.ok` and `validation.result.ok`):

1. **Compute the affected set** from the change set and the commit response
   `items[]`:
   - *devices*: keys of `replaceDevices`, removed device ids, plus the owning
     device of every replaced/removed vertex and edge endpoint (derivable from
     the id conventions — vertex `device-a.module-1.port-out-1.out` → device
     `device-a`).
   - *edge pairs*: `replaceEdges` / `addExternalEdges` keys and removed edge
     ids, mapped to their `deviceA::deviceB` pair keys (both directions belong
     to one pair item).
2. **Apply removes locally**: deleted entities leave the indexes and caches
   immediately (no read needed to know they are gone).
3. **Invalidate and eagerly re-fetch** the remaining affected entities with the
   existing scoped queries: `nodeStatus/<device-id>/…` per affected device and
   the edge-pair item per affected pair — direct pair addressing
   `externalEdgesByDeviceKey/<deviceA::deviceB>/<projection>` is **verified**
   on 2025.4.9 (returns the single pair item). Cached domain objects for these
   ids are dropped or updated so subsequent property access sees the new
   state; per-entity fetch timestamps are updated (ADR-0007).
4. **Sections go stale, not eager**: if the services section (`inspect/paths`)
   or other section-level data was loaded, mark it stale and let the next
   access re-load it (ADR-0007 lazy path). Commits change services only
   indirectly; eager re-reads here are usually wasted.
5. **Propagation handling**: the re-fetch verifies the committed change is
   visible (e.g. a replaced field has the committed value) and retries briefly
   if the projection lags; give up after a small bounded window and surface
   the staleness (log + fetch timestamp), never hang.
   **[VERIFY]** the actual delay between `updateTopology` OK and collector
   visibility on a real instance — if it is consistently ~0, drop the retry.

A failed commit changes nothing server-side (reject-before-apply, verified) —
the snapshot is left untouched.

## Consequences

- Post-commit cost is proportional to the **change set size**, not the network:
  N affected devices ⇒ ~N × 21 KB + one edge query.
- The snapshot stays a pure read model built from collector responses — no
  fabricated entries (option 2 rejected), no divergence between "what we wrote"
  and "what the server derived".
- The refresh step needs the affected-set derivation to be exact; the id
  conventions it relies on are already documented (concepts.md §3.1) and
  fixture-tested.
- Remaining `[VERIFY]` (tracked in concepts.md §5.1): the collector
  propagation delay after a commit — requires a live write test (coordinate
  nudge + revert) to size the retry window.
- Together with ADR-0009: `commit()` = pre-commit conflict check → POST →
  result evaluation → targeted refresh. One documented lifecycle.
