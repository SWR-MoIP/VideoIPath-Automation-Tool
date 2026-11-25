"""Alarm order: worst severity first, documented tie-break, independent of server response order."""

from __future__ import annotations

from itertools import permutations

import pytest

from videoipath_automation_tool.apps.inspect.model.alarms import InspectApiAlarmItem
from videoipath_automation_tool.apps.inspect.snapshot import InspectSnapshot

from .test_snapshot import FakeFetcher


def test_tied_alarms_have_the_same_order_for_any_server_order() -> None:
    alarms = [
        _alarm("alarm-1", "link-down", ["leaf-a", "1", "10004"], severity=5, sa=2, title="Ethernet link down"),
        _alarm("alarm-2", "link-down", ["leaf-a", "1", "10002"], severity=5, sa=2, title="Ethernet link down 2"),
        _alarm("alarm-3", "licence", ["leaf-a"], severity=5, sa=2, title="Licence missing"),
        _alarm("alarm-4", "no-lock", ["leaf-a", "3", "10002"], severity=5, sa=2, title="No lock"),
        _alarm("alarm-5", "minor", ["leaf-a"], severity=3, sa=2, title="Minor alarm"),
    ]

    results = {_device_alarm_order(list(order)) for order in permutations(alarms)}

    assert results == {
        (
            ("alarm-3", "alarm-2", "alarm-1", "alarm-4", "alarm-5"),
            "Licence missing",
        )
    }


@pytest.mark.parametrize("reverse", [False, True])
def test_higher_sa_wins_a_severity_tie(reverse: bool) -> None:
    alarms = [
        _alarm("alarm-a", "a-alert", ["leaf-a"], severity=5, sa=2, title="Not service affecting"),
        _alarm("alarm-b", "b-alert", ["leaf-a"], severity=5, sa=5, title="Service affecting"),
    ]
    if reverse:
        alarms.reverse()

    order, message = _device_alarm_order(alarms)

    assert order == ("alarm-b", "alarm-a")
    assert message == "Service affecting"


def test_severity_still_ranks_before_sa() -> None:
    alarms = [
        _alarm("alarm-a", "a", ["leaf-a"], severity=3, sa=5, title="Minor but SA"),
        _alarm("alarm-b", "b", ["leaf-a"], severity=5, sa=0, title="Critical"),
    ]

    order, _ = _device_alarm_order(alarms)

    assert order == ("alarm-b", "alarm-a")


def test_missing_severity_and_identity_sort_last() -> None:
    alarms = [
        InspectApiAlarmItem.model_validate({"_id": "alarm-empty", "id": {"pointId": ["leaf-a"]}}),
        _alarm("alarm-x", "x", ["leaf-a"], severity=1, sa=None, title="Cleared"),
    ]

    order, _ = _device_alarm_order(alarms)

    assert order == ("alarm-x", "alarm-empty")


def _device_alarm_order(items: list[InspectApiAlarmItem]) -> tuple[tuple[str | None, ...], str | None]:
    fetcher = FakeFetcher()
    fetcher._alarms = items
    snapshot = InspectSnapshot(
        fetcher=fetcher,
        device_items=fetcher.get_device_skeleton(),
        edge_items=fetcher.get_edge_skeleton(),
    )
    device = snapshot.get_device("leaf-a")
    assert device is not None
    return tuple(alarm.id for alarm in device.alarms), device.status_message


def _alarm(
    alarm_id: str,
    alert_id: str,
    point_id: list[str],
    *,
    severity: int,
    sa: int | None,
    title: str,
) -> InspectApiAlarmItem:
    return InspectApiAlarmItem.model_validate(
        {
            "_id": alarm_id,
            "desc": {"alertId": {"label": title}},
            "id": {"alertId": alert_id, "component": 0, "pointId": point_id},
            "info": {"severity": severity, "sa": sa},
        }
    )
