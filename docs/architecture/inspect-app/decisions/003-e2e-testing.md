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

## Consequences

- Highest confidence: tests exercise the real API, auth, and payload shapes.
- Simple setup: one E2E style, one configuration path, no cassette maintenance.
- Tests are stateful, environment-dependent, and slower — acceptable for the
  current team size and Inspect scope.
- Mock/cassette/fake-server layers can be revisited via a new ADR if CI
  automation or faster feedback loops become a priority.
