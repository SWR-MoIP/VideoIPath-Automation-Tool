"""Register a custom vertex processor and use a custom naming convention.

Description
-----------
Defines a tiny processor for a single-sender device, registers it on one engine, and previews a
topology-only blueprint (written as a dictionary) for an existing Inspect device. The endpoint label
convention (``<device>-E<engine>P<program>-<direction><media code>-<index>``) is a ``NamingScheme``,
so it can change without touching the processor. Also shows a module-scoped call. Uncomment the apply
section after reviewing the changes to write them to the server.

Prerequisites
-------------
- A reachable VideoIPath server (VideoIPath >= 2025.4) with topology write access.
- An Inspect device whose codec sender port is labelled ``Video Sender``.

Related examples
----------------
- 01_onboard_with_blueprint.py
- 03_topology_and_inspect/02_configure_vertices_inspect.py
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from videoipath_automation_tool import VideoIPathApp
from videoipath_automation_tool.provisioning import (
    Blueprint,
    DeviceTarget,
    EndpointIdentity,
    Field,
    Join,
    ModuleTarget,
    NamingScheme,
    ProcessingContext,
    ProcessorResult,
    ProvisioningDevice,
    ProvisioningEngine,
    VertexEdit,
    VertexPatch,
    VertexProcessor,
)

SERVER_ADDRESS = "<your-videoipath-ip-or-domain>"
USERNAME = "<your-videoipath-api-user>"
PASSWORD = "<your-videoipath-api-password>"

DEVICE_ID = "device12"  # existing Inspect device
MODULE_ID: str | None = None  # e.g. "device12.dev.1" to configure one module only


class SimpleParams(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    factory_label: str


class SimpleVideoProcessor(VertexProcessor[SimpleParams]):
    params_model = SimpleParams

    def process(self, context: ProcessingContext, params: SimpleParams) -> ProcessorResult:
        vertex = context.require_vertex(kind="codec", factory_label=params.factory_label, vertex_type="In")
        return ProcessorResult(
            vertices=[
                VertexEdit(
                    vertex_id=vertex.id,
                    fields=VertexPatch(use_as_endpoint=True, description=params.factory_label),
                    endpoint=EndpointIdentity(direction="TX", media="video", index=1, engine=0, program=1),
                )
            ]
        )


NAMING = NamingScheme(
    endpoint_label=Join(
        parts=[
            Field("device.label"),
            "E{endpoint.engine}P{endpoint.program}",
            Join(parts=[Field("endpoint.direction"), Field("endpoint.media", mapping={"video": "20", "audio": "30"})]),
            Field("endpoint.index", format="02d"),
        ],
        separator="-",
    )
)

BLUEPRINT = {
    "schema_version": 1,
    "defaults": {
        "topology": {
            "vertex_processor": {
                "processor_type": "example-org.simple-video",
                "params": {"factory_label": "Video Sender"},
            }
        }
    },
}


def main() -> None:
    app = VideoIPathApp(server_address=SERVER_ADDRESS, username=USERNAME, password=PASSWORD, use_https=False)
    engine = ProvisioningEngine(app, processors={"example-org.simple-video": SimpleVideoProcessor}, naming=NAMING)

    target = ModuleTarget(device_id=DEVICE_ID, module_id=MODULE_ID) if MODULE_ID else DeviceTarget(device_id=DEVICE_ID)
    device = ProvisioningDevice(
        key="device-a", label="device-a", topology=target, module_position="1" if MODULE_ID else None
    )

    plan = engine.plan(device, Blueprint.from_dict(BLUEPRINT), scope="topology")
    print(plan.summary())  # e.g. label: '' -> 'device-a-E0P1-TX20-01'

    # Uncomment the following block to execute the reviewed plan.
    # if plan.has_changes:
    #     print(plan.apply().status)


if __name__ == "__main__":
    main()
