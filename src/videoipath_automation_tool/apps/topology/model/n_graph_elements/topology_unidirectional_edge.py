from enum import Enum
from typing import List, Literal, Optional

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
    )  # TODO: Find MAX
    weight: int = Field(
        default=0,
        ge=0,
        description="Enables service-based weight calculation. The given number is the weight that each service contributes with.",
        title="Weight per service",
    )  # TODO: Find MAX


class WeightFactors(BaseModel, validate_assignment=True):
    bandwidth: Bandwidth
    service: Service


class ConfigPriority(int, Enum):  # Important: In this case, the Enum is based on int, not str !
    high = 1
    low = 3
    normal = 2
    off = 0


RedundancyMode = Literal["Any", "OnlyMain", "OnlySpare"]


class UnidirectionalEdge(NGraphElement):
    """Model for unidirectional Edge."""

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
    weightFactors: WeightFactors
    type: Literal["unidirectionalEdge"] = "unidirectionalEdge"

    @classmethod
    def create(
        cls,
        preset: Literal["arista"],
        from_ip_vertex: IpVertex,
        to_ip_vertex: IpVertex,
        redundancy_mode: Optional[RedundancyMode] = "Any",
        bandwidth: Optional[float] = -1.0,
        weight: Optional[int] = 1,
    ) -> "UnidirectionalEdge":
        """Create a new UnidirectionalEdge instance for edge between two given IP Vertices.

        Args:
            preset: The preset to use (e.g. "arista")
            from_ip_vertex: The source IP Vertex.
            to_ip_vertex: The destination IP Vertex.
            **kwargs: Additional parameters.

        """
        # check direction -> Always from out to in:
        if from_ip_vertex.vertexType != "Out":
            raise ValueError(f"From edge must be of type 'Out' but is '{from_ip_vertex.vertexType}'")
        if to_ip_vertex.vertexType != "In":
            raise ValueError(f"To edge must be of type 'In' but is '{to_ip_vertex.vertexType}'")

        # generate key and name from vertices:
        key = f"{from_ip_vertex.id}::{to_ip_vertex.id}"
        label = f"{from_ip_vertex.fDescriptor.label} -> {to_ip_vertex.fDescriptor.label}"

        # Merge default values with kwargs:
        if preset == "arista":
            preset_data = {
                "active": True,
                "bandwidth": bandwidth,
                "capacity": 65535,
                "conflictPri": ConfigPriority.off,
                "descriptor": Descriptor(label="", desc=""),
                "excludeFormats": [],
                "fDescriptor": Descriptor(label=label, desc=""),
                "fromId": from_ip_vertex.id,
                "includeFormats": [],
                "redundancyMode": redundancy_mode,
                "tags": [],
                "toId": to_ip_vertex.id,
                "weight": weight,
                "weightFactors": WeightFactors(bandwidth=Bandwidth(weight=0), service=Service(max=100, weight=0)),
                "type": "unidirectionalEdge",
                "_vid": key,
                "_rev": None,
                "_id": key,
            }
        elif preset == "":
            pass
        else:
            raise ValueError(f"Unknown preset '{preset}'")

        return cls.model_validate(preset_data)

    def is_internal(self) -> bool:
        """Check if the edge is internal (i.e. connects two vertices of the same device)."""
        if self.fromId.startswith("device"):
            from_device_id = self.fromId.split(".")[0]
        elif self.fromId.startswith("virtual."):
            from_device_id = f"virtual.{self.fromId.split('.')[1]}"

        if self.toId.startswith("device"):
            to_device_id = self.toId.split(".")[0]
        elif self.toId.startswith("virtual."):
            to_device_id = f"virtual.{self.toId.split('.')[1]}"

        if not from_device_id or not to_device_id:
            raise ValueError(f"Could not determine device IDs from edge IDs '{self.fromId}' and '{self.toId}'")

        if from_device_id == to_device_id:
            return True
        else:
            return False
