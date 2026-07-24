"""Connect to a VideoIPath server and verify the connection.

Description
-----------
The entry point to the whole package is a single ``VideoIPathApp`` object. This example shows the two
ways to construct it (explicit arguments vs. ``VIPAT_*`` environment variables / a ``.env`` file),
how to verify connectivity, read the server version, and how the sub-apps
(``inventory``, ``topology``, ``inspect``, ``preferences``, ``profile``, ``security``) hang off it.

Every other example in this folder assumes this connection boilerplate and jumps straight into the
relevant sub-app.

Prerequisites
-------------
- A reachable VideoIPath server and valid credentials.
- videoipath-automation-tool installed (``pip install videoipath-automation-tool``).

Related examples
----------------
- 02_inventory/01_create_and_add_device.py
- 04_inspect/01_explore_topology_read_only.py
"""

from __future__ import annotations

from videoipath_automation_tool import VideoIPathApp

# Placeholder values — replace with your environment's data.
SERVER_ADDRESS = "<your-videoipath-ip-or-domain>"
USERNAME = "<your-videoipath-api-user>"
PASSWORD = "<your-videoipath-api-password>"


def main() -> None:
    # --- 1. Connect with explicit arguments -----------------------------------
    # `use_https`/`verify_ssl_cert` default to True; they are relaxed here for a lab server.
    app = VideoIPathApp(
        server_address=SERVER_ADDRESS,
        username=USERNAME,
        password=PASSWORD,
        use_https=False,
        verify_ssl_cert=False,
    )

    # --- 2. Alternative: connect from environment / .env ----------------------
    # With VIPAT_VIDEOIPATH_SERVER_ADDRESS, VIPAT_VIDEOIPATH_USERNAME, VIPAT_VIDEOIPATH_PASSWORD
    # (and optional VIPAT_USE_HTTPS / VIPAT_VERIFY_SSL_CERT) set, no arguments are needed:
    #
    #     app = VideoIPathApp()

    # --- 3. Verify the connection ---------------------------------------------
    app.check_connection()  # raises ConnectionError if the server is unreachable / credentials fail
    print("Connected to", SERVER_ADDRESS)
    # > Connected to 192.0.2.10

    print("Server version:", app.get_server_version())
    # > Server version: 2025.4.9

    # --- 4. Sub-apps are lazily initialized on first access -------------------
    # Each sub-app is the namespace for one area of the API.
    print("Inventory devices:", len(app.inventory.list_device_ids_by_driver("com.nevion.NMOS_multidevice-0.1.0")))
    # > Inventory devices: 3

    print("Topology devices in Inspect:", len(app.inspect.devices))
    # > Topology devices in Inspect: 12


if __name__ == "__main__":
    main()
