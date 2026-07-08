# ADR-0008: Collector-only endpoint policy (no legacy topology API)

> Status: **Accepted**
> Date: 2026-07-08 · Deciders: Jonas Scholl

## Context

The Inspect package sits on top of two API generations that can both read and
write the same topology data:

- **Legacy topology surface** (used by `app.topology` today):
  `GET/PATCH /rest/v2/data/config/network/nGraphElements/**` — revisioned
  (`_rev`, `mode: strict`) — plus older status views such as
  `GET /rest/v2/data/status/network/edgesByDevice/**`.
- **Inspect surface**: collector data reads
  (`GET /rest/v2/data/status/collector/…`, scoped or `/**`), collector actions
  (`POST /rest/v2/actions/status/collector/*` — `updateTopology`,
  `lookupInspectDevice`, `lookupSyncInfo`, …), and the network actions used by
  Inspect workflows (`POST /rest/v2/actions/status/network/{addDevices,syncDevices}`).

In the product, Inspect **replaces** the Topology app; `nGraphElements` remains
the underlying store (`updateTopology` writes land there, ADR-0006), but it is
an implementation detail behind the Inspect facade. Mixing the two surfaces in
one package layer would mean two write models (revisioned strict PATCH vs.
commit-time-validated bulk action), two read shapes for the same entities, and
a version-gating story spanning both.

The Inspect UI's captured traffic (initial load) uses **only** the Inspect
surface, and the UI bundle (`/assets/index-*.js`, 2025.4.9) contains **zero
references to `nGraphElements`** — the edit and commit flows are built on the
collector lookups (`lookupInspectEdgesByIds`, `lookupInspectVertexByIds`, …)
and `updateTopology`
([endpoints.md](../endpoints.md#action-registration-discovery)). The vendor's
own client never touches the legacy surface.

## Options

1. **Collector-only (Inspect surface only).** The package never calls
   `nGraphElements` or other legacy topology endpoints at runtime.
   - Pros: one API generation; one write model; matches what the vendor UI
     does; simple version gating; no accidental coupling to the app Inspect
     replaces.
   - Cons: gives up the only **server-enforced** optimistic locking
     (`PATCH nGraphElements` strict mode) and the only revision-bearing read —
     consistency must be solved client-side (ADR-0009).

2. **Hybrid: Inspect surface + `nGraphElements` reads for `_rev`.**
   - Pros: real revision tokens for conflict detection.
   - Cons: reads and writes disagree (`_rev` from config plane is **ignored**
     by `updateTopology` — verified last-writer-wins on 2025.4.9, so the token
     buys detection only, not enforcement); couples the package to the legacy
     surface anyway.

3. **Hybrid: `updateTopology` for bulk, strict `PATCH nGraphElements` for
   single-entity writes needing hard concurrency guarantees.**
   - Pros: server-enforced locking where it matters.
   - Cons: two write paths with different validation semantics (`updateTopology`
     runs booking/service validation; a raw PATCH bypasses it) — dangerous, not
     just inconsistent.

## Decision

**Option 1: the Inspect package uses only the Inspect surface.** Allowed at
runtime:

| Kind | Endpoints |
| ---- | --------- |
| Data reads | `GET /rest/v2/data/status/collector/…` (scoped queries and `/**`) |
| Collector actions | `POST /rest/v2/actions/status/collector/*` (`updateTopology`, `lookupInspectDevice`, `lookupSyncInfo`, and further registered lookups) |
| Network actions | `POST /rest/v2/actions/status/network/addDevices`, `…/syncDevices` |
| System probes | `GET /rest/v2/data/status/system/about/…` (version gating) |

Explicitly **not called** by the package:

- `GET`/`PATCH /rest/v2/data/config/network/nGraphElements/**`
- `GET /rest/v2/data/status/network/edgesByDevice/**`
- RPC topology calls

These stay documented in [endpoints.md](../endpoints.md) as **store
documentation and discovery/cross-check references** only. `app.topology`
remains the public escape hatch for raw, revisioned `nGraphElements` access —
unchanged and out of scope here.

## Consequences

- **No `_rev` is available to the Inspect package** (collector items and all
  verified lookup responses carry none), and the write path enforces none
  (last-writer-wins, verified 2025.4.9). Write consistency is therefore
  solved client-side — [ADR-0009](./0009-write-consistency.md).
- The persisted form of an element (all config fields needed to build full
  `replace*` payloads) comes from collector-namespace lookups — verified on
  2025.4.9: `lookupInspectDevice` (devices), `lookupInspectVertexById`/`…ByIds`
  (vertices), `lookupInspectEdgesByIds` (edges, full persisted form, batched;
  see [endpoints.md](../endpoints.md#post-restv2actionsstatuscollectorlookupinspectedgesbyids))
  — not from `nGraphElements` reads. (`lookupGraphElement` does not exist.)
- The connector URL allow-list for Inspect gains only Inspect-surface prefixes;
  `config/network/nGraphElements` is not added for the Inspect app.
- If a future server version changes the Inspect surface (e.g. registers
  `validateTopology`, adds rev enforcement to `updateTopology`), the policy is
  re-evaluated per version — never by silently reaching for the legacy API.
