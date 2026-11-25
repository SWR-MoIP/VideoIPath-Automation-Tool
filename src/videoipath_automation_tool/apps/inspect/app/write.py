"""User-facing topology writes: direct auto-commit sugar + the explicit transaction.

Direct methods (``place_device``, ``update_device``, ``connect`` …) each open a single-change
transaction and commit it immediately. For batched, atomic changes use ``transaction()`` as a
context manager and call ``commit()`` explicitly.

Domain objects also support a unit-of-work pattern: mutate attributes via setters (pending edits
stage on the snapshot), then call ``update(device)`` / ``update(vertex)`` / ``update(edge)`` to
auto-commit, or ``tx.update(...)`` to stage into an open transaction.

Every write is bound to the app's internal snapshot: on a successful commit the touched entities are
refreshed in place — but only if the snapshot has already been loaded, so a pure-write
workflow never triggers an unnecessary topology read.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Protocol

from videoipath_automation_tool.apps.inspect.api import InspectAPI
from videoipath_automation_tool.apps.inspect.model.common import (
    InspectCodecFormat,
    InspectConfigPriority,
    InspectControl,
    InspectIconSize,
    InspectIconType,
    InspectRedundancyMode,
    InspectSdpStrategy,
    InspectSipsMode,
)
from videoipath_automation_tool.apps.inspect.transaction import (
    CommitResult,
    Editable,
    InspectTransaction,
    _is_single_editable,
    _require_live_object,
    _stage_editable,
)

if TYPE_CHECKING:
    from videoipath_automation_tool.apps.inspect.snapshot import InspectSnapshot


class _HasInspectState(Protocol):
    _inspect_api: InspectAPI
    _logger: logging.Logger
    _snapshot: InspectSnapshot | None


class InspectWriteMixin:
    _inspect_api: InspectAPI
    _logger: logging.Logger
    _snapshot: InspectSnapshot | None

    def transaction(self: _HasInspectState) -> InspectTransaction:
        """Open a batched, atomic transaction bound to the app's internal snapshot."""
        return InspectTransaction(self._inspect_api, snapshot=self._snapshot, logger=self._logger)

    def update(self: _HasInspectState, obj: Editable | Sequence[Editable]) -> CommitResult:
        """Flush pending domain-object edits through a new auto-committed transaction.

        Accepts an :class:`InspectDevice`, :class:`InspectVertex`, :class:`InspectEdge`,
        :class:`InspectModule`, or a sequence of them. For a device, also cascades every dirty
        vertex/edge/module whose id belongs to that device (unit of work).

        For batched changes, mutate domain objects then call ``tx.update(obj)`` on an open
        :meth:`transaction` and ``commit()`` yourself.
        """
        objects = list(obj) if isinstance(obj, Sequence) and not _is_single_editable(obj) else [obj]  # type: ignore[list-item]
        if not objects:
            raise ValueError("Nothing to update.")
        if self._snapshot is None:
            raise RuntimeError(
                "Inspect snapshot is not available; load the topology (e.g. access app.inspect.devices) "
                "before updating domain objects."
            )
        for item in objects:
            _require_live_object(self._snapshot, item)

        txn = self.transaction()
        flushed_keys: list[tuple[str, str]] = []
        for item in objects:
            flushed_keys.extend(_stage_editable(txn, self._snapshot, item))

        if not flushed_keys and len(txn) == 0:
            raise ValueError("No pending edits to flush.")
        result = txn.commit()
        for kind, entity_id in flushed_keys:
            self._snapshot.clear_staged(kind=kind, entity_id=entity_id)
        return result

    def place_device(self: _HasInspectState, device_id: str, x: float, y: float) -> CommitResult:
        """Move a device to grid coordinates (single auto-committed change)."""
        with self.transaction() as tx:
            tx.place_device(device_id, x, y)
            return tx.commit()

    def update_device(
        self: _HasInspectState,
        device_id: str,
        *,
        label: str | None = None,
        description: str | None = None,
        icon_type: InspectIconType | str | None = None,
        icon_size: InspectIconSize | str | None = None,
        sdp_strategy: InspectSdpStrategy | str | None = None,
        site_id: str | None = None,
        tags: list[str] | None = None,
        local_assigned_tags: list[str] | None = None,
        coordinates: dict[str, float] | None = None,
    ) -> CommitResult:
        """Edit a device's "Edit Device" dialog fields (single auto-committed change)."""
        with self.transaction() as tx:
            tx.update_device(
                device_id,
                label=label,
                description=description,
                icon_type=icon_type,
                icon_size=icon_size,
                sdp_strategy=sdp_strategy,
                site_id=site_id,
                tags=tags,
                local_assigned_tags=local_assigned_tags,
                coordinates=coordinates,
            )
            return tx.commit()

    def update_module(
        self: _HasInspectState,
        module_id: str,
        *,
        tags: list[str] | None = None,
    ) -> CommitResult:
        """Edit a module's locally assigned tags (single auto-committed change).

        Diffs the desired list against the current local tags and calls ``assignTag`` /
        ``unassignTag``. Requires a loaded inspect snapshot (module detail is hydrated on demand).
        """
        if self._snapshot is None:
            raise RuntimeError(
                "Inspect snapshot is not available; load the topology (e.g. access app.inspect.devices) "
                "before updating modules."
            )
        with self.transaction() as tx:
            tx.update_module(module_id, tags=tags)
            return tx.commit()

    def update_vertex(
        self: _HasInspectState,
        vertex_id: str,
        *,
        use_as_endpoint: bool | None = None,
        label: str | None = None,
        tags: list[str] | None = None,
        form_tags: list[str] | None = None,
        description: str | None = None,
        active: bool | None = None,
        sips_mode: InspectSipsMode | str | None = None,
        control: InspectControl | str | None = None,
        control_props: Any | None = None,
        extra_alert_filters: list[Any] | None = None,
        custom: dict[str, Any] | None = None,
        queueable: bool | None = None,
        destination_monitor_leader: bool | None = None,
        park_port: int | None = None,
        ip_address: str | None = None,
        ip_netmask: str | None = None,
        public: bool | None = None,
        vlan_id: str | None = None,
        vrf_id: str | None = None,
        supports_cpipe: bool | None = None,
        supports_igmp: bool | None = None,
        supports_mac_forwarding: bool | None = None,
        supports_nso: bool | None = None,
        supports_openflow: bool | None = None,
        supports_pseudo_wires: bool | None = None,
        supports_static_igmp: bool | None = None,
        supports_vlan: bool | None = None,
        supports_vpls: bool | None = None,
        supports_vxlan: bool | None = None,
        sdp_support: bool | None = None,
        is_igmp_source: bool | None = None,
        specific_type: str | None = None,
        codec_format: InspectCodecFormat | str | None = None,
        multiplicity: int | None = None,
        codec_public: bool | None = None,
        extra_formats: list[Any] | None = None,
        bidir_partner_id: str | None = None,
        partner_config: Any | None = None,
        service_id: Any | None = None,
        main_src_info: dict[str, Any] | None = None,
        main_dst_info: dict[str, Any] | None = None,
        spare_src_info: dict[str, Any] | None = None,
        spare_dst_info: dict[str, Any] | None = None,
        main_destination_port: int | None = None,
        spare_destination_port: int | None = None,
    ) -> CommitResult:
        """Edit a vertex (single auto-committed change; update-only).

        ``control`` accepts full/semi/off and preserves configuration priority; ``control="off"``
        disables control. ``control_props`` replaces the properties; pass at most one of the two.
        """
        with self.transaction() as tx:
            tx.update_vertex(
                vertex_id,
                use_as_endpoint=use_as_endpoint,
                label=label,
                tags=tags,
                form_tags=form_tags,
                description=description,
                active=active,
                sips_mode=sips_mode,
                control=control,
                control_props=control_props,
                extra_alert_filters=extra_alert_filters,
                custom=custom,
                queueable=queueable,
                destination_monitor_leader=destination_monitor_leader,
                park_port=park_port,
                ip_address=ip_address,
                ip_netmask=ip_netmask,
                public=public,
                vlan_id=vlan_id,
                vrf_id=vrf_id,
                supports_cpipe=supports_cpipe,
                supports_igmp=supports_igmp,
                supports_mac_forwarding=supports_mac_forwarding,
                supports_nso=supports_nso,
                supports_openflow=supports_openflow,
                supports_pseudo_wires=supports_pseudo_wires,
                supports_static_igmp=supports_static_igmp,
                supports_vlan=supports_vlan,
                supports_vpls=supports_vpls,
                supports_vxlan=supports_vxlan,
                sdp_support=sdp_support,
                is_igmp_source=is_igmp_source,
                specific_type=specific_type,
                codec_format=codec_format,
                multiplicity=multiplicity,
                codec_public=codec_public,
                extra_formats=extra_formats,
                bidir_partner_id=bidir_partner_id,
                partner_config=partner_config,
                service_id=service_id,
                main_src_info=main_src_info,
                main_dst_info=main_dst_info,
                spare_src_info=spare_src_info,
                spare_dst_info=spare_dst_info,
                main_destination_port=main_destination_port,
                spare_destination_port=spare_destination_port,
            )
            return tx.commit()

    def update_edge(
        self: _HasInspectState,
        edge_id: str,
        *,
        label: str | None = None,
        description: str | None = None,
        weight: int | None = None,
        capacity: int | None = None,
        bandwidth: float | None = None,
        redundancy_mode: InspectRedundancyMode | str | None = None,
        conflict_priority: InspectConfigPriority | int | str | None = None,
        include_formats: list[str] | None = None,
        exclude_formats: list[str] | None = None,
        bandwidth_weight_factor: int | None = None,
        weight_per_service: int | None = None,
        active: bool | None = None,
        tags: list[str] | None = None,
        also_opposite: bool = False,
    ) -> CommitResult:
        """Edit an existing edge's "Edit Edge" dialog fields (single auto-committed change).

        With ``also_opposite`` the same changes are applied to the opposite directed edge too.
        """
        with self.transaction() as tx:
            tx.update_edge(
                edge_id,
                label=label,
                description=description,
                weight=weight,
                capacity=capacity,
                bandwidth=bandwidth,
                redundancy_mode=redundancy_mode,
                conflict_priority=conflict_priority,
                include_formats=include_formats,
                exclude_formats=exclude_formats,
                bandwidth_weight_factor=bandwidth_weight_factor,
                weight_per_service=weight_per_service,
                active=active,
                tags=tags,
                also_opposite=also_opposite,
            )
            return tx.commit()

    def connect(
        self: _HasInspectState,
        from_vertex: str,
        to_vertex: str,
        *,
        bidirectional: bool = True,
        overwrite: bool = False,
        **edge_fields: Any,
    ) -> CommitResult:
        """Create an edge (and its reverse if bidirectional) between two vertices."""
        with self.transaction() as tx:
            tx.connect(from_vertex, to_vertex, bidirectional=bidirectional, overwrite=overwrite, **edge_fields)
            return tx.commit()

    def disconnect(
        self: _HasInspectState,
        from_vertex: str,
        to_vertex: str,
        *,
        bidirectional: bool = True,
    ) -> CommitResult:
        """Remove the edge (and its reverse if bidirectional) between two vertices."""
        with self.transaction() as tx:
            tx.disconnect(from_vertex, to_vertex, bidirectional=bidirectional)
            return tx.commit()

    def remove_device_from_topology(self: _HasInspectState, device_id: str) -> CommitResult:
        """Remove a device (its baseDevice element) from the topology graph.

        Works for both physical and virtual (``virtual.N``) devices via ``updateTopology``.
        """
        with self.transaction() as tx:
            tx.remove_device(device_id)
            return tx.commit()


__all__ = ["InspectWriteMixin"]
