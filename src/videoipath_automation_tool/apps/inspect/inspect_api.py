"""Raw Inspect API layer: one method per verified endpoint, typed responses, no business logic.

All reads use the collector namespace only ([ADR-0008]); scoped queries come from
``queries.py`` ([ADR-0007]). Writes go through ``updateTopology`` and the ``addDevices`` /
``syncDevices`` network actions.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from videoipath_automation_tool.apps.inspect import queries
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
from videoipath_automation_tool.apps.inspect.model.update_topology import (
    InspectApiUpdateTopologyData,
    InspectApiUpdateTopologyRequest,
    InspectApiUpdateTopologyResponse,
)
from videoipath_automation_tool.connector.vip_connector import VideoIPathConnector
from videoipath_automation_tool.utils.cross_app_utils import create_fallback_logger


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


class InspectAPI:
    def __init__(self, vip_connector: VideoIPathConnector, logger: Optional[logging.Logger] = None):
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

    def add_devices(self, items: list[InspectApiAddDevicesItem]) -> InspectApiSimpleActionResponse:
        request = InspectApiAddDevicesRequest(data=items)
        response = self.vip_connector.rest.post("/rest/v2/actions/status/network/addDevices", request)
        return InspectApiSimpleActionResponse.model_validate(_post_envelope(response))

    def sync_devices(
        self, device_ids: list[str], add_only: bool = True, conflict_strategy: int = 0
    ) -> InspectApiSimpleActionResponse:
        request = InspectApiSyncDevicesRequest(
            data=InspectApiSyncDevicesRequestData(
                ids=device_ids, addOnly=add_only, conflictStrategy=conflict_strategy
            )
        )
        response = self.vip_connector.rest.post("/rest/v2/actions/status/network/syncDevices", request)
        return InspectApiSimpleActionResponse.model_validate(_post_envelope(response))


def _header_dict(response: Any) -> dict[str, Any]:
    header = getattr(response, "header", None)
    if header is None:
        return {}
    return header.model_dump(mode="json") if hasattr(header, "model_dump") else dict(header)


def _post_envelope(response: Any) -> dict[str, Any]:
    """Reassemble a ``{data, header}`` dict from a ResponseV2Post for DTO validation."""
    return {"data": response.data, "header": _header_dict(response)}


__all__ = ["InspectAPI"]
