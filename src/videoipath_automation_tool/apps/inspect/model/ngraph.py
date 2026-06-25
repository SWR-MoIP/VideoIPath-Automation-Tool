from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from videoipath_automation_tool.apps.inspect.model.common import (
    InspectApiBaseModel,
    InspectApiDescriptor,
)


InspectApiNGraphElementType = Literal[
    "baseDevice",
    "codecVertex",
    "genericVertex",
    "ipVertex",
    "nGraphResourceTransform",
    "unidirectionalEdge",
]


class InspectApiGpid(InspectApiBaseModel):
    component: int | None = None
    pointId: list[str] = Field(default_factory=list)


class InspectApiMapElement(InspectApiBaseModel):
    cType: str = "Topology"
    id: str = ""
    name: str = ""
    visible: bool = True
    x: float = 0.0
    y: float = 0.0


class InspectApiNGraphElement(InspectApiBaseModel):
    id: str = Field(alias="_id")
    rev: str | None = Field(default=None, alias="_rev")
    vid: str | None = Field(default=None, alias="_vid")
    descriptor: InspectApiDescriptor = Field(default_factory=InspectApiDescriptor)
    fDescriptor: InspectApiDescriptor = Field(default_factory=InspectApiDescriptor)
    tags: list[str] = Field(default_factory=list)
    type: InspectApiNGraphElementType


class InspectApiBaseDevice(InspectApiNGraphElement):
    type: Literal["baseDevice"] = "baseDevice"
    iconSize: str = "medium"
    iconType: str = "default"
    isVirtual: bool = False
    maps: list[InspectApiMapElement] = Field(default_factory=list)
    sdpStrategy: str = "always"
    siteId: str | None = None


class InspectApiVertex(InspectApiNGraphElement):
    deviceId: str
    gpid: InspectApiGpid | None = None
    configPriority: str | int | None = None
    control: str | int | None = None
    custom: dict[str, Any] = Field(default_factory=dict)
    extraAlertFilters: list[Any] = Field(default_factory=list)
    imgUrl: str | None = None
    isVirtual: bool = False
    maps: list[InspectApiMapElement] = Field(default_factory=list)
    sipsMode: str | None = None
    useAsEndpoint: bool | None = None
    vertexType: str | None = None


class InspectApiIpVertex(InspectApiVertex):
    type: Literal["ipVertex"] = "ipVertex"
    ipAddress: str | None = None
    ipNetmask: str | None = None
    public: bool | None = None
    supportsCpipeCfg: bool | None = None
    supportsIgmpCfg: bool | None = None
    supportsMacForwardingCfg: bool | None = None
    supportsNsoCfg: bool | None = None
    supportsOpenflowCfg: bool | None = None
    supportsStaticIgmpCfg: bool | None = None
    supportsVlanCfg: bool | None = None
    supportsVplsCfg: bool | None = None
    vlanId: str | None = None
    vrfId: str | None = None


class InspectApiCodecVertex(InspectApiVertex):
    type: Literal["codecVertex"] = "codecVertex"
    codecFormat: str | None = None
    codecType: str | None = None


class InspectApiGenericVertex(InspectApiVertex):
    type: Literal["genericVertex"] = "genericVertex"


class InspectApiWeightFactorBandwidth(InspectApiBaseModel):
    weight: int = 0


class InspectApiWeightFactorService(InspectApiBaseModel):
    max: int = 100
    weight: int = 0


class InspectApiWeightFactors(InspectApiBaseModel):
    bandwidth: InspectApiWeightFactorBandwidth = Field(default_factory=InspectApiWeightFactorBandwidth)
    service: InspectApiWeightFactorService = Field(default_factory=InspectApiWeightFactorService)


class InspectApiUnidirectionalEdge(InspectApiNGraphElement):
    type: Literal["unidirectionalEdge"] = "unidirectionalEdge"
    active: bool = True
    bandwidth: float | int = -1.0
    capacity: int = 65535
    conflictPri: int | str = 0
    excludeFormats: list[str] = Field(default_factory=list)
    fromId: str
    includeFormats: list[str] = Field(default_factory=list)
    redundancyMode: str = "Any"
    toId: str
    weight: int = 0
    weightFactors: InspectApiWeightFactors = Field(default_factory=InspectApiWeightFactors)


class InspectApiNGraphResourceTransform(InspectApiNGraphElement):
    type: Literal["nGraphResourceTransform"] = "nGraphResourceTransform"


__all__ = [
    "InspectApiBaseDevice",
    "InspectApiCodecVertex",
    "InspectApiGenericVertex",
    "InspectApiGpid",
    "InspectApiIpVertex",
    "InspectApiMapElement",
    "InspectApiNGraphElement",
    "InspectApiNGraphElementType",
    "InspectApiNGraphResourceTransform",
    "InspectApiUnidirectionalEdge",
    "InspectApiVertex",
    "InspectApiWeightFactorBandwidth",
    "InspectApiWeightFactorService",
    "InspectApiWeightFactors",
]
