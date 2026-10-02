"""Blueprint-driven Inventory and Inspect configuration.

A standalone feature: construct :class:`BlueprintEngine` with an app (``BlueprintEngine(app)``),
describe a device with :class:`BlueprintDevice`, then pass a YAML file path or :class:`Blueprint` to
``engine.plan(...)`` (read-only preview) and ``plan.apply()``, or ``engine.apply(...)`` in one call.
``VideoIPathApp`` neither imports nor exposes this package.

Importing this package and loading blueprints never connects to a server.
"""

from __future__ import annotations

from videoipath_automation_tool.blueprints.engine import BlueprintApp, BlueprintEngine, BlueprintPlan
from videoipath_automation_tool.blueprints.errors import (
    BlueprintApplyError,
    BlueprintCapabilityError,
    BlueprintConflictError,
    BlueprintError,
    BlueprintTargetError,
    BlueprintValidationError,
    ProcessorInputError,
    ValidationIssue,
)
from videoipath_automation_tool.blueprints.models import (
    AlternativeAddress,
    ApplyOptions,
    ApplyResult,
    Blueprint,
    BlueprintDevice,
    CatalogId,
    Coordinates,
    Credentials,
    DevicePatch,
    DeviceTarget,
    Diagnostic,
    EndpointIdentity,
    FieldChange,
    InterfaceBinding,
    InventorySettings,
    ModulePatch,
    ModuleTarget,
    PhaseResult,
    PlannedOperation,
    PlannedPhase,
    ProcessorResult,
    TagDelta,
    VertexEdit,
    VertexPatch,
)
from videoipath_automation_tool.blueprints.naming import (
    DEFAULT_NAMING,
    Field,
    Join,
    NameContext,
    NameRenderer,
    NamingScheme,
    Text,
)
from videoipath_automation_tool.blueprints.processors import (
    DeviceRecord,
    DriverContext,
    ModuleRecord,
    PortRecord,
    ProcessingContext,
    ProcessorRegistry,
    SourceFacts,
    VertexProcessor,
    VertexRecord,
)
from videoipath_automation_tool.blueprints.processors.matrox import MatroxConvertIPParams, MatroxConvertIPProcessor
from videoipath_automation_tool.blueprints.resolution import published_json_schema

__all__ = [
    "DEFAULT_NAMING",
    "AlternativeAddress",
    "ApplyOptions",
    "ApplyResult",
    "Blueprint",
    "BlueprintApp",
    "BlueprintApplyError",
    "BlueprintCapabilityError",
    "BlueprintConflictError",
    "BlueprintDevice",
    "BlueprintEngine",
    "BlueprintError",
    "BlueprintPlan",
    "BlueprintTargetError",
    "BlueprintValidationError",
    "CatalogId",
    "Coordinates",
    "Credentials",
    "DevicePatch",
    "DeviceRecord",
    "DeviceTarget",
    "Diagnostic",
    "DriverContext",
    "EndpointIdentity",
    "Field",
    "FieldChange",
    "InterfaceBinding",
    "InventorySettings",
    "Join",
    "MatroxConvertIPParams",
    "MatroxConvertIPProcessor",
    "ModulePatch",
    "ModuleRecord",
    "ModuleTarget",
    "NameContext",
    "NameRenderer",
    "NamingScheme",
    "PhaseResult",
    "PlannedOperation",
    "PlannedPhase",
    "PortRecord",
    "ProcessingContext",
    "ProcessorInputError",
    "ProcessorRegistry",
    "ProcessorResult",
    "SourceFacts",
    "TagDelta",
    "Text",
    "ValidationIssue",
    "VertexEdit",
    "VertexPatch",
    "VertexProcessor",
    "VertexRecord",
    "published_json_schema",
]
