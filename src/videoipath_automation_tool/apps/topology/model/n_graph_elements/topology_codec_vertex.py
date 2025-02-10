from typing import Literal, Union

from pydantic import BaseModel, Field
from pydantic.networks import IPvAnyAddress
from pydantic_extra_types.mac_address import MacAddress

from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_vertex import Vertex


# VLAN
class nVlan1Q(BaseModel, validate_assignment=True):
    type: Literal["nVlan1Q"] = "nVlan1Q"
    vlan: int = Field(..., ge=1, le=4094)


class QinQ(BaseModel, validate_assignment=True):
    type: Literal["nVlanQinQ"] = "nVlanQinQ"
    vlanInner: int = Field(..., ge=1, le=4094)
    vlanOuter: int = Field(..., ge=1, le=4094)


class nVlanPattern(BaseModel, validate_assignment=True):
    type: Literal["nVlanPattern"] = "nVlanPattern"
    vlanP: int = Field(..., ge=1, le=4094)


# Destination IP
class nAddress(BaseModel, validate_assignment=True):
    type: Literal["nAddress"] = "nAddress"
    addr: IPvAnyAddress


class nPoolId(BaseModel, validate_assignment=True):
    type: Literal["nPoolId"] = "nPoolId"
    poolId: str


# Literal Types
CodecFormat = Literal["Video", "Audio", "ASI", "Ancillary"]


# Codec Vertex
class CodecVertex(Vertex):
    type: Literal["codecVertex"] = "codecVertex"
    bidirPartnerId: None | str = None
    codecFormat: CodecFormat = "Video"
    extraFormats: list = []
    isIgmpSource: bool = False
    mainDstIp: None | Union[nAddress, nPoolId]
    mainDstMac: None | MacAddress
    mainDstPort: None | int
    mainDstVlan: None | Union[nVlan1Q, QinQ, nVlanPattern]
    mainSrcGateway: None | IPvAnyAddress
    mainSrcIp: None | IPvAnyAddress
    mainSrcMac: None | MacAddress
    mainSrcNetmask: None | IPvAnyAddress
    multiplicity: int = Field(..., ge=1)
    partnerConfig: None | dict[str, Union[str, int, bool]]
    public: bool = False
    sdpSupport: bool = True
    serviceId: None | int
    spareDstIp: None | Union[nAddress, nPoolId]
    spareDstMac: None | MacAddress
    spareDstPort: None | int
    spareDstVlan: None | Union[nVlan1Q, QinQ, nVlanPattern]
    spareSrcGateway: None | IPvAnyAddress
    spareSrcIp: None | IPvAnyAddress
    spareSrcMac: None | MacAddress
    spareSrcNetmask: None | IPvAnyAddress

    # --- Setters and Getters ---

    # - IP Defaults -
    @property
    def main_source_ip(self) -> None | IPvAnyAddress:
        """GUI: IP Defaults | MAIN | Source IP"""
        return self.mainSrcIp

    @main_source_ip.setter
    def main_source_ip(self, ip_address: IPvAnyAddress):
        """GUI: IP Defaults | MAIN | Source IP"""
        self.mainSrcIp = ip_address

    @property
    def spare_source_ip(self) -> None | IPvAnyAddress:
        """GUI: IP Defaults | SPARE | Source IP"""
        return self.spareSrcIp

    @spare_source_ip.setter
    def spare_source_ip(self, ip_address: IPvAnyAddress):
        """GUI: IP Defaults | SPARE | Source IP"""
        self.spareSrcIp = ip_address

    @property
    def main_source_gateway(self) -> None | IPvAnyAddress:
        """GUI: IP Defaults | MAIN | Source Gateway"""
        return self.mainSrcGateway

    @main_source_gateway.setter
    def main_source_gateway(self, ip_address: IPvAnyAddress):
        """GUI: IP Defaults | MAIN | Source Gateway"""
        self.mainSrcGateway = ip_address

    @property
    def spare_source_gateway(self) -> None | IPvAnyAddress:
        """GUI: IP Defaults | SPARE | Source Gateway"""
        return self.spareSrcGateway

    @spare_source_gateway.setter
    def spare_source_gateway(self, ip_address: IPvAnyAddress):
        """GUI: IP Defaults | SPARE | Source Gateway"""
        self.spareSrcGateway = ip_address

    @property
    def main_source_netmask(self) -> None | IPvAnyAddress:
        """GUI: IP Defaults | MAIN | Source Netmask"""
        return self.mainSrcNetmask

    @main_source_netmask.setter
    def main_source_netmask(self, ip_address: IPvAnyAddress):
        """GUI: IP Defaults | MAIN | Source Netmask"""
        self.mainSrcNetmask = ip_address

    @property
    def spare_source_netmask(self) -> None | IPvAnyAddress:
        """GUI: IP Defaults | SPARE | Source Netmask"""
        return self.spareSrcNetmask

    @spare_source_netmask.setter
    def spare_source_netmask(self, ip_address: IPvAnyAddress):
        """GUI: IP Defaults | SPARE | Source Netmask"""
        self.spareSrcNetmask = ip_address

    # - Connection Defaults -
    @property
    def main_destination_vlan_dot1Q(self) -> None | nVlan1Q:
        """GUI: Connection Defaults | MAIN | VLAN (dot1Q - IEEE 802.1Q)"""
        if self.mainDstVlan is None:
            return None
        if isinstance(self.mainDstVlan, QinQ):
            raise ValueError("Main Destination is set to QinQ, not dot1Q. Use 'main_destination_vlan_qinq' instead.")
        elif isinstance(self.mainDstVlan, nVlanPattern):
            raise ValueError(
                "Main Destination is set to VLAN Ranges, not dot1Q. Use 'main_destination_vlan_ranges' instead."
            )
        return self.mainDstVlan

    @main_destination_vlan_dot1Q.setter
    def main_destination_vlan_dot1Q(self, vlan_tag: int):
        """GUI: Connection Defaults | MAIN | VLAN (dot1Q - IEEE 802.1Q)"""
        self.mainDstVlan = nVlan1Q(vlan=vlan_tag)

    @property
    def spare_destination_vlan_dot1Q(self) -> None | nVlan1Q:
        """GUI: Connection Defaults | SPARE | VLAN (dot1Q - IEEE 802.1Q)"""
        if self.spareDstVlan is None:
            return None
        if isinstance(self.spareDstVlan, QinQ):
            raise ValueError("Spare Destination is set to QinQ, not dot1Q. Use 'spare_destination_vlan_qinq' instead.")
        elif isinstance(self.spareDstVlan, nVlanPattern):
            raise ValueError(
                "Spare Destination is set to VLAN Ranges, not dot1Q. Use 'spare_destination_vlan_ranges' instead."
            )
        return self.spareDstVlan

    @spare_destination_vlan_dot1Q.setter
    def spare_destination_vlan_dot1Q(self, vlan_tag: int):
        """GUI: Connection Defaults | SPARE | VLAN (dot1Q - IEEE 802.1Q)"""
        self.spareDstVlan = nVlan1Q(vlan=vlan_tag)

    @property
    def main_destination_vlan_qinq(self) -> None | QinQ:
        """GUI: Connection Defaults | MAIN | VLAN (QinQ - 802.1Q tunneling)"""
        if self.mainDstVlan is None:
            return None
        if isinstance(self.mainDstVlan, nVlan1Q):
            raise ValueError("Main Destination is set to dot1Q, not QinQ. Use 'main_destination_vlan_dot1Q' instead.")
        elif isinstance(self.mainDstVlan, nVlanPattern):
            raise ValueError(
                "Main Destination is set to VLAN Ranges, not QinQ. Use 'main_destination_vlan_ranges' instead."
            )
        return self.mainDstVlan

    @main_destination_vlan_qinq.setter
    def main_destination_vlan_qinq(self, outer_vlan_tag: int, inner_vlan_tag: int):
        """GUI: Connection Defaults | MAIN | VLAN (QinQ - 802.1Q tunneling)"""
        self.mainDstVlan = QinQ(vlanOuter=outer_vlan_tag, vlanInner=inner_vlan_tag)

    @property
    def spare_destination_vlan_qinq(self) -> None | QinQ:
        """GUI: Connection Defaults | SPARE | VLAN (QinQ - 802.1Q tunneling)"""
        if self.spareDstVlan is None:
            return None
        if isinstance(self.spareDstVlan, nVlan1Q):
            raise ValueError("Spare Destination is set to dot1Q, not QinQ. Use 'spare_destination_vlan_dot1Q' instead.")
        elif isinstance(self.spareDstVlan, nVlanPattern):
            raise ValueError(
                "Spare Destination is set to VLAN Ranges, not QinQ. Use 'spare_destination_vlan_ranges' instead."
            )
        return self.spareDstVlan

    @spare_destination_vlan_qinq.setter
    def spare_destination_vlan_qinq(self, outer_vlan_tag: int, inner_vlan_tag: int):
        """GUI: Connection Defaults | SPARE | VLAN (QinQ - 802.1Q tunneling)"""
        self.spareDstVlan = QinQ(vlanOuter=outer_vlan_tag, vlanInner=inner_vlan_tag)

    # Port
    @property
    def main_destination_port(self) -> None | int:
        """GUI: Connection Defaults | MAIN | Port"""
        return self.mainDstPort

    @main_destination_port.setter
    def main_destination_port(self, port: int):
        """GUI: Connection Defaults | MAIN | Port"""
        self.mainDstPort = port

    @property
    def spare_destination_port(self) -> None | int:
        """GUI: Connection Defaults | SPARE | Port"""
        return self.spareDstPort

    @spare_destination_port.setter
    def spare_destination_port(self, port: int):
        """GUI: Connection Defaults | SPARE | Port"""
        self.spareDstPort = port

    @property
    def main_destination_pool(self) -> None | str:
        """GUI: Connection Defaults | MAIN | Multicast Address (poolId)"""
        if self.mainDstIp is None:
            return None
        if isinstance(self.mainDstIp, nAddress):
            raise ValueError(
                "Main Destination is set to an IP Address, not a Pool ID. Use 'main_destination_ip' instead."
            )
        return self.mainDstIp.poolId

    @main_destination_pool.setter
    def main_destination_pool(self, pool_label: str):
        """GUI: Connection Defaults | MAIN | Multicast Address (poolId)"""
        self.mainDstIp = nPoolId(poolId=pool_label)

    @property
    def spare_destination_pool(self) -> None | str:
        """GUI: Connection Defaults | SPARE | Multicast Address (poolId)"""
        if self.spareDstIp is None:
            return None
        if isinstance(self.spareDstIp, nAddress):
            raise ValueError(
                "Spare Destination is set to an IP Address, not a Pool ID. Use 'spare_destination_ip' instead."
            )
        return self.spareDstIp.poolId

    @spare_destination_pool.setter
    def spare_destination_pool(self, pool_label: str):
        """GUI: Connection Defaults | SPARE | Multicast Address (poolId)"""
        self.spareDstIp = nPoolId(poolId=pool_label)

    @property
    def main_destination_ip(self) -> None | IPvAnyAddress:
        """GUI: Connection Defaults | MAIN | Multicast Address (address)"""
        if self.mainDstIp is None:
            return None
        if isinstance(self.mainDstIp, nPoolId):
            raise ValueError(
                "Main Destination is set to a Pool ID, not an IP Address. Use 'main_destination_pool' instead."
            )
        return self.mainDstIp.addr

    @main_destination_ip.setter
    def main_destination_ip(self, ip_address: IPvAnyAddress):
        """GUI: Connection Defaults | MAIN | Multicast Address (address)"""
        self.mainDstIp = nAddress(addr=ip_address)

    @property
    def spare_destination_ip(self) -> None | IPvAnyAddress:
        """GUI: Connection Defaults | SPARE | Multicast Address (address)"""
        if self.spareDstIp is None:
            return None
        if isinstance(self.spareDstIp, nPoolId):
            raise ValueError(
                "Spare Destination is set to a Pool ID, not an IP Address. Use 'spare_destination_pool' instead."
            )
        return self.spareDstIp.addr

    @spare_destination_ip.setter
    def spare_destination_ip(self, ip_address: IPvAnyAddress):
        """GUI: Connection Defaults | SPARE | Multicast Address (address)"""
        self.spareDstIp = nAddress(addr=ip_address)

    @property
    def main_source_mac(self) -> None | MacAddress:
        """GUI: Connection Defaults | MAIN | Source Mac-address"""
        return self.mainSrcMac

    @main_source_mac.setter
    def main_source_mac(self, mac_address: MacAddress):
        """GUI: Connection Defaults | MAIN | Source Mac-address"""
        self.mainSrcMac = mac_address

    @property
    def spare_source_mac(self) -> None | MacAddress:
        """GUI: Connection Defaults | SPARE | Source Mac-address"""
        return self.spareSrcMac

    @spare_source_mac.setter
    def spare_source_mac(self, mac_address: MacAddress):
        """GUI: Connection Defaults | SPARE | Source Mac-address"""
        self.spareSrcMac = mac_address

    @property
    def main_destination_mac(self) -> None | MacAddress:
        """GUI: Connection Defaults | MAIN | Destination Mac-address"""
        return self.mainDstMac

    @main_destination_mac.setter
    def main_destination_mac(self, mac_address: MacAddress):
        """GUI: Connection Defaults | MAIN | Destination Mac-address"""
        self.mainDstMac = mac_address

    # --- Getter and Setter Aliases ---
    main_multicast_pool = main_destination_pool
    spare_multicast_pool = spare_destination_pool
    main_multicast_ip = main_destination_ip
    spare_multicast_ip = spare_destination_ip
