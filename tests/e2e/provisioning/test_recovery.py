"""Actual rediscovery, stale server state, and failed readiness with recoverable IDs."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from videoipath_automation_tool.provisioning import (
    ApplyOptions,
    DeviceTarget,
    EdgePatch,
    InventoryNotReadyError,
    InventorySettings,
    NamingScheme,
    PeerEndpoint,
    PortSelector,
    ProvisioningApplyError,
    ProvisioningCapabilityError,
    ProvisioningConflictError,
    ProvisioningConnection,
)

from .helpers import (
    LiveProvisioning,
    assert_confirmed,
    assert_no_writes,
    assert_not_in_topology,
    observe_writes,
    wait_until,
)

if TYPE_CHECKING:
    from videoipath_automation_tool.provisioning import ProvisioningDevice

pytestmark = pytest.mark.e2e


def test_add_only_sync_of_new_module(live: LiveProvisioning) -> None:
    device = live.onboard("ADD-MODULE")
    original_vertices = _vertex_ids(live, device)
    updated = live.plan(device, inputs={"modules": 2}).apply()
    assert updated.status == "partial" and updated.replan_required
    _wait_sync(live, device, "add")
    result = live.plan(device, inputs={"modules": 2}, options=ApplyOptions(sync="add_only")).apply()
    assert_confirmed(result)
    assert any(op.action == "sync" for op in result.phase("topology_sync").operations)
    vertices = _vertex_ids(live, device)
    assert len(vertices) == 8 and original_vertices < vertices
    with observe_writes(live.app) as writes:
        assert live.plan(device, inputs={"modules": 2}).apply().status == "no_change"
        assert_no_writes(writes)


def test_rediscovery_add_only_and_reconcile(live: LiveProvisioning) -> None:
    device = live.device("SYNC")
    initial = live.plan(device, options=ApplyOptions(sync="add_only")).apply()
    assert_confirmed(initial)
    assert any(op.action == "add_to_topology" for op in initial.phase("topology_sync").operations)
    device = device.model_copy(update={"inventory_id": initial.inventory_id})
    original_vertices = _vertex_ids(live, device)
    plan = live.plan(device, variants=["expanded"])
    assert not plan.fully_resolved and plan.phase("topology").status == "deferred"
    updated = plan.apply()
    assert updated.status == "partial" and updated.replan_required
    assert updated.verification == "confirmed"
    assert updated.phase("inventory").status == "completed"
    assert updated.phase("topology").status == "deferred"
    assert live.inventory(device).configuration.custom_settings.num_router_ports == 3
    assert _vertex_ids(live, device) == original_vertices
    _wait_sync(live, device, "add")
    # Expanding the mock router also changes its switching core, so a full sync is required.
    added = live.plan(device, variants=["expanded"], options=ApplyOptions(sync="reconcile")).apply()
    assert_confirmed(added)
    assert not added.replan_required
    assert len(_vertex_ids(live, device)) == 6

    shrinking = live.plan(device).apply()
    assert shrinking.status == "partial" and shrinking.replan_required
    _wait_sync(live, device, "remove")
    with observe_writes(live.app) as writes:
        with pytest.raises(ProvisioningCapabilityError, match="add_only"):
            live.plan(device)
        assert_no_writes(writes)
    assert len(_vertex_ids(live, device)) == 6
    assert_confirmed(live.plan(device, options=ApplyOptions(sync="reconcile")).apply())
    assert _vertex_ids(live, device) == original_vertices
    with observe_writes(live.app) as writes:
        assert live.plan(device).apply().status == "no_change"
        assert_no_writes(writes)


@pytest.mark.parametrize("scope", ["inventory", "topology"])
@pytest.mark.parametrize("dry_run", [False, True], ids=["apply", "dry-run"])
def test_stale_device_plan_preserves_external_change(live: LiveProvisioning, scope: str, dry_run: bool) -> None:
    device = live.onboard("STALE")
    plan = live.plan(
        device,
        scope=scope,
        naming=NamingScheme(
            inventory_description="E2E planned-description", device_description="E2E planned-description"
        ),
    )
    if scope == "inventory":
        record = live.inventory(device)
        record.configuration.description = "E2E external-description"
        live.app.inventory.update_device(record, config_only=True)
    else:
        with live.app.inspect.transaction() as tx:
            tx.update_device(device.inventory_id, description="E2E external-description")
            tx.commit()
    with observe_writes(live.app) as writes:
        with pytest.raises(ProvisioningApplyError) as caught:
            plan.apply(dry_run=dry_run)
        assert isinstance(caught.value.__cause__, ProvisioningConflictError)
        assert caught.value.result.status == "failed"
        assert caught.value.result.phase(scope).status == "failed"
        assert_no_writes(writes)
    description = (
        live.inventory(device).configuration.description if scope == "inventory" else live.topology(device).description
    )
    assert description == "E2E external-description"


def test_stale_connection_plan_preserves_external_change(live: LiveProvisioning) -> None:
    local, peer = live.onboard("STALE-LINK-A"), live.onboard("STALE-LINK-B")
    local = local.model_copy(
        update={
            "connections": [
                ProvisioningConnection(
                    local=PortSelector(factory_label="Router Out 11.1"),
                    peer=PeerEndpoint(
                        target=DeviceTarget(device_id=peer.inventory_id),
                        port=PortSelector(factory_label="Router In 11.1"),
                    ),
                    direction="outgoing",
                    fields=EdgePatch(weight=3, tags=[live.tag]),
                )
            ]
        }
    )
    result = live.plan(local, scope="topology").apply()
    assert_confirmed(result)
    edge_id = result.connections[0].edge_ids[0]
    desired = local.model_copy(
        update={"connections": [local.connections[0].model_copy(update={"fields": EdgePatch(weight=5)})]}
    )
    plan = live.plan(desired, scope="topology")
    with live.app.inspect.transaction() as tx:
        tx.update_edge(edge_id, weight=11)
        tx.commit()
    with observe_writes(live.app) as writes:
        with pytest.raises(ProvisioningApplyError) as caught:
            plan.apply()
        assert isinstance(caught.value.__cause__, ProvisioningConflictError)
        assert caught.value.result.status == "failed"
        assert_no_writes(writes)
    live.app.inspect.refresh()
    assert next(e for e in live.app.inspect.edges if e.id == edge_id).weight == 11


def test_inactive_device_timeout_then_recovery(live: LiveProvisioning) -> None:
    device = live.device("READINESS", inventory_overrides=InventorySettings(active=False))
    with pytest.raises(ProvisioningApplyError) as caught:
        live.plan(device, options=ApplyOptions(inventory_ready_timeout=2, poll_interval=0.25)).apply()
    error = caught.value
    assert isinstance(error.__cause__, InventoryNotReadyError)
    assert error.result.status == "partial"
    assert error.result.inventory_id is not None
    assert error.result.phase("inventory").status == "completed"
    assert error.result.phase("inventory_readiness").status == "failed"
    device = device.model_copy(update={"inventory_id": error.result.inventory_id})
    assert live.inventory(device).configuration.active is False
    live.app.inspect.refresh()
    assert_not_in_topology(live.app, device.inventory_id)

    device = device.model_copy(update={"inventory_overrides": InventorySettings(active=True)})
    assert_confirmed(live.plan(device, scope="inventory").apply())
    assert_confirmed(live.plan(device).apply())
    assert live.topology(device).id == error.result.inventory_id
    assert (
        live.app.inventory.find_device_id_by_label(device.label, label_search_mode="user_defined_label_only")
        == error.result.inventory_id
    )
    with observe_writes(live.app) as writes:
        assert live.plan(device).apply().status == "no_change"
        assert_no_writes(writes)


def _vertex_ids(live: LiveProvisioning, device: ProvisioningDevice) -> set[str]:
    return {v.id for m in live.topology(device).modules for v in m.vertices if v.vertex_type in ("In", "Out")}


def _wait_sync(live: LiveProvisioning, device: ProvisioningDevice, change: str) -> None:
    wait_until(
        lambda: live.app.inspect.get_sync_info([device.inventory_id]).get(device.inventory_id),
        lambda info: info is not None and bool(getattr(info, change)),
        f"mock driver {change} discovery for {device.label}",
    )
