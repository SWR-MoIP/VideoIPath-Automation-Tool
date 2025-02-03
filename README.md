<div align="center">
  <img alt="VideoIPath Automation Tool" src="./docs/images/readme_banner.svg" width="400" />
</div>

<p align="center">A Python package for automating VideoIPath configuration workflows.<p align="center">
<hr />

## ⚠️ Attention ⚠️

This Python package, the VideoIPath Automation Tool, is still under development and currently in the alpha phase. Features and interfaces may change significantly as development progresses. Feel free to use the module and provide feedback, but be aware that breaking changes may occur in future versions.

## Introduction

The **VideoIPath Automation Tool** is a Python package designed to simplify and optimize interactions with the VideoIPath API. The focus is on providing a user-friendly and efficient way to automate configuration tasks and bulk operations on VideoIPath servers. The package abstracts the complexity of the API and provides a high-level interface. Currently, the package offers methods for managing devices  in the Inventory and Topology apps, as well as the configuration of multicast pools and profiles.

The provided methods and data models ensure easy handling, robust validation, comprehensive logging, and enhanced reliability.

## Getting started

### Prerequisites

- Access to a VideoIPath Server
- A user account with API access credentials
- Python 3.11 or higher

### Installation

The package is available via the [Gitlab Package Index of the MOIP group](https://gitlab.swr.ard/groups/moip/-/packages/). There are multiple ways to install
it, but since it's not available in the public PyPI you either have to setup authentication to the private
package index or download the build artifact manually.

#### Option 1 (quick): Downloading the Build Artifact manually

1. Download the latest version of the package from the [Package Registry]()
2. Install the package using pip:

```bash
pip3 install "path/to/downloads/VideoIPath_Automation_Tool-0.1.0.tar.gz"
```

#### Option 2 (preferred): Set up Registry

1. Create a [personal access token](https://gitlab.swr.ard/-/user_settings/personal_access_tokens) with the `api` scope. Don't use whitespace in the name because it might cause issues with the authentication later.
2. Go to the [videoipath-automation-tool](https://gitlab.swr.ard/groups/moip/-/packages/594) package index entry and follow the instructions there.

> **Note**: On Windows, `~/.piprc` or `pip.conf` does not work, instead create a `%APPDATA%\pip\pip.ini` file. For more information on PIP configuration on different operating systems see the [official documentation](https://pip.pypa.io/en/stable/topics/configuration/)

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