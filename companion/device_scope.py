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

from companion import access, prefs
from server import (
    device_config, device_dirs, fleet_db, hardware, history_db)

# Never carries a MAC, token or secret: the type is safe to hand to templates.
Device = collections.namedtuple(
    "Device", "id name hardware_type state_path state_dir is_live owner_user_id",
    defaults=(None,))

LIVE_NAME = "Orly frame"
LIVE_ID = "live"
# Mirrors the byos `--sleep` default: the interval assumed for a device whose
# own wake interval was never set.
DEFAULT_WAKE_INTERVAL_S = 3600

STATUS_NEVER_SEEN = "never_seen"
STATUS_OFFLINE = "offline"
STATUS_ONLINE = "online"

_DEVICE_URL_PREFIX = "/devices/"


def _owner_of(row):
    """The row's owner user id, or None for a row that carries none."""
    try:
        value = row["owner_user_id"]
    except (IndexError, KeyError):
        return None
    return None if value is None else int(value)


def _live_from_row(root, row):
    name = None if row is None else row["name"]
    return Device(
        id=LIVE_ID if row is None else str(row["id"]),
        name=name or LIVE_NAME,
        hardware_type=hardware.LEGACY_KEY if row is None else str(row["hardware_type"]),
        state_path=device_dirs.LIVE_STATE_PATH,
        state_dir=root,
        is_live=True,
        owner_user_id=None if row is None else _owner_of(row))


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
        is_live=False,
        owner_user_id=_owner_of(row))


def load_devices(root):
    """The live frame first, then the others by name then id. Never raises."""
    return _devices_from_rows(root, _fleet_rows(root), True)


def _devices_from_rows(root, rows, with_fallback):
    """Devices for `rows`, live first then by name then id. The synthetic
    live entry (no fleet row) is added only when `with_fallback`."""
    live = None
    others = []
    for row in rows:
        device = _device_from_row(root, row)
        if device is None:
            continue
        if device.is_live:
            live = device
        else:
            others.append(device)
    others.sort(key=lambda d: (d.name, d.id))
    if live is None and with_fallback:
        live = _live_from_row(root, None)
    return ([live] if live is not None else []) + others


def _is_user_view():
    """True when this request's principal is a plain user."""
    principal = prefs.current_principal()
    return principal is not None and principal[1] == access.USER


def _co_managed_ids(root, user_id):
    """Ids of the frames `user_id` co-manages; an empty set on any problem,
    so a database without the table or an unreadable one never hides the
    frames the user owns."""
    if user_id is None:
        return set()
    try:
        conn = fleet_db.connect_readonly(root)
    except (fleet_db.FleetDbError, sqlite3.Error, OSError):
        return set()
    try:
        return fleet_db.co_managed_device_ids(conn, user_id)
    except (fleet_db.FleetDbError, sqlite3.Error, OSError):
        return set()
    finally:
        conn.close()


def load_devices_for(root, principal):
    """The devices `principal` may see: all of them for an admin or when no
    principal is known, and for a user the frames they own or co-manage. A
    user's list never holds the synthetic live fallback, so a user with no
    frame sees none. Never raises."""
    if principal is None or principal.role != access.USER:
        return load_devices(root)
    shared = _co_managed_ids(root, principal.user_id)
    visible = [
        row for row in _fleet_rows(root)
        if principal.user_id is not None and (
            _owner_of(row) == principal.user_id or str(row["id"]) in shared)]
    return _devices_from_rows(root, visible, False)


def personal_frames_for(root, principal):
    """The frames `principal` owns or co-manages (any role), built from fleet
    rows only: no synthetic live fallback, and an administrator's other frames
    are not included. Empty for no principal or one without a user id."""
    if principal is None or principal.user_id is None:
        return []
    shared = _co_managed_ids(root, principal.user_id)
    mine = [
        row for row in _fleet_rows(root)
        if _owner_of(row) == principal.user_id or str(row["id"]) in shared]
    return _devices_from_rows(root, mine, False)


def has_fleet_rows(root):
    """True when a migrated fleet.db holds at least one device row."""
    return bool(_fleet_rows(root))


def default_frame_for(root, principal):
    """The frame a signed-in user or administrator lands on: the first of the
    frames they own or co-manage by name (case-insensitive) then id, or None
    when they have none. Built from fleet data only."""
    frames = personal_frames_for(root, principal)
    if not frames:
        return None
    return min(frames, key=lambda d: (d.name.casefold(), d.id))


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


def last_check_in_ts(state_dir):
    """The raw ISO `ts` of the newest check-in in the history database, or
    None (no database, no reading, or an unreadable one)."""
    if not os.path.exists(history_db.history_db_path(state_dir)):
        return None
    try:
        with history_db.open_db(state_dir) as conn:
            row = history_db.latest_device_health(conn)
    except (sqlite3.Error, OSError):
        return None
    return row["ts"] if row else None


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

_SCOPE_CTX = contextvars.ContextVar("skypane_device_scope", default=(None, (), None, None))


def set_request_scope(device, devices, viewer_id=None, root=None):
    """Store this request's device and device list, plus the signed-in user's
    id and the state root the frame switcher needs to label shared frames.
    The sole mutation path; call it exactly once per request."""
    _SCOPE_CTX.set((device, tuple(devices), viewer_id, root))


def current_device():
    return _SCOPE_CTX.get()[0]


def current_devices():
    return _SCOPE_CTX.get()[1]


# One row of the frame switcher. `co_managed` marks a frame the viewer
# manages but does not own; `owner_email` is set only when the row shows it.
SwitcherEntry = collections.namedtuple("SwitcherEntry", "device co_managed owner_email")


def _owner_emails(root, user_ids):
    """{user id: email} for the ids; empty on any problem."""
    ids = sorted({int(i) for i in user_ids})
    if not ids or root is None:
        return {}
    try:
        conn = fleet_db.connect_readonly(root)
    except (fleet_db.FleetDbError, sqlite3.Error, OSError):
        return {}
    try:
        marks = ",".join("?" for _ in ids)
        rows = conn.execute(
            "SELECT id, email FROM users WHERE id IN (%s)" % marks, ids).fetchall()
        return {int(row["id"]): str(row["email"]) for row in rows}
    except (sqlite3.Error, OSError):
        return {}
    finally:
        conn.close()


def foreign_frame_owner_email():
    """The owner's email when this request's administrator is viewing a frame
    they neither own nor co-manage, else None (a user, a frame of their own, a
    frame with no owner or no scope). Only an administrator ever gets it."""
    device, _devices, viewer_id, root = _SCOPE_CTX.get()
    principal = prefs.current_principal()
    if device is None or viewer_id is None or principal is None \
            or principal[1] != access.ADMIN or root is None:
        return None
    owner = device.owner_user_id
    if owner is None or owner == viewer_id \
            or device.id in _co_managed_ids(root, viewer_id):
        return None
    return _owner_emails(root, [owner]).get(owner)


def viewer_may_rename_current():
    """Whether this request's viewer may rename this request's frame: an
    administrator, or the frame's owner (a co-manager may not)."""
    device, _devices, viewer_id, _root = _SCOPE_CTX.get()
    principal = prefs.current_principal()
    if device is None or principal is None:
        return False
    if principal[1] == access.ADMIN:
        return True
    return viewer_id is not None and device.owner_user_id == viewer_id


def _switcher_devices(device, devices, viewer_id, root):
    """The scope's devices the switcher lists, and the co-managed ids. A user's
    scope is already their own frames. An administrator's scope is every frame,
    so it is cut to the frames they own or co-manage plus the one being viewed."""
    shared = _co_managed_ids(root, viewer_id) if root is not None else set()
    if _is_user_view() or viewer_id is None:
        return list(devices), shared
    kept = [
        d for d in devices
        if d.owner_user_id == viewer_id or d.id in shared or d.id == device.id]
    return kept, shared


def switcher_entries():
    """The frames the frame switcher lists for this request, in scope order;
    empty when no frame is in scope. Owner emails are attached only to frames
    the viewer co-manages or, for an administrator, views without owning."""
    device, devices, viewer_id, root = _SCOPE_CTX.get()
    if device is None:
        return ()
    listed, shared = _switcher_devices(device, devices, viewer_id, root)
    foreign = [
        d for d in listed
        if viewer_id is not None and d.owner_user_id not in (None, viewer_id)]
    emails = _owner_emails(root, [d.owner_user_id for d in foreign])
    return tuple(
        SwitcherEntry(
            d, d.id in shared and d in foreign,
            emails.get(d.owner_user_id) if d in foreign else None)
        for d in listed)


def console_frame_entries():
    """Every frame of the platform with its owner's email, in scope order; the
    list a Console frame page's chip offers. Only an administrator's scope
    holds every frame, so for anyone else this is just their own scope with no
    owner emails: it never widens what a viewer may see. Owner emails come from
    one query."""
    device, devices, _viewer_id, root = _SCOPE_CTX.get()
    if device is None:
        return ()
    principal = prefs.current_principal()
    if principal is None or principal[1] != access.ADMIN:
        return tuple(SwitcherEntry(d, False, None) for d in devices)
    emails = _owner_emails(
        root, [d.owner_user_id for d in devices if d.owner_user_id is not None])
    return tuple(
        SwitcherEntry(d, False, emails.get(d.owner_user_id)) for d in devices)


def _unprefixed(device):
    """True when `device` is addressed without a /devices/<id> prefix: only
    the synthetic live entry that has no fleet row. Every device with a fleet
    row is addressed by its id, for every principal."""
    return device.id == LIVE_ID


def selector_value(device):
    """The selector option value for `device`: the literal "live" for the
    un-prefixed live frame, else the real id."""
    return LIVE_ID if _unprefixed(device) else device.id


def current_prefix():
    """"" for the un-prefixed live frame or no scope, else "/devices/<id>"."""
    device = current_device()
    if device is None or _unprefixed(device):
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
    if _unprefixed(device):
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
    global Update page, plus the Console airline editor)."""
    from companion import ui_base
    return tuple(
        route for route, _label in ui_base.NAV_TABS if route != ui_base.UPDATE_ROUTE
    ) + (ui_base.AIRLINE_EDITOR_ROUTE,)


def _switch_device(value, devices):
    """The Device in `devices` that `value` ("live" or a device id) names."""
    if value == LIVE_ID:
        if _is_user_view():
            return None
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
