# SPDX-License-Identifier: AGPL-3.0-only
"""Compatibility alias: this module is server.pairing.pairings."""
import sys
from typing import TYPE_CHECKING

from server.pairing import pairings as _moved

if TYPE_CHECKING:
    # Type checkers only (never executed): expose the moved module's public
    # names on the old path. At runtime the alias below is the same module.
    from server.pairing.pairings import *  # noqa: F403

sys.modules[__name__] = _moved
