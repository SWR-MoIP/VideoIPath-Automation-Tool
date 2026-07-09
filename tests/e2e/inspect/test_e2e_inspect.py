"""Independent Inspect capability tests against a live instance.

Every test builds its **own** minimal topology (1–3 mock devices) via the ``topology_builder``
fixture — unique labels/addresses per test, guaranteed teardown (edges → topology node → inventory
entry) even on failure. All assertions are scoped to the test's own device ids, so the persisted
workflow topology or any other state on a shared instance never interferes.

Developer-run only (see ``tests/e2e/conftest.py``). Run with::

    poetry run test-e2e
"""

from __future__ import annotations

import pytest

from videoipath_automation_tool.apps.inspect.errors import InspectCommitConflictError, InspectCommitError
from videoipath_automation_tool.apps.videoipath_app import VideoIPathApp

from ..helpers import TEST_TAG_ID, FetchSpy, TopologyBuilder, create_test_tag, delete_test_tag, edges_between


pytestmark = pytest.mark.e2e


def test_skeleton_read_no_hydration(app: VideoIPathApp, topology_builder: TopologyBuilder) -> None:
    id_a, id_b = topology_builder.add_devices([("SKEL-A", 2), ("SKEL-B", 2)])
    topology_builder.link(id_a, id_b)
    app.inspect.refresh()
    with FetchSpy(app.inspect._inspect_api) as spy:
        assert len(edges_between(app, id_a, id_b)) == 2
    assert spy.count == 0  # skeleton read triggers no per-device hydration


def test_lazy_hydration(app: VideoIPathApp, topology_builder: TopologyBuilder) -> None:
    id_a, id_b = topology_builder.add_devices([("HYD-A", 2), ("HYD-B", 2)])
    app.inspect.refresh()
    assert not app.inspect.is_device_hydrated(id_a)
    with FetchSpy(app.inspect._inspect_api) as spy:
        ports = app.inspect.get_device(id_a).ports  # one detail fetch
        assert spy.count == 1
        _ = app.inspect.get_device(id_a).ports  # cached
        assert spy.count == 1
    assert len(ports) > 0  # mock devices expose router ports
    assert app.inspect.is_device_hydrated(id_a)
    assert not app.inspect.is_device_hydrated(id_b)


def test_connectivity_graph(app: VideoIPathApp, topology_builder: TopologyBuilder) -> None:
    hub, id_b, id_c = topology_builder.add_devices([("HUB-A", 2), ("HUB-B", 2), ("HUB-C", 2)])
    topology_builder.link(hub, id_b)
    topology_builder.link(hub, id_c)
    app.inspect.refresh()
    linked = {d.label for d in app.inspect.get_device(hub).linked_devices}
    assert linked == {topology_builder.labels[id_b], topology_builder.labels[id_c]}


def test_edge_pair_refresh(app: VideoIPathApp, topology_builder: TopologyBuilder) -> None:
    id_a, id_b = topology_builder.add_devices([("EDGE-A", 2), ("EDGE-B", 2)])
    topology_builder.link(id_a, id_b)
    app.inspect.refresh()
    edge_id = edges_between(app, id_a, id_b)[0].id
    result = app.inspect.update_edge(edge_id, weight=7)
    assert result.ok
    # Survives the targeted post-commit refresh without a full reload.
    assert any(e.id == edge_id for e in app.inspect.edges)


def test_transaction_atomicity(app: VideoIPathApp, topology_builder: TopologyBuilder) -> None:
    id_a, id_b = topology_builder.add_devices([("ATOM-A", 2), ("ATOM-B", 2)])
    topology_builder.link(id_a, id_b)
    app.inspect.refresh()
    edge_id = edges_between(app, id_a, id_b)[0].id
    with pytest.raises(InspectCommitError):
        with app.inspect.transaction() as tx:
            tx.update_edge(edge_id, weight=13)
            tx.remove("does-not-exist::also-not-real")
            tx.commit()
    # Nothing applied: the edge is still present.
    app.inspect.refresh()
    assert any(e.id == edge_id for e in app.inspect.edges)


def test_conflict_detection(app: VideoIPathApp, topology_builder: TopologyBuilder) -> None:
    id_a, id_b = topology_builder.add_devices([("CONF-A", 2), ("CONF-B", 2)])
    topology_builder.link(id_a, id_b)
    app.inspect.refresh()
    edge_id = edges_between(app, id_a, id_b)[0].id
    tx = app.inspect.transaction()
    tx.update_edge(edge_id, weight=21)
    # Out-of-band change via a second app instance.
    other = VideoIPathApp()
    other.inspect.update_edge(edge_id, weight=9)
    with pytest.raises(InspectCommitConflictError) as exc:
        tx.commit()
    assert any(c.entity_id == edge_id for c in exc.value.conflicts)
    tx.rebase()
    tx.commit()


def test_assign_tag_to_port(app: VideoIPathApp, topology_builder: TopologyBuilder) -> None:
    # Inspect-only capability: assign a catalog tag to a port.
    (device_id,) = topology_builder.add_devices([("TAG-A", 2)])
    create_test_tag(app)
    try:
        app.inspect.refresh()
        vertex_id = next(
            p.vertex_id
            for p in app.inspect.get_device(device_id).ports
            if p.vertex_id and "Router In" in (p.label or "")
        )
        result = app.inspect.update_vertex(vertex_id, tags=[TEST_TAG_ID])
        assert result.ok
        app.inspect.refresh()
        port = next(p for p in app.inspect.get_device(device_id).ports if p.vertex_id == vertex_id)
        assert TEST_TAG_ID in port.tags
    finally:
        delete_test_tag(app)  # also removes the port binding


def test_device_placement(app: VideoIPathApp, topology_builder: TopologyBuilder) -> None:
    (device_id,) = topology_builder.add_devices([("PLACE-A", 2)])
    app.inspect.place_device(device_id, 4200, 4200)
    app.inspect.refresh()
    coords = app.inspect.get_device(device_id).coordinates
    assert coords is not None and coords["x"] == 4200 and coords["y"] == 4200


def test_disconnect_reconnect_cycle(app: VideoIPathApp, topology_builder: TopologyBuilder) -> None:
    id_a, id_b = topology_builder.add_devices([("CYC-A", 2), ("CYC-B", 2)])
    topology_builder.link(id_a, id_b)
    app.inspect.refresh()
    directed = [tuple(e.id.split("::", 1)) for e in edges_between(app, id_a, id_b)]
    assert directed
    for from_vertex, to_vertex in directed:
        app.inspect.disconnect(from_vertex, to_vertex, bidirectional=False)
    app.inspect.refresh()
    assert not edges_between(app, id_a, id_b)
    for from_vertex, to_vertex in directed:
        app.inspect.connect(from_vertex, to_vertex, bidirectional=False)
    app.inspect.refresh()
    assert len(edges_between(app, id_a, id_b)) == len(directed)


def test_full_vs_skeleton_equivalence(app: VideoIPathApp, topology_builder: TopologyBuilder) -> None:
    id_a, id_b, id_c = topology_builder.add_devices([("EQ-A", 2), ("EQ-B", 2), ("EQ-C", 2)])
    topology_builder.link(id_a, id_b)
    topology_builder.link(id_b, id_c)

    def graph_view() -> dict[str, tuple[str | None, frozenset[str | None]]]:
        return {
            device_id: (
                app.inspect.get_device(device_id).label,
                frozenset(d.label for d in app.inspect.get_device(device_id).linked_devices),
            )
            for device_id in (id_a, id_b, id_c)
        }

    try:
        app.inspect.refresh(load="skeleton")
        app.inspect.preload([id_a, id_b, id_c])
        skeleton = graph_view()
        app.inspect.refresh(load="full")
        full = graph_view()
        assert skeleton == full
    finally:
        app.inspect.refresh(load="skeleton")  # restore default load mode
