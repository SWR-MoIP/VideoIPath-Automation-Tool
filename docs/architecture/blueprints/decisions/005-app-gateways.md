# ADR-005: Inventory and Inspect are reached through two gateways

> Status: **Accepted**
>
> Why the feature is not on the app: [ADR-001](./001-standalone-feature.md).

## Context

The engine needs current Inventory records, a scoped Inspect topology, an
Inspect commit, and module tag actions. Inspect also keeps a live snapshot with
uncommitted domain-object edits. Reading that snapshot during planning would
treat a caller's unsaved edits as server truth, or flush them.

## Options

- Call `app.inventory` and `app.inspect` from the planner and the executor
  wherever a read or write is needed.
- Confine every app call to `inventory.py` and `inspect.py`.

## Decision

`InventoryGateway` is the only object that calls `app.inventory`. It reads one
record, resolves an SNMP configuration by exact label or id, creates with
`add_device`, and updates with `update_device`. Label lookups use
`find_device_id_by_label`. Address conflict checks use
`find_device_ids_by_addresses`: one read for all addresses, compared after
normalization on both sides (IP literals in compressed form, other identifiers
case-insensitively). An empty item list is no match. A response with no item
list raises; the gateway turns that into `BlueprintError`.

`InspectGateway` is the only object that calls `app.inspect`. Scope data is
built from fresh collector and lookup reads (`get_device_detail`,
`lookup_inspect_device`, `lookup_vertices`), not from the live snapshot's
domain objects. If the collector already has the device, a failed edit-form
lookup is `BlueprintError`. The virtual-device fallback, where there is no
topology node, still treats a missing form as absent. Pending edits are visible
only through `staged_edit_keys()`, which is used to reject overlap, not to seed
the plan. A reported `syncDevices` failure is `BlueprintError` and is not
retried. `addDevices` failure stays `TopologyNotReadyError`.

Topology writes go through one `InspectTransaction`: `update_device` and
`update_vertex` intents, then `commit()`. Module tags use `assignTag` and
`unassignTag` on the internal Inspect API handle, because those actions are
not part of `updateTopology`. After tag writes, the gateway asks the snapshot,
if one is loaded, to refresh that device.

Processors never receive a gateway. They receive `ProcessingContext`
([ADR-004](./004-processors-propose.md)).

## Consequences

- A test can replace the two app surfaces without standing up HTTP.
- A change to Inventory or Inspect call style has two files to update, not the
  planner.
- `InspectGateway` reaches `_inspect_api` for detail reads and tag actions.
  That is a deliberate crack in the public-method rule, limited to this
  module, because the public Inspect app does not expose those calls in the
  shape the engine needs.
- Fresh reads can disagree with the snapshot the caller is looking at. That
  is intentional. The plan describes server state. Overlapping uncommitted
  edits fail the apply until the caller commits or discards them.
