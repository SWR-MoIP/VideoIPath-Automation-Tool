"""Anonymized regressions for server behavior first observed by the live suite."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from videoipath_automation_tool.apps.inspect.errors import InspectEntityNotFoundError
from videoipath_automation_tool.provisioning import Blueprint, DeviceTarget, ProvisioningDevice, ProvisioningError
from videoipath_automation_tool.provisioning.inspect import InspectGateway

from .conftest import make_inspect_app, matrox_layout

if TYPE_CHECKING:
    from videoipath_automation_tool.apps.inspect.model.actions import InspectApiLookupInspectDeviceResponse
    from videoipath_automation_tool.provisioning import ProvisioningEngine

    from .conftest import FakeInspectServer, FakeInventory


def test_inventory_only_collector_node_is_added_before_configuration(
    engine: ProvisioningEngine, inventory: FakeInventory, server: FakeInspectServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    inventory.seed("device1", label="device-a")
    server.nodes["device1"] = {"_id": "device1", "modules": {}}
    server.discoverable["device1"] = matrox_layout("device1")
    original = server.lookup_inspect_device

    def lookup(device_id: str) -> InspectApiLookupInspectDeviceResponse:
        if device_id not in server.device_forms:
            raise InspectEntityNotFoundError(device_id, "device")
        return original(device_id)

    monkeypatch.setattr(server, "lookup_inspect_device", lookup)
    gateway = InspectGateway(make_inspect_app(server))
    assert not gateway.in_topology("device1")
    assert gateway.read_peer_scope(DeviceTarget(device_id="device1")) is None
    plan = engine.plan(
        ProvisioningDevice(key="device-a", label="device-a", inventory_id="device1"),
        Blueprint.from_dict({"schema_version": 1, "defaults": {"topology": {"device": {"tags": ["tag-a"]}}}}),
        scope="topology",
    )
    assert not plan.fully_resolved and not server.writes
    result = plan.apply()
    assert result.status == "succeeded"
    assert [name for name, _ in server.writes] == ["add_devices", "sync_devices", "update_topology"]


def test_membership_lookup_failure_is_not_treated_as_absence(
    server: FakeInspectServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    server.nodes["device1"] = {"_id": "device1", "modules": {}}

    def fail(device_id: str) -> None:
        raise ConnectionError("test transport failure")

    monkeypatch.setattr(server, "lookup_inspect_device", fail)
    with pytest.raises(ProvisioningError, match="Inspect edit form"):
        InspectGateway(make_inspect_app(server)).in_topology("device1")
    assert not server.writes


def test_missing_collector_factory_labels_use_driver_graph_without_editable_names(
    server: FakeInspectServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    layout = matrox_layout("device1")
    server.install(layout)
    labels: dict[str, str] = {}
    expected: dict[str, str] = {}
    for module in server.nodes["device1"]["modules"].values():
        for port in module["ports"].values():
            expected[port["pid"]] = port["label"]
            info = port["vertexInfo"]
            sides = [info["in"], info["out"]] if info["type"] == "double" else [info]
            labels.update({side["id"]: port["label"] for side in sides})
            port["label"] = None
            port["descriptor"] = {"label": "editable-name", "desc": ""}
    calls: list[tuple[str, ...]] = []

    def factory_labels(*vertex_ids: str) -> dict[str, str]:
        calls.append(vertex_ids)
        return labels

    monkeypatch.setattr(server, "get_ngraph_factory_labels", factory_labels, raising=False)
    scope = InspectGateway(make_inspect_app(server)).read_scope(DeviceTarget(device_id="device1"))
    assert {port.id: port.factory_label for port in scope.ports} == expected
    assert all(port.label == "editable-name" for port in scope.ports)
    assert all(vertex.factory_label == expected[vertex.port_id] for vertex in scope.vertices)
    assert len(calls) == 1 and set(calls[0]) == set(labels)
    assert not server.writes
