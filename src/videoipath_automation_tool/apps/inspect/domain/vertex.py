"""Typed vertex domain views ([ADR-0007]).

A vertex is one directed endpoint of a port (a port carries one vertex, or an ``out``/``in`` pair).
``InspectVertex`` is the base read/write view over the vertex edit form (``lookupInspectVertexById``);
concrete kinds subclass it to expose their kind-specific attributes:

- ``InspectIpVertex``    — IP config (address, netmask, VLAN, VRF, config-support flags).
- ``InspectCodecVertex`` — codec config (``typeFields.generic`` / ``typeFields.specific``).
- ``InspectGenericVertex`` — base fields only.
- ``InspectResourceTransformVertex`` — base fields only (kind-specific fields await a live sample).

Router vertices are surfaced as the base ``InspectVertex`` (their ``park_port`` lives on the base).
Instances are built by :meth:`InspectSnapshot.get_vertex`, which picks the subclass from the edit
form's ``typeFields.type``.

Editable attributes use property setters that stage pending wire-field intents on the snapshot
(read-your-writes). Flush with ``app.inspect.update(vertex)``, ``app.inspect.update(device)``,
or ``tx.update(...)`` inside a transaction.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any, Literal

from videoipath_automation_tool.apps.inspect.model.collector import InspectApiSingleVertexInfo
from videoipath_automation_tool.apps.inspect.model.common import (
    InspectEditableModel,
    InspectVertexKind,
    InspectVertexType,
    _STAGED_MISSING,
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


class InspectVertex(InspectEditableModel):
    """Base read/write view of a single vertex.

    Direction and the ``isActive`` / ``isControlled`` / ``isEndpoint`` status flags resolve offline
    from the owning port's ``vertexInfo`` (``vertex_info``, set when built via a port); the config
    fields resolve live from the snapshot's cached edit form, with pending setter edits taking
    precedence (read-your-writes)."""

    snapshot: InspectSnapshot
    id: str
    vertex_info: InspectApiSingleVertexInfo | None = None
    port_factory_label: str | None = None

    @property
    def _edit_kind(self) -> Literal["vertex"]:
        return "vertex"

    # --- Offline / identity ---

    @property
    def vertex_type(self) -> InspectVertexType | str | None:
        """Vertex direction: ``"In"`` / ``"Out"`` / ``"Internal"`` / …. Offline from the port's
        ``vertexInfo``; falls back to the lookup response when built without a port."""
        if self.vertex_info is not None:
            return self.vertex_info.vertexType
        lookup = self._lookup()
        return lookup.vertexType if lookup else None

    @property
    def factory_label(self) -> str | None:
        """Device-reported factory label of the owning port (set when built via a port)."""
        return self.port_factory_label

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

    # --- Base edit-form fields ---

    @property
    def label(self) -> str | None:
        return self._staged_or("label", lambda: self._form_get("label"))

    @label.setter
    def label(self, value: str) -> None:
        self._stage("label", value)

    @property
    def description(self) -> str | None:
        return self._staged_or("desc", lambda: self._form_get("desc"))

    @description.setter
    def description(self, value: str) -> None:
        self._stage("desc", value)

    @property
    def tags(self) -> list[str]:
        """Tags assigned to this vertex (``localAssignedTags``)."""
        return self._staged_or(
            "localAssignedTags",
            lambda: list(self._form_get("localAssignedTags") or []),
            adapt=list,
        )

    @tags.setter
    def tags(self, value: list[str]) -> None:
        self._stage("localAssignedTags", list(value))

    @property
    def form_tags(self) -> list[str]:
        """The vertex form's ``tags`` list (distinct from :attr:`tags` / ``localAssignedTags``)."""
        return self._staged_or("tags", lambda: list(self._form_get("tags") or []), adapt=list)

    @form_tags.setter
    def form_tags(self, value: list[str]) -> None:
        self._stage("tags", list(value))

    @property
    def active(self) -> bool | None:
        return self._staged_or("active", lambda: self._form_get("active"))

    @active.setter
    def active(self, value: bool) -> None:
        self._stage("active", value)

    @property
    def use_as_endpoint(self) -> bool | None:
        """Whether the vertex is usable as a service endpoint ("Use as endpoint" in the UI)."""
        return self._staged_or("useAsEndpoint", lambda: self._form_get("useAsEndpoint"))

    @use_as_endpoint.setter
    def use_as_endpoint(self, value: bool) -> None:
        self._stage("useAsEndpoint", value)

    @property
    def sips_mode(self) -> str | None:
        return self._staged_or("sipsMode", lambda: self._form_get("sipsMode"))

    @sips_mode.setter
    def sips_mode(self, value: str) -> None:
        self._stage("sipsMode", value)

    @property
    def control_props(self) -> InspectApiVertexControlProps | None:
        return self._staged_or("controlProps", lambda: self._form_get("controlProps"), adapt=self._as_control_props)

    @control_props.setter
    def control_props(self, value: Any) -> None:
        self._stage("controlProps", value)

    @property
    def control(self) -> str | None:
        """Best-effort ``control`` scalar (``"full"`` / ``"off"`` / ``"semi"``).

        The verified 2025.4.9 vertex edit form exposes ``controlProps`` rather than a ``control``
        scalar; this setter stages a top-level ``control`` intent (allowed by ``extra="allow"``)
        for servers that accept it. Prefer :attr:`control_props` when targeting the verified form.
        """
        return self._staged_or("control", lambda: self._form_get("control"))

    @control.setter
    def control(self, value: str) -> None:
        warnings.warn(
            "InspectVertex.control stages a best-effort top-level 'control' field; the verified "
            "2025.4.9 edit form exposes controlProps instead. Prefer control_props when possible.",
            UserWarning,
            stacklevel=2,
        )
        self._stage("control", value)

    @property
    def extra_alert_filters(self) -> list[Any]:
        return self._staged_or(
            "extraAlertFilters",
            lambda: list(self._form_get("extraAlertFilters") or []),
            adapt=list,
        )

    @extra_alert_filters.setter
    def extra_alert_filters(self, value: list[Any]) -> None:
        self._stage("extraAlertFilters", list(value))

    @property
    def custom(self) -> dict[str, Any]:
        return self._staged_or("custom", lambda: dict(self._form_get("custom") or {}), adapt=dict)

    @custom.setter
    def custom(self, value: dict[str, Any]) -> None:
        self._stage("custom", dict(value))

    @property
    def queueable(self) -> bool | None:
        return self._staged_or("queueable", lambda: self._form_get("queueable"))

    @queueable.setter
    def queueable(self, value: bool) -> None:
        self._stage("queueable", value)

    @property
    def destination_monitor_leader(self) -> bool | None:
        return self._staged_or(
            "destinationMonitorLeader",
            lambda: self._form_get("destinationMonitorLeader"),
        )

    @destination_monitor_leader.setter
    def destination_monitor_leader(self, value: bool) -> None:
        self._stage("destinationMonitorLeader", value)

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
        return self._staged_or(
            "typeFields.parkPort",
            lambda: self.type_fields.parkPort if self.type_fields is not None else None,
        )

    @park_port.setter
    def park_port(self, value: int) -> None:
        self._stage("typeFields.parkPort", value)

    @property
    def type_fields(self) -> InspectApiVertexTypeFields | None:
        return self._form_get("typeFields")

    # --- Internal ---

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

    def _form_get(self, attr: str, default: Any = None) -> Any:
        form = self._form()
        return getattr(form, attr, default) if form is not None else default

    @staticmethod
    def _as_control_props(value: Any) -> InspectApiVertexControlProps | None:
        from videoipath_automation_tool.apps.inspect.model.actions import InspectApiVertexControlProps

        if value is None or isinstance(value, InspectApiVertexControlProps):
            return value
        return InspectApiVertexControlProps.model_validate(value)


class InspectGenericVertex(InspectVertex):
    """A generic vertex (``typeFields.type == "generic"``); exposes the base fields only."""


class InspectIpVertex(InspectVertex):
    """An IP vertex (``typeFields.type == "ip"``): IP addressing and config-support flags."""

    @property
    def ip_address(self) -> str | None:
        return self._tf("ipAddress", "typeFields.ipAddress")

    @ip_address.setter
    def ip_address(self, value: str) -> None:
        self._stage("typeFields.ipAddress", value)

    @property
    def ip_netmask(self) -> str | None:
        return self._tf("ipNetmask", "typeFields.ipNetmask")

    @ip_netmask.setter
    def ip_netmask(self, value: str) -> None:
        self._stage("typeFields.ipNetmask", value)

    @property
    def public(self) -> bool | None:
        return self._tf("public", "typeFields.public")

    @public.setter
    def public(self, value: bool) -> None:
        self._stage("typeFields.public", value)

    @property
    def vlan_id(self) -> str | None:
        return self._tf("vlanId", "typeFields.vlanId")

    @vlan_id.setter
    def vlan_id(self, value: str) -> None:
        self._stage("typeFields.vlanId", value)

    @property
    def vrf_id(self) -> str | None:
        return self._tf("vrfId", "typeFields.vrfId")

    @vrf_id.setter
    def vrf_id(self, value: str) -> None:
        self._stage("typeFields.vrfId", value)

    @property
    def supports_cpipe(self) -> bool | None:
        return self._tf("supportsCpipeCfg", "typeFields.supportsCpipeCfg")

    @supports_cpipe.setter
    def supports_cpipe(self, value: bool) -> None:
        self._stage("typeFields.supportsCpipeCfg", value)

    @property
    def supports_igmp(self) -> bool | None:
        return self._tf("supportsIgmpCfg", "typeFields.supportsIgmpCfg")

    @supports_igmp.setter
    def supports_igmp(self, value: bool) -> None:
        self._stage("typeFields.supportsIgmpCfg", value)

    @property
    def supports_mac_forwarding(self) -> bool | None:
        return self._tf("supportsMacForwardingCfg", "typeFields.supportsMacForwardingCfg")

    @supports_mac_forwarding.setter
    def supports_mac_forwarding(self, value: bool) -> None:
        self._stage("typeFields.supportsMacForwardingCfg", value)

    @property
    def supports_nso(self) -> bool | None:
        return self._tf("supportsNsoCfg", "typeFields.supportsNsoCfg")

    @supports_nso.setter
    def supports_nso(self, value: bool) -> None:
        self._stage("typeFields.supportsNsoCfg", value)

    @property
    def supports_openflow(self) -> bool | None:
        return self._tf("supportsOpenflowCfg", "typeFields.supportsOpenflowCfg")

    @supports_openflow.setter
    def supports_openflow(self, value: bool) -> None:
        self._stage("typeFields.supportsOpenflowCfg", value)

    @property
    def supports_static_igmp(self) -> bool | None:
        return self._tf("supportsStaticIgmpCfg", "typeFields.supportsStaticIgmpCfg")

    @supports_static_igmp.setter
    def supports_static_igmp(self, value: bool) -> None:
        self._stage("typeFields.supportsStaticIgmpCfg", value)

    # Alias matching the topology app's naming used by vertex processors.
    @property
    def supports_static_igmp_config(self) -> bool | None:
        return self.supports_static_igmp

    @supports_static_igmp_config.setter
    def supports_static_igmp_config(self, value: bool) -> None:
        self.supports_static_igmp = value

    @property
    def supports_vlan(self) -> bool | None:
        return self._tf("supportsVlanCfg", "typeFields.supportsVlanCfg")

    @supports_vlan.setter
    def supports_vlan(self, value: bool) -> None:
        self._stage("typeFields.supportsVlanCfg", value)

    @property
    def supports_vpls(self) -> bool | None:
        return self._tf("supportsVplsCfg", "typeFields.supportsVplsCfg")

    @supports_vpls.setter
    def supports_vpls(self, value: bool) -> None:
        self._stage("typeFields.supportsVplsCfg", value)

    def _tf(self, name: str, staged_field: str) -> Any:
        return self._staged_or(
            staged_field,
            lambda: getattr(self.type_fields, name, None) if self.type_fields is not None else None,
        )


class InspectCodecVertex(InspectVertex):
    """A codec vertex (``typeFields.type == "codec"``): codec format and source/destination config,
    read from the ``typeFields.generic`` / ``typeFields.specific`` blocks (verified 2025.4.9)."""

    @property
    def codec_format(self) -> str | None:
        return self._generic_get("codecFormat", "typeFields.generic.codecFormat")

    @codec_format.setter
    def codec_format(self, value: str) -> None:
        self._stage("typeFields.generic.codecFormat", value)

    @property
    def public(self) -> bool | None:
        return self._generic_get("public", "typeFields.generic.public")

    @public.setter
    def public(self, value: bool) -> None:
        self._stage("typeFields.generic.public", value)

    @property
    def multiplicity(self) -> int | None:
        return self._generic_get("multiplicity", "typeFields.generic.multiplicity")

    @multiplicity.setter
    def multiplicity(self, value: int) -> None:
        self._stage("typeFields.generic.multiplicity", value)

    @property
    def extra_formats(self) -> list[Any]:
        return self._staged_or(
            "typeFields.generic.extraFormats",
            lambda: list(g.extraFormats) if (g := self.generic) else [],
            adapt=list,
        )

    @extra_formats.setter
    def extra_formats(self, value: list[Any]) -> None:
        self._stage("typeFields.generic.extraFormats", list(value))

    @property
    def bidir_partner_id(self) -> str | None:
        return self._generic_get("bidirPartnerId", "typeFields.generic.bidirPartnerId")

    @bidir_partner_id.setter
    def bidir_partner_id(self, value: str | None) -> None:
        self._stage("typeFields.generic.bidirPartnerId", value)

    @property
    def partner_config(self) -> Any:
        return self._generic_get("partnerConfig", "typeFields.generic.partnerConfig")

    @partner_config.setter
    def partner_config(self, value: Any) -> None:
        self._stage("typeFields.generic.partnerConfig", value)

    @property
    def service_id(self) -> Any:
        return self._generic_get("serviceId", "typeFields.generic.serviceId")

    @service_id.setter
    def service_id(self, value: Any) -> None:
        self._stage("typeFields.generic.serviceId", value)

    @property
    def main_src_info(self) -> dict[str, Any] | None:
        return self._endpoint_info("mainSrcInfo")

    @main_src_info.setter
    def main_src_info(self, value: dict[str, Any] | None) -> None:
        self._stage("typeFields.generic.mainSrcInfo", value)

    @property
    def main_dst_info(self) -> dict[str, Any] | None:
        return self._endpoint_info("mainDstInfo")

    @main_dst_info.setter
    def main_dst_info(self, value: dict[str, Any] | None) -> None:
        self._stage("typeFields.generic.mainDstInfo", value)

    @property
    def spare_src_info(self) -> dict[str, Any] | None:
        return self._endpoint_info("spareSrcInfo")

    @spare_src_info.setter
    def spare_src_info(self, value: dict[str, Any] | None) -> None:
        self._stage("typeFields.generic.spareSrcInfo", value)

    @property
    def spare_dst_info(self) -> dict[str, Any] | None:
        return self._endpoint_info("spareDstInfo")

    @spare_dst_info.setter
    def spare_dst_info(self, value: dict[str, Any] | None) -> None:
        self._stage("typeFields.generic.spareDstInfo", value)

    @property
    def main_destination_port(self) -> int | None:
        return self._staged_or(
            "typeFields.generic.mainDstInfo.port",
            lambda: self._port_from_endpoint_info(self.main_dst_info),
        )

    @main_destination_port.setter
    def main_destination_port(self, value: int) -> None:
        self._stage("typeFields.generic.mainDstInfo.port", value)

    @property
    def spare_destination_port(self) -> int | None:
        return self._staged_or(
            "typeFields.generic.spareDstInfo.port",
            lambda: self._port_from_endpoint_info(self.spare_dst_info),
        )

    @spare_destination_port.setter
    def spare_destination_port(self, value: int) -> None:
        self._stage("typeFields.generic.spareDstInfo.port", value)

    @property
    def is_igmp_source(self) -> bool | None:
        return self._specific_get("isIgmpSource", "typeFields.specific.isIgmpSource")

    @is_igmp_source.setter
    def is_igmp_source(self, value: bool) -> None:
        self._stage("typeFields.specific.isIgmpSource", value)

    @property
    def sdp_support(self) -> bool | None:
        return self._specific_get("sdpSupport", "typeFields.specific.sdpSupport")

    @sdp_support.setter
    def sdp_support(self, value: bool) -> None:
        self._stage("typeFields.specific.sdpSupport", value)

    @property
    def specific_type(self) -> str | None:
        return self._specific_get("type", "typeFields.specific.type")

    @specific_type.setter
    def specific_type(self, value: str) -> None:
        self._stage("typeFields.specific.type", value)

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

    def _generic_get(self, attr: str, staged_field: str) -> Any:
        return self._staged_or(
            staged_field,
            lambda: getattr(g, attr, None) if (g := self.generic) else None,
        )

    def _specific_get(self, attr: str, staged_field: str) -> Any:
        return self._staged_or(
            staged_field,
            lambda: getattr(s, attr, None) if (s := self.specific) else None,
        )

    @staticmethod
    def _port_from_endpoint_info(info: dict[str, Any] | None) -> int | None:
        port = info.get("port") if info else None
        return int(port) if isinstance(port, (int, float)) else port

    def _endpoint_info(self, name: str) -> dict[str, Any] | None:
        staged = self._staged(f"typeFields.generic.{name}")
        if staged is not _STAGED_MISSING:
            return dict(staged) if isinstance(staged, dict) else staged
        # Merge leaf-level staged ports into the baseline block for read-your-writes.
        generic = self.generic
        baseline = getattr(generic, name, None) if generic else None
        merged: dict[str, Any] = dict(baseline) if isinstance(baseline, dict) else {}
        for leaf in ("ip", "mac", "port", "vlan", "gateway", "netmask"):
            leaf_staged = self._staged(f"typeFields.generic.{name}.{leaf}")
            if leaf_staged is not _STAGED_MISSING:
                merged[leaf] = leaf_staged
        return merged or (baseline if isinstance(baseline, dict) else None)

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
    port_factory_label: str | None = None,
) -> InspectVertex:
    """Construct the typed vertex view for ``vertex_id`` from its ``typeFields.type`` kind (falls
    back to the base :class:`InspectVertex` when the kind is unknown, e.g. no fetcher)."""
    cls = _VERTEX_CLASS_BY_KIND.get(kind, InspectVertex)
    return cls(
        snapshot=snapshot,
        id=vertex_id,
        vertex_info=vertex_info,
        port_factory_label=port_factory_label,
    )


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
