# Blueprints — Reference

Complete user reference for `videoipath_automation_tool.blueprints`. For a short
introduction, read the [getting-started page](../../getting-started-guide/05_Blueprints.md)
first. Why the feature works this way is in [concepts.md](./concepts.md) and the
[decisions](./decisions/README.md). Vertex processors, including the built-in
Matrox processor, have their own page: [processors.md](./processors.md).

## Contents

1. [Engine API](#1-engine-api)
2. [Describing a device: `BlueprintDevice`](#2-describing-a-device-blueprintdevice)
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

## 1. Engine API

`BlueprintEngine(app, *, processors=None, options=None, naming=None, logger=None)`
takes any object with `inventory` and `inspect` properties (the `BlueprintApp`
protocol). `VideoIPathApp` satisfies it. The app has no blueprint attribute, so
you construct the engine yourself.

| Member | Purpose |
|---|---|
| `plan(device, blueprint, *, scope="all", inventory_variant="default", topology_variant="default", naming=None, options=None)` | Read-only. Loads and resolves the blueprint, reads current state, returns a `BlueprintPlan`. |
| `apply(device, blueprint, *, ..., dry_run=False)` | Same arguments as `plan`, plus `dry_run`. Identical to `plan(...).apply(dry_run=...)`. |
| `validate(blueprint)` | Offline. Resolves every variant and reports unregistered processors. |
| `json_schema()` | Document JSON Schema for this engine: `processor_type` limited to the registered processors, with each one's parameters. |
| `register_processor(processor_id, processor_cls)` | Registers a processor for this engine only. See [processors.md](./processors.md). |
| `configure(*, options=..., naming=...)` | Replaces engine defaults. See [section 9](#9-engine-configuration). |
| `options`, `naming`, `registry`, `app` | Current defaults. `registry` returns a copy. |

`scope` is `"all"`, `"inventory"`, or `"topology"`. The blueprint argument accepts
a file path string, a `pathlib.Path` (or another `os.PathLike[str]`), or a
`Blueprint` instance.

**`BlueprintPlan`**

| Member | Meaning |
|---|---|
| `apply(*, dry_run=False)` | Re-checks the plan's assumptions and executes it. A dry run performs every check but no write. |
| `summary()` | Human-readable, redacted before/after listing, bindings, diagnostics, and unresolved work. |
| `phases`, `phase(name)` | `PlannedPhase` records (`planned`, `no_change`, `deferred`, `skipped`) with their `PlannedOperation`s and `FieldChange`s. |
| `has_changes` | `True` when any phase is `planned` or `deferred`. |
| `fully_resolved` | `False` when topology work is deferred until apply. |
| `interface_bindings`, `diagnostics`, `skipped_sections` | Resolved `ip_vertex_mapping`, warnings, and sections the scope skipped. |
| `source_key`, `scope`, `inventory_variant`, `topology_variant`, `inventory_id`, `topology_target`, `driver_id`, `driver_schema_version`, `processor_type`, `blueprint_digest` | Identity of what was planned. |

A plan is an in-memory object bound to the app it was built with. It also holds
unredacted Inventory values for the write, so it is not a document you save and
replay elsewhere.

**`ApplyResult`**

| Field | Meaning |
|---|---|
| `status` | `succeeded`, `no_change`, `planned` (dry run), `failed`, `partial`, or `unknown`. |
| `ok` | `True` for `succeeded`, `no_change`, and `planned`. |
| `inventory_id`, `topology_device_id`, `module_id`, `source_key` | Ids involved. Persist `inventory_id` in your source system. |
| `phases`, `phase(name)` | `PhaseResult` per phase: `completed`, `no_change`, `skipped`, `failed`, `unknown`, `not_run`, `planned`, or `deferred`. |
| `interface_bindings`, `diagnostics` | As on the plan, after deferred work was materialized. |
| `materialized` | `True` when deferred topology work was computed during apply. |
| `verification`, `verification_detail` | `confirmed`, `unconfirmed`, or `not_applicable`. |
| `dry_run` | Whether this was a dry run. |

## 2. Describing a device: `BlueprintDevice`

`BlueprintDevice` is one device, module, or virtual device, plus the facts only
your source system knows.

| Field | Meaning |
|---|---|
| `key` | Your id for this device, for example the id in the source system, so you can match a result back to it. It is not written to VideoIPath. |
| `label`, `description` | Instance facts used by naming. |
| `inventory_id` | The Inventory record that already belongs to this device. If that record is missing, planning fails. The engine will not create a second one in its place. Leave the field out when a selected inventory section should create the record. |
| `management_address`, `alternative_addresses` | Connection addresses. The driver decides the string format, so these are not always IP addresses. An alternative address is a string or an `AlternativeAddress(address, credentials)`. Leave the field out to leave the server value alone. Pass `[]` to clear alternative addresses. A supplied list is the full desired set and also replaces per-address credentials: a plain string carries none, so an existing credential is cleared unless that address is an `AlternativeAddress`. An address listed twice fails. |
| `credentials` | Runtime `Credentials(username, password)`. Credentials stay out of YAML, and the engine redacts them in plans, results, and errors. |
| `topology` | `DeviceTarget(device_id)` or `ModuleTarget(device_id, module_id)`, using exact Inspect ids. Leave it out to target the Inventory id, including an id this same plan creates. |
| `module_position` | Module context you supply for naming and mappings. It is a string, such as `"0"`, `"A1"`, or `"1/2"`. |
| `inventory_overrides` | Per-device Inventory settings that are not secrets (`InventorySettings`): `custom_settings`, `generic_settings`, `snmp`, `metadata`, `active`. Applied after the selected variant. |
| `attributes` | JSON facts you own. Scalar leaves are available to naming as `attributes.<name>`, and processors see them on `context.source`. |

`BlueprintDevice.from_inventory(inventory_device, key=None)` binds an existing
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

inventory:
  default:
    driver_id: com.nevion.NMOS_multidevice-0.1.0
    generic_settings: {enable_https: false, http_auth: 0}
    custom_settings: {port: 8080, disable_rx_sdp_with_null: true}

topology:
  default:
    device: {icon_size: medium}
    ip_vertex_mapping:
      stream-a: [P1]
      stream-b: [P2]
    vertex_processor:
      processor_type: matrox.convertip.default
      params:
        redundant_streams: true
        video_receiver_tags: [Format~~video-tag-a]
        video_sender_tags: [Format~~video-tag-b]
  receiver:
    vertex_processor:
      params: {mode: rx}
```

`schema_version` must be `1`. `inventory` and `topology` are each optional, and
the file needs at least one of them. A section you include must contain a
`default` entry. Variant names start with a letter or digit and may contain
letters, digits, `_`, `.`, and `-`.

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

## 4. Variants

`inventory_variant` and `topology_variant` are chosen independently. Both default
to `default`. An unknown name fails, and the error lists the names that exist.
There is no silent fallback to `default`.

A named entry is a patch on top of that section's `default`
([ADR-006](./decisions/006-variant-merge.md)):

- Mappings merge by key. A scalar replaces the inherited value. A list replaces the inherited list as a whole, so the two lists are not concatenated.
- A naming expression replaces the inherited expression. A tag specification does the same.
- `vertex_processor: null` turns off a processor inherited from `default`. A different `processor_type` replaces the whole processor declaration, parameters included.
- A different `driver_id` drops the inherited `custom_settings`.
- `false`, `0`, `[]`, and `""` are values you set on purpose. Leaving the key out is a different choice.

Per-device `inventory_overrides` are applied after the variant.

The loader rejects `extends`, imports, YAML anchors, and merge keys. Each document
is complete by itself. When you need to preprocess one, build a dictionary in
Python and pass it to `Blueprint.from_dict`.

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

These check the document structure only. They do not connect to a server.
`blueprint.variant_names("inventory" | "topology")` lists the variants.

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
topology.receiver.vertex_processor.params.redundant_streams
Expected a boolean; received a different type.
```

`engine.validate(blueprint)`, or `blueprint.validate_full(registry)`, resolves
every variant, including variants you are not about to apply, and reports
processors that are not registered. Planning only needs the processors for the
scope you selected, so an Inventory-only run works without a topology plugin.

`BlueprintValidationError.issues` holds `ValidationIssue` records (`path`,
`message`, `code`, `source`, `line`, `column`). Issues carry a path, not the raw
value, so secrets do not leak into errors.

For editor support, use the packaged JSON Schema from `published_json_schema()`,
or the file `videoipath_automation_tool/blueprints/schemas/blueprint-v1.schema.json`.
It describes the built-in processors' parameters and accepts any other
`processor_type` with unconstrained `params`, so it also works with processors
registered elsewhere.

When you use custom processors, export `engine.json_schema()` instead. It limits
`processor_type` to the engine's registered processors (a variant may still omit
it to inherit the `default` processor) and validates each one's `params`, so
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
| `device.key`, `device.label`, `device.description` | `BlueprintDevice` |
| `module.position` | `BlueprintDevice.module_position` |
| `endpoint.direction`, `endpoint.media`, `endpoint.index`, `endpoint.engine`, `endpoint.program`, `endpoint.leg` | The processor's `EndpointIdentity` |
| `vertex.factory_label`, `vertex.id` | The discovered vertex |
| `attributes.<name>` | Scalar leaves of `BlueprintDevice.attributes` |

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
from videoipath_automation_tool.blueprints import Field, Join, NamingScheme

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

When the blocks cannot express a name, put a computed value in `attributes`, or
pass a Python object with `render(context: NameContext) -> str` (the
`NameRenderer` protocol) for that entry. Python renderers are not available in
YAML.

**Checks.** Before any write, every rendered endpoint label is checked. It has to
be non-empty, it cannot contain control characters, and it cannot duplicate
another endpoint label on the same device, including endpoints this plan does not
change. A collision fails and names the colliding ids.
`ApplyOptions(naming_collisions="allow")` lets the write proceed. Names are kept
as rendered. The engine does not truncate them, and it does not append a number
to make them unique.

## 7. Planning and applying

```python
from videoipath_automation_tool.blueprints import ApplyOptions

plan = engine.plan(
    device,
    blueprint,
    scope="all",                     # "all" | "inventory" | "topology"
    inventory_variant="default",
    topology_variant="receiver",
    options=ApplyOptions(sync="add_only", discovery_timeout=60),
)
```

**`ApplyOptions`**

| Field | Default | Meaning |
|---|---|---|
| `sync` | `"add_only"` | Topology synchronization policy (below). |
| `discovery_timeout` | `30.0` | Seconds to wait for discovery during apply. |
| `poll_interval` | `1.0` | Seconds between discovery polls. |
| `naming_collisions` | `"reject"` | `"allow"` lets duplicate endpoint labels through. |

Planning reads the current state. It does not write, synchronize, stage snapshot
edits, or create catalog entries. The plan lists every phase with the exact
before and after values (secrets redacted), where each value came from
(`default`, `variant:<name>`, `instance`, `naming`, `processor:<id>`,
`override:<id>`), the interface bindings, and any diagnostics.

Apply then runs the phases in this order
([ADR-002](./decisions/002-plan-then-apply.md)):

1. `inventory` creates or updates the record. A new id is stored on the result immediately.
2. `discovery` waits, bounded by `discovery_timeout`.
3. `topology_sync` adds the device to the topology, or synchronizes it.
4. `topology` edits the device and its vertices in one Inspect transaction, with conflict checking.
5. `module_tags` assigns or unassigns tags as separate actions.
6. `verification` reads the device back. `result.verification` is `confirmed` or `unconfirmed`.

A phase with nothing to do is skipped. If the whole apply would change nothing,
it writes nothing.

### Deferred topology work

Sometimes the topology edits depend on work that has not happened yet: a record
this plan creates, Inventory changes that may alter discovery (address,
alternative addresses, credentials, generic or custom settings, `active`), a
device that is not in the topology yet, or a synchronization that is still
pending. The plan marks that work `deferred`, and `plan.fully_resolved` is
`False`. During `apply()` the engine polls for discovery up to
`discovery_timeout`, then computes the exact edits from the blueprint,
parameters, naming, and target captured on the plan. Those edits are recorded on
the result. If that later step fails, the earlier phases stay applied, and the
result says so.

If you want to see every write before it happens, split the scopes. Apply
`scope="inventory"`, add the device with `app.inspect.add_devices_to_topology([...])`,
then build a fully resolved `scope="topology"` plan, read it, and call
`plan.apply()`.

### Dry runs

`plan.apply(dry_run=True)` runs the same stale-plan, conflict, and pending-edit
checks, then returns before any write. Deferred topology stays `deferred`,
because those edits depend on writes the dry run does not perform. `status` is
`planned` when writes would have run, and `no_change` otherwise. You can dry-run a
plan and apply that same plan afterwards.

### Synchronization

| `ApplyOptions.sync` | Behavior |
|---|---|
| `"none"` | The device must already be in the topology. The engine does not add it and does not synchronize it. |
| `"add_only"` | Default. Adds the device and synchronizes new elements only. If that synchronization would update or remove elements, the apply fails. It does not escalate to a full reconcile. |
| `"reconcile"` | A full synchronization is allowed. |

Service conflicts fail the apply. The engine does not invalidate or cancel
services. A module target does not add its parent device to the topology and
does not synchronize it. If the parent is absent, planning fails; if it still
needs a sync, the plan reports a diagnostic.

### Conflict checks

Before writing, the engine reads the Inventory record and the scoped topology
again. If anything the plan relied on has changed, it raises
`BlueprintConflictError`. Build a new plan. The Inspect transaction then checks
its own baseline, and module tags are read again immediately before their phase.
These checks run in the client, so a short gap between the read and the write
remains. Uncommitted edits on `app.inspect` that overlap the plan are rejected,
so commit or discard them first. Pending edits outside the plan are left as they
are.

## 8. Results, errors, and recovery

`plan.apply()` returns an `ApplyResult` when `status` is `succeeded` or
`no_change` (`planned` on a dry run). On failure it raises `BlueprintApplyError`.
The exception's `.result` has `status` `failed` (nothing was written), `partial`
(something was written), or `unknown` (a write raised and the client cannot prove
the server rejected it). The original error is `__cause__`.

```python
from videoipath_automation_tool.blueprints import BlueprintApplyError

try:
    result = engine.apply(device, blueprint)
except BlueprintApplyError as error:
    result = error.result
    if result.inventory_id:            # created before the failure: bind it, never create again
        save_binding(device.key, result.inventory_id)
    raise
```

What you do next depends on how far the apply got:

- The record was created, then discovery timed out. `status` is `partial` and `inventory_id` is set. Retry with `BlueprintDevice(..., inventory_id=result.inventory_id)`.
- Topology committed, then a module tag failed. `status` is `partial`. The result lists the committed edits and the tag operations that finished. Replan to finish the rest.
- A write timed out. `status` is `unknown`. Read the server back before you retry. Building a new plan does that read.
- Verification could not confirm the write, or a later phase failed before the topology read-back ran. The write stays applied, and `verification` is `"unconfirmed"`.

The engine does not roll a partial apply back.

All errors derive from `BlueprintError`:

| Error | Raised when |
|---|---|
| `BlueprintValidationError` | A document, naming expression, or parameter is invalid. `.issues` lists `ValidationIssue`s; `.codes` lists their codes. |
| `BlueprintTargetError` | A binding is missing, ambiguous, or outside the target scope. |
| `ProcessorInputError` | The discovered topology is unsupported or still incomplete. |
| `BlueprintCapabilityError` | The engine cannot perform the requested operation. |
| `BlueprintConflictError` | The plan is stale: the server changed since planning. |
| `BlueprintApplyError` | An apply failed. `.result` is the `ApplyResult`. |

## 9. Engine configuration

```python
engine = BlueprintEngine(
    app,
    processors={"example-org.simple-video": SimpleVideoProcessor},
    options=ApplyOptions(sync="add_only", discovery_timeout=60),
    naming=NamingScheme(endpoint_label="{device.label}-{endpoint.direction}-{endpoint.index:02d}"),
)
# equivalent:
engine = BlueprintEngine(app)
engine.register_processor("example-org.simple-video", SimpleVideoProcessor)
engine.configure(options=ApplyOptions(sync="add_only", discovery_timeout=60))
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

Engine logs go to the `videoipath_automation_tool_blueprints` logger unless you
pass `logger=`.

## 10. Source-system adapters

The library does not depend on NetBox, or on any other source system. An adapter
is an ordinary function you write:

```python
from videoipath_automation_tool.blueprints import BlueprintDevice, Credentials, ModuleTarget


def to_blueprint_device(record: dict) -> BlueprintDevice:
    """Translate one source record (already selected and policy-checked by the caller)."""
    return BlueprintDevice(
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
are stored, how cables are built, and when the job runs.

## 11. Limits and verification status

- An Inventory round-trip keeps the fields the Inventory models know about, the same way `InventoryApp.update_device` does. Wire fields those models do not parse are dropped.
- `http_auth` is the raw server mode code. Alternative addresses that carry credentials use the `{address, authentication: {user, password}}` entry shape already used by Inventory.
- Tag references are exact catalog ids. The client does not check that the tag exists.
- Endpoint label uniqueness is checked per device, not across the whole system.
- Vertex control configuration waits until its Inspect mapping has been verified.
- Offline tests cover the feature with synthetic Inspect and Inventory data. Try the writes you care about on a test system before you use them in production.
- Also outside this feature: picking a processor from the driver automatically, pruning old configuration, rolling back a partial apply, migrating drivers, inferring cables or edges, provisioning services, and scheduling a fleet.

## 12. Public API index

Everything below is importable from `videoipath_automation_tool.blueprints`.

| Area | Names |
|---|---|
| Engine | `BlueprintEngine`, `BlueprintPlan`, `BlueprintApp` |
| Document | `Blueprint`, `InventorySettings`, `CatalogId`, `published_json_schema` |
| Device facts | `BlueprintDevice`, `Credentials`, `AlternativeAddress`, `DeviceTarget`, `ModuleTarget` |
| Patches | `DevicePatch`, `ModulePatch`, `VertexPatch`, `Coordinates`, `TagDelta` |
| Options and results | `ApplyOptions`, `ApplyResult`, `PhaseResult`, `PlannedPhase`, `PlannedOperation`, `FieldChange`, `InterfaceBinding`, `Diagnostic` |
| Naming | `NamingScheme`, `DEFAULT_NAMING`, `Text`, `Field`, `Join`, `NameContext`, `NameRenderer` |
| Processors | `VertexProcessor`, `ProcessorRegistry`, `ProcessingContext`, `ProcessorResult`, `VertexEdit`, `EndpointIdentity`, `SourceFacts`, `DriverContext`, `DeviceRecord`, `ModuleRecord`, `PortRecord`, `VertexRecord`, `MatroxConvertIPProcessor`, `MatroxConvertIPParams` |
| Errors | `BlueprintError`, `BlueprintValidationError`, `ValidationIssue`, `BlueprintTargetError`, `ProcessorInputError`, `BlueprintCapabilityError`, `BlueprintConflictError`, `BlueprintApplyError` |
