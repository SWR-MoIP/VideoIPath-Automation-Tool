"""Independent rollout budgets, status gates, and delayed topology visibility, entirely offline."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from pydantic import ValidationError

from tests.provisioning.conftest import FakeInspectServer, FakeInventory, build_layout, matrox_layout
from tests.provisioning.test_engine import _blueprint, _device, _existing
from videoipath_automation_tool.apps.inventory.model.device_status import DeviceStatus
from videoipath_automation_tool.apps.inventory.model.inventory_device import InventoryDevice
from videoipath_automation_tool.provisioning import (
    ApplyOptions,
    Blueprint,
    DeviceTarget,
    InventoryNotReadyError,
    ModuleTarget,
    ProvisioningApplyError,
    ProvisioningDevice,
    ProvisioningEngine,
    TopologyNotReadyError,
)


def _new_device() -> ProvisioningDevice:
    return ProvisioningDevice(key="device-a", label="device-a", management_address="192.0.2.10")


def _on_sleep(engine: ProvisioningEngine, callback: Callable[[float], None]) -> None:
    advance = engine._sleep

    def sleep(seconds: float) -> None:
        advance(seconds)
        callback(engine._clock())

    engine._sleep = sleep


def test_inventory_gate_precedes_every_topology_write(
    engine: ProvisioningEngine, inventory: FakeInventory, server: FakeInspectServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    inventory.status_sequence["device100"] = [None, False, True]
    server.discoverable["device100"] = matrox_layout("device100", "tx")
    read = inventory.refresh_device_status

    def status(device: InventoryDevice) -> InventoryDevice:
        assert server.writes == []
        return read(device)

    monkeypatch.setattr(inventory, "refresh_device_status", status)
    plan = engine.plan(_new_device(), _blueprint())
    assert inventory.status_reads == [] and engine._clock() == 0
    assert plan.phase("inventory_readiness").status == "deferred"
    result = plan.apply()
    assert result.status == "succeeded" and engine._clock() == 2
    assert inventory.status_reads == ["device100"] * 3
    assert result.phase("inventory_readiness").status == "completed"
    assert result.phase("discovery").status == "completed"
    assert [phase.name for phase in result.phases] == [
        "inventory",
        "inventory_readiness",
        "topology_sync",
        "discovery",
        "topology",
        "module_tags",
        "verification",
    ]


@pytest.mark.parametrize("state", [None, False])
def test_inventory_timeout_keeps_id_and_does_not_start_topology(
    engine: ProvisioningEngine, inventory: FakeInventory, server: FakeInspectServer, state: bool | None
) -> None:
    inventory.status_sequence["device100"] = [state]
    with pytest.raises(ProvisioningApplyError) as info:
        engine.apply(_new_device(), _blueprint(), options=ApplyOptions(inventory_ready_timeout=2.5))
    result = info.value.result
    assert isinstance(info.value.__cause__, InventoryNotReadyError)
    assert result.status == "partial" and result.inventory_id == "device100"
    assert result.phase("inventory").status == "completed"
    assert result.phase("inventory_readiness").status == "failed"
    assert "device100" in result.phase("inventory_readiness").message
    assert "2.5s" in result.phase("inventory_readiness").message
    assert ("status unavailable" if state is None else "reachable=False") in result.phase("inventory_readiness").message
    assert all(result.phase(name).status == "not_run" for name in ("topology_sync", "discovery", "topology"))
    assert server.writes == [] and len(inventory.status_reads) == 3 and engine._clock() == 2.5


def test_topology_gets_a_fresh_full_budget_after_slow_inventory(
    engine: ProvisioningEngine, inventory: FakeInventory, server: FakeInspectServer
) -> None:
    inventory.status_sequence["device100"] = [False] * 9 + [True]

    def discover(now: float) -> None:
        if now == 68:
            server.discoverable["device100"] = matrox_layout("device100", "tx")

    _on_sleep(engine, discover)
    result = engine.apply(_new_device(), _blueprint())
    assert result.status == "succeeded" and engine._clock() == 68
    assert len(inventory.status_reads) == 10


def test_reachability_bypass_is_explicit_and_reported(
    engine: ProvisioningEngine, inventory: FakeInventory, server: FakeInspectServer
) -> None:
    inventory.status_sequence["device100"] = [False]
    server.discoverable["device100"] = matrox_layout("device100", "tx")
    plan = engine.plan(_new_device(), _blueprint(), options=ApplyOptions(require_reachable=False))
    assert plan.phase("inventory_readiness").status == "skipped"
    result = plan.apply()
    assert result.status == "succeeded" and inventory.status_reads == []
    assert result.phase("inventory_readiness").status == "skipped"
    assert "require_reachable=False" in result.phase("inventory_readiness").message


def test_accepted_add_and_sync_are_not_repeated_while_visibility_lags(
    engine: ProvisioningEngine, server: FakeInspectServer
) -> None:
    server.discoverable["device100"] = matrox_layout("device100", "tx")
    server.add_visibility_polls = 4
    server.sync_completion_polls = 4
    result = engine.apply(_new_device(), _blueprint())
    assert result.status == "succeeded" and engine._clock() > 0
    assert [name for name, _ in server.writes] == ["add_devices", "sync_devices", "update_topology"]


@pytest.mark.parametrize("stage", ["addition", "sync", "ports"])
def test_topology_timeout_reports_the_stalled_stage(
    engine: ProvisioningEngine, server: FakeInspectServer, stage: str
) -> None:
    server.discoverable["device100"] = (
        build_layout("device100", {"device100.dev.0": []}) if stage == "ports" else matrox_layout("device100", "tx")
    )
    server.add_visibility_polls = 100 if stage == "addition" else 0
    server.sync_completion_polls = 100 if stage == "sync" else 0
    with pytest.raises(ProvisioningApplyError) as info:
        engine.apply(_new_device(), _blueprint(), options=ApplyOptions(topology_ready_timeout=2.5))
    result = info.value.result
    assert isinstance(info.value.__cause__, TopologyNotReadyError)
    failed_phase = "discovery" if stage == "ports" else "topology_sync"
    assert result.phase(failed_phase).status == "failed"
    assert "device100" in result.phase(failed_phase).message and "2.5s" in result.phase(failed_phase).message
    assert result.phase("inventory_readiness").status == "completed"
    assert result.phase("topology").status == "not_run"
    assert result.inventory_id == "device100" and result.status == "partial"
    assert [name for name, _ in server.writes].count("add_devices") == 1
    assert [name for name, _ in server.writes].count("sync_devices") == (0 if stage == "addition" else 1)
    assert engine._clock() == 2.5


def test_newly_discovered_ports_are_synchronized_before_configuration(
    engine: ProvisioningEngine, server: FakeInspectServer
) -> None:
    server.discoverable["device100"] = build_layout("device100", {"device100.dev.0": []})

    def discover(now: float) -> None:
        if now == 2:
            server.discoverable["device100"] = matrox_layout("device100", "tx")
            server.sync["device100"] = {"add": {"ports": 4}, "update": {}, "remove": {}}

    _on_sleep(engine, discover)
    result = engine.apply(_new_device(), _blueprint())
    assert result.status == "succeeded" and engine._clock() == 2
    assert [name for name, _ in server.writes] == ["add_devices", "sync_devices", "sync_devices", "update_topology"]


def test_retry_after_port_timeout_defers_existing_incomplete_topology(
    engine: ProvisioningEngine, inventory: FakeInventory, server: FakeInspectServer
) -> None:
    server.discoverable["device100"] = build_layout("device100", {"device100.dev.0": []})
    with pytest.raises(ProvisioningApplyError) as info:
        engine.apply(_new_device(), _blueprint(), options=ApplyOptions(topology_ready_timeout=2))
    retry = _new_device().model_copy(update={"inventory_id": info.value.result.inventory_id})
    _on_sleep(engine, lambda now: server.install(matrox_layout("device100", "tx")))
    plan = engine.plan(retry, _blueprint())
    assert not plan.fully_resolved and plan.phase("discovery").status == "deferred"
    result = plan.apply()
    assert result.status == "succeeded" and engine._clock() == 3
    assert inventory.writes == [("add", "device100")]
    assert [name for name, _ in server.writes].count("add_devices") == 1


@pytest.mark.parametrize("failure", ["transport", "value", "validation"])
def test_inventory_status_errors_are_not_retried(
    engine: ProvisioningEngine, inventory: FakeInventory, server: FakeInspectServer, failure: str
) -> None:
    error: Exception = ConnectionError("offline") if failure == "transport" else ValueError("invalid response")
    if failure == "validation":
        with pytest.raises(ValidationError) as invalid:
            DeviceStatus.model_validate({})
        error = invalid.value
    inventory.status_sequence["device100"] = [error]
    with pytest.raises(ProvisioningApplyError) as info:
        engine.apply(_new_device(), _blueprint())
    assert info.value.__cause__ is error
    assert info.value.result.phase("inventory_readiness").status == "failed"
    assert len(inventory.status_reads) == 1 and engine._clock() == 0 and server.writes == []


def test_slow_status_request_counts_against_inventory_deadline(
    engine: ProvisioningEngine, inventory: FakeInventory, server: FakeInspectServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    read = inventory.refresh_device_status

    def slow_status(device: InventoryDevice) -> InventoryDevice:
        engine._sleep(10)
        return read(device)

    monkeypatch.setattr(inventory, "refresh_device_status", slow_status)
    with pytest.raises(ProvisioningApplyError) as info:
        engine.apply(_new_device(), _blueprint())
    assert isinstance(info.value.__cause__, InventoryNotReadyError)
    assert inventory.status_reads == ["device100"] and server.writes == []


def test_slow_membership_read_cannot_start_a_write_after_deadline(
    engine: ProvisioningEngine, server: FakeInspectServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    read = server.get_device_detail

    def slow_detail(device_id: str) -> Any:
        engine._sleep(60)
        return read(device_id)

    monkeypatch.setattr(server, "get_device_detail", slow_detail)
    with pytest.raises(ProvisioningApplyError) as info:
        engine.apply(_new_device(), _blueprint())
    assert isinstance(info.value.__cause__, TopologyNotReadyError)
    assert info.value.result.phase("topology_sync").status == "failed"
    assert server.calls == ["detail:device100"] and server.writes == []


def test_slow_topology_data_read_does_not_start_another_read_after_deadline(
    engine: ProvisioningEngine, server: FakeInspectServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    server.discoverable["device100"] = matrox_layout("device100", "tx")
    read = server.lookup_inspect_device

    def slow_form(device_id: str) -> Any:
        # Membership now checks the edit form too; delay the discovery read after sync.
        if any(name == "sync_devices" for name, _ in server.writes):
            engine._sleep(60)
        return read(device_id)

    monkeypatch.setattr(server, "lookup_inspect_device", slow_form)
    with pytest.raises(ProvisioningApplyError) as info:
        engine.apply(_new_device(), _blueprint())
    assert isinstance(info.value.__cause__, TopologyNotReadyError)
    assert info.value.result.phase("discovery").status == "failed"
    assert not any(call.startswith("lookup_vertices") for call in server.calls)
    assert [name for name, _ in server.writes] == ["add_devices", "sync_devices"]


def test_late_sync_response_keeps_successful_operations_without_configuration_writes(
    engine: ProvisioningEngine, server: FakeInspectServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    server.discoverable["device100"] = matrox_layout("device100", "tx")
    sync = server.sync_devices

    def slow_sync(*args: Any, **kwargs: Any) -> Any:
        response = sync(*args, **kwargs)
        engine._sleep(60)
        return response

    monkeypatch.setattr(server, "sync_devices", slow_sync)
    with pytest.raises(ProvisioningApplyError) as info:
        engine.apply(_new_device(), _blueprint())
    result = info.value.result
    phase = result.phase("topology_sync")
    assert isinstance(info.value.__cause__, TopologyNotReadyError)
    assert phase.status == "failed" and "synchronization accepted" in phase.message
    assert [operation.action for operation in phase.operations] == ["add_to_topology", "sync"]
    assert result.phase("discovery").status == "not_run"
    assert result.inventory_id == "device100" and result.status == "partial"
    assert [name for name, _ in server.writes] == ["add_devices", "sync_devices"]


def test_expiry_before_first_topology_poll_is_reported_in_topology_sync(
    engine: ProvisioningEngine, server: FakeInspectServer
) -> None:
    engine._sleep(1)
    with pytest.raises(ProvisioningApplyError) as info:
        engine.apply(_new_device(), _blueprint(), options=ApplyOptions(topology_ready_timeout=1e-30))
    assert info.value.result.phase("inventory_readiness").status == "completed"
    assert info.value.result.phase("topology_sync").status == "failed"
    assert server.calls == [] and server.writes == []


@pytest.mark.parametrize("stage", ["inventory", "topology"])
def test_poll_interval_is_capped_to_the_remaining_stage_budget(
    engine: ProvisioningEngine, inventory: FakeInventory, server: FakeInspectServer, stage: str
) -> None:
    if stage == "inventory":
        inventory.status_sequence["device100"] = [False]
    options = ApplyOptions(inventory_ready_timeout=2.5, topology_ready_timeout=2.5, poll_interval=20)
    with pytest.raises(ProvisioningApplyError):
        engine.apply(_new_device(), _blueprint(), options=options)
    assert engine._clock() == 2.5 and inventory.status_reads == ["device100"]
    assert len(server.writes) == (0 if stage == "inventory" else 1)


def test_inventory_only_and_fully_resolved_topology_skip_the_gate(
    engine: ProvisioningEngine, inventory: FakeInventory, server: FakeInspectServer
) -> None:
    inventory.status_sequence["device100"] = [False]
    result = engine.apply(_new_device(), _blueprint(), scope="inventory")
    assert result.phase("inventory_readiness").status == "skipped"
    _existing(inventory, server)
    inventory.status_sequence["device1"] = [False]
    result = engine.apply(_device(), _blueprint())
    assert result.phase("inventory_readiness").status == "skipped"
    assert result.status == "succeeded" and inventory.status_reads == []


@pytest.mark.parametrize("kind", ["virtual", "module"])
def test_deferred_virtual_and_unbound_module_targets_skip_inventory_readiness(
    engine: ProvisioningEngine, inventory: FakeInventory, server: FakeInspectServer, kind: str
) -> None:
    device_id = "virtual.1" if kind == "virtual" else "device1"
    module_id = f"{device_id}.dev.0"
    server.install(build_layout(device_id, {module_id: []}))
    target = (
        DeviceTarget(device_id=device_id)
        if kind == "virtual"
        else ModuleTarget(device_id=device_id, module_id=module_id)
    )
    device = ProvisioningDevice(key="device-a", label="device-a", topology=target)
    blueprint = Blueprint.from_dict(
        {"schema_version": 1, "defaults": {"topology": {"ip_vertex_mapping": {"a": ["P1"]}}}}
    )
    _on_sleep(engine, lambda now: server.install(matrox_layout(device_id, "tx")))
    plan = engine.plan(device, blueprint)
    assert not plan.fully_resolved and plan.phase("inventory_readiness").status == "skipped"
    result = plan.apply()
    assert result.materialized and result.phase("inventory_readiness").status == "skipped"
    assert inventory.status_reads == [] and engine._clock() == 1
    assert not any(name in {"add_devices", "sync_devices"} for name, _ in server.writes)


def test_topology_only_physical_target_checks_its_inventory_record(
    engine: ProvisioningEngine, inventory: FakeInventory, server: FakeInspectServer
) -> None:
    inventory.seed("device1")
    inventory.status_sequence["device1"] = [False, True]
    server.discoverable["device1"] = matrox_layout("device1", "tx")
    device = ProvisioningDevice(key="device-a", label="device-a", topology=DeviceTarget(device_id="device1"))
    result = engine.apply(device, _blueprint(), scope="topology")
    assert result.status == "succeeded" and inventory.status_reads == ["device1", "device1"]


def test_deferred_module_checks_its_own_inventory_binding(
    engine: ProvisioningEngine, inventory: FakeInventory, server: FakeInspectServer
) -> None:
    inventory.seed("device1")
    inventory.seed("device5", label="module-a", address="192.0.2.55")
    inventory.status_sequence["device1"] = [False]
    inventory.status_sequence["device5"] = [False, True]
    server.install(build_layout("device1", {"device1.dev.0": []}))
    device = ProvisioningDevice(
        key="module-a",
        label="module-a",
        inventory_id="device5",
        topology=ModuleTarget(device_id="device1", module_id="device1.dev.0"),
    )
    blueprint = Blueprint.from_dict(
        {"schema_version": 1, "defaults": {"topology": {"ip_vertex_mapping": {"a": ["P1"]}}}}
    )
    _on_sleep(engine, lambda now: server.install(matrox_layout("device1", "tx")) if now == 2 else None)
    result = engine.apply(device, blueprint, scope="topology")
    assert result.materialized and result.phase("inventory_readiness").status == "completed"
    assert inventory.status_reads == ["device5", "device5"]
    assert inventory.writes == [] and not any(name in {"add_devices", "sync_devices"} for name, _ in server.writes)


def test_dry_run_does_not_poll_or_sleep(
    engine: ProvisioningEngine, inventory: FakeInventory, server: FakeInspectServer
) -> None:
    inventory.status_sequence["device100"] = [ConnectionError("must not read")]
    result = engine.apply(_new_device(), _blueprint(), dry_run=True)
    assert result.phase("inventory_readiness").status == "deferred"
    assert result.phase("discovery").status == "deferred"
    assert inventory.status_reads == [] and engine._clock() == 0
    assert inventory.writes == [] and server.writes == []


def test_plans_capture_readiness_options(engine: ProvisioningEngine, inventory: FakeInventory) -> None:
    inventory.status_sequence["device100"] = [False]
    engine.configure(options=ApplyOptions(inventory_ready_timeout=2, topology_ready_timeout=3))
    plan = engine.plan(_new_device(), _blueprint())
    engine.configure(options=ApplyOptions(inventory_ready_timeout=100, require_reachable=False))
    with pytest.raises(ProvisioningApplyError) as info:
        plan.apply()
    assert isinstance(info.value.__cause__, InventoryNotReadyError) and engine._clock() == 2


@pytest.mark.parametrize("field", ["inventory_ready_timeout", "topology_ready_timeout", "poll_interval"])
@pytest.mark.parametrize("value", [0, -1, float("inf"), float("-inf"), float("nan"), True])
def test_readiness_times_must_be_positive_finite_numbers(field: str, value: Any) -> None:
    with pytest.raises(ValidationError):
        ApplyOptions(**{field: value})


def test_old_timeout_option_is_rejected() -> None:
    with pytest.raises(ValidationError, match="discovery_timeout"):
        ApplyOptions(discovery_timeout=30)
