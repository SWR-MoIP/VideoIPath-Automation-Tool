import logging
from typing import Optional

from videoipath_automation_tool.apps.inspect.inspect_api import InspectAPI
from videoipath_automation_tool.connector.vip_connector import VideoIPathConnector
from videoipath_automation_tool.utils.cross_app_utils import create_fallback_logger


class InspectApp:
    def __init__(self, vip_connector: VideoIPathConnector, logger: Optional[logging.Logger] = None):
        """InspectApp contains functionality to interact with the VideoIPath Inspect-App.

        Args:
            vip_connector (VideoIPathConnector): VideoIPathConnector instance to handle the connection to the VideoIPath-Server.
            logger (Optional[logging.Logger], optional): Logger instance to use for logging.
        """
        # --- Setup Logging ---
        self._logger = logger or create_fallback_logger("videoipath_automation_tool_inspect_app")

        # --- Setup Inspect API ---
        self._inspect_api = InspectAPI(vip_connector=vip_connector, logger=self._logger)

        self._logger.debug("Inspect APP initialized.")
