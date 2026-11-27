"""What the linter reports, and the rules it reports it for."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class Level(StrEnum):
    """How bad a finding is. Only errors fail a run."""

    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class Rule:
    """A single check, with the identifier people can look up and ignore."""

    id: str
    level: Level
    summary: str


@dataclass(frozen=True, slots=True)
class Finding:
    """A problem found in a file, at a line when it is known."""

    rule: Rule
    message: str
    file: Path
    line: int | None = None

    @property
    def level(self) -> Level:
        """Return the level of the rule this finding is for."""
        return self.rule.level

    @property
    def sort_key(self) -> tuple[str, int, str, str]:
        """Return the key that puts findings in file and line order."""
        return (str(self.file), self.line or 0, self.rule.id, self.message)


RULES: dict[str, Rule] = {}


def define_rule(rule_id: str, level: Level, summary: str) -> Rule:
    """Define a rule, making sure every identifier is used once."""
    if rule_id in RULES:
        msg = f"Rule {rule_id} is defined twice"
        raise ValueError(msg)

    RULES[rule_id] = Rule(rule_id, level, summary)
    return RULES[rule_id]
