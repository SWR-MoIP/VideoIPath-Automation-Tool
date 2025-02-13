import logging
from typing import Optional

from videoipath_automation_tool.apps.inventory.inventory_app import InventoryApp
from videoipath_automation_tool.apps.preferences.preferences_app import PreferencesApp
from videoipath_automation_tool.apps.profile.profile_app import ProfileApp
from videoipath_automation_tool.apps.topology.topology_app import TopologyApp
from videoipath_automation_tool.connector.vip_connector import VideoIPathConnector
from videoipath_automation_tool.settings import Settings


class VideoIPathApp:
    def __init__(
        self,
        server_address: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_https: Optional[bool] = None,
        verify_ssl_cert: Optional[bool] = None,
        log_level: Optional[str] = None,
        environment: Optional[str] = None,
    ):
        """Main class for VideoIPath Automation Tool.
        VideoIPathApp contains all Apps and methods to interact with the VideoIPath System.

        Initialize the VideoIPath Automation Tool, establish connection to the VideoIPath-Server and initialize the Apps for interaction.
        Parameters can be provided directly or read from the environment variables.

        Args:
            server_address (str, optional): IP or hostname of the VideoIPath-Server. [ENV: VIPAT_VIDEOIPATH_SERVER_ADDRESS]
            username (str, optional): Username for the API User. [ENV: VIPAT_VIDEOIPATH_USERNAME]
            password (str, optional): Password for the API User. [ENV: VIPAT_VIDEOIPATH_PASSWORD]
            use_https (bool, optional): Set to `True` if the VideoIPath Server uses HTTPS. [ENV: VIPAT_USE_HTTPS]
            verify_ssl_cert (bool, optional): Set to `True` if the SSL certificate should be verified. [ENV: VIPAT_VERIFY_SSL_CERT]
            log_level (str, optional): The log level for the logging module, possible values are `DEBUG`, `INFO`, `WARNING`, `ERROR`, and `CRITICAL`. [ENV: VIPAT_LOG_LEVEL]
            environment (str, optional): Define the environment: `DEV`, `TEST`, `PROD`. [ENV: VIPAT_ENVIRONMENT]
        """

        # --- Load environment variables ---
        _settings = Settings()

        # --- Setup Logging ---
        log_level = (
            log_level.upper()
            if log_level
            else (_settings.VIPAT_LOG_LEVEL.upper() if _settings.VIPAT_LOG_LEVEL else "INFO")
        )

        if log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError(
                "Invalid log level provided. Please provide a valid log level: 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'."
            )

        logging.basicConfig(level=log_level)

        self._logger = logging.getLogger("videoipath_automation_tool")

        # --- Setup Environment ---
        environment = (
            environment.upper()
            if environment
            else (_settings.VIPAT_ENVIRONMENT.upper() if _settings.VIPAT_ENVIRONMENT else "DEV")
        )

        if environment not in ["DEV", "TEST", "PROD"]:
            raise ValueError("Invalid environment provided. Please provide a valid environment: 'DEV', 'TEST', 'PROD'.")

        self._logger.debug(f"Environment set to '{environment}'.")

        # --- Initialize VideoIPath API Connector including check for connection and authentication ---
        self._logger.debug("Initialize VideoIPath API Connector.")

        if server_address is None and _settings.VIPAT_VIDEOIPATH_SERVER_ADDRESS is None:
            raise ValueError(
                "No address provided. Please provide an address or set it as an environment variable: 'VIPAT_VIDEOIPATH_SERVER_ADDRESS'."
            )
        _vip_server_address = (
            server_address if server_address is not None else _settings.VIPAT_VIDEOIPATH_SERVER_ADDRESS
        )
        self._logger.debug(f"Server address: '{_vip_server_address}'")

        if username is None and _settings.VIPAT_VIDEOIPATH_USERNAME is None:
            raise ValueError(
                "No username provided. Please provide a username or set it as an environment variable: 'VIPAT_VIDEOIPATH_USERNAME'."
            )
        _vip_username = username if username is not None else _settings.VIPAT_VIDEOIPATH_USERNAME
        self._logger.debug(f"Username: '{_vip_username}'")

        if password is None and _settings.VIPAT_VIDEOIPATH_PASSWORD is None:
            raise ValueError(
                "No password provided. Please provide a password or set it as an environment variable: 'VIPAT_VIDEOIPATH_PASSWORD'."
            )
        _vip_password = password if password is not None else _settings.VIPAT_VIDEOIPATH_PASSWORD
        self._logger.debug("Password provided!")

        use_https = use_https if use_https is not None else _settings.VIPAT_USE_HTTPS
        self._logger.debug("HTTPS enabled.") if use_https else self._logger.debug("HTTP enabled.")

        verify_ssl_cert = verify_ssl_cert if verify_ssl_cert is not None else _settings.VIPAT_VERIFY_SSL_CERT
        if use_https:
            self._logger.debug("Verify SSL certificate enabled.") if verify_ssl_cert else self._logger.debug(
                "Verify SSL certificate disabled."
            )

        if _vip_server_address is None:
            raise ValueError("No server address provided. Please provide a server address.")

        if not _vip_username:
            raise ValueError("No username provided. Please provide a username.")

        if not _vip_password:
            raise ValueError("No password provided. Please provide a password.")

        self._videoipath_connector = VideoIPathConnector(
            server_address=_vip_server_address,
            username=_vip_username,
            password=_vip_password,
            use_https=use_https,
            verify_ssl_cert=verify_ssl_cert,
            logger=self._logger,
        )

        # --- Reset the variables and settings ---
        del server_address, _vip_server_address
        del username, _vip_username
        del password, _vip_password
        del use_https
        del verify_ssl_cert
        del log_level

        # --- Initialize Apps ---
        self.inventory = InventoryApp(vip_connector=self._videoipath_connector, logger=self._logger)
        self.topology = TopologyApp(vip_connector=self._videoipath_connector, logger=self._logger)
        self.preferences = PreferencesApp(vip_connector=self._videoipath_connector, logger=self._logger)
        self.profile = ProfileApp(vip_connector=self._videoipath_connector, logger=self._logger)

        # --- For Development, map the internal methods to the VideoIPathApp ---
        if environment == "DEV":
            self._inventory_api = self.inventory._inventory_api
            self._topology_api = self.topology._topology_api
            self._preferences_api = self.preferences._preferences_api
            self._profile_api = self.profile._profile_api

        self._logger.info("VideoIPath Automation Tool initialized.")

    # def demo_method_using_multiple_apps(self):
    #     self._inventory.create_device()                            # (not a real method, just for demonstration)
    #     self._inspect.move_device_relative(100, 100, "device371")
