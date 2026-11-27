"""An app, as the files the linter found for it."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from .document import Document


@dataclass(slots=True)
class App:
    """The configuration files of one app.

    The rules run on files that may have failed the schema, so the accessors
    hand back values of the expected type only, and an empty one otherwise.
    """

    path: Path
    config: Document
    build: Document | None = None
    translations: list[Document] = field(default_factory=list)
    community: bool = False

    @property
    def arch(self) -> list[str]:
        """Return the architectures the app says it supports."""
        return strings(self.config.data, "arch")

    @property
    def schema(self) -> dict[str, Any] | None:
        """Return the options schema, or None when options are not checked."""
        schema = self.config.data.get("schema", {})
        return schema if isinstance(schema, dict) else None


def mapping(data: dict[str, Any], key: str) -> dict[str, Any]:
    """Return a value that should be a mapping, or an empty one."""
    value = data.get(key)
    return value if isinstance(value, dict) else {}


def strings(data: dict[str, Any], key: str) -> list[str]:
    """Return the strings in a value that should be a list of them."""
    value = data.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
