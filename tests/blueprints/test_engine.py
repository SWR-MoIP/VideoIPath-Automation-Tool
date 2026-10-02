"""Engine configuration, read-only planning, execution phases, conflicts, and partial failures."""

from __future__ import annotations

import inspect
import subprocess
import sys
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel, ConfigDict

from tests.blueprints.conftest import NMOS, FakeInspectServer, FakeInventory, make_inspect_app, matrox_layout
from videoipath_automation_tool.apps.inspect.snapshot import InspectSnapshot
from videoipath_automation_tool.blueprints import (
    AlternativeAddress,
    ApplyOptions,
    Blueprint,
    BlueprintApplyError,
    BlueprintCapabilityError,
    BlueprintConflictError,
    BlueprintDevice,
    BlueprintEngine,
    BlueprintError,
    BlueprintPlan,
    BlueprintTargetError,
    BlueprintValidationError,
    Credentials,
    DeviceTarget,
    EndpointIdentity,
    ModuleTarget,
    NamingScheme,
    ProcessingContext,
    ProcessorInputError,
    ProcessorResult,
    VertexEdit,
    VertexPatch,
    VertexProcessor,
    published_json_schema,
)

MATROX = {
    "schema_version": 1,
    "inventory": {"default": {"driver_id": NMOS, "custom_settings": {"port": 8080}}},
    "topology": {
        "default": {
            "device": {"icon_size": "medium"},
            "ip_vertex_mapping": {"stream-a": ["P1"], "stream-b": ["P2"]},
            "vertex_processor": {
                "processor_type": "matrox.convertip.default",
                "params": {"redundant_streams": True, "video_sender_tags": ["video-tag-b"]},
            },
        },
        "receiver": {"vertex_processor": {"params": {"mode": "rx"}}},
    },
}


def _blueprint(document: dict[str, Any] = MATROX, **topology_default: Any) -> Blueprint:
    data = {
        **document,
        "topology": {**document["topology"], "default": {**document["topology"]["default"], **topology_default}},
    }
    return Blueprint.from_dict(data)


def _device(**fields: Any) -> BlueprintDevice:
    return BlueprintDevice(**{"key": "key-a", "label": "device-a", "inventory_id": "device1", **fields})


def _existing(inventory: FakeInventory, server: FakeInspectServer, mode: str = "tx") -> None:
    inventory.seed("device1", label="device-a", custom={"port": 8080, "indices_in_ids": False})
    server.install(matrox_layout("device1", mode))


# --- Construction and configuration ---


class _ExplodingApp:
    @property
    def inventory(self) -> Any:
        raise AssertionError("inventory accessed")

    @property
    def inspect(self) -> Any:
        raise AssertionError("inspect accessed")


class _Params(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    factory_label: str


class SimpleVideoProcessor(VertexProcessor[_Params]):
    params_model = _Params

    def process(self, context: ProcessingContext, params: _Params) -> ProcessorResult:
        vertex = context.require_vertex(kind="codec", factory_label=params.factory_label, vertex_type="In")
        return ProcessorResult(
            vertices=[
                VertexEdit(
                    vertex_id=vertex.id,
                    fields=VertexPatch(use_as_endpoint=True),
                    endpoint=EndpointIdentity(direction="TX", media="video", index=1),
                )
            ]
        )


def test_construction_is_lazy_and_injection_matches_configuration() -> None:
    options = ApplyOptions(sync="none", discovery_timeout=60)
    naming = NamingScheme(endpoint_label="{device.label}-{endpoint.index:02d}")
    injected = BlueprintEngine(
        _ExplodingApp(), processors={"example-org.simple": SimpleVideoProcessor}, options=options, naming=naming
    )
    configured = BlueprintEngine(_ExplodingApp())
    configured.register_processor("example-org.simple", SimpleVideoProcessor)
    configured.configure(options=options)
    configured.configure(naming=naming)
    assert (injected.options, injected.naming, injected.registry.ids()) == (
        configured.options,
        configured.naming,
        configured.registry.ids(),
    )
    configured.configure(options=None)
    assert configured.options == ApplyOptions() and configured.naming == naming
    with pytest.raises(ValueError, match="already registered"):
        configured.register_processor("example-org.simple", SimpleVideoProcessor)
    with pytest.raises(TypeError):
        configured.configure(options={"sync": "none"})  # type: ignore[arg-type]
    assert "example-org.simple" not in BlueprintEngine(_ExplodingApp()).registry


def test_apply_has_the_plan_signature_plus_dry_run() -> None:
    plan_parameters = list(inspect.signature(BlueprintEngine.plan).parameters.values())
    apply_parameters = list(inspect.signature(BlueprintEngine.apply).parameters.values())
    assert apply_parameters[:-1] == plan_parameters
    assert (apply_parameters[-1].name, apply_parameters[-1].default) == ("dry_run", False)
    assert inspect.signature(BlueprintPlan.apply).parameters["dry_run"].default is False


def test_normal_app_import_does_not_load_blueprints() -> None:
    code = "import sys, videoipath_automation_tool; print('videoipath_automation_tool.blueprints' in sys.modules, 'yaml' in sys.modules)"
    output = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout.split()
    assert output == ["False", "False"]


# --- Planning ---


def test_planning_is_read_only(
    engine: BlueprintEngine, inventory: FakeInventory, server: FakeInspectServer, app: Any
) -> None:
    _existing(inventory, server)
    inventory.devices["device1"].configuration.config.desc.label = "old"
    plan = engine.plan(_device(), _blueprint())
    assert plan.fully_resolved and plan.has_changes
    assert inventory.writes == [] and server.writes == []
    assert app.inspect._snapshot is None
    assert [phase.status for phase in plan.phases] == ["planned", "skipped", "no_change", "planned", "skipped"]
    assert plan.phase("inventory").operations[0].changes[0].model_dump() == {
        "field": "label",
        "before": "old",
        "after": "device-a",
        "source": "naming",
        "sensitive": False,
    }
    assert [b.port_id for b in plan.interface_bindings] == ["device1.dev.0.P1", "device1.dev.0.P2"]


def test_inventory_only_scope_never_touches_inspect(inventory: FakeInventory) -> None:
    inventory.seed("device1", label="device-a")
    app = SimpleNamespace(inventory=inventory)
    document = {**MATROX, "topology": {"default": {"vertex_processor": {"processor_type": "example-org.missing"}}}}
    result = BlueprintEngine(app).apply(_device(), Blueprint.from_dict(document), scope="inventory")
    assert result.status == "succeeded" and result.phase("topology").status == "skipped"
    assert inventory.devices["device1"].configuration.config.customSettings.port == 8080


def test_apply_then_reapply_converges(
    engine: BlueprintEngine, inventory: FakeInventory, server: FakeInspectServer
) -> None:
    _existing(inventory, server)
    result = engine.apply(_device(), _blueprint())
    assert result.status == "succeeded" and result.verification == "confirmed"
    assert [name for name, _ in server.writes] == ["update_topology"]
    labels = {f["fields"]["label"] for f in server.vertex_forms.values() if f["fields"]["useAsEndpoint"]}
    assert labels == {"device-a-TX-video-01", "device-a-TX-audio-01"}

    server.writes.clear()
    again = engine.apply(_device(), _blueprint())
    assert again.status == "no_change" and again.verification == "not_applicable"
    assert server.writes == [] and inventory.writes == []


def test_both_usage_styles_execute_the_same_workflow() -> None:
    outcomes = []
    for style in ("direct", "two-step"):
        inventory, server = FakeInventory(), FakeInspectServer()
        _existing(inventory, server)
        engine = BlueprintEngine(SimpleNamespace(inventory=inventory, inspect=make_inspect_app(server)))
        if style == "direct":
            result = engine.apply(_device(), _blueprint(), topology_variant="default")
        else:
            result = engine.plan(_device(), _blueprint(), topology_variant="default").apply()
        outcomes.append((result.model_dump(), server.writes, inventory.writes))
    assert outcomes[0] == outcomes[1]


def test_update_preserves_unmanaged_fields_and_redacts_secrets(
    engine: BlueprintEngine, inventory: FakeInventory, server: FakeInspectServer
) -> None:
    _existing(inventory, server)
    document = {**MATROX, "inventory": {"default": {"driver_id": NMOS, "custom_settings": {"disable_rx_sdp": True}}}}
    device = _device(
        credentials=Credentials(username="test-user", password="test-password"),
        alternative_addresses=[
            "192.0.2.20",
            AlternativeAddress(
                address="192.0.2.21", credentials=Credentials(username="test-user", password="alt-password")
            ),
        ],
    )
    plan = engine.plan(device, Blueprint.from_dict(document), scope="inventory")
    summary = plan.summary()
    assert "test-password" not in summary and "alt-password" not in summary and "********" in summary
    assert "test-password" not in repr(device) and "test-password" not in plan.model_dump_json()
    plan.apply()
    stored = inventory.devices["device1"].configuration
    assert stored.config.customSettings.port == 8080 and stored.config.customSettings.indices_in_ids is False
    assert stored.config.customSettings.disable_rx_sdp is True
    assert (stored.config.cinfo.auth.user, stored.config.cinfo.auth.password) == ("test-user", "test-password")
    assert stored.config.cinfo.altAddresses == ["192.0.2.20", "192.0.2.21"]
    assert stored.config.cinfo.altAddressesWithAuth == [
        {"address": "192.0.2.21", "authentication": {"user": "test-user", "password": "alt-password"}}
    ]
    # A changed password alone still writes; omission preserves it.
    changed = device.model_copy(update={"credentials": Credentials(username="test-user", password="new-password")})
    assert engine.plan(changed, Blueprint.from_dict(document), scope="inventory").phase("inventory").status == "planned"
    assert (
        engine.plan(_device(), Blueprint.from_dict(document), scope="inventory").phase("inventory").status
        == "no_change"
    )


def test_api_key_is_redacted_in_the_plan(engine: BlueprintEngine) -> None:
    secret = "synthetic-key-value"
    document = {
        "schema_version": 1,
        "inventory": {
            "default": {
                "driver_id": "com.nevion.spg9000-0.1.0",
                "custom_settings": {"x_api_key": secret},
            }
        },
    }
    device = BlueprintDevice(key="key-a", label="device-a", management_address="192.0.2.40")
    plan = engine.plan(device, Blueprint.from_dict(document), scope="inventory")
    change = next(
        item for item in plan.phase("inventory").operations[0].changes if item.field == "custom_settings.x_api_key"
    )
    assert change.sensitive and change.after == "********"
    assert secret not in plan.summary()
    assert secret not in plan.model_dump_json()


def test_inventory_binding_rules(engine: BlueprintEngine, inventory: FakeInventory, server: FakeInspectServer) -> None:
    inventory.seed("device1", label="device-a", address="192.0.2.10")
    with pytest.raises(BlueprintTargetError, match="'device9' was not found"):
        engine.plan(_device(inventory_id="device9"), _blueprint(), scope="inventory")
    new = BlueprintDevice(key="key-b", label="device-a", management_address="192.0.2.10")
    with pytest.raises(BlueprintTargetError, match="used by device1.*Bind the existing record"):
        engine.plan(new, _blueprint(), scope="inventory")
    assert inventory.address_lookups == 1
    with pytest.raises(BlueprintTargetError, match="requires 'management_address'"):
        engine.plan(BlueprintDevice(key="key-b", label="device-b"), _blueprint(), scope="inventory")
    other_driver = {**MATROX, "inventory": {"default": {"driver_id": "com.nevion.NMOS-0.1.0"}}}
    with pytest.raises(BlueprintCapabilityError, match="Driver migration"):
        engine.plan(_device(), Blueprint.from_dict(other_driver), scope="inventory")


def test_snmp_references_resolve_exactly(engine: BlueprintEngine, inventory: FakeInventory) -> None:
    inventory.seed("device1", label="device-a")

    def plan_with(reference: Any) -> Any:
        document = {**MATROX, "inventory": {"default": {"driver_id": NMOS, "snmp": {"configuration": reference}}}}
        return engine.plan(_device(), Blueprint.from_dict(document), scope="inventory")

    assert plan_with("snmp-a").phase("inventory").operations[0].changes[0].after == "snmp-1"
    assert plan_with({"id": "default"}).phase("inventory").status == "no_change"
    with pytest.raises(BlueprintTargetError, match="No SNMP configuration"):
        plan_with("missing")
    inventory.snmp["snmp-2"] = "snmp-a"
    with pytest.raises(BlueprintTargetError, match="ambiguous"):
        plan_with("snmp-a")


# --- Creation, discovery, and synchronization ---


def test_create_discover_and_configure(
    engine: BlueprintEngine, inventory: FakeInventory, server: FakeInspectServer
) -> None:
    device = BlueprintDevice(key="key-new", label="device-new", management_address="192.0.2.50")
    plan = engine.plan(device, _blueprint())
    assert not plan.fully_resolved and plan.phase("topology").status == "deferred"
    assert "materialized during apply()" in plan.summary()

    server.discoverable["device100"] = matrox_layout("device100", "tx")
    result = plan.apply()
    assert result.status == "succeeded" and result.materialized
    assert (result.inventory_id, result.topology_device_id) == ("device100", "device100")
    assert [name for name, _ in server.writes] == ["add_devices", "sync_devices", "update_topology"]
    assert [op.action for op in result.phase("topology_sync").operations] == ["add_to_topology", "sync"]
    assert server.vertex_forms["device100.0.vs.v"]["fields"]["label"] == "device-new-TX-video-01"


def test_discovery_timeout_reports_created_id(engine: BlueprintEngine, server: FakeInspectServer) -> None:
    device = BlueprintDevice(key="key-new", label="device-new", management_address="192.0.2.50")
    with pytest.raises(BlueprintApplyError) as info:
        engine.apply(device, _blueprint(), options=ApplyOptions(discovery_timeout=3, poll_interval=1))
    result = info.value.result
    assert result.status == "partial" and result.inventory_id == "device100"
    assert result.phase("inventory").status == "completed"
    assert result.phase("discovery").status == "failed"
    assert "not ready after 3s" in result.phase("discovery").message
    assert [name for name, _ in server.writes].count("add_devices") == 4


def test_sync_policies(engine: BlueprintEngine, inventory: FakeInventory, server: FakeInspectServer) -> None:
    inventory.seed("device1", label="device-a", custom={"port": 8080})
    with pytest.raises(BlueprintTargetError, match="not in the topology"):
        engine.plan(_device(), _blueprint(), options=ApplyOptions(sync="none"))

    server.install(matrox_layout("device1", "tx"))
    server.sync["device1"] = {"add": {}, "update": {"x": 1}, "remove": {}}
    with pytest.raises(BlueprintCapabilityError, match="add_only' is insufficient"):
        engine.plan(_device(), _blueprint())
    warned = engine.plan(_device(), _blueprint(), options=ApplyOptions(sync="none"))
    assert warned.fully_resolved and warned.diagnostics[0].code == "topology.sync_pending"

    result = engine.apply(_device(), _blueprint(), options=ApplyOptions(sync="reconcile"))
    assert ("sync_devices", ("device1", False)) in server.writes and result.materialized


def test_sync_lookup_failure_fails_planning(
    engine: BlueprintEngine, inventory: FakeInventory, server: FakeInspectServer
) -> None:
    _existing(inventory, server)
    server.fail_sync_info = ConnectionError("sync lookup failed")
    with pytest.raises(BlueprintError, match="synchronization status") as info:
        engine.plan(_device(), _blueprint())
    assert type(info.value) is BlueprintError


# --- Conflicts and staged edits ---


def test_stale_plans_are_rejected(engine: BlueprintEngine, inventory: FakeInventory, server: FakeInspectServer) -> None:
    _existing(inventory, server)
    inventory.devices["device1"].configuration.config.desc.label = "old"
    plan = engine.plan(_device(), _blueprint())
    inventory.devices["device1"].configuration.config.desc.label = "edited-elsewhere"
    with pytest.raises(BlueprintApplyError) as info:
        plan.apply()
    assert info.value.result.status == "failed" and isinstance(info.value.__cause__, BlueprintConflictError)
    assert inventory.writes == []

    inventory.devices["device1"].configuration.config.desc.label = "device-a"
    plan = engine.plan(_device(), _blueprint())
    server.vertex_forms["device1.0.vs.v"]["fields"]["desc"] = "edited-elsewhere"
    with pytest.raises(BlueprintApplyError, match="changed since planning"):
        plan.apply()
    assert server.writes == []


def test_staged_edits_overlap_is_rejected_and_unrelated_edits_survive(
    engine: BlueprintEngine, inventory: FakeInventory, server: FakeInspectServer, app: Any
) -> None:
    _existing(inventory, server)
    app.inspect._snapshot = InspectSnapshot(fetcher=server, device_items=server.get_device_skeleton())
    app.inspect._snapshot.stage_edit("vertex", "device1.0.vs.v", "label", "pending")
    app.inspect._snapshot.stage_edit("vertex", "device1.0.P1.in", "label", "unrelated")
    with pytest.raises(BlueprintApplyError, match="Pending uncommitted Inspect edits overlap"):
        engine.apply(_device(), _blueprint())
    app.inspect._snapshot.clear_staged(kind="vertex", entity_id="device1.0.vs.v")
    assert engine.apply(_device(), _blueprint()).status == "succeeded"
    assert app.inspect._snapshot.get_staged_edits("vertex", "device1.0.P1.in") == {"label": "unrelated"}


# --- Failures ---


@pytest.mark.parametrize(
    ("error", "status"), [(ConnectionError("timeout"), "unknown"), (BlueprintConflictError("x"), "partial")]
)
def test_commit_failure_outcomes(
    engine: BlueprintEngine, inventory: FakeInventory, server: FakeInspectServer, error: Exception, status: str
) -> None:
    _existing(inventory, server)
    inventory.devices["device1"].configuration.config.desc.label = "old"
    server.fail_commit = error
    with pytest.raises(BlueprintApplyError) as info:
        engine.apply(_device(), _blueprint())
    result = info.value.result
    assert result.status == status and result.phase("inventory").status == "completed"
    assert result.phase("topology").status == ("unknown" if status == "unknown" else "failed")
    assert info.value.__cause__ is error


def test_inventory_write_unknown_outcome(
    engine: BlueprintEngine, inventory: FakeInventory, server: FakeInspectServer
) -> None:
    _existing(inventory, server)
    inventory.devices["device1"].configuration.config.desc.label = "old"
    inventory.fail_next_write = TimeoutError("read timed out")
    with pytest.raises(BlueprintApplyError) as info:
        engine.apply(_device(), _blueprint())
    assert info.value.result.status == "unknown" and info.value.result.phase("topology").status == "not_run"


def test_inventory_preread_failure_is_a_known_rejection(
    engine: BlueprintEngine, inventory: FakeInventory, server: FakeInspectServer
) -> None:
    _existing(inventory, server)
    inventory.devices["device1"].configuration.config.desc.label = "old"
    inventory.fail_next_write = ValueError("Failed to retrieve existing device configuration from Inventory: timed out")
    with pytest.raises(BlueprintApplyError) as info:
        engine.apply(_device(), _blueprint())
    result = info.value.result
    assert result.status == "failed" and result.phase("inventory").status == "failed"
    assert result.verification == "not_applicable"
    assert inventory.writes == []


# --- Modules ---


def _chassis(server: FakeInspectServer, inventory: FakeInventory) -> None:
    inventory.seed("device1", label="chassis-a")
    layout = matrox_layout("device1", "rx", module="device1.dev.1")
    sibling = matrox_layout("device1", "tx", module="device1.dev.2")
    layout["node"]["modules"].update(sibling["node"]["modules"])
    layout["vertex_forms"].update(sibling["vertex_forms"])
    layout["node"]["modules"]["device1.dev.1"]["tagsInfo"]["assigned"] = {
        "all": ["inherited", "keep"],
        "local": {"keep": {}, "old": {}},
    }
    server.install(layout)


def test_module_target_scope_and_tags(
    engine: BlueprintEngine, inventory: FakeInventory, server: FakeInspectServer
) -> None:
    _chassis(server, inventory)
    document = {
        "schema_version": 1,
        "topology": {
            "default": {
                "module": {"tags": {"add": ["new"], "remove": ["old"]}},
                "vertex_processor": {"processor_type": "matrox.convertip.default"},
            }
        },
    }
    module = BlueprintDevice(
        key="module-a",
        label="module-a",
        topology=ModuleTarget(device_id="device1", module_id="device1.dev.1"),
        module_position="1",
    )
    result = engine.apply(module, Blueprint.from_dict(document))
    assert result.status == "succeeded" and result.verification == "confirmed"
    assert [(name, payload) for name, payload in server.writes if name != "update_topology"] == [
        ("assign", ("new", ("device:device1.dev.1",))),
        ("unassign", ("old", ("device:device1.dev.1",))),
    ]
    delta = next(payload for name, payload in server.writes if name == "update_topology")
    assert delta["replaceDevices"] == {}
    assert all(vertex_id.startswith("device1.1.") for vertex_id in delta["replaceVertices"])
    assert server.vertex_forms["device1.1.vr.v"]["fields"]["label"] == "module-a-M1-RX-video-01"
    assert inventory.writes == []


def _mark_endpoint(server: FakeInspectServer, vertex_id: str) -> None:
    for node in server.nodes.values():
        for module in node["modules"].values():
            for port in module["ports"].values():
                info = port["vertexInfo"]
                sides = [info] if "id" in info else [side for side in (info.get("in"), info.get("out")) if side]
                for side in sides:
                    if side.get("id") == vertex_id:
                        side["fields"]["isEndpoint"] = True
                        return
    raise AssertionError(vertex_id)


def test_sibling_endpoint_label_change_rejects_the_plan(
    engine: BlueprintEngine, inventory: FakeInventory, server: FakeInspectServer
) -> None:
    _chassis(server, inventory)
    sibling = "device1.2.vs.v"
    _mark_endpoint(server, sibling)
    server.vertex_forms[sibling]["fields"]["label"] = "sibling-endpoint"
    module = BlueprintDevice(
        key="module-a",
        label="module-a",
        topology=ModuleTarget(device_id="device1", module_id="device1.dev.1"),
    )
    document = {
        "schema_version": 1,
        "topology": {"default": {"vertex_processor": {"processor_type": "matrox.convertip.default"}}},
    }
    plan = engine.plan(module, Blueprint.from_dict(document))
    assert plan.fully_resolved
    server.vertex_forms[sibling]["fields"]["label"] = "renamed-endpoint"
    with pytest.raises(BlueprintApplyError, match="changed since planning") as info:
        plan.apply()
    assert isinstance(info.value.__cause__, BlueprintConflictError)
    assert server.writes == []


def test_module_target_rejections(engine: BlueprintEngine, inventory: FakeInventory, server: FakeInspectServer) -> None:
    _chassis(server, inventory)
    module = BlueprintDevice(
        key="module-a", label="module-a", topology=ModuleTarget(device_id="device1", module_id="device1.dev.1")
    )
    device_settings = {"schema_version": 1, "topology": {"default": {"device": {"icon_type": "monitor"}}}}
    with pytest.raises(BlueprintTargetError, match="cannot be applied to a module target"):
        engine.plan(module, Blueprint.from_dict(device_settings))
    missing = module.model_copy(update={"topology": ModuleTarget(device_id="device1", module_id="device2.dev.1")})
    with pytest.raises(BlueprintTargetError, match="does not belong"):
        engine.plan(missing, Blueprint.from_dict({"schema_version": 1, "topology": {"default": {}}}))


def test_module_tag_failure_is_a_partial_result(
    engine: BlueprintEngine, inventory: FakeInventory, server: FakeInspectServer
) -> None:
    _chassis(server, inventory)
    server.fail_tag = "old"
    document = {
        "schema_version": 1,
        "topology": {
            "default": {
                "module": {"tags": ["keep", "new"]},
                "vertex_processor": {"processor_type": "matrox.convertip.default"},
            }
        },
    }
    module = BlueprintDevice(
        key="module-a", label="module-a", topology=ModuleTarget(device_id="device1", module_id="device1.dev.1")
    )
    with pytest.raises(BlueprintApplyError) as info:
        engine.apply(module, Blueprint.from_dict(document))
    result = info.value.result
    assert result.status == "partial"
    assert result.phase("topology").status == "completed"
    assert result.phase("module_tags").status == "failed"
    assert result.verification == "unconfirmed"
    assert result.verification_detail is not None and "topology read-back did not run" in result.verification_detail
    assert [op.action for op in result.phase("module_tags").operations] == ["assign_tag"]


# --- Naming, overrides, mapping, custom processors ---


def test_label_collisions_and_overrides(
    engine: BlueprintEngine, inventory: FakeInventory, server: FakeInspectServer
) -> None:
    _existing(inventory, server)
    colliding = NamingScheme(endpoint_label="{device.label}-{endpoint.direction}")
    with pytest.raises(BlueprintValidationError, match="Endpoint label collision"):
        engine.plan(_device(), _blueprint(), naming=colliding)
    assert engine.plan(
        _device(), _blueprint(), naming=colliding, options=ApplyOptions(naming_collisions="allow")
    ).has_changes

    overrides = [{"factory_label": "Audio Sender", "direction": "In", "fields": {"label": "custom-audio"}}]
    plan = engine.plan(_device(), _blueprint(vertices=overrides), naming=colliding)
    changes = {op.entity_id: {c.field: c for c in op.changes} for op in plan.phase("topology").operations}
    assert changes["device1.0.as.v"]["label"].after == "custom-audio"
    assert changes["device1.0.as.v"]["label"].source.startswith("override:")

    with pytest.raises(BlueprintTargetError, match="must match exactly one vertex"):
        engine.plan(_device(), _blueprint(vertices=[{"factory_label": "P1", "fields": {"active": False}}]))


def test_interface_mapping_rules(engine: BlueprintEngine, inventory: FakeInventory, server: FakeInspectServer) -> None:
    _existing(inventory, server)
    mapping = {"a": ["X{module.position}", "P{module.position}"], "b": ["P2"]}
    plan = engine.plan(_device(module_position="1"), _blueprint(ip_vertex_mapping=mapping))
    assert [(b.key, b.candidate, b.out_vertex_id) for b in plan.interface_bindings] == [
        ("a", "P1", "device1.0.P1.out"),
        ("b", "P2", "device1.0.P2.out"),
    ]
    with pytest.raises(BlueprintTargetError, match="no IP port .* matches 'X1', 'X2'"):
        engine.plan(_device(), _blueprint(ip_vertex_mapping={"a": ["X1", "X2"]}))
    with pytest.raises(BlueprintValidationError, match="requires BlueprintDevice.module_position"):
        engine.plan(_device(), _blueprint(ip_vertex_mapping={"a": ["P{module.position}"]}))


def test_custom_processor_and_naming_change_rename_the_same_ids(
    inventory: FakeInventory, server: FakeInspectServer, app: Any
) -> None:
    _existing(inventory, server)
    engine = BlueprintEngine(app, processors={"example-org.simple-video": SimpleVideoProcessor})
    document = {
        "schema_version": 1,
        "topology": {
            "default": {
                "vertex_processor": {
                    "processor_type": "example-org.simple-video",
                    "params": {"factory_label": "Video Sender"},
                }
            }
        },
    }
    plan = engine.plan(_device(), Blueprint.from_dict(document))
    engine.register_processor("example-org.later", SimpleVideoProcessor)  # does not affect the existing plan
    engine.configure(naming=NamingScheme(endpoint_label="{device.label}-later"))
    plan.apply()
    assert server.vertex_forms["device1.0.vs.v"]["fields"]["label"] == "device-a-TX-video-01"

    engine.apply(_device(), Blueprint.from_dict(document), naming=NamingScheme(endpoint_label="{device.label}-video"))
    assert server.vertex_forms["device1.0.vs.v"]["fields"]["label"] == "device-a-video"


def test_topology_only_virtual_device(engine: BlueprintEngine, server: FakeInspectServer) -> None:
    layout = matrox_layout("virtual.1", "tx")
    layout["node"] = {"_id": "virtual-1", "modules": {}}
    server.install(layout)
    server.nodes["virtual-1"] = server.nodes.pop("virtual.1")
    device = BlueprintDevice(key="virtual-a", label="virtual-a", topology=DeviceTarget(device_id="virtual.1"))
    document = {"schema_version": 1, "topology": {"default": {"device": {"icon_type": "server"}}}}
    result = engine.apply(device, Blueprint.from_dict(document))
    assert result.status == "succeeded"
    assert server.device_forms["virtual.1"]["iconType"] == "server"
    assert server.device_forms["virtual.1"]["descriptor"]["label"] == "virtual-a"


def test_from_inventory_and_engine_validation(engine: BlueprintEngine, inventory: FakeInventory) -> None:
    record = inventory.seed("device1", label="device-a")
    device = BlueprintDevice.from_inventory(record)
    assert (device.key, device.label, device.inventory_id, device.management_address) == (
        "device1",
        "device-a",
        "device1",
        None,
    )
    engine.validate(_blueprint())
    unknown = {"schema_version": 1, "topology": {"default": {"vertex_processor": {"processor_type": "example-org.x"}}}}
    with pytest.raises(BlueprintValidationError, match="not registered"):
        engine.validate(Blueprint.from_dict(unknown))


class _ModeParams(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    mode: str


class MisbehavingProcessor(VertexProcessor[_ModeParams]):
    """Returns deliberately invalid output to exercise the engine's output validation."""

    params_model = _ModeParams

    def process(self, context: ProcessingContext, params: _ModeParams) -> Any:
        codec = context.find_vertices(kind="codec")[0]
        if params.mode == "sibling":
            return ProcessorResult(vertices=[VertexEdit(vertex_id="device1.2.vs.v", fields=VertexPatch(active=False))])
        if params.mode == "device-patch":
            return ProcessorResult(device={"icon_type": "monitor"})
        if params.mode == "conflict":
            return ProcessorResult(
                vertices=[
                    VertexEdit(vertex_id=codec.id, fields=VertexPatch(label="a")),
                    VertexEdit(vertex_id=codec.id, fields=VertexPatch(label="b")),
                ]
            )
        if params.mode == "duplicate":
            edit = VertexEdit(vertex_id=codec.id, fields=VertexPatch(active=True))
            return ProcessorResult(vertices=[edit, edit])
        if params.mode == "bypass":
            return ProcessorResult.model_construct(
                vertices=[VertexEdit.model_construct(vertex_id=codec.id, fields={"label": 5})]
            )
        if params.mode == "sdp-on-ip":
            ip = context.find_vertices(kind="ip")[0]
            return ProcessorResult(vertices=[VertexEdit(vertex_id=ip.id, fields=VertexPatch(sdp_support=True))])
        if params.mode == "wrong-type":
            return {"vertices": []}
        raise RuntimeError("boom")


@pytest.mark.parametrize(
    ("mode", "error", "message"),
    [
        ("sibling", BlueprintTargetError, "outside module 'device1.dev.1'"),
        ("device-patch", BlueprintTargetError, "device-wide changes for a module target"),
        ("conflict", ProcessorInputError, "conflicting 'label' values"),
        ("bypass", ProcessorInputError, "invalid result"),
        ("sdp-on-ip", BlueprintCapabilityError, "only supported on codec vertices"),
        ("wrong-type", ProcessorInputError, "must return a ProcessorResult"),
        ("crash", ProcessorInputError, "failed: RuntimeError: boom"),
    ],
)
def test_processor_output_is_validated(
    inventory: FakeInventory, server: FakeInspectServer, app: Any, mode: str, error: type, message: str
) -> None:
    _chassis(server, inventory)
    engine = BlueprintEngine(app, processors={"example-org.bad": MisbehavingProcessor})
    document = {
        "schema_version": 1,
        "topology": {"default": {"vertex_processor": {"processor_type": "example-org.bad", "params": {"mode": mode}}}},
    }
    module = BlueprintDevice(
        key="module-a", label="module-a", topology=ModuleTarget(device_id="device1", module_id="device1.dev.1")
    )
    with pytest.raises(error, match=message):
        engine.plan(module, Blueprint.from_dict(document))
    assert server.writes == []


def test_identical_duplicate_edits_are_deduplicated(
    inventory: FakeInventory, server: FakeInspectServer, app: Any
) -> None:
    _chassis(server, inventory)
    engine = BlueprintEngine(app, processors={"example-org.bad": MisbehavingProcessor})
    document = {
        "schema_version": 1,
        "topology": {
            "default": {"vertex_processor": {"processor_type": "example-org.bad", "params": {"mode": "duplicate"}}}
        },
    }
    module = BlueprintDevice(
        key="module-a", label="module-a", topology=ModuleTarget(device_id="device1", module_id="device1.dev.1")
    )
    assert engine.plan(module, Blueprint.from_dict(document)).phase("topology").status == "no_change"


def test_module_tag_baseline_conflict_after_topology_commit(
    engine: BlueprintEngine, inventory: FakeInventory, server: FakeInspectServer
) -> None:
    _chassis(server, inventory)
    document = {
        "schema_version": 1,
        "topology": {
            "default": {
                "module": {"tags": ["keep", "new"]},
                "vertex_processor": {"processor_type": "matrox.convertip.default"},
            }
        },
    }
    module = BlueprintDevice(
        key="module-a", label="module-a", topology=ModuleTarget(device_id="device1", module_id="device1.dev.1")
    )
    plan = engine.plan(module, Blueprint.from_dict(document))
    original_commit = server.update_topology

    def commit_then_retag(delta: Any) -> Any:
        response = original_commit(delta)
        server.nodes["device1"]["modules"]["device1.dev.1"]["tagsInfo"]["assigned"]["local"]["other"] = {}
        return response

    server.update_topology = commit_then_retag  # type: ignore[method-assign]
    with pytest.raises(BlueprintApplyError) as info:
        plan.apply()
    result = info.value.result
    assert (result.status, result.phase("topology").status, result.phase("module_tags").status) == (
        "partial",
        "completed",
        "failed",
    )
    assert not [name for name, _ in server.writes if name in ("assign", "unassign")]


def test_module_tags_without_local_distinction_allow_only_additions(
    engine: BlueprintEngine, inventory: FakeInventory, server: FakeInspectServer
) -> None:
    _chassis(server, inventory)
    server.nodes["device1"]["modules"]["device1.dev.1"]["tagsInfo"] = {"assigned": {"all": ["inherited"]}}
    module = BlueprintDevice(
        key="module-a", label="module-a", topology=ModuleTarget(device_id="device1", module_id="device1.dev.1")
    )

    def plan_with(tags: Any) -> Any:
        return engine.plan(
            module, Blueprint.from_dict({"schema_version": 1, "topology": {"default": {"module": {"tags": tags}}}})
        )

    with pytest.raises(BlueprintCapabilityError, match="cannot be distinguished"):
        plan_with(["keep"])
    with pytest.raises(BlueprintCapabilityError, match="cannot be distinguished"):
        plan_with({"remove": ["inherited"]})
    assert [op.action for op in plan_with({"add": ["new"]}).phase("module_tags").operations] == ["assign_tag"]


def test_module_with_own_inventory_record_never_touches_the_parent(
    engine: BlueprintEngine, inventory: FakeInventory, server: FakeInspectServer
) -> None:
    _chassis(server, inventory)
    inventory.seed("device5", label="module-a", address="192.0.2.55", custom={"port": 80})
    server.sync["device1"] = {"add": {"x": 1}, "update": {}, "remove": {}}
    module = BlueprintDevice(
        key="module-a",
        label="module-a",
        inventory_id="device5",
        topology=ModuleTarget(device_id="device1", module_id="device1.dev.1"),
    )
    plan = engine.plan(module, _blueprint(device=None))
    assert plan.phase("inventory").status == "planned" and plan.phase("topology").status == "deferred"
    result = plan.apply()
    assert result.status == "succeeded" and result.materialized
    assert inventory.writes == [("update", "device5")]
    assert not [name for name, _ in server.writes if name in ("add_devices", "sync_devices")]
    delta = next(payload for name, payload in server.writes if name == "update_topology")
    assert delta["replaceDevices"] == {} and all(v.startswith("device1.1.") for v in delta["replaceVertices"])


# --- Dry run ---


def test_dry_run_checks_everything_but_writes_nothing(
    engine: BlueprintEngine, inventory: FakeInventory, server: FakeInspectServer, app: Any
) -> None:
    _existing(inventory, server)
    inventory.devices["device1"].configuration.config.desc.label = "old"
    plan = engine.plan(_device(), _blueprint())

    preview = plan.apply(dry_run=True)
    assert (preview.status, preview.dry_run, preview.ok, preview.verification) == (
        "planned",
        True,
        True,
        "not_applicable",
    )
    assert [(p.name, p.status) for p in preview.phases] == [
        ("inventory", "planned"),
        ("discovery", "skipped"),
        ("topology_sync", "no_change"),
        ("topology", "planned"),
        ("module_tags", "skipped"),
        ("verification", "skipped"),
    ]
    assert preview.phase("topology").operations == plan.phase("topology").operations
    assert [b.key for b in preview.interface_bindings] == ["stream-a", "stream-b"]
    assert inventory.writes == [] and server.writes == [] and app.inspect._snapshot is None

    result = plan.apply()  # the same plan still applies after a dry run
    assert result.status == "succeeded" and not result.dry_run
    assert engine.apply(_device(), _blueprint(), dry_run=True).status == "no_change"


def test_dry_run_detects_stale_plans(
    engine: BlueprintEngine, inventory: FakeInventory, server: FakeInspectServer
) -> None:
    _existing(inventory, server)
    plan = engine.plan(_device(), _blueprint())
    server.vertex_forms["device1.0.vs.v"]["fields"]["desc"] = "edited-elsewhere"
    with pytest.raises(BlueprintApplyError) as info:
        plan.apply(dry_run=True)
    assert info.value.result.status == "failed" and info.value.result.dry_run
    assert server.writes == []


def test_dry_run_reports_deferred_work_for_creation(
    engine: BlueprintEngine, inventory: FakeInventory, server: FakeInspectServer
) -> None:
    device = BlueprintDevice(key="key-new", label="device-new", management_address="192.0.2.50")
    result = engine.apply(device, _blueprint(), dry_run=True)
    assert result.status == "planned" and result.inventory_id is None
    assert result.phase("inventory").operations[0].action == "create"
    assert {result.phase(name).status for name in ("discovery", "topology_sync", "topology", "module_tags")} == {
        "deferred"
    }
    assert inventory.writes == [] and server.writes == []


def test_dry_run_module_tags(engine: BlueprintEngine, inventory: FakeInventory, server: FakeInspectServer) -> None:
    _chassis(server, inventory)
    document = {"schema_version": 1, "topology": {"default": {"module": {"tags": ["keep", "new"]}}}}
    module = BlueprintDevice(
        key="module-a", label="module-a", topology=ModuleTarget(device_id="device1", module_id="device1.dev.1")
    )
    result = engine.apply(module, Blueprint.from_dict(document), dry_run=True)
    assert result.phase("module_tags").status == "planned"
    assert [op.action for op in result.phase("module_tags").operations] == ["assign_tag", "unassign_tag"]
    assert server.writes == []


class _KindFieldParams(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    ports_on_ip: bool = False


class KindFieldProcessor(VertexProcessor[_KindFieldParams]):
    """Proposes destination ports (codec) and static IGMP support (IP)."""

    params_model = _KindFieldParams

    def process(self, context: ProcessingContext, params: _KindFieldParams) -> ProcessorResult:
        codec = context.require_vertex(kind="codec", factory_label="Video Sender")
        ip = context.require_vertex(kind="ip", factory_label="P1", vertex_type="Out")
        port_target = ip if params.ports_on_ip else codec
        return ProcessorResult(
            vertices=[
                VertexEdit(
                    vertex_id=port_target.id,
                    fields=VertexPatch(main_destination_port=50311, spare_destination_port=50312),
                ),
                VertexEdit(vertex_id=ip.id, fields=VertexPatch(supports_static_igmp=True)),
            ]
        )


def test_kind_specific_fields_round_trip(inventory: FakeInventory, server: FakeInspectServer, app: Any) -> None:
    _existing(inventory, server)
    engine = BlueprintEngine(app, processors={"example-org.kind-fields": KindFieldProcessor})
    document = {
        "schema_version": 1,
        "topology": {"default": {"vertex_processor": {"processor_type": "example-org.kind-fields"}}},
    }
    result = engine.apply(_device(), Blueprint.from_dict(document), scope="topology")
    assert result.status == "succeeded" and result.verification == "confirmed"
    generic = server.vertex_forms["device1.0.vs.v"]["fields"]["typeFields"]["generic"]
    assert (generic["mainDstInfo"]["port"], generic["spareDstInfo"]["port"]) == (50311, 50312)
    assert server.vertex_forms["device1.0.P1.out"]["fields"]["typeFields"]["supportsStaticIgmpCfg"] is True
    assert (
        engine.plan(_device(), Blueprint.from_dict(document), scope="topology").phase("topology").status == "no_change"
    )

    wrong = {
        "schema_version": 1,
        "topology": {
            "default": {
                "vertex_processor": {"processor_type": "example-org.kind-fields", "params": {"ports_on_ip": True}}
            }
        },
    }
    with pytest.raises(BlueprintCapabilityError, match="'main_destination_port' is only supported on codec vertices"):
        engine.plan(_device(), Blueprint.from_dict(wrong), scope="topology")


def test_engine_schema_lists_only_registered_processors(app: Any) -> None:
    engine = BlueprintEngine(app, processors={"example-org.simple-video": SimpleVideoProcessor})
    spec = engine.json_schema()["$defs"]["VertexProcessorSpec"]
    assert spec["properties"]["processor_type"]["enum"] == ["example-org.simple-video", "matrox.convertip.default"]
    assert "enum" not in published_json_schema()["$defs"]["VertexProcessorSpec"]["properties"]["processor_type"]
