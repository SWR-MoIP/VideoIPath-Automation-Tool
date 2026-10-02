"""Strict YAML loading for blueprints.

Starts from PyYAML's safe loading (a dedicated ``SafeLoader`` subclass; PyYAML is never modified
globally) and adds the project's requirements:

- exactly one UTF-8 document with a mapping root, within size and depth limits;
- duplicate keys rejected at any depth; mapping keys must be strings;
- no aliases, anchors, merge keys, or custom tags;
- implicit scalars restricted to ``true``/``false``, ``null``/``~``, decimal integers, and plain
  decimal floats — ``off``, ``yes``, timestamps, octal/sexagesimal numbers stay strings;
- every node's line/column is recorded so validation errors point at the source.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, ClassVar

import yaml

from videoipath_automation_tool.blueprints.errors import BlueprintValidationError, ValidationIssue

MAX_DOCUMENT_BYTES = 1024 * 1024
MAX_DEPTH = 32
MAX_NODES = 100_000


def read_blueprint_file(path: Path) -> bytes:
    """Read a blueprint file, enforcing the size limit before parsing."""
    with path.open("rb") as handle:
        data = handle.read(MAX_DOCUMENT_BYTES + 1)
    if len(data) > MAX_DOCUMENT_BYTES:
        raise _error(f"document exceeds {MAX_DOCUMENT_BYTES} bytes", str(path))
    return data


def parse_yaml(
    text: str | bytes, *, source: str | None = None
) -> tuple[dict[str, Any], dict[tuple[Any, ...], tuple[int, int]]]:
    """Parse one strict YAML document; returns ``(data, locations)`` where ``locations`` maps each
    document path to its 1-based ``(line, column)``."""
    if isinstance(text, bytes):
        if len(text) > MAX_DOCUMENT_BYTES:
            raise _error(f"document exceeds {MAX_DOCUMENT_BYTES} bytes", source)
        try:
            text = text.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise _error(f"document is not valid UTF-8 ({exc.reason} at byte {exc.start})", source) from None
    elif len(text.encode("utf-8")) > MAX_DOCUMENT_BYTES:
        raise _error(f"document exceeds {MAX_DOCUMENT_BYTES} bytes", source)
    text = text.removeprefix("﻿")

    loader = _StrictLoader(text)
    try:
        node = loader.get_single_node()
    except _LoaderError as exc:
        raise _error(exc.message, source, exc.mark) from None
    except RecursionError:
        raise _error(f"document nesting exceeds depth {MAX_DEPTH}", source) from None
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        problem = getattr(exc, "problem", None) or str(exc)
        raise _error(f"invalid YAML: {problem}", source, mark) from None
    finally:
        loader.dispose()

    if node is None:
        raise _error("document is empty", source)
    builder = _Builder(source)
    data = builder.build(node, (), depth=0)
    if not isinstance(data, dict):
        raise _error("the document root must be a mapping", source, node.start_mark)
    return data, builder.locations


# --- Internal ---

_BOOL_RE = re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$")
_NULL_RE = re.compile(r"^(?:~|null|Null|NULL|)$")
_INT_RE = re.compile(r"^[-+]?(?:0|[1-9][0-9]*)$")
_FLOAT_RE = re.compile(r"^[-+]?(?:[0-9]+\.[0-9]*|\.[0-9]+)(?:[eE][-+]?[0-9]+)?$|^[-+]?[0-9]+[eE][-+]?[0-9]+$")

_TAG_STR = "tag:yaml.org,2002:str"
_TAG_BOOL = "tag:yaml.org,2002:bool"
_TAG_NULL = "tag:yaml.org,2002:null"
_TAG_INT = "tag:yaml.org,2002:int"
_TAG_FLOAT = "tag:yaml.org,2002:float"
_TAG_MAP = "tag:yaml.org,2002:map"
_TAG_SEQ = "tag:yaml.org,2002:seq"


class _LoaderError(Exception):
    def __init__(self, message: str, mark: Any) -> None:
        self.message = message
        self.mark = mark
        super().__init__(message)


class _StrictLoader(yaml.SafeLoader):
    """Safe loader with restricted implicit scalars that rejects aliases and anchors."""

    yaml_implicit_resolvers: ClassVar[dict[str, list[Any]]] = {}

    def compose_node(self, parent: Any, index: Any) -> Any:
        if self.check_event(yaml.AliasEvent):
            raise _LoaderError("aliases are not supported", self.peek_event().start_mark)
        event = self.peek_event()
        if getattr(event, "anchor", None) is not None:
            raise _LoaderError("anchors are not supported", event.start_mark)
        return super().compose_node(parent, index)


for _tag, _regexp, _first in (
    (_TAG_BOOL, _BOOL_RE, list("tTfF")),
    (_TAG_NULL, _NULL_RE, ["~", "n", "N", ""]),
    (_TAG_INT, _INT_RE, list("-+0123456789")),
    (_TAG_FLOAT, _FLOAT_RE, list("-+.0123456789")),
):
    _StrictLoader.add_implicit_resolver(_tag, _regexp, _first)


class _Builder:
    """Constructs plain Python data from the composed node tree, enforcing the strict rules."""

    def __init__(self, source: str | None) -> None:
        self._source = source
        self._nodes = 0
        self.locations: dict[tuple[Any, ...], tuple[int, int]] = {}

    def build(self, node: Any, path: tuple[Any, ...], depth: int) -> Any:
        self._nodes += 1
        if self._nodes > MAX_NODES:
            raise _error(f"document exceeds {MAX_NODES} nodes", self._source, node.start_mark)
        if depth > MAX_DEPTH:
            raise _error(f"document nesting exceeds depth {MAX_DEPTH}", self._source, node.start_mark)
        self.locations[path] = (node.start_mark.line + 1, node.start_mark.column + 1)

        if isinstance(node, yaml.MappingNode):
            if node.tag != _TAG_MAP:
                raise _error(f"unsupported tag {node.tag!r}", self._source, node.start_mark)
            result: dict[str, Any] = {}
            for key_node, value_node in node.value:
                if key_node.tag == "tag:yaml.org,2002:merge" or (key_node.value == "<<" and key_node.style is None):
                    raise _error("merge keys ('<<') are not supported", self._source, key_node.start_mark)
                if not isinstance(key_node, yaml.ScalarNode) or key_node.tag != _TAG_STR:
                    raise _error("mapping keys must be strings", self._source, key_node.start_mark)
                key = key_node.value
                if key in result:
                    raise _error(f"duplicate key {key!r}", self._source, key_node.start_mark)
                result[key] = self.build(value_node, path + (key,), depth + 1)
            return result
        if isinstance(node, yaml.SequenceNode):
            if node.tag != _TAG_SEQ:
                raise _error(f"unsupported tag {node.tag!r}", self._source, node.start_mark)
            return [self.build(item, path + (index,), depth + 1) for index, item in enumerate(node.value)]
        return self._scalar(node)

    def _scalar(self, node: Any) -> Any:
        tag, value = node.tag, node.value
        if tag == _TAG_STR:
            return value
        if tag == _TAG_NULL and _NULL_RE.match(value):
            return None
        if tag == _TAG_BOOL and _BOOL_RE.match(value):
            return value.lower() == "true"
        if tag == _TAG_INT and _INT_RE.match(value):
            return int(value)
        if tag == _TAG_FLOAT and _FLOAT_RE.match(value):
            return float(value)
        raise _error(f"unsupported scalar tag or value for tag {tag!r}", self._source, node.start_mark)


def _error(message: str, source: str | None, mark: Any = None) -> BlueprintValidationError:
    return BlueprintValidationError(
        ValidationIssue(
            message=message,
            code="yaml.invalid",
            source=source,
            line=mark.line + 1 if mark is not None else None,
            column=mark.column + 1 if mark is not None else None,
        )
    )


__all__ = ["MAX_DEPTH", "MAX_DOCUMENT_BYTES", "MAX_NODES", "parse_yaml", "read_blueprint_file"]
