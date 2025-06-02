import logging
from typing import Optional

from videoipath_automation_tool.connector.vip_base_connector import VideoIPathBaseConnectorTimeouts
from videoipath_automation_tool.connector.vip_rest_connector import (
    VideoIPathRestConnector,
)
from videoipath_automation_tool.connector.vip_rpc_connector import (
    VideoIPathRPCConnector,
)
from videoipath_automation_tool.utils.cross_app_utils import create_fallback_logger


class VideoIPathConnector:
    def __init__(
        self,
        server_address: str,
        username: str,
        password: str,
        use_https: bool = True,
        verify_ssl_cert: bool = True,
        logger: Optional[logging.Logger] = None,
        timeout_http_get: int = 10,
        timeout_http_patch: int = 10,
        timeout_http_post: int = 10,
    ):
        """
        Low-level HTTP client for the VideoIPath API with support for REST v2 and RPC calls.
        Authentication is handled via Basic Authentication.

        This class provides methods to send REST v2 GET and PATCH requests, as well as RPC POST
        requests to a VideoIPath server. Additionally, it offers functionality to verify
        connection and authentication status.

        Args:
            server_address (str): The IP address or url of the VideoIPath server.
            username (str): Username for authentication.
            password (str): Password for authentication.
            use_https (bool): If `True`, HTTPS is used for the connection (default: `True`).
            verify_ssl_cert (bool): If `True`, SSL certificate verification is enabled (default: `True`).
            logger (Optional[logging.Logger]): Logger instance. If `None`, a fallback logger is used.
        """
        self._logger = logger or create_fallback_logger("videoipath_automation_tool_connector")
        self._videoipath_version = ""

        timeouts = VideoIPathBaseConnectorTimeouts(
            get=timeout_http_get,
            patch=timeout_http_patch,
            post=timeout_http_post,
        )

        self._rest_connector = VideoIPathRestConnector(
            server_address=server_address,
            username=username,
            password=password,
            use_https=use_https,
            verify_ssl_cert=verify_ssl_cert,
            logger=self._logger,
            timeouts=timeouts,
        )
        self._rpc_connector = VideoIPathRPCConnector(
            server_address=server_address,
            username=username,
            password=password,
            use_https=use_https,
            verify_ssl_cert=verify_ssl_cert,
            logger=self._logger,
            timeouts=timeouts,
        )

        self._logger.debug("VideoIPath Connectors initialized.")

    def refresh_videoipath_version(self):
        """Method to refresh the VideoIPath version attribute."""
        try:
            response = self.rest.get("/rest/v2/data/status/system/about/version", auth_check=False)
            version = response.data["status"]["system"]["about"]["version"]
            self._videoipath_version = version
        except Exception as error:
            error_message = f"Error while fetching VideoIPath version: {error}"
            raise Exception(error_message)

    def fetch_driver_schema_from_server(self) -> list[dict]:
        """
        Fetches the driver schema from the VideoIPath server.

        Returns:
            list[dict]: A list of driver schema entries.
        """
        try:
            response = self.rest.get("/rest/v2/data/status/system/drivers/**")
            return response.data["status"]["system"]["drivers"]["_items"]
        except Exception as error:
            error_message = f"Error while fetching driver schema from server: {error}"
            raise Exception(error_message)

    # --- Getter and Setter ---

    @property
    def rest(self) -> VideoIPathRestConnector:
        return self._rest_connector

    @property
    def rpc(self) -> VideoIPathRPCConnector:
        return self._rpc_connector

    @property
    def videoipath_version(self) -> str:
        if self._videoipath_version == "":
            self.refresh_videoipath_version()
        return self._videoipath_version
