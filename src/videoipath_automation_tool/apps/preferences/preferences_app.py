import logging
from typing import Optional

from videoipath_automation_tool.apps.preferences.preferences_api import PreferencesAPI
from videoipath_automation_tool.apps.preferences.sections.system_configuration import SystemConfiguration

# from videoipath_automation_tool.apps.preferences.sections.apps import Apps
# from videoipath_automation_tool.apps.preferences.sections.license import License
# from videoipath_automation_tool.apps.preferences.sections.packages_and_certificates import PackagesAndCertificates
from videoipath_automation_tool.connector.vip_connector import VideoIPathConnector


class PreferencesApp:
    def __init__(self, vip_connector: VideoIPathConnector, logger: Optional[logging.Logger] = None):
        """PreferencesApp contains functionality to interact with the VideoIPath System Preferences.

        Args:
            vip_connector (VideoIPathConnector): VideoIPathConnector instance to handle the connection to the VideoIPath-Server.
            logger (Optional[logging.Logger], optional): Logger instance to use for logging.
        """
        # --- Setup Logging ---
        if logger is None:
            self.logger = logging.getLogger(
                "videoipath_automation_tool_preferences_app"
            )  # create fallback logger if no logger is provided
            self.logger.debug(
                "No logger for System Preferences App provided. Creating fallback logger: 'videoipath_automation_tool_preferences_app'."
            )
        else:
            self.logger = logger

        # --- Setup System Preferences API ---
        try:
            self._preferences_api = PreferencesAPI(vip_connector=vip_connector)
            self.logger.debug("System Preferences API initialized.")
        except Exception as e:
            self.logger.error(f"Error initializing System Preferences API: {e}")
            raise ConnectionError("Error initializing System Preferences API.")

        # --- Setup Sections ---
        self.system_configuration = SystemConfiguration(preferences_api=self._preferences_api, logger=self.logger)
        # self.packages_and_certificates = PackagesAndCertificates(preferences_api=self._preferences_api, logger=self.logger)
        # self.system_configuration = SystemConfiguration(preferences_api=self._preferences_api, logger=self.logger)
        # self.system_configuration = SystemConfiguration(preferences_api=self._preferences_api, logger=self.logger)
