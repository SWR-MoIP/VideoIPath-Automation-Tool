"""Document validation, variant resolution, driver validation, and schema export."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel, ConfigDict

from videoipath_automation_tool.provisioning import (
    Blueprint,
    InventorySettings,
    ProcessorRegistry,
    ProcessorResult,
    ProvisioningValidationError,
    VertexProcessor,
    published_json_schema,
)
from videoipath_automation_tool.provisioning.resolution import resolve_blueprint

NMOS = "com.nevion.NMOS_multidevice-0.1.0"


def _document() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "defaults": {
            "inventory": {
                "driver_id": NMOS,
                "generic_settings": {"enable_https": False, "http_auth": 0},
                "custom_settings": {"port": 8080, "disable_rx_sdp_with_null": True},
                "metadata": {"site": "site-a"},
            },
            "topology": {
                "device": {"icon_size": "medium", "tags": ["tag-a"]},
                "vertex_processor": {
                    "processor_type": "matrox.convertip.default",
                    "params": {"redundant_streams": True, "video_receiver_tags": ["video-tag-a"]},
                },
                "naming": {"endpoint_label": "{device.label}-{endpoint.index:02d}"},
            },
        },
        "variants": {
            "secure": {"inventory": {"generic_settings": {"enable_https": True}, "custom_settings": {"port": 443}}},
            "other-driver": {
                "inventory": {"driver_id": "com.nevion.NMOS-0.1.0", "custom_settings": {"always_enable_rtp": True}}
            },
            "receiver": {"topology": {"vertex_processor": {"params": {"mode": "rx", "video_receiver_tags": []}}}},
            "no-processor": {"topology": {"vertex_processor": None, "device": {"tags": []}}},
            "custom": {
                "topology": {
                    "vertex_processor": {"processor_type": "example-org.simple", "params": {"factory_label": "x"}}
                }
            },
        },
    }


class _SimpleParams(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    factory_label: str


class _Simple(VertexProcessor[_SimpleParams]):
    params_model = _SimpleParams

    def process(self, context: Any, params: _SimpleParams) -> ProcessorResult:
        return ProcessorResult()


def _registry() -> ProcessorRegistry:
    return ProcessorRegistry({"example-org.simple": _Simple})


def _resolve(blueprint: Blueprint, **kwargs: Any) -> Any:
    options = {"scope": "all", "registry": _registry()}
    options.update(kwargs)
    return resolve_blueprint(blueprint, **options)


def test_named_variant_patches_default_and_records_provenance() -> None:
    resolved = _resolve(Blueprint.from_dict(_document()), variants=["secure", "receiver"])
    assert resolved.inventory.custom_settings == {"port": 443, "disable_rx_sdp_with_null": True}
    assert resolved.inventory.config.generic_settings.managed() == {"enable_https": True, "http_auth": 0}
    assert resolved.inventory.provenance["custom_settings.port"] == "variant:secure"
    assert resolved.inventory.provenance["custom_settings.disable_rx_sdp_with_null"] == "defaults"
    params = resolved.topology.params
    assert (params.mode, params.redundant_streams, params.video_receiver_tags) == ("rx", True, [])
    assert resolved.naming.entries() == {"endpoint_label": "{device.label}-{endpoint.index:02d}"}


def test_null_disables_processor_and_empty_list_replaces() -> None:
    resolved = _resolve(Blueprint.from_dict(_document()), variants=["no-processor"])
    assert resolved.topology.processor_cls is None
    assert resolved.topology.config.device.managed() == {"icon_size": "medium", "tags": []}


def test_processor_change_does_not_inherit_parameters() -> None:
    resolved = _resolve(Blueprint.from_dict(_document()), variants=["custom"])
    assert resolved.topology.processor_id == "example-org.simple"
    assert resolved.topology.params == _SimpleParams(factory_label="x")


def test_driver_change_replaces_custom_settings_base() -> None:
    resolved = _resolve(Blueprint.from_dict(_document()), variants=["other-driver"])
    assert resolved.inventory.driver_id == "com.nevion.NMOS-0.1.0"
    assert resolved.inventory.custom_settings == {"always_enable_rtp": True}
    assert resolved.inventory.config.metadata == {"site": "site-a"}


def test_instance_overrides_apply_last() -> None:
    overrides = InventorySettings(custom_settings={"port": 9000}, active=False)
    resolved = _resolve(Blueprint.from_dict(_document()), overrides=overrides)
    assert resolved.inventory.custom_settings["port"] == 9000
    assert resolved.inventory.provenance["custom_settings.port"] == "instance"
    assert resolved.inventory.config.active is False


def test_unknown_variant_never_falls_back() -> None:
    with pytest.raises(
        ProvisioningValidationError, match="Available: secure, other-driver, receiver, no-processor, custom"
    ):
        _resolve(Blueprint.from_dict(_document()), variants=["reciever"])


def test_section_selection_rules() -> None:
    topology_only = Blueprint.from_dict({"schema_version": 1, "defaults": {"topology": {}}})
    assert _resolve(topology_only).skipped == {"inventory": "section absent from blueprint"}
    with pytest.raises(ProvisioningValidationError, match="no 'inventory' section"):
        _resolve(topology_only, scope="inventory")
    with pytest.raises(ProvisioningValidationError, match="Unknown variant"):
        _resolve(topology_only, variants=["secure"])
    assert _resolve(Blueprint.from_dict(_document()), scope="inventory").skipped == {
        "topology": "not in scope 'inventory'"
    }


def test_source_document_is_not_mutated() -> None:
    document = _document()
    original = copy.deepcopy(document)
    blueprint = Blueprint.from_dict(document)
    _resolve(blueprint, variants=["secure", "receiver"])
    _resolve(blueprint, variants=["secure", "receiver"])
    assert document == original
    assert (
        blueprint.model_dump(exclude_unset=True, by_alias=True)["variants"]["receiver"]
        == original["variants"]["receiver"]
    )


@pytest.mark.parametrize(
    ("patch", "message"),
    [
        ({"defaults": {"inventory": {"driver_id": NMOS, "custom_settings": {"prot": 1}}}}, "Unknown custom setting"),
        ({"defaults": {"inventory": {"driver_id": NMOS, "custom_settings": {"port": "80"}}}}, "Expected an integer"),
        (
            {"defaults": {"inventory": {"driver_id": NMOS, "custom_settings": {"port": 0}}}},
            "greater than or equal to 1",
        ),
        ({"defaults": {"inventory": {"driver_id": NMOS, "custom_settings": {"driver_id": NMOS}}}}, "driver_id"),
        ({"defaults": {"inventory": {"driver_id": "example.unknown-1.0"}}}, "Unknown driver"),
        ({"defaults": {"inventory": {"custom_settings": {}}}}, "needs a driver_id"),
        ({"defaults": {"inventory": {"driver_id": NMOS, "generic_settings": {"enable_https": "false"}}}}, "boolean"),
        (
            {"defaults": {"inventory": {"driver_id": NMOS, "naming": {"endpoint_label": "x"}}}},
            "not valid in the 'inventory'",
        ),
    ],
)
def test_inventory_validation(patch: dict[str, Any], message: str) -> None:
    with pytest.raises(ProvisioningValidationError, match=message):
        Blueprint.from_dict({"schema_version": 1, **patch}).validate_full()


@pytest.mark.parametrize(
    ("document", "message"),
    [
        ({"schema_version": 2, "defaults": {"topology": {}}}, "schema_version"),
        ({"schema_version": 1, "defaults": {}}, "needs an 'inventory' or a 'topology'"),
        ({"schema_version": 1, "variants": {"rx": {"topology": {}}}}, "Field required"),
        ({"schema_version": 1, "defaults": {"topology": {"unknown": 1}}}, "Unknown field"),
        ({"schema_version": 1, "defaults": {"topology": {"device": {"label": None}}}}, "null is not supported"),
        (
            {"schema_version": 1, "defaults": {"topology": {"device": {"tags": {"add": ["a"], "remove": ["a"]}}}}},
            "both add and remove",
        ),
        ({"schema_version": 1, "defaults": {"topology": {"vertices": [{"fields": {}}]}}}, "exactly one of"),
        (
            {"schema_version": 1, "defaults": {"topology": {"naming": {"endpoint_label": "{device.nope}"}}}},
            "unknown field",
        ),
        ({"schema_version": 1, "defaults": {"topology": {"ip_vertex_mapping": {"a": []}}}}, "at least 1"),
        ({"schema_version": "1", "defaults": {"topology": {}}}, "schema_version"),
    ],
)
def test_document_validation(document: dict[str, Any], message: str) -> None:
    with pytest.raises(ProvisioningValidationError, match=message):
        Blueprint.from_dict(document)


def test_full_validation_checks_unused_variants_and_reports_unavailable_processors() -> None:
    document = _document()
    document["variants"]["broken"] = {"topology": {"vertex_processor": {"params": {"redundant_streams": "false"}}}}
    blueprint = Blueprint.from_dict(document)
    with pytest.raises(ProvisioningValidationError) as info:
        blueprint.validate_full(ProcessorRegistry())
    codes = {issue.path: issue.code for issue in info.value.issues}
    assert codes["variants.broken.topology.vertex_processor.params.redundant_streams"] == "schema.bool_type"
    assert codes["variants.custom.topology.vertex_processor.processor_type"] == "processor.unavailable"
    blueprint.model_copy()  # structural load did not need the plugin
    _resolve(blueprint, scope="inventory")  # inventory-only use works without the plugin


def test_planning_requires_selected_processor() -> None:
    blueprint = Blueprint.from_dict(_document())
    with pytest.raises(ProvisioningValidationError, match="Unknown processor 'example-org.simple'"):
        _resolve(blueprint, variants=["custom"], registry=ProcessorRegistry())


def test_schema_export_matches_runtime_and_package() -> None:
    generated = Blueprint.json_schema(ProcessorRegistry())
    assert generated == published_json_schema()
    packaged = (
        Path(__file__).parents[2] / "src/videoipath_automation_tool/provisioning/schemas/blueprint-v1.schema.json"
    )
    assert json.loads(packaged.read_text()) == generated
    branches = generated["$defs"]["VertexProcessorSpecTemplate"]["allOf"]
    assert [b["if"]["properties"]["processor_type"]["const"] for b in branches] == ["matrox.convertip.default"]
    custom = Blueprint.json_schema(_registry())
    assert len(custom["$defs"]["VertexProcessorSpecTemplate"]["allOf"]) == 2
    assert "allOf" not in Blueprint.json_schema()["$defs"]["VertexProcessorSpecTemplate"]


def test_schema_can_restrict_processor_types_to_registered_ids() -> None:
    open_spec = Blueprint.json_schema(_registry())["$defs"]["VertexProcessorSpecTemplate"]
    assert "enum" not in open_spec["properties"]["processor_type"]
    restricted = Blueprint.json_schema(_registry(), restrict_processor_types=True)["$defs"][
        "VertexProcessorSpecTemplate"
    ]
    processor_type = restricted["properties"]["processor_type"]
    assert processor_type["enum"] == ["example-org.simple", "matrox.convertip.default"]
    assert processor_type["type"] == "string" and "anyOf" not in processor_type
    assert "processor_type" not in restricted.get("required", [])  # variants may inherit it
    assert len(restricted["allOf"]) == 2
    with pytest.raises(ValueError, match="requires a registry"):
        Blueprint.json_schema(restrict_processor_types=True)


def test_documented_example_blueprint_is_valid() -> None:
    example = Path(__file__).parents[2] / "docs/examples/07_provisioning/matrox-convertip.yml"
    blueprint = Blueprint.load(example)
    blueprint.validate_full(ProcessorRegistry())
    assert blueprint.variant_names() == ["receiver", "four-split"]
