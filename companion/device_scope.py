"""Which device a companion request is for, where its directory is, whether
it can be polled from here, and whether it looks offline.

Leaf module: stdlib plus `server.*` helpers and `companion.routes` (imported
lazily inside `scoped()` to avoid a cycle). No HTTP code.

Security invariant: a URL id is only a lookup key into fleet.db. The device
directory always comes from the stored `state_path`, validated by
`server.device_dirs.resolve_state_dir`; an unknown, malformed or
unresolvable id yields None and never falls back to the live frame.

The per-request scope follows `companion/prefs.py`: one set path
(`set_request_scope`, called once per request by the dispatcher), many read
paths (`current_device`, `current_devices`, `current_prefix`, `scoped`), no
other mutation path and no process-wide "current device".
"""
import collections
import contextvars
import json
import os
import sqlite3
import threading
import time
import urllib.parse

from server import (
    device_config, device_dirs, fleet_db, hardware, history_db)

# Never carries a MAC, token or secret: the type is safe to hand to templates.
Device = collections.namedtuple(
    "Device", "id name hardware_type state_path state_dir is_live")

LIVE_NAME = "Orly frame"
LIVE_ID = "live"
# Mirrors the byos `--sleep` default: the interval assumed for a device whose
# own wake interval was never set.
DEFAULT_WAKE_INTERVAL_S = 3600

STATUS_NEVER_SEEN = "never_seen"
STATUS_OFFLINE = "offline"
STATUS_ONLINE = "online"

_DEVICE_URL_PREFIX = "/devices/"


def _live_from_row(root, row):
    name = None if row is None else row["name"]
    return Device(
        id=LIVE_ID if row is None else str(row["id"]),
        name=name or LIVE_NAME,
        hardware_type=hardware.LEGACY_KEY if row is None else str(row["hardware_type"]),
        state_path=device_dirs.LIVE_STATE_PATH,
        state_dir=root,
        is_live=True)


def live_device(root):
    """The live frame, named from its fleet row when there is one."""
    for row in _fleet_rows(root):
        if row["state_path"] == device_dirs.LIVE_STATE_PATH:
            return _live_from_row(root, row)
    return _live_from_row(root, None)


def _fleet_rows(root):
    """Device rows of a migrated, readable fleet.db; [] on any problem."""
    try:
        conn = fleet_db.connect_readonly(root)
    except (fleet_db.FleetDbError, sqlite3.Error, OSError):
        return []
    try:
        if fleet_db.meta_get(conn, fleet_db.META_MIGRATED) is None:
            return []
        return fleet_db.list_devices(conn)
    except (fleet_db.FleetDbError, sqlite3.Error, OSError):
        return []
    finally:
        conn.close()


def _device_from_row(root, row):
    """A Device for the row, or None when its state_path is unusable."""
    state_path = str(row["state_path"])
    if state_path == device_dirs.LIVE_STATE_PATH:
        return _live_from_row(root, row)
    try:
        state_dir = device_dirs.resolve_state_dir(root, state_path)
    except ValueError:
        return None
    device_id = str(row["id"])
    return Device(
        id=device_id,
        name=row["name"] or device_id,
        hardware_type=str(row["hardware_type"]),
        state_path=state_path,
        state_dir=state_dir,
        is_live=False)


def load_devices(root):
    """The live frame first, then the others by name then id. Never raises."""
    live = None
    others = []
    for row in _fleet_rows(root):
        device = _device_from_row(root, row)
        if device is None:
            continue
        if device.is_live:
            live = device
        else:
            others.append(device)
    others.sort(key=lambda d: (d.name, d.id))
    return [live or _live_from_row(root, None)] + others


def find_device(root, device_id):
    """The Device for `device_id`, or None for an unknown or malformed id or
    a row whose stored state_path fails validation."""
    if not isinstance(device_id, str) or not device_dirs.is_valid_device_id(device_id):
        return None
    for row in _fleet_rows(root):
        if str(row["id"]) == device_id:
            return _device_from_row(root, row)
    return None


# --- per-device poll locks ---------------------------------------------------

_POLL_LOCKS = {}
# Leaf lock: held only to fetch or create a registry entry, never while polling.
_POLL_LOCKS_GUARD = threading.Lock()


def poll_lock_for(state_dir):
    """The one in-process poll lock for this device directory. Callers use
    a non-blocking acquire; holding one device's lock never blocks another's."""
    key = os.path.realpath(state_dir)
    with _POLL_LOCKS_GUARD:
        lock = _POLL_LOCKS.get(key)
        if lock is None:
            lock = _POLL_LOCKS[key] = threading.Lock()
        return lock


# --- capability and status ---------------------------------------------------

def profile_for(device):
    """The hardware profile of `device`. Never raises: an unknown or
    gated-off hardware type, None or a malformed value reads as the
    legacy profile, so a page can always render."""
    try:
        return hardware.get_profile(device.hardware_type, os.environ)
    except Exception:
        return hardware.REGISTRY[hardware.LEGACY_KEY]


def _battery_received_at(state_dir):
    """`received_at` of the device's own battery_state.json, or None."""
    try:
        with open(os.path.join(state_dir, "battery_state.json")) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    received = data.get("received_at") if isinstance(data, dict) else None
    if isinstance(received, bool) or not isinstance(received, (int, float)):
        return None
    return float(received)


def last_check_in_epoch(state_dir):
    """Epoch seconds of the newest check-in recorded for this directory, or None."""
    if os.path.exists(history_db.history_db_path(state_dir)):
        try:
            with history_db.open_db(state_dir) as conn:
                row = history_db.latest_device_health(conn)
        except (sqlite3.Error, OSError):
            row = None
        if row is not None:
            parsed = history_db.instant_or_none(row.get("ts"))
            if parsed is not None:
                return parsed.timestamp()
    return _battery_received_at(state_dir)


def device_status(device, now_epoch):
    """None for the live frame, else "never_seen", "offline" or "online".

    Offline means the last check-in is older than twice the device's own
    wake interval."""
    if device.is_live:
        return None
    last = last_check_in_epoch(device.state_dir)
    if last is None:
        return STATUS_NEVER_SEEN
    interval = device_config.load_device_config(device.state_dir)["wake_interval_s"]
    if interval is None:
        interval = DEFAULT_WAKE_INTERVAL_S
    return STATUS_OFFLINE if now_epoch - last > 2 * interval else STATUS_ONLINE


def now_epoch():
    return time.time()


# --- request scope ---------------------------------------------------------

_SCOPE_CTX = contextvars.ContextVar("skypane_device_scope", default=(None, ()))


def set_request_scope(device, devices):
    """Store this request's device and device list. The sole mutation path;
    call it exactly once per request."""
    _SCOPE_CTX.set((device, tuple(devices)))


def current_device():
    return _SCOPE_CTX.get()[0]


def current_devices():
    return _SCOPE_CTX.get()[1]


def current_prefix():
    """"" for the live frame or no scope, else "/devices/<id>"."""
    device = current_device()
    if device is None or device.is_live:
        return ""
    return _DEVICE_URL_PREFIX + device.id


def strip_prefix(path):
    """`path` without a well-formed /devices/<id> prefix; anything else is
    returned unchanged."""
    from companion import routes
    matched = routes.DEVICE_PREFIX_RE.match(path)
    if matched is None:
        return path
    return matched.group(2) or "/"


def strip_current_prefix(value):
    """`value` without this request's own /devices/<id> prefix. A value under
    any other prefix, or a non-string, is returned unchanged, so it fails every
    exact-membership test against un-prefixed routes."""
    prefix = current_prefix()
    if prefix and isinstance(value, str):
        if value == prefix:
            return "/"
        if value.startswith(prefix + "/"):
            return value[len(prefix):]
    return value


def target_path(path, device):
    """The same page under `device`: un-prefixed for the live frame."""
    base = strip_prefix(path)
    if device.is_live:
        return base
    return _DEVICE_URL_PREFIX + device.id + base


def scoped(path, method="GET"):
    """`path` under the current device's prefix when the matching route is
    device-scoped; global routes, the live frame and no scope leave it as is.
    A query string or fragment is preserved after the path."""
    prefix = current_prefix()
    if not prefix:
        return path
    cut = len(path)
    for mark in ("?", "#"):
        index = path.find(mark)
        if index != -1:
            cut = min(cut, index)
    from companion import routes
    found = routes.match(method, path[:cut], "")
    if found is None or not found[0].device_scoped:
        return path
    return prefix + path


# --- no-script device switch ---------------------------------------------------

# Returned by `switch_target` for a `device` value that names no known device.
SWITCH_UNKNOWN = ""


def page_routes():
    """The un-prefixed paths of the device-scoped pages (every nav tab but the
    global Update page)."""
    from companion import ui_base
    return tuple(
        route for route, _label in ui_base.NAV_TABS if route != ui_base.UPDATE_ROUTE)


def _switch_device(value, devices):
    """The Device in `devices` that `value` ("live" or a device id) names."""
    if value == LIVE_ID:
        return next((d for d in devices if d.is_live), None)
    if not device_dirs.is_valid_device_id(value):
        return None
    return next((d for d in devices if d.id == value), None)


def switch_target(path, query, devices):
    """Where the selector form's no-script submit goes.

    `path` is the matched, un-prefixed route path (never request text) and
    `devices` the fleet's loaded devices. Returns None when the query carries
    no `device` parameter or `path` is not a device-scoped page, SWITCH_UNKNOWN
    when its first value names no device, else the same page under that device
    with the other query parameters kept. The location is built only from the
    fixed page path and a validated device id, so it can never leave the site.
    """
    if path not in page_routes():
        return None
    params = urllib.parse.parse_qsl(query, keep_blank_values=True)
    values = [value for key, value in params if key == "device"]
    if not values:
        return None
    target = _switch_device(values[0], devices)
    if target is None:
        return SWITCH_UNKNOWN
    location = target_path(path, target)
    rest = [(key, value) for key, value in params if key != "device"]
    if rest:
        location += "?" + urllib.parse.urlencode(rest)
    return location
