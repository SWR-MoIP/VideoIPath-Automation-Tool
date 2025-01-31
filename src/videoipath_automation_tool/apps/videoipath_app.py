# External Imports
import logging

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
        self, ip=None, username=None, password=None, ssl=None, ssl_verify=None, log_level=None, environment=None
    ):
        """Initialize the VideoIPath Automation Tool, establish connection to the VideoIPath-Server and initialize the Apps for interaction.
        Parameters can be provided directly or read from the environment variables.

        Args:
            ip (str, optional): IP or hostname of the VideoIPath-Server. [ENV: VIPAT_VIDEOIPATH_IP]
            username (str, optional): Username for the API User. [ENV: VIPAT_VIDEOIPATH_USER]
            password (str, optional): Password for the API User. [ENV: VIPAT_VIDEOIPATH_PWD]
            ssl (bool, optional): Enable SSL / Usage of HTTPS. [ENV: VIPAT_HTTPS]
            ssl_verify (bool, optional): Enable SSL verification. [ENV: VIPAT_HTTPS_VERIFY]
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

        self.logger.debug(f"Environment set to '{environment}' environment.")

        # --- Setup VideoIPath API Connector ---
        self.logger.debug("Initialize VideoIPath API Connector.")

        if ip is None and Settings().VIPAT_VIDEOIPATH_IP is None:
            raise ValueError(
                "No IP address provided. Please provide an IP address or set it as an environment variable: 'VIPAT_VIDEOIPATH_IP'."
            )
        vip_ip = ip if ip is not None else Settings().VIPAT_VIDEOIPATH_IP
        self.logger.debug(f"VideoIPath-Server IP: {vip_ip}")

        if username is None and Settings().VIPAT_VIDEOIPATH_USER is None:
            raise ValueError(
                "No username provided. Please provide a username or set it as an environment variable: 'VIPAT_VIDEOIPATH_USER'."
            )
        vip_username = username if username is not None else Settings().VIPAT_VIDEOIPATH_USER
        self.logger.debug(f"Username: {vip_username}")

        if password is None and Settings().VIPAT_VIDEOIPATH_PWD is None:
            raise ValueError(
                "No password provided. Please provide a password or set it as an environment variable: 'VIPAT_VIDEOIPATH_PWD'."
            )
        vip_password = password if password is not None else Settings().VIPAT_VIDEOIPATH_PWD
        self.logger.debug("Password provided!")

        ssl = ssl if ssl is not None else Settings().VIPAT_HTTPS
        self.logger.debug("SSL enabled.") if ssl else self.logger.debug("SSL disabled.")

        ssl_verify = ssl_verify if ssl_verify is not None else Settings().VIPAT_HTTPS_VERIFY
        if ssl:
            self.logger.debug("SSL verification enabled.") if ssl_verify else self.logger.debug(
                "SSL verification disabled."
            )

        # Initialize VideoIPath API Connector
        self._videoipath_connector = VideoIPathConnector(
            ip=vip_ip, username=vip_username, password=vip_password, ssl=ssl, ssl_verify=ssl_verify, logger=self.logger
        )

        # Check connection
        if self._videoipath_connector.test_connection():
            version = self._videoipath_connector.videoipath_version  # Initially get the VideoIPath version
            self.logger.info(
                f"Connection to VideoIPath-Server at '{self._videoipath_connector.ip}' with user '{self._videoipath_connector.username}' established."
            )
            self.logger.debug(f"VideoIPath-Server version: {version}")
        else:
            self.logger.error(
                f"Connection to VideoIPath-Server at '{self._videoipath_connector.ip}' with user '{self._videoipath_connector.username}' failed."
            )
            raise ConnectionError("Connection to VideoIPath-Server failed.")

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
