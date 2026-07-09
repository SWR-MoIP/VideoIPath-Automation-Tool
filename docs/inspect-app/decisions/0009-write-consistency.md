# ADR-0009: Write consistency — client-side compare-and-commit

> Status: **Accepted** — complements [ADR-0006](./0006-commit-write-model.md)
> (commit model) under the [ADR-0008](./0008-collector-only-endpoints.md)
> endpoint policy
> Date: 2026-07-08 · Deciders: Jonas Scholl

## Context

Requirement: a write must not silently overwrite changes somebody else made
between our read and our commit (lost update). What the server gives us
(verified 2025.4.9, see
[endpoints.md — `updateTopology`](../endpoints.md#post-restv2actionsstatuscollectorupdatetopology)):

- **`updateTopology` is last-writer-wins.** A stale `_rev` in `replace*`
  payloads is **ignored** — there is no server-enforced optimistic locking on
  the Inspect write path. Commit-time validation protects *service integrity*
  (booking-blocked deletes, dangling edge refs), **not** concurrent edits.
- **Collector reads carry no `_rev`.** The only revisioned surface is
  `nGraphElements`, which the package does not call
  ([ADR-0008](./0008-collector-only-endpoints.md)).
- **`replace*` entries are full-object upserts** (ADR-0006): committing an edge
  weight change means sending the *complete* edge. A payload built from stale
  state clobbers every other field — so a write is exposed to lost updates even
  when the caller only intends to touch one field.
- **No server-side staging**: `validateTopology`/`discardTopology` are
  unregistered stubs; the change set exists only client-side until the one
  `updateTopology` POST (atomic, reject-before-apply).

## Options

1. **Accept last-writer-wins.** Document the risk, do nothing.
   - Pros: zero cost.
   - Cons: violates the requirement; full-object upserts make silent clobbering
     likely, not just possible.

2. **Client-side compare-and-commit.** Record a baseline of every touched
   entity at staging time; immediately before the commit POST, re-read the
   entities and compare against the baseline; abort on any drift.
   - Pros: detects concurrent modification with Inspect-surface endpoints only;
     the stage-time read is needed anyway to build full `replace*` payloads;
     conflicts surface as one typed error before anything is written.
   - Cons: a race window remains between the pre-commit re-read and the POST
     (TOCTOU) — detection, not enforcement; costs one extra scoped read per
     touched entity at commit time.

3. **Rev tokens from `nGraphElements`.**
   - Cons: rejected by ADR-0008; and pointless as enforcement — `updateTopology`
     ignores `_rev`, so the token would still only enable client-side detection
     (same guarantee as option 2, plus a legacy-surface dependency).

4. **Strict `PATCH nGraphElements` for writes.**
   - Cons: rejected by ADR-0008; bypasses `updateTopology`'s booking/service
     validation — trades one integrity mechanism for another.

## Decision

**Option 2: compare-and-commit, built into the change-set lifecycle
(ADR-0006's transaction / direct-write paths both get it).**

1. **Baseline at staging time.** When an entity is first staged (replace or
   remove), the change set fetches and stores its current form via
   Inspect-surface lookups (all verified 2025.4.9, payloads in
   [endpoints.md](../endpoints.md#post-restv2actionsstatuscollectorlookupinspectedgesbyids);
   none of them exposes a `_rev`):
   - edges: `lookupInspectEdgesByIds` — the **full persisted edge form**
     (every `replaceEdges` field), batched; the UI's own edit flow calls it
     with both directions of a connection.
   - vertices: `lookupInspectVertexByIds` (batched) — editable vertex form
     (`fields` incl. label, tags, `typeFields` capability flags,
     `useAsEndpoint`). Vertex tag bindings come from this lookup (and hydrated
     port `tagsInfo`), **not** from `nGraphElements` — they are stored in
     `videoipath_docs.device_tags` server-side
     ([concepts.md §3.4](../concepts.md#34-tagging--device-vs-vertex-inspect-vs-topology)).
   - devices: `lookupInspectDevice` — editable device form (coordinates,
     descriptor, iconType, sdpStrategy, tags).

   The lookup forms **are** the write shapes — no client-side mapping
   (all three verified 2025.4.9 by live commit + byte-identical revert):
   `replaceEdges` takes the persisted edge form exactly as
   `lookupInspectEdgesByIds` returns it; `replaceDevices` takes exactly
   `lookupInspectDevice`'s `fields` object (`coordinates`/`localAssignedTags`
   mandatory; the raw persisted `baseDevice` element is rejected with HTTP
   400 — the server maps `coordinates` → `maps[]` itself); `replaceVertices`
   takes exactly `lookupInspectVertexById`'s `fields` object. Note
   `replaceVertices` is **update-only**: an unknown vertex id fails
   validation (*"Vertex … was not found in graph"*) — vertices originate from
   device sync, not from commits. The baseline serves double duty: it is the
   basis for building the full `replace*` payload (caller mutations applied
   on top) *and* the reference for conflict detection, compared on the
   editable fields. For `remove` entries the baseline is the element's
   existence + form.

2. **Pre-commit conflict check.** `commit()` re-fetches the same entities and
   deep-compares against the baselines over the fields the package models
   (volatile status fields excluded). Any mismatch aborts the whole commit —
   consistent with the server's all-or-nothing apply — and raises a typed
   conflict error carrying the entity ids and per-field diffs. The caller
   decides: re-stage on top of fresh state, or override.

3. **Override is explicit.** A caller can skip the check
   (`commit(check_conflicts=False)` or equivalent) — that is deliberate
   last-writer-wins, stated in the call. The server's `force` flag is
   unrelated (it does not bypass apply-gate errors; verified) and stays an
   independent, documented option.

4. **Commit result still rules.** Compare-and-commit runs *before* the POST;
   `data.res.ok` / `data.validation.result.ok` evaluation after the POST is
   unchanged (ADR-0006).

## Consequences

- **Honest guarantee: detection, not enforcement.** The re-read→POST window
  cannot be closed with the current server. This is the strongest guarantee
  available on the Inspect surface; state it plainly in user docs. Re-check
  per server version whether `updateTopology` gains rev enforcement
  (**[VERIFY]** on upgrades; concepts.md §5.1).
- One extra lookup round per stage and per commit — bounded by change-set
  size, not network size, and batchable: `lookupInspectEdgesByIds` and
  `lookupInspectVertexByIds` take id lists natively (verified).
- The conflict check needs a stable field-level equality over the persisted
  form — DTO comparison must exclude server-managed/volatile fields; document
  the excluded set alongside the DTOs.
- Snapshot data (rev-less, possibly stale) is explicitly **not** used as the
  baseline; baselines always come from fresh lookups at stage time. The
  snapshot is a read surface, not a write token
  ([ADR-0007](./0007-lazy-snapshot-loading.md),
  ADR-0010 for post-commit refresh).
- The lookup→write round-trip is exact for devices **and vertices** (both
  verified: commit + revert left the persisted element byte-identical except
  `_rev`) and trivial for edges. One caveat, applying to devices and vertices
  alike: the lookups (and the collector) return the **effective** label — the
  persisted `descriptor` merged with the `fDescriptor` fallback.
  `descriptor` is stored verbatim on commit, so a client that round-trips the
  lookup unchanged pins the fallback label into `descriptor` (the label stops
  tracking device-reported names). The persisted-vs-fallback distinction is
  not observable on the Inspect surface; the UI has the same property.
  Document it; don't touch `descriptor`/label fields unless the caller set
  them.
