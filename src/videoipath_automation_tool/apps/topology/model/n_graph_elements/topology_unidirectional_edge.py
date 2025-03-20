from enum import Enum
from typing import List, Literal

from pydantic import BaseModel, Field

from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_ip_vertex import IpVertex
from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_n_graph_element import (
    Descriptor,
    NGraphElement,
)


class Bandwidth(BaseModel, validate_assignment=True):
    weight: int = Field(
        default=0,
        ge=0,
        description="Enables bandwidth-based weight calculation. The number corresponds to the weight at 100 percent link utilization.",
        title="Bandwidth weight factor",
    )


class Service(BaseModel, validate_assignment=True):
    max: int = Field(
        default=0,
        ge=0,
        description="The maximum value that service weighting will contribute with. Useful to define an absolute.",
        title="Max total",
    )
    weight: int = Field(
        default=0,
        ge=0,
        description="Enables service-based weight calculation. The given number is the weight that each service contributes with.",
        title="Weight per service",
    )


class WeightFactors(BaseModel, validate_assignment=True):
    bandwidth: Bandwidth
    service: Service


class ConfigPriority(int, Enum):  # Note: Enum is based on int
    high = 1
    low = 3
    normal = 2
    off = 0


RedundancyMode = Literal["Any", "OnlyMain", "OnlySpare"]


class UnidirectionalEdge(NGraphElement):
    """
    Represents the attributes of a unidirectional edge.

    """

    active: bool = True
    bandwidth: float = Field(
        default=-1.0, ge=-1.0, description="Max allowed bandwidth.", title="Bandwidth capacity in Mbit/s"
    )  # -1.0 => not set
    capacity: int = Field(
        default=65535, ge=0, description="Max number of simultaneous services.", title="Services capacity"
    )  # 65535 => not set
    conflictPri: ConfigPriority = ConfigPriority.off
    descriptor: Descriptor
    excludeFormats: List[str] = Field(default=[], description="List of formats to exclude from the edge.")
    fDescriptor: Descriptor
    fromId: str
    includeFormats: List[str] = Field(default=[], description="List of formats to include in the edge.")
    redundancyMode: RedundancyMode = "Any"
    tags: List[str] = Field(default=[], description="List of tags.")
    toId: str
    weight: int = Field(default=0, ge=0, description="The edge weight/cost for routing.", title="Fixed weight")
    weightFactors: WeightFactors = Field(
        default_factory=lambda: WeightFactors(bandwidth=Bandwidth(weight=0), service=Service(max=100, weight=0))
    )
    type: Literal["unidirectionalEdge"] = "unidirectionalEdge"

    @property
    def include_formats(self) -> List[str]:
        """Include Formats: List of formats to include in the edge."""
        return self.includeFormats

    @include_formats.setter
    def include_formats(self, value: List[str]):
        """Include Formats: List of formats to include in the edge."""
        self.includeFormats = value

    @property
    def exclude_formats(self) -> List[str]:
        """Exclude Formats: List of formats to exclude from the edge."""
        return self.excludeFormats

    @exclude_formats.setter
    def exclude_formats(self, value: List[str]):
        """Exclude Formats: List of formats to exclude from the edge."""
        self.excludeFormats = value

    @property
    def conflict_priority(self) -> Literal["high", "low", "normal", "off"]:
        """Conflict Priority (`high`, `low`, `normal`, `off`)."""
        return self.conflictPri.name

    @conflict_priority.setter
    def conflict_priority(self, value: Literal["high", "low", "normal", "off"]):
        """Conflict Priority (`high`, `low`, `normal`, `off`)."""
        try:
            self.conflictPri = ConfigPriority[value]
        except KeyError:
            raise ValueError(
                f"Invalid conflict priority: {value}. Must be one of {list(ConfigPriority.__members__.keys())}"
            )

    @property
    def redundancy_mode(self) -> RedundancyMode:
        """Redundancy Mode: `Any`, `OnlyMain` or `OnlySpare`."""
        return self.redundancyMode

    @redundancy_mode.setter
    def redundancy_mode(self, value: RedundancyMode):
        """Redundancy Mode: `Any`, `OnlyMain` or `OnlySpare`."""
        self.redundancyMode = value

    @property
    def fixed_weight(self) -> int:
        """Fixed weight: The edge weight/cost for routing."""
        return self.weight

    @fixed_weight.setter
    def fixed_weight(self, value: int):
        """Fixed weight: The edge weight/cost for routing."""
        self.weight = value

    @property
    def bandwidth_capacity(self) -> float:
        """Bandwidth capacity: Max allowed bandwidth."""
        return self.bandwidth

    @bandwidth_capacity.setter
    def bandwidth_capacity(self, value: float):
        """Bandwidth capacity: Max allowed bandwidth."""
        self.bandwidth = value

    def disable_bandwidth_capacity(self):
        """Disable bandwidth capacity (Set to `Disabled` / internal value: -1)."""
        self.bandwidth = -1

    @property
    def services_capacity(self) -> int:
        """Services capacity: Max number of simultaneous services."""
        return self.capacity

    @services_capacity.setter
    def services_capacity(self, value: int):
        """Services capacity: Max number of simultaneous services."""
        self.capacity = value

    def disable_service_capacity(self):
        """Disable service capacity (Set to `Unlimited` / internal value: 65535)."""
        self.capacity = 65535

    @property
    def bandwidth_weight_factor(self) -> int:
        """Bandwidth weight factor: Enables bandwidth-based weight calculation. The number corresponds to the weight at 100 percent link utilization."""
        return self.weightFactors.bandwidth.weight

    @bandwidth_weight_factor.setter
    def bandwidth_weight_factor(self, value: int):
        """Bandwidth weight factor: Enables bandwidth-based weight calculation. The number corresponds to the weight at 100 percent link utilization."""
        self.weightFactors.bandwidth.weight = value

    def disable_bandwidth_weight_factor(self):
        """Disable bandwidth weight factor (Set to `Disabled` / internal value: 0)."""
        self.weightFactors.bandwidth.weight = 0

    @property
    def weight_per_service(self) -> Service:
        """Weight per service: Enables service-based weight calculation. The given number is the weight that each service contributes with."""
        return self.weightFactors.service

    @weight_per_service.setter
    def weight_per_service(self, value: Service | tuple[int, int]):
        """Weight per service: Enables service-based weight calculation. The given number is the weight that each service contributes with.\n
        Expects a tuple (max, weight) or a Service object"""
        if isinstance(value, tuple):
            if not all(isinstance(i, int) for i in value):
                raise TypeError("weight_per_service tuple must contain two integers (max, weight)")
            self.weightFactors.service.max = value[0]
            self.weightFactors.service.weight = value[1]
        elif isinstance(value, Service):
            self.weightFactors.service = value
        else:
            raise TypeError("weight_per_service must be of type Service or tuple[int, int]")

    def disable_weight_per_service(self):
        """Disable weight per service (Set to `Disabled` / internal values: max=100, weight=0)."""
        self.weightFactors.service.max = 100
        self.weightFactors.service.weight = 0

    @property
    def from_id(self) -> str:
        """The source vertex ID."""
        return self.fromId

    @property
    def to_id(self) -> str:
        """The destination vertex ID."""
        return self.toId

    # --- Class Methods ---
    @classmethod
    def build_edge_from_vertices(
        cls,
        from_ip_vertex: IpVertex,
        to_ip_vertex: IpVertex,
        description: str = "",
        tags: List[str] = [],
        include_formats: List[str] = [],
        exclude_formats: List[str] = [],
        conflict_priority: Literal["high", "low", "normal", "off"] = "off",
        redundancy_mode: RedundancyMode = "Any",
        fixed_weight: int = 1,
        bandwidth_capacity: float = -1.0,
        services_capacity: int = 65535,
        bandwidth_weight_factor: int = 0,
        weight_per_service: Service | tuple[int, int] = Service(max=100, weight=0),
        active: bool = True,
    ) -> "UnidirectionalEdge":
        """Create a new UnidirectionalEdge instance for edge between two given IP Vertices.

        Args:
            from_ip_vertex (IpVertex): The source IP Vertex.
            to_ip_vertex (IpVertex): The destination IP Vertex.
            description (str): Description of the edge.
            tags (List[str]): List of tags.
            include_formats (List[str]): List of formats to include in the edge.
            exclude_formats (List[str]): List of formats to exclude from the edge.
            conflict_priority (Literal["high", "low", "normal", "off"]): Conflict Priority.
            redundancy_mode (RedundancyMode): Redundancy Mode: `Any`, `OnlyMain` or `OnlySpare`.
            fixed_weight (int): The edge weight/cost for routing.
            bandwidth_capacity (float): Max allowed bandwidth.
            services_capacity (int): Max number of simultaneous services.
            bandwidth_weight_factor (int): Bandwidth weight factor: Enables bandwidth-based weight calculation. The number corresponds to the weight at 100 percent link utilization.
            weight_per_service (Service | tuple[int, int]): Weight per service: Enables service-based weight calculation. The given number is the weight that each service contributes with.
            active (bool): Active state of the edge.
        """

        if from_ip_vertex.vertexType != "Out":
            raise ValueError(
                f"From edge '{from_ip_vertex.id}' must be of type 'Out' but is '{from_ip_vertex.vertexType}'"
            )
        if to_ip_vertex.vertexType != "In":
            raise ValueError(f"To edge '{to_ip_vertex.id}' must be of type 'In' but is '{to_ip_vertex.vertexType}'")

        # Generate nGraph id/key and label in schema of Inspect App from given IP Vertex instances:
        key = f"{from_ip_vertex.id}::{to_ip_vertex.id}"
        label = f"{from_ip_vertex.fDescriptor.label} -\u003e {to_ip_vertex.fDescriptor.label}"

        # Convert weight_per_service if it's a tuple
        if isinstance(weight_per_service, tuple):
            weight_per_service = Service(max=weight_per_service[0], weight=weight_per_service[1])

        return cls(
            active=active,
            bandwidth=bandwidth_capacity,
            capacity=services_capacity,
            conflictPri=ConfigPriority[conflict_priority],
            descriptor=Descriptor(label=label, desc=description),
            excludeFormats=exclude_formats,
            fDescriptor=Descriptor(label="", desc=""),
            fromId=from_ip_vertex.id,
            includeFormats=include_formats,
            redundancyMode=redundancy_mode,
            tags=tags,
            toId=to_ip_vertex.id,
            weight=fixed_weight,
            weightFactors=WeightFactors(
                bandwidth=Bandwidth(weight=bandwidth_weight_factor),
                service=weight_per_service,
            ),
            type="unidirectionalEdge",
            _vid=key,
            _rev=None,
            _id=key,
        )

    # --- Methods ---
    def is_internal(self) -> bool:
        """Check if the edge is internal (i.e. connects two vertices of the same device)
        by comparing the device IDs of the source and destination vertices.

        Returns:
            bool: True if the edge is internal, False otherwise.
        """

        def get_device_id(edge_id: str) -> str:
            if edge_id.startswith("device"):
                return edge_id.split(".")[0]
            elif edge_id.startswith("virtual."):
                return f"virtual.{edge_id.split('.')[1]}"
            raise ValueError(f"Could not determine device ID from edge ID '{edge_id}'")

        return get_device_id(self.fromId) == get_device_id(self.toId)
