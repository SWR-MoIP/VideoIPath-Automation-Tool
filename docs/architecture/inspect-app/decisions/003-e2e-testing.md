# ADR-003: E2E testing strategy

> Status: **Accepted**

## Decision

**Live server E2E only — developer-run, locally, against a real VideoIPath
instance.** Offline unit tests use anonymized fixtures under
`tests/inspect/fixtures/`.

E2E tests use the Python package against a live server. Credentials and
connection details come from `.env` (see `.env.template`). No recorded HTTP
cassettes, no fake VideoIPath server.

These tests are **not** required on every CI push; they are run locally when a
developer has an instance available (`poetry run test-e2e`).

## Maintenance lifecycle suite

Run the focused maintenance suite with:

```bash
poetry run test-e2e tests/e2e/apps/test_inspect_maintenance.py
```

The suite targets the 2026.2 API and has been verified against **2026.2.0**.

Its eight cases form three groups:

- **Lifecycle — four cases:** one-time, daily, weekly, and monthly bookings.
  Checks include persisted metadata and dates, revision conflicts, lock
  preservation, start-now, filtering, and independent recurring occurrences.
- **Resource targets — three cases:** modules, ports, and edges. Checks include
  resource relationships and full snapshot reads.
- **Immediate and open-ended — one case:** nullable timestamps, schedule updates,
  and preservation of staged topology edits.

Tests assert persisted server values and returned booking IDs, not just operation
success.

Tests use exclusively their own mock-driver devices, `E2E-` labels, and the
`vipat-e2e` tag. Each test also has a unique tag for finding its bookings after a
rename or a lost response. This module disables the shared session sweep and
cleans only its own resources.

Cleanup also runs on test failure, in this order:

1. Unlock any remaining test bookings.
2. Delete the bookings and verify their absence.
3. Remove the mock devices and verify their absence from Inspect and Inventory.

Impact preview and current-impact calls assert empty service impacts on these
isolated mocks; populated impact parsing is covered offline. Start-now assertions
use server state and resolved windows, allowing server/runner clock skew.

The normal E2E gate applies, so these tests do not run in the default offline suite.

## Consequences

- Highest confidence: tests exercise the real API, auth, and payload shapes.
- Simple setup: one E2E style, one configuration path, no cassette maintenance.
- Tests are stateful, environment-dependent, and slower — acceptable for the
  current team size and Inspect scope.
- Mock/cassette/fake-server layers can be revisited via a new ADR if CI
  automation or faster feedback loops become a priority.
