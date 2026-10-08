"""Small live-test fixtures; all writes pass through the real SDK and server."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar
from unittest.mock import Mock, patch

import pytest
from pydantic import BaseModel, ConfigDict

from videoipath_automation_tool.apps.inspect.errors import InspectEntityNotFoundError
from videoipath_automation_tool.provisioning import (
    Blueprint,
    EndpointIdentity,
    ProcessorResult,
    ProvisioningDevice,
    ProvisioningEngine,
    TopologyNotReadyError,
    VertexEdit,
    VertexPatch,
    VertexProcessor,
)

from ..helpers import unique_label

if TYPE_CHECKING:
    from videoipath_automation_tool.apps.inspect.domain.device import InspectDevice
    from videoipath_automation_tool.apps.inventory.model.inventory_device import InventoryDevice
    from videoipath_automation_tool.apps.videoipath_app import VideoIPathApp
    from videoipath_automation_tool.provisioning import ApplyResult, ProcessingContext, ProvisioningPlan

BLUEPRINT_PATH = Path(__file__).parent / "fixtures" / "mock-router.yml"
T = TypeVar("T")


class RouterParams(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class RouterProcessor(VertexProcessor[RouterParams]):
    """Expose directional mock router vertices as deterministically named endpoints."""

    params_model = RouterParams

    def process(self, context: ProcessingContext, params: RouterParams) -> ProcessorResult:
        vertices = [v for v in context.find_vertices(kind="router") if v.vertex_type in ("In", "Out")]
        if not vertices:
            raise TopologyNotReadyError("Mock router directional ports are not discovered yet.")
        return ProcessorResult(
            vertices=[
                VertexEdit(
                    vertex_id=vertex.id,
                    fields=VertexPatch(use_as_endpoint=True, active=True),
                    endpoint=EndpointIdentity(
                        direction="RX" if vertex.vertex_type == "In" else "TX", media="video", index=index
                    ),
                )
                for index, vertex in enumerate(vertices, 1)
            ]
        )


class LiveProvisioning:
    """Allocate a small scenario and provide fresh reads, without faking any server behavior."""

    def __init__(self, app: VideoIPathApp, addresses: Iterator[str], origin: tuple[int, int], tag: str) -> None:
        self.app = app
        self.tag = tag
        self.engine = ProvisioningEngine(app, processors={"example-org.e2e-router": RouterProcessor})
        self.blueprint = Blueprint.load(BLUEPRINT_PATH)
        self._addresses = addresses
        self._origin = origin
        self._slot = 0

    def device(self, name: str, **fields: Any) -> ProvisioningDevice:
        label = unique_label(f"PROV-{name}")
        x, y = self._origin
        facts = ProvisioningDevice(
            key=label,
            label=label,
            management_address=next(self._addresses),
            attributes={"x": x + self._slot * 300, "y": y},
            **fields,
        )
        self._slot += 1
        return facts

    def plan(self, device: ProvisioningDevice, **kwargs: Any) -> ProvisioningPlan:
        blueprint = kwargs.pop("blueprint", self.blueprint)
        inputs = {
            "x": device.attributes["x"],
            "y": device.attributes["y"],
            "marker_tag": self.tag,
            **kwargs.pop("inputs", {}),
        }
        return self.engine.plan(device, blueprint, inputs=inputs, **kwargs)

    def onboard(self, name: str, **kwargs: Any) -> ProvisioningDevice:
        device = self.device(name)
        result = self.plan(device, **kwargs).apply()
        assert_confirmed(result)
        assert result.inventory_id is not None
        return device.model_copy(update={"inventory_id": result.inventory_id})

    def inventory(self, device: ProvisioningDevice) -> InventoryDevice:
        assert device.inventory_id is not None
        return self.app.inventory.get_device(device_id=device.inventory_id, config_only=True)

    def topology(self, device: ProvisioningDevice) -> InspectDevice:
        assert device.inventory_id is not None
        self.app.inspect.refresh()
        found = self.app.inspect.get_device(device.inventory_id)
        assert found is not None, f"Provisioned device {device.label} is missing from Inspect"
        return found


def assert_confirmed(result: ApplyResult) -> None:
    assert result.status == "succeeded", result.model_dump()
    assert result.verification == "confirmed", result.verification_detail


def assert_not_in_topology(app: VideoIPathApp, device_id: str) -> None:
    # Collector nodes include Inventory-only devices; an edit form exists only after topology add.
    with pytest.raises(InspectEntityNotFoundError):
        app.inspect._inspect_api.lookup_inspect_device(device_id)


def wait_until(read: Callable[[], T], ready: Callable[[T], bool], description: str, timeout: float = 60) -> T:
    """Poll only the expected asynchronous state; API errors propagate immediately."""
    deadline = time.monotonic() + timeout
    while True:
        value = read()
        if ready(value):
            return value
        if time.monotonic() >= deadline:
            raise AssertionError(f"Timed out waiting for {description}; last state: {value!r}")
        time.sleep(0.5)


@contextmanager
def observe_writes(app: VideoIPathApp) -> Iterator[list[Mock]]:
    """Record SDK mutation calls while forwarding every call to its real implementation."""
    targets = [
        (app.inventory, "add_device"),
        (app.inventory, "update_device"),
        *[
            (app.inspect._inspect_api, name)
            for name in ("add_devices", "sync_devices", "update_topology", "assign_tag", "unassign_tag")
        ],
    ]
    with ExitStack() as stack:
        yield [stack.enter_context(patch.object(owner, name, wraps=getattr(owner, name))) for owner, name in targets]


def assert_no_writes(writes: list[Mock]) -> None:
    assert not [call for spy in writes for call in spy.mock_calls]
