#!/usr/bin/env python3
"""The owner's default aircraft type per airline: `{airline illustration key:
type code}`, stored in `{fleet root}/airline_default_types.json`, one file
for every frame.

The companion's airline editor writes it (a star on one type row) and reads
it back to mark that row. The live frame's picture choice reads it too
(`illustrations.select_illustration`): an airline with no picture of its own
shows the picture of its default type. Same file
contract as the other owner registries: a never-raising load that rebuilds
every entry from scratch, validate-before-write, an atomic write, a hard cap
and one process-wide lock around the load-modify-write cycle.
"""
import json
import os
import re
import threading

from server import atomic_io, device_dirs
from server.plane import illustrations

DEFAULT_TYPES_FILENAME = "airline_default_types.json"
MAX_ENTRIES = 300

# A key is an illustration key (lowercase alphanumerics and hyphens); a type
# code is an upper-case designator such as A320 or A350-1000.
_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,99}$")
_CODE_RE = re.compile(r"^[A-Z0-9][A-Z0-9-]{1,11}$")

SET_OK = "ok"
SET_REJECTED = "rejected"
SET_FULL = "full"
SET_FAILED = "failed"

_WRITE_LOCK = threading.Lock()


def default_types_path(state_dir):
    return os.path.join(device_dirs.fleet_root_for(state_dir), DEFAULT_TYPES_FILENAME)


def normalise_code(raw):
    """The upper-cased type code, or `None` for anything that is not one."""
    if not isinstance(raw, str):
        return None
    code = raw.strip().upper()
    return code if _CODE_RE.match(code) else None


def load_default_types(state_dir):
    """`{airline key: type code}`; `{}` for a missing or invalid file.
    Never raises."""
    if not state_dir:
        return {}
    return load_default_types_file(default_types_path(state_dir))


def load_default_types_file(path):
    """`{airline key: type code}` read from exactly the file at `path`, with
    the same validation and cap as `load_default_types`; `{}` for a missing
    or invalid file. Never raises."""
    try:
        with open(path) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    registry = {}
    for key in sorted(k for k in data if isinstance(k, str)):
        if len(registry) >= MAX_ENTRIES:
            break
        code = normalise_code(data[key])
        if _KEY_RE.match(key) and code:
            registry[key] = code
    return registry


def set_default_type(state_dir, key, code, livery_key=None):
    """Make `code` the default type of the airline `key`, or clear the entry
    when `code` is empty. Returns a `SET_*` value; never raises.

    A type is refused (`SET_REJECTED`, nothing written) unless the airline has
    a picture for it: its type artwork, built in or uploaded, or the artwork
    `livery_key` that was just stored as this type's picture. Clearing is
    always allowed."""
    if not isinstance(key, str) or not _KEY_RE.match(key):
        return SET_REJECTED
    clear = not (isinstance(code, str) and code.strip())
    normalised = None if clear else normalise_code(code)
    if not clear and normalised is None:
        return SET_REJECTED
    if not clear and not (
            illustrations.has_type_livery(key, normalised, state_dir)
            or (livery_key and illustrations.resolved_illustration_path(livery_key, state_dir))):
        return SET_REJECTED
    with _WRITE_LOCK:
        registry = load_default_types(state_dir)
        if clear:
            registry.pop(key, None)
        elif key not in registry and len(registry) >= MAX_ENTRIES:
            return SET_FULL
        else:
            registry[key] = normalised
        try:
            path = default_types_path(state_dir)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            atomic_io.atomic_write(path, json.dumps(registry, indent=1))
        except Exception:
            return SET_FAILED
    return SET_OK
