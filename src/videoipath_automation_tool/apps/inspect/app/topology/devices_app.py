import logging

from videoipath_automation_tool.apps.inspect.inspect_api import InspectAPI


class InspectDevicesApp:
    def __init__(self, inspect_api: InspectAPI, logger: logging.Logger):
        self._inspect_api = inspect_api
        self._logger = logger
