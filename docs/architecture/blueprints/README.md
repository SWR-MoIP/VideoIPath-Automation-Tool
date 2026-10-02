# Blueprints — Architecture

Design record for the blueprint feature in this package
(`src/videoipath_automation_tool/blueprints/`).

A blueprint is a reusable description of one device type. `BlueprintEngine` combines
that description with the facts of one device, previews the changes, and writes
them through the existing Inventory and Inspect apps. `VideoIPathApp` does not
import or expose the feature. You construct the engine yourself.

For a short introduction, start with the
[getting-started page](../../getting-started-guide/05_Blueprints.md). Runnable
scripts are in [docs/examples/07_blueprints](../../examples/07_blueprints/).
Offline tests live under `tests/blueprints/`. There is no live-server suite for
this feature yet.

## Reading order

1. **[reference.md](./reference.md)** — complete user reference: engine API,
   `BlueprintDevice`, the YAML document, variants, loading, naming, apply phases,
   errors, configuration, limits, and the public API index.
2. **[processors.md](./processors.md)** — the vertex processor contract and the
   built-in Matrox ConvertIP processor.
3. **[concepts.md](./concepts.md)** — boundaries, module map, and the plan/apply flow.
4. **[decisions/](./decisions/)** — the choices that would be expensive to reverse.
   Start with [the index](./decisions/README.md).

The topology phase commits through Inspect's existing transaction. That write
model is recorded in
[Inspect ADR-004](../inspect-app/decisions/004-commit-write-model.md).

## Decision log

| Question | Decision | Status |
| -------- | -------- | ------ |
| Where does the feature sit in the package? | [ADR-001](./decisions/001-standalone-feature.md) | Accepted |
| How is a change previewed and written? | [ADR-002](./decisions/002-plan-then-apply.md) | Accepted |
| What does a blueprint update touch? | [ADR-003](./decisions/003-managed-fields.md) | Accepted |
| Who interprets discovered vertices? | [ADR-004](./decisions/004-processors-propose.md) | Accepted |
| Who may call Inventory and Inspect? | [ADR-005](./decisions/005-app-gateways.md) | Accepted |
| How do blueprint variants combine? | [ADR-006](./decisions/006-variant-merge.md) | Accepted |
