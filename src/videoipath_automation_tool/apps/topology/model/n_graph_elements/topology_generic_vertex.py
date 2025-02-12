from typing import Literal

from videoipath_automation_tool.apps.topology.model.n_graph_elements.topology_vertex import Vertex


class GenericVertex(Vertex):
    """Represents a generic vertex in the topology."""

    type: Literal["genericVertex"] = "genericVertex"
