"""Tag assign / unassign action envelopes (``/rest/v2/actions/status/tags/*``).

Used for module (and potentially other resource) tag bindings that are not written via
``updateTopology``.
"""

from __future__ import annotations

from pydantic import Field

from videoipath_automation_tool.apps.inspect.model.common import (
    InspectApiBaseModel,
    InspectApiPostRequestHeader,
)


def module_resource_id(module_pid: str) -> str:
    """Collector resource id for a module pid (``device57.dev.0`` → ``device:device57.dev.0``)."""
    if module_pid.startswith("device:"):
        return module_pid
    return f"device:{module_pid}"


class InspectApiAssignTagData(InspectApiBaseModel):
    tagId: str
    elementIds: list[str] = Field(default_factory=list)


class InspectApiAssignTagRequest(InspectApiBaseModel):
    header: InspectApiPostRequestHeader = Field(default_factory=InspectApiPostRequestHeader)
    data: InspectApiAssignTagData


__all__ = [
    "InspectApiAssignTagData",
    "InspectApiAssignTagRequest",
    "module_resource_id",
]
