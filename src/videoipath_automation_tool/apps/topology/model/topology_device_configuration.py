import warnings
from itertools import chain
from typing import List, Literal

from pydantic import BaseModel, Field
from typing_extensions import deprecated

from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_base_device import BaseDevice
from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_codec_vertex import CodecVertex
from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_generic_vertex import GenericVertex
from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_ip_vertex import IpVertex
from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_n_graph_element import (
    IconSize,
    IconType,
    MapsElement,
    SdpStrategy,
)
from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_unidirectional_edge import (
    UnidirectionalEdge,
)
from videoipath_automation_tool.utils.custom_warnings import ElementNotFoundWarning


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
    generic_vertices: List[GenericVertex] = Field(default_factory=list)
    ip_vertices: List[IpVertex] = Field(default_factory=list)
    codec_vertices: List[CodecVertex] = Field(default_factory=list)
    internal_edges: List[UnidirectionalEdge] = Field(default_factory=list)
    external_edges: List[UnidirectionalEdge] = Field(default_factory=list)

    # --- Setters and Getters ---

    # Note: Every Topology Device has a Base Device,
    # therefore, the getters and setters for the Base Device are defined here to provide
    # a more convenient way to access the Base Device properties.

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

    @property
    def icon_size(self) -> IconSize:
        """Size of the icon representing the device"""
        return self.base_device.iconSize

    @icon_size.setter
    def icon_size(self, value: IconSize):
        self.base_device.iconSize = value

    @property
    def icon_type(self) -> IconType:
        """Type of the icon representing the device"""
        return self.base_device.iconType

    @icon_type.setter
    def icon_type(self, value: IconType):
        self.base_device.iconType = value

    @property
    def position_x(self) -> float:
        """X position of the device on the topology canvas"""
        if not self.base_device.maps or type(self.base_device.maps[0]) is not MapsElement:
            return 0
        return self.base_device.maps[0].x

    @position_x.setter
    def position_x(self, value: float):
        if not self.base_device.maps or type(self.base_device.maps[0]) is not MapsElement:
            self.base_device.maps = [MapsElement(x=value, y=0)]
        else:
            self.base_device.maps[0].x = value

    @property
    def position_y(self) -> float:
        """Y position of the device on the topology canvas"""
        if not self.base_device.maps or type(self.base_device.maps[0]) is not MapsElement:
            return 0
        return self.base_device.maps[0].y

    @position_y.setter
    def position_y(self, value: float):
        if not self.base_device.maps or type(self.base_device.maps[0]) is not MapsElement:
            self.base_device.maps = [MapsElement(x=0, y=value)]
        else:
            self.base_device.maps[0].y = value

    @property
    def tags(self) -> List[str]:
        """Tags associated with the device"""
        return self.base_device.tags

    @tags.setter
    def tags(self, value: List[str]):
        self.base_device.tags = value

    @property
    def sdp_polling_strategy(self) -> SdpStrategy:
        """SDP polling strategy of the device. Possible values are:
        - `always` for 'Continuous'
        - `once` for 'Fetch and Confirm'
        - `video` for 'Always Video, Confirm Others'
        """
        return self.base_device.sdpStrategy

    @sdp_polling_strategy.setter
    def sdp_polling_strategy(self, value: SdpStrategy):
        self.base_device.sdpStrategy = value

    @property
    def site_id(self) -> str | None:
        """Site ID of the device"""
        return self.base_device.siteId

    @site_id.setter
    def site_id(self, value: str):
        self.base_device.siteId = value

    # --- Methods ---
    def get_nGraphElement_by_id(
        self, element_id: str
    ) -> BaseDevice | CodecVertex | GenericVertex | IpVertex | UnidirectionalEdge | None:
        """Get an nGraphElement by its ID. Method will return the first element found with the specified ID.

        Args:
            element_id (str): The ID of the element to search for.

        Returns:
            The matching nGraphElement, or `None` if not found.
        """
        all_elements = chain(
            [self.base_device],
            self.generic_vertices,
            self.ip_vertices,
            self.codec_vertices,
            self.internal_edges,
            self.external_edges,
        )

        matching_element = next((element for element in all_elements if element.id == element_id), None)

        if matching_element is None:
            warnings.warn(f"Element with ID '{element_id}' not found.", ElementNotFoundWarning)

        return matching_element

    def get_vertex_by_label(
        self,
        label: str,
        label_type: Literal["user_defined", "factory", "all"] = "user_defined",
        vertex_type: Literal["all", "codec_vertex", "ip_vertex", "generic_vertex"] = "all",
    ) -> CodecVertex | IpVertex | GenericVertex | None:
        """Get a codec, ip or generic vertex by its label. The search can be filtered by vertex type and label type.
        Method will return the first vertex found with the specified label.

        Args:
            label (str): The label of the vertex
            label_type (str, optional): Label type to search for (`user_defined`, `factory` or `all`). Defaults to `user_defined`.
            vertex_type (str, optional): Filter the search to a specific vertex type (`all`, `codec_vertex`, `ip_vertex`, `generic_vertex`). Defaults to `all`.

        Returns:
            The vertex object with the specified label, or `None` if not found.
        """
        vertex_groups = {
            "codec_vertex": self.codec_vertices,
            "ip_vertex": self.ip_vertices,
            "generic_vertex": self.generic_vertices,
        }

        selected_vertex_groups = (
            vertex_groups.values() if vertex_type == "all" else [vertex_groups.get(vertex_type, [])]
        )

        matching_vertex = next(
            (
                vertex
                for vertex_list in selected_vertex_groups
                for vertex in vertex_list
                if (label_type == "all" and (vertex.label == label or vertex.factory_label == label))
                or (label_type == "user_defined" and vertex.label == label)
                or (label_type == "factory" and vertex.factory_label == label)
            ),
            None,
        )

        if matching_vertex is None:
            warnings.warn(
                f"Vertex with label '{label}' (label_type: {label_type}, vertex_type: {vertex_type}) not found.",
                ElementNotFoundWarning,
            )

        return matching_vertex

    @deprecated(
        "The method `get_ip_vertex_by_label` is deprecated and will be removed in a future release. ",
        category=None,
    )
    def get_ip_vertex_by_label(self, label: str) -> IpVertex:
        """Get an IpVertex by its label"""
        return_dict = {"in": None, "out": None}
        return_dict["in"] = self.get_ip_vertex_by_factory_label_and_direction(label, "in")
        return_dict["out"] = self.get_ip_vertex_by_factory_label_and_direction(label, "out")
        return return_dict

    @deprecated(
        "The method `get_ip_vertex_by_label` is deprecated and will be removed in a future release. ",
        category=None,
    )
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
