"""Concise, side-effect-free __repr__/__str__ for Inspect developer-facing classes."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from videoipath_automation_tool.apps.inspect.domain.alarm import InspectAlarm
from videoipath_automation_tool.apps.inspect.domain.device import InspectDevice, VirtualDeviceSpec
from videoipath_automation_tool.apps.inspect.domain.module import VirtualModuleSpec
from videoipath_automation_tool.apps.inspect.domain.port import InspectPortTemplate, PortFromTemplate
from videoipath_automation_tool.apps.inspect.domain.vertex import InspectVertex
from videoipath_automation_tool.apps.inspect.model.alarms import InspectApiAlarmItem
from videoipath_automation_tool.apps.inspect.model.collector import InspectApiSingleVertexInfo
from videoipath_automation_tool.apps.inspect.snapshot import InspectSnapshot
from videoipath_automation_tool.apps.inspect.transaction import CommitResult, InspectTransaction

from .conftest import load_fixture
from .test_snapshot import FakeFetcher


def _assert_clean_repr(obj: object, *, class_name: str, contains: str) -> str:
    text = repr(obj)
    assert text.startswith(f"{class_name}(")
    assert contains in text
    assert "InspectSnapshot object" not in text
    assert "path_item=" not in text
    assert "_items" not in text
    assert str(obj) == text
    return text


@pytest.fixture
def snap() -> tuple[InspectSnapshot, FakeFetcher]:
    fetcher = FakeFetcher()
    snapshot = InspectSnapshot(
        fetcher=fetcher,
        device_items=fetcher.get_device_skeleton(),
        edge_items=fetcher.get_edge_skeleton(),
    )
    fetcher.skeleton_calls = 0
    return snapshot, fetcher


def test_device_repr_is_concise_and_does_not_hydrate(snap: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snapshot, fetcher = snap
    device = snapshot.get_device("leaf-a")
    assert device is not None
    text = _assert_clean_repr(device, class_name="InspectDevice", contains="leaf-a")
    assert "label='LEAF-A'" in text
    assert "virtual=" not in text
    assert device.is_hydrated is False
    assert fetcher.device_detail_calls == []


def test_device_repr_marks_virtual_id() -> None:
    fetcher = FakeFetcher()
    snapshot = InspectSnapshot(fetcher=fetcher, device_items=[], edge_items=[])
    device = InspectDevice(snapshot=snapshot, id="virtual.2")
    text = repr(device)
    assert text.startswith("InspectDevice(")
    assert "id='virtual.2'" in text
    assert "virtual=True" in text
    assert str(device) == text


def test_device_repr_survives_missing_record(snap: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snapshot, _ = snap
    device = snapshot.get_device("leaf-a")
    assert device is not None
    snapshot._devices_by_id.pop("leaf-a")
    text = repr(device)
    assert text.startswith("InspectDevice(")
    assert "id='leaf-a'" in text
    assert "label=" not in text
    assert str(device) == text


def test_port_module_edge_service_vertex_reprs(snap: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snapshot, _ = snap
    device = snapshot.get_device("leaf-a")
    assert device is not None

    ports = device.ports
    assert ports
    port = ports[0]
    _assert_clean_repr(port, class_name="InspectPort", contains=port.id or "")
    assert f"device='{port.indexed.device_id}'" in repr(port)

    modules = device.modules
    assert modules
    module = modules[0]
    text = _assert_clean_repr(module, class_name="InspectModule", contains=module.id)
    assert "device='leaf-a'" in text

    edge = snapshot.edges[0]
    text = _assert_clean_repr(edge, class_name="InspectEdge", contains=edge.id)
    assert "from_device=" in text and "to_device=" in text

    services = snapshot.services
    assert services
    service = services[0]
    text = _assert_clean_repr(service, class_name="InspectService", contains=service.booking_id)
    assert "path_item=" not in text

    vertex = port._offline_vertices()[0]
    text = _assert_clean_repr(vertex, class_name="InspectVertex", contains=vertex.id)
    assert "type=" in text


def test_typed_vertex_repr_uses_subclass_name(snap: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snapshot, _ = snap
    vertex = snapshot.get_vertex("leaf-a.0.up1")
    assert vertex is not None
    text = _assert_clean_repr(vertex, class_name="InspectIpVertex", contains=vertex.id)
    assert text.startswith("InspectIpVertex(")


def test_snapshot_repr(snap: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snapshot, _ = snap
    text = _assert_clean_repr(snapshot, class_name="InspectSnapshot", contains="devices=2")
    assert "edge_pairs=1" in text


def test_internal_index_record_reprs(snap: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snapshot, _ = snap
    device = snapshot.get_device("leaf-a")
    assert device is not None
    _ = device.ports

    record = snapshot.get_device_record("leaf-a")
    assert record is not None
    text = _assert_clean_repr(record, class_name="_DeviceRecord", contains="leaf-a")
    assert "level=" in text

    indexed_port = snapshot._ports_by_device_id["leaf-a"][0]
    text = _assert_clean_repr(indexed_port, class_name="_IndexedPort", contains="leaf-a")
    assert "port_id=" in text

    indexed_edge = snapshot._edges_by_device_id["leaf-a"][0]
    text = _assert_clean_repr(indexed_edge, class_name="_IndexedEdge", contains=indexed_edge.edge_id)
    assert "from_device_id=" in text


def test_builder_reprs() -> None:
    port = PortFromTemplate(template_id="tpl-a", count=3)
    text = _assert_clean_repr(port, class_name="PortFromTemplate", contains="tpl-a")
    assert "count=3" in text

    module = VirtualModuleSpec(ports=[port], module_number=1)
    text = _assert_clean_repr(module, class_name="VirtualModuleSpec", contains="ports=1")
    assert "module_number=1" in text

    device_spec = VirtualDeviceSpec(modules=[module, VirtualModuleSpec()])
    text = _assert_clean_repr(device_spec, class_name="VirtualDeviceSpec", contains="modules=2")

    template = InspectPortTemplate(id="tpl-a", label="Port A", kind="ip", direction="Out", vertex={"type": "ip"})
    text = _assert_clean_repr(template, class_name="InspectPortTemplate", contains="tpl-a")
    assert "vertex=" not in text
    assert "kind='ip'" in text


def test_alarm_repr_truncates_long_message() -> None:
    item = InspectApiAlarmItem.model_validate(
        load_fixture("alarms_current.json")["data"]["status"]["alarms"]["current"]["_items"][0]
    )
    alarm = InspectAlarm(item=item)
    text = _assert_clean_repr(alarm, class_name="InspectAlarm", contains=alarm.id or "")
    assert "severity=" in text
    assert "message=" in text

    long_details = "x" * 80
    long_item = InspectApiAlarmItem.model_validate(
        {
            "_id": "alarm-long",
            "info": {"details": long_details, "severity": 3},
        }
    )
    long_alarm = InspectAlarm(item=long_item)
    text = repr(long_alarm)
    assert "…" in text
    assert long_details not in text


def test_transaction_and_commit_result_reprs() -> None:
    tx = InspectTransaction(api=SimpleNamespace())
    text = _assert_clean_repr(tx, class_name="InspectTransaction", contains="staged=0")
    assert "committed=" not in text
    assert "discarded=" not in text

    tx._committed = True
    assert "committed=True" in repr(tx)

    result = CommitResult(applied_ids=["device-a", "device-b"], created_ids=["virtual.1"])
    text = _assert_clean_repr(result, class_name="CommitResult", contains="applied=2")
    assert "created=1" in text
    assert "response=" not in text


def test_format_repr_skips_failing_callables() -> None:
    from videoipath_automation_tool.apps.inspect.model.common import format_repr

    class _Probe:
        pass

    text = format_repr(_Probe(), id="a", label=lambda: (_ for _ in ()).throw(RuntimeError("boom")), extra=None)
    assert text == "_Probe(id='a')"


def test_offline_vertex_repr_without_lookup(snap: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snapshot, fetcher = snap
    info = InspectApiSingleVertexInfo.model_validate({"id": "leaf-a.0.up1", "vertexType": "Out"})
    vertex = InspectVertex(snapshot=snapshot, id="leaf-a.0.up1", vertex_info=info)
    text = _assert_clean_repr(vertex, class_name="InspectVertex", contains="leaf-a.0.up1")
    assert "type='Out'" in text
    assert fetcher.vertex_lookup_calls == []
