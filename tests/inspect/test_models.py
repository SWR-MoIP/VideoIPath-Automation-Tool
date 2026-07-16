"""Contract tests: every fixture parses into its DTO, and write-payload builders reproduce
the verified request shapes byte-for-byte."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from videoipath_automation_tool.apps.inspect.model.actions import (
    InspectApiLookupEdgesResponse,
    InspectApiLookupInspectDeviceResponse,
    InspectApiLookupVertexResponse,
    InspectApiLookupVerticesResponse,
)
from videoipath_automation_tool.apps.inspect.model.collector import (
    InspectApiDoubleVertexInfo,
    InspectApiExternalEdgesByDeviceKeyItem,
    InspectApiNodeStatusItem,
    InspectApiPathItem,
    InspectApiSingleVertexInfo,
    InspectPortStatus,
)
from videoipath_automation_tool.apps.inspect.model.update_topology import (
    InspectApiUpdateTopologyData,
    InspectApiUpdateTopologyResponse,
)


def test_device_skeleton_items_parse_and_expose_effective_label(load: Callable[[str], dict[str, Any]]) -> None:
    items = _node_items(load("skeleton_nodestatus_short.json"))
    assert items
    for raw in items:
        node = InspectApiNodeStatusItem.model_validate(raw)
        assert node.id
        assert node.effective_label  # comes from descriptor.label, not a top-level label


def test_device_skeleton_exposes_description(load: Callable[[str], dict[str, Any]]) -> None:
    items = _node_items(load("skeleton_nodestatus_short.json"))
    node = InspectApiNodeStatusItem.model_validate(items[0])
    assert node.effective_description == "Example device description"


def test_node_effective_description_prefers_descriptor_then_fdescriptor() -> None:
    both = InspectApiNodeStatusItem.model_validate(
        {"_id": "device-a", "descriptor": {"desc": "user desc"}, "fDescriptor": {"desc": "factory desc"}}
    )
    assert both.effective_description == "user desc"

    factory_only = InspectApiNodeStatusItem.model_validate(
        {"_id": "device-a", "descriptor": {"desc": ""}, "fDescriptor": {"desc": "factory desc"}}
    )
    assert factory_only.effective_description == "factory desc"

    assert InspectApiNodeStatusItem.model_validate({"_id": "device-a"}).effective_description is None


def test_device_detail_parses_modules_and_ports(load: Callable[[str], dict[str, Any]]) -> None:
    items = _node_items(load("device_hydration_modules_ports.json"))
    node = InspectApiNodeStatusItem.model_validate(items[0])
    assert node.modules
    module = next(iter(node.modules.values()))
    assert module.ports


def test_device_detail_ports_expose_factory_label_and_override(load: Callable[[str], dict[str, Any]]) -> None:
    items = _node_items(load("device_hydration_modules_ports.json"))
    node = InspectApiNodeStatusItem.model_validate(items[0])
    ports = next(iter(node.modules.values())).ports
    port = ports["device-a.dev.module-1.port-out-1"]
    assert port.label == "port-out-1"  # factory label survives the override
    assert port.effective_label == "port-out-1 (out)"
    assert port.effective_description == "Example port description"


def test_port_vertex_info_parses_single_and_double(load: Callable[[str], dict[str, Any]]) -> None:
    items = _node_items(load("device_hydration_modules_ports.json"))
    node = InspectApiNodeStatusItem.model_validate(items[0])
    ports = next(iter(node.modules.values())).ports

    single = ports["device-a.dev.module-1.port-out-1"].parsed_vertex_info
    assert isinstance(single, InspectApiSingleVertexInfo)
    assert single.vertexType == "Out"
    assert single.fields is not None and single.fields.isActive is True and single.fields.isControlled is True

    double = ports["device-a.dev.module-1.port-bidi-1"].parsed_vertex_info
    assert isinstance(double, InspectApiDoubleVertexInfo)
    assert double.in_ is not None and double.in_.vertexType == "In"
    assert double.out is not None and double.out.vertexType == "Out"


def test_port_parsed_vertex_info_coerces_raw_dict() -> None:
    port = InspectPortStatus.model_construct(
        vertexInfo={"type": "single", "id": "device-a.1.p1.out", "vertexType": "Out"}
    )
    info = port.parsed_vertex_info
    assert isinstance(info, InspectApiSingleVertexInfo)
    assert info.id == "device-a.1.p1.out"

    assert InspectPortStatus.model_construct(vertexInfo={"type": "unknown"}).parsed_vertex_info is None
    assert InspectPortStatus.model_validate({"_id": "device-a.1.p1"}).parsed_vertex_info is None


def test_lookup_vertices_batch_response_parses(load: Callable[[str], dict[str, Any]]) -> None:
    resp = InspectApiLookupVerticesResponse.model_validate(load("lookup_inspect_vertices_by_ids.json"))
    details = resp.data["device-a.module-1.port-out-1.out"]
    assert details.vertexType == "Out"
    assert details.fields.typeFields is not None and details.fields.typeFields.type == "ip"
    assert details.fields.controlProps is not None
    assert details.fields.controlProps.configPriority == "off"
    assert details.fields.controlProps.onlyInitial is False


def test_edge_skeleton_items_parse(load: Callable[[str], dict[str, Any]]) -> None:
    items = load("edge_skeleton.json")["data"]["status"]["collector"]["externalEdgesByDeviceKey"]["_items"]
    assert len(items) > 0
    edge = InspectApiExternalEdgesByDeviceKeyItem.model_validate(items[0])
    assert "::" in edge.id
    assert edge.primary is not None


def test_paths_fixture_parses(load: Callable[[str], dict[str, Any]]) -> None:
    items = load("inspect_paths_limit5.json")["data"]["status"]["collector"]["inspect"]["paths"]["_items"]
    for raw in items:
        path = InspectApiPathItem.model_validate(raw)
        assert path.serviceFields.bid


def test_lookup_edges_returns_full_persisted_edge_form(load: Callable[[str], dict[str, Any]]) -> None:
    resp = InspectApiLookupEdgesResponse.model_validate(load("lookup_inspect_edges_by_ids.json"))
    key = next(iter(resp.data))
    edge = resp.data[key].edge
    assert edge.fromId and edge.toId
    assert edge.capacity == 65535


def test_lookup_vertex_edit_form(load: Callable[[str], dict[str, Any]]) -> None:
    resp = InspectApiLookupVertexResponse.model_validate(load("lookup_inspect_vertex_by_id.json"))
    assert resp.data.fields.typeFields is not None
    assert resp.data.vertexType in ("In", "Out", "Internal", None)


def test_lookup_device_fields() -> None:
    resp = InspectApiLookupInspectDeviceResponse.model_validate(_device_lookup_fixture())
    assert resp.data.fields.coordinates is not None


def test_replace_devices_payload_roundtrips_byte_for_byte(load: Callable[[str], dict[str, Any]]) -> None:
    fixture = load("update_topology_replace_devices.json")
    data = InspectApiUpdateTopologyData.model_validate(fixture["request"]["data"])
    built = data.model_dump(mode="json", by_alias=True)
    assert built["replaceDevices"] == fixture["request"]["data"]["replaceDevices"]


def test_replace_vertices_payload_roundtrips_byte_for_byte(load: Callable[[str], dict[str, Any]]) -> None:
    fixture = load("update_topology_replace_vertices.json")
    data = InspectApiUpdateTopologyData.model_validate(fixture["request"]["data"])
    built = data.model_dump(mode="json", by_alias=True)
    assert built["replaceVertices"] == fixture["request"]["data"]["replaceVertices"]


def test_commit_success_and_failure_flags(load: Callable[[str], dict[str, Any]]) -> None:
    ok = InspectApiUpdateTopologyResponse.model_validate(load("update_topology_success.json"))
    assert ok.committed is True

    fail_booking = InspectApiUpdateTopologyResponse.model_validate(load("update_topology_fail_booking.json"))
    assert fail_booking.committed is False
    assert fail_booking.data.validation.details  # per-entity detail present

    fail_remove = InspectApiUpdateTopologyResponse.model_validate(load("update_topology_fail_remove.json"))
    assert fail_remove.committed is False


def test_inspect_icon_type_matches_topology_icon_type() -> None:
    """Drift guard: the inspect-local Literal must stay in sync with the topology app's IconType."""
    from typing import get_args

    from videoipath_automation_tool.apps.inspect.model.common import InspectIconType
    from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_n_graph_element import IconType

    assert set(get_args(InspectIconType)) == set(get_args(IconType))


def test_port_assigned_tags_from_tags_info() -> None:
    port = InspectPortStatus.model_validate(
        {
            "_id": "device-a.1.p1",
            "tagsInfo": {"assigned": {"all": ["Video~~T"], "inherited": {}, "local": {"Video~~T": {}}}},
        }
    )
    assert port.assigned_tags == ["Video~~T"]
    assert InspectPortStatus.model_validate({"_id": "device-a.1.p2"}).assigned_tags == []


# --- Internal ---


def _node_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return payload["data"]["status"]["collector"]["inspect"]["nodeStatus"]["_items"]


def _device_lookup_fixture() -> dict[str, Any]:
    # lookupInspectDevice example from endpoints.md (anonymized)
    return {
        "data": {
            "assignedTags": {"all": [], "inherited": {}, "inheritedConflict": False, "local": {}},
            "fields": {
                "coordinates": {"x": 500, "y": 8150},
                "descriptor": {"desc": "", "label": "Example Device A"},
                "iconSize": "medium",
                "iconType": "gateway",
                "localAssignedTags": [],
                "sdpStrategy": "always",
                "siteId": None,
                "tags": [],
                "virtualDeviceFields": None,
            },
        },
        "header": {"auth": True, "caption": "OK", "code": "OK", "id": "0", "msg": [], "ok": True, "user": "api-user"},
    }
