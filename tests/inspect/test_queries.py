from __future__ import annotations

import urllib.parse

import pytest

from videoipath_automation_tool.apps.inspect.api import queries
from videoipath_automation_tool.apps.inspect.errors import InspectQueryTooLongError


def test_all_queries_within_length_limit() -> None:
    for build in (queries.device_skeleton, queries.edge_skeleton, queries.paths_section, queries.collector_full):
        path = build()
        assert len(path) < queries.MAX_QUERY_LENGTH
        assert path.startswith("/rest/v2/data/status/collector/")


def test_device_skeleton_suppresses_modules_and_selects_skeleton_fields() -> None:
    path = queries.device_skeleton()
    decoded = urllib.parse.unquote(path)
    assert 'modules/"_noId"' in decoded
    assert "nodeStatus/*" in decoded
    for field in ("descriptor", "meta", "status", "syncSeverity", "tags"):
        assert field in decoded


def test_device_detail_uses_direct_id_and_full_subtree() -> None:
    path = queries.device_detail("device12")
    assert path.endswith("/nodeStatus/device12/**")


def test_edge_pair_targets_single_pair() -> None:
    path = queries.edge_pair("device12::device7")
    decoded = urllib.parse.unquote(path)
    assert "externalEdgesByDeviceKey/device12::device7" in decoded


def test_encode_preserves_grammar_characters_and_encodes_quotes_and_spaces() -> None:
    encoded = queries.encode("/a b/*/x,y/'z'/\"q\"")
    assert "%20" in encoded  # space encoded
    assert "%22" in encoded  # double-quote encoded
    assert "/*/" in encoded  # star preserved
    assert "'z'" in encoded  # single-quote preserved


def test_query_too_long_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(queries, "MAX_QUERY_LENGTH", 10)
    with pytest.raises(InspectQueryTooLongError):
        queries.device_skeleton()
