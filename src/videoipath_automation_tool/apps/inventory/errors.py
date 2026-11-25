"""Typed Inventory errors."""

from __future__ import annotations

from typing import Literal

InventoryWriteOperation = Literal["add", "update"]


class InventoryStatusUnavailableError(ValueError):
    """The device has no Inventory status yet; a later single-attempt read may succeed."""


class InventoryWriteNotAppliedError(ValueError):
    """An Inventory write was rejected by the server or not attempted, so it did not change the record.

    ``operation`` names the write that was not applied. ``device_id`` is set when the record is already
    known, including a tracking-id cleanup that runs after a successful add. Subclasses ``ValueError``
    so existing callers that catch ``ValueError`` keep working.
    """

    def __init__(self, message: str, *, operation: InventoryWriteOperation, device_id: str | None = None) -> None:
        self.operation: InventoryWriteOperation = operation
        self.device_id = device_id
        super().__init__(message)


class InventoryRecordCreatedError(Exception):
    """The Inventory record exists, and a later step in ``add_device`` did not finish.

    ``device_id`` is the new record. The unfinished step's outcome is not known.
    """

    def __init__(self, device_id: str, message: str) -> None:
        self.device_id = device_id
        super().__init__(message)


__all__ = [
    "InventoryRecordCreatedError",
    "InventoryStatusUnavailableError",
    "InventoryWriteNotAppliedError",
    "InventoryWriteOperation",
]
