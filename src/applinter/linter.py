"""Finding the files of an app and running every check on them."""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import document
from .app import App
from .findings import Finding, Level, define_rule
from .rules import CHECKS
from .schema import defaults, validate

if TYPE_CHECKING:
    from pathlib import Path

# The Supervisor tries these in this order: supervisor/const.py,
# FILE_SUFFIX_CONFIGURATION.
SUFFIXES = (".yaml", ".yml", ".json")

APP_NOT_FOUND = define_rule(
    "app-not-found", Level.ERROR, "There is no app configuration."
)
MULTIPLE_FILES = define_rule(
    "multiple-files",
    Level.ERROR,
    "A file exists in more than one format, and only one of them is read.",
)


def lint(path: Path, *, community: bool = False) -> list[Finding]:
    """Lint the app in a directory, and return what is wrong with it."""
    if not path.is_dir():
        return [Finding(APP_NOT_FOUND, "The app directory does not exist", path)]

    findings: list[Finding] = []

    config_path = _find(path, "config", findings)
    if config_path is None:
        message = "There is no config.yaml, config.yml or config.json"
        return [*findings, Finding(APP_NOT_FOUND, message, path)]

    config, problems = document.load(config_path)
    findings.extend(problems)
    if config is None:
        return findings

    app = App(path, config, community=community)
    findings.extend(validate(config, "config"))
    findings.extend(defaults(config, "config"))

    if build_path := _find(path, "build", findings):
        app.build, problems = document.load(build_path)
        findings.extend(problems)

    if app.build is not None:
        findings.extend(validate(app.build, "build"))
        findings.extend(defaults(app.build, "build"))

    for translation_path in _translations(path):
        translation, problems = document.load(translation_path)
        findings.extend(problems)
        if translation is not None:
            app.translations.append(translation)
            findings.extend(validate(translation, "translations"))

    for check in CHECKS:
        findings.extend(check(app))

    return sorted(findings, key=lambda finding: finding.sort_key)


def _find(path: Path, name: str, findings: list[Finding]) -> Path | None:
    """Return the file with a name in the first format found, if any."""
    candidates = [
        path / f"{name}{suffix}"
        for suffix in SUFFIXES
        if (path / f"{name}{suffix}").is_file()
    ]
    if len(candidates) > 1:
        names = " and ".join(candidate.name for candidate in candidates)
        findings.append(
            Finding(
                MULTIPLE_FILES,
                f"Found {names}; keep only one, the linter checked "
                f"{candidates[0].name}",
                candidates[1],
            )
        )

    return candidates[0] if candidates else None


def _translations(path: Path) -> list[Path]:
    """Return the translation files of the app, like the Supervisor finds them."""
    directory = path / "translations"
    if not directory.is_dir():
        return []

    return sorted(
        file
        for file in directory.iterdir()
        if file.is_file() and file.suffix in SUFFIXES
    )
