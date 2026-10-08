# Provisioning — Vertex processors

A processor reads the vertices one driver discovered and proposes configuration.
The engine validates the proposal, applies naming, compares it with the server,
and writes ([ADR-004](./decisions/004-processors-propose.md)). The rest of the
provisioning reference is in [reference.md](./reference.md).

## 1. Writing a processor

```python
from pydantic import BaseModel, ConfigDict

from videoipath_automation_tool.provisioning import (
    EndpointIdentity, ProcessingContext, ProcessorResult, VertexEdit, VertexPatch, VertexProcessor,
)


class SimpleParams(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    factory_label: str


class SimpleVideoProcessor(VertexProcessor[SimpleParams]):
    params_model = SimpleParams

    def process(self, context: ProcessingContext, params: SimpleParams) -> ProcessorResult:
        vertex = context.require_vertex(kind="codec", factory_label=params.factory_label, vertex_type="In")
        return ProcessorResult(
            vertices=[
                VertexEdit(
                    vertex_id=vertex.id,
                    fields=VertexPatch(use_as_endpoint=True),
                    endpoint=EndpointIdentity(direction="TX", media="video", index=1),
                )
            ]
        )


engine.register_processor("example-org.simple-video", SimpleVideoProcessor)
```

```yaml
defaults:
  topology:
    vertex_processor:
      processor_type: example-org.simple-video
      params: {factory_label: Video Sender}
```

A processor subclasses `VertexProcessor[ParamsT]`, declares `params_model` (a
Pydantic model class), and implements `process(context, params)`. Typed inputs may supply `params` or individual parameter values using
`{$input: name}`. The engine
validates the resolved `params` against `params_model` before calling `process`, and
creates a new processor instance for every run, so an instance may keep
run-local state.

## 2. Input: `ProcessingContext`

`ProcessingContext` is a detached, immutable snapshot of the target scope.

| Field | Content |
|---|---|
| `source` | `SourceFacts`: `key`, `label`, `description`, `module_position`, `attributes` from `ProvisioningDevice`. No credentials. |
| `scope`, `device_id`, `module_id` | `"device"` or `"module"`, and the target ids. |
| `device` | `DeviceRecord`: label, description, factory label, icon, SDP strategy, site, coordinates, tags. |
| `modules`, `ports`, `vertices` | `ModuleRecord`, `PortRecord`, `VertexRecord` tuples, limited to the target scope. A module target sees only its own module. |
| `port_bindings` | Generic `port_mapping` bindings, separate from the legacy IP-only `interfaces`. |
| `interfaces` | The resolved `ip_vertex_mapping` as `InterfaceBinding`s (`key`, `candidate`, `port_id`, `in_vertex_id`, `out_vertex_id`). |
| `owner` | `DriverContext` of the topology owner's Inventory record: `inventory_id`, `driver_id`, `address`, `custom_settings`. |
| `inventory` | The source entity's own `DriverContext` when it differs from the owner (a module with its own record). |

`VertexRecord` carries `id`, `port_id`, `module_id`, `factory_label`,
`port_label`, `vertex_type` (`In`, `Out`, `Internal`, `Undecided`), `kind`
(`codec`, `ip`, `router`, `generic`),
the current `label`, `description`, `use_as_endpoint`, `active`, `sips_mode`,
`tags`, `codec_format`, `media_type`, and the kind-specific fields.

Helpers:

| Method | Returns |
|---|---|
| `vertex(vertex_id)` | The in-scope vertex, or `None`. |
| `find_vertices(*, kind=None, vertex_type=None, factory_label=None, module_id=None)` | Every in-scope match (exact comparisons), ordered by id. |
| `require_vertex(...)` | The single match. Raises `ProcessorInputError` for zero or several. |

## 3. Output: `ProcessorResult`

Return `ProcessorResult(vertices=[VertexEdit, ...], device=DevicePatch | None, module=ModulePatch | None, diagnostics=[...])`.

- `VertexEdit(vertex_id, fields=VertexPatch(...), endpoint=EndpointIdentity(...))`. `VertexPatch` uses the same fields as YAML vertex overrides ([reference §3](./reference.md#vertex-fields)).
- Give each endpoint an `EndpointIdentity(direction, media, index, engine=None, program=None, leg=None)` and let naming build the labels.
- `DevicePatch` is valid on device targets only, `ModulePatch` on module targets only.
- `Diagnostic(level="info" | "warning", code, message, entity_id=None)` shows up on the plan and the result.

The engine rejects ids outside the target scope, device patches on a module
target, and conflicting proposals. Identical duplicate proposals are merged.
Kind-specific fields on the wrong vertex kind (for example `sdp_support` on an IP
vertex) are rejected.

Precedence: explicit `topology.device` values override processor defaults,
naming overrides proposed labels, and explicit `vertices` overrides win over
both.

Raise `TopologyNotReadyError` when discovery is still incomplete (for example,
vertices without an edit form, or no codec vertices yet). While topology work is
deferred, the engine retries only this error, until `topology_ready_timeout`. Raise
`ProcessorInputError` when the layout is unsupported; the apply fails at once.

## 4. Registration

Registration belongs to one engine (`ProvisioningEngine(app, processors={...})` or
`engine.register_processor(id, cls)`). Ids use letters, digits, `.`, `_`, and
`-`. Registering an id that already exists, including a built-in id, fails. YAML
names the registered id; it does not name a Python import path.

A processor is trusted code running in your process. It is not sandboxed. Keep
it free of network calls and source-system imports.

`ProcessorRegistry` is the standalone registry type. It includes the built-ins
by default (`include_builtins=True`) and is what `Blueprint.validate_full(registry)`
and `Blueprint.json_schema(registry, restrict_processor_types=...)` take. `engine.registry` returns a copy of
the engine's registrations.

## 5. Porting a `TopologyDevice`-based processor

- Report problems as returned `Diagnostic` values, or with ordinary logging, rather than through the script-manager logger.
- Read vertices with `context.find_vertices(...)`. The context is a snapshot, so there is no mutable `TopologyDevice` to walk.
- Describe each endpoint with `EndpointIdentity`, and pass module context through `module_position` and `attributes`. Put the label convention in a `NamingScheme` instead of parsing a base label or splitting on `-MODULE-`.
- Propose `VertexEdit` and `DevicePatch` values. The processor should not mutate vertex attributes itself.
- Replace `kwargs` with a strict Pydantic `params_model`, and write the previous defaults into that model. An omitted tag parameter leaves tags unmanaged. Older processors often cleared them when the argument was missing, so set `[]` when clearing is still what you want.
- Keep the processor free of network calls and source-system imports.

## 6. Built-in: `matrox.convertip.default`

Class `MatroxConvertIPProcessor`, parameters `MatroxConvertIPParams`.

The processor recognizes three layouts. **tx** is one video codec vertex and one
audio codec vertex, both `In`. **rx** is the same pair, both `Out`.
**four_split** is four `Out` video receivers whose factory labels are
`Video Receiver 0` through `Video Receiver 3` (indices 1–4), plus one audio
receiver. Media is taken from the codec format, then from `Video` or `Audio` in
the factory label. Any other mix fails. The processor does not skip vertices it
does not recognize.

| Parameter | Default | Meaning |
|---|---|---|
| `mode` | `auto` | `tx`, `rx`, or `four_split` checks that the discovered layout matches. The parameter does not switch the hardware mode. |
| `video_receiver_tags`, `video_sender_tags`, `audio_receiver_tags`, `audio_sender_tags` | omitted | Category tags. Leave the parameter out to leave tags alone, pass `[]` to clear them, or pass `{add, remove}` to add and remove. |
| `redundant_streams` | omitted | `true` sets `SIPSAuto`, `false` sets `NONE`, and omitting the parameter leaves the value alone. `true` requires exactly two streaming IP vertices. Use `ip_vertex_mapping` when the device also has management ports. The processor does not check that paths actually run through that pair. |
| `allow_null_audio_label` | `false` | When `true`, the single codec vertex labelled exactly `null`, which cannot be classified, is accepted as audio. The processor emits a warning diagnostic. |
| `configure_control` | `false` | Not available yet. Setting it raises `ProvisioningCapabilityError`. The Inspect control mapping is still unverified, so control settings on the device stay as they are. |

The proposal enables the endpoints and assigns an `EndpointIdentity` with engine
`0` and program `1`. The factory label becomes the description, joined with the
device description when you supplied one. Senders get SDP support. On a device
target the icon is `gateway` for tx, and `monitor` for rx and four-split.
