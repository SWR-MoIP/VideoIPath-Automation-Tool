import requests

from videoipath_automation_tool.connector.models.request_rpc import RequestRPC
from videoipath_automation_tool.connector.models.response_rpc import ResponseRPC
from videoipath_automation_tool.connector.vip_base_connector import VideoIPathBaseConnector


class VideoIPathRPCConnector(VideoIPathBaseConnector):
    ALLOWED_PREFIXES = set()
    ALLOWED_EXACT_MATCHES = {
        "/api/getUtcTime",
        "/api/getCurrentUser",
        "/api/updateDevices",
        "/api/updateMulticastRanges",
        "/api/uploadLicense",
        "/api/activateLicense",
        "/api/deactivateLicense",
        "/api/updateSnmpConfig",
    }

    def post(self, url_path: str, body: RequestRPC, url_validation: bool = True) -> ResponseRPC:
        """
        Executes a RPC POST request to the VideoIPath API.

        This method validates the URL (unless skipped), constructs the request, and handles API responses.

        Args:
            url_path (str): The API endpoint path (e.g., "/api/updateDevices").
            body (RequestRPC): The request body object.
            url_validation (bool, optional): If `True`, validates the URL path (default: `True`).

        Returns:
            ResponseRPC: The validated API response object.

        Raises:
            ValueError: If the URL path is invalid or the API response contains an error.
            TimeoutError: If the request times out.
            ConnectionError: If the server cannot be reached.
            requests.RequestException: For other network-related errors.

        Example:
            response = connector.post("/api/updateDevices", body)
            print(response.data)
        """
        if url_validation:
            self._validate_url(url_path)

        response = self._execute_request(
            method="POST",
            url=self._build_url(url_path),
            timeout=self.timeouts.post,
            request_payload=body.model_dump(mode="json", by_alias=True),
        )

        return ResponseRPC.model_validate(response.json())

    def post_file_as_bytes(
        self, url_path: str, file_name: str, file_content: str, url_validation: bool = True
    ) -> ResponseRPC:
        """
        Executes a RPC POST request to the VideoIPath API with a file attachment.
        Mainly used for uploading license files.

        """
        if url_validation:
            self._validate_url(url_path)

        url = self._build_url(url_path)

        file_content_bytes = file_content.encode("utf-8")

        files = {"files": (file_name, file_content_bytes, "application/octet-stream")}

        try:
            response = requests.post(
                url,
                auth=(self._username, self._password),
                headers={"Accept": "application/json", "Accept-Encoding": "gzip, deflate"},
                files=files,
                verify=self.verify_ssl_cert,
            )

        except Exception as e:
            self._handle_request_exceptions(url, e)
        if response.status_code != 200:
            raise ValueError(f"Error while executing POST request to '{url}': {response.text}")
        return ResponseRPC.model_validate(response.json())

    def is_connected(self) -> bool:
        """Method to test the connection to the VideoIPath API by executing a POST request to the getUtcTime endpoint.
        Note: getUtcTime is a public endpoint that does not require authentication.

        Returns:
            bool: True if connection successful, False otherwise
        """
        url = "/api/getUtcTime"

        body = RequestRPC()
        body.header.id = 0

        self._logger.debug(f"Verifying connection to '{url}'")

        try:
            self._execute_request(
                method="POST",
                url=self._build_url(url),
                timeout=self.timeouts.post,
                request_payload=body.model_dump(mode="json", by_alias=True),
            )
            return True
        except Exception as error:
            self._logger.error(f"Error while verifying connection to VideoIPath: {error}")
            return False

    def is_authenticated(self) -> bool:
        """Method to test the authentication to the VideoIPath API by executing a POST request to the getCurrentUser endpoint.
        Note: getCurrentUser requires authentication.

        Returns:
            bool: True if authentication successful, False otherwise
        """
        url = "/api/getCurrentUser"

        body = RequestRPC()
        body.header.id = 0

        self._logger.debug(f"Verifying authentication to '{url}' with user '{self._username}'")

        try:
            self.post(url, body=body)
            return True
        except PermissionError:
            return False

    # --- Internal methods ---

    def _validate_url(self, url_path: str):
        """Validates if a given URL is allowed.

        Args:
            url_path (str): The API URL path to validate.

        Raises:
            ValueError: If the URL is not allowed.
        """

        if not (
            url_path in self.ALLOWED_EXACT_MATCHES
            or any(url_path.startswith(prefix) for prefix in self.ALLOWED_PREFIXES)
        ):
            error_message = (
                f"Invalid URL path '{url_path}'. Allowed exact matches: {self.ALLOWED_EXACT_MATCHES}, "
                f"allowed prefixes: {', '.join(self.ALLOWED_PREFIXES)}"
            )
            raise ValueError(error_message)
