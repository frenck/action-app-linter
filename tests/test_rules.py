"""Tests for the rules that need more cases than the fixtures have."""

import pytest

from applinter.findings import Level, define_rule
from applinter.rules.config import image_problem

HINT = "use lowercase letters, digits and separators such as - and ."


@pytest.mark.parametrize(
    "image",
    [
        "nginx",
        "library/nginx",
        "ghcr.io/hassio-addons/example/{arch}",
        "homeassistant/{arch}-addon-example",
        "localhost/example",
        "registry.example.com:5000/team/app",
        "[::1]:5000/app",
        "my_org/my__app",
        "example/app--name",
    ],
)
def test_valid_images(image: str) -> None:
    """Test image names the Supervisor accepts."""
    assert image_problem(image) is None


@pytest.mark.parametrize(
    ("image", "problem"),
    [
        ("", "is empty"),
        (
            "ghcr.io/Example/app",
            f"has an invalid part 'Example'; {HINT}",
        ),
        ("GHCR.io/example/app", "must have a lowercase registry, not 'GHCR.io'"),
        ("Example/app", "must have a lowercase registry, not 'Example'"),
        ("bad_registry.io/app", "has an invalid registry 'bad_registry.io'"),
        ("ghcr.io/", "has no name after the registry"),
        (
            "example/app:1.0.0",
            "must not have a tag; the Supervisor adds the version itself",
        ),
        (
            "example/-app",
            f"has an invalid part '-app'; {HINT}",
        ),
        (
            "example/app.",
            f"has an invalid part 'app.'; {HINT}",
        ),
    ],
)
def test_invalid_images(image: str, problem: str) -> None:
    """Test image names the Supervisor refuses, and why."""
    assert image_problem(image) == problem


def test_rule_defined_twice() -> None:
    """Test a rule identifier cannot be used twice."""
    with pytest.raises(ValueError, match="Rule schema is defined twice"):
        define_rule("schema", Level.ERROR, "Again")
