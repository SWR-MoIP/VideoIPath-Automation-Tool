"""Onboard and configure a device from a blueprint.

Description
-----------
Loads ``matrox-convertip.yml``, describes one device with neutral instance facts, previews the plan,
and applies it (as a dry run by default). On the first run the Inventory record is created and the topology work is deferred
until the driver has discovered the device; later runs bind the stored Inventory id and are no-ops
when nothing changed. A partial failure still reports the created id so a retry never creates a
duplicate.

Prerequisites
-------------
- A reachable VideoIPath server (VideoIPath >= 2025.4) with Inventory and topology write access.

Related examples
----------------
- 02_custom_processor_and_naming.py
- 06_workflows/01_full_onboarding_pipeline.py
"""

from __future__ import annotations

from pathlib import Path

from videoipath_automation_tool import VideoIPathApp
from videoipath_automation_tool.blueprints import (
    ApplyOptions,
    BlueprintApplyError,
    BlueprintDevice,
    BlueprintEngine,
    Credentials,
)

SERVER_ADDRESS = "<your-videoipath-ip-or-domain>"
USERNAME = "<your-videoipath-api-user>"
PASSWORD = "<your-videoipath-api-password>"

BLUEPRINT = Path(__file__).with_name("matrox-convertip.yml")
DRY_RUN = True  # set to False to write to the server
STORED_INVENTORY_ID: str | None = None  # e.g. "device12" once known (persist it in your source system)


def main() -> None:
    # --- 1. Connect and build the engine ---------------------------------------
    app = VideoIPathApp(server_address=SERVER_ADDRESS, username=USERNAME, password=PASSWORD, use_https=False)
    engine = BlueprintEngine(app, options=ApplyOptions(sync="add_only", discovery_timeout=60))

    # --- 2. Describe the device with neutral facts -----------------------------
    device = BlueprintDevice(
        key="device-a",
        label="device-a",
        description="studio-a",
        inventory_id=STORED_INVENTORY_ID,
        management_address="192.0.2.10",
        credentials=Credentials(username="test-user", password="test-password"),
    )

    # --- 3. Load the blueprint internally and preview --------------------------
    plan = engine.plan(device, BLUEPRINT, topology_variant="receiver")
    print(plan.summary())
    if not plan.has_changes:
        return

    # --- 4. Apply and handle partial outcomes ----------------------------------
    try:
        result = plan.apply(dry_run=DRY_RUN)  # a dry run checks everything but writes nothing
    except BlueprintApplyError as error:
        result = error.result
        print(f"Apply {result.status}; known Inventory id: {result.inventory_id}")
        for phase in result.phases:
            print(f"  {phase.name}: {phase.status} {phase.message or ''}")
        raise
    print(f"{result.status}: inventory={result.inventory_id} verification={result.verification}")
    for binding in result.interface_bindings:
        print(f"  {binding.key} -> {binding.port_id}")


if __name__ == "__main__":
    main()
