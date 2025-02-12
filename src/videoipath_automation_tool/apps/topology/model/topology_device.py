from pydantic import BaseModel

from videoipath_automation_tool.apps.topology.model.topology_device_configuration import TopologyDeviceConfiguration


class TopologyDevice(BaseModel):
    """
    Class which contains full information about a device in the topology.

    Attributes:
        configuration (TopologyDeviceConfiguration): The configuration of the device
    """

    configuration: TopologyDeviceConfiguration
