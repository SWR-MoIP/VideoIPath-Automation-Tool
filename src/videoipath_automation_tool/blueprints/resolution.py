"""Variant resolution, driver/parameter validation, and JSON Schema export.

Resolution order per section: the ``default`` entry, then the selected named entry (a patch), then
per-instance Inventory overrides. Merge rules are small and fixed:

- mappings merge recursively by key; scalars replace; lists replace entirely; ``{}`` adds nothing;
- naming expressions and tag specifications are replaced as a whole;
- ``vertex_processor: null`` disables an inherited processor; a different ``processor_type``
  replaces the whole processor specification (parameters are not inherited);
- a different ``driver_id`` replaces the inherited ``custom_settings``.

The source document is never mutated. Every merged leaf records its provenance (``default``,
``variant:<name>``, ``instance``) so plans can explain where a managed value came from.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.resources
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from videoipath_automation_tool.apps.inventory.model.drivers import (
    DRIVER_ID_TO_CUSTOM_SETTINGS,
    SELECTED_SCHEMA_VERSION,
)
from videoipath_automation_tool.blueprints.errors import BlueprintValidationError, ValidationIssue
from videoipath_automation_tool.blueprints.models import (
    Blueprint,
    InventoryConfig,
    InventorySettings,
    Scope,
    TopologyConfig,
    issues_from_pydantic,
)
from videoipath_automation_tool.blueprints.naming import NamingScheme
from videoipath_automation_tool.blueprints.processors import ProcessorRegistry, VertexProcessor

Provenance = dict[str, str]


class ResolvedInventory(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    variant: str
    driver_id: str
    schema_version: str = SELECTED_SCHEMA_VERSION
    config: InventoryConfig
    custom_settings: dict[str, Any]
    """Explicitly configured custom settings (Python field names), validated against the driver model."""
    provenance: Provenance


class ResolvedTopology(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    variant: str
    config: TopologyConfig
    processor_id: str | None = None
    processor_cls: type[VertexProcessor] | None = None  # type: ignore[type-arg]
    params: BaseModel | None = None
    provenance: Provenance


class ResolvedBlueprint(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    inventory: ResolvedInventory | None = None
    topology: ResolvedTopology | None = None
    naming: NamingScheme
    skipped: dict[str, str]
    digest: str


def resolve_blueprint(
    blueprint: Blueprint,
    *,
    scope: Scope,
    inventory_variant: str,
    topology_variant: str,
    registry: ProcessorRegistry,
    overrides: InventorySettings | None = None,
) -> ResolvedBlueprint:
    """Resolve the selected sections and variants; raises :class:`BlueprintValidationError`."""
    if scope not in ("all", "inventory", "topology"):
        raise BlueprintValidationError(f"Invalid scope {scope!r}; expected 'all', 'inventory', or 'topology'.")
    selected = {
        "inventory": _select(blueprint, "inventory", inventory_variant, scope),
        "topology": _select(blueprint, "topology", topology_variant, scope),
    }
    skipped = {section: reason for section, reason in selected.items() if reason is not None}

    inventory = None
    if "inventory" not in skipped:
        inventory = resolve_inventory(blueprint, inventory_variant, overrides=overrides)
    topology = None
    if "topology" not in skipped:
        topology = resolve_topology(blueprint, topology_variant, registry=registry, require_processor=True)

    naming = NamingScheme.layered(
        inventory.config.naming.to_scheme() if inventory and inventory.config.naming else None,
        topology.config.naming.to_scheme() if topology and topology.config.naming else None,
    )
    return ResolvedBlueprint(
        inventory=inventory, topology=topology, naming=naming, skipped=skipped, digest=blueprint_digest(blueprint)
    )


def resolve_inventory(
    blueprint: Blueprint, variant: str, *, overrides: InventorySettings | None = None
) -> ResolvedInventory:
    raw = _raw_entries(blueprint, "inventory")
    base = copy.deepcopy(raw["default"])
    provenance = _leaf_provenance(base, "default")
    if variant != "default":
        patch = raw[variant]
        if "driver_id" in patch and patch["driver_id"] != base.get("driver_id"):
            base.pop("custom_settings", None)
            provenance = {path: src for path, src in provenance.items() if not path.startswith("custom_settings")}
        base = _merge(base, patch, (), provenance, f"variant:{variant}")
    if overrides is not None:
        base = _merge(base, overrides.model_dump(exclude_unset=True), (), provenance, "instance")

    entry_path = ("inventory", variant)
    config = _validate_entry(InventoryConfig, base, blueprint, entry_path, provenance)
    if config.driver_id is None:
        raise BlueprintValidationError(
            _issue(blueprint, entry_path + ("driver_id",), "Field required (inventory needs a driver_id).", "missing")
        )
    model = DRIVER_ID_TO_CUSTOM_SETTINGS.get(config.driver_id)
    if model is None:
        raise BlueprintValidationError(
            _issue(
                blueprint,
                _source_path(entry_path, ("driver_id",), provenance, "driver_id"),
                f"Unknown driver '{config.driver_id}' for the selected driver schema {SELECTED_SCHEMA_VERSION}.",
                "driver.unknown",
            )
        )
    custom = dict(config.custom_settings or {})
    return ResolvedInventory(
        variant=variant,
        driver_id=config.driver_id,
        config=config,
        custom_settings=_validate_custom_settings(model, custom, blueprint, entry_path, provenance, config.driver_id),
        provenance=provenance,
    )


def resolve_topology(
    blueprint: Blueprint,
    variant: str,
    *,
    registry: ProcessorRegistry | None,
    require_processor: bool,
) -> ResolvedTopology:
    raw = _raw_entries(blueprint, "topology")
    base = copy.deepcopy(raw["default"])
    provenance = _leaf_provenance(base, "default")
    if variant != "default":
        patch = copy.deepcopy(raw[variant])
        source = f"variant:{variant}"
        if "vertex_processor" in patch:
            base["vertex_processor"] = _merge_processor(
                base.get("vertex_processor"), patch.pop("vertex_processor"), provenance, source
            )
        base = _merge(base, patch, (), provenance, source)

    entry_path = ("topology", variant)
    config = _validate_entry(TopologyConfig, base, blueprint, entry_path, provenance)
    spec = config.vertex_processor
    if spec is None:
        return ResolvedTopology(variant=variant, config=config, provenance=provenance)
    if spec.processor_type is None:
        raise BlueprintValidationError(
            _issue(blueprint, entry_path + ("vertex_processor", "processor_type"), "Field required.", "missing")
        )
    if registry is None or (spec.processor_type not in registry and not require_processor):
        return ResolvedTopology(variant=variant, config=config, processor_id=spec.processor_type, provenance=provenance)

    type_path = _source_path(
        entry_path, ("vertex_processor", "processor_type"), provenance, "vertex_processor.processor_type"
    )
    try:
        processor_cls = registry.get(spec.processor_type)
    except BlueprintValidationError as exc:
        raise BlueprintValidationError(
            _issue(blueprint, type_path, exc.issues[0].message, "processor.unknown")
        ) from None
    try:
        params = registry.validate_params(spec.processor_type, spec.params)
    except BlueprintValidationError as exc:
        raise BlueprintValidationError(
            [
                _relocate_relative(
                    blueprint,
                    entry_path,
                    issue.model_copy(update={"path": f"vertex_processor.params.{issue.path}".rstrip(".")}),
                    provenance,
                )
                for issue in exc.issues
            ]
        ) from None
    return ResolvedTopology(
        variant=variant,
        config=config,
        processor_id=spec.processor_type,
        processor_cls=processor_cls,
        params=params,
        provenance=provenance,
    )


def validate_all_variants(blueprint: Blueprint, registry: ProcessorRegistry | None) -> None:
    """Resolve every variant of every section; collect and raise all issues."""
    issues: list[ValidationIssue] = []
    for variant in blueprint.variant_names("inventory"):
        try:
            resolve_inventory(blueprint, variant)
        except BlueprintValidationError as exc:
            issues.extend(exc.issues)
    for variant in blueprint.variant_names("topology"):
        try:
            resolved = resolve_topology(blueprint, variant, registry=registry, require_processor=False)
        except BlueprintValidationError as exc:
            issues.extend(exc.issues)
            continue
        if registry is not None and resolved.processor_id is not None and resolved.processor_cls is None:
            issues.append(
                _issue(
                    blueprint,
                    ("topology", variant, "vertex_processor", "processor_type"),
                    f"Processor '{resolved.processor_id}' is not registered; its parameters were not validated.",
                    "processor.unavailable",
                )
            )
    if issues:
        raise BlueprintValidationError(issues)


def blueprint_digest(blueprint: Blueprint) -> str:
    """Stable digest of the normalized document."""
    document = blueprint.model_dump(mode="json", by_alias=True, exclude_unset=True)
    return hashlib.sha256(json.dumps(document, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def blueprint_json_schema(
    registry: ProcessorRegistry | None = None, *, restrict_processor_types: bool = False
) -> dict[str, Any]:
    """JSON Schema (draft 2020-12) generated from the runtime models. With ``registry``, the
    ``params`` of each registered ``processor_type`` are described through ``if``/``then`` branches.

    ``restrict_processor_types`` (requires ``registry``) limits ``processor_type`` to the registered
    ids, so editors flag unknown or misspelled processors. A variant may still omit it to inherit
    the ``default`` processor. Without it, unknown ids are accepted and their ``params`` are
    unconstrained (the packaged schema stays usable with processors registered elsewhere).
    """
    if restrict_processor_types and registry is None:
        raise ValueError("restrict_processor_types requires a registry.")
    schema = Blueprint.model_json_schema(by_alias=True)
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://github.com/SWR-MoIP/VideoIPath-Automation-Tool/blueprint-v1.schema.json",
        **schema,
        "title": "VideoIPath Automation Tool blueprint (schema_version 1)",
    }
    if registry is None:
        return schema
    defs = schema.setdefault("$defs", {})
    branches: list[dict[str, Any]] = []
    for processor_id in registry.ids():
        params_schema = registry.get(processor_id).params_model.model_json_schema(
            by_alias=True, ref_template="#/$defs/{model}"
        )
        defs.update(params_schema.pop("$defs", {}))
        branches.append(
            {
                "if": {"properties": {"processor_type": {"const": processor_id}}, "required": ["processor_type"]},
                "then": {"properties": {"params": params_schema}},
            }
        )
    spec = defs["VertexProcessorSpec"]
    if branches:
        spec["allOf"] = branches
    if restrict_processor_types:
        processor_type = spec["properties"]["processor_type"]
        processor_type.pop("anyOf", None)
        processor_type.update({"type": "string", "enum": registry.ids()})
    return schema


def published_json_schema() -> dict[str, Any]:
    """The packaged ``schemas/blueprint-v1.schema.json`` (document plus built-in processor parameters)."""
    resource = importlib.resources.files("videoipath_automation_tool.blueprints").joinpath(
        "schemas/blueprint-v1.schema.json"
    )
    return json.loads(resource.read_text(encoding="utf-8"))


# --- Internal ---

_ATOMIC_KEYS = frozenset({"tags"})


def _select(blueprint: Blueprint, section: Literal["inventory", "topology"], variant: str, scope: Scope) -> str | None:
    """``None`` when the section is selected, else the skip reason. Raises for invalid requests."""
    names = blueprint.variant_names(section)
    if not names:
        if scope == section:
            raise BlueprintValidationError(
                ValidationIssue(
                    path=section,
                    message=f"scope='{section}' requested but the blueprint has no '{section}' section.",
                    code="section.missing",
                )
            )
        if variant != "default":
            raise BlueprintValidationError(
                ValidationIssue(
                    path=section,
                    message=f"variant '{variant}' requested for the absent '{section}' section.",
                    code="section.missing",
                )
            )
        return "section absent from blueprint"
    if variant not in names:
        raise BlueprintValidationError(
            ValidationIssue(
                path=section,
                message=f"Unknown {section} variant '{variant}'. Available: {', '.join(names)}.",
                code="variant.unknown",
            )
        )
    if scope not in ("all", section):
        return f"not in scope '{scope}'"
    return None


def _raw_entries(blueprint: Blueprint, section: str) -> dict[str, dict[str, Any]]:
    document = blueprint.model_dump(mode="python", by_alias=True, exclude_unset=True)
    return document.get(section) or {}


def _merge(
    base: dict[str, Any], patch: dict[str, Any], path: tuple[str, ...], provenance: Provenance, source: str
) -> dict[str, Any]:
    merged = dict(base)
    for key, value in patch.items():
        child = path + (key,)
        current = merged.get(key)
        if isinstance(value, dict) and isinstance(current, dict) and not _atomic(child):
            merged[key] = _merge(current, value, child, provenance, source)
            continue
        merged[key] = copy.deepcopy(value)
        prefix = ".".join(child)
        for stale in [p for p in provenance if p == prefix or p.startswith(prefix + ".")]:
            del provenance[stale]
        provenance.update(_leaf_provenance(value, source, child))
    return merged


def _merge_processor(base: Any, patch: Any, provenance: Provenance, source: str) -> Any:
    """``null`` disables; a different ``processor_type`` replaces the whole spec; else params merge."""
    replaces = (
        patch is None
        or not isinstance(base, dict)
        or not isinstance(patch, dict)
        or patch.get("processor_type", base.get("processor_type")) != base.get("processor_type")
    )
    if not replaces:
        return _merge(base, patch, ("vertex_processor",), provenance, source)
    for stale in [p for p in provenance if p == "vertex_processor" or p.startswith("vertex_processor.")]:
        del provenance[stale]
    provenance.update(_leaf_provenance(patch, source, ("vertex_processor",)))
    return copy.deepcopy(patch)


def _atomic(path: tuple[str, ...]) -> bool:
    """Naming expressions and tag specifications are replaced as a whole."""
    return (len(path) == 2 and path[0] == "naming") or path[-1] in _ATOMIC_KEYS or path[-1].endswith("_tags")


def _leaf_provenance(value: Any, source: str, path: tuple[str, ...] = ()) -> Provenance:
    if isinstance(value, dict) and value and not (path and _atomic(path)):
        result: Provenance = {}
        for key, child in value.items():
            result.update(_leaf_provenance(child, source, path + (str(key),)))
        return result
    return {".".join(path): source} if path else {}


def _source_path(
    entry_path: tuple[str, ...], relative: tuple[Any, ...], provenance: Provenance, key: str
) -> tuple[Any, ...]:
    """Document path of a merged field: point at the entry the value actually came from."""
    source = provenance.get(key) or next(
        (src for path, src in provenance.items() if path.startswith(key + ".") or key.startswith(path + ".")), None
    )
    section = entry_path[0]
    if source == "default":
        return (section, "default") + relative
    if source == "instance":
        return ("device", "inventory_overrides") + relative
    return entry_path + relative


def _validate_entry(
    model: type[BaseModel],
    data: dict[str, Any],
    blueprint: Blueprint,
    entry_path: tuple[str, ...],
    provenance: Provenance,
) -> Any:
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        issues = issues_from_pydantic(exc, data=data)
        raise BlueprintValidationError(
            [_relocate_relative(blueprint, entry_path, issue, provenance) for issue in issues]
        ) from None


def _validate_custom_settings(
    model: type[BaseModel],
    custom: dict[str, Any],
    blueprint: Blueprint,
    entry_path: tuple[str, ...],
    provenance: Provenance,
    driver_id: str,
) -> dict[str, Any]:
    allowed = set(model.model_fields) - {"driver_id"}
    unknown = sorted(set(custom) - allowed)
    if unknown:
        raise BlueprintValidationError(
            [
                _issue(
                    blueprint,
                    _source_path(entry_path, ("custom_settings", key), provenance, f"custom_settings.{key}"),
                    f"Unknown custom setting for driver '{driver_id}' (schema {SELECTED_SCHEMA_VERSION}). "
                    f"Allowed: {', '.join(sorted(allowed)) or 'none'}.",
                    "driver.unknown_setting",
                )
                for key in unknown
            ]
        )
    try:
        instance = model.model_validate(custom, strict=True, by_name=True, by_alias=False)
    except ValidationError as exc:
        issues = issues_from_pydantic(exc, data=custom)
        raise BlueprintValidationError(
            [
                _relocate(
                    blueprint,
                    _source_path(entry_path, ("custom_settings",), provenance, f"custom_settings.{issue.path}"),
                    issue.model_copy(
                        update={"message": f"{issue.message} (driver '{driver_id}', schema {SELECTED_SCHEMA_VERSION})"}
                    ),
                )
                for issue in issues
            ]
        ) from None
    return {key: getattr(instance, key) for key in custom}


def _relocate_relative(
    blueprint: Blueprint, entry_path: tuple[str, ...], issue: ValidationIssue, provenance: Provenance
) -> ValidationIssue:
    relative = tuple(issue.path.split(".")) if issue.path else ()
    path = _source_path(entry_path, relative, provenance, issue.path)
    return _issue(blueprint, path, issue.message, issue.code)


def _relocate(blueprint: Blueprint, prefix: tuple[Any, ...], issue: ValidationIssue) -> ValidationIssue:
    relative = tuple(issue.path.split(".")) if issue.path else ()
    return _issue(blueprint, prefix + relative, issue.message, issue.code)


def _issue(blueprint: Blueprint, path: tuple[Any, ...], message: str, code: str) -> ValidationIssue:
    keys = tuple(int(part) if isinstance(part, str) and part.isdigit() else part for part in path)
    source, line, column = None, None, None
    for end in range(len(keys), -1, -1):
        source, line, column = blueprint.location_of(keys[:end])
        if line is not None:
            break
    return ValidationIssue(
        path=".".join(str(part) for part in path),
        message=message,
        code=code,
        source=source,
        line=line,
        column=column,
    )


__all__ = [
    "ResolvedBlueprint",
    "ResolvedInventory",
    "ResolvedTopology",
    "blueprint_digest",
    "blueprint_json_schema",
    "published_json_schema",
    "resolve_blueprint",
    "resolve_inventory",
    "resolve_topology",
    "validate_all_variants",
]
