"""Read-only exports under /api/export/, protected by one bearer token:

  battery-history  the `device_health` table, JSON Lines
  flights          the `runway_events` table, JSON Lines
  poll-cycles      the bounded `poll_cycles` trace, JSON Lines
  status           one JSON object: what is on the panel, the queue, the
                   pacing state, the pipeline heartbeat and a few settings

The two JSON Lines routes and battery-history take exactly one `since` parameter; `status`
takes none. None exposes a location, a name, a secret or a path.

Packaged as an `ExportMixin` that `Handler` inherits, like `SignInMixin`.
Never imports `companion.app`. The handler provides `send_html()`,
`_not_found_page()`, `_login_throttle_key()`, `_send_hardening_headers()`
and `args.state_dir`.

Security invariants:
- The feature is off (the route answers like an unknown path) unless
  SKYPANE_EXPORT_TOKEN is set to at least MIN_TOKEN_CHARS characters. The
  variable is read on every request.
- Only the Authorization header authenticates. The Cookie header is never
  read, no cookie is ever set, so a signed-in session grants nothing here.
- The token is compared as bytes with hmac.compare_digest and is never
  written to a log, a response or an exception message.
- Failed attempts count against a per-client throttle that is checked
  before the token is compared, so a blocked client cannot test guesses.
- The data comes from `history_db.export_device_health`, which opens
  history.db read-only.
"""
import hmac
import json
import os
import re
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl

from companion import oidc
from server import check_interval, device_config, history_db, state_store
from server.wake_stats import WAKE_COLUMNS

EXPORT_ROUTE = "/api/export/battery-history"
FLIGHTS_ROUTE = "/api/export/flights"
POLL_CYCLES_ROUTE = "/api/export/poll-cycles"
STATUS_ROUTE = "/api/export/status"
EXPORT_ROUTES = (EXPORT_ROUTE, FLIGHTS_ROUTE, POLL_CYCLES_ROUTE, STATUS_ROUTE)
TOKEN_ENV_VAR = "SKYPANE_EXPORT_TOKEN"
MIN_TOKEN_CHARS = 32

MAX_ROWS = 100000
MAX_AGE = timedelta(days=400)
MAX_FUTURE = timedelta(days=1)

# Failed attempts per client address (the same /64 collapse as sign-in).
FAILURE_LIMIT = 10
FAILURE_WINDOW_S = 60
FAILURE_THROTTLE = oidc.StartThrottle(limit=FAILURE_LIMIT, window=FAILURE_WINDOW_S)

_SINCE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")
_SINCE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
_BEARER_PREFIX = "bearer "
_PLAIN = "text/plain; charset=utf-8"
_NDJSON = "application/x-ndjson; charset=utf-8"
_COLUMNS = ("ts", "battery_mv", "fw_version", "boot_reason", "rssi") + WAKE_COLUMNS

_UNAUTHORIZED_BODY = b"Unauthorized\n"
_THROTTLED_BODY = b"Too many failed attempts\n"
_BAD_REQUEST_BODY = (
    b"Use exactly one parameter, since=<UTC time like 2026-10-23T04:25:00Z>, "
    b"within the last 400 days\n")
_TOO_MANY_BODY = b"Too many rows; use a later since\n"
_UNAVAILABLE_BODY = b"History unavailable\n"
_STATUS_BAD_REQUEST_BODY = b"This route takes no parameter\n"
_JSON = "application/json; charset=utf-8"

# JSON Lines routes: the columns each line carries and the reader that
# yields them. A reader takes (state_dir, since, max_rows).
def _table_reader(table):
    return lambda state_dir, since, max_rows: history_db.export_table_rows(
        state_dir, table, since, max_rows)


_LINE_EXPORTS = {
    EXPORT_ROUTE: (_COLUMNS, history_db.export_device_health),
    FLIGHTS_ROUTE: (history_db.EXPORT_TABLES["runway_events"], _table_reader("runway_events")),
    POLL_CYCLES_ROUTE: (history_db.EXPORT_TABLES["poll_cycles"], _table_reader("poll_cycles")),
}

_FLIGHT_VIEW_KEYS = (
    "hex", "callsign", "aircraft_type", "altitude_ft", "altitude_ref_ft",
    "vertical_rate_fpm", "on_ground",
)
_DEVICE_VIEW_KEYS = (
    "wake_interval_s", "tracked_runway", "display_enabled", "quiet_hours_enabled",
    "quiet_hours_start", "quiet_hours_end", "timezone",
)


def configured_token():
    """The export token as bytes, or None when the feature is off."""
    value = os.environ.get(TOKEN_ENV_VAR, "")
    if len(value) < MIN_TOKEN_CHARS:
        return None
    return value.encode("utf-8")


def _presented_token(authorization):
    """The bytes after `Bearer `, or None for any other header shape."""
    if authorization is None or len(authorization) <= len(_BEARER_PREFIX):
        return None
    if authorization[:len(_BEARER_PREFIX)].lower() != _BEARER_PREFIX:
        return None
    # http.server decodes header bytes as latin-1, so this round-trips.
    return authorization[len(_BEARER_PREFIX):].encode("latin-1")


def parse_since(query, now):
    """The validated `since` text for a raw query string, or None.

    Exactly one parameter, named `since`, in the strict UTC form, no older
    than MAX_AGE and no further ahead than MAX_FUTURE.
    """
    try:
        pairs = parse_qsl(query, keep_blank_values=True, max_num_fields=4)
    except ValueError:
        return None
    if len(pairs) != 1 or pairs[0][0] != "since":
        return None
    since = pairs[0][1]
    if _SINCE_RE.fullmatch(since) is None:
        return None
    try:
        moment = datetime.strptime(since, _SINCE_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    if moment < now - MAX_AGE or moment > now + MAX_FUTURE:
        return None
    return since


def _render_lines(rows, columns=_COLUMNS):
    return "".join(
        json.dumps(dict(zip(columns, row))) + "\n" for row in rows
    ).encode("utf-8")


def _flight_view(flight):
    """The few fields of a stored flight worth showing, or None."""
    if not isinstance(flight, dict):
        return None
    return {key: flight.get(key) for key in _FLIGHT_VIEW_KEYS}


def status_snapshot(state_dir, now):
    """What the frame is doing right now, from files and tables opened
    read-only: the flight on the panel, the display queue, the redraw
    pacing, the pipeline heartbeat and the handful of settings that decide
    them. No location, no name and no secret is included.
    """
    poll_state = state_store.load_poll_state(state_dir)
    config = device_config.load_device_config(state_dir)
    experiment = check_interval.read_experiment(state_dir, now)
    last_redraw = poll_state.get(check_interval.LAST_FLIGHT_REDRAW_KEY)
    pending = []
    for entry in _pending_entries(poll_state):
        first_seen = entry["first_seen"]
        view = _flight_view(entry["flight"])
        view["first_seen"] = first_seen
        view["age_s"] = round(now - first_seen, 1)
        pending.append(view)
    return {
        "now": datetime.fromtimestamp(now, timezone.utc).isoformat(timespec="seconds"),
        "shown": _flight_view(poll_state.get("last_flight")),
        "shown_state": poll_state.get("last_confirmed_state"),
        "previous": _flight_view(poll_state.get("previous_flight")),
        "pending": pending,
        "hold_state": poll_state.get("hold_state"),
        "last_advance_at": poll_state.get("last_advance_at"),
        "last_flight_redraw_at": last_redraw,
        "device": {key: config.get(key) for key in _DEVICE_VIEW_KEYS},
        "check_interval_experiment": (
            None if experiment is None
            else {"check_interval_s": experiment[0], "expires_at": experiment[1]}),
        "meta": history_db.export_status_meta(state_dir),
    }


def _pending_entries(poll_state):
    """`poll_state["pending_flights"]` as validated `{"flight", "first_seen"}`
    entries, the way the poll cycle reads it, without importing it."""
    entries = []
    value = poll_state.get("pending_flights")
    if not isinstance(value, list):
        return entries
    for entry in value:
        if not isinstance(entry, dict) or not isinstance(entry.get("flight"), dict):
            continue
        first_seen = entry.get("first_seen")
        if isinstance(first_seen, bool) or not isinstance(first_seen, (int, float)):
            continue
        entries.append({"flight": entry["flight"], "first_seen": float(first_seen)})
    return entries


class ExportMixin:
    def _send_export(self, code, content_type, body, extra_headers=()):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for name, value in extra_headers:
            self.send_header(name, value)
        self._send_hardening_headers()
        self.end_headers()
        self.wfile.write(body)

    def _handle_export_get(self, query, route=EXPORT_ROUTE):
        expected = configured_token()
        if expected is None:
            return self.send_html(404, self._not_found_page())
        key = self._login_throttle_key()
        if FAILURE_THROTTLE.is_blocked(key):
            return self._send_export(
                429, _PLAIN, _THROTTLED_BODY,
                (("Retry-After", str(FAILURE_WINDOW_S)),))
        presented = _presented_token(self.headers.get("Authorization"))
        if presented is None or not hmac.compare_digest(presented, expected):
            FAILURE_THROTTLE.allow(key)
            return self._send_export(
                401, _PLAIN, _UNAUTHORIZED_BODY,
                (("WWW-Authenticate", "Bearer"),))
        if route == STATUS_ROUTE:
            return self._serve_status(query)
        return self._serve_export(query, route)

    def _serve_status(self, query):
        if query:
            return self._send_export(400, _PLAIN, _STATUS_BAD_REQUEST_BODY)
        try:
            snapshot = status_snapshot(self.args.state_dir, time.time())
        except (sqlite3.Error, OSError):
            return self._send_export(503, _PLAIN, _UNAVAILABLE_BODY)
        return self._send_export(200, _JSON, (json.dumps(snapshot) + "\n").encode("utf-8"))

    def _serve_export(self, query, route=EXPORT_ROUTE):
        columns, reader = _LINE_EXPORTS[route]
        since = parse_since(query, datetime.now(timezone.utc))
        if since is None:
            return self._send_export(400, _PLAIN, _BAD_REQUEST_BODY)
        try:
            rows = reader(self.args.state_dir, since, MAX_ROWS)
        except history_db.TooManyRows:
            return self._send_export(413, _PLAIN, _TOO_MANY_BODY)
        except (sqlite3.Error, OSError):
            return self._send_export(503, _PLAIN, _UNAVAILABLE_BODY)
        return self._send_export(200, _NDJSON, _render_lines(rows, columns))
