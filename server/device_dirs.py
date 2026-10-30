"""Maps a fleet.db `state_path` to a directory under the state root.

Leaf module: stdlib plus `server.atomic_io` and `server.panel_format`.
It is the only code that decides which directory a device may use.

Security invariant: a device directory comes from a validated `state_path`
(either "." for the live frame or "devices/<id>") and never from request
text. The shape check runs first and no string that failed it is ever
joined onto a path; the resolved directory must additionally stay inside
`<root>/devices` once symlinks are followed, and a symlinked device
directory is refused outright (the backup refuses symlinks too, so one is
never legitimate).
"""
from __future__ import annotations

import os
import re
import sys

# Same repo-root sys.path bootstrap as server/fleet_db.py.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from server import atomic_io, panel_format  # noqa: E402

LIVE_STATE_PATH = "."
DEVICES_DIRNAME = "devices"
PANEL_FILENAME = "panel.bin"
CONFIG_FILENAME = "device_config.json"
# `\Z` (not `$`) so a trailing newline cannot slip through.
DEVICE_ID_RE = re.compile(r"\Ad_[0-9a-f]{8}\Z")

_DEVICE_PATH_PREFIX = DEVICES_DIRNAME + "/"


def is_valid_device_id(value: str) -> bool:
    return DEVICE_ID_RE.match(value) is not None


def state_path_for(device_id: str) -> str:
    """The state_path a device with this id stores in fleet.db."""
    if not is_valid_device_id(device_id):
        raise ValueError(f"invalid device id: {device_id!r}")
    return _DEVICE_PATH_PREFIX + device_id


def valid_state_path(state_path: str) -> bool:
    """Pure shape check: "." or "devices/<id>". Touches no filesystem."""
    if state_path == LIVE_STATE_PATH:
        return True
    if not state_path.startswith(_DEVICE_PATH_PREFIX):
        return False
    return is_valid_device_id(state_path[len(_DEVICE_PATH_PREFIX):])


def resolve_state_dir(root: str, state_path: str) -> str:
    """Return the directory for `state_path` under `root`.

    Raises ValueError for a bad shape, a symlinked device directory, or a
    directory that would resolve outside `<root>/devices`.
    """
    if not valid_state_path(state_path):
        raise ValueError(f"invalid state_path: {state_path!r}")
    if state_path == LIVE_STATE_PATH:
        return root
    device_id = state_path[len(_DEVICE_PATH_PREFIX):]
    candidate = os.path.join(root, DEVICES_DIRNAME, device_id)
    real_devices = os.path.realpath(os.path.join(root, DEVICES_DIRNAME))
    real_candidate = os.path.realpath(candidate)
    if real_candidate != os.path.join(real_devices, device_id):
        raise ValueError(f"state_path escapes the devices directory: {state_path!r}")
    if os.path.commonpath([real_devices, real_candidate]) != real_devices:
        raise ValueError(f"state_path escapes the devices directory: {state_path!r}")
    return candidate


def _seed_if_absent(path: str, data: bytes) -> None:
    if not os.path.exists(path):
        atomic_io.atomic_write(path, data)


def provision_device_dir(
    root: str,
    device_id: str,
    width: int,
    height: int,
    fill: int | None = None,
) -> str:
    """Create `<root>/devices/<id>/` with a seeded config and panel.

    The panel is two pixels per byte, `(width // 2) * height` bytes, each
    byte `fill` (default: the white nibble in both halves). Existing files
    are never overwritten and nothing else is created. Returns the
    directory.
    """
    directory = os.path.join(root, DEVICES_DIRNAME, device_id)
    state_path_for(device_id)  # validates the id before any filesystem write
    os.makedirs(directory, exist_ok=True)
    if fill is None:
        fill = (panel_format.WHITE << 4) | panel_format.WHITE
    _seed_if_absent(os.path.join(directory, CONFIG_FILENAME), b"{}\n")
    _seed_if_absent(
        os.path.join(directory, PANEL_FILENAME),
        bytes([fill]) * ((width // 2) * height),
    )
    return directory
