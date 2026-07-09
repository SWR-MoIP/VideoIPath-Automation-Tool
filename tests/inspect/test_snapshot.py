"""Snapshot unit tests with a fake fetcher: skeleton indexes, exactly-one hydration per device,
section laziness, preload fan-out, refresh, and post-commit targeted refresh."""

from __future__ import annotations

import pytest

from videoipath_automation_tool.apps.inspect.model.collector import (
    InspectApiExternalEdgesByDeviceKeyItem,
    InspectApiNodeStatusItem,
    InspectApiPathItem,
)
from videoipath_automation_tool.apps.inspect.snapshot import HydrationLevel, InspectSnapshot


# --- Test data builders (small synthetic leaf-spine-ish graph) ---


def _skeleton_node(device_id: str, label: str, x: float = 0.0, y: float = 0.0, sync: int = 0):
    return InspectApiNodeStatusItem.model_validate(
        {
            "_id": device_id,
            "_vid": device_id,
            "deviceId": device_id,
            "descriptor": {"desc": "", "label": label},
            "meta": {"coordinates": {"x": x, "y": y}, "isVirtual": True, "iconType": "switch"},
            "status": {"sa": 0, "severity": 0},
            "syncSeverity": sync,
            "tags": ["#e2e"],
            "modules": {},
        }
    )


def _detail_node(device_id: str, label: str, port_pids: list[str]):
    ports = {
        pid: {
            "pid": pid,
            "descriptor": {"label": pid.split(".")[-1]},
            "status": {"sa": 0, "severity": 0},
            "vertexInfo": {"type": "single", "id": pid.replace(".dev.", "."), "vertexType": "Out"},
        }
        for pid in port_pids
    }
    return InspectApiNodeStatusItem.model_validate(
        {
            "_id": device_id,
            "_vid": device_id,
            "deviceId": device_id,
            "descriptor": {"desc": "", "label": label},
            "meta": {"coordinates": {"x": 0, "y": 0}},
            "status": {"sa": 0, "severity": 0},
            "syncSeverity": 0,
            "modules": {f"{device_id}.dev.0": {"pid": f"{device_id}.dev.0", "ports": ports}},
        }
    )


def _edge_pair(dev_a: str, dev_b: str, port_a: str, port_b: str):
    edge_id = f"{port_a}::{port_b}"
    return InspectApiExternalEdgesByDeviceKeyItem.model_validate(
        {
            "_id": f"{dev_a}::{dev_b}",
            "_vid": f"{dev_a}::{dev_b}",
            "primary": {
                "devicePid": dev_a,
                "label": dev_a,
                "data": {
                    edge_id: {
                        "id": edge_id,
                        "fromStatus": {"context": {"devicePid": dev_a, "portPid": port_a}, "label": "out"},
                        "toStatus": {"context": {"devicePid": dev_b, "portPid": port_b}, "label": "in"},
                    }
                },
            },
            "secondary": {"devicePid": dev_b, "label": dev_b, "data": {}},
            "status": {"alarm": 0, "bandwidth": 0, "maintenance": 0, "ptp": 0},
        }
    )


def _path_item(booking: str, dev_a: str, dev_b: str):
    return InspectApiPathItem.model_validate(
        {
            "_id": f"{booking}::main",
            "_vid": f"_:{booking}::main",
            "serviceFields": {"bid": booking, "isMain": True, "fromLabel": "src", "toLabel": "dst"},
            "path": [
                {"bid": booking, "structure": {"deviceId": dev_a, "devicePid": dev_a}},
                {"bid": booking, "structure": {"deviceId": dev_b, "devicePid": dev_b}},
            ],
        }
    )


class FakeFetcher:
    """Records how many detail/section fetches occur so laziness can be asserted."""

    def __init__(self):
        self.device_detail_calls: list[str] = []
        self.edge_pair_calls: list[str] = []
        self.section_calls = 0
        self.skeleton_calls = 0
        self._details = {
            "spine-a": _detail_node("spine-a", "SPINE-A", ["spine-a.dev.0.swp1", "spine-a.dev.0.swp2"]),
            "leaf-a": _detail_node("leaf-a", "LEAF-A", ["leaf-a.dev.0.up1", "leaf-a.dev.0.host1"]),
        }
        self._paths = [_path_item("1001", "leaf-a", "spine-a")]

    def get_device_skeleton(self):
        self.skeleton_calls += 1
        return [_skeleton_node("spine-a", "SPINE-A"), _skeleton_node("leaf-a", "LEAF-A")]

    def get_edge_skeleton(self):
        return [_edge_pair("leaf-a", "spine-a", "leaf-a.dev.0.up1", "spine-a.dev.0.swp1")]

    def get_device_detail(self, device_id):
        self.device_detail_calls.append(device_id)
        return self._details.get(device_id)

    def get_edge_pair(self, pair_id):
        self.edge_pair_calls.append(pair_id)
        a, b = pair_id.split("::")
        return _edge_pair(a, b, f"{a}.dev.0.up1", f"{b}.dev.0.swp1")

    def get_paths_section(self):
        self.section_calls += 1
        return self._paths


@pytest.fixture
def snapshot():
    fetcher = FakeFetcher()
    snap = InspectSnapshot(
        fetcher=fetcher,
        device_items=fetcher.get_device_skeleton(),
        edge_items=fetcher.get_edge_skeleton(),
    )
    fetcher.skeleton_calls = 0  # reset after construction
    return snap, fetcher


def test_skeleton_indexes_devices_and_edges(snapshot):
    snap, fetcher = snapshot
    assert {d.id for d in snap.devices} == {"spine-a", "leaf-a"}
    leaf = snap.get_device("leaf-a")
    assert leaf.label == "LEAF-A"
    assert leaf.is_virtual is True
    assert leaf.coordinates == {"x": 0.0, "y": 0.0}
    assert len(snap.edges) == 1
    assert fetcher.device_detail_calls == []  # nothing hydrated yet


def test_find_by_label(snapshot):
    snap, _ = snapshot
    assert snap.find_device_by_label("SPINE-A").id == "spine-a"


def test_ports_trigger_exactly_one_hydration(snapshot):
    snap, fetcher = snapshot
    leaf = snap.get_device("leaf-a")
    assert leaf.is_hydrated is False
    ports = leaf.ports
    assert {p.id for p in ports} == {"leaf-a.dev.0.up1", "leaf-a.dev.0.host1"}
    assert leaf.is_hydrated is True
    # Access again → no second fetch
    _ = leaf.ports
    assert fetcher.device_detail_calls == ["leaf-a"]
    # Other device still skeleton
    assert snap.get_device("spine-a").is_hydrated is False


def test_edges_do_not_trigger_hydration(snapshot):
    snap, fetcher = snapshot
    edge = snap.edges[0]
    assert edge.from_device.id == "leaf-a"
    assert edge.to_device.id == "spine-a"
    assert edge.status is not None
    assert fetcher.device_detail_calls == []


def test_edge_from_port_triggers_owning_device_hydration(snapshot):
    snap, fetcher = snapshot
    edge = snap.edges[0]
    port = edge.from_port
    assert port is not None
    assert port.id == "leaf-a.dev.0.up1"
    assert fetcher.device_detail_calls == ["leaf-a"]


def test_services_section_is_lazy(snapshot):
    snap, fetcher = snapshot
    assert fetcher.section_calls == 0
    services = snap.services
    assert {s.booking_id for s in services} == {"1001"}
    _ = snap.services  # second access
    assert fetcher.section_calls == 1
    assert {d.id for d in snap.get_services_for_device("leaf-a")[0].path_devices} == {"leaf-a", "spine-a"}


def test_linked_devices_from_edges(snapshot):
    snap, _ = snapshot
    assert {d.id for d in snap.get_device("leaf-a").linked_devices} == {"spine-a"}


def test_preload_hydrates_all(snapshot):
    snap, fetcher = snapshot
    snap.preload()
    assert set(fetcher.device_detail_calls) == {"spine-a", "leaf-a"}
    assert snap.get_device("spine-a").is_hydrated


def test_refresh_returns_new_snapshot(snapshot):
    snap, fetcher = snapshot
    new = snap.refresh()
    assert new is not snap
    assert fetcher.skeleton_calls == 1
    assert {d.id for d in new.devices} == {"spine-a", "leaf-a"}


def test_post_commit_removes_locally_and_refreshes_pair(snapshot):
    snap, fetcher = snapshot
    # remove a device locally
    snap.apply_post_commit(removed_ids=["spine-a"], mark_paths_stale=False)
    assert snap.get_device("spine-a") is None
    assert {d.id for d in snap.devices} == {"leaf-a"}


def test_post_commit_refreshes_edge_pair(snapshot):
    snap, fetcher = snapshot
    snap.apply_post_commit(pair_ids=["leaf-a::spine-a"])
    assert "leaf-a::spine-a" in fetcher.edge_pair_calls


def test_post_commit_marks_paths_stale(snapshot):
    snap, fetcher = snapshot
    _ = snap.services  # load section
    assert fetcher.section_calls == 1
    snap.apply_post_commit(mark_paths_stale=True)
    _ = snap.services  # reload
    assert fetcher.section_calls == 2


def test_post_commit_reindexes_changed_label(snapshot):
    # Latent-bug guard: a committed label change must re-point the label index (ADR-0010).
    snap, fetcher = snapshot
    fetcher._details["leaf-a"] = _detail_node("leaf-a", "LEAF-A-RENAMED", ["leaf-a.dev.0.up1"])
    snap.apply_post_commit(device_ids=["leaf-a"], mark_paths_stale=False)
    assert snap.find_device_by_label("LEAF-A-RENAMED").id == "leaf-a"
    assert snap.find_device_by_label("LEAF-A") is None


def test_post_commit_refetch_failure_does_not_raise_and_self_heals(snapshot):
    snap, fetcher = snapshot
    calls = {"n": 0}
    real = fetcher.get_device_detail

    def flaky(device_id):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("network blip")
        return real(device_id)

    fetcher.get_device_detail = flaky
    # The refresh failure is swallowed (the commit result must survive); the device is marked stale.
    snap.apply_post_commit(device_ids=["leaf-a"], mark_paths_stale=False)
    # Next access re-fetches (self-heal) and succeeds.
    assert snap.get_device("leaf-a").label == "LEAF-A"
    assert calls["n"] == 2


def test_apply_network_refresh_adds_new_device_and_edge(snapshot):
    snap, fetcher = snapshot
    fetcher._details["leaf-b"] = _detail_node("leaf-b", "LEAF-B", ["leaf-b.dev.0.up1"])
    fetcher.get_edge_skeleton = lambda: [
        _edge_pair("leaf-a", "spine-a", "leaf-a.dev.0.up1", "spine-a.dev.0.swp1"),
        _edge_pair("leaf-b", "spine-a", "leaf-b.dev.0.up1", "spine-a.dev.0.swp2"),
    ]
    snap.apply_network_refresh(["leaf-b"])
    assert snap.get_device("leaf-b") is not None
    assert snap.find_device_by_label("LEAF-B").id == "leaf-b"
    assert {e.pair_id for e in snap.get_edges_for_device("leaf-b")} == {"leaf-b::spine-a"}


def test_full_snapshot_is_hydrated_without_fetcher():
    fetcher = FakeFetcher()
    # Build a full snapshot manually (device_level=FULL, path_items provided)
    snap = InspectSnapshot(
        fetcher=None,
        device_items=[fetcher._details["leaf-a"], fetcher._details["spine-a"]],
        edge_items=[_edge_pair("leaf-a", "spine-a", "leaf-a.dev.0.up1", "spine-a.dev.0.swp1")],
        device_level=HydrationLevel.FULL,
        path_items=fetcher._paths,
    )
    leaf = snap.get_device("leaf-a")
    assert leaf.is_hydrated
    assert len(leaf.ports) == 2
    # sections available without a fetcher
    assert {s.booking_id for s in snap.services} == {"1001"}
    # refresh without a fetcher raises
    with pytest.raises(RuntimeError):
        snap.refresh()
