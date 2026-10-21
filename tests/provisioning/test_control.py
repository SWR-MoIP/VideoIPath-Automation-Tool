"""Control proposals, planning, serialized writes, and read-back verification (offline)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from videoipath_automation_tool.apps.inspect.model.common import InspectControl
from videoipath_automation_tool.provisioning import (
    Blueprint,
    DeviceTarget,
    ProcessingContext,
    ProcessorResult,
    ProvisioningApplyError,
    ProvisioningDevice,
    ProvisioningEngine,
    ProvisioningValidationError,
    VertexEdit,
    VertexPatch,
    VertexProcessor,
)

from .conftest import FakeInspectServer, build_layout, matrox_layout

CORE_ID = "device-a.0.core.v"


class ControlParams(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    control: InspectControl = "full"


class CoreProcessor(VertexProcessor[ControlParams]):
    params_model = ControlParams

    def process(self, context: ProcessingContext, params: ControlParams) -> ProcessorResult:
        core = context.require_vertex(factory_label="Switching Core", kind="ip", vertex_type="Internal")
        return ProcessorResult(vertices=[VertexEdit(vertex_id=core.id, fields=VertexPatch(control=params.control))])


@pytest.mark.parametrize("mode", ["full", "semi", "off"])
def test_processor_control_plan_apply_and_reapply(app: SimpleNamespace, server: FakeInspectServer, mode: str) -> None:
    _install_core(server)
    before = "full" if mode == "semi" else "semi"
    props = server.vertex_forms[CORE_ID]["fields"]["controlProps"]
    props["onlyInitial"] = before == "semi"
    engine = ProvisioningEngine(app, processors={"example-org.core": CoreProcessor})
    blueprint = _blueprint(mode)
    plan = engine.plan(_device(), blueprint, scope="topology")
    assert server.writes == []
    changes = next(op.changes for op in plan.phase("topology").operations if op.entity_id == CORE_ID)
    assert [(change.field, change.before, change.after) for change in changes] == [("control", before, mode)]

    result = plan.apply()
    assert result.status == "succeeded" and result.verification == "confirmed"
    wire = next(payload for action, payload in server.writes if action == "update_topology")["replaceVertices"][CORE_ID]
    assert "control" not in wire
    assert wire["controlProps"] == (None if mode == "off" else {**props, "onlyInitial": mode == "semi"})
    server.writes.clear()
    assert engine.apply(_device(), blueprint, scope="topology").status == "no_change"
    assert server.writes == []


def test_explicit_override_wins_and_yaml_off_is_a_string(app: SimpleNamespace, server: FakeInspectServer) -> None:
    _install_core(server)
    engine = ProvisioningEngine(app, processors={"example-org.core": CoreProcessor})
    blueprint = Blueprint.from_yaml("""
schema_version: 1
defaults:
  topology:
    vertex_processor: {processor_type: example-org.core}
    vertices:
      - factory_label: Switching Core
        kind: ip
        fields: {control: off}
""")
    result = engine.apply(_device(), blueprint, scope="topology")
    assert result.verification == "confirmed"
    assert server.vertex_forms[CORE_ID]["fields"]["controlProps"] is None


def test_control_change_invalidates_saved_plan(app: SimpleNamespace, server: FakeInspectServer) -> None:
    _install_core(server)
    engine = ProvisioningEngine(app, processors={"example-org.core": CoreProcessor})
    plan = engine.plan(_device(), _blueprint(), scope="topology")
    server.vertex_forms[CORE_ID]["fields"]["controlProps"] = None
    with pytest.raises(ProvisioningApplyError, match="changed since planning"):
        plan.apply()
    assert server.writes == []


def test_control_readback_mismatch_is_reported(
    app: SimpleNamespace, server: FakeInspectServer, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_core(server)
    original = server.update_topology

    def ignore_control(delta: Any) -> Any:
        response = original(delta)
        server.vertex_forms[CORE_ID]["fields"]["controlProps"] = None
        return response

    monkeypatch.setattr(server, "update_topology", ignore_control)
    engine = ProvisioningEngine(app, processors={"example-org.core": CoreProcessor})
    result = engine.apply(_device(), _blueprint(), scope="topology")
    assert result.status == "succeeded" and result.verification == "unconfirmed" and not result.ok
    assert f"{CORE_ID}.control" in result.verification_detail


@pytest.mark.parametrize("layout", ["tx", "rx", "four_split"])
@pytest.mark.parametrize("configure", [False, True])
def test_matrox_control_writes_only_when_requested(
    app: SimpleNamespace, server: FakeInspectServer, layout: str, configure: bool
) -> None:
    server.install(matrox_layout("device-a", layout))
    for vertex in server.vertex_forms.values():
        vertex["fields"]["controlProps"] = None
    blueprint = Blueprint.from_dict(
        {
            "schema_version": 1,
            "defaults": {
                "topology": {
                    "vertex_processor": {
                        "processor_type": "matrox.convertip.default",
                        "params": {"configure_control": configure},
                    }
                }
            },
        }
    )
    engine = ProvisioningEngine(app)
    result = engine.apply(_device(), blueprint, scope="topology")
    assert result.verification == "confirmed"
    for vertex in server.vertex_forms.values():
        fields = vertex["fields"]
        expected = (
            {"configPriority": "off", "onlyInitial": False}
            if configure and fields["typeFields"]["type"] == "codec"
            else None
        )
        assert fields["controlProps"] == expected
        assert "control" not in fields
    assert engine.apply(_device(), blueprint, scope="topology").status == "no_change"


@pytest.mark.parametrize("value", [None, "invalid", True])
def test_control_patch_validation(value: Any) -> None:
    with pytest.raises(ValidationError):
        VertexPatch(control=value)
    with pytest.raises(ProvisioningValidationError):
        Blueprint.from_dict(
            {
                "schema_version": 1,
                "defaults": {"topology": {"vertices": [{"vertex_id": CORE_ID, "fields": {"control": value}}]}},
            }
        )


def test_omitted_control_is_unmanaged() -> None:
    assert "control" not in VertexPatch().managed()


# --- Internal ---


def _device() -> ProvisioningDevice:
    return ProvisioningDevice(key="key-a", label="device-a", topology=DeviceTarget(device_id="device-a"))


def _blueprint(mode: str = "full") -> Blueprint:
    topology: dict[str, Any] = {"vertex_processor": {"processor_type": "example-org.core", "params": {"control": mode}}}
    return Blueprint.from_dict({"schema_version": 1, "defaults": {"topology": topology}})


def _install_core(server: FakeInspectServer) -> None:
    server.install(
        build_layout("device-a", {"device-a.dev.0": [("core", "Switching Core", [("v", "Internal", "ip", None)])]})
    )
    server.vertex_forms[CORE_ID]["fields"]["controlProps"] = {
        "configPriority": "high",
        "onlyInitial": True,
        "extension": "value-a",
    }
