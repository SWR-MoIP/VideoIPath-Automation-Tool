import logging
from typing import List, Literal, Optional, overload

from videoipath_automation_tool.apps.inventory.inventory_api import InventoryAPI
from videoipath_automation_tool.apps.inventory.model import DriverLiteral
from videoipath_automation_tool.apps.inventory.model.drivers import (
    CustomSettings_com_nevion_arista_0_1_0,
    CustomSettings_com_nevion_dhd_series52_0_1_0,
    CustomSettings_com_nevion_lawo_ravenna_0_1_0,
    CustomSettings_com_nevion_NMOS_0_1_0,
    CustomSettings_com_nevion_NMOS_multidevice_0_1_0,
    CustomSettings_com_nevion_nodectrl_0_1_0,
    CustomSettings_com_nevion_openflow_0_0_1,
    CustomSettings_com_nevion_powercore_0_1_0,
    CustomSettings_com_nevion_r3lay_0_1_0,
    CustomSettings_com_nevion_selenio_13p_0_1_0,
    CustomSettings_com_nevion_virtuoso_mi_0_1_0,
    CustomSettings_com_sony_MLS_X1_1_0,
)
from videoipath_automation_tool.apps.inventory.model.inventory_device import InventoryDevice
from videoipath_automation_tool.apps.inventory.model.inventory_device_configuration_compare import (
    InventoryDeviceComparison,
)
from videoipath_automation_tool.connector.vip_connector import VideoIPathConnector
from videoipath_automation_tool.utils.cross_app_utils import validate_device_id_string


class InventoryApp:
    def __init__(self, vip_connector: VideoIPathConnector, logger: Optional[logging.Logger] = None):
        """Inventory App contains functionality to interact with VideoIPath-Inventory.

        Args:
            vip_connector (VideoIPathConnector): VideoIPathConnector instance to handle the connection to VideoIPath-Server.
            logger (Optional[logging.Logger], optional): Logger instance to use for logging.
        """
        # --- Setup Logging ---
        if logger is None:
            self._logger = logging.getLogger(
                "videoipath_automation_tool_inventory_app"
            )  # create fallback logger if no logger is provided
        else:
            self._logger = logger

        # --- Setup Inventory API ---
        try:
            self._inventory_api = InventoryAPI(vip_connector=vip_connector, logger=self._logger)
            self._logger.debug("Inventory API successfully initialized.")
        except Exception as e:
            self._logger.error(f"Error initializing Inventory API: {e}")
            raise ConnectionError("Error initializing Inventory API.")

    @overload
    def create_device(
        self, driver: Literal["com.nevion.NMOS_multidevice-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_NMOS_multidevice_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.NMOS-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_NMOS_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.selenio_13p-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_selenio_13p_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.arista-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_arista_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.r3lay-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_r3lay_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.powercore-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_powercore_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.nodectrl-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_nodectrl_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.sony.MLS-X1-1.0"]
    ) -> InventoryDevice[CustomSettings_com_sony_MLS_X1_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.dhd_series52-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_dhd_series52_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.virtuoso_mi-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_virtuoso_mi_0_1_0]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.openflow-0.0.1"]
    ) -> InventoryDevice[CustomSettings_com_nevion_openflow_0_0_1]: ...

    @overload
    def create_device(
        self, driver: Literal["com.nevion.lawo_ravenna-0.1.0"]
    ) -> InventoryDevice[CustomSettings_com_nevion_lawo_ravenna_0_1_0]: ...

    @overload
    def create_device(
        self, driver: DriverLiteral
    ) -> InventoryDevice: ...  # workaround to show all drivers in intellisense because otherwise it will only show intellisense for the closest matching overload

    def create_device(self, driver: DriverLiteral) -> InventoryDevice:
        """Method to create a new device configuration for VideoIPath-Inventory.
        Returns an empty InventoryDevice instance with the given driver.

        Args:
            driver (str): Driver of the device to create. (e.g. "com.nevion.NMOS_multidevice-0.1.0")

        Returns:
            InventoryDevice: Empty device configuration for the given driver.
        """
        return InventoryDevice.create(driver=str(driver))

    def add_device(
        self, device: InventoryDevice, label_check: bool = True, address_check: bool = True, config_only: bool = False
    ) -> InventoryDevice:
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

    def get_device(
        self,
        label: Optional[str] = None,
        device_id: Optional[str] = None,
        address: Optional[str] = None,
        config_only: bool = False,
    ) -> InventoryDevice:
        """Method to get a online device from VideoIPath-Inventory by label, device_id or address as InventoryDevice instance.

        Raises:
            ValueError:  If more than one parameter is given.
            ValueError:  If no device with given label, device_id or address exists in inventory.
            ValueError:  If more than one device with given label or address exists in inventory.

        Returns:
            InventoryDevice: Online configuration of the requested device.
        """

        # Validate which parameter is given, raise error if more than one parameter is given!
        # & Check if device with given label, device_id or address exists in inventory, raise error if not!
        if sum([1 for x in [label, device_id, address] if x is not None]) > 1:
            raise ValueError("Only one parameter is allowed! Please use either label, device_id or address.")
        if label is not None:
            devices = self._inventory_api.get_device_ids(label=label)
            if len(devices["active"]) == 0:
                if validate_device_id_string(device_id=label, include_virtual=False):
                    self._logger.warning(
                        f"It seems that the provided label '{label}' is a device_id. Please use get_device(device_id='{label}') instead."
                    )
                raise ValueError(f"No device with label '{label}' found in Inventory.")
            if len(devices["active"]) > 1:
                raise ValueError(f"More than one device with label '{label}' found in Inventory: {devices['active']}")
            device_id = devices["active"][0]
        elif device_id is not None:
            if validate_device_id_string(device_id=device_id, include_virtual=False):
                if not self._inventory_api.device_id_exists(device_id):
                    raise ValueError(f"No device with id '{device_id}' found in Inventory.")
            else:
                raise ValueError(f"Invalid device_id '{device_id}' provided!")
        elif address is not None:
            devices = self._inventory_api.get_device_ids(address=str(address))
            if len(devices["active"]) == 0:
                raise ValueError(f"No device with address '{address}' found in Inventory.")
            if len(devices["active"]) > 1:
                raise ValueError(
                    f"More than one device with address '{address}' found in Inventory: {devices['active']}"
                )
            device_id = devices["active"][0]

        # Get online configuration of device from VideoIPath-Inventory and return configured InventoryDevice instance:
        if type(device_id) is not str:
            raise ValueError("device_id must be a string.")
        online_device = self._inventory_api.get_device(device_id=device_id, config_only=config_only)
        return online_device

    def update_device(self, device: InventoryDevice) -> InventoryDevice:
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
        if not validate_device_id_string(device_id=device_id, include_virtual=False):
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
