# External Imports
import logging
from typing import Literal

# Internal Imports
from videoipath_automation_tool.apps.inventory.inventory_api import InventoryAPI
from videoipath_automation_tool.apps.preferences.preferences_api import PreferencesAPI
from videoipath_automation_tool.apps.preferences.preferences_app import PreferencesApp
from videoipath_automation_tool.apps.profile.profile_api import ProfileAPI
from videoipath_automation_tool.apps.profile.profile_app import ProfileApp
from videoipath_automation_tool.apps.topology.topology_api import TopologyAPI
from videoipath_automation_tool.settings import Settings
from videoipath_automation_tool.connector.vip_connector import VideoIPathConnector
from videoipath_automation_tool.apps.inventory.inventory_app import InventoryApp
from videoipath_automation_tool.apps.topology.topology_app import TopologyApp


class VideoIPathApp:
    """Main class for VideoIPath Automation Tool.
    VideoIPathApp contains all Apps and methods to interact with the VideoIPath System.
    """

    def __init__(
        self,
        server_address=None,
        username=None,
        password=None,
        use_https=None,
        verify_ssl_cert=None,
        log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO",
        environment=None,
    ):
        """Initialize the VideoIPath Automation Tool, establish connection to the VideoIPath-Server and initialize the Apps for interaction.
        Parameters can be provided directly or read from the environment variables.

        Args:
            server_address (str, optional): IP or hostname of the VideoIPath-Server. [ENV: VIPAT_VIDEOIPATH_SERVER_ADDRESS]
            username (str, optional): Username for the API User. [ENV: VIPAT_VIDEOIPATH_USERNAME]
            password (str, optional): Password for the API User. [ENV: VIPAT_VIDEOIPATH_PASSWORD]
            use_https (bool, optional): Use HTTPS for the connection. [ENV: VIPAT_USE_HTTPS]
            verify_ssl_cert (bool, optional): Verify the SSL certificate of the VideoIPath-Server. [ENV: VIPAT_VERIFY_SSL_CERT]
            log_level (str, optional): Define the log level: 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'. [ENV: VIPAT_LOG_LEVEL]
            environment (str, optional): Define the environment: 'DEV', 'TEST', 'PROD'. [ENV: VIPAT_ENVIRONMENT]
        """

        # --- Setup Logging ---
        log_level = (
            log_level.upper()
            if log_level
            else (Settings().VIPAT_LOG_LEVEL.upper() if Settings().VIPAT_LOG_LEVEL else "INFO")
        )

        if log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError(
                "Invalid log level provided. Please provide a valid log level: 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'."
            )

        logging.basicConfig(level=log_level)

        self.logger = logging.getLogger("videoipath_automation_tool")

        # --- Setup Environment ---
        environment = (
            environment.upper()
            if environment
            else (Settings().VIPAT_ENVIRONMENT.upper() if Settings().VIPAT_ENVIRONMENT else "DEV")
        )

        if environment not in ["DEV", "TEST", "PROD"]:
            raise ValueError("Invalid environment provided. Please provide a valid environment: 'DEV', 'TEST', 'PROD'.")

        self.logger.debug(f"Environment set to '{environment}'.")

        # --- Setup VideoIPath API Connector ---
        self.logger.debug("Initialize VideoIPath API Connector.")

        if server_address is None and Settings().VIPAT_VIDEOIPATH_SERVER_ADDRESS is None:
            raise ValueError(
                "No address provided. Please provide an address or set it as an environment variable: 'VIPAT_VIDEOIPATH_SERVER_ADDRESS'."
            )
        vip_server_address = (
            server_address if server_address is not None else Settings().VIPAT_VIDEOIPATH_SERVER_ADDRESS
        )
        self.logger.debug(f"Server address: '{vip_server_address}'")

        if username is None and Settings().VIPAT_VIDEOIPATH_USERNAME is None:
            raise ValueError(
                "No username provided. Please provide a username or set it as an environment variable: 'VIPAT_VIDEOIPATH_USERNAME'."
            )
        vip_username = username if username is not None else Settings().VIPAT_VIDEOIPATH_USERNAME
        self.logger.debug(f"Username: '{vip_username}'")

        if password is None and Settings().VIPAT_VIDEOIPATH_PASSWORD is None:
            raise ValueError(
                "No password provided. Please provide a password or set it as an environment variable: 'VIPAT_VIDEOIPATH_PASSWORD'."
            )
        vip_password = password if password is not None else Settings().VIPAT_VIDEOIPATH_PASSWORD
        self.logger.debug("Password provided!")

        use_https = use_https if use_https is not None else Settings().VIPAT_USE_HTTPS
        self.logger.debug("HTTPS enabled.") if use_https else self.logger.debug("HTTP enabled.")

        verify_ssl_cert = verify_ssl_cert if verify_ssl_cert is not None else Settings().VIPAT_VERIFY_SSL_CERT
        if use_https:
            self.logger.debug("Verify SSL certificate enabled.") if verify_ssl_cert else self.logger.debug(
                "Verify SSL certificate disabled."
            )

        # --- Initialize VideoIPath API Connector including check for connection and authentication ---
        self._videoipath_connector = VideoIPathConnector(
            server_address=vip_server_address,
            username=vip_username,
            password=vip_password,
            use_https=use_https,
            verify_ssl_cert=verify_ssl_cert,
            logger=self.logger,
        )

        # --- Initialize Apps ---
        self._inventory = InventoryApp(vip_connector=self._videoipath_connector, logger=self.logger)

        self._topology = TopologyApp(vip_connector=self._videoipath_connector, logger=self.logger)

        self._preferences = PreferencesApp(vip_connector=self._videoipath_connector, logger=self.logger)

        self._profile = ProfileApp(vip_connector=self._videoipath_connector, logger=self.logger)

        # --- Development ---
        if environment == "DEV":
            self.logger.debug("Development environment detected. Initializing API classes for development ...")

            self._inventory_api = InventoryAPI(vip_connector=self._videoipath_connector)
            self.logger.debug("Inventory API initialized.")

            self._topology_api = TopologyAPI(vip_connector=self._videoipath_connector)
            self.logger.debug("Topology API initialized.")

            self._preferences_api = PreferencesAPI(vip_connector=self._videoipath_connector)
            self.logger.debug("Preferences API initialized.")

            self._profile_api = ProfileAPI(vip_connector=self._videoipath_connector)
            self.logger.debug("Profile API initialized.")

        self.logger.info("VideoIPath Automation Tool successfully initialized.")

    # def demo_method_using_multiple_apps(self):
    #     self._inventory.create_device()                            # (not a real method, just for demonstration)
    #     self._inspect.move_device_relative(100, 100, "device371")

    # Getter for Apps to access the functionality from outside the class
    @property
    def inventory(self):
        return self._inventory

    # @property
    # def inspect(self):
    #     return self._inspect

    @property
    def topology(self):
        return self._topology

    @property
    def preferences(self):
        return self._preferences

    @property
    def profile(self):
        return self._profile

    # # --- Development ---
    # if Settings().ENVIRONMENT and Settings().ENVIRONMENT.upper() == "DEV":
    #     @property
    #     def inventory_api(self):
    #         return self._inventory_api

    #     @property
    #     def topology_api(self):
    #         return self._topology_api
