from __future__ import annotations

from typing import TYPE_CHECKING, Any

from videoipath_automation_tool.apps.inspect.model.collector import (
    InspectApiDoubleVertexInfo,
    InspectApiSingleVertexInfo,
)
from videoipath_automation_tool.apps.inspect.model.common import (
    InspectApiStatusSummary,
    InspectFrozenModel,
    InspectVertexKind,
    InspectVertexType,
)

if TYPE_CHECKING:
    from videoipath_automation_tool.apps.inspect.domain.device import InspectDevice
    from videoipath_automation_tool.apps.inspect.domain.edge import InspectEdge
    from videoipath_automation_tool.apps.inspect.model.actions import (
        InspectApiLookupVertexResponseData,
        InspectApiVertexControlProps,
        InspectApiVertexEditForm,
        InspectApiVertexTypeFields,
    )
from videoipath_automation_tool.apps.inspect.snapshot import (
    InspectSnapshot,
    _IndexedPort,
    _port_id_from_status,
    _vertex_ids_from_status,
)


class InspectPort(InspectFrozenModel):
    snapshot: InspectSnapshot
    indexed: _IndexedPort

    @property
    def id(self) -> str | None:
        return _port_id_from_status(self.indexed.port)

    @property
    def label(self) -> str | None:
        """The label the UI shows: the manual override (``descriptor.label``), falling back to the
        device-reported factory label."""
        return self.indexed.port.effective_label

    @property
    def factory_label(self) -> str | None:
        """The device-reported (factory) port label, even when a manual override is set."""
        return self.indexed.port.label

    @property
    def description(self) -> str | None:
        return self.indexed.port.effective_description

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
    def vertex_info(self) -> InspectApiSingleVertexInfo | InspectApiDoubleVertexInfo | None:
        """The port's raw (typed) ``vertexInfo`` from the collector."""
        return self.indexed.port.parsed_vertex_info

    @property
    def vertex_type(self) -> InspectVertexType | str | None:
        """Vertex direction: ``"In"`` / ``"Out"`` / ``"Internal"`` / …; ``"BiDirectional"`` when the
        port carries a double (in+out) vertexInfo."""
        info = self.vertex_info
        if info is None:
            return None
        if isinstance(info, InspectApiDoubleVertexInfo):
            return "BiDirectional"
        return info.vertexType

    @property
    def is_bidirectional(self) -> bool | None:
        info = self.vertex_info
        return isinstance(info, InspectApiDoubleVertexInfo) if info is not None else None

    @property
    def is_active(self) -> bool | None:
        return self._vertex_flag("isActive")

    @property
    def is_controlled(self) -> bool | None:
        return self._vertex_flag("isControlled")

    @property
    def is_endpoint(self) -> bool | None:
        """Whether the vertex is usable as a service endpoint ("use as endpoint" in the UI)."""
        return self._vertex_flag("isEndpoint")

    @property
    def vertex_id(self) -> str | None:
        vertex_ids = self.vertex_ids
        return vertex_ids[0] if vertex_ids else None

    @property
    def vertex_ids(self) -> tuple[str, ...]:
        """All vertex ids of this port: one for a single vertex, (out, in) for a bidirectional."""
        return _vertex_ids_from_status(self.indexed.port)

    @property
    def vertex_kind(self) -> InspectVertexKind | str | None:
        """Vertex kind: ``"generic"`` / ``"ip"`` / ``"codec"`` / ``"router"`` — from the vertex edit
        form's ``typeFields.type`` (triggers a lazy vertex lookup on first access)."""
        type_fields = self.type_fields
        return type_fields.type if type_fields is not None else None

    @property
    def type_fields(self) -> InspectApiVertexTypeFields | None:
        form = self._edit_form()
        return form.typeFields if form else None

    @property
    def sips_mode(self) -> str | None:
        form = self._edit_form()
        return form.sipsMode if form else None

    @property
    def control_props(self) -> InspectApiVertexControlProps | None:
        form = self._edit_form()
        return form.controlProps if form else None

    @property
    def extra_alert_filters(self) -> list[Any]:
        form = self._edit_form()
        return list(form.extraAlertFilters) if form else []

    @property
    def custom(self) -> dict[str, Any]:
        form = self._edit_form()
        return dict(form.custom) if form else {}

    @property
    def custom_schemas(self) -> dict[str, Any]:
        lookup = self._vertex_lookup()
        return dict(lookup.customSchemas) if lookup else {}

    @property
    def queueable(self) -> bool | None:
        form = self._edit_form()
        return form.queueable if form else None

    @property
    def destination_monitor_leader(self) -> bool | None:
        form = self._edit_form()
        return form.destinationMonitorLeader if form else None

    @property
    def park_port(self) -> int | None:
        """Park port (router vertices): ``typeFields.parkPort`` from the vertex edit form."""
        type_fields = self.type_fields
        return type_fields.parkPort if type_fields is not None else None

    @property
    def edge(self) -> InspectEdge | None:
        port_id = self.id
        if not port_id:
            return None
        return self.snapshot.get_edge_for_port(self.indexed.device_id, port_id)

    def _vertex_lookup(self) -> InspectApiLookupVertexResponseData | None:
        vertex_id = self.vertex_id
        if not vertex_id:
            return None
        return self.snapshot.get_vertex_details(vertex_id)

    def _edit_form(self) -> InspectApiVertexEditForm | None:
        lookup = self._vertex_lookup()
        return lookup.fields if lookup else None

    def _vertex_flag(self, name: str) -> bool | None:
        """Resolve a ``vertexInfo.fields`` flag; for double vertices: True if either side is True,
        False only if all sides are known False, else None."""
        info = self.vertex_info
        if info is None:
            return None
        sides = (info,) if isinstance(info, InspectApiSingleVertexInfo) else (info.out, info.in_)
        values = [
            getattr(side.fields, name) if side is not None and side.fields is not None else None for side in sides
        ]
        if any(value is True for value in values):
            return True
        if values and all(value is False for value in values):
            return False
        return None
