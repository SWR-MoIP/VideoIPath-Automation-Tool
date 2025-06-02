import json
import logging
from abc import ABC, abstractmethod
from typing import Optional

import requests


class VideoIPathBaseConnectorTimeouts:
    """Timeouts for VideoIPath API requests."""

    def __init__(self, get: int = 10, patch: int = 10, post: int = 10):
        """
        Initializes the timeouts for VideoIPath API requests.

        Args:
            get (int): Timeout for GET requests in seconds (default: 10).
            patch (int): Timeout for PATCH requests in seconds (default: 10).
            post (int): Timeout for POST requests in seconds (default: 10).
        """
        self.get = get
        self.patch = patch
        self.post = post


class VideoIPathBaseConnector(ABC):
    def __init__(
        self,
        server_address: str,
        username: str,
        password: str,
        logger: logging.Logger,
        timeouts: VideoIPathBaseConnectorTimeouts,
        use_https: bool = True,
        verify_ssl_cert: bool = True,
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
        self._username = username
        self._password = password
        self._logger = logger
        self.use_https = use_https
        self.verify_ssl_cert = verify_ssl_cert
        self._videoipath_version = ""
        self.timeouts = timeouts

        self.server_address = self._parse_server_address(
            server_address
        )  # Server address has to be set after use_https, because address might change use_https setting

        self._validate_and_initialize_connector()
        self._logger.debug(f"{self.__class__.__name__} initialized.")

    @abstractmethod
    def is_connected(self) -> bool:
        """Method to test the connection to the VideoIPath API.

        Returns:
            bool: True if connection successful, False otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    def is_authenticated(self) -> bool:
        """Method to test the authentication to the VideoIPath API.

        Returns:
            bool: True if authentication successful, False otherwise.
        """
        raise NotImplementedError

    # --- Internal methods ---

    def _validate_and_initialize_connector(self):
        if not self.server_address:
            raise ValueError("Server address is required.")

        if not self._username:
            raise ValueError("Username is required.")

        if not self._password:
            raise ValueError("Password is required.")

        self._logger.debug(
            f"Testing connection to VideoIPath-Server with address: '{self.server_address}', username: '{self._username}' and provided password (Use HTTPS: '{self.use_https}', Verify SSL Cert: '{self.verify_ssl_cert}')."
        )

        if not self.is_connected():
            raise ConnectionError("Connection to VideoIPath failed.")

        if not self.is_authenticated():
            raise PermissionError("Authentication to VideoIPath failed.")

        self._logger.debug("Connection and authentication to VideoIPath successful.")

    def _build_url(self, url_path: str) -> str:
        """Builds the full API URL.

        Args:
            url_path (str): The relative URL path. E.g., "/rest/v2/data/status/system/about/version"

        Returns:
            str: The full URL. E.g., "https://vip.company.com/rest/v2/data/status/system/about/version"
        """
        return f"{self.base_url.rstrip('/')}/{url_path.lstrip('/')}"

    def _handle_request_exceptions(self, url: str, exception: Exception):
        """Handles exceptions raised during an HTTP request."""
        if isinstance(exception, requests.exceptions.Timeout):
            raise TimeoutError(f"Timeout while requesting '{url}'")
        elif isinstance(exception, requests.exceptions.ConnectionError):
            raise ConnectionError(f"Connection error while requesting '{url}'")
        else:
            raise requests.RequestException(f"General request error for '{url}': {exception}")

    def _log_response(self, response: requests.Response):
        """Logs the HTTP response."""
        try:
            self._logger.debug(f"HTTP Response [{response.status_code}]: {response.json()}")
        except json.JSONDecodeError:
            self._logger.debug(f"HTTP Response [{response.status_code}] (RAW): {response.text}")
        self._logger.debug(f"HTTP Response Headers: {response.headers}")

    def _execute_request(
        self, method: str, url: str, timeout: int, request_payload: Optional[dict] = None
    ) -> requests.Response:
        """Executes an HTTP request and returns the response."""

        handlers = {
            "GET": requests.get,
            "PATCH": requests.patch,
            "POST": requests.post,
        }

        request_config = {
            "url": url,
            "auth": (self._username, self._password),
            "timeout": timeout,
            "verify": self.verify_ssl_cert,
            "headers": {"Content-Type": "application/json", "Accept-Encoding": "gzip, deflate"},
        }

        try:
            handle_request = handlers[method]
            if method == "GET":
                response = handle_request(**request_config)
            else:
                response = handle_request(
                    **request_config,
                    data=json.dumps(request_payload) if request_payload else None,
                )
        except KeyError:
            self._handle_request_exceptions(url, Exception(f"Unsupported HTTP method: {method}"))
        except Exception as e:
            self._handle_request_exceptions(url, e)

        self._log_response(response)

        if not response.ok:
            raise Exception(f"Error in API response for path {url}: {response.status_code}, {response.reason}")

        return response

    def _parse_server_address(self, server_address: str) -> str:
        if server_address.startswith("http://"):
            server_address = server_address.removeprefix("http://")
            self._logger.debug("Server address contains 'http://'. Removed.")
        elif server_address.startswith("https://"):
            server_address = server_address.removeprefix("https://")

            if not self.use_https:
                self._logger.warning("Server address contains 'https://' but HTTPS is not set. Enforcing HTTPS.")
                self.use_https = True
            else:
                self._logger.debug("Server address contains 'https://'. Removed.")

        if server_address.endswith("/"):
            server_address = server_address.removesuffix("/")
            self._logger.info("Server address contains trailing '/'. Removed.")

        return server_address

    @property
    def base_url(self) -> str:
        """Returns the base URL of the API (including protocol)."""
        protocol = "https" if self.use_https else "http"
        return f"{protocol}://{self.server_address}"
