"""Checks on the files in translations/."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from applinter.app import mapping
from applinter.findings import Level, define_rule

from .registry import check

if TYPE_CHECKING:
    from collections.abc import Iterator

    from applinter.app import App
    from applinter.document import Document
    from applinter.findings import Finding

# The language codes of the frontend, such as en, nl, pt-BR and zh-Hans:
# home-assistant/frontend, src/translations/translationMetadata.json.
RE_LANGUAGE = re.compile(r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")

TRANSLATION_UNKNOWN_OPTION = define_rule(
    "translation-unknown-option",
    Level.WARNING,
    "A translation names an option that is not in the schema.",
)
TRANSLATION_FILENAME = define_rule(
    "translation-filename",
    Level.WARNING,
    "A translation file is not named after a language code.",
)
TRANSLATION_UNKNOWN_PORT = define_rule(
    "translation-unknown-port",
    Level.WARNING,
    "A translation describes a port that is not in 'ports'.",
)


@check
def translated_options(app: App) -> Iterator[Finding]:
    """Check every translated option exists, so no translation goes unseen.

    The options under fields belong to the nested options in the schema.
    """
    if (schema := app.schema) is None:
        return

    for translation in app.translations:
        fields = mapping(translation.data, "configuration")
        yield from _unknown_options(translation, fields, schema, ("configuration",))


def _unknown_options(
    translation: Document,
    fields: dict[str, Any],
    schema: dict[str, Any],
    path: tuple[str, ...],
) -> Iterator[Finding]:
    """Find translated options missing from the schema, nested ones included."""
    for key, field in fields.items():
        option = ".".join((*path[1::2], key))
        if key not in schema:
            yield translation.finding(
                TRANSLATION_UNKNOWN_OPTION,
                f"Option '{option}' is not in 'schema' of the configuration",
                (*path, key),
            )
            continue

        nested_fields = mapping(field, "fields") if isinstance(field, dict) else {}
        if not nested_fields:
            continue

        # A nested option is a mapping, or a list holding one mapping.
        nested_schema = schema[key]
        if isinstance(nested_schema, list) and nested_schema:
            nested_schema = nested_schema[0]

        if isinstance(nested_schema, dict):
            yield from _unknown_options(
                translation, nested_fields, nested_schema, (*path, key, "fields")
            )
        else:
            yield translation.finding(
                TRANSLATION_UNKNOWN_OPTION,
                f"Option '{option}' has 'fields', but no nested options in 'schema'",
                (*path, key, "fields"),
            )


@check
def translation_filename(app: App) -> Iterator[Finding]:
    """Check translation files are named after a language, or they go unused."""
    for translation in app.translations:
        if not RE_LANGUAGE.match(translation.path.stem):
            yield translation.finding(
                TRANSLATION_FILENAME,
                f"'{translation.path.name}' is not named after a language code, "
                "such as en.yaml or pt-BR.yaml, so it is never used",
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
