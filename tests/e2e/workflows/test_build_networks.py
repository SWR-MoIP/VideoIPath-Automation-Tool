"""Generic ordered network-builder suite: one Test* subclass per architecture.

Each subclass pairs a :class:`~tests.e2e.networks.Network` with a map ``offset``. The base
:class:`NetworkBuildSuite` turns that into a live VideoIPath topology step by step:

  connect → create inventory devices → add to topology → label & tag → connect links → verify

Define a new architecture by adding a ``Network`` in ``tests/e2e/networks.py`` and a three-line
``Test*`` subclass here. Each network builds as its own independent suite at its own map region.

Built networks are left in VideoIPath for manual inspection. The next e2e run's session-start sweep
removes every ``E2E-`` artifact before rebuilding.

Run with::

    poetry run test-e2e
"""

from __future__ import annotations

from typing import Iterator

import pytest

from videoipath_automation_tool.apps.videoipath_app import VideoIPathApp

from ..helpers import E2E_TAG, NetworkBuild, edges_between
from ..networks import Network, build_network

pytestmark = pytest.mark.e2e


# --- Concrete networks -----------------------------------------------------------------------------
# Each is intentionally small and easy to picture; every ``Test*`` subclass in the builder suite
# pairs one of these with a distinct map offset.

LINE = build_network(
    "line",
    devices=[("line-a", 0, 0), ("line-b", 300, 0), ("line-c", 600, 0)],
    links=[("line-a", "line-b"), ("line-b", "line-c")],
)

RING = build_network(
    "ring",
    devices=[("ring-1", 0, 0), ("ring-2", 300, 0), ("ring-3", 300, 300), ("ring-4", 0, 300)],
    links=[("ring-1", "ring-2"), ("ring-2", "ring-3"), ("ring-3", "ring-4"), ("ring-4", "ring-1")],
)

STAR = build_network(
    "star",
    devices=[("hub", 300, 300), ("spoke-1", 0, 0), ("spoke-2", 600, 0), ("spoke-3", 0, 600), ("spoke-4", 600, 600)],
    links=[("hub", "spoke-1"), ("hub", "spoke-2"), ("hub", "spoke-3"), ("hub", "spoke-4")],
)

# 2-tier spine-leaf (Clos): every leaf meshed to every spine; endpoints attach to leaf pairs
# (dual-homed on the first two pairs, single-homed on the third).
SPINE_LEAF_2_TIER = build_network(
    "spine-leaf-2tier",
    devices=[
        ("spine-1", 500, 0),
        ("spine-2", 1100, 0),
        ("leaf-1", 0, 400),
        ("leaf-2", 300, 400),
        ("leaf-3", 600, 400),
        ("leaf-4", 900, 400),
        ("leaf-5", 1200, 400),
        ("leaf-6", 1500, 400),
        ("endpoint-1", 150, 800),
        ("endpoint-2", 750, 800),
        ("endpoint-3", 1200, 800),
        ("endpoint-4", 1500, 800),
    ],
    links=[
        # Full mesh: leaf ↔ spine
        ("leaf-1", "spine-1"),
        ("leaf-1", "spine-2"),
        ("leaf-2", "spine-1"),
        ("leaf-2", "spine-2"),
        ("leaf-3", "spine-1"),
        ("leaf-3", "spine-2"),
        ("leaf-4", "spine-1"),
        ("leaf-4", "spine-2"),
        ("leaf-5", "spine-1"),
        ("leaf-5", "spine-2"),
        ("leaf-6", "spine-1"),
        ("leaf-6", "spine-2"),
        # Endpoints
        ("endpoint-1", "leaf-1"),
        ("endpoint-1", "leaf-2"),
        ("endpoint-2", "leaf-3"),
        ("endpoint-2", "leaf-4"),
        ("endpoint-3", "leaf-5"),
        ("endpoint-4", "leaf-6"),
    ],
)

# Traditional 3-tier: core ↔ aggregation (full mesh) + overlapping aggregation↔access pairs + dual-homed endpoints.
SPINE_LEAF_3_TIER = build_network(
    "spine-leaf-3tier",
    devices=[
        ("core-1", 450, 0),
        ("core-2", 1050, 0),
        ("agg-1", 0, 400),
        ("agg-2", 500, 400),
        ("agg-3", 1000, 400),
        ("agg-4", 1500, 400),
        ("access-1", 0, 800),
        ("access-2", 300, 800),
        ("access-3", 600, 800),
        ("access-4", 900, 800),
        ("access-5", 1200, 800),
        ("access-6", 1500, 800),
        ("endpoint-1", 150, 1200),
        ("endpoint-2", 750, 1200),
        ("endpoint-3", 1350, 1200),
    ],
    links=[
        ("core-1", "core-2"),
        # Full mesh: core ↔ aggregation
        ("core-1", "agg-1"),
        ("core-1", "agg-2"),
        ("core-1", "agg-3"),
        ("core-1", "agg-4"),
        ("core-2", "agg-1"),
        ("core-2", "agg-2"),
        ("core-2", "agg-3"),
        ("core-2", "agg-4"),
        # Overlapping access pairs → aggregation pairs
        ("access-1", "agg-1"),
        ("access-1", "agg-2"),
        ("access-2", "agg-1"),
        ("access-2", "agg-2"),
        ("access-3", "agg-2"),
        ("access-3", "agg-3"),
        ("access-4", "agg-2"),
        ("access-4", "agg-3"),
        ("access-5", "agg-3"),
        ("access-5", "agg-4"),
        ("access-6", "agg-3"),
        ("access-6", "agg-4"),
        # Dual-homed endpoints
        ("endpoint-1", "access-1"),
        ("endpoint-1", "access-2"),
        ("endpoint-2", "access-3"),
        ("endpoint-2", "access-4"),
        ("endpoint-3", "access-5"),
        ("endpoint-3", "access-6"),
    ],
)


@pytest.fixture(scope="class")
def build(request: pytest.FixtureRequest, app: VideoIPathApp, e2e_addresses: Iterator[str]) -> Iterator[NetworkBuild]:
    """Drive a :class:`NetworkBuild` for the requesting suite (no teardown — networks persist)."""
    network: Network = request.cls.network
    offset: tuple[int, int] = request.cls.offset
    yield NetworkBuild(app, network, offset, e2e_addresses)


@pytest.mark.incremental
class NetworkBuildSuite:
    """Base suite — not collected (no ``Test`` prefix). Subclasses set ``network`` and ``offset``."""

    network: Network
    offset: tuple[int, int]

    def test_connect(self, app: VideoIPathApp) -> None:
        app.check_connection()
        assert app.get_server_version()

    def test_create_inventory_devices(self, build: NetworkBuild) -> None:
        build.create_devices()
        assert len(build.device_ids) == len(build.network.devices)

    def test_add_to_topology(self, app: VideoIPathApp, build: NetworkBuild) -> None:
        build.add_to_topology()
        topology_ids = {device.id for device in app.inspect.devices}
        assert set(build.device_ids.values()) <= topology_ids

    def test_label_and_tag(self, app: VideoIPathApp, build: NetworkBuild) -> None:
        build.label_and_tag()
        for spec in build.network.devices:
            device = app.inspect.get_device(build.device_ids[spec.name])
            assert device is not None
            assert device.label == build.label_of(spec.name)
            assert E2E_TAG in device.tags

    def test_connect_links(self, app: VideoIPathApp, build: NetworkBuild) -> None:
        build.connect_links()
        for link in build.network.links:
            id_a = build.device_ids[build.network.devices[link.a].name]
            id_b = build.device_ids[build.network.devices[link.b].name]
            pair_edges = edges_between(app, id_a, id_b)
            assert len(pair_edges) == build.network.parallel_count(link) * 2

    def test_verify_connectivity(self, app: VideoIPathApp, build: NetworkBuild) -> None:
        app.inspect.refresh()
        adjacency = build.network.neighbours()
        for spec in build.network.devices:
            device_id = build.device_ids[spec.name]
            label = build.label_of(spec.name)
            assert (
                app.inventory.find_device_id_by_label(label, label_search_mode="user_defined_label_only") == device_id
            )
            device = app.inspect.get_device(device_id)
            assert device is not None
            expected = {build.label_of(neighbour) for neighbour in adjacency[spec.name]}
            assert {linked.label for linked in device.linked_devices} == expected


class TestLineNetwork(NetworkBuildSuite):
    network = LINE
    offset = (0, 6000)


class TestRingNetwork(NetworkBuildSuite):
    network = RING
    offset = (2000, 6000)


class TestStarNetwork(NetworkBuildSuite):
    network = STAR
    offset = (0, 7000)


class TestSpineLeaf2TierNetwork(NetworkBuildSuite):
    network = SPINE_LEAF_2_TIER
    offset = (0, 8000)


class TestSpineLeaf3TierNetwork(NetworkBuildSuite):
    network = SPINE_LEAF_3_TIER
    offset = (2500, 8000)
