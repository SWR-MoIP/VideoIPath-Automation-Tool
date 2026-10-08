# Provisioning — Concepts

Design record for the provisioning package. Field-level usage is in
[reference.md](./reference.md) and [processors.md](./processors.md).

## 1. What the feature is

The SDK apps expose the operations needed to configure VideoIPath yourself.
Provisioning adds a declarative layer that combines reusable configuration,
device facts, naming, and processors into a reviewable plan, then applies it
through those apps.

Inventory onboards a device. Inspect places it in the topology and edits
vertices. A blueprint is the reusable configuration template within provisioning:
it describes how one *kind* of device should be configured in both places, so a
caller can apply that description to many real devices.

The caller supplies the instance facts (`ProvisioningDevice`): source-system id,
label, addresses, credentials, an optional Inventory id, and an optional
Inspect target, and concrete external connections. The blueprint supplies the type: driver settings, topology
appearance, vertex interpretation, port mapping, and naming. The engine does not know NetBox
or any other source system. Translation into `ProvisioningDevice` stays outside
the package.

`plan()` reads current server state and returns a reviewable `ProvisioningPlan`.
`plan.apply()` writes. The two calls share one executor. `engine.apply(...)`
is `plan` followed by `apply`.

## 2. Dependency direction

Document models, naming, and processors do not call VideoIPath. The only
modules that touch `app.inventory` and `app.inspect` are the two gateways
([ADR-005](./decisions/005-app-gateways.md)). `VideoIPathApp` does not depend
on this package at all.

```mermaid
flowchart LR
  caller[Caller]
  engine[engine.py]
  resolution[resolution.py]
  naming[naming.py]
  processors[processors/]
  inventory[inventory.py]
  inspectgw[inspect.py]
  apps[InventoryApp and InspectApp]

  caller --> engine
  engine --> resolution
  engine --> naming
  engine --> processors
  engine --> inventory
  engine --> inspectgw
  resolution --> processors
  inventory --> apps
  inspectgw --> apps
```

`ProvisioningEngine` is constructed with a `ProvisioningApp` protocol (`inventory`
and `inspect` properties). `VideoIPathApp` satisfies that protocol without
being imported here. Construction does not touch the app or the network.

PyYAML is a normal package dependency. The parser lives in `loader.py`.
`models.py` imports it for `Blueprint.load` / `from_yaml`, so importing
`Blueprint` imports PyYAML. The parser is a dedicated `SafeLoader` subclass:
one UTF-8 document, mapping root, no duplicate keys, aliases, anchors, merge
keys, or custom tags. Limits are 1 MiB, 32 levels, and 100,000 nodes.

## 3. Module map

| Module | Responsibility |
| ------ | -------------- |
| `models.py` | Strict document, device facts, patches, plan and result records. |
| `loader.py` | YAML parsing and source locations for errors. |
| `resolution.py` | Variant merge, driver and parameter validation, JSON Schema. |
| `naming.py` | `Text` / `Field` / `Join` expressions and layering. |
| `processors/` | `VertexProcessor`, detached records, per-engine `ProcessorRegistry`, Matrox built-in. |
| `inventory.py` | `InventoryGateway`: one Inventory record, managed-field diff, create/update. |
| `connections.py` | Pure generic port resolution, directional edge selection and managed-field diffs. |
| `inspect.py` | `InspectGateway`: fresh scoped read, processor run, topology commit, module tags. |
| `engine.py` | Configuration, `plan()`, captured inputs, phased `apply()`. |
| `errors.py` | `ProvisioningError` hierarchy. Validation issues carry a path, not raw values. |
| `schemas/blueprint-v1.schema.json` | Generated document schema. `tests/provisioning/test_resolution.py` fails when the file is stale. |

Public types are re-exported from `provisioning/__init__.py`. Engine internals
(`_Planner`, `_Executor`, `_Captured`, the gateways' work models) are not.

## 4. From document to writes

```mermaid
flowchart TD
  yaml[Blueprint YAML or dict]
  device[ProvisioningDevice]
  resolved[ResolvedBlueprint]
  plan[ProvisioningPlan]
  apply[apply]
  inv[Inventory create or update]
  disc[Discovery wait]
  sync[Add or synchronize]
  topo[Inspect transaction]
  tags[Module tag actions]
  verify[Read back]

  yaml --> resolved
  device --> resolved
  resolved --> plan
  device --> plan
  plan --> apply
  apply --> inv --> disc --> sync --> topo --> tags --> verify
```

Resolution ([ADR-007](./decisions/007-typed-inputs.md)) copies `defaults`, applies
caller-selected variant overlays in order, binds declared inputs in the effective
scope, then applies per-instance `inventory_overrides`. Variants may span both
Inventory and Topology. Unknown or repeated names fail. Input references retain
their types, replace whole nodes during merging, and are never evaluated a second
time. Inputs without defaults are needed only when the selected scope uses them.

Driver `custom_settings` are checked against the model for
`SELECTED_SCHEMA_VERSION`; processor `params` against the registered `params_model`.
Every merged leaf retains provenance (`defaults`, `variant:<name>`, `instance`,
with `|input:<name>` for input values). The source document is never mutated.

Naming is layered after that, entry by entry, later sources winning:
library default, engine `naming`, resolved blueprint naming (a topology entry
replaces the same inventory entry), then the `naming` argument on the call. An explicit
`None` turns that entry off. Names are rendered from facts on `ProvisioningDevice`,
`module_position`, `EndpointIdentity`, scalar `attributes`, and bound `inputs`. They are not
read off the current server label, so a second apply cannot grow a second suffix.

## 5. Planning

`plan()` deep-copies the device, the blueprint, and the processor registry, and
stores them on the plan together with copied inputs, ordered variants, the resolved document, the layered naming
scheme, and the effective `ApplyOptions`. Later `engine.configure(...)` or
`register_processor(...)` does not change a plan that already exists.

Planning reads. It does not write, synchronize, stage snapshot edits, or create
catalog tag entries.

Inventory planning compares managed fields with the current record
([ADR-003](./decisions/003-managed-fields.md)) and records a create, an update,
or no change. A supplied `inventory_id` that does not exist fails. The engine
does not create a replacement record.

Topology planning needs a target. That is `ProvisioningDevice.topology`, or a
`DeviceTarget` built from `inventory_id` when topology was omitted. When the
exact edits cannot be known yet, the topology phases are marked `deferred` and
`fully_resolved` is `False`. That happens when:

- this plan creates the Inventory record the topology device id will come from
- an Inventory update may alter discovery (address, alternate addresses,
  credentials, generic settings, custom settings, or `active`). Apply stops
  after Inventory, sets `replan_required`, and returns `status="partial"`.
  Plan again once the driver has rediscovered the device
- the device is not in the topology yet and `sync` allows adding it
- synchronization is pending and this target is allowed to perform it

A module target does not add or synchronize its parent device. If the parent is
absent, planning fails. If a sync is pending, the plan warns and continues
against the current topology.

When nothing is deferred, planning reads a detached scope
([ADR-005](./decisions/005-app-gateways.md)), runs the processor
([ADR-004](./decisions/004-processors-propose.md)), and stores the exact edits
plus a fingerprint of the scope.

The public plan fields (phases, bindings, diagnostics, digest, ids) are the
review surface. `summary()` redacts secrets. `apply()` also uses private
captured work, including unredacted Inventory values, so a plan is an in-memory
object bound to the app it was built with. It is not a document you save and
replay in another process.

## 6. Applying

[ADR-002](./decisions/002-plan-then-apply.md) defines phased execution;
[ADR-008](./decisions/008-staged-readiness.md) refines readiness into two budgets:

1. `inventory` — create or update the one record. A new id is stored on the result immediately.
2. `inventory_readiness` — poll fresh Inventory status for `reachable=True`, bounded by `inventory_ready_timeout` (10 seconds). Missing status and unreachable devices remain pending.
3. `topology_sync` — add the device, confirm visibility, and synchronize it according to `ApplyOptions.sync`.
4. `discovery` — wait for required local topology data (`TopologyNotReadyError`). It shares a separate `topology_ready_timeout` (60 seconds) with topology sync; other errors fail at once.
5. `topology` — device, vertex and resolved edge edits in one `InspectTransaction`, then commit.
6. `module_tags` — `assignTag` / `unassignTag` actions, one tag at a time. These are not part of the topology commit.
7. `verification` — read back what this apply wrote.

Both budgets use the injected monotonic clock and `poll_interval` (1 second).
Inventory-only applies, resolved topology, virtual targets, and module-only edits
without their own Inventory binding skip reachability. Mock/static devices can
opt out with `require_reachable=False`. Plans and dry runs never poll. Incomplete
local topology produces deferred plan phases, enabling a retry after partial
rollout. Peer discovery retains its existing explicit-replan behavior.

An Inventory update that may alter discovery does not continue into discovery
or topology in the same apply. Those phases stay `deferred`, the result status
is `partial`, and `replan_required` is true. The call does not raise. Inventory
verification still runs. After the driver has rediscovered the device, build a
new plan. Creating a record still polls for discovery: a new device has no
previous topology.

`sync` defaults to `add_only`. `none` requires the device to already be in the
topology. `add_only` adds the device and synchronizes new elements; if the
pending sync would update or remove elements, apply fails instead of escalating.
`reconcile` allows a full sync. The gateway calls `sync_devices` without a
conflict strategy, so Inspect's default `ConflictStrategy.STRICT` applies.
A reported `syncDevices` failure is an error and is not retried. Adding a
device that is not discovered yet stays `TopologyNotReadyError` and is retried
until `topology_ready_timeout`.

A module target never reaches this add/sync path.

Unchanged phases are skipped. An apply that would change nothing writes nothing.
A dry run performs the same stale-plan, conflict, and pending-edit checks without
writing. Changes report `planned`; work dependent on writes stays `deferred`.
It does not consume the plan and leaves verification `not_applicable`.

Use `engine.plan(...)` and `plan.summary()` for a read-only preview. Phases
whose edits depend on earlier writes stay `deferred` in the plan. Calling
`plan.apply()` executes the reviewed plan and checks current state before the
relevant writes.

Before an Inventory update, the gateway re-reads the record, compares
fingerprints of the managed fields, and repeats the label and address conflict
check. A response with no address item list fails the check. Before a topology
commit that was fully resolved at plan time, it re-reads the scope and compares
the fingerprint,
including sibling endpoint labels that the collision check depends on.
Module tags are re-read immediately before their phase. Pending uncommitted
Inspect edits that overlap the plan's device, vertices, or module are rejected.
The Inspect transaction then does its own baseline check. These checks are
client-side. A short gap between the read and the write remains.

If a later phase fails, earlier phases stay applied. `ProvisioningApplyError.result`
is `partial` when something was written, `failed` when nothing was, and
`unknown` when a write raised and the client cannot prove the server rejected
it (`InspectCommitError`, `InspectCommitConflictError`, `ProvisioningError`, and
known Inventory `ValueError` messages count as known rejections, including a
failed re-read that happens before `update_device` sends the update). A failed
synchronization lookup is also an error; it is not treated as "nothing pending".
Verification does not roll a write back. A mismatched or failed read-back, or a
later phase that fails before the topology read-back runs, sets `verification`
to `unconfirmed` and leaves the writes in place.

## 7. What stays outside

The package does not select a processor from the driver id, prune configuration
it used to manage, roll back a partial apply, migrate drivers, infer cables, or
provision services. Catalog tags are referenced by id and are not created.
Endpoint label uniqueness is checked per device, including endpoints outside
the changed set, and not across the system. `ApplyOptions(naming_collisions="allow")`
is the escape hatch. Names are not truncated or given a numeric suffix.

Offline tests under `tests/provisioning/` drive the engine with fakes. Live
behavior of the writes still has to be checked on a test system.
