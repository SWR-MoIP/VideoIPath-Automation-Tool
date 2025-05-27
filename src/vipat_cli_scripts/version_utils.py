import importlib.util
import os
from pathlib import Path
from types import ModuleType

from videoipath_automation_tool.apps.inventory.model.drivers import SELECTED_SCHEMA_VERSION

current_file = Path(__file__).resolve()
ROOT_DIR = current_file.parent.parent / "videoipath_automation_tool"


def list_available_schema_versions() -> list[str]:
    schema_dir = os.path.join(ROOT_DIR, "apps", "inventory", "model", "driver_schema")
    return sorted(
        [f.split(".json")[0] for f in os.listdir(schema_dir) if f.endswith(".json")],
        key=lambda x: tuple(map(int, x.split("."))),
    )


def list_videoipath_versions():
    versions = list_available_schema_versions()
    print("Available VideoIPath driver schema versions:")
    for version in versions:
        print(f"- {version}")
    return None


def get_videoipath_version():
    print(f"Active VideoIPath driver schema version: {SELECTED_SCHEMA_VERSION}")
    return None


def load_module(module_name: str, file_path: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        module_name,
        file_path,
    )

    if spec is None or spec.loader is None:
        raise ValueError("Failed to load drivers module")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
