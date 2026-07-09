"""Sequential end-to-end workflow: connect → inventory → inspect topology → edges, step by step.

Each build step of the real user journey is its own test with verification, running in definition
order and sharing state via a class-scoped fixture. Once a step fails, the remaining steps are
skipped (``@pytest.mark.incremental``, see ``conftest.py``).

The suite builds a full dedicated leaf-spine topology (30 devices, 40 bidirectional links —
including two parallel links) that replicates the local VideoIPath instance, with fixed
``E2E-WF-`` labels in its own map region. There is **no teardown**: the built topology persists in
VideoIPath after the run for manual inspection; the next run's session sweep removes it.

Run with::

    poetry run test-e2e
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterator

import pytest
from pydantic import BaseModel

from videoipath_automation_tool.apps.inspect.model.common import InspectFrozenModel
from videoipath_automation_tool.apps.videoipath_app import VideoIPathApp

from .helpers import E2E_TAG, create_mock_device, discover_router_vertices, edges_between

pytestmark = pytest.mark.e2e


class DeviceSpec(InspectFrozenModel):
    name: str
    x: int
    y: int
    ports: int


class LinkSpec(InspectFrozenModel):
    a: int  # device index
    b: int  # device index


# A full leaf-spine in its own map region (all coordinates shifted +3000 in y so the test data
# rather not conflict with other data). Port counts equal each device's link degree; devices with
# no links sit at the region origin. Two device pairs — (2, 15) and (5, 16) — carry parallel links,
# represented here as repeated ``LinkSpec`` entries.
DEVICES = [
    DeviceSpec(name="E2E-WF-DEV-00", x=-2301, y=11141, ports=2),
    DeviceSpec(name="E2E-WF-DEV-01", x=-1496, y=11082, ports=1),
    DeviceSpec(name="E2E-WF-DEV-02", x=2100, y=11800, ports=11),
    DeviceSpec(name="E2E-WF-DEV-03", x=3600, y=11800, ports=4),
    DeviceSpec(name="E2E-WF-DEV-04", x=3000, y=11800, ports=4),
    DeviceSpec(name="E2E-WF-DEV-05", x=1500, y=11800, ports=9),
    DeviceSpec(name="E2E-WF-DEV-06", x=0, y=3000, ports=1),
    DeviceSpec(name="E2E-WF-DEV-07", x=1600, y=12300, ports=2),
    DeviceSpec(name="E2E-WF-DEV-08", x=2000, y=12300, ports=2),
    DeviceSpec(name="E2E-WF-DEV-09", x=1600, y=12050, ports=1),
    DeviceSpec(name="E2E-WF-DEV-10", x=-2000, y=10800, ports=3),
    DeviceSpec(name="E2E-WF-DEV-11", x=0, y=3000, ports=1),
    DeviceSpec(name="E2E-WF-DEV-12", x=1600, y=13300, ports=2),
    DeviceSpec(name="E2E-WF-DEV-13", x=0, y=3000, ports=1),
    DeviceSpec(name="E2E-WF-DEV-14", x=2000, y=12800, ports=2),
    DeviceSpec(name="E2E-WF-DEV-15", x=0, y=11400, ports=7),
    DeviceSpec(name="E2E-WF-DEV-16", x=0, y=10600, ports=7),
    DeviceSpec(name="E2E-WF-DEV-17", x=-1800, y=11600, ports=3),
    DeviceSpec(name="E2E-WF-DEV-18", x=500, y=10850, ports=2),
    DeviceSpec(name="E2E-WF-DEV-19", x=-2800, y=11200, ports=2),
    DeviceSpec(name="E2E-WF-DEV-20", x=3500, y=12300, ports=2),
    DeviceSpec(name="E2E-WF-DEV-21", x=767, y=11434, ports=1),
    DeviceSpec(name="E2E-WF-DEV-22", x=1600, y=12800, ports=2),
    DeviceSpec(name="E2E-WF-DEV-23", x=2000, y=12550, ports=2),
    DeviceSpec(name="E2E-WF-DEV-24", x=1600, y=12550, ports=2),
    DeviceSpec(name="E2E-WF-DEV-25", x=900, y=10850, ports=2),
    DeviceSpec(name="E2E-WF-DEV-26", x=0, y=3000, ports=1),
    DeviceSpec(name="E2E-WF-DEV-27", x=3500, y=12050, ports=2),
    DeviceSpec(name="E2E-WF-DEV-28", x=3100, y=12300, ports=2),
    DeviceSpec(name="E2E-WF-DEV-29", x=1046, y=11159, ports=2),
]
LINKS = [
    LinkSpec(a=0, b=10),
    LinkSpec(a=0, b=17),
    LinkSpec(a=2, b=7),
    LinkSpec(a=2, b=8),
    LinkSpec(a=2, b=9),
    LinkSpec(a=2, b=12),
    LinkSpec(a=2, b=14),
    LinkSpec(a=2, b=15),
    LinkSpec(a=2, b=15),
    LinkSpec(a=2, b=21),
    LinkSpec(a=2, b=22),
    LinkSpec(a=2, b=23),
    LinkSpec(a=2, b=24),
    LinkSpec(a=3, b=15),
    LinkSpec(a=3, b=20),
    LinkSpec(a=3, b=27),
    LinkSpec(a=3, b=28),
    LinkSpec(a=4, b=16),
    LinkSpec(a=4, b=20),
    LinkSpec(a=4, b=27),
    LinkSpec(a=4, b=28),
    LinkSpec(a=5, b=7),
    LinkSpec(a=5, b=8),
    LinkSpec(a=5, b=12),
    LinkSpec(a=5, b=14),
    LinkSpec(a=5, b=16),
    LinkSpec(a=5, b=16),
    LinkSpec(a=5, b=22),
    LinkSpec(a=5, b=23),
    LinkSpec(a=5, b=24),
    LinkSpec(a=10, b=16),
    LinkSpec(a=10, b=19),
    LinkSpec(a=15, b=17),
    LinkSpec(a=15, b=18),
    LinkSpec(a=15, b=25),
    LinkSpec(a=15, b=29),
    LinkSpec(a=16, b=18),
    LinkSpec(a=16, b=25),
    LinkSpec(a=16, b=29),
    LinkSpec(a=17, b=19),
]


class WorkflowState(BaseModel):
    """Mutable state shared across the sequential steps."""

    device_ids: dict[str, str] = {}  # spec name -> VideoIPath device id
    out_vertices: dict[str, list[str]] = {}  # device id -> ordered out-vertex ids
    in_vertices: dict[str, list[str]] = {}  # device id -> ordered in-vertex ids
    edge_id: str | None = None  # representative edge for the update step


@pytest.fixture(scope="class")
def state() -> WorkflowState:
    return WorkflowState()


def _expected_adjacency() -> dict[str, set[str]]:
    """Undirected neighbour set per device name (from the specs)."""
    adjacency: dict[str, set[str]] = {d.name: set() for d in DEVICES}
    for link in LINKS:
        na, nb = DEVICES[link.a].name, DEVICES[link.b].name
        adjacency[na].add(nb)
        adjacency[nb].add(na)
    return adjacency


@pytest.mark.incremental
class TestInventoryToInspectWorkflow:
    def test_connect(self, app: VideoIPathApp) -> None:
        app.check_connection()  # raises ConnectionError on failure
        assert app.get_server_version()

    def test_create_inventory_devices(
        self, app: VideoIPathApp, state: WorkflowState, e2e_addresses: Iterator[str]
    ) -> None:
        for spec in DEVICES:
            state.device_ids[spec.name] = create_mock_device(
                app, label=spec.name, address=next(e2e_addresses), ports=spec.ports
            )
        assert len(state.device_ids) == len(DEVICES)

    def test_verify_inventory(self, app: VideoIPathApp, state: WorkflowState) -> None:
        for spec in DEVICES:
            device_id = state.device_ids[spec.name]
            assert app.inventory.find_device_id_by_label(spec.name) == device_id
            device = app.inventory.get_device(device_id=device_id, config_only=True)
            assert device.configuration.label == spec.name

    def test_add_to_topology(self, app: VideoIPathApp, state: WorkflowState) -> None:
        app.inspect.add_devices_to_topology([(state.device_ids[s.name], s.x, s.y) for s in DEVICES])
        app.inspect.refresh()
        topology_ids = {d.id for d in app.inspect.devices}
        assert set(state.device_ids.values()) <= topology_ids

    def test_configure_labels_and_tags(self, app: VideoIPathApp, state: WorkflowState) -> None:
        with app.inspect.transaction() as tx:
            for spec in DEVICES:
                tx.update_device(state.device_ids[spec.name], label=spec.name, tags=[E2E_TAG])
            tx.commit()
        app.inspect.refresh()
        for spec in DEVICES:
            device = app.inspect.get_device(state.device_ids[spec.name])
            assert device is not None
            assert device.label == spec.name
            assert E2E_TAG in device.tags

    def test_discover_ports(self, app: VideoIPathApp, state: WorkflowState) -> None:
        vertices = discover_router_vertices(app, list(state.device_ids.values()))
        for spec in DEVICES:
            outs, ins = vertices[state.device_ids[spec.name]]
            assert len(outs) == spec.ports
            assert len(ins) == spec.ports
            state.out_vertices[state.device_ids[spec.name]] = outs
            state.in_vertices[state.device_ids[spec.name]] = ins

    def test_connect_edges(self, app: VideoIPathApp, state: WorkflowState) -> None:
        slot: dict[str, int] = defaultdict(int)
        with app.inspect.transaction() as tx:
            for link in LINKS:
                id_a, id_b = state.device_ids[DEVICES[link.a].name], state.device_ids[DEVICES[link.b].name]
                ka, kb = slot[id_a], slot[id_b]
                slot[id_a] += 1
                slot[id_b] += 1
                # Bidirectional link between port slot ka on A and kb on B (two directed edges).
                tx.connect(state.out_vertices[id_a][ka], state.in_vertices[id_b][kb], bidirectional=False)
                tx.connect(state.out_vertices[id_b][kb], state.in_vertices[id_a][ka], bidirectional=False)
            tx.commit()
        app.inspect.refresh()
        for link in LINKS:
            id_a, id_b = state.device_ids[DEVICES[link.a].name], state.device_ids[DEVICES[link.b].name]
            pair_edges = edges_between(app, id_a, id_b)
            # Two directed edges per bidirectional link; a pair with parallel links has more.
            parallel = sum(1 for other in LINKS if {other.a, other.b} == {link.a, link.b})
            assert len(pair_edges) == parallel * 2
        state.edge_id = pair_edges[0].id

    def test_update_edge_weight(self, app: VideoIPathApp, state: WorkflowState) -> None:
        assert state.edge_id is not None
        result = app.inspect.update_edge(state.edge_id, weight=7)
        assert result.ok
        # Survives the targeted post-commit refresh without a full reload.
        assert any(e.id == state.edge_id for e in app.inspect.edges)

    def test_verify_connectivity_and_persistence(self, app: VideoIPathApp, state: WorkflowState) -> None:
        # A fresh read of the final state: labels, adjacency, and edge count all match the specs.
        # There is no teardown — this persisted topology remains in VideoIPath after the run.
        app.inspect.refresh()
        labels = {d.label for d in app.inspect.devices}
        assert all(spec.name in labels for spec in DEVICES)
        adjacency = _expected_adjacency()
        for spec in DEVICES:
            device = app.inspect.get_device(state.device_ids[spec.name])
            assert device is not None
            assert {d.label for d in device.linked_devices} == adjacency[spec.name]
        known = set(state.device_ids.values())
        workflow_edges = [
            e
            for e in app.inspect.edges
            if (e.from_device and e.from_device.id in known) or (e.to_device and e.to_device.id in known)
        ]
        assert len(workflow_edges) == len(LINKS) * 2
