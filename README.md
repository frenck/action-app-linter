# 🚀 Frenck's GitHub Action: Home Assistant App Linter

[![GitHub Release][releases-shield]][releases]
![Project Stage][project-stage-shield]
![Project Maintenance][maintenance-shield]
[![License][license-shield]](LICENSE.md)

[![Sponsor Frenck via GitHub Sponsors][github-sponsors-shield]][github-sponsors]

🚀 Frenck's GitHub Action for linting Home Assistant Apps.

## About

This GitHub Action checks the configuration of a Home Assistant app the way
the Supervisor reads it: `config.yaml`, `build.yaml` and the files in
`translations/`, in YAML or JSON.

It finds what the Supervisor refuses, what it silently ignores, what it
deprecated, and options set to the value they have anyway. Every problem is
an annotation on the line it is on, so it shows up right in the pull request.

## Usage

```yaml
name: Lint
on: [push, pull_request]
jobs:
  build:
    name: App configuration
    runs-on: ubuntu-latest
    steps:
      - name: ⤵️ Check out code from GitHub
        uses: actions/checkout@v7
      - name: 🚀 Run Home Assistant App Lint
        uses: frenck/action-app-linter@v3.0.0
        with:
          path: "./example"
```

## Arguments

|    Input    | Description                                                            |    Usage     |
| :---------: | :--------------------------------------------------------------------- | :----------: |
|   `path`    | Path to the app, the directory its `config.yaml` is in.                | **Required** |
| `community` | Add the checks of the Home Assistant Community Apps project.           |  _Optional_  |
|  `ignore`   | Rules to skip, separated by commas or newlines, such as `full-access`. |  _Optional_  |

Errors fail the run, warnings do not.

## Rules

Each finding names its rule, so you can look it up here, or skip it with the
`ignore` input.

| Rule                         | Level   | What it finds                                                                 |
| ---------------------------- | ------- | ----------------------------------------------------------------------------- |
| `app-not-found`              | error   | There is no app configuration.                                                |
| `invalid-file`               | error   | A file is not valid YAML or JSON, or not a mapping.                           |
| `multiple-files`             | error   | A file exists in more than one format, and only one of them is read.          |
| `duplicate-key`              | error   | A key is set more than once; only the last one counts.                        |
| `schema`                     | error   | A value does not match what the Supervisor accepts.                           |
| `unknown-key`                | error   | A key the Supervisor does not know.                                           |
| `default-value`              | error   | An option is set to its default; leave it out.                                |
| `invalid-image`              | error   | `image` is not a valid image name.                                            |
| `invalid-slug`               | error   | The slug is too long, or does not make a valid image name.                    |
| `invalid-url`                | error   | `url` is not a valid URL.                                                     |
| `option-not-in-schema`       | error   | An option has no entry in the schema, so the Supervisor drops it.             |
| `port-description-unknown`   | warning | `ports_description` describes a port that is not in `ports`.                  |
| `map-conflict`               | error   | `map` holds folders that rule each other out.                                 |
| `full-access`                | warning | `full_access` gives the app all hardware.                                     |
| `full-access-redundant`      | error   | `full_access` already covers `devices`, `gpio`, `uart` and `usb`.             |
| `ingress-webui`              | error   | `webui` is not used when Ingress is enabled.                                  |
| `ingress-port-random`        | error   | A random Ingress port is only needed on the host network.                     |
| `ingress-port-reserved`      | error   | A mapped port is in the range random Ingress ports come from.                 |
| `cold-backup-hooks`          | error   | Backup commands do not run for cold backups.                                  |
| `deprecated-arch`            | warning | An architecture Home Assistant no longer supports.                            |
| `deprecated-machine`         | warning | A machine Home Assistant no longer supports.                                  |
| `deprecated-advanced`        | warning | The Supervisor ignores `advanced`.                                            |
| `deprecated-auto-uart`       | error   | `auto_uart` was replaced by `uart`.                                           |
| `deprecated-codenotary`      | error   | The Supervisor no longer uses `codenotary`.                                   |
| `deprecated-devices`         | error   | `devices` uses the old format with permissions.                               |
| `deprecated-map-config`      | warning | `config` in `map` was replaced by `homeassistant_config`.                     |
| `deprecated-map-type`        | warning | A map type that was renamed for apps.                                         |
| `deprecated-snapshot`        | error   | The snapshot options were renamed to backup.                                  |
| `deprecated-squash`          | error   | `squash` is not supported by Docker BuildKit, which the Supervisor uses.      |
| `deprecated-startup`         | error   | `startup` uses `before` or `after`.                                           |
| `deprecated-tmpfs`           | error   | `tmpfs` uses the old format; it is a boolean now.                             |
| `deprecated-watchdog`        | error   | `watchdog` is obsolete; use a HEALTHCHECK in the Dockerfile.                  |
| `build-deprecated`           | warning | The Supervisor deprecated `build.yaml` for the apps it builds.                |
| `build-arch-missing`         | error   | An architecture in `config.yaml` has no base image in `build.yaml`.           |
| `build-arch-unused`          | warning | A base image in `build.yaml` is for an architecture the app does not support. |
| `translation-unknown-option` | warning | A translation names an option that is not in the schema.                      |
| `translation-unknown-port`   | warning | A translation describes a port that is not in `ports`.                        |
| `community-version`          | error   | The version of a community app is `dev`; releases set the real one.           |
| `community-build-file`       | error   | A community app needs a `build.yaml` with a base image per architecture.      |

The last two only run with `community: true`. In that mode `build-deprecated`
does not run: the Community Apps workflows still read the base images from
`build.yaml`.

## Running it locally

The linter is a Python package, and the action runs the same command:

```bash
uvx --from git+https://github.com/frenck/action-app-linter app-linter ./example
```

Give it more than one directory to lint several apps at once. `--community`
and `--ignore` work like the inputs of the action, and `--format github`
prints the annotations instead of plain lines.

## Editor support

The JSON schemas in [`src/applinter/schemas`](src/applinter/schemas) work in
any editor that supports them. For example, with the YAML extension for
Visual Studio Code, put this at the top of `config.yaml`:

```yaml
# yaml-language-server: $schema=https://raw.githubusercontent.com/frenck/action-app-linter/main/src/applinter/schemas/config.schema.json
```

## Upgrading from version 2

Version 3 is a rewrite, and it is stricter. It checks a lot more of what the
Supervisor checks, so an app that passed version 2 may fail version 3. What
changed:

- The checks now follow the current Supervisor: new machines and
  capabilities pass, and values the Supervisor refuses (such as a `timeout`
  below 10, an `image` with a tag, or a bad option type in `schema`) fail.
- `supervisor_api_tcp: true` is no longer flagged as a default. The
  Supervisor has no default on purpose, as it will change it.
- Translations are checked, and so are `options` against `schema` and
  `ports_description` against `ports`.
- `apparmor` must be a boolean; a custom profile goes in `apparmor.txt`.
- Findings point at the line, and name the rule.
- The action no longer builds an image when it runs, so it starts in seconds.
- There is no moving `v3` tag. Pin an exact version, and let Dependabot or
  Renovate bump it.

## Versions & Updating

Releases are based on [Semantic Versioning][semver], and use the format of
`MAJOR.MINOR.PATCH`. In a nutshell, the version will be incremented based on
the following:

- `MAJOR`: Incompatible or major changes.
- `MINOR`: Backwards-compatible new features and enhancements.
- `PATCH`: Backwards-compatible bugfixes and package updates.

Releases are immutable, and every tag is an exact version. Nothing like
`v3` moves along with new releases, so a run never changes under you. Pin a
version, or better, the commit SHA of one:

```yaml
- name: 🚀 Run Home Assistant App Lint
  uses: frenck/action-app-linter@v3.0.0
```

### Automatically update using Dependabot

Dependabot can open a pull request on your repository whenever there is a
new release. You can instantly see if the new version works (as the pull
request shows the success or failure status) and you can decide to merge it.

To enable Dependabot, create a file called `.github/dependabot.yaml`:

```yaml
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: daily
```

## Changelog & Releases

This repository keeps a change log using [GitHub's releases][releases]
functionality.

## Contributing

This is an active open-source project. We are always open to people who want to
use the code or contribute to it.

We've set up a separate document for our
[contribution guidelines](.github/CONTRIBUTING.md).

Thank you for being involved! :heart_eyes:

## Authors & contributors

The original setup of this repository is by [Franck Nijhof][frenck].

For a full list of all authors and contributors,
check [the contributor's page][contributors].

## License

MIT License

Copyright (c) 2021-2026 Franck Nijhof

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

[contributors]: https://github.com/frenck/action-app-linter/graphs/contributors
[frenck]: https://github.com/frenck
[github-sponsors-shield]: https://frenck.dev/wp-content/uploads/2019/12/github_sponsor.png
[github-sponsors]: https://github.com/sponsors/frenck
[license-shield]: https://img.shields.io/github/license/frenck/action-app-linter.svg
[maintenance-shield]: https://img.shields.io/maintenance/yes/2026.svg
[project-stage-shield]: https://img.shields.io/badge/project%20stage-production%20ready-brightgreen.svg
[releases-shield]: https://img.shields.io/github/release/frenck/action-app-linter.svg
[releases]: https://github.com/frenck/action-app-linter/releases
[semver]: http://semver.org/spec/v2.0.0.html
