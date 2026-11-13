<div align="center">
  <img src="https://raw.githubusercontent.com/SWR-MoIP/VideoIPath-Automation-Tool/refs/heads/main/docs/images/logo-lightmode.svg#gh-light-mode-only" width="400" />
  <img src="./docs/images/logo-darkmode.svg#gh-dark-mode-only" width="400" alt="" />
</div>

<p align="center">A <a href="https://www.python.org" target="_blank" rel="noopener noreferrer">Python</a> package for automating <a href="https://nevion.com/videoipath" target="_blank" rel="noopener noreferrer">VideoIPath</a> configuration workflows.</p>

<div align="center">
  
[![PyPI version](https://img.shields.io/pypi/v/videoipath-automation-tool)](https://pypi.org/project/videoipath-automation-tool/)
[![GitHub Workflow Status](https://github.com/SWR-MoIP/VideoIPath-Automation-Tool/actions/workflows/ci.yml/badge.svg)](https://github.com/SWR-MoIP/VideoIPath-Automation-Tool/actions/workflows/ci.yml)
[![Python Versions](https://img.shields.io/badge/python-3.11%20|%203.12%20|%203.13%20|%203.14-blue)](https://github.com/SWR-MoIP/VideoIPath-Automation-Tool)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)

</div>


## Introduction

The **VideoIPath Automation Tool** is a Python package designed to simplify interactions with the VideoIPath API. Its focus is on automating configuration tasks and bulk operations on VideoIPath servers in a user-friendly and efficient way. The package hides the complexity of the API behind a clean, high-level interface – from system-wide **Settings**, through device onboarding in **Inventory**, to network modeling in **Topology** and **Inspect**.

Its data models provide robust validation and easy handling, complemented by comprehensive logging.

## Quick Start Guide

### Prerequisites

- Access to a VideoIPath Server (version 2023.4.2 or higher, LTS versions recommended)
- Username and Password for a user account with API access
- Python 3.11 or higher

### Installation

The package is available via the [Python Package Index (PyPI)](https://pypi.org/project/videoipath-automation-tool/) and can be installed directly using `pip`.

#### Install the package using pip

```bash
pip install videoipath-automation-tool
```

For production use, it is recommended to pin a minor version, as minor releases may contain breaking changes until 1.0:

```bash
pip install "videoipath-automation-tool~=0.11.0"
```

**Note:** By default, the latest Long-Term Support (LTS) version (currently **2024.4.30**) is used for schema validation and IntelliSense.

To switch to a specific version, see the [Driver Versioning Guide](https://github.com/SWR-MoIP/VideoIPath-Automation-Tool/blob/main/docs/driver-versioning.md)

### A Simple Example: Adding a Device to the Inventory

```python
# Import the `VideoIPathApp` class from the videoipath_automation_tool package
from videoipath_automation_tool import VideoIPathApp

# Initialize the VideoIPathApp
app = VideoIPathApp(server_address="10.1.100.10", username="api-user", password="veryStrongPassword", use_https=False, verify_ssl_cert=False)

# Create a device object with NMOS Multidevice driver
staged_device = app.inventory.create_device(driver="com.nevion.NMOS_multidevice-0.1.0")

# Set the device label, description, address, nmos port and disable 'Use indices in IDs' option
staged_device.configuration.label = "Media-Node-1"
staged_device.configuration.description = "Hello World"
staged_device.configuration.address = "10.100.100.1"
staged_device.configuration.custom_settings.port = 8080
staged_device.configuration.custom_settings.indices_in_ids = False

# Add the configured device to the inventory of the VideoIPath server
# This immediately registers the device and returns the assigned device object.
try:
    device = app.inventory.add_device(staged_device)
    print(f"Device added successfully: {device.device_id}")
    #> Device added successfully: device34
except Exception as e:
    print(f"Failed to add device: {e}")
```

## Documentation

- [Getting Started Guide](https://github.com/SWR-MoIP/VideoIPath-Automation-Tool/blob/main/docs/getting-started-guide/README.md)
- [Examples](https://github.com/SWR-MoIP/VideoIPath-Automation-Tool/blob/main/docs/examples/README.md)
- [Driver Versioning](https://github.com/SWR-MoIP/VideoIPath-Automation-Tool/blob/main/docs/driver-versioning.md)
- [Python Module Architecture](https://github.com/SWR-MoIP/VideoIPath-Automation-Tool/blob/main/docs/architecture/python-module-architecture.md)
- [Development and Release](https://github.com/SWR-MoIP/VideoIPath-Automation-Tool/blob/main/docs/development-and-release.md)

## Feedback & Contributions

Your feedback and contributions are highly appreciated! There are several ways to participate and help improve the **VideoIPath Automation Tool**:

<p>
  ✅ <strong>Report issues & suggest features:</strong> Open an issue on GitHub:  
  ➝ <a href="https://github.com/SWR-MoIP/VideoIPath-Automation-Tool/issues">GitHub Issues</a>
</p>

<p>
  ✅ <strong>Contribute via pull requests:</strong> If you want to implement a fix or a new feature yourself, feel free to fork the repository and submit a pull request.  
  ➝ <a href="https://github.com/SWR-MoIP/VideoIPath-Automation-Tool/fork">Fork the Repository</a>
</p>

<p>
  ✅ <strong>Discuss & provide feedback:</strong> If you have general feedback or ideas that don’t fit into an issue, feel free to reach out via email:  
  📧 <a href="mailto:moip@swr.de">moip@swr.de</a>
</p>

Thank you for your support and contributions!

## Disclaimer

VideoIPath Automation Tool is an independent software tool that can be used with the [VideoIPath](https://nevion.com/videoipath) media orchestration platform. However, it is not a product or service offered by Nevion, and Nevion is not responsible for its functionality, performance, support, or any unforeseen consequences arising from its use. Nevion's VideoIPath platform is used to manage critical media infrastructure, and special care is advised concerning the use of external tools such as this.

## License

[Affero General Public License v3.0](https://github.com/SWR-MoIP/VideoIPath-Automation-Tool/blob/main/LICENSE)
