from typing import Generic, Optional

from pydantic import BaseModel
from typing_extensions import deprecated

from videoipath_automation_tool.apps.inventory.model.device_status import DeviceStatus
from videoipath_automation_tool.apps.inventory.model.drivers import CustomSettingsType
from videoipath_automation_tool.apps.inventory.model.inventory_device_configuration import (
    Auth,
    DeviceConfiguration,
    DriverInfos,
)


class InventoryDevice(BaseModel, Generic[CustomSettingsType], validate_assignment=True):
    """InventoryDevice class is used to represent a device configuration for VideoIPath inventory."""

    configuration: DeviceConfiguration[CustomSettingsType]
    status: Optional[DeviceStatus] = None

    @property
    def device_id(self):
        return self.configuration.id

    # --- Deprecated properties ---
    @deprecated(
        "The property `label` at the root level of the inventory device is deprecated and will be removed in the future.\n"
        " It is moved to the `configuration` property: `configuration.label`. ",
        category=None,
    )
    @property
    def label(self):
        return self.configuration.config.desc.label

    @deprecated(
        "The property `label` at the root level of the inventory device is deprecated and will be removed in the future.\n"
        " It is moved to the `configuration` property: `configuration.label`. ",
        category=None,
    )
    @label.setter
    def label(self, value):
        self.configuration.config.desc.label = value

    @deprecated(
        "The property `description` at the root level of the inventory device is deprecated and will be removed in the future.\n"
        " It is moved to the `configuration` property: `configuration.description`. ",
        category=None,
    )
    @property
    def description(self):
        return self.configuration.config.desc.desc

    @deprecated(
        "The property `description` at the root level of the inventory device is deprecated and will be removed in the future.\n"
        " It is moved to the `configuration` property: `configuration.description`. ",
        category=None,
    )
    @description.setter
    def description(self, value):
        self.configuration.config.desc.desc = value

    @deprecated(
        "The property `address` at the root level of the inventory device is deprecated and will be removed in the future.\n"
        " It is moved to the `configuration` property: `configuration.address`. ",
        category=None,
    )
    @property
    def address(self):
        return self.configuration.config.cinfo.address

    @deprecated(
        "The property `address` at the root level of the inventory device is deprecated and will be removed in the future.\n"
        " It is moved to the `configuration` property: `configuration.address`. ",
        category=None,
    )
    @address.setter
    def address(self, value):
        self.configuration.config.cinfo.address = value

    @deprecated(
        "The property `custom` at the root level of the inventory device is deprecated and will be removed in the future.\n"
        " It is moved to the `configuration` property: `configuration.custom_settings`. ",
        category=None,
    )
    @property
    def custom(self):
        return self.configuration.config.customSettings

    @deprecated(
        "The property `custom` at the root level of the inventory device is deprecated and will be removed in the future.\n"
        " It is moved to the `configuration` property: `configuration.custom_settings`. ",
        category=None,
    )
    @custom.setter
    def custom(self, value):
        self.configuration.config.customSettings = value

    @deprecated(
        "The property `user` at the root level of the inventory device is deprecated and will be removed in the future.\n"
        " It is moved to the `configuration` property: `configuration.username`. ",
        category=None,
    )
    @property
    def user(self):
        if self.configuration.config.cinfo.auth is None:
            raise ValueError("No user set in device configuration.")
        return self.configuration.config.cinfo.auth.user

    @deprecated(
        "The property `user` at the root level of the inventory device is deprecated and will be removed in the future.\n"
        " It is moved to the `configuration` property: `configuration.username`. ",
        category=None,
    )
    @user.setter
    def user(self, value):
        if self.configuration.config.cinfo.auth is None:
            self.configuration.config.cinfo.auth = Auth()
        self.configuration.config.cinfo.auth.user = value

    @deprecated(
        "The property `password` at the root level of the inventory device is deprecated and will be removed in the future.\n"
        " It is moved to the `configuration` property: `configuration.password`. ",
        category=None,
    )
    @property
    def password(self):
        if self.configuration.config.cinfo.auth is None:
            raise ValueError("No password set in device configuration.")
        return self.configuration.config.cinfo.auth.password

    @deprecated(
        "The property `password` at the root level of the inventory device is deprecated and will be removed in the future.\n"
        " It is moved to the `configuration` property: `configuration.password`. ",
        category=None,
    )
    @password.setter
    def password(self, value):
        if self.configuration.config.cinfo.auth is None:
            self.configuration.config.cinfo.auth = Auth()
        self.configuration.config.cinfo.auth.password = value

    @deprecated(
        "The property `device_id` at the root level of the inventory device is deprecated and will be removed in the future.\n"
        " It is moved to the `configuration` property: `configuration.id`. ",
        category=None,
    )
    @classmethod
    def create(cls, driver_id: str) -> "InventoryDevice":
        """Method to create an inventory device instance with a specific driver and default values.

        Args:
            driver_id: The driver_id string of the driver to use, e.g. "com.nevion.NMOS_multidevice-0.1.0".

        Returns:
            InventoryDevice: The created inventory device instance
        """
        instance = cls.model_validate({"configuration": {"config": {"customSettings": {"driver_id": driver_id}}}})

        driver_id = instance.configuration.config.customSettings.driver_id
        driver_name = driver_id.split("-")[0].split(".")[2]
        driver_organization = driver_id.split(".")[0] + "." + driver_id.split(".")[1]
        driver_version = driver_id.split("-")[1]

        instance.configuration.config.driver = DriverInfos(
            name=driver_name, organization=driver_organization, version=driver_version
        )
        return instance

    @classmethod
    def parse_configuration(cls, data: dict):
        """Method to create an inventory device instance from a API style configuration dictionary.

        Args:
            data: The API style configuration dictionary to parse (e.g. fetched from /rest/v2/data/config/devman/devices/device10/**).

        Returns:
            InventoryDevice: The created inventory device instance
        """
        driver_organization = data["config"]["driver"]["organization"]
        driver_name = data["config"]["driver"]["name"]
        driver_version = data["config"]["driver"]["version"]
        driver_id = f"{driver_organization}.{driver_name}-{driver_version}"

        data["config"]["customSettings"]["driver_id"] = driver_id

        instance = cls.model_validate({"configuration": data})
        return instance

    def dump_configuration(self) -> dict:
        """Method to dump the device configuration as a API style configuration dictionary."""
        # Important: by_alias must be set to True, because the API uses "." in the keys,
        # which is not allowed in Python and workarounded by using the alias of a pydatic field.
        return self.configuration.model_dump(
            mode="json",
            by_alias=True,
            exclude={"config": {"customSettings": {"driver_id"}}},
        )
