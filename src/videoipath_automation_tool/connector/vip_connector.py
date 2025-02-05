import logging
import json
import requests
from typing import Optional

from videoipath_automation_tool.utils.cross_app_utils import create_fallback_logger
from videoipath_automation_tool.connector.models.request_rest_v2 import RequestV2Patch
from videoipath_automation_tool.connector.models.response_rest_v2 import ResponseV2Get, ResponseV2Patch
from videoipath_automation_tool.connector.models.response_rpc import ResponseRPC


class VideoIPathConnector:
    TIMEOUTS = {"GET": 5, "POST": 10, "PATCH": 30}

    ALLOWED_URLS = {
        "GET": {
            "REST_V2": {
                "PREFIXES": {"/rest/v2/data/config/", "/rest/v2/data/status/"},
                "EXACT_MATCHES": {"/rest/v2/data/*"},
            }
        },
        "PATCH": {"REST_V2": {"PREFIXES": {"/rest/v2/data/config/"}, "EXACT_MATCHES": set()}},
        "POST": {
            "REST_V2": {"PREFIXES": set(), "EXACT_MATCHES": set()},
            "RPC_API": {"PREFIXES": {"/api/"}, "EXACT_MATCHES": set()},
        },
    }

    HEADERS = {
        "GET": {
            "REST_V2": {"Content-Type": "application/json", "Accept-Encoding": "gzip, deflate"},
        }
    }

    EXCEPTION_MESSAGES = {
        "Timeout": "Timeout while requesting '{url}'",
        "ConnectionError": "Connection error while requesting '{url}'",
        "RequestException": "General request error for '{url}': {exception}",
    }

    def __init__(
        self,
        server_address: str,
        username: str,
        password: str,
        use_https: bool = True,
        verify_ssl_cert: bool = True,
        logger: Optional[logging.Logger] = None,
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
            _videoipath_version (str): VideoIPath version retrieved from the server.
            _timeouts (dict): Default timeout values for HTTP methods (`get`: 5s, `post`: 10s, `patch`: 30s).
        """
        self.username = username
        self.password = password
        self.verify_ssl_cert = verify_ssl_cert
        self._logger = logger or create_fallback_logger("videoipath_automation_tool_connector")
        self._videoipath_version = ""

        self.use_https = use_https
        self.server_address = server_address

        self._logger.debug(f"Logger initialized: '{self._logger.name}'")

        self._initialize_connector()
        self._logger.info("VideoIPath connector initialized.")

    def http_get_v2(self, url_path: str, auth_check: bool = True, node_check: bool = True) -> ResponseV2Get:
        """
        Executes a REST v2 GET request to the VideoIPath API.

        This method validates the URL, constructs the request, and handles API responses.
        It optionally checks authentication and validates if response data matches the expected structure.

        Args:
            url_path (str): The API endpoint path (e.g., "/rest/v2/data/status/system/about/version").
            auth_check (bool, optional): If `True`, verifies authentication status in the response (default: `True`).
            node_check (bool, optional): If `True`, ensures that all expected nodes are present in the response data (default: `True`).

        Returns:
            ResponseV2Get: The validated API response object.

        Raises:
            ValueError: If the URL path is invalid or the API response contains an error.
            PermissionError: If authentication fails.
            TimeoutError: If the request times out.
            ConnectionError: If the server cannot be reached.
            requests.RequestException: For other network-related errors.

        Example:
            response = connector.http_get_v2("/rest/v2/data/status/system/about/version")
            print(response.data)
        """

        # 1. Check URL
        self._validate_url(url_path, "GET", "REST_V2")

        if "/..." in url_path:
            error_message = "Wildcard '/...' is not allowed in URL path."
            self._logger.error(error_message)
            raise ValueError(error_message)

        # 2. Construct URL
        url = self._build_url(url_path)

        # 3. Execute GET request and receive response
        try:
            response = requests.get(
                url,
                auth=(self.username, self.password),
                timeout=self.TIMEOUTS["GET"],
                verify=self.verify_ssl_cert,
                headers=self.HEADERS["GET"]["REST_V2"],
            )
        except requests.exceptions.Timeout:
            self._logger.warning(self.EXCEPTION_MESSAGES["Timeout"].format(url=url))
            raise TimeoutError(self.EXCEPTION_MESSAGES["Timeout"].format(url=url))
        except requests.exceptions.ConnectionError:
            self._logger.warning(self.EXCEPTION_MESSAGES["ConnectionError"].format(url=url))
            raise ConnectionError(self.EXCEPTION_MESSAGES["ConnectionError"].format(url=url))
        except requests.exceptions.RequestException as e:
            self._logger.error(self.EXCEPTION_MESSAGES["RequestException"].format(url=url, exception=e))
            raise

        try:
            self._logger.debug(f"HTTP-GET Response [{response.status_code}]: {response.json()}")
        except json.JSONDecodeError:
            self._logger.debug(f"HTTP-GET Response [{response.status_code}] (RAW): {response.text}")
        self._logger.debug(f"HTTP-GET Response Headers: {response.headers}")

        if not response.ok:
            raise ValueError(f"Error in API response for path {url}: {response.status_code}, {response.reason}")

        # 4. Validate response format
        response_object = ResponseV2Get.model_validate(response.json())

        # 5. Validate response status
        if response_object.header.code != "OK":
            raise ValueError(f"Error in API response: {response_object.header.code}, {response_object.header.msg}")

        if auth_check:
            if not response_object.header.auth:
                raise PermissionError(
                    f"Authentication failed for path {url}: {response.status_code}, {response.reason}"
                )
        else:
            self._logger.debug("Authentication check skipped.")

        # 6. Check if all nodes in the URL path are present in the response data
        if node_check:
            self._validate_v2_response_data(response_object, url_path)
        else:
            self._logger.debug("Node check skipped.")

        return response_object

    def http_patch_v2(self, url_path: str, body: RequestV2Patch) -> ResponseV2Patch:
        """Method to execute a REST v2 PATCH request to the VideoIPath API.

        Args:
            url_path (str): URL path (e.g. "/rest/v2/data/status/system/about/version")
            body (dict): Request body as dictionary

        Raises:
            e: RequestException
            ValueError: Not a valid REST v2 URL path or error in API response

        Returns:
            ResponseV2: validated response object
        """

        # 1. Construct URL
        if not url_path.startswith("/rest/v2/"):
            raise ValueError("REST v2 calls are only allowed for /rest/v2/ URL paths.")

        protocol = "https" if self.use_https else "http"
        url = f"{protocol}://{self.server_address}{url_path}"

        # 2. Execute PATCH request and receive response
        data = body.model_dump(mode="json", by_alias=True)

        try:
            response = requests.patch(
                url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(data),
                auth=(self.username, self.password),
                timeout=self.TIMEOUTS["PATCH"],
                verify=self.verify_ssl_cert,
            )
        except requests.exceptions.RequestException as e:
            self._logger.error(f"Error in PATCH request: {e}")
            raise e from None

        self._logger.debug(f"HTTP-PATCH Response: {response.json()}")

        if not response.ok:
            raise ValueError(f"Error in API response for path {url}: {response.status_code}, {response.reason}")

        # 3. Validate response format
        response_object = ResponseV2Patch.model_validate(response.json())

        # 4. Validate response status
        if response_object.header.code != "OK":
            raise ValueError(f"Error in API response: {response_object.header.code}, {response_object.header.msg}")

        return response_object

    def http_post_rpc(self, url_path: str, body: dict) -> ResponseRPC:
        """Method to execute a POST request to the VideoIPath API for RPC calls.

        Args:
            url_path (str): URL path (e.g. "/api/getCurrentUser"). Attention: Only allowed for RPC calls.
            body (dict): Request body as dictionary

        Raises:
            e: RequestException
            ValueError: Not a valid RPC URL path or error in API response

        Returns:
            ResponseRPC: validated response object
        """

        # 1. Construct URL
        if not url_path.startswith("/api/"):
            raise ValueError("RPC calls are only allowed for /api/ URL paths.")

        protocol = "https" if self.use_https else "http"
        url = f"{protocol}://{self.server_address}{url_path}"

        # 2. Execute POST request and receive response
        try:
            response = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(body),
                auth=(self.username, self.password),
                timeout=self.TIMEOUTS["POST"],
                verify=self.verify_ssl_cert,
            )
        except requests.exceptions.RequestException as e:
            self._logger.error(f"Error in POST request: {e}")
            raise e from None

        self._logger.debug(f"HTTP-POST Response: {response.json()}")

        # 3. Validate response format
        response_object = ResponseRPC.model_validate(response.json())

        # 4. Validate response status
        if not response_object.header.ok:
            raise ValueError(f"Error in API response: {response_object.header.caption}, {response_object.header.msg}")

        return response_object

    def verify_api_connection(self) -> bool:
        """Method to test the connection to the VideoIPath API by executing a GET request to the root path.

        Returns:
            bool: True if connection successful, False otherwise
        """
        url = "/rest/v2/data/*"

        self._logger.debug(f"Verifying connection to '{url}'")
        response = self.http_get_v2(url, auth_check=False)

        if response is not None and response.header.code == "OK":
            return True

        return False

    def verify_api_authentication(self) -> bool:
        """Method to test the authentication to the VideoIPath API by executing a GET request to the root path.

        Returns:
            bool: True if authentication successful, False otherwise
        """
        url = "/rest/v2/data/*"

        self._logger.debug(f"Verifying authentication to '{url}' with user '{self.username}'")

        try:
            response = self.http_get_v2(url)
        except PermissionError:
            return False

        if response is not None and response.header.code == "OK" and response.header.auth is True:
            return True

        return False

    def refresh_videoipath_version(self):
        """Method to refresh the VideoIPath version attribute."""
        try:
            response = self.http_get_v2("/rest/v2/data/status/system/about/version", auth_check=False)
            version = response.data["status"]["system"]["about"]["version"]
            self._videoipath_version = version
        except:
            print("Error while fetching VideoIPath version.")

    # --- Internal Methods ---
    def _initialize_connector(self):
        # --- Validate server address ---
        if not self.server_address:
            error_message = "Server address is required."
            self._logger.error(error_message)
            raise ValueError(error_message)

        # --- Validate username ---
        if not self.username:
            error_message = "Username is required."
            self._logger.error(error_message)
            raise ValueError(error_message)

        # --- Validate password ---
        if not self.password:
            error_message = "Password is required."
            self._logger.error(error_message)
            raise ValueError(error_message)

        # --- Test connection and authentication ---
        self._logger.debug(
            f"Testing connection to VideoIPath-Server with address: '{self.server_address}', username: '{self.username}' and provided password (Use HTTPS: '{self.use_https}', Verify SSL Cert: '{self.verify_ssl_cert}')."
        )

        if not self.verify_api_connection():
            error_message = "Connection to VideoIPath failed."
            self._logger.error(error_message)
            raise ConnectionError(error_message)

        if not self.verify_api_authentication():
            error_message = "Authentication to VideoIPath failed."
            self._logger.error(error_message)
            raise PermissionError(error_message)

        self._logger.debug("Connection and authentication to VideoIPath successful.")

    def _validate_server_address(self, server_address: str) -> str:
        # Todo: Implement/Improve validation of server address
        # Behaviors:
        # 1. Check if valid hostname (?), URL, IPv4 or IPv6 (ToDo: Port allowed ? Yes/No)
        # 2. If URL with http or https => remove http or https, if https => inform that https is enforced and set use_https to True
        # 3. If "/" at the end => remove
        # Format: e.g
        #   - "192.168.0.1"
        #   - "vip.company.com"
        #   - "http://vip.company.com"
        #   - "https://vip.company.com"
        #   - "PC31543" (???)

        # raise ValueError(f"Server address '{value}' is not valid.")

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

        # ToDo: Regex validation for hostname, URL, IPv4, IPv6

        return server_address

    def _validate_v2_response_data(self, response_data: ResponseV2Get, resource_path: str):
        """
        Validate if all nodes in the URL path are present in the response data.
        Comma-separated nodes are supported.
        Limitation: Validation stops at the first "*" or "_items" node, because the response data structure after these nodes is unknown.
        """

        nodes = []
        for node in resource_path.removeprefix("/rest/v2/").split("/"):
            if node and "*" not in node and "_items" not in node:
                nodes.append(node)
            else:
                break

        current_nodes = [response_data.model_dump(mode="json")]

        for node in nodes:
            node_parts = node.split(",")
            next_nodes = []
            for current_node in current_nodes:
                for part in node_parts:
                    try:
                        next_nodes.append(current_node[part])
                    except KeyError:
                        error_message = (
                            f"Node '{part}' ('/{node}') not found in response. Check the URL path: {resource_path}"
                        )
                        self._logger.error(error_message)
                        self._logger.debug(f"Response Data: {response_data.model_dump(mode='json')}")
                        raise ValueError(error_message) from None
            current_nodes = next_nodes

    def _validate_url(self, url_path: str, http_method: str, api_type: str):
        """Validates if a given URL is allowed based on the method and API type.

        Args:
            url_path (str): The API URL path to validate.
            http_method (str): The HTTP method (GET, PATCH, POST).
            api_type (str): The API type (REST_V2, RPC_API).

        Raises:
            ValueError: If the URL is not allowed.
        """
        try:
            allowed_prefixes = self.ALLOWED_URLS[http_method][api_type]["PREFIXES"]
            allowed_exact_matches = self.ALLOWED_URLS[http_method][api_type]["EXACT_MATCHES"]
        except KeyError:
            valid_methods = ", ".join(self.ALLOWED_URLS.keys())
            valid_apis = ", ".join(self.ALLOWED_URLS.get(http_method, {}).keys())
            error_message = f"Invalid method/API type: '{http_method}/{api_type}'. Valid methods: {valid_methods}. Valid APIs for {http_method}: {valid_apis}."
            self._logger.error(error_message)
            raise ValueError(error_message)

        if not (url_path in allowed_exact_matches or any(url_path.startswith(prefix) for prefix in allowed_prefixes)):
            error_message = (
                f"Invalid URL path '{url_path}'. Allowed exact matches: {allowed_exact_matches}, "
                f"allowed prefixes: {', '.join(allowed_prefixes)}"
            )
            self._logger.error(error_message)
            raise ValueError(error_message)

    def _build_url(self, url_path: str) -> str:
        """Builds the full API URL."""
        return f"{self.base_url}{url_path}"

    # --- Getter and Setter ---
    @property
    def videoipath_version(self) -> str:
        if self._videoipath_version == "":
            self.refresh_videoipath_version()
        return self._videoipath_version

    @property
    def server_address(self) -> str:
        return self._server_address

    @property
    def base_url(self) -> str:
        """Returns the base URL of the API (including protocol)."""
        protocol = "https" if self.use_https else "http"
        return f"{protocol}://{self.server_address}"

    @server_address.setter
    def server_address(self, value: str):
        value = self._validate_server_address(value)

        if not value or value.strip() == "":
            raise ValueError("Server address cannot be empty.")

        self._server_address = value
