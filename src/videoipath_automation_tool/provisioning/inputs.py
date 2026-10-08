"""Strict, source-independent input declarations and typed value references."""

from __future__ import annotations

import copy
import math
from collections.abc import Mapping
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, StringConstraints, model_validator

from videoipath_automation_tool.provisioning.errors import ProvisioningValidationError, ValidationIssue

InputName = Annotated[str, StringConstraints(pattern=r"^[A-Za-z_][A-Za-z0-9_-]*$")]


class InputReference(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, validate_by_name=True, validate_by_alias=True)

    name: InputName = Field(alias="$input")


class LiteralValue(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, validate_by_name=True, validate_by_alias=True)

    value: JsonValue = Field(alias="$literal")


class InputDefinition(BaseModel):
    """A small JSON Schema vocabulary; defaults are values, never expressions."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, validate_by_name=True, validate_by_alias=True)

    type: Literal["string", "integer", "number", "boolean", "array", "object", "null"]
    description: str | None = None
    default: JsonValue = None
    enum: Annotated[list[JsonValue], Field(min_length=1)] | None = None
    items: InputDefinition | None = None
    properties: dict[str, InputDefinition] | None = None
    required: list[str] | None = None
    additional_properties: bool = Field(default=False, alias="additionalProperties")

    @model_validator(mode="after")
    def _definition(self) -> InputDefinition:
        supplied = self.model_fields_set
        if "items" in supplied and self.type != "array":
            raise ValueError("items is only valid for array inputs")
        if supplied & {"properties", "required", "additional_properties"} and self.type != "object":
            raise ValueError("properties, required and additionalProperties are only valid for object inputs")
        if self.required is not None:
            if len(set(self.required)) != len(self.required):
                raise ValueError("required contains duplicate property names")
            if set(self.required) - set(self.properties or {}):
                raise ValueError("required must name declared properties")
        for value in self.enum or []:
            if value_issues(self, value, (), check_enum=False):
                raise ValueError("enum entries must conform to the declared input type and structure")
        if "default" in supplied:
            issues = value_issues(self, self.default, ())
            if issues:
                raise ValueError("invalid input default: " + "; ".join(issue.message for issue in issues))
        return self


def bind_inputs(
    definitions: Mapping[str, InputDefinition], supplied: Mapping[str, JsonValue] | None
) -> dict[str, JsonValue]:
    """Validate supplied values and copy defaults. Requiredness is checked at each use site."""
    if supplied is not None and not isinstance(supplied, Mapping):
        raise TypeError("inputs must be a mapping or None.")
    values = {
        name: copy.deepcopy(spec.default) for name, spec in definitions.items() if "default" in spec.model_fields_set
    }
    issues: list[ValidationIssue] = []
    for name, value in (supplied or {}).items():
        if name not in definitions:
            issues.append(ValidationIssue(path=f"inputs.{name}", message="Unknown input.", code="input.unknown"))
        else:
            issues.extend(value_issues(definitions[name], value, ("inputs", name)))
            values[name] = copy.deepcopy(value)
    if issues:
        raise ProvisioningValidationError(issues)
    return values


def value_issues(
    definition: InputDefinition, value: Any, path: tuple[str | int, ...], *, check_enum: bool = True
) -> list[ValidationIssue]:
    """Validate without coercion or including raw values in diagnostics."""
    kind = definition.type
    matches = {
        "string": isinstance(value, str),
        "integer": type(value) is int,
        "number": type(value) in (int, float) and (not isinstance(value, float) or math.isfinite(value)),
        "boolean": type(value) is bool,
        "array": isinstance(value, list),
        "object": isinstance(value, dict) and all(isinstance(key, str) for key in value),
        "null": value is None,
    }
    if not matches[kind]:
        return [_issue(path, f"Expected input type '{kind}'; received a different type.", "input.type")]
    issues: list[ValidationIssue] = []
    if check_enum and definition.enum is not None and not any(_equal(value, entry) for entry in definition.enum):
        issues.append(_issue(path, "Input value is not in the declared enum.", "input.enum"))
    if kind == "array":
        for index, item in enumerate(value):
            if definition.items is not None:
                issues.extend(value_issues(definition.items, item, path + (index,)))
            elif not _is_json(item):
                issues.append(_issue(path + (index,), "Expected a JSON value.", "input.type"))
    if kind == "object":
        properties = definition.properties or {}
        for name in definition.required or []:
            if name not in value:
                issues.append(_issue(path + (name,), "Required input property is missing.", "input.missing"))
        for name, item in value.items():
            if name in properties:
                issues.extend(value_issues(properties[name], item, path + (name,)))
            elif not definition.additional_properties:
                issues.append(_issue(path + (name,), "Unknown input property.", "input.unknown_property"))
            elif not _is_json(item):
                issues.append(_issue(path + (name,), "Expected a JSON value.", "input.type"))
    return issues


def is_expression(value: Any) -> bool:
    return isinstance(value, dict) and bool(value.keys() & {"$input", "$literal"})


def contains_expression(value: Any) -> bool:
    if isinstance(value, (InputReference, LiteralValue)):
        return True
    if isinstance(value, dict):
        return is_expression(value) or any(contains_expression(child) for child in value.values())
    if isinstance(value, list):
        return any(contains_expression(child) for child in value)
    return False


def _issue(path: tuple[str | int, ...], message: str, code: str) -> ValidationIssue:
    return ValidationIssue(path=".".join(map(str, path)), message=message, code=code)


def _equal(left: JsonValue, right: JsonValue) -> bool:
    if type(left) is bool or type(right) is bool:
        return type(left) is type(right) and left == right
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(_equal(a, b) for a, b in zip(left, right, strict=True))
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(_equal(left[key], right[key]) for key in left)
    return left == right


def _is_json(value: Any) -> bool:
    if value is None or type(value) in (str, bool, int):
        return True
    if type(value) is float:
        return math.isfinite(value)
    if isinstance(value, list):
        return all(_is_json(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _is_json(item) for key, item in value.items())
    return False
