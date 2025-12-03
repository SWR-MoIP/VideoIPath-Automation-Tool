"""MCP Server implementation for VideoIPath Automation Tool."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp.server import FastMCP
from mcp.server.fastmcp import Context
from mcp.server.session import ServerSession

from videoipath_automation_tool.apps.inventory import InventoryApp
from videoipath_automation_tool.connector.vip_connector import VideoIPathConnector


@dataclass
class AppContext:
    """Application context with typed dependencies."""

    connector: VideoIPathConnector
    inventory_app: InventoryApp
    logger: logging.Logger


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle with type-safe context."""
    import os

    server_address = os.getenv("VIDEOIPATH_SERVER_ADDRESS", "")
    username = os.getenv("VIDEOIPATH_USERNAME", "")
    password = os.getenv("VIDEOIPATH_PASSWORD", "")
    use_https = os.getenv("VIDEOIPATH_USE_HTTPS", "true").lower() == "true"
    verify_ssl = os.getenv("VIDEOIPATH_VERIFY_SSL", "true").lower() == "true"

    if not server_address or not username or not password:
        raise ValueError(
            "Missing required environment variables: VIDEOIPATH_SERVER_ADDRESS, VIDEOIPATH_USERNAME, VIDEOIPATH_PASSWORD"
        )

    logger = logging.getLogger("videoipath_mcp_server")
    logger.setLevel(logging.INFO)

    logger.info("Starting VideoIPath MCP Server")
    logger.info(f"Server address: {server_address}")
    logger.info(f"Username: {username}")
    logger.info(f"Password: {password}")
    logger.info(f"Use HTTPS: {use_https}")
    logger.info(f"Verify SSL: {verify_ssl}")

    connector = VideoIPathConnector(
        server_address=server_address,
        username=username,
        password=password,
        use_https=use_https,
        verify_ssl_cert=verify_ssl,
        logger=logger,
    )

    inventory_app = InventoryApp(vip_connector=connector, logger=logger)

    logger.info("Inventory app initialized")

    try:
        yield AppContext(connector=connector, inventory_app=inventory_app, logger=logger)
    finally:
        pass


mcp = FastMCP("VideoIPath Automation Tool", lifespan=app_lifespan)


def get_inventory_app(ctx: Context[ServerSession, AppContext]) -> InventoryApp:
    """Get the inventory app from context."""
    return ctx.request_context.lifespan_context.inventory_app


def get_logger(ctx: Context[ServerSession, AppContext]) -> logging.Logger:
    """Get the logger from context."""
    return ctx.request_context.lifespan_context.logger
