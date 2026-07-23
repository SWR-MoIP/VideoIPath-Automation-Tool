"""Snapshot unit tests with a fake fetcher: skeleton indexes, exactly-one hydration per device,
section laziness, preload fan-out, refresh, and post-commit targeted refresh."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from videoipath_automation_tool.apps.inspect.model.actions import (
    InspectApiLookupEdgesResponse,
    InspectApiLookupVerticesResponse,
)
from videoipath_automation_tool.apps.inspect.model.alarms import InspectApiAlarmItem
from videoipath_automation_tool.apps.inspect.model.collector import (
    InspectApiExternalEdgesByDeviceKeyItem,
    InspectApiNodeStatusItem,
    InspectApiPathItem,
)
from videoipath_automation_tool.apps.inspect.model.common import InspectSeverity
from videoipath_automation_tool.apps.inspect.snapshot import HydrationLevel, InspectSnapshot

from .conftest import load_fixture


def test_skeleton_indexes_devices_and_edges(snapshot: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snap, fetcher = snapshot
    assert {d.id for d in snap.devices} == {"spine-a", "leaf-a"}
    leaf = snap.get_device("leaf-a")
    assert leaf.label == "LEAF-A"
    assert leaf.is_virtual is True
    assert leaf.coordinates == {"x": 0.0, "y": 0.0}
    assert len(snap.edges) == 1
    assert fetcher.device_detail_calls == []  # nothing hydrated yet


def test_find_by_label(snapshot: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snap, _ = snapshot
    assert snap.find_device_by_label("SPINE-A").id == "spine-a"


def test_device_description_from_descriptor(snapshot: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snap, _ = snapshot
    assert snap.get_device("leaf-a").description == "LEAF-A description"


def test_ports_trigger_exactly_one_hydration(snapshot: tuple[InspectSnapshot, FakeFetcher]) -> None:
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


def test_edges_do_not_trigger_hydration(snapshot: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snap, fetcher = snapshot
    edge = snap.edges[0]
    assert edge.from_device.id == "leaf-a"
    assert edge.to_device.id == "spine-a"
    assert edge.status is not None
    assert fetcher.device_detail_calls == []


def test_edge_from_port_triggers_owning_device_hydration(snapshot: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snap, fetcher = snapshot
    edge = snap.edges[0]
    port = edge.from_port
    assert port is not None
    assert port.id == "leaf-a.dev.0.up1"
    assert fetcher.device_detail_calls == ["leaf-a"]


def test_services_section_is_lazy(snapshot: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snap, fetcher = snapshot
    assert fetcher.section_calls == 0
    services = snap.services
    assert {s.booking_id for s in services} == {"1001"}
    _ = snap.services  # second access
    assert fetcher.section_calls == 1
    assert {d.id for d in snap.get_services_for_device("leaf-a")[0].path_devices} == {"leaf-a", "spine-a"}


def test_alarms_section_is_lazy_and_correlates(snapshot: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snap, fetcher = snapshot
    fetcher._alarms = [
        InspectApiAlarmItem.model_validate(raw)
        for raw in load_fixture("alarms_current.json")["data"]["status"]["alarms"]["current"]["_items"]
    ]
    # Remap fixture device-a alarms onto leaf-a for this snapshot's devices.
    for item in fetcher._alarms:
        assert item.id is not None
        item.id.pointId = ["leaf-a", *item.id.pointId[1:]]

    assert fetcher.alarm_section_calls == 0
    device = snap.get_device("leaf-a")
    alarms = device.alarms
    assert fetcher.alarm_section_calls == 1
    assert len(alarms) == 3
    assert alarms[0].severity == InspectSeverity.MAJOR  # worst first
    assert alarms[0].message == "Loss of protection"
    assert device.status_message == "Loss of protection"
    _ = device.alarms
    assert fetcher.alarm_section_calls == 1

    module_alarms = snap.get_alarms_for_module("leaf-a", "leaf-a.dev.module-1")
    assert len(module_alarms) == 1
    assert module_alarms[0].message == "Loss of protection"

    port_alarms = snap.get_alarms_for_port("leaf-a.dev.module-1.port-out-1")
    assert len(port_alarms) == 1
    assert port_alarms[0].message == "Loss of disjunctivity"
    assert port_alarms[0].severity == InspectSeverity.MINOR


def test_post_commit_marks_alarms_stale(snapshot: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snap, fetcher = snapshot
    fetcher._alarms = [
        InspectApiAlarmItem.model_validate(
            {
                "_id": "1:leaf-a.dev:Mock",
                "acked": False,
                "id": {"alertId": "Mock", "component": 1, "pointId": ["leaf-a", "dev"]},
                "info": {"details": "Mock driver in use", "severity": 2, "sa": 2},
            }
        )
    ]
    assert len(snap.get_device("leaf-a").alarms) == 1
    assert fetcher.alarm_section_calls == 1
    snap.apply_post_commit(mark_paths_stale=True)
    assert len(snap.get_device("leaf-a").alarms) == 1
    assert fetcher.alarm_section_calls == 2


def test_linked_devices_from_edges(snapshot: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snap, _ = snapshot
    assert {d.id for d in snap.get_device("leaf-a").linked_devices} == {"spine-a"}


def test_preload_hydrates_all(snapshot: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snap, fetcher = snapshot
    snap.preload()
    assert set(fetcher.device_detail_calls) == {"spine-a", "leaf-a"}
    assert snap.get_device("spine-a").is_hydrated


def test_refresh_returns_new_snapshot(snapshot: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snap, fetcher = snapshot
    new = snap.refresh()
    assert new is not snap
    assert fetcher.skeleton_calls == 1
    assert {d.id for d in new.devices} == {"spine-a", "leaf-a"}


def test_post_commit_removes_locally_and_refreshes_pair(snapshot: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snap, fetcher = snapshot
    # remove a device locally
    snap.apply_post_commit(removed_ids=["spine-a"], mark_paths_stale=False)
    assert snap.get_device("spine-a") is None
    assert {d.id for d in snap.devices} == {"leaf-a"}


def test_post_commit_refreshes_edge_pair(snapshot: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snap, fetcher = snapshot
    snap.apply_post_commit(pair_ids=["leaf-a::spine-a"])
    assert "leaf-a::spine-a" in fetcher.edge_pair_calls


def test_post_commit_marks_paths_stale(snapshot: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snap, fetcher = snapshot
    _ = snap.services  # load section
    assert fetcher.section_calls == 1
    snap.apply_post_commit(mark_paths_stale=True)
    _ = snap.services  # reload
    assert fetcher.section_calls == 2


def test_post_commit_reindexes_changed_label(snapshot: tuple[InspectSnapshot, FakeFetcher]) -> None:
    # Latent-bug guard: a committed label change must re-point the label index (ADR-0010).
    snap, fetcher = snapshot
    fetcher._details["leaf-a"] = _detail_node("leaf-a", "LEAF-A-RENAMED", ["leaf-a.dev.0.up1"])
    snap.apply_post_commit(device_ids=["leaf-a"], mark_paths_stale=False)
    assert snap.find_device_by_label("LEAF-A-RENAMED").id == "leaf-a"
    assert snap.find_device_by_label("LEAF-A") is None


def test_post_commit_refetch_failure_does_not_raise_and_self_heals(
    snapshot: tuple[InspectSnapshot, FakeFetcher],
) -> None:
    snap, fetcher = snapshot
    calls = {"n": 0}
    real = fetcher.get_device_detail

    def flaky(device_id: str) -> InspectApiNodeStatusItem | None:
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


def test_apply_network_refresh_adds_new_device_and_edge(snapshot: tuple[InspectSnapshot, FakeFetcher]) -> None:
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


def test_full_snapshot_is_hydrated_without_fetcher() -> None:
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


def test_port_is_lean_and_vertex_carries_flags(snapshot: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snap, _ = snapshot
    port = snap.get_port("leaf-a", "leaf-a.dev.0.up1")
    # Port keeps only the module-level attributes.
    assert port.label == "up1"  # descriptor override
    assert port.factory_label == "up1-factory"
    assert not hasattr(port, "is_active")  # vertex-specific fields live on the vertex now
    assert not hasattr(port, "edge")  # edges are accessed via the collection now
    # The direction/status flags live on the vertex.
    assert port.is_bidirectional is False
    assert port.vertex_out is not None
    assert port.vertex_out.id == "leaf-a.0.up1"
    assert port.vertex_out.vertex_type == "Out"
    assert port.vertex_out.is_active is True
    assert port.vertex_out.is_controlled is True
    assert port.vertex_out.is_endpoint is False
    assert port.vertex_in is None


def test_bidirectional_port_vertex_accessors(snapshot: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snap, fetcher = snapshot
    fetcher._details["leaf-a"] = _filter_detail_node("leaf-a", "LEAF-A")
    port = snap.get_port("leaf-a", "leaf-a.dev.1.bidi1")
    assert port.is_bidirectional is True
    assert port.vertex_out is not None and port.vertex_out.vertex_type == "Out"
    assert port.vertex_in is not None and port.vertex_in.vertex_type == "In"
    assert port.vertex_out.id == "leaf-a.1.bidi1.out"
    assert port.vertex_in.id == "leaf-a.1.bidi1.in"


def test_vertex_config_attrs_fetch_once_and_cache(snapshot: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snap, fetcher = snapshot
    vertex = snap.get_port("leaf-a", "leaf-a.dev.0.up1").vertex_out
    assert vertex is not None
    assert vertex.type_fields is not None and vertex.type_fields.type == "ip"
    assert vertex.vertex_kind == "ip"
    assert vertex.sips_mode == "NONE"
    assert vertex.control_props is not None and vertex.control_props.configPriority == "off"
    assert vertex.extra_alert_filters == []
    assert vertex.custom == {}
    assert vertex.custom_schemas == {}
    assert vertex.queueable is False
    assert vertex.destination_monitor_leader is False
    assert vertex.park_port is None
    _ = vertex.vertex_kind  # second access → cached
    assert fetcher.vertex_lookup_calls == [["leaf-a.0.up1"]]


def test_vertex_lookup_invalidated_by_post_commit_device_refresh(
    snapshot: tuple[InspectSnapshot, FakeFetcher],
) -> None:
    snap, fetcher = snapshot
    _ = snap.get_port("leaf-a", "leaf-a.dev.0.up1").vertex_out.vertex_kind
    assert len(fetcher.vertex_lookup_calls) == 1
    snap.apply_post_commit(device_ids=["leaf-a"], mark_paths_stale=False)
    _ = snap.get_port("leaf-a", "leaf-a.dev.0.up1").vertex_out.vertex_kind
    assert len(fetcher.vertex_lookup_calls) == 2


def test_vertex_flags_offline_but_config_none_without_fetcher() -> None:
    fetcher = FakeFetcher()
    snap = InspectSnapshot(
        fetcher=None,
        device_items=[fetcher._details["leaf-a"]],
        device_level=HydrationLevel.FULL,
    )
    vertex = snap.get_port("leaf-a", "leaf-a.dev.0.up1").vertex_out
    assert vertex is not None
    assert vertex.vertex_type == "Out"  # offline from the port's vertexInfo
    assert vertex.is_active is True  # offline
    assert vertex.vertex_kind is None  # needs a lookup; no fetcher
    assert vertex.sips_mode is None
    assert vertex.control_props is None
    assert vertex.park_port is None


def test_filter_ports_by_module_and_direction(snapshot: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snap, fetcher = snapshot
    fetcher._details["leaf-a"] = _filter_detail_node("leaf-a", "LEAF-A")
    leaf = snap.get_device("leaf-a")
    assert {p.label for p in leaf.filter_ports(module_id="leaf-a.dev.0")} == {"up1", "host1"}
    assert {p.label for p in leaf.filter_ports(vertex_type="Out")} == {"up1"}
    assert {p.label for p in leaf.filter_ports(vertex_type="BiDirectional")} == {"bidi1"}
    assert {p.label for p in leaf.filter_ports(module_id="leaf-a.dev.1", vertex_type="BiDirectional")} == {"bidi1"}
    assert fetcher.vertex_lookup_calls == []


def test_filter_ports_by_flags(snapshot: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snap, fetcher = snapshot
    fetcher._details["leaf-a"] = _filter_detail_node("leaf-a", "LEAF-A")
    leaf = snap.get_device("leaf-a")
    assert {p.label for p in leaf.filter_ports(active=True)} == {"up1", "bidi1"}
    assert {p.label for p in leaf.filter_ports(active=False)} == {"host1"}  # mgmt1 (unknown) never matches
    assert {p.label for p in leaf.filter_ports(endpoint=True)} == {"host1", "bidi1"}
    assert {p.label for p in leaf.filter_ports(controlled=True)} == {"up1"}
    assert {p.label for p in leaf.filter_ports(active=True, endpoint=True)} == {"bidi1"}
    assert fetcher.vertex_lookup_calls == []


def test_filter_ports_by_kind_uses_one_batched_lookup(snapshot: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snap, fetcher = snapshot
    fetcher._details["leaf-a"] = _filter_detail_node("leaf-a", "LEAF-A")
    leaf = snap.get_device("leaf-a")
    ports = leaf.filter_ports(kind="ip")
    assert {p.label for p in ports} == {"up1", "host1", "bidi1"}  # mgmt1 has no vertex → excluded
    assert len(fetcher.vertex_lookup_calls) == 1  # one batched call for all uncached vertices
    assert set(fetcher.vertex_lookup_calls[0]) == {"leaf-a.0.up1", "leaf-a.0.host1", "leaf-a.1.bidi1.out"}
    _ = leaf.filter_ports(kind="ip")  # cached → no further lookups
    assert len(fetcher.vertex_lookup_calls) == 1


# --- Internal ---


def _skeleton_node(
    device_id: str,
    label: str,
    x: float = 0.0,
    y: float = 0.0,
    sync: int = 0,
) -> InspectApiNodeStatusItem:
    return InspectApiNodeStatusItem.model_validate(
        {
            "_id": device_id,
            "_vid": device_id,
            "deviceId": device_id,
            "descriptor": {"desc": f"{label} description", "label": label},
            "meta": {"coordinates": {"x": x, "y": y}, "isVirtual": True, "iconType": "switch"},
            "status": {"sa": 0, "severity": 0},
            "syncSeverity": sync,
            "tags": ["#e2e"],
            "modules": {},
        }
    )


def _detail_node(device_id: str, label: str, port_pids: list[str]) -> InspectApiNodeStatusItem:
    ports = {
        pid: {
            "pid": pid,
            "descriptor": {"label": pid.split(".")[-1]},
            "label": f"{pid.split('.')[-1]}-factory",
            "status": {"sa": 0, "severity": 0},
            "vertexInfo": _single_vertex_info(
                pid.replace(".dev.", "."), "Out", active=True, controlled=True, endpoint=False
            ),
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
            "modules": {
                f"{device_id}.dev.0": {
                    "pid": f"{device_id}.dev.0",
                    "descriptor": {"label": "Slot 0"},
                    "ports": ports,
                }
            },
        }
    )


def _single_vertex_info(vertex_id: str, vertex_type: str, *, active: bool, controlled: bool, endpoint: bool) -> dict:
    return {
        "type": "single",
        "id": vertex_id,
        "vertexType": vertex_type,
        "fields": {"isActive": active, "isControlled": controlled, "isEndpoint": endpoint},
    }


def _filter_detail_node(device_id: str, label: str) -> InspectApiNodeStatusItem:
    """A hydrated device with port variety for filter tests: two single vertices (Out active
    controlled / In inactive endpoint), one double (bidirectional endpoint), one without vertexInfo."""

    def port(module: str, name: str, vertex_info: dict | None) -> dict:
        entry: dict = {"pid": f"{device_id}.dev.{module}.{name}", "descriptor": {"label": name}}
        if vertex_info is not None:
            entry["vertexInfo"] = vertex_info
        return entry

    modules = {
        f"{device_id}.dev.0": {
            "pid": f"{device_id}.dev.0",
            "descriptor": {"label": "Slot 0"},
            "ports": {
                f"{device_id}.dev.0.up1": port(
                    "0",
                    "up1",
                    _single_vertex_info(f"{device_id}.0.up1", "Out", active=True, controlled=True, endpoint=False),
                ),
                f"{device_id}.dev.0.host1": port(
                    "0",
                    "host1",
                    _single_vertex_info(f"{device_id}.0.host1", "In", active=False, controlled=False, endpoint=True),
                ),
            },
        },
        f"{device_id}.dev.1": {
            "pid": f"{device_id}.dev.1",
            "descriptor": {"label": "Slot 1"},
            "ports": {
                f"{device_id}.dev.1.bidi1": port(
                    "1",
                    "bidi1",
                    {
                        "type": "double",
                        "in": _single_vertex_info(
                            f"{device_id}.1.bidi1.in", "In", active=True, controlled=False, endpoint=True
                        ),
                        "out": _single_vertex_info(
                            f"{device_id}.1.bidi1.out", "Out", active=True, controlled=False, endpoint=True
                        ),
                    },
                ),
                f"{device_id}.dev.1.mgmt1": port("1", "mgmt1", None),
            },
        },
    }
    return InspectApiNodeStatusItem.model_validate(
        {
            "_id": device_id,
            "_vid": device_id,
            "deviceId": device_id,
            "descriptor": {"desc": "", "label": label},
            "modules": modules,
        }
    )


def _edge_pair(dev_a: str, dev_b: str, port_a: str, port_b: str) -> InspectApiExternalEdgesByDeviceKeyItem:
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


def _path_item(booking: str, dev_a: str, dev_b: str) -> InspectApiPathItem:
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

    def __init__(self) -> None:
        self.device_detail_calls: list[str] = []
        self.edge_pair_calls: list[str] = []
        self.vertex_lookup_calls: list[list[str]] = []
        self.edge_lookup_calls: list[list[str]] = []
        self.section_calls = 0
        self.alarm_section_calls = 0
        self.skeleton_calls = 0
        self._details = {
            "spine-a": _detail_node("spine-a", "SPINE-A", ["spine-a.dev.0.swp1", "spine-a.dev.0.swp2"]),
            "leaf-a": _detail_node("leaf-a", "LEAF-A", ["leaf-a.dev.0.up1", "leaf-a.dev.0.host1"]),
        }
        self._paths = [_path_item("1001", "leaf-a", "spine-a")]
        self._alarms: list[InspectApiAlarmItem] = []

    def get_device_skeleton(self) -> list[InspectApiNodeStatusItem]:
        self.skeleton_calls += 1
        return [_skeleton_node("spine-a", "SPINE-A"), _skeleton_node("leaf-a", "LEAF-A")]

    def get_edge_skeleton(self) -> list[InspectApiExternalEdgesByDeviceKeyItem]:
        return [_edge_pair("leaf-a", "spine-a", "leaf-a.dev.0.up1", "spine-a.dev.0.swp1")]

    def get_device_detail(self, device_id: str) -> InspectApiNodeStatusItem | None:
        self.device_detail_calls.append(device_id)
        return self._details.get(device_id)

    def get_edge_pair(self, pair_id: str) -> InspectApiExternalEdgesByDeviceKeyItem:
        self.edge_pair_calls.append(pair_id)
        a, b = pair_id.split("::")
        return _edge_pair(a, b, f"{a}.dev.0.up1", f"{b}.dev.0.swp1")

    def get_paths_section(self) -> list[InspectApiPathItem]:
        self.section_calls += 1
        return self._paths

    def get_alarms_section(self) -> list[InspectApiAlarmItem]:
        self.alarm_section_calls += 1
        return list(self._alarms)

    def lookup_vertices(self, vertex_ids: list[str]) -> InspectApiLookupVerticesResponse:
        self.vertex_lookup_calls.append(list(vertex_ids))
        data = {vertex_id: _vertex_lookup_item(vertex_id) for vertex_id in vertex_ids}
        return InspectApiLookupVerticesResponse.model_validate({"data": data, "header": _fetcher_ok_header()})

    def lookup_edges(self, edge_ids: list[str]) -> InspectApiLookupEdgesResponse:
        self.edge_lookup_calls.append(list(edge_ids))
        data = {
            edge_id: {
                "edge": {"fromId": edge_id.split("::")[0], "toId": edge_id.split("::")[-1]},
                "fromDevice": None,
                "toDevice": None,
            }
            for edge_id in edge_ids
        }
        return InspectApiLookupEdgesResponse.model_validate({"data": data, "header": _fetcher_ok_header()})


def _fetcher_ok_header() -> dict[str, object]:
    return {
        "auth": True,
        "caption": "Operation Successful",
        "code": "OK",
        "errorCodes": [],
        "errorDetails": [],
        "id": "0",
        "msg": [],
        "ok": True,
        "user": "api-user",
    }


def _vertex_lookup_item(vertex_id: str) -> dict[str, object]:
    """An IP-vertex lookup item; codec ids (containing 'codec') return the codec fixture's data."""
    if "codec" in vertex_id:
        item = dict(load_fixture("lookup_inspect_codec_vertex_by_id.json")["data"])
        item["id"] = vertex_id
        return item
    return {
        "id": vertex_id,
        "isVirtual": False,
        "vertexType": "Out",
        "customSchemas": {},
        "fields": {
            "active": True,
            "controlProps": {"configPriority": "off", "onlyInitial": False},
            "custom": {},
            "desc": "",
            "destinationMonitorLeader": False,
            "extraAlertFilters": [],
            "label": vertex_id,
            "localAssignedTags": [],
            "queueable": False,
            "sipsMode": "NONE",
            "tags": [],
            "typeFields": {"type": "ip", "ipAddress": "10.0.0.1", "vlanId": "100"},
            "useAsEndpoint": False,
        },
    }


# --- Typed vertices + edge config (new field coverage) ---


def test_get_vertex_returns_typed_ip_vertex(snapshot: tuple[InspectSnapshot, FakeFetcher]) -> None:
    from videoipath_automation_tool.apps.inspect.domain.vertex import InspectIpVertex

    snap, _ = snapshot
    vertex = snap.get_vertex("leaf-a.0.up1")
    assert isinstance(vertex, InspectIpVertex)
    assert vertex.vertex_kind == "ip"
    assert vertex.vertex_type == "Out"
    assert vertex.ip_address == "10.0.0.1"
    assert vertex.vlan_id == "100"


def test_get_vertex_returns_typed_codec_vertex(snapshot: tuple[InspectSnapshot, FakeFetcher]) -> None:
    from videoipath_automation_tool.apps.inspect.domain.vertex import InspectCodecVertex

    snap, _ = snapshot
    vertex = snap.get_vertex("device-a.1.codec-out-1.out")
    assert isinstance(vertex, InspectCodecVertex)
    assert vertex.vertex_kind == "codec"
    assert vertex.codec_format == "Video"
    assert vertex.is_igmp_source is False
    assert vertex.sdp_support is True
    assert vertex.main_dst_info == {"ip": "10.0.0.1", "mac": None, "port": 5000, "vlan": None}


def test_edge_config_props_and_detail_cache(snapshot: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snap, fetcher = snapshot
    edge = snap.edges[0]
    assert edge.redundancy_mode == "Any"
    assert edge.fixed_weight == 1
    assert edge.conflict_priority == "off"  # on-wire 0 -> "off"
    assert edge.services_capacity == 65535
    assert edge.bandwidth_weight_factor == 0
    _ = edge.label  # further access is served from the cache
    assert fetcher.edge_lookup_calls == [[edge.id]]


# --- Modules ---


def test_device_modules_group_ports(snapshot: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snap, _ = snapshot
    leaf = snap.get_device("leaf-a")
    modules = leaf.modules
    assert len(modules) == 1
    module = modules[0]
    assert module.id == "leaf-a.dev.0"
    assert module.label == "Slot 0"
    assert {p.label for p in module.ports} == {"up1", "host1"}
    # module.ports == device.ports grouped by module, and every port links back to its module
    assert {p.id for p in module.ports} == {
        p.id for p in leaf.ports if p.module is not None and p.module.id == "leaf-a.dev.0"
    }
    assert all(p.module is not None for p in leaf.ports)
    assert all(p.module is not None and p.module.id == module.id for p in module.ports)
    # flattened convenience: one vertex per (single-vertex) port
    assert len(module.vertices) == 2
    assert leaf.get_module("leaf-a.dev.0").id == "leaf-a.dev.0"
    assert leaf.get_module("no-such-module") is None


def test_module_vertices_uses_one_batched_lookup(snapshot: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snap, fetcher = snapshot
    module = snap.get_device("leaf-a").get_module("leaf-a.dev.0")
    assert module is not None
    vertices = module.vertices
    assert {v.id for v in vertices} == {"leaf-a.0.up1", "leaf-a.0.host1"}
    assert len(fetcher.vertex_lookup_calls) == 1
    assert set(fetcher.vertex_lookup_calls[0]) == {"leaf-a.0.up1", "leaf-a.0.host1"}


def test_get_vertices_by_module_label_uses_one_batched_lookup(
    snapshot: tuple[InspectSnapshot, FakeFetcher],
) -> None:
    snap, fetcher = snapshot
    fetcher._details["leaf-a"] = _filter_detail_node("leaf-a", "LEAF-A")
    leaf = snap.get_device("leaf-a")
    vertices = leaf.get_vertices_by_module_label("Slot 1")
    assert {v.id for v in vertices} == {"leaf-a.1.bidi1.out", "leaf-a.1.bidi1.in"}
    assert len(fetcher.vertex_lookup_calls) == 1
    assert set(fetcher.vertex_lookup_calls[0]) == {"leaf-a.1.bidi1.out", "leaf-a.1.bidi1.in"}
    ip_only = leaf.get_vertices_by_module_label("Slot 1", kind="ip")
    assert {v.id for v in ip_only} == {"leaf-a.1.bidi1.out", "leaf-a.1.bidi1.in"}
    assert len(fetcher.vertex_lookup_calls) == 1  # cached → no further lookups


def test_preload_continues_when_one_device_fails(snapshot: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snap, fetcher = snapshot

    original = fetcher.get_device_detail

    def flaky_detail(device_id: str) -> InspectApiNodeStatusItem | None:
        if device_id == "spine-a":
            raise RuntimeError("simulated detail failure")
        return original(device_id)

    fetcher.get_device_detail = flaky_detail  # type: ignore[method-assign]
    snap.preload()
    assert "leaf-a" in fetcher.device_detail_calls
    assert snap.get_device("leaf-a").is_hydrated is True
    assert snap.get_device("spine-a").is_hydrated is False
    assert "spine-a" in snap._stale_devices


def test_device_exposes_multiple_modules(snapshot: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snap, fetcher = snapshot
    fetcher._details["leaf-a"] = _filter_detail_node("leaf-a", "LEAF-A")
    leaf = snap.get_device("leaf-a")
    modules = {m.label: m for m in leaf.modules}
    assert set(modules) == {"Slot 0", "Slot 1"}
    assert {p.label for p in modules["Slot 0"].ports} == {"up1", "host1"}
    assert {p.label for p in modules["Slot 1"].ports} == {"bidi1", "mgmt1"}


@pytest.fixture
def snapshot() -> Iterator[tuple[InspectSnapshot, FakeFetcher]]:
    fetcher = FakeFetcher()
    snap = InspectSnapshot(
        fetcher=fetcher,
        device_items=fetcher.get_device_skeleton(),
        edge_items=fetcher.get_edge_skeleton(),
    )
    fetcher.skeleton_calls = 0  # reset after construction
    yield snap, fetcher
