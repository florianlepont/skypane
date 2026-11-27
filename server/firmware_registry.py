"""Compatibility alias: this module is server.firmware.registry."""
import sys
from typing import TYPE_CHECKING

from server.firmware import registry as _moved

if TYPE_CHECKING:
    # Type checkers only (never executed): expose the moved module's public
    # names on the old path. At runtime the alias below is the same module.
    from server.firmware.registry import *  # noqa: F403

sys.modules[__name__] = _moved
