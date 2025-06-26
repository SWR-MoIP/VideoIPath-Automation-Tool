import logging
import time
import urllib.parse
from typing import List, Optional, Type
from uuid import uuid4

from pydantic import IPvAnyAddress
from typing_extensions import deprecated

from videoipath_automation_tool.apps.inventory.inventory_utils import (
    construct_driver_id_from_info,
    extract_driver_info_from_id,
)
from videoipath_automation_tool.apps.inventory.model.device_status import DeviceStatus
from videoipath_automation_tool.apps.inventory.model.drivers import CustomSettingsType, DriverLiteral
from videoipath_automation_tool.apps.inventory.model.global_snmp_config import SnmpConfiguration
from videoipath_automation_tool.apps.inventory.model.global_snmp_request_rpc import SnmpRequestRpc
from videoipath_automation_tool.apps.inventory.model.inventory_device import InventoryDevice
from videoipath_automation_tool.apps.inventory.model.inventory_discovered_device import DiscoveredInventoryDevice
from videoipath_automation_tool.apps.inventory.model.inventory_request_rpc import InventoryRequestRpc
from videoipath_automation_tool.connector.models.response_rpc import ResponseRPC
from videoipath_automation_tool.connector.vip_connector import VideoIPathConnector
from videoipath_automation_tool.utils.cross_app_utils import create_fallback_logger, extract_natural_sort_key
from videoipath_automation_tool.validators.device_id import validate_device_id


class InventoryAPI:
    STATUS_FETCH_RETRY_DEFAULT = 20
    STATUS_FETCH_DELAY_DEFAULT = 2

    def __init__(self, vip_connector: VideoIPathConnector, logger: Optional[logging.Logger] = None):
        """
        Class for VideoIPath Inventory API.
        """

        # --- Setup Logging ---
        self._logger = logger or create_fallback_logger("videoipath_automation_tool_inventory_api")
        self.vip_connector = vip_connector

        self._logger.debug("Inventory API initialized.")

    # --- Device Management Methods ---
    # --- Device CRUD Methods ---
    def get_device(
        self,
        device_id: str,
        custom_settings_type: Optional[Type[CustomSettingsType]] = None,
        config_only: bool = False,
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice[CustomSettingsType]:
        """Method to get a device by device id from VideoIPath-Inventory

        Args:
            device_id (str): Device ID
            custom_settings_type (Optional[Type[CustomSettingsType]], optional): Custom settings type to use. Defaults to None.
            config_only (bool, optional): Get only the configuration of the device. Defaults to False.
            status_fetch_retry (int, optional): Number of retries to fetch device status. Defaults to 20.
            status_fetch_delay (int, optional): Delay between status fetch retries. Defaults to 2.
        Returns:
            InventoryDevice: Device object
        """
        if not device_id.startswith("device"):
            raise ValueError("device_id must start with 'device'.")
        self._logger.debug(f"Retrieving device '{device_id}' from VideoIPath-Inventory.")
        if custom_settings_type:
            self._logger.debug(
                f"Using custom settings type '{custom_settings_type.__name__}' for device '{device_id}'."
            )

        online_device = self._fetch_device_config(device_id)

        if not config_only:
            if not isinstance(status_fetch_retry, int):
                self._logger.warning("status_fetch_retry must be an integer. Using default value of 20.")
                status_fetch_retry = 20
            if not isinstance(status_fetch_delay, int):
                self._logger.warning("status_check_delay must be an integer. Using default value of 2.")
                status_fetch_delay = 2
            if status_fetch_retry < 1:
                self._logger.warning("status_fetch_retry must be greater than 0. Using default value of 20.")
                status_fetch_retry = 20
            if status_fetch_delay < 1:
                self._logger.warning("status_check_delay must be greater than 0. Using default value of 2.")
                status_fetch_delay = 2
            retry_cnt = status_fetch_retry
            while retry_cnt > 0:
                try:
                    online_device.status = self._fetch_device_status(online_device.configuration.id)
                    if online_device.status:
                        break
                except ValueError:
                    self._logger.debug(
                        f"Failed to get device status for device '{online_device.configuration.id}', retrying ({21 - retry_cnt}/{status_fetch_retry}) ..."
                    )
                    time.sleep(status_fetch_delay)
                    retry_cnt -= 1
            if retry_cnt == 0 and not online_device.status:
                self._logger.warning(
                    f"Failed to get device status for device '{online_device.configuration.id}'. Retry limit reached. Returning device without status."
                )
        else:
            self._logger.debug(f"Skipping status update for device '{device_id}'.")

        self._logger.debug(f"Device '{device_id}' retrieved from VideoIPath-Inventory.")
        return online_device

    def add_device(
        self,
        device: InventoryDevice,
        clear_uuid_after_add: bool = True,
        config_only: bool = False,
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice:
        """Method to add a new device with config to VideoIPath-Inventory

        Args:
            device (InventoryDevice): Device object to add
            clear_uuid_after_add (bool, optional): Remove generated UUID from device configuration after adding. Defaults to True.
            config_only (bool, optional): Fetch only the configuration of the device after adding. Defaults to False.
            status_fetch_retry (int, optional): Number of retries to fetch device status. Defaults to 20.
            status_fetch_delay (int, optional): Delay between status fetch retries. Defaults to 2.

        Raises:
            ValueError: Raised if adding device fails.

        Returns:
            InventoryDevice: Refetched device object from Inventory including device ID set by VideoIPath-Server
        """

        if device.configuration.id != "":
            raise ValueError(
                "Device ID must be empty when adding a new device! "
                "Set 'id' to an empty string 'InventoryDevice.remove_device_id()' or use 'inventory_api.update_device()' if an existing device should be updated."
            )

        self._logger.debug(
            f"Adding new device with label '{device.configuration.config.desc.label}' and address '{device.configuration.config.cinfo.address}' to VideoIPath-Inventory."
        )

        tracking_id = str(uuid4())
        self._logger.debug(f"Tracking ID generated: {tracking_id}")

        modified_device = device.model_copy(deep=True)
        modified_device.configuration.meta["uuid"] = tracking_id
        self._logger.debug(f"Add Meta field 'uuid' with tracking ID '{tracking_id}' to device configuration.")

        body = InventoryRequestRpc()

        driver_id = construct_driver_id_from_info(
            driver_organization=modified_device.configuration.config.driver.organization,
            driver_name=modified_device.configuration.config.driver.name,
            driver_version=modified_device.configuration.config.driver.version,
        )

        modified_device.configuration.config.customSettings.driver_id = driver_id

        body.add(modified_device)

        debug_body_without_password = body.model_dump(mode="json")
        config = debug_body_without_password["data"]["add"][""]["config"]
        config = self._hide_password_in_config_dict_for_debug_message(config)
        self._logger.debug(f"RPC Request body generated (password fields hidden): {debug_body_without_password}")

        response = self.vip_connector.rpc.post("/api/updateDevices", body=body)

        if response.header.status != "OK":
            raise ValueError(f"Failed to add device to VideoIPath-Inventory. Error: {response}")

        online_device = self._fetch_device_config_by_uuid(uuid=tracking_id)

        self._logger.debug(
            f"Device with id '{online_device.configuration.id}' added successfully to VideoIPath-Inventory."
        )

        if not clear_uuid_after_add:
            self._logger.debug("Skip removing tracking ID ('uuid' meta field) from device configuration.")
        else:
            modified_device = online_device.model_copy(deep=True)
            modified_device.configuration.meta.pop("uuid")
            self._logger.debug(
                "Remove tracking ID ('uuid' meta field) from device configuration and update device in VideoIPath-Inventory."
            )
            online_device = self.update_device(
                device=modified_device, config_only=True
            )  # Use config_only=True to avoid status fetch and speed up the process
            self._logger.debug("Tracking ID removed successfully from device configuration.")

        if config_only:
            self._logger.debug("Skip fetching device status after adding.")
        else:
            self._logger.warning(
                "Fetching device status is enabled and may take up to 30 seconds for devices, which are not accessible for VideoIPath-Server (e.g. offline devices). "
                "To speed up the process for those devices, `add_device(..., config_only=True)` can be used and the status retrieval can be omitted."
            )
            online_device = self.get_device(
                device_id=online_device.configuration.id,
                config_only=config_only,
                status_fetch_delay=status_fetch_delay,
                status_fetch_retry=status_fetch_retry,
            )

            self._logger.debug(f"Device added successfully with id: {online_device.configuration.id}")

        return online_device

    def update_device(
        self,
        device: InventoryDevice,
        config_only: bool = False,
        status_fetch_retry: int = STATUS_FETCH_RETRY_DEFAULT,
        status_fetch_delay: int = STATUS_FETCH_DELAY_DEFAULT,
    ) -> InventoryDevice:
        """Method to update a device config in VideoIPath-Inventory

        Args:
            device (InventoryDevice): Device object to update
            config_only (bool, optional): Fetch only the configuration of the device after updating. Defaults to False.

        Returns:
            InventoryDevice: Refetched device object from Inventory
        """
        try:
            device_id = validate_device_id(device_id=device.device_id)
        except ValueError:
            raise ValueError(
                "To update a device, a valid 'device_id' must be set in the device configuration. "
                "For a new device, use 'add_device'. If the device already exists, retrieve its configuration "
                "from the VideoIPath inventory using 'get_device' or set device_id manually first."
            ) from None

        self._logger.debug(f"Updating device with id '{device.configuration.id}' in VideoIPath-Inventory.")
        body = InventoryRequestRpc()

        driver_id = construct_driver_id_from_info(
            driver_organization=device.configuration.config.driver.organization,
            driver_name=device.configuration.config.driver.name,
            driver_version=device.configuration.config.driver.version,
        )
        device.configuration.config.customSettings.driver_id = driver_id

        body.update(device)

        debug_body_without_password = body.model_dump(mode="json")
        config = debug_body_without_password["data"]["update"][device_id]["config"]
        config = self._hide_password_in_config_dict_for_debug_message(config)
        self._logger.debug(f"RPC Request body generated (password fields hidden): {debug_body_without_password}")

        response = self.vip_connector.rpc.post("/api/updateDevices", body=body)

        if response.header.status != "OK":
            raise ValueError(f"Failed to update device in VideoIPath-Inventory. Error: {response}")

        online_device = self.get_device(
            device_id=device.configuration.id,
            config_only=config_only,
            status_fetch_delay=status_fetch_delay,
            status_fetch_retry=status_fetch_retry,
        )
        self._logger.debug(f"Device with id '{device.configuration.id}' updated successfully.")
        return online_device

    def remove_device(self, device_id: str) -> ResponseRPC:
        """Method to remove a device from VideoIPath-Inventory

        Args:
            device_id (str): Device ID

        Returns:
            ResponseRPC: Response object
        """
        self._logger.debug(f"Removing device with id '{device_id}' from VideoIPath-Inventory.")
        body = InventoryRequestRpc()

        body.remove(device_id)

        self._logger.debug(f"RPC Request body generated: {body.model_dump(mode='json')}")

        response = self.vip_connector.rpc.post("/api/updateDevices", body=body)

        if response.header.status != "OK":
            raise ValueError(f"Failed to remove device from VideoIPath-Inventory. Error: {response}")

        return response

    def _hide_password_in_config_dict_for_debug_message(self, body: dict) -> dict:
        """Internal helper method to hide the passwords in the configuration dictionary of the RPC request body

        Args:
            body (dict): "config" section of InventoryRequestRpc as dictionary

        Returns:
            dict: config section of the RPC request body with hidden password
        """
        if body["cinfo"]["auth"] is not None:
            body["cinfo"]["auth"]["password"] = "********"

        for alt_address in body["cinfo"]["altAddressesWithAuth"]:
            alt_address["authentication"]["password"] = "********"
        return body

    def _fetch_device_config(self, device_id: str) -> InventoryDevice:
        """Method to receive a device config by device id from VideoIPath-Inventory

        Args:
            device_id (str): Device id (e.g. "device1")

        Returns:
            InventoryDevice: Device object
        """
        device_id = validate_device_id(device_id=device_id)
        response = self.vip_connector.rest.get(f"/rest/v2/data/config/devman/devices/* where id='{device_id}' /**")
        if response.data and response.data["config"]["devman"]["devices"]["_items"]:
            device = InventoryDevice.parse_configuration(response.data["config"]["devman"]["devices"]["_items"][0])
            return device
        raise ValueError(f"Device with id '{device_id}' not found.")

    def _fetch_device_status(self, device_id: str) -> DeviceStatus:
        """Method to receive the status of a device by device id from VideoIPath-Inventory

        Args:
            device_id (str): Device ID

        Returns:
            DeviceStatus: Device status.
        """
        device_id = validate_device_id(device_id=device_id)
        response = self.vip_connector.rest.get(f"/rest/v2/data/status/devman/devices/* where id='{device_id}' /**")
        if response.data and response.data["status"]["devman"]["devices"]["_items"]:
            return DeviceStatus(**response.data["status"]["devman"]["devices"]["_items"][0])
        raise ValueError(f"Device with id '{device_id}' not found.")

    def _fetch_device_config_by_uuid(self, uuid: str) -> InventoryDevice:
        """Method to receive a device configuration by uuid in Meta field from VideoIPath-Inventory

        Args:
            uuid (str): UUID in Meta field of device configuration

        Returns:
            InventoryDevice: Device object
        """
        self._logger.debug(f"Fetching device configuration by given 'uuid' meta field value'{uuid}'.")

        device_id = self.get_device_id_by_meta_field_value("uuid", uuid)
        if not device_id:
            raise ValueError(f"No device with uuid '{uuid}' found.")
        if isinstance(device_id, list):
            raise ValueError(f"Multiple devices with uuid '{uuid}' found.")

        device = self._fetch_device_config(device_id)

        self._logger.debug(f"Device with id '{device.configuration.id}' fetched successfully.")

        return device

    # --- Helper Methods ---
    def check_device_id_exists(self, device_id: str) -> bool:
        """Method to check if a device id exists in VideoIPath-Inventory"""
        escaped_device_id = urllib.parse.quote(device_id, safe="")
        response = self.vip_connector.rest.get(
            f"/rest/v2/data/config/devman/devices/* where id='{escaped_device_id}' /_id"
        )
        if response.data and response.data["config"]["devman"]["devices"]["_items"] != []:
            if "_id" in response.data["config"]["devman"]["devices"]["_items"][0]:
                return True
        return False

    def fetch_device_ids_list(self) -> List[str]:
        url_path = "/rest/v2/data/config/devman/devices/*"
        response = self.vip_connector.rest.get(url_path)
        if not response.data:
            raise ValueError("Response data is empty.")
        return [device["_id"] for device in response.data["config"]["devman"]["devices"]["_items"]]

    def fetch_device_ids_by_driver(self, driver: DriverLiteral) -> List[str]:
        """Fetch all device IDs by driver ID from VideoIPath-Inventory with natural sorting."""
        driver_organization, driver_name, driver_version = extract_driver_info_from_id(driver_id=driver)

        escaped_driver_organization = urllib.parse.quote(driver_organization, safe="")
        escaped_driver_name = urllib.parse.quote(driver_name, safe="")
        escaped_driver_version = urllib.parse.quote(driver_version, safe="")

        url_path = (
            f"/rest/v2/data/config/devman/devices/* "
            f"where (config.driver.name='{escaped_driver_name}' "
            f"and config.driver.version='{escaped_driver_version}' "
            f"and config.driver.organization='{escaped_driver_organization}') /**"
        )

        response = self.vip_connector.rest.get(url_path)

        if not response.data:
            raise ValueError("Response data is empty.")

        device_ids = [device["_id"] for device in response.data["config"]["devman"]["devices"]["_items"]]
        return sorted(device_ids, key=extract_natural_sort_key)

    # --- Bulk Device Label Fetching Methods ---
    def fetch_devices_factory_labels_as_dict(self) -> dict[str, str]:
        """Method to fetch all device factory labels from VideoIPath-Inventory

        Returns:
            dict: {device_id: factory_device_label}
        """
        url = "/rest/v2/data/status/devman/devices/*/deviceInfo/label"
        response = self.vip_connector.rest.get(url)
        if not response.data:
            raise ValueError("Response data is empty.")
        return {
            device["_id"]: device["deviceInfo"]["label"]
            for device in response.data["status"]["devman"]["devices"]["_items"]
        }

    def fetch_devices_user_defined_labels_as_dict(self) -> dict[str, str]:
        """
        Method to fetch all user defined device labels from VideoIPath-Inventory

        Returns:
            dict: {device_id: user_defined_device_label}
        """
        url = "/rest/v2/data/config/devman/devices/*/config/desc/label"
        response = self.vip_connector.rest.get(url)
        if not response.data:
            raise ValueError("Response data is empty.")
        return {
            device["_id"]: device["config"]["desc"]["label"]
            for device in response.data["config"]["devman"]["devices"]["_items"]
        }

    def fetch_devices_canonical_labels_as_dict(self) -> dict[str, str]:
        """Method to fetch all canonical device labels from VideoIPath-Inventory

        Returns:
            dict: {device_id: canonical_device_label}
        """
        url = "/rest/v2/data/status/devman/devices/*/canonicalLabel"
        response = self.vip_connector.rest.get(url)
        if not response.data:
            raise ValueError("Response data is empty.")
        return {
            device["_id"]: device["canonicalLabel"] for device in response.data["status"]["devman"]["devices"]["_items"]
        }

    def filter_ids_from_label_dict(self, label_dict: dict, label: str) -> Optional[str | List[str]]:
        """
        Method to filter device ids from a label dictionary by given label.
        If label is not found, None is returned.
        If multiple devices with the same label are found, a list of device ids is returned.

        Args:
            label_dict (dict): Dictionary with device ids and labels
            label (str): Label to filter

        Returns:
            Optional[str | List[str]]: Device id or list of device ids
        """
        if not label:
            raise ValueError("Label must not be empty.")

        device_ids = [device_id for device_id, device_label in label_dict.items() if device_label == label]
        if len(device_ids) == 0:
            return None
        elif len(device_ids) == 1:
            return device_ids[0]
        else:
            return device_ids

    # --- Targeted Device Lookup Methods ---
    def get_device_id_by_user_defined_label(self, label: str) -> Optional[str | List[str]]:
        """Method to get a device id by user-defined label from VideoIPath-Inventory

        Args:
            label (str): User-defined label

        Returns:
            Optional[str | List[str]]: Device id, None if label does not exist, List of device ids if multiple devices with the same label exist
        """
        if not label:
            raise ValueError("Label must not be empty.")

        escaped_label = urllib.parse.quote(label, safe="")
        url = f"/rest/v2/data/config/devman/devices/* where config.desc.label='{escaped_label}' /_id"
        response = self.vip_connector.rest.get(url)

        if response.data and response.data["config"]["devman"]["devices"]["_items"]:
            if len(response.data["config"]["devman"]["devices"]["_items"]) == 1:
                return response.data["config"]["devman"]["devices"]["_items"][0]["_id"]
            elif len(response.data["config"]["devman"]["devices"]["_items"]) > 1:
                return [device["_id"] for device in response.data["config"]["devman"]["devices"]["_items"]]
        return None

    def get_device_id_by_canonical_label(self, label: str) -> Optional[str | List[str]]:
        """Method to get a device id by canonical label from VideoIPath-Inventory

        Args:
            label (str): Canonical label

        Returns:
            Optional[str | List[str]]: Device id, None if label does not exist, List of device ids if multiple devices with the same label exist
        """
        if not label:
            raise ValueError("Label must not be empty.")

        escaped_label = urllib.parse.quote(label, safe="")
        url = f"/rest/v2/data/status/devman/devices/* where canonicalLabel='{escaped_label}' /_id"
        response = self.vip_connector.rest.get(url)

        if response.data and response.data["status"]["devman"]["devices"]["_items"]:
            if len(response.data["status"]["devman"]["devices"]["_items"]) == 1:
                return response.data["status"]["devman"]["devices"]["_items"][0]["_id"]
            elif len(response.data["status"]["devman"]["devices"]["_items"]) > 1:
                return [device["_id"] for device in response.data["status"]["devman"]["devices"]["_items"]]
        return None

    def get_device_id_by_factory_label(self, label: str) -> Optional[str | List[str]]:
        """Method to get a device id by factory label from VideoIPath-Inventory

        Args:
            label (str): Factory label

        Returns:
            Optional[str | List[str]]: Device id, None if label does not exist, List of device ids if multiple devices with the same label exist
        """
        if not label:
            raise ValueError("Label must not be empty.")

        escaped_label = urllib.parse.quote(label, safe="")
        url = f"/rest/v2/data/status/devman/devices/* where deviceInfo.label='{escaped_label}' /_id"
        response = self.vip_connector.rest.get(url)

        if response.data and response.data["status"]["devman"]["devices"]["_items"]:
            if len(response.data["status"]["devman"]["devices"]["_items"]) == 1:
                return response.data["status"]["devman"]["devices"]["_items"][0]["_id"]
            elif len(response.data["status"]["devman"]["devices"]["_items"]) > 1:
                return [device["_id"] for device in response.data["status"]["devman"]["devices"]["_items"]]
        return None

    def get_device_id_by_address(self, address: str, include_alt_addresses: bool = True) -> Optional[str | List[str]]:
        """Method to get a device id by address from VideoIPath-Inventory

        Args:
            address (str): Address / AltAddress of device
            include_alt_addresses (bool, optional): Include AltAddresses in search. Defaults to True.

        Returns:
            Optional[str | List[str]]: Device id, None if address does not exist, List of device ids if multiple devices with the same address exist
        """
        if include_alt_addresses:
            url = "/rest/v2/data/config/devman/devices/*/config/cinfo/address,altAddresses,altAddresses/**"
            # altAddresses contains all addresses from altAddressesWithAuth, therefore no need to fetch altAddressesWithAuth
        else:
            escaped_address = urllib.parse.quote(address, safe="")
            url = f"/rest/v2/data/config/devman/devices/* where config.cinfo.address='{escaped_address}' /_id"

        response = self.vip_connector.rest.get(url)

        if response.data and response.data["config"]["devman"]["devices"]["_items"]:
            devices = response.data["config"]["devman"]["devices"]["_items"]
        else:
            raise ValueError("Response data is empty.")

        device_ids = []
        for device in devices:
            if (
                address in device["config"]["cinfo"].get("altAddresses")
                or address == device["config"]["cinfo"]["address"]
            ):
                device_ids.append(device["_id"])

        if len(device_ids) == 0:
            return None
        elif len(device_ids) == 1:
            return device_ids[0]
        else:
            return device_ids

    def get_device_id_by_meta_field_value(self, meta_field: str, value: str) -> Optional[str | List[str]]:
        """Method to get a device id by given meta field value from VideoIPath-Inventory

        Args:
            meta_field (str): Meta field name
            value (str): Meta field value

        Returns:
            Optional[str | List[str]]: Device id, None if value does not exist, List of device ids if multiple devices with the same value exist
        """

        if not meta_field:
            raise ValueError("Meta field must not be empty.")
        if not value:
            raise ValueError("Value must not be empty.")

        escaped_field = urllib.parse.quote(meta_field, safe="")
        escaped_value = urllib.parse.quote(value, safe="")

        url = f"/rest/v2/data/config/devman/devices/* where meta.{escaped_field}='{escaped_value}' /_id"
        response = self.vip_connector.rest.get(url)

        if response.data and response.data["config"]["devman"]["devices"]["_items"]:
            devices = response.data["config"]["devman"]["devices"]["_items"]
        else:
            raise ValueError("Response data is empty.")

        device_ids = [device["_id"] for device in devices]
        if len(device_ids) == 0:
            return None
        elif len(device_ids) == 1:
            return device_ids[0]
        else:
            return device_ids

    # --- Discovered Device Management Methods ---
    def get_discovered_devices(self) -> List[DiscoveredInventoryDevice]:
        """Method to get all discovered devices from VideoIPath-Inventory

        Returns:
            List[InventoryDevice]: List of discovered devices
        """
        url = "/rest/v2/data/status/devman/discoveredDevices/**"
        response = self.vip_connector.rest.get(url)
        if not response.data:
            raise ValueError("Response data is empty.")

        # Add driver_id to custom settings
        for device in response.data["status"]["devman"]["discoveredDevices"]["_items"]:
            for config in device["suggestedConfigs"]:
                config["customSettings"]["driver_id"] = construct_driver_id_from_info(
                    driver_organization=config["driver"]["organization"],
                    driver_name=config["driver"]["name"],
                    driver_version=config["driver"]["version"],
                )

        return [
            DiscoveredInventoryDevice.model_validate(device)
            for device in response.data["status"]["devman"]["discoveredDevices"]["_items"]
        ]

    def get_discovered_device(self, discovered_device_id: str) -> DiscoveredInventoryDevice:
        """Method to get a discovered device by id from VideoIPath-Inventory

        Args:
            id (str): Device ID

        Returns:
            InventoryDevice: Discovered device object
        """
        url = f"/rest/v2/data/status/devman/discoveredDevices/* where _id='{discovered_device_id}' /**"
        response = self.vip_connector.rest.get(url)
        if not response.data:
            raise ValueError("Response data is empty.")

        if len(response.data["status"]["devman"]["discoveredDevices"]["_items"]) > 1:
            raise ValueError(f"Multiple devices with id '{discovered_device_id}' found.")

        # Add driver_id to custom settings
        device = response.data["status"]["devman"]["discoveredDevices"]["_items"][0]
        for config in device["suggestedConfigs"]:
            config["customSettings"]["driver_id"] = construct_driver_id_from_info(
                driver_organization=config["driver"]["organization"],
                driver_name=config["driver"]["name"],
                driver_version=config["driver"]["version"],
            )

        return DiscoveredInventoryDevice.model_validate(
            response.data["status"]["devman"]["discoveredDevices"]["_items"][0]
        )

    # --- Global SNMP Configuration Helpers ---
    def get_global_snmp_config_id_by_label(self, label: str) -> Optional[str | List[str]]:
        """Method to get the global SNMP configuration id by label.
        Note: If multiple SNMP configurations with the same label exist, a list of ids is returned.

        Args:
            label (str): Label of the SNMP configuration

        Returns:
            Optional[str | List[str]]: SNMP configuration id, None if not found, List of ids if multiple configurations with the same label exist
        """
        if not label:
            raise ValueError("Label must not be empty.")

        escaped_label = urllib.parse.quote(label, safe="")
        url = f"/rest/v2/data/config/system/snmp/*/* where descriptor.label='{escaped_label}' /*"
        response = self.vip_connector.rest.get(url)
        if response.data and response.data["config"]["system"]["snmp"]["session"]:
            matches = response.data["config"]["system"]["snmp"]["session"]
            if len(matches) == 1:
                return list(matches.keys())[0]
            elif len(matches) > 1:
                self._logger.warning(
                    f"Multiple SNMP configurations found with label '{label}''. Returning all matching ids."
                )
                return list(matches.keys())
        return None

    def get_global_snmp_config_label_by_id(self, snmp_config_id: str) -> Optional[str]:
        """Method to get the global SNMP configuration label by id.

        Args:
            snmp_config_id (str): SNMP configuration id

        Returns:
            Optional[str]: SNMP configuration label, None if not found
        """
        if not snmp_config_id:
            raise ValueError("SNMP configuration id must not be empty.")

        url = f"/rest/v2/data/config/system/snmp/session/{snmp_config_id}/descriptor/label"
        response = self.vip_connector.rest.get(url, node_check=False)
        if response.data and response.data["config"]["system"]["snmp"]["session"]:
            if snmp_config_id in response.data["config"]["system"]["snmp"]["session"]:
                return response.data["config"]["system"]["snmp"]["session"][snmp_config_id]["descriptor"]["label"]
        return None

    def get_all_global_snmp_config_ids(self) -> dict[str, str]:
        """Method to list all global SNMP configuration ids with their labels.

        Returns:
            dict: {snmp_config_id: snmp_config_label}
        """
        url = "/rest/v2/data/config/system/snmp/*/*/descriptor/label"
        response = self.vip_connector.rest.get(url)
        if not response.data:
            raise ValueError("Response data is empty.")

        snmp_configs = response.data["config"]["system"]["snmp"]["session"]
        return {
            snmp_config_id: snmp_config["descriptor"]["label"] for snmp_config_id, snmp_config in snmp_configs.items()
        }

    # --- Global SNMP Configuration CRUD Methods ---
    def get_global_snmp_config(self, snmp_config_id: str) -> SnmpConfiguration:
        """Method to get a global SNMP configuration by id from VideoIPath-Inventory

        Args:
            snmp_config_id (str): SNMP configuration id

        Returns:
            GlobalSnmpConfig: Global SNMP configuration object
        """
        if not snmp_config_id:
            raise ValueError("SNMP configuration id must not be empty.")

        url = f"/rest/v2/data/config/system/snmp/session/{snmp_config_id}/**"
        response = self.vip_connector.rest.get(url)
        if not response.data:
            raise ValueError("Response data is empty.")

        return SnmpConfiguration.parse_from_dict(response.data["config"]["system"]["snmp"]["session"])

    def add_global_snmp_config(self, snmp_config: SnmpConfiguration) -> SnmpConfiguration:
        """Method to add a new global SNMP configuration

        Args:
            snmp_config (SnmpConfiguration): SNMP configuration object to add

        Returns:
            SnmpConfiguration: Added SNMP configuration object
        """
        if not snmp_config.id:
            raise ValueError("SNMP configuration id must be set.")

        self._logger.debug(f"Adding new global SNMP configuration with id '{snmp_config.id}'.")

        existing_configs_label = self.get_global_snmp_config_label_by_id(snmp_config.id)
        if existing_configs_label is not None:
            raise ValueError(f"SNMP configuration with id '{snmp_config.id}' already exists. Please update it instead.")

        body = SnmpRequestRpc()
        body.add(snmp_config)

        response = self.vip_connector.rpc.post("/api/updateSnmpConfig", body=body)

        if response.header.status != "OK":
            raise ValueError(f"Failed to add global SNMP configuration. Error: {response}")

        return self.get_global_snmp_config(snmp_config_id=snmp_config.id)

    def update_global_snmp_config(self, snmp_config: SnmpConfiguration) -> SnmpConfiguration:
        """Method to update a global SNMP configuration

        Args:
            snmp_config (SnmpConfiguration): SNMP configuration object to update

        Returns:
            SnmpConfiguration: Updated SNMP configuration object
        """
        if not snmp_config.id:
            raise ValueError("SNMP configuration id must be set.")

        self._logger.debug(f"Updating global SNMP configuration with id '{snmp_config.id}'.")

        existing_configs_label = self.get_global_snmp_config_label_by_id(snmp_config.id)
        if existing_configs_label is None:
            raise ValueError(f"SNMP configuration with id '{snmp_config.id}' does not exist. Please add it first.")

        body = SnmpRequestRpc()
        body.update(snmp_config)

        response = self.vip_connector.rpc.post("/api/updateSnmpConfig", body=body)

        if response.header.status != "OK":
            raise ValueError(f"Failed to update global SNMP configuration. Error: {response}")

        return self.get_global_snmp_config(snmp_config_id=snmp_config.id)

    def remove_global_snmp_config(self, snmp_config_id: str) -> ResponseRPC:
        """Method to remove a global SNMP configuration by id from VideoIPath-Inventory

        Args:
            snmp_config_id (str): SNMP configuration id

        Returns:
            ResponseRPC: Response object
        """
        if not snmp_config_id:
            raise ValueError("SNMP configuration id must be set.")

        self._logger.debug(f"Removing global SNMP configuration with id '{snmp_config_id}'.")

        body = SnmpRequestRpc()
        body.remove(snmp_config_id)

        response = self.vip_connector.rpc.post("/api/updateSnmpConfig", body=body)

        if response.header.status != "OK":
            raise ValueError(f"Failed to remove global SNMP configuration. Error: {response}")

        return response

    # --- Deprecated Methods ---
    @deprecated(
        "The method `fetch_device_ids_list` is deprecated and will be removed in a future release. ",
    )
    def get_device_ids_legacy(self, address: Optional[IPvAnyAddress | str] = None, label: Optional[str] = None) -> dict:
        """Method to get device id/s from VideoIPath-Inventory filtered by ip_address or label.
            Note: Only one of 'ip_address' or 'label' can be provided! Label filtering only works for manually set labels.

        Args:
            ip_address (str, optional): IP address (including altAddresses) of device. Defaults to None.
            label (str, optional): Label of device. Defaults to None.

        Returns:
            dict: {"active": [device_id], "inactive": [device_id]}
        """
        request_base_url = "/rest/v2/data/config/devman/devices/*"

        if address and label:
            raise ValueError("Only one of 'ip_address' or 'label' can be provided.")
        elif address:
            mode = "ip"
            request_filter = "/active, config/cinfo/address,altAddresses/**"
        elif label:
            mode = "label"
            escaped_label = urllib.parse.quote(label, safe="")
            request_filter = f"where config.desc.label='{escaped_label}' /active"
        else:
            mode = "all"
            request_filter = "/active"

        response = self.vip_connector.rest.get(f"{request_base_url} {request_filter}")

        if response.data:
            devices = response.data["config"]["devman"]["devices"]["_items"]
        else:
            raise ValueError("Response data is empty.")

        if mode == "ip":
            # Filter devices by ip address => IP must set as main address or in altAddresses
            devices = [
                device
                for device in devices
                if str(address) in device["config"]["cinfo"]["altAddresses"]
                or str(address) == device["config"]["cinfo"]["address"]
            ]

        return {
            "active": [device["_id"] for device in devices if device["active"]],
            "inactive": [device["_id"] for device in devices if not device["active"]],
        }

    @deprecated(
        "The method `get_device_id_list` is deprecated and will be removed in a future release. Please use `fetch_device_ids` instead. ",
    )
    def get_device_id_list(self) -> List[str]:
        """Method to get a list of all device ids in VideoIPath-Inventory"""
        return self.fetch_device_ids_list()

    @deprecated(
        "The method `device_id_exists` is deprecated and will be removed in a future release. Please use `check_device_id_exists` instead. ",
    )
    def device_id_exists(self, device_id: str) -> bool:
        """Method to check if a device id exists in VideoIPath-Inventory"""
        return self.check_device_id_exists(device_id)

    @deprecated(
        "The method `device_label_exists` is deprecated and will be removed in a future release. Please use `check_device_user_defined_label_exists` instead. ",
    )
    def device_label_exists(self, label: str) -> Optional[str | List[str]]:
        """Method to check if a device with given user-defined label exists in VideoIPath-Inventory

        Args:
            label (str): User defined label to check

        Returns:
            None | List[str]: List of device ids with the given label, None if label does not exist
        """
        data = self.get_device_id_by_user_defined_label(label)
        return data

    @deprecated(
        "The method `get_device_label_id_dict` is deprecated and will be removed in a future release. ",
    )
    def get_device_label_id_dict(self) -> dict:
        """Method to get a dictionary of all devices in VideoIPath-Inventory with id, label and ip
        Returns:
            dict: {device_id: {"label": device_label_manually_set, "canonicalLabel": device_label_canonical, "address": device_ip}}
        """
        url = "/rest/v2/data/config/devman/devices/*/config/*/label,address"
        config_data = self.vip_connector.rest.get(url)
        url = "/rest/v2/data/status/devman/devices/*/canonicalLabel"
        status_data = self.vip_connector.rest.get(url)

        if not config_data.data or not status_data.data:
            raise ValueError("Response data is empty.")

        device_dict = {}
        for device in config_data.data["config"]["devman"]["devices"]["_items"]:
            device_id = device["_id"]
            device_dict[device_id] = {
                "label": device["config"]["desc"]["label"],
                "address": device["config"]["cinfo"]["address"],
                "canonicalLabel": None,  # will be filled later
            }

        for status_device in status_data.data["status"]["devman"]["devices"]["_items"]:
            if status_device["_id"] in device_dict and "canonicalLabel" in status_device:
                device_dict[status_device["_id"]]["canonicalLabel"] = status_device["canonicalLabel"]

        return device_dict
