# ADR-009: Concrete external edges belong to the device instance

> Status: **Accepted**
>
> Extends [ADR-003](./003-managed-fields.md) and [ADR-005](./005-app-gateways.md).

## Context

Provisioning a device includes configuring its external edges. Reusable
device templates must remain independent of instance-specific cabling and the
system supplying it. IP interfaces and directed media ports need the same flow.

## Decision

`TopologyConfig.port_mapping` maps reusable local names to ordered port selectors
in the blueprint document. Existing overlay and typed-input semantics apply. The separate
`ip_vertex_mapping` and processor `interfaces` retain their existing behavior;
generic mappings are exposed as `port_bindings`.

`ProvisioningDevice.edges` declares each concrete edge through
`ProvisioningEdge`, `PeerEndpoint` and `EdgePatch`. The local port is a
mapping key or direct selector. Peers use exact VideoIPath device/module ids
and port selectors. Source-system adapters remain outside provisioning.

Direction is derived from actual Out/In vertices, with explicit direction
overrides. Vertex ids are never synthesized from naming conventions. Edges are
identified by their directed vertex pair, created when absent, and updated only
in explicitly managed fields. Other edges are preserved; empty input never prunes.

The Inspect gateway reads peers and edge forms freshly, checks captured baselines
and staged-edit overlap, and commits device, vertex and edge intents together in
the existing topology transaction. Pure resolution/diff logic lives in
`edges.py`; processors receive no gateway or external write scope.

Missing peer discovery is reported per edge as `deferred`. Remaining local
work and resolved edges can run. The result is `partial` with
`replan_required=True`, even if no write was necessary. A new plan is needed when
peers appear; applying an old plan does not adopt new peer topology. Invalid
selectors, ambiguous directions and failed reads are errors, not pending work.

## Consequences

- Blueprint and instance facts fully describe the requested configuration.
- One `ProvisioningEdge` declaration can produce one directed VideoIPath edge or both directions.
- Missing peers do not prevent otherwise valid local onboarding.
- Plans and results expose bindings, concrete edge ids and unresolved reasons.
- No peer provisioning, implicit synchronization, pruning or rollback is added.
