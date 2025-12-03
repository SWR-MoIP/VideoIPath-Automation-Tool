"""Inventory app MCP tools."""

from typing import Any, List, Optional

from mcp.server.fastmcp import Context
from mcp.server.session import ServerSession

from ...server import AppContext, get_inventory_app, get_logger, mcp


@mcp.tool()
def inventory_get_device(
    device_id: str,
    config_only: bool = False,
    *,
    ctx: Context[ServerSession, AppContext] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get a device from VideoIPath inventory by device ID.

    Args:
        device_id: The device ID (e.g., "device1")
        config_only: If True, only fetch configuration without status. Defaults to False.
        ctx: MCP context (automatically injected)

    Returns:
        Device configuration and status as a dictionary
    """
    inventory_app = get_inventory_app(ctx)
    logger = get_logger(ctx)

    try:
        device = inventory_app.get_device(device_id=device_id, config_only=config_only)
        result = device.model_dump(mode="json", exclude_none=True)
        logger.info(f"Retrieved device: {device_id}")
        return result
    except Exception as e:
        logger.error(f"Error retrieving device {device_id}: {e}")
        raise


@mcp.tool()
def inventory_list_devices(
    driver: Optional[str] = None,
    *,
    ctx: Context[ServerSession, AppContext] = None,  # type: ignore[assignment]
) -> List[str]:
    """List all device IDs from VideoIPath inventory.

    Args:
        driver: Optional driver ID to filter devices (e.g., "com.nevion.arista-0.1.0")
        ctx: MCP context (automatically injected)

    Returns:
        List of device IDs
    """
    inventory_app = get_inventory_app(ctx)
    logger = get_logger(ctx)

    try:
        if driver:
            device_ids = inventory_app.list_device_ids_by_driver(driver=driver)
        else:
            device_ids = inventory_app._inventory_api.fetch_device_ids_list()
        logger.info(f"Listed {len(device_ids)} devices")
        return device_ids
    except Exception as e:
        logger.error(f"Error listing devices: {e}")
        raise


@mcp.tool()
def inventory_add_device(
    device_config: dict[str, Any],
    label_check: bool = True,
    address_check: bool = True,
    config_only: bool = False,
    *,
    ctx: Context[ServerSession, AppContext] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Add a new device to VideoIPath inventory.

    Args:
        device_config: Device configuration dictionary (must include driver_id in customSettings)
        label_check: Check if device with same label already exists. Defaults to True.
        address_check: Check if device with same address already exists. Defaults to True.
        config_only: Add device with configuration only (skip status fetch). Defaults to False.
        ctx: MCP context (automatically injected)

    Returns:
        Added device configuration and status as a dictionary
    """
    from videoipath_automation_tool.apps.inventory.model.inventory_device import InventoryDevice

    inventory_app = get_inventory_app(ctx)
    logger = get_logger(ctx)

    try:
        device = InventoryDevice.model_validate(device_config)
        device.remove_device_id()
        added_device = inventory_app.add_device(
            device=device, label_check=label_check, address_check=address_check, config_only=config_only
        )
        result = added_device.model_dump(mode="json", exclude_none=True)
        logger.info(f"Added device: {added_device.device_id}")
        return result
    except Exception as e:
        logger.error(f"Error adding device: {e}")
        raise


@mcp.tool()
def inventory_update_device(
    device_config: dict[str, Any],
    compare_config: bool = True,
    config_only: bool = False,
    *,
    ctx: Context[ServerSession, AppContext] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Update an existing device in VideoIPath inventory.

    Args:
        device_config: Device configuration dictionary (must include device ID)
        compare_config: Compare configuration before updating to prevent unnecessary updates. Defaults to True.
        config_only: Update device with configuration only (skip status fetch). Defaults to False.
        ctx: MCP context (automatically injected)

    Returns:
        Updated device configuration and status as a dictionary
    """
    from videoipath_automation_tool.apps.inventory.model.inventory_device import InventoryDevice

    inventory_app = get_inventory_app(ctx)
    logger = get_logger(ctx)

    try:
        device = InventoryDevice.model_validate(device_config)
        updated_device = inventory_app.update_device(
            device=device, compare_config=compare_config, config_only=config_only
        )
        result = updated_device.model_dump(mode="json", exclude_none=True)
        logger.info(f"Updated device: {updated_device.device_id}")
        return result
    except Exception as e:
        logger.error(f"Error updating device: {e}")
        raise


@mcp.tool()
def inventory_remove_device(
    device_id: str,
    check_remove: bool = True,
    *,
    ctx: Context[ServerSession, AppContext] = None,  # type: ignore[assignment]
) -> Optional[dict[str, Any]]:
    """Remove a device from VideoIPath inventory.

    Args:
        device_id: The device ID to remove
        check_remove: Verify that device was removed successfully. Defaults to True.
        ctx: MCP context (automatically injected)

    Returns:
        Last device configuration before removal, or None if device didn't exist
    """
    inventory_app = get_inventory_app(ctx)
    logger = get_logger(ctx)

    try:
        removed_device = inventory_app.remove_device(device_id=device_id, check_remove=check_remove)
        if removed_device:
            result = removed_device.model_dump(mode="json", exclude_none=True)
            logger.info(f"Removed device: {device_id}")
            return result
        else:
            logger.warning(f"Device {device_id} not found for removal")
            return None
    except Exception as e:
        logger.error(f"Error removing device {device_id}: {e}")
        raise


@mcp.tool()
def inventory_find_device_by_label(
    label: str,
    label_search_mode: str = "canonical_label",
    *,
    ctx: Context[ServerSession, AppContext] = None,  # type: ignore[assignment]
) -> Optional[str | List[str]]:
    """Find device ID(s) by label.

    Args:
        label: The device label to search for
        label_search_mode: Search mode - "canonical_label", "factory_label_only", or "user_defined_label_only". Defaults to "canonical_label".
        ctx: MCP context (automatically injected)

    Returns:
        Device ID or list of device IDs if multiple matches, None if not found
    """
    inventory_app = get_inventory_app(ctx)
    logger = get_logger(ctx)

    try:
        result = inventory_app.find_device_id_by_label(label=label, label_search_mode=label_search_mode)
        logger.info(f"Found device(s) for label '{label}': {result}")
        return result
    except Exception as e:
        logger.error(f"Error finding device by label '{label}': {e}")
        raise


@mcp.tool()
def inventory_get_discovered_devices(
    *,
    ctx: Context[ServerSession, AppContext] = None,  # type: ignore[assignment]
) -> List[dict[str, Any]]:
    """Get all discovered devices from VideoIPath inventory.

    Args:
        ctx: MCP context (automatically injected)

    Returns:
        List of discovered device configurations
    """
    inventory_app = get_inventory_app(ctx)
    logger = get_logger(ctx)

    try:
        discovered_devices = inventory_app.get_discovered_devices()
        result = [device.model_dump(mode="json", exclude_none=True) for device in discovered_devices]
        logger.info(f"Retrieved {len(discovered_devices)} discovered devices")
        return result
    except Exception as e:
        logger.error(f"Error retrieving discovered devices: {e}")
        raise


@mcp.tool()
def inventory_enable_device(
    device_id: str,
    *,
    ctx: Context[ServerSession, AppContext] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Enable a device in VideoIPath inventory.

    Args:
        device_id: The device ID to enable
        ctx: MCP context (automatically injected)

    Returns:
        Device configuration after enabling
    """
    inventory_app = get_inventory_app(ctx)
    logger = get_logger(ctx)

    try:
        device = inventory_app.enable_device(device_id=device_id)
        result = device.model_dump(mode="json", exclude_none=True)
        logger.info(f"Enabled device: {device_id}")
        return result
    except Exception as e:
        logger.error(f"Error enabling device {device_id}: {e}")
        raise


@mcp.tool()
def inventory_disable_device(
    device_id: str,
    *,
    ctx: Context[ServerSession, AppContext] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Disable a device in VideoIPath inventory.

    Args:
        device_id: The device ID to disable
        ctx: MCP context (automatically injected)

    Returns:
        Device configuration after disabling
    """
    inventory_app = get_inventory_app(ctx)
    logger = get_logger(ctx)

    try:
        device = inventory_app.disable_device(device_id=device_id)
        result = device.model_dump(mode="json", exclude_none=True)
        logger.info(f"Disabled device: {device_id}")
        return result
    except Exception as e:
        logger.error(f"Error disabling device {device_id}: {e}")
        raise


@mcp.tool()
def inventory_get_global_snmp_config(
    snmp_config_id: str,
    *,
    ctx: Context[ServerSession, AppContext] = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """Get a global SNMP configuration by ID.

    Args:
        snmp_config_id: The SNMP configuration ID
        ctx: MCP context (automatically injected)

    Returns:
        SNMP configuration as a dictionary
    """
    inventory_app = get_inventory_app(ctx)
    logger = get_logger(ctx)

    try:
        snmp_config = inventory_app.get_global_snmp_config(snmp_config_id=snmp_config_id)
        result = snmp_config.model_dump(mode="json", exclude_none=True)
        logger.info(f"Retrieved SNMP config: {snmp_config_id}")
        return result
    except Exception as e:
        logger.error(f"Error retrieving SNMP config {snmp_config_id}: {e}")
        raise


@mcp.tool()
def inventory_list_global_snmp_configs(
    *,
    ctx: Context[ServerSession, AppContext] = None,  # type: ignore[assignment]
) -> dict[str, str]:
    """List all global SNMP configuration IDs with their labels.

    Args:
        ctx: MCP context (automatically injected)

    Returns:
        Dictionary mapping SNMP config IDs to labels
    """
    inventory_app = get_inventory_app(ctx)
    logger = get_logger(ctx)

    try:
        snmp_configs = inventory_app.get_all_global_snmp_config_ids()
        logger.info(f"Listed {len(snmp_configs)} SNMP configurations")
        return snmp_configs
    except Exception as e:
        logger.error(f"Error listing SNMP configs: {e}")
        raise


def register_inventory_tools() -> None:
    """Register all inventory tools with the MCP server.

    This function is called automatically when the module is imported.
    All tools are registered via the @mcp.tool() decorator.
    """
    pass
