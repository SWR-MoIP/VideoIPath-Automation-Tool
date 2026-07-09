# Inspect App — Implementation Plan

> Status: **Implemented** · Last updated: 2026-07-09
>
> Turns the concept phase ([concepts.md](./concepts.md), [endpoints.md](./endpoints.md),
> [ADRs 0001–0010](./decisions/README.md)) into the shipped `app.inspect` surface.
> All wire facts referenced below are live-verified against VideoIPath 2025.4.9.
>
> **Shipped:** code under `src/videoipath_automation_tool/apps/inspect/`; offline tests under
> `tests/inspect/`; developer-run live E2E suite (`-m e2e`) under `tests/e2e/inspect/`; user guide
> at [getting-started 05_Inspect](../getting-started-guide/05_Inspect.md). Milestones M1–M5 below
> are complete.

## 1. Context

The inspect-app concept phase is complete: all wire formats are captured and live-verified against VideoIPath 2025.4.9 ([endpoints.md](./endpoints.md)), and ten ADRs pin the architecture. This plan turns the concepts into the shipped `app.inspect` package surface. The existing code under `src/videoipath_automation_tool/apps/inspect/` (snapshot.py, domain/, model/) is a **draft** — it predates ADR-0007/0009/0010 (it parses one full collector response, no lazy hydration, no writes) and will be reworked in place.

Governing decisions (all Accepted):

| ADR | Decision (implementation-relevant core) |
| --- | --- |
| [0001](./decisions/0001-api-paradigm.md)/[0003](./decisions/0003-websocket-subscriptions.md) | Request/response only; no WebSocket API |
| [0004](./decisions/0004-async-strategy.md) | Sync public API; internal thread-pool parallelism for multi-request operations |
| [0005](./decisions/0005-e2e-testing.md) | E2E = developer-run live-server tests via `tests/.env.test`; offline fixture tests feed from `tests/fixtures/inspect/<version>/` |
| [0006](./decisions/0006-commit-write-model.md) | Commit-style writes: hybrid — direct auto-commit methods + explicit transaction context manager; success = `header.ok ∧ data.res.ok ∧ data.validation.result.ok` |
| [0007](./decisions/0007-lazy-snapshot-loading.md) | Skeleton-first snapshot (devices + edges scoped queries), transparent per-entity lazy hydration, section-level lazy loads, accreting state, `load="full"` eager mode |
| [0008](./decisions/0008-collector-only-endpoints.md) | Collector-only endpoints: never call `nGraphElements` / `edgesByDevice` at runtime |
| [0009](./decisions/0009-write-consistency.md) | Client-side compare-and-commit; baselines from `lookupInspectDevice` / `lookupInspectVertexByIds` / `lookupInspectEdgesByIds` (lookup forms **are** the write shapes); typed conflict error; explicit override |
| [0010](./decisions/0010-post-commit-snapshot-refresh.md) | Post-commit targeted refresh: local removes, per-device/per-pair scoped re-reads (~25 ms propagation, no retry loop), sections marked stale |

Verified server facts the code must encode: `replaceDevices`/`replaceVertices` take **edit forms** (`coordinates`+`localAssignedTags` mandatory for devices), `replaceVertices` is **update-only**, `replaceEdges` takes the raw persisted edge form, last-writer-wins (no `_rev` anywhere on the Inspect surface), reject-before-apply atomicity, HTTP 414 for over-long projections, `"_noId"` suppresses expansion, effective-label merging in lookups/collector.

## 2. Public API (the user-facing contract — design this first, code to it)

### 2.1 Entry point

```python
app = VideoIPathApp(...)
snapshot = app.inspect.get_snapshot()            # skeleton: all devices + edges, 2 parallel GETs
snapshot = app.inspect.get_snapshot(load="full") # eager /** fallback (point-in-time)
```

### 2.2 Reads (snapshot + domain objects, ADR-0007)

```python
dev = snapshot.get_device("device12")            # skeleton-backed, no I/O
dev = snapshot.find_device_by_label("BU-LEAF-A") # exact; find_devices_by_label for lists
devs = snapshot.devices                          # list[InspectDevice]
edges = snapshot.edges                           # list[InspectEdge] (pair-level)
svcs = snapshot.services                         # lazy: loads inspect/paths section on first touch

dev.label, dev.id, dev.coordinates, dev.status, dev.sync_severity, dev.tags   # skeleton fields
dev.ports          # first access → one GET nodeStatus/<id>/<detail projection>, then local
dev.edges          # local (edge skeleton)
dev.services       # triggers paths section load once
dev.linked_devices # local graph walk
port.vertex_id, port.status, port.edge, port.device
edge.from_device, edge.to_port, edge.status, edge.pair_id

snapshot.preload(devices=[...])                  # batch hydration, thread pool (ADR-0004)
snapshot.refresh()                               # returns a NEW snapshot (never mutates)
snapshot.fetched_at(entity_or_section)           # freshness introspection
```

Contract (already documented in models.md): at most one hydration fetch per entity/section; getters can raise connector errors; snapshot is not a single point in time.

### 2.3 Writes (change set, ADR-0006/0009/0010)

```python
# Convenience direct writes (auto-commit, one updateTopology each):
app.inspect.place_device("device12", x=1600, y=9050)
app.inspect.update_device("device12", label="BU-LEAF-A", icon_type="switch")
app.inspect.update_vertex("device12.1.Ethernet1.out", use_as_endpoint=True)
app.inspect.update_edge(edge_id, weight=10)
app.inspect.connect("device12.1.Ethernet1.out", "device7.0.swp1.in",
                    bidirectional=True, capacity=65535)   # paired edges
app.inspect.disconnect(edge_or_pair_id)
app.inspect.remove_device_from_topology("device12")       # remove baseDevice element

# Batched, atomic (primary path for pipelines):
with app.inspect.transaction() as tx:
    tx.place_device("device12", x=100, y=200)
    tx.connect(a_out, b_in, bidirectional=True)
    tx.remove(edge_id)
    result = tx.commit()          # conflict check → POST → targeted snapshot refresh
# exit without commit → discard + warning log; exception → discard

result.ok, result.applied_ids, result.validation  # typed CommitResult

# Conflict handling (ADR-0009):
try:
    tx.commit()
except InspectCommitConflictError as e:
    e.conflicts   # [{entity_id, kind, field_diffs}]
    tx.rebase()   # re-fetch baselines, re-apply staged intents; then commit again
tx.commit(check_conflicts=False)   # explicit last-writer-wins
```

Semantics: staging an entity fetches its baseline via the lookups (batched); caller mutations are field-level *intents* applied onto the baseline at commit-build time; `remove` baselines assert existence. Direct writes are sugar: open implicit tx → stage → commit.

### 2.4 Topology device/sync actions (network actions)

```python
app.inspect.add_devices_to_topology([("device12", 100, 200), ...])  # addDevices action
app.inspect.sync_devices(["device12"], add_only=True, conflict_strategy=ConflictStrategy.STRICT)
info = app.inspect.get_sync_info(["device12"])                      # lookupSyncInfo
```

### 2.5 Errors (new `apps/inspect/errors.py`)

`InspectError` (base) → `InspectCommitError` (carries `CommitResult` with `res.msg` + `validation` details), `InspectCommitConflictError`, `InspectEntityNotFoundError`, `InspectQueryTooLongError` (HTTP 414 → message points at `load="full"`). Connector-level errors pass through unchanged.

## 3. Module layout (target)

```
apps/inspect/
├── __init__.py                  # public re-exports
├── inspect_app.py               # InspectApp: composes read + write + actions mixins
├── inspect_api.py               # raw API layer: all HTTP calls, typed responses
├── queries.py                   # scoped-query/projection builder + frozen projection constants
├── errors.py
├── app/                         # user-facing method mixins (inventory-app pattern)
│   ├── read.py                  # get_snapshot, find_* helpers
│   ├── write.py                 # direct writes + transaction()
│   └── actions.py               # add/sync devices, sync info
├── snapshot.py                  # InspectSnapshot: state, indexes, hydration, refresh hooks
├── changeset.py                 # InspectTransaction, staging entries, baselines, commit
├── domain/                      # InspectDevice/Port/Edge/Service (extend existing)
└── model/                       # InspectApi* DTOs (extend existing: collector.py, actions.py,
                                 #   update_topology.py, ngraph.py, common.py)
```

Follows the established package idioms: `*App` composed from mixins (like `InventoryApp`), `*API` raw layer, Pydantic DTOs under `model/`, snake_case fields with wire aliases.

## 4. Implementation detail per component

### 4.1 Connector changes (small, prerequisite)

`connector/vip_rest_connector.py`:
- **POST allow-list**: add prefix `/rest/v2/actions/status/network/` (for `addDevices`/`syncDevices`). GET already covers `/rest/v2/data/status/`; POST already covers `…/actions/status/collector/`.
- **`/...` wildcard block**: GET currently raises on any `"/..."` in the path — scoped projections *require* `/.../` segments. Move this check behind the existing `node_check`/`url_validation` flags or add `allow_projection: bool = False` param that InspectAPI sets. Do not weaken behavior for existing callers.
- **`node_check=False`** for scoped reads (partial trees don't contain all envelope nodes).
- URL-encode query paths (space `%20`, `"` `%22`, parens, `=`) in `queries.py`, not in the connector.

### 4.2 `queries.py` — the projection catalogue

Single home for every verified query string (they are contract, not ad-hoc):
- `DEVICE_SKELETON` — trimmed msg-13 projection with `modules/"_noId"` (the full UI projection 414s; the trimmed variant is verified at ~8.6 KB/27 devices).
- `DEVICE_DETAIL(device_id)` — direct-id form `nodeStatus/<id>/…` with `modules/*` detail projection.
- `EDGE_SKELETON` — msg-14 lean projection; `EDGE_PAIR(pair_id)` — direct pair-key form.
- `PATHS_SECTION` — msg-12 serviceFields+path projection.
- Encoding helper `encode_query(path) -> str` + length guard raising `InspectQueryTooLongError` before sending (proxy limit).
Unit-test each constant against the fixtures (round-trip: query → fixture response parses into DTOs).

### 4.3 `inspect_api.py` — raw layer (one method per endpoint)

| Method | Endpoint |
| ------ | -------- |
| `get_collector_full()` | `GET …/status/collector/**` |
| `get_device_skeleton()` / `get_device_detail(id)` | scoped nodeStatus queries |
| `get_edge_skeleton()` / `get_edge_pair(pair_id)` | scoped externalEdgesByDeviceKey |
| `get_paths_section()` | scoped inspect/paths |
| `lookup_inspect_device(id)` | POST lookupInspectDevice |
| `lookup_vertices(ids)` | POST lookupInspectVertexByIds |
| `lookup_edges(ids)` | POST lookupInspectEdgesByIds |
| `lookup_sync_info(ids)` | POST lookupSyncInfo |
| `update_topology(delta)` | POST updateTopology |
| `add_devices(items)` / `sync_devices(req)` | POST network actions |
| `get_registered_actions()` | GET actions schema (version gating) |

Each returns typed DTOs; each logs at DEBUG. No business logic here.

### 4.4 DTO additions (`model/`)

- `collector.py`: already covers nodeStatus/paths/edges — verify field coverage against the skeleton/detail fixtures; add missing fields (`relatedNodeTags`, `ptpDeviceStatus`, `tagsInfo`, `meta` extras) as **optional** so skeleton and full payloads parse with one model set (skeleton items simply have `modules={}` / fields absent).
- `actions.py`: add `InspectApiLookupEdgesByIdsRequest/Response(+Item)`, `InspectApiLookupVertexByIdRequest/Response`, `InspectApiVertexEditForm` (the `fields` object incl. `typeFields`), reuse existing lookup DTOs.
- `update_topology.py`: encode the **verified per-kind shapes** — `InspectApiDeviceEditForm` (== lookupInspectDevice.fields; used in `replaceDevices`), `InspectApiVertexEditForm` (`replaceVertices`), persisted edge model (`replaceEdges`, reuse/align with `ngraph.py` edge). `CommitResponse` with `items[]`, `res`, `validation{createIds, details, result}`.
- All DTOs: `model_config = ConfigDict(extra="allow")` on read models (unknown-field tolerance across server versions), strict on write payload models.

### 4.5 `snapshot.py` rework (keep public getters, change internals)

State per ADR-0007/0010:
- `_records`: skeleton-indexed devices/edges as today, plus `_hydration: dict[str, _EntityState]` where `_EntityState = (level: SKELETON|FULL, fetched_at: datetime)`; `_sections: dict[str, _SectionState]` (paths, maintenanceBookings…).
- Constructor takes `fetcher: InspectAPI | None` + parsed skeleton payloads. `from_full_response(response)` classmethod → everything marked FULL, fetcher optional (fixtures/offline: lazy loading inert; raise a clear error if an unloaded section is touched with no fetcher).
- `_ensure_device_detail(device_id)`: no-op if FULL; else `get_device_detail`, re-parse item, replace record, rebuild that device's port index entries, drop that device's cached domain wrappers, stamp `fetched_at`. Same pattern `_ensure_section("paths")`.
- **Concurrency**: a `threading.Lock` around merge operations (preload uses a pool); document snapshot as not-thread-safe for general use, but hydration merges are internally consistent.
- `preload(devices=None)`: ThreadPoolExecutor (bounded, e.g. 8) over `_ensure_device_detail` (ADR-0004).
- **Post-commit hooks** (called by changeset, ADR-0010): `_apply_removals(ids)`, `_refresh_devices(ids)`, `_refresh_edge_pairs(pair_ids)`, `_mark_section_stale("paths")`.
- Keep `raw_response` only for `load="full"` snapshots; skeleton snapshots expose `raw_skeleton` parts instead.

### 4.6 Domain objects (`domain/`)

Property → data-source mapping (drives which getter triggers hydration):

| Property | Source | Hydrates? |
| -------- | ------ | --------- |
| `InspectDevice.id/label/pid/coordinates/status/sync_severity/tags/icon` | skeleton | no |
| `InspectDevice.ports`, `InspectPort.*` | device detail | yes (device) |
| `InspectDevice.edges`, `InspectEdge.*` | edge skeleton | no |
| `InspectDevice.services`, `InspectService.*`, `InspectEdge.services` | paths section | yes (section) |
| `InspectPort.edge` | edge skeleton index | no |

Add `InspectDevice.is_hydrated` / `snapshot.fetched_at(...)` for introspection. Keep frozen-dataclass wrappers + snapshot back-reference pattern from the draft.

### 4.7 `changeset.py` — transaction, baselines, commit

- `_StagedEntry(kind: DEVICE|VERTEX|EDGE, id, baseline: DTO, intents: dict[field, value] | REMOVE)`.
- **Staging**: first touch of an entity fetches baselines via *batched* lookups (`lookup_edges`, `lookup_vertices` accept lists; device lookup is per-id). Staging validates the entity exists (translate lookup miss → `InspectEntityNotFoundError`); vertices/devices cannot be *created* (update-only — enforced client-side with a clear message).
- `connect(a_vertex, b_vertex, bidirectional=True, **edge_fields)`: builds one/two `replaceEdges` entries keyed `a::b` (and `b::a`) from a default edge template (capacity 65535, redundancyMode "Any", weightFactors default — the verified persisted-edge defaults); no baseline needed for *new* edge keys, but stage a lookup to detect "already exists" and require explicit `overwrite=True`.
- **Payload build**: intents applied onto baselines → per-kind write DTOs (devices/vertices: edit forms verbatim — **no** field mapping; edges: persisted form). Label/desc caveat: `descriptor` fields are only included in the diff-intents if the caller set them (never round-trip the effective label silently).
- **Commit sequence** (one method, well-logged):
  1. re-fetch baselines (batched), deep-compare vs staged baselines over editable fields (exclude volatile: statuses, `assignedTags.inherited`); mismatch → `InspectCommitConflictError` (all conflicts collected, nothing sent);
  2. POST `update_topology`;
  3. evaluate three-flag success; failure → `InspectCommitError` with typed validation details;
  4. targeted snapshot refresh (if the tx was created from a snapshot): removes applied locally, affected devices/pairs re-fetched, paths section marked stale. Affected-set derivation from staged keys + `items[]` using the id conventions (vertex id → owning device; edge key → pair id).
- `rebase()`: refresh baselines, keep intents, drop conflicts resolution to caller when intent-field itself conflicts.
- Transaction is single-use; `discard()` clears; context-manager exit without commit logs a warning (explicitly decided: **no auto-commit on exit** — commit must be visible in user code).

### 4.8 `InspectApp` + package integration

- `inspect_app.py`: composes mixins; ctor `(vip_connector, logger)` like the other apps.
- `videoipath_app.py`: add lazy `inspect` property + `self._inspect_api = self.inspect._inspect_api` in the DEV block; placeholder `self._inspect = None`.
- **Version gating**: on `InspectApp` init, check `get_server_version()` ≥ 2025.4 (first verified: 2025.4.9); below → log warning "Inspect API surface unverified for this server version". Optionally probe `get_registered_actions()` at DEBUG.
- `apps/inspect/__init__.py`: export `InspectApp`, domain classes, `InspectSnapshot`, errors, `ConflictStrategy`.

## 5. Milestones (PR-sized, each independently shippable)

1. **M1 – Connector + queries + API layer (read)**: connector changes, `queries.py`, `inspect_api.py` read methods, DTO gap-fill; offline fixture tests green.
2. **M2 – Snapshot rework + domain (read path complete)**: hydration states, sections, preload, `from_full_response`; `app.inspect.get_snapshot()`; VideoIPathApp property; unit tests with fake fetcher (hydration counts, merge idempotency).
3. **M3 – Lookups + actions**: lookup API methods + DTOs, `get_sync_info`, `add_devices_to_topology`, `sync_devices`.
4. **M4 – Change set + writes**: `changeset.py`, direct write sugar, commit lifecycle incl. conflict check + targeted refresh; unit tests with mocked API (payload-shape assertions against the four updateTopology fixtures; conflict scenarios; refresh-hook calls).
5. **M5 – E2E suite** (below) + getting-started doc page (`docs/getting-started-guide/0X_Inspect.md`) + [models.md](./models.md)/README sync.

## 6. Testing

### 6.1 Offline (runs in CI, every push)

- **Fixture contract tests** (`tests/inspect/test_models.py`): every fixture in `tests/fixtures/inspect/2025.4.9/` parses into its DTO; write-payload builders reproduce the fixture requests byte-for-byte (devices/vertices edit forms, edge form, no-op).
- **Snapshot unit tests** (`tests/inspect/test_snapshot.py`): fake fetcher returning fixture payloads — skeleton indexes, exactly-one hydration fetch per device, section laziness, preload fan-out, post-commit hooks (removal drops indexes; refresh replaces records; stale section reloads).
- **Changeset unit tests** (`tests/inspect/test_changeset.py`): staging→baseline capture, intent application, conflict detection (mutated baseline → error with field diffs), `check_conflicts=False` bypass, three-flag result evaluation incl. the captured failure fixtures, affected-set derivation.
- **Query tests**: encoding, 414 length guard, projection constants stability.

### 6.2 E2E — live instance, topology replica (ADR-0005)

Location `tests/e2e/inspect/`, pytest marker `e2e` (excluded by default via `addopts = -m "not e2e"`), gated on `VIPAT_E2E_ENABLED=1` in `tests/.env.test` **plus** a server-version allowlist check. Every created element uses label prefix `E2E-` (in both inventory and inspect) and the `vipat-e2e` tag.

**Namespace & lifecycle:** cleanup runs **at startup** (`scenario.cleanup(app)`), not on teardown — so after a run the built topology **persists** in VideoIPath for manual inspection, and the next run starts from a clean namespace. Mutating tests revert their own changes, so the persisted end state is the complete topology.

**Scenario: `LeafSpineScenario` (module `tests/e2e/inspect/scenario.py`)** — an anonymized replica of the local instance's topology, captured to `leaf_spine_topology.json` (indices/coordinates/link-pairs only; no real names/ids). Built with **virtual (mock-driver) devices only** via the real user flow:

1. **Inventory** — `app.inventory.create_device(driver="com.nevion.mock-0.1.0")` with a router module sized to the device's degree (`num_router_ports`), then `add_device`. No hardware; the topology app is never used.
2. **Inspect** — `add_devices_to_topology` (placement at the captured coordinates), `update_device(label=…, tags=[…])` to set the E2E display label + tag, then `connect` each link (ports discovered from `device.ports`).

`cleanup` removes edges, then the topology node (`remove_device_from_topology`), then the inventory entry — discovering E2E devices by label in **both** inventory and inspect (catches orphans from an aborted run).

**Test list** (`test_e2e_leaf_spine.py`, session-scoped scenario fixture; all reads/writes via `app.inspect`):
1. `test_all_devices_present` — every scenario device appears with its `E2E-` label.
2. `test_skeleton_read_no_hydration` — scenario edge count == `expected_edge_count()`; **no** hydration fetches during the skeleton read (spy counter).
3. `test_lazy_hydration` — `get_device(id).ports` → exactly one detail fetch, cached thereafter; hydration state flips; mock devices expose router ports.
4. `test_connectivity_graph` — `linked_devices` of the busiest device == its fixture adjacency.
5. `test_edge_pair_refresh` — `update_edge(weight=…)`; edge survives targeted refresh without a full reload; revert.
6. `test_transaction_atomicity` — tx with a valid edge edit + a `remove` of a non-existent id → `InspectCommitError`, nothing applied.
7. `test_conflict_detection` — edit an edge; mutate it out-of-band (second `VideoIPathApp`); `commit()` → `InspectCommitConflictError`; `rebase()` + commit succeeds; revert.
8. `test_device_placement_roundtrip` — `place_device` new coordinates; verify; revert.
9. `test_disconnect_reconnect_cycle` — disconnect a link's directed edges, assert gone, reconnect, assert restored.
10. `test_full_vs_skeleton_equivalence` — `load="full"` and skeleton+preload resolve the same connectivity graph.
11. `test_state_persists` — after the suite the complete topology (all devices + edges) remains.

Never touched: non-`E2E-` devices, bookings/services (read-only asserts only), profiles/security sections.

## 7. Risks & mitigations

- **Connector `/...`-block relaxation** could affect existing callers → new opt-in parameter only; existing default behavior unchanged; unit test both.
- **Skeleton projection length vs. proxies** (414 verified for full UI projection) → pre-flight length guard + documented `load="full"` fallback.
- **Version drift** (all verification on 2025.4.9) → version gate + `get_registered_actions()` probe; concepts.md upgrade checklist already mandates re-verification; read DTOs `extra="allow"`.
- **Draft-code compatibility**: `InspectSnapshot.from_response()` exists in the draft — keep as alias of `from_full_response` (nothing published depends on it yet; package unreleased for inspect, so breaking the draft internals is acceptable).
- **Shared-instance E2E safety** → tag/prefix discipline, env gating, teardown-finalizer, no writes outside `E2E-` namespace (test 4/6 operate on scenario-owned edges only).

## 8. Verification of the implementation

- `poetry run pytest` (offline suite) green in CI.
- `poetry run pytest -m e2e tests/e2e/inspect` against the local 2025.4.9 instance (`tests/.env.test`) — full scenario build → tests → teardown leaves the instance in its pre-run state (asserted by test 10).
- `poetry run ruff check src/ tests/` clean.
- Manual smoke in DEV env: `app._inspect_api` exposure, DEBUG logs show skeleton (2 GETs) then exactly one hydration GET on first `ports` access.
