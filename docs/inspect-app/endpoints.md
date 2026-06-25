# Inspect App Endpoint Reference

Captured against a local VideoIPath test instance. All hostnames, usernames,
device IDs, booking IDs, labels, endpoint IDs, IP addresses, multicast
addresses, UUIDs, and revisions in this document are anonymized examples. Only
read-only requests and one empty no-op `updateTopology` POST were executed.

The Inspect package scope follows the accepted ADRs:

- Request/response only; no WebSocket subscription API.
- Stateless reads; callers re-fetch when they need fresh status.
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

Purpose: canonical Inspect read aggregate. This is the primary read surface for
services, path drill-down, external edge status, and optional topology node
status.

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

Purpose: existing status-plane edge view. This is not the collector facade, but
it is useful for cross-checking edge payload fields when
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

Purpose: revisioned config store that `updateTopology` persists into. Inspect
models include independent `InspectApi*` nGraph DTOs for this persisted shape, but
they do not import or subclass topology app models.

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

Known failure shape from the accepted ADR:

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
