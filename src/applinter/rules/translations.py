"""Checks on the files in translations/."""

from __future__ import annotations

from typing import TYPE_CHECKING

from applinter.app import mapping
from applinter.findings import Level, define_rule

from .registry import check

if TYPE_CHECKING:
    from collections.abc import Iterator

    from applinter.app import App
    from applinter.findings import Finding

TRANSLATION_UNKNOWN_OPTION = define_rule(
    "translation-unknown-option",
    Level.WARNING,
    "A translation names an option that is not in the schema.",
)
TRANSLATION_UNKNOWN_PORT = define_rule(
    "translation-unknown-port",
    Level.WARNING,
    "A translation describes a port that is not in 'ports'.",
)


@check
def translated_options(app: App) -> Iterator[Finding]:
    """Check every translated option exists, so no translation goes unseen."""
    if (schema := app.schema) is None:
        return

    for translation in app.translations:
        for key in mapping(translation.data, "configuration"):
            if key not in schema:
                yield translation.finding(
                    TRANSLATION_UNKNOWN_OPTION,
                    f"Option '{key}' is not in 'schema' of the configuration",
                    ("configuration", key),
                )


@check
def translated_ports(app: App) -> Iterator[Finding]:
    """Check every translated port description belongs to a port."""
    ports = {str(port) for port in mapping(app.config.data, "ports")}
    for translation in app.translations:
        for port in mapping(translation.data, "network"):
            if str(port) not in ports:
                yield translation.finding(
                    TRANSLATION_UNKNOWN_PORT,
                    f"Port '{port}' is not in 'ports' of the configuration",
                    ("network", port),
                )
