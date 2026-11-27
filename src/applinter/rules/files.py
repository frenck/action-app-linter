"""Checks on the other files of an app, which the Supervisor reads as they are."""

from __future__ import annotations

import errno
from typing import TYPE_CHECKING

from applinter.const import REPOSITORY_FILES
from applinter.findings import Finding, Level, define_rule

from .registry import check

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from applinter.app import App

UNREADABLE_FILE = define_rule(
    "unreadable-file",
    Level.ERROR,
    "A symlinked file of the app that the Supervisor refuses or cannot read.",
)


@check
def repository_files(app: App) -> Iterator[Finding]:
    """Check symlinked app files stay readable, like the Supervisor reads them.

    A port of resolve_in_repository() in supervisor/apps/model.py: a file that
    resolves outside the repository or into .git is refused, and one that does
    not resolve to a regular file counts as missing. Plain files are fine.
    """
    root = repository_root(app.path)
    for name in REPOSITORY_FILES:
        path = app.path / name
        if path.is_symlink() and (problem := _problem(path, root)):
            yield Finding(UNREADABLE_FILE, f"{name} {problem}", path)


def repository_root(path: Path) -> Path:
    """Return the repository an app is in: the closest directory with .git.

    Without one, the directory the app is in stands in for the repository,
    as apps sit at the top of their repository.
    """
    resolved = path.resolve()
    for candidate in (resolved, *resolved.parents):
        if (candidate / ".git").exists():
            return candidate

    return resolved.parent


def _problem(path: Path, root: Path) -> str | None:
    """Return why the Supervisor would not read a symlinked file, if it would not."""
    try:
        resolved = path.resolve(strict=True)
    # Python before 3.13 raises RuntimeError for a symlink loop.
    except (OSError, RuntimeError) as err:
        if isinstance(err, FileNotFoundError):
            return (
                f"links to {path.readlink()}, which does not exist; the Supervisor "
                "treats it as missing"
            )
        if isinstance(err, RuntimeError) or err.errno in {
            errno.ELOOP,
            errno.ENAMETOOLONG,
        }:
            return "is a symlink that never resolves; the Supervisor refuses it"
        raise

    try:
        relative = resolved.relative_to(root)
    except ValueError:
        return (
            f"links to {resolved}, outside the repository; the Supervisor refuses "
            "it, copy the file instead"
        )

    if ".git" in relative.parts:
        return "links into .git; the Supervisor refuses it"
    if not resolved.is_file():
        return (
            "links to something that is not a file; the Supervisor treats it as missing"
        )

    return None
