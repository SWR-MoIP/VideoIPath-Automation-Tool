"""Shared fixtures for offline Inspect tests."""

import json
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "inspect" / "2025.4.9"


def load_fixture(name: str) -> dict:
    with open(FIXTURE_DIR / name) as handle:
        return json.load(handle)


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURE_DIR


@pytest.fixture
def load():
    return load_fixture
