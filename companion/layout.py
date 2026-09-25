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
# getElementById()/classList. Duplicated here rather than imported — a
# Python module cannot import a JS file — so a drift between the two
# silently stops the menu opening, with no automated signal from either
# file in isolation. A DOM-contract guard reads the JS source, the
# stylesheet and the rendered page, and requires all three to agree.
NAV_TOGGLE_ID = "site-nav-toggle"
MOBILE_NAV_ID = "mobile-nav"
MOBILE_NAV_OPEN_CLASS = "mobile-nav--open"

# The fixed accessible name for the hamburger toggle button. State is
# communicated entirely through aria-expanded — the correct ARIA
# disclosure pattern; swapping this label to a close verb on open would
# change the announced name under the user mid-interaction. Do not vary it
# by state.
# Renamed from "Open menu": the panel this toggle controls no longer
# holds a menu of pages — the bottom tab bar owns destinations now, and
# what remains behind the hamburger is the state reminder plus language,
# theme and Sign out.
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
# contract as above. Registered on the shell because its known consumers
# (quiet-hours dial, wake-interval slider) live on different settings
# pages and the set is expected to grow; its guard returns before
# touching a page with no [data-value-control] wrapper.
#
# This is the only script the value-controls feature needs: five
# controls share one clamp/round/keyboard model rather than duplicating
# it per control.
VALUE_CONTROLS_SCRIPT_SRC = "/static/value-controls.js"

# The registration seam value-controls.js reads, defined here so a page
# module never types the attribute name and a rename cannot drift from
# the script (a harness asserts the served script body names every one
# of them). A control opts in entirely by attribute, so there is no
# per-control JavaScript.
#
# The wrapper is a LAYER, never the control: the value is always held by
# the native <input>/<select> named by VALUE_CONTROL_FIELD_ATTR, which
# the server renders unconditionally.
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
# native input holds. Absent, the number is written straight in, for a
# numeric input. VALUE_CONTROL_FORMAT_CLOCK makes the script read/write
# "HH:MM" instead: an <input type="time"> silently discards anything
# else, so a minute count written in empties the field the form posts,
# with no error anywhere.
VALUE_CONTROL_FORMAT_ATTR = "data-value-format"
VALUE_CONTROL_FORMAT_CLOCK = "clock"

# THE MIRROR is a native control inside the wrapper that carries the
# same value as the field and posts nothing — an `<input type="range">`
# with no `name`, so it cannot submit.
#
# A native range input already has the keyboard model this script
# implements (arrows, Page, Home/End), native aria-valuenow, native
# touch dragging and a platform-native thumb. role="slider" must NOT be
# added — the element already has those semantics, and a redundant role
# is a double-role error.
#
# A wrapper carrying a mirror gets no preventDefault and no steering
# from this file's own gesture handlers: preventDefault() on a
# pointerdown over a native range cancels the browser's own thumb drag,
# and a keydown handler that both prevents default and steps the value
# would move the control twice per arrow press. The script's job with a
# mirror is only to sync.
VALUE_CONTROL_INPUT_ATTR = "data-value-input"

# A READOUT is an element whose whole text is a sentence about the
# value, rendered by the server and rewritten by the script as the
# value moves. It carries the field's own name so it can live anywhere
# in the document — it is not gated, since it must be correct with
# scripts blocked.
#
# The sentence is server-rendered and already translated, like
# VALUE_CONTROL_TEXT_ATTR above: no copy lives in the script, so a
# French reader can never be dropped into English by moving a slider.
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

# The painted position has no constant here, deliberately: it travels
# on the `--value-fraction` custom property, written by the server once
# and rewritten by value-controls.js on every steer. A CSS custom
# property's name begins with two hyphens, which
# companion/test_i18n.py's D-05 scan reads as untranslated user-facing
# copy — measured, and it fails. The name lives inline in the one
# markup template that emits it, in value-controls.js's own
# FRACTION_PROPERTY, and in style.css; a harness pins all three to one
# string.

# The class companion/static/style.css hides by default and reveals
# under `.js`. Defined here so a page module never types it, and pinned
# by a harness against both the stylesheet and the no-JS control
# contract's own registry.
#
# The class goes on the gated element itself, never on an ancestor:
# "carries the class" is checkable from rendered markup without parsing
# the whole tree.
JS_GATE_CLASS = "js-gate"

UI_THEME_CHOICES = ("auto", "light", "dark")

# The quick-action form protocol, shared by companion/app.py and
# config_page.py — a page module may never import another page module,
# so this lives in the shared layer instead.
QUICK_STATE_FIELD = "state"
QUICK_STATE_ON = "on"
QUICK_STATE_OFF = "off"

# The eleven QUICK_ACTION_* constants, moved here byte-identical from
# config_page.py: frame_strip_html() below is the one write site for
# both switch cells, and home_page.py needs these from a shared module
# too. Every English value is unchanged, so every French catalogue
# entry in companion/i18n_fr/display.py keeps resolving — the
# catalogue is keyed by English string, not by which module defines the
# constant.
QUICK_ACTION_SCREEN_LABEL = "Screen"
QUICK_ACTION_ON_TEXT = "On"
QUICK_ACTION_OFF_TEXT = "Off"
QUICK_ACTION_SWITCH_ON_BUTTON = "Switch on"
QUICK_ACTION_SWITCH_OFF_BUTTON = "Switch off"
QUICK_ACTION_QUIET_LABEL = "Quiet hours"
QUICK_ACTION_QUIET_ON_TEMPLATE = "On — %s to %s"
QUICK_ACTION_QUIET_OFF_TEXT = "Off"
# These four action wordings are no longer rendered markup: they used
# to be the switch button's own visible text ("Switch off"/"Éteindre"),
# which a role="switch" control may not be named by — a name that reads
# as an action contradicts aria-checked. The button is now named by the
# setting via aria-labelledby; these constants survive only as names
# test_status_pages.py asserts are no longer rendered.
QUICK_ACTION_QUIET_TURN_ON_BUTTON = "Turn on"
QUICK_ACTION_QUIET_TURN_OFF_BUTTON = "Turn off"

# THE NO-JS FLOOR HERE IS STRUCTURAL, NOT ADDITIVE. Each switch IS the
# <form> that already shipped: a real POST to its own /quick/* route
# with a `state` field and a `return_to` hidden field the server
# whitelists by membership. companion/static/quick-switch.js intercepts
# the submit of a control that already works; remove the script and
# the button still posts, the server still saves. `role="switch"` and
# `aria-checked` are rendered here, from the saved value, so the
# accessible state is correct on a scripts-blocked page too.
# The attribute the script marks its own unconfirmed control with —
# freshness.js's swap already skips a region carrying or containing
# it. Not a "data-quick-switch-*" name: `data-quick-switch` is the
# form's own handshake attribute and a shipped check counts its
# occurrences, so a child attribute containing it as a substring would
# inflate that count.
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
# FLASH_MESSAGES[FLASH_KEY_QUICK_FAILED] — the same generic sentence
# this app already shows when a quick action fails, so neither reader
# is told a status code or anything else the server knows. layout.py
# may not import companion/app.py, so the English literal is
# duplicated here, keyed by English string in the French catalogue
# like the QUICK_ACTION_* constants above.
QUICK_SWITCH_FAILED_TEXT = "Couldn't change that — please try again."
QUICK_SWITCH_FAILED_ATTR = "data-quick-failed-text"
QUICK_TOAST_ATTR = "data-quick-toast"
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

# 27-08-PLAN.md Task 2 (CFG-69): the quiet cell's caption link, appended
# to the SAME `delay_caption_html` slot the switch cells already share —
# never a new slot, never a per-page fork (D-23; see frame_strip_html()
# below). The link text is scanner-visible for the identical D-08 reason
# the six _FRAME_*_TEXT constants above are: a local, byte-identical copy
# rather than a cross-module attribute read.
_FRAME_QUIET_SCHEDULE_LINK_TEXT = "Change the schedule"
# Byte-identical to companion/pages/config_page.py's own
# QUIET_HOURS_GROUP_HEADING_ID (27-08-PLAN.md Task 1) — duplicated, never
# imported, for the same "a page module may never import another page
# module" reason QUICK_ACTION_QUIET_LABEL and its ten siblings above are
# local copies rather than a cross-module read. The two constants must
# be kept byte-identical by hand; a harness proves it (27-08-PLAN.md
# Task 2's own check).
_FRAME_QUIET_SCHEDULE_TARGET_ID = "quiet-hours-group-heading"

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
# `display: none` still lets every <use href="#icon-..."> reference
# below resolve correctly — this sprite must never move inside a
# conditionally rendered region: a <use> referencing a symbol that isn't
# in the DOM at all (not merely hidden) resolves to nothing.
#
# Each symbol carries fill="none"/stroke="currentColor" so a single CSS
# `color` property drives the whole glyph, with no second colour mapping
# to keep in sync. The four tile icons use a 20x20 viewBox; the hamburger
# uses 24x24. Every glyph is built from plain <path>/<line>/<rect>/
# <circle> primitives — legible outline shapes, not detailed
# illustration.
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
    """A `<svg>` referencing one symbol from ICON_DEFS_HTML via `<use>`, or the
    empty string when `icon_id` is not a member of ICON_IDS.

    This is a whitelist, not a sanitiser: `icon_id` becomes a `#`-prefixed
    fragment identifier inside a `<use href="...">` attribute, and an id
    that reached the output unchecked would be an attacker-influenceable
    fragment reference. An unrecognised id fails visibly-but-safely — a
    missing icon, not a dangling or injectable reference.

    The explicit `width`/`height` attributes are belt-and-braces against
    companion/static/style.css's `.icon` sizing rule being lost or
    overridden: an `<svg>` with neither renders at the SVG default 300x150.

    `aria-hidden="true"` is unconditional: every icon in this app sits
    beside its own visible text label, so the icon is decorative and
    announcing it would duplicate the label.
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

    This function is FORMATTING, never a verdict: it says how long remains
    until an instant somebody else computed, never "late"/"held"/"due" —
    those words are frame_state's and stay server-rendered.

    A `seconds_ahead` that has already elapsed resolves to the zero bucket
    via _age_bucket()'s own clamp, never a negative number or a past-tense
    string.

    `lang` is the same trailing keyword every sibling here carries. French
    collapses the sub-minute bucket the way the past form does, into "in a
    moment"; both strings live in companion/i18n_fr/health.py, read through
    i18n.t_lang() and never duplicated as a module literal.
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
    its unit (D-09) is added; the ladder and the French unit suffixes are
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
# client-side, in the reader's own language. Rendered onto <body> by
# page_shell() and read back with getAttribute() — several of these
# elements sit inside freshness.js's swap targets, and <body> is never
# swapped.
#
# One complete wording per bucket per direction, so the script carries no
# language logic: it substitutes a quantity into a string and stops. "#"
# is the quantity's place, not "%s": these strings reach the browser as
# attribute values, and companion/test_i18n.py's Check 3 scans every
# French render for a stray "%s"/"%d"/"{}" — "#" is not one.
#
# These are not a second ladder: they are the same ladder's own output
# with the number lifted out, and test_companion_app.py asserts each
# wording, filled with the quantity _age_bucket() picks, equals
# relative_age_text()/relative_future_text()'s own return value for
# every bucket, in both languages.
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
# with the number lifted back out, so the script carries no language
# logic.
#
# One complete wording per bucket, reusing RELATIVE_QUANTITY_MARK ("#"):
# these strings reach the browser as attribute values, and
# companion/test_i18n.py's Check 3 scans every French render for a stray
# "%s"/"%d"/"{}"; "#" is not one. The French U+00A0 between number and
# unit lives in the i18n_fr catalogue entry, not in this module.
#
# All four buckets ship even though a quiet window's arithmetic can
# never reach "d": "s" is reachable (a zero-length window is real), and
# a ladder with a hole in it is one somebody falls through the day a
# caller changes.
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
REFRESH_PAGE_FLIGHTS = nav_slug(FLIGHTS_ROUTE)

# 23-08-PLAN.md Task 1 (D7/CFG-37): the two cross-file literals the
# new-row highlight is built on, duplicated into
# companion/static/freshness.js rather than imported — a static asset is
# not a Python module — and pinned equal by
# companion/test_status_pages.py, exactly like REFRESH_PENDING_ATTR
# above.
#
# REFRESH_ROW_ID_ATTR carries a stable identity for the EVENT a row
# describes, and the word "event" is the whole of it. The Flights table
# already numbers its detail rows `flight-detail-{n}` and groups its two
# representations by `data-filter-group={n}`, but both of those are the
# row's POSITION IN THIS RENDER — they pair a summary row with its own
# detail row, which is all they were ever for. A highlight keyed to a
# position would light up every row below an insertion the moment one
# arrived at the top, which is the exact opposite of the signal D7 asks
# for. companion/pages/history_page.py renders this from the
# runway_events row's own primary key.
REFRESH_ROW_ID_ATTR = "data-flight-id"
# The class freshness.js adds to a row whose identity was NOT in the set
# it knew before the swap. One-shot by construction: nothing removes it,
# because the node it lands on was itself just inserted and the next
# swap replaces that node entirely.
REFRESH_NEW_ROW_CLASS = "is-new-row"

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
# FLIGHTS (23-08-PLAN.md Task 1, D7/CFG-37): the two renderings of the
# list — the phone `<ul class="history-cards">` and the desktop
# `.data-table-wrap` — plus the live count and the freshness line. Both
# renderings, not whichever the current breakpoint shows: the CSS
# sibling toggle decides which is visible, both are always in the DOM,
# and a swap that replaced only one would leave the other showing an
# older list the moment a window was resized.
#
# WHAT IS DELIBERATELY OUT, and why it is the interesting half.
# companion/static/list-filter.js resolves FOUR elements exactly once,
# at load — the `[data-filter-input]` itself, `[data-filter-clear]`,
# `[data-filter-empty]` and every `[data-filter-set]` — and holds those
# references for the life of the page. Replacing any one of them detaches
# the node the script is still writing to, so the filter goes silently
# dead and an in-progress query is discarded with it. That is the same
# trade Health's entry above records for the sparkline and the registry
# card, and it is why `[data-filter-count]` IS here while its three
# siblings are not: the count is the one the script now looks up fresh
# on every keystroke, precisely so it could join this list.
#
# The rows themselves were never captured — list-filter.js queries
# `[data-filter-text]` fresh on every input event, for its own
# breakpoint reason — so swapping them costs that script nothing. What
# a swap DOES cost is the filter's applied state, since the server
# renders the list unfiltered: list-filter.js re-runs its one
# applyFilter() when the loop announces a swap, which is what keeps a
# typed query applied across a refresh.
#
# Deliberately NOT nested: no entry here contains another.
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
    REFRESH_PAGE_FLIGHTS: (
        ".page-header__freshness",
        "ul.history-cards",
        ".data-table-wrap",
        "[data-filter-count]",
        # 29-03-PLAN.md Task 1 (CFG-83): the Show-more nav's own `href`
        # advances by one page on every render (history_page.py's
        # `_show_more_html()`), so a background refresh that skipped
        # this region would leave a STALE href on screen after the
        # first swap — clicking it would silently re-request the page
        # the visitor is already on instead of the next one. Declaring
        # it here is also why `_show_more_html()` renders an EMPTY
        # `<nav>` rather than nothing at all when there is no more to
        # show: `test_view_pages.py`'s registry-witness check requires
        # every declared region to be findable in every rendered page,
        # including its single-row fixture where nothing remains.
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
    #
    # No ARIA role on the pill: a live region announces on content mutation, not
    # on visibility, and the page load is already announced as a navigation.
    # Known gap: a reload while a screen reader has focus on the body resets its
    # virtual cursor.
    pill_html = (
        '<span class="refresh-pill" data-refresh-pill data-loaded-at="%s" hidden>%s%s</span>'
        % (escape_html(now), icon_html("icon-refresh"), escape_html(i18n.t(REFRESH_PILL_TEXT))))
    # Server-rendered static and neutral; the breathing motion is a class
    # freshness.js adds/removes, so a scripts-blocked page shows a still dot
    # beside a static age.
    # `.dot--off` carries no verdict colour — a loop's live/paused state is not a
    # device verdict — and is aria-hidden since the Paused/Reconnecting badge
    # beside it already announces the real state.
    dot_html = (
        '<span class="dot dot--off" %s aria-hidden="true"></span>'
        % REFRESH_LIVE_DOT_ATTR)
    # The clock is local_clock_text() with `now_parsed` set to the same instant,
    # forcing its same-day "HH:MM" branch. The full Europe/Paris timestamp stays
    # on the span's `title` via _full_local_timestamp_text(); `data-loaded-at` on
    # the pill carries the machine-readable instant freshness.js actually reads —
    # the `title` is tooltip only.
    #
    # `.time-value`, not `.mono`: monospace is reserved for identifiers (callsign,
    # ICAO24 hex), not a wall-clock time. `.time-value` keeps tabular numerals so
    # the digits hold their column as the clock ticks.
    _now_parsed = parse_iso(now)
    _clock_text = (
        local_clock_text(_now_parsed, now_parsed=_now_parsed)
        if _now_parsed is not None else now)
    clock_html = (
        '<span class="time-value" data-refresh-clock title="%s">%s</span>'
        % (escape_html(full_local_timestamp_text(now)),
           relative_time_html(now, now, static_text=_clock_text)))
    # One block-level wrapper for prefix+clock+pill: `.page-header` is a block
    # box, and a bare inline pill span forces an anonymous block box, producing an
    # extra gap. The descendant selector `.page-header .refresh-pill` still
    # matches through the wrapper.
    #
    # This element is a REFRESH_SWAP_SELECTORS_BY_PAGE entry: freshness.js
    # replaces it wholesale, so a render-time value is honest only until the next
    # swap.
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
    # FLASH_SLOT_MARKER as a literal splice point directly below the header. A
    # page built on page_header() gets the marker replaced and `flash_html`
    # cleared; a page without page_header() (login, 404) keeps its old
    # before-body slot untouched. The unconditional second replace() below strips
    # any leftover marker so it never reaches the browser.
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

    # <aside> precedes <header> in source order: at desktop width, where CSS
    # hides the header, a keyboard user tabs into the sidebar nav first, with no
    # invisible stop before it. Both nav copies stay in the DOM always; only the
    # 960px CSS media query decides which is visible (no inline styles, no hidden
    # attribute, no ARIA hint), so exactly one navigation landmark is ever
    # exposed to the accessibility tree.
    #
    # ICON_DEFS_HTML is emitted once per document, right after <body>: the
    # sprite's one definition site. The theme form renders once in the sidebar
    # and once in the hamburger dropdown (from the same theme_form_html string),
    # never a third time in the header.
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
        # The tab bar sits outside and after .dashboard-shell, a sibling rather than
        # a descendant of the scrolled content column, so its `position: fixed` box
        # is not nested inside the shell's own stacking/overflow context. `""` on a
        # page with no bar, emitting a bare newline like the flash slot does.
        "%s\n"
        # The optimistic switch's failure announcement: rendered empty, once per
        # document, never hidden. A live region added at announce time is one screen
        # readers often miss, so it exists from load and only its text changes;
        # role="alert" implies aria-live="assertive" for a failure the user is
        # waiting on.
        #
        # The one script-only surface here, and additive: with no script there is no
        # fetch, so there is no failure to report beyond the server's own flash on
        # the page a 303 lands on.
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

    `caption` is escaped here. `content_html` is the caller's own already-safe
    markup and is interpolated verbatim with no re-escaping — re-encoding it
    here would double-encode already-escaped tags. `status` maps to one of
    three fixed CSS class suffixes; an unrecognised value falls back to the
    neutral class rather than emitting an arbitrary class name.

    `icon` is a whitelisted id from ICON_IDS, not markup, passed to icon_html()
    — this function's only route to raw HTML besides `content_html`. When
    falsy or unknown, the caption renders exactly as before this parameter
    existed.

    `caption_title` is an attribute value, not markup: escaped through the
    same escape_html() call as `caption`, and added as `title="..."` on the
    caption label — a household reader sees the plain label, the technical
    term stays one hover away.
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
    """One real `role="switch"` control, shared verbatim by the Frame strip's
    Screen and Quiet hours switches and the Device page's Diagnostic LED, so
    their markup, ARIA and posts cannot drift apart.

    `action`/`return_to` are written escaped into the form; the server
    validates `return_to` by membership against a whitelist before using it as
    a redirect — this function has no opinion on validity.

    `is_on` is the SAVED value: it sets `aria-checked` and the posted `state`,
    always the OPPOSITE of `is_on` — with scripts blocked, a switch must post
    the flip, not re-assert its current state. The accessible name is the
    setting (`label_id`); `state_id` describes the current state and may be a
    space-separated id list. Track and thumb are `aria-hidden` presentational.

    `form_id` is for the one caller whose switch cannot contain its own form
    (nested forms are invalid HTML): this renders the button only, attached
    via `form=`, with the caller rendering the matching empty `<form>` as a
    sibling.
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
    pages' switches and next-update headline can never disagree.

    `device_config` fallback defaults are duplicated here rather than imported
    (this module does not import from server/). `return_to` is written
    escaped; the server validates it against a route whitelist before using it
    as a redirect target.

    Renders no update cell when no next-wake data is available. Three states
    share one dot vocabulary: due `.dot--ok`, held the neutral `.dot--off`,
    late `.dot--warn`, the warn signal carried by wording and dot, never text
    colour.

    Both switch forms carry `data-quick-switch`, the hook
    companion/static/dirty-state.js keys its leave-guard on — do not delete it
    as apparently unused.

    Every interpolated value crosses escape_html(); every string crosses
    i18n.t().
    """
    device_cfg = ctx.get("device_config") or {}
    now_value = ctx.get("now")

    # The one state resolution: wake.next_wake_status(), against the same
    # (last_checkin_ts, device_config) pair every caller already used to
    # compute `next_wake_iso` above — calling it again here is not a second,
    # disagreeing computation (see this function's own docstring).
    #
    # `battery_critical` is the battery-empty latch, read once per request by
    # page_context() — never a second read of poll_state.json here. Without
    # it, a parked frame would cross the warn threshold every wake cycle and
    # the strip would wrongly announce "late" for a frame that is deliberately
    # resting on a flat battery.
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
    # The one write site for the Quiet hours caption link: appended to a COPY
    # of the shared delay sentence, never to `delay_caption_html` itself, which
    # is also the Screen cell's own caption. Always a real `<a href>`, including
    # when `return_to` is already DISPLAY_ROUTE — a same-page fragment link
    # still works with no script.
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
        # The countdown, in the cell's caption row beside — never inside — the
        # headline. It is formatting and decides nothing: the instant comes from
        # wake.next_wake_status() and the state word from frame_state.resolve_state(),
        # both already computed above. companion/static/relative-time.js advances the
        # duration without ever re-deciding whether the frame is due, held or late —
        # computing lateness in two places is what caused a prior false alarm.
        #
        # `countdown=True` keeps it a countdown after its instant passes, reading
        # the translated waiting wording rather than silently turning into an age —
        # a late frame reads "Expected since 14:32 / waiting…", never "2m ago",
        # which would be a second, quieter lateness claim beside the headline's.
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
    primitive (dot + optional label + verdict + detail), used by Home's status
    card and the Calendar status row alike.

    `label` is optional: a falsy value omits the `<span>` entirely, not just
    its text. `verdict` and `detail` must carry two different pieces of
    information — a state word versus a freshness/detail clause — never the
    same sentence rendered twice.

    `state` maps through the same `_STATUS_DOT_CLASSES` fallback
    status_dot()/stat_tile() use for the dot, and through
    card_status_class()'s whitelist for the outer modifier — never a bare
    interpolation of an unvalidated `state`: an unrecognised value degrades to
    the default dot and no outer modifier, rather than an
    attacker-influenceable class name. `verdict`, `detail` and `label` are all
    escaped here.

    The caller is responsible for translating `label`/`verdict`/`detail`
    through i18n.t() before calling this; status_row() itself calls no t().
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
    """The escaped two-part empty-state block used for the flight log, the
    gallery, and the unresolved-prefix list.

    `compact` is a keyword-with-default whose falsy value is byte-identical to
    this function's pre-existing output. Why it exists: an empty state
    rendered inside a `.stat-tile` put a 22px serif heading inside a card
    whose own caption is 12px, an inverted type hierarchy. The compact form
    drops the heading to the Emphasis role (16px sans semibold) and the body
    to the label size — reusing the established bottom type rung rather than
    inventing a new tier.

    Those are the same two treatments a filled tile's verdict and detail rows
    wear, so a compact empty state occupies exactly those slots' rhythm. It
    reaches them through its own class names rather than borrowing
    `.widget-verdict`/`.widget-detail`: an empty state's heading is not a
    verdict, and a pinned test asserts the Resolution-rate tile carries no
    `.widget-verdict` anywhere.
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
    """The shared page-header component every authenticated page's render()
    opens with, in place of a bare <h1>.

    THIS SIGNATURE IS A CONTRACT: page_header(title, purpose=None,
    freshness_html=None, action_html=None) is called by this exact name and
    parameter order across many page modules — do not rename or reorder these
    parameters.

    `title` is escaped and wrapped in `<h1 class="page-title">`. `purpose`,
    when truthy, is escaped and rendered as `<p class="page-header__purpose
    text-body">`.

    `freshness_html` and `action_html`, when truthy, are the caller's own
    already-safe markup, interpolated verbatim with no escape_html() call —
    re-encoding either here would double-encode already-escaped tags. Callers
    are responsible for escaping any user-influenced data before passing it
    through either parameter.

    The blocks are concatenated title, then freshness/action, then purpose
    last; this ordering is separate from the signature contract above and may
    change independently.

    The returned string ends with FLASH_SLOT_MARKER, appended after the
    closing `</div>` — not a signature change. page_shell() is the marker's
    only consumer.
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

    `mono_columns` names zero-based column indices that get the monospace
    class (callsigns, hex codes, timestamps). Returns empty_state()'s output
    instead of an empty table when `rows` is empty.

    `raw_columns` names column indices whose cell value is ALREADY-SAFE,
    pre-built HTML, interpolated without a call to escape_html() — every other
    column is escaped as before. Only place the output of a builder that
    already escapes internally (e.g. concise_timestamp_html(), status_dot())
    in a raw_columns cell, never a bare string: doing so reopens an
    XSS-shaped defect this module's single-escaping-choke-point discipline
    otherwise closes.

    `desc_columns` names column indices that get the description-role class
    (`desc`), for prose columns rendered in the muted secondary strength.
    `mono_columns`, `raw_columns` and `desc_columns` are mutually orthogonal
    and may safely name the same index.

    `prose` adds the modifier class `data-table--prose`, releasing a table
    from the shared no-wrap/no-crop floor for columns holding full sentences
    rather than short values.

    `modifier` appends one additional `data-table--<modifier>` class; pass the
    bare stem ("readings"), never the full class name — the `data-table--`
    prefix is added here so every modifier is spelled the same way in the
    stylesheet.
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
