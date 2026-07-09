"""Network-action mixin tests with a fake connector."""

from types import SimpleNamespace

import pytest

from videoipath_automation_tool.apps.inspect.app.actions import ConflictStrategy, InspectActionsMixin
from videoipath_automation_tool.apps.inspect.api import InspectAPI


def _ok_header():
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


class FakeRest:
    def __init__(self, post_data):
        self._post_data = post_data
        self.post_calls = []

    def post(self, url_path, body, **kwargs):
        self.post_calls.append((url_path, body.model_dump(mode="json", by_alias=True)))
        return SimpleNamespace(data=self._post_data, header=_ok_header())


class _RecordingSnapshot:
    """Stand-in that records apply_network_refresh calls (see snapshot.apply_network_refresh)."""

    def __init__(self):
        self.network_refresh_calls = []

    def apply_network_refresh(self, device_ids):
        self.network_refresh_calls.append(list(device_ids))


class _App(InspectActionsMixin):
    def __init__(self, post_data, snapshot=None):
        import logging

        self._logger = logging.getLogger("test")
        self._inspect_api = InspectAPI(SimpleNamespace(rest=FakeRest(post_data)), self._logger)
        self._snapshot = snapshot


def test_conflict_strategy_values():
    assert int(ConflictStrategy.STRICT) == 0
    assert int(ConflictStrategy.INVALIDATE_SERVICES) == 1
    assert int(ConflictStrategy.CANCEL_SERVICES) == 2


def test_add_devices_builds_placement_items():
    app = _App({"msg": [], "ok": True})
    assert app.add_devices_to_topology([("device12", 100, 200), "device13"]) is True
    _, payload = app._inspect_api.vip_connector.rest.post_calls[0]
    assert payload["data"] == [{"id": "device12", "x": 100, "y": 200}, {"id": "device13", "x": 0, "y": 0}]


def test_sync_devices_passes_strategy():
    app = _App({"msg": [], "ok": True})
    app.sync_devices(["device12"], add_only=True, conflict_strategy=ConflictStrategy.CANCEL_SERVICES)
    _, payload = app._inspect_api.vip_connector.rest.post_calls[0]
    assert payload["data"] == {"ids": ["device12"], "addOnly": True, "conflictStrategy": 2}


def test_sync_devices_reports_failure():
    app = _App({"msg": ["No topology reported by the device"], "ok": False})
    assert app.sync_devices(["device12"]) is False


def test_empty_lists_rejected():
    app = _App({"msg": [], "ok": True})
    with pytest.raises(ValueError):
        app.sync_devices([])
    with pytest.raises(ValueError):
        app.get_sync_info([])


# --- Post-action snapshot refresh (ADR-0010) ---


def test_add_devices_refreshes_snapshot_when_loaded():
    snap = _RecordingSnapshot()
    app = _App({"msg": [], "ok": True}, snapshot=snap)
    assert app.add_devices_to_topology([("device12", 1, 2), "device13"]) is True
    assert snap.network_refresh_calls == [["device12", "device13"]]


def test_sync_devices_refreshes_snapshot_when_loaded():
    snap = _RecordingSnapshot()
    app = _App({"msg": [], "ok": True}, snapshot=snap)
    assert app.sync_devices(["device12", "device13"]) is True
    assert snap.network_refresh_calls == [["device12", "device13"]]


def test_network_action_without_snapshot_does_not_build_one():
    # _snapshot is None: a pure-action workflow must not trigger a topology read.
    app = _App({"msg": [], "ok": True})
    assert app.add_devices_to_topology(["device12"]) is True


def test_failed_action_does_not_refresh():
    snap = _RecordingSnapshot()
    app = _App({"msg": ["nope"], "ok": False}, snapshot=snap)
    assert app.sync_devices(["device12"]) is False
    assert snap.network_refresh_calls == []
