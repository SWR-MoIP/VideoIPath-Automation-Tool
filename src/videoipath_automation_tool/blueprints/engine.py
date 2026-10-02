"""The standalone :class:`BlueprintEngine`: configuration, read-only planning, and execution.

``engine.plan(...)`` reads VideoIPath state and returns an immutable :class:`BlueprintPlan`; it never
writes, synchronizes, stages snapshot edits, or creates catalog entries. ``plan.apply()`` executes
exactly that plan through the shared executor, checking the captured baselines first.
``engine.apply(...)`` is ``engine.plan(...).apply()``. ``dry_run=True`` runs the same execution path —
including the stale-plan, conflict, and staged-edit checks — but performs no write.

Execution phases (absent or unchanged phases are skipped): Inventory → discovery readiness →
topology membership/synchronization → topology commit (one ``InspectTransaction``) → module tags
(separate RPCs) → verification. Inventory and Inspect writes are separate operations; there is no
transaction spanning the whole deployment and no automatic rollback. Failures raise
:class:`BlueprintApplyError` carrying an :class:`ApplyResult` with every known id and phase outcome.
"""

from __future__ import annotations

import contextlib
import logging
import time
from collections.abc import Callable, Iterator, Mapping
from os import PathLike
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, PrivateAttr

from videoipath_automation_tool.apps.inspect.errors import InspectCommitConflictError, InspectCommitError
from videoipath_automation_tool.apps.inventory.errors import InventoryWriteNotAppliedError
from videoipath_automation_tool.apps.inventory.model.inventory_device import InventoryDevice
from videoipath_automation_tool.blueprints.errors import (
    BlueprintApplyError,
    BlueprintCapabilityError,
    BlueprintConflictError,
    BlueprintError,
    BlueprintTargetError,
    BlueprintValidationError,
    TopologyNotReadyError,
)
from videoipath_automation_tool.blueprints.inspect import (
    InspectGateway,
    TopologyWork,
    compute_topology_work,
    name_context,
    verify_topology,
)
from videoipath_automation_tool.blueprints.inventory import (
    InventoryGateway,
    InventoryWork,
    build_candidate,
    check_baseline,
    new_device,
    plan_inventory,
    recheck_conflicts,
    verify,
)
from videoipath_automation_tool.blueprints.models import (
    ApplyOptions,
    ApplyResult,
    Blueprint,
    BlueprintDevice,
    DeviceTarget,
    Diagnostic,
    InterfaceBinding,
    ModuleTarget,
    PhaseName,
    PhaseResult,
    PlannedOperation,
    PlannedPhase,
    Scope,
    TopologyTarget,
)
from videoipath_automation_tool.blueprints.naming import DEFAULT_NAMING, NamingScheme, render_name
from videoipath_automation_tool.blueprints.processors import (
    DriverContext,
    ProcessorRegistry,
    SourceFacts,
    VertexProcessor,
)
from videoipath_automation_tool.blueprints.resolution import ResolvedBlueprint, resolve_blueprint
from videoipath_automation_tool.validators.device_id import validate_device_id

# Sentinel for "argument not supplied" (distinct from an explicit None).
_UNSET: Any = object()


class BlueprintApp(Protocol):
    """The app interface the engine needs; :class:`VideoIPathApp` satisfies it unchanged."""

    @property
    def inventory(self) -> Any:
        """The Inventory app (``InventoryApp``)."""

    @property
    def inspect(self) -> Any:
        """The Inspect app (``InspectApp``)."""


class BlueprintPlan(BaseModel):
    """A reviewed, immutable preview of intended changes. ``apply()`` executes exactly this plan.

    ``fully_resolved`` is ``False`` when topology work depends on earlier phases (Inventory creation,
    topology-affecting Inventory changes, topology membership, or pending synchronization); that work
    is materialized during ``apply()`` from the captured configuration and recorded in the result.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    source_key: str
    scope: Scope
    inventory_variant: str | None = None
    topology_variant: str | None = None
    blueprint_digest: str
    driver_id: str | None = None
    driver_schema_version: str | None = None
    processor_type: str | None = None
    inventory_id: str | None = None
    topology_target: TopologyTarget | None = None
    phases: list[PlannedPhase]
    interface_bindings: list[InterfaceBinding]
    diagnostics: list[Diagnostic]
    skipped_sections: dict[str, str]
    fully_resolved: bool

    _captured: _Captured = PrivateAttr()
    _executor: _Executor = PrivateAttr()

    @property
    def has_changes(self) -> bool:
        return any(phase.status in ("planned", "deferred") for phase in self.phases)

    def phase(self, name: PhaseName) -> PlannedPhase | None:
        return next((phase for phase in self.phases if phase.name == name), None)

    def apply(self, *, dry_run: bool = False) -> ApplyResult:
        """Check the captured assumptions and execute this plan (no configuration overrides).

        With ``dry_run=True`` every check runs against current server state, but no write, topology
        action, or tag action is performed; the result reports the writes that would run
        (``status="planned"``). Deferred topology work needs earlier writes and is reported as
        ``deferred``.
        """
        return self._executor.execute(self, dry_run=dry_run)

    def summary(self) -> str:
        """Human-readable, redacted summary with before/after values and unresolved work."""
        header = f"Blueprint plan for '{self.source_key}' (scope={self.scope}"
        if self.inventory_variant:
            header += f", inventory={self.inventory_variant}"
        if self.topology_variant:
            header += f", topology={self.topology_variant}"
        lines = [header + f", digest={self.blueprint_digest[:12]})"]
        for phase in self.phases:
            line = f"{phase.name} [{phase.status}]"
            if phase.reason:
                line += f": {phase.reason}"
            lines.append(line)
            for operation in phase.operations:
                lines.append(f"  {operation.action} {operation.entity_kind} {operation.entity_id or '(new)'}")
                for change in operation.changes:
                    lines.append(f"    ~ {change.field}: {change.before!r} -> {change.after!r} ({change.source})")
        for binding in self.interface_bindings:
            lines.append(f"interface {binding.key} -> port {binding.port_id} ({binding.candidate})")
        for diagnostic in self.diagnostics:
            lines.append(f"[{diagnostic.level}] {diagnostic.code}: {diagnostic.message}")
        if not self.fully_resolved:
            lines.append(
                "Not fully resolved: deferred topology work is materialized during apply() after earlier phases; "
                "if it then fails validation, earlier phases remain applied and are reported."
            )
        return "\n".join(lines)

    def __repr__(self) -> str:
        statuses = ", ".join(f"{phase.name}={phase.status}" for phase in self.phases)
        return f"BlueprintPlan(source_key={self.source_key!r}, {statuses}, fully_resolved={self.fully_resolved})"

    __str__ = __repr__


class BlueprintEngine:
    """Standalone blueprint engine bound to one injected app for its lifetime.

    Only ``app`` is required. ``processors`` (id → class) are added to the built-ins, ``options`` and
    ``naming`` set engine-wide defaults; each has a post-initialization equivalent
    (:meth:`register_processor`, :meth:`configure`) with identical validation. Construction does
    not access app properties or the network. Every plan captures copies of its effective options,
    naming, and processor registrations; later configuration only affects future plans.
    """

    def __init__(
        self,
        app: BlueprintApp,
        *,
        processors: Mapping[str, type[VertexProcessor[Any]]] | None = None,
        options: ApplyOptions | None = None,
        naming: NamingScheme | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._app = app
        self._logger = logger or logging.getLogger("videoipath_automation_tool_blueprints")
        self._registry = ProcessorRegistry(processors)
        self._options = ApplyOptions()
        self._naming: NamingScheme | None = None
        self.configure(
            options=options if options is not None else _UNSET,
            naming=naming if naming is not None else _UNSET,
        )
        self._clock: Callable[[], float] = time.monotonic
        self._sleep: Callable[[float], None] = time.sleep

    # --- Configuration ---

    @property
    def app(self) -> BlueprintApp:
        return self._app

    @property
    def options(self) -> ApplyOptions:
        return self._options

    @property
    def naming(self) -> NamingScheme | None:
        return self._naming

    @property
    def registry(self) -> ProcessorRegistry:
        """A copy of this engine's registrations (mutating it does not affect the engine)."""
        return self._registry.copy()

    def register_processor(self, processor_id: str, processor_cls: type[VertexProcessor[Any]]) -> None:
        """Register a processor for this engine only; duplicate ids fail."""
        self._registry.register(processor_id, processor_cls)

    def configure(
        self,
        *,
        options: ApplyOptions | None = _UNSET,
        naming: NamingScheme | None = _UNSET,
    ) -> None:
        """Replace engine defaults. Omitted arguments keep the current defaults; a supplied model
        replaces that category; an explicit ``None`` resets it to the library defaults. Values are
        validated before anything changes."""
        if options is not _UNSET and options is not None and not isinstance(options, ApplyOptions):
            raise TypeError("options must be ApplyOptions or None.")
        if naming is not _UNSET and naming is not None and not isinstance(naming, NamingScheme):
            raise TypeError("naming must be a NamingScheme or None.")
        if options is not _UNSET:
            self._options = options.model_copy() if options is not None else ApplyOptions()
        if naming is not _UNSET:
            self._naming = naming.model_copy() if naming is not None else None

    def validate(self, blueprint: Blueprint | str | PathLike[str]) -> None:
        """Validate every variant of ``blueprint`` against this engine's processors (offline).

        Accepts a Blueprint instance or a YAML file path (string or path-like object).

        Raises:
            BlueprintValidationError: listing all issues, including unregistered processors.
        """
        self._load_blueprint(blueprint).validate_full(self._registry)

    def json_schema(self) -> dict[str, Any]:
        """Blueprint JSON Schema for this engine: ``processor_type`` is limited to the registered
        processors, and each one's ``params`` are described by its parameter schema."""
        return Blueprint.json_schema(registry=self._registry, restrict_processor_types=True)

    # --- Planning and application ---

    def plan(
        self,
        device: BlueprintDevice,
        blueprint: Blueprint | str | PathLike[str],
        *,
        scope: Scope = "all",
        inventory_variant: str = "default",
        topology_variant: str = "default",
        naming: NamingScheme | None = None,
        options: ApplyOptions | None = None,
    ) -> BlueprintPlan:
        """Load/resolve the blueprint, read current state, and compute changes. Read-only.

        ``blueprint`` accepts a Blueprint instance or a YAML file path (string or path-like
        object). Files are loaded once during planning; applying the plan never re-reads them.
        Use ``Blueprint.from_yaml(text)`` for raw YAML strings.
        """
        if not isinstance(device, BlueprintDevice):
            raise TypeError("device must be a BlueprintDevice.")
        if naming is not None and not isinstance(naming, NamingScheme):
            raise TypeError("naming must be a NamingScheme.")
        if options is not None and not isinstance(options, ApplyOptions):
            raise TypeError("options must be ApplyOptions.")

        device = device.model_copy(deep=True)
        blueprint = self._load_blueprint(blueprint).model_copy(deep=True)
        registry = self._registry.copy()
        effective_options = options or self._options
        resolved = resolve_blueprint(
            blueprint,
            scope=scope,
            inventory_variant=inventory_variant,
            topology_variant=topology_variant,
            registry=registry,
            overrides=device.inventory_overrides,
        )
        captured = _Captured(
            device=device,
            resolved=resolved,
            naming=NamingScheme.layered(DEFAULT_NAMING, self._naming, resolved.naming, naming),
            options=effective_options,
            registry=registry,
        )
        return _Planner(self._app, captured, scope, self._executor()).build()

    def apply(
        self,
        device: BlueprintDevice,
        blueprint: Blueprint | str | PathLike[str],
        *,
        scope: Scope = "all",
        inventory_variant: str = "default",
        topology_variant: str = "default",
        naming: NamingScheme | None = None,
        options: ApplyOptions | None = None,
        dry_run: bool = False,
    ) -> ApplyResult:
        """Load/plan and apply; identical to ``self.plan(...).apply(dry_run=dry_run)``.

        Accepts the same Blueprint instance or YAML file path as :meth:`plan`.
        """
        return self.plan(
            device,
            blueprint,
            scope=scope,
            inventory_variant=inventory_variant,
            topology_variant=topology_variant,
            naming=naming,
            options=options,
        ).apply(dry_run=dry_run)

    def __repr__(self) -> str:
        return f"BlueprintEngine(processors={self._registry.ids()}, options={self._options!r})"

    # --- Internal ---

    @staticmethod
    def _load_blueprint(blueprint: Blueprint | str | PathLike[str]) -> Blueprint:
        if isinstance(blueprint, Blueprint):
            return blueprint
        if isinstance(blueprint, (str, PathLike)):
            return Blueprint.load(blueprint)
        raise TypeError("blueprint must be a Blueprint instance or a YAML file path (str or PathLike[str]).")

    def _executor(self) -> _Executor:
        return _Executor(self._app, clock=self._clock, sleep=self._sleep, logger=self._logger)


# --- Internal: captured inputs ---


class _Captured(BaseModel):
    """Copies of everything a plan needs to execute, including deferred phases."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    device: BlueprintDevice
    resolved: ResolvedBlueprint
    naming: NamingScheme
    options: ApplyOptions
    registry: ProcessorRegistry
    inventory_work: InventoryWork | None = None
    topology_target: TopologyTarget | None = None
    topology_work: TopologyWork | None = None
    topology_deferred: bool = False

    @property
    def source(self) -> SourceFacts:
        device = self.device
        return SourceFacts(
            key=device.key,
            label=device.label,
            description=device.description,
            module_position=device.module_position,
            attributes=device.model_dump(mode="json")["attributes"],
        )


# --- Internal: planning ---


class _Planner:
    def __init__(self, app: BlueprintApp, captured: _Captured, scope: Scope, executor: _Executor) -> None:
        self._app = app
        self._captured = captured
        self._scope = scope
        self._executor = executor
        self._inventory_gateway: InventoryGateway | None = None

    def build(self) -> BlueprintPlan:
        captured = self._captured
        resolved = captured.resolved
        phases: list[PlannedPhase] = []
        diagnostics: list[Diagnostic] = []

        inventory_work, current = self._plan_inventory(phases)
        target, deferred_reason, topology_work = self._plan_topology(inventory_work, current, phases, diagnostics)

        captured = captured.model_copy(
            update={
                "inventory_work": inventory_work,
                "topology_target": target,
                "topology_work": topology_work,
                "topology_deferred": deferred_reason is not None,
            }
        )
        plan = BlueprintPlan(
            source_key=captured.device.key,
            scope=self._scope,
            inventory_variant=resolved.inventory.variant if resolved.inventory else None,
            topology_variant=resolved.topology.variant if resolved.topology else None,
            blueprint_digest=resolved.digest,
            driver_id=resolved.inventory.driver_id if resolved.inventory else None,
            driver_schema_version=resolved.inventory.schema_version if resolved.inventory else None,
            processor_type=resolved.topology.processor_id if resolved.topology else None,
            inventory_id=captured.device.inventory_id,
            topology_target=target,
            phases=phases,
            interface_bindings=list(topology_work.bindings) if topology_work else [],
            diagnostics=diagnostics + (list(topology_work.diagnostics) if topology_work else []),
            skipped_sections=dict(resolved.skipped),
            fully_resolved=deferred_reason is None,
        )
        plan._captured = captured
        plan._executor = self._executor
        return plan

    def _plan_inventory(self, phases: list[PlannedPhase]) -> tuple[InventoryWork | None, InventoryDevice | None]:
        resolved = self._captured.resolved
        if resolved.inventory is None:
            phases.append(PlannedPhase(name="inventory", status="skipped", reason=resolved.skipped.get("inventory")))
            return None, None
        naming = self._captured.naming
        context = name_context(self._captured.source)
        label = render_name("inventory_label", naming.inventory_label, context) if naming.inventory_label else None
        description = (
            render_name("inventory_description", naming.inventory_description, context)
            if naming.inventory_description
            else None
        )
        work, current = plan_inventory(
            self._inventory(),
            resolved.inventory,
            self._captured.device,
            label=label,
            description=description,
            write_credentials=self._captured.options.write_credentials,
        )
        operation = work.operation
        phases.append(
            PlannedPhase(
                name="inventory",
                status="planned" if operation else "no_change",
                operations=[operation] if operation else [],
            )
        )
        return work, current

    def _plan_topology(
        self,
        inventory_work: InventoryWork | None,
        current: InventoryDevice | None,
        phases: list[PlannedPhase],
        diagnostics: list[Diagnostic],
    ) -> tuple[TopologyTarget | None, str | None, TopologyWork | None]:
        captured = self._captured
        resolved = captured.resolved
        if resolved.topology is None:
            reason = resolved.skipped.get("topology")
            phases.extend(PlannedPhase(name=name, status="skipped", reason=reason) for name in _TOPOLOGY_PHASES)
            return None, None, None

        device = captured.device
        target: TopologyTarget | None = device.topology
        if target is None and device.inventory_id is not None:
            target = DeviceTarget(device_id=device.inventory_id)
        creating = inventory_work is not None and inventory_work.action == "create"
        if target is None and not creating:
            raise BlueprintTargetError(
                f"Topology configuration for '{device.key}' needs an explicit 'topology' target or an 'inventory_id'."
            )

        reason: str | None = None
        if target is None:
            reason = "the topology device is the Inventory record created by this plan"
        elif inventory_work is not None and inventory_work.affects_topology:
            reason = "planned Inventory changes may alter the discovered topology"
        else:
            reason = self._membership_reason(target, diagnostics)

        if reason is not None:
            phases.extend(PlannedPhase(name=name, status="deferred", reason=reason) for name in _TOPOLOGY_PHASES)
            return target, reason, None

        assert target is not None
        work = self._materialize(target, current)
        phases.append(PlannedPhase(name="discovery", status="skipped", reason="topology already present"))
        phases.append(PlannedPhase(name="topology_sync", status="no_change"))
        phases.append(
            PlannedPhase(
                name="topology",
                status="planned" if work.has_topology_writes else "no_change",
                operations=work.topology_operations,
            )
        )
        phases.append(
            PlannedPhase(
                name="module_tags",
                status="planned" if work.has_module_writes else ("no_change" if work.module_id else "skipped"),
                reason=None if work.module_id else "device target",
                operations=work.module_operations,
            )
        )
        return target, None, work

    def _membership_reason(self, target: TopologyTarget, diagnostics: list[Diagnostic]) -> str | None:
        sync = self._captured.options.sync
        gateway = InspectGateway(self._app.inspect)
        if not gateway.in_topology(target.device_id):
            if sync == "none" or isinstance(target, ModuleTarget):
                raise BlueprintTargetError(
                    f"Inspect device '{target.device_id}' is not in the topology"
                    + (
                        " (sync='none')."
                        if sync == "none"
                        else "; a module target requires its device in the topology."
                    )
                )
            return "the device must first be added to the topology"
        info = gateway.sync_info(target.device_id)
        if not _sync_pending(info):
            return None
        if sync == "none" or isinstance(target, ModuleTarget):
            # A module target never synchronizes its whole parent device implicitly.
            diagnostics.append(
                Diagnostic(
                    level="warning",
                    code="topology.sync_pending",
                    message="Synchronization is pending but not performed (sync='none' or a module target); "
                    "planned against the current topology.",
                    entity_id=target.device_id,
                )
            )
            return None
        if sync == "add_only" and (info.update or info.remove):
            raise BlueprintCapabilityError(
                f"Synchronizing '{target.device_id}' requires updates/removals; sync='add_only' is insufficient "
                "(use sync='reconcile' deliberately, or synchronize through the Inspect API)."
            )
        return "topology synchronization is pending"

    def _materialize(self, target: TopologyTarget, current: InventoryDevice | None) -> TopologyWork:
        return _materialize_topology(self._app, self._captured, target, self._inventory, current)

    def _inventory(self) -> InventoryGateway:
        if self._inventory_gateway is None:
            self._inventory_gateway = InventoryGateway(self._app.inventory)
        return self._inventory_gateway


def _materialize_topology(
    app: BlueprintApp,
    captured: _Captured,
    target: TopologyTarget,
    inventory: Callable[[], InventoryGateway],
    current: InventoryDevice | None,
) -> TopologyWork:
    """Collect a fresh scoped context and compute exact topology edits from the captured configuration."""
    assert captured.resolved.topology is not None
    scope = InspectGateway(app.inspect).read_scope(target)
    own = _driver_context(current) if current is not None else None
    owner = (
        own if own is not None and own.inventory_id == target.device_id else _owner_context(inventory, target.device_id)
    )
    return compute_topology_work(
        scope=scope,
        resolved=captured.resolved.topology,
        naming=captured.naming,
        source=captured.source,
        owner=owner,
        inventory=own,
        allow_label_collisions=captured.options.naming_collisions == "allow",
    )


# --- Internal: execution ---


class _Executor:
    """Executes plans through the bound app; uses only the plan's captured settings."""

    def __init__(
        self, app: BlueprintApp, *, clock: Callable[[], float], sleep: Callable[[float], None], logger: logging.Logger
    ) -> None:
        self._app = app
        self._clock = clock
        self._sleep = sleep
        self._logger = logger

    def execute(self, plan: BlueprintPlan, *, dry_run: bool = False) -> ApplyResult:
        return _Execution(self, plan, dry_run=dry_run).run()


class _Execution:
    def __init__(self, executor: _Executor, plan: BlueprintPlan, *, dry_run: bool) -> None:
        self._executor = executor
        self._app = executor._app
        self._plan = plan
        self._captured: _Captured = plan._captured
        self._dry_run = dry_run
        self._would_write = False
        self._result = ApplyResult(source_key=plan.source_key, inventory_id=plan.inventory_id, dry_run=dry_run)
        self._phases: dict[str, PhaseResult] = {
            phase.name: PhaseResult(
                name=phase.name,
                status=phase.status if phase.status in ("skipped", "no_change") else "not_run",
                message=phase.reason if phase.status == "skipped" else None,
            )
            for phase in plan.phases
        }
        self._phases["verification"] = PhaseResult(name="verification", status="not_run")
        self._current: str | None = None
        self._unknown = False
        self._wrote: list[str] = []
        self._mismatches: list[str] = []
        self._verification_errors: list[str] = []
        self._inventory_gateway: InventoryGateway | None = None
        self._current_inventory: InventoryDevice | None = None
        self._topology_readback_done = False

    def run(self) -> ApplyResult:
        try:
            self._run_inventory()
            if self._captured.resolved.topology is not None:
                self._run_topology()
        except Exception as exc:  # noqa: BLE001
            self._fail(exc)
        self._finish()
        return self._result

    # --- Phases ---

    def _run_inventory(self) -> None:
        work = self._captured.inventory_work
        if work is None:
            return
        phase = self._enter("inventory")
        gateway = self._inventory()
        if work.action == "none":
            phase.status = "no_change"
            return
        if work.action == "create":
            recheck_conflicts(gateway, self._captured.device, work)
            candidate = build_candidate(new_device(work.driver_id), work.desired)
            if self._dry_run:
                self._planned(phase, [work.operation])
                return
            with self._write(create=True):
                online = gateway.create(candidate)
            self._result.inventory_id = online.device_id
        else:
            assert work.inventory_id is not None
            fresh = gateway.read(work.inventory_id)
            check_baseline(work, fresh)
            if self._dry_run:
                self._planned(phase, [work.operation])
                return
            with self._write():
                online = gateway.update(build_candidate(fresh, work.desired))
        self._current_inventory = online
        self._mismatches.extend(f"inventory.{field}" for field in verify(online, work.desired))
        phase.status = "completed"
        phase.operations = [work.operation] if work.operation else []
        phase.message = f"Inventory record '{online.device_id}'"
        self._wrote.append("inventory")

    def _run_topology(self) -> None:
        captured = self._captured
        if captured.topology_deferred and self._dry_run:
            reason = self._plan.phase("topology").reason if self._plan.phase("topology") else None
            for name in _TOPOLOGY_PHASES:
                phase = self._enter(name)
                phase.status = "deferred"
                phase.message = f"not run in a dry run: {reason}"
            self._would_write = True
            return
        target = captured.topology_target
        if target is None:
            if self._result.inventory_id is None:
                raise BlueprintTargetError("No topology target: the Inventory record id is unknown.")
            target = DeviceTarget(device_id=self._result.inventory_id)
        self._result.topology_device_id = target.device_id
        self._result.module_id = target.module_id if isinstance(target, ModuleTarget) else None
        gateway = InspectGateway(self._app.inspect)

        if captured.topology_deferred:
            work = self._discover_and_materialize(gateway, target)
            self._result.materialized = True
        else:
            assert captured.topology_work is not None
            work = captured.topology_work
            self._enter("topology")
            if gateway.read_scope(target).fingerprint != work.fingerprint:
                raise BlueprintConflictError(
                    f"The topology of {_target_label(target)} changed since planning; create a new plan."
                )
        self._result.interface_bindings = list(work.bindings)
        self._result.diagnostics.extend(work.diagnostics)

        overlap = gateway.staged_edit_keys() & work.touched_keys()
        if overlap:
            entities = ", ".join(f"{kind} '{entity_id}'" for kind, entity_id in sorted(overlap))
            raise BlueprintConflictError(
                f"Pending uncommitted Inspect edits overlap this plan ({entities}); commit or discard them first."
            )

        phase = self._enter("topology")
        if work.has_topology_writes and self._dry_run:
            self._planned(phase, work.topology_operations)
        elif work.has_topology_writes:
            with self._write():
                gateway.commit(work)
            phase.status = "completed"
            phase.operations = list(work.topology_operations)
            self._wrote.append("topology")
        else:
            phase.status = "no_change"

        self._run_module_tags(gateway, work)
        if "topology" in self._wrote or "module_tags" in self._wrote:
            try:
                self._mismatches.extend(verify_topology(gateway.read_scope(target), work))
            except Exception as exc:  # noqa: BLE001 - verification never turns an applied write into a failure
                self._verification_errors.append(f"topology read-back failed: {type(exc).__name__}: {exc}")
            finally:
                self._topology_readback_done = True

    def _run_module_tags(self, gateway: InspectGateway, work: TopologyWork) -> None:
        phase = self._enter("module_tags")
        if work.module_id is None:
            phase.status = "skipped"
            phase.message = "device target"
            return
        if not work.has_module_writes:
            phase.status = "no_change"
            return
        current = gateway.module_local_tags(work.device_id, work.module_id)
        if work.module_tag_baseline is not None and set(current or ()) != set(work.module_tag_baseline):
            raise BlueprintConflictError(
                f"Local tags of module '{work.module_id}' changed since planning; the tag phase was not applied."
            )
        if self._dry_run:
            self._planned(phase, work.module_operations)
            return
        for operation in work.module_operations:
            tag = operation.changes[0].after
            with self._write():
                if operation.action == "assign_tag":
                    gateway.assign_tag(tag, work.module_id)
                else:
                    gateway.unassign_tag(tag, work.module_id)
            phase.operations.append(operation)
            if "module_tags" not in self._wrote:
                self._wrote.append("module_tags")
        gateway.refresh_device(work.device_id)
        phase.status = "completed"

    def _discover_and_materialize(self, gateway: InspectGateway, target: TopologyTarget) -> TopologyWork:
        options = self._captured.options
        discovery = self._enter("discovery")
        deadline = self._executor._clock() + options.discovery_timeout
        sync_phase = self._phases["topology_sync"]
        sync_phase.status = "no_change"
        while True:
            try:
                self._ensure_membership(gateway, target)
                self._enter("topology")
                work = _materialize_topology(
                    self._app, self._captured, target, self._inventory, self._current_inventory
                )
                discovery.status = "completed"
                return work
            except TopologyNotReadyError as exc:
                if self._unknown:
                    raise
                remaining = deadline - self._executor._clock()
                if remaining <= 0:
                    self._current = "discovery"
                    raise TopologyNotReadyError(
                        f"Topology not ready after {options.discovery_timeout:g}s: {exc}"
                    ) from exc
                self._executor._sleep(min(options.poll_interval, remaining))

    def _ensure_membership(self, gateway: InspectGateway, target: TopologyTarget) -> None:
        sync = self._captured.options.sync
        phase = self._enter("topology_sync")
        if isinstance(target, ModuleTarget):
            # Never add or synchronize a whole parent device to reach a module target.
            if not gateway.in_topology(target.device_id):
                raise BlueprintTargetError(
                    f"Parent device '{target.device_id}' of module '{target.module_id}' is not in the topology."
                )
            return
        if not gateway.in_topology(target.device_id):
            if sync == "none":
                raise BlueprintTargetError(f"Inspect device '{target.device_id}' is not in the topology (sync='none').")
            with self._write():
                gateway.add_to_topology(target.device_id)
            self._record_sync(phase, "add_to_topology", target.device_id)
        info = gateway.sync_info(target.device_id)
        if not _sync_pending(info) or sync == "none":
            return
        if sync == "add_only" and (info.update or info.remove):
            raise BlueprintCapabilityError(
                f"Synchronizing '{target.device_id}' requires updates/removals; sync='add_only' is insufficient."
            )
        with self._write():
            gateway.sync(target.device_id, add_only=sync == "add_only")
        self._record_sync(phase, "sync", target.device_id)

    def _record_sync(self, phase: PhaseResult, action: str, device_id: str) -> None:
        phase.operations.append(PlannedOperation(action=action, entity_kind="device", entity_id=device_id))  # type: ignore[arg-type]
        phase.status = "completed"
        if "topology_sync" not in self._wrote:
            self._wrote.append("topology_sync")

    # --- Bookkeeping ---

    def _planned(self, phase: PhaseResult, operations: list[PlannedOperation | None]) -> None:
        """Dry run: record the writes that would run instead of performing them."""
        phase.status = "planned"
        phase.operations = [operation for operation in operations if operation is not None]
        phase.message = "dry run: not applied"
        self._would_write = True

    def _enter(self, name: str) -> PhaseResult:
        self._current = name
        phase = self._phases.setdefault(name, PhaseResult(name=name, status="not_run"))  # type: ignore[arg-type]
        return phase

    @contextlib.contextmanager
    def _write(self, *, create: bool = False) -> Iterator[None]:
        """Mark a server write; an unexpected exception means the outcome is unknown."""
        try:
            yield
        except Exception as exc:
            self._unknown = not _known_rejection(exc, create=create)
            raise

    def _fail(self, exc: Exception) -> None:
        name = self._current or "inventory"
        phase = self._phases.setdefault(name, PhaseResult(name=name, status="not_run"))  # type: ignore[arg-type]
        phase.status = "unknown" if self._unknown else "failed"
        phase.message = f"{type(exc).__name__}: {exc}"
        if self._unknown:
            self._result.status = "unknown"
        elif self._wrote:
            self._result.status = "partial"
        else:
            self._result.status = "failed"
        self._error = exc

    def _finish(self) -> None:
        result = self._result
        if self._wrote:
            verification = self._phases["verification"]
            if ("topology" in self._wrote or "module_tags" in self._wrote) and not self._topology_readback_done:
                self._verification_errors.append("topology read-back did not run")
            if self._mismatches or self._verification_errors:
                result.verification = "unconfirmed"
                result.verification_detail = "; ".join(
                    ([f"read-back differs for {', '.join(self._mismatches)}"] if self._mismatches else [])
                    + self._verification_errors
                )
            else:
                result.verification = "confirmed"
            verification.status = "completed"
        else:
            self._phases["verification"].status = "skipped"
        result.phases = [self._phases[name] for name in _PHASE_ORDER if name in self._phases]
        error = getattr(self, "_error", None)
        if error is not None:
            self._executor._logger.warning(
                "Blueprint apply for '%s' ended %s: %s", result.source_key, result.status, error
            )
            raise BlueprintApplyError(result, f"{type(error).__name__}: {error}") from error
        if self._dry_run:
            result.verification_detail = "dry run: nothing was written"
            result.status = "planned" if self._would_write else "no_change"
        else:
            result.status = "succeeded" if self._wrote else "no_change"
        self._executor._logger.info("Blueprint apply for '%s' %s.", result.source_key, result.status)

    def _inventory(self) -> InventoryGateway:
        if self._inventory_gateway is None:
            self._inventory_gateway = InventoryGateway(self._app.inventory)
        return self._inventory_gateway


# --- Internal helpers ---

_TOPOLOGY_PHASES: tuple[PhaseName, ...] = ("discovery", "topology_sync", "topology", "module_tags")
_PHASE_ORDER: tuple[str, ...] = ("inventory", "discovery", "topology_sync", "topology", "module_tags", "verification")


def _known_rejection(exc: Exception, *, create: bool) -> bool:
    """Whether a write error proves the server did not apply the change."""
    if isinstance(exc, (InspectCommitError, InspectCommitConflictError, BlueprintError)):
        return True
    if isinstance(exc, InventoryWriteNotAppliedError):
        # A create is only known to be rejected when the add itself failed: the follow-up update
        # (tracking-id cleanup) runs after the record already exists.
        return exc.operation == "add" if create else True
    return False


def _sync_pending(info: Any) -> bool:
    return info is not None and bool(info.add or info.update or info.remove)


def _target_label(target: TopologyTarget) -> str:
    if isinstance(target, ModuleTarget):
        return f"module '{target.module_id}' of device '{target.device_id}'"
    return f"device '{target.device_id}'"


def _driver_context(device: InventoryDevice) -> DriverContext:
    return DriverContext(
        inventory_id=device.device_id,
        driver_id=device.driver_id,
        address=device.configuration.config.cinfo.address or None,
        custom_settings=device.configuration.config.customSettings.model_dump(mode="json", exclude={"driver_id"}),
    )


def _owner_context(inventory: Callable[[], InventoryGateway], device_id: str) -> DriverContext | None:
    try:
        validate_device_id(device_id)
    except ValueError:
        return None  # e.g. virtual devices have no Inventory record
    try:
        return _driver_context(inventory().read(device_id))
    except (BlueprintTargetError, BlueprintValidationError):
        return None


BlueprintPlan.model_rebuild()

__all__ = ["BlueprintApp", "BlueprintEngine", "BlueprintPlan"]
