import logging

from videoipath_automation_tool.apps.inspect.app.topology.devices_app import InspectDevicesApp
from videoipath_automation_tool.apps.inspect.inspect_api import InspectAPI


class InspectTopologyApp:
    def __init__(self, inspect_api: InspectAPI, logger: logging.Logger):
        self._inspect_api = inspect_api
        self._logger = logger
        self.devices = InspectDevicesApp(inspect_api, logger)
