"""Pytest entry points for unit, e2e, and combined test suites."""

from __future__ import annotations

import sys

import pytest

from vipat_cli_scripts.project_env import prepare_e2e_env

_UNIT_ARGS = ["-m", "not e2e", "--ignore=tests/e2e"]
_E2E_ARGS = ["-m", "e2e", "tests/e2e", "--no-cov"]


def _run(args: list[str], *, extra: list[str] | None = None) -> int:
    return pytest.main([*args, *(extra if extra is not None else sys.argv[1:])])


def run_unit() -> None:
    raise SystemExit(_run(_UNIT_ARGS))


def run_e2e() -> None:
    prepare_e2e_env()
    raise SystemExit(_run(_E2E_ARGS))


def run() -> None:
    rc = _run(_UNIT_ARGS, extra=[])
    if rc != 0:
        raise SystemExit(rc)
    prepare_e2e_env()
    raise SystemExit(_run(_E2E_ARGS, extra=[]))
