"""Every fixture app, linted, against the findings it should have."""

from pathlib import Path

import pytest
from syrupy.assertion import SnapshotAssertion

from applinter.linter import lint
from applinter.output import plain

from .conftest import FIXTURES

APPS = sorted(path.name for path in FIXTURES.iterdir() if path.is_dir())
COMMUNITY_APPS = ["build", "build-single-image", "community", "valid", "valid-json"]


@pytest.mark.usefixtures("apps")
@pytest.mark.parametrize("app", APPS)
def test_app(app: str, snapshot: SnapshotAssertion) -> None:
    """Test the findings for each fixture app."""
    assert [plain(finding) for finding in lint(Path(app))] == snapshot


@pytest.mark.usefixtures("apps")
@pytest.mark.parametrize("app", COMMUNITY_APPS)
def test_app_community(app: str, snapshot: SnapshotAssertion) -> None:
    """Test the findings for fixture apps in community mode."""
    findings = lint(Path(app), community=True)
    assert [plain(finding) for finding in findings] == snapshot


@pytest.mark.usefixtures("apps")
@pytest.mark.parametrize(
    ("app", "community"),
    [
        ("valid", False),
        ("valid", True),
        ("valid-json", False),
        ("valid-json", True),
        # Not in community mode: a community app needs a build file.
        ("minimal", False),
    ],
)
def test_valid_apps_are_clean(app: str, *, community: bool) -> None:
    """Test the valid fixture apps have no errors, whatever the mode."""
    findings = lint(Path(app), community=community)
    assert [plain(finding) for finding in findings if finding.level == "error"] == []


@pytest.mark.usefixtures("apps")
def test_missing_directory() -> None:
    """Test a directory that does not exist is reported, not a crash."""
    assert [plain(finding) for finding in lint(Path("does-not-exist"))] == [
        "does-not-exist: error: The app directory does not exist [app-not-found]"
    ]
