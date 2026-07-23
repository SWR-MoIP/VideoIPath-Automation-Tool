---
description: Python testing conventions for src/ and tests/
alwaysApply: false
globs: src/**/*.py,tests/**/*.py
paths:
  - "src/**/*.py"
  - "tests/**/*.py"
---

# Python testing

## Framework and commands

- Use **pytest** for all tests.
- Prefer the dedicated entry points over bare `pytest`:

```bash
poetry run test-unit              # offline/unit suite (CI default)
poetry run test-e2e               # live-server e2e (loads .env)
poetry run test               # unit then e2e sequentially

# Single file or test (extra args pass through to test-unit / test-e2e)
poetry run test-unit tests/validators/test_device_id.py
poetry run test-e2e tests/e2e/inspect/test_e2e_inspect.py::test_name
```

- `poetry run pytest` also runs unit tests only (e2e excluded via `addopts` in `pyproject.toml`).

### VS Code

Use the launch configs in `.vscode/launch.json`:

- **Unit Tests** / **Unit Tests (current file)** — offline suite
- **E2E Tests** / **E2E Tests (current file)** — live-server suite

Or run **Tests** from `.vscode/tasks.json` (`poetry run test`).

## Unit vs e2e separation

| Layer | Unit | E2E |
|-------|------|-----|
| Location | `tests/` except `tests/e2e/` | `tests/e2e/` only |
| Marker | unmarked | `@pytest.mark.e2e` |
| Env | `tests/conftest.py` (dummy values) | `.env` (copy from `.env.template`) |
| Run command | `test-unit` / `pytest` | `test-e2e` |
| CI | yes | no |

Default `addopts` run coverage on `src/` and exclude e2e (`-m "not e2e"`).

## Assertions

- Use `pytest.raises(SpecificError)` with the exact exception type.
- Do not catch or assert against bare `Exception` when a domain error exists.

## Unit and offline tests

- Mock external I/O with fake connectors and lightweight stand-ins (see `tests/inspect/test_actions.py`).
- Dummy `VIPAT_*` env vars are set in `tests/conftest.py` (autouse fixture; skipped for e2e).
- Load JSON fixtures from `tests/<app>/fixtures/<version>/` using `pathlib.Path`.
- Put shared fixtures in `conftest.py` at the appropriate directory level.
- Use session-scoped fixtures only when setup is expensive and reuse is intentional.

## E2E tests

- Live-server tests live under `tests/e2e/` only.
- Mark with `@pytest.mark.e2e`; they are excluded from the default suite.
- E2e entry points (`poetry run test-e2e`, `poetry run test`, VS Code **E2E Tests**) load `.env` and enable the suite automatically. E2e runs use `--no-cov`.
- Copy `.env.template` to `.env` (gitignored), set connection vars. The e2e conftest loads `.env` automatically when present.
- Run with `poetry run test-e2e` (no extra env vars on the command line).
- Namespace all writes with the `E2E-` label prefix and `vipat-e2e` tag.
- Do not add e2e tests to the default CI/offline run.

## Test data

- All fixture and test data must follow anonymization rules in `AGENTS.md`.
- Preserve structure and relationships; replace real hostnames, IPs, and customer identifiers with generic placeholders.

## Coverage

- Default runs report coverage on `src/`.
- Do not disable coverage flags without a clear reason.
