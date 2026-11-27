"""Checks on build.yaml."""

from __future__ import annotations

from typing import TYPE_CHECKING

from applinter.const import ARCH_DEPRECATED
from applinter.findings import Level, define_rule

from .config import DEPRECATED_ARCH, DEPRECATED_CODENOTARY
from .registry import check

if TYPE_CHECKING:
    from collections.abc import Iterator

    from applinter.app import App
    from applinter.findings import Finding

BUILD_DEPRECATED = define_rule(
    "build-deprecated",
    Level.WARNING,
    "The Supervisor deprecated build.yaml for the apps it builds.",
)
BUILD_ARCH_MISSING = define_rule(
    "build-arch-missing",
    Level.ERROR,
    "An architecture in config.yaml has no base image in build.yaml.",
)
BUILD_ARCH_UNUSED = define_rule(
    "build-arch-unused",
    Level.WARNING,
    "A base image in build.yaml is for an architecture the app does not support.",
)
DEPRECATED_SQUASH = define_rule(
    "deprecated-squash",
    Level.ERROR,
    "'squash' is not supported by Docker BuildKit, which the Supervisor uses.",
)


@check
def build_deprecated(app: App) -> Iterator[Finding]:
    """Flag a build file the Supervisor reads, which it deprecated.

    The Supervisor only reads it for apps it builds itself, so not when the
    app has an image. The Community Apps workflows still read it, so it is
    not flagged in community mode either.
    """
    if app.build is None or app.community or "image" in app.config.data:
        return

    yield app.build.finding(
        BUILD_DEPRECATED,
        f"The Supervisor deprecated {app.build.path.name}; move the base image, "
        "build arguments and labels into the Dockerfile",
    )


@check
def build_options(app: App) -> Iterator[Finding]:
    """Flag options in the build file that are no longer used."""
    if app.build is None:
        return

    if "codenotary" in app.build.data:
        yield app.build.finding(
            DEPRECATED_CODENOTARY,
            "'codenotary' is no longer used; remove it",
            ("codenotary",),
        )

    if "squash" in app.build.data:
        yield app.build.finding(
            DEPRECATED_SQUASH,
            "'squash' is not supported by Docker BuildKit, which the Supervisor "
            "builds with; remove it",
            ("squash",),
        )


@check
def build_architectures(app: App) -> Iterator[Finding]:
    """Check the base images match the architectures of the app."""
    if app.build is None:
        return

    build_from = app.build.data.get("build_from")
    if not isinstance(build_from, dict) or not build_from:
        return

    for arch in build_from:
        if arch in ARCH_DEPRECATED:
            yield app.build.finding(
                DEPRECATED_ARCH,
                f"Architecture '{arch}' is no longer supported since Home Assistant "
                "2025.12; remove it from 'build_from'",
                ("build_from", arch),
            )
        elif arch not in app.arch:
            yield app.build.finding(
                BUILD_ARCH_UNUSED,
                f"'build_from' has a base image for '{arch}', which is not in "
                "'arch' of the configuration",
                ("build_from", arch),
            )

    for arch in app.arch:
        if arch not in build_from:
            yield app.build.finding(
                BUILD_ARCH_MISSING,
                f"'build_from' has no base image for '{arch}', so the app cannot "
                "be built for it",
                ("build_from",),
            )
