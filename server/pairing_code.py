"""Compatibility alias: this module is server.pairing.code."""
import sys
from typing import TYPE_CHECKING

from server.pairing import code as _moved

if TYPE_CHECKING:
    # Type checkers only (never executed): expose the moved module's public
    # names on the old path. At runtime the alias below is the same module.
    from server.pairing.code import *  # noqa: F403

sys.modules[__name__] = _moved
