"""Control levels round-trip through the public Inspect write surfaces."""

from __future__ import annotations

import json
from typing import Any

import pytest

from videoipath_automation_tool.apps.inspect.domain.vertex import build_vertex
from videoipath_automation_tool.apps.inspect.errors import InspectCommitConflictError
from videoipath_automation_tool.apps.inspect.model.actions import InspectApiVertexControlProps, InspectApiVertexEditForm
from videoipath_automation_tool.apps.inspect.snapshot import InspectSnapshot
from videoipath_automation_tool.apps.inspect.transaction import InspectTransaction

from .test_domain_writes import _WriteApp
from .test_transaction import FakeAPI, _vertex_data

VERTEX_ID = "device-a.core.v"


@pytest.mark.parametrize("mode", ["full", "semi", "off"])
@pytest.mark.parametrize("surface", ["domain", "direct", "transaction", "intents"])
def test_control_write_surfaces(mode: str, surface: str) -> None:
    original = {"configPriority": "high", "onlyInitial": False, "extension": {"enabled": True}}
    api, snapshot = _setup(original)
    app = _WriteApp(api, snapshot)
    vertex = build_vertex(snapshot, VERTEX_ID, kind="ip")
    if surface == "domain":
        vertex.control = mode
        assert vertex.control == mode
        assert api.update_calls == []
        app.update(vertex)
        assert snapshot.get_staged_edits("vertex", VERTEX_ID) == {}
    elif surface == "direct":
        app.update_vertex(VERTEX_ID, control=mode)
    else:
        with InspectTransaction(api) as tx:
            if surface == "intents":
                tx.update_vertex(VERTEX_ID, intents={"control": mode})
            else:
                tx.update_vertex(VERTEX_ID, control=mode)
            tx.commit()

    wire = json.loads(api.update_calls[0].model_dump_json())["replaceVertices"][VERTEX_ID]
    assert "control" not in wire
    assert wire["controlProps"] == (None if mode == "off" else {**original, "onlyInitial": mode == "semi"})
    assert api.vertices[VERTEX_ID].fields.controlProps.model_dump() == original


def test_enable_from_off_uses_exact_verified_payload() -> None:
    api, snapshot = _setup()
    _WriteApp(api, snapshot).update_vertex(VERTEX_ID, control="full")
    wire = api.update_calls[0].model_dump(mode="json")["replaceVertices"][VERTEX_ID]
    assert wire["controlProps"] == {"configPriority": "off", "onlyInitial": False}
    assert "control" not in wire


@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        ({"controlProps": None}, "off"),
        ({"controlProps": {"onlyInitial": False}}, "full"),
        ({"controlProps": {"onlyInitial": True}}, "semi"),
        ({"controlProps": {"configPriority": "off"}}, None),
        ({}, "off"),
    ],
)
def test_control_reads_edit_form(fields: dict[str, Any], expected: str | None) -> None:
    _, snapshot = _setup()
    snapshot._vertex_details[VERTEX_ID].fields = InspectApiVertexEditForm.model_validate(fields)
    assert build_vertex(snapshot, VERTEX_ID, kind="ip").control == expected


def test_control_without_form_and_unset_priority() -> None:
    snapshot = InspectSnapshot()
    vertex = build_vertex(snapshot, VERTEX_ID, kind="ip")
    assert vertex.control is None
    vertex.control_props = {"onlyInitial": True, "extension": "value-a"}
    assert vertex.control == "semi"
    vertex.control = "full"
    assert vertex.control_props.model_dump() == {"configPriority": "off", "onlyInitial": False, "extension": "value-a"}


@pytest.mark.parametrize("surface", ["domain", "transaction"])
def test_repeated_mixed_assignments_keep_latest_order(surface: str) -> None:
    api, snapshot = _setup({"configPriority": "low", "onlyInitial": False})
    edits = [
        ("control", "full"),
        ("controlProps", {"configPriority": "high", "onlyInitial": True}),
        ("control", "full"),
        ("controlProps", {"configPriority": "off"}),
        ("control", "semi"),
    ]
    if surface == "domain":
        vertex = build_vertex(snapshot, VERTEX_ID, kind="ip")
        for key, value in edits:
            setattr(vertex, "control_props" if key == "controlProps" else key, value)
        assert vertex.control == "semi"
        assert vertex.control_props.model_dump() == {"configPriority": "off", "onlyInitial": True}
        _WriteApp(api, snapshot).update(vertex)
    else:
        with InspectTransaction(api) as tx:
            for key, value in edits:
                tx.update_vertex(VERTEX_ID, **{"control_props" if key == "controlProps" else key: value})
            tx.commit()
    assert api.update_calls[0].replaceVertices[VERTEX_ID].controlProps.model_dump() == {
        "configPriority": "off",
        "onlyInitial": True,
    }


@pytest.mark.parametrize("surface", ["direct", "transaction"])
def test_control_and_properties_in_one_call_are_rejected(surface: str) -> None:
    api, snapshot = _setup()
    props = {"configPriority": "low", "onlyInitial": True}
    with pytest.raises(ValueError, match="not both"):
        if surface == "direct":
            _WriteApp(api, snapshot).update_vertex(VERTEX_ID, control="full", control_props=props)
        else:
            with InspectTransaction(api) as tx:
                tx.update_vertex(VERTEX_ID, control="full", control_props=props)
    assert api.update_calls == []
    assert api.lookup_vertices_calls == []


def test_none_control_properties_keyword_leaves_control_unchanged() -> None:
    original = {"configPriority": "high", "onlyInitial": True}
    api, snapshot = _setup(original)
    _WriteApp(api, snapshot).update_vertex(VERTEX_ID, label="label-a", control_props=None)
    assert api.update_calls[0].model_dump(mode="json")["replaceVertices"][VERTEX_ID]["controlProps"] == original


@pytest.mark.parametrize("surface", ["domain", "intents"])
def test_none_control_drops_pending_control_edits(surface: str) -> None:
    original = {"configPriority": "high", "onlyInitial": True}
    api, snapshot = _setup(original)
    if surface == "domain":
        vertex = build_vertex(snapshot, VERTEX_ID, kind="ip")
        vertex.control_props = None
        vertex.control = "full"
        vertex.control = None
        assert vertex.control == "semi"
        vertex.label = "label-a"
        _WriteApp(api, snapshot).update(vertex)
    else:
        with InspectTransaction(api) as tx:
            tx.update_vertex(VERTEX_ID, control="full")
            tx.update_vertex(VERTEX_ID, label="label-a", intents={"control": None})
            tx.commit()
    wire = api.update_calls[0].model_dump(mode="json")["replaceVertices"][VERTEX_ID]
    assert wire["controlProps"] == original
    assert wire["label"] == "label-a"


def test_staged_properties_are_detached_from_caller_and_getter() -> None:
    _, snapshot = _setup()
    vertex = build_vertex(snapshot, VERTEX_ID, kind="ip")
    props = InspectApiVertexControlProps(configPriority="high", onlyInitial=True)
    vertex.control_props = props
    props.onlyInitial = False
    vertex.control_props.onlyInitial = False
    assert vertex.control == "semi"


def test_staged_control_reads_do_not_fetch_when_baseline_is_unneeded() -> None:
    api = FakeAPI()
    snapshot = InspectSnapshot(fetcher=api)
    vertex = build_vertex(snapshot, VERTEX_ID, kind="ip")
    vertex.control = "full"
    assert vertex.control == "full"
    vertex.control = "off"
    assert vertex.control == "off" and vertex.control_props is None
    vertex.control_props = {"configPriority": "high", "onlyInitial": True}
    assert vertex.control == "semi"
    vertex.control = "full"
    assert vertex.control_props.model_dump() == {"configPriority": "high", "onlyInitial": False}
    assert api.lookup_vertices_calls == []


@pytest.mark.parametrize("surface", ["domain", "direct", "transaction", "intents"])
def test_invalid_control_is_rejected_before_writing(surface: str) -> None:
    api, snapshot = _setup()
    with pytest.raises(ValueError, match="Unsupported vertex control"):
        if surface == "domain":
            build_vertex(snapshot, VERTEX_ID, kind="ip").control = "invalid"
        elif surface == "direct":
            _WriteApp(api, snapshot).update_vertex(VERTEX_ID, control="invalid")
        else:
            with InspectTransaction(api) as tx:
                kwargs = {"intents": {"control": "invalid"}} if surface == "intents" else {"control": "invalid"}
                tx.update_vertex(VERTEX_ID, **kwargs)
    assert api.update_calls == []
    assert snapshot.get_staged_edits("vertex", VERTEX_ID) == {}


def test_rebase_preserves_latest_priority_and_unknown_properties() -> None:
    api, _ = _setup({"configPriority": "low", "onlyInitial": True})
    with InspectTransaction(api) as tx:
        tx.update_vertex(VERTEX_ID, control="full")
        api.vertices[VERTEX_ID].fields.controlProps = InspectApiVertexControlProps(
            configPriority="high", onlyInitial=True, extension="server-value"
        )
        with pytest.raises(InspectCommitConflictError):
            tx.commit()
        assert api.update_calls == []
        tx.rebase().commit()
    assert api.update_calls[0].replaceVertices[VERTEX_ID].controlProps.model_dump() == {
        "configPriority": "high",
        "onlyInitial": False,
        "extension": "server-value",
    }


# --- Internal ---


def _setup(props: dict[str, Any] | None = None) -> tuple[FakeAPI, InspectSnapshot]:
    api = FakeAPI()
    lookup = _vertex_data()
    lookup.id = VERTEX_ID
    lookup.fields.controlProps = InspectApiVertexControlProps.model_validate(props) if props is not None else None
    api.vertices[VERTEX_ID] = lookup
    snapshot = InspectSnapshot()
    snapshot._vertex_details[VERTEX_ID] = lookup.model_copy(deep=True)
    return api, snapshot
