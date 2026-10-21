"""Blueprint entry points load file inputs and retain reviewed content for later application."""

from __future__ import annotations

from pathlib import Path, PurePath
from types import SimpleNamespace

import pytest

from tests.provisioning.conftest import NMOS, FakeInventory
from videoipath_automation_tool.provisioning import (
    Blueprint,
    ProvisioningDevice,
    ProvisioningEngine,
    ProvisioningValidationError,
)


@pytest.fixture
def blueprint_path(tmp_path: Path) -> Path:
    path = tmp_path / "device-blueprint.yml"
    path.write_text(
        f"schema_version: 1\ndefaults:\n  inventory:\n    driver_id: {NMOS}\n    custom_settings: {{port: 8080}}\n",
        encoding="utf-8",
    )
    return path


@pytest.mark.parametrize("source_type", [str, Path, PurePath], ids=["string", "path", "pathlike"])
def test_file_inputs_match_blueprint_instances(
    blueprint_path: Path, inventory: FakeInventory, source_type: type[str | PurePath]
) -> None:
    inventory.seed("device1", label="device-a", custom={"port": 80})
    engine = ProvisioningEngine(SimpleNamespace(inventory=inventory))
    device = ProvisioningDevice(key="device-a", label="device-a", inventory_id="device1")
    source = source_type(blueprint_path)

    engine.validate(source)
    expected = engine.plan(device, Blueprint.load(blueprint_path), scope="inventory")
    actual = engine.plan(device, source, scope="inventory")
    assert actual.model_dump() == expected.model_dump()
    assert inventory.writes == []

    result = engine.apply(device, source, scope="inventory")
    assert result.status == "succeeded"
    assert inventory.devices["device1"].configuration.custom_settings.port == 8080


def test_apply_loads_file_once(blueprint_path: Path, inventory: FakeInventory, monkeypatch: pytest.MonkeyPatch) -> None:
    inventory.seed("device1", label="device-a", custom={"port": 80})
    engine = ProvisioningEngine(SimpleNamespace(inventory=inventory))
    device = ProvisioningDevice(key="device-a", label="device-a", inventory_id="device1")
    original_load = Blueprint.load
    loaded: list[Path] = []

    def load_once(path: Path) -> Blueprint:
        loaded.append(path)
        return original_load(path)

    monkeypatch.setattr(Blueprint, "load", load_once)
    engine.apply(device, blueprint_path, scope="inventory")
    assert loaded == [blueprint_path]


def test_plans_keep_loaded_content_when_file_changes_or_disappears(
    blueprint_path: Path, inventory: FakeInventory
) -> None:
    inventory.seed("device1", label="device-a", custom={"port": 80})
    engine = ProvisioningEngine(SimpleNamespace(inventory=inventory))
    device = ProvisioningDevice(key="device-a", label="device-a", inventory_id="device1")

    first = engine.plan(device, blueprint_path, scope="inventory")
    blueprint_path.write_text(blueprint_path.read_text(encoding="utf-8").replace("8080", "9090"), encoding="utf-8")
    first.apply()
    assert inventory.devices["device1"].configuration.custom_settings.port == 8080

    second = engine.plan(device, blueprint_path, scope="inventory")
    assert second.blueprint_digest != first.blueprint_digest
    blueprint_path.unlink()
    second.apply()
    assert inventory.devices["device1"].configuration.custom_settings.port == 9090


@pytest.mark.parametrize("method", ["plan", "apply", "validate"])
def test_file_errors_happen_before_app_access(
    blueprint_path: Path, method: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = ProvisioningEngine(SimpleNamespace())
    device = ProvisioningDevice(key="device-a", label="device-a", inventory_id="device1")
    operation = getattr(engine, method)
    args = () if method == "validate" else (device,)
    monkeypatch.chdir(blueprint_path.parent)

    with pytest.raises(FileNotFoundError):
        operation(*args, "missing.yml")
    with pytest.raises(FileNotFoundError):
        operation(*args, "schema_version: 1")  # Strings are paths, not implicit YAML documents.

    blueprint_path.write_text("schema_version: 1\nschema_version: 1\n", encoding="utf-8")
    with pytest.raises(ProvisioningValidationError, match="duplicate key") as error:
        operation(*args, blueprint_path.name)
    assert blueprint_path.name in str(error.value)


@pytest.mark.parametrize("method", ["plan", "apply", "validate"])
def test_invalid_blueprint_input_has_a_useful_type_error(method: str) -> None:
    engine = ProvisioningEngine(SimpleNamespace())
    device = ProvisioningDevice(key="device-a", label="device-a", inventory_id="device1")
    args = () if method == "validate" else (device,)
    with pytest.raises(TypeError, match="Blueprint instance or a YAML file path"):
        getattr(engine, method)(*args, {"schema_version": 1})
