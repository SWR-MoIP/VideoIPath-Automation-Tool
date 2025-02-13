import logging
from typing import Optional

from pydantic import IPvAnyAddress

from videoipath_automation_tool.apps.preferences.model.preferences_allocator_pools import (
    MulticastRangeInfoEntry,
    MulticastRanges,
)
from videoipath_automation_tool.apps.preferences.preferences_api import PreferencesAPI
from videoipath_automation_tool.connector.models.response_rpc import ResponseRPC


class AllocationPools:
    def __init__(self, preferences_api: PreferencesAPI, logger: logging.Logger):
        self._logger = logger
        self._preferences_api = preferences_api

    def get_multicast_ranges(self) -> "MulticastRanges":
        """Get all multicast ranges from the VideoIPath System Preferences."""
        pools_as_list = self._preferences_api.get_multicast_ranges()
        if not pools_as_list:
            self._logger.warning("No multicast ranges found in the VideoIPath System Preferences.")
            return MulticastRanges.create(pools=[])
        return MulticastRanges.create(pools=pools_as_list)

    def create_local_multicast_pool(
        self, name: str, start_ip: Optional[IPvAnyAddress] = None, end_ip: Optional[IPvAnyAddress] = None
    ) -> MulticastRangeInfoEntry:
        """Create a local Multicast Range instance.
        Push to VideoIPath System Preferences with add_multicast_pool().

        Args:
            name (str): Name of the Multicast Range.
            startip (Optional[IPvAnyAddress], optional): Start IP address of the Multicast Range. Defaults to None.
            endip (Optional[IPvAnyAddress], optional): End IP address of the Multicast Range. Defaults to None.
        """
        instance = MulticastRangeInfoEntry.create(id=name, vid=name, ranges=[])
        if start_ip and end_ip:
            instance.add_range(start_ip=start_ip, end_ip=end_ip)
        elif start_ip or end_ip:
            logging.warning("Both startip and endip must be provided to create a range.")
        return instance

    def remove_multicast_pool(
        self, pool: list[str] | list[MulticastRangeInfoEntry] | str | MulticastRangeInfoEntry
    ) -> ResponseRPC:
        """Remove one or multiple multicast ranges from the VideoIPath System Preferences.

        Args:
            pool (list[str] | list[MulticastRangeInfoEntry] | str | MulticastRangeInfoEntry): (List of) label(s) or object(s) to remove.

        """
        if type(pool) is str or type(pool) is MulticastRangeInfoEntry:
            pool_list = [pool]
        elif type(pool) is list:
            pool_list = pool
        else:
            raise ValueError(
                "Invalid input type. Expected str, MulticastRangeInfoEntry or list[str] or list[MulticastRangeInfoEntry]."
            )

        remove_label_list = []

        for pool_item in pool_list:
            if type(pool_item) is str:
                remove_label_list.append(pool_item)
            elif type(pool_item) is MulticastRangeInfoEntry:
                remove_label_list.append(pool_item.id)

        # check if every pool exists in the system preferences
        existing_pools = self.get_multicast_ranges().available_ranges
        for remove_label in remove_label_list:
            if remove_label not in existing_pools:
                raise ValueError(f"Pool with label '{remove_label}' not found in the VideoIPath System Preferences.")

        return self._preferences_api.remove_multicast_pool_by_label(remove_list=remove_label_list)

    def update_multicast_pool(self, pools: MulticastRangeInfoEntry | list[MulticastRangeInfoEntry]) -> MulticastRanges:
        """Update a Multicast Range in the VideoIPath System Preferences.
            (If the pool does not exist, it will be created.)

        Args:
            pools (MulticastRangeInfoEntry | list[MulticastRangeInfoEntry]): (List of) MulticastRangeInfoEntry object(s) to update.
        """
        self._preferences_api.update_multicast_pool(pools=pools)
        # TODO: Improve business logic, error handling, logging, ...
        return self.get_multicast_ranges()

    def add_multicast_pool(
        self, pools: MulticastRangeInfoEntry | list[MulticastRangeInfoEntry], force: bool = False
    ) -> MulticastRanges:
        """Add a Multicast Range to the VideoIPath System Preferences.
        If force is set to True, a pool with the same label will be overwritten.

        Args:
            pool (MulticastRangeInfoEntry): MulticastRangeInfoEntry object to add.
            force (bool, optional): Overwrite existing pool with the same label. Defaults to False.

        """
        # check if pool already exists
        existing_pools = self.get_multicast_ranges().available_ranges
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


class SystemConfiguration:
    def __init__(self, preferences_api: PreferencesAPI, logger: logging.Logger):
        self._logger = logger
        self._preferences_api = preferences_api

        try:
            self.allocation_pools = AllocationPools(preferences_api=self._preferences_api, logger=self._logger)
        except Exception:
            raise ConnectionError("Error initializing Preferences App / System Configuration / Allocation Pools.")
