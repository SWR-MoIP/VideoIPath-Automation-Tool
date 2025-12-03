# VideoIPath MCP Server

A Model Context Protocol (MCP) server for VideoIPath Automation Tool, providing AI assistants with access to VideoIPath inventory management capabilities.

## Features

- **Device Management**: Get, add, update, and remove devices from VideoIPath inventory
- **Device Discovery**: List and retrieve discovered devices
- **Device Search**: Find devices by label, address, or driver
- **SNMP Configuration**: Manage global SNMP configurations
- **Extensible Architecture**: Easy to add support for other VideoIPath apps (topology, profile, security, preferences)

## Installation

The MCP server is included as part of the VideoIPath Automation Tool package. Install dependencies:

```bash
pip install videoipath-automation-tool
```

Or install from source:

```bash
poetry install
```

## Configuration

The MCP server requires the following environment variables:

- `VIDEOIPATH_SERVER_ADDRESS`: The IP address or URL of the VideoIPath server
- `VIDEOIPATH_USERNAME`: Username for authentication
- `VIDEOIPATH_PASSWORD`: Password for authentication
- `VIDEOIPATH_USE_HTTPS`: Use HTTPS (default: `true`)
- `VIDEOIPATH_VERIFY_SSL`: Verify SSL certificates (default: `true`)

## Usage

### Running the Server

Run the MCP server using the command-line entry point:

```bash
videoipath-mcp-server
```

Or run directly with Python:

```bash
python -m videoipath_mcp.main
```

### Cursor Configuration

To configure the MCP server in Cursor IDE, you have two options:

#### Option 1: Using Cursor Settings UI

1. **Open Cursor Settings**:
   - Launch Cursor
   - Click on the gear icon (⚙️) in the upper right corner to open Settings
   - Or use `Cmd+,` (macOS) / `Ctrl+,` (Windows/Linux)

2. **Navigate to MCP Configuration**:
   - In the left sidebar, select **Features**
   - Click on **MCP** (Model Context Protocol)

3. **Add a New MCP Server**:
   - Click the **+ Add New MCP Server** button
   - A modal will appear prompting you to enter the server details

4. **Enter Server Details**:
   - **Name**: Enter a nickname for your MCP server (e.g., `videoipath`)
   - **Type**: Select **Stdio** (standard input/output)
   - **Command**: Enter the command to start the server:
     ```
     videoipath-mcp-server
     ```
     Or if using Python directly:
     ```
     python -m videoipath_mcp.main
     ```
   - **Environment Variables**: Add the following environment variables:
     - `VIDEOIPATH_SERVER_ADDRESS`: Your VideoIPath server address
     - `VIDEOIPATH_USERNAME`: Your username
     - `VIDEOIPATH_PASSWORD`: Your password
     - `VIDEOIPATH_USE_HTTPS`: `true` or `false` (default: `true`)
     - `VIDEOIPATH_VERIFY_SSL`: `true` or `false` (default: `true`)

5. **Save and Verify**:
   - Click **Save** to add the MCP server
   - The server should appear in the list of MCP servers
   - Click the refresh button (🔄) to populate the tool list
   - Verify that the inventory tools are listed and available

#### Option 2: Using Configuration File

Cursor also supports configuration via a settings file. Add the following to your Cursor settings (typically located at `~/.cursor/settings.json` or accessed via `Cmd+Shift+P` → "Preferences: Open User Settings (JSON)"):

```json
{
  "mcp.servers": {
    "videoipath": {
      "command": "videoipath-mcp-server",
      "env": {
        "VIDEOIPATH_SERVER_ADDRESS": "your-server-address",
        "VIDEOIPATH_USERNAME": "your-username",
        "VIDEOIPATH_PASSWORD": "your-password",
        "VIDEOIPATH_USE_HTTPS": "true",
        "VIDEOIPATH_VERIFY_SSL": "true"
      }
    }
  }
}
```

**Note**: After adding the configuration, restart Cursor or reload the window (`Cmd+Shift+P` → "Developer: Reload Window") for the changes to take effect.

#### Using MCP Tools in Cursor

Once configured, the MCP tools will be automatically available to the Composer agent in Cursor. You can:
- Ask the agent to use specific tools (e.g., "List all devices in the inventory")
- The agent will automatically select appropriate tools based on your requests
- View available tools in the MCP settings panel

### Claude Desktop Configuration

Add the server to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "videoipath": {
      "command": "videoipath-mcp-server",
      "env": {
        "VIDEOIPATH_SERVER_ADDRESS": "your-server-address",
        "VIDEOIPATH_USERNAME": "your-username",
        "VIDEOIPATH_PASSWORD": "your-password",
        "VIDEOIPATH_USE_HTTPS": "true",
        "VIDEOIPATH_VERIFY_SSL": "true"
      }
    }
  }
}
```

### Available Tools

#### Device Management

- `inventory_get_device`: Get a device by device ID
- `inventory_list_devices`: List all device IDs (optionally filtered by driver)
- `inventory_add_device`: Add a new device to inventory
- `inventory_update_device`: Update an existing device
- `inventory_remove_device`: Remove a device from inventory
- `inventory_enable_device`: Enable a device
- `inventory_disable_device`: Disable a device

#### Device Discovery

- `inventory_get_discovered_devices`: Get all discovered devices
- `inventory_find_device_by_label`: Find device(s) by label

#### SNMP Configuration

- `inventory_get_global_snmp_config`: Get a global SNMP configuration
- `inventory_list_global_snmp_configs`: List all global SNMP configurations

## Architecture

The MCP server is built using FastMCP from the official MCP Python SDK, following best practices:

- **Lifespan Management**: Proper initialization and cleanup of resources
- **Type Safety**: Typed context and dependencies
- **Extensible Design**: Modular structure for adding new apps
- **Error Handling**: Comprehensive error handling and logging

### Directory Structure

```
src/videoipath_mcp/
├── __init__.py          # Package initialization
├── main.py              # Main entry point
├── server.py            # Core server implementation
├── apps/
│   ├── __init__.py
│   └── inventory/
│       ├── __init__.py
│       └── tools.py     # Inventory app tools
└── README.md            # This file
```

### Adding New Apps

To add support for additional VideoIPath apps (e.g., topology, profile):

1. Create a new directory under `src/videoipath_mcp/apps/` (e.g., `topology/`)
2. Create `tools.py` with your app's tools using the `@mcp.tool()` decorator
3. Import and register the tools in `main.py`
4. Add the app to the `AppContext` in `server.py` if needed

Example:

```python
# src/videoipath_mcp/apps/topology/tools.py
from ...server import mcp, get_topology_app

@mcp.tool()
def topology_get_device(device_id: str, ctx: Context = None):
    """Get a topology device."""
    topology_app = get_topology_app(ctx)
    return topology_app.get_device(device_id=device_id)
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
ruff format src/videoipath_mcp
ruff check src/videoipath_mcp
```

## License

AGPL-3.0-only - See LICENSE file for details.

