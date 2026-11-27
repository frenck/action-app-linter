"""Validating documents against the JSON schemas that ship with the linter."""

from __future__ import annotations

import json
from datetime import date
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jsonschema import Draft7Validator
from jsonschema.exceptions import ValidationError, best_match

from .findings import Level, define_rule

if TYPE_CHECKING:
    from collections.abc import Iterator

    from .document import Document
    from .findings import Finding

SCHEMA = define_rule(
    "schema", Level.ERROR, "A value does not match what the Supervisor accepts."
)
UNKNOWN_KEY = define_rule(
    "unknown-key", Level.ERROR, "A key the Supervisor does not know."
)
DEFAULT_VALUE = define_rule(
    "default-value", Level.ERROR, "An option is set to its default; leave it out."
)

# Errors from these keywords only say that some other check failed.
_UMBRELLA_KEYWORDS = {"anyOf", "oneOf"}


@cache
def load_schema(name: str) -> dict[str, Any]:
    """Return one of the bundled schemas, by file name without extension."""
    schema_file = Path(__file__).parent / "schemas" / f"{name}.schema.json"
    return json.loads(schema_file.read_text(encoding="utf-8"))


@cache
def _validator(name: str) -> Draft7Validator:
    """Return a validator for one of the bundled schemas."""
    return Draft7Validator(load_schema(name))


def validate(document: Document, schema_name: str) -> Iterator[Finding]:
    """Check a document against a schema, one finding per problem."""
    errors = _validator(schema_name).iter_errors(document.data)
    for error in sorted(errors, key=lambda error: list(map(str, error.absolute_path))):
        yield from _findings(document, error)


def defaults(document: Document, schema_name: str) -> Iterator[Finding]:
    """Find top level options that are set to the value they have anyway.

    Deprecated options are left alone: they get a better message of their own.
    """
    properties = load_schema(schema_name)["properties"]
    for key, value in document.data.items():
        prop = properties.get(key, {})
        if "default" not in prop or prop.get("deprecated"):
            continue

        default = prop["default"]
        # Compare types too, or 0 would count as the default false.
        if type(value) is type(default) and value == default:
            yield document.finding(
                DEFAULT_VALUE,
                f"'{key}' is set to {json.dumps(default)}, which is the default; "
                "remove it",
                (key,),
            )


def _findings(document: Document, error: ValidationError) -> Iterator[Finding]:
    """Turn a validation error into findings with a readable message."""
    for cause in _causes(error):
        path = list(cause.absolute_path)

        if cause.validator == "additionalProperties":
            known = _schema(cause).get("properties", {})
            for key in _instance(cause):
                if key not in known:
                    key_path = [*path, key]
                    message = f"'{_dotted(key_path)}' is not a known option"
                    yield document.finding(UNKNOWN_KEY, message, key_path)
            continue

        # A key with a bad name: the error is on the mapping, the instance is
        # the key, so point at the key itself.
        if "propertyNames" in cause.schema_path:
            key_path = [*path, _instance(cause)]
            yield document.finding(
                SCHEMA, _message(cause, key_path, key=True), key_path
            )
            continue

        yield document.finding(SCHEMA, _message(cause, path), path)


def _causes(error: ValidationError) -> Iterator[ValidationError]:
    """Dig into anyOf and oneOf for the errors that explain what is wrong.

    A value that fails every branch fails each of them for a reason, and most
    of those reasons are noise: a string that does not match its pattern is
    not helped by hearing it is not an object either. A branch only counts
    when the value is of the kind it describes. When one branch is left, all
    of its errors matter; with more, the best of them does.
    """
    if error.validator not in _UMBRELLA_KEYWORDS or not error.context:
        yield error
        return

    branches: dict[str | int, list[ValidationError]] = {}
    for cause in error.context:
        branches.setdefault(cause.relative_schema_path[0], []).append(cause)

    applicable = [
        causes
        for causes in branches.values()
        if not all(_is_wrong_kind(cause) for cause in causes)
    ]

    if len(applicable) == 1:
        for cause in applicable[0]:
            yield from _causes(cause)
    elif applicable and (
        best := best_match(cause for causes in applicable for cause in causes)
    ):
        yield from _causes(best)
    else:
        yield error


def _is_wrong_kind(error: ValidationError) -> bool:
    """Return whether an error only says the value is not of the right kind."""
    return not error.relative_path and error.validator in {"const", "type"}


def _message(
    error: ValidationError, path: list[str | int], *, key: bool = False
) -> str:
    """Return the message for an error, saying which value it is about."""
    where = f"'{_dotted(path)}'" if path else "The file"
    if key:
        where = f"Key {where}"
    value = _instance(error)
    instance = _render(value)

    if error.validator in _UMBRELLA_KEYWORDS:
        kinds = sorted(
            {
                kind
                for cause in error.context or []
                if cause.validator == "type"
                for kind in _as_list(_validator_value(cause))
            }
            | {
                json.dumps(_validator_value(cause))
                for cause in error.context or []
                if cause.validator == "const"
            }
        )
        return f"{where} must be {' or '.join(kinds)}, not {_json_type(value)}"

    if error.validator == "pattern" and "description" in _schema(error):
        expected = _lower_first(_schema(error)["description"])
        if key:
            return f"{where} is not valid, expected {expected}"
        return f"{where} is {instance}, expected {expected}"

    if error.validator == "enum":
        # Values that also exist with a ! in front, to exclude them, are
        # listed once; the description tells about the !.
        options = [
            option
            for option in _validator_value(error)
            if not (
                isinstance(option, str)
                and option.startswith("!")
                and option[1:] in _validator_value(error)
            )
        ]
        allowed = ", ".join(json.dumps(option) for option in options)
        return f"{where} is {instance}, expected one of: {allowed}"

    if error.validator == "type":
        expected = _as_list(_validator_value(error))
        message = (
            f"{where} must be of type {' or '.join(expected)}, not {_json_type(value)}"
        )
        # The two mistakes YAML makes easy: quoting a boolean, and not quoting
        # a version, which turns 1.10 into the number 1.1, or 2025-01-01 into
        # a date.
        if "boolean" in expected and str(value).lower() in {"true", "false"}:
            return f"{message}; remove the quotes"
        if "string" in expected and _json_type(value) in {"date", "integer", "number"}:
            return f"{message}; put it in quotes"
        return message

    if error.validator == "required":
        missing = error.message.removesuffix(" is a required property")
        return f"{missing} is required" if not path else f"{where} needs {missing}"

    return f"{where}: {error.message}"


# In this order: a boolean is an int to Python, and both are numbers. A date
# is not JSON, but YAML reads 2025-01-01 as one.
_JSON_TYPES: tuple[tuple[type, str], ...] = (
    (type(None), "null"),
    (date, "date"),
    (bool, "boolean"),
    (int, "integer"),
    (float, "number"),
    (str, "string"),
    (list, "array"),
)


def _render(value: Any) -> str:
    """Return a value the way JSON writes it.

    YAML has more types than JSON, such as dates; those show as text.
    """
    return json.dumps(value, default=str)


def _json_type(value: Any) -> str:
    """Return the JSON type name of a value, the way the schema names it."""
    for python_type, name in _JSON_TYPES:
        if isinstance(value, python_type):
            return name
    return "object"


# jsonschema sets these on every error a validator yields; its type stubs
# allow for them to be unset, which never happens for those errors.
def _instance(error: ValidationError) -> Any:
    """Return the value an error is about."""
    return error.instance


def _validator_value(error: ValidationError) -> Any:
    """Return what the failing keyword asked for, such as the allowed values."""
    return error.validator_value


def _schema(error: ValidationError) -> dict[str, Any]:
    """Return the part of the schema the value failed."""
    return error.schema if isinstance(error.schema, dict) else {}


def _as_list(value: str | list[str]) -> list[str]:
    """Return a type of a JSON schema as a list, as it can be one or several."""
    return value if isinstance(value, list) else [value]


def _dotted(path: list[str | int]) -> str:
    """Return a key path the way people write it, such as map.0.type."""
    return ".".join(str(part) for part in path)


def _lower_first(text: str) -> str:
    """Return the text with a lowercase first letter, to continue a sentence."""
    return text[:1].lower() + text[1:].rstrip(".")
