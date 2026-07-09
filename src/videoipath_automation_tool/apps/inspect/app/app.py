"""InspectApp — the user-facing entry point for the VideoIPath Inspect surface.

Read-only monitoring plus commit-style topology writes, built entirely on the collector API
([ADR-0008]). Composed from focused mixins, mirroring the Inventory/Topology app layout.
"""

from __future__ import annotations

import logging
from typing import Optional

from videoipath_automation_tool.apps.inspect.api import InspectAPI
from videoipath_automation_tool.apps.inspect.snapshot import InspectSnapshot
from videoipath_automation_tool.connector.vip_connector import VideoIPathConnector

from .actions import InspectActionsMixin
from .read import InspectReadMixin, LoadMode
from .write import InspectWriteMixin

# First VideoIPath version the Inspect collector surface was verified against.
_MIN_VERIFIED_VERSION = (2025, 4)


class InspectApp(InspectReadMixin, InspectWriteMixin, InspectActionsMixin):
    def __init__(
        self,
        vip_connector: VideoIPathConnector,
        logger: Optional[logging.Logger] = None,
        load: LoadMode = "skeleton",
    ):
        """Inspect App: read the topology/status and apply commit-style topology changes.

        The app keeps a single internal topology view that is loaded lazily on the first read and
        kept up to date across writes; interact with it entirely through this app (``app.inspect``),
        the same way as the other apps. Call :meth:`refresh` to reload it from the server.

        Args:
            vip_connector (VideoIPathConnector): connector handling the VideoIPath connection.
            logger (Optional[logging.Logger]): logger instance.
            load (LoadMode): how the internal view is loaded — ``"skeleton"`` (default; fast, with
                lazy per-device detail) or ``"full"`` (eager, point-in-time).
        """
        self._logger = logger or logging.getLogger("videoipath_automation_tool_inspect_app")
        self._inspect_api = InspectAPI(vip_connector=vip_connector, logger=self._logger)
        self._vip_connector = vip_connector
        self._load_mode: LoadMode = load
        self._snapshot: Optional[InspectSnapshot] = None
        self._warn_if_version_unverified()
        self._logger.debug("Inspect APP initialized.")

    def _warn_if_version_unverified(self) -> None:
        version = self._vip_connector.videoipath_version
        parsed = _parse_version(version)
        if parsed is not None and parsed < _MIN_VERIFIED_VERSION:
            self._logger.warning(
                f"Inspect app: VideoIPath version '{version}' predates the first verified Inspect "
                f"surface ({_MIN_VERIFIED_VERSION[0]}.{_MIN_VERIFIED_VERSION[1]}). Behaviour is unverified."
            )


def _parse_version(version: str) -> Optional[tuple[int, int]]:
    parts = version.split(".")
    if len(parts) < 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None


__all__ = ["InspectApp"]
