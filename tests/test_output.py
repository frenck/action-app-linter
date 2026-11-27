"""Tests for what the linter prints."""

import io
from pathlib import Path

import pytest

from applinter.findings import Finding, Level, Rule
from applinter.output import annotation, display_path, plain, report

RULE = Rule("example", Level.ERROR, "An example")
WARNING = Rule("example-warning", Level.WARNING, "An example warning")


def test_annotation_escapes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test messages and properties are escaped for workflow commands."""
    monkeypatch.chdir(tmp_path)
    finding = Finding(RULE, "100% wrong\nreally", Path("app,1/config.yaml"), 3)

    assert annotation(finding) == (
        "::error file=app%2C1/config.yaml,title=App linter%3A example,line=3"
        "::100%25 wrong%0Areally"
    )


def test_annotation_without_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test a finding without a line annotates the whole file."""
    monkeypatch.chdir(tmp_path)
    finding = Finding(WARNING, "Look", Path("app/build.yaml"))

    assert annotation(finding) == (
        "::warning file=app/build.yaml,title=App linter%3A example-warning::Look"
    )


def test_display_path_outside(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test a path outside the working directory is shown as it is."""
    monkeypatch.chdir(tmp_path)

    assert display_path(Path("/elsewhere/config.yaml")) == "/elsewhere/config.yaml"
    assert display_path(tmp_path / "app" / "config.yaml") == "app/config.yaml"


@pytest.mark.parametrize(
    ("findings", "summary"),
    [
        ([], "No problems found"),
        ([Finding(RULE, "a", Path("x"))], "Found 1 error and 0 warnings"),
        (
            [Finding(RULE, "a", Path("x")), Finding(WARNING, "b", Path("x"))] * 2,
            "Found 2 errors and 2 warnings",
        ),
    ],
)
def test_report(findings: list[Finding], summary: str) -> None:
    """Test the report ends with a summary of what it found."""
    stream = io.StringIO()

    report(findings, stream, github=False)

    lines = stream.getvalue().splitlines()
    assert lines[-1] == summary
    assert lines[:-1] == [plain(finding) for finding in findings]
