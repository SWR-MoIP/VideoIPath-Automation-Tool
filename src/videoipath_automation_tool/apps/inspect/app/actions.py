"""Topology device/sync network actions (addDevices, syncDevices, lookupSyncInfo) and
virtual-device create / port-template helpers (updateVirtualInstances,
updateVirtualTemplates, addVirtualTopology).

These wrap the ``actions/status/network/*`` and ``lookupSyncInfo`` endpoints used by the Inspect
device-onboarding-into-topology workflows. Placement, metadata edits, connections, and removal of
virtual devices go through the same write/transaction path as physical devices ([ADR-0006]); only
creating a virtual device (and managing port templates / adding ports from templates) uses these
dedicated network actions.
"""

from __future__ import annotations

import logging
from enum import IntEnum
from typing import TYPE_CHECKING, Iterable, Mapping, Optional, Protocol, Union

from videoipath_automation_tool.apps.inspect.api import InspectAPI
from videoipath_automation_tool.apps.inspect.domain.device import VirtualDeviceSpec
from videoipath_automation_tool.apps.inspect.domain.port import (
    InspectPortTemplate,
    PortFromTemplate,
    _ports_to_count_by_template,
)
from videoipath_automation_tool.apps.inspect.errors import InspectError
from videoipath_automation_tool.apps.inspect.model.actions import (
    InspectApiAddDevicesItem,
    InspectApiLookupSyncInfoItem,
)
from videoipath_automation_tool.apps.inspect.model.virtual import (
    InspectApiAddVirtualTopologyData,
    InspectApiUpdateVirtualInstancesData,
    InspectApiUpdateVirtualTemplatesData,
    InspectApiVirtualTemplateWriteBody,
)
from videoipath_automation_tool.validators.virtual_device_id import validate_virtual_device_id

if TYPE_CHECKING:
    from videoipath_automation_tool.apps.inspect.domain.device import InspectDevice
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

    def add_devices_to_topology(
        self: _HasInspectApi,
        devices: Iterable[AddDeviceSpec],
        *,
        sync: bool = True,
        add_only: bool = True,
        conflict_strategy: ConflictStrategy = ConflictStrategy.STRICT,
    ) -> bool:
        """Add onboarded devices to the topology graph (``addDevices`` network action).

        By default also runs ``syncDevices`` so driver-reported ports/vertices appear in the
        graph — the usual onboarding sequence in one call. Pass ``sync=False`` to place only.

        Args:
            devices: device ids, or ``(device_id, x, y)`` tuples to place them.
            sync: when ``True`` (default), synchronize driver-reported topology after adding.
            add_only: forwarded to ``syncDevices`` (only add new elements; do not remove/update).
            conflict_strategy: forwarded to ``syncDevices`` for conflicts with active services.

        Returns:
            bool: whether every action that ran reported success (``data.ok``). On sync failure
            after a successful add, the snapshot is still refreshed for the added devices.
        """
        items = [_to_add_item(spec) for spec in devices]
        device_ids = [item.id for item in items]
        response = self._inspect_api.add_devices(items)
        if not response.data.ok:
            self._logger.warning(f"addDevices reported failure: {response.data.msg}")
            return False
        if sync and device_ids:
            sync_response = self._inspect_api.sync_devices(
                device_ids, add_only=add_only, conflict_strategy=int(conflict_strategy)
            )
            if not sync_response.data.ok:
                self._logger.warning(f"syncDevices reported failure: {sync_response.data.msg}")
                self._refresh_after_network_action(device_ids)
                return False
        self._refresh_after_network_action(device_ids)
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

    # --- Virtual devices / port templates (UI: Create virtual devices) ---

    def list_port_templates(self: _HasInspectApi) -> list[InspectPortTemplate]:
        """List port templates available when building virtual devices."""
        return [InspectPortTemplate.from_wire(item) for item in self._inspect_api.get_virtual_templates()]

    def create_port_template(
        self: _HasInspectApi,
        template_id: str,
        label: str,
        vertex: dict,
        *,
        force: bool = False,
    ) -> bool:
        """Create or replace a port template (UI: Manage port templates).

        Args:
            template_id: client-chosen template id (non-empty).
            label: display label in the Add port dropdown.
            vertex: vertex configuration payload (same shape as template ``vertex`` on read).
            force: pass-through to the network action.
        """
        if not template_id:
            raise ValueError("template_id must not be empty.")
        if not label:
            raise ValueError("label must not be empty.")
        response = self._inspect_api.update_virtual_templates(
            InspectApiUpdateVirtualTemplatesData(
                add={template_id: InspectApiVirtualTemplateWriteBody(label=label, vertex=vertex)},
                remove=[],
                force=force,
            )
        )
        if not response.data.ok:
            self._logger.warning(f"updateVirtualTemplates reported failure: {response.data.msg}")
            return False
        return True

    def delete_port_templates(self: _HasInspectApi, template_ids: Iterable[str], *, force: bool = False) -> bool:
        """Remove port templates by id."""
        ids = list(template_ids)
        if not ids:
            raise ValueError("template_ids must not be empty.")
        if any(not template_id for template_id in ids):
            raise ValueError("template_ids must not contain empty ids.")
        response = self._inspect_api.update_virtual_templates(
            InspectApiUpdateVirtualTemplatesData(add={}, remove=ids, force=force)
        )
        if not response.data.ok:
            self._logger.warning(f"updateVirtualTemplates reported failure: {response.data.msg}")
            return False
        return True

    def create_virtual_device(self: _HasInspectApi, spec: VirtualDeviceSpec) -> "InspectDevice":
        """Create one virtual device from a module/port-template spec.

        The device is created unplaced (``coordinates`` null); use ``place_device`` /
        ``update_device`` / ``remove_device_from_topology`` afterwards — the same methods as for
        physical devices. ``InspectDevice.is_virtual`` is ``True`` on the returned object.
        """
        return self.create_virtual_devices(spec, copies=1)[0]

    def create_virtual_devices(
        self: _HasInspectApi,
        spec: VirtualDeviceSpec,
        *,
        copies: int = 1,
    ) -> list["InspectDevice"]:
        """Create one or more virtual devices from a module/port-template spec.

        Devices are created unplaced (``coordinates`` null); use ``place_device`` to position them
        and the normal device write methods for metadata edits / removal.

        Args:
            spec: module/port definition (UI: Virtual Devices dialog).
            copies: number of identical devices to create (UI: Number of copies).

        Returns:
            Created :class:`InspectDevice` objects (server-assigned ``virtual.N`` ids).

        Raises:
            InspectError: the network action failed, or created devices are not yet in the snapshot.
        """
        if copies < 1:
            raise ValueError("copies must be at least 1.")
        body = spec.to_wire()
        response = self._inspect_api.update_virtual_instances(
            InspectApiUpdateVirtualInstancesData(
                add=[body for _ in range(copies)],
                update={},
                remove=[],
                force=False,
            )
        )
        if not (response.header.ok and response.data.res.ok and response.data.validation.result.ok):
            msgs = response.data.res.msg or response.data.validation.result.msg
            detail = "; ".join(m for m in msgs if m) or "updateVirtualInstances reported failure"
            raise InspectError(f"create_virtual_devices failed: {detail}")
        created_ids = list(response.data.addedDeviceLabels)
        snapshot = self._ensure_snapshot()
        snapshot.upsert_devices_from_skeleton(created_ids)
        devices: list[InspectDevice] = []
        for device_id in created_ids:
            device = snapshot.get_device(device_id)
            if device is None:
                self._logger.warning(
                    "Virtual device '%s' was created but is not yet visible in the Inspect snapshot.",
                    device_id,
                )
                continue
            devices.append(device)
        if not devices:
            raise InspectError(
                f"Virtual device(s) created ({', '.join(created_ids) or 'none'}) "
                "but not visible in the Inspect snapshot."
            )
        return devices

    def add_virtual_ports(
        self: _HasInspectApi,
        device_id: str,
        module_number: int,
        ports: Mapping[str, int] | list[PortFromTemplate],
    ) -> bool:
        """Add ports from templates to an existing virtual-device module.

        Args:
            device_id: virtual device id (``virtual.N``).
            module_number: target module index (UI module number).
            ports: ``{template_id: count}`` or a list of :class:`PortFromTemplate`.
        """
        validate_virtual_device_id(device_id)
        if module_number < 0:
            raise ValueError("module_number must be non-negative.")
        count_by_template = _ports_to_count_by_template(ports)
        if not count_by_template:
            raise ValueError("ports must not be empty.")
        response = self._inspect_api.add_virtual_topology(
            InspectApiAddVirtualTopologyData(
                deviceId=device_id,
                moduleId=module_number,
                countByVertexTemplate=count_by_template,
            )
        )
        if not response.data.ok:
            self._logger.warning(f"addVirtualTopology reported failure: {response.data.msg}")
            return False
        self._refresh_after_network_action([device_id])
        return True

    def _ensure_snapshot(self: _HasInspectApi) -> "InspectSnapshot":
        """Return the app snapshot, building it lazily when the read mixin is available."""
        get_snapshot = getattr(self, "_get_snapshot", None)
        if callable(get_snapshot):
            return get_snapshot()
        if self._snapshot is not None:
            return self._snapshot
        raise InspectError(
            "Inspect snapshot is not available; load the topology (e.g. access app.inspect.devices) "
            "before creating virtual devices, or use InspectApp rather than a bare actions mixin."
        )

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
