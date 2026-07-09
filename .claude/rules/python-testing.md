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
- Default suite (excludes e2e):

```bash
poetry run pytest
```

- Single file:

```bash
poetry run pytest tests/validators/test_device_id.py
```

Default `addopts` in `pyproject.toml` run coverage on `src/` and exclude e2e (`-m "not e2e"`).

## Assertions

- Use `pytest.raises(SpecificError)` with the exact exception type.
- Do not catch or assert against bare `Exception` when a domain error exists.

## Unit and offline tests

- Mock external I/O with fake connectors and lightweight stand-ins (see `tests/inspect/test_actions.py`).
- Load JSON fixtures from `tests/fixtures/` using `pathlib.Path`.
- Put shared fixtures in `conftest.py` at the appropriate directory level.
- Use session-scoped fixtures only when setup is expensive and reuse is intentional.

## E2E tests

- Live-server tests live under `tests/e2e/` only.
- Mark with `@pytest.mark.e2e`; they are excluded from the default suite.
- Require `VIPAT_E2E_ENABLED=1` in `tests/.env.test` and run explicitly:

```bash
poetry run pytest -m e2e tests/e2e/inspect
```

- Namespace all writes with the `E2E-` label prefix and `vipat-e2e` tag.
- Do not add e2e tests to the default CI/offline run.

## Test data

- All fixture and test data must follow anonymization rules in `AGENTS.md`.
- Preserve structure and relationships; replace real hostnames, IPs, and customer identifiers with generic placeholders.

## Coverage

- Default runs report coverage on `src/`.
- Do not disable coverage flags without a clear reason.
