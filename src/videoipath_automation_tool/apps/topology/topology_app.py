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
        self.experimental = TopologyExperimental(self._topology_api, self._logger, get_device_method=self.get_device)

        # --- Setup Synchronize Layer ---
        self.synchronize = TopologySynchronize(self._topology_api, self._logger)

        self._logger.debug("Topology APP initialized.")

    # --- Topology Device CRUD Operations ---

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
                        f"No services affected by updating device '{device.configuration.base_device.label}'/'{device.configuration.base_device.factory_label}'."
                    )
                else:
                    self._logger.warning(
                        f"Services affected by updating device '{device.configuration.base_device.label}'/'{device.configuration.base_device.factory_label}': {affected_services_list}. No changes applied. Release the affected services or set 'ignore_affected_services' to True."
                    )
                    return device

            response = self._topology_api.apply_device_configuration_changes(changes)
            if response:
                self._logger.info(
                    f"Device '{device.configuration.base_device.label}'/'{device.configuration.base_device.factory_label}' updated in topology."
                )
            else:
                self._logger.info(
                    f"No changes detected for device '{device.configuration.base_device.label}'/'{device.configuration.base_device.factory_label}'."
                )
        else:
            response = self._topology_api.add_device_initially(device)
            self._logger.info(
                f"Device '{device.configuration.base_device.label}'/'{device.configuration.base_device.factory_label}' added to topology."
            )
        return_device = self._topology_api.get_device_from_topology(device.configuration.base_device.id)
        return return_device

    def remove_device_by_id(self, device_id: str, ignore_affected_services: bool = False):
        """Remove a device from the topology by its device id.

        Args:
            device_id (str): Device Id (e.g. "device1")
            ignore_affected_services (bool, optional): If True, the method will remove the device even if services are affected. Defaults to False.

        Returns:
            RequestRestV2 | None: RequestRestV2 object if the device was removed successfully, None otherwise.

        """
        device_id = validate_device_id_including_virtual(device_id)

        device = self._topology_api.get_device_from_topology(device_id)
        return self.remove_device(device, ignore_affected_services)

    def remove_device(self, device: TopologyDevice, ignore_affected_services: bool = False):
        """Remove a device from the topology by

        Args:
            device (TopologyDevice): TopologyDevice object.
            ignore_affected_services (bool, optional): If True, the method will remove the device even if services are affected. Defaults to False.

        Returns:
            RequestRestV2 | None: RequestRestV2 object if the device was removed successfully, None otherwise.

        """

        if not ignore_affected_services:
            affected_services_list = self.list_services_affected_by_device_remove(device)
            if len(affected_services_list) == 0:
                self._logger.info(
                    f"No services affected by removing device '{device.configuration.base_device.label}'/'{device.configuration.base_device.factory_label}'."
                )
            else:
                self._logger.warning(
                    f"Services affected by removing device '{device.configuration.base_device.label}'/'{device.configuration.base_device.factory_label}': {affected_services_list}. No changes applied. Release the affected services or set 'ignore_affected_services' to True."
                )
                return None

        return self._topology_api.remove_device(device)

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

    def add_device_initially(self, device: TopologyDevice):
        """Add a device to the topology.

        Args:
            device (TopologyDevice): TopologyDevice object.

        Returns:
            RequestRestV2: RequestRestV2 object.
        """
        # For virtual devices, remove revision
        if device.configuration.base_device.isVirtual:
            if device.configuration.base_device.rev is None:
                self._logger.info(
                    f"Revision of virtual device '{device.configuration.base_device.label}' is None. It is assumed that the device does not yet exist on the server. Therefore the next free virtual device id will be determined automatically."
                )
                next_id = self._topology_api.get_next_virtual_device_id()
                self._logger.info(f"Next free virtual device id: '{next_id}'")
                device.set_virtual_device_id(next_id)

        return self._topology_api.add_device_initially(device)

    # --- Topology Device Helper Methods ---
    def find_device_id_by_label(
        self,
        label: str,
        label_search_mode: Literal[
            "canonical_label", "factory_label_only", "user_defined_label_only"
        ] = "canonical_label",
    ) -> Optional[str | List[str]]:
        """Find a device id by its label.

        Args:
            label (str): Label of the device.
            label_search_mode (Literal[&quot;canonical_label&quot;, &quot;factory_label_only&quot;, &quot;user_defined_label_only&quot;], optional): Label search mode. Defaults to "canonical_label".

        Returns:
            Optional[str | List[str]]: Device Id or list of Device Ids.
        """
        if label_search_mode == "canonical_label":
            return self._topology_api.get_device_id_by_canonical_label(label)
        elif label_search_mode == "factory_label_only":
            return self._topology_api.get_device_id_by_factory_label(label)
        elif label_search_mode == "user_defined_label_only":
            return self._topology_api.get_device_id_by_user_defined_label(label)
        else:
            raise ValueError(f"Invalid label_search_mode: {label_search_mode}")

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

    def list_services_affected_by_device_remove(self, device: TopologyDevice) -> list[str]:
        """
        List all bookings that are impacted if the given device is removed.

        Args:
            device (TopologyDevice): The device to be removed.

        Returns:
            list[str]: A list of affected booking IDs. Returns an empty list if no bookings are impacted.
        """
        validation = self._topology_api.validate_topology_remove(device)

        details = validation.data.get("details", {})
        return list(details) if details else []

    # --- Virtual Device Methods ---
    def create_virtual_device(self) -> TopologyDevice:
        """Create a virtual device with placeholder id 'virtual.0'.
        If this device is added to the topology, it will determine the next available virtual device id automatically.

        Returns:
            TopologyDevice: TopologyDevice object.
        """
        return TopologyDevice.create_virtual_device()

    # --- Wrapper methods for backward compatibility ---

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

    # --- Experimental Methods ---

    def create_edges(
        self,
        device_1_id: str,
        device_1_vertex_factory_label: str,
        device_2_id: str,
        device_2_vertex_factory_label: str,
        bandwidth: Optional[int] = None,
        bandwidth_factor: Optional[float] = None,
        redundancy_mode: Optional[str] = None,
        fixed_weight: Optional[int] = None,
    ) -> list[UnidirectionalEdge]:
        """
        This method automatically determines the correct edge configuration based on the vertex configuration of the devices.

        Args:
            device_1_id (str): Device Id of the first device.
            device_1_vertex_factory_label (str): Vertex factory label of the first device. Note: Do not specify 'in' or 'out' (e.g., use 'Ethernet1' instead of 'Ethernet1 (in)').
            device_2_id (str): Device Id of the second device.
            device_2_vertex_factory_label (str): Vertex factory label of the second device. Note: Do not specify 'in' or 'out' (e.g., use 'Ethernet1' instead of 'Ethernet1 (in)').
            bandwidth (Optional[int], optional): Bandwidth of the edge. Defaults to None.
            bandwidth_factor (Optional[float], optional): Factor to reduce the bandwidth for reserve capacity (e.g., 0.9 for 90%). Defaults to None.
            redundancy_mode (Optional[str], optional): Specifies the redundancy mode of the edge. Possible values: 'OnlyMain', 'OnlySpare', 'Any'. Defaults to None.
            fixed_weight (Optional[int], optional): Fixed weight of the edge. Defaults to None.

        Returns:
            list[UnidirectionalEdge]: A list of unidirectional edges representing the connection between the devices.
        """
        return self.experimental.create_edges(
            device_1_id=device_1_id,
            device_1_vertex_factory_label=device_1_vertex_factory_label,
            device_2_id=device_2_id,
            device_2_vertex_factory_label=device_2_vertex_factory_label,
            bandwidth=bandwidth,
            bandwidth_factor=bandwidth_factor,
            redundancy_mode=redundancy_mode,
            fixed_weight=fixed_weight,
        )


class TopologyExperimental:
    def __init__(self, topology_api: TopologyAPI, logger: logging.Logger, get_device_method):
        """Experimental layer for the TopologyApp."""

        self._topology_app = topology_api
        self._logger = logger
        self.get_device = get_device_method

    def replace_device_id(
        self,
        source_device: TopologyDevice,
        new_device_id: str,
        clear_revision: Optional[bool] = True,
        clear_external_edges: Optional[bool] = False,
    ) -> TopologyDevice:
        """Replace the device id of a device in the topology.
        Usefull for transferring a device to another VideoIPath-Server.

        Args:
            device (TopologyDevice): TopologyDevice object.
            new_device_id (str): New device id.
            clear_revision (Optional[bool], optional): If True, the revision of the device will be cleared. Defaults to True.
            clear_external_edges (Optional[bool], optional): If True, external edges will be removed. Defaults to False.
        Returns:
            TopologyDevice: Updated TopologyDevice object.
        """
        new_device_id = validate_device_id_including_virtual(new_device_id)
        old_device_id = source_device.configuration.base_device.id
        target_device = source_device.model_copy(deep=True)

        # 1. Base Device
        target_device.configuration.base_device.id = new_device_id
        target_device.configuration.base_device.vid = new_device_id
        target_device.configuration.base_device.rev = (
            None if clear_revision else target_device.configuration.base_device.rev
        )

        # 2. Vertices (Generic, Codec, IP)
        all_vertices = (
            target_device.configuration.generic_vertices
            + target_device.configuration.codec_vertices
            + target_device.configuration.ip_vertices
        )

        for vertex in all_vertices:
            vertex.id = vertex.id.replace(old_device_id, new_device_id)
            vertex.vid = vertex.vid.replace(old_device_id, new_device_id)
            vertex.deviceId = new_device_id
            if vertex.isVirtual:
                vertex.gpid.pointId[0] = new_device_id.replace("virtual.", "virtual-")
            else:
                vertex.gpid.pointId[0] = new_device_id
            vertex.rev = None if clear_revision else vertex.rev

        # 3. Edges
        all_edges = target_device.configuration.internal_edges + target_device.configuration.external_edges

        for edge in all_edges:
            if clear_external_edges and not edge.is_internal():
                target_device.configuration.external_edges.remove(edge)
                continue
            edge.id = edge.id.replace(old_device_id, new_device_id)
            edge.vid = edge.vid.replace(old_device_id, new_device_id)
            edge.fromId = edge.fromId.replace(old_device_id, new_device_id)
            edge.toId = edge.toId.replace(old_device_id, new_device_id)
            edge.rev = None if clear_revision else edge.rev

        return target_device

    # TODO: Refactor for production use
    def create_edges(
        self,
        device_1_id: str,
        device_1_vertex_factory_label: str,
        device_2_id: str,
        device_2_vertex_factory_label: str,
        bandwidth: Optional[int] = None,
        bandwidth_factor: Optional[float] = None,
        redundancy_mode: Optional[str] = None,
        fixed_weight: Optional[int] = None,
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
                    from_ip_vertex=device_2_vertices["out"], to_ip_vertex=device_1_vertices["in"]
                )
            )
            edges.append(
                UnidirectionalEdge.build_edge_from_vertices(
                    from_ip_vertex=device_1_vertices["out"], to_ip_vertex=device_2_vertices["in"]
                )
            )
        elif device_1_status == "both" and device_2_status == "out":
            edges.append(
                UnidirectionalEdge.build_edge_from_vertices(
                    from_ip_vertex=device_2_vertices["out"], to_ip_vertex=device_1_vertices["in"]
                )
            )
        elif device_1_status == "both" and device_2_status == "in":
            edges.append(
                UnidirectionalEdge.build_edge_from_vertices(
                    from_ip_vertex=device_1_vertices["out"], to_ip_vertex=device_2_vertices["in"]
                )
            )
        elif device_1_status == "out" and device_2_status == "both":
            edges.append(
                UnidirectionalEdge.build_edge_from_vertices(
                    from_ip_vertex=device_1_vertices["out"], to_ip_vertex=device_2_vertices["in"]
                )
            )
        elif device_1_status == "in" and device_2_status == "both":
            edges.append(
                UnidirectionalEdge.build_edge_from_vertices(
                    from_ip_vertex=device_2_vertices["out"], to_ip_vertex=device_1_vertices["in"]
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

        if fixed_weight:
            for edge in edges:
                edge.fixed_weight = fixed_weight

        for edge in edges:
            self._logger.info(f"Edge created: {edge.label}")
        return edges


class TopologySynchronize:
    """Synchronization layer for the TopologyApp.

    Note: Currently in development. Not all methods are implemented yet.

    => Use `topology.get_device_from_driver()` and `topology.add_device_initially()` or `topology.update_device()` for initial device synchronization.
    => For Synchronization of changed Elements:
    Get changes via `topology._topology_api.analyze_device_configuration_changes_local(device, device_from_driver)`. Analyze these with your own logic, if necessary change the configuration of the device and apply the changes via `topology.update_device(device)`.

    """

    def __init__(self, topology_api: TopologyAPI, logger: logging.Logger):
        self._topology_api = topology_api
        self._logger = logger

        # Status Reference:
        # - `InSync` (BaseDevice, internal Edges, Vertices): The device in topology is synchronized with the driver.
        # - `Missing` (BaseDevice, internal/external Edges, Vertices): Topology Elements, which are not available in the driver. (Note: This includes self-created edges)
        # - `NoContact` (BaseDevice, internal Edges, Vertices): Device/Element is not reachable, same status for corresponding internal edges and vertices.
        # - `NoDriver`: The device has been disabled in or removed from the inventory.
        # - `Changed` (BaseDevice, Edges, Vertices):
        #       - Device template config was changed but not applied to the topology. (e.g. new factory label/description, internal edges in different constellation)
        #       - Element template config was changed but not applied to the topology (e.g. factory label, factory description). Not sure which other properties are relevant.
        # - `Virtual` (Virtual BaseDevice, Virtual Vertices): The device/Element is a virtual entity.
        #
        # Note
        # - External Edges are always in status `Missing`.
        # - If a BaseDevice is in status `NoDriver`, all corresponding internal edges get the status `Missing`. Vertices get the status `NoDriver`.
        # - If a BaseDevice is in status `NoContact`, all corresponding internal edges get the status `Missing`. Vertices get the status `NoContact`.
        # - If a BaseDevice is in status `Virtual`, all corresponding internal edges get the status `Missing`. Vertices get the status `Virtual`.
        # - A BaseDevice shows the status `Changed` if at least one of its internal edges or vertices has the status `Missing`.
        # - A BaseDevice remains in status `InSync` if corresponding internal edges and vertices are in status `Changed`.

    def get_all_device_status(self) -> dict[str, str]:
        """Get the synchronization status of all devices in the topology.

        Returns:
            dict: Dictionary with the sync status of all devices. Format: {device_id: sync_status}
            Possible sync_status values:
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

    def get_detailed_device_status(self, device_id: str) -> dict[str, str]:
        """Get the synchronization status of all elements of a device in the topology.

        Args:
            device_id (str): Device Id (e.g. "device1")

        Returns:
            dict: Dictionary with the sync status of all elements of the device. Format: {element_id: sync_status}
            Possible sync_status values: `InSync`, `Missing`, `NoContact`, `NoDriver`, `Changed`, `Virtual`
        """
        return self._topology_api.get_device_elements_sync_status(device_id)

    @staticmethod
    def filter_device_status(
        device_status: dict[str, str],
        sync_status: Literal["InSync", "Missing", "NoContact", "NoDriver", "Changed", "Virtual"],
    ) -> list[str]:
        """Filter the device status dictionary by a specific sync status.
        Status dictionary format can be obtained via `get_detailed_device_status()` or `get_all_device_status()`.

        Args:
            device_status (dict[str, str]): Dictionary with the sync status of all devices. Format: {device_id: sync_status}
            sync_status (str): Sync status to filter for. Possible values: `InSync`, `Missing`, `NoContact`, `NoDriver`, `Changed`, `Virtual`

        Returns:
            list: List of device ids with the specified sync status.
        """
        return [device_id for device_id, status in device_status.items() if status == sync_status]

    # TODO: Implement more methods for synchronization
    # - sync_device => behavior like in the GUI + additional options, e.g. map_config_by_label ...
    # - ...
