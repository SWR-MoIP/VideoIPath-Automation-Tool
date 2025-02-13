from typing import Optional

from pydantic.networks import IPvAnyAddress

from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_vertex import Vertex


class IpVertex(Vertex):
    """
    Represents an IP vertex in the topology.

    Attributes:
        ipAddress (Optional[IPvAnyAddress]): IP Address
        ipNetmask (Optional[IPvAnyAddress]): IP Netmask
        public (bool): Public (Share via distributed systems)
        supportsCpipeCfg (bool): Supports C-Pipe Config
        supportsIgmpCfg (bool): Supports Igmp Config
        supportsMacForwardingCfg (bool): Supports Mac Forwarding Config
        supportsNsoCfg (bool): Supports Nso Config
        supportsOpenflowCfg (bool): Supports Openflow Config
        supportsStaticIgmpCfg (bool): Supports Static Igmp Config
        supportsVlanCfg (bool): Supports Vlan Config
        supportsVplsCfg (bool): Supports VPLS Config
        vlanId (Optional[str]): ID of VLAN to use
        vrfId (Optional[str]): ID of VRF to use
    """

    ipAddress: Optional[IPvAnyAddress]
    ipNetmask: Optional[IPvAnyAddress]
    public: bool = False
    supportsCpipeCfg: bool = True
    supportsIgmpCfg: bool = True
    supportsMacForwardingCfg: bool = True
    supportsNsoCfg: bool = True
    supportsOpenflowCfg: bool = True
    supportsStaticIgmpCfg: bool = True
    supportsVlanCfg: bool = True
    supportsVplsCfg: bool = True
    vlanId: Optional[str]
    vrfId: Optional[str]

    # --- Getters and Setters ---

    @property
    def ip_address(self) -> Optional[IPvAnyAddress]:
        """IP Address"""
        return self.ipAddress

    @ip_address.setter
    def ip_address(self, value: Optional[IPvAnyAddress]):
        """IP Address"""
        self.ipAddress = value

    @property
    def ip_netmask(self) -> Optional[IPvAnyAddress]:
        """IP Netmask"""
        return self.ipNetmask

    @ip_netmask.setter
    def ip_netmask(self, value: Optional[IPvAnyAddress]):
        """IP Netmask"""
        self.ipNetmask = value

    @property
    def vlan_id(self) -> Optional[str]:
        """Vlan Id"""
        return self.vlanId

    @vlan_id.setter
    def vlan_id(self, value: Optional[str]):
        """Vlan Id"""
        self.vlanId = value

    @property
    def supports_cpipe_config(self) -> bool:
        """Supports C-Pipe Config"""
        return self.supportsCpipeCfg

    @supports_cpipe_config.setter
    def supports_cpipe_config(self, value: bool):
        """Supports C-Pipe Config"""
        self.supportsCpipeCfg = value

    @property
    def supports_igmp_config(self) -> bool:
        """Supports Igmp Config"""
        return self.supportsIgmpCfg

    @supports_igmp_config.setter
    def supports_igmp_config(self, value: bool):
        """Supports Igmp Config"""
        self.supportsIgmpCfg = value

    @property
    def supports_mac_forwarding_config(self) -> bool:
        """Supports Mac Forwarding Config"""
        return self.supportsMacForwardingCfg

    @supports_mac_forwarding_config.setter
    def supports_mac_forwarding_config(self, value: bool):
        """Supports Mac Forwarding Config"""
        self.supportsMacForwardingCfg = value

    @property
    def supports_nso_config(self) -> bool:
        """Supports Nso Config"""
        return self.supportsNsoCfg

    @supports_nso_config.setter
    def supports_nso_config(self, value: bool):
        """Supports Nso Config"""
        self.supportsNsoCfg = value

    @property
    def supports_openflow_config(self) -> bool:
        """Supports Openflow Config"""
        return self.supportsOpenflowCfg

    @supports_openflow_config.setter
    def supports_openflow_config(self, value: bool):
        """Supports Openflow Config"""
        self.supportsOpenflowCfg = value

    @property
    def supports_static_igmp_config(self) -> bool:
        """Supports Static Igmp Config"""
        return self.supportsStaticIgmpCfg

    @supports_static_igmp_config.setter
    def supports_static_igmp_config(self, value: bool):
        """Supports Static Igmp Config"""
        self.supportsStaticIgmpCfg = value

    @property
    def supports_vlan_config(self) -> bool:
        """Supports Vlan Config"""
        return self.supportsVlanCfg

    @supports_vlan_config.setter
    def supports_vlan_config(self, value: bool):
        """Supports Vlan Config"""
        self.supportsVlanCfg = value

    @property
    def supports_vpls_config(self) -> bool:
        """Supports VPLS Config"""
        return self.supportsVplsCfg

    @supports_vpls_config.setter
    def supports_vpls_config(self, value: bool):
        """Supports VPLS Config"""
        self.supportsVplsCfg = value
