# External imports

from pydantic import BaseModel

# Internal imports
from videoipath_automation_tool.apps.topology.model.topology_device_configuration import TopologyDeviceConfiguration


class TopologyDevice(BaseModel):
    """
    Class which contains full information about a device in the topology
    """

    configuration: TopologyDeviceConfiguration
