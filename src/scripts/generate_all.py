import argparse
import importlib.util
import os
from pathlib import Path
from types import ModuleType


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


generate_driver_models_mod = load_module("generate_driver_models", "src/scripts/generate_driver_models.py")


list_available_schema_versions = generate_driver_models_mod.list_available_schema_versions
generate_driver_models = generate_driver_models_mod.main


current_file = Path(__file__).resolve()
ROOT_DIR = current_file.parent.parent / "videoipath_automation_tool"

parser = argparse.ArgumentParser(description="Generate all version-specific code for a given VideoIPath version")
parser.add_argument("version", help="Version of VideoIPath to use", default="2024.4.12", nargs="?")


def main():
    args = parser.parse_args()
    schema_file = os.path.join(ROOT_DIR, "apps", "inventory", "model", "driver_schema", f"{args.version}.json")

    if not os.path.exists(schema_file):
        print(
            f"VideoIPath version {args.version} is currently not supported. Please create an issue on https://github.com/SWR-MoIP/VideoIPath-Automation-Tool/issues to request support for this version or use one of the following versions:"
        )
        print("\n".join(list_available_schema_versions()))
        exit(1)

    generate_driver_models(schema_file)

    # Note: Module should be loaded after generate_driver_models to ensure it imports the correct version of the drivers module
    generate_overloads_mod = load_module("generate_overloads", "src/scripts/generate_overloads.py")
    generate_overloads = generate_overloads_mod.main
    generate_overloads()


if __name__ == "__main__":
    main()
