from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Iterator

from videoipath_automation_tool.apps.inspect.model.collector import (
    InspectApiCollectorResponse,
    InspectApiExternalEdgeStatus,
    InspectApiModuleStatus,
    InspectApiNodeStatusItem,
    InspectApiPathItem,
    InspectPortStatus,
)

if TYPE_CHECKING:
    from videoipath_automation_tool.apps.inspect.domain.device import InspectDevice
    from videoipath_automation_tool.apps.inspect.domain.edge import InspectEdge
    from videoipath_automation_tool.apps.inspect.domain.port import InspectPort
    from videoipath_automation_tool.apps.inspect.domain.service import InspectService


@dataclass(frozen=True, slots=True)
class _DeviceRecord:
    device_id: str
    label: str | None
    pid: str | None
    node: InspectApiNodeStatusItem | None


@dataclass(frozen=True, slots=True)
class _IndexedPort:
    device_id: str
    module_id: str | None
    port: InspectPortStatus


@dataclass(frozen=True, slots=True)
class _IndexedEdge:
    edge_id: str
    pair_id: str
    edge: InspectApiExternalEdgeStatus
    primary_device_id: str | None
    secondary_device_id: str | None
    from_device_id: str | None
    from_port_id: str | None
    to_device_id: str | None
    to_port_id: str | None


class InspectSnapshot:
    def __init__(self, response: InspectApiCollectorResponse) -> None:
        self._response = response
        collector = response.data.status.collector

        self._node_status_items = collector.inspect.node_status_items
        self._path_items = collector.inspect.path_items
        self._external_edge_items = collector.external_edges_by_device_key_items

        self._devices_by_id: dict[str, _DeviceRecord] = {}
        self._devices_by_label: dict[str, list[str]] = {}
        self._paths_by_booking_id: dict[str, InspectApiPathItem] = {}
        self._services_by_device_id: dict[str, list[str]] = {}
        self._ports_by_device_id: dict[str, list[_IndexedPort]] = {}
        self._port_by_key: dict[tuple[str, str], _IndexedPort] = {}
        self._ports_by_pid: dict[str, list[_IndexedPort]] = {}
        self._edges_by_device_id: dict[str, list[_IndexedEdge]] = {}
        self._edge_by_port_key: dict[tuple[str, str], _IndexedEdge] = {}

        self._device_cache: dict[str, InspectDevice] = {}
        self._port_cache: dict[tuple[str, str], InspectPort] = {}
        self._edge_cache: dict[str, InspectEdge] = {}
        self._service_cache: dict[str, InspectService] = {}
        self._ports_for_device_cache: dict[str, list[InspectPort]] = {}
        self._edges_for_device_cache: dict[str, list[InspectEdge]] = {}
        self._services_for_device_cache: dict[str, list[InspectService]] = {}

        self._build_device_indexes()
        self._build_path_indexes()
        self._build_port_indexes()
        self._build_edge_indexes()

    @property
    def raw_response(self) -> InspectApiCollectorResponse:
        return self._response

    @classmethod
    def from_response(cls, response: InspectApiCollectorResponse) -> InspectSnapshot:
        return cls(response)

    def get_device_by_id(self, device_id: str) -> InspectDevice | None:
        record = self._devices_by_id.get(device_id)
        if record is None:
            return None
        return self._wrap_device(record)

    def find_devices_by_name(self, label: str) -> list[InspectDevice]:
        devices: list[InspectDevice] = []
        for device_id in self._devices_by_label.get(label, []):
            device = self.get_device_by_id(device_id)
            if device is not None:
                devices.append(device)
        return devices

    def get_devices(self) -> list[InspectDevice]:
        return [self._wrap_device(record) for record in self._devices_by_id.values()]

    def get_service_by_booking_id(self, booking_id: str) -> InspectService | None:
        path_item = self._paths_by_booking_id.get(booking_id)
        if path_item is None:
            return None
        return self._wrap_service(path_item)

    def get_services(self) -> list[InspectService]:
        return [self._wrap_service(item) for item in self._path_items]

    def get_port(self, device_id: str, port_id: str) -> InspectPort | None:
        indexed = self._port_by_key.get((device_id, port_id))
        if indexed is None:
            return None
        return self._wrap_port(indexed)

    def find_port_by_id(self, port_id: str) -> InspectPort | None:
        indexed_ports = self._ports_by_pid.get(port_id)
        if not indexed_ports:
            return None
        return self._wrap_port(indexed_ports[0])

    def get_ports_for_device(self, device_id: str) -> list[InspectPort]:
        cached = self._ports_for_device_cache.get(device_id)
        if cached is not None:
            return cached
        ports = [self._wrap_port(indexed) for indexed in self._ports_by_device_id.get(device_id, [])]
        self._ports_for_device_cache[device_id] = ports
        return ports

    def get_edge_for_port(self, device_id: str, port_id: str) -> InspectEdge | None:
        indexed = self._edge_by_port_key.get((device_id, port_id))
        if indexed is None:
            return None
        return self._wrap_edge(indexed)

    def get_edges(self) -> list[InspectEdge]:
        seen: set[str] = set()
        edges: list[InspectEdge] = []
        for indexed_edges in self._edges_by_device_id.values():
            for indexed in indexed_edges:
                if indexed.edge_id in seen:
                    continue
                seen.add(indexed.edge_id)
                edges.append(self._wrap_edge(indexed))
        return edges

    def get_edges_for_device(self, device_id: str) -> list[InspectEdge]:
        cached = self._edges_for_device_cache.get(device_id)
        if cached is not None:
            return cached
        seen: set[str] = set()
        edges: list[InspectEdge] = []
        for indexed in self._edges_by_device_id.get(device_id, []):
            if indexed.edge_id in seen:
                continue
            seen.add(indexed.edge_id)
            edges.append(self._wrap_edge(indexed))
        self._edges_for_device_cache[device_id] = edges
        return edges

    def get_services_for_device(self, device_id: str) -> list[InspectService]:
        cached = self._services_for_device_cache.get(device_id)
        if cached is not None:
            return cached
        services: list[InspectService] = []
        for booking_id in self._services_by_device_id.get(device_id, []):
            service = self.get_service_by_booking_id(booking_id)
            if service is not None:
                services.append(service)
        self._services_for_device_cache[device_id] = services
        return services

    def get_linked_devices(self, device_id: str) -> list[InspectDevice]:
        linked: set[str] = set()
        for indexed in self._edges_by_device_id.get(device_id, []):
            for candidate in (indexed.from_device_id, indexed.to_device_id):
                if candidate and candidate != device_id:
                    linked.add(candidate)
        for booking_id in self._services_by_device_id.get(device_id, []):
            path_item = self._paths_by_booking_id.get(booking_id)
            if path_item is None:
                continue
            for segment in path_item.path:
                structure = segment.structure
                if structure and structure.deviceId and structure.deviceId != device_id:
                    linked.add(structure.deviceId)
        return [device for linked_id in sorted(linked) if (device := self.get_device_by_id(linked_id)) is not None]

    def _wrap_device(self, record: _DeviceRecord) -> InspectDevice:
        from videoipath_automation_tool.apps.inspect.domain.device import InspectDevice

        cached = self._device_cache.get(record.device_id)
        if cached is not None:
            return cached
        device = InspectDevice(snapshot=self, record=record)
        self._device_cache[record.device_id] = device
        return device

    def _wrap_port(self, indexed: _IndexedPort) -> InspectPort:
        from videoipath_automation_tool.apps.inspect.domain.port import InspectPort

        port_id = _port_id_from_status(indexed.port)
        if port_id is not None:
            key = (indexed.device_id, port_id)
            cached = self._port_cache.get(key)
            if cached is not None:
                return cached
            port = InspectPort(snapshot=self, indexed=indexed)
            self._port_cache[key] = port
            return port
        return InspectPort(snapshot=self, indexed=indexed)

    def _wrap_edge(self, indexed: _IndexedEdge) -> InspectEdge:
        from videoipath_automation_tool.apps.inspect.domain.edge import InspectEdge

        cached = self._edge_cache.get(indexed.edge_id)
        if cached is not None:
            return cached
        edge = InspectEdge(snapshot=self, indexed=indexed)
        self._edge_cache[indexed.edge_id] = edge
        return edge

    def _wrap_service(self, path_item: InspectApiPathItem) -> InspectService:
        from videoipath_automation_tool.apps.inspect.domain.service import InspectService

        booking_id = path_item.serviceFields.bid
        cached = self._service_cache.get(booking_id)
        if cached is not None:
            return cached
        service = InspectService(snapshot=self, path_item=path_item)
        self._service_cache[booking_id] = service
        return service

    def _build_device_indexes(self) -> None:
        for node in self._node_status_items:
            device_id = node.deviceId or node.pid or node.id
            if not device_id:
                continue
            self._upsert_device_record(
                _DeviceRecord(
                    device_id=device_id,
                    label=node.label,
                    pid=node.pid,
                    node=node,
                )
            )

        for path_item in self._path_items:
            for segment in path_item.path:
                structure = segment.structure
                if structure is None or not structure.deviceId:
                    continue
                existing = self._devices_by_id.get(structure.deviceId)
                if existing is not None and existing.node is not None:
                    continue
                self._upsert_device_record(
                    _DeviceRecord(
                        device_id=structure.deviceId,
                        label=structure.deviceLabel,
                        pid=structure.devicePid,
                        node=existing.node if existing else None,
                    )
                )

    def _upsert_device_record(self, record: _DeviceRecord) -> None:
        existing = self._devices_by_id.get(record.device_id)
        if existing is not None and existing.node is not None and record.node is None:
            merged = existing
        elif existing is not None and record.node is not None:
            merged = _DeviceRecord(
                device_id=record.device_id,
                label=record.label or existing.label,
                pid=record.pid or existing.pid,
                node=record.node,
            )
        else:
            merged = record

        self._devices_by_id[merged.device_id] = merged
        if merged.label:
            labels = self._devices_by_label.setdefault(merged.label, [])
            if merged.device_id not in labels:
                labels.append(merged.device_id)

    def _build_path_indexes(self) -> None:
        for path_item in self._path_items:
            booking_id = path_item.serviceFields.bid
            self._paths_by_booking_id[booking_id] = path_item
            device_ids: set[str] = set()
            for segment in path_item.path:
                structure = segment.structure
                if structure and structure.deviceId:
                    device_ids.add(structure.deviceId)
            for device_id in device_ids:
                booking_ids = self._services_by_device_id.setdefault(device_id, [])
                if booking_id not in booking_ids:
                    booking_ids.append(booking_id)

    def _build_port_indexes(self) -> None:
        for node in self._node_status_items:
            device_id = node.deviceId or node.pid or node.id
            if not device_id:
                continue
            for module in _iter_modules(node.modules):
                module_id = module.pid or module.id
                for port in _iter_ports(module.ports):
                    indexed = _IndexedPort(device_id=device_id, module_id=module_id, port=port)
                    self._ports_by_device_id.setdefault(device_id, []).append(indexed)
                    port_id = _port_id_from_status(port)
                    if port_id is None:
                        continue
                    key = (device_id, port_id)
                    self._port_by_key[key] = indexed
                    self._ports_by_pid.setdefault(port_id, []).append(indexed)

    def _build_edge_indexes(self) -> None:
        for pair_item in self._external_edge_items:
            primary_device_id = pair_item.primary.devicePid
            secondary_device_id = pair_item.secondary.devicePid
            for side, device_id in (
                (pair_item.primary, primary_device_id),
                (pair_item.secondary, secondary_device_id),
            ):
                if not device_id:
                    continue
                for edge in side.data.values():
                    from_device_id = (
                        _device_id_from_context(edge.fromStatus.context if edge.fromStatus else None)
                        or primary_device_id
                    )
                    from_port_id = _port_id_from_endpoint(edge.fromStatus)
                    to_device_id = (
                        _device_id_from_context(edge.toStatus.context if edge.toStatus else None)
                        or secondary_device_id
                    )
                    to_port_id = _port_id_from_endpoint(edge.toStatus)
                    indexed = _IndexedEdge(
                        edge_id=edge.id,
                        pair_id=pair_item.id,
                        edge=edge,
                        primary_device_id=primary_device_id,
                        secondary_device_id=secondary_device_id,
                        from_device_id=from_device_id,
                        from_port_id=from_port_id,
                        to_device_id=to_device_id,
                        to_port_id=to_port_id,
                    )
                    self._edges_by_device_id.setdefault(device_id, []).append(indexed)
                    for endpoint_device_id, port_id in (
                        (from_device_id, from_port_id),
                        (to_device_id, to_port_id),
                    ):
                        if endpoint_device_id and port_id:
                            self._edge_by_port_key[(endpoint_device_id, port_id)] = indexed


def _device_id_from_context(context: Any) -> str | None:
    if context is None:
        return None
    device_pid = getattr(context, "devicePid", None)
    if device_pid:
        return device_pid
    if isinstance(context, dict):
        value = context.get("devicePid")
        return value if isinstance(value, str) else None
    return None


def _port_id_from_endpoint(endpoint: Any) -> str | None:
    if endpoint is None:
        return None
    pid = getattr(endpoint, "pid", None)
    if isinstance(pid, str) and pid:
        return pid
    context = getattr(endpoint, "context", None)
    if context is not None:
        if isinstance(context, dict):
            port_pid = context.get("portPid")
        else:
            port_pid = getattr(context, "portPid", None)
        if isinstance(port_pid, str) and port_pid:
            return port_pid
    return None


def _port_id_from_status(port: InspectPortStatus) -> str | None:
    port_id = port.pid or port.id
    return port_id if port_id else None


def _iter_modules(modules: dict[str, InspectApiModuleStatus] | list[InspectApiModuleStatus]) -> Iterator[InspectApiModuleStatus]:
    if isinstance(modules, dict):
        yield from modules.values()
        return
    yield from modules


def _iter_ports(ports: dict[str, InspectPortStatus] | list[InspectPortStatus]) -> Iterator[InspectPortStatus]:
    if isinstance(ports, dict):
        yield from ports.values()
        return
    yield from ports
