"""Live external links, managed edge fields, and deferred peer recovery."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from videoipath_automation_tool.provisioning import (
    Blueprint,
    DeviceTarget,
    EdgePatch,
    PeerEndpoint,
    PortSelector,
    ProvisioningConnection,
)

from ..helpers import edges_between
from .helpers import LiveProvisioning, assert_confirmed, assert_no_writes, observe_writes

if TYPE_CHECKING:
    from videoipath_automation_tool.apps.inspect.domain.port import InspectPort
    from videoipath_automation_tool.provisioning import ProvisioningDevice

pytestmark = pytest.mark.e2e


def test_directed_connections_and_managed_updates(live: LiveProvisioning) -> None:
    local = live.onboard("LINK-A")
    peer = live.onboard("LINK-B")
    output, input_port = _ports(live, local)
    peer_output, peer_input = _ports(live, peer)
    document = live.blueprint.model_dump(exclude_unset=True, by_alias=True)
    document["defaults"]["topology"]["port_mapping"] = {"send": [{"factory_label": output.factory_label}]}
    blueprint = Blueprint.from_dict(document)
    local = local.model_copy(
        update={
            "connections": [
                ProvisioningConnection(
                    local="send",
                    peer=PeerEndpoint(
                        target=DeviceTarget(device_id=peer.inventory_id), port=PortSelector(port_id=peer_input.id)
                    ),
                    direction="outgoing",
                    fields=EdgePatch(label=f"{local.label}-out", weight=7, capacity=1000, tags=[live.tag]),
                ),
                ProvisioningConnection(
                    local=PortSelector(port_id=input_port.id),
                    peer=PeerEndpoint(
                        target=DeviceTarget(device_id=peer.inventory_id), port=PortSelector(port_id=peer_output.id)
                    ),
                    direction="incoming",
                    fields=EdgePatch(label=f"{local.label}-in", weight=9, tags=[live.tag]),
                ),
            ]
        }
    )
    with observe_writes(live.app) as writes:
        plan = live.plan(local, blueprint=blueprint, scope="topology")
        assert plan.fully_resolved
        assert plan.port_bindings[0].port_id == output.id
        assert [c.status for c in plan.connections] == ["planned", "planned"]
        assert plan.apply(dry_run=True).status == "planned"
        assert_no_writes(writes)
    live.app.inspect.refresh()
    assert edges_between(live.app, local.inventory_id, peer.inventory_id) == []
    result = plan.apply()
    assert_confirmed(result)
    assert [c.status for c in result.connections] == ["completed", "completed"]
    edge_ids = {edge_id for c in result.connections for edge_id in c.edge_ids}
    live.app.inspect.refresh()
    edges = edges_between(live.app, local.inventory_id, peer.inventory_id)
    assert {e.id for e in edges} == edge_ids
    assert {(e.from_port.id, e.to_port.id) for e in edges} == {
        (output.id, peer_input.id),
        (peer_output.id, input_port.id),
    }
    outbound_id = result.connections[0].edge_ids[0]
    outbound = next(e for e in edges if e.id == outbound_id)
    assert (outbound.label, outbound.weight, outbound.capacity) == (f"{local.label}-out", 7, 1000)
    assert live.tag in outbound.tags

    with observe_writes(live.app) as writes:
        assert live.plan(local, blueprint=blueprint, scope="topology").apply().status == "no_change"
        assert_no_writes(writes)

    # An unmanaged field and a second, unrelated link must survive an edge update.
    with live.app.inspect.transaction() as tx:
        tx.update_edge(outbound_id, description="E2E preserve-edge-description")
        tx.commit()
    unchanged_id = result.connections[1].edge_ids[0]
    live.app.inspect.refresh()
    unchanged = next(e for e in live.app.inspect.edges if e.id == unchanged_id)
    unchanged_before = (unchanged.label, unchanged.weight, unchanged.tags)
    connection = local.connections[0].model_copy(update={"fields": EdgePatch(weight=0, active=False)})
    updated = local.model_copy(update={"connections": [connection]})
    assert_confirmed(live.plan(updated, blueprint=blueprint, scope="topology").apply())
    live.app.inspect.refresh()
    edges = {e.id: e for e in edges_between(live.app, local.inventory_id, peer.inventory_id)}
    assert set(edges) == edge_ids
    assert (edges[outbound_id].weight, edges[outbound_id].active) == (0, False)
    assert edges[outbound_id].label == f"{local.label}-out"
    assert edges[outbound_id].description == "E2E preserve-edge-description"
    assert (edges[unchanged_id].label, edges[unchanged_id].weight, edges[unchanged_id].tags) == unchanged_before


def test_missing_peer_requires_a_new_plan(live: LiveProvisioning) -> None:
    local = live.onboard("DEFERRED-A")
    peer = live.onboard("DEFERRED-B", scope="inventory")
    output, _ = _ports(live, local)
    local = local.model_copy(
        update={
            "connections": [
                ProvisioningConnection(
                    local=PortSelector(port_id=output.id),
                    peer=PeerEndpoint(
                        target=DeviceTarget(device_id=peer.inventory_id),
                        port=PortSelector(factory_label="Router In 11.1"),
                    ),
                    direction="outgoing",
                    fields=EdgePatch(label=f"{local.label}-deferred", tags=[live.tag]),
                )
            ]
        }
    )
    plan = live.plan(local, scope="topology")
    assert not plan.fully_resolved and plan.connections[0].status == "deferred"
    with observe_writes(live.app) as writes:
        preview = plan.apply(dry_run=True)
        assert preview.status == "planned" and preview.replan_required
        assert_no_writes(writes)

    # Availability after planning must not silently change the reviewed connection plan.
    assert_confirmed(live.plan(peer, scope="topology").apply())
    with observe_writes(live.app) as writes:
        pending = plan.apply()
        assert pending.status == "partial" and pending.replan_required
        assert pending.connections[0].status == "deferred"
        assert_no_writes(writes)
    live.app.inspect.refresh()
    assert edges_between(live.app, local.inventory_id, peer.inventory_id) == []
    resolved = live.plan(local, scope="topology").apply()
    assert_confirmed(resolved)
    assert not resolved.replan_required
    live.app.inspect.refresh()
    assert {e.id for e in edges_between(live.app, local.inventory_id, peer.inventory_id)} == set(
        resolved.connections[0].edge_ids
    )
    assert len(resolved.connections[0].edge_ids) == 1


def _ports(live: LiveProvisioning, device: ProvisioningDevice) -> tuple[InspectPort, InspectPort]:
    ports = live.topology(device).ports
    return (
        next(p for p in ports if p.factory_label == "Router Out 11.1"),
        next(p for p in ports if p.factory_label == "Router In 11.1"),
    )
