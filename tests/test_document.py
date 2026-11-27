"""Tests for reading files and finding the line of each value."""

from pathlib import Path

import pytest

from applinter.document import load


def test_yaml_lines(tmp_path: Path) -> None:
    """Test keys and list items get the line they are on."""
    path = tmp_path / "config.yaml"
    path.write_text(
        "---\nname: Test\narch:\n  - amd64\n  - aarch64\nmap:\n  - type: share\n"
    )

    document, findings = load(path)

    assert not findings
    assert document is not None
    assert document.line(["name"]) == 2
    assert document.line(["arch", 1]) == 5
    assert document.line(["map", 0, "type"]) == 7
    assert document.line(["map", 0, "unknown"]) == 7
    assert document.line(["unknown"]) is None
    assert document.line() is None


def test_json_with_tabs(tmp_path: Path) -> None:
    """Test JSON indented with tabs, which YAML does not allow, has lines."""
    path = tmp_path / "config.json"
    path.write_text('{\n\t"name": "Test",\n\t"arch": [\n\t\t"amd64"\n\t]\n}\n')

    document, findings = load(path)

    assert not findings
    assert document is not None
    assert document.data == {"name": "Test", "arch": ["amd64"]}
    assert document.line(["arch", 0]) == 4


def test_json_without_lines(tmp_path: Path) -> None:
    """Test JSON that cannot be read as YAML still loads, without lines."""
    path = tmp_path / "config.json"
    # JSON allows a DEL character in a string, YAML does not.
    path.write_text('{"name": "Ex\x7fample", "slug": "test"}')

    document, findings = load(path)

    assert not findings
    assert document is not None
    assert document.data == {"name": "Ex\x7fample", "slug": "test"}
    assert document.line(["slug"]) is None


def test_json_is_not_yaml(tmp_path: Path) -> None:
    """Test a .json file is held to JSON, and not read as YAML."""
    path = tmp_path / "config.json"
    path.write_text("name: Test\n")

    document, findings = load(path)

    assert document is None
    assert [finding.rule.id for finding in findings] == ["invalid-file"]


def test_unreadable_file(tmp_path: Path) -> None:
    """Test a file that is not UTF-8 is reported, not a crash."""
    path = tmp_path / "config.yaml"
    path.write_bytes(b"name: \xff\xfe\n")

    document, findings = load(path)

    assert document is None
    assert findings[0].message.startswith("Cannot read the file")


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("", "The file is empty"),
        ("# Only a comment\n", "The file is empty"),
        (
            "just a string\n",
            "The file must hold a mapping of keys and values, not a str",
        ),
        (
            "--- a\n--- b\n",
            (
                "Not valid YAML: expected a single document in the stream, "
                "but found another document"
            ),
        ),
        (
            "name: \x07\n",
            "Not valid YAML: the character #x0007 is not allowed",
        ),
        (
            "a: !!python/name:os.system\n",
            (
                "Not valid YAML: could not determine a constructor for the tag "
                "'tag:yaml.org,2002:python/name:os.system'"
            ),
        ),
    ],
)
def test_unusable_yaml(tmp_path: Path, content: str, message: str) -> None:
    """Test YAML that does not make an app configuration is reported."""
    path = tmp_path / "config.yaml"
    path.write_text(content)

    document, findings = load(path)

    assert document is None
    assert [finding.message for finding in findings] == [message]


def test_yaml_merge_keys(tmp_path: Path) -> None:
    """Test overriding a key pulled in with a merge key is not a duplicate."""
    path = tmp_path / "config.yaml"
    path.write_text("options:\n  <<: &defaults {foo: a, bar: b}\n  foo: c\n")

    document, findings = load(path)

    assert not findings
    assert document is not None
    assert document.data == {"options": {"foo": "c", "bar": "b"}}
    assert document.line(["options", "foo"]) == 3


def test_yaml_impossible_date(tmp_path: Path) -> None:
    """Test a date YAML reads but Python cannot hold is reported, not a crash."""
    path = tmp_path / "config.yaml"
    path.write_text("name: Test\noptions: 2025-02-30\n")

    document, findings = load(path)

    assert document is None
    assert [(finding.message, finding.line) for finding in findings] == [
        (
            (
                "Not valid YAML: 2025-02-30 is not a date that exists; put it in "
                "quotes if it is not meant as a date"
            ),
            2,
        )
    ]
