"""companion/ui_base.py: the foundation layer of the companion service's page
shell and component library — module-wide constants (site title, local
timezone, nav route/label tables, icon sprite, quick-action and frame-strip
wording, status-dot/stat-tile class tables), plus the three
zero-dependency-on-a-sibling-ui-module helpers (`nav_slug`, `icon_html`,
`escape_html`) every other `companion/ui_*.py` module and page module builds
on. stdlib `html` and `zoneinfo` only, plus `companion.frame_state` for the
frame-strip dot-class table and `companion.i18n` for the stable message IDs
the nav/quick-action/frame-strip wording below declares; no import from
another `companion/ui_*.py` module, `companion.app`, or a page module.

`escape_html()` is defined once, here; every companion/pages/*.py module
must import and use it rather than the stdlib `html` module directly, or
build markup without going through this helper. One helper makes the
escaping obligation auditable with a single grep across the package.
"""
import html
from zoneinfo import ZoneInfo

# companion.frame_state is a shared, page-independent module; importing it
# carries no cycle. Its STATE_DUE/STATE_HELD/STATE_LATE constants back
# _FRAME_DOT_CLASS_BY_STATE below, the dot-class table companion/
# ui_components.py's frame_strip_html() reads.
import companion.frame_state as frame_state
import companion.i18n as i18n

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
# The Update page: a third Advanced-group destination alongside Health
# and Device, for reviewing and installing firmware releases.
UPDATE_ROUTE = "/update"

ADVANCED_GROUP_LABEL = i18n.msg("nav.advanced", "Advanced")

# The seven nav-tab labels, each a Message so its French lookup survives a
# reword of the English below; declared once here since NAV_GROUPS/
# NAV_TABS are the one source of these labels for every renderer.
_NAV_LABEL_HOME = i18n.msg("nav.home", "Home")
_NAV_LABEL_DISPLAY = i18n.msg("nav.display", "Display")
_NAV_LABEL_FLIGHTS = i18n.msg("nav.flights", "Flights")
_NAV_LABEL_AIRLINES = i18n.msg("nav.airlines", "Airlines")
_NAV_LABEL_HEALTH = i18n.msg("nav.health", "Health")
_NAV_LABEL_DEVICE = i18n.msg("nav.device", "Device")
_NAV_LABEL_UPDATE = i18n.msg("nav.update", "Update")

NAV_GROUPS = (
    ("", (
        (HOME_ROUTE, _NAV_LABEL_HOME),
        (DISPLAY_ROUTE, _NAV_LABEL_DISPLAY),
        (FLIGHTS_ROUTE, _NAV_LABEL_FLIGHTS),
        (AIRLINES_ROUTE, _NAV_LABEL_AIRLINES),
    )),
    (ADVANCED_GROUP_LABEL, (
        (HEALTH_ROUTE, _NAV_LABEL_HEALTH),
        (DEVICE_ROUTE, _NAV_LABEL_DEVICE),
        (UPDATE_ROUTE, _NAV_LABEL_UPDATE),
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
NAV_TOGGLE_LABEL = i18n.msg("nav.account_and_preferences", "Account and preferences")

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

# Must equal companion/app.py's TOAST_SCRIPT_ROUTE exactly, same contract
# as above: dismiss and auto-hide for every toast.
TOAST_SCRIPT_SRC = "/static/toast.js"

# Must equal companion/app.py's POLL_COOLDOWN_SCRIPT_ROUTE exactly, same
# contract as above.
POLL_COOLDOWN_SCRIPT_SRC = "/static/poll-cooldown.js"

# Must equal companion/app.py's CONFIRM_SUBMIT_SCRIPT_ROUTE exactly, same
# contract as above.
CONFIRM_SUBMIT_SCRIPT_SRC = "/static/confirm-submit.js"

# Must equal companion/app.py's THEME_PREVIEW_SCRIPT_ROUTE exactly, same
# contract as above.
THEME_PREVIEW_SCRIPT_SRC = "/static/theme-preview.js"

# Must equal companion/app.py's AIRLINE_TYPES_SCRIPT_ROUTE exactly, same
# contract as above.
AIRLINE_TYPES_SCRIPT_SRC = "/static/airline-types.js"

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
# it is looked up by stable id (or, for the four retired button
# wordings below that reach no i18n.t() call, kept as plain text).
#
# Each Message's id names the i18n_fr module that actually owns its
# French translation today (health.py for "Screen", display.py for the
# rest) — none of them is common.py/nav.py, and that catalogue stays
# untouched by this plan; the id-with-no-BY_ID-entry fallback keeps
# every one of these resolving until a later plan migrates that module.
QUICK_ACTION_SCREEN_LABEL = i18n.msg("health.screen", "Screen")
QUICK_ACTION_ON_TEXT = i18n.msg("display.on", "On")
QUICK_ACTION_OFF_TEXT = i18n.msg("display.off", "Off")
QUICK_ACTION_SWITCH_ON_BUTTON = "Switch on"
QUICK_ACTION_SWITCH_OFF_BUTTON = "Switch off"
QUICK_ACTION_QUIET_LABEL = i18n.msg("display.quiet_hours", "Quiet hours")
QUICK_ACTION_QUIET_ON_TEMPLATE = i18n.msg("display.on_to", "On — %s to %s")
# Same id as QUICK_ACTION_OFF_TEXT above: same English, same French
# translation, and msg() is idempotent for a repeat id/English pair.
QUICK_ACTION_QUIET_OFF_TEXT = i18n.msg("display.off", "Off")
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
# like the QUICK_ACTION_* constants above. Same id as the FLASH_MESSAGES
# entry app.py will declare in its own migration.
QUICK_SWITCH_FAILED_TEXT = i18n.msg(
    "common.couldn_t_change_that_please_try_again",
    "Couldn't change that — please try again.")
# Hooks on Health's two docked state toasts, named once so the page that
# renders them and the refresh registry that swaps them agree.
HEALTH_ANOMALY_CLASS = "health-anomaly"
HEALTH_SOURCE_FAULT_CLASS = "health-source-fault"
# The empty live region quick-switch.js announces a failure in, and the
# server-rendered, translated error toast it clones into that region.
QUICK_TOAST_ATTR = "data-quick-toast"
QUICK_TOAST_TEMPLATE_ATTR = "data-quick-toast-template"
# No longer used by frame_strip_html(): the one computed delay
# sentence below (frame_state.py's DELAY_DUE/DELAY_HELD/DELAY_UNKNOWN)
# replaces this old static caption. It survives as DELAY_UNKNOWN's own
# wording (_FRAME_DELAY_UNKNOWN_TEXT below) and stays defined because
# config_page.py still references it directly. Its id/English is owned
# by display.py, which stays untouched by this plan.
QUICK_ACTION_APPLIES_SENTENCE = i18n.msg(
    "display.applies_the_next_time_the_frame_wakes_up",
    "Applies the next time the frame wakes up.")

# The strip's own heading; resolves through a stable id so layout code never
# imports a page module.
FRAME_STRIP_HEADING = i18n.msg("home.frame", "Frame")

# frame_state.py's HEADLINE_DUE/HEADLINE_HELD/HEADLINE_LATE are the
# one canonical registry of this copy; frame_strip_html() below calls
# frame_state.resolve_state()/headline_template() to pick between them,
# never re-deriving that decision.

# The six _FRAME_*_TEXT constants exist because companion/frame_state.py
# defines the same wording as its own module constants, and a local copy
# here is what companion/ui_components.py's frame_strip_html() actually
# passes to i18n.t(). Kept byte-identical to their frame_state.py
# counterparts. Two of the three headlines and the schedule-link text
# below are owned by home.py's catalogue (untouched by this plan); the
# held headline and both delay sentences are owned by frame_state.py's
# own catalogue, migrated later in this same plan.
_FRAME_HEADLINE_DUE_TEXT = i18n.msg("home.next_update", "Next update %s")
_FRAME_HEADLINE_HELD_TEXT = i18n.msg(
    "frame_state.next_wake_around_quiet_hours",
    "Next wake around %s · quiet hours")
_FRAME_HEADLINE_LATE_TEXT = i18n.msg(
    "home.expected_since", "Update overdue · expected at %s")
_FRAME_DELAY_DUE_TEXT = i18n.msg(
    "frame_state.applies_at_the_next_wake_around",
    "Applies at the next wake, around %s.")
_FRAME_DELAY_HELD_TEXT = i18n.msg(
    "frame_state.applies_when_quiet_hours_end_around",
    "Applies when quiet hours end, around %s.")
# Byte-identical to QUICK_ACTION_APPLIES_SENTENCE above by
# construction (same value, not a coincidence) — the retired static
# caption's own text survives as exactly this one computed branch's
# wording, including its Message identity.
_FRAME_DELAY_UNKNOWN_TEXT = QUICK_ACTION_APPLIES_SENTENCE

# The quiet cell's caption link, appended to the same
# `delay_caption_html` slot the switch cells share — never a new slot.
# Owned by home.py's catalogue, like the two headlines above.
_FRAME_QUIET_SCHEDULE_LINK_TEXT = i18n.msg("home.change_the_schedule", "Change the schedule")
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

# Two more, for Home's status header: a warning triangle leading an
# overdue line and a chevron closing the "See Health" pill.
ICON_IDS = ICON_IDS + (
    "icon-warning",
    "icon-chevron-right",
)

# One more icon, for the bottom tab bar's "More" cell. Appended, not
# merged, for the same reason above.
ICON_IDS = ICON_IDS + (
    "icon-more",
)

# The toast family's glyphs: one per tone, a bin for a confirmed
# deletion, the dismiss cross and the Undo arrow.
ICON_IDS = ICON_IDS + (
    "icon-toast-success",
    "icon-toast-info",
    "icon-toast-warning",
    "icon-toast-error",
    "icon-toast-pending",
    "icon-toast-trash",
    "icon-close",
    "icon-undo",
)

# One more icon, for the mobile #site-nav-toggle: the panel it opens
# holds no page-navigation links (those moved to the bottom tab bar), so
# the hamburger glyph read as site navigation; replaced by a gear.
# Appended, not merged, for the same reason above.
ICON_IDS = ICON_IDS + (
    "icon-gear",
)

# One more icon, for the Update nav destination: a two-arrow cycle
# glyph, distinct from icon-refresh (reserved for the copy-button/
# manual-refresh family). Appended, not merged, for the same reason
# above.
ICON_IDS = ICON_IDS + (
    "icon-nav-update",
)

# Three more, for the Display page's look picker: the "Change" pencil,
# the look sheet's close cross and the "Add a special look" plus.
ICON_IDS = ICON_IDS + (
    "icon-pencil",
    "icon-plus",
)

# An outlined "i" in a circle, for the small info buttons that open a
# hover/focus tooltip.
ICON_IDS = ICON_IDS + (
    "icon-info",
)

# Two more, for the Flights phone card: a framed-picture glyph for its
# icon-only "View picture" link, and a filled side-view plane that sits
# on the card's route track.
ICON_IDS = ICON_IDS + (
    "icon-picture",
    "icon-plane",
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
    # The Update nav destination's glyph: a two-arrow cycle, same
    # viewBox/stroke language as the other icon-nav-* symbols, distinct
    # from icon-refresh (reserved for the copy-button/manual-refresh
    # family).
    '<symbol id="icon-nav-update" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.5" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<path d="M3 9.5a7 7 0 0 1 11.5-4.5M17 10.5a7 7 0 0 1-11.5 4.5"/>'
    '<path d="M13 3.5v3h3M7 16.5v-3H4"/>'
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
    '<symbol id="icon-warning" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M10 3 2.5 16.5h15z"/><path d="M10 8.5v3.5M10 14.3v.01"/>'
    "</symbol>"
    '<symbol id="icon-chevron-right" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M8 5l5 5-5 5"/>'
    "</symbol>"
    '<symbol id="icon-pencil" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M13.5 3.5l3 3L7 16H4v-3z"/><path d="M11.5 5.5l3 3"/>'
    "</symbol>"
    '<symbol id="icon-plus" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M10 4v12M4 10h12"/>'
    "</symbol>"
    '<symbol id="icon-info" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="10" cy="10" r="7.5"/><path d="M10 9v4.5M10 6.4v.01"/>'
    "</symbol>"
    # The toast family's tone glyphs, drawn inside a filled disc, so each
    # shape alone tells the tones apart (tick, "i", "!", cross, clock with
    # a return arrow) without relying on the disc's colour.
    '<symbol id="icon-toast-success" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M5 10.4l3.2 3.2L15 6.6"/>'
    "</symbol>"
    '<symbol id="icon-toast-info" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M10 9v5.2"/><path d="M10 5.9v.01"/>'
    "</symbol>"
    '<symbol id="icon-toast-warning" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M10 5.2v6"/><path d="M10 14.6v.01"/>'
    "</symbol>"
    '<symbol id="icon-toast-error" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M6.6 6.6l6.8 6.8M13.4 6.6l-6.8 6.8"/>'
    "</symbol>"
    '<symbol id="icon-toast-pending" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M10 6.2V10l2.6 1.7"/><path d="M15.4 8.2A5.6 5.6 0 1 0 15 12.6"/>'
    '<path d="M15.8 5.2v3.2h-3.2"/>'
    "</symbol>"
    '<symbol id="icon-toast-trash" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M4.5 6h11M8 6V4.5h4V6M6 6l.7 9.5h6.6L14 6"/>'
    "</symbol>"
    '<symbol id="icon-close" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.7" stroke-linecap="round">'
    '<path d="M5.5 5.5l9 9M14.5 5.5l-9 9"/>'
    "</symbol>"
    '<symbol id="icon-picture" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="2.5" y="3.5" width="15" height="13" rx="2"/><circle cx="7.5" cy="8.5" r="1.5"/>'
    '<path d="M17.5 13.5l-4.5-4.5-8 7.5"/>'
    "</symbol>"
    # Points right (east), the direction the route line reads in.
    '<symbol id="icon-plane" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="0">'
    '<path fill="currentColor" d="M18.5 10c0-.7-.6-1.2-1.3-1.2h-4.4L8.6 2.5H6.9l2 6.3H4.6L3 6.8H1.6'
    'l1 3.2-1 3.2H3l1.6-2h4.3l-2 6.3h1.7l4.2-6.3h4.4c.7 0 1.3-.5 1.3-1.2z"/>'
    "</symbol>"
    '<symbol id="icon-undo" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M7.5 5L4 8.5 7.5 12"/><path d="M4 8.5h7.5a4 4 0 0 1 0 8H9"/>'
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
    "update": "icon-nav-update",
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
HEALTH_ALERT_SUFFIX_TEXT = i18n.msg("nav.attention_needed", " — attention needed")
# A substitution token, never markup that ships: page_header() emits it,
# page_shell() swaps it for the flash banner when present, and strips any
# leftover occurrence unconditionally before the response is returned.
FLASH_SLOT_MARKER = "<!--flash-slot-->"
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
