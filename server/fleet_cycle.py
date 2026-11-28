# SPDX-License-Identifier: AGPL-3.0-only
"""Compatibility alias: this module is server.polling.fleet_cycle."""
import sys
from typing import TYPE_CHECKING

from server.polling import fleet_cycle as _moved

if TYPE_CHECKING:
    # Type checkers only (never executed): expose the moved module's public
    # names on the old path. At runtime the alias below is the same module.
    from server.polling.fleet_cycle import *  # noqa: F403

sys.modules[__name__] = _moved
