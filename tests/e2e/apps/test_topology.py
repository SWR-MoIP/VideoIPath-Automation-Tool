"""Focused Topology app suite (legacy path), skipped on VideoIPath 2026.x+.

Builds a device via Inspect (``topology_builder``), then exercises the classic Topology API:
``get_device``, ``find_device_id_by_label``, and a label / position round-trip. TopologyApp is
deprecated on 2025.x and raises ``TopologyUnsupportedError`` on 2026.x — prefer Inspect elsewhere.

Run with::

    poetry run test-e2e
"""

from __future__ import annotations

import pytest

from videoipath_automation_tool.apps.topology.errors import TopologyUnsupportedError
from videoipath_automation_tool.apps.topology.topology_app import TopologyApp
from videoipath_automation_tool.apps.videoipath_app import VideoIPathApp

from ..helpers import TopologyBuilder

pytestmark = pytest.mark.e2e


@pytest.fixture
def topology(app: VideoIPathApp) -> TopologyApp:
    try:
        return app.topology
    except TopologyUnsupportedError as exc:
        pytest.skip(str(exc))


def test_get_device_and_find_by_label(
    app: VideoIPathApp, topology: TopologyApp, topology_builder: TopologyBuilder
) -> None:
    (device_id,) = topology_builder.add_devices([("TOPO-A", 2)])
    label = topology_builder.labels[device_id]
    device = topology.get_device(device_id)
    assert device.configuration.base_device.id == device_id
    found = topology.find_device_id_by_label(label, label_search_mode="user_defined_label_only")
    assert found == device_id


def test_update_label_and_position(
    app: VideoIPathApp, topology: TopologyApp, topology_builder: TopologyBuilder
) -> None:
    (device_id,) = topology_builder.add_devices([("TOPO-B", 2)])
    device = topology.get_device(device_id)
    new_label = topology_builder.labels[device_id] + "-MOVED"
    x, y = topology_builder.origin[0] + 150, topology_builder.origin[1] + 150
    device.configuration.label = new_label
    device.configuration.position_x = x
    device.configuration.position_y = y
    updated = topology.update_device(device)
    assert updated.configuration.label == new_label
    assert updated.configuration.position_x == x
    assert updated.configuration.position_y == y

    app.inspect.refresh()
    inspect_device = app.inspect.get_device(device_id)
    assert inspect_device is not None
    assert inspect_device.label == new_label
    assert inspect_device.coordinates is not None
    assert inspect_device.coordinates["x"] == x
    assert inspect_device.coordinates["y"] == y
