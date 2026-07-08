# ADR-0006: Commit-style write model (change sets)

> Status: **Accepted**
> Date: 2026-06-18 · Deciders: Paul Winterstein, Jonas Scholl
>
> Concurrency handling for this write model is decided in
> [ADR-0009](./0009-write-consistency.md) (compare-and-commit; the server is
> last-writer-wins). Post-commit snapshot refresh is decided in
> [ADR-0010](./0010-post-commit-snapshot-refresh.md).

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

**Data vs. operations:** Pydantic models / DTOs hold **data only** — fields,
nested structures, validation. They do not expose `add`, `update`, `delete`, or
`commit` methods. All mutations go through the **app instance** or an optional
**transaction** object that stages changes and commits them to the server.

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
topology + status + services tree ([concepts.md §3.1](../concepts.md#31-collector-aggregate--primary-read-surface)).
Edge keys (`fromId::toId`) and vertex ids are consistent between read and write.

#### Response shape — successful commit (verified 2026-07-08, VideoIPath 2025.4.9)

Edge `weight` change applied via `replaceEdges`:

```json
{
  "data": {
    "items": [
      {
        "external": null,
        "id": "device-a.dev.module-1.port-out-1.out::device-b.dev.module-1.port-in-1.in",
        "idx": 0,
        "res": { "msg": [""], "ok": true }
      }
    ],
    "res": { "msg": [], "ok": true },
    "validation": {
      "createIds": [],
      "details": {},
      "result": { "msg": [], "ok": true }
    }
  },
  "header": { "ok": true, "code": "OK" }
}
```

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
(e.g. `"booking-1001"`):

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
    "user": "api-user"
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
        "booking-1001": {
          "isCancel": false,
          "isProduct": false,
          "resolvable": false,
          "rev": "2-2026-06-15T13:03:50.000000000Z[UTC]",
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
like the existing `PATCH nGraphElements` path. On 2025.4.9, `updateTopology` is
**last-writer-wins** — a stale `_rev` in the payload is ignored
([endpoints.md](../endpoints.md#post-restv2actionsstatuscollectorupdatetopology)).

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
collector read aggregate keeps its own status-oriented shape. **Confirmed
last-writer-wins** on 2025.4.9 — `updateTopology` does not enforce `_rev`
checks; stale `_rev` in `replaceEdges` is ignored
([endpoints.md](../endpoints.md#post-restv2actionsstatuscollectorupdatetopology)).

What remains unverified:

- ~~Whether the server exposes a **separate staging / change-set id** API~~
  **Confirmed client-side only** on 2025.4.9.
- ~~**Successful** commit response shape~~ **Confirmed** (see above).
- ~~**Partial apply** after validation~~ **Confirmed reject-before-apply**.
- ~~Validation `status` codes and `resolvable`~~ **Confirmed** for booking-blocked
  delete (`status: -22`, `resolvable: false`). `resolvable: true` not observed.
- ~~`validateTopology` / `discardTopology` / `importTopology` / `exportTopology`~~
  **Confirmed unregistered** on 2025.4.9 via
  `GET /rest/v2/actions/status/collector/<name>` schema (empty `collector: {}`);
  27+ POST payload variants tried. See
  [endpoints.md — Action registration discovery](../endpoints.md#action-registration-discovery).
- ~~Import / Export (preview)~~ **Confirmed unregistered** — empty data
  namespaces and empty GET action schema.
- Other `…/actions/status/collector/*` lookup endpoints — captured in
  [endpoints.md](../endpoints.md).

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

**Option 3 (hybrid): explicit transaction via context manager, plus direct write
operations on the app.**

- **Data-only DTOs** — models represent server payloads; no behaviour methods.
- **App-level direct writes** — `add` / `update` / `delete` on the inspect app
  apply and commit immediately (one change set, one `updateTopology` call), for
  simple one-off scripts.
- **Optional transaction** — a context manager (e.g. `with app.inspect.transaction()`
  or similar) stages multiple actions and commits them atomically on exit; discard
  on error or explicit cancel.

Staging is **client-side** until the `POST …/updateTopology` commit; there is no
separate server-side change-set id (per verified wire format below).

## Consequences

- Two documented usage styles, but both map to the same underlying commit
  payload shape.
- Context manager must define exit behaviour: commit on success, discard/raise
  on failure; document what happens to an uncommitted transaction.
- DTOs stay portable and serializable; business logic lives in the app/transaction
  layer, consistent with existing topology/inventory patterns.
- Single-change scripts stay ergonomic via direct writes; pipeline edits that
  touch multiple elements use the transaction path for atomicity.
