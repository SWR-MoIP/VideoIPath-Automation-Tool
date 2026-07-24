# ADR-008: Post-commit snapshot maintenance — targeted invalidation + scoped re-fetch

> Status: **Accepted** — extends [ADR-005](./005-lazy-snapshot-loading.md)
> to the write path ([ADR-004](./004-commit-write-model.md))

## Decision

**Targeted invalidation + scoped re-fetch of affected entities**, with lazy
fallback for sections. After a successful commit:

1. **Compute the affected set** from the change set and the commit response
   `items[]`: devices (replaced/removed + owners of touched vertices/edges) and
   edge pairs (`deviceA::deviceB`).
2. **Apply removes locally** — deleted entities leave the indexes immediately.
3. **Invalidate and eagerly re-fetch** remaining affected entities with the
   existing scoped queries (`nodeStatus/<device-id>/…`,
   `externalEdgesByDeviceKey/<deviceA::deviceB>/…`). Drop cached domain objects;
   update per-entity fetch timestamps.
4. **Sections go stale, not eager** — services and alarms re-load lazily on next
   access.
5. **No retry window** — on 2025.4.9 the collector projection updates
   effectively synchronously with the commit (~25 ms to first-poll visibility).
   The targeted re-fetch doubles as the verification read.

A failed commit changes nothing server-side — the snapshot is left untouched.

**Extensions:**

- **Network actions** (`addDevices` / `syncDevices`) call
  `apply_network_refresh(device_ids)`: upsert named devices and reconcile
  edge pairs from one edge-skeleton read scoped to pairs touching an affected
  device.
- **Refresh is resilient.** A failed scoped re-fetch marks just that entity
  stale and logs; never propagates. Stale entities self-heal on next access.

## Consequences

- Post-commit cost is proportional to **change-set size**, not network size.
- The snapshot stays a pure read model built from collector responses — no
  fabricated entries.
- Together with ADR-007: `commit()` = pre-commit conflict check → POST →
  result evaluation → targeted refresh.
