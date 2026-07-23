from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal, Self

from pydantic import Field

from videoipath_automation_tool.apps.inspect.domain.module import VirtualModuleSpec
from videoipath_automation_tool.apps.inspect.domain.port import PortFromTemplate
from videoipath_automation_tool.apps.inspect.model.common import (
    InspectApiStatusSummary,
    InspectEditableModel,
    InspectIconSize,
    InspectIconType,
    InspectInternalModel,
    InspectSdpStrategy,
    InspectSeverity,
    InspectVertexKind,
    InspectVertexType,
    format_repr,
)
from videoipath_automation_tool.apps.inspect.model.virtual import InspectApiVirtualDeviceWriteBody
from videoipath_automation_tool.apps.inspect.snapshot import InspectSnapshot
from videoipath_automation_tool.validators.virtual_device_id import is_virtual_device_id

if TYPE_CHECKING:
    from videoipath_automation_tool.apps.inspect.domain.alarm import InspectAlarm
    from videoipath_automation_tool.apps.inspect.domain.edge import InspectEdge
    from videoipath_automation_tool.apps.inspect.domain.module import InspectModule
    from videoipath_automation_tool.apps.inspect.domain.port import InspectPort
    from videoipath_automation_tool.apps.inspect.domain.service import InspectService
    from videoipath_automation_tool.apps.inspect.domain.vertex import InspectVertex
    from videoipath_automation_tool.apps.inspect.snapshot import _DeviceRecord


class InspectDevice(InspectEditableModel):
    """A topology device/node. Skeleton fields (id, label, coordinates, status, sync, tags) are
    available immediately; ``ports`` and ``services`` lazily hydrate from the server on first
    access ([ADR-0007]). The record is resolved live from the snapshot, so a held reference sees
    hydrated/refreshed data transparently.

    Editable attributes use property setters that stage pending intents on the snapshot
    (read-your-writes). Flush with ``app.inspect.update(device)`` or ``tx.update(device)``
    inside a transaction.
    """

    snapshot: InspectSnapshot
    id: str

    @property
    def _edit_kind(self) -> Literal["device"]:
        return "device"

    @property
    def label(self) -> str | None:
        return self._staged_or("descriptor.label", lambda: self._record().label)

    @label.setter
    def label(self, value: str) -> None:
        self._stage("descriptor.label", value)

    @property
    def description(self) -> str | None:
        return self._staged_or(
            "descriptor.desc",
            lambda: self._record().node.effective_description,
        )

    @description.setter
    def description(self, value: str) -> None:
        self._stage("descriptor.desc", value)

    @property
    def factory_label(self) -> str | None:
        """Device-reported factory label (``fDescriptor.label`` / collector ``label``)."""
        node = self._record().node
        return node.label

    @property
    def pid(self) -> str | None:
        return self._record().pid

    @property
    def is_virtual(self) -> bool | None:
        """Whether this is a topology virtual device (``virtual.N``).

        ``virtual.N`` ids are always virtual; otherwise the collector ``meta.isVirtual`` flag is
        used when present.
        """
        if is_virtual_device_id(self.id):
            return True
        meta = self._record().node.meta
        return meta.isVirtual if meta is not None else None

    @property
    def icon_type(self) -> InspectIconType | str | None:
        return self._staged_or("iconType", lambda: self._meta_get("iconType"))

    @icon_type.setter
    def icon_type(self, value: InspectIconType | str) -> None:
        self._stage("iconType", value)

    @property
    def icon_size(self) -> InspectIconSize | str | None:
        """Device icon size ("Device icon size" in the UI): ``"auto"`` / ``"large"`` / ``"medium"`` /
        ``"small"``."""
        return self._staged_or("iconSize", lambda: self._meta_get("iconSize"))

    @icon_size.setter
    def icon_size(self, value: InspectIconSize | str) -> None:
        self._stage("iconSize", value)

    @property
    def sdp_strategy(self) -> InspectSdpStrategy | str | None:
        """SDP polling strategy ("SDP polling strategy" in the UI): ``"always"`` (Continuous) /
        ``"once"`` (Fetch and Confirm) / ``"video"`` (Continuous Video, Confirm Others)."""
        return self._staged_or("sdpStrategy", lambda: self._meta_get("sdpStrategy"))

    @sdp_strategy.setter
    def sdp_strategy(self, value: InspectSdpStrategy | str) -> None:
        self._stage("sdpStrategy", value)

    @property
    def site_id(self) -> str | None:
        """The id of the site this device is located at ("Site ID" in the UI)."""
        return self._staged_or("siteId", lambda: self._meta_get("siteId"))

    @site_id.setter
    def site_id(self, value: str) -> None:
        self._stage("siteId", value)

    @property
    def status(self) -> InspectApiStatusSummary | None:
        return self._record().node.status

    @property
    def sync_severity(self) -> InspectSeverity | int | str | None:
        return self._record().node.syncSeverity

    @property
    def alarms(self) -> list[InspectAlarm]:
        """Active alarms correlated to this device (worst severity first)."""
        return self.snapshot.get_alarms_for_device(self.id)

    @property
    def status_message(self) -> str | None:
        """Message of the worst active alarm on this device, if any."""
        alarms = self.alarms
        return alarms[0].message if alarms else None

    @property
    def tags(self) -> list[str]:
        return self._staged_or("tags", lambda: list(self._record().node.tags), adapt=list)

    @tags.setter
    def tags(self, value: list[str] | tuple[str, ...]) -> None:
        self._stage("tags", list(value))

    @property
    def local_assigned_tags(self) -> list[str]:
        """Device ``localAssignedTags`` (distinct from collector ``tags`` when both are present)."""
        return self._staged_or("localAssignedTags", lambda: [], adapt=list)

    @local_assigned_tags.setter
    def local_assigned_tags(self, value: list[str]) -> None:
        self._stage("localAssignedTags", list(value))

    @property
    def coordinates(self) -> dict[str, float | int | str | None] | None:
        return self._staged_or(
            "coordinates",
            lambda: self._record().node.coordinates,
            adapt=lambda value: dict(value) if value is not None else None,
        )

    @coordinates.setter
    def coordinates(self, value: dict[str, float | int] | None) -> None:
        self._stage("coordinates", dict(value) if value is not None else None)

    @property
    def is_hydrated(self) -> bool:
        return self.snapshot.is_device_hydrated(self.id)

    @property
    def fetched_at(self) -> datetime | None:
        return self.snapshot.fetched_at(self.id)

    @property
    def modules(self) -> list[InspectModule]:
        """The device's modules / slots, each owning many ports/vertices."""
        return self.snapshot.get_modules_for_device(self.id)

    def get_module(self, module_id: str) -> InspectModule | None:
        return self.snapshot.get_module(self.id, module_id)

    @property
    def ports(self) -> list[InspectPort]:
        """All port rows across the device's modules (flattened). Use :attr:`modules` for the
        module → port grouping."""
        return self.snapshot.get_ports_for_device(self.id)

    @property
    def codec_vertices(self) -> list[InspectVertex]:
        """All codec vertices across this device's ports (hydrates + batches vertex lookups)."""
        return self._vertices_of_kind("codec")

    @property
    def ip_vertices(self) -> list[InspectVertex]:
        """All IP vertices across this device's ports (hydrates + batches vertex lookups)."""
        return self._vertices_of_kind("ip")

    @property
    def generic_vertices(self) -> list[InspectVertex]:
        """All generic vertices across this device's ports (hydrates + batches vertex lookups)."""
        return self._vertices_of_kind("generic")

    def find_vertex_by_factory_label(
        self,
        label: str,
        *,
        kind: InspectVertexKind | str | None = None,
        vertex_type: InspectVertexType | str | None = None,
    ) -> InspectVertex | None:
        """First vertex whose owning port's factory label equals ``label`` (optionally filtered)."""
        for vertex in self._all_vertices():
            if vertex.factory_label != label:
                continue
            if kind is not None and vertex.vertex_kind != kind:
                continue
            if vertex_type is not None and vertex.vertex_type != vertex_type:
                continue
            return vertex
        return None

    def get_vertices_by_module_label(
        self,
        module_label: str,
        *,
        kind: InspectVertexKind | str | None = None,
    ) -> list[InspectVertex]:
        """Vertices belonging to modules whose label equals ``module_label`` (e.g. ``Slot 3``)."""
        module_ids = {m.id for m in self.modules if m.label == module_label}
        if not module_ids:
            return []
        result: list[InspectVertex] = []
        for port in self.ports:
            if port.indexed.module_id not in module_ids:
                continue
            for vertex in port._vertices():
                if kind is not None and vertex.vertex_kind != kind:
                    continue
                result.append(vertex)
        return result

    def get_vertex_by_id(self, vertex_id: str) -> InspectVertex | None:
        """A vertex of this device by id, or ``None`` if it is not on any port."""
        for vertex in self._all_vertices():
            if vertex.id == vertex_id:
                return vertex
        if vertex_id.startswith(self.id + ".") or (
            self.id.startswith("virtual.") and vertex_id.startswith(self.id + ".")
        ):
            return self.snapshot.get_vertex(vertex_id)
        return None

    def filter_ports(
        self,
        *,
        module_id: str | None = None,
        vertex_type: InspectVertexType | str | None = None,
        kind: InspectVertexKind | str | None = None,
        active: bool | None = None,
        controlled: bool | None = None,
        endpoint: bool | None = None,
    ) -> list[InspectPort]:
        """Filter this device's ports by their vertices' attributes.

        ``vertex_type`` is the port-level direction (``"BiDirectional"`` for a two-vertex port, else
        the single vertex's direction); ``active`` / ``controlled`` / ``endpoint`` aggregate the
        port's vertices (True if any vertex is True, False only if all are known False). These are
        evaluated offline from the already-hydrated ``vertexInfo``. ``kind`` (``"generic"`` / ``"ip"``
        / ``"codec"`` / ``"router"``) requires the vertex edit form: uncached vertices are resolved
        with a single batched ``lookupInspectVertexByIds`` call. A port whose value for an explicit
        filter is unknown never matches.
        """
        result: list[InspectPort] = []
        for port in self.ports:
            if module_id is not None and port.indexed.module_id != module_id:
                continue
            vertices = port._offline_vertices()
            if vertex_type is not None and _port_direction(vertices) != vertex_type:
                continue
            if active is not None and _aggregate_flag(vertices, "is_active") is not active:
                continue
            if controlled is not None and _aggregate_flag(vertices, "is_controlled") is not controlled:
                continue
            if endpoint is not None and _aggregate_flag(vertices, "is_endpoint") is not endpoint:
                continue
            result.append(port)

        if kind is not None:
            first_sides = [sides[0] for p in result if (sides := p._vertex_sides())]
            self.snapshot.get_vertex_details_many([vid for vid, _ in first_sides])
            result = [
                p
                for p in result
                if (sides := p._vertex_sides())
                and (v := self.snapshot.get_vertex(sides[0][0], vertex_info=sides[0][1])) is not None
                and v.vertex_kind == kind
            ]
        return result

    @property
    def edges(self) -> list[InspectEdge]:
        return self.snapshot.get_edges_for_device(self.id)

    @property
    def services(self) -> list[InspectService]:
        return self.snapshot.get_services_for_device(self.id)

    @property
    def linked_devices(self) -> list[InspectDevice]:
        return self.snapshot.get_linked_devices(self.id)

    def __repr__(self) -> str:
        return format_repr(
            self,
            id=self.id,
            label=lambda: self._record().label,
            virtual=True if is_virtual_device_id(self.id) else None,
        )

    __str__ = __repr__

    def _record(self) -> "_DeviceRecord":
        record = self.snapshot.get_device_record(self.id)
        if record is None:
            raise KeyError(f"Device '{self.id}' is no longer present in the snapshot.")
        return record

    def _meta_get(self, attr: str, default: Any = None) -> Any:
        meta = self._record().node.meta
        return getattr(meta, attr, default) if meta is not None else default

    def _all_vertices(self) -> list[InspectVertex]:
        sides = [side for port in self.ports for side in port._vertex_sides()]
        self.snapshot.get_vertex_details_many([vid for vid, _ in sides])
        result: list[InspectVertex] = []
        for port in self.ports:
            result.extend(port._vertices())
        return result

    def _vertices_of_kind(self, kind: str) -> list[InspectVertex]:
        return [v for v in self._all_vertices() if v.vertex_kind == kind]


class VirtualDeviceSpec(InspectInternalModel):
    """Declarative definition of a virtual device, matching the Create Virtual Devices dialog.

    Mutable so fluent helpers (``add_module`` / ``add_port``) can mirror the UI workflow.
    """

    modules: list[VirtualModuleSpec] = Field(default_factory=lambda: [VirtualModuleSpec()])

    @classmethod
    def empty(cls) -> VirtualDeviceSpec:
        """One empty module, as in the UI default."""
        return cls(modules=[VirtualModuleSpec()])

    def add_module(self) -> Self:
        """Append an empty module (UI: + Add module)."""
        self.modules.append(VirtualModuleSpec())
        return self

    def add_port(self, template_id: str, count: int = 1, *, module_index: int = -1) -> Self:
        """Add a port from a template to a module (UI: Add port)."""
        if not self.modules:
            self.modules.append(VirtualModuleSpec())
        idx = module_index if module_index >= 0 else len(self.modules) + module_index
        if idx < 0 or idx >= len(self.modules):
            raise IndexError(f"module_index {module_index} is out of range for {len(self.modules)} module(s).")
        self.modules[idx].ports.append(PortFromTemplate(template_id=template_id, count=count))
        return self

    def to_wire(self) -> InspectApiVirtualDeviceWriteBody:
        return InspectApiVirtualDeviceWriteBody(modules=[module.to_wire() for module in self.modules])

    def __repr__(self) -> str:
        return format_repr(self, modules=len(self.modules))

    __str__ = __repr__

    @classmethod
    def from_ports(cls, *ports: PortFromTemplate | tuple[str, int] | str) -> VirtualDeviceSpec:
        """Build a single-module device from port specs."""
        resolved: list[PortFromTemplate] = []
        for port in ports:
            if isinstance(port, PortFromTemplate):
                resolved.append(port)
            elif isinstance(port, str):
                resolved.append(PortFromTemplate(template_id=port))
            else:
                template_id, count = port
                resolved.append(PortFromTemplate(template_id=template_id, count=count))
        return cls(modules=[VirtualModuleSpec(ports=resolved)])


# --- Internal ---


def _port_direction(vertices: list[InspectVertex]) -> str | None:
    """Port-level direction: ``"BiDirectional"`` for a two-vertex port, else the single vertex's
    direction (None for a port without vertices)."""
    if len(vertices) > 1:
        return "BiDirectional"
    return vertices[0].vertex_type if vertices else None


def _aggregate_flag(vertices: list[InspectVertex], attr: str) -> bool | None:
    """Aggregate a vertex boolean flag across a port: True if any vertex is True, False only if all
    are known False, else None (unknown)."""
    values = [getattr(vertex, attr) for vertex in vertices]
    if any(value is True for value in values):
        return True
    if values and all(value is False for value in values):
        return False
    return None


__all__ = ["InspectDevice", "VirtualDeviceSpec"]
