# ADR-007: Typed inputs and ordered overlays

> Status: **Accepted**
>
> Supersedes [ADR-006](./006-variant-merge.md). Managed-field semantics remain
> defined by [ADR-003](./003-managed-fields.md).

## Context

Reusable device configuration needs instance values from arbitrary callers.
Separate Inventory and Topology variant axes limit composition and mix base
configuration with named patches. Source-system models do not belong in YAML.

## Decision

The document has `schema_version: 1`, typed `inputs`, Inventory/Topology
`defaults`, and optional `variants`. Each variant can patch either section or
both. Callers explicitly select an ordered sequence; later variants win.

Resolution copies defaults, merges overlays, inserts typed input values,
applies instance Inventory overrides, then validates the effective configuration.
Mappings merge; lists, tag specifications and individual naming expressions
replace. Driver changes discard custom settings; processor changes replace
processor parameters. Input and literal operators replace whole nodes.

Input declarations use a strict, recursive JSON Schema vocabulary for scalar,
array and object values. Objects are closed by default. Supplied values replace
input defaults without coercion. Missing inputs fail when the effective scope
uses them. `{$input: name}` inserts a value; `{$literal: ...}` escapes operators.
Inserted values are never interpreted again. Naming can use input scalar leaves.

The existing runtime configuration models also define document template fields
and editor schemas. Runtime driver and registered processor validation follows
binding. Loader errors retain YAML positions; resolved leaves retain YAML and
input provenance. Source ids, credentials and source-system adapters stay with
the caller. No source system selects variants implicitly.

The generated schema is `blueprint-v1.schema.json`. Offline validation checks
defaults and each variant separately, or one explicit combination; planning
checks the chosen combination and scope before server I/O.

## Consequences

The same blueprint works with hand-written facts, NetBox, CSV or any other
adapter. Existing configuration and execution capabilities remain available.
Callers can combine independent policies and device layouts without creating a
variant for every pair.

Plans capture copied input values and the selected order, so later caller edits
do not change execution. YAML remains self-contained and uses the safe loader;
there is no import, expression-evaluation or fleet-execution language.
