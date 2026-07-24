from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import IntEnum
from typing import TYPE_CHECKING, Any, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from videoipath_automation_tool.apps.inspect.snapshot import InspectSnapshot

# Sentinel returned by :meth:`InspectSnapshot.get_staged_value` / :meth:`InspectEditableModel._staged`
# when no pending edit exists for a field.
_STAGED_MISSING: Any = object()

_T = TypeVar("_T")


class InspectSeverity(IntEnum):
    """VideoIPath status/alarm severity. Int-valued so ``== N``, ``int(x)``, and ordering still
    work; ``str(x)`` / ``.label`` give the human label. Unknown wire codes are kept as raw ints
    by the model validators (never crash).

    Scale derived from VideoIPath 2026.2.0 (built-in correlation templates + live alarms + sync
    info); higher is worse.
    """

    NONE = 0
    OK = 1
    NOTICE = 2
    WARNING = 3
    MINOR = 4
    MAJOR = 5
    CRITICAL = 6

    def __str__(self) -> str:
        return self.label

    @property
    def label(self) -> str:
        return _SEVERITY_LABELS[self]


def map_severity(raw: Any) -> InspectSeverity | int | str | None:
    """Known int → :class:`InspectSeverity`; ``None`` / str / unknown int pass through unchanged."""
    if isinstance(raw, InspectSeverity):
        return raw
    if isinstance(raw, int) and not isinstance(raw, bool) and raw in _SEVERITY_LABELS:
        return InspectSeverity(raw)
    return raw


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

# SIPS mode on vertices (mirrors the topology app's ``SipsMode``).
InspectSipsMode = Literal["NONE", "SIPSAuto", "SIPSDuplicate", "SIPSMerge", "SIPSSplit"]

# Vertex control level (mirrors the topology app's ``Control``).
InspectControl = Literal["full", "off", "semi"]

# Codec format on codec vertices (mirrors the topology app's ``CodecFormat``).
InspectCodecFormat = Literal["Video", "Audio", "ASI", "Ancillary"]

# Map coordinate type on nGraph map elements (mirrors topology ``cType``).
InspectMapCType = Literal["Topology", "Geo"]


def format_repr(obj: object, /, **fields: Any) -> str:
    """Concise ``ClassName(k=v, ...)`` repr. Callable values are evaluated defensively
    (skipped on error); None values are omitted. Never raises."""
    parts: list[str] = []
    for key, value in fields.items():
        if callable(value):
            try:
                value = value()
            except Exception:
                continue
        if value is None:
            continue
        parts.append(f"{key}={value!r}")
    return f"{type(obj).__name__}({', '.join(parts)})"


class InspectApiBaseModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, validate_assignment=True, extra="allow")


class InspectInternalModel(BaseModel):
    model_config = ConfigDict(validate_assignment=True, arbitrary_types_allowed=True)


class InspectFrozenModel(InspectInternalModel):
    model_config = ConfigDict(frozen=True, slots=True, validate_assignment=True, arbitrary_types_allowed=True)


class InspectEditableModel(InspectInternalModel, ABC):
    """Mutable domain view: identity fields are set at construction; editable attributes are
    exposed as property setters that stage pending edits on the snapshot (read-your-writes).

    Subclasses must provide ``snapshot``, ``id``, and :attr:`_edit_kind`. Staging helpers
    (:meth:`_stage` / :meth:`_staged`) are shared here.
    """

    model_config = ConfigDict(validate_assignment=True, arbitrary_types_allowed=True)

    snapshot: InspectSnapshot

    @property
    @abstractmethod
    def _edit_kind(self) -> Literal["device", "vertex", "edge", "module"]:
        """Snapshot staging namespace for this entity (``device`` / ``vertex`` / ``edge`` / ``module``)."""

    def _stage(self, field: str, value: Any) -> None:
        self.snapshot.stage_edit(self._edit_kind, self.id, field, value)

    def _staged(self, field: str) -> Any:
        return self.snapshot.get_staged_value(self._edit_kind, self.id, field)

    def _staged_or(
        self,
        field: str,
        fallback: Callable[[], _T],
        *,
        adapt: Callable[[Any], _T] | None = None,
    ) -> _T:
        """Return the staged value for ``field``, else ``fallback()``.

        When a staged value exists and ``adapt`` is given, ``adapt(staged)`` is returned (e.g.
        ``list`` / ``dict`` for defensive copies).
        """
        staged = self._staged(field)
        if staged is not _STAGED_MISSING:
            return adapt(staged) if adapt is not None else staged
        return fallback()


class InspectApiDescriptor(InspectApiBaseModel):
    desc: str = ""
    label: str = ""


class InspectApiCollection(InspectApiBaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list, alias="_items")


class InspectApiStatusSummary(InspectApiBaseModel):
    sa: InspectSeverity | int | str | None = None
    severity: InspectSeverity | int | str | None = None

    @field_validator("sa", "severity", mode="before")
    @classmethod
    def _map_severity_fields(cls, value: Any) -> Any:
        return map_severity(value)


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


# --- Internal ---

_SEVERITY_LABELS: dict[InspectSeverity, str] = {
    InspectSeverity.NONE: "None",
    InspectSeverity.OK: "OK",
    InspectSeverity.NOTICE: "Notice",
    InspectSeverity.WARNING: "Warning",
    InspectSeverity.MINOR: "Minor",
    InspectSeverity.MAJOR: "Major",
    InspectSeverity.CRITICAL: "Critical",
}


__all__ = [
    "InspectApiActionValidationErrorResponse",
    "InspectApiBaseModel",
    "InspectEditableModel",
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
    "CONFLICT_PRIORITY_BY_INT",
    "CONFLICT_PRIORITY_TO_INT",
    "InspectCodecFormat",
    "InspectConfigPriority",
    "InspectControl",
    "InspectIconSize",
    "InspectIconType",
    "InspectMapCType",
    "InspectRedundancyMode",
    "InspectSdpStrategy",
    "InspectSeverity",
    "InspectSipsMode",
    "InspectVertexKind",
    "InspectVertexType",
    "format_repr",
    "map_severity",
    "_STAGED_MISSING",
]
