"""Live control writes on disposable mock switch, codec, and router vertices.

The module shares one real mock-driver device; every test initializes its target's control.
Only the test-owned device is removed at teardown. Connection settings come from the local
gitignored .env, and the standard E2E gate excludes these tests from offline runs.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from pydantic import BaseModel, ConfigDict

from videoipath_automation_tool.apps.inspect.errors import InspectCommitConflictError, InspectEntityNotFoundError
from videoipath_automation_tool.apps.inspect.model.common import InspectControl
from videoipath_automation_tool.provisioning import (
    ApplyOptions,
    Blueprint,
    InventorySettings,
    ProcessorResult,
    VertexEdit,
    VertexPatch,
    VertexProcessor,
)

from ..helpers import remove_devices
from .helpers import LiveProvisioning, assert_confirmed, assert_no_writes, observe_writes

if TYPE_CHECKING:
    from videoipath_automation_tool.apps.inspect.domain.vertex import InspectVertex
    from videoipath_automation_tool.apps.videoipath_app import VideoIPathApp
    from videoipath_automation_tool.provisioning import ProcessingContext, ProvisioningDevice

pytestmark = pytest.mark.e2e


@pytest.fixture(scope="module")
def control_rig(
    app: VideoIPathApp,
    e2e_addresses: Iterator[str],
    e2e_map_origins: Iterator[tuple[int, int]],
    provisioning_tag: str,
) -> Iterator[tuple[LiveProvisioning, ProvisioningDevice]]:
    live = LiveProvisioning(app, e2e_addresses, next(e2e_map_origins), provisioning_tag)
    device = live.device(
        "CONTROL",
        inventory_overrides=InventorySettings(custom_settings={"num_switch_modules": 1, "num_codec_modules": 1}),
    )
    try:
        result = live.plan(device, inputs={"ports": 1}, options=ApplyOptions(inventory_ready_timeout=60)).apply()
        assert_confirmed(result)
        assert result.inventory_id is not None
        device = device.model_copy(update={"inventory_id": result.inventory_id})
        yield live, device
    finally:
        device_id = device.inventory_id or app.inventory.find_device_id_by_label(
            device.label, label_search_mode="user_defined_label_only"
        )
        if device_id is not None:
            remove_devices(app, {device_id})
            assert (
                app.inventory.find_device_id_by_label(device.label, label_search_mode="user_defined_label_only") is None
            )
            with pytest.raises(InspectEntityNotFoundError):
                app.inspect._inspect_api.lookup_inspect_device(device_id)


@pytest.mark.parametrize("kind", ["ip", "codec", "router"])
@pytest.mark.parametrize("surface", ["direct", "domain", "transaction"])
def test_control_modes_round_trip(
    control_rig: tuple[LiveProvisioning, ProvisioningDevice], kind: str, surface: str
) -> None:
    live, device = control_rig
    vertex_id = _target(live, device, kind).id
    assert live.app.inspect.update_vertex(vertex_id, control="off").ok
    _assert_control(live, device, vertex_id, "off")
    api = live.app.inspect._inspect_api

    for mode in ("full", "semi", "off"):
        with patch.object(api, "update_topology", wraps=api.update_topology) as write:
            if surface == "domain":
                vertex = _vertex(live, device, vertex_id)
                vertex.control = mode
                assert vertex.control == mode
                assert live.app.inspect.update(vertex).ok
            elif surface == "transaction":
                with live.app.inspect.transaction() as tx:
                    tx.update_vertex(vertex_id, control=mode)
                    assert tx.commit().ok
            else:
                assert live.app.inspect.update_vertex(vertex_id, control=mode).ok
        assert write.call_count == 1
        payload = write.call_args.args[0].model_dump(mode="json")["replaceVertices"][vertex_id]
        assert "control" not in payload
        assert payload["controlProps"] == (
            None if mode == "off" else {"configPriority": "off", "onlyInitial": mode == "semi"}
        )
        _assert_control(live, device, vertex_id, mode)


@pytest.mark.parametrize("kind", ["ip", "codec", "router"])
def test_control_preserves_priority_and_raw_properties_take_precedence(
    control_rig: tuple[LiveProvisioning, ProvisioningDevice], kind: str
) -> None:
    live, device = control_rig
    vertex_id = _target(live, device, kind).id
    assert live.app.inspect.update_vertex(vertex_id, control_props={"configPriority": "high", "onlyInitial": True}).ok
    vertex = _vertex(live, device, vertex_id)
    vertex.control = "full"
    assert vertex.control_props.configPriority == "high"
    assert live.app.inspect.update(vertex).ok
    _assert_control(live, device, vertex_id, "full", priority="high")

    with pytest.raises(ValueError, match="not both"):
        live.app.inspect.update_vertex(
            vertex_id, control="full", control_props={"configPriority": "high", "onlyInitial": True}
        )
    assert live.app.inspect.update_vertex(vertex_id, control_props={"configPriority": "high", "onlyInitial": True}).ok
    _assert_control(live, device, vertex_id, "semi", priority="high")
    assert live.app.inspect.update_vertex(vertex_id, description="E2E-control", control_props=None).ok
    _assert_control(live, device, vertex_id, "semi", priority="high")
    vertex = _vertex(live, device, vertex_id)
    vertex.control_props = None
    assert live.app.inspect.update(vertex).ok
    _assert_control(live, device, vertex_id, "off")


def test_control_conflict_and_rebase_preserve_new_priority(
    control_rig: tuple[LiveProvisioning, ProvisioningDevice],
) -> None:
    live, device = control_rig
    vertex_id = _target(live, device, "ip").id
    assert live.app.inspect.update_vertex(vertex_id, control_props={"configPriority": "low", "onlyInitial": True}).ok
    with live.app.inspect.transaction() as tx:
        tx.update_vertex(vertex_id, control="full")
        assert live.app.inspect.update_vertex(
            vertex_id, control_props={"configPriority": "high", "onlyInitial": True}
        ).ok
        with observe_writes(live.app) as writes:
            with pytest.raises(InspectCommitConflictError):
                tx.commit()
            assert_no_writes(writes)
        assert tx.rebase().commit().ok
    _assert_control(live, device, vertex_id, "full", priority="high")


@pytest.mark.parametrize("kind", ["ip", "codec", "router"])
def test_processor_control_plans_verifies_and_converges(
    control_rig: tuple[LiveProvisioning, ProvisioningDevice], kind: str
) -> None:
    live, device = control_rig
    vertex_id = _target(live, device, kind).id
    processor_id = f"example-org.e2e-control-{kind}"
    live.engine.register_processor(processor_id, _ControlProcessor)
    assert live.app.inspect.update_vertex(vertex_id, control="off").ok
    options = ApplyOptions(sync="none")

    for mode in ("full", "semi", "off"):
        blueprint = _blueprint(processor_id, vertex_id, mode)
        with observe_writes(live.app) as writes:
            plan = live.engine.plan(device, blueprint, scope="topology", options=options)
            changes = [
                change
                for operation in plan.phase("topology").operations
                if operation.entity_id == vertex_id
                for change in operation.changes
            ]
            assert any(change.field == "control" and change.after == mode for change in changes)
            assert plan.apply(dry_run=True).status == "planned"
            assert_no_writes(writes)
        assert_confirmed(plan.apply())
        _assert_control(live, device, vertex_id, mode)
        with observe_writes(live.app) as writes:
            again = live.engine.plan(device, blueprint, scope="topology", options=options)
            assert not again.has_changes
            assert again.apply().status == "no_change"
            assert_no_writes(writes)

    override = _blueprint(processor_id, vertex_id, "off", override="full")
    assert_confirmed(live.engine.apply(device, override, scope="topology", options=options))
    _assert_control(live, device, vertex_id, "full")


# --- Internal ---


class _ControlParams(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    vertex_id: str
    control: InspectControl


class _ControlProcessor(VertexProcessor[_ControlParams]):
    params_model = _ControlParams

    def process(self, context: ProcessingContext, params: _ControlParams) -> ProcessorResult:
        vertex = context.vertex(params.vertex_id)
        assert vertex is not None, "Control target must belong to the test device"
        return ProcessorResult(vertices=[VertexEdit(vertex_id=vertex.id, fields=VertexPatch(control=params.control))])


def _blueprint(processor_id: str, vertex_id: str, mode: str, *, override: str | None = None) -> Blueprint:
    document = {
        "schema_version": 1,
        "defaults": {
            "topology": {
                "vertex_processor": {
                    "processor_type": processor_id,
                    "params": {"vertex_id": vertex_id, "control": mode},
                }
            }
        },
    }
    if override is not None:
        document["defaults"]["topology"]["vertices"] = [{"vertex_id": vertex_id, "fields": {"control": override}}]
    return Blueprint.from_dict(document)


def _target(live: LiveProvisioning, device: ProvisioningDevice, kind: str) -> InspectVertex:
    vertices = [v for m in live.topology(device).modules for v in m.vertices if v.vertex_kind == kind]
    if kind == "ip":
        vertices = [v for v in vertices if v.vertex_type == "Internal"]
    assert vertices, f"Mock driver must expose a {'switching core' if kind == 'ip' else kind} vertex"
    return min(vertices, key=lambda vertex: vertex.id)


def _vertex(live: LiveProvisioning, device: ProvisioningDevice, vertex_id: str) -> InspectVertex:
    return next(v for m in live.topology(device).modules for v in m.vertices if v.id == vertex_id)


def _assert_control(
    live: LiveProvisioning, device: ProvisioningDevice, vertex_id: str, mode: str, *, priority: str = "off"
) -> None:
    # Read the server's edit form directly as well as a refreshed public domain view.
    form = live.app.inspect._inspect_api.lookup_vertices([vertex_id]).data[vertex_id].fields
    if mode == "off":
        assert form.controlProps is None
    else:
        assert form.controlProps is not None
        assert form.controlProps.onlyInitial is (mode == "semi")
        assert form.controlProps.configPriority == priority
    assert _vertex(live, device, vertex_id).control == mode
