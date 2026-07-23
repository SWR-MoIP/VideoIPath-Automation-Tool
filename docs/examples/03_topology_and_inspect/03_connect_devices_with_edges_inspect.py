"""Connect two devices with edges (Inspect app).

Description
-----------
A physical link between two devices is modeled as a pair of directed edges (one per direction) between
an out-vertex on one device and an in-vertex on the other. This example connects ``leaf-1`` to
``spine-1`` bidirectionally, then tunes the resulting edge's routing weight. The paired
``03_connect_devices_with_edges_topology.py`` does the same with the Topology app.

Edge creation has no property-setter form, so ``connect`` is used directly; editing an existing edge
uses the recommended setter + ``app.inspect.update(edge)`` style.

Prerequisites
-------------
- A reachable VideoIPath server, VideoIPath >= 2025.4.
- Devices ``leaf-1`` and ``spine-1`` in the topology with synced ports.

Related examples
----------------
- 03_topology_and_inspect/03_connect_devices_with_edges_topology.py
- 04_inspect/02_transactions_and_conflicts.py
"""

from __future__ import annotations

from videoipath_automation_tool import VideoIPathApp
from videoipath_automation_tool.apps.inspect import InspectDevice
from videoipath_automation_tool.apps.inspect.domain import InspectVertex

SERVER_ADDRESS = "<your-videoipath-ip-or-domain>"
USERNAME = "<your-videoipath-api-user>"
PASSWORD = "<your-videoipath-api-password>"


def first_free_port_vertices(device: InspectDevice) -> tuple[InspectVertex, InspectVertex]:
    """Return the (out, in) vertices of the device's first usable port."""
    for port in device.ports:
        if port.vertex_out is not None and port.vertex_in is not None:
            return port.vertex_out, port.vertex_in
    raise LookupError(f"No connectable port found on {device.label}.")


def main() -> None:
    # --- 1. Connect -----------------------------------------------------------
    app = VideoIPathApp(server_address=SERVER_ADDRESS, username=USERNAME, password=PASSWORD, use_https=False)

    leaf = app.inspect.find_device_by_label("leaf-1")
    spine = app.inspect.find_device_by_label("spine-1")
    assert leaf is not None and spine is not None

    leaf_out, leaf_in = first_free_port_vertices(leaf)
    spine_out, spine_in = first_free_port_vertices(spine)

    # --- 2. Create the bidirectional link -------------------------------------
    # bidirectional=True also stages the reverse edge. Extra edge fields (bandwidth, weight,
    # redundancy) are passed straight through. Bandwidth here reserves 10% headroom (90% of 10G).
    app.inspect.connect(
        leaf_out.id,
        spine_in.id,
        bidirectional=True,
        bandwidth=int(10_000 * 0.9),
        redundancy_mode="OnlyMain",
    )
    print(f"Connected {leaf.label} <-> {spine.label}")
    # > Connected leaf-1 <-> spine-1

    # --- 3. Verify connectivity -----------------------------------------------
    neighbours = {d.label for d in leaf.linked_devices}
    print("leaf-1 neighbours:", neighbours)
    # > leaf-1 neighbours: {'spine-1'}

    # --- 4. Tune an existing edge via setter (recommended) --------------------
    edge = next((e for e in leaf.edges if e.to_device and e.to_device.label == "spine-1"), None)
    if edge is not None:
        edge.weight = 7
        app.inspect.update(edge)
        print("Set edge weight to", edge.weight)
        # > Set edge weight to 7

    # --- 5. Remove the link ----------------------------------------------------
    # app.inspect.disconnect(leaf_out.id, spine_in.id, bidirectional=True)


if __name__ == "__main__":
    main()
