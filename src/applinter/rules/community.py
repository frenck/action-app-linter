"""Checks for the Home Assistant Community Apps project, in community mode only."""

from __future__ import annotations

from typing import TYPE_CHECKING

from applinter.findings import Finding, Level, define_rule

from .registry import check

if TYPE_CHECKING:
    from collections.abc import Iterator

    from applinter.app import App

COMMUNITY_VERSION = define_rule(
    "community-version",
    Level.ERROR,
    "The version of a community app is 'dev'; releases set the real one.",
)
COMMUNITY_BUILD_FILE = define_rule(
    "community-build-file",
    Level.ERROR,
    "A community app needs a build.yaml with a base image per architecture.",
)


@check
def community_version(app: App) -> Iterator[Finding]:
    """Check the version is dev, which the release workflow replaces."""
    if not app.community:
        return

    version = app.config.data.get("version")
    if version is not None and version != "dev":
        yield app.config.finding(
            COMMUNITY_VERSION,
            f"'version' is {version!r}; community apps use 'dev'",
            ("version",),
        )


@check
def community_build_file(app: App) -> Iterator[Finding]:
    """Check the build file the Community Apps workflows read the base image from."""
    if not app.community:
        return

    if app.build is None:
        yield Finding(
            COMMUNITY_BUILD_FILE,
            "The build.yaml is missing; the Community Apps workflows read the "
            "base image for each architecture from it",
            app.path / "build.yaml",
        )
        return

    if not isinstance(app.build.data.get("build_from"), dict):
        yield app.build.finding(
            COMMUNITY_BUILD_FILE,
            "'build_from' must have a base image per architecture; the Community "
            "Apps workflows read it that way",
            ("build_from",),
        )
