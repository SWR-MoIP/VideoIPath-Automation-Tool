# ADR-0005: E2E testing strategy

> Status: **Accepted**
> Date: 2026-06-15 · Deciders: Paul Winterstein, Jonas Scholl

## Context

Inspect spans config CRUD and status reads against a proprietary server whose
payloads vary by version. Tests must be **low-effort and trustworthy** — when
green they should genuinely mean "this works against VideoIPath".

Today the suite is small (validators) and a live server is configured via
`tests/.env.test` + `pytest-dotenv`. There is precedent for "validate our
assumptions against the live server": `advanced_driver_schema_check` compares
local vs. server driver schemas.

We want to keep testing **simple** for now: one layer, run locally by the
developer against a real instance — not a multi-tier strategy with mocks,
cassettes, and fake servers.

## Options

- **Live server only** — trustworthy, but flaky/stateful/slow; bad for CI on
  every push.
- **Recorded HTTP interactions** (`respx` for `httpx` / `vcrpy` for `requests`)
  — record real request/response pairs once, replay offline. Fast, stable,
  realistic — as long as cassettes are periodically re-recorded.
- **Fake VideoIPath server** (small FastAPI app emulating endpoints + WS) — more
  setup, but enables deterministic **end-to-end incl. WebSocket** flows that
  cassettes can't easily replay.
- **Fixture/contract tests** — assert our Pydantic models parse real captured
  payloads and our diff logic produces expected patches. Cheap, deterministic,
  catches model drift.

## Decision

**Live server E2E only — developer-run, locally, against a real VideoIPath instance.**

E2E tests use the Python package to execute full test scenarios against a live
server. The developer provides credentials and connection details (via
`tests/.env.test` or equivalent). No recorded HTTP cassettes, no fake VideoIPath
server, and no separate contract/fixture test layer for now.

These tests are **not** required on every CI push; they are run locally when a
developer has an instance available.

## Consequences

- Highest confidence: tests exercise the real API, auth, and payload shapes.
- Simple setup: one test style, one configuration path, no cassette maintenance.
- Tests are stateful, environment-dependent, and slower — acceptable trade-off
  for the current team size and Inspect scope.
- Mock/cassette/fake-server layers can be revisited via a new ADR if CI
  automation or faster feedback loops become a priority.
