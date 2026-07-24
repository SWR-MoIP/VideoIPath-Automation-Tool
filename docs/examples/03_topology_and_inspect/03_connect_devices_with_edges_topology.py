"""Connect two devices with edges (Topology app).

Description
-----------
A physical link between two devices is modeled as directed edges between their vertices. This example
connects ``leaf-1`` to ``spine-1`` using ``create_edges`` (which resolves the correct vertex pairing
from factory labels), attaches the edges to the device, and pushes it. The paired
``03_connect_devices_with_edges_inspect.py`` does the same with the Inspect app.

Prerequisites
-------------
- A reachable VideoIPath server; devices ``leaf-1`` and ``spine-1`` in the topology.
- NOTE: the Topology app is deprecated on VideoIPath 2025.x and unsupported on 2026.x (its
  constructor raises ``TopologyUnsupportedError``). On modern servers prefer the paired
  ``03_connect_devices_with_edges_inspect.py``.

Related examples
----------------
- 03_topology_and_inspect/03_connect_devices_with_edges_inspect.py
"""

from __future__ import annotations

from videoipath_automation_tool import VideoIPathApp

SERVER_ADDRESS = "<your-videoipath-ip-or-domain>"
USERNAME = "<your-videoipath-api-user>"
PASSWORD = "<your-videoipath-api-password>"


def main() -> None:
    # --- 1. Connect -----------------------------------------------------------
    app = VideoIPathApp(server_address=SERVER_ADDRESS, username=USERNAME, password=PASSWORD, use_https=False)

    leaf_id = app.topology.find_device_id_by_label("leaf-1", label_search_mode="user_defined_label_only")
    spine_id = app.topology.find_device_id_by_label("spine-1", label_search_mode="user_defined_label_only")
    assert isinstance(leaf_id, str) and isinstance(spine_id, str)

    # --- 2. Build the directed edges between two ports ------------------------
    # create_edges pairs the out/in vertices behind the given factory labels. `bandwidth_factor`
    # reserves headroom (0.9 -> use 90% of the nominal bandwidth); redundancy_mode tags the link.
    edges = app.topology.create_edges(
        device_1_id=leaf_id,
        device_1_vertex_factory_label="port-out-1",
        device_2_id=spine_id,
        device_2_vertex_factory_label="port-in-1",
        bandwidth=10000,
        bandwidth_factor=0.9,
        redundancy_mode="OnlyMain",
    )

    # --- 3. Attach the edges to the device and push ---------------------------
    leaf = app.topology.get_device(device_id=leaf_id)
    leaf.configuration.external_edges.extend(edges)
    app.topology.update_device(device=leaf)
    print(f"Connected leaf-1 <-> spine-1 with {len(edges)} directed edge(s).")
    # > Connected leaf-1 <-> spine-1 with 2 directed edge(s).

    # --- 4. Tune an existing edge ---------------------------------------------
    edge = edges[0]
    edge.weight = 7
    app.topology.update_element(edge)
    print("Set edge weight to", edge.weight)
    # > Set edge weight to 7


if __name__ == "__main__":
    main()
