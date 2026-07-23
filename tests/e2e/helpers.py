"""Shared helpers for the developer-run live-server E2E suite ([ADR-0005]).

Everything the suite writes is namespaced (``E2E-`` label prefix + ``vipat-e2e`` tag) so a shared
local instance stays safe. Cleanup is a single session-start :func:`sweep_e2e_namespace` that
removes **every** ``E2E-`` artifact left from a prior run (devices and their edges in both the
inventory and the Inspect graph, plus ``E2E-`` profiles, security domains, multicast pools, and e2e
catalog tags). Suites leave their topologies in place — including the network-builder architectures —
for manual inspection after the run.

Devices are always virtual (mock-driver); no real hardware is involved. The build path is the real
user flow: **inventory** (create + add device) → **inspect** (add to topology graph, label + tag,
connect ports).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable, Iterator
from uuid import uuid4

import requests

if TYPE_CHECKING:
    from videoipath_automation_tool.apps.inspect.domain.device import InspectDevice
    from videoipath_automation_tool.apps.inspect.domain.edge import InspectEdge
    from videoipath_automation_tool.apps.videoipath_app import VideoIPathApp

    from .networks import Network

E2E_PREFIX = "E2E-"
E2E_TAG = "vipat-e2e"
MOCK_DRIVER = "com.nevion.mock-0.1.0"

# Catalog tags created via simple API requests for the Inspect tag tests. Tag references are
# ``Category~~name`` ids; they live in the existing "Video" format category.
TEST_TAG_CATEGORY = "Video"
TEST_TAG_NAME = "E2E-VIDEO-TAG"
TEST_TAG_ID = f"{TEST_TAG_CATEGORY}~~{TEST_TAG_NAME}"

MODULE_TEST_TAG_CATEGORY = "Video"
MODULE_TEST_TAG_NAME = "E2E-MODULE-TAG"
MODULE_TEST_TAG_ID = f"{MODULE_TEST_TAG_CATEGORY}~~{MODULE_TEST_TAG_NAME}"


def unique_label(base: str) -> str:
    """A per-test unique device label, always under the ``E2E-`` prefix so the sweep catches orphans."""
    return f"{E2E_PREFIX}T-{uuid4().hex[:6].upper()}-{base}"


def unique_name(base: str) -> str:
    """A per-test unique ``E2E-`` name for profiles / domains / pools so the sweep catches orphans."""
    return f"{E2E_PREFIX}{base}-{uuid4().hex[:6].upper()}"


# --- Device build path (inventory -> inspect) ------------------------------------------------------


def create_mock_device(app: "VideoIPathApp", *, label: str, address: str, ports: int) -> str:
    """Create a virtual (mock-driver) device in the inventory and return its device id.

    Mirrors the inventory example: create a device from a driver, set its typed ``custom_settings``,
    and add it. The mock driver exposes one router module with ``ports`` router ports.
    """
    device = app.inventory.create_device(driver=MOCK_DRIVER)
    device.configuration.label = label
    device.configuration.address = address
    settings = device.configuration.custom_settings
    settings.num_router_modules = 1
    settings.num_router_ports = ports
    settings.num_codec_modules = 0
    online = app.inventory.add_device(device=device, address_check=False)
    return online.configuration.device_id


def router_ports(device: "InspectDevice") -> list[tuple[str, str]]:
    """Ordered ``(out-vertex-id, in-vertex-id)`` pairs for a mock router device, one per port slot.

    A mock router device exposes separate "Router Out N" and "Router In N" ports; this pairs them by
    slot so a caller can wire the out side of one device to the in side of another.
    """
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
    outs.sort(key=_vertex_slot)
    ins.sort(key=_vertex_slot)
    return list(zip(outs, ins))


class PortCursor:
    """Hands out a device's router ports one slot at a time (the next free out/in vertex pair)."""

    def __init__(self, ports: list[tuple[str, str]]) -> None:
        self._ports = ports
        self._next = 0

    def next_port(self) -> tuple[str, str]:
        """Return the next unused ``(out-vertex-id, in-vertex-id)`` pair."""
        if self._next >= len(self._ports):
            raise LookupError("No free router port left on this device.")
        pair = self._ports[self._next]
        self._next += 1
        return pair


def discover_port_cursors(app: "VideoIPathApp", device_ids: Iterable[str]) -> dict[str, PortCursor]:
    """A next-free-port cursor per device: refresh the view, hydrate in one batch, read the ports."""
    ids = list(device_ids)
    app.inspect.refresh()
    app.inspect.preload(ids)
    cursors: dict[str, PortCursor] = {}
    for device_id in ids:
        device = app.inspect.get_device(device_id)
        if device is None:
            raise LookupError(f"Device '{device_id}' not found in the inspect topology.")
        cursors[device_id] = PortCursor(router_ports(device))
    return cursors


def edges_between(app: "VideoIPathApp", id_a: str, id_b: str) -> list["InspectEdge"]:
    """All directed edges between two devices (either direction)."""
    return [
        edge
        for edge in app.inspect.edges
        if edge.from_device and edge.to_device and {edge.from_device.id, edge.to_device.id} == {id_a, id_b}
    ]


class NetworkBuild:
    """Builds a :class:`Network` into a live topology step by step (the engine behind the builder suite).

    Each phase of the real user journey is one readable call, and a little state is kept between
    phases: inventory create → onboard into the Inspect topology (at ``base position + offset``) →
    label & tag → connect the links. Device labels are ``E2E-<network>-<name>`` so they are unique
    per network and caught by the session sweep.
    """

    def __init__(
        self,
        app: "VideoIPathApp",
        network: "Network",
        offset: tuple[int, int],
        addresses: Iterator[str],
    ) -> None:
        self._app = app
        self.network = network
        self._offset = offset
        self._addresses = addresses
        self.device_ids: dict[str, str] = {}  # spec name -> VideoIPath device id

    def label_of(self, name: str) -> str:
        return f"{E2E_PREFIX}{self.network.name}-{name}"

    def create_devices(self) -> None:
        for spec in self.network.devices:
            self.device_ids[spec.name] = create_mock_device(
                self._app, label=self.label_of(spec.name), address=next(self._addresses), ports=spec.ports
            )

    def add_to_topology(self) -> None:
        dx, dy = self._offset
        placements = [(self.device_ids[s.name], s.x + dx, s.y + dy) for s in self.network.devices]
        self._app.inspect.add_devices_to_topology(placements)

    def label_and_tag(self) -> None:
        with self._app.inspect.transaction() as tx:
            for spec in self.network.devices:
                tx.update_device(self.device_ids[spec.name], label=self.label_of(spec.name), tags=[E2E_TAG])
            tx.commit()

    def connect_links(self) -> None:
        cursors = discover_port_cursors(self._app, self.device_ids.values())
        with self._app.inspect.transaction() as tx:
            for link in self.network.links:
                id_a = self.device_ids[self.network.devices[link.a].name]
                id_b = self.device_ids[self.network.devices[link.b].name]
                a_out, a_in = cursors[id_a].next_port()
                b_out, b_in = cursors[id_b].next_port()
                # A physical link is two directed edges: out of A -> in of B, and out of B -> in of A.
                tx.connect(a_out, b_in, bidirectional=False)
                tx.connect(b_out, a_in, bidirectional=False)
            tx.commit()


class TopologyBuilder:
    """Per-test factory for a small mock topology; mirrors the user flow and tracks created ids.

    ``add_devices`` onboards mock devices (inventory → Inspect topology → label + e2e tag); ``link``
    connects the next free router port of two devices bidirectionally (two directed edges). Devices
    persist until the next e2e session-start sweep.

    Pass a unique ``(x, y)`` origin per test (via the session ``e2e_map_origins`` fixture) so
    builders never stack on the same map coordinates.
    """

    def __init__(self, app: "VideoIPathApp", addresses: Iterator[str], *, x: int, y: int) -> None:
        self._app = app
        self._addresses = addresses
        self.origin = (x, y)
        self._x = x
        self._y = y
        self.device_ids: list[str] = []
        self.labels: dict[str, str] = {}  # device id -> unique E2E label
        self._cursors: dict[str, PortCursor] = {}

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
        self._cursors.clear()  # ports changed; rediscover before the next link
        return created

    def link(self, id_a: str, id_b: str) -> None:
        """Connect the next free port pair of two devices bidirectionally (two directed edges)."""
        if not self._cursors:
            self._cursors = discover_port_cursors(self._app, self.device_ids)
        a_out, a_in = self._cursors[id_a].next_port()
        b_out, b_in = self._cursors[id_b].next_port()
        with self._app.inspect.transaction() as tx:
            tx.connect(a_out, b_in, bidirectional=False)
            tx.connect(b_out, a_in, bidirectional=False)
            tx.commit()


# --- Cleanup ---------------------------------------------------------------------------------------


def remove_devices(app: "VideoIPathApp", device_ids: set[str]) -> None:
    """Remove the given devices — edges first, then the topology node, then the inventory entry.

    A device lives in two places — the inventory and the Inspect topology graph — and removing it
    from one does not remove it from the other. Used by the session-start sweep; best-effort so
    cleanup errors never abort the suite.
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
    """Remove every ``E2E-`` artifact so a run starts from a clean namespace (best-effort).

    Covers devices (in both the inventory and the topology graph, catching orphans from an aborted
    run as well as an intentionally persisted build), plus ``E2E-`` profiles, security domains,
    multicast pools, and the e2e catalog tags.
    """
    delete_test_tag(app)
    delete_module_test_tag(app)

    inventory_labels = app.inventory._inventory_api.fetch_devices_user_defined_labels_as_dict()
    inventory_ids = {i for i, label in inventory_labels.items() if (label or "").startswith(E2E_PREFIX)}
    app.inspect.refresh()
    topology_ids = {d.id for d in app.inspect.devices if (d.label or "").startswith(E2E_PREFIX)}
    remove_devices(app, inventory_ids | topology_ids)

    _sweep_profiles(app)
    _sweep_domains(app)
    _sweep_multicast_pools(app)


def _sweep_profiles(app: "VideoIPathApp") -> None:
    try:
        profiles = app.profile.get_profiles() or []
        for profile in profiles:
            if (profile.name or "").startswith(E2E_PREFIX):
                app.profile.remove_profile(profile=profile)
    except Exception:  # best-effort cleanup
        pass


def _sweep_domains(app: "VideoIPathApp") -> None:
    try:
        for domain in app.security.domains.get_all_domains():
            if (domain.name or "").startswith(E2E_PREFIX):
                app.security.domains.remove_domain(domain)
    except Exception:  # best-effort cleanup
        pass


def _sweep_multicast_pools(app: "VideoIPathApp") -> None:
    try:
        pools = app.preferences.system_configuration.allocation_pools.get_multicast_ranges()
        e2e_pools = [name for name in pools.available_ranges if name.startswith(E2E_PREFIX)]
        if e2e_pools:
            app.preferences.system_configuration.allocation_pools.remove_multicast_range(e2e_pools)
    except Exception:  # best-effort cleanup
        pass


class FetchSpy:
    """Wraps ``get_device_detail`` to count per-device hydration fetches."""

    def __init__(self, api: Any) -> None:
        self._api = api
        self._orig = api.get_device_detail
        self.count = 0

    def __enter__(self) -> "FetchSpy":
        def counting(device_id: str) -> Any:
            self.count += 1
            return self._orig(device_id)

        self._api.get_device_detail = counting
        return self

    def __exit__(self, *exc: object) -> None:
        self._api.get_device_detail = self._orig


# --- Test tag catalog (simple API requests) --------------------------------------------------------


def create_catalog_tag(app: "VideoIPathApp", *, category: str, name: str) -> str:
    """Create a catalog tag under ``category`` (idempotent). Returns the ``Category~~name`` id."""
    cat = _tag_category(app, category)
    if cat is None:
        raise RuntimeError(f"Tag category '{category}' not found on the server.")
    children = dict(cat.get("children") or {})
    children[name] = {"exclusive": False, "children": {}}
    body = {
        "actions": [
            {
                "_action": "update",
                "_id": category,
                "_rev": cat["_rev"],
                "children": children,
                "type": cat.get("type", "format"),
                "exclusive": cat.get("exclusive", False),
                "formatTagLinks": cat.get("formatTagLinks", {}),
                "locationTypes": cat.get("locationTypes", []),
            }
        ]
    }
    _raw_request(app, "patch", "/rest/v2/data/config/tags/tagTrees", body)
    return f"{category}~~{name}"


def catalog_tag_exists(app: "VideoIPathApp", *, category: str, name: str) -> bool:
    cat = _tag_category(app, category)
    return cat is not None and name in (cat.get("children") or {})


def delete_catalog_tag(app: "VideoIPathApp", tag_id: str) -> None:
    """Force-delete a catalog tag (removes it and any resource bindings) if it exists."""
    category, _, name = tag_id.partition("~~")
    if not category or not name or not catalog_tag_exists(app, category=category, name=name):
        return
    _raw_request(
        app,
        "post",
        "/rest/v2/actions/status/tags/forceDeleteTag",
        {"header": {"id": 0}, "data": {"tagId": tag_id}},
    )


def create_test_tag(app: "VideoIPathApp") -> None:
    """Create the E2E port/vertex test video tag in the catalog (idempotent)."""
    create_catalog_tag(app, category=TEST_TAG_CATEGORY, name=TEST_TAG_NAME)


def delete_test_tag(app: "VideoIPathApp") -> None:
    """Force-delete the port/vertex test tag (removes it and any port bindings) if it exists."""
    delete_catalog_tag(app, TEST_TAG_ID)


def create_module_test_tag(app: "VideoIPathApp") -> None:
    """Create the E2E module test tag in the catalog (idempotent)."""
    create_catalog_tag(app, category=MODULE_TEST_TAG_CATEGORY, name=MODULE_TEST_TAG_NAME)


def delete_module_test_tag(app: "VideoIPathApp") -> None:
    """Force-delete the module test tag (removes it and any module bindings) if it exists."""
    delete_catalog_tag(app, MODULE_TEST_TAG_ID)


# --- Internal --------------------------------------------------------------------------------------


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
