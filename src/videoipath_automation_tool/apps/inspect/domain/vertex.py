"""Typed vertex domain views ([ADR-0007]).

A vertex is one directed endpoint of a port (a port carries one vertex, or an ``out``/``in`` pair).
``InspectVertex`` is the base read view over the vertex edit form (``lookupInspectVertexById``);
concrete kinds subclass it to expose their kind-specific attributes:

- ``InspectIpVertex``    — IP config (address, netmask, VLAN, VRF, config-support flags).
- ``InspectCodecVertex`` — codec config (``typeFields.generic`` / ``typeFields.specific``).
- ``InspectGenericVertex`` — base fields only.
- ``InspectResourceTransformVertex`` — base fields only (kind-specific fields await a live sample).

Router vertices are surfaced as the base ``InspectVertex`` (their ``park_port`` lives on the base).
Instances are built by :meth:`InspectSnapshot.get_vertex`, which picks the subclass from the edit
form's ``typeFields.type``. Edits go through ``app.inspect.update_vertex(vertex.id, ...)``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from videoipath_automation_tool.apps.inspect.model.collector import InspectApiSingleVertexInfo
from videoipath_automation_tool.apps.inspect.model.common import (
    InspectFrozenModel,
    InspectVertexKind,
    InspectVertexType,
)
from videoipath_automation_tool.apps.inspect.snapshot import InspectSnapshot

if TYPE_CHECKING:
    from videoipath_automation_tool.apps.inspect.model.actions import (
        InspectApiCodecGeneric,
        InspectApiCodecSpecific,
        InspectApiLookupVertexResponseData,
        InspectApiVertexControlProps,
        InspectApiVertexEditForm,
        InspectApiVertexTypeFields,
    )


class InspectVertex(InspectFrozenModel):
    """Base read view of a single vertex.

    Direction and the ``isActive`` / ``isControlled`` / ``isEndpoint`` status flags resolve offline
    from the owning port's ``vertexInfo`` (``vertex_info``, set when built via a port); the config
    fields (label, tags, SIPS, control, IP/codec, …) resolve live from the snapshot's cached edit
    form (``lookupInspectVertexById``)."""

    snapshot: InspectSnapshot
    id: str
    vertex_info: InspectApiSingleVertexInfo | None = None

    @property
    def vertex_type(self) -> InspectVertexType | str | None:
        """Vertex direction: ``"In"`` / ``"Out"`` / ``"Internal"`` / …. Offline from the port's
        ``vertexInfo``; falls back to the lookup response when built without a port."""
        if self.vertex_info is not None:
            return self.vertex_info.vertexType
        lookup = self._lookup()
        return lookup.vertexType if lookup else None

    @property
    def is_active(self) -> bool | None:
        return self._info_flag("isActive")

    @property
    def is_controlled(self) -> bool | None:
        return self._info_flag("isControlled")

    @property
    def is_endpoint(self) -> bool | None:
        """Whether the vertex is usable as a service endpoint ("Use as endpoint" in the UI)."""
        return self._info_flag("isEndpoint")

    @property
    def label(self) -> str | None:
        form = self._form()
        return form.label if form else None

    @property
    def description(self) -> str | None:
        form = self._form()
        return form.desc if form else None

    @property
    def tags(self) -> list[str]:
        """Tags assigned to this vertex (``localAssignedTags``). Assign with
        ``app.inspect.update_vertex(vertex.id, tags=[...])``."""
        form = self._form()
        return list(form.localAssignedTags) if form else []

    @property
    def active(self) -> bool | None:
        form = self._form()
        return form.active if form else None

    @property
    def use_as_endpoint(self) -> bool | None:
        """Whether the vertex is usable as a service endpoint ("Use as endpoint" in the UI)."""
        form = self._form()
        return form.useAsEndpoint if form else None

    @property
    def sips_mode(self) -> str | None:
        form = self._form()
        return form.sipsMode if form else None

    @property
    def control_props(self) -> InspectApiVertexControlProps | None:
        form = self._form()
        return form.controlProps if form else None

    @property
    def extra_alert_filters(self) -> list[Any]:
        form = self._form()
        return list(form.extraAlertFilters) if form else []

    @property
    def custom(self) -> dict[str, Any]:
        form = self._form()
        return dict(form.custom) if form else {}

    @property
    def queueable(self) -> bool | None:
        form = self._form()
        return form.queueable if form else None

    @property
    def destination_monitor_leader(self) -> bool | None:
        form = self._form()
        return form.destinationMonitorLeader if form else None

    @property
    def vertex_kind(self) -> InspectVertexKind | str | None:
        """Vertex kind from ``typeFields.type``: ``"generic"`` / ``"ip"`` / ``"codec"`` / ``"router"``."""
        type_fields = self.type_fields
        return type_fields.type if type_fields is not None else None

    @property
    def custom_schemas(self) -> dict[str, Any]:
        lookup = self._lookup()
        return dict(lookup.customSchemas) if lookup else {}

    @property
    def is_virtual(self) -> bool | None:
        lookup = self._lookup()
        return lookup.isVirtual if lookup else None

    @property
    def park_port(self) -> int | None:
        """Park port (router vertices): ``typeFields.parkPort``."""
        type_fields = self.type_fields
        return type_fields.parkPort if type_fields is not None else None

    @property
    def type_fields(self) -> InspectApiVertexTypeFields | None:
        form = self._form()
        return form.typeFields if form else None

    def _info_flag(self, name: str) -> bool | None:
        info = self.vertex_info
        if info is None or info.fields is None:
            return None
        return getattr(info.fields, name, None)

    def _lookup(self) -> InspectApiLookupVertexResponseData | None:
        return self.snapshot.get_vertex_details(self.id)

    def _form(self) -> InspectApiVertexEditForm | None:
        lookup = self._lookup()
        return lookup.fields if lookup else None


class InspectGenericVertex(InspectVertex):
    """A generic vertex (``typeFields.type == "generic"``); exposes the base fields only."""


class InspectIpVertex(InspectVertex):
    """An IP vertex (``typeFields.type == "ip"``): IP addressing and config-support flags."""

    @property
    def ip_address(self) -> str | None:
        return self._tf("ipAddress")

    @property
    def ip_netmask(self) -> str | None:
        return self._tf("ipNetmask")

    @property
    def public(self) -> bool | None:
        return self._tf("public")

    @property
    def vlan_id(self) -> str | None:
        return self._tf("vlanId")

    @property
    def vrf_id(self) -> str | None:
        return self._tf("vrfId")

    @property
    def supports_cpipe(self) -> bool | None:
        return self._tf("supportsCpipeCfg")

    @property
    def supports_igmp(self) -> bool | None:
        return self._tf("supportsIgmpCfg")

    @property
    def supports_mac_forwarding(self) -> bool | None:
        return self._tf("supportsMacForwardingCfg")

    @property
    def supports_nso(self) -> bool | None:
        return self._tf("supportsNsoCfg")

    @property
    def supports_openflow(self) -> bool | None:
        return self._tf("supportsOpenflowCfg")

    @property
    def supports_static_igmp(self) -> bool | None:
        return self._tf("supportsStaticIgmpCfg")

    @property
    def supports_vlan(self) -> bool | None:
        return self._tf("supportsVlanCfg")

    @property
    def supports_vpls(self) -> bool | None:
        return self._tf("supportsVplsCfg")

    def _tf(self, name: str) -> Any:
        type_fields = self.type_fields
        return getattr(type_fields, name, None) if type_fields is not None else None


class InspectCodecVertex(InspectVertex):
    """A codec vertex (``typeFields.type == "codec"``): codec format and source/destination config,
    read from the ``typeFields.generic`` / ``typeFields.specific`` blocks (verified 2025.4.9)."""

    @property
    def codec_format(self) -> str | None:
        generic = self.generic
        return generic.codecFormat if generic else None

    @property
    def public(self) -> bool | None:
        generic = self.generic
        return generic.public if generic else None

    @property
    def multiplicity(self) -> int | None:
        generic = self.generic
        return generic.multiplicity if generic else None

    @property
    def extra_formats(self) -> list[Any]:
        generic = self.generic
        return list(generic.extraFormats) if generic else []

    @property
    def main_src_info(self) -> dict[str, Any] | None:
        generic = self.generic
        return generic.mainSrcInfo if generic else None

    @property
    def main_dst_info(self) -> dict[str, Any] | None:
        generic = self.generic
        return generic.mainDstInfo if generic else None

    @property
    def spare_src_info(self) -> dict[str, Any] | None:
        generic = self.generic
        return generic.spareSrcInfo if generic else None

    @property
    def spare_dst_info(self) -> dict[str, Any] | None:
        generic = self.generic
        return generic.spareDstInfo if generic else None

    @property
    def is_igmp_source(self) -> bool | None:
        specific = self.specific
        return specific.isIgmpSource if specific else None

    @property
    def sdp_support(self) -> bool | None:
        specific = self.specific
        return specific.sdpSupport if specific else None

    @property
    def generic(self) -> InspectApiCodecGeneric | None:
        """The typed ``typeFields.generic`` block (parsed from the lossless-preserved extra)."""
        from videoipath_automation_tool.apps.inspect.model.actions import InspectApiCodecGeneric

        raw = self._type_fields_extra("generic")
        return InspectApiCodecGeneric.model_validate(raw) if isinstance(raw, dict) else None

    @property
    def specific(self) -> InspectApiCodecSpecific | None:
        """The typed ``typeFields.specific`` block (parsed from the lossless-preserved extra)."""
        from videoipath_automation_tool.apps.inspect.model.actions import InspectApiCodecSpecific

        raw = self._type_fields_extra("specific")
        return InspectApiCodecSpecific.model_validate(raw) if isinstance(raw, dict) else None

    def _type_fields_extra(self, name: str) -> Any:
        type_fields = self.type_fields
        return getattr(type_fields, name, None) if type_fields is not None else None


class InspectResourceTransformVertex(InspectVertex):
    """A resource-transform vertex. Exposes the base fields; kind-specific attributes await a live
    sample (none present on the verified 2025.4.9 server)."""


def build_vertex(
    snapshot: InspectSnapshot,
    vertex_id: str,
    kind: InspectVertexKind | str | None,
    vertex_info: InspectApiSingleVertexInfo | None = None,
) -> InspectVertex:
    """Construct the typed vertex view for ``vertex_id`` from its ``typeFields.type`` kind (falls
    back to the base :class:`InspectVertex` when the kind is unknown, e.g. no fetcher)."""
    cls = _VERTEX_CLASS_BY_KIND.get(kind, InspectVertex)
    return cls(snapshot=snapshot, id=vertex_id, vertex_info=vertex_info)


_VERTEX_CLASS_BY_KIND: dict[str | None, type[InspectVertex]] = {
    "ip": InspectIpVertex,
    "codec": InspectCodecVertex,
    "generic": InspectGenericVertex,
    "resourceTransform": InspectResourceTransformVertex,
    "nGraphResourceTransform": InspectResourceTransformVertex,
}


__all__ = [
    "InspectVertex",
    "InspectGenericVertex",
    "InspectIpVertex",
    "InspectCodecVertex",
    "InspectResourceTransformVertex",
    "build_vertex",
]
