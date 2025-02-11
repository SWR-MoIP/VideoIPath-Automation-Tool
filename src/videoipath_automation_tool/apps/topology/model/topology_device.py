# External imports
from typing import Optional

from pydantic import BaseModel

# Internal imports
from videoipath_automation_tool.apps.topology.model.topology_device_configuration import TopologyDeviceConfiguration


class TopologyDevice(BaseModel):
    """
    Class which contains full information about a device in the topology
    """

    configuration: TopologyDeviceConfiguration
    _online_configuration: Optional[TopologyDeviceConfiguration] = (
        None  # Configuration that is currently applied to the device => used for comparison! Will be synced before any action is executed!
    )


#     @classmethod
#     def from_nGraphElements(cls, device: BaseDevice, codec_vertices: List[CodecVertex],
#                             generic_vertices: List[GenericVertex], ip_vertices: List[IpVertex],
#                             internal_edges: List[UnidirectionalEdge], external_edges: List[UnidirectionalEdge]):
#         """
#         Create a TopologyDevice object from multiple nGraphElements
#         """
#         #
#         data = {
#                 "configuration": {
#                     "base_device": device,
#                     "generic_vertices": generic_vertices,
#                     "ip_vertices": ip_vertices,
#                     "codec_vertices": codec_vertices,
#                     "internal_edges": internal_edges,
#                     "external_edges": external_edges
#                 },
#                 "_online_configuration": {
#                     "base_device": device,
#                     "generic_vertices": generic_vertices,
#                     "ip_vertices": ip_vertices,
#                     "codec_vertices": codec_vertices,
#                     "internal_edges": internal_edges,
#                     "external_edges": external_edges
#                 }
#             }
#         instance = cls.model_validate(data)
#         return instance

#     @classmethod
#     def from_dump(cls, configuration: dict):
#         """
#         Create a TopologyDevice object from a dictionary. Important: Dump model by alias ("_id", "_rev", "_vid" instead of "id", "rev", "vid")
#         """
#         config = configuration['configuration']
#         instance = cls(configuration=TopologyDeviceConfiguration(base_device=BaseDevice(**config['base_device']),
#                                                                 generic_vertices=[GenericVertex(**vertex) for vertex in config['generic_vertices']],
#                                                                 ip_vertices=[IpVertex(**vertex) for vertex in config['ip_vertices']],
#                                                                 codec_vertices=[CodecVertex(**vertex) for vertex in config['codec_vertices']],
#                                                                 internal_edges=[UnidirectionalEdge(**vertex) for vertex in config['internal_edges']],
#                                                                 external_edges=[UnidirectionalEdge(**vertex) for vertex in config['external_edges']],
#                      )
#             )
#         instance._online_configuration = TopologyDeviceConfiguration(base_device=BaseDevice(**config['base_device']),
#                                                                     generic_vertices=[GenericVertex(**vertex) for vertex in config['generic_vertices']],
#                                                                     ip_vertices=[IpVertex(**vertex) for vertex in config['ip_vertices']],
#                                                                     codec_vertices=[CodecVertex(**vertex) for vertex in config['codec_vertices']],
#                                                                     internal_edges=[UnidirectionalEdge(**vertex) for vertex in config['internal_edges']],
#                                                                     external_edges=[UnidirectionalEdge(**vertex) for vertex in config['external_edges']],
#         )
#         return instance

#     def get_diff(self):
#         """
#         Get the difference between the configuration and the online configuration
#         """
#         return list(dictdiffer.diff(self.configuration.model_dump(mode="json"), self._online_configuration.model_dump(mode="json")))

#     def print_diff(self):
#         """
#         Print the difference between the configuration and the online configuration
#         """
#         diff_list = self.get_diff()
#         for diff_type, key, value in diff_list:
#             print(f"{diff_type}: {key} - {value}")
#         return diff_list

#     def force_online_revision_to_local(self):
#         """
#         Force the revision of the online configuration to the local configuration
#         """
#         self.configuration.base_device.rev = self._online_configuration.base_device.rev
#         for vertex in self.configuration.codec_vertices:
#             vertex.rev = self._online_configuration.codec_vertices[self.configuration.codec_vertices.index(vertex)].rev
#         for vertex in self.configuration.generic_vertices:
#             vertex.rev = self._online_configuration.generic_vertices[self.configuration.generic_vertices.index(vertex)].rev
#         for vertex in self.configuration.ip_vertices:
#             vertex.rev = self._online_configuration.ip_vertices[self.configuration.ip_vertices.index(vertex)].rev
#         for edge in self.configuration.internal_edges:
#             edge.rev = self._online_configuration.internal_edges[self.configuration.internal_edges.index(edge)].rev
#         for edge in self.configuration.external_edges:
#             edge.rev = self._online_configuration.external_edges[self.configuration.external_edges.index(edge)].rev
#         return self

# # ARISTA
#     def get_arista_ip_vertices(self, factory_label: str, direction: Literal["bidirectional", "in", "out"] = "bidirectional") -> List[IpVertex]:
#         if "/" in factory_label:
#             factory_label = factory_label.replace('/', '_')

#         vertex_list = []
#         for vertex in self.configuration.ip_vertices:
#             if len(vertex.gpid.pointId) > 0 and vertex.gpid.pointId[-1] == factory_label:
#                 vertex_list.append(vertex)

#         if len(vertex_list) == 0:
#             raise ValueError(f"No IP Vertex found with label '{factory_label}'")
#         if len(vertex_list) > 2:
#             raise ValueError(f"More then IP Vertices found with label '{factory_label}': {vertex_list}")

#         if direction == "bidirectional":
#             return vertex_list
#         elif direction == "in" or direction == "out":
#             for vertex in vertex_list:
#                 if vertex.vertexType.lower() == direction:
#                     return [vertex]
#             raise ValueError(f"No IP Vertex found with label '{factory_label}' and direction '{direction}'")

#     def get_arista_ip_vertex(self, factory_label: str, direction: Literal["in", "out"]) -> IpVertex:
#         """ Get the IP Vertex with the given factory label and direction

#         Args:
#             factory_label (str): Port label of the Arista switch (e.g. "Ethernet4/64", "Ethernet4")
#             direction (Literal[&quot;in&quot;, &quot;out&quot;]): Direction of the IP Vertex (in or out)

#         Returns:
#             IpVertex: IP Vertex with the given factory label and direction
#         """
#         return self.get_arista_ip_vertices(factory_label, direction)[0]

#     def get_arista_ip_vertex_pair(self, factory_label: str) -> Tuple[IpVertex, IpVertex]:
#         """ Get the IP Vertex pair with the given factory label

#         Args:
#             factory_label (str): Port label of the Arista switch (e.g. "Ethernet4/64", "Ethernet4")

#         Returns:
#             Tuple[IpVertex, IpVertex]: Tuple with the IP Vertex pair, firt is the out vertex, second is the in vertex
#         """
#         try:
#             return self.get_arista_ip_vertex(factory_label, "out"), self.get_arista_ip_vertex(factory_label, "in")
#         except ValueError as e:
#             raise ValueError(f"Error while getting IP Vertex pair for '{factory_label}': {e}")

# # GENERIC
#     def get_ip_vertices(self, factory_label: str, direction: Literal["bidirectional", "in", "out"] = "bidirectional") -> List[IpVertex]:
#         vertex_list = []
#         for vertex in self.configuration.ip_vertices:
#             if len(vertex.gpid.pointId) > 0 and vertex.fDescriptor.label.replace(" (in)","").replace(" (out)","")  == factory_label: #vertex.fDescriptor.label.split(" (in)")[0].split(" (out)")[0] == factory_label:
#                 vertex_list.append(vertex)

#         if len(vertex_list) == 0:
#             raise ValueError(f"No IP Vertex found with label '{factory_label}'")
#         if len(vertex_list) > 2:
#             raise ValueError(f"More then IP Vertices found with label '{factory_label}': {vertex_list}")

#         if direction == "bidirectional":
#             return vertex_list
#         elif direction == "in" or direction == "out":
#             for vertex in vertex_list:
#                 if vertex.vertexType.lower() == direction:
#                     return [vertex]
#             raise ValueError(f"No IP Vertex found with label '{factory_label}' and direction '{direction}'")

#     def get_ip_vertex(self, factory_label: str, direction: Literal["in", "out"]) -> IpVertex:
#         """ Get the IP Vertex with the given factory label and direction

#         Args:
#             factory_label (str): Port label (e.g. "e1", "P0")
#             direction (Literal[&quot;in&quot;, &quot;out&quot;]): Direction of the IP Vertex (in or out)

#         Returns:
#             IpVertex: IP Vertex with the given factory label and direction
#         """
#         return self.get_ip_vertices(factory_label, direction)[0]

#     def get_ip_vertex_pair(self, factory_label: str) -> Tuple[IpVertex, IpVertex]:
#         """ Get the IP Vertex pair with the given factory label
#         Experimental method !

#         Args:
#             factory_label (str): Port label of the Arista switch (e.g. "Ethernet4/64", "Ethernet4")

#         Returns:
#             Tuple[IpVertex, IpVertex]: Tuple with the IP Vertex pair, firt is the out vertex, second is the in vertex
#         """
#         try:
#             return self.get_ip_vertex(factory_label, "out"), self.get_ip_vertex(factory_label, "in")
#         except ValueError as e:
#             raise ValueError(f"Error while getting IP Vertex pair for '{factory_label}': {e}")

#     # Filtered Getter
#     @property
#     def get_ip_out_vertices(self):
#         return [vertex for vertex in self.configuration.ip_vertices if vertex.vertexType == "Out"]

#     @property
#     def get_ip_in_vertices(self):
#         return [vertex for vertex in self.configuration.ip_vertices if vertex.vertexType == "In"]

#     @property
#     def get_ip_vertex_pairs(self):
#         """
#         Get all pairs of IP Vertices
#         """
#         pairs = []
#         for out_vertex in self.get_ip_out_vertices:
#             for in_vertex in self.get_ip_in_vertices:
#                 if out_vertex.gpid.pointId[-1] == in_vertex.gpid.pointId[-1]:
#                     pairs.append((out_vertex, in_vertex))
#         return pairs


#     # Getter
#     @property
#     def id(self):
#         return self.configuration.base_device.id

#     @property
#     def label(self):
#         if self.configuration.base_device.descriptor.label is None or self.configuration.base_device.descriptor.label == "":
#             return self.configuration.base_device.fDescriptor.label
#         return self.configuration.base_device.descriptor.label

#     def get_vertex_by_id(self, id):
#         """
#         Get a vertex by its id
#         """
#         for vertex in self.vertices:
#             if vertex.id == id:
#                 return vertex
#         return None

#     #Example!!
#     def example_auto_generate(self):
#         """
#         Example method to demonstrate how to auto generate vertice configurations
#         """
#         for vertex in self.configuration.codec_vertices:
#             vout=0
#             aout=0
#             vin=0
#             ain=0
#             vertex.useAsEndpoint = True
#             vertex.control = "full"
#             if vertex.codecFormat == "Video":
#                 if vertex.vertexType == "Out":
#                     vout+=1
#                     vertex.descriptor.label = f"VideoOut-{vout}"
#                     vertex.sipsMode = SipsMode("SIPSMerge")
#                     vertex.tags.append("#VIDEO_OUT")
#                 elif vertex.vertexType == "In":
#                     vin+=1
#                     vertex.descriptor.label = f"VideoIn-{vin}"
#                     vertex.sipsMode = SipsMode("SIPSSplit")
#                     vertex.tags.append("#VIDEO_IN")
#             elif vertex.codecFormat == "Audio":
#                 if vertex.vertexType == "Out":
#                     aout+=1
#                     vertex.descriptor.label = f"AudioOut-{aout}"
#                     vertex.sipsMode = SipsMode("SIPSMerge")
#                     vertex.tags.append("#AUDIO_OUT")
#                 elif vertex.vertexType == "In":
#                     ain+=1
#                     vertex.descriptor.label = f"AudioIn-{ain}"
#                     vertex.sipsMode = SipsMode("SIPSSplit")
#                     vertex.tags.append("#AUDIO_IN")

#     # getter for all vertices in a list
#     @property
#     def vertices(self):
#         return [self.configuration.base_device] + self.configuration.codec_vertices + self.configuration.generic_vertices + self.configuration.ip_vertices + self.configuration.internal_edges + self.configuration.external_edges

#     @property
#     def online_vertices(self):
#         # access the online configuration
#         config = self._online_configuration
#         return [config.base_device] + config.codec_vertices + config.generic_vertices + config.ip_vertices + config.internal_edges + config.external_edges
#         #return [self._online_configuration.base_device] + self._online_configuration.codec_vertices + self._online_configuration.generic_vertices + self._online_configuration.ip_vertices + self._online_configuration.internal_edges + self._online_configuration.external_edges
