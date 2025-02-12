# External Imports
from typing import List, Literal

from pydantic import BaseModel
from typing_extensions import deprecated

# Internal Imports
from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_base_device import BaseDevice
from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_codec_vertex import CodecVertex
from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_generic_vertex import GenericVertex
from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_ip_vertex import IpVertex
from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_unidirectional_edge import (
    UnidirectionalEdge,
)


class TopologyDeviceConfiguration(BaseModel):
    """
    Class which contains the configuration of a device in the topology

    Attributes:
        base_device (BaseDevice): Configuration of the base device (e.g. device label, description, appearance)
        generic_vertices (List[GenericVertex]): Configuration of the generic vertices of the device
        ip_vertices (List[IpVertex]): Configuration of the IP vertices of the device
        codec_vertices (List[CodecVertex]): Configuration of the codec vertices of the device
        internal_edges (List[UnidirectionalEdge]): Configuration of the internal unidirectional edges of the device (All edges that connect vertices within the same device)
        external_edges (List[UnidirectionalEdge]): Configuration of the external unidirectional edges of the device (All edges that connect this device to other devices)
    """

    base_device: BaseDevice
    generic_vertices: List[GenericVertex] = []
    ip_vertices: List[IpVertex] = []
    codec_vertices: List[CodecVertex] = []
    internal_edges: List[UnidirectionalEdge] = []
    external_edges: List[UnidirectionalEdge] = []

    # --- Setters / Getters ---
    @property
    def label(self):
        """User defined label of the device"""
        return self.base_device.label

    @label.setter
    def label(self, value):
        self.base_device.label = value

    @property
    def description(self):
        """User defined description of the device"""
        return self.base_device.description

    @description.setter
    def description(self, value):
        self.base_device.description = value

    @property
    def factory_label(self):
        """Factory label of the device"""
        return self.base_device.factory_label

    @property
    def factory_description(self):
        """Factory description of the device"""
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

    def get_vertex_by_label(
        self,
        label: str,
        mode: Literal["user_defined", "factory"] = "user_defined",
        filter: Literal["all", "codec_vertex", "ip_vertex", "generic_vertex"] = "all",
    ) -> CodecVertex | IpVertex | GenericVertex | None:
        """Get a codec, ip or generic vertex by its label. The search can be filtered by vertex type and label type.
        Method will return the first vertex found with the specified label.

        Args:
            label (str): The label of the vertex
            mode (str, optional): Label type to search for (`user_defined` or `factory`). Defaults to `user_defined`.
            filter (str, optional): Filter the search to a specific vertex type (`all`, `codec_vertex`, `ip_vertex`, `generic_vertex`). Defaults to `all`.

        Returns:
            CodecVertex | IpVertex | GenericVertex | None: The vertex with the specified label, or `None` if not found.
        """

        vertex_sets = [
            (self.codec_vertices, "codec_vertex"),
            (self.ip_vertices, "ip_vertex"),
            (self.generic_vertices, "generic_vertex"),
        ]

        for vertices, filter_type in vertex_sets:
            if filter in ("all", filter_type):
                for vertex in vertices:
                    if (mode == "user_defined" and vertex.label == label) or (
                        mode == "factory" and vertex.factory_label == label
                    ):
                        return vertex

        return None

    @deprecated(
        "The method `get_ip_vertex_by_label` is deprecated." " TODO,",
        category=None,
    )
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
