"""Transaction unit tests with a fake API (offline).

Covers staging + intent application, payload-shape assertions against the verified write forms,
the three-flag commit result, conflict detection (compare-and-commit), the ``check_conflicts=False``
bypass, ``rebase``, and the post-commit targeted-refresh hook derivation.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from videoipath_automation_tool.apps.inspect.transaction import InspectTransaction
from videoipath_automation_tool.apps.inspect.errors import (
    InspectCommitConflictError,
    InspectCommitError,
    InspectEntityNotFoundError,
)
from videoipath_automation_tool.apps.inspect.model.actions import (
    InspectApiLookupEdgeResponseItem,
    InspectApiLookupInspectDeviceResponse,
    InspectApiLookupVertexResponseData,
)
from videoipath_automation_tool.apps.inspect.model.update_topology import InspectApiUpdateTopologyResponse

from .conftest import load_fixture

_OK_HEADER = {
    "auth": True,
    "caption": "OK",
    "code": "OK",
    "errorCodes": [],
    "errorDetails": [],
    "id": "0",
    "msg": [],
    "ok": True,
    "user": "api-user",
}

A_OUT = "device12.1.Ethernet1.out"
B_IN = "device7.0.swp1.in"
EDGE_ID = f"{A_OUT}::{B_IN}"


# --- Staging + payload shape ---


def test_connect_builds_edge_payload() -> None:
    api = FakeAPI()
    with _txn(api) as tx:
        tx.connect(A_OUT, B_IN, bidirectional=False, weight=10)
        tx.commit()
    delta = api.update_calls[0]
    assert list(delta.replaceEdges) == [EDGE_ID]
    edge = delta.replaceEdges[EDGE_ID]
    assert edge.fromId == A_OUT and edge.toId == B_IN
    assert edge.weight == 10 and edge.capacity == 65535 and edge.redundancyMode == "Any"


def test_connect_bidirectional_stages_reverse_edge() -> None:
    api = FakeAPI()
    with _txn(api) as tx:
        tx.connect(A_OUT, B_IN, bidirectional=True)
        tx.commit()
    keys = set(api.update_calls[0].replaceEdges)
    assert keys == {EDGE_ID, "device7.0.swp1.out::device12.1.Ethernet1.in"}


def test_connect_existing_edge_requires_overwrite() -> None:
    api = FakeAPI()
    api.edges[EDGE_ID] = _edge_item()
    with _txn(api) as tx:
        with pytest.raises(ValueError, match="already exists"):
            tx.connect(A_OUT, B_IN, bidirectional=False)


def test_update_edge_applies_intent() -> None:
    api = FakeAPI()
    api.edges[EDGE_ID] = _edge_item()
    with _txn(api) as tx:
        tx.update_edge(EDGE_ID, weight=42)
        tx.commit()
    assert api.update_calls[0].replaceEdges[EDGE_ID].weight == 42


def test_update_edge_missing_raises_not_found() -> None:
    api = FakeAPI()
    with _txn(api) as tx:
        with pytest.raises(InspectEntityNotFoundError):
            tx.update_edge(EDGE_ID, weight=42)


def test_update_device_only_changes_label_when_set() -> None:
    api = FakeAPI()
    api.devices["device12"] = _device_response(label="Original", icon_type="switch")
    with _txn(api) as tx:
        tx.update_device("device12", icon_type="router")
        tx.commit()
    form = api.update_calls[0].replaceDevices["device12"]
    assert form.descriptor.label == "Original"  # round-tripped, not cleared (descriptor mandatory)
    assert form.iconType == "router"


def test_update_device_sets_label() -> None:
    api = FakeAPI()
    api.devices["device12"] = _device_response(label="Original")
    with _txn(api) as tx:
        tx.update_device("device12", label="BU-LEAF-A")
        tx.commit()
    assert api.update_calls[0].replaceDevices["device12"].descriptor.label == "BU-LEAF-A"


def test_place_device_sets_coordinates() -> None:
    api = FakeAPI()
    api.devices["device12"] = _device_response()
    with _txn(api) as tx:
        tx.place_device("device12", 1600, 9050)
        tx.commit()
    assert api.update_calls[0].replaceDevices["device12"].coordinates == {"x": 1600, "y": 9050}


def test_update_vertex_sets_endpoint() -> None:
    api = FakeAPI()
    api.vertices[A_OUT] = _vertex_data()
    with _txn(api) as tx:
        tx.update_vertex(A_OUT, use_as_endpoint=True)
        tx.commit()
    assert api.update_calls[0].replaceVertices[A_OUT].useAsEndpoint is True


def test_update_vertex_assigns_tags_as_local() -> None:
    # Port tag assignment goes to localAssignedTags, not the plain fields.tags list.
    api = FakeAPI()
    api.vertices[A_OUT] = _vertex_data()
    with _txn(api) as tx:
        tx.update_vertex(A_OUT, tags=["Video~~T"])
        tx.commit()
    form = api.update_calls[0].replaceVertices[A_OUT]
    assert form.localAssignedTags == ["Video~~T"]
    assert form.tags == []


def test_remove_appends_to_remove_list() -> None:
    api = FakeAPI()
    with _txn(api) as tx:
        tx.remove(EDGE_ID)
        tx.commit()
    assert api.update_calls[0].remove == [EDGE_ID]


def test_disconnect_removes_both_directions() -> None:
    api = FakeAPI()
    with _txn(api) as tx:
        tx.disconnect(A_OUT, B_IN, bidirectional=True)
        tx.commit()
    assert set(api.update_calls[0].remove) == {EDGE_ID, "device7.0.swp1.out::device12.1.Ethernet1.in"}


# --- Commit result / failure ---


def test_commit_success_returns_result() -> None:
    api = FakeAPI()
    api.edges[EDGE_ID] = _edge_item()
    with _txn(api) as tx:
        tx.update_edge(EDGE_ID, weight=5)
        result = tx.commit()
    assert result.ok is True
    assert result.applied_ids == [EDGE_ID]


def test_commit_failure_raises_commit_error() -> None:
    api = FakeAPI()
    api.update_response = InspectApiUpdateTopologyResponse.model_validate(
        load_fixture("update_topology_fail_remove.json")
    )
    with _txn(api) as tx:
        tx.remove("nonexistent-edge-id-xyz")
        with pytest.raises(InspectCommitError) as exc:
            tx.commit()
    assert "non-existent" in str(exc.value)


def test_empty_commit_rejected() -> None:
    api = FakeAPI()
    tx = _txn(api)
    with pytest.raises(ValueError, match="Nothing staged"):
        tx.commit()


# --- Conflict detection (ADR-0009) ---


def test_conflict_detected_on_baseline_change() -> None:
    api = FakeAPI()
    api.edges[EDGE_ID] = _edge_item(weight=1)
    tx = _txn(api)
    tx.update_edge(EDGE_ID, weight=99)
    api.edges[EDGE_ID] = _edge_item(weight=5)  # concurrent out-of-band change
    with pytest.raises(InspectCommitConflictError) as exc:
        tx.commit()
    conflict = exc.value.conflicts[0]
    assert conflict.entity_id == EDGE_ID
    assert "weight" in conflict.field_diffs
    assert conflict.field_diffs["weight"] == (1, 5)
    assert not api.update_calls  # nothing sent


def test_conflict_check_bypass() -> None:
    api = FakeAPI()
    api.edges[EDGE_ID] = _edge_item(weight=1)
    tx = _txn(api)
    tx.update_edge(EDGE_ID, weight=99)
    api.edges[EDGE_ID] = _edge_item(weight=5)
    tx.commit(check_conflicts=False)
    assert api.update_calls  # sent despite the change


def test_conflict_when_entity_vanishes() -> None:
    api = FakeAPI()
    api.edges[EDGE_ID] = _edge_item()
    tx = _txn(api)
    tx.update_edge(EDGE_ID, weight=7)
    api.edges.clear()  # removed out-of-band
    with pytest.raises(InspectCommitConflictError) as exc:
        tx.commit()
    assert "__exists__" in exc.value.conflicts[0].field_diffs


def test_rebase_refetches_baseline() -> None:
    api = FakeAPI()
    api.edges[EDGE_ID] = _edge_item(weight=1)
    tx = _txn(api)
    tx.update_edge(EDGE_ID, weight=99)
    api.edges[EDGE_ID] = _edge_item(weight=5)
    with pytest.raises(InspectCommitConflictError):
        tx.commit()
    tx.rebase()
    tx.commit()  # now baseline == server, no conflict
    assert api.update_calls[0].replaceEdges[EDGE_ID].weight == 99


# --- Post-commit refresh hook derivation (ADR-0010) ---


def test_post_commit_refresh_derives_affected_ids() -> None:
    api = FakeAPI()
    snapshot = FakeSnapshot()
    with _txn(api, snapshot=snapshot) as tx:
        tx.connect(A_OUT, B_IN, bidirectional=True)
        tx.commit()
    call = snapshot.calls[0]
    assert set(call["pair_ids"]) == {"device12::device7", "device7::device12"}
    assert call["device_ids"] == []
    assert call["mark_paths_stale"] is True


def test_post_commit_refresh_vertex_maps_to_device() -> None:
    api = FakeAPI()
    api.vertices[A_OUT] = _vertex_data()
    snapshot = FakeSnapshot()
    with _txn(api, snapshot=snapshot) as tx:
        tx.update_vertex(A_OUT, use_as_endpoint=True)
        tx.commit()
    assert snapshot.calls[0]["device_ids"] == ["device12"]


# --- Lifecycle ---


def test_reuse_after_commit_rejected() -> None:
    api = FakeAPI()
    api.edges[EDGE_ID] = _edge_item()
    tx = _txn(api)
    tx.update_edge(EDGE_ID, weight=5)
    tx.commit()
    with pytest.raises(RuntimeError, match="already committed"):
        tx.update_edge(EDGE_ID, weight=6)


def test_context_exit_without_commit_discards(caplog: pytest.LogCaptureFixture) -> None:
    api = FakeAPI()
    api.edges[EDGE_ID] = _edge_item()
    with _txn(api) as tx:
        tx.update_edge(EDGE_ID, weight=5)
    assert not api.update_calls
    assert tx._discarded


# --- Internal ---


def _device_response(
    label: str = "Dev A",
    coordinates: dict[str, int] | None = None,
    icon_type: str = "switch",
    tags: list[str] | None = None,
) -> InspectApiLookupInspectDeviceResponse:
    return InspectApiLookupInspectDeviceResponse.model_validate(
        {
            "data": {
                "assignedTags": {"all": [], "inherited": {}, "inheritedConflict": False, "local": {}},
                "fields": {
                    "coordinates": coordinates or {"x": 0, "y": 0},
                    "descriptor": {"desc": "", "label": label},
                    "iconSize": "medium",
                    "iconType": icon_type,
                    "localAssignedTags": [],
                    "sdpStrategy": None,
                    "siteId": None,
                    "tags": tags or [],
                    "virtualDeviceFields": None,
                },
            },
            "header": _OK_HEADER,
        }
    )


def _vertex_data() -> InspectApiLookupVertexResponseData:
    fixture = load_fixture("lookup_inspect_vertex_by_id.json")
    return InspectApiLookupVertexResponseData.model_validate(fixture["data"])


def _edge_item(weight: int = 1) -> InspectApiLookupEdgeResponseItem:
    edge = {
        "active": True,
        "bandwidth": -1.0,
        "capacity": 65535,
        "conflictPri": 0,
        "descriptor": {"desc": "", "label": ""},
        "excludeFormats": [],
        "fDescriptor": {"desc": "", "label": ""},
        "fromId": A_OUT,
        "includeFormats": [],
        "redundancyMode": "Any",
        "tags": [],
        "toId": B_IN,
        "weight": weight,
        "weightFactors": {"bandwidth": {"weight": 0}, "service": {"max": 100, "weight": 0}},
    }
    return InspectApiLookupEdgeResponseItem.model_validate(
        {"edge": edge, "fromDevice": "device12", "toDevice": "device7"}
    )


class FakeAPI:
    def __init__(self) -> None:
        self.devices: dict[str, InspectApiLookupInspectDeviceResponse] = {}
        self.vertices: dict[str, InspectApiLookupVertexResponseData] = {}
        self.edges: dict[str, InspectApiLookupEdgeResponseItem] = {}
        self.update_response = InspectApiUpdateTopologyResponse.model_validate(
            load_fixture("update_topology_success.json")
        )
        self.update_calls: list[Any] = []
        self.lookup_device_calls: list[str] = []
        self.lookup_vertices_calls: list[list[str]] = []
        self.lookup_edges_calls: list[list[str]] = []

    def lookup_inspect_device(self, device_id: str) -> InspectApiLookupInspectDeviceResponse:
        self.lookup_device_calls.append(device_id)
        if device_id not in self.devices:
            raise KeyError(device_id)
        return self.devices[device_id]

    def lookup_vertices(self, ids: list[str]) -> SimpleNamespace:
        self.lookup_vertices_calls.append(list(ids))
        return SimpleNamespace(data={i: self.vertices[i] for i in ids if i in self.vertices})

    def lookup_edges(self, ids: list[str]) -> SimpleNamespace:
        self.lookup_edges_calls.append(list(ids))
        return SimpleNamespace(data={i: self.edges[i] for i in ids if i in self.edges})

    def update_topology(self, delta: Any) -> InspectApiUpdateTopologyResponse:
        self.update_calls.append(delta)
        return self.update_response


class FakeSnapshot:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def apply_post_commit(self, **kwargs: Any) -> None:
        self.calls.append(kwargs)


def _txn(api: FakeAPI, snapshot: FakeSnapshot | None = None) -> InspectTransaction:
    return InspectTransaction(api, snapshot=snapshot)
