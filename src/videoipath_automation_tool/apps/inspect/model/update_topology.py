from __future__ import annotations

from typing import Any

from pydantic import Field

from videoipath_automation_tool.apps.inspect.model.common import (
    InspectApiBaseModel,
    InspectApiPostRequestHeader,
    InspectApiRestV2Header,
)
from videoipath_automation_tool.apps.inspect.model.ngraph import (
    InspectApiBaseDevice,
    InspectApiCodecVertex,
    InspectApiGenericVertex,
    InspectApiIpVertex,
    InspectApiNGraphResourceTransform,
    InspectApiUnidirectionalEdge,
)


InspectApiReplaceVertex = InspectApiIpVertex | InspectApiCodecVertex | InspectApiGenericVertex | dict[str, Any]
InspectApiReplaceDevice = InspectApiBaseDevice | dict[str, Any]
InspectApiReplaceResourceTransform = InspectApiNGraphResourceTransform | dict[str, Any]


class InspectApiUpdateTopologyData(InspectApiBaseModel):
    replaceDevices: dict[str, InspectApiReplaceDevice] = Field(default_factory=dict)
    replaceVertices: dict[str, InspectApiReplaceVertex] = Field(default_factory=dict)
    replaceEdges: dict[str, InspectApiUnidirectionalEdge] = Field(default_factory=dict)
    replaceResourceTransforms: dict[str, InspectApiReplaceResourceTransform] = Field(default_factory=dict)
    addExternalEdges: list[InspectApiUnidirectionalEdge] = Field(default_factory=list)
    remove: list[str] = Field(default_factory=list)
    force: bool = False


class InspectApiUpdateTopologyRequest(InspectApiBaseModel):
    header: InspectApiPostRequestHeader = Field(default_factory=InspectApiPostRequestHeader)
    data: InspectApiUpdateTopologyData = Field(default_factory=InspectApiUpdateTopologyData)


class InspectApiUpdateTopologyResult(InspectApiBaseModel):
    msg: list[str] = Field(default_factory=list)
    ok: bool


class InspectApiUpdateTopologyValidationDetail(InspectApiBaseModel):
    isCancel: bool | None = None
    isProduct: bool | None = None
    resolvable: bool | None = None
    rev: str | None = None
    status: int | str | None = None
    type: str | None = None


class InspectApiUpdateTopologyValidation(InspectApiBaseModel):
    createIds: list[str] = Field(default_factory=list)
    details: dict[str, InspectApiUpdateTopologyValidationDetail] = Field(default_factory=dict)
    result: InspectApiUpdateTopologyResult


class InspectApiUpdateTopologyResponseData(InspectApiBaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list)
    res: InspectApiUpdateTopologyResult
    validation: InspectApiUpdateTopologyValidation


class InspectApiUpdateTopologyResponse(InspectApiBaseModel):
    data: InspectApiUpdateTopologyResponseData
    header: InspectApiRestV2Header

    @property
    def committed(self) -> bool:
        return self.header.ok and self.data.res.ok and self.data.validation.result.ok


__all__ = [
    "InspectApiReplaceDevice",
    "InspectApiReplaceResourceTransform",
    "InspectApiReplaceVertex",
    "InspectApiUpdateTopologyData",
    "InspectApiUpdateTopologyRequest",
    "InspectApiUpdateTopologyResponse",
    "InspectApiUpdateTopologyResponseData",
    "InspectApiUpdateTopologyResult",
    "InspectApiUpdateTopologyValidation",
    "InspectApiUpdateTopologyValidationDetail",
]
