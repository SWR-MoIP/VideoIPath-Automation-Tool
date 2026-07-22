from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# The icon types selectable in the VideoIPath UI (mirrors the topology app's ``IconType``; live data
# may contain further values, so read/write surfaces use the permissive ``InspectIconType | str``).
InspectIconType = Literal[
    "default",
    "none",
    "device",
    "camera",
    "monitor",
    "encoder",
    "decoder",
    "audioMixer",
    "videoMixer",
    "processingDevice",
    "transportStreamProcessor",
    "mediaDevice",
    "server",
    "gateway",
    "ipSwitchRouter",
    "vlanCloud",
    "videoAudioRouterMatrix",
    "encoderDecoder",
]

# Device icon size selectable in the UI (mirrors the topology app's ``IconSize``).
InspectIconSize = Literal["auto", "large", "medium", "small"]

# SDP polling strategy: "always" (Continuous), "once" (Fetch and Confirm), "video" (Continuous
# Video, Confirm Others). Mirrors the topology app's ``SdpStrategy``.
InspectSdpStrategy = Literal["always", "once", "video"]

# Vertex direction as reported in ``vertexInfo.vertexType`` (a "double" vertexInfo is the
# bidirectional case and is surfaced as "BiDirectional").
InspectVertexType = Literal["BiDirectional", "In", "Internal", "Out", "Undecided"]

# Vertex kind from the vertex edit form's ``typeFields.type``. "ip", "codec" and "router" are
# verified against a live 2025.4.9 server; "generic" is inferred from the nGraph element types.
# Read surfaces use the permissive ``InspectVertexKind | str`` for unknown future kinds.
InspectVertexKind = Literal["generic", "ip", "codec", "router"]

# Edge redundancy mode (mirrors the topology app's ``RedundancyMode``).
InspectRedundancyMode = Literal["Any", "OnlyMain", "OnlySpare"]

# Conflict priority for edges (``conflictPri``) and vertex control (``controlProps.configPriority``).
# The UI labels are off/high/normal/low; the edge form carries the priority as an int on the wire
# (verified 2025.4.9), so read/write surfaces convert with the mappings below.
InspectConfigPriority = Literal["off", "high", "normal", "low"]
CONFLICT_PRIORITY_TO_INT: dict[str, int] = {"off": 0, "high": 1, "normal": 2, "low": 3}
CONFLICT_PRIORITY_BY_INT: dict[int, str] = {value: name for name, value in CONFLICT_PRIORITY_TO_INT.items()}


class InspectApiBaseModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, validate_assignment=True, extra="allow")


class InspectInternalModel(BaseModel):
    model_config = ConfigDict(validate_assignment=True, arbitrary_types_allowed=True)


class InspectFrozenModel(InspectInternalModel):
    model_config = ConfigDict(frozen=True, slots=True, validate_assignment=True, arbitrary_types_allowed=True)


class InspectApiDescriptor(InspectApiBaseModel):
    desc: str = ""
    label: str = ""


class InspectApiCollection(InspectApiBaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list, alias="_items")


class InspectApiStatusSummary(InspectApiBaseModel):
    sa: int | str | None = None
    severity: int | str | None = None


class InspectApiStatusContext(InspectApiBaseModel):
    devicePid: str | None = None
    modulePid: str | None = None
    portPid: str | None = None


class InspectApiEndpointStatus(InspectApiBaseModel):
    context: InspectApiStatusContext | None = None
    label: str | None = None
    pid: str | None = None
    status: InspectApiStatusSummary | None = None


class InspectServiceStatus(InspectApiBaseModel):
    config: InspectApiStatusSummary | None = None
    total: InspectApiStatusSummary | None = None


class InspectApiRestV2Header(InspectApiBaseModel):
    auth: bool
    caption: str
    code: str
    errorCodes: list[Any] = Field(default_factory=list)
    errorDetails: list[Any] = Field(default_factory=list)
    id: str
    msg: list[str] = Field(default_factory=list)
    ok: bool
    user: str


class InspectApiPostRequestHeader(InspectApiBaseModel):
    id: int = 0


class InspectApiSimpleActionResult(InspectApiBaseModel):
    msg: list[str] = Field(default_factory=list)
    ok: bool


class InspectApiSimpleActionResponse(InspectApiBaseModel):
    data: InspectApiSimpleActionResult
    header: InspectApiRestV2Header


class InspectApiActionValidationErrorResponse(InspectApiBaseModel):
    header: InspectApiRestV2Header


__all__ = [
    "InspectApiActionValidationErrorResponse",
    "InspectApiBaseModel",
    "InspectFrozenModel",
    "InspectInternalModel",
    "InspectApiCollection",
    "InspectApiDescriptor",
    "InspectApiEndpointStatus",
    "InspectApiPostRequestHeader",
    "InspectApiRestV2Header",
    "InspectServiceStatus",
    "InspectApiSimpleActionResponse",
    "InspectApiSimpleActionResult",
    "InspectApiStatusContext",
    "InspectApiStatusSummary",
    "InspectConfigPriority",
    "InspectIconSize",
    "InspectIconType",
    "InspectRedundancyMode",
    "InspectSdpStrategy",
    "InspectVertexKind",
    "InspectVertexType",
]
