# ADR-006: Collector-only endpoint policy (no legacy topology API)

> Status: **Accepted**

## Decision

**The Inspect package uses only the Inspect surface.** Allowed at runtime:

| Kind | Endpoints |
| ---- | --------- |
| Data reads | `GET /rest/v2/data/status/collector/…` (scoped queries and `/**`) |
| Collector actions | `POST /rest/v2/actions/status/collector/*` (`updateTopology`, lookups, …) |
| Network actions | `POST /rest/v2/actions/status/network/{addDevices,syncDevices,updateVirtualInstances,updateVirtualTemplates,addVirtualTopology}` |
| Tag actions | `POST /rest/v2/actions/status/tags/{assignTag,unassignTag}` |
| Maintenance actions | `POST /rest/v2/actions/status/pathman/{updateMaintenance,validateMaintenanceImpactDetailed,fetchMaintenanceImpact}` (exact allow-list entries) |
| Alarm reads | `GET /rest/v2/data/status/alarms/current/…` |
| Virtual reads | `GET /rest/v2/data/status/network/{virtualDevices,virtualTemplates}/**` |
| System probes | `GET /rest/v2/data/status/system/about/…` (version gating) |

Explicitly **not called** by the package:

- `GET`/`PATCH /rest/v2/data/config/network/nGraphElements/**`
- `GET /rest/v2/data/status/network/edgesByDevice/**`
- RPC topology calls

These stay documented in [endpoints.md](../endpoints.md) as store documentation
only. `app.topology` remains the escape hatch for raw, revisioned
`nGraphElements` access.

## Consequences

- **Topology collector reads have no `_rev`**, and topology writes enforce
  none (last-writer-wins). Topology write consistency is solved client-side —
  [ADR-007](./007-write-consistency.md).
- Maintenance collector reads expose `rev`. Maintenance updates use a fresh read
  and submit that revision; `expected_rev` optionally checks the caller's baseline.
  These immediate actions run independently of topology transactions. The three
  pathman actions above were verified on **2026.2.0**; no general pathman prefix
  is allowed. Compatibility with older versions is untested.
- Persisted forms for `replace*` payloads come from collector-namespace lookups
  (`lookupInspectDevice`, `lookupInspectVertexByIds`,
  `lookupInspectEdgesByIds`), not from `nGraphElements` reads.
- The connector URL allow-list for Inspect gains only Inspect-surface prefixes.
