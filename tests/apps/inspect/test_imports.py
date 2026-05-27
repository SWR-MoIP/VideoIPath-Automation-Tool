import logging
from unittest.mock import MagicMock

from videoipath_automation_tool.apps.inspect import InspectAPI, InspectApp
from videoipath_automation_tool.apps.inspect.app.topology.devices_app import InspectDevicesApp
from videoipath_automation_tool.apps.inspect.app.topology.topology_app import InspectTopologyApp


def test_inspect_app_and_api_import():
    assert InspectApp is not None
    assert InspectAPI is not None


def test_inspect_topology_devices_wiring():
    vip_connector = MagicMock()
    logger = logging.getLogger("test_inspect_imports")
    inspect_app = InspectApp(vip_connector=vip_connector, logger=logger)

    assert isinstance(inspect_app.topology, InspectTopologyApp)
    assert isinstance(inspect_app.topology.devices, InspectDevicesApp)
    assert inspect_app._inspect_api.collector is not None
    assert inspect_app._inspect_api.network is not None
