"""Fixed leaf-spine scenario for the Inspect E2E suite ([ADR-0005]).

Declaratively models a small, fully-flexed leaf-spine network (two planes, red/blue), modelled on
the real local rig. Devices and their IP vertices are created through the **topology app** (vertices
cannot be created via ``updateTopology`` — [ADR-0009]); placement, connections, edits and removals
that Inspect owns are then driven through ``app.inspect``.

Every created element is namespaced so a shared instance is safe:
  * device/vertex labels start with ``E2E-``,
  * every element carries the ``vipat-e2e`` tag.

Vertex ids are **discovered** from an Inspect snapshot after creation (each vertex is created with a
unique descriptor label and looked up by ``port.label``), so the scenario does not depend on the
server's vertex-id format.

NOTE (developer-run): the exact virtual-device build calls exercise the *experimental* topology
virtual-device API; confirm labels/ids on the first live run against your instance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from videoipath_automation_tool.apps.videoipath_app import VideoIPathApp

E2E_PREFIX = "E2E-"
E2E_TAG = "vipat-e2e"

# Grid coordinates per role tier.
_Y_SPINE = 0.0
_Y_LEAF = 200.0
_Y_ENDPOINT = 400.0
_X_STEP = 300.0


@dataclass(frozen=True)
class DeviceSpec:
    label: str
    icon_type: str
    ports: tuple[str, ...]
    x: float
    y: float


@dataclass(frozen=True)
class LinkSpec:
    """A bidirectional connection between two ports (built as two directed edges)."""

    from_device: str
    from_port: str
    to_device: str
    to_port: str


def _vertex_token(device_label: str, port: str, direction: str) -> str:
    """Unique descriptor label used to discover the created vertex on the Inspect surface."""
    return f"{device_label}|{port}|{direction}"


def _build_specs() -> tuple[list[DeviceSpec], list[LinkSpec]]:
    spines = [
        DeviceSpec("E2E-SPINE-A", "ipSwitchRouter", tuple(f"downlink{i}" for i in range(4)), 0 * _X_STEP, _Y_SPINE),
        DeviceSpec("E2E-SPINE-B", "ipSwitchRouter", tuple(f"downlink{i}" for i in range(4)), 3 * _X_STEP, _Y_SPINE),
    ]
    leaf_ports = ("uplink0", "uplink1", "host0", "host1", "host2", "host3")
    leaves = [
        DeviceSpec("E2E-LEAF-A1", "ipSwitchRouter", leaf_ports, 0 * _X_STEP, _Y_LEAF),
        DeviceSpec("E2E-LEAF-A2", "ipSwitchRouter", leaf_ports, 1 * _X_STEP, _Y_LEAF),
        DeviceSpec("E2E-LEAF-B1", "ipSwitchRouter", leaf_ports, 2 * _X_STEP, _Y_LEAF),
        DeviceSpec("E2E-LEAF-B2", "ipSwitchRouter", leaf_ports, 3 * _X_STEP, _Y_LEAF),
    ]
    endpoint_ports = ("eth-a", "eth-b")
    endpoints = [
        DeviceSpec("E2E-ENC-1", "encoder", endpoint_ports, 0 * _X_STEP, _Y_ENDPOINT),
        DeviceSpec("E2E-ENC-2", "encoder", endpoint_ports, 1 * _X_STEP, _Y_ENDPOINT),
        DeviceSpec("E2E-DEC-1", "decoder", endpoint_ports, 2 * _X_STEP, _Y_ENDPOINT),
        DeviceSpec("E2E-DEC-2", "decoder", endpoint_ports, 3 * _X_STEP, _Y_ENDPOINT),
    ]

    links: list[LinkSpec] = [
        # Uplinks: each leaf's uplink0 to a downlink on its plane's spine.
        LinkSpec("E2E-LEAF-A1", "uplink0", "E2E-SPINE-A", "downlink0"),
        LinkSpec("E2E-LEAF-A2", "uplink0", "E2E-SPINE-A", "downlink1"),
        LinkSpec("E2E-LEAF-B1", "uplink0", "E2E-SPINE-B", "downlink0"),
        LinkSpec("E2E-LEAF-B2", "uplink0", "E2E-SPINE-B", "downlink1"),
        # Endpoint red-plane (eth-a) and blue-plane (eth-b) attachments.
        LinkSpec("E2E-ENC-1", "eth-a", "E2E-LEAF-A1", "host0"),
        LinkSpec("E2E-ENC-1", "eth-b", "E2E-LEAF-B1", "host0"),
        LinkSpec("E2E-ENC-2", "eth-a", "E2E-LEAF-A1", "host1"),
        LinkSpec("E2E-ENC-2", "eth-b", "E2E-LEAF-B1", "host1"),
        LinkSpec("E2E-DEC-1", "eth-a", "E2E-LEAF-A2", "host0"),
        LinkSpec("E2E-DEC-1", "eth-b", "E2E-LEAF-B2", "host0"),
        LinkSpec("E2E-DEC-2", "eth-a", "E2E-LEAF-A2", "host1"),
        LinkSpec("E2E-DEC-2", "eth-b", "E2E-LEAF-B2", "host1"),
    ]
    return [*spines, *leaves, *endpoints], links


class LeafSpineScenario:
    """Builds, inspects, and tears down the fixed leaf-spine network on a live instance."""

    def __init__(self) -> None:
        self.devices, self.links = _build_specs()
        # Resolved after build():
        self.device_ids: dict[str, str] = {}  # label -> device id
        self._vertex_ids: dict[str, str] = {}  # token -> inspect vertex id

    # --- Introspection helpers ---

    @property
    def device_labels(self) -> list[str]:
        return [d.label for d in self.devices]

    def device_id(self, label: str) -> str:
        return self.device_ids[label]

    def out_vertex(self, label: str, port: str) -> str:
        return self._vertex_ids[_vertex_token(label, port, "out")]

    def in_vertex(self, label: str, port: str) -> str:
        return self._vertex_ids[_vertex_token(label, port, "in")]

    def expected_edge_count(self) -> int:
        # Two directed edges per bidirectional link.
        return len(self.links) * 2

    # --- Build ---

    def build(self, app: "VideoIPathApp") -> None:
        for spec in self.devices:
            device_id = self._create_device(app, spec)
            self.device_ids[spec.label] = device_id
        # Place the devices on the grid (they are already graph elements after creation).
        with app.inspect.transaction() as tx:
            for spec in self.devices:
                tx.place_device(self.device_ids[spec.label], spec.x, spec.y)
            tx.commit()
        self._connect_links(app)

    def _create_device(self, app: "VideoIPathApp", spec: DeviceSpec) -> str:
        device = app.topology.create_virtual_device()
        device.configuration.base_device.label = spec.label
        device.configuration.base_device.tags = [E2E_TAG]
        device.add_virtual_module()
        for port in spec.ports:
            for direction, api_dir in (("out", "Out"), ("in", "In")):
                vertex = device.add_virtual_ip_vertex(vertex_direction=api_dir)
                vertex.label = _vertex_token(spec.label, port, direction)
                vertex.tags = [E2E_TAG]
        app.topology.add_device_initially(device)
        # add_device_initially assigns the next free virtual id onto the base device; read it
        # directly rather than looking up by label (the label index is only eventually consistent).
        device_id = device.configuration.base_device.id
        if not device_id:
            raise RuntimeError(f"Device '{spec.label}' has no id after creation.")
        # Virtual-device vertices do not surface as ports in the Inspect nodeStatus, so capture
        # their ids straight from the created graph elements (keyed by the descriptor label we set).
        for vtx in device.configuration.ip_vertices:
            self._vertex_ids[vtx.label] = vtx.id
        return device_id

    def _connect_links(self, app: "VideoIPathApp") -> None:
        with app.inspect.transaction() as tx:
            for link in self.links:
                tx.connect(
                    self.out_vertex(link.from_device, link.from_port),
                    self.in_vertex(link.to_device, link.to_port),
                    bidirectional=False,
                )
                tx.connect(
                    self.out_vertex(link.to_device, link.to_port),
                    self.in_vertex(link.from_device, link.from_port),
                    bidirectional=False,
                )
            tx.commit()

    # --- Teardown ---

    def teardown(self, app: "VideoIPathApp") -> None:
        """Remove all scenario edges then all scenario devices. Safe to call repeatedly.

        Discovers the currently-present E2E devices and their edges from a live snapshot (by the
        ``E2E-`` label prefix), so it also cleans up orphaned runs and never tries to remove an edge
        that is already gone.
        """
        app.inspect.refresh()
        # Only touch devices that currently exist (discovered by label prefix), so teardown is
        # idempotent — a second call finds nothing and is a no-op.
        known_ids = {d.id for d in app.inspect.devices if (d.label or "").startswith(E2E_PREFIX)}
        if not known_ids:
            return
        # Edges first (only the ones that actually exist).
        edge_ids = [
            edge.id
            for edge in app.inspect.edges
            if (edge.from_device and edge.from_device.id in known_ids)
            or (edge.to_device and edge.to_device.id in known_ids)
        ]
        if edge_ids:
            with app.inspect.transaction() as tx:
                for edge_id in edge_ids:
                    tx.remove(edge_id)
                tx.commit(check_conflicts=False)
        for device_id in known_ids:
            try:
                app.topology.remove_device_by_id(device_id, ignore_affected_services=True)
            except Exception:  # already gone / not an nGraphElement — best-effort cleanup
                pass

    def assert_clean(self, app: "VideoIPathApp") -> None:
        app.inspect.refresh()
        leftover = [d.label for d in app.inspect.devices if (d.label or "").startswith(E2E_PREFIX)]
        assert not leftover, f"E2E devices still present after teardown: {leftover}"
