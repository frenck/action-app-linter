"""The command line, which is also what the GitHub Action runs."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .findings import RULES, Level
from .linter import lint
from .output import report

if TYPE_CHECKING:
    from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    """Run the linter, and return the exit code: 1 when there are errors."""
    parser = _parser()
    arguments = parser.parse_args(argv)

    # Read here rather than as a default of --ignore, so a typo in the
    # action input is a usage error like a typo on the command line.
    try:
        ignored = set(_rule_ids(os.environ.get("INPUT_IGNORE", "")))
    except argparse.ArgumentTypeError as err:
        parser.error(f"INPUT_IGNORE: {err}")
    ignored.update(arguments.ignore or [])

    findings = [
        finding
        for path in arguments.paths
        for finding in lint(path, community=arguments.community)
        if finding.rule.id not in ignored
    ]

    github = arguments.format == "github" or (
        arguments.format == "auto" and os.environ.get("GITHUB_ACTIONS") == "true"
    )
    report(findings, sys.stdout, github=github)

    return int(any(finding.level is Level.ERROR for finding in findings))


def _parser() -> argparse.ArgumentParser:
    """Return the argument parser.

    The GitHub Action passes its inputs as INPUT_* environment variables, so
    each option falls back to the one for its input.
    """
    parser = argparse.ArgumentParser(
        prog="app-linter",
        description="Lint the configuration of Home Assistant apps.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=_input_paths(),
        metavar="PATH",
        help="directory of an app, where its config.yaml is (default: INPUT_PATH)",
    )
    parser.add_argument(
        "--community",
        action="store_true",
        default=os.environ.get("INPUT_COMMUNITY", "").strip().lower() == "true",
        help="add the checks of the Home Assistant Community Apps project",
    )
    parser.add_argument(
        "--ignore",
        action="extend",
        type=_rule_ids,
        metavar="RULES",
        help=(
            "rules to skip, separated by commas; can be given more than once, "
            "and adds to INPUT_IGNORE"
        ),
    )
    parser.add_argument(
        "--format",
        choices=["auto", "github", "text"],
        default="auto",
        help="github prints annotations; auto does when it runs on GitHub Actions",
    )
    parser.add_argument(
        "--version", action=_VersionAction, help="show the version and exit"
    )
    return parser


class _VersionAction(argparse.Action):
    """Print the version, reading it only when asked for.

    Reading package metadata costs a tenth of a second at startup, which every
    run of the action would pay for a flag it never uses.
    """

    def __init__(self, option_strings: list[str], dest: str, **kwargs: Any) -> None:
        """Take no value, like the built-in version action."""
        super().__init__(option_strings, dest, nargs=0, **kwargs)

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,  # noqa: ARG002 - argparse hands it over
        values: str | Sequence[Any] | None,  # noqa: ARG002
        option_string: str | None = None,  # noqa: ARG002
    ) -> None:
        """Print the version and stop."""
        from importlib.metadata import version  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

        # On stdout, like the version action of argparse itself.
        sys.stdout.write(f"{parser.prog} {version('app-linter')}\n")
        parser.exit()


def _input_paths() -> list[Path]:
    """Return the app directory the GitHub Action was given, if any."""
    if path := os.environ.get("INPUT_PATH", "").strip():
        return [Path(path)]
    return [Path()]


def _rule_ids(value: str) -> list[str]:
    """Split a list of rule identifiers, refusing ones that do not exist."""
    rule_ids = [rule_id for rule_id in re.split(r"[\s,]+", value) if rule_id]
    if unknown := sorted(set(rule_ids) - RULES.keys()):
        msg = f"unknown rule: {', '.join(unknown)}"
        raise argparse.ArgumentTypeError(msg)
    return rule_ids
