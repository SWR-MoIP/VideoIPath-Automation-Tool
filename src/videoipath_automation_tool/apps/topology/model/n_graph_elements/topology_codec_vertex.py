import warnings
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field
from pydantic.networks import IPvAnyAddress
from pydantic_extra_types.mac_address import MacAddress

from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_vertex import Vertex


class DataTypeMismatchWarning(Warning):
    pass


warnings.simplefilter("always", DataTypeMismatchWarning)


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
    vlanP: str = ""


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
    def main_source_ip(self) -> Optional[IPvAnyAddress]:
        """GUI: IP Defaults | MAIN | Source IP"""
        return self.mainSrcIp

    @main_source_ip.setter
    def main_source_ip(self, ip_address: IPvAnyAddress):
        """GUI: IP Defaults | MAIN | Source IP"""
        self.mainSrcIp = ip_address

    @property
    def spare_source_ip(self) -> Optional[IPvAnyAddress]:
        """GUI: IP Defaults | SPARE | Source IP"""
        return self.spareSrcIp

    @spare_source_ip.setter
    def spare_source_ip(self, ip_address: IPvAnyAddress):
        """GUI: IP Defaults | SPARE | Source IP"""
        self.spareSrcIp = ip_address

    @property
    def main_source_gateway(self) -> Optional[IPvAnyAddress]:
        """GUI: IP Defaults | MAIN | Source Gateway"""
        return self.mainSrcGateway

    @main_source_gateway.setter
    def main_source_gateway(self, ip_address: IPvAnyAddress):
        """GUI: IP Defaults | MAIN | Source Gateway"""
        self.mainSrcGateway = ip_address

    @property
    def spare_source_gateway(self) -> Optional[IPvAnyAddress]:
        """GUI: IP Defaults | SPARE | Source Gateway"""
        return self.spareSrcGateway

    @spare_source_gateway.setter
    def spare_source_gateway(self, ip_address: IPvAnyAddress):
        """GUI: IP Defaults | SPARE | Source Gateway"""
        self.spareSrcGateway = ip_address

    @property
    def main_source_netmask(self) -> Optional[IPvAnyAddress]:
        """GUI: IP Defaults | MAIN | Source Netmask"""
        return self.mainSrcNetmask

    @main_source_netmask.setter
    def main_source_netmask(self, ip_address: IPvAnyAddress):
        """GUI: IP Defaults | MAIN | Source Netmask"""
        self.mainSrcNetmask = ip_address

    @property
    def spare_source_netmask(self) -> Optional[IPvAnyAddress]:
        """GUI: IP Defaults | SPARE | Source Netmask"""
        return self.spareSrcNetmask

    @spare_source_netmask.setter
    def spare_source_netmask(self, ip_address: IPvAnyAddress):
        """GUI: IP Defaults | SPARE | Source Netmask"""
        self.spareSrcNetmask = ip_address

    # - Connection Defaults -
    @property
    def main_destination_vlan_dot1Q(self) -> Optional[int]:
        """GUI: Connection Defaults | MAIN | VLAN (dot1Q - IEEE 802.1Q)"""
        if self.mainDstVlan is None:
            return None
        if isinstance(self.mainDstVlan, QinQ):
            warnings.warn(
                "Main Destination is set to QinQ, not dot1Q. Use 'main_destination_vlan_qinq' instead.",
                DataTypeMismatchWarning,
            )
            return None
        elif isinstance(self.mainDstVlan, nVlanPattern):
            warnings.warn(
                "Main Destination is set to VLAN Ranges, not dot1Q. Use 'main_destination_vlan_ranges' instead.",
                DataTypeMismatchWarning,
            )
            return None
        return self.mainDstVlan.vlan

    @main_destination_vlan_dot1Q.setter
    def main_destination_vlan_dot1Q(self, vlan_tag: int):
        """GUI: Connection Defaults | MAIN | VLAN (dot1Q - IEEE 802.1Q)"""
        self.mainDstVlan = nVlan1Q(vlan=vlan_tag)

    @property
    def spare_destination_vlan_dot1Q(self) -> Optional[int]:
        """GUI: Connection Defaults | SPARE | VLAN (dot1Q - IEEE 802.1Q)"""
        if self.spareDstVlan is None:
            return None
        if isinstance(self.spareDstVlan, QinQ):
            warnings.warn(
                "Spare Destination is set to QinQ, not dot1Q. Use 'spare_destination_vlan_qinq' instead.",
                DataTypeMismatchWarning,
            )
            return None
        elif isinstance(self.spareDstVlan, nVlanPattern):
            warnings.warn(
                "Spare Destination is set to VLAN Ranges, not dot1Q. Use 'spare_destination_vlan_ranges' instead.",
                DataTypeMismatchWarning,
            )
            return None
        return self.spareDstVlan.vlan

    @spare_destination_vlan_dot1Q.setter
    def spare_destination_vlan_dot1Q(self, vlan_tag: int):
        """GUI: Connection Defaults | SPARE | VLAN (dot1Q - IEEE 802.1Q)"""
        self.spareDstVlan = nVlan1Q(vlan=vlan_tag)

    @property
    def main_destination_vlan_qinq(self) -> Optional[QinQ]:
        """GUI: Connection Defaults | MAIN | VLAN (QinQ - 802.1Q tunneling)"""
        if self.mainDstVlan is None:
            return None
        if isinstance(self.mainDstVlan, nVlan1Q):
            warnings.warn(
                "Main Destination is set to dot1Q, not QinQ. Use 'main_destination_vlan_dot1Q' instead.",
                DataTypeMismatchWarning,
            )
            return None
        elif isinstance(self.mainDstVlan, nVlanPattern):
            warnings.warn(
                "Main Destination is set to VLAN Ranges, not QinQ. Use 'main_destination_vlan_ranges' instead.",
                DataTypeMismatchWarning,
            )
            return None
        return self.mainDstVlan

    @main_destination_vlan_qinq.setter
    def main_destination_vlan_qinq(self, outer_vlan_tag: int, inner_vlan_tag: int):
        """GUI: Connection Defaults | MAIN | VLAN (QinQ - 802.1Q tunneling)"""
        self.mainDstVlan = QinQ(vlanOuter=outer_vlan_tag, vlanInner=inner_vlan_tag)

    @property
    def spare_destination_vlan_qinq(self) -> Optional[QinQ]:
        """GUI: Connection Defaults | SPARE | VLAN (QinQ - 802.1Q tunneling)"""
        if self.spareDstVlan is None:
            return None
        if isinstance(self.spareDstVlan, nVlan1Q):
            warnings.warn(
                "Spare Destination is set to dot1Q, not QinQ. Use 'spare_destination_vlan_dot1Q' instead.",
                DataTypeMismatchWarning,
            )
            return None
        elif isinstance(self.spareDstVlan, nVlanPattern):
            warnings.warn(
                "Spare Destination is set to VLAN Ranges, not QinQ. Use 'spare_destination_vlan_ranges' instead.",
                DataTypeMismatchWarning,
            )
            return None
        return self.spareDstVlan

    @spare_destination_vlan_qinq.setter
    def spare_destination_vlan_qinq(self, outer_vlan_tag: int, inner_vlan_tag: int):
        """GUI: Connection Defaults | SPARE | VLAN (QinQ - 802.1Q tunneling)"""
        self.spareDstVlan = QinQ(vlanOuter=outer_vlan_tag, vlanInner=inner_vlan_tag)

    @property
    def main_destination_vlan_ranges(self) -> Optional[str]:
        """GUI: Connection Defaults | MAIN | VLAN (Ranges)"""
        if self.mainDstVlan is None:
            return None
        if isinstance(self.mainDstVlan, nVlan1Q):
            warnings.warn(
                "Main Destination is set to dot1Q, not VLAN Ranges. Use 'main_destination_vlan_dot1Q' instead.",
                DataTypeMismatchWarning,
            )
            return None
        elif isinstance(self.mainDstVlan, QinQ):
            warnings.warn(
                "Main Destination is set to QinQ, not VLAN Ranges. Use 'main_destination_vlan_qinq' instead.",
                DataTypeMismatchWarning,
            )
            return None
        return self.mainDstVlan.vlanP

    @main_destination_vlan_ranges.setter
    def main_destination_vlan_ranges(self, vlan_range: str):
        """GUI: Connection Defaults | MAIN | VLAN (Ranges)"""
        self.mainDstVlan = nVlanPattern(vlanP=vlan_range)

    @property
    def spare_destination_vlan_ranges(self) -> Optional[str]:
        """GUI: Connection Defaults | SPARE | VLAN (Ranges)"""
        if self.spareDstVlan is None:
            return None
        if isinstance(self.spareDstVlan, nVlan1Q):
            warnings.warn(
                "Spare Destination is set to dot1Q, not VLAN Ranges. Use 'spare_destination_vlan_dot1Q' instead.",
                DataTypeMismatchWarning,
            )
            return None
        elif isinstance(self.spareDstVlan, QinQ):
            warnings.warn(
                "Spare Destination is set to QinQ, not VLAN Ranges. Use 'spare_destination_vlan_qinq' instead.",
                DataTypeMismatchWarning,
            )
            return None
        return self.spareDstVlan.vlanP

    @spare_destination_vlan_ranges.setter
    def spare_destination_vlan_ranges(self, vlan_range: str):
        """GUI: Connection Defaults | SPARE | VLAN (Ranges)"""
        self.spareDstVlan = nVlanPattern(vlanP=vlan_range)

    @property
    def main_destination_port(self) -> Optional[int]:
        """GUI: Connection Defaults | MAIN | Port"""
        return self.mainDstPort

    @main_destination_port.setter
    def main_destination_port(self, port: int):
        """GUI: Connection Defaults | MAIN | Port"""
        self.mainDstPort = port

    @property
    def spare_destination_port(self) -> Optional[int]:
        """GUI: Connection Defaults | SPARE | Port"""
        return self.spareDstPort

    @spare_destination_port.setter
    def spare_destination_port(self, port: int):
        """GUI: Connection Defaults | SPARE | Port"""
        self.spareDstPort = port

    @property
    def main_destination_address_pool(self) -> Optional[str]:
        """GUI: Connection Defaults | MAIN | Multicast Address (poolId)"""
        if self.mainDstIp is None:
            return None
        if isinstance(self.mainDstIp, nAddress):
            warnings.warn(
                "Main Destination is set to an IP Address, not a Pool ID. Use 'main_destination_address_ip' instead.",
                DataTypeMismatchWarning,
            )
            return None
        return self.mainDstIp.poolId

    @main_destination_address_pool.setter
    def main_destination_address_pool(self, pool_label: str):
        """GUI: Connection Defaults | MAIN | Multicast Address (poolId)"""
        self.mainDstIp = nPoolId(poolId=pool_label)

    @property
    def spare_destination_address_pool(self) -> Optional[str]:
        """GUI: Connection Defaults | SPARE | Multicast Address (poolId)"""
        if self.spareDstIp is None:
            return None
        if isinstance(self.spareDstIp, nAddress):
            warnings.warn(
                "Spare Destination is set to an IP Address, not a Pool ID. Use 'spare_destination_address_ip' instead.",
                DataTypeMismatchWarning,
            )
            return None
        return self.spareDstIp.poolId

    @spare_destination_address_pool.setter
    def spare_destination_address_pool(self, pool_label: str):
        """GUI: Connection Defaults | SPARE | Multicast Address (poolId)"""
        self.spareDstIp = nPoolId(poolId=pool_label)

    @property
    def main_destination_address_ip(self) -> Optional[IPvAnyAddress]:
        """GUI: Connection Defaults | MAIN | Multicast Address (address)"""
        if self.mainDstIp is None:
            return None
        if isinstance(self.mainDstIp, nPoolId):
            warnings.warn(
                "Main Destination is set to a Pool ID, not an IP Address. Use 'main_destination_address_pool' instead.",
                DataTypeMismatchWarning,
            )
            return None
        return self.mainDstIp.addr

    @main_destination_address_ip.setter
    def main_destination_address_ip(self, multicast_ip_address: IPvAnyAddress):
        """GUI: Connection Defaults | MAIN | Multicast Address (address)"""
        self.mainDstIp = nAddress(addr=multicast_ip_address)

    @property
    def spare_destination_address_ip(self) -> Optional[IPvAnyAddress]:
        """GUI: Connection Defaults | SPARE | Multicast Address (address)"""
        if self.spareDstIp is None:
            return None
        if isinstance(self.spareDstIp, nPoolId):
            warnings.warn(
                "Spare Destination is set to a Pool ID, not an IP Address. Use 'spare_destination_address_pool' instead.",
                DataTypeMismatchWarning,
            )
            return None
        return self.spareDstIp.addr

    @spare_destination_address_ip.setter
    def spare_destination_address_ip(self, multicast_ip_address: IPvAnyAddress):
        """GUI: Connection Defaults | SPARE | Multicast Address (address)"""
        self.spareDstIp = nAddress(addr=multicast_ip_address)

    @property
    def main_source_mac(self) -> Optional[MacAddress]:
        """GUI: Connection Defaults | MAIN | Source Mac-address"""
        return self.mainSrcMac

    @main_source_mac.setter
    def main_source_mac(self, mac_address: MacAddress):
        """GUI: Connection Defaults | MAIN | Source Mac-address"""
        self.mainSrcMac = mac_address

    @property
    def spare_source_mac(self) -> Optional[MacAddress]:
        """GUI: Connection Defaults | SPARE | Source Mac-address"""
        return self.spareSrcMac

    @spare_source_mac.setter
    def spare_source_mac(self, mac_address: MacAddress):
        """GUI: Connection Defaults | SPARE | Source Mac-address"""
        self.spareSrcMac = mac_address

    @property
    def main_destination_mac(self) -> Optional[MacAddress]:
        """GUI: Connection Defaults | MAIN | Destination Mac-address"""
        return self.mainDstMac

    @main_destination_mac.setter
    def main_destination_mac(self, mac_address: MacAddress):
        """GUI: Connection Defaults | MAIN | Destination Mac-address"""
        self.mainDstMac = mac_address

    @property
    def spare_destination_mac(self) -> Optional[MacAddress]:
        """GUI: Connection Defaults | SPARE | Destination Mac-address"""
        return self.spareDstMac

    @spare_destination_mac.setter
    def spare_destination_mac(self, mac_address: MacAddress):
        """GUI: Connection Defaults | SPARE | Destination Mac-address"""
        self.spareDstMac = mac_address
