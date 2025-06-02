import logging
from typing import Literal, Optional

from videoipath_automation_tool.apps.inventory import InventoryApp
from videoipath_automation_tool.apps.inventory.model.drivers import AVAILABLE_SCHEMA_VERSIONS, SELECTED_SCHEMA_VERSION
from videoipath_automation_tool.apps.preferences.preferences_app import PreferencesApp
from videoipath_automation_tool.apps.profile.profile_app import ProfileApp
from videoipath_automation_tool.apps.topology.topology_app import TopologyApp
from videoipath_automation_tool.connector.vip_connector import VideoIPathConnector
from videoipath_automation_tool.settings import Settings
from videoipath_automation_tool.utils.driver_schema_comparison import (
    DriverSchemaComparator,
    load_driver_schema_from_file,
)


class VideoIPathApp:
    """Main class for VideoIPath Automation Tool.
    VideoIPathApp contains all Apps and methods to interact with the VideoIPath System.
    """

    def __init__(
        self,
        server_address: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_https: Optional[bool] = None,
        verify_ssl_cert: Optional[bool] = None,
        log_level: Optional[Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]] = None,
        environment: Optional[str] = None,
        advanced_driver_schema_check: Optional[bool] = None,
        timeout_http_get: Optional[int] = None,
        timeout_http_patch: Optional[int] = None,
        timeout_http_post: Optional[int] = None,
    ):
        """
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
            advanced_driver_schema_check (bool, optional): Enable advanced driver schema check, which contains comparison of the driver schema (custom fields) with the fetched driver schema from the VideoIPath Server. [ENV: VIPAT_ADVANCED_DRIVER_SCHEMA_CHECK]
            timeout_http_get (int, optional): Timeout for HTTP GET requests in seconds. [ENV: VIPAT_TIMEOUT_HTTP_GET]
            timeout_http_patch (int, optional): Timeout for HTTP PATCH requests in seconds. [ENV: VIPAT_TIMEOUT_HTTP_PATCH]
            timeout_http_post (int, optional): Timeout for HTTP POST requests in seconds. [ENV: VIPAT_TIMEOUT_HTTP_POST]
        """

        # --- Load environment variables ---
        _settings = Settings()

        # --- Setup Logging ---
        root_logger = logging.getLogger()  # get root logger to set global log level as fallback

        log_level = (
            log_level.upper()
            if log_level
            else (
                _settings.VIPAT_LOG_LEVEL.upper()
                if _settings.VIPAT_LOG_LEVEL
                else logging.getLevelName(root_logger.level)
            )
        )  # type: ignore

        if log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError(
                "Invalid log level provided. Please provide a valid log level: 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'."
            )

        self._logger = logging.getLogger("videoipath_automation_tool")

        if not self._logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(levelname)s:%(asctime)s:%(name)s:%(message)s")
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)
            self._logger.propagate = False

        self._logger.setLevel(log_level)

        # --- Setup Environment ---
        environment = (
            environment.upper()
            if environment
            else (_settings.VIPAT_ENVIRONMENT.upper() if _settings.VIPAT_ENVIRONMENT else "DEV")
        )

        if environment not in ["DEV", "TEST", "PROD"]:
            raise ValueError("Invalid environment provided. Please provide a valid environment: 'DEV', 'TEST', 'PROD'.")

        self._logger.debug(f"Environment set to '{environment}'.")

        # --- Setup Advanced Driver Schema Check ---
        advanced_driver_schema_check = (
            advanced_driver_schema_check
            if advanced_driver_schema_check is not None
            else _settings.VIPAT_ADVANCED_DRIVER_SCHEMA_CHECK
        )

        # --- Setup Timeouts ---
        timeout_http_get = timeout_http_get if timeout_http_get is not None else _settings.VIPAT_TIMEOUT_HTTP_GET
        self._logger.debug(f"HTTP GET timeout set to {timeout_http_get} seconds.")
        if timeout_http_get <= 0:
            raise ValueError("HTTP GET timeout must be greater than 0 seconds.")
        if timeout_http_get <= 5:
            self._logger.warning(
                f"HTTP GET timeout is set to a low value ({timeout_http_get} seconds). This may lead to timeouts during API requests."
            )

        timeout_http_patch = (
            timeout_http_patch if timeout_http_patch is not None else _settings.VIPAT_TIMEOUT_HTTP_PATCH
        )
        self._logger.debug(f"HTTP PATCH timeout set to {timeout_http_patch} seconds.")
        if timeout_http_patch <= 0:
            raise ValueError("HTTP PATCH timeout must be greater than 0 seconds.")
        if timeout_http_patch <= 5:
            self._logger.warning(
                f"HTTP PATCH timeout is set to a low value ({timeout_http_patch} seconds). This may lead to timeouts during API requests."
            )

        timeout_http_post = timeout_http_post if timeout_http_post is not None else _settings.VIPAT_TIMEOUT_HTTP_POST
        self._logger.debug(f"HTTP POST timeout set to {timeout_http_post} seconds.")
        if timeout_http_post <= 0:
            raise ValueError("HTTP POST timeout must be greater than 0 seconds.")
        if timeout_http_post <= 5:
            self._logger.warning(
                f"HTTP POST timeout is set to a low value ({timeout_http_post} seconds). This may lead to timeouts during API requests."
            )

        # --- Initialize VideoIPath API Connector including check for connection and authentication ---
        self._logger.debug("Initialize VideoIPath API Connector.")

        _vip_server_address = (
            server_address if server_address is not None else _settings.VIPAT_VIDEOIPATH_SERVER_ADDRESS
        )
        self._logger.debug(f"Server address: '{_vip_server_address}'")

        _vip_username = username if username is not None else _settings.VIPAT_VIDEOIPATH_USERNAME
        self._logger.debug(f"Username: '{_vip_username}'")

        _vip_password = password if password is not None else _settings.VIPAT_VIDEOIPATH_PASSWORD
        if _vip_password:
            self._logger.debug("Password provided!")

        use_https = use_https if use_https is not None else _settings.VIPAT_USE_HTTPS
        self._logger.debug("HTTPS enabled.") if use_https else self._logger.debug("HTTP enabled.")

        verify_ssl_cert = verify_ssl_cert if verify_ssl_cert is not None else _settings.VIPAT_VERIFY_SSL_CERT
        if use_https:
            self._logger.debug("Verify SSL certificate enabled.") if verify_ssl_cert else self._logger.debug(
                "Verify SSL certificate disabled."
            )

        if _vip_server_address is None:
            raise ValueError(
                "No address provided. Please provide an address or set it as an environment variable: 'VIPAT_VIDEOIPATH_SERVER_ADDRESS'."
            )

        if not _vip_username:
            raise ValueError(
                "No username provided. Please provide a username or set it as an environment variable: 'VIPAT_VIDEOIPATH_USERNAME'."
            )

        if not _vip_password:
            raise ValueError(
                "No password provided. Please provide a password or set it as an environment variable: 'VIPAT_VIDEOIPATH_PASSWORD'."
            )

        self._videoipath_connector = VideoIPathConnector(
            server_address=_vip_server_address,
            username=_vip_username,
            password=_vip_password,
            use_https=use_https,
            verify_ssl_cert=verify_ssl_cert,
            logger=self._logger,
            timeout_http_get=timeout_http_get,
            timeout_http_patch=timeout_http_patch,
            timeout_http_post=timeout_http_post,
        )

        # --- Reset the variables ---
        server_address = None
        _vip_server_address = None
        username = None
        _vip_username = None
        password = None
        _vip_password = None
        use_https = None
        verify_ssl_cert = None
        log_level = None
        _settings = None

        del server_address, _vip_server_address
        del username, _vip_username
        del password, _vip_password
        del use_https
        del verify_ssl_cert
        del log_level
        del _settings

        # --- Check Driver Schema Version ---
        self._logger.debug(
            "Advanced driver schema check enabled."
            if advanced_driver_schema_check
            else "Advanced driver schema check disabled. Only basic version check will be performed."
        )
        self._basic_version_check()

        if advanced_driver_schema_check:
            self._advanced_driver_schema_check()

        # --- Initialize App placeholders ---
        self._inventory = None
        self._topology = None
        self._preferences = None
        self._profile = None

        self._logger.info("VideoIPath Automation Tool initialized.")

        # --- For Development Environment, load the APIs directly and map them to the VideoIPathApp for easier access ---
        if environment == "DEV":
            self._inventory_api = self.inventory._inventory_api
            self._topology_api = self.topology._topology_api
            self._preferences_api = self.preferences._preferences_api
            self._profile_api = self.profile._profile_api

    # --- Getters to enable lazy loading ---
    @property
    def inventory(self):
        if self._inventory is None:
            self._logger.debug("InventoryApp first called. Initialize InventoryApp.")
            self._inventory = InventoryApp(vip_connector=self._videoipath_connector, logger=self._logger)
        return self._inventory

    @property
    def topology(self):
        if self._topology is None:
            self._logger.debug("TopologyApp first called. Initialize TopologyApp.")
            self._topology = TopologyApp(vip_connector=self._videoipath_connector, logger=self._logger)
        return self._topology

    @property
    def preferences(self):
        if self._preferences is None:
            self._logger.debug("PreferencesApp first called. Initialize PreferencesApp.")
            self._preferences = PreferencesApp(vip_connector=self._videoipath_connector, logger=self._logger)
        return self._preferences

    @property
    def profile(self):
        if self._profile is None:
            self._logger.debug("ProfileApp first called. Initialize ProfileApp.")
            self._profile = ProfileApp(vip_connector=self._videoipath_connector, logger=self._logger)
        return self._profile

    # --- Basic Methods ---
    def _determine_fallback_driver_schema_version(self) -> Optional[str]:
        """
        Determine the fallback driver schema version based on the VideoIPath Server version.

        Returns:
            Optional[str]: The fallback driver schema version or None if no fallback is needed.
        """
        server_version = self.get_server_version()
        self._logger.debug(f"VideoIPath Server version: {server_version}")

        if server_version in AVAILABLE_SCHEMA_VERSIONS:
            return None  # No fallback needed, the server version is supported.

        fallback_version = (
            AVAILABLE_SCHEMA_VERSIONS[-1]
            if server_version > AVAILABLE_SCHEMA_VERSIONS[-1]
            else AVAILABLE_SCHEMA_VERSIONS[0]
        )
        return fallback_version

    def _basic_version_check(self):
        """Log compatibility status between the VideoIPath Server version and the selected driver schema version."""
        server_version = self.get_server_version()
        if server_version == SELECTED_SCHEMA_VERSION:
            self._logger.debug(
                f"VideoIPath Server version matches the driver schema version: {SELECTED_SCHEMA_VERSION}."
            )
            return

        if server_version in AVAILABLE_SCHEMA_VERSIONS:
            self._logger.warning(
                f"VideoIPath Server version '{server_version}' is supported but does not match the driver schema version '{SELECTED_SCHEMA_VERSION}'. Please run `set-videoipath-version {server_version}` to set the correct schema version.",
            )
            return

        self._logger.warning(
            f"VideoIPath Server version '{server_version}' is not natively supported. "
            f"A fallback driver schema version may be used, or support for this version can be requested. "
            f"To request support, open an issue at: https://github.com/SWR-MoIP/VideoIPath-Automation-Tool/issues"
        )
        fallback_version = self._determine_fallback_driver_schema_version()
        if fallback_version:
            if fallback_version == SELECTED_SCHEMA_VERSION:
                self._logger.warning(
                    f"The selected driver schema '{SELECTED_SCHEMA_VERSION}' already matches the determined fallback version."
                )
            else:
                self._logger.warning(
                    f"Fallback driver schema version determined: {fallback_version}. To apply it, run `set-videoipath-version {fallback_version}`."
                )

    def _advanced_driver_schema_check(self):
        self._logger.debug("Starting advanced driver schema check.")

        try:
            local_schema = load_driver_schema_from_file(SELECTED_SCHEMA_VERSION)
            self._logger.debug(f"Local driver schema loaded successfully: {SELECTED_SCHEMA_VERSION}")
        except Exception as e:
            self._logger.warning(f"Failed to load local driver schema: {e}, skipping advanced driver schema checks.")
            return

        try:
            server_schema = self._videoipath_connector.fetch_driver_schema_from_server()
            server_version = self.get_server_version()
            self._logger.debug(f"Driver schema fetched from VideoIPath Server: {server_version}")
        except Exception as e:
            self._logger.warning(
                f"Failed to fetch driver schema from the VideoIPath server: {e}, skipping advanced driver schema checks."
            )
            return

        try:
            comparison_result = DriverSchemaComparator.compare_driver_schemas(
                compare_schema=local_schema, reference_schema=server_schema
            )
        except Exception as e:
            self._logger.error(f"Error during driver schema comparison: {e}")
            return

        if comparison_result:
            if DriverSchemaComparator.missmatch_in_driver_schema(comparison_result=comparison_result):
                self._logger.warning(
                    "Advanced driver schema check found mismatches between the server and local driver schemas:"
                    f"{comparison_result}"
                )
            else:
                self._logger.debug(
                    "Advanced driver schema check found no mismatches between the server and local driver schemas."
                )

    def get_server_version(self) -> str:
        """Get the VideoIPath Server version.

        Returns:
            str: The VideoIPath Server version (e.g. '2024.1.4').
        """
        return self._videoipath_connector.videoipath_version

    def check_connection(self):
        """Check the connection to the VideoIPath Server including authentication.

        Raises:
            ConnectionError: If the connection to the VideoIPath Server failed.
        """
        rpc_connection = self._videoipath_connector.rpc.is_connected()
        rest_connection = self._videoipath_connector.rest.is_connected()
        rpc_authenticated = self._videoipath_connector.rpc.is_authenticated()
        rest_authenticated = self._videoipath_connector.rest.is_authenticated()

        if rpc_connection and rest_connection and rpc_authenticated and rest_authenticated:
            self._logger.info("Connection to VideoIPath Server successful.")
        else:
            raise ConnectionError("Connection to VideoIPath Server failed.")

    def help(self):
        help_message = """
        For more information, please visit the GitHub repository:
        https://github.com/SWR-MoIP/VideoIPath-Automation-Tool
        """
        print(help_message)
        return help_message
