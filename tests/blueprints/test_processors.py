"""Processor contract, registry, detached context, and the built-in Matrox ConvertIP processor."""

from __future__ import annotations

import random
from typing import Any

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from tests.blueprints.conftest import FakeInspectServer, make_inspect_app, matrox_layout
from videoipath_automation_tool.blueprints import (
    BlueprintCapabilityError,
    BlueprintValidationError,
    DeviceTarget,
    InterfaceBinding,
    MatroxConvertIPParams,
    MatroxConvertIPProcessor,
    ModuleTarget,
    ProcessingContext,
    ProcessorInputError,
    ProcessorRegistry,
    ProcessorResult,
    SourceFacts,
    TagDelta,
    TopologyNotReadyError,
    VertexProcessor,
)
from videoipath_automation_tool.blueprints.inspect import InspectGateway, build_context


def _context(
    layout: dict[str, Any],
    *,
    module: str | None = None,
    description: str | None = None,
    interfaces: tuple[InterfaceBinding, ...] = (),
    mutate: Any = None,
) -> ProcessingContext:
    server = FakeInspectServer()
    server.install(layout)
    if mutate is not None:
        mutate(server)
    target = (
        ModuleTarget(device_id=layout["device_id"], module_id=module)
        if module
        else DeviceTarget(device_id=layout["device_id"])
    )
    scope = InspectGateway(make_inspect_app(server)).read_scope(target)
    source = SourceFacts(key="key-a", label="device-a", description=description)
    return build_context(scope, source, list(interfaces), None, None)


def _process(context: ProcessingContext, **params: Any) -> ProcessorResult:
    return MatroxConvertIPProcessor().process(context, MatroxConvertIPParams(**params))


def _by_label(result: ProcessorResult, context: ProcessingContext) -> dict[str, Any]:
    return {context.vertex(edit.vertex_id).factory_label: edit for edit in result.vertices}


# --- Registry ---


class _Params(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class _Noop(VertexProcessor[_Params]):
    params_model = _Params

    def process(self, context: ProcessingContext, params: _Params) -> ProcessorResult:
        return ProcessorResult()


def test_registry_rules() -> None:
    mapping = {"example-org.noop": _Noop}
    registry = ProcessorRegistry(mapping)
    mapping["example-org.other"] = _Noop
    assert registry.ids() == ["example-org.noop", "matrox.convertip.default"]

    with pytest.raises(ValueError, match="already registered"):
        registry.register("matrox.convertip.default", _Noop)
    with pytest.raises(ValueError, match="Invalid processor id"):
        registry.register("bad id", _Noop)
    with pytest.raises(TypeError, match="VertexProcessor subclass"):
        registry.register("example-org.x", object)  # type: ignore[arg-type]
    with pytest.raises(BlueprintValidationError, match="Available: example-org.noop, matrox.convertip.default"):
        registry.get("missing")

    clone = registry.copy()
    clone.register("example-org.clone", _Noop)
    assert "example-org.clone" not in registry
    assert registry.params_schema("matrox.convertip.default")["title"] == "MatroxConvertIPParams"


def test_params_validation_carries_paths() -> None:
    with pytest.raises(BlueprintValidationError) as info:
        ProcessorRegistry().validate_params("matrox.convertip.default", {"mode": "sideways"}, ("params",))
    assert info.value.issues[0].path == "params.mode"


# --- Context ---


def test_context_is_detached_scoped_and_immutable() -> None:
    layout = matrox_layout("device1", "rx")
    context = _context(layout)
    with pytest.raises(ValidationError):
        context.vertices[0].label = "changed"  # type: ignore[misc]
    assert len(context.find_vertices(kind="codec")) == 2
    assert context.require_vertex(factory_label="Video Receiver", vertex_type="Out").kind == "codec"
    with pytest.raises(ProcessorInputError, match="found 6 vertices"):
        context.require_vertex(kind="ip")


def test_module_context_contains_only_module_vertices() -> None:
    layout = matrox_layout("device1", "rx", module="device1.dev.1")
    sibling = matrox_layout("device1", "tx", module="device1.dev.2")
    layout["node"]["modules"].update(sibling["node"]["modules"])
    layout["vertex_forms"].update(sibling["vertex_forms"])
    context = _context(layout, module="device1.dev.2")
    assert context.scope == "module"
    assert {v.module_id for v in context.vertices} == {"device1.dev.2"}
    assert {v.vertex_type for v in context.find_vertices(kind="codec")} == {"In"}


# --- Matrox recognition ---


def test_tx_layout() -> None:
    context = _context(matrox_layout("device1", "tx"), description="studio-a")
    result = _process(context, video_sender_tags=["video-tag-b"])
    edits = _by_label(result, context)
    video = edits["Video Sender"]
    assert video.endpoint.model_dump() == {
        "direction": "TX",
        "media": "video",
        "index": 1,
        "engine": 0,
        "program": 1,
        "leg": None,
    }
    assert video.fields.managed() == {
        "use_as_endpoint": True,
        "description": "Video Sender | studio-a",
        "sdp_support": True,
        "tags": ["video-tag-b"],
    }
    assert "tags" not in edits["Audio Sender"].fields.managed()
    assert result.device.icon_type == "gateway"


def test_rx_layout_without_sdp_and_with_sips() -> None:
    context = _context(matrox_layout("device1", "rx"))
    result = _process(context, redundant_streams=False, audio_receiver_tags=[])
    audio = _by_label(result, context)["Audio Receiver"]
    assert audio.fields.managed() == {
        "use_as_endpoint": True,
        "description": "Audio Receiver",
        "sips_mode": "NONE",
        "tags": [],
    }
    assert result.device.icon_type == "monitor"


def test_four_split_layout_normalizes_indices() -> None:
    context = _context(matrox_layout("device1", "four_split"))
    result = _process(context, mode="four_split", video_receiver_tags=TagDelta(add=["video-tag-c"]))
    edits = _by_label(result, context)
    assert [edits[f"Video Receiver {i}"].endpoint.index for i in range(4)] == [1, 2, 3, 4]
    assert edits["Audio Receiver"].endpoint.index == 1
    assert edits["Video Receiver 0"].fields.tags == TagDelta(add=["video-tag-c"])


def test_processing_is_deterministic_regardless_of_order() -> None:
    context = _context(matrox_layout("device1", "four_split"))
    shuffled = list(context.vertices)
    random.Random(4).shuffle(shuffled)
    other = context.model_copy(update={"vertices": tuple(shuffled)})
    assert _process(context) == _process(other)


@pytest.mark.parametrize(
    ("mutate", "error", "message"),
    [
        (lambda s: s.vertex_forms.pop("device1.0.ar.v"), TopologyNotReadyError, "unknown kind"),
        (lambda s: _relabel(s, "device1.0.vr3.v", "Video Receiver 7"), ProcessorInputError, "indices"),
        (
            lambda s: _relabel(s, "device1.0.vr3.v", "Video Receiver"),
            ProcessorInputError,
            "no 'Video Receiver <n>' index",
        ),
        (
            lambda s: _set_media(s, "device1.0.ar.v", "video"),
            ProcessorInputError,
            "unsupported RX layout with 5 video and 0 audio",
        ),
    ],
)
def test_invalid_four_split_layouts(mutate: Any, error: type[Exception], message: str) -> None:
    context = _context(matrox_layout("device1", "four_split"), mutate=mutate)
    with pytest.raises(error, match=message):
        _process(context)


def test_mode_must_agree_with_observed_layout() -> None:
    with pytest.raises(ProcessorInputError, match="mode 'rx' was requested"):
        _process(_context(matrox_layout("device1", "tx")), mode="rx")


def test_mixed_directions_and_missing_codecs_fail() -> None:
    def mixed(server: FakeInspectServer) -> None:
        node_port = server.nodes["device1"]["modules"]["device1.dev.0"]["ports"]["device1.dev.0.as"]
        node_port["vertexInfo"]["vertexType"] = "Out"

    with pytest.raises(ProcessorInputError, match="all be 'In'"):
        _process(_context(matrox_layout("device1", "tx"), mutate=mixed))

    def no_codecs(server: FakeInspectServer) -> None:
        for form in server.vertex_forms.values():
            form["fields"]["typeFields"]["type"] = "ip"

    with pytest.raises(TopologyNotReadyError, match="no codec vertices"):
        _process(_context(matrox_layout("device1", "tx"), mutate=no_codecs))


def test_label_fallback_and_null_audio_workaround() -> None:
    def unstructured(label: str) -> Any:
        def mutate(server: FakeInspectServer) -> None:
            for vertex_id in ("device1.0.vs.v", "device1.0.as.v"):
                type_fields = server.vertex_forms[vertex_id]["fields"]["typeFields"]
                type_fields["generic"]["codecFormat"] = None
                type_fields["specific"]["type"] = None
            _relabel(server, "device1.0.as.v", label)

        return mutate

    context = _context(matrox_layout("device1", "tx"), mutate=unstructured("Main Audio"))
    assert _by_label(_process(context), context)["Main Audio"].endpoint.media == "audio"

    context = _context(matrox_layout("device1", "tx"), mutate=unstructured("null"))
    with pytest.raises(ProcessorInputError, match="cannot classify"):
        _process(context)
    result = _process(context, allow_null_audio_label=True)
    assert _by_label(result, context)["null"].endpoint.media == "audio"
    assert any(d.code == "matrox.null_audio_label" for d in result.diagnostics)

    context = _context(matrox_layout("device1", "tx"), mutate=unstructured("null-ish"))
    with pytest.raises(ProcessorInputError, match="cannot classify"):
        _process(context, allow_null_audio_label=True)


def test_redundancy_validation() -> None:
    context = _context(matrox_layout("device1", "tx"))
    with pytest.raises(ProcessorInputError, match="exactly two 'Out' streaming IP vertices"):
        _process(context, redundant_streams=True)  # MGMT counts without an explicit mapping
    bindings = (
        InterfaceBinding(
            key="a", candidate="P1", port_id="p1", in_vertex_id="device1.0.P1.in", out_vertex_id="device1.0.P1.out"
        ),
        InterfaceBinding(
            key="b", candidate="P2", port_id="p2", in_vertex_id="device1.0.P2.in", out_vertex_id="device1.0.P2.out"
        ),
    )
    result = _process(_context(matrox_layout("device1", "tx"), interfaces=bindings), redundant_streams=True)
    assert any("device1.0.P1.out, device1.0.P2.out" in d.message for d in result.diagnostics)


def test_control_configuration_is_an_explicit_capability_error() -> None:
    with pytest.raises(BlueprintCapabilityError, match="control"):
        _process(_context(matrox_layout("device1", "tx")), configure_control=True)


def test_module_target_proposes_no_device_patch() -> None:
    layout = matrox_layout("device1", "rx", module="device1.dev.3")
    result = _process(_context(layout, module="device1.dev.3"))
    assert result.device is None


# --- Helpers ---


def _relabel(server: FakeInspectServer, vertex_id: str, label: str) -> None:
    for module in server.nodes["device1"]["modules"].values():
        for port in module["ports"].values():
            if port["vertexInfo"].get("id") == vertex_id:
                port["label"] = label


def _set_media(server: FakeInspectServer, vertex_id: str, media: str) -> None:
    type_fields = server.vertex_forms[vertex_id]["fields"]["typeFields"]
    type_fields["generic"]["codecFormat"] = media.capitalize()
    type_fields["specific"]["type"] = media
