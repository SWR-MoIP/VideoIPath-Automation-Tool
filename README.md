<div align="center">
  <img alt="VideoIPath Automation Tool" src="./docs/images/readme_banner.svg" width="400" />
</div>

<p align="center">A Python package for automating VideoIPath configuration workflows.<p align="center">
<hr />

> **⚠️ Attention ⚠️**<br>
>This Python package, the VideoIPath Automation Tool, is still under development and currently in the alpha phase. Features and interfaces may change significantly as development progresses. Feel free to use the module and provide feedback, but be aware that breaking changes may occur in future versions.

## Introduction

The **VideoIPath Automation Tool** is a Python package designed to simplify and optimize interactions with the VideoIPath API. The focus is on providing a user-friendly and efficient way to automate configuration tasks and bulk operations on VideoIPath servers. The package abstracts the complexity of the API and provides a high-level interface. Currently, the package offers methods for managing devices  in the Inventory and Topology apps, as well as the configuration of multicast pools and profiles.

The provided methods and data models ensure easy handling, robust validation, comprehensive logging, and enhanced reliability.

## Getting started

### Prerequisites

- Access to a VideoIPath Server (version 2023.4.2 or higher, LTS versions recommended)
- A user account with API access credentials
- Python 3.11 or higher

### Installation

Since the repository is currently private, the package must be downloaded manually as a build artifact from the [GitHub Releases section](https://github.com/SWR-MoIP/VideoIPath-Automation-Tool/releases).

Once the repository is public, the package will be available via the public PyPI registry for easy installation.

#### Install the package using pip

```bash
pip3 install "path/to/downloads/VideoIPath_Automation_Tool-0.1.0.tar.gz"
```

### A Simple Example

```python
# Import the `VideoIPathApp` class from the videoipath_automation_tool package
from videoipath_automation_tool import VideoIPathApp

# Initialize the VideoIPathApp
app = VideoIPathApp(server_address="10.1.100.10", username="api-user", password="VIP2024PWD")

# Create a device object with NMOS driver
staged_device = app.inventory.create_device(driver="com.nevion.NMOS_multidevice-0.1.0")

# Set the device label, description, address, nmos port and disable 'Use indices in IDs' option
staged_device.label = "Media-Node-1"
staged_device.description = "Hello World"
staged_device.address = "10.100.100.1"
staged_device.custom.port = 8080
staged_device.custom.indices_in_ids = False

# Add the device to the inventory
device = app.inventory.add_device(staged_device)

# Print the device id of the added device
print(device.device_id)
```

## Documentation

- [Examples](./docs/examples/README.md)
- [Driver Compatibility](./docs/driver_compatibility.md)
- [Development and Release](./docs/development-and-release.md)

## License

[Affero General Public License v3.0](LICENSE)
