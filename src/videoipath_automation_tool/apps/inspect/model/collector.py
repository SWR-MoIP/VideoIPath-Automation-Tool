from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from videoipath_automation_tool.apps.inspect.model.common import (
    InspectApiBaseModel,
    InspectApiCollection,
    InspectApiDescriptor,
    InspectApiEndpointStatus,
    InspectApiRestV2Header,
    InspectApiStatusContext,
    InspectServiceStatus,
    InspectApiStatusSummary,
)


class InspectApiGenericServiceFields(InspectApiBaseModel):
    allocationState: int | None = None
    cancelTime: str | None = None
    descriptor: InspectApiDescriptor | None = None
    locked: bool | None = None
    state: int | None = None
    tags: list[str] = Field(default_factory=list)


class InspectApiPathServiceFields(InspectApiBaseModel):
    bid: str
    ctype: int | None = None
    formatSubState: int | None = None
    from_: str | None = Field(default=None, alias="from")
    fromLabel: str | None = None
    fromPid: str | None = None
    fromStatus: InspectApiStatusSummary | None = None
    generic: InspectApiGenericServiceFields | None = None
    isMain: bool | None = None
    serviceStatus: InspectServiceStatus | None = None
    to: str | None = None
    toLabel: str | None = None
    toPid: str | None = None
    toStatus: InspectApiStatusSummary | None = None


class InspectApiPathStructure(InspectApiBaseModel):
    deviceId: str | None = None
    deviceLabel: str | None = None
    devicePid: str | None = None
    expectConfig: bool | None = None
    inputStatus: InspectApiEndpointStatus | None = None
    moduleAndDeviceStatus: InspectApiStatusSummary | None = None
    outputStatus: InspectApiEndpointStatus | None = None


class InspectApiPathSegment(InspectApiBaseModel):
    bid: str
    ipDesc: str | None = None
    structure: InspectApiPathStructure | None = None


class InspectApiPathItem(InspectApiBaseModel):
    id: str = Field(alias="_id")
    vid: str = Field(alias="_vid")
    path: list[InspectApiPathSegment] = Field(default_factory=list)
    serviceFields: InspectApiPathServiceFields


class InspectApiNodeMeta(InspectApiBaseModel):
    coordinates: dict[str, float | int | str | None] | None = None
    hwPanelType: str | None = None
    iconSize: str | None = None
    iconType: str | None = None
    isCore: bool | None = None
    isVirtual: bool | None = None
    sdpStrategy: str | None = None
    siteId: str | None = None
    tags: list[str] = Field(default_factory=list)


class InspectApiVertexInfoFields(InspectApiBaseModel):
    isActive: bool | None = None
    isControlled: bool | None = None
    isEndpoint: bool | None = None


class InspectApiSingleVertexInfo(InspectApiBaseModel):
    type: Literal["single"] = "single"
    id: str | None = None
    label: str | None = None
    vertexType: str | None = None
    fields: InspectApiVertexInfoFields | None = None


class InspectApiDoubleVertexInfo(InspectApiBaseModel):
    type: Literal["double"] = "double"
    in_: InspectApiSingleVertexInfo | None = Field(default=None, alias="in")
    out: InspectApiSingleVertexInfo | None = None


class InspectApiPathDescriptionItem(InspectApiBaseModel):
    bookingId: str | None = None
    deviceLevel: dict[str, Any] | None = None
    fromStatus: InspectApiStatusSummary | None = None
    isMain: bool | None = None
    serviceLabel: str | None = None
    serviceLevel: dict[str, Any] | None = None
    serviceStatus: InspectServiceStatus | InspectApiStatusSummary | None = None
    toStatus: InspectApiStatusSummary | None = None


class InspectPortStatus(InspectApiBaseModel):
    id: str | None = Field(default=None, alias="_id")
    vid: str | None = Field(default=None, alias="_vid")
    context: InspectApiStatusContext | None = None
    descriptor: InspectApiDescriptor | None = None
    label: str | None = None
    pid: str | None = None
    relatedNodeTags: list[str] = Field(default_factory=list)
    resourceId: str | None = None
    status: InspectApiStatusSummary | None = None
    tagsInfo: dict[str, Any] | None = None
    vertexInfo: InspectApiSingleVertexInfo | InspectApiDoubleVertexInfo | dict[str, Any] | None = None
    pathDescriptions: dict[str, InspectApiPathDescriptionItem] = Field(default_factory=dict)

    @property
    def assigned_tags(self) -> list[str]:
        """Effective tags assigned to this port (from ``tagsInfo.assigned.all``)."""
        if not self.tagsInfo:
            return []
        assigned = self.tagsInfo.get("assigned")
        if isinstance(assigned, dict) and isinstance(assigned.get("all"), list):
            return list(assigned["all"])
        return []

    @property
    def effective_label(self) -> str | None:
        if self.descriptor is not None and self.descriptor.label:
            return self.descriptor.label
        return self.label


class InspectApiModuleStatus(InspectApiBaseModel):
    id: str | None = Field(default=None, alias="_id")
    vid: str | None = Field(default=None, alias="_vid")
    context: InspectApiStatusContext | None = None
    descriptor: InspectApiDescriptor | None = None
    label: str | None = None
    pid: str | None = None
    ports: dict[str, InspectPortStatus] | list[InspectPortStatus] = Field(default_factory=dict)
    status: InspectApiStatusSummary | None = None


class InspectApiNodeStatusItem(InspectApiBaseModel):
    id: str = Field(alias="_id")
    vid: str | None = Field(default=None, alias="_vid")
    context: InspectApiStatusContext | None = None
    descriptor: InspectApiDescriptor | None = None
    deviceId: str | None = None
    fDescriptor: InspectApiDescriptor | None = None
    hasEndpoints: bool | None = None
    label: str | None = None
    meta: InspectApiNodeMeta | None = None
    modules: dict[str, InspectApiModuleStatus] | list[InspectApiModuleStatus] = Field(default_factory=dict)
    pathDescriptions: dict[str, InspectApiPathDescriptionItem] = Field(default_factory=dict)
    pid: str | None = None
    ptpDeviceStatus: dict[str, Any] | None = None
    relatedNodeTags: list[str] = Field(default_factory=list)
    resourceId: str | None = None
    status: InspectApiStatusSummary | None = None
    syncSeverity: int | str | None = None
    tags: list[str] = Field(default_factory=list)
    tagsInfo: dict[str, Any] | None = None

    @property
    def effective_label(self) -> str | None:
        """The label the UI shows: user ``descriptor.label``, falling back to the device-reported
        ``fDescriptor.label`` (and finally the legacy top-level ``label`` field, if present)."""
        if self.descriptor is not None and self.descriptor.label:
            return self.descriptor.label
        if self.fDescriptor is not None and self.fDescriptor.label:
            return self.fDescriptor.label
        return self.label

    @property
    def coordinates(self) -> dict[str, float | int | str | None] | None:
        return self.meta.coordinates if self.meta is not None else None


class InspectApiExternalEdgeLiveStatus(InspectApiBaseModel):
    alarm: int | str | None = None
    bandwidth: int | float | str | None = None
    maintenance: int | str | None = None
    ptp: int | str | None = None


class InspectApiExternalEdgeStatus(InspectApiBaseModel):
    bandwidth: float | int | None = None
    fromStatus: InspectApiEndpointStatus | None = None
    id: str
    maxBandwidth: float | int | None = None
    pathDescriptions: dict[str, InspectApiPathDescriptionItem] = Field(default_factory=dict)
    ratio: float | int | None = None
    status: InspectApiExternalEdgeLiveStatus | None = None
    toStatus: InspectApiEndpointStatus | None = None


class InspectApiExternalEdgeSide(InspectApiBaseModel):
    data: dict[str, InspectApiExternalEdgeStatus] = Field(default_factory=dict)
    devicePid: str | None = None
    label: str | None = None


class InspectApiExternalEdgesByDeviceKeyItem(InspectApiBaseModel):
    id: str = Field(alias="_id")
    vid: str = Field(alias="_vid")
    primary: InspectApiExternalEdgeSide
    secondary: InspectApiExternalEdgeSide
    status: InspectApiExternalEdgeLiveStatus | None = None


class InspectApiMaintenanceBookingItem(InspectApiBaseModel):
    id: str = Field(alias="_id")
    vid: str | None = Field(default=None, alias="_vid")


class InspectApiSuperProfileItem(InspectApiBaseModel):
    id: str = Field(alias="_id")
    vid: str | None = Field(default=None, alias="_vid")


class InspectApiTagInfoItem(InspectApiBaseModel):
    id: str = Field(alias="_id")
    vid: str | None = Field(default=None, alias="_vid")


class InspectApiCollectorInspect(InspectApiBaseModel):
    nodeStatus: InspectApiCollection = Field(default_factory=InspectApiCollection)
    paths: InspectApiCollection = Field(default_factory=InspectApiCollection)

    @property
    def node_status_items(self) -> list[InspectApiNodeStatusItem]:
        return [InspectApiNodeStatusItem.model_validate(item) for item in self.nodeStatus.items]

    @property
    def path_items(self) -> list[InspectApiPathItem]:
        return [InspectApiPathItem.model_validate(item) for item in self.paths.items]


class InspectApiCollector(InspectApiBaseModel):
    inspect: InspectApiCollectorInspect = Field(default_factory=InspectApiCollectorInspect)
    externalEdgesByDeviceKey: InspectApiCollection = Field(default_factory=InspectApiCollection)
    maintenanceBookings: InspectApiCollection = Field(default_factory=InspectApiCollection)
    security: dict[str, Any] = Field(default_factory=dict)
    superProfiles: InspectApiCollection = Field(default_factory=InspectApiCollection)
    tagInfo: InspectApiCollection = Field(default_factory=InspectApiCollection)

    @property
    def external_edges_by_device_key_items(self) -> list[InspectApiExternalEdgesByDeviceKeyItem]:
        return [
            InspectApiExternalEdgesByDeviceKeyItem.model_validate(item) for item in self.externalEdgesByDeviceKey.items
        ]

    @property
    def maintenance_booking_items(self) -> list[InspectApiMaintenanceBookingItem]:
        return [InspectApiMaintenanceBookingItem.model_validate(item) for item in self.maintenanceBookings.items]

    @property
    def super_profile_items(self) -> list[InspectApiSuperProfileItem]:
        return [InspectApiSuperProfileItem.model_validate(item) for item in self.superProfiles.items]

    @property
    def tag_info_items(self) -> list[InspectApiTagInfoItem]:
        return [InspectApiTagInfoItem.model_validate(item) for item in self.tagInfo.items]


class InspectApiCollectorStatus(InspectApiBaseModel):
    collector: InspectApiCollector = Field(default_factory=InspectApiCollector)


class InspectApiCollectorResponseData(InspectApiBaseModel):
    status: InspectApiCollectorStatus


class InspectApiCollectorResponse(InspectApiBaseModel):
    data: InspectApiCollectorResponseData
    header: InspectApiRestV2Header


__all__ = [
    "InspectApiCollector",
    "InspectApiCollectorInspect",
    "InspectApiCollectorResponse",
    "InspectApiCollectorResponseData",
    "InspectApiCollectorStatus",
    "InspectApiDoubleVertexInfo",
    "InspectApiExternalEdgeLiveStatus",
    "InspectApiExternalEdgeSide",
    "InspectApiExternalEdgeStatus",
    "InspectApiExternalEdgesByDeviceKeyItem",
    "InspectApiGenericServiceFields",
    "InspectApiMaintenanceBookingItem",
    "InspectApiModuleStatus",
    "InspectApiNodeMeta",
    "InspectApiNodeStatusItem",
    "InspectApiPathDescriptionItem",
    "InspectApiPathItem",
    "InspectApiPathSegment",
    "InspectApiPathServiceFields",
    "InspectApiPathStructure",
    "InspectPortStatus",
    "InspectApiSingleVertexInfo",
    "InspectApiSuperProfileItem",
    "InspectApiTagInfoItem",
    "InspectApiVertexInfoFields",
]
