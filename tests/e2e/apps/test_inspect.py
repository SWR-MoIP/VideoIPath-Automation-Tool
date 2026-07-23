"""Focused Inspect app suite: read/write capabilities against a live instance.

Every test builds its **own** minimal topology (1–3 mock devices) via the ``topology_builder``
fixture — unique labels/addresses per test. Assertions are scoped to the test's own device ids so
other suites on a shared instance never interfere. ``E2E-`` artifacts persist until the next e2e
session-start sweep.

Run with::

    poetry run test-e2e
"""

from __future__ import annotations

import pytest

from videoipath_automation_tool.apps.inspect import VirtualDeviceSpec
from videoipath_automation_tool.apps.inspect.errors import InspectCommitConflictError, InspectCommitError
from videoipath_automation_tool.apps.videoipath_app import VideoIPathApp

from ..helpers import (
    E2E_TAG,
    MODULE_TEST_TAG_ID,
    TEST_TAG_ID,
    FetchSpy,
    TopologyBuilder,
    create_module_test_tag,
    create_test_tag,
    edges_between,
    router_ports,
    unique_label,
)

pytestmark = pytest.mark.e2e


def test_skeleton_read_no_hydration(app: VideoIPathApp, topology_builder: TopologyBuilder) -> None:
    id_a, id_b = topology_builder.add_devices([("SKEL-A", 2), ("SKEL-B", 2)])
    topology_builder.link(id_a, id_b)
    app.inspect.refresh()
    with FetchSpy(app.inspect._inspect_api) as spy:
        assert len(edges_between(app, id_a, id_b)) == 2
    assert spy.count == 0


def test_lazy_hydration(app: VideoIPathApp, topology_builder: TopologyBuilder) -> None:
    id_a, id_b = topology_builder.add_devices([("HYD-A", 2), ("HYD-B", 2)])
    app.inspect.refresh()
    assert not app.inspect.is_device_hydrated(id_a)
    with FetchSpy(app.inspect._inspect_api) as spy:
        ports = app.inspect.get_device(id_a).ports
        assert spy.count == 1
        _ = app.inspect.get_device(id_a).ports
        assert spy.count == 1
    assert len(ports) > 0
    assert app.inspect.is_device_hydrated(id_a)
    assert not app.inspect.is_device_hydrated(id_b)


def test_connectivity_graph(app: VideoIPathApp, topology_builder: TopologyBuilder) -> None:
    hub, id_b, id_c = topology_builder.add_devices([("HUB-A", 2), ("HUB-B", 2), ("HUB-C", 2)])
    topology_builder.link(hub, id_b)
    topology_builder.link(hub, id_c)
    app.inspect.refresh()
    linked = {device.label for device in app.inspect.get_device(hub).linked_devices}
    assert linked == {topology_builder.labels[id_b], topology_builder.labels[id_c]}


def test_edge_pair_refresh(app: VideoIPathApp, topology_builder: TopologyBuilder) -> None:
    id_a, id_b = topology_builder.add_devices([("EDGE-A", 2), ("EDGE-B", 2)])
    topology_builder.link(id_a, id_b)
    app.inspect.refresh()
    edge_id = edges_between(app, id_a, id_b)[0].id
    result = app.inspect.update_edge(edge_id, weight=7)
    assert result.ok
    assert any(edge.id == edge_id for edge in app.inspect.edges)


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
    app.inspect.refresh()
    assert any(edge.id == edge_id for edge in app.inspect.edges)


def test_conflict_detection(app: VideoIPathApp, topology_builder: TopologyBuilder) -> None:
    id_a, id_b = topology_builder.add_devices([("CONF-A", 2), ("CONF-B", 2)])
    topology_builder.link(id_a, id_b)
    app.inspect.refresh()
    edge_id = edges_between(app, id_a, id_b)[0].id
    tx = app.inspect.transaction()
    tx.update_edge(edge_id, weight=21)
    other = VideoIPathApp()
    other.inspect.update_edge(edge_id, weight=9)
    with pytest.raises(InspectCommitConflictError) as exc:
        tx.commit()
    assert any(conflict.entity_id == edge_id for conflict in exc.value.conflicts)
    tx.rebase()
    tx.commit()


def test_assign_tag_to_port(app: VideoIPathApp, topology_builder: TopologyBuilder) -> None:
    (device_id,) = topology_builder.add_devices([("TAG-A", 2)])
    create_test_tag(app)
    app.inspect.refresh()
    device = app.inspect.get_device(device_id)
    assert device is not None
    _out, in_vertex = router_ports(device)[0]
    result = app.inspect.update_vertex(in_vertex, tags=[TEST_TAG_ID])
    assert result.ok
    app.inspect.refresh()
    port = next(
        port
        for port in app.inspect.get_device(device_id).ports
        if port.vertex_in is not None and port.vertex_in.id == in_vertex
    )
    assert TEST_TAG_ID in port.tags


def test_assign_and_unassign_module_tag(app: VideoIPathApp, topology_builder: TopologyBuilder) -> None:
    (device_id,) = topology_builder.add_devices([("MOD-TAG-A", 2)])
    create_module_test_tag(app)
    app.inspect.refresh()
    device = app.inspect.get_device(device_id)
    assert device is not None
    assert device.modules
    module = device.modules[0]
    module_id = module.id

    module.tags = [MODULE_TEST_TAG_ID]
    result = app.inspect.update(module)
    assert result.ok

    app.inspect.refresh()
    module = app.inspect.get_device(device_id).get_module(module_id)
    assert module is not None
    assert MODULE_TEST_TAG_ID in module.tags

    module.tags = []
    result = app.inspect.update(module)
    assert result.ok

    app.inspect.refresh()
    module = app.inspect.get_device(device_id).get_module(module_id)
    assert module is not None
    assert MODULE_TEST_TAG_ID not in module.tags


def test_update_vertex_fields(app: VideoIPathApp, topology_builder: TopologyBuilder) -> None:
    (device_id,) = topology_builder.add_devices([("VTX-A", 2)])
    app.inspect.refresh()
    device = app.inspect.get_device(device_id)
    assert device is not None
    _out, vertex_id = router_ports(device)[0]
    alert_filter = "0:*:e2e-alarm:*"
    result = app.inspect.update_vertex(
        vertex_id,
        label="E2E Router In",
        description="E2E vertex description",
        use_as_endpoint=True,
        active=True,
        sips_mode="SIPSAuto",
        control_props={"configPriority": "high", "onlyInitial": True},
        extra_alert_filters=[alert_filter],
        custom={"e2e-param": "e2e-value"},
        park_port=7,
    )
    assert result.ok

    app.inspect.refresh()
    port = next(
        port
        for port in app.inspect.get_device(device_id).ports
        if port.vertex_in is not None and port.vertex_in.id == vertex_id
    )
    vertex = port.vertex_in
    assert vertex is not None
    assert vertex.label == "E2E Router In"
    assert vertex.description == "E2E vertex description"
    assert vertex.use_as_endpoint is True
    assert vertex.active is True
    assert vertex.sips_mode == "SIPSAuto"
    assert vertex.control_props is not None
    assert vertex.control_props.configPriority == "high"
    assert vertex.control_props.onlyInitial is True
    assert alert_filter in vertex.extra_alert_filters
    assert vertex.custom.get("e2e-param") == "e2e-value"
    assert vertex.park_port == 7
    assert vertex.vertex_kind == "router"
    assert vertex.type_fields is not None and vertex.type_fields.type == "router"


def test_device_placement(app: VideoIPathApp, topology_builder: TopologyBuilder) -> None:
    (device_id,) = topology_builder.add_devices([("PLACE-A", 2)])
    x, y = topology_builder.origin[0] + 150, topology_builder.origin[1] + 150
    app.inspect.place_device(device_id, x, y)
    app.inspect.refresh()
    coords = app.inspect.get_device(device_id).coordinates
    assert coords is not None and coords["x"] == x and coords["y"] == y


def test_disconnect_reconnect_cycle(app: VideoIPathApp, topology_builder: TopologyBuilder) -> None:
    id_a, id_b = topology_builder.add_devices([("CYC-A", 2), ("CYC-B", 2)])
    topology_builder.link(id_a, id_b)
    app.inspect.refresh()
    directed = [tuple(edge.id.split("::", 1)) for edge in edges_between(app, id_a, id_b)]
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
                frozenset(device.label for device in app.inspect.get_device(device_id).linked_devices),
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
        app.inspect.refresh(load="skeleton")


def test_create_virtual_device(app: VideoIPathApp, e2e_map_origins) -> None:
    templates = app.inspect.list_port_templates()
    if not templates:
        pytest.skip("No port templates available on this server.")
    by_id = {template.id: template for template in templates}
    # Prefer a known pair from the docs example; otherwise pick any two templates.
    if "ip_in" in by_id and "ip_out" in by_id:
        spec = VirtualDeviceSpec.from_ports(("ip_in", 1), ("ip_out", 1))
    else:
        first = templates[0]
        second = templates[1] if len(templates) > 1 else templates[0]
        spec = VirtualDeviceSpec.from_ports((first.id, 1), (second.id, 1))

    device = app.inspect.create_virtual_device(spec)
    assert device.is_virtual is True
    label = unique_label("VIRTUAL")
    device.label = label
    device.tags = [E2E_TAG, "virtual"]
    app.inspect.update(device)
    x, y = next(e2e_map_origins)
    app.inspect.place_device(device.id, x=x, y=y)
    app.inspect.refresh()
    loaded = app.inspect.get_device(device.id)
    assert loaded is not None
    assert loaded.label == label
    assert loaded.coordinates is not None
    assert loaded.coordinates["x"] == x and loaded.coordinates["y"] == y
