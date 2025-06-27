import logging
from typing import List, Literal, Optional

from typing_extensions import deprecated

from videoipath_automation_tool.apps.inventory.app.create_device import InventoryCreateDeviceMixin
from videoipath_automation_tool.apps.inventory.app.create_device_from_discovered_device import (
    InventoryCreateDeviceFromDiscoveredDeviceMixin,
)
from videoipath_automation_tool.apps.inventory.app.get_device import InventoryGetDeviceMixin
from videoipath_automation_tool.apps.inventory.inventory_api import InventoryAPI
from videoipath_automation_tool.apps.inventory.model.drivers import CustomSettings, CustomSettingsType, DriverLiteral
from videoipath_automation_tool.apps.inventory.model.global_snmp_config import SnmpConfiguration
from videoipath_automation_tool.apps.inventory.model.inventory_device import InventoryDevice
from videoipath_automation_tool.apps.inventory.model.inventory_device_configuration_compare import (
    InventoryDeviceComparison,
)
from videoipath_automation_tool.apps.inventory.model.inventory_discovered_device import DiscoveredInventoryDevice
from videoipath_automation_tool.connector.models.response_rpc import ResponseRPC
from videoipath_automation_tool.connector.vip_connector import VideoIPathConnector
from videoipath_automation_tool.validators.device_id import validate_device_id


class InventoryApp(InventoryCreateDeviceMixin, InventoryCreateDeviceFromDiscoveredDeviceMixin, InventoryGetDeviceMixin):
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

    # --- Device CRUD Methods ---
    def add_device(
        self,
        device: InventoryDevice[CustomSettingsType],
        label_check: bool = True,
        address_check: bool = True,
        config_only: bool = False,
    ) -> InventoryDevice[CustomSettingsType]:
        """Method to add a device to VideoIPath-Inventory. Method will check if a device with same label or address already exists in inventory.
        After adding the device, the online configuration is returned as InventoryDevice instance.

        Args:
            device (InventoryDevice): Device to add to Inventory.
            label_check (bool, optional): Check if device with same user defined label already exists in Inventory. Defaults to True.
            address_check (bool, optional): Check if device with same address already exists in Inventory. Defaults to True.
            config_only (bool, optional): Add device with configuration only. Defaults to False.

        Raises:
            ValueError:  If device with same label or address already exists in inventory.

        Returns:
            InventoryDevice: Refetched device object from Inventory including device ID set by VideoIPath-Server.
            (Attention: device_id is set by VideoIPath-Inventory, so it is not known before adding the device.)
        """
        if label_check:
            label = device.label
            devices_with_label = self._inventory_api.get_device_id_by_user_defined_label(label=label)
            if devices_with_label is not None:
                raise ValueError(f"Device with label '{label}' already exists in Inventory: {devices_with_label}")

        if address_check:
            addresses = []
            addresses.append(device.configuration.address)
            addresses.extend(device.configuration.config.cinfo.altAddresses)
            for alt_address_with_auth in device.configuration.config.cinfo.altAddressesWithAuth:
                addresses.append(alt_address_with_auth.get("address"))
            addresses = list(set(addresses))

            devices_with_address = []
            for address in addresses:
                devices = self._inventory_api.get_device_id_by_address(address=address)
                if devices is not None:
                    devices_with_address.extend(devices) if isinstance(devices, list) else devices_with_address.append(
                        devices
                    )

            devices_with_address = list(set(devices_with_address))
            if devices_with_address != []:
                raise ValueError(
                    f"Devices with one of the addresses {', '.join(addresses)} already exists in Inventory: {', '.join(devices_with_address)}"
                )

        online_device = self._inventory_api.add_device(device, config_only=config_only)
        self._logger.info(
            f"Device '{online_device.label}' added successfully to Inventory with id '{online_device.device_id}'."
        )

        return online_device

    def update_device(
        self, device: InventoryDevice[CustomSettingsType], compare_config: bool = True, config_only: bool = False
    ) -> InventoryDevice[CustomSettingsType]:
        """
        Method to update a devices configuration in VideoIPath-Inventory.
        Returns the online configuration of the updated device as InventoryDevice instance.

        Args:
            device (InventoryDevice): Device to update in Inventory.
            compare_config (bool, optional): Compare the configuration of the device with the existing device configuration in Inventory, to prevent unnecessary updates. Defaults to True.
            config_only (bool, optional): Update device with configuration only. Defaults to False.

        Raises:
            ValueError: If no device_id is given in device configuration (in InventoryDevice instance).

        Returns:
            InventoryDevice: Refetched device object from Inventory.
        """
        try:
            device_id = validate_device_id(device_id=device.device_id)  # noqa: F841
        except ValueError:
            raise ValueError(
                "To update a device, a valid 'device_id' must be set in the device configuration. "
                "For a new device, use 'add_device'. If the device already exists, retrieve its configuration "
                "from the VideoIPath inventory using 'get_device' first."
            ) from None

        try:
            existing_device = self._inventory_api.get_device(device_id=device.device_id, config_only=True)
        except ValueError as e:
            raise ValueError(f"Failed to retrieve existing device configuration from Inventory: {e}") from None

        if compare_config:
            comparison = self.diff_device_configuration(reference_device=existing_device, staged_device=device)
            filtered_diffs = comparison.get_all_differences()

            if filtered_diffs.added or filtered_diffs.changed or filtered_diffs.removed:
                debug_message = self._hide_passwords_in_diffs(filtered_diffs.model_dump(mode="json"))
                self._logger.info(
                    f"Device configuration changed. Updating device in Inventory. Changes: {debug_message}"
                )
            else:
                self._logger.info("Device configuration did not change. No update necessary.")
                return device
        else:
            self._logger.info("Updating device in Inventory without comparing configuration.")

        online_device = self._inventory_api.update_device(device, config_only=config_only)
        self._logger.info(f"Device '{online_device.label}' updated in Inventory with id '{online_device.device_id}'.")
        return online_device

    def remove_device(self, device_id: str, check_remove: bool = True) -> Optional[InventoryDevice[CustomSettings]]:
        """Method to remove a device from VideoIPath-Inventory.
        Method returns last device configuration before removal.

        Args:
            device_id (str): Device ID of the device to remove.
            check_remove (bool, optional): Check if device was removed successfully. Defaults to True.

        Returns:
            InventoryDevice: Last configuration of the removed device
        """

        if not validate_device_id(device_id=device_id):
            raise ValueError(f"Device id '{device_id}' is not a valid device id.")

        if not self._inventory_api.check_device_id_exists(device_id):
            self._logger.warning(f"Device with id '{device_id}' not found in Inventory.")
            return None

        last_device_configuration = self._inventory_api.get_device(device_id=device_id, config_only=True)

        self._logger.info(f"Removing device with id '{device_id}' from Inventory")

        self._inventory_api.remove_device(device_id)

        if check_remove:
            if self._inventory_api.check_device_id_exists(device_id):
                raise ValueError(
                    f"Failed to remove device from VideoIPath-Inventory. Device with id '{device_id}' still exists."
                )
            else:
                self._logger.info(f"Device with id '{device_id}' removed from Inventory.")

        return last_device_configuration

    def refresh_device_status(self, device: InventoryDevice[CustomSettingsType]) -> InventoryDevice[CustomSettingsType]:
        """Method to refresh the status of a device from VideoIPath-Inventory

        Args:
            device (InventoryDevice): Device to refresh the status for.

        Returns:
            InventoryDevice: Device with updated status.
        """
        device_id = device.device_id
        device.status = self._inventory_api._fetch_device_status(device_id)
        return device

    # Note: create_device(), create_device_from_discovered_device(), get_device() are implemented in the respective mixins.

    def get_discovered_devices(self) -> List[DiscoveredInventoryDevice]:
        """Method to get all discovered devices from VideoIPath-Inventory.

        Returns:
            List[InventoryDevice]: List of discovered devices.
        """
        return self._inventory_api.get_discovered_devices()

    # --- Helper Methods ---
    def find_device_id_by_label(
        self,
        label: str,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
    ) -> Optional[str | List[str]]:
        """Find a device id by its label.

        Args:
            label (str): Label of the device.
            label_search_mode (Literal[&quot;canonical_label&quot;, &quot;factory_label_only&quot;, &quot;user_defined_label_only&quot;], optional): Label search mode. Defaults to "canonical_label".

        Returns:
            Optional[str | List[str]]: Device Id or list of Device Ids.
        """
        if label_search_mode == "canonical_label":
            return self._inventory_api.get_device_id_by_canonical_label(label)
        elif label_search_mode == "factory_label_only":
            return self._inventory_api.get_device_id_by_factory_label(label)
        elif label_search_mode == "user_defined_label_only":
            return self._inventory_api.get_device_id_by_user_defined_label(label)
        else:
            raise ValueError(f"Invalid label_search_mode: {label_search_mode}")

    def list_device_ids_by_driver(self, driver: DriverLiteral) -> List[str]:
        """Method to list all device ids by driver id.

        Args:
            driver (DriverLiteral): Driver to filter devices by (e.g. `com.nevion.arista-0.1.0`).
        Returns:
            List[str]: List of device ids.
        """
        return self._inventory_api.fetch_device_ids_by_driver(driver=driver)

    def enable_device(self, device_id: str) -> InventoryDevice[CustomSettings]:
        """Method to enable a device in VideoIPath-Inventory.

        Args:
            device_id (str): Device ID of the device to enable.

        Returns:
            InventoryDevice: Device with updated status.
        """
        device = self._inventory_api.get_device(device_id=device_id)
        if device.configuration.active is True:
            self._logger.info(f"Device with id '{device_id}' is already enabled.")
            return device
        else:
            self._logger.info(f"Enabling device with id '{device_id}'.")
            device.configuration.active = True
            device = self.update_device(device)
            if device.configuration.active is True:
                self._logger.info(f"Device with id '{device_id}' successfully enabled.")
            else:
                self._logger.error(f"Failed to enable device with id '{device_id}'.")
            return device

    def disable_device(self, device_id: str) -> InventoryDevice[CustomSettings]:
        """Method to disable a device in VideoIPath-Inventory.

        Args:
            device_id (str): Device ID of the device to disable.

        Returns:
            InventoryDevice: Device with updated status.
        """
        device = self._inventory_api.get_device(device_id=device_id)
        if device.configuration.active is False:
            self._logger.info(f"Device with id '{device_id}' is already disabled.")
            return device
        else:
            self._logger.info(f"Disabling device with id '{device_id}'.")
            device.configuration.active = False
            device = self.update_device(device)
            if device.configuration.active is False:
                self._logger.info(f"Device with id '{device_id}' successfully disabled.")
            else:
                self._logger.error(f"Failed to disable device with id '{device_id}'.")
            return device

    # --- Device Comparison Methods ---
    def diff_device_configuration(
        self, reference_device: InventoryDevice, staged_device: InventoryDevice
    ) -> "InventoryDeviceComparison":
        """Method to compare two devices from VideoIPath-Inventory.
        Returns a dictionary with the differences between the two devices.

        Args:
            reference_device (InventoryDevice): Reference device to compare.
            staged_device (InventoryDevice): Staged device to compare.

        Returns:
            InventoryDeviceComparison: Object containing the differences between the two devices.
        """
        comparison = InventoryDeviceComparison.analyze_inventory_devices(reference_device, staged_device)
        return comparison

    def _hide_passwords_in_diffs(self, diffs: dict) -> dict:
        """Internal helper method to hide the passwords in the differences dictionary

        Args:
            diffs (dict): Differences dictionary

        Returns:
            dict: config section of the RPC request body with hidden password
        """

        for diff in diffs["changed"] + diffs["added"] + diffs["removed"]:
            if diff["path"].startswith("root['config']['cinfo']['auth']['password']"):
                diff["new_value"] = "********"
                diff["old_value"] = "********"
            if diff["path"].startswith("root['config']['cinfo']['altAddressesWithAuth']"):
                diff["new_value"] = "********"
                diff["old_value"] = "********"
            if diff["path"].startswith("root['config']['cinfo']['auth']") and diff["type"] == "type_changed":
                if diff["new_value"] is not None:
                    diff["new_value"]["password"] = "********"
                if diff["old_value"] is not None:
                    diff["old_value"]["password"] = "********"
        return diffs

    @staticmethod
    def dump_configuration(device: InventoryDevice) -> dict:
        """Method to dump the device configuration as a API style configuration dictionary.
        Method could also be used to export a device configuration e.g. to a file.

        Returns:
            dict: The dumped configuration dictionary
        """
        return device.dump_configuration()

    @staticmethod
    def parse_configuration(config: dict) -> InventoryDevice:
        """Method to create an inventory device instance from a API style configuration dictionary.
        Method could also be used to import a device configuration e.g. from a file.

        Args:
            data: The API style configuration dictionary to parse (e.g. fetched from /rest/v2/data/config/devman/devices/device10/**).

        Returns:
            InventoryDevice: The created inventory device instance
        """
        return InventoryDevice.parse_configuration(config)

    # --- Global SNMP Configuration Helpers ---
    def get_global_snmp_config_id_by_label(self, label: str) -> Optional[str | List[str]]:
        """Method to get the global SNMP configuration id by label.
        Note: If multiple SNMP configurations with the same label exist, a list of ids is returned.

        Args:
            label (str): Label of the SNMP configuration

        Returns:
            Optional[str | List[str]]: SNMP configuration id, None if not found, List of ids if multiple configurations with the same label exist
        """
        return self._inventory_api.get_global_snmp_config_id_by_label(label=label)

    def get_global_snmp_config_label_by_id(self, snmp_config_id: str) -> Optional[str]:
        """Method to get the global SNMP configuration label by id.

        Args:
            snmp_config_id (str): SNMP configuration id

        Returns:
            Optional[str]: SNMP configuration label, None if not found
        """
        return self._inventory_api.get_global_snmp_config_label_by_id(snmp_config_id=snmp_config_id)

    def get_all_global_snmp_config_ids(self) -> dict[str, str]:
        """Method to list all global SNMP configuration ids with their labels.

        Returns:
            dict: {snmp_config_id: snmp_config_label}
        """
        return self._inventory_api.get_all_global_snmp_config_ids()

    # --- Global SNMP Configuration CRUD Methods ---
    def get_global_snmp_config(self, snmp_config_id: str) -> SnmpConfiguration:
        """Method to get a global SNMP configuration by id from VideoIPath-Inventory

        Args:
            snmp_config_id (str): SNMP configuration id

        Returns:
            GlobalSnmpConfig: Global SNMP configuration object
        """
        return self._inventory_api.get_global_snmp_config(snmp_config_id=snmp_config_id)

    def add_global_snmp_config(self, snmp_config: SnmpConfiguration) -> SnmpConfiguration:
        """Method to add a new global SNMP configuration

        Args:
            snmp_config (SnmpConfiguration): SNMP configuration object to add

        Returns:
            SnmpConfiguration: Added SNMP configuration object
        """
        return self._inventory_api.add_global_snmp_config(snmp_config=snmp_config)

    def update_global_snmp_config(self, snmp_config: SnmpConfiguration) -> SnmpConfiguration:
        """Method to update a global SNMP configuration

        Args:
            snmp_config (SnmpConfiguration): SNMP configuration object to update

        Returns:
            SnmpConfiguration: Updated SNMP configuration object
        """
        return self._inventory_api.update_global_snmp_config(snmp_config=snmp_config)

    def remove_global_snmp_config(self, snmp_config_id: str) -> ResponseRPC:
        """Method to remove a global SNMP configuration by id from VideoIPath-Inventory

        Args:
            snmp_config_id (str): SNMP configuration id

        Returns:
            ResponseRPC: Response object
        """
        return self._inventory_api.remove_global_snmp_config(snmp_config_id=snmp_config_id)

    # --- Deprecated Methods ---
    @deprecated(
        "This method is deprecated and will be removed in future versions.",
    )
    def check_device_exists(self, label: str) -> None | List[str]:
        """Method to check if a device with the given user-defined label exists in VideoIPath-Inventory.
        Returns List of device_ids with the given label.
        If no device with the given label exists, None is returned.
        """
        devices = self._inventory_api.get_device_id_by_user_defined_label(label=label)

        if devices is None:
            self._logger.info(f"No device with label '{label}' found in Inventory.")
        elif isinstance(devices, list):
            if len(devices) > 1:
                self._logger.info(f"Multiple devices with label '{label}' found in Inventory: {', '.join(devices)}")
            else:
                devices = devices[0]

        if isinstance(devices, str):
            self._logger.info(f"Device with label '{label}' found in Inventory: {devices}")
            devices = [devices]
        return devices
