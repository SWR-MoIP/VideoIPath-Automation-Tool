"""Shared helpers for the developer-run live-server E2E suite ([ADR-0005]).

Everything the suite writes is namespaced (``E2E-`` label prefix + ``vipat-e2e`` tag) so a shared
local instance stays safe. Two cleanup layers use that namespace:

* ``sweep_e2e_namespace`` — session-start sweep that removes **every** ``E2E-`` device (and its
  edges) left over from a prior run, in both the inventory and the inspect topology graph.
* ``remove_devices`` — targeted removal of exactly the devices a single test created (used by the
  per-test ``topology_builder`` teardown).

Devices are always virtual (mock-driver); no real hardware is involved. The build path is the real
user flow: **inventory** (create + add device) → **inspect** (add to topology graph, label + tag,
connect ports).
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any, Iterator
from uuid import uuid4

import requests

if TYPE_CHECKING:
    from videoipath_automation_tool.apps.inspect.domain.edge import InspectEdge
    from videoipath_automation_tool.apps.videoipath_app import VideoIPathApp

E2E_PREFIX = "E2E-"
E2E_TAG = "vipat-e2e"
MOCK_DRIVER = "com.nevion.mock-0.1.0"

# A test video tag, created via a simple API request and assigned to a port via the inspect app.
# Tag references are ``Category~~name`` ids; it lives in the existing "Video" format category.
TEST_TAG_CATEGORY = "Video"
TEST_TAG_NAME = "E2E-VIDEO-TAG"
TEST_TAG_ID = f"{TEST_TAG_CATEGORY}~~{TEST_TAG_NAME}"


def unique_label(base: str) -> str:
    """A per-test unique device label, always under the ``E2E-`` prefix so the sweep catches orphans."""
    return f"{E2E_PREFIX}T-{uuid4().hex[:6].upper()}-{base}"


def create_mock_device(app: "VideoIPathApp", *, label: str, address: str, ports: int) -> str:
    """Create a virtual (mock-driver) device in the inventory and return its device id."""
    device = app.inventory.create_device(driver=MOCK_DRIVER)
    device.configuration.label = label
    device.configuration.address = address
    settings = device.configuration.custom_settings
    settings.num_router_modules = 1
    settings.num_router_ports = ports
    settings.num_codec_modules = 0
    online = app.inventory.add_device(device=device, address_check=False)
    return online.configuration.device_id


def discover_router_vertices(app: "VideoIPathApp", device_ids: list[str]) -> dict[str, tuple[list[str], list[str]]]:
    """Per device id: the (out, in) router vertex ids, each sorted by port slot.

    Refreshes the snapshot and preloads the devices in parallel to avoid N+1 detail fetches.
    """
    app.inspect.refresh()
    app.inspect.preload(device_ids)
    vertices: dict[str, tuple[list[str], list[str]]] = {}
    for device_id in device_ids:
        device = app.inspect.get_device(device_id)
        if device is None:
            raise LookupError(f"Device '{device_id}' not found in the inspect topology.")
        outs: list[str] = []
        ins: list[str] = []
        for port in device.ports:
            label = port.label or ""
            vertex = port.vertex_out or port.vertex_in
            if vertex is None:
                continue
            if "Router Out" in label:
                outs.append(vertex.id)
            elif "Router In" in label:
                ins.append(vertex.id)
        vertices[device_id] = (sorted(outs, key=_vertex_slot), sorted(ins, key=_vertex_slot))
    return vertices


def edges_between(app: "VideoIPathApp", id_a: str, id_b: str) -> list["InspectEdge"]:
    """All directed edges between two devices (either direction)."""
    return [
        e
        for e in app.inspect.edges
        if e.from_device and e.to_device and {e.from_device.id, e.to_device.id} == {id_a, id_b}
    ]


def remove_devices(app: "VideoIPathApp", device_ids: set[str]) -> None:
    """Remove the given devices — edges first, then the topology node, then the inventory entry.

    A device lives in two places — the inventory and the inspect topology graph — and removing it
    from one does not remove it from the other. Removal is best-effort so cleanup errors never mask
    a test failure.
    """
    if not device_ids:
        return
    app.inspect.refresh()
    edge_ids = [
        edge.id
        for edge in app.inspect.edges
        if (edge.from_device and edge.from_device.id in device_ids)
        or (edge.to_device and edge.to_device.id in device_ids)
    ]
    if edge_ids:
        with app.inspect.transaction() as tx:
            for edge_id in edge_ids:
                tx.remove(edge_id)
            tx.commit(check_conflicts=False)
    topology_ids = {d.id for d in app.inspect.devices} & device_ids
    for device_id in topology_ids:
        try:
            app.inspect.remove_device_from_topology(device_id)
        except Exception:  # best-effort cleanup
            pass
    for device_id in device_ids:
        try:
            app.inventory.remove_device(device_id=device_id, check_remove=False)
        except Exception:  # best-effort cleanup
            pass


def sweep_e2e_namespace(app: "VideoIPathApp") -> None:
    """Remove every ``E2E-`` device (and the test tag) so a run starts from a clean namespace.

    Discovers devices by their ``E2E-`` label in **both** the inventory and the topology graph,
    catching orphans from an aborted run as well as the intentionally persisted workflow topology.
    """
    delete_test_tag(app)
    inventory_labels = app.inventory._inventory_api.fetch_devices_user_defined_labels_as_dict()
    inventory_ids = {i for i, label in inventory_labels.items() if (label or "").startswith(E2E_PREFIX)}
    app.inspect.refresh()
    topology_ids = {d.id for d in app.inspect.devices if (d.label or "").startswith(E2E_PREFIX)}
    remove_devices(app, inventory_ids | topology_ids)


class TopologyBuilder:
    """Builds a minimal per-test topology of mock devices and tracks their ids for teardown.

    ``add_devices`` mirrors the real user flow (inventory → topology graph → label + tag); ``link``
    connects the next free port pair of two devices bidirectionally (two directed edges).
    """

    def __init__(self, app: "VideoIPathApp", addresses: Iterator[str], *, x: int = 0, y: int = 4200) -> None:
        self._app = app
        self._addresses = addresses
        self._x = x
        self._y = y
        self.device_ids: list[str] = []
        self.labels: dict[str, str] = {}  # device id -> unique E2E label
        self._out: dict[str, list[str]] = {}  # device id -> ordered out-vertex ids
        self._in: dict[str, list[str]] = {}  # device id -> ordered in-vertex ids
        self._slot: dict[str, int] = defaultdict(int)  # device id -> next free port slot

    def add_devices(self, specs: list[tuple[str, int]]) -> list[str]:
        """Create mock devices from ``(base_label, ports)`` specs and add them to the topology graph.

        Labels are made unique per test via :func:`unique_label`; returns the new device ids.
        """
        created: list[str] = []
        for base_label, ports in specs:
            label = unique_label(base_label)
            device_id = create_mock_device(self._app, label=label, address=next(self._addresses), ports=ports)
            self.labels[device_id] = label
            created.append(device_id)
        offset = len(self.device_ids)
        self._app.inspect.add_devices_to_topology(
            [(device_id, self._x + (offset + i) * 300, self._y) for i, device_id in enumerate(created)]
        )
        with self._app.inspect.transaction() as tx:
            for device_id in created:
                tx.update_device(device_id, label=self.labels[device_id], tags=[E2E_TAG])
            tx.commit()
        self.device_ids.extend(created)
        return created

    def discover(self) -> None:
        """Discover the router port vertices of all tracked devices (needed before ``link``)."""
        for device_id, (outs, ins) in discover_router_vertices(self._app, self.device_ids).items():
            self._out[device_id] = outs
            self._in[device_id] = ins

    def link(self, id_a: str, id_b: str) -> None:
        """Connect the next free port pair of two devices bidirectionally (two directed edges)."""
        if id_a not in self._out or id_b not in self._out:
            self.discover()
        ka, kb = self._slot[id_a], self._slot[id_b]
        self._slot[id_a] += 1
        self._slot[id_b] += 1
        with self._app.inspect.transaction() as tx:
            tx.connect(self._out[id_a][ka], self._in[id_b][kb], bidirectional=False)
            tx.connect(self._out[id_b][kb], self._in[id_a][ka], bidirectional=False)
            tx.commit()


class FetchSpy:
    """Wraps get_device_detail to count hydration fetches."""

    def __init__(self, api):
        self._api = api
        self._orig = api.get_device_detail
        self.count = 0

    def __enter__(self):
        def counting(device_id):
            self.count += 1
            return self._orig(device_id)

        self._api.get_device_detail = counting
        return self

    def __exit__(self, *exc):
        self._api.get_device_detail = self._orig


# --- Test tag catalog (simple API requests) ---


def create_test_tag(app: "VideoIPathApp") -> None:
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


def test_tag_exists(app: "VideoIPathApp") -> bool:
    category = _tag_category(app, TEST_TAG_CATEGORY)
    return category is not None and TEST_TAG_NAME in (category.get("children") or {})


def delete_test_tag(app: "VideoIPathApp") -> None:
    """Force-delete the test tag (removes it and any port bindings) if it exists."""
    if test_tag_exists(app):
        _raw_request(
            app,
            "post",
            "/rest/v2/actions/status/tags/forceDeleteTag",
            {"header": {"id": 0}, "data": {"tagId": TEST_TAG_ID}},
        )


# --- Internal ---


def _vertex_slot(vertex_id: str) -> int:
    """Sort key: the trailing integer of a mock router vertex id (``device59.11.7`` -> 7)."""
    return int(vertex_id.rsplit(".", 1)[-1])


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
