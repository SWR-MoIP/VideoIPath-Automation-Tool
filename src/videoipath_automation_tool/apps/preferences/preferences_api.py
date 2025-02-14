from typing import List

from videoipath_automation_tool.apps.preferences.model import *
from videoipath_automation_tool.apps.preferences.model.interface_item import InterfaceItem
from videoipath_automation_tool.apps.preferences.model.package_item import PackageItem
from videoipath_automation_tool.apps.preferences.model.preferences_allocator_pools import MulticastRangeInfoEntry
from videoipath_automation_tool.connector.models.request_rpc import RequestRPC
from videoipath_automation_tool.connector.models.response_rpc import ResponseRPC
from videoipath_automation_tool.connector.vip_connector import VideoIPathConnector


class PreferencesAPI:
    """
    Class for VideoIPath System Preferences API.
    By now, only the Multicast Pools are supported.

    """

    def __init__(self, vip_connector: VideoIPathConnector):
        self.vip_connector = vip_connector

    # --- System Configuration ---
    # ----- Network
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

    # ----- Allocation Pools
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
        # print(body)
        body = RequestRPC()
        body.header.id = 0
        body.data.update = update_dict

        return self.vip_connector.rpc.post("/api/updateMulticastRanges", body=body)

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
