"""Vertex control levels and their Inspect edit-form representation.

Control intents stay semantic until applied to a fresh edit form so rebasing preserves
unmanaged configuration priority and server-specific properties.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, cast, get_args

from pydantic import BaseModel

from videoipath_automation_tool.apps.inspect.errors import InspectUnsupportedFieldError
from videoipath_automation_tool.apps.inspect.model.actions import InspectApiVertexControlProps, InspectApiVertexEditForm
from videoipath_automation_tool.apps.inspect.model.common import InspectControl

_CONTROL_LEVELS: tuple[str, ...] = get_args(InspectControl)
_CONTROL_KEYS = ("control", "controlProps")


def validate_control(value: str) -> InspectControl:
    if value not in _CONTROL_LEVELS:
        expected = ", ".join(repr(level) for level in _CONTROL_LEVELS)
        raise ValueError(f"Unsupported vertex control {value!r}; expected one of {expected}.")
    return cast(InspectControl, value)


def control_from_props(props: InspectApiVertexControlProps | None) -> InspectControl | None:
    """Decode a known edit form's properties; incomplete properties have unknown control."""
    if props is None:
        return "off"
    if props.onlyInitial is None:
        return None
    return "semi" if props.onlyInitial else "full"


def control_from_form(form: InspectApiVertexEditForm | None) -> InspectControl | None:
    """Control level of a loaded edit form, or ``None`` without one.

    A form without ``controlProps`` is uncontrolled: every write serializes the field as null.
    """
    if form is None:
        return None
    return control_from_props(form.controlProps)


def control_to_props(value: str, props: InspectApiVertexControlProps | None) -> InspectApiVertexControlProps | None:
    """Change the control mode while preserving the other properties on the current form."""
    control = validate_control(value)
    if control == "off":
        return None
    result = props.model_copy(deep=True) if props is not None else InspectApiVertexControlProps()
    if result.configPriority is None:
        result.configPriority = "off"
    result.onlyInitial = control == "semi"
    return result


def validate_vertex_intents(updates: Iterable[tuple[str, Any]]) -> list[tuple[str, Any]]:
    """Validate control edits and detach property objects; ``control=None`` stays an unmanage marker."""
    validated: list[tuple[str, Any]] = []
    for key, value in updates:
        if key == "control" and value is not None:
            value = validate_control(value)
        elif key == "controlProps" and value is not None:
            value = InspectApiVertexControlProps.model_validate(value).model_copy(deep=True)
        validated.append((key, value))
    return validated


def merge_vertex_intents(target: dict[str, Any], updates: Iterable[tuple[str, Any]]) -> None:
    """Merge validated edits, keeping control edits in their latest assignment order.

    ``control=None`` drops every pending control edit, leaving control unmanaged.
    """
    for key, value in updates:
        if key == "control" and value is None:
            for control_key in _CONTROL_KEYS:
                target.pop(control_key, None)
            continue
        if key in _CONTROL_KEYS:
            target.pop(key, None)
        target[key] = value


def has_control_intents(intents: Mapping[str, Any]) -> bool:
    return any(key in intents for key in _CONTROL_KEYS)


def needs_control_baseline(intents: Mapping[str, Any]) -> bool:
    """Whether resolving the pending control edits depends on the current ``controlProps``.

    A pending replacement (including null) or a pending ``off`` determines the result on its own.
    """
    return "controlProps" not in intents and intents.get("control") != "off"


def staged_control_props(
    props: InspectApiVertexControlProps | None, intents: Mapping[str, Any]
) -> InspectApiVertexControlProps | None:
    """Resolve ordered pending control edits onto ``props`` without mutating it."""
    result = props.model_copy(deep=True) if props is not None else None
    for key, value in intents.items():
        if key == "controlProps":
            result = (
                InspectApiVertexControlProps.model_validate(value).model_copy(deep=True) if value is not None else None
            )
        elif key == "control":
            result = control_to_props(value, result)
    return result


def require_supported_type_field(form: InspectApiVertexEditForm, wire_path: str, *, entity_id: str) -> None:
    """Reject a ``typeFields.*`` path whose key is absent from the lookup form.

    Only ``typeFields`` paths are checked. Top-level keys such as ``control`` are absent from
    the form by design and are mapped onto ``controlProps`` at commit.
    """
    if not wire_path.startswith("typeFields."):
        return
    if _form_has_path(form, wire_path):
        return
    raise InspectUnsupportedFieldError(entity_id, wire_path, kind="vertex")


def _form_has_path(form: InspectApiVertexEditForm, wire_path: str) -> bool:
    node: Any = form
    for key in wire_path.split("."):
        if not _node_has_key(node, key):
            return False
        node = _node_child(node, key)
    return True


def _node_has_key(node: Any, key: str) -> bool:
    if isinstance(node, BaseModel):
        return key in node.model_fields_set or key in (node.model_extra or {})
    if isinstance(node, dict):
        return key in node
    return False


def _node_child(node: Any, key: str) -> Any:
    if isinstance(node, BaseModel):
        extra = node.model_extra or {}
        if key in extra:
            return extra[key]
        return getattr(node, key)
    return node[key]


def control_wire_intents(intents: Mapping[str, Any], props: InspectApiVertexControlProps | None) -> dict[str, Any]:
    """Replace semantic control edits with the resolved ``controlProps`` wire intent."""
    if not has_control_intents(intents):
        return dict(intents)
    wire = {key: value for key, value in intents.items() if key not in _CONTROL_KEYS}
    wire["controlProps"] = staged_control_props(props, intents)
    return wire
