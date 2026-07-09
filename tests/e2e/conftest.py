"""Gating and shared fixtures for the developer-run live-server E2E suite ([ADR-0005]).

These tests are excluded by default (``-m "not e2e"`` in ``pyproject.toml``) and only run when:
  * you pass ``-m e2e`` on the command line, **and**
  * ``VIPAT_E2E_ENABLED=1`` is set (put it in ``tests/.env.test`` next to the connection vars), **and**
  * the target server is a verified version (>= 2025.4).

Everything the suite writes is namespaced (``E2E-`` label prefix + ``vipat-e2e`` tag) so a shared
local instance is safe: the scenario teardown removes only that namespace.
"""

from __future__ import annotations

import os

import pytest

from videoipath_automation_tool.apps.inspect.inspect_app import _MIN_VERIFIED_VERSION, _parse_version
from videoipath_automation_tool.apps.videoipath_app import VideoIPathApp


def _e2e_enabled() -> bool:
    return os.environ.get("VIPAT_E2E_ENABLED", "").strip() == "1"


@pytest.fixture(scope="session")
def app() -> VideoIPathApp:
    """A live ``VideoIPathApp`` built from ``tests/.env.test``; skips unless E2E is enabled + verified."""
    if not _e2e_enabled():
        pytest.skip("E2E disabled (set VIPAT_E2E_ENABLED=1 in tests/.env.test to run).")
    application = VideoIPathApp()
    version = application._videoipath_connector.videoipath_version
    parsed = _parse_version(version)
    if parsed is None or parsed < _MIN_VERIFIED_VERSION:
        pytest.skip(
            f"Server version '{version}' is below the verified Inspect baseline "
            f"{_MIN_VERIFIED_VERSION[0]}.{_MIN_VERIFIED_VERSION[1]}."
        )
    return application
