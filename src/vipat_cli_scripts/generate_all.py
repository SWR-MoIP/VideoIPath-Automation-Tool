import argparse
from pathlib import Path

from vipat_cli_scripts.generate_driver_models import main as generate_driver_models
from vipat_cli_scripts.version_utils import ROOT_DIR, list_available_schema_versions, load_module

parser = argparse.ArgumentParser(description="Generate all version-specific code for a given VideoIPath version")
parser.add_argument("version", help="Version of VideoIPath to use", default="2024.4.14", nargs="?")


def main():
    args = parser.parse_args()
    schema_file = Path(ROOT_DIR) / "apps" / "inventory" / "model" / "driver_schema" / f"{args.version}.json"
    print(f"Generate Schema for VideoIPath version {args.version} ...")

    if not schema_file.exists():
        print(
            f"VideoIPath version {args.version} is currently not supported. Please create an issue on https://github.com/SWR-MoIP/VideoIPath-Automation-Tool/issues to request support for this version or use one of the following versions:"
        )
        versions = list_available_schema_versions()
        for version in versions:
            print(f"- {version}")
        exit(1)

    generate_driver_models(schema_file)

    # Note: Module should be loaded after generate_driver_models to ensure it imports the correct version of the drivers module
    generate_overloads_path = ROOT_DIR.parent / "vipat_cli_scripts" / "generate_overloads.py"
    generate_overloads_mod = load_module("generate_overloads", generate_overloads_path)
    generate_overloads = generate_overloads_mod.main
    generate_overloads()


if __name__ == "__main__":
    main()
