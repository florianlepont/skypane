#!/usr/bin/env python3
"""SkyPane companion service: a stdlib `ThreadingHTTPServer` with a
hand-rolled route table, run as its own systemd unit, separate from the
vendored device-protocol server in `stub-server/`.

Every route except the login routes and the stylesheet requires a
session (`Handler.require_session()`), enforced in this one file. Binds
`--bind 0.0.0.0` by default; production passes `--bind 127.0.0.1`
because Caddy is the only intended client.

Never writes the poll pipeline's own persisted flight-state file —
`server.poll_loop.run_once()` is that file's one legitimate writer.

`main()` fails closed on a missing password rather than starting with
auth silently disabled.
"""
import email.message
# Serialises the login lockout's server-computed remaining-seconds figure
# into the data-* attribute companion/static/login-card.js seeds its
# countdown from; never anything client-supplied.
import json
import os
import socket
import sqlite3
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlsplit

from PIL import Image

# Same repo-root sys.path bootstrap as server/poll_loop.py, so
# server.* resolves whether this file runs as a package or standalone.
_HERE = os.path.dirname(os.path.abspath(__file__))  # companion/
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from companion import (  # noqa: E402
    auth, frame_state, i18n, illustration_normalize, layout, prefs, theme_preview, wake)
from companion.pages import (  # noqa: E402
    airlines_page,
    config_page,
    health_page,
    history_page,
    home_page,
)
# Reuses airlines_page's own membership test rather than re-implementing
# it, so the render path (airlines_page.render()) and the write path
# (Handler._handle_manual_resolve_post() below) can never diverge.
from companion.pages.airlines_page import unresolved_row_for_prefix  # noqa: E402
from server import device_config, history_db, notify  # noqa: E402
from server.plane import (  # noqa: E402
    calendar_rules, colour_rules, illustrations, manual_resolutions)
import server.poll_loop as poll_loop  # noqa: E402

DEFAULT_PORT = 8643
GALLERY_DIRNAME = "gallery"
GALLERY_DEFAULT_LIMIT = 30
POLL_COOLDOWN_S = 45  # tens of seconds, a double-click guard, not an abuse rate-limit.
THEME_COOKIE_MAX_AGE_S = 365 * 24 * 3600
# Reuses THEME_COOKIE_MAX_AGE_S's own value and reasoning: a per-browser
# preference the site should remember indefinitely.
LANG_COOKIE_MAX_AGE_S = THEME_COOKIE_MAX_AGE_S
MAX_FORM_BYTES = 8192  # far more than any form on this site needs.
# Bounds peak memory per upload to a few MB. Enforced by the caller
# (Handler._read_upload_body()), not by parse_single_uploaded_file().
MAX_ILLUSTRATION_UPLOAD_BYTES = 4 * 1024 * 1024
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
STYLE_ROUTE = "/static/style.css"
# Each *_SCRIPT_ROUTE is the authoritative value a matching
# *_SCRIPT_SRC constant elsewhere must equal exactly; a test asserts
# the sync. Most are pre-auth by design (no session data, or served
# only to the login page itself).
SCRIPT_ROUTE = "/static/battery-trend.js"
NAV_SCRIPT_ROUTE = "/static/nav-dropdown.js"
DIRTY_STATE_SCRIPT_ROUTE = "/static/dirty-state.js"
LIST_FILTER_SCRIPT_ROUTE = "/static/list-filter.js"
COPY_BUTTON_SCRIPT_ROUTE = "/static/copy-button.js"
FRESHNESS_SCRIPT_ROUTE = "/static/freshness.js"
PANEL_LOOKUP_SCRIPT_ROUTE = "/static/panel-lookup.js"
FLASH_CLEANUP_SCRIPT_ROUTE = "/static/flash-cleanup.js"
POLL_COOLDOWN_SCRIPT_ROUTE = "/static/poll-cooldown.js"
CONFIRM_SUBMIT_SCRIPT_ROUTE = "/static/confirm-submit.js"
THEME_PREVIEW_SCRIPT_ROUTE = "/static/theme-preview.js"
FLIGHT_ROWS_SCRIPT_ROUTE = "/static/flight-rows.js"
LOGIN_CARD_SCRIPT_ROUTE = "/static/login-card.js"
SUBMIT_GUARD_SCRIPT_ROUTE = "/static/submit-guard.js"
RELATIVE_TIME_SCRIPT_ROUTE = "/static/relative-time.js"
QUICK_SWITCH_SCRIPT_ROUTE = "/static/quick-switch.js"
VALUE_CONTROLS_SCRIPT_ROUTE = "/static/value-controls.js"
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
THEME_ROUTE = "/ui-theme"
LANG_ROUTE = "/ui-lang"
LOGOUT_ROUTE = "/logout"
# The Preview page is retired into History; kept as a fixed-redirect
# source only.
PREVIEW_PAGE_ROUTE = "/preview"
GALLERY_ROUTE_PREFIX = "/gallery/"
# Rebound from config_page.py (the single definition site) rather than
# retyped, to avoid a reverse-import cycle. Same for RULES_*/CALENDAR_*/
# NOTIFICATIONS_TEST_ROUTE and the FLASH_KEY_* constants below.
RUNWAY_IMAGE_ROUTE_PREFIX = config_page.RUNWAY_IMAGE_ROUTE_PREFIX
ILLUSTRATION_IMAGE_ROUTE_PREFIX = "/illustration/"
# Rebound from companion/theme_preview.py — the render/cache mechanism,
# not a page module, owns this prefix since it is also used from
# config_page.py's own theme-picker markup.
THEME_PREVIEW_ROUTE_PREFIX = theme_preview.THEME_PREVIEW_ROUTE_PREFIX
RULES_ADD_ROUTE = config_page.RULES_ADD_ROUTE
RULES_DELETE_ROUTE_PREFIX = config_page.RULES_DELETE_ROUTE_PREFIX
RULES_DELETE_ROUTE_SUFFIX = config_page.RULES_DELETE_ROUTE_SUFFIX
CALENDAR_DISCONNECT_ROUTE = config_page.CALENDAR_DISCONNECT_ROUTE
CALENDAR_CONNECT_ROUTE = config_page.CALENDAR_CONNECT_ROUTE
NOTIFICATIONS_TEST_ROUTE = config_page.NOTIFICATIONS_TEST_ROUTE

# The flash-key string literals below are defined exactly once, in
# companion/pages/config_page.py or companion/pages/airlines_page.py —
# imported here under their historical FLASH_KEY_* names so every
# existing call site in this file (and its test assertions against the
# literal query-string values) stays unchanged.
FLASH_KEY_SAVED = config_page.FLASH_SAVED
FLASH_KEY_SAVE_FAILED = config_page.FLASH_SAVE_FAILED
FLASH_KEY_POLL_TRIGGERED = config_page.FLASH_POLL_TRIGGERED
FLASH_KEY_POLL_COOLDOWN = config_page.FLASH_POLL_COOLDOWN
FLASH_KEY_POLL_FAILED = config_page.FLASH_POLL_FAILED
FLASH_KEY_POLL_ALREADY_RUNNING = config_page.FLASH_POLL_ALREADY_RUNNING
FLASH_KEY_ILLUSTRATION_REPLACED = airlines_page.FLASH_ILLUSTRATION_REPLACED
FLASH_KEY_ILLUSTRATION_REJECTED = airlines_page.FLASH_ILLUSTRATION_REJECTED
FLASH_KEY_ILLUSTRATION_REPLACE_FAILED = airlines_page.FLASH_ILLUSTRATION_REPLACE_FAILED
FLASH_KEY_MANUAL_RESOLVED = airlines_page.FLASH_MANUAL_RESOLVED
FLASH_KEY_MANUAL_NAME_EMPTY = airlines_page.FLASH_MANUAL_NAME_EMPTY
FLASH_KEY_MANUAL_NAME_TOO_LONG = airlines_page.FLASH_MANUAL_NAME_TOO_LONG
FLASH_KEY_MANUAL_NAME_RESERVED = airlines_page.FLASH_MANUAL_NAME_RESERVED
FLASH_KEY_MANUAL_PREFIX_STALE = airlines_page.FLASH_MANUAL_PREFIX_STALE
FLASH_KEY_MANUAL_REGISTRY_FULL = airlines_page.FLASH_MANUAL_REGISTRY_FULL
FLASH_KEY_MANUAL_SAVE_FAILED = airlines_page.FLASH_MANUAL_SAVE_FAILED
FLASH_KEY_MANUAL_DELETE_FAILED = airlines_page.FLASH_MANUAL_DELETE_FAILED
# Distinguishes a name the operator genuinely typed but that
# add_entry() can't use, from a genuinely empty field.
FLASH_KEY_MANUAL_NAME_UNUSABLE = airlines_page.FLASH_MANUAL_NAME_UNUSABLE
FLASH_KEY_RULE_ADDED = config_page.FLASH_RULE_ADDED
FLASH_KEY_RULE_REPLACED = config_page.FLASH_RULE_REPLACED
FLASH_KEY_RULE_KEY_INVALID = config_page.FLASH_RULE_KEY_INVALID
FLASH_KEY_RULE_REGISTRY_FULL = config_page.FLASH_RULE_REGISTRY_FULL
FLASH_KEY_RULE_SAVE_FAILED = config_page.FLASH_RULE_SAVE_FAILED
FLASH_KEY_RULE_DELETED = config_page.FLASH_RULE_DELETED
FLASH_KEY_RULE_DELETE_FAILED = config_page.FLASH_RULE_DELETE_FAILED
FLASH_KEY_CALENDAR_CONNECTED = config_page.FLASH_CALENDAR_CONNECTED
FLASH_KEY_CALENDAR_SYNC_FAILED = config_page.FLASH_CALENDAR_SYNC_FAILED
FLASH_KEY_CALENDAR_DISCONNECTED = config_page.FLASH_CALENDAR_DISCONNECTED
FLASH_KEY_CALENDAR_SYNC_DEFERRED = config_page.FLASH_CALENDAR_SYNC_DEFERRED
FLASH_KEY_CALENDAR_CONNECT_OK = config_page.FLASH_CALENDAR_CONNECT_OK
FLASH_KEY_CALENDAR_CONNECT_INVALID = config_page.FLASH_CALENDAR_CONNECT_INVALID
FLASH_KEY_NOTIFICATIONS_TEST_OK = config_page.FLASH_NOTIFICATIONS_TEST_OK
FLASH_KEY_NOTIFICATIONS_TEST_FAILED = config_page.FLASH_NOTIFICATIONS_TEST_FAILED

# A fixed key -> copy dictionary — the flash mechanism only ever renders
# one of these, never a value taken verbatim from the query string.
# FLASH_KEY_POLL_COOLDOWN's "{n}" is filled in with a server-computed
# remaining-seconds figure, never anything client-supplied.
FLASH_KEY_DISPLAY_ON = "display_on"
FLASH_KEY_DISPLAY_OFF = "display_off"
FLASH_KEY_QUIET_ON = "quiet_on"
FLASH_KEY_QUIET_OFF = "quiet_off"
FLASH_KEY_QUICK_FAILED = "quick_failed"
# The LED switch's own two outcomes, worded like the Quiet-hours pair
# rather than the Screen pair — the LED, like quiet hours, takes effect
# on the frame's next wake rather than within about five minutes.
FLASH_KEY_LED_ON = "led_on"
FLASH_KEY_LED_OFF = "led_off"

FLASH_MESSAGES = {
    FLASH_KEY_DISPLAY_ON: (
        "Screen switched on — the frame will wake up and show a picture "
        "within about five minutes."),
    FLASH_KEY_DISPLAY_OFF: (
        "Screen switched off — the frame will blank itself within about "
        "five minutes."),
    FLASH_KEY_QUIET_ON: "Quiet hours turned on — applies the next time the frame wakes up.",
    FLASH_KEY_QUIET_OFF: "Quiet hours turned off — applies the next time the frame wakes up.",
    FLASH_KEY_QUICK_FAILED: "Couldn't change that — please try again.",
    FLASH_KEY_LED_ON: "Diagnostic LED turned on — applies the next time the frame wakes up.",
    FLASH_KEY_LED_OFF: "Diagnostic LED turned off — applies the next time the frame wakes up.",
    # "%s" is filled by _resolve_flash_text()'s own frame-state special
    # case below with one computed delay sentence (companion/frame_state.py,
    # via the same wake.next_wake_status() triple the Frame strip and the
    # Quiet hours caption both read).
    FLASH_KEY_SAVED: "Saved — %s",
    FLASH_KEY_SAVE_FAILED: (
        "Couldn't save settings — please try again. If this keeps "
        "happening, check the companion service logs."),
    FLASH_KEY_POLL_TRIGGERED: (
        "Refreshing — the frame's new picture will appear on Home within a "
        "few seconds."),
    FLASH_KEY_POLL_COOLDOWN: "Poll triggered recently — try again in {n}s.",
    FLASH_KEY_POLL_FAILED: (
        "Poll trigger failed — please try again. If this keeps happening, "
        "check the companion service logs."),
    FLASH_KEY_POLL_ALREADY_RUNNING: "A poll is already in progress — try again in a moment.",
    FLASH_KEY_ILLUSTRATION_REPLACED: (
        "Illustration replaced — the frame will use it next time it wakes and polls."),
    # Actionable, states the real requirements in user terms, and never
    # echoes a server path or any part of the uploaded file back to the
    # client — validate_illustration_file()'s own problem strings go to
    # the service log only, never into this copy.
    FLASH_KEY_ILLUSTRATION_REJECTED: (
        "Couldn't use that image — upload a transparent PNG that's at "
        "least 1200 pixels wide and landscape (wider than tall)."),
    FLASH_KEY_ILLUSTRATION_REPLACE_FAILED: (
        "Couldn't replace the illustration — please try again. If this "
        "keeps happening, check the companion service logs."),
    # Must not imply the frame changes instantly: the frame only ever
    # picks up a manual resolution on its next wake/poll, bounded by
    # `wake_interval_s` (device_config.py) — never sooner, whatever the
    # copy might otherwise suggest.
    FLASH_KEY_MANUAL_RESOLVED: (
        "Airline name saved — the frame will pick it up next time it "
        "wakes and polls."),
    FLASH_KEY_MANUAL_NAME_EMPTY: "Enter an airline name before saving.",
    FLASH_KEY_MANUAL_NAME_TOO_LONG: (
        "That name's too long — airline names top out at 100 characters."),
    FLASH_KEY_MANUAL_NAME_RESERVED: (
        "That name is reserved for the frame's own fallback artwork — "
        "try the airline's real name instead."),
    FLASH_KEY_MANUAL_PREFIX_STALE: (
        "That coverage gap isn't there anymore — check Health for "
        "current gaps."),
    FLASH_KEY_MANUAL_REGISTRY_FULL: (
        "The manual-resolution list is full (200 entries) — delete an "
        "old one before adding another."),
    FLASH_KEY_MANUAL_SAVE_FAILED: (
        "Couldn't save that resolution — the frame's state directory "
        "may not be writable."),
    FLASH_KEY_MANUAL_DELETE_FAILED: (
        "Couldn't delete that entry — the frame's state directory may "
        "not be writable."),
    # Distinct from FLASH_KEY_MANUAL_NAME_EMPTY above — the operator did
    # type something, it just can't be turned into an illustration key.
    # Never echoes the rejected value back.
    FLASH_KEY_MANUAL_NAME_UNUSABLE: (
        "That name can't be used for an illustration — try a different "
        "spelling, or a name with letters and numbers."),
    # rule_replaced's copy is a template: the {key} placeholder is filled
    # in by _resolve_flash_text()'s own second special case below, never
    # interpolated here.
    FLASH_KEY_RULE_ADDED: (
        "Rule added — the frame will use it next time it wakes and polls."),
    FLASH_KEY_RULE_REPLACED: (
        "Updated the rule for {key} — it replaces the one that was "
        "there before, applied next time the frame wakes and polls."),
    FLASH_KEY_RULE_KEY_INVALID: (
        "That doesn't match the selected kind's format — a callsign "
        "(e.g. AFR1234), an ICAO24 hex (e.g. 3944F2), or a 3-letter "
        "prefix (e.g. AFR)."),
    # The entry count is a literal; colour_rules.COLOUR_RULE_MAX_ENTRIES
    # is also 200, and the two must be kept equal by hand (a test pins
    # this).
    FLASH_KEY_RULE_REGISTRY_FULL: (
        "The rules list is full (200 entries) — delete an old one "
        "before adding another."),
    FLASH_KEY_RULE_SAVE_FAILED: (
        "Couldn't save that rule — the frame's state directory may not "
        "be writable."),
    FLASH_KEY_RULE_DELETED: (
        "Rule deleted — the frame will stop using it next time it "
        "wakes and polls."),
    FLASH_KEY_RULE_DELETE_FAILED: (
        "Couldn't delete that rule — the frame's state directory may "
        "not be writable."),
    # "{n}"/"{s}" are filled from a fresh on-disk read at render time,
    # never carried through the redirect's query string.
    FLASH_KEY_CALENDAR_CONNECTED: (
        "Connected — {n} flight{s} from this calendar in the frame's "
        "current window."),
    # Never echoes anything the operator submitted or any exception text.
    FLASH_KEY_CALENDAR_SYNC_FAILED: (
        "Saved, but couldn't sync that calendar right now — check the "
        "URL and try again. The frame will keep retrying on its own "
        "schedule."),
    # States both halves of what a disconnect did: the calendar is
    # disconnected, AND the flights it had supplied are gone from disk —
    # a promise the code keeps and the operator has no other way to learn.
    FLASH_KEY_CALENDAR_DISCONNECTED: (
        "Calendar disconnected — the flights it supplied have been "
        "deleted from the server."),
    # Deliberately not FLASH_KEY_POLL_ALREADY_RUNNING's copy: that string
    # says nothing about whether the save itself succeeded, which would
    # leave the operator unsure their URL was even stored. This key says
    # plainly that the save landed and the sync will happen on the
    # frame's own next scheduled poll.
    FLASH_KEY_CALENDAR_SYNC_DEFERRED: (
        "Saved — a poll was already running, so this calendar will "
        "sync on the frame's next scheduled poll."),
    # "{n}" is filled by _resolve_flash_text()'s own fourth special case
    # below, read fresh from disk at render time — never carried through
    # the redirect's query string.
    FLASH_KEY_CALENDAR_CONNECT_OK: "Calendar connected — {n} flights found.",
    FLASH_KEY_CALENDAR_CONNECT_INVALID: (
        "Paste a valid calendar feed URL to connect one."),
    # Never echoes the stored URL or any part of server.notify's own
    # transport-exception text.
    FLASH_KEY_NOTIFICATIONS_TEST_OK: "Test notification sent.",
    FLASH_KEY_NOTIFICATIONS_TEST_FAILED: "Couldn't reach that topic — check the URL.",
}

# Every FLASH_KEY_* -> the ARIA role its rendered flash banner should
# carry — "alert" (assertive) for a genuine failure, "status" (polite)
# for everything else. page_context() resolves this into
# ctx["flash_role"], threaded into every layout.flash_banner(role=...)
# call site below.
FLASH_ROLES = {
    FLASH_KEY_SAVED: "status",
    FLASH_KEY_SAVE_FAILED: "alert",
    FLASH_KEY_POLL_TRIGGERED: "status",
    FLASH_KEY_POLL_COOLDOWN: "status",
    FLASH_KEY_POLL_FAILED: "alert",
    # Informational, not itself a failure — a different session/tab is
    # already legitimately running a poll.
    FLASH_KEY_POLL_ALREADY_RUNNING: "status",
    # Success and rejection are both user-facing outcomes of a normal
    # upload flow (polite "status"); an unexpected server-side failure
    # takes the assertive "alert" role, matching FLASH_KEY_SAVE_FAILED's
    # own treatment above.
    FLASH_KEY_ILLUSTRATION_REPLACED: "status",
    FLASH_KEY_ILLUSTRATION_REJECTED: "status",
    FLASH_KEY_ILLUSTRATION_REPLACE_FAILED: "alert",
    # Success is "status"; every rejection or failure is "alert".
    FLASH_KEY_MANUAL_RESOLVED: "status",
    FLASH_KEY_MANUAL_NAME_EMPTY: "alert",
    FLASH_KEY_MANUAL_NAME_TOO_LONG: "alert",
    FLASH_KEY_MANUAL_NAME_RESERVED: "alert",
    FLASH_KEY_MANUAL_PREFIX_STALE: "alert",
    FLASH_KEY_MANUAL_REGISTRY_FULL: "alert",
    FLASH_KEY_MANUAL_SAVE_FAILED: "alert",
    FLASH_KEY_MANUAL_DELETE_FAILED: "alert",
    FLASH_KEY_MANUAL_NAME_UNUSABLE: "alert",
    # Added/replaced/deleted are "status" (an outcome of a normal
    # add/delete flow); key-invalid/registry-full/save-failed/
    # delete-failed are "alert" (a rejection or a genuine failure).
    FLASH_KEY_RULE_ADDED: "status",
    FLASH_KEY_RULE_REPLACED: "status",
    FLASH_KEY_RULE_KEY_INVALID: "alert",
    FLASH_KEY_RULE_REGISTRY_FULL: "alert",
    FLASH_KEY_RULE_SAVE_FAILED: "alert",
    FLASH_KEY_RULE_DELETED: "status",
    FLASH_KEY_RULE_DELETE_FAILED: "alert",
    FLASH_KEY_CALENDAR_CONNECTED: "status",
    FLASH_KEY_CALENDAR_SYNC_FAILED: "alert",
    FLASH_KEY_CALENDAR_DISCONNECTED: "status",
    FLASH_KEY_CALENDAR_SYNC_DEFERRED: "status",
    FLASH_KEY_CALENDAR_CONNECT_OK: "status",
    FLASH_KEY_CALENDAR_CONNECT_INVALID: "alert",
    FLASH_KEY_NOTIFICATIONS_TEST_OK: "status",
    FLASH_KEY_NOTIFICATIONS_TEST_FAILED: "alert",
}

_STYLE_CSS_PATH = os.path.join(_HERE, "static", "style.css")
_BATTERY_TREND_JS_PATH = os.path.join(_HERE, "static", "battery-trend.js")
_NAV_DROPDOWN_JS_PATH = os.path.join(_HERE, "static", "nav-dropdown.js")
_DIRTY_STATE_JS_PATH = os.path.join(_HERE, "static", "dirty-state.js")
_LIST_FILTER_JS_PATH = os.path.join(_HERE, "static", "list-filter.js")
_COPY_BUTTON_JS_PATH = os.path.join(_HERE, "static", "copy-button.js")
_FRESHNESS_JS_PATH = os.path.join(_HERE, "static", "freshness.js")
_PANEL_LOOKUP_JS_PATH = os.path.join(_HERE, "static", "panel-lookup.js")
_FLASH_CLEANUP_JS_PATH = os.path.join(_HERE, "static", "flash-cleanup.js")
_POLL_COOLDOWN_JS_PATH = os.path.join(_HERE, "static", "poll-cooldown.js")
_CONFIRM_SUBMIT_JS_PATH = os.path.join(_HERE, "static", "confirm-submit.js")
_THEME_PREVIEW_JS_PATH = os.path.join(_HERE, "static", "theme-preview.js")
_FLIGHT_ROWS_JS_PATH = os.path.join(_HERE, "static", "flight-rows.js")
_LOGIN_CARD_JS_PATH = os.path.join(_HERE, "static", "login-card.js")
_SUBMIT_GUARD_JS_PATH = os.path.join(_HERE, "static", "submit-guard.js")
_RELATIVE_TIME_JS_PATH = os.path.join(_HERE, "static", "relative-time.js")
_QUICK_SWITCH_JS_PATH = os.path.join(_HERE, "static", "quick-switch.js")
_VALUE_CONTROLS_JS_PATH = os.path.join(_HERE, "static", "value-controls.js")
_RUNWAY_IMAGE_DIR = os.path.join(_HERE, "static")

# Process-global, not per-session: keyed per client IP and bounded, so
# failed logins from one address never lock another.
LOGIN_THROTTLE = auth.LoginThrottle()

# Guards the check-cooldown -> run_once() -> mark-triggered sequence in
# _handle_poll_now(), so two concurrent POST /poll-now requests can
# never both call poll_loop.run_once(). Process-local only: correct
# because main() runs exactly one ThreadingHTTPServer in one OS process.
_POLL_LOCK = threading.Lock()

_PAGE_TITLES = {
    layout.HOME_ROUTE: "Home",
    layout.DISPLAY_ROUTE: "Display",
    layout.FLIGHTS_ROUTE: "Flights",
    layout.AIRLINES_ROUTE: "Airlines",
    layout.HEALTH_ROUTE: "Health",
    layout.DEVICE_ROUTE: "Device",
}

# The login card's one-sentence purpose text.
LOGIN_EXPLANATION_TEXT = "Sign in to manage this device's settings."

# A module constant beside LOGIN_EXPLANATION_TEXT because _login_body()
# and the live countdown's template must both build from this one string.
LOGIN_LOCKOUT_TEXT = "Too many attempts — try again in %ds."

# The substitution token the live countdown swaps for the remaining
# figure each second. "__N__" is excluded from test_i18n.py's French-
# catalogue scan as an uppercase code; a lowercase placeholder would not
# be, and would have to be translated (meaningless) or exempted.
LOGIN_LOCKOUT_TEMPLATE_TOKEN = "__N__"

# The id the login card's one message element carries (wrong-password
# and lockout share it); `aria-describedby` points at it only when a
# message is rendered.
LOGIN_MESSAGE_ID = "login-error"

# Rendered as server-escaped data-* attributes and swapped by
# companion/static/login-card.js, so that file hard-codes no English.
LOGIN_REVEAL_SHOW_LABEL = "Show password"
LOGIN_REVEAL_HIDE_LABEL = "Hide password"

# Marks, not words — deliberately not translated; legible without
# relying on colour alone.
LOGIN_REVEAL_MASKED_GLYPH = "●"
LOGIN_REVEAL_SHOWN_GLYPH = "○"

# `layout.page_header()` escapes both when it renders them — these are
# always plain strings, never pre-escaped markup.
NOT_FOUND_TITLE = "Page not found."
NOT_FOUND_PURPOSE_TEXT = "The page you requested doesn't exist or may have moved."

# do_POST()'s own Origin/Sec-Fetch-Site gate's 403 body — see
# _forbidden_page() below.
FORBIDDEN_TITLE = "Request refused"
FORBIDDEN_PURPOSE_TEXT = (
    "This request came from another site, so it was refused. Open SkyPane "
    "directly and try again.")


def _validated_next_route(candidate):
    """Validate a caller-supplied `next` redirect target against
    `layout.NAV_TABS`'s known routes. Open-redirect mitigation: an exact
    membership test, never `startswith`/URL-parsed/regex-matched.
    Anything not byte-identical to a real route is discarded (`None`).
    """
    allowed = {route for route, _ in layout.NAV_TABS}
    return candidate if candidate in allowed else None


def _resolve_flash_text(
        flash_key, state_dir, rule_key=None, last_checkin_ts=None, device_cfg=None,
        battery_critical=False):
    """Build this flash's already-translated message text, or None if
    flash_key is unknown.

    rule_key: re-normalised before interpolation — never trusted raw;
    a failed check degrades to the generic FLASH_KEY_RULE_ADDED copy.
    last_checkin_ts/device_cfg/battery_critical: feed the one computed
    delay sentence via the same wake.next_wake_status() triple every
    other reader shares, so they can never disagree.
    """
    if flash_key not in FLASH_MESSAGES:
        return None
    # Translate first, fill placeholders after, so the French template
    # controls where the value lands. One expression, so test_i18n.py's
    # scanner sees FLASH_MESSAGES as a real i18n.t() consumer.
    template = i18n.t(FLASH_MESSAGES[flash_key])
    if flash_key == FLASH_KEY_SAVED:
        next_wake_iso, effective_interval_s, hold_reason = wake.next_wake_status(
            last_checkin_ts, device_cfg or {}, battery_critical=battery_critical)
        delay_template = frame_state.delay_sentence_template(
            next_wake_iso, effective_interval_s, hold_reason)
        delay_text = i18n.t(delay_template)
        if "%s" in delay_text:
            next_wake_parsed = layout.parse_iso(next_wake_iso)
            clock = (
                layout.local_clock_text(next_wake_parsed)
                if next_wake_parsed is not None else None)
            delay_text = (
                delay_text % clock if clock else i18n.t(frame_state.DELAY_UNKNOWN))
        # Lower-cased so the computed clause reads naturally after
        # "Saved — " (every frame_state sentence is written to stand
        # alone, capitalised, as a settings-caption's own second
        # sentence — not as a flash banner's trailing clause).
        if delay_text:
            delay_text = delay_text[:1].lower() + delay_text[1:]
        return template % delay_text
    if flash_key == FLASH_KEY_POLL_COOLDOWN:
        return template.format(n=poll_cooldown_remaining(state_dir))
    if flash_key == FLASH_KEY_CALENDAR_CONNECTED:
        # Read fresh from disk, on this redirect target's own render —
        # never carried through the redirect's query string, which is
        # client-supplied on the way back in. load_calendar_registry() is
        # contractually never-raising, which is what makes it safe to
        # call unconditionally here on every render that carries this key.
        count = len(calendar_rules.load_calendar_registry(state_dir)["entries"])
        return template.format(n=count, s="" if count == 1 else "s")
    if flash_key == FLASH_KEY_CALENDAR_CONNECT_OK:
        count = len(calendar_rules.load_calendar_registry(state_dir)["entries"])
        return template.format(n=count)
    if flash_key == FLASH_KEY_RULE_REPLACED:
        normalised_key = colour_rules.normalise_rule_callsign(rule_key)
        if normalised_key is None:
            # Goes through i18n.t() like every other return path here —
            # an invalid rule_key must not silently produce an
            # untranslated English banner under a French request.
            return i18n.t(FLASH_MESSAGES[FLASH_KEY_RULE_ADDED])
        return template.format(key=normalised_key)
    return template


def poll_cooldown_remaining(state_dir):
    """Seconds remaining before another `POST /poll-now` is allowed, or 0
    when the cooldown has elapsed. Server-global and persisted in
    `history.db`'s meta table (not the session cookie), so a second
    browser tab cannot bypass it and a service restart does not reset it.
    """
    with history_db.open_db(state_dir) as conn:
        value = history_db.get_meta(conn, history_db.META_LAST_POLL_TRIGGER)
    if not value:
        return 0
    try:
        last_triggered = int(value)
    except (TypeError, ValueError):
        return 0
    remaining = POLL_COOLDOWN_S - (time.time() - last_triggered)
    return int(remaining) if remaining > 0 else 0


def env_wake_interval_default():
    """Deployed SKYPANE_SLEEP_S as an int, or None. Read fresh each call,
    not captured at import time. Clamped to `[WAKE_INTERVAL_MIN_S,
    WAKE_INTERVAL_MAX_S]` only for this Settings form `min=` pre-fill —
    `wake.effective_wake_interval_s()` reads the unclamped value. Fail-open
    (None), unlike `configured_password()`'s fail-closed contract: a UI
    convenience, not an auth boundary.
    """
    value = wake.env_sleep_s()
    if value is None:
        return None
    if device_config.WAKE_INTERVAL_MIN_S <= value <= device_config.WAKE_INTERVAL_MAX_S:
        return value
    return None


def _safe_last_checkin_ts(state_dir):
    """The device's last real check-in, as the raw `device_health.ts`
    string `history_db.latest_device_health()` returns, or `None` on any
    failure — a missing/locked/unreadable database, or simply no reading
    recorded yet. Narrow `(sqlite3.Error, OSError)` catch, the same
    shape `companion.pages.health_page._safe_query()` uses so one
    section's data access never faults the whole page render.
    """
    try:
        with history_db.open_db(state_dir) as conn:
            row = history_db.latest_device_health(conn)
    except (sqlite3.Error, OSError):
        return None
    return row["ts"] if row else None


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
            rows = history_db.recent_runway_events(conn, limit=1)
    except Exception:
        return None
    return rows[0] if rows else None


def mark_poll_triggered(state_dir):
    with history_db.open_db(state_dir) as conn:
        history_db.set_meta(
            conn, history_db.META_LAST_POLL_TRIGGER, str(int(time.time())))


def gallery_entries(state_dir, limit=GALLERY_DEFAULT_LIMIT):
    """The newest `limit` gallery filenames (name-descending; files are
    named by timestamp, so lexical order is chronological), filtered to
    files ending in the PNG extension. A missing gallery directory
    returns an empty list rather than raising.
    """
    gallery_dir = os.path.join(state_dir, GALLERY_DIRNAME)
    try:
        entries = sorted(
            (entry.name for entry in os.scandir(gallery_dir)
             if entry.is_file() and entry.name.endswith(".png")),
            reverse=True,
        )
    except OSError:
        return []
    return entries[:limit]


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


def _runway_image_filename(runway_id):
    """The single, mechanical place the on-disk naming convention is
    expressed: `runway-{runway_id}.png`.
    """
    return "runway-%s.png" % runway_id


def _runway_image_path(runway_id, image_dir=_RUNWAY_IMAGE_DIR):
    return os.path.join(image_dir, _runway_image_filename(runway_id))


def runway_images_available(image_dir=_RUNWAY_IMAGE_DIR):
    """The subset of `device_config.RUNWAY_IDS` that currently has a real
    `runway-{id}.png` file on disk. A missing `image_dir`, a missing
    individual file, or any other OS-level error while checking is a
    graceful-fallback state, not an error: `os.path.isfile()` already
    swallows `OSError`/`ValueError` and returns `False`. The result is
    bounded by the fixed `RUNWAY_IDS` registry (iterated, never
    `os.scandir()`-ed), so it can never report an image for an id that
    isn't a real runway.
    """
    available = set()
    for runway_id in device_config.RUNWAY_IDS:
        if os.path.isfile(_runway_image_path(runway_id, image_dir)):
            available.add(runway_id)
    return available


def _illustration_filenames(state_dir=None):
    """The known-safe membership set for validating a requested
    illustration key before any filesystem path is constructed: the
    fixed vendored list, unioned with resolved `manual_resolutions.json`
    entries. The manual half comes from a prior, already-durable
    request, never the current one. Recomputed per call, never cached,
    since that manual state is mutable.
    """
    filenames = set(illustrations.target_filenames())
    if state_dir:
        for entry in manual_resolutions.load_manual_resolutions(state_dir).values():
            key = manual_resolutions.illustration_key_for_name(entry["airline_name"])
            if key:
                filenames.add(key + ".png")
    return frozenset(filenames)


def parse_single_uploaded_file(content_type, body):
    """Parse a `multipart/form-data` body known to hold exactly one file
    part, returning its raw payload `bytes`, or `None` for anything that
    doesn't match that exact shape. Never raises. The header block
    (filename, field name, media type) is discarded and never parsed —
    the destination path and the "is this an image" check both come
    from elsewhere, never from this body's own claims.
    """
    try:
        message = email.message.Message()
        message["content-type"] = content_type
        if message.get_content_type() != "multipart/form-data":
            return None
        boundary = message.get_param("boundary")
        if not isinstance(boundary, str) or not boundary:
            return None
        boundary_bytes = boundary.encode("ascii")
        if len(boundary_bytes) > 70:  # RFC 2046 boundary length ceiling.
            return None

        delimiter = b"--" + boundary_bytes
        segments = body.split(delimiter)
        # Exactly one part: a preamble, the part itself, and an epilogue.
        # Zero parts, two-or-more parts, and a missing closing delimiter
        # all produce a different segment count and are rejected here.
        if len(segments) != 3:
            return None
        preamble, part, epilogue = segments
        if preamble.strip(b"\r\n \t") != b"":
            return None
        if not epilogue.startswith(b"--"):
            return None

        if not part.startswith(b"\r\n"):
            return None
        part = part[2:]
        header_block, separator, payload = part.partition(b"\r\n\r\n")
        if not separator:
            return None
        del header_block  # discarded — see docstring above.

        if payload.endswith(b"\r\n"):
            payload = payload[:-2]
        if not payload:
            return None
        return payload
    except Exception:
        return None


class Handler(BaseHTTPRequestHandler):
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

    def send_html(self, code, html_str):
        body = html_str.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        # Every HTML page is either session-gated or a login form — never
        # something a shared cache or the back button should replay
        # after sign-out.
        self.send_header("Cache-Control", "no-store")
        self._send_hardening_headers()
        self.end_headers()
        self.wfile.write(body)

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
        remainder is still drained so the connection isn't left corrupt.
        Reachable pre-auth from `POST /login`.
        """
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0:
            return {}
        try:
            raw = self.rfile.read(min(length, MAX_FORM_BYTES + 1))
            if length > MAX_FORM_BYTES:
                remaining = length - len(raw)
                while remaining > 0:
                    chunk = self.rfile.read(min(remaining, 65536))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                return {}
        except socket.timeout:
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
        first so the connection isn't left mid-body.
        """
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except (TypeError, ValueError):
            return None
        if length <= 0:
            return None
        try:
            raw = self.rfile.read(min(length, MAX_ILLUSTRATION_UPLOAD_BYTES + 1))
            if length > MAX_ILLUSTRATION_UPLOAD_BYTES:
                remaining = length - len(raw)
                while remaining > 0:
                    chunk = self.rfile.read(min(remaining, 65536))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                return None
        except socket.timeout:
            return None
        return raw

    def page_context(self):
        """Build the `ctx` dict every page module's render()/handle_post()
        receives — documented in full in companion/pages/__init__.py.
        """
        parsed = urlsplit(self.path)
        params = parse_qs(parsed.query)
        flash_key = params.get("flash", [None])[0]
        # For FLASH_KEY_RULE_REPLACED's copy; re-normalised inside
        # _resolve_flash_text() before ever being interpolated.
        rule_key = params.get("rule", [None])[0]
        state_dir = self.args.state_dir
        now = history_db.utc_now_iso()
        # Must run before safe_health_state() below: a fresh per-thread
        # ContextVar defaults to English, so setting the language late
        # would build health markup in the wrong language.
        prefs.set_request_prefs(lang=self._lang_from_request())
        # Computed once, threaded into ctx, so health_page.render() reuses
        # this snapshot instead of a second, non-atomic set of reads.
        health_state = health_page.safe_health_state(state_dir, now)
        # Loaded once, reused for both "device_config" and "screen_id".
        device_cfg = device_config.load_device_config(state_dir)
        # Loaded once, reused for three calendar_* ctx keys below.
        calendar_registry = calendar_rules.load_calendar_registry(state_dir)
        # Reused by _resolve_flash_text()'s FLASH_KEY_SAVED special case.
        last_checkin_ts = _safe_last_checkin_ts(state_dir)
        # Reused by _resolve_flash_text()'s delay-sentence computation.
        battery_critical = wake.read_battery_critical(state_dir)
        return {
            "state_dir": state_dir,
            "ui_theme": self._resolved_ui_theme(),
            "lang": prefs.current_lang(),
            "device_config": device_cfg,
            # The persisted screen_id, read from the same device_config
            # dict already loaded above — consumed via
            # companion.screens.current_screen_id(ctx), which already
            # falls back to DEFAULT_SCREEN_ID for a missing/unknown value.
            "screen_id": device_cfg.get("screen_id"),
            # Data only; the page module formats it, matching wake.py's
            # no-view-dependency rule.
            "last_checkin_ts": last_checkin_ts,
            "battery_critical": battery_critical,
            # An int in [WAKE_INTERVAL_MIN_S, MAX_S] or None. An on-disk
            # wake_interval_s always wins; this is only the pre-fill for
            # before the user ever sets one explicitly.
            "wake_interval_env_default": env_wake_interval_default(),
            "flash": _resolve_flash_text(
                flash_key, state_dir, rule_key=rule_key, last_checkin_ts=last_checkin_ts,
                device_cfg=device_cfg, battery_critical=battery_critical),
            "flash_role": FLASH_ROLES.get(flash_key, "status"),
            "poll_cooldown_remaining": poll_cooldown_remaining(state_dir),
            "gallery_entries": gallery_entries(state_dir),
            "runway_images": runway_images_available(),
            # The "ok"/"warn"/"error" severity, sourced from the single
            # `health_state` computed above rather than a second query.
            "health_severity": health_state["severity"] if health_state else "ok",
            "health_state": health_state,
            "now": now,
            # Deliberately unvalidated: validation belongs to
            # airlines_page.unresolved_row_for_prefix(), the single
            # membership test shared by the render and write paths.
            "resolve_prefix": params.get(
                airlines_page.RESOLVE_QUERY_PARAM, [None])[0],
            # Deliberately unvalidated: validation belongs to
            # history_page.flights_limit(). Presentation-only.
            "flights_limit": params.get(
                history_page.FLIGHTS_LIMIT_QUERY_PARAM, [None])[0],
            # Read fresh per request, never through the poll cycle's own
            # process-scoped cache — this is a long-running server.
            "manual_resolutions": manual_resolutions.load_manual_resolutions(state_dir),
            # Read fresh per request for the same reason.
            # cycle.
            "colour_rules": colour_rules.load_colour_rules(state_dir),
            # A status line only needs presence, not the value: the
            # calendar URL is a subscription secret, never rendered.
            "calendar_configured": calendar_rules.calendar_is_configured(state_dir),
            # Read fresh from disk; a sync landing mid-session must be
            # visible on the very next request.
            "calendar_last_synced_at": calendar_registry["last_synced_at"],
            # Distinguishes "just connected, no sync yet" from "has been
            # failing", without a new server-side field.
            "calendar_last_attempt_at": calendar_registry["last_attempt_at"],
            "calendar_entry_count": len(calendar_registry["entries"]),
            # Consumed by config_page.calendar_group()'s status branch
            # alone; never widens calendar_configured's own bool contract.
            "calendar_drift": calendar_rules.calendar_secret_mode_is_unsafe(state_dir),
        }

    # --- shared page fragments -------------------------------------------

    def _not_found_page(self):
        """The shared 404 body, reached pre-auth from static-asset
        delegates too. `health_alert` is computed only on
        `self._is_authenticated()` (a pure bool check) so Health's
        warn/error state never leaks to an unauthenticated caller.
        `self.page_context()` is deliberately not called: too many
        reads for an error path.
        """
        # Pre-session: resolved from the cookie or Accept-Language.
        prefs.set_request_prefs(lang=self._lang_from_request())
        health_alert = None
        if self._is_authenticated():
            health_state = health_page.safe_health_state(
                self.args.state_dir, history_db.utc_now_iso())
            health_alert = health_state["severity"] if health_state else "ok"
        body = (
            layout.page_header(i18n.t(NOT_FOUND_TITLE), purpose=i18n.t(NOT_FOUND_PURPOSE_TEXT))
            + '<p class="text-body"><a href="%s">%s</a></p>'
            % (HOME_ROUTE, layout.escape_html(i18n.t("Back to Home")))
        )
        return layout.page_shell(
            # The <title> tag's own short form — distinct from
            # NOT_FOUND_TITLE above (the page heading's longer sentence) —
            # needs its own i18n.t() entry so the browser tab is
            # translated too.
            title=i18n.t("Not Found"), active="", body=body,
            ui_theme=self._resolved_ui_theme(), health_alert=health_alert)

    def _forbidden_page(self):
        """The shared 403 body for do_POST()'s Origin/Sec-Fetch-Site gate.
        Byte-for-byte the same shape as `_not_found_page()` above, kept
        as a separate helper so a later route-table refactor can relocate
        this gate independently.
        """
        prefs.set_request_prefs(lang=self._lang_from_request())
        health_alert = None
        if self._is_authenticated():
            health_state = health_page.safe_health_state(
                self.args.state_dir, history_db.utc_now_iso())
            health_alert = health_state["severity"] if health_state else "ok"
        body = (
            layout.page_header(i18n.t(FORBIDDEN_TITLE), purpose=i18n.t(FORBIDDEN_PURPOSE_TEXT))
            + '<p class="text-body"><a href="%s">%s</a></p>'
            % (HOME_ROUTE, layout.escape_html(i18n.t("Back to Home")))
        )
        return layout.page_shell(
            title=i18n.t(FORBIDDEN_TITLE), active="", body=body,
            ui_theme=self._resolved_ui_theme(), health_alert=health_alert)

    def _login_body(self, error=None, lockout_seconds=None, next_route=None):
        """The login card's inner markup. `next_route` rides a hidden
        field so a failed login doesn't lose the destination. `error` is
        already translated by the caller; this only escapes it, so
        test_i18n.py's scanner can trace the literal at its one call
        site. `aria-invalid="true"` fires only on wrong-password, never
        on lockout (the typed value isn't what's wrong).
        """
        parts = [
            '<h1 class="page-title">SkyPane</h1>',
            '<p class="text-body">%s</p>' % layout.escape_html(i18n.t(LOGIN_EXPLANATION_TEXT)),
        ]
        # `if lockout_seconds:` (not `is not None`): a zero or absent
        # figure never renders a lockout sentence, matching
        # companion/static/login-card.js's own `remaining > 0` guard.
        locked = bool(lockout_seconds)
        if locked:
            message = i18n.t(LOGIN_LOCKOUT_TEXT) % lockout_seconds
        elif error:
            message = error
        else:
            message = None

        field_attrs = ""
        if message is not None:
            field_attrs += ' aria-describedby="%s"' % LOGIN_MESSAGE_ID
        if message is not None and not locked:
            field_attrs += ' aria-invalid="true"'
        # During a lockout both controls are natively disabled. This is
        # an affordance, never a boundary: companion/auth.py's
        # LoginThrottle is re-consulted on every POST before the
        # password is even looked at, so a visitor who re-enables these
        # two elements in devtools gains nothing at all.
        if locked:
            field_attrs += " disabled"

        # The live countdown's seed and template, server-computed and
        # serialised here — never computed from a client clock.
        form_attrs = ""
        if locked:
            form_attrs = (
                ' data-lockout-seconds="%s" data-lockout-template="%s"'
                ' data-lockout-token="%s"' % (
                    layout.escape_html(json.dumps(int(lockout_seconds))),
                    layout.escape_html(
                        i18n.t(LOGIN_LOCKOUT_TEXT).replace(
                            "%d", LOGIN_LOCKOUT_TEMPLATE_TOKEN)),
                    layout.escape_html(LOGIN_LOCKOUT_TEMPLATE_TOKEN)))

        message_html = (
            '<p id="%s" class="field-error text-label" role="alert">%s</p>'
            % (LOGIN_MESSAGE_ID, layout.escape_html(message))
        ) if message is not None else ""

        next_field_html = (
            '<input type="hidden" name="next" value="%s">'
            % layout.escape_html(next_route)) if next_route else ""
        parts.append(
            '<form method="post" action="%s" class="login-form"%s>'
            "%s"
            '<label for="password">%s</label>'
            '<span class="login-form__field">'
            '<input type="password" id="password" name="password" '
            'class="login-form__input" '
            'autocomplete="current-password" autofocus required%s>'
            "%s"
            "</span>"
            "%s"
            '<button type="submit"%s>%s</button>'
            "</form>" % (
                LOGIN_ROUTE, form_attrs, next_field_html,
                layout.escape_html(i18n.t("Password")),
                field_attrs,
                self._login_reveal_toggle_html(),
                message_html,
                " disabled" if locked else "",
                layout.escape_html(i18n.t("Sign in")))
        )
        return "".join(parts)

    @staticmethod
    def _login_reveal_toggle_html():
        """The show-password toggle. Server-rendered `hidden`, always —
        a script-blocked browser never sees it (no-JS floor by
        construction), and the form still submits normally. Glyph swaps
        with state so appearance isn't carried by colour alone; both
        labels/glyphs are server-escaped data-* attributes so no English
        is hard-coded in the JS.
        """
        show_label = i18n.t(LOGIN_REVEAL_SHOW_LABEL)
        return (
            '<button type="button" class="copy-btn login-reveal" hidden '
            'aria-pressed="false" aria-label="%s" title="%s" '
            'data-login-reveal data-show-label="%s" data-hide-label="%s" '
            'data-show-glyph="%s" data-hide-glyph="%s">'
            '<span class="icon login-reveal__glyph" aria-hidden="true" '
            'data-login-reveal-glyph>%s</span>'
            "</button>" % (
                layout.escape_html(show_label),
                layout.escape_html(show_label),
                layout.escape_html(show_label),
                layout.escape_html(i18n.t(LOGIN_REVEAL_HIDE_LABEL)),
                layout.escape_html(LOGIN_REVEAL_MASKED_GLYPH),
                layout.escape_html(LOGIN_REVEAL_SHOWN_GLYPH),
                layout.escape_html(LOGIN_REVEAL_MASKED_GLYPH))
        )

    def _render_login_page(self, error=None, lockout_seconds=None, next_route=None):
        # Pre-session, like _not_found_page() above.
        prefs.set_request_prefs(lang=self._lang_from_request())
        body = self._login_body(
            error=error, lockout_seconds=lockout_seconds, next_route=next_route)
        return layout.login_shell(body, ui_theme=self._resolved_ui_theme())

    def _serve_stylesheet(self):
        try:
            with open(_STYLE_CSS_PATH, "rb") as fh:
                payload = fh.read()
        except OSError:
            return self.send_html(404, self._not_found_page())
        # Pre-auth, identical for every client: legitimately shared-cacheable.
        return self.send_bytes(200, "text/css", payload, cache_seconds=300, public=True)

    def _serve_script_file(self, abs_path):
        """Serve one fixed JavaScript file, pre-auth. `abs_path` is
        always one of this module's own path constants, never a
        client-supplied segment, so it has no path-traversal surface.
        Shared body for every `_serve_*_script()` method below.
        """
        try:
            with open(abs_path, "rb") as fh:
                payload = fh.read()
        except OSError:
            return self.send_html(404, self._not_found_page())
        # text/javascript is the sole current-standard MIME type for
        # JavaScript per RFC 9239 (2022), which obsoletes RFC 4329's older
        # application/-prefixed form — deliberately not used here.
        return self.send_bytes(200, "text/javascript", payload, cache_seconds=300, public=True)

    # Each below is a thin delegate onto _serve_script_file(). No
    # catch-all /static/ handler: a new script needs its own route,
    # serve method and do_GET() branch.

    def _serve_battery_trend_script(self):
        return self._serve_script_file(_BATTERY_TREND_JS_PATH)

    def _serve_nav_dropdown_script(self):
        return self._serve_script_file(_NAV_DROPDOWN_JS_PATH)

    def _serve_dirty_state_script(self):
        return self._serve_script_file(_DIRTY_STATE_JS_PATH)

    def _serve_list_filter_script(self):
        return self._serve_script_file(_LIST_FILTER_JS_PATH)

    def _serve_copy_button_script(self):
        return self._serve_script_file(_COPY_BUTTON_JS_PATH)

    def _serve_freshness_script(self):
        return self._serve_script_file(_FRESHNESS_JS_PATH)

    def _serve_panel_lookup_script(self):
        return self._serve_script_file(_PANEL_LOOKUP_JS_PATH)

    def _serve_flash_cleanup_script(self):
        return self._serve_script_file(_FLASH_CLEANUP_JS_PATH)

    def _serve_poll_cooldown_script(self):
        return self._serve_script_file(_POLL_COOLDOWN_JS_PATH)

    def _serve_confirm_submit_script(self):
        return self._serve_script_file(_CONFIRM_SUBMIT_JS_PATH)

    def _serve_theme_preview_script(self):
        return self._serve_script_file(_THEME_PREVIEW_JS_PATH)

    def _serve_flight_rows_script(self):
        return self._serve_script_file(_FLIGHT_ROWS_JS_PATH)

    def _serve_login_card_script(self):
        return self._serve_script_file(_LOGIN_CARD_JS_PATH)

    def _serve_submit_guard_script(self):
        return self._serve_script_file(_SUBMIT_GUARD_JS_PATH)

    def _serve_relative_time_script(self):
        return self._serve_script_file(_RELATIVE_TIME_JS_PATH)

    def _serve_quick_switch_script(self):
        return self._serve_script_file(_QUICK_SWITCH_JS_PATH)

    def _serve_value_controls_script(self):
        return self._serve_script_file(_VALUE_CONTROLS_JS_PATH)

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
        try:
            with open(path, "rb") as fh:
                payload = fh.read()
        except OSError:
            return self.send_html(404, self._not_found_page())
        return self.send_bytes(200, "image/png", payload, cache_seconds=300)

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

    def _handle_illustration_replace(self, key):
        """POST /illustration/{key}.png — upload a replacement
        illustration, the first untrusted file upload this codebase
        handles. Membership-tests `key` before any path is built or
        body byte is read. Only the server's own Pillow re-encode is
        ever written to disk — the client's original bytes are never
        stored. No CSRF token: relies on SameSite=Strict, like every
        other state-changing POST.
        """
        filename = key + ".png"
        if filename not in _illustration_filenames(self.args.state_dir):
            return self.send_html(404, self._not_found_page())

        raw = self._read_upload_body()
        if raw is None:
            return self.redirect(
                "/airlines?flash=%s" % quote(FLASH_KEY_ILLUSTRATION_REJECTED))

        payload = parse_single_uploaded_file(self.headers.get("Content-Type"), raw)
        if payload is None or len(payload) > MAX_ILLUSTRATION_UPLOAD_BYTES:
            return self.redirect(
                "/airlines?flash=%s" % quote(FLASH_KEY_ILLUSTRATION_REJECTED))

        state_dir = self.args.state_dir
        override_dir = illustrations.override_dir_for_state_dir(state_dir)
        try:
            os.makedirs(override_dir, exist_ok=True)
        except OSError:
            return self.redirect(
                "/airlines?flash=%s" % quote(FLASH_KEY_ILLUSTRATION_REPLACE_FAILED))

        # Both temps live in override_dir so os.replace() below is a
        # same-filesystem atomic rename, named from key+pid only.
        raw_tmp_path = os.path.join(
            override_dir, ".%s.%d.upload.tmp" % (key, os.getpid()))
        encoded_tmp_path = os.path.join(
            override_dir, ".%s.%d.encoded.tmp" % (key, os.getpid()))
        try:
            with open(raw_tmp_path, "wb") as fh:
                fh.write(payload)

            # Reads format/dimensions from the header only, rejecting an
            # over-cap pixel count before any pixel data decodes — a
            # decompression-bomb upload is never expanded.
            problems = illustrations.validate_illustration_file(raw_tmp_path)
            if problems:
                for problem in problems:
                    print("illustration replace rejected for %r: %s" % (key, problem))
                return self.redirect(
                    "/airlines?flash=%s" % quote(FLASH_KEY_ILLUSTRATION_REJECTED))

            with Image.open(raw_tmp_path) as img:
                rgba = img.convert("RGBA")
                rgba.save(encoded_tmp_path, format="PNG")

            override_path = illustrations.override_path_for_key(key, state_dir)
            os.replace(encoded_tmp_path, override_path)
            return self.redirect(
                "/airlines?flash=%s" % quote(FLASH_KEY_ILLUSTRATION_REPLACED))
        except Exception:
            return self.redirect(
                "/airlines?flash=%s" % quote(FLASH_KEY_ILLUSTRATION_REPLACE_FAILED))
        finally:
            for tmp_path in (raw_tmp_path, encoded_tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def _handle_manual_resolve_post(self):
        """POST /airlines/resolve — Step A of the two-step resolve flow.
        `prefix` is re-validated against the live unresolved-callsign
        registry, never trusted from the hidden form field; a stale
        prefix writes nothing. The illustration key on success is
        recomputed server-side from the just-persisted name, never from
        the form value. No CSRF token: relies on SameSite=Strict, like
        every other state-changing route.
        """
        form = self.read_form()
        state_dir = self.args.state_dir

        row = unresolved_row_for_prefix(state_dir, form.get("prefix"))
        if row is None:
            return self.redirect(
                "%s?flash=%s"
                % (airlines_page.AIRLINES_ROUTE, quote(FLASH_KEY_MANUAL_PREFIX_STALE)))
        prefix = row[0]

        result = manual_resolutions.add_entry(state_dir, prefix, form.get("airline_name"))

        if result == manual_resolutions.ADD_OK:
            registry = manual_resolutions.load_manual_resolutions(state_dir)
            entry = registry.get(prefix) or {}
            key = manual_resolutions.illustration_key_for_name(entry.get("airline_name"))
            if key and illustrations.resolved_illustration_path(key, state_dir) is not None:
                return self.redirect(
                    "%s?flash=%s"
                    % (airlines_page.AIRLINES_ROUTE, quote(FLASH_KEY_MANUAL_RESOLVED)))
            return self.redirect(
                "%s?resolve=%s&flash=%s"
                % (airlines_page.AIRLINES_ROUTE, quote(prefix, safe=""),
                   quote(FLASH_KEY_MANUAL_RESOLVED)))

        if result == manual_resolutions.ADD_REJECTED_PREFIX:
            flash_key = FLASH_KEY_MANUAL_NAME_EMPTY
        elif result == manual_resolutions.ADD_REJECTED_NAME_EMPTY:
            # add_entry() collapses "empty" and "supplied but unusable"
            # onto one result code; distinguish them here by re-reading
            # the same raw posted value, never re-deriving the regex.
            raw_name = form.get("airline_name")
            if isinstance(raw_name, str) and raw_name.strip():
                flash_key = FLASH_KEY_MANUAL_NAME_UNUSABLE
            else:
                flash_key = FLASH_KEY_MANUAL_NAME_EMPTY
        elif result == manual_resolutions.ADD_REJECTED_NAME_TOO_LONG:
            flash_key = FLASH_KEY_MANUAL_NAME_TOO_LONG
        elif result == manual_resolutions.ADD_REJECTED_NAME_RESERVED:
            flash_key = FLASH_KEY_MANUAL_NAME_RESERVED
        elif result == manual_resolutions.ADD_REJECTED_FULL:
            flash_key = FLASH_KEY_MANUAL_REGISTRY_FULL
        elif result == manual_resolutions.ADD_FAILED:
            flash_key = FLASH_KEY_MANUAL_SAVE_FAILED
        else:
            # An unrecognised result must still speak, never fall through
            # to no flash at all.
            flash_key = FLASH_KEY_MANUAL_SAVE_FAILED
        return self.redirect(
            "%s?resolve=%s&flash=%s"
            % (airlines_page.AIRLINES_ROUTE, quote(prefix, safe=""), quote(flash_key)))

    def _handle_manual_resolution_delete(self, key):
        """POST /airlines/manual-resolutions/{prefix}/delete. `key` is
        normalised and used only as a dict key into
        `manual_resolutions.json`, never joined into a filesystem path.
        Deleting an already-absent prefix is success, not an error
        (idempotent double-submission tolerance); only a genuine write
        failure gets a failure flash.
        """
        prefix = manual_resolutions.normalise_prefix(key)
        if prefix is None:
            return self.send_html(404, self._not_found_page())

        state_dir = self.args.state_dir
        existed = prefix in manual_resolutions.load_manual_resolutions(state_dir)
        deleted = manual_resolutions.delete_entry(state_dir, prefix)
        if not deleted and existed:
            return self.redirect(
                "%s?flash=%s"
                % (airlines_page.AIRLINES_ROUTE, quote(FLASH_KEY_MANUAL_DELETE_FAILED)))
        return self.redirect(airlines_page.AIRLINES_ROUTE)

    def _handle_rule_add_post(self):
        """POST /settings/rules/add: the colour-rules editor's immediate
        add route, an action outside SETTINGS_ROUTE. `colour_rules.add_rule()`
        is the single validation authority; this handler validates
        nothing itself and maps every result to a flash key with an
        explicit branch, so an unrecognised result can never fall
        through silently. No CSRF token, like every state-changing route.
        """
        form = self.read_form()
        state_dir = self.args.state_dir

        submitted_kind = form.get("rule_kind")
        submitted_key = form.get("rule_key")
        submitted_theme_id = form.get("rule_theme_id")

        result = colour_rules.add_rule(
            state_dir, submitted_kind, submitted_key, submitted_theme_id)

        if result == colour_rules.ADD_OK_NEW:
            return self.redirect(
                "%s?flash=%s" % (DISPLAY_ROUTE, quote(FLASH_KEY_RULE_ADDED)))
        if result == colour_rules.ADD_OK_REPLACED:
            # Both segments are already known-valid at this point (that is
            # exactly why add_rule() returned ADD_OK_REPLACED rather than
            # a rejection) — re-derived here, never trusted from the raw
            # form value (validate-then-echo).
            normalised_kind = colour_rules.normalise_rule_kind(submitted_kind)
            normalised_value = colour_rules.normalise_rule_value(
                normalised_kind, submitted_key)
            return self.redirect(
                "%s?flash=%s&rule=%s"
                % (DISPLAY_ROUTE, quote(FLASH_KEY_RULE_REPLACED),
                   quote(normalised_value, safe="")))
        if result == colour_rules.ADD_REJECTED_KEY:
            flash_key = FLASH_KEY_RULE_KEY_INVALID
        elif result == colour_rules.ADD_REJECTED_FULL:
            flash_key = FLASH_KEY_RULE_REGISTRY_FULL
        else:
            # ADD_REJECTED_KIND, ADD_REJECTED_THEME, ADD_FAILED, and any
            # unrecognised result all reuse the generic save-failed key —
            # a result must never fall through to no flash at all.
            flash_key = FLASH_KEY_RULE_SAVE_FAILED
        return self.redirect("%s?flash=%s" % (DISPLAY_ROUTE, quote(flash_key)))

    def _handle_rule_delete(self, kind, value):
        """POST /settings/rules/{kind}/{value}/delete. `kind` and
        `value` are re-normalised before any registry lookup — an
        unrecognised kind or malformed value 404s without touching the
        registry. Deleting an already-absent pair is success, not an
        error (idempotent double-submission tolerance).
        """
        normalised_kind = colour_rules.normalise_rule_kind(kind)
        if normalised_kind is None:
            return self.send_html(404, self._not_found_page())
        normalised_value = colour_rules.normalise_rule_value(normalised_kind, value)
        if normalised_value is None:
            return self.send_html(404, self._not_found_page())

        state_dir = self.args.state_dir
        registry = colour_rules.load_colour_rules(state_dir)
        existed = normalised_value in registry.get(normalised_kind, {})
        deleted = colour_rules.delete_rule(state_dir, normalised_kind, normalised_value)
        if deleted:
            return self.redirect(
                "%s?flash=%s" % (DISPLAY_ROUTE, quote(FLASH_KEY_RULE_DELETED)))
        if existed:
            return self.redirect(
                "%s?flash=%s" % (DISPLAY_ROUTE, quote(FLASH_KEY_RULE_DELETE_FAILED)))
        return self.redirect(DISPLAY_ROUTE)

    def _handle_calendar_disconnect_post(self):
        """POST /settings/calendar/disconnect. Two-step confirmation,
        server-side: a bare or non-matching confirm value renders the
        confirm page at 200 without touching anything — the client-side
        `confirm()` dialog is a misclick guard only, never the security
        control. Only an exact confirm match proceeds to clear the URL.
        """
        form = self.read_form()
        confirm = form.get(config_page.CALENDAR_DISCONNECT_CONFIRM_FIELD)
        if confirm != config_page.CALENDAR_DISCONNECT_CONFIRM_VALUE:
            ctx = self.page_context()
            body = config_page.calendar_disconnect_confirm_page(ctx)
            return self.send_html(200, self._page_shell_for(DISPLAY_ROUTE, body, ctx))
        state_dir = self.args.state_dir
        if calendar_rules.save_calendar_url(
                state_dir, calendar_rules.CLEAR_CALENDAR_URL):
            return self.redirect(
                "%s?flash=%s" % (DISPLAY_ROUTE, quote(FLASH_KEY_CALENDAR_DISCONNECTED)))
        return self.redirect(
            "%s?flash=%s" % (DISPLAY_ROUTE, quote(FLASH_KEY_CALENDAR_SYNC_FAILED)))

    def _handle_calendar_connect_post(self):
        """POST /settings/calendar/connect: the Calendar card's own
        dedicated route — never the scoped settings handler, since a
        scoped POST carrying only `calendar_url` would read every
        absent checkbox on Display as an explicit OFF. Writes the URL,
        then syncs under `_POLL_LOCK` (process-local; see
        `_handle_settings_post()` for the cross-process lock).
        """
        form = self.read_form()
        signal = config_page.submitted_calendar_signal(form)
        if signal in (
                config_page.CALENDAR_URL_SIGNAL_CARRY_FORWARD,
                config_page.CALENDAR_URL_SIGNAL_INVALID,
                config_page.CALENDAR_URL_SIGNAL_CLEAR):
            return self.redirect(
                "%s?flash=%s" % (DISPLAY_ROUTE, quote(FLASH_KEY_CALENDAR_CONNECT_INVALID)))
        state_dir = self.args.state_dir
        stripped_url = (form.get("calendar_url") or "").strip()
        if not calendar_rules.save_calendar_url(state_dir, stripped_url):
            return self.redirect(
                "%s?flash=%s" % (DISPLAY_ROUTE, quote(FLASH_KEY_CALENDAR_SYNC_FAILED)))
        if not _POLL_LOCK.acquire(blocking=False):
            return self.redirect(
                "%s?flash=%s" % (DISPLAY_ROUTE, quote(FLASH_KEY_CALENDAR_SYNC_DEFERRED)))
        try:
            result_code, _registry = calendar_rules.refresh_calendar_registry(
                state_dir, poll_loop.now_s(), min_interval_s=0)
        finally:
            _POLL_LOCK.release()
        if result_code == calendar_rules.FETCH_OK:
            return self.redirect(
                "%s?flash=%s" % (DISPLAY_ROUTE, quote(FLASH_KEY_CALENDAR_CONNECT_OK)))
        return self.redirect(
            "%s?flash=%s" % (DISPLAY_ROUTE, quote(FLASH_KEY_CALENDAR_SYNC_FAILED)))

    def _handle_notifications_test_post(self):
        """POST /settings/notifications/test. SSRF-by-proxy guard: the
        topic URL is read from the stored device config, never from the
        submitted form body — accepting a client-supplied URL here would
        turn this button into an open request-forwarder.
        """
        state_dir = self.args.state_dir
        stored_notifications = device_config.load_device_config(state_dir)["notifications"]
        topic_url = stored_notifications.get("topic_url")
        if not topic_url:
            return self.redirect(
                "%s?flash=%s" % (DEVICE_ROUTE, quote(FLASH_KEY_NOTIFICATIONS_TEST_FAILED)))
        lang = stored_notifications.get("lang") or "en"
        sent = notify.send_notification(
            topic_url,
            notify.body_for_lang(notify.TEST_NOTIFICATION_TITLE, lang),
            notify.body_for_lang(notify.TEST_NOTIFICATION_BODY, lang))
        if sent:
            return self.redirect(
                "%s?flash=%s" % (DEVICE_ROUTE, quote(FLASH_KEY_NOTIFICATIONS_TEST_OK)))
        return self.redirect(
            "%s?flash=%s" % (DEVICE_ROUTE, quote(FLASH_KEY_NOTIFICATIONS_TEST_FAILED)))

    def _referring_tab(self):
        referer = self.headers.get("Referer", "")
        try:
            path = urlsplit(referer).path
        except ValueError:
            path = ""
        allowed = {route for route, _ in layout.NAV_TABS}
        return path if path in allowed else HOME_ROUTE

    def _page_shell_for(self, route, body, ctx):
        """The `layout.page_shell()` assembly both `_render_tab()`
        (every GET) and `_handle_settings_post()`'s rejected-save branch
        (a POST that already has its own rendered `body`) need, so
        there is one `page_shell()` call site for both.
        """
        flash_html = (
            layout.flash_banner(ctx["flash"], role=ctx["flash_role"])
            if ctx["flash"] else None)
        return layout.page_shell(
            title=i18n.t(_PAGE_TITLES[route]), active=layout.nav_slug(route),
            body=body,
            ui_theme=ctx["ui_theme"], flash=flash_html,
            health_alert=ctx["health_severity"], device_config=ctx["device_config"])

    def _render_tab(self, route, render):
        """Render one authenticated tab: `render(ctx) -> body markup`
        (a page module's render(), or a lambda binding a scope onto
        config_page.render()) wrapped in layout.page_shell(), so the six
        live routes share one body instead of six copies of it.
        """
        if not self.require_session():
            return None
        ctx = self.page_context()
        body = render(ctx)
        return self.send_html(200, self._page_shell_for(route, body, ctx))

    # --- GET -------------------------------------------------------------

    def do_GET(self):
        parsed = urlsplit(self.path)
        path = parsed.path

        if path == LOGIN_ROUTE:
            if self._is_authenticated():
                return self.redirect(HOME_ROUTE)
            # A `?next=` query value survives the require_session()
            # redirect round-trip; validated here too (not only on the
            # POST path) so an unrecognised value never even renders a
            # hidden field for the user to resubmit.
            next_route = _validated_next_route(
                parse_qs(parsed.query).get("next", [None])[0])
            return self.send_html(200, self._render_login_page(next_route=next_route))

        if path == STYLE_ROUTE:
            return self._serve_stylesheet()

        # Pre-auth, matching /static/style.css: a static asset carries no
        # per-user or sensitive data, so gating it would add a session
        # round-trip for zero benefit. Every other *_SCRIPT_ROUTE branch
        # below shares this same reasoning.
        if path == SCRIPT_ROUTE:
            return self._serve_battery_trend_script()

        if path == NAV_SCRIPT_ROUTE:
            return self._serve_nav_dropdown_script()

        if path == DIRTY_STATE_SCRIPT_ROUTE:
            return self._serve_dirty_state_script()

        if path == LIST_FILTER_SCRIPT_ROUTE:
            return self._serve_list_filter_script()

        if path == COPY_BUTTON_SCRIPT_ROUTE:
            return self._serve_copy_button_script()

        if path == FRESHNESS_SCRIPT_ROUTE:
            return self._serve_freshness_script()

        if path == PANEL_LOOKUP_SCRIPT_ROUTE:
            return self._serve_panel_lookup_script()

        if path == FLASH_CLEANUP_SCRIPT_ROUTE:
            return self._serve_flash_cleanup_script()

        if path == POLL_COOLDOWN_SCRIPT_ROUTE:
            return self._serve_poll_cooldown_script()

        if path == CONFIRM_SUBMIT_SCRIPT_ROUTE:
            return self._serve_confirm_submit_script()

        if path == THEME_PREVIEW_SCRIPT_ROUTE:
            return self._serve_theme_preview_script()

        if path == FLIGHT_ROWS_SCRIPT_ROUTE:
            return self._serve_flight_rows_script()

        if path == LOGIN_CARD_SCRIPT_ROUTE:
            return self._serve_login_card_script()

        if path == SUBMIT_GUARD_SCRIPT_ROUTE:
            return self._serve_submit_guard_script()

        if path == RELATIVE_TIME_SCRIPT_ROUTE:
            return self._serve_relative_time_script()

        if path == QUICK_SWITCH_SCRIPT_ROUTE:
            return self._serve_quick_switch_script()

        if path == VALUE_CONTROLS_SCRIPT_ROUTE:
            return self._serve_value_controls_script()

        # The six live tabs, each through _render_tab() above.
        if path == HOME_ROUTE:
            return self._render_tab(HOME_ROUTE, home_page.render)

        if path == DISPLAY_ROUTE:
            return self._render_tab(
                DISPLAY_ROUTE,
                lambda ctx: config_page.render(ctx, scope=config_page.SCOPE_DISPLAY))

        if path == DEVICE_ROUTE:
            return self._render_tab(
                DEVICE_ROUTE,
                lambda ctx: config_page.render(ctx, scope=config_page.SCOPE_DEVICE))

        if path == FLIGHTS_ROUTE:
            return self._render_tab(FLIGHTS_ROUTE, history_page.render)

        if path == HEALTH_ROUTE:
            return self._render_tab(HEALTH_ROUTE, health_page.render)

        if path == AIRLINES_ROUTE:
            return self._render_tab(AIRLINES_ROUTE, airlines_page.render)

        # The pre-refactor page routes survive as fixed 303s so a stale
        # bookmark or link still lands somewhere useful. The targets are
        # literals, never derived from any request value.
        if path == SETTINGS_ROUTE:
            if not self.require_session():
                return None
            return self.redirect(DISPLAY_ROUTE)

        if path == HISTORY_LEGACY_ROUTE:
            if not self.require_session():
                return None
            return self.redirect(FLIGHTS_ROUTE)

        if path == PREVIEW_PAGE_ROUTE:
            if not self.require_session():
                return None
            # The Preview page is retired — History (now Flights)
            # absorbed all of its content — so this route exists solely
            # to send a stale bookmark/link somewhere useful. Fixed
            # literal target, never a request value.
            return self.redirect(FLIGHTS_ROUTE)

        if path.startswith(GALLERY_ROUTE_PREFIX):
            if not self.require_session():
                return None
            return self._serve_gallery_image(path[len(GALLERY_ROUTE_PREFIX):])

        if path.startswith(RUNWAY_IMAGE_ROUTE_PREFIX) and path.endswith(".png"):
            if not self.require_session():
                return None
            runway_id = path[len(RUNWAY_IMAGE_ROUTE_PREFIX):-len(".png")]
            return self._serve_runway_image(runway_id)

        if path.startswith(ILLUSTRATION_IMAGE_ROUTE_PREFIX) and path.endswith(".png"):
            if not self.require_session():
                return None
            key = path[len(ILLUSTRATION_IMAGE_ROUTE_PREFIX):-len(".png")]
            return self._serve_illustration_image(key)

        if path.startswith(THEME_PREVIEW_ROUTE_PREFIX) and path.endswith(".png"):
            if not self.require_session():
                return None
            theme_id = path[len(THEME_PREVIEW_ROUTE_PREFIX):-len(".png")]
            return self._serve_theme_preview_image(theme_id)

        return self.send_html(404, self._not_found_page())

    # --- POST --------------------------------------------------------------

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
            # Translated here, at the literal call site — see
            # _login_body()'s own docstring for why (`error` is an
            # opaque parameter by the time it reaches that function,
            # invisible to the ast-based scanner that traces i18n.t()
            # call arguments).
            error=i18n.t("Incorrect password. Try again."), next_route=next_route))

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
                state_dir, poll_loop.now_s(), min_interval_s=0)
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
                    poll_loop.run_once(
                        state_dir=state_dir, geofence=self.args.geofence)
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

    def _handle_theme_post(self):
        form = self.read_form()
        submitted = form.get("ui_theme")
        cookie_header = None
        if submitted in layout.UI_THEME_CHOICES:
            # Routed through auth.secure_cookie_flag() so this cookie
            # and the session cookie cannot drift on the Secure flag.
            cookie_header = (
                "%s=%s; HttpOnly%s; SameSite=Strict; Path=/; Max-Age=%d"
                % (auth.UI_THEME_COOKIE_NAME, submitted, auth.secure_cookie_flag(),
                   THEME_COOKIE_MAX_AGE_S))
        return self.redirect(self._referring_tab(), set_cookie=cookie_header)

    def _handle_lang_post(self):
        """POST /ui-lang — byte-for-byte sibling of _handle_theme_post()
        above. An unrecognised value sets no cookie and still redirects,
        exactly like the theme route already behaves.
        """
        form = self.read_form()
        submitted = form.get("ui_lang")
        cookie_header = None
        if submitted in prefs.LANG_CHOICES:
            cookie_header = (
                "%s=%s; HttpOnly%s; SameSite=Strict; Path=/; Max-Age=%d"
                % (auth.UI_LANG_COOKIE_NAME, submitted, auth.secure_cookie_flag(),
                   LANG_COOKIE_MAX_AGE_S))
        return self.redirect(self._referring_tab(), set_cookie=cookie_header)

    # Runs as the first statement, before urlsplit()/routing, so it covers
    # every route uniformly including ones added later. Defence in depth
    # on top of SameSite=Strict (see auth.post_origin_ok()'s docstring).
    def do_POST(self):
        if not auth.post_origin_ok(self.headers):
            return self.send_html(403, self._forbidden_page())

        parsed = urlsplit(self.path)
        path = parsed.path

        if path == LOGIN_ROUTE:
            return self._handle_login_post()

        if path == SETTINGS_ROUTE:
            if not self.require_session():
                return None
            return self._handle_settings_post()

        if path == POLL_ROUTE:
            if not self.require_session():
                return None
            return self._handle_poll_now()

        if path == QUICK_DISPLAY_ROUTE:
            if not self.require_session():
                return None
            return self._handle_quick_toggle("display_enabled")

        if path == QUICK_QUIET_HOURS_ROUTE:
            if not self.require_session():
                return None
            return self._handle_quick_toggle("quiet_hours_enabled")

        # Session-checked POST only, no CSRF token — SameSite=Strict is
        # the only control here, so this must never be reachable by GET.
        # return_to whitelist: /device is the LED switch's only page, so
        # it is both the sole allowed value and the fallback.
        if path == QUICK_LED_ROUTE:
            if not self.require_session():
                return None
            return self._handle_quick_toggle(
                "led_enabled",
                allowed_return_to=(layout.DEVICE_ROUTE,),
                fallback_return_to=layout.DEVICE_ROUTE)

        # Gated like every other state-changing route above — an
        # unauthenticated caller setting another visitor's UI theme
        # cookie is a real state change, not a cosmetic no-op.
        if path == THEME_ROUTE:
            if not self.require_session():
                return None
            return self._handle_theme_post()

        # Gated identically to THEME_ROUTE above — neither route may be
        # reachable without a session.
        if path == LANG_ROUTE:
            if not self.require_session():
                return None
            return self._handle_lang_post()

        # Gated too: an unauthenticated POST is a CSRF-shaped forced
        # sign-out. Revokes the token server-side before clearing the
        # cookie, so replaying the old cookie value stops verifying.
        if path == LOGOUT_ROUTE:
            if not self.require_session():
                return None
            token = auth.parse_cookies(
                self.headers.get("Cookie")).get(auth.SESSION_COOKIE_NAME)
            if token:
                auth.revoke(token)
            return self.redirect(LOGIN_ROUTE, set_cookie=auth.logout_set_cookie_header())

        # Step A of the two-step resolve flow — the session gate runs
        # first, before any registry read or write, matching every other
        # authenticated branch here.
        if path == airlines_page.RESOLVE_ROUTE:
            if not self.require_session():
                return None
            return self._handle_manual_resolve_post()

        # Mirrors the illustration-prefix branch's own slice-arithmetic
        # shape below, but with a prefix and a suffix (the prefix
        # segment is a dict key, not a filename).
        if path.startswith(airlines_page.MANUAL_DELETE_ROUTE_PREFIX) and path.endswith(
                airlines_page.MANUAL_DELETE_ROUTE_SUFFIX):
            if not self.require_session():
                return None
            key = path[
                len(airlines_page.MANUAL_DELETE_ROUTE_PREFIX):
                -len(airlines_page.MANUAL_DELETE_ROUTE_SUFFIX)]
            return self._handle_manual_resolution_delete(key)

        # Mirrors the GET dispatch's own ILLUSTRATION_IMAGE_ROUTE_PREFIX
        # branch above byte for byte — same prefix constant, same ".png"
        # suffix test, same require_session() gate first, same slice
        # arithmetic.
        if path.startswith(ILLUSTRATION_IMAGE_ROUTE_PREFIX) and path.endswith(".png"):
            if not self.require_session():
                return None
            key = path[len(ILLUSTRATION_IMAGE_ROUTE_PREFIX):-len(".png")]
            return self._handle_illustration_replace(key)

        # The rules editor's two immediate POST routes, behind the same
        # require_session() gate as every other state-changing route
        # above — no new auth mechanism and no CSRF token, inheriting the
        # site-wide session gate and the SameSite=Strict cookie control
        # uniformly applied here.
        if path == RULES_ADD_ROUTE:
            if not self.require_session():
                return None
            return self._handle_rule_add_post()

        # The calendar disconnect action's own dedicated route, gated
        # identically to every other state-changing route above.
        if path == CALENDAR_DISCONNECT_ROUTE:
            if not self.require_session():
                return None
            return self._handle_calendar_disconnect_post()

        if path == CALENDAR_CONNECT_ROUTE:
            if not self.require_session():
                return None
            return self._handle_calendar_connect_post()

        if path == NOTIFICATIONS_TEST_ROUTE:
            if not self.require_session():
                return None
            return self._handle_notifications_test_post()

        # Mirrors the manual-resolution delete branch's own startswith/
        # endswith shape above, with the one extra step this route's
        # two-segment path needs: split the recovered middle on a slash
        # ONCE to recover the kind and the value. A middle that does not
        # split into exactly two non-empty segments is a 404.
        if path.startswith(RULES_DELETE_ROUTE_PREFIX) and path.endswith(
                RULES_DELETE_ROUTE_SUFFIX):
            if not self.require_session():
                return None
            middle = path[
                len(RULES_DELETE_ROUTE_PREFIX):-len(RULES_DELETE_ROUTE_SUFFIX)]
            segments = middle.split("/", 1)
            if len(segments) != 2 or not segments[0] or not segments[1]:
                return self.send_html(404, self._not_found_page())
            return self._handle_rule_delete(segments[0], segments[1])

        return self.send_html(404, self._not_found_page())

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
        default=poll_loop.DEFAULT_STATE_DIR,
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
    # every server.poll_loop print a POST /poll-now trigger emits if the
    # service is ever killed before the buffer next flushes.
    sys.stdout.reconfigure(line_buffering=True)

    Handler.args = args
    server = ThreadingHTTPServer((args.bind, args.port), Handler)
    print("companion: serving on %s:%d (state_dir=%s)" % (
        args.bind, args.port, args.state_dir))
    server.serve_forever()


if __name__ == "__main__":
    main()
