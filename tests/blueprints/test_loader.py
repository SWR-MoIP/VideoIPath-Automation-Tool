"""Strict YAML loading: safety rules, scalar resolution, and source locations."""

from __future__ import annotations

from pathlib import Path

import pytest

from videoipath_automation_tool.blueprints import Blueprint, BlueprintValidationError
from videoipath_automation_tool.blueprints.loader import MAX_DOCUMENT_BYTES, parse_yaml

MINIMAL = "schema_version: 1\ntopology:\n  default: {}\n"


def _issue(text: str | bytes) -> str:
    with pytest.raises(BlueprintValidationError) as info:
        parse_yaml(text, source="bp.yml")
    return str(info.value)


def test_scalars_are_resolved_strictly() -> None:
    data, _ = parse_yaml("a: true\nb: off\nc: yes\nd: 2024-01-01\ne: 010\nf: 1.5\ng: ~\nh: 07:30\ni: -3\n")
    assert data == {
        "a": True,
        "b": "off",
        "c": "yes",
        "d": "2024-01-01",
        "e": "010",
        "f": 1.5,
        "g": None,
        "h": "07:30",
        "i": -3,
    }


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("a: 1\na: 2\n", "duplicate key 'a'"),
        ("a:\n  b:\n    c: 1\n    c: 2\n", "duplicate key 'c'"),
        ("a: &anchor 1\n", "anchors are not supported"),
        ("<<: {a: 1}\n", "merge keys"),
        ("a: !custom 1\n", "unsupported scalar tag"),
        ("a: !!python/object:os.system x\n", "unsupported scalar tag"),
        ("- 1\n- 2\n", "root must be a mapping"),
        ("a: 1\n---\nb: 2\n", "another document"),
        ("1: one\n", "mapping keys must be strings"),
        ("? [a]\n: 1\n", "mapping keys must be strings"),
        ("", "document is empty"),
        ("a: [1\n", "invalid YAML"),
    ],
)
def test_rejected_documents(text: str, message: str) -> None:
    assert message in _issue(text)


def test_aliases_are_rejected() -> None:
    assert "anchors are not supported" in _issue("a: &x [1]\nb: *x\n")


def test_size_depth_and_encoding_limits() -> None:
    assert "exceeds" in _issue(b"a: " + b"x" * MAX_DOCUMENT_BYTES)
    assert "depth" in _issue("a: " + "[" * 40 + "]" * 40 + "\n")
    assert "UTF-8" in _issue(b"a: \xff\xfe\n")


def test_errors_carry_source_line_and_column() -> None:
    text = "schema_version: 1\ntopology:\n  default:\n    vertex_processor:\n      processor_type: x\n      params:\n        flag: 1\n      extra: 2\n"
    with pytest.raises(BlueprintValidationError) as info:
        Blueprint.from_yaml(text, source="bp.yml")
    issue = info.value.issues[0]
    assert (issue.source, issue.line, issue.column, issue.path) == (
        "bp.yml",
        8,
        14,
        "topology.default.vertex_processor.extra",
    )
    assert str(issue).startswith("bp.yml:8:14\ntopology.default.vertex_processor.extra\n")


def test_load_from_file_and_bytes(tmp_path: Path) -> None:
    path = tmp_path / "bp.yml"
    path.write_text(MINIMAL, encoding="utf-8")
    assert Blueprint.load(path).variant_names("topology") == ["default"]
    assert Blueprint.from_yaml(MINIMAL.encode("utf-8")).topology is not None
    assert Blueprint.from_yaml("\ufeff" + MINIMAL).topology is not None
