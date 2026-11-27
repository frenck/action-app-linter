"""What the linter knows about the Supervisor.

Most of this mirrors the Supervisor source, which is the only real
specification of an app. The comments say where each value comes from, so
the next person can check whether it still holds.
"""

import re

# supervisor/const.py: ARCH_DEPRECATED. No longer supported since Home
# Assistant 2025.12.
ARCH_DEPRECATED = frozenset({"armhf", "armv7", "i386"})

# supervisor/const.py: MACHINE_DEPRECATED. Dropped with the architectures.
MACHINE_DEPRECATED = frozenset(
    {
        "odroid-xu",
        "qemuarm",
        "qemux86",
        "raspberrypi",
        "raspberrypi2",
        "raspberrypi3",
        "raspberrypi4",
        "tinker",
    }
)

# supervisor/const.py: INGRESS_DYNAMIC_PORT_MIN and INGRESS_DYNAMIC_PORT_MAX.
# The range a random Ingress port (ingress_port: 0) is picked from.
INGRESS_DYNAMIC_PORTS = range(62000, 65500 + 1)

# supervisor/apps/const.py: SLUG_MAX_LENGTH. The Supervisor puts an 8
# character repository hash and an underscore in front of the slug, and the
# whole has to fit in the path of a Unix socket.
SLUG_MAX_LENGTH = 60 - len("12345678_")

# supervisor/apps/validate.py: the map types replaced in Supervisor 2026.07.
MAP_TYPES_LEGACY = {
    "addon_config": "app_config",
    "addons": "local_apps",
    "all_addon_configs": "all_app_configs",
}

# supervisor/apps/validate.py: map types the Supervisor ignores when
# "config" is mapped as well.
MAP_TYPES_CONFLICTING_WITH_CONFIG = frozenset(
    {"addon_config", "app_config", "homeassistant_config"}
)

# supervisor/apps/validate.py: RE_VOLUME, the string form of a map entry.
RE_MAP_ENTRY = re.compile(r"^(\w+)(?::(?:rw|ro))?$")

# supervisor/apps/validate.py: the startup values migrated in 2018.
STARTUP_LEGACY = {"after": "application", "before": "services"}

# supervisor/apps/validate.py: the options renamed to backup in 2021.
SNAPSHOT_OPTIONS = {
    "snapshot": "backup",
    "snapshot_exclude": "backup_exclude",
    "snapshot_post": "backup_post",
    "snapshot_pre": "backup_pre",
}

# supervisor/docker/utils.py: IMAGE_DOMAIN_REGEX, a registry with an
# optional port.
_DOMAIN_COMPONENT = r"(?:[a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9])"
RE_IMAGE_DOMAIN = re.compile(
    rf"(?:{_DOMAIN_COMPONENT}(?:\.{_DOMAIN_COMPONENT})*|\[(?:[a-fA-F0-9:]+)\])"
    r"(?::[0-9]+)?"
)

# supervisor/validate.py: _RE_IMAGE_PATH_COMPONENT. Placeholders such as
# {arch} count as letters.
_IMAGE_ALPHANUMERIC = r"(?:[a-z0-9]|\{[a-z]+\})+"
RE_IMAGE_PATH_COMPONENT = re.compile(
    rf"^{_IMAGE_ALPHANUMERIC}(?:(?:[._]|__|-+){_IMAGE_ALPHANUMERIC})*$"
)
