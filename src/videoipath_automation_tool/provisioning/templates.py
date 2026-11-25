"""Derive strict document templates from the same models used after input resolution.

Value positions accept references and literal escapes. Discriminator ids stay static. Keeping
this derivation centralized makes the editor schema and the loader follow the runtime fields.
"""

from __future__ import annotations

import copy
import types
from functools import reduce
from operator import or_
from typing import Annotated, Any, ForwardRef, Union, get_args, get_origin

from pydantic import BaseModel, ConfigDict, create_model, model_validator

from videoipath_automation_tool.provisioning.errors import ProvisioningValidationError, ValidationIssue
from videoipath_automation_tool.provisioning.inputs import (
    InputDefinition,
    InputReference,
    LiteralValue,
    contains_expression,
    is_expression,
)
from videoipath_automation_tool.provisioning.naming import reference_paths


def template_models(*models: type[BaseModel]) -> list[type[BaseModel]]:
    """Generate recursive template types, preserving constraints and literal-only validators."""
    cache: dict[type[BaseModel], type[BaseModel] | ForwardRef] = {}

    def annotation(value: Any) -> Any:
        origin, args = get_origin(value), get_args(value)
        if origin is Annotated:
            return Annotated[annotation(args[0]), *args[1:]]
        if origin in (Union, types.UnionType):
            return reduce(or_, (annotation(arg) for arg in args))
        if origin is list:
            return list[annotation(args[0]) | InputReference | LiteralValue]
        if origin is dict:
            return dict[args[0], annotation(args[1]) | InputReference | LiteralValue]
        if isinstance(value, type) and issubclass(value, BaseModel):
            return build(value)
        return value

    def build(model: type[BaseModel]) -> type[BaseModel] | ForwardRef:
        if model in cache:
            return cache[model]
        name = f"{model.__name__}Template"
        cache[model] = ForwardRef(name)
        fields: dict[str, Any] = {}
        for key, original in model.model_fields.items():
            info = copy.copy(original)
            value_type = annotation(original.annotation)
            if original.metadata:
                value_type = Annotated[value_type, *original.metadata]
                info.metadata = []
            if key not in {"driver_id", "processor_type"}:
                value_type = value_type | InputReference | LiteralValue
            fields[key] = (value_type, info)

        @model_validator(mode="before")
        def validate_literals(data: Any) -> Any:
            if not contains_expression(data):
                model.model_validate(data)
            return data

        generated = create_model(
            name,
            __config__=ConfigDict(extra="forbid", strict=True, frozen=True),
            __validators__={"validate_literals": validate_literals},
            **fields,
        )
        cache[model] = generated
        return generated

    result = [build(model) for model in models]
    namespace = {value.__name__: value for value in cache.values() if isinstance(value, type)}
    for generated in namespace.values():
        generated.model_rebuild(_types_namespace=namespace)
    return result


def validate_document_references(document: dict[str, Any], definitions: dict[str, InputDefinition]) -> None:
    """Check operators and declared naming paths, including in unused variants."""
    issues: list[ValidationIssue] = []

    def problem(path: tuple[str | int, ...], message: str) -> None:
        issues.append(ValidationIssue(path=".".join(map(str, path)), message=message, code="input.reference"))

    def naming_path(field: str, path: tuple[str | int, ...]) -> None:
        if not field.startswith("inputs."):
            return
        parts = field.split(".")[1:]
        definition = definitions.get(parts[0])
        if definition is None:
            problem(path, f"Unknown input reference '{parts[0]}'.")
            return
        for part in parts[1:]:
            properties = definition.properties or {}
            if definition.type != "object":
                problem(path, "Naming input path traverses a non-object input.")
                return
            if part not in properties:
                if not definition.additional_properties:
                    problem(path, f"Unknown property in naming input reference '{field}'.")
                return
            definition = properties[part]

    def naming_expression(value: Any, path: tuple[str | int, ...]) -> None:
        if isinstance(value, str):
            try:
                for field in reference_paths(value):
                    naming_path(field, path)
            except ValueError as exc:
                problem(path, str(exc))
        elif isinstance(value, dict):
            if isinstance(value.get("field"), str):
                naming_path(value["field"], path + ("field",))
            if isinstance(value.get("join"), list):
                for index, child in enumerate(value["join"]):
                    naming_expression(child, path + ("join", index))

    def walk(value: Any, path: tuple[str | int, ...]) -> None:
        if is_expression(value):
            if len(value) != 1:
                problem(path, "An input reference or literal escape must contain exactly one operator.")
            elif "$input" in value:
                name = value["$input"]
                if not isinstance(name, str) or name not in definitions:
                    problem(path, "Input reference must name a declared input.")
                if path[-1] in {"driver_id", "processor_type", "vertex_processor"}:
                    problem(path, "Driver and processor declarations must remain static.")
            return
        if len(path) >= 2 and path[-2] == "naming":
            naming_expression(value, path)
        if isinstance(value, dict):
            for key, child in value.items():
                walk(child, path + (key,))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, path + (index,))

    walk(document.get("defaults", {}), ("defaults",))
    walk(document.get("variants", {}), ("variants",))
    if issues:
        raise ProvisioningValidationError(issues)
