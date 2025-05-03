from itertools import chain
from typing import Literal

from pydantic import BaseModel

from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_base_device import BaseDevice
from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_codec_vertex import (
    CodecVertex,
)
from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_generic_vertex import GenericVertex
from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_ip_vertex import IpVertex
from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_unidirectional_edge import (
    UnidirectionalEdge,
)
from videoipath_automation_tool.apps.topology.model.topology_device_configuration import TopologyDeviceConfiguration
from videoipath_automation_tool.validators.virtual_device_id import validate_virtual_device_id


class TopologyDevice(BaseModel):
    """
    Class which contains full information about a device in the topology.

    Attributes:
        configuration (TopologyDeviceConfiguration): The configuration of the device
    """

    configuration: TopologyDeviceConfiguration

    def migrate_external_edges_to_new_id_format(self):
        """
        Migrate external edges to the new id format, which is `fromId::toId`.
        """
        for edge in self.configuration.external_edges:
            if "::" not in edge.id:
                from_id = edge.fromId
                to_id = edge.toId

                edge_id = f"{from_id}::{to_id}"
                edge.id = edge_id
                edge.vid = edge_id

    # Note: All methods for editing a virtual device are experimental! They are not yet fully tested and optimized. Use with caution!

    @classmethod
    def create_virtual_device(cls) -> "TopologyDevice":
        """
        Create a virtual device with virtual.0 id and a virtual switching core (Module #0).

        Note: All methods for editing a virtual device are experimental! They are not yet fully tested and optimized. Use with caution!

        Args:
            label (str): The label of the device

        Returns:
            TopologyDevice: The created virtual device
        """
        base_device = {
            "_id": "virtual.0",
            "_rev": None,
            "_vid": "virtual.0",
            "descriptor": {"label": "", "desc": ""},
            "fDescriptor": {"label": "Virtual Device 1", "desc": ""},
            "iconSize": "auto",
            "iconType": "default",
            "isVirtual": True,
            "maps": [{"cType": "Topology", "id": "Default", "name": "Default", "visible": True, "x": 0.0, "y": 0.0}],
            "sdpStrategy": "always",
            "tags": [],
            "type": "baseDevice",
        }
        switching_core = {
            "_id": "virtual.0.0.0",
            "_rev": None,
            "_vid": "virtual.0.0.0",
            "descriptor": {"label": "", "desc": ""},
            "fDescriptor": {"label": "Virtual Device 1 Virtual Switching Core 0", "desc": ""},
            "deviceId": "virtual.0",
            "gpid": {"component": 15, "pointId": ["virtual-0", "virt", "0", "0"]},
            "tags": [],
            "configPriority": "off",
            "control": "off",
            "custom": {},
            "extraAlertFilters": [],
            "imgUrl": "",
            "isVirtual": True,
            "maps": [],
            "sipsMode": "NONE",
            "useAsEndpoint": False,
            "vertexType": "Internal",
            "type": "genericVertex",
        }
        base_device_element = BaseDevice.model_validate(base_device)
        switching_core_element = GenericVertex.model_validate(switching_core)
        return cls(
            configuration=TopologyDeviceConfiguration(
                base_device=base_device_element, generic_vertices=[switching_core_element]
            )
        )

    def validate_device_is_virtual(self):
        if not self.configuration.base_device.isVirtual:
            raise ValueError("The device is not a virtual device.")

    def _get_next_virtual_module_number(self) -> int:
        """
        Determine the next available module number. Each module number is in the format `virtual.<device_id>.<module_number>`. Module number is incremented by 1 for each new module.
        Note: All methods for editing a virtual device are experimental! They are not yet fully tested and optimized. Use with caution!

        Returns:
            int: The next available module number
        """

        self.validate_device_is_virtual()

        highest_module_number = -1
        for vertex in self.configuration.generic_vertices:
            vertex_id = vertex.id
            if vertex.vertex_type == "Internal" and vertex_id.split(".")[-1] == "0":
                module_number = int(vertex_id.split(".")[-2])
                if module_number > highest_module_number:
                    highest_module_number = module_number
        return highest_module_number + 1

    def _get_next_virtual_vertex_number(self) -> int:
        """
        Determine the next available vertex id. Each vertex id is in the format `virtual.<device_id>.<module_number>.<vertex_number>`. Vertex number is incremented by 1 for each new vertex over all modules.
        Note: All methods for editing a virtual device are experimental! They are not yet fully tested and optimized. Use with caution!

        Returns:
            int: The next available vertex number
        """

        self.validate_device_is_virtual()

        highest_vertex_number = -1
        for vertex in (
            self.configuration.codec_vertices + self.configuration.ip_vertices + self.configuration.generic_vertices
        ):
            vertex_id = vertex.id
            vertex_number = int(vertex_id.split(".")[-1])
            if vertex_number > highest_vertex_number:
                highest_vertex_number = vertex_number

        return highest_vertex_number + 1

    def list_module_numbers(self) -> list[int]:
        """
        List all module numbers of the virtual device.
        Note: All methods for editing a virtual device are experimental! They are not yet fully tested and optimized. Use with caution!

        Returns:
            list[int]: The list of module numbers
        """

        self.validate_device_is_virtual()

        module_numbers = []
        for vertex in self.configuration.generic_vertices:
            vertex_id = vertex.id
            if vertex.vertex_type == "Internal" and vertex_id.split(".")[-1] == "0":
                module_number = int(vertex_id.split(".")[-2])
                module_numbers.append(module_number)
        return module_numbers

    def add_virtual_module(self) -> GenericVertex:
        """
        Add a virtual switching core module to the virtual device.
        Note: All methods for editing a virtual device are experimental! They are not yet fully tested and optimized. Use with caution!
        """

        self.validate_device_is_virtual()

        module_number = self._get_next_virtual_module_number()
        device_id = self.configuration.base_device.id
        device_number = int(device_id.split(".")[-1])
        module_id = f"{device_id}.{module_number}.0"
        module_vertex = {
            "_id": module_id,
            "_rev": None,
            "_vid": module_id,
            "descriptor": {"label": "", "desc": ""},
            "fDescriptor": {
                "label": f"Virtual Device {device_number + 1} Virtual Switching Core {module_number}",
                "desc": "",
            },
            "deviceId": f"{device_id}",
            "gpid": {
                "component": 15,
                "pointId": [device_id.replace(".", "-"), "virt", str(module_number), "0"],
            },
            "tags": [],
            "configPriority": "off",
            "control": "off",
            "custom": {},
            "extraAlertFilters": [],
            "imgUrl": "",
            "isVirtual": True,
            "maps": [],
            "sipsMode": "NONE",
            "useAsEndpoint": False,
            "vertexType": "Internal",
            "type": "genericVertex",
        }
        module_vertex_element = GenericVertex.model_validate(module_vertex)
        self.configuration.generic_vertices.append(module_vertex_element)
        return module_vertex_element

    def add_virtual_codec_vertex(
        self,
        vertex_direction: Literal[
            "BiDirectional",
            "In",
            "Out",
        ] = "BiDirectional",
        codec_format: Literal["Video", "Audio", "ASI"] = "Video",
        module_number: int = 0,
    ) -> CodecVertex:
        """
        Add a codec vertex to the virtual device, which will be connected to the switching core.
        Note: All methods for editing a virtual device are experimental! They are not yet fully tested and optimized. Use with caution!

        Args:
            vertex_direction (Literal["BiDirectional", "In", "Out"], optional): The direction of the vertex. Default is `"BiDirectional"`.
            codec_format (Literal["Video", "Audio", "ASI"], optional): The codec format of the vertex. Default is `"Video"`.
            module_number (int, optional): The module number of the vertex. Default is `0`.
        """

        self.validate_device_is_virtual()

        if not isinstance(module_number, int):
            raise ValueError("module_number must be an integer.")
        if module_number < 0:
            raise ValueError("module_number must be a positive integer.")

        module_id = f"{self.configuration.base_device.id}.{module_number}.0"
        module_vertex = self.configuration.get_nGraphElement_by_id(module_id)
        if module_vertex is None:
            raise ValueError(f"Module {module_id} does not exist, please create it first.")

        device_id = self.configuration.base_device.id
        device_number = int(device_id.split(".")[-1])
        vertex_number = self._get_next_virtual_vertex_number()
        vertex_id = f"{device_id}.{module_number}.{vertex_number}"
        codec_vertex = {
            "_id": vertex_id,
            "_rev": None,
            "_vid": vertex_id,
            "descriptor": {"label": "", "desc": ""},
            "fDescriptor": {
                "label": f"Vertex {vertex_number}",
                "desc": f"Virtual Device {device_number + 1} Vertex {vertex_number}",
            },
            "deviceId": f"{device_id}",
            "gpid": {
                "component": 15,
                "pointId": [device_id.replace(".", "-"), "virt", str(module_number), str(vertex_number)],
            },
            "tags": [],
            "mainDstIp": None,
            "mainDstMac": None,
            "mainDstPort": None,
            "mainDstVlan": None,
            "mainSrcGateway": None,
            "mainSrcIp": None,
            "mainSrcMac": None,
            "mainSrcNetmask": None,
            "partnerConfig": None,
            "public": False,
            "sdpSupport": False,
            "serviceId": None,
            "spareDstIp": None,
            "spareDstMac": None,
            "spareDstPort": None,
            "spareDstVlan": None,
            "spareSrcGateway": None,
            "spareSrcIp": None,
            "spareSrcMac": None,
            "spareSrcNetmask": None,
            "multiplicity": 1,
            "codecFormat": codec_format,
            "configPriority": "off",
            "control": "off",
            "custom": {},
            "extraAlertFilters": [],
            "imgUrl": "",
            "isVirtual": True,
            "maps": [],
            "sipsMode": "NONE",
            "useAsEndpoint": False,
            "vertexType": vertex_direction,
            "type": "codecVertex",
        }
        codec_vertex_element = CodecVertex.model_validate(codec_vertex)
        self.configuration.codec_vertices.append(codec_vertex_element)

        if codec_vertex_element.vertex_type == "In" or codec_vertex_element.vertex_type == "BiDirectional":
            unidirectional_edge = {
                "_id": f"{vertex_id}::{module_id}",
                "_rev": None,
                "_vid": f"{vertex_id}::{module_id}",
                "active": True,
                "bandwidth": -1,
                "capacity": 65535,
                "conflictPri": 0,
                "descriptor": {"label": "", "desc": ""},
                "excludeFormats": [],
                "fDescriptor": {
                    "label": f"Vertex {vertex_number} -> Virtual Device {device_number + 1} Virtual Switching Core {module_number}",
                    "desc": "",
                },
                "fromId": f"{vertex_id}",
                "includeFormats": [],
                "redundancyMode": "Any",
                "tags": [],
                "toId": f"{module_id}",
                "type": "unidirectionalEdge",
                "weight": 1,
                "weightFactors": {"bandwidth": {"weight": 0}, "service": {"max": 100, "weight": 0}},
            }
            unidirectional_edge_element = UnidirectionalEdge.model_validate(unidirectional_edge)
            self.configuration.internal_edges.append(unidirectional_edge_element)

        if codec_vertex_element.vertex_type == "Out" or codec_vertex_element.vertex_type == "BiDirectional":
            unidirectional_edge = {
                "_id": f"{module_id}::{vertex_id}",
                "_rev": None,
                "_vid": f"{module_id}::{vertex_id}",
                "active": True,
                "bandwidth": -1,
                "capacity": 65535,
                "conflictPri": 0,
                "descriptor": {"label": "", "desc": ""},
                "excludeFormats": [],
                "fDescriptor": {
                    "label": f"Virtual Device {device_number + 1} Virtual Switching Core {module_number} -> Vertex {vertex_number}",
                    "desc": "",
                },
                "fromId": f"{module_id}",
                "includeFormats": [],
                "redundancyMode": "Any",
                "tags": [],
                "toId": f"{vertex_id}",
                "type": "unidirectionalEdge",
                "weight": 1,
                "weightFactors": {"bandwidth": {"weight": 0}, "service": {"max": 100, "weight": 0}},
            }
            unidirectional_edge_element = UnidirectionalEdge.model_validate(unidirectional_edge)
            self.configuration.internal_edges.append(unidirectional_edge_element)

        return codec_vertex_element

    def add_virtual_ip_vertex(
        self,
        vertex_direction: Literal[
            "BiDirectional",
            "In",
            "Out",
        ] = "BiDirectional",
        module_number: int = 0,
    ) -> IpVertex:
        """
        Add an IP vertex to the virtual device, which will be connected to the switching core.
        Note: All methods for editing a virtual device are experimental! They are not yet fully tested and optimized. Use with caution!

        Args:
            vertex_direction (Literal["BiDirectional", "In", "Out"], optional): The direction of the vertex. Default is `"BiDirectional"`.
            module_number (int, optional): The module number of the vertex. Default is `0`.
        """

        self.validate_device_is_virtual()

        if not isinstance(module_number, int):
            raise ValueError("module_number must be an integer.")
        if module_number < 0:
            raise ValueError("module_number must be a positive integer.")

        module_id = f"{self.configuration.base_device.id}.{module_number}.0"
        module_vertex = self.configuration.get_nGraphElement_by_id(module_id)
        if module_vertex is None:
            raise ValueError(f"Module {module_id} does not exist, please create it first.")

        device_id = self.configuration.base_device.id
        device_number = int(device_id.split(".")[-1])
        vertex_number = self._get_next_virtual_vertex_number()
        vertex_id = f"{device_id}.{module_number}.{vertex_number}"
        ip_vertex = {
            "_id": vertex_id,
            "_rev": None,
            "_vid": vertex_id,
            "descriptor": {"label": "", "desc": ""},
            "fDescriptor": {
                "label": f"Vertex {vertex_number}",
                "desc": f"Virtual Device {device_number + 1} Vertex {vertex_number}",
            },
            "deviceId": f"{device_id}",
            "gpid": {
                "component": 15,
                "pointId": [device_id.replace(".", "-"), "virt", str(module_number), str(vertex_number)],
            },
            "tags": [],
            "sipsMode": "NONE",
            "supportsCpipeCfg": False,
            "vlanId": "",
            "supportsOpenflowCfg": False,
            "isVirtual": True,
            "custom": {},
            "partnerConfig": None,
            "extraAlertFilters": [],
            "imgUrl": "",
            "isIgmpSource": False,
            "vrfId": "",
            "ipAddress": None,
            "ipNetmask": None,
            "supportsStaticIgmpCfg": False,
            "supportsIgmpCfg": False,
            "supportsVlanCfg": False,
            "useAsEndpoint": False,
            "control": "off",
            "supportsVplsCfg": False,
            "configPriority": "off",
            "vertexType": vertex_direction,
            "type": "ipVertex",
        }
        ip_vertex_element = IpVertex.model_validate(ip_vertex)
        self.configuration.ip_vertices.append(ip_vertex_element)

        if ip_vertex_element.vertex_type == "In" or ip_vertex_element.vertex_type == "BiDirectional":
            unidirectional_edge = {
                "_id": f"{vertex_id}::{module_id}",
                "_rev": None,
                "_vid": f"{vertex_id}::{module_id}",
                "active": True,
                "bandwidth": -1,
                "capacity": 65535,
                "conflictPri": 0,
                "descriptor": {"label": "", "desc": ""},
                "excludeFormats": [],
                "fDescriptor": {
                    "label": f"Vertex {vertex_number} -> Virtual Device {device_number + 1} Virtual Switching Core {module_number}",
                    "desc": "",
                },
                "fromId": f"{vertex_id}",
                "includeFormats": [],
                "redundancyMode": "Any",
                "tags": [],
                "toId": f"{module_id}",
                "type": "unidirectionalEdge",
                "weight": 1,
                "weightFactors": {"bandwidth": {"weight": 0}, "service": {"max": 100, "weight": 0}},
            }
            unidirectional_edge_element = UnidirectionalEdge.model_validate(unidirectional_edge)
            self.configuration.internal_edges.append(unidirectional_edge_element)

        if ip_vertex_element.vertex_type == "Out" or ip_vertex_element.vertex_type == "BiDirectional":
            unidirectional_edge = {
                "_id": f"{module_id}::{vertex_id}",
                "_rev": None,
                "_vid": f"{module_id}::{vertex_id}",
                "active": True,
                "bandwidth": -1,
                "capacity": 65535,
                "conflictPri": 0,
                "descriptor": {"label": "", "desc": ""},
                "excludeFormats": [],
                "fDescriptor": {
                    "label": f"Virtual Device {device_number + 1} Virtual Switching Core {module_number} -> Vertex {vertex_number}",
                    "desc": "",
                },
                "fromId": f"{module_id}",
                "includeFormats": [],
                "redundancyMode": "Any",
                "tags": [],
                "toId": f"{vertex_id}",
                "type": "unidirectionalEdge",
                "weight": 1,
                "weightFactors": {"bandwidth": {"weight": 0}, "service": {"max": 100, "weight": 0}},
            }
            unidirectional_edge_element = UnidirectionalEdge.model_validate(unidirectional_edge)
            self.configuration.internal_edges.append(unidirectional_edge_element)

        return ip_vertex_element

    def add_virtual_generic_vertex(
        self,
        vertex_direction: Literal[
            "BiDirectional",
            "In",
            "Out",
        ] = "BiDirectional",
        module_number: int = 0,
    ) -> GenericVertex:
        """
        Add a generic vertex to the virtual device, which will be connected to the switching core.
        Note: All methods for editing a virtual device are experimental! They are not yet fully tested and optimized. Use with caution!

        Args:
            vertex_direction (Literal["BiDirectional", "In", "Out"], optional): The direction of the vertex. Default is `"BiDirectional"`.
            module_number (int, optional): The module number of the vertex. Default is `0`.
        """

        self.validate_device_is_virtual()

        if not isinstance(module_number, int):
            raise ValueError("module_number must be an integer.")
        if module_number < 0:
            raise ValueError("module_number must be a positive integer.")

        module_id = f"{self.configuration.base_device.id}.{module_number}.0"
        module_vertex = self.configuration.get_nGraphElement_by_id(module_id)
        if module_vertex is None:
            raise ValueError(f"Module {module_id} does not exist, please create it first.")

        device_id = self.configuration.base_device.id
        device_number = int(device_id.split(".")[-1])
        vertex_number = self._get_next_virtual_vertex_number()
        vertex_id = f"{device_id}.{module_number}.{vertex_number}"
        generic_vertex = {
            "_id": vertex_id,
            "_rev": None,
            "_vid": vertex_id,
            "descriptor": {"label": "", "desc": ""},
            "fDescriptor": {
                "label": f"Vertex {vertex_number}",
                "desc": f"Virtual Device {device_number + 1} Vertex {vertex_number}",
            },
            "deviceId": f"{device_id}",
            "gpid": {
                "component": 15,
                "pointId": [device_id.replace(".", "-"), "virt", str(module_number), str(vertex_number)],
            },
            "tags": [],
            "configPriority": "off",
            "control": False,
            "custom": {},
            "extraAlertFilters": [],
            "imgUrl": "",
            "isVirtual": True,
            "maps": [],
            "sipsMode": "NONE",
            "useAsEndpoint": False,
            "vertexType": vertex_direction,
            "type": "genericVertex",
        }
        generic_vertex_element = GenericVertex.model_validate(generic_vertex)
        self.configuration.generic_vertices.append(generic_vertex_element)

        if generic_vertex_element.vertex_type == "In" or generic_vertex_element.vertex_type == "BiDirectional":
            unidirectional_edge = {
                "_id": f"{vertex_id}::{module_id}",
                "_rev": None,
                "_vid": f"{vertex_id}::{module_id}",
                "active": True,
                "bandwidth": -1,
                "capacity": 65535,
                "conflictPri": 0,
                "descriptor": {"label": "", "desc": ""},
                "excludeFormats": [],
                "fDescriptor": {
                    "label": f"Vertex {vertex_number} -> Virtual Device {device_number + 1} Virtual Switching Core {module_number}",
                    "desc": "",
                },
                "fromId": f"{vertex_id}",
                "includeFormats": [],
                "redundancyMode": "Any",
                "tags": [],
                "toId": f"{module_id}",
                "type": "unidirectionalEdge",
                "weight": 1,
                "weightFactors": {"bandwidth": {"weight": 0}, "service": {"max": 100, "weight": 0}},
            }
            unidirectional_edge_element = UnidirectionalEdge.model_validate(unidirectional_edge)
            self.configuration.internal_edges.append(unidirectional_edge_element)

        if generic_vertex_element.vertex_type == "Out" or generic_vertex_element.vertex_type == "BiDirectional":
            unidirectional_edge = {
                "_id": f"{module_id}::{vertex_id}",
                "_rev": None,
                "_vid": f"{module_id}::{vertex_id}",
                "active": True,
                "bandwidth": -1,
                "capacity": 65535,
                "conflictPri": 0,
                "descriptor": {"label": "", "desc": ""},
                "excludeFormats": [],
                "fDescriptor": {
                    "label": f"Virtual Device {device_number + 1} Virtual Switching Core {module_number} -> Vertex {vertex_number}",
                    "desc": "",
                },
                "fromId": f"{module_id}",
                "includeFormats": [],
                "redundancyMode": "Any",
                "tags": [],
                "toId": f"{vertex_id}",
                "type": "unidirectionalEdge",
                "weight": 1,
                "weightFactors": {"bandwidth": {"weight": 0}, "service": {"max": 100, "weight": 0}},
            }
            unidirectional_edge_element = UnidirectionalEdge.model_validate(unidirectional_edge)
            self.configuration.internal_edges.append(unidirectional_edge_element)

        return generic_vertex_element

    def remove_virtual_vertex(self, vertex_id: str):
        """
        Remove a virtual vertex from the virtual device. If a module id is provided, the module and all vertices connected to it will be removed.
        Note: All methods for editing a virtual device are experimental! They are not yet fully tested and optimized. Use with caution!

        Args:
            vertex_id (str): The id of the vertex to remove
        """

        self.validate_device_is_virtual()

        vertex = self.configuration.get_nGraphElement_by_id(vertex_id)
        if vertex is None:
            raise ValueError(f"Vertex {vertex_id} does not exist.")
        if not (isinstance(vertex, CodecVertex) or isinstance(vertex, IpVertex) or isinstance(vertex, GenericVertex)):
            raise ValueError("Vertex must be a CodecVertex, IpVertex or GenericVertex.")

        # get all edges connected to the vertex
        edges = self.configuration.get_internal_edges_connected_to_vertex(vertex_id)
        vertices = []
        vertices.append(vertex)

        if isinstance(vertex, GenericVertex) and vertex.vertex_type == "Internal":
            # get all internal vertices connected to the vertex
            if edges is not None:
                for edge in edges:
                    vertices.append(self.configuration.get_internal_vertices_connected_to_edge(edge.id))

        if edges is not None:
            for edge in edges:
                self.configuration.internal_edges.remove(edge)

        for vertex in vertices:
            if isinstance(vertex, CodecVertex):
                self.configuration.codec_vertices.remove(vertex)
            elif isinstance(vertex, IpVertex):
                self.configuration.ip_vertices.remove(vertex)
            elif isinstance(vertex, GenericVertex):
                self.configuration.generic_vertices.remove(vertex)

    def set_virtual_device_id(self, device_id: str):
        """
        Set the device id of the virtual device.
        Note: All methods for editing a virtual device are experimental! They are not yet fully tested and optimized. Use with caution!

        Args:
            device_id (str): The new device id
        """

        self.validate_device_is_virtual()

        old_device_id = self.configuration.base_device.id
        old_device_number = int(old_device_id.split(".")[-1]) + 1

        device_id = validate_virtual_device_id(device_id)
        device_number = int(device_id.split(".")[-1]) + 1

        # Modify the device id in the base device
        self.configuration.base_device.id = device_id
        self.configuration.base_device.vid = device_id
        self.configuration.base_device.fDescriptor.label = f"Virtual Device {device_number}"

        # Modify the device id in all vertices
        for vertex in chain(
            self.configuration.codec_vertices, self.configuration.ip_vertices, self.configuration.generic_vertices
        ):
            vertex.deviceId = device_id
            vertex.gpid.pointId[0] = device_id.replace(".", "-")
            vertex_id = vertex.id
            vertex_id_internals = vertex_id.split(".")[2:]
            vertex.id = f"{device_id}.{'.'.join(vertex_id_internals)}"
            vertex.vid = vertex.id

            if isinstance(vertex, GenericVertex) and vertex.vertexType == "Internal":
                vertex.fDescriptor.label = (
                    f"Virtual Device {device_number} Virtual Switching Core {vertex_id_internals[0]}"
                )
            else:
                vertex.fDescriptor.desc = f"Virtual Device {device_number} Vertex {vertex_id_internals[1]}"

        # Modify the device id in all edges
        for edge in self.configuration.internal_edges:
            edge.fromId = f"virtual.{device_id.split('.')[-1]}.{'.'.join(edge.fromId.split('.')[2:])}"
            edge.toId = f"virtual.{device_id.split('.')[-1]}.{'.'.join(edge.toId.split('.')[2:])}"
            edge.vid = f"{edge.fromId}::{edge.toId}"
            edge.id = edge.vid
            edge.fDescriptor.label = edge.fDescriptor.label.replace(
                f"Virtual Device {old_device_number}", f"Virtual Device {device_number}"
            )

        for edge in self.configuration.external_edges:
            if edge.fromId.startswith(old_device_id):
                edge.fromId = f"virtual.{device_id.split('.')[-1]}.{'.'.join(edge.fromId.split('.')[2:])}"
            if edge.toId.startswith(old_device_id):
                edge.toId = f"virtual.{device_id.split('.')[-1]}.{'.'.join(edge.toId.split('.')[2:])}"

            edge.vid = f"{edge.fromId}::{edge.toId}"
            edge.id = edge.vid
            edge.fDescriptor.label = edge.fDescriptor.label.replace(
                f"Virtual Device {old_device_number}", f"Virtual Device {device_number}"
            )
