---
description: Python code quality conventions for src/ and tests/
alwaysApply: false
globs: src/**/*.py,tests/**/*.py
paths:
  - "src/**/*.py"
  - "tests/**/*.py"
---

# Python code quality

## Structured data

- Use **Pydantic `BaseModel`** for API responses, settings, and schemas.
- Use **`@dataclass`** only for simple internal structs that do not need validation.
- Prefer typed models over plain `dict` for structured data.

## Exceptions

- Raise **specific, descriptive exceptions** rather than bare `Exception`.
- Follow domain error hierarchies: a base exception class plus typed subclasses with context attributes (see `src/videoipath_automation_tool/apps/inspect/errors.py`).

## Context managers

- Use `with` for files, locks, test spies, and connector wrappers.

## Quality gates

Before finishing Python changes, run:

```bash
poetry run ruff check --fix src/ tests/
poetry run ruff format src/ tests/
```

Pre-commit hooks mirror these commands (see `.pre-commit-config.yaml`).

## Generated and sensitive code

- Do **not** hand-edit `src/videoipath_automation_tool/apps/inventory/model/drivers.py` — regenerate with `set-videoipath-version <version>`.
- All committed data must follow the anonymization rules in `AGENTS.md`.

## Change scope

- Keep diffs minimal and focused.
- Match surrounding patterns: mixins, module docstrings, `TYPE_CHECKING` imports, and existing naming in the file you edit.
