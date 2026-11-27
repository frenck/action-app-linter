"""Reading app files, and keeping track of the line every value is on."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import yaml

from .findings import Finding, Level, define_rule

if TYPE_CHECKING:
    from pathlib import Path

    from .findings import Rule

type KeyPath = Sequence[str | int]

DUPLICATE_KEY = define_rule(
    "duplicate-key",
    Level.ERROR,
    "A key is set more than once; only the last one counts.",
)
_MERGE_TAG = "tag:yaml.org,2002:merge"

INVALID_FILE = define_rule(
    "invalid-file", Level.ERROR, "A file is not valid YAML or JSON, or not a mapping."
)


@dataclass(slots=True)
class Document:
    """A parsed file, with the line of each key and list item in it."""

    path: Path
    data: dict[str, Any]
    lines: dict[tuple[str, ...], int] = field(default_factory=dict)

    def line(self, key_path: KeyPath = ()) -> int | None:
        """Return the line of a value, or of the closest parent that has one."""
        path = tuple(str(part) for part in key_path)
        while path:
            if (line := self.lines.get(path)) is not None:
                return line
            path = path[:-1]

        return None

    def finding(self, rule: Rule, message: str, key_path: KeyPath = ()) -> Finding:
        """Return a finding in this document, at the line of a value."""
        return Finding(rule, message, self.path, self.line(key_path))


def load(path: Path) -> tuple[Document | None, list[Finding]]:
    """Read a YAML or JSON file.

    Returns no document when the file cannot be used at all, along with the
    findings that explain why.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as err:
        return None, [Finding(INVALID_FILE, f"Cannot read the file: {err}", path)]

    if path.suffix == ".json":
        return _load_json(path, text)

    return _load_yaml(path, text)


def _load_yaml(path: Path, text: str) -> tuple[Document | None, list[Finding]]:
    """Read a YAML file, building the data from the same nodes the lines come from."""
    try:
        # The loader already reads the text, and refuses characters YAML
        # does not allow, while it is created.
        loader = yaml.SafeLoader(text)
        try:
            node = loader.get_single_node()
            # Index before building the data: building it flattens merge keys
            # (<<) into their mapping, which then looks like duplicate keys.
            lines, findings = _index(path, node)
            data = loader.construct_document(node) if node is not None else None
        finally:
            loader.dispose()
    except yaml.MarkedYAMLError as err:
        return None, [_yaml_error(path, err)]
    except yaml.YAMLError as err:
        return None, [Finding(INVALID_FILE, f"Not valid YAML: {err}", path)]
    except ValueError as err:
        # Values YAML reads but Python cannot hold, such as the date 2025-02-30.
        return None, [Finding(INVALID_FILE, f"Not valid YAML: {err}", path)]

    return _document(path, data, lines, findings)


def _load_json(path: Path, text: str) -> tuple[Document | None, list[Finding]]:
    """Read a JSON file.

    The data comes from the JSON parser, so the file has to be real JSON. The
    lines come from reading it as YAML too, which JSON nearly always is. Tabs
    are fine in JSON but not in YAML; as whitespace they only move columns,
    so swapping them for spaces keeps every line where it is.
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError as err:
        message = f"Not valid JSON: {err.msg}"
        return None, [Finding(INVALID_FILE, message, path, err.lineno)]

    try:
        node = yaml.compose(text.replace("\t", " "), Loader=yaml.SafeLoader)
    except yaml.YAMLError:
        node = None

    return _document(path, data, *_index(path, node))


def _document(
    path: Path,
    data: Any,
    lines: dict[tuple[str, ...], int],
    findings: list[Finding],
) -> tuple[Document | None, list[Finding]]:
    """Return the document, unless its data is not a mapping."""
    if data is None:
        return None, [Finding(INVALID_FILE, "The file is empty", path)]

    if not isinstance(data, dict):
        kind = type(data).__name__
        message = f"The file must hold a mapping of keys and values, not a {kind}"
        return None, [Finding(INVALID_FILE, message, path, 1)]

    return Document(path, data, lines), findings


def _index(
    path: Path, node: yaml.Node | None
) -> tuple[dict[tuple[str, ...], int], list[Finding]]:
    """Return the line of every key and list item, and the duplicate keys."""
    lines: dict[tuple[str, ...], int] = {}
    findings: list[Finding] = []
    if node is not None:
        _walk(path, node, (), lines, findings)

    return lines, findings


def _walk(
    path: Path,
    node: yaml.Node,
    key_path: tuple[str, ...],
    lines: dict[tuple[str, ...], int],
    findings: list[Finding],
) -> None:
    """Record the line of every key and list item, and find duplicate keys."""
    if isinstance(node, yaml.MappingNode):
        seen: set[str] = set()
        for key_node, value_node in node.value:
            # A merge key (<<) pulls in another mapping; its own keys may
            # be overridden here, which is the point of it.
            if key_node.tag == _MERGE_TAG:
                continue

            key = str(key_node.value)
            child_path = (*key_path, key)

            if key in seen:
                findings.append(
                    Finding(
                        DUPLICATE_KEY,
                        f"'{'.'.join(child_path)}' is set more than once; "
                        "only the last one counts",
                        path,
                        key_node.start_mark.line + 1,
                    )
                )

            # The last one wins in the data, so it wins here too.
            seen.add(key)
            lines[child_path] = key_node.start_mark.line + 1
            _walk(path, value_node, child_path, lines, findings)

    elif isinstance(node, yaml.SequenceNode):
        for index, item_node in enumerate(node.value):
            item_path = (*key_path, str(index))
            lines[item_path] = item_node.start_mark.line + 1
            _walk(path, item_node, item_path, lines, findings)


def _yaml_error(path: Path, err: yaml.MarkedYAMLError) -> Finding:
    """Turn a YAML error into a finding on the line it points at."""
    mark = err.problem_mark or err.context_mark
    problem = err.problem or err.context or "unknown problem"
    # Some problems only make sense after their context, such as "expected a
    # single document in the stream" followed by "but found another document".
    if err.context and problem.startswith("but "):
        problem = f"{err.context}, {problem}"
    line = mark.line + 1 if mark else None
    return Finding(INVALID_FILE, f"Not valid YAML: {problem}", path, line)
