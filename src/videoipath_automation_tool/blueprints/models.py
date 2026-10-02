"""Public blueprint models: the YAML document, source-independent device facts, typed patches and
processor output, and the plan/result records.

Document models are strict (``extra="forbid"``, no implicit coercion) and immutable. Open mappings
exist only where intentional: driver ``custom_settings`` (validated against the selected driver at
resolution), processor ``params`` (validated by the registered processor), ``metadata``, and caller
``attributes``. Patch fields use *absence* to mean "unmanaged"; ``null`` is rejected there because it
would be ambiguous with absence.
"""

from __future__ import annotations

from os import PathLike
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    PrivateAttr,
    SecretStr,
    StringConstraints,
    ValidationError,
    model_validator,
)

from videoipath_automation_tool.apps.inspect.model.common import (
    InspectIconSize,
    InspectIconType,
    InspectSdpStrategy,
    InspectSipsMode,
)
from videoipath_automation_tool.blueprints.errors import BlueprintValidationError, ValidationIssue
from videoipath_automation_tool.blueprints.loader import parse_yaml, read_blueprint_file
from videoipath_automation_tool.blueprints.naming import (
    INVENTORY_NAMING_ENTRIES,
    TOPOLOGY_NAMING_ENTRIES,
    BlueprintNaming,
)
from videoipath_automation_tool.utils.cross_app_utils import normalize_address
from videoipath_automation_tool.validators.device_id import validate_device_id

if TYPE_CHECKING:
    from videoipath_automation_tool.apps.inventory.model.inventory_device import InventoryDevice
    from videoipath_automation_tool.blueprints.processors import ProcessorRegistry

NonEmptyStr = Annotated[str, StringConstraints(min_length=1)]
VariantName = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")]
MetadataValue = str | int | float | bool
Scope = Literal["all", "inventory", "topology"]
SyncPolicy = Literal["none", "add_only", "reconcile"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class _PatchModel(_StrictModel):
    """Absent fields are unmanaged; explicit ``null`` is rejected (ambiguous with absence)."""

    @model_validator(mode="before")
    @classmethod
    def _reject_nulls(cls, data: Any) -> Any:
        if isinstance(data, dict):
            nulls = sorted(str(key) for key, value in data.items() if value is None)
            if nulls:
                raise ValueError(f"null is not supported for {', '.join(nulls)}; omit the field to leave it unmanaged")
        return data

    def managed(self) -> dict[str, Any]:
        """The explicitly supplied fields and their values."""
        return {name: getattr(self, name) for name in type(self).model_fields if name in self.model_fields_set}


# --- Tags ---


class TagDelta(_StrictModel):
    """Additive tag change that preserves unrelated local tags. Tag references are exact catalog
    tag ids (for example ``Format~~V_1080p50``); the engine never creates catalog entries."""

    add: list[NonEmptyStr] = Field(default_factory=list)
    remove: list[NonEmptyStr] = Field(default_factory=list)

    @model_validator(mode="after")
    def _no_overlap(self) -> TagDelta:
        overlap = sorted(set(self.add) & set(self.remove))
        if overlap:
            raise ValueError(f"tags listed in both add and remove: {', '.join(overlap)}")
        if not self.add and not self.remove:
            raise ValueError("a tag delta needs at least one 'add' or 'remove' entry")
        return self


TagSpec = list[NonEmptyStr] | TagDelta
"""A list replaces the local tags exactly (``[]`` clears them); ``{add, remove}`` changes them additively."""


# --- Topology patches (YAML and processor output share these contracts) ---


class Coordinates(_StrictModel):
    x: float
    y: float


class DevicePatch(_PatchModel):
    """Inspect device fields (device targets only). Device label/description come from naming."""

    icon_type: InspectIconType | None = None
    icon_size: InspectIconSize | None = None
    sdp_strategy: InspectSdpStrategy | None = None
    site_id: NonEmptyStr | None = None
    coordinates: Coordinates | None = None
    tags: TagSpec | None = None


class ModulePatch(_PatchModel):
    """Module-local tag settings (module targets only)."""

    tags: TagSpec | None = None


class VertexPatch(_PatchModel):
    """Supported vertex edits. ``""`` is an explicit clear for label/description.

    Kind-specific fields: ``sdp_support`` and the destination ports apply to codec vertices,
    ``supports_static_igmp`` to IP vertices.
    """

    use_as_endpoint: bool | None = None
    label: str | None = None
    description: str | None = None
    active: bool | None = None
    sips_mode: InspectSipsMode | None = None
    tags: TagSpec | None = None
    sdp_support: bool | None = None
    main_destination_port: Annotated[int, Field(ge=0, le=65535)] | None = None
    spare_destination_port: Annotated[int, Field(ge=0, le=65535)] | None = None
    supports_static_igmp: bool | None = None


class VertexOverride(_StrictModel):
    """Explicit vertex edit. Select by exact ``vertex_id``, or by exact ``factory_label`` (supports
    ``{module.position}``) optionally restricted by ``kind`` / ``direction``; must match exactly one vertex."""

    vertex_id: NonEmptyStr | None = None
    factory_label: NonEmptyStr | None = None
    kind: NonEmptyStr | None = None
    direction: Literal["In", "Out", "Internal", "Undecided"] | None = None
    fields: VertexPatch

    @model_validator(mode="after")
    def _one_selector(self) -> VertexOverride:
        if (self.vertex_id is None) == (self.factory_label is None):
            raise ValueError("specify exactly one of 'vertex_id' or 'factory_label'")
        if self.vertex_id is not None and (self.kind is not None or self.direction is not None):
            raise ValueError("'kind' / 'direction' only refine a 'factory_label' selector")
        return self


class VertexProcessorSpec(_StrictModel):
    """Processor declaration. ``processor_type`` may be inherited from ``default`` by a variant;
    it is required on the resolved configuration."""

    processor_type: NonEmptyStr | None = None
    params: dict[str, Any] = Field(default_factory=dict)


# --- Inventory configuration ---


class CatalogId(_StrictModel):
    """Exact catalog id reference, e.g. ``{id: default}`` for the system SNMP configuration."""

    id: NonEmptyStr


class SnmpSelection(_PatchModel):
    """Global SNMP selection. ``configuration`` is an exact label (string) or ``{id: ...}``."""

    use_global_settings: bool | None = None
    configuration: NonEmptyStr | CatalogId | None = None


class GenericSettings(_PatchModel):
    """Generic connection settings (``cinfo.http``). ``http_auth`` is the server's raw
    ``httpAuth`` mode code (``0`` disables HTTP authentication)."""

    enable_https: bool | None = None
    trust_all_certificates: bool | None = None
    http_auth: Annotated[int, Field(ge=0)] | None = None


class InventorySettings(_StrictModel):
    """Inventory settings that may also be supplied per instance (``BlueprintDevice.inventory_overrides``)."""

    active: bool | None = None
    generic_settings: GenericSettings | None = None
    snmp: SnmpSelection | None = None
    custom_settings: dict[str, Any] | None = None
    metadata: dict[NonEmptyStr, MetadataValue] | None = None


class InventoryConfig(InventorySettings):
    """One Inventory entry (``default`` or a named variant patch)."""

    driver_id: NonEmptyStr | None = None
    naming: BlueprintNaming | None = None

    @model_validator(mode="after")
    def _inventory_naming_only(self) -> InventoryConfig:
        _check_naming_entries(self.naming, INVENTORY_NAMING_ENTRIES, "inventory")
        if self.custom_settings is not None and "driver_id" in self.custom_settings:
            raise ValueError("'driver_id' belongs at the inventory entry level, not inside custom_settings")
        return self


class TopologyConfig(_StrictModel):
    """One topology entry (``default`` or a named variant patch)."""

    device: DevicePatch | None = None
    module: ModulePatch | None = None
    ip_vertex_mapping: dict[NonEmptyStr, Annotated[list[NonEmptyStr], Field(min_length=1)]] | None = None
    vertex_processor: VertexProcessorSpec | None = None
    naming: BlueprintNaming | None = None
    vertices: list[VertexOverride] | None = None

    @model_validator(mode="after")
    def _topology_naming_only(self) -> TopologyConfig:
        _check_naming_entries(self.naming, TOPOLOGY_NAMING_ENTRIES, "topology")
        return self


class Blueprint(_StrictModel):
    """A reusable, type-level configuration with ``default`` entries and optional named variants.

    Load with :meth:`load` (file), :meth:`from_yaml` (text/bytes), or :meth:`from_dict` (mapping).
    Loading never connects to a server. A named variant is a patch over its section's ``default``.
    """

    schema_version: Literal[1]
    inventory: dict[VariantName, InventoryConfig] | None = None
    topology: dict[VariantName, TopologyConfig] | None = None

    _source: str | None = PrivateAttr(default=None)
    _locations: dict[tuple[Any, ...], tuple[int, int]] = PrivateAttr(default_factory=dict)

    @model_validator(mode="after")
    def _sections(self) -> Blueprint:
        if self.inventory is None and self.topology is None:
            raise ValueError("a blueprint needs an 'inventory' or a 'topology' section")
        for name, section in (("inventory", self.inventory), ("topology", self.topology)):
            if section is not None and "default" not in section:
                raise ValueError(f"the '{name}' section must contain a 'default' entry")
        return self

    # --- Construction ---

    @classmethod
    def load(cls, path: str | PathLike[str]) -> Blueprint:
        """Load one UTF-8 YAML blueprint file."""
        path = Path(path)
        return cls.from_yaml(read_blueprint_file(path), source=str(path))

    @classmethod
    def from_yaml(cls, text: str | bytes, *, source: str | None = None) -> Blueprint:
        """Parse YAML text with strict, safe loading."""
        data, locations = parse_yaml(text, source=source)
        return cls._from_data(data, source=source, locations=locations)

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, source: str | None = None) -> Blueprint:
        """Build from a mapping (e.g. produced by caller preprocessing). The mapping is not retained."""
        if not isinstance(data, dict):
            raise BlueprintValidationError(ValidationIssue(message="a blueprint must be a mapping", source=source))
        return cls._from_data(data, source=source, locations={})

    # --- Validation and schema ---

    def validate_full(self, registry: ProcessorRegistry | None = None) -> None:
        """Resolve and validate *every* variant (including unused ones) against the selected driver
        models, naming rules, and — when ``registry`` is given — processor parameter schemas.
        Processors absent from ``registry`` are reported as ``processor.unavailable`` issues.

        Raises:
            BlueprintValidationError: listing all issues found.
        """
        from videoipath_automation_tool.blueprints.resolution import validate_all_variants

        validate_all_variants(self, registry)

    @classmethod
    def json_schema(
        cls, registry: ProcessorRegistry | None = None, *, restrict_processor_types: bool = False
    ) -> dict[str, Any]:
        """JSON Schema of the document; with ``registry``, adds parameter schemas per processor id.
        ``restrict_processor_types`` additionally limits ``processor_type`` to the registered ids."""
        from videoipath_automation_tool.blueprints.resolution import blueprint_json_schema

        return blueprint_json_schema(registry, restrict_processor_types=restrict_processor_types)

    def variant_names(self, section: Literal["inventory", "topology"]) -> list[str]:
        entries = getattr(self, section)
        return list(entries) if entries else []

    def location_of(self, path: tuple[Any, ...]) -> tuple[str | None, int | None, int | None]:
        """``(source, line, column)`` of a document path when loaded from YAML."""
        line_col = self._locations.get(tuple(path))
        return self._source, (line_col[0] if line_col else None), (line_col[1] if line_col else None)

    # --- Internal ---

    @classmethod
    def _from_data(
        cls,
        data: dict[str, Any],
        *,
        source: str | None,
        locations: dict[tuple[Any, ...], tuple[int, int]],
    ) -> Blueprint:
        try:
            blueprint = cls.model_validate(data)
        except ValidationError as exc:
            raise BlueprintValidationError(
                issues_from_pydantic(exc, data=data, source=source, locations=locations)
            ) from None
        blueprint._source = source
        blueprint._locations = dict(locations)
        return blueprint


# --- Source-independent device facts ---


class Credentials(_StrictModel):
    """Runtime device credentials (never part of YAML; redacted from reprs and plans)."""

    username: str
    password: SecretStr


class AlternativeAddress(_StrictModel):
    address: NonEmptyStr
    credentials: Credentials | None = None


class DeviceTarget(_StrictModel):
    """Configure the topology of an exact Inspect device."""

    device_id: NonEmptyStr


class ModuleTarget(_StrictModel):
    """Configure only one exact module of an Inspect device (ids come from Inspect, never labels)."""

    device_id: NonEmptyStr
    module_id: NonEmptyStr


TopologyTarget = DeviceTarget | ModuleTarget


class BlueprintDevice(_StrictModel):
    """Instance facts and explicit VideoIPath bindings for one source entity.

    ``key`` is an opaque caller correlation key (never written to VideoIPath). ``inventory_id`` binds
    this entity's *own* Inventory record; without it, a selected inventory section creates one.
    ``topology`` binds an exact Inspect device or module; without it the Inventory id is used.
    ``alternative_addresses``: omitted = unmanaged, ``[]`` = clear. A supplied list is the full desired
    set and also replaces per-address credentials: a plain string carries none, so an existing
    credential for that address is cleared unless it is repeated as an ``AlternativeAddress``.
    ``attributes`` are caller-owned facts available to naming (scalar leaves) and processors.
    """

    key: NonEmptyStr
    label: NonEmptyStr
    description: str | None = None
    inventory_id: Annotated[str, AfterValidator(validate_device_id)] | None = None
    management_address: NonEmptyStr | None = None
    alternative_addresses: list[NonEmptyStr | AlternativeAddress] | None = None
    credentials: Credentials | None = None
    topology: TopologyTarget | None = None
    module_position: NonEmptyStr | None = None
    inventory_overrides: InventorySettings | None = None
    attributes: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _unique_addresses(self) -> BlueprintDevice:
        seen: dict[str, Any] = {}
        if self.management_address is not None:
            seen[normalize_address(self.management_address)] = None
        for entry in self.alternative_addresses or []:
            address = entry if isinstance(entry, str) else entry.address
            normalized = normalize_address(address)
            if normalized in seen:
                raise ValueError(f"address {address!r} is listed more than once")
            seen[normalized] = entry
        return self

    @classmethod
    def from_inventory(cls, device: InventoryDevice, *, key: str | None = None) -> BlueprintDevice:
        """Convenience binding for an existing Inventory device (id, label, description only)."""
        configuration = device.configuration
        return cls(
            key=key or configuration.id,
            label=configuration.config.desc.label or configuration.id,
            description=configuration.config.desc.desc or None,
            inventory_id=configuration.id,
        )


# --- Processor output contract ---


class EndpointIdentity(_StrictModel):
    """Semantic endpoint facts for naming (never a company-specific label)."""

    direction: NonEmptyStr
    media: NonEmptyStr
    index: Annotated[int, Field(ge=0)]
    engine: Annotated[int, Field(ge=0)] | None = None
    program: Annotated[int, Field(ge=0)] | None = None
    leg: NonEmptyStr | None = None


class VertexEdit(_StrictModel):
    """Proposed edits for one exact vertex id within the processing scope."""

    vertex_id: NonEmptyStr
    fields: VertexPatch = Field(default_factory=VertexPatch)
    endpoint: EndpointIdentity | None = None


class Diagnostic(_StrictModel):
    level: Literal["info", "warning"] = "info"
    code: NonEmptyStr
    message: str
    entity_id: str | None = None


class ProcessorResult(_StrictModel):
    vertices: list[VertexEdit] = Field(default_factory=list)
    device: DevicePatch | None = None
    module: ModulePatch | None = None
    diagnostics: list[Diagnostic] = Field(default_factory=list)


# --- Options ---


class ApplyOptions(_StrictModel):
    """Execution options.

    ``sync``: ``"none"`` requires existing topology; ``"add_only"`` (default) adds/syncs only new
    elements; ``"reconcile"`` permits a full sync. Service conflicts are always handled strictly.
    ``discovery_timeout`` / ``poll_interval`` bound the wait for driver discovery (seconds).
    ``naming_collisions="allow"`` permits duplicate endpoint labels within a device.
    ``write_credentials=True`` writes the supplied credentials to an existing Inventory record even when
    nothing else changes (secrets are masked on read, so a plan cannot tell whether they differ).
    """

    sync: SyncPolicy = "add_only"
    discovery_timeout: Annotated[float, Field(gt=0)] = 30.0
    poll_interval: Annotated[float, Field(gt=0)] = 1.0
    naming_collisions: Literal["reject", "allow"] = "reject"
    write_credentials: bool = False


# --- Plan and result records ---

PhaseName = Literal["inventory", "discovery", "topology_sync", "topology", "module_tags", "verification"]


class FieldChange(BaseModel):
    """One managed field: ``before`` / ``after`` are redacted when ``sensitive``."""

    model_config = ConfigDict(frozen=True)

    field: str
    before: Any = None
    after: Any = None
    source: str = ""
    sensitive: bool = False


class PlannedOperation(BaseModel):
    model_config = ConfigDict(frozen=True)

    action: Literal["create", "update", "assign_tag", "unassign_tag", "add_to_topology", "sync"]
    entity_kind: Literal["inventory", "device", "vertex", "module"]
    entity_id: str | None = None
    changes: list[FieldChange] = Field(default_factory=list)
    endpoint: EndpointIdentity | None = None


class PlannedPhase(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: PhaseName
    status: Literal["planned", "no_change", "deferred", "skipped"]
    reason: str | None = None
    operations: list[PlannedOperation] = Field(default_factory=list)


class InterfaceBinding(BaseModel):
    """A caller interface key resolved to an exact port and its directional vertices."""

    model_config = ConfigDict(frozen=True)

    key: str
    candidate: str
    port_id: str
    in_vertex_id: str | None = None
    out_vertex_id: str | None = None


class PhaseResult(BaseModel):
    name: PhaseName
    status: Literal["completed", "no_change", "skipped", "failed", "unknown", "not_run", "planned", "deferred"]
    """``planned`` / ``deferred`` occur only in dry runs (writes that would run / work that needs earlier writes)."""
    message: str | None = None
    operations: list[PlannedOperation] = Field(default_factory=list)


class ApplyResult(BaseModel):
    """What actually happened. Known ids are always reported, including after a failure.

    In a dry run (``dry_run=True``) nothing is written: ``status`` is ``planned`` when writes would
    run and ``no_change`` otherwise, and write phases report ``planned`` / ``deferred``.
    """

    status: Literal["succeeded", "no_change", "failed", "partial", "unknown", "planned"] = "no_change"
    dry_run: bool = False
    source_key: str
    inventory_id: str | None = None
    topology_device_id: str | None = None
    module_id: str | None = None
    phases: list[PhaseResult] = Field(default_factory=list)
    interface_bindings: list[InterfaceBinding] = Field(default_factory=list)
    materialized: bool = False
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    verification: Literal["confirmed", "unconfirmed", "not_applicable"] = "not_applicable"
    verification_detail: str | None = None

    @property
    def ok(self) -> bool:
        return self.status in ("succeeded", "no_change", "planned")

    def phase(self, name: PhaseName) -> PhaseResult | None:
        return next((phase for phase in self.phases if phase.name == name), None)


# --- Helpers ---


def issues_from_pydantic(
    exc: ValidationError,
    *,
    data: Any = None,
    prefix: tuple[Any, ...] = (),
    source: str | None = None,
    locations: dict[tuple[Any, ...], tuple[int, int]] | None = None,
) -> list[ValidationIssue]:
    """Convert a pydantic error to issues with document paths and YAML locations (no input values).

    ``data`` is the validated input; it is used to drop union-member tags pydantic inserts into
    error locations."""
    issues: list[ValidationIssue] = []
    for error in exc.errors(include_input=False, include_url=False):
        loc = prefix + _document_loc(tuple(error["loc"]), data)
        line_col = _nearest_location(loc, locations or {})
        issues.append(
            ValidationIssue(
                path=".".join(str(part) for part in loc),
                message=_friendly_message(error),
                code=f"schema.{error['type']}",
                source=source,
                line=line_col[0] if line_col else None,
                column=line_col[1] if line_col else None,
            )
        )
    return issues


def _check_naming_entries(naming: BlueprintNaming | None, allowed: frozenset[str], section: str) -> None:
    if naming is None:
        return
    invalid = sorted(name for name in naming.model_fields_set if name not in allowed)
    if invalid:
        raise ValueError(
            f"naming entries {', '.join(invalid)} are not valid in the '{section}' section "
            f"(allowed: {', '.join(sorted(allowed))})"
        )


def _document_loc(loc: tuple[Any, ...], data: Any) -> tuple[Any, ...]:
    """Walk ``data`` along ``loc``; parts that are not keys/indices (union-member tags) are dropped,
    except a trailing one (the name of a missing field)."""
    if data is None:
        return loc
    node = data
    kept: list[Any] = []
    for index, part in enumerate(loc):
        if (
            isinstance(node, dict)
            and part in node
            or isinstance(node, list)
            and isinstance(part, int)
            and 0 <= part < len(node)
        ):
            node = node[part]
        elif index < len(loc) - 1:
            continue
        kept.append(part)
    return tuple(kept)


def _nearest_location(
    loc: tuple[Any, ...], locations: dict[tuple[Any, ...], tuple[int, int]]
) -> tuple[int, int] | None:
    for end in range(len(loc), -1, -1):
        found = locations.get(loc[:end])
        if found is not None:
            return found
    return None


def _friendly_message(error: Any) -> str:
    kind = error["type"]
    if kind == "bool_type":
        return "Expected a boolean; received a different type."
    if kind == "int_type":
        return "Expected an integer; received a different type."
    if kind == "string_type":
        return "Expected a string; received a different type."
    if kind == "extra_forbidden":
        return "Unknown field."
    if kind == "missing":
        return "Field required."
    message = str(error["msg"])
    return message.removeprefix("Value error, ")


__all__ = [
    "AlternativeAddress",
    "ApplyOptions",
    "ApplyResult",
    "Blueprint",
    "BlueprintDevice",
    "CatalogId",
    "Coordinates",
    "Credentials",
    "DevicePatch",
    "DeviceTarget",
    "Diagnostic",
    "EndpointIdentity",
    "FieldChange",
    "GenericSettings",
    "InterfaceBinding",
    "InventoryConfig",
    "InventorySettings",
    "ModulePatch",
    "ModuleTarget",
    "PhaseResult",
    "PlannedOperation",
    "PlannedPhase",
    "ProcessorResult",
    "Scope",
    "SnmpSelection",
    "TagDelta",
    "TagSpec",
    "TopologyConfig",
    "TopologyTarget",
    "VertexEdit",
    "VertexOverride",
    "VertexPatch",
    "VertexProcessorSpec",
    "normalize_address",
]
