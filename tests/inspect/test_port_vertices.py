"""Port vertex accessors for every single-vertex type and for double ports."""

from __future__ import annotations

import pytest

from videoipath_automation_tool.apps.inspect.domain.port import InspectPort
from videoipath_automation_tool.apps.inspect.model.collector import InspectApiNodeStatusItem
from videoipath_automation_tool.apps.inspect.snapshot import InspectSnapshot

from .test_snapshot import FakeFetcher, _single_vertex_info

_DEVICE = "leaf-a"


@pytest.fixture
def snap() -> tuple[InspectSnapshot, FakeFetcher]:
    fetcher = FakeFetcher()
    fetcher._details[_DEVICE] = _vertex_type_node()
    snapshot = InspectSnapshot(
        fetcher=fetcher,
        device_items=fetcher.get_device_skeleton(),
        edge_items=fetcher.get_edge_skeleton(),
    )
    return snapshot, fetcher


@pytest.mark.parametrize(
    ("port_name", "accessor", "vertex_type"),
    [
        ("port-in-1", "vertex_in", "In"),
        ("port-out-1", "vertex_out", "Out"),
        ("port-internal-1", "vertex_internal", "Internal"),
        ("port-bidi-1", "vertex_bidirectional", "BiDirectional"),
    ],
)
def test_single_vertex_port_exposes_only_its_type(
    snap: tuple[InspectSnapshot, FakeFetcher], port_name: str, accessor: str, vertex_type: str
) -> None:
    port = _port(snap[0], port_name)

    accessors = {name: getattr(port, name) for name in _ACCESSORS}

    assert port.is_bidirectional is False
    assert accessors[accessor] is not None
    assert accessors[accessor].id == f"{_DEVICE}.0.{port_name}"
    assert accessors[accessor].vertex_type == vertex_type
    assert all(vertex is None for name, vertex in accessors.items() if name != accessor)
    assert [vertex.id for vertex in port.vertices] == [f"{_DEVICE}.0.{port_name}"]


def test_double_port_keeps_out_and_in_and_has_no_single_bidirectional(
    snap: tuple[InspectSnapshot, FakeFetcher],
) -> None:
    port = _port(snap[0], "port-double-1")

    assert port.is_bidirectional is True
    assert port.vertex_out is not None and port.vertex_out.id == f"{_DEVICE}.0.port-double-1.out"
    assert port.vertex_in is not None and port.vertex_in.id == f"{_DEVICE}.0.port-double-1.in"
    assert port.vertex_internal is None
    assert port.vertex_bidirectional is None
    assert {vertex.id for vertex in port.vertices} == {
        f"{_DEVICE}.0.port-double-1.out",
        f"{_DEVICE}.0.port-double-1.in",
    }


def test_undecided_vertex_is_reachable_via_vertices(snap: tuple[InspectSnapshot, FakeFetcher]) -> None:
    port = _port(snap[0], "port-undecided-1")

    assert all(getattr(port, name) is None for name in _ACCESSORS)
    assert [vertex.vertex_type for vertex in port.vertices] == ["Undecided"]


def test_vertices_batches_the_lookup(snap: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snapshot, fetcher = snap
    port = _port(snapshot, "port-double-1")
    fetcher.vertex_lookup_calls.clear()

    _ = port.vertices

    assert len(fetcher.vertex_lookup_calls) == 1
    assert set(fetcher.vertex_lookup_calls[0]) == {
        f"{_DEVICE}.0.port-double-1.out",
        f"{_DEVICE}.0.port-double-1.in",
    }


def test_filter_ports_bidirectional_matches_single_and_double(snap: tuple[InspectSnapshot, FakeFetcher]) -> None:
    device = snap[0].get_device(_DEVICE)
    assert device is not None

    matches = {port.label: port.is_bidirectional for port in device.filter_ports(vertex_type="BiDirectional")}

    assert matches == {"port-bidi-1": False, "port-double-1": True}


_ACCESSORS = ("vertex_in", "vertex_out", "vertex_internal", "vertex_bidirectional")


def _port(snapshot: InspectSnapshot, name: str) -> InspectPort:
    port = snapshot.get_port(_DEVICE, f"{_DEVICE}.dev.0.{name}")
    assert port is not None
    return port


def _vertex_type_node() -> InspectApiNodeStatusItem:
    """One module with a single In / Out / Internal / BiDirectional / Undecided port and a double port."""

    def single(name: str, vertex_type: str) -> dict:
        return _single_vertex_info(f"{_DEVICE}.0.{name}", vertex_type, active=True, controlled=True, endpoint=False)

    vertex_infos = {
        "port-in-1": single("port-in-1", "In"),
        "port-out-1": single("port-out-1", "Out"),
        "port-internal-1": single("port-internal-1", "Internal"),
        "port-bidi-1": single("port-bidi-1", "BiDirectional"),
        "port-undecided-1": single("port-undecided-1", "Undecided"),
        "port-double-1": {
            "type": "double",
            "out": {"type": "single", "id": f"{_DEVICE}.0.port-double-1.out", "fields": {}},
            "in": {"type": "single", "id": f"{_DEVICE}.0.port-double-1.in", "fields": {}},
        },
    }
    ports = {
        f"{_DEVICE}.dev.0.{name}": {
            "pid": f"{_DEVICE}.dev.0.{name}",
            "descriptor": {"label": name},
            "vertexInfo": info,
        }
        for name, info in vertex_infos.items()
    }
    return InspectApiNodeStatusItem.model_validate(
        {
            "_id": _DEVICE,
            "_vid": _DEVICE,
            "deviceId": _DEVICE,
            "descriptor": {"desc": "", "label": "LEAF-A"},
            "fDescriptor": {"desc": "", "label": "LEAF-A-factory"},
            "modules": {
                f"{_DEVICE}.dev.0": {"pid": f"{_DEVICE}.dev.0", "descriptor": {"label": "Slot 0"}, "ports": ports}
            },
        }
    )
