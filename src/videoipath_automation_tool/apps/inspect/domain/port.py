from __future__ import annotations

from typing import TYPE_CHECKING

from videoipath_automation_tool.apps.inspect.model.collector import (
    InspectApiSingleVertexInfo,
    InspectPortStatus,
)
from videoipath_automation_tool.apps.inspect.model.common import InspectApiStatusSummary, InspectFrozenModel
from videoipath_automation_tool.apps.inspect.snapshot import InspectSnapshot, _IndexedPort, _port_id_from_status

if TYPE_CHECKING:
    from videoipath_automation_tool.apps.inspect.domain.device import InspectDevice
    from videoipath_automation_tool.apps.inspect.domain.edge import InspectEdge


class InspectPort(InspectFrozenModel):
    snapshot: InspectSnapshot
    indexed: _IndexedPort

    @property
    def id(self) -> str | None:
        return _port_id_from_status(self.indexed.port)

    @property
    def label(self) -> str | None:
        return self.indexed.port.effective_label

    @property
    def device(self) -> InspectDevice | None:
        return self.snapshot.get_device_by_id(self.indexed.device_id)

    @property
    def module_id(self) -> str | None:
        return self.indexed.module_id

    @property
    def status(self) -> InspectApiStatusSummary | None:
        return self.indexed.port.status

    @property
    def tags(self) -> list[str]:
        """Tags assigned to this port (as ``Category~~name`` ids). Assign them with
        ``app.inspect.update_vertex(port.vertex_id, tags=[...])``."""
        return self.indexed.port.assigned_tags

    @property
    def vertex_id(self) -> str | None:
        return self._vertex_id_from(self.indexed.port)

    @property
    def edge(self) -> InspectEdge | None:
        port_id = self.id
        if not port_id:
            return None
        return self.snapshot.get_edge_for_port(self.indexed.device_id, port_id)

    @staticmethod
    def _vertex_id_from(port: InspectPortStatus) -> str | None:
        vertex_info = port.vertexInfo
        if vertex_info is None:
            return None
        if isinstance(vertex_info, InspectApiSingleVertexInfo):
            return vertex_info.id
        if isinstance(vertex_info, dict):
            vertex_type = vertex_info.get("type")
            if vertex_type == "single":
                single = vertex_info.get("id")
                return single if isinstance(single, str) else None
            if vertex_type == "double":
                for key in ("in", "out"):
                    side = vertex_info.get(key)
                    if isinstance(side, dict) and isinstance(side.get("id"), str):
                        return side["id"]
        else:
            for candidate in (getattr(vertex_info, "out", None), getattr(vertex_info, "in_", None)):
                if candidate is not None and candidate.id:
                    return candidate.id
        return None
