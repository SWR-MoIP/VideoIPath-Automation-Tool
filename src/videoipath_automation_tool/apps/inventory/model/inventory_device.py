from typing import Generic, Optional

from pydantic import BaseModel
from typing_extensions import deprecated

from videoipath_automation_tool.apps.inventory.inventory_utils import (
    construct_driver_id_from_info,
    extract_driver_info_from_id,
)
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

    # --- Methods ---
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
        driver_organization, driver_name, driver_version = extract_driver_info_from_id(driver_id)

        instance.configuration.config.driver = DriverInfos(
            name=driver_name, organization=driver_organization, version=driver_version
        )
        return instance

    @classmethod
    def parse_configuration(cls, data: dict):
        """Method to create an inventory device instance from a API style configuration dictionary.
        Method could also be used to import a device configuration e.g. from a file.

        Args:
            data: The API style configuration dictionary to parse (e.g. fetched from /rest/v2/data/config/devman/devices/device10/**).

        Returns:
            InventoryDevice: The created inventory device instance
        """

        data["config"]["customSettings"]["driver_id"] = construct_driver_id_from_info(
            driver_organization=data["config"]["driver"]["organization"],
            driver_name=data["config"]["driver"]["name"],
            driver_version=data["config"]["driver"]["version"],
        )

        instance = cls.model_validate({"configuration": data})
        return instance

    def dump_configuration(self) -> dict:
        """Method to dump the device configuration as a API style configuration dictionary.
        Method could also be used to export a device configuration e.g. to a file.

        Returns:
            dict: The dumped configuration dictionary
        """
        # Important: by_alias must be set to True, because the API uses "." in the custom settings key-strings,
        # which is not allowed in Python and workarounded by using the alias of a pydatic field.
        return self.configuration.model_dump(
            mode="json",
            by_alias=True,
            exclude={"config": {"customSettings": {"driver_id"}}},
        )

    def remove_device_id(self) -> None:
        """
        Removes the device id in the associated device configuration.

        This method resets the `id` attribute of the `configuration` to an empty string.
        It is useful when a device configuration needs to be duplicated or re-added
        in the inventory.

        Raises:
            ValueError: If the `configuration` attribute is not set.
        """
        if self.configuration is None:
            raise ValueError("Configuration is not set. Cannot reset device ID.")

        self.configuration.id = ""

    # --- Getter in GUI Style ---
    @property
    def device_id(self) -> str:
        """The device id of the device."""
        return self.configuration.id

    @property
    def label(self) -> str:
        """The label of the device."""
        if self.status:
            return self.status.canonicalLabel
        else:
            return self.configuration.config.desc.label

    @property
    def factory_label(self) -> Optional[str]:
        """The factory label of the device."""
        if self.status:
            return self.status.deviceInfo.label
        else:
            return None

    @property
    def ip_address(self) -> Optional[str | list[str]]:
        """The IP address of the device."""

        address = self.configuration.config.cinfo.address
        alt_adresses = self.configuration.config.cinfo.altAddresses

        address_list = []
        if address:
            address_list.append(address)
        if alt_adresses:
            address_list.extend(alt_adresses)

        if len(address_list) == 1:
            return address_list[0]
        else:
            return address_list

    @property
    def reachable(self) -> Optional[bool]:
        """The reachable status of the device."""
        if self.status:
            return self.status.reachable
        else:
            return None

    @property
    def active(self) -> Optional[bool]:
        """The active status (Enabled/Disabled) of the device."""
        return self.configuration.active

    @property
    def serial_number(self):
        """The serial number of the device."""
        if self.status:
            return self.status.deviceInfo.hw.serial
        else:
            return None

    @property
    def software_version(self):
        """The software version of the device."""
        if self.status:
            return self.status.deviceInfo.product.swVersion
        else:
            return None

    @property
    def driver_id(self):
        """The driver id of the device."""
        return construct_driver_id_from_info(
            driver_organization=self.configuration.config.driver.organization,
            driver_name=self.configuration.config.driver.name,
            driver_version=self.configuration.config.driver.version,
        )

    # --- Deprecated Setter/Getter ---
    @label.setter
    @deprecated(
        "The property `label` at the root level of the inventory device is deprecated and will be removed in the future.\n"
        " It is moved to the `configuration` property: `configuration.label`. ",
    )
    def label(self, value):
        self.configuration.config.desc.label = value

    @property
    @deprecated(
        "The property `description` at the root level of the inventory device is deprecated and will be removed in the future.\n"
        " It is moved to the `configuration` property: `configuration.description`. ",
    )
    def description(self):
        return self.configuration.config.desc.desc

    @description.setter
    @deprecated(
        "The property `description` at the root level of the inventory device is deprecated and will be removed in the future.\n"
        " It is moved to the `configuration` property: `configuration.description`. ",
    )
    def description(self, value):
        self.configuration.config.desc.desc = value

    @property
    @deprecated(
        "The property `address` at the root level of the inventory device is deprecated and will be removed in the future.\n"
        " It is moved to the `configuration` property: `configuration.address`. ",
    )
    def address(self):
        return self.configuration.config.cinfo.address

    @address.setter
    @deprecated(
        "The property `address` at the root level of the inventory device is deprecated and will be removed in the future.\n"
        " It is moved to the `configuration` property: `configuration.address`. ",
    )
    def address(self, value):
        self.configuration.config.cinfo.address = value

    @property
    @deprecated(
        "The property `custom` at the root level of the inventory device is deprecated and will be removed in the future.\n"
        " It is moved to the `configuration` property: `configuration.custom_settings`. ",
    )
    def custom(self):
        return self.configuration.config.customSettings

    @custom.setter
    @deprecated(
        "The property `custom` at the root level of the inventory device is deprecated and will be removed in the future.\n"
        " It is moved to the `configuration` property: `configuration.custom_settings`. ",
    )
    def custom(self, value):
        self.configuration.config.customSettings = value

    @property
    @deprecated(
        "The property `user` at the root level of the inventory device is deprecated and will be removed in the future.\n"
        " It is moved to the `configuration` property: `configuration.username`. ",
    )
    def user(self):
        if self.configuration.config.cinfo.auth is None:
            raise ValueError("No user set in device configuration.")
        return self.configuration.config.cinfo.auth.user

    @user.setter
    @deprecated(
        "The property `user` at the root level of the inventory device is deprecated and will be removed in the future.\n"
        " It is moved to the `configuration` property: `configuration.username`. ",
    )
    def user(self, value):
        if self.configuration.config.cinfo.auth is None:
            self.configuration.config.cinfo.auth = Auth()
        self.configuration.config.cinfo.auth.user = value

    @property
    @deprecated(
        "The property `password` at the root level of the inventory device is deprecated and will be removed in the future.\n"
        " It is moved to the `configuration` property: `configuration.password`. ",
    )
    def password(self):
        if self.configuration.config.cinfo.auth is None:
            raise ValueError("No password set in device configuration.")
        return self.configuration.config.cinfo.auth.password

    @password.setter
    @deprecated(
        "The property `password` at the root level of the inventory device is deprecated and will be removed in the future.\n"
        " It is moved to the `configuration` property: `configuration.password`. ",
    )
    def password(self, value):
        if self.configuration.config.cinfo.auth is None:
            self.configuration.config.cinfo.auth = Auth()
        self.configuration.config.cinfo.auth.password = value
