"""Reading app files, and keeping track of the line every value is on."""

from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
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
_TIMESTAMP_TAG = "tag:yaml.org,2002:timestamp"

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
    node = None
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
    except yaml.reader.ReaderError as err:
        return None, [_reader_error(path, text, err)]
    except yaml.MarkedYAMLError as err:
        return None, [_yaml_error(path, err)]
    except _SelfReferenceError as err:
        message = "Not valid YAML: an anchor contains an alias to itself"
        return None, [Finding(INVALID_FILE, message, path, err.line)]
    except ValueError as err:
        return None, [_impossible_value(path, node, err)]

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
    indexer = _Indexer(path)
    if node is not None:
        indexer.walk(node, (), frozenset())

    return indexer.lines, indexer.findings


@dataclass(slots=True)
class _Indexer:
    """Walks the nodes of a file once, recording lines and duplicate keys."""

    path: Path
    lines: dict[tuple[str, ...], int] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    seen: set[int] = field(default_factory=set)

    def walk(
        self, node: yaml.Node, key_path: tuple[str, ...], ancestors: frozenset[int]
    ) -> None:
        """Record the line of every key and list item under a node.

        An alias is the very node of its anchor, so a node shows up once per
        alias. It is walked only the first time: its lines and duplicates are
        those of the anchor, and a file of nested aliases cannot blow up the
        walk. A node that is its own ancestor would never end the data at all.
        """
        if id(node) in ancestors:
            raise _SelfReferenceError(node.start_mark.line + 1)
        if id(node) in self.seen:
            return
        self.seen.add(id(node))
        ancestors |= {id(node)}

        if isinstance(node, yaml.MappingNode):
            self._walk_mapping(node, key_path, ancestors)
        elif isinstance(node, yaml.SequenceNode):
            for index, item_node in enumerate(node.value):
                item_path = (*key_path, str(index))
                self.lines[item_path] = item_node.start_mark.line + 1
                self.walk(item_node, item_path, ancestors)

    def _walk_mapping(
        self,
        node: yaml.MappingNode,
        key_path: tuple[str, ...],
        ancestors: frozenset[int],
    ) -> None:
        """Record the keys of a mapping, and find the ones set twice."""
        keys: set[str] = set()
        for key_node, value_node in node.value:
            # A merge key (<<) pulls in another mapping; its own keys may
            # be overridden here, which is the point of it.
            if key_node.tag == _MERGE_TAG:
                continue

            key = str(key_node.value)
            child_path = (*key_path, key)

            if key in keys:
                self.findings.append(
                    Finding(
                        DUPLICATE_KEY,
                        f"'{'.'.join(child_path)}' is set more than once; "
                        "only the last one counts",
                        self.path,
                        key_node.start_mark.line + 1,
                    )
                )

            # The last one wins in the data, so it wins here too.
            keys.add(key)
            self.lines[child_path] = key_node.start_mark.line + 1
            self.walk(value_node, child_path, ancestors)


class _SelfReferenceError(Exception):
    """An anchor that contains an alias to itself."""

    def __init__(self, line: int) -> None:
        """Remember the line of the anchor."""
        super().__init__(line)
        self.line = line


def _reader_error(path: Path, text: str, err: yaml.reader.ReaderError) -> Finding:
    """Turn a character YAML does not allow into a finding on its line."""
    line = text.count("\n", 0, err.position) + 1
    code = ord(err.character) if isinstance(err.character, str) else err.character
    message = f"Not valid YAML: the character #x{code:04x} is not allowed"
    return Finding(INVALID_FILE, message, path, line)


def _impossible_value(path: Path, node: yaml.Node | None, err: ValueError) -> Finding:
    """Find the value YAML reads but Python cannot hold: a date that does not exist.

    YAML reads 2025-02-30 as a date, unquoted, and building the data fails on
    it. The nodes still have it, with its line.
    """
    constructor = yaml.SafeLoader("")
    for scalar in _scalars(node):
        if scalar.tag != _TIMESTAMP_TAG:
            continue
        try:
            constructor.construct_yaml_timestamp(scalar)
        except ValueError:
            return Finding(
                INVALID_FILE,
                f"Not valid YAML: {scalar.value} is not a date that exists; "
                "put it in quotes if it is not meant as a date",
                path,
                scalar.start_mark.line + 1,
            )

    # Dates are the only known cause; anything else still gets reported.
    return Finding(INVALID_FILE, f"Not valid YAML: {err}", path)  # pragma: no cover


def _scalars(node: yaml.Node | None) -> Iterator[yaml.ScalarNode]:
    """Yield every scalar under a node, each node once."""
    stack, seen = [node], set()
    while stack:
        current = stack.pop()
        if current is None or id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, yaml.ScalarNode):
            yield current
        elif isinstance(current, yaml.MappingNode):
            stack.extend(item for pair in current.value for item in pair)
        elif isinstance(current, yaml.SequenceNode):
            stack.extend(current.value)


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
