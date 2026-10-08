"""Composable naming for Inventory, topology device, and endpoint labels.

A naming *entry* (``inventory_label``, ``endpoint_label``, …) holds one expression built from three
blocks — :class:`Text`, :class:`Field`, and :class:`Join` — or a template string such as
``"{device.label}-{endpoint.index:02d}"``, which compiles to the same blocks. Names are derived only
from explicit facts (device facts, module position, semantic endpoint identity, caller attributes),
never from a current label, so applying twice cannot append a second suffix.

Formatting supports a deliberately small subset: alignment, zero padding, minimum width, and the
``d`` / ``s`` types. There are no conversions, attribute traversal, indexing, or expressions. For a
computation the blocks cannot express, pass a trusted Python :class:`NameRenderer` for that entry.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, InstanceOf, JsonValue, model_validator
from pydantic import Field as PydanticField

from videoipath_automation_tool.provisioning.errors import ProvisioningValidationError, ValidationIssue

if TYPE_CHECKING:
    from videoipath_automation_tool.provisioning.inputs import InputDefinition

NAMING_ENTRIES: tuple[str, ...] = (
    "inventory_label",
    "inventory_description",
    "device_label",
    "device_description",
    "endpoint_label",
    "endpoint_description",
)

INVENTORY_NAMING_ENTRIES: frozenset[str] = frozenset({"inventory_label", "inventory_description"})
TOPOLOGY_NAMING_ENTRIES: frozenset[str] = frozenset(NAMING_ENTRIES) - INVENTORY_NAMING_ENTRIES


class Text(BaseModel):
    """A literal text block: ``Text("-")`` or YAML ``{text: "-"}``."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    text: str

    def __init__(self, text: str | None = None, /, **data: Any) -> None:
        if text is not None:
            data["text"] = text
        super().__init__(**data)


class Field(BaseModel):
    """One naming fact: ``Field("endpoint.index", format="02d")`` or YAML ``{field: endpoint.index, format: 02d}``.

    ``mapping`` translates the (stringified) value; ``prefix`` / ``suffix`` are only emitted when the
    value is present, so an absent optional field leaves no dangling separator text.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, validate_by_name=True, validate_by_alias=True)

    path: str = PydanticField(alias="field")
    format: str | None = None
    mapping: dict[str, str] | None = None
    prefix: str = ""
    suffix: str = ""

    def __init__(self, path: str | None = None, /, **data: Any) -> None:
        if path is not None:
            data["path"] = path
        super().__init__(**data)


class Join(BaseModel):
    """Join rendered parts with ``separator``. With ``skip_missing``, parts whose *optional* value is
    absent are omitted; unknown fields, type errors, and failed mappings are still errors."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, validate_by_name=True, validate_by_alias=True)

    parts: list[NameExpr] = PydanticField(alias="join")
    separator: str = ""
    skip_missing: bool = False

    def __init__(self, parts: list[Any] | None = None, /, **data: Any) -> None:
        if parts is not None:
            data["parts"] = parts
        super().__init__(**data)


NameExpr = str | Text | Field | Join
Join.model_rebuild()


class NameContext(BaseModel):
    """The facts available to naming. Namespaces: ``device`` (key, label, description), ``module``
    (position), ``endpoint`` (direction, media, index, engine, program, leg), ``vertex``
    (factory_label, id), ``attributes`` (caller-owned scalar facts), and ``inputs`` (bound values)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    device: dict[str, Any] = PydanticField(default_factory=dict)
    module: dict[str, Any] = PydanticField(default_factory=dict)
    endpoint: dict[str, Any] = PydanticField(default_factory=dict)
    vertex: dict[str, Any] = PydanticField(default_factory=dict)
    attributes: dict[str, JsonValue] = PydanticField(default_factory=dict)
    inputs: dict[str, JsonValue] = PydanticField(default_factory=dict)

    def value(self, path: str) -> Any:
        """The value at ``path`` (e.g. ``"device.label"``), or ``None`` when absent."""
        namespace, _, rest = path.partition(".")
        node: Any = getattr(self, namespace, None) if namespace in _NAMESPACES else None
        for part in rest.split(".") if rest else []:
            if not isinstance(node, dict):
                return None
            node = node.get(part)
        return node


@runtime_checkable
class NameRenderer(Protocol):
    """Trusted Python escape hatch for one naming entry; never loaded from YAML."""

    def render(self, context: NameContext) -> str:
        """Return the name for ``context``."""


NamingEntry = NameExpr | InstanceOf[NameRenderer]


class NamingScheme(BaseModel):
    """Naming entries. Only explicitly supplied entries take part in layering, so a scheme can
    override a single entry; an explicit ``None`` disables (unmanages) that entry.

    Precedence: library defaults < engine defaults < resolved blueprint naming < call-time naming.
    An entry is replaced as a whole — expressions are never merged structurally.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)

    inventory_label: NamingEntry | None = None
    inventory_description: NamingEntry | None = None
    device_label: NamingEntry | None = None
    device_description: NamingEntry | None = None
    endpoint_label: NamingEntry | None = None
    endpoint_description: NamingEntry | None = None

    @model_validator(mode="after")
    def _validate_expressions(self) -> NamingScheme:
        problems = [
            f"{entry}: {message}"
            for entry, expr in self.entries().items()
            for message in validate_expression(entry, expr)
        ]
        if problems:
            raise ValueError("; ".join(problems))
        return self

    def entries(self) -> dict[str, NamingEntry | None]:
        """The explicitly supplied entries (including explicit ``None``)."""
        return {name: getattr(self, name) for name in NAMING_ENTRIES if name in self.model_fields_set}

    @classmethod
    def layered(cls, *schemes: NamingScheme | None) -> NamingScheme:
        """Combine schemes entry by entry; later schemes win for the entries they supply."""
        merged: dict[str, Any] = {}
        for scheme in schemes:
            if scheme is not None:
                merged.update(scheme.entries())
        return cls(**merged)


class BlueprintNaming(BaseModel):
    """The YAML form of naming entries (no Python renderers)."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    inventory_label: NameExpr | None = None
    inventory_description: NameExpr | None = None
    device_label: NameExpr | None = None
    device_description: NameExpr | None = None
    endpoint_label: NameExpr | None = None
    endpoint_description: NameExpr | None = None

    @model_validator(mode="after")
    def _validate_expressions(self) -> BlueprintNaming:
        problems = [
            f"{entry}: {message}"
            for entry in NAMING_ENTRIES
            if entry in self.model_fields_set
            for message in validate_expression(entry, getattr(self, entry))
        ]
        if problems:
            raise ValueError("; ".join(problems))
        return self

    def to_scheme(self) -> NamingScheme:
        return NamingScheme(**{name: getattr(self, name) for name in NAMING_ENTRIES if name in self.model_fields_set})


def validate_expression(entry: str, expr: Any) -> list[str]:
    """Static checks for one entry: template syntax, known paths, namespaces, and format specs."""
    if not isinstance(expr, (str, Text, Field, Join)):
        return []  # None (disabled) or a trusted Python renderer
    allowed = _ENTRY_NAMESPACES.get(entry, _NAMESPACES)
    problems: list[str] = []
    try:
        fields = _fields_of(expr)
    except _TemplateSyntaxError as exc:
        return [str(exc)]
    for field in fields:
        problem = _check_field(field, allowed)
        if problem:
            problems.append(problem)
    return problems


def reference_paths(expr: Any) -> list[str]:
    """Dotted paths used by a naming expression, for offline input-reference checks."""
    return [field.path for field in _fields_of(expr)]


def validate_naming_inputs(
    naming: NamingScheme,
    definitions: Mapping[str, InputDefinition],
    values: Mapping[str, JsonValue],
    *,
    entries: frozenset[str] | None = None,
) -> None:
    """Check naming inputs in the final layered scheme before reading server state."""
    issues: list[ValidationIssue] = []
    context = NameContext(inputs=dict(values))
    for entry, expression in naming.entries().items():
        if entries is not None and entry not in entries:
            continue
        for path in reference_paths(expression):
            if not path.startswith("inputs."):
                continue
            parts = path.split(".")[1:]
            definition = definitions.get(parts[0])
            message, code = None, "input.reference"
            if definition is None:
                message = "Naming reference must name a declared input."
            elif parts[0] not in values:
                message, code = "Required naming input is missing.", "input.missing"
            else:
                for part in parts[1:]:
                    if definition.type != "object":
                        message = "Naming input path traverses a non-object input."
                        break
                    properties = definition.properties or {}
                    if part not in properties:
                        if not definition.additional_properties:
                            message = "Unknown property in naming input reference."
                        break
                    definition = properties[part]
                if isinstance(context.value(path), (dict, list)):
                    message = "Naming inputs must reference scalar leaves."
            if message:
                issues.append(ValidationIssue(path=f"naming.{entry}", message=message, code=code))
    if issues:
        raise ProvisioningValidationError(issues)


def render_name(entry: str, expr: Any, context: NameContext) -> str:
    """Render ``expr`` for ``entry``; raises :class:`ProvisioningValidationError` on missing required
    values, type/format errors, failed mappings, or an empty/control-character result."""
    try:
        if isinstance(expr, (str, Text, Field, Join)):
            value = _render(expr, context)
        else:
            value = expr.render(context)
            if not isinstance(value, str):
                raise _RenderError(f"renderer returned {type(value).__name__}, expected str")
    except _Missing as missing:
        raise _naming_error(entry, f"required value '{missing.path}' is missing", "naming.missing") from None
    except _RenderError as exc:
        raise _naming_error(entry, str(exc), "naming.render") from None
    if not value.strip():
        raise _naming_error(entry, "rendered an empty name", "naming.empty")
    if _CONTROL_CHARS.search(value):
        raise _naming_error(entry, "rendered a name containing control characters", "naming.invalid")
    return value


# --- Internal ---

_NAMESPACES: frozenset[str] = frozenset({"device", "module", "endpoint", "vertex", "attributes", "inputs"})
_KNOWN_PATHS: frozenset[str] = frozenset(
    {
        "device.key",
        "device.label",
        "device.description",
        "module.position",
        "endpoint.direction",
        "endpoint.media",
        "endpoint.index",
        "endpoint.engine",
        "endpoint.program",
        "endpoint.leg",
        "vertex.factory_label",
        "vertex.id",
    }
)
_NON_ENDPOINT_NAMESPACES = frozenset({"device", "module", "attributes", "inputs"})
_ENTRY_NAMESPACES: dict[str, frozenset[str]] = {
    "inventory_label": _NON_ENDPOINT_NAMESPACES,
    "inventory_description": _NON_ENDPOINT_NAMESPACES,
    "device_label": _NON_ENDPOINT_NAMESPACES,
    "device_description": _NON_ENDPOINT_NAMESPACES,
    "endpoint_label": _NAMESPACES,
    "endpoint_description": _NAMESPACES,
}
_PATH_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_-]*)+")
_FORMAT_RE = re.compile(r"[<>^]?0?(?:[1-9][0-9]{0,2})?[ds]?")
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


class _TemplateSyntaxError(ValueError):
    pass


class _Missing(Exception):
    def __init__(self, path: str) -> None:
        self.path = path


class _RenderError(Exception):
    pass


def _naming_error(entry: str, message: str, code: str) -> ProvisioningValidationError:
    return ProvisioningValidationError(ValidationIssue(path=f"naming.{entry}", message=message, code=code))


def _compile_template(template: str) -> list[Text | Field]:
    """Compile ``"{a.b}-x{c.d:02d}"`` into literal and field blocks (``{{`` / ``}}`` escape braces)."""
    parts: list[Text | Field] = []
    buffer = ""
    index = 0
    while index < len(template):
        char = template[index]
        if char == "{":
            if template.startswith("{{", index):
                buffer += "{"
                index += 2
                continue
            end = template.find("}", index)
            if end == -1:
                raise _TemplateSyntaxError(f"unclosed '{{' in template {template!r}")
            token = template[index + 1 : end]
            if "{" in token:
                raise _TemplateSyntaxError(f"nested braces are not supported in template {template!r}")
            path, _, spec = token.partition(":")
            if buffer:
                parts.append(Text(buffer))
                buffer = ""
            parts.append(Field(path, format=spec or None))
            index = end + 1
        elif char == "}":
            if template.startswith("}}", index):
                buffer += "}"
                index += 2
                continue
            raise _TemplateSyntaxError(f"single '}}' in template {template!r}; use '}}}}' for a literal brace")
        else:
            buffer += char
            index += 1
    if buffer:
        parts.append(Text(buffer))
    return parts


def _fields_of(expr: Any) -> list[Field]:
    if isinstance(expr, str):
        return [part for part in _compile_template(expr) if isinstance(part, Field)]
    if isinstance(expr, Field):
        return [expr]
    if isinstance(expr, Join):
        return [field for part in expr.parts for field in _fields_of(part)]
    return []


def _check_field(field: Field, allowed: frozenset[str]) -> str | None:
    path = field.path
    if not _PATH_RE.fullmatch(path):
        return f"invalid field reference {path!r} (use dotted names such as 'device.label')"
    namespace = path.split(".", 1)[0]
    if namespace not in _NAMESPACES or (namespace not in {"attributes", "inputs"} and path not in _KNOWN_PATHS):
        return f"unknown field {path!r}"
    if namespace not in allowed:
        return f"field {path!r} is not available for this entry"
    if field.format is not None and not _FORMAT_RE.fullmatch(field.format):
        return f"unsupported format {field.format!r} for {path!r} (supported: alignment, 0-padding, width, d, s)"
    return None


def _render(expr: Any, context: NameContext) -> str:
    if isinstance(expr, str):
        return "".join(_render(part, context) for part in _compile_template(expr))
    if isinstance(expr, Text):
        return expr.text
    if isinstance(expr, Field):
        return _render_field(expr, context)
    if isinstance(expr, Join):
        rendered: list[str] = []
        for part in expr.parts:
            try:
                rendered.append(_render(part, context))
            except _Missing:
                if not expr.skip_missing:
                    raise
        return expr.separator.join(rendered)
    raise _RenderError(f"unsupported naming block {type(expr).__name__}")


def _render_field(field: Field, context: NameContext) -> str:
    value = context.value(field.path)
    if value is None:
        raise _Missing(field.path)
    if isinstance(value, (dict, list)):
        raise _RenderError(f"'{field.path}' is not a scalar value")
    if field.mapping is not None:
        key = value if isinstance(value, str) else str(value).lower() if isinstance(value, bool) else str(value)
        if key not in field.mapping:
            raise _RenderError(f"no mapping for value {key!r} of '{field.path}'")
        value = field.mapping[key]
    text = _format_value(field, value)
    return f"{field.prefix}{text}{field.suffix}"


def _format_value(field: Field, value: Any) -> str:
    spec = field.format or ""
    if spec.endswith("d") and (isinstance(value, bool) or not isinstance(value, int)):
        raise _RenderError(f"format {spec!r} requires an integer for '{field.path}'")
    if spec.endswith("s") and not isinstance(value, str):
        raise _RenderError(f"format {spec!r} requires a string for '{field.path}'")
    if isinstance(value, bool):
        value = str(value).lower()
    if not spec:
        return str(value)
    return format(value if isinstance(value, (int, float)) else str(value), spec)


# Defined after the helpers above, which its construction-time validation uses.
DEFAULT_NAMING = NamingScheme(
    inventory_label="{device.label}",
    device_label="{device.label}",
    endpoint_label=Join(
        parts=[
            "{device.label}",
            Field("module.position", prefix="M"),
            "{endpoint.direction}",
            "{endpoint.media}",
            Field("endpoint.index", format="02d"),
        ],
        separator="-",
        skip_missing=True,
    ),
)
"""Library defaults: Inventory and device labels use ``device.label``; endpoint labels join the device
label, an optional ``M<position>`` component, direction, media, and a two-digit index (for example
``device-a-TX-video-01`` or ``device-a-M1-RX-audio-01``). Descriptions are unmanaged by default."""


__all__ = [
    "DEFAULT_NAMING",
    "INVENTORY_NAMING_ENTRIES",
    "NAMING_ENTRIES",
    "TOPOLOGY_NAMING_ENTRIES",
    "BlueprintNaming",
    "Field",
    "Join",
    "NameContext",
    "NameExpr",
    "NameRenderer",
    "NamingScheme",
    "Text",
    "render_name",
    "validate_expression",
]
