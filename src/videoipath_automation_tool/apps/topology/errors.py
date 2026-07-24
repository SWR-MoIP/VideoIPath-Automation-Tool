"""Typed exceptions for the Topology app."""

from __future__ import annotations


class TopologyUnsupportedError(Exception):
    """Raised when TopologyApp is used against an unsupported VideoIPath version."""
