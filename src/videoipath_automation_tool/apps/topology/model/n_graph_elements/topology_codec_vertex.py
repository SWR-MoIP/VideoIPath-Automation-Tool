import warnings
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field
from pydantic.networks import IPvAnyAddress
from pydantic_extra_types.mac_address import MacAddress

from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_vertex import Vertex
from videoipath_automation_tool.utils.custom_warnings import DataTypeMismatchWarning


# --- VLAN Types ---
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


# --- Multicast Address Types ---
class nAddress(BaseModel, validate_assignment=True):
    type: Literal["nAddress"] = "nAddress"
    addr: IPvAnyAddress


class nPoolId(BaseModel, validate_assignment=True):
    type: Literal["nPoolId"] = "nPoolId"
    poolId: str


# --- Codec Format Literal ---
CodecFormat = Literal["Video", "Audio", "ASI", "Ancillary"]


class CodecVertex(Vertex):
    type: Literal["codecVertex"] = "codecVertex"
    bidirPartnerId: Optional[str] = None
    codecFormat: CodecFormat = "Video"
    extraFormats: list = Field(default_factory=list)
    isIgmpSource: bool = False
    mainDstIp: Optional[Union[nAddress, nPoolId]]
    mainDstMac: Optional[MacAddress]
    mainDstPort: Optional[int]
    mainDstVlan: Optional[Union[nVlan1Q, QinQ, nVlanPattern]]
    mainSrcGateway: Optional[IPvAnyAddress]
    mainSrcIp: Optional[IPvAnyAddress]
    mainSrcMac: Optional[MacAddress]
    mainSrcNetmask: Optional[IPvAnyAddress]
    multiplicity: int = Field(..., ge=1)
    partnerConfig: Optional[dict[str, Union[str, int, bool]]]
    public: bool = False
    sdpSupport: bool = True
    serviceId: Optional[int]
    spareDstIp: Optional[Union[nAddress, nPoolId]]
    spareDstMac: Optional[MacAddress]
    spareDstPort: Optional[int]
    spareDstVlan: Optional[Union[nVlan1Q, QinQ, nVlanPattern]]
    spareSrcGateway: Optional[IPvAnyAddress]
    spareSrcIp: Optional[IPvAnyAddress]
    spareSrcMac: Optional[MacAddress]
    spareSrcNetmask: Optional[IPvAnyAddress]

    @staticmethod
    def _warn_type_mismatch(component_name: str, actual: str, expected: str, method_name: str):
        """
        Issues a warning when a data type mismatch occurs.

        Args:
            component_name (str): A user-friendly, GUI-oriented description of the component
                                (e.g., 'MAIN | VLAN', 'SPARE | Multicast Address').
            actual (str): The current data type assigned to the component.
            expected (str): The expected or required data type.
            method_name (str): The correct method to use for setting the expected data type.

        Example:
            _warn_type_mismatch("SPARE | Multicast Address", "Pool ID", "IP Address", "spare_destination_address_ip")
            -> "Warning: 'SPARE | Multicast Address' is set to 'Pool ID', not 'IP Address'. Use 'spare_destination_address_ip' instead."
        """
        warnings.warn(
            f"Warning: {component_name} is set to '{actual}', not '{expected}'. Use '{method_name}' instead.",
            DataTypeMismatchWarning,
        )

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
            self._warn_type_mismatch("MAIN | VLAN", "QinQ", "dot1Q", "main_destination_vlan_qinq")
            return None
        elif isinstance(self.mainDstVlan, nVlanPattern):
            self._warn_type_mismatch("MAIN | VLAN", "VLAN Ranges", "dot1Q", "main_destination_vlan_ranges")
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
            self._warn_type_mismatch("SPARE | VLAN", "QinQ", "dot1Q", "spare_destination_vlan_qinq")
            return None
        elif isinstance(self.spareDstVlan, nVlanPattern):
            self._warn_type_mismatch("SPARE | VLAN", "VLAN Ranges", "dot1Q", "spare_destination_vlan_ranges")
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
            self._warn_type_mismatch("MAIN | VLAN", "dot1Q", "QinQ", "main_destination_vlan_dot1Q")
            return None
        elif isinstance(self.mainDstVlan, nVlanPattern):
            self._warn_type_mismatch("MAIN | VLAN", "VLAN Ranges", "QinQ", "main_destination_vlan_ranges")
            return None
        return self.mainDstVlan

    @main_destination_vlan_qinq.setter
    def main_destination_vlan_qinq(self, vlan_pair: tuple[int, int]):
        """GUI: Connection Defaults | MAIN | VLAN (QinQ - 802.1Q tunneling)\n
        Expects a tuple (outer_vlan, inner_vlan)"""
        self.mainDstVlan = QinQ(vlanOuter=vlan_pair[0], vlanInner=vlan_pair[1])

    @property
    def spare_destination_vlan_qinq(self) -> Optional[QinQ]:
        """GUI: Connection Defaults | SPARE | VLAN (QinQ - 802.1Q tunneling)"""
        if self.spareDstVlan is None:
            return None
        if isinstance(self.spareDstVlan, nVlan1Q):
            self._warn_type_mismatch("SPARE | VLAN", "dot1Q", "QinQ", "spare_destination_vlan_dot1Q")
            return None
        elif isinstance(self.spareDstVlan, nVlanPattern):
            self._warn_type_mismatch("SPARE | VLAN", "VLAN Ranges", "QinQ", "spare_destination_vlan_ranges")
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
            self._warn_type_mismatch("MAIN | VLAN", "dot1Q", "VLAN Ranges", "main_destination_vlan_dot1Q")
            return None
        elif isinstance(self.mainDstVlan, QinQ):
            self._warn_type_mismatch("MAIN | VLAN", "QinQ", "VLAN Ranges", "main_destination_vlan_qinq")
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
            self._warn_type_mismatch("SPARE | VLAN", "dot1Q", "VLAN Ranges", "spare_destination_vlan_dot1Q")
            return None
        elif isinstance(self.spareDstVlan, QinQ):
            self._warn_type_mismatch("SPARE | VLAN", "QinQ", "VLAN Ranges", "spare_destination_vlan_qinq")
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
            self._warn_type_mismatch("MAIN | Multicast Address", "IP Address", "Pool ID", "main_destination_address_ip")
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
            self._warn_type_mismatch(
                "SPARE | Multicast Address", "IP Address", "Pool ID", "spare_destination_address_ip"
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
            self._warn_type_mismatch(
                "MAIN | Multicast Address", "Pool ID", "IP Address", "main_destination_address_pool"
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
            self._warn_type_mismatch(
                "SPARE | Multicast Address", "Pool ID", "IP Address", "spare_destination_address_pool"
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
