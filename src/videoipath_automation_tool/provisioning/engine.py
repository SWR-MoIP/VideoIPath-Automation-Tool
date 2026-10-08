"""The standalone :class:`ProvisioningEngine`: configuration, read-only planning, and execution.

``engine.plan(...)`` reads VideoIPath state and returns an immutable :class:`ProvisioningPlan`; it never
writes, synchronizes, stages snapshot edits, or creates catalog entries. ``plan.apply()`` executes
exactly that plan through the shared executor, checking the captured baselines first.
``engine.apply(...)`` is ``engine.plan(...).apply()``. ``dry_run=True`` runs the same execution path —
including the stale-plan, conflict, and staged-edit checks — but performs no write.

A topology-affecting Inventory update (address, alternate addresses, credentials, generic or custom
settings, or ``active``) stops after Inventory. The result is ``partial`` with ``replan_required``;
plan again after the driver has rediscovered the device. Creating a record still waits for discovery
during apply, because a new device has no previous topology.

Execution phases (absent or unchanged phases are skipped): Inventory → Inventory reachability →
topology membership/synchronization → required topology data → topology commit (one ``InspectTransaction``) → module tags
(separate RPCs) → verification. Inventory and Inspect writes are separate operations; there is no
transaction spanning the whole deployment and no automatic rollback. Failures raise
:class:`ProvisioningApplyError` carrying an :class:`ApplyResult` with every known id and phase outcome.
"""

from __future__ import annotations

import contextlib
import logging
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from os import PathLike
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, JsonValue, PrivateAttr

from videoipath_automation_tool.apps.inspect.errors import InspectCommitConflictError, InspectCommitError
from videoipath_automation_tool.apps.inspect.model.actions import InspectApiLookupSyncInfoItem
from videoipath_automation_tool.apps.inventory.errors import InventoryWriteNotAppliedError
from videoipath_automation_tool.apps.inventory.model.inventory_device import InventoryDevice
from videoipath_automation_tool.provisioning.errors import (
    InventoryNotReadyError,
    ProvisioningApplyError,
    ProvisioningCapabilityError,
    ProvisioningConflictError,
    ProvisioningError,
    ProvisioningTargetError,
    ProvisioningValidationError,
    TopologyNotReadyError,
)
from videoipath_automation_tool.provisioning.inspect import (
    InspectGateway,
    ScopeData,
    TopologyWork,
    compute_topology_work,
    name_context,
    verify_topology,
)
from videoipath_automation_tool.provisioning.inventory import (
    InventoryGateway,
    InventoryWork,
    build_candidate,
    check_baseline,
    new_device,
    plan_inventory,
    recheck_conflicts,
    verify,
)
from videoipath_automation_tool.provisioning.models import (
    ApplyOptions,
    ApplyResult,
    Blueprint,
    DeviceTarget,
    Diagnostic,
    EdgeState,
    InterfaceBinding,
    ModuleTarget,
    PhaseName,
    PhaseResult,
    PlannedOperation,
    PlannedPhase,
    PortBinding,
    ProvisioningDevice,
    Scope,
    TopologyTarget,
)
from videoipath_automation_tool.provisioning.naming import (
    DEFAULT_NAMING,
    INVENTORY_NAMING_ENTRIES,
    TOPOLOGY_NAMING_ENTRIES,
    NamingScheme,
    render_name,
    validate_naming_inputs,
)
from videoipath_automation_tool.provisioning.processors import (
    DriverContext,
    ProcessorRegistry,
    SourceFacts,
    VertexProcessor,
)
from videoipath_automation_tool.provisioning.resolution import ResolvedBlueprint, resolve_blueprint
from videoipath_automation_tool.validators.device_id import validate_device_id

# Sentinel for "argument not supplied" (distinct from an explicit None).
_UNSET: Any = object()


class ProvisioningApp(Protocol):
    """The app interface the engine needs; :class:`VideoIPathApp` satisfies it unchanged."""

    @property
    def inventory(self) -> Any:
        """The Inventory app (``InventoryApp``)."""

    @property
    def inspect(self) -> Any:
        """The Inspect app (``InspectApp``)."""


class ProvisioningPlan(BaseModel):
    """A reviewed, immutable preview of intended changes. ``apply()`` executes exactly this plan.

    ``fully_resolved`` is ``False`` when topology work depends on earlier phases or peers are missing. Inventory creation,
    topology membership, and pending synchronization are materialized during ``apply()`` from the
    captured configuration. A topology-affecting Inventory update is not: ``apply()`` stops after
    Inventory and the result asks for a new plan. Missing peers stay deferred until a new plan;
    the remaining local configuration and resolvable edges can still be applied.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    source_key: str
    scope: Scope
    variants: tuple[str, ...] = ()
    blueprint_digest: str
    driver_id: str | None = None
    driver_schema_version: str | None = None
    processor_type: str | None = None
    inventory_id: str | None = None
    topology_target: TopologyTarget | None = None
    phases: list[PlannedPhase]
    interface_bindings: list[InterfaceBinding]
    port_bindings: list[PortBinding] = Field(default_factory=list)
    edges: list[EdgeState] = Field(default_factory=list)
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
        (``status="planned"``). Deferred topology work that still needs earlier writes is reported as
        ``deferred``.

        A topology-affecting Inventory update stops after Inventory on a real run (``status="partial"``,
        ``replan_required=True``) and does not raise. A dry run of that plan reports the same phases as
        ``deferred`` and sets ``replan_required``.
        """
        return self._executor.execute(self, dry_run=dry_run)

    def summary(self) -> str:
        """Human-readable, redacted summary with before/after values and unresolved work."""
        header = f"Blueprint plan for '{self.source_key}' (scope={self.scope}"
        if self.variants:
            header += f", variants={list(self.variants)}"
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
        for binding in self.port_bindings:
            lines.append(f"port {binding.key} -> {binding.port_id} ({binding.candidate})")
        for edge in self.edges:
            lines.append(f"edge {edge.index} [{edge.status}]: " + (edge.reason or ", ".join(edge.edge_ids)))
        for diagnostic in self.diagnostics:
            lines.append(f"[{diagnostic.level}] {diagnostic.code}: {diagnostic.message}")
        if not self.fully_resolved:
            if any(edge.status == "deferred" for edge in self.edges) and not self._captured.topology_deferred:
                lines.append("Edges remain open: create a new plan when the peer topology is available.")
            elif self._captured.topology_requires_replan:
                lines.append(
                    "Not fully resolved: apply stops after Inventory; replan once the driver has rediscovered "
                    "the device."
                )
            else:
                lines.append(
                    "Not fully resolved: deferred topology work is materialized during apply() after earlier phases; "
                    "if it then fails validation, earlier phases remain applied and are reported."
                )
        return "\n".join(lines)

    def __repr__(self) -> str:
        statuses = ", ".join(f"{phase.name}={phase.status}" for phase in self.phases)
        return f"ProvisioningPlan(source_key={self.source_key!r}, {statuses}, fully_resolved={self.fully_resolved})"

    __str__ = __repr__


class ProvisioningEngine:
    """Standalone provisioning engine bound to one injected app for its lifetime.

    Only ``app`` is required. ``processors`` (id → class) are added to the built-ins, ``options`` and
    ``naming`` set engine-wide defaults; each has a post-initialization equivalent
    (:meth:`register_processor`, :meth:`configure`) with identical validation. Construction does
    not access app properties or the network. Every plan captures copies of its effective options,
    naming, and processor registrations; later configuration only affects future plans.
    """

    def __init__(
        self,
        app: ProvisioningApp,
        *,
        processors: Mapping[str, type[VertexProcessor[Any]]] | None = None,
        options: ApplyOptions | None = None,
        naming: NamingScheme | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._app = app
        self._logger = logger or logging.getLogger("videoipath_automation_tool_provisioning")
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
    def app(self) -> ProvisioningApp:
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

    def validate(
        self,
        blueprint: Blueprint | str | PathLike[str],
        *,
        inputs: Mapping[str, JsonValue] | None = None,
        variants: Sequence[str] | None = None,
    ) -> None:
        """Validate defaults and individual variants, or an explicit combination, offline.

        Accepts a Blueprint instance or a YAML file path (string or path-like object).
        ``inputs`` binds declared values; ``variants`` selects one ordered combination.

        Raises:
            ProvisioningValidationError: listing all issues, including unregistered processors.
        """
        self._load_blueprint(blueprint).validate_full(self._registry, inputs=inputs, variants=variants)

    def json_schema(self) -> dict[str, Any]:
        """Blueprint JSON Schema for this engine: ``processor_type`` is limited to the registered
        processors, and each one's ``params`` are described by its parameter schema."""
        return Blueprint.json_schema(registry=self._registry, restrict_processor_types=True)

    # --- Planning and application ---

    def plan(
        self,
        device: ProvisioningDevice,
        blueprint: Blueprint | str | PathLike[str],
        *,
        scope: Scope = "all",
        inputs: Mapping[str, JsonValue] | None = None,
        variants: Sequence[str] = (),
        naming: NamingScheme | None = None,
        options: ApplyOptions | None = None,
    ) -> ProvisioningPlan:
        """Load/resolve the blueprint, read current state, and compute changes. Read-only.

        ``blueprint`` accepts a Blueprint instance or a YAML file path (string or path-like
        object). Files are loaded once during planning; applying the plan never re-reads them.
        Use ``Blueprint.from_yaml(text)`` for raw YAML strings.
        """
        if not isinstance(device, ProvisioningDevice):
            raise TypeError("device must be a ProvisioningDevice.")
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
            inputs=inputs,
            variants=variants,
            registry=registry,
            overrides=device.inventory_overrides,
        )
        if device.edges and scope != "inventory":
            if resolved.topology is None:
                raise ProvisioningValidationError("Edges require a topology section in the selected configuration.")
            keys = set(resolved.topology.config.ip_vertex_mapping or {}) | set(
                resolved.topology.config.port_mapping or {}
            )
            for edge in device.edges:
                if isinstance(edge.local, str) and edge.local not in keys:
                    raise ProvisioningValidationError(f"Unknown local port mapping '{edge.local}'.")
        captured = _Captured(
            device=device,
            resolved=resolved,
            naming=NamingScheme.layered(DEFAULT_NAMING, self._naming, resolved.naming, naming),
            options=effective_options,
            registry=registry,
        )
        active_naming = (INVENTORY_NAMING_ENTRIES if resolved.inventory else frozenset()) | (
            TOPOLOGY_NAMING_ENTRIES if resolved.topology else frozenset()
        )
        validate_naming_inputs(captured.naming, blueprint.inputs, resolved.inputs, entries=active_naming)
        return _Planner(self._app, captured, scope, self._executor()).build()

    def apply(
        self,
        device: ProvisioningDevice,
        blueprint: Blueprint | str | PathLike[str],
        *,
        scope: Scope = "all",
        inputs: Mapping[str, JsonValue] | None = None,
        variants: Sequence[str] = (),
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
            inputs=inputs,
            variants=variants,
            naming=naming,
            options=options,
        ).apply(dry_run=dry_run)

    def __repr__(self) -> str:
        return f"ProvisioningEngine(processors={self._registry.ids()}, options={self._options!r})"

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

    device: ProvisioningDevice
    resolved: ResolvedBlueprint
    naming: NamingScheme
    options: ApplyOptions
    registry: ProcessorRegistry
    inventory_work: InventoryWork | None = None
    topology_target: TopologyTarget | None = None
    topology_work: TopologyWork | None = None
    topology_deferred: bool = False
    topology_requires_replan: bool = False
    edge_peers: dict[int, ScopeData | None] = Field(default_factory=dict)

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
    def __init__(self, app: ProvisioningApp, captured: _Captured, scope: Scope, executor: _Executor) -> None:
        self._app = app
        self._captured = captured
        self._scope = scope
        self._executor = executor
        self._inventory_gateway: InventoryGateway | None = None

    def build(self) -> ProvisioningPlan:
        captured = self._captured
        resolved = captured.resolved
        phases: list[PlannedPhase] = []
        diagnostics: list[Diagnostic] = []

        if resolved.topology is not None and captured.device.edges:
            captured = captured.model_copy(
                update={"edge_peers": InspectGateway(self._app.inspect).read_edge_peers(captured.device.edges)}
            )
            self._captured = captured

        inventory_work, current = self._plan_inventory(phases)
        target, deferred_reason, topology_work, topology_requires_replan = self._plan_topology(
            inventory_work, current, phases, diagnostics
        )

        captured = captured.model_copy(
            update={
                "inventory_work": inventory_work,
                "topology_target": target,
                "topology_work": topology_work,
                "topology_deferred": deferred_reason is not None,
                "topology_requires_replan": topology_requires_replan,
            }
        )
        plan = ProvisioningPlan(
            source_key=captured.device.key,
            scope=self._scope,
            variants=resolved.variants,
            blueprint_digest=resolved.digest,
            driver_id=resolved.inventory.driver_id if resolved.inventory else None,
            driver_schema_version=resolved.inventory.schema_version if resolved.inventory else None,
            processor_type=resolved.topology.processor_id if resolved.topology else None,
            inventory_id=captured.device.inventory_id,
            topology_target=target,
            phases=phases,
            interface_bindings=list(topology_work.bindings) if topology_work else [],
            port_bindings=list(topology_work.port_bindings) if topology_work else [],
            edges=[state.model_copy(deep=True) for state in topology_work.edge_work.states]
            if topology_work
            else [
                EdgeState(index=index, edge=edge, status="deferred", reason=deferred_reason)
                for index, edge in enumerate(captured.device.edges)
                if resolved.topology is not None
            ],
            diagnostics=diagnostics + (list(topology_work.diagnostics) if topology_work else []),
            skipped_sections=dict(resolved.skipped),
            fully_resolved=deferred_reason is None and not (topology_work and topology_work.edge_work.pending),
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
        context = name_context(self._captured.source, inputs=self._captured.resolved.inputs)
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
    ) -> tuple[TopologyTarget | None, str | None, TopologyWork | None, bool]:
        captured = self._captured
        resolved = captured.resolved
        if resolved.topology is None:
            reason = resolved.skipped.get("topology")
            phases.extend(PlannedPhase(name=name, status="skipped", reason=reason) for name in _TOPOLOGY_PHASES)
            return None, None, None, False

        device = captured.device
        target: TopologyTarget | None = device.topology
        if target is None and device.inventory_id is not None:
            target = DeviceTarget(device_id=device.inventory_id)
        creating = inventory_work is not None and inventory_work.action == "create"
        if target is None and not creating:
            raise ProvisioningTargetError(
                f"Topology configuration for '{device.key}' needs an explicit 'topology' target or an 'inventory_id'."
            )

        reason: str | None = None
        requires_replan = False
        if target is None:
            reason = "the topology device is the Inventory record created by this plan"
        elif inventory_work is not None and inventory_work.affects_topology and inventory_work.action == "update":
            reason = (
                "planned Inventory changes may alter the discovered topology; "
                "apply stops after Inventory — plan again once the driver has rediscovered the device"
            )
            requires_replan = True
        elif inventory_work is not None and inventory_work.affects_topology:
            reason = "planned Inventory changes may alter the discovered topology"
        else:
            reason = self._membership_reason(target, diagnostics)

        work: TopologyWork | None = None
        if reason is None:
            assert target is not None
            try:
                work = self._materialize(target, current)
            except TopologyNotReadyError as exc:
                reason = str(exc)

        if reason is not None:
            for name in _TOPOLOGY_PHASES:
                skip = _inventory_readiness_skip(captured, target) if name == "inventory_readiness" else None
                phases.append(PlannedPhase(name=name, status="skipped" if skip else "deferred", reason=skip or reason))
            return target, reason, None, requires_replan

        assert work is not None
        phases.append(PlannedPhase(name="inventory_readiness", status="skipped", reason="topology already ready"))
        phases.append(PlannedPhase(name="topology_sync", status="no_change"))
        phases.append(PlannedPhase(name="discovery", status="skipped", reason="topology already ready"))
        phases.append(
            PlannedPhase(
                name="topology",
                status="planned"
                if work.has_topology_writes
                else ("deferred" if work.edge_work.pending else "no_change"),
                reason="Peer edges remain open; create a new plan when available." if work.edge_work.pending else None,
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
        return target, None, work, False

    def _membership_reason(self, target: TopologyTarget, diagnostics: list[Diagnostic]) -> str | None:
        sync = self._captured.options.sync
        gateway = InspectGateway(self._app.inspect)
        if not gateway.in_topology(target.device_id):
            if sync == "none" or isinstance(target, ModuleTarget):
                raise ProvisioningTargetError(
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
            raise ProvisioningCapabilityError(
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
    app: ProvisioningApp,
    captured: _Captured,
    target: TopologyTarget,
    inventory: Callable[[], InventoryGateway],
    current: InventoryDevice | None,
    *,
    gateway: InspectGateway | None = None,
) -> TopologyWork:
    """Collect a fresh scoped context and compute exact topology edits from the captured configuration."""
    assert captured.resolved.topology is not None
    gateway = gateway or InspectGateway(app.inspect)
    scope = gateway.read_scope(target)
    gateway.check_deadline()
    own = _driver_context(current) if current is not None else None
    owner = (
        own if own is not None and own.inventory_id == target.device_id else _owner_context(inventory, target.device_id)
    )
    gateway.check_deadline()
    work = compute_topology_work(
        scope=scope,
        resolved=captured.resolved.topology,
        naming=captured.naming,
        source=captured.source,
        owner=owner,
        inventory=own,
        allow_label_collisions=captured.options.naming_collisions == "allow",
    )
    return gateway.plan_edges(work, scope, captured.device.edges, captured.edge_peers, captured.device.module_position)


# --- Internal: execution ---


class _Executor:
    """Executes plans through the bound app; uses only the plan's captured settings."""

    def __init__(
        self,
        app: ProvisioningApp,
        *,
        clock: Callable[[], float],
        sleep: Callable[[float], None],
        logger: logging.Logger,
    ) -> None:
        self._app = app
        self._clock = clock
        self._sleep = sleep
        self._logger = logger

    def execute(self, plan: ProvisioningPlan, *, dry_run: bool = False) -> ApplyResult:
        return _Execution(self, plan, dry_run=dry_run).run()


class _Execution:
    def __init__(self, executor: _Executor, plan: ProvisioningPlan, *, dry_run: bool) -> None:
        self._executor = executor
        self._app = executor._app
        self._plan = plan
        self._captured: _Captured = plan._captured
        self._dry_run = dry_run
        self._would_write = False
        self._result = ApplyResult(source_key=plan.source_key, inventory_id=plan.inventory_id, dry_run=dry_run)
        self._result.edges = [
            state.model_copy(deep=True, update={"status": "not_run"})
            if state.status == "planned"
            else state.model_copy(deep=True)
            for state in plan.edges
        ]
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
        self._topology_add_requested = False
        self._requested_sync: InspectApiLookupSyncInfoItem | None = None

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
            recheck_conflicts(gateway, self._captured.device, work)
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
        if captured.topology_requires_replan:
            reason = self._plan.phase("topology").reason if self._plan.phase("topology") else None
            for name in _TOPOLOGY_PHASES:
                if self._phases[name].status == "skipped":
                    continue
                phase = self._enter(name)
                phase.status = "deferred"
                phase.message = reason
            self._result.replan_required = True
            if self._dry_run:
                self._would_write = True
            return
        if captured.topology_deferred and self._dry_run:
            reason = self._plan.phase("topology").reason if self._plan.phase("topology") else None
            for name in _TOPOLOGY_PHASES:
                if self._phases[name].status == "skipped":
                    continue
                phase = self._enter(name)
                phase.status = "deferred"
                phase.message = f"not run in a dry run: {reason}"
            self._would_write = True
            return
        target = captured.topology_target
        if target is None:
            if self._result.inventory_id is None:
                raise ProvisioningTargetError("No topology target: the Inventory record id is unknown.")
            target = DeviceTarget(device_id=self._result.inventory_id)
        self._result.topology_device_id = target.device_id
        self._result.module_id = target.module_id if isinstance(target, ModuleTarget) else None
        gateway = InspectGateway(self._app.inspect)

        if captured.topology_deferred:
            self._wait_for_inventory(target)
            work = self._discover_and_materialize(target)
            self._result.materialized = True
        else:
            assert captured.topology_work is not None
            work = captured.topology_work
            self._enter("topology")
            if gateway.read_scope(target).fingerprint != work.fingerprint:
                raise ProvisioningConflictError(
                    f"The topology of {_target_label(target)} changed since planning; create a new plan."
                )
        self._enter("topology")
        self._result.interface_bindings = list(work.bindings)
        self._result.port_bindings = list(work.port_bindings)
        self._result.edges = [
            state.model_copy(deep=True, update={"status": "not_run"})
            if state.status == "planned" and not self._dry_run
            else state.model_copy(deep=True)
            for state in work.edge_work.states
        ]
        self._result.replan_required = work.edge_work.pending
        if work.edge_work.pending and self._dry_run:
            self._would_write = True
        self._result.diagnostics.extend(work.diagnostics)

        gateway.check_peers(captured.device.edges, captured.edge_peers)
        gateway.check_edges(work.edge_work)

        overlap = gateway.staged_edit_keys() & work.touched_keys()
        if overlap:
            entities = ", ".join(f"{kind} '{entity_id}'" for kind, entity_id in sorted(overlap))
            raise ProvisioningConflictError(
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
            self._result.edges = [
                state.model_copy(update={"status": "completed"}) if state.status == "not_run" else state
                for state in self._result.edges
            ]
        else:
            phase.status = "deferred" if work.edge_work.pending else "no_change"
        if work.edge_work.pending:
            phase.message = "Peer edges remain open; create a new plan when available."

        self._run_module_tags(gateway, work)
        if "topology" in self._wrote or "module_tags" in self._wrote:
            try:
                self._mismatches.extend(verify_topology(gateway.read_scope(target), work))
                self._mismatches.extend(gateway.verify_edges(work.edge_work))
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
            raise ProvisioningConflictError(
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

    def _wait_for_inventory(self, target: TopologyTarget) -> None:
        phase = self._enter("inventory_readiness")
        skip = _inventory_readiness_skip(self._captured, target)
        if skip:
            phase.status = "skipped"
            phase.message = skip
            return
        inventory_id = self._result.inventory_id or self._captured.device.inventory_id or target.device_id
        wait = self._readiness_wait("inventory_readiness", inventory_id, self._captured.options.inventory_ready_timeout)
        gateway = self._inventory()
        try:
            wait.check()
            record = self._current_inventory
            if record is None or record.device_id != inventory_id:
                record = gateway.read(inventory_id)
            while True:
                wait.check()
                status = gateway.read_status(record)
                wait.condition = "status unavailable" if status is None else f"reachable={status.reachable}"
                wait.check()
                if status is not None and status.reachable:
                    phase.status = "completed"
                    phase.message = f"Inventory device '{inventory_id}' is reachable"
                    return
                wait.pause(wait.condition)
        except _ReadinessExpired as exc:
            raise InventoryNotReadyError(str(exc)) from None

    def _discover_and_materialize(self, target: TopologyTarget) -> TopologyWork:
        wait = self._readiness_wait("topology_sync", target.device_id, self._captured.options.topology_ready_timeout)
        gateway = InspectGateway(self._app.inspect, check_deadline=wait.check)
        sync_phase = self._enter("topology_sync")
        sync_phase.status = "no_change"
        try:
            while True:
                wait.check()
                try:
                    wait.stage = "topology_sync"
                    self._ensure_membership(gateway, target, wait)
                    wait.check()
                    wait.stage = "discovery"
                    wait.condition = "waiting for required topology data"
                    discovery = self._enter("discovery")
                    work = _materialize_topology(
                        self._app, self._captured, target, self._inventory, self._current_inventory, gateway=gateway
                    )
                    wait.check()
                    discovery.status = "completed"
                    discovery.message = f"Required topology data for '{target.device_id}' is ready"
                    return work
                except TopologyNotReadyError as exc:
                    if self._unknown:
                        raise
                    wait.pause(str(exc))
        except _ReadinessExpired as exc:
            raise TopologyNotReadyError(str(exc)) from None

    def _readiness_wait(self, stage: PhaseName, device_id: str, timeout: float) -> _ReadinessWait:
        return _ReadinessWait(
            stage=stage,
            device_id=device_id,
            timeout=timeout,
            poll_interval=self._captured.options.poll_interval,
            clock=self._executor._clock,
            sleep=self._executor._sleep,
        )

    def _ensure_membership(self, gateway: InspectGateway, target: TopologyTarget, wait: _ReadinessWait) -> None:
        sync = self._captured.options.sync
        phase = self._enter("topology_sync")
        if isinstance(target, ModuleTarget):
            # Never add or synchronize a whole parent device to reach a module target.
            if not gateway.in_topology(target.device_id):
                raise ProvisioningTargetError(
                    f"Parent device '{target.device_id}' of module '{target.module_id}' is not in the topology."
                )
            return
        if not gateway.in_topology(target.device_id):
            wait.condition = "device is not yet in the topology"
            if sync == "none":
                raise ProvisioningTargetError(
                    f"Inspect device '{target.device_id}' is not in the topology (sync='none')."
                )
            if self._topology_add_requested:
                raise TopologyNotReadyError("Topology addition accepted; waiting for the device to appear.")
            with self._write():
                gateway.add_to_topology(target.device_id)
            self._topology_add_requested = True
            self._record_sync(phase, "add_to_topology", target.device_id)
            wait.condition = "Topology addition accepted; waiting for the device to appear."
            if not gateway.in_topology(target.device_id):
                raise TopologyNotReadyError(wait.condition)
        wait.condition = "topology membership confirmed; synchronization status not yet available"
        info = gateway.sync_info(target.device_id)
        if not _sync_pending(info) or sync == "none":
            self._requested_sync = None
            return
        if sync == "add_only" and (info.update or info.remove):
            raise ProvisioningCapabilityError(
                f"Synchronizing '{target.device_id}' requires updates/removals; sync='add_only' is insufficient."
            )
        previous = self._requested_sync
        if previous is not None and (info.add, info.update, info.remove) == (
            previous.add,
            previous.update,
            previous.remove,
        ):
            raise TopologyNotReadyError("Topology synchronization is still pending.")
        with self._write():
            gateway.sync(target.device_id, add_only=sync == "add_only")
        self._record_sync(phase, "sync", target.device_id)
        wait.condition = "Topology synchronization accepted; waiting for completion."
        self._requested_sync = info.model_copy(deep=True)
        if _sync_pending(gateway.sync_info(target.device_id)):
            raise TopologyNotReadyError("Topology synchronization is still pending.")
        self._requested_sync = None

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
        if name == "topology":
            self._result.edges = [
                state.model_copy(update={"status": "unknown" if self._unknown else "failed", "reason": phase.message})
                if state.status == "not_run"
                else state
                for state in self._result.edges
            ]
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
                "Provisioning apply for '%s' ended %s: %s", result.source_key, result.status, error
            )
            raise ProvisioningApplyError(result, f"{type(error).__name__}: {error}") from error
        if self._dry_run:
            result.verification_detail = "dry run: nothing was written"
            result.status = "planned" if self._would_write else "no_change"
        elif result.replan_required:
            result.status = "partial"
        else:
            result.status = "succeeded" if self._wrote else "no_change"
        self._executor._logger.info("Provisioning apply for '%s' %s.", result.source_key, result.status)

    def _inventory(self) -> InventoryGateway:
        if self._inventory_gateway is None:
            self._inventory_gateway = InventoryGateway(self._app.inventory)
        return self._inventory_gateway


# --- Internal helpers ---

_TOPOLOGY_PHASES: tuple[PhaseName, ...] = (
    "inventory_readiness",
    "topology_sync",
    "discovery",
    "topology",
    "module_tags",
)
_PHASE_ORDER: tuple[str, ...] = ("inventory", *_TOPOLOGY_PHASES, "verification")


class _ReadinessExpired(ProvisioningError):
    """Internal deadline signal; kept distinct from a retryable not-ready observation."""


class _ReadinessWait(BaseModel):
    """A fixed monotonic budget, including read time, shared by one readiness stage."""

    stage: PhaseName
    device_id: str
    timeout: float
    poll_interval: float
    clock: Callable[[], float]
    sleep: Callable[[float], None]
    condition: str = "no status observed yet"
    _deadline: float = PrivateAttr()

    def model_post_init(self, context: Any) -> None:
        self._deadline = self.clock() + self.timeout

    def check(self) -> None:
        if self.clock() >= self._deadline:
            raise _ReadinessExpired(
                f"{self.stage} for device '{self.device_id}' not ready after {self.timeout:g}s: {self.condition}"
            )

    def pause(self, condition: str) -> None:
        self.condition = condition
        self.check()
        self.sleep(min(self.poll_interval, max(0.0, self._deadline - self.clock())))


def _inventory_readiness_skip(captured: _Captured, target: TopologyTarget | None) -> str | None:
    if not captured.options.require_reachable:
        return "Inventory reachability check disabled (require_reachable=False)"
    if target is not None and target.device_id.startswith("virtual."):
        return "virtual topology target"
    if (
        isinstance(target, ModuleTarget)
        and captured.device.inventory_id is None
        and captured.resolved.inventory is None
    ):
        return "module-only topology target without its own Inventory binding"
    return None


def _known_rejection(exc: Exception, *, create: bool) -> bool:
    """Whether a write error proves the server did not apply the change."""
    if isinstance(exc, (InspectCommitError, InspectCommitConflictError, ProvisioningError)):
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
    except (ProvisioningTargetError, ProvisioningValidationError):
        return None


ProvisioningPlan.model_rebuild()

__all__ = ["ProvisioningApp", "ProvisioningEngine", "ProvisioningPlan"]
