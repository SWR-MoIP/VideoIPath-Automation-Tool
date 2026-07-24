"""Load project-root ``.env`` for e2e and local development."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _PROJECT_ROOT / ".env"

_LEGACY_ENV_ALIASES = {
    "VIDEOIPATH_SERVER_ADDRESS": "VIPAT_VIDEOIPATH_SERVER_ADDRESS",
    "VIDEOIPATH_USERNAME": "VIPAT_VIDEOIPATH_USERNAME",
    "VIDEOIPATH_PASSWORD": "VIPAT_VIDEOIPATH_PASSWORD",
    "VIDEOIPATH_USE_HTTPS": "VIPAT_USE_HTTPS",
    "VIDEOIPATH_VERIFY_SSL": "VIPAT_VERIFY_SSL_CERT",
    "VIDEOIPATH_VERIFY_SSL_CERT": "VIPAT_VERIFY_SSL_CERT",
}


def load_project_env() -> None:
    """Load ``.env`` from the project root and normalize legacy variable names."""
    if _ENV_FILE.is_file():
        load_dotenv(_ENV_FILE, override=True)
    for legacy, canonical in _LEGACY_ENV_ALIASES.items():
        legacy_value = os.environ.get(legacy)
        if legacy_value and not os.environ.get(canonical):
            os.environ[canonical] = legacy_value


def prepare_e2e_env() -> None:
    """Load ``.env`` and enable the e2e gate for explicit e2e test runs."""
    load_project_env()
    os.environ["VIPAT_E2E_ENABLED"] = "1"
