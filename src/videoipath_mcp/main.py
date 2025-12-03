"""Main entry point for the MCP server."""

from videoipath_mcp.apps.inventory import register_inventory_tools
from videoipath_mcp.apps.inventory.tools import (  # noqa: F401
    inventory_add_device,
    inventory_disable_device,
    inventory_enable_device,
    inventory_find_device_by_label,
    inventory_get_device,
    inventory_get_discovered_devices,
    inventory_get_global_snmp_config,
    inventory_list_devices,
    inventory_list_global_snmp_configs,
    inventory_remove_device,
    inventory_update_device,
)
from videoipath_mcp.server import mcp


def main() -> None:
    """Main entry point for the MCP server."""
    register_inventory_tools()
    mcp.run()


if __name__ == "__main__":
    main()
