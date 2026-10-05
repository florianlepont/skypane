#!/usr/bin/env python3
"""SkyPane companion service: a stdlib `ThreadingHTTPServer` with a
hand-rolled route table, run as its own systemd unit, separate from the
vendored device-protocol server in `stub-server/`.

Every route except the login routes and the stylesheet requires a
session (`Handler.require_session()`), enforced in this one file. Binds
`--bind 0.0.0.0` by default; production passes `--bind 127.0.0.1`
because Caddy is the only intended client.

Never writes the poll pipeline's own persisted flight-state file —
`server.poll_cycle.run_once()` is that file's one legitimate writer.

`main()` fails closed on a missing password rather than starting with
auth silently disabled.
"""
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlsplit

# Same repo-root sys.path bootstrap as server/poll_loop.py, so
# server.* resolves whether this file runs as a package or standalone.
_HERE = os.path.dirname(os.path.abspath(__file__))  # companion/
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from companion import (  # noqa: E402
    auth, flash, freshness, i18n, illustration_normalize, layout, login_page, page_context,
    post_actions, prefs, request_body, routes, static_files, theme_preview)
from companion.pages import (  # noqa: E402
    # airlines_page is unused by this module's own code; kept so
    # companion/test_post_origin.py's app.airlines_page.* route reads
    # keep resolving.
    airlines_page,  # noqa: F401
    config_page,
    health_page,
    update_page,
)
from server import device_config, firmware_registry, history_db  # noqa: E402
from server.plane import calendar_rules, illustrations, name_overrides  # noqa: E402
import server.poll_cycle as poll_cycle  # noqa: E402
import server.state_store as state_store  # noqa: E402

DEFAULT_PORT = 8643
# The gallery-directory-name convention lives in companion/page_context.py
# (build_page_context()'s "gallery_entries" loader owns it); rebound here
# under its historical name since companion/test_freshness_token.py reads
# app.GALLERY_DIRNAME directly and gallery_bytes() below still uses it.
GALLERY_DIRNAME = page_context.GALLERY_DIRNAME
THEME_COOKIE_MAX_AGE_S = 365 * 24 * 3600
# Reuses THEME_COOKIE_MAX_AGE_S's own value and reasoning: a per-browser
# preference the site should remember indefinitely.
LANG_COOKIE_MAX_AGE_S = THEME_COOKIE_MAX_AGE_S
MAX_FORM_BYTES = 8192  # far more than any form on this site needs.
# Bounds peak memory per upload to a few MB. Enforced by the caller
# (Handler._read_upload_body()), not by parse_single_uploaded_file().
# Single definition site is companion/post_actions.py (the illustration-
# replace handler's own module) — rebound here rather than retyped;
# companion/pages/airlines_page.py imports it from this module lazily.
MAX_ILLUSTRATION_UPLOAD_BYTES = post_actions.MAX_ILLUSTRATION_UPLOAD_BYTES
# Bounds a stalled/slow-drip client's socket reads (including the
# unauthenticated POST /login body) so it cannot tie up a worker thread
# indefinitely — a slowloris-shaped DoS reachable before any credential
# check.
REQUEST_SOCKET_TIMEOUT_S = 30

# The Content-Security-Policy sent on every response. No 'unsafe-inline'
# on script-src (no inline <script> anywhere); style-src allows
# 'unsafe-inline' solely for theme-swatch `style="background:..."`
# attributes sourced from the fixed THEMES registry, never user input.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; img-src 'self' data:; "
    "style-src 'self' 'unsafe-inline'; script-src 'self'; "
    "form-action 'self'; frame-ancestors 'none'"
)
# The same environment variable deploy/skypane-byos.service passes to
# byos_server.py as --sleep, via the identical EnvironmentFile=. Not
# imported from companion/auth.py: unrelated lifecycles.
SLEEP_ENV_VAR = "SKYPANE_SLEEP_S"

LOGIN_ROUTE = "/login"
# Moved to companion/static_files.py (the static allowlist module);
# rebound here under their historical names so every existing call site
# and test assertion in this file keeps resolving.
STYLE_ROUTE = static_files.STYLE_ROUTE
SCRIPT_ROUTE = static_files.SCRIPT_ROUTE
NAV_SCRIPT_ROUTE = static_files.NAV_SCRIPT_ROUTE
DIRTY_STATE_SCRIPT_ROUTE = static_files.DIRTY_STATE_SCRIPT_ROUTE
LIST_FILTER_SCRIPT_ROUTE = static_files.LIST_FILTER_SCRIPT_ROUTE
COPY_BUTTON_SCRIPT_ROUTE = static_files.COPY_BUTTON_SCRIPT_ROUTE
FRESHNESS_SCRIPT_ROUTE = static_files.FRESHNESS_SCRIPT_ROUTE
PANEL_LOOKUP_SCRIPT_ROUTE = static_files.PANEL_LOOKUP_SCRIPT_ROUTE
FLASH_CLEANUP_SCRIPT_ROUTE = static_files.FLASH_CLEANUP_SCRIPT_ROUTE
TOAST_SCRIPT_ROUTE = static_files.TOAST_SCRIPT_ROUTE
POLL_COOLDOWN_SCRIPT_ROUTE = static_files.POLL_COOLDOWN_SCRIPT_ROUTE
CONFIRM_SUBMIT_SCRIPT_ROUTE = static_files.CONFIRM_SUBMIT_SCRIPT_ROUTE
THEME_PREVIEW_SCRIPT_ROUTE = static_files.THEME_PREVIEW_SCRIPT_ROUTE
AIRLINE_TYPES_SCRIPT_ROUTE = static_files.AIRLINE_TYPES_SCRIPT_ROUTE
LOGIN_CARD_SCRIPT_ROUTE = static_files.LOGIN_CARD_SCRIPT_ROUTE
SUBMIT_GUARD_SCRIPT_ROUTE = static_files.SUBMIT_GUARD_SCRIPT_ROUTE
RELATIVE_TIME_SCRIPT_ROUTE = static_files.RELATIVE_TIME_SCRIPT_ROUTE
QUICK_SWITCH_SCRIPT_ROUTE = static_files.QUICK_SWITCH_SCRIPT_ROUTE
VALUE_CONTROLS_SCRIPT_ROUTE = static_files.VALUE_CONTROLS_SCRIPT_ROUTE
CALENDAR_SHEET_SCRIPT_ROUTE = static_files.CALENDAR_SHEET_SCRIPT_ROUTE
# Single definition site is companion/pages/config_page.py (app.py imports
# that module, so the reverse import would be a cycle) — rebound here
# rather than re-typed, exactly like RUNWAY_IMAGE_ROUTE_PREFIX and the
# FLASH_KEY_* constants below.
SETTINGS_ROUTE = config_page.SETTINGS_ROUTE
POLL_ROUTE = "/poll-now"

# The page routes. All six live tabs are declared once, in
# companion/layout.py's NAV_GROUPS; these aliases exist so this module's
# dispatch reads by name.
HOME_ROUTE = layout.HOME_ROUTE
DISPLAY_ROUTE = layout.DISPLAY_ROUTE
FLIGHTS_ROUTE = layout.FLIGHTS_ROUTE
AIRLINES_ROUTE = layout.AIRLINES_ROUTE
HEALTH_ROUTE = layout.HEALTH_ROUTE
DEVICE_ROUTE = layout.DEVICE_ROUTE
UPDATE_ROUTE = layout.UPDATE_ROUTE
# The pre-refactor History route, kept as a fixed 303 to FLIGHTS_ROUTE
# for stale bookmarks — the same treatment PREVIEW_PAGE_ROUTE gets.
HISTORY_LEGACY_ROUTE = "/history"
# Quick-action routes the Screen on/off and Quiet-hours instant switches
# post to. Literal here, byte-identical to the values home_page.py used
# to define, since this module can never import a page module either.
QUICK_DISPLAY_ROUTE = "/quick/display"
QUICK_QUIET_HOURS_ROUTE = "/quick/quiet-hours"
# The Diagnostic LED switch sends a PARTIAL payload rather than a
# checkbox inside the merged settings form, because a partial
# POST /settings is exactly the shape that silently switches off
# whatever it omits. One explicit `led_enabled` keyword straight to
# device_config.save_device_config(), never a partial settings save.
QUICK_LED_ROUTE = "/quick/led"
# Content negotiation, not a second route shape: a form post gets a 303
# with a flash, a fetch (identified by this header) gets a 204. Only
# the value is a constant; the header name has no module-level constant.
QUICK_FETCH_HEADER_VALUE = "quick-switch"
# companion/static/freshness.js's own X-Requested-With value: it marks a
# conditional freshness tick (see _render_tab()'s 304 branch) so that an
# ordinary browser navigation with a stale cached If-None-Match can never
# be answered 304 by accident - only a tick that identifies itself this
# way is ever eligible for one.
FRESHNESS_FETCH_HEADER_VALUE = "freshness"
THEME_ROUTE = "/ui-theme"
LANG_ROUTE = "/ui-lang"
LOGOUT_ROUTE = "/logout"
# The Preview page is retired into History; kept as a fixed-redirect
# source only.
PREVIEW_PAGE_ROUTE = "/preview"
GALLERY_ROUTE_PREFIX = "/gallery/"
# Rebound from config_page.py (the single definition site) rather than
# retyped, to avoid a reverse-import cycle. Same for RULES_*/CALENDAR_*
# and the FLASH_KEY_* constants below.
RUNWAY_IMAGE_ROUTE_PREFIX = config_page.RUNWAY_IMAGE_ROUTE_PREFIX
ILLUSTRATION_IMAGE_ROUTE_PREFIX = "/illustration/"
# Rebound from companion/theme_preview.py — the render/cache mechanism,
# not a page module, owns this prefix since it is also used from
# config_page.py's own theme-picker markup.
THEME_PREVIEW_ROUTE_PREFIX = theme_preview.THEME_PREVIEW_ROUTE_PREFIX
FRAME_PREVIEW_ROUTE_PREFIX = theme_preview.FRAME_PREVIEW_ROUTE_PREFIX
RULES_ADD_ROUTE = config_page.RULES_ADD_ROUTE
RULES_DELETE_ROUTE_PREFIX = config_page.RULES_DELETE_ROUTE_PREFIX
RULES_DELETE_ROUTE_SUFFIX = config_page.RULES_DELETE_ROUTE_SUFFIX
CALENDAR_DISCONNECT_ROUTE = config_page.CALENDAR_DISCONNECT_ROUTE
CALENDAR_CONNECT_ROUTE = config_page.CALENDAR_CONNECT_ROUTE
UPDATE_INSTALL_ROUTE = update_page.INSTALL_ROUTE
UPDATE_CANCEL_ROUTE = update_page.CANCEL_ROUTE

# The flash vocabulary (FLASH_MESSAGES/FLASH_ROLES/every FLASH_KEY_*)
# and its text resolution now live in companion/flash.py — rebound here
# under their historical names so every existing call site in this file,
# and every test assertion against the literal query-string values,
# stays unchanged.
FLASH_KEY_SAVED = flash.FLASH_KEY_SAVED
FLASH_KEY_SAVE_FAILED = flash.FLASH_KEY_SAVE_FAILED
FLASH_KEY_POLL_TRIGGERED = flash.FLASH_KEY_POLL_TRIGGERED
FLASH_KEY_POLL_COOLDOWN = flash.FLASH_KEY_POLL_COOLDOWN
FLASH_KEY_POLL_FAILED = flash.FLASH_KEY_POLL_FAILED
FLASH_KEY_POLL_ALREADY_RUNNING = flash.FLASH_KEY_POLL_ALREADY_RUNNING
FLASH_KEY_ILLUSTRATION_REPLACED = flash.FLASH_KEY_ILLUSTRATION_REPLACED
FLASH_KEY_ILLUSTRATION_REJECTED = flash.FLASH_KEY_ILLUSTRATION_REJECTED
FLASH_KEY_ILLUSTRATION_REPLACE_FAILED = flash.FLASH_KEY_ILLUSTRATION_REPLACE_FAILED
FLASH_KEY_MANUAL_RESOLVED = flash.FLASH_KEY_MANUAL_RESOLVED
FLASH_KEY_MANUAL_NAME_EMPTY = flash.FLASH_KEY_MANUAL_NAME_EMPTY
FLASH_KEY_MANUAL_NAME_TOO_LONG = flash.FLASH_KEY_MANUAL_NAME_TOO_LONG
FLASH_KEY_MANUAL_NAME_RESERVED = flash.FLASH_KEY_MANUAL_NAME_RESERVED
FLASH_KEY_MANUAL_PREFIX_STALE = flash.FLASH_KEY_MANUAL_PREFIX_STALE
FLASH_KEY_MANUAL_REGISTRY_FULL = flash.FLASH_KEY_MANUAL_REGISTRY_FULL
FLASH_KEY_MANUAL_SAVE_FAILED = flash.FLASH_KEY_MANUAL_SAVE_FAILED
FLASH_KEY_MANUAL_DELETE_FAILED = flash.FLASH_KEY_MANUAL_DELETE_FAILED
FLASH_KEY_MANUAL_NAME_UNUSABLE = flash.FLASH_KEY_MANUAL_NAME_UNUSABLE
FLASH_KEY_RULE_ADDED = flash.FLASH_KEY_RULE_ADDED
FLASH_KEY_RULE_REPLACED = flash.FLASH_KEY_RULE_REPLACED
FLASH_KEY_RULE_KEY_INVALID = flash.FLASH_KEY_RULE_KEY_INVALID
FLASH_KEY_RULE_REGISTRY_FULL = flash.FLASH_KEY_RULE_REGISTRY_FULL
FLASH_KEY_RULE_SAVE_FAILED = flash.FLASH_KEY_RULE_SAVE_FAILED
FLASH_KEY_RULE_DELETED = flash.FLASH_KEY_RULE_DELETED
FLASH_KEY_RULE_DELETE_FAILED = flash.FLASH_KEY_RULE_DELETE_FAILED
FLASH_KEY_CALENDAR_CONNECTED = flash.FLASH_KEY_CALENDAR_CONNECTED
FLASH_KEY_CALENDAR_SYNC_FAILED = flash.FLASH_KEY_CALENDAR_SYNC_FAILED
FLASH_KEY_CALENDAR_DISCONNECTED = flash.FLASH_KEY_CALENDAR_DISCONNECTED
FLASH_KEY_CALENDAR_SYNC_DEFERRED = flash.FLASH_KEY_CALENDAR_SYNC_DEFERRED
FLASH_KEY_CALENDAR_CONNECT_OK = flash.FLASH_KEY_CALENDAR_CONNECT_OK
FLASH_KEY_CALENDAR_CONNECT_INVALID = flash.FLASH_KEY_CALENDAR_CONNECT_INVALID
FLASH_KEY_CALENDAR_CONNECT_FAILED = flash.FLASH_KEY_CALENDAR_CONNECT_FAILED
FLASH_KEY_UPDATE_SCHEDULE_FAILED = flash.FLASH_KEY_UPDATE_SCHEDULE_FAILED
FLASH_KEY_UPDATE_CANCEL_FAILED = flash.FLASH_KEY_UPDATE_CANCEL_FAILED
FLASH_KEY_UPDATE_BUSY = flash.FLASH_KEY_UPDATE_BUSY
FLASH_KEY_DISPLAY_ON = flash.FLASH_KEY_DISPLAY_ON
FLASH_KEY_DISPLAY_OFF = flash.FLASH_KEY_DISPLAY_OFF
FLASH_KEY_QUIET_ON = flash.FLASH_KEY_QUIET_ON
FLASH_KEY_QUIET_OFF = flash.FLASH_KEY_QUIET_OFF
FLASH_KEY_QUICK_FAILED = flash.FLASH_KEY_QUICK_FAILED
FLASH_KEY_LED_ON = flash.FLASH_KEY_LED_ON
FLASH_KEY_LED_OFF = flash.FLASH_KEY_LED_OFF
FLASH_MESSAGES = flash.FLASH_MESSAGES
FLASH_ROLES = flash.FLASH_ROLES
FLASH_TONES = flash.FLASH_TONES

# Moved to companion/static_files.py; rebound under their historical
# names so every existing call site, and every existing test monkeypatch
# target that reaches the real caller, keeps resolving. `_serve_static()`
# below is the caller of `_static_entry()`/`_not_modified()`, so a test
# that wants to change what it sees monkeypatches `static_files.*`
# directly (a monkeypatch of these aliases would never be seen by the
# functions that actually run) - see companion/test_static_cache.py.
_STATIC_CACHE = static_files._STATIC_CACHE
_read_static_bytes = static_files.read_static_bytes
_static_entry = static_files.static_entry
_if_none_match_matches = static_files.if_none_match_matches
_not_modified = static_files.not_modified


# Process-global, not per-session: keyed per client IP and bounded, so
# failed logins from one address never lock another.
LOGIN_THROTTLE = auth.LoginThrottle()

# Guards the check-cooldown -> run_once() -> mark-triggered sequence in
# _handle_poll_now(), so two concurrent POST /poll-now requests can
# never both call poll_cycle.run_once(). Process-local only: correct
# because main() runs exactly one ThreadingHTTPServer in one OS process -
# the in-process fast path. Cross-process exclusion (the systemd oneshot
# racing this same handler) is poll_cycle.poll_cycle_lock()'s poll.lock,
# taken inside run_once() itself with lock_timeout_s=0 below, so a busy
# lock never blocks this request thread. Single definition site is
# companion/post_actions.py (whose own calendar-connect route also
# guards under it) — rebound here, never a second, independent Lock().
_POLL_LOCK = post_actions._POLL_LOCK

# The same six (route, label) pairs layout.NAV_TABS already carries as
# Messages — reused rather than re-declared, so this dict's labels never
# drift from the nav's own and this module never registers a second
# Message for the same id.
_PAGE_TITLES = dict(layout.NAV_TABS)

# The literal call-site translation _handle_login_post() below needs —
# see that method's own comment for why it cannot go through a
# constant `login_page` would otherwise own.
_INCORRECT_PASSWORD_TEXT = i18n.msg(
    "common.incorrect_password_try_again", "Incorrect password. Try again.")

# Each tab's own extra scripts, on top of layout.GLOBAL_PAGE_SCRIPTS
# (present on every authenticated page regardless). One tuple per
# layout.NAV_TABS route - companion/test_page_scripts.py's hook-coverage
# test fails, naming the route, if a tab is ever added here without one.
# Each tuple is the SUPERSET over every state the page can be in,
# including a region freshness.js may swap in later with no fresh page
# load of its own (for example Flights' rows, or Display's calendar-
# disconnect confirm dialog once the calendar is connected) - never only
# what a freshly-seeded, empty state happens to render.
_PAGE_SCRIPTS = {
    layout.HOME_ROUTE: (
        layout.FRESHNESS_SCRIPT_SRC,
        layout.QUICK_SWITCH_SCRIPT_SRC,
    ),
    layout.DISPLAY_ROUTE: (
        layout.CALENDAR_SHEET_SCRIPT_SRC,
        layout.CONFIRM_SUBMIT_SCRIPT_SRC,
        layout.DIRTY_STATE_SCRIPT_SRC,
        layout.FRESHNESS_SCRIPT_SRC,
        layout.QUICK_SWITCH_SCRIPT_SRC,
        layout.THEME_PREVIEW_SCRIPT_SRC,
        layout.VALUE_CONTROLS_SCRIPT_SRC,
    ),
    layout.DEVICE_ROUTE: (
        layout.DIRTY_STATE_SCRIPT_SRC,
        layout.POLL_COOLDOWN_SCRIPT_SRC,
        layout.QUICK_SWITCH_SCRIPT_SRC,
        layout.VALUE_CONTROLS_SCRIPT_SRC,
    ),
    layout.FLIGHTS_ROUTE: (
        layout.FRESHNESS_SCRIPT_SRC,
        layout.LIST_FILTER_SCRIPT_SRC,
        layout.PANEL_LOOKUP_SCRIPT_SRC,
    ),
    layout.HEALTH_ROUTE: (
        layout.COPY_BUTTON_SCRIPT_SRC,
        layout.FRESHNESS_SCRIPT_SRC,
        layout.LIST_FILTER_SCRIPT_SRC,
        layout.PANEL_LOOKUP_SCRIPT_SRC,
    ),
    layout.AIRLINES_ROUTE: (
        layout.AIRLINE_TYPES_SCRIPT_SRC,
        layout.LIST_FILTER_SCRIPT_SRC,
        layout.PANEL_LOOKUP_SCRIPT_SRC,
    ),
    # CONFIRM_SUBMIT_SCRIPT_SRC gates the per-release Install form's
    # data-confirm misclick guard: the script never sets a "confirm"
    # field of its own, so accepting the native confirm() dialog still
    # lands on _handle_update_install_post()'s server-side confirm page,
    # never schedules directly.
    layout.UPDATE_ROUTE: (
        layout.CONFIRM_SUBMIT_SCRIPT_SRC,
    ),
}

# The freshness-token machinery (the four refresh-page slugs, every
# _freshness_*() stamp/signal helper, and _page_freshness_token() itself)
# now lives in companion/freshness.py. Only these two names are rebound
# here: every other freshness helper is purely internal to that module's
# own token computation, with no other call site in this file.
_FRESHNESS_PAGE_SLUGS = freshness._FRESHNESS_PAGE_SLUGS
# Called through this module global (not a direct freshness.* call) so
# test_freshness_token.py's `monkeypatch.setattr(app, "_page_freshness_token",
# ...)` still reaches every call site below.
_page_freshness_token = freshness._page_freshness_token


# The login card's markup and its own text constants, and the shared
# 404/403 error-page bodies, now live in companion/login_page.py.


def _validated_next_route(candidate):
    """Validate a caller-supplied `next` redirect target against
    `layout.NAV_TABS`'s known routes. Open-redirect mitigation: an exact
    membership test, never `startswith`/URL-parsed/regex-matched.
    Anything not byte-identical to a real route is discarded (`None`).
    """
    allowed = {route for route, _ in layout.NAV_TABS}
    return candidate if candidate in allowed else None


# The flash-text resolution (_resolve_flash_text()) and the poll-trigger
# cooldown read (poll_cooldown_remaining()) now live in companion/flash.py
# — rebound here under their historical names.
_resolve_flash_text = flash.resolve_flash_text
poll_cooldown_remaining = flash.poll_cooldown_remaining

# page_context()'s own lazy loaders (_safe_poll_cooldown_remaining(),
# _lazy_health_state(), _lazy_health_severity()), the Settings form's
# SKYPANE_SLEEP_S pre-fill (env_wake_interval_default()), and the last-
# check-in reader page_context() shares with resolve_flash_text()
# (_safe_last_checkin_ts()) all now live in companion/page_context.py —
# rebound here under their historical names for the tests that still read
# them off this module.
_safe_poll_cooldown_remaining = page_context._safe_poll_cooldown_remaining
_lazy_health_state = page_context._lazy_health_state
_lazy_health_severity = page_context._lazy_health_severity
env_wake_interval_default = page_context.env_wake_interval_default
_safe_last_checkin_ts = page_context._safe_last_checkin_ts


def _safe_latest_runway_event(state_dir):
    """The single most recent `runway_events` row (the `?live=1` render
    source), or `None` on any failure — a missing/locked/unreadable
    database, a malformed row, or simply no event recorded yet.
    Deliberately a broad `except Exception` (not the narrower
    `(sqlite3.Error, OSError)` `_safe_last_checkin_ts()` above uses): any
    exception reading the event must degrade to `live_event=None` (the
    fixed fictional scene), never a 500 — this route's one query is not
    allowed to be the reason a preview image fails to render.
    """
    try:
        with history_db.open_db(state_dir) as conn:
            rows = history_db.recent_runway_events(
                conn, limit=1,
                airline_names=name_overrides.names_by_prefix(
                    name_overrides.load_name_overrides(state_dir)))
    except Exception:
        return None
    return rows[0] if rows else None


def mark_poll_triggered(state_dir):
    with history_db.open_db(state_dir) as conn:
        history_db.set_meta(
            conn, history_db.META_LAST_POLL_TRIGGER, str(int(time.time())))


# gallery_entries() (page_context()'s own lazy loader) and
# runway_images_available()/_runway_image_path()/_runway_image_filename()
# (the runway-diagram-presence check page_context() also computes eagerly,
# plus _serve_runway_image()'s own path builder below) now live in
# companion/page_context.py — rebound here under their historical names.
gallery_entries = page_context.gallery_entries
runway_images_available = page_context.runway_images_available
_runway_image_path = page_context._runway_image_path


def gallery_bytes(state_dir, requested):
    """Return the named gallery file's bytes only when `requested` is an
    exact match against a real `os.scandir()` listing of the gallery
    directory — the requested name is never joined onto a filesystem
    path; an unmatched, traversal-shaped, or otherwise unknown name
    returns None.
    """
    gallery_dir = os.path.join(state_dir, GALLERY_DIRNAME)
    try:
        for entry in os.scandir(gallery_dir):
            if entry.is_file() and entry.name == requested:
                with open(entry.path, "rb") as fh:
                    return fh.read()
    except OSError:
        return None
    return None


# _illustration_filenames()/parse_single_uploaded_file() now live in
# companion/post_actions.py (the illustration-replace handler's own
# module, and _serve_illustration_image()'s below) — rebound here under
# their historical names; companion/pages/airlines_page.py imports
# MAX_ILLUSTRATION_UPLOAD_BYTES from this module lazily.
_illustration_filenames = post_actions._illustration_filenames
parse_single_uploaded_file = post_actions.parse_single_uploaded_file


# The typed PageContext every page module's render()/handle_post()
# receives (replacing the _LazyContext dict subclass that used to live
# here) now lives in companion/page_context.py — see that module's own
# docstring. Handler.page_context() below is a one-line delegation to
# page_context.build_page_context().


class Handler(post_actions.SettingsActionsMixin, BaseHTTPRequestHandler):
    server_version = "skypane-companion"
    args = None
    # socketserver.StreamRequestHandler honours this attribute, so a
    # stalled read (e.g. the unauthenticated POST /login body) raises
    # socket.timeout instead of blocking the worker thread forever.
    timeout = REQUEST_SOCKET_TIMEOUT_S

    # --- response helpers -------------------------------------------

    def _send_hardening_headers(self):
        """Baseline hardening headers for every response: this is an
        authenticated admin panel on the public internet, so a missing
        X-Frame-Options/CSP enables clickjacking and a missing
        X-Content-Type-Options enables MIME-sniffing XSS.
        """
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Content-Security-Policy", CONTENT_SECURITY_POLICY)

    def send_html(self, code, html_str, etag=None):
        """`etag` (default `None`) is a change TOKEN, never a cache
        freshness signal - it rides alongside `Cache-Control: no-store`
        below, always, so it can only ever be used for the freshness
        tick's own conditional GET (`_render_tab()`), never to let a
        shared cache or the back button replay a stale page.
        """
        body = html_str.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        # Every HTML page is either session-gated or a login form — never
        # something a shared cache or the back button should replay
        # after sign-out.
        self.send_header("Cache-Control", "no-store")
        if etag is not None:
            self.send_header("ETag", etag)
        self._send_hardening_headers()
        self.end_headers()
        self.wfile.write(body)

    def send_not_modified(self, etag):
        """304 for a freshness tick whose token still matches
        `_render_tab()`'s freshly-computed one: no body, the same quoted
        ETag the client's own If-None-Match already named, and
        `Cache-Control: no-store` still - the ETag here is only ever a
        change token, never a signal that a shared cache or the back
        button may replay this page.
        """
        self.send_response(304)
        self.send_header("ETag", etag)
        self.send_header("Cache-Control", "no-store")
        self._send_hardening_headers()
        self.end_headers()

    def send_bytes(self, code, content_type, payload, cache_seconds=0, public=False):
        """`public` (default False, fail-closed): a shared cache has no
        knowledge of the session cookie, so `public=True` must be an
        explicit opt-in, never the default, or a shared cache could
        replay a session-gated response to a different client.
        """
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        if cache_seconds > 0:
            scope = "public" if public else "private"
            self.send_header(
                "Cache-Control", "%s, max-age=%d" % (scope, cache_seconds))
        else:
            self.send_header("Cache-Control", "no-store")
        self._send_hardening_headers()
        self.end_headers()
        self.wfile.write(payload)

    def send_no_content(self):
        """204 with no body and no Location — the fetch half of a
        /quick/* route's content negotiation. No Location, deliberately:
        `fetch()` follows a same-origin redirect silently by default, so
        a 303 would read as success to a client whose session just
        expired. companion/static/freshness.js sets `redirect: "manual"`
        to match.
        """
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.send_header("Cache-Control", "no-store")
        self._send_hardening_headers()
        self.end_headers()

    def _wants_no_content(self):
        """Whether this request identified itself as a fetch rather than
        a browser form submission. An exact value test: a browser form
        post sends no `X-Requested-With` at all.
        """
        return self.headers.get("X-Requested-With") == QUICK_FETCH_HEADER_VALUE

    def redirect(self, location, set_cookie=None):
        # Cache-Control: no-store matters here because a 303 can carry a
        # Set-Cookie.
        self.send_response(303)
        self.send_header("Location", location)
        if set_cookie:
            self.send_header("Set-Cookie", set_cookie)
        self.send_header("Content-Length", "0")
        self.send_header("Cache-Control", "no-store")
        self._send_hardening_headers()
        self.end_headers()

    # --- auth ----------------------------------------------------------

    def _is_authenticated(self):
        # This is the only place the revocation check runs — every
        # require_session() call site below goes through this single
        # predicate, never duplicated per route.
        cookies = auth.parse_cookies(self.headers.get("Cookie"))
        token = cookies.get(auth.SESSION_COOKIE_NAME)
        return bool(token) and auth.verify_session_token(token) and not auth.is_revoked(token)

    def require_session(self):
        if self._is_authenticated():
            return True
        # Carries the requested route through login via an allowlisted
        # `next` param, validated by _validated_next_route(); unrecognised
        # values discard silently to the bare LOGIN_ROUTE.
        requested_path = urlsplit(self.path).path
        next_route = _validated_next_route(requested_path)
        if next_route:
            # safe="" so the value is unambiguously one query token
            # ("/login?next=%2Fhealth", not "/login?next=/health").
            self.redirect(
                "%s?next=%s" % (LOGIN_ROUTE, quote(next_route, safe="")))
        else:
            self.redirect(LOGIN_ROUTE)
        return False

    def _resolved_ui_theme(self):
        cookies = auth.parse_cookies(self.headers.get("Cookie"))
        return layout.ui_theme_from_cookie(cookies)

    def _lang_from_request(self):
        """The cookie set by POST /ui-lang wins when present and valid;
        otherwise the first supported entry in Accept-Language decides
        ("fr*" -> French, anything else -> English). Never interpolates
        a header byte into the page — the return value is always a
        member of prefs.LANG_CHOICES.
        """
        cookies = auth.parse_cookies(self.headers.get("Cookie"))
        cookie_value = cookies.get(auth.UI_LANG_COOKIE_NAME)
        if cookie_value in prefs.LANG_CHOICES:
            return cookie_value
        header = self.headers.get("Accept-Language", "")
        for entry in header.split(","):
            tag = entry.split(";", 1)[0].strip().lower()
            if not tag:
                continue
            return "fr" if tag.startswith("fr") else "en"
        return prefs.DEFAULT_LANG

    # --- form / query parsing -------------------------------------------

    def read_form(self):
        """Read the request body as `application/x-www-form-urlencoded`,
        capped at MAX_FORM_BYTES. An oversized/undecodable/stalled
        (`socket.timeout`, bounded by `Handler.timeout`) body degrades
        to an empty form rather than raising; an oversized body's
        remainder is still drained (via `request_body.drain_capped_body()`)
        so the connection isn't left corrupt. Reachable pre-auth from
        `POST /login`.
        """
        length = request_body.parse_content_length(self.headers)
        if length <= 0:
            return {}
        raw, _over_cap = request_body.drain_capped_body(self.rfile, length, MAX_FORM_BYTES)
        if raw is None:
            return {}
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            return {}
        parsed = parse_qs(text, keep_blank_values=True)
        return {key: values[0] for key, values in parsed.items() if values}

    def _read_upload_body(self):
        """Read the POST body for an illustration-replace request,
        bounded by `MAX_ILLUSTRATION_UPLOAD_BYTES`. Returns `None` for
        an absent/unparseable/non-positive/over-cap length or a
        `socket.timeout`; an over-cap body's remainder is still drained
        first (via `request_body.drain_capped_body()`) so the connection
        isn't left mid-body.
        """
        length = request_body.parse_content_length(self.headers)
        if length <= 0:
            return None
        raw, _over_cap = request_body.drain_capped_body(
            self.rfile, length, MAX_ILLUSTRATION_UPLOAD_BYTES)
        return raw

    def page_context(self):
        """Build the `PageContext` every page module's render()/
        handle_post() receives — documented in full in
        companion/pages/__init__.py and companion/page_context.py.
        """
        return page_context.build_page_context(self)

    # --- shared page fragments -------------------------------------------

    def _not_found_page(self):
        """The shared 404 body, reached pre-auth from static-asset
        delegates too. `health_alert` is computed only on
        `self._is_authenticated()` (a pure bool check) so Health's
        warn/error state never leaks to an unauthenticated caller — and
        even then, from `safe_health_signals()` alone: the nav dot's
        severity, never the markup `health_state_from_signals()` would
        build for an error page that never renders it.
        `self.page_context()` is deliberately not called: too many
        reads for an error path. The markup itself is
        `companion/login_page.py`'s `not_found_page()`.
        """
        # Pre-session: resolved from the cookie or Accept-Language.
        prefs.set_request_prefs(lang=self._lang_from_request())
        health_alert = None
        if self._is_authenticated():
            signals = health_page.safe_health_signals(
                self.args.state_dir, history_db.utc_now_iso())
            health_alert = signals["severity"] if signals else "ok"
        return login_page.not_found_page(self._resolved_ui_theme(), health_alert)

    def _forbidden_page(self):
        """The shared 403 body for do_POST()'s Origin/Sec-Fetch-Site gate.
        Byte-for-byte the same shape as `_not_found_page()` above. The
        markup itself is `companion/login_page.py`'s `forbidden_page()`.
        """
        prefs.set_request_prefs(lang=self._lang_from_request())
        health_alert = None
        if self._is_authenticated():
            signals = health_page.safe_health_signals(
                self.args.state_dir, history_db.utc_now_iso())
            health_alert = signals["severity"] if signals else "ok"
        return login_page.forbidden_page(self._resolved_ui_theme(), health_alert)

    def _render_login_page(self, error=None, lockout_seconds=None, next_route=None):
        # Pre-session, like _not_found_page() above. The markup itself is
        # companion/login_page.py's render_login_page()/login_body().
        prefs.set_request_prefs(lang=self._lang_from_request())
        return login_page.render_login_page(
            self._resolved_ui_theme(), error=error, lockout_seconds=lockout_seconds,
            next_route=next_route)

    def _serve_static(self, abs_path, content_type, cache_control):
        """Shared body behind `_serve_static_route()` and
        `_serve_runway_image()`: an in-memory, read-once-per-process
        cache (`_static_entry()`), RFC 9110 conditional evaluation
        (`_not_modified()`), and a bodiless 304 on a match. `cache_control`
        is sent verbatim on both a 200 and a 304, so a caller's own policy
        (shared pre-auth vs. private) never depends on which status this
        particular request happens to get.
        """
        try:
            entry = _static_entry(abs_path)
        except OSError:
            return self.send_html(404, self._not_found_page())
        if _not_modified(self.headers, entry.etag, entry.mtime_s):
            self.send_response(304)
            self.send_header("ETag", entry.etag)
            self.send_header("Last-Modified", entry.last_modified)
            self.send_header("Cache-Control", cache_control)
            self._send_hardening_headers()
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(entry.payload)))
        self.send_header("ETag", entry.etag)
        self.send_header("Last-Modified", entry.last_modified)
        self.send_header("Cache-Control", cache_control)
        self._send_hardening_headers()
        self.end_headers()
        self.wfile.write(entry.payload)

    def _serve_static_route(self, route):
        """Look up `route` in the static allowlist (companion/static_files.py's
        STATIC_ROUTES) and serve it through `_serve_static()` above.
        `route` is always a value already matched by an exact dict-key
        lookup (companion/routes.py's ROUTES table), never a
        client-supplied path segment, so this has no path-traversal
        surface. No catch-all /static/ handler: a new script needs its
        own STATIC_ROUTES entry and route-table row.
        """
        asset = static_files.STATIC_ROUTES[route]
        return self._serve_static(asset.path, asset.content_type, asset.cache_control)

    def _serve_gallery_image(self, requested):
        payload = gallery_bytes(self.args.state_dir, requested)
        if payload is None:
            return self.send_html(404, self._not_found_page())
        # This route sits behind do_GET()'s require_session() gate, so it
        # deliberately relies on send_bytes()'s non-shared (private)
        # default rather than opting into shared cacheability.
        return self.send_bytes(200, "image/png", payload, cache_seconds=3600)

    def _serve_runway_image(self, runway_id):
        # Membership test first (validate-then-join): an unknown id and
        # an unreadable file return the same 404, leaking nothing about
        # the filesystem.
        if runway_id not in device_config.RUNWAY_IDS:
            return self.send_html(404, self._not_found_page())
        path = _runway_image_path(runway_id)
        # Policy unchanged (private, max-age=300; this route sits behind
        # do_GET()'s require_session() gate, so the conditional path
        # below is only ever reached post-auth) — it now also gains an
        # ETag/Last-Modified and in-memory bytes via _serve_static().
        return self._serve_static(path, "image/png", "private, max-age=300")

    def _serve_illustration_image(self, key):
        # Membership test first (validate-then-join, same shape as
        # _serve_runway_image()). The set is a per-request union of
        # vendored and server-persisted manual keys, computed fresh.
        filename = key + ".png"
        if filename not in _illustration_filenames(self.args.state_dir):
            return self.send_html(404, self._not_found_page())
        # An overridden key's bytes may have originated as a user
        # upload, but this route only ever decodes bytes this server's
        # own Pillow re-encoded in _handle_illustration_replace() —
        # never a client's raw upload.
        path = illustrations.resolved_illustration_path(key, self.args.state_dir)
        if path is None:
            return self.send_html(404, self._not_found_page())
        # lru_cache'd per path+mtime, so a replaced asset is picked up
        # on the very next request, not left stale.
        try:
            payload = illustration_normalize.cached_normalized_png_bytes(path)
        except Exception:
            # Any decode failure degrades to the same 404, never a 500.
            return self.send_html(404, self._not_found_page())
        return self.send_bytes(200, "image/png", payload, cache_seconds=300)

    def _serve_theme_preview_image(self, theme_id):
        # Membership test first, same shape as _serve_runway_image().
        if theme_id not in device_config.THEMES:
            return self.send_html(404, self._not_found_page())
        # The non-live variant is always the fixed fictional scene. A
        # `?live=1` request reads the operator's own most recent
        # runway_events row and renders it into a raster (never markup);
        # any read/coercion failure degrades to the fixed scene.
        parsed = urlsplit(self.path)
        live_flag = parse_qs(parsed.query).get("live", [None])[0]
        live_event = None
        if live_flag == "1":
            live_event = _safe_latest_runway_event(self.args.state_dir)
        try:
            payload = theme_preview.cached_preview_bytes(
                self.args.state_dir, theme_id, live_event=live_event)
        except OSError:
            return self.send_html(404, self._not_found_page())
        except Exception:
            return self.send_html(404, self._not_found_page())
        if payload is None:
            return self.send_html(404, self._not_found_page())
        return self.send_bytes(200, "image/png", payload, cache_seconds=300)

    def _serve_frame_preview_image(self, theme_id):
        # Every part is an allow-list member before it reaches the cache
        # path: the theme id from the registry, state and size from
        # theme_preview's own tuples. A missing parameter takes the
        # default; an unknown one is a 404, never a guess.
        if theme_id not in device_config.THEMES:
            return self.send_html(404, self._not_found_page())
        query = parse_qs(urlsplit(self.path).query)
        state = query.get("state", [theme_preview.FRAME_PREVIEW_STATE_DEPARTING])[0]
        size = query.get("size", [theme_preview.FRAME_PREVIEW_SIZE_LARGE])[0]
        if (state not in theme_preview.FRAME_PREVIEW_STATES
                or size not in theme_preview.FRAME_PREVIEW_SIZES):
            return self.send_html(404, self._not_found_page())
        try:
            payload = theme_preview.cached_frame_preview_bytes(
                self.args.state_dir, theme_id, state, size)
        except Exception:
            return self.send_html(404, self._not_found_page())
        if payload is None:
            return self.send_html(404, self._not_found_page())
        return self.send_bytes(200, "image/png", payload, cache_seconds=300)

    # _handle_illustration_replace(), _handle_manual_resolve_post(),
    # _handle_manual_resolution_delete(), _handle_rule_add_post(),
    # _handle_rule_delete(), _handle_calendar_disconnect_post(),
    # and _handle_calendar_connect_post() now live on companion/post_actions.py's SettingsActionsMixin, which
    # this class inherits — method names unchanged, so
    # companion/routes.py's ROUTES table keeps resolving them.

    def _referring_tab(self):
        referer = self.headers.get("Referer", "")
        try:
            path = urlsplit(referer).path
        except ValueError:
            path = ""
        allowed = {route for route, _ in layout.NAV_TABS}
        return path if path in allowed else HOME_ROUTE

    def _page_shell_for(self, route, body, ctx, refresh_token=None):
        """The `layout.page_shell()` assembly both `_render_tab()`
        (every GET) and `_handle_settings_post()`'s rejected-save branch
        (a POST that already has its own rendered `body`) need, so
        there is one `page_shell()` call site for both. `refresh_token`
        (default `None`, matching the rejected-save branch, which never
        carries one) forwards straight to `layout.page_shell()`, which
        renders it onto `<body>` only when given.
        """
        flash_html = flash.flash_toast_html(ctx.flash_key, ctx.flash, self.path)
        return layout.page_shell(
            title=i18n.t(_PAGE_TITLES[route]), active=layout.nav_slug(route),
            body=body,
            ui_theme=ctx.ui_theme, flash=flash_html,
            health_alert=ctx.health_severity, device_config=ctx.device_config,
            scripts=_PAGE_SCRIPTS[route], refresh_token=refresh_token)

    def _render_tab(self, route, render):
        """Render one authenticated tab: `render(ctx) -> body markup`
        (a page module's render(), or a lambda binding a scope onto
        config_page.render()) wrapped in layout.page_shell(), so the six
        live routes share one body instead of six copies of it.

        On one of the four refresh pages, computes
        `_page_freshness_token()` right after `page_context()` but
        BEFORE `render()` runs at all: a freshness tick
        (`X-Requested-With: freshness`) whose own `If-None-Match`
        already matches gets a bodiless 304 through
        `send_not_modified()` here, with `render()` never called for
        it. A normal navigation (no `X-Requested-With: freshness`) is
        never answered 304, even carrying a stale matching
        If-None-Match from an earlier tick. `/device` and `/airlines`
        are not refresh pages, so they skip this whole branch and
        carry neither an ETag nor a `data-refresh-token` attribute.
        """
        ctx = self.page_context()
        if layout.nav_slug(route) in _FRESHNESS_PAGE_SLUGS:
            query = urlsplit(self.path).query
            token = _page_freshness_token(route, ctx, query)
            quoted_etag = '"%s"' % token
            is_freshness_tick = (
                self.headers.get("X-Requested-With") == FRESHNESS_FETCH_HEADER_VALUE)
            if is_freshness_tick and _if_none_match_matches(self.headers, quoted_etag):
                return self.send_not_modified(quoted_etag)
            body = render(ctx)
            return self.send_html(
                200, self._page_shell_for(route, body, ctx, refresh_token=token),
                etag=quoted_etag)
        body = render(ctx)
        return self.send_html(200, self._page_shell_for(route, body, ctx))

    # --- routing -----------------------------------------------------------

    def _handle_login_get(self):
        """GET LOGIN_ROUTE: already authenticated redirects home;
        otherwise renders the login form with a validated `?next=`
        destination carried through, so an unrecognised value never even
        renders a hidden field for the user to resubmit.
        """
        if self._is_authenticated():
            return self.redirect(HOME_ROUTE)
        next_route = _validated_next_route(
            parse_qs(urlsplit(self.path).query).get("next", [None])[0])
        return self.send_html(200, self._render_login_page(next_route=next_route))

    def _handle_logout_post(self):
        """POST LOGOUT_ROUTE: revokes the session token server-side
        before clearing the cookie, so replaying the old cookie value
        stops verifying. Session gating happens in routes.ROUTES before
        this runs.
        """
        token = auth.parse_cookies(self.headers.get("Cookie")).get(auth.SESSION_COOKIE_NAME)
        if token:
            auth.revoke(token)
        return self.redirect(LOGIN_ROUTE, set_cookie=auth.logout_set_cookie_header())

    def _handle_rule_delete_post(self, middle):
        """POST RULES_DELETE_ROUTE_PREFIX/{kind}/{value}/RULES_DELETE_ROUTE_SUFFIX:
        split the captured middle on '/' once to recover kind and value.
        A middle that does not split into exactly two non-empty segments
        is a 404. Session gating happens in routes.ROUTES before this
        runs.
        """
        segments = middle.split("/", 1)
        if len(segments) != 2 or not segments[0] or not segments[1]:
            return self.send_html(404, self._not_found_page())
        return self._handle_rule_delete(segments[0], segments[1])

    def do_GET(self):
        """One `history_db.connection_scope()` for the whole request:
        every `history_db.open_db()` call `_dispatch()` makes on this
        thread (however many route handlers read the database) shares one
        connection, opened lazily on the first database read - a static
        asset or an unauthenticated/pre-login route that reads no
        database table never opens one at all.
        """
        with history_db.connection_scope(self.args.state_dir):
            return self._dispatch("GET")

    # Runs as the first statement for a POST, before urlsplit()/routing, so
    # it covers every route uniformly including ones added later. Defence
    # in depth on top of SameSite=Strict (see auth.post_origin_ok()'s
    # docstring).
    def _dispatch(self, method):
        """The one dispatch every do_GET()/do_POST() call goes through:
        `routes.match()` looks the request up in routes.ROUTES, the one
        table that makes every route's gating a field of the route
        itself rather than a hand-repeated `require_session()` call, and
        this method is the ONLY place that gate now runs.
        """
        if method == "POST" and not auth.post_origin_ok(self.headers):
            return self.send_html(403, self._forbidden_page())
        parsed = urlsplit(self.path)
        result = routes.match(method, parsed.path, parsed.query)
        if result is None:
            return self.send_html(404, self._not_found_page())
        route, route_match = result
        if route.auth_required and not self.require_session():
            return None
        return route.handler(self, route_match)

    def _login_throttle_key(self):
        """The one place this handler derives a LoginThrottle bucket key,
        so every LOGIN_THROTTLE call site below uses the identical
        derivation (`auth.login_throttle_key()`, trusting
        X-Forwarded-For only from a loopback peer — Caddy in
        production).
        """
        return auth.login_throttle_key(
            self.client_address[0], self.headers.get("X-Forwarded-For"))

    def _handle_login_post(self):
        # Read and validate `next` before the lockout/password checks so
        # it survives every branch below (lockout, incorrect password,
        # and success) — a failed attempt must not lose the
        # originally-requested destination.
        form = self.read_form()
        next_route = _validated_next_route(form.get("next"))
        throttle_key = self._login_throttle_key()
        if LOGIN_THROTTLE.locked_out(throttle_key):
            remaining = LOGIN_THROTTLE.seconds_remaining(throttle_key)
            return self.send_html(429, self._render_login_page(
                lockout_seconds=remaining, next_route=next_route))
        submitted = form.get("password", "")
        if auth.password_ok(submitted):
            LOGIN_THROTTLE.record_success(throttle_key)
            token = auth.issue_session_token()
            return self.redirect(
                next_route or HOME_ROUTE,
                set_cookie=auth.session_set_cookie_header(token))
        LOGIN_THROTTLE.record_failure(throttle_key)
        return self.send_html(401, self._render_login_page(
            # Translated here, at the call site — see login_page.py's
            # own login_body() docstring for why (`error` is an opaque
            # parameter by the time it reaches that function).
            error=i18n.t(_INCORRECT_PASSWORD_TEXT), next_route=next_route))

    def _handle_settings_post(self):
        """POST /settings. Re-renders the scoped page at 200 with field
        errors attached, never redirects, when validation rejects the
        submission. On a calendar-URL save, syncs under `_POLL_LOCK`,
        which is process-local only — cross-process safety is the
        `fcntl.flock()` lock inside `calendar_rules` itself. No caught
        error's text is ever read: it can contain the calendar URL.
        """
        state_dir = self.args.state_dir
        form = self.read_form()
        ctx = self.page_context()
        errors = {}
        flash_key = config_page.handle_post(form, ctx, errors=errors)
        back = config_page.submitted_return_route(form)
        if errors:
            scope = config_page.submitted_scope(form)
            body = config_page.render(ctx, scope=scope, errors=errors, submitted=form)
            return self.send_html(200, self._page_shell_for(back, body, ctx))
        if flash_key != FLASH_KEY_SAVED:
            return self.redirect("%s?flash=%s" % (back, quote(flash_key)))

        calendar_signal = config_page.submitted_calendar_signal(form)
        if calendar_signal == config_page.CALENDAR_URL_SIGNAL_CLEAR:
            return self._settings_saved_redirect(back, FLASH_KEY_CALENDAR_DISCONNECTED)
        if calendar_signal != config_page.CALENDAR_URL_SIGNAL_SET:
            return self._settings_saved_redirect(back, FLASH_KEY_SAVED)

        if not _POLL_LOCK.acquire(blocking=False):
            return self._settings_saved_redirect(back, FLASH_KEY_CALENDAR_SYNC_DEFERRED)
        try:
            result_code, _registry = calendar_rules.refresh_calendar_registry(
                state_dir, poll_cycle.now_s(), min_interval_s=0)
        finally:
            _POLL_LOCK.release()

        if result_code == calendar_rules.FETCH_OK:
            return self._settings_saved_redirect(back, FLASH_KEY_CALENDAR_CONNECTED)
        return self._settings_saved_redirect(back, FLASH_KEY_CALENDAR_SYNC_FAILED)

    def _settings_saved_redirect(self, back, flash_key):
        """The success-branch response for POST /settings. Reached only
        after the write already landed; `flash_key` names the
        calendar-sync outcome only, never whether the save succeeded.
        """
        return self.redirect("%s?flash=%s" % (back, quote(flash_key)))

    def _handle_poll_now(self):
        # The trigger lives on Home (Refresh now) and on Device (Poll);
        # redirect back to whichever page posted it.
        back = self._referring_tab()
        # Non-blocking acquire, never a timeout.
        if not _POLL_LOCK.acquire(blocking=False):
            # The loser gets an honest "already running" redirect rather
            # than racing into a second poll cycle.
            return self.redirect(
                "%s?flash=%s" % (back, quote(FLASH_KEY_POLL_ALREADY_RUNNING)))
        try:
            state_dir = self.args.state_dir
            remaining = poll_cooldown_remaining(state_dir)
            if remaining > 0:
                flash = FLASH_KEY_POLL_COOLDOWN
            else:
                try:
                    # The exact production code path the systemd timer
                    # already runs, in-process — never a second process
                    # and never a re-parsed subprocess result.
                    # lock_timeout_s=0: never block this request thread on
                    # poll.lock — a lock held by another process (the
                    # oneshot, or an overlapping trigger) must answer at
                    # once, exactly like the in-process _POLL_LOCK above.
                    poll_cycle.run_once(
                        state_dir=state_dir, geofence=self.args.geofence,
                        lock_timeout_s=0)
                except poll_cycle.PollBusy:
                    flash = FLASH_KEY_POLL_ALREADY_RUNNING
                except Exception:
                    flash = FLASH_KEY_POLL_FAILED
                else:
                    mark_poll_triggered(state_dir)
                    flash = FLASH_KEY_POLL_TRIGGERED
        finally:
            # A failed poll still releases the guard: never a wedged trigger.
            _POLL_LOCK.release()
        # Written only after release, so an immediate double-tap sees
        # the lock already free rather than a stale "already running".
        return self.redirect("%s?flash=%s" % (back, quote(flash)))

    def _handle_quick_toggle(self, field, allowed_return_to=None, fallback_return_to=None):
        """The Home page's one-tap switches. `state` ("on"/"off") is the
        only field read; every other device-config value is carried
        forward untouched. `return_to` is membership-tested against
        `allowed_return_to`, never string-prefix-matched or URL-parsed,
        so it cannot become an open redirect. `allowed_return_to`/
        `fallback_return_to` are per-caller, not one shared whitelist,
        since each switch lives on a different subset of pages.
        """
        if allowed_return_to is None:
            allowed_return_to = (layout.HOME_ROUTE, layout.DISPLAY_ROUTE)
        if fallback_return_to is None:
            fallback_return_to = layout.DISPLAY_ROUTE
        form = self.read_form()
        return_to = form.get("return_to")
        if return_to not in allowed_return_to:
            return_to = fallback_return_to
        state = form.get(layout.QUICK_STATE_FIELD)
        if state not in (layout.QUICK_STATE_ON, layout.QUICK_STATE_OFF):
            # NOT a 204, even for a fetch: the client reads 204 as
            # confirmation and would leave its optimistic flip standing,
            # showing a state the frame is not in. A rejected submission
            # must reach the client as a failure in BOTH shapes.
            return self.redirect(
                "%s?flash=%s" % (return_to, quote(FLASH_KEY_QUICK_FAILED)))
        enabled = state == layout.QUICK_STATE_ON
        if field == "display_enabled":
            kwargs = {"display_enabled": enabled}
            flash_key = FLASH_KEY_DISPLAY_ON if enabled else FLASH_KEY_DISPLAY_OFF
        elif field == "led_enabled":
            # One explicit keyword, the same shape the two branches
            # beside it use. This is the whole reason the LED needed a
            # route of its own rather than a fetch at POST /settings — a
            # partial settings body silently resolves every field it omits.
            kwargs = {"led_enabled": enabled}
            flash_key = FLASH_KEY_LED_ON if enabled else FLASH_KEY_LED_OFF
        else:
            kwargs = {"quiet_hours_enabled": enabled}
            flash_key = FLASH_KEY_QUIET_ON if enabled else FLASH_KEY_QUIET_OFF
        try:
            device_config.save_device_config(self.args.state_dir, **kwargs)
        except (ValueError, OSError):
            flash_key = FLASH_KEY_QUICK_FAILED
        # The write happens identically in both shapes; only the
        # response differs. A failed save still redirects even for a
        # fetch, so the client sees a non-OK status and rolls its
        # optimistic flip back rather than reading an empty 204 as a
        # confirmation.
        if flash_key != FLASH_KEY_QUICK_FAILED and self._wants_no_content():
            return self.send_no_content()
        return self.redirect("%s?flash=%s" % (return_to, quote(flash_key)))

    def _choice_cookie_header(self, name, value, choices, max_age_s):
        """The `Set-Cookie` header for a UI-preference cookie (theme,
        lang): `name=value` with HttpOnly/SameSite=Strict/Path=/, or
        None when `value` is not a member of `choices` — an unrecognised
        submission sets no cookie at all. Routed through
        auth.secure_cookie_flag() so every cookie this app sets, session
        included, agrees on the Secure flag. The one format string
        `_handle_theme_post()`/`_handle_lang_post()` below share.
        """
        if value not in choices:
            return None
        return "%s=%s; HttpOnly%s; SameSite=Strict; Path=/; Max-Age=%d" % (
            name, value, auth.secure_cookie_flag(), max_age_s)

    def _handle_theme_post(self):
        form = self.read_form()
        cookie_header = self._choice_cookie_header(
            auth.UI_THEME_COOKIE_NAME, form.get("ui_theme"), layout.UI_THEME_CHOICES,
            THEME_COOKIE_MAX_AGE_S)
        return self.redirect(self._referring_tab(), set_cookie=cookie_header)

    def _handle_lang_post(self):
        """POST /ui-lang — byte-for-byte sibling of _handle_theme_post()
        above. An unrecognised value sets no cookie and still redirects,
        exactly like the theme route already behaves.
        """
        form = self.read_form()
        cookie_header = self._choice_cookie_header(
            auth.UI_LANG_COOKIE_NAME, form.get("ui_lang"), prefs.LANG_CHOICES,
            LANG_COOKIE_MAX_AGE_S)
        return self.redirect(self._referring_tab(), set_cookie=cookie_header)

    def _handle_update_install_post(self):
        """POST UPDATE_INSTALL_ROUTE: two-step confirmation, server-side,
        the same control-flow shape as
        `SettingsActionsMixin._handle_calendar_disconnect_post()` — a
        bare or non-matching `confirm` value renders the confirm page at
        200 without touching the registry, since that page (not the
        client-side `data-confirm` dialog the per-row Install form
        carries) is the real gate. `version` is checked against the
        registry's own version pattern and length cap before anything
        renders it, so an implausible value (a script tag, an oversized
        string) is treated as unknown rather than ever reaching a
        template — and the registry's own membership/floor/running-
        version checks in schedule_release() cover every other rejection
        (unknown, below floor, same as running, busy).
        """
        form = self.read_form()
        version = form.get("version") or ""
        if (
                len(version) > firmware_registry.VERSION_MAX_LEN
                or not firmware_registry.VERSION_RE.match(version)):
            return self.redirect(
                "%s?flash=%s" % (UPDATE_ROUTE, quote(FLASH_KEY_UPDATE_SCHEDULE_FAILED)))
        if form.get("confirm") != "yes":
            ctx = self.page_context()
            next_wake_text, wake_held = update_page.compute_next_wake_text(ctx)
            confirm_view = firmware_registry.update_view(
                firmware_registry.load_registry(self.args.state_dir),
                firmware_registry.load_device_report(self.args.state_dir),
                history_db.utc_now_iso())
            is_bench = any(
                release.get("version") == version and release.get("bench")
                for release in confirm_view.get("releases") or [])
            body = update_page.update_install_confirm_page(
                ctx, version, next_wake_text, wake_held=wake_held, is_bench=is_bench)
            return self.send_html(200, self._page_shell_for(UPDATE_ROUTE, body, ctx))
        state_dir = self.args.state_dir
        now = history_db.utc_now_iso()
        view = firmware_registry.update_view(
            firmware_registry.load_registry(state_dir),
            firmware_registry.load_device_report(state_dir), now)
        try:
            result = firmware_registry.schedule_release(
                state_dir, version, view.get("running_version"), now)
        except (OSError, TimeoutError):
            result = None
        if result == "scheduled":
            return self.redirect(UPDATE_ROUTE)
        if result == "busy":
            # An install is already running -- the generic
            # schedule-failed copy tells the operator to retry, which
            # cannot work until that install finishes.
            return self.redirect(
                "%s?flash=%s" % (UPDATE_ROUTE, quote(FLASH_KEY_UPDATE_BUSY)))
        return self.redirect(
            "%s?flash=%s" % (UPDATE_ROUTE, quote(FLASH_KEY_UPDATE_SCHEDULE_FAILED)))

    def _handle_update_cancel_post(self):
        """POST UPDATE_CANCEL_ROUTE: a plain POST, no confirmation step —
        cancelling is non-destructive and immediately reversible
        (Install again). Only fails once the device has already
        acknowledged the offer (firmware_registry.cancel_schedule()'s
        own "not_cancellable" outcome).
        """
        try:
            result = firmware_registry.cancel_schedule(self.args.state_dir)
        except (OSError, TimeoutError):
            result = None
        if result in ("cancelled", "none"):
            return self.redirect(UPDATE_ROUTE)
        return self.redirect(
            "%s?flash=%s" % (UPDATE_ROUTE, quote(FLASH_KEY_UPDATE_CANCEL_FAILED)))

    def do_POST(self):
        """Same one-connection-per-request scope as `do_GET()` above,
        wrapped around the unchanged `_dispatch()` dispatch - the
        Origin/Sec-Fetch-Site gate stays that dispatch's first statement,
        run before this scope has opened anything.
        """
        with history_db.connection_scope(self.args.state_dir):
            return self._dispatch("POST")

    # --- logging -------------------------------------------------------

    def log_message(self, fmt, *fmt_args):
        # Method and path only — matching stub-server/byos_server.py's own
        # override. Never a header, a cookie, a form body, or a query
        # string; the query string is stripped here even though
        # self.path may carry one (e.g. a flash-key redirect).
        print("%s %s" % (self.command, urlsplit(self.path).path))


def build_parser():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--bind",
        default="0.0.0.0",
        help="Address to listen on. Production passes 127.0.0.1 because "
             "Caddy is the only intended client (SEC-01/D-22); the "
             "default keeps LAN/dev use working unchanged.",
    )
    parser.add_argument(
        "--state-dir",
        default=state_store.DEFAULT_STATE_DIR,
        help="Directory holding the poll pipeline's own state (default: "
             "server/state/) — read-only from this service's perspective "
             "except via the real production poll cycle POST /poll-now "
             "triggers.",
    )
    parser.add_argument(
        "--geofence",
        default=None,
        help="Path to the geofence JSON forwarded to a manually-triggered "
             "poll cycle (default: adsb-test/runway3.json).",
    )
    return parser


def main():
    args = build_parser().parse_args()
    try:
        auth.configured_password()
    except auth.AuthNotConfigured as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    # Matches stub-server/byos_server.py's own main(): stdout is fully
    # buffered (not line-buffered) once journald redirects it away from a
    # TTY, which can silently lose this process's own startup line and
    # every server.poll_cycle print (still prefixed "poll_loop: ") a POST
    # /poll-now trigger emits if the service is ever killed before the
    # buffer next flushes.
    sys.stdout.reconfigure(line_buffering=True)

    Handler.args = args
    server = ThreadingHTTPServer((args.bind, args.port), Handler)
    print("companion: serving on %s:%d (state_dir=%s)" % (
        args.bind, args.port, args.state_dir))
    server.serve_forever()


if __name__ == "__main__":
    main()
