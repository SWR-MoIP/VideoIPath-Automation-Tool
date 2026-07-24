"""Shared fixtures for offline Inspect tests."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "2025.4.9"


def load_fixture(name: str) -> dict[str, Any]:
    with open(FIXTURE_DIR / name) as handle:
        return json.load(handle)


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURE_DIR


@pytest.fixture
def load() -> Callable[[str], dict[str, Any]]:
    return load_fixture
