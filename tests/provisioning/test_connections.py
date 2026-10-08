"""Generic connections through the real provisioning engine and Inspect transaction, offline."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import ValidationError

from tests.provisioning.conftest import HEADER, FakeInspectServer, FakeInventory, build_layout, matrox_layout
from videoipath_automation_tool.apps.inspect.errors import InspectCommitError
from videoipath_automation_tool.apps.inspect.model.actions import InspectApiEdgeForm
from videoipath_automation_tool.apps.inspect.model.update_topology import InspectApiUpdateTopologyResponse
from videoipath_automation_tool.provisioning import (
    Blueprint,
    DeviceTarget,
    EdgePatch,
    ModuleTarget,
    PeerEndpoint,
    PortSelector,
    ProvisioningApplyError,
    ProvisioningConnection,
    ProvisioningDevice,
    ProvisioningEngine,
    ProvisioningTargetError,
    ProvisioningValidationError,
    TagDelta,
)


def _blueprint(**topology: Any) -> Blueprint:
    config = {"port_mapping": {"uplink": [{"factory_label": "P1"}]}, **topology}
    return Blueprint.from_dict({"schema_version": 1, "defaults": {"topology": config}})


def _connection(**kwargs: Any) -> ProvisioningConnection:
    values = {
        "local": "uplink",
        "peer": PeerEndpoint(target=DeviceTarget(device_id="device2"), port=PortSelector(factory_label="P1")),
        **kwargs,
    }
    return ProvisioningConnection(**values)


def _device(*connections: ProvisioningConnection, **kwargs: Any) -> ProvisioningDevice:
    return ProvisioningDevice(
        key="device-a", label="device-a", inventory_id="device1", connections=list(connections), **kwargs
    )


def _seed(inventory: FakeInventory, server: FakeInspectServer, *, peer: bool = True) -> None:
    inventory.seed("device1", label="device-a")
    server.install(matrox_layout("device1"))
    if peer:
        server.install(matrox_layout("device2"))


def test_bidirectional_create_shared_commit_and_idempotence(
    engine: ProvisioningEngine,
    inventory: FakeInventory,
    server: FakeInspectServer,
) -> None:
    _seed(inventory, server)
    device = _device(_connection(fields=EdgePatch(weight=0, capacity=0, bandwidth=0.0, active=False)))
    blueprint = _blueprint(vertices=[{"factory_label": "Video Sender", "fields": {"active": False}}])
    plan = engine.plan(device, blueprint)
    assert not server.writes
    assert plan.fully_resolved and len(plan.connections[0].edge_ids) == 2
    assert plan.interface_bindings == [] and plan.port_bindings[0].key == "uplink"
    assert "connection 0 [planned]" in plan.summary()
    assert plan.apply(dry_run=True).connections[0].status == "planned"
    assert not server.writes
    result = plan.apply()
    assert result.status == "succeeded" and result.verification == "confirmed"
    assert result.connections[0].status == "completed"
    assert len(server.writes) == 1
    delta = server.writes[0][1]
    assert delta["replaceDevices"] and delta["replaceVertices"] and len(delta["replaceEdges"]) == 2
    assert all(
        not form["active"] and form["capacity"] == 0 and form["weight"] == 0 for form in server.edge_forms.values()
    )
    assert engine.apply(device, blueprint).status == "no_change"
    assert len(server.writes) == 1


@pytest.mark.parametrize("media", ["video", "audio"])
@pytest.mark.parametrize("direction", ["auto", "outgoing"])
def test_directed_media_without_direction_suffix(
    engine: ProvisioningEngine,
    inventory: FakeInventory,
    server: FakeInspectServer,
    media: str,
    direction: str,
) -> None:
    inventory.seed("device1")
    for device_id, side in [("device1", "Out"), ("device2", "In")]:
        server.install(
            build_layout(device_id, {f"{device_id}.dev.0": [("port-1", "media-1", [("vertex", side, "codec", media)])]})
        )
    peer = PeerEndpoint(target=DeviceTarget(device_id="device2"), port=PortSelector(factory_label="media-1"))
    result = engine.apply(
        _device(_connection(local=PortSelector(factory_label="media-1"), peer=peer, direction=direction)),
        _blueprint(port_mapping={}),
    )
    assert result.connections[0].edge_ids == ["device1.0.port-1.vertex::device2.0.port-1.vertex"]
    assert len(server.edge_forms) == 1


@pytest.mark.parametrize("direction,count", [("incoming", 1), ("outgoing", 1), ("bidirectional", 2)])
def test_explicit_directions(
    engine: ProvisioningEngine, inventory: FakeInventory, server: FakeInspectServer, direction: str, count: int
) -> None:
    _seed(inventory, server)
    result = engine.apply(_device(_connection(direction=direction)), _blueprint())
    assert len(result.connections[0].edge_ids) == count
    if direction == "incoming":
        assert result.connections[0].edge_ids == ["device2.0.P1.out::device1.0.P1.in"]


def test_managed_updates_preserve_other_edges_and_nested_fields(
    engine: ProvisioningEngine,
    inventory: FakeInventory,
    server: FakeInspectServer,
) -> None:
    _seed(inventory, server)
    engine.apply(_device(_connection()), _blueprint())
    for form in server.edge_forms.values():
        form["descriptor"]["desc"] = "keep-description"
        form["fDescriptor"]["label"] = "factory-edge"
        form["tags"] = ["tag-a", "tag-b"]
        form["weightFactors"] = {"bandwidth": {"weight": 5}, "service": {"max": 43, "weight": 3}}
    foreign = "device1.0.P2.out::device2.0.P2.in"
    server.edge_forms[foreign] = InspectApiEdgeForm(fromId="device1.0.P2.out", toId="device2.0.P2.in").model_dump()
    fields = EdgePatch(
        label="edge-a",
        tags=TagDelta(add=["tag-c"], remove=["tag-a"]),
        weight_per_service=0,
        conflict_priority="high",
        include_formats=[],
        exclude_formats=["format-a"],
        redundancy_mode="Any",
        bandwidth_weight_factor=0,
    )
    result = engine.apply(_device(_connection(fields=fields)), _blueprint())
    for edge_id in result.connections[0].edge_ids:
        form = server.edge_forms[edge_id]
        assert form["descriptor"] == {"label": "edge-a", "desc": "keep-description"}
        assert form["fDescriptor"]["label"] == "factory-edge"
        assert form["tags"] == ["tag-b", "tag-c"]
        assert form["weightFactors"] == {"bandwidth": {"weight": 0}, "service": {"max": 43, "weight": 0}}
        assert form["conflictPri"] == 1 and form["excludeFormats"] == ["format-a"]
    assert foreign in server.edge_forms
    assert engine.apply(_device(_connection(fields=fields)), _blueprint()).status == "no_change"
    assert engine.apply(_device(), _blueprint()).status == "no_change"
    assert len(server.edge_forms) == 3


def test_duplicate_connections_coalesce_or_reject_conflicts(
    engine: ProvisioningEngine,
    inventory: FakeInventory,
    server: FakeInspectServer,
) -> None:
    _seed(inventory, server)
    connection = _connection(fields=EdgePatch(weight=3))
    plan = engine.plan(_device(connection, connection, _connection(fields=EdgePatch(label="edge-a"))), _blueprint())
    assert len([op for op in plan.phase("topology").operations if op.entity_kind == "edge"]) == 2
    with pytest.raises(ProvisioningValidationError, match="Conflicting 'weight'"):
        engine.plan(_device(connection, _connection(fields=EdgePatch(weight=4))), _blueprint())
    assert not server.writes


def test_missing_peer_is_partial_and_frozen_until_replan(
    engine: ProvisioningEngine,
    inventory: FakeInventory,
    server: FakeInspectServer,
) -> None:
    _seed(inventory, server, peer=False)
    device, blueprint = _device(_connection()), _blueprint()
    plan = engine.plan(device, blueprint)
    assert not plan.fully_resolved and plan.connections[0].status == "deferred"
    preview = plan.apply(dry_run=True)
    assert preview.status == "planned" and preview.replan_required and not server.writes
    server.install(matrox_layout("device2"))
    result = plan.apply()
    assert result.status == "partial" and result.replan_required and not result.ok
    assert not server.edge_forms
    assert result.connections[0].local and result.connections[0].peer is None
    assert engine.apply(device, blueprint).status == "succeeded"


def test_pending_without_any_write_is_still_partial(
    engine: ProvisioningEngine,
    inventory: FakeInventory,
    server: FakeInspectServer,
) -> None:
    _seed(inventory, server, peer=False)
    engine.apply(_device(), _blueprint())
    server.writes.clear()
    result = engine.apply(_device(_connection()), _blueprint())
    assert result.status == "partial" and result.phase("topology").status == "deferred"
    assert result.verification == "not_applicable" and not server.writes


def test_mixed_ready_and_pending_connections(
    engine: ProvisioningEngine,
    inventory: FakeInventory,
    server: FakeInspectServer,
) -> None:
    _seed(inventory, server)
    missing = PeerEndpoint(target=DeviceTarget(device_id="device3"), port=PortSelector(factory_label="P1"))
    result = engine.apply(_device(_connection(), _connection(peer=missing)), _blueprint())
    assert result.status == "partial" and result.verification == "confirmed"
    assert [state.status for state in result.connections] == ["completed", "deferred"]
    assert len(server.edge_forms) == 2


@pytest.mark.parametrize("missing", ["module", "ports"])
def test_undiscovered_peer_module_or_ports_is_pending(
    engine: ProvisioningEngine,
    inventory: FakeInventory,
    server: FakeInspectServer,
    missing: str,
) -> None:
    _seed(inventory, server)
    if missing == "ports":
        server.nodes["device2"]["modules"]["device2.dev.0"]["ports"] = {}
    target = ModuleTarget(device_id="device2", module_id="device2.dev.1" if missing == "module" else "device2.dev.0")
    peer = PeerEndpoint(target=target, port=PortSelector(factory_label="P1"))
    assert engine.apply(_device(_connection(peer=peer)), _blueprint()).connections[0].status == "deferred"


def test_peer_selector_miss_and_transport_error_are_not_pending(
    engine: ProvisioningEngine,
    inventory: FakeInventory,
    server: FakeInspectServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed(inventory, server)
    peer = PeerEndpoint(target=DeviceTarget(device_id="device2"), port=PortSelector(factory_label="absent"))
    with pytest.raises(ProvisioningTargetError, match="no match"):
        engine.plan(_device(_connection(peer=peer)), _blueprint())

    def fail(device_id: str) -> None:
        raise OSError("read failed")

    monkeypatch.setattr(server, "get_device_detail", fail)
    with pytest.raises(OSError, match="read failed"):
        engine.plan(_device(_connection()), _blueprint())
    assert not server.writes


@pytest.mark.parametrize("change", ["peer", "edge_created", "edge_updated", "edge_removed"])
@pytest.mark.parametrize("dry_run", [False, True])
def test_stale_peer_and_edge_baselines(
    engine: ProvisioningEngine,
    inventory: FakeInventory,
    server: FakeInspectServer,
    change: str,
    dry_run: bool,
) -> None:
    _seed(inventory, server)
    device, blueprint = _device(_connection()), _blueprint()
    if change in ("edge_updated", "edge_removed"):
        engine.apply(device, blueprint)
    plan = engine.plan(device, blueprint)
    if change == "peer":
        server.vertex_forms["device2.0.P1.out"]["fields"]["active"] = False
    elif change == "edge_created":
        server.edge_forms["device1.0.P1.out::device2.0.P1.in"] = InspectApiEdgeForm(
            fromId="device1.0.P1.out", toId="device2.0.P1.in"
        ).model_dump()
    elif change == "edge_updated":
        next(iter(server.edge_forms.values()))["weight"] = 8
    else:
        server.edge_forms.pop(next(iter(server.edge_forms)))
    server.writes.clear()
    with pytest.raises(ProvisioningApplyError, match="changed"):
        plan.apply(dry_run=dry_run)
    assert not server.writes


@pytest.mark.parametrize("kind", ["edge", "vertex", "module", "device"])
def test_pending_snapshot_edits_on_connection_entities(
    engine: ProvisioningEngine,
    inventory: FakeInventory,
    server: FakeInspectServer,
    app: SimpleNamespace,
    kind: str,
) -> None:
    _seed(inventory, server)
    plan = engine.plan(_device(_connection()), _blueprint())
    entity_id = {
        "edge": plan.connections[0].edge_ids[0],
        "vertex": "device2.0.P1.in",
        "module": "device2.dev.0",
        "device": "device2",
    }[kind]
    app.inspect._get_snapshot().stage_edit(kind, entity_id, "label", "pending")
    with pytest.raises(ProvisioningApplyError, match="Pending uncommitted"):
        plan.apply()
    assert not server.writes


def test_plan_copies_connections_and_edge_fields(
    engine: ProvisioningEngine,
    inventory: FakeInventory,
    server: FakeInspectServer,
) -> None:
    _seed(inventory, server)
    fields = EdgePatch(tags=["tag-a"])
    device = _device(_connection(fields=fields))
    plan = engine.plan(device, _blueprint())
    fields.tags.append("tag-b")
    device.connections.clear()
    plan.connections[0].connection.fields.tags.append("tag-c")
    result = plan.apply()
    assert all(form["tags"] == ["tag-a"] for form in server.edge_forms.values())
    assert result.connections[0].status == "completed"


def test_local_discovery_materializes_edges(
    engine: ProvisioningEngine,
    inventory: FakeInventory,
    server: FakeInspectServer,
) -> None:
    inventory.seed("device1")
    server.discoverable["device1"] = matrox_layout("device1")
    server.install(matrox_layout("device2"))
    plan = engine.plan(_device(_connection()), _blueprint())
    assert not plan.fully_resolved
    assert plan.apply(dry_run=True).connections[0].status == "deferred"
    assert not server.writes
    result = plan.apply()
    assert result.materialized and result.status == "succeeded" and len(server.edge_forms) == 2


def test_failure_and_verification_status(
    engine: ProvisioningEngine,
    inventory: FakeInventory,
    server: FakeInspectServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed(inventory, server)
    rejection = InspectApiUpdateTopologyResponse.model_validate(
        {
            "header": HEADER,
            "data": {
                "items": [],
                "res": {"ok": False, "msg": ["rejected"]},
                "validation": {"result": {"ok": True, "msg": []}, "createIds": [], "details": {}},
            },
        }
    )
    server.fail_commit = InspectCommitError(rejection)
    with pytest.raises(ProvisioningApplyError) as error:
        engine.apply(_device(_connection()), _blueprint())
    assert error.value.result.connections[0].status == "failed"
    assert not server.edge_forms
    server.fail_commit = None
    original = server.update_topology

    def discard_edges(delta: Any) -> Any:
        result = original(delta)
        server.edge_forms.clear()
        return result

    monkeypatch.setattr(server, "update_topology", discard_edges)
    result = engine.apply(_device(_connection()), _blueprint())
    assert result.status == "succeeded" and result.verification == "unconfirmed"
    assert "fromId" in result.verification_detail


def test_legacy_ip_mapping_can_supply_connection_without_changing_processor_inputs(
    engine: ProvisioningEngine,
    inventory: FakeInventory,
    server: FakeInspectServer,
) -> None:
    _seed(inventory, server)
    blueprint = _blueprint(
        port_mapping={"media": [{"factory_label": "Video Sender"}]},
        ip_vertex_mapping={"uplink": ["P1"], "backup": ["P2"]},
        vertex_processor={"processor_type": "matrox.convertip.default", "params": {"redundant_streams": True}},
    )
    plan = engine.plan(_device(_connection()), blueprint)
    assert [binding.key for binding in plan.interface_bindings] == ["uplink", "backup"]
    assert [binding.key for binding in plan.port_bindings] == ["media"]
    assert plan.apply().ok


@pytest.mark.parametrize("fields", [{}, {"port_id": "port-a", "factory_label": "port-a"}])
def test_port_selector_validation(fields: dict[str, Any]) -> None:
    with pytest.raises(ValidationError, match="exactly one"):
        PortSelector(**fields)


def test_local_fallback_module_scope_and_ambiguity(
    engine: ProvisioningEngine,
    inventory: FakeInventory,
    server: FakeInspectServer,
) -> None:
    _seed(inventory, server)
    second = matrox_layout("device1", module="device1.dev.1")
    server.nodes["device1"]["modules"].update(second["node"]["modules"])
    server.vertex_forms.update(second["vertex_forms"])
    with pytest.raises(ProvisioningTargetError, match="multiple ports"):
        engine.plan(_device(_connection()), _blueprint())
    blueprint = _blueprint(
        port_mapping={"uplink": [{"factory_label": "missing"}, {"factory_label": "P{module.position}", "kind": "ip"}]}
    )
    device = _device(
        _connection(), module_position="1", topology=ModuleTarget(device_id="device1", module_id="device1.dev.0")
    )
    assert engine.apply(device, blueprint).connections[0].local.port_id == "device1.dev.0.P1"
    wrong = _connection(local=PortSelector(port_id="device1.dev.1.P1"))
    with pytest.raises(ProvisioningTargetError, match="no match"):
        engine.plan(_device(wrong, topology=device.topology), _blueprint(port_mapping={}))


def test_invalid_input_scope_and_mapping_keys_fail_before_io() -> None:
    class NoIO:
        def __getattr__(self, key: str) -> Any:
            raise AssertionError(f"unexpected I/O: {key}")

    engine = ProvisioningEngine(NoIO())
    with pytest.raises(ProvisioningValidationError, match="Unknown local port"):
        engine.plan(_device(_connection(local="unknown")), _blueprint())
    with pytest.raises(ProvisioningValidationError, match="require a topology section"):
        engine.plan(
            _device(_connection()),
            Blueprint.from_dict(
                {"schema_version": 1, "defaults": {"inventory": {"driver_id": "com.nevion.NMOS_multidevice-0.1.0"}}}
            ),
        )
    with pytest.raises(ProvisioningValidationError, match="distinct keys"):
        _blueprint(ip_vertex_mapping={"uplink": ["P1"]})


def test_inventory_scope_skips_connections(
    engine: ProvisioningEngine,
    inventory: FakeInventory,
    server: FakeInspectServer,
) -> None:
    _seed(inventory, server)
    blueprint = Blueprint.from_dict(
        {"schema_version": 1, "defaults": {"inventory": {"driver_id": "com.nevion.NMOS_multidevice-0.1.0"}}}
    )
    plan = engine.plan(_device(_connection()), blueprint, scope="inventory")
    assert not server.calls and not plan.connections and plan.fully_resolved
    assert plan.skipped_sections["topology"] == "not in scope 'inventory'"
