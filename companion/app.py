#!/usr/bin/env python3
"""SkyPane companion service: a stdlib `ThreadingHTTPServer` with a
hand-rolled route table, run as its own systemd unit, separate from the
vendored device-protocol server in `stub-server/`.

Every route except the login routes and the stylesheet calls
`Handler.require_session()` as its first statement and returns immediately
when the session is invalid — this file is the single place that gate is
enforced, not each page module. The same exemption list also controls the
caching scope on byte-served responses (`Handler.send_bytes()`'s `public`
parameter): a route not in this list must never be advertised to a shared
cache as storable.

Binds `--bind` (default `0.0.0.0`); production passes `--bind 127.0.0.1`
because Caddy is the only intended client and this process itself makes
outbound calls (poll trigger, calendar fetch, ntfy) — a systemd IP filter
cannot express "outbound anywhere, inbound loopback only", which is why
`stub-server/byos_server.py` (no outbound calls) uses that filter instead.

Never writes the poll pipeline's own persisted flight-state file —
`server.poll_loop.run_once()` is that file's one legitimate writer.
`POST /poll-now` calls `run_once()` directly, in-process: the same
production code path the systemd timer already runs on its own cadence.

`main()` calls `companion.auth.configured_password()` before binding the
socket. A missing password fails closed — this service must never come up
with authentication silently disabled.
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
# `server.device_config`/`server.history_db`/`server.poll_loop` all
# resolve whether this file is imported as a package or executed
# directly (`server/.venv/bin/python3 companion/app.py`, the exact
# invocation the systemd unit uses).
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
# Comfortably above any real high-resolution transparent aircraft PNG —
# every vendored asset in server/assets/icons/illustrations/ is well under
# this — while bounding a single request's peak memory to a few MB on a
# CX22-class VPS. Enforcing this size is the caller's job
# (Handler._read_upload_body()), not parse_single_uploaded_file()'s own.
MAX_ILLUSTRATION_UPLOAD_BYTES = 4 * 1024 * 1024
# Bounds how long a single connection's socket reads (including the
# unauthenticated POST /login body read in read_form()) may block on a
# slow/stalled client. Without this, a client that opens a connection with
# a plausible Content-Length and then trickles (or never sends) the body
# ties up a ThreadingHTTPServer worker thread indefinitely — a slowloris-
# shaped DoS reachable before any credential check. 30s comfortably covers
# a slow real client on this LAN/VPN deployment while bounding the worst case.
REQUEST_SOCKET_TIMEOUT_S = 30

# The Content-Security-Policy sent on every response (see
# _send_hardening_headers() below).
#   script-src 'self'  — deliberately no 'unsafe-inline' and no nonce;
#     this is where the real XSS risk lives, and the app has no inline
#     <script> elements.
#   style-src 'self' 'unsafe-inline'  — solely for the seven
#     style="background:..." theme-swatch attributes in
#     companion/pages/config_page.py's _theme_chip_grid_html() and its
#     single-theme/calendar-section siblings. Every one of those values
#     comes from the fixed 18-member server/device_config.py THEMES
#     registry and is never user input, so this allowance carries no
#     injection path.
#   img-src 'self' data:  — the `data:` value is needed for the inline
#     favicon/icon data URI companion/layout.py already emits.
#   form-action 'self'  — every <form> on the site posts back to this
#     same origin; complements the existing SameSite=Strict session
#     cookie against cross-origin form posting.
#   frame-ancestors 'none'  — the modern companion to the existing
#     X-Frame-Options: DENY below, which is kept for older browsers.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; img-src 'self' data:; "
    "style-src 'self' 'unsafe-inline'; script-src 'self'; "
    "form-action 'self'; frame-ancestors 'none'"
)
# The same environment variable deploy/skypane-byos.service passes to
# byos_server.py as --sleep. It reaches this process because
# deploy/skypane-companion.service declares the identical
# EnvironmentFile=/opt/skypane/skypane.env directive. Deliberately not
# imported from companion/auth.py: that module owns the password
# variable's name, not this one, and the two have unrelated lifecycles.
SLEEP_ENV_VAR = "SKYPANE_SLEEP_S"

LOGIN_ROUTE = "/login"
STYLE_ROUTE = "/static/style.css"
# Each *_SCRIPT_ROUTE below is the authoritative route value: the
# matching companion/layout.py (or health_page.py) *_SCRIPT_SRC constant
# must equal it exactly, and a test asserts the two stay in sync. Most
# are pre-auth (served before a session exists) by design — either they
# carry no session data and no-op via their own guard clause, or
# (login-card.js) the only page that loads them is the login page itself.
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
# CONTENT NEGOTIATION, not a second route shape. A /quick/* route
# answers exactly what it answers today for a form post — a 303 with a
# flash — and answers a request that identifies itself as a fetch with a
# 204 and no body. The header is the convention companion/static/
# freshness.js already sends; a browser form post never sends it, so
# the no-JS redirect is byte-identical to a plain form post.
# Only the VALUE is a constant here. The header NAME is written at its
# one use site below, because no HTTP header name in this module is a
# module-level constant and a lone exception would be the drift, not
# the convention.
QUICK_FETCH_HEADER_VALUE = "quick-switch"
THEME_ROUTE = "/ui-theme"
LANG_ROUTE = "/ui-lang"
LOGOUT_ROUTE = "/logout"
# The standalone Preview HTML page is retired — its content moved into
# History — so this route is kept solely as a fixed-redirect source, not
# a page route. Named PREVIEW_PAGE_ROUTE (not PREVIEW_ROUTE) to say what
# it now is.
PREVIEW_PAGE_ROUTE = "/preview"
GALLERY_ROUTE_PREFIX = "/gallery/"
# Single definition site is companion/pages/config_page.py (app.py imports
# that module, so the reverse import would be a cycle) — rebound here
# exactly like the FLASH_KEY_* constants below.
RUNWAY_IMAGE_ROUTE_PREFIX = config_page.RUNWAY_IMAGE_ROUTE_PREFIX
# The Airlines gallery's per-variant illustration image route. Naming
# convention matches RUNWAY_IMAGE_ROUTE_PREFIX above.
ILLUSTRATION_IMAGE_ROUTE_PREFIX = "/illustration/"
# Single definition site is companion/theme_preview.py, NOT a page
# module — deliberately the opposite of RUNWAY_IMAGE_ROUTE_PREFIX/
# ILLUSTRATION_IMAGE_ROUTE_PREFIX's precedent of living with the emitter.
# Here the render/cache mechanism owns the prefix since it is also
# rebound a second time, from
# companion/pages/config_page.py, for the Settings theme picker's own
# markup — see theme_preview.py's module docstring for the full reasoning.
THEME_PREVIEW_ROUTE_PREFIX = theme_preview.THEME_PREVIEW_ROUTE_PREFIX
# Single definition site is companion/pages/config_page.py (app.py
# imports that module, so the reverse import would be a cycle) — rebound
# here exactly like RUNWAY_IMAGE_ROUTE_PREFIX/SETTINGS_ROUTE above. Same
# for the CALENDAR_*/NOTIFICATIONS_TEST_ROUTE constants below.
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
    # "{n}"/"{s}" are filled by _resolve_flash_text()'s third special
    # case below, from a fresh on-disk read of the registry's entry
    # count at render time — never carried through the redirect's query
    # string. States what the count means in checkable terms (flights
    # from this calendar inside the frame's window) without implying the
    # frame watches for them or will announce them.
    FLASH_KEY_CALENDAR_CONNECTED: (
        "Connected — {n} flight{s} from this calendar in the frame's "
        "current window."),
    # The single honest generic failure message: honestly states the
    # frame retries on its own schedule regardless — the URL was saved
    # whether or not this one fetch succeeded. Never echoes anything the
    # operator submitted, and no exception text is ever read to build
    # this string.
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

# Process-global, not per-session: there are no distinct users for a
# per-session counter to key on. Keyed per client IP and bounded
# (auth.LoginThrottle/auth.login_throttle_key()): failed logins from one
# address never lock another, and the bucket table cannot grow without
# limit under a spray of source addresses.
LOGIN_THROTTLE = auth.LoginThrottle()

# Same process-global-singleton shape as LOGIN_THROTTLE above: a single,
# module-level `threading.Lock()` guarding the entire
# check-cooldown -> run_once() -> mark-triggered sequence in
# _handle_poll_now(), so two POST /poll-now requests arriving before the
# first has finished can never both call poll_loop.run_once(). Correct
# because main() runs exactly one ThreadingHTTPServer in a single OS
# process (no worker/replica config anywhere in
# deploy/skypane-companion.service) — a cross-process or file-based lock
# would be the wrong tool here.
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

# The login card's lockout sentence, a module constant beside
# LOGIN_EXPLANATION_TEXT above because _login_body() and the live
# countdown's own template must both be built from this one string
# rather than from two literals that could drift.
LOGIN_LOCKOUT_TEXT = "Too many attempts — try again in %ds."

# The substitution token the live countdown swaps for the current
# remaining figure each second, mirroring companion/pages/config_page.py's
# own POLL_COOLDOWN_TEMPLATE_TOKEN exactly. The template is built by
# replacing "%d" in the already-translated sentence rather than by hand,
# because the French catalogue entry puts a space before the unit
# ("dans %d s.") and rebuilding that on the JS side would silently drop it.
#
# The value is POLL_COOLDOWN_TEMPLATE_TOKEN's own, byte for byte, and
# that is load-bearing: companion/test_i18n.py scans every uppercase
# module constant in this file and demands a French catalogue entry for
# it, excluding only values that are plainly not prose. "__N__" is
# excluded as an uppercase code; a lowercase placeholder would not be,
# and would have to be either translated (meaningless) or exempted.
LOGIN_LOCKOUT_TEMPLATE_TOKEN = "__N__"

# The id the login card's one message element carries (the wrong-password
# error and the lockout sentence share it), and the id
# `aria-describedby` points at when, and only when, that message is
# rendered. One constant, so the attribute and its target can never
# drift apart.
LOGIN_MESSAGE_ID = "login-error"

# The show-password toggle's two accessible names. Both are rendered on
# every login page as server-escaped data-* attributes and swapped by
# companion/static/login-card.js, so that file hard-codes no English of
# its own.
LOGIN_REVEAL_SHOW_LABEL = "Show password"
LOGIN_REVEAL_HIDE_LABEL = "Hide password"

# The toggle's two glyphs: a filled circle while the value is masked, a
# hollow one while it is revealed. Not translated and never translatable
# — they are marks, not words, which is why they sit outside the
# LOGIN_REVEAL_*_LABEL pair above and inside an aria-hidden span. They
# exist so the control's own state is legible without relying on colour
# (the pressed wash) alone.
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
    """Validate a caller-supplied `next` redirect target (a GET query
    value or a POST form value) against `layout.NAV_TABS`'s known routes.

    Open-redirect mitigation: an exact-membership equality test against
    the NAV_TABS route literals — never `str.startswith("/")`, never
    URL-parsed, never regex-matched, so there is no parsing logic an
    attacker-controlled value could exploit. Anything not byte-identical
    to a real route is discarded (`None`) and the caller falls back to
    its own safe default. Mirrors `Handler._referring_tab()`'s own
    allowlist shape, but is module-level since it must validate both a
    query-string value (GET) and a form value (POST).
    """
    allowed = {route for route, _ in layout.NAV_TABS}
    return candidate if candidate in allowed else None


def _resolve_flash_text(
        flash_key, state_dir, rule_key=None, last_checkin_ts=None, device_cfg=None,
        battery_critical=False):
    """Build this flash's already-translated message text, or None if
    flash_key is unknown.

    rule_key: re-normalised through colour_rules.normalise_rule_callsign()
    before it is ever interpolated — never trusted from the request
    unvalidated. A value that fails this check degrades to the generic
    FLASH_KEY_RULE_ADDED copy rather than ever reaching the page
    unvalidated; escape_html() on render is the second line.
    last_checkin_ts/device_cfg: feed the one computed delay sentence
    FLASH_KEY_SAVED needs, via the same wake.next_wake_status() triple
    the Frame strip and Quiet hours caption both read, so the three can
    never disagree about when a save reaches the frame.
    battery_critical: page_context()'s own single per-request
    wake.read_battery_critical(state_dir) read, passed straight through
    rather than reading poll_state.json a second time per request.
    """
    if flash_key not in FLASH_MESSAGES:
        return None
    # Translate the template first, then fill any "{n}"/"{s}"/"{key}"/"%s"
    # placeholder afterwards, never the other way round, so the French
    # template controls where the interpolated value lands. Written as
    # one expression so test_i18n.py's ast-based scanner sees
    # FLASH_MESSAGES as a real i18n.t() consumer and scans every one of
    # its values for a French catalogue entry.
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
    """Return the deployed SKYPANE_SLEEP_S as an int, or None.

    Delegates the raw read to `wake.env_sleep_s()` (the same per-call,
    uncached `os.environ.get(SLEEP_ENV_VAR)` read), so there is exactly
    one place in this codebase that reads `SKYPANE_SLEEP_S`. Never
    captured at import time, so a redeployed env file takes effect on
    the next service restart.

    The `[WAKE_INTERVAL_MIN_S, WAKE_INTERVAL_MAX_S]` clamp stays here
    rather than in `wake.env_sleep_s()`: it exists solely so this
    result can be rendered as a `value` attribute on a Settings form's
    `min="60"` numeric input without failing HTML5 constraint
    validation — `deploy/skypane.env.example` ships `SKYPANE_SLEEP_S=30`,
    below that floor. That clamp does not apply to
    `wake.effective_wake_interval_s()`'s own threshold arithmetic, which
    must read the shipped value as the device's real, unclamped cadence.

    Fail-open (returns None for unset/empty/non-numeric/out-of-range),
    unlike `configured_password()`'s fail-closed auth-boundary contract:
    this is a UI pre-fill convenience whose absence has a designed empty
    state, the Wake interval field's placeholder text. Never raises.
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
    """The known-safe membership set `Handler._serve_illustration_image()`
    and `Handler._handle_illustration_replace()` validate a requested key
    against before any filesystem path is constructed — computed fresh
    on every call, closed and server-controlled: the fixed, code-shipped
    `illustrations.target_filenames()` list, unioned with one
    `"{key}.png"` per resolved entry in `manual_resolutions.json`.

    The manual half is read from state a previous, authenticated,
    already-validated request durably persisted (`POST
    /airlines/resolve`), never derived from the current request — this
    preserves validate-then-join: by the time the membership test runs,
    the key is prior server state this request merely references, not
    something this request asserts about itself. Recomputed per call
    rather than cached, because that manual state is mutable; no
    mtime-invalidated cache, matching `gallery_entries()`'s and
    `runway_images_available()`'s own always-fresh posture.
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
    part, returning that part's raw payload `bytes`, or `None` for
    anything that doesn't match that exact shape. Never raises for any
    input, including `None`/empty/truncated/binary-garbage `body` and a
    `None` `content_type` — every failure mode degrades to `None`.

    Deliberately not a general multipart parser: the one form this route
    ever serves carries a single file input and nothing else, so
    refusing anything but exactly one part is the smallest
    provably-correct behaviour.

    The part's header block (declared filename, field name, media type)
    is discarded entirely and never parsed. The destination path an
    upload is eventually written to is derived solely from the URL key
    the caller has already membership-validated against
    `_illustration_filenames(state_dir)`, never from anything in this
    body. A client-declared media type is not evidence of anything
    either: `illustrations.validate_illustration_file()`'s own
    Pillow-based header read is the sole authority on "is this really an
    image".

    Enforcing `MAX_ILLUSTRATION_UPLOAD_BYTES` is the caller's
    responsibility (`Handler._read_upload_body()`), not this function's.

    Boundary/media-type parsing uses `email.message.Message` — the
    non-deprecated stdlib replacement for `cgi.parse_header`; do not
    "modernise" this back to the `cgi` module, which is deprecated and
    removed in Python 3.13.
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
    # socketserver.StreamRequestHandler honours this attribute by calling
    # self.connection.settimeout(self.timeout) before setup, so a stalled
    # read anywhere on the connection (in particular the unauthenticated
    # POST /login body read) raises socket.timeout instead of blocking
    # the worker thread forever.
    timeout = REQUEST_SOCKET_TIMEOUT_S

    # --- response helpers -------------------------------------------

    def _send_hardening_headers(self):
        """Baseline hardening headers applied to every response.

        This is an authenticated admin panel (device config, poll
        trigger, LED control) reachable from the public internet — with
        no X-Frame-Options/CSP an authenticated page can be framed by a
        third-party site for clickjacking, and with no
        X-Content-Type-Options a MIME-sniffing quirk is one upstream
        misconfiguration away from an XSS vector. See
        CONTENT_SECURITY_POLICY's own module-level comment for the
        directive-by-directive CSP rationale.
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
        """`public` (default False, fail-closed) decides whether a cached
        response is advertised as shared-cacheable. A shared/intermediary
        cache has no knowledge of the session cookie `require_session()`
        checked — telling it a response may be stored means it can later
        replay that response to a different client that never presented
        the cookie. Callers must therefore explicitly opt into shared
        cacheability by passing a true `public` value; a route that is
        genuinely session-gated should never need to.
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
        /quick/* route's content negotiation.

        Carries send_html()'s/redirect()'s own `Cache-Control: no-store`
        and the same _send_hardening_headers() set, because a response to
        a state change on a session-gated route is no less sensitive for
        being empty.

        No Location header, deliberately: `fetch()` follows a same-origin
        redirect silently by default and reports the final response's
        status, so a 303 answered to a fetch would be read as success by
        a client whose session had just expired. companion/static/
        freshness.js sets `redirect: "manual"` to match.
        """
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.send_header("Cache-Control", "no-store")
        self._send_hardening_headers()
        self.end_headers()

    def _wants_no_content(self):
        """Whether this request identified itself as a fetch rather than a
        browser form submission.

        An exact value test, not mere header presence: the response shape
        is being chosen by something the caller controls, so the narrowest
        possible predicate is the right one. A browser form post sends no
        `X-Requested-With` at all, which keeps the no-JS path unaffected.
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
        # Carry the originally-requested protected route through the
        # login round-trip via an allowlisted `next` query parameter, so
        # a successful login returns the user to the exact route they
        # asked for instead of always /settings. _validated_next_route()
        # is the sole gate — an unrecognised requested_path is silently
        # discarded and the redirect degrades to the bare LOGIN_ROUTE.
        requested_path = urlsplit(self.path).path
        next_route = _validated_next_route(requested_path)
        if next_route:
            # safe="" (never the default safe="/") so the encoded value
            # is unambiguously a single query-string token
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
        """Read the request body as a `application/x-www-form-urlencoded`
        form, capped at MAX_FORM_BYTES. An oversized or undecodable body
        degrades to an empty form rather than raising — the remainder of
        an oversized body is still drained from the socket so a
        persistent connection is not left in a corrupted state.

        `Handler.timeout` (set on the class) bounds every socket read
        below, including this one — reachable pre-auth from
        `POST /login`. A stalled/slow-drip body triggers `socket.timeout`
        here, which is treated exactly like any other malformed-body case
        (degrade to an empty form) rather than propagating and blocking
        the worker thread indefinitely.
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
        """Read the POST body for an illustration-replace request, bounded
        by `MAX_ILLUSTRATION_UPLOAD_BYTES` — mirrors `read_form()`'s own
        draining discipline above rather than reusing it (`read_form()`
        is urlencoded-only and capped much lower). Returns `None` when
        `Content-Length` is absent, unparseable, non-positive, or exceeds
        the cap; an over-cap body still has its remainder drained from
        the socket in bounded chunks first, so a persistent connection is
        never left mid-body. `socket.timeout` (bounded by `Handler.timeout`)
        is treated exactly like any other malformed/over-cap body.
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
        # For FLASH_KEY_RULE_REPLACED's own "Updated the rule for {key}"
        # copy. Passed straight through to _resolve_flash_text(), which
        # is the sole place it is re-normalised before ever being
        # interpolated.
        rule_key = params.get("rule", [None])[0]
        state_dir = self.args.state_dir
        now = history_db.utc_now_iso()
        # Resolve this request's language preference exactly once,
        # immediately, and publish it through prefs so layout.py's
        # readers and this dict's own "lang" key below can never disagree.
        #
        # This must run before health_page.safe_health_state() below:
        # that call's own section builders format timestamps and
        # verdicts through layout.local_clock_text()/relative_age_text(),
        # both of which resolve their own `lang=None` default via
        # prefs.current_lang() at call time, not at read time. A
        # `ThreadingHTTPServer` request handler runs in a brand-new
        # native thread with a fresh contextvars.Context (never copied
        # from any other request's thread), so calling
        # safe_health_state() before this line means the health-state
        # markup is built under the ContextVar's bare default (English)
        # regardless of the requester's own language.
        prefs.set_request_prefs(lang=self._lang_from_request())
        # Computed once per request (fail-closed to None on any
        # unanticipated exception — see health_page.safe_health_state()'s
        # docstring) and threaded into ctx, so health_page.render() can
        # reuse the exact same DB-read snapshot instead of re-deriving it
        # from a second, non-atomic set of reads when the user is on
        # /health.
        health_state = health_page.safe_health_state(state_dir, now)
        # Loaded once per request and reused for both the "device_config"
        # and "screen_id" ctx keys below, rather than calling
        # load_device_config() a second time — screens.current_screen_id()
        # already membership-tests this value and falls back to
        # DEFAULT_SCREEN_ID, so no second validation is needed here.
        device_cfg = device_config.load_device_config(state_dir)
        # Loaded once per request and reused for three ctx keys below,
        # rather than calling load_calendar_registry() three times.
        # load_calendar_registry() is contractually never-raising, which
        # is what makes this safe to call unconditionally on every
        # authenticated page render.
        calendar_registry = calendar_rules.load_calendar_registry(state_dir)
        # Captured once here and reused for both the "last_checkin_ts"
        # ctx key below and _resolve_flash_text()'s own FLASH_KEY_SAVED
        # special case — never a second, independent read of the same fact.
        last_checkin_ts = _safe_last_checkin_ts(state_dir)
        # Read once per request, reused by both this dict's own
        # "battery_critical" key below and _resolve_flash_text()'s
        # FLASH_KEY_SAVED delay-sentence computation — never a second
        # read of poll_state.json for the same fact within one request.
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
            # Data only — the page module that renders it formats it
            # (wake.next_wake_at_iso() + layout.local_clock_text()),
            # matching wake.py's own deliberate no-view-dependency rule.
            "last_checkin_ts": last_checkin_ts,
            # The battery-empty latch, read once above and threaded into
            # every wake.next_wake_status()/wake.effective_wake_interval_s()
            # call this request makes (the Frame strip, the flash text,
            # and every other reader that shares this ctx) — so a parked
            # frame's monitoring never mistakes its own hourly parked
            # cadence for silence.
            "battery_critical": battery_critical,
            # The deployed SKYPANE_SLEEP_S, read fresh from this
            # process's own environment on every request — an int in
            # [WAKE_INTERVAL_MIN_S, WAKE_INTERVAL_MAX_S] or None. An
            # on-disk wake_interval_s always wins; config_page's render()
            # only consults this key when the stored value is None, i.e.
            # before the user has ever set one explicitly. Once a user
            # saves any value, the stored one wins permanently —
            # save_device_config() has no unset path (an empty numeric
            # input means "leave unchanged", never "clear").
            "wake_interval_env_default": env_wake_interval_default(),
            "flash": _resolve_flash_text(
                flash_key, state_dir, rule_key=rule_key, last_checkin_ts=last_checkin_ts,
                device_cfg=device_cfg, battery_critical=battery_critical),
            # The ARIA role the resolved flash text should render with,
            # looked up from the same flash_key this method already
            # resolved above — "status" for any key not in FLASH_ROLES
            # (including no flash at all).
            "flash_role": FLASH_ROLES.get(flash_key, "status"),
            "poll_cooldown_remaining": poll_cooldown_remaining(state_dir),
            "gallery_entries": gallery_entries(state_dir),
            "runway_images": runway_images_available(),
            # Computed here, not by a nav renderer, because
            # companion/pages/__init__.py forbids a page module importing
            # another page module — this file already imports health_page
            # legitimately, so this is the boundary's intended crossing
            # point. health_page.safe_health_state() (called above to
            # build `health_state`) is contractually never-raising
            # because this line runs on every authenticated page render.
            #
            # This is the "ok"/"warn"/"error" severity string, sourced
            # from the single `health_state` computed above (falling
            # back to "ok" when that computation failed) rather than a
            # second, independent health_page.health_severity() call.
            "health_severity": health_state["severity"] if health_state else "ok",
            "health_state": health_state,
            "now": now,
            # The raw `?resolve=` query value, or None — deliberately
            # unvalidated here. Validation belongs to
            # `airlines_page.unresolved_row_for_prefix()`, the single
            # membership test shared by the render path
            # (airlines_page.render()) and the write path
            # (Handler._handle_manual_resolve_post()); passing the raw
            # value through ctx and validating at the point of use is
            # what keeps those two from drifting apart. No illustration
            # key ever travels in a URL under any name — the resolve
            # section derives Step A versus Step B from server state alone.
            "resolve_prefix": params.get(
                airlines_page.RESOLVE_QUERY_PARAM, [None])[0],
            # The raw `?limit=` query value, or None — deliberately
            # unvalidated here, following "resolve_prefix" above.
            # Validation belongs to `history_page.flights_limit()`, the
            # single clamp shared by every consumer. No POST handler ever
            # consults this key — it is presentation-only, read only by
            # `history_page.render()`.
            "flights_limit": params.get(
                history_page.FLIGHTS_LIMIT_QUERY_PARAM, [None])[0],
            # Read fresh per request, never through the poll cycle's own
            # process-scoped cache, which exists only for its own
            # once-per-cycle read. This service is a long-running
            # ThreadingHTTPServer, so it must never read a manual
            # resolution through that cache.
            "manual_resolutions": manual_resolutions.load_manual_resolutions(state_dir),
            # Read fresh per request for the identical reason
            # manual_resolutions above is: never the poll cycle's own
            # once-per-cycle process-scoped registry cache. A
            # companion-side save landing mid-request must always be
            # visible on the very next request, not just the next poll
            # cycle.
            "colour_rules": colour_rules.load_colour_rules(state_dir),
            # Read fresh on every request, never captured at import
            # time, so a change to the secret file or its permissions is
            # visible on the very next request — the same per-call shape
            # env_wake_interval_default() above
            # already carries. This key is a boolean, not a string,
            # A status line only needs presence, not the value: the
            # calendar URL is a subscription secret, and it has no
            # rendering, logging or flash call site anywhere under
            # companion/.
            "calendar_configured": calendar_rules.calendar_is_configured(state_dir),
            # Read fresh per request from disk, never through the poll
            # cycle's own process-scoped cache, for the identical reason
            # manual_resolutions/colour_rules above are read fresh — this
            # service is a long-running ThreadingHTTPServer, and a sync
            # landing mid-session must be visible on the very next
            # request. load_calendar_registry() is contractually
            # never-raising, which is what makes it safe to call
            # unconditionally on every authenticated page render.
            "calendar_last_synced_at": calendar_registry["last_synced_at"],
            # The derived failed-fetch signal config_page.calendar_group()'s
            # status row needs — at least one fetch has been attempted
            # since connecting when this is not None, distinguishing
            # "just connected, no sync yet" from "has been failing"
            # without a new server-side field.
            "calendar_last_attempt_at": calendar_registry["last_attempt_at"],
            # The status row's own flight-count detail.
            "calendar_entry_count": len(calendar_registry["entries"]),
            # Read fresh on every request for the identical reason
            # calendar_configured/calendar_last_synced_at above are —
            # this is a long-running threaded server, and a mode
            # drifting mid-session has to be visible on the very next
            # request. Consumed by config_page.calendar_group()'s fourth
            # status branch alone; never widens calendar_configured's own
            # bool contract.
            "calendar_drift": calendar_rules.calendar_secret_mode_is_unsafe(state_dir),
        }

    # --- shared page fragments -------------------------------------------

    def _not_found_page(self):
        """The shared 404 body, reached from eleven call sites across this
        module — including the two pre-auth static-asset delegates,
        `_serve_stylesheet()` and `_serve_script_file()`, both reached
        before any `require_session()` gate because static assets are
        exempt from the session gate entirely.

        The Health nav dot is threaded through `health_alert` on the
        `self._is_authenticated()` branch only — that predicate is a
        pure bool check with no side effect, unlike `require_session()`
        (which redirects). Computing severity unconditionally would leak
        Health's warn/error state to an unauthenticated caller landing on
        either of the two pre-auth paths named above. `self.page_context()`
        is deliberately not called here: it performs six-plus SQLite
        reads, a device-config load and a filesystem scan for a single
        value on what is, structurally, an error path.
        """
        # This route renders before any session check, so the language
        # is resolved from the cookie (if any) or Accept-Language,
        # exactly like the login page below — never left at the
        # ContextVar's bare default.
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
        """The shared 403 body for do_POST()'s Origin/Sec-Fetch-Site gate —
        the one response every rejected cross-site POST gets, login
        included.

        Byte-for-byte the same shape as `_not_found_page()` immediately
        above (same reasons apply verbatim: pre-auth safe, resolves lang
        from the cookie/Accept-Language since this renders before any
        session check could run, and threads `health_alert` through
        `self._is_authenticated()` only — never leaking Health's state to
        an unauthenticated caller). Kept as a separate helper so a later
        route-table refactor can relocate this gate without also having
        to split the two response bodies apart first.
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
        """The login card's inner markup.

        `next_route` (already validated by `_validated_next_route()` at
        every call site — never a raw, unvalidated value) is carried
        through a hidden form field so a failed login attempt does not
        lose the originally-requested destination, and is only ever
        rendered when truthy.

        The lockout/error paragraph (whichever applies) carries
        `role="alert"` so assistive tech announces it immediately rather
        than waiting for the user to discover it visually, and sits
        directly under the password field in the shared `.field-error
        text-label` treatment — one error voice, the lockout sentence and
        the wrong-password sentence sharing the element id and differing
        only in copy. The password field carries
        `autocomplete="current-password"` and `autofocus` unconditionally
        — this is the one page in the app with a single,
        always-relevant focus target.

        `error`, when truthy, is already translated — the caller runs it
        through i18n.t() before passing it in, so test_i18n.py's scanner
        can trace the literal at its one real call site. This function
        only escapes it; it never calls i18n.t() itself on `error`.

        `aria-describedby` is emitted only when a message is actually
        rendered, and `aria-invalid="true"` only on the wrong-password
        branch — never with a negative value (that would announce a
        field as validated-and-fine before anything has been validated),
        and never on the lockout branch, where the typed value is not
        what is wrong.
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

        # The live countdown's seed and template, on the form itself —
        # the same server-computes-it/data-attribute/script-reads-it
        # mechanism companion/pages/config_page.py's poll_trigger_
        # section() and companion/static/poll-cooldown.js established,
        # reused rather than re-derived. The remaining figure is
        # LOGIN_THROTTLE.seconds_remaining(key)'s own output for the
        # caller's own bucket, serialised here; it is never computed
        # from a client clock, and no throttling constant crosses to
        # the client.
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
        """The show-password toggle.

        Server-rendered with the `hidden` attribute, always, on every
        branch. companion/static/login-card.js is the only thing that
        ever removes it, at load — the no-JS floor held by construction
        rather than by a fallback: a browser with scripts blocked never
        runs that file, so it never sees this control at all. The same
        browser loses nothing else: the form still submits and the
        password still reaches the server exactly as before.

        Reuses `.copy-btn`'s visual box, fill and hit area verbatim, but
        not its SVG sprite: the glyph is a text character in the same
        14px box instead. The glyph is swapped with the state (filled =
        the value is masked, hollow = it is revealed) so the control's
        own appearance is not carried by colour alone; `aria-pressed`
        and the two translated accessible names carry it for everyone
        else.

        Both labels and both glyphs are rendered here, as server-escaped
        data-* attributes, and read back by the script — the same shape
        flight-rows.js's own data-show-label/data-hide-label pair uses,
        so no English string is ever hard-coded on the JS side.
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
        # Pre-session, exactly like _not_found_page() above — resolved
        # from the cookie or Accept-Language, never left at the
        # ContextVar's bare default.
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
        # One of the two gate exemptions named in this module's
        # docstring (login routes, stylesheet): no per-user content,
        # identical for every client, so it is legitimately
        # shared-cacheable.
        return self.send_bytes(200, "text/css", payload, cache_seconds=300, public=True)

    def _serve_script_file(self, abs_path):
        """Serve one fixed JavaScript file, pre-auth, structurally
        identical to _serve_stylesheet() above. Unlike
        _serve_gallery_image(), this resolves a single fixed module
        constant (`abs_path` is always one of this module's own path
        constants, never a client-supplied segment) and never joins a
        request-derived segment into a filesystem path, so it has no
        path-traversal surface. Shared body for every _serve_*_script()
        method below.

        `public=True`: this route is pre-auth and content-identical for
        every client (like `_serve_stylesheet()`, opted in the same
        way), so shared/intermediary caching is safe.
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

    # Each of the following is a thin delegate onto _serve_script_file(),
    # kept as its own named method (rather than inlined at the do_GET
    # call site) because an existing check references some of them by
    # name. There is no catch-all /static/ handler in this module: a new
    # script needs its own route constant, its own serve method and its
    # own branch in do_GET(), and a harness does a real GET of it
    # because a registration whose route 404s is a control that renders
    # and silently does nothing. `_serve_login_card_script()`'s single
    # consumer is the login page itself, which cannot have a session.

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
        # Membership test first, before any path is ever constructed
        # (validate-then-join, never sanitise-then-join). An unknown id
        # and an unreadable file both return this same 404, so a caller
        # can never distinguish "not a real runway" from "no image for a
        # real runway" — leaking nothing about the filesystem beyond the
        # RUNWAY_IDS set the authenticated /settings page already
        # renders in full to the same caller.
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
        # Membership test first, before any path is ever constructed
        # (validate-then-join, never sanitise-then-join — same shape as
        # _serve_runway_image() above). An unknown key, a missing file
        # and a malformed/unreadable asset all return this same 404 — a
        # caller can never distinguish "not a real illustration" from
        # "no file for a real one" from "normalization failed on this
        # one file"; illustrations.resolved_illustration_path()'s own
        # _UNSAFE_KEY_RE check below is defence in depth, never a
        # substitute for this membership test. The set consulted here is
        # a per-request union of vendored and server-persisted manual
        # keys (see _illustration_filenames()'s own docstring) — computed
        # fresh, not read from an import-time constant.
        filename = key + ".png"
        if filename not in _illustration_filenames(self.args.state_dir):
            return self.send_html(404, self._not_found_page())
        # resolved_illustration_path() checks
        # {state_dir}/illustration_overrides/{key}.png first, falling back
        # to the vendored file — the same seam server.plane.illustrations.
        # select_illustration() goes through for the panel compositor.
        # The key set this route accepts is still closed and
        # server-controlled (the membership test above); the bytes on
        # disk for an overridden key may have originated as a user
        # upload (POST /illustration/{key}.png, this route's sibling
        # below). That is still safe to decode here because this route
        # only ever sees bytes this server itself re-encoded through
        # Pillow in _handle_illustration_replace() after
        # validate_illustration_file() passed — never a client's raw
        # uploaded bytes — and because a decode failure on either an
        # override or a vendored file still degrades to this same
        # uniform 404, never a 500.
        path = illustrations.resolved_illustration_path(key, self.args.state_dir)
        if path is None:
            return self.send_html(404, self._not_found_page())
        # cached_normalized_png_bytes() is lru_cache'd per path+mtime, so
        # a replaced/overridden asset (a changed mtime, or a changed path
        # entirely once an override first appears) is picked up on the
        # very next request, not decoded/re-encoded once and left stale.
        try:
            payload = illustration_normalize.cached_normalized_png_bytes(path)
        except Exception:
            # Any decode/normalize failure on this one asset degrades to
            # the same 404 as a missing file (T-260902req-05), never a
            # 500 — the membership test above already proved this is a
            # known-safe key, whether it currently resolves to the
            # vendored file or a validated user override.
            return self.send_html(404, self._not_found_page())
        return self.send_bytes(200, "image/png", payload, cache_seconds=300)

    def _serve_theme_preview_image(self, theme_id):
        # This route's key set is closed and server-controlled
        # (device_config.THEMES). Membership test first, before any path
        # is ever constructed (validate-then-join, never
        # sanitise-then-join — same shape as _serve_runway_image()
        # above); theme_preview.cache_path() repeats this exact guard at
        # the boundary itself, so the helper stays safe even if some
        # future caller forgets to check membership first.
        if theme_id not in device_config.THEMES:
            return self.send_html(404, self._not_found_page())
        # The non-live variant is always produced from theme_preview.py's
        # own fixed fictional scene — never from client input, never
        # from live flight data. A `?live=1` request additionally reads
        # the operator's own most recent runway_events row (server-side
        # data this same session already sees in full on Home/Flights)
        # and renders it into a raster, never markup — only its integer
        # id ever reaches a filename, and any read/coercion failure
        # degrades to the fixed fictional scene, never a 500 (see
        # _safe_latest_runway_event()'s own docstring). This route is
        # not dispatched through page_context(), so it re-derives
        # `?live=` from self.path itself.
        parsed = urlsplit(self.path)
        live_flag = parse_qs(parsed.query).get("live", [None])[0]
        live_event = None
        if live_flag == "1":
            live_event = _safe_latest_runway_event(self.args.state_dir)
        # An unknown id (above), a render failure, and an OSError
        # writing/reading the cache file all degrade to this same 404 —
        # a caller can never distinguish "not a real theme" from "no
        # image for a real theme" from "render failed for this one theme".
        try:
            payload = theme_preview.cached_preview_bytes(
                self.args.state_dir, theme_id, live_event=live_event)
        except OSError:
            return self.send_html(404, self._not_found_page())
        except Exception:
            return self.send_html(404, self._not_found_page())
        if payload is None:
            return self.send_html(404, self._not_found_page())
        # Same cache window _serve_runway_image()/_serve_illustration_image()
        # use, relying on send_bytes()'s non-shared/private default since
        # this route sits behind do_GET()'s session gate.
        return self.send_bytes(200, "image/png", payload, cache_seconds=300)

    def _handle_illustration_replace(self, key):
        """POST /illustration/{key}.png — upload a replacement
        illustration. This is the feature's entire security surface: the
        first untrusted file upload this codebase has ever handled.
        Steps run in this exact order; the ordering is the security
        property, not an implementation detail:

        1. Membership test on `key` first, before any path is constructed
           or any byte of the body is read — validate-then-join, never
           sanitise-then-join, over the same closed set
           `_serve_illustration_image()` above already validates
           against, so a traversal-shaped key is structurally unable to
           reach a path here. A manually-resolved key is safe to accept
           because it can only be present in the set once a prior,
           authenticated Step A request already persisted it to
           `manual_resolutions.json` — this request merely references
           already-durable server state.
        2. `_read_upload_body()` — bounded by `MAX_ILLUSTRATION_UPLOAD_
           BYTES`, draining an over-cap body so the connection is not
           left corrupted.
        3. `parse_single_uploaded_file()` — a strict, stdlib-only,
           single-part multipart parse. The client's declared filename is
           never read by construction; the destination filename is always
           the already-membership-validated URL key.
        4. Write the raw payload to a temp file inside this key's override
           directory, named from the validated key plus this process's
           pid, then run `illustrations.validate_illustration_file()`
           against it — the same validation every vendored illustration
           is held to. A non-empty problem list rejects the upload; the
           problem strings go to the service log only, never the response.
        5. Only once validated: decode with Pillow, convert to RGBA, and
           re-encode to a second temp file. The client's original bytes
           are never stored — this route only ever writes bytes this
           server's own Pillow encoder produced, which also strips any
           ancillary chunk, trailing appended data, or polyglot payload
           the original upload may have carried.
        6. `os.replace()` the re-encoded temp onto the override path —
           atomic, since both temps live in the same override directory
           as the destination — then redirect with the success flash.
           Every failure branch unlinks both temp files first.

        No CSRF token: the session cookie's `SameSite=Strict` flag is this
        site's documented CSRF control for every state-changing POST —
        this route follows that same, already-established posture
        (matching `POST /settings` and `POST /poll-now`) rather than
        inventing a second mechanism for itself alone.
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

        # Both temp files live alongside the destination (inside
        # override_dir) so the final os.replace() below stays a same-
        # filesystem, atomic rename — never a cross-filesystem copy.
        # Named from the validated key plus this process's pid plus a
        # fixed suffix, never from anything in the request.
        raw_tmp_path = os.path.join(
            override_dir, ".%s.%d.upload.tmp" % (key, os.getpid()))
        encoded_tmp_path = os.path.join(
            override_dir, ".%s.%d.encoded.tmp" % (key, os.getpid()))
        try:
            with open(raw_tmp_path, "wb") as fh:
                fh.write(payload)

            # This is what proves the bytes are really an image: it opens
            # the file with Pillow and reads format/dimensions from the
            # header, returning early on an over-cap pixel count before
            # any pixel data is decoded, so a decompression-bomb upload is
            # rejected without ever being expanded (T-v26-02-04).
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
        An `app.py`-owned handler, sibling to `_handle_poll_now()` and
        `_handle_illustration_replace()` above rather than a page
        module's `handle_post()`, because it must choose between two
        redirect targets and the documented `handle_post(form, ctx) ->
        flash_key` contract (companion/pages/__init__.py) returns only a
        flash key. Body runs in this exact order:

        1. Read the form and the state dir.
        2. `unresolved_row_for_prefix()` — the single membership test,
           re-run here rather than trusted from the hidden `prefix`
           field, matching `server/device_config.py`'s own
           re-validate-on-write discipline. A `None` result means the
           prefix is not a live member of the unresolved-callsign-prefix
           registry right now — nothing is written and nothing else
           runs; the operator lands back on Airlines with the stale
           flash. Every value used downstream comes from the validated
           tuple's own `row[0]`, never the raw form string.
        3. `manual_resolutions.add_entry()` — the module's own full
           validation ladder (prefix shape was already proven by step 2;
           this call re-validates the name: empty, over-length, reserved,
           and the registry cap).
        4. Map the result to a flash key with an explicit branch per
           value — never a dict-driven lookup, so an unrecognised result
           cannot silently pass through with no flash at all; anything
           unrecognised falls to `FLASH_KEY_MANUAL_SAVE_FAILED`. Any
           non-`ADD_OK` result redirects to `AIRLINES_ROUTE` with
           `?resolve={validated prefix}&flash={key}`, returning the
           operator to the form with their context intact.
        5. On `ADD_OK`: recompute the illustration key server-side from
           the name that was just persisted (re-read via
           `load_manual_resolutions()`, never the form value — the
           stored value is the authority). When
           `illustrations.resolved_illustration_path()` already resolves
           for that key (the named airline already has artwork, so no
           upload is ever asked for), redirect to
           `AIRLINES_ROUTE?flash=manual_resolved`; otherwise redirect to
           `AIRLINES_ROUTE?resolve={prefix}&flash=manual_resolved` so the
           page renders Step B. Both branches carry the success flash,
           which tells the operator the change reaches the frame at its
           next wake, never that it is instant.

        Every interpolated value in a redirect `Location` passes through
        `quote()`, matching the existing `quote(FLASH_KEY_...)` discipline
        at every other redirect in this file.

        No CSRF token: relies on the session cookie's `SameSite=Strict`
        flag, like every other state-changing route (see
        `_handle_illustration_replace()`'s own docstring above).
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
            # add_entry() collapses "field was empty" and "field was
            # supplied but illustration_key_for_name() returned None"
            # onto this one result code. Distinguish them here, at the
            # presentation layer only, by re-reading the same raw posted
            # value already passed to add_entry() two lines above — never
            # a second read_form() call, never a re-derivation of
            # manual_resolutions.py's own regex/validation logic.
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
        """POST /airlines/manual-resolutions/{prefix}/delete. Deliberately
        does not membership-test `key` against the unresolved-prefix
        registry the way `_handle_manual_resolve_post()` above does: a
        prefix is removed from that registry as soon as it resolves, so
        gating delete on it would make an entry undeletable the moment it
        started working. The safety property here is different and
        sufficient: `key` is normalised and used only as a dict key into
        `manual_resolutions.json`, never joined into a filesystem path,
        and `delete_entry()` touches nothing but that one JSON file — it
        cannot reach, and never reaches, the illustration override
        directory.

        A malformed prefix (fails `normalise_prefix()`) 404s without
        touching the registry. Deleting an already-absent prefix is a
        success, not an error — idempotent double-submission tolerance,
        matching this codebase's existing posture — so no flash on a
        second, identical POST either. Only a genuine write failure on a
        prefix that was present gets `FLASH_KEY_MANUAL_DELETE_FAILED`; the
        row's disappearance from the management list is otherwise the
        only confirmation.
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
        """POST /settings/rules/add: the per-flight colour-rules editor's
        immediate add route, following `_handle_manual_resolve_post()`'s
        shape above — an immediate action outside SETTINGS_ROUTE and the
        settings form's unsaved-changes dirty bar.

        Reads `rule_kind`/`rule_key`/`rule_theme_id` and calls
        `colour_rules.add_rule(state_dir, kind, key, theme_id)`, which is
        the single validation authority (kind membership, per-kind key
        format, theme membership, the registry cap, all checked before
        any write) — this handler performs no validation of its own.
        Maps the result to a flash key with an explicit branch per
        value, never a dict-driven lookup, so an unrecognised result
        cannot silently pass through with no flash at all: the new-entry
        result to the added key; the replaced result to the replaced
        key, with the just-added normalised value appended as a `rule=`
        query parameter so the replaced entry stays legible; the
        rejected-key result to the key-invalid key; the full result to
        the registry-full key. A crafted `rule_kind` or `rule_theme_id`
        is a hostile-request shape, not a genuine user mistake, and
        reuses the generic save-failed key rather than earning its own
        message — the failed result and any other unrecognised result
        map to the same generic key.

        No CSRF token, like every other state-changing route (see
        `_handle_illustration_replace()`'s own docstring above).
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
        """POST /settings/rules/{kind}/{value}/delete: mirrors
        `_handle_manual_resolution_delete()`'s shape above, with the one
        extra normalisation step this route's two-segment path needs.
        Both `kind` and `value` are re-normalised through
        `colour_rules.normalise_rule_kind()`/`normalise_rule_value()`
        before either is ever used as a registry lookup — an
        unrecognised kind or a malformed value 404s without touching
        the registry, never a lookup against a request-supplied string.

        Deleting an already-absent `(kind, value)` is success, not an
        error — idempotent double-submission tolerance, matching
        `_handle_manual_resolution_delete()`'s own established posture:
        that case redirects with no flash at all, exactly like a repeat
        delete of an already-gone manual resolution does.
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
        """POST /settings/calendar/disconnect: the calendar disconnect
        action's own dedicated, session-gated route.

        Two-step confirmation, server-side: a bare POST, or one carrying
        any confirm value other than
        `config_page.CALENDAR_DISCONNECT_CONFIRM_VALUE`, renders
        `config_page.calendar_disconnect_confirm_page(ctx)` directly at
        200 and returns without touching anything — the native
        `confirm()` `companion/static/confirm-submit.js` shows is a
        misclick guard only, never the security control; this branch is
        what holds against a hand-crafted request or a no-JS/CSP-blocked
        browser. Only an exact match on the accepted confirm value
        proceeds to call `calendar_rules.save_calendar_url(state_dir,
        calendar_rules.CLEAR_CALENDAR_URL)` — the single existing
        disconnect writer.

        The writer's boolean result is branched on explicitly: success
        redirects with `FLASH_KEY_CALENDAR_DISCONNECTED`; failure
        redirects with the existing generic `FLASH_KEY_CALENDAR_SYNC_FAILED`
        rather than inventing a second failure message for the same
        "couldn't touch the calendar's stored state" outcome.

        This route never calls `config_page.submitted_calendar_signal()`:
        this route's only possible meaning is "disconnect" once its own
        confirm gate passes.
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
        dedicated Connect/Replace route.

        This route must never reach the scoped settings handler's own
        scope/`in_scope` machinery: once Calendar shares Display's
        scope, a scoped POST carrying only a `calendar_url` field would
        read every absent checkbox on that page (Screen on/off, Quiet
        hours) as an explicit OFF and silently switch off both. It
        touches only `server/plane/calendar_rules.py`'s own writer pair,
        the same pair `_handle_settings_post()`'s calendar branch
        already calls for the save-triggered sync.

        Validation reuses `config_page.submitted_calendar_signal()` — the
        same resolver `_handle_settings_post()` consults, never a second
        URL-shape validator. Its `CLEAR`/`CARRY_FORWARD` outcomes cannot
        mean what they mean there: this form carries no
        `calendar_disconnect` field (so `CLEAR` cannot occur), and an
        empty `calendar_url` here is a genuine rejection — both
        `CARRY_FORWARD` and `INVALID` therefore redirect with the same
        rejection flash key.

        On acceptance: the URL is written, then, under `_POLL_LOCK` (the
        same lock `_handle_settings_post()` uses, serialising only
        against a concurrent request in this process),
        `calendar_rules.refresh_calendar_registry(state_dir,
        poll_loop.now_s(), min_interval_s=0)`. A successful fetch
        redirects with `FLASH_KEY_CALENDAR_CONNECT_OK`; a lock
        contention or a failed fetch both redirect with the existing
        generic `FLASH_KEY_CALENDAR_SYNC_FAILED`/
        `FLASH_KEY_CALENDAR_SYNC_DEFERRED` keys rather than earning a
        third/fourth failure message for the same "couldn't sync right
        now" outcome.
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
        """POST /settings/notifications/test: the Notifications group's
        own dedicated, session-gated immediate-action route — a sibling
        of `_handle_calendar_connect_post()` above, following that
        method's identical gate-then-dispatch shape in `do_POST()`.

        Elevation-of-privilege / SSRF-by-proxy: the topic URL is read
        from `device_config.load_device_config(state_dir)["notifications"]`
        — the stored value — and never from the submitted form body. A
        submitted `topic_url` field, if any, is never even looked at:
        accepting one here would turn this button into an open
        request-forwarder, sending an attacker-supplied URL through this
        server's own outbound network path on every click.

        With no topic URL stored, this redirects with the generic
        `FLASH_KEY_NOTIFICATIONS_TEST_FAILED` flash and never calls
        `notify.send_notification()` at all — there is nothing to test.
        Otherwise it calls that function with the fixed "Send a test"
        title/body pair, translated into the stored group's own `lang`
        via `notify.body_for_lang()` — never the requesting browser's own
        per-request language, which `server/poll_loop.py`'s real
        battery/silence transition pushes have no way to read either.
        `send_notification()`'s own boolean result is branched on
        explicitly: `True` redirects with the success flash, `False` (an
        unsafe URL, a timeout, a non-2xx response, or a transport
        exception — all folded into one bool by that function's own
        never-raising contract) redirects with the identical generic
        failure flash the unset-URL branch above already uses.
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
        """The `layout.page_shell()` assembly `_render_tab()` below needs
        on every GET, and `_handle_settings_post()`'s rejected-save
        branch also needs on a POST — factored out here so the failure
        branch, which already has its own `ctx` and already built its
        own `body` via a direct `config_page.render()` call, reuses this
        shell assembly instead of a second literal `page_shell()` call
        site. `_render_tab()` itself cannot be reused directly for that
        branch: it unconditionally re-checks `require_session()` (already
        checked once in `do_POST()` before dispatch) and always calls
        `render(ctx)` itself with no way to pass through an
        already-rendered body carrying `errors`/`submitted`.

        Passes `ctx["device_config"]` through as `page_shell()`'s
        `device_config` keyword — the one call site that covers both the
        GET path and the rejected-save POST's redisplay, so the nav's
        state reminder is always computed from the same value the Frame
        strip reads.
        """
        flash_html = (
            layout.flash_banner(ctx["flash"], role=ctx["flash_role"])
            if ctx["flash"] else None)
        return layout.page_shell(
            # _PAGE_TITLES' six values are the exact same English strings
            # as the corresponding nav labels — companion/i18n_fr/nav.py
            # already carries their French entries, so this i18n.t()
            # call resolves through that existing catalogue without a
            # new entry.
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
        """POST /settings — an app.py-owned handler, a sibling of
        `_handle_poll_now()` and `_handle_manual_resolve_post()` above,
        because this write path must choose between more than one
        outcome and the documented `handle_post(form, ctx) -> flash_key`
        contract (companion/pages/__init__.py) returns only a single
        key. Adds no route and no new gate — the session gate stays
        exactly where it was, in `do_POST()`, before dispatch.

        Body, in order:

        1. `config_page.handle_post(form, ctx, errors={})` runs every
           field validation and the device-config/secret-file writes,
           filling `errors` in place on any rejection.
        2. A non-empty `errors` re-renders the same scoped page directly
           at 200 with the user's own submission and each offending
           control's own message, never a redirect and never a flash
           banner (the message lives at the field) — mirroring
           `_handle_login_post()`'s own render-on-failure precedent. Any
           other non-`FLASH_KEY_SAVED` result falls through to the
           pre-existing redirect-with-flash behaviour, so no rejection
           can fall through silently. No fetch is ever attempted on a
           rejected save.
        3. `config_page.submitted_calendar_signal()` — the same resolver
           `handle_post()` itself just consulted, called again here
           (never re-derived) so persistence and this sync decision can
           never disagree about what the submission meant. `carry_forward`
           redirects with the ordinary saved key. `clear` needs no fetch:
           the erase already happened inside `handle_post()`'s own call
           to `calendar_rules.save_calendar_url()`.
        4. `set` — acquire `_POLL_LOCK`, the same lock `_handle_poll_now()`
           uses, with the same non-blocking acquire. `_POLL_LOCK` only
           serializes against another concurrent request in this same
           process; `skypane-poll.service`'s refresh cycle is a separate
           OS process with its own copy of every lock in this file, so
           `_POLL_LOCK` is invisible to it. The actual cross-process
           protection against that race lives inside
           `calendar_rules.refresh_calendar_registry()`/
           `save_calendar_url()` themselves, via an `fcntl.flock()`-based
           lock over a dedicated file in `state_dir`, visible to any
           process including the poll service. On contention with
           another companion request, the deferred key is the honest
           answer that the save landed and the sync did not run here.
        5. Inside the lock: `calendar_rules.refresh_calendar_registry()`
           directly — never `poll_loop.run_once()`, which would run a
           full detection/render cycle this save has no need for — with
           `min_interval_s=0` (omitting it would resolve to the standard
           throttle interval and silently skip the sync). The lock is
           released in a `finally`, so one failed sync cannot wedge a
           later manual poll trigger.

        No handler wraps the refresh call: `refresh_calendar_registry()`
        is contractually never-raising, and reading a caught error's
        text here would risk putting the full request URL into a
        message, since that is what network/name-resolution error
        strings routinely contain.

        The returned `(result_code, registry)` is branched on
        explicitly: the success constant redirects with the connected
        key, and every other value maps to the single failure key rather
        than being assumed away.

        The manual poll trigger's own cooldown machinery is neither
        consulted nor updated here: this is not a poll, and borrowing
        that cooldown would let an unrelated settings save block a real
        poll trigger for its duration.
        """
        state_dir = self.args.state_dir
        form = self.read_form()
        ctx = self.page_context()
        errors = {}
        flash_key = config_page.handle_post(form, ctx, errors=errors)
        # Land back on the scoped page the form came from.
        back = config_page.submitted_return_route(form)
        # A rejected save with at least one field-level error re-renders
        # the same scoped page directly at 200, carrying the user's own
        # submission and each control's own message — never a redirect.
        # See this method's own docstring bullet 2 for the full
        # reasoning.
        if errors:
            scope = config_page.submitted_scope(form)
            body = config_page.render(ctx, scope=scope, errors=errors, submitted=form)
            return self.send_html(200, self._page_shell_for(back, body, ctx))
        # Fallback for any failure path that somehow produced no field
        # error (there is none today — every FLASH_SAVE_FAILED return in
        # config_page.handle_post() now notes one — but this branch stays
        # so a future gate that forgets to call _note_error() still
        # rejects visibly instead of falling through to the success path
        # below).
        if flash_key != FLASH_KEY_SAVED:
            return self.redirect("%s?flash=%s" % (back, quote(flash_key)))

        calendar_signal = config_page.submitted_calendar_signal(form)
        if calendar_signal == config_page.CALENDAR_URL_SIGNAL_CLEAR:
            return self._settings_saved_redirect(back, FLASH_KEY_CALENDAR_DISCONNECTED)
        if calendar_signal != config_page.CALENDAR_URL_SIGNAL_SET:
            # carry_forward — an unrelated settings save. No fetch, no
            # lock acquisition: byte-identical to today's behaviour.
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
        """The success-branch response for POST /settings. Every call
        site above is only reached after `_handle_settings_post()`'s own
        `flash_key != FLASH_KEY_SAVED` guard has already passed, so the
        write has already landed on disk by the time this runs —
        `flash_key` here only names which calendar-sync outcome the
        browser's flash banner shows, never whether the save itself
        succeeded.
        """
        return self.redirect("%s?flash=%s" % (back, quote(flash_key)))

    def _handle_poll_now(self):
        # The trigger lives on Home (Refresh now) and on Device (Poll);
        # redirect back to whichever page posted it.
        back = self._referring_tab()
        # Non-blocking acquire, never a timeout.
        if not _POLL_LOCK.acquire(blocking=False):
            # Two requests arriving before the first has finished must
            # never both pass the cooldown check and both call
            # run_once() — the loser gets an immediate, honest "already
            # running" redirect instead of racing into a second poll
            # cycle or queueing silently behind a blocking acquire.
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
            # Always released — including on the except Exception: branch
            # above, which must stay inside this try so a failed poll
            # still releases the guard for the next attempt (never a
            # permanently wedged trigger, T-06.6.2-05).
            _POLL_LOCK.release()
        # The redirect is written only AFTER the lock is released: writing
        # it from inside the try left a window in which a client that
        # acted on the 303 immediately (the cooldown harness check, or a
        # double-tap on Refresh now) could reach the non-blocking acquire
        # above before this thread's finally ran, and be told "already
        # running" instead of the cooldown it had actually earned.
        return self.redirect("%s?flash=%s" % (back, quote(flash)))

    def _handle_quick_toggle(self, field, allowed_return_to=None, fallback_return_to=None):
        """The Home page's one-tap switches — POST /quick/display,
        POST /quick/quiet-hours, and POST /quick/led. The body carries
        exactly one meaningful field, `state`, whose value is the state
        to switch to ("on"/"off"), so a repeated submission is
        idempotent. Every other device-config value is carried forward
        untouched (save_device_config() treats a None keyword as "leave
        unchanged"), which is what makes this safe to expose to someone
        who never opens the settings pages. Session-gated in do_POST()
        like every other state-changing route.

        The redirect target comes from a form field, `return_to`,
        carrying whichever page the switch was pressed on
        (layout.frame_strip_html()'s own hidden field). It is
        membership-tested against `allowed_return_to` — the same "build
        a small whitelist, test membership, fall back to a known-safe
        route" shape `_referring_tab()` above uses for the Referer
        header — never string-prefix-matched, never parsed as a URL, so
        `https://evil.example/`, `//evil.example` and `/flights` all
        fall back to `fallback_return_to` rather than becoming an open
        redirect. All three redirects below use the resolved value.

        `allowed_return_to`/`fallback_return_to` are parameterised (not a
        single shared whitelist) because each route's switch lives on a
        different subset of pages — widening one shared tuple would
        silently let a crafted `return_to` on one route redirect
        somewhere that route has never redirected to. Each caller
        therefore passes its own whitelist and its own fallback; the
        shape — a small tuple, a membership test, a known-safe fallback —
        is identical for all callers and must not be reinvented. `None`
        defaults to `(layout.HOME_ROUTE, layout.DISPLAY_ROUTE)` /
        `layout.DISPLAY_ROUTE`, for the Display/Quiet-hours callers.
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

    # The Origin/Sec-Fetch-Site gate runs as the very first statement of
    # do_POST(), before urlsplit()/routing and before any read_form() —
    # so it covers LOGIN_ROUTE and every route below uniformly, and a
    # route added later here is covered automatically without editing
    # this gate. Defence in depth on top of SameSite=Strict (see
    # auth.post_origin_ok()'s own docstring for why both layers exist).
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

        # Gated here beside every other state-changing route, so this
        # write is a session-checked POST and nothing else — there is no
        # CSRF token anywhere in this app, and SameSite=Strict is the
        # only control, which is exactly why a state change must never
        # be reachable by GET. Its return_to whitelist is its own: the
        # LED switch lives on the Device page and nowhere else, so
        # /device is the single member and the fallback both.
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

        # Gated too, even though an unauthenticated POST /logout looks
        # harmless at first glance — it is a CSRF-shaped forced-sign-out
        # of whoever holds the session, and gating it costs a signed-out
        # caller nothing since they are already signed out. Also revokes
        # the presented token server-side before clearing the client's
        # cookie, so replaying the same cookie value after Sign out no
        # longer verifies.
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
