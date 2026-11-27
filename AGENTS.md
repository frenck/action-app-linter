# AGENTS.md

Guidance for AI coding agents (and humans) working in this repository. This file
follows the [agents.md](https://agents.md) convention. `CLAUDE.md` is a symlink
to this file, so Claude-compatible tooling reads the same guidance.

## What this project is

The app linter checks the configuration of a Home Assistant app the way the
Supervisor reads it: `config.yaml`, `build.yaml` and `translations/*.yaml`, in
YAML or JSON. It runs as a GitHub Action, a container image and a CLI. Every
problem is a finding with a rule, a level (only errors fail a run), a message
and, when known, a line.

## Project layout

| Path                   | Purpose                                                  |
| ---------------------- | -------------------------------------------------------- |
| `src/applinter/`       | The package                                              |
| `  cli.py`             | Command line, and the INPUT\_\* variables of the action  |
| `  linter.py`          | Finds the files of an app, and runs everything on them   |
| `  document.py`        | Reads YAML and JSON, keeping the line of every value     |
| `  schema.py`          | JSON schema validation, turned into readable findings    |
| `  schemas/`           | The JSON schemas, also usable in editors                 |
| `  rules/`             | The checks a schema cannot express, one module per file  |
| `  const.py`           | What the linter knows about the Supervisor, with sources |
| `  findings.py`        | `Rule`, `Finding` and the registry of all rules          |
| `  output.py`          | Everything printed: plain lines or GitHub annotations    |
| `tests/fixtures/apps/` | Apps, valid and broken on purpose, one directory each    |
| `tests/`               | pytest suite with syrupy snapshots                       |
| `action.yaml`          | The GitHub Action; runs the published image              |
| `Dockerfile`           | The container image, built from the wheel                |

## Commands

This is a [uv][uv] project that also uses Node.js for Prettier, with
[prek][prek] running the hooks. Set up and run the gate with:

```bash
npm install
uv sync --group dev
uv run prek run --all-files   # lint, format, type, and test hooks
uv run pytest                 # just the tests
```

During iteration, running a single tool directly is fine and faster:
`uv run pytest -k ...`, `uv run ruff check .`, `uv run ty check`. Update
snapshots with `uv run pytest --snapshot-update` and review the diff before
committing it.

## Conventions

- The Supervisor is the specification. `supervisor/apps/validate.py` is where
  most of it lives. When a check or a schema value comes from the Supervisor,
  say where in a comment, so the next person can check it still holds.
- Structure goes in the JSON schemas; everything else is a check in
  `rules/`. A check is a function decorated with `@check` that yields
  findings. It runs on files that may have failed the schema, so it never
  trusts a value to have the right type; use `App.arch`, `mapping()` and
  `strings()` from `app.py`.
- Every rule is defined once with `rule()`, and listed in the README. A test
  fails when one is missing there.
- Forms the Supervisor still migrates (such as `snapshot` or `tmpfs` as a
  string) stay valid in the schema, marked `deprecated`, so their own rule
  explains them instead of a generic schema error.
- Messages name the option the way people write it (`map.0.type`), say what
  is wrong, and what to do about it.
- New checks need a fixture app that triggers them; snapshots cover the rest.
- Every test carries a one-line docstring describing what it verifies.
  Coverage is enforced at 95%.
- Comments explain the why, not the what. Clarity over cleverness, clear names,
  and blank lines between logical steps.

## Writing and voice

English for all public artifacts (commits, PRs, issues). Held to a high bar:
clear, honest, no filler. Avoid:

- AI cheerleading and marketing speak (leverage, synergize, delight).
- Em-dashes and en-dashes anywhere. Use a period, colon, comma, or parentheses;
  hyphen only for compound words. Restructure a sentence rather than reach for one.
- "e.g.", "i.e.", "etc."; write "like", "for example", "such as".
- CAPS for emphasis (use italics); "click" as a verb (use "select").
- "HA"/"HASS"; write "Home Assistant" in full, and never frame it as fragile.
- "master/slave"; use "client/server", "leader/follower", "main/replica".

See [AI_POLICY.md](AI_POLICY.md) for the contribution policy around AI tooling.

## Gotchas

- JSON files are parsed as JSON, and read a second time as YAML only for the
  line numbers. Tabs are swapped for spaces first: they are valid JSON
  whitespace but not valid YAML, and swapping them keeps every line in place.
- The `default-value` rule compares types too, or `0` would count as the
  default `false`. Options without a default in the Supervisor (such as
  `supervisor_api_tcp`) must not get one in the schema.
- An `anyOf` error is expanded into the errors of the branch the value is of
  the kind for; see `_causes()` in `schema.py`. Without that, a bad string
  gets told it is not an object.
- The fixture apps are broken on purpose. Prettier, yamllint and the prek
  hooks skip `tests/fixtures/`; keep it that way.
- prek hands pylint the files one by one, so `ignore = ["tests"]` does not keep
  it out of the tests.
- coverage needs `source_pkgs`, not `source`: with the src layout a bare
  package name silently measures nothing.

## Releasing

Releases are immutable: once published, a release and its tag never change.
So nothing gets published by hand. Release-drafter keeps a draft with the
next version; the release pull request points `action.yaml` at that version
(`docker://ghcr.io/frenck/action-app-linter:<version>`). Then the Release
workflow, started with "Run workflow" on `main`:

1. checks that every workflow run on that commit passed, that there is one
   draft whose tag does not exist yet, and that `action.yaml` points at it;
2. builds the package;
3. pushes the image to GHCR, so the release never points at a missing one;
4. publishes the draft, with its tag on that very commit.

A job that fails after the release is published can simply be re-run. Every
tag is an exact version; nothing like `v3` or `latest` moves along.

[prek]: https://github.com/j178/prek
[uv]: https://docs.astral.sh/uv/
