"""Vertex processor contract: one class, one required method, explicit per-engine registration.

A processor *decides* configuration; it never writes. It receives a detached, read-only
:class:`ProcessingContext` (exact device/module scope, immutable records built from fresh server
reads — no reference to the live Inspect snapshot) and validated parameters, and returns a typed
:class:`~videoipath_automation_tool.provisioning.models.ProcessorResult`. The engine validates the
output (scope, conflicts, capabilities), renders names, compares, and performs the writes.

Custom processors are trusted Python code, not sandboxed: the contract prevents accidental
library-side writes and enforces scope, but cannot stop a plugin that deliberately opens its own
network connection.
"""

from __future__ import annotations

import copy
import re
from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any, ClassVar, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, JsonValue, ValidationError

from videoipath_automation_tool.provisioning.errors import (
    ProcessorInputError,
    ProvisioningValidationError,
    ValidationIssue,
)
from videoipath_automation_tool.provisioning.models import (
    InterfaceBinding,
    PortBinding,
    ProcessorResult,
    issues_from_pydantic,
)

ParamsT = TypeVar("ParamsT", bound=BaseModel)


class _Record(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class VertexRecord(_Record):
    """Detached view of one vertex: identity, owning port/module, recognition facts, current values."""

    id: str
    port_id: str | None = None
    module_id: str | None = None
    factory_label: str | None = None
    """Device-reported (factory) label of the owning port."""
    port_label: str | None = None
    vertex_type: str | None = None
    """Direction from ``vertexInfo``: ``In`` / ``Out`` / ``Internal`` / ``Undecided``."""
    kind: str | None = None
    """``typeFields.type``: ``codec`` / ``ip`` / ``router`` / ``generic``."""
    label: str = ""
    description: str = ""
    use_as_endpoint: bool | None = None
    active: bool | None = None
    sips_mode: str | None = None
    tags: tuple[str, ...] = ()
    codec_format: str | None = None
    """Codec ``typeFields.generic.codecFormat`` (``Video`` / ``Audio`` / …)."""
    media_type: str | None = None
    """Codec ``typeFields.specific.type`` (e.g. ``video`` / ``audio``)."""
    sdp_support: bool | None = None
    main_destination_port: int | None = None
    """Codec ``typeFields.generic.mainDstInfo.port``."""
    spare_destination_port: int | None = None
    """Codec ``typeFields.generic.spareDstInfo.port``."""
    supports_static_igmp: bool | None = None
    """IP ``typeFields.supportsStaticIgmpCfg``."""


class PortRecord(_Record):
    id: str
    module_id: str | None = None
    factory_label: str | None = None
    label: str | None = None
    vertex_ids: tuple[str, ...] = ()


class ModuleRecord(_Record):
    id: str
    label: str | None = None
    local_tags: tuple[str, ...] | None = None
    """Locally assigned tags; ``None`` when the server representation cannot distinguish them."""


class DeviceRecord(_Record):
    id: str
    label: str = ""
    """Persisted descriptor label (``""`` when the factory label is in effect)."""
    description: str = ""
    factory_label: str | None = None
    icon_type: str | None = None
    icon_size: str | None = None
    sdp_strategy: str | None = None
    site_id: str | None = None
    coordinates: tuple[float, float] | None = None
    tags: tuple[str, ...] = ()


class SourceFacts(_Record):
    """Caller facts (no credentials)."""

    key: str
    label: str
    description: str | None = None
    module_position: str | None = None
    attributes: dict[str, JsonValue] = Field(default_factory=dict)


class DriverContext(_Record):
    """An Inventory record's driver identity and custom settings (Python field names)."""

    inventory_id: str
    driver_id: str
    address: str | None = None
    """Management address of the record (``cinfo.address``)."""
    custom_settings: dict[str, Any] = Field(default_factory=dict)


class ProcessingContext(_Record):
    """Everything a processor may use to decide configuration, scoped to one device or module.

    ``vertices`` contains only in-scope vertices (for a module target: that module's vertices); a
    processor cannot widen scope by returning other ids. ``owner`` is the topology owner's Inventory
    context; ``inventory`` is the source entity's own record when it differs from the owner.
    """

    source: SourceFacts
    scope: Literal["device", "module"]
    device_id: str
    module_id: str | None = None
    device: DeviceRecord | None = None
    modules: tuple[ModuleRecord, ...] = ()
    ports: tuple[PortRecord, ...] = ()
    vertices: tuple[VertexRecord, ...] = ()
    interfaces: tuple[InterfaceBinding, ...] = ()
    port_bindings: tuple[PortBinding, ...] = ()
    owner: DriverContext | None = None
    inventory: DriverContext | None = None
    capabilities: frozenset[str] = frozenset()

    def vertex(self, vertex_id: str) -> VertexRecord | None:
        return next((vertex for vertex in self.vertices if vertex.id == vertex_id), None)

    def find_vertices(
        self,
        *,
        kind: str | None = None,
        vertex_type: str | None = None,
        factory_label: str | None = None,
        module_id: str | None = None,
    ) -> list[VertexRecord]:
        """In-scope vertices matching every given filter (exact comparisons), ordered by id."""
        return [
            vertex
            for vertex in sorted(self.vertices, key=lambda record: record.id)
            if (kind is None or vertex.kind == kind)
            and (vertex_type is None or vertex.vertex_type == vertex_type)
            and (factory_label is None or vertex.factory_label == factory_label)
            and (module_id is None or vertex.module_id == module_id)
        ]

    def require_vertex(
        self,
        *,
        kind: str | None = None,
        vertex_type: str | None = None,
        factory_label: str | None = None,
        module_id: str | None = None,
    ) -> VertexRecord:
        """Exactly one matching in-scope vertex; raises :class:`ProcessorInputError` otherwise."""
        matches = self.find_vertices(
            kind=kind, vertex_type=vertex_type, factory_label=factory_label, module_id=module_id
        )
        if len(matches) != 1:
            criteria = ", ".join(
                f"{name}={value!r}"
                for name, value in (
                    ("kind", kind),
                    ("vertex_type", vertex_type),
                    ("factory_label", factory_label),
                    ("module_id", module_id),
                )
                if value is not None
            )
            found = "no vertex" if not matches else f"{len(matches)} vertices ({', '.join(v.id for v in matches)})"
            raise ProcessorInputError(
                f"Expected exactly one vertex with {criteria} in {self.scope_label}; found {found}."
            )
        return matches[0]

    @property
    def scope_label(self) -> str:
        return (
            f"module '{self.module_id}' of device '{self.device_id}'"
            if self.module_id
            else f"device '{self.device_id}'"
        )


class VertexProcessor(ABC, Generic[ParamsT]):
    """Base class for processors. Declare ``params_model`` and implement :meth:`process`.

    A new instance is created for every processing run, so instances may keep run-local state.
    """

    params_model: ClassVar[type[BaseModel]]

    @abstractmethod
    def process(self, context: ProcessingContext, params: ParamsT) -> ProcessorResult:
        """Interpret the scoped topology and propose configuration. Raise
        :class:`TopologyNotReadyError` when discovery is still incomplete (retried while topology work is
        deferred) and :class:`ProcessorInputError` when the layout is unsupported (fails immediately)."""


class ProcessorRegistry:
    """Per-engine processor registrations (never process-global). Built-ins are included by default;
    duplicate ids fail — a built-in is never silently overridden."""

    def __init__(
        self,
        processors: Mapping[str, type[VertexProcessor[Any]]] | None = None,
        *,
        include_builtins: bool = True,
    ) -> None:
        self._processors: dict[str, type[VertexProcessor[Any]]] = {}
        if include_builtins:
            for processor_id, processor_cls in _builtin_processors().items():
                self.register(processor_id, processor_cls)
        for processor_id, processor_cls in dict(processors or {}).items():
            self.register(processor_id, processor_cls)

    def register(self, processor_id: str, processor_cls: type[VertexProcessor[Any]]) -> None:
        if not isinstance(processor_id, str) or not _PROCESSOR_ID_RE.fullmatch(processor_id):
            raise ValueError(f"Invalid processor id {processor_id!r} (letters, digits, '.', '_', '-').")
        if not (isinstance(processor_cls, type) and issubclass(processor_cls, VertexProcessor)):
            raise TypeError(f"Processor '{processor_id}' must be a VertexProcessor subclass.")
        params_model = getattr(processor_cls, "params_model", None)
        if not (isinstance(params_model, type) and issubclass(params_model, BaseModel)):
            raise TypeError(f"Processor '{processor_id}' must declare 'params_model' as a pydantic model class.")
        if processor_id in self._processors:
            raise ValueError(f"Processor id '{processor_id}' is already registered; use a new id.")
        self._processors[processor_id] = processor_cls

    def get(self, processor_id: str) -> type[VertexProcessor[Any]]:
        processor_cls = self._processors.get(processor_id)
        if processor_cls is None:
            raise ProvisioningValidationError(
                ValidationIssue(
                    message=f"Unknown processor '{processor_id}'. Available: {', '.join(self.ids()) or 'none'}.",
                    code="processor.unknown",
                )
            )
        return processor_cls

    def ids(self) -> list[str]:
        return sorted(self._processors)

    def __contains__(self, processor_id: object) -> bool:
        return processor_id in self._processors

    def copy(self) -> ProcessorRegistry:
        clone = ProcessorRegistry(include_builtins=False)
        clone._processors = dict(self._processors)
        return clone

    def params_schema(self, processor_id: str) -> dict[str, Any]:
        return self.get(processor_id).params_model.model_json_schema()

    def validate_params(self, processor_id: str, params: Mapping[str, Any], path: tuple[Any, ...] = ()) -> BaseModel:
        """Validate ``params`` with the processor's model; issues carry ``path`` (document location)."""
        params_model = self.get(processor_id).params_model
        data = copy.deepcopy(dict(params))
        try:
            return params_model.model_validate(data)
        except ValidationError as exc:
            raise ProvisioningValidationError(issues_from_pydantic(exc, data=data, prefix=path)) from None

    def __repr__(self) -> str:
        return f"ProcessorRegistry({', '.join(self.ids())})"


# --- Internal ---

_PROCESSOR_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")


def _builtin_processors() -> dict[str, type[VertexProcessor[Any]]]:
    from videoipath_automation_tool.provisioning.processors.matrox import MatroxConvertIPProcessor

    return {"matrox.convertip.default": MatroxConvertIPProcessor}


__all__ = [
    "DeviceRecord",
    "DriverContext",
    "ModuleRecord",
    "PortRecord",
    "ProcessingContext",
    "ProcessorRegistry",
    "SourceFacts",
    "VertexProcessor",
    "VertexRecord",
]
