"""Typed exceptions for blueprint loading, planning, and application.

Every error derives from :class:`BlueprintError`. Validation problems carry structured
:class:`ValidationIssue` records (document path, optional YAML location, issue code) instead of
raw values, so messages never echo credentials or arbitrary server payloads.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from videoipath_automation_tool.blueprints.models import ApplyResult


class ValidationIssue(BaseModel):
    """One validation finding. ``path`` is the dotted document path (e.g.
    ``topology.receiver.vertex_processor.params.redundant_streams``)."""

    model_config = ConfigDict(frozen=True)

    path: str = ""
    message: str
    code: str = "invalid"
    source: str | None = None
    line: int | None = None
    column: int | None = None

    def __str__(self) -> str:
        lines: list[str] = []
        if self.source or self.line is not None:
            location = self.source or "<blueprint>"
            if self.line is not None:
                location += f":{self.line}:{self.column or 1}"
            lines.append(location)
        if self.path:
            lines.append(self.path)
        lines.append(self.message)
        return "\n".join(lines)


class BlueprintError(Exception):
    """Base class for all blueprint errors."""


class BlueprintValidationError(BlueprintError):
    """A blueprint, device description, naming rule, or processor parameter set is invalid."""

    def __init__(self, issues: Iterable[ValidationIssue] | ValidationIssue | str, *, code: str = "invalid") -> None:
        if isinstance(issues, str):
            issues = [ValidationIssue(message=issues, code=code)]
        elif isinstance(issues, ValidationIssue):
            issues = [issues]
        self.issues: list[ValidationIssue] = list(issues)
        super().__init__("\n\n".join(str(issue) for issue in self.issues) or "Blueprint validation failed.")

    @property
    def codes(self) -> list[str]:
        return [issue.code for issue in self.issues]


class BlueprintTargetError(BlueprintError):
    """A binding is missing or ambiguous, or a target lies outside the requested scope."""


class ProcessorInputError(BlueprintError):
    """A processor cannot interpret the observed topology (unsupported or incomplete layout)."""


class BlueprintCapabilityError(BlueprintError):
    """A requested operation is not supported by the adapter or the server."""


class BlueprintConflictError(BlueprintError):
    """A reviewed plan or a managed baseline changed since it was captured; replan."""


class BlueprintApplyError(BlueprintError):
    """Execution failed, partially succeeded, or ended with an unknown outcome.

    ``result`` is the structured :class:`ApplyResult` describing every completed, failed, and
    unknown phase, including any Inventory id created before the failure. The original error is
    chained as ``__cause__``.
    """

    def __init__(self, result: ApplyResult, message: str) -> None:
        self.result = result
        super().__init__(f"Blueprint apply {result.status} for '{result.source_key}': {message}")


__all__ = [
    "BlueprintApplyError",
    "BlueprintCapabilityError",
    "BlueprintConflictError",
    "BlueprintError",
    "BlueprintTargetError",
    "BlueprintValidationError",
    "ProcessorInputError",
    "ValidationIssue",
]
