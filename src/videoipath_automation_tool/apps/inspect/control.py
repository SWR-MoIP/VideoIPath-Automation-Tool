"""Vertex control levels and their Inspect edit-form representation.

Control intents stay semantic until applied to a fresh edit form so rebasing preserves
unmanaged configuration priority and server-specific properties.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from videoipath_automation_tool.apps.inspect.model.actions import InspectApiVertexControlProps, InspectApiVertexEditForm
from videoipath_automation_tool.apps.inspect.model.common import InspectControl


def validate_control(value: str) -> InspectControl:
    if value not in ("full", "semi", "off"):
        raise ValueError(f"Unsupported vertex control {value!r}; expected 'full', 'semi', or 'off'.")
    return cast(InspectControl, value)


def control_from_props(props: InspectApiVertexControlProps | None) -> InspectControl | None:
    """Decode a known edit form's properties; incomplete properties have unknown control."""
    if props is None:
        return "off"
    if props.onlyInitial is None:
        return None
    return "semi" if props.onlyInitial else "full"


def control_from_form(form: InspectApiVertexEditForm | None) -> InspectControl | None:
    """Distinguish an explicit null (off) from a missing form or missing control field."""
    if form is None or "controlProps" not in form.model_fields_set:
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


def merge_vertex_intents(target: dict[str, Any], updates: Mapping[str, Any]) -> None:
    """Validate control edits and keep their latest assignment order, including repeated keys."""
    validated = dict(updates)
    for key, value in updates.items():
        if key == "control":
            validated[key] = validate_control(value)
        elif key == "controlProps" and value is not None:
            validated[key] = InspectApiVertexControlProps.model_validate(value).model_copy(deep=True)
    for key, value in validated.items():
        if key in ("control", "controlProps"):
            target.pop(key, None)
        target[key] = value


def staged_control_props(
    props: InspectApiVertexControlProps | None, intents: Mapping[str, Any]
) -> InspectApiVertexControlProps | None:
    """Resolve ordered pending control edits for a domain view without mutating its baseline."""
    result = props.model_copy(deep=True) if props is not None else None
    for key, value in intents.items():
        if key == "controlProps":
            result = (
                InspectApiVertexControlProps.model_validate(value).model_copy(deep=True) if value is not None else None
            )
        elif key == "control":
            result = control_to_props(value, result)
    return result
