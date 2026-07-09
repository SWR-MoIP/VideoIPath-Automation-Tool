# Inspect App Endpoint Reference

Captured against a local VideoIPath test instance. All hostnames, usernames,
device IDs, booking IDs, labels, endpoint IDs, IP addresses, multicast
addresses, UUIDs, and revisions in this document are anonymized examples. Only
read-only requests and one empty no-op `updateTopology` POST were executed.

The Inspect package scope follows the accepted ADRs:

- Request/response only; no WebSocket subscription API. Subscription *captures*
  are still used as an endpoint-discovery source — see
  [Collector Scoped Queries](#collector-scoped-queries-captured-from-the-inspect-ui).
- Snapshot-scoped reads: a snapshot loads a skeleton first and lazily hydrates
  detail; fresh status means building a new snapshot
  ([ADR-0007](./decisions/0007-lazy-snapshot-loading.md)).
- Data-only DTOs; write/commit behaviour belongs in the future app/transaction
  layer, not in the model classes.

## Common Envelope

All observed REST v2 responses use the standard envelope:

```json
{
  "data": {},
  "header": {
    "auth": true,
    "caption": "Operation Successful",
    "code": "OK",
    "errorCodes": [],
    "errorDetails": [],
    "id": "",
    "msg": [],
    "ok": true,
    "user": "api-user"
  }
}
```

`header.ok` only describes transport/envelope success. For `updateTopology`,
commit success must also check `data.res.ok` and
`data.validation.result.ok`.

## `GET /rest/v2/data/status/system/about/version`

Purpose: identify the server version used for endpoint and payload capture.

Request:

```http
GET /rest/v2/data/status/system/about/version
Authorization: Basic <credentials>
Accept: application/json
```

Response example:

```json
{
  "data": {
    "status": {
      "system": {
        "about": {
          "version": "2025.4.x"
        }
      }
    }
  },
  "header": {
    "auth": true,
    "caption": "Operation Successful",
    "code": "OK",
    "errorCodes": [],
    "errorDetails": [],
    "id": "",
    "msg": [],
    "ok": true,
    "user": "api-user"
  }
}
```

## `GET /rest/v2/data/status/collector/**`

Purpose: full Inspect read aggregate — services, path drill-down, external edge
status, and topology node status in one response.

> Since [ADR-0007](./decisions/0007-lazy-snapshot-loading.md) this full fetch is
> the **eager/fallback mode** only. The default read path uses the scoped
> queries documented in
> [Collector Scoped Queries](#collector-scoped-queries-captured-from-the-inspect-ui),
> which is also how the vendor's Inspect UI loads its data.

Observed top-level sections:

- `inspect.nodeStatus`
- `inspect.paths`
- `externalEdgesByDeviceKey`
- `maintenanceBookings`
- `superProfiles`
- `tagInfo`

`security/**` returned an empty `collector` object on this instance.

Request:

```http
GET /rest/v2/data/status/collector/**
Authorization: Basic <credentials>
Accept: application/json
```

Response shape example:

```json
{
  "data": {
    "status": {
      "collector": {
        "externalEdgesByDeviceKey": { "_items": [] },
        "inspect": {
          "nodeStatus": { "_items": [] },
          "paths": { "_items": [] }
        },
        "maintenanceBookings": { "_items": [] },
        "superProfiles": { "_items": [] },
        "tagInfo": { "_items": [] }
      }
    }
  },
  "header": {
    "auth": true,
    "caption": "Operation Successful",
    "code": "OK",
    "errorCodes": [],
    "errorDetails": [],
    "id": "",
    "msg": [],
    "ok": true,
    "user": "api-user"
  }
}
```

## Collector Scoped Queries (captured from the Inspect UI)

Source: a browser WebSocket capture of the Inspect app's **initial load**
(2026-07-08, VideoIPath 2025.4.x test instance, 27 devices / 40 edge pairs).
The UI never fetches `/status/collector/**`. It opens ~8 **parallel scoped
subscriptions**, each addressing a collector sub-path with a filter and a deep
field projection. These queries are the concrete basis for the skeleton +
lazy-hydration loading model ([ADR-0007](./decisions/0007-lazy-snapshot-loading.md)).

All ids, labels, and addresses below are anonymized. Decoded paths are shown
with URL encoding removed (`%20` → space, `%22` → `"`, `%2C` → `,`,
`%3D` → `=`, `%3C` → `<`).

### Observed subscription transport (reference only — out of package scope)

Each subscription is one WebSocket message; the `path` addresses the same data
tree as REST v2:

```json
{"channel": "subsc", "messageId": 14, "path": "/status/collector/externalEdgesByDeviceKey/<url-encoded query>", "id": "<uuid>"}
```

The initial reply carries the full query result; the `data` object mirrors the
REST v2 `data` tree exactly (`_items[]`, `_id`, `_vid`):

```json
{"channel": "subsc", "id": "<uuid>", "messageId": 14, "payload": {"_id": "<uuid>", "_ver": [1, 1], "data": {"status": {"collector": {"externalEdgesByDeviceKey": {"_items": ["..."]}}}}}}
```

Protocol details (verified by live connection and the UI bundle on 2025.4.9):

| Item | Value |
| ---- | ----- |
| URL | `{ws\|wss}://<host>/rest/v2/sessions/me/ws?exclusive=false` |
| Auth | Session cookies on the WebSocket handshake (same as REST) |
| Subscribe | `{"channel":"subsc","messageId":N,"path":"<url-encoded query>","id":"<uuid>"}` |
| Initial reply | `{"channel":"subsc","id":"…","messageId":N,"payload":{"_id":"…","_ver":[1,1],"data":{…}}}` |
| Unsubscribe | `{"channel":"unsubsc","messageId":N,"id":"<subscription-uuid>"}` |
| Delta frames | `payload.data._e` (observed in the UI decoder) |
| Reconnect | UI re-opens when the socket is gone and the tab is visible; no dedicated heartbeat channel |

The package stays request/response ([ADR-0001](./decisions/0001-api-paradigm.md),
[ADR-0003](./decisions/0003-websocket-subscriptions.md)): the same query paths
work as `GET /rest/v2/data<decoded path>`. **Confirmed** on VideoIPath 2025.4.9
for practical query lengths; URL encoding of spaces (`%20`), quotes (`%22`),
parentheses (`%28`/`%29`), and `=` (`%3D`) works as captured. The **full** UI
projection below returns **HTTP 414** (URI Too Long) as a REST GET — a
proxy/URL-length constraint, not a server bug — so the package uses a trimmed
skeleton projection or the `/**` fallback.

Measured payload sizes (2025.4.9 instance, 30 devices / 40 edge pairs):

| Query | Size |
| ----- | ---- |
| `GET …/status/collector/**` (eager fallback) | **19.3 MB** |
| Trimmed device skeleton + edge skeleton | **~92 KB** |
| Minimal `nodeStatus` projection with `"_noId"` (all 30 devices) | **8 KB** |
| Single device `/**` (hydration) | **21 KB** |

### Query language observed on collector paths

| Construct | Example | Meaning |
| --------- | ------- | ------- |
| `*` | `nodeStatus/*` | Select all items of a collection |
| `"<id>"` | `fromStatus/generic/alias/"a0"` | Select one child by literal key |
| `"_noId"` | `modules/"_noId"` | Subtree expansion suppressor — collection queries return `"modules": {}`; single-device queries omit the `modules` key. Also used on `inspect/paths/"_noId"/…` |
| `* where <expr>` | `* where syncSeverity=2` | Filter items; operators seen: `=`, `<=`, `and`, `or`, parentheses, `contains(<field>,'<str>')`, `lower(<field>)` |
| `limit N` | `* where … limit 1000000` | Cap the number of returned items (UI uses `1000` for side lists, `1000000` for the full topology) |
| `order by <field> asc(en) alphanum` | `panelConfigs/* order by label asc(en) alphanum` | Server-side sort (seen outside the collector) |
| `/field1,field2/` | `/deviceId,resourceId/` | Project only the listed fields at the current level |
| `/.../` | `…/coordinates/x,y/.../...` | Pop one level back up in the projection tree |
| `/**` | `status,syncSeverity/**` | Include the full subtree below the selected fields |
| *(no projection)* | `externalEdgesByDeviceKey` | **No expansion**: the bare collection root returns no items (observed, msg 15) |

### Device skeleton — `nodeStatus` without modules (UI main topology load)

The UI's primary topology query. Note `modules/"_noId"`: **the vendor UI itself
loads devices without module/port detail**. All 27 captured items came back
with `modules: {}`.

Decoded subscription path (one line, msg 13):

```text
/status/collector/inspect/nodeStatus/* where ((syncSeverity=0) or (syncSeverity=1)) or (syncSeverity=3) limit 1000000/deviceId,resourceId/.../context/devicePid,modulePid,portPid/.../.../descriptor/desc,label/.../.../meta/hwPanelType,isCore,isVirtual,siteId/.../coordinates/x,y/.../.../iconSize,iconType,sdpStrategy/**/.../.../tags/*/.../.../.../relatedNodeTags/*/.../.../status,syncSeverity/**/.../.../tags/*/.../.../modules/"_noId"/resourceId/.../context/devicePid,modulePid,portPid/.../.../descriptor/desc,label/.../.../ptpStatus,status/**/.../.../relatedNodeTags/*/.../.../tags/*/.../.../ports/*/pid,resourceId/.../context/devicePid,modulePid,portPid/.../.../descriptor/desc,label/.../.../relatedNodeTags/*/.../.../status/**/.../.../tags/*/.../.../vertexInfo/id,type,vertexType/.../fields/isActive,isControlled,isEndpoint/.../.../in,out/id,label/.../.../.../ptpPortStatus/info/clockType,domain,identity/.../.../status/**/.../.../.../tagsInfo/assigned/inheritedConflict/.../all/*/.../.../inherited/*/label/.../ancestors/*/.../.../path/*/.../.../.../.../local/*/label/.../path/*/.../.../.../.../.../custom/*/.../.../.../pathDescriptions/*/deviceLevel/deviceId,deviceLabel,devicePid,expectConfig/.../inputStatus,outputStatus/label,pid/.../context/devicePid,modulePid,portPid/.../.../status/**/.../.../.../moduleAndDeviceStatus/**/.../.../.../serviceLevel/bookingId,isMain,serviceLabel/.../fromStatus,toStatus/label,pid/.../context/devicePid,modulePid,portPid/.../.../status/**/.../.../.../serviceStatus/config,total/**/.../.../.../.../.../.../.../.../tagsInfo/assigned/inheritedConflict/.../all/*/.../.../inherited/*/label/.../ancestors/*/.../.../path/*/.../.../.../.../local/*/label/.../path/*/.../.../.../.../.../custom/*/.../.../.../.../.../ptpDeviceStatus/info/clockType,domain,identity/.../.../status/**/.../.../.../tagsInfo/assigned/inheritedConflict/.../all/*/.../.../inherited/*/label/.../ancestors/*/.../.../path/*/.../.../.../.../local/*/label/.../path/*/.../.../.../.../.../custom/*
```

Effective skeleton selection per device (the module subtree is projected in
full but suppressed by `"_noId"`):

- identity: `deviceId`, `resourceId`, `context{devicePid,modulePid,portPid}`
- display: `descriptor{desc,label}`,
  `meta{hwPanelType,isCore,isVirtual,siteId,coordinates{x,y},iconSize,iconType,sdpStrategy,tags}`
- state: `status/**`, `syncSeverity`, `ptpDeviceStatus{info,status}`
- tagging: `tags`, `relatedNodeTags`, `tagsInfo{assigned,custom}`

The UI splits `nodeStatus` by sync state into three subscriptions with the same
projection: this one (`syncSeverity` 0/1/3, topology map), a sync-pending list
(msg 9, below), and a label-search variant
(`* where (syncSeverity=3) and (contains(lower(descriptor.label),'')) limit 1000`,
msg 10). A package skeleton load can drop the `where` clause and fetch all
devices in one query. **Confirmed:** omitting `where` does **not** require
`limit` (30 devices returned with or without `limit 1000000` on 2025.4.9).

Anonymized response item (skeleton shape — note `modules: {}`):

```json
{
  "_id": "device-a",
  "_vid": "device-a",
  "context": { "devicePid": "device-a", "modulePid": null, "portPid": null },
  "descriptor": {
    "desc": "Type: example_multidevice\nIP: <device-ip>",
    "label": "Example Device A"
  },
  "deviceId": "device-a",
  "meta": {
    "coordinates": { "x": 1600.0, "y": 9050.0 },
    "hwPanelType": null,
    "iconSize": "medium",
    "iconType": "default",
    "isCore": false,
    "isVirtual": false,
    "sdpStrategy": "always",
    "siteId": null,
    "tags": []
  },
  "modules": {},
  "ptpDeviceStatus": {
    "info": null,
    "status": { "sa": 2, "severity": 6 }
  },
  "relatedNodeTags": ["Format~~example"],
  "resourceId": "device:device-a",
  "status": { "sa": 2, "severity": 6 },
  "syncSeverity": 0,
  "tags": [],
  "tagsInfo": {
    "assigned": { "all": [], "inherited": {}, "inheritedConflict": false, "local": {} },
    "custom": []
  }
}
```

### Device detail — `nodeStatus` with `modules/*` (hydration template)

The sync-pending subscription (msg 9) is **byte-identical** to the skeleton
query except for two segments:

```text
- * where ((syncSeverity=0) or (syncSeverity=1)) or (syncSeverity=3) limit 1000000
+ * where syncSeverity=2 limit 1000
- modules/"_noId"
+ modules/*
```

With `modules/*` the projection expands modules → ports → `vertexInfo`,
`ptpPortStatus`, per-port `status/**`, `tagsInfo`, and `pathDescriptions`
(`deviceLevel` + `serviceLevel`) — the full drill-down detail.

This is the template for **per-device lazy hydration**
([ADR-0007](./decisions/0007-lazy-snapshot-loading.md)): reuse the detail
projection but scope it to one device. **Confirmed** on 2025.4.9 — both work;
prefer the shorter direct-id form:

```http
GET /rest/v2/data/status/collector/inspect/nodeStatus/<device-id>/modules/*/…
GET /rest/v2/data/status/collector/inspect/nodeStatus/* where deviceId='<device-id>' limit 1/modules/*/…
```

**Confirmed** populated `modules/*` on synced devices (`syncSeverity` 0/1/3):
module keys map to child objects whose expansion follows the projection depth
(e.g. `…/modules/*/ports/*/pid,descriptor/label,status` yields ports with
`pid`, `descriptor.label`, and `status`). Devices with `syncSeverity=2`
(sync-pending) return `"modules": {}` even with `modules/*` — modules populate
only after sync completes; the earlier capture was not a projection bug.
`GET …/nodeStatus/<device-id>/**` returns the full subtree (~21 KB for one
device) — fixture:
`tests/fixtures/inspect/2025.4.9/device_hydration_modules_ports.json`.

### Edge skeleton — `externalEdgesByDeviceKey` lean projection

The UI loads **all** edge pairs with a lean projection (msg 14): endpoint
device pids/labels, edge ids, endpoint port labels + `context`, and the
pair-level status severities — **no `pathDescriptions`, no bandwidth numbers**
(only the `bandwidth` *severity* inside `status`).

Decoded subscription path (one line, msg 14):

```text
/status/collector/externalEdgesByDeviceKey/* limit 1000000/primary,secondary/devicePid,label/.../.../status/alarm,bandwidth,maintenance,ptp/.../.../primary/data/*/id/.../fromStatus,toStatus/label/.../context/devicePid,modulePid,portPid/.../.../.../.../.../.../secondary/data/*/id/.../fromStatus,toStatus/label/.../context/devicePid,modulePid,portPid
```

Anonymized response item:

```json
{
  "_id": "device-a::device-b",
  "_vid": "device-a::device-b",
  "primary": {
    "data": {
      "edge-uuid-0001": {
        "id": "edge-uuid-0001",
        "fromStatus": {
          "context": {
            "devicePid": "device-a",
            "modulePid": "device-a.dev.module-1",
            "portPid": "device-a.dev.module-1.port-out-1"
          },
          "label": "Port A (out)"
        },
        "toStatus": {
          "context": {
            "devicePid": "device-b",
            "modulePid": "device-b.dev.module-1",
            "portPid": "device-b.dev.module-1.port-in-1"
          },
          "label": "Port B (in)"
        }
      }
    },
    "devicePid": "device-a",
    "label": "Example Device A"
  },
  "secondary": {
    "data": {},
    "devicePid": "device-b",
    "label": "Example Device B"
  },
  "status": { "alarm": 1, "bandwidth": null, "maintenance": null, "ptp": 1 }
}
```

A parallel subscription to the **bare collection root**
(`/status/collector/externalEdgesByDeviceKey`, msg 15) returned `_items: []`
while the projected query returned 40 items — without a projection or `/**`
there is no expansion. Edge detail (bandwidth values, `pathDescriptions`) stays
in the full per-pair shape documented under
[`GET …/externalEdgesByDeviceKey/**`](#get-restv2datastatuscollectorexternaledgesbydevicekey).

### Service list — `inspect/paths` projection

The UI subscribes to `inspect/paths` with a projection covering `serviceFields`
and the per-hop `path` structure (msg 12; the capture returned no items — no
active services at capture time; the item shape is documented under
[`GET …/inspect/paths/**`](#get-restv2datastatuscollectorinspectpaths)):

```text
/status/collector/inspect/paths/"_noId"/serviceFields/bid,from,fromLabel,isMain,to,toLabel/.../fromStatus,toStatus/**/.../.../generic/descriptor/desc,label/.../.../.../serviceStatus/config,total/**/.../.../.../.../path/*/bid,ipDesc/.../structure/deviceId,deviceLabel,devicePid,expectConfig/.../inputStatus,outputStatus/label,pid/.../context/devicePid,modulePid,portPid/.../.../status/**/.../.../.../moduleAndDeviceStatus/**
```

Selected: `serviceFields{bid,from,fromLabel,isMain,to,toLabel,fromStatus,
toStatus,generic.descriptor,serviceStatus{config,total}}` plus
`path[]{bid,ipDesc,structure{deviceId,deviceLabel,devicePid,expectConfig,
inputStatus,outputStatus,moduleAndDeviceStatus}}` — everything the snapshot's
service index needs, without the full raw records.

### Auxiliary section queries

Also part of the UI's initial load (initial replies at capture time in
parentheses):

| Sub-path (decoded) | Purpose | msg |
| ------------------ | ------- | --- |
| `/status/collector/maintenanceBookings/* where ((contains(lower(generic.descriptor.label),'')) or (contains(tags,''))) and (generic.state<=1)/<projection: action, allowOverlap, rev, trigger, generic, scheduleInfo, tags, devices, edges, modules, ports>` | Active maintenance bookings (empty) | 16 |
| `/status/collector/superProfiles` *(projection not captured; reply held profile records)* | Routing profiles (populated) | 3 |
| `/status/collector/tagInfo` *(projection not captured; reply held `profileTags._items[]`)* | Tag → profile mappings (populated) | 4 |
| `/status/conman/services/"_noId" where connection.generic.state<=1/<large projection incl. children where child.connection.specific.type in (bundle, group, rec_group, connection)>` | Rich service list for the Services panel — **not** a collector path; reference only (empty) | 11 |
| `/status/system/about/copyright,gitHead,version` | Version probe | 17 |
| `/status/system/status/serverState/broadcastAddress,hostname,mode,role` | Server role/state | 19 |

## `GET /rest/v2/data/status/collector/inspect/paths/**`

Purpose: list service/path records with endpoint labels, service state, and
per-hop path structures.

Request:

```http
GET /rest/v2/data/status/collector/inspect/paths/**
Authorization: Basic <credentials>
Accept: application/json
```

Response item example:

```json
{
  "_id": "booking-1001::main",
  "_vid": "_:booking-1001::main",
  "serviceFields": {
    "bid": "booking-1001",
    "ctype": 2,
    "formatSubState": 0,
    "from": "topo:device-a.module-1.port-out-1",
    "fromLabel": "Source Endpoint A",
    "fromPid": "device-a.dev.module-1.port-out-1",
    "fromStatus": { "sa": 0, "severity": 1 },
    "generic": {
      "allocationState": 0,
      "cancelTime": null,
      "descriptor": {
        "desc": "",
        "label": "Source Endpoint A -> Destination Endpoint B"
      },
      "locked": false,
      "state": 1,
      "tags": []
    },
    "isMain": true,
    "serviceStatus": {
      "config": { "sa": 0, "severity": 1 },
      "total": { "sa": 0, "severity": 1 }
    },
    "to": "topo:device-b.module-2.port-in-1",
    "toLabel": "Destination Endpoint B",
    "toPid": "device-b.dev.module-2.port-in-1",
    "toStatus": { "sa": 0, "severity": 1 }
  },
  "path": [
    {
      "bid": "booking-1001",
      "ipDesc": "<multicast-address>:<port>",
      "structure": {
        "deviceId": "device-a",
        "deviceLabel": "Example Source Device",
        "devicePid": "device-a",
        "expectConfig": true,
        "inputStatus": {
          "context": {
            "devicePid": "device-a",
            "modulePid": "device-a.dev.module-1",
            "portPid": "device-a.dev.module-1.port-out-1"
          },
          "label": "Source Endpoint A",
          "pid": "device-a.dev.module-1.port-out-1",
          "status": { "sa": 0, "severity": 1 }
        },
        "moduleAndDeviceStatus": { "sa": 0, "severity": 1 },
        "outputStatus": {
          "context": {
            "devicePid": "device-a",
            "modulePid": "device-a.dev.network-module",
            "portPid": "device-a.dev.network-module.port-1"
          },
          "label": "Network Port A",
          "pid": "device-a.dev.network-module.port-1",
          "status": { "sa": 0, "severity": 1 }
        }
      }
    }
  ]
}
```

## `GET /rest/v2/data/status/collector/externalEdgesByDeviceKey/**`

Purpose: live inter-device link status grouped by device pair.

Request:

```http
GET /rest/v2/data/status/collector/externalEdgesByDeviceKey/**
Authorization: Basic <credentials>
Accept: application/json
```

Response item example:

```json
{
  "_id": "device-a::device-b",
  "_vid": "device-a::device-b",
  "status": {
    "alarm": 1,
    "bandwidth": null,
    "maintenance": null,
    "ptp": 1
  },
  "primary": {
    "devicePid": "device-a",
    "label": "Example Source Device",
    "data": {
      "edge-uuid-0001": {
        "bandwidth": 0.0,
        "fromStatus": {
          "context": {
            "devicePid": "device-a",
            "modulePid": "device-a.dev.module-1",
            "portPid": "device-a.dev.module-1.port-out-1"
          },
          "label": "Port A (out)",
          "pid": "device-a.dev.module-1.port-out-1",
          "status": { "sa": 0, "severity": 1 }
        },
        "id": "edge-uuid-0001",
        "maxBandwidth": null,
        "pathDescriptions": {},
        "ratio": 0.0,
        "status": {
          "alarm": 1,
          "bandwidth": null,
          "maintenance": null,
          "ptp": 1
        },
        "toStatus": {
          "context": {
            "devicePid": "device-b",
            "modulePid": "device-b.dev.module-1",
            "portPid": "device-b.dev.module-1.port-in-1"
          },
          "label": "Port B (in)",
          "pid": "device-b.dev.module-1.port-in-1",
          "status": { "sa": 0, "severity": 1 }
        }
      }
    }
  },
  "secondary": {
    "devicePid": "device-b",
    "label": "Example Destination Device",
    "data": {}
  }
}
```

## `GET /rest/v2/data/status/collector/inspect/nodeStatus/**`

Purpose: topology node/device status, including modules, ports,
`vertexInfo`, coordinates, statuses, and embedded path descriptions when the
server/user exposes them.

In the sanitized capture, the endpoint was valid but returned no items:

```json
{
  "data": {
    "status": {
      "collector": {
        "inspect": {
          "nodeStatus": {
            "_items": []
          }
        }
      }
    }
  },
  "header": {
    "auth": true,
    "caption": "Operation Successful",
    "code": "OK",
    "errorCodes": [],
    "errorDetails": [],
    "id": "",
    "msg": [],
    "ok": true,
    "user": "api-user"
  }
}
```

The model still includes `InspectApiNodeStatusItem` based on the accepted concept
document and the known Inspect UI payload shape.

## `GET /rest/v2/data/status/collector/maintenanceBookings/**`

Purpose: maintenance booking status relevant to Inspect service/link display.

Observed response on this instance:

```json
{
  "data": {
    "status": {
      "collector": {
        "maintenanceBookings": {
          "_items": []
        }
      }
    }
  }
}
```

## `GET /rest/v2/data/status/collector/superProfiles/**`

Purpose: routing/super-profile status data used by the Inspect aggregate.

Observed response on this instance:

```json
{
  "data": {
    "status": {
      "collector": {
        "superProfiles": {
          "_items": []
        }
      }
    }
  }
}
```

## `GET /rest/v2/data/status/collector/tagInfo/**`

Purpose: tag/profile metadata used by the Inspect aggregate.

Observed response on this instance:

```json
{
  "data": {
    "status": {
      "collector": {
        "tagInfo": {
          "_items": []
        }
      }
    }
  }
}
```

## `GET /rest/v2/data/status/network/edgesByDevice/**`

> **Reference only — not called by the package**
> ([ADR-0008](./decisions/0008-collector-only-endpoints.md)).

Purpose: existing status-plane edge view. This is not the collector facade, but
it is useful for cross-checking edge payload fields during discovery when
`config/network/nGraphElements` is unavailable or permission-filtered.

Request:

```http
GET /rest/v2/data/status/network/edgesByDevice/**
Authorization: Basic <credentials>
Accept: application/json
```

Response fragment:

```json
{
  "data": {
    "status": {
      "network": {
        "edgesByDevice": {
          "_items": [
            {
              "_id": "device-a",
              "_vid": "device-a",
              "edge-uuid-0001": {
                "active": true,
                "bandwidth": -1.0,
                "capacity": 65535,
                "conflictPri": 0,
                "descriptor": { "desc": "", "label": "" },
                "excludeFormats": [],
                "fromId": "device-a.module-1.port-out-1",
                "includeFormats": [],
                "redundancyMode": "Any",
                "tags": [],
                "toId": "device-b.module-1.port-in-1",
                "type": "unidirectionalEdge",
                "weight": 1,
                "weightFactors": {
                  "bandwidth": { "weight": 0 },
                  "service": { "max": 100, "weight": 0 }
                }
              }
            }
          ]
        }
      }
    }
  }
}
```

## `GET /rest/v2/data/config/network/nGraphElements/**`

> **Reference only — not called by the package**
> ([ADR-0008](./decisions/0008-collector-only-endpoints.md)). This is
> `app.topology`'s surface; it is documented here because `updateTopology`
> persists into it and the `replace*` payloads carry the persisted element
> shape. Its `_rev` is irrelevant to Inspect writes — `updateTopology` ignores
> revisions (last-writer-wins; see
> [ADR-0009](./decisions/0009-write-consistency.md)).

Purpose: revisioned config store that `updateTopology` persists into. Inspect
models include independent `InspectApi*` nGraph DTOs for this persisted shape, but
they do not import or subclass topology app models.

> **Vertex tags are not stored here.** Device-level tags appear on `baseDevice`
> items, but tag bindings on individual vertices live in
> `videoipath_docs.device_tags` (separate from the `ngraph` table). Inspect
> surfaces vertex tags via `lookupInspectVertexByIds` and hydrated port
> `tagsInfo` in `nodeStatus` — see
> [concepts.md §3.4](./concepts.md#34-tagging--device-vs-vertex-inspect-vs-topology).
> `app.topology` only knows the `nGraphElements` shape and therefore has no
> vertex-tag API.

In the sanitized capture, the endpoint was valid but returned no items:

```json
{
  "data": {
    "config": {
      "network": {
        "nGraphElements": {
          "_items": []
        }
      }
    }
  },
  "header": {
    "auth": true,
    "caption": "Operation Successful",
    "code": "OK",
    "errorCodes": [],
    "errorDetails": [],
    "id": "",
    "msg": [],
    "ok": true,
    "user": "api-user"
  }
}
```

Relevant type-filtered forms:

```http
GET /rest/v2/data/config/network/nGraphElements/* where type='baseDevice' /**
GET /rest/v2/data/config/network/nGraphElements/* where type='ipVertex' /**
GET /rest/v2/data/config/network/nGraphElements/* where type='codecVertex' /**
GET /rest/v2/data/config/network/nGraphElements/* where type='genericVertex' /**
GET /rest/v2/data/config/network/nGraphElements/* where type='unidirectionalEdge' /**
GET /rest/v2/data/config/network/nGraphElements/* where type='nGraphResourceTransform' /**
```

## Known Action Endpoints Needing Payload Capture

Manual endpoint discovery also identified the following Inspect-related action
endpoints. The examples below are anonymized and were captured with safe lookup
or no-op requests.

### `POST /rest/v2/actions/status/collector/lookupInspectEdgesByIds`

**Verified 2025.4.9.** The Inspect-surface source of an edge's **full persisted
form** — every field a `replaceEdges` payload needs (`weight`, `capacity`,
`bandwidth`, `redundancyMode`, `weightFactors`, `descriptor`, `fDescriptor`,
`tags`, `conflictPri`, `includeFormats`, `excludeFormats`). Batched by design.
This is the stage-time baseline read for compare-and-commit
([ADR-0009](./decisions/0009-write-consistency.md)). The UI bundle's edge edit
flow calls it with **both directions of a connection**
(`[edgeId, pairedEdgeId]`) before opening the dialog. **No `_rev` anywhere in
the response.**

> A `lookupGraphElement` action does **not** exist on 2025.4.9 (POST →
> `No action node in request`); earlier references to it were wrong.

Request:

```json
{
  "header": { "id": 0 },
  "data": ["device-a.module-1.port-out-1.out::device-b.module-1.port-in-1.in"]
}
```

Response (keyed by requested edge id):

```json
{
  "data": {
    "device-a.module-1.port-out-1.out::device-b.module-1.port-in-1.in": {
      "edge": {
        "active": true,
        "bandwidth": -1.0,
        "capacity": 65535,
        "conflictPri": 0,
        "descriptor": { "desc": "", "label": "" },
        "excludeFormats": [],
        "fDescriptor": { "desc": "", "label": "" },
        "fromId": "device-a.module-1.port-out-1.out",
        "includeFormats": [],
        "redundancyMode": "Any",
        "tags": [],
        "toId": "device-b.module-1.port-in-1.in",
        "weight": 1,
        "weightFactors": {
          "bandwidth": { "weight": 0 },
          "service": { "max": 100, "weight": 0 }
        }
      },
      "fromDevice": "device-a",
      "toDevice": "device-b"
    }
  },
  "header": { "ok": true, "code": "OK" }
}
```

Fixture: `tests/fixtures/inspect/2025.4.9/lookup_inspect_edges_by_ids.json`.

### `POST /rest/v2/actions/status/collector/lookupInspectVertexById` / `…ByIds`

**Verified 2025.4.9.** Editable vertex form for one id (`data: "<vertex-id>"`)
or batched (`…ByIds`, `data: ["<id>", …]`, response keyed by id). The UI bundle
uses only the batched form. **No `_rev`.** Together with
`lookupInspectDevice` (devices, above) and `lookupInspectEdgesByIds` this
covers all three `replace*` element kinds for stage-time baselines
(ADR-0009).

> **Vertex tags.** Tag bindings on a vertex are **not** part of the topology
> `nGraphElements` store (`app.topology` has no equivalent). Server-side they
> live in `videoipath_docs.device_tags`, separate from the `ngraph` table.
> This lookup is the Inspect-surface source for vertex tag state:
> `assignedTags` (with `all`, `inherited`, `local`, `inheritedConflict`) and
> `fields.tags` / `fields.localAssignedTags`. Hydrated `nodeStatus` ports carry
> the same bindings under `tagsInfo` for read-side display
> ([concepts.md §3.4](./concepts.md#34-tagging--device-vs-vertex-inspect-vs-topology)).

Response (single form; `…ByIds` nests this per id):

```json
{
  "data": {
    "assignedTags": { "all": [], "inherited": {}, "inheritedConflict": false, "local": {} },
    "context": {
      "devicePid": "device-a",
      "modulePid": "device-a.dev.module-1",
      "portPid": "device-a.dev.module-1.port-out-1"
    },
    "customSchemas": {},
    "fields": {
      "active": true,
      "controlProps": null,
      "custom": {},
      "desc": "",
      "destinationMonitorLeader": false,
      "extraAlertFilters": [],
      "label": "Port A (out)",
      "localAssignedTags": [],
      "queueable": false,
      "sipsMode": "NONE",
      "tags": [],
      "typeFields": {
        "ipAddress": null,
        "ipNetmask": null,
        "public": false,
        "supportsCpipeCfg": false,
        "supportsIgmpCfg": false,
        "supportsMacForwardingCfg": false,
        "supportsNsoCfg": false,
        "supportsOpenflowCfg": false,
        "supportsStaticIgmpCfg": false,
        "supportsVlanCfg": false,
        "supportsVplsCfg": false,
        "type": "ip",
        "vlanId": null,
        "vrfId": null
      },
      "useAsEndpoint": false
    },
    "id": "device-a.module-1.port-out-1.out",
    "isVirtual": false,
    "vertexType": "Out"
  },
  "header": { "ok": true, "code": "OK" }
}
```

Fixture: `tests/fixtures/inspect/2025.4.9/lookup_inspect_vertex_by_id.json`.

The `fields` object is **exactly the accepted `replaceVertices` payload shape**
(verified 2025.4.9 — see
[`updateTopology`](#post-restv2actionsstatuscollectorupdatetopology);
update-only). The same effective-label caveat as `lookupInspectDevice`
applies: `label` here can carry the `fDescriptor` fallback while the persisted
`descriptor.label` is empty.

### `POST /rest/v2/actions/status/collector/lookupNodeInfo` / `…/lookupEdgeInfo` / `…/lookupDeviceVertices`

**Verified 2025.4.9 — display-oriented**, not baselines. `lookupNodeInfo`
(`data: "<device-id>"`) and `lookupEdgeInfo` (`data: "<edge-id>"`) return
info-panel section lists (`[{header, content: [{label, field: {type, value},
meta}]}]`) — the drill-down side panels, with port `context` pids in `meta`.
`lookupDeviceVertices` takes `{"primary": "<device-a>", "secondary":
"<device-b>"}` and returns the connectable vertices per side in the same
label/value style (the connect dialog's port lists).

### `POST /rest/v2/actions/status/collector/lookupInspectDevice`

Purpose: collector lookup for one Inspect device/topology node.

Request:

```http
POST /rest/v2/actions/status/collector/lookupInspectDevice
Authorization: Basic <credentials>
Content-Type: application/json
Accept: application/json
```

```json
{
  "header": { "id": 0 },
  "data": "device-a"
}
```

Response example:

```json
{
  "data": {
    "assignedTags": {
      "all": [],
      "inherited": {},
      "inheritedConflict": false,
      "local": {}
    },
    "fields": {
      "coordinates": {
        "x": 500,
        "y": 8150
      },
      "descriptor": {
        "desc": "Example device description",
        "label": "Example Source Device"
      },
      "iconSize": "medium",
      "iconType": "gateway",
      "localAssignedTags": [],
      "sdpStrategy": "always",
      "siteId": null,
      "tags": ["#example-tag-a", "#example-tag-b"],
      "virtualDeviceFields": null
    }
  },
  "header": {
    "auth": true,
    "caption": "Operation Successful",
    "code": "OK",
    "errorCodes": [],
    "errorDetails": [],
    "id": "0",
    "msg": [],
    "ok": true,
    "user": "api-user"
  }
}
```

Model coverage:

- `InspectApiLookupInspectDeviceRequest`
- `InspectApiLookupInspectDeviceResponse`
- `InspectApiAssignedTags`
- `InspectApiLookupInspectDeviceFields`

The `fields` object is **exactly the accepted `replaceDevices` payload shape**
(verified 2025.4.9 — see
[`updateTopology`](#post-restv2actionsstatuscollectorupdatetopology)). Note
that `descriptor` here carries the *effective* label (persisted `descriptor`
merged with the `fDescriptor` fallback); committing it verbatim pins the
fallback label into the persisted `descriptor`.

Invalid object-style request example:

```json
{
  "header": {
    "auth": true,
    "caption": "Invalid Request",
    "code": "INVALID_REQUEST",
    "errorDetails": [
      {
        "msg": "Can't convert { object } to String",
        "path": [],
        "type": "conversionError"
      }
    ],
    "id": "0",
    "msg": ["Can't convert { object } to String"],
    "ok": false,
    "user": "api-user"
  }
}
```

### `POST /rest/v2/actions/status/collector/lookupSyncInfo`

Purpose: collector lookup for synchronization information.

Request:

```http
POST /rest/v2/actions/status/collector/lookupSyncInfo
Authorization: Basic <credentials>
Content-Type: application/json
Accept: application/json
```

```json
{
  "header": { "id": 0 },
  "data": ["device-a"]
}
```

Response example:

```json
{
  "data": {
    "device-a": {
      "add": {},
      "label": "Example Source Device",
      "remove": {},
      "severity": 0,
      "update": {}
    }
  },
  "header": {
    "auth": true,
    "caption": "Operation Successful",
    "code": "OK",
    "errorCodes": [],
    "errorDetails": [],
    "id": "0",
    "msg": [],
    "ok": true,
    "user": "api-user"
  }
}
```

Model coverage:

- `InspectApiLookupSyncInfoRequest`
- `InspectApiLookupSyncInfoResponse`
- `InspectApiLookupSyncInfoItem`

The device list must be non-empty. An empty list produced:

```json
{
  "header": {
    "auth": true,
    "caption": "Invalid Request",
    "code": "INVALID_REQUEST",
    "errorDetails": [
      {
        "msg": "Cannot create NonEmptyList from empty list",
        "path": [],
        "type": "conversionError"
      }
    ],
    "id": "0",
    "msg": ["Cannot create NonEmptyList from empty list"],
    "ok": false,
    "user": "api-user"
  }
}
```

### `POST /rest/v2/actions/status/network/addDevices`

Purpose: network action used by Inspect topology workflows to add devices.

Request shape:

```http
POST /rest/v2/actions/status/network/addDevices
Authorization: Basic <credentials>
Content-Type: application/json
Accept: application/json
```

```json
{
  "header": { "id": 0 },
  "data": [
    {
      "id": "device-a",
      "x": 500,
      "y": 8150
    }
  ]
}
```

No-op request used for safe capture:

```json
{
  "header": { "id": 0 },
  "data": []
}
```

No-op response:

```json
{
  "data": {
    "msg": [],
    "ok": true
  },
  "header": {
    "auth": true,
    "caption": "Operation Successful",
    "code": "OK",
    "errorCodes": [],
    "errorDetails": [],
    "id": "0",
    "msg": [],
    "ok": true,
    "user": "api-user"
  }
}
```

Model coverage:

- `InspectApiAddDevicesRequest`
- `InspectApiAddDevicesItem`
- `InspectApiSimpleActionResponse`
- `InspectApiActionValidationErrorResponse`

Non-empty request against a device outside the caller's writable domains returned
an HTTP 422 validation envelope and did not create any `nGraphElements`:

```json
{
  "header": {
    "auth": true,
    "caption": "The request could not be processed due to e.g. validation errors",
    "code": "VALIDATION_ERROR",
    "errorCodes": [],
    "errorDetails": [
      {
        "cause": "general",
        "msg": "Operation 'update' not allowed for resource type 'device' in domain 'GroupDomainId(example-domain)'",
        "path": ["device-a"],
        "type": "validationError"
      }
    ],
    "id": "",
    "msg": [
      "Operation 'update' not allowed for resource type 'device' in domain 'GroupDomainId(example-domain)'"
    ],
    "ok": false,
    "user": "api-user"
  }
}
```

Non-empty request against a disposable, non-driver device ID returned the normal
action response envelope with `data.ok: false` and did not create any
`nGraphElements`:

```json
{
  "data": {
    "msg": ["No topology reported by the device"],
    "ok": false
  },
  "header": {
    "auth": true,
    "caption": "Operation Successful",
    "code": "OK",
    "errorCodes": [],
    "errorDetails": [],
    "id": "0",
    "msg": [],
    "ok": true,
    "user": "api-user"
  }
}
```

### `POST /rest/v2/actions/status/network/syncDevices`

Purpose: network action used by Inspect topology workflows to synchronize
devices.

Request:

```http
POST /rest/v2/actions/status/network/syncDevices
Authorization: Basic <credentials>
Content-Type: application/json
Accept: application/json
```

```json
{
  "header": { "id": 0 },
  "data": {
    "ids": ["device-a"],
    "addOnly": true,
    "conflictStrategy": 0
  }
}
```

`conflictStrategy` values observed in the frontend bundle:

| Value | Meaning |
| --- | --- |
| `0` | Strict |
| `1` | Invalidate services |
| `2` | Cancel services |

No-op request used for safe capture:

```json
{
  "header": { "id": 0 },
  "data": {
    "ids": [],
    "addOnly": true,
    "conflictStrategy": 0
  }
}
```

No-op response:

```json
{
  "data": {
    "msg": [],
    "ok": true
  },
  "header": {
    "auth": true,
    "caption": "Operation Successful",
    "code": "OK",
    "errorCodes": [],
    "errorDetails": [],
    "id": "0",
    "msg": [],
    "ok": true,
    "user": "api-user"
  }
}
```

Model coverage:

- `InspectApiSyncDevicesRequest`
- `InspectApiSyncDevicesRequestData`
- `InspectApiSimpleActionResponse`

Non-empty request against a disposable, non-driver device ID returned:

```json
{
  "data": {
    "msg": [
      "A device sync requires the device to be present both in the graph and in the driver"
    ],
    "ok": false
  },
  "header": {
    "auth": true,
    "caption": "Operation Successful",
    "code": "OK",
    "errorCodes": [],
    "errorDetails": [],
    "id": "0",
    "msg": [],
    "ok": true,
    "user": "api-user"
  }
}
```

## `POST /rest/v2/actions/status/collector/updateTopology`

Purpose: Inspect commit endpoint. The client sends a full change set; empty
maps/lists mean no changes in that category. Staging is client-side until this
POST.

No-op request used for this capture:

```http
POST /rest/v2/actions/status/collector/updateTopology
Authorization: Basic <credentials>
Content-Type: application/json
Accept: application/json
```

```json
{
  "header": { "id": 0 },
  "data": {
    "replaceDevices": {},
    "replaceVertices": {},
    "replaceEdges": {},
    "replaceResourceTransforms": {},
    "addExternalEdges": [],
    "remove": [],
    "force": false
  }
}
```

No-op response:

```json
{
  "data": {
    "items": [],
    "res": {
      "msg": [],
      "ok": true
    },
    "validation": {
      "createIds": [],
      "details": {},
      "result": {
        "msg": [],
        "ok": true
      }
    }
  },
  "header": {
    "auth": true,
    "caption": "Operation Successful",
    "code": "OK",
    "errorCodes": [],
    "errorDetails": [],
    "id": "0",
    "msg": [],
    "ok": true,
    "user": "api-user"
  }
}
```

Successful commit detection:

```python
committed = response.header.ok and response.data.res.ok and response.data.validation.result.ok
```

Concurrency: the action performs **no revision check** — a stale `_rev` in
`replace*` payloads is ignored (last-writer-wins, verified 2025.4.9). Conflict
detection is client-side compare-and-commit
([ADR-0009](./decisions/0009-write-consistency.md)); after a successful commit
the snapshot is refreshed with targeted scoped reads
([ADR-0010](./decisions/0010-post-commit-snapshot-refresh.md)).

Failure modes (verified 2025.4.9):

| Failure mode | `data.res.ok` | `validation.result.ok` | Example |
| ------------ | ------------- | ---------------------- | ------- |
| Validation gate | `false` | `false` | Booking-blocked device remove (`status: -22`, `resolvable: false`) |
| Apply gate | `false` | `true` | `remove: ["unknown-id"]` → *Cannot remove non-existent object* |
| Bad edge reference | `false` | `true` | `replaceEdges` with non-existent `fromId` |

- **No partial apply**: mixing a valid `replaceEdges` with an invalid `remove`
  in one commit fails entirely (`items: []`) — reject-before-apply.
- **`force: true` does not bypass apply-gate errors** (`res.ok` stays `false`
  for non-existent remove keys).
- **`replaceDevices` takes the edit form, not the persisted element**
  (verified 2025.4.9 via a device coordinate commit + revert): sending the raw
  `baseDevice` element (`maps[]`, `fDescriptor`, `type`, …) is rejected with
  HTTP 400 conversion errors — `coordinates` and `localAssignedTags` are
  **mandatory**. The accepted shape is exactly `lookupInspectDevice`'s
  `fields` object; the server maps `coordinates` → `maps[]` itself:

  ```json
  {
    "replaceDevices": {
      "device-a": {
        "coordinates": { "x": 1600.0, "y": 9050.0 },
        "descriptor": { "desc": "", "label": "" },
        "iconSize": "medium",
        "iconType": "default",
        "localAssignedTags": [],
        "sdpStrategy": "always",
        "siteId": null,
        "tags": [],
        "virtualDeviceFields": null
      }
    }
  }
  ```

  `descriptor` is stored **verbatim** (an empty persisted descriptor stayed
  empty across commit + revert; the element round-tripped byte-identical
  except `_rev`). Caveat: the lookups return the *effective* label (persisted
  `descriptor` merged with the `fDescriptor` fallback) — a client that
  round-trips them unchanged pins the fallback label into `descriptor`.
  `replaceEdges` takes the raw persisted edge form (captured UI commit +
  verified apply).
- **`replaceVertices` takes the vertex edit form and is update-only**
  (verified 2025.4.9 via a `desc` round-trip on a live vertex, byte-identical
  revert): the accepted shape is exactly `lookupInspectVertexById`'s `fields`
  object. Committing a **new** vertex id passes schema conversion but fails
  validation with *"Vertex with id … was not found in graph"* — standalone
  vertices cannot be created through `updateTopology`; they originate from
  device sync (`syncDevices`) or virtual-device definitions.
- **Collector propagation**: a committed change is visible in collector reads
  ~25 ms after the POST returns (three samples, first poll each time) — the
  projection updates synchronously with the commit for practical purposes.
- Writes appear in `nGraphElements` under the composite `fromId::toId` key with
  a bumped `_rev`; a parallel UUID-keyed document may also exist for the same
  edge.
- `resolvable: true` has not been observed on 2025.4.9.
- Fixtures: `tests/fixtures/inspect/2025.4.9/update_topology_success.json`,
  `…/update_topology_replace_devices.json` (edit-form request, success
  response, and the raw-element rejection error),
  `…/update_topology_replace_vertices.json` (vertex edit-form request,
  success response, and the update-only validation failure),
  `…/update_topology_fail_remove.json`, `…/update_topology_fail_booking.json`.

Applied-change response (verified on 2025.4.9 — edge `weight` change):

```json
{
  "data": {
    "items": [
      {
        "external": null,
        "id": "device-a.dev.module-1.port-out-1.out::device-b.dev.module-1.port-in-1.in",
        "idx": 0,
        "res": { "msg": [""], "ok": true }
      }
    ],
    "res": { "msg": [], "ok": true },
    "validation": {
      "createIds": [],
      "details": {},
      "result": { "msg": [], "ok": true }
    }
  },
  "header": { "ok": true, "code": "OK" }
}
```

Known failure shape from the accepted ADR (booking-blocked device delete,
verified 2025.4.9):

```json
{
  "data": {
    "items": [],
    "res": { "msg": ["Validation failed"], "ok": false },
    "validation": {
      "details": {
        "booking-1001": {
          "isCancel": false,
          "isProduct": false,
          "resolvable": false,
          "rev": "2-2026-06-10T19:54:01.297948842Z[UTC]",
          "status": -22,
          "type": "generic"
        }
      },
      "result": {
        "msg": ["A required edge was not found. (main); A required edge was not found. (redundant)"],
        "ok": false
      }
    }
  }
}
```

Earlier anonymized failure shape (browser capture, 2026-06-18):

```json
{
  "data": {
    "items": [],
    "res": {
      "msg": ["Validation failed"],
      "ok": false
    },
    "validation": {
      "createIds": [],
      "details": {
        "booking-1001": {
          "isCancel": false,
          "isProduct": false,
          "resolvable": false,
          "rev": "2-2026-01-01T00:00:00.000000000Z[UTC]",
          "status": -22,
          "type": "generic"
        }
      },
      "result": {
        "msg": ["A required edge was not found. (main)"],
        "ok": false
      }
    }
  }
}
```

## Action registration discovery

`GET /rest/v2/actions/status/collector/<actionName>` returns whether an action
is registered on the server (verified 2025.4.9):

```http
GET /rest/v2/actions/status/collector/updateTopology
```

```json
{
  "actions": {
    "status": {
      "collector": {
        "updateTopology": { "desc": "", "label": "UpdateTopology" }
      }
    }
  },
  "header": { "ok": true, "code": "OK" }
}
```

The complete registered set (`GET /rest/v2/actions/status/collector/**`,
enumerated live on 2025.4.9):

```text
findContext                lookupInspectDevice        lookupPathHistoryTimes
lookupConfigDesc           lookupInspectEdgesByIds    lookupPathNodeAlarms
lookupDeviceAlarms         lookupInspectVertexById    lookupResourceSummary
lookupDeviceVertices       lookupInspectVertexByIds   lookupResourceTransformInfo
lookupEdgeInfo             lookupInstancesStatus      lookupServiceInfo
                           lookupNodeInfo             lookupSyncInfo
                           lookupPathHistory          lookupVertexAlarms
                                                      restoreHistoricalPath
                                                      updateTopology
```

Unregistered actions return an empty `collector` object; POST to those URLs
responds with `No action node in request` regardless of payload. On 2025.4.9
`lookupGraphElement`, `validateTopology`, `discardTopology`, `importTopology`,
`exportTopology`, and `importExport/{import,export}` are **not registered**
(27+ POST payload variants tried for `validateTopology`; the UI bundle
references none of them; `importExport` data namespaces are empty under
`status`/`config`/`experimental`). These are unregistered server stubs — no
further payload probing is warranted unless a future version registers them
(re-check the GET schema after upgrades). Fixture:
`tests/fixtures/inspect/2025.4.9/action_schema_collector.json`.

Cross-check against the UI bundle (`/assets/index-*.js`, 2025.4.9): it
references `updateTopology`, `addDevices`, `syncDevices`, `lookupSyncInfo`,
`lookupInspectEdgesByIds`, `lookupInspectVertexByIds`, `lookupEdgeInfo`,
`lookupNodeInfo`, and `lookupConfigDesc` — and contains **zero references to
`nGraphElements`** ([ADR-0008](./decisions/0008-collector-only-endpoints.md)).
