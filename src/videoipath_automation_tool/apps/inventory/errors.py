"""Typed Inventory errors."""

from __future__ import annotations

from typing import Literal

InventoryWriteOperation = Literal["add", "update"]


class InventoryWriteNotAppliedError(ValueError):
    """An Inventory write was rejected by the server or not attempted, so it did not change the record.

    ``operation`` names the write that was not applied. Subclasses ``ValueError`` so existing callers
    that catch ``ValueError`` keep working.
    """

    def __init__(self, message: str, *, operation: InventoryWriteOperation) -> None:
        self.operation: InventoryWriteOperation = operation
        super().__init__(message)


__all__ = ["InventoryWriteNotAppliedError", "InventoryWriteOperation"]
