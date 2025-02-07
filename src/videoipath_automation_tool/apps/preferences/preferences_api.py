from typing import List

from videoipath_automation_tool.apps.preferences.model import *

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

    def get_multicast_pools(self) -> List[MulticastRangeInfoEntry]:
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
