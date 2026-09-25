"""companion/layout.py: the escaped page shell and component library for the
SkyPane companion service.

stdlib `html` and `datetime` only — no imports from server/, and nothing
from companion.auth beyond the UI-theme cookie name.

`escape_html()` is defined once, here; every companion/pages/*.py module
must import and use it rather than the stdlib `html` module directly, or
build markup without going through this helper. One helper makes the
escaping obligation auditable with a single grep across the package.
"""
import html
from datetime import datetime
from zoneinfo import ZoneInfo

from companion.auth import UI_THEME_COOKIE_NAME
# companion.i18n/companion.prefs are shared, page-independent modules like
# companion.auth: importing them carries no cycle, since neither imports this
# module or companion.app (companion.app imports layout.py, never the
# reverse).
import companion.i18n as i18n
import companion.prefs as prefs
# companion.wake/companion.frame_state are shared, page-independent
# modules; importing them carries no cycle. companion.wake is a thin shim
# over server/wake.py, never a direct server/ import from here.
# frame_strip_html() below is the one consumer of both, so lateness is
# resolved by frame_state.resolve_state(), never re-derived here.
import companion.wake as wake
import companion.frame_state as frame_state

SITE_TITLE = "SkyPane"

# Visible timestamps render in LOCAL_TZ and carry the day once the value is
# no longer "today" ("3 Sep 21:50"), rather than a bare UTC clock. The
# `title` attribute carries a local full timestamp (see
# FULL_TIMESTAMP_SENTINEL_NOW below); the raw ISO no longer appears in any
# `title` this module renders.
LOCAL_TZ = ZoneInfo("Europe/Paris")
_MONTH_ABBR = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
# The French month-abbreviation table local_clock_text() selects instead
# of _MONTH_ABBR above under a French request — same twelve-entry shape,
# parallel index.
_MONTH_ABBR_FR = ("janv.", "févr.", "mars", "avr.", "mai", "juin",
                   "juil.", "août", "sept.", "oct.", "nov.", "déc.")

# Ordered (route, label) pairs, grouped into an unlabelled "everyday" group
# and a labelled "Advanced" group. Login is deliberately absent: it is
# shown instead of any page when unauthenticated, never as a nav tab.
# NAV_TABS below is derived from this tuple so every existing (route,
# label) consumer keeps working unchanged.
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

# Ordered (route, label) pairs, flattened from NAV_GROUPS in display order.
# Login is deliberately absent, as above. The old "/settings" and
# "/history" routes are not tabs any more — companion/app.py keeps both as
# fixed 303 redirects so a stale bookmark still lands somewhere useful.
NAV_TABS = tuple(
    (route, label) for _group_label, entries in NAV_GROUPS for route, label in entries)

# The slug a route is identified by inside the nav renderers and by
# page_shell()'s `active` argument. The home route "/" has no path segment
# to strip, so it gets an explicit slug rather than "".
HOME_NAV_SLUG = "home"


def nav_slug(route):
    """The `active` slug for a NAV_TABS route: "home" for HOME_ROUTE,
    otherwise the route with its leading slash removed.
    """
    if route == HOME_ROUTE:
        return HOME_NAV_SLUG
    return route.lstrip("/")


# The exact literals companion/static/nav-dropdown.js looks up via
# getElementById()/classList. Duplicated here since a Python module
# cannot import a JS file; a DOM-contract guard reads the JS source, the
# stylesheet and the rendered page, and requires all three to agree.
NAV_TOGGLE_ID = "site-nav-toggle"
MOBILE_NAV_ID = "mobile-nav"
MOBILE_NAV_OPEN_CLASS = "mobile-nav--open"

# The fixed accessible name for the hamburger toggle button; state is
# communicated entirely through aria-expanded, so this must not vary by
# state. Renamed from "Open menu": the panel no longer holds a menu of
# pages — the bottom tab bar owns destinations now, and what remains is
# the state reminder plus language, theme and Sign out.
NAV_TOGGLE_LABEL = "Account and preferences"

# Must equal companion/app.py's NAV_SCRIPT_ROUTE exactly. Duplicated
# rather than imported: companion/pages/__init__.py's boundary forbids
# the reverse direction, since app.py imports this module. A harness
# asserts the equality.
NAV_DROPDOWN_SCRIPT_SRC = "/static/nav-dropdown.js"

# Four more pre-auth static JS route constants, the same
# duplicated-not-imported contract as NAV_DROPDOWN_SCRIPT_SRC above — each
# must equal companion/app.py's matching *_SCRIPT_ROUTE constant exactly,
# asserted by a harness.
DIRTY_STATE_SCRIPT_SRC = "/static/dirty-state.js"
LIST_FILTER_SCRIPT_SRC = "/static/list-filter.js"
COPY_BUTTON_SCRIPT_SRC = "/static/copy-button.js"
FRESHNESS_SCRIPT_SRC = "/static/freshness.js"

# Must equal companion/app.py's PANEL_LOOKUP_SCRIPT_ROUTE exactly, the
# same duplicated-not-imported contract as above.
PANEL_LOOKUP_SCRIPT_SRC = "/static/panel-lookup.js"

# Must equal companion/app.py's FLASH_CLEANUP_SCRIPT_ROUTE exactly, same
# contract as above.
FLASH_CLEANUP_SCRIPT_SRC = "/static/flash-cleanup.js"

# Must equal companion/app.py's POLL_COOLDOWN_SCRIPT_ROUTE exactly, same
# contract as above.
POLL_COOLDOWN_SCRIPT_SRC = "/static/poll-cooldown.js"

# Must equal companion/app.py's CONFIRM_SUBMIT_SCRIPT_ROUTE exactly, same
# contract as above.
CONFIRM_SUBMIT_SCRIPT_SRC = "/static/confirm-submit.js"

# Must equal companion/app.py's THEME_PREVIEW_SCRIPT_ROUTE exactly, same
# contract as above.
THEME_PREVIEW_SCRIPT_SRC = "/static/theme-preview.js"

# Must equal companion/app.py's FLIGHT_ROWS_SCRIPT_ROUTE exactly, same
# contract as above.
FLIGHT_ROWS_SCRIPT_SRC = "/static/flight-rows.js"

# Must equal companion/app.py's LOGIN_CARD_SCRIPT_ROUTE exactly, same
# contract as above. Emitted by login_shell() alone — the only static
# script loaded on the pre-auth page; page_shell() never emits it.
LOGIN_CARD_SCRIPT_SRC = "/static/login-card.js"

# Must equal companion/app.py's SUBMIT_GUARD_SCRIPT_ROUTE exactly, same
# contract as above: one shared disable-on-submit guard for every form.
SUBMIT_GUARD_SCRIPT_SRC = "/static/submit-guard.js"

# Must equal companion/app.py's RELATIVE_TIME_SCRIPT_ROUTE exactly, same
# contract as above. Ticks every <time data-relative> element
# relative_time_html() renders; registered on the shell since no page
# module knows whether it has one.
RELATIVE_TIME_SCRIPT_SRC = "/static/relative-time.js"
# Must equal companion/app.py's QUICK_SWITCH_SCRIPT_ROUTE exactly, same
# contract as above. Registered on the shell because its listener is
# delegated at document level over every [data-quick-switch] form, which
# already live on three different pages.
QUICK_SWITCH_SCRIPT_SRC = "/static/quick-switch.js"
# Must equal companion/app.py's VALUE_CONTROLS_SCRIPT_ROUTE exactly, same
# contract as above; its guard returns before touching a page with no
# [data-value-control] wrapper.

# The only script the value-controls feature needs: five controls share
# one clamp/round/keyboard model rather than duplicating it per control.
VALUE_CONTROLS_SCRIPT_SRC = "/static/value-controls.js"

# The registration seam value-controls.js reads, defined here so a page
# module never types the attribute name (a harness asserts the served
# script body names each one). A control opts in entirely by attribute.

# The wrapper is a layer, never the control: the value is always held by
# the native <input>/<select> named by VALUE_CONTROL_FIELD_ATTR.
VALUE_CONTROL_ATTR = "data-value-control"
VALUE_CONTROL_FIELD_ATTR = "data-value-field"
# The id of the form that input belongs to. Load-bearing: this app's
# settings groups attach ACROSS the DOM through a form= attribute (a
# <form> cannot nest inside another), so an ancestor walk from the
# wrapper would miss the field.
VALUE_CONTROL_FORM_ATTR = "data-value-form"
VALUE_CONTROL_MIN_ATTR = "data-value-min"
VALUE_CONTROL_MAX_ATTR = "data-value-max"
VALUE_CONTROL_STEP_ATTR = "data-value-step"
VALUE_CONTROL_HANDLE_ATTR = "data-value-handle"
VALUE_CONTROL_TRACK_ATTR = "data-value-track"
# The server-rendered, already-translated aria-valuetext template, with
# VALUE_CONTROL_TEXT_TOKEN standing in for the number. No copy lives in
# the script: absent this attribute it writes no aria-valuetext at all.
VALUE_CONTROL_TEXT_ATTR = "data-value-text"
# "#" (not "{}"): these templates reach the browser as attribute values,
# and companion/test_i18n.py's Check 3 scans every French render for a
# stray "%s"/"%d"/"{}" — the real failure mode of a mistyped catalogue
# key. RELATIVE_QUANTITY_MARK below applies the same "#" choice for the
# same reason.
VALUE_CONTROL_TEXT_TOKEN = "#"
# "angular" for a dial, absent for a left-to-right track.
VALUE_CONTROL_GEOMETRY_ATTR = "data-value-geometry"

# The codec between the NUMBER value-controls.js steers and the TEXT the
# native input holds. Absent, the number is written straight in.
# VALUE_CONTROL_FORMAT_CLOCK makes the script read/write "HH:MM" instead:
# an <input type="time"> silently discards anything else, emptying the
# field with no error.
VALUE_CONTROL_FORMAT_ATTR = "data-value-format"
VALUE_CONTROL_FORMAT_CLOCK = "clock"

# The mirror is a native control inside the wrapper, carrying the same
# value as the field and posting nothing — an `<input type="range">`
# with no `name`.

# It already has the keyboard model this script implements, native
# aria-valuenow and touch dragging; role="slider" must not be added,
# since the element already has those semantics.

# A wrapper carrying a mirror gets no preventDefault or steering from
# this file's own handlers, since a native range already drags itself;
# the script's job with a mirror is only to sync.
VALUE_CONTROL_INPUT_ATTR = "data-value-input"

# A readout is an element whose whole text is a sentence about the
# value, rendered by the server and rewritten by the script. It carries
# the field's own name so it can live anywhere — not gated, since it
# must be correct with scripts blocked.

# The sentence is server-rendered and already translated: no copy lives
# in the script, so a French reader is never dropped into English.
VALUE_CONTROL_READOUT_ATTR = "data-value-readout"
VALUE_CONTROL_READOUT_TEXT_ATTR = "data-value-readout-text"
# What the value is divided by before substitution, rounded up (60 for
# a readout speaking in whole minutes about a field holding seconds).
# The ceiling rather than the floor, since every consumer states a
# bound and "at most 1 min" would be false for a 90-second cadence.
VALUE_CONTROL_READOUT_SCALE_ATTR = "data-value-readout-scale"
# The value at which the readout says nothing at all: a readout
# comparing the proposed value against the saved one has nothing to say
# while they are equal (every page load). Absent, the readout always
# speaks.
VALUE_CONTROL_READOUT_BASE_ATTR = "data-value-readout-base"

# A readout-scoped clock-format signal: VALUE_CONTROL_FORMAT_ATTR lives
# on the wrapper, but a readout is found by the field's name, never by
# walking up to a containing wrapper, so the wrapper's format cannot be
# seen from it. Reuses the existing VALUE_CONTROL_FORMAT_CLOCK value on
# a second element, for the same reason.
VALUE_CONTROL_READOUT_FORMAT_ATTR = "data-value-readout-format"

# The painted position has no constant here: it travels on the
# `--value-fraction` custom property, server-written once and rewritten
# by value-controls.js on every steer. Its name fails
# companion/test_i18n.py's untranslated-copy scan (a leading `--`), so it
# lives inline in the markup, the script and style.css — pinned equal.

# The class companion/static/style.css hides by default and reveals
# under `.js`. Defined here so a page module never types it, and pinned
# against both the stylesheet and the no-JS control contract's registry.

# The class goes on the gated element itself, never an ancestor: that
# is checkable from rendered markup without parsing the whole tree.
JS_GATE_CLASS = "js-gate"

UI_THEME_CHOICES = ("auto", "light", "dark")

# The quick-action form protocol, shared by companion/app.py and
# config_page.py — a page module may never import another page module,
# so this lives in the shared layer instead.
QUICK_STATE_FIELD = "state"
QUICK_STATE_ON = "on"
QUICK_STATE_OFF = "off"

# The eleven QUICK_ACTION_* constants, moved here byte-identical from
# config_page.py, so home_page.py can share them too. Every English
# value is unchanged, so every French catalogue entry keeps resolving —
# it is keyed by English string, not by which module holds the constant.
QUICK_ACTION_SCREEN_LABEL = "Screen"
QUICK_ACTION_ON_TEXT = "On"
QUICK_ACTION_OFF_TEXT = "Off"
QUICK_ACTION_SWITCH_ON_BUTTON = "Switch on"
QUICK_ACTION_SWITCH_OFF_BUTTON = "Switch off"
QUICK_ACTION_QUIET_LABEL = "Quiet hours"
QUICK_ACTION_QUIET_ON_TEMPLATE = "On — %s to %s"
QUICK_ACTION_QUIET_OFF_TEXT = "Off"
# These four action wordings are no longer rendered markup: a
# role="switch" control may not be named by an action ("Switch off"
# contradicts aria-checked), so the button is now named by the setting
# via aria-labelledby. The constants survive only as names
# test_status_pages.py asserts are no longer rendered.
QUICK_ACTION_QUIET_TURN_ON_BUTTON = "Turn on"
QUICK_ACTION_QUIET_TURN_OFF_BUTTON = "Turn off"

# The no-JS floor here is structural, not additive: each switch IS the
# <form> that already shipped, POSTing to its own /quick/* route with a
# `state` field; remove quick-switch.js and the button still posts, the
# server still saves. `role="switch"`/`aria-checked` render from the
# saved value, so the accessible state is correct with no script too.

# The attribute the script marks its own unconfirmed control with;
# freshness.js's swap skips a region carrying it. Not a
# "data-quick-switch-*" name: a shipped check counts `data-quick-switch`
# occurrences, and a substring match would inflate that count.
QUICK_SWITCH_CONTROL_ATTR = "data-quick-control"
# The element the script marks pending: the whole cell/card holding
# the switch, so the region freshness.js would otherwise repaint is
# the one that stands still. Marking the region (not just the button)
# documents which region is being held.
QUICK_SWITCH_REGION_ATTR = "data-quick-region"
# The two state wordings, both server-rendered, exactly one hidden —
# this keeps companion/static/quick-switch.js free of user-facing copy
# entirely: an optimistic flip and its rollback are a pure attribute
# change over text the server already translated.
QUICK_STATE_ON_ATTR = "data-quick-state-on"
QUICK_STATE_OFF_ATTR = "data-quick-state-off"
# The accessible-name/description anchors. frame_strip_html() renders
# at most once per document, so these are fixed ids; config_page.py's
# LED switch carries its own pair.
QUICK_SWITCH_SCREEN_LABEL_ID = "quick-switch-screen-label"
QUICK_SWITCH_SCREEN_STATE_ID = "quick-switch-screen-state"
QUICK_SWITCH_QUIET_LABEL_ID = "quick-switch-quiet-label"
QUICK_SWITCH_QUIET_STATE_ID = "quick-switch-quiet-state"
# The failure announcement, byte-identical to companion/app.py's own
# FLASH_MESSAGES[FLASH_KEY_QUICK_FAILED]: neither reader is told a
# status code or anything else the server knows. layout.py may not
# import companion/app.py, so the English literal is duplicated here,
# like the QUICK_ACTION_* constants above.
QUICK_SWITCH_FAILED_TEXT = "Couldn't change that — please try again."
QUICK_SWITCH_FAILED_ATTR = "data-quick-failed-text"
QUICK_TOAST_ATTR = "data-quick-toast"
# No longer used by frame_strip_html(): the one computed delay
# sentence below (frame_state.py's DELAY_DUE/DELAY_HELD/DELAY_UNKNOWN)
# replaces this old static caption. It survives as DELAY_UNKNOWN's own
# wording (_FRAME_DELAY_UNKNOWN_TEXT below) and stays defined because
# config_page.py still references it directly.
QUICK_ACTION_APPLIES_SENTENCE = "Applies the next time the frame wakes up."

# The strip's own heading, byte-identical to home_page.FRAME_ROW_LABEL
# ("Frame") — both resolve through the same i18n catalogue entry, keyed
# by English string. A second, separately named constant is required
# because layout.py may never import a page module.
FRAME_STRIP_HEADING = "Frame"

# frame_state.py's HEADLINE_DUE/HEADLINE_HELD/HEADLINE_LATE are the
# one canonical registry of this copy; frame_strip_html() below calls
# frame_state.resolve_state()/headline_template() to pick between them,
# never re-deriving that decision.

# The six _FRAME_*_TEXT constants exist only because
# companion/test_i18n.py's AST scan proves a string alive by tracing a
# local `i18n.t(CONSTANT)` call, and cannot follow an attribute access.
# Kept byte-identical to their frame_state.py counterparts; only the
# wording's scanner-visible home is local.
_FRAME_HEADLINE_DUE_TEXT = "Next update ≈ %s"
_FRAME_HEADLINE_HELD_TEXT = "Next wake around %s · quiet hours"
_FRAME_HEADLINE_LATE_TEXT = "Expected since %s"
_FRAME_DELAY_DUE_TEXT = "Applies at the next wake, around %s."
_FRAME_DELAY_HELD_TEXT = "Applies when quiet hours end, around %s."
# Byte-identical to QUICK_ACTION_APPLIES_SENTENCE above by
# construction (same value, not a coincidence) — the retired static
# caption's own text survives as exactly this one computed branch's
# wording.
_FRAME_DELAY_UNKNOWN_TEXT = QUICK_ACTION_APPLIES_SENTENCE

# The quiet cell's caption link, appended to the same
# `delay_caption_html` slot the switch cells share — never a new slot.
# The link text is scanner-visible for the same reason the six
# _FRAME_*_TEXT constants above are: a local, byte-identical copy.
_FRAME_QUIET_SCHEDULE_LINK_TEXT = "Change the schedule"
# Byte-identical to config_page.py's own QUIET_HOURS_GROUP_HEADING_ID
# — duplicated, never imported, since a page module may never import
# another. Kept byte-identical by hand; a harness proves it.
_FRAME_QUIET_SCHEDULE_TARGET_ID = "quiet-hours-group-heading"

# The frame's held state reuses the app's existing neutral "off" dot
# — never a new colour, never the warn dot. "late" is `.dot--warn`;
# there is no fourth, "error" tier in the frame-state vocabulary any
# more.
_FRAME_DOT_CLASS_BY_STATE = {
    frame_state.STATE_DUE: "dot--ok",
    frame_state.STATE_HELD: "dot--off",
    frame_state.STATE_LATE: "dot--warn",
}

# "off" is a fourth, additive entry — never a fourth colour. `.dot--off`
# is defined in companion/static/style.css as "a neutral, everyday
# state ... never a problem"; `status_dot("off", label)` now renders it
# with its normal visible `.dot-label`, matching its siblings' shape.

# Additive by construction: no pre-existing caller passes "off", so
# every one is byte-identical to before. `_DEFAULT_STATUS_DOT_CLASS`
# still resolves an unrecognised state to the warn class; "off" is now
# a recognised state rather than an arbitrary one.
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

# card_status_class()'s own whitelist, kept as bare suffixes (not
# full class names) so the caller's own base class never has to be
# typed twice.
_CARD_STATUS_SUFFIXES = {
    "ok": "--ok",
    "warn": "--warn",
    "error": "--error",
}

# The icon-id whitelist for icon_html(). Grown incrementally as new nav
# labels and controls gained glyphs; the hamburger member is defined here
# rather than by its own consumer so ICON_DEFS_HTML stays the single write
# site for every icon in the app.
ICON_IDS = (
    "icon-device",
    "icon-pipeline",
    "icon-corroboration",
    # "icon-battery" has no consumer anywhere in the app today. Retained on
    # purpose: pruning it would also require a matching <symbol> deletion and
    # matching assertion edits in test_companion_app.py's sprite-integrity
    # check. This whitelist is an injection guard on icon_html()'s fragment
    # reference, not a usage index of what is currently rendered.
    "icon-battery",
    "icon-hamburger",
    "icon-nav-config",
    "icon-nav-health",
    "icon-nav-airlines",
    "icon-nav-history",
    # Stays a whitelist member even though NAV_TABS no longer references a
    # "preview" nav tab: its consumer is now history_page.py's View-panel
    # trigger button. Do not remove this as apparently-orphaned — an id
    # outside this whitelist makes icon_html() silently return "" and the
    # button would render an empty box with no error.
    "icon-nav-preview",
    "icon-nav-home",
    "icon-nav-flights",
    "icon-nav-device",
    "icon-nav-display",
    "icon-power",
    "icon-moon",
)

# Four more icons for the per-page redesign plans. Appended, not
# reordered, so ICON_DEFS_HTML's own symbol-id/ICON_IDS agreement check
# stays a straightforward set comparison.
ICON_IDS = ICON_IDS + (
    "icon-check",
    "icon-copy",
    "icon-refresh",
    "icon-search",
)

# One more icon, for the Airlines lightbox replace zone's upload glyph.
# Appended, not merged into an existing tuple, for the same reason above.
ICON_IDS = ICON_IDS + (
    "icon-upload",
)

# One more icon, for the bottom tab bar's "More" cell. Appended, not
# merged, for the same reason above.
ICON_IDS = ICON_IDS + (
    "icon-more",
)

# One more icon, for the mobile #site-nav-toggle: the panel it opens
# holds no page-navigation links (those moved to the bottom tab bar), so
# the hamburger glyph read as site navigation; replaced by a gear.
# Appended, not merged, for the same reason above.
ICON_IDS = ICON_IDS + (
    "icon-gear",
)

# One shared inline sprite, emitted once per document by page_shell().
# This sprite must never move inside a conditionally rendered region: a
# <use> referencing a symbol that isn't in the DOM at all (not merely
# hidden via `display: none`) resolves to nothing.

# Each symbol carries fill="none"/stroke="currentColor" so a single CSS
# `color` property drives the whole glyph. The four tile icons use a
# 20x20 viewBox; the hamburger uses 24x24 — plain <path>/<line>/<rect>/
# <circle> primitives, not detailed illustration.
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
    # Four more glyphs, same viewBox/stroke language as the ten above.
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
    # #site-nav-toggle's glyph: a centre circle plus a toothed outer ring,
    # same viewBox/stroke language as its closest neighbours by stroke
    # weight, built from <circle>/<path> only.
    '<symbol id="icon-gear" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="10" cy="10" r="2.6"/>'
    '<path d="M10 2.5v2.4M10 15.1v2.4M17.5 10h-2.4M4.9 10H2.5'
    'M15.3 4.7l-1.7 1.7M6.4 13.6l-1.7 1.7M15.3 15.3l-1.7-1.7'
    'M6.4 6.4L4.7 4.7"/>'
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
    # One more glyph, same viewBox/stroke language as above — the Airlines
    # lightbox replace zone's upload arrow-over-tray.
    '<symbol id="icon-upload" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<path d="M10 13V3"/>'
    '<path d="M6 7l4-4 4 4"/>'
    '<path d="M3.5 13v3a1.5 1.5 0 0 0 1.5 1.5h10a1.5 1.5 0 0 0 1.5-1.5v-3"/>'
    "</symbol>"
    # The bottom tab bar's "More" glyph: three dots drawn as zero-length
    # round-capped strokes rather than three <circle fill="currentColor">,
    # so this symbol keeps the sprite's own
    # fill="none"/stroke="currentColor" language.
    '<symbol id="icon-more" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="2.2" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<path d="M4.5 10h.01M10 10h.01M15.5 10h.01"/>'
    "</symbol>"
    "</defs>"
    "</svg>"
)

# The tint class stat_tile() adds to its own icon instance. Its
# counterpart is companion/static/style.css's `.stat-tile__icon` rule —
# a test harness reads that stylesheet from disk and asserts this class
# name actually appears in it, guarding against the two silently
# drifting apart.
STAT_TILE_ICON_CLASS = "stat-tile__icon"

# The Health route's slug, matching what _nav_links() already computes
# (`route.lstrip("/")`) — named once so a renderer can identify the
# Health link without re-deriving it from an already-escaped route
# string.
HEALTH_NAV_SLUG = "health"

# slug -> icon-id, one per NAV_TABS entry. A slug not present here
# (which cannot happen for a real NAV_TABS entry) falls through
# icon_html()'s own whitelist fallback ("" for an unrecognised id),
# never a KeyError.
NAV_ICON_IDS = {
    # Keyed by nav_slug(route). "flights" keeps the History clock glyph;
    # Home/Display/Device get their own symbols above.
    "home": "icon-nav-home",
    "display": "icon-nav-display",
    "flights": "icon-nav-history",
    "airlines": "icon-nav-airlines",
    "health": "icon-nav-health",
    "device": "icon-nav-device",
}

# The fragment id the skip-link's first-focusable <a href="#..."> points
# at and <main> carries as its own id. Named once so page_shell() never
# has the two literals drift apart.
SKIP_LINK_TARGET_ID = "main-content"

# A zero-external-dependency local favicon — a data URI needs neither a
# new static file nor a new route. #B13F16 is the light-mode
# --color-accent token. Held as its own module constant so
# login_shell() can reuse this exact literal without duplicating it.
FAVICON_LINK_HTML = (
    '<link rel="icon" href="data:image/svg+xml,'
    '%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 20 20%27%3E'
    '%3Crect width=%2720%27 height=%2720%27 rx=%274%27 fill=%27%23B13F16%27/%3E'
    '%3Ctext x=%2710%27 y=%2714%27 text-anchor=%27middle%27 '
    'font-family=%27Georgia,serif%27 font-size=%2712%27 fill=%27%23FFFFFF%27'
    '%3ES%3C/text%3E%3C/svg%3E">'
)

# The dot's own class, layered on top of the existing .dot/.dot--error
# classes rather than a new colour. Its counterpart is
# companion/static/style.css's `.nav-notification` rule — a test
# harness reads that stylesheet from disk and asserts this class name
# appears in it.
NAV_NOTIFICATION_CLASS = "nav-notification"

# Appended (not substituted) after the "Health" nav label text via a
# visually-hidden span, so assistive tech announces "Health — attention
# needed" rather than losing the word "Health" to an aria-label
# override.
HEALTH_ALERT_SUFFIX_TEXT = " — attention needed"


def icon_html(icon_id, size=20, extra_class=""):
    """A `<svg>` referencing one symbol from ICON_DEFS_HTML via `<use>`, or
    "" when `icon_id` is not a member of ICON_IDS.

    A whitelist, not a sanitiser: `icon_id` becomes a fragment identifier
    inside `<use href="...">`, so an unchecked id would be an
    attacker-influenceable reference; an unrecognised id fails
    visibly-but-safely (a missing icon) instead. `width`/`height` guard
    against companion/static/style.css's `.icon` rule being lost (an
    `<svg>` with neither renders at the SVG default 300x150).
    `aria-hidden="true"` is unconditional: every icon sits beside its own
    visible text label, so announcing it would duplicate the label.
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

    `None` becomes an empty string; any other non-string is coerced via
    str() first. Never raises, so a malformed upstream value degrades to an
    escaped string instead of crashing a page render.
    """
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    return html.escape(value, quote=True)


# Shared "absolute + relative" timestamp helpers, promoted from
# health_page.py's own private copies since one page module may not
# import another. Consumed by every page module that renders a stored
# instant.


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


# The French unit-suffix table relative_age_text()'s French branch
# consumes, in the same "fixed dict, membership lookup, documented
# fallback" shape _STATUS_DOT_CLASSES uses. Kept complete even though
# "s" is never reached (the seconds bucket short-circuits to
# "à l'instant" first).
_AGE_UNIT_SUFFIX_FR = {
    "s": "s",
    "m": "min",
    "h": "h",
    "d": "j",
}


def _age_bucket(age_seconds):
    """The s/m/h/d bucket a whole number of seconds falls in, as a `(value,
    unit_letter)` pair — the only place in this module the three
    threshold boundaries are written down.

    "3m ago" and "in 3m" are one ladder read in two directions: they
    must never disagree about where a bucket ends, so naming the
    boundaries once here makes that structural. The unit letters are
    the English suffixes themselves, so the English branch formats
    straight from this pair and the French branch maps them through
    _AGE_UNIT_SUFFIX_FR above.

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
    """"Ns ago"/"Nm ago"/"Nh ago"/"Nd ago" using the s/m/h/d threshold ladder
    `_age_bucket()` defines, shared with relative_future_text() below. A
    negative age (clock skew) is clamped to 0 rather than read as "in the
    future".

    `lang` is a trailing keyword; `None` resolves to prefs.current_lang() and
    the English branch stays byte-for-byte unchanged for every pre-existing
    call site.

    French collapses the whole under-a-minute bucket into one "à l'instant"
    phrase regardless of the exact second count. The minute/hour/day buckets
    carry a real U+00A0 non-breaking space between the number and the unit;
    that copy lives in companion/i18n_fr/health.py, read through
    i18n.t_lang() rather than duplicated as a module literal.
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
    """"in Ns"/"in Nm"/"in Nh"/"in Nd" — the forward reading of the same
    ladder relative_age_text() above reads backwards, over the same
    _age_bucket() boundaries.

    This function is formatting, never a verdict: it says how long
    remains until an instant somebody else computed, never
    "late"/"held"/"due" — those words are frame_state's. A `seconds_ahead`
    that has already elapsed resolves to the zero bucket, never a
    negative number or a past-tense string.

    `lang` is the same trailing keyword every sibling carries. French
    collapses the sub-minute bucket into "in a moment"; both strings live
    in companion/i18n_fr/health.py, read through i18n.t_lang().
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


def duration_text(seconds, lang=None):
    """A bare LENGTH of time — "5m"/"5 min", "2h"/"2 h" — over the same
    _age_bucket() ladder the two relative forms above read in their two
    directions.

    The third reading of one ladder: it names a cadence or a measured gap
    with no connector and no tense, unlike its two siblings which state an
    instant relative to now. Only the real U+00A0 between the number and
    its unit is added; the ladder and the French unit suffixes are
    not restated.

    A negative or non-numeric input clamps to the zero bucket through
    _age_bucket(), exactly as both siblings do. Never raises.
    """
    value, unit = _age_bucket(seconds)
    if lang is None:
        lang = prefs.current_lang()
    if lang == "fr":
        return "%d %s" % (value, _AGE_UNIT_SUFFIX_FR[unit])
    return "%d%s" % (value, unit)


# companion/static/relative-time.js rewrites every <time data-relative>
# element once a second, so the four bucket wordings must exist
# client-side. Rendered onto <body> by page_shell() and read back with
# getAttribute(), since several of these elements sit inside
# freshness.js's swap targets.

# One complete wording per bucket per direction, so the script carries no
# language logic. "#" is the quantity's place, not "%s": these reach the
# browser as attribute values, and companion/test_i18n.py's Check 3 scans
# every French render for a stray "%s"/"%d"/"{}" — "#" is not one.

# Not a second ladder: the same ladder's own output with the number
# lifted out. test_companion_app.py asserts each wording, filled with the
# quantity _age_bucket() picks, equals relative_age_text()'s/
# relative_future_text()'s own return value, in both languages.
RELATIVE_QUANTITY_MARK = "#"
RELATIVE_PAST_SECONDS_TEXT = "#s ago"
RELATIVE_PAST_MINUTES_TEXT = "#m ago"
RELATIVE_PAST_HOURS_TEXT = "#h ago"
RELATIVE_PAST_DAYS_TEXT = "#d ago"
RELATIVE_FUTURE_SECONDS_TEXT = "in #s"
RELATIVE_FUTURE_MINUTES_TEXT = "in #m"
RELATIVE_FUTURE_HOURS_TEXT = "in #h"
RELATIVE_FUTURE_DAYS_TEXT = "in #d"

# What a countdown reads once its instant has passed. Never a warning
# word or colour — a thing which has not happened yet is not a fault;
# this is the app's neutral breathing treatment.
RELATIVE_WAITING_TEXT = "waiting…"

# Must equal the attribute names companion/static/relative-time.js
# reads, in bucket order (s/m/h/d), matching _age_bucket()'s own unit
# letters. test_companion_app.py pins every one present in that file's
# source.
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
# COUNTDOWN rather than an age (see its `countdown` keyword). Also
# read by companion/static/relative-time.js.
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
    """The ticker's own copy as `((attribute name, translated wording), ...)`,
    ready for page_shell() to render onto `<body>`.

    Nine pairs: four past wordings, four future wordings, and the waiting
    phrase an expired countdown reads. Every value goes through
    i18n.t_lang() here, server-side, so companion/static/relative-time.js
    carries no French at all.
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


# duration_text() above is this app's one length-of-time ladder.
# companion/static/value-controls.js's quiet-hours readout needs a LIVE
# duration after a drag/keyboard step/edit, which never round-trips
# through the server: these wordings are duration_text()'s own output
# with the number lifted back out.

# One complete wording per bucket, reusing RELATIVE_QUANTITY_MARK ("#")
# for the same attribute-value scanning reason above. The French U+00A0
# between number and unit lives in the i18n_fr catalogue entry, not in
# this module.

# All four buckets ship even though a quiet window's arithmetic can
# never reach "d": "s" is reachable (a zero-length window is real), and
# a ladder with a hole in it is one somebody falls through later.
DURATION_SECONDS_TEXT = "#s"
DURATION_MINUTES_TEXT = "#m"
DURATION_HOURS_TEXT = "#h"
DURATION_DAYS_TEXT = "#d"

# Ordered s/m/h/d, matching _age_bucket()'s own unit letters. Read by
# config_page.py's quiet_dial_readout_html() and by
# companion/static/value-controls.js, which walks these four attributes
# in order to pick the bucket the live window falls in.
DURATION_ATTRS = (
    "data-duration-s",
    "data-duration-m",
    "data-duration-h",
    "data-duration-d",
)


def _machine_instant(parsed):
    """`parsed` as a machine-readable Europe/Paris ISO-8601 instant at
    seconds precision, or "" when it cannot be produced.

    The value `relative_time_html()` puts in a `datetime` attribute —
    never the raw stored string: it carries the same instant converted
    onto the one timezone this app speaks, offset included, so the
    script reading it is unambiguous.

    A naive datetime is taken as UTC, matching `local_clock_text()`'s own
    convention. Never raises: an unconvertible input returns "", and the
    caller renders plain text rather than an element with an empty
    attribute.
    """
    try:
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=ZoneInfo("UTC"))
        return parsed.astimezone(LOCAL_TZ).isoformat(timespec="seconds")
    except (ValueError, OverflowError, AttributeError):
        return ""


def relative_time_html(ts, now_ts, fallback="no reading yet", lang=None,
                       countdown=False, static_text=None):
    """`<time datetime="<instant>" data-relative><relative age></time>` — the
    app's one relative-time element. Callers interpolate the return value
    verbatim, never re-escaping it (already escaped here); the no-JS
    rendering is the complete server text, no ticker needed. Returns the
    escaped `fallback` when `ts` is falsy, escaped `ts` on parse failure.

    `countdown` counts toward a future instant, reading
    RELATIVE_WAITING_TEXT once it passes rather than becoming an age.
    `static_text` renders fixed text instead of the ladder's output, for
    the one case where the server rendering must stay true with no
    ticker (e.g. an absolute clock rather than a duration).
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
    """`"<ts> (<relative age> ago)"` — the house "absolute + relative"
    timestamp format, shared by every caller. Returns `fallback` when
    `ts` is falsy; returns `ts` unchanged (absolute only) when
    age_seconds() cannot parse either side — never raising.

    The return value is plain, unescaped text, the same contract
    status_dot()'s `label` carries: every caller must escape it directly
    or hand it to a builder that already escapes (e.g. data_table()).
    Absolute-first ordering (ISO string, then relative age in
    parentheses) is canonical and must not be reversed.

    `lang` defaults to `None`, resolved via relative_age_text()'s own
    default; an explicit `lang` threads through for a caller with no
    request context (e.g. a server-side notification body).
    """
    if not ts:
        return fallback
    age = age_seconds(ts, now_ts)
    if age is None:
        return ts
    return "%s (%s)" % (ts, relative_age_text(age, lang=lang))


# A `now_parsed` guaranteed to fall on a different calendar day than
# any real timestamp, forcing local_clock_text()'s cross-day "D Mon
# HH:MM" branch — how concise_timestamp_html()'s `title` below becomes a
# full local timestamp, reusing local_clock_text() rather than a second
# implementation.
_FULL_TIMESTAMP_SENTINEL_NOW = datetime(1970, 1, 1, tzinfo=ZoneInfo("UTC"))


def concise_timestamp_html(ts, now_ts, fallback="no reading yet", lang=None):
    """`<span class="mono" title="<D Mon HH:MM local>"><HH:MM local>
    (<relative>)</span>` — the concise-timestamp-by-default format,
    absolute-first per absolute_and_relative()'s ordering. `title` is
    always a full, day-qualified local timestamp, never the raw ISO
    string.

    Callers interpolate the return value verbatim, never re-escaping it.
    Returns the escaped `fallback` when `ts` is falsy; on a parse
    failure, returns a span with the raw value in both slots rather than
    raising. absolute_and_relative() remains the right choice for any
    plain-text-only call site. `lang` defaults to `None`, resolved via
    local_clock_text()'s/relative_age_text()'s own default.
    """
    if not ts:
        return escape_html(fallback)
    parsed = parse_iso(ts)
    age = age_seconds(ts, now_ts)
    if parsed is None or age is None:
        return '<span class="mono" title="%s">%s</span>' % (
            escape_html(ts), escape_html(ts))
    full_local = local_clock_text(parsed, _FULL_TIMESTAMP_SENTINEL_NOW, lang=lang)
    # The parenthesised relative half is relative_time_html()'s element,
    # not a bare escaped string, so every caller inherits the convention.
    # The parentheses stay OUTSIDE the element — punctuation, not part of
    # the age — so the ticker rewriting the element's text need not
    # reproduce them.
    return '<span class="mono" title="%s">%s (%s)</span>' % (
        escape_html(full_local),
        escape_html(local_clock_text(parsed, parse_iso(now_ts), lang=lang)),
        relative_time_html(ts, now_ts, lang=lang))


def month_abbr(month, lang=None):
    """The language-aware abbreviated month name, for callers that build
    their own "D Mon" labels (the Health battery chart's X axis) — the
    same tables local_clock_text() below selects between, exposed once
    instead of copied. `lang` defaults to the request's resolved
    language; `month` is 1..12.
    """
    if lang is None:
        lang = prefs.current_lang()
    table = _MONTH_ABBR_FR if lang == "fr" else _MONTH_ABBR
    return table[month - 1]


def local_clock_text(parsed, now_parsed=None, lang=None):
    """`parsed` (aware or naive) rendered on LOCAL_TZ: "HH:MM" when it falls
    on the same local day as `now_parsed` (or when no `now` is supplied),
    otherwise "D Mon HH:MM". A naive datetime is taken as UTC. Never
    raises.

    `lang` defaults to `None`, resolved to prefs.current_lang(): under a
    French request the month abbreviation comes from _MONTH_ABBR_FR
    instead; the clock itself stays 24-hour Europe/Paris in both
    languages.
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
    """Return the UI theme named by `cookies`, or "auto" when the cookie is
    missing or holds a value outside UI_THEME_CHOICES.

    Membership test before use: a client-controlled cookie value is never
    trusted as-is.
    """
    if not isinstance(cookies, dict):
        return "auto"
    value = cookies.get(UI_THEME_COOKIE_NAME)
    return value if value in UI_THEME_CHOICES else "auto"


def _nav_links(active):
    """Return one (is_active, escaped_route, escaped_label, slug) tuple per
    NAV_TABS entry, in NAV_TABS order.

    The single place NAV_TABS is iterated and its route/label pair
    escaped; sidebar_nav() and _mobile_nav_html() both consume this (via
    _nav_groups() below) instead of re-implementing the same
    escaping/active-state logic twice. The unescaped `slug` lets a
    renderer identify a specific link (e.g. the Health nav-tab
    notification dot's target) without re-deriving it from an
    already-escaped route string.
    """
    links = []
    for route, label in NAV_TABS:
        slug = nav_slug(route)
        is_active = slug == active
        # The label is looked up through i18n.t() at render time — NAV_TABS/
        # NAV_GROUPS keep their English values; escape_html() still wraps the
        # result, exactly like any other t() call site.
        links.append((is_active, escape_html(route), escape_html(i18n.t(label)), slug))
    return links


def _nav_groups(active):
    """NAV_GROUPS in display order, each as (escaped_group_label, links)
    where `links` is the slice of _nav_links(active) belonging to that
    group. The one place the group structure is walked, so the sidebar
    and the dropdown can never disagree about which tab sits under the
    "Advanced" label.

    The Advanced group (Health, Device) renders on every page for every
    request; `/health` and `/device` were always reachable by URL and stay
    session-gated regardless.
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


# There are exactly two live nav renderers, sidebar_nav() and
# _mobile_nav_html() below, both fed by _nav_links() above. A
# horizontally-scrollable nav strip used to render here; real-device
# testing found it hid most tabs behind an undiscoverable swipe, so it
# was replaced rather than repaired.


def _health_alert_markup(severity):
    """The Health nav-tab notification dot plus its visually-hidden
    screen-reader suffix, built once so every nav renderer shares one
    markup source. `severity` is "warn" or "error"; the dot class comes
    from the same `_STATUS_DOT_CLASSES` dict status_dot() uses.

    Appends a visually-hidden text suffix rather than an `aria-label`:
    an `aria-label` would replace the link's accessible name, dropping
    the word "Health". The absence of this markup is the all-clear
    signal: nothing renders when everything is fine.
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
# The middle dot that separates the two state segments, promoted to a
# named constant because the two segments are `white-space: nowrap`
# spans inside a wrapping flex row (the line may break BETWEEN them,
# never inside one), so the separator is a sibling of both rather than
# punctuation embedded in one.
NAV_STATUS_SEPARATOR_TEXT = " · "


def nav_status_html(device_config, active=None):
    """The nav's state-only reminder: one shared body, called by both
    sidebar_nav() and _mobile_nav_html(), reading the same `device_config`
    fields frame_strip_html() reads, so all three can never disagree.
    Returns "" when `device_config` is falsy.

    A plain `<a href="/">` — no form, no button, no script. Its
    `aria-label` states where it goes, since the two dot+word segments
    alone do not read as a destination; every value crosses
    escape_html(), every string crosses i18n.t().

    `active`: on Home's own slug, renders a `<span>` with no `href`
    instead, since a link there would promise navigation to the page
    already occupied; its `aria-label` reuses the same translated
    strings the segments show, so the two cannot drift.
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
    dashboard sidebar column at desktop width. Renders NAV_TABS via the
    shared _nav_links() helper; the 960px CSS media query, not this
    function, decides whether sidebar_nav() or _mobile_nav_html() is
    visible.

    `health_alert` is `None`/`"ok"` for no dot, or `"warn"`/`"error"` to
    append _health_alert_markup() after the Health link's label only,
    interpolated verbatim as already-built safe HTML. The active link's
    `<a>` carries `aria-current="page"` — never the inactive links.

    `device_config` threads to nav_status_html(), whose reminder markup
    is prepended before this function's `<nav>`; `None` renders none.
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
        # An unlabelled group renders its links bare; a labelled group
        # ("Advanced") wraps them in a .nav-group carrying a small uppercase
        # label so the split reads at a glance.
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
        # `active` is threaded through so the reminder can drop its href on
        # Home — one shared body, two call sites, one active-route argument, so
        # the sidebar and the dropdown can still never disagree about its shape
        # either.
        nav_status_html(device_config, active=active),
        # "Primary navigation" is the one nav landmark exposed to the
        # accessibility tree at any given viewport width (see this module's own
        # comment above _mobile_nav_html()).
        escape_html(i18n.t("Primary navigation")),
        "".join(parts))


# The bottom tab bar's "More" cell label. Sentence case, and not the
# label voice — a nav destination is a destination, not a label, which
# is why companion/static/style.css's `.tab-bar__label` declares no
# uppercase and no tracking.
TAB_BAR_MORE_LABEL = "More"

# The glyph on that cell. A whitelist member (ICON_IDS above), so
# icon_html()'s own fallback contract applies unchanged.
TAB_BAR_MORE_ICON_ID = "icon-more"

# The `<body>` marker page_shell() adds only when the tab bar really
# renders. companion/static/style.css scopes the sub-960px page-foot
# clearance to it, so pages that render no bar reserve no space for
# one.
TAB_BAR_BODY_CLASS = "has-tab-bar"

# companion/static/freshness.js shows a visible neutral badge when its
# refresh loop is retrying or idle, instead of stopping dead. The badge
# is built client-side, so its two strings are server-rendered onto
# <body> and read with getAttribute().

# They live on <body> rather than on the pill: the pill's freshness
# wrapper is a swap target, and an attribute there would be replaced out
# from under the script on every refresh.

# Emitted unconditionally, like the deferred scripts below: most pages
# carry no refresh loop, and the attributes are inert there.
REFRESH_PAUSED_TEXT = "Paused"
REFRESH_RECONNECTING_TEXT = "Reconnecting…"

# Must equal the attribute names companion/static/freshness.js reads.
REFRESH_PAUSED_ATTR = "data-refresh-paused-text"
REFRESH_RECONNECTING_ATTR = "data-refresh-reconnecting-text"


# freshness.js used to carry a hard-coded selector list, duplicated and
# pinned equal elsewhere — three hand-maintained copies is a shape this
# codebase has learned not to build: they drift silently after the day
# they are written.

# One mapping here, one page key rendered on <body>, and one object
# literal in the script mirroring this, pinned entry-for-entry and
# key-for-key by companion/test_status_pages.py in both directions. The
# keys are nav_slug()'s own values, never a second vocabulary.
REFRESH_PAGE_ATTR = "data-refresh-page"
REFRESH_PAGE_HOME = nav_slug(HOME_ROUTE)
REFRESH_PAGE_DISPLAY = nav_slug(DISPLAY_ROUTE)
REFRESH_PAGE_HEALTH = nav_slug(HEALTH_ROUTE)
REFRESH_PAGE_FLIGHTS = nav_slug(FLIGHTS_ROUTE)

# The two cross-file literals the new-row highlight is built on,
# duplicated into freshness.js rather than imported, and pinned equal by
# companion/test_status_pages.py.

# REFRESH_ROW_ID_ATTR carries a stable identity for the EVENT a row
# describes, not its position: a highlight keyed to position would light
# up every row below an insertion. Rendered from the runway_events row's
# own primary key.
REFRESH_ROW_ID_ATTR = "data-flight-id"
# The class freshness.js adds to a row whose identity was not in the
# set it knew before the swap. One-shot by construction: the node it
# lands on was itself just inserted, and the next swap replaces that
# node entirely.
REFRESH_NEW_ROW_CLASS = "is-new-row"

# The marker a region carries while it holds an OPTIMISTIC control whose
# server confirmation has not arrived. The swap skips it, since
# repainting with the server's older answer would make the control
# appear to bounce back. Duplicated into freshness.js, pinned by
# companion/test_status_pages.py.
REFRESH_PENDING_ATTR = "data-pending"

# The single, greppable definition of every DOM region freshness.js
# swaps wholesale, replacing each node with its fetched equivalent.
# Duplicated rather than imported — freshness.js is a static asset, not
# a Python module.

# HEALTH: excludes the sparkline, the registry card/filter bar and every
# <details> — swapping any would leave battery-trend.js's chart or
# list-filter.js's filter permanently dead (each captures its DOM once).

# `a[href="/health"]`, not a ".dot" selector, is the nav-severity target:
# the severity dot only exists in the DOM for "warn"/"error", so a
# dot-only selector would have nothing to replace when severity clears.

# HOME: the regions that change between polls, plus the freshness line.
# The recent-flights SECTION, not its <ul>, is the target so the
# empty-state-to-list transition is covered too. Not nested.

# FLIGHTS: both renderings of the list (phone cards, desktop table) plus
# the count and freshness line — a swap replacing only one would leave
# the other stale after a resize.

# Deliberately excluded: list-filter.js resolves four elements once at
# load and holds those references; replacing any detaches the node it
# writes to, silently killing the filter. `[data-filter-count]` is here
# since the script now looks it up fresh on every keystroke.

# The rows themselves were never captured (list-filter.js queries them
# fresh), so swapping them costs nothing; the filter's applied state
# does need list-filter.js to re-run after a swap, since the server
# renders the list unfiltered.

# DISPLAY: only the strip and freshness line — a deliberate asymmetry
# with Home. Everything else on that page is a form, and a swap must
# never touch a form: it would discard a half-typed value silently.
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
    REFRESH_PAGE_FLIGHTS: (
        ".page-header__freshness",
        "ul.history-cards",
        ".data-table-wrap",
        "[data-filter-count]",
        # The Show-more nav's own `href` advances by one page on every
        # render; a skipped refresh would leave a stale href on screen.
        # Declaring it here is also why _show_more_html() renders an
        # empty <nav> rather than nothing: the registry-witness check
        # requires every declared region findable in every rendered page.
        ".flights-more",
    ),
}


def _tab_bar_html(active, health_alert=None, device_config=None):
    """Bottom tab bar shown below 960px, replacing the hamburger dropdown as the
    sub-960px nav.

    Renders NAV_GROUPS via _nav_groups()/_nav_links(), the same iteration
    sidebar_nav() and _mobile_nav_html() use, so all three renderings share one
    route list. The "More" overflow uses a native <details>/<summary> so it works
    with scripts blocked. health_alert is drawn on the More summary, not on the
    Health link inside it, since the sheet is collapsed by default.
    Returns "" when device_config is falsy (no session context, e.g.
    login/404 pages).
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
                # Reuses .mobile-nav__link rather than a new class, so the sheet's rows share
                # its 44px/16px tap-target geometry instead of duplicating the numbers.
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
        # Same translated landmark name as sidebar_nav(); the 960px CSS breakpoint sets
        # display: none on the losing copy, so only one is ever in the accessibility
        # tree.
        escape_html(i18n.t("Primary navigation")),
        "".join(cells))


def _tab_bar_cell_body(icon_id, label, extra_html=""):
    """One tab cell's icon-above-label stack, wrapped in a pill span for the
    active/hover tint.

    The pill wraps the cell rather than replacing it, so the cell keeps its full
    78x56px tap area while the active tint is inset from the edge. `label` and
    `extra_html` arrive already escaped/safe and are interpolated verbatim.
    """
    return (
        '<span class="tab-bar__pill">%s'
        '<span class="tab-bar__label">%s</span>%s</span>'
    ) % (
        icon_html(icon_id, extra_class="tab-bar__icon"), label, extra_html)


def _theme_form_html(resolved_theme):
    # A function-scoped lookup table, not `choice.capitalize()`:
    # companion/test_i18n.py's AST scanner cannot fold a `.capitalize()` call back
    # to a literal, so `choice` indexes this table before reaching i18n.t(),
    # keeping the call scanner-visible.
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
               # `choice` ("auto"/"light"/"dark") is the form's own value and stays an
               # untranslated identifier; only the rendered label text goes through i18n.t().
               escape_html(i18n.t(_THEME_LABEL_TEXT[choice]))))
    # An aria-label disambiguates this segmented group from its siblings below;
    # the theme ids ("Auto"/"Light"/"Dark") are identifiers, so only the group
    # label is translated.
    return (
        '<form class="theme-form" method="post" action="/ui-theme" aria-label="%s">%s</form>'
        % (escape_html(i18n.t("Theme")), "".join(options)))


def _lang_form_html(resolved_lang):
    """The FR/EN language switch, a sibling of _theme_form_html() in shape.
    "FR"/"EN" are identifiers and are never passed through i18n.t().
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


def _logout_form_html():
    """The POST /logout control, shared verbatim by the sidebar and mobile-nav
    footers.

    The `/logout` path is hard-coded rather than imported from companion.app to
    avoid a circular import. method="post" matters: a GET logout can be
    triggered by a stray prefetch, crawler or `<img src="/logout">`, silently
    ending a session.
    """
    return (
        '<form method="post" action="/logout" class="logout-form">'
        '<button type="submit">%s</button>'
        "</form>"
    ) % escape_html(i18n.t("Sign out"))


def _mobile_nav_html(
        active, theme_form_html, health_alert=None, lang_form_html="",
        device_config=None):
    """The hamburger toggle and its <960px preferences panel: language/theme
    switches and Sign out. Destination links live in _tab_bar_html() instead, so
    this panel carries no navigation landmark of its own.

    The panel pushes content down in-flow (flex-basis: 100%) rather than
    overlaying it, and is always rendered closed — companion/static/
    nav-dropdown.js toggles the open class client-side, keyed off the toggle's
    aria-expanded attribute. `health_alert` is accepted but unused, kept only so
    existing call sites stay unchanged.
    """
    del health_alert
    toggle_html = (
        '<button type="button" id="%s" class="site-nav-toggle" '
        'aria-label="%s" aria-expanded="false" aria-controls="%s">%s</button>'
    ) % (
        NAV_TOGGLE_ID, escape_html(i18n.t(NAV_TOGGLE_LABEL)), MOBILE_NAV_ID,
        icon_html("icon-gear", size=24))
    # Footer order: language, theme, Sign out.
    footer_html = (
        '<div class="mobile-nav__footer">%s%s%s</div>'
        % (lang_form_html, theme_form_html, _logout_form_html()))
    # The document carries exactly two "Primary navigation" landmarks (sidebar,
    # tab bar); the 960px CSS breakpoint exposes exactly one to the accessibility
    # tree at a time.
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
    """Minimal HTML5 document for the pre-authentication login page.

    Deliberately separate from page_shell() rather than a parameterized branch:
    page_shell() always renders the full authenticated sidebar/mobile-nav/
    footer, which would visually imply the whole site's nav is usable before
    signing in. Shares page_shell()'s outer document structure (doctype, head,
    FAVICON_LINK_HTML) but the body holds only the login card: no icon sprite,
    skip link, sidebar or nav-dropdown script. Emits exactly one deferred script
    tag, the login card's own.
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
        # Only "Login" is translated; SITE_TITLE is a brand name and stays
        # untranslated, so the title keeps the same "<page> - <product>" shape as
        # page_shell()'s <title>.
        escape_html(i18n.t("Login")),
        escape_html(SITE_TITLE),
        FAVICON_LINK_HTML,
        body,
        LOGIN_CARD_SCRIPT_SRC,
    )


# A substitution token, never markup that ships: page_header() emits it,
# page_shell() swaps it for the flash banner when present, and strips any
# leftover occurrence unconditionally before the response is returned.
FLASH_SLOT_MARKER = "<!--flash-slot-->"


# The freshness line: one definition site with three call sites, so markup
# read by two scripts and pinned by test harnesses cannot drift between
# copies. companion/pages/health_page.py imports these names from here rather
# than redefining them.
REFRESH_PILL_TEXT = "Updating…"

# The hook companion/static/freshness.js toggles its breathing class on.
# Duplicated rather than imported, since freshness.js is a static asset, not a
# Python module.
REFRESH_LIVE_DOT_ATTR = "data-refresh-live-dot"

FRESHNESS_PREFIX_TEXT = "Updated "

# A `now_parsed` guaranteed to fall on a different Europe/Paris calendar day
# than any real device reading, forcing local_clock_text()'s cross-day
# "D Mon HH:MM" branch instead of duplicating that format elsewhere.
FULL_TIMESTAMP_SENTINEL_NOW = datetime(1970, 1, 1, tzinfo=ZoneInfo("UTC"))


def full_local_timestamp_text(ts):
    """`"D Mon HH:MM"` in Europe/Paris: the full local timestamp used for
    `title`/`aria-label`/`data-when` attributes on a stored instant.

    Falls back to the raw `ts` string, never raising, if it fails to parse.
    """
    parsed = parse_iso(ts)
    if parsed is None:
        return ts or ""
    return local_clock_text(parsed, now_parsed=FULL_TIMESTAMP_SENTINEL_NOW)


def freshness_line_html(now, lang=None):
    """The page-header freshness line: a neutral live dot, the "Updated " prefix,
    the clock and the hidden "Updating…" pill (carrying `data-loaded-at`),
    inside one block-level wrapper.

    Returns "" when `now` is falsy, so there is no honest instant to render;
    with no `data-loaded-at` marker, companion/static/freshness.js's loop never
    starts.

    Callers interpolate the return value verbatim (RAW markup); every piece is
    already escaped internally via escape_html().
    """
    if not now:
        return ""
    # escape_html() is required on `now`: i18n.t(REFRESH_PILL_TEXT) is not
    # pre-escaped.

    # No ARIA role on the pill: a live region announces on content
    # mutation, not visibility. Known gap: a reload while a screen
    # reader has focus resets its virtual cursor.
    pill_html = (
        '<span class="refresh-pill" data-refresh-pill data-loaded-at="%s" hidden>%s%s</span>'
        % (escape_html(now), icon_html("icon-refresh"), escape_html(i18n.t(REFRESH_PILL_TEXT))))
    # Server-rendered static and neutral; the breathing motion is a class
    # freshness.js adds/removes, so a scripts-blocked page shows a still
    # dot beside a static age. `.dot--off` carries no verdict colour —
    # a loop's live/paused state is not a device verdict.
    dot_html = (
        '<span class="dot dot--off" %s aria-hidden="true"></span>'
        % REFRESH_LIVE_DOT_ATTR)
    # The clock is local_clock_text() with `now_parsed` set to the same
    # instant, forcing its same-day "HH:MM" branch. `data-loaded-at` on
    # the pill carries the machine-readable instant freshness.js reads;
    # the `title` is tooltip only.

    # `.time-value`, not `.mono`: monospace is reserved for identifiers,
    # not a wall-clock time; `.time-value` keeps tabular numerals so the
    # digits hold their column as the clock ticks.
    _now_parsed = parse_iso(now)
    _clock_text = (
        local_clock_text(_now_parsed, now_parsed=_now_parsed)
        if _now_parsed is not None else now)
    clock_html = (
        '<span class="time-value" data-refresh-clock title="%s">%s</span>'
        % (escape_html(full_local_timestamp_text(now)),
           relative_time_html(now, now, static_text=_clock_text)))
    # One block-level wrapper for prefix+clock+pill: `.page-header` is a
    # block box, and a bare inline pill span would force an anonymous
    # block box, producing an extra gap.

    # This element is a REFRESH_SWAP_SELECTORS_BY_PAGE entry: freshness.js
    # replaces it wholesale, so a render-time value is honest only until
    # the next swap.
    freshness_html = (
        '<p class="page-header__freshness text-label">%s%s%s%s</p>'
        % (dot_html, escape_html(i18n.t(FRESHNESS_PREFIX_TEXT)),
           clock_html, pill_html))
    return freshness_html


def page_shell(
        title, active, body, ui_theme="auto", flash=None, banner=None,
        health_alert=None, lang=None, device_config=None):
    """Return a complete HTML5 document wrapping `body` in the shared shell.

    `title` and nav labels are escaped here. `body`, `flash` and `banner` are
    pre-built markup strings; the caller must have already escaped their own
    dynamic parts.

    `health_alert` is `None`/`"ok"` (no dot) or `"warn"`/`"error"` (a dot),
    threaded to sidebar_nav() and _mobile_nav_html(); a caller with no request
    context (login, 404, preview-image errors) draws no dot. `lang` defaults to
    `None`, resolved through prefs.current_lang(). `device_config` defaults to
    `None`, the same no-context degrade, threaded to both nav renderers via
    nav_status_html().
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
    # "" when `device_config` is falsy (no session, e.g. 404/preview-image
    # pages), so `<body>` carries TAB_BAR_BODY_CLASS only when the bar is really
    # present — letting companion/static/style.css reserve the bar's clearance
    # only on pages that have one.
    tab_bar_html = _tab_bar_html(
        active, health_alert=health_alert, device_config=device_config)
    body_class_attr = (
        ' class="%s"' % TAB_BAR_BODY_CLASS if tab_bar_html else "")
    # freshness.js's two neutral loop-state strings, translated here and read
    # client-side; see their constants above for why they live on <body>.
    body_class_attr += (
        ' %s="%s" %s="%s"' % (
            REFRESH_PAUSED_ATTR,
            escape_html(i18n.t(REFRESH_PAUSED_TEXT)),
            REFRESH_RECONNECTING_ATTR,
            escape_html(i18n.t(REFRESH_RECONNECTING_TEXT))))
    # The page key selecting this document's swap-region list out of
    # REFRESH_SWAP_SELECTORS_BY_PAGE. Lives on <body> because it, like the other
    # attributes here, sits beside elements that are themselves swap targets, and
    # <body> is the one element no swap ever replaces. Rendered for every page; an
    # unknown key selects nothing.
    body_class_attr += ' %s="%s"' % (
        REFRESH_PAGE_ATTR, escape_html(active))
    # The optimistic switch's user-facing sentence, translated here and read
    # client-side, on <body> for the same swap-safety reason as the attributes
    # above — emitted unconditionally; a page with no switch carries one inert
    # attribute.
    body_class_attr += ' %s="%s"' % (
        QUICK_SWITCH_FAILED_ATTR, escape_html(i18n.t(QUICK_SWITCH_FAILED_TEXT)))
    # relative-time.js's nine wordings, on <body> for the same swap-safety
    # reason. Emitted unconditionally; a page with no relative time carries nine
    # inert attributes.
    for _copy_attr, _copy_text in relative_copy_attrs():
        body_class_attr += ' %s="%s"' % (_copy_attr, escape_html(_copy_text))
    flash_html = flash or ""
    banner_html = banner or ""

    # `body` is an opaque pre-built string, so page_header() leaves
    # FLASH_SLOT_MARKER as a literal splice point below the header. A page
    # built on page_header() gets the marker replaced and `flash_html`
    # cleared; other pages keep their old before-body slot. The second
    # replace() below strips any leftover marker unconditionally.
    if FLASH_SLOT_MARKER in body:
        body = body.replace(FLASH_SLOT_MARKER, flash_html, 1)
        flash_html = ""
    body = body.replace(FLASH_SLOT_MARKER, "")

    # The sidebar's theme picker and Sign out control, grouped in one footer
    # region. Order: language, theme, Sign out — this and _mobile_nav_html()'s
    # own footer_html must change together.
    sidebar_footer_html = (
        '<div class="sidebar-footer">%s%s%s</div>'
        % (lang_form_html, theme_form_html, _logout_form_html()))

    # The first focusable element in <body>, before even ICON_DEFS_HTML — a
    # keyboard/screen-reader user's very first tab stop on every page.
    skip_link_html = (
        '<a class="skip-link" href="#%s">Skip to content</a>'
        % SKIP_LINK_TARGET_ID)

    # <aside> precedes <header> in source order: at desktop width, where
    # CSS hides the header, a keyboard user tabs into the sidebar nav
    # first. Both nav copies stay in the DOM always; only the 960px CSS
    # media query decides which is visible, so exactly one navigation
    # landmark is ever exposed to the accessibility tree.

    # ICON_DEFS_HTML is emitted once per document, right after <body>.
    # The theme form renders once in the sidebar and once in the
    # hamburger dropdown, never a third time in the header.
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
        # The tab bar sits outside .dashboard-shell, a sibling rather than
        # a descendant of the scrolled content column, so its
        # `position: fixed` box is not nested inside the shell's own
        # stacking context. `""` on a page with no bar, like the flash slot.
        "%s\n"
        # The optimistic switch's failure announcement: rendered empty,
        # once per document, never hidden — a live region added at
        # announce time is one screen readers often miss. role="alert"
        # implies aria-live="assertive" for a failure the user awaits.

        # The one script-only surface here, and additive: with no script
        # there is no fetch, so nothing here can fail beyond what the
        # server's own flash already reports.
        '<div class="quick-toast" %s role="alert"></div>\n'
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
        QUICK_TOAST_ATTR,
        NAV_DROPDOWN_SCRIPT_SRC,
        # Emitted unconditionally on every authenticated page, matching
        # nav-dropdown.js and battery-trend.js's serve-everywhere,
        # no-op-via-guard-clause convention.
        DIRTY_STATE_SCRIPT_SRC,
        LIST_FILTER_SCRIPT_SRC,
        COPY_BUTTON_SCRIPT_SRC,
        FRESHNESS_SCRIPT_SRC,
        # Same unconditional convention; History and the Airlines gallery both
        # render #panel-lookup-dialog.
        PANEL_LOOKUP_SCRIPT_SRC,
        # Same unconditional convention; cleans up after the flash banner this
        # function emits on every authenticated page.
        FLASH_CLEANUP_SCRIPT_SRC,
        # Same unconditional convention; only Settings renders #poll-trigger-btn.
        POLL_COOLDOWN_SCRIPT_SRC,
        # Same unconditional convention; only the Device page renders a
        # form[data-confirm] (the calendar disconnect form).
        CONFIRM_SUBMIT_SCRIPT_SRC,
        # Same unconditional convention; only Display renders .theme-live-preview
        # img plus .theme-chip-grid.
        THEME_PREVIEW_SCRIPT_SRC,
        # Same unconditional convention; only Flights renders .flight-detail-row /
        # [data-row-toggle].
        FLIGHT_ROWS_SCRIPT_SRC,
        # Same unconditional convention, and here the convention is the point: the
        # guard is a delegated document-level submit listener, so covering every
        # form costs one registration.
        SUBMIT_GUARD_SCRIPT_SRC,
        # Same unconditional convention. The elements it ticks come from one
        # builder (relative_time_html(), reached mostly via
        # concise_timestamp_html()), so no page module needs to know whether it has
        # one; its own guard clause returns early otherwise.
        RELATIVE_TIME_SCRIPT_SRC,
        # Same unconditional convention: the listener is delegated at document level
        # over every [data-quick-switch] form (Home/Display's Frame strip, Device's
        # LED switch), and with the file absent those forms still post and still
        # save.
        QUICK_SWITCH_SCRIPT_SRC,
        # Same unconditional convention: listeners are delegated at document level
        # over every [data-value-control] wrapper (quiet-hours dial, wake-interval
        # slider, more expected), and with the file absent each value is still held
        # by a native input the form posts.
        VALUE_CONTROLS_SCRIPT_SRC,
    )


_FLASH_ROLES = {"status", "alert"}


def flash_banner(message, role="status"):
    """An accent-bordered confirmation block for a save confirmation.

    `role` is validated against `_FLASH_ROLES` (falling back to "status"),
    rendered as the `<div>`'s ARIA role: `role="alert"` (assertive) for a
    save/poll failure, `role="status"` (polite) otherwise, chosen by the
    caller's severity.
    """
    resolved_role = role if role in _FLASH_ROLES else "status"
    return (
        '<div class="banner banner--flash" role="%s">%s</div>'
        % (resolved_role, escape_html(message)))


def anomaly_banner(message, severity="error"):
    """A warning/destructive-bordered block for anomaly flagging.

    `severity` chooses both the CSS class and ARIA role: `"error"` (default)
    renders `banner--anomaly`/`role="alert"`; `"warn"` renders
    `banner--warn`/`role="status"` — a warning-only state announces politely,
    not as an assertive interruption.
    """
    css_class = "banner--anomaly" if severity == "error" else "banner--warn"
    role = "alert" if severity == "error" else "status"
    return (
        '<div class="banner %s" role="%s">%s</div>'
        % (css_class, role, escape_html(message)))


def status_dot(state, label, title=None, visually_hide_label=False):
    """A small coloured status indicator plus an escaped text label.

    `state` maps to one of three fixed CSS class suffixes; an unrecognised
    value falls back to the warning class rather than emitting an arbitrary
    class name.

    `title` is optional; when falsy no `title` attribute is emitted (backward
    compatible with two-positional-argument call sites). When truthy it is
    escaped through escape_html() and added as `title="..."` on the label span.

    `visually_hide_label` is a keyword-with-default, byte-identical-when-falsy
    parameter: only Flights' Corroboration cell passes True, which keeps the
    dot and its accessible name/title but hides the visible word so the column
    can shrink to a dot-only width.
    """
    css_class = _STATUS_DOT_CLASSES.get(state, _DEFAULT_STATUS_DOT_CLASS)
    title_attr = ' title="%s"' % escape_html(title) if title else ""
    label_class = "dot-label visually-hidden" if visually_hide_label else "dot-label"
    # With the label clipped away, a title on that span is unreachable by
    # hover, so it moves onto the dot itself, the only visible element left.
    # Default (label visible) output stays byte-identical.
    dot_title = title_attr if visually_hide_label else ""
    label_title = "" if visually_hide_label else title_attr
    return (
        '<span class="dot %s"%s></span><span class="%s"%s>%s</span>'
        % (css_class, dot_title, label_class, label_title, escape_html(label)))


def stat_tile(caption, content_html, status=None, icon=None, caption_title=None):
    """A status-coloured dashboard card wrapping already-built markup.

    `caption` is escaped here. `content_html` is the caller's own
    already-safe markup, interpolated verbatim with no re-escaping —
    re-encoding it would double-encode already-escaped tags. `status`
    maps to one of three fixed CSS class suffixes; an unrecognised value
    falls back to the neutral class rather than an arbitrary class name.

    `icon` is a whitelisted ICON_IDS id, not markup, passed to
    icon_html() — this function's only other route to raw HTML.
    `caption_title` is an attribute value, escaped through the same
    escape_html() call as `caption`, and added as `title="..."` on the
    caption label.
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


def quick_switch_html(action, return_to, is_on, label_id, state_id, form_id=None):
    """One real `role="switch"` control, shared verbatim by the Frame
    strip's two switches and the Device page's Diagnostic LED, so their
    markup, ARIA and posts cannot drift. `return_to` is written escaped;
    the server validates it against a whitelist before redirecting.

    `is_on` is the saved value: it sets `aria-checked` and the posted
    `state`, always the opposite — with scripts blocked, a switch must
    post the flip, not re-assert its state. `form_id` is for the one
    caller whose switch cannot contain its own form (nested forms are
    invalid HTML): renders the button only, attached via `form=`.
    """
    button_html = (
        '<button type="submit" class="switch" role="switch" aria-checked="%s"'
        ' aria-labelledby="%s" aria-describedby="%s" %s%s>'
        '<span class="switch__track" aria-hidden="true">'
        '<span class="switch__thumb"></span></span>'
        "</button>"
    ) % (
        "true" if is_on else "false",
        escape_html(label_id), escape_html(state_id),
        QUICK_SWITCH_CONTROL_ATTR,
        (' form="%s"' % escape_html(form_id)) if form_id else "",
    )
    if form_id:
        return button_html
    next_state = QUICK_STATE_OFF if is_on else QUICK_STATE_ON
    return (
        '<form method="post" action="%s" class="quick-action__form" data-quick-switch>'
        '<input type="hidden" name="%s" value="%s">'
        '<input type="hidden" name="return_to" value="%s">'
        "%s"
        "</form>"
    ) % (
        escape_html(action),
        QUICK_STATE_FIELD, escape_html(next_state),
        escape_html(return_to),
        button_html,
    )


def quick_switch_state_html(state_id, on_text, off_text, is_on, extra_class=""):
    """The visible state beside a switch: both wordings, server-rendered and
    translated, with exactly one `hidden`.

    Keeps companion/static/quick-switch.js free of user-facing copy: an
    optimistic flip and its rollback are a pure attribute change over text the
    server already produced in the reader's own language. `hidden` is honoured
    with or without scripts, so a scripts-blocked reader sees exactly one
    state word.
    """
    css_class = "text-body quick-action__state"
    if extra_class:
        css_class = css_class + " " + extra_class
    return (
        '<span class="%s" id="%s">'
        '<span %s%s>%s</span>'
        '<span %s%s>%s</span>'
        "</span>"
    ) % (
        css_class, escape_html(state_id),
        QUICK_STATE_ON_ATTR, "" if is_on else " hidden", escape_html(on_text),
        QUICK_STATE_OFF_ATTR, " hidden" if is_on else "", escape_html(off_text),
    )


def _frame_strip_cell_html(extra_class, label_row_html, state_row_html, caption_row_html,
                           extra_attrs=""):
    """One Frame-strip cell wrapper: every cell (both switches and the update
    cell) is the same wrapper with the same three-row structure (label,
    state-plus-control, caption); only `extra_class` and each row's content
    differ. A row with nothing to put in it still emits that row's own empty
    div, never an omitted row, so all three cells' rows line up.

    A harness asserts the three cells' row class attributes are
    byte-identical; the outer wrapper's class list legitimately differs —
    only the switch cells carry the `quick-action`/`quick-action--on/off`
    control-state edge.
    """
    cell_class = "frame-strip__cell"
    if extra_class:
        cell_class = cell_class + " " + extra_class
    # `extra_attrs` carries QUICK_SWITCH_REGION_ATTR on the two switch cells and
    # nothing on the update cell — the region companion/static/quick-switch.js
    # marks pending while its fetch is in flight, and freshness.js's swap
    # already skips when it is.
    return (
        '<div class="%s"%s>'
        '<div class="frame-strip__row frame-strip__row--label">%s</div>'
        '<div class="frame-strip__row frame-strip__row--state">%s</div>'
        '<div class="frame-strip__row frame-strip__row--caption">%s</div>'
        "</div>"
    ) % (cell_class, (" " + extra_attrs) if extra_attrs else "",
         label_row_html, state_row_html, caption_row_html)


def frame_strip_html(ctx, return_to, next_wake_iso=None):
    """The "Frame" strip: one shared body, called identically by
    home_page.render() and config_page.render()'s Display scope, so both
    pages' switches and headline can never disagree. `return_to` is
    written escaped; the server validates it against a route whitelist
    before using it as a redirect target.

    Renders no update cell when no next-wake data is available. Three
    states share one dot vocabulary: due `.dot--ok`, held the neutral
    `.dot--off`, late `.dot--warn`, the warn signal carried by wording
    and dot, never text colour. Both switch forms carry
    `data-quick-switch`, the hook companion/static/dirty-state.js keys
    its leave-guard on — do not delete it as apparently unused. Every
    value crosses escape_html(); every string crosses i18n.t().
    """
    device_cfg = ctx.get("device_config") or {}
    now_value = ctx.get("now")

    # The one state resolution: wake.next_wake_status(), against the same
    # pair every caller already used to compute `next_wake_iso` above —
    # not a second, disagreeing computation.

    # `battery_critical` is the battery-empty latch, read once per
    # request by page_context() — never a second read here. Without it,
    # a parked frame would cross the warn threshold every wake cycle and
    # wrongly announce "late" on a flat battery.
    resolved_next_wake_iso, effective_interval_s, hold_reason = wake.next_wake_status(
        ctx.get("last_checkin_ts"), device_cfg, battery_critical=ctx.get("battery_critical", False))
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

    # The one computed delay sentence, shared verbatim by both switch cells'
    # captions.
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
    display_label_html = '<span class="text-label quick-action__label" id="%s">%s%s</span>' % (
        QUICK_SWITCH_SCREEN_LABEL_ID,
        icon_html("icon-power", size=16, extra_class="quick-action__icon"),
        escape_html(i18n.t(QUICK_ACTION_SCREEN_LABEL)))
    display_state_row_html = (
        quick_switch_state_html(
            QUICK_SWITCH_SCREEN_STATE_ID,
            i18n.t(QUICK_ACTION_ON_TEXT), i18n.t(QUICK_ACTION_OFF_TEXT), is_display_on)
        + quick_switch_html(
            "/quick/display", return_to, is_display_on,
            QUICK_SWITCH_SCREEN_LABEL_ID, QUICK_SWITCH_SCREEN_STATE_ID))
    display_cell_html = _frame_strip_cell_html(
        "quick-action quick-action--%s" % ("on" if is_display_on else "off"),
        display_label_html, display_state_row_html, delay_caption_html,
        extra_attrs=QUICK_SWITCH_REGION_ATTR)

    quiet_enabled = device_cfg.get("quiet_hours_enabled", False)
    is_quiet_on = quiet_enabled is True
    quiet_start = device_cfg.get("quiet_hours_start") or "23:00"
    quiet_end = device_cfg.get("quiet_hours_end") or "07:00"
    quiet_label_html = '<span class="text-label quick-action__label" id="%s">%s%s</span>' % (
        QUICK_SWITCH_QUIET_LABEL_ID,
        icon_html("icon-moon", size=16, extra_class="quick-action__icon"),
        escape_html(i18n.t(QUICK_ACTION_QUIET_LABEL)))
    quiet_state_row_html = (
        quick_switch_state_html(
            QUICK_SWITCH_QUIET_STATE_ID,
            i18n.t(QUICK_ACTION_QUIET_ON_TEMPLATE) % (quiet_start, quiet_end),
            i18n.t(QUICK_ACTION_QUIET_OFF_TEXT), is_quiet_on)
        + quick_switch_html(
            "/quick/quiet-hours", return_to, is_quiet_on,
            QUICK_SWITCH_QUIET_LABEL_ID, QUICK_SWITCH_QUIET_STATE_ID))
    # The one write site for the Quiet hours caption link: appended to a
    # copy of the shared delay sentence, never to `delay_caption_html`
    # itself, which is also the Screen cell's own caption. Always a real
    # `<a href>`, even when `return_to` is already DISPLAY_ROUTE — a
    # same-page fragment link still works with no script.
    quiet_schedule_link_html = '<a class="text-link frame-strip__schedule-link" href="%s#%s">%s</a>' % (
        DISPLAY_ROUTE, _FRAME_QUIET_SCHEDULE_TARGET_ID,
        escape_html(i18n.t(_FRAME_QUIET_SCHEDULE_LINK_TEXT)))
    quiet_caption_html = delay_caption_html + quiet_schedule_link_html
    quiet_cell_html = _frame_strip_cell_html(
        "quick-action quick-action--%s" % ("on" if is_quiet_on else "off"),
        quiet_label_html, quiet_state_row_html, quiet_caption_html,
        extra_attrs=QUICK_SWITCH_REGION_ATTR)

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
        # The clock value is its own `.time-value` element, not baked into the
        # sentence's escaped text: each headline template carries exactly one
        # "%s", so the leading text, the clock span and the trailing text are
        # escaped separately at their own interpolation sites.
        headline_before, headline_after = i18n.t(headline_i18n_source).split("%s", 1)
        headline_text = "%s%s%s" % (
            escape_html(headline_before),
            '<span class="time-value time-value--primary">%s</span>' % escape_html(next_wake_clock),
            escape_html(headline_after),
        )
        update_state_row_html = (
            '<p class="%s"><span class="dot %s"></span>%s</p>'
        ) % (headline_class, dot_class, headline_text)
        # The countdown, beside — never inside — the headline. It is
        # formatting and decides nothing: the instant and state word both
        # come from calls already made above; relative-time.js advances
        # the duration without re-deciding due/held/late.

        # `countdown=True` keeps it a countdown after its instant passes,
        # reading the waiting wording rather than silently becoming an
        # age: "Expected since 14:32 / waiting…", never "2m ago" — a
        # second, quieter lateness claim beside the headline's.
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
    """`base_class + "--ok"/"--warn"/"--error"` for a whitelisted status; the
    empty string for `None` or anything unrecognised.

    `status` is looked up in a fixed three-key whitelist, the same discipline
    status_dot()/stat_tile() use — an unrecognised value can never become an
    arbitrary, attacker-influenceable class name. `base_class` is expected to
    be a module constant or call-site literal, never derived from data.

    The fallback deliberately differs from stat_tile()'s: stat_tile()'s base
    rule already declares a coloured top border that needs some colour, while
    a page-level card's base rule declares a plain hairline, so "no status"
    here means "no modifier, keep the neutral edge" — the absence of a
    coloured edge is itself the "no verdict" signal.
    """
    suffix = _CARD_STATUS_SUFFIXES.get(status)
    return base_class + suffix if suffix else ""


def status_row(label, verdict, detail, state):
    """`<div class="status-row status-row--ok|warn|error">`: one shared row
    primitive (dot + optional label + verdict + detail), used by Home's
    status card and the Calendar status row alike. `label` falsy omits
    the `<span>` entirely, not just its text.

    `state` maps through the same `_STATUS_DOT_CLASSES` fallback
    status_dot()/stat_tile() use, and through card_status_class()'s
    whitelist for the outer modifier — never a bare interpolation, so an
    unrecognised value degrades to the default dot rather than an
    attacker-influenceable class name. `verdict`/`detail`/`label` are
    escaped here; the caller translates them through i18n.t() first.
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
    """A `<div class="section-intro">` wrapping one id-anchored `<h2>` plus a
    muted one-sentence description on the same baseline.

    Shared across page modules since `companion/pages/__init__.py` forbids
    one page module importing another. The `<h2 id="..." class="text-heading">`
    keeps the exact attribute order and escape_html() call
    health_page.py's structural checks pin — this builder must never drift
    from that shape.

    `section_id` is escaped too, like every other string this file
    interpolates into an attribute or text node: every current call site
    passes a fixed module constant, but this helper is shared going forward
    and must not be the one place a caller is trusted.
    """
    return (
        '<div class="section-intro">'
        '<h2 id="%s" class="text-heading">%s</h2>'
        '<p class="text-label section-caption">%s</p>'
        "</div>"
    ) % (escape_html(section_id), escape_html(heading), escape_html(description))


def empty_state(heading, body, compact=False):
    """The escaped two-part empty-state block used for the flight log,
    the gallery, and the unresolved-prefix list.

    `compact` falsy is byte-identical to this function's pre-existing
    output. Why it exists: an empty state inside a `.stat-tile` put a
    22px serif heading inside a card whose own caption is 12px, an
    inverted hierarchy. Compact drops the heading to the Emphasis role
    and the body to the label size, matching a filled tile's verdict and
    detail rows through its own class names, never by borrowing
    `.widget-verdict`/`.widget-detail` — an empty state's heading is not
    a verdict.
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
    """The shared page-header component every authenticated page's
    render() opens with, in place of a bare <h1>. This exact signature
    and parameter order is called across many page modules — do not
    rename or reorder.

    `title`/`purpose` are escaped here. `freshness_html`/`action_html`,
    when truthy, are the caller's own already-safe markup, interpolated
    verbatim with no escape_html() call — callers must escape any
    user-influenced data before passing it through either parameter.

    Blocks concatenate title, then freshness/action, then purpose last.
    The returned string ends with FLASH_SLOT_MARKER, which page_shell()
    is the only consumer of.
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
    Returns empty_state()'s output instead of an empty table when `rows`
    is empty. `mono_columns` names zero-based indices that get the
    monospace class.
    `raw_columns` names indices whose value is already-safe, pre-built
    HTML, interpolated without escape_html() — only place the output of
    a builder that already escapes internally, never a bare string: that
    reopens the XSS-shaped defect this module's escaping discipline
    otherwise closes. `desc_columns` names indices that get the
    description-role class; all three name sets are orthogonal.

    `prose` releases a table from the shared no-wrap/no-crop floor, for
    full-sentence columns. `modifier` appends one `data-table--<modifier>`
    class; pass the bare stem, never the full class name.
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
            # mono is joined first so a mono-only cell's attribute string stays
            # byte-identical to the pre-desc_columns output; test_view_pages.py pins
            # that shape.
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
