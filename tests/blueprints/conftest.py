"""Offline harness for blueprint tests.

- ``FakeInventory`` implements the handful of ``InventoryApp`` methods the engine uses, backed by
  in-memory :class:`InventoryDevice` records.
- ``FakeInspectServer`` is an in-memory stand-in for ``InspectAPI``; it sits behind a *real*
  ``InspectApp`` so transactions, conflict checks, and snapshot refreshes run unchanged.
- ``matrox_layout`` builds synthetic (anonymized) ConvertIP topologies: ``tx``, ``rx``, ``four_split``.
"""

from __future__ import annotations

import copy
import logging
from types import SimpleNamespace
from typing import Any

import pytest

from videoipath_automation_tool.apps.inspect.app import InspectApp
from videoipath_automation_tool.apps.inspect.model.actions import (
    InspectApiLookupInspectDeviceResponse,
    InspectApiLookupSyncInfoResponse,
    InspectApiLookupVerticesResponse,
)
from videoipath_automation_tool.apps.inspect.model.collector import InspectApiNodeStatusItem
from videoipath_automation_tool.apps.inspect.model.common import InspectApiSimpleActionResponse
from videoipath_automation_tool.apps.inspect.model.update_topology import InspectApiUpdateTopologyResponse
from videoipath_automation_tool.apps.inventory.model.inventory_device import InventoryDevice
from videoipath_automation_tool.blueprints import BlueprintEngine
from videoipath_automation_tool.utils.cross_app_utils import normalize_address

NMOS = "com.nevion.NMOS_multidevice-0.1.0"
HEADER = {"auth": True, "caption": "OK", "code": "OK", "id": "0", "ok": True, "user": "test-user"}


# --- Inventory ---


class FakeInventory:
    def __init__(self) -> None:
        self.devices: dict[str, InventoryDevice] = {}
        self.snmp: dict[str, str] = {"default": "Default configuration", "snmp-1": "snmp-a"}
        self.writes: list[tuple[str, str]] = []
        self.address_lookups = 0
        self.fail_address_read = False
        self.fail_next_write: Exception | None = None
        self._next_id = 100

    def seed(self, device_id: str, **fields: Any) -> InventoryDevice:
        device = InventoryDevice.create(fields.pop("driver_id", NMOS))
        device.configuration.id = device_id
        device.configuration.config.desc.label = fields.pop("label", device_id)
        device.configuration.config.cinfo.address = fields.pop("address", "192.0.2.1")
        for name, value in fields.pop("custom", {}).items():
            setattr(device.configuration.config.customSettings, name, value)
        assert not fields, fields
        self.devices[device_id] = device
        return device

    def get_device(self, device_id: str, config_only: bool = False) -> InventoryDevice:
        if device_id not in self.devices:
            raise ValueError(f"No device with id '{device_id}' found in Inventory.")
        return self.devices[device_id].model_copy(deep=True)

    def add_device(self, device: InventoryDevice, label_check: bool, address_check: bool, config_only: bool) -> Any:
        assert not label_check and not address_check and config_only
        self._maybe_fail()
        device_id = f"device{self._next_id}"
        self._next_id += 1
        stored = device.model_copy(deep=True)
        stored.configuration.id = device_id
        self.devices[device_id] = stored
        self.writes.append(("add", device_id))
        return stored.model_copy(deep=True)

    def update_device(self, device: InventoryDevice, compare_config: bool, config_only: bool) -> Any:
        assert compare_config is False and config_only
        self._maybe_fail()
        self.devices[device.device_id] = device.model_copy(deep=True)
        self.writes.append(("update", device.device_id))
        return device.model_copy(deep=True)

    def find_device_id_by_label(self, label: str, label_search_mode: str) -> Any:
        ids = [i for i, d in self.devices.items() if d.configuration.config.desc.label == label]
        return None if not ids else ids[0] if len(ids) == 1 else ids

    def get_global_snmp_config_id_by_label(self, label: str) -> Any:
        ids = [i for i, lbl in self.snmp.items() if lbl == label]
        return None if not ids else ids[0] if len(ids) == 1 else ids

    def get_global_snmp_config_label_by_id(self, snmp_config_id: str) -> str | None:
        return self.snmp.get(snmp_config_id)

    def find_device_ids_by_addresses(self, addresses: Any) -> dict[str, list[str]]:
        self.address_lookups += 1
        if self.fail_address_read:
            raise ValueError("Response data is empty.")
        result: dict[str, list[str]] = {}
        for address in addresses:
            wanted = normalize_address(address)
            result[address] = sorted(
                i
                for i, device in self.devices.items()
                if any(
                    normalize_address(known) == wanted
                    for known in [
                        device.configuration.config.cinfo.address,
                        *device.configuration.config.cinfo.altAddresses,
                    ]
                    if known
                )
            )
        return result

    def _maybe_fail(self) -> None:
        if self.fail_next_write is not None:
            error, self.fail_next_write = self.fail_next_write, None
            raise error


# --- Inspect ---


class FakeInspectServer:
    """In-memory Inspect API (only the endpoints the engine and transactions use)."""

    def __init__(self) -> None:
        self.nodes: dict[str, dict[str, Any]] = {}
        self.device_forms: dict[str, dict[str, Any]] = {}
        self.vertex_forms: dict[str, dict[str, Any]] = {}
        self.sync: dict[str, dict[str, Any]] = {}
        self.discoverable: dict[str, dict[str, Any]] = {}
        self.calls: list[str] = []
        self.writes: list[tuple[str, Any]] = []
        self.fail_commit: Exception | None = None
        self.fail_tag: str | None = None
        self.fail_sync_info: Exception | None = None
        self.fail_sync = False

    # Setup

    def install(self, layout: dict[str, Any]) -> None:
        self.nodes[layout["device_id"]] = copy.deepcopy(layout["node"])
        self.device_forms[layout["device_id"]] = copy.deepcopy(layout["device_form"])
        self.vertex_forms.update(copy.deepcopy(layout["vertex_forms"]))

    # Reads

    def get_device_detail(self, device_id: str) -> InspectApiNodeStatusItem | None:
        self.calls.append(f"detail:{device_id}")
        node = self.nodes.get(device_id)
        return InspectApiNodeStatusItem.model_validate(copy.deepcopy(node)) if node is not None else None

    def lookup_inspect_device(self, device_id: str) -> InspectApiLookupInspectDeviceResponse:
        self.calls.append(f"lookup_device:{device_id}")
        if device_id not in self.device_forms:
            raise ValueError(f"unknown device {device_id}")
        data = {"assignedTags": {}, "fields": copy.deepcopy(self.device_forms[device_id])}
        return InspectApiLookupInspectDeviceResponse.model_validate({"data": data, "header": HEADER})

    def lookup_vertices(self, vertex_ids: list[str]) -> InspectApiLookupVerticesResponse:
        self.calls.append(f"lookup_vertices:{len(vertex_ids)}")
        data = {vid: copy.deepcopy(self.vertex_forms[vid]) for vid in vertex_ids if vid in self.vertex_forms}
        return InspectApiLookupVerticesResponse.model_validate({"data": data, "header": HEADER})

    def lookup_sync_info(self, device_ids: list[str]) -> InspectApiLookupSyncInfoResponse:
        self.calls.append("sync_info")
        if self.fail_sync_info is not None:
            error, self.fail_sync_info = self.fail_sync_info, None
            raise error
        data = {d: {"label": d, **self.sync[d]} for d in device_ids if d in self.sync}
        return InspectApiLookupSyncInfoResponse.model_validate({"data": data, "header": HEADER})

    def get_device_skeleton(self) -> list[InspectApiNodeStatusItem]:
        return [InspectApiNodeStatusItem.model_validate({"_id": d}) for d in self.nodes]

    def get_edge_skeleton(self) -> list[Any]:
        return []

    # Writes

    def update_topology(self, delta: Any) -> InspectApiUpdateTopologyResponse:
        self.writes.append(("update_topology", delta.model_dump(mode="json")))
        if self.fail_commit is not None:
            error, self.fail_commit = self.fail_commit, None
            raise error
        for device_id, form in delta.replaceDevices.items():
            self.device_forms[device_id] = form.model_dump(mode="json")
        for vertex_id, form in delta.replaceVertices.items():
            self.vertex_forms[vertex_id]["fields"] = form.model_dump(mode="json")
        result = {"msg": [], "ok": True}
        data = {"items": [], "res": result, "validation": {"createIds": [], "details": {}, "result": result}}
        return InspectApiUpdateTopologyResponse.model_validate({"data": data, "header": HEADER})

    def assign_tag(self, tag_id: str, element_ids: list[str]) -> InspectApiSimpleActionResponse:
        return self._tag("assign", tag_id, element_ids)

    def unassign_tag(self, tag_id: str, element_ids: list[str]) -> InspectApiSimpleActionResponse:
        return self._tag("unassign", tag_id, element_ids)

    def add_devices(self, items: list[Any]) -> InspectApiSimpleActionResponse:
        for item in items:
            self.writes.append(("add_devices", item.id))
            pending = self.discoverable.get(item.id)
            if pending is None:
                return _action(False, ["device not discovered"])
            self.nodes[item.id] = {"_id": item.id, "modules": {}}
            self.device_forms[item.id] = copy.deepcopy(pending["device_form"])
            self.sync[item.id] = {"add": {"modules": 1}, "update": {}, "remove": {}}
        return _action(True)

    def sync_devices(self, device_ids: list[str], add_only: bool = True, conflict_strategy: int = 0) -> Any:
        for device_id in device_ids:
            self.writes.append(("sync_devices", (device_id, add_only)))
            if self.fail_sync:
                return _action(False, ["sync rejected"])
            pending = self.discoverable.pop(device_id, None)
            if pending is not None:
                self.install(pending)
            self.sync.pop(device_id, None)
        return _action(True)

    def _tag(self, action: str, tag_id: str, element_ids: list[str]) -> InspectApiSimpleActionResponse:
        self.writes.append((action, (tag_id, tuple(element_ids))))
        if self.fail_tag == tag_id:
            return _action(False, ["tag rejected"])
        for element in element_ids:
            module_id = element.removeprefix("device:")
            device_id = module_id.split(".", 1)[0]
            module = self.nodes[device_id]["modules"][module_id]
            local = module.setdefault("tagsInfo", {}).setdefault("assigned", {}).setdefault("local", {})
            if action == "assign":
                local[tag_id] = {}
            else:
                local.pop(tag_id, None)
        return _action(True)


def _action(ok: bool, msg: list[str] | None = None) -> InspectApiSimpleActionResponse:
    return InspectApiSimpleActionResponse.model_validate({"data": {"ok": ok, "msg": msg or []}, "header": HEADER})


def make_inspect_app(server: FakeInspectServer) -> InspectApp:
    app = InspectApp.__new__(InspectApp)
    app._logger = logging.getLogger("test-inspect")
    app._inspect_api = server
    app._vip_connector = None
    app._load_mode = "skeleton"
    app._snapshot = None
    return app


# --- Synthetic layouts ---


def vertex_form(vertex_id: str, vertex_type: str, kind: str, **fields: Any) -> dict[str, Any]:
    type_fields: dict[str, Any] = {"type": kind}
    if kind == "codec":
        media = fields.pop("media")
        type_fields["generic"] = {"codecFormat": media.capitalize() if media else None, "multiplicity": 1}
        type_fields["specific"] = {"type": media, "sdpSupport": False, "isIgmpSource": False}
    form = {
        "active": True,
        "controlProps": {"configPriority": "off", "onlyInitial": False},
        "custom": {},
        "desc": "",
        "label": fields.pop("label", ""),
        "localAssignedTags": fields.pop("tags", []),
        "sipsMode": "NONE",
        "tags": [],
        "typeFields": type_fields,
        "useAsEndpoint": fields.pop("use_as_endpoint", False),
    }
    assert not fields, fields
    return {"id": vertex_id, "vertexType": vertex_type, "fields": form}


def build_layout(
    device_id: str, modules: dict[str, list[tuple[str, str, list[tuple[str, str, str, str | None]]]]]
) -> dict[str, Any]:
    """``modules``: module id -> [(port suffix, factory label, [(vertex suffix, type, kind, media)])]."""
    node_modules: dict[str, Any] = {}
    forms: dict[str, Any] = {}
    for module_id, ports in modules.items():
        node_ports: dict[str, Any] = {}
        for port_suffix, factory_label, vertices in ports:
            port_id = f"{module_id}.{port_suffix}"
            sides = []
            for vertex_suffix, vertex_type, kind, media in vertices:
                vertex_id = f"{device_id}.{module_id.split('.')[-1]}.{port_suffix}.{vertex_suffix}"
                sides.append(
                    {
                        "type": "single",
                        "id": vertex_id,
                        "label": factory_label,
                        "vertexType": vertex_type,
                        "fields": {"isActive": True, "isControlled": False, "isEndpoint": False},
                    }
                )
                forms[vertex_id] = vertex_form(
                    vertex_id, vertex_type, kind, **({"media": media} if kind == "codec" else {})
                )
            if len(sides) == 1:
                info: dict[str, Any] = sides[0]
            else:
                info = {"type": "double", **{("in" if s["vertexType"] == "In" else "out"): s for s in sides}}
            node_ports[port_id] = {"pid": port_id, "label": factory_label, "vertexInfo": info}
        node_modules[module_id] = {
            "pid": module_id,
            "label": f"Slot {module_id}",
            "ports": node_ports,
            "tagsInfo": {"assigned": {"all": [], "local": {}}},
        }
    return {
        "device_id": device_id,
        "node": {"_id": device_id, "fDescriptor": {"label": "factory-device", "desc": ""}, "modules": node_modules},
        "device_form": {
            "coordinates": {"x": 0, "y": 0},
            "descriptor": {"label": "", "desc": ""},
            "iconSize": "auto",
            "iconType": "default",
            "localAssignedTags": [],
            "sdpStrategy": "always",
            "siteId": None,
            "tags": [],
        },
        "vertex_forms": forms,
    }


def matrox_layout(device_id: str = "device1", mode: str = "tx", module: str | None = None) -> dict[str, Any]:
    module_id = module or f"{device_id}.dev.0"
    ip_ports = [
        ("P1", "P1", [("in", "In", "ip", None), ("out", "Out", "ip", None)]),
        ("P2", "P2", [("in", "In", "ip", None), ("out", "Out", "ip", None)]),
        ("MGMT", "MGMT", [("in", "In", "ip", None), ("out", "Out", "ip", None)]),
    ]
    if mode == "tx":
        codecs = [
            ("vs", "Video Sender", [("v", "In", "codec", "video")]),
            ("as", "Audio Sender", [("v", "In", "codec", "audio")]),
        ]
    elif mode == "rx":
        codecs = [
            ("vr", "Video Receiver", [("v", "Out", "codec", "video")]),
            ("ar", "Audio Receiver", [("v", "Out", "codec", "audio")]),
        ]
    else:
        codecs = [(f"vr{i}", f"Video Receiver {i}", [("v", "Out", "codec", "video")]) for i in range(4)]
        codecs.append(("ar", "Audio Receiver", [("v", "Out", "codec", "audio")]))
    return build_layout(device_id, {module_id: codecs + ip_ports})


# --- Fixtures ---


@pytest.fixture
def inventory() -> FakeInventory:
    return FakeInventory()


@pytest.fixture
def server() -> FakeInspectServer:
    return FakeInspectServer()


@pytest.fixture
def app(inventory: FakeInventory, server: FakeInspectServer) -> SimpleNamespace:
    return SimpleNamespace(inventory=inventory, inspect=make_inspect_app(server))


@pytest.fixture
def engine(app: SimpleNamespace) -> BlueprintEngine:
    engine = BlueprintEngine(app)
    clock = {"now": 0.0}
    engine._clock = lambda: clock["now"]
    engine._sleep = lambda seconds: clock.__setitem__("now", clock["now"] + seconds)
    return engine
