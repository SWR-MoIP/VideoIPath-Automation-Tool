"""``service.alarms`` correlates service alarms (``pointId = ["book", <booking id>]``) to the booking."""

from __future__ import annotations

import pytest

from videoipath_automation_tool.apps.inspect.model.alarms import InspectApiAlarmItem
from videoipath_automation_tool.apps.inspect.snapshot import InspectSnapshot

from .test_snapshot import FakeFetcher


@pytest.fixture
def snap() -> tuple[InspectSnapshot, FakeFetcher]:
    fetcher = FakeFetcher()
    snapshot = InspectSnapshot(
        fetcher=fetcher,
        device_items=fetcher.get_device_skeleton(),
        edge_items=fetcher.get_edge_skeleton(),
    )
    return snapshot, fetcher


def test_service_alarms_returns_booking_alarms(snap: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snapshot, fetcher = snap
    fetcher._alarms = [
        _service_alarm("alarm-1", "1001", "device-a, module-1, port-1: Link down"),
        _service_alarm("alarm-2", "1002", "device-b, module-1, port-1: Link down"),
    ]

    service = snapshot.get_service_by_booking_id("1001")

    assert service is not None
    assert [alarm.id for alarm in service.alarms] == ["alarm-1"]
    assert service.alarms[0].message == "Service alarm active: device-a, module-1, port-1: Link down"


def test_service_alarms_ignore_alarms_keyed_by_bare_booking_id(snap: tuple[InspectSnapshot, FakeFetcher]) -> None:
    snapshot, fetcher = snap
    fetcher._alarms = [
        InspectApiAlarmItem.model_validate({"_id": "alarm-1", "id": {"alertId": "x", "pointId": ["1001"]}})
    ]

    service = snapshot.get_service_by_booking_id("1001")

    assert service is not None
    assert service.alarms == []


def _service_alarm(alarm_id: str, booking_id: str, details: str) -> InspectApiAlarmItem:
    """A service alarm in the live 2025.4 shape (anonymized)."""
    return InspectApiAlarmItem.model_validate(
        {
            "_id": alarm_id,
            "acked": False,
            "hidden": False,
            "desc": {
                "alertId": {"label": "Service alarm active", "desc": ""},
                "pointId": [{"label": "Booking"}, {"label": booking_id}],
            },
            "id": {"alertId": "service-alarm", "component": 0, "pointId": ["book", booking_id]},
            "info": {"details": details, "severity": 4, "sa": 4},
        }
    )
