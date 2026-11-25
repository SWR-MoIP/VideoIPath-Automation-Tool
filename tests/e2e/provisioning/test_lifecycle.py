"""Onboarding, managed updates, naming, and module-scoped configuration."""

from __future__ import annotations

import pytest

from videoipath_automation_tool.provisioning import (
    ApplyOptions,
    Blueprint,
    InventorySettings,
    ModuleTarget,
    NamingScheme,
    ProvisioningValidationError,
)

from .helpers import (
    BLUEPRINT_PATH,
    LiveProvisioning,
    assert_confirmed,
    assert_no_writes,
    assert_not_in_topology,
    observe_writes,
)

pytestmark = pytest.mark.e2e


def test_preview_apply_and_idempotent_reapply(live: LiveProvisioning) -> None:
    device = live.device("LIFECYCLE", description="E2E provisioned router")
    naming = NamingScheme(inventory_description="{device.description}", device_description="{device.description}")
    with observe_writes(live.app) as writes:
        plan = live.plan(device, blueprint=BLUEPRINT_PATH, naming=naming)
        assert not plan.fully_resolved
        assert plan.phase("inventory").operations[0].action == "create"
        assert plan.phase("topology").status == "deferred"
        preview = plan.apply(dry_run=True)
        assert preview.status == "planned"
        assert preview.inventory_id is None
        assert_no_writes(writes)
    assert live.app.inventory.find_device_id_by_label(device.label, label_search_mode="user_defined_label_only") is None
    live.app.inspect.refresh()
    assert not [d for d in live.app.inspect.devices if d.label == device.label]

    result = plan.apply()
    assert_confirmed(result)
    assert result.inventory_id is not None
    assert result.topology_device_id == result.inventory_id
    assert result.phase("inventory_readiness").status == "completed"
    device = device.model_copy(update={"inventory_id": result.inventory_id})
    inventory = live.inventory(device).configuration
    assert inventory.label == device.label
    assert inventory.address == device.management_address
    assert inventory.description == device.description
    assert inventory.custom_settings.num_router_ports == 2
    topology = live.topology(device)
    assert topology.label == device.label
    assert topology.description == device.description
    assert live.tag in topology.tags
    assert topology.coordinates == {"x": device.attributes["x"], "y": device.attributes["y"]}
    endpoints = [v for m in topology.modules for v in m.vertices if v.use_as_endpoint]
    assert len(endpoints) == 4
    assert all(v.active and v.label.startswith(f"{device.label}-endpoint-") for v in endpoints)
    assert len({v.label for v in endpoints}) == 4

    with observe_writes(live.app) as writes:
        again = live.plan(device, naming=naming)
        assert again.fully_resolved and not again.has_changes
        assert again.apply().status == "no_change"
        assert_no_writes(writes)
    assert live.inventory(device).configuration.device_id == result.inventory_id


def test_inventory_and_topology_scopes(live: LiveProvisioning) -> None:
    device = live.device("SCOPES")
    result = live.plan(device, scope="inventory").apply()
    assert_confirmed(result)
    assert result.phase("topology").status == "skipped"
    device = device.model_copy(update={"inventory_id": result.inventory_id})
    original = live.inventory(device).configuration.model_dump()
    live.app.inspect.refresh()
    assert_not_in_topology(live.app, device.inventory_id)

    assert_confirmed(live.plan(device, scope="topology").apply())
    assert live.topology(device).label == device.label
    assert live.inventory(device).configuration.model_dump() == original


def test_managed_updates_preserve_unmanaged_fields(live: LiveProvisioning, catalog_tag: str) -> None:
    device = live.onboard("MANAGED")
    inventory = live.inventory(device)
    inventory.configuration.custom_settings.bulk = False
    live.app.inventory.update_device(inventory, config_only=True)
    with live.app.inspect.transaction() as tx:
        tx.update_device(device.inventory_id, description="E2E preserve-description", tags=[live.tag, catalog_tag])
        tx.commit()

    # A variant configures both scopes; the per-instance Inventory setting wins over the variant.
    device = device.model_copy(
        update={"inventory_overrides": InventorySettings(custom_settings={"matrix_type": "1:1"})}
    )
    plan = live.plan(device, variants=["matrix"], scope="inventory")
    changes = {change.field: change for op in plan.phase("inventory").operations for change in op.changes}
    assert changes["custom_settings.matrix_type"].source == "instance"
    assert_confirmed(plan.apply())
    assert live.inventory(device).configuration.custom_settings.matrix_type == "1:1"
    assert live.inventory(device).configuration.custom_settings.bulk is False

    # Avoid synchronization here: this test concerns managed-field preservation, not rediscovery.
    result = live.plan(device, variants=["matrix"], scope="topology", options=ApplyOptions(sync="none")).apply()
    assert_confirmed(result)
    topology = live.topology(device)
    assert topology.icon_size == "large"
    assert topology.description == "E2E preserve-description"
    assert set(topology.tags) == {live.tag, catalog_tag}
    assert live.inventory(device).configuration.custom_settings.bulk is False


def test_endpoint_rename_and_collision_rejection(live: LiveProvisioning) -> None:
    device = live.onboard("NAMING")
    original = {v.id: v.label for m in live.topology(device).modules for v in m.vertices if v.use_as_endpoint}
    with observe_writes(live.app) as writes:
        plan = live.plan(device, scope="topology", inputs={"endpoint_prefix": "renamed"})
        assert plan.apply(dry_run=True).status == "planned"
        assert_no_writes(writes)
    assert {v.id: v.label for m in live.topology(device).modules for v in m.vertices if v.use_as_endpoint} == original
    assert_confirmed(plan.apply())
    renamed = {v.id: v.label for m in live.topology(device).modules for v in m.vertices if v.use_as_endpoint}
    assert renamed.keys() == original.keys()
    assert all(label.startswith(f"{device.label}-renamed-") for label in renamed.values())
    with observe_writes(live.app) as writes:
        with pytest.raises(ProvisioningValidationError, match="[Cc]ollision|[Dd]uplicate"):
            live.plan(device, scope="topology", naming=NamingScheme(endpoint_label="{device.label}"))
        assert_no_writes(writes)
    assert {v.id: v.label for m in live.topology(device).modules for v in m.vertices if v.use_as_endpoint} == renamed


def test_module_target_tags_and_sibling_isolation(live: LiveProvisioning, catalog_tag: str) -> None:
    device = live.onboard("MODULES", inputs={"modules": 2})
    topology = live.topology(device)
    module, sibling = sorted(topology.modules, key=lambda item: item.id)
    parent_before = (topology.label, topology.description, topology.tags, topology.coordinates)
    sibling_before = {v.id: (v.label, v.active, v.use_as_endpoint) for v in sibling.vertices}
    inventory_before = live.inventory(device).configuration.model_dump()
    target = device.model_copy(update={"topology": ModuleTarget(device_id=topology.id, module_id=module.id)})
    blueprint = Blueprint.from_dict(
        {
            "schema_version": 1,
            "defaults": {
                "topology": {
                    "module": {"tags": {"add": [catalog_tag]}},
                    "vertex_processor": {"processor_type": "example-org.e2e-router"},
                    "naming": {"endpoint_label": "{device.label}-module-{endpoint.direction}-{endpoint.index:02d}"},
                }
            },
        }
    )
    with observe_writes(live.app) as writes:
        plan = live.engine.plan(target, blueprint, scope="topology")
        assert plan.apply(dry_run=True).phase("module_tags").status == "planned"
        assert_no_writes(writes)
    assert_confirmed(plan.apply())
    topology = live.topology(device)
    assert catalog_tag in topology.get_module(module.id).tags
    assert all("-module-" in v.label for v in topology.get_module(module.id).vertices if v.use_as_endpoint)
    assert {
        v.id: (v.label, v.active, v.use_as_endpoint) for v in topology.get_module(sibling.id).vertices
    } == sibling_before
    assert (topology.label, topology.description, topology.tags, topology.coordinates) == parent_before
    assert live.inventory(device).configuration.model_dump() == inventory_before
    with observe_writes(live.app) as writes:
        assert live.engine.apply(target, blueprint, scope="topology").status == "no_change"
        assert_no_writes(writes)
    remove = Blueprint.from_dict(
        {"schema_version": 1, "defaults": {"topology": {"module": {"tags": {"remove": [catalog_tag]}}}}}
    )
    assert_confirmed(live.engine.apply(target, remove, scope="topology"))
    assert catalog_tag not in live.topology(device).get_module(module.id).tags
