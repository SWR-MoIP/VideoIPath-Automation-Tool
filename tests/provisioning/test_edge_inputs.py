"""Schema-v2 binding, overlay and source-location behavior of generic port mappings."""

from __future__ import annotations

from typing import Any

import pytest

from tests.provisioning.conftest import FakeInspectServer, FakeInventory
from tests.provisioning.test_edges import _device, _edge, _seed
from videoipath_automation_tool.provisioning import Blueprint, ProvisioningEngine, ProvisioningValidationError
from videoipath_automation_tool.provisioning.resolution import resolve_blueprint


@pytest.mark.parametrize("position", ["value", "selector", "list", "mapping"])
def test_typed_mapping_input_positions(
    engine: ProvisioningEngine,
    inventory: FakeInventory,
    server: FakeInspectServer,
    position: str,
) -> None:
    _seed(inventory, server)
    expression = {"$input": "ports"}
    mappings = {
        "value": {"uplink": [{"factory_label": expression}]},
        "selector": {"uplink": [expression]},
        "list": {"uplink": expression},
        "mapping": expression,
    }
    values = {
        "value": "P1",
        "selector": {"factory_label": "P1"},
        "list": [{"factory_label": "P1"}],
        "mapping": {"uplink": [{"factory_label": "P1"}]},
    }
    definitions = {
        "value": {"type": "string"},
        "selector": {"type": "object", "additionalProperties": True},
        "list": {"type": "array", "items": {"type": "object", "additionalProperties": True}},
        "mapping": {"type": "object", "additionalProperties": True},
    }
    blueprint = Blueprint.from_dict(
        {
            "schema_version": 1,
            "inputs": {"ports": definitions[position]},
            "defaults": {"topology": {"port_mapping": mappings[position]}},
        }
    )
    inputs = {"ports": values[position]}
    resolved = resolve_blueprint(blueprint, inputs=inputs)
    assert any("input:ports" in source for source in resolved.topology.provenance.values())
    plan = engine.plan(_device(_edge()), blueprint, inputs=inputs)
    inputs["ports"] = "changed"
    result = plan.apply()
    assert result.edges[0].local.port_id == "device1.dev.0.P1"
    assert result.ok and len(server.edge_forms) == 2


def test_mapping_overlay_order_lists_replace_and_atomic_inputs() -> None:
    blueprint = Blueprint.from_dict(
        {
            "schema_version": 1,
            "inputs": {
                "ports": {
                    "type": "object",
                    "additionalProperties": True,
                    "default": {"replacement": [{"factory_label": "P3"}]},
                }
            },
            "defaults": {
                "topology": {
                    "port_mapping": {
                        "uplink": [{"factory_label": "missing"}, {"factory_label": "P1"}],
                        "other": [{"factory_label": "P2"}],
                    }
                }
            },
            "variants": {
                "first": {"topology": {"port_mapping": {"uplink": [{"factory_label": "P2"}]}}},
                "second": {"topology": {"port_mapping": {"uplink": [{"factory_label": "P1"}]}}},
                "input": {"topology": {"port_mapping": {"$input": "ports"}}},
            },
        }
    )
    resolved = resolve_blueprint(blueprint, variants=["first", "second"])
    assert [item.factory_label for item in resolved.topology.config.port_mapping["uplink"]] == ["P1"]
    assert set(resolved.topology.config.port_mapping) == {"uplink", "other"}
    assert resolved.topology.provenance["port_mapping.uplink"] == "variant:second"
    assert set(resolve_blueprint(blueprint, variants=["input"]).topology.config.port_mapping) == {"replacement"}
    assert len(blueprint.defaults.topology.port_mapping["uplink"]) == 2


def test_literal_and_inserted_operator_text_is_not_reinterpreted() -> None:
    blueprint = Blueprint.from_dict(
        {
            "schema_version": 1,
            "inputs": {"label": {"type": "string", "default": "$input: not-an-operator"}},
            "defaults": {
                "topology": {
                    "port_mapping": {
                        "literal": {"$literal": [{"factory_label": "$input: literal"}]},
                        "inserted": [{"factory_label": {"$input": "label"}}],
                    }
                }
            },
        }
    )
    mapping = resolve_blueprint(blueprint).topology.config.port_mapping
    assert mapping["literal"][0].factory_label == "$input: literal"
    assert mapping["inserted"][0].factory_label == "$input: not-an-operator"


def test_runtime_selector_errors_retain_yaml_origin_and_fail_before_io() -> None:
    blueprint = Blueprint.from_yaml(
        """schema_version: 1
inputs:
  selector:
    type: object
    additionalProperties: true
defaults:
  topology:
    port_mapping:
      uplink:
      - {$input: selector}
""",
        source="device.yml",
    )

    class NoIO:
        def __getattr__(self, key: str) -> Any:
            raise AttributeError(f"unexpected I/O: {key}")

    with pytest.raises(ProvisioningValidationError, match="exactly one") as error:
        ProvisioningEngine(NoIO()).plan(
            _device(_edge()), blueprint, inputs={"selector": {"port_id": "port-a", "factory_label": "P1"}}
        )
    issue = error.value.issues[0]
    assert issue.source == "device.yml" and issue.line == 10
    assert issue.path.startswith("defaults.topology.port_mapping")


def test_missing_mapping_input_is_only_required_in_effective_scope() -> None:
    blueprint = Blueprint.from_dict(
        {
            "schema_version": 1,
            "inputs": {"port": {"type": "string"}},
            "defaults": {
                "inventory": {"driver_id": "com.nevion.NMOS_multidevice-0.1.0"},
                "topology": {"port_mapping": {"uplink": [{"factory_label": {"$input": "port"}}]}},
            },
            "variants": {"fixed": {"topology": {"port_mapping": {"uplink": [{"factory_label": "P1"}]}}}},
        }
    )
    assert resolve_blueprint(blueprint, scope="inventory").topology is None
    with pytest.raises(ProvisioningValidationError, match="Required input is missing"):
        resolve_blueprint(blueprint)
    assert (
        resolve_blueprint(blueprint, variants=["fixed"]).topology.config.port_mapping["uplink"][0].factory_label == "P1"
    )
