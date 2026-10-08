"""Preview edges between existing devices using a reusable port mapping.

Edge facts and edge settings belong to the device instance. The blueprint
maps reusable local port names. Set VideoIPath credentials through the normal
VIPAT_* environment variables and replace the synthetic device ids/port labels.
Only planning runs by default; uncomment plan.apply() to execute the changes.
"""

from __future__ import annotations

from pathlib import Path

from videoipath_automation_tool import VideoIPathApp
from videoipath_automation_tool.provisioning import (
    DeviceTarget,
    EdgePatch,
    PeerEndpoint,
    PortSelector,
    ProvisioningDevice,
    ProvisioningEdge,
    ProvisioningEngine,
)


def main() -> None:
    engine = ProvisioningEngine(VideoIPathApp())
    device = ProvisioningDevice(
        key="device-a",
        label="device-a",
        inventory_id="device1",
        edges=[
            ProvisioningEdge(
                local="uplink",
                peer=PeerEndpoint(
                    target=DeviceTarget(device_id="device2"),
                    port=PortSelector(factory_label="port-1"),
                ),
                direction="auto",
                fields=EdgePatch(weight=10, label="edge-a"),
            ),
        ],
    )
    blueprint = Path(__file__).with_name("external-edges.yml")
    plan = engine.plan(device, blueprint, scope="topology")
    print(plan.summary())

    # result = plan.apply()
    # for edge in result.edges:
    #     print(edge.index, edge.status, edge.edge_ids, edge.reason)
    # A missing peer gives status="partial", replan_required=True. Plan again
    # when it is available. Existing unrelated edges are never removed.


if __name__ == "__main__":
    main()
