# Provisioning — Reference

Complete user reference for `videoipath_automation_tool.provisioning`. For a short
introduction, read the [getting-started page](../../getting-started-guide/05_Provisioning.md)
first. Why the feature works this way is in [concepts.md](./concepts.md) and the
[decisions](./decisions/README.md). Vertex processors, including the built-in
Matrox processor, have their own page: [processors.md](./processors.md).

## Contents

1. [Engine API](#1-engine-api)
2. [Describing a device: `ProvisioningDevice`](#2-describing-a-device-provisioningdevice)
3. [Blueprint document](#3-blueprint-document)
4. [Variants](#4-variants)
5. [Loading and validation](#5-loading-and-validation)
6. [Naming](#6-naming)
7. [Planning and applying](#7-planning-and-applying)
8. [Results, errors, and recovery](#8-results-errors-and-recovery)
9. [Engine configuration](#9-engine-configuration)
10. [Source-system adapters](#10-source-system-adapters)
11. [Limits and verification status](#11-limits-and-verification-status)
12. [Public API index](#12-public-api-index)
13. [Migrating from the former API](#13-migrating-from-the-former-api)

## 1. Engine API

`ProvisioningEngine(app, *, processors=None, options=None, naming=None, logger=None)`
takes any object with `inventory` and `inspect` properties (the `ProvisioningApp`
protocol). `VideoIPathApp` satisfies it. The app has no provisioning attribute, so
you construct the engine yourself.

| Member | Purpose |
|---|---|
| `plan(device, blueprint, *, scope="all", inputs=None, variants=(), naming=None, options=None)` | Read-only. Loads and resolves the blueprint, reads current state, returns a `ProvisioningPlan`. |
| `apply(device, blueprint, *, ..., dry_run=False)` | Same arguments as `plan`, plus `dry_run`. Identical to `plan(...).apply(dry_run=...)`. |
| `validate(blueprint, *, inputs=None, variants=None)` | Offline. Checks the base and every individual variant, or one explicit combination, including registered processor parameters. |
| `json_schema()` | Document JSON Schema for this engine: `processor_type` limited to the registered processors, with each one's parameters. |
| `register_processor(processor_id, processor_cls)` | Registers a processor for this engine only. See [processors.md](./processors.md). |
| `configure(*, options=..., naming=...)` | Replaces engine defaults. See [section 9](#9-engine-configuration). |
| `options`, `naming`, `registry`, `app` | Current defaults. `registry` returns a copy. |

`scope` is `"all"`, `"inventory"`, or `"topology"`. The blueprint argument accepts
a file path string, a `pathlib.Path` (or another `os.PathLike[str]`), or a
`Blueprint` instance.

**`ProvisioningPlan`**

| Member | Meaning |
|---|---|
| `apply(*, dry_run=False)` | Re-checks the plan's assumptions and executes it. A dry run runs the checks without writes. |
| `summary()` | Human-readable, redacted before/after listing, bindings, diagnostics, and unresolved work. |
| `phases`, `phase(name)` | `PlannedPhase` records (`planned`, `no_change`, `deferred`, `skipped`) with their `PlannedOperation`s and `FieldChange`s. |
| `has_changes` | `True` when any phase is `planned` or `deferred`. |
| `fully_resolved` | `False` when local topology work is deferred, an Inventory update requires replanning, or peer edges remain unresolved. |
| `interface_bindings`, `port_bindings`, `edges` | Legacy IP bindings, generic port bindings, and each edge’s endpoints, edge ids, status and unresolved reason. |
| `diagnostics`, `skipped_sections` | Warnings and sections the scope skipped. |
| `source_key`, `scope`, `variants`, `inventory_id`, `topology_target`, `driver_id`, `driver_schema_version`, `processor_type`, `blueprint_digest` | Identity of what was planned. |

A plan is an in-memory object bound to the app it was built with. It also holds
unredacted Inventory values for the write, so it is not a document you save and
replay elsewhere.

**`ApplyResult`**

| Field | Meaning |
|---|---|
| `status` | `succeeded`, `no_change`, `planned` (dry run), `failed`, `partial`, or `unknown`. `partial` with `replan_required` is returned, not raised. |
| `ok` | `True` for `succeeded`, `no_change`, and `planned`, except when `verification` is `unconfirmed`. A succeeded write with an unconfirmed read-back stays `succeeded`; `ok` is false so it is not treated as confirmed. |
| `replan_required` | `True` after an Inventory update requiring rediscovery, or when peer edges remain open. Real runs return `partial`; dry runs return `planned`. Create a new plan when discovery is ready. |
| `inventory_id`, `topology_device_id`, `module_id`, `source_key` | Ids involved. Persist `inventory_id` in your source system. |
| `phases`, `phase(name)` | `PhaseResult` per phase: `completed`, `no_change`, `skipped`, `failed`, `unknown`, `not_run`, `planned`, or `deferred`. `deferred` reports work still waiting for discovery or a new plan. |
| `interface_bindings`, `port_bindings`, `edges`, `diagnostics` | Resolved bindings and edge outcomes after execution. Deferred edges retain the reason and available endpoint information. |
| `materialized` | `True` when deferred topology work was computed during apply. |
| `verification`, `verification_detail` | `confirmed`, `unconfirmed`, or `not_applicable`. |
| `dry_run` | Whether the execution performed checks without writes. |

## 2. Describing a device: `ProvisioningDevice`

`ProvisioningDevice` is one device, module, or virtual device, plus the facts only
your source system knows.

| Field | Meaning |
|---|---|
| `key` | Your id for this device, for example the id in the source system, so you can match a result back to it. It is not written to VideoIPath. |
| `label`, `description` | Instance facts used by naming. |
| `inventory_id` | The Inventory record that already belongs to this device. If that record is missing, planning fails. The engine will not create a second one in its place. Leave the field out when a selected inventory section should create the record. |
| `management_address`, `alternative_addresses` | Connection addresses. The driver decides the string format, so these are not always IP addresses. An alternative address is a string or an `AlternativeAddress(address, credentials)`. Leave the field out to leave the server value alone. Pass `[]` to clear alternative addresses. A supplied list is the full desired set and also replaces per-address credentials: a plain string carries none, so an existing credential is cleared unless that address is an `AlternativeAddress`. An address listed twice fails. |
| `credentials` | Runtime `Credentials(username, password)`. Credentials stay out of YAML, and the engine redacts them in plans, results, and errors. Secrets are write-only: the server masks them on read, so a plan never compares them. They are written on create and with every update; a credential change alone needs `ApplyOptions(write_credentials=True)`. |
| `topology` | `DeviceTarget(device_id)` or `ModuleTarget(device_id, module_id)`, using exact Inspect ids. Leave it out to target the Inventory id, including an id this same plan creates. |
| `module_position` | Module context you supply for naming and mappings. It is a string, such as `"0"`, `"A1"`, or `"1/2"`. |
| `inventory_overrides` | Per-device Inventory settings that are not secrets (`InventorySettings`): `custom_settings`, `generic_settings`, `snmp`, `metadata`, `active`. Applied after the selected variant. |
| `edges` | Concrete external edges: local port, peer device/module and port, direction and managed edge fields. Defaults to `[]`; does not remove existing edges. |
| `attributes` | JSON facts you own. Scalar leaves are available to naming as `attributes.<name>`, and processors see them on `context.source`. |

`ProvisioningDevice.from_inventory(inventory_device, key=None)` binds an existing
Inventory device by id, label, and description.

These are the arrangements the engine supports:

- **Standalone device.** Pass `inventory_id`, or let the inventory section create the record. Topology defaults to that device.
- **Chassis.** Use a device-scoped blueprint for the chassis. Call the engine again for each module, with a `ModuleTarget` and that module's own blueprint.
- **Module with no Inventory record.** Pass a `ModuleTarget` and a topology-only blueprint, or set `scope="topology"`.
- **Module with its own Inventory record.** `inventory_id` names the module's record. `ModuleTarget` names the module inside its parent. The two ids do not have to match. The parent device stays as it is.
- **Several topology scopes for one source entity.** Call the engine more than once with the same `key` and different targets. Configure Inventory on one of those calls.
- **Existing virtual device.** Pass `DeviceTarget("virtual.N")` and `scope="topology"`.

Take module ids from Inspect (`device.modules`). A module label or a slot label is
a display name. The engine does not use it as identity.

## 3. Blueprint document

```yaml
schema_version: 1
defaults:
  inventory:
    driver_id: com.nevion.NMOS_multidevice-0.1.0
    generic_settings:
      enable_https: false
      http_auth: 0
    custom_settings:
      port: 8080
      disable_rx_sdp_with_null: true
  topology:
    device:
      icon_size: medium
    ip_vertex_mapping:
      stream-a:
      - P1
      stream-b:
      - P2
    vertex_processor:
      processor_type: matrox.convertip.default
      params:
        redundant_streams: true
        video_receiver_tags:
        - Format~~video-tag-a
        video_sender_tags:
        - Format~~video-tag-b
variants:
  receiver:
    topology:
      vertex_processor:
        params:
          mode: rx
```

`schema_version` must be the integer `1`. `defaults` contains `inventory`,
`topology`, or both. `inputs` and `variants` are optional. Each variant contains
Inventory and/or Topology configuration patches. Variant names start with a
letter or digit and may contain letters, digits, `_`, `.`, and `-`.

### Typed inputs

Inputs declare values the caller supplies independently of any source system:

```yaml
inputs:
  api_port:
    type: integer
    default: 8080
  location:
    type: object
    properties:
      code: {type: string}
    required: [code]
  video_tags:
    type: array
    items: {type: string}
    default: []
defaults:
  inventory:
    driver_id: com.nevion.NMOS_multidevice-0.1.0
    custom_settings:
      port: {$input: api_port}
```

`type` supports `string`, `integer`, `number`, `boolean`, `array`, `object`,
and `null`. Definitions also accept `description`, `default`, and `enum`.
Arrays accept a recursive `items` definition. Objects accept recursive
`properties`, a `required` property-name list, and `additionalProperties`
(default `false`). Types are strict: a boolean is not an integer, and a numeric
string is not converted. Defaults and enum entries must conform to the declaration.

A supplied input replaces its whole default; nested property defaults are not
inserted automatically. An input without a default is required when the effective
selected scope uses it. Unknown supplied inputs or declared-reference names fail.
Naming can use scalar leaves as `{inputs.location.code}`. Input names start with
a letter or underscore and may contain letters, digits, `_`, and `-`.

`{$input: api_port}` inserts a typed value at a configuration value position,
including whole lists and objects. `{$literal: ...}` escapes a value containing
operator keys. Each operator mapping contains exactly one key. Inserted values
are never evaluated again as operators. Section keys, driver ids, and processor
declarations stay static; processor parameters can contain references.

```python
plan = engine.plan(
    device, blueprint,
    inputs={"location": {"code": "site-a"}, "video_tags": ["video-tag-a"]},
    variants=["secure", "receiver"],
)
```

### Inventory entry

| Key | Effect |
|---|---|
| `driver_id` | Required on the resolved entry. Checked against the driver schema selected in this library. It belongs on the entry, not inside `custom_settings`. |
| `custom_settings` | Driver settings, keyed by the Python field name (`port`, for example). An unknown name, a wrong type (`"80"` where an integer is required), or a value outside the allowed range fails the plan before any write. |
| `generic_settings` | `enable_https`, `trust_all_certificates`, and `http_auth`. `http_auth` is the server's raw `httpAuth` mode code. `0` turns HTTP authentication off. |
| `snmp` | `use_global_settings`, and `configuration` as an exact label (a string) or `{id: ...}`, for example `{id: default}`. A missing or ambiguous label fails. |
| `active` | Enables or disables the record. |
| `metadata` | Patches `meta` by key. Values are strings, numbers, or booleans. Keys you leave out stay as they are. |
| `naming` | `inventory_label` and `inventory_description`. See [section 6](#6-naming). |

### Topology entry

| Key | Effect |
|---|---|
| `device` | Device targets only: `icon_type`, `icon_size`, `sdp_strategy`, `site_id`, `coordinates` with `x` and `y`, and `tags`. |
| `module` | Module targets only: `tags` on that module. |
| `ip_vertex_mapping` | Your interface key, mapped to an ordered list of candidate port factory labels. The first candidate that matches exactly one IP port in scope wins. A candidate that matches more than one port fails the plan, and later candidates are not tried. Labels may contain `{module.position}`. Bindings show up in the plan and the result for cable workflows. The mapping itself writes nothing. |
| `vertex_processor` | `processor_type` and `params`. The registered processor validates `params`. See [processors.md](./processors.md). |
| `vertices` | Explicit overrides. Point at the vertex with `vertex_id`, or with `factory_label` (may contain `{module.position}`) optionally narrowed by `kind` and `direction` (`In`, `Out`, `Internal`, `Undecided`), and supply `fields`. Those fields use the same contract as processor output. Each override must match exactly one vertex. |
| `naming` | `device_label`, `device_description`, `endpoint_label`, `endpoint_description`. |
| `port_mapping` | Generic local port names mapped to ordered lists of `PortSelector` objects. Supports typed inputs and variant overlays. Keys must differ from `ip_vertex_mapping`. |

### Vertex fields

On a vertex override or in processor output, `fields` may set:

| Field | Applies to |
|---|---|
| `use_as_endpoint`, `label`, `description`, `active`, `sips_mode`, `tags` | All vertices. `""` clears a label or a description. |
| `sdp_support`, `main_destination_port`, `spare_destination_port` | Codec vertices. Ports are `0`–`65535`. |
| `supports_static_igmp` | IP vertices. |

Explicit `null` is rejected on any patch field. Omit the field instead.

### Tags

Tags are exact catalog ids, such as `Format~~V_1080p50`. The engine does not
create catalog entries.

- A list replaces the local tags exactly, and `[]` clears them.
- `{add: [...], remove: [...]}` changes the listed tags and leaves every other local tag in place. A tag may not appear in both lists, and at least one list must be non-empty.
- Inherited tags stay as they are. Only local tags are edited.

### Leaving a field out

**Leaving a field out leaves the server value alone.** An update writes only the
fields the resolved blueprint, the instance facts, or naming actually set.
Everything else on the record stays as it is. Delete a field from the blueprint,
or switch variants, and values written by an earlier configuration remain on the
server. The engine does not store what it applied last time. If a variant should
turn a stream off, replace a tag set, or clear an endpoint flag, put that new
value in the variant. Background: [ADR-003](./decisions/003-managed-fields.md).

### External edges

Declare concrete edges on **`ProvisioningDevice.edges`**. The YAML
blueprint provides reusable local port names; peer identities and edge settings
are instance facts supplied by the caller.

One `ProvisioningEdge` declaration can produce one or both directed VideoIPath
edges. Its `EdgeState` is available through `plan.edges` and `result.edges`:
`state.edge` contains the declaration, while `state.edge_ids` lists the directed
server edges.

```yaml
schema_version: 1
defaults:
  topology:
    port_mapping:
      uplink:
        - factory_label: port-1
```

```python
from videoipath_automation_tool.provisioning import (
    DeviceTarget, EdgePatch, PeerEndpoint, PortSelector,
    ProvisioningEdge, ProvisioningDevice, ProvisioningEngine,
)

device = ProvisioningDevice(
    key="device-a",
    label="device-a",
    inventory_id="device1",
    edges=[
        ProvisioningEdge(
            local="uplink",
            peer=PeerEndpoint(
                target=DeviceTarget(device_id="device2"),
                port=PortSelector(factory_label="port-1"),
            ),
            direction="auto",
            fields=EdgePatch(weight=10, label="edge-a"),
        ),
    ],
)
engine = ProvisioningEngine(app)  # an existing VideoIPathApp
plan = engine.plan(device, "external-edges.yml", scope="topology")
print(plan.summary())
result = plan.apply()
for edge in result.edges:
    print(edge.index, edge.status, edge.edge_ids, edge.reason)
```

Use actual VideoIPath ids and factory labels in place of the synthetic values.
For a new device, omit `inventory_id`, supply the normal onboarding facts and
use a blueprint with Inventory configuration and the default `scope="all"`.

`local` can also be a direct selector such as
`PortSelector(port_id="device1.dev.0.port-1")`; no mapping is needed then.
The selected configuration still needs a topology section (`topology: {}` is
sufficient). `scope="inventory"` skips all edge work.

`PortSelector` takes exactly one of `port_id` or `factory_label`, with optional
`kind` to select vertices of a particular kind. A peer can use `ModuleTarget`
to restrict selection to one module. Factory labels are exact matches, not
editable display labels. Candidates in `port_mapping` are tried in order;
an ambiguous candidate fails immediately. Local factory labels can contain
`{module.position}`. Mapping keys must not duplicate `ip_vertex_mapping` keys;
either mapping's keys may be used as `local`.

Schema-v2 inputs work at selector value, selector object, candidate list or
whole mapping positions. Overlays merge mapping keys and replace candidate
lists. Input and literal operators retain their existing atomic replacement
semantics. See [the runnable example](../../examples/07_provisioning/03_external_edges.py)
and [its input-enabled blueprint](../../examples/07_provisioning/external-edges.yml).

| Direction | Behavior relative to the local device |
|---|---|
| `auto` (default) | Create the possible Out→In directions: one edge for a directed port pair, two when both directions exist. |
| `outgoing` | Local Out → peer In. |
| `incoming` | Peer Out → local In. |
| `bidirectional` | Require and create both directions. |

This works with IP and directed media ports. Actual discovered vertex ids are
used, including ids without `.in`/`.out` suffixes. Invalid or ambiguous
directions fail; internal device structure remains driver-owned.

`EdgePatch` applies the same specified fields to each requested direction:
`label`, `description`, `weight`, `capacity`, `bandwidth`, `redundancy_mode`,
`conflict_priority`, `include_formats`, `exclude_formats`,
`bandwidth_weight_factor`, `weight_per_service`, `active`, and `tags`.
Omitted fields remain unmanaged, explicit `null` is rejected, and tags support
replacement lists or `TagDelta`. Use two directed edge declarations when
opposite directions need different settings. Repeated declarations of the same
directed edge combine compatible fields and reject conflicting requirements.

Missing edges are created; existing edges are updated only where managed values
differ. Other edges are never removed, including when `edges=[]`.
Device, vertex and edge changes share the topology transaction. Plans check
peer/edge baselines and uncommitted edit overlap before writing, and verify
written edge fields afterward.

Missing peer devices, modules or ports remain `deferred` while other work can
finish. `fully_resolved` is false; real apply returns `partial` with
`replan_required=True`, even if no writes were needed. Create a **new plan** when
the peer appears. The engine neither provisions nor synchronizes peer devices.
A selector miss among discovered ports and API failures are errors, not deferred
discovery. A dry run reports planned/deferred work without writing.

## 4. Variants

`variants=["secure", "receiver"]` selects an ordered sequence of overlays.
The default is an empty sequence, which uses `defaults` directly. An overlay
may patch Inventory, Topology, or both, and may introduce an absent section.
Unknown or repeated names fail; strings are not accepted as a variant sequence.
The library never selects a variant from source-system facts.

Resolution order ([ADR-007](./decisions/007-typed-inputs.md)):

1. Copy `defaults`.
2. Merge selected variants in order, with later values winning.
3. Bind typed inputs in the effective selected scope.
4. Apply the device's `inventory_overrides`.
5. Validate driver settings, processor parameters, and naming.

Mappings merge by key; scalars and whole lists replace inherited values. Each
naming expression and tag specification replaces as a whole. References and
literal escapes are atomic during merging; their resulting objects are not
merged back into inherited objects. `vertex_processor: null` disables an
inherited processor. Changing its `processor_type` replaces the declaration
and parameters. Changing `driver_id` discards inherited `custom_settings`.
`false`, `0`, `[]`, and `""` remain explicit values.

Every leaf retains its YAML origin (`defaults`, `variant:<name>`, or `instance`).
A referenced value additionally records `|input:<name>`. Source documents and
caller input objects are copied. A plan captures the selected variant order,
effective input values, processor registry, naming, and options for later apply.

## 5. Loading and validation

Pass a file directly to any engine entry point:

```python
from pathlib import Path

engine.validate("blueprints/matrox-convertip.yml")  # optional: validate every variant offline
plan = engine.plan(device, Path("blueprints/matrox-convertip.yml"))
```

Strings always mean file paths, and relative paths use the current working
directory. For raw YAML text, pass `Blueprint.from_yaml(text)` explicitly. Use
`Blueprint.load(path)` when you want to load once and reuse a blueprint across
many calls.

| Constructor | Input |
|---|---|
| `Blueprint.load(path)` | A YAML file. |
| `Blueprint.from_yaml(text, *, source=None)` | YAML text or bytes. `source` names it in error messages. |
| `Blueprint.from_dict(mapping, *, source=None)` | An already-parsed mapping. |

Loading checks document structure, input definitions, and references in all
variants without contacting a server. `blueprint.variant_names()` lists the
common overlay names; there is no named default variant.

Files are loaded once per engine call. A plan retains the loaded configuration,
so `plan.apply()` does not read the file again even if it has changed or been
deleted. Create a new plan to use updated file contents. Missing files raise the
normal file error; YAML validation errors retain their source locations. Loading
errors occur before server access.

YAML parsing is strict. The loader accepts one UTF-8 document with a mapping at
the root, and it rejects duplicate keys, aliases, anchors, merge keys, and custom
tags. Only `true` and `false` are booleans, so `off` and `yes` stay strings.
Timestamps stay strings. A document may be at most 1 MiB, 32 levels deep, and
100,000 nodes. Errors point at the source:

```text
blueprint.yml:24:9
variants.receiver.topology.vertex_processor.params.redundant_streams
Expected a boolean; received a different type.
```

`engine.validate(blueprint, inputs=...)`, or
`blueprint.validate_full(registry, inputs=...)`, checks the base and every
individual variant. Supplying `variants=[...]` checks that specific ordered
combination instead. Required inputs must be provided unless they have defaults
or are replaced in that combination. Arbitrary combinations are checked at
planning time, before server access. Validation also reports unregistered
processors. An Inventory-only plan works without a Topology plugin.

`ProvisioningValidationError.issues` holds `ValidationIssue` records (`path`,
`message`, `code`, `source`, `line`, `column`). Issues carry a path, not the raw
value, so secrets do not leak into errors.

For editor support, use the packaged JSON Schema from `published_json_schema()`,
or the file `videoipath_automation_tool/provisioning/schemas/blueprint-v1.schema.json`.
It describes the built-in processors' parameters and accepts any other
`processor_type` with unconstrained `params`, so it also works with processors
registered elsewhere.

When you use custom processors, export `engine.json_schema()` instead. It limits
`processor_type` to the engine's registered processors (a variant may still omit
it to inherit a processor from `defaults`) and validates each one's `params`, so
editors flag unknown or misspelled processors and invalid parameters.
`Blueprint.json_schema(registry, restrict_processor_types=True)` does the same
without an engine; without the flag, only the parameter schemas are added.

The schema is an editor aid. Runtime validation (`engine.validate`, `plan`) is
authoritative and also catches what the packaged schema lets through.

## 6. Naming

Names are built from the facts you pass in. The engine does not read the label
currently on the server and append to it, so a second apply cannot grow a second
suffix. A rename updates the same server ids.

| Entry | Default (`DEFAULT_NAMING`) |
|---|---|
| `inventory_label` | `{device.label}` |
| `device_label` | `{device.label}` for device targets. A module target does not rename the parent device. |
| `endpoint_label` | `device-a-TX-video-01`, or `device-a-M1-RX-audio-01` when you set a module position |
| `inventory_description`, `device_description`, `endpoint_description` | Left unmanaged |

Available fields:

| Field | Source |
|---|---|
| `device.key`, `device.label`, `device.description` | `ProvisioningDevice` |
| `module.position` | `ProvisioningDevice.module_position` |
| `endpoint.direction`, `endpoint.media`, `endpoint.index`, `endpoint.engine`, `endpoint.program`, `endpoint.leg` | The processor's `EndpointIdentity` |
| `vertex.factory_label`, `vertex.id` | The discovered vertex |
| `attributes.<name>` | Scalar leaves of `ProvisioningDevice.attributes` |
| `inputs.<name>` | Scalar leaves of bound blueprint inputs, including nested object paths |

An expression is a template string, or a tree of blocks:

| Block | YAML form | Python form |
|---|---|---|
| Text | `"literal {field}"` or `{text: ...}` | `"..."` or `Text("...")` |
| Field | `{field: path, format, mapping, prefix, suffix}` | `Field("path", format=..., mapping=..., prefix=..., suffix=...)` |
| Join | `{join: [...], separator, skip_missing}` | `Join(parts=[...], separator=..., skip_missing=...)` |

```yaml
naming:
  endpoint_label:
    join:
      - "{device.label}"
      - field: module.position
        prefix: M
      - "{endpoint.direction}"
      - "{endpoint.media}"
      - "{endpoint.index:02d}"
    separator: "-"
    skip_missing: true
```

```python
from videoipath_automation_tool.provisioning import Field, Join, NamingScheme

scheme = NamingScheme(
    endpoint_label=Join(
        parts=[
            Field("device.label"),
            "E{endpoint.engine}P{endpoint.program}",
            Join(parts=[Field("endpoint.direction"), Field("endpoint.media", mapping={"video": "20", "audio": "30"})]),
            Field("endpoint.index", format="02d"),
        ],
        separator="-",
    )
)
result = engine.apply(device, blueprint, naming=scheme)  # device-a-E0P1-TX20-01
```

Format specs cover alignment, zero padding, minimum width, `d`, and `s`. `02d`
sets a minimum width, so `123` stays `123`.

`skip_missing` skips only an optional value that is absent. An unknown field, a
type error, or a mapping that fails still fails the plan.

**Layering.** For each entry, later sources replace earlier ones: the library
default, then the engine `naming`, then the blueprint (a topology entry replaces
the same inventory entry), then the `naming` argument on that call. An entry is
replaced as a whole; expressions are not merged. Set an entry to `None` to turn
that name off. `NamingScheme.layered(*schemes)` performs the same combination.
Declarative expressions are copied recursively when configuring engine defaults
and capturing a plan, including nested `Join.parts` and `Field.mapping` values.
Later mutations of caller expressions or engine defaults do not change an
existing plan's naming, including work deferred until discovery.

When the blocks cannot express a name, put a computed value in `attributes`, or
pass a Python object with `render(context: NameContext) -> str` (the
`NameRenderer` protocol) for that entry. Python renderers are not available in
YAML. These trusted callbacks are retained by reference: their state and behavior
remain caller-controlled, so keep them stable while a saved plan is pending.

**Checks.** Before any write, every rendered endpoint label is checked. It has to
be non-empty, it cannot contain control characters, and it cannot duplicate
another endpoint label on the same device, including endpoints this plan does not
change. A collision fails and names the colliding ids.
`ApplyOptions(naming_collisions="allow")` lets the write proceed. Names are kept
as rendered. The engine does not truncate them, and it does not append a number
to make them unique.

## 7. Planning and applying

```python
from videoipath_automation_tool.provisioning import ApplyOptions

plan = engine.plan(
    device,
    blueprint,
    scope="all",                     # "all" | "inventory" | "topology"
    variants=["receiver"],
    options=ApplyOptions(sync="add_only", topology_ready_timeout=60),
)
```

**`ApplyOptions`**

| Field | Default | Meaning |
|---|---|---|
| `sync` | `"add_only"` | Topology synchronization policy (below). |
| `inventory_ready_timeout` | `10.0` | Seconds to wait for Inventory to report `reachable=True` before deferred topology rollout. |
| `topology_ready_timeout` | `60.0` | Independent seconds for topology addition, synchronization, and required ports/vertices. Starts after the Inventory gate. |
| `require_reachable` | `True` | Set `False` to bypass the Inventory gate explicitly, for example for mock/static devices. |
| `poll_interval` | `1.0` | Seconds between readiness polls, capped to the remaining stage budget. |
| `naming_collisions` | `"reject"` | `"allow"` lets duplicate endpoint labels through. |
| `write_credentials` | `False` | Write the supplied credentials to an existing record even when nothing else changes (password rotation). |

Planning reads the current state. It does not write, synchronize, stage snapshot
edits, or create catalog entries. The plan lists every phase with the exact
before and after values (secrets redacted), where each value came from
(`default`, `variant:<name>`, `instance`, `naming`, `processor:<id>`,
`override:<id>`), the interface bindings, and any diagnostics.

Apply then runs the phases in this order
([ADR-008](./decisions/008-staged-readiness.md)):

1. `inventory` creates or updates the record. A new id is stored on the result immediately.
2. `inventory_readiness` polls one fresh Inventory status at a time until `reachable=True`, bounded by `inventory_ready_timeout`.
3. `topology_sync` adds the device to the topology, confirms its visibility, and completes permitted synchronization.
4. `discovery` waits for the required topology data (`TopologyNotReadyError`). It shares `topology_ready_timeout` with `topology_sync`.
5. `topology` edits the device, its vertices and resolved external edges in one Inspect transaction, with conflict checking.
6. `module_tags` assigns or unassigns tags as separate actions.
7. `verification` reads the device back. `result.verification` is `confirmed` or `unconfirmed`.

Both timeouts and `poll_interval` must be positive and finite. The Inventory wait
does not consume the topology budget. Polling starts immediately, includes read
time, and starts no further polls or rollout actions after the deadline. An
in-flight request retains its connector-level HTTP timeout; these are readiness
budgets, not a hard total duration for the whole apply.

The Inventory gate applies to deferred rollout with an Inventory record. It uses
the created/bound record, or the physical topology target's Inventory record when
there is no source binding. Inventory-only applies, fully resolved topology,
virtual targets, and module-only edits without their own Inventory binding skip
the gate. `require_reachable=False` also reports the gate as `skipped` and performs
no status requests. Dry runs report pending readiness as `deferred` without polling.

Unavailable status and `reachable=False` remain pending until the Inventory
deadline. Expiry raises `InventoryNotReadyError` through `ProvisioningApplyError`.
Topology expiry raises `TopologyNotReadyError`; the failed phase is
`topology_sync` or `discovery`, depending on what stalled. Messages include the
device ID, stage, timeout, and last condition. Transport, status validation,
unsupported processor configurations, and failed synchronization are errors,
not retryable readiness conditions. Completed operations and known IDs remain
on the result.

A phase with nothing to do is skipped. If the whole apply would change nothing,
it writes nothing.

### Deferred topology work

Sometimes the topology edits depend on work that has not happened yet: a record
this plan creates, a device that is not in the topology yet, a synchronization
that is still pending, or required local topology data that has not appeared.
The plan marks that work `deferred`, and `plan.fully_resolved` is `False`.
During `apply()` the engine first checks Inventory readiness, then uses a fresh
`topology_ready_timeout` budget to compute the exact edits from the blueprint,
parameters, naming, and target captured on the plan. Those edits are recorded on
the result. If that later step fails, the earlier phases stay applied, and the
result says so.

An accepted topology addition is not resubmitted while waiting for visibility.
An accepted synchronization with the same pending changes is polled; newly
reported changes can trigger another permitted synchronization. A retry after
partial discovery binds the known Inventory ID and can plan against incomplete
local topology without recreating the record. Missing peer edges still
require a new plan when the peers become available.

An Inventory update that changes address, alternate addresses, credentials,
generic or custom settings, or `active` is different. The plan marks the topology
phases `deferred` with `fully_resolved` false, but `apply()` stops after
Inventory. It does not poll, and it does not guess when rediscovery has finished.
The result has `status="partial"` and `replan_required=True`, and the call does
not raise. Inventory verification still runs. Plan again once the driver has
rediscovered the device.

If you want to see every write before it happens, split the scopes. Apply
`scope="inventory"`, add the device with `app.inspect.add_devices_to_topology([...])`,
then build a fully resolved `scope="topology"` plan, read it, and call
`plan.apply()`.

### Previewing changes

Use `engine.plan(...)` and `plan.summary()` to review changes without writing.
Phases that depend on earlier writes remain `deferred`. Call `plan.apply()`
to execute the reviewed plan; it re-checks current state before the relevant
writes, as described under [Conflict checks](#conflict-checks).

### Synchronization

| `ApplyOptions.sync` | Behavior |
|---|---|
| `"none"` | The device must already be in the topology. The engine does not add it and does not synchronize it. |
| `"add_only"` | Default. Adds the device and synchronizes new elements only. If that synchronization would update or remove elements, the apply fails. It does not escalate to a full reconcile. |
| `"reconcile"` | A full synchronization is allowed. |

A `syncDevices` failure is an error and is not retried. Adding a device that is
not discovered yet stays `TopologyNotReadyError` and is retried until
`topology_ready_timeout`.

Service conflicts fail the apply. The engine does not invalidate or cancel
services. A module target does not add its parent device to the topology and
does not synchronize it. If the parent is absent, planning fails; if it still
needs a sync, the plan reports a diagnostic.

### Conflict checks

Before writing, the engine reads the Inventory record and the scoped topology
again. If anything the plan relied on has changed, it raises
`ProvisioningConflictError`. Inventory baseline checks also run when the plan
requires no Inventory update; the fresh record remains available to deferred
processors. An Inventory update also repeats the label and address
conflict check. A response with no address item list fails that check. Build a
new plan.

For fully resolved device topology plans using `add_only` or `reconcile`, apply
also reads synchronization status again. Pending synchronization invalidates the
plan and requires a new one; apply does not synchronize and replace the reviewed
work. Lookup failures propagate. `sync="none"` and module targets retain their
policy of working against the current topology without synchronization.

The Inspect transaction then checks
its own baseline, and module tags are read again immediately before their phase.
These checks run in the client, so a short gap between the read and the write
remains. Uncommitted edits on `app.inspect` that overlap the plan are rejected,
so commit or discard them first. Pending edits outside the plan are left as they
are.

A dry run (`plan.apply(dry_run=True)` or `engine.apply(..., dry_run=True)`)
runs the stale-plan, conflict, and pending-edit checks, then returns before writes.
Write phases report `planned`; work dependent on writes remains `deferred`.
`status` is `planned` when changes would run, or `no_change` otherwise. A dry run
does not consume the plan, so that same reviewed plan can subsequently apply.

## 8. Results, errors, and recovery

`plan.apply()` returns an `ApplyResult` when `status` is `succeeded`,
`no_change`, `planned` (dry run), or `partial` with `replan_required`. On
failure it raises `ProvisioningApplyError`. The exception's `.result` has `status`
`failed` (nothing was written), `partial` (something was written), or `unknown`
(a write raised and the client cannot prove the server rejected it). The
original error is `__cause__`.

```python
from videoipath_automation_tool.provisioning import ProvisioningApplyError

try:
    result = engine.apply(device, blueprint)
except ProvisioningApplyError as error:
    result = error.result
    if result.inventory_id:            # created before the failure: bind it, never create again
        save_binding(device.key, result.inventory_id)
    raise
```

What you do next depends on how far the apply got:

- An Inventory update may change the discovered topology. `status` is `partial` and `replan_required` is true. Apply did not raise. Plan again after rediscovery.
- The record was created, then discovery timed out. `status` is `partial` and `inventory_id` is set. Retry with `ProvisioningDevice(..., inventory_id=result.inventory_id)`.
- Topology committed, then a module tag failed. `status` is `partial`. The result lists the committed edits and the tag operations that finished. Replan to finish the rest.
- A write timed out. `status` is `unknown`. Read the server back before you retry. Building a new plan does that read.
- The record was inserted and tracking-id cleanup did not finish. `status` is `unknown` and `inventory_id` is set. Bind that id; do not create again.
- Verification could not confirm the write, or a later phase failed before the topology read-back ran. The write stays applied, `verification` is `"unconfirmed"`, and `ok` is false. `status` stays `succeeded` when the write itself completed. Read the server back before retrying.

The engine does not roll a partial apply back.

All errors derive from `ProvisioningError`:

| Error | Raised when |
|---|---|
| `ProvisioningValidationError` | A document, naming expression, or parameter is invalid. `.issues` lists `ValidationIssue`s; `.codes` lists their codes. |
| `InventoryNotReadyError` | The Inventory readiness deadline expired before the device became reachable. |
| `ProvisioningTargetError` | A binding is missing, ambiguous, or outside the target scope. |
| `ProcessorInputError` | The discovered topology is unsupported. |
| `TopologyNotReadyError` | The discovered topology is still incomplete. Retried while topology work is deferred. |
| `ProvisioningCapabilityError` | The engine cannot perform the requested operation. |
| `ProvisioningConflictError` | The plan is stale: the server changed since planning. |
| `ProvisioningApplyError` | An apply failed. `.result` is the `ApplyResult`. |

## 9. Engine configuration

```python
engine = ProvisioningEngine(
    app,
    processors={"example-org.simple-video": SimpleVideoProcessor},
    options=ApplyOptions(sync="add_only", topology_ready_timeout=60),
    naming=NamingScheme(endpoint_label="{device.label}-{endpoint.direction}-{endpoint.index:02d}"),
)
# equivalent:
engine = ProvisioningEngine(app)
engine.register_processor("example-org.simple-video", SimpleVideoProcessor)
engine.configure(options=ApplyOptions(sync="add_only", topology_ready_timeout=60))
engine.configure(naming=NamingScheme(endpoint_label="{device.label}-{endpoint.direction}-{endpoint.index:02d}"))
```

Constructing the engine does not touch the app or the network. In `configure`,
an omitted argument keeps the current default, a supplied model replaces it, and
`None` restores the library default. Each plan keeps its own copy of the options,
naming, and processor registrations that were in effect when you built it.
Configuration you change afterwards applies to later plans only. Options and
naming passed to `plan()` apply to that plan only. Two engines can share one app
and still keep separate registries. Sharing the app does not make concurrent
writes to the same server safe.

Engine logs go to the `videoipath_automation_tool_provisioning` logger unless you
pass `logger=`.

## 10. Source-system adapters

The library does not depend on NetBox, or on any other source system. An adapter
is an ordinary function you write:

```python
from videoipath_automation_tool.provisioning import ProvisioningDevice, Credentials, ModuleTarget


def to_provisioning_device(record: dict) -> ProvisioningDevice:
    """Translate one source record (already selected and policy-checked by the caller)."""
    return ProvisioningDevice(
        key=str(record["id"]),
        label=record["name"],
        inventory_id=record.get("videoipath_inventory_id"),
        management_address=record["primary_address"],
        alternative_addresses=record.get("alternative_addresses"),
        credentials=Credentials(username=record["user"], password=fetch_secret(record)),
        topology=ModuleTarget(device_id=record["parent_inspect_id"], module_id=record["inspect_module_id"])
        if record.get("inspect_module_id")
        else None,
        module_position=record.get("module_position"),
        attributes={"site": record.get("site")},
    )
```

You keep the decisions around the engine: which blueprint and variant to use,
which address role is allowed, where credentials come from, where returned ids
are stored, which concrete edges to supply, and when the job runs.

## 11. Limits and verification status

- An Inventory round-trip keeps the fields the Inventory models know about, the same way `InventoryApp.update_device` does. Wire fields those models do not parse are dropped.
- `http_auth` is the raw server mode code. Alternative addresses that carry credentials use the `{address, authentication: {user, password}}` entry shape already used by Inventory.
- Tag references are exact catalog ids. The client does not check that the tag exists.
- Endpoint label uniqueness is checked per device, not across the whole system.
- Vertex control configuration waits until its Inspect mapping has been verified.
- Offline tests cover the feature with synthetic Inspect and Inventory data. Try the writes you care about on a test system before you use them in production.
- Also outside this feature: picking a processor from the driver automatically, pruning old configuration, rolling back a partial apply, migrating drivers, inferring physical cabling, provisioning services, and scheduling a fleet.

## 12. Public API index

Everything below is importable from `videoipath_automation_tool.provisioning`.

| Area | Names |
|---|---|
| Engine | `ProvisioningEngine`, `ProvisioningPlan`, `ProvisioningApp` |
| Document | `Blueprint`, `BlueprintConfiguration`, `InputDefinition`, `InputReference`, `LiteralValue`, `InventorySettings`, `CatalogId`, `published_json_schema` |
| Device facts | `ProvisioningDevice`, `Credentials`, `AlternativeAddress`, `DeviceTarget`, `ModuleTarget` |
| Edges | `ProvisioningEdge`, `PeerEndpoint`, `PortSelector`, `EdgeState`, `PortBinding` |
| Patches | `DevicePatch`, `ModulePatch`, `VertexPatch`, `EdgePatch`, `Coordinates`, `TagDelta` |
| Options and results | `ApplyOptions`, `ApplyResult`, `PhaseResult`, `PlannedPhase`, `PlannedOperation`, `FieldChange`, `InterfaceBinding`, `Diagnostic` |
| Naming | `NamingScheme`, `DEFAULT_NAMING`, `Text`, `Field`, `Join`, `NameContext`, `NameRenderer` |
| Processors | `VertexProcessor`, `ProcessorRegistry`, `ProcessingContext`, `ProcessorResult`, `VertexEdit`, `EndpointIdentity`, `SourceFacts`, `DriverContext`, `DeviceRecord`, `ModuleRecord`, `PortRecord`, `VertexRecord`, `MatroxConvertIPProcessor`, `MatroxConvertIPParams` |
| Errors | `ProvisioningError`, `ProvisioningValidationError`, `ValidationIssue`, `ProvisioningTargetError`, `ProcessorInputError`, `InventoryNotReadyError`, `TopologyNotReadyError`, `ProvisioningCapabilityError`, `ProvisioningConflictError`, `ProvisioningApplyError` |

## 13. Migrating from the former API

The declarative configuration layer is now called **Provisioning**. A **Blueprint**
remains a reusable configuration template within it. Update Python imports and
call sites as follows; the former package and class names have no compatibility
aliases.

| Former API | Current API |
|---|---|
| `videoipath_automation_tool.blueprints` (including submodules) | `videoipath_automation_tool.provisioning` |
| `BlueprintEngine` | `ProvisioningEngine` |
| `BlueprintPlan` | `ProvisioningPlan` |
| `BlueprintApp` | `ProvisioningApp` |
| `BlueprintDevice` | `ProvisioningDevice` |
| `BlueprintConnection` | `ProvisioningEdge` |
| `BlueprintError`, `BlueprintValidationError`, `BlueprintTargetError`, `BlueprintCapabilityError`, `BlueprintConflictError`, `BlueprintApplyError` | The same names with the `Provisioning` prefix |
| Logger `videoipath_automation_tool_blueprints` | `videoipath_automation_tool_provisioning` |

`Blueprint`, its configuration and naming models, and the `blueprint` arguments
and `blueprint_digest` plan field keep their names. Documents use
`schema_version: 1`. The packaged schema is
`videoipath_automation_tool/provisioning/schemas/blueprint-v1.schema.json`.

### Edge names

The former Connection names are removed without compatibility aliases. Update
constructors, attribute access and serialized field names:

| Former API | Current API |
|---|---|
| `ProvisioningConnection` | `ProvisioningEdge` |
| `ProvisioningDevice.connections` / `connections=` | `ProvisioningDevice.edges` / `edges=` |
| `ProvisioningPlan.connections` | `ProvisioningPlan.edges` |
| `ApplyResult.connections` | `ApplyResult.edges` |
| `ConnectionState` | `EdgeState` |
| `ConnectionState.connection` | `EdgeState.edge` |

`connections=` is rejected by `ProvisioningDevice`. Blueprint YAML is unchanged;
concrete edges still belong to the device instance. Direction selection, managed
fields and deferred peers keep the same behavior. `edges=[]` removes nothing.

### Readiness options

`ApplyOptions.discovery_timeout` has been removed without an alias. Use
`inventory_ready_timeout=10.0` and `topology_ready_timeout=60.0` instead. Set
`require_reachable=False` explicitly for mock/static devices that do not report
reachability. The new `inventory_readiness` phase precedes `topology_sync`, and
`discovery` now follows synchronization. Consumers of phase lists should use
phase names rather than positional indexes.
