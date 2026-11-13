"""Onboard and configure a device from a blueprint.

Description
-----------
Loads ``matrox-convertip.yml``, describes one device with neutral instance facts, and previews the plan
without writing. Uncomment the apply section after reviewing the changes. On the first apply the
Inventory record is created and topology work waits until the driver has discovered the device;
later runs bind the stored Inventory id and are no-ops when nothing changed. A partial failure still
reports the created id so a retry never creates a duplicate.

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
from videoipath_automation_tool.provisioning import (
    ApplyOptions,
    Credentials,
    ProvisioningDevice,
    ProvisioningEngine,
)

SERVER_ADDRESS = "<your-videoipath-ip-or-domain>"
USERNAME = "<your-videoipath-api-user>"
PASSWORD = "<your-videoipath-api-password>"

BLUEPRINT = Path(__file__).with_name("matrox-convertip.yml")
STORED_INVENTORY_ID: str | None = None  # e.g. "device12" once known (persist it in your source system)


def main() -> None:
    # --- 1. Connect and build the engine ---------------------------------------
    app = VideoIPathApp(server_address=SERVER_ADDRESS, username=USERNAME, password=PASSWORD, use_https=False)
    engine = ProvisioningEngine(
        app,
        options=ApplyOptions(sync="add_only", inventory_ready_timeout=10, topology_ready_timeout=60),
    )
    # For mock/static devices only: set require_reachable=False to skip the Inventory gate.

    # --- 2. Describe the device with neutral facts -----------------------------
    device = ProvisioningDevice(
        key="device-a",
        label="device-a",
        description="studio-a",
        inventory_id=STORED_INVENTORY_ID,
        management_address="192.0.2.10",
        credentials=Credentials(username="test-user", password="test-password"),
    )

    # --- 3. Load the blueprint internally and preview --------------------------
    plan = engine.plan(device, BLUEPRINT, variants=["receiver"])
    print(plan.summary())

    # --- 4. Apply and handle partial outcomes ----------------------------------
    # Uncomment the following block to execute the reviewed plan.
    # from videoipath_automation_tool.provisioning import ProvisioningApplyError
    #
    # if not plan.has_changes:
    #     return
    # try:
    #     result = plan.apply()
    # except ProvisioningApplyError as error:
    #     result = error.result
    #     print(f"Apply {result.status}; known Inventory id: {result.inventory_id}")
    #     for phase in result.phases:
    #         print(f"  {phase.name}: {phase.status} {phase.message or ''}")
    #     raise
    # print(f"{result.status}: inventory={result.inventory_id} verification={result.verification}")
    # for binding in result.interface_bindings:
    #     print(f"  {binding.key} -> {binding.port_id}")


if __name__ == "__main__":
    main()
