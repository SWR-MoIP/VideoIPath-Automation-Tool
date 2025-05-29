import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Union

from videoipath_automation_tool.apps.inventory.model.drivers import SELECTED_SCHEMA_VERSION

current_file = Path(__file__).resolve()
ROOT_DIR = current_file.parent.parent / "videoipath_automation_tool"


def list_available_schema_versions() -> list[str]:
    schema_dir = ROOT_DIR / "apps" / "inventory" / "model" / "driver_schema"
    return sorted(
        [f.stem for f in Path(schema_dir).glob("*.json")],
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


def load_module(module_name: str, file_path: Union[str, Path]) -> ModuleType:
    file_path = Path(file_path).resolve()

    if not file_path.exists():
        raise FileNotFoundError(f"Module file not found: {file_path}")

    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to load module: {module_name} from {file_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
