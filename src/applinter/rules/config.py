"""Checks on config.yaml."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlparse

from applinter.app import items, mapping, strings
from applinter.const import (
    ARCH_DEPRECATED,
    ARCH_SUPPORTED,
    INGRESS_DYNAMIC_PORTS,
    MACHINE_DEPRECATED,
    MAP_TYPES_CONFLICTING_WITH_CONFIG,
    MAP_TYPES_LEGACY,
    RE_IMAGE_DOMAIN,
    RE_IMAGE_PATH_COMPONENT,
    RE_MAP_ENTRY,
    SLUG_MAX_LENGTH,
    SNAPSHOT_OPTIONS,
    STARTUP_LEGACY,
)
from applinter.findings import Level, define_rule

from .registry import check

if TYPE_CHECKING:
    from collections.abc import Iterator

    from applinter.app import App
    from applinter.findings import Finding

DEPRECATED_ARCH = define_rule(
    "deprecated-arch",
    Level.WARNING,
    "An architecture Home Assistant no longer supports.",
)
DEPRECATED_MACHINE = define_rule(
    "deprecated-machine", Level.WARNING, "A machine Home Assistant no longer supports."
)
DEPRECATED_ADVANCED = define_rule(
    "deprecated-advanced", Level.WARNING, "The Supervisor ignores 'advanced'."
)
DEPRECATED_AUTO_UART = define_rule(
    "deprecated-auto-uart", Level.ERROR, "'auto_uart' was replaced by 'uart'."
)
DEPRECATED_CODENOTARY = define_rule(
    "deprecated-codenotary", Level.ERROR, "The Supervisor no longer uses 'codenotary'."
)
DEPRECATED_DEVICES = define_rule(
    "deprecated-devices", Level.ERROR, "'devices' uses the old format with permissions."
)
DEPRECATED_MAP_CONFIG = define_rule(
    "deprecated-map-config",
    Level.WARNING,
    "'config' in 'map' was replaced by 'homeassistant_config'.",
)
DEPRECATED_MAP_TYPE = define_rule(
    "deprecated-map-type", Level.WARNING, "A map type that was renamed for apps."
)
DEPRECATED_SNAPSHOT = define_rule(
    "deprecated-snapshot", Level.ERROR, "The snapshot options were renamed to backup."
)
DEPRECATED_STARTUP = define_rule(
    "deprecated-startup", Level.ERROR, "'startup' uses 'before' or 'after'."
)
DEPRECATED_TMPFS = define_rule(
    "deprecated-tmpfs", Level.ERROR, "'tmpfs' uses the old format; it is a boolean now."
)
DEPRECATED_WATCHDOG = define_rule(
    "deprecated-watchdog",
    Level.ERROR,
    "'watchdog' is obsolete; use a HEALTHCHECK in the Dockerfile.",
)
MAP_CONFLICT = define_rule(
    "map-conflict", Level.ERROR, "'map' holds folders that rule each other out."
)
FULL_ACCESS = define_rule(
    "full-access", Level.WARNING, "'full_access' gives the app all hardware."
)
FULL_ACCESS_REDUNDANT = define_rule(
    "full-access-redundant",
    Level.ERROR,
    "'full_access' already covers 'devices', 'gpio', 'uart' and 'usb'.",
)
INGRESS_WEBUI = define_rule(
    "ingress-webui", Level.ERROR, "'webui' is not used when Ingress is enabled."
)
INGRESS_PORT_RANDOM = define_rule(
    "ingress-port-random",
    Level.ERROR,
    "A random Ingress port is only needed on the host network.",
)
INGRESS_PORT_RESERVED = define_rule(
    "ingress-port-reserved",
    Level.ERROR,
    "A mapped port is in the range random Ingress ports come from.",
)
COLD_BACKUP_HOOKS = define_rule(
    "cold-backup-hooks",
    Level.ERROR,
    "Backup commands do not run for cold backups.",
)
INVALID_IMAGE = define_rule(
    "invalid-image", Level.ERROR, "'image' is not a valid image name."
)
INVALID_URL = define_rule("invalid-url", Level.ERROR, "'url' is not a valid URL.")
INVALID_SLUG = define_rule(
    "invalid-slug",
    Level.ERROR,
    "The slug is too long, or does not make a valid image name.",
)
OPTION_NOT_IN_SCHEMA = define_rule(
    "option-not-in-schema",
    Level.ERROR,
    "An option has no entry in the schema, so the Supervisor drops it.",
)
PORT_DESCRIPTION_UNKNOWN = define_rule(
    "port-description-unknown",
    Level.WARNING,
    "'ports_description' describes a port that is not in 'ports'.",
)


@check
def deprecated_arch(app: App) -> Iterator[Finding]:
    """Flag the 32-bit architectures Home Assistant dropped."""
    for index, arch in enumerate(app.arch):
        if arch in ARCH_DEPRECATED:
            yield app.config.finding(
                DEPRECATED_ARCH,
                f"Architecture '{arch}' is no longer supported since Home Assistant "
                "2025.12; remove it from 'arch'",
                ("arch", index),
            )


@check
def deprecated_machine(app: App) -> Iterator[Finding]:
    """Flag the machines Home Assistant dropped along with their architecture."""
    for index, machine in enumerate(strings(app.config.data, "machine")):
        if machine.removeprefix("!") in MACHINE_DEPRECATED:
            yield app.config.finding(
                DEPRECATED_MACHINE,
                f"Machine '{machine.removeprefix('!')}' is no longer supported by "
                "Home Assistant; remove it from 'machine'",
                ("machine", index),
            )


@check
def deprecated_options(app: App) -> Iterator[Finding]:
    """Flag options the Supervisor renamed, replaced or stopped using."""
    config = app.config.data

    if "advanced" in config:
        yield app.config.finding(
            DEPRECATED_ADVANCED,
            "'advanced' is ignored by the Supervisor since 2026.03; remove it",
            ("advanced",),
        )

    if "auto_uart" in config:
        yield app.config.finding(
            DEPRECATED_AUTO_UART,
            "'auto_uart' is deprecated; use 'uart'",
            ("auto_uart",),
        )

    if "codenotary" in config:
        yield app.config.finding(
            DEPRECATED_CODENOTARY,
            "'codenotary' is no longer used; remove it",
            ("codenotary",),
        )

    if "watchdog" in config:
        yield app.config.finding(
            DEPRECATED_WATCHDOG,
            "'watchdog' is obsolete; use a HEALTHCHECK in the Dockerfile instead",
            ("watchdog",),
        )

    for old, new in SNAPSHOT_OPTIONS.items():
        if old in config:
            yield app.config.finding(
                DEPRECATED_SNAPSHOT, f"'{old}' was renamed; use '{new}'", (old,)
            )


@check
def deprecated_formats(app: App) -> Iterator[Finding]:
    """Flag values in a format the Supervisor still migrates, but deprecated."""
    config = app.config.data

    startup = config.get("startup")
    if isinstance(startup, str) and startup in STARTUP_LEGACY:
        yield app.config.finding(
            DEPRECATED_STARTUP,
            f"'startup' value '{startup}' is deprecated; "
            f"use '{STARTUP_LEGACY[startup]}'",
            ("startup",),
        )

    if isinstance(config.get("tmpfs"), str):
        yield app.config.finding(
            DEPRECATED_TMPFS,
            "'tmpfs' uses a deprecated format; it is a boolean now",
            ("tmpfs",),
        )

    for index, device in enumerate(strings(config, "devices")):
        if ":" in device:
            yield app.config.finding(
                DEPRECATED_DEVICES,
                f"Device '{device}' uses a deprecated format; "
                f"list the path only, such as '{device.split(':')[0]}'",
                ("devices", index),
            )


@check
def map_folders(app: App) -> Iterator[Finding]:
    """Check the folders in map for legacy names and conflicts."""
    types: dict[str, int] = {}
    for index, entry in enumerate(items(app.config.data, "map")):
        if (map_type := _map_type(entry)) is not None:
            types.setdefault(map_type, index)

    for legacy, current in MAP_TYPES_LEGACY.items():
        if legacy not in types:
            continue

        if current in types:
            yield app.config.finding(
                MAP_CONFLICT,
                f"'map' has both '{legacy}' and '{current}'; "
                f"the Supervisor ignores '{legacy}', remove it",
                ("map", types[legacy]),
            )
        else:
            yield app.config.finding(
                DEPRECATED_MAP_TYPE,
                f"'map' type '{legacy}' was renamed; use '{current}', which needs "
                "Supervisor 2026.07 or newer",
                ("map", types[legacy]),
            )

    if "config" not in types:
        return

    if conflicting := sorted(MAP_TYPES_CONFLICTING_WITH_CONFIG & types.keys()):
        names = ", ".join(f"'{name}'" for name in conflicting)
        yield app.config.finding(
            MAP_CONFLICT,
            f"'map' has 'config' together with {names}, which the Supervisor "
            "ignores when 'config' is mapped",
            ("map", types["config"]),
        )
    else:
        yield app.config.finding(
            DEPRECATED_MAP_CONFIG,
            "'map' type 'config' was replaced by 'homeassistant_config'. See: "
            "https://developers.home-assistant.io/blog/2023/11/06/public-addon-config",
            ("map", types["config"]),
        )


@check
def full_access(app: App) -> Iterator[Finding]:
    """Check full hardware access, which makes the specific options pointless."""
    config = app.config.data
    if not config.get("full_access"):
        return

    yield app.config.finding(
        FULL_ACCESS,
        "'full_access' gives the app all hardware; consider options such as "
        "'devices' instead",
        ("full_access",),
    )

    for key in ("devices", "gpio", "uart", "usb"):
        if config.get(key):
            yield app.config.finding(
                FULL_ACCESS_REDUNDANT,
                f"'{key}' is not needed with 'full_access'; remove it",
                (key,),
            )


@check
def ingress(app: App) -> Iterator[Finding]:
    """Check the Ingress settings."""
    config = app.config.data
    if not config.get("ingress"):
        return

    if config.get("webui"):
        yield app.config.finding(
            INGRESS_WEBUI, "'webui' is not used with Ingress; remove it", ("webui",)
        )

    if config.get("ingress_port") != 0:
        return

    if not config.get("host_network"):
        yield app.config.finding(
            INGRESS_PORT_RANDOM,
            "'ingress_port' is 0, but the app does not run on the host network; "
            "a fixed port works fine there",
            ("ingress_port",),
        )

    # A random Ingress port could land on one of these, exposing Ingress on
    # the host without authentication. The Supervisor refuses the app.
    for port in mapping(config, "ports"):
        number = str(port).partition("/")[0]
        if number.isdigit() and int(number) in INGRESS_DYNAMIC_PORTS:
            yield app.config.finding(
                INGRESS_PORT_RESERVED,
                f"Port {number} is in the range random Ingress ports come from "
                f"({INGRESS_DYNAMIC_PORTS.start}-{INGRESS_DYNAMIC_PORTS.stop - 1}); "
                "the Supervisor refuses this app",
                ("ports", port),
            )


@check
def cold_backup_hooks(app: App) -> Iterator[Finding]:
    """Check for backup commands, which a cold backup never runs."""
    config = app.config.data
    if config.get("backup") != "cold":
        return

    for key in ("backup_pre", "backup_post"):
        if key in config:
            yield app.config.finding(
                COLD_BACKUP_HOOKS,
                f"'{key}' does not run for cold backups; remove it",
                (key,),
            )


@check
def image(app: App) -> Iterator[Finding]:
    """Check the image name the way the Supervisor does."""
    value = app.config.data.get("image")
    if not isinstance(value, str):
        return

    if problem := image_problem(value):
        yield app.config.finding(INVALID_IMAGE, f"'image' {problem}", ("image",))


@check
def url(app: App) -> Iterator[Finding]:
    """Check the URL has a scheme and a host, like the Supervisor wants."""
    value = app.config.data.get("url")
    if not isinstance(value, str):
        return

    parsed = urlparse(value)
    if not parsed.scheme or not parsed.netloc:
        yield app.config.finding(
            INVALID_URL, f"'url' is not a valid URL: '{value}'", ("url",)
        )


@check
def slug(app: App) -> Iterator[Finding]:
    """Check the slug fits the limits the Supervisor puts on it."""
    config = app.config.data
    value = config.get("slug")
    if not isinstance(value, str) or not value:
        return

    if len(value) > SLUG_MAX_LENGTH:
        yield app.config.finding(
            INVALID_SLUG,
            f"'slug' is {len(value)} characters long; the Supervisor does not load "
            f"apps from a repository with a slug longer than {SLUG_MAX_LENGTH}",
            ("slug",),
        )

    # Without an image the Supervisor builds one, and names it after the slug.
    if "image" not in config and not RE_IMAGE_PATH_COMPONENT.match(
        f"addon-{value.lower()}"
    ):
        yield app.config.finding(
            INVALID_SLUG,
            f"'slug' '{value}' does not make a valid image name, so the Supervisor "
            "cannot build the app",
            ("slug",),
        )


@check
def options_in_schema(app: App) -> Iterator[Finding]:
    """Check every default option has a schema entry."""
    if (schema := app.schema) is None:
        return

    for key in mapping(app.config.data, "options"):
        if key not in schema:
            yield app.config.finding(
                OPTION_NOT_IN_SCHEMA,
                f"Option '{key}' is not in 'schema', so the Supervisor drops it",
                ("options", key),
            )


@check
def ports_description(app: App) -> Iterator[Finding]:
    """Check every port description belongs to a port."""
    ports = {str(port) for port in mapping(app.config.data, "ports")}
    for port in mapping(app.config.data, "ports_description"):
        if str(port) not in ports:
            yield app.config.finding(
                PORT_DESCRIPTION_UNKNOWN,
                f"'ports_description' describes port '{port}', which is not in 'ports'",
                ("ports_description", port),
            )


def image_problem(value: str) -> str | None:
    """Return what is wrong with an image name, or None when it is fine.

    A port of docker_image() in supervisor/validate.py, with the registry
    split from split_docker_domain() in supervisor/docker/utils.py.
    """
    if not value:
        return "is empty"

    registry, separator, path = value.partition("/")
    if not separator or not (
        registry == "localhost"
        or "." in registry
        or ":" in registry
        or registry.lower() != registry
    ):
        # The first part is an organization on Docker Hub, not a registry.
        registry, path = "", value

    if registry and registry != registry.lower():
        return f"must have a lowercase registry, not '{registry}'"
    if registry and not RE_IMAGE_DOMAIN.fullmatch(registry):
        return f"has an invalid registry '{registry}'"
    if not path:
        return "has no name after the registry"
    if ":" in path:
        return "must not have a tag; the Supervisor adds the version itself"

    for component in path.split("/"):
        if not RE_IMAGE_PATH_COMPONENT.match(component):
            return (
                f"has an invalid part '{component}'; use lowercase letters, digits "
                "and separators such as - and ."
            )

    return None


def _map_type(entry: object) -> str | None:
    """Return the folder type of a map entry, in either of its forms."""
    if isinstance(entry, dict):
        map_type = entry.get("type")
        return map_type if isinstance(map_type, str) else None

    if isinstance(entry, str) and (match := RE_MAP_ENTRY.match(entry)):
        return match.group(1)

    return None


ARCH_UNSUPPORTED = define_rule(
    "arch-unsupported",
    Level.ERROR,
    "The app supports no architecture Home Assistant still runs on.",
)
MACHINE_UNAVAILABLE = define_rule(
    "machine-unavailable",
    Level.ERROR,
    "'machine' leaves no machine the app can be installed on.",
)
LEGACY_NESTED_OPTION = define_rule(
    "legacy-nested-option",
    Level.WARNING,
    "A legacy app has an option that cannot be passed as an environment variable.",
)


@check
def arch_supported(app: App) -> Iterator[Finding]:
    """Check the app runs on at least one architecture that is still supported.

    Otherwise the Supervisor suggests users remove it: supervisor/apps/app.py,
    IssueType.DEPRECATED_ARCH_APP.
    """
    if not isinstance(app.config.data.get("arch"), list):
        return

    if not ARCH_SUPPORTED & set(app.arch):
        supported = " or ".join(f"'{arch}'" for arch in sorted(ARCH_SUPPORTED))
        yield app.config.finding(
            ARCH_UNSUPPORTED,
            f"'arch' has no architecture Home Assistant supports; add {supported}",
            ("arch",),
        )


@check
def machine_available(app: App) -> Iterator[Finding]:
    """Check the machine list leaves a machine to install the app on.

    The Supervisor only installs an app on a machine that is in the list,
    so a list of exclusions alone rules out every machine:
    supervisor/apps/model.py, _validate_availability().
    """
    machines = strings(app.config.data, "machine")
    if not machines:
        return

    included = [machine for machine in machines if not machine.startswith("!")]
    if not included:
        yield app.config.finding(
            MACHINE_UNAVAILABLE,
            "'machine' only excludes machines, but the Supervisor only installs "
            "apps on machines in the list, so this app installs nowhere; list the "
            "machines it supports, or remove 'machine'",
            ("machine",),
        )
    elif all(machine in MACHINE_DEPRECATED for machine in included):
        yield app.config.finding(
            MACHINE_UNAVAILABLE,
            "'machine' only lists machines Home Assistant no longer supports",
            ("machine",),
        )


@check
def legacy_options(app: App) -> Iterator[Finding]:
    """Check a legacy app only has options that fit in an environment variable.

    supervisor/docker/app.py: environment, which skips the others.
    """
    if not app.config.data.get("legacy"):
        return

    for key, value in mapping(app.config.data, "options").items():
        if not isinstance(value, (int, str)):
            yield app.config.finding(
                LEGACY_NESTED_OPTION,
                f"Option '{key}' is not a whole number or text, so a legacy app "
                "does not get it as an environment variable",
                ("options", key),
            )
