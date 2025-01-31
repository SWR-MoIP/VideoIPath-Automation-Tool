import logging
from typing import List, Optional
from pydantic.networks import IPvAnyAddress

from videoipath_automation_tool.apps.preferences.model.preferences_allocator_pools import (
    MulticastPools,
    MulticastRangeInfoEntry,
)
from videoipath_automation_tool.apps.preferences.preferences_api import PreferencesAPI
from videoipath_automation_tool.connector.models.response_rpc import ResponseRPC
from videoipath_automation_tool.connector.vip_connector import VideoIPathConnector


class PreferencesApp:
    def __init__(self, vip_connector: VideoIPathConnector, logger: Optional[logging.Logger] = None):
        """PreferencesApp contains functionality to interact with the VideoIPath System Preferences.

        Args:
            vip_connector (VideoIPathConnector): VideoIPathConnector instance to handle the connection to the VideoIPath-Server.
            logger (Optional[logging.Logger], optional): Logger instance to use for logging.
        """
        # --- Setup Logging ---
        if logger is None:
            self.logger = logging.getLogger(
                "videoipath_automation_tool_preferences_app"
            )  # use fallback logger if no logger is provided
            self.logger.debug(
                "No logger for System Preferences App provided. Using fallback logger: 'videoipath_automation_tool_preferences_app'."
            )
        else:
            self.logger = logger

        # --- Setup System Preferences API ---
        try:
            self._preferences_api = PreferencesAPI(vip_connector=vip_connector)
            self.logger.debug("System Preferences API successfully initialized.")
        except Exception as e:
            self.logger.error(f"Error initializing System Preferences API: {e}")
            raise ConnectionError("Error initializing System Preferences API.")

    def get_multicast_pools(self) -> "MulticastPools":
        """Get all multicast pools from the VideoIPath System Preferences."""
        pools_as_list = self._preferences_api.get_multicast_pools()
        if not pools_as_list:
            self.logger.warning("No multicast pools found in the VideoIPath System Preferences.")
            return MulticastPools.create(pools=[])
        return MulticastPools.create(pools=pools_as_list)

    def create_local_multicast_pool(
        self, name: str, start_ip: Optional[IPvAnyAddress] = None, end_ip: Optional[IPvAnyAddress] = None
    ) -> MulticastRangeInfoEntry:
        """Create a local Multicast Pool instance.
        Push to VideoIPath System Preferences with add_multicast_pool().

        Args:
            name (str): Name of the Multicast Pool.
            startip (Optional[IPvAnyAddress], optional): Start IP address of the Multicast Pool. Defaults to None.
            endip (Optional[IPvAnyAddress], optional): End IP address of the Multicast Pool. Defaults to None.
        """
        instance = MulticastRangeInfoEntry.create(id=name, vid=name, ranges=[])
        if start_ip and end_ip:
            instance.add_range(start_ip=start_ip, end_ip=end_ip)
        elif start_ip or end_ip:
            logging.warning("Both startip and endip must be provided to create a range.")
        return instance

    def remove_multicast_pool(
        self, pool: List[str] | List[MulticastRangeInfoEntry] | str | MulticastRangeInfoEntry
    ) -> ResponseRPC:
        """Remove one or multiple multicast pools from the VideoIPath System Preferences.

        Args:
            pool (List[str] | List[MulticastRangeInfoEntry] | str | MulticastRangeInfoEntry): (List of) label(s) or object(s) to remove.

        """
        if type(pool) is str or type(pool) is MulticastRangeInfoEntry:
            pool_list = [pool]
        elif type(pool) is list:
            pool_list = pool
        else:
            raise ValueError(
                "Invalid input type. Expected str, MulticastRangeInfoEntry or List[str] or List[MulticastRangeInfoEntry]."
            )

        remove_label_list = []

        for pool_item in pool_list:
            if type(pool_item) is str:
                remove_label_list.append(pool_item)
            elif type(pool_item) is MulticastRangeInfoEntry:
                remove_label_list.append(pool_item.id)

        # check if every pool exists in the system preferences
        existing_pools = self.get_multicast_pools().available_pools
        for remove_label in remove_label_list:
            if remove_label not in existing_pools:
                raise ValueError(f"Pool with label '{remove_label}' not found in the VideoIPath System Preferences.")

        return self._preferences_api.remove_multicast_pool_by_label(remove_list=remove_label_list)

    def update_multicast_pool(self, pools: MulticastRangeInfoEntry | List[MulticastRangeInfoEntry]) -> MulticastPools:
        """Update a multicast pool in the VideoIPath System Preferences.
            (If the pool does not exist, it will be created.)

        Args:
            pools (MulticastRangeInfoEntry | List[MulticastRangeInfoEntry]): (List of) MulticastRangeInfoEntry object(s) to update.
        """
        self._preferences_api.update_multicast_pool(pools=pools)
        # TODO: Improve business logic, error handling, logging, ...
        return self.get_multicast_pools()

    def add_multicast_pool(
        self, pools: MulticastRangeInfoEntry | List[MulticastRangeInfoEntry], force: bool = False
    ) -> MulticastPools:
        """Add a multicast pool to the VideoIPath System Preferences.
        If force is set to True, a pool with the same label will be overwritten.

        Args:
            pool (MulticastRangeInfoEntry): MulticastRangeInfoEntry object to add.
            force (bool, optional): Overwrite existing pool with the same label. Defaults to False.

        """
        # check if pool already exists
        existing_pools = self.get_multicast_pools().available_pools
        remove_list = []
        if type(pools) is MulticastRangeInfoEntry:
            if pools.id in existing_pools:
                if not force:
                    raise ValueError(
                        f"Pool with label '{pools.id}' already exists in the VideoIPath System Preferences."
                    )
                else:
                    remove_list.append(pools.id)
        elif type(pools) is list:
            for pool in pools:
                if pool.id in existing_pools:
                    if not force:
                        raise ValueError(
                            f"Pool with label '{pool.id}' already exists in the VideoIPath System Preferences."
                        )
                    else:
                        remove_list.append(pool.id)
        # Remove existing pool(s) with the same label(s)
        if remove_list:
            self.remove_multicast_pool(pool=remove_list)
        # Add the new pool(s)
        return self.update_multicast_pool(pools=pools)
