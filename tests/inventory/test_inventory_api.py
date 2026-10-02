"""InventoryAPI address lookups and typed write rejections with a fake connector."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from videoipath_automation_tool.apps.inventory.app.app import InventoryApp
from videoipath_automation_tool.apps.inventory.errors import InventoryWriteNotAppliedError
from videoipath_automation_tool.apps.inventory.inventory_api import InventoryAPI
from videoipath_automation_tool.apps.inventory.model.inventory_device import InventoryDevice

NMOS = "com.nevion.NMOS_multidevice-0.1.0"


class FakeRest:
    def __init__(self, data: Any) -> None:
        self._data = data
        self.get_calls: list[str] = []

    def get(self, url_path: str, **kwargs: Any) -> SimpleNamespace:
        self.get_calls.append(url_path)
        return SimpleNamespace(data=self._data)


class FakeRpc:
    def __init__(self, status: str) -> None:
        self._status = status

    def post(self, url_path: str, body: Any, **kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(header=SimpleNamespace(status=self._status))


def _api(data: Any = None, *, rpc_status: str = "OK") -> InventoryAPI:
    return InventoryAPI(SimpleNamespace(rest=FakeRest(data), rpc=FakeRpc(rpc_status)))  # type: ignore[arg-type]


def _devices(*devices: dict[str, Any]) -> dict[str, Any]:
    return {"config": {"devman": {"devices": {"_items": list(devices)}}}}


def _device(device_id: str, address: Any, alternates: Any = None) -> dict[str, Any]:
    cinfo: dict[str, Any] = {"address": address}
    if alternates is not None:
        cinfo["altAddresses"] = alternates
    return {"_id": device_id, "config": {"cinfo": cinfo}}


# --- Address lookups ---


def test_find_device_ids_by_addresses_normalizes_both_sides_in_one_read() -> None:
    api = _api(
        _devices(
            _device("device1", "Device-A.example"),
            _device("device2", "192.0.2.1", ["2001:db8:0:0::1"]),
            _device("device3", "192.0.2.3", None),
        )
    )
    found = api.find_device_ids_by_addresses(["device-a.example", "2001:db8::1", " 192.0.2.3 ", "192.0.2.9", ""])
    assert found == {
        "device-a.example": ["device1"],
        "2001:db8::1": ["device2"],
        " 192.0.2.3 ": ["device3"],
        "192.0.2.9": [],
    }
    assert len(api.vip_connector.rest.get_calls) == 1


def test_find_device_ids_by_addresses_reports_every_match_sorted() -> None:
    api = _api(_devices(_device("device2", "192.0.2.1"), _device("device1", "192.0.2.5", ["192.0.2.1"])))
    assert api.find_device_ids_by_addresses(["192.0.2.1"]) == {"192.0.2.1": ["device1", "device2"]}


@pytest.mark.parametrize("data", [None, [], {}, {"config": {"devman": {"devices": {}}}}])
def test_find_device_ids_by_addresses_without_items_is_no_match(data: Any) -> None:
    assert _api(data).find_device_ids_by_addresses(["192.0.2.1"]) == {"192.0.2.1": []}


def test_find_device_ids_by_addresses_without_input_skips_the_read() -> None:
    api = _api(_devices(_device("device1", "192.0.2.1")))
    assert api.find_device_ids_by_addresses(["", ""]) == {}
    assert api.vip_connector.rest.get_calls == []


def test_get_device_id_by_address_keeps_exact_matching() -> None:
    api = _api(_devices(_device("device1", "Device-A.example"), _device("device2", "192.0.2.1", ["192.0.2.2"])))
    assert api.get_device_id_by_address("Device-A.example") == "device1"
    assert api.get_device_id_by_address("device-a.example") is None
    assert api.get_device_id_by_address("192.0.2.2") == "device2"
    with pytest.raises(ValueError, match="Response data is empty"):
        _api(None).get_device_id_by_address("192.0.2.1")


# --- Write rejections ---


def test_rejected_add_is_typed() -> None:
    with pytest.raises(InventoryWriteNotAppliedError, match="Failed to add device") as info:
        _api(rpc_status="ERROR").add_device(InventoryDevice.create(NMOS), config_only=True)
    assert info.value.operation == "add"
    assert isinstance(info.value, ValueError)


def test_rejected_update_is_typed() -> None:
    device = InventoryDevice.create(NMOS)
    device.configuration.id = "device1"
    with pytest.raises(InventoryWriteNotAppliedError, match="Failed to update device") as info:
        _api(rpc_status="ERROR").update_device(device, config_only=True)
    assert info.value.operation == "update"


def test_failed_preread_before_update_is_typed(monkeypatch: pytest.MonkeyPatch) -> None:
    app = InventoryApp(SimpleNamespace(rest=FakeRest(None), rpc=FakeRpc("OK")))  # type: ignore[arg-type]

    def missing(**kwargs: Any) -> InventoryDevice:
        raise ValueError("timed out")

    monkeypatch.setattr(app._inventory_api, "get_device", missing)
    device = InventoryDevice.create(NMOS)
    device.configuration.id = "device1"
    with pytest.raises(InventoryWriteNotAppliedError, match="Failed to retrieve existing device") as info:
        app.update_device(device, compare_config=False, config_only=True)
    assert info.value.operation == "update"
