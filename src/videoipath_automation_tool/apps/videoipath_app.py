import logging

from videoipath_automation_tool.apps.inventory.inventory_app import InventoryApp
from videoipath_automation_tool.apps.preferences.preferences_app import PreferencesApp
from videoipath_automation_tool.apps.profile.profile_app import ProfileApp
from videoipath_automation_tool.apps.topology.topology_app import TopologyApp
from videoipath_automation_tool.connector.vip_connector import VideoIPathConnector
from videoipath_automation_tool.settings import Settings


class VideoIPathApp:
    """Main class for VideoIPath Automation Tool.
    VideoIPathApp contains all Apps and methods to interact with the VideoIPath System.
    """

    def __init__(
        self,
        server_address: str | None = None,
        username: str | None = None,
        password: str | None = None,
        use_https=None,
        verify_ssl_cert=None,
        log_level: str | None = None,
        environment=None,
    ):
        """Initialize the VideoIPath Automation Tool, establish connection to the VideoIPath-Server and initialize the Apps for interaction.
        Parameters can be provided directly or read from the environment variables.

        Args:
            server_address (str, optional): IP or hostname of the VideoIPath-Server. [ENV: VIPAT_VIDEOIPATH_SERVER_ADDRESS]
            username (str, optional): Username for the API User. [ENV: VIPAT_VIDEOIPATH_USERNAME]
            password (str, optional): Password for the API User. [ENV: VIPAT_VIDEOIPATH_PASSWORD]
            use_https (bool, optional): Set to `True` if the VideoIPath Server uses HTTPS. [ENV: VIPAT_USE_HTTPS]
            verify_ssl_cert (bool, optional): Set to `True` if the SSL certificate should be verified. [ENV: VIPAT_VERIFY_SSL_CERT]
            log_level (str, optional): The log level for the logging module, possible values are `DEBUG`, `INFO`, `WARNING`, `ERROR`, and `CRITICAL`. [ENV: VIPAT_LOG_LEVEL]
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
        if vip_server_address is None:
            raise ValueError("No server address provided. Please provide a server address.")

        if not vip_username:
            raise ValueError("No username provided. Please provide a username.")

        if not vip_password:
            raise ValueError("No password provided. Please provide a password.")

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
            self.logger.debug("Development environment configured, map API Methods to VidoIPathApp for easier access.")
            self.inventory_api = self._inventory._inventory_api
            self.topology_api = self._topology._topology_api
            self.preferences_api = self._preferences._preferences_api
            self.profile_api = self._profile._profile_api

        self.logger.info("VideoIPath Automation Tool initialized.")

    # def demo_method_using_multiple_apps(self):
    #     self._inventory.create_device()                            # (not a real method, just for demonstration)
    #     self._inspect.move_device_relative(100, 100, "device371")

    # --- Getters ---
    @property
    def inventory(self):
        return self._inventory

    @property
    def topology(self):
        return self._topology

    @property
    def preferences(self):
        return self._preferences

    @property
    def profile(self):
        return self._profile
