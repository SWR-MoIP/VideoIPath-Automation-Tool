# ADR-0005: E2E testing strategy

> Status: **Proposed**
> Date: 2026-06-15 · Deciders: Paul Winterstein, Jonas Scholl

## Context

Inspect spans config CRUD, status reads, and a WebSocket channel against a
proprietary server whose payloads vary by version. Tests must be **low-effort,
stable, and trustworthy** — i.e. they should fail only for real regressions, and
when green they should genuinely mean "this works against VideoIPath".

Today the suite is small (validators) and a live server is configured via
`tests/.env.test` + `pytest-dotenv`. There is precedent for "validate our
assumptions against the live server": `advanced_driver_schema_check` compares
local vs. server driver schemas.

The tension: a **live-only** suite is the most trustworthy but is slow, flaky,
stateful, and needs infrastructure; a **mock-only** suite is fast and stable but
only tests our assumptions, not reality.

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

_To be decided._
