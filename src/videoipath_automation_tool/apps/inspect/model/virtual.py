"""Wire models for Inspect virtual devices and port templates (verified 2025.4.9).

The VideoIPath UI creates topology virtual devices via network actions
(``updateVirtualInstances``, ``updateVirtualTemplates``, ``addVirtualTopology``).
After create, placement / metadata / edges / removal use the same collector
``updateTopology`` path as physical devices. Status reads use
``status/network/virtualDevices`` and ``status/network/virtualTemplates``.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from videoipath_automation_tool.apps.inspect.model.common import (
    InspectApiBaseModel,
    InspectApiPostRequestHeader,
    InspectApiRestV2Header,
    InspectApiSimpleActionResult,
)


class InspectApiVirtualPortFromTemplate(InspectApiBaseModel):
    """One port instantiation from a port template (wire: ``vertices[]`` entry)."""

    templateId: str
    count: int = 1


class InspectApiVirtualModule(InspectApiBaseModel):
    """A module on a virtual device definition (wire shape shared by reads and writes)."""

    moduleNumber: int | None = None
    vertices: list[InspectApiVirtualPortFromTemplate] = Field(default_factory=list)


class InspectApiVirtualDeviceFields(InspectApiBaseModel):
    """``lookupInspectDevice.fields.virtualDeviceFields`` (verified 2025.4.9)."""

    dynamic: list[InspectApiVirtualModule] = Field(default_factory=list)
    manual: list[InspectApiVirtualModule] = Field(default_factory=list)


class InspectApiVirtualDeviceInstance(InspectApiBaseModel):
    """One entry from ``status/network/virtualDevices`` (create/update body omits ``_id``)."""

    id: str | None = Field(default=None, alias="_id")
    vid: str | None = Field(default=None, alias="_vid")
    modules: list[InspectApiVirtualModule] = Field(default_factory=list)


class InspectApiVirtualDeviceWriteBody(InspectApiBaseModel):
    """Body for one virtual device in ``updateVirtualInstances`` add/update."""

    modules: list[InspectApiVirtualModule] = Field(default_factory=list)


class InspectApiUpdateVirtualInstancesData(InspectApiBaseModel):
    add: list[InspectApiVirtualDeviceWriteBody] = Field(default_factory=list)
    update: dict[str, InspectApiVirtualDeviceWriteBody] = Field(default_factory=dict)
    remove: list[str] = Field(default_factory=list)
    force: bool = False


class InspectApiUpdateVirtualInstancesRequest(InspectApiBaseModel):
    header: InspectApiPostRequestHeader = Field(default_factory=InspectApiPostRequestHeader)
    data: InspectApiUpdateVirtualInstancesData


class InspectApiUpdateVirtualInstancesValidation(InspectApiBaseModel):
    createIds: list[Any] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)
    result: InspectApiSimpleActionResult


class InspectApiUpdateVirtualInstancesResponseData(InspectApiBaseModel):
    addedDeviceLabels: dict[str, str] = Field(default_factory=dict)
    res: InspectApiSimpleActionResult
    validation: InspectApiUpdateVirtualInstancesValidation


class InspectApiUpdateVirtualInstancesResponse(InspectApiBaseModel):
    data: InspectApiUpdateVirtualInstancesResponseData
    header: InspectApiRestV2Header


class InspectApiVirtualTemplateVertex(InspectApiBaseModel):
    """Vertex config embedded in a port template (lossless; ``extra="allow"``)."""

    type: str | None = None
    vertexType: str | None = None
    codecFormat: str | None = None
    isVirtual: bool | None = None
    active: bool | None = None
    control: str | None = None
    configPriority: str | None = None
    useAsEndpoint: bool | None = None
    deviceId: str | None = None
    descriptor: dict[str, Any] | None = None
    fDescriptor: dict[str, Any] | None = None
    custom: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    maps: list[Any] = Field(default_factory=list)
    sipsMode: str | None = None
    imgUrl: str | None = None
    extraAlertFilters: list[Any] = Field(default_factory=list)
    gpid: dict[str, Any] | None = None


class InspectApiVirtualTemplateItem(InspectApiBaseModel):
    """One entry from ``status/network/virtualTemplates``."""

    id: str = Field(alias="_id")
    vid: str | None = Field(default=None, alias="_vid")
    label: str
    vertex: InspectApiVirtualTemplateVertex


class InspectApiVirtualTemplateWriteBody(InspectApiBaseModel):
    """Body for one port template in ``updateVirtualTemplates.add``."""

    label: str
    vertex: dict[str, Any]


class InspectApiUpdateVirtualTemplatesData(InspectApiBaseModel):
    add: dict[str, InspectApiVirtualTemplateWriteBody] = Field(default_factory=dict)
    remove: list[str] = Field(default_factory=list)
    force: bool = False


class InspectApiUpdateVirtualTemplatesRequest(InspectApiBaseModel):
    header: InspectApiPostRequestHeader = Field(default_factory=InspectApiPostRequestHeader)
    data: InspectApiUpdateVirtualTemplatesData


class InspectApiAddVirtualTopologyData(InspectApiBaseModel):
    deviceId: str
    moduleId: int
    countByVertexTemplate: dict[str, int] = Field(default_factory=dict)


class InspectApiAddVirtualTopologyRequest(InspectApiBaseModel):
    header: InspectApiPostRequestHeader = Field(default_factory=InspectApiPostRequestHeader)
    data: InspectApiAddVirtualTopologyData


__all__ = [
    "InspectApiAddVirtualTopologyData",
    "InspectApiAddVirtualTopologyRequest",
    "InspectApiUpdateVirtualInstancesData",
    "InspectApiUpdateVirtualInstancesRequest",
    "InspectApiUpdateVirtualInstancesResponse",
    "InspectApiUpdateVirtualInstancesResponseData",
    "InspectApiUpdateVirtualInstancesValidation",
    "InspectApiUpdateVirtualTemplatesData",
    "InspectApiUpdateVirtualTemplatesRequest",
    "InspectApiVirtualDeviceFields",
    "InspectApiVirtualDeviceInstance",
    "InspectApiVirtualDeviceWriteBody",
    "InspectApiVirtualModule",
    "InspectApiVirtualPortFromTemplate",
    "InspectApiVirtualTemplateItem",
    "InspectApiVirtualTemplateVertex",
    "InspectApiVirtualTemplateWriteBody",
]
