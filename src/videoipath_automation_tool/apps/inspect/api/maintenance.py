"""Verified maintenance endpoints, kept separate from topology transactions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import TypeAdapter

from ..errors import InspectMaintenanceError
from ..model.common import InspectApiBaseModel
from ..model.maintenance import (
    InspectApiFetchMaintenanceImpactData,
    InspectApiFetchMaintenanceImpactRequest,
    InspectApiMaintenanceBookingItem,
    InspectApiUpdateMaintenanceData,
    InspectApiUpdateMaintenanceRequest,
    InspectApiUpdateMaintenanceResponse,
    InspectApiValidateMaintenanceData,
    InspectApiValidateMaintenanceRequest,
    MaintenanceImpact,
    MaintenanceResult,
)
from . import queries

if TYPE_CHECKING:
    from videoipath_automation_tool.connector.vip_connector import VideoIPathConnector


class InspectMaintenanceAPI:
    vip_connector: VideoIPathConnector

    def get_maintenance_section(self) -> list[InspectApiMaintenanceBookingItem]:
        response = None
        try:
            response = self.vip_connector.rest.get(queries.maintenance_section(), allow_projection=True)
            _check_header(response, "read", [])
            collection = response.data["status"]["collector"]["maintenanceBookings"]
            return [InspectApiMaintenanceBookingItem.model_validate(item) for item in collection.get("_items", [])]
        except InspectMaintenanceError:
            raise
        except Exception as exc:  # The connector also raises untyped transport/envelope errors.
            raise InspectMaintenanceError("read", [], str(exc), response) from exc

    def update_maintenance(self, data: InspectApiUpdateMaintenanceData, *, operation: str) -> MaintenanceResult:
        ids = [item.id for item in data.update] + data.delete
        response = self._maintenance_post(
            "updateMaintenance", InspectApiUpdateMaintenanceRequest(data=data), operation, ids
        )
        try:
            parsed = InspectApiUpdateMaintenanceResponse.model_validate(
                {"data": response.data, "header": response.header.model_dump(mode="json")}
            )
        except ValueError as exc:
            raise InspectMaintenanceError(operation, ids, f"Invalid response: {exc}", response) from exc
        if not parsed.data.result.ok:
            raise InspectMaintenanceError(operation, ids, "; ".join(parsed.data.result.msg), parsed)
        return parsed.data.result.model_copy(update={"details": parsed.data.details})

    def validate_maintenance(self, data: InspectApiValidateMaintenanceData) -> dict[str, MaintenanceImpact]:
        ids = [data.id] if data.id else []
        response = self._maintenance_post(
            "validateMaintenanceImpactDetailed", InspectApiValidateMaintenanceRequest(data=data), "validate", ids
        )
        return _impact_map(response, "validate", ids, _IMPACT)

    def fetch_maintenance_impact(self, ids: list[str]) -> dict[str, dict[str, MaintenanceImpact]]:
        response = self._maintenance_post(
            "fetchMaintenanceImpact",
            InspectApiFetchMaintenanceImpactRequest(data=InspectApiFetchMaintenanceImpactData(ids=ids)),
            "impact",
            ids,
        )
        return _impact_map(response, "impact", ids, _IMPACTS)

    def _maintenance_post(self, action: str, body: InspectApiBaseModel, operation: str, ids: list[str]) -> Any:
        response = None
        try:
            response = self.vip_connector.rest.post(f"/rest/v2/actions/status/pathman/{action}", body)
            _check_header(response, operation, ids)
            return response
        except InspectMaintenanceError:
            raise
        except Exception as exc:
            raise InspectMaintenanceError(operation, ids, str(exc), response) from exc


def _check_header(response: Any, operation: str, ids: list[str]) -> None:
    header = response.header.model_dump(mode="json")
    if not header.get("ok") or not header.get("auth") or header.get("code") != "OK":
        raise InspectMaintenanceError(operation, ids, "; ".join(header.get("msg", [])) or "Envelope rejected", response)


def _impact_map(response: Any, operation: str, ids: list[str], adapter: TypeAdapter) -> Any:
    try:
        return adapter.validate_python(response.data)
    except ValueError as exc:
        raise InspectMaintenanceError(operation, ids, f"Invalid impact response: {exc}", response) from exc


_IMPACT = TypeAdapter(dict[str, MaintenanceImpact])
_IMPACTS = TypeAdapter(dict[str, dict[str, MaintenanceImpact]])
