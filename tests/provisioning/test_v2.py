"""Typed inputs and ordered overlays, exercised through resolution and the real engine."""

from __future__ import annotations

import copy
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel, ConfigDict, JsonValue

from tests.provisioning.conftest import NMOS, FakeInspectServer, FakeInventory, matrox_layout
from videoipath_automation_tool.provisioning import (
    Blueprint,
    InputDefinition,
    InventorySettings,
    NamingScheme,
    ProcessorRegistry,
    ProcessorResult,
    ProvisioningDevice,
    ProvisioningEngine,
    ProvisioningValidationError,
    VertexProcessor,
)
from videoipath_automation_tool.provisioning.naming import NameContext, render_name
from videoipath_automation_tool.provisioning.resolution import resolve_blueprint


def _document() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "inputs": {
            "port": {"type": "integer", "default": 8080},
            "enabled": {"type": "boolean", "default": False},
            "tags": {"type": "array", "items": {"type": "string"}, "default": []},
            "site": {
                "type": "object",
                "properties": {"code": {"type": "string"}},
                "required": ["code"],
                "default": {"code": "site-a"},
            },
        },
        "defaults": {
            "inventory": {
                "driver_id": NMOS,
                "custom_settings": {"port": {"$input": "port"}},
                "generic_settings": {"enable_https": {"$input": "enabled"}},
                "metadata": {"site": "site-a"},
            },
            "topology": {
                "vertex_processor": {
                    "processor_type": "matrox.convertip.default",
                    "params": {"video_sender_tags": {"$input": "tags"}},
                },
                "naming": {"endpoint_label": "{device.label}-{inputs.site.code}-{endpoint.media}-{endpoint.index:02d}"},
            },
        },
        "variants": {
            "secure": {"inventory": {"custom_settings": {"port": 443}}},
            "alternate": {"inventory": {"custom_settings": {"port": 9000}}},
            "receiver": {"topology": {"vertex_processor": {"params": {"mode": "rx"}}}},
        },
    }


def _blueprint(**updates: Any) -> Blueprint:
    document = _document()
    document.update(updates)
    return Blueprint.from_dict(document)


def _resolve(blueprint: Blueprint, **kwargs: Any) -> Any:
    return resolve_blueprint(blueprint, registry=ProcessorRegistry(), **kwargs)


def test_inputs_preserve_types_and_provenance_and_overrides_apply_last() -> None:
    resolved = _resolve(_blueprint(), inputs={"port": 9090})
    assert resolved.inventory.custom_settings == {"port": 9090}
    assert resolved.inventory.config.generic_settings.enable_https is False
    assert resolved.topology.params.video_sender_tags == []
    assert resolved.inventory.provenance["custom_settings.port"] == "defaults|input:port"
    assert resolved.topology.provenance["vertex_processor.params.video_sender_tags"] == "defaults|input:tags"
    overridden = _resolve(
        _blueprint(), inputs={"port": 9090}, overrides=InventorySettings(custom_settings={"port": 10000})
    )
    assert overridden.inventory.custom_settings == {"port": 10000}
    assert overridden.inventory.provenance["custom_settings.port"] == "instance"


@pytest.mark.parametrize(
    ("inputs", "code"),
    [
        ({"port": True}, "input.type"),
        ({"port": "8080"}, "input.type"),
        ({"port": 8080.0}, "input.type"),
        ({"enabled": 0}, "input.type"),
        ({"tags": [False]}, "input.type"),
        ({"site": {}}, "input.missing"),
        ({"site": {"code": "site-a", "unknown": 1}}, "input.unknown_property"),
        ({"other": 1}, "input.unknown"),
    ],
)
def test_bad_inputs_fail_before_app_access(inputs: dict[str, JsonValue], code: str) -> None:
    engine = ProvisioningEngine(SimpleNamespace())
    device = ProvisioningDevice(key="device-a", label="device-a")
    with pytest.raises(ProvisioningValidationError) as error:
        engine.plan(device, _blueprint(), inputs=inputs)
    assert code in {issue.code for issue in error.value.issues}


@pytest.mark.parametrize(
    "definition",
    [
        {"type": "integer", "default": True},
        {"type": "boolean", "default": "false"},
        {"type": "integer", "enum": [False]},
        {"type": "integer", "enum": [1], "default": 2},
        {"type": "array", "items": {"type": "string"}, "default": [1]},
        {"type": "object", "default": {"undeclared": 1}},
        {"type": "object", "required": ["missing"]},
        {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a", "a"]},
        {"type": "string", "items": {"type": "string"}},
        {"type": "string", "properties": {}},
    ],
)
def test_invalid_input_declarations_fail_on_load(definition: dict[str, Any]) -> None:
    with pytest.raises(ProvisioningValidationError):
        Blueprint.from_dict({"schema_version": 1, "inputs": {"bad": definition}, "defaults": {"topology": {}}})


def test_all_input_types_and_open_objects() -> None:
    definitions = {
        "text": {"type": "string", "default": ""},
        "integer": {"type": "integer", "default": 0},
        "number": {"type": "number", "default": 1.5},
        "boolean": {"type": "boolean", "default": False},
        "array": {"type": "array", "default": [None, {"a": 1}]},
        "object": {"type": "object", "additionalProperties": True, "default": {"a": [None]}},
        "null_value": {"type": "null", "default": None},
    }
    blueprint = Blueprint.from_dict({"schema_version": 1, "inputs": definitions, "defaults": {"topology": {}}})
    assert _resolve(blueprint).inputs == {name: spec["default"] for name, spec in definitions.items()}
    assert InputDefinition(type="number", default=2).default == 2


def test_requiredness_uses_effective_scope_and_overlays() -> None:
    document = _document()
    document["inputs"]["port"].pop("default")
    document["defaults"]["inventory"]["metadata"] = {}
    blueprint = Blueprint.from_dict(document)
    with pytest.raises(ProvisioningValidationError, match="Required input is missing"):
        _resolve(blueprint)
    assert _resolve(blueprint, scope="topology").inventory is None
    assert _resolve(blueprint, variants=["secure"]).inventory.custom_settings == {"port": 443}
    blueprint.validate_full(ProcessorRegistry(), variants=["secure"])
    with pytest.raises(ProvisioningValidationError, match="Required input is missing"):
        blueprint.validate_full(ProcessorRegistry())


def test_overlay_order_and_cross_section_selection() -> None:
    blueprint = _blueprint()
    first = _resolve(blueprint, variants=["secure", "alternate", "receiver"])
    second = _resolve(blueprint, variants=["alternate", "secure"])
    assert first.inventory.custom_settings == {"port": 9000}
    assert first.topology.params.mode == "rx"
    assert first.variants == ("secure", "alternate", "receiver")
    assert second.inventory.custom_settings == {"port": 443}
    assert first.inventory.provenance["custom_settings.port"] == "variant:alternate"


@pytest.mark.parametrize("variants", [["secure", "secure"], ["missing"]])
def test_invalid_variant_selection(variants: list[str]) -> None:
    with pytest.raises(ProvisioningValidationError):
        _resolve(_blueprint(), variants=variants)


@pytest.mark.parametrize("variants", ["secure", {"secure"}, [1]])
def test_variant_argument_must_be_a_sequence_of_names(variants: Any) -> None:
    with pytest.raises(TypeError, match="sequence of names"):
        _resolve(_blueprint(), variants=variants)


def test_overlay_can_add_a_section() -> None:
    blueprint = Blueprint.from_dict(
        {
            "schema_version": 1,
            "defaults": {"topology": {}},
            "variants": {"onboard": {"inventory": {"driver_id": NMOS}}},
        }
    )
    assert _resolve(blueprint, variants=["onboard"], scope="inventory").inventory.driver_id == NMOS


class _PayloadParams(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    payload: JsonValue


class _PayloadProcessor(VertexProcessor[_PayloadParams]):
    params_model = _PayloadParams

    def process(self, context: Any, params: _PayloadParams) -> ProcessorResult:
        return ProcessorResult()


def _payload_blueprint(payload: Any, inputs: dict[str, Any] | None = None) -> Blueprint:
    return Blueprint.from_dict(
        {
            "schema_version": 1,
            "inputs": inputs or {},
            "defaults": {
                "topology": {
                    "vertex_processor": {"processor_type": "example-org.payload", "params": {"payload": payload}}
                }
            },
        }
    )


def _payload(blueprint: Blueprint, **kwargs: Any) -> Any:
    registry = ProcessorRegistry({"example-org.payload": _PayloadProcessor})
    return resolve_blueprint(blueprint, registry=registry, **kwargs).topology.params.payload


def test_nested_references_and_literal_escapes_are_not_reinterpreted() -> None:
    blueprint = _payload_blueprint(
        [{"$input": "facts"}, {"$literal": {"$input": "not-declared"}}],
        {"facts": {"type": "object", "additionalProperties": True}},
    )
    value = {"$input": "also-not-declared", "nested": [False, 0, ""]}
    assert _payload(blueprint, inputs={"facts": value}) == [value, {"$input": "not-declared"}]


def test_whole_object_reference_is_atomic_during_merge() -> None:
    blueprint = _payload_blueprint({"a": 1, "b": 2}, {"replacement": {"type": "object", "additionalProperties": True}})
    document = blueprint.model_dump(by_alias=True, exclude_unset=True)
    document["variants"] = {
        "replace": {"topology": {"vertex_processor": {"params": {"payload": {"$input": "replacement"}}}}}
    }
    assert _payload(Blueprint.from_dict(document), variants=["replace"], inputs={"replacement": {"c": 3}}) == {"c": 3}


@pytest.mark.parametrize(
    "payload", [{"$input": "unknown"}, {"$input": "known", "extra": 1}, {"$literal": 1, "$input": "known"}]
)
def test_unknown_or_malformed_references_fail_on_load(payload: Any) -> None:
    with pytest.raises(ProvisioningValidationError):
        _payload_blueprint(payload, {"known": {"type": "string"}})


def test_static_ids_and_unknown_fields_cannot_be_parameterized() -> None:
    document = _blueprint().model_dump(by_alias=True, exclude_unset=True)
    document["defaults"]["inventory"]["driver_id"] = {"$input": "port"}
    with pytest.raises(ProvisioningValidationError):
        Blueprint.from_dict(document)
    document["defaults"]["inventory"]["driver_id"] = NMOS
    document["defaults"]["topology"]["vertex_processor"] = {"$input": "port"}
    with pytest.raises(ProvisioningValidationError):
        Blueprint.from_dict(document)
    document["defaults"]["topology"]["vertex_processor"] = {"processor_type": "matrox.convertip.default"}
    document["defaults"]["inventory"]["typo"] = {"$input": "port"}
    with pytest.raises(ProvisioningValidationError, match="Unknown field"):
        Blueprint.from_dict(document)


def test_reference_error_and_driver_validation_keep_yaml_origin() -> None:
    text = f"""schema_version: 1
inputs:
  port: {{type: integer, default: 0}}
defaults:
  inventory:
    driver_id: {NMOS}
    custom_settings:
      port: {{$input: port}}
"""
    blueprint = Blueprint.from_yaml(text, source="device.yml")
    with pytest.raises(ProvisioningValidationError) as error:
        _resolve(blueprint)
    issue = error.value.issues[0]
    assert (issue.path, issue.source, issue.line) == ("defaults.inventory.custom_settings.port", "device.yml", 8)
    with pytest.raises(ProvisioningValidationError) as error:
        Blueprint.from_yaml(text.replace("$input: port", "$input: unknown"), source="device.yml")
    assert error.value.issues[0].line == 8


def test_naming_inputs_include_object_leaves_and_keep_literal_text() -> None:
    naming = NamingScheme(
        endpoint_label={"join": [{"text": "{inputs.literal}"}, {"field": "inputs.site.code"}], "separator": "-"}
    )
    assert (
        render_name("endpoint_label", naming.endpoint_label, NameContext(inputs={"site": {"code": "site-a"}}))
        == "{inputs.literal}-site-a"
    )
    blueprint = _blueprint()
    document = blueprint.model_dump(by_alias=True, exclude_unset=True)
    document["defaults"]["topology"]["naming"] = {"endpoint_label": "{inputs.site.unknown}"}
    with pytest.raises(ProvisioningValidationError, match="Unknown property"):
        Blueprint.from_dict(document)


def test_engine_uses_and_captures_inputs_for_all_naming_targets(
    engine: ProvisioningEngine, inventory: FakeInventory, server: FakeInspectServer
) -> None:
    inventory.seed("device1", label="device-a", custom={"port": 8080})
    server.install(matrox_layout("device1", "tx"))
    document = _blueprint().model_dump(by_alias=True, exclude_unset=True)
    document["defaults"]["inventory"]["naming"] = {"inventory_label": "{inputs.site.code}-{device.label}"}
    document["defaults"]["topology"]["naming"]["device_label"] = "{inputs.site.code}-{device.label}"
    blueprint = Blueprint.from_dict(document)
    original = copy.deepcopy(document)
    inputs: dict[str, Any] = {"site": {"code": "site-b"}, "tags": ["video-tag-a"]}
    variants: list[str] = []
    device = ProvisioningDevice(key="device-a", label="device-a", inventory_id="device1")
    plan = engine.plan(device, blueprint, inputs=inputs, variants=variants)
    inputs["site"]["code"] = "changed"
    inputs["tags"].append("changed")
    variants.append("receiver")
    result = plan.apply()
    assert result.ok and plan.variants == ()
    assert inventory.devices["device1"].configuration.config.desc.label == "site-b-device-a"
    assert server.device_forms["device1"]["descriptor"]["label"] == "site-b-device-a"
    changes = [change for operation in result.phase("topology").operations for change in operation.changes]
    assert any(change.after == "device-a-site-b-video-01" for change in changes)
    assert blueprint.model_dump(by_alias=True, exclude_unset=True) == original
    assert (
        engine.apply(device, blueprint, inputs={"site": {"code": "site-b"}, "tags": ["video-tag-a"]}).status
        == "no_change"
    )


def test_combined_variants_are_validated_and_captured_before_app_access() -> None:
    blueprint = _blueprint()
    engine = ProvisioningEngine(SimpleNamespace())
    engine.validate(blueprint, variants=["secure", "receiver"])
    device = ProvisioningDevice(key="device-a", label="device-a")
    with pytest.raises(ProvisioningValidationError):
        engine.plan(device, blueprint, inputs={"port": "secret-value"})
    with pytest.raises(ProvisioningValidationError) as error:
        engine.validate(blueprint, inputs={"port": "secret-value"})
    assert "secret-value" not in str(error.value)


@pytest.mark.parametrize("naming", ["{inputs.unknown}", "{inputs.site}", "{inputs.site.code}"])
def test_call_time_naming_input_validation_happens_before_reads(naming: str) -> None:
    engine = ProvisioningEngine(SimpleNamespace())
    document = _blueprint().model_dump(by_alias=True, exclude_unset=True)
    document["inputs"]["site"].pop("default")
    document["defaults"].pop("topology")
    device = ProvisioningDevice(key="device-a", label="device-a")
    values = {"site": {"code": "site-a"}} if naming == "{inputs.site}" else None
    with pytest.raises(ProvisioningValidationError):
        engine.plan(device, Blueprint.from_dict(document), inputs=values, naming=NamingScheme(inventory_label=naming))


def test_unused_naming_inputs_do_not_affect_inventory_only_plans(inventory: FakeInventory) -> None:
    inventory.seed("device1", label="device-a", custom={"port": 8080})
    engine = ProvisioningEngine(
        SimpleNamespace(inventory=inventory), naming=NamingScheme(endpoint_label="{inputs.tags}")
    )
    device = ProvisioningDevice(key="device-a", label="device-a", inventory_id="device1")
    assert engine.plan(device, _blueprint(), scope="inventory").fully_resolved


@pytest.mark.parametrize("version", [True, 2.0, "2"])
def test_schema_version_is_strictly_an_integer(version: Any) -> None:
    with pytest.raises(ProvisioningValidationError):
        Blueprint.from_dict({"schema_version": version, "defaults": {"topology": {}}})


def test_full_validation_reports_errors_in_both_sections() -> None:
    document = _blueprint().model_dump(by_alias=True, exclude_unset=True)
    document["defaults"]["inventory"]["custom_settings"]["port"] = 0
    document["defaults"]["topology"]["vertex_processor"]["params"]["mode"] = "invalid"
    with pytest.raises(ProvisioningValidationError) as error:
        Blueprint.from_dict(document).validate_full(ProcessorRegistry(), variants=[])
    assert {issue.path for issue in error.value.issues} == {
        "defaults.inventory.custom_settings.port",
        "defaults.topology.vertex_processor.params.mode",
    }
