"""Compatibility alias: this module is server.firmware.cli. Run as
`python3 -m server.firmware_cli` it executes that module's main()."""
import sys
from typing import TYPE_CHECKING

from server.firmware import cli as _moved

if TYPE_CHECKING:
    # Type checkers only (never executed): expose the moved module's public
    # names on the old path. At runtime the alias below is the same module.
    from server.firmware.cli import *  # noqa: F403

if __name__ == "__main__":
    sys.exit(_moved.main())

sys.modules[__name__] = _moved
