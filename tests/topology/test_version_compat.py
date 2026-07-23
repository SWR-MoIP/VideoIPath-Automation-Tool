"""TopologyApp VideoIPath version compatibility gate."""

from __future__ import annotations

import warnings
from types import SimpleNamespace

import pytest

from videoipath_automation_tool.apps.topology.errors import TopologyUnsupportedError
from videoipath_automation_tool.apps.topology.topology_app import TopologyApp


def _fake_connector(version: str) -> SimpleNamespace:
    return SimpleNamespace(videoipath_version=version)


def test_topology_app_supported_on_2024() -> None:
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always", DeprecationWarning)
        app = TopologyApp(vip_connector=_fake_connector("2024.4.30"))  # type: ignore[arg-type]
    assert app is not None
    assert not any(issubclass(w.category, DeprecationWarning) for w in record)


def test_topology_app_deprecated_on_2025() -> None:
    with pytest.warns(DeprecationWarning, match="deprecated on VideoIPath 2025") as record:
        app = TopologyApp(vip_connector=_fake_connector("2025.4.9"))  # type: ignore[arg-type]
    assert app is not None
    assert len(record) == 1
    assert "InspectApp" in str(record[0].message)


def test_topology_app_unsupported_on_2026() -> None:
    with pytest.raises(TopologyUnsupportedError, match="not supported on VideoIPath 2026.1.0"):
        TopologyApp(vip_connector=_fake_connector("2026.1.0"))  # type: ignore[arg-type]


def test_topology_app_skips_gate_for_unparseable_version() -> None:
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always", DeprecationWarning)
        app = TopologyApp(vip_connector=_fake_connector("unknown"))  # type: ignore[arg-type]
    assert app is not None
    assert not any(issubclass(w.category, DeprecationWarning) for w in record)
