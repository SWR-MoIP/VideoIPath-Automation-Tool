"""Check real pytest collection without contacting a server or running E2E fixtures."""

from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

from vipat_cli_scripts import test_runner as runner

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("selection", "expected"),
    [
        ([], {"test_provision", "test_connection", "test_other"}),
        (["tests/e2e/provisioning"], {"test_provision", "test_connection"}),
        (["tests/e2e/provisioning/test_scenario.py"], {"test_provision", "test_connection"}),
        (["tests/e2e/provisioning/test_scenario.py::test_provision"], {"test_provision"}),
        (["-k", "connection"], {"test_connection"}),
    ],
    ids=["default", "directory", "file", "node", "options-only"],
)
def test_e2e_entry_point_selects_only_requested_tests(tmp_path: Path, selection: list[str], expected: set[str]) -> None:
    (tmp_path / "pytest.ini").write_text("[pytest]\nmarkers = e2e: live test marker\n", encoding="utf-8")
    scenarios = tmp_path / "tests" / "e2e" / "provisioning"
    scenarios.mkdir(parents=True)
    prefix = "import pytest\npytestmark = pytest.mark.e2e\n"
    (scenarios / "test_scenario.py").write_text(
        prefix + "def test_provision(): pass\ndef test_connection(): pass\n", encoding="utf-8"
    )
    (scenarios.parent / "test_other.py").write_text(prefix + "def test_other(): pass\n", encoding="utf-8")
    (tmp_path / "tests" / "test_unit.py").write_text("def test_unit(): pass\n", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from vipat_cli_scripts.test_runner import run_e2e; run_e2e()",
            *selection,
            "--collect-only",
            "-q",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    collected = {line.rsplit("::", 1)[-1] for line in result.stdout.splitlines() if "::" in line}
    assert collected == expected


@pytest.mark.parametrize("unit_status", [0, 1])
def test_combined_entry_point_retains_default_suite_and_stops_on_unit_failure(
    monkeypatch: pytest.MonkeyPatch, unit_status: int
) -> None:
    calls: list[list[str]] = []
    prepared: list[bool] = []

    def run(args: list[str], *, extra: list[str]) -> int:
        assert extra == []
        calls.append(args)
        return unit_status if args is runner._UNIT_ARGS else 0

    monkeypatch.setattr(runner, "_run", run)
    monkeypatch.setattr(runner, "prepare_e2e_env", lambda: prepared.append(True))
    with pytest.raises(SystemExit) as caught:
        runner.run()
    assert caught.value.code == unit_status
    assert calls == ([runner._UNIT_ARGS] if unit_status else [runner._UNIT_ARGS, runner._E2E_ARGS])
    assert prepared == ([] if unit_status else [True])
