from deepdiff.diff import DeepDiff
from pydantic import BaseModel, Field

from videoipath_automation_tool.apps.inventory.model.inventory_device import InventoryDevice


class InventoryDeviceConfigurationDiff(BaseModel):
    """Class which contains the configuration differences on attribute level between two Inventory device configs."""

    added: list = Field(default_factory=list)
    changed: list = Field(default_factory=list)
    removed: list = Field(default_factory=list)


class InventoryDeviceComparison(BaseModel):
    """Class which contains the differences between two devices from VideoIPath-Inventory."""

    reference_device: InventoryDevice
    staged_device: InventoryDevice
    configuration_diff: InventoryDeviceConfigurationDiff

    def get_all_differences(
        self, include_password_diffs: bool = True, include_device_id_diff: bool = True
    ) -> InventoryDeviceConfigurationDiff:
        """
        Returns all differences between the reference and staged device. Optionally, password differences can be excluded.

        Args:
            include_password_diffs (bool): If False, all differences related to passwords will be excluded.
            include_device_id_diff (bool): If False, the device_id difference will be excluded.

        Returns:
            InventoryDeviceConfigurationDiff: A copy of the object containing all differences between the two devices.
        """
        config_diff_copy = self.configuration_diff.model_copy(deep=True)

        if not include_password_diffs:
            config_diff_copy.added = [
                element
                for element in config_diff_copy.added
                if not (
                    element["path"] == "root['config']['cinfo']['auth']['password']"
                    or element["path"].startswith("root['config']['cinfo']['altAddressesWithAuth']")
                )
            ]
            config_diff_copy.changed = [
                element
                for element in config_diff_copy.changed
                if not (
                    element["path"] == "root['config']['cinfo']['auth']['password']"
                    or element["path"].startswith("root['config']['cinfo']['altAddressesWithAuth']")
                )
            ]
            config_diff_copy.removed = [
                element
                for element in config_diff_copy.removed
                if not (
                    element["path"] == "root['config']['cinfo']['auth']['password']"
                    or element["path"].startswith("root['config']['cinfo']['altAddressesWithAuth']")
                )
            ]

        if not include_device_id_diff:
            config_diff_copy.added = [element for element in config_diff_copy.added if element["path"] != "root['id']"]
            config_diff_copy.changed = [
                element for element in config_diff_copy.changed if element["path"] != "root['id']"
            ]
            config_diff_copy.removed = [
                element for element in config_diff_copy.removed if element["path"] != "root['id']"
            ]

        return config_diff_copy

    @staticmethod
    def get_value_by_path(dict_data: dict, path: str):
        """
        Function to access nested values in a dictionary using a DeepDiff styled string path.

        Args:
            dict_data (dict): The dictionary to access the value from.
            path (str): The path to the value. e.g., "root['meta']['abc']"
        """
        path = path.removeprefix("root")

        # Convert the string path into a list of keys
        path_parts = path_parts = path.replace("']['", "/")[2:-2].split("/")

        # extract the value
        for part in path_parts:
            dict_data = dict_data[part]
        return dict_data

    @classmethod
    def analyze_inventory_devices(
        cls, reference_device: InventoryDevice, staged_device: InventoryDevice, ignore_authentification: bool = True
    ) -> "InventoryDeviceComparison":
        """Analyze the differences between two Inventory devices."""

        element_differences = DeepDiff(
            reference_device.configuration.model_dump(), staged_device.configuration.model_dump(), ignore_order=True
        )  # Note: To exclude Getters, model_dump() is used
        difference_keys = element_differences.keys()

        diff_object = InventoryDeviceConfigurationDiff()

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
                raise ValueError(f"Disallowed differences: {difference_keys} - {element_differences}")

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
                        "old_type": str(element_differences["type_changes"][type_change]["old_type"]),
                        "new_type": str(element_differences["type_changes"][type_change]["new_type"]),
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
                        "new_value": InventoryDeviceComparison.get_value_by_path(
                            element_differences.t2, dictionary_item_added
                        ),
                    }
                    diff_object.added.append(data_element)

            if "dictionary_item_removed" in element_differences:
                for dictionary_item_removed in element_differences["dictionary_item_removed"]:
                    data_element = {
                        "type": "dictionary_item_removed",
                        "path": dictionary_item_removed,
                        "old_value": InventoryDeviceComparison.get_value_by_path(
                            element_differences.t1, dictionary_item_removed
                        ),
                    }
                    diff_object.removed.append(data_element)

            if "unprocessed" in element_differences:
                raise ValueError(f"Unprocessed differences: {element_differences['unprocessed']}")

        return cls(
            reference_device=reference_device,
            staged_device=staged_device,
            configuration_diff=diff_object,
        )
