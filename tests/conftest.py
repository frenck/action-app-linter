"""Shared fixtures for the tests."""

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "apps"


@pytest.fixture
def apps(monkeypatch: pytest.MonkeyPatch) -> Path:
    """Work from the fixture apps, so reported paths are short and stable."""
    monkeypatch.chdir(FIXTURES)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    for name in ("INPUT_PATH", "INPUT_COMMUNITY", "INPUT_IGNORE"):
        monkeypatch.delenv(name, raising=False)
    return FIXTURES
