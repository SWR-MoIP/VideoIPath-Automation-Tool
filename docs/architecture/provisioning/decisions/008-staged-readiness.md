# ADR-008: Independent Inventory and topology readiness deadlines

> Status: **Accepted**
>
> Refines the phase order and readiness timing in [ADR-002](./002-plan-then-apply.md)
> and supersedes the retry policy in [ADR-004](./004-processors-propose.md).

## Context

An accepted Inventory write does not mean VideoIPath can connect to the device.
Topology membership, synchronization, ports, and vertices can appear later.
A shared timeout obscures which stage stalled and lets Inventory waiting consume
the time needed for topology discovery. Mock and static devices may never report
reachability even though their topology is usable.

## Decision

Apply phases are `inventory`, `inventory_readiness`, `topology_sync`, `discovery`,
`topology`, `module_tags`, and `verification`.

Before deferred topology rollout for an Inventory-backed device, poll fresh
Inventory status until `reachable=True`. Each attempt calls
`InventoryApp.refresh_device_status()` once; the executor does not use the
SDK's internally retried `get_device(config_only=False)`. Only
`InventoryStatusUnavailableError` and `reachable=False` remain pending.
Transport failures and malformed status fail immediately.

`ApplyOptions.inventory_ready_timeout` defaults to 10 seconds. After that gate
succeeds, a new `topology_ready_timeout` budget of 60 seconds covers topology
addition, synchronization, and the required ports and vertices. Both timeouts
and `poll_interval` (default 1 second) must be positive and finite. Deadlines use
the injected monotonic clock, include request time, and never restart on
progress. The first check is immediate; sleeps are capped to the remaining
budget. No new readiness requests or rollout actions begin after expiry.
In-flight HTTP requests retain their connector-level timeouts.

`require_reachable=False` explicitly bypasses the Inventory gate for mock or
static devices. Virtual targets and module-only topology targets without their
own Inventory binding skip it. Otherwise, check the created or bound Inventory
record, falling back to a physical topology target's Inventory record. A module
target never causes addition or synchronization of its entire parent device.

Inventory-only applies finish after Inventory. Fully resolved topology plans do
not acquire a reachability requirement. Topology-changing Inventory updates
still stop with `partial` and `replan_required=True` before rollout.

Topology polling reads fresh membership, synchronization state, and scoped data.
Confirm membership and finish permitted synchronization before configuration
writes. An accepted addition is not resubmitted while membership or ports are
pending. An accepted synchronization with the same pending changes is polled;
newly discovered changes may require another synchronization under the captured
policy. Permanent processor, capability, and synchronization errors fail at once.
Only local `TopologyNotReadyError` signals missing data that can be retried.
Unknown write outcomes are never automatically retried.

Planning converts local `TopologyNotReadyError` into deferred topology work,
including when an earlier rollout already added the device. Planning and dry
runs never sleep, and dry runs report deferred readiness without rollout actions.
Missing peer edges continue to require a new plan.

## Consequences

- `discovery_timeout` is removed without an alias. Callers configure the two
  deadlines and, where needed, the explicit reachability bypass.
- Inventory timeouts raise `InventoryNotReadyError`; topology timeouts raise
  `TopologyNotReadyError`. Both identify the device, stage, configured timeout,
  and last observed condition in the partial result's failed phase.
- Known IDs and successful operations survive failure. A caller can bind the
  returned Inventory ID and plan again without creating a duplicate record.
- Timeouts bound readiness polling, not an entire apply or a request already in
  flight. Configuration writes and verification follow successful readiness.
- Blueprint YAML and its generated schema are unchanged.
