from typing import List

from pydantic import BaseModel, Field
from pydantic.networks import IPvAnyAddress

# REST API Model


class Range(BaseModel, validate_assignment=True):
    startip: IPvAnyAddress = Field(alias="start")
    endip: IPvAnyAddress = Field(alias="end")


class Utilization(BaseModel, validate_assignment=True):
    percentage: int = Field(alias="percentage")
    total: int = Field(alias="total")
    used: int = Field(alias="used")


class MulticastRangeInfoEntry(BaseModel, validate_assignment=True):
    """MulticastPool class for VideoIPath System Preferences API."""

    id: str = Field(default_factory=str, alias="_id")
    vid: str = Field(default_factory=str, alias="_vid")
    ranges: List[Range]
    utilization: Utilization

    @classmethod
    def create(cls, id: str, vid: str, ranges: List[Range]) -> "MulticastRangeInfoEntry":
        """Method to create a local Multicast Pool instance."""
        utilization = Utilization(percentage=0, total=0, used=0)
        return cls(_id=id, _vid=vid, ranges=ranges, utilization=utilization)

    @classmethod
    def parse_online_configuration(cls, data: dict) -> "MulticastRangeInfoEntry":
        """Method to create a Multicast Pool instance from a "API style" dictionary."""
        instance = cls.model_validate(data)
        return instance

    def dump_range_rpc(self) -> list:
        """Method to dump the Multicast Pool ranges as list in RPC Style."""
        return [range_obj.model_dump(mode="json") for range_obj in self.ranges]

    def add_ip_range(self, start_ip: IPvAnyAddress, end_ip: IPvAnyAddress) -> "MulticastRangeInfoEntry":
        # Check if start_ip is lower than end_ip
        if start_ip > end_ip:  # type: ignore # TODO: Fix typing issue
            raise ValueError(f"Start IP {start_ip} is higher than End IP {end_ip}.")

        # Initialize Range object
        range_obj = Range(start=start_ip, end=end_ip)

        # Check if exact range already exists
        for range_item in self.ranges:
            if range_obj.startip == range_item.startip and range_obj.endip == range_item.endip:
                raise ValueError(
                    f"Range {range_item.startip} - {range_item.endip} already exists in the Multicast Pool."
                )

        self.ranges.append(range_obj)
        return self

    def remove_range(self, range_id: int) -> "MulticastRangeInfoEntry":
        if 0 <= range_id < len(self.ranges):
            del self.ranges[range_id]
        else:
            raise IndexError(f"range_id {range_id} is out of bounds.")
        return self


# User Interface Model


class MulticastRanges(BaseModel):
    available_ranges: List[str] = Field(default_factory=list)
    _pool_list: List[MulticastRangeInfoEntry]

    @classmethod
    def create(cls, pools: List[MulticastRangeInfoEntry]) -> "MulticastRanges":
        """Method to create a Multicast Range instance from a "API style" dictionary."""
        instance = cls()

        instance._pool_list = pools

        for pool in pools:
            instance.available_ranges.append(pool.id)

        return instance

    @property
    def allocator_range_list(self) -> List[MulticastRangeInfoEntry]:
        return self._pool_list

    def get_range_by_name(self, name: str) -> MulticastRangeInfoEntry:
        for allocator_range in self.allocator_range_list:
            if allocator_range.id == name:
                return allocator_range
        raise ValueError(f"Range with label '{name}' not found in the VideoIPath System Preferences.")
