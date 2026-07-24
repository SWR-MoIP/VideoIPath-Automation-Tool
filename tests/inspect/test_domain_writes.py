"""Writable domain objects + app.inspect.update() cascade (offline)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from videoipath_automation_tool.apps.inspect.app.write import InspectWriteMixin
from videoipath_automation_tool.apps.inspect.domain.edge import InspectEdge
from videoipath_automation_tool.apps.inspect.domain.vertex import InspectCodecVertex, InspectIpVertex, build_vertex
from videoipath_automation_tool.apps.inspect.model.actions import (
    InspectApiLookupEdgeResponseItem,
    InspectApiLookupInspectDeviceResponse,
    InspectApiLookupVertexResponseData,
)
from videoipath_automation_tool.apps.inspect.model.update_topology import InspectApiUpdateTopologyResponse
from videoipath_automation_tool.apps.inspect.snapshot import InspectSnapshot, _IndexedEdge, _STAGED_MISSING
from videoipath_automation_tool.apps.inspect.transaction import InspectTransaction

from .conftest import load_fixture

_OK_HEADER = {
    "auth": True,
    "caption": "OK",
    "code": "OK",
    "errorCodes": [],
    "errorDetails": [],
    "id": "0",
    "msg": [],
    "ok": True,
    "user": "api-user",
}

CODEC_ID = "device-a.module-1.port-out-1.out"
DEVICE_ID = "device-a"
EDGE_ID = "device-a.1.p1.out::device-b.1.p1.in"


def test_vertex_setter_stages_and_reads_own_writes() -> None:
    snapshot = InspectSnapshot()
    vertex = build_vertex(snapshot, "device-a.1.v1", kind="generic", port_factory_label="Port A")
    assert vertex.factory_label == "Port A"
    assert vertex.label is None

    vertex.label = "new-label"
    vertex.use_as_endpoint = True
    vertex.tags = ["Video~~T"]

    assert vertex.label == "new-label"
    assert vertex.use_as_endpoint is True
    assert vertex.tags == ["Video~~T"]
    staged = snapshot.get_staged_edits("vertex", "device-a.1.v1")
    assert staged["label"] == "new-label"
    assert staged["useAsEndpoint"] is True
    assert staged["localAssignedTags"] == ["Video~~T"]


def test_codec_vertex_nested_setters() -> None:
    snapshot = InspectSnapshot()
    fixture = load_fixture("lookup_inspect_codec_vertex_by_id.json")
    snapshot._vertex_details[CODEC_ID] = InspectApiLookupVertexResponseData.model_validate(fixture["data"])
    vertex = build_vertex(snapshot, CODEC_ID, kind="codec", port_factory_label="TX  #1")
    assert isinstance(vertex, InspectCodecVertex)

    assert vertex.sdp_support is True
    vertex.sdp_support = False
    vertex.main_destination_port = 50311
    assert vertex.sdp_support is False
    assert vertex.main_destination_port == 50311

    staged = snapshot.get_staged_edits("vertex", CODEC_ID)
    assert staged["typeFields.specific.sdpSupport"] is False
    assert staged["typeFields.generic.mainDstInfo.port"] == 50311


def test_ip_vertex_supports_static_igmp_alias() -> None:
    snapshot = InspectSnapshot()
    vertex = build_vertex(snapshot, "device-a.SwitchingCore", kind="ip")
    assert isinstance(vertex, InspectIpVertex)
    vertex.supports_static_igmp_config = True
    assert vertex.supports_static_igmp is True
    assert snapshot.get_staged_value("vertex", "device-a.SwitchingCore", "typeFields.supportsStaticIgmpCfg") is True


def test_control_setter_warns() -> None:
    snapshot = InspectSnapshot()
    vertex = build_vertex(snapshot, "device-a.1.v1", kind="codec")
    with pytest.warns(UserWarning, match="best-effort"):
        vertex.control = "full"
    assert snapshot.get_staged_value("vertex", "device-a.1.v1", "control") == "full"


def test_device_setters_stage_descriptor_and_icon() -> None:
    snapshot = _skeleton_snapshot_with_device(DEVICE_ID, label="Old")
    device = snapshot.get_device(DEVICE_ID)
    assert device is not None
    device.label = "New Label"
    device.icon_type = "gateway"
    device.tags = ["#SITE"]
    device.coordinates = {"x": 10.0, "y": 20.0}

    assert device.label == "New Label"
    assert device.icon_type == "gateway"
    assert device.tags == ["#SITE"]
    assert device.coordinates == {"x": 10.0, "y": 20.0}
    staged = snapshot.get_staged_edits("device", DEVICE_ID)
    assert staged["descriptor.label"] == "New Label"
    assert staged["iconType"] == "gateway"
    assert staged["coordinates"] == {"x": 10.0, "y": 20.0}


def test_update_device_cascades_vertex_edits() -> None:
    api = FakeAPI()
    api.devices[DEVICE_ID] = _device_response()
    codec_fixture = load_fixture("lookup_inspect_codec_vertex_by_id.json")
    api.vertices[CODEC_ID] = InspectApiLookupVertexResponseData.model_validate(codec_fixture["data"])

    snapshot = _skeleton_snapshot_with_device(DEVICE_ID)
    snapshot._vertex_details[CODEC_ID] = api.vertices[CODEC_ID]
    snapshot._fetcher = api  # type: ignore[assignment]

    device = snapshot.get_device(DEVICE_ID)
    assert device is not None
    device.label = "Synced"
    vertex = build_vertex(snapshot, CODEC_ID, kind="codec")
    assert isinstance(vertex, InspectCodecVertex)
    vertex.sdp_support = True
    vertex.main_destination_port = 50311

    app = _WriteApp(api, snapshot)
    result = app.update(device)
    assert result.ok
    assert len(api.update_calls) == 1
    delta = api.update_calls[0]
    assert DEVICE_ID in delta.replaceDevices
    assert delta.replaceDevices[DEVICE_ID].descriptor.label == "Synced"
    assert CODEC_ID in delta.replaceVertices
    form = delta.replaceVertices[CODEC_ID]
    assert (
        form.typeFields.specific["sdpSupport"] is True
        or getattr(form.typeFields, "specific", {}).get("sdpSupport") is True
        or _nested_get(form, "typeFields.specific.sdpSupport") is True
    )
    # Pending edits cleared after commit.
    assert snapshot.get_staged_edits("device", DEVICE_ID) == {}
    assert snapshot.get_staged_edits("vertex", CODEC_ID) == {}


def test_transaction_update_stages_domain_edits() -> None:
    api = FakeAPI()
    api.devices[DEVICE_ID] = _device_response()
    snapshot = _skeleton_snapshot_with_device(DEVICE_ID)
    device = snapshot.get_device(DEVICE_ID)
    assert device is not None
    device.label = "Via Tx"

    app = _WriteApp(api, snapshot)
    with app.transaction() as tx:
        returned = tx.update(device)
        assert returned is tx
        tx.commit()
    assert api.update_calls[0].replaceDevices[DEVICE_ID].descriptor.label == "Via Tx"


def test_transaction_codec_nested_intents_round_trip() -> None:
    api = FakeAPI()
    codec_fixture = load_fixture("lookup_inspect_codec_vertex_by_id.json")
    api.vertices[CODEC_ID] = InspectApiLookupVertexResponseData.model_validate(codec_fixture["data"])
    with InspectTransaction(api) as tx:
        tx.update_vertex(CODEC_ID, sdp_support=False, main_destination_port=50311)
        tx.commit()
    form = api.update_calls[0].replaceVertices[CODEC_ID]
    specific = getattr(form.typeFields, "specific")
    generic = getattr(form.typeFields, "generic")
    if isinstance(specific, dict):
        assert specific["sdpSupport"] is False
    else:
        assert specific.sdpSupport is False
    if isinstance(generic, dict):
        assert generic["mainDstInfo"]["port"] == 50311
        assert generic["mainDstInfo"]["ip"] == "10.0.0.1"  # untouched leaf preserved
    else:
        assert generic.mainDstInfo["port"] == 50311


def test_edge_setters_stage_weight_factors() -> None:
    from videoipath_automation_tool.apps.inspect.model.collector import InspectApiExternalEdgeStatus

    snapshot = InspectSnapshot()
    indexed = _IndexedEdge(
        edge_id=EDGE_ID,
        pair_id="device-a::device-b",
        edge=InspectApiExternalEdgeStatus(id=EDGE_ID),
        pair_status=None,
        primary_device_id="device-a",
        secondary_device_id="device-b",
        from_device_id="device-a",
        from_port_id="p1",
        to_device_id="device-b",
        to_port_id="p1",
    )
    edge = InspectEdge(snapshot=snapshot, indexed=indexed)
    edge.weight = 42
    edge.bandwidth_weight_factor = 3
    assert edge.weight == 42
    assert edge.bandwidth_weight_factor == 3
    staged = snapshot.get_staged_edits("edge", EDGE_ID)
    assert staged["weight"] == 42
    assert staged["weightFactors.bandwidth.weight"] == 3


MODULE_ID = "device-a.dev.0"


def test_module_tags_setter_stages_and_reads_own_writes() -> None:
    snapshot = _snapshot_with_module(DEVICE_ID, MODULE_ID, local_tags=["Format~~A"])
    module = snapshot.get_module(DEVICE_ID, MODULE_ID)
    assert module is not None
    assert module.tags == ["Format~~A"]

    module.tags = ["Format~~B", "Format~~C"]
    assert module.tags == ["Format~~B", "Format~~C"]
    assert snapshot.get_staged_edits("module", MODULE_ID)["tags"] == ["Format~~B", "Format~~C"]


def test_update_module_diffs_assign_and_unassign() -> None:
    api = FakeAPI()
    snapshot = _snapshot_with_module(DEVICE_ID, MODULE_ID, local_tags=["Format~~Keep", "Format~~Old"])
    app = _WriteApp(api, snapshot)

    result = app.update_module(MODULE_ID, tags=["Format~~Keep", "Format~~New"])
    assert result.ok
    assert result.response is None
    assert api.update_calls == []
    assert api.assign_calls == [("Format~~New", ["device:device-a.dev.0"])]
    assert api.unassign_calls == [("Format~~Old", ["device:device-a.dev.0"])]


def test_update_module_noop_when_tags_unchanged() -> None:
    api = FakeAPI()
    snapshot = _snapshot_with_module(DEVICE_ID, MODULE_ID, local_tags=["Format~~A"])
    app = _WriteApp(api, snapshot)

    result = app.update_module(MODULE_ID, tags=["Format~~A"])
    assert result.ok
    assert api.assign_calls == []
    assert api.unassign_calls == []


def test_update_module_via_domain_object() -> None:
    api = FakeAPI()
    snapshot = _snapshot_with_module(DEVICE_ID, MODULE_ID, local_tags=[])
    module = snapshot.get_module(DEVICE_ID, MODULE_ID)
    assert module is not None
    module.tags = ["Format~~V_720p60"]

    app = _WriteApp(api, snapshot)
    result = app.update(module)
    assert result.ok
    assert api.assign_calls == [("Format~~V_720p60", ["device:device-a.dev.0"])]
    assert snapshot.get_staged_edits("module", MODULE_ID) == {}


def test_update_device_cascades_module_tag_edits() -> None:
    api = FakeAPI()
    api.devices[DEVICE_ID] = _device_response()
    snapshot = _snapshot_with_module(DEVICE_ID, MODULE_ID, local_tags=["Format~~Old"])
    device = snapshot.get_device(DEVICE_ID)
    assert device is not None
    device.label = "Synced"
    module = snapshot.get_module(DEVICE_ID, MODULE_ID)
    assert module is not None
    module.tags = ["Format~~New"]

    app = _WriteApp(api, snapshot)
    result = app.update(device)
    assert result.ok
    assert len(api.update_calls) == 1
    assert api.update_calls[0].replaceDevices[DEVICE_ID].descriptor.label == "Synced"
    assert api.assign_calls == [("Format~~New", ["device:device-a.dev.0"])]
    assert api.unassign_calls == [("Format~~Old", ["device:device-a.dev.0"])]
    assert snapshot.get_staged_edits("module", MODULE_ID) == {}


# --- Internal ---


def _nested_get(obj: Any, path: str) -> Any:
    cur = obj
    for part in path.split("."):
        if cur is None:
            return _STAGED_MISSING
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            cur = getattr(cur, part, None)
    return cur


def _skeleton_snapshot_with_device(device_id: str, label: str = "Device A") -> InspectSnapshot:
    from videoipath_automation_tool.apps.inspect.model.collector import InspectApiNodeStatusItem

    node = InspectApiNodeStatusItem.model_validate(
        {
            "_id": device_id,
            "deviceId": device_id,
            "label": label,
            "desc": "",
            "tags": [],
            "meta": {"iconType": "default", "iconSize": "medium", "coordinates": {"x": 0, "y": 0}},
            "status": {"sa": 0, "severity": 0},
        }
    )
    return InspectSnapshot(device_items=[node])


def _snapshot_with_module(
    device_id: str,
    module_id: str,
    *,
    local_tags: list[str] | None = None,
    all_tags: list[str] | None = None,
) -> InspectSnapshot:
    from videoipath_automation_tool.apps.inspect.model.collector import InspectApiModuleStatus
    from videoipath_automation_tool.apps.inspect.snapshot import HydrationLevel

    snapshot = _skeleton_snapshot_with_device(device_id)
    local_tags = list(local_tags or [])
    all_tags = list(all_tags) if all_tags is not None else list(local_tags)
    status = InspectApiModuleStatus.model_validate(
        {
            "_id": module_id,
            "pid": module_id,
            "label": "Module 0",
            "tagsInfo": {
                "assigned": {
                    "all": all_tags,
                    "inherited": {},
                    "inheritedConflict": False,
                    "local": {tag: {"label": tag, "path": []} for tag in local_tags},
                }
            },
        }
    )
    snapshot._modules_by_device_id[device_id] = {module_id: status}
    record = snapshot._devices_by_id[device_id]
    record.level = HydrationLevel.FULL
    return snapshot


def _device_response(label: str = "Device A") -> InspectApiLookupInspectDeviceResponse:
    return InspectApiLookupInspectDeviceResponse.model_validate(
        {
            "data": {
                "assignedTags": {"all": [], "inherited": {}, "inheritedConflict": False, "local": {}},
                "fields": {
                    "coordinates": {"x": 0, "y": 0},
                    "descriptor": {"desc": "", "label": label},
                    "iconSize": "medium",
                    "iconType": "default",
                    "localAssignedTags": [],
                    "sdpStrategy": None,
                    "siteId": None,
                    "tags": [],
                    "virtualDeviceFields": None,
                },
            },
            "header": _OK_HEADER,
        }
    )


class FakeAPI:
    def __init__(self) -> None:
        self.devices: dict[str, InspectApiLookupInspectDeviceResponse] = {}
        self.vertices: dict[str, InspectApiLookupVertexResponseData] = {}
        self.edges: dict[str, InspectApiLookupEdgeResponseItem] = {}
        self.update_response = InspectApiUpdateTopologyResponse.model_validate(
            load_fixture("update_topology_success.json")
        )
        self.update_calls: list[Any] = []
        self.assign_calls: list[tuple[str, list[str]]] = []
        self.unassign_calls: list[tuple[str, list[str]]] = []

    def lookup_inspect_device(self, device_id: str) -> InspectApiLookupInspectDeviceResponse:
        if device_id not in self.devices:
            raise KeyError(device_id)
        return self.devices[device_id]

    def lookup_vertices(self, ids: list[str]) -> SimpleNamespace:
        return SimpleNamespace(data={i: self.vertices[i] for i in ids if i in self.vertices})

    def lookup_edges(self, ids: list[str]) -> SimpleNamespace:
        return SimpleNamespace(data={i: self.edges[i] for i in ids if i in self.edges})

    def update_topology(self, delta: Any) -> InspectApiUpdateTopologyResponse:
        self.update_calls.append(delta)
        return self.update_response

    def assign_tag(self, tag_id: str, element_ids: list[str]) -> SimpleNamespace:
        self.assign_calls.append((tag_id, list(element_ids)))
        return _ok_simple_action()

    def unassign_tag(self, tag_id: str, element_ids: list[str]) -> SimpleNamespace:
        self.unassign_calls.append((tag_id, list(element_ids)))
        return _ok_simple_action()


def _ok_simple_action() -> SimpleNamespace:
    return SimpleNamespace(
        header=SimpleNamespace(ok=True, msg=[]),
        data=SimpleNamespace(ok=True, msg=[]),
    )


class _WriteApp(InspectWriteMixin):
    def __init__(self, api: FakeAPI, snapshot: InspectSnapshot) -> None:
        self._inspect_api = api  # type: ignore[assignment]
        self._logger = __import__("logging").getLogger("test")
        self._snapshot = snapshot
