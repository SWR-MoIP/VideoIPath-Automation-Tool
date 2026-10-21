# ADR-004: Processors propose, the engine writes

> Status: **Accepted**
>
> Where the proposal is computed: [ADR-005](./005-app-gateways.md).
>
> The original retry policy below is superseded by
> [ADR-008](./008-staged-readiness.md): only `TopologyNotReadyError` is retried;
> `ProcessorInputError` fails immediately.

## Context

Device types do not share a vertex layout. Matrox ConvertIP endpoints are not
the same shape as the next driver. That interpretation changes more often than
the write path, and it has to be replaceable per engine without editing
Inventory or Inspect.

## Options

- Teach the engine one layout per `driver_id`.
- Let a processor call `app.inspect` and write the vertices it wants.
- Let a processor return a typed proposal. The engine validates, names,
  compares, and writes.

## Decision

A `VertexProcessor` implements `process(context, params) -> ProcessorResult`.
`params` are a strict Pydantic model declared as `params_model`. A new instance
is created for each run.

`ProcessingContext` is a frozen snapshot of one device or one module: source
facts without credentials, ports, vertices, resolved interface bindings, and
optional driver context. It is not a reference to the live Inspect snapshot. A
module target's context contains only that module's vertices. Returning an id
outside the scope fails.

The engine rejects device patches on a module target, module patches on a
device target, conflicting proposals (identical duplicates are merged), and
kind-specific fields on the wrong vertex kind (`sdp_support` and destination
ports need a codec vertex, `supports_static_igmp` an IP vertex). Explicit `topology.device` values override
processor device defaults. Naming overrides proposed labels. Explicit `vertices`
overrides win over both.

The original policy treated `ProcessorInputError` as an unsupported or not-yet-ready
layout and retried it during deferred topology work until `discovery_timeout`.
See ADR-008 for the current distinction between readiness and permanent errors.

Registration is per engine ([ADR-001](./001-standalone-feature.md)). Duplicate
ids fail, including the built-in `matrox.convertip.default`. YAML names the
registered id. It does not name a Python import path. The built-in is included
unless a registry is built with `include_builtins=False`.

## Consequences

- New device types are new classes, not new branches in the executor.
- Processors are trusted code in the caller's process. The contract stops
  accidental writes through the engine. It does not sandbox a processor that
  opens its own network connection.
- The engine does not pick a processor by driver id. The blueprint names
  `processor_type`. An Inventory-only plan does not need a topology processor.
- `engine.validate()` resolves every variant and reports processors that are
  not registered. Planning only requires the processor for the selected scope.
