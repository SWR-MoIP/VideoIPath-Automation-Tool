# ADR-003: Updates touch only managed fields

> Status: **Accepted**

## Context

A blueprint is reused across devices and edited over time. Callers also set
fields in the VideoIPath UI, or with other scripts, that the blueprint does not
mention. An update has to change the fields the blueprint owns without wiping
the rest.

## Options

- Treat the blueprint as a full desired document and reset every omitted field.
- Remember the last applied document and revert fields that disappeared from it.
- Write only fields the resolved blueprint, the instance facts, or naming set
  on this run.

## Decision

Absence means unmanaged. An update deep-copies the current Inventory record and
overlays managed fields only. The same rule applies to topology patches:
`DevicePatch`, `ModulePatch`, and `VertexPatch` reject `null`, because `null`
would be ambiguous with "leave it alone". Explicit `false`, `0`, `[]`, and
`""` are values. `[]` clears a list that is managed, such as local tags or
alternate addresses.

There is no stored last-applied state. Removing a key from a blueprint, or
switching variant, does not put the previous value back. A variant that must
turn something off has to set the new value.

Naming follows the same rule. An entry left unset is unmanaged. An entry set
to `None` in a later naming layer turns that name off. Rendered names come from
caller facts and endpoint identity, not from the label currently on the server.

The Inventory round-trip preserves what `InventoryDevice` represents, which is
the same boundary as `InventoryApp.update_device`. Wire fields those models do
not parse are dropped. Once a managed change exists, the engine calls
`update_device(..., compare_config=False)` so an explicit credential change is
not swallowed by Inventory's own authentication filter.

## Consequences

- A second apply of an unchanged blueprint is a no-op for fields that already
  match, and it does not rename by appending to the current label.
- The engine cannot garbage-collect a tag or a setting it applied last year
  and no longer mentions. Pruning is a caller decision: set the new value.
- Plans can show provenance per managed field. They cannot show "this server
  value came from a previous blueprint".
- Secrets are redacted in `FieldChange` and in `summary()`, and they are kept
  on the private captured work used to write.
- Secrets are write-only. The server masks them on read, so they are never
  compared and never cause an update on their own. They are written on create
  and with every update; `ApplyOptions(write_credentials=True)` forces a write
  for a credential-only change.
