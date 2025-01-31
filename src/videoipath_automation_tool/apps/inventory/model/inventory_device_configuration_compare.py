from deepdiff.diff import DeepDiff
from pydantic import BaseModel

from videoipath_automation_tool.apps.inventory.model.inventory_device import InventoryDevice


class InventoryDeviceConfigurationDiff(BaseModel):
    """Class which contains the configuration differences on attribute level between two Inventory device configs."""

    added: list = []
    changed: list = []
    removed: list = []


class InventoryDeviceComparison(BaseModel):
    """Class which contains the differences between two devices from VideoIPath-Inventory."""

    reference_device: InventoryDevice
    staged_device: InventoryDevice
    configuration_diff: InventoryDeviceConfigurationDiff

    @classmethod
    def analyze_inventory_devices(
        cls, reference_device: InventoryDevice, staged_device: InventoryDevice, ignore_authentification: bool = True
    ) -> "InventoryDeviceComparison":
        """Analyze the differences between two Inventory devices."""

        element_differences = DeepDiff(reference_device.configuration, staged_device.configuration, ignore_order=True)
        difference_keys = element_differences.keys()

        if len(difference_keys) > 0:
            allowed_diff_types = [  # noqa: F841 
                "values_changed",  # Indicates changes in values between two comparable objects
                "type_changes",  # Indicates changes in the data type of an object
                "iterable_item_added",  # Identifies items added to an iterable (e.g., lists, tuples)
                "iterable_item_removed",  # Identifies items removed from an iterable (e.g., lists, tuples)
                "unprocessed"  # Indicates differences that were not processed by DeepDiff
                "dictionary_item_added",  # Identifies items added to a dictionary
                "dictionary_item_removed",  # Identifies items removed from a dictionary
            ] 

            disallowed_diff_types = [
                "set_item_added",  # Shows items added to a set in the comparison object
                "set_item_removed",  # Shows items removed from a set in the comparison object
                "iterable_item_moved",  # Indicates items that were moved to a new position in an iterable
                "repetition_change",  # Detects changes in the frequency of repeated items in an iterable
                "attribute_added",  # Identifies attributes added to an object
                "attribute_removed",  # Identifies attributes removed from an object
                "attribute_value_changed",  # Indicates changes in the value of an attribute
            ]

            if any([diff_type in difference_keys for diff_type in disallowed_diff_types]):
                raise ValueError(f"Disallowed differences in nGraphElement: {difference_keys} - {element_differences}")

            diff_object = InventoryDeviceConfigurationDiff()

            # Check allowed diff types
            if "values_changed" in element_differences:
                for value_changed in element_differences["values_changed"]:
                    data_element = {
                        "type": "value_changed",
                        "path": value_changed,
                        "old_value": element_differences["values_changed"][value_changed]["old_value"],
                        "new_value": element_differences["values_changed"][value_changed]["new_value"],
                    }
                    diff_object.changed.append(data_element)

            if "type_changes" in element_differences:
                for type_change in element_differences["type_changes"]:
                    data_element = {
                        "type": "type_changed",
                        "path": type_change,
                        "old_type": element_differences["type_changes"][type_change]["old_type"],
                        "new_type": element_differences["type_changes"][type_change]["new_type"],
                    }
                    if "old_value" in element_differences["type_changes"][type_change]:
                        data_element["old_value"] = element_differences["type_changes"][type_change]["old_value"]
                    if "new_value" in element_differences["type_changes"][type_change]:
                        data_element["new_value"] = element_differences["type_changes"][type_change]["new_value"]
                    diff_object.changed.append(data_element)

            if "iterable_item_added" in element_differences:
                for iterable_item_added in element_differences["iterable_item_added"]:
                    data_element = {
                        "type": "iterable_item_added",
                        "path": iterable_item_added,
                        "value": element_differences["iterable_item_added"][iterable_item_added],
                    }
                    diff_object.added.append(data_element)

            if "iterable_item_removed" in element_differences:
                for iterable_item_removed in element_differences["iterable_item_removed"]:
                    data_element = {
                        "type": "iterable_item_removed",
                        "path": iterable_item_removed,
                        "value": element_differences["iterable_item_removed"][iterable_item_removed],
                    }
                    diff_object.removed.append(data_element)

            if "dictionary_item_added" in element_differences:
                for dictionary_item_added in element_differences["dictionary_item_added"]:
                    data_element = {
                        "type": "dictionary_item_added",
                        "path": dictionary_item_added,
                        "value": element_differences["dictionary_item_added"][dictionary_item_added],
                    }
                    diff_object.added.append(data_element)

            if "dictionary_item_removed" in element_differences:
                for dictionary_item_removed in element_differences["dictionary_item_removed"]:
                    data_element = {
                        "type": "dictionary_item_removed",
                        "path": dictionary_item_removed,
                        "value": element_differences["dictionary_item_removed"][dictionary_item_removed],
                    }
                    diff_object.removed.append(data_element)

            if "unprocessed" in element_differences:
                raise ValueError(f"Unprocessed differences: {element_differences['unprocessed']}")

        return cls(
            reference_device=reference_device,
            staged_device=staged_device,
            configuration_diff=diff_object,
        )
