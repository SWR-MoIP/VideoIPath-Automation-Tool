"""Object lifetime after app.inspect.refresh() (offline)."""

from __future__ import annotations

import logging

import pytest

from videoipath_automation_tool.apps.inspect.app.read import InspectReadMixin
from videoipath_automation_tool.apps.inspect.app.write import InspectWriteMixin
from videoipath_automation_tool.apps.inspect.domain.vertex import build_vertex
from videoipath_automation_tool.apps.inspect.errors import InspectPendingEditsError, InspectSnapshotReplacedError
from videoipath_automation_tool.apps.inspect.model.actions import InspectApiLookupInspectDeviceResponse
from videoipath_automation_tool.apps.inspect.model.collector import InspectApiNodeStatusItem
from videoipath_automation_tool.apps.inspect.model.update_topology import InspectApiUpdateTopologyResponse
from videoipath_automation_tool.apps.inspect.snapshot import InspectSnapshot

from .conftest import load_fixture

DEVICE_ID = "device-a"


def test_refresh_rejects_a_setter_and_update_on_the_old_object() -> None:
    api = _Api()
    app = _App(api, _skeleton(label="Device A"))
    old = app.get_device(DEVICE_ID)
    assert old is not None

    app.refresh()
    with pytest.raises(InspectSnapshotReplacedError, match="re-fetch the object after refresh"):
        old.label = "lost"
    assert old.label == "Device A"
    with pytest.raises(InspectSnapshotReplacedError, match="re-fetch the object after refresh"):
        app.update(old)

    fresh = app.get_device(DEVICE_ID)
    assert fresh is not None and fresh is not old
    with pytest.raises(ValueError, match="No pending edits to flush"):
        app.update(fresh)
    fresh.label = "New"
    result = app.update(fresh)
    assert result.ok
    assert api.update_calls[0].replaceDevices[DEVICE_ID].descriptor.label == "New"


def test_refresh_refuses_pending_edits_unless_discarded() -> None:
    api = _Api()
    app = _App(api, _skeleton(label="Device A"))
    device = app.get_device(DEVICE_ID)
    assert device is not None
    device.label = "pending"

    with pytest.raises(InspectPendingEditsError) as raised:
        app.refresh()
    assert raised.value.keys == [("device", DEVICE_ID)]
    assert device.label == "pending"
    assert app.get_device(DEVICE_ID) is device

    app.refresh(discard_pending=True)
    assert device.label == "Device A"
    with pytest.raises(InspectSnapshotReplacedError):
        device.label = "after-discard"


@pytest.mark.parametrize("edit", ["clear", "reject"])
def test_refresh_ignores_cleared_or_rejected_vertex_edits(edit: str) -> None:
    snapshot = _skeleton(label="Device A")
    app = _App(_Api(), snapshot)
    vertex = build_vertex(snapshot, "device-a.module-1.port-out-1", kind="ip")
    if edit == "clear":
        vertex.control = "full"
        vertex.control = None
    else:
        with pytest.raises(ValueError, match="Unsupported vertex control"):
            vertex.control = "invalid"
    assert snapshot.get_staged_edits("vertex", vertex.id) == {}
    assert snapshot.pending_edit_keys() == []
    app.refresh()
    assert snapshot.replaced


@pytest.mark.parametrize("discard_pending", [False, True])
def test_refresh_handles_edits_staged_during_loading(monkeypatch: pytest.MonkeyPatch, discard_pending: bool) -> None:
    snapshot = _skeleton(label="Device A")
    app = _App(_Api(), snapshot)
    device = app.get_device(DEVICE_ID)
    assert device is not None

    def load_with_pending_edit(load: str) -> InspectSnapshot:
        device.label = "staged-during-load"
        return _skeleton(label="Reloaded")

    monkeypatch.setattr(app, "_load_snapshot", load_with_pending_edit)
    if discard_pending:
        app.refresh(load="full", discard_pending=True)
        assert snapshot.replaced
        assert snapshot.pending_edit_keys() == []
        assert device.label == "Device A"
        assert app.get_device(DEVICE_ID).label == "Reloaded"
        assert app._load_mode == "full"
    else:
        with pytest.raises(InspectPendingEditsError) as raised:
            app.refresh(load="full")
        assert raised.value.keys == [("device", DEVICE_ID)]
        assert not snapshot.replaced
        assert app.get_device(DEVICE_ID) is device
        assert device.label == "staged-during-load"
        assert app._load_mode == "skeleton"
        assert app.update(device).ok


def test_failed_refresh_does_not_discard_pending_edits() -> None:
    snapshot = _skeleton(label="Device A")
    app = _App(_Api(), snapshot)
    device = app.get_device(DEVICE_ID)
    assert device is not None
    device.label = "pending"
    app.fail_load = True
    with pytest.raises(RuntimeError, match="load failed"):
        app.refresh(discard_pending=True)
    assert not snapshot.replaced
    assert device.label == "pending"
    assert app.update(device).ok


def test_transaction_opened_before_refresh_rejects_staging_and_commit() -> None:
    api = _Api()
    app = _App(api, _skeleton(label="Device A"))
    old = app.get_device(DEVICE_ID)
    assert old is not None

    with app.transaction() as tx:
        app.refresh()
        with pytest.raises(InspectSnapshotReplacedError):
            tx.place_device(DEVICE_ID, 1.0, 2.0)
        with pytest.raises(InspectSnapshotReplacedError):
            tx.update(old)
        with pytest.raises(InspectSnapshotReplacedError):
            tx.commit()
    assert api.update_calls == []


def test_failed_refresh_leaves_the_current_snapshot_writable() -> None:
    app = _App(_Api(), _skeleton(label="Device A"))
    device = app.get_device(DEVICE_ID)
    assert device is not None
    app.fail_load = True

    with pytest.raises(RuntimeError, match="load failed"):
        app.refresh()
    device.label = "still-writable"
    assert device.label == "still-writable"


def _skeleton(label: str) -> InspectSnapshot:
    node = InspectApiNodeStatusItem.model_validate(
        {
            "_id": DEVICE_ID,
            "deviceId": DEVICE_ID,
            "label": label,
            "desc": "",
            "tags": [],
            "meta": {"iconType": "default", "iconSize": "medium", "coordinates": {"x": 0, "y": 0}},
            "status": {"sa": 0, "severity": 0},
        }
    )
    return InspectSnapshot(device_items=[node])


class _App(InspectReadMixin, InspectWriteMixin):
    def __init__(self, api: _Api, snapshot: InspectSnapshot) -> None:
        self._inspect_api = api  # type: ignore[assignment]
        self._logger = logging.getLogger("test")
        self._snapshot = snapshot
        self._load_mode = "skeleton"
        self.fail_load = False

    def _load_snapshot(self, load: str) -> InspectSnapshot:
        if self.fail_load:
            raise RuntimeError("load failed")
        return _skeleton(label="Device A")


class _Api:
    def __init__(self) -> None:
        self.update_calls: list[object] = []
        self.update_response = InspectApiUpdateTopologyResponse.model_validate(
            load_fixture("update_topology_success.json")
        )
        self.devices = {
            DEVICE_ID: InspectApiLookupInspectDeviceResponse.model_validate(
                {
                    "data": {
                        "assignedTags": {"all": [], "inherited": {}, "inheritedConflict": False, "local": {}},
                        "fields": {
                            "coordinates": {"x": 0, "y": 0},
                            "descriptor": {"desc": "", "label": "Device A"},
                            "iconSize": "medium",
                            "iconType": "default",
                            "localAssignedTags": [],
                            "sdpStrategy": None,
                            "siteId": None,
                            "tags": [],
                            "virtualDeviceFields": None,
                        },
                    },
                    "header": {
                        "auth": True,
                        "caption": "OK",
                        "code": "OK",
                        "errorCodes": [],
                        "errorDetails": [],
                        "id": "0",
                        "msg": [],
                        "ok": True,
                        "user": "api-user",
                    },
                }
            )
        }

    def lookup_inspect_device(self, device_id: str) -> InspectApiLookupInspectDeviceResponse:
        return self.devices[device_id]

    def update_topology(self, delta: object) -> InspectApiUpdateTopologyResponse:
        self.update_calls.append(delta)
        return self.update_response
