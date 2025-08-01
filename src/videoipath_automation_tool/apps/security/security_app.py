import logging
from typing import Optional

from videoipath_automation_tool.apps.security.app.security_domains_app import SecurityDomains
from videoipath_automation_tool.apps.security.app.security_resources_app import SecurityResources
from videoipath_automation_tool.apps.security.security_api import SecurityAPI
from videoipath_automation_tool.connector.vip_connector import VideoIPathConnector
from videoipath_automation_tool.utils.cross_app_utils import create_fallback_logger


class SecurityApp:
    def __init__(self, vip_connector: VideoIPathConnector, logger: Optional[logging.Logger] = None):
        """SecurityApp contains functionality to interact with the VideoIPath Security App.

        Args:
            vip_connector (VideoIPathConnector): VideoIPathConnector instance to handle the connection to the VideoIPath-Server.
            logger (Optional[logging.Logger], optional): Logger instance to use for logging.
        """
        # --- Setup Logging ---
        self._logger = logger or create_fallback_logger("videoipath_automation_tool_security_app")

        # --- Setup Security API ---
        self._security_api = SecurityAPI(vip_connector=vip_connector, logger=self._logger)

        # --- Setup Domains Layer ---
        self.domains = SecurityDomains(self._security_api, self._logger)

        # --- Setup Resources Layer ---
        self.resources = SecurityResources(self._security_api, self._logger)

        self._logger.debug("Security APP initialized.")
