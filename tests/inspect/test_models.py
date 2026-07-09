"""Contract tests: every fixture parses into its DTO, and write-payload builders reproduce
the verified request shapes byte-for-byte."""

from videoipath_automation_tool.apps.inspect.model.actions import (
    InspectApiLookupEdgesResponse,
    InspectApiLookupInspectDeviceResponse,
    InspectApiLookupVertexResponse,
)
from videoipath_automation_tool.apps.inspect.model.collector import (
    InspectApiExternalEdgesByDeviceKeyItem,
    InspectApiNodeStatusItem,
    InspectApiPathItem,
    InspectPortStatus,
)
from videoipath_automation_tool.apps.inspect.model.update_topology import (
    InspectApiUpdateTopologyData,
    InspectApiUpdateTopologyResponse,
)


def _node_items(payload):
    return payload["data"]["status"]["collector"]["inspect"]["nodeStatus"]["_items"]


def test_device_skeleton_items_parse_and_expose_effective_label(load):
    items = _node_items(load("skeleton_nodestatus_short.json"))
    assert items
    for raw in items:
        node = InspectApiNodeStatusItem.model_validate(raw)
        assert node.id
        assert node.effective_label  # comes from descriptor.label, not a top-level label


def test_device_detail_parses_modules_and_ports(load):
    items = _node_items(load("device_hydration_modules_ports.json"))
    node = InspectApiNodeStatusItem.model_validate(items[0])
    assert node.modules
    module = next(iter(node.modules.values()))
    assert module.ports


def test_edge_skeleton_items_parse(load):
    items = load("edge_skeleton.json")["data"]["status"]["collector"]["externalEdgesByDeviceKey"]["_items"]
    assert len(items) > 0
    edge = InspectApiExternalEdgesByDeviceKeyItem.model_validate(items[0])
    assert "::" in edge.id
    assert edge.primary is not None


def test_paths_fixture_parses(load):
    items = load("inspect_paths_limit5.json")["data"]["status"]["collector"]["inspect"]["paths"]["_items"]
    for raw in items:
        path = InspectApiPathItem.model_validate(raw)
        assert path.serviceFields.bid


def test_lookup_edges_returns_full_persisted_edge_form(load):
    resp = InspectApiLookupEdgesResponse.model_validate(load("lookup_inspect_edges_by_ids.json"))
    key = next(iter(resp.data))
    edge = resp.data[key].edge
    assert edge.fromId and edge.toId
    assert edge.capacity == 65535


def test_lookup_vertex_edit_form(load):
    resp = InspectApiLookupVertexResponse.model_validate(load("lookup_inspect_vertex_by_id.json"))
    assert resp.data.fields.typeFields is not None
    assert resp.data.vertexType in ("In", "Out", "Internal", None)


def test_lookup_device_fields():
    resp = InspectApiLookupInspectDeviceResponse.model_validate(_device_lookup_fixture())
    assert resp.data.fields.coordinates is not None


def _device_lookup_fixture():
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


def test_replace_devices_payload_roundtrips_byte_for_byte(load):
    fixture = load("update_topology_replace_devices.json")
    data = InspectApiUpdateTopologyData.model_validate(fixture["request"]["data"])
    built = data.model_dump(mode="json", by_alias=True)
    assert built["replaceDevices"] == fixture["request"]["data"]["replaceDevices"]


def test_replace_vertices_payload_roundtrips_byte_for_byte(load):
    fixture = load("update_topology_replace_vertices.json")
    data = InspectApiUpdateTopologyData.model_validate(fixture["request"]["data"])
    built = data.model_dump(mode="json", by_alias=True)
    assert built["replaceVertices"] == fixture["request"]["data"]["replaceVertices"]


def test_commit_success_and_failure_flags(load):
    ok = InspectApiUpdateTopologyResponse.model_validate(load("update_topology_success.json"))
    assert ok.committed is True

    fail_booking = InspectApiUpdateTopologyResponse.model_validate(load("update_topology_fail_booking.json"))
    assert fail_booking.committed is False
    assert fail_booking.data.validation.details  # per-entity detail present

    fail_remove = InspectApiUpdateTopologyResponse.model_validate(load("update_topology_fail_remove.json"))
    assert fail_remove.committed is False


def test_port_assigned_tags_from_tags_info():
    port = InspectPortStatus.model_validate(
        {
            "_id": "device-a.1.p1",
            "tagsInfo": {"assigned": {"all": ["Video~~T"], "inherited": {}, "local": {"Video~~T": {}}}},
        }
    )
    assert port.assigned_tags == ["Video~~T"]
    assert InspectPortStatus.model_validate({"_id": "device-a.1.p2"}).assigned_tags == []
