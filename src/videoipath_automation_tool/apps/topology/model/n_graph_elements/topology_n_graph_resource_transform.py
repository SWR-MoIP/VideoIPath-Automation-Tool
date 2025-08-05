from typing import List, Literal

from pydantic import Field

from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_n_graph_element import (
    Descriptor,
    NGraphElement,
)


class NGraphResourceTransform(NGraphElement):
    """
    Represents the attributes of a nGraphResourceTransform.

    """

    active: bool = Field(default=True)
    descriptor: Descriptor
    fDescriptor: Descriptor
    fromId: str
    tags: List[str] = Field(default=[], description="List of tags.")
    toId: str
    fResourceIds: List[str] = Field(default=[], description="Factory resource ids")
    resourceIds: List[str] = Field(default=[], description="User resource ids")
    type: Literal["nGraphResourceTransform"] = "nGraphResourceTransform"

    @property
    def from_id(self) -> str:
        """The source vertex ID."""
        return self.fromId

    @property
    def to_id(self) -> str:
        """The destination vertex ID."""
        return self.toId

    @property
    def factory_resource_ids(self) -> List[str]:
        """The factory resource IDs."""
        return self.fResourceIds

    @property
    def resource_ids(self) -> List[str]:
        """The user defined resource IDs."""
        return self.resourceIds
