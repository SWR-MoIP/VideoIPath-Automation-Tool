import argparse
import json
from pathlib import Path

from vipat_cli_scripts.version_utils import ROOT_DIR, list_available_schema_versions, load_module

DEFAULT_VERSION = "2024.4.14"
DEFAULT_SCHEMA_FILE = Path(ROOT_DIR) / "apps" / "inventory" / "model" / "driver_schema" / f"{DEFAULT_VERSION}.json"
DEFAULT_OUTPUT_FILE = Path(ROOT_DIR) / "apps" / "inventory" / "model" / "drivers.py"


parser = argparse.ArgumentParser(description="Generate Pydantic models from driver schema")
parser.add_argument(
    "schema_file",
    nargs="?",
    type=Path,
    default=DEFAULT_SCHEMA_FILE,
    help="Path to the driver schema JSON file",
)
parser.add_argument(
    "output_file",
    nargs="?",
    type=Path,
    default=DEFAULT_OUTPUT_FILE,
    help="Path where the generated Python file will be saved",
)


def _generate_driver_model(driver_schema: dict) -> str:
    pmb_module = load_module("pydantic_model_builder", Path(ROOT_DIR) / "utils" / "pydantic_model_builder.py")
    PydanticModelBuilder = pmb_module.PydanticModelBuilder
    PydanticModelField = pmb_module.PydanticModelField

    driver_id = driver_schema["_id"]
    builder = PydanticModelBuilder(
        name=_get_custom_settings_class_name(driver_id), parent_classes=["DriverCustomSettings"]
    )

    builder.add_field(
        PydanticModelField(
            name="driver_id",
            type=f'Literal["{driver_id}"]',
            default=driver_id,
        )
    )

    if "values" in driver_schema["customSettings"]["_schema"]:
        for field_id, field in driver_schema["customSettings"]["_schema"]["values"].items():
            default = field["_schema"]["default"]
            min_value, max_value = _get_attribute_range(field)
            type_, literal_options = _get_attribute_type(field)

            builder.add_field(
                PydanticModelField(
                    name=field_id.split(".")[-1],
                    type=type_,
                    default=default,
                    alias=field_id,
                    label=field["_schema"]["descriptor"]["label"],
                    description=field["_schema"]["descriptor"]["desc"],
                    is_optional=field["_schema"]["isNullable"],
                    min_value=min_value,
                    max_value=max_value,
                    literal_options=literal_options,
                )
            )

    return builder.build()


def _generate_driver_id_custom_settings_mapping(drivers: list[dict]) -> str:
    mapping = ",\n\t".join(
        [f'"{driver["_id"]}": {_get_custom_settings_class_name(driver["_id"])}' for driver in drivers]
    )
    return f"DRIVER_ID_TO_CUSTOM_SETTINGS: Dict[str, Type[DriverCustomSettings]] = {{\n\t{mapping}\n}}"


def _generate_driver_literal(drivers: list[dict]) -> str:
    return "DriverLiteral = Literal[\n\t" + ",\n\t".join([f'"{driver["_id"]}"' for driver in drivers]) + "\n]"


def _generate_custom_settings_type(drivers: list[dict]) -> str:
    custom_settings_classes = ",\n\t".join([_get_custom_settings_class_name(driver["_id"]) for driver in drivers])
    return f"CustomSettings = Union[\n\t{custom_settings_classes}\n]"


def _get_custom_settings_class_name(driver_id: str) -> str:
    return f"CustomSettings_{driver_id.replace('.', '_').replace('-', '_')}"


def _get_attribute_range(field: dict) -> tuple[int | None, int | None]:
    if "ranges" not in field["_schema"] or len(field["_schema"]["ranges"]) == 0:
        return None, None

    min_value = field["_schema"]["default"]
    max_value = field["_schema"]["default"]

    for range in field["_schema"]["ranges"]:
        range_start, range_end, _step = range

        min_value = min(min_value, range_start)
        max_value = max(max_value, range_end)

    return min_value, max_value


def _get_attribute_type(field: dict) -> tuple[str, list[tuple[str | int | float, str, bool]] | None]:
    if "options" in field["_schema"] and len(field["_schema"]["options"]) > 0:

        def format_value(value: str | int | float) -> str:
            if isinstance(value, str):
                return f'"{value}"'
            return str(value)

        return (
            "Literal[" + ", ".join([format_value(option["value"]) for option in field["_schema"]["options"]]) + "]",
            [
                (option["value"], option["descriptor"]["label"], option["value"] == field["_schema"]["default"])
                for option in field["_schema"]["options"]
            ],
        )
    return field["_schema"]["type"], None


def main(schema_file: Path = DEFAULT_SCHEMA_FILE, output_file: Path = DEFAULT_OUTPUT_FILE):
    with open(schema_file, "r", encoding="utf-8") as f:
        schema = json.load(f)

    drivers = schema["data"]["status"]["system"]["drivers"]["_items"]
    driver_models = "\n\n".join([_generate_driver_model(driver) for driver in drivers])

    code = f"""from abc import ABC
from typing import Dict, Literal, Type, TypeVar, Union, Optional

from pydantic import BaseModel, Field

# Notes:
# - The name of the custom settings model follows the naming convention: CustomSettings_<driver_organization>_<driver_name>_<driver_version> => "." and "-" are replaced by "_"!
# - Schema {Path(schema_file).name} is used as reference to define the custom settings model!
# - The "driver_id" attribute is necessary for the discriminator, which is used to determine the correct model for the custom settings in DeviceConfiguration!
# - The "alias" attribute is used to map the attribute to the correct key (with driver organization & name) in the JSON payload for the API!
# - "DriverLiteral" is used to provide a list of all possible drivers in the IDEs IntelliSense!

SELECTED_SCHEMA_VERSION = "{Path(schema_file).stem}"
AVAILABLE_SCHEMA_VERSIONS = {list_available_schema_versions()}

class DriverCustomSettings(ABC, BaseModel, validate_assignment=True): ...


{driver_models}

{_generate_driver_id_custom_settings_mapping(drivers)}

{_generate_driver_literal(drivers)}

# Important:
# To make the discriminator work properly, the custom settings model must be included in the Union type!
# This must be statically typed in order to make intellisense work, we can't reuse DRIVER_ID_TO_CUSTOM_SETTINGS here
{_generate_custom_settings_type(drivers)}

# used for generic typing to ensure intellisense and correct typing
CustomSettingsType = TypeVar("CustomSettingsType", bound=CustomSettings)

"""
    print("Drivers generated successfully!")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(code)
        print(f"Updated {output_file}")


if __name__ == "__main__":
    args = parser.parse_args()
    main(args.schema_file, args.output_file)
