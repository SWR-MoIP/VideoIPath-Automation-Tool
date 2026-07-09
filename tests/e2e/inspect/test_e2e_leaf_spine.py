"""End-to-end Inspect tests against a live instance using the fixed leaf-spine scenario.

Developer-run only (see ``tests/e2e/conftest.py``). Ordered by dependency and sharing one
session-scoped scenario that is built once and torn down at the end (an autouse finalizer also
cleans up if a run aborts). All writes stay inside the ``E2E-`` / ``vipat-e2e`` namespace.

Everything goes through ``app.inspect`` — the app owns its topology view internally; tests call
``app.inspect.refresh()`` to get a fresh read and then use ``app.inspect.devices`` / ``get_device`` /
``edges`` directly.

Run with::

    poetry run pytest -m e2e tests/e2e/inspect
"""

from __future__ import annotations

import pytest

from videoipath_automation_tool.apps.inspect.errors import InspectCommitConflictError, InspectCommitError
from videoipath_automation_tool.apps.videoipath_app import VideoIPathApp

from .scenario import E2E_PREFIX, LeafSpineScenario

pytestmark = pytest.mark.e2e


@pytest.fixture(scope="session")
def scenario(app: VideoIPathApp):
    scn = LeafSpineScenario()
    scn.teardown(app)  # clean slate from any aborted prior run
    scn.build(app)
    yield scn
    scn.teardown(app)
    scn.assert_clean(app)


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


def test_build_and_skeleton_read(app, scenario):
    app.inspect.refresh()
    with _FetchSpy(app.inspect._inspect_api) as spy:
        labels = {d.label for d in app.inspect.devices}
        for expected in scenario.device_labels:
            assert expected in labels
        known = set(scenario.device_ids.values())
        scenario_edges = [
            e
            for e in app.inspect.edges
            if (e.from_device and e.from_device.id in known) or (e.to_device and e.to_device.id in known)
        ]
        assert len(scenario_edges) >= scenario.expected_edge_count()
    assert spy.count == 0  # skeleton read triggers no hydration


def test_lazy_hydration(app, scenario):
    # Virtual devices do not expose ports in nodeStatus; this asserts the hydration *mechanic*
    # (exactly one detail fetch per device, cached thereafter, hydration state flips).
    app.inspect.refresh()
    leaf_id = scenario.device_id("E2E-LEAF-A1")
    other_id = scenario.device_id("E2E-SPINE-A")
    assert not app.inspect.is_device_hydrated(leaf_id)
    with _FetchSpy(app.inspect._inspect_api) as spy:
        _ = app.inspect.get_device(leaf_id).ports  # triggers one detail fetch
        assert spy.count == 1
        _ = app.inspect.get_device(leaf_id).ports  # cached, no further fetch
        assert spy.count == 1
    assert app.inspect.is_device_hydrated(leaf_id)
    assert not app.inspect.is_device_hydrated(other_id)


def test_connectivity_graph(app, scenario):
    app.inspect.refresh()
    enc1 = app.inspect.get_device(scenario.device_id("E2E-ENC-1"))
    linked = {d.label for d in enc1.linked_devices}
    assert linked == {"E2E-LEAF-A1", "E2E-LEAF-B1"}
    # Spine adjacency: SPINE-A is linked to both red leaves.
    spine_a = app.inspect.get_device(scenario.device_id("E2E-SPINE-A"))
    spine_links = {d.label for d in spine_a.linked_devices}
    assert {"E2E-LEAF-A1", "E2E-LEAF-A2"} <= spine_links


def test_edge_pair_refresh(app, scenario):
    app.inspect.refresh()  # load the internal view so the write can update it in place
    edge_id = f"{scenario.out_vertex('E2E-LEAF-A1', 'uplink0')}::{scenario.in_vertex('E2E-SPINE-A', 'downlink0')}"
    result = app.inspect.update_edge(edge_id, weight=7)
    assert result.ok
    # The edge survives the targeted post-commit refresh without a full reload.
    assert any(e.id == edge_id for e in app.inspect.edges)
    app.inspect.update_edge(edge_id, weight=1)  # revert


def test_transaction_atomicity(app, scenario):
    edge_id = f"{scenario.out_vertex('E2E-LEAF-A2', 'uplink0')}::{scenario.in_vertex('E2E-SPINE-A', 'downlink1')}"
    with pytest.raises(InspectCommitError):
        with app.inspect.transaction() as tx:
            tx.update_edge(edge_id, weight=13)
            tx.remove("does-not-exist::also-not-real")
            tx.commit()
    # Nothing applied: the edge is still present on the server.
    app.inspect.refresh()
    assert any(e.id == edge_id for e in app.inspect.edges)


def test_conflict_detection(app, scenario):
    edge_id = f"{scenario.out_vertex('E2E-LEAF-B1', 'uplink0')}::{scenario.in_vertex('E2E-SPINE-B', 'downlink0')}"
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
    device_id = scenario.device_id("E2E-ENC-1")
    app.inspect.place_device(device_id, 4200, 4200)
    app.inspect.refresh()
    coords = app.inspect.get_device(device_id).coordinates
    assert coords is not None and coords["x"] == 4200 and coords["y"] == 4200
    # revert to scenario coordinates
    spec = next(d for d in scenario.devices if d.label == "E2E-ENC-1")
    app.inspect.place_device(device_id, spec.x, spec.y)


def test_disconnect_connect_cycle(app, scenario):
    a_out = scenario.out_vertex("E2E-DEC-2", "eth-a")
    b_in = scenario.in_vertex("E2E-LEAF-A2", "host1")
    b_out = scenario.out_vertex("E2E-LEAF-A2", "host1")
    a_in = scenario.in_vertex("E2E-DEC-2", "eth-a")
    app.inspect.disconnect(a_out, b_in, bidirectional=False)
    app.inspect.disconnect(b_out, a_in, bidirectional=False)
    app.inspect.refresh()
    assert not any(e.id == f"{a_out}::{b_in}" for e in app.inspect.edges)
    # reconnect
    app.inspect.connect(a_out, b_in, bidirectional=False)
    app.inspect.connect(b_out, a_in, bidirectional=False)
    app.inspect.refresh()
    assert any(e.id == f"{a_out}::{b_in}" for e in app.inspect.edges)


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
    app.inspect.refresh(load="skeleton")  # restore default load mode for later tests


def test_teardown(app, scenario):
    # Explicit teardown assertion; the fixture finalizer repeats it for aborted runs.
    scenario.teardown(app)
    scenario.assert_clean(app)
    app.inspect.refresh()
    assert not any((d.label or "").startswith(E2E_PREFIX) for d in app.inspect.devices)
