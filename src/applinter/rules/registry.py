"""The list of checks every lint run goes through."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from applinter.app import App
    from applinter.findings import Finding

type Check = Callable[[App], Iterator[Finding]]

CHECKS: list[Check] = []


def check(func: Check) -> Check:
    """Register a check, so every lint run includes it."""
    CHECKS.append(func)
    return func
