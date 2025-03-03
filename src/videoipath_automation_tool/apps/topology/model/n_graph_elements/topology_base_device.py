from typing import List, Literal, Optional

from pydantic import Field

from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_n_graph_element import (
    IconSize,
    IconType,
    MapsElement,
    NGraphElement,
    SdpStrategy,
)


class BaseDevice(NGraphElement):
    """
    Represents the fundamental attributes of a device within a topology, including its appearance,
    position, and essential properties. This class serves as the core element for any topology device
    and is mandatory in all configurations.

    Attributes:
        type (Literal["baseDevice"]): Specifies the type of the device element, fixed as `"baseDevice"`.
        iconSize (IconSize): Defines the size of the device icon. Default is `"medium"`.
        iconType (IconType): Specifies the type of icon used for the device. Default is `"default"`.
        isVirtual (bool): Indicates whether the device is virtual. Default is `False`.
        maps (List[MapsElement]): A list of maps that define the device's position within the topology.
        sdpStrategy (SdpStrategy): Defines the SDP Polling strategy used by the device. Default is `"always"`.
        siteId (Optional[str]): An optional identifier for the site to which the device belongs.

    Note:
        To facilitate access to the properties of `BaseDevice`, corresponding getter and setter methods
        are implemented in the `TopologyDeviceConfiguration` class.
    """

    type: Literal["baseDevice"] = "baseDevice"
    iconSize: IconSize = "medium"
    iconType: IconType = "default"
    isVirtual: bool = False
    maps: List[MapsElement] = Field(default_factory=list)
    sdpStrategy: SdpStrategy = "always"
    siteId: Optional[str] = None

    # Note:
    # To facilitate access to the properties of `BaseDevice`, corresponding getter and setter methods
    # are implemented in the `TopologyDeviceConfiguration` class.
