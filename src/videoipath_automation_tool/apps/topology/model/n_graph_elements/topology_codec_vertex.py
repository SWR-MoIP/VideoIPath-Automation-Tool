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
