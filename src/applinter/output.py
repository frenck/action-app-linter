"""Everything the linter prints, for a terminal or for GitHub Actions."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

from .findings import Level

if TYPE_CHECKING:
    from collections.abc import Iterable

    from .findings import Finding


def report(findings: Iterable[Finding], stream: TextIO, *, github: bool) -> None:
    """Print the findings, as annotations on GitHub and plain lines otherwise."""
    findings = list(findings)
    for finding in findings:
        line = annotation(finding) if github else plain(finding)
        stream.write(f"{line}\n")

    stream.write(f"{summary(findings)}\n")


def plain(finding: Finding) -> str:
    """Return a finding the way compilers print them, so editors can jump to it."""
    location = display_path(finding.file)
    if finding.line is not None:
        location = f"{location}:{finding.line}"

    return f"{location}: {finding.level}: {finding.message} [{finding.rule.id}]"


def annotation(finding: Finding) -> str:
    """Return a finding as a GitHub Actions workflow command.

    GitHub shows these as annotations on the file and line, both in the run
    and on the pull request.
    """
    properties = {
        "file": display_path(finding.file),
        "title": f"App linter: {finding.rule.id}",
    }
    if finding.line is not None:
        properties["line"] = str(finding.line)

    rendered = ",".join(
        f"{key}={_escape_property(value)}" for key, value in properties.items()
    )
    return f"::{finding.level} {rendered}::{_escape_data(finding.message)}"


def summary(findings: list[Finding]) -> str:
    """Return a line counting the errors and warnings."""
    errors = sum(finding.level is Level.ERROR for finding in findings)
    warnings = len(findings) - errors
    if not findings:
        return "No problems found"

    return f"Found {_count(errors, 'error')} and {_count(warnings, 'warning')}"


def display_path(path: Path) -> str:
    """Return a path relative to the working directory when it is inside it.

    GitHub resolves annotation paths against the workspace, which is where
    the action runs.
    """
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return os.fspath(path)


def _count(amount: int, noun: str) -> str:
    """Return an amount with the noun, plural when it needs to be."""
    return f"{amount} {noun}" if amount == 1 else f"{amount} {noun}s"


def _escape_data(value: str) -> str:
    """Escape the message of a workflow command."""
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _escape_property(value: str) -> str:
    """Escape a property of a workflow command, which also may not hold : or ,."""
    return _escape_data(value).replace(":", "%3A").replace(",", "%2C")
