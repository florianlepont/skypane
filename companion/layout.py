"""companion/layout.py — the escaped page shell and 06-UI-SPEC.md's
component library for the SkyPane companion service.

stdlib `html` and `datetime` only — no imports from server/, and
nothing from companion.auth beyond the UI-theme cookie name.

06-RESEARCH.md's Pitfall 2: stdlib string formatting has no
autoescaping, so every interpolation site is a manual opt-in.
`escape_html()` is defined once, here, and every `companion/pages/*.py`
module (plans 06-05 through 06-09) must import and use it — no page
module may reach into the stdlib `html` module's escaping function
directly, and no page module may build markup without going through
this one helper. That single-helper discipline is what makes the
escaping obligation auditable with one grep across the whole package.
"""
import html
from datetime import datetime
from zoneinfo import ZoneInfo

from companion.auth import UI_THEME_COOKIE_NAME
# 20-01-PLAN.md Task 2/3 (D-01..D-09): companion.i18n/companion.prefs
# are both shared, page-independent modules (like companion.auth
# above) — layout.py importing them carries no cycle, since neither
# imports anything from this module or from companion.app
# (companion.app is the one that imports layout.py, never the
# reverse).
import companion.i18n as i18n
import companion.prefs as prefs
# 22-04-PLAN.md Task 1 (D-03/CFG-26): companion.wake/companion.frame_state
# are both shared, page-independent modules exactly like companion.auth/
# companion.i18n/companion.prefs above — importing them carries no cycle
# (neither imports companion.layout), and R-01 (this module's own docstring)
# is respected: companion.wake is a thin shim over server/wake.py, never a
# direct server/ import from here. frame_strip_html() below is the one
# consumer of both, so the strip's headline/dot/delay-sentence decision is
# resolved by companion.frame_state.resolve_state(), never re-derived here.
import companion.wake as wake
import companion.frame_state as frame_state

SITE_TITLE = "SkyPane"

# Phase 18 (audit finding H-3/H-4): every timestamp used to render as a
# bare UTC clock ("21:50 UTC") with the date hidden in a tooltip. The
# household this frame hangs in lives on Paris time, so visible
# timestamps now render in LOCAL_TZ, and carry the day once the value
# is no longer "today" ("3 Sep 21:50"). 22-06-PLAN.md Task 3 (D-05, B4):
# the `title` attribute used to carry the raw ISO string instead — the
# one place this rule did not reach — and now carries a local FULL
# timestamp (see `_FULL_TIMESTAMP_SENTINEL_NOW` below) instead; the raw
# ISO no longer appears in any `title` this module renders.
LOCAL_TZ = ZoneInfo("Europe/Paris")
_MONTH_ABBR = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
# D-07, 20-03-PLAN.md Task 2: the French month-abbreviation table
# local_clock_text() selects instead of _MONTH_ABBR above under a
# French request — same twelve-entry shape, parallel index.
_MONTH_ABBR_FR = ("janv.", "févr.", "mars", "avr.", "mai", "juin",
                   "juil.", "août", "sept.", "oct.", "nov.", "déc.")

# Ordered (route, label) pairs — 06-UI-SPEC.md's Page Inventory. Login is
# deliberately absent: it is shown instead of any page when unauthenticated,
# never as a nav tab.
# Companion audit / UX refactor (phase 18): the flat four-tab set is
# replaced by two GROUPS of tabs — the everyday group (no label) that a
# household member uses without any technical background, and an
# "Advanced" group for setup, diagnostics and debugging. Each entry is
# (route, label). NAV_TABS below is DERIVED from this tuple so every
# existing consumer of the flat (route, label) sequence (the login
# `?next=` allowlist, `_referring_tab()`, the page-title map guard, both
# nav renderers) keeps working unchanged.
HOME_ROUTE = "/"
DISPLAY_ROUTE = "/display"
FLIGHTS_ROUTE = "/flights"
AIRLINES_ROUTE = "/airlines"
HEALTH_ROUTE = "/health"
DEVICE_ROUTE = "/device"

ADVANCED_GROUP_LABEL = "Advanced"

NAV_GROUPS = (
    ("", (
        (HOME_ROUTE, "Home"),
        (DISPLAY_ROUTE, "Display"),
        (FLIGHTS_ROUTE, "Flights"),
        (AIRLINES_ROUTE, "Airlines"),
    )),
    (ADVANCED_GROUP_LABEL, (
        (HEALTH_ROUTE, "Health"),
        (DEVICE_ROUTE, "Device"),
    )),
)

# Ordered (route, label) pairs, flattened from NAV_GROUPS in display
# order. Login is deliberately absent: it is shown instead of any page
# when unauthenticated, never as a nav tab. The old "/settings" and
# "/history" routes are not tabs any more — companion/app.py keeps both
# as fixed 303 redirects (to DISPLAY_ROUTE and FLIGHTS_ROUTE) so a stale
# bookmark still lands somewhere useful.
NAV_TABS = tuple(
    (route, label) for _group_label, entries in NAV_GROUPS for route, label in entries)

# The slug a route is identified by inside the nav renderers and by
# page_shell()'s `active` argument. The home route "/" has no path
# segment to strip, so it gets an explicit slug rather than "".
HOME_NAV_SLUG = "home"


def nav_slug(route):
    """The `active` slug for a NAV_TABS route: "home" for HOME_ROUTE,
    otherwise the route with its leading slash removed."""
    if route == HOME_ROUTE:
        return HOME_NAV_SLUG
    return route.lstrip("/")


# --- 06.6.1-05: hamburger nav DOM contract (D-06) -----------------------
#
# The exact literals companion/static/nav-dropdown.js looks up via
# getElementById()/classList. Duplicated here rather than imported from
# that JS file — there is no such import path, a Python module cannot
# import a JS file — so if any of these three drifts from the JS file's
# own literals, the menu silently stops opening on a phone with no
# automated signal from either file in isolation. The Task 3 three-file
# DOM contract guard (06.6.1-05-PLAN.md) reads the JS source and the
# stylesheet from disk and requires all three to appear in both AND in
# the rendered page.
NAV_TOGGLE_ID = "site-nav-toggle"
MOBILE_NAV_ID = "mobile-nav"
MOBILE_NAV_OPEN_CLASS = "mobile-nav--open"

# The fixed accessible name for the hamburger toggle button
# (06.6.1-UI-SPEC.md's Copywriting Contract). State is communicated
# entirely through aria-expanded, which is the correct ARIA disclosure
# pattern — swapping this label to a close verb on open would make the
# announced name change under the user mid-interaction. Do not add logic
# that varies it BY STATE — it is still translated through i18n.t() at
# its one render site (D-05, 20-12-PLAN.md Task 1: a real completeness
# gap this constant's own render site had left un-wrapped).
# 22-14-PLAN.md Task 2 (X9/D-10, 22-UI-SPEC.md §3.1): renamed from
# "Open menu". The panel this toggle controls no longer holds a menu of
# pages at all — the bottom tab bar owns destinations now, and what is
# left behind the hamburger is the state reminder plus the language,
# theme and Sign out controls. An accessible name that describes
# something the control no longer opens is the same class of defect as
# B10's own "go to Home" label on the Home page, so it is corrected in
# the same plan that causes it rather than left to drift.
NAV_TOGGLE_LABEL = "Account and preferences"

# Must equal companion/app.py's NAV_SCRIPT_ROUTE exactly. Duplicated
# rather than imported because companion/pages/__init__.py's boundary —
# and a plain import cycle, since app.py imports this module — forbids
# the reverse direction, exactly as health_page.BATTERY_TREND_SCRIPT_SRC's
# own comment already states for its own route pair. The Task 3 checks
# assert the equality.
NAV_DROPDOWN_SCRIPT_SRC = "/static/nav-dropdown.js"

# 06.6.3: four more pre-auth static JS route constants, same
# duplicated-not-imported contract as NAV_DROPDOWN_SCRIPT_SRC above —
# each must equal companion/app.py's matching *_SCRIPT_ROUTE constant
# exactly (that module's own Task 2 checks assert the equality).
DIRTY_STATE_SCRIPT_SRC = "/static/dirty-state.js"
LIST_FILTER_SCRIPT_SRC = "/static/list-filter.js"
COPY_BUTTON_SCRIPT_SRC = "/static/copy-button.js"
FRESHNESS_SCRIPT_SRC = "/static/freshness.js"

# D-20 (06.6.4.1-02): must equal companion/app.py's PANEL_LOOKUP_SCRIPT_ROUTE
# exactly, same duplicated-not-imported contract as the four constants above.
PANEL_LOOKUP_SCRIPT_SRC = "/static/panel-lookup.js"

# Quick task 260903-peo (UIR-19): must equal companion/app.py's
# FLASH_CLEANUP_SCRIPT_ROUTE exactly, same duplicated-not-imported
# contract as the constants above.
FLASH_CLEANUP_SCRIPT_SRC = "/static/flash-cleanup.js"

# 19-04-PLAN.md (D-18/A-35): must equal companion/app.py's
# POLL_COOLDOWN_SCRIPT_ROUTE exactly, same duplicated-not-imported
# contract as the constants above.
POLL_COOLDOWN_SCRIPT_SRC = "/static/poll-cooldown.js"

# 19-11-PLAN.md Task 2 (D-08/A-26): must equal companion/app.py's
# CONFIRM_SUBMIT_SCRIPT_ROUTE exactly, same duplicated-not-imported
# contract as the constants above — the ninth static script.
CONFIRM_SUBMIT_SCRIPT_SRC = "/static/confirm-submit.js"

# 20-08-PLAN.md Task 3 (D-22..D-24/D-32): must equal companion/app.py's
# THEME_PREVIEW_SCRIPT_ROUTE exactly, same duplicated-not-imported
# contract as the constants above — the tenth static script.
THEME_PREVIEW_SCRIPT_SRC = "/static/theme-preview.js"

# 21-03-PLAN.md Task 2 (D-15/R-12): must equal companion/app.py's
# FLIGHT_ROWS_SCRIPT_ROUTE exactly, same duplicated-not-imported
# contract as the constants above — the eleventh static script.
FLIGHT_ROWS_SCRIPT_SRC = "/static/flight-rows.js"

# 22-13-PLAN.md Task 2 (X3): must equal companion/app.py's
# LOGIN_CARD_SCRIPT_ROUTE exactly, same duplicated-not-imported
# contract as the constants above — the twelfth static script, and the
# first one this app has ever loaded on its PRE-AUTH page. Every
# sibling above is emitted by page_shell(); this one is emitted by
# login_shell() alone, and page_shell() never emits it (nothing on an
# authenticated page carries a .login-form).
LOGIN_CARD_SCRIPT_SRC = "/static/login-card.js"

# 22-15-PLAN.md Task 3 (T14): must equal companion/app.py's
# SUBMIT_GUARD_SCRIPT_ROUTE exactly, same duplicated-not-imported
# contract as the constants above — the THIRTEENTH static script and the
# TWELFTH emitted by page_shell(), which is what moves the deferred-tag
# count on an authenticated page from eleven to twelve. One shared
# disable-on-submit guard for every form, replacing the one-form-only
# coverage poll-cooldown.js provided.
SUBMIT_GUARD_SCRIPT_SRC = "/static/submit-guard.js"

# 23-05-PLAN.md Task 1 (D14/CFG-34): must equal companion/app.py's
# RELATIVE_TIME_SCRIPT_ROUTE exactly, same duplicated-not-imported
# contract as the constants above — the FOURTEENTH static script and the
# THIRTEENTH emitted by page_shell(), which is what moves the deferred-tag
# count on an authenticated page from twelve to thirteen. It ticks every
# <time data-relative> element relative_time_html() below renders, so it
# is registered here rather than per page for the same reason
# submit-guard.js is: the elements come from ONE shared builder that most
# page modules reach through concise_timestamp_html() without naming, so
# no page module actually knows whether it has one.
RELATIVE_TIME_SCRIPT_SRC = "/static/relative-time.js"

UI_THEME_CHOICES = ("auto", "light", "dark")

# D-16/D-19 (20-01-PLAN.md Task 2): the quick-action form protocol,
# moved here from companion/pages/home_page.py's own identical
# constants so both companion/app.py and, from 20-07, config_page.py
# can share one home for it — a page module may never import another
# page module. home_page.py keeps its own copies untouched until
# 20-06 deletes them with the rest of Home's quick-action code; the
# two definitions are byte-identical in the meantime.
QUICK_STATE_FIELD = "state"
QUICK_STATE_ON = "on"
QUICK_STATE_OFF = "off"

# 21-04-PLAN.md Task 1 (D-01/D-02/R-01): the eleven QUICK_ACTION_*
# constants, moved here byte-identical from companion/pages/
# config_page.py — frame_strip_html() below is the ONE write site for
# both switch cells, and a page module may never import another page
# module, so home_page.py (Home's own caller) needs these from a
# shared module too. Every English VALUE is unchanged from
# config_page.py's own copy, so every French catalogue entry in
# companion/i18n_fr/display.py keeps resolving correctly — the
# catalogue is keyed by English string, not by which Python module
# defines the constant that holds it.
QUICK_ACTION_SCREEN_LABEL = "Screen"
QUICK_ACTION_ON_TEXT = "On"
QUICK_ACTION_OFF_TEXT = "Off"
QUICK_ACTION_SWITCH_ON_BUTTON = "Switch on"
QUICK_ACTION_SWITCH_OFF_BUTTON = "Switch off"
QUICK_ACTION_QUIET_LABEL = "Quiet hours"
QUICK_ACTION_QUIET_ON_TEMPLATE = "On — %s to %s"
QUICK_ACTION_QUIET_OFF_TEXT = "Off"
QUICK_ACTION_QUIET_TURN_ON_BUTTON = "Turn on"
QUICK_ACTION_QUIET_TURN_OFF_BUTTON = "Turn off"
# QUICK_ACTION_APPLIES_SENTENCE ("Applies the next time the frame wakes
# up.") is no longer USED by frame_strip_html() as of 22-04-PLAN.md
# Task 1 (D-04): it used to be a static per-control caption regardless
# of state; the one computed delay sentence below — companion/
# frame_state.py's DELAY_DUE/DELAY_HELD/DELAY_UNKNOWN, resolved from the
# SAME state result the headline reads — replaces it, and the retired
# TEXT survives only as DELAY_UNKNOWN's own wording (the honest
# no-check-in fallback; see _FRAME_DELAY_UNKNOWN_TEXT below, kept
# byte-identical to this constant on purpose). The constant itself
# stays defined (not deleted) because companion/pages/config_page.py
# and companion/test_config_page.py — both owned by plan 22-05 in this
# same wave — still reference it directly; that plan is the one that
# retires the settings form's own remaining static-caption consumer and
# this constant together, in its own commit.
QUICK_ACTION_APPLIES_SENTENCE = "Applies the next time the frame wakes up."

# 21-04-PLAN.md Task 1 (D-01): the strip's own heading. Byte-identical
# English value to home_page.FRAME_ROW_LABEL ("Frame") — both resolve
# through the SAME companion/i18n_fr/home.py catalogue entry
# ("Frame": "Cadre"), since the catalogue is keyed by the English
# string, not by which constant/module holds it. A second, separately
# named constant (rather than importing FRAME_ROW_LABEL) is required
# because layout.py may never import a page module.
FRAME_STRIP_HEADING = "Frame"

# 22-04-PLAN.md Task 1 (D-03/CFG-26): NEXT_UPDATE_TEMPLATE/
# EXPECTED_SINCE_TEMPLATE are retired as independently-named constants —
# companion/frame_state.py's HEADLINE_DUE/HEADLINE_HELD/HEADLINE_LATE are
# now the ONE canonical registry of this copy, and frame_strip_html()
# below calls frame_state.resolve_state()/headline_template() to decide
# which applies; this module never re-derives that decision.
#
# The six _FRAME_*_TEXT constants below exist ONLY because this is a
# scanned module: companion/test_i18n.py's D-08 AST scan proves a string
# is alive by tracing a real `i18n.t(SOME_MODULE_CONSTANT)` call site in
# one of a fixed list of files, and that scan cannot follow an imported
# module's attribute access (`frame_state.HEADLINE_DUE`) — frame_state.py
# is not itself in that scanned list yet (a deliberate 22-02-PLAN.md
# choice; plan 22-08 owns widening the scanner to include it, which will
# make these six local copies redundant, not wrong). Until then, keep
# every value here byte-identical to its frame_state.py counterpart —
# never independently reworded — and select among them by comparing
# frame_state.headline_template()/delay_sentence_template()'s own return
# value, so the DECISION stays sourced from that module, not re-derived
# here; only the wording's scanner-visible home is local.
_FRAME_HEADLINE_DUE_TEXT = "Next update ≈ %s"
_FRAME_HEADLINE_HELD_TEXT = "Next wake around %s · quiet hours"
_FRAME_HEADLINE_LATE_TEXT = "Expected since %s"
_FRAME_DELAY_DUE_TEXT = "Applies at the next wake, around %s."
_FRAME_DELAY_HELD_TEXT = "Applies when quiet hours end, around %s."
# Byte-identical to QUICK_ACTION_APPLIES_SENTENCE above by construction
# (same value, not a coincidence) — the retired static caption's own
# TEXT survives as exactly this one computed branch's wording.
_FRAME_DELAY_UNKNOWN_TEXT = QUICK_ACTION_APPLIES_SENTENCE

# The frame's held state reuses the app's existing neutral "off" dot
# (companion/static/style.css's own comment: "a neutral, everyday state
# ... never a problem") — never a new colour, never the warn dot
# (22-UI-SPEC.md §3.3 rule 1). "late" is `.dot--warn`; there is no
# fourth, "error" tier in the frame-state vocabulary any more (D-03
# collapses the strip's old unconditional "any lateness is a warning"
# behaviour into exactly three states).
_FRAME_DOT_CLASS_BY_STATE = {
    frame_state.STATE_DUE: "dot--ok",
    frame_state.STATE_HELD: "dot--off",
    frame_state.STATE_LATE: "dot--warn",
}

# 22-12-PLAN.md Task 1 (X8, 22-UI-SPEC.md §5 contract 4): "off" is a
# FOURTH, additive entry — never a fourth colour and never a fifth dot.
# `.dot--off` has been in companion/static/style.css since phase 21
# (D-03) and is defined there as "a neutral, everyday state ... never a
# problem"; until now the only way to reach it was to hand-build the
# span, which companion/pages/health_page.py's `_pipeline_section()`
# does for exactly that reason (its own comment says so). Adding the
# entry here means `status_dot("off", label)` now renders the neutral
# dot plus its normal visible `.dot-label`, so Health's "Only one saw
# it" row keeps the identical markup shape as its two siblings instead
# of a hand-rolled copy of this function's output.
#
# Additive by construction: no pre-existing caller of `status_dot()`,
# `status_row()` or `_health_alert_markup()` passes "off" (grep: every
# `status_row()` call site in companion/pages/ passes "ok"/"warn"/
# "error" only, and `severity` is never "off"), so every one of them is
# byte-identical to before. `_DEFAULT_STATUS_DOT_CLASS` still resolves
# an UNRECOGNISED state to the warn class, which is what
# companion/test_companion_app.py's own "not-a-real-state" fallback
# check exercises — that check is unaffected, "off" is now a
# recognised state rather than an arbitrary one.
_STATUS_DOT_CLASSES = {
    "ok": "dot--ok",
    "warn": "dot--warn",
    "error": "dot--error",
    "off": "dot--off",
}
_DEFAULT_STATUS_DOT_CLASS = _STATUS_DOT_CLASSES["warn"]

_STAT_TILE_BORDER_CLASSES = {
    "ok": "stat-tile--ok",
    "warn": "stat-tile--warn",
    "error": "stat-tile--error",
}
_DEFAULT_STAT_TILE_CLASS = "stat-tile--accent"

# quick task 260902-gjj (ISSUE 2): card_status_class()'s own whitelist,
# kept as bare suffixes (not full class names) so the caller's own base
# class never has to be typed twice.
_CARD_STATUS_SUFFIXES = {
    "ok": "--ok",
    "warn": "--warn",
    "error": "--error",
}

# --- 06.6.1-04: icon sprite (D-02) -------------------------------------
#
# The whitelist. Originally capped at exactly five ids by
# 06.6.1-UI-SPEC.md's Design System contract. 06.6.2-05 (D-17) supersedes
# that cap: five per-nav-label icons (`icon-nav-*`) are added below so
# every sidebar/mobile-nav label carries a small outline glyph — the
# whitelist grows from five to ten members, and this is now the current
# whole set again, not an incomplete one. The hamburger member is
# consumed by plan 06.6.1-05's mobile-nav toggle button; it is defined
# here anyway (rather than by that later plan) so the sprite in
# ICON_DEFS_HTML stays the single write site for every icon in the app,
# never two.
ICON_IDS = (
    "icon-device",
    "icon-pipeline",
    "icon-corroboration",
    # quick task 260902-j8w: as of this quick task, "icon-battery" has no
    # consumer anywhere in the app — companion/pages/health_page.py's
    # ICON_BATTERY constant and its one call site (the Battery-trend
    # section heading) were both removed at the developer's own
    # instruction. Retained here anyway, on purpose, not as an
    # oversight: pruning it would force a matching `<symbol>` deletion
    # below plus four assertion edits in test_companion_app.py's
    # `_icon_sprite_integrity()` (the fourteen-member count, the
    # duplicate check, the symbol-id/ICON_IDS set-equality check, and
    # the `<symbol` count) — a cross-page change to this shared
    # component, well outside a one-heading-glyph removal's scope. This
    # whitelist is an injection guard on icon_html()'s fragment
    # reference, not a usage index of what is currently rendered —
    # "icon-nav-preview" below is this file's existing precedent for
    # exactly that reading. The sprite is `display: none`
    # (companion/static/style.css's `.icon-defs` rule) and the retained
    # symbol costs roughly 200 bytes. Pruning `icon-battery` (and its
    # `<symbol>` below, and the four test_companion_app.py assertions)
    # is a real, optional follow-up the developer can take or decline —
    # not done here.
    "icon-battery",
    "icon-hamburger",
    "icon-nav-config",
    "icon-nav-health",
    "icon-nav-airlines",
    "icon-nav-history",
    # 06.6.4.1-08 (D-22): stays a whitelist member even though NAV_TABS/
    # NAV_ICON_IDS no longer reference a "preview" nav tab — its consumer
    # is now companion/pages/history_page.py's View-panel trigger button
    # (the eye glyph on each row's "View panel near this time" control),
    # not a nav tab. Do not remove this as apparently-orphaned: an id
    # outside this whitelist makes icon_html() silently return "" and the
    # trigger button would render an empty box with no error.
    "icon-nav-preview",
    "icon-nav-home",
    "icon-nav-flights",
    "icon-nav-device",
    "icon-nav-display",
    "icon-power",
    "icon-moon",
)

# 06.6.3: four more icons for the per-page redesign plans (D-05/D-23/
# D-12/D-20) grow the whitelist from ten to fourteen. Appended, not
# reordered, so ICON_DEFS_HTML's own symbol-id/ICON_IDS agreement check
# stays a straightforward set comparison.
ICON_IDS = ICON_IDS + (
    "icon-check",
    "icon-copy",
    "icon-refresh",
    "icon-search",
)

# quick task 260903-df3: one more icon for the Airlines lightbox replace
# zone (the framed action area's upload glyph). Appended, not merged into
# either tuple above, for the same "appended, not reordered" reason those
# tuples' own comments already state — grows the whitelist from fourteen
# to fifteen.
ICON_IDS = ICON_IDS + (
    "icon-upload",
)

# 22-14-PLAN.md Task 1 (X9/D-10): one more icon for the bottom tab bar's
# "More" cell — appended, not merged into either tuple above, for the
# same "appended, not reordered" reason those tuples' own comments
# already state — grows the whitelist from twenty-one to twenty-two.
ICON_IDS = ICON_IDS + (
    "icon-more",
)

# One shared inline sprite, emitted once per document by page_shell().
# `display: none` (companion/static/style.css's `.icon-defs` rule) still
# lets every <use href="#icon-..."> reference below resolve correctly —
# that is the entire technique. Because of that, this sprite must never
# be moved inside a conditionally-rendered region: a `<use>` referencing
# a symbol that isn't in the DOM at all (not merely hidden) resolves to
# nothing.
#
# Each symbol carries fill="none"/stroke="currentColor" so a single CSS
# `color` property drives the whole glyph — this is what lets
# .stat-tile__icon's per-status tint rules (companion/static/style.css)
# work with no second colour mapping to keep in sync. The four tile
# icons use a 20x20 viewBox; the hamburger (plan 06.6.1-05) uses 24x24
# and is three horizontal lines, per the UI-SPEC. Every glyph is built
# from plain <path>/<line>/<rect>/<circle> primitives — legible outline
# shapes, not detailed illustration.
ICON_DEFS_HTML = (
    '<svg class="icon-defs" aria-hidden="true" focusable="false">'
    "<defs>"
    '<symbol id="icon-device" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<rect x="5" y="2" width="10" height="16" rx="2"/>'
    '<path d="M7.5 10l2 2 4-4.5"/>'
    "</symbol>"
    '<symbol id="icon-pipeline" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<path d="M10 16v-3"/>'
    '<path d="M6.5 11.5a5 5 0 0 1 7 0"/>'
    '<path d="M4 8.5a9 9 0 0 1 12 0"/>'
    "</symbol>"
    '<symbol id="icon-corroboration" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<circle cx="8" cy="10" r="5"/>'
    '<circle cx="12" cy="10" r="5"/>'
    "</symbol>"
    '<symbol id="icon-battery" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<rect x="2" y="6" width="14" height="8" rx="1.5"/>'
    '<path d="M18 8.5v3"/>'
    '<path d="M5 9v2"/>'
    "</symbol>"
    '<symbol id="icon-hamburger" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<line x1="4" y1="7" x2="20" y2="7"/>'
    '<line x1="4" y1="12" x2="20" y2="12"/>'
    '<line x1="4" y1="17" x2="20" y2="17"/>'
    "</symbol>"
    '<symbol id="icon-nav-config" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<path d="M3 5h8M15 5h2"/><circle cx="12" cy="5" r="2"/>'
    '<path d="M3 10h2M9 10h8"/><circle cx="7" cy="10" r="2"/>'
    '<path d="M3 15h8M15 15h2"/><circle cx="12" cy="15" r="2"/>'
    "</symbol>"
    '<symbol id="icon-nav-health" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<path d="M2 10h4l2-5 3 10 2-5h5"/>'
    "</symbol>"
    '<symbol id="icon-nav-airlines" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<path d="M3 3h7l7 7-7 7-7-7z"/><circle cx="7" cy="7" r="1.5"/>'
    "</symbol>"
    '<symbol id="icon-nav-history" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<circle cx="10" cy="10" r="7"/><path d="M10 6v4l3 2"/>'
    "</symbol>"
    '<symbol id="icon-nav-preview" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<path d="M2 10s3-5 8-5 8 5 8 5-3 5-8 5-8-5-8-5z"/>'
    '<circle cx="10" cy="10" r="2.5"/>'
    "</symbol>"
    # 06.6.3: four more glyphs (D-05/D-23/D-12/D-20), same viewBox/stroke
    # language as the ten above.
    '<symbol id="icon-nav-home" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M3 9.5L10 3.5l7 6"/><path d="M5 8.5V16.5h4v-4h2v4h4V8.5"/>'
    "</symbol>"
    '<symbol id="icon-nav-flights" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M2.5 12l4-1.5L14 3.5a1.6 1.6 0 0 1 2.3 2.3L9.5 13.5 8 17.5l-1.5-3.5z"/>'
    '<path d="M6.5 14l-2 2"/>'
    "</symbol>"
    '<symbol id="icon-nav-device" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="5" y="5" width="10" height="10" rx="2"/><rect x="8" y="8" width="4" height="4"/>'
    '<path d="M8 2v3M12 2v3M8 15v3M12 15v3M2 8h3M2 12h3M15 8h3M15 12h3"/>'
    "</symbol>"
    '<symbol id="icon-nav-display" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="2.5" y="3.5" width="15" height="11" rx="1.5"/><path d="M7 17.5h6"/>'
    '<path d="M6 11l2.5-3 2 2.5 1.5-1.5 2 2"/>'
    "</symbol>"
    '<symbol id="icon-power" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M10 3v7"/><path d="M6 6a6 6 0 1 0 8 0"/>'
    "</symbol>"
    '<symbol id="icon-moon" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M16 12.5A7 7 0 0 1 7.5 4a7 7 0 1 0 8.5 8.5z"/>'
    "</symbol>"
    '<symbol id="icon-check" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<path d="M4 10.5l4 4 8-9"/>'
    "</symbol>"
    '<symbol id="icon-copy" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<rect x="3" y="3" width="10" height="10" rx="1.5"/>'
    '<path d="M7 17h8a2 2 0 0 0 2-2V7"/>'
    "</symbol>"
    '<symbol id="icon-refresh" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<path d="M16 10a6 6 0 1 1-2-4.5"/>'
    '<path d="M16 2.5v4h-4"/>'
    "</symbol>"
    '<symbol id="icon-search" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<circle cx="8.5" cy="8.5" r="5.5"/>'
    '<path d="M13.5 13.5L17.5 17.5"/>'
    "</symbol>"
    # quick task 260903-df3: one more glyph, same viewBox/stroke language
    # as the fourteen above — the Airlines lightbox replace zone's upload
    # arrow-over-tray.
    '<symbol id="icon-upload" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<path d="M10 13V3"/>'
    '<path d="M6 7l4-4 4 4"/>'
    '<path d="M3.5 13v3a1.5 1.5 0 0 0 1.5 1.5h10a1.5 1.5 0 0 0 1.5-1.5v-3"/>'
    "</symbol>"
    # 22-14-PLAN.md Task 1 (X9/D-10): the bottom tab bar's "More" glyph —
    # three dots drawn as zero-length round-capped strokes rather than
    # three <circle fill="currentColor">, so this symbol keeps the
    # sprite's own fill="none"/stroke="currentColor" language and stays
    # driven by a single CSS `color` property like every glyph above it.
    '<symbol id="icon-more" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="2.2" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<path d="M4.5 10h.01M10 10h.01M15.5 10h.01"/>'
    "</symbol>"
    "</defs>"
    "</svg>"
)

# The tint class stat_tile() adds to its own icon instance. Its
# counterpart is companion/static/style.css's `.stat-tile__icon` (and
# the per-status `.stat-tile--* .stat-tile__icon` overrides) — Task 1's
# test harness reads that stylesheet from disk and asserts this class
# name actually appears in it, guarding against the two silently
# drifting apart.
STAT_TILE_ICON_CLASS = "stat-tile__icon"

# --- 06.6.1-04 Task 3: Health nav-tab notification dot (D-02) ---------
#
# The Health route's slug, matching what _nav_links() already computes
# (`route.lstrip("/")`) — named once so a renderer can identify the
# Health link without re-deriving it from an already-escaped route
# string.
HEALTH_NAV_SLUG = "health"

# 06.6.2-05 (D-17): slug -> icon-id, one per NAV_TABS entry. Consumed by
# sidebar_nav()/_mobile_nav_html() via _nav_links()'s already-computed
# `slug` (route.lstrip("/")) — a slug not present here (which cannot
# happen for a real NAV_TABS entry) falls through icon_html()'s own
# whitelist-fallback ("" for an unrecognised id), never a KeyError.
NAV_ICON_IDS = {
    # Phase 18: keyed by nav_slug(route). "flights" keeps the History
    # clock glyph; Home/Display/Device get their own symbols above.
    "home": "icon-nav-home",
    "display": "icon-nav-display",
    "flights": "icon-nav-history",
    "airlines": "icon-nav-airlines",
    "health": "icon-nav-health",
    "device": "icon-nav-device",
}

# 06.6.2-05 (UXA-10): the fragment id the skip-link's first-focusable
# <a href="#..."> points at and <main> carries as its own id. Named once
# so page_shell() never has the two literals drift apart.
SKIP_LINK_TARGET_ID = "main-content"

# 06.6.2-05 (UXA-10): a zero-external-dependency local favicon — a data
# URI needs neither a new static file nor a new route. #B13F16 is the
# light-mode --color-accent token (companion/static/style.css, plan
# 06.6.2-01). Held as its own module constant (rather than inlined
# directly in page_shell()'s format string) specifically so plan
# 06.6.2-07's new login_shell() function can reuse this exact literal
# later without duplicating it.
FAVICON_LINK_HTML = (
    '<link rel="icon" href="data:image/svg+xml,'
    '%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 20 20%27%3E'
    '%3Crect width=%2720%27 height=%2720%27 rx=%274%27 fill=%27%23B13F16%27/%3E'
    '%3Ctext x=%2710%27 y=%2714%27 text-anchor=%27middle%27 '
    'font-family=%27Georgia,serif%27 font-size=%2712%27 fill=%27%23FFFFFF%27'
    '%3ES%3C/text%3E%3C/svg%3E">'
)

# The dot's own class, layered on top of the existing .dot/.dot--error
# classes (see _health_alert_markup()) rather than a new colour. Its
# counterpart is companion/static/style.css's `.nav-notification` rule
# — Task 3's test harness reads that stylesheet from disk and asserts
# this class name actually appears in it.
NAV_NOTIFICATION_CLASS = "nav-notification"

# 06.6.1-UI-SPEC.md's Copywriting Contract, verbatim: appended (not
# substituted) after the "Health" nav label text via a visually-hidden
# span, so assistive tech announces "Health — attention needed" rather
# than losing the word "Health" to an aria-label override. Translated
# through i18n.t() at its one render site (D-05, 20-12-PLAN.md Task 1:
# a real completeness gap this constant's own render site had left
# un-wrapped).
HEALTH_ALERT_SUFFIX_TEXT = " — attention needed"


def icon_html(icon_id, size=20, extra_class=""):
    """A `<svg>` referencing one symbol from ICON_DEFS_HTML via `<use>`,
    or the empty string when `icon_id` is not a member of ICON_IDS.

    This is a whitelist, not a sanitiser — the same discipline
    status_dot() and stat_tile() already apply to their own state
    arguments. `icon_id` becomes a `#`-prefixed fragment identifier
    inside a `<use href="...">` attribute; an id that reached the output
    unchecked would be an attacker-influenceable fragment reference. An
    unrecognised id instead fails visibly-but-safely — a missing icon,
    not a dangling or injectable reference.

    The explicit `width`/`height` attributes are belt-and-braces against
    companion/static/style.css's `.icon` sizing rule being lost or
    overridden: an `<svg>` with neither an attribute nor a CSS size
    renders at the SVG default 300x150 and would blow the layout apart.
    This mirrors how the battery sparkline already carries both fixed
    attributes and a CSS override.

    `aria-hidden="true"` is set unconditionally: every icon in this app
    sits beside its own visible text label — a tile caption, a nav link
    label, a filter-bar/pill label — so the icon is decorative and
    announcing it would duplicate the label. Do not "improve" this by
    adding a `<title>`. (SUPERSEDED, quick task 260902-j8w: a section
    heading — Health's `Battery trend` — used to be named here too, as
    the one place a glyph sat beside a heading rather than a tile/control
    label. That heading's glyph was removed at the developer's own
    instruction; glyphs in this app are now a tile/control affordance
    only, never a heading one.)
    """
    if icon_id not in ICON_IDS:
        return ""
    css_class = "icon"
    if extra_class:
        css_class = "%s %s" % (css_class, extra_class)
    return (
        '<svg class="%s" width="%d" height="%d" aria-hidden="true" '
        'focusable="false"><use href="#%s"></use></svg>'
    ) % (css_class, size, size, icon_id)


def escape_html(value):
    """Coerce `value` to its escaped string form for safe HTML interpolation.

    None becomes an empty string; any other non-string is coerced via
    str() first. Never raises, so a malformed upstream value (an
    ADS-B/adsbdb-sourced airline name, callsign, or unresolved prefix)
    degrades to an escaped string instead of crashing a page render.
    """
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    return html.escape(value, quote=True)


# --- 06.6-01: shared "absolute + relative" timestamp helpers (D-02) ----
#
# Promoted verbatim (in logic) from companion/pages/health_page.py's own
# private copies, which is why this section exists here rather than in
# each page module: companion/pages/__init__.py forbids one page module
# importing another, so a helper every page module needs to reach must
# live in this shared layer instead. health_page.py's Device check-in
# and ADS-B pipeline rows already ship the "ISO (Nm ago)" format this
# promotes; 06.6-03 (History + Preview, wave 2) consumes these same four
# functions rather than duplicating the logic a third time.


def parse_iso(ts):
    """Parse `ts` as an ISO-8601 datetime, or return None.

    Never raises: a non-`str` input or a string `datetime.fromisoformat()`
    cannot parse both degrade to None rather than propagating a
    TypeError/ValueError into a page render.
    """
    if not isinstance(ts, str):
        return None
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def age_seconds(ts, now_ts):
    """The number of seconds between `ts` and `now_ts` (both parsed via
    parse_iso()), or None when either side fails to parse — including
    when one side is timezone-naive and the other timezone-aware, which
    parse_iso() alone cannot catch since each string parses fine on its
    own; only the subtraction raises.
    """
    parsed = parse_iso(ts)
    now_parsed = parse_iso(now_ts)
    if parsed is None or now_parsed is None:
        return None
    try:
        return (now_parsed - parsed).total_seconds()
    except TypeError:
        return None


# D-07, 20-03-PLAN.md Task 2: the French unit-suffix table
# relative_age_text()'s French branch consumes below, in the same
# "fixed dict, membership lookup, documented fallback" shape
# _STATUS_DOT_CLASSES already uses. Kept complete (all four English
# unit letters) even though the "s" entry is never actually reached
# (the seconds bucket always short-circuits to "à l'instant" before
# consulting this table) — the same audit-by-grep discipline every
# other fixed-vocabulary dict in this module follows.
_AGE_UNIT_SUFFIX_FR = {
    "s": "s",
    "m": "min",
    "h": "h",
    "d": "j",
}


def _age_bucket(age_seconds):
    """The s/m/h/d bucket a whole number of seconds falls in, as a
    `(value, unit_letter)` pair — and the ONLY place in this module the
    three threshold boundaries are written down.

    23-03-PLAN.md Task 1 extracted this out of `relative_age_text()`
    below, unchanged, so the future form beside it can read the SAME
    boundaries instead of restating them. "3m ago" and "in 3m" are one
    ladder read in two directions: they must never be able to disagree
    about where a bucket ends, and naming the boundaries once is what
    makes that structural rather than a convention somebody has to
    remember. The unit letters are the English suffixes themselves, so
    the English branch formats straight from this pair and the French
    branch maps them through `_AGE_UNIT_SUFFIX_FR` above.

    A negative input (clock skew, or an instant that has already
    elapsed) is clamped to 0 rather than read as a negative bucket —
    both directions inherit that clamp from here.
    """
    age_seconds = max(0, int(age_seconds))
    if age_seconds < 60:
        return age_seconds, "s"
    if age_seconds < 3600:
        return age_seconds // 60, "m"
    if age_seconds < 86400:
        return age_seconds // 3600, "h"
    return age_seconds // 86400, "d"


def relative_age_text(age_seconds, lang=None):
    """"Ns ago"/"Nm ago"/"Nh ago"/"Nd ago" using the s/m/h/d threshold
    ladder this app already ships on the Device/Pipeline rows — the
    ladder itself is `_age_bucket()` above, called here rather than
    restated, so this function and `relative_future_text()` below share
    one set of boundaries. A negative age (clock skew) is clamped to 0
    rather than read as "in the future".

    `lang` (D-07, 20-03-PLAN.md Task 2) is a trailing keyword whose
    `None` resolves to `prefs.current_lang()` — every pre-existing call
    site passes only the positional `age_seconds` and keeps getting the
    identical English string this function has always returned; the
    English branch below is byte-for-byte unchanged. Only a French
    request (an explicit `lang="fr"`, or a request whose
    `prefs.current_lang()` resolves to `"fr"`) takes the French branch.

    French collapses the whole under-a-minute bucket into one
    "à l'instant" ("just now") regardless of the exact second count —
    the idiomatic French phrasing 20-CONTEXT.md's D-07 names, rather
    than a literal "il y a %d secondes". The minute/hour/day buckets
    read "il y a N <unit>" (a real U+00A0 non-breaking space
    between the number and the unit, per D-09), with the unit taken
    from `_AGE_UNIT_SUFFIX_FR` above and the connector taken from the
    `"%s ago"` catalogue entry — the copy for both lives in
    `companion/i18n_fr/health.py`, read here through `i18n.t_lang()`
    rather than duplicated as a module literal.
    """
    age_seconds = max(0, int(age_seconds))
    if lang is None:
        lang = prefs.current_lang()
    value, unit = _age_bucket(age_seconds)
    if lang == "fr":
        if unit == "s":
            return i18n.t_lang("just now", "fr")
        quantity = "%d %s" % (value, _AGE_UNIT_SUFFIX_FR[unit])
        return i18n.t_lang("%s ago", "fr") % quantity
    return "%d%s ago" % (value, unit)


def relative_future_text(seconds_ahead, lang=None):
    """"in Ns"/"in Nm"/"in Nh"/"in Nd" — the FORWARD reading of the same
    ladder `relative_age_text()` above reads backwards, over the same
    `_age_bucket()` boundaries (23-03-PLAN.md Task 1, for the countdown
    plan 23-06 puts beside a server-computed next-wake instant).

    This function is FORMATTING, never a verdict. It says how long
    remains until an instant somebody else computed; it never says
    "late", "held", "due", or anything at all about the device's state.
    Those words are `frame_state`'s and stay server-rendered.

    A `seconds_ahead` that has already elapsed (a negative) resolves to
    the zero bucket via `_age_bucket()`'s own clamp — never a negative
    number, and never a past-tense string. A caller wanting the past
    tense asks `relative_age_text()` for it explicitly;
    `relative_time_html()` below is the one place that chooses between
    them.

    `lang` is the same trailing keyword every sibling here carries: its
    `None` resolves to `prefs.current_lang()`. French collapses the
    whole under-a-minute bucket the way the past form does, into one
    "in a moment" phrase rather than a literal second count, and reads
    the connector from the `"in %s"` catalogue entry with a real U+00A0
    between the number and the unit (D-09). Both strings live in
    `companion/i18n_fr/health.py` beside the past form's own, read here
    through `i18n.t_lang()` and never duplicated as a module literal —
    which is what lets plan 23-05's ticker script carry no French at
    all.
    """
    value, unit = _age_bucket(seconds_ahead)
    if lang is None:
        lang = prefs.current_lang()
    if lang == "fr":
        if unit == "s":
            return i18n.t_lang("in a moment", "fr")
        quantity = "%d %s" % (value, _AGE_UNIT_SUFFIX_FR[unit])
        return i18n.t_lang("in %s", "fr") % quantity
    return "in %d%s" % (value, unit)


# --- 23-05-PLAN.md Task 1 (D14/CFG-34): the ticker's copy -------------
#
# companion/static/relative-time.js rewrites every <time data-relative>
# element once a second, which means the four bucket wordings have to
# exist CLIENT-side, in the reader's own language. They are rendered
# onto <body> by page_shell() below and read back with getAttribute(),
# the same attribute-with-English-fallback idiom REFRESH_PAUSED_TEXT
# already uses, and for the same reason it gives: several of these
# elements sit inside freshness.js's swap targets, so an attribute on
# the element itself would be replaced out from under the script on
# every successful refresh. <body> never is.
#
# ONE wording per bucket per direction, complete, rather than a
# connector plus a unit word plus a separator plus a collapse flag. The
# script then carries no language logic at all — it substitutes a
# quantity into a string and stops. French collapsing its whole
# sub-minute bucket into a phrase with no number in it ("à l’instant",
# "dans un instant") is then just a wording with no place to substitute
# into, which is data, not a branch.
#
# "#" IS THE QUANTITY'S PLACE, AND IT IS NOT "%s" ON PURPOSE. These
# strings reach the browser as attribute values on a rendered page, and
# companion/test_i18n.py's Check 3 scans every French render for a
# stray "%s"/"%d"/"{}" — the real failure mode of a mistyped catalogue
# key. A "%s" here would trip that check on every page in the app, and
# the check is right to object: a format artefact in rendered markup is
# exactly what it is looking for. "#" is not one.
#
# These are NOT a second ladder. They are the same ladder's own output
# with the number lifted out, and test_companion_app.py asserts exactly
# that: each wording, filled with the quantity _age_bucket() picks,
# must EQUAL relative_age_text()/relative_future_text()'s own return
# value for a representative instant in every bucket, in both
# languages. Change a wording here without changing the function and
# that check names the bucket, the language and both strings.
RELATIVE_QUANTITY_MARK = "#"
RELATIVE_PAST_SECONDS_TEXT = "#s ago"
RELATIVE_PAST_MINUTES_TEXT = "#m ago"
RELATIVE_PAST_HOURS_TEXT = "#h ago"
RELATIVE_PAST_DAYS_TEXT = "#d ago"
RELATIVE_FUTURE_SECONDS_TEXT = "in #s"
RELATIVE_FUTURE_MINUTES_TEXT = "in #m"
RELATIVE_FUTURE_HOURS_TEXT = "in #h"
RELATIVE_FUTURE_DAYS_TEXT = "in #d"

# What a countdown reads once its instant has passed. NEVER a warning
# word and never a warn colour: 22-15 made freshness.js's own failure
# states neutral on the argued ground that a thing which has not
# happened yet is not a fault, and the same reasoning governs here. It
# is the app's neutral breathing treatment and nothing else.
RELATIVE_WAITING_TEXT = "waiting…"

# Must equal the attribute names companion/static/relative-time.js
# reads, in this order — bucket order, s/m/h/d, matching _age_bucket()'s
# own unit letters. test_companion_app.py pins every one of them present
# in that file's source.
RELATIVE_PAST_ATTRS = (
    "data-relative-past-s",
    "data-relative-past-m",
    "data-relative-past-h",
    "data-relative-past-d",
)
RELATIVE_FUTURE_ATTRS = (
    "data-relative-future-s",
    "data-relative-future-m",
    "data-relative-future-h",
    "data-relative-future-d",
)
RELATIVE_WAITING_ATTR = "data-relative-waiting"

# The marker relative_time_html() puts on an element that is a
# COUNTDOWN rather than an age (see its `countdown` keyword). Also read
# by companion/static/relative-time.js.
RELATIVE_COUNTDOWN_ATTR = "data-relative-countdown"

# Ordered s/m/h/d, matching the attribute tuples above and
# _age_bucket()'s own unit letters.
_RELATIVE_PAST_TEXTS = (
    RELATIVE_PAST_SECONDS_TEXT, RELATIVE_PAST_MINUTES_TEXT,
    RELATIVE_PAST_HOURS_TEXT, RELATIVE_PAST_DAYS_TEXT,
)
_RELATIVE_FUTURE_TEXTS = (
    RELATIVE_FUTURE_SECONDS_TEXT, RELATIVE_FUTURE_MINUTES_TEXT,
    RELATIVE_FUTURE_HOURS_TEXT, RELATIVE_FUTURE_DAYS_TEXT,
)


def relative_copy_attrs(lang=None):
    """The ticker's own copy as `((attribute name, translated wording),
    ...)`, ready for page_shell() to render onto `<body>`.

    Nine pairs: four past wordings, four future wordings, and the
    waiting phrase an expired countdown reads. Every value goes through
    `i18n.t_lang()` here, server-side, which is what lets
    `companion/static/relative-time.js` carry no French at all.
    """
    if lang is None:
        lang = prefs.current_lang()
    pairs = []
    for attr, text in zip(RELATIVE_PAST_ATTRS, _RELATIVE_PAST_TEXTS):
        pairs.append((attr, i18n.t_lang(text, lang)))
    for attr, text in zip(RELATIVE_FUTURE_ATTRS, _RELATIVE_FUTURE_TEXTS):
        pairs.append((attr, i18n.t_lang(text, lang)))
    pairs.append(
        (RELATIVE_WAITING_ATTR, i18n.t_lang(RELATIVE_WAITING_TEXT, lang)))
    return tuple(pairs)


def _machine_instant(parsed):
    """`parsed` as a machine-readable Europe/Paris ISO-8601 instant at
    seconds precision, or "" when it cannot be produced.

    This is the value `relative_time_html()` puts in a `datetime`
    attribute. It is deliberately NOT the raw stored string: D-05/B4's
    rule is that no raw, unconverted timestamp reaches the page, and two
    shipped checks assert exactly that over `concise_timestamp_html()`'s
    output — so the attribute carries the same instant, converted onto
    the one timezone this app speaks, offset included. An offset is what
    makes it unambiguous to the script that will read it.

    A naive datetime is taken as UTC, matching `local_clock_text()`'s
    own convention and `history_db.utc_now_iso()`'s own output. Never
    raises: an input that cannot be converted returns "", and the caller
    renders plain text rather than an element with an empty attribute.
    """
    try:
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=ZoneInfo("UTC"))
        return parsed.astimezone(LOCAL_TZ).isoformat(timespec="seconds")
    except (ValueError, OverflowError, AttributeError):
        return ""


def relative_time_html(ts, now_ts, fallback="no reading yet", lang=None,
                       countdown=False, static_text=None):
    """"<time datetime="<instant>" data-relative><relative age></time>" —
    the app's ONE relative-time element (23-03-PLAN.md Task 1, D14/
    CFG-34). Before this function the codebase rendered no `<time>`
    element anywhere: every relative age was plain text baked into a
    span at render time and frozen until something replaced the whole
    region.

    The visible text is `relative_age_text()`'s own return value for a
    past instant and `relative_future_text()`'s for a future one — one
    function, both directions, so plan 23-06's countdown has nothing to
    add here. Neither string is re-derived: this is a wrapping, and if
    the rendered text changes for any input the conversion is wrong.

    `datetime` carries the machine-readable instant (`_machine_instant()`
    above); `data-relative` is the hook plan 23-05's ticker queries.
    Nothing else goes in the element — no class that carries meaning, no
    state word. It is semantic, not presentational: a caller that wants
    the `.time-value` role puts that class on its OWN wrapper, because
    monospace stays reserved for identifiers (C5, Phase 22).

    THE NO-JS FLOOR IS THIS FUNCTION'S OUTPUT, not an enhancement over
    it. With scripts blocked the element reads exactly what the bare
    text read before — the text is server-rendered and complete — and
    the ticker is the layer added over it, never a prerequisite for it.

    THIS IS A RAW-MARKUP-PRODUCING FUNCTION: callers interpolate the
    return value verbatim — never re-escape it — and place it only in
    data_table()'s raw_columns parameter, or directly in already-safe
    markup (never in a data_table() column outside raw_columns). Both
    the instant and the text are escaped here, at the interpolation
    site, the same discipline `concise_timestamp_html()` below carries.

    Returns the escaped `fallback` (a bare string, no markup — matching
    `absolute_and_relative()`'s own no-markup fallback contract) when
    `ts` is falsy, and the escaped `ts` when it, `now_ts` or the
    conversion fails — never raising, and never an element carrying an
    empty or invented instant, which reads as a correct time to a script
    and is worse than no element at all.

    `lang` is the same trailing keyword every sibling here carries: its
    `None` resolves through `relative_age_text()`'s own
    `prefs.current_lang()` default.

    `countdown` (23-05-PLAN.md Task 1) marks the element as a COUNTDOWN
    rather than an age: it adds `RELATIVE_COUNTDOWN_ATTR`, and once the
    instant has passed the element reads `RELATIVE_WAITING_TEXT` instead
    of turning into an age. A countdown that has run out is still a
    countdown, and silently becoming "0s ago" would change what the
    element is about halfway through its own life.
    `companion/static/relative-time.js` reads the same marker and makes
    exactly the same choice client-side, so the two never disagree and
    the no-JS rendering of an expired countdown is already correct.
    The default is False, which produces the byte-identical element
    23-03 shipped. No page renders a countdown yet; plan 23-06's
    next-wake line is its first consumer.

    `static_text` (23-06-PLAN.md) renders THAT text instead of the
    ladder's output, leaving the `datetime` attribute and the
    `data-relative` hook exactly as they are — the element is still the
    ticker's, and `companion/static/relative-time.js` replaces the text
    with the live age on its first pass. It exists for one situation and
    should be used in no other: a line whose SERVER rendering has to
    stay true for a reader with no ticker to advance it. Health's
    freshness line is that line — "Updated 0s ago" is true at load and
    false a second later, which is 19-09/A-20's own frozen zero, while
    "Updated 14:32" is true forever and becomes "Updated 3m ago" the
    moment a script runs. THE CALLER IS ASSERTING THAT ITS TEXT IS TRUE
    INDEPENDENT OF NOW: pass a clock or an absolute date, never a
    duration. `None` is the default and produces the byte-identical
    element 23-03 shipped.
    """
    if not ts:
        return escape_html(fallback)
    parsed = parse_iso(ts)
    age = age_seconds(ts, now_ts)
    if parsed is None or age is None:
        return escape_html(ts)
    instant = _machine_instant(parsed)
    if not instant:
        return escape_html(ts)
    if static_text is not None:
        text = static_text
    elif countdown and age >= 0:
        text = i18n.t_lang(
            RELATIVE_WAITING_TEXT,
            lang if lang is not None else prefs.current_lang())
    elif age < 0:
        text = relative_future_text(-age, lang=lang)
    else:
        text = relative_age_text(age, lang=lang)
    marker = " " + RELATIVE_COUNTDOWN_ATTR if countdown else ""
    return '<time datetime="%s" data-relative%s>%s</time>' % (
        escape_html(instant), marker, escape_html(text))


def absolute_and_relative(ts, now_ts, fallback="no reading yet", lang=None):
    """"<ts> (<relative age> ago)" — the house "absolute + relative"
    timestamp format (D-02), already shipped on this page's Device
    check-in and ADS-B pipeline rows and now shared for every caller.

    Returns `fallback` when `ts` is falsy (None or empty string); returns
    `ts` unchanged (absolute only, no relative suffix) when age_seconds()
    cannot parse either side — an unparseable or missing `now_ts` — never
    raising. This is a deliberate hardening over the pre-promotion
    health_page.py path, where an empty-string `ts` would have reached
    the relative-age helper as `None` and raised a TypeError mid-render.

    The return value is plain, unescaped text — the same contract
    status_dot()'s `label` parameter already carries. Every caller must
    keep escaping it: wrap it in escape_html() directly, or hand it to a
    builder such as data_table() that already escapes every cell it is
    given.

    Absolute-first ordering (the ISO string first, the relative age in
    parentheses) is this app's shipped, canonical convention and must
    not be reversed — 06.3-UI-SPEC.md's Typography section shows a
    relative-first example, but that is illustrative prose no 06.3 plan
    task implements or depends on (06.6-RESEARCH.md Open Question 1).

    `lang` (Polish fix 2, mirroring local_clock_text()'s own trailing
    keyword, D-07): `None` resolves via `relative_age_text()`'s own
    `prefs.current_lang()` default, so every pre-existing call site
    (passing only `ts`/`now_ts`) keeps its identical English output. An
    explicit `lang` is threaded straight through to `relative_age_text()`
    for a caller that needs a specific language regardless of the
    current request's own ContextVar-resolved language — e.g. a
    server-side notification body (D-28) rendered with no request
    context to read from at all.
    """
    if not ts:
        return fallback
    age = age_seconds(ts, now_ts)
    if age is None:
        return ts
    return "%s (%s)" % (ts, relative_age_text(age, lang=lang))


# 22-06-PLAN.md Task 3 (D-05, B4): a `now_parsed` guaranteed to fall on a
# DIFFERENT Europe/Paris calendar day than any real timestamp this app
# renders, so passing it to `local_clock_text()` forces that function's
# own cross-day "D Mon HH:MM" branch — this is how `concise_timestamp_
# html()`'s `title` below is built as a full local timestamp, reusing
# `local_clock_text()` itself (the one visible-time formatter) rather
# than a second, competing implementation.
_FULL_TIMESTAMP_SENTINEL_NOW = datetime(1970, 1, 1, tzinfo=ZoneInfo("UTC"))


def concise_timestamp_html(ts, now_ts, fallback="no reading yet", lang=None):
    """"<span class="mono" title="<D Mon HH:MM local>"><HH:MM local> (<relative>)</span>"
    — D-09's concise-timestamp-by-default format (06.6.3-UI-SPEC.md's New
    Component Contracts). The visible text is `local_clock_text()`'s own
    Europe/Paris clock (bare "HH:MM" on the same local day as `now_ts`,
    "D Mon HH:MM" otherwise) plus the existing `relative_age_text()`
    suffix, preserving `absolute_and_relative()`'s established
    absolute-first ordering convention (do not reverse to
    relative-first). The `title` attribute is a full local timestamp —
    always day-qualified, via `local_clock_text()`'s own cross-day
    branch forced by `_FULL_TIMESTAMP_SENTINEL_NOW` above — never the
    raw ISO string.

    Corrected under D-05/22-06-PLAN.md Task 3 (B4): this docstring used
    to promise `"<HH:MM> UTC (<relative>)"` — a stale "UTC" suffix the
    code below never actually emitted even before this task (the visible
    text was already `local_clock_text()`'s Paris-local output) — and
    the `title` WAS the raw, unconverted ISO string until this task. That
    stale docstring is exactly what `companion/pages/health_page.py`'s
    battery code copied when it built its own "HH:MM UTC (relative)"
    readout by hand instead of calling this function (B4) — corrected
    here rather than merely worked around at that one call site.

    THIS IS A RAW-MARKUP-PRODUCING FUNCTION: callers interpolate the
    return value verbatim — never re-escape it — and place it only in
    data_table()'s new raw_columns parameter, or directly in
    already-safe markup (never in a data_table() column outside
    raw_columns).

    Returns the escaped `fallback` (a bare string, no markup — matching
    absolute_and_relative()'s own no-markup fallback contract) when `ts`
    is falsy. When `ts` fails to parse (or age_seconds() cannot compute,
    e.g. a mismatched now_ts), returns a span with the raw value in both
    the title and visible-text slots rather than raising — there is
    nothing to convert once parsing itself has failed, so this one
    degrade path is unchanged by this task.

    absolute_and_relative() is not deleted by this function's addition —
    it remains the right choice for any plain-text-only call site (e.g.
    Preview's no-panel caption); do not replace those call sites with
    this function.

    `lang` (Polish fix 2, mirroring local_clock_text()'s own trailing
    keyword, D-07): `None` resolves via `local_clock_text()`'s/
    `relative_age_text()`'s own `prefs.current_lang()` default, so every
    pre-existing call site (passing only `ts`/`now_ts`) keeps its
    identical English output — the French month table/relative-age
    connector only apply when the CURRENT REQUEST's language is French
    (or an explicit `lang="fr"` is passed here), never unconditionally.
    """
    if not ts:
        return escape_html(fallback)
    parsed = parse_iso(ts)
    age = age_seconds(ts, now_ts)
    if parsed is None or age is None:
        return '<span class="mono" title="%s">%s</span>' % (
            escape_html(ts), escape_html(ts))
    full_local = local_clock_text(parsed, _FULL_TIMESTAMP_SENTINEL_NOW, lang=lang)
    # 23-03-PLAN.md Task 1 (D14/CFG-34): the parenthesised relative half
    # is now relative_time_html()'s element rather than a bare escaped
    # string, so every surface reading THROUGH this function inherits
    # the convention without its own page module changing at all. The
    # parentheses stay OUTSIDE the element: they are this format's
    # punctuation, not part of the age, and the ticker that rewrites the
    # element's text in plan 23-05 must not have to reproduce them. The
    # outer span, its class, its title and the absolute-first ordering
    # are untouched — reversing that ordering is not this plan's
    # business (06.6-RESEARCH.md Open Question 1).
    return '<span class="mono" title="%s">%s (%s)</span>' % (
        escape_html(full_local),
        escape_html(local_clock_text(parsed, parse_iso(now_ts), lang=lang)),
        relative_time_html(ts, now_ts, lang=lang))


def month_abbr(month, lang=None):
    """Phase 21 polish: the language-aware abbreviated month name, for
    callers that build their own "D Mon" labels (the Health battery
    chart's X axis) — the same twelve-entry tables local_clock_text()
    below selects between, exposed once instead of copied. `lang`
    defaults to the request's resolved language; `month` is 1..12."""
    if lang is None:
        lang = prefs.current_lang()
    table = _MONTH_ABBR_FR if lang == "fr" else _MONTH_ABBR
    return table[month - 1]


def local_clock_text(parsed, now_parsed=None, lang=None):
    """`parsed` (an aware or naive datetime) rendered on LOCAL_TZ: "HH:MM"
    when it falls on the same local day as `now_parsed` (or when no `now`
    is supplied), otherwise "D Mon HH:MM". A naive datetime is taken as
    UTC, matching history_db.utc_now_iso()'s own output. Never raises.

    `lang` (D-07, 20-03-PLAN.md Task 2) is a trailing keyword whose
    `None` resolves to `prefs.current_lang()` — every pre-existing call
    site passes only `parsed` (and, at most, `now_parsed` by keyword),
    so the English month table (`_MONTH_ABBR`) and this function's
    English output are unchanged. Under a French request, the month
    abbreviation comes from `_MONTH_ABBR_FR` instead; the clock itself
    stays 24-hour Europe/Paris in both languages — no locale module,
    no `%p`, no change to the timezone handling.
    """
    try:
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=ZoneInfo("UTC"))
        local = parsed.astimezone(LOCAL_TZ)
        clock = local.strftime("%H:%M")
        if now_parsed is not None:
            if now_parsed.tzinfo is None:
                now_parsed = now_parsed.replace(tzinfo=ZoneInfo("UTC"))
            if now_parsed.astimezone(LOCAL_TZ).date() == local.date():
                return clock
            if lang is None:
                lang = prefs.current_lang()
            return "%d %s %s" % (local.day, month_abbr(local.month, lang), clock)
        return clock
    except (ValueError, OverflowError, AttributeError):
        return parsed.strftime("%H:%M") if hasattr(parsed, "strftime") else ""


def ui_theme_from_cookie(cookies):
    """Return the CFG-09 UI theme named by `cookies`, or "auto" when the
    cookie is missing or holds a value outside UI_THEME_CHOICES.

    Membership test before use, mirroring the same discipline this
    codebase already applies to theme/runway ids elsewhere (ASVS V5) —
    a client-controlled cookie value is never trusted as-is.
    """
    if not isinstance(cookies, dict):
        return "auto"
    value = cookies.get(UI_THEME_COOKIE_NAME)
    return value if value in UI_THEME_CHOICES else "auto"


def _nav_links(active):
    """Return one (is_active, escaped_route, escaped_label, slug) tuple
    per NAV_TABS entry, in NAV_TABS order.

    This is the single place NAV_TABS is iterated and its route/label
    pair escaped; sidebar_nav() (vertical, >=960px) and _mobile_nav_html()
    (hamburger dropdown, <960px, 06.6.1-05) both consume this (via
    _nav_groups() below) instead of re-iterating NAV_TABS and
    re-implementing the same escaping/active-state logic twice. The
    unescaped route `slug` (06.6.1-04) is part of what this function
    single-sources too, so a renderer can identify a specific link (e.g.
    the Health nav-tab notification dot's target) without re-deriving
    "which link is Health" from an already-escaped route string.
    """
    links = []
    for route, label in NAV_TABS:
        slug = nav_slug(route)
        is_active = slug == active
        # D-05/D-09 (20-01-PLAN.md Task 3): the label is looked up
        # through i18n.t() at render time — NAV_TABS/NAV_GROUPS keep
        # their English values (D-01); escape_html() still wraps the
        # result, exactly like any other t() call site.
        links.append((is_active, escape_html(route), escape_html(i18n.t(label)), slug))
    return links


def _nav_groups(active):
    """NAV_GROUPS in display order, each as (escaped_group_label, links)
    where `links` is the slice of _nav_links(active) belonging to that
    group. Phase 18: the one place the group structure is walked, so the
    sidebar and the dropdown can never disagree about which tab sits
    under the "Advanced" label.

    D-17 (21-01-PLAN.md Task 1): the group whose label is
    ADVANCED_GROUP_LABEL (Health, Device) used to be omitted entirely
    in simple mode (D-30, 20-01-PLAN.md Task 3); that gate is deleted
    along with simple mode itself — the Advanced group now renders on
    every page for every request, like every other group. `/health`
    and `/device` were always reachable by URL and stay session-gated
    regardless (companion/pages/__init__.py's ctx contract).
    """
    links = _nav_links(active)
    groups = []
    offset = 0
    for group_label, entries in NAV_GROUPS:
        count = len(entries)
        group_links = links[offset:offset + count]
        offset += count
        groups.append((escape_html(i18n.t(group_label)), group_links))
    return groups


# 06.6.1-05 (D-06, superseding D-00): the horizontally-scrollable nav
# strip's renderer used to live here. Real-device testing found the
# pattern hid most tabs behind an undiscoverable swipe even after its own
# flexbox sizing bug was fixed, so it was replaced rather than repaired a
# second time — see companion/static/style.css's own header comment for
# the full flexbox history. There are now exactly two live nav
# renderers, sidebar_nav() and _mobile_nav_html() below, both fed by
# _nav_links() above.


def _health_alert_markup(severity):
    """The Health nav-tab notification dot plus its visually-hidden
    screen-reader suffix (06.6.1-UI-SPEC.md's Layout Contract / D-02),
    built once so both `_nav_html()`-style and `sidebar_nav()` renderers
    share exactly one markup source for it — today only `sidebar_nav()`
    calls this (the horizontal `_nav_html()` renderer is retired by plan
    06.6.1-05 rather than gaining this markup itself).

    `severity` is `"warn"` or `"error"` — this function is only ever
    called when the caller has already checked severity is not `"ok"`/
    falsy (06.6.2-06, UXA-14). The dot class is looked up via the same
    `_STATUS_DOT_CLASSES` dict `status_dot()` uses (reused, not
    duplicated), so a warning-only Health state draws `dot--warn` rather
    than always the maximal `dot--error` treatment.

    Appends a visually-hidden text suffix rather than an `aria-label` on
    the link: an `aria-label` would *replace* the link's accessible
    name, so the announced text would become only the alert phrasing and
    the word "Health" would be lost. An appended visually-hidden span
    leaves the existing "Health" name intact and adds to it — this is
    06.6.1-UI-SPEC.md's stated reason and a correctness point, not a
    style preference.

    The absence of this markup is deliberately the all-clear signal —
    the same precedent the anomaly banner and CFG-05's source-fault
    badge already set in this codebase: nothing is rendered when
    everything is fine, so there is no "all good" chrome to ignore.
    """
    dot_class = _STATUS_DOT_CLASSES.get(severity, _DEFAULT_STATUS_DOT_CLASS)
    return (
        '<span class="dot %s %s"></span>'
        '<span class="visually-hidden">%s</span>'
    ) % (dot_class, NAV_NOTIFICATION_CLASS, escape_html(i18n.t(HEALTH_ALERT_SUFFIX_TEXT)))


NAV_SCREEN_ON_TEXT = "Screen on"
NAV_SCREEN_OFF_TEXT = "Screen off"
NAV_QUIET_ON_TEXT = "Quiet hours on"
NAV_QUIET_OFF_TEXT = "Quiet hours off"
NAV_STATUS_ARIA_LABEL_TEXT = "Screen and quiet hours status — go to Home"
# 22-14-PLAN.md Task 2 (B10, 22-UI-SPEC.md §5 contract 6): the middle dot
# that separates the two state segments. Promoted out of the format
# string to a named constant because the two segments are now
# `white-space: nowrap` spans inside a wrapping flex row (the line may
# break BETWEEN them, never inside one), so the separator is a sibling
# of both rather than punctuation embedded in one of them.
NAV_STATUS_SEPARATOR_TEXT = " · "


def nav_status_html(device_config, active=None):
    """The nav's state-only reminder — D-03 (21-CONTEXT.md, R-03): one
    shared body, called by BOTH `sidebar_nav()` and `_mobile_nav_html()`
    below, so the two nav copies can never disagree about the frame's
    current Screen/Quiet-hours state — the same "one function, two call
    sites" contract `sidebar_nav()`'s own docstring already states for
    `_nav_links()`.

    Reads the exact same two `device_config` fields `layout.frame_
    strip_html()` reads (`display_enabled`/`quiet_hours_enabled`), so
    the strip and this reminder can never disagree either — there is
    only one source of truth for both.

    Returns `""` when `device_config` is falsy — `None` means "no
    request context available" (the login shell, a 404, any error
    page rendered before a session exists), and degrades to no
    reminder at all, matching `_health_alert_markup()`'s own documented
    "absence is the correct signal, not merely convenient" contract.

    A plain `<a href="/">` — no `<form>`, no `<button>`, no script
    (D-03: "the nav shows a state reminder, not buttons" — the phase 18
    audit finding that the nav must carry no actions). The visible text
    is two dot+word segments ("Screen on · Quiet hours off"); the
    link's own `aria-label` states where it goes, since the visible
    text alone does not read as a link destination to a screen-reader
    user. Every value crosses `escape_html()`; every string crosses
    `i18n.t()` at its interpolation site.

    `active` (22-14-PLAN.md Task 2, B10/D-04, 22-UI-SPEC.md §5 contract
    6, keyword-with-default so no existing positional call site changes
    meaning): the caller's own active-route slug. When it is Home's own
    slug this renders a `<span>` with NO `href` at all, whose
    `aria-label` names only the state — because on Home the link's
    "— go to Home" label promised navigation the element could not
    perform, which is the defect B10 names, and the wording is not what
    is wrong with it. D-04's "the reminder stays only if it links
    somewhere useful" is then satisfied by construction rather than by
    copy: on Home it is not a link, so it cannot claim a destination the
    user already occupies. Everywhere else it stays the existing
    `<a href="/">` with its destination-naming label, byte-identical to
    this function's own pre-22-14 output.

    The Home variant's `aria-label` is composed from the SAME two
    translated state strings the visible segments interpolate, never a
    second wording — so the announced name and the rendered text cannot
    drift, and no new catalogue entry is introduced for a string that is
    already on screen.

    B10 also changes the two segments' SHAPE (not their text): each is
    wrapped in its own `.nav-status__segment` span so
    companion/static/style.css can give it `white-space: nowrap`. The
    audit measured the old inline run wrapping mid-phrase ("Screen on ·
    Quiet hours" / "on"; FR "Heures / calmes activées"); the line may
    now break between the two segments, never inside one.
    """
    if not device_config:
        return ""
    display_enabled = device_config.get("display_enabled", True)
    is_display_on = display_enabled is not False
    quiet_enabled = device_config.get("quiet_hours_enabled", False)
    is_quiet_on = quiet_enabled is True
    screen_dot_class = "dot--ok" if is_display_on else "dot--off"
    screen_text = i18n.t(NAV_SCREEN_ON_TEXT if is_display_on else NAV_SCREEN_OFF_TEXT)
    quiet_dot_class = "dot--ok" if is_quiet_on else "dot--off"
    quiet_text = i18n.t(NAV_QUIET_ON_TEXT if is_quiet_on else NAV_QUIET_OFF_TEXT)
    segments = (
        '<span class="nav-status__segment">'
        '<span class="dot %s"></span><span class="dot-label">%s</span>'
        "</span>"
        '<span class="nav-status__sep">%s</span>'
        '<span class="nav-status__segment">'
        '<span class="dot %s"></span><span class="dot-label">%s</span>'
        "</span>"
    ) % (
        screen_dot_class, escape_html(screen_text),
        escape_html(NAV_STATUS_SEPARATOR_TEXT),
        quiet_dot_class, escape_html(quiet_text),
    )
    if active == nav_slug(HOME_ROUTE):
        return (
            '<span class="nav-status text-label" aria-label="%s">%s</span>'
        ) % (
            escape_html(
                screen_text + NAV_STATUS_SEPARATOR_TEXT + quiet_text),
            segments,
        )
    return (
        '<a class="nav-status text-label" href="%s" aria-label="%s">%s</a>'
    ) % (
        HOME_ROUTE, escape_html(i18n.t(NAV_STATUS_ARIA_LABEL_TEXT)), segments,
    )


def sidebar_nav(active, health_alert=None, device_config=None):
    """The vertical Primary-navigation landmark shown by page_shell()'s
    dashboard sidebar column at desktop width.

    Renders the same NAV_TABS route set as _nav_html() — via the shared
    _nav_links() helper, so the two renderers can never drift — just in
    a vertical arrangement. companion/static/style.css's 960px media
    query decides which of the two copies is visible at a given
    viewport width; this function has no opinion on visibility.

    `health_alert` (06.6.1-04, keyword-with-default so no existing
    positional call site changes meaning; 06.6.2-06/UXA-14 widened the
    contract from a boolean to a severity string) is `None`/`"ok"` for
    no dot, or `"warn"`/`"error"` to append `_health_alert_markup()`
    (drawn with that exact severity) after the label text of the link
    whose slug matches HEALTH_NAV_SLUG, and only that link. The markup
    is already-built safe HTML and is interpolated verbatim, exactly
    like status_dot()'s output is in other builders — it is not routed
    through escape_html() again.

    06.6.2-05 (D-17/UXA-10): each link is prefixed with its
    NAV_ICON_IDS-mapped icon (icon_html()'s own whitelist-fallback
    contract makes an unrecognised slug render no icon rather than
    raising — this cannot happen for a real NAV_TABS entry, but keeps
    the call safe). The active link's `<a>` carries `aria-current="page"`
    — never the inactive links — so exactly one link at a time announces
    "current page" to assistive tech. The active-pill *visual* treatment
    (background tint, radius) lives in companion/static/style.css's
    `.sidebar-link--active` rule, not here; the class names themselves
    are unchanged.

    `device_config` (D-03, 21-04-PLAN.md Task 2, keyword-with-default
    so no existing positional call site changes meaning): threaded
    straight to `nav_status_html()`, whose own reminder markup is
    prepended before this function's `<nav>` — i.e. between the brand
    (`page_shell()`'s own `.sidebar-title` span) and the primary nav
    list, exactly where 21-UI-SPEC.md §B places it. `None` (no request
    context) renders no reminder at all, byte-identical to this
    function's own pre-21-04 output.
    """
    parts = []
    for group_label, group_links in _nav_groups(active):
        links = []
        for is_active, route, label, slug in group_links:
            if is_active:
                css_class = "sidebar-link sidebar-link--active"
                aria_current = ' aria-current="page"'
            else:
                css_class = "sidebar-link"
                aria_current = ""
            icon = icon_html(
                NAV_ICON_IDS.get(slug, ""), extra_class="sidebar-link__icon")
            alert_html = (
                _health_alert_markup(health_alert)
                if health_alert in ("warn", "error") and slug == HEALTH_NAV_SLUG else "")
            links.append(
                '<a class="%s" href="%s"%s>%s%s%s</a>'
                % (css_class, route, aria_current, icon, label, alert_html))
        # Phase 18: an unlabelled group renders its links bare; a labelled
        # group ("Advanced") wraps them in a .nav-group carrying a small
        # uppercase label so the split reads at a glance.
        if group_label:
            parts.append(
                '<div class="nav-group nav-group--advanced">'
                '<span class="nav-group__label text-label">%s</span>%s</div>'
                % (group_label, "".join(links)))
        else:
            parts.append("".join(links))
    return (
        "%s"
        '<nav class="sidebar-nav" aria-label="%s">%s</nav>'
    ) % (
        # 22-14-PLAN.md Task 2 (B10): `active` is threaded through so the
        # reminder can drop its href on Home — one shared body, two call
        # sites, one active-route argument, so the sidebar and the
        # dropdown can still never disagree about its shape either.
        nav_status_html(device_config, active=active),
        # 22-08-PLAN.md Task 2 (D-06/B16): was the hard-coded literal
        # "Primary navigation" — an untranslated accessible name for the
        # one nav landmark exposed to the accessibility tree at any given
        # viewport width (see this module's own comment on that exposure
        # above _mobile_nav_html()).
        escape_html(i18n.t("Primary navigation")),
        "".join(parts))


# --- 22-14-PLAN.md Task 1 (X9, D-10, 22-UI-SPEC.md §3.1) ---------------
#
# The bottom tab bar's "More" cell label. Sentence case, and NOT the
# label voice — a nav destination is a destination, not a label, which
# is why companion/static/style.css's `.tab-bar__label` declares no
# uppercase and no tracking.
TAB_BAR_MORE_LABEL = "More"

# The glyph on that cell. A whitelist member (ICON_IDS above), so
# icon_html()'s own fallback contract applies unchanged.
TAB_BAR_MORE_ICON_ID = "icon-more"

# The `<body>` marker page_shell() adds ONLY when the tab bar really
# renders. companion/static/style.css scopes the sub-960px page-foot
# clearance to it, so the 404 and the preview-image error pages — which
# render no bar — reserve no space for one.
TAB_BAR_BODY_CLASS = "has-tab-bar"

# T13 (22-AUDIT.md, 22-UI-SPEC.md §1's copy table and §5 contract 9,
# 22-15-PLAN.md Task 2). companion/static/freshness.js shows a visible
# neutral badge when its refresh loop is retrying or deliberately idle,
# instead of stopping dead and silently. The badge is built client-side
# — the loop can be in either state long after the server's response was
# written — so its two strings are server-rendered onto `<body>` here
# and read with getAttribute(), the same attribute-with-English-fallback
# idiom dirty-state.js and poll-cooldown.js already use.
#
# They live on `<body>` rather than on the pill, deliberately: the pill
# itself is rendered by companion/pages/health_page.py, which this plan
# does not own, and the freshness wrapper it sits in is one of
# freshness.js's own swap targets — an attribute there would be replaced
# out from under the script on every successful refresh. `<body>` is
# never swapped.
#
# Emitted unconditionally, exactly like the eleven deferred scripts
# below: most pages carry no refresh loop at all and the attributes are
# inert there, which is this file's established convention rather than
# an oversight.
REFRESH_PAUSED_TEXT = "Paused"
REFRESH_RECONNECTING_TEXT = "Reconnecting…"

# Must equal the attribute names companion/static/freshness.js reads.
REFRESH_PAUSED_ATTR = "data-refresh-paused-text"
REFRESH_RECONNECTING_ATTR = "data-refresh-reconnecting-text"


# --- 23-06-PLAN.md Task 1 (D1/CFG-35): the swap registry --------------
#
# companion/static/freshness.js used to carry one hard-coded list of
# five selectors, duplicated in companion/pages/health_page.py and
# pinned equal. D1 puts the same loop on Home and on the Display scope,
# and three hand-maintained tuples is the shape scope_groups()'s own
# SCOPE_ALL already taught this codebase not to build: they agree on the
# day they are written and drift silently afterwards, with no signal
# from any one of them alone.
#
# So: ONE mapping here, one page key rendered on <body> by page_shell()
# below, and one object literal in the script mirroring this. The
# cross-file agreement is pinned entry-for-entry AND key-for-key by
# companion/test_status_pages.py, in both directions — a key the script
# carries and this mapping does not is the drift the one-tuple pin
# structurally could not see.
#
# THE KEYS ARE nav_slug()'s OWN VALUES, never a second vocabulary:
# page_shell() already receives exactly this string as `active`, so the
# key has one definition site too (companion/app.py's _page_shell_for()
# calls nav_slug(route) once for every authenticated page).
REFRESH_PAGE_ATTR = "data-refresh-page"
REFRESH_PAGE_HOME = nav_slug(HOME_ROUTE)
REFRESH_PAGE_DISPLAY = nav_slug(DISPLAY_ROUTE)
REFRESH_PAGE_HEALTH = nav_slug(HEALTH_ROUTE)

# The marker a region carries while it holds an OPTIMISTIC control whose
# server confirmation has not arrived (D1 races D2 — 23-RESEARCH.md's
# own coupling). The swap skips any region containing it, because the
# swap is the thing that would repaint a flip the user just made with
# the server's older answer, making the control appear to bounce back.
# Implemented in the swap by 23-06; plan 23-07 sets the attribute on its
# own control and nothing else has to change. Duplicated into
# freshness.js rather than imported — a static asset is not a Python
# module — and pinned by companion/test_status_pages.py, exactly like
# every other cross-file literal in this file.
REFRESH_PENDING_ATTR = "data-pending"

# 19-09-PLAN.md (D-02), moved here in full by 23-06-PLAN.md Task 1: the
# single, greppable definition of every DOM region
# companion/static/freshness.js swaps wholesale, replacing each node
# with its own equivalent from a fetched copy of the same page.
# Duplicated rather than imported — freshness.js is a static asset, not
# a Python module — matching the BATTERY_READOUT_ID/SPARKLINE_HIT_CLASS
# cross-file contract companion/pages/health_page.py carries. Any change
# to the script's own registry must change this mapping too.
#
# HEALTH (19-09-PLAN.md's own five, in their original order):
# deliberately EXCLUDES the sparkline <svg>/.sparkline-hit, the registry
# card and its filter bar, and every <details> disclosure — swapping any
# of those would leave companion/static/battery-trend.js's chart or
# companion/static/list-filter.js's filter permanently dead (each
# captures its DOM once, with no re-init hook) or would silently discard
# an in-progress filter query. See freshness.js's own header for the
# fuller record of this trade.
#
# `a[href="/health"]` — not a ".dot"/".nav-notification" selector — is
# the nav-severity swap target on purpose: the severity dot only exists
# in the DOM when severity is "warn"/"error" (_health_alert_markup()
# renders nothing at all for "ok"), so a dot-only selector would have
# nothing to replace on the far more common transition where severity
# newly clears. The whole nav link is always present in both documents
# regardless of severity, in both nav renderings (sidebar_nav() and
# _tab_bar_html()), so swapping it whole is what keeps the swap correct
# across every severity transition, not just a fixed dot.
#
# HOME (23-06-PLAN.md Task 2): the four regions that actually change
# between polls, plus the freshness line. The strip is where the frame's
# state is claimed and the tiles are what a glance reads; the picture is
# the thing a new render produces; the recent-flights SECTION rather
# than its <ul> is the target so the empty-state-to-list transition is
# covered too (a node present on only one side is never swapped — see
# freshness.js's own comment on that accepted cost). The freshness line
# is here for the same reason it is on Health: it carries data-loaded-at
# and the state badge the loop rebuilds inside it.
# Deliberately NOT nested: no entry here contains another, so no swap
# can detach a node another entry is about to replace.
#
# DISPLAY (23-06-PLAN.md Task 2): deliberately the strip and the
# freshness line and NOTHING ELSE — and this asymmetry with Home is a
# decision, not an omission for a later reader to "complete".
# Everything else on that page is a form, and a form is the one thing a
# swap must never touch: replacing a fieldset under a half-typed value
# discards it silently, and 22-01/B1 (that page rendered unsaveable) is
# the defect of record for what goes wrong when this page's form is
# treated as ordinary markup. The dirty-form stand-down in freshness.js
# is the second belt on the same braces.
REFRESH_SWAP_SELECTORS_BY_PAGE = {
    REFRESH_PAGE_HOME: (
        ".page-header__freshness",
        ".frame-strip",
        ".home-status-grid",
        "figure.preview-frame",
        'section[aria-labelledby="home-flights"]',
    ),
    REFRESH_PAGE_DISPLAY: (
        ".page-header__freshness",
        ".frame-strip",
    ),
    REFRESH_PAGE_HEALTH: (
        ".dashboard-grid",
        "div.banner--anomaly, div.banner--warn",
        "section.banner",
        ".page-header__freshness",
        'a[href="/health"]',
    ),
}


def _tab_bar_html(active, health_alert=None, device_config=None):
    """The bottom tab bar — the THIRD nav rendering (X9, locked to this
    mechanism by D-10), shown by page_shell() below 960px only.

    D-10 is locked and non-discretionary: this is a bottom tab bar, NOT
    an overlay drawer. `.claude/skills/sketch-findings-skypane/
    references/mobile-navigation.md` carries a locked REJECTED verdict on
    the absolute-positioned overlay for the primary nav, established by
    real-device testing during 06.6.1-06 — an out-of-flow panel could
    only ever cover content, never push it, which is exactly why the
    shipped hamburger dropdown is in-flow via `flex-basis: 100%`. That
    verdict is untouched by this function and must stay that way.

    Consumes `_nav_groups()` — and therefore `_nav_links()` — exactly
    like `sidebar_nav()` and `_mobile_nav_html()` do. This is that
    helper's THIRD consumer, not a hand-listed copy of the routes: the
    structural guarantee that the three renderings can never disagree
    about the tab set is the entire reason this module iterates NAV_TABS
    in one place, and hand-listing "/", "/display", "/flights",
    "/airlines" here would quietly retire it. Adding a route to
    NAV_GROUPS changes all three renderings together or none of them.

    The everyday/Advanced split is read from `_nav_groups()`'s own group
    LABEL, not from a second list: the unlabelled group is the four
    everyday destinations (each its own cell), and the labelled
    ("Advanced") group is what the "More" sheet holds. That is the same
    structure `sidebar_nav()` already renders as a `.nav-group`.

    "More" is a native `<details>`/`<summary>`, deliberately: it is
    keyboard-operable, announced by screen readers as a disclosure, and
    FULLY FUNCTIONAL WITH SCRIPTS BLOCKED. The no-JS floor (D-09) is met
    by construction here rather than by a fallback path that could rot —
    this file emits no script hook for it and
    companion/static/nav-dropdown.js never looks it up. Its open state
    resets naturally on navigation (a page load), so there is no
    close-on-navigate logic to write either.

    The sheet's upward `position: absolute` (see the `.tab-bar__more-
    panel` rule in companion/static/style.css) is NOT a reversal of the
    rejected-overlay verdict above. That verdict is specifically about
    the PRIMARY nav's push-versus-overlay behaviour on a component that
    must be able to push page content down; this is a two-item secondary
    sheet anchored to an already-fixed bar that pushes nothing and never
    could. Recorded here, and in the stylesheet, so a future reader does
    not read the one as a reversal of the other.

    When the current page is one of the Advanced destinations the More
    summary wears the active pill, so a collapsed bar never lies about
    where you are; `aria-current="page"` stays on the one real link
    (T-22-53), never on the summary, since a `<summary>` is a disclosure
    control and not the current page.

    `health_alert` (`None`/`"ok"`/`"warn"`/`"error"`, the same contract
    `sidebar_nav()` and `_mobile_nav_html()` take): drawn on the More
    SUMMARY rather than on the Health link inside the sheet. This is the
    one deliberate divergence from the other two renderings and it is a
    correctness point, not a style choice — the sheet is collapsed by
    default, so a dot inside it would be invisible at exactly the moment
    it has something to say. The summary is the visible cell that leads
    to Health, and `_health_alert_markup()`'s own visually-hidden suffix
    rides along with it, so the count stays exactly one per nav renderer.

    Returns `""` when `device_config` is falsy — the identical "no
    request context available" degrade contract `nav_status_html()`
    above already documents, which is what keeps the bar off the login
    shell, the 404 and every pre-session page: a page rendered before a
    session exists has no destinations to offer. Nav visibility has
    always been presentation-only in this app (T-22-52); `/health` and
    `/device` stay session-gated on the server regardless of which
    rendering links to them.
    """
    if not device_config:
        return ""
    cells = []
    sheet_links = []
    sheet_holds_active = False
    for group_label, group_links in _nav_groups(active):
        for is_active, route, label, slug in group_links:
            aria_current = ' aria-current="page"' if is_active else ""
            if group_label:
                sheet_holds_active = sheet_holds_active or is_active
                css_class = (
                    "mobile-nav__link mobile-nav__link--active"
                    if is_active else "mobile-nav__link")
                # .mobile-nav__link is REUSED verbatim rather than
                # re-declared: 22-UI-SPEC.md §3.1 puts the sheet's rows
                # at "`.mobile-nav__link`'s own 44px / 16px geometry",
                # and reusing the class is what makes that literally
                # true instead of a second set of numbers to keep in
                # step with quick task 260902-qkm's restored 44px floor.
                sheet_links.append(
                    '<a class="%s" href="%s"%s>%s</a>'
                    % (css_class, route, aria_current, label))
                continue
            css_class = (
                "tab-bar__link tab-bar__link--active"
                if is_active else "tab-bar__link")
            cells.append(
                '<a class="%s" href="%s"%s>%s</a>'
                % (css_class, route, aria_current,
                   _tab_bar_cell_body(NAV_ICON_IDS.get(slug, ""), label)))
    summary_class = (
        "tab-bar__link tab-bar__link--active"
        if sheet_holds_active else "tab-bar__link")
    alert_html = (
        _health_alert_markup(health_alert)
        if health_alert in ("warn", "error") else "")
    cells.append(
        '<details class="tab-bar__more">'
        '<summary class="%s">%s</summary>'
        '<div class="tab-bar__more-panel">%s</div>'
        "</details>"
        % (summary_class,
           _tab_bar_cell_body(
               TAB_BAR_MORE_ICON_ID,
               escape_html(i18n.t(TAB_BAR_MORE_LABEL)),
               extra_html=alert_html),
           "".join(sheet_links)))
    return (
        '<nav class="tab-bar" aria-label="%s">%s</nav>'
    ) % (
        # The same translated landmark name sidebar_nav() uses. Exactly
        # one of the two is ever exposed to the accessibility tree,
        # because companion/static/style.css's 960px rule removes the
        # losing copy with `display: none` — which takes it out of the
        # layout, the tab order and the accessibility tree together.
        # This is the SAME invariant page_shell()'s own comment already
        # states for the sidebar/dropdown pair; the tab bar replaces the
        # dropdown as the sub-960px half of it.
        escape_html(i18n.t("Primary navigation")),
        "".join(cells))


def _tab_bar_cell_body(icon_id, label, extra_html=""):
    """One tab cell's inner icon-above-label stack, wrapped in the pill
    span the active/hover treatments paint.

    The pill is a WRAPPER inside the cell rather than the cell itself
    (22-UI-SPEC.md §3.1): the cell keeps its full 78x56px tap area while
    the tint is inset from the cell edge, so the active signal reads as
    a pill and not as a full-bleed block. `label` arrives already
    escaped from `_nav_links()` (or escaped at this function's call site
    for the "More" cell); `extra_html` is already-built safe markup,
    interpolated verbatim exactly like `_health_alert_markup()`'s output
    is in `sidebar_nav()`.
    """
    return (
        '<span class="tab-bar__pill">%s'
        '<span class="tab-bar__label">%s</span>%s</span>'
    ) % (
        icon_html(icon_id, extra_class="tab-bar__icon"), label, extra_html)


def _theme_form_html(resolved_theme):
    # 22-08-PLAN.md Task 2 (D-06/B16): a function-scoped lookup table,
    # not `choice.capitalize()` — companion/test_i18n.py's ast-based
    # scanner cannot fold a `.capitalize()` method call back to a
    # literal, so a call shaped `i18n.t(choice.capitalize())` would be
    # scanner-invisible (Check 1 would never demand "Auto"/"Light"/
    # "Dark" have a catalogue entry, and Check 2 would then have to
    # carry them as an undocumented-looking dead-translation exception).
    # This table mirrors the scanner's own documented "a builder
    # constructs its own small lookup table function-locally, then
    # indexes it with a runtime loop variable inside i18n.t()" pattern
    # (test_i18n.py's Pass 1b comment) — `choice` (the loop variable
    # below) indexes it inside the very i18n.t() call the scanner traces.
    _THEME_LABEL_TEXT = {"auto": "Auto", "light": "Light", "dark": "Dark"}
    options = []
    for choice in UI_THEME_CHOICES:
        is_active = choice == resolved_theme
        css_class = (
            "theme-option theme-option--active"
            if is_active else "theme-option")
        options.append(
            '<button type="submit" name="ui_theme" value="%s" class="%s" aria-pressed="%s">%s</button>'
            % (escape_html(choice), css_class, "true" if is_active else "false",
               # `choice` itself ("auto"/"light"/"dark") is the form's own
               # submitted value and stays an untranslated identifier
               # (D-05); only the rendered label text is translated —
               # "Auto"/"Light"/"Dark" were all still English under a
               # French sidebar.
               escape_html(i18n.t(_THEME_LABEL_TEXT[choice]))))
    # D-02/D-29 (20-01-PLAN.md Task 3, 20-UI-SPEC.md §I): an aria-label
    # disambiguates this now-identical-looking segmented group from the
    # two new siblings below — the theme ids ("Auto"/"Light"/"Dark")
    # are identifiers already, so only the group label is translated.
    return (
        '<form class="theme-form" method="post" action="/ui-theme" aria-label="%s">%s</form>'
        % (escape_html(i18n.t("Theme")), "".join(options)))


def _lang_form_html(resolved_lang):
    """The FR/EN language switch (D-02, 20-01-PLAN.md Task 3) — a
    sibling of _theme_form_html() above, identical in shape. "FR"/"EN"
    are identifiers (D-05) and are never passed through i18n.t().
    """
    options = []
    for choice in prefs.LANG_CHOICES:
        is_active = choice == resolved_lang
        css_class = (
            "theme-option theme-option--active"
            if is_active else "theme-option")
        options.append(
            '<button type="submit" name="ui_lang" value="%s" class="%s" aria-pressed="%s">%s</button>'
            % (escape_html(choice), css_class, "true" if is_active else "false",
               escape_html(choice.upper())))
    return (
        '<form class="theme-form" method="post" action="/ui-lang" aria-label="%s">%s</form>'
        % (escape_html(i18n.t("Language")), "".join(options)))


    # D-17 (21-01-PLAN.md Task 1): _mode_form_html() is deleted along
    # with the rest of the simple-mode mechanism it fed.


def _logout_form_html():
    """The POST `/logout` sign-out control (06.6.2-05, D-11/D-17), shared
    verbatim by both the sidebar footer and the mobile-nav dropdown
    footer built below — one write site for the Sign out control, never
    two independent copies.

    The literal `/logout` path is hard-coded here rather than imported
    from `companion.app` — the same precedent `_theme_form_html()`'s own
    hard-coded `action="/ui-theme"` literal already sets, documented
    there for the same reason: `companion/app.py` imports this module,
    so the reverse import would be a cycle.

    `method="post"` matters: D-11 moves `/logout` off GET specifically so
    a stray prefetch, crawler, or `<img src="/logout">`-shaped link can
    no longer end a session. A plain `<a href="/logout">` here would
    reopen exactly that hole.
    """
    return (
        '<form method="post" action="/logout" class="logout-form">'
        '<button type="submit">%s</button>'
        "</form>"
    ) % escape_html(i18n.t("Sign out"))


def _mobile_nav_html(
        active, theme_form_html, health_alert=None, lang_form_html="",
        device_config=None):
    """The hamburger toggle button plus the dropdown panel it controls —
    the <960px preferences panel (D-06, 06.6.1-UI-SPEC.md's Layout
    Contract; reduced to preferences by 22-14-PLAN.md Task 2).

    22-14-PLAN.md Task 2 (X9/D-10, 22-UI-SPEC.md §3.1): this panel no
    longer holds the destination links, and therefore no longer carries
    a navigation landmark of its own. Its `<nav class="mobile-nav__nav">`
    block WAS the ~420px page shove the audit measured on a 390x844
    viewport — a near-full-screen push to reach any page — and
    `_tab_bar_html()` above now owns destinations at zero page shift.
    What is left is the state reminder, then the language and theme
    switches, then Sign out: preferences, which is what the renamed
    NAV_TOGGLE_LABEL now says out loud.

    The in-flow `flex-basis: 100%` push-down MECHANISM is untouched and
    must stay untouched — it is the recorded fix for the rejected
    absolute-positioned overlay (06.6.1-06) and this plan does not
    reopen it; only the panel's CONTENTS shrank.

    `health_alert` is consequently no longer drawn here: with the Health
    link gone from this panel there is no link to hang the dot on. The
    "one notification dot per nav renderer" contract is unchanged — the
    two renderers are now `sidebar_nav()` and `_tab_bar_html()`. The
    parameter is KEPT rather than removed so `page_shell()`'s own call
    site and every positional caller stay as they are; see the
    no-op note at its use site below.

    `theme_form_html` is taken as a parameter rather than built here via
    _theme_form_html(), so page_shell() keeps building it exactly once
    and passing the same string to both copies — this is what makes the
    "both theme-form copies present" check meaningful rather than an
    accident. `lang_form_html` (D-02, 20-01-PLAN.md Task 3) follows the
    identical discipline — page_shell() builds both exactly once and
    passes the same strings to both footer copies, so they can never
    drift. D-17 (21-01-PLAN.md Task 1): the sibling `mode_form_html`
    parameter is removed outright, not merely defaulted — the footer
    slot it fed no longer exists.

    The panel is always rendered without MOBILE_NAV_OPEN_CLASS — the
    server never renders it open. A server-rendered open state would
    flash the menu open on every page load; companion/static/
    nav-dropdown.js is what adds/removes the class client-side, keyed off
    the toggle's own aria-expanded attribute (the single source of truth
    for the open state, never a second variable to keep in sync).

    `health_alert` (06.6.2-06/UXA-14) is now a deliberate NO-OP here —
    22-14-PLAN.md Task 2 moved the destination links, and with them the
    Health link the dot attached to, onto `_tab_bar_html()`. It is read
    below only to keep the parameter honest for linters and readers; the
    dot itself is drawn by `sidebar_nav()` and `_tab_bar_html()`, which
    is still exactly one per nav renderer.

    `device_config` (D-03, 21-04-PLAN.md Task 2): threaded straight to
    `nav_status_html()`, whose own reminder markup is the first child of
    `#mobile-nav` — mirroring `sidebar_nav()`'s own "under the brand,
    above the list" placement exactly, and now its ONLY non-footer
    child. `None` renders no reminder at all.
    """
    # 22-14-PLAN.md Task 2: `health_alert` is accepted and deliberately
    # unused (see the docstring above). Named here rather than dropped
    # from the signature so every existing keyword call site is
    # unchanged, and referenced so it cannot be mistaken for an
    # oversight.
    del health_alert
    toggle_html = (
        '<button type="button" id="%s" class="site-nav-toggle" '
        'aria-label="%s" aria-expanded="false" aria-controls="%s">%s</button>'
    ) % (
        NAV_TOGGLE_ID, escape_html(i18n.t(NAV_TOGGLE_LABEL)), MOBILE_NAV_ID,
        icon_html("icon-hamburger", size=24))
    # D-02 (20-01-PLAN.md Task 3): resolved order — language, theme,
    # Sign out. D-17 (21-01-PLAN.md Task 1, 21-UI-SPEC.md §G): the
    # simple-mode switch that used to sit between theme and Sign out
    # is deleted; the footer now holds exactly two switches.
    footer_html = (
        '<div class="mobile-nav__footer">%s%s%s</div>'
        % (lang_form_html, theme_form_html, _logout_form_html()))
    # 22-14-PLAN.md Task 2 (X9/D-10): the `<nav class="mobile-nav__nav">`
    # that used to sit between the reminder and the footer is REMOVED,
    # not merely emptied — an empty navigation landmark would still be
    # announced, and the panel's own 22-08 "Primary navigation"
    # aria-label goes with it, so the sub-960px landmark is now
    # `_tab_bar_html()`'s. The document still carries exactly two
    # landmarks with that name (sidebar + tab bar) and still exposes
    # exactly one at any viewport width.
    panel_html = (
        '<div id="%s" class="mobile-nav">'
        "%s"
        "%s"
        "</div>"
    ) % (
        MOBILE_NAV_ID, nav_status_html(device_config, active=active),
        footer_html)
    return toggle_html + panel_html


def login_shell(body, ui_theme="auto", lang=None):
    """A dedicated, minimal HTML5 document for the pre-authentication
    login page — 06.6.2-07 (UXA-03).

    This function exists specifically because page_shell() always
    renders the full authenticated sidebar/mobile-nav/theme-form-footer
    regardless of the `active=""` value login's old call site passed —
    that is UXA-03's root cause (a real, reproduced production defect:
    the login page visually implied the whole site's navigation was
    usable before signing in). login_shell() is a deliberately
    separate, smaller sibling of page_shell(), not a parameterized
    branch inside it — it shares page_shell()'s outer document
    structure (doctype, `<html lang="..." data-ui-theme="...">`,
    `<head>` with charset/viewport/title/stylesheet link/
    FAVICON_LINK_HTML, reusing that constant rather than duplicating
    the data-URI literal) but its `<body>` contains only the login
    card: no ICON_DEFS_HTML sprite (nothing on this page uses an
    icon), no skip link (there is no nav to skip past), no sidebar, no
    mobile-nav dropdown, no NAV_DROPDOWN_SCRIPT_SRC script tag.

    22-13-PLAN.md Task 2 (X3) corrects the last clause of that
    sentence, which had been true until this plan and is no longer:
    this shell emits EXACTLY ONE deferred script tag — the login
    card's own script, sourced from the module constant defined beside
    its eleven siblings near the top of this file — and no others. It
    is still not the NAV_DROPDOWN_SCRIPT_SRC tag (there is no nav here
    to drop down), and none of page_shell()'s eleven other script tags
    appear either. That one script is what the login card's
    show-password toggle and its live lockout countdown load from;
    without it both would be dead markup, since companion/app.py's
    login route is a bare `return layout.login_shell(body,
    ui_theme=...)` with no script emission of its own to extend.
    Leaving the old "emits no script tag" wording in place would have
    been the same stale-doc failure D-05 had to fix in
    concise_timestamp_html().

    (This paragraph names the constant by description rather than by
    token on purpose: 22-13-PLAN.md Task 2's own acceptance criterion
    counts occurrences of that token in this file and expects exactly
    the definition and its one use.)

    `body` is the caller's own already-built, already-escaped markup —
    the same "caller has escaped its own dynamic parts" contract every
    other body-accepting builder in this module follows (page_shell(),
    stat_tile(), etc.) — and is interpolated verbatim into
    `<div class="login-card">`.

    `lang` (D-03, 20-01-PLAN.md Task 3): defaults to `None`, resolved
    to `prefs.current_lang()` — always one of `prefs.LANG_CHOICES`, so
    the `<html lang="...">` attribute is never built from an
    unvalidated value. `companion/app.py`'s pre-session callers
    (login, 404) call `prefs.set_request_prefs(lang=...)` themselves
    before rendering, exactly like the login route already does for
    `ui_theme` via `_resolved_ui_theme()`.
    """
    resolved_theme = ui_theme if ui_theme in UI_THEME_CHOICES else "auto"
    resolved_lang = lang if lang in prefs.LANG_CHOICES else prefs.current_lang()
    return (
        "<!DOCTYPE html>\n"
        '<html lang="%s" data-ui-theme="%s">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>%s - %s</title>\n"
        '<link rel="stylesheet" href="/static/style.css">\n'
        "%s\n"
        "</head>\n"
        "<body>\n"
        '<div class="login-shell">\n'
        '<div class="login-card">\n'
        "%s\n"
        "</div>\n"
        "</div>\n"
        '<script src="%s" defer></script>\n'
        "</body>\n"
        "</html>\n"
    ) % (
        escape_html(resolved_lang),
        escape_html(resolved_theme),
        # 22-08-PLAN.md Task 1 (D-06/B16): the login `<title>` literal
        # lived here as "Login - %s" (hard-coded English), not in
        # companion/app.py — only the "Login" half is translated; the
        # product-name half (SITE_TITLE) is never translated (D-05: a
        # brand name), keeping the same "<page> - <product>" shape a
        # French title reads as page_shell()'s own <title> does.
        escape_html(i18n.t("Login")),
        escape_html(SITE_TITLE),
        FAVICON_LINK_HTML,
        body,
        LOGIN_CARD_SCRIPT_SRC,
    )


# 06.6.4.1.1-04 (D-17): a substitution token, never markup that ships. It
# has exactly one definition site (here). page_header() emits it as the
# last thing in its returned string; page_shell() below is the only
# consumer — it swaps the token for the flash banner when the token is
# present (every page built on page_header()) and unconditionally strips
# any leftover occurrence before the response is returned, so it can
# never reach the browser on any path, flash or no-flash.
FLASH_SLOT_MARKER = "<!--flash-slot-->"


# --- 23-06-PLAN.md Task 2 (D1/CFG-35): the freshness line -------------
#
# Promoted here verbatim from companion/pages/health_page.py, which built
# it alone until D1 put the same refresh loop on Home and on the Display
# scope. ONE definition site, three call sites — the same contract
# frame_strip_html() and sidebar_nav() already state in their own
# docstrings, and for the same reason: three copies of a line whose
# markup is read by two scripts and pinned by four harnesses would drift
# the first time one of them was edited.
#
# The three strings below moved with it. companion/pages/health_page.py
# keeps all three NAMES, resolving from here, because shipped harness
# checks and other call sites use them.
REFRESH_PILL_TEXT = "Updating…"

# 23-05-PLAN.md Task 2 (D22's remainder): the hook
# companion/static/freshness.js toggles its breathing class on.
# Duplicated rather than imported — freshness.js is a static asset, not
# a Python module — matching every other cross-file literal here.
REFRESH_LIVE_DOT_ATTR = "data-refresh-live-dot"

# 19-09-PLAN.md (D-02, A-20): SUPERSEDED — PERSISTENT_FRESHNESS_PREFIX_TEXT
# used to read "Live — refreshed ", prefixing a
# concise_timestamp_html(now, now) timestamp. That timestamp's own
# relative-age suffix ("(0s ago)") was structurally always zero: `now`
# is computed exactly once per request by page_context() and immediately
# fed back into the very timestamp claiming to be "(Ns ago)" of itself —
# so the line asserted a liveness the render-time mechanism never
# actually measured. This is the plain, honest label that replaced it.
FRESHNESS_PREFIX_TEXT = "Updated "

# 22-06-PLAN.md Task 2 (D-05, B4), promoted here by 23-06-PLAN.md Task 2
# together with the freshness line that needs it: a `now_parsed`
# guaranteed to fall on a DIFFERENT Europe/Paris calendar day than any
# real device reading (no SkyPane device predates this constant), so
# passing it to local_clock_text() forces that function's own cross-day
# "D Mon HH:MM" branch — reusing the one formatter (D-05's own rule)
# rather than re-deriving a second, competing day-plus-clock format.
FULL_TIMESTAMP_SENTINEL_NOW = datetime(1970, 1, 1, tzinfo=ZoneInfo("UTC"))


def full_local_timestamp_text(ts):
    """"D Mon HH:MM" in Europe/Paris — the full local timestamp every
    `title`/`aria-label`/`data-when` this app emits for a stored instant
    carries (D-05, B4), via `local_clock_text()`'s own cross-day branch
    (forced by `FULL_TIMESTAMP_SENTINEL_NOW` above), never a bare clock
    and never the raw UTC ISO that finding replaced.

    Falls back to the raw `ts` string (never raising) when it fails to
    parse — the same graceful-degradation precedent every sibling here
    sets. `companion/pages/health_page.py` keeps its own
    `_full_local_timestamp_text()` name as a delegate to this.
    """
    parsed = parse_iso(ts)
    if parsed is None:
        return ts or ""
    return local_clock_text(parsed, now_parsed=FULL_TIMESTAMP_SENTINEL_NOW)


def freshness_line_html(now, lang=None):
    """The page-header freshness line: a neutral live dot, the "Updated "
    prefix, the clock element and the hidden "Updating…" pill that
    carries `data-loaded-at`, all inside ONE block-level wrapper.

    Returns "" when `now` is falsy. A caller with no render instant has
    nothing honest to put here, and an element carrying an empty or
    invented instant reads as a correct time to a script — the same
    degrade `frame_strip_html()` applies when it has no next wake, and
    the same one `relative_time_html()` applies to an unparseable value.
    With no marker there is no `[data-loaded-at]`, so
    `companion/static/freshness.js` returns at its first guard and that
    page simply has no loop.

    `lang` is the trailing keyword every sibling here carries; its `None`
    resolves through `i18n.t()`'s own request-language default.

    THIS IS A RAW-MARKUP-PRODUCING FUNCTION: callers interpolate the
    return value verbatim, into `page_header()`'s `freshness_html` slot,
    and never re-escape it. Everything interpolated below crosses
    escape_html() at its own site.

    The three call sites are Health, Home and the Display scope
    (23-06-PLAN.md Task 2, D1/CFG-35). The wrapper is one of every one of
    those pages' own swap targets, so the line a swap replaces and the
    line the ticker advances are the same one.
    """
    if not now:
        return ""
    # 260902-chc: SUPERSEDED — this used to be a manual Refresh link
    # (D-12/UXA-13, see the reversal record above this function). It is
    # now the hidden-by-default "Updating…" pill companion/static/
    # freshness.js reveals just before each visibility-gated reload.
    # `data-loaded-at` survives the reversal unchanged — `now` is
    # already computed once per request by companion/app.py's
    # page_context() — and gains a second job there (a tab returning
    # from a long hidden stretch uses it to decide whether it owes an
    # immediate catch-up refresh; see freshness.js's own header).
    # escape_html() is required on `now` only: it used to be the sole
    # requester, back when REFRESH_PILL_TEXT was a static module
    # constant needing none. 20-03-PLAN.md Task 3 (D-05/T-20-03): a
    # translated string is not pre-escaped, so i18n.t(REFRESH_PILL_TEXT)
    # now goes through escape_html() too, like every other t() result.
    #
    # No ARIA role on the pill: a live region announces on content
    # mutation, not on a visibility change, so a role="status" pill whose
    # text never changes would announce nothing anyway — and the page
    # load this pill precedes is itself announced as a navigation by
    # every screen reader, making a second announcement redundant. The
    # real accessibility cost this mechanism carries and does not solve:
    # a reload that fires while a screen-reader user is reading with
    # focus on the document body returns their virtual cursor to the
    # top, and freshness.js's interaction-skip guard cannot detect that
    # state. Accepted in writing, not left as an omission: the lever if
    # this bites is the refresh interval, not the announcement, and a
    # live screen-reader pass is named in this task's SUMMARY.
    pill_html = (
        '<span class="refresh-pill" data-refresh-pill data-loaded-at="%s" hidden>%s%s</span>'
        % (escape_html(now), icon_html("icon-refresh"), escape_html(i18n.t(REFRESH_PILL_TEXT))))
    # 23-05-PLAN.md Task 2 (D22's remainder): the neutral dot that
    # breathes while companion/static/freshness.js's loop is live and
    # stops the instant it pauses or starts reconnecting. Server-rendered
    # STATIC and neutral — the motion is one class that script adds and
    # removes, so a page with scripts blocked shows a still dot beside an
    # age that does not move, which is exactly what is true there.
    #
    # `.dot--off` with no modifier of its own: a refresh loop that is
    # listening is not a device verdict and must not borrow one's colour.
    # aria-hidden because it is decorative — the loop's real state is
    # already announced by the Paused/Reconnecting badge freshness.js
    # builds beside it, and a second, wordless signal would only repeat
    # it.
    dot_html = (
        '<span class="dot dot--off" %s aria-hidden="true"></span>'
        % REFRESH_LIVE_DOT_ATTR)
    # 19-09-PLAN.md (D-02, A-20): SUPERSEDED, and for the reason that
    # task itself named. It replaced concise_timestamp_html(now, now)'s
    # "(0s ago)" with a clock-only "Updated HH:MM", because the relative
    # half was STRUCTURALLY ALWAYS ZERO: `now` was computed once per
    # request and immediately fed back into a timestamp claiming to be
    # "(Ns ago)" of itself, so the line asserted a liveness the
    # render-time mechanism never measured. That defect was the frozen
    # zero, not the age.
    #
    # 23-05-PLAN.md Task 2 (D14/D22/CFG-34) removes the freeze rather
    # than the age. This is relative_time_html() over the same
    # instant `data-loaded-at` already carries, and
    # companion/static/relative-time.js rewrites it once a second —
    # "Updated 3m ago" on a page that has been open three minutes, which
    # is a claim about NOW rather than about a moment. A page saying
    # "Updated 14:32" tells the truth about an instant and says nothing
    # at all about whether it is still current; announcing its own
    # staleness is the whole point of D22.
    #
    # 23-06-PLAN.md: WHAT THE SERVER WRITES INTO THAT ELEMENT IS THE
    # CLOCK, not the ladder's zero bucket. 23-05 rendered "0s ago" here
    # and recorded the cost in its own SUMMARY (finding 2): with scripts
    # blocked nothing ever advances it, so that reader got a permanently
    # frozen "Updated 0s ago" — 19-09/A-20's own defect ("(0s ago)" was
    # structurally always zero) handed back to the one reader who cannot
    # see the ticker. The fix is the ordinary progressive-enhancement
    # shape the rest of this app already uses: the SERVER renders the
    # honest static thing and the SCRIPT upgrades it. The element, its
    # machine-readable `datetime` and its `data-relative` hook are
    # unchanged — only the text the server puts inside it — so with
    # scripts on the first repaint (one second after load, and after
    # every swap) turns "Updated 14:32" into "Updated 3m ago", and with
    # scripts blocked the line reads a clock that stays true forever.
    # Both readers get a true statement, which is the whole of the
    # no-JS floor's claim.
    #
    # The clock is `local_clock_text()` with `now_parsed` set to the same
    # instant — its same-day branch, i.e. a bare "HH:MM", identical in
    # both languages and identical to what this line rendered from
    # 19-09 until 23-05.
    #
    # Nothing is lost: the full Europe/Paris local timestamp stays on the
    # span's `title` (22-16's own D-05/CFG-28 conversion, unchanged).
    # `data-refresh-clock` is kept as this span's own hook for
    # companion/static/freshness.js — that file reads nothing from the
    # span itself (the whole wrapper is swapped instead), but the
    # attribute keeps the element easy to find from a future edit or a
    # live DOM inspection.
    #
    # Consequence worth stating: the freshness wrapper now differs from
    # its freshly-fetched counterpart on every cycle, because the live
    # age has advanced while the fetched one reads zero — so
    # freshness.js's "the region did not change" skip no longer applies
    # to this one region. That is correct rather than a regression: the
    # age really did change, and the swap is what resets it to the truth.
    # 22-12-PLAN.md Task 3 (C5): `mono` -> `time-value`. This page's own
    # "Updated HH:MM" was the last of the four treatments C5 replaces
    # here, and it was the one that most plainly broke the rule:
    # monospace is reserved for IDENTIFIERS — the callsign, the ICAO24
    # hex, the masked calendar URL — and a wall-clock time is not one.
    # `.time-value` is the single time-value role (sans, tabular
    # numerals, so the digits still hold their column as the clock
    # ticks), which is exactly what the monospace family was being used
    # for here. The base shape, not `--primary`: this is a caption under
    # the page title, not a headline.
    #
    # 22-16-PLAN.md's closing sweep (D-05/CFG-28). The `title` used to
    # carry the raw UTC ISO instant verbatim, and 22-12-PLAN.md left it
    # standing with a note saying why: 19-09-PLAN.md (D-02/A-20) put it
    # there deliberately and companion/test_status_pages.py pinned it by
    # name, so converting it meant deliberately re-targeting another
    # plan's pin. That is exactly what this plan owns.
    #
    # It fails two of D-05/CFG-28's own clauses at once: "every `title`
    # tooltip carries a local full timestamp", and "raw ISO survives
    # only behind a copy control" — a `title` is a tooltip, and this one
    # sits behind no `.copy-btn` at all, so the requirement could not be
    # honestly ticked while it stood.
    #
    # The conversion is the pattern 22-06-PLAN.md Task 3 already proved
    # on `concise_timestamp_html()`: the full Europe/Paris local
    # timestamp from `local_clock_text()`'s own cross-day branch, forced
    # by `_FULL_TIMESTAMP_SENTINEL_NOW`. This module already exposes it
    # as `_full_local_timestamp_text()`, which every battery `title`/
    # `aria-label`/`data-when` on this page has used since that plan —
    # so this is a fourth caller of an existing helper, not a second
    # date path, and it degrades identically (an unparseable value falls
    # back to the raw string rather than raising).
    #
    # What is NOT lost with the ISO: `data-loaded-at` on the refresh
    # pill still carries the real machine-readable instant, which is
    # what companion/static/freshness.js actually reads. The `title` was
    # only ever a human-facing tooltip.
    _now_parsed = parse_iso(now)
    _clock_text = (
        local_clock_text(_now_parsed, now_parsed=_now_parsed)
        if _now_parsed is not None else now)
    clock_html = (
        '<span class="time-value" data-refresh-clock title="%s">%s</span>'
        % (escape_html(full_local_timestamp_text(now)),
           relative_time_html(now, now, static_text=_clock_text)))
    # 21-02-PLAN.md (D-18): the Pause/Resume button that used to sit here
    # is deleted outright — no replacement control, no placeholder. The
    # freshness line is now just the prefix, the clock and the pill.
    #
    # Quick task 260903-peo (UIR-18): the pill and the clock still join
    # inside ONE block-level wrapper — load-bearing, not decorative.
    # `.page-header` is a plain block box; 260902-ep7 (BUG 1) fixed a
    # measured 28px title-to-purpose gap caused by a stranded inline-level
    # child (the bare pill span) forcing an anonymous block box between
    # the block <h1> and the block <p class="page-header__purpose">. The
    # pill escapes that only because `.page-header .refresh-pill` is
    # absolutely positioned; a second bare inline node next to it would
    # recreate the exact same condition. Wrapping both in one block-level
    # <p> keeps `.page-header`'s children all block-level, and
    # `.page-header .refresh-pill` — a descendant selector — still
    # matches straight through the wrapper, so the pill's `top: 8px;
    # right: 0` offsets (anchored to `.page-header`, the nearest
    # positioned ancestor, never the wrapper) are unchanged.
    #
    # This whole `<p class="page-header__freshness">` element is one of
    # REFRESH_SWAP_SELECTORS_BY_PAGE's own entries — freshness.js replaces it
    # wholesale from its own fetch, so a render-time value here is
    # honest for exactly as long as it takes the next successful swap to
    # replace it, never longer.
    freshness_html = (
        '<p class="page-header__freshness text-label">%s%s%s%s</p>'
        % (dot_html, escape_html(i18n.t(FRESHNESS_PREFIX_TEXT)),
           clock_html, pill_html))
    return freshness_html


def page_shell(
        title, active, body, ui_theme="auto", flash=None, banner=None,
        health_alert=None, lang=None, device_config=None):
    """Return a complete HTML5 document wrapping `body` in the shared shell.

    `title` and every nav label are escaped here. `body`, `flash` and
    `banner` are pre-built markup strings — the caller is responsible
    for having escaped their own dynamic parts (they are typically the
    output of this module's other builders, which already escape).

    `health_alert` (06.6.1-04, keyword-with-default, placed last so no
    positional call site shifts; 06.6.2-06/UXA-14 widened the contract
    from a boolean to a severity string) is threaded through to
    sidebar_nav() and (06.6.1-05) _mobile_nav_html(). It is `None`/`"ok"`
    (no dot) or `"warn"`/`"error"` (a dot with that class), a display
    signal only, defaulting to no dot, so any caller without a request
    context — login, 404, the preview-image error pages — draws no dot,
    which is correct rather than merely convenient.

    `lang` (D-03, 20-01-PLAN.md Task 3): defaults to `None`, resolved
    to `prefs.current_lang()` — always one of `prefs.LANG_CHOICES`. A
    `None` default is deliberate: no existing page-module call site
    (~40 of them) has to change, since `companion/app.py`'s
    `page_context()` already calls `prefs.set_request_prefs()` once
    per request before any page module renders.

    `device_config` (D-03, 21-04-PLAN.md Task 2, R-03): defaults to
    `None`, the exact same "no request context available" degrade
    contract `health_alert`'s own docstring above already documents —
    threaded through to both `sidebar_nav()` and `_mobile_nav_html()`,
    which each pass it straight to `nav_status_html()`. `companion/
    app.py`'s `_page_shell_for()` is the one call site that passes
    `ctx["device_config"]`, covering both the GET path and a rejected-
    save POST's redisplay; every other call site (login, 404, the
    preview-image error pages) leaves this `None`, so those pages'
    nav renders no reminder — byte-identical to this function's own
    pre-21-04 output.
    """
    resolved_theme = ui_theme if ui_theme in UI_THEME_CHOICES else "auto"
    resolved_lang = lang if lang in prefs.LANG_CHOICES else prefs.current_lang()
    sidebar_html = sidebar_nav(
        active, health_alert=health_alert, device_config=device_config)
    theme_form_html = _theme_form_html(resolved_theme)
    lang_form_html = _lang_form_html(resolved_lang)
    mobile_nav_html = _mobile_nav_html(
        active, theme_form_html, health_alert=health_alert,
        lang_form_html=lang_form_html, device_config=device_config)
    # 22-14-PLAN.md Task 1 (X9/D-10): the third nav rendering. `""` when
    # `device_config` is falsy — the 404 and the preview-image error
    # pages, which have no session and therefore no destinations to
    # offer, exactly like the state reminder above them. `<body>` then
    # carries TAB_BAR_BODY_CLASS only when the bar is really there, so
    # companion/static/style.css can reserve the bar's own clearance at
    # the foot of the page without reserving it on a page that has no
    # bar (a `:has()` selector would have been the other way to do this;
    # the file is pinned at exactly one `@supports selector(:has(*))`
    # block by companion/test_config_page.py, and a server-rendered
    # class costs nothing and degrades everywhere).
    tab_bar_html = _tab_bar_html(
        active, health_alert=health_alert, device_config=device_config)
    body_class_attr = (
        ' class="%s"' % TAB_BAR_BODY_CLASS if tab_bar_html else "")
    # T13 (22-15-PLAN.md Task 2): freshness.js's two neutral loop-state
    # strings, translated here and read client-side. See their constants
    # above for why they live on <body>.
    body_class_attr += (
        ' %s="%s" %s="%s"' % (
            REFRESH_PAUSED_ATTR,
            escape_html(i18n.t(REFRESH_PAUSED_TEXT)),
            REFRESH_RECONNECTING_ATTR,
            escape_html(i18n.t(REFRESH_RECONNECTING_TEXT))))
    # 23-06-PLAN.md Task 1 (D1/CFG-35): the page key that selects this
    # document's swap-region list out of REFRESH_SWAP_SELECTORS_BY_PAGE
    # above. On <body> for the reason the two attributes above are: the
    # freshness wrapper and the nav link are themselves swap targets, and
    # <body> is the one element no swap ever replaces.
    #
    # Rendered for EVERY page, including the ones that declare no
    # regions, and the guard is in the script rather than in whether the
    # attribute was emitted — the same "emitted unconditionally, inert
    # where it does not apply" convention the eleven deferred scripts and
    # the copy attributes above already follow. `active` is nav_slug()'s
    # own output, which is what makes the key set have one definition
    # site; an unknown key (a future page, a bare test render) selects
    # nothing and the loop returns.
    body_class_attr += ' %s="%s"' % (
        REFRESH_PAGE_ATTR, escape_html(active))
    # 23-05-PLAN.md Task 1 (D14/CFG-34): relative-time.js's nine
    # wordings, on <body> for exactly the reason the two above are —
    # several <time data-relative> elements sit inside freshness.js's
    # swap targets, and <body> is never swapped. Emitted
    # unconditionally, like every deferred script below: a page with no
    # relative time on it carries nine inert attributes, which is this
    # file's established convention and not an oversight.
    for _copy_attr, _copy_text in relative_copy_attrs():
        body_class_attr += ' %s="%s"' % (_copy_attr, escape_html(_copy_text))
    flash_html = flash or ""
    banner_html = banner or ""

    # 06.6.4.1.1-04 (D-17): move the flash banner to directly below the
    # page header instead of above the page title, so saving no longer
    # shifts the title down. `body` is one opaque pre-built string by
    # the time it reaches this function, so there is no structural
    # handle on "just after the header" — page_header() instead leaves
    # FLASH_SLOT_MARKER as a literal handle at exactly that point.
    #   - A page built on page_header() (every authenticated page today)
    #     carries the marker in `body`; the flash banner is spliced in
    #     right there and `flash_html` is cleared so it is not also
    #     emitted in its old pre-body slot.
    #   - A page that does NOT use page_header() (login, 404, and any
    #     future bare page) has no marker in `body`; `flash_html` is left
    #     untouched and keeps rendering in today's before-body slot, so
    #     no such caller has to change and none silently loses its
    #     banner.
    #   - The unconditional second replace() below guarantees the marker
    #     itself never reaches the browser, including on the no-flash
    #     path where `flash_html` is "" (nothing to splice in, but a
    #     `page_header()` body still carries the marker literal).
    if FLASH_SLOT_MARKER in body:
        body = body.replace(FLASH_SLOT_MARKER, flash_html, 1)
        flash_html = ""
    body = body.replace(FLASH_SLOT_MARKER, "")

    # 06.6.2-05 (D-17): the sidebar's theme picker and Sign out control,
    # grouped into one footer region — the exact artifact Phase 06.6.3
    # was told to expect by name (a .sidebar-footer wrapper). Replaces
    # the previous bare theme_form_html-only slot. D-02 (20-01-PLAN.md
    # Task 3): resolved order — language, theme, Sign out; this and
    # _mobile_nav_html()'s own footer_html must change together.
    # D-17 (21-01-PLAN.md Task 1, 21-UI-SPEC.md §G): the simple-mode
    # switch that used to sit between theme and Sign out is deleted —
    # the footer now holds exactly two switches, language then theme.
    sidebar_footer_html = (
        '<div class="sidebar-footer">%s%s%s</div>'
        % (lang_form_html, theme_form_html, _logout_form_html()))

    # 06.6.2-05 (UXA-10): the first focusable element in <body>, before
    # even ICON_DEFS_HTML — a keyboard/screen-reader user's very first
    # tab stop on every page.
    skip_link_html = (
        '<a class="skip-link" href="#%s">Skip to content</a>'
        % SKIP_LINK_TARGET_ID)

    # The <aside> deliberately precedes the <header> in source order: at
    # desktop width, where CSS hides the header entirely, a keyboard user
    # tabs into the visible sidebar navigation first, with no invisible
    # stops before it. Both nav copies (the sidebar and, 06.6.1-05, the
    # hamburger dropdown; 22-14-PLAN.md Task 1, the bottom tab bar that
    # takes the dropdown's landmark over) are always present in the DOM —
    # companion/static/style.css's 960px media query is the only thing
    # that decides which copy is visible, never anything in this function
    # (no inline styles, no boolean-hidden attribute, no ARIA visibility
    # hint). Because the two nav landmarks share the same "Primary
    # navigation" label and are toggled by the same CSS rule (never by
    # this function), exactly one navigation landmark is exposed to the
    # accessibility tree at any given viewport width — the 960px rule
    # removes the losing copy with display:none, which takes it out of
    # the layout, the tab order and the accessibility tree together, not
    # merely out of view. 06.6.1-04: ICON_DEFS_HTML is emitted here
    # unconditionally, once per document, immediately inside <body> and
    # before the dashboard-shell div — the only definition site for every
    # icon in the app. 06.6.1-05: the theme form is now rendered once in
    # the sidebar and once inside the hamburger dropdown panel (built by
    # _mobile_nav_html() above from the same theme_form_html string) —
    # it is no longer rendered a third time directly in the header, which
    # is what removes D-00's crush-bug root cause instead of re-tuning it
    # a second time. A single deferred <script> tag, referencing
    # NAV_DROPDOWN_SCRIPT_SRC, is emitted immediately before </body>.
    return (
        "<!DOCTYPE html>\n"
        '<html lang="%s" data-ui-theme="%s">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>%s - %s</title>\n"
        '<link rel="stylesheet" href="/static/style.css">\n'
        "%s\n"
        "</head>\n"
        "<body%s>\n"
        "%s\n"
        "%s\n"
        '<div class="dashboard-shell">\n'
        '<aside class="dashboard-sidebar">\n'
        '<span class="site-title sidebar-title">%s</span>\n'
        "%s\n"
        "%s\n"
        "</aside>\n"
        '<header class="site-header">\n'
        '<span class="site-title">%s</span>\n'
        "%s\n"
        "</header>\n"
        '<main class="page-content dashboard-main" id="%s" tabindex="-1">\n'
        "%s\n%s\n%s\n"
        "</main>\n"
        "</div>\n"
        # 22-14-PLAN.md Task 1 (X9/D-10): the tab bar sits OUTSIDE
        # .dashboard-shell and after it, so it is a sibling of the shell
        # rather than a descendant of the scrolled content column — a
        # `position: fixed` box inside .dashboard-main would still be
        # fixed to the viewport, but nesting it there would put it
        # inside the shell's own stacking/overflow context for no
        # reason. `""` on a page that renders no bar, which leaves this
        # slot emitting a bare newline exactly like the flash slot does.
        "%s\n"
        '<script src="%s" defer></script>\n'
        '<script src="%s" defer></script>\n'
        '<script src="%s" defer></script>\n'
        '<script src="%s" defer></script>\n'
        '<script src="%s" defer></script>\n'
        '<script src="%s" defer></script>\n'
        '<script src="%s" defer></script>\n'
        '<script src="%s" defer></script>\n'
        '<script src="%s" defer></script>\n'
        '<script src="%s" defer></script>\n'
        '<script src="%s" defer></script>\n'
        '<script src="%s" defer></script>\n'
        '<script src="%s" defer></script>\n'
        "</body>\n"
        "</html>\n"
    ) % (
        escape_html(resolved_lang),
        escape_html(resolved_theme),
        escape_html(title), escape_html(SITE_TITLE),
        FAVICON_LINK_HTML,
        body_class_attr,
        skip_link_html,
        ICON_DEFS_HTML,
        escape_html(SITE_TITLE),
        sidebar_html,
        sidebar_footer_html,
        escape_html(SITE_TITLE),
        mobile_nav_html,
        SKIP_LINK_TARGET_ID,
        flash_html, banner_html, body,
        tab_bar_html,
        NAV_DROPDOWN_SCRIPT_SRC,
        # 06.6.3: emitted unconditionally on every authenticated page,
        # matching nav-dropdown.js/battery-trend.js's own "served
        # everywhere, no-ops via guard clause" convention — never
        # conditionally included per page.
        DIRTY_STATE_SCRIPT_SRC,
        LIST_FILTER_SCRIPT_SRC,
        COPY_BUTTON_SCRIPT_SRC,
        FRESHNESS_SCRIPT_SRC,
        # 06.6.4.1-02 (D-20): sixth script, same unconditional/no-op-via-
        # guard-clause convention — served every page; since quick task
        # 260902-tli both History and the Airlines gallery render
        # #panel-lookup-dialog.
        PANEL_LOOKUP_SCRIPT_SRC,
        # Quick task 260903-peo (UIR-19): seventh script, same
        # unconditional/no-op-via-guard-clause convention — served every
        # page, since the flash banner it cleans up after is emitted by
        # this function for every authenticated page, not just one.
        FLASH_CLEANUP_SCRIPT_SRC,
        # 19-04-PLAN.md (D-18/A-35): eighth script, same unconditional/
        # no-op-via-guard-clause convention — served every page, since
        # only Settings renders #poll-trigger-btn.
        POLL_COOLDOWN_SCRIPT_SRC,
        # 19-11-PLAN.md Task 2 (D-08/A-26): ninth script, same
        # unconditional/no-op-via-guard-clause convention — served every
        # page, since only the Device page renders a
        # form[data-confirm] (the calendar disconnect form).
        CONFIRM_SUBMIT_SCRIPT_SRC,
        # 20-08-PLAN.md Task 3 (D-22..D-24): tenth script, same
        # unconditional/no-op-via-guard-clause convention — served every
        # page, since only Display (from 20-11) renders
        # .theme-live-preview img plus a .theme-chip-grid.
        THEME_PREVIEW_SCRIPT_SRC,
        # 21-03-PLAN.md Task 2 (D-15/R-12): eleventh script, same
        # unconditional/no-op-via-guard-clause convention — served every
        # page, since only Flights renders .flight-detail-row/
        # [data-row-toggle].
        FLIGHT_ROWS_SCRIPT_SRC,
        # 22-15-PLAN.md Task 3 (T14): twelfth script on this shell, same
        # unconditional convention — and here the convention is the
        # point rather than a habit. The guard is a DELEGATED document
        # level submit listener, so covering every form in the app costs
        # exactly one registration; a per-page include would be the
        # per-page handler this file exists to replace.
        SUBMIT_GUARD_SCRIPT_SRC,
        # 23-05-PLAN.md Task 1 (D14/CFG-34): thirteenth script on this
        # shell, same unconditional convention — and, as with
        # submit-guard.js above, the convention is the point rather than
        # a habit. The elements it ticks are produced by ONE builder
        # (relative_time_html(), reached by most callers through
        # concise_timestamp_html()), so no page module knows whether it
        # has one; a per-page include would have to enumerate a set the
        # pages do not own. Its own guard clause returns before
        # registering anything on a page with no such element.
        RELATIVE_TIME_SCRIPT_SRC,
    )


_FLASH_ROLES = {"status", "alert"}


def flash_banner(message, role="status"):
    """An accent-bordered confirmation block (D-07's save confirmation).

    `role` (06.6.2-06, UXA-07) is validated against `_FLASH_ROLES`
    (falling back to `"status"` for anything else) — the same
    whitelist-with-safe-fallback discipline `status_dot()`'s `state`
    parameter already uses — and rendered as the `<div>`'s ARIA `role`
    attribute, so a save/poll failure announces as `role="alert"`
    (assertive) while every other outcome stays `role="status"`
    (polite), chosen by the caller's real severity rather than one role
    for every outcome.
    """
    resolved_role = role if role in _FLASH_ROLES else "status"
    return (
        '<div class="banner banner--flash" role="%s">%s</div>'
        % (resolved_role, escape_html(message)))


def anomaly_banner(message, severity="error"):
    """A warning/destructive-bordered block for D-14's anomaly flagging.

    `severity` (06.6.2-06, UXA-14) chooses both the CSS class and the
    ARIA role: `"error"` (the default, preserving every existing
    positional/no-keyword call site's prior meaning) renders
    `banner--anomaly`/`role="alert"`; anything else (in practice only
    `"warn"`) renders the new `banner--warn`/`role="status"` — a
    warning-only Health state is announced politely, not as an
    assertive interruption.
    """
    css_class = "banner--anomaly" if severity == "error" else "banner--warn"
    role = "alert" if severity == "error" else "status"
    return (
        '<div class="banner %s" role="%s">%s</div>'
        % (css_class, role, escape_html(message)))


def status_dot(state, label, title=None, visually_hide_label=False):
    """A small coloured status indicator plus an escaped text label.

    `state` maps to exactly one of three fixed CSS class suffixes; an
    unrecognised state falls back to the warning class rather than
    emitting an arbitrary, attacker-influenceable class name.

    `title` (quick task 260902-w4t, UIR-04) is optional and defaults to
    None for backward compatibility: every pre-existing call site passes
    exactly two positional arguments, and when `title` is falsy the
    returned markup is character-for-character what it was before this
    parameter existed — no `title` attribute is emitted at all. When
    `title` is truthy it is escaped through the same `escape_html()`
    call `label` already goes through (the identical single-escaping
    discipline `concise_timestamp_html()` uses for its own `title`) and
    added as a `title="..."` attribute on the `dot-label` span, giving a
    shortened visible label room to carry a longer form as a tooltip.

    `visually_hide_label` (21-03-PLAN.md Task 1, D-15) is a
    keyword-with-default, byte-identical-when-falsy parameter, matching
    `stat_tile()`'s own `caption_title` contract: every pre-existing call
    site (which never passes this keyword) gets a return value that is
    character-for-character what this function returned before this
    parameter existed. Only Flights' desktop Corroboration cell
    (`history_page._history_table_html()`) passes `True` — the dot stays
    visible, the accessible name and `title` tooltip are unchanged, but
    the label span's class becomes `"dot-label visually-hidden"` instead
    of `"dot-label"`, removing the visible word so the column can shrink
    to a dot-only width (21-UI-SPEC.md §F). Health's own call sites
    (`health_page.py`) never pass this keyword and are unaffected.
    """
    css_class = _STATUS_DOT_CLASSES.get(state, _DEFAULT_STATUS_DOT_CLASS)
    title_attr = ' title="%s"' % escape_html(title) if title else ""
    label_class = "dot-label visually-hidden" if visually_hide_label else "dot-label"
    # 21-REVIEW.md WR-03: with the label clipped away, a title on that
    # span is unreachable by hover — it moves onto the dot itself, the
    # only visible element left, so the tooltip still exists. The
    # default (label visible) output is byte-identical to before.
    dot_title = title_attr if visually_hide_label else ""
    label_title = "" if visually_hide_label else title_attr
    return (
        '<span class="dot %s"%s></span><span class="%s"%s>%s</span>'
        % (css_class, dot_title, label_class, label_title, escape_html(label)))


def stat_tile(caption, content_html, status=None, icon=None, caption_title=None):
    """A status-coloured dashboard card wrapping already-built markup.

    `caption` is escaped here. `content_html` is the caller's own
    already-safe markup (e.g. status_dot()'s raw <span> pair,
    data_table()'s table, empty_state()'s block, or a hand-built <p>
    string) and is interpolated verbatim, with no call to
    escape_html() and no other transformation — re-encoding it here
    would double-encode already-escaped tags and print them as visible
    text instead of rendering. `status` maps to one of three fixed
    CSS class suffixes ("ok"/"warn"/"error"); None or an unrecognised
    value falls back to the accent-neutral class rather than emitting
    an arbitrary, attacker-influenceable class name.

    `icon` (06.6.1-04, D-02) is a whitelisted id from ICON_IDS — not
    markup — passed straight to icon_html(), which is this function's
    only route to injecting raw HTML beyond `content_html`; that is
    deliberate, so stat_tile() never grows a second free-form raw-markup
    parameter. When falsy (the default) or not a member of ICON_IDS, the
    caption renders exactly as it did before this parameter existed —
    every pre-existing call site is byte-identical. When it names a
    valid icon, the caption element becomes the icon markup (tinted via
    STAT_TILE_ICON_CLASS) followed by the escaped caption text in a
    <span>, so companion/static/style.css's flex caption rule lays them
    out on one line.

    `caption_title` (19-06, D-06) is an ATTRIBUTE VALUE, not markup — it
    is escaped here through the same escape_html() call `caption` and
    status_dot()'s own `title` parameter already go through, and is
    never interpolated as raw HTML. That is why adding it does not
    violate the "never grow a second free-form raw-markup parameter"
    rule stated above for `icon`: an attribute value and a markup
    fragment are different trust levels, and this parameter is the
    former. When falsy (the default), the returned string is
    BYTE-IDENTICAL to what this function returned before this
    parameter existed, on both the icon and no-icon branches — no
    `title` attribute is emitted at all. When truthy, a
    `title="{escaped caption_title}"` attribute is added to the
    `<p class="text-label stat-tile__caption">` element (the label
    itself) and nothing else changes. D-06's purpose: a household
    reader sees a plain-language label; the technical term a developer
    needs to grep/diagnose by stays one hover away instead of being
    deleted outright.
    """
    css_class = "stat-tile " + _STAT_TILE_BORDER_CLASSES.get(
        status, _DEFAULT_STAT_TILE_CLASS)
    icon_markup = icon_html(icon, extra_class=STAT_TILE_ICON_CLASS) if icon else ""
    if icon_markup:
        caption_html = icon_markup + "<span>%s</span>" % escape_html(caption)
    else:
        caption_html = escape_html(caption)
    title_attr = ' title="%s"' % escape_html(caption_title) if caption_title else ""
    return (
        '<div class="%s">'
        '<p class="text-label stat-tile__caption"%s>%s</p>'
        "%s"
        "</div>"
    ) % (css_class, title_attr, caption_html, content_html)


def _frame_strip_cell_html(extra_class, label_row_html, state_row_html, caption_row_html):
    """One Frame-strip cell wrapper (22-04-PLAN.md Task 1, B13): every
    cell — both switches and the update cell alike — is the SAME
    wrapper element with the SAME three-row internal structure (label,
    then state plus control, then caption); only `extra_class` (the
    switch cells' `quick-action quick-action--on/off` control-state
    modifier — the update cell never receives one) and each row's own
    content differ. A cell with nothing to put in a row still emits
    that row's own div, empty — an empty track, never an omitted row —
    which is what lets all three cells' rows line up instead of each
    cell laying itself out independently (today's Screen/Quiet-hours/
    Update cells measure 119/165/69px tall for exactly that reason).

    A harness asserts the three cells' ROW class attributes
    (`frame-strip__row frame-strip__row--label/--state/
    --caption`) are byte-identical across all three cells; the outer
    wrapper's own class list legitimately differs (only the two switch
    cells carry `quick-action`/`quick-action--on/off` — that left edge
    is a control-state signal, and painting it on the non-interactive
    update cell would claim a state it does not have).
    """
    cell_class = "frame-strip__cell"
    if extra_class:
        cell_class = cell_class + " " + extra_class
    return (
        '<div class="%s">'
        '<div class="frame-strip__row frame-strip__row--label">%s</div>'
        '<div class="frame-strip__row frame-strip__row--state">%s</div>'
        '<div class="frame-strip__row frame-strip__row--caption">%s</div>'
        "</div>"
    ) % (cell_class, label_row_html, state_row_html, caption_row_html)


def frame_strip_html(ctx, return_to, next_wake_iso=None):
    """The "Frame" strip (D-01/D-02/D-05, 21-CONTEXT.md; R-01; D-03/
    CFG-26, 22-02-PLAN.md/22-04-PLAN.md Task 1): one shared body, called
    identically by home_page.render() (with `return_to=HOME_ROUTE`) and
    config_page.render()'s Display scope (with `return_to=DISPLAY_
    ROUTE`) — the two pages' copies of the Screen/Quiet-hours instant
    switches and the next-update headline can therefore never disagree,
    the same "one function, two call sites" contract sidebar_nav()'s
    own docstring already states for the nav.

    `ctx["device_config"]` supplies `display_enabled`/`quiet_hours_
    enabled`/`quiet_hours_start`/`quiet_hours_end` — read with the
    exact same literal fallback defaults companion/pages/config_page.py's
    own display_group()/quiet_hours_group() resolve from server.
    device_config.DEFAULT_DISPLAY_ENABLED/DEFAULT_QUIET_HOURS_ENABLED/
    _START/_END. The literals are duplicated here, never imported,
    because this module's own docstring forbids importing anything
    from server/ (R-01) — `ctx["device_config"]` already carries these
    fields fully resolved on every real request (companion/app.py's
    page_context() calls server.device_config.load_device_config()
    once per request), so the fallback only matters for a bare/partial
    ctx built by a test or an empty-state render.

    `return_to` is written verbatim (escaped) into a hidden field on
    each switch's own form — R-02, 21-CONTEXT.md: `app._handle_quick_
    toggle()` is what validates it against `{HOME_ROUTE, DISPLAY_
    ROUTE}` before ever using it as a redirect target; this function
    has no opinion on validity, it only renders whatever the caller
    passes (Home passes HOME_ROUTE, Display passes DISPLAY_ROUTE —
    both members of that same whitelist by construction).

    `next_wake_iso` is accepted (and every existing call site in
    home_page.py/config_page.py keeps passing it, unchanged, since both
    modules are owned by other plans in this same wave) but is no
    longer this function's own source of truth for lateness — 22-04-
    PLAN.md Task 1 (D-03/CFG-26) replaces the local, quiet-hours-blind
    `age >= 0` warn trigger with `companion.wake.next_wake_status()` /
    `companion.frame_state.resolve_state()`, called fresh here against
    the SAME `ctx["last_checkin_ts"]`/`ctx["device_config"]` inputs the
    caller already used to compute the `next_wake_iso` it passes in —
    calling that same deterministic function twice is not the
    re-derivation CFG-26 forbids (the two calls can never disagree,
    since they share identical inputs); duplicating the DECISION logic
    itself (a second grace-window/quiet-hours computation) would be.
    The parameter stays in the signature only for call-site
    compatibility with those two modules.

    Renders no update cell at all — not even an empty
    `.frame-strip__cell--update` wrapper — when no next-wake data is
    available (`frame_state.resolve_state()` degrades to
    `STATE_UNKNOWN`): this function never fabricates a placeholder
    "Next update ≈ —" line or claims a state it does not have.

    Three states, one dot vocabulary (22-UI-SPEC.md §3.3): due draws
    `.dot--ok`, held draws `.dot--off` (the app's existing neutral,
    "not a problem" dot — never a new colour), late draws `.dot--warn`
    and the ONLY state whose headline carries the
    `status-card__headline--warn` class — which, per the 20-04 contrast
    gate, resolves to `--color-text` visually; the warn signal is
    carried by the wording and the dot, never by text colour (rule 2).

    The switch cells reuse `.quick-action`/`.quick-action--on`/`--off`
    for their control-state left edge (unchanged), now folded into
    `_frame_strip_cell_html()`'s shared three-row wrapper — the label
    row, the state-plus-control row (state text and the `<form>`
    together), and the caption row (the one computed delay sentence,
    D-04). No second on/off dot is added inside a switch cell —
    `.quick-action--on`/`--off`'s own 4px left-edge colour already is
    that signal (the same anti-duplication principle status_row()'s
    own docstring states for verdict/detail).

    Both switch forms carry the literal attribute `data-quick-switch`
    (D-04 handshake, 22-05-PLAN.md Task 3, same wave): the stable hook
    that plan's leave-guard suppression keys on, since
    `quick-action__form` — the only class either form carried before
    this task — is a presentation class a later CSS change could
    legitimately rename. Do not delete this attribute as apparently
    unused from this module's own perspective; companion/static/
    dirty-state.js is its consumer.

    The whole strip is a hand-built `<div class="frame-strip stat-tile
    stat-tile--accent">` — it borrows `stat_tile()`'s CSS classes for
    the card surface (accent-bordered, "the control area"), never its
    Python builder: the strip's own `<h2>` needs the Section-heading
    role (22px serif), not `stat_tile()`'s smaller Label-voice caption
    role.

    Every interpolated value crosses `escape_html()`; every
    user-visible string crosses `i18n.t()` at its interpolation site.
    Pure markup — no `<script>`, no inline handler.
    """
    device_cfg = ctx.get("device_config") or {}
    now_value = ctx.get("now")

    # D-03/CFG-26 (22-02-PLAN.md Task 1, 22-04-PLAN.md Task 1): the one
    # state resolution. `wake.next_wake_status()` is the SAME function,
    # against the SAME (last_checkin_ts, device_config) pair, every
    # caller of this function already used to compute the `next_wake_iso`
    # argument above — see this function's own docstring for why calling
    # it again here is not a second, disagreeing computation.
    resolved_next_wake_iso, effective_interval_s, hold_reason = wake.next_wake_status(
        ctx.get("last_checkin_ts"), device_cfg)
    resolved_state = frame_state.resolve_state(
        resolved_next_wake_iso, effective_interval_s, hold_reason, now_value)
    headline_template_value = frame_state.headline_template(resolved_state)
    delay_template_value = frame_state.delay_sentence_template(
        resolved_next_wake_iso, effective_interval_s, hold_reason, now_value)

    next_wake_clock = None
    if resolved_next_wake_iso:
        next_wake_parsed = parse_iso(resolved_next_wake_iso)
        if next_wake_parsed is not None:
            next_wake_clock = local_clock_text(next_wake_parsed, now_parsed=parse_iso(now_value))

    # D-04: the one computed delay sentence, shared verbatim by both
    # switch cells' captions — replacing the four retired wordings a
    # static per-control literal used to carry regardless of state.
    if delay_template_value == frame_state.DELAY_HELD and next_wake_clock is not None:
        delay_sentence_text = i18n.t(_FRAME_DELAY_HELD_TEXT) % next_wake_clock
    elif delay_template_value == frame_state.DELAY_DUE and next_wake_clock is not None:
        delay_sentence_text = i18n.t(_FRAME_DELAY_DUE_TEXT) % next_wake_clock
    else:
        delay_sentence_text = i18n.t(_FRAME_DELAY_UNKNOWN_TEXT)
    delay_caption_html = '<p class="text-label section-caption">%s</p>' % escape_html(
        delay_sentence_text)

    display_enabled = device_cfg.get("display_enabled", True)
    is_display_on = display_enabled is not False
    next_display_state = QUICK_STATE_OFF if is_display_on else QUICK_STATE_ON
    display_state_text = i18n.t(QUICK_ACTION_ON_TEXT if is_display_on else QUICK_ACTION_OFF_TEXT)
    display_label_html = '<span class="text-label quick-action__label">%s%s</span>' % (
        icon_html("icon-power", size=16, extra_class="quick-action__icon"),
        escape_html(i18n.t(QUICK_ACTION_SCREEN_LABEL)))
    display_state_row_html = (
        '<span class="text-body quick-action__state">%s</span>'
        '<form method="post" action="/quick/display" class="quick-action__form" data-quick-switch>'
        '<input type="hidden" name="%s" value="%s">'
        '<input type="hidden" name="return_to" value="%s">'
        '<button type="submit">%s</button>'
        "</form>"
    ) % (
        escape_html(display_state_text),
        QUICK_STATE_FIELD, escape_html(next_display_state),
        escape_html(return_to),
        escape_html(i18n.t(
            QUICK_ACTION_SWITCH_OFF_BUTTON if is_display_on else QUICK_ACTION_SWITCH_ON_BUTTON)),
    )
    display_cell_html = _frame_strip_cell_html(
        "quick-action quick-action--%s" % ("on" if is_display_on else "off"),
        display_label_html, display_state_row_html, delay_caption_html)

    quiet_enabled = device_cfg.get("quiet_hours_enabled", False)
    is_quiet_on = quiet_enabled is True
    next_quiet_state = QUICK_STATE_OFF if is_quiet_on else QUICK_STATE_ON
    quiet_start = device_cfg.get("quiet_hours_start") or "23:00"
    quiet_end = device_cfg.get("quiet_hours_end") or "07:00"
    quiet_state_text = (
        i18n.t(QUICK_ACTION_QUIET_ON_TEMPLATE) % (quiet_start, quiet_end)
        if is_quiet_on else i18n.t(QUICK_ACTION_QUIET_OFF_TEXT))
    quiet_label_html = '<span class="text-label quick-action__label">%s%s</span>' % (
        icon_html("icon-moon", size=16, extra_class="quick-action__icon"),
        escape_html(i18n.t(QUICK_ACTION_QUIET_LABEL)))
    quiet_state_row_html = (
        '<span class="text-body quick-action__state">%s</span>'
        '<form method="post" action="/quick/quiet-hours" class="quick-action__form" data-quick-switch>'
        '<input type="hidden" name="%s" value="%s">'
        '<input type="hidden" name="return_to" value="%s">'
        '<button type="submit">%s</button>'
        "</form>"
    ) % (
        escape_html(quiet_state_text),
        QUICK_STATE_FIELD, escape_html(next_quiet_state),
        escape_html(return_to),
        escape_html(i18n.t(
            QUICK_ACTION_QUIET_TURN_OFF_BUTTON if is_quiet_on else QUICK_ACTION_QUIET_TURN_ON_BUTTON)),
    )
    quiet_cell_html = _frame_strip_cell_html(
        "quick-action quick-action--%s" % ("on" if is_quiet_on else "off"),
        quiet_label_html, quiet_state_row_html, delay_caption_html)

    update_cell_html = ""
    if next_wake_clock is not None:
        dot_class = _FRAME_DOT_CLASS_BY_STATE.get(resolved_state, "dot--ok")
        headline_class = "status-card__headline"
        if headline_template_value == frame_state.HEADLINE_LATE:
            headline_i18n_source = _FRAME_HEADLINE_LATE_TEXT
            headline_class = headline_class + " status-card__headline--warn"
        elif headline_template_value == frame_state.HEADLINE_HELD:
            headline_i18n_source = _FRAME_HEADLINE_HELD_TEXT
        else:
            headline_i18n_source = _FRAME_HEADLINE_DUE_TEXT
        # C5 (22-04-PLAN.md Task 2): the clock value is its own
        # `.time-value` element, not baked into the sentence's escaped
        # text — every one of the three headline templates carries
        # exactly one "%s", so splitting on it and escaping each of the
        # three pieces (the leading text, the clock span, the trailing
        # text) separately still crosses escape_html() at every
        # interpolation site, matching this function's own discipline.
        headline_before, headline_after = i18n.t(headline_i18n_source).split("%s", 1)
        headline_text = "%s%s%s" % (
            escape_html(headline_before),
            '<span class="time-value time-value--primary">%s</span>' % escape_html(next_wake_clock),
            escape_html(headline_after),
        )
        update_state_row_html = (
            '<p class="%s"><span class="dot %s"></span>%s</p>'
        ) % (headline_class, dot_class, headline_text)
        # 23-06-PLAN.md Task 2 (D1/CFG-35): the countdown, in the cell's
        # caption row beside — never inside — the headline.
        #
        # IT IS FORMATTING, AND IT DECIDES NOTHING. The instant it counts
        # toward is `resolved_next_wake_iso`, computed above by
        # companion/wake.py's next_wake_status(); the state word beside
        # it is frame_state.resolve_state()'s, through
        # headline_template(). This element re-derives neither. It
        # renders a DURATION, which is the question the user actually
        # asks ("will I make the next RER"), and
        # companion/static/relative-time.js advances that duration once a
        # second without ever asking whether the frame is due, held or
        # late — D-03/CFG-26's rule, which exists because two places
        # computing lateness is exactly how X2's nightly false alarm
        # happened.
        #
        # `countdown=True` is what keeps it a countdown after its instant
        # passes: it reads the translated waiting wording rather than
        # silently turning into an age, so a late frame's cell says
        # "Expected since 14:32 / waiting…" and never "2m ago", which
        # would be a second, quieter lateness claim beside the headline's.
        countdown_html = (
            '<p class="text-label section-caption">%s</p>'
            % relative_time_html(resolved_next_wake_iso, now_value, countdown=True))
        update_cell_html = _frame_strip_cell_html(
            "frame-strip__cell--update", "", update_state_row_html, countdown_html)

    return (
        '<div class="frame-strip stat-tile stat-tile--accent" aria-labelledby="frame-strip-heading">'
        '<h2 id="frame-strip-heading" class="text-heading">%s</h2>'
        '<div class="frame-strip__cells">%s%s%s</div>'
        "</div>"
    ) % (
        escape_html(i18n.t(FRAME_STRIP_HEADING)),
        display_cell_html, quiet_cell_html, update_cell_html,
    )


def card_status_class(base_class, status):
    """`base_class + "--ok"/"--warn"/"--error"` for one of the three
    whitelisted statuses; the empty string for `None` or anything
    unrecognised.

    The one status->card-modifier mapping (quick task 260902-gjj, ISSUE
    2), living beside `_STATUS_DOT_CLASSES`/`_STAT_TILE_BORDER_CLASSES`
    so the vocabulary has exactly one home. `status` is looked up in a
    fixed three-key whitelist, the same discipline `status_dot()` and
    `stat_tile()` already document — an unrecognised value can never
    become an arbitrary, attacker-influenceable class name. `base_class`
    is expected to be a module constant or a call-site literal, never
    itself derived from data.

    The fallback deliberately differs from `stat_tile()`'s: `stat_tile()`
    falls back to `stat-tile--accent` because `.stat-tile`'s base rule
    already declares a 3px top border that has to be *some* colour. A
    page-level card's base rule (`.battery-trend-section`, `.page-section`)
    declares a plain 1px hairline, so "no status" correctly means "no
    modifier at all, keep the neutral edge" — the absence of a coloured
    edge is itself the signal that the card carries no verdict. Getting
    this backwards (defaulting to an accent modifier) would put a 3px
    accent border on the Resolution-statistics card, which carries no
    status field of any kind, and would require broadening style.css's
    exhaustive accent-reservation list a second time in two days, for no
    reported problem.
    """
    suffix = _CARD_STATUS_SUFFIXES.get(status)
    return base_class + suffix if suffix else ""


def status_row(label, verdict, detail, state):
    """<div class="status-row status-row--ok|warn|error"> — D-21's one
    shared row primitive (dot + optional label + verdict + detail),
    consumed by Home's status card (20-06) and the Calendar status row
    (20-07) alike (20-UI-SPEC.md Section Anatomy A).

    `label` is optional: a falsy value omits the `<span>` element
    entirely, not merely its text — Calendar's own status row passes
    "" because its surrounding `<h2>Calendar</h2>` already names the
    subject, and a repeated "CALENDAR" label would be redundant
    chrome. `verdict` and `detail` must carry two DIFFERENT pieces of
    information — a state word versus a freshness/detail clause — by
    contract: this primitive exists specifically to fix the Home
    Frame-tile defect where `DEVICE_STATE_TEXT`/`FRAME_STATE_TEXT`'s
    verdict sentence used to be rendered twice, once as the tile's own
    verdict paragraph and once again inside `health_state["device_
    html"]`'s own embedded verdict paragraph.

    `state` maps through the SAME `_STATUS_DOT_CLASSES`/
    `_DEFAULT_STATUS_DOT_CLASS` fallback `status_dot()`/`stat_tile()`
    already use for the dot, and through `card_status_class()`'s own
    three-key whitelist for the outer modifier class — never a second,
    bare `%s` interpolation of an unvalidated `state` (T-20-18): an
    unrecognised state degrades to the default (warn) dot and to NO
    outer modifier class at all, rather than emitting an arbitrary,
    attacker-influenceable class name. `verdict` and `detail` are both
    escaped here (T-20-03) — `label` is escaped too, inside the
    optional span.

    The caller is responsible for translating `label`/`verdict`/
    `detail` through `i18n.t()` BEFORE calling this — status_row()
    itself calls no `t()` and treats every argument as already-
    resolved display text.
    """
    dot_class = _STATUS_DOT_CLASSES.get(state, _DEFAULT_STATUS_DOT_CLASS)
    modifier = card_status_class("status-row", state)
    css_class = "status-row" + ((" " + modifier) if modifier else "")
    label_html = (
        '<span class="status-row__label text-label">%s</span>' % escape_html(label)
        if label else "")
    return (
        '<div class="%s">'
        '<span class="dot %s"></span>%s'
        '<span class="status-row__verdict">%s</span>'
        '<span class="status-row__detail">%s</span>'
        "</div>"
    ) % (css_class, dot_class, label_html, escape_html(verdict), escape_html(detail))


def section_intro_html(section_id, heading, description):
    """A `<div class="section-intro">` wrapping one id-anchored `<h2>`
    plus a muted one-sentence description on the same baseline.

    Promoted here, byte-identical (markup and CSS class unchanged),
    from `companion/pages/health_page.py`'s own former private copy,
    `_section_intro_html()` (20-UI-SPEC.md Section Anatomy C):
    `companion/pages/__init__.py` forbids one page module importing
    another, so a helper both `health_page.py` and `config_page.py`
    (20-07's Display supersections) need must live in this shared
    layer instead — the same reasoning D-21's `status_row()` above is
    added here for, in the same phase.

    The `<h2 id="..." class="text-heading">...</h2>` this emits keeps
    the same attribute order (`id` then `class`) and the same
    `escape_html()` call on the heading text health_page.py's own
    pinned structural checks already match literally — this builder
    must never drift from that shape. The description keeps the
    `text-label section-caption` pairing already established for this
    "muted one-sentence-under-a-heading" role.

    WR-03 fix (20-REVIEW.md): `section_id` is escaped too, like every
    other string this file interpolates into an HTML attribute or text
    node — this was the one exception to that "escape everything,
    unconditionally" invariant. Every current call site passes a fixed
    module-level string constant, so this was not exploitable today,
    but this helper is shared across page modules going forward and
    must not be the one place a caller is trusted.
    """
    return (
        '<div class="section-intro">'
        '<h2 id="%s" class="text-heading">%s</h2>'
        '<p class="text-label section-caption">%s</p>'
        "</div>"
    ) % (escape_html(section_id), escape_html(heading), escape_html(description))


def empty_state(heading, body, compact=False):
    """The escaped two-part empty-state block (06-UI-SPEC.md's Copywriting
    Contract) used for the flight log, the gallery, and the unresolved-
    prefix list.

    `compact` (22-12-PLAN.md Task 1 — D-08's C1, 22-UI-SPEC.md §1's
    Typography row and §2's X8) is a keyword-with-default whose falsy
    value returns markup that is BYTE-IDENTICAL to what this function
    returned before the parameter existed, matching `stat_tile()`'s own
    `caption_title` and `status_dot()`'s own `visually_hide_label`
    contract. Every full-card caller (companion/pages/home_page.py's two,
    companion/pages/history_page.py's one, `data_table()`'s own no-rows
    fallback below, and health_page.py's battery-card and registry-card
    call sites) passes two positional arguments and is unaffected.

    Why the variant exists: an empty state rendered INSIDE a
    `.stat-tile` put a 22px serif `.text-heading` inside a card whose own
    caption is 12px — the inverted hierarchy defect 06.6.4.1.1's finding
    1.1 already closed once for nested cards, reopened here by reuse
    (22-AUDIT.md X8). The compact form drops the heading to the Emphasis
    role (16px sans semibold: `.text-body`'s size plus the semibold
    weight `.empty-state--compact .empty-state__heading` supplies) and
    the body to the label size at the file's own 70% muted strength
    (`.text-label` composed with `.section-caption`, the established
    "muted strength onto a sizing class" idiom — never a fourth muted
    value). No new type tier and no 14px heading role is invented; the
    established bottom rung is reused, which is what 22-UI-SPEC.md §1
    asks for.

    Those are the SAME two treatments a filled Health tile's verdict and
    detail rows wear, so inside a tile the empty state occupies exactly
    the verdict and detail slots of X8's one-tile anatomy and an empty
    tile reads with a filled tile's rhythm. It reaches them through the
    empty state's OWN class names rather than by borrowing
    `.widget-verdict`/`.widget-detail`: an empty state's heading is not a
    verdict, and companion/test_status_pages.py pins that the
    Resolution-rate tile carries no `.widget-verdict` anywhere (D-03/
    A-21 — that tile makes no judgement), which borrowing the class
    would have quietly broken on its own empty branch.
    """
    if compact:
        return (
            '<div class="empty-state empty-state--compact">'
            '<p class="empty-state__heading text-body">%s</p>'
            '<p class="empty-state__body text-label section-caption">%s</p>'
            "</div>"
        ) % (escape_html(heading), escape_html(body))
    return (
        '<div class="empty-state">'
        '<p class="empty-state__heading text-heading">%s</p>'
        '<p class="empty-state__body text-body">%s</p>'
        "</div>"
    ) % (escape_html(heading), escape_html(body))


def page_header(title, purpose=None, freshness_html=None, action_html=None):
    """The shared page-header component (06.6.2 D-16) every authenticated
    page's render() opens with, in place of an independent bare <h1>.

    THIS SIGNATURE IS A LITERAL CONTRACT: Phase 06.6.3's five per-page
    redesign plans call page_header(title, purpose=None,
    freshness_html=None, action_html=None) by this exact name and
    parameter order — do not rename or reorder these parameters after
    this plan ships. Every call site this plan adds passes only `title`
    (positional); those calls remain byte-compatible with later call
    sites that also pass `purpose`/`freshness_html`/`action_html`.

    `title` is escaped here and wrapped in an <h1 class="page-title">
    (06.6.2 D-15's distinct ~30px serif page-title role, separate from
    the existing 20px .text-heading section-heading role).

    `purpose` is escaped here too, when truthy, and rendered as a
    one-sentence <p class="page-header__purpose text-body">.

    `freshness_html` and `action_html`, when truthy, are each the
    caller's own already-safe markup and are interpolated verbatim —
    no call to escape_html(), no other transformation. This is the same
    "escape the caption, pass already-built content through verbatim"
    contract stat_tile()'s `content_html` parameter uses; re-encoding
    either of these two here would double-encode already-escaped tags
    and print them as visible text instead of rendering. Callers are
    responsible for escaping/composing any user-influenced data before
    passing it through either parameter.

    Quick task 260901-tsa: `freshness_block` and `action_block` are
    concatenated BEFORE `purpose_html` below — title, then the Refresh
    link/action row, then the purpose sentence last. That is the
    validated Health sketch's own header markup: the title and the
    Refresh anchor sit inside one `.page-header` element, with the
    purpose sentence following after it, not wedged between the title
    and its action link. The LITERAL CONTRACT paragraph above covers the
    signature — parameter names and their order — which this edit does
    not touch; the order the three optional blocks are concatenated into
    the returned string is a separate thing and was never part of that
    contract. Blast radius: Health is the only call site today passing
    both a purpose and a freshness block. For a caller passing exactly
    one of the three optional blocks (every other page, today), the
    concatenation produces the identical string either way — `"%s%s%s" %
    (p, "", "")` and `"%s%s%s" % ("", "", p)` are the same string — so
    Settings, Airlines and History are byte-identical before and after
    this reorder; this is a Health-only visual change. With the purpose
    paragraph now the last in-flow child of a block-level `.page-header`
    that has no padding and no border, its own bottom margin collapses
    with the parent's `margin-bottom`, so the gap below the header block
    is unchanged rather than doubled.

    06.6.4.1.1-04 (D-17): the returned string now ends with
    FLASH_SLOT_MARKER, appended after the closing `</div>`. This is NOT
    a signature change — the LITERAL CONTRACT above governs this
    function's parameter names and order, not the content of what it
    returns — but it is documented here explicitly so the next reader
    does not mistake it for one. `page_shell()` is the marker's only
    consumer: it splices the flash banner in at that exact point and
    strips the marker unconditionally before the response ships.
    """
    purpose_html = (
        '<p class="page-header__purpose text-body">%s</p>' % escape_html(purpose)
        if purpose else "")
    freshness_block = freshness_html if freshness_html else ""
    action_block = action_html if action_html else ""
    return (
        '<div class="page-header">'
        '<h1 class="page-title">%s</h1>'
        "%s%s%s"
        "</div>"
        "%s"
    ) % (
        escape_html(title), freshness_block, action_block, purpose_html,
        FLASH_SLOT_MARKER,
    )


def data_table(headers, rows, mono_columns=(), raw_columns=(), desc_columns=(), prose=False,
               modifier=None):
    """A header row plus alternating body rows, every value escaped.

    `mono_columns` names the zero-based column indices that get the
    monospace class (callsigns, hex codes, prefixes, timestamps, per
    06-UI-SPEC.md's Typography section). Returns empty_state()'s output
    instead of an empty table when `rows` is empty.

    `raw_columns` (06.6.3, D-09) names the zero-based column indices
    whose cell value is ALREADY-SAFE, pre-built HTML — the same
    "already-built content passed through verbatim" contract
    stat_tile()'s `content_html` parameter documents — and is
    interpolated without a call to escape_html(). Every other column
    (the default for all of them) is escaped exactly as before this
    parameter existed; every pre-existing call site passing no
    raw_columns argument is byte-identical. Only ever place the output
    of a builder that already escapes internally (concise_timestamp_html(),
    status_dot()) in a raw_columns cell — never a bare string; doing so
    would reopen the exact XSS-shaped defect this module's single-
    escaping-choke-point discipline otherwise closes (06.6.3-RESEARCH.md
    Pitfall 3). `mono_columns` and `raw_columns` are orthogonal (one
    controls a CSS class, the other controls escaping) and may safely
    name the same index, though concise_timestamp_html()'s own
    `<span class="mono">` makes a redundant mono_columns entry
    pointless for that specific case.

    `desc_columns` (quick task 260902-bl2) is `mono_columns`' direct
    sibling: the zero-based column indices that get the description
    role's class (`desc`) — a column holding descriptive prose rather
    than data, which the validated Health sketch renders in the muted
    secondary strength so the eye lands on the values beside it. Added
    because the Resolution-statistics table's Description column
    measured full-strength `--color-text` (`rgb(23, 25, 31)`) with an
    empty `classList`: before this keyword, `data_table()` had no
    column-role class hook for anything but the monospace role, so a
    column of prose had no class for a stylesheet rule to target at
    all. Changes no cell content and no escaping — the same boundary
    `mono_columns` already keeps. `mono_columns`, `raw_columns` and
    `desc_columns` are mutually orthogonal (one controls a class, one
    controls escaping, one controls a class) and may safely name the
    same index.

    `prose` (quick task 260901-uzi) adds the modifier class
    `data-table--prose` to the emitted `<table>` when true; the default,
    false, is byte-identical to this function's pre-existing output.
    `.data-table` carries `min-width: max-content` in style.css so that
    tables of short values (callsigns, hex codes, prefixes, timestamps)
    are never cropped — but a cell's max-content width is its text with
    no wrapping at all, which is correct for those short values and wrong
    for a column holding full sentences: the table then cannot fit any
    container narrower than the whole unwrapped sentence, and
    `.data-table-wrap`'s horizontal scroll becomes a permanent state
    rather than a safety net. Measured on the Resolution-statistics
    table: 1172px of content inside an 831px container. This keyword
    changes no cell's content or escaping — it only adds a class the
    stylesheet uses to release that one table from the shared no-crop
    floor.

    `modifier` (quick task 260913-cz6) appends one additional
    `data-table--<modifier>` class to the emitted `<table>`, the same
    additive per-table scoping hook `_registry_table_html()` already
    hand-writes for `data-table--registry` — that table builds its own
    markup (it needs a per-row attribute this function has no hook for),
    so until now a table rendered THROUGH this function had no way to
    carry a scoping class at all, and `prose` was the only, hard-coded
    exception. `None`, the default, is byte-identical to this function's
    pre-existing output, as is `prose=True`; the two are independent and
    may be combined. Pass the bare stem ("readings"), never the full
    class name — the `data-table--` prefix is added here so every
    modifier in the app is spelled the same way in the stylesheet.
    """
    if not rows:
        return empty_state("No data yet.", "Nothing to show here yet.")

    header_cells = "".join(
        "<th>%s</th>" % escape_html(header) for header in headers)

    body_rows = []
    for row_index, row in enumerate(rows):
        row_class = "row-alt" if row_index % 2 else "row"
        cells = []
        for column_index, cell in enumerate(row):
            # mono is joined first so a mono-only cell's attribute string
            # stays byte-identical to this loop's pre-desc_columns output
            # — test_view_pages.py::_mono_columns_present() asserts that
            # merged-cell mono output and must stay green unedited.
            cell_roles = []
            if column_index in mono_columns:
                cell_roles.append("mono")
            if column_index in desc_columns:
                cell_roles.append("desc")
            cell_class = ' class="%s"' % " ".join(cell_roles) if cell_roles else ""
            cell_html = cell if column_index in raw_columns else escape_html(cell)
            cells.append("<td%s>%s</td>" % (cell_class, cell_html))
        body_rows.append('<tr class="%s">%s</tr>' % (row_class, "".join(cells)))

    table_class = "data-table data-table--prose" if prose else "data-table"
    if modifier:
        table_class += " data-table--%s" % modifier
    return (
        '<div class="data-table-wrap">'
        '<table class="%s">'
        "<thead><tr>%s</tr></thead>"
        "<tbody>%s</tbody>"
        "</table>"
        "</div>"
    ) % (table_class, header_cells, "".join(body_rows))
