"""GET /api/export/battery-history: a read-only JSON Lines export of the
`device_health` table, protected by one bearer token.

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
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl

from companion import oidc
from server import history_db

EXPORT_ROUTE = "/api/export/battery-history"
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
_COLUMNS = ("ts", "battery_mv", "fw_version", "boot_reason", "rssi")

_UNAUTHORIZED_BODY = b"Unauthorized\n"
_THROTTLED_BODY = b"Too many failed attempts\n"
_BAD_REQUEST_BODY = (
    b"Use exactly one parameter, since=<UTC time like 2026-10-23T04:25:00Z>, "
    b"within the last 400 days\n")
_TOO_MANY_BODY = b"Too many rows; use a later since\n"
_UNAVAILABLE_BODY = b"History unavailable\n"


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


def _render_lines(rows):
    return "".join(
        json.dumps(dict(zip(_COLUMNS, row))) + "\n" for row in rows
    ).encode("utf-8")


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

    def _handle_export_get(self, query):
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
        return self._serve_export(query)

    def _serve_export(self, query):
        since = parse_since(query, datetime.now(timezone.utc))
        if since is None:
            return self._send_export(400, _PLAIN, _BAD_REQUEST_BODY)
        try:
            rows = history_db.export_device_health(
                self.args.state_dir, since, MAX_ROWS)
        except history_db.TooManyRows:
            return self._send_export(413, _PLAIN, _TOO_MANY_BODY)
        except (sqlite3.Error, OSError):
            return self._send_export(503, _PLAIN, _UNAVAILABLE_BODY)
        return self._send_export(200, _NDJSON, _render_lines(rows))
