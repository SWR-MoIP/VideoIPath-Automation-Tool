"""Resolve ordered v2 overlays, typed inputs, driver settings and processor parameters."""

from __future__ import annotations

import copy
import hashlib
import importlib.resources
import json
from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, JsonValue, ValidationError

from videoipath_automation_tool.apps.inventory.model.drivers import (
    DRIVER_ID_TO_CUSTOM_SETTINGS,
    SELECTED_SCHEMA_VERSION,
)
from videoipath_automation_tool.provisioning.errors import ProvisioningValidationError, ValidationIssue
from videoipath_automation_tool.provisioning.inputs import bind_inputs, is_expression
from videoipath_automation_tool.provisioning.models import (
    Blueprint,
    InventoryConfig,
    InventorySettings,
    Scope,
    TopologyConfig,
    issues_from_pydantic,
)
from videoipath_automation_tool.provisioning.naming import NamingScheme, validate_naming_inputs
from videoipath_automation_tool.provisioning.processors import ProcessorRegistry, VertexProcessor

Provenance = dict[str, str]


class ResolvedInventory(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    driver_id: str
    schema_version: str = SELECTED_SCHEMA_VERSION
    config: InventoryConfig
    custom_settings: dict[str, Any]
    provenance: Provenance


class ResolvedTopology(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    config: TopologyConfig
    processor_id: str | None = None
    processor_cls: type[VertexProcessor] | None = None  # type: ignore[type-arg]
    params: BaseModel | None = None
    provenance: Provenance
    inputs: dict[str, JsonValue] = Field(default_factory=dict)


class ResolvedBlueprint(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    inventory: ResolvedInventory | None = None
    topology: ResolvedTopology | None = None
    variants: tuple[str, ...] = ()
    inputs: dict[str, JsonValue] = Field(default_factory=dict)
    naming: NamingScheme
    skipped: dict[str, str]
    digest: str


def resolve_blueprint(
    blueprint: Blueprint,
    *,
    scope: Scope = "all",
    variants: Sequence[str] = (),
    inputs: Mapping[str, JsonValue] | None = None,
    registry: ProcessorRegistry | None = None,
    overrides: InventorySettings | None = None,
    require_processor: bool = True,
) -> ResolvedBlueprint:
    """Merge and bind before any server access. Source documents are never mutated."""
    if scope not in ("all", "inventory", "topology"):
        raise ProvisioningValidationError("Invalid scope; expected 'all', 'inventory', or 'topology'.")
    selected = _selected_variants(blueprint, variants)
    values = bind_inputs(blueprint.inputs, inputs)
    document = blueprint.model_dump(mode="python", by_alias=True, exclude_unset=True)
    raw = copy.deepcopy(document["defaults"])
    origins = {section: _leaf_provenance(config, "defaults") for section, config in raw.items()}
    for variant in selected:
        for section, patch in document.get("variants", {}).get(variant, {}).items():
            provenance = origins.setdefault(section, {})
            base = raw.get(section, {})
            patch = copy.deepcopy(patch)
            source = f"variant:{variant}"
            if section == "inventory" and "driver_id" in patch and patch["driver_id"] != base.get("driver_id"):
                base.pop("custom_settings", None)
                _forget(provenance, "custom_settings")
            if section == "topology" and "vertex_processor" in patch:
                base["vertex_processor"] = _merge_processor(
                    base.get("vertex_processor"), patch.pop("vertex_processor"), provenance, source
                )
            raw[section] = _merge(base, patch, (), provenance, source)

    skipped: dict[str, str] = {}
    configs: dict[str, dict[str, Any]] = {}
    for section in ("inventory", "topology"):
        if scope not in ("all", section):
            skipped[section] = f"not in scope '{scope}'"
        elif section not in raw:
            if scope == section:
                raise ProvisioningValidationError(
                    _issue(
                        blueprint,
                        ("defaults", section),
                        f"scope='{section}' requested but the blueprint has no '{section}' section.",
                        "section.missing",
                    )
                )
            skipped[section] = "section absent from blueprint"
        else:
            configs[section] = _materialize(raw[section], values, blueprint, (section,), origins[section])

    if overrides is not None and "inventory" in configs:
        configs["inventory"] = _merge(
            configs["inventory"], overrides.model_dump(exclude_unset=True), (), origins["inventory"], "instance"
        )
    inventory = (
        _resolve_inventory(configs["inventory"], blueprint, origins["inventory"]) if "inventory" in configs else None
    )
    topology = (
        _resolve_topology(configs["topology"], blueprint, origins["topology"], registry, require_processor, values)
        if "topology" in configs
        else None
    )
    naming = NamingScheme.layered(
        inventory.config.naming.to_scheme() if inventory and inventory.config.naming else None,
        topology.config.naming.to_scheme() if topology and topology.config.naming else None,
    )
    for section, config in (("inventory", inventory), ("topology", topology)):
        if config is not None and config.config.naming is not None:
            try:
                validate_naming_inputs(config.config.naming.to_scheme(), blueprint.inputs, values)
            except ProvisioningValidationError as exc:
                raise ProvisioningValidationError(
                    [_relocate_relative(blueprint, (section,), issue, config.provenance) for issue in exc.issues]
                ) from None
    return ResolvedBlueprint(
        inventory=inventory,
        topology=topology,
        variants=selected,
        inputs=values,
        naming=naming,
        skipped=skipped,
        digest=blueprint_digest(blueprint),
    )


def validate_all_variants(
    blueprint: Blueprint,
    registry: ProcessorRegistry | None,
    *,
    inputs: Mapping[str, JsonValue] | None = None,
    variants: Sequence[str] | None = None,
) -> None:
    """Check the base and each overlay, or one explicitly selected combination, offline."""
    combinations = [variants] if variants is not None else [(), *((name,) for name in blueprint.variant_names())]
    issues: list[ValidationIssue] = []
    for combination in combinations:
        try:
            selected = _selected_variants(blueprint, combination)
        except ProvisioningValidationError as exc:
            issues.extend(exc.issues)
            continue
        sections = set(blueprint.defaults.model_fields_set)
        for name in selected:
            sections.update(blueprint.variants[name].model_fields_set)
        # Validate both sections independently so a broken Inventory setting does not hide
        # a Topology or processor error in the same configuration.
        for section in ("inventory", "topology"):
            if section not in sections:
                continue
            try:
                resolved = resolve_blueprint(
                    blueprint,
                    scope=section,
                    variants=selected,
                    inputs=inputs,
                    registry=registry,
                    require_processor=False,
                )
            except ProvisioningValidationError as exc:
                issues.extend(exc.issues)
                continue
            topology = resolved.topology
            if (
                registry is not None
                and topology is not None
                and topology.processor_id is not None
                and topology.processor_cls is None
            ):
                path = _source_path(
                    ("topology",),
                    ("vertex_processor", "processor_type"),
                    topology.provenance,
                    "vertex_processor.processor_type",
                )
                issues.append(
                    _issue(
                        blueprint,
                        path,
                        f"Processor '{topology.processor_id}' is not registered; its parameters were not validated.",
                        "processor.unavailable",
                    )
                )
    if issues:
        unique = {(issue.path, issue.code, issue.message): issue for issue in issues}
        raise ProvisioningValidationError(list(unique.values()))


def blueprint_digest(blueprint: Blueprint) -> str:
    document = blueprint.model_dump(mode="json", by_alias=True, exclude_unset=True)
    return hashlib.sha256(json.dumps(document, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def blueprint_json_schema(
    registry: ProcessorRegistry | None = None, *, restrict_processor_types: bool = False
) -> dict[str, Any]:
    """Draft 2020-12 document schema; typed value positions also accept input references."""
    if restrict_processor_types and registry is None:
        raise ValueError("restrict_processor_types requires a registry.")
    schema = Blueprint.model_json_schema(by_alias=True)
    schema.update(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://github.com/SWR-MoIP/VideoIPath-Automation-Tool/blueprint-v1.schema.json",
            "title": "VideoIPath Automation Tool blueprint (schema_version 1)",
        }
    )
    configuration = schema["$defs"]["BlueprintConfiguration"]
    # Section keys are structural and explicit null is rejected by the loader.
    for section in ("inventory", "topology"):
        configuration["properties"][section] = {"$ref": f"#/$defs/{section.title()}ConfigTemplate"}
    schema["properties"]["defaults"]["anyOf"] = [{"required": ["inventory"]}, {"required": ["topology"]}]
    if registry is None:
        return schema
    defs = schema["$defs"]
    branches: list[dict[str, Any]] = []
    for processor_id in registry.ids():
        params = registry.get(processor_id).params_model.model_json_schema(
            by_alias=True, ref_template="#/$defs/{model}"
        )
        extra_defs = params.pop("$defs", {})
        # Prefix custom parameter definitions to avoid overwriting document definitions.
        prefix = processor_id + "."

        def rewrite(value: Any, prefix: str = prefix) -> Any:
            if isinstance(value, list):
                return [rewrite(item) for item in value]
            if not isinstance(value, dict):
                return value
            result = {key: rewrite(item) for key, item in value.items()}
            if "$ref" in result and result["$ref"].startswith("#/$defs/"):
                result["$ref"] = "#/$defs/" + prefix + result["$ref"].removeprefix("#/$defs/")
            if "properties" in result:
                result["properties"] = {key: _value_schema(item) for key, item in result["properties"].items()}
            if "items" in result:
                result["items"] = _value_schema(result["items"])
            if isinstance(result.get("additionalProperties"), dict):
                result["additionalProperties"] = _value_schema(result["additionalProperties"])
            return result

        defs.update({prefix + name: rewrite(value) for name, value in extra_defs.items()})
        branches.append(
            {
                "if": {"properties": {"processor_type": {"const": processor_id}}, "required": ["processor_type"]},
                "then": {"properties": {"params": _value_schema(rewrite(params))}},
            }
        )
    spec = defs["VertexProcessorSpecTemplate"]
    if branches:
        spec["allOf"] = branches
    if restrict_processor_types:
        spec["properties"]["processor_type"] = {"type": "string", "enum": registry.ids()}
    return schema


def published_json_schema() -> dict[str, Any]:
    resource = importlib.resources.files("videoipath_automation_tool.provisioning").joinpath(
        "schemas/blueprint-v1.schema.json"
    )
    return json.loads(resource.read_text(encoding="utf-8"))


# --- Internal ---


def _resolve_inventory(data: dict[str, Any], blueprint: Blueprint, provenance: Provenance) -> ResolvedInventory:
    entry_path = ("inventory",)
    config = _validate_entry(InventoryConfig, data, blueprint, entry_path, provenance)
    if config.driver_id is None:
        raise ProvisioningValidationError(
            _issue(
                blueprint,
                _source_path(entry_path, ("driver_id",), provenance, "driver_id"),
                "Field required (inventory needs a driver_id).",
                "missing",
            )
        )
    model = DRIVER_ID_TO_CUSTOM_SETTINGS.get(config.driver_id)
    if model is None:
        raise ProvisioningValidationError(
            _issue(
                blueprint,
                _source_path(entry_path, ("driver_id",), provenance, "driver_id"),
                f"Unknown driver '{config.driver_id}' for the selected driver schema {SELECTED_SCHEMA_VERSION}.",
                "driver.unknown",
            )
        )
    custom = dict(config.custom_settings or {})
    return ResolvedInventory(
        driver_id=config.driver_id,
        config=config,
        custom_settings=_validate_custom_settings(model, custom, blueprint, entry_path, provenance, config.driver_id),
        provenance=provenance,
    )


def _resolve_topology(
    data: dict[str, Any],
    blueprint: Blueprint,
    provenance: Provenance,
    registry: ProcessorRegistry | None,
    require_processor: bool,
    inputs: dict[str, JsonValue],
) -> ResolvedTopology:
    entry_path = ("topology",)
    config = _validate_entry(TopologyConfig, data, blueprint, entry_path, provenance)
    spec = config.vertex_processor
    common = {"config": config, "provenance": provenance, "inputs": copy.deepcopy(inputs)}
    if spec is None:
        return ResolvedTopology(**common)
    type_path = _source_path(
        entry_path, ("vertex_processor", "processor_type"), provenance, "vertex_processor.processor_type"
    )
    if spec.processor_type is None:
        raise ProvisioningValidationError(_issue(blueprint, type_path, "Field required.", "missing"))
    if registry is None or (spec.processor_type not in registry and not require_processor):
        return ResolvedTopology(processor_id=spec.processor_type, **common)
    try:
        processor_cls = registry.get(spec.processor_type)
    except ProvisioningValidationError as exc:
        raise ProvisioningValidationError(
            _issue(blueprint, type_path, exc.issues[0].message, "processor.unknown")
        ) from None
    try:
        params = registry.validate_params(spec.processor_type, spec.params)
    except ProvisioningValidationError as exc:
        raise ProvisioningValidationError(
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
    return ResolvedTopology(processor_id=spec.processor_type, processor_cls=processor_cls, params=params, **common)


def _selected_variants(blueprint: Blueprint, variants: Sequence[str]) -> tuple[str, ...]:
    if (
        isinstance(variants, (str, bytes))
        or not isinstance(variants, Sequence)
        or any(not isinstance(name, str) for name in variants)
    ):
        raise TypeError("variants must be a sequence of names, not a string.")
    selected = tuple(variants)
    if len(set(selected)) != len(selected):
        raise ProvisioningValidationError(
            ValidationIssue(path="variants", message="A variant may only be selected once.", code="variant.duplicate")
        )
    unknown = [name for name in selected if name not in blueprint.variants]
    if unknown:
        raise ProvisioningValidationError(
            ValidationIssue(
                path="variants",
                message=f"Unknown variant '{unknown[0]}'. Available: {', '.join(blueprint.variant_names()) or 'none'}.",
                code="variant.unknown",
            )
        )
    return selected


def _materialize(
    value: Any,
    inputs: dict[str, JsonValue],
    blueprint: Blueprint,
    entry_path: tuple[str, ...],
    provenance: Provenance,
    path: tuple[str | int, ...] = (),
) -> Any:
    if is_expression(value):
        key = ".".join(map(str, path))
        origin = _origin(provenance, key)
        if "$literal" in value:
            result = copy.deepcopy(value["$literal"])
            _forget(provenance, key)
            provenance.update(_leaf_provenance(result, origin, path))
            return result
        name = value["$input"]
        if name not in inputs:
            raise ProvisioningValidationError(
                _issue(
                    blueprint,
                    _source_path(entry_path, path, provenance, key),
                    "Required input is missing.",
                    "input.missing",
                )
            )
        result = copy.deepcopy(inputs[name])
        _forget(provenance, key)
        provenance.update(_leaf_provenance(result, f"{origin}|input:{name}", path))
        return result
    if isinstance(value, dict):
        return {
            key: _materialize(child, inputs, blueprint, entry_path, provenance, path + (key,))
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [
            _materialize(child, inputs, blueprint, entry_path, provenance, path + (index,))
            for index, child in enumerate(value)
        ]
    return value


def _merge(
    base: dict[str, Any], patch: dict[str, Any], path: tuple[str, ...], provenance: Provenance, source: str
) -> dict[str, Any]:
    merged = dict(base)
    for key, value in patch.items():
        child, current = path + (key,), merged.get(key)
        if (
            isinstance(value, dict)
            and isinstance(current, dict)
            and not _atomic(child)
            and not is_expression(value)
            and not is_expression(current)
        ):
            merged[key] = _merge(current, value, child, provenance, source)
        else:
            merged[key] = copy.deepcopy(value)
            _forget(provenance, ".".join(child))
            provenance.update(_leaf_provenance(value, source, child))
    return merged


def _merge_processor(base: Any, patch: Any, provenance: Provenance, source: str) -> Any:
    if (
        patch is not None
        and isinstance(base, dict)
        and isinstance(patch, dict)
        and patch.get("processor_type", base.get("processor_type")) == base.get("processor_type")
    ):
        return _merge(base, patch, ("vertex_processor",), provenance, source)
    _forget(provenance, "vertex_processor")
    provenance.update(_leaf_provenance(patch, source, ("vertex_processor",)))
    return copy.deepcopy(patch)


def _atomic(path: tuple[str | int, ...]) -> bool:
    return bool(path) and (
        (len(path) == 2 and path[0] == "naming")
        or path[-1] == "tags"
        or isinstance(path[-1], str)
        and path[-1].endswith("_tags")
    )


def _leaf_provenance(value: Any, source: str, path: tuple[str | int, ...] = ()) -> Provenance:
    if isinstance(value, dict) and value and not is_expression(value) and not _atomic(path):
        return {
            key: origin
            for name, child in value.items()
            for key, origin in _leaf_provenance(child, source, path + (name,)).items()
        }
    return {".".join(map(str, path)): source} if path else {}


def _forget(provenance: Provenance, prefix: str) -> None:
    for stale in [key for key in provenance if key == prefix or key.startswith(prefix + ".")]:
        del provenance[stale]


def _origin(provenance: Provenance, key: str) -> str:
    return provenance.get(key) or next(
        (source for path, source in provenance.items() if path.startswith(key + ".") or key.startswith(path + ".")),
        "defaults",
    )


def _source_path(
    entry_path: tuple[str, ...], relative: tuple[Any, ...], provenance: Provenance, key: str
) -> tuple[Any, ...]:
    source = _origin(provenance, key).split("|input:", 1)[0]
    section = entry_path[0]
    if source == "instance":
        return ("device", "inventory_overrides") + relative
    if source.startswith("variant:"):
        return ("variants", source.removeprefix("variant:"), section) + relative
    return ("defaults", section) + relative


def _value_schema(schema: dict[str, Any]) -> dict[str, Any]:
    return {"anyOf": [schema, {"$ref": "#/$defs/InputReference"}, {"$ref": "#/$defs/LiteralValue"}]}


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
        raise ProvisioningValidationError(
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
        raise ProvisioningValidationError(
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
        raise ProvisioningValidationError(
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
