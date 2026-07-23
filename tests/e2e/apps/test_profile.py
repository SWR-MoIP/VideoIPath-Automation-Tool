"""Focused Profile app suite: create and clone an ``E2E-`` profile.

Mirrors ``docs/examples/05_administration/02_profiles.py``. Profiles are left in place; the next e2e
session-start sweep removes ``E2E-`` profiles.

Run with::

    poetry run test-e2e
"""

from __future__ import annotations

import pytest

from videoipath_automation_tool.apps.videoipath_app import VideoIPathApp

from ..helpers import unique_name

pytestmark = pytest.mark.e2e


def test_profile_create_and_clone(app: VideoIPathApp) -> None:
    names_before = app.profile.list_profile_names() or []
    assert isinstance(names_before, list)

    profile_name = unique_name("profile")
    created = app.profile.create_profile(name=profile_name)
    created = app.profile.add_profile(created)
    names = app.profile.list_profile_names() or []
    assert profile_name in names

    fetched = app.profile.get_profile_by_name(profile_name)
    assert fetched is not None
    source = fetched[0] if isinstance(fetched, list) else fetched

    clone = app.profile.clone_profile(source)
    clone = app.profile.add_profile(clone)
    assert clone.name.endswith("(clone)")
    clone_names = app.profile.list_profile_names() or []
    assert clone.name in clone_names
