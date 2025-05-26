import argparse
import os

from videoipath_automation_tool.scripts.generate_driver_models import main as generate_driver_models
from videoipath_automation_tool.scripts.generate_overloads import main as generate_overloads
from videoipath_automation_tool.utils.script_utils import ROOT_DIR

parser = argparse.ArgumentParser(description="Generate all version-specific code for a given VideoIPath version")
parser.add_argument("version", help="Version of VideoIPath to use", default="2024.4.12", nargs="?")


def main():
    args = parser.parse_args()
    schema_file = os.path.join(ROOT_DIR, "apps", "inventory", "model", "driver_schema", f"{args.version}.json")

    if not os.path.exists(schema_file):
        print(
            f"VideoIPath version {args.version} is currently not supported. Please create an issue on https://github.com/SWR-MoIP/VideoIPath-Automation-Tool/issues to request support for this version."
        )
        exit(1)

    generate_driver_models(schema_file)
    generate_overloads()


if __name__ == "__main__":
    main()
