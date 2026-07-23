"""Raw Inspect API layer: one method per verified endpoint, typed responses, no business logic.

All reads use the collector namespace only ([ADR-0008]); scoped queries come from
``queries.py`` ([ADR-0007]). Writes go through ``updateTopology`` and the network
actions (``addDevices``, ``syncDevices``, virtual-device actions).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from . import queries
from videoipath_automation_tool.apps.inspect.model.actions import (
    InspectApiAddDevicesItem,
    InspectApiAddDevicesRequest,
    InspectApiLookupEdgesRequest,
    InspectApiLookupEdgesResponse,
    InspectApiLookupInspectDeviceRequest,
    InspectApiLookupInspectDeviceResponse,
    InspectApiLookupSyncInfoRequest,
    InspectApiLookupSyncInfoResponse,
    InspectApiLookupVerticesRequest,
    InspectApiLookupVerticesResponse,
    InspectApiSyncDevicesRequest,
    InspectApiSyncDevicesRequestData,
)
from videoipath_automation_tool.apps.inspect.model.collector import (
    InspectApiCollectorResponse,
    InspectApiExternalEdgesByDeviceKeyItem,
    InspectApiNodeStatusItem,
    InspectApiPathItem,
)
from videoipath_automation_tool.apps.inspect.model.common import (
    InspectApiSimpleActionResponse,
)
from videoipath_automation_tool.apps.inspect.model.tags import (
    InspectApiAssignTagData,
    InspectApiAssignTagRequest,
)
from videoipath_automation_tool.apps.inspect.model.update_topology import (
    InspectApiUpdateTopologyData,
    InspectApiUpdateTopologyRequest,
    InspectApiUpdateTopologyResponse,
)
from videoipath_automation_tool.apps.inspect.model.virtual import (
    InspectApiAddVirtualTopologyData,
    InspectApiAddVirtualTopologyRequest,
    InspectApiUpdateVirtualInstancesData,
    InspectApiUpdateVirtualInstancesRequest,
    InspectApiUpdateVirtualInstancesResponse,
    InspectApiUpdateVirtualTemplatesData,
    InspectApiUpdateVirtualTemplatesRequest,
    InspectApiVirtualDeviceInstance,
    InspectApiVirtualTemplateItem,
)
from videoipath_automation_tool.connector.vip_connector import VideoIPathConnector
from videoipath_automation_tool.utils.cross_app_utils import create_fallback_logger


class InspectAPI:
    def __init__(self, vip_connector: VideoIPathConnector, logger: Optional[logging.Logger] = None) -> None:
        self._logger = logger or create_fallback_logger("videoipath_automation_tool_inspect_api")
        self.vip_connector = vip_connector
        self._logger.debug("Inspect API initialized.")

    # --- Collector reads (scoped, ADR-0007) ---

    def get_device_skeleton(self) -> list[InspectApiNodeStatusItem]:
        """All devices without module/port detail (skeleton load)."""
        response = self.vip_connector.rest.get(queries.device_skeleton(), allow_projection=True)
        items = _extract_items(response.data, "status", "collector", "inspect", "nodeStatus")
        return [InspectApiNodeStatusItem.model_validate(item) for item in items]

    def get_device_detail(self, device_id: str) -> Optional[InspectApiNodeStatusItem]:
        """One device's full nodeStatus sub-tree (lazy hydration)."""
        response = self.vip_connector.rest.get(queries.device_detail(device_id), allow_projection=True)
        items = _extract_items(response.data, "status", "collector", "inspect", "nodeStatus")
        if not items:
            return None
        return InspectApiNodeStatusItem.model_validate(items[0])

    def get_edge_skeleton(self) -> list[InspectApiExternalEdgesByDeviceKeyItem]:
        """All external-edge device pairs, lean projection."""
        response = self.vip_connector.rest.get(queries.edge_skeleton(), allow_projection=True)
        items = _extract_items(response.data, "status", "collector", "externalEdgesByDeviceKey")
        return [InspectApiExternalEdgesByDeviceKeyItem.model_validate(item) for item in items]

    def get_edge_pair(self, pair_id: str) -> Optional[InspectApiExternalEdgesByDeviceKeyItem]:
        """A single external-edge device pair (targeted refresh, ADR-0010)."""
        response = self.vip_connector.rest.get(queries.edge_pair(pair_id), allow_projection=True)
        items = _extract_items(response.data, "status", "collector", "externalEdgesByDeviceKey")
        if not items:
            return None
        return InspectApiExternalEdgesByDeviceKeyItem.model_validate(items[0])

    def get_paths_section(self) -> list[InspectApiPathItem]:
        """The services/paths section."""
        response = self.vip_connector.rest.get(queries.paths_section(), allow_projection=True)
        items = _extract_items(response.data, "status", "collector", "inspect", "paths")
        return [InspectApiPathItem.model_validate(item) for item in items]

    def get_collector_full(self) -> InspectApiCollectorResponse:
        """The full collector aggregate (eager / fallback mode)."""
        response = self.vip_connector.rest.get(queries.collector_full(), allow_projection=True)
        return InspectApiCollectorResponse.model_validate({"data": response.data, "header": _header_dict(response)})

    # --- Virtual device / port-template reads ---

    def get_virtual_templates(self) -> list[InspectApiVirtualTemplateItem]:
        """All port templates (UI: Manage port templates)."""
        response = self.vip_connector.rest.get(queries.virtual_templates(), allow_projection=True)
        items = _extract_items(response.data, "status", "network", "virtualTemplates")
        return [InspectApiVirtualTemplateItem.model_validate(item) for item in items]

    def get_virtual_devices(self) -> list[InspectApiVirtualDeviceInstance]:
        """All virtual device module/port definitions."""
        response = self.vip_connector.rest.get(queries.virtual_devices(), allow_projection=True)
        items = _extract_items(response.data, "status", "network", "virtualDevices")
        return [InspectApiVirtualDeviceInstance.model_validate(item) for item in items]

    # --- Lookups (baselines for compare-and-commit, ADR-0009) ---

    def lookup_inspect_device(self, device_id: str) -> InspectApiLookupInspectDeviceResponse:
        request = InspectApiLookupInspectDeviceRequest(data=device_id)
        response = self.vip_connector.rest.post("/rest/v2/actions/status/collector/lookupInspectDevice", request)
        return InspectApiLookupInspectDeviceResponse.model_validate(_post_envelope(response))

    def lookup_vertices(self, vertex_ids: list[str]) -> InspectApiLookupVerticesResponse:
        request = InspectApiLookupVerticesRequest(data=vertex_ids)
        response = self.vip_connector.rest.post("/rest/v2/actions/status/collector/lookupInspectVertexByIds", request)
        return InspectApiLookupVerticesResponse.model_validate(_post_envelope(response))

    def lookup_edges(self, edge_ids: list[str]) -> InspectApiLookupEdgesResponse:
        request = InspectApiLookupEdgesRequest(data=edge_ids)
        response = self.vip_connector.rest.post("/rest/v2/actions/status/collector/lookupInspectEdgesByIds", request)
        return InspectApiLookupEdgesResponse.model_validate(_post_envelope(response))

    def lookup_sync_info(self, device_ids: list[str]) -> InspectApiLookupSyncInfoResponse:
        request = InspectApiLookupSyncInfoRequest(data=device_ids)
        response = self.vip_connector.rest.post("/rest/v2/actions/status/collector/lookupSyncInfo", request)
        return InspectApiLookupSyncInfoResponse.model_validate(_post_envelope(response))

    # --- Writes ---

    def update_topology(self, delta: InspectApiUpdateTopologyData) -> InspectApiUpdateTopologyResponse:
        request = InspectApiUpdateTopologyRequest(data=delta)
        response = self.vip_connector.rest.post("/rest/v2/actions/status/collector/updateTopology", request)
        return InspectApiUpdateTopologyResponse.model_validate(_post_envelope(response))

    def assign_tag(self, tag_id: str, element_ids: list[str]) -> InspectApiSimpleActionResponse:
        """Bind ``tag_id`` to one or more resource ids (e.g. ``device:{modulePid}``)."""
        request = InspectApiAssignTagRequest(data=InspectApiAssignTagData(tagId=tag_id, elementIds=element_ids))
        response = self.vip_connector.rest.post("/rest/v2/actions/status/tags/assignTag", request)
        return _tag_action_response(response)

    def unassign_tag(self, tag_id: str, element_ids: list[str]) -> InspectApiSimpleActionResponse:
        """Remove ``tag_id`` from one or more resource ids (e.g. ``device:{modulePid}``)."""
        request = InspectApiAssignTagRequest(data=InspectApiAssignTagData(tagId=tag_id, elementIds=element_ids))
        response = self.vip_connector.rest.post("/rest/v2/actions/status/tags/unassignTag", request)
        return _tag_action_response(response)

    def add_devices(self, items: list[InspectApiAddDevicesItem]) -> InspectApiSimpleActionResponse:
        request = InspectApiAddDevicesRequest(data=items)
        response = self.vip_connector.rest.post("/rest/v2/actions/status/network/addDevices", request)
        return InspectApiSimpleActionResponse.model_validate(_post_envelope(response))

    def sync_devices(
        self, device_ids: list[str], add_only: bool = True, conflict_strategy: int = 0
    ) -> InspectApiSimpleActionResponse:
        request = InspectApiSyncDevicesRequest(
            data=InspectApiSyncDevicesRequestData(ids=device_ids, addOnly=add_only, conflictStrategy=conflict_strategy)
        )
        response = self.vip_connector.rest.post("/rest/v2/actions/status/network/syncDevices", request)
        return InspectApiSimpleActionResponse.model_validate(_post_envelope(response))

    def update_virtual_instances(
        self, data: InspectApiUpdateVirtualInstancesData
    ) -> InspectApiUpdateVirtualInstancesResponse:
        """Create virtual devices (UI: Create virtual devices); wire also supports update/remove."""
        request = InspectApiUpdateVirtualInstancesRequest(data=data)
        response = self.vip_connector.rest.post("/rest/v2/actions/status/network/updateVirtualInstances", request)
        return InspectApiUpdateVirtualInstancesResponse.model_validate(_post_envelope(response))

    def update_virtual_templates(self, data: InspectApiUpdateVirtualTemplatesData) -> InspectApiSimpleActionResponse:
        """Add or remove port templates (UI: Manage port templates)."""
        request = InspectApiUpdateVirtualTemplatesRequest(data=data)
        response = self.vip_connector.rest.post("/rest/v2/actions/status/network/updateVirtualTemplates", request)
        return InspectApiSimpleActionResponse.model_validate(_post_envelope(response))

    def add_virtual_topology(self, data: InspectApiAddVirtualTopologyData) -> InspectApiSimpleActionResponse:
        """Add ports from templates to an existing virtual-device module."""
        request = InspectApiAddVirtualTopologyRequest(data=data)
        response = self.vip_connector.rest.post("/rest/v2/actions/status/network/addVirtualTopology", request)
        return InspectApiSimpleActionResponse.model_validate(_post_envelope(response))


# --- Internal ---


def _extract_items(data: dict[str, Any], *path: str) -> list[dict[str, Any]]:
    """Walk ``data`` down ``path`` and return the ``_items`` list (empty if any node is absent)."""
    node: Any = data
    for key in path:
        if not isinstance(node, dict):
            return []
        node = node.get(key)
        if node is None:
            return []
    if isinstance(node, dict):
        items = node.get("_items", [])
        return items if isinstance(items, list) else []
    return []


def _header_dict(response: Any) -> dict[str, Any]:
    header = getattr(response, "header", None)
    if header is None:
        return {}
    return header.model_dump(mode="json") if hasattr(header, "model_dump") else dict(header)


def _post_envelope(response: Any) -> dict[str, Any]:
    """Reassemble a ``{data, header}`` dict from a ResponseV2Post for DTO validation."""
    return {"data": response.data, "header": _header_dict(response)}


def _tag_action_response(response: Any) -> InspectApiSimpleActionResponse:
    """Normalize assignTag / unassignTag responses (server often returns ``data: null``)."""
    header = _header_dict(response)
    data = response.data
    if not isinstance(data, dict):
        data = {"ok": bool(header.get("ok")), "msg": list(header.get("msg") or [])}
    elif "ok" not in data:
        data = {**data, "ok": bool(header.get("ok")), "msg": list(data.get("msg") or header.get("msg") or [])}
    return InspectApiSimpleActionResponse.model_validate({"data": data, "header": header})


__all__ = ["InspectAPI"]
