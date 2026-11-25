# ADR-006: Variants are a fixed patch over `default`

> Status: **Superseded by [ADR-007](./007-typed-inputs.md)**
>
> What a merged field means at write time: [ADR-003](./003-managed-fields.md).

## Context

One device type often has a handful of layouts (a receiver against a sender,
for example) that share most of their driver settings. Authors will reach for
YAML anchors, merge keys, and `extends` unless the document says how composition
works.

## Options

- General composition: anchors, merge keys, includes, and list concatenation.
- One rule: `default`, then a named patch, then instance overrides. No other
  composition.

## Decision

`inventory_variant` and `topology_variant` are selected independently. Both
default to `default`. An unknown name fails and the error lists the names that
exist. There is no fallback.

A named entry patches that section's `default`:

- mappings merge by key
- scalars replace
- lists replace as a whole
- naming expressions and tag specifications replace as a whole
- `vertex_processor: null` disables an inherited processor
- a different `processor_type` replaces the whole processor declaration,
  parameters included
- a different `driver_id` drops the inherited `custom_settings`

`inventory_overrides` on `ProvisioningDevice` are a third patch, applied only to
the inventory section, and recorded as provenance `instance`.

The loader rejects YAML aliases, anchors, and merge keys, so a document cannot
smuggle a second composition language past the merge rules. Documents that
need generation are built in Python and passed to `Blueprint.from_dict`.

`schema_version` is part of this superseded document model. The published schema
is defined by [ADR-007](./007-typed-inputs.md).

## Consequences

- A variant file is readable without resolving anchors. What you see in the
  named entry is the patch, not a full copy.
- Authors cannot share a list fragment across variants. They repeat the list,
  or they generate the document in Python.
- Changing merge behavior later would change the meaning of existing files.
  That is why this is a decision record rather than a loader detail.
- `engine.json_schema()` adds the parameter schemas of processors registered
  on that engine and limits `processor_type` to them. The packaged file does
  not include third-party processors and accepts any `processor_type`.
