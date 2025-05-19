from videoipath_automation_tool.apps.inventory.model.inventory_device import InventoryDevice
from videoipath_automation_tool.connector.models.request_rpc import RequestRPC
from videoipath_automation_tool.validators.device_id import validate_device_id


class InventoryRequestRpc(RequestRPC):
    # Wrapper class for RequestRpc

    def add(self, device: InventoryDevice):
        """Method to add a new device with config to VideoIPath-Inventory

        Args:
            device (InventoryDevice): Device to add
        """
        if device.configuration.id != "":
            raise ValueError("Device ID must be empty for adding a new device!")
        return super().add(device.configuration.id, device.configuration)

    def update(self, device: InventoryDevice):
        """Method to update a device config in VideoIPath-Inventory

        Args:
            device (InventoryDevice): Device to update
        """
        try:
            validate_device_id(device.configuration.id)
        except ValueError as e:
            raise ValueError(
                f"To update a device, a valid 'device_id' must be set in the device configuration. Error: {e}"
            )
        return super().update(device.configuration.id, device.configuration)

    def remove(self, device_id: str | list[str]):
        """Method to remove a device from VideoIPath-Inventory

        Args:
            device_id (str | list[str]): Id or List of Ids of the device
        """
        try:
            if isinstance(device_id, list):
                for d_id in device_id:
                    validate_device_id(d_id)
            else:
                validate_device_id(device_id)
        except ValueError as e:
            raise ValueError(f"Invalid device_id(s) given. Error: {e}")
        return super().remove(device_id)
