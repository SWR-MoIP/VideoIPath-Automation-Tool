import logging
from typing import Optional

from videoipath_automation_tool.apps.inspect.api.topology.collector_api import InspectCollectorAPI
from videoipath_automation_tool.apps.inspect.api.topology.network_api import InspectNetworkActionsAPI
from videoipath_automation_tool.connector.vip_connector import VideoIPathConnector
from videoipath_automation_tool.utils.cross_app_utils import create_fallback_logger


class InspectAPI:
    def __init__(self, vip_connector: VideoIPathConnector, logger: Optional[logging.Logger] = None):
        """
        API-oriented layer for Inspect-App-related operations.


        Args:
            vip_connector (VideoIPathConnector): VideoIPathConnector instance to handle the connection to the VideoIPath-Server.
            logger (Optional[logging.Logger]): Logger instance. If `None`, a fallback logger is used.
        """

        # --- Setup Logging ---
        self._logger = logger or create_fallback_logger("videoipath_automation_tool_inspect_api")
        self.vip_connector = vip_connector

        # --- Setup API Sub-Layers ---
        self.collector = InspectCollectorAPI(vip_connector=vip_connector, logger=self._logger)
        self.network = InspectNetworkActionsAPI(vip_connector=vip_connector, logger=self._logger)

        self._logger.debug("Inspect API initialized.")
