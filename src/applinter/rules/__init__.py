"""The checks that go beyond what a JSON schema can express.

Every check takes an app and yields findings. Checks run on files that may
have failed the schema, so they never trust a value to have the right type.
Importing a module registers its checks.
"""

from . import build, community, config, translations
from .registry import CHECKS, check

__all__ = ["CHECKS", "build", "check", "community", "config", "translations"]
