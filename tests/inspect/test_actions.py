"""Network-action mixin tests with a fake connector."""

from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any

import pytest

from videoipath_automation_tool.apps.inspect.app.actions import ConflictStrategy, InspectActionsMixin
from videoipath_automation_tool.apps.inspect.api import InspectAPI

_ADD_DEVICES = "/rest/v2/actions/status/network/addDevices"
_SYNC_DEVICES = "/rest/v2/actions/status/network/syncDevices"


class FakeRest:
    def __init__(
        self,
        post_data: dict[str, Any] | None = None,
        *,
        by_path: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self._post_data = post_data if post_data is not None else {"msg": [], "ok": True}
        self._by_path = by_path or {}
        self.post_calls: list[tuple[str, dict[str, Any]]] = []

    def post(self, url_path: str, body: Any, **kwargs: Any) -> SimpleNamespace:
        self.post_calls.append((url_path, body.model_dump(mode="json", by_alias=True)))
        data = self._by_path.get(url_path, self._post_data)
        return SimpleNamespace(data=data, header=_ok_header())


def test_conflict_strategy_values() -> None:
    assert int(ConflictStrategy.STRICT) == 0
    assert int(ConflictStrategy.INVALIDATE_SERVICES) == 1
    assert int(ConflictStrategy.CANCEL_SERVICES) == 2


def test_add_devices_builds_placement_items() -> None:
    app = _App()
    assert app.add_devices_to_topology([("device12", 100, 200), "device13"], sync=False) is True
    paths = [path for path, _ in app._inspect_api.vip_connector.rest.post_calls]
    assert paths == [_ADD_DEVICES]
    _, payload = app._inspect_api.vip_connector.rest.post_calls[0]
    assert payload["data"] == [{"id": "device12", "x": 100, "y": 200}, {"id": "device13", "x": 0, "y": 0}]


def test_add_devices_syncs_by_default() -> None:
    app = _App()
    assert app.add_devices_to_topology([("device12", 100, 200), "device13"]) is True
    rest = app._inspect_api.vip_connector.rest
    assert [path for path, _ in rest.post_calls] == [_ADD_DEVICES, _SYNC_DEVICES]
    assert rest.post_calls[0][1]["data"] == [
        {"id": "device12", "x": 100, "y": 200},
        {"id": "device13", "x": 0, "y": 0},
    ]
    assert rest.post_calls[1][1]["data"] == {
        "ids": ["device12", "device13"],
        "addOnly": True,
        "conflictStrategy": 0,
    }


def test_add_devices_passes_sync_options() -> None:
    app = _App()
    assert (
        app.add_devices_to_topology(
            ["device12"],
            sync=True,
            add_only=False,
            conflict_strategy=ConflictStrategy.CANCEL_SERVICES,
        )
        is True
    )
    _, sync_payload = app._inspect_api.vip_connector.rest.post_calls[1]
    assert sync_payload["data"] == {
        "ids": ["device12"],
        "addOnly": False,
        "conflictStrategy": 2,
    }


def test_add_devices_sync_false_skips_sync() -> None:
    app = _App()
    assert app.add_devices_to_topology(["device12"], sync=False) is True
    paths = [path for path, _ in app._inspect_api.vip_connector.rest.post_calls]
    assert paths == [_ADD_DEVICES]


def test_sync_devices_passes_strategy() -> None:
    app = _App()
    app.sync_devices(["device12"], add_only=True, conflict_strategy=ConflictStrategy.CANCEL_SERVICES)
    _, payload = app._inspect_api.vip_connector.rest.post_calls[0]
    assert payload["data"] == {"ids": ["device12"], "addOnly": True, "conflictStrategy": 2}


def test_sync_devices_reports_failure() -> None:
    app = _App({"msg": ["No topology reported by the device"], "ok": False})
    assert app.sync_devices(["device12"]) is False


def test_empty_lists_rejected() -> None:
    app = _App()
    with pytest.raises(ValueError):
        app.sync_devices([])
    with pytest.raises(ValueError):
        app.get_sync_info([])


# --- Post-action snapshot refresh ---


def test_add_devices_refreshes_snapshot_when_loaded() -> None:
    snap = _RecordingSnapshot()
    app = _App(snapshot=snap)
    assert app.add_devices_to_topology([("device12", 1, 2), "device13"]) is True
    assert snap.network_refresh_calls == [["device12", "device13"]]


def test_sync_devices_refreshes_snapshot_when_loaded() -> None:
    snap = _RecordingSnapshot()
    app = _App(snapshot=snap)
    assert app.sync_devices(["device12", "device13"]) is True
    assert snap.network_refresh_calls == [["device12", "device13"]]


def test_network_action_without_snapshot_does_not_build_one() -> None:
    # _snapshot is None: a pure-action workflow must not trigger a topology read.
    app = _App()
    assert app.add_devices_to_topology(["device12"]) is True


def test_failed_action_does_not_refresh() -> None:
    snap = _RecordingSnapshot()
    app = _App({"msg": ["nope"], "ok": False}, snapshot=snap)
    assert app.sync_devices(["device12"]) is False
    assert snap.network_refresh_calls == []


def test_add_devices_failure_skips_sync_and_refresh() -> None:
    snap = _RecordingSnapshot()
    app = _App(
        by_path={_ADD_DEVICES: {"msg": ["add failed"], "ok": False}},
        snapshot=snap,
    )
    assert app.add_devices_to_topology(["device12"]) is False
    paths = [path for path, _ in app._inspect_api.vip_connector.rest.post_calls]
    assert paths == [_ADD_DEVICES]
    assert snap.network_refresh_calls == []


def test_add_devices_sync_failure_refreshes_and_returns_false() -> None:
    snap = _RecordingSnapshot()
    app = _App(
        by_path={
            _ADD_DEVICES: {"msg": [], "ok": True},
            _SYNC_DEVICES: {"msg": ["sync failed"], "ok": False},
        },
        snapshot=snap,
    )
    assert app.add_devices_to_topology(["device12"]) is False
    paths = [path for path, _ in app._inspect_api.vip_connector.rest.post_calls]
    assert paths == [_ADD_DEVICES, _SYNC_DEVICES]
    assert snap.network_refresh_calls == [["device12"]]


# --- Internal ---


def _ok_header() -> SimpleNamespace:
    return SimpleNamespace(
        model_dump=lambda mode="json": {
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
    )


class _RecordingSnapshot:
    """Stand-in that records apply_network_refresh calls (see snapshot.apply_network_refresh)."""

    def __init__(self) -> None:
        self.network_refresh_calls: list[list[str]] = []

    def apply_network_refresh(self, device_ids: list[str]) -> None:
        self.network_refresh_calls.append(list(device_ids))


class _App(InspectActionsMixin):
    def __init__(
        self,
        post_data: dict[str, Any] | None = None,
        snapshot: _RecordingSnapshot | None = None,
        *,
        by_path: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self._logger = logging.getLogger("test")
        self._inspect_api = InspectAPI(
            SimpleNamespace(rest=FakeRest(post_data, by_path=by_path)),
            self._logger,
        )
        self._snapshot = snapshot
