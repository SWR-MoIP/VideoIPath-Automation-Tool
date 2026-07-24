"""Virtual device / port-template domain, wire, and actions tests."""

from __future__ import annotations

import logging
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import pytest

from videoipath_automation_tool.apps.inspect.app.actions import InspectActionsMixin
from videoipath_automation_tool.apps.inspect.app.write import InspectWriteMixin
from videoipath_automation_tool.apps.inspect.api import InspectAPI
from videoipath_automation_tool.apps.inspect.domain.device import InspectDevice, VirtualDeviceSpec
from videoipath_automation_tool.apps.inspect.domain.port import (
    InspectPortTemplate,
    PortFromTemplate,
    _ports_to_count_by_template,
)
from videoipath_automation_tool.apps.inspect.errors import InspectError
from videoipath_automation_tool.apps.inspect.model.actions import (
    InspectApiLookupInspectDeviceFields,
    InspectApiLookupInspectDeviceResponse,
)
from videoipath_automation_tool.apps.inspect.model.collector import InspectApiNodeStatusItem
from videoipath_automation_tool.apps.inspect.model.update_topology import InspectApiUpdateTopologyResponse
from videoipath_automation_tool.apps.inspect.model.virtual import (
    InspectApiAddVirtualTopologyData,
    InspectApiUpdateVirtualInstancesData,
    InspectApiUpdateVirtualInstancesResponse,
    InspectApiUpdateVirtualTemplatesData,
    InspectApiVirtualDeviceInstance,
    InspectApiVirtualTemplateItem,
)
from videoipath_automation_tool.apps.inspect.snapshot import InspectSnapshot


def test_virtual_templates_fixture_parses(load: Callable[[str], dict[str, Any]]) -> None:
    items = load("virtual_templates.json")["data"]["status"]["network"]["virtualTemplates"]["_items"]
    templates = [InspectApiVirtualTemplateItem.model_validate(item) for item in items]
    assert templates[0].id == "generic_bidir"
    assert templates[0].vertex.type == "genericVertex"
    assert templates[1].id == "video_in"
    assert templates[1].vertex.codecFormat == "Video"


def test_virtual_devices_fixture_parses(load: Callable[[str], dict[str, Any]]) -> None:
    items = load("virtual_devices.json")["data"]["status"]["network"]["virtualDevices"]["_items"]
    devices = [InspectApiVirtualDeviceInstance.model_validate(item) for item in items]
    assert devices[0].id == "virtual.1"
    assert devices[0].modules[0].vertices[0].templateId == "ip_in"
    assert devices[1].modules == []


def test_update_virtual_instances_create_response_parses(load: Callable[[str], dict[str, Any]]) -> None:
    resp = InspectApiUpdateVirtualInstancesResponse.model_validate(load("update_virtual_instances_create.json"))
    assert resp.data.addedDeviceLabels == {"virtual.1": "Virtual Device 1"}
    assert resp.data.res.ok is True
    assert resp.data.validation.result.ok is True


def test_lookup_virtual_device_fields_typed(load: Callable[[str], dict[str, Any]]) -> None:
    resp = InspectApiLookupInspectDeviceResponse.model_validate(load("lookup_inspect_virtual_device.json"))
    fields = resp.data.fields.virtualDeviceFields
    assert fields is not None
    assert fields.dynamic[0].moduleNumber == 0
    assert fields.dynamic[0].vertices[0].templateId == "generic_bidir"
    assert fields.manual == []
    assert resp.data.fields.coordinates is None


def test_virtual_device_edit_form_round_trips_virtual_device_fields(
    load: Callable[[str], dict[str, Any]],
) -> None:
    """replaceDevices can round-trip a virtual device's lookup form including virtualDeviceFields."""
    raw_fields = load("lookup_inspect_virtual_device.json")["data"]["fields"]
    fields = InspectApiLookupInspectDeviceFields.model_validate(raw_fields)
    dumped = fields.model_dump(mode="json", by_alias=True)
    assert dumped["virtualDeviceFields"] == raw_fields["virtualDeviceFields"]
    assert dumped["descriptor"]["label"] == "Virtual Device 1"


def test_spec_to_wire_matches_ui_payload() -> None:
    spec = (
        VirtualDeviceSpec.empty()
        .add_port("video_in", count=2)
        .add_port("video_out", count=2)
        .add_module()
        .add_port("ip_in")
    )
    wire = spec.to_wire()
    payload = wire.model_dump(mode="json", by_alias=True)
    assert payload == {
        "modules": [
            {
                "moduleNumber": None,
                "vertices": [
                    {"templateId": "video_in", "count": 2},
                    {"templateId": "video_out", "count": 2},
                ],
            },
            {
                "moduleNumber": None,
                "vertices": [{"templateId": "ip_in", "count": 1}],
            },
        ]
    }


def test_spec_from_ports() -> None:
    spec = VirtualDeviceSpec.from_ports("ip_in", ("ip_out", 2), PortFromTemplate(template_id="video_in", count=1))
    assert [p.template_id for p in spec.modules[0].ports] == ["ip_in", "ip_out", "video_in"]
    assert spec.modules[0].ports[1].count == 2


def test_port_template_domain_summary(load: Callable[[str], dict[str, Any]]) -> None:
    items = load("virtual_templates.json")["data"]["status"]["network"]["virtualTemplates"]["_items"]
    template = InspectPortTemplate.from_wire(InspectApiVirtualTemplateItem.model_validate(items[1]))
    assert template.id == "video_in"
    assert template.label == "Video in"
    assert template.kind == "codecVertex"
    assert template.direction == "In"
    assert template.codec_format == "Video"


def test_ports_to_count_by_template_merges_lists() -> None:
    assert _ports_to_count_by_template(
        [PortFromTemplate(template_id="video_in", count=2), PortFromTemplate(template_id="video_in", count=3)]
    ) == {"video_in": 5}
    assert _ports_to_count_by_template({"ip_out": 1}) == {"ip_out": 1}


def test_create_virtual_devices_returns_inspect_devices(load: Callable[[str], dict[str, Any]]) -> None:
    create = load("update_virtual_instances_create.json")["data"]
    app = _App(post_data=create, skeleton_nodes=[_virtual_skeleton_node("virtual.1", "Virtual Device 1")])
    devices = app.create_virtual_devices(VirtualDeviceSpec.from_ports("generic_bidir"), copies=2)
    assert len(devices) == 1
    assert isinstance(devices[0], InspectDevice)
    assert devices[0].id == "virtual.1"
    assert devices[0].is_virtual is True
    assert devices[0].label == "Virtual Device 1"
    url, payload = app._inspect_api.vip_connector.rest.post_calls[0]
    assert url.endswith("/network/updateVirtualInstances")
    assert len(payload["data"]["add"]) == 2
    assert payload["data"]["add"][0]["modules"][0]["vertices"] == [{"templateId": "generic_bidir", "count": 1}]
    assert app._snapshot.upsert_calls == [["virtual.1"]]


def test_create_virtual_device_singular(load: Callable[[str], dict[str, Any]]) -> None:
    app = _App(
        post_data=load("update_virtual_instances_create.json")["data"],
        skeleton_nodes=[_virtual_skeleton_node("virtual.1", "Virtual Device 1")],
    )
    device = app.create_virtual_device(VirtualDeviceSpec.empty())
    assert device.id == "virtual.1"
    assert device.is_virtual is True


def test_create_virtual_device_raises_on_failure() -> None:
    app = _App(
        post_data={
            "addedDeviceLabels": {},
            "res": {"msg": ["boom"], "ok": False},
            "validation": {"createIds": [], "details": {}, "result": {"msg": [], "ok": True}},
        },
        skeleton_nodes=[],
    )
    with pytest.raises(InspectError):
        app.create_virtual_device(VirtualDeviceSpec.empty())


def test_remove_device_from_topology_uses_update_topology_for_virtual(
    load: Callable[[str], dict[str, Any]],
) -> None:
    """Virtual device removal uses the normal updateTopology path (verified 2025.4.9)."""
    api = _FakeWriteAPI(load("update_topology_success.json"))
    app = _WriteApp(api)
    result = app.remove_device_from_topology("virtual.1")
    assert result.ok is True
    assert len(api.update_calls) == 1
    assert api.update_calls[0].remove == ["virtual.1"]
    assert api.virtual_instance_calls == []


def test_transaction_remove_virtual_and_physical_uses_update_topology(
    load: Callable[[str], dict[str, Any]],
) -> None:
    api = _FakeWriteAPI(load("update_topology_success.json"))
    app = _WriteApp(api)
    with app.transaction() as tx:
        tx.remove_device("virtual.1")
        tx.remove_device("device5")
        result = tx.commit(check_conflicts=False)
    assert result.ok is True
    assert len(api.update_calls) == 1
    assert set(api.update_calls[0].remove) == {"virtual.1", "device5"}
    assert api.virtual_instance_calls == []


def test_add_virtual_ports() -> None:
    app = _App(post_data={"msg": [], "ok": True}, skeleton_nodes=[])
    assert app.add_virtual_ports("virtual.1", 0, {"ip_out": 1}) is True
    url, payload = app._inspect_api.vip_connector.rest.post_calls[0]
    assert url.endswith("/network/addVirtualTopology")
    assert payload["data"] == {
        "deviceId": "virtual.1",
        "moduleId": 0,
        "countByVertexTemplate": {"ip_out": 1},
    }


def test_port_template_crud_payloads() -> None:
    app = _App(post_data={"msg": [], "ok": True}, skeleton_nodes=[])
    assert app.create_port_template("example_tpl", "Example", {"type": "genericVertex", "vertexType": "In"}) is True
    assert app.delete_port_templates(["example_tpl"]) is True
    add_payload = app._inspect_api.vip_connector.rest.post_calls[0][1]["data"]
    assert add_payload["add"]["example_tpl"]["label"] == "Example"
    remove_payload = app._inspect_api.vip_connector.rest.post_calls[1][1]["data"]
    assert remove_payload["remove"] == ["example_tpl"]


def test_list_port_templates(load: Callable[[str], dict[str, Any]]) -> None:
    app = _App(
        get_data=load("virtual_templates.json")["data"],
        post_data={"msg": [], "ok": True},
        skeleton_nodes=[],
    )
    templates = app.list_port_templates()
    assert [t.id for t in templates] == ["generic_bidir", "video_in"]


def test_invalid_inputs_rejected() -> None:
    app = _App(post_data={"msg": [], "ok": True}, skeleton_nodes=[])
    with pytest.raises(ValueError):
        app.create_virtual_devices(VirtualDeviceSpec.empty(), copies=0)
    with pytest.raises(ValueError):
        app.create_port_template("", "x", {})
    with pytest.raises(ValueError):
        PortFromTemplate(template_id="x", count=0)


def test_api_virtual_reads_and_writes(load: Callable[[str], dict[str, Any]]) -> None:
    templates_data = load("virtual_templates.json")["data"]
    rest = _FakeRest(get_data=templates_data, post_data=load("update_virtual_instances_create.json")["data"])
    api = InspectAPI(SimpleNamespace(rest=rest))
    templates = api.get_virtual_templates()
    assert templates[0].id == "generic_bidir"
    assert rest.get_calls[0][0].endswith("/virtualTemplates/**")
    assert rest.get_calls[0][1] is True

    rest._get_data = load("virtual_devices.json")["data"]
    devices = api.get_virtual_devices()
    assert devices[0].id == "virtual.1"
    assert rest.get_calls[1][0].endswith("/virtualDevices/**")

    resp = api.update_virtual_instances(
        InspectApiUpdateVirtualInstancesData(add=[VirtualDeviceSpec.from_ports("generic_bidir").to_wire()])
    )
    assert resp.data.addedDeviceLabels["virtual.1"] == "Virtual Device 1"
    assert rest.post_calls[0][0].endswith("/updateVirtualInstances")

    rest._post_data = {"msg": [], "ok": True}
    api.update_virtual_templates(InspectApiUpdateVirtualTemplatesData())
    api.add_virtual_topology(
        InspectApiAddVirtualTopologyData(deviceId="virtual.1", moduleId=0, countByVertexTemplate={"ip_out": 1})
    )
    assert rest.post_calls[1][0].endswith("/updateVirtualTemplates")
    assert rest.post_calls[2][0].endswith("/addVirtualTopology")


def test_upsert_devices_from_skeleton_indexes_virtual_nodes() -> None:
    nodes = [_virtual_skeleton_node("virtual.1", "Virtual Device 1")]
    api = InspectAPI(SimpleNamespace(rest=_FakeRest(get_data={}, post_data={})))
    api.get_device_skeleton = lambda: list(nodes)  # type: ignore[method-assign]
    snap = InspectSnapshot(fetcher=api, device_items=[], edge_items=[])
    snap.upsert_devices_from_skeleton(["virtual.1"])
    device = snap.get_device("virtual.1")
    assert device is not None
    assert device.is_virtual is True
    assert device.label == "Virtual Device 1"


# --- Internal ---


def _virtual_skeleton_node(device_id: str, label: str) -> InspectApiNodeStatusItem:
    dash = device_id.replace(".", "-")
    return InspectApiNodeStatusItem.model_validate(
        {
            "_id": dash,
            "_vid": dash,
            "descriptor": {"label": label},
            "deviceId": device_id,
            "resourceId": f"device:{dash}",
        }
    )


class _FakeRest:
    def __init__(
        self,
        get_data: dict[str, Any] | None = None,
        post_data: dict[str, Any] | None = None,
        skeleton_nodes: list[InspectApiNodeStatusItem] | None = None,
    ) -> None:
        self._get_data = get_data or {}
        self._post_data = post_data or {}
        self._skeleton_nodes = skeleton_nodes or []
        self.get_calls: list[tuple[str, bool]] = []
        self.post_calls: list[tuple[str, dict[str, Any]]] = []

    def get(self, url_path: str, allow_projection: bool = False, **kwargs: Any) -> SimpleNamespace:
        self.get_calls.append((url_path, allow_projection))
        return SimpleNamespace(data=self._get_data, header=_ok_header())

    def post(self, url_path: str, body: Any, **kwargs: Any) -> SimpleNamespace:
        payload = body.model_dump(mode="json", by_alias=True)
        self.post_calls.append((url_path, payload))
        return SimpleNamespace(data=self._post_data, header=_ok_header())


class _RecordingSnapshot:
    def __init__(self, devices: dict[str, InspectDevice] | None = None) -> None:
        self.network_refresh_calls: list[list[str]] = []
        self.upsert_calls: list[list[str]] = []
        self._devices = devices or {}

    def apply_network_refresh(self, device_ids: list[str]) -> None:
        self.network_refresh_calls.append(list(device_ids))

    def upsert_devices_from_skeleton(self, device_ids: list[str]) -> None:
        self.upsert_calls.append(list(device_ids))

    def get_device(self, device_id: str) -> InspectDevice | None:
        return self._devices.get(device_id)

    def apply_post_commit(self, **kwargs: Any) -> None:
        return None


class _App(InspectActionsMixin):
    def __init__(
        self,
        post_data: dict[str, Any],
        get_data: dict[str, Any] | None = None,
        skeleton_nodes: list[InspectApiNodeStatusItem] | None = None,
        snapshot: _RecordingSnapshot | None = None,
    ) -> None:
        self._logger = logging.getLogger("test")
        rest = _FakeRest(get_data=get_data, post_data=post_data, skeleton_nodes=skeleton_nodes)
        self._inspect_api = InspectAPI(SimpleNamespace(rest=rest))
        # Bind skeleton fetch onto the API for recording-snapshot tests that call real upsert.
        self._inspect_api.get_device_skeleton = lambda: list(skeleton_nodes or [])  # type: ignore[method-assign]
        if snapshot is not None:
            self._snapshot = snapshot
        else:
            devices: dict[str, InspectDevice] = {}
            recording = _RecordingSnapshot(devices=devices)
            # Populate devices after upsert by wrapping upsert to create InspectDevice stubs.
            real_snap = InspectSnapshot(fetcher=self._inspect_api, device_items=[], edge_items=[])

            def _upsert(device_ids: list[str]) -> None:
                recording.upsert_calls.append(list(device_ids))
                real_snap.upsert_devices_from_skeleton(device_ids)
                for device_id in device_ids:
                    device = real_snap.get_device(device_id)
                    if device is not None:
                        devices[device_id] = device

            recording.upsert_devices_from_skeleton = _upsert  # type: ignore[method-assign]
            recording.get_device = devices.get  # type: ignore[method-assign]
            self._snapshot = recording

    def _get_snapshot(self) -> Any:
        return self._snapshot


class _FakeWriteAPI:
    def __init__(self, topology_response: dict[str, Any]) -> None:
        self.update_response = InspectApiUpdateTopologyResponse.model_validate(topology_response)
        self.update_calls: list[Any] = []
        self.virtual_instance_calls: list[Any] = []

    def update_topology(self, delta: Any) -> InspectApiUpdateTopologyResponse:
        self.update_calls.append(delta)
        return self.update_response

    def update_virtual_instances(self, data: Any) -> Any:
        self.virtual_instance_calls.append(data)
        raise AssertionError("updateVirtualInstances must not be used for virtual device removal")


class _WriteApp(InspectWriteMixin):
    def __init__(self, api: _FakeWriteAPI) -> None:
        self._logger = logging.getLogger("test")
        self._inspect_api = api  # type: ignore[assignment]
        self._snapshot = _RecordingSnapshot()


def _ok_header() -> SimpleNamespace:
    return SimpleNamespace(
        model_dump=lambda mode="json": {
            "auth": True,
            "caption": "OK",
            "code": "OK",
            "errorCodes": [],
            "errorDetails": [],
            "id": "0",
            "msg": [],
            "ok": True,
            "user": "api-user",
        },
        auth=True,
        caption="OK",
        code="OK",
        errorCodes=[],
        errorDetails=[],
        id="0",
        msg=[],
        ok=True,
        user="api-user",
    )
