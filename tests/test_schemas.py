"""Tests for the bundled schemas and the rule documentation."""

import re
from pathlib import Path

import pytest
from jsonschema import Draft7Validator

from applinter.findings import RULES
from applinter.schema import load_schema

README = Path(__file__).parent.parent / "README.md"


@pytest.mark.parametrize("name", ["build", "config", "translations"])
def test_schema_is_valid(name: str) -> None:
    """Test each bundled schema is a valid JSON schema."""
    Draft7Validator.check_schema(load_schema(name))


@pytest.mark.parametrize("rule_id", sorted(RULES))
def test_rule_is_documented(rule_id: str) -> None:
    """Test every rule is in the README, so people can look it up."""
    table_row = re.compile(rf"^\| `{re.escape(rule_id)}` +\|", re.MULTILINE)
    assert table_row.search(README.read_text(encoding="utf-8"))
