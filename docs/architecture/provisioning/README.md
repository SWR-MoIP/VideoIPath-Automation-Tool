# Provisioning — Architecture

Design record for the declarative provisioning layer in this package
(`src/videoipath_automation_tool/provisioning/`).

Provisioning automates device configuration in an Infrastructure as Code style
on top of the existing VideoIPath SDK. A blueprint is one part of this layer:
a reusable configuration template for a device type. `ProvisioningEngine`
combines that template with device facts, previews the changes, and writes them
through the existing Inventory and Inspect apps. `VideoIPathApp` does not import
or expose the feature. You construct the engine yourself.

For a short introduction, start with the
[getting-started page](../../getting-started-guide/05_Provisioning.md). Runnable
scripts are in [docs/examples/07_provisioning](../../examples/07_provisioning/).
Offline tests live under `tests/provisioning/`. Live-server workflows live under
`tests/e2e/provisioning/`; see [E2E coverage](#e2e-coverage) below.

## Reading order

1. **[reference.md](./reference.md)** — complete user reference: engine API,
   `ProvisioningDevice`, the YAML document, variants, loading, naming, apply phases,
   errors, configuration, limits, and the public API index.
2. **[processors.md](./processors.md)** — the vertex processor contract and the
   built-in Matrox ConvertIP processor.
3. **[concepts.md](./concepts.md)** — boundaries, module map, and the plan/apply flow.
4. **[decisions/](./decisions/)** — the choices that would be expensive to reverse.
   Start with [the index](./decisions/README.md).

The topology phase commits through Inspect's existing transaction. That write
model is recorded in
[Inspect ADR-004](../inspect-app/decisions/004-commit-write-model.md).

## E2E coverage

Run against a configured local test instance:

```bash
poetry run test-e2e tests/e2e/provisioning
poetry run test-e2e tests/e2e/provisioning/test_lifecycle.py
poetry run test-e2e tests/e2e/provisioning/test_lifecycle.py::test_preview_apply_and_idempotent_reapply
```

The entry point loads the gitignored project `.env`, including legacy
`VIDEOIPATH_*` connection variables. Explicit paths select only those tests.
The suite requires VideoIPath 2025 or newer, the server's
`com.nevion.mock-0.1.0` driver, and permissions to configure Inventory, Inspect,
and catalog tags. It needs no physical devices. It is excluded from the default
offline/CI test run.

The scenarios cover YAML inputs and variants, preview and dry run, onboarding,
Inventory/topology scope isolation, managed-field preservation, endpoint naming,
module-local tags, directed connections, deferred peers, rediscovery and sync
policies, stale plans, and recovery from an Inventory readiness timeout. Each
scenario owns its devices and checks persisted values through fresh server reads.
Mutation spies forward calls to the real SDK and verify that dry runs and
idempotent reapplications issue no writes.

Devices use unique `E2E-` labels and the resolved `vipat-e2e` catalog tag. They
remain on the server for manual inspection after success or failure. As with
the rest of the E2E suite, the next E2E session removes **all** prior `E2E-`
resources, including resources from other E2E scenarios, before creating new
ones. Run live sessions serially against an instance. Discovery polling is bounded;
transport errors and unexpected failures are not retried.

External connection behavior is recorded in [ADR-009](./decisions/009-external-connections.md).

## Decision log

| Question | Decision | Status |
| -------- | -------- | ------ |
| Where does the feature sit in the package? | [ADR-001](./decisions/001-standalone-feature.md) | Accepted |
| How is a change previewed and written? | [ADR-002](./decisions/002-plan-then-apply.md) | Accepted |
| What does a blueprint update touch? | [ADR-003](./decisions/003-managed-fields.md) | Accepted |
| Who interprets discovered vertices? | [ADR-004](./decisions/004-processors-propose.md) | Accepted |
| Who may call Inventory and Inspect? | [ADR-005](./decisions/005-app-gateways.md) | Accepted |
| How do blueprint inputs and variants resolve? | [ADR-007](./decisions/007-typed-inputs.md) | Accepted |
| When is a device ready for rollout? | [ADR-008](./decisions/008-staged-readiness.md) | Accepted |
