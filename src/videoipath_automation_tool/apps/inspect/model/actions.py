from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from videoipath_automation_tool.apps.inspect.model.common import (
    InspectApiBaseModel,
    InspectApiDescriptor,
    InspectApiPostRequestHeader,
    InspectApiRestV2Header,
)


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
    virtualDeviceFields: dict[str, Any] | None = None


class InspectApiLookupInspectDeviceResponseData(InspectApiBaseModel):
    assignedTags: InspectApiAssignedTags
    fields: InspectApiLookupInspectDeviceFields


class InspectApiLookupInspectDeviceResponse(InspectApiBaseModel):
    data: InspectApiLookupInspectDeviceResponseData
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
    "InspectApiLookupInspectDeviceFields",
    "InspectApiLookupInspectDeviceRequest",
    "InspectApiLookupInspectDeviceResponse",
    "InspectApiLookupInspectDeviceResponseData",
    "InspectApiLookupSyncInfoItem",
    "InspectApiLookupSyncInfoRequest",
    "InspectApiLookupSyncInfoResponse",
    "InspectApiSyncDevicesRequest",
    "InspectApiSyncDevicesRequestData",
]
