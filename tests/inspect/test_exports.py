"""Export contract tests: the inspect package and its model package define a complete ``__all__``
so star imports stay well-defined (no namespace pollution)."""

from __future__ import annotations

from videoipath_automation_tool import apps
from videoipath_automation_tool.apps import inspect
from videoipath_automation_tool.apps.inspect import model
from videoipath_automation_tool.apps.inspect.model import actions, collector, common, ngraph, update_topology


def test_model_package_all_aggregates_submodules() -> None:
    expected = {
        *actions.__all__,
        *collector.__all__,
        *common.__all__,
        *ngraph.__all__,
        *update_topology.__all__,
    }
    assert set(model.__all__) == expected
    assert len(model.__all__) == len(set(model.__all__))  # no duplicates across submodules


def test_model_package_all_names_resolve() -> None:
    for name in model.__all__:
        assert hasattr(model, name), f"model.__all__ contains unresolvable name: {name}"


def test_inspect_package_all_names_resolve() -> None:
    assert {"InspectApp", "InspectDevice", "InspectError"} <= set(inspect.__all__)
    for name in inspect.__all__:
        assert hasattr(inspect, name), f"inspect.__all__ contains unresolvable name: {name}"


def test_apps_star_import_is_clean() -> None:
    assert apps.inspect is inspect
    assert hasattr(inspect, "__all__")
