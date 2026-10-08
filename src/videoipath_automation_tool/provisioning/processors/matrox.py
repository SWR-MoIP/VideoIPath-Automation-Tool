"""Built-in processor for Matrox ConvertIP devices (``matrox.convertip.default``).

Supported layouts (recognized from codec composition and direction, never from a vertex count alone):

- ``tx``: one video and one audio transmitter.
- ``rx``: one video and one audio receiver.
- ``four_split``: four video receivers with distinct indices 1–4 (parsed from the factory label
  ``Video Receiver <n>``, zero-based on the device) and one audio receiver.

For the observed codec convention an ``In`` codec vertex is a transmitter and an ``Out`` codec vertex
a receiver; this interpretation is local to this processor. Media is taken from structured codec
information first (``codecFormat`` / specific type) and only then from ``Video`` / ``Audio`` words in
the factory label. ``mode`` asserts the recognized layout; it does not switch hardware between TX and
RX (that is a device/driver change followed by synchronization and replanning).

Proposed edits: endpoint enablement, semantic endpoint identity (engine ``0``, program ``1``), the
factory label as description (joined with the caller's device description when given), sender SDP
support, SIPS mode and category tags only when requested, and a ``gateway`` (TX) / ``monitor`` (RX,
four-split) icon as a device-target default. Vertex control is not configured: its Inspect mapping
is unverified, so ``configure_control: true`` fails with a capability error.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict

from videoipath_automation_tool.provisioning.errors import (
    ProcessorInputError,
    ProvisioningCapabilityError,
    TopologyNotReadyError,
)
from videoipath_automation_tool.provisioning.models import (
    DevicePatch,
    Diagnostic,
    EndpointIdentity,
    ProcessorResult,
    TagSpec,
    VertexEdit,
    VertexPatch,
)
from videoipath_automation_tool.provisioning.processors import ProcessingContext, VertexProcessor, VertexRecord

Layout = Literal["tx", "rx", "four_split"]


class MatroxConvertIPParams(BaseModel):
    """Parameters. Omitted tag parameters leave local tags unchanged (``[]`` clears them); an omitted
    ``redundant_streams`` preserves the SIPS mode (``true`` → ``SIPSAuto``, ``false`` → ``NONE``)."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    mode: Literal["auto", "tx", "rx", "four_split"] = "auto"
    video_receiver_tags: TagSpec | None = None
    video_sender_tags: TagSpec | None = None
    audio_receiver_tags: TagSpec | None = None
    audio_sender_tags: TagSpec | None = None
    redundant_streams: bool | None = None
    allow_null_audio_label: bool = False
    """Compatibility for a driver defect that labels the single audio endpoint ``null``."""
    configure_control: bool = False


class MatroxConvertIPProcessor(VertexProcessor[MatroxConvertIPParams]):
    params_model = MatroxConvertIPParams

    def process(self, context: ProcessingContext, params: MatroxConvertIPParams) -> ProcessorResult:
        if params.configure_control:
            raise ProvisioningCapabilityError(
                "Matrox ConvertIP: configuring vertex control is not supported until its Inspect mapping is verified; "
                "remove 'configure_control' to preserve the current control settings."
            )
        diagnostics: list[Diagnostic] = []

        unknown = [vertex.id for vertex in context.vertices if vertex.kind is None]
        if unknown:
            raise TopologyNotReadyError(
                f"Matrox ConvertIP: unknown kind for vertices {', '.join(sorted(unknown))} in {context.scope_label} "
                "(no edit form; incomplete discovery?)."
            )
        codecs = context.find_vertices(kind="codec")
        if not codecs:
            raise TopologyNotReadyError(
                f"Matrox ConvertIP: no codec vertices in {context.scope_label} (incomplete discovery or unsupported layout)."
            )
        media = self._classify_media(codecs, params, diagnostics)
        direction = self._direction(codecs)
        layout = self._layout(direction, codecs, media)
        if params.mode != "auto" and params.mode != layout:
            raise ProcessorInputError(
                f"Matrox ConvertIP: mode '{params.mode}' was requested but {context.scope_label} has a '{layout}' layout."
            )
        indices = self._indices(layout, codecs, media)

        if params.redundant_streams:
            diagnostics.append(self._check_redundancy(context, codecs[0].vertex_type or ""))

        edits = [
            VertexEdit(
                vertex_id=vertex.id,
                fields=self._fields(vertex, direction, media[vertex.id], params, context),
                endpoint=EndpointIdentity(
                    direction=direction, media=media[vertex.id], index=indices[vertex.id], engine=0, program=1
                ),
            )
            for vertex in codecs
        ]
        device = (
            DevicePatch(icon_type="gateway" if layout == "tx" else "monitor") if context.scope == "device" else None
        )
        diagnostics.append(Diagnostic(code="matrox.layout", message=f"Recognized '{layout}' layout."))
        return ProcessorResult(vertices=edits, device=device, diagnostics=diagnostics)

    # --- Recognition ---

    @staticmethod
    def _classify_media(
        codecs: list[VertexRecord], params: MatroxConvertIPParams, diagnostics: list[Diagnostic]
    ) -> dict[str, str]:
        media: dict[str, str] = {}
        unknown: list[VertexRecord] = []
        for vertex in codecs:
            kind = _structured_media(vertex) or _label_media(vertex.factory_label)
            if kind is None:
                unknown.append(vertex)
            else:
                media[vertex.id] = kind

        if unknown and params.allow_null_audio_label:
            null_labelled = [v for v in unknown if (v.factory_label or "").strip().lower() == "null"]
            if len(unknown) == 1 and len(null_labelled) == 1 and "audio" not in media.values():
                vertex = null_labelled[0]
                media[vertex.id] = "audio"
                unknown = []
                diagnostics.append(
                    Diagnostic(
                        level="warning",
                        code="matrox.null_audio_label",
                        message="Treated the single codec vertex labelled 'null' as the audio endpoint "
                        "(allow_null_audio_label compatibility workaround).",
                        entity_id=vertex.id,
                    )
                )
        if unknown:
            labels = ", ".join(f"{v.id} ({v.factory_label!r})" for v in unknown)
            raise ProcessorInputError(f"Matrox ConvertIP: cannot classify codec vertices as video or audio: {labels}.")
        return media

    @staticmethod
    def _direction(codecs: list[VertexRecord]) -> str:
        directions = {vertex.vertex_type for vertex in codecs}
        if len(directions) != 1 or next(iter(directions)) not in _DIRECTIONS:
            raise ProcessorInputError(
                f"Matrox ConvertIP: codec vertices must all be 'In' (TX) or all 'Out' (RX); found {sorted(map(str, directions))}."
            )
        return _DIRECTIONS[next(iter(directions))]

    @staticmethod
    def _layout(direction: str, codecs: list[VertexRecord], media: dict[str, str]) -> Layout:
        videos = sum(1 for vertex in codecs if media[vertex.id] == "video")
        audios = sum(1 for vertex in codecs if media[vertex.id] == "audio")
        if (videos, audios) == (1, 1):
            return "tx" if direction == "TX" else "rx"
        if direction == "RX" and (videos, audios) == (4, 1):
            return "four_split"
        raise ProcessorInputError(
            f"Matrox ConvertIP: unsupported {direction} layout with {videos} video and {audios} audio codec vertices."
        )

    @staticmethod
    def _indices(layout: Layout, codecs: list[VertexRecord], media: dict[str, str]) -> dict[str, int]:
        indices = {vertex.id: 1 for vertex in codecs}
        if layout != "four_split":
            return indices
        for vertex in codecs:
            if media[vertex.id] != "video":
                continue
            match = _FOUR_SPLIT_INDEX.search((vertex.factory_label or "").strip())
            if match is None:
                raise ProcessorInputError(
                    f"Matrox ConvertIP: four-split video vertex {vertex.id} has no 'Video Receiver <n>' index "
                    f"in its factory label {vertex.factory_label!r}."
                )
            indices[vertex.id] = int(match.group(1)) + 1
        found = sorted(indices[v.id] for v in codecs if media[v.id] == "video")
        if found != [1, 2, 3, 4]:
            raise ProcessorInputError(
                f"Matrox ConvertIP: four-split video indices must be 0–3 on the device (1–4 after normalization); found {found}."
            )
        return indices

    @staticmethod
    def _check_redundancy(context: ProcessingContext, codec_type: str) -> Diagnostic:
        stream_type = "Out" if codec_type == "In" else "In"
        if context.interfaces:
            streaming = [
                vertex_id
                for binding in context.interfaces
                if (vertex_id := binding.out_vertex_id if stream_type == "Out" else binding.in_vertex_id) is not None
            ]
            origin = "ip_vertex_mapping"
        else:
            streaming = [vertex.id for vertex in context.find_vertices(kind="ip", vertex_type=stream_type)]
            origin = "in-scope IP vertices"
        if len(streaming) != 2:
            raise ProcessorInputError(
                f"Matrox ConvertIP: redundant_streams requires exactly two '{stream_type}' streaming IP vertices "
                f"({origin}); found {len(streaming)}. Use ip_vertex_mapping to select the streaming pair."
            )
        return Diagnostic(
            code="matrox.redundancy",
            message=f"Redundant streaming pair {', '.join(sorted(streaming))} ({origin}); "
            "stream paths through the pair are not verified by this processor.",
        )

    # --- Proposals ---

    @staticmethod
    def _fields(
        vertex: VertexRecord, direction: str, media: str, params: MatroxConvertIPParams, context: ProcessingContext
    ) -> VertexPatch:
        description = vertex.factory_label or ""
        if context.source.description:
            description = f"{description} | {context.source.description}" if description else context.source.description
        fields: dict[str, object] = {"use_as_endpoint": True, "description": description}
        if direction == "TX":
            fields["sdp_support"] = True
        if params.redundant_streams is not None:
            fields["sips_mode"] = "SIPSAuto" if params.redundant_streams else "NONE"
        tags = {
            ("video", "TX"): params.video_sender_tags,
            ("video", "RX"): params.video_receiver_tags,
            ("audio", "TX"): params.audio_sender_tags,
            ("audio", "RX"): params.audio_receiver_tags,
        }[(media, direction)]
        if tags is not None:
            fields["tags"] = tags
        return VertexPatch(**fields)


# --- Internal ---

_DIRECTIONS = {"In": "TX", "Out": "RX"}
_FOUR_SPLIT_INDEX = re.compile(r"Video Receiver\s+(\d+)$", re.IGNORECASE)
_VIDEO_WORD = re.compile(r"\bvideo\b", re.IGNORECASE)
_AUDIO_WORD = re.compile(r"\baudio\b", re.IGNORECASE)


def _structured_media(vertex: VertexRecord) -> str | None:
    for value in (vertex.codec_format, vertex.media_type):
        if value and value.lower() in ("video", "audio"):
            return value.lower()
    return None


def _label_media(label: str | None) -> str | None:
    if not label:
        return None
    is_video, is_audio = bool(_VIDEO_WORD.search(label)), bool(_AUDIO_WORD.search(label))
    if is_video == is_audio:
        return None
    return "video" if is_video else "audio"


__all__ = ["MatroxConvertIPParams", "MatroxConvertIPProcessor"]
