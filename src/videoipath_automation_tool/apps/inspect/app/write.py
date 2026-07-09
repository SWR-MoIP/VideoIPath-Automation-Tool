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
from typing import Any, Optional, Protocol

from videoipath_automation_tool.apps.inspect.transaction import CommitResult, InspectTransaction
from videoipath_automation_tool.apps.inspect.api import InspectAPI
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
        icon_type: Optional[str] = None,
        sdp_strategy: Optional[str] = None,
        tags: Optional[list[str]] = None,
        coordinates: Optional[dict[str, float]] = None,
    ) -> CommitResult:
        """Edit a device's placement/appearance fields (single auto-committed change)."""
        with self.transaction() as tx:
            tx.update_device(
                device_id,
                label=label,
                icon_type=icon_type,
                sdp_strategy=sdp_strategy,
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
    ) -> CommitResult:
        """Edit a vertex (single auto-committed change; update-only)."""
        with self.transaction() as tx:
            tx.update_vertex(vertex_id, use_as_endpoint=use_as_endpoint, label=label, tags=tags)
            return tx.commit()

    def update_edge(
        self: _HasInspectState,
        edge_id: str,
        *,
        weight: Optional[int] = None,
        capacity: Optional[int] = None,
        bandwidth: Optional[float] = None,
        redundancy_mode: Optional[str] = None,
        active: Optional[bool] = None,
        tags: Optional[list[str]] = None,
    ) -> CommitResult:
        """Edit an existing edge (single auto-committed change)."""
        with self.transaction() as tx:
            tx.update_edge(
                edge_id,
                weight=weight,
                capacity=capacity,
                bandwidth=bandwidth,
                redundancy_mode=redundancy_mode,
                active=active,
                tags=tags,
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
        """Remove a device (its baseDevice element) from the topology graph."""
        with self.transaction() as tx:
            tx.remove_device(device_id)
            return tx.commit()


__all__ = ["InspectWriteMixin"]
