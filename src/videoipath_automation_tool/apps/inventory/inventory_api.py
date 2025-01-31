import logging
import time
from typing import List, Optional
from pydantic import BaseModel, IPvAnyAddress, model_validator
from uuid import uuid4

from videoipath_automation_tool.apps.inventory.model.device_status import DeviceStatus
from videoipath_automation_tool.apps.inventory.model.inventory_device import InventoryDevice
from videoipath_automation_tool.apps.inventory.model.inventory_request_rpc import InventoryRequestRpc
from videoipath_automation_tool.apps.utils.cross_app_utils import validate_device_id_string
from videoipath_automation_tool.connector.models.response_rpc import ResponseRPC
from videoipath_automation_tool.connector.vip_connector import VideoIPathConnector


class InventoryAPI(BaseModel):
    """
    Class for VideoIPath inventory API.
    """

    vip_connector: VideoIPathConnector
    model_config: dict = {"arbitrary_types_allowed": True}
    logger: Optional[logging.Logger] = None

    @model_validator(mode="after")
    def initialize_connector(self):
        if self.logger is None:
            self.logger = logging.getLogger(
                "videoipath_automation_tool_inventory_api"
            )  # use fallback logger if no logger is provided
            self.logger.debug(
                "No logger for connector provided. Using fallback logger: 'videoipath_automation_tool_inventory_api'."
            )
        self.logger.debug("Inventory API logger initialized.")
        return self

    def get_device_ids(self, address: Optional[IPvAnyAddress | str] = None, label: Optional[str] = None) -> dict:
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
            request_filter = f"where config.desc.label='{label}' /active"
        else:
            mode = "all"
            request_filter = "/active"

        response = self.vip_connector.http_get_v2(f"{request_base_url} {request_filter}")

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

    def get_device(self, device_id: str, config_only: bool = False) -> InventoryDevice:
        """Method to get a device by device id from VideoIPath-Inventory

        Args:
            device_id (str): Device ID

        Returns:
            InventoryDevice: Device object
        """
        if not device_id.startswith("device"):
            raise ValueError("device_id must start with 'device'.")
        self.logger.debug(f"Retrieving device '{device_id}' from VideoIPath-Inventory.")
        device = self._get_device_config(device_id)
        if not config_only:
            device.status = self._get_device_status(device_id)
        else:
            self.logger.debug(f"Skipping status update for device '{device_id}'.")
        self.logger.debug(f"Device '{device_id}' retrieved from VideoIPath-Inventory.")
        return device

    def refresh_device_status(self, device: InventoryDevice) -> InventoryDevice:
        """Method to update the status of a device in VideoIPath-Inventory"""
        if not device.configuration.id.startswith("device"):
            raise ValueError("device_id must start with 'device'.")
        device.status = self._get_device_status(device.configuration.id)
        return device

    def add_device(
        self, device: InventoryDevice, clear_uuid_after_add: bool = True, config_only: bool = False
    ) -> InventoryDevice:
        """Method to add a new device with config to VideoIPath-Inventory

        Args:
            device (InventoryDevice): Device object to add
            clear_uuid_after_add (bool, optional): Remove UUID from online device configuration after adding. Defaults to True.

        Raises:
            ValueError: Raised if adding device fails.

        Returns:
            InventoryDevice: Online device object with  backend generated ID
        """
        self.logger.debug(
            f"Adding new device with label '{device.configuration.config.desc.label}' to VideoIPath-Inventory."
        )

        tracking_id = str(uuid4())
        self.logger.debug(f"Tracking ID generated: {tracking_id}")

        modified_device = device.model_copy(deep=True)
        modified_device.configuration.meta["uuid"] = tracking_id
        self.logger.debug(
            f"Modified device configuration with tracking ID: {modified_device.configuration.meta['uuid']}"
        )

        body = InventoryRequestRpc()
        # temporary workaround to set driver_id in customSettings
        driver_organization = modified_device.configuration.config.driver.organization
        driver_name = modified_device.configuration.config.driver.name
        driver_version = modified_device.configuration.config.driver.version
        modified_device.configuration.config.customSettings.driver_id = (
            f"{driver_organization}.{driver_name}-{driver_version}"
        )
        body.add(modified_device)
        # remove driver_id from customSettings
        modified_device.configuration.config.customSettings.__delattr__("driver_id")
        dumped_body = body.model_dump(mode="json")
        self.logger.debug(f"RPC Request body generated: {dumped_body}")

        response = self.vip_connector.http_post_rpc("/api/updateDevices", body=dumped_body)

        if response.header.status != "OK":
            raise ValueError(f"Failed to add device to VideoIPath-Inventory. Error: {response}")

        online_device = self._get_device_config_by_uuid(uuid=tracking_id)
        if not config_only:
            # retry to get status:
            retry_cnt = 20
            while retry_cnt > 0:
                try:
                    online_device.status = self._get_device_status(online_device.configuration.id)
                    if online_device.status:
                        break
                except ValueError:
                    self.logger.debug(
                        f"Failed to get device status for device '{online_device.configuration.id}', retrying ({21-retry_cnt}/20) ..."
                    )
                    time.sleep(2)
                    retry_cnt -= 1
            if retry_cnt == 0 and not online_device.status:
                raise ValueError(f"Failed to get device status for device '{online_device.configuration.id}'.")
        self.logger.debug(f"Device added successfully with id: {online_device.configuration.id}")

        if clear_uuid_after_add:
            modified_device = online_device.model_copy(deep=True)
            modified_device.configuration.meta.pop("uuid")
            self.logger.debug("Removed tracking ID from device configuration.")

            self.update_device(device=modified_device)
            if response.header.status != "OK":
                raise ValueError(f"Failed to update device in VideoIPath-Inventory. Error: {response}")

            online_device = modified_device
            self.logger.debug("Tracking ID removed successfully from device configuration.")
        return online_device

    def update_device(self, device: InventoryDevice, config_only: bool = False) -> InventoryDevice:
        """Method to update a device config in VideoIPath-Inventory"""
        self.logger.debug(f"Updating device with id '{device.configuration.id}' in VideoIPath-Inventory.")
        body = InventoryRequestRpc()

        # temporary workaround to set driver_id in customSettings
        driver_organization = device.configuration.config.driver.organization
        driver_name = device.configuration.config.driver.name
        driver_version = device.configuration.config.driver.version
        device.configuration.config.customSettings.driver_id = f"{driver_organization}.{driver_name}-{driver_version}"

        body.update(device)
        # remove driver_id from customSettings
        device.configuration.config.customSettings.__delattr__("driver_id")
        dumped_body = body.model_dump(mode="json")
        self.logger.debug(f"RPC Request body generated: {dumped_body}")

        response = self.vip_connector.http_post_rpc("/api/updateDevices", body=dumped_body)

        if response.header.status != "OK":
            raise ValueError(f"Failed to update device in VideoIPath-Inventory. Error: {response}")

        online_device = self.get_device(device_id=device.configuration.id, config_only=config_only)
        self.logger.debug(f"Device updated successfully with id: {online_device.device_id}")
        return online_device

    def remove_device(self, device_id: str) -> ResponseRPC:
        """Method to remove a device from VideoIPath-Inventory"""
        self.logger.debug(f"Removing device with id '{device_id}' from VideoIPath-Inventory.")
        body = InventoryRequestRpc()
        body.remove(device_id)
        dumped_body = body.model_dump(mode="json")
        self.logger.debug(f"RPC Request body generated: {dumped_body}")

        response = self.vip_connector.http_post_rpc("/api/updateDevices", body=dumped_body)

        if response.header.status != "OK":
            raise ValueError(f"Failed to remove device from VideoIPath-Inventory. Error: {response}")

        return response

    # --- Internal Methods ---
    def _get_device_config(self, device_id: str) -> InventoryDevice:
        """Method to receive a device config by device id from VideoIPath-Inventory

        Args:
            device_id (str): Device id (e.g. "device1")

        Returns:
            InventoryDevice: Device object
        """
        if not validate_device_id_string(device_id=device_id, include_virtual=False):
            raise ValueError("device_id must start with 'device'.")
        response = self.vip_connector.http_get_v2(f"/rest/v2/data/config/devman/devices/* where id='{device_id}' /**")
        if response.data and response.data["config"]["devman"]["devices"]["_items"]:
            device = InventoryDevice.parse_configuration(response.data["config"]["devman"]["devices"]["_items"][0])
            return device
        raise ValueError(f"Device with id '{device_id}' not found.")

    def _get_device_config_by_uuid(self, uuid: str) -> InventoryDevice:
        """Method to receive a device by uuid in Meta field from VideoIPath-Inventory

        Args:
            uuid (str): UUID in Meta field of device configuration

        Returns:
            InventoryDevice: Device object
        """
        response = self.vip_connector.http_get_v2(f"/rest/v2/data/config/devman/devices/* where meta.uuid='{uuid}' /**")
        if response.data and response.data["config"]["devman"]["devices"]["_items"]:
            items = response.data["config"]["devman"]["devices"]["_items"]
            if len(items) > 1:
                raise ValueError(f"Multiple devices with uuid '{uuid}' found.")
            device = InventoryDevice.parse_configuration(items[0])
            return device
        raise ValueError(f"No device with uuid '{uuid}' found.")

    def _get_device_status(self, device_id: str) -> DeviceStatus:
        """Method to receive the status of a device by device id from VideoIPath-Inventory

        Args:
            device_id (str): Device ID

        Returns:
            DeviceStatus: Device status.
        """
        response = self.vip_connector.http_get_v2(f"/rest/v2/data/status/devman/devices/* where id='{device_id}' /**")
        if response.data and response.data["status"]["devman"]["devices"]["_items"]:
            return DeviceStatus(**response.data["status"]["devman"]["devices"]["_items"][0])
        raise ValueError(f"Device with id '{device_id}' not found.")

    # Helpers
    def get_device_id_list(self) -> List[str]:
        url_path = "/rest/v2/data/config/devman/devices/*"
        response = self.vip_connector.http_get_v2(url_path)
        if not response.data:
            raise ValueError("Response data is empty.")
        return [device["_id"] for device in response.data["config"]["devman"]["devices"]["_items"]]

    def get_device_label_id_dict(self) -> dict:
        """Method to get a dictionary of all devices in VideoIPath-Inventory with id, label and ip
        Returns:
            dict: {device_id: {"label": device_label_manually_set, "canonicalLabel": device_label_canonical, "address": device_ip}}
        """
        url = "/rest/v2/data/config/devman/devices/*/config/*/label,address"
        config_data = self.vip_connector.http_get_v2(url)
        url = "/rest/v2/data/status/devman/devices/*/canonicalLabel"
        status_data = self.vip_connector.http_get_v2(url)

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

    def device_id_exists(self, device_id: str) -> bool:
        """Method to check if a device id exists in VideoIPath-Inventory"""
        response = self.vip_connector.http_get_v2(f"/rest/v2/data/config/devman/devices/* where id='{device_id}' /_id")
        if response.data and [] != response.data["config"]["devman"]["devices"]["_items"]:
            if "_id" in response.data["config"]["devman"]["devices"]["_items"][0]:
                return True
        return False
