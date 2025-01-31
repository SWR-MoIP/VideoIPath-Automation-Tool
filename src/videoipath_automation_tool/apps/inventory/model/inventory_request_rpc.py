from videoipath_automation_tool.apps.inventory.model.inventory_device import InventoryDevice
from videoipath_automation_tool.connector.models.request_rpc import RequestRpc


class InventoryRequestRpc(RequestRpc):
    # Wrapper class for RequestRpc

    def add(self, device: InventoryDevice):
        """Method to add a new device with config to VideoIPath-Inventory

        Args:
            device (InventoryDevice): Device to add
        """
        return super().add(device.configuration.id, device.configuration)

    def update(self, device: InventoryDevice):
        """Method to update a device config in VideoIPath-Inventory

        Args:
            device (InventoryDevice): Device to update
        """
        return super().update(device.configuration.id, device.configuration)

    def remove(self, device_id: str | list[str]):
        """Method to remove a device from VideoIPath-Inventory

        Args:
            device_id (str | list[str]): Id or List of Ids of the device
        """
        return super().remove(device_id)
