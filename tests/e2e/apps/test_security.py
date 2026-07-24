"""Focused Security app suite: domain create + device membership assign/clear.

Mirrors ``docs/examples/05_administration/01_security_domains_and_memberships.py``. Uses a
``topology_builder`` device so memberships attach to a real inventory id. ``E2E-`` domains and
devices persist until the next e2e session-start sweep.

Run with::

    poetry run test-e2e
"""

from __future__ import annotations

import pytest

from videoipath_automation_tool.apps.videoipath_app import VideoIPathApp

from ..helpers import TopologyBuilder, unique_name

pytestmark = pytest.mark.e2e


def test_domain_and_membership_lifecycle(app: VideoIPathApp, topology_builder: TopologyBuilder) -> None:
    (device_id,) = topology_builder.add_devices([("SEC-A", 2)])
    domain_name = unique_name("domain")
    domain = app.security.domains.create_domain(name=domain_name, description="E2E security domain")
    assert domain.name == domain_name
    assert domain_name in app.security.domains.list_domain_names()

    memberships = app.security.resources.get_device_memberships(device_id=device_id)
    memberships.domains = app.security.resources.convert_domain_names_to_ids([domain_name])
    app.security.resources.update_memberships(memberships=memberships)

    memberships = app.security.resources.get_device_memberships(device_id=device_id)
    names = set(app.security.resources.convert_domain_ids_to_names(memberships.domains))
    assert domain_name in names

    memberships = app.security.resources.get_device_memberships(device_id=device_id)
    memberships.domains = []
    app.security.resources.update_memberships(memberships=memberships)
    memberships = app.security.resources.get_device_memberships(device_id=device_id)
    assert memberships.domains == []
