from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import Field

from videoipath_automation_tool.apps.inspect.domain.port import PortFromTemplate
from videoipath_automation_tool.apps.inspect.model.common import (
    InspectApiStatusSummary,
    InspectEditableModel,
    InspectInternalModel,
)
from videoipath_automation_tool.apps.inspect.model.virtual import InspectApiVirtualModule
from videoipath_automation_tool.apps.inspect.snapshot import InspectSnapshot, _STAGED_MISSING

if TYPE_CHECKING:
    from videoipath_automation_tool.apps.inspect.domain.device import InspectDevice
    from videoipath_automation_tool.apps.inspect.domain.port import InspectPort
    from videoipath_automation_tool.apps.inspect.domain.vertex import InspectVertex
    from videoipath_automation_tool.apps.inspect.model.collector import InspectApiModuleStatus


class VirtualModuleSpec(InspectInternalModel):
    """One module on a virtual device (UI: Module 1, Module 2, …). Mutable for fluent building."""

    ports: list[PortFromTemplate] = Field(default_factory=list)
    module_number: int | None = None

    def to_wire(self) -> InspectApiVirtualModule:
        return InspectApiVirtualModule(
            moduleNumber=self.module_number,
            vertices=[port.to_wire() for port in self.ports],
        )


class InspectModule(InspectEditableModel):
    """A device module / slot. A module owns many ports, each of which carries one or more vertices, so a module
    holds many vertices in total. The module status is resolved live from the snapshot, so a held
    reference sees hydrated/refreshed data transparently.

    Prefer :attr:`id` and :attr:`device` (``module.device.id``) over the constructor fields
    ``module_id`` / ``device_id``.

    Editable attributes use property setters that stage pending intents on the snapshot
    (read-your-writes). Flush with ``app.inspect.update(module)``, ``app.inspect.update(device)``,
    or ``tx.update(...)`` inside a transaction. Module tags are committed via ``assignTag`` /
    ``unassignTag`` (not ``updateTopology``).
    """

    snapshot: InspectSnapshot
    device_id: str
    module_id: str

    @property
    def _edit_kind(self) -> Literal["module"]:
        return "module"

    @property
    def id(self) -> str:
        return self.module_id

    @property
    def label(self) -> str | None:
        """The module label."""
        status = self._status()
        return status.effective_label if status is not None else None

    @property
    def description(self) -> str | None:
        status = self._status()
        return status.effective_description if status is not None else None

    @property
    def status(self) -> InspectApiStatusSummary | None:
        status = self._status()
        return status.status if status is not None else None

    @property
    def tags(self) -> list[str]:
        """Locally assigned module tags (``tagsInfo.assigned.local``; writable via assign/unassign)."""
        staged = self._staged("tags")
        if staged is not _STAGED_MISSING:
            return list(staged)
        status = self._status()
        if status is None:
            return []
        local = status.local_assigned_tags
        return list(local) if local else list(status.assigned_tags)

    @tags.setter
    def tags(self, value: list[str]) -> None:
        self._stage("tags", list(value))

    @property
    def device(self) -> InspectDevice | None:
        """The owning device; use ``module.device.id`` for the device id."""
        return self.snapshot.get_device_by_id(self.device_id)

    @property
    def ports(self) -> list[InspectPort]:
        """The port rows in this module (e.g. "Router In 11.1", "Router Out 11.1", …)."""
        return self.snapshot.get_ports_for_module(self.device_id, self.module_id)

    @property
    def vertices(self) -> list[InspectVertex]:
        """Every vertex across the module's ports (triggers a lazy vertex lookup per port for the
        typed kind)."""
        return [vertex for port in self.ports for vertex in port._vertices()]

    def _status(self) -> InspectApiModuleStatus | None:
        return self.snapshot.get_module_status(self.device_id, self.module_id)


__all__ = ["InspectModule", "VirtualModuleSpec"]
