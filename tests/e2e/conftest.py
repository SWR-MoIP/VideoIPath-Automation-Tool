"""Gating and shared fixtures for the developer-run live-server E2E suite ([ADR-0005]).

These tests are excluded by default (``-m "not e2e"`` in ``pyproject.toml``) and only run when:
  * you invoke an e2e entry point (``poetry run test-e2e``, ``poetry run test``, or VS Code **E2E Tests**), **and**
  * connection vars are set in the project root ``.env`` (copy from ``.env.template``), **and**
  * the target server is a verified version (>= 2025.4).

E2e entry points load ``.env`` and enable the suite automatically. E2e runs never collect coverage
(``--no-cov``).

Everything the suite writes is namespaced (``E2E-`` label prefix + ``vipat-e2e`` tag) so a shared
local instance is safe: the scenario teardown removes only that namespace.
"""

from __future__ import annotations

import os

import pytest

from videoipath_automation_tool.apps.inspect.inspect_app import _MIN_VERIFIED_VERSION, _parse_version
from videoipath_automation_tool.apps.videoipath_app import VideoIPathApp
from vipat_cli_scripts.project_env import load_project_env

load_project_env()


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
