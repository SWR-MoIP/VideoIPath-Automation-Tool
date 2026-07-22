"""User-facing topology writes: direct auto-commit sugar + the explicit transaction ([ADR-0006]).

Direct methods (``place_device``, ``update_device``, ``connect`` …) each open a single-change
transaction and commit it immediately. For batched, atomic changes use ``transaction()`` as a
context manager and call ``commit()`` explicitly.

Every write is bound to the app's internal snapshot: on a successful commit the touched entities are
refreshed in place ([ADR-0010]) — but only if the snapshot has already been loaded, so a pure-write
workflow never triggers an unnecessary topology read.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional, Protocol

from videoipath_automation_tool.apps.inspect.transaction import CommitResult, InspectTransaction
from videoipath_automation_tool.apps.inspect.api import InspectAPI
from videoipath_automation_tool.apps.inspect.model.common import (
    InspectConfigPriority,
    InspectIconSize,
    InspectIconType,
    InspectRedundancyMode,
    InspectSdpStrategy,
)

if TYPE_CHECKING:
    from videoipath_automation_tool.apps.inspect.snapshot import InspectSnapshot


class _HasInspectState(Protocol):
    _inspect_api: InspectAPI
    _logger: logging.Logger
    _snapshot: Optional[InspectSnapshot]


class InspectWriteMixin:
    _inspect_api: InspectAPI
    _logger: logging.Logger
    _snapshot: Optional[InspectSnapshot]

    def transaction(self: _HasInspectState) -> InspectTransaction:
        """Open a batched, atomic transaction bound to the app's internal snapshot."""
        return InspectTransaction(self._inspect_api, snapshot=self._snapshot, logger=self._logger)

    def place_device(self: _HasInspectState, device_id: str, x: float, y: float) -> CommitResult:
        """Move a device to grid coordinates (single auto-committed change)."""
        with self.transaction() as tx:
            tx.place_device(device_id, x, y)
            return tx.commit()

    def update_device(
        self: _HasInspectState,
        device_id: str,
        *,
        label: Optional[str] = None,
        description: Optional[str] = None,
        icon_type: Optional[InspectIconType | str] = None,
        icon_size: Optional[InspectIconSize | str] = None,
        sdp_strategy: Optional[InspectSdpStrategy | str] = None,
        site_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
        coordinates: Optional[dict[str, float]] = None,
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
                coordinates=coordinates,
            )
            return tx.commit()

    def update_vertex(
        self: _HasInspectState,
        vertex_id: str,
        *,
        use_as_endpoint: Optional[bool] = None,
        label: Optional[str] = None,
        tags: Optional[list[str]] = None,
        description: Optional[str] = None,
        active: Optional[bool] = None,
        sips_mode: Optional[str] = None,
        control_props: Optional[Any] = None,
        extra_alert_filters: Optional[list[Any]] = None,
        custom: Optional[dict[str, Any]] = None,
        park_port: Optional[int] = None,
        ip_address: Optional[str] = None,
        ip_netmask: Optional[str] = None,
        public: Optional[bool] = None,
        vlan_id: Optional[str] = None,
        vrf_id: Optional[str] = None,
        supports_cpipe: Optional[bool] = None,
        supports_igmp: Optional[bool] = None,
        supports_mac_forwarding: Optional[bool] = None,
        supports_nso: Optional[bool] = None,
        supports_openflow: Optional[bool] = None,
        supports_static_igmp: Optional[bool] = None,
        supports_vlan: Optional[bool] = None,
        supports_vpls: Optional[bool] = None,
    ) -> CommitResult:
        """Edit a vertex (single auto-committed change; update-only)."""
        with self.transaction() as tx:
            tx.update_vertex(
                vertex_id,
                use_as_endpoint=use_as_endpoint,
                label=label,
                tags=tags,
                description=description,
                active=active,
                sips_mode=sips_mode,
                control_props=control_props,
                extra_alert_filters=extra_alert_filters,
                custom=custom,
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
                supports_static_igmp=supports_static_igmp,
                supports_vlan=supports_vlan,
                supports_vpls=supports_vpls,
            )
            return tx.commit()

    def update_edge(
        self: _HasInspectState,
        edge_id: str,
        *,
        label: Optional[str] = None,
        description: Optional[str] = None,
        weight: Optional[int] = None,
        capacity: Optional[int] = None,
        bandwidth: Optional[float] = None,
        redundancy_mode: Optional[InspectRedundancyMode | str] = None,
        conflict_priority: Optional[InspectConfigPriority | int | str] = None,
        include_formats: Optional[list[str]] = None,
        exclude_formats: Optional[list[str]] = None,
        bandwidth_weight_factor: Optional[int] = None,
        weight_per_service: Optional[int] = None,
        active: Optional[bool] = None,
        tags: Optional[list[str]] = None,
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
