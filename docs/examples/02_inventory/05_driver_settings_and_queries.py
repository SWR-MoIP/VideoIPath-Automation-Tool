"""Driver-specific settings and inventory queries.

Description
-----------
Every driver exposes its own typed ``custom_settings`` model, so the fields you can set depend on the
driver id you pass to ``create_device``. This example inspects and edits those settings, then shows
the common inventory lookup helpers (all device ids for a driver, id-by-label) and a short global SNMP
configuration section.

Prerequisites
-------------
- A reachable VideoIPath server with devices in the inventory.

Related examples
----------------
- 02_inventory/01_create_and_add_device.py
"""

from __future__ import annotations

from videoipath_automation_tool import VideoIPathApp

SERVER_ADDRESS = "<your-videoipath-ip-or-domain>"
USERNAME = "<your-videoipath-api-user>"
PASSWORD = "<your-videoipath-api-password>"

DRIVER = "com.nevion.NMOS_multidevice-0.1.0"


def main() -> None:
    # --- 1. Connect -----------------------------------------------------------
    app = VideoIPathApp(server_address=SERVER_ADDRESS, username=USERNAME, password=PASSWORD, use_https=False)

    # --- 2. Inspect and edit typed driver settings ----------------------------
    device = app.inventory.create_device(driver=DRIVER)
    settings = device.configuration.custom_settings

    # The available fields are specific to this driver; read defaults, then change them.
    print("Default NMOS port:", settings.port)
    # > Default NMOS port: 8080
    settings.port = 8000
    settings.indices_in_ids = True

    # --- 3. Query the inventory -----------------------------------------------
    device_ids = app.inventory.list_device_ids_by_driver(DRIVER)
    print(f"{len(device_ids)} device(s) use this driver: {device_ids}")
    # > 2 device(s) use this driver: ['device34', 'device36']

    device_id = app.inventory.find_device_id_by_label("device-a", label_search_mode="user_defined_label_only")
    print("device-a ->", device_id)
    # > device-a -> device34

    # --- 4. Global SNMP configurations ----------------------------------------
    snmp_configs = app.inventory.get_all_global_snmp_config_ids()
    print("Global SNMP configs:", snmp_configs)
    # > Global SNMP configs: {'default': 'default'}

    default_snmp = app.inventory.get_global_snmp_config("default")
    print("Default SNMP read community:", default_snmp.security.read.community)
    # > Default SNMP read community: public


if __name__ == "__main__":
    main()
