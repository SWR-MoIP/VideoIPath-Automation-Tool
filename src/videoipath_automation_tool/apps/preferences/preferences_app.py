import logging
from typing import Optional

from videoipath_automation_tool.apps.preferences.preferences_api import PreferencesAPI
from videoipath_automation_tool.apps.preferences.sections.license import License
from videoipath_automation_tool.apps.preferences.sections.packages_and_certificates import PackagesAndCertificates
from videoipath_automation_tool.apps.preferences.sections.system_configuration import SystemConfiguration

# from videoipath_automation_tool.apps.preferences.sections.apps import Apps
# from videoipath_automation_tool.apps.preferences.sections.packages_and_certificates import PackagesAndCertificates
from videoipath_automation_tool.connector.vip_connector import VideoIPathConnector
from videoipath_automation_tool.utils.cross_app_utils import create_fallback_logger


class PreferencesApp:
    def __init__(self, vip_connector: VideoIPathConnector, logger: Optional[logging.Logger] = None):
        """PreferencesApp contains functionality to interact with the VideoIPath System Preferences App.

        Args:
            vip_connector (VideoIPathConnector): VideoIPathConnector instance to handle the connection to the VideoIPath-Server.
            logger (Optional[logging.Logger], optional): Logger instance to use for logging.
        """

        # --- Setup Logging ---
        self._logger = logger or create_fallback_logger("videoipath_automation_tool_preferences_app")

        # --- Setup System Preferences API ---
        self._preferences_api = PreferencesAPI(vip_connector=vip_connector)

        # --- Setup Preferences Sections ---
        self.system_configuration = SystemConfiguration(preferences_api=self._preferences_api, logger=self._logger)
        self.packages_and_certificates = PackagesAndCertificates(
            preferences_api=self._preferences_api, logger=self._logger
        )
        self.license = License(preferences_api=self._preferences_api, logger=self._logger)

        # self.apps = Apps(preferences_api=self._preferences_api, logger=self.logger)
