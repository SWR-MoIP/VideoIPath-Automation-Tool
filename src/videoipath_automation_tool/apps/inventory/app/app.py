import logging
from typing import List, Optional

from videoipath_automation_tool.apps.inventory.app.create_device import InventoryCreateDeviceMixin
from videoipath_automation_tool.apps.inventory.app.get_device import InventoryGetDeviceMixin
from videoipath_automation_tool.apps.inventory.inventory_api import InventoryAPI
from videoipath_automation_tool.apps.inventory.model.drivers import CustomSettingsType
from videoipath_automation_tool.apps.inventory.model.inventory_device import InventoryDevice
from videoipath_automation_tool.apps.inventory.model.inventory_device_configuration_compare import (
    InventoryDeviceComparison,
)
from videoipath_automation_tool.connector.vip_connector import VideoIPathConnector
from videoipath_automation_tool.validators.device_id import validate_device_id


class InventoryApp(InventoryCreateDeviceMixin, InventoryGetDeviceMixin):
    def __init__(self, vip_connector: VideoIPathConnector, logger: Optional[logging.Logger] = None):
        """Inventory App contains functionality to interact with VideoIPath-Inventory.

        Args:
            vip_connector (VideoIPathConnector): VideoIPathConnector instance to handle the connection to VideoIPath-Server.
            logger (Optional[logging.Logger], optional): Logger instance to use for logging.
        """
        # --- Setup Logging ---
        self._logger = logger or logging.getLogger("videoipath_automation_tool_inventory_app")

        # --- Setup Inventory API ---
        self._inventory_api = InventoryAPI(vip_connector=vip_connector, logger=self._logger)

        self._logger.debug("Inventory APP initialized.")

    def add_device(
        self,
        device: InventoryDevice[CustomSettingsType],
        label_check: bool = True,
        address_check: bool = True,
        config_only: bool = False,
    ) -> InventoryDevice[CustomSettingsType]:
        """Method to add a device to VideoIPath-Inventory. Method will check if a device with same label or address already exists in inventory.
        After adding the device, the online configuration is returned as InventoryDevice instance.

        Raises:
            ValueError:  If device with same label or address already exists in inventory.

        Returns:
            InventoryDevice: Online configuration of the added device. Attention: device_id is set by VideoIPath-Inventory, so it is not known before adding the device.
        """
        if label_check:
            # Check if device with same label already exists in inventory:
            label = device.label
            devices_with_label = self._inventory_api.get_device_ids(label=label)
            if len(devices_with_label["active"]) > 0:
                raise ValueError(
                    f"Device with label '{label}' already exists in Inventory: {devices_with_label['active']}"
                )

        if address_check:
            # Check if device with same address already exists in inventory:
            address = device.address
            devices_with_address = self._inventory_api.get_device_ids(address=str(address))
            if len(devices_with_address["active"]) > 0:
                raise ValueError(
                    f"Device with address '{address}' already exists in Inventory: {devices_with_address['active']}"
                )

        online_device = self._inventory_api.add_device(device, config_only=config_only)
        self._logger.info(f"Device '{online_device.label}' added to Inventory with id '{online_device.device_id}'.")
        return online_device

    def update_device(self, device: InventoryDevice[CustomSettingsType]) -> InventoryDevice[CustomSettingsType]:
        """Method to update a device in VideoIPath-Inventory.
        Returns the online configuration of the updated device as InventoryDevice instance.

        Raises:
            ValueError:  If no device_id is given in device configuration (in InventoryDevice instance).

        Returns:
            InventoryDevice: Online configuration of the updated device.
        """
        if "device" not in device.device_id:
            raise ValueError(
                "No device_id given in device configuration. Please pull the device configuration from VideoIPath-Inventory."
            )
        online_device = self._inventory_api.update_device(device)

        self._logger.info(f"Device '{online_device.label}' updated in Inventory with id '{online_device.device_id}'.")
        return online_device

    def diff_device_configuration(
        self, reference_device: InventoryDevice, staged_device: InventoryDevice
    ) -> "InventoryDeviceComparison":
        """Method to compare two devices from VideoIPath-Inventory.
        Returns a dictionary with the differences between the two devices.
        """
        comparison = InventoryDeviceComparison.analyze_inventory_devices(reference_device, staged_device)
        return comparison

    def remove_device(self, device_id: str, check_remove: bool = True):
        """Method to remove a device from VideoIPath-Inventory"""
        if not validate_device_id(device_id=device_id):
            message = f"Device id '{device_id}' is not a valid device id."
            self._logger.debug(message)
            raise ValueError(message)

        if not self._inventory_api.device_id_exists(device_id):
            message = f"Device with id '{device_id}' not found in Inventory."
            self._logger.debug(message)
            raise ValueError(message)

        response = self._inventory_api.remove_device(device_id)

        if check_remove:
            if response.header.status != "OK":
                message = f"Failed to remove device from VideoIPath-Inventory. Error: {response}"
                self._logger.debug(message)
                raise ValueError(message)

            if self._inventory_api.device_id_exists(device_id):
                message = (
                    f"Failed to remove device from VideoIPath-Inventory. Device with id '{device_id}' still exists."
                )
                self._logger.debug(message)
                raise ValueError(message)
            else:
                self._logger.info(f"Device with id '{device_id}' removed from Inventory.")

    def check_device_exists(self, label: str) -> None | List[str]:
        """Method to check if a device with the given user-defined label exists in VideoIPath-Inventory.
        Returns List of device_ids with the given label.
        If no device with the given label exists, None is returned.
        """
        devices = self._inventory_api.device_label_exists(label)
        return devices

    @staticmethod
    def dump_configuration(device: InventoryDevice) -> dict:
        """Method to dump the configuration of a device as dictionary."""
        return device.dump_configuration()

    @staticmethod
    def parse_configuration(config: dict) -> InventoryDevice:
        """Method to parse a configuration dictionary to a InventoryDevice instance."""
        return InventoryDevice.parse_configuration(config)
