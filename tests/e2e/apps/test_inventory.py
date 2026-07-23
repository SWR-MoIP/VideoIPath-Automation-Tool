"""Focused Inventory app suite: create → get → diff → update → clone → enable/disable.

Ordered ``@pytest.mark.incremental`` steps mirror ``docs/examples/02_inventory/``. Devices use the
mock driver and the ``E2E-`` namespace; they persist until the next e2e session-start sweep.

Run with::

    poetry run test-e2e
"""

from __future__ import annotations

from typing import Iterator

import pytest
from pydantic import BaseModel

from videoipath_automation_tool.apps.videoipath_app import VideoIPathApp

from ..helpers import MOCK_DRIVER, create_mock_device, unique_label

pytestmark = pytest.mark.e2e


class InventoryState(BaseModel):
    device_ids: list[str] = []
    label: str | None = None
    address: str | None = None


@pytest.fixture(scope="class")
def state() -> InventoryState:
    return InventoryState()


@pytest.mark.incremental
class TestInventoryLifecycle:
    def test_create_and_add(self, app: VideoIPathApp, state: InventoryState, e2e_addresses: Iterator[str]) -> None:
        state.label = unique_label("INV")
        state.address = next(e2e_addresses)
        device_id = create_mock_device(app, label=state.label, address=state.address, ports=2)
        state.device_ids.append(device_id)
        assert device_id

    def test_get_by_label_and_id(self, app: VideoIPathApp, state: InventoryState) -> None:
        assert state.label is not None
        device_id = state.device_ids[0]
        found = app.inventory.find_device_id_by_label(state.label, label_search_mode="user_defined_label_only")
        assert found == device_id
        by_id = app.inventory.get_device(device_id=device_id, config_only=True, custom_settings_type=MOCK_DRIVER)
        by_label = app.inventory.get_device(
            label=state.label, label_search_mode="user_defined_label_only", config_only=True
        )
        assert by_id.configuration.label == state.label
        assert by_label.configuration.device_id == device_id

    def test_diff_unchanged(self, app: VideoIPathApp, state: InventoryState) -> None:
        device_id = state.device_ids[0]
        reference = app.inventory.get_device(device_id=device_id, config_only=True, custom_settings_type=MOCK_DRIVER)
        staged = app.inventory.get_device(device_id=device_id, config_only=True, custom_settings_type=MOCK_DRIVER)
        diff = app.inventory.diff_device_configuration(reference_device=reference, staged_device=staged)
        assert not diff.configuration_diff.added
        assert not diff.configuration_diff.changed
        assert not diff.configuration_diff.removed

    def test_update_description(self, app: VideoIPathApp, state: InventoryState) -> None:
        device_id = state.device_ids[0]
        reference = app.inventory.get_device(device_id=device_id, config_only=True, custom_settings_type=MOCK_DRIVER)
        staged = app.inventory.get_device(device_id=device_id, config_only=True, custom_settings_type=MOCK_DRIVER)
        staged.configuration.description = "E2E inventory lifecycle device"
        diff = app.inventory.diff_device_configuration(reference_device=reference, staged_device=staged)
        assert diff.configuration_diff.changed
        app.inventory.update_device(device=staged)
        updated = app.inventory.get_device(device_id=device_id, config_only=True)
        assert updated.configuration.description == "E2E inventory lifecycle device"

    def test_dump_parse_clone(self, app: VideoIPathApp, state: InventoryState, e2e_addresses: Iterator[str]) -> None:
        device_id = state.device_ids[0]
        device = app.inventory.get_device(device_id=device_id, config_only=True, custom_settings_type=MOCK_DRIVER)
        dump = app.inventory.dump_configuration(device)
        clone = app.inventory.parse_configuration(dump)
        clone.configuration.label = unique_label("INV-CLONE")
        clone.configuration.address = next(e2e_addresses)
        clone.remove_device_id()
        cloned = app.inventory.add_device(device=clone, address_check=False)
        state.device_ids.append(cloned.configuration.device_id)
        assert cloned.configuration.device_id != device_id
        assert cloned.configuration.label == clone.configuration.label

    def test_disable_and_enable(self, app: VideoIPathApp, state: InventoryState) -> None:
        device_id = state.device_ids[0]
        disabled = app.inventory.disable_device(device_id)
        assert disabled.configuration.active is False
        enabled = app.inventory.enable_device(device_id)
        assert enabled.configuration.active is True
