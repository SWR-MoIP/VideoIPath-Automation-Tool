# ADR-0006: Commit-style write model (change sets)

> Status: **Proposed**
> Date: 2026-06-18 · Deciders: Paul Winterstein, Jonas Scholl

## Context

Inspect applies configuration changes with a **commit-style** model: when the
operator creates, edits, or deletes topology elements / connections, the actions
are first **gathered into a change set** and then **committed together**, rather
than each change hitting the server immediately.

This differs from the existing apps. Today the write path is **immediate and
per-call**:

- Topology: `get_device` → mutate locally → `update_device` diffs against the
  server and applies the changes with a revisioned
  `PATCH /rest/v2/data/config/network/nGraphElements` (mode `strict`, `_rev`
  checked).
- Inventory: `add_device` / `update_device` go through the RPC
  `/api/updateDevices` call.

There is **no commit, transaction, or staging concept** in the package today
(the topology "staged device" is only an in-memory diff input, not a server-side
batch). So Inspect's commit behaviour is a **net-new write path**, not a reuse of
the existing one.

### Verified wire format (browser capture, 2026-06-18)

Inspect applies topology edits with a **single bulk action** — not the existing
revisioned `PATCH …/data/config/network/nGraphElements` path:

| Item | Value |
| ---- | ----- |
| Method / path | `POST /rest/v2/actions/status/collector/updateTopology` |
| Auth | Session cookies (`VipathSession`, …) + `XSRF-TOKEN` cookie and matching `x-xsrf-token` header |
| Envelope | Standard v2 `{ "header": { "id": 0 }, "data": { … } }` |

The `data` object carries the **entire delta** in one request. Empty maps /
arrays mean “no change” for that category:

| Field | Shape | Purpose |
| ----- | ----- | ------- |
| `replaceDevices` | `Record<id, device>` | Upsert devices |
| `replaceVertices` | `Record<id, vertex>` | Upsert vertices |
| `replaceEdges` | `Record<"fromId::toId", edge>` | Upsert edges (composite key) |
| `replaceResourceTransforms` | `Record<id, …>` | Upsert resource transforms |
| `addExternalEdges` | `edge[]` | Add external edges |
| `remove` | `string[]` | Remove entities by id |
| `force` | `boolean` | Force apply (example used `false`) |

**Edge key:** `"<fromId>::<toId>"` — e.g.
`device0.1.10.out::device1.1.11.in`.

**Minimal example** (set edge `weight` to `1`; other categories empty):

```json
{
  "header": { "id": 0 },
  "data": {
    "replaceDevices": {},
    "replaceVertices": {},
    "replaceEdges": {
      "device0.1.10.out::device1.1.11.in": {
        "fromId": "device0.1.10.out",
        "toId": "device1.1.11.in",
        "descriptor": { "label": "Eth 1.10 (out) -> Eth 1.11 (in)", "desc": "" },
        "fDescriptor": { "label": "", "desc": "" },
        "tags": [],
        "active": true,
        "weight": 1,
        "capacity": 65535,
        "bandwidth": -1,
        "weightFactors": {
          "bandwidth": { "weight": 0 },
          "service": { "weight": 0, "max": 100 }
        },
        "redundancyMode": "Any",
        "conflictPri": 0,
        "includeFormats": [],
        "excludeFormats": []
      }
    },
    "replaceResourceTransforms": {},
    "addExternalEdges": [],
    "remove": [],
    "force": false
  }
}
```

This confirms the **gather-then-commit** mental model at the API boundary: the
Inspect UI accumulates edits client-side, then sends one `updateTopology` payload
with populated `replace*` / `add*` / `remove` sections. Reads use the matching
**collector** namespace: `GET …/data/status/collector/**` returns the composed
topology + status + services tree ([concepts.md §3.1](../concepts.md#31-collector-aggregate--primary-inspect-read-surface)).
Edge keys (`fromId::toId`) and vertex ids are consistent between read and write.

#### Response shape — failed commit (browser capture, 2026-06-18)

**Important:** HTTP / envelope success is **not** commit success. On a failed
delete-device attempt the top-level `header` still reported success:

| Field | Failed-commit value | Meaning |
| ----- | ------------------- | ------- |
| `header.ok` | `true` | Transport / auth succeeded |
| `header.code` | `"OK"` | Envelope accepted |
| `data.res.ok` | `false` | Commit rejected |
| `data.res.msg` | `["Validation failed"]` | High-level failure reason |
| `data.validation.result.ok` | `false` | Validation gate failed |
| `data.validation.result.msg` | e.g. `["A required edge was not found. (main)"]` | Actionable validation message |
| `data.items` | `[]` | No applied changes returned |

Per-entity validation details live in `data.validation.details`, keyed by id
(e.g. `"100001"`):

| Field | Example | Notes |
| ----- | ------- | ----- |
| `status` | `-22` | Server-specific error code |
| `rev` | `"2-2026-06-15T13:03:50.631612311Z[UTC]"` | Entity revision at validation time |
| `resolvable` | `false` | Whether the client can fix/retry in-place |
| `type` | `"generic"` | Error category |
| `isCancel` / `isProduct` | `false` | Flags on the validation item |

```json
{
  "header": {
    "auth": true,
    "caption": "Operation Successful",
    "code": "OK",
    "ok": true,
    "user": "sysadmin"
  },
  "data": {
    "items": [],
    "res": {
      "msg": ["Validation failed"],
      "ok": false
    },
    "validation": {
      "createIds": [],
      "details": {
        "100001": {
          "isCancel": false,
          "isProduct": false,
          "resolvable": false,
          "rev": "2-2026-06-15T13:03:50.631612311Z[UTC]",
          "status": -22,
          "type": "generic"
        }
      },
      "result": {
        "msg": ["A required edge was not found. (main)"],
        "ok": false
      }
    }
  }
}
```

The package must treat a commit as failed when `data.res.ok` or
`data.validation.result.ok` is `false`, even if `header.ok` is `true`. Revisions
appear on validation detail entries (`rev`), not as a top-level `_rev` conflict
like the existing `PATCH nGraphElements` path — **[VERIFY]** whether revision
mismatch surfaces the same way on other failure modes.

### Write target — the `nGraphElements` config store (confirmed)

`updateTopology` is a status-namespace **action**, but it persists to the
existing **`config/network/nGraphElements`** store. Confirmed by capture: the
edge `device0.1.10.out::device1.1.11.in` set to `weight: 1` via this action
appears in `GET /rest/v2/data/config/network/nGraphElements/**` with `weight: 1`
and a bumped `_rev` (`3-…`). Elements are revisioned (`_rev` = `N-<timestamp>`)
and typed (`baseDevice`, `codecVertex`, `ipVertex`, `unidirectionalEdge`) — the
same model `app.topology` already uses. Inter-device links persist as **paired
unidirectional edges** (`a::b` and `b::a`, `capacity: 65535`); the failed-delete
error *"A required edge was not found. (main)"* refers to this edge model. See
[concepts.md §3.3](../concepts.md#33-config-store--ngraphelements-write-target).

This means the change-set write layer does **not** need new topology element
models — it can reuse the existing ones for the persisted form, while the
collector read aggregate keeps its own status-oriented shape. **[VERIFY]**
whether `updateTopology` enforces `_rev` optimistic concurrency or is
last-writer-wins.

What remains **[VERIFY]**:

- Whether the server exposes a **separate staging / change-set id** API, or
  staging is purely client-side until this POST.
- **Successful** commit response shape (`data.items` contents when `ok: true`).
- Whether multi-category edits that pass validation can still **partially apply**
  (the failed example returned empty `items`, suggesting reject-before-apply).
- Other `…/actions/status/collector/*` endpoints (discard, validate-only, …).
- Meaning of validation `status` codes (e.g. `-22`) and when `resolvable` is
  `true`.
- Cross-check against the
  [Public API 2025 LTS](https://documenter.getpostman.com/view/11222813/2sBXihpCS8#intro)
  (`Connections` / `Partial Connections` / `Import and Export`).

## Options

1. **Auto-commit per call (hide the change set).** Each `add/update/delete`
   transparently opens a change set, applies one action, and commits — mimicking
   the existing immediate-write UX.
   - Pros: familiar; matches the current topology/inventory mental model; simple
     for one-off scripts.
   - Cons: defeats the point of batching (atomic multi-element changes, fewer
     round-trips, single validation/commit); doesn't expose commit-time conflict
     handling; may not even match how the server expects connections to be built.

2. **Explicit change set only.** Force callers to open a change set, stage
   actions, then commit (or discard).
   - Pros: faithful to the server model; enables atomic multi-step edits and a
     single pre-commit validation; explicit conflict/rollback handling.
   - Cons: more ceremony for the trivial single-change case; easy to leak an
     un-committed change set.

3. **Hybrid: explicit change set with a convenience auto-commit default.**
   Provide a first-class change-set object (ideally a context manager) for
   batched, atomic edits, *and* a convenience path where a single
   `add/update/delete` auto-commits when no change set is open.
   - Pros: ergonomic for both one-off scripts and batched pipeline edits;
     exposes commit/validate/discard when needed; degrades to simple usage.
   - Cons: two usage styles to document; must define what happens to an open
     change set on error / context exit.

## Decision

_To be decided._
