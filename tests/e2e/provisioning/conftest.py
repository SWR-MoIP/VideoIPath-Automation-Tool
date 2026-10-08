"""Provisioning scenarios share the standard E2E session gate, allocators, and cleanup."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ..helpers import create_e2e_tag, create_module_test_tag, module_test_tag_id
from .helpers import LiveProvisioning

if TYPE_CHECKING:
    from collections.abc import Iterator

    from videoipath_automation_tool.apps.videoipath_app import VideoIPathApp


@pytest.fixture
def live(
    app: VideoIPathApp, e2e_addresses: Iterator[str], e2e_map_origins: Iterator[tuple[int, int]], provisioning_tag: str
) -> LiveProvisioning:
    return LiveProvisioning(app, e2e_addresses, next(e2e_map_origins), provisioning_tag)


@pytest.fixture(scope="session")
def provisioning_tag(app: VideoIPathApp, e2e_sweep: None) -> str:
    return create_e2e_tag(app)


@pytest.fixture
def catalog_tag(app: VideoIPathApp) -> str:
    create_module_test_tag(app)
    return module_test_tag_id(app)
