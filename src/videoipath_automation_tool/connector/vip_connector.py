# External Imports
import logging
from typing import Optional
from typing_extensions import deprecated
import requests
import json

from pydantic import BaseModel, IPvAnyAddress, model_validator

# Internal Imports
from videoipath_automation_tool.connector.models.request_rest_v2 import RequestV2Patch
from videoipath_automation_tool.connector.models.response_rest_v2 import ResponseV2Get, ResponseV2Patch
from videoipath_automation_tool.connector.models.response_rpc import ResponseRPC


class VideoIPathConnector(BaseModel):
    """
    Class for VideoIPath API Connector using Basic Auth.
    VideoIPathConnector contains all HTTP methods to interact with the VideoIPath API.
    """

    ip: str | IPvAnyAddress
    username: str
    password: str
    ssl: bool
    ssl_verify: bool
    logger: Optional[logging.Logger] = None
    model_config: dict = {"arbitrary_types_allowed": True}
    _videoipath_version: str = ""
    # definitions for timeout handling
    _get_timeout: int = 5
    _post_timeout: int = 10
    _patch_timeout: int = 30

    @model_validator(mode="after")
    def initialize_connector(self):
        if self.logger is None:
            self.logger = logging.getLogger(
                "videoipath_automation_tool_connector"
            )  # use fallback logger if no logger is provided
            self.logger.debug(
                "No logger for connector provided. Using fallback logger: 'videoipath_automation_tool_connector'."
            )
        self.logger.debug("Connector logger initialized.")
        return self

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
            or url_path.startswith("/rest/v2/data/config")
            or url_path.startswith("/rest/v2/data/status")
        ):
            raise ValueError(
                "REST v2 calls are only allowed for '/rest/v2/data/config' and '/rest/v2/data/status' URL paths."
            )

        if "/..." in url_path:
            raise ValueError("Wildcard '/...' is not allowed in URL path.")

        # 2. Construct URL
        protocol = "https" if self.ssl else "http"
        url = f"{protocol}://{self.ip}{url_path}"

        # 3. Execute GET request and receive response
        response = requests.get(
            url,
            auth=(self.username, self.password),
            timeout=self._get_timeout,
            verify=self.ssl_verify,
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

        protocol = "https" if self.ssl else "http"
        url = f"{protocol}://{self.ip}{url_path}"

        # 2. Execute PATCH request and receive response
        data = body.model_dump(mode="json", by_alias=True)

        response = requests.patch(
            url,
            headers={"Content-Type": "application/json"},
            data=json.dumps(data),
            auth=(self.username, self.password),
            timeout=self._patch_timeout,
            verify=self.ssl_verify,
        )

        if not response.ok:
            self.logger.debug(f"Response: {response.json()}")
            raise ValueError(f"Error in API response for path {url}: {response.status_code}, {response.reason}")

        # 3. Validate response format
        self.logger.debug(f"Response: {response.json()}")
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

        protocol = "https" if self.ssl else "http"
        url = f"{protocol}://{self.ip}{url_path}"

        # print(json.dumps(body, indent=4))
        # 2. Execute POST request and receive response
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            data=json.dumps(body),
            auth=(self.username, self.password),
            timeout=self._post_timeout,
            verify=self.ssl_verify,
        )

        # 3. Validate response format
        response_object = ResponseRPC.model_validate(response.json())

        # 4. Validate response status
        if not response_object.header.ok:
            raise ValueError(f"Error in API response: {response_object.header.caption}, {response_object.header.msg}")

        return response_object

    def test_connection(self) -> bool:
        """Method to test the connection and authentication to the VideoIPath API by executing a GET request to the root path.

        Returns:
            bool: True if connection and authentication successful, False otherwise
        """
        url = "/rest/v2/data/*"
        try:
            response = self.http_get_v2(url)
        except:
            return False
        if response is not None and response.header.code == "OK" and response.header.auth is True:
            return True
        return False

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

    # --- Deprecated Methods ---
    @deprecated(
        "This method is deprecated and will be removed in future versions. Please use the newer method for API requests."
    )
    def http_get_legacy(self, url_path: str):
        """Method to execute a legacy (v1) GET request to the VideoIPath API.
        Attention: No response validation implemented for legacy API

        Args:
            url_path (str): URL path (e.g. "/rest/v1/data/status/system/about/version")

        Returns:
            dict: Response body as dictionary
        """
        # 1. Construct URL
        protocol = "https" if self.ssl else "http"
        url = f"{protocol}://{self.ip}{url_path}"

        # 2. Execute GET request and receive response
        try:
            response = requests.get(
                url,
                auth=(self.username, self.password),
                timeout=self._get_timeout,
                verify=self.ssl_verify,
            )
        except requests.exceptions.RequestException as e:
            print(e)
            return None

        # Attention: No response validation implemented for legacy API

        return response.json()

    @deprecated(
        "This method is deprecated and will be removed in future versions. Please use the newer method for API requests."
    )
    def http_patch_legacy(self, url_path: str, body: dict) -> dict:
        # 1. Construct URL
        protocol = "https" if self.ssl else "http"
        url = f"{protocol}://{self.ip}{url_path}"

        # 2. Execute PATCH request and receive response
        try:
            response = requests.patch(
                url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(body),
                auth=(self.username, self.password),
                timeout=self._patch_timeout,
                verify=self.ssl_verify,
            )

        # 3. Validate response format
        except requests.exceptions.RequestException as e:
            print(e)
            return None

        # Attention: No response validation implemented for legacy API

        return response.json()

    @deprecated(
        "This method is deprecated and will be removed in future versions. Please use the newer method for API requests."
    )
    def http_post_legacy(self, url_path: str, body: dict) -> dict:
        """Method to execute a legacy (v1) POST request to the VideoIPath API.

        Args:
            url_path (str): URL path (e.g. "/rest/v1/actions/status/pathman/validateTopologyUpdate")
            body (dict): Request body as dictionary

        Returns:
            dict: Response body as dictionary
        """
        # 1. Construct URL
        protocol = "https" if self.ssl else "http"
        url = f"{protocol}://{self.ip}{url_path}"

        # 2. Execute POST request and receive response
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            data=json.dumps(body),
            auth=(self.username, self.password),
            timeout=self._post_timeout,
            verify=self.ssl_verify,
        )

        # Attention: No response validation implemented for legacy API

        return response.json()
