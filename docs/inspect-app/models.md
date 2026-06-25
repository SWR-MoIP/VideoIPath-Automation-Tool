# Inspect App Data Model

This document describes Inspect data as package users should think about it:
services, devices, ports, edges, status, and topology changes.

The implementation uses two layers:

- **Transport DTOs** in `src/videoipath_automation_tool/apps/inspect/model/` mirror
  HTTP request and response payloads. These classes are prefixed with `InspectApi`
  and are intended for direct API communication and parsing.
- **Domain models** in `src/videoipath_automation_tool/apps/inspect/domain/` are
  the objects package users work with: `InspectDevice`, `InspectPort`,
  `InspectEdge`, and `InspectService`. They are built from an `InspectSnapshot`
  and resolve relations from internal indexes instead of making extra HTTP calls.

Wire-shape examples and endpoint references live in
[endpoints.md](./endpoints.md). All examples below are anonymized.

## Two Layers

```mermaid
flowchart LR
    Http[HTTP collector response] --> ApiDto[InspectApiCollectorResponse]
    ApiDto --> Snapshot[InspectSnapshot]
    Snapshot --> Device[InspectDevice]
    Device --> Ports[InspectPort]
    Device --> Edges[InspectEdge]
    Device --> Services[InspectService]
```

Typical read flow:

```python
response = InspectApiCollectorResponse.model_validate(payload)
snapshot = InspectSnapshot.from_response(response)
device = snapshot.get_device_by_id("device-a")
ports = device.ports
edges = device.edges
services = device.services
linked = device.linked_devices

port = ports[0]
if port.edge is not None:
    peer = port.edge.to_device
    peer_port = port.edge.to_port
```

Relation getters resolve full domain objects from snapshot indexes. Repeated
access returns the same cached instance for a given device, port, edge, or
service.

Refresh data by fetching a new collector response and building a new snapshot.
Relation getters never perform hidden HTTP requests.

## Mental Model

Inspect is built from two data surfaces:

- A **collector snapshot** describes what the Inspect UI can show right now:
  services, path hops, devices, ports, external edges, sync hints, and status.
- A **topology change set** describes what the client wants to commit to the
  persisted graph store.

```mermaid
flowchart LR
    Service[Service booking] --> Path[Path hops]
    Path --> DeviceA[Device A]
    Path --> DeviceB[Device B]
    DeviceA --> PortA[Input/output ports]
    DeviceB --> PortB[Input/output ports]
    PortA --> Edge[External edge status]
    Edge --> PortB
    DeviceA --> Sync[Sync information]
    ChangeSet[Topology change set] --> Graph[nGraphElements store]
```

## Collector Snapshot

The collector response is a REST v2 envelope with a `header` and a `data` object.
The useful Inspect content is under `data.status.collector`.

```json
{
  "data": {
    "status": {
      "collector": {
        "inspect": {
          "paths": { "_items": [] },
          "nodeStatus": { "_items": [] }
        },
        "externalEdgesByDeviceKey": { "_items": [] },
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
    "id": "",
    "msg": [],
    "ok": true,
    "user": "api-user"
  }
}
```

VideoIPath collections use `_items`. Transport DTOs preserve that wire shape.
`InspectSnapshot` indexes the parsed collector data once and exposes user-facing
objects from those indexes.

## User-Facing Domain Objects

These are the classes package users should prefer for read-side workflows.

### `InspectDevice`

Represents one topology device/node with status, sync hints, and relations.

| Field / property | Meaning |
| --- | --- |
| `id` | Device identifier, for example `device-a` |
| `label` | Display label |
| `status` | Device status summary |
| `sync_severity` | Sync severity from node status |
| `tags` | Assigned tags |
| `coordinates` | Topology map position when available |
| `ports` | Ports on this device |
| `edges` | External edges touching this device |
| `services` | Services whose path includes this device |
| `linked_devices` | Neighbour devices via edges or shared service paths |

Lookup:

```python
device = snapshot.get_device_by_id("device-a")
matches = snapshot.find_devices_by_name("Example Device A")
```

### `InspectPort`

Represents one module port with status, optional vertex linkage, and an optional
external edge to another device.

| Field / property | Meaning |
| --- | --- |
| `id` | Port pid |
| `label` | Display label |
| `device` | Owning `InspectDevice` |
| `module_id` | Owning module |
| `status` | Port status summary |
| `vertex_id` | Linked topology vertex when available |
| `edge` | External edge when this port connects to another device; otherwise `None` |

### `InspectEdge`

Represents one external edge status entry between two endpoint devices/ports.

| Field / property | Meaning |
| --- | --- |
| `id` | Edge identifier |
| `from_device` / `to_device` | Endpoint devices |
| `from_port` / `to_port` | Endpoint ports |
| `bandwidth` / `max_bandwidth` | Bandwidth values |
| `status` | Alarm, bandwidth, maintenance, and PTP summary |
| `services` | Services touching either endpoint device |

### `InspectService`

Represents one service/booking path across devices and ports.

| Field / property | Meaning |
| --- | --- |
| `booking_id` | Booking identifier |
| `label` | Service label when available |
| `source` / `destination` | Endpoint labels |
| `source_device` / `destination_device` | Endpoint devices |
| `source_port` / `destination_port` | Endpoint ports |
| `status` | Service status summary |
| `path_devices` | Ordered devices in the path |
| `path_ports` | Ports encountered in the path |

Lookup:

```python
service = snapshot.get_service_by_booking_id("booking-1001")
all_services = snapshot.get_services()
```

## Transport DTO Examples

A path item links one service or booking to the devices and ports used to carry
it. This is the best starting point when a caller wants to answer: "Which devices
does this service traverse?"

```json
{
  "_id": "booking-1001::main",
  "_vid": "_:booking-1001::main",
  "serviceFields": {
    "bid": "booking-1001",
    "from": "endpoint-a",
    "fromLabel": "Example Source",
    "fromPid": "endpoint-a-pid",
    "to": "endpoint-b",
    "toLabel": "Example Destination",
    "toPid": "endpoint-b-pid",
    "isMain": true,
    "serviceStatus": {
      "config": { "sa": 0, "severity": 0 },
      "total": { "sa": 0, "severity": 0 }
    }
  },
  "path": [
    {
      "bid": "booking-1001",
      "ipDesc": "<multicast-address>:<port>",
      "structure": {
        "deviceId": "device-a",
        "devicePid": "device-a",
        "deviceLabel": "Example Device A",
        "expectConfig": true,
        "inputStatus": {
          "pid": "port-a-in",
          "label": "Input Port",
          "context": {
            "devicePid": "device-a",
            "modulePid": "module-a",
            "portPid": "port-a-in"
          },
          "status": { "sa": 0, "severity": 0 }
        },
        "outputStatus": {
          "pid": "port-a-out",
          "label": "Output Port",
          "context": {
            "devicePid": "device-a",
            "modulePid": "module-a",
            "portPid": "port-a-out"
          },
          "status": { "sa": 0, "severity": 0 }
        },
        "moduleAndDeviceStatus": { "sa": 0, "severity": 0 }
      }
    }
  ]
}
```

In Python this maps to `InspectApiPathItem`, `InspectApiPathServiceFields`,
`InspectApiPathSegment`, and `InspectApiPathStructure`.

## Devices, Modules, And Ports

Node status describes a device-like node as the Inspect UI sees it. It can
include coordinates, modules, ports, status, tags, sync severity, and embedded
references back to service paths.

```json
{
  "_id": "node-device-a",
  "_vid": "_:node-device-a",
  "deviceId": "device-a",
  "pid": "device-a",
  "label": "Example Device A",
  "meta": {
    "coordinates": { "x": 500, "y": 8150 }
  },
  "status": { "sa": 0, "severity": 0 },
  "syncSeverity": 0,
  "tags": ["#example-tag"],
  "modules": {
    "module-a": {
      "_id": "module-a",
      "pid": "module-a",
      "label": "Example Module",
      "status": { "sa": 0, "severity": 0 },
      "ports": {
        "port-a-out": {
          "_id": "port-a-out",
          "pid": "port-a-out",
          "label": "Output Port",
          "status": { "sa": 0, "severity": 0 },
          "vertexInfo": {
            "type": "single",
            "id": "vertex-a-out",
            "label": "Output Vertex",
            "vertexType": "ip",
            "fields": {
              "isActive": true,
              "isControlled": true,
              "isEndpoint": false
            }
          }
        }
      }
    }
  }
}
```

In Python this maps to `InspectApiNodeStatusItem`, `InspectApiModuleStatus`,
`InspectApiPortStatus`, `InspectApiSingleVertexInfo`, and `InspectApiDoubleVertexInfo`.

## External Edges

External edge status groups live connectivity between two devices. Each group has
two sides, and each side can contain one or more edge entries keyed by edge ID.

```json
{
  "_id": "device-a::device-b",
  "_vid": "device-a::device-b",
  "primary": {
    "devicePid": "device-a",
    "label": "Example Device A",
    "data": {
      "edge-a-b-0001": {
        "id": "edge-a-b-0001",
        "bandwidth": 1000,
        "maxBandwidth": 10000,
        "ratio": 0.1,
        "fromStatus": {
          "pid": "port-a-out",
          "label": "Output Port",
          "status": { "sa": 0, "severity": 0 }
        },
        "toStatus": {
          "pid": "port-b-in",
          "label": "Input Port",
          "status": { "sa": 0, "severity": 0 }
        },
        "status": {
          "alarm": 0,
          "bandwidth": 0,
          "maintenance": 0,
          "ptp": 0
        }
      }
    }
  },
  "secondary": {
    "devicePid": "device-b",
    "label": "Example Device B",
    "data": {}
  },
  "status": {
    "alarm": 0,
    "bandwidth": 0,
    "maintenance": 0,
    "ptp": 0
  }
}
```

In Python this maps to `InspectApiExternalEdgesByDeviceKeyItem`,
`InspectApiExternalEdgeSide`, `InspectApiExternalEdgeStatus`, and
`InspectApiExternalEdgeLiveStatus`.

## Lookup And Sync Actions

Action endpoints return focused views for UI workflows.

`lookupInspectDevice` returns editable/display fields for one device:

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
      "coordinates": { "x": 500, "y": 8150 },
      "descriptor": {
        "desc": "Example device description",
        "label": "Example Device A"
      },
      "iconSize": "medium",
      "iconType": "gateway",
      "localAssignedTags": [],
      "sdpStrategy": "always",
      "siteId": null,
      "tags": ["#example-tag"],
      "virtualDeviceFields": null
    }
  }
}
```

`lookupSyncInfo` returns per-device sync differences:

```json
{
  "data": {
    "device-a": {
      "add": {},
      "label": "Example Device A",
      "remove": {},
      "severity": 0,
      "update": {}
    }
  }
}
```

`addDevices` and `syncDevices` use the same normal action-result shape when the
action runs:

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
    "id": "0",
    "msg": [],
    "ok": true,
    "user": "api-user"
  }
}
```

Some invalid `addDevices` requests can be rejected before an action result is
returned. Those responses contain only the REST header with validation details.

## Persisted Topology Graph

The collector snapshot is a status view. Committed Inspect topology data is stored
in `config.network.nGraphElements._items[]`. Each item has an ID, optional
revision, display descriptors, tags, and a `type` value that tells callers which
shape to parse.

```mermaid
flowchart LR
    BaseDevice[baseDevice: device node]
    IpVertex[ipVertex: IP port/vertex]
    CodecVertex[codecVertex: media endpoint vertex]
    GenericVertex[genericVertex: generic vertex]
    Edge[unidirectionalEdge: connection]
    Transform[nGraphResourceTransform: resource mapping]

    BaseDevice --> IpVertex
    BaseDevice --> CodecVertex
    BaseDevice --> GenericVertex
    IpVertex --> Edge
    Edge --> IpVertex
    Transform --> Edge
```

Example persisted graph elements:

```json
[
  {
    "_id": "device-a",
    "_vid": "device-a",
    "_rev": "1-example-revision",
    "type": "baseDevice",
    "descriptor": {
      "label": "Example Device A",
      "desc": "Example device description"
    },
    "fDescriptor": {
      "label": "Example Device A",
      "desc": "Example device description"
    },
    "iconSize": "medium",
    "iconType": "gateway",
    "isVirtual": false,
    "maps": [],
    "sdpStrategy": "always",
    "siteId": null,
    "tags": ["#example-tag"]
  },
  {
    "_id": "vertex-a-out",
    "_vid": "vertex-a-out",
    "type": "ipVertex",
    "deviceId": "device-a",
    "descriptor": { "label": "Output Vertex", "desc": "" },
    "fDescriptor": { "label": "Output Vertex", "desc": "" },
    "gpid": {
      "component": 1,
      "pointId": ["device-a", "module-a", "port-a-out"]
    },
    "ipAddress": "198.51.100.10",
    "ipNetmask": "255.255.255.0",
    "supportsIgmpCfg": true,
    "tags": []
  },
  {
    "_id": "edge-a-b-0001",
    "_vid": "edge-a-b-0001",
    "type": "unidirectionalEdge",
    "fromId": "vertex-a-out",
    "toId": "vertex-b-in",
    "active": true,
    "bandwidth": -1,
    "capacity": 65535,
    "redundancyMode": "Any",
    "weight": 0,
    "weightFactors": {
      "bandwidth": { "weight": 0 },
      "service": { "max": 100, "weight": 0 }
    },
    "tags": []
  }
]
```

In Python these shapes live in `ngraph.py`.

## Committing Changes

`updateTopology` sends the whole change set in one request. Empty maps/lists are a
valid no-op. Non-empty maps upsert graph elements by ID, `addExternalEdges` adds
edge objects, and `remove` deletes graph elements by ID.

```json
{
  "header": { "id": 0 },
  "data": {
    "replaceDevices": {
      "device-a": {
        "_id": "device-a",
        "_vid": "device-a",
        "type": "baseDevice",
        "descriptor": { "label": "Example Device A", "desc": "" },
        "fDescriptor": { "label": "Example Device A", "desc": "" },
        "tags": []
      }
    },
    "replaceVertices": {
      "vertex-a-out": {
        "_id": "vertex-a-out",
        "_vid": "vertex-a-out",
        "type": "ipVertex",
        "deviceId": "device-a",
        "descriptor": { "label": "Output Vertex", "desc": "" },
        "fDescriptor": { "label": "Output Vertex", "desc": "" },
        "tags": []
      }
    },
    "replaceEdges": {
      "vertex-a-out::vertex-b-in": {
        "_id": "edge-a-b-0001",
        "_vid": "edge-a-b-0001",
        "type": "unidirectionalEdge",
        "fromId": "vertex-a-out",
        "toId": "vertex-b-in",
        "descriptor": { "label": "", "desc": "" },
        "fDescriptor": { "label": "", "desc": "" },
        "tags": []
      }
    },
    "replaceResourceTransforms": {},
    "addExternalEdges": [],
    "remove": [],
    "force": false
  }
}
```

A commit is successful only when all three success flags are true:

```python
response.header.ok and response.data.res.ok and response.data.validation.result.ok
```

Validation failures can still arrive with `header.ok == true`, so callers must
inspect `data.res`, `data.validation.result`, and `data.validation.details`.

## Python Module Layout

Transport DTOs are split by payload area under `apps/inspect/model/`:

- `common.py` — shared envelopes, descriptors, status summaries, action wrappers
- `collector.py` — collector snapshot wire models
- `ngraph.py` — persisted `nGraphElements` wire models
- `actions.py` — lookup/add/sync action request and response DTOs
- `update_topology.py` — `updateTopology` change-set and commit response DTOs

User-facing read models live alongside the snapshot:

- `snapshot.py` — `InspectSnapshot` and internal indexes
- `domain/device.py` — `InspectDevice`
- `domain/port.py` — `InspectPort`
- `domain/edge.py` — `InspectEdge`
- `domain/service.py` — `InspectService`

When adding transport fields, prefer extending the nearest existing `InspectApi*`
DTO. When adding user-facing behaviour, extend the domain layer and snapshot
indexes instead of exposing raw HTTP nesting to callers.
