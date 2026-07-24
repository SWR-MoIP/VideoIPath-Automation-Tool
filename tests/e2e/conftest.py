"""Gating and shared fixtures for the developer-run live-server E2E suite.

These tests are excluded by default (``-m "not e2e"`` in ``pyproject.toml``) and only run when:
  * you invoke an e2e entry point (``poetry run test-e2e``, ``poetry run test``, or VS Code **E2E Tests**), **and**
  * connection vars are set in the project root ``.env`` (copy from ``.env.template``).

Version gates (by VideoIPath major year):
  * Topology e2e (``apps/test_topology.py``) is skipped when major > 2025.
  * Inspect e2e (``apps/test_inspect.py`` and ``workflows/``) is skipped when major < 2025.

E2e entry points load ``.env`` and enable the suite automatically. E2e runs never collect coverage
(``--no-cov``).

Layout of the suite:
  * ``workflows/`` — general, ordered "build the scenario step by step" suites: the generic
    network-builder (one suite per :mod:`networks` architecture) and the cross-app onboarding pipeline.
  * ``apps/`` — focused per-app suites (inventory, inspect, topology, preferences, profile, security).

Everything the suite writes is namespaced (``E2E-`` label prefix + ``vipat-e2e`` tag) so a shared
local instance is safe. Cleanup is a single session-start sweep that removes every ``E2E-``
artifact left from a prior run; suites intentionally leave their topologies (including the
network-builder architectures) in VideoIPath for manual inspection after the run.
"""

from __future__ import annotations

import os
from itertools import count
from pathlib import Path
from typing import Iterator, Optional

import pytest

from videoipath_automation_tool.apps.inspect.app.app import _parse_version
from videoipath_automation_tool.apps.videoipath_app import VideoIPathApp
from vipat_cli_scripts.project_env import load_project_env

from .helpers import TopologyBuilder, sweep_e2e_namespace

load_project_env()

_STEP_FAILED_KEY = pytest.StashKey[str]()

# TopologyApp is unsupported above this major year; InspectApp is the replacement.
_TOPOLOGY_MAX_MAJOR = 2025
# Inspect e2e requires this major year or newer.
_INSPECT_MIN_MAJOR = 2025


def _e2e_enabled() -> bool:
    return os.environ.get("VIPAT_E2E_ENABLED", "").strip() == "1"


def _server_major(app: VideoIPathApp) -> Optional[int]:
    parsed = _parse_version(app._videoipath_connector.videoipath_version)
    return parsed[0] if parsed is not None else None


@pytest.fixture(scope="session")
def app() -> VideoIPathApp:
    """A live ``VideoIPathApp`` built from the project ``.env``; skips unless E2E is enabled."""
    load_project_env()
    if not _e2e_enabled():
        pytest.skip("E2E disabled (use poetry run test-e2e, poetry run test, or the VS Code E2E launch config).")
    return VideoIPathApp()


@pytest.fixture(autouse=True)
def _gate_topology_and_inspect_e2e(request: pytest.FixtureRequest, app: VideoIPathApp) -> None:
    """Skip Topology/Inspect suites when the live server major year is out of range."""
    path = Path(str(request.path))
    major = _server_major(app)
    if major is None:
        return

    is_topology = path.name == "test_topology.py"
    is_inspect = path.name == "test_inspect.py" or "workflows" in path.parts
    version = app._videoipath_connector.videoipath_version

    if is_topology and major > _TOPOLOGY_MAX_MAJOR:
        pytest.skip(
            f"Topology e2e skipped on VideoIPath {version} (major > {_TOPOLOGY_MAX_MAJOR}). "
            "Use InspectApp (app.inspect) instead."
        )
    if is_inspect and major < _INSPECT_MIN_MAJOR:
        pytest.skip(f"Inspect e2e skipped on VideoIPath {version} (major < {_INSPECT_MIN_MAJOR}).")


@pytest.fixture(scope="session", autouse=True)
def e2e_sweep(app: VideoIPathApp) -> None:
    """Session-start sweep: remove every ``E2E-`` artifact left over from a prior run."""
    sweep_e2e_namespace(app)


@pytest.fixture(scope="session")
def e2e_addresses() -> Iterator[str]:
    """Session-wide device address allocator (private ``10.99.0.0/16`` range), so addresses never collide."""
    return (f"10.99.{i // 256}.{i % 256}" for i in count(1))


@pytest.fixture(scope="session")
def e2e_map_origins() -> Iterator[tuple[int, int]]:
    """Session-wide map-origin allocator so per-test TopologyBuilder instances never stack.

    Laid out in a grid well clear of the workflow network-builder region (y >= 6000).
    Each slot is large enough for a few devices spaced 300 apart horizontally.
    """
    cols, slot_w, slot_h, base_x, base_y = 8, 1200, 800, 0, 2000
    return ((base_x + (i % cols) * slot_w, base_y + (i // cols) * slot_h) for i in count())


@pytest.fixture
def topology_builder(
    app: VideoIPathApp, e2e_addresses: Iterator[str], e2e_map_origins: Iterator[tuple[int, int]]
) -> TopologyBuilder:
    """A per-test topology factory with a unique map origin (session sweep cleans ``E2E-`` artifacts)."""
    x, y = next(e2e_map_origins)
    return TopologyBuilder(app, e2e_addresses, x=x, y=y)


# --- Sequential suite support (``@pytest.mark.incremental``) ---
# Later steps of an ordered suite are skipped (not failed) once an earlier step fails. With the
# default ``-x`` in ``addopts`` the run stops at the first failure anyway; these hooks make the
# behavior sensible without it too (e.g. ``--maxfail=0``). Each test class has its own failure stash,
# so ordered suites (including the per-network builder subclasses) are isolated from one another.


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
        pytest.skip(f"previous step in this suite failed ({failed})")
