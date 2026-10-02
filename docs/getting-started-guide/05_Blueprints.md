# 05 — Blueprint-driven Configuration

A **blueprint** is a YAML file that describes how one *kind* of device should be
configured: its Inventory driver settings, how it appears in Inspect, and which of
its discovered vertices become named, tagged endpoints. You write it once and
apply it to every real device of that kind.

This page covers the essentials. The complete reference (every field, option,
error, and the API index) is in
[docs/architecture/blueprints](../architecture/blueprints/README.md).

## 1. Key concepts

| Concept | What it is |
|---|---|
| `Blueprint` | The YAML document: an `inventory` and/or `topology` section, each with a `default` entry and optional named **variants**. |
| `BlueprintDevice` | The facts of one real device that only your source system knows: id, label, addresses, credentials. |
| `BlueprintEngine` | Combines a blueprint with a device. `plan()` previews the changes, `apply()` writes them through `app.inventory` and `app.inspect`. |
| Vertex processor | Plugin code that recognizes a driver's discovered vertices and proposes endpoint settings. A Matrox ConvertIP processor is built in. |
| Naming | Rules that build labels from device facts, so re-applying never stacks suffixes. |

Two rules shape everything else:

- **Plan, then apply.** Planning only reads. The plan shows every change with
  before and after values, so you can review it before anything is written.
- **Only what you set is managed.** Fields the blueprint leaves out stay as they
  are on the server. Removing a field from the blueprint does not reset it.

## 2. Quick start

```python
from videoipath_automation_tool import VideoIPathApp
from videoipath_automation_tool.blueprints import BlueprintDevice, BlueprintEngine

app = VideoIPathApp()
engine = BlueprintEngine(app)  # the app has no blueprint attribute; create the engine yourself

device = BlueprintDevice(key="device-a", label="device-a", management_address="192.0.2.10")

plan = engine.plan(device, "blueprints/matrox-convertip.yml")
print(plan.summary())  # review the changes

result = plan.apply()
print(result.status, result.inventory_id)  # persist inventory_id in your source system
```

`engine.apply(device, blueprint)` plans and applies in one call. Pass
`dry_run=True` to `apply()` to run every check without writing. The blueprint
argument is a file path or a `Blueprint` object; PyYAML ships with the package.

On later runs, pass the stored id as `BlueprintDevice(..., inventory_id=...)` so the
engine updates that record instead of creating a new one. When nothing changed,
the apply writes nothing.

## 3. Writing a blueprint

```yaml
schema_version: 1

inventory:
  default:
    driver_id: com.nevion.NMOS_multidevice-0.1.0
    generic_settings: {enable_https: false, http_auth: 0}
    custom_settings: {port: 8080}

topology:
  default:
    device: {icon_size: medium}
    vertex_processor:
      processor_type: matrox.convertip.default
      params:
        redundant_streams: true
        video_sender_tags: [Format~~video-tag-b]
  receiver:
    vertex_processor:
      params: {mode: rx}
```

- **`inventory`** sets the driver and its settings. `custom_settings` are checked
  against the driver schema, so a typo or wrong type fails the plan before any write.
- **`topology`** sets device appearance, the vertex processor and its `params`,
  and optional explicit vertex overrides.
- **Variants** such as `receiver` are patches on top of `default`. Choose them per
  call with `inventory_variant=` and `topology_variant=`.
- **Tags** are exact catalog ids. A list replaces the local tags; `{add: [...], remove: [...]}`
  changes only the listed ones.

Check every variant offline with `engine.validate("blueprints/matrox-convertip.yml")`.
Errors point at the file, line, and field. For editor completion, use the
packaged JSON Schema (`published_json_schema()`), or `engine.json_schema()` when
you register custom processors (it only accepts registered `processor_type` values).

Details: [document reference](../architecture/blueprints/reference.md#3-blueprint-document),
[variants](../architecture/blueprints/reference.md#4-variants),
[loading and validation](../architecture/blueprints/reference.md#5-loading-and-validation).

## 4. Describing a device

```python
from videoipath_automation_tool.blueprints import BlueprintDevice, Credentials, ModuleTarget

device = BlueprintDevice(
    key="source-id-42",                 # your id; never written to VideoIPath
    label="device-a",
    inventory_id="device12",            # omit on first run to create the record
    management_address="192.0.2.10",
    credentials=Credentials(username="test-user", password="test-password"),
    attributes={"site": "site-a"},      # extra facts for naming
)
```

Credentials stay out of YAML and are redacted in plans, results, and errors. To
configure one module of a chassis, pass `topology=ModuleTarget(device_id, module_id)`
with the exact Inspect ids.

Details: [all fields and supported arrangements](../architecture/blueprints/reference.md#2-describing-a-device-blueprintdevice).

## 5. Naming

By default, Inventory and device labels are the device `label`, and endpoint
labels look like `device-a-TX-video-01` (or `device-a-M1-RX-audio-01` with a
module position). Override any entry in the blueprint or per call:

```yaml
topology:
  default:
    naming:
      endpoint_label: "{device.label}-{endpoint.direction}-{endpoint.index:02d}"
```

Endpoint labels must be unique on the device; a collision fails the plan.

Details: [fields, `Text` / `Field` / `Join` blocks, layering](../architecture/blueprints/reference.md#6-naming).

## 6. What apply does

Apply runs these phases in order, skipping any with nothing to do:

1. **inventory** — create or update the record.
2. **discovery** — wait for the driver to discover the device (`discovery_timeout`).
3. **topology_sync** — add the device to the topology or synchronize it.
4. **topology** — commit device and vertex edits in one Inspect transaction.
5. **module_tags** — assign or remove module tags.
6. **verification** — read back what was written.

When the plan creates the Inventory record, the topology edits cannot be known
yet. The plan marks them `deferred` and computes them during apply, after
discovery. If the server changed since planning, apply raises
`BlueprintConflictError`; build a new plan. Behavior is tuned with
`ApplyOptions` (`sync`, `discovery_timeout`, ...).

Details: [planning and applying](../architecture/blueprints/reference.md#7-planning-and-applying).

## 7. Handling failures

Apply never rolls back. If a later phase fails, the earlier ones stay applied and
`BlueprintApplyError.result` tells you how far it got:

```python
from videoipath_automation_tool.blueprints import BlueprintApplyError

try:
    result = engine.apply(device, "blueprints/matrox-convertip.yml")
except BlueprintApplyError as error:
    if error.result.inventory_id:  # record was created: store it so a retry updates, not duplicates
        save_binding(device.key, error.result.inventory_id)
    raise
```

Details: [results, errors, and recovery](../architecture/blueprints/reference.md#8-results-errors-and-recovery).

## 8. Custom processors

When no built-in processor fits a driver, write one: a `VertexProcessor` subclass
with a Pydantic `params_model` that reads the discovered vertices and returns
proposed edits. Register it on the engine and reference its id in YAML:

```python
engine.register_processor("example-org.simple-video", SimpleVideoProcessor)
```

Details: [processor contract and the Matrox built-in](../architecture/blueprints/processors.md).

## Next steps

- Runnable scripts: [docs/examples/07_blueprints](../examples/07_blueprints/)
- Full reference: [reference.md](../architecture/blueprints/reference.md)
- Design and decisions: [concepts.md](../architecture/blueprints/concepts.md)
