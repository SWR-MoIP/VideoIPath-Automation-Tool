"""Topology scenario for the Inspect E2E suite ([ADR-0005]).

Replicates the structure of the local VideoIPath instance (anonymized to indices/coordinates/links
in ``leaf_spine_topology.json``) using **virtual (mock-driver) devices only**. The build path is the
real user flow:

  1. **Inventory** — create each device with the ``com.nevion.mock`` driver (a simulated device with
     configurable router ports) and ``add_device`` it. No real hardware is involved.
  2. **Inspect** — add the devices to the topology graph, set their E2E display label + tag, then
     connect their ports.

The topology app is never used.

Namespacing: every device carries the ``E2E-`` label prefix (in both inventory and inspect) and the
``vipat-e2e`` tag. Cleanup runs at **startup** (``cleanup``), not on teardown — so the built
topology persists in VideoIPath after a run for manual inspection, and the next run starts fresh.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import requests

if TYPE_CHECKING:
    from videoipath_automation_tool.apps.videoipath_app import VideoIPathApp

E2E_PREFIX = "E2E-"
E2E_TAG = "vipat-e2e"
MOCK_DRIVER = "com.nevion.mock-0.1.0"
TOPOLOGY_FILE = Path(__file__).parent / "leaf_spine_topology.json"

# A test video tag, created via a simple API request in setup and assigned to a port via the inspect
# app. Tag references are ``Category~~name`` ids; it lives in the existing "Video" format category.
TEST_TAG_CATEGORY = "Video"
TEST_TAG_NAME = "E2E-VIDEO-TAG"
TEST_TAG_ID = f"{TEST_TAG_CATEGORY}~~{TEST_TAG_NAME}"


def _raw_request(app: "VideoIPathApp", method: str, path: str, body: dict[str, Any]) -> requests.Response:
    """A minimal authenticated REST call (for tag-catalog management, which the package's connector
    allow-list intentionally does not cover)."""
    rc = app._videoipath_connector.rest
    response = getattr(requests, method)(
        rc._build_url(path), json=body, auth=(rc._username, rc._password), verify=rc.verify_ssl_cert
    )
    response.raise_for_status()
    return response


def _tag_category(app: "VideoIPathApp", category: str) -> dict[str, Any] | None:
    trees = app._videoipath_connector.rest.get("/rest/v2/data/config/tags/tagTrees/**")
    for item in trees.data["config"]["tags"]["tagTrees"].get("_items", []):
        if item.get("_id") == category:
            return item
    return None

# The fixture coordinates are captured from the live topology, so the replica would sit right on top
# of it. Shift the whole E2E topology into its own region of the map so it never overlaps.
POSITION_OFFSET_X = 0
POSITION_OFFSET_Y = 3000


@dataclass(frozen=True)
class DeviceSpec:
    name: str
    x: int
    y: int
    ports: int


@dataclass(frozen=True)
class LinkSpec:
    a: int  # device index
    b: int  # device index
    count: int  # number of parallel bidirectional links


def _vertex_slot(vertex_id: str) -> int:
    """Sort key: the trailing integer of a mock router vertex id (``device59.11.7`` -> 7)."""
    return int(vertex_id.rsplit(".", 1)[-1])


class LeafSpineScenario:
    def __init__(self) -> None:
        data = json.loads(TOPOLOGY_FILE.read_text())
        # Bake the offset into the specs so build placement and the placement-revert test agree.
        self.devices = [
            DeviceSpec(d["name"], d["x"] + POSITION_OFFSET_X, d["y"] + POSITION_OFFSET_Y, d["ports"])
            for d in data["devices"]
        ]
        self.links = [LinkSpec(a, b, n) for a, b, n in data["links"]]
        self.device_ids: dict[str, str] = {}  # E2E name -> VideoIPath device id
        self._out: dict[str, list[str]] = {}  # name -> ordered out-vertex ids
        self._in: dict[str, list[str]] = {}  # name -> ordered in-vertex ids

    # --- Introspection ---

    @property
    def device_names(self) -> list[str]:
        return [d.name for d in self.devices]

    def device_id(self, name: str) -> str:
        return self.device_ids[name]

    def adjacency(self) -> dict[str, set[str]]:
        """Undirected neighbour set per device name (from the fixture)."""
        adj: dict[str, set[str]] = {d.name: set() for d in self.devices}
        for link in self.links:
            na, nb = self.devices[link.a].name, self.devices[link.b].name
            adj[na].add(nb)
            adj[nb].add(na)
        return adj

    def expected_edge_count(self) -> int:
        # Two directed edges per bidirectional link.
        return sum(link.count for link in self.links) * 2

    def a_link(self) -> tuple[str, str]:
        """A representative connected device pair (names)."""
        link = self.links[0]
        return self.devices[link.a].name, self.devices[link.b].name

    # --- Test tag catalog (simple API requests) ---

    def create_test_tag(self, app: "VideoIPathApp") -> None:
        """Create the E2E test video tag in the catalog (idempotent)."""
        category = _tag_category(app, TEST_TAG_CATEGORY)
        if category is None:
            raise RuntimeError(f"Tag category '{TEST_TAG_CATEGORY}' not found on the server.")
        children = dict(category.get("children") or {})
        children[TEST_TAG_NAME] = {"exclusive": False, "children": {}}
        body = {
            "actions": [
                {
                    "_action": "update",
                    "_id": TEST_TAG_CATEGORY,
                    "_rev": category["_rev"],
                    "children": children,
                    "type": category.get("type", "format"),
                    "exclusive": category.get("exclusive", False),
                    "formatTagLinks": category.get("formatTagLinks", {}),
                    "locationTypes": category.get("locationTypes", []),
                }
            ]
        }
        _raw_request(app, "patch", "/rest/v2/data/config/tags/tagTrees", body)

    def test_tag_exists(self, app: "VideoIPathApp") -> bool:
        category = _tag_category(app, TEST_TAG_CATEGORY)
        return category is not None and TEST_TAG_NAME in (category.get("children") or {})

    def delete_test_tag(self, app: "VideoIPathApp") -> None:
        """Force-delete the test tag (removes it and any port bindings) if it exists."""
        if self.test_tag_exists(app):
            _raw_request(
                app,
                "post",
                "/rest/v2/actions/status/tags/forceDeleteTag",
                {"header": {"id": 0}, "data": {"tagId": TEST_TAG_ID}},
            )

    # --- Startup cleanup (removes any prior E2E state) ---

    def cleanup(self, app: "VideoIPathApp") -> None:
        """Remove every E2E device (and its edges) so a run starts from a clean namespace.

        A device lives in two places — the inventory and the inspect topology graph — and removing
        it from one does not remove it from the other. So we discover E2E devices by their ``E2E-``
        label in **both** (catching orphans from an aborted run) and remove edges, the topology node,
        and the inventory entry.
        """
        self.delete_test_tag(app)
        inventory_labels = app.inventory._inventory_api.fetch_devices_user_defined_labels_as_dict()
        inventory_ids = {i for i, label in inventory_labels.items() if (label or "").startswith(E2E_PREFIX)}
        app.inspect.refresh()
        topology_ids = {d.id for d in app.inspect.devices if (d.label or "").startswith(E2E_PREFIX)}
        all_ids = inventory_ids | topology_ids
        if not all_ids:
            return
        # Edges first (only those that actually exist).
        edge_ids = [
            edge.id
            for edge in app.inspect.edges
            if (edge.from_device and edge.from_device.id in all_ids)
            or (edge.to_device and edge.to_device.id in all_ids)
        ]
        if edge_ids:
            with app.inspect.transaction() as tx:
                for edge_id in edge_ids:
                    tx.remove(edge_id)
                tx.commit(check_conflicts=False)
        # Remove the topology node, then the inventory entry.
        for device_id in topology_ids:
            try:
                app.inspect.remove_device_from_topology(device_id)
            except Exception:  # best-effort cleanup
                pass
        for device_id in inventory_ids:
            try:
                app.inventory.remove_device(device_id=device_id, check_remove=False)
            except Exception:  # best-effort cleanup
                pass

    # --- Build ---

    def build(self, app: "VideoIPathApp") -> None:
        self._create_inventory_devices(app)
        # Add to the inspect topology graph at their coordinates.
        app.inspect.add_devices_to_topology([(self.device_ids[s.name], s.x, s.y) for s in self.devices])
        # Configure them in inspect: E2E display label + tag.
        with app.inspect.transaction() as tx:
            for spec in self.devices:
                tx.update_device(self.device_ids[spec.name], label=spec.name, tags=[E2E_TAG])
            tx.commit()
        self._discover_ports(app)
        self._connect(app)
        # Create the test video tag so the port-tagging test can assign it.
        self.create_test_tag(app)

    def _create_inventory_devices(self, app: "VideoIPathApp") -> None:
        for i, spec in enumerate(self.devices):
            device = app.inventory.create_device(driver=MOCK_DRIVER)
            device.configuration.label = spec.name
            device.configuration.address = f"10.99.{i // 256}.{i % 256}"
            settings = device.configuration.custom_settings
            settings.num_router_modules = 1
            settings.num_router_ports = spec.ports
            settings.num_codec_modules = 0
            online = app.inventory.add_device(device=device, address_check=False)
            self.device_ids[spec.name] = online.configuration.device_id

    def _discover_ports(self, app: "VideoIPathApp") -> None:
        app.inspect.refresh()
        app.inspect.preload(list(self.device_ids.values()))
        for spec in self.devices:
            device = app.inspect.get_device(self.device_ids[spec.name])
            outs: list[str] = []
            ins: list[str] = []
            for port in device.ports:
                label = port.label or ""
                if not port.vertex_id:
                    continue
                if "Router Out" in label:
                    outs.append(port.vertex_id)
                elif "Router In" in label:
                    ins.append(port.vertex_id)
            self._out[spec.name] = sorted(outs, key=_vertex_slot)
            self._in[spec.name] = sorted(ins, key=_vertex_slot)

    def _connect(self, app: "VideoIPathApp") -> None:
        slot: dict[str, int] = defaultdict(int)
        with app.inspect.transaction() as tx:
            for link in self.links:
                na, nb = self.devices[link.a].name, self.devices[link.b].name
                for _ in range(link.count):
                    ka, kb = slot[na], slot[nb]
                    slot[na] += 1
                    slot[nb] += 1
                    # Bidirectional link between interface ka on A and kb on B.
                    tx.connect(self._out[na][ka], self._in[nb][kb], bidirectional=False)
                    tx.connect(self._out[nb][kb], self._in[na][ka], bidirectional=False)
            tx.commit()
