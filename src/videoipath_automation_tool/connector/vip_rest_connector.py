from typing import Literal

from videoipath_automation_tool.connector.models.request_rest_v2 import RequestV2Patch, RequestV2Post
from videoipath_automation_tool.connector.models.response_rest_v2 import ResponseV2Get, ResponseV2Patch, ResponseV2Post
from videoipath_automation_tool.connector.vip_base_connector import VideoIPathBaseConnector


class VideoIPathRestConnector(VideoIPathBaseConnector):
    ALLOWED_URLS = {
        "GET": {
            "PREFIXES": {"/rest/v2/data/config/", "/rest/v2/data/status/"},
            "EXACT_MATCHES": {"/rest/v2/data/*"},
        },
        "PATCH": {"PREFIXES": {"/rest/v2/data/config/"}, "EXACT_MATCHES": set()},
        "POST": {
            "PREFIXES": {"/rest/v2/actions/status/collector/"},
            "EXACT_MATCHES": {"/rest/v2/actions/status/pathman/validateTopologyUpdate"},
        },
    }

    def get(
        self,
        url_path: str,
        auth_check: bool = True,
        node_check: bool = True,
        url_validation: bool = True,
        version: Literal["v2"] = "v2",
    ) -> ResponseV2Get:
        """
        Executes a REST v2 GET request to the VideoIPath API.

        This method validates the URL, constructs the request, and handles API responses.
        It optionally checks authentication and validates if response data matches the expected structure.

        Args:
            url_path (str): The API endpoint path (e.g., "/rest/v2/data/status/system/about/version").
            auth_check (bool, optional): If `True`, verifies authentication status in the response (default: `True`).
            node_check (bool, optional): If `True`, ensures that all expected nodes are present in the response data (default: `True`).
            url_validation (bool, optional): If `True`, validates the URL path (default: `True`).
            version (Literal["v2"], optional): The API version to use (default: "v2").

        Returns:
            ResponseV2Get: The validated API response object.

        Raises:
            ValueError: If the URL path is invalid or the API response contains an error.
            PermissionError: If authentication fails.
            TimeoutError: If the request times out.
            ConnectionError: If the server cannot be reached.
            requests.RequestException: For other network-related errors.

        Example:
            response = connector.get("/rest/v2/data/status/system/about/version")
            print(response.data)
        """
        if url_validation:
            self._validate_url(url_path, "GET")

        if "/..." in url_path:
            error_message = "Wildcard '/...' is not allowed in URL path."
            raise ValueError(error_message)

        response = self._execute_request(
            method="GET",
            url=self._build_url(url_path),
            timeout=self.timeouts.get,
            request_payload=None,
        )

        response_object = ResponseV2Get.model_validate(response.json())

        if response_object.header.code != "OK":
            raise Exception(f"Error in API response: {response_object.header.code}, {response_object.header.msg}")

        if auth_check:
            if not response_object.header.auth:
                raise PermissionError(
                    f"Authentication failed for path {url_path}: {response.status_code}, {response.reason}"
                )
        else:
            self._logger.debug("Authentication check skipped.")

        if node_check:
            self._validate_v2_response_data(response_object, url_path)
        else:
            self._logger.debug("Node check skipped.")

        return response_object

    def patch(
        self,
        url_path: str,
        body: RequestV2Patch,
        auth_check: bool = True,
        url_validation: bool = True,
        version: Literal["v2"] = "v2",
    ) -> ResponseV2Patch:
        """
        Executes a REST v2 PATCH request to the VideoIPath API.

        This method validates the URL, constructs the request, and handles API responses.

        Args:
            url_path (str): The API endpoint path (e.g., "/rest/v2/data/config/network/nGraphElements").
            body (RequestV2Patch): The request body object.
            auth_check (bool, optional): If `True`, verifies authentication status in the response (default: `True`).
            url_validation (bool, optional): If `True`, validates the URL path (default: `True`).
            version (Literal["v2"], optional): The API version to use (default: "v2").

        Returns:
            ResponseV2Patch: The validated API response object.

        Raises:
            ValueError: If the URL path is invalid or the API response contains an error.
            PermissionError: If authentication fails.
            TimeoutError: If the request times out.
            ConnectionError: If the server cannot be reached.
            requests.RequestException: For other network-related errors.

        Example:
            response = connector.patch("/rest/v2/data/config/network/nGraphElements", body)
            print(response.data)
        """
        if url_validation:
            self._validate_url(url_path, "PATCH")

        response = self._execute_request(
            method="PATCH",
            url=self._build_url(url_path),
            timeout=self.timeouts.patch,
            request_payload=body.model_dump(mode="json", by_alias=True),
        )

        response_object = ResponseV2Patch.model_validate(response.json())

        if response_object.header.code != "OK":
            raise Exception(f"Error in API response: {response_object.header.code}, {response_object.header.msg}")

        if auth_check:
            if not response_object.header.auth:
                raise PermissionError(
                    f"Authentication failed for path {url_path}: {response.status_code}, {response.reason}"
                )
        else:
            self._logger.debug("Authentication check skipped.")

        # Note: Content validation for PATCH responses is not implemented in this method.
        # It is recommended to perform any necessary validation of the response content
        # in the calling method after receiving the response from this PATCH request.

        return response_object

    def post(
        self,
        url_path: str,
        body: RequestV2Post,
        auth_check: bool = True,
        url_validation: bool = True,
        version: Literal["v2"] = "v2",
    ) -> ResponseV2Post:
        """
        Executes a REST v2 POST request to the VideoIPath API.

        This method validates the URL, constructs the request, and handles API responses.

        Args:
            url_path (str): The API endpoint path (e.g., "/rest/v2/actions/status/collector/lookupGraphElement").
            body (RequestV2Post): The request body object.
            auth_check (bool, optional): If `True`, verifies authentication status in the response (default: `True`).
            url_validation (bool, optional): If `True`, validates the URL path (default: `True`).
            version (Literal["v2"], optional): The API version to use (default: "v2").

        Returns:
            ResponseV2Post: The validated API response object.

        Raises:
            ValueError: If the URL path is invalid or the API response contains an error.
            PermissionError: If authentication fails.
            TimeoutError: If the request times out.
            ConnectionError: If the server cannot be reached.
            requests.RequestException: For other network-related errors.

        Example:
            response = connector.post("/rest/v2/actions/status/collector/lookupGraphElement", body)
            print(response.data)
        """
        if url_validation:
            self._validate_url(url_path, "POST")

        response = self._execute_request(
            method="POST",
            url=self._build_url(url_path),
            timeout=self.timeouts.post,
            request_payload=body.model_dump(mode="json", by_alias=True),
        )

        response_object = ResponseV2Post.model_validate(response.json())

        if response_object.header.code != "OK":
            raise Exception(f"Error in API response: {response_object.header.code}, {response_object.header.msg}")

        if auth_check:
            if not response_object.header.auth:
                raise PermissionError(
                    f"Authentication failed for path {url_path}: {response.status_code}, {response.reason}"
                )
        else:
            self._logger.debug("Authentication check skipped.")

        # Note: Content validation for POST responses is not implemented in this method.
        # It is recommended to perform any necessary validation of the response content
        # in the calling method after receiving the response from this POST request.

        return response_object

    def is_connected(self) -> bool:
        """Method to test the connection to the VideoIPath API by executing a GET request to the root path.

        Returns:
            bool: True if connection successful, False otherwise
        """
        url = "/rest/v2/data/*"

        self._logger.debug(f"Verifying connection to '{url}'")

        try:
            response = self.get(url, auth_check=False)
            return response and hasattr(response, "header") and response.header.code == "OK"
        except Exception as error:
            self._logger.error(f"Error while verifying connection to VideoIPath: {error}")
            return False

    def is_authenticated(self) -> bool:
        """Method to test the authentication to the VideoIPath API by executing a GET request to the root path.

        Returns:
            bool: True if authentication successful, False otherwise
        """
        url = "/rest/v2/data/*"

        self._logger.debug(f"Verifying authentication to '{url}' with user '{self._username}'")

        try:
            self.get(url)
            return True
        except PermissionError:
            return False

    # --- Internal Methods ---

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
                        self._logger.debug(f"Response Data: {response_data.model_dump(mode='json')}")
                        raise ValueError(error_message) from None
            current_nodes = next_nodes

    def _validate_url(self, url_path: str, http_method: Literal["GET", "PATCH", "POST"]):
        """Validates if a given URL is allowed based on the method and API type.

        Args:
            url_path (str): The API URL path to validate.
            http_method (Literal["GET", "PATCH", "POST"]): The HTTP method to validate.
            api_type (Literal["REST_V2", "RPC_API"]): The API type to validate.

        Raises:
            ValueError: If the URL is not allowed.
        """
        try:
            allowed_prefixes = self.ALLOWED_URLS[http_method]["PREFIXES"]
            allowed_exact_matches = self.ALLOWED_URLS[http_method]["EXACT_MATCHES"]
        except KeyError:
            valid_methods = ", ".join(self.ALLOWED_URLS.keys())
            error_message = f"Invalid method for VideoIPath REST API: '{http_method}'. Valid methods: {valid_methods}."
            raise ValueError(error_message)

        if not (url_path in allowed_exact_matches or any(url_path.startswith(prefix) for prefix in allowed_prefixes)):
            error_message = (
                f"Invalid URL path '{url_path}'. Allowed exact matches: {allowed_exact_matches}, "
                f"allowed prefixes: {', '.join(allowed_prefixes)}"
            )
            raise ValueError(error_message)
