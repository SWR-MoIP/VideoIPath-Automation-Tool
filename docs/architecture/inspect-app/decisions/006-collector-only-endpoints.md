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

- **No `_rev` is available** to the Inspect package, and the write path
  enforces none (last-writer-wins). Write consistency is solved client-side —
  [ADR-007](./007-write-consistency.md).
- Persisted forms for `replace*` payloads come from collector-namespace lookups
  (`lookupInspectDevice`, `lookupInspectVertexByIds`,
  `lookupInspectEdgesByIds`), not from `nGraphElements` reads.
- The connector URL allow-list for Inspect gains only Inspect-surface prefixes.
