# 05 — Provisioning

**Provisioning** is a declarative configuration layer on top of the VideoIPath
SDK. It automates device configuration in an Infrastructure as Code style:
combine reusable templates with device facts, review a plan, then apply it
through the existing Inventory and Inspect apps.

A **blueprint** is a YAML file that describes how one *kind* of device should be
configured: its Inventory driver settings, how it appears in Inspect, and which of
its discovered vertices become named, tagged endpoints. You write it once and
apply it to every real device of that kind. Blueprints are the templates used
within provisioning.

This page covers the essentials. The complete reference (every field, option,
error, and the API index) is in
[docs/architecture/provisioning](../architecture/provisioning/README.md).
For existing Python integrations, see the
[API migration notes](../architecture/provisioning/reference.md#13-migrating-from-the-former-api).

## 1. Key concepts

| Concept | What it is |
|---|---|
| `Blueprint` | The v2 YAML document: typed `inputs`, Inventory/Topology `defaults`, and optional ordered variant overlays. |
| `ProvisioningDevice` | The facts of one real device that only your source system knows: id, label, addresses, credentials. |
| `ProvisioningEngine` | Combines a blueprint with a device. `plan()` previews the changes, `apply()` writes them through `app.inventory` and `app.inspect`. |
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
from videoipath_automation_tool.provisioning import ProvisioningDevice, ProvisioningEngine

app = VideoIPathApp()
engine = ProvisioningEngine(app)  # the app has no provisioning attribute; create the engine yourself

device = ProvisioningDevice(key="device-a", label="device-a", management_address="192.0.2.10")

plan = engine.plan(device, "blueprints/matrox-convertip.yml")
print(plan.summary())  # review the changes

result = plan.apply()
print(result.status, result.inventory_id)  # persist inventory_id in your source system
```

`engine.apply(device, blueprint)` plans and applies in one call. For a read-only
preview, use `engine.plan(...)` and `plan.summary()`. Call `plan.apply()` when
you want to execute the reviewed changes. The blueprint
argument is a file path or a `Blueprint` object; PyYAML ships with the package.

On later runs, pass the stored id as `ProvisioningDevice(..., inventory_id=...)` so the
engine updates that record instead of creating a new one. When nothing changed,
the apply writes nothing.

### External edges

Supply concrete edges through `ProvisioningDevice.edges`. Each
`ProvisioningEdge` contains a local port (a mapping key or `PortSelector`),
a `PeerEndpoint` identifying the other device/module and port, and optional
`EdgePatch` settings. The blueprint's `defaults.topology.port_mapping` maps
reusable local names to discovered ports. `plan(...).apply()` creates or updates
the requested edges along with device and vertex settings.

`direction="auto"` derives one or both directions from the actual port vertices.
Existing unrelated edges remain unchanged. Missing peers are reported per
edge as `deferred`; the result is `partial` with `replan_required=True`.
Build a new plan after the peer becomes available.

See the [complete example](../examples/07_provisioning/03_external_edges.py)
and [edge reference](../architecture/provisioning/reference.md#external-edges).

## 3. Writing a blueprint

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
  topology:
    device:
      icon_size: medium
    vertex_processor:
      processor_type: matrox.convertip.default
      params:
        redundant_streams: true
        video_sender_tags:
        - Format~~video-tag-b
variants:
  receiver:
    topology:
      vertex_processor:
        params:
          mode: rx
```

- **`inventory`** sets the driver and its settings. `custom_settings` are checked
  against the driver schema, so a typo or wrong type fails the plan before any write.
- **`topology`** sets device appearance, the vertex processor and its `params`,
  and optional explicit vertex overrides.
- **Variants** such as `receiver` patch `defaults`. Choose an ordered sequence per
  call with `variants=["secure", "receiver"]`; later values win.
- **Tags** are exact catalog ids. A list replaces the local tags; `{add: [...], remove: [...]}`
  changes only the listed ones.

- **Inputs** declare strict types and optional defaults. Use `port: {$input: api_port}`
  and pass `inputs={"api_port": 8080}` to the engine. Naming can use scalar input
  leaves such as `{inputs.location.code}`. Values can come from any caller or data source.

Check the base and every individual variant offline with `engine.validate("blueprints/matrox-convertip.yml")`.
Use `engine.validate(path, inputs=..., variants=[...])` to check one combined
selection. Errors point at the file, line, and field. For editor completion, use the
packaged JSON Schema (`published_json_schema()`), or `engine.json_schema()` when
you register custom processors (it only accepts registered `processor_type` values).

Details: [document reference](../architecture/provisioning/reference.md#3-blueprint-document),
[variants](../architecture/provisioning/reference.md#4-variants),
[loading and validation](../architecture/provisioning/reference.md#5-loading-and-validation).

## 4. Describing a device

```python
from videoipath_automation_tool.provisioning import ProvisioningDevice, Credentials, ModuleTarget

device = ProvisioningDevice(
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

Details: [all fields and supported arrangements](../architecture/provisioning/reference.md#2-describing-a-device-provisioningdevice).

## 5. Naming

By default, Inventory and device labels are the device `label`, and endpoint
labels look like `device-a-TX-video-01` (or `device-a-M1-RX-audio-01` with a
module position). Override any entry in the blueprint or per call:

```yaml
defaults:
  topology:
    naming:
      endpoint_label: "{device.label}-{endpoint.direction}-{endpoint.index:02d}"
```

Endpoint labels must be unique on the device; a collision fails the plan.

Details: [fields, `Text` / `Field` / `Join` blocks, layering](../architecture/provisioning/reference.md#6-naming).

## 6. What apply does

Apply runs these phases in order, skipping any with nothing to do:

1. **inventory** — create or update the record.
2. **inventory_readiness** — wait up to `inventory_ready_timeout` (10 seconds) for `reachable=True`.
3. **topology_sync** — add the device to the topology, confirm its visibility, and synchronize it.
4. **discovery** — wait for the required ports and vertices. This shares a fresh `topology_ready_timeout` (60 seconds) with topology synchronization.
5. **topology** — commit device, vertex and resolved external edge edits in one Inspect transaction.
6. **module_tags** — assign or remove module tags.
7. **verification** — read back what was written.

When the plan creates the Inventory record, the topology edits cannot be known
yet. The plan marks them `deferred` and computes them during apply, after
discovery.

Inventory and topology have independent budgets; each polls every `poll_interval`
(1 second by default). For mock/static devices, use
`ApplyOptions(require_reachable=False)` to bypass the Inventory gate. Inventory-only
applies and already resolved topology do not wait for reachability. Dry runs never
poll. A timeout identifies the stalled phase and retains the created Inventory ID
so a later plan can continue from that record.

When an update changes the address, alternate addresses, credentials, generic or
custom settings, or whether the device is active, apply stops after Inventory.
The result is `partial` with `replan_required`. Plan again after the driver has
rediscovered the device.

If the server changed since planning, apply raises
`ProvisioningConflictError`; build a new plan. Behavior is tuned with
`ApplyOptions` (`sync`, `inventory_ready_timeout`, `topology_ready_timeout`, ...).

Details: [planning and applying](../architecture/provisioning/reference.md#7-planning-and-applying).

## 7. Handling failures

Apply never rolls back. If a later phase fails, the earlier ones stay applied and
`ProvisioningApplyError.result` tells you how far it got:

```python
from videoipath_automation_tool.provisioning import ProvisioningApplyError

try:
    result = engine.apply(device, "blueprints/matrox-convertip.yml")
except ProvisioningApplyError as error:
    if error.result.inventory_id:  # record was created: store it so a retry updates, not duplicates
        save_binding(device.key, error.result.inventory_id)
    raise
```

Details: [results, errors, and recovery](../architecture/provisioning/reference.md#8-results-errors-and-recovery).

## 8. Custom processors

When no built-in processor fits a driver, write one: a `VertexProcessor` subclass
with a Pydantic `params_model` that reads the discovered vertices and returns
proposed edits. Register it on the engine and reference its id in YAML:

```python
engine.register_processor("example-org.simple-video", SimpleVideoProcessor)
```

Details: [processor contract and the Matrox built-in](../architecture/provisioning/processors.md).

## Next steps

- Runnable scripts: [docs/examples/07_provisioning](../examples/07_provisioning/)
- Full reference: [reference.md](../architecture/provisioning/reference.md)
- Design and decisions: [concepts.md](../architecture/provisioning/concepts.md)
