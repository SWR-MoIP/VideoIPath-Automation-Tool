import logging
import json
import requests
from typing import Optional

from videoipath_automation_tool.utils.cross_app_utils import create_fallback_logger
from videoipath_automation_tool.connector.models.request_rest_v2 import RequestV2Patch
from videoipath_automation_tool.connector.models.response_rest_v2 import ResponseV2Get, ResponseV2Patch
from videoipath_automation_tool.connector.models.response_rpc import ResponseRPC


class VideoIPathConnector:
    """
    Class for VideoIPath API Connector using Basic Auth.
    VideoIPathConnector contains all HTTP methods to interact with the VideoIPath API.
    """

    DEFAULT_TIMEOUTS = {"get": 5, "post": 10, "patch": 30}

    def __init__(
        self,
        server_address: str,
        username: str,
        password: str,
        use_https: bool = True,
        verify_ssl_cert: bool = True,
        logger: Optional[logging.Logger] = None,
    ):
        self.server_address = server_address
        self.username = username
        self.password = password
        self.use_https = use_https
        self.verify_ssl_cert = verify_ssl_cert
        self._logger = logger or create_fallback_logger("videoipath_automation_tool_connector")
        self._videoipath_version = ""
        self._timeouts = self.DEFAULT_TIMEOUTS.copy()

        self._logger.debug(f"VideoIPath connector logger initialized: '{self._logger.name}'")

    def http_get_v2(self, url_path: str) -> ResponseV2Get:
        """Method to execute a REST v2 GET request to the VideoIPath API.

        Args:
            url_path (str): URL path (e.g. "/rest/v2/data/status/system/about/version")

        Raises:
            ValueError: Not a valid REST v2 URL path or error in API response

        Returns:
            ResponseV2: validated response object
        """

        # 1. Check URL
        if not (
            url_path == "/rest/v2/data/*"
            or url_path.startswith("/rest/v2/data/config/")
            or url_path.startswith("/rest/v2/data/status/")
        ):
            error_message = "REST v2 calls are only allowed for URL paths starting with '/rest/v2/data/config' or '/rest/v2/data/status'."
            self._logger.error(error_message)
            raise ValueError(error_message)

        if "/..." in url_path:
            error_message = "Wildcard '/...' is not allowed in URL path."
            self._logger.error(error_message)
            raise ValueError(error_message)

        # 2. Construct URL
        protocol = "https" if self.use_https else "http"
        url = f"{protocol}://{self.server_address}{url_path}"

        # 3. Execute GET request and receive response
        response = requests.get(
            url,
            auth=(self.username, self.password),
            timeout=self._timeouts["get"],
            verify=self.verify_ssl_cert,
            headers={
                "Content-Type": "application/json",
                "Accept-Encoding": "gzip, deflate",
            },
        )

        if not response.ok:
            raise ValueError(f"Error in API response for path {url}: {response.status_code}, {response.reason}")

        # 4. Validate response format
        response_object = ResponseV2Get.model_validate(response.json())

        # 5. Validate response status
        if response_object.header.code != "OK":
            raise ValueError(f"Error in API response: {response_object.header.code}, {response_object.header.msg}")

        if response_object.header.auth is False:
            raise PermissionError(f"Authentication failed for path {url}: {response.status_code}, {response.reason}")

        # 6. Check if all nodes in the URL path are present in the response data
        self._validate_v2_response_data(response_object, url_path)

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

        response = requests.patch(
            url,
            headers={"Content-Type": "application/json"},
            data=json.dumps(data),
            auth=(self.username, self.password),
            timeout=self._timeouts["patch"],
            verify=self.verify_ssl_cert,
        )

        if not response.ok:
            self._logger.debug(f"Response: {response.json()}")
            raise ValueError(f"Error in API response for path {url}: {response.status_code}, {response.reason}")

        # 3. Validate response format
        self._logger.debug(f"Response: {response.json()}")
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

        # print(json.dumps(body, indent=4))
        # 2. Execute POST request and receive response
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            data=json.dumps(body),
            auth=(self.username, self.password),
            timeout=self._timeouts["post"],
            verify=self.verify_ssl_cert,
        )

        # 3. Validate response format
        response_object = ResponseRPC.model_validate(response.json())

        # 4. Validate response status
        if not response_object.header.ok:
            raise ValueError(f"Error in API response: {response_object.header.caption}, {response_object.header.msg}")

        return response_object

    def test_authentication(self) -> bool:
        """Method to test the authentication to the VideoIPath API by executing a GET request to the root path.

        Returns:
            bool: True if authentication successful, False otherwise
        """
        url = "/rest/v2/data/*"
        try:
            response = self.http_get_v2(url)
        except:
            return False
        if response is not None and response.header.code == "OK" and response.header.auth is True:
            return True
        return False

    def test_connection(self) -> bool:
        """Method to test the connection to the VideoIPath API by executing a GET request to the root path.

        Returns:
            bool: True if connection successful, False otherwise
        """
        url = "/rest/v2/data/*"
        try:
            response = self.http_get_v2(url)
        except:
            return False
        if response is not None and response.header.code == "OK":
            return True
        return False

    def refresh_videoipath_version(self):
        """ Refresh the VideoIPath version. """
        self._videoipath_version = ""
        self.videoipath_version 

    # --- Internal Methods ---
    def _validate_v2_response_data(self, response: ResponseV2Get, url: str):
        """Every node in the URL path should be present in the response. If not, raise an error."""
        nodes = []
        path_splitted = url.removeprefix("/rest/v2/").split("/")

        for node in path_splitted:
            if "*" in node or "_items" in node:
                break
            nodes.append(node)

        current_node = response.model_dump(mode="json")
        for node in nodes:
            try:
                current_node = current_node[node]
            except KeyError:
                raise ValueError(
                    f"Node '{node}' not found in response. Check the URL path: {url}"
                ) from None  # from None suppresses the original KeyError and improves the error message

    # --- Getter and Setter ---
    @property
    def videoipath_version(self) -> str:
        if self._videoipath_version == "":
            try:
                response = self.http_get_v2("/rest/v2/data/status/system/about/version")
                version = response.data["status"]["system"]["about"]["version"]
                self._videoipath_version = version
            except:
                print("Error getting VideoIPath version.")
        return self._videoipath_version