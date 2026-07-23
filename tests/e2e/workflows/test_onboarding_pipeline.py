"""Cross-app onboarding pipeline: inventory → Inspect topology → edges → security domains.

Mirrors ``docs/examples/06_workflows/01_full_onboarding_pipeline.py`` on a small 2-leaf / 1-spine
network, as an ordered ``@pytest.mark.incremental`` suite. Reachability polling is omitted because
mock devices are not reachable. The built topology is left in VideoIPath; the next e2e session's
sweep removes ``E2E-`` artifacts.

Run with::

    poetry run test-e2e
"""

from __future__ import annotations

from typing import Iterator

import pytest
from pydantic import BaseModel

from videoipath_automation_tool.apps.videoipath_app import VideoIPathApp

from ..helpers import E2E_TAG, create_mock_device, discover_port_cursors, unique_name
from ..networks import build_network

pytestmark = pytest.mark.e2e

PIPELINE = build_network(
    "onboard",
    devices=[("leaf-1", 0, 0), ("leaf-2", 600, 0), ("spine-1", 300, 400)],
    links=[("leaf-1", "spine-1"), ("leaf-2", "spine-1")],
)
# Below the network-builder map regions (spine-leaf 3-tier reaches y≈9200 at offset (2500, 8000)).
OFFSET = (0, 10000)

SITE_TAG = "site-a"


class PipelineState(BaseModel):
    device_ids: dict[str, str] = {}
    domain_name: str | None = None


@pytest.fixture(scope="class")
def state() -> PipelineState:
    return PipelineState()


@pytest.mark.incremental
class TestOnboardingPipeline:
    def test_connect(self, app: VideoIPathApp) -> None:
        app.check_connection()
        assert app.get_server_version()

    def test_create_inventory_devices(
        self, app: VideoIPathApp, state: PipelineState, e2e_addresses: Iterator[str]
    ) -> None:
        for spec in PIPELINE.devices:
            label = f"E2E-{PIPELINE.name}-{spec.name}"
            state.device_ids[spec.name] = create_mock_device(
                app, label=label, address=next(e2e_addresses), ports=spec.ports
            )
        assert len(state.device_ids) == len(PIPELINE.devices)

    def test_add_to_topology(self, app: VideoIPathApp, state: PipelineState) -> None:
        dx, dy = OFFSET
        app.inspect.add_devices_to_topology(
            [(state.device_ids[spec.name], spec.x + dx, spec.y + dy) for spec in PIPELINE.devices]
        )
        topology_ids = {device.id for device in app.inspect.devices}
        assert set(state.device_ids.values()) <= topology_ids

    def test_configure_devices(self, app: VideoIPathApp, state: PipelineState) -> None:
        with app.inspect.transaction() as tx:
            for spec in PIPELINE.devices:
                device = app.inspect.get_device(state.device_ids[spec.name])
                assert device is not None
                device.label = f"E2E-{PIPELINE.name}-{spec.name}"
                device.description = f"Onboarding pipeline {spec.name}"
                device.tags = [E2E_TAG, SITE_TAG]
                tx.update(device)
            tx.commit()
        for spec in PIPELINE.devices:
            device = app.inspect.get_device(state.device_ids[spec.name])
            assert device is not None
            assert device.label == f"E2E-{PIPELINE.name}-{spec.name}"
            assert SITE_TAG in device.tags

    def test_connect_links(self, app: VideoIPathApp, state: PipelineState) -> None:
        cursors = discover_port_cursors(app, state.device_ids.values())
        with app.inspect.transaction() as tx:
            for link in PIPELINE.links:
                id_a = state.device_ids[PIPELINE.devices[link.a].name]
                id_b = state.device_ids[PIPELINE.devices[link.b].name]
                a_out, a_in = cursors[id_a].next_port()
                b_out, b_in = cursors[id_b].next_port()
                tx.connect(a_out, b_in, bidirectional=False)
                tx.connect(b_out, a_in, bidirectional=False)
            tx.commit()

    def test_assign_security_domains(self, app: VideoIPathApp, state: PipelineState) -> None:
        state.domain_name = unique_name("domain")
        app.security.domains.create_domain(name=state.domain_name, description="E2E onboarding pipeline domain")
        for device_id in state.device_ids.values():
            memberships = app.security.resources.get_device_memberships(device_id=device_id)
            memberships.domains = app.security.resources.convert_domain_names_to_ids([state.domain_name])
            app.security.resources.update_memberships(memberships=memberships)

    def test_verify_pipeline(self, app: VideoIPathApp, state: PipelineState) -> None:
        app.inspect.refresh()
        adjacency = PIPELINE.neighbours()
        assert state.domain_name is not None
        for spec in PIPELINE.devices:
            device_id = state.device_ids[spec.name]
            label = f"E2E-{PIPELINE.name}-{spec.name}"
            device = app.inspect.get_device(device_id)
            assert device is not None
            assert device.label == label
            expected = {f"E2E-{PIPELINE.name}-{neighbour}" for neighbour in adjacency[spec.name]}
            assert {linked.label for linked in device.linked_devices} == expected
            memberships = app.security.resources.get_device_memberships(device_id=device_id)
            names = set(app.security.resources.convert_domain_ids_to_names(memberships.domains))
            assert state.domain_name in names
