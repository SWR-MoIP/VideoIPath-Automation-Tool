"""Naming blocks, templates, layering, and rendering errors."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from videoipath_automation_tool.blueprints import (
    DEFAULT_NAMING,
    BlueprintValidationError,
    Field,
    Join,
    NameContext,
    NamingScheme,
    Text,
)
from videoipath_automation_tool.blueprints.naming import BlueprintNaming, render_name


def _context(position: str | None = None, index: int = 1, **attributes: object) -> NameContext:
    return NameContext(
        device={"key": "key-a", "label": "device-a", "description": None},
        module={"position": position},
        endpoint={"direction": "TX", "media": "video", "index": index, "engine": 0, "program": 1, "leg": None},
        vertex={"factory_label": "Video Sender", "id": "device1.0.vs.v"},
        attributes=dict(attributes),
    )


def test_default_endpoint_label_with_optional_module() -> None:
    expression = DEFAULT_NAMING.endpoint_label
    assert render_name("endpoint_label", expression, _context()) == "device-a-TX-video-01"
    assert render_name("endpoint_label", expression, _context(position="0")) == "device-a-M0-TX-video-01"
    assert render_name("endpoint_label", expression, _context(position="A1", index=123)) == "device-a-MA1-TX-video-123"


def test_engine_program_media_code_convention() -> None:
    scheme = NamingScheme(
        endpoint_label=Join(
            parts=[
                Field("device.label"),
                "E{endpoint.engine}P{endpoint.program}",
                Join(
                    parts=[Field("endpoint.direction"), Field("endpoint.media", mapping={"video": "20", "audio": "30"})]
                ),
                Field("endpoint.index", format="02d"),
            ],
            separator="-",
        )
    )
    assert render_name("endpoint_label", scheme.endpoint_label, _context()) == "device-a-E0P1-TX20-01"


def test_yaml_structured_form_and_text_block() -> None:
    naming = BlueprintNaming.model_validate(
        {
            "endpoint_label": {
                "join": ["{device.label}", {"field": "attributes.site", "suffix": "!"}, {"text": "x"}],
                "separator": "_",
            }
        }
    )
    assert render_name("endpoint_label", naming.endpoint_label, _context(site="site-ä")) == "device-a_site-ä!_x"
    assert render_name("device_label", Text("fixed"), _context()) == "fixed"
    assert render_name("device_label", "{{literal}}-{device.label}", _context()) == "{literal}-device-a"


@pytest.mark.parametrize(
    ("entry", "expression", "message"),
    [
        ("inventory_label", "{device.label!r}", "invalid field reference"),
        ("inventory_label", "{device.label[0]}", "invalid field reference"),
        ("inventory_label", "{device.nope}", "unknown field"),
        ("inventory_label", "{endpoint.index}", "not available for this entry"),
        ("endpoint_label", "{endpoint.index:x}", "unsupported format"),
        ("endpoint_label", "{endpoint.index:{width}}", "nested braces"),
        ("endpoint_label", "{device.label", "unclosed"),
        ("endpoint_label", "a}b", "single '}'"),
    ],
)
def test_static_validation(entry: str, expression: str, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        NamingScheme(**{entry: expression})


@pytest.mark.parametrize(
    ("expression", "code"),
    [
        ("{device.description}", "naming.missing"),
        (Join(parts=["{device.description}"], skip_missing=False), "naming.missing"),
        (Field("endpoint.media", mapping={"audio": "30"}), "naming.render"),
        (Field("device.label", format="02d"), "naming.render"),
        (Field("attributes.nested"), "naming.render"),
        (Text(" "), "naming.empty"),
        (Text("a\nb"), "naming.invalid"),
    ],
)
def test_render_errors(expression: object, code: str) -> None:
    with pytest.raises(BlueprintValidationError) as info:
        render_name("endpoint_label", expression, _context(nested={"a": 1}))
    assert info.value.codes == [code]


def test_skip_missing_only_skips_absent_values() -> None:
    join = Join(
        parts=["{device.label}", "{device.description}", "{attributes.missing}"], separator="-", skip_missing=True
    )
    assert render_name("endpoint_label", join, _context()) == "device-a"
    failing = Join(parts=["{device.label}", Field("endpoint.media", mapping={"audio": "30"})], skip_missing=True)
    with pytest.raises(BlueprintValidationError, match="no mapping"):
        render_name("endpoint_label", failing, _context())


def test_python_renderer_and_layering() -> None:
    class Upper:
        def render(self, context: NameContext) -> str:
            return str(context.value("device.label")).upper()

    engine = NamingScheme(device_label=Upper())
    call = NamingScheme(endpoint_label=None)
    layered = NamingScheme.layered(DEFAULT_NAMING, engine, None, call)
    assert render_name("device_label", layered.device_label, _context()) == "DEVICE-A"
    assert layered.endpoint_label is None
    assert layered.inventory_label == "{device.label}"
    assert set(layered.entries()) == {"inventory_label", "device_label", "endpoint_label"}
