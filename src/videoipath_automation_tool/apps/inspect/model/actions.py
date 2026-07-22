from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from videoipath_automation_tool.apps.inspect.model.common import (
    InspectApiBaseModel,
    InspectApiDescriptor,
    InspectApiPostRequestHeader,
    InspectApiRestV2Header,
)
from videoipath_automation_tool.apps.inspect.model.virtual import InspectApiVirtualDeviceFields


class InspectApiLookupInspectDeviceRequest(InspectApiBaseModel):
    header: InspectApiPostRequestHeader = Field(default_factory=InspectApiPostRequestHeader)
    data: str


class InspectApiAssignedTags(InspectApiBaseModel):
    all: list[str] = Field(default_factory=list)
    inherited: dict[str, Any] = Field(default_factory=dict)
    inheritedConflict: bool = False
    local: dict[str, Any] = Field(default_factory=dict)


class InspectApiLookupInspectDeviceFields(InspectApiBaseModel):
    coordinates: dict[str, float | int] | None = None
    descriptor: InspectApiDescriptor
    iconSize: str | None = None
    iconType: str | None = None
    localAssignedTags: list[str] = Field(default_factory=list)
    sdpStrategy: str | None = None
    siteId: str | None = None
    tags: list[str] = Field(default_factory=list)
    virtualDeviceFields: InspectApiVirtualDeviceFields | None = None


class InspectApiLookupInspectDeviceResponseData(InspectApiBaseModel):
    assignedTags: InspectApiAssignedTags
    fields: InspectApiLookupInspectDeviceFields


class InspectApiLookupInspectDeviceResponse(InspectApiBaseModel):
    data: InspectApiLookupInspectDeviceResponseData
    header: InspectApiRestV2Header


# --- Vertex lookup / edit form (also the replaceVertices write shape, verified 2025.4.9) ---


class InspectApiCodecGeneric(InspectApiBaseModel):
    """The ``typeFields.generic`` block of a codec vertex edit form (verified 2025.4.9). Nested
    endpoint blocks are kept as dicts for lossless round-tripping (``extra="allow"`` on the base)."""

    bidirPartnerId: str | None = None
    codecFormat: str | None = None
    extraFormats: list[Any] = Field(default_factory=list)
    mainDstInfo: dict[str, Any] | None = None
    mainSrcInfo: dict[str, Any] | None = None
    multiplicity: int | None = None
    partnerConfig: Any | None = None
    public: bool | None = None
    serviceId: Any | None = None
    spareDstInfo: dict[str, Any] | None = None
    spareSrcInfo: dict[str, Any] | None = None


class InspectApiCodecSpecific(InspectApiBaseModel):
    """The ``typeFields.specific`` block of a codec vertex edit form (verified 2025.4.9)."""

    isIgmpSource: bool | None = None
    sdpSupport: bool | None = None
    type: str | None = None


class InspectApiVertexTypeFields(InspectApiBaseModel):
    ipAddress: str | None = None
    ipNetmask: str | None = None
    parkPort: int | None = None
    public: bool | None = None
    supportsCpipeCfg: bool | None = None
    supportsIgmpCfg: bool | None = None
    supportsMacForwardingCfg: bool | None = None
    supportsNsoCfg: bool | None = None
    supportsOpenflowCfg: bool | None = None
    supportsStaticIgmpCfg: bool | None = None
    supportsVlanCfg: bool | None = None
    supportsVplsCfg: bool | None = None
    type: str | None = None
    vlanId: str | None = None
    vrfId: str | None = None
    # Codec vertices additionally carry ``generic`` / ``specific`` blocks here; they are preserved
    # losslessly by ``extra="allow"`` (declaring them would emit ``null`` on non-codec vertices and
    # break the byte-for-byte ``replaceVertices`` round-trip) and read back typed via
    # ``InspectApiCodecGeneric`` / ``InspectApiCodecSpecific`` in the codec vertex view.


class InspectApiVertexControlProps(InspectApiBaseModel):
    """Control properties of a controlled vertex (verified against a live 2025.4.9 server)."""

    configPriority: str | None = None
    onlyInitial: bool | None = None


class InspectApiVertexEditForm(InspectApiBaseModel):
    """The vertex ``fields`` object returned by ``lookupInspectVertexById`` — this exact shape is
    what ``replaceVertices`` accepts (update-only; verified 2025.4.9)."""

    active: bool | None = None
    controlProps: InspectApiVertexControlProps | None = None
    custom: dict[str, Any] = Field(default_factory=dict)
    desc: str = ""
    destinationMonitorLeader: bool | None = None
    extraAlertFilters: list[Any] = Field(default_factory=list)
    label: str = ""
    localAssignedTags: list[str] = Field(default_factory=list)
    queueable: bool | None = None
    sipsMode: str | None = None
    tags: list[str] = Field(default_factory=list)
    typeFields: InspectApiVertexTypeFields | None = None
    useAsEndpoint: bool | None = None


class InspectApiLookupVertexRequest(InspectApiBaseModel):
    header: InspectApiPostRequestHeader = Field(default_factory=InspectApiPostRequestHeader)
    data: str


class InspectApiLookupVerticesRequest(InspectApiBaseModel):
    header: InspectApiPostRequestHeader = Field(default_factory=InspectApiPostRequestHeader)
    data: list[str]


class InspectApiLookupVertexResponseData(InspectApiBaseModel):
    assignedTags: InspectApiAssignedTags | None = None
    context: dict[str, Any] | None = None
    customSchemas: dict[str, Any] = Field(default_factory=dict)
    fields: InspectApiVertexEditForm
    id: str
    isVirtual: bool | None = None
    vertexType: str | None = None


class InspectApiLookupVertexResponse(InspectApiBaseModel):
    data: InspectApiLookupVertexResponseData
    header: InspectApiRestV2Header


class InspectApiLookupVerticesResponse(InspectApiBaseModel):
    data: dict[str, InspectApiLookupVertexResponseData]
    header: InspectApiRestV2Header


# --- Edge lookup (also the replaceEdges write shape, verified 2025.4.9) ---


class InspectApiEdgeForm(InspectApiBaseModel):
    """The persisted edge object returned by ``lookupInspectEdgesByIds`` — this exact shape is what
    ``replaceEdges`` accepts (verified 2025.4.9). No ``_id`` / ``_rev`` / ``type`` in the write form."""

    active: bool = True
    bandwidth: float | int = -1.0
    capacity: int = 65535
    conflictPri: int | str = 0
    descriptor: InspectApiDescriptor = Field(default_factory=InspectApiDescriptor)
    excludeFormats: list[str] = Field(default_factory=list)
    fDescriptor: InspectApiDescriptor = Field(default_factory=InspectApiDescriptor)
    fromId: str
    includeFormats: list[str] = Field(default_factory=list)
    redundancyMode: str = "Any"
    tags: list[str] = Field(default_factory=list)
    toId: str
    weight: int = 1
    weightFactors: dict[str, Any] = Field(
        default_factory=lambda: {"bandwidth": {"weight": 0}, "service": {"max": 100, "weight": 0}}
    )


class InspectApiLookupEdgesRequest(InspectApiBaseModel):
    header: InspectApiPostRequestHeader = Field(default_factory=InspectApiPostRequestHeader)
    data: list[str]


class InspectApiLookupEdgeResponseItem(InspectApiBaseModel):
    edge: InspectApiEdgeForm
    fromDevice: str | None = None
    toDevice: str | None = None


class InspectApiLookupEdgesResponse(InspectApiBaseModel):
    data: dict[str, InspectApiLookupEdgeResponseItem]
    header: InspectApiRestV2Header


class InspectApiLookupSyncInfoRequest(InspectApiBaseModel):
    header: InspectApiPostRequestHeader = Field(default_factory=InspectApiPostRequestHeader)
    data: list[str]


class InspectApiLookupSyncInfoItem(InspectApiBaseModel):
    add: dict[str, Any] = Field(default_factory=dict)
    label: str
    remove: dict[str, Any] = Field(default_factory=dict)
    severity: int | str | None = None
    update: dict[str, Any] = Field(default_factory=dict)


class InspectApiLookupSyncInfoResponse(InspectApiBaseModel):
    data: dict[str, InspectApiLookupSyncInfoItem]
    header: InspectApiRestV2Header


class InspectApiAddDevicesItem(InspectApiBaseModel):
    id: str
    x: float | int
    y: float | int


class InspectApiAddDevicesRequest(InspectApiBaseModel):
    header: InspectApiPostRequestHeader = Field(default_factory=InspectApiPostRequestHeader)
    data: list[InspectApiAddDevicesItem]


class InspectApiSyncDevicesRequestData(InspectApiBaseModel):
    ids: list[str] = Field(default_factory=list)
    addOnly: bool
    conflictStrategy: Literal[0, 1, 2]


class InspectApiSyncDevicesRequest(InspectApiBaseModel):
    header: InspectApiPostRequestHeader = Field(default_factory=InspectApiPostRequestHeader)
    data: InspectApiSyncDevicesRequestData


__all__ = [
    "InspectApiAddDevicesItem",
    "InspectApiAddDevicesRequest",
    "InspectApiAssignedTags",
    "InspectApiCodecGeneric",
    "InspectApiCodecSpecific",
    "InspectApiEdgeForm",
    "InspectApiLookupEdgeResponseItem",
    "InspectApiLookupEdgesRequest",
    "InspectApiLookupEdgesResponse",
    "InspectApiLookupInspectDeviceFields",
    "InspectApiLookupInspectDeviceRequest",
    "InspectApiLookupInspectDeviceResponse",
    "InspectApiLookupInspectDeviceResponseData",
    "InspectApiLookupSyncInfoItem",
    "InspectApiLookupSyncInfoRequest",
    "InspectApiLookupSyncInfoResponse",
    "InspectApiLookupVerticesRequest",
    "InspectApiLookupVerticesResponse",
    "InspectApiLookupVertexRequest",
    "InspectApiLookupVertexResponse",
    "InspectApiLookupVertexResponseData",
    "InspectApiSyncDevicesRequest",
    "InspectApiSyncDevicesRequestData",
    "InspectApiVertexControlProps",
    "InspectApiVertexEditForm",
    "InspectApiVertexTypeFields",
]
