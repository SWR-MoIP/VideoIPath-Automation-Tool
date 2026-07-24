"""InspectApp beta status warning."""

from __future__ import annotations

import logging
import warnings
from types import SimpleNamespace

import pytest

from videoipath_automation_tool.apps.inspect.app.app import InspectApp


def _fake_connector(version: str = "2025.4.9") -> SimpleNamespace:
    return SimpleNamespace(videoipath_version=version)


def test_inspect_app_emits_beta_user_warning() -> None:
    with pytest.warns(UserWarning, match="InspectApp is in beta") as record:
        app = InspectApp(vip_connector=_fake_connector())  # type: ignore[arg-type]
    assert app is not None
    assert len(record) == 1


def test_inspect_app_logs_beta_warning(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("test_inspect_beta_warning")
    with caplog.at_level(logging.WARNING, logger=logger.name), warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        InspectApp(vip_connector=_fake_connector(), logger=logger)  # type: ignore[arg-type]
    assert any("InspectApp is in beta" in message for message in caplog.messages)
