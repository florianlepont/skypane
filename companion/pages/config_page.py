"""The Settings page: theme/runway/LED/quiet-hours/wake-interval/
calendar/notifications controls, rendered and validated against
`server.device_config`'s own registries, plus the per-flight
colour-rules editor and the manual "Trigger poll now" control (its
route, cooldown gate and poll trigger are owned by companion/app.py;
this module only renders its button/copy).
"""
import collections
import re
from datetime import timedelta
from urllib.parse import urlsplit

from companion import i18n
from companion import theme_preview
# The one battery estimator, imported as a module and called qualified
# — a bare `from companion.battery import battery_life_estimate` would
# make the estimate read as this page's own.
from companion import battery
from companion import draw
from companion.layout import escape_html
import companion.layout as layout
from companion import prefs
from companion import screens
from companion import wake
# history_db.recent_runway_events() is a second, independent call to
# the same helper home_page._recent_flights() uses — page modules never
# import each other directly.
from server import device_config, history_db, panel_format
from server.plane import calendar_rules, colour_rules

# The single definition of this route prefix. companion/app.py rebinds
# it (RUNWAY_IMAGE_ROUTE_PREFIX = config_page.RUNWAY_IMAGE_ROUTE_PREFIX)
# rather than re-typing the literal — app.py imports this module, so
# the reverse import would be a cycle.
RUNWAY_IMAGE_ROUTE_PREFIX = "/runway-image/"
RUNWAY_IMAGE_ALT_TEMPLATE = "Airport diagram for %s"

# Same one-definition-site discipline as RUNWAY_IMAGE_ROUTE_PREFIX
# above, with the definition site inverted: companion/theme_preview.py
# owns the prefix and alt-text template, since both this module and
# companion/app.py need to rebind the same constant.
THEME_PREVIEW_ROUTE_PREFIX = theme_preview.THEME_PREVIEW_ROUTE_PREFIX
THEME_PREVIEW_ALT_TEMPLATE = theme_preview.THEME_PREVIEW_ALT_TEMPLATE

# The live preview's `<img>` width/height come from the render
# pipeline's real served dimensions, never a CSS aspect-ratio guess. It
# shares the chip grid's crop/size; only the rendered scene differs
# (the last real runway event instead of the fixed fixture).
THEME_LIVE_PREVIEW_WIDTH, THEME_LIVE_PREVIEW_HEIGHT = theme_preview.THEME_PREVIEW_SIZE
THEME_LIVE_PREVIEW_ALT_TEMPLATE = "Live preview of the %s theme"
THEME_LIVE_PREVIEW_CAPTION_WITH_FLIGHT_TEMPLATE = "Preview with your last flight: %s"
THEME_LIVE_PREVIEW_CAPTION_SAMPLE = "Preview with a sample flight"

# The single definition of this route. companion/app.py rebinds its own
# SETTINGS_ROUTE constant to this value rather than re-typing the
# literal. The old "/config" path is retired: it 404s by design, no
# redirect.
SETTINGS_ROUTE = "/settings"

# Interpolated twice — the settings <form>'s id and the dirty-bar save
# button's form attribute — and the two must never be re-typed as
# literals, since a mismatch would produce a Save button that looks
# correct in markup and silently submits nothing.
SETTINGS_FORM_ID = "settings-form"

# The one settings form renders as two pages sharing the same POST
# route and the same handle_post(): the everyday "Display" page (theme,
# quiet hours, screen on/off) and the advanced "Device" page (runway,
# diagnostic LED, wake interval, calendar, colour rules, manual
# refresh). Which groups land on which page is declared per screen type
# in companion/screens.py, not hard-coded here.
#
# `render(ctx)` with no scope renders the whole legacy page, every
# group, for existing harness checks against the full form;
# companion/app.py never uses that scope for a live route.
SCOPE_ALL = "all"
SCOPE_DISPLAY = "display"
SCOPE_DEVICE = "device"
SCOPES = (SCOPE_ALL, SCOPE_DISPLAY, SCOPE_DEVICE)

# Hidden form fields a scoped page submits so handle_post() knows which
# groups were on the page (absent checkbox => leave unchanged for a
# group that was never rendered, never switch it off) and where to
# redirect back to.
SCOPE_FIELD_NAME = "scope"
RETURN_TO_FIELD_NAME = "return_to"

DISPLAY_PAGE_TITLE = "Display"
DISPLAY_PAGE_PURPOSE = "Everything about what the frame shows and when."
DEVICE_PAGE_TITLE = "Device"
DEVICE_PAGE_PURPOSE = "Hardware, data and diagnostics for the frame."
SCREEN_CAPTION_TEMPLATE = "Screen: %s"

# The three headed supersections Display's own groups render under, in
# this locked order. Each heading/intro pair renders through the shared
# section-intro helper in layout.py.
DISPLAY_LOOK_SECTION_ID = "display-look"
DISPLAY_LOOK_HEADING = "Look"
DISPLAY_LOOK_INTRO = (
    "— the theme, flight colours and calendar that decide how the "
    "picture looks.")
DISPLAY_WATCHES_SECTION_ID = "display-watches"
DISPLAY_WATCHES_HEADING = "What it watches"
DISPLAY_WATCHES_INTRO = "— which Orly runway the frame is watching."
DISPLAY_ON_SECTION_ID = "display-on"
DISPLAY_ON_HEADING = "When it is on"
DISPLAY_ON_INTRO = "— when the screen is lit and when it stays quiet."
# Device's own two supersections, the same section_intro_html() shape
# as the three above. The LED/Notifications pairing is a real shared
# subject: both cards are the frame's signalling channels — the LED
# reports on the device itself, notifications report on the reader's
# phone.
DEVICE_WAKES_SECTION_ID = "device-wakes"
DEVICE_WAKES_HEADING = "When it wakes"
DEVICE_WAKES_INTRO = "— how often the frame wakes up to fetch a new picture."
DEVICE_TELLS_SECTION_ID = "device-tells"
DEVICE_TELLS_HEADING = "How it tells you"
DEVICE_TELLS_INTRO = "— the light on the frame and the alerts on your phone."
DEVICE_POLL_SECTION_ID = "device-poll"
DEVICE_POLL_HEADING = "When you can't wait"
DEVICE_POLL_INTRO = "— fetch a new picture right now."
# An element id, not a class, since its own <label> targets it via for=.
SCREEN_SELECTOR_ID = "screen-id-selector"
SCREEN_SELECTOR_LABEL_TEXT = "Screen type"

# "Aspect": the one merged card, a native `<details name="aspect-rows">`
# accordion over four rows. No radiogroup selects which row is showing
# — a grouped `<details>` set is mutually exclusive by construction,
# with zero script. The COLOUR_USAGE_* values below are a purely
# presentational label (a `data-usage` attribute and this card's own
# branch keys), never submitted to handle_post() — distinct from the
# three saved field names (theme/theme_arriving/calendar_theme_id)
# each row's own palette posts through via form="settings-form".
ASPECT_HEADING = "Aspect"
ASPECT_HEADING_ID = "aspect-heading"
COLOUR_USAGE_DEPARTURES = "departures"
COLOUR_USAGE_ARRIVALS = "arrivals"
COLOUR_USAGE_CALENDAR = "calendar"
COLOUR_USAGE_RULES = "rules"
# Locked order: every row-building loop below walks this exact tuple,
# so the row order and the no-JS floor's stacked-panel order can never
# drift apart.
COLOUR_USAGES = (
    COLOUR_USAGE_DEPARTURES, COLOUR_USAGE_ARRIVALS, COLOUR_USAGE_CALENDAR,
    COLOUR_USAGE_RULES)
FRAME_COLOURS_ROW_LABELS = {
    COLOUR_USAGE_DEPARTURES: "Departures",
    COLOUR_USAGE_ARRIVALS: "Arrivals",
    COLOUR_USAGE_CALENDAR: "Calendar flights",
    COLOUR_USAGE_RULES: "Per-flight rules",
}
# The grouped-<details> `name` attribute value every one of the four
# Aspect accordion rows shares (native grouped disclosure,
# one-open-at-a-time with zero script) — one constant so the four rows
# agree rather than four literals that can drift apart.
ASPECT_ROWS_GROUP_NAME = "aspect-rows"
# The closed-row <summary> format, e.g. "Departures — Red", joining two
# already-translated strings with an em dash. The em dash is
# punctuation, not copy, so this template carries no French entry.
ASPECT_ROW_SUMMARY_TEMPLATE = "%s — %s"
# The one-line legend naming every chip's two .theme-chip__dot
# swatches, rendered once under each grid rather than once per chip.
#
# The dots are `_palette_hex(theme["departing_index"])` and
# `_palette_hex(theme["arriving_index"])` — the ink a theme paints a
# departure and an arrival in, never the background. Every theme has
# `departing_index == arriving_index`, so the two dots are always the
# same ink; a middle-dot separator ("Departures · Arrivals") would
# read as a promise of two different colours that the registry does
# not carry, so the copy is one phrase naming what the shared colour is
# for. `test_config_page.py` computes the expected label count from the
# registry at check time, never a restated literal.
THEME_CHIP_SWATCH_LEGEND = "Departures & arrivals"
# The "Current" badge's own text, server-rendered onto the saved
# chip/card as `data-current-label` and read back by
# `content: attr(data-current-label)` in style.css.
CURRENT_BADGE_LABEL = "Current"
# The attribute the badge's content: attr(...) reads. Written as
# literal text at both the markup site below and in style.css.
CURRENT_BADGE_ATTR = "data-current-label"

# The leading "Same as departures" chip Arrivals/Calendar's own grids
# gain, submitting the empty string (the clear signal handle_post()
# maps to device_config.CLEAR_THEME_ARRIVING/None) — reused verbatim as
# both the chip's own label and the row's own "no override" meta text.
SAME_AS_DEPARTURES_LABEL = "Same as departures"
FRAME_COLOURS_RULES_COUNT_SINGULAR = "1 rule"
FRAME_COLOURS_RULES_COUNT_PLURAL_TEMPLATE = "%d rules"
FRAME_COLOURS_RULES_EMPTY_META = "No rules yet"


def scope_groups(scope, screen_id=None):
    """The ordered tuple of settings-group ids the given scope renders
    for the given screen type. SCOPE_ALL preserves the historical
    single-page order; the two live scopes read the screen type's own
    declaration in companion/screens.py.
    """
    screen = screens.screen_type(screen_id)
    if scope == SCOPE_DISPLAY:
        return tuple(screen["everyday_groups"])
    if scope == SCOPE_DEVICE:
        return tuple(screen["advanced_groups"])
    # Every registered group must appear somewhere in this fixed tuple:
    # a test pins the invariant that the two live scopes' groups are
    # disjoint and their union equals this tuple's own set exactly.
    return (
        screens.GROUP_THEME, screens.GROUP_RUNWAY, screens.GROUP_LED,
        screens.GROUP_QUIET_HOURS, screens.GROUP_WAKE_INTERVAL,
        screens.GROUP_CALENDAR, screens.GROUP_NOTIFICATIONS)


def submitted_scope(form):
    """The scope a submitted settings form was rendered with — SCOPE_ALL
    when the field is absent (the legacy single-page form) or carries
    anything outside SCOPES (a crafted value degrades to the widest,
    most conservative reading rather than being rejected: every group's
    own validation still runs).
    """
    value = form.get(SCOPE_FIELD_NAME)
    return value if value in SCOPES else SCOPE_ALL


def submitted_return_route(form):
    """Where a settings POST redirects back to: the page it came from,
    validated byte-for-byte against the two scoped page routes, else
    the Display page. Never a raw form value.
    """
    value = form.get(RETURN_TO_FIELD_NAME)
    if value in (layout.DISPLAY_ROUTE, layout.DEVICE_ROUTE):
        return value
    return layout.DISPLAY_ROUTE

# The sole accepted submitted value for each checkbox — shared by the
# group's own markup and handle_post()'s validator so the two can never
# drift apart.
LED_CHECKBOX_VALUE = "on"
QUIET_HOURS_CHECKBOX_VALUE = "on"
DISPLAY_CHECKBOX_VALUE = "on"

RUNWAY_SECTION_CAPTION = "Which Orly runway the device watches."
LED_SECTION_CAPTION = "Lit only during the device's brief wake window."

# Stable DOM ids for the group headings a radiogroup's aria-labelledby
# points at, and for each hint paragraph an aria-describedby points at.
# Only the groups that gain role="radiogroup" (the two theme chip grids
# and the runway row) get a *_GROUP_HEADING_ID; every hint gets a
# *_CAPTION_ID/*_HINT_ID regardless, since a hint can describe a
# single-control field too.
RUNWAY_SECTION_CAPTION_ID = "runway-caption"
RUNWAY_GROUP_HEADING_ID = "runway-group-heading"
LED_SECTION_CAPTION_ID = "led-caption"
POLL_SECTION_HEADING = "Manual refresh"
POLL_SECTION_CAPTION = "Trigger an immediate poll cycle."
LED_SECTION_HEADING = "Diagnostic LED"

# The Frame strip is the only quiet-hours on/off control; this caption
# states enable-by-schedule semantics rather than an on/off state.
QUIET_HOURS_SECTION_HEADING = "Quiet hours"
QUIET_HOURS_SECTION_CAPTION = (
    "Pauses the frame's wake, poll and display cycle during the "
    "schedule below.")
QUIET_HOURS_SECTION_CAPTION_ID = "quiet-hours-caption"
# The card's own heading id: the Frame strip's Quiet-hours switch cell
# links here as a fragment target, not a new control.
QUIET_HOURS_GROUP_HEADING_ID = "quiet-hours-group-heading"

# The Night preset's start/end are sourced from device_config's own
# shipped defaults rather than retyped literals, so the preset and the
# default can never drift apart.
QUIET_HOURS_PRESET_NIGHT_START = device_config.DEFAULT_QUIET_HOURS_START
QUIET_HOURS_PRESET_NIGHT_END = device_config.DEFAULT_QUIET_HOURS_END
QUIET_HOURS_PRESET_NIGHT_LABEL = "Night"
QUIET_HOURS_PRESET_WORKDAY_START = "08:00"
QUIET_HOURS_PRESET_WORKDAY_END = "18:00"
QUIET_HOURS_PRESET_WORKDAY_LABEL = "Day"
# "Always on" unchecks the enable checkbox and leaves both times
# untouched, via a distinct data-preset-enabled="0" attribute rather
# than overloading the time attributes with a sentinel value.
QUIET_HOURS_PRESET_ALWAYS_ON_LABEL = "Always on"
QUIET_HOURS_PRESET_ATTR = "data-quiet-preset"

WAKE_INTERVAL_SECTION_HEADING = "Wake interval"
WAKE_INTERVAL_SECTION_CAPTION = "Shorter: fresher data, more battery drain."
WAKE_INTERVAL_PLACEHOLDER_TEXT = "Uses server default"
# The unit, rendered as a sibling beside the number input (never a
# placeholder, which vanishes once a value is typed). Not routed
# through i18n.t(): "s" is the SI symbol for a second, the same symbol
# in French, so it is a unit symbol, not prose. aria-hidden, since the
# field's own translated label already says "seconds".
WAKE_INTERVAL_UNIT_LABEL = "s"
WAKE_INTERVAL_INPUT_ID = "wake-interval-s"
WAKE_INTERVAL_SECTION_CAPTION_ID = "wake-interval-caption"

# The wake interval trades off freshness against battery life. Only one
# side can be stated honestly today: freshness is true by construction
# as long as it says "at most" (the frame learns about a plane at its
# next wake, so it appears at most one interval later). Battery life
# has no first-principles formula (no per-wake energy cost is known),
# so its figure comes from `battery.battery_life_estimate()`'s own
# observed discharge slope, or the named "not enough history" state
# when it refuses to derive one — never an invented number.
WAKE_INTERVAL_FIELD_NAME = "wake_interval_s"
WAKE_GAUGE_CLASS = "wake-gauge"
WAKE_GAUGE_FRESHNESS_ID = "wake-gauge-freshness"
WAKE_GAUGE_BATTERY_ID = "wake-gauge-battery"
WAKE_GAUGE_SECONDS_PER_MINUTE = 60
# Deliberately shorter than health_page's own 3-month trend window:
# this sentence says "recent", and two weeks is comfortably more than
# battery.LIFE_MIN_OBSERVED_SPAN_DAYS while staying recent.
WAKE_BATTERY_WINDOW_DAYS = 14
# The quantity's place is "#", never "%s"/"%d"/"{}": every template
# below reaches the browser as an attribute value value-controls.js
# substitutes into live, and a check scans every French render for a
# stray format artefact.
WAKE_FRESHNESS_TEXT = (
    "A plane reaches the frame at most # min later.")
# Carries this app's own "≈" honesty marker plus the source of the
# claim, so it is never read as a datasheet number.
WAKE_BATTERY_DAY_TEXT = (
    "≈ # day of battery left, from this frame's own recent readings.")
WAKE_BATTERY_DAYS_TEXT = (
    "≈ # days of battery left, from this frame's own recent readings.")
WAKE_BATTERY_UNKNOWN_TEXT = (
    "Not enough battery history yet to say how long a charge lasts.")
# Neither the bound nor the battery figure applies while the screen is
# off, since DISPLAY_OFF_SLEEP_S is pinned independently of this field
# then.
WAKE_BATTERY_SCREEN_OFF_TEXT = (
    "While the screen is off, the frame wakes every %s instead.")
# The relative half, and the only half value-controls.js may recompute
# while the slider moves: two cadences, never a ratio (which would only
# be a valid multiplier on lifetime if every joule went into waking).
# "%d" is the saved cadence (server-side, fixed for the page); "#" is
# the proposed one, the only thing the script substitutes.
WAKE_BATTERY_INSTEAD_TEXT = (
    "This setting wakes the frame every # min instead of every %d min.")

WAKE_SLIDER_CLASS = "wake-slider"
WAKE_SLIDER_INPUT_CLASS = "wake-slider__input"
WAKE_SLIDER_STEP_S = 60
# Its own accessible name: the number input's label names that
# control, and two controls sharing one name loses a screen-reader
# visitor track of which they are on.
WAKE_SLIDER_LABEL = "Wake interval slider"

NOTIFICATIONS_SECTION_HEADING = "Notifications"
NOTIFICATIONS_SECTION_CAPTION = "Get a push alert about battery or connection issues."
NOTIFICATIONS_SECTION_CAPTION_ID = "notifications-caption"
# Write-only, like the calendar feed URL — never rendered back, not
# partially masked. The status row reports only whether a URL is stored.
NOTIFICATIONS_STATUS_CONFIGURED_VERDICT = "Configured"
NOTIFICATIONS_STATUS_NOT_CONFIGURED_VERDICT = "Not configured"
NOTIFICATIONS_URL_FIELD_LABEL = "Push topic URL"
NOTIFICATIONS_URL_HINT = "Paste your ntfy.sh topic URL (or a self-hosted one)."
NOTIFICATIONS_URL_HINT_ID = "notifications-url-hint"
NOTIFICATIONS_URL_HOW_IT_WORKS_BODY = (
    "Stored on the server and never shown back here — pasting a new "
    "one replaces the old.")
NOTIFICATIONS_REPLACE_URL_SUMMARY = "Replace the URL"
# A shape bound against an absurd paste; the arbiter of an acceptable
# topic URL stays server/notify.py's send-time gate, not this bound.
NOTIFICATIONS_URL_MAX_LEN = 2048
NOTIFICATIONS_BATTERY_LABEL = "Battery low"
NOTIFICATIONS_SILENT_LABEL = "Frame silent"
NOTIFICATIONS_TEST_BUTTON_TEXT = "Send a test"
NOTIFICATIONS_BATTERY_CHECKBOX_VALUE = "on"
NOTIFICATIONS_SILENT_CHECKBOX_VALUE = "on"
NOTIFICATIONS_TEST_ROUTE = "/settings/notifications/test"
ERROR_NOTIFICATIONS_URL_TOO_LONG = "That link is too long."

# The Screen on/off and Quiet hours routes the Frame strip's switches
# post to. Home's own route constants are byte-for-byte duplicates,
# never imported: a page module may never import another page module.
QUICK_DISPLAY_ROUTE = "/quick/display"
QUICK_QUIET_HOURS_ROUTE = "/quick/quiet-hours"

# DIRTY_SECTION_ATTR is read by companion/static/dirty-state.js;
# STATIC_SAVE_FALLBACK_ATTR names the native fallback Save button.
# Neither static file imports this module, so the values must be kept
# equal by hand.
DIRTY_SECTION_ATTR = "data-dirty-section"
STATIC_SAVE_FALLBACK_ATTR = "data-static-save-fallback"

# The words dirty-state.js's updateBar()/dirtySectionLabels() carry as
# translated data-* attributes on the save bar. Each constant's own
# English value is also dirty-state.js's documented `|| "English
# fallback"` literal, so the two can never silently disagree about what
# the bar renders without the attribute.
#
# DIRTY_BAR_INITIAL_TEXT is carried only as a data-* attribute, never
# used to seed [data-dirty-count]'s markup: the bar itself renders
# visible (not `hidden`), so seeding the count span with this text
# would announce a false "Unsaved changes" claim via `role="status"` on
# every page load before anything changed. dirty-state.js writes it
# only once it actually finds a difference.
DIRTY_BAR_INITIAL_TEXT = "Unsaved changes"
DIRTY_CHANGED_SUFFIX = " changed"
DIRTY_AND = " and "
DIRTY_LIST_AND = ", and "
DIRTY_UNSAVED_SINGULAR = "1 unsaved change"
DIRTY_UNSAVED_PLURAL = " unsaved changes"
# The ellipsis is the single U+2026 character, matching this module's
# "Polling…" and layout.py's "Reconnecting…" — never three periods.
DIRTY_SAVING_TEXT = "Saving…"

# "{n}" is filled in with a server-computed remaining-seconds figure,
# never anything client-supplied. This is the button-adjacent copy
# shown while the trigger is disabled — a separate rendering site from
# companion/app.py's own FLASH_MESSAGES entry for the same event, since
# a page module must never import companion/app.py.
POLL_COOLDOWN_HELPER_TEXT = "Poll triggered recently — try again in {n}s."

# DOM ids the live countdown script (poll-cooldown.js) hooks with
# document.getElementById(), shared with poll_trigger_section()'s
# markup so the two can never drift apart.
POLL_TRIGGER_BUTTON_ID = "poll-trigger-btn"
POLL_COOLDOWN_TEXT_ID = "poll-cooldown-text"

# The enabled (zero-cooldown) branch's button label while a submit is
# pending. Cosmetic only: companion/app.py's _POLL_LOCK is the actual
# correctness boundary.
POLL_SUBMIT_PENDING_TEXT = "Polling…"

# The placeholder the client substitutes the live second count into, so
# the ticking copy stays word-identical to the static, server-rendered
# copy and to the post-redirect flash banner.
POLL_COOLDOWN_TEMPLATE_TOKEN = "__N__"

# The flash keys this module's handle_post() can return — the single
# source of truth companion/app.py's own flash-key constants and
# FLASH_MESSAGES dict reference.
FLASH_SAVED = "saved"
FLASH_SAVE_FAILED = "save_failed"
FLASH_POLL_TRIGGERED = "poll_triggered"
FLASH_POLL_COOLDOWN = "poll_cooldown"
# Distinct from FLASH_SAVE_FAILED: a run_once() exception inside
# POST /poll-now must not show "Couldn't save settings" for a failure
# unrelated to saving settings.
FLASH_POLL_FAILED = "poll_failed"
# Distinct from FLASH_POLL_COOLDOWN: this key means a poll is executing
# on this exact request right now, in another thread —
# `_POLL_LOCK.acquire(blocking=False)` failing is the only producer,
# closing the window where two requests could both observe zero
# cooldown and both call `poll_loop.run_once()`.
FLASH_POLL_ALREADY_RUNNING = "poll_already_running"

# The per-flight colour-rules editor's routes. Add and delete are
# immediate POSTs on their own routes, outside SETTINGS_ROUTE and the
# settings form's dirty bar — a rule is a one-step immediate act, not a
# pending edit.
RULES_ADD_ROUTE = "/settings/rules/add"
RULES_DELETE_ROUTE_PREFIX = "/settings/rules/"
RULES_DELETE_ROUTE_SUFFIX = "/delete"

# An immediate, session-gated POST outside SETTINGS_ROUTE and the
# settings form's dirty bar: a one-step act, not a pending settings edit.
CALENDAR_DISCONNECT_ROUTE = "/settings/calendar/disconnect"

RULES_SECTION_CAPTION = "Give one flight, one aircraft or one airline its own theme."
RULES_HOW_RULES_COMBINE_SUMMARY = "How rules combine"
RULES_HOW_RULES_COMBINE_BODY = (
    "The most specific match wins — a flight rule beats an aircraft "
    "rule, which beats an airline rule — and adding a key that's "
    "already in use replaces the existing rule for it.")
RULE_KIND_FIELD_LABEL = "Match by"
RULE_VALUE_FIELD_LABEL = "Value"
RULE_ADD_BUTTON_TEXT = "Add rule"
# The plain-language segment labels, used by both the add form's
# segment text and the rule-row kind badge, so the two can never
# disagree.
RULE_KIND_LABELS = {
    colour_rules.RULE_KIND_CALLSIGN: "Flight",
    colour_rules.RULE_KIND_HEX: "Aircraft",
    colour_rules.RULE_KIND_PREFIX: "Airline",
}
# A separate mapping from RULE_KIND_LABELS above, read only for each
# segment's own title attribute, never shown as the visible label text.
RULE_KIND_TITLES = {
    colour_rules.RULE_KIND_CALLSIGN: "Callsign",
    colour_rules.RULE_KIND_HEX: "ICAO24 hex",
    colour_rules.RULE_KIND_PREFIX: "Callsign prefix",
}
RULE_VALUE_PLACEHOLDER = "AFR1234"
RULES_EMPTY_HEADING = "No flight colours yet."
RULES_EMPTY_BODY = (
    "Add one above to give a flight, aircraft or airline its own theme.")
RULE_REMOVE_BUTTON_TEXT = "Remove"
# The suggestion chips' own label prefix; the joined callsign list
# itself is data, never translated.
RULE_SUGGESTIONS_LABEL = "Recent:"
# aria-labelledby targets for the two radiogroups the add form carries.
RULE_KIND_HEADING_ID = "rule-kind-heading"
RULE_THEME_HEADING_ID = "rule-theme-heading"
RULE_REMOVE_CONFIRM_QUESTION = "Remove this rule?"

# The flash keys this module's rule-add/rule-delete routes (owned by
# companion/app.py) can produce; app.py rebinds each under its own
# FLASH_KEY_RULE_* name and owns the message text/ARIA role.
FLASH_RULE_ADDED = "rule_added"
FLASH_RULE_REPLACED = "rule_replaced"
FLASH_RULE_KEY_INVALID = "rule_key_invalid"
FLASH_RULE_REGISTRY_FULL = "rule_registry_full"
FLASH_RULE_SAVE_FAILED = "rule_save_failed"
FLASH_RULE_DELETED = "rule_deleted"
FLASH_RULE_DELETE_FAILED = "rule_delete_failed"

# This feature can only colour a flight that happens to be the one
# currently on screen — it does not track, watch, follow, monitor,
# notify, or know a flight is happening independently of what is on
# screen, and no string below may imply otherwise.
CALENDAR_HOW_IT_WORKS_SUMMARY = "How it works"
CALENDAR_HOW_IT_WORKS_BODY = (
    "It can only colour a flight that happens to be on screen — it "
    "does not track or announce anything on its own. Applies on the "
    "frame's next scheduled poll, not immediately.")
# "Not connected" covers both the never-configured and the
# permission-drifted states — a drifted stored link is not usably
# connected either.
CALENDAR_STATUS_CONNECTED_VERDICT = "Connected"
CALENDAR_STATUS_NOT_CONNECTED_VERDICT = "Not connected"
CALENDAR_STATUS_DETAIL_SINGULAR_TEMPLATE = "1 upcoming flight · checked %s"
CALENDAR_STATUS_DETAIL_TEMPLATE = "%d upcoming flights · checked %s"
# A fixed dict keyed on a category derived from existing fields
# (last_attempt_at newer than any usable last_synced_at) — never the
# fetch's own caught exception text, which is not persisted anywhere
# this module could read it from.
CALENDAR_STATUS_FETCH_FAILED_DETAIL = "The feed could not be read"

CALENDAR_CONNECT_BUTTON_TEXT = "Connect calendar"
CALENDAR_REPLACE_URL_SUMMARY = "Replace the feed URL"
# The same form/route posts the URL field in both states, but the
# button reads shorter once a feed is already stored — "Connect
# calendar" only ever applies to a first-time paste.
CALENDAR_REPLACE_BUTTON_TEXT = "Replace"
CALENDAR_CONNECT_ROUTE = "/settings/calendar/connect"

# Plain, honest wording: no surveillance verb, no promise the frame
# cannot keep. The file the URL is stored in is never named below.
CALENDAR_URL_FIELD_LABEL = "Calendar feed URL"
CALENDAR_URL_HINT = (
    "Your calendar's private iCal link. Stored on the server and never "
    "shown back here — pasting a new one replaces the old.")
CALENDAR_URL_HINT_ID = "calendar-url-hint"

# The Aspect card's copy floor exempts these two: DISPLAY_LOOK_INTRO
# (a different card's own intro) and CALENDAR_URL_HINT (its wording is
# never to be shortened). Kept here, beside the strings they exempt,
# rather than in a second harness-side list that could drift from this
# one.
ASPECT_CAPTION_EXEMPTIONS = (
    DISPLAY_LOOK_INTRO,
    CALENDAR_URL_HINT,
)
# A cross-DOM form= attribute (CALENDAR_DISCONNECT_FORM_ID) lets this
# button submit a <form> that is never its own DOM ancestor.
CALENDAR_DISCONNECT_BUTTON_TEXT = "Disconnect"
CALENDAR_DISCONNECT_FORM_ID = "calendar-disconnect-form"
# submitted_calendar_signal()'s gates still compare a submitted
# calendar_disconnect field against this value, kept deliberately
# reachable for a hostile client crafting that field into a /settings
# POST. The dedicated CALENDAR_DISCONNECT_ROUTE never reads this value
# at all — it always means "disconnect", once its own confirm gate
# passes.
CALENDAR_DISCONNECT_CHECKBOX_VALUE = "on"

# The dedicated disconnect route's own confirm gate — the single
# definition site the markup, the client-side misclick guard
# (confirm-submit.js) and the handler all read. Deliberately a
# different field name from calendar_disconnect above: this field means
# "the confirmation step passed", that one meant "the checkbox was
# ticked".
CALENDAR_DISCONNECT_CONFIRM_FIELD = "confirm"
CALENDAR_DISCONNECT_CONFIRM_VALUE = "yes"
# The question confirm-submit.js passes to window.confirm() (a
# misclick guard only), carried via the disconnect form's data-confirm
# attribute, never duplicated in the script itself.
CALENDAR_DISCONNECT_CONFIRM_QUESTION = (
    "Disconnect this calendar and delete the flights it supplied?")
# What a no-JS or CSP-blocked browser sees instead of the native dialog
# above, on the server-rendered two-step confirmation page.
CALENDAR_DISCONNECT_CONFIRM_HEADING = "Disconnect calendar?"
CALENDAR_DISCONNECT_CONFIRM_SENTENCE = (
    "This disconnects your calendar and deletes the flights it "
    "supplied from the server. This can't be undone — you'd need to "
    "paste the feed URL again to reconnect.")
CALENDAR_DISCONNECT_CONFIRM_BUTTON_TEXT = "Disconnect calendar"
CALENDAR_DISCONNECT_CANCEL_TEXT = "Cancel"
# The one string in this interface permitted to reference "the server",
# since this is the one case where the operator has to act there.
# Names no path, filename or part of the URL.
CALENDAR_STATUS_PERMISSION_UNSAFE = (
    "Connected, but ignored — its saved link on the server became "
    "readable beyond this frame. Paste the feed URL again below to "
    "store it safely.")
# A shape bound against an absurd paste, not a definition of an
# acceptable URL. The arbiter of whether a URL is acceptable stays the
# server-side safety gate and the fetch itself.
CALENDAR_URL_MAX_LEN = 2048

# The flash keys the save-triggered immediate sync can produce;
# companion/app.py rebinds each under its own FLASH_KEY_CALENDAR_* name.
FLASH_CALENDAR_CONNECTED = "calendar_connected"
FLASH_CALENDAR_SYNC_FAILED = "calendar_sync_failed"
FLASH_CALENDAR_DISCONNECTED = "calendar_disconnected"
FLASH_CALENDAR_SYNC_DEFERRED = "calendar_sync_deferred"
# The two outcomes only POST /settings/calendar/connect can produce.
# The failure path reuses FLASH_CALENDAR_SYNC_FAILED rather than a
# third calendar failure message.
FLASH_CALENDAR_CONNECT_OK = "calendar_connect_ok"
FLASH_CALENDAR_CONNECT_INVALID = "calendar_connect_invalid"

# The two outcomes POST /settings/notifications/test can produce.
FLASH_NOTIFICATIONS_TEST_OK = "notifications_test_ok"
FLASH_NOTIFICATIONS_TEST_FAILED = "notifications_test_failed"


def _field_error_html(errors, field, control_id):
    """"" when `field` carries no message in `errors`, otherwise a
    single `role="alert"` paragraph rendered after the offending
    control. `control_id` need not match a real DOM id on the control —
    it only builds the stable anchor id `_field_error_attrs()` points
    `aria-describedby` at, so the message is programmatically
    associated with the control, not merely visually adjacent.
    """
    message = errors.get(field) if errors else None
    if not message:
        return ""
    return (
        '<p class="field-error text-label" id="%s-error" role="alert">%s</p>'
    ) % (escape_html(control_id), escape_html(i18n.t(message)))


def _describedby_attr(*ids):
    """The single builder of every `aria-describedby` fragment this
    file emits. Drops every falsy id and joins the survivors with one
    space, in the order given (hint first, then error). Returns "" when
    no id survives, so no control ever emits a bare `aria-describedby=""`.
    """
    present = [control_id for control_id in ids if control_id]
    if not present:
        return ""
    return ' aria-describedby="%s"' % escape_html(" ".join(present))


# The suffix appended to a caption's own apply-timing clause when the
# next-wake value is known — never baked into the caption constant
# itself, so the caption reads unchanged when the value is not known.
NEXT_WAKE_CAPTION_SUFFIX_TEMPLATE = " (next wake ≈ %s)"


def _with_next_wake(caption, next_wake_clock):
    """`caption` unchanged when `next_wake_clock` is falsy — no
    placeholder, no "unknown" — otherwise `caption` plus
    `NEXT_WAKE_CAPTION_SUFFIX_TEMPLATE % next_wake_clock`. The single
    implementation every caption site below uses.

    `caption` is translated by the caller; this function only
    translates its own suffix template, before substituting
    `next_wake_clock` into it.
    """
    if not next_wake_clock:
        return caption
    return caption + (i18n.t(NEXT_WAKE_CAPTION_SUFFIX_TEMPLATE) % next_wake_clock)


def _field_error_attrs(errors, field, control_id, hint_id=None):
    """The ARIA attribute fragment for the control `_field_error_html()`
    built an error anchor for, folding in an optional `hint_id` via
    `_describedby_attr()` — hint first, then the error id.

    Three shapes: no error and no hint -> `""`; no error, a hint ->
    ` aria-describedby="{hint_id}"` alone; an error (hint or not) ->
    ` aria-invalid="true"` plus a combined `aria-describedby`.

    Applied to controls with exactly one natural DOM element to
    decorate; the three radio-group fields render their error the same
    way but skip this fragment entirely, since no single native input
    in a same-named radio group is uniquely "the" control to describe
    — their hint links to the `role="radiogroup"` container instead.
    """
    has_error = bool(errors and errors.get(field))
    error_id = ("%s-error" % control_id) if has_error else None
    describedby = _describedby_attr(hint_id, error_id)
    if has_error:
        return ' aria-invalid="true"%s' % describedby
    return describedby


def _submitted_or_current(submitted, field, current):
    """`submitted[field]` when `field` is present in `submitted` — an
    empty string is a meaningful submitted value, never treated as
    absent — else `current`. `submitted` is `None` for every render()
    call that is not re-rendering a rejected save, so `current` always
    wins then. Never `or`.
    """
    if submitted is not None and field in submitted:
        return submitted[field]
    return current


def _submitted_checkbox_checked(submitted, field, checked_value, current_checked):
    """The rendered `checked` state for one of the absent-means-False
    checkbox fields on a rejected save's re-render.

    When a real submission happened (`submitted is not None`), an
    absent field means unchecked, and a present-but-wrong value also
    renders unchecked (the field's own error message reports the
    problem, never a bogus stuck-on box). `submitted is None` (an
    ordinary page-load render, never a rejected-save re-render) falls
    back to `current_checked` untouched — this is why `render()` must
    not collapse a `None` `submitted` to `{}`.
    """
    if submitted is None:
        return bool(current_checked)
    return submitted.get(field) == checked_value


def _palette_hex(index):
    """`#RRGGBB`, computed from `panel_format.PALETTE_RGB`'s flat int
    list at palette index `index` — never a hardcoded hex literal, so a
    future re-tuning of the physical panel ink automatically updates
    every swatch that calls this helper.
    """
    r, g, b = panel_format.PALETTE_RGB[index * 3: index * 3 + 3]
    return "#%02X%02X%02X" % (r, g, b)


def _palette_swatch_html(theme_id, extra_class=""):
    """A CSS-drawn, non-photographic themed swatch: one outer
    `<span class="palette-swatch">` filled with
    `_palette_hex(departing_index)`, plus an optional child band span
    carrying `_palette_hex(band_index)` when it differs from
    `departing_index` — keeping a same-index theme's band solid rather
    than faking a two-tone band the real panel paints as one colour.
    Its geometry is a stylesheet rule; only the two colours compute here.
    """
    theme = device_config.THEMES[theme_id]
    hex_fill = _palette_hex(theme["departing_index"])
    css_class = "palette-swatch"
    if extra_class:
        css_class += " " + extra_class
    band_html = ""
    if "band_index" in theme and theme["band_index"] != theme["departing_index"]:
        band_html = '<span class="palette-swatch__band" style="background:%s"></span>' % (
            escape_html(_palette_hex(theme["band_index"])))
    return '<span class="%s" aria-hidden="true" style="background:%s">%s</span>' % (
        escape_html(css_class), escape_html(hex_fill), band_html)


def _palette_chip_html(field_name, theme_id, selected, radio_form_id=None):
    """One palette entry: a `<label class="palette-chip">` wrapping a
    visually-hidden native radio, this theme's own
    `_palette_swatch_html()` (no `<img>`, no per-chip preview route
    call), and a caption.

    `data-preview-src` on the `<label>` must not be dropped:
    `theme-preview.js` resolves the live preview source off the
    changed radio input's `parentNode`; dropping it silently stops the
    live preview from following selection.

    No `--selected` server class or "Current" badge here: this chip's
    selected state is the live `:has(input:checked)` treatment, so a
    second, server-rendered signal would be redundant.
    """
    form_attr_html = ' form="%s"' % escape_html(radio_form_id) if radio_form_id else ""
    escaped_id = escape_html(theme_id)
    label = i18n.t(device_config.theme_label(theme_id))
    check_html = ""
    if selected:
        check_html = (
            '<span class="palette-chip__check">%s'
            '<span class="visually-hidden">%s</span></span>'
        ) % (layout.icon_html("icon-check"), escape_html(i18n.t("Selected")))
    return (
        '<label class="palette-chip" data-preview-src="%s%s.png?live=1">'
        '<input type="radio" name="%s" value="%s" class="visually-hidden"%s%s>'
        "%s"
        '<span class="palette-chip__name">%s</span>'
        "%s"
        "</label>"
    ) % (
        THEME_PREVIEW_ROUTE_PREFIX, escaped_id,
        escape_html(field_name), escaped_id, form_attr_html,
        " checked" if selected else "",
        _palette_swatch_html(theme_id, extra_class="palette-chip__swatch"),
        escape_html(label),
        check_html,
    )


def _palette_grid_html(
        field_name, selected_theme_id, radio_form_id=None, leading_html="",
        labelled_by=""):
    """The wrapping palette grid: `<div class="palette" role=
    "radiogroup">`, looping `device_config.THEME_IDS` in registry
    order and interpolating `leading_html` before the chips, so a
    caller can prepend `_same_as_departures_chip_html()`'s output
    unchanged.

    No `id` attribute: this function has three call sites on one page,
    and an `id` emitted inside a multi-call renderer would either
    collide or go un-controlled by anything.
    """
    labelled_by_html = ' aria-labelledby="%s"' % escape_html(labelled_by) if labelled_by else ""
    chips = [
        _palette_chip_html(
            field_name, theme_id, theme_id == selected_theme_id,
            radio_form_id=radio_form_id)
        for theme_id in device_config.THEME_IDS
    ]
    return '<div class="palette" role="radiogroup"%s>%s%s</div>' % (
        labelled_by_html, leading_html, "".join(chips))


def _usage_row_summary_html(usage, theme_id, meta_text=None):
    """One Aspect accordion row's `<summary>`: the row's swatch, then a
    name span wrapping a nested meta span, "{row label} — {meta}". The
    em-dash join is computed once from `ASPECT_ROW_SUMMARY_TEMPLATE`,
    then sliced back into the meta span's own tail, so the dash has one
    source. `meta_text`, when omitted, defaults to the saved theme name.
    """
    if meta_text is None:
        meta_text = i18n.t(device_config.theme_label(theme_id))
    row_label = i18n.t(FRAME_COLOURS_ROW_LABELS[usage])
    escaped_row_label = escape_html(row_label)
    escaped_meta = escape_html(meta_text)
    joined = ASPECT_ROW_SUMMARY_TEMPLATE % (escaped_row_label, escaped_meta)
    meta_suffix_html = joined[len(escaped_row_label):]
    swatch_html = (
        _palette_swatch_html(theme_id, extra_class="usage-row__swatch")
        if theme_id is not None else ""
    )
    return (
        "<summary>%s"
        '<span class="usage-row__name">%s'
        '<span class="usage-row__meta">%s</span>'
        "</span>"
        "</summary>"
    ) % (swatch_html, escaped_row_label, meta_suffix_html)


def _theme_chip_grid_html(
        field_name, selected_theme_id, extra_class="", extra_attr="", chip_extra_class="",
        radio_form_id=None, leading_chip_html=""):
    """The one chip-grid renderer, called once per usage panel
    (departures, arrivals, calendar, rule-add). Call sites differ only
    in the radio group's `name`, the checked chip, the wrapper
    class/attribute, and an optional `leading_chip_html` fragment
    (typically "Same as departures", submitting an empty string).

    `chip_extra_class` shrinks every chip to compact geometry; the
    grid-level `extra_class` alone has no chip-shrinking rule.
    `radio_form_id`, when given, adds `form=` to every radio, so the
    grid posts through the settings form even rendered as its sibling.
    """
    form_attr_html = ' form="%s"' % escape_html(radio_form_id) if radio_form_id else ""
    chips = []
    for theme_id in device_config.THEME_IDS:
        selected = theme_id == selected_theme_id
        checked = " checked" if selected else ""
        chip_class = "theme-chip"
        current_attr_html = ""
        if selected:
            chip_class += " theme-chip--selected"
            # Emitted only on the saved chip: only
            # `.theme-chip--selected:not(:has(input:checked))::after`
            # ever reads it.
            current_attr_html = ' %s="%s"' % (
                CURRENT_BADGE_ATTR, escape_html(i18n.t(CURRENT_BADGE_LABEL)))
        if chip_extra_class:
            chip_class += " " + chip_extra_class
        theme = device_config.THEMES[theme_id]
        # device_config.theme_label()'s registry text is translated at
        # this display site; the theme id itself never changes.
        label = i18n.t(device_config.theme_label(theme_id))
        escaped_id = escape_html(theme_id)
        departing_hex = _palette_hex(theme["departing_index"])
        arriving_hex = _palette_hex(theme["arriving_index"])
        chips.append(
            '<label class="%s" data-preview-src="%s%s.png?live=1"%s>'
            '<input type="radio" name="%s" value="%s" class="visually-hidden"%s%s>'
            # background-color, not the background shorthand: the
            # shorthand resets background-image to none, and an inline
            # style beats every author rule, making style.css's
            # skeleton sheen for this band unreachable otherwise.
            '<img class="theme-chip__preview" src="%s%s.png" alt="%s" '
            'width="320" height="120" loading="lazy" style="background-color:%s">'
            '<span class="theme-chip__body">'
            '<span class="theme-chip__name">%s</span>'
            '<span class="theme-chip__swatches" aria-hidden="true">'
            '<span class="theme-chip__dot" style="background:%s"></span>'
            '<span class="theme-chip__dot" style="background:%s"></span>'
            "</span>"
            "</span>"
            '<span class="theme-chip__check">%s<span class="visually-hidden">%s</span></span>'
            "</label>"
            % (
                chip_class, THEME_PREVIEW_ROUTE_PREFIX, escaped_id, current_attr_html,
                escape_html(field_name), escaped_id, form_attr_html, checked,
                THEME_PREVIEW_ROUTE_PREFIX, escaped_id,
                escape_html(i18n.t(THEME_PREVIEW_ALT_TEMPLATE) % label),
                escape_html(departing_hex),
                escape_html(label),
                escape_html(departing_hex), escape_html(arriving_hex),
                layout.icon_html("icon-check"),
                escape_html(i18n.t("Selected")),
            )
        )
    grid_class = "theme-chip-grid"
    if extra_class:
        grid_class = grid_class + " " + extra_class
    attr_html = (" %s" % extra_attr) if extra_attr else ""
    # The swatch legend is one line under the grid and outside it, so
    # it is not a child of the element carrying role="radiogroup",
    # where a stray non-radio child would be announced inside the group.
    legend_html = '<p class="text-label section-caption">%s</p>' % escape_html(
        i18n.t(THEME_CHIP_SWATCH_LEGEND))
    return '<div class="%s"%s>%s%s</div>%s' % (
        grid_class, attr_html, leading_chip_html, "".join(chips), legend_html)


def _theme_live_preview_html(current_theme_id, state_dir, extra_class=""):
    """The Aspect card's live preview figure. The `<img src>` is the
    saved theme's live preview route (`current_theme_id`,
    membership-tested against `device_config.THEMES`), the one eagerly-
    loaded image on this page. Without JavaScript it never changes;
    `theme-preview.js` swaps it on chip selection.

    The caption reads the most recent runway event's callsign, using
    the same connection helper `_rule_suggestion_chips_html()` uses,
    degrading to the sample-flight wording on any exception or a falsy
    `state_dir` — never raising, never a 500.
    """
    live_theme_id = (
        current_theme_id if current_theme_id in device_config.THEMES
        else device_config.DEFAULT_THEME_ID)
    label = i18n.t(device_config.theme_label(live_theme_id))
    callsign = None
    if state_dir:
        try:
            with history_db.open_db(state_dir) as conn:
                rows = history_db.recent_runway_events(conn, limit=1)
            if rows:
                callsign = rows[0].get("callsign")
        except Exception:
            callsign = None
    if callsign:
        caption_text = i18n.t(THEME_LIVE_PREVIEW_CAPTION_WITH_FLIGHT_TEMPLATE) % callsign
    else:
        caption_text = i18n.t(THEME_LIVE_PREVIEW_CAPTION_SAMPLE)
    figure_class = "theme-live-preview"
    if extra_class:
        figure_class = figure_class + " " + extra_class
    return (
        '<figure class="%s">'
        '<img class="theme-live-preview__image" src="%s%s.png?live=1" '
        'width="%d" height="%d" loading="eager" alt="%s">'
        '<figcaption class="text-label">%s</figcaption>'
        "</figure>"
    ) % (
        figure_class,
        THEME_PREVIEW_ROUTE_PREFIX, escape_html(live_theme_id),
        THEME_LIVE_PREVIEW_WIDTH, THEME_LIVE_PREVIEW_HEIGHT,
        escape_html(i18n.t(THEME_LIVE_PREVIEW_ALT_TEMPLATE) % label),
        escape_html(caption_text),
    )


def _same_as_departures_chip_html(field_name, checked, radio_form_id=None):
    """The leading, non-theme chip Arrivals'/Calendar's own rows
    prepend to their palette grid via `_palette_grid_html()`'s
    `leading_html` seam — submits the empty string for `field_name`
    (the clear signal), never a real theme id.

    No "Current" badge here: the live `:has(input:checked)` treatment
    on `.leading-option` is the one selected-state signal this control
    needs; a second, server-rendered one would be two sources of truth.
    """
    form_attr_html = ' form="%s"' % escape_html(radio_form_id) if radio_form_id else ""
    return (
        '<label class="leading-option">'
        '<input type="radio" name="%s" value="" class="visually-hidden"%s%s>'
        '<span class="leading-option__name">%s</span>'
        '<span class="theme-chip__check">%s<span class="visually-hidden">%s</span></span>'
        "</label>"
    ) % (
        escape_html(field_name), form_attr_html, " checked" if checked else "",
        escape_html(i18n.t(SAME_AS_DEPARTURES_LABEL)),
        layout.icon_html("icon-check"), escape_html(i18n.t("Selected")),
    )


def _usage_row_html(usage, summary_html, body_html, is_open=False, extra_class=""):
    """One Aspect accordion row. The row is a container only:
    `summary_html` and `body_html` arrive already built by the caller,
    so `_aspect_card_html()` can show all four rows' shapes side by
    side rather than hiding them inside branches here.

    Grouped `<details name="...">` is native, mutually-exclusive-by-
    construction accordion behaviour — zero script, zero server-side
    "which row is open" state beyond `is_open` (Departures ships
    `open`; the other three never do).
    """
    row_class = "usage-row"
    if extra_class:
        row_class = row_class + " " + extra_class
    return (
        '<details class="%s" name="%s" data-usage="%s"%s>'
        "%s%s"
        "</details>"
    ) % (
        escape_html(row_class), escape_html(ASPECT_ROWS_GROUP_NAME), escape_html(usage),
        " open" if is_open else "",
        summary_html, body_html,
    )


def _aspect_card_html(
        ctx, current_theme_id, current_theme_arriving, current_calendar_theme_id,
        errors=None, submitted=None, state_dir=None,
        calendar_configured=False, calendar_drift=False, calendar_last_synced_at=None,
        calendar_last_attempt_at=None, now=None, calendar_entry_count=0):
    """"Aspect": the one tile with a native accordion, one live preview
    above four grouped `_usage_row_html()` rows in `COLOUR_USAGES`'
    locked order. `_calendar_connection_html()` builds the calendar
    row's connection block. `errors`/`submitted`/`state_dir`
    repopulate the theme palettes on a rejected save.
    `departures_safe_id` (and its equivalents) keep an unregistered
    theme id from ever reaching `device_config.THEMES[...]`.
    """
    effective_theme_id = _submitted_or_current(submitted, "theme", current_theme_id)
    # The live preview is keyed off effective_theme_id (the same
    # repopulation value every palette grid below uses), not the bare
    # saved current_theme_id, so a rejected save's re-render shows the
    # submitted theme, not the stored one.
    live_preview_html = _theme_live_preview_html(
        effective_theme_id, state_dir, extra_class="aspect-card__preview")

    # An unregistered stored/submitted theme id never reaches
    # device_config.THEMES[...] — it resolves to DEFAULT_THEME_ID
    # before any swatch or label is computed. Also the fallback
    # swatch/label source for Arrivals/Calendar's own "Same as
    # departures" state.
    departures_safe_id = (
        effective_theme_id if effective_theme_id in device_config.THEMES
        else device_config.DEFAULT_THEME_ID)
    departures_row = _usage_row_html(
        COLOUR_USAGE_DEPARTURES,
        _usage_row_summary_html(COLOUR_USAGE_DEPARTURES, departures_safe_id),
        _palette_grid_html(
            "theme", effective_theme_id, radio_form_id=SETTINGS_FORM_ID,
            labelled_by=ASPECT_HEADING_ID)
        + _field_error_html(errors, "theme", "theme"),
        is_open=True)

    effective_arriving = _submitted_or_current(
        submitted, "theme_arriving", current_theme_arriving)
    arrivals_same_checked = not effective_arriving
    arrivals_leading = _same_as_departures_chip_html(
        "theme_arriving", arrivals_same_checked, radio_form_id=SETTINGS_FORM_ID)
    # Carried verbatim from `_frame_colours_card_html()`: "Same as
    # departures" falls back to the DEPARTURES theme's own swatch/label
    # for this row's summary, never a blank/neutral placeholder — a
    # scripts-blocked reader closing this row still sees which colour
    # it actually resolves to.
    if arrivals_same_checked:
        arrivals_meta = i18n.t(SAME_AS_DEPARTURES_LABEL)
        arrivals_swatch_id = departures_safe_id
    else:
        arrivals_safe_id = (
            effective_arriving if effective_arriving in device_config.THEMES
            else departures_safe_id)
        arrivals_meta = i18n.t(device_config.theme_label(arrivals_safe_id))
        arrivals_swatch_id = arrivals_safe_id
    arrivals_row = _usage_row_html(
        COLOUR_USAGE_ARRIVALS,
        _usage_row_summary_html(
            COLOUR_USAGE_ARRIVALS, arrivals_swatch_id, meta_text=arrivals_meta),
        _palette_grid_html(
            "theme_arriving", effective_arriving, radio_form_id=SETTINGS_FORM_ID,
            leading_html=arrivals_leading, labelled_by=ASPECT_HEADING_ID)
        + _field_error_html(errors, "theme_arriving", "theme-arriving"))

    effective_calendar = _submitted_or_current(
        submitted, "calendar_theme_id", current_calendar_theme_id)
    calendar_same_checked = not effective_calendar
    calendar_leading = _same_as_departures_chip_html(
        "calendar_theme_id", calendar_same_checked, radio_form_id=SETTINGS_FORM_ID)
    if calendar_same_checked:
        calendar_meta = i18n.t(SAME_AS_DEPARTURES_LABEL)
        calendar_swatch_id = departures_safe_id
    else:
        calendar_safe_id = (
            effective_calendar if effective_calendar in device_config.THEMES
            else departures_safe_id)
        calendar_meta = i18n.t(device_config.theme_label(calendar_safe_id))
        calendar_swatch_id = calendar_safe_id
    # The calendar's connection block nests directly beneath this row's
    # palette and field error. The disconnect form returned alongside
    # it is not part of the row body: it is a sibling fragment of the
    # whole .aspect-card div, concatenated onto this function's own
    # return value below.
    calendar_connection_row_html, calendar_disconnect_form_html = _calendar_connection_html(
        calendar_configured, calendar_drift, calendar_last_synced_at,
        calendar_last_attempt_at, now, calendar_entry_count,
        errors=errors, submitted=submitted, state_dir=state_dir)
    calendar_row = _usage_row_html(
        COLOUR_USAGE_CALENDAR,
        _usage_row_summary_html(
            COLOUR_USAGE_CALENDAR, calendar_swatch_id, meta_text=calendar_meta),
        _palette_grid_html(
            "calendar_theme_id", effective_calendar, radio_form_id=SETTINGS_FORM_ID,
            leading_html=calendar_leading, labelled_by=ASPECT_HEADING_ID)
        + _field_error_html(errors, "calendar_theme_id", "calendar-theme")
        + calendar_connection_row_html)

    # The rules row's body: the rule list (or empty state), the add
    # form and the suggestion chips sit inside a nested
    # <details class="rule-add"> disclosure; "How rules combine" sits
    # outside it, since it explains the list, not the form.
    registry = ctx.get("colour_rules")
    if not isinstance(registry, dict):
        registry = {kind: {} for kind in colour_rules.RULE_KINDS}
    rule_rows = colour_rules.rule_rows(registry)
    rules_caption_html = '<p class="text-label section-caption">%s</p>' % escape_html(
        i18n.t(RULES_SECTION_CAPTION))
    rules_how_combine_html = (
        '<details><summary>%s</summary><p class="text-body">%s</p></details>'
    ) % (
        escape_html(i18n.t(RULES_HOW_RULES_COMBINE_SUMMARY)),
        escape_html(i18n.t(RULES_HOW_RULES_COMBINE_BODY)),
    )
    if not rule_rows:
        rules_list_html = (
            '<div class="empty-state-plain"><p class="text-label">%s %s</p></div>'
        ) % (escape_html(i18n.t(RULES_EMPTY_HEADING)), escape_html(i18n.t(RULES_EMPTY_BODY)))
        rules_meta = i18n.t(FRAME_COLOURS_RULES_EMPTY_META)
    else:
        rules_list_html = _rule_list_html(rule_rows)
        rule_count = len(rule_rows)
        if rule_count == 1:
            rules_meta = i18n.t(FRAME_COLOURS_RULES_COUNT_SINGULAR)
        else:
            rules_meta = i18n.t(FRAME_COLOURS_RULES_COUNT_PLURAL_TEMPLATE) % rule_count
    # The rule-add disclosure's <summary> reuses RULE_ADD_BUTTON_TEXT
    # rather than inventing a new summary string.
    rule_add_html = (
        '<details class="rule-add"><summary>%s</summary>%s%s</details>'
    ) % (
        escape_html(i18n.t(RULE_ADD_BUTTON_TEXT)),
        _rule_add_form_html(),
        _rule_suggestion_chips_html(ctx.get("state_dir")),
    )
    rules_row = _usage_row_html(
        COLOUR_USAGE_RULES,
        _usage_row_summary_html(COLOUR_USAGE_RULES, None, meta_text=rules_meta),
        rules_caption_html + rules_list_html + rule_add_html + rules_how_combine_html,
        extra_class="usage-row--secondary")

    rows_html = departures_row + arrivals_row + calendar_row + rules_row
    card_html = (
        '<div class="page-section aspect-card" %s="%s">'
        '<h2 class="text-heading" id="%s">%s</h2>'
        "%s"
        "%s"
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(i18n.t(ASPECT_HEADING)),
        escape_html(ASPECT_HEADING_ID), escape_html(i18n.t(ASPECT_HEADING)),
        live_preview_html,
        rows_html,
    )
    # The disconnect form is a data-only sibling of the whole
    # .aspect-card div, never nested inside it or the Calendar row.
    return card_html + calendar_disconnect_form_html


def runway_fieldset(
        current_runway_id, images_available=(), errors=None, submitted=None,
        next_wake_clock=None):
    """One selectable `.runway-card` per `device_config.RUNWAYS` entry.
    The entire card (`<label>`) is the hit target, wrapping a
    visually-hidden (never `display:none`) native radio so keyboard/
    no-JS selection still works. An `<img>` renders when `runway_id` is
    a member of `images_available`.

    Named by an `<h2>` rather than a `<legend>`, since a `<legend>`
    outside a `<fieldset>` has no accessible group semantics; the
    `.runway-row` wrapper carries `role="radiogroup"` instead.
    `errors`/`submitted` repopulate the selected card on a rejected
    save. Each radio carries an explicit `form=` attribute so the group
    keeps posting even when rendered as a form sibling.
    """
    effective_runway_id = _submitted_or_current(
        submitted, "tracked_runway", current_runway_id)
    cards = []
    for runway_id in device_config.RUNWAY_IDS:
        selected = runway_id == effective_runway_id
        checked = " checked" if selected else ""
        card_class = (
            "runway-card runway-card--selected" if selected else "runway-card")
        # Emitted only on the saved card.
        current_attr_html = (
            ' %s="%s"' % (CURRENT_BADGE_ATTR, escape_html(i18n.t(CURRENT_BADGE_LABEL)))
            if selected else "")
        label = i18n.t(device_config.runway_label(runway_id))
        escaped_id = escape_html(runway_id)
        image_html = ""
        if runway_id in images_available:
            image_html = (
                '<img class="runway-card__image" src="%s%s.png" alt="%s">'
                % (
                    RUNWAY_IMAGE_ROUTE_PREFIX, escaped_id,
                    escape_html(i18n.t(RUNWAY_IMAGE_ALT_TEMPLATE) % label),
                )
            )
        cards.append(
            '<label class="%s"%s>'
            '<input type="radio" name="tracked_runway" value="%s" class="visually-hidden" '
            'form="%s"%s>'
            '<span class="runway-card__number">%s</span>'
            "%s"
            '<span class="runway-card__check">%s<span class="visually-hidden">%s</span></span>'
            "</label>"
            % (
                card_class, current_attr_html,
                escaped_id, SETTINGS_FORM_ID, checked,
                escape_html(label),
                image_html, layout.icon_html("icon-check"),
                escape_html(i18n.t("Selected")),
            )
        )
    runway_error_html = _field_error_html(errors, "tracked_runway", "tracked-runway")
    row_attr = 'role="radiogroup" aria-labelledby="%s"%s' % (
        escape_html(RUNWAY_GROUP_HEADING_ID), _describedby_attr(RUNWAY_SECTION_CAPTION_ID))
    return (
        '<div class="theme-status" %s="%s">'
        '<h2 class="text-heading" id="%s">%s</h2>'
        '<p class="text-label section-caption" id="%s">%s</p>'
        '<div class="runway-row" %s>%s</div>'
        "%s"
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(i18n.t("Runway")),
        escape_html(RUNWAY_GROUP_HEADING_ID),
        escape_html(i18n.t("Runway")),
        escape_html(RUNWAY_SECTION_CAPTION_ID),
        escape_html(_with_next_wake(i18n.t(RUNWAY_SECTION_CAPTION), next_wake_clock)),
        row_attr,
        "".join(cards),
        runway_error_html,
    )


def led_group(current_led_enabled, errors=None, submitted=None, next_wake_clock=None):
    """The Diagnostic LED settings group: a sibling of Theme and
    Runway in the merged settings form, with no `<fieldset>`/`<legend>`
    (named by an `<h2>` instead) and no `role="radiogroup"` (a single
    checkbox gets `aria-describedby` instead).

    The `<label>` carries `class="settings-checkbox"`: unclassed, it
    would fall through to the global `input, select` rule and paint an
    oversized filled box. `errors`/`submitted` repopulate this
    checkbox's `checked` state from a rejected save.
    """
    is_on = current_led_enabled is True
    error_html = _field_error_html(errors, "led_enabled", "led-enabled")
    # Hint-then-error order: the switch's own state span, then the
    # group's caption hint, then the error anchor when there is one.
    described_by = QUICK_LED_STATE_ID + " " + LED_SECTION_CAPTION_ID
    if errors and errors.get("led_enabled"):
        described_by = described_by + " led-enabled-error"
    return (
        '<div class="theme-status" %s="%s" %s>'
        '<h2 class="text-heading" id="%s">%s</h2>'
        '<p class="text-label section-caption" id="%s">%s</p>'
        '<div class="settings-switch-row">%s%s</div>'
        "%s"
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(i18n.t(LED_SECTION_HEADING)),
        layout.QUICK_SWITCH_REGION_ATTR,
        escape_html(QUICK_LED_LABEL_ID), escape_html(i18n.t(LED_SECTION_HEADING)),
        escape_html(LED_SECTION_CAPTION_ID),
        escape_html(_with_next_wake(i18n.t(LED_SECTION_CAPTION), next_wake_clock)),
        layout.quick_switch_state_html(
            QUICK_LED_STATE_ID,
            i18n.t(layout.QUICK_ACTION_ON_TEXT), i18n.t(layout.QUICK_ACTION_OFF_TEXT), is_on),
        layout.quick_switch_html(
            "", "", is_on, QUICK_LED_LABEL_ID,
            described_by, form_id=QUICK_LED_FORM_ID),
        error_html,
    )


QUICK_LED_FORM_ID = "quick-led"
QUICK_LED_LABEL_ID = "quick-switch-led-label"
QUICK_LED_STATE_ID = "quick-switch-led-state"


def quick_led_form_html(current_led_enabled):
    """The Diagnostic LED switch's own empty `<form>`, a sibling of the
    settings form: `led_group()` renders inside it, and a `<form>` can
    never nest inside another, so the button reaches this element
    across the DOM via `form="{QUICK_LED_FORM_ID}"`.

    The posted `state` is the opposite of the stored one, so a press
    with scripts blocked switches the LED rather than re-asserting its
    current state; `quick-switch.js` keeps that field inverted after an
    optimistic flip. `data-quick-switch` is the handshake both
    `dirty-state.js` and `quick-switch.js` key on.
    """
    next_state = (
        layout.QUICK_STATE_OFF if current_led_enabled is True else layout.QUICK_STATE_ON)
    return (
        '<form method="post" action="/quick/led" id="%s" '
        'class="quick-action__form" data-quick-switch>'
        '<input type="hidden" name="state" value="%s">'
        '<input type="hidden" name="return_to" value="%s">'
        "</form>"
    ) % (
        escape_html(QUICK_LED_FORM_ID),
        escape_html(next_state),
        escape_html(layout.DEVICE_ROUTE),
    )


# The quiet window always runs forward from start, through midnight if
# necessary: 23:00 to 07:00 is eight hours going forward and sixteen
# going the other way, and an `end - start` implementation would draw
# the wrong one. The shipped default window is exactly this case.
#
# The same shape regex feeds both the text and the drawn geometry, so a
# future loosening cannot apply to one and not the other.
_HHMM_RE = re.compile(r"^\d{2}:\d{2}$")

QUIET_WINDOW_MINUTES_PER_DAY = 24 * 60

# `start_fraction`/`sweep_fraction` are turns of the ring (0 at twelve
# o'clock, growing clockwise, matching companion/draw.py's circle
# helpers); `minutes` is the same span in whole minutes, the single
# source both a card's printed duration and its drawn arc read from.
QuietWindowSpan = collections.namedtuple(
    "QuietWindowSpan", "start_fraction sweep_fraction minutes")


def quiet_window_minute_of_day(value):
    """`value` ("HH:MM") as whole minutes since local midnight, or `None`
    when it is not a real time of day. Never raises.

    `None` is the "render nothing" signal: an unset or unparseable
    stored window must draw no arc rather than a plausible-looking one
    starting at midnight. Values reaching here are already
    server-validated by `handle_post()`; this is the second gate.

    The shape regex alone is not enough: `^\\d{2}:\\d{2}$` accepts
    "99:99", which would become minute 5,999 of a 1,440-minute day.
    """
    if not value or not _HHMM_RE.match(str(value)):
        return None
    hours, minutes = (int(part) for part in str(value).split(":"))
    if hours > 23 or minutes > 59:
        return None
    return hours * 60 + minutes


def quiet_window_span(start_hm, end_hm):
    """The quiet window as a `QuietWindowSpan`, or `None` when either
    end does not parse. Never raises. Always forward from `start_hm`,
    through midnight if necessary (a modulo, not a subtraction): 23:00
    to 07:00 is 480 minutes, and 07:00 to 23:00 is its complement, 960.

    Equal start and end is a zero-length window, not a whole day,
    matching `server.device_config.seconds_until_quiet_hours_end()`'s
    contract — the largest expressible window is therefore 1439
    minutes, matching the dial's own `aria-valuemax`.
    """
    start = quiet_window_minute_of_day(start_hm)
    end = quiet_window_minute_of_day(end_hm)
    if start is None or end is None:
        return None
    minutes = (end - start) % QUIET_WINDOW_MINUTES_PER_DAY
    return QuietWindowSpan(
        start / float(QUIET_WINDOW_MINUTES_PER_DAY),
        minutes / float(QUIET_WINDOW_MINUTES_PER_DAY),
        minutes)


def _normalised_time_html(value):
    """The normalised 24h value rendered as a visible, `aria-hidden`
    sibling beside a native `<input type="time">`, since a native time
    control formats from the browser's own locale (e.g. "23:00" as
    "11:00 PM" in en-US) with no way to tell it matches a preset.

    Renders nothing for a falsy/unparseable value. The span carries
    `QUIET_NORMALISED_TIME_ATTR`, a hook `value-controls.js` reads to
    hide it on a browser that is already unambiguous.
    """
    if not value or not _HHMM_RE.match(str(value)):
        return ""
    return (
        ' <span class="text-label field-inline-value" %s aria-hidden="true">%s</span>'
    ) % (QUIET_NORMALISED_TIME_ATTR, escape_html(value))


# Class names as constants rather than literals at the emission site: a
# class that exists in Python and nowhere in style.css paints nothing,
# and a check scans emitted markup against the stylesheet for exactly
# that.
QUIET_DIAL_CLASS = "quiet-dial"
QUIET_DIAL_RING_CLASS = "quiet-dial__ring"
QUIET_DIAL_DAY_CLASS = "quiet-dial__day"
QUIET_DIAL_ARC_CLASS = "quiet-dial__arc"
QUIET_DIAL_HOUR_CLASS = "quiet-dial__hour"
QUIET_DIAL_READOUT_CLASS = "quiet-dial__readout"

QUIET_PRESET_ROW_CLASS = "quiet-preset-row"
QUIET_TIMES_ROW_CLASS = "quiet-times-row"

# The stable hook _normalised_time_html() marks its own span with, so
# value-controls.js can find and hide only it, never the wake-interval
# unit sibling that shares .field-inline-value but carries no hook.
QUIET_NORMALISED_TIME_ATTR = "data-normalised-time"

# CSS pixels, with an explicit intrinsic size so the <svg> never falls
# back to the format's own 300x150 default.
QUIET_DIAL_SIZE = 176
# 176 - 14 - 3 = 78 (SIZE // 2 - STROKE // 2 - CLEARANCE): chosen so the
# radius lands on a whole number, since a rounding tail would make every
# recomputed-from-markup check invent a tolerance to hide it.
QUIET_DIAL_STROKE = 14
# Clear space between the stroke's outer edge and the viewBox edge: a
# stroked arc extends half its stroke width past the nominal radius.
QUIET_DIAL_CLEARANCE = 3
QUIET_DIAL_RADIUS = QUIET_DIAL_SIZE // 2 - QUIET_DIAL_STROKE // 2 - QUIET_DIAL_CLEARANCE

# The three property names value-controls.js's generic pair seam reads
# or writes, decided here since every such name is a server decision.
QUIET_DIAL_PAIR_ATTR = "data-value-pair"
QUIET_DIAL_PAIR_PROPERTY_ATTR = "data-value-pair-property"

# A dict rather than three top-level string constants: a constant whose
# value begins with "--" trips test_i18n.py's untranslated-string scan
# (a leading "--" is not a valid identifier start, so the scanner's
# bare-identifier exclusion never reaches it); a dict value is scanned
# under a separate exclusion that does reach it.
QUIET_DIAL_PAIR_PROPERTIES = {
    "start": "--quiet-start-fraction",
    "end": "--quiet-end-fraction",
    "sweep": "--quiet-sweep-fraction",
}

# Four anchor hours, not twenty-four: the quarter turns are the only
# hours a reader resolves at a glance, and twenty-four labels on this
# ring is illegible at the contract's minimum width. 00 is marked
# because midnight is the case this control's arithmetic exists for.
#
# Each hour is paired with its own modifier class rather than templated
# from one "quiet-dial__hour--%d" constant: test_i18n.py strips a
# literal's format specs before checking whether it is a bare
# identifier, so the templated form would read as untranslated
# user-facing copy and fail that scan.
QUIET_DIAL_LABELLED_HOURS = (
    (0, "quiet-dial__hour--0"),
    (6, "quiet-dial__hour--6"),
    (12, "quiet-dial__hour--12"),
    (18, "quiet-dial__hour--18"),
)

# "23:00 → 07:00 · 8h". No letters of its own (the duration's unit
# comes from layout.duration_text(), which speaks both languages), so
# it needs no catalogue entry.
QUIET_DIAL_READOUT_TEMPLATE = "%s → %s · %s"

# A full turn in degrees, and the quarter turn that moves <circle>'s
# three-o'clock dash origin to twelve o'clock (the same correction
# draw.py's ring_gauge() applies, restated here since this drawing
# additionally rotates by the window's own start).
_QUIET_DIAL_FULL_TURN_DEG = 360.0
_QUIET_DIAL_TWELVE_OCLOCK_DEG = -90.0


def quiet_dial_svg(span):
    """The 24h ring as one `<svg>`: a full-circumference day, plus the
    quiet arc when `span` describes one. Never raises; server-drawn, so
    a scripts-blocked visitor still sees the saved window correctly.

    No arc for `span is None` or a zero-length window: a zero-length
    dash would render as a dot, reading as "a few minutes" rather than
    "no window". `fill="none"`/`stroke-width` are presentation
    attributes, deliberately not stylesheet declarations, since a CSS
    rule would beat them and flatten the derived geometry.
    """
    centre = QUIET_DIAL_SIZE // 2
    shapes = [draw.circle(QUIET_DIAL_DAY_CLASS, centre, centre, QUIET_DIAL_RADIUS, attrs={
        "fill": "none",
        "stroke-width": QUIET_DIAL_STROKE,
    })]
    if span is not None and span.minutes > 0:
        shapes.append(draw.circle(
            QUIET_DIAL_ARC_CLASS, centre, centre, QUIET_DIAL_RADIUS, attrs={
                "fill": "none",
                "stroke-width": QUIET_DIAL_STROKE,
                "stroke-dasharray": draw.unit_circle_dash_array(
                    span.sweep_fraction, QUIET_DIAL_RADIUS),
                # Twelve o'clock plus the window's own start, clockwise —
                # <circle>'s dash origin is three o'clock and grows
                # clockwise already.
                "transform": "rotate(%.4f %d %d)" % (
                    _QUIET_DIAL_TWELVE_OCLOCK_DEG
                    + _QUIET_DIAL_FULL_TURN_DEG * span.start_fraction,
                    centre, centre),
            }))
    return (
        '<svg class="%s" viewBox="0 0 %d %d" width="%d" height="%d" '
        'aria-hidden="true" focusable="false">%s</svg>'
    ) % (
        escape_html(QUIET_DIAL_RING_CLASS), QUIET_DIAL_SIZE, QUIET_DIAL_SIZE,
        QUIET_DIAL_SIZE, QUIET_DIAL_SIZE, "".join(shapes),
    )


def quiet_dial_html(span, handles_html=""):
    """The ring and its four anchor-hour labels, as one positioned block.
    Labels are HTML outside the `<svg>`, not `<text>` inside it, so a
    viewBox never has to contain drawn text, and they stay a constant
    CSS size. `handles_html` renders last (document order is paint
    order). This `<div>` is the pair seam's shared ancestor: the
    handles' fractions publish here, from the same `span` triple
    `quiet_dial_svg()` draws from, so the two geometries never disagree.
    """
    hours_html = "".join(
        '<span class="text-label %s %s" aria-hidden="true">%02d</span>' % (
            escape_html(QUIET_DIAL_HOUR_CLASS), escape_html(modifier_class), hour)
        for hour, modifier_class in QUIET_DIAL_LABELLED_HOURS)
    pair_attrs = ""
    if span is not None:
        end_fraction = (span.start_fraction + span.sweep_fraction) % 1.0
        pair_attrs = (
            ' %s="%s" style="%s: %.6f; %s: %.6f; %s: %.6f;"'
        ) % (
            QUIET_DIAL_PAIR_ATTR, escape_html(QUIET_DIAL_PAIR_PROPERTIES["sweep"]),
            QUIET_DIAL_PAIR_PROPERTIES["start"], span.start_fraction,
            QUIET_DIAL_PAIR_PROPERTIES["end"], end_fraction,
            QUIET_DIAL_PAIR_PROPERTIES["sweep"], span.sweep_fraction,
        )
    return '<div class="%s"%s>%s%s%s</div>' % (
        escape_html(QUIET_DIAL_CLASS), pair_attrs, quiet_dial_svg(span), hours_html, handles_html)


# Everything below renders inside the `.js` gate; the ring, the
# readout, the three presets and both time inputs all survive with
# scripts blocked, and only the dragging is hidden without script.
QUIET_DIAL_HANDLE_LAYER_CLASS = "quiet-dial__handles"
QUIET_DIAL_HANDLE_CLASS = "quiet-dial__handle"
# The box value-controls.js measures the pointer angle against: the
# ring's own square, so the angle is measured about the ring's centre.
QUIET_DIAL_HANDLE_TRACK_CLASS = "quiet-dial__handle-track"

# The steering range, in minutes since local midnight. The maximum is
# 1439, not 1440: 1440 would make 00:00 and "24:00" the same instant
# with two values, and the End key would write a time no
# <input type="time"> accepts.
QUIET_DIAL_HANDLE_MIN = 0
QUIET_DIAL_HANDLE_MAX = QUIET_WINDOW_MINUTES_PER_DAY - 1

# The native <input type="range"> keyboard model: arrows move one step,
# Page keys move ten steps, Home/End go to the two ends. Ten steps of
# 15 minutes is 10.4% of the day, matching a native range control's
# Page-key proportion rather than a fixed value — a per-control page
# size would be a second keyboard model on the second settings page.
QUIET_DIAL_HANDLE_STEP = 15

# The two ends, each with the field it steers and the accessible name
# that says WHICH end it is. aria-valuetext carries the time itself and
# nothing else (layout.VALUE_CONTROL_TEXT_TOKEN alone, no sentence around
# it): a screen reader reading "one thousand three hundred and eighty"
# instead of "23:00" is the whole reason aria-valuetext exists, and
# repeating the label on every arrow press is noise, not information.
QUIET_DIAL_START_LABEL = "Quiet hours start"
QUIET_DIAL_END_LABEL = "Quiet hours end"


def quiet_dial_handle_fraction(minute):
    """`minute` as the 0..1 fraction of a turn the stylesheet positions
    the handle from — deliberately the same formula value-controls.js's
    `paint()` uses, `(value - min) / (max - min)`, rather than the
    `minute / 1440` the arc is drawn from. The server paints the handle
    once and the script repaints it on every step; using a formula that
    only agrees in theory would make it jump imperceptibly on the first
    arrow press and never quite line up with the arc again.
    """
    return minute / float(QUIET_DIAL_HANDLE_MAX)


def quiet_dial_handles_html(start_hm, end_hm):
    """The two drag handles, each in its own `.js`-gated wrapper: a
    real `<button type="button">` (never a bare `<div>`, and never a
    plain `<button>`, which would default to form submit on Enter).

    Driven from the two native inputs, never from state of its own, so
    the existing presets already move the handles with no code of
    their own. No handle for an end that does not parse. No minimum
    separation between the two ends (a zero-length window is a real
    state); z-order is document order, so the end handle wins a
    pointer-down where they overlap, and moving it separates the pair.
    """
    handles = []
    for value, field, label, pair_property in (
            (start_hm, "quiet_hours_start", QUIET_DIAL_START_LABEL,
             QUIET_DIAL_PAIR_PROPERTIES["start"]),
            (end_hm, "quiet_hours_end", QUIET_DIAL_END_LABEL,
             QUIET_DIAL_PAIR_PROPERTIES["end"])):
        minute = quiet_window_minute_of_day(value)
        if minute is None:
            continue
        handles.append((
            '<div class="value-control %s %s" %s %s="%s" %s="%s" %s="%d" %s="%d" %s="%d"'
            ' %s="angular" %s="%s" %s="%s" %s="%s" style="--value-fraction: %.6f">'
            '<span class="value-control__track %s" %s></span>'
            '<button type="button" class="value-control__handle control-hit-area %s" %s'
            ' role="slider" aria-valuemin="%d" aria-valuemax="%d" aria-valuenow="%d"'
            ' aria-valuetext="%s" aria-label="%s"></button>'
            "</div>"
        ) % (
            escape_html(QUIET_DIAL_HANDLE_LAYER_CLASS), escape_html(layout.JS_GATE_CLASS),
            layout.VALUE_CONTROL_ATTR,
            layout.VALUE_CONTROL_FIELD_ATTR, escape_html(field),
            layout.VALUE_CONTROL_FORM_ATTR, escape_html(SETTINGS_FORM_ID),
            layout.VALUE_CONTROL_MIN_ATTR, QUIET_DIAL_HANDLE_MIN,
            layout.VALUE_CONTROL_MAX_ATTR, QUIET_DIAL_HANDLE_MAX,
            layout.VALUE_CONTROL_STEP_ATTR, QUIET_DIAL_HANDLE_STEP,
            layout.VALUE_CONTROL_GEOMETRY_ATTR,
            layout.VALUE_CONTROL_FORMAT_ATTR, escape_html(layout.VALUE_CONTROL_FORMAT_CLOCK),
            layout.VALUE_CONTROL_TEXT_ATTR, escape_html(layout.VALUE_CONTROL_TEXT_TOKEN),
            # Names which of quiet_dial_html()'s ancestor properties
            # this handle publishes its fraction under; value-controls.js
            # finds that ancestor via ancestorWith().
            QUIET_DIAL_PAIR_PROPERTY_ATTR, escape_html(pair_property),
            quiet_dial_handle_fraction(minute),
            escape_html(QUIET_DIAL_HANDLE_TRACK_CLASS), layout.VALUE_CONTROL_TRACK_ATTR,
            escape_html(QUIET_DIAL_HANDLE_CLASS), layout.VALUE_CONTROL_HANDLE_ATTR,
            QUIET_DIAL_HANDLE_MIN, QUIET_DIAL_HANDLE_MAX, minute,
            escape_html(value), escape_html(i18n.t(label)),
        ))
    return "".join(handles)


# layout.DURATION_ATTRS' four English wordings, in the same s/m/h/d
# order, zipped against that tuple below so an attribute name and its
# translated wording are always written together.
_QUIET_DIAL_DURATION_TEXTS = (
    layout.DURATION_SECONDS_TEXT, layout.DURATION_MINUTES_TEXT,
    layout.DURATION_HOURS_TEXT, layout.DURATION_DAYS_TEXT,
)


def quiet_dial_readout_html(start_hm, end_hm, span):
    """"23:00 → 07:00 · 8h" — the window in words, or "" when `span` is
    None. `aria-hidden="true"`, not a live region: dragging fires
    continuously, and the focused handle's own `aria-valuetext` is
    already the debounced announcement path.

    The duration comes from `layout.duration_text()`, this app's one
    length-of-time ladder, coarse by construction (a 90-minute window
    reads "1h"). Three children, not one text node: the two endpoint
    spans carry the `data-value-readout` seam so `value-controls.js`
    can substitute "HH:MM" client-side; the duration span carries all
    four `layout.DURATION_ATTRS` translated wordings, so the client
    substitutes a quantity into the right bucket with no language logic
    of its own.
    """
    if span is None:
        return ""
    duration_attrs_html = "".join(
        ' %s="%s"' % (attr, escape_html(i18n.t(text)))
        for attr, text in zip(layout.DURATION_ATTRS, _QUIET_DIAL_DURATION_TEXTS))
    return (
        '<p class="time-value %s" aria-hidden="true">'
        '<span %s="quiet_hours_start" %s="%s" %s="%s">%s</span>'
        ' → '
        '<span %s="quiet_hours_end" %s="%s" %s="%s">%s</span>'
        ' · '
        '<span %s="quiet_hours_start" %s="%d"%s>%s</span>'
        "</p>"
    ) % (
        escape_html(QUIET_DIAL_READOUT_CLASS),
        layout.VALUE_CONTROL_READOUT_ATTR,
        layout.VALUE_CONTROL_READOUT_FORMAT_ATTR, escape_html(layout.VALUE_CONTROL_FORMAT_CLOCK),
        layout.VALUE_CONTROL_READOUT_TEXT_ATTR,
        escape_html(layout.VALUE_CONTROL_TEXT_TOKEN), escape_html(start_hm),
        layout.VALUE_CONTROL_READOUT_ATTR,
        layout.VALUE_CONTROL_READOUT_FORMAT_ATTR, escape_html(layout.VALUE_CONTROL_FORMAT_CLOCK),
        layout.VALUE_CONTROL_READOUT_TEXT_ATTR,
        escape_html(layout.VALUE_CONTROL_TEXT_TOKEN), escape_html(end_hm),
        layout.VALUE_CONTROL_READOUT_ATTR,
        layout.VALUE_CONTROL_READOUT_BASE_ATTR, quiet_window_minute_of_day(start_hm),
        duration_attrs_html,
        escape_html(layout.duration_text(span.minutes * 60)),
    )


def quiet_hours_group(current_start, current_end, errors=None, submitted=None):
    """The Quiet hours settings card: a sibling of the settings form,
    never a literal descendant; both time inputs submit via `form=`.

    Neither time input is ever `disabled`: they stay interactive
    whether or not Quiet hours is on, since the Frame strip is the only
    on/off control. The three presets are client-side-only
    `type="button"` elements dirty-state.js writes into the two time
    fields, inert with no script. `errors`/`submitted` repopulate both
    controls; the server-side HH:MM gate in `handle_post()` is the real
    validation.
    """
    # The group's single hint links to both time inputs (there is no
    # separate per-field hint for Start vs End).
    effective_start = _submitted_or_current(submitted, "quiet_hours_start", current_start)
    start_error_attrs = _field_error_attrs(
        errors, "quiet_hours_start", "quiet-hours-start", hint_id=QUIET_HOURS_SECTION_CAPTION_ID)
    start_error_html = _field_error_html(errors, "quiet_hours_start", "quiet-hours-start")

    effective_end = _submitted_or_current(submitted, "quiet_hours_end", current_end)
    end_error_attrs = _field_error_attrs(
        errors, "quiet_hours_end", "quiet-hours-end", hint_id=QUIET_HOURS_SECTION_CAPTION_ID)
    end_error_html = _field_error_html(errors, "quiet_hours_end", "quiet-hours-end")

    # The preset row is a segmented control with no selected state:
    # these buttons are momentary actions that write into the time
    # fields, not a persistent choice.
    preset_row_html = (
        '<div class="%s">'
        '<button type="button" %s data-preset-start="%s" data-preset-end="%s">%s</button>'
        '<button type="button" %s data-preset-start="%s" data-preset-end="%s">%s</button>'
        '<button type="button" %s data-preset-enabled="0">%s</button>'
        "</div>"
    ) % (
        QUIET_PRESET_ROW_CLASS,
        QUIET_HOURS_PRESET_ATTR,
        escape_html(QUIET_HOURS_PRESET_NIGHT_START), escape_html(QUIET_HOURS_PRESET_NIGHT_END),
        escape_html(i18n.t(QUIET_HOURS_PRESET_NIGHT_LABEL)),
        QUIET_HOURS_PRESET_ATTR,
        escape_html(QUIET_HOURS_PRESET_WORKDAY_START), escape_html(QUIET_HOURS_PRESET_WORKDAY_END),
        escape_html(i18n.t(QUIET_HOURS_PRESET_WORKDAY_LABEL)),
        QUIET_HOURS_PRESET_ATTR,
        escape_html(i18n.t(QUIET_HOURS_PRESET_ALWAYS_ON_LABEL)),
    )

    # `<html lang>` already carries the site's language, but a native
    # time control formats itself from the browser's own locale, not
    # the document's — this attribute is the standards-level request;
    # `_normalised_time_html()` is the fallback that holds when a
    # browser ignores it.
    #
    # The ring reads before the controls that change it (a picture of
    # what is set, then how to change it), so it renders between the
    # caption and the presets rather than after the fields.
    #
    # Drawn from the same effective values the two inputs are populated
    # from, never from `current_start`/`current_end` directly, so on a
    # rejected save the arc shows what was submitted, not what is
    # stored.
    dial_span = quiet_window_span(effective_start, effective_end)
    dial_html = quiet_dial_html(
        dial_span, quiet_dial_handles_html(effective_start, effective_end))
    readout_html = quiet_dial_readout_html(effective_start, effective_end, dial_span)

    site_lang = prefs.current_lang()
    caption_html = i18n.t(QUIET_HOURS_SECTION_CAPTION)
    # Each field gets its own unclassed grid cell holding its label and
    # its own error paragraph together, so an error never displaces its
    # sibling column under the two-column grid.
    return (
        '<div class="theme-status" %s="%s">'
        '<h2 class="text-heading" id="%s">%s</h2>'
        '<p class="text-label section-caption" id="%s">%s</p>'
        "%s%s"
        "%s"
        '<div class="%s">'
        '<div><label>%s <input type="time" name="quiet_hours_start" value="%s" required'
        ' lang="%s" form="%s"%s>%s</label>%s</div>'
        '<div><label>%s <input type="time" name="quiet_hours_end" value="%s" required'
        ' lang="%s" form="%s"%s>%s</label>%s</div>'
        "</div>"
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(i18n.t(QUIET_HOURS_SECTION_HEADING)),
        escape_html(QUIET_HOURS_GROUP_HEADING_ID),
        escape_html(i18n.t(QUIET_HOURS_SECTION_HEADING)),
        escape_html(QUIET_HOURS_SECTION_CAPTION_ID),
        escape_html(caption_html),
        dial_html, readout_html,
        preset_row_html,
        QUIET_TIMES_ROW_CLASS,
        escape_html(i18n.t("Start")),
        escape_html(effective_start), escape_html(site_lang), SETTINGS_FORM_ID, start_error_attrs,
        _normalised_time_html(effective_start),
        start_error_html,
        escape_html(i18n.t("End")),
        escape_html(effective_end), escape_html(site_lang), SETTINGS_FORM_ID, end_error_attrs,
        _normalised_time_html(effective_end),
        end_error_html,
    )


def wake_gauge_interval_s(current_wake_interval_s, submitted=None):
    """The interval the two gauges describe, as an int inside
    `[WAKE_INTERVAL_MIN_S, WAKE_INTERVAL_MAX_S]`, or `None` (nothing
    renders). On a rejected save, echoes the raw submitted string
    rather than the stored value so the gauges match the field being
    fixed — but an out-of-range echo ("7", "99999") still renders no
    gauge. Total by construction: never raises.
    """
    if submitted is not None and "wake_interval_s" in submitted:
        raw = submitted["wake_interval_s"]
        try:
            candidate = int(str(raw).strip())
        except (TypeError, ValueError):
            return None
    elif isinstance(current_wake_interval_s, int) and not isinstance(
            current_wake_interval_s, bool):
        candidate = current_wake_interval_s
    else:
        return None
    if device_config.WAKE_INTERVAL_MIN_S <= candidate <= device_config.WAKE_INTERVAL_MAX_S:
        return candidate
    return None


def _wake_minutes(interval_s):
    """`interval_s` as a whole number of minutes, rounded up.

    Both sentences are claims about a bound: a 90-second cadence bounds
    the wait at a minute and a half, and `90 // 60` would print "at
    most 1 min", which is false. The ceiling prints "at most 2 min",
    true and merely loose. This control's own step is a whole minute;
    the ceiling matters for values already on disk from before it
    existed.
    """
    return -(-int(interval_s) // WAKE_GAUGE_SECONDS_PER_MINUTE)


def wake_freshness_text(interval_s):
    """"A plane reaches the frame at most 5 min after it passes." — the
    bound, or `""` when there is no interval to bound.

    "At most" is the whole sentence: the frame learns about a plane at
    its next wake, so a plane that passes one instant after a wake
    appears one whole interval later and never later — true for every
    interval, by construction, unlike a claim about typical behaviour.
    """
    if interval_s is None:
        return ""
    return i18n.t(WAKE_FRESHNESS_TEXT).replace(
        layout.VALUE_CONTROL_TEXT_TOKEN, str(_wake_minutes(interval_s)))


def wake_battery_observed_text(interval_s, battery_rows=None):
    """The battery half: an absolute figure only when observed history
    supports one, else the named "not enough history yet" sentence;
    `""` when there is no interval. The figure is
    `battery.battery_life_estimate()`'s, never computed here — this
    only picks singular vs. plural wording. `battery_rows` defaults to
    `()`, the ordinary state of a fresh deployment.
    """
    if interval_s is None:
        return ""
    estimate = battery.battery_life_estimate(
        battery_rows or (), interval_s, interval_s)
    days = estimate["days_remaining"]
    if (estimate["trend"] == battery.LIFE_TREND_FALLING
            and isinstance(days, int) and not isinstance(days, bool)):
        template = WAKE_BATTERY_DAY_TEXT if days == 1 else WAKE_BATTERY_DAYS_TEXT
        return i18n.t(template).replace(
            layout.VALUE_CONTROL_TEXT_TOKEN, str(days))
    return i18n.t(WAKE_BATTERY_UNKNOWN_TEXT)


def wake_screen_off_text():
    """"While the screen is off the frame wakes every 5m instead,
    whatever this is set to."

    Rendered unconditionally beside the battery sentence, not gated on
    `display_enabled`: the clause is true whichever way that switch is
    set, and a qualifier shown only once the screen is off is one
    nobody reads in time.

    The cadence goes through `layout.duration_text()` since it is a
    fixed constant; the two sentences above do not, since their number
    changes as the slider moves and would need a second copy of the
    ladder in JavaScript to recompute client-side.
    """
    return i18n.t(WAKE_BATTERY_SCREEN_OFF_TEXT) % layout.duration_text(
        device_config.DISPLAY_OFF_SLEEP_S)


def wake_battery_relative_template(saved_interval_s):
    """The relative clause's template, saved cadence already written
    in and `#` standing for the proposed one — `""` with no usable
    saved cadence. "This setting wakes the frame every # min instead of
    every 10 min." — two whole cadences, not a ratio, since a ratio
    needs a decimal mark that differs between English and French.

    Routed through `battery.battery_life_estimate()`'s
    `relative_factor` for its guard: a clause built on a cadence that
    function would refuse (bool, non-numeric, non-positive) is about
    nothing.
    """
    estimate = battery.battery_life_estimate(
        (), saved_interval_s, saved_interval_s)
    if estimate["relative_factor"] is None:
        return ""
    return i18n.t(WAKE_BATTERY_INSTEAD_TEXT) % _wake_minutes(saved_interval_s)


def wake_battery_relative_text(proposed_interval_s, saved_interval_s):
    """The relative clause as the server would render it for a given
    proposal — `""` when the two cadences are equal, the case every
    real page render produces. The one definition of this sentence in
    Python; `test_browser_ux.py` compares the script's own live output
    against it. Never carries a days figure: that half stays
    server-rendered, deliberately unreachable from script.
    """
    template = wake_battery_relative_template(saved_interval_s)
    if not template:
        return ""
    estimate = battery.battery_life_estimate(
        (), saved_interval_s, proposed_interval_s)
    factor = estimate["relative_factor"]
    if factor is None or factor == 1.0:
        return ""
    return template.replace(
        layout.VALUE_CONTROL_TEXT_TOKEN, str(_wake_minutes(proposed_interval_s)))


def wake_battery_rows(state_dir, now=None):
    """`WAKE_BATTERY_WINDOW_DAYS` of daily battery averages for the
    battery sentence, or `()` on any read failure or absent state dir.
    Never raises: a settings page that 500s because a battery history
    table could not be opened would be worse than a card that says it
    has no history yet.

    Read here rather than threaded through `ctx`: this is the only card
    that needs the series, and `page_context()` runs on every
    authenticated render.
    """
    if not state_dir:
        return ()
    try:
        with history_db.open_db(state_dir) as conn:
            return history_db.daily_battery_averages(
                conn, since=_wake_battery_cutoff_iso(now))
    except Exception:
        return ()


def _wake_battery_cutoff_iso(now):
    """The `since=` bound for the read above, or `None` when `now` does
    not parse — in which case `daily_battery_averages()` degrades to an
    UNBOUNDED read, health_page's own documented choice for the one
    input it does not control: more history rather than none.
    """
    parsed = layout.parse_iso(now)
    if parsed is None:
        return None
    return (parsed - timedelta(days=WAKE_BATTERY_WINDOW_DAYS)).isoformat(
        timespec="seconds")


def wake_gauges_html(interval_s, battery_rows=None):
    """The two gauges, as two muted sentences — `""` when there is no
    interval. Server-rendered, outside the `.js` gate: a script only
    updates these, never creates them, so a failed script leaves
    correct sentences. Neither is a live region — they'd re-announce
    continuously during a drag; the range announces itself natively.
    """
    if interval_s is None:
        return ""
    # The freshness paragraph is entirely live (its whole text is
    # arithmetic on the value); the battery paragraph's figure came
    # from observed history, so only its trailing span (two cadences,
    # no days figure) may be rewritten by script.
    return (
        '<p class="text-label section-caption %s" id="%s" %s="%s" %s="%s" %s="%d">%s</p>'
        '<p class="text-label section-caption %s" id="%s">%s %s '
        '<span %s="%s" %s="%s" %s="%d" %s="%d">%s</span></p>'
    ) % (
        escape_html(WAKE_GAUGE_CLASS), escape_html(WAKE_GAUGE_FRESHNESS_ID),
        layout.VALUE_CONTROL_READOUT_ATTR, escape_html(WAKE_INTERVAL_FIELD_NAME),
        layout.VALUE_CONTROL_READOUT_TEXT_ATTR,
        escape_html(i18n.t(WAKE_FRESHNESS_TEXT)),
        layout.VALUE_CONTROL_READOUT_SCALE_ATTR, WAKE_GAUGE_SECONDS_PER_MINUTE,
        escape_html(wake_freshness_text(interval_s)),

        escape_html(WAKE_GAUGE_CLASS), escape_html(WAKE_GAUGE_BATTERY_ID),
        escape_html(wake_battery_observed_text(interval_s, battery_rows)),
        escape_html(wake_screen_off_text()),
        layout.VALUE_CONTROL_READOUT_ATTR, escape_html(WAKE_INTERVAL_FIELD_NAME),
        layout.VALUE_CONTROL_READOUT_TEXT_ATTR,
        escape_html(wake_battery_relative_template(interval_s)),
        layout.VALUE_CONTROL_READOUT_SCALE_ATTR, WAKE_GAUGE_SECONDS_PER_MINUTE,
        # The base: the readout says nothing while the proposed value
        # is still the saved one (every page load and no-JS render).
        layout.VALUE_CONTROL_READOUT_BASE_ATTR, interval_s,
        escape_html(wake_battery_relative_text(interval_s, interval_s)),
    )


def wake_slider_html(interval_s):
    """The range input, inside the `.js` gate — `""` when there is no
    saved interval to start from.

    Carries no `name`: a named range would post a second value for
    `wake_interval_s`, and whichever arrived last would win silently.
    The `<input type="number">` is the only control on this card that
    posts; this one only writes into it via `value-controls.js`.

    Gated, since a range with no script drags and shows nothing; the
    gauges and number input are not gated. `min`/`max` come from
    `device_config`, never re-typed, so this control can never accept
    what `save_device_config()`'s own server-side re-check would reject.
    """
    if interval_s is None:
        return ""
    return (
        '<div class="%s %s" %s %s="%s" %s="%s" %s="%d" %s="%d" %s="%d">'
        '<input type="range" class="%s" %s value="%d" min="%d" max="%d" step="%d"'
        ' aria-label="%s" aria-describedby="%s %s">'
        "</div>"
    ) % (
        escape_html(WAKE_SLIDER_CLASS), escape_html(layout.JS_GATE_CLASS),
        layout.VALUE_CONTROL_ATTR,
        layout.VALUE_CONTROL_FIELD_ATTR, escape_html(WAKE_INTERVAL_FIELD_NAME),
        layout.VALUE_CONTROL_FORM_ATTR, SETTINGS_FORM_ID,
        layout.VALUE_CONTROL_MIN_ATTR, device_config.WAKE_INTERVAL_MIN_S,
        layout.VALUE_CONTROL_MAX_ATTR, device_config.WAKE_INTERVAL_MAX_S,
        layout.VALUE_CONTROL_STEP_ATTR, WAKE_SLIDER_STEP_S,
        escape_html(WAKE_SLIDER_INPUT_CLASS), layout.VALUE_CONTROL_INPUT_ATTR,
        interval_s,
        device_config.WAKE_INTERVAL_MIN_S, device_config.WAKE_INTERVAL_MAX_S,
        WAKE_SLIDER_STEP_S,
        escape_html(i18n.t(WAKE_SLIDER_LABEL)),
        escape_html(WAKE_GAUGE_FRESHNESS_ID), escape_html(WAKE_GAUGE_BATTERY_ID),
    )


def wake_interval_group(current_wake_interval_s, errors=None, submitted=None, next_wake_clock=None,
                        battery_rows=None):
    """The Wake interval settings group: a plain `<label>` wraps a
    single `<input type="number">` (no checkbox gate, unlike
    `quiet_hours_group()`). `min`/`max` come from `device_config`
    rather than re-typed literals.

    The `value` attribute is emitted only for an in-range, non-bool
    int; otherwise the placeholder carries the empty state — an
    out-of-range `value` fails HTML5 constraint validation and blocks
    the whole form's submission. On a rejected save the raw submitted
    string is echoed back verbatim instead, bypassing that guard so the
    user sees what they typed. `battery_rows` feeds the battery gauge,
    which appends after the error block.
    """
    if submitted is not None and "wake_interval_s" in submitted:
        raw_submitted = submitted["wake_interval_s"]
        value_attr = ' value="%s"' % escape_html(raw_submitted) if raw_submitted else ""
    else:
        value_attr = (
            ' value="%d"' % current_wake_interval_s
            if (
                isinstance(current_wake_interval_s, int)
                and not isinstance(current_wake_interval_s, bool)
                and device_config.WAKE_INTERVAL_MIN_S <= current_wake_interval_s <= device_config.WAKE_INTERVAL_MAX_S
            ) else "")
    error_attrs = _field_error_attrs(
        errors, "wake_interval_s", "wake-interval-s", hint_id=WAKE_INTERVAL_SECTION_CAPTION_ID)
    error_html = _field_error_html(errors, "wake_interval_s", "wake-interval-s")
    # One resolution of the gauges' and the slider's subject, so the
    # three can never describe different values.
    gauge_interval_s = wake_gauge_interval_s(current_wake_interval_s, submitted)
    return (
        '<div class="theme-status" %s="%s">'
        '<h2 class="text-heading">%s</h2>'
        '<p class="text-label section-caption" id="%s">%s</p>'
        # The label is its own element above the control (for=), not a
        # wrapping <label> — a wrapping label put its text and the
        # input on one line, misaligning this field against every
        # sibling field on the page.
        '<label for="%s">%s</label>'
        '<input type="number" id="%s" name="wake_interval_s" min="%d" max="%d"'
        ' placeholder="%s"%s%s>'
        # The unit as a sibling, aria-hidden: the label above already
        # names the unit, so repeating it would announce the fact twice.
        '<span class="text-label field-inline-value" aria-hidden="true">%s</span>'
        "%s"
        # The slider sits after the error message, not between it and
        # the field, so the error stays adjacent to the control it is
        # about. The gauges come last, since they describe what the
        # setting means, after the control that sets it.
        "%s%s"
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(i18n.t(WAKE_INTERVAL_SECTION_HEADING)),
        escape_html(i18n.t(WAKE_INTERVAL_SECTION_HEADING)),
        escape_html(WAKE_INTERVAL_SECTION_CAPTION_ID),
        escape_html(_with_next_wake(i18n.t(WAKE_INTERVAL_SECTION_CAPTION), next_wake_clock)),
        escape_html(WAKE_INTERVAL_INPUT_ID), escape_html(i18n.t("Wake interval (seconds)")),
        escape_html(WAKE_INTERVAL_INPUT_ID),
        device_config.WAKE_INTERVAL_MIN_S, device_config.WAKE_INTERVAL_MAX_S,
        escape_html(i18n.t(WAKE_INTERVAL_PLACEHOLDER_TEXT)),
        value_attr, error_attrs,
        escape_html(WAKE_INTERVAL_UNIT_LABEL),
        error_html,
        wake_slider_html(gauge_interval_s),
        wake_gauges_html(gauge_interval_s, battery_rows),
    )


def notifications_group(
        configured, current_battery_low, current_frame_silent,
        errors=None, submitted=None):
    """The Notifications settings card (Device scope only): battery-low
    and frame-silent checkboxes plus a write-only push-topic URL field.
    `configured` is a bare bool: the status row and the input (no
    `value` attribute, ever) never reveal the stored secret.

    The URL field waits on the page-wide Save; only "Send a test" is
    its own immediate-POST form, a sibling of `#settings-form`, since
    an immediate action must never nest inside the Save form.
    `errors`/`submitted` repopulate both checkboxes on a rejected save.
    """
    status_html = layout.status_row(
        "",
        i18n.t(
            NOTIFICATIONS_STATUS_CONFIGURED_VERDICT if configured
            else NOTIFICATIONS_STATUS_NOT_CONFIGURED_VERDICT),
        "",
        "ok" if configured else "warn")

    url_error_attrs = _field_error_attrs(
        errors, "notifications_topic_url", "notifications-topic-url",
        hint_id=NOTIFICATIONS_URL_HINT_ID)
    url_error_html = _field_error_html(
        errors, "notifications_topic_url", "notifications-topic-url")
    # Reuses the Calendar card's "How it works" summary label rather
    # than a second, near-duplicate string. Unconditional: the
    # storage/replacement fact is true whether or not a URL is stored yet.
    how_it_works_html = (
        '<details><summary>%s</summary><p class="text-body">%s</p></details>'
    ) % (
        escape_html(i18n.t(CALENDAR_HOW_IT_WORKS_SUMMARY)),
        escape_html(i18n.t(NOTIFICATIONS_URL_HOW_IT_WORKS_BODY)),
    )
    field_html = (
        '<div class="rule-add-form__field">'
        '<label for="notifications-topic-url">%s</label>'
        '<input type="text" id="notifications-topic-url" '
        'name="notifications_topic_url" autocomplete="off" '
        'spellcheck="false" maxlength="%s"%s>'
        '<p class="text-label section-caption" id="%s">%s</p>'
        "%s"
        "%s"
        "</div>"
    ) % (
        escape_html(i18n.t(NOTIFICATIONS_URL_FIELD_LABEL)),
        NOTIFICATIONS_URL_MAX_LEN, url_error_attrs,
        escape_html(NOTIFICATIONS_URL_HINT_ID), escape_html(i18n.t(NOTIFICATIONS_URL_HINT)),
        url_error_html,
        how_it_works_html,
    )
    if configured:
        field_html = (
            '<details class="calendar-url-disclosure"><summary>%s</summary>%s</details>'
        ) % (escape_html(i18n.t(NOTIFICATIONS_REPLACE_URL_SUMMARY)), field_html)

    battery_checked = _submitted_checkbox_checked(
        submitted, "notifications_battery", NOTIFICATIONS_BATTERY_CHECKBOX_VALUE,
        current_battery_low)
    battery_error_attrs = _field_error_attrs(
        errors, "notifications_battery", "notifications-battery")
    battery_error_html = _field_error_html(
        errors, "notifications_battery", "notifications-battery")

    silent_checked = _submitted_checkbox_checked(
        submitted, "notifications_silent", NOTIFICATIONS_SILENT_CHECKBOX_VALUE,
        current_frame_silent)
    silent_error_attrs = _field_error_attrs(
        errors, "notifications_silent", "notifications-silent")
    silent_error_html = _field_error_html(
        errors, "notifications_silent", "notifications-silent")

    return (
        '<div class="theme-status" %s="%s">'
        '<h2 class="text-heading">%s</h2>'
        '<p class="text-label section-caption" id="%s">%s</p>'
        "%s"
        "%s"
        '<label class="settings-checkbox">'
        '<input type="checkbox" name="notifications_battery" value="%s"%s%s> %s'
        "</label>"
        "%s"
        '<label class="settings-checkbox">'
        '<input type="checkbox" name="notifications_silent" value="%s"%s%s> %s'
        "</label>"
        "%s"
        # Cross-DOM form= binds this button to the sibling
        # notifications-test form (notifications_test_section() below).
        '<button type="submit" form="notifications-test">%s</button>'
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(i18n.t(NOTIFICATIONS_SECTION_HEADING)),
        escape_html(i18n.t(NOTIFICATIONS_SECTION_HEADING)),
        escape_html(NOTIFICATIONS_SECTION_CAPTION_ID), escape_html(i18n.t(NOTIFICATIONS_SECTION_CAPTION)),
        status_html,
        field_html,
        escape_html(NOTIFICATIONS_BATTERY_CHECKBOX_VALUE), " checked" if battery_checked else "",
        battery_error_attrs, escape_html(i18n.t(NOTIFICATIONS_BATTERY_LABEL)),
        battery_error_html,
        escape_html(NOTIFICATIONS_SILENT_CHECKBOX_VALUE), " checked" if silent_checked else "",
        silent_error_attrs, escape_html(i18n.t(NOTIFICATIONS_SILENT_LABEL)),
        silent_error_html,
        escape_html(i18n.t(NOTIFICATIONS_TEST_BUTTON_TEXT)),
    )


def notifications_test_section():
    """The "Send a test" button's own empty `<form>`, a sibling of
    `<form id="{SETTINGS_FORM_ID}">` — an immediate action must never
    nest inside the page-wide Save form. `render()` emits this after
    `</form>` closes, on the Device scope only.

    Carries no `data-confirm`: the handler reads the stored URL from
    disk and never trusts the request body, which is the real
    mitigation, not a confirmation dialog.
    """
    # The action and id are literal path/attribute text, not a %s
    # interpolation: this module's acceptance gate greps them.
    # The form stays a sibling of #settings-form, since a <form> can
    # never nest inside another <form>; the button reaches it via
    # form="notifications-test".
    return (
        '<form method="post" action="/settings/notifications/test" '
        'id="notifications-test" class="notifications-test-form"></form>'
    )


def _masked_calendar_url(url):
    """host + "…" — never the path, query, fragment or userinfo of the
    stored calendar feed URL.

    Uses a real `urlsplit()` parse rather than a byte-offset truncation:
    a naive `url[:20] + "…"` would not be safe, since a short host could
    still leak leading path/query/token characters.

    Returns "" on any failure (falsy url, unparsable, empty netloc); the
    caller omits the masked-URL line entirely rather than fabricate one.
    This is the only place in the module that reads a stored secret URL
    back for display — every other secret-URL field stays write-only.
    """
    if not url:
        return ""
    try:
        netloc = urlsplit(url).netloc
    except ValueError:
        return ""
    if not netloc:
        return ""
    return "%s…" % netloc


def _calendar_connection_html(
        configured, drift, last_synced_at, last_attempt_at, now, entry_count,
        errors=None, submitted=None, state_dir=None):
    """Calendar's connection block inside the Aspect card's Calendar
    row: status, connect/replace form or masked URL, and the cross-DOM
    Disconnect button. Returns `(row_body_html, disconnect_form_html)`
    separately, since HTML forbids nesting the disconnect form inside
    the row's own connect/replace form.

    The feed URL field is write-only: never a `value` attribute, only a
    masked `host + "…"` once connected. Drift is checked before
    `configured`, since a drifted link already forces it False.
    Disconnect posts an empty confirm field to a two-step, server-
    rendered confirm page; the client-side `data-confirm` dialog is a
    misclick guard only, never the real gate.
    """
    # Drift first: it already forces `configured` False, so checking
    # `not configured` first would make this branch unreachable.
    if drift:
        verdict = i18n.t(CALENDAR_STATUS_NOT_CONNECTED_VERDICT)
        detail = i18n.t(CALENDAR_STATUS_PERMISSION_UNSAFE)
        state = "error"
    elif not configured:
        verdict = i18n.t(CALENDAR_STATUS_NOT_CONNECTED_VERDICT)
        detail = ""
        state = "warn"
    else:
        usable = (
            bool(last_synced_at)
            and layout.parse_iso(last_synced_at) is not None
            and layout.age_seconds(last_synced_at, now) is not None)
        verdict = i18n.t(CALENDAR_STATUS_CONNECTED_VERDICT)
        if usable:
            age = layout.age_seconds(last_synced_at, now)
            if entry_count == 1:
                detail = i18n.t(CALENDAR_STATUS_DETAIL_SINGULAR_TEMPLATE) % (
                    layout.relative_age_text(age),)
            else:
                detail = i18n.t(CALENDAR_STATUS_DETAIL_TEMPLATE) % (
                    entry_count, layout.relative_age_text(age))
            state = "ok"
        elif last_attempt_at is not None:
            detail = i18n.t(CALENDAR_STATUS_FETCH_FAILED_DETAIL)
            state = "error"
        else:
            detail = ""
            state = "warn"
    status_html = layout.status_row("", verdict, detail, state)

    error_attrs = _field_error_attrs(
        errors, "calendar_url", "calendar-connect-url", hint_id=CALENDAR_URL_HINT_ID)
    error_html = _field_error_html(errors, "calendar_url", "calendar-connect-url")
    field_html = (
        '<div class="rule-add-form__field">'
        '<label for="calendar-connect-url">%s</label>'
        '<input type="text" id="calendar-connect-url" name="calendar_url" '
        'autocomplete="off" spellcheck="false" maxlength="%s"%s>'
        '<p class="text-label section-caption" id="%s">%s</p>'
        "%s"
        "</div>"
    ) % (
        escape_html(i18n.t(CALENDAR_URL_FIELD_LABEL)),
        CALENDAR_URL_MAX_LEN, error_attrs,
        escape_html(CALENDAR_URL_HINT_ID), escape_html(i18n.t(CALENDAR_URL_HINT)),
        error_html,
    )
    # Literal id/action text, not a %s interpolation: this module's
    # acceptance gate greps the attribute text directly.
    disconnect_button_html = (
        '<button type="submit" form="calendar-disconnect-form" class="calendar-disconnect-btn">%s</button>'
    ) % escape_html(i18n.t(CALENDAR_DISCONNECT_BUTTON_TEXT))
    if configured:
        # configured=True here already means calendar_is_configured()'s
        # own drift guard passed upstream, so this second read is safe.
        masked_url = _masked_calendar_url(
            calendar_rules.configured_calendar_url(state_dir) if state_dir else "")
        masked_url_html = (
            '<p class="text-body calendar-masked-url">%s</p>' % escape_html(masked_url)
            if masked_url else "")
        replace_form_html = (
            '<form method="post" action="/settings/calendar/connect" class="rule-add-form">'
            "%s"
            '<button type="submit">%s</button>'
            "</form>"
        ) % (
            field_html,
            escape_html(i18n.t(CALENDAR_REPLACE_BUTTON_TEXT)),
        )
        disclosure_html = (
            '<details class="calendar-url-disclosure"><summary class="text-link">%s</summary>%s</details>'
        ) % (escape_html(i18n.t(CALENDAR_REPLACE_URL_SUMMARY)), replace_form_html)
        actions_html = (
            '<p class="calendar-actions">%s%s</p>' % (disclosure_html, disconnect_button_html))
        state_branch_html = masked_url_html + actions_html
    else:
        connect_form_html = (
            '<form method="post" action="/settings/calendar/connect" class="rule-add-form">'
            "%s"
            '<button type="submit">%s</button>'
            "</form>"
        ) % (
            field_html,
            escape_html(i18n.t(CALENDAR_CONNECT_BUTTON_TEXT)),
        )
        if drift:
            drift_actions_html = (
                '<p class="calendar-actions calendar-actions--solo">%s</p>'
                % disconnect_button_html)
        else:
            drift_actions_html = ""
        state_branch_html = connect_form_html + drift_actions_html

    how_it_works_html = (
        '<details><summary>%s</summary><p class="text-body">%s</p></details>'
    ) % (
        escape_html(i18n.t(CALENDAR_HOW_IT_WORKS_SUMMARY)),
        escape_html(i18n.t(CALENDAR_HOW_IT_WORKS_BODY)),
    )

    # No wrapping element: the caller places this fragment directly
    # inside the Calendar <details> row.
    row_body_html = status_html + state_branch_html + how_it_works_html

    if configured or drift:
        disconnect_form_html = (
            '<form id="%s" method="post" action="%s" data-confirm="%s" '
            'data-confirm-value="%s">'
            '<input type="hidden" name="%s" value="" data-confirm-field>'
            "</form>"
        ) % (
            escape_html(CALENDAR_DISCONNECT_FORM_ID),
            CALENDAR_DISCONNECT_ROUTE,
            escape_html(i18n.t(CALENDAR_DISCONNECT_CONFIRM_QUESTION)),
            escape_html(CALENDAR_DISCONNECT_CONFIRM_VALUE),
            CALENDAR_DISCONNECT_CONFIRM_FIELD,
        )
    else:
        disconnect_form_html = ""

    return row_body_html, disconnect_form_html


def calendar_disconnect_confirm_page(ctx):
    """Two-step disconnect confirmation, rendered whenever the posted
    confirm field does not exactly match the expected value (including
    a bare POST with none). This page is the actual security control:
    it works with JavaScript disabled, blocked by CSP, or against a
    hand-crafted request that skips the client-side confirm dialog.

    The form re-posts to the same route with the confirm field
    pre-filled; cancel is a plain link back to Display, never a second
    form. `ctx` is accepted but unused today, matching every other
    scoped builder's signature.
    """
    return (
        layout.page_header(i18n.t(CALENDAR_DISCONNECT_CONFIRM_HEADING))
        + '<p class="text-body">%s</p>'
        '<form method="post" action="%s">'
        '<input type="hidden" name="%s" value="%s">'
        '<button type="submit">%s</button>'
        "</form>"
        '<p><a class="text-label" href="%s">%s</a></p>'
    ) % (
        escape_html(i18n.t(CALENDAR_DISCONNECT_CONFIRM_SENTENCE)),
        CALENDAR_DISCONNECT_ROUTE,
        CALENDAR_DISCONNECT_CONFIRM_FIELD, escape_html(CALENDAR_DISCONNECT_CONFIRM_VALUE),
        escape_html(i18n.t(CALENDAR_DISCONNECT_CONFIRM_BUTTON_TEXT)),
        layout.DISPLAY_ROUTE, escape_html(i18n.t(CALENDAR_DISCONNECT_CANCEL_TEXT)),
    )


def poll_trigger_section(cooldown_remaining):
    """The manual poll-trigger control: an enabled button, or a
    native-disabled button with remaining-seconds copy during a
    cooldown. Emits zero `<script>` elements: the countdown lives in
    `poll-cooldown.js`, driven by `data-*` attributes, UX only —
    `_handle_poll_now()` re-checks the cooldown server-side regardless.
    The caption is computed once, above both branches.
    """
    # `> 0`, not truthy: must agree with poll-cooldown.js's own
    # `remaining > 0` guard, or a negative value would disable the
    # button natively while the script no-ops, with no way to re-enable
    # it client-side.
    caption_html = (
        '<p class="text-label section-caption">%s</p>'
        % escape_html(i18n.t(POLL_SECTION_CAPTION)))
    if cooldown_remaining > 0:
        translated_helper_text = i18n.t(POLL_COOLDOWN_HELPER_TEXT)
        cooldown_text = translated_helper_text.format(n=cooldown_remaining)
        template = translated_helper_text.format(n=POLL_COOLDOWN_TEMPLATE_TOKEN)
        return (
            "%s"
            '<form method="post" action="/poll-now">'
            '<button type="submit" id="%s" disabled '
            'data-cooldown="%s" data-cooldown-text-id="%s" '
            'data-cooldown-template="%s" data-cooldown-token="%s">'
            "%s</button>"
            "</form>"
            '<p class="text-body" id="%s">%s</p>'
        ) % (
            caption_html,
            POLL_TRIGGER_BUTTON_ID,
            escape_html(str(cooldown_remaining)),
            escape_html(POLL_COOLDOWN_TEXT_ID),
            escape_html(template),
            escape_html(POLL_COOLDOWN_TEMPLATE_TOKEN),
            escape_html(i18n.t("Trigger poll now")),
            POLL_COOLDOWN_TEXT_ID,
            escape_html(cooldown_text),
        )
    return (
        "%s"
        '<form method="post" action="/poll-now">'
        '<button type="submit" id="%s" data-submit-pending="%s">'
        "%s</button>"
        "</form>"
    ) % (
        caption_html,
        POLL_TRIGGER_BUTTON_ID,
        escape_html(i18n.t(POLL_SUBMIT_PENDING_TEXT)),
        escape_html(i18n.t("Trigger poll now")),
    )


# The per-flight colour-rules editor: an add form (its own immediate
# POST route) plus an always-present list with a plain per-row Delete
# button (its own immediate POST route).


def _rule_delete_action(kind, value):
    """The delete form's `action` for `(kind, value)`:
    `/settings/rules/{kind}/{value}/delete` — both segments are already
    normalised, allowlisted uppercase alphanumerics by the time a row
    reaches here, so `escape_html()` is the only encoding needed. One
    builder for both the desktop and mobile row renderers, so they can
    never diverge into building two different strings for the same row.
    """
    return "%s%s/%s%s" % (
        RULES_DELETE_ROUTE_PREFIX, escape_html(kind), escape_html(value),
        RULES_DELETE_ROUTE_SUFFIX,
    )


def _rule_kind_radio_html(kind, checked):
    """One native radio + `<label>` pair for the "Match by" segmented
    control. The radio is visually hidden and styled via the adjacent
    label (`.theme-form input[type="radio"] + label`); the plain-
    language word is the visible label text, and the technical term is
    the label's own `title` attribute, so a hovering mouse user still
    finds the exact vocabulary without it cluttering the visible label.
    """
    radio_id = "rule-kind-%s" % kind
    return (
        '<input type="radio" name="rule_kind" id="%s" value="%s" '
        'class="visually-hidden"%s>'
        '<label for="%s" title="%s">%s</label>'
    ) % (
        escape_html(radio_id), escape_html(kind), " checked" if checked else "",
        escape_html(radio_id), escape_html(i18n.t(RULE_KIND_TITLES[kind])),
        escape_html(i18n.t(RULE_KIND_LABELS[kind])),
    )


def _rule_add_form_html(errors=None, submitted=None):
    """The one-line add-rule form: a `role="radiogroup"` of native
    radios styled as a segmented control, a value input, a compact
    theme-chip grid and an "Add rule" button, one `<form>` targeting
    `RULES_ADD_ROUTE`.

    No per-segment placeholder swap on selection (no script wires it):
    one static placeholder covers the always-valid default kind only.
    Validation errors render under the field, keeping the typed value.
    """
    selected_kind = _submitted_or_current(
        submitted, "rule_kind", colour_rules.RULE_KIND_CALLSIGN)
    kind_radios = "".join(
        _rule_kind_radio_html(kind, kind == selected_kind)
        for kind in colour_rules.RULE_KINDS)
    kind_error_html = _field_error_html(errors, "rule_kind", "rule-kind")

    submitted_value = submitted.get("rule_key", "") if submitted is not None else ""
    value_error_attrs = _field_error_attrs(errors, "rule_key", "rule-key")
    value_error_html = _field_error_html(errors, "rule_key", "rule-key")

    selected_theme_id = _submitted_or_current(
        submitted, "rule_theme_id", device_config.THEME_IDS[0])
    theme_error_html = _field_error_html(errors, "rule_theme_id", "rule-theme")
    chip_grid_html = _theme_chip_grid_html(
        "rule_theme_id", selected_theme_id,
        extra_class="theme-chip-grid--compact", chip_extra_class="theme-chip--compact",
        extra_attr='role="radiogroup" aria-labelledby="%s"' % escape_html(RULE_THEME_HEADING_ID))

    return (
        '<form method="post" action="%s" class="rule-add-form rule-add-form--inline">'
        '<div class="rule-add-form__field rule-add-form__field--kind" role="radiogroup" '
        'aria-labelledby="%s">'
        '<span id="%s" class="visually-hidden">%s</span>'
        '<div class="theme-form">%s</div>'
        "%s"
        "</div>"
        '<div class="rule-add-form__field">'
        '<label for="rule-key" class="visually-hidden">%s</label>'
        '<input type="text" id="rule-key" name="rule_key" maxlength="8" '
        'required autocomplete="off" placeholder="%s" value="%s"%s>'
        "%s"
        "</div>"
        '<div class="rule-add-form__field">'
        '<span id="%s" class="visually-hidden">%s</span>'
        "%s"
        "%s"
        "</div>"
        '<button type="submit">%s</button>'
        "</form>"
    ) % (
        RULES_ADD_ROUTE,
        escape_html(RULE_KIND_HEADING_ID),
        escape_html(RULE_KIND_HEADING_ID), escape_html(i18n.t(RULE_KIND_FIELD_LABEL)),
        kind_radios,
        kind_error_html,
        escape_html(i18n.t(RULE_VALUE_FIELD_LABEL)),
        escape_html(RULE_VALUE_PLACEHOLDER), escape_html(submitted_value), value_error_attrs,
        value_error_html,
        escape_html(RULE_THEME_HEADING_ID), escape_html(i18n.t("Theme")),
        chip_grid_html,
        theme_error_html,
        escape_html(i18n.t(RULE_ADD_BUTTON_TEXT)),
    )


def _rule_suggestion_chips_html(state_dir):
    """Up to five distinct recent callsigns as suggestion chips, from
    `history_db.recent_runway_events()` (a second, independent call to
    the same shared helper `home_page._recent_flights()` uses, since
    page modules never import each other directly). The `<button
    type="button">` chips ship with no script to wire them in this
    phase, so they degrade to inert, never to invisible.

    Returns "" when there are no recent events, or on any read failure
    — never raises.
    """
    try:
        with history_db.open_db(state_dir) as conn:
            rows = history_db.recent_runway_events(conn, limit=20)
    except Exception:
        return ""
    seen = []
    for row in rows:
        callsign = row.get("callsign")
        if callsign and callsign not in seen:
            seen.append(callsign)
        if len(seen) >= 5:
            break
    if not seen:
        return ""
    chips = " · ".join(
        '<button type="button" class="rule-suggestion-chip" data-kind="callsign" '
        'data-value="%s">%s</button>' % (escape_html(cs), escape_html(cs))
        for cs in seen)
    return '<p class="text-label rule-suggestions">%s %s</p>' % (
        escape_html(i18n.t(RULE_SUGGESTIONS_LABEL)), chips)


def _rule_row_html(kind, value, theme_id):
    """One `<li class="rule-row">`: the theme's two palette dots, the
    key, a kind badge, the theme's display name, and a Remove form.

    The Remove form's `data-confirm` is a misclick guard only: deleting
    a rule is immediately reversible (re-adding the same key restores
    it), and the server-side handler requires no confirm value.
    """
    departing_hex = _palette_hex(device_config.THEMES[theme_id]["departing_index"])
    arriving_hex = _palette_hex(device_config.THEMES[theme_id]["arriving_index"])
    swatch_html = (
        '<span class="rule-row__swatch theme-chip__swatches" aria-hidden="true">'
        '<span class="theme-chip__dot" style="background:%s"></span>'
        '<span class="theme-chip__dot" style="background:%s"></span>'
        "</span>"
    ) % (escape_html(departing_hex), escape_html(arriving_hex))
    delete_form = (
        '<form method="post" action="%s" data-confirm="%s">'
        '<button type="submit">%s</button>'
        "</form>"
    ) % (
        _rule_delete_action(kind, value),
        escape_html(i18n.t(RULE_REMOVE_CONFIRM_QUESTION)),
        escape_html(i18n.t(RULE_REMOVE_BUTTON_TEXT)),
    )
    return (
        '<li class="rule-row">'
        "%s"
        '<span class="rule-row__key mono">%s</span>'
        '<span class="rule-row__kind banner__pill">%s</span>'
        '<span class="rule-row__theme">%s</span>'
        "%s"
        "</li>"
    ) % (
        swatch_html,
        escape_html(value),
        escape_html(i18n.t(RULE_KIND_LABELS.get(kind, kind))),
        escape_html(i18n.t(device_config.theme_label(theme_id))),
        delete_form,
    )


def _rule_list_html(rows):
    """`<ul class="rule-list">`, one `.rule-row` per row.
    `colour_rules.rule_rows()` already orders rows most-specific first
    (callsign, then hex, then prefix) and alphabetically within each
    kind, so no re-sort is needed here. Returns "" for an empty list;
    the caller renders its own empty state in that case.
    """
    if not rows:
        return ""
    items = "".join(
        _rule_row_html(kind, value, theme_id)
        for kind, value, theme_id, _created_at in rows)
    return '<ul class="rule-list">%s</ul>' % items


def _nested_wrapper_html(html_fragment, base_class, nested_class):
    """Appends a `--nested` modifier class to a group builder's own
    outer wrapper, so a card rendered under a supersection heading
    renders one heading rung below it instead of Device's un-nested tier.

    `nested_class` is a literal string at every call site, never
    derived from `base_class`, so it stays grep-visible. Each builder
    emits its wrapper class exactly once as `class="{base_class}"`, so a
    single count-limited `str.replace()` is the whole mechanism.
    """
    needle = 'class="%s"' % base_class
    replacement = 'class="%s %s"' % (base_class, nested_class)
    return html_fragment.replace(needle, replacement, 1)


def _display_groups_html(builders, groups):
    """Display scope's two headed supersections: "What it watches"
    (Runway) and "When it is on" (Quiet hours) — each card gets the
    `--nested` modifier (`_nested_wrapper_html()`). Returns
    `(watches_html, on_html)`.

    Both cards render as siblings of the settings `<form>`, not inside
    it: their own inputs cross-submit via `form="{SETTINGS_FORM_ID}"`,
    since their instant-switch controls would otherwise need to nest a
    `<form>` inside another `<form>`, which HTML forbids.
    """
    runway_html = (
        _nested_wrapper_html(builders[screens.GROUP_RUNWAY](), "theme-status", "theme-status--nested")
        if screens.GROUP_RUNWAY in groups else "")
    watches_supersection_html = (
        layout.section_intro_html(
            DISPLAY_WATCHES_SECTION_ID, i18n.t(DISPLAY_WATCHES_HEADING),
            i18n.t(DISPLAY_WATCHES_INTRO))
        + runway_html
    )
    quiet_hours_html = (
        _nested_wrapper_html(
            builders[screens.GROUP_QUIET_HOURS](), "theme-status", "theme-status--nested")
        if screens.GROUP_QUIET_HOURS in groups else "")
    on_supersection_html = (
        layout.section_intro_html(
            DISPLAY_ON_SECTION_ID, i18n.t(DISPLAY_ON_HEADING), i18n.t(DISPLAY_ON_INTRO))
        + quiet_hours_html
    )
    return watches_supersection_html, on_supersection_html


def _device_groups_html(builders, groups):
    """Device scope's two headed supersections: "When it wakes" (Wake
    interval alone) and "How it tells you" (Diagnostic LED and
    Notifications together).

    Unlike `_display_groups_html()`, a supersection's heading is
    omitted entirely when every card under it is absent — an intro
    sentence introducing nothing is worse than no heading at all.
    """
    wake_interval_html = (
        _nested_wrapper_html(
            builders[screens.GROUP_WAKE_INTERVAL](), "theme-status", "theme-status--nested")
        if screens.GROUP_WAKE_INTERVAL in groups and screens.GROUP_WAKE_INTERVAL in builders
        else "")
    wakes_supersection_html = (
        (layout.section_intro_html(
            DEVICE_WAKES_SECTION_ID, i18n.t(DEVICE_WAKES_HEADING), i18n.t(DEVICE_WAKES_INTRO))
         + wake_interval_html)
        if wake_interval_html else "")

    led_html = (
        _nested_wrapper_html(
            builders[screens.GROUP_LED](), "theme-status", "theme-status--nested")
        if screens.GROUP_LED in groups and screens.GROUP_LED in builders else "")
    notifications_html = (
        _nested_wrapper_html(
            builders[screens.GROUP_NOTIFICATIONS](), "theme-status", "theme-status--nested")
        if screens.GROUP_NOTIFICATIONS in groups and screens.GROUP_NOTIFICATIONS in builders
        else "")
    tells_cards_html = led_html + notifications_html
    tells_supersection_html = (
        (layout.section_intro_html(
            DEVICE_TELLS_SECTION_ID, i18n.t(DEVICE_TELLS_HEADING), i18n.t(DEVICE_TELLS_INTRO))
         + tells_cards_html)
        if tells_cards_html else "")

    return wakes_supersection_html + tells_supersection_html


def render(ctx, scope=SCOPE_ALL, errors=None, submitted=None):
    """Render one settings page (SCOPE_ALL/SCOPE_DISPLAY/SCOPE_DEVICE).

    `errors`/`submitted` are passed together only by a rejected save,
    threaded into each group builder so a field can repopulate itself.
    `submitted` is deliberately not defaulted to `{}`: `None` (an
    ordinary load) and an actual dict mean different things to
    `_submitted_checkbox_checked()` — collapsing them would render
    every checkbox unchecked on every ordinary load.
    """
    if errors is None:
        errors = {}
    device_cfg = ctx.get("device_config") or {}
    current_theme_id = device_cfg.get("theme", device_config.DEFAULT_THEME_ID)
    # Explicit `.get()`, no `or` fallback: `None` is a meaningful value
    # (no arrivals-theme override), not an oversight.
    current_theme_arriving = device_cfg.get("theme_arriving")
    current_runway_id = device_cfg.get(
        "tracked_runway", device_config.DEFAULT_RUNWAY_ID)
    current_led_enabled = device_cfg.get(
        "led_enabled", device_config.DEFAULT_LED_ENABLED)
    current_quiet_start = device_cfg.get(
        "quiet_hours_start", device_config.DEFAULT_QUIET_HOURS_START)
    current_quiet_end = device_cfg.get(
        "quiet_hours_end", device_config.DEFAULT_QUIET_HOURS_END)
    # `is None`, not `or`: 0 is never a valid wake_interval_s. Falls back
    # to the deployed SKYPANE_SLEEP_S env default when device_config has
    # no value yet (e.g. a fresh install with no systemd unit).
    current_wake_interval_s = device_cfg.get("wake_interval_s")
    if current_wake_interval_s is None:
        current_wake_interval_s = ctx.get("wake_interval_env_default")
    # Explicit `.get()`, no `or` fallback: `None` means no calendar
    # theme chosen yet, defaulting to the base theme.
    current_calendar_theme_id = device_cfg.get("calendar_theme_id")
    calendar_configured = ctx.get("calendar_configured")
    calendar_last_synced_at = ctx.get("calendar_last_synced_at")
    # last_attempt_at distinguishes "just connected, no sync yet" from
    # "has been failing"; entry_count feeds the status detail template.
    calendar_last_attempt_at = ctx.get("calendar_last_attempt_at")
    calendar_entry_count = ctx.get("calendar_entry_count") or 0
    calendar_drift = ctx.get("calendar_drift")
    # A device_config.json predating this field resolves through
    # device_config.DEFAULT_NOTIFICATIONS, never a KeyError.
    current_notifications = device_cfg.get("notifications") or device_config.DEFAULT_NOTIFICATIONS
    notifications_configured = bool(current_notifications.get("topic_url"))
    current_notifications_battery = current_notifications.get(
        "battery_low", device_config.DEFAULT_NOTIFICATIONS["battery_low"])
    current_notifications_silent = current_notifications.get(
        "frame_silent", device_config.DEFAULT_NOTIFICATIONS["frame_silent"])
    cooldown_remaining = ctx.get("poll_cooldown_remaining", 0)
    # next_wake_clock is the shared next-wake clock string threaded into
    # every group's caption and the Device header slot; None when
    # unknown (no check-in yet, or no known interval), and every
    # consumer omits the suffix/line in that case rather than show a
    # placeholder.
    next_wake_clock = None
    next_wake_iso, _, _ = wake.next_wake_status(
        ctx.get("last_checkin_ts"), device_cfg)
    if next_wake_iso:
        next_wake_parsed = layout.parse_iso(next_wake_iso)
        if next_wake_parsed is not None:
            next_wake_clock = layout.local_clock_text(
                next_wake_parsed, now_parsed=layout.parse_iso(ctx.get("now")))

    # data-dirty-form marks the form dirty-state.js watches to drive the
    # save bar below. The native Save button (STATIC_SAVE_FALLBACK_ATTR)
    # is the one save affordance on the page — an AST check pins it
    # reaching this function's own return as a bare name, so it can
    # never accidentally duplicate or vanish.
    #
    # No `hidden` attribute: this bar is the only save affordance for a
    # scripts-blocked visitor, so it must render visible by default.
    # dirty-state.js hides it at init and reveals it on real changes.
    # Cancel is a native `type="reset"` (works without script);
    # `[data-dirty-count]` starts empty to avoid a false "Unsaved
    # changes" announcement on every fresh, unscripted page load.
    dirty_changed_suffix_html = escape_html(i18n.t(DIRTY_CHANGED_SUFFIX))
    dirty_and_html = escape_html(i18n.t(DIRTY_AND))
    dirty_list_and_html = escape_html(i18n.t(DIRTY_LIST_AND))
    dirty_unsaved_singular_html = escape_html(i18n.t(DIRTY_UNSAVED_SINGULAR))
    dirty_unsaved_plural_html = escape_html(i18n.t(DIRTY_UNSAVED_PLURAL))
    dirty_saving_html = escape_html(i18n.t(DIRTY_SAVING_TEXT))
    dirty_initial_text_html = escape_html(i18n.t(DIRTY_BAR_INITIAL_TEXT))

    screen_id = screens.current_screen_id(ctx)
    screen = screens.screen_type(screen_id)
    if scope not in SCOPES:
        scope = SCOPE_ALL
    groups = scope_groups(scope, screen_id)

    # screens.GROUP_THEME/GROUP_CALENDAR have no entry here: their own
    # renderer (the Aspect card, built by render()'s Display branch)
    # contains real <form> elements that must never render as a literal
    # descendant of <form id="{SETTINGS_FORM_ID}">.
    builders = {
        screens.GROUP_RUNWAY: lambda: runway_fieldset(
            current_runway_id, ctx.get("runway_images") or (),
            errors=errors, submitted=submitted, next_wake_clock=next_wake_clock),
        screens.GROUP_LED: lambda: led_group(
            current_led_enabled, errors=errors, submitted=submitted,
            next_wake_clock=next_wake_clock),
        screens.GROUP_QUIET_HOURS: lambda: quiet_hours_group(
            current_quiet_start, current_quiet_end,
            errors=errors, submitted=submitted),
        # Read inside the lambda so it costs nothing unless this group
        # is actually in scope.
        screens.GROUP_WAKE_INTERVAL: lambda: wake_interval_group(
            current_wake_interval_s, errors=errors, submitted=submitted,
            next_wake_clock=next_wake_clock,
            battery_rows=wake_battery_rows(ctx.get("state_dir"), ctx.get("now"))),
        screens.GROUP_NOTIFICATIONS: lambda: notifications_group(
            notifications_configured, current_notifications_battery,
            current_notifications_silent, errors=errors, submitted=submitted),
    }
    # Its own immediate-POST form; must render after </form> closes so
    # it never nests inside the settings form.
    notifications_test_html = (
        notifications_test_section() if screens.GROUP_NOTIFICATIONS in groups else "")
    # The LED switch's own instant-toggle form, for the same reason.
    quick_led_html = (
        quick_led_form_html(current_led_enabled) if screens.GROUP_LED in groups else "")
    if scope == SCOPE_DISPLAY:
        # The strip and this freshness line are the only elements this
        # page declares swappable (layout.REFRESH_SWAP_SELECTORS_BY_PAGE);
        # everything else here is a <form>, and a swap mid-edit would
        # corrupt it. The refresh loop also stands down while the save
        # bar reports unsaved edits.
        header = layout.page_header(
            i18n.t(DISPLAY_PAGE_TITLE), purpose=i18n.t(DISPLAY_PAGE_PURPOSE),
            freshness_html=layout.freshness_line_html(ctx.get("now")),
            action_html=_screen_caption_html(screen) + _screen_selector_html(screen_id, errors=errors))
        frame_strip_section_html = layout.frame_strip_html(
            ctx, return_to=layout.DISPLAY_ROUTE, next_wake_iso=next_wake_iso)
        hidden_html = _scope_fields_html(scope, layout.DISPLAY_ROUTE)
        show_poll = False
        # groups_html stays empty on Display: every saved control here
        # cross-submits from outside the form via
        # form="{SETTINGS_FORM_ID}".
        # submits from outside the form via `form="{SETTINGS_FORM_ID}"`,
        # exactly like Runway/Calendar already do (Structural Note 2's
        # own "the physical form becomes a pure submission target").
        #
        # Gated on GROUP_THEME alone: safe only because
        # companion/screens.py's one registered screen type lists
        # GROUP_THEME and GROUP_CALENDAR together (always both true or
        # both false today). A future screen type with only one of the
        # two must split this gate.
        aspect_section_html = (
            layout.section_intro_html(
                DISPLAY_LOOK_SECTION_ID, i18n.t(DISPLAY_LOOK_HEADING), i18n.t(DISPLAY_LOOK_INTRO))
            + _nested_wrapper_html(
                _aspect_card_html(
                    ctx, current_theme_id, current_theme_arriving, current_calendar_theme_id,
                    errors=errors, submitted=submitted, state_dir=ctx.get("state_dir"),
                    calendar_configured=calendar_configured, calendar_drift=calendar_drift,
                    calendar_last_synced_at=calendar_last_synced_at,
                    calendar_last_attempt_at=calendar_last_attempt_at, now=ctx.get("now"),
                    calendar_entry_count=calendar_entry_count),
                "page-section aspect-card", "page-section--nested")
            if screens.GROUP_THEME in groups else "")
        groups_html = ""
        (display_watches_supersection_html,
            display_on_supersection_html) = _display_groups_html(builders, groups)
    elif scope == SCOPE_DEVICE:
        header = layout.page_header(
            i18n.t(DEVICE_PAGE_TITLE), purpose=i18n.t(DEVICE_PAGE_PURPOSE),
            action_html=(
                _screen_caption_html(screen) + _screen_selector_html(screen_id, errors=errors)
                + _next_wake_caption_html(next_wake_clock)))
        hidden_html = _scope_fields_html(scope, layout.DEVICE_ROUTE)
        # The Frame strip renders only on Home and Display, never Device.
        frame_strip_section_html = ""
        show_poll = bool(screen.get("has_manual_poll"))
        groups_html = _device_groups_html(builders, groups)
        aspect_section_html = ""
        display_watches_supersection_html = ""
        display_on_supersection_html = ""
    else:
        header = layout.page_header(i18n.t("Settings"))
        hidden_html = ""
        frame_strip_section_html = ""
        show_poll = True
        # SCOPE_ALL is the legacy, never-served whole-page render, kept
        # byte-identical to its pre-existing output for harness checks
        # against the full form; no live app.py route uses it.
        groups_html = "".join(builders[g]() for g in groups if g in builders)
        aspect_section_html = ""
        display_watches_supersection_html = ""
        display_on_supersection_html = ""

    poll_section_html = (
        '<section class="page-section">'
        '<h2 class="text-heading">%s</h2>'
        "%s"
        "</section>" % (escape_html(i18n.t(POLL_SECTION_HEADING)), poll_trigger_section(cooldown_remaining))
        if show_poll else "")
    # Device-scope-only: wraps the Poll card under its own supersection,
    # "When you can't wait". "" on Display/SCOPE_ALL, which never set
    # show_poll for this branch.
    poll_supersection_html = (
        (layout.section_intro_html(
            DEVICE_POLL_SECTION_ID, i18n.t(DEVICE_POLL_HEADING), i18n.t(DEVICE_POLL_INTRO))
         + _nested_wrapper_html(poll_section_html, "page-section", "page-section--nested"))
        if scope == SCOPE_DEVICE and poll_section_html else "")

    return (
        header
        # The Frame strip renders after the header and before the
        # form; "" on Device and SCOPE_ALL.
        + frame_strip_section_html
        + '<form class="config-form" id="%s" data-dirty-form method="post" action="%s">'
        "%s"
        "%s"
        "</form>"
        "%s"
        "%s"
        "%s"
        "%s"
        "%s"
        "%s"
        # The dirty bar is last, after </form> and the Poll section, so
        # its position: fixed sits outside the short settings form.
        # A native type="reset" Cancel and an empty-until-JS count span
        # keep this bar usable with no script (see local-variable
        # comment above).
        '<div class="dirty-bar" data-dirty-bar role="status" '
        'data-dirty-changed-suffix="%s" data-dirty-and="%s" '
        'data-dirty-list-and="%s" data-dirty-unsaved-singular="%s" '
        'data-dirty-unsaved-plural="%s" data-dirty-saving="%s" '
        'data-dirty-initial-text="%s">'
        "<span data-dirty-count></span>"
        '<button type="submit" class="dirty-bar__save" form="%s" %s>%s</button>'
        '<button type="reset" form="%s" class="dirty-bar__cancel" data-dirty-cancel>%s</button>'
        "</div>"
    ) % (
        SETTINGS_FORM_ID,
        SETTINGS_ROUTE,
        hidden_html,
        groups_html,
        # "" on the Device/SCOPE_ALL paths (both set it to "" above).
        aspect_section_html,
        display_watches_supersection_html,
        notifications_test_html,
        quick_led_html,
        display_on_supersection_html,
        poll_supersection_html if scope == SCOPE_DEVICE else poll_section_html,
        dirty_changed_suffix_html,
        dirty_and_html,
        dirty_list_and_html,
        dirty_unsaved_singular_html,
        dirty_unsaved_plural_html,
        dirty_saving_html,
        dirty_initial_text_html,
        # STATIC_SAVE_FALLBACK_ATTR must reach here as a bare name for
        # the AST invariant checked elsewhere.
        SETTINGS_FORM_ID,
        STATIC_SAVE_FALLBACK_ATTR,
        escape_html(i18n.t("Save settings")),
        # The Cancel button: form=, then its label.
        SETTINGS_FORM_ID,
        escape_html(i18n.t("Cancel")),
    )


def _screen_caption_html(screen):
    """The small "Screen: Plane frame" line under a scoped page's title —
    the visible end of the companion/screens.py seam. Rendered as an
    already-safe block for page_header()'s `action_html` slot.
    """
    # screen["label"] is translated at this display site (i18n.t());
    # the screen id itself never changes.
    return (
        '<p class="page-header__screen text-label">%s</p>'
        % escape_html(i18n.t(SCREEN_CAPTION_TEMPLATE) % i18n.t(screen["label"])))


NEXT_WAKE_HEADER_LABEL = "Next wake"
NEXT_WAKE_HEADER_VALUE_TEMPLATE = "≈ %s"


def _next_wake_caption_html(next_wake_clock):
    """The Device page header's "Next wake ≈ HH:MM" line (Home's own
    copy lives in `home_page.py`). Returns "" when `next_wake_clock` is
    falsy — no placeholder, no "unknown".
    """
    if not next_wake_clock:
        return ""
    return (
        '<p class="page-header__screen text-label">%s</p>'
        % escape_html(
            "%s %s" % (
                i18n.t(NEXT_WAKE_HEADER_LABEL),
                i18n.t(NEXT_WAKE_HEADER_VALUE_TEMPLATE) % next_wake_clock)))


def _screen_selector_html(current_screen_id, errors=None):
    """A `<select name="screen_id">` for switching which registered
    screen type this settings page edits. Returns "" when only one
    screen type is registered, since a one-option choice has no real
    decision value.

    Rendered inside `page_header()`'s action slot, visually before
    `<form id="{SETTINGS_FORM_ID}">` opens, but must still submit with
    it — the `form="{SETTINGS_FORM_ID}"` attribute makes that possible.

    `errors` renders a rejected `screen_id` message; no `submitted`
    repopulation is needed, since `current_screen_id` already reflects
    any rejected submission.
    """
    if len(screens.SCREEN_IDS) <= 1:
        return ""
    options = []
    for screen_id in screens.SCREEN_IDS:
        selected = " selected" if screen_id == current_screen_id else ""
        label = screens.screen_type(screen_id)["label"]
        options.append(
            '<option value="%s"%s>%s</option>'
            % (escape_html(screen_id), selected, escape_html(label)))
    error_html = _field_error_html(errors, "screen_id", SCREEN_SELECTOR_ID)
    return (
        '<label class="visually-hidden" for="%s">%s</label>'
        '<select name="screen_id" id="%s" form="%s">%s</select>'
        "%s"
    ) % (
        SCREEN_SELECTOR_ID, escape_html(i18n.t(SCREEN_SELECTOR_LABEL_TEXT)),
        SCREEN_SELECTOR_ID, SETTINGS_FORM_ID, "".join(options),
        error_html,
    )


def _scope_fields_html(scope, return_route):
    return (
        '<input type="hidden" name="%s" value="%s">'
        '<input type="hidden" name="%s" value="%s">'
    ) % (
        SCOPE_FIELD_NAME, escape_html(scope),
        RETURN_TO_FIELD_NAME, escape_html(return_route),
    )


# The four outcomes of resolving the submitted calendar fields. Plain
# strings, never rendered and never travel in a URL. Four distinct
# sentinels (not e.g. two bools) so a caller cannot mistake one outcome
# for another by falsy-comparing the wrong pair.
CALENDAR_URL_SIGNAL_CARRY_FORWARD = "carry_forward"
CALENDAR_URL_SIGNAL_SET = "set"
CALENDAR_URL_SIGNAL_CLEAR = "clear"
CALENDAR_URL_SIGNAL_INVALID = "invalid"

# handle_post()'s per-field error messages, one constant per rejected
# field, so the copy exists in exactly one place. Sentence case, no
# stack-trace vocabulary, matching this file's label voice.
ERROR_INVALID_CHOICE = "That is not one of the available choices."
ERROR_UNEXPECTED_SWITCH_VALUE = "That switch sent an unexpected value."
ERROR_WAKE_INTERVAL_RANGE = "Enter a whole number of seconds between 60 and 3600."
ERROR_QUIET_HOURS_TIME_SHAPE = "Enter a time as HH:MM, for example 23:00."
# Covers both the over-length and the contradictory (calendar_url +
# calendar_disconnect together) cases; deliberately never echoes any
# part of the submitted URL back.
ERROR_CALENDAR_URL_INVALID = (
    "That link is too long, or conflicts with the disconnect option below.")

# A local copy of device_config's private HH:MM pattern — not imported,
# since it is private to that module. UX pre-check only:
# save_device_config()'s own identical gate is authoritative; a test
# pins the two patterns against the same input table so they cannot
# silently drift apart.
_QUIET_HOURS_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)\Z")


def _note_error(errors, field, message):
    """No-ops when `errors is None`. Otherwise sets `errors[field]`
    only if that field has no message yet, so a later, more generic
    gate can never overwrite an earlier, more specific one.
    """
    if errors is None:
        return
    if field not in errors:
        errors[field] = message


def submitted_calendar_signal(form):
    """The single definition of what a submitted `calendar_url` +
    `calendar_disconnect` pair means. Both `handle_post()` and the
    calendar-connect route call this, so the two can never disagree.

    An absent/empty URL with no checkbox resolves to carry-forward, not
    disconnect: the write-only URL field renders empty on every load
    regardless of state, so treating an ordinary save's empty
    submission as "disconnect" would silently wipe the calendar.

    Never raises, and never itself persists. The in-form checkbox these
    gates interpret no longer renders, but a crafted request can still
    send it, so the gates stay to keep `handle_post()`'s all-or-nothing
    rejection covering that shape.
    """
    # A page that never rendered the Calendar group cannot have meant
    # anything by the field's absence.
    if screens.GROUP_CALENDAR not in scope_groups(submitted_scope(form)):
        return CALENDAR_URL_SIGNAL_CARRY_FORWARD
    raw_url = form.get("calendar_url")
    stripped_url = raw_url.strip() if isinstance(raw_url, str) else ""
    disconnect = form.get("calendar_disconnect")

    if disconnect is not None and disconnect != CALENDAR_DISCONNECT_CHECKBOX_VALUE:
        return CALENDAR_URL_SIGNAL_INVALID
    if disconnect is not None and stripped_url:
        return CALENDAR_URL_SIGNAL_INVALID
    if disconnect is not None:
        return CALENDAR_URL_SIGNAL_CLEAR
    if not stripped_url:
        return CALENDAR_URL_SIGNAL_CARRY_FORWARD
    if len(stripped_url) > CALENDAR_URL_MAX_LEN:
        return CALENDAR_URL_SIGNAL_INVALID
    return CALENDAR_URL_SIGNAL_SET


def handle_post(form, ctx, errors=None):
    """Validate the submitted settings state against `device_config`'s
    own registries and validators, then persist all fields in one
    `save_device_config()` call. Rejection is all-or-nothing: a crafted
    or invalid value in any field aborts before any write.

    Every checkbox not rendered on the current scope resolves absent
    -> `None` (leave unchanged), never `False` — a scope with no control
    for a field must not silently turn it off. The two Notifications
    checkboxes are the exception, since their card is always in scope
    when rendered.

    `wake_interval_s` needs a string-to-int conversion that the two
    quiet-hours time fields skip, since those stay strings in
    `device_config`. `errors`, if given, is filled via `_note_error()`.
    The calendar secret write is layered after the device-config write,
    only for the `set`/`clear` signals, since `carry_forward` would
    otherwise erase the fetched calendar registry.
    """
    state_dir = ctx["state_dir"]
    scope = submitted_scope(form)
    in_scope = set(scope_groups(scope, screens.current_screen_id(ctx)))
    submitted_theme = form.get("theme")
    submitted_theme_arriving = form.get("theme_arriving")
    submitted_runway = form.get("tracked_runway")
    submitted_led = form.get("led_enabled")
    submitted_qh_enabled = form.get("quiet_hours_enabled")
    submitted_qh_start = form.get("quiet_hours_start")
    submitted_qh_end = form.get("quiet_hours_end")
    submitted_wake_interval = form.get("wake_interval_s")
    submitted_display = form.get("display_enabled")
    submitted_calendar_theme_id = form.get("calendar_theme_id")
    submitted_calendar_url = form.get("calendar_url")
    submitted_screen_id = form.get("screen_id")
    submitted_notifications_topic_url = form.get("notifications_topic_url")
    submitted_notifications_battery = form.get("notifications_battery")
    submitted_notifications_silent = form.get("notifications_silent")
    calendar_signal = submitted_calendar_signal(form)

    if submitted_theme is not None and submitted_theme not in device_config.THEME_IDS:
        _note_error(errors, "theme", ERROR_INVALID_CHOICE)
        return FLASH_SAVE_FAILED
    if submitted_screen_id is not None and submitted_screen_id not in screens.SCREEN_IDS:
        _note_error(errors, "screen_id", ERROR_INVALID_CHOICE)
        return FLASH_SAVE_FAILED
    if calendar_signal == CALENDAR_URL_SIGNAL_INVALID:
        _note_error(errors, "calendar_url", ERROR_CALENDAR_URL_INVALID)
        return FLASH_SAVE_FAILED
    # A shape bound against an absurd paste, checked only when the field
    # is actually in scope.
    if (
        screens.GROUP_NOTIFICATIONS in in_scope
        and submitted_notifications_topic_url
        and len(submitted_notifications_topic_url.strip()) > NOTIFICATIONS_URL_MAX_LEN
    ):
        _note_error(errors, "notifications_topic_url", ERROR_NOTIFICATIONS_URL_TOO_LONG)
        return FLASH_SAVE_FAILED
    # Both gates below exempt "" in addition to a real theme id: the
    # "Same as departures" chip submits "" for this field, and rejecting
    # it would reject the whole save whenever a user picks that option.
    if (
        submitted_calendar_theme_id is not None
        and submitted_calendar_theme_id not in ("",) + device_config.THEME_IDS
    ):
        _note_error(errors, "calendar_theme_id", ERROR_INVALID_CHOICE)
        return FLASH_SAVE_FAILED
    if (
        submitted_theme_arriving is not None
        and submitted_theme_arriving not in ("",) + device_config.THEME_IDS
    ):
        _note_error(errors, "theme_arriving", ERROR_INVALID_CHOICE)
        return FLASH_SAVE_FAILED
    if submitted_runway is not None and submitted_runway not in device_config.RUNWAY_IDS:
        _note_error(errors, "tracked_runway", ERROR_INVALID_CHOICE)
        return FLASH_SAVE_FAILED
    # A malformed value here is a real user error, reported at this
    # field; absent still means unchanged (including structural absence
    # on a scope that never rendered this group).
    if submitted_qh_start is not None and not _QUIET_HOURS_TIME_RE.match(submitted_qh_start):
        _note_error(errors, "quiet_hours_start", ERROR_QUIET_HOURS_TIME_SHAPE)
        return FLASH_SAVE_FAILED
    if submitted_qh_end is not None and not _QUIET_HOURS_TIME_RE.match(submitted_qh_end):
        _note_error(errors, "quiet_hours_end", ERROR_QUIET_HOURS_TIME_SHAPE)
        return FLASH_SAVE_FAILED
    # theme_arriving: out of scope or genuinely absent -> unchanged; ""
    # -> CLEAR_THEME_ARRIVING; anything else has already passed the
    # membership gate above, so it is a real theme id.
    if screens.GROUP_THEME not in in_scope:
        theme_arriving = None
    elif submitted_theme_arriving is None:
        theme_arriving = None
    elif submitted_theme_arriving == "":
        theme_arriving = device_config.CLEAR_THEME_ARRIVING
    else:
        theme_arriving = submitted_theme_arriving
    if submitted_led is None:
        led_enabled = None
    elif submitted_led == LED_CHECKBOX_VALUE:
        led_enabled = True
    else:
        _note_error(errors, "led_enabled", ERROR_UNEXPECTED_SWITCH_VALUE)
        return FLASH_SAVE_FAILED
    if submitted_qh_enabled is None:
        quiet_hours_enabled = None
    elif submitted_qh_enabled == QUIET_HOURS_CHECKBOX_VALUE:
        quiet_hours_enabled = True
    else:
        _note_error(errors, "quiet_hours_enabled", ERROR_UNEXPECTED_SWITCH_VALUE)
        return FLASH_SAVE_FAILED
    if submitted_wake_interval is None or submitted_wake_interval == "":
        wake_interval_s = None
    else:
        try:
            wake_interval_s = int(submitted_wake_interval)
        except ValueError:
            _note_error(errors, "wake_interval_s", ERROR_WAKE_INTERVAL_RANGE)
            return FLASH_SAVE_FAILED
        # A syntactically valid but out-of-range value would otherwise
        # only surface via save_device_config()'s own generic
        # ValueError; checked here to report it at this field.
        if not (
            device_config.WAKE_INTERVAL_MIN_S
            <= wake_interval_s
            <= device_config.WAKE_INTERVAL_MAX_S
        ):
            _note_error(errors, "wake_interval_s", ERROR_WAKE_INTERVAL_RANGE)
            return FLASH_SAVE_FAILED
    if submitted_display is None:
        display_enabled = None
    elif submitted_display == DISPLAY_CHECKBOX_VALUE:
        display_enabled = True
    else:
        _note_error(errors, "display_enabled", ERROR_UNEXPECTED_SWITCH_VALUE)
        return FLASH_SAVE_FAILED
    # Unlike the fields above, these two checkboxes DO resolve absent ->
    # False: their card is always in scope when rendered (see docstring).
    if screens.GROUP_NOTIFICATIONS not in in_scope:
        notifications = None
    else:
        if submitted_notifications_battery is None:
            notifications_battery = False
        elif submitted_notifications_battery == NOTIFICATIONS_BATTERY_CHECKBOX_VALUE:
            notifications_battery = True
        else:
            _note_error(errors, "notifications_battery", ERROR_UNEXPECTED_SWITCH_VALUE)
            return FLASH_SAVE_FAILED
        if submitted_notifications_silent is None:
            notifications_silent = False
        elif submitted_notifications_silent == NOTIFICATIONS_SILENT_CHECKBOX_VALUE:
            notifications_silent = True
        else:
            _note_error(errors, "notifications_silent", ERROR_UNEXPECTED_SWITCH_VALUE)
            return FLASH_SAVE_FAILED
        # An empty submission means leave the stored URL unchanged,
        # never clear it — there is no UI affordance to clear a
        # configured topic URL. Read fresh from disk rather than from
        # ctx, so this is correct even with a stale ctx.
        current_notifications_on_disk = device_config.load_device_config(
            state_dir)["notifications"]
        stripped_notifications_url = (submitted_notifications_topic_url or "").strip()
        notifications_topic_url = (
            stripped_notifications_url if stripped_notifications_url
            else current_notifications_on_disk.get("topic_url"))
        notifications = {
            "topic_url": notifications_topic_url,
            "battery_low": notifications_battery,
            "frame_silent": notifications_silent,
            # Written from the session's resolved language at save
            # time; there is no language-picking control for this
            # group (the poll loop has no browser to ask).
            "lang": ctx.get("lang") or device_config.DEFAULT_NOTIFICATIONS["lang"],
        }

    try:
        device_config.save_device_config(
            state_dir, theme=submitted_theme, theme_arriving=theme_arriving,
            tracked_runway=submitted_runway,
            led_enabled=led_enabled, quiet_hours_enabled=quiet_hours_enabled,
            quiet_hours_start=submitted_qh_start, quiet_hours_end=submitted_qh_end,
            wake_interval_s=wake_interval_s, display_enabled=display_enabled,
            calendar_theme_id=submitted_calendar_theme_id,
            screen_id=submitted_screen_id, notifications=notifications)
    except (ValueError, OSError):
        return FLASH_SAVE_FAILED

    if calendar_signal == CALENDAR_URL_SIGNAL_CLEAR:
        if not calendar_rules.save_calendar_url(
                state_dir, calendar_rules.CLEAR_CALENDAR_URL):
            return FLASH_SAVE_FAILED
    elif calendar_signal == CALENDAR_URL_SIGNAL_SET:
        if not calendar_rules.save_calendar_url(
                state_dir, submitted_calendar_url.strip()):
            return FLASH_SAVE_FAILED

    return FLASH_SAVED
