"""Scoped collector query catalogue for the Inspect app.

Every query string here is **verified live against VideoIPath 2025.4.9** and is the
concrete basis for the skeleton-first + lazy-hydration loading model ([ADR-0007]).
The Inspect UI issues the same paths over WebSocket subscriptions; the package
issues them as REST GETs (see docs/architecture/inspect-app/endpoints.md).

Projection grammar used below (verified):
- ``*``            select all items of a collection
- ``"_noId"``      suppress a sub-tree (returns ``{}`` / omits the key)
- ``field/**``     select a field's full sub-tree
- ``a,b``          select several leaf fields at the current level
- ``/.../``        pop one level back up in the projection tree

The full UI projection is too long for a REST GET (HTTP 414); the skeleton
projections here are deliberately trimmed to stay well within the URI limit.
"""

from __future__ import annotations

import urllib.parse

from videoipath_automation_tool.apps.inspect.errors import InspectQueryTooLongError

# Base for all collector data reads.
_DATA = "/rest/v2/data"

# Conservative URI length ceiling (path only). Verified queries are ~200-370 chars;
# the full UI projection (thousands of chars) triggers HTTP 414 behind the proxy.
MAX_QUERY_LENGTH = 4000


def encode(path: str) -> str:
    """Percent-encode a collector query path, preserving projection-grammar characters."""
    return urllib.parse.quote(path, safe=_SAFE)


def device_skeleton() -> str:
    """GET path for the device skeleton (all devices, no module/port detail)."""
    return _build(_DEVICE_SKELETON)


def device_detail(device_id: str) -> str:
    """GET path for one device's full nodeStatus sub-tree (modules, ports, vertexInfo, ...)."""
    return _build(f"/status/collector/inspect/nodeStatus/{device_id}/**")


def edge_skeleton() -> str:
    """GET path for the lean edge skeleton (all device pairs, connectivity + status severities)."""
    return _build(_EDGE_SKELETON)


def edge_pair(pair_id: str) -> str:
    """GET path for a single external-edge device pair (targeted refresh, [ADR-0010])."""
    return _build(f"/status/collector/externalEdgesByDeviceKey/{pair_id}" + _EDGE_LEAN_TAIL)


def paths_section() -> str:
    """GET path for the services/paths section."""
    return _build(_PATHS_SECTION)


def alarms_section() -> str:
    """GET path for the current-alarms section (``status/alarms/current``)."""
    return _build(_ALARMS_SECTION)


def collector_full() -> str:
    """GET path for the full collector aggregate (eager / fallback mode)."""
    return _build(_COLLECTOR_FULL)


def virtual_templates() -> str:
    """GET path for all port templates (``status/network/virtualTemplates``)."""
    return _build(_VIRTUAL_TEMPLATES)


def virtual_devices() -> str:
    """GET path for all virtual device definitions (``status/network/virtualDevices``)."""
    return _build(_VIRTUAL_DEVICES)


# --- Internal ---

# Characters that are meaningful in the projection grammar and must survive encoding.
# Everything else (spaces, double quotes, ...) is percent-encoded.
_SAFE = "/*,'=()"

# Device skeleton: identity + descriptor + meta (incl. coordinates) + status + syncSeverity
# + tags, with the module sub-tree suppressed ("_noId"). ~200 char URL, ~30 KB / 30 devices.
_DEVICE_SKELETON = (
    "/status/collector/inspect/nodeStatus/*"
    "/deviceId,resourceId,syncSeverity"
    "/.../descriptor/**"
    "/.../.../meta/**"
    "/.../.../status/**"
    "/.../.../tags/*"
    '/.../.../modules/"_noId"'
)

# Edge skeleton (lean): device-pair keys, edge ids, endpoint port context+labels, and the
# pair-level status severities. No pathDescriptions, no bandwidth values. ~370 char URL.
_EDGE_LEAN_TAIL = (
    "/primary,secondary/devicePid,label"
    "/.../.../status/alarm,bandwidth,maintenance,ptp"
    "/.../.../primary/data/*/id"
    "/.../fromStatus,toStatus/label"
    "/.../context/devicePid,modulePid,portPid"
    "/.../.../.../.../.../.../secondary/data/*/id"
    "/.../fromStatus,toStatus/label"
    "/.../context/devicePid,modulePid,portPid"
)
_EDGE_SKELETON = "/status/collector/externalEdgesByDeviceKey/*" + _EDGE_LEAN_TAIL

# Services / paths section: serviceFields (endpoints, labels, status) + per-hop path structure.
_PATHS_SECTION = (
    "/status/collector/inspect/paths/*"
    "/serviceFields/bid,from,fromLabel,isMain,to,toLabel"
    "/.../generic/descriptor/**"
    "/.../.../serviceStatus/**"
    "/.../.../.../path/*/bid,ipDesc"
    "/.../structure/deviceId,deviceLabel,devicePid"
    "/.../inputStatus,outputStatus/label,pid"
)

# Current alarms: lean projection of identity, acknowledgement, point labels, and severity/message.
# Verified 2026.2.0: two `/.../` pops after each selected sub-tree (same grammar as the collector
# skeleton); three pops omit ``info``.
_ALARMS_SECTION = (
    "/status/alarms/current/*"
    "/acked,hidden"
    "/.../id/**"
    "/.../.../desc/**"
    "/.../.../info/details,severity,sa,headSeverity,time"
)

# Full aggregate (eager / fallback mode).
_COLLECTOR_FULL = "/status/collector/**"

# Virtual device / port-template definitions (network status, not collector).
_VIRTUAL_TEMPLATES = "/status/network/virtualTemplates/**"
_VIRTUAL_DEVICES = "/status/network/virtualDevices/**"


def _build(path: str) -> str:
    encoded = encode(_DATA + path)
    if len(encoded) > MAX_QUERY_LENGTH:
        raise InspectQueryTooLongError(len(encoded), MAX_QUERY_LENGTH)
    return encoded


__all__ = [
    "MAX_QUERY_LENGTH",
    "encode",
    "device_skeleton",
    "device_detail",
    "edge_skeleton",
    "edge_pair",
    "paths_section",
    "alarms_section",
    "collector_full",
    "virtual_templates",
    "virtual_devices",
]
