from typing import List, Literal, Optional

from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_n_graph_element import (
    IconSize,
    IconType,
    MapsElement,
    NGraphElement,
    SdpStrategy,
)


class BaseDevice(NGraphElement):
    type: Literal["baseDevice"] = "baseDevice"
    iconSize: IconSize = "medium"
    iconType: IconType = "default"
    isVirtual: bool = False
    maps: List[MapsElement] = []
    sdpStrategy: SdpStrategy = "always"
    siteId: Optional[str] = None

    # Note:
    # To provide easy access to the properties of the BaseDevice class,
    # corresponding getter and setter methods are defined in TopologyDeviceConfiguration Class.
