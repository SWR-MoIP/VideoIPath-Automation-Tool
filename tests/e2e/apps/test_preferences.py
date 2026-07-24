"""Focused Preferences app suite: system info reads + multicast pool lifecycle.

Mirrors ``docs/examples/05_administration/03_multicast_pools.py``. The multicast pool uses a unique
``E2E-`` name and is left in place; the next e2e session-start sweep removes it.

Run with::

    poetry run test-e2e
"""

from __future__ import annotations

import pytest

from videoipath_automation_tool.apps.videoipath_app import VideoIPathApp

from ..helpers import unique_name

pytestmark = pytest.mark.e2e


def test_read_system_network_info(app: VideoIPathApp) -> None:
    network = app.preferences.system_configuration.network
    hostname = network.get_hostname()
    assert isinstance(hostname, str) and hostname
    interfaces = network.get_all_interfaces()
    assert isinstance(interfaces, list)
    dns_servers = network.get_dns_servers()
    assert isinstance(dns_servers, list)


def test_multicast_pool_lifecycle(app: VideoIPathApp) -> None:
    pools = app.preferences.system_configuration.allocation_pools
    existing = pools.get_multicast_ranges()
    assert isinstance(existing.available_ranges, list)

    pool_name = unique_name("pool")
    staged = pools.create_multicast_range(name=pool_name, start_ip="239.99.0.0", end_ip="239.99.0.255")
    pools.add_multicast_range(staged)
    assert pool_name in pools.get_multicast_ranges().available_ranges

    pool = pools.get_multicast_range_by_name(pool_name)
    pool.add_ip_range(start_ip="239.99.1.0", end_ip="239.99.1.255")
    pools.update_multicast_range(pool)
    refreshed = pools.get_multicast_range_by_name(pool_name)
    assert len(refreshed.ranges) == 2
