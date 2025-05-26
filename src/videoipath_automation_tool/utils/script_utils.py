import importlib.util
import os
from types import ModuleType

UTILS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(UTILS_DIR)


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
