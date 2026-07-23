from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping, Self

from pydantic import Field, model_validator

from videoipath_automation_tool.apps.inspect.model.collector import (
    InspectApiDoubleVertexInfo,
    InspectApiSingleVertexInfo,
)
from videoipath_automation_tool.apps.inspect.model.common import InspectFrozenModel
from videoipath_automation_tool.apps.inspect.model.virtual import (
    InspectApiVirtualPortFromTemplate,
    InspectApiVirtualTemplateItem,
)
from videoipath_automation_tool.apps.inspect.snapshot import (
    InspectSnapshot,
    _IndexedPort,
    _port_id_from_status,
)

if TYPE_CHECKING:
    from videoipath_automation_tool.apps.inspect.domain.device import InspectDevice
    from videoipath_automation_tool.apps.inspect.domain.edge import InspectEdge
    from videoipath_automation_tool.apps.inspect.domain.module import InspectModule
    from videoipath_automation_tool.apps.inspect.domain.vertex import InspectVertex
    from videoipath_automation_tool.apps.inspect.model.common import InspectApiStatusSummary


class PortFromTemplate(InspectFrozenModel):
    """One port (or set of ports) instantiated from a port template (virtual-device create)."""

    template_id: str
    count: int = 1

    @model_validator(mode="after")
    def _validate_count(self) -> Self:
        if not self.template_id:
            raise ValueError("template_id must not be empty.")
        if self.count < 1:
            raise ValueError("count must be at least 1.")
        return self

    def to_wire(self) -> InspectApiVirtualPortFromTemplate:
        return InspectApiVirtualPortFromTemplate(templateId=self.template_id, count=self.count)


class InspectPortTemplate(InspectFrozenModel):
    """A port template (UI term; API: virtual template)."""

    id: str
    label: str
    kind: str | None = None
    direction: str | None = None
    codec_format: str | None = None
    vertex: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_wire(cls, wire: InspectApiVirtualTemplateItem) -> InspectPortTemplate:
        vertex = wire.vertex.model_dump(mode="json", exclude_none=False)
        return cls(
            id=wire.id,
            label=wire.label,
            kind=wire.vertex.type,
            direction=wire.vertex.vertexType,
            codec_format=wire.vertex.codecFormat,
            vertex=vertex,
        )


class InspectPort(InspectFrozenModel):
    """A port (the Inspect UI's "Module" edit modal): a lean container that owns one or more vertices.

    Its own editable attributes are ``label``, ``description`` and ``tags``; ``id``, ``status`` and
    ``factory_label`` are read-only. Navigate to the owning module via :attr:`module` (use
    ``port.module.id``). All vertex-specific configuration (direction, active/controlled/endpoint,
    IP/codec fields, SIPS, control, …) lives on the vertices reachable via :attr:`vertex_out` /
    :attr:`vertex_in`.
    """

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
    def status(self) -> InspectApiStatusSummary | None:
        return self.indexed.port.status

    @property
    def tags(self) -> list[str]:
        """Tags assigned to this port (as ``Category~~name`` ids). Assign them with
        ``app.inspect.update_vertex(v.id, tags=[...])`` for a vertex ``v`` from
        :attr:`vertex_out` / :attr:`vertex_in`."""
        return self.indexed.port.assigned_tags

    @property
    def device(self) -> InspectDevice | None:
        return self.snapshot.get_device_by_id(self.indexed.device_id)

    @property
    def module(self) -> InspectModule | None:
        """The module / slot this port belongs to."""
        module_id = self.indexed.module_id
        if module_id is None:
            return None
        return self.snapshot.get_module(self.indexed.device_id, module_id)

    @property
    def is_bidirectional(self) -> bool:
        """True when this port carries a ``double`` ``vertexInfo`` (separate out and in vertices)."""
        return isinstance(self.indexed.port.parsed_vertex_info, InspectApiDoubleVertexInfo)

    @property
    def vertex_out(self) -> InspectVertex | None:
        """The ``Out`` vertex, if this port has one; ``None`` otherwise."""
        return self._vertex_by_type("Out")

    @property
    def vertex_in(self) -> InspectVertex | None:
        """The ``In`` vertex, if this port has one; ``None`` otherwise."""
        return self._vertex_by_type("In")

    @property
    def edges(self) -> list[InspectEdge]:
        """The edges incident on this port. The Inspect read view (``externalEdgesByDeviceKey``) keys
        edge endpoints by *port* — with a UUID edge id and only a direction hint in the endpoint label
        — so edges are exposed at the port level here, not per vertex."""
        port_id = self.id
        if not port_id:
            return []
        return self.snapshot.get_edges_for_port(self.indexed.device_id, port_id)

    def _vertex_by_type(self, vertex_type: str) -> InspectVertex | None:
        for vid, side in self._vertex_sides():
            if side.vertexType == vertex_type:
                return self.snapshot.get_vertex(vid, vertex_info=side, port_factory_label=self.factory_label)
        return None

    def _vertices(self) -> list[InspectVertex]:
        """All typed vertex views this port carries (including Internal/Undecided). Prefer
        :attr:`vertex_out` / :attr:`vertex_in` for the public API."""
        return [
            self.snapshot.get_vertex(vid, vertex_info=side, port_factory_label=self.factory_label)
            for vid, side in self._vertex_sides()
        ]

    def _vertex_sides(self) -> list[tuple[str, InspectApiSingleVertexInfo]]:
        """(vertex id, its offline ``vertexInfo`` side) for each vertex the port carries."""
        info = self.indexed.port.parsed_vertex_info
        if info is None:
            return []
        if isinstance(info, InspectApiSingleVertexInfo):
            return [(info.id, info)] if info.id else []
        return [(side.id, side) for side in (info.out, info.in_) if side is not None and side.id]

    def _offline_vertices(self) -> list[InspectVertex]:
        """Base vertex views built purely from the offline ``vertexInfo`` (no lookup). Used for
        offline filtering; direction/active/controlled/endpoint resolve without a fetch."""
        from videoipath_automation_tool.apps.inspect.domain.vertex import InspectVertex

        return [InspectVertex(snapshot=self.snapshot, id=vid, vertex_info=side) for vid, side in self._vertex_sides()]


def _ports_to_count_by_template(
    ports: Mapping[str, int] | list[PortFromTemplate],
) -> dict[str, int]:
    """Normalize port specs to the ``countByVertexTemplate`` wire map."""
    result: dict[str, int]
    if isinstance(ports, Mapping):
        result = {template_id: count for template_id, count in ports.items()}
    else:
        result = {}
        for port in ports:
            result[port.template_id] = result.get(port.template_id, 0) + port.count
    for template_id, count in result.items():
        if not template_id:
            raise ValueError("template_id must not be empty.")
        if count < 1:
            raise ValueError(f"count for template {template_id!r} must be at least 1.")
    return result


__all__ = ["InspectPort", "InspectPortTemplate", "PortFromTemplate"]
