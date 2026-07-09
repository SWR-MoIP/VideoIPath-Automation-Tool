"""Gating and shared fixtures for the developer-run live-server E2E suite ([ADR-0005]).

These tests are excluded by default (``-m "not e2e"`` in ``pyproject.toml``) and only run when:
  * you invoke an e2e entry point (``poetry run test-e2e``, ``poetry run test``, or VS Code **E2E Tests**), **and**
  * connection vars are set in the project root ``.env`` (copy from ``.env.template``), **and**
  * the target server is a verified version (>= 2025.4).

E2e entry points load ``.env`` and enable the suite automatically. E2e runs never collect coverage
(``--no-cov``).

Everything the suite writes is namespaced (``E2E-`` label prefix + ``vipat-e2e`` tag) so a shared
local instance is safe. Cleanup has two layers: a session-start sweep removes any leftovers from
prior runs, and the per-test ``topology_builder`` fixture removes exactly the devices a test
created (also on failure). The sequential workflow suite intentionally leaves its topology behind
for manual inspection; the next run's sweep removes it.
"""

from __future__ import annotations

import os
from itertools import count
from typing import Iterator

import pytest

from videoipath_automation_tool.apps.inspect.app.app import _MIN_VERIFIED_VERSION, _parse_version
from videoipath_automation_tool.apps.videoipath_app import VideoIPathApp
from vipat_cli_scripts.project_env import load_project_env

from .helpers import TopologyBuilder, remove_devices, sweep_e2e_namespace

load_project_env()

_STEP_FAILED_KEY = pytest.StashKey[str]()


def _e2e_enabled() -> bool:
    return os.environ.get("VIPAT_E2E_ENABLED", "").strip() == "1"


@pytest.fixture(scope="session")
def app() -> VideoIPathApp:
    """A live ``VideoIPathApp`` built from the project ``.env``; skips unless E2E is enabled + verified."""
    load_project_env()
    if not _e2e_enabled():
        pytest.skip("E2E disabled (use poetry run test-e2e, poetry run test, or the VS Code E2E launch config).")
    application = VideoIPathApp()
    version = application._videoipath_connector.videoipath_version
    parsed = _parse_version(version)
    if parsed is None or parsed < _MIN_VERIFIED_VERSION:
        pytest.skip(
            f"Server version '{version}' is below the verified Inspect baseline "
            f"{_MIN_VERIFIED_VERSION[0]}.{_MIN_VERIFIED_VERSION[1]}."
        )
    return application


@pytest.fixture(scope="session", autouse=True)
def e2e_sweep(app: VideoIPathApp) -> None:
    """Session-start sweep: remove every ``E2E-`` device left over from a prior run."""
    sweep_e2e_namespace(app)


@pytest.fixture(scope="session")
def e2e_addresses() -> Iterator[str]:
    """Session-wide device address allocator (private ``10.99.0.0/16`` range), so addresses never collide."""
    return (f"10.99.{i // 256}.{i % 256}" for i in count(1))


@pytest.fixture
def topology_builder(app: VideoIPathApp, e2e_addresses: Iterator[str]) -> Iterator[TopologyBuilder]:
    """A per-test topology factory; teardown removes exactly the devices the test created."""
    builder = TopologyBuilder(app, e2e_addresses)
    yield builder
    remove_devices(app, set(builder.device_ids))


# --- Sequential workflow support (``@pytest.mark.incremental``) ---
# Later steps of a sequential suite are skipped (not failed) once an earlier step fails. With the
# default ``-x`` in ``addopts`` the run stops at the first failure anyway; these hooks make the
# behavior sensible without it too (e.g. ``--maxfail=0``).


def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo) -> None:
    if "incremental" not in item.keywords or item.parent is None:
        return
    if call.excinfo is not None and not call.excinfo.errisinstance(pytest.skip.Exception):
        item.parent.stash.setdefault(_STEP_FAILED_KEY, item.name)


def pytest_runtest_setup(item: pytest.Item) -> None:
    if "incremental" not in item.keywords or item.parent is None:
        return
    failed = item.parent.stash.get(_STEP_FAILED_KEY, None)
    if failed is not None:
        pytest.skip(f"previous workflow step failed ({failed})")
