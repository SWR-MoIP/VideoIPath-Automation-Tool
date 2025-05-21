from typing import List

from pydantic import BaseModel, Field

from videoipath_automation_tool.apps.inventory.version_2024_3_3.model.drivers import CustomSettings
from videoipath_automation_tool.apps.inventory.version_2024_3_3.model.inventory_device_configuration import Config


class DiscoveredInventoryDevice(BaseModel):
    """
    Represents a discovered device in the inventory.
    """

    id: str = Field(alias="_id")
    vid: str = Field(alias="_vid")
    exists: list[str]
    ipAddressOpt: str
    source: str
    suggestedConfigs: List[Config[CustomSettings]]
