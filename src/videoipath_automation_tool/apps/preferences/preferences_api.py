import json
import warnings
from typing import List

from videoipath_automation_tool.apps.preferences.model import *
from videoipath_automation_tool.apps.preferences.model.allocator_pools_models import MulticastRangeInfoEntry
from videoipath_automation_tool.apps.preferences.model.interface_item import InterfaceItem
from videoipath_automation_tool.apps.preferences.model.package_item import PackageItem
from videoipath_automation_tool.connector.models.request_rpc import RequestRPC
from videoipath_automation_tool.connector.models.response_rpc import ResponseRPC
from videoipath_automation_tool.connector.vip_connector import VideoIPathConnector
from videoipath_automation_tool.utils.custom_warnings import LicenseFileAlreadyExistsWarning


class PreferencesAPI:
    """
    Class for VideoIPath System Preferences API.
    """

    def __init__(self, vip_connector: VideoIPathConnector):
        self.vip_connector = vip_connector

    # --- System Configuration ---
    # Network
    def get_hostname(self) -> str:
        """
        Get the hostname of the VideoIPath System.

        Returns:
            str: Hostname of the VideoIPath System.

        Raises:
            ValueError: If no data is returned from the VideoIPath API.
        """
        response = self.vip_connector.rest.get("/rest/v2/data/config/system/ip/hostname")
        return response.data["config"]["system"]["ip"]["hostname"]

    def get_all_interfaces(self) -> list[InterfaceItem]:
        """
        Get all interfaces from the VideoIPath System Preferences.

        Returns:
            List[InterfaceItem]: List of Interface objects.

        Raises:
            ValueError: If no data is returned from the VideoIPath API.
        """

        response = self.vip_connector.rest.get("/rest/v2/data/config/system/ip/interfaces/**")
        if not response.data:
            raise ValueError("No data returned from VideoIPath API.")
        interfaces = []
        interface_names = response.data["config"]["system"]["ip"]["interfaces"].keys()

        for interface in interface_names:
            data = response.data["config"]["system"]["ip"]["interfaces"][interface]
            interfaces.append(InterfaceItem(name=interface, **data))
            data = None

        return interfaces

    def get_interface_by_name(self, name: str) -> InterfaceItem:
        """Get an interface by name from the VideoIPath System Preferences.

        Args:
            name (str): Name of the interface to get.

        Returns:
            InterfaceItem: Interface object.

        Raises:
            ValueError: If no data is returned from the VideoIPath API.
        """
        response = self.vip_connector.rest.get("/rest/v2/data/config/system/ip/interfaces/*")
        if name not in response.data["config"]["system"]["ip"]["interfaces"]:
            raise ValueError(f"Interface with name '{name}' not found in VideoIPath System Preferences.")
        response = self.vip_connector.rest.get(f"/rest/v2/data/config/system/ip/interfaces/{name}/**")
        if not response.data:
            raise ValueError("No data returned from VideoIPath API.")
        return InterfaceItem(name=name, **response.data["config"]["system"]["ip"]["interfaces"][name])

    def get_all_dns_servers(self) -> List[str]:
        """Get all DNS servers from the VideoIPath System Preferences.

        Returns:
            List[str]: List of DNS servers.

        Raises:
            ValueError: If no data is returned from the VideoIPath API.
        """
        response = self.vip_connector.rest.get("/rest/v2/data/config/system/ip/dnsServers/**")
        if not response.data:
            raise ValueError("No data returned from VideoIPath API.")
        return response.data["config"]["system"]["ip"]["dnsServers"]

    # LDAP

    # Northbound

    # Security

    # Alarm

    # Allocator Pools
    def get_multicast_ranges(self) -> List[MulticastRangeInfoEntry]:
        """
        Get all multicast pools from the VideoIPath System Preferences.
        """
        multicast_pools = []
        response = self.vip_connector.rest.get("/rest/v2/data/status/configman/multicastRangeInfo/**")
        if not response.data:
            raise ValueError("No data returned from VideoIPath API.")
        for pool in response.data["status"]["configman"]["multicastRangeInfo"]["_items"]:
            multicast_pools.append(MulticastRangeInfoEntry.parse_online_configuration(pool))
        return multicast_pools

    def remove_multicast_pool_by_label(self, remove_list: List[str]) -> ResponseRPC:
        """
        Remove one or multiple multicast pools from the VideoIPath System Preferences by label.
        """

        body = RequestRPC()
        body.header.id = 0
        body.data.remove = remove_list

        return self.vip_connector.rpc.post("/api/updateMulticastRanges", body=body)

    def update_multicast_pool(self, pools: MulticastRangeInfoEntry | List[MulticastRangeInfoEntry]):
        """
        Update a multicast pool in the VideoIPath System Preferences.
        """
        if type(pools) is MulticastRangeInfoEntry:
            pool_list = [pools]
        elif type(pools) is list:
            pool_list = pools

        update_dict = {}
        for pool in pool_list:
            update_dict[pool.id] = pool.dump_range_rpc()

        # body = {"header": {"id": 0}, "data": {"update": update_dict}}
        body = RequestRPC()
        body.header.id = 0
        body.data.update = update_dict

        return self.vip_connector.rpc.post("/api/updateMulticastRanges", body=body)

    # Customize Background

    # --- Packages & Certificates ---
    def get_all_packages(self) -> List[PackageItem]:
        """
        Get all packages from the VideoIPath System Preferences / Packages & Certificates.
        """
        packages = []
        response = self.vip_connector.rest.get("/rest/v2/data/status/system/packages/**")
        if not response.data:
            raise ValueError("No data returned from VideoIPath API.")
        for package in response.data["status"]["system"]["packages"]["_items"]:
            packages.append(PackageItem.model_validate(package))
        return packages

    # --- License ---
    def get_license_activation_code(self) -> str:
        """
        Get the main activation code from the VideoIPath System Preferences / License.
        """
        response = self.vip_connector.rest.get("/rest/v2/data/status/licensing/activationCode")
        return response.data["status"]["licensing"]["activationCode"]

    def get_license_activation_codes(self) -> List[str]:
        """
        Get all activation codes from the VideoIPath System Preferences / License.
        """
        response = self.vip_connector.rest.get("/rest/v2/data/status/licensing/activationCodes/**")
        return response.data["status"]["licensing"]["activationCodes"]

    def get_license_plan(self):
        """
        Get the plan from the VideoIPath System Preferences / License.
        """
        response = self.vip_connector.rest.get("/rest/v2/data/status/licensing/capabilityNow/plan")
        text = response.data["status"]["licensing"]["capabilityNow"]["plan"]
        if type(text) is not str:
            return text
        else:
            return text.capitalize()

    def get_license_concurrent_users(self):
        """
        Get the number of concurrent users allowed from the VideoIPath System Preferences / License.
        """
        response = self.vip_connector.rest.get("/rest/v2/data/status/licensing/capabilityNow/users")
        return response.data["status"]["licensing"]["capabilityNow"]["users"]

    def _fetch_license_advanced_functionality(self) -> List[str]:
        """
        Get the licensed advanced functionality from the VideoIPath System Preferences / License.
        """
        response = self.vip_connector.rest.get("/rest/v2/data/status/licensing/capabilityNow/options/*")
        return response.data["status"]["licensing"]["capabilityNow"]["options"]

    def _fetch_advanced_functionality_capability_labels(self) -> dict[str, str]:
        """
        Get the capability labels from the VideoIPath System Preferences / License.
        """
        response = self.vip_connector.rest.get("/rest/v2/data/status/licensing/capabilityLabels/*")
        return response.data["status"]["licensing"]["capabilityLabels"]

    def _fetch_license_information(self) -> dict:
        """
        Get the full license information from the VideoIPath System Preferences / License.
        """
        response = self.vip_connector.rest.get("/rest/v2/data/status/licensing/**")
        return response.data["status"]["licensing"]

    def _fetch_license_num_connections_now(self) -> dict:
        """
        Get the Normal Connections and Low Bitrate Connections from the VideoIPath System Preferences / License.

        Returns:
            dict: Number of connections for each available type (e.g. {"lowBitrateConnection": 38, "normalConnection": 27}).

        Raises:
            ValueError: If no data is returned from the VideoIPath API.
        """
        response = self.vip_connector.rest.get("/rest/v2/data/status/pathman/numConnectionsNow/**")
        items_list = response.data["status"]["pathman"]["numConnectionsNow"]["_items"]
        return {item["_id"]: item["_value"] for item in items_list}

    def _fetch_license_num_devices(self) -> dict:
        """
        Get the number of Drivers, NMOS devices, Switches from the VideoIPath System Preferences / License.

        Returns:
            dict: Number of devices for each available type (e.g. {"driver": 6, "nevion": 1, "nmos": 30, "switch": 8}).

        Raises:
            ValueError: If no data is returned from the VideoIPath API.
        """
        response = self.vip_connector.rest.get("/rest/v2/data/status/devman/numDevices/**")
        items_list = response.data["status"]["devman"]["numDevices"]["_items"]
        return {item["_id"]: item["_value"] for item in items_list}

    def _fetch_license_num_tally_used(self) -> int:
        """
        Get the Number of enabled tallies from the VideoIPath System Preferences / License.
        """
        response = self.vip_connector.rest.get("/rest/v2/data/status/tallyman/numTallyUsed")
        return response.data["status"]["tallyman"]["numTallyUsed"]

    def _fetch_license_num_pages_used(self) -> int:
        """
        Get the Number of pages used from the VideoIPath System Preferences / License.
        """
        response = self.vip_connector.rest.get("/rest/v2/data/status/gui/operate/numPagesUsed")
        return response.data["status"]["gui"]["operate"]["numPagesUsed"]

    def _fetch_license_num_nmos_query_apis_used(self) -> int:
        """
        Get the Number of NMOS external registries from the VideoIPath System Preferences / License.
        """
        response = self.vip_connector.rest.get("/rest/v2/data/status/devman/numNmosQueryApisUsed")
        return response.data["status"]["devman"]["numNmosQueryApisUsed"]

    def _prepare_license_for_upload(self, license_dict: dict) -> str:
        """
        Prepare the license for upload to the VideoIPath System Preferences / License.
        Removes all unnecessary whitespaces and newlines and converts the dictionary to a binary for RPC request.

        Args:
            license_dict (dict): License file as dictionary.
        """
        return json.dumps(license_dict, separators=(",", ":"))

    def get_license_by_signature(self, signature: str) -> dict | None:
        """
        Get a license by signature from the VideoIPath System Preferences / License.

        Args:
            signature (str): Signature of the license.

        Returns:
            dict: License information. If the license is not found, returns None.

        Raises:
            ValueError: If no data is returned from the VideoIPath API.
        """
        response = self.vip_connector.rest.get("/rest/v2/data/status/licensing/licenses/**")
        items_list = response.data["status"]["licensing"]["licenses"]["_items"]
        license = next((item for item in items_list if item["_vid"] == signature), None)
        if not license:
            return None
        return license

    def upload_license(self, license_dict: dict) -> dict | None:
        """
        Upload a license to the VideoIPath System Preferences / License.

        Args:
            license_dict (dict): License file as dictionary.

        Returns:
            dict: Fetched license information from the VideoIPath System Preferences / License. If the license is already uploaded, returns None.
        """
        license_filename = license_dict.get("ID", None)
        license_signature = license_dict.get("Signature", None)

        if not license_filename:
            raise ValueError("License file must contain a 'ID' key.")

        if not license_signature:
            raise ValueError("License file must contain a 'Signature' key.")

        license_server = self.get_license_by_signature(signature=license_signature)

        if license_server:
            warnings.warn(
                f"License with signature '{license_signature}' is already uploaded. License file '{license_filename}.txt' will not be uploaded again.",
                LicenseFileAlreadyExistsWarning,
            )
            return None

        license_binary = self._prepare_license_for_upload(license_dict)
        try:
            response = self.vip_connector.rpc.post_file_as_bytes(
                "/api/uploadLicense", f"{license_filename}.txt", license_binary
            )
        except ValueError:
            raise ValueError("Error while uploading license, probably the license file is not valid.") from None
        if response.data:
            return self.get_license_by_signature(signature=license_signature)

    def activate_license(self, license_signature: str) -> dict | None:
        """
        Activate a license in the VideoIPath System Preferences / License.

        Args:
            license_signature (str): Signature of the license.

        Returns:
            dict: Fetched license information from the VideoIPath System Preferences / License. If the license is not found, returns None.
        """

        license_server = self.get_license_by_signature(signature=license_signature)

        if not license_server:
            raise ValueError(
                f"License with signature '{license_signature}' not found in the VideoIPath System Preferences."
            )

        body = RequestRPC()
        body.header.id = 0
        body.data = license_signature

        response = self.vip_connector.rpc.post("/api/activateLicense", body=body)
        if response.data:
            return self.get_license_by_signature(signature=license_signature)
        return None

    def deactivate_license(self, license_signature: str) -> dict | None:
        """
        Deactivate a license in the VideoIPath System Preferences / License.

        Args:
            license_signature (str): Signature of the license.

        Returns:
            dict: Fetched license information from the VideoIPath System Preferences / License. If the license is not found, returns None.
        """

        license_server = self.get_license_by_signature(signature=license_signature)

        if not license_server:
            raise ValueError(
                f"License with signature '{license_signature}' not found in the VideoIPath System Preferences."
            )

        body = RequestRPC()
        body.header.id = 0
        body.data = license_signature

        response = self.vip_connector.rpc.post("/api/deactivateLicense", body=body)
        if response.data:
            return self.get_license_by_signature(signature=license_signature)
        return None
