"""Topology device/sync network actions (addDevices, syncDevices, lookupSyncInfo).

These wrap the ``actions/status/network/*`` and ``lookupSyncInfo`` endpoints used by the Inspect
device-onboarding-into-topology workflows. Placement and connections themselves go through the
transaction ([ADR-0006]); these actions handle bringing a device's driver-reported topology into
the graph and keeping it in sync.
"""

from __future__ import annotations

import logging
from enum import IntEnum
from typing import Iterable, Optional, Protocol, Union

from videoipath_automation_tool.apps.inspect.api import InspectAPI
from videoipath_automation_tool.apps.inspect.model.actions import (
    InspectApiAddDevicesItem,
    InspectApiLookupSyncInfoItem,
)
from videoipath_automation_tool.apps.inspect.snapshot import InspectSnapshot


class ConflictStrategy(IntEnum):
    """Conflict handling for ``syncDevices`` (values verified from the Inspect UI bundle)."""

    STRICT = 0
    INVALIDATE_SERVICES = 1
    CANCEL_SERVICES = 2


# (device_id, x, y) or just device_id (placed at 0,0).
AddDeviceSpec = Union[str, tuple[str, float, float]]


class _HasInspectApi(Protocol):
    _inspect_api: InspectAPI
    _logger: logging.Logger
    _snapshot: Optional[InspectSnapshot]


class InspectActionsMixin:
    _inspect_api: InspectAPI
    _logger: logging.Logger
    _snapshot: Optional[InspectSnapshot]

    def get_sync_info(self: _HasInspectApi, device_ids: list[str]) -> dict[str, InspectApiLookupSyncInfoItem]:
        """Per-device sync differences (what would be added/removed/updated on the next sync)."""
        if not device_ids:
            raise ValueError("device_ids must not be empty.")
        return self._inspect_api.lookup_sync_info(device_ids).data

    def add_devices_to_topology(self: _HasInspectApi, devices: Iterable[AddDeviceSpec]) -> bool:
        """Add onboarded devices to the topology graph (``addDevices`` network action).

        Args:
            devices: device ids, or ``(device_id, x, y)`` tuples to place them.

        Returns:
            bool: whether the action reported success (``data.ok``).
        """
        items = [_to_add_item(spec) for spec in devices]
        response = self._inspect_api.add_devices(items)
        if not response.data.ok:
            self._logger.warning(f"addDevices reported failure: {response.data.msg}")
            return False
        self._refresh_after_network_action([item.id for item in items])
        return True

    def sync_devices(
        self: _HasInspectApi,
        device_ids: list[str],
        add_only: bool = True,
        conflict_strategy: ConflictStrategy = ConflictStrategy.STRICT,
    ) -> bool:
        """Synchronize devices' driver-reported topology into the graph (``syncDevices`` action).

        Args:
            device_ids: devices to synchronize.
            add_only: only add new elements; do not remove/update existing ones.
            conflict_strategy: how to handle conflicts with active services.

        Returns:
            bool: whether the action reported success (``data.ok``).
        """
        if not device_ids:
            raise ValueError("device_ids must not be empty.")
        response = self._inspect_api.sync_devices(
            device_ids, add_only=add_only, conflict_strategy=int(conflict_strategy)
        )
        if not response.data.ok:
            self._logger.warning(f"syncDevices reported failure: {response.data.msg}")
            return False
        self._refresh_after_network_action(device_ids)
        return True

    def _refresh_after_network_action(self: _HasInspectApi, device_ids: list[str]) -> None:
        """Update the internal snapshot for the affected devices after a successful network action.

        Only refreshes when a snapshot is already loaded, so a pure-action workflow never triggers
        an unnecessary topology read (mirrors the write path; [ADR-0010])."""
        if self._snapshot is not None:
            self._snapshot.apply_network_refresh(device_ids)


def _to_add_item(spec: AddDeviceSpec) -> InspectApiAddDevicesItem:
    if isinstance(spec, str):
        return InspectApiAddDevicesItem(id=spec, x=0, y=0)
    device_id, x, y = spec
    return InspectApiAddDevicesItem(id=device_id, x=x, y=y)


__all__ = ["InspectActionsMixin", "ConflictStrategy", "AddDeviceSpec"]
