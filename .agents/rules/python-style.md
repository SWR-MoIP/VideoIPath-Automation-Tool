---
description: Python coding style for src/ and tests/
alwaysApply: false
globs: src/**/*.py,tests/**/*.py
paths:
  - "src/**/*.py"
  - "tests/**/*.py"
---

# Python coding style

## Type hints

- Annotate all function parameters and return types.
- Use `from __future__ import annotations` in new modules.
- Use `TYPE_CHECKING` blocks for imports needed only for type hints.

## Formatting and naming

- Follow PEP 8 with **snake_case** for functions, variables, and modules.
- Max line length is **120** characters (ruff formatter default in this project — not Black's 88).
- Format with **ruff**, not Black:

```bash
poetry run ruff format src/ tests/
```

## Strings and paths

- Use **f-strings** for string formatting; avoid `%` formatting and `.format()`.
- Use **`pathlib.Path`** over `os.path` for filesystem operations.

## Comprehensions and readability

- Prefer list/dict/set comprehensions over explicit loops when the result stays readable.
- Do not sacrifice clarity for brevity.

## Layout and whitespace

- Group **logically related lines** together (e.g. setup, core logic, cleanup).
- Separate groups with a **single blank line**; use an extra blank line between larger sections when it aids scanning.
- Do not sprinkle blank lines randomly, and do not leave long unbroken blocks when a visual break would help.
- Within a function, keep the main path easy to follow: inputs and validation first, then the core work, then return/cleanup.

## Public before private

- Place **public** API first so readers see the most relevant surface when scrolling: public classes, methods, functions, and module-level constants.
- Place **private** members after public ones: names prefixed with `_` (attributes, methods, functions, nested helpers) and internal implementation details.
- In classes: public methods first, then `_`-prefixed helpers and internal state accessors.
- In modules: public exports and user-facing functions first; private helpers and module-internal constants at the bottom.
- A short section comment (e.g. `# --- Internal ---`) is fine when a class or module has a large private block.

## Resources

- Use **context managers** (`with`) for files, locks, and other resources that need cleanup.
