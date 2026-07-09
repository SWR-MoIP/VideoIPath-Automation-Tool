"""Shared pytest configuration for offline unit tests."""

from __future__ import annotations

import pytest

UNIT_TEST_ENV = {
    "VIPAT_ENVIRONMENT": "DEV",
    "VIPAT_VIDEOIPATH_SERVER_ADDRESS": "vip-server.example",
    "VIPAT_VIDEOIPATH_USERNAME": "test-user",
    "VIPAT_VIDEOIPATH_PASSWORD": "test-password",
    "VIPAT_USE_HTTPS": "true",
    "VIPAT_VERIFY_SSL_CERT": "false",
    "VIPAT_LOG_LEVEL": "DEBUG",
}


@pytest.fixture(autouse=True)
def _unit_test_env(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    if request.node.get_closest_marker("e2e"):
        return
    for key, value in UNIT_TEST_ENV.items():
        monkeypatch.setenv(key, value)
