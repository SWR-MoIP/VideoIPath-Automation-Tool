# External Imports
from typing import List, Literal
from pydantic import BaseModel

# Internal Imports
from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_base_device import BaseDevice
from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_codec_vertex import CodecVertex
from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_generic_vertex import GenericVertex
from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_ip_vertex import IpVertex
from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_unidirectional_edge import (
    UnidirectionalEdge,
)


class TopologyDeviceConfiguration(BaseModel):
    """Class which contains the configuration of a device in the topology"""

    base_device: BaseDevice
    generic_vertices: List[GenericVertex] = []
    ip_vertices: List[IpVertex] = []
    codec_vertices: List[CodecVertex] = []
    internal_edges: List[
        UnidirectionalEdge
    ] = []  # List of edges that connect vertices within the same device (internal unidirectional edges)
    external_edges: List[UnidirectionalEdge] = []  # List of edges that connect this device to other devices

    # --- Setters / Getters ---
    @property
    def label(self):
        """Get the manually set label of the device"""
        return self.base_device.label

    @label.setter
    def label(self, value):
        self.base_device.label = value

    @property
    def description(self):
        """Get the manually set description of the device"""
        return self.base_device.description

    @description.setter
    def description(self, value):
        self.base_device.description = value

    @property
    def factory_label(self):
        """Get the factory label of the device"""
        return self.base_device.factory_label

    @property
    def factory_description(self):
        """Get the factory description of the device"""
        return self.base_device.factory_description

    # --- Methods ---
    def get_nGraphElement_by_id(
        self, id: str
    ) -> BaseDevice | CodecVertex | GenericVertex | IpVertex | UnidirectionalEdge:
        """Get a nGraphElement by its id"""
        nGraphElement_list = (
            [self.base_device]
            + self.generic_vertices
            + self.ip_vertices
            + self.codec_vertices
            + self.internal_edges
            + self.external_edges
        )
        for element in nGraphElement_list:
            if element.id == id:
                return element
        raise ValueError(f"Element with id '{id}' not found.")

    def get_ip_vertex_by_label(self, label: str) -> IpVertex:
        """Get an IpVertex by its label"""
        return_dict = {"in": None, "out": None}
        return_dict["in"] = self.get_ip_vertex_by_factory_label_and_direction(label, "in")
        return_dict["out"] = self.get_ip_vertex_by_factory_label_and_direction(label, "out")
        return return_dict

    def get_ip_vertex_by_factory_label_and_direction(
        self, factory_label: str, direction: Literal["out", "in"]
    ) -> IpVertex | None:
        """Get an IpVertex by its factory label"""
        label = f"{factory_label} ({direction})"

        return_value = None

        for ip_vertex in self.ip_vertices:
            if ip_vertex.factory_label == label:
                return_value = ip_vertex

        if return_value is None:
            for ip_vertex in self.ip_vertices:
                if f" ({direction}) " in ip_vertex.factory_label:
                    # remove the direction part from the factory label
                    fallback_label = (
                        f'{ip_vertex.factory_label.split(" (")[0]} {ip_vertex.factory_label.split(") ")[1]}'
                    )
                    if fallback_label == factory_label:
                        return_value = ip_vertex

        return return_value
        # raise ValueError(f"IP Vertex with factory label '{factory_label}' not found.")
