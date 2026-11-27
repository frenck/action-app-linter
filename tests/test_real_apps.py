"""Real apps, linted, so a change shows what it does to apps people ship."""

from pathlib import Path

import pytest
from syrupy.assertion import SnapshotAssertion

from applinter.findings import Level
from applinter.linter import lint
from applinter.output import plain

REAL = Path(__file__).parent / "fixtures" / "real"
APPS = sorted(path.name for path in REAL.iterdir() if path.is_dir())

# Kept to the standard of the linter: an error here is a false positive, or
# a change these projects need to hear about before a release.
MUST_PASS = [app for app in APPS if app.startswith(("official-", "community-"))]


@pytest.fixture
def real(monkeypatch: pytest.MonkeyPatch) -> Path:
    """Work from the real apps, so reported paths are short and stable."""
    monkeypatch.chdir(REAL)
    return REAL


@pytest.mark.usefixtures("real")
@pytest.mark.parametrize("app", APPS)
def test_real_app(app: str, snapshot: SnapshotAssertion) -> None:
    """Test the findings for each real app."""
    community = app.startswith("community-")
    findings = lint(Path(app), community=community)
    assert [plain(finding) for finding in findings] == snapshot


@pytest.mark.usefixtures("real")
@pytest.mark.parametrize("app", MUST_PASS)
def test_real_app_has_no_errors(app: str) -> None:
    """Test the official and Community Apps pass, whatever the snapshots say."""
    community = app.startswith("community-")
    findings = lint(Path(app), community=community)
    assert [plain(f) for f in findings if f.level is Level.ERROR] == []


def test_real_apps_are_there() -> None:
    """Test the real apps did not go missing, which would pass everything."""
    assert len(APPS) >= 10
    assert len(MUST_PASS) >= 7
