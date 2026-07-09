"""End-to-end Inspect tests against a live instance, replicating the local topology.

Developer-run only (see ``tests/e2e/conftest.py``). A session-scoped fixture cleans up any prior
E2E state **at startup** and then builds the topology with virtual (mock-driver) devices via the
inventory → inspect flow. There is **no teardown**: the built topology persists in VideoIPath after
the run (the next run cleans it up and rebuilds). Mutating tests revert their own changes, so the
persisted end state is the complete topology.

Everything goes through ``app.inventory`` (device creation) and ``app.inspect`` (topology). The
topology app is never used.

Run with::

    poetry run pytest -m e2e tests/e2e/inspect
"""

from __future__ import annotations

import pytest

from videoipath_automation_tool.apps.inspect.errors import InspectCommitConflictError, InspectCommitError
from videoipath_automation_tool.apps.videoipath_app import VideoIPathApp

from .scenario import LeafSpineScenario


pytestmark = pytest.mark.e2e


@pytest.fixture(scope="session")
def scenario(app: VideoIPathApp):
    scn = LeafSpineScenario()
    scn.cleanup(app)  # startup cleanup only — no teardown, state persists after the run
    scn.build(app)
    return scn


class _FetchSpy:
    """Wraps get_device_detail to count hydration fetches."""

    def __init__(self, api):
        self._api = api
        self._orig = api.get_device_detail
        self.count = 0

    def __enter__(self):
        def counting(device_id):
            self.count += 1
            return self._orig(device_id)

        self._api.get_device_detail = counting
        return self

    def __exit__(self, *exc):
        self._api.get_device_detail = self._orig


def _edges_between(app, id_a: str, id_b: str):
    return [
        e
        for e in app.inspect.edges
        if e.from_device and e.to_device and {e.from_device.id, e.to_device.id} == {id_a, id_b}
    ]


def _busiest_device(scenario) -> str:
    adjacency = scenario.adjacency()
    return max(scenario.device_names, key=lambda n: len(adjacency[n]))


def test_all_devices_present(app, scenario):
    app.inspect.refresh()
    labels = {d.label for d in app.inspect.devices}
    for name in scenario.device_names:
        assert name in labels


def test_skeleton_read_no_hydration(app, scenario):
    app.inspect.refresh()
    with _FetchSpy(app.inspect._inspect_api) as spy:
        known = set(scenario.device_ids.values())
        scenario_edges = [
            e
            for e in app.inspect.edges
            if (e.from_device and e.from_device.id in known) or (e.to_device and e.to_device.id in known)
        ]
        assert len(scenario_edges) == scenario.expected_edge_count()
    assert spy.count == 0  # skeleton read triggers no per-device hydration


def test_lazy_hydration(app, scenario):
    app.inspect.refresh()
    name = _busiest_device(scenario)
    device_id = scenario.device_id(name)
    other_id = scenario.device_id(next(n for n in scenario.device_names if n != name))
    assert not app.inspect.is_device_hydrated(device_id)
    with _FetchSpy(app.inspect._inspect_api) as spy:
        ports = app.inspect.get_device(device_id).ports  # one detail fetch
        assert spy.count == 1
        _ = app.inspect.get_device(device_id).ports  # cached
        assert spy.count == 1
    assert len(ports) > 0  # mock devices expose router ports
    assert app.inspect.is_device_hydrated(device_id)
    assert not app.inspect.is_device_hydrated(other_id)


def test_connectivity_graph(app, scenario):
    app.inspect.refresh()
    adjacency = scenario.adjacency()
    name = _busiest_device(scenario)
    device = app.inspect.get_device(scenario.device_id(name))
    linked = {d.label for d in device.linked_devices}
    assert linked == adjacency[name]


def test_edge_pair_refresh(app, scenario):
    app.inspect.refresh()
    name_a, name_b = scenario.a_link()
    id_a, id_b = scenario.device_id(name_a), scenario.device_id(name_b)
    edges = _edges_between(app, id_a, id_b)
    assert edges
    edge_id = edges[0].id
    result = app.inspect.update_edge(edge_id, weight=7)
    assert result.ok
    # Survives the targeted post-commit refresh without a full reload.
    assert any(e.id == edge_id for e in app.inspect.edges)
    app.inspect.update_edge(edge_id, weight=1)  # revert


def test_transaction_atomicity(app, scenario):
    name_a, name_b = scenario.a_link()
    id_a, id_b = scenario.device_id(name_a), scenario.device_id(name_b)
    app.inspect.refresh()
    edge_id = _edges_between(app, id_a, id_b)[0].id
    with pytest.raises(InspectCommitError):
        with app.inspect.transaction() as tx:
            tx.update_edge(edge_id, weight=13)
            tx.remove("does-not-exist::also-not-real")
            tx.commit()
    # Nothing applied: the edge is still present.
    app.inspect.refresh()
    assert any(e.id == edge_id for e in app.inspect.edges)


def test_conflict_detection(app, scenario):
    app.inspect.refresh()
    name_a, name_b = scenario.a_link()
    id_a, id_b = scenario.device_id(name_a), scenario.device_id(name_b)
    edge_id = _edges_between(app, id_a, id_b)[0].id
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
    app.inspect.update_edge(edge_id, weight=1)  # revert


def test_device_placement_roundtrip(app, scenario):
    name = scenario.device_names[0]
    spec = next(s for s in scenario.devices if s.name == name)
    device_id = scenario.device_id(name)
    app.inspect.place_device(device_id, 4200, 4200)
    app.inspect.refresh()
    coords = app.inspect.get_device(device_id).coordinates
    assert coords is not None and coords["x"] == 4200 and coords["y"] == 4200
    app.inspect.place_device(device_id, spec.x, spec.y)  # revert


def test_disconnect_reconnect_cycle(app, scenario):
    app.inspect.refresh()
    name_a, name_b = scenario.a_link()
    id_a, id_b = scenario.device_id(name_a), scenario.device_id(name_b)
    directed = [tuple(e.id.split("::", 1)) for e in _edges_between(app, id_a, id_b)]
    assert directed
    for from_vertex, to_vertex in directed:
        app.inspect.disconnect(from_vertex, to_vertex, bidirectional=False)
    app.inspect.refresh()
    assert not _edges_between(app, id_a, id_b)
    for from_vertex, to_vertex in directed:
        app.inspect.connect(from_vertex, to_vertex, bidirectional=False)
    app.inspect.refresh()
    assert len(_edges_between(app, id_a, id_b)) == len(directed)


def test_full_vs_skeleton_equivalence(app, scenario):
    def graph_view() -> dict:
        return {
            device_id: (
                app.inspect.get_device(device_id).label,
                frozenset(d.label for d in app.inspect.get_device(device_id).linked_devices),
            )
            for device_id in scenario.device_ids.values()
        }

    app.inspect.refresh(load="skeleton")
    app.inspect.preload(list(scenario.device_ids.values()))
    skeleton = graph_view()
    app.inspect.refresh(load="full")
    full = graph_view()
    assert skeleton == full
    app.inspect.refresh(load="skeleton")  # restore default load mode


def test_state_persists(app, scenario):
    # There is no teardown: after the suite the complete topology remains in VideoIPath.
    app.inspect.refresh()
    labels = {d.label for d in app.inspect.devices}
    assert all(name in labels for name in scenario.device_names)
    known = set(scenario.device_ids.values())
    scenario_edges = [
        e
        for e in app.inspect.edges
        if (e.from_device and e.from_device.id in known) or (e.to_device and e.to_device.id in known)
    ]
    assert len(scenario_edges) == scenario.expected_edge_count()
