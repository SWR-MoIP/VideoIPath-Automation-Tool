"""Regression coverage for captured Inventory, synchronization, and naming state."""

from __future__ import annotations

from typing import Any, Literal

import pytest
from pydantic import BaseModel, ConfigDict

from tests.provisioning.conftest import NMOS, FakeInspectServer, FakeInventory, matrox_layout
from tests.provisioning.test_engine import _blueprint, _device, _existing
from videoipath_automation_tool.provisioning import (
    ApplyOptions,
    Blueprint,
    Field,
    Join,
    ModuleTarget,
    NameContext,
    NamingScheme,
    ProcessingContext,
    ProcessorResult,
    ProvisioningApplyError,
    ProvisioningConflictError,
    ProvisioningDevice,
    ProvisioningEngine,
    ProvisioningError,
    TopologyNotReadyError,
    VertexEdit,
    VertexPatch,
    VertexProcessor,
)


@pytest.mark.parametrize("dry_run", [False, True])
@pytest.mark.parametrize("changed", ["managed_setting", "driver"])
def test_unchanged_inventory_rechecks_baseline(
    engine: ProvisioningEngine,
    inventory: FakeInventory,
    server: FakeInspectServer,
    dry_run: bool,
    changed: str,
) -> None:
    _existing(inventory, server)
    plan = engine.plan(_device(), _blueprint())
    assert plan.phase("inventory").status == "no_change"
    if changed == "managed_setting":
        inventory.devices["device1"].configuration.config.customSettings.port = 9090
    else:
        inventory.devices["device1"].configuration.config.driver.version = "0.2.0"

    with pytest.raises(ProvisioningApplyError, match="changed since planning") as caught:
        plan.apply(dry_run=dry_run)
    assert isinstance(caught.value.__cause__, ProvisioningConflictError)
    assert ("driver_id" if changed == "driver" else "custom_settings.port") in str(caught.value)
    assert caught.value.result.phase("inventory").status == "failed"
    assert inventory.writes == [] and server.writes == []


@pytest.mark.parametrize("dry_run", [False, True])
def test_unchanged_inventory_allows_unmanaged_changes(
    engine: ProvisioningEngine, inventory: FakeInventory, server: FakeInspectServer, dry_run: bool
) -> None:
    _existing(inventory, server)
    plan = engine.plan(_device(), _blueprint())
    inventory.devices["device1"].configuration.metadata["note"] = "updated externally"

    result = plan.apply(dry_run=dry_run)
    assert result.status == ("planned" if dry_run else "succeeded")
    assert result.phase("inventory").status == "no_change" and inventory.writes == []
    assert inventory.devices["device1"].configuration.metadata["note"] == "updated externally"


class _ContextParams(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class _InventoryContextProcessor(VertexProcessor[_ContextParams]):
    params_model = _ContextParams

    def process(self, context: ProcessingContext, params: _ContextParams) -> ProcessorResult:
        assert context.inventory is not None and context.inventory.inventory_id == "device5"
        assert context.owner is not None and context.owner.inventory_id == "device1"
        vertex = context.require_vertex(factory_label="Video Sender")
        if vertex.kind is None:
            raise TopologyNotReadyError("Waiting for the vertex edit form.")
        return ProcessorResult(
            vertices=[VertexEdit(vertex_id=vertex.id, fields=VertexPatch(label=context.inventory.inventory_id))]
        )


@pytest.mark.parametrize("require_reachable", [False, True])
def test_deferred_processor_keeps_unchanged_inventory_context(
    engine: ProvisioningEngine, inventory: FakeInventory, server: FakeInspectServer, require_reachable: bool
) -> None:
    _existing(inventory, server)
    inventory.seed("device5", label="module-a", address="192.0.2.55")
    engine.register_processor("example-org.inventory-context", _InventoryContextProcessor)
    device = ProvisioningDevice(
        key="module-a",
        label="module-a",
        inventory_id="device5",
        topology=ModuleTarget(device_id="device1", module_id="device1.dev.0"),
    )
    blueprint = Blueprint.from_dict(
        {
            "schema_version": 1,
            "defaults": {
                "inventory": {"driver_id": NMOS},
                "topology": {"vertex_processor": {"processor_type": "example-org.inventory-context"}},
            },
        }
    )
    form = server.vertex_forms.pop("device1.0.vs.v")
    plan = engine.plan(device, blueprint, options=ApplyOptions(require_reachable=require_reachable))
    assert not plan.fully_resolved and plan.phase("inventory").status == "no_change"
    server.vertex_forms["device1.0.vs.v"] = form

    result = plan.apply()
    assert result.status == "succeeded" and result.materialized
    assert result.phase("inventory").status == "no_change" and inventory.writes == []
    assert inventory.status_reads == (["device5"] if require_reachable else [])
    assert server.vertex_forms["device1.0.vs.v"]["fields"]["label"] == "device5"


@pytest.mark.parametrize("dry_run", [False, True])
@pytest.mark.parametrize("sync", ["add_only", "reconcile"])
@pytest.mark.parametrize("pending", ["add", "update", "remove"])
def test_resolved_plan_rejects_new_pending_sync(
    engine: ProvisioningEngine,
    inventory: FakeInventory,
    server: FakeInspectServer,
    dry_run: bool,
    sync: Literal["add_only", "reconcile"],
    pending: str,
) -> None:
    _existing(inventory, server)
    plan = engine.plan(_device(), _blueprint(), options=ApplyOptions(sync=sync))
    assert plan.fully_resolved
    server.sync["device1"] = {"add": {}, "update": {}, "remove": {}, pending: {"vertices": 1}}

    with pytest.raises(ProvisioningApplyError, match="synchronization.*new plan") as caught:
        plan.apply(dry_run=dry_run)
    assert isinstance(caught.value.__cause__, ProvisioningConflictError)
    assert caught.value.result.status == "failed"
    assert inventory.writes == [] and server.writes == []


@pytest.mark.parametrize("dry_run", [False, True])
def test_resolved_plan_propagates_sync_lookup_failure(
    engine: ProvisioningEngine, inventory: FakeInventory, server: FakeInspectServer, dry_run: bool
) -> None:
    _existing(inventory, server)
    plan = engine.plan(_device(), _blueprint())
    server.fail_sync_info = ConnectionError("sync lookup failed")

    with pytest.raises(ProvisioningApplyError, match="synchronization status") as caught:
        plan.apply(dry_run=dry_run)
    assert type(caught.value.__cause__) is ProvisioningError
    assert inventory.writes == [] and server.writes == []


def test_sync_conflict_retains_completed_inventory_phase(
    engine: ProvisioningEngine, inventory: FakeInventory, server: FakeInspectServer
) -> None:
    _existing(inventory, server)
    inventory.devices["device1"].configuration.label = "old-label"
    plan = engine.plan(_device(), _blueprint())
    assert plan.fully_resolved
    server.sync["device1"] = {"add": {"vertices": 1}, "update": {}, "remove": {}}

    with pytest.raises(ProvisioningApplyError) as caught:
        plan.apply()
    result = caught.value.result
    assert isinstance(caught.value.__cause__, ProvisioningConflictError)
    assert result.status == "partial" and result.inventory_id == "device1"
    assert result.phase("inventory").status == "completed"
    assert result.phase("inventory").operations
    assert inventory.writes == [("update", "device1")] and server.writes == []


@pytest.mark.parametrize(
    ("target_kind", "sync"),
    [("device", "none"), ("module", "none"), ("module", "add_only"), ("module", "reconcile")],
)
def test_resolved_plan_preserves_explicit_no_sync_policies(
    engine: ProvisioningEngine,
    inventory: FakeInventory,
    server: FakeInspectServer,
    target_kind: str,
    sync: Literal["none", "add_only", "reconcile"],
) -> None:
    _existing(inventory, server)
    target = ModuleTarget(device_id="device1", module_id="device1.dev.0") if target_kind == "module" else None
    plan = engine.plan(_device(topology=target), _blueprint(device=None), options=ApplyOptions(sync=sync))
    server.sync["device1"] = {"add": {}, "update": {"vertices": 1}, "remove": {}}

    result = plan.apply()
    assert result.status == "succeeded"
    assert not any(name in {"add_devices", "sync_devices"} for name, _ in server.writes)


@pytest.mark.parametrize("source", ["engine_before_plan", "engine_after_plan", "call"])
@pytest.mark.parametrize("mutation", ["parts", "mapping"])
def test_deferred_plan_captures_nested_naming(
    engine: ProvisioningEngine, server: FakeInspectServer, source: str, mutation: str
) -> None:
    media = Field("endpoint.media", mapping={"video": "video", "audio": "audio"})
    nested = Join(parts=[media, Field("endpoint.index", format="02d")], separator="-")
    naming = NamingScheme(endpoint_label=Join(parts=[Field("device.label"), nested], separator="-"))
    device = ProvisioningDevice(key="device-a", label="device-a", management_address="192.0.2.10")
    server.discoverable["device100"] = matrox_layout("device100")
    if source != "call":
        engine.configure(naming=naming)

    def mutate() -> None:
        if mutation == "parts":
            nested.parts.insert(0, "later")
        else:
            media.mapping["video"] = "later"

    if source == "engine_before_plan":
        mutate()
    plan = engine.plan(device, _blueprint(), naming=naming if source == "call" else None)
    assert not plan.fully_resolved
    if source == "call":
        mutate()
    elif source == "engine_after_plan":
        # Engine defaults are caller-accessible too; captured plans must be independent of them.
        engine_expression = engine.naming.endpoint_label
        if mutation == "parts":
            engine_expression.parts[1].parts.insert(0, "later")
        else:
            engine_expression.parts[1].parts[0].mapping["video"] = "later"

    result = plan.apply()
    assert result.status == "succeeded"
    assert server.vertex_forms["device100.0.vs.v"]["fields"]["label"] == "device-a-video-01"
    assert server.vertex_forms["device100.0.as.v"]["fields"]["label"] == "device-a-audio-01"


def test_captured_naming_keeps_trusted_python_renderer(
    engine: ProvisioningEngine, inventory: FakeInventory, server: FakeInspectServer
) -> None:
    class Renderer:
        def __deepcopy__(self, memo: dict[int, Any]) -> Renderer:
            raise TypeError("Trusted callback must not be copied.")

        def render(self, context: NameContext) -> str:
            return "device-a-custom"

    _existing(inventory, server)
    renderer = Renderer()
    engine.configure(naming=NamingScheme(device_label=renderer))
    assert engine.naming.device_label is renderer
    result = engine.plan(_device(), _blueprint()).apply()
    assert result.status == "succeeded"
    assert server.device_forms["device1"]["descriptor"]["label"] == "device-a-custom"
