from typing import Optional

from pydantic import Field
from pydantic.networks import IPvAnyAddress

from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_vertex import Vertex


class IpVertex(Vertex):
    ipAddress: None | IPvAnyAddress
    ipNetmask: None | IPvAnyAddress
    public: bool = False
    supportsCpipeCfg: bool = Field(True, description="Supports C-Pipe Config")
    supportsIgmpCfg: bool = Field(True, description="Supports Igmp Config")
    supportsMacForwardingCfg: bool = Field(True, description="Supports Mac Forwarding Config")
    supportsNsoCfg: bool = Field(True, description="Supports Nso Config")
    supportsOpenflowCfg: bool = Field(True, description="Supports Openflow Config")
    supportsStaticIgmpCfg: bool = Field(True, description="Supports Static Igmp Config")
    supportsVlanCfg: bool = Field(True, description="Supports Vlan Config")
    supportsVplsCfg: bool = Field(True, description="Supports VPLS Config")
    vlanId: Optional[str] = Field(None, description="Vlan Id")
    vrfId: Optional[str] = Field(None, description="VRF Id")
