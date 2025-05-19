from videoipath_automation_tool.apps.inventory.model.generate.pydantic_model_builder import (
    PydanticModelBuilder,
    PydanticModelField,
)


class DriverModelGenerator:
    def __init__(self, schema: dict):
        self.schema = schema

    def generate(self):
        drivers = self.schema["data"]["status"]["system"]["drivers"]["_items"]

        driver_models = "\n\n".join([self._generate_driver_model(driver) for driver in drivers])

        code = f"""
from abc import ABC
from typing import Dict, Literal, Type, TypeVar, Union, Optional

from pydantic import BaseModel, Field

# Notes:
# - The name of the custom settings model follows the naming convention: CustomSettings_<driver_organization>_<driver_name>_<driver_version> => "." and "-" are replaced by "_"!
# - src/videoipath_automation_tool/apps/inventory/model/driver_schema/2024.1.4.json.json is used as reference to define the custom settings model!
# - The "driver_id" attribute is necessary for the discriminator, which is used to determine the correct model for the custom settings in DeviceConfiguration!
# - The "alias" attribute is used to map the attribute to the correct key (with driver organization & name) in the JSON payload for the API!
# - "DriverLiteral" is used to provide a list of all possible drivers in the IDEs IntelliSense!


class DriverCustomSettings(ABC, BaseModel, validate_assignment=True): ...


{driver_models}

{self._generate_driver_id_custom_settings_mapping(drivers)}

{self._generate_driver_literal(drivers)}

# Important:
# To make the discriminator work properly, the custom settings model must be included in the Union type!
# This must be statically typed in order to make intellisense work, we can't reuse DRIVER_ID_TO_CUSTOM_SETTINGS here
{self._generate_custom_settings_type(drivers)}

# used for generic typing to ensure intellisense and correct typing
CustomSettingsType = TypeVar("CustomSettingsType", bound=CustomSettings)

"""

        with open("drivers_generated.py", "w") as f:
            f.write(code)

    def _generate_driver_model(self, driver_schema: dict) -> str:
        driver_id = driver_schema["_id"]

        builder = PydanticModelBuilder(
            name=self._get_custom_settings_class_name(driver_id), parent_classes=["DriverCustomSettings"]
        )

        builder.add_field(
            PydanticModelField(
                name="driver_id",
                type=f'Literal["{driver_id}"]',
                default=driver_id,
            )
        )

        for field_id, field in driver_schema["customSettings"]["_schema"]["values"].items():
            builder.add_field(
                PydanticModelField(
                    name=field_id.split(".")[-1],
                    type=field["_schema"]["type"],
                    default=field["_schema"]["default"],
                    alias=field_id,
                    label=field["_schema"]["descriptor"]["label"],
                    description=field["_schema"]["descriptor"]["desc"],
                    is_optional=field["_schema"]["isNullable"],
                )
            )

        return builder.build()

    def _generate_driver_id_custom_settings_mapping(self, drivers: list[dict]) -> str:
        mapping = ",\n\t".join(
            [f'"{driver["_id"]}": {self._get_custom_settings_class_name(driver["_id"])}' for driver in drivers]
        )
        return f"DRIVER_ID_TO_CUSTOM_SETTINGS: Dict[str, Type[DriverCustomSettings]] = {{\n\t{mapping}\n}}"

    def _generate_driver_literal(self, drivers: list[dict]) -> str:
        return "DriverLiteral = Literal[\n\t" + ",\n\t".join([f'"{driver["_id"]}"' for driver in drivers]) + "\n]"

    def _generate_custom_settings_type(self, drivers: list[dict]) -> str:
        custom_settings_classes = ",\n\t".join(
            [self._get_custom_settings_class_name(driver["_id"]) for driver in drivers]
        )
        return f"CustomSettings = Union[\n\t{custom_settings_classes}\n]"

    def _get_custom_settings_class_name(self, driver_id: str) -> str:
        return f"CustomSettings_{driver_id.replace('.', '_').replace('-', '_')}"
