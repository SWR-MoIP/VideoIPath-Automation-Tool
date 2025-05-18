from typing import List

from deepdiff.diff import DeepDiff
from pydantic import BaseModel, Field

from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_codec_vertex import CodecVertex
from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_generic_vertex import GenericVertex
from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_ip_vertex import IpVertex
from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_n_graph_element import NGraphElement
from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_unidirectional_edge import (
    UnidirectionalEdge,
)
from videoipath_automation_tool.apps.topology.model.topology_device import TopologyDevice


def is_revision_path(path: str) -> bool:
    """
    Returns True if the given DeepDiff path refers to the 'rev' attribute directly under root.
    Examples that return True:
    - "root['rev']"
    - "root.rev"
    """
    path = path.strip()
    if path.startswith("root"):
        path = path[4:].strip()
    return path in (".rev", "['rev']", '["rev"]')


class NGraphElementConfigurationDiff(BaseModel):
    """Class which contains the configuration differences on attribute level between two nGraphElements."""

    added: list = Field(default_factory=list)
    changed: list = Field(default_factory=list)
    removed: list = Field(default_factory=list)

    def get_changed_ignore_rev(self) -> list:
        """Method to get the changed values of the nGraphElement, ignoring the revision."""
        return [change for change in self.changed if not is_revision_path(change["path"])]

    def get_removed_ignore_rev(self) -> list:
        """Method to get the removed values of the nGraphElement, ignoring the revision."""
        return [remove for remove in self.removed if not is_revision_path(remove["path"])]

    def get_added_ignore_rev(self) -> list:
        """Method to get the added values of the nGraphElement, ignoring the revision."""
        return [add for add in self.added if not is_revision_path(add["path"])]


class NGraphElementDiff(BaseModel):
    id: str = Field(default_factory=str)
    reference_element: NGraphElement
    staged_element: NGraphElement
    configuration_diff: NGraphElementConfigurationDiff = Field(default_factory=NGraphElementConfigurationDiff)

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
    def compare_nGraphElement(
        cls, reference_element: NGraphElement, staged_element: NGraphElement
    ) -> "NGraphElementDiff":
        """Method to compare two nGraphElements.
        Returns a dictionary with the differences between the two nGraphElements.
        """
        element_differences = DeepDiff(
            reference_element.model_dump(), staged_element.model_dump()
        )  # Note: To exclude Getters, model_dump() is used
        difference_keys = element_differences.keys()

        diff_object = NGraphElementConfigurationDiff()

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
                        "new_value": NGraphElementDiff.get_value_by_path(element_differences.t2, dictionary_item_added),
                    }
                    diff_object.added.append(data_element)

            if "dictionary_item_removed" in element_differences:
                for dictionary_item_removed in element_differences["dictionary_item_removed"]:
                    data_element = {
                        "type": "dictionary_item_removed",
                        "path": dictionary_item_removed,
                        "old_value": NGraphElementDiff.get_value_by_path(
                            element_differences.t1, dictionary_item_removed
                        ),
                    }
                    diff_object.removed.append(data_element)

            if "unprocessed" in element_differences:
                raise ValueError(f"Unprocessed differences: {element_differences['unprocessed']}")

        return cls(
            id=reference_element.id,
            reference_element=reference_element,
            staged_element=staged_element,
            configuration_diff=diff_object,
        )


class NGraphElementListComparison(BaseModel):
    """Class which contains the differences between two lists of nGraphElements. Categorized by added, removed and changed elements."""

    added: List[NGraphElement] = []
    removed: List[NGraphElement] = []
    common: List[NGraphElementDiff] = []

    def get_added(self) -> List[NGraphElement]:
        """Method to get the added nGraphElements."""
        return self.added

    def get_removed(self) -> List[NGraphElement]:
        """Method to get the removed nGraphElements."""
        return self.removed

    def get_changed(self, include_rev=True) -> List[NGraphElementDiff]:
        """Method to get the nGraphElements with changed values (including removed and added values)."""
        elements_with_changed_values = [
            element
            for element in self.common
            if (
                element.configuration_diff.changed
                if include_rev
                else element.configuration_diff.get_changed_ignore_rev()
            )
        ]
        elements_with_removed_values = [
            element
            for element in self.common
            if (
                element.configuration_diff.removed
                if include_rev
                else element.configuration_diff.get_removed_ignore_rev()
            )
        ]
        elements_with_added_values = [
            element
            for element in self.common
            if (element.configuration_diff.added if include_rev else element.configuration_diff.get_added_ignore_rev())
        ]

        all_elements = elements_with_changed_values + elements_with_removed_values + elements_with_added_values

        # Remove duplicates
        unique_elements = []
        unique_ids = []
        for element in all_elements:
            if element.id not in unique_ids:
                unique_elements.append(element)
                unique_ids.append(element.id)

        return unique_elements


class TopologyDeviceComparison(BaseModel):
    """Class which contains the differences between two devices from VideoIPath-Topology."""

    reference_device: TopologyDevice
    staged_device: TopologyDevice

    base_device: NGraphElementDiff
    generic_vertices: NGraphElementListComparison
    ip_vertices: NGraphElementListComparison
    codec_vertices: NGraphElementListComparison
    internal_edges: NGraphElementListComparison
    external_edges: NGraphElementListComparison

    @classmethod
    def analyze_topology_devices(
        cls, reference_device: TopologyDevice, staged_device: TopologyDevice, ignore_rev=True
    ) -> "TopologyDeviceComparison":
        """Method to compare two devices from VideoIPath-Topology."""
        base_device = NGraphElementDiff.compare_nGraphElement(
            reference_device.configuration.base_device, staged_device.configuration.base_device
        )
        generic_vertices = cls.create_compare_list(
            reference_device.configuration.generic_vertices, staged_device.configuration.generic_vertices
        )
        ip_vertices = cls.create_compare_list(
            reference_device.configuration.ip_vertices, staged_device.configuration.ip_vertices
        )
        codec_vertices = cls.create_compare_list(
            reference_device.configuration.codec_vertices, staged_device.configuration.codec_vertices
        )
        internal_edges = cls.create_compare_list(
            reference_device.configuration.internal_edges, staged_device.configuration.internal_edges
        )
        external_edges = cls.create_compare_list(
            reference_device.configuration.external_edges, staged_device.configuration.external_edges
        )

        return cls(
            reference_device=reference_device,
            staged_device=staged_device,
            base_device=base_device,
            generic_vertices=generic_vertices,
            ip_vertices=ip_vertices,
            codec_vertices=codec_vertices,
            internal_edges=internal_edges,
            external_edges=external_edges,
        )

    @staticmethod
    def create_compare_list(
        reference_elements: List[NGraphElement]
        | List[GenericVertex]
        | List[IpVertex]
        | List[CodecVertex]
        | List[UnidirectionalEdge],
        staged_elements: List[NGraphElement]
        | List[GenericVertex]
        | List[IpVertex]
        | List[CodecVertex]
        | List[UnidirectionalEdge],
    ) -> NGraphElementListComparison:
        """Method to create a comparison list between two lists of nGraphElements."""
        reference_element_ids = [element.id for element in reference_elements]
        staged_element_ids = [element.id for element in staged_elements]

        # Use set to find the added, removed and common elements
        added_ids = set(staged_element_ids) - set(reference_element_ids)
        removed_ids = set(reference_element_ids) - set(staged_element_ids)
        common_ids = set(reference_element_ids) & set(staged_element_ids)

        # Fill the added and removed lists
        added_nGraphElements = [element for element in staged_elements if element.id in added_ids]
        removed_nGraphElements = [element for element in reference_elements if element.id in removed_ids]

        # Compare the common elements
        common_nGraphElements = []

        # For easier comparison, convert the nGraphElements to dictionaries
        reference_elements_dict = {element.id: element for element in reference_elements}
        staged_elements_dict = {element.id: element for element in staged_elements}

        for id in common_ids:
            reference_element = reference_elements_dict[id]
            staged_element = staged_elements_dict[id]
            common_nGraphElements.append(NGraphElementDiff.compare_nGraphElement(reference_element, staged_element))

        return NGraphElementListComparison(
            added=added_nGraphElements, removed=removed_nGraphElements, common=common_nGraphElements
        )

    def get_changed_elements(self, include_rev=False) -> List[NGraphElementDiff]:
        """Method to get the changed elements of the device."""
        changed_elements = []

        if include_rev:
            if len(self.base_device.configuration_diff.changed) > 0:
                changed_elements.append(self.base_device)
        else:
            if len(self.base_device.configuration_diff.get_changed_ignore_rev()) > 0:
                changed_elements.append(self.base_device)

        if len(self.generic_vertices.get_changed(include_rev)) > 0:
            changed_elements += self.generic_vertices.get_changed(include_rev)

        if len(self.ip_vertices.get_changed(include_rev)) > 0:
            changed_elements += self.ip_vertices.get_changed(include_rev)

        if len(self.codec_vertices.get_changed(include_rev)) > 0:
            changed_elements += self.codec_vertices.get_changed(include_rev)

        if len(self.internal_edges.get_changed(include_rev)) > 0:
            changed_elements += self.internal_edges.get_changed(include_rev)

        if len(self.external_edges.get_changed(include_rev)) > 0:
            changed_elements += self.external_edges.get_changed(include_rev)

        return changed_elements

    def get_added_elements(self) -> List[NGraphElement]:
        """Method to get the added elements of the device."""
        added_elements = []
        added_elements += self.generic_vertices.get_added()
        added_elements += self.ip_vertices.get_added()
        added_elements += self.codec_vertices.get_added()
        added_elements += self.internal_edges.get_added()
        added_elements += self.external_edges.get_added()
        return added_elements

    def get_removed_elements(self) -> List[NGraphElement]:
        """Method to get the removed elements of the device."""
        removed_elements = []
        removed_elements += self.generic_vertices.get_removed()
        removed_elements += self.ip_vertices.get_removed()
        removed_elements += self.codec_vertices.get_removed()
        removed_elements += self.internal_edges.get_removed()
        removed_elements += self.external_edges.get_removed()
        return removed_elements
