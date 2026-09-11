#!/usr/bin/env python3
"""companion/app.py — the SkyPane companion service entrypoint: a stdlib
`ThreadingHTTPServer` plus a hand-rolled route table, mirroring
`stub-server/byos_server.py`'s own shape (D-03, 06-CONTEXT.md: this is a
separate process, its own systemd unit — it never touches that vendored
device-protocol server).

Whole-site auth gate (D-02): every route except the login routes, the
stylesheet, and the theme-toggle POST calls `Handler.require_session()`
as its first statement and returns immediately when the session is
invalid — this file is the single place that gate is enforced, not each
page module. This same exemption list also decides the caching scope on
byte-served responses (`Handler.send_bytes()`'s `public` parameter): a
route not in this list must never be advertised to a shared/intermediary
cache as storable, so the two lists are not allowed to silently drift
apart.

This service binds all interfaces (0.0.0.0), exactly like
`stub-server/byos_server.py` already does in production — loopback
restriction is enforced at the firewall/reverse-proxy layer (ufw + Caddy)
rather than in the app, matching `deploy/skypane-byos.service`'s own
documented discipline (plan 06-11 adds the matching ufw deny for this
service's own port).

This service never writes the poll pipeline's own persisted flight-state
file — `server.poll_loop.run_once()` is that file's one legitimate writer
(06-RESEARCH.md's Pitfall 5). `POST /poll-now` calls `run_once()`
directly, in-process: the exact same production code path the systemd
timer already runs on its own 30-second cadence, never a second process
and never a re-implementation.

Startup refusal: `main()` calls `companion.auth.configured_password()`
before binding the socket. A missing password fails closed — this
service must never come up with authentication silently disabled.
"""
import email.message
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
# invocation the systemd unit uses). Quick task 260903-c4o retired this
# file's only two `server.panel_preview` call sites along with the
# /preview.png route they served — that module is no longer imported
# here.
_HERE = os.path.dirname(os.path.abspath(__file__))  # companion/
_REPO_ROOT = os.path.dirname(_HERE)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from companion import auth, illustration_normalize, layout, theme_preview, wake  # noqa: E402
from companion.pages import (  # noqa: E402
    airlines_page,
    config_page,
    health_page,
    history_page,
    home_page,
)
# Phase 13 plan 13-06: the module is already imported above
# (airlines_page); this named import reuses its D-11 membership test
# rather than re-implementing it, so the render path
# (airlines_page.render()) and the write path
# (Handler._handle_manual_resolve_post() below) can never diverge.
from companion.pages.airlines_page import unresolved_row_for_prefix  # noqa: E402
from server import device_config, history_db  # noqa: E402
from server.plane import (  # noqa: E402
    calendar_rules, colour_rules, illustrations, manual_resolutions)
import server.poll_loop as poll_loop  # noqa: E402

DEFAULT_PORT = 8643
GALLERY_DIRNAME = "gallery"
GALLERY_DEFAULT_LIMIT = 30
POLL_COOLDOWN_S = 45  # D-17: tens of seconds, a double-click guard, not an abuse rate-limit.
THEME_COOKIE_MAX_AGE_S = 365 * 24 * 3600
MAX_FORM_BYTES = 8192  # far more than any form on this site needs (Pitfall/T-06-05-07).
# quick task 260902-v26: comfortably above any real high-resolution
# transparent aircraft PNG — every vendored asset in
# server/assets/icons/illustrations/ is well under this — while bounding
# a single request's peak memory to a few MB on a CX22-class VPS.
# Enforcing this size is the caller's job (Handler._read_upload_body(),
# plan 02's Task 2), not parse_single_uploaded_file()'s own.
MAX_ILLUSTRATION_UPLOAD_BYTES = 4 * 1024 * 1024
# WR-03: bounds how long a single connection's socket reads (including the
# unauthenticated POST /login body read in read_form()) may block on a
# slow/stalled client. Without this, a client that opens a connection with
# a plausible Content-Length and then trickles (or never sends) the body
# ties up a ThreadingHTTPServer worker thread indefinitely — a slowloris-
# shaped DoS reachable before any credential check. 30s comfortably covers
# a slow real client on this LAN/VPN deployment while bounding the worst case.
REQUEST_SOCKET_TIMEOUT_S = 30

# 19-04-PLAN.md (D-18/A-35, T-19-06/T-19-17/T-19-18/T-19-19): the
# orchestrator-amended Content-Security-Policy sent on every response
# (see _send_hardening_headers() below). This is an authenticated admin
# panel reachable from the public internet with no CSP at all before
# this plan.
#   script-src 'self'  — deliberately no 'unsafe-inline' and no nonce.
#     This is where the real XSS risk lives, and Task 1 of this plan
#     (19-04-PLAN.md) removed the app's last two inline <script>
#     elements (companion/pages/config_page.py's poll_trigger_section(),
#     externalized to companion/static/poll-cooldown.js), so nothing
#     needs an exception here.
#   style-src 'self' 'unsafe-inline'  — solely for the seven
#     style="background:..." theme-swatch attributes in
#     companion/pages/config_page.py's _theme_chip_grid_html() and its
#     single-theme/calendar-section siblings. Every one of those values
#     comes from the fixed 18-member server/device_config.py THEMES
#     registry and is never user input, so this allowance carries no
#     injection path; a class-per-theme CSS refactor was rejected
#     because it would churn dozens of pinned render checks for no
#     security gain.
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
# D-07 (11-04): the same environment variable deploy/skypane-byos.service
# passes to byos_server.py as --sleep. It reaches this process because
# deploy/skypane-companion.service declares the identical
# EnvironmentFile=/opt/skypane/skypane.env directive — no file parsing, no
# dotenv loader, no new deployment step. Deliberately not imported from
# companion/auth.py: that module owns the password variable's name, not
# this one, and the two have unrelated lifecycles.
SLEEP_ENV_VAR = "SKYPANE_SLEEP_S"

LOGIN_ROUTE = "/login"
STYLE_ROUTE = "/static/style.css"
# Authoritative route value — companion/pages/health_page.py's
# BATTERY_TREND_SCRIPT_SRC (plan 06.5-02) must equal this exactly; that
# plan adds a check asserting the two stay in sync. Do not edit one
# without the other.
SCRIPT_ROUTE = "/static/battery-trend.js"
# Authoritative route value — companion/layout.py's NAV_DROPDOWN_SCRIPT_SRC
# (plan 06.6.1-05) must equal this exactly; that plan's Task 3 asserts the
# two stay in sync, mirroring SCRIPT_ROUTE/BATTERY_TREND_SCRIPT_SRC's own
# established pair above.
NAV_SCRIPT_ROUTE = "/static/nav-dropdown.js"
# 06.6.3: four more authoritative route values — each must equal
# companion/layout.py's matching *_SCRIPT_SRC constant exactly (this
# plan's own checks assert the equality), mirroring the
# SCRIPT_ROUTE/NAV_SCRIPT_ROUTE pairs above.
DIRTY_STATE_SCRIPT_ROUTE = "/static/dirty-state.js"
LIST_FILTER_SCRIPT_ROUTE = "/static/list-filter.js"
COPY_BUTTON_SCRIPT_ROUTE = "/static/copy-button.js"
FRESHNESS_SCRIPT_ROUTE = "/static/freshness.js"
# D-20 (06.6.4.1-02): companion/layout.py's PANEL_LOOKUP_SCRIPT_SRC must
# equal this exactly, mirroring the SCRIPT_ROUTE/NAV_SCRIPT_ROUTE pairs above.
PANEL_LOOKUP_SCRIPT_ROUTE = "/static/panel-lookup.js"
# Quick task 260903-peo (UIR-19): companion/layout.py's
# FLASH_CLEANUP_SCRIPT_SRC must equal this exactly, mirroring the
# SCRIPT_ROUTE/NAV_SCRIPT_ROUTE pairs above.
FLASH_CLEANUP_SCRIPT_ROUTE = "/static/flash-cleanup.js"
# 19-04-PLAN.md (D-18/A-35): companion/layout.py's
# POLL_COOLDOWN_SCRIPT_SRC must equal this exactly, mirroring the
# SCRIPT_ROUTE/NAV_SCRIPT_ROUTE pairs above.
POLL_COOLDOWN_SCRIPT_ROUTE = "/static/poll-cooldown.js"
# 19-11-PLAN.md Task 2 (D-08/A-26): companion/layout.py's
# CONFIRM_SUBMIT_SCRIPT_SRC must equal this exactly, mirroring the
# SCRIPT_ROUTE/NAV_SCRIPT_ROUTE pairs above — the ninth static script.
CONFIRM_SUBMIT_SCRIPT_ROUTE = "/static/confirm-submit.js"
# Single definition site is companion/pages/config_page.py (app.py imports
# that module, so the reverse import would be a cycle) — rebound here
# rather than re-typed, exactly like RUNWAY_IMAGE_ROUTE_PREFIX and the
# FLASH_KEY_* constants below (D-26, 06.6.4.1-07: renamed from "/config"
# to "/settings"; the old path now 404s by design, no redirect).
SETTINGS_ROUTE = config_page.SETTINGS_ROUTE
POLL_ROUTE = "/poll-now"

# Phase 18 (companion audit / UX refactor): the page routes. All six
# live tabs are declared once, in companion/layout.py's NAV_GROUPS;
# these aliases exist so this module's dispatch reads by name.
HOME_ROUTE = layout.HOME_ROUTE
DISPLAY_ROUTE = layout.DISPLAY_ROUTE
FLIGHTS_ROUTE = layout.FLIGHTS_ROUTE
AIRLINES_ROUTE = layout.AIRLINES_ROUTE
HEALTH_ROUTE = layout.HEALTH_ROUTE
DEVICE_ROUTE = layout.DEVICE_ROUTE
# The pre-phase-18 History route, kept as a fixed 303 to FLIGHTS_ROUTE
# for stale bookmarks — the same treatment PREVIEW_PAGE_ROUTE gets.
HISTORY_LEGACY_ROUTE = "/history"
# Quick-action routes the Home page's widgets post to. Must equal
# companion/pages/home_page.py's own literals (that module cannot
# import this one).
QUICK_DISPLAY_ROUTE = home_page.QUICK_DISPLAY_ROUTE
QUICK_QUIET_HOURS_ROUTE = home_page.QUICK_QUIET_HOURS_ROUTE
assert POLL_ROUTE == home_page.POLL_ROUTE
THEME_ROUTE = "/ui-theme"
LOGOUT_ROUTE = "/logout"
# D-22 (06.6.4.1-08): the standalone Preview HTML page is retired — its
# entire content moved into History (06.6.4.1-05) — so this route is kept
# solely as a fixed-redirect source, not a page route. Named
# PREVIEW_PAGE_ROUTE (not PREVIEW_ROUTE) to say what it now is.
PREVIEW_PAGE_ROUTE = "/preview"
GALLERY_ROUTE_PREFIX = "/gallery/"
# Single definition site is companion/pages/config_page.py (app.py imports
# that module, so the reverse import would be a cycle) — rebound here
# exactly like the FLASH_KEY_* constants below.
RUNWAY_IMAGE_ROUTE_PREFIX = config_page.RUNWAY_IMAGE_ROUTE_PREFIX
# D-15 (06.6.4.1-02): the Airlines gallery's per-variant illustration image
# route. Naming convention matches RUNWAY_IMAGE_ROUTE_PREFIX above.
ILLUSTRATION_IMAGE_ROUTE_PREFIX = "/illustration/"
# Single definition site is companion/theme_preview.py (06.6.4.1.1-01),
# NOT a page module — deliberately the opposite of
# RUNWAY_IMAGE_ROUTE_PREFIX/ILLUSTRATION_IMAGE_ROUTE_PREFIX's precedent of
# living with the emitter. Here the render/cache mechanism owns the prefix
# since a later plan rebinds it a second time, from
# companion/pages/config_page.py, for the Settings theme picker's own
# markup — see theme_preview.py's module docstring for the full reasoning.
THEME_PREVIEW_ROUTE_PREFIX = theme_preview.THEME_PREVIEW_ROUTE_PREFIX
# Phase 15 D-10 (15-05-PLAN.md): single definition site is companion/
# pages/config_page.py (app.py imports that module, so the reverse import
# would be a cycle) — rebound here exactly like RUNWAY_IMAGE_ROUTE_PREFIX/
# SETTINGS_ROUTE above.
RULES_ADD_ROUTE = config_page.RULES_ADD_ROUTE
RULES_DELETE_ROUTE_PREFIX = config_page.RULES_DELETE_ROUTE_PREFIX
RULES_DELETE_ROUTE_SUFFIX = config_page.RULES_DELETE_ROUTE_SUFFIX
# 19-11-PLAN.md Task 1 (D-08/A-26): single definition site is companion/
# pages/config_page.py, rebound here exactly like RULES_ADD_ROUTE above
# rather than retyped as a literal (app.py imports that module, so the
# reverse import would be a cycle).
CALENDAR_DISCONNECT_ROUTE = config_page.CALENDAR_DISCONNECT_ROUTE

# The four flash-key string literals are defined exactly once, in
# companion/pages/config_page.py (plan 06-07's Task 2) — imported here
# under their historical FLASH_KEY_* names so every existing call site in
# this file (and companion/test_companion_app.py's own assertions against
# the literal query-string values) stays unchanged.
FLASH_KEY_SAVED = config_page.FLASH_SAVED
FLASH_KEY_SAVE_FAILED = config_page.FLASH_SAVE_FAILED
FLASH_KEY_POLL_TRIGGERED = config_page.FLASH_POLL_TRIGGERED
FLASH_KEY_POLL_COOLDOWN = config_page.FLASH_POLL_COOLDOWN
FLASH_KEY_POLL_FAILED = config_page.FLASH_POLL_FAILED
FLASH_KEY_POLL_ALREADY_RUNNING = config_page.FLASH_POLL_ALREADY_RUNNING
# quick task 260902-v26: the three illustration-replace flash keys are
# defined once in companion/pages/airlines_page.py (that module's own
# comment explains why, mirroring config_page.py's FLASH_* rebinding
# pattern above exactly).
FLASH_KEY_ILLUSTRATION_REPLACED = airlines_page.FLASH_ILLUSTRATION_REPLACED
FLASH_KEY_ILLUSTRATION_REJECTED = airlines_page.FLASH_ILLUSTRATION_REJECTED
FLASH_KEY_ILLUSTRATION_REPLACE_FAILED = airlines_page.FLASH_ILLUSTRATION_REPLACE_FAILED
# Phase 13 plan 13-06: the eight manual-resolution flash keys are defined
# once in companion/pages/airlines_page.py, for the identical reason the
# three FLASH_ILLUSTRATION_* keys above are — mirroring that same
# rebinding pattern exactly.
FLASH_KEY_MANUAL_RESOLVED = airlines_page.FLASH_MANUAL_RESOLVED
FLASH_KEY_MANUAL_NAME_EMPTY = airlines_page.FLASH_MANUAL_NAME_EMPTY
FLASH_KEY_MANUAL_NAME_TOO_LONG = airlines_page.FLASH_MANUAL_NAME_TOO_LONG
FLASH_KEY_MANUAL_NAME_RESERVED = airlines_page.FLASH_MANUAL_NAME_RESERVED
FLASH_KEY_MANUAL_PREFIX_STALE = airlines_page.FLASH_MANUAL_PREFIX_STALE
FLASH_KEY_MANUAL_REGISTRY_FULL = airlines_page.FLASH_MANUAL_REGISTRY_FULL
FLASH_KEY_MANUAL_SAVE_FAILED = airlines_page.FLASH_MANUAL_SAVE_FAILED
FLASH_KEY_MANUAL_DELETE_FAILED = airlines_page.FLASH_MANUAL_DELETE_FAILED
# Phase 14 plan 14-07 (closes 13-UAT.md's G-01): a ninth manual-resolution
# flash key, declared by plan 14-02 beside the other eight and rebound
# here exactly like them — distinguishes a name the operator genuinely
# typed but that add_entry() can't use, from a genuinely empty field.
FLASH_KEY_MANUAL_NAME_UNUSABLE = airlines_page.FLASH_MANUAL_NAME_UNUSABLE
# Phase 15 D-10 (15-05-PLAN.md): the seven rule-editor flash keys are
# defined once in companion/pages/config_page.py, for the identical
# reason FLASH_KEY_SAVED/etc. above are — mirroring that same rebinding
# pattern exactly.
FLASH_KEY_RULE_ADDED = config_page.FLASH_RULE_ADDED
FLASH_KEY_RULE_REPLACED = config_page.FLASH_RULE_REPLACED
FLASH_KEY_RULE_KEY_INVALID = config_page.FLASH_RULE_KEY_INVALID
FLASH_KEY_RULE_REGISTRY_FULL = config_page.FLASH_RULE_REGISTRY_FULL
FLASH_KEY_RULE_SAVE_FAILED = config_page.FLASH_RULE_SAVE_FAILED
FLASH_KEY_RULE_DELETED = config_page.FLASH_RULE_DELETED
FLASH_KEY_RULE_DELETE_FAILED = config_page.FLASH_RULE_DELETE_FAILED
# Phase 17 plan 04 (D-06/D-09): the four save-triggered-sync flash keys
# are defined once in companion/pages/config_page.py, for the identical
# reason FLASH_KEY_SAVED/FLASH_KEY_RULE_*/etc. above are — mirroring that
# same rebinding pattern exactly.
FLASH_KEY_CALENDAR_CONNECTED = config_page.FLASH_CALENDAR_CONNECTED
FLASH_KEY_CALENDAR_SYNC_FAILED = config_page.FLASH_CALENDAR_SYNC_FAILED
FLASH_KEY_CALENDAR_DISCONNECTED = config_page.FLASH_CALENDAR_DISCONNECTED
FLASH_KEY_CALENDAR_SYNC_DEFERRED = config_page.FLASH_CALENDAR_SYNC_DEFERRED

# A fixed key -> 06-UI-SPEC.md-copy dictionary — the flash mechanism only
# ever renders one of these, never a value taken verbatim from the query
# string (T-06-05-05). FLASH_KEY_POLL_COOLDOWN's "{n}" is filled in with a
# server-computed remaining-seconds figure, never anything client-supplied.
# Phase 18: quick-action outcomes (Home page widgets).
FLASH_KEY_DISPLAY_ON = "display_on"
FLASH_KEY_DISPLAY_OFF = "display_off"
FLASH_KEY_QUIET_ON = "quiet_on"
FLASH_KEY_QUIET_OFF = "quiet_off"
FLASH_KEY_QUICK_FAILED = "quick_failed"

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
    FLASH_KEY_SAVED: "Saved — will apply on the frame's next scheduled refresh.",
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
        "Illustration replaced — will apply on the frame's next scheduled refresh."),
    # Actionable, states the real requirements in user terms, and never
    # echoes a server path or any part of the uploaded file back to the
    # client (T-v26-02-08) — validate_illustration_file()'s own problem
    # strings go to the service log only, never into this copy.
    FLASH_KEY_ILLUSTRATION_REJECTED: (
        "Couldn't use that image — upload a transparent PNG that's at "
        "least 1200 pixels wide and landscape (wider than tall)."),
    FLASH_KEY_ILLUSTRATION_REPLACE_FAILED: (
        "Couldn't replace the illustration — please try again. If this "
        "keeps happening, check the companion service logs."),
    # Phase 13 plan 13-06: 13-UI-SPEC.md's Full Copy Deck, byte-identical.
    # The success string is this phase's latency-honesty obligation,
    # carried over from the Phase 12 precedent (FLASH_KEY_SAVED above): it
    # must not imply the frame changes instantly. The frame only ever
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
    # Two planner-added failure keys (not in the UI-SPEC deck — that deck
    # covers the six operator-facing rejections only), written in
    # FLASH_KEY_ILLUSTRATION_REPLACE_FAILED's own established voice above.
    FLASH_KEY_MANUAL_SAVE_FAILED: (
        "Couldn't save that resolution — the frame's state directory "
        "may not be writable."),
    FLASH_KEY_MANUAL_DELETE_FAILED: (
        "Couldn't delete that entry — the frame's state directory may "
        "not be writable."),
    # Phase 14 plan 14-07 (13-UAT.md G-01): distinct from
    # FLASH_KEY_MANUAL_NAME_EMPTY above — the operator DID type something,
    # it just can't be turned into an illustration key. Actionable, states
    # the real requirement in user terms, never echoes the rejected value
    # back, matching FLASH_KEY_ILLUSTRATION_REJECTED's own established voice.
    FLASH_KEY_MANUAL_NAME_UNUSABLE: (
        "That name can't be used for an illustration — try a different "
        "spelling, or a name with letters and numbers."),
    # Phase 15 D-10 (15-05-PLAN.md, 15-UI-SPEC.md's Flash Messages table,
    # byte-identical). rule_replaced's copy is a template: the {key}
    # placeholder is filled in by _resolve_flash_text()'s own second
    # special case below, never interpolated here.
    FLASH_KEY_RULE_ADDED: (
        "Rule added — the frame will use it next time it wakes and polls."),
    FLASH_KEY_RULE_REPLACED: (
        "Updated the rule for {key} — it replaces the one that was "
        "there before, applied next time the frame wakes and polls."),
    FLASH_KEY_RULE_KEY_INVALID: (
        "That doesn't match the selected kind's format — a callsign "
        "(e.g. AFR1234), an ICAO24 hex (e.g. 3944F2), or a 3-letter "
        "prefix (e.g. AFR)."),
    # The entry count is a literal, matching FLASH_KEY_MANUAL_REGISTRY_
    # FULL's own established shape above — colour_rules.COLOUR_RULE_MAX_
    # ENTRIES is also 200; the two must be kept equal by hand (a check in
    # companion/test_companion_app.py pins this).
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
    # Phase 17 plan 04 (D-06): the save-triggered immediate sync's four
    # outcomes. FLASH_KEY_CALENDAR_CONNECTED's "{n}"/"{s}" are filled by
    # _resolve_flash_text()'s third special case below, from a fresh
    # on-disk read of the registry's entry count at render time — never
    # carried through the redirect's query string (a client-supplied
    # count would defeat this mechanism's whole "only fixed server-side
    # copy" contract). States what the count means in checkable terms
    # (flights from THIS calendar inside the frame's window) without
    # ever implying the frame watches for them or will announce them —
    # matching the locked Phase 16 register's own constraint.
    FLASH_KEY_CALENDAR_CONNECTED: (
        "Connected — {n} flight{s} from this calendar in the frame's "
        "current window."),
    # The single honest generic failure (D-06/17-CONTEXT.md's "one
    # honest generic failure message, not a per-cause copy deck" —
    # FETCH_REJECTED_URL has zero call sites, so there is no second
    # cause this code can actually distinguish). Actionable, and
    # honestly states the frame retries on its own schedule regardless
    # — the URL was saved whether or not this one fetch succeeded. Never
    # echoes anything the operator submitted, and no exception's text is
    # ever read to build this string (T-17-FLASH).
    FLASH_KEY_CALENDAR_SYNC_FAILED: (
        "Saved, but couldn't sync that calendar right now — check the "
        "URL and try again. The frame will keep retrying on its own "
        "schedule."),
    # States both halves of what a disconnect did (D-04): the calendar
    # is disconnected, AND the flights it had supplied are gone from
    # disk — a promise the code keeps and the operator has no other way
    # to learn.
    FLASH_KEY_CALENDAR_DISCONNECTED: (
        "Calendar disconnected — the flights it supplied have been "
        "deleted from the server."),
    # Deliberately NOT FLASH_KEY_POLL_ALREADY_RUNNING's copy (D-09): that
    # string says nothing about whether the save itself succeeded, which
    # would leave the operator unsure their URL was even stored. The
    # LOCK behaviour is what's reused here, not the copy — this key says
    # plainly that the save landed and the sync will happen on the
    # frame's own next scheduled poll.
    FLASH_KEY_CALENDAR_SYNC_DEFERRED: (
        "Saved — a poll was already running, so this calendar will "
        "sync on the frame's next scheduled poll."),
}

# 06.6.2-06 (UXA-07): every FLASH_KEY_* -> the ARIA role its rendered
# flash banner should carry — "alert" (assertive) for a genuine failure,
# "status" (polite) for everything else, chosen by real severity rather
# than one role for every outcome. page_context() resolves this into
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
    # Phase 13 plan 13-06: "status" for the one success outcome, "alert"
    # for every rejection/failure — matching the plan's own explicit role
    # assignment (13-UI-SPEC.md's copy deck), not this dict's usual
    # success/rejection-both-status split above.
    FLASH_KEY_MANUAL_RESOLVED: "status",
    FLASH_KEY_MANUAL_NAME_EMPTY: "alert",
    FLASH_KEY_MANUAL_NAME_TOO_LONG: "alert",
    FLASH_KEY_MANUAL_NAME_RESERVED: "alert",
    FLASH_KEY_MANUAL_PREFIX_STALE: "alert",
    FLASH_KEY_MANUAL_REGISTRY_FULL: "alert",
    FLASH_KEY_MANUAL_SAVE_FAILED: "alert",
    FLASH_KEY_MANUAL_DELETE_FAILED: "alert",
    FLASH_KEY_MANUAL_NAME_UNUSABLE: "alert",
    # Phase 15 D-10: added/replaced/deleted are "status" (an outcome of a
    # normal add/delete flow); key-invalid/registry-full/save-failed/
    # delete-failed are "alert" (a rejection or a genuine failure) —
    # matching this dict's usual success/rejection split above.
    FLASH_KEY_RULE_ADDED: "status",
    FLASH_KEY_RULE_REPLACED: "status",
    FLASH_KEY_RULE_KEY_INVALID: "alert",
    FLASH_KEY_RULE_REGISTRY_FULL: "alert",
    FLASH_KEY_RULE_SAVE_FAILED: "alert",
    FLASH_KEY_RULE_DELETED: "status",
    FLASH_KEY_RULE_DELETE_FAILED: "alert",
    # Phase 17 plan 04 (D-06): the failure takes the assertive role,
    # matching every other genuine failure on this page
    # (FLASH_KEY_SAVE_FAILED/FLASH_KEY_POLL_FAILED/etc. above); the other
    # three are outcomes of a normal save flow, not failures.
    FLASH_KEY_CALENDAR_CONNECTED: "status",
    FLASH_KEY_CALENDAR_SYNC_FAILED: "alert",
    FLASH_KEY_CALENDAR_DISCONNECTED: "status",
    FLASH_KEY_CALENDAR_SYNC_DEFERRED: "status",
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
_RUNWAY_IMAGE_DIR = os.path.join(_HERE, "static")

# Process-global, not per-session (06-RESEARCH.md Pitfall 8's own login
# analogue) — D-01/D-02 mean there are no distinct users for a per-session
# counter to key on.
LOGIN_THROTTLE = auth.LoginThrottle()

# Same process-global-singleton shape as LOGIN_THROTTLE above (UXA-15):
# a single, module-level `threading.Lock()` guarding the entire
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
    # 06.6.4.1-08 (D-22): "/preview" entry removed — the Preview page is
    # retired (PREVIEW_PAGE_ROUTE now only redirects); NAV_TABS shrinks to
    # match in companion/layout.py.
}

# 06.6.2-07 (UXA-03): the login card's one-sentence purpose text, shown
# instead of the generic "Companion Access" copy the old page_shell()-based
# login reused.
LOGIN_EXPLANATION_TEXT = "Sign in to manage this device's settings."

# Quick task 260903-peo (UIR-16): the 404 page's title and one-sentence
# purpose, promoted to module constants matching LOGIN_EXPLANATION_TEXT's
# own precedent for user-facing copy. `layout.page_header()` escapes both
# when it renders them — these are always plain strings, never
# pre-escaped markup.
NOT_FOUND_TITLE = "Page not found."
NOT_FOUND_PURPOSE_TEXT = "The page you requested doesn't exist or may have moved."


def _validated_next_route(candidate):
    """Validate a caller-supplied `next` redirect target (a GET query
    value or a POST form value) against `layout.NAV_TABS`'s known
    routes — 06.6.2-07 (T-06.6.2-12, high-severity open-redirect
    mitigation).

    This is deliberately an exact-membership equality test against the
    set of NAV_TABS route literals — never `str.startswith("/")`, never
    URL-parsed, never regex-matched. There is no parsing logic here an
    attacker-controlled value could exploit: `candidate` either equals
    one of the known routes byte-for-byte, or it is discarded (returns
    `None`). A scheme-relative value (`//evil.example`), an absolute URL
    (`https://evil.example`), a path-traversal-shaped value, or any
    value not byte-identical to a real NAV_TABS route all fail this
    test and fall back to the caller's own safe default
    (`SETTINGS_ROUTE` on a successful POST, the bare `LOGIN_ROUTE` on an
    unauthenticated GET) — an open redirect is structurally impossible
    here, not merely discouraged. Deliberately not stated as a literal
    route count here (06.6.4.1-07): the allowlist is derived from
    NAV_TABS at runtime and self-adjusts whenever that tuple's own
    membership changes, so this docstring never needs a second edit
    when a route is added, renamed, or removed.

    Mirrors `Handler._referring_tab()`'s own exact-membership allowlist
    shape, but is a module-level function (not a method) since it must
    validate both a query-string value (GET) and a form value (POST),
    neither of which is `self.headers.get("Referer")`.
    """
    allowed = {route for route, _ in layout.NAV_TABS}
    return candidate if candidate in allowed else None


def _resolve_flash_text(flash_key, state_dir, rule_key=None):
    """`rule_key` (Phase 15 D-10, 15-05-PLAN.md) is the second special
    case this function carries, mirroring FLASH_KEY_POLL_COOLDOWN's own
    runtime-value-interpolation shape immediately below: FLASH_KEY_RULE_
    REPLACED's template names the key the operator just typed
    (`page_context()` passes the raw `rule=` query value through this
    parameter).

    T-15-14: `rule_key` is re-normalised through `colour_rules.
    normalise_rule_callsign()` before it is ever interpolated — never
    trusted from the request unvalidated. That normaliser's charset
    (`[A-Z0-9]{2,8}`) is a strict superset of the hex and prefix
    normalisers' own charsets, so it validates "is this safe to echo" for
    a value of any of the three kinds without needing to know which kind
    produced it (the kind itself does not travel in this redirect — only
    the already-normalised value does). A value that fails this check —
    including `None`, an empty string, or anything a hostile query
    parameter could carry — degrades to the generic FLASH_KEY_RULE_ADDED
    copy rather than ever reaching the page unvalidated; `escape_html()`
    on render (`layout.flash_banner()`) is the second line.
    """
    if flash_key not in FLASH_MESSAGES:
        return None
    template = FLASH_MESSAGES[flash_key]
    if flash_key == FLASH_KEY_POLL_COOLDOWN:
        return template.format(n=poll_cooldown_remaining(state_dir))
    if flash_key == FLASH_KEY_CALENDAR_CONNECTED:
        # Phase 17 plan 04 (D-06): the third special case, and the only
        # one this key needs. Read fresh from disk, on THIS redirect
        # target's own render — never carried through the redirect's
        # query string, which is client-supplied on the way back in and
        # would violate this mechanism's "only fixed server-side copy"
        # contract. load_calendar_registry() is contractually
        # never-raising (plan 16-03), which is what makes it safe to
        # call unconditionally here on every render that carries this
        # key.
        count = len(calendar_rules.load_calendar_registry(state_dir)["entries"])
        return template.format(n=count, s="" if count == 1 else "s")
    if flash_key == FLASH_KEY_RULE_REPLACED:
        normalised_key = colour_rules.normalise_rule_callsign(rule_key)
        if normalised_key is None:
            return FLASH_MESSAGES[FLASH_KEY_RULE_ADDED]
        return template.format(key=normalised_key)
    return template


def poll_cooldown_remaining(state_dir):
    """Seconds remaining before another `POST /poll-now` is allowed, or 0
    when the cooldown has elapsed. Server-global and persisted in
    `history.db`'s meta table (not the session cookie), so a second
    browser tab cannot bypass it and a service restart does not reset it
    (D-17, 06-RESEARCH.md Pitfall 8).
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

    19-12-PLAN.md Task 3 (D-13): the raw read now delegates to
    `wake.env_sleep_s()` — the SAME per-call, uncached
    `os.environ.get(SLEEP_ENV_VAR)` read that function already
    performs — so there is exactly ONE place in this codebase that
    reads `SKYPANE_SLEEP_S`. The `[device_config.WAKE_INTERVAL_MIN_S,
    device_config.WAKE_INTERVAL_MAX_S]` clamp below deliberately stays
    HERE rather than moving into `wake.env_sleep_s()`: that clamp exists
    solely so this function's result can be rendered as a `value`
    attribute on a Settings form's `min="60"` numeric input without
    failing HTML5 constraint validation — a UI-rendering constraint that
    does not apply to `wake.effective_wake_interval_s()`'s threshold
    arithmetic, which must read the shipped `SKYPANE_SLEEP_S=30` (below
    that same 60s floor) as the device's real, unclamped cadence. Never
    captured at import time — matching `auth.configured_password()`'s
    own per-call shape, so a redeployed env file takes effect on the
    next service restart with nothing cached in between.

    Contract difference from `configured_password()`: that function is
    fail-closed and raises `AuthNotConfigured` when its variable is
    missing, because it guards an auth boundary. This function is
    fail-open and returns `None` for every failure case (unset, empty,
    non-numeric, or out of range), because it is a UI pre-fill
    convenience whose absence has a designed, legitimate empty state —
    the Wake interval field's `WAKE_INTERVAL_PLACEHOLDER_TEXT`
    (`config_page.py`).

    The `[device_config.WAKE_INTERVAL_MIN_S, device_config.WAKE_INTERVAL_MAX_S]`
    range check is not belt-and-braces: `deploy/skypane.env.example` ships
    `SKYPANE_SLEEP_S=30`, below the field's own 60s floor. Rendering that
    as a `value` attribute on a `min="60"` numeric input would fail HTML5
    constraint validation and block submission of the *entire* Settings
    form, not just this field. The honest, designed behaviour for a
    deployed value the form cannot represent is the placeholder, not a
    number the user cannot save. Never raises.
    """
    value = wake.env_sleep_s()
    if value is None:
        return None
    if device_config.WAKE_INTERVAL_MIN_S <= value <= device_config.WAKE_INTERVAL_MAX_S:
        return value
    return None


def _safe_last_checkin_ts(state_dir):
    """The device's last real check-in, as the raw `device_health.ts`
    string `history_db.latest_device_health()` returns, or `None` on
    ANY failure — a missing/locked/unreadable database, or simply no
    reading recorded yet (19-12-PLAN.md Task 3, D-13). Modelled on
    `companion.pages.health_page._safe_query()`'s own narrow
    `(sqlite3.Error, OSError)` catch, the established shape for "one
    section's data access must never fault the whole page render" in
    this codebase; `companion/app.py` has no sibling of its own to
    reuse because none of `page_context()`'s existing SQLite reads
    (`poll_cooldown_remaining()`, `mark_poll_triggered()`) run inside a
    try/except of their own.
    """
    try:
        with history_db.open_db(state_dir) as conn:
            row = history_db.latest_device_health(conn)
    except (sqlite3.Error, OSError):
        return None
    return row["ts"] if row else None


def mark_poll_triggered(state_dir):
    with history_db.open_db(state_dir) as conn:
        history_db.set_meta(
            conn, history_db.META_LAST_POLL_TRIGGER, str(int(time.time())))


def gallery_entries(state_dir, limit=GALLERY_DEFAULT_LIMIT):
    """The newest `limit` gallery filenames (name-descending — plan 06-10
    names them by timestamp, so lexical order is chronological), filtered
    to files ending in the PNG extension. A missing gallery directory
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
    directory — the requested name is never joined onto a filesystem path
    (T-06-05-02); an unmatched, traversal-shaped, or otherwise unknown
    name returns None.
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
    """The single, mechanical place the on-disk naming convention (D-03's
    asset contract) is expressed: `runway-{runway_id}.png`.
    """
    return "runway-%s.png" % runway_id


def _runway_image_path(runway_id, image_dir=_RUNWAY_IMAGE_DIR):
    return os.path.join(image_dir, _runway_image_filename(runway_id))


def runway_images_available(image_dir=_RUNWAY_IMAGE_DIR):
    """The subset of `device_config.RUNWAY_IDS` that currently has a real
    `runway-{id}.png` file on disk. A missing `image_dir`, a missing
    individual file, or any other OS-level error while checking
    (permissions, a symlink loop) is not an error — it is D-03's
    documented graceful-fallback state, so this never raises:
    `os.path.isfile()` itself already swallows `OSError`/`ValueError`
    and returns `False`. The result is bounded by the fixed `RUNWAY_IDS`
    registry (iterated, never `os.scandir()`-ed), so it can never report
    an image for an id that isn't a real runway.
    """
    available = set()
    for runway_id in device_config.RUNWAY_IDS:
        if os.path.isfile(_runway_image_path(runway_id, image_dir)):
            available.add(runway_id)
    return available


def _illustration_filenames(state_dir=None):
    """The known-safe membership set `Handler._serve_illustration_image()`
    and `Handler._handle_illustration_replace()` validate a requested key
    against BEFORE any filesystem path is constructed (D-15) — computed
    fresh on every call, not memoised at import time (phase 13, D-09).

    The set is still closed and still server-controlled — what changed is
    that it is now the union of two server-side sources rather than one,
    and it is computed per request because the second source is mutable:
    `illustrations.target_filenames()` (the fixed, code-shipped vendored
    list, unchanged) plus, when `state_dir` is truthy, one `"{key}.png"`
    per entry in `manual_resolutions.load_manual_resolutions(state_dir)`
    whose `manual_resolutions.illustration_key_for_name(entry["airline_
    name"])` comes back truthy.

    The manual half is read from `manual_resolutions.json`, i.e. from
    state a previous, authenticated, already-validated request durably
    persisted (`POST /airlines/resolve`, `Handler._handle_manual_resolve_
    post()`) — it is never derived from the current request. This is what
    preserves validate-then-join and re-establishes `T-v26-02-01` rather
    than relaxing it: Step A persists the entry before Step B's upload is
    ever offered, so by the time `Handler._handle_illustration_replace()`
    runs its membership test the key is prior server state that this
    request merely references, not something this request asserts about
    itself.

    The cost is one small JSON read per authenticated illustration
    request, the same order as the unconditional `device_config.load_
    device_config()` already in `page_context()` and the same freshness
    posture as `gallery_entries()` and `runway_images_available()`. An
    mtime-invalidated module-level cache is explicitly rejected: this
    codebase has no precedent for one, and it would add a staleness
    window for no benefit at one operator's traffic volume.
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
    anything that doesn't match that exact shape. Never raises, for any
    input including `None`/empty/truncated/binary-garbage `body` and a
    `None` `content_type` — every failure mode degrades to `None`
    (quick task 260902-v26, matching `read_form()`'s own never-raises
    discipline above).

    This is deliberately NOT a general multipart parser. The one form
    this route ever serves carries a single file input and nothing else,
    so refusing anything but exactly one part is the smallest
    provably-correct behaviour, not an arbitrary restriction — a second
    part, a missing part, or a malformed delimiter structure all return
    `None` rather than being tolerated or best-effort-parsed.

    The part's header block (its declared filename, field name, and
    declared media type) is discarded entirely and never parsed — by
    construction, not merely by convention, this function has no code
    path that reads a client-declared filename. The destination path an
    upload is eventually written to is derived solely from the URL key
    the caller has already membership-validated against `_illustration_
    filenames(state_dir)` (phase 13, D-09: the widened per-request union
    of vendored and server-persisted manual keys), never from anything in
    this body. Likewise, a client-declared media
    type is not evidence of anything: `illustrations.validate_illustration_
    file()`'s own Pillow-based header read is the sole authority on
    "is this really an image", not this parser and not this header block.

    Enforcing `MAX_ILLUSTRATION_UPLOAD_BYTES` is the caller's
    responsibility (`Handler._read_upload_body()`, plan 02's Task 2), not
    this function's — this parser only ever sees bytes the caller already
    decided to hand it and never independently bounds anything by size.

    Boundary/media-type parsing uses `email.message.Message` (assign the
    raw header value, then `get_content_type()`/`get_param("boundary")`)
    — the non-deprecated stdlib replacement for `cgi.parse_header` on
    this project's pinned Python 3.11 venv. Do not "modernise" this back
    to the `cgi` module: it is deprecated there and removed outright in
    Python 3.13.
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
        del header_block  # deliberately discarded — see docstring above.

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
    # WR-03: socketserver.StreamRequestHandler honours this attribute by
    # calling self.connection.settimeout(self.timeout) before setup, so a
    # stalled read anywhere on the connection (in particular the
    # unauthenticated POST /login body read) raises socket.timeout instead
    # of blocking the worker thread forever.
    timeout = REQUEST_SOCKET_TIMEOUT_S

    # --- response helpers -------------------------------------------

    def _send_hardening_headers(self):
        """WR-02: baseline hardening headers applied to every response.

        This is an authenticated admin panel (device config, poll
        trigger, LED control) reachable from the public internet per
        this module's own docstring — with no X-Frame-Options/CSP an
        authenticated page can be framed by a third-party site for
        clickjacking, and with no X-Content-Type-Options a MIME-sniffing
        quirk is one upstream misconfiguration away from an XSS vector.

        19-04-PLAN.md (D-18/A-35): the fourth header, Content-Security-
        Policy, completes that stated intent — see
        CONTENT_SECURITY_POLICY's own module-level comment for the
        directive-by-directive rationale.
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
        # Phase 18 (audit): every HTML page is either session-gated or a
        # login form — never something a shared cache or the back button
        # should replay after sign-out.
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
        genuinely session-gated should never need to (WR-02,
        06.4-REVIEW.md).
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

    def redirect(self, location, set_cookie=None):
        # 19-04-PLAN.md (D-18/A-35, T-19-05): a 303 used to send none of
        # send_html()'s/send_bytes()'s headers; Cache-Control: no-store
        # matters here because a 303 can carry a Set-Cookie.
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
        # A-33/D-16: this is the ONLY place the revocation check runs —
        # every one of the 9+ require_session() call sites below goes
        # through this single predicate, never duplicated per route.
        cookies = auth.parse_cookies(self.headers.get("Cookie"))
        token = cookies.get(auth.SESSION_COOKIE_NAME)
        return bool(token) and auth.verify_session_token(token) and not auth.is_revoked(token)

    def require_session(self):
        if self._is_authenticated():
            return True
        # 06.6.2-07 (UXA-03): carry the originally-requested protected
        # route through the login round-trip via an allowlisted `next`
        # query parameter, so a successful login returns the user to
        # the exact route they asked for instead of always /settings.
        # _validated_next_route() (T-06.6.2-12) is the sole gate — an
        # unrecognised requested_path is silently discarded and the
        # redirect degrades to the bare LOGIN_ROUTE exactly as before
        # this change.
        requested_path = urlsplit(self.path).path
        next_route = _validated_next_route(requested_path)
        if next_route:
            # safe="" (never the default safe="/") so the encoded value
            # is unambiguously a single query-string token — matching
            # this plan's own acceptance criteria ("/login?next=%2Fhealth",
            # not "/login?next=/health").
            self.redirect(
                "%s?next=%s" % (LOGIN_ROUTE, quote(next_route, safe="")))
        else:
            self.redirect(LOGIN_ROUTE)
        return False

    def _resolved_ui_theme(self):
        cookies = auth.parse_cookies(self.headers.get("Cookie"))
        return layout.ui_theme_from_cookie(cookies)

    # --- form / query parsing -------------------------------------------

    def read_form(self):
        """Read the request body as a `application/x-www-form-urlencoded`
        form, capped at MAX_FORM_BYTES. An oversized or undecodable body
        degrades to an empty form rather than raising (T-06-05-07) — the
        remainder of an oversized body is still drained from the socket
        so a persistent connection is not left in a corrupted state.

        WR-03: `Handler.timeout` (set on the class) bounds every socket
        read below, including this one — reachable pre-auth from
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
        by `MAX_ILLUSTRATION_UPLOAD_BYTES` (quick task 260902-v26,
        T-v26-02-03) — deliberately mirrors `read_form()`'s own draining
        discipline above rather than reusing it (`read_form()` is
        urlencoded-only and capped much lower). Returns `None` when
        `Content-Length` is absent, unparseable, non-positive, or exceeds
        the cap; an over-cap body still has its remainder drained from
        the socket in bounded chunks first, so a persistent connection is
        never left mid-body. `socket.timeout` (bounded by `Handler.timeout`,
        WR-03) is treated exactly like any other malformed/over-cap body.
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
        # Phase 15 D-10: the raw `rule=` query value, read alongside the
        # existing flash-key read — for FLASH_KEY_RULE_REPLACED's own
        # "Updated the rule for {key}" copy. Passed straight through to
        # _resolve_flash_text(), which is the sole place it is
        # re-normalised before ever being interpolated (T-15-14).
        rule_key = params.get("rule", [None])[0]
        state_dir = self.args.state_dir
        now = history_db.utc_now_iso()
        # WR-04: compute once per request (fail-closed to None on any
        # unanticipated exception — see health_page.safe_health_state()'s
        # docstring) and thread both the derived severity and the full
        # state dict into ctx, so health_page.render() can reuse the
        # exact same DB-read snapshot instead of re-deriving it from a
        # second, non-atomic set of reads when the user is on /health.
        health_state = health_page.safe_health_state(state_dir, now)
        # 19-12-PLAN.md Task 2 (D-23): loaded ONCE per request and reused
        # for both the "device_config" and "screen_id" ctx keys below,
        # rather than calling load_device_config() a second time —
        # screens.current_screen_id(ctx) already membership-tests this
        # value and falls back to DEFAULT_SCREEN_ID, so no second
        # validation is needed at this layer.
        device_cfg = device_config.load_device_config(state_dir)
        return {
            "state_dir": state_dir,
            "ui_theme": self._resolved_ui_theme(),
            "device_config": device_cfg,
            # 19-12-PLAN.md Task 2 (D-23): the persisted screen_id, read
            # from the SAME device_config dict already loaded above —
            # config_page.py's render()/handle_post() consume this via
            # companion.screens.current_screen_id(ctx), which already
            # falls back to DEFAULT_SCREEN_ID for a missing/unknown value.
            "screen_id": device_cfg.get("screen_id"),
            # 19-12-PLAN.md Task 3 (D-13): the raw ISO string of the
            # device's last check-in, or None on any failure or absence
            # (_safe_last_checkin_ts()'s own fail-soft contract above).
            # Data only — the page module that renders it formats it
            # (wake.next_wake_at_iso() + layout.local_clock_text()),
            # matching wake.py's own deliberate no-view-dependency rule.
            "last_checkin_ts": _safe_last_checkin_ts(state_dir),
            # D-07 (11-04): the deployed SKYPANE_SLEEP_S, read fresh from
            # this process's own environment on every request — an int in
            # [WAKE_INTERVAL_MIN_S, WAKE_INTERVAL_MAX_S] or None. An
            # on-disk wake_interval_s (above) always wins; config_page's
            # render() only consults this key when the stored value is
            # None, i.e. before the user has ever set one explicitly.
            # Once a user saves any value, the stored one wins
            # permanently — save_device_config() has no unset path
            # (11-RESEARCH.md Open Question 2: an empty numeric input
            # means "leave unchanged", never "clear").
            "wake_interval_env_default": env_wake_interval_default(),
            "flash": _resolve_flash_text(flash_key, state_dir, rule_key=rule_key),
            # 06.6.2-06 (UXA-07): the ARIA role the resolved flash text
            # should render with, looked up from the same flash_key this
            # method already resolved above — "status" for any key not
            # in FLASH_ROLES (including no flash at all), the same
            # safe-fallback direction flash_banner()'s own role
            # whitelist uses.
            "flash_role": FLASH_ROLES.get(flash_key, "status"),
            "poll_cooldown_remaining": poll_cooldown_remaining(state_dir),
            "gallery_entries": gallery_entries(state_dir),
            "runway_images": runway_images_available(),
            # 06.6.1-04: computed here, not by a nav renderer, because
            # companion/pages/__init__.py forbids a page module importing
            # another page module — this file already imports health_page
            # legitimately (the runway_images entry above set the same
            # precedent in Phase 06.4), so this is the boundary's intended
            # crossing point. health_page.safe_health_state() (called
            # above to build `health_state`) is contractually
            # never-raising *because* this line runs on every
            # authenticated page render.
            #
            # 06.6.2-06 (UXA-14): this key was previously a boolean
            # named for the old anomaly_active() call; it is now the
            # "ok"/"warn"/"error" severity string. WR-04: sourced from
            # the single `health_state` computed above (falling back to
            # "ok" when that computation failed) rather than a second,
            # independent health_page.health_severity() call — every
            # consumer below moved together in the earlier commit that
            # introduced this key, and this one collapses the
            # once-per-page-render duplicate DB read that commit left
            # behind.
            "health_severity": health_state["severity"] if health_state else "ok",
            "health_state": health_state,
            "now": now,
            # Phase 13 plan 13-06: the raw `?resolve=` query value, or
            # None — deliberately unvalidated here. Validation belongs to
            # `airlines_page.unresolved_row_for_prefix()`, which is the
            # single D-11 membership test shared by the render path
            # (airlines_page.render()) and the write path
            # (Handler._handle_manual_resolve_post()); passing the raw
            # value through ctx and validating at the point of use is
            # what keeps those two from drifting apart. No illustration
            # key ever travels in a URL under any name — the resolve
            # section derives Step A versus Step B from server state
            # alone (plan 13-04), and that absence is a deliberate part
            # of this phase's threat posture.
            "resolve_prefix": params.get(
                airlines_page.RESOLVE_QUERY_PARAM, [None])[0],
            # 19-08-PLAN.md Task 3 (D-22, T-19-30/T-19-31): an exact
            # membership test against "1", nothing else — the same
            # discipline layout.ui_theme_from_cookie()/submitted_scope()
            # already apply to a query/cookie value before trusting it.
            # Presentation-only: this decides whether airlines_page's
            # artwork-editing forms (replace/upload/delete) RENDER, and
            # is NEVER consulted by any POST handler — those routes keep
            # their own require_session() gate regardless of this flag.
            # See companion/pages/__init__.py's ctx contract for the
            # full boundary statement.
            "edit_mode": params.get(
                airlines_page.EDIT_QUERY_PARAM, [None])[0] == "1",
            # Read fresh per request, exactly like device_config.load_
            # device_config(state_dir) above — never the process-scoped
            # cache set_manual_registry_state_dir()/airline_name_for_
            # prefix() expose, which exists only for the poll cycle's own
            # once-per-cycle read. This service is a long-running
            # ThreadingHTTPServer, so it must never read a manual
            # resolution through that cache.
            "manual_resolutions": manual_resolutions.load_manual_resolutions(state_dir),
            # Phase 15 D-10 (15-05-PLAN.md): read fresh per request,
            # exactly like manual_resolutions above and for the identical
            # reason — never the poll cycle's own once-per-cycle
            # process-scoped registry cache (see server/plane/
            # colour_rules.py's module docstring for that cache's own
            # setter). This service is a long-running
            # ThreadingHTTPServer, so a companion-side save landing
            # mid-request must always be visible on the very next
            # request, not just the next poll cycle.
            "colour_rules": colour_rules.load_colour_rules(state_dir),
            # Phase 17 (17-02-PLAN.md): read fresh on every request, never
            # captured at import time, so a change to the secret file or
            # its permissions is visible on the very next request — the
            # same per-call shape env_wake_interval_default() above
            # already carries. This key is a boolean, not a string,
            # because a status line only needs presence, not the value:
            # the calendar URL is a subscription secret, and it has no
            # rendering, logging or flash call site anywhere under
            # companion/ (T-16-SECRET, T-17-SECRET). That is no longer a
            # process-boundary claim — it never was one, since all three
            # systemd units run as the same user and load the same
            # environment file, and this process's ability to read the
            # value itself is not new here either: `POST /poll-now`
            # already calls the poll cycle in-process, and that cycle's
            # own calendar refresh has always read this value. What is
            # new, and deliberate, is that the companion also writes it
            # now (`save_calendar_url()`, plan 17-01's Settings save).
            "calendar_configured": calendar_rules.calendar_is_configured(state_dir),
            # Read fresh per request from disk, never through the poll
            # cycle's own process-scoped cache, for the identical reason
            # manual_resolutions/colour_rules above are read fresh — this
            # service is a long-running ThreadingHTTPServer, and a sync
            # landing mid-session must be visible on the very next
            # request. load_calendar_registry() is contractually
            # never-raising (plan 16-03), which is what makes it safe to
            # call unconditionally on every authenticated page render
            # (T-16-DOS).
            "calendar_last_synced_at": calendar_rules.load_calendar_registry(
                state_dir)["last_synced_at"],
            # Phase 17 plan 04 (D-02/D-08): the narrow predicate plan
            # 17-01 added, read fresh on every request for the identical
            # reason calendar_configured/calendar_last_synced_at above
            # are — this is a long-running threaded server, and a mode
            # drifting mid-session has to be visible on the very next
            # request. Consumed by config_page.calendar_group()'s fourth
            # status branch alone; never widens calendar_configured's own
            # bool contract (D-08).
            "calendar_drift": calendar_rules.calendar_secret_mode_is_unsafe(state_dir),
        }

    # --- shared page fragments -------------------------------------------

    def _not_found_page(self):
        """The shared 404 body, reached from ELEVEN call sites across this
        module — including the two PRE-AUTH static-asset delegates,
        `_serve_stylesheet()` and `_serve_script_file()`, both reached
        before any `require_session()` gate because D-02 exempts static
        assets from the session gate entirely. Quick task 260903-peo
        (UIR-16): the heading now uses the shared `layout.page_header()`
        component (the 30px serif `.page-title` role every other
        authenticated page opens with) instead of the old bare
        `<h1 class="text-heading">` (the 20px section-heading role,
        wrong here).

        The Health nav dot is threaded through `health_alert` on the
        `self._is_authenticated()` branch ONLY — that predicate (L549) is
        a pure bool check with no side effect, unlike `require_session()`
        (which redirects). Computing severity unconditionally would leak
        Health's warn/error state to an unauthenticated caller landing on
        either of the two pre-auth paths named above. `self.page_context()`
        is deliberately NOT called here: it performs six-plus SQLite
        reads, a device-config load and a filesystem scan for a single
        value on what is, structurally, an error path.
        """
        health_alert = None
        if self._is_authenticated():
            health_state = health_page.safe_health_state(
                self.args.state_dir, history_db.utc_now_iso())
            health_alert = health_state["severity"] if health_state else "ok"
        body = (
            layout.page_header(NOT_FOUND_TITLE, purpose=NOT_FOUND_PURPOSE_TEXT)
            + '<p class="text-body"><a href="%s">Back to Home</a></p>' % HOME_ROUTE
        )
        return layout.page_shell(
            title="Not Found", active="", body=body,
            ui_theme=self._resolved_ui_theme(), health_alert=health_alert)

    def _login_body(self, error=None, lockout_seconds=None, next_route=None):
        """The login card's inner markup — 06.6.2-07 (UXA-03).

        `next_route` (already validated by `_validated_next_route()` at
        every call site — never a raw, unvalidated value) is carried
        through a hidden form field so a failed login attempt does not
        lose the originally-requested destination, and is only ever
        rendered when truthy.

        The lockout/error paragraph (whichever applies) carries
        `role="alert"` so assistive tech announces it immediately
        rather than waiting for the user to discover it visually. The
        password field carries `autocomplete="current-password"`
        (password-manager support, T-06.6.2-14) and `autofocus`
        unconditionally — this is the one page in the app with a
        single, always-relevant focus target, so no error-conditional
        branching is needed.
        """
        parts = [
            '<h1 class="page-title">SkyPane</h1>',
            '<p class="text-body">%s</p>' % layout.escape_html(LOGIN_EXPLANATION_TEXT),
        ]
        if lockout_seconds:
            parts.append(
                '<p class="text-body" role="alert">%s</p>'
                % layout.escape_html(
                    "Too many attempts — try again in %ds." % lockout_seconds))
        elif error:
            parts.append(
                '<p class="text-body" role="alert">%s</p>'
                % layout.escape_html(error))
        next_field_html = (
            '<input type="hidden" name="next" value="%s">'
            % layout.escape_html(next_route)) if next_route else ""
        parts.append(
            '<form method="post" action="%s">'
            "%s"
            '<label for="password">Password</label>'
            '<input type="password" id="password" name="password" '
            'autocomplete="current-password" autofocus required>'
            '<button type="submit">Sign in</button>'
            "</form>" % (LOGIN_ROUTE, next_field_html)
        )
        return "".join(parts)

    def _render_login_page(self, error=None, lockout_seconds=None, next_route=None):
        body = self._login_body(
            error=error, lockout_seconds=lockout_seconds, next_route=next_route)
        return layout.login_shell(body, ui_theme=self._resolved_ui_theme())

    def _serve_stylesheet(self):
        try:
            with open(_STYLE_CSS_PATH, "rb") as fh:
                payload = fh.read()
        except OSError:
            return self.send_html(404, self._not_found_page())
        # One of the three D-02 gate exemptions named in this module's
        # docstring (login routes, stylesheet, theme-toggle POST): no
        # per-user content, identical for every client, so it is
        # legitimately shared-cacheable.
        return self.send_bytes(200, "text/css", payload, cache_seconds=300, public=True)

    def _serve_script_file(self, abs_path):
        """Serve one fixed JavaScript file, pre-auth, structurally
        identical to _serve_stylesheet() above. Unlike
        _serve_gallery_image(), this resolves a single fixed module
        constant (`abs_path` is always one of this module's own path
        constants — _BATTERY_TREND_JS_PATH or _NAV_DROPDOWN_JS_PATH — never
        a client-supplied segment) and never joins a request-derived
        segment into a filesystem path, so it has no path-traversal
        surface. Shared body for _serve_battery_trend_script() and
        _serve_nav_dropdown_script() below.

        `public=True`: this route is pre-auth and content-identical for
        every client (like `_serve_stylesheet()`, opted in the same way),
        so shared/intermediary caching is safe — matches
        `send_bytes()`'s WR-02 fix (quick task 260829-0rl), which made
        `private` the default for every OTHER route and left this one an
        accidental straggler only because this method predates that
        parameter existing at all.
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

    def _serve_battery_trend_script(self):
        """Serve companion/static/battery-trend.js, pre-auth. Thin
        delegate onto _serve_script_file() — kept as its own named method
        (rather than inlined at the do_GET call site) since an existing
        check references it by name.
        """
        return self._serve_script_file(_BATTERY_TREND_JS_PATH)

    def _serve_nav_dropdown_script(self):
        """Serve companion/static/nav-dropdown.js, pre-auth. Thin delegate
        onto _serve_script_file(), matching _serve_battery_trend_script()'s
        shape exactly.
        """
        return self._serve_script_file(_NAV_DROPDOWN_JS_PATH)

    def _serve_dirty_state_script(self):
        """Serve companion/static/dirty-state.js, pre-auth. Thin delegate
        onto _serve_script_file(), matching _serve_nav_dropdown_script()'s
        shape exactly.
        """
        return self._serve_script_file(_DIRTY_STATE_JS_PATH)

    def _serve_list_filter_script(self):
        """Serve companion/static/list-filter.js, pre-auth. Thin delegate
        onto _serve_script_file(), matching _serve_nav_dropdown_script()'s
        shape exactly.
        """
        return self._serve_script_file(_LIST_FILTER_JS_PATH)

    def _serve_copy_button_script(self):
        """Serve companion/static/copy-button.js, pre-auth. Thin delegate
        onto _serve_script_file(), matching _serve_nav_dropdown_script()'s
        shape exactly.
        """
        return self._serve_script_file(_COPY_BUTTON_JS_PATH)

    def _serve_freshness_script(self):
        """Serve companion/static/freshness.js, pre-auth. Thin delegate
        onto _serve_script_file(), matching _serve_nav_dropdown_script()'s
        shape exactly.
        """
        return self._serve_script_file(_FRESHNESS_JS_PATH)

    def _serve_panel_lookup_script(self):
        """Serve companion/static/panel-lookup.js, pre-auth. Thin delegate
        onto _serve_script_file(), matching _serve_nav_dropdown_script()'s
        shape exactly.
        """
        return self._serve_script_file(_PANEL_LOOKUP_JS_PATH)

    def _serve_flash_cleanup_script(self):
        """Serve companion/static/flash-cleanup.js, pre-auth. Thin
        delegate onto _serve_script_file(), matching
        _serve_panel_lookup_script()'s shape exactly (quick task
        260903-peo, UIR-19).
        """
        return self._serve_script_file(_FLASH_CLEANUP_JS_PATH)

    def _serve_poll_cooldown_script(self):
        """Serve companion/static/poll-cooldown.js, pre-auth. Thin
        delegate onto _serve_script_file(), matching
        _serve_flash_cleanup_script()'s shape exactly (19-04-PLAN.md,
        D-18/A-35).
        """
        return self._serve_script_file(_POLL_COOLDOWN_JS_PATH)

    def _serve_confirm_submit_script(self):
        """Serve companion/static/confirm-submit.js, pre-auth. Thin
        delegate onto _serve_script_file(), matching
        _serve_poll_cooldown_script()'s shape exactly (19-11-PLAN.md
        Task 2, D-08/A-26).
        """
        return self._serve_script_file(_CONFIRM_SUBMIT_JS_PATH)

    def _serve_gallery_image(self, requested):
        payload = gallery_bytes(self.args.state_dir, requested)
        if payload is None:
            return self.send_html(404, self._not_found_page())
        # This route sits behind do_GET()'s require_session() gate, so it
        # deliberately relies on send_bytes()'s non-shared (private)
        # default rather than opting into shared cacheability.
        return self.send_bytes(200, "image/png", payload, cache_seconds=3600)

    def _serve_runway_image(self, runway_id):
        # Membership test FIRST, before any path is ever constructed
        # (validate-then-join, never sanitise-then-join — T-06.4-02). An
        # unknown id and an unreadable file both return this same 404, so
        # a caller can never distinguish "not a real runway" from "no
        # image for a real runway" — leaking nothing about the
        # filesystem beyond the RUNWAY_IDS set the authenticated /settings
        # page already renders in full to the same caller.
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
        # Membership test FIRST, before any path is ever constructed
        # (validate-then-join, never sanitise-then-join — same shape as
        # _serve_runway_image() above, D-15). An unknown key, a missing
        # file and a malformed/unreadable asset all return this same 404
        # (quick task 260902-req-02, T-260902req-05) — a caller can never
        # distinguish "not a real illustration" from "no file for a real
        # one" from "normalization failed on this one file";
        # illustrations.resolved_illustration_path()'s own _UNSAFE_KEY_RE
        # check below is defence in depth, never a substitute for this
        # membership test. Phase 13 (D-09): the set consulted here is now
        # a per-request union of vendored and server-persisted manual
        # keys (see _illustration_filenames()'s own docstring) — computed
        # fresh, not read from an import-time constant.
        filename = key + ".png"
        if filename not in _illustration_filenames(self.args.state_dir):
            return self.send_html(404, self._not_found_page())
        # quick task 260902-v26: resolved_illustration_path() checks
        # {state_dir}/illustration_overrides/{key}.png first, falling back
        # to the vendored file — the same seam server.plane.illustrations.
        # select_illustration() goes through for the panel compositor
        # (plan 01). The *key set* this route accepts is still closed and
        # server-controlled (the membership test above); what changed
        # since 260902-req-02 is that the *bytes on disk* for an
        # overridden key may now have originated as a user upload
        # (POST /illustration/{key}.png, this route's sibling below, no
        # longer "never user-supplied image bytes" as this comment used to
        # claim). That is still safe to decode here because this route
        # only ever sees bytes this server itself re-encoded through
        # Pillow in _handle_illustration_replace() after
        # validate_illustration_file() passed — never a client's raw
        # uploaded bytes — and because a decode failure on either an
        # override or a vendored file still degrades to this same uniform
        # 404 (T-260902req-05), never a 500.
        path = illustrations.resolved_illustration_path(key, self.args.state_dir)
        if path is None:
            return self.send_html(404, self._not_found_page())
        # T-260902req-06: cached_normalized_png_bytes() is lru_cache'd per
        # path+mtime, so a replaced/overridden asset (a changed mtime, or a
        # changed path entirely once an override first appears) is picked
        # up on the very next request, not decoded/re-encoded once and
        # left stale.
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
        # T-06.6.4.1.1-01/T-06.6.4.1.1-05: this route's key set is closed
        # and server-controlled (device_config.THEMES) — the bytes it
        # serves are always produced by this server itself from vendored
        # font/illustration assets, never from client input, and the
        # rendered scene is theme_preview.py's own module-level fixture
        # (D-06), so no live flight/device data can ever reach an image
        # served here. Membership test FIRST, before any path is ever
        # constructed (validate-then-join, never sanitise-then-join —
        # same shape as _serve_runway_image() above, T-06.6.4.1.1-01);
        # theme_preview.cache_path() repeats this exact guard at the
        # boundary itself, so the helper stays safe even if some future
        # caller forgets to check membership first.
        if theme_id not in device_config.THEMES:
            return self.send_html(404, self._not_found_page())
        # T-06.6.4.1.1-02: an unknown id (above), a render failure, and an
        # OSError writing/reading the cache file all degrade to this same
        # 404 — a caller can never distinguish "not a real theme" from "no
        # image for a real theme" from "render failed for this one theme".
        try:
            payload = theme_preview.cached_preview_bytes(self.args.state_dir, theme_id)
        except OSError:
            return self.send_html(404, self._not_found_page())
        except Exception:
            return self.send_html(404, self._not_found_page())
        if payload is None:
            return self.send_html(404, self._not_found_page())
        # Same cache window _serve_runway_image()/_serve_illustration_image()
        # use, relying on send_bytes()'s non-shared/private default since
        # this route sits behind do_GET()'s session gate (see the dispatch
        # block in do_GET() below).
        return self.send_bytes(200, "image/png", payload, cache_seconds=300)

    def _handle_illustration_replace(self, key):
        """POST /illustration/{key}.png — upload a replacement illustration
        (quick task 260902-v26, T-v26-02-*). This is the feature's entire
        security surface: the first untrusted file upload this codebase
        has ever handled. Steps run in this exact order; the ordering is
        the security property, not an implementation detail:

        1. Membership test on `key` FIRST, before any path is constructed
           or any byte of the body is read — validate-then-join, never
           sanitise-then-join, over the SAME closed set
           `_serve_illustration_image()` above already validates against
           (D-15). A traversal-shaped key is structurally unable to reach
           a path here, for exactly the reason that method's own comment
           documents. Phase 13 (D-09): the set this step consults is now
           the widened `_illustration_filenames(state_dir)` union of
           vendored and server-persisted manual keys. A manually-resolved
           key is safe to accept here for exactly one reason: it can only
           be present in the set because a prior, authenticated Step A
           request (`Handler._handle_manual_resolve_post()`) already
           persisted it to `manual_resolutions.json` — this request never
           supplies or asserts that key itself, it merely references
           already-durable server state.
        2. `_read_upload_body()` — bounded by `MAX_ILLUSTRATION_UPLOAD_
           BYTES`, draining an over-cap body so the connection is not
           left corrupted (T-v26-02-03).
        3. `parse_single_uploaded_file()` — a strict, stdlib-only,
           single-part multipart parse. The client's declared filename is
           never read by construction; the destination filename is always
           the already-membership-validated URL key, never anything from
           the request (T-v26-02-01).
        4. Write the raw payload to a temp file inside this key's override
           directory, named from the validated key plus this process's
           pid (never from the request), then run `illustrations.
           validate_illustration_file()` against it — the SAME validation
           every vendored illustration is held to (D-03/D-04). A non-empty
           problem list rejects the upload; the problem strings (which
           carry the server-side temp path) go to the service log only,
           never into the response (T-v26-02-08).
        5. Only once validated: decode with Pillow, convert to RGBA, and
           re-encode to a second temp file in the same directory. The
           client's original bytes are NEVER stored — this route only
           ever writes bytes this server's own Pillow encoder produced,
           so `_serve_illustration_image()` above (and, after the next
           poll cycle, the panel compositor via `select_illustration()`)
           only ever decode server-produced bytes, never a remote
           client's. This also strips any ancillary chunk, trailing
           appended data, or polyglot payload the original upload may
           have carried (T-v26-02-05).
        6. `os.replace()` the re-encoded temp onto the override path —
           atomic on one filesystem, since both temps live in the same
           override directory as the destination (T-v26-02-09) — then
           redirect with the success flash. Every failure branch unlinks
           both temp files before redirecting with the appropriate flash.

        No CSRF token: the session cookie's `SameSite=Strict` flag is this
        site's documented CSRF control for every state-changing POST
        (companion/auth.py:132) — this route follows that same,
        already-established posture (matching `POST /settings` and
        `POST /poll-now`) rather than inventing a second mechanism for
        itself alone (T-v26-02-07, accepted risk).
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
        """POST /airlines/resolve — Step A of the two-step resolve flow
        (phase 13, D-03/D-07/D-11). An `app.py`-owned handler, sibling to
        `_handle_poll_now()` and `_handle_illustration_replace()` above
        rather than a page module's `handle_post()`, because it must
        choose between two redirect targets and the documented
        `handle_post(form, ctx) -> flash_key` contract
        (companion/pages/__init__.py) returns only a flash key. Body runs
        in this exact order:

        1. Read the form and the state dir.
        2. `unresolved_row_for_prefix()` — D-11's single membership test,
           re-run here rather than trusted from the hidden `prefix`
           field, exactly matching `server/device_config.py`'s own
           re-validate-on-write discipline (`save_device_config()`). A
           `None` result means the prefix is not a live member of the
           unresolved-callsign-prefix registry right now — nothing is
           written and nothing else runs; the operator lands back on
           Airlines with the stale flash. Every value used downstream
           (the write, both possible redirects) comes from the validated
           tuple's own `row[0]`, never the raw form string (T-13-08).
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
           the name that was JUST persisted (re-read via `load_manual_
           resolutions()`, never the form value — the stored value is the
           authority, T-13-08). When `illustrations.resolved_illustration_
           path()` already resolves for that key (D-03: the named airline
           already has artwork, so no upload is ever asked for), redirect
           to `AIRLINES_ROUTE?flash=manual_resolved`; otherwise redirect
           to `AIRLINES_ROUTE?resolve={prefix}&flash=manual_resolved` so
           the page renders Step B. Both branches carry the success
           flash, which tells the operator the change reaches the frame
           at its next wake, never that it is instant (13-UI-SPEC.md's
           latency-honesty obligation).

        Every interpolated value in a redirect `Location` passes through
        `quote()`, matching the existing `quote(FLASH_KEY_...)` discipline
        at every other redirect in this file.

        No CSRF token: the session cookie's `SameSite=Strict` flag is this
        site's documented CSRF control for every state-changing POST
        (companion/auth.py:132) — this route follows that same,
        already-established posture (matching `POST /settings`,
        `POST /poll-now`, and `POST /illustration/{key}.png`) rather than
        inventing a second mechanism for itself alone (T-13-07, accepted
        risk).
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
            # 13-UAT.md G-01: add_entry() collapses "field was empty" and
            # "field was supplied but illustration_key_for_name() returned
            # None" onto this one result code (its own docstring steps 2
            # and 3). Distinguish them here, at the presentation layer
            # only, by re-reading the same raw posted value already passed
            # to add_entry() two lines above — never a second read_form()
            # call, never a re-derivation of manual_resolutions.py's own
            # regex/validation logic.
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
        """POST /airlines/manual-resolutions/{prefix}/delete (phase 13,
        D-08). Deliberately does NOT membership-test `key` against the
        unresolved-prefix registry the way `_handle_manual_resolve_post()`
        above does: D-14 removes a prefix from that registry as soon as it
        resolves, so gating delete on it would make an entry undeletable
        the moment it started working — the exact opposite of D-08's
        recoverability goal. The safety property here is different and
        sufficient: `key` is normalised and used only as a dict key into
        `manual_resolutions.json`, never joined into a filesystem path,
        and `delete_entry()` touches nothing but that one JSON file (D-08)
        — it cannot reach, and never reaches, the illustration override
        directory (T-13-10).

        A malformed prefix (fails `normalise_prefix()`) 404s without
        touching the registry. Deleting an already-absent prefix is a
        success, not an error — idempotent double-submission tolerance,
        matching this codebase's existing posture — so no flash on a
        second, identical POST either. Only a genuine write failure on a
        prefix that WAS present gets `FLASH_KEY_MANUAL_DELETE_FAILED`; the
        row's disappearance from the management list is otherwise the
        only confirmation (13-UI-SPEC.md's copy deck has no delete-success
        string by design).
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
        """POST /settings/rules/add (Phase 15 D-10, D-11, 15-05-PLAN.md):
        the per-flight colour-rules editor's immediate add route,
        following `_handle_manual_resolve_post()`'s shape above — an
        immediate action outside SETTINGS_ROUTE and the settings form's
        unsaved-changes dirty bar.

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
        query parameter (D-09's "make replaced legible" requirement);
        the rejected-key result to the key-invalid key; the full result
        to the registry-full key. A crafted `rule_kind` or
        `rule_theme_id` (the rejected-kind/rejected-theme results) is a
        hostile-request shape, not a genuine user mistake, and reuses
        the generic save-failed key rather than earning its own message
        (15-UI-SPEC.md's own explicit asymmetry) — the failed result and
        any other unrecognised result map to the same generic key.

        No CSRF token: the session cookie's `SameSite=Strict` flag is
        this site's documented CSRF control for every state-changing
        POST (companion/auth.py:132), matching every other route in
        this file rather than inventing a second mechanism for this
        route pair alone (T-15-13, accepted risk).
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
                "%s?flash=%s" % (DEVICE_ROUTE, quote(FLASH_KEY_RULE_ADDED)))
        if result == colour_rules.ADD_OK_REPLACED:
            # Both segments are already known-valid at this point (that is
            # exactly why add_rule() returned ADD_OK_REPLACED rather than
            # a rejection) — re-derived here, never trusted from the raw
            # form value, matching T-15-14's validate-then-echo discipline.
            normalised_kind = colour_rules.normalise_rule_kind(submitted_kind)
            normalised_value = colour_rules.normalise_rule_value(
                normalised_kind, submitted_key)
            return self.redirect(
                "%s?flash=%s&rule=%s"
                % (DEVICE_ROUTE, quote(FLASH_KEY_RULE_REPLACED),
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
        return self.redirect("%s?flash=%s" % (DEVICE_ROUTE, quote(flash_key)))

    def _handle_rule_delete(self, kind, value):
        """POST /settings/rules/{kind}/{value}/delete (Phase 15 D-10,
        T-15-01, 15-05-PLAN.md): mirrors `_handle_manual_resolution_
        delete()`'s shape above, with the one extra normalisation step
        this route's two-segment path needs. Both `kind` and `value` are
        re-normalised through `colour_rules.normalise_rule_kind()`/
        `normalise_rule_value()` BEFORE either is ever used as a registry
        lookup — an unrecognised kind or a malformed value 404s without
        touching the registry, never a lookup against a request-supplied
        string (T-15-01).

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
                "%s?flash=%s" % (DEVICE_ROUTE, quote(FLASH_KEY_RULE_DELETED)))
        if existed:
            return self.redirect(
                "%s?flash=%s" % (DEVICE_ROUTE, quote(FLASH_KEY_RULE_DELETE_FAILED)))
        return self.redirect(DEVICE_ROUTE)

    def _handle_calendar_disconnect_post(self):
        """POST /settings/calendar/disconnect (19-11-PLAN.md Task 1,
        D-08/A-26): the calendar disconnect action's own dedicated,
        session-gated route — a sibling of `_handle_rule_add_post()`/
        `_handle_rule_delete()` above, following their identical
        gate-then-dispatch shape in `do_POST()` (`require_session()` is
        checked there, before this method is ever called).

        Two-step confirmation, server-side: a bare POST, or one carrying
        any confirm value other than
        `config_page.CALENDAR_DISCONNECT_CONFIRM_VALUE`, renders
        `config_page.calendar_disconnect_confirm_page(ctx)` directly at
        200 and returns WITHOUT touching anything — the native
        `confirm()` `companion/static/confirm-submit.js` shows (Task 2)
        is a misclick guard only, never the security control; this
        branch is what holds against a hand-crafted request or a
        no-JS/CSP-blocked browser. Only an EXACT match on the accepted
        confirm value proceeds to call
        `calendar_rules.save_calendar_url(state_dir, calendar_rules.
        CLEAR_CALENDAR_URL)` — the single existing disconnect writer
        (`server/plane/calendar_rules.py`), never a reimplementation.
        That writer's own identity-only sentinel comparison is what
        takes the "clear" path rather than the ordinary "set a URL"
        path.

        The writer's boolean result is branched on explicitly, matching
        `_handle_rule_add_post()`'s own never-a-dict-lookup discipline:
        success redirects to the Device page with the existing
        `FLASH_KEY_CALENDAR_DISCONNECTED` key (already used by the
        retired in-form path, unchanged copy); failure redirects with
        the existing generic `FLASH_KEY_CALENDAR_SYNC_FAILED` key rather
        than inventing a second failure message for what is, from the
        operator's point of view, the same "couldn't touch the
        calendar's stored state" failure.

        This route never calls `config_page.submitted_calendar_signal()`:
        that resolver exists to interpret a `calendar_url`/
        `calendar_disconnect` PAIR submitted alongside the rest of the
        settings form, and this route's only possible meaning is
        "disconnect" once its own confirm gate passes (see that
        resolver's own docstring for the decision record).
        """
        form = self.read_form()
        confirm = form.get(config_page.CALENDAR_DISCONNECT_CONFIRM_FIELD)
        if confirm != config_page.CALENDAR_DISCONNECT_CONFIRM_VALUE:
            ctx = self.page_context()
            body = config_page.calendar_disconnect_confirm_page(ctx)
            return self.send_html(200, self._page_shell_for(DEVICE_ROUTE, body, ctx))
        state_dir = self.args.state_dir
        if calendar_rules.save_calendar_url(
                state_dir, calendar_rules.CLEAR_CALENDAR_URL):
            return self.redirect(
                "%s?flash=%s" % (DEVICE_ROUTE, quote(FLASH_KEY_CALENDAR_DISCONNECTED)))
        return self.redirect(
            "%s?flash=%s" % (DEVICE_ROUTE, quote(FLASH_KEY_CALENDAR_SYNC_FAILED)))

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
        on every GET, and `_handle_settings_post()`'s D-07 rejected-save
        branch (19-07-PLAN.md Task 3) also needs on a POST — factored out
        here so the failure branch, which already has its own `ctx` and
        already built its own `body` via a direct `config_page.render()`
        call, reuses this shell assembly instead of a second literal
        `page_shell()` call site. `_render_tab()` itself cannot be reused
        directly for that branch: it unconditionally re-checks
        `require_session()` (already checked once in `do_POST()` before
        dispatch) and always calls `render(ctx)` itself with no way to
        pass through an already-rendered body carrying `errors`/
        `submitted`.
        """
        flash_html = (
            layout.flash_banner(ctx["flash"], role=ctx["flash_role"])
            if ctx["flash"] else None)
        return layout.page_shell(
            title=_PAGE_TITLES[route], active=layout.nav_slug(route), body=body,
            ui_theme=ctx["ui_theme"], flash=flash_html,
            health_alert=ctx["health_severity"])

    def _render_tab(self, route, render):
        """Render one authenticated tab: `render(ctx) -> body markup`
        (a page module's render(), or a lambda binding a scope onto
        config_page.render()) wrapped in layout.page_shell(). Phase 18
        revived this from dead code so the six live routes share one
        body instead of six copies of it.
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
            # 06.6.2-07 (UXA-03): a `?next=` query value survives the
            # require_session() redirect round-trip; validated here too
            # (not only on the POST path) so an unrecognised value never
            # even renders a hidden field for the user to resubmit.
            next_route = _validated_next_route(
                parse_qs(parsed.query).get("next", [None])[0])
            return self.send_html(200, self._render_login_page(next_route=next_route))

        if path == STYLE_ROUTE:
            return self._serve_stylesheet()

        # Pre-auth, matching /static/style.css: a static asset carries no
        # per-user or sensitive data, so gating it would add a session
        # round-trip for zero benefit (06.5-RESEARCH.md, Security Domain,
        # V2/V4 both "no"). NAV_SCRIPT_ROUTE (06.6.1-05) below is the same
        # reasoning, not a second justification.
        if path == SCRIPT_ROUTE:
            return self._serve_battery_trend_script()

        if path == NAV_SCRIPT_ROUTE:
            return self._serve_nav_dropdown_script()

        # 06.6.3: four more pre-auth static routes, same reasoning as
        # NAV_SCRIPT_ROUTE immediately above — a static asset carries no
        # per-user data, so gating it would add a session round-trip for
        # zero benefit.
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

        # Phase 18: the six live tabs, each through _render_tab() above.
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

        # Phase 18: the pre-refactor page routes survive as fixed 303s so
        # a stale bookmark or link still lands somewhere useful. The
        # targets are literals, never derived from any request value —
        # the same reasoning PREVIEW_PAGE_ROUTE's own redirect below has
        # always documented.
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
            # D-22: the Preview page is retired — History (now Flights)
            # absorbed all of its content (06.6.4.1-05) — so this route
            # exists solely to send a stale bookmark/link somewhere
            # useful. Fixed literal target, never a request value.
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

    def _handle_login_post(self):
        # 06.6.2-07 (UXA-03/T-06.6.2-12): read and validate `next` before
        # the lockout/password checks so it survives every branch below
        # (lockout, incorrect password, and success) — a failed attempt
        # must not lose the originally-requested destination.
        form = self.read_form()
        next_route = _validated_next_route(form.get("next"))
        if LOGIN_THROTTLE.locked_out():
            remaining = LOGIN_THROTTLE.seconds_remaining()
            return self.send_html(429, self._render_login_page(
                lockout_seconds=remaining, next_route=next_route))
        submitted = form.get("password", "")
        if auth.password_ok(submitted):
            LOGIN_THROTTLE.record_success()
            token = auth.issue_session_token()
            return self.redirect(
                next_route or HOME_ROUTE,
                set_cookie=auth.session_set_cookie_header(token))
        LOGIN_THROTTLE.record_failure()
        return self.send_html(401, self._render_login_page(
            error="Incorrect password. Try again.", next_route=next_route))

    def _handle_settings_post(self):
        """POST /settings — an app.py-owned handler (D-06/D-09), a
        sibling of `_handle_poll_now()` and `_handle_manual_resolve_
        post()` above, because this write path must choose between more
        than one outcome and the documented `handle_post(form, ctx) ->
        flash_key` contract (companion/pages/__init__.py) returns only a
        single key. Adds no route and no new gate — the session gate
        stays exactly where it was, in `do_POST()`, before dispatch.

        Body, in order:

        1. `config_page.handle_post()`, now called with an `errors={}`
           keyword — every existing field validation and the
           device-config/secret-file writes, completely unchanged from
           before this plan, now also filling that dict in place on any
           rejection.
        2. (19-07-PLAN.md Task 3, D-07/A-25) When `errors` came back
           non-empty, render the SAME scoped page directly at 200 with
           the user's own submission still in the fields and each
           offending control's own message — mirroring
           `_handle_login_post()`'s own 200-on-failure-render precedent
           (`_render_login_page()`/`self.send_html(401, ...)` above),
           the only other place in this codebase that renders instead of
           redirecting on a rejected form. Deliberately no flash banner
           on this branch: the whole point of D-07 is that the message
           lives at the field, and a duplicate top-of-page banner would
           restate it. 200, not 422: D-07's own text says "renders the
           page directly (200) on validation failure", and unlike
           `_handle_login_post()`'s 401 (which carries real auth
           meaning), this rejection carries none — a 200 also keeps the
           browser's back/forward history sane for a form the user is
           still actively editing.
        3. Any OTHER non-`FLASH_KEY_SAVED` result — a failure path that
           somehow produced no field error — falls through to the
           pre-existing redirect-with-flash behaviour, unchanged, so no
           rejection can ever fall through silently. No fetch is ever
           attempted on a rejected save, by either branch.
        4. `config_page.submitted_calendar_signal()` — the SAME resolver
           `handle_post()` itself just consulted, called again here
           (never re-derived) so persistence and this sync decision can
           never disagree about what the submission meant. `carry_
           forward` (or anything the resolver did not itself return,
           which cannot happen but is treated identically rather than
           assumed away) redirects with the ordinary saved key — this
           branch is byte-identical in observable behaviour to before
           this plan, because it is the branch every settings save that
           touches no calendar field takes.
        5. `clear` — no fetch: there is nothing to fetch, and the erase
           already happened inside `handle_post()`'s own call to
           `calendar_rules.save_calendar_url()`.
        6. `set` — D-09: acquire `_POLL_LOCK`, the SAME lock `_handle_
           poll_now()` uses, with the same non-blocking acquire, rather
           than a second lock. Corrected 2026-09-10 (CR-01/IN-01, Phase
           17 review): this bullet previously claimed `_POLL_LOCK`
           closes the race against "a poll cycle's own calendar
           refresh" — that is false. `_POLL_LOCK` is a plain
           `threading.Lock()` living in THIS process's memory; it only
           ever serializes this call against another concurrent request
           in the SAME companion process (a simultaneous `/poll-now`, or
           a second `/settings` POST). `skypane-poll.service`'s own
           refresh cycle is a separate OS process with its own,
           unrelated copy of every lock in this file — `_POLL_LOCK` is
           invisible to it, no matter how it is reused. The actual
           cross-process protection against that race now lives inside
           `calendar_rules.refresh_calendar_registry()` and
           `calendar_rules.save_calendar_url()` themselves, via
           `calendar_rules._calendar_registry_lock()` — an
           `fcntl.flock()`-based lock over a dedicated file in
           `state_dir`, acquired around each function's entire
           read-modify-write sequence, and visible to any process,
           including the poll service. `_POLL_LOCK` is still acquired
           here, and is still correct for what it actually does: on
           contention with another *companion* request, the deferred
           key is the honest answer that the save landed and the sync
           did not run in this request.
        7. Inside the lock: `calendar_rules.refresh_calendar_registry()`
           directly — never `poll_loop.run_once()`, which would run a
           full detection/render cycle this save has no need for — with
           `min_interval_s=0`. Zero, not omitted: omitting it resolves
           to the standard throttle interval, which is the exact silent
           no-op D-06 exists to prevent, and it produces no error and no
           log line to reveal itself. The lock is released in a
           `finally` covering every path out of this branch, so one
           failed sync cannot wedge a later manual poll trigger.

        No handler wraps the refresh call, and nothing in this method
        ever reads the text of a caught error. `refresh_calendar_
        registry()` is contractually never-raising — it carries its own
        top-level catch-all that falls back to whatever is durably on
        disk. A handler here would be dead code with one live
        consequence: the moment anything touched a caught value, the
        full request URL would be back in a message, because that is
        what network and name-resolution error strings routinely
        contain (T-17-FLASH).

        The returned `(result_code, registry)` is branched on
        explicitly, matching `_handle_manual_resolve_post()`'s own
        recorded reasoning that an unrecognised value must not be able
        to fall through with no outcome at all: the success constant
        redirects with the connected key, and every other value —
        including the two that cannot actually fire from here,
        `FETCH_SKIPPED_THROTTLED` (impossible because the interval is
        zero) and `FETCH_SKIPPED_UNCONFIGURED` (impossible because the
        write just succeeded) — maps to the single failure key rather
        than being assumed away.

        The manual poll trigger's own cooldown machinery (the pair of
        helpers `_handle_poll_now()` consults and updates above) is
        neither consulted nor updated anywhere in this method: this is
        not a poll, it renders nothing and drives no panel, and
        borrowing that cooldown would let an unrelated settings save
        block a real poll trigger for its duration.
        """
        state_dir = self.args.state_dir
        form = self.read_form()
        ctx = self.page_context()
        errors = {}
        flash_key = config_page.handle_post(form, ctx, errors=errors)
        # Phase 18: land back on the scoped page the form came from.
        back = config_page.submitted_return_route(form)
        # 19-07-PLAN.md Task 3 (D-07/A-25): a rejected save with at least
        # one field-level error re-renders the SAME scoped page directly
        # at 200, carrying the user's own submission and each control's
        # own message — never a redirect. See this method's own
        # docstring bullet 2 for the full reasoning (the 401-vs-200
        # distinction from _handle_login_post(), and why no flash banner
        # is set here).
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
            return self.redirect(
                "%s?flash=%s" % (back, quote(FLASH_KEY_CALENDAR_DISCONNECTED)))
        if calendar_signal != config_page.CALENDAR_URL_SIGNAL_SET:
            # carry_forward — an unrelated settings save. No fetch, no
            # lock acquisition: byte-identical to today's behaviour.
            return self.redirect("%s?flash=%s" % (back, quote(FLASH_KEY_SAVED)))

        if not _POLL_LOCK.acquire(blocking=False):
            return self.redirect(
                "%s?flash=%s" % (back, quote(FLASH_KEY_CALENDAR_SYNC_DEFERRED)))
        try:
            result_code, _registry = calendar_rules.refresh_calendar_registry(
                state_dir, poll_loop.now_s(), min_interval_s=0)
        finally:
            _POLL_LOCK.release()

        if result_code == calendar_rules.FETCH_OK:
            return self.redirect(
                "%s?flash=%s" % (back, quote(FLASH_KEY_CALENDAR_CONNECTED)))
        return self.redirect(
            "%s?flash=%s" % (back, quote(FLASH_KEY_CALENDAR_SYNC_FAILED)))

    def _handle_poll_now(self):
        # Phase 18: the trigger lives on Home (Refresh now) and on Device
        # (Poll); redirect back to whichever page posted it.
        back = self._referring_tab()
        # UXA-15: non-blocking acquire, never a timeout (06.6.2-RESEARCH.md).
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
                return self.redirect(
                    "%s?flash=%s" % (back, quote(FLASH_KEY_POLL_COOLDOWN)))
            try:
                # Pattern 3 (06-RESEARCH.md): the exact production code
                # path the systemd timer already runs, in-process — never
                # a second process and never a re-parsed subprocess
                # result.
                poll_loop.run_once(state_dir=state_dir, geofence=self.args.geofence)
            except Exception:
                return self.redirect(
                    "%s?flash=%s" % (back, quote(FLASH_KEY_POLL_FAILED)))
            mark_poll_triggered(state_dir)
            return self.redirect(
                "%s?flash=%s" % (back, quote(FLASH_KEY_POLL_TRIGGERED)))
        finally:
            # Always released — including on the except Exception: branch
            # above, which must stay inside this try so a failed poll
            # still releases the guard for the next attempt (never a
            # permanently wedged trigger, T-06.6.2-05).
            _POLL_LOCK.release()

    def _handle_quick_toggle(self, field):
        """Phase 18: the Home page's one-tap switches — POST /quick/display
        and POST /quick/quiet-hours. The body carries exactly one field,
        `state`, whose value is the state to switch TO ("on"/"off"), so a
        repeated submission is idempotent. Every other device-config
        value is carried forward untouched (save_device_config() treats
        a None keyword as "leave unchanged"), which is what makes this
        safe to expose to someone who never opens the settings pages.
        Session-gated in do_POST() like every other state-changing
        route.
        """
        form = self.read_form()
        state = form.get(home_page.QUICK_STATE_FIELD)
        if state not in (home_page.QUICK_STATE_ON, home_page.QUICK_STATE_OFF):
            return self.redirect(
                "%s?flash=%s" % (HOME_ROUTE, quote(FLASH_KEY_QUICK_FAILED)))
        enabled = state == home_page.QUICK_STATE_ON
        if field == "display_enabled":
            kwargs = {"display_enabled": enabled}
            flash_key = FLASH_KEY_DISPLAY_ON if enabled else FLASH_KEY_DISPLAY_OFF
        else:
            kwargs = {"quiet_hours_enabled": enabled}
            flash_key = FLASH_KEY_QUIET_ON if enabled else FLASH_KEY_QUIET_OFF
        try:
            device_config.save_device_config(self.args.state_dir, **kwargs)
        except (ValueError, OSError):
            flash_key = FLASH_KEY_QUICK_FAILED
        return self.redirect("%s?flash=%s" % (HOME_ROUTE, quote(flash_key)))

    def _handle_theme_post(self):
        form = self.read_form()
        submitted = form.get("ui_theme")
        cookie_header = None
        if submitted in layout.UI_THEME_CHOICES:
            # A-34/D-17: routed through auth.secure_cookie_flag() so this
            # cookie and the session cookie cannot drift on the Secure flag.
            cookie_header = (
                "%s=%s; HttpOnly%s; SameSite=Strict; Path=/; Max-Age=%d"
                % (auth.UI_THEME_COOKIE_NAME, submitted, auth.secure_cookie_flag(),
                   THEME_COOKIE_MAX_AGE_S))
        return self.redirect(self._referring_tab(), set_cookie=cookie_header)

    def do_POST(self):
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

        # 19-04-PLAN.md (D-18/A-35, T-19-04): gated like every other
        # state-changing route above — an unauthenticated caller setting
        # another visitor's UI theme cookie is a real state change, not
        # a cosmetic no-op.
        if path == THEME_ROUTE:
            if not self.require_session():
                return None
            return self._handle_theme_post()

        # 19-04-PLAN.md (D-18/A-35, T-19-04): gated too, even though an
        # unauthenticated POST /logout looks harmless at first glance —
        # it is a CSRF-shaped forced-sign-out of whoever holds the
        # session, and gating it costs a signed-out caller nothing since
        # they are already signed out. A-33/D-16 (plan 19-02): also
        # revokes the presented token server-side before clearing the
        # client's cookie, so replaying the same cookie value after Sign
        # out no longer verifies.
        if path == LOGOUT_ROUTE:
            if not self.require_session():
                return None
            token = auth.parse_cookies(
                self.headers.get("Cookie")).get(auth.SESSION_COOKIE_NAME)
            if token:
                auth.revoke(token)
            return self.redirect(LOGIN_ROUTE, set_cookie=auth.logout_set_cookie_header())

        # Phase 13 plan 13-06: Step A of the two-step resolve flow (D-03,
        # D-11) — the session gate runs first, before any registry read or
        # write, matching every other authenticated branch here.
        if path == airlines_page.RESOLVE_ROUTE:
            if not self.require_session():
                return None
            return self._handle_manual_resolve_post()

        # Phase 13 plan 13-06 (D-08): mirrors the illustration-prefix
        # branch's own slice-arithmetic shape below, but with a prefix AND
        # a suffix (the prefix segment is a dict key, not a filename).
        if path.startswith(airlines_page.MANUAL_DELETE_ROUTE_PREFIX) and path.endswith(
                airlines_page.MANUAL_DELETE_ROUTE_SUFFIX):
            if not self.require_session():
                return None
            key = path[
                len(airlines_page.MANUAL_DELETE_ROUTE_PREFIX):
                -len(airlines_page.MANUAL_DELETE_ROUTE_SUFFIX)]
            return self._handle_manual_resolution_delete(key)

        # quick task 260902-v26: mirrors the GET dispatch's own
        # ILLUSTRATION_IMAGE_ROUTE_PREFIX branch above byte for byte — same
        # prefix constant, same ".png" suffix test, same require_session()
        # gate first, same slice arithmetic.
        if path.startswith(ILLUSTRATION_IMAGE_ROUTE_PREFIX) and path.endswith(".png"):
            if not self.require_session():
                return None
            key = path[len(ILLUSTRATION_IMAGE_ROUTE_PREFIX):-len(".png")]
            return self._handle_illustration_replace(key)

        # Phase 15 D-10 (15-05-PLAN.md): the rules editor's two immediate
        # POST routes, behind the same require_session() gate as every
        # other state-changing route above — no new auth mechanism and no
        # CSRF token, inheriting the site-wide session gate and the
        # SameSite=Strict cookie control uniformly applied here.
        if path == RULES_ADD_ROUTE:
            if not self.require_session():
                return None
            return self._handle_rule_add_post()

        # 19-11-PLAN.md Task 1 (D-08/A-26): the calendar disconnect
        # action's own dedicated route, gated identically to every other
        # state-changing route above.
        if path == CALENDAR_DISCONNECT_ROUTE:
            if not self.require_session():
                return None
            return self._handle_calendar_disconnect_post()

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
        # string (T-06-05-08); the query string is stripped here even
        # though self.path may carry one (e.g. a flash-key redirect).
        print("%s %s" % (self.command, urlsplit(self.path).path))


def build_parser():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
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
    server = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    print("companion: serving on port %d (state_dir=%s)" % (args.port, args.state_dir))
    server.serve_forever()


if __name__ == "__main__":
    main()
