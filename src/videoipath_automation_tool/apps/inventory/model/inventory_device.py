from typing import Generic, Optional

from pydantic import BaseModel

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

    # Setter / getter to improve the usability of the class
    @property
    def label(self):
        return self.configuration.config.desc.label

    @label.setter
    def label(self, value):
        self.configuration.config.desc.label = value

    @property
    def description(self):
        return self.configuration.config.desc.desc

    @description.setter
    def description(self, value):
        self.configuration.config.desc.desc = value

    @property
    def address(self):
        return self.configuration.config.cinfo.address

    @address.setter
    def address(self, value):
        self.configuration.config.cinfo.address = value

    @property  # Access to custom settings via "custom" property => e.g. device.custom.experimental_alarm_port
    def custom(self):
        return self.configuration.config.customSettings

    @custom.setter
    def custom(self, value):
        self.configuration.config.customSettings = value

    # TODO:
    # Known Issue: If a password is set, it is not possible to change the user without setting the password again!
    # TO FIX!
    @property
    def user(self):
        if self.configuration.config.cinfo.auth is None:
            raise ValueError("No user set in device configuration.")
        return self.configuration.config.cinfo.auth.user

    @user.setter
    def user(self, value):
        if self.configuration.config.cinfo.auth is None:
            self.configuration.config.cinfo.auth = Auth()
        self.configuration.config.cinfo.auth.user = value

    @property
    def password(self):
        if self.configuration.config.cinfo.auth is None:
            raise ValueError("No password set in device configuration.")
        return self.configuration.config.cinfo.auth.password

    @password.setter
    def password(self, value):
        if self.configuration.config.cinfo.auth is None:
            self.configuration.config.cinfo.auth = Auth()
        self.configuration.config.cinfo.auth.password = value

    @property
    def device_id(self):
        return self.configuration.id

    @classmethod
    def create(cls, driver: str):
        """Method to create a inventory device instance with a specific driver and default values."""
        instance = cls.model_validate({"configuration": {"config": {"customSettings": {"driver_id": driver}}}})
        # Use driver_id string to fill driver info, then remove "driver_id" from customSettings!
        driver_id = instance.configuration.config.customSettings.driver_id
        driver_name = driver_id.split("-")[0].split(".")[2]
        driver_organization = driver_id.split(".")[0] + "." + driver_id.split(".")[1]
        driver_version = driver_id.split("-")[1]
        instance.configuration.config.driver = DriverInfos(
            name=driver_name, organization=driver_organization, version=driver_version
        )
        instance.configuration.config.customSettings.__delattr__("driver_id")
        return instance

    @classmethod
    def parse_configuration(cls, data: dict) -> "InventoryDevice":  # TODO evtl. Return hint weg?
        """Method to create a inventory device instance from a API style configuration dictionary."""
        # Use driver_id string to fill driver info, then remove "driver_id" from customSettings!
        driver_organization = data["config"]["driver"]["organization"]
        driver_name = data["config"]["driver"]["name"]
        driver_version = data["config"]["driver"]["version"]
        driver_id = f"{driver_organization}.{driver_name}-{driver_version}"
        data["config"]["customSettings"]["driver_id"] = driver_id
        instance = cls.model_validate({"configuration": data})
        instance.configuration.config.customSettings.__delattr__("driver_id")
        return instance

    def dump_configuration(self) -> dict:
        """Method to dump the device configuration as a API style configuration dictionary."""
        # Important: by_alias must be set to True, because the API uses "." in the keys, which is not allowed in Python and workarounded by using the alias of a pydatic field.
        return self.configuration.model_dump(mode="json", by_alias=True)
