"""Maintenance contracts: real wire shapes, fake transport, no live data."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime, time, timedelta
from types import SimpleNamespace
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from videoipath_automation_tool.apps.inspect import (
    InspectApp,
    InspectEntityNotFoundError,
    InspectMaintenanceConflictError,
    InspectMaintenanceError,
    MaintenanceBookingSpec,
    MaintenanceOnceSchedule,
    MaintenanceRecurringSchedule,
    MaintenanceTargets,
)
from videoipath_automation_tool.apps.inspect.api import InspectAPI, queries
from videoipath_automation_tool.apps.inspect.model.collector import (
    InspectApiCollectorResponse,
    InspectApiExternalEdgesByDeviceKeyItem,
    InspectApiNodeStatusItem,
)
from videoipath_automation_tool.apps.inspect.model.common import InspectApiRestV2Header
from videoipath_automation_tool.apps.inspect.snapshot import HydrationLevel, InspectSnapshot
from videoipath_automation_tool.connector.vip_rest_connector import VideoIPathRestConnector

START = datetime(2030, 1, 1, tzinfo=UTC)


@pytest.fixture
def booking() -> dict[str, Any]:
    return {
        "_id": "booking-a",
        "_vid": "view-a",
        "rev": "revision-a",
        "generic": {
            "descriptor": {"label": "maintenance-a", "desc": "Example maintenance"},
            "state": 0,
            "locked": False,
        },
        "scheduleInfo": {"startTimestamp": 1893456000000, "endTimestamp": 1893542400000, "infinite": False},
        "action": "nothing",
        "trigger": "create",
        "allowOverlap": False,
        "switchFormatStateOnReroute": False,
        "tags": ["tag-a"],
        "devices": [{"label": "device-a", "context": {"devicePid": "device-a"}, "pid": ["device-a"]}],
        "modules": [
            {
                "label": "module-1",
                "context": {"devicePid": "device-a", "modulePid": "device-a.dev.0"},
                "pid": ["device-a", "dev", "0"],
            }
        ],
        "ports": [
            {
                "label": "port-out-1",
                "context": {
                    "devicePid": "device-a",
                    "modulePid": "device-a.dev.0",
                    "portPid": "device-a.dev.0.port-out-1",
                },
                "pid": ["device-a", "dev", "0", "port-out-1"],
            }
        ],
        "edges": [],
    }


def test_once_schedule_timezone_nulls_and_validation() -> None:
    start = datetime(2030, 1, 1, 1, tzinfo=ZoneInfo("Europe/Berlin"))
    assert MaintenanceOnceSchedule(start=start).to_wire().startTimestamp == 1893456000000
    assert MaintenanceOnceSchedule().to_wire().model_dump() == {
        "type": "once",
        "startTimestamp": None,
        "endTimestamp": None,
    }
    with pytest.raises(ValidationError):
        MaintenanceOnceSchedule(start=datetime(2030, 1, 1))  # noqa: DTZ001 — invalid input under test
    with pytest.raises(ValidationError):
        MaintenanceOnceSchedule(start=START, end=START)


def test_once_schedule_orders_instants_across_dst_fold() -> None:
    zone = ZoneInfo("Europe/Berlin")
    first = datetime(2030, 10, 27, 2, 45, tzinfo=zone, fold=0)
    second = datetime(2030, 10, 27, 2, 15, tzinfo=zone, fold=1)
    wire = MaintenanceOnceSchedule(start=first, end=second).to_wire()
    assert wire.endTimestamp - wire.startTimestamp == 30 * 60 * 1000
    with pytest.raises(ValidationError):
        MaintenanceOnceSchedule(start=second, end=first)


@pytest.mark.parametrize("frequency,code,weekdays", [("daily", 0, []), ("weekly", 1, [1, 5]), ("monthly", 2, [])])
def test_recurring_encoding(frequency: str, code: int, weekdays: list[int]) -> None:
    schedule = _recurring(
        frequency=frequency, weekdays=weekdays, pattern_iteration_filter=[2], instance_iteration_filter=[3]
    )
    wire = schedule.to_wire().model_dump()
    assert wire == {
        "type": "recurring",
        "pattern": {
            "pattern": code,
            "startTime": 1893456000000,
            "endTime": 1896134400000,
            "timeZoneId": "Europe/Berlin",
            "weekDays": weekdays,
            "iterationFilter": [2],
        },
        "instance": {"localStartTime": 3600, "localEndTime": 7200, "iterationFilter": [3]},
    }


@pytest.mark.parametrize(
    "changes",
    [
        {"timezone": "not-a-zone"},
        {"end": START},
        {"start": datetime(2030, 1, 1)},  # noqa: DTZ001 — invalid input under test
        {"frequency": "weekly"},
        {"frequency": "weekly", "weekdays": [0]},
        {"frequency": "weekly", "weekdays": [1, 1]},
        {"weekdays": [2]},
        {"local_end": time(1)},
        {"local_start": time(1, tzinfo=UTC)},
        {"local_start": time(1, microsecond=1)},
    ],
)
def test_invalid_recurring_rules(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        _recurring(**changes)


def test_recurrence_is_batched_as_dated_windows() -> None:
    app, rest = _app([])
    app.create_maintenance_booking(_spec(schedule=_recurring()))
    assert len(rest.posts) == 1
    creates = rest.posts[0][1]["data"]["create"]
    assert len(creates) == 31
    assert all(c["scheduleInfo"]["type"] == "once" for c in creates)
    assert creates[0]["scheduleInfo"] == {
        "type": "once",
        "startTimestamp": 1893456000000,
        "endTimestamp": 1893459600000,
    }
    assert creates[1]["scheduleInfo"]["startTimestamp"] - creates[0]["scheduleInfo"]["startTimestamp"] == 86400000


def test_weekly_monthly_overnight_and_dst_expansion() -> None:
    weekly = _recurring(frequency="weekly", weekdays=[1, 5]).expand()
    assert all(w.start.astimezone(ZoneInfo("Europe/Berlin")).isoweekday() in (1, 5) for w in weekly)
    monthly = _recurring(
        frequency="monthly",
        start=datetime(2030, 1, 31, tzinfo=UTC),
        end=datetime(2030, 5, 1, tzinfo=UTC),
        local_end=time(4),
    ).expand()
    assert [w.start.month for w in monthly] == [1, 3]  # No February 31 or April 31.
    overnight = _recurring(local_start=time(23), local_end=time(1)).expand()[0]
    assert overnight.end - overnight.start == timedelta(hours=2)
    dst = _recurring(
        start=datetime(2030, 3, 30, tzinfo=UTC),
        end=datetime(2030, 4, 2, tzinfo=UTC),
        local_start=time(1),
        local_end=time(4),
    ).expand()
    assert [w.end - w.start for w in dst] == [timedelta(hours=3), timedelta(hours=2), timedelta(hours=3)]
    with pytest.raises(ValueError, match="Nonexistent"):
        _recurring(
            start=datetime(2030, 3, 30, tzinfo=UTC),
            end=datetime(2030, 4, 2, tzinfo=UTC),
            local_start=time(2, 30),
            local_end=time(4),
        ).expand()
    ambiguous = _recurring(
        start=datetime(2030, 10, 27, tzinfo=UTC),
        end=datetime(2030, 10, 28, tzinfo=UTC),
        local_start=time(2, 30),
        local_end=time(3),
    ).expand()
    assert ambiguous[0].start.hour == 0  # First 02:30 (summer offset).


def test_expansion_validation_precedes_writes() -> None:
    app, rest = _app([])
    for schedule in [
        _recurring(pattern_iteration_filter=[1]),
        _recurring(instance_iteration_filter=[1]),
        _recurring(end=START + timedelta(minutes=1)),
        _recurring(end=START + timedelta(days=1002)),
    ]:
        with pytest.raises(ValueError):
            app.create_maintenance_booking(_spec(schedule=schedule))
    assert not rest.posts


def test_targets_normalize_objects_and_keep_canonical_identifiers() -> None:
    snapshot = _snapshot()
    device = snapshot.get_device("device-a")
    module = device.modules[0]
    port = module.ports[0]
    targets = MaintenanceTargets(devices=[device, "device-a"], modules=[module], ports=[port])
    assert targets.pids == ["device-a", "device-a.dev.0", "device-a.dev.0.port-out-1"]
    assert targets.devices == ["device-a"]
    with pytest.raises(ValidationError):
        MaintenanceTargets(devices=[module])
    with pytest.raises(ValidationError):
        MaintenanceTargets(devices=[""])
    with pytest.raises(ValidationError):
        MaintenanceTargets(devices="device-a")
    with pytest.raises(ValidationError):
        MaintenanceBookingSpec(label="a", targets=MaintenanceTargets(), schedule=MaintenanceOnceSchedule())


def test_virtual_device_pid_differs_from_id() -> None:
    node = InspectApiNodeStatusItem(_id="virtual-1", _vid="1", deviceId="virtual.1", pid="virtual-1")
    snapshot = InspectSnapshot(device_items=[node])
    assert MaintenanceTargets(devices=[snapshot.get_device("virtual.1")]).pids == ["virtual-1"]


def test_lazy_section_filters_and_resource_relationships(booking: dict[str, Any]) -> None:
    active = deepcopy(booking)
    active.update(_id="booking-b", tags=["SPECIAL"])
    active["generic"]["state"] = 1
    future = deepcopy(booking)
    future.update(_id="booking-c")
    future["generic"]["state"] = 9
    app, rest = _app([booking, active, future])
    assert rest.get_calls == []
    assert len(app.maintenance_bookings) == 3
    assert app.get_maintenance_booking("booking-a") is app.maintenance_bookings[0]
    assert app.get_maintenance_booking("missing") is None
    assert len(app.find_maintenance_bookings("scheduled", "MAINTENANCE")) == 1
    assert len(app.find_maintenance_bookings("active", "special")) == 1
    assert app.get_maintenance_booking("booking-c").state == 9
    with pytest.raises(ValueError):
        app.find_maintenance_bookings("invalid")
    item = app.get_maintenance_booking("booking-a")
    assert item.starts_at == START
    assert item.ends_at == START + timedelta(days=1)
    assert item.description == "Example maintenance"
    assert item.action == "nothing" and item.trigger == "create"
    assert not item.allow_overlap and not item.switch_format_state_on_reroute
    assert item.devices[0].id == "device-a"
    assert item.modules[0].id == "device-a.dev.0"
    assert item.ports[0].id == "device-a.dev.0.port-out-1"
    assert item.id in [b.id for b in item.devices[0].maintenance_bookings]
    assert item.id in [b.id for b in item.modules[0].maintenance_bookings]
    assert item.id in [b.id for b in item.ports[0].maintenance_bookings]
    assert rest.get_calls == [queries.maintenance_section()]


def test_full_snapshot_reuses_bookings_and_preserves_unresolved_ids(booking: dict[str, Any]) -> None:
    booking["scheduleInfo"].update(infinite=True, endTimestamp=9223372036854775807)
    response = InspectApiCollectorResponse.model_validate(
        {
            "header": _header().model_dump(),
            "data": {"status": {"collector": {"maintenanceBookings": {"_items": [booking]}}}},
        }
    )
    snapshot = InspectSnapshot.from_full_response(response)
    item = snapshot.maintenance_bookings[0]
    assert item.ends_at is None
    assert item.devices == [] and item.modules == [] and item.ports == []
    assert item.raw.ports[0].pid == ["device-a", "dev", "0", "port-out-1"]
    assert snapshot.section_fetched_at("maintenance") is not None


def test_empty_reads_and_full_section_do_not_hydrate_devices() -> None:
    app, rest = _app([])
    node = InspectApiNodeStatusItem(_id="device-a", _vid="device-a", deviceId="device-a")
    app._snapshot = InspectSnapshot(fetcher=app._inspect_api, device_items=[node])
    assert app.maintenance_bookings == []
    assert app.find_maintenance_bookings("active") == []
    assert app.get_maintenance_booking("missing") is None
    assert not app._snapshot.is_device_hydrated("device-a")
    assert rest.get_calls == [queries.maintenance_section()]
    response = InspectApiCollectorResponse.model_validate(
        {"header": _header().model_dump(), "data": {"status": {"collector": {"maintenanceBookings": {"_items": []}}}}}
    )
    app._snapshot = InspectSnapshot.from_full_response(response, fetcher=app._inspect_api)
    rest.fail_get = True
    assert app.maintenance_bookings == []
    assert app.validate_maintenance_booking(_spec()) == {}


def test_edge_targets_and_local_module_keys_resolve(booking: dict[str, Any]) -> None:
    app, rest = _app([booking])
    record = app._snapshot.get_device_record("device-a")
    module = record.node.modules.pop("device-a.dev.0")
    record.node.modules["module-local-key"] = module
    endpoint = deepcopy(booking["ports"][0])
    rest.bookings[0].update(
        devices=[], modules=[], ports=[], edges=[{"id": "edge-a", "from": endpoint, "to": endpoint}]
    )
    status = endpoint | {"pid": endpoint["context"]["portPid"]}
    pair = InspectApiExternalEdgesByDeviceKeyItem.model_validate(
        {
            "_id": "device-a::device-b",
            "_vid": "pair-a",
            "primary": {
                "devicePid": "device-a",
                "data": {"edge-a": {"id": "edge-a", "fromStatus": status, "toStatus": status}},
            },
            "secondary": {"devicePid": "device-b", "data": {}},
        }
    )
    app._snapshot = InspectSnapshot(
        fetcher=app._inspect_api, device_items=[record.node], edge_items=[pair], device_level=HydrationLevel.FULL
    )
    item = app.maintenance_bookings[0]
    edge = item.edges[0]
    assert MaintenanceTargets(edges=[edge, "edge-a"]).edges == ["edge-a"]
    assert [b.id for b in edge.maintenance_bookings] == [item.id]
    device = app._snapshot.get_device("device-a")
    assert [b.id for b in device.maintenance_bookings] == [item.id]
    assert [b.id for b in device.modules[0].maintenance_bookings] == [item.id]
    assert [b.id for b in device.ports[0].maintenance_bookings] == [item.id]
    assert rest.get_calls == [queries.maintenance_section()]


def test_result_uses_server_detail_ids_and_never_guesses() -> None:
    app, rest = _app([])
    assert app.create_maintenance_booking(_spec()).details == {}
    rest.details = {"server-booking-a": {"rev": "revision-a", "isCancel": False, "status": 0, "type": "generic"}}
    result = app.create_maintenance_booking(_spec())
    assert list(result.details) == ["server-booking-a"]
    assert result.details["server-booking-a"].rev == "revision-a"


def test_create_update_delete_payloads_and_revision(booking: dict[str, Any]) -> None:
    booking["generic"]["locked"] = True
    app, rest = _app([booking])
    spec = _spec()
    assert app.create_maintenance_booking(spec).ok
    create = rest.posts[-1][1]["data"]
    assert create["update"] == [] and create["delete"] == []
    definition = create["create"][0]["serviceDefinition"]
    assert definition["devicePids"] == ["device-a"] and "pids" not in definition
    assert app.update_maintenance_booking("booking-a", spec, expected_rev="revision-a").ok
    update = rest.posts[-1][1]["data"]["update"][0]
    assert update["id"] == "booking-a" and update["rev"] == "revision-a"
    assert update["inheritable"]["locked"] is True
    assert update["updater"]["pids"] == ["device-a"] and "devicePids" not in update["updater"]
    assert app.update_maintenance_booking("booking-a", spec, locked=False).ok
    assert not rest.posts[-1][1]["data"]["update"][0]["inheritable"]["locked"]
    assert app.delete_maintenance_bookings(["booking-a", "booking-a"]).ok
    assert rest.posts[-1][1]["data"] == {"create": [], "update": [], "delete": ["booking-a"]}
    assert all(p.endswith("/updateMaintenance") for p, _ in rest.posts)


def test_update_uses_fresh_revision_over_cached_booking(booking: dict[str, Any]) -> None:
    app, rest = _app([booking])
    assert app.maintenance_bookings[0].rev == "revision-a"
    rest.bookings[0]["rev"] = "revision-b"
    rest.bookings[0]["generic"]["locked"] = True
    app.update_maintenance_booking("booking-a", _spec())
    update = rest.posts[-1][1]["data"]["update"][0]
    assert update["rev"] == "revision-b" and update["inheritable"]["locked"]


@pytest.mark.parametrize("action", ["nothing", "invalidate", "reroute", "rerouteSA"])
def test_action_settings_are_serialized(action: str) -> None:
    app, rest = _app([])
    app.create_maintenance_booking(
        _spec(action=action, trigger="active", allow_overlap=True, switch_format_state_on_reroute=True)
    )
    definition = rest.posts[-1][1]["data"]["create"][0]["serviceDefinition"]
    assert definition["action"] == action and definition["trigger"] == "active"
    assert definition["allowOverlap"] and definition["switchFormatStateOnReroute"]


def test_missing_or_conflicting_update_does_not_write(booking: dict[str, Any]) -> None:
    app, rest = _app([booking])
    with pytest.raises(InspectEntityNotFoundError):
        app.update_maintenance_booking("absent", _spec())
    with pytest.raises(InspectMaintenanceConflictError) as caught:
        app.update_maintenance_booking("booking-a", _spec(), expected_rev="old")
    assert caught.value.actual_rev == "revision-a"
    assert rest.posts == []


def test_write_revalidates_nested_lists_without_io() -> None:
    app, rest = _app([])
    spec = _spec()
    spec.targets.devices.clear()
    with pytest.raises(ValidationError):
        app.create_maintenance_booking(spec)
    assert not rest.posts and not rest.get_calls


def test_recurring_update_requires_explicit_one_time_window(booking: dict[str, Any]) -> None:
    app, rest = _app([booking])
    with pytest.raises(ValueError, match="one-time schedule"):
        app.update_maintenance_booking("booking-a", _spec(schedule=_recurring()))
    assert not rest.posts and not rest.get_calls


def test_success_invalidates_without_losing_staged_edits_or_result(booking: dict[str, Any]) -> None:
    app, rest = _app([booking])
    held = app.maintenance_bookings[0]
    snapshot = app._snapshot
    snapshot.stage_edit("device", "device-a", "descriptor.label", "pending")
    rest.fail_get = True
    assert app.create_maintenance_booking(_spec()).ok  # Invalidation performs no I/O.
    assert snapshot.get_staged_edits("device", "device-a") == {"descriptor.label": "pending"}
    assert "device-a" in snapshot._stale_devices
    assert not snapshot._section_loaded["maintenance"]
    with pytest.raises(InspectMaintenanceError):
        _ = held.label
    rest.fail_get = False
    rest.bookings[0]["generic"]["descriptor"]["label"] = "updated"
    assert held.label == "updated"


@pytest.mark.parametrize("failure", ["result", "header", "malformed", "timeout"])
def test_failed_writes_are_typed_and_never_retried(booking: dict[str, Any], failure: str) -> None:
    app, rest = _app([booking])
    _ = app.maintenance_bookings
    rest.failure = failure
    with pytest.raises(InspectMaintenanceError) as caught:
        app.create_maintenance_booking(_spec())
    assert caught.value.operation == "create"
    assert len(rest.posts) == 1
    assert app._snapshot._section_loaded["maintenance"]


def test_preview_and_current_impact_are_read_only(booking: dict[str, Any]) -> None:
    app, rest = _app([booking])
    rest.impact = {
        "service-a": {
            "label": "service-a",
            "start": 0,
            "end": 1000,
            "protection": "none",
            "maxSaBefore": 0,
            "maxSaAfter": 2,
            "entries": [
                {
                    "start": 0,
                    "end": 1000,
                    "saBefore": 0,
                    "saAfter": 2,
                    "contributors": {"booking-a": {"label": "maintenance-a"}},
                }
            ],
        }
    }
    impact = app.validate_maintenance_booking(_spec(), booking_id="booking-a")
    assert impact["service-a"][0].entries[0].contributors["booking-a"].label == "maintenance-a"
    assert rest.posts[-1][1]["data"]["id"] == "booking-a"
    assert app.get_maintenance_impact(["booking-a"])["booking-a"]["service-a"].maxSaAfter == 2
    assert all("updateMaintenance" not in path for path, _ in rest.posts)
    assert rest.get_calls == []


@pytest.mark.parametrize("ids", [[], [""], [" a "], "booking-a"])
def test_invalid_booking_ids(ids: Any) -> None:
    app, rest = _app([])
    with pytest.raises(ValueError):
        app.delete_maintenance_bookings(ids)
    with pytest.raises(ValueError):
        app.get_maintenance_impact(ids)
    assert rest.posts == []


def test_exact_connector_allowlist() -> None:
    connector = object.__new__(VideoIPathRestConnector)
    for action in ("updateMaintenance", "fetchMaintenanceImpact", "validateMaintenanceImpactDetailed"):
        connector._validate_url(f"/rest/v2/actions/status/pathman/{action}", "POST")
    with pytest.raises(ValueError):
        connector._validate_url("/rest/v2/actions/status/pathman/unrelatedAction", "POST")


def _recurring(**changes: Any) -> MaintenanceRecurringSchedule:
    return MaintenanceRecurringSchedule(
        **(
            {
                "frequency": "daily",
                "start": START,
                "end": START + timedelta(days=31),
                "timezone": "Europe/Berlin",
                "local_start": time(1),
                "local_end": time(2),
            }
            | changes
        )
    )


def _spec(**changes: Any) -> MaintenanceBookingSpec:
    return MaintenanceBookingSpec(
        **(
            {
                "label": "maintenance-a",
                "targets": MaintenanceTargets(devices=["device-a"]),
                "schedule": MaintenanceOnceSchedule(start=START, end=START + timedelta(days=1)),
            }
            | changes
        )
    )


def _header(**changes: Any) -> InspectApiRestV2Header:
    return InspectApiRestV2Header(
        **(
            {"auth": True, "caption": "OK", "code": "OK", "id": "0", "msg": [], "ok": True, "user": "test-user"}
            | changes
        )
    )


def _snapshot(fetcher: InspectAPI | None = None) -> InspectSnapshot:
    node = InspectApiNodeStatusItem.model_validate(
        {
            "_id": "device-a",
            "_vid": "1",
            "deviceId": "device-a",
            "pid": "device-a",
            "context": {"devicePid": "device-a"},
            "modules": {
                "device-a.dev.0": {
                    "pid": "device-a.dev.0",
                    "context": {"devicePid": "device-a", "modulePid": "device-a.dev.0"},
                    "ports": {"device-a.dev.0.port-out-1": {"pid": "device-a.dev.0.port-out-1"}},
                }
            },
        }
    )
    return InspectSnapshot(fetcher=fetcher, device_items=[node], device_level=HydrationLevel.FULL)


def _app(bookings: list[dict[str, Any]]) -> tuple[InspectApp, FakeRest]:
    rest = FakeRest(bookings)
    with pytest.warns(UserWarning, match="beta"):
        app = InspectApp(SimpleNamespace(rest=rest, videoipath_version="2026.2.0"))
    app._snapshot = _snapshot(app._inspect_api)
    return app, rest


class FakeRest:
    def __init__(self, bookings: list[dict[str, Any]]) -> None:
        self.bookings = deepcopy(bookings)
        self.get_calls: list[str] = []
        self.posts: list[tuple[str, dict[str, Any]]] = []
        self.fail_get = False
        self.failure: str | None = None
        self.impact: dict[str, Any] = {}
        self.details: dict[str, Any] = {}

    def get(self, path: str, **kwargs: Any) -> SimpleNamespace:
        self.get_calls.append(path)
        if self.fail_get:
            raise ConnectionError("test read failed")
        assert path == queries.maintenance_section()
        return SimpleNamespace(
            header=_header(), data={"status": {"collector": {"maintenanceBookings": {"_items": self.bookings}}}}
        )

    def post(self, path: str, body: Any) -> SimpleNamespace:
        self.posts.append((path, body.model_dump(mode="json", by_alias=True)))
        if self.failure == "timeout":
            raise TimeoutError("test timeout")
        data: Any = {"result": {"ok": self.failure != "result", "msg": ["test response"]}, "details": self.details}
        if self.failure == "malformed":
            data = {}
        elif path.endswith("validateMaintenanceImpactDetailed"):
            data = self.impact
        elif path.endswith("fetchMaintenanceImpact"):
            data = {"booking-a": self.impact}
        return SimpleNamespace(header=_header(ok=self.failure != "header"), data=data)
