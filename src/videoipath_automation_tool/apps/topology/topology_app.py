import logging
from typing import List, Literal, Optional

from typing_extensions import deprecated

from videoipath_automation_tool.apps.topology.helper.placement import TopologyPlacement
from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_base_device import BaseDevice
from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_codec_vertex import CodecVertex
from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_generic_vertex import GenericVertex
from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_ip_vertex import IpVertex
from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_unidirectional_edge import (
    UnidirectionalEdge,
)
from videoipath_automation_tool.apps.topology.model.topology_device import TopologyDevice
from videoipath_automation_tool.apps.topology.topology_api import TopologyAPI
from videoipath_automation_tool.connector.vip_connector import VideoIPathConnector
from videoipath_automation_tool.utils.cross_app_utils import create_fallback_logger
from videoipath_automation_tool.validators.device_id_including_virtual import validate_device_id_including_virtual


class TopologyApp:
    def __init__(self, vip_connector: VideoIPathConnector, logger: Optional[logging.Logger] = None):
        """TopologyApp contains functionality to interact with the VideoIPath Topology.

        Args:
            vip_connector (VideoIPathConnector): VideoIPathConnector instance to handle the connection to the VideoIPath-Server.
            logger (Optional[logging.Logger], optional): Logger instance to use for logging.
        """
        # --- Setup Logging ---
        self._logger = logger or create_fallback_logger("videoipath_automation_tool_inventory_app")

        # --- Setup Topology API ---
        self._topology_api = TopologyAPI(vip_connector=vip_connector, logger=self._logger)

        # --- Setup Placement Layer ---
        self.placement = TopologyPlacement(self._topology_api, self._logger)

        # --- Setup Experimental Layer ---
        self.experimental = TopologyExperimental(self._topology_api, self._logger)

        # --- Setup Synchronize Layer ---
        self.synchronize = TopologySynchronize(self._topology_api, self._logger)

        self._logger.debug("Topology APP initialized.")

    def get_device(self, device_id: str) -> TopologyDevice:
        """Get a topology device by its device id. If the device does not exist, method will try to create the device from the driver.

        Args:
            device_id (str): Device Id (e.g. "device1")

        Returns:
            TopologyDevice: TopologyDevice object.
        """
        device_id = validate_device_id_including_virtual(device_id)

        if not self._topology_api.check_device_in_topology_available(device_id):
            if device_id.startswith("virtual"):
                raise ValueError(
                    f"Virtual Device with id '{device_id}' not found in topology, please create and add it first."
                )
            if not self.check_device_from_driver_available(device_id):
                raise ValueError(f"Device with id '{device_id}' not found in topology and driver not available")
            return self._topology_api.get_device_from_driver(device_id)
        else:
            return self._topology_api.get_device_from_topology(device_id)

    def update_device(self, device: TopologyDevice, ignore_affected_services: bool = False) -> TopologyDevice:
        """Update a device in the topology. If the device does not exist, it will be added to the topology.

        Args:
            device (TopologyDevice): TopologyDevice object.
            ignore_affected_services (bool, optional): If True, the method will update the device even if services are affected. Defaults to False.

        Returns:
            TopologyDevice: Updated TopologyDevice object, refetched from the topology.
        """
        if self.check_device_in_topology_available(device.configuration.base_device.id):
            changes = self._topology_api.analyze_device_configuration_changes(device)
            self._logger.debug(f"Changes: {changes.get_changed_elements()}")

            if not ignore_affected_services:
                affected_services_list = self.list_services_affected_by_device_update(device)
                if len(affected_services_list) == 0:
                    self._logger.info(
                        f"No services affected by updating device '{device.configuration.base_device.label}'."
                    )
                else:
                    self._logger.warning(
                        f"Services affected by updating device '{device.configuration.base_device.label}': {affected_services_list}. No changes applied. Release the affected services or set 'ignore_affected_services' to True."
                    )
                    return device

            response = self._topology_api.apply_device_configuration_changes(changes)
            if response:
                self._logger.info(f"Device '{device.configuration.base_device.label}' updated in topology.")
            else:
                self._logger.info(f"No changes detected for device '{device.configuration.base_device.label}'.")
        else:
            response = self._topology_api.add_device_initially(device)
            self._logger.info(f"Device '{device.configuration.base_device.label}' added to topology.")
        return_device = self._topology_api.get_device_from_topology(device.configuration.base_device.id)
        return return_device

    def get_device_from_driver(self, device_id: str) -> TopologyDevice:
        """Get a device auto generated by VideoIPath via the driver.

        Args:
            device_id (str): Device Id (e.g. "device1")

        Returns:
            TopologyDevice: TopologyDevice object.
        """
        return self._topology_api.get_device_from_driver(device_id)

    def get_element_by_id(
        self, vertex_id: str
    ) -> BaseDevice | CodecVertex | IpVertex | UnidirectionalEdge | GenericVertex:
        """
        Get an element by its unique id.

        Args:
            vertex_id (str): Unique Vertex id.

        Returns:
            BaseDevice | CodecVertex | IpVertex | UnidirectionalEdge | GenericVertex: nGraph element object.
        """
        return self._topology_api._fetch_nGraphElement_by_key(vertex_id)

    def get_element_by_label(
        self,
        vertex_label: str,
        mode: Literal["user_defined", "factory"] = "user_defined",
        filter_type: Literal[
            "all", "base_device", "codec_vertex", "ip_vertex", "unidirectional_edge", "generic_vertex"
        ] = "all",
    ) -> (
        BaseDevice
        | CodecVertex
        | IpVertex
        | UnidirectionalEdge
        | GenericVertex
        | List[BaseDevice | CodecVertex | IpVertex | UnidirectionalEdge | GenericVertex]
    ):
        """Get an element by its label.

        Args:
            label (str): Label of the element.
            mode (Literal[&quot;user_defined&quot;, &quot;factory&quot;], optional): Search mode. Defaults to "user_defined".
            filter_type (Literal[&quot;all&quot;, &quot;base_device&quot;, &quot;codec_vertex&quot;, &quot;ip_vertex&quot;, &quot;unidirectional_edge&quot;, &quot;generic_vertex&quot;], optional): Filter type. Defaults to "all".

        Returns:
            nGraph element object or list of objects.
        """
        return self._topology_api.get_element_by_label(vertex_label, mode, filter_type)

    def update_element(self, element: BaseDevice | CodecVertex | IpVertex | UnidirectionalEdge | GenericVertex):
        """
        Update a single nGraph element in the topology.

        Args:
            vertex (BaseDevice | CodecVertex | IpVertex | UnidirectionalEdge | GenericVertex): nGraph element object.
        """
        return self._topology_api.update_element(element)

    def check_device_from_driver_available(self, device_id: str) -> bool:
        """Check if the representation generated by a driver is available for a device.

        Args:
            device_id (str): Device Id (e.g. "device1")

        Returns:
            bool: True if the representation generated by a driver is available, False otherwise.
        """
        return self._topology_api.check_device_from_driver_available(device_id)

    def check_device_in_topology_available(self, device_id: str) -> bool:
        """Check if a device exists in the topology.

        Args:
            device_id (str): Device Id (e.g. "device1")

        Returns:
            bool: True if the device exists, False otherwise.
        """
        return self._topology_api.check_device_in_topology_available(device_id)

    def add_device_initially(self, device: TopologyDevice):
        """Add a device to the topology.

        Args:
            device (TopologyDevice): TopologyDevice object.

        Returns:
            RequestRestV2: RequestRestV2 object.
        """
        return self._topology_api.add_device_initially(device)

    def list_services_affected_by_device_update(self, device: TopologyDevice) -> list[str]:
        """
        List all bookings that are impacted if the given device configuration is applied.

        Args:
            device (TopologyDevice): The device whose configuration changes should be analyzed.

        Returns:
            list[str]: A list of affected booking IDs. Returns an empty list if no bookings are impacted.
        """
        changes = self._topology_api.analyze_device_configuration_changes(device)
        validation = self._topology_api.validate_topology_update(changes)

        details = validation.data.get("details", {})
        return list(details) if details else []

    # Wrapper methods for backward compatibility

    @deprecated("This method is deprecated and will be removed in future versions. Use 'get_element_by_label' instead.")
    def get_vertex_by_label(
        self, vertex_label: str, mode: Literal["user_defined", "factory"] = "user_defined"
    ) -> (
        BaseDevice
        | CodecVertex
        | IpVertex
        | UnidirectionalEdge
        | GenericVertex
        | List[BaseDevice | CodecVertex | IpVertex | UnidirectionalEdge | GenericVertex]
    ):
        self._logger.warning(
            "Method 'get_vertex_by_label' is deprecated. It will be removed in future versions. Please use 'get_element_by_label' instead."
        )
        return self._topology_api.get_element_by_label(vertex_label, mode)

    @deprecated("This method is deprecated and will be removed in future versions. Use 'update_element' instead.")
    def update_vertex(self, vertex: BaseDevice | CodecVertex | IpVertex | UnidirectionalEdge | GenericVertex):
        """
        Update a single vertex in the topology.

        Args:
            vertex (BaseDevice | CodecVertex | IpVertex | UnidirectionalEdge | GenericVertex): Vertex object.
        """
        self._logger.warning(
            "Method 'update_vertex' is deprecated. It will be removed in future versions. Please use 'update_element' instead."
        )
        return self._topology_api.update_element(vertex)

    # --- Experimental ---

    def create_edges(
        self,
        device_1_id: str,
        device_1_vertex_factory_label: str,
        device_2_id: str,
        device_2_vertex_factory_label: str,
        bandwidth: Optional[int] = None,
        bandwidth_factor: Optional[float] = None,
        redundancy_mode: Optional[str] = None,
    ) -> list[UnidirectionalEdge]:
        """
        The method will automatically determine the correct edge configuration based on the vertex configuration of the devices.
        """
        device_1 = self.get_device(device_1_id)
        device_2 = self.get_device(device_2_id)
        device_1_vertices = device_1.configuration.get_ip_vertex_by_label(device_1_vertex_factory_label)
        device_2_vertices = device_2.configuration.get_ip_vertex_by_label(device_2_vertex_factory_label)
        if not device_1_vertices:
            raise ValueError(
                f"Vertex with label '{device_1_vertex_factory_label}' not found in device '{device_1.configuration.base_device.label}'."
            )
        if not device_2_vertices:
            raise ValueError(
                f"Vertex with label '{device_2_vertex_factory_label}' not found in device '{device_2.configuration.base_device.label}'."
            )

        # print(device_1_vertices)
        # print(device_2_vertices)
        # TODO!

        if "in" in device_1_vertices and "out" in device_1_vertices:
            if device_1_vertices["in"] and device_1_vertices["out"]:
                device_1_status = "both"
            elif device_1_vertices["out"]:
                device_1_status = "out"
            elif device_1_vertices["in"]:
                device_1_status = "in"
            else:
                device_1_status = None

        if "in" in device_2_vertices and "out" in device_2_vertices:
            if device_2_vertices["in"] and device_2_vertices["out"]:
                device_2_status = "both"
            elif device_2_vertices["out"]:
                device_2_status = "out"
            elif device_2_vertices["in"]:
                device_2_status = "in"
            else:
                device_2_status = None

        if not device_1_status or not device_2_status:
            raise ValueError("Invalid vertex configuration.")

        edges = []  # type: list[UnidirectionalEdge]

        if device_1_status == "both" and device_2_status == "both":
            edges.append(
                UnidirectionalEdge.build_edge_from_vertices(
                    preset="arista", from_ip_vertex=device_2_vertices["out"], to_ip_vertex=device_1_vertices["in"]
                )
            )
            edges.append(
                UnidirectionalEdge.build_edge_from_vertices(
                    preset="arista", from_ip_vertex=device_1_vertices["out"], to_ip_vertex=device_2_vertices["in"]
                )
            )
        elif device_1_status == "both" and device_2_status == "out":
            edges.append(
                UnidirectionalEdge.build_edge_from_vertices(
                    preset="arista", from_ip_vertex=device_2_vertices["out"], to_ip_vertex=device_1_vertices["in"]
                )
            )
        elif device_1_status == "both" and device_2_status == "in":
            edges.append(
                UnidirectionalEdge.build_edge_from_vertices(
                    preset="arista", from_ip_vertex=device_1_vertices["out"], to_ip_vertex=device_2_vertices["in"]
                )
            )
        elif device_1_status == "out" and device_2_status == "both":
            edges.append(
                UnidirectionalEdge.build_edge_from_vertices(
                    preset="arista", from_ip_vertex=device_1_vertices["out"], to_ip_vertex=device_2_vertices["in"]
                )
            )
        elif device_1_status == "in" and device_2_status == "both":
            edges.append(
                UnidirectionalEdge.build_edge_from_vertices(
                    preset="arista", from_ip_vertex=device_2_vertices["out"], to_ip_vertex=device_1_vertices["in"]
                )
            )

        if bandwidth:
            for edge in edges:
                edge.bandwidth = bandwidth
                if bandwidth_factor:
                    edge.bandwidth = int(bandwidth * bandwidth_factor)

        if redundancy_mode:
            if redundancy_mode == "OnlyMain" or redundancy_mode == "OnlySpare" or redundancy_mode == "Any":
                for edge in edges:
                    edge.redundancyMode = redundancy_mode
            else:
                raise ValueError("Invalid redundancy mode, must be 'OnlyMain', 'OnlySpare' or 'Any'.")

        for edge in edges:
            self._logger.info(f"Edge created: {edge.factory_label}")
        return edges


class TopologyExperimental:
    def __init__(self, topology_api: TopologyAPI, logger: logging.Logger):
        self._topology_api = topology_api
        self._logger = logger

    def auto_create_edge(
        self,
        device_1: TopologyDevice,
        device_1_vertex_label: str,
        device_2: TopologyDevice,
        device_2_vertex_label: str,
        bandwidth: Optional[int] = None,
        bandwidth_factor: Optional[float] = None,
        redundancy_mode: Optional[str] = None,
    ) -> list[UnidirectionalEdge]:
        device_1_vertices = device_1.configuration.get_ip_vertex_by_label(device_1_vertex_label)
        device_2_vertices = device_2.configuration.get_ip_vertex_by_label(device_2_vertex_label)
        if not device_1_vertices:
            raise ValueError(
                f"Vertex with label '{device_1_vertex_label}' not found in device '{device_1.configuration.base_device.label}'."
            )
        if not device_2_vertices:
            raise ValueError(
                f"Vertex with label '{device_2_vertex_label}' not found in device '{device_2.configuration.base_device.label}'."
            )

        if "in" in device_1_vertices and "out" in device_1_vertices:
            if device_1_vertices["in"] and device_1_vertices["out"]:
                device_1_status = "both"
            elif device_1_vertices["out"]:
                device_1_status = "out"
            elif device_1_vertices["in"]:
                device_1_status = "in"
            else:
                device_1_status = None

        if "in" in device_2_vertices and "out" in device_2_vertices:
            if device_2_vertices["in"] and device_2_vertices["out"]:
                device_2_status = "both"
            elif device_2_vertices["out"]:
                device_2_status = "out"
            elif device_2_vertices["in"]:
                device_2_status = "in"
            else:
                device_2_status = None

        if not device_1_status or not device_2_status:
            raise ValueError("Invalid vertex configuration.")

        edges = []  # type: list[UnidirectionalEdge]

        if device_1_status == "both" and device_2_status == "both":
            edges.append(
                UnidirectionalEdge.build_edge_from_vertices(
                    preset="arista", from_ip_vertex=device_2_vertices["out"], to_ip_vertex=device_1_vertices["in"]
                )
            )
            edges.append(
                UnidirectionalEdge.build_edge_from_vertices(
                    preset="arista", from_ip_vertex=device_1_vertices["out"], to_ip_vertex=device_2_vertices["in"]
                )
            )
        elif device_1_status == "both" and device_2_status == "out":
            edges.append(
                UnidirectionalEdge.build_edge_from_vertices(
                    preset="arista", from_ip_vertex=device_2_vertices["out"], to_ip_vertex=device_1_vertices["in"]
                )
            )
        elif device_1_status == "both" and device_2_status == "in":
            edges.append(
                UnidirectionalEdge.build_edge_from_vertices(
                    preset="arista", from_ip_vertex=device_1_vertices["out"], to_ip_vertex=device_2_vertices["in"]
                )
            )
        elif device_1_status == "out" and device_2_status == "both":
            edges.append(
                UnidirectionalEdge.build_edge_from_vertices(
                    preset="arista", from_ip_vertex=device_1_vertices["out"], to_ip_vertex=device_2_vertices["in"]
                )
            )
        elif device_1_status == "in" and device_2_status == "both":
            edges.append(
                UnidirectionalEdge.build_edge_from_vertices(
                    preset="arista", from_ip_vertex=device_2_vertices["out"], to_ip_vertex=device_1_vertices["in"]
                )
            )

        if bandwidth:
            for edge in edges:
                edge.bandwidth = bandwidth
                if bandwidth_factor:
                    edge.bandwidth = int(bandwidth * bandwidth_factor)

        if redundancy_mode:
            if redundancy_mode == "OnlyMain" or redundancy_mode == "OnlySpare" or redundancy_mode == "Any":
                for edge in edges:
                    edge.redundancyMode = redundancy_mode
            else:
                raise ValueError("Invalid redundancy mode, must be 'OnlyMain', 'OnlySpare' or 'Any'.")

        return edges


class TopologySynchronize:
    def __init__(self, topology_api: TopologyAPI, logger: logging.Logger):
        self._topology_api = topology_api
        self._logger = logger

    def get_all_device_status(self) -> dict[str, str]:
        """Get the synchronization status of all devices in the topology.

        Returns:
            dict: Dictionary with the sync status of all devices. Format: {device_id: sync_status}
            Possible sync_status values: `InSync`, `Missing`, `NoContact`, `NoDriver`, `Changed`, `Virtual`

        """
        return self._topology_api.get_all_device_sync_status()

    def get_device_status(self, device_id: str) -> str:
        """Get the synchronization status of a device in the topology.

        Args:
            device_id (str): Device Id (e.g. "device1")

        Returns:
            str: Sync status of the device. Possible values: `InSync`, `Missing`, `NoContact`, `NoDriver`, `Changed`, `Virtual`
        """
        return self._topology_api.get_device_sync_status(device_id)
