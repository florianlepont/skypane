"""companion/pages/config_page.py — CFG-01 (theme picker), CFG-12 (runway
picker), and CFG-07's "Trigger poll now" control (06-CONTEXT.md).

Both `render()` and `handle_post()` are real and live as of this plan
(06-07): the Theme and Runway fieldsets render from `server.device_config`'s
own registries with the current values pre-selected, and a POST validates
both fields against those same registries — server-side — before ever
calling `device_config.save_device_config()`. The "Trigger poll now"
control below is unrelated plumbing owned by companion/app.py (plan
06-05): its POST /poll-now target, cooldown gate, and in-process
server.poll_loop.run_once() call all live there, not here — this module
only renders the button/copy for it.
"""
import re

from companion import theme_preview
from companion.layout import escape_html
import companion.layout as layout
from companion import screens
from companion import wake
# Phase 15 D-10 (15-05-PLAN.md): the one deliberate exception to this
# package's own page-module-isolation convention (companion/pages/
# __init__.py; see airlines_page.py's own precedent comment for the same
# convention applied to server.plane imports). DELETE_BUTTON_TEXT is a
# single locked-English string with identical meaning on both pages — the
# rules list's per-row Delete button reuses it rather than minting a
# second string, exactly as the plan directs. This does not create an
# import cycle: airlines_page.py never imports config_page.py.
#
# 19-12-PLAN.md Task 2 (D-22, Device-page half): EDIT_QUERY_PARAM joins
# the same deliberate exception, for the identical reason — the Device
# page's "Edit artwork" link is built from airlines_page's own query-
# param constant rather than a retyped "edit" literal.
from companion.pages.airlines_page import DELETE_BUTTON_TEXT, EDIT_QUERY_PARAM
from server import device_config, panel_format
from server.plane import calendar_rules, colour_rules

# The single definition of this route prefix in the repository (06.4).
# companion/app.py rebinds it (RUNWAY_IMAGE_ROUTE_PREFIX =
# config_page.RUNWAY_IMAGE_ROUTE_PREFIX) rather than re-typing the
# literal, exactly as it already does for the FLASH_KEY_* constants —
# app.py imports this module, so the reverse import would be a cycle.
RUNWAY_IMAGE_ROUTE_PREFIX = "/runway-image/"
RUNWAY_IMAGE_ALT_TEMPLATE = "Airport diagram for %s"

# 06.6.4.1.1-05: same one-definition-site discipline as
# RUNWAY_IMAGE_ROUTE_PREFIX above, with the definition site inverted —
# the mechanism module (companion/theme_preview.py) owns the prefix and
# alt-text template here, not this emitter module, because both this
# module and companion/app.py need to rebind the same constant. The
# literal is still typed exactly once in the repository, in
# theme_preview.py.
THEME_PREVIEW_ROUTE_PREFIX = theme_preview.THEME_PREVIEW_ROUTE_PREFIX
THEME_PREVIEW_ALT_TEMPLATE = theme_preview.THEME_PREVIEW_ALT_TEMPLATE

# The single definition of this route in the repository (06.6.4.1, D-05/
# D-26). companion/app.py rebinds its own SETTINGS_ROUTE constant to this
# value rather than re-typing the literal (06.6.4.1-07), mirroring
# RUNWAY_IMAGE_ROUTE_PREFIX's own rebinding discipline above — app.py
# imports this module, so the reverse import would be a cycle. The old
# "/config" path is retired: it 404s by design, no redirect (D-26).
SETTINGS_ROUTE = "/settings"

# quick task 260901-re6: this value is interpolated twice — once as the
# settings <form>'s id, once as the dirty-bar save button's form
# attribute — and the two must never be re-typed as literals, because a
# mismatch produces a Save button that looks correct in markup and
# silently submits nothing. Same one-definition-site discipline as
# RUNWAY_IMAGE_ROUTE_PREFIX/SETTINGS_ROUTE above.
SETTINGS_FORM_ID = "settings-form"

# --- Phase 18 (companion audit / UX refactor): page scopes -------------
#
# The one settings form used to render every group on a single
# "/settings" page. It now renders as two pages sharing the same POST
# route and the same handle_post(): the everyday "Display" page (theme,
# quiet hours, screen on/off) and the advanced "Device" page (runway,
# diagnostic LED, wake interval, calendar, colour rules, manual
# refresh). Which groups land on which page is declared per screen type
# in companion/screens.py, not hard-coded here.
#
# `render(ctx)` with no scope keeps rendering the whole legacy page —
# every group, in the historical order — so existing harness checks
# against the full form stay meaningful. companion/app.py never uses
# that scope for a live route any more.
SCOPE_ALL = "all"
SCOPE_DISPLAY = "display"
SCOPE_DEVICE = "device"
SCOPES = (SCOPE_ALL, SCOPE_DISPLAY, SCOPE_DEVICE)

# Hidden form fields a scoped page submits so handle_post() knows which
# groups were on the page (absent checkbox => "leave unchanged" for a
# group that was never rendered, never "switch it off") and where to
# redirect back to.
SCOPE_FIELD_NAME = "scope"
RETURN_TO_FIELD_NAME = "return_to"

DISPLAY_PAGE_TITLE = "Display"
DISPLAY_PAGE_PURPOSE = (
    "How the frame looks. Changes reach the frame the next time it wakes up.")
DEVICE_PAGE_TITLE = "Device"
DEVICE_PAGE_PURPOSE = (
    "Hardware, data and diagnostics for the frame. Nothing here needs "
    "changing day to day.")
SCREEN_CAPTION_TEMPLATE = "Screen: %s"
# 19-12-PLAN.md Task 2 (D-23): the conditional screen-type <select> — an
# element id (not a class) because its own <label> targets it via `for`.
SCREEN_SELECTOR_ID = "screen-id-selector"
SCREEN_SELECTOR_LABEL_TEXT = "Screen type"
# The Device-page-only link to the artwork editor (D-22's Device-page
# half, 19-12-PLAN.md Task 2). Built from airlines_page.AIRLINES_ROUTE
# (rebound below as layout.AIRLINES_ROUTE, already duplicated there) and
# airlines_page.EDIT_QUERY_PARAM — never a retyped "/airlines?edit=1"
# literal.
EDIT_ARTWORK_LINK_TEXT = "Edit artwork"
EDIT_ARTWORK_LINK_CAPTION = "Opens Airlines with the artwork-editing forms available."


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
    return (
        screens.GROUP_THEME, screens.GROUP_RUNWAY, screens.GROUP_LED,
        screens.GROUP_QUIET_HOURS, screens.GROUP_WAKE_INTERVAL,
        screens.GROUP_DISPLAY, screens.GROUP_CALENDAR)


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

# The sole accepted submitted value for the LED checkbox (D-01) — shared
# by led_group()'s markup and handle_post()'s validator so the two can
# never drift apart.
LED_CHECKBOX_VALUE = "on"

# The sole accepted submitted value for the Quiet hours enable checkbox
# (10-05-PLAN.md), mirroring LED_CHECKBOX_VALUE's own rationale exactly:
# shared by quiet_hours_group()'s markup and handle_post()'s validator so
# the two can never drift apart.
QUIET_HOURS_CHECKBOX_VALUE = "on"

# The sole accepted submitted value for the Display enable checkbox
# (12-UI-SPEC.md), mirroring LED_CHECKBOX_VALUE's/QUIET_HOURS_CHECKBOX_VALUE's
# own rationale exactly: shared by display_group()'s markup and
# handle_post()'s validator so the two can never drift apart.
DISPLAY_CHECKBOX_VALUE = "on"

# Phase 15 D-05 (15-UI-SPEC.md Copywriting Contract): the arrivals-theme-
# override checkbox's sole accepted submitted value - a fourth consumer of
# the same absent-means-off idiom LED_CHECKBOX_VALUE/
# QUIET_HOURS_CHECKBOX_VALUE/DISPLAY_CHECKBOX_VALUE already establish,
# shared by theme_fieldset()'s markup and handle_post()'s validator so the
# two can never drift apart.
ARRIVING_CHECKBOX_VALUE = "on"
# An element id, not a class - unlike the three checkboxes above, this one
# is referenced by companion/static/style.css's `:has()` reveal selector,
# which must target one specific control rather than a class three other
# checkboxes on this page already share.
THEME_ARRIVING_TOGGLE_ID = "theme-arriving-toggle"
# The attribute-as-CSS-hook naming the revealed second (arrivals) chip
# grid, following this app's existing data-dirty-section/
# data-static-save-fallback/data-filter-group convention.
ARRIVAL_GRID_ATTR = "data-arrival-grid"
# Locked-English copy (15-UI-SPEC.md Copywriting Contract) - do not
# paraphrase.
THEME_ARRIVING_CHECKBOX_LABEL = "Use a different theme for arrivals"
THEME_DIRECTION_LABEL = "Arrivals theme"

# quick task 260901-re6: each settings group used to render a description
# sentence above its control (THEME_SECTION_DESCRIPTION/
# RUNWAY_SECTION_DESCRIPTION, D-02 06.6.4.1) AND a helper sentence below
# it (THEME_HELPER_TEXT/RUNWAY_HELPER_TEXT/LED_HELPER_TEXT) — Theme and
# Runway rendered both, LED escaped the doubling but kept its lone
# paragraph un-muted and positioned after its control instead of before.
# All five of those constants are retired outright. Each group now
# carries exactly one caption, rendered once, directly under the group
# heading and before the control, styled as a single muted sentence via
# a CSS modifier class in companion/static/style.css. The LED group is
# the odd one out only in that it never had a pair to merge — its single
# paragraph is reworded and relocated, not merged with anything.
#
# quick task 260901-s5o: a fourth caption, POLL_SECTION_CAPTION, joins
# the three above. Poll was never part of the description/helper merge
# those three came out of — it is a `<section class="page-section">`,
# not a `.theme-status` group, and had no paragraph of its own to merge.
# It was simply skipped, leaving the page's fourth section as the only
# one with a bare heading. This caption is new copy, validated against
# the Settings Save Bar Sketch, not merged from anything. Unlike the
# other three, it is consumed by a two-branch renderer
# (poll_trigger_section()), so it must be interpolated on both branches
# or it would silently vanish for the whole cooldown window.
THEME_SECTION_CAPTION = (
    "Panel colors for departing/arriving flights. Applies on the "
    "device's next scheduled poll, not immediately.")
RUNWAY_SECTION_CAPTION = (
    "Which Orly runway the device watches. Applies on the next "
    "scheduled poll, not immediately.")
LED_SECTION_CAPTION = (
    "Lit only during the device's brief wake window, not visible from "
    "the wall side. Applies on the next scheduled poll.")

# 19-11-PLAN.md Task 3 (D-12/A-30): stable DOM ids for the group headings
# a radiogroup's aria-labelledby points at, and for each hint paragraph
# an aria-describedby points at — constants here, never a literal at a
# render site, matching this file's own convention (see e.g.
# RUNWAY_IMAGE_ROUTE_PREFIX above). Only the groups that actually gain
# `role="radiogroup"` (the two theme chip grids and the runway row) get
# a *_GROUP_HEADING_ID; every hint below gets a *_CAPTION_ID/*_HINT_ID
# regardless, since a hint can describe a single-control field too (a
# checkbox, a time/number input, a <select>) with no radiogroup at all.
THEME_SECTION_CAPTION_ID = "theme-caption"
THEME_GROUP_HEADING_ID = "theme-group-heading"
THEME_ARRIVING_GROUP_HEADING_ID = "theme-arriving-group-heading"
RUNWAY_SECTION_CAPTION_ID = "runway-caption"
RUNWAY_GROUP_HEADING_ID = "runway-group-heading"
LED_SECTION_CAPTION_ID = "led-caption"
POLL_SECTION_HEADING = "Manual refresh"
POLL_SECTION_CAPTION = (
    "Manually trigger an immediate poll cycle instead of waiting for "
    "the next scheduled one.")
# D-05 (06.6.4.1): the LED group's new user-facing heading, once it moves
# from its own <fieldset>/<legend> into a sibling <h2>-headed group of
# the merged form — see led_group() below.
LED_SECTION_HEADING = "Diagnostic LED"

# 10-05-PLAN.md / 10-UI-SPEC.md Copywriting Contract: the Quiet hours
# group's heading and caption, locked verbatim. Unlike Theme/Runway/LED's
# captions, this one deliberately restates the "could now be hours away"
# duration caveat (D-02) directly in its own sentence, rather than a
# separate flash message — this is the one settings field on the page
# whose wait can stretch from minutes to hours.
QUIET_HOURS_SECTION_HEADING = "Quiet hours"
QUIET_HOURS_SECTION_CAPTION = (
    "Pauses the frame's wake, poll and display cycle overnight. Applies "
    "on the next scheduled poll, which may now be hours away.")
# 19-11-PLAN.md Task 3 (D-12/A-30): see THEME_SECTION_CAPTION_ID's own
# comment above.
QUIET_HOURS_SECTION_CAPTION_ID = "quiet-hours-caption"

# 19-10-PLAN.md (D-14/S-04): three one-tap presets, client-side only - no
# server change (see quiet_hours_group()'s docstring). The Night preset's
# start/end are sourced from server.device_config's own shipped defaults
# rather than retyped literals, so the preset and the default can never
# drift apart. Ranges use a real U+2013 en dash, matching this module's
# real-Unicode punctuation convention (see its em dashes elsewhere).
QUIET_HOURS_PRESET_NIGHT_START = device_config.DEFAULT_QUIET_HOURS_START
QUIET_HOURS_PRESET_NIGHT_END = device_config.DEFAULT_QUIET_HOURS_END
QUIET_HOURS_PRESET_NIGHT_LABEL = "Night (%s–%s)" % (
    QUIET_HOURS_PRESET_NIGHT_START, QUIET_HOURS_PRESET_NIGHT_END)
QUIET_HOURS_PRESET_WORKDAY_START = "08:00"
QUIET_HOURS_PRESET_WORKDAY_END = "18:00"
QUIET_HOURS_PRESET_WORKDAY_LABEL = "Work day (%s–%s)" % (
    QUIET_HOURS_PRESET_WORKDAY_START, QUIET_HOURS_PRESET_WORKDAY_END)
# "Always on (off)": this preset UNCHECKS the enable checkbox and leaves
# both times untouched - "off" means the curfew is disabled while the
# configured window stays intact, the pre-configure-before-enabling
# behaviour quiet_hours_group()'s own docstring already locks. Expressed
# via a distinct data-preset-enabled="0" attribute rather than
# overloading the time attributes with a sentinel value.
QUIET_HOURS_PRESET_ALWAYS_ON_LABEL = "Always on (off)"
QUIET_HOURS_PRESET_ATTR = "data-quiet-preset"

# 11-UI-SPEC.md Copywriting Contract, locked verbatim (D-05). The caption's
# closing sentence deliberately reuses the same "Applies on the next
# scheduled poll" clause every sibling caption ends on (D-06 — no new
# apply-timing mechanism exists for this field either). The placeholder is
# a legitimate empty state (D-07: "never explicitly set"), not an error
# state — it names the fallback behavior instead of showing a fabricated
# number.
WAKE_INTERVAL_SECTION_HEADING = "Wake interval"
WAKE_INTERVAL_SECTION_CAPTION = (
    "How often the frame wakes to poll for updates. Shorter means "
    "fresher info and more battery drain; longer means more battery "
    "life and staler info at a glance. Applies on the next scheduled "
    "poll.")
WAKE_INTERVAL_PLACEHOLDER_TEXT = "Uses server default"
# 19-11-PLAN.md Task 3 (D-12/A-30): see THEME_SECTION_CAPTION_ID's own
# comment above.
WAKE_INTERVAL_SECTION_CAPTION_ID = "wake-interval-caption"

# 12-UI-SPEC.md Copywriting Contract, locked verbatim (D-02, 12-CONTEXT.md).
# Unlike every other caption on this page, this one does not reuse the
# generic "applies on the next scheduled poll" clause: while the display is
# off, the device does not follow wake_interval_s or quiet hours at all — D-01
# pins the off-state check-in to a fixed 300s cadence, independent of both —
# so this field's apply-timing genuinely differs and earns its own honest
# sentence instead. The caption must never say "instant" or "immediate" —
# D-02 is explicit the change is not, and the UI must not imply otherwise.
DISPLAY_SECTION_HEADING = "Screen on / off"
DISPLAY_SECTION_CAPTION = (
    "Turns the physical panel off remotely, without touching the "
    "hardware. Takes effect within about 5 minutes, both switching off "
    "and back on.")
# 19-11-PLAN.md Task 3 (D-12/A-30): see THEME_SECTION_CAPTION_ID's own
# comment above.
DISPLAY_SECTION_CAPTION_ID = "display-caption"

# Read elsewhere, not just here — this module's existing
# duplicated-not-imported must-equal discipline (matches
# OPEN_CLASS/MOBILE_NAV_OPEN_CLASS's own precedent): DIRTY_SECTION_ATTR
# is read by companion/static/dirty-state.js (the section-aware
# [data-dirty-count] copy walks every element carrying this attribute),
# and STATIC_SAVE_FALLBACK_ATTR is read by a `.js`-gated rule in
# companion/static/style.css (`.js [data-static-save-fallback] {
# display: none; }`, landed by 06.6.4.1-01). Neither file imports this
# module — the values must be kept equal by hand.
DIRTY_SECTION_ATTR = "data-dirty-section"
STATIC_SAVE_FALLBACK_ATTR = "data-static-save-fallback"
# D-03: the dirty-bar's seeded [data-dirty-count] text before
# dirty-state.js's own section-aware copy ever runs (a no-JS page, or
# the brief window before the script executes, would otherwise show
# this raw string).
DIRTY_BAR_INITIAL_TEXT = "Unsaved changes"

# Matches 06-UI-SPEC.md's Copywriting Contract "Poll-trigger cooldown"
# row verbatim (D-17); "{n}" is filled in with a server-computed
# remaining-seconds figure, never anything client-supplied. This text is
# intentionally the *button-adjacent* copy shown while the trigger is
# disabled — a separate rendering site from companion/app.py's own
# FLASH_MESSAGES entry for the same event (the post-redirect flash
# banner), not a shared constant, since a page module must never import
# companion/app.py (that would be a cycle: app.py already imports this
# module).
POLL_COOLDOWN_HELPER_TEXT = "Poll triggered recently — try again in {n}s."

# DOM ids the D-01 live countdown script (companion/static/
# poll-cooldown.js as of 19-04-PLAN.md/D-18) hooks with
# document.getElementById() — shared between poll_trigger_section()'s
# markup and the script so the two can never drift apart.
POLL_TRIGGER_BUTTON_ID = "poll-trigger-btn"
POLL_COOLDOWN_TEXT_ID = "poll-cooldown-text"

# UXA-15: the enabled (zero-cooldown) branch's button label while a
# submit is pending, swapped in by companion/static/poll-cooldown.js
# (19-04-PLAN.md/D-18) via the button's data-submit-pending attribute.
# Cosmetic only — companion/app.py's _POLL_LOCK is the actual
# correctness boundary, this is purely the immediate-feedback
# affordance.
POLL_SUBMIT_PENDING_TEXT = "Polling…"

# The placeholder the client substitutes the live second count into. The
# countdown reuses POLL_COOLDOWN_HELPER_TEXT with this token standing in
# for the "{n}" slot precisely so the ticking copy stays word-identical to
# the static, server-rendered copy above and to companion/app.py's
# FLASH_MESSAGES[FLASH_KEY_POLL_COOLDOWN] post-redirect banner. The copy
# exists in one place (this constant) and is formatted twice — once with
# a real integer for the no-JS render, once with this token for the
# script template — never rewritten or duplicated.
POLL_COOLDOWN_TEMPLATE_TOKEN = "__N__"

# The four flash keys this module's handle_post() can return, defined
# here — the single source of truth companion/app.py's own flash-key
# constants and FLASH_MESSAGES dict reference, per this plan's Task 2
# ("the key strings exist in exactly one place"). Values match
# companion/app.py's pre-existing FLASH_KEY_* string literals exactly, so
# a redirect's ?flash= query parameter round-trips through
# app.py's FLASH_MESSAGES lookup unchanged.
FLASH_SAVED = "saved"
FLASH_SAVE_FAILED = "save_failed"
FLASH_POLL_TRIGGERED = "poll_triggered"
FLASH_POLL_COOLDOWN = "poll_cooldown"
# Distinct from FLASH_SAVE_FAILED (2026-08-28 fix): a run_once() exception
# inside POST /poll-now used to redirect with FLASH_SAVE_FAILED, showing
# "Couldn't save settings" for a failure that has nothing to do with
# saving settings — confusing and actively misleading about what broke.
FLASH_POLL_FAILED = "poll_failed"
# Distinct from FLASH_POLL_COOLDOWN (UXA-15 fix): the cooldown key means
# "wait, you already triggered one recently" (a stale, seconds-old fact
# checked against history_db). This key means "a poll is executing on
# this exact request, right now, in another thread" — companion/app.py's
# non-blocking `_POLL_LOCK.acquire(blocking=False)` failing is the only
# thing that ever produces it, closing the TOCTOU window where two
# requests arriving before the first finishes could both observe zero
# cooldown and both call `poll_loop.run_once()`.
FLASH_POLL_ALREADY_RUNNING = "poll_already_running"

# Phase 15 D-10/D-11 (15-05-PLAN.md): the per-flight colour-rules editor's
# route constants, mirroring how airlines_page.py owns RESOLVE_ROUTE/
# MANUAL_DELETE_ROUTE_PREFIX/_SUFFIX and companion/app.py rebinds them
# rather than re-typing the literals. Add and delete are immediate POSTs
# on their own routes, outside SETTINGS_ROUTE and the settings form's
# unsaved-changes dirty bar — a rule is a one-step immediate act, not a
# pending edit.
RULES_ADD_ROUTE = "/settings/rules/add"
RULES_DELETE_ROUTE_PREFIX = "/settings/rules/"
RULES_DELETE_ROUTE_SUFFIX = "/delete"

# 19-11-PLAN.md Task 1 (D-08/A-26): the calendar disconnect action's own
# route, following RULES_ADD_ROUTE's exact naming/rebinding convention
# immediately above — companion/app.py rebinds this rather than
# retyping the literal, since app.py imports this module (the reverse
# import would be a cycle). An immediate, session-gated POST outside
# SETTINGS_ROUTE and the settings form's dirty bar, for the identical
# reason a colour rule's add/delete are: this is a one-step act, not a
# pending settings edit.
CALENDAR_DISCONNECT_ROUTE = "/settings/calendar/disconnect"

# Locked-English copy (15-UI-SPEC.md Copywriting Contract, Rules
# section) - verbatim, do not paraphrase.
RULES_SECTION_HEADING = "Per-flight colour rules"
RULES_SECTION_CAPTION = (
    "Override the theme for one exact flight, aircraft, or carrier. Most "
    "specific match wins — a callsign rule beats a hex rule, which beats "
    "a prefix rule — and adding a key that's already in use replaces the "
    "existing rule for it. Applies on the frame's next scheduled poll, "
    "not immediately.")
RULE_KIND_FIELD_LABEL = "Match by"
RULE_VALUE_FIELD_LABEL = "Value"
RULE_THEME_FIELD_LABEL = "Theme"
RULE_ADD_BUTTON_TEXT = "Add rule"
# An ordered mapping from each colour_rules.RULE_KINDS member to its
# label - used by BOTH the add form's <option> text and the list's Kind
# cell, so the two can never disagree (15-UI-SPEC.md: "never abbreviated
# differently in the list than in the form").
RULE_KIND_LABELS = {
    colour_rules.RULE_KIND_CALLSIGN: "Callsign",
    colour_rules.RULE_KIND_HEX: "ICAO24 hex",
    colour_rules.RULE_KIND_PREFIX: "Callsign prefix",
}
RULE_VALUE_HINT = (
    "Exact callsign (e.g. AFR1234), ICAO24 hex (e.g. 3944F2), or a "
    "3-letter prefix (e.g. AFR) — matching the kind selected above.")
RULES_EMPTY_HEADING = "No rules yet"
RULES_EMPTY_BODY = (
    "Add one above to give a specific flight, aircraft, or carrier its "
    "own theme, regardless of direction.")
# A trailing empty header for the delete column, matching
# _manual_resolution_table_html()'s own trailing empty <th>.
RULE_HEADERS = ("Kind", "Key", "Theme", "Added", "")

# The seven flash keys this module's rule-add/rule-delete routes (owned by
# companion/app.py, Task 2) can produce, defined here for the identical
# reason FLASH_SAVED/FLASH_SAVE_FAILED/etc. above are: companion/app.py
# rebinds each under its own FLASH_KEY_RULE_* name and owns the message
# text/ARIA role, mirroring the FLASH_MANUAL_* rebinding pattern
# airlines_page.py already establishes.
FLASH_RULE_ADDED = "rule_added"
FLASH_RULE_REPLACED = "rule_replaced"
FLASH_RULE_KEY_INVALID = "rule_key_invalid"
FLASH_RULE_REGISTRY_FULL = "rule_registry_full"
FLASH_RULE_SAVE_FAILED = "rule_save_failed"
FLASH_RULE_DELETED = "rule_deleted"
FLASH_RULE_DELETE_FAILED = "rule_delete_failed"

# Phase 16 (16-05-PLAN.md, 16-UI-SPEC.md Copywriting Contract) - verbatim,
# do not paraphrase. Every string below is written against
# .planning/ROADMAP.md's Phase 16 measured finding 3: on the one measured
# duty day, none of the calendar owner's three flights were among the
# frame's 201 detections. This feature can only colour a flight that
# happens to be the one currently on screen - it does not track, watch,
# follow, monitor, notify, or know a flight is happening independently of
# what is on screen, and no string here may imply otherwise.
CALENDAR_SECTION_HEADING = "Calendar"
CALENDAR_SECTION_CAPTION = (
    "When the flight the frame is currently showing is one your "
    "connected calendar lists, it uses this theme instead of the usual "
    "one. It can only colour a flight that happens to be on screen — "
    "it does not track or announce anything on its own. Applies on the "
    "frame's next scheduled poll, not immediately.")
CALENDAR_STATUS_NOT_CONFIGURED = (
    "Not connected. Paste your calendar's feed URL below to connect one.")
CALENDAR_STATUS_CONFIGURED_PENDING = "Connected — waiting for the first sync."
# The relative-timestamp slot is left open so calendar_group() can
# interpolate concise_timestamp_html()'s raw markup without the escaping
# collision a single format string would create.
CALENDAR_STATUS_CONFIGURED_SYNCED_PREFIX = "Connected — last synced "
CALENDAR_THEME_FIELD_LABEL = "Theme"
# Deliberate repeat of the caption's own core constraint, placed right
# where the operator picks the theme (16-UI-SPEC.md's own stated
# reasoning): this is the single sentence most likely to be skimmed past
# if it appears only once, at the top of the section.
CALENDAR_THEME_HINT = (
    "Used only when a flight from the calendar happens to be the one on "
    "screen.")
# 19-11-PLAN.md Task 3 (D-12/A-30): see THEME_SECTION_CAPTION_ID's own
# comment above — these two calendar hints are per-field, not
# group-level, but link to their control the identical way.
CALENDAR_THEME_HINT_ID = "calendar-theme-hint"

# Phase 17 plan 03 (D-01/D-02/D-07) — Claude's-discretion wording, final
# once written, matching the locked Phase 16 register above: plain,
# honest, no surveillance verb, no promise the frame cannot keep. The
# file the URL is stored in is never named anywhere below — the
# developer pushed back explicitly on being shown implementation
# mechanics without being told they were mechanics (17-CONTEXT.md
# Specifics).
CALENDAR_URL_FIELD_LABEL = "Calendar feed URL"
CALENDAR_URL_HINT = (
    "Your calendar's private iCal link. Stored on the server and never "
    "shown back here — pasting a new one replaces the old.")
CALENDAR_URL_HINT_ID = "calendar-url-hint"
# Names both halves of what disconnecting does (D-07): the operator
# deserves to see the flights-deletion consequence before they act, not
# discover it afterwards. 19-11-PLAN.md (D-08/A-26): the in-form checkbox
# this label used to sit beside is retired — the same wording now labels
# the standalone disconnect button calendar_disconnect_section() renders
# (below) and, unchanged, the confirmation copy the frame's disconnect
# promise keeps.
CALENDAR_DISCONNECT_CHECKBOX_LABEL = (
    "Disconnect this calendar and delete the flights it supplied")
# Matches the shape of LED_CHECKBOX_VALUE/QUIET_HOURS_CHECKBOX_VALUE/
# DISPLAY_CHECKBOX_VALUE/ARRIVING_CHECKBOX_VALUE above. 19-11-PLAN.md
# (D-08/A-26): the checkbox markup that used to submit this value is
# retired, but the value itself is NOT — submitted_calendar_signal()'s
# gates 1-3 below still compare a submitted calendar_disconnect field
# against it, kept deliberately reachable for a hostile client crafting
# that field into a /settings POST (19-RESEARCH.md Pitfall 7). The
# dedicated CALENDAR_DISCONNECT_ROUTE below never reads this value at
# all — it always means "disconnect", once its own confirm gate passes.
CALENDAR_DISCONNECT_CHECKBOX_VALUE = "on"

# 19-11-PLAN.md Task 1 (D-08/A-26): the dedicated disconnect route's own
# confirm gate — the single definition site the markup
# (calendar_disconnect_section()/calendar_disconnect_confirm_page()
# below), the client-side misclick guard (companion/static/
# confirm-submit.js, Task 2), and the handler
# (companion/app.py's _handle_calendar_disconnect_post()) all read,
# rather than each retyping the field name/accepted value as a literal.
# Deliberately a different field name from calendar_disconnect above —
# the two routes' confirm semantics must never be conflated: this field
# means "the confirmation step passed", that one meant "the in-form
# checkbox was ticked".
CALENDAR_DISCONNECT_CONFIRM_FIELD = "confirm"
CALENDAR_DISCONNECT_CONFIRM_VALUE = "yes"
# The question companion/static/confirm-submit.js passes to
# window.confirm() (a misclick guard only — see that file's own header
# comment) — carried to the browser via calendar_disconnect_section()'s
# own data-confirm attribute, never duplicated in the script itself.
CALENDAR_DISCONNECT_CONFIRM_QUESTION = (
    "Disconnect this calendar and delete the flights it supplied?")
# The server-rendered two-step confirmation page's own copy
# (calendar_disconnect_confirm_page() below) — what a no-JS or
# CSP-blocked browser sees instead of the native dialog above. States
# the same consequence in a full sentence, since there is no button
# label length constraint here the way there is on the standalone
# button.
CALENDAR_DISCONNECT_CONFIRM_HEADING = "Disconnect calendar?"
CALENDAR_DISCONNECT_CONFIRM_SENTENCE = (
    "This disconnects your calendar and deletes the flights it "
    "supplied from the server. This can't be undone — you'd need to "
    "paste the feed URL again to reconnect.")
CALENDAR_DISCONNECT_CONFIRM_BUTTON_TEXT = "Disconnect calendar"
CALENDAR_DISCONNECT_CANCEL_TEXT = "Cancel"
# D-02's fourth status state: the one string in this interface permitted
# to reference "the server", because it is the one case where the
# operator has to act there. Names no path, no filename, no part of the
# URL. Deliberately carries no apostrophe/quote/ampersand — calendar_
# group() interpolates every status string through escape_html(), and a
# literal-substring check against the raw constant (this module's own
# Task 1 verification) would otherwise be comparing against a character
# escape_html() rewrites (the same apostrophe-escaping surprise plan
# 17-02 recorded for CALENDAR_STATUS_NOT_CONFIGURED).
CALENDAR_STATUS_PERMISSION_UNSAFE = (
    "Connected, but ignored — its saved link on the server became "
    "readable beyond this frame. Paste the feed URL again below to "
    "store it safely.")
# A shape bound against an absurd paste, not a definition of an
# acceptable URL. The single arbiter of whether a URL is acceptable
# stays the existing server-side safety gate (calendar_rules._url_is_
# safe()) and the fetch itself; a second definition here would drift
# from that one and start refusing feeds the fetch would accept.
CALENDAR_URL_MAX_LEN = 2048

# Phase 17 plan 04 (D-06/D-09): the four flash keys the save-triggered
# immediate sync can produce, defined here for the identical reason
# FLASH_SAVED/FLASH_POLL_TRIGGERED/etc. above are — companion/app.py
# rebinds each under its own FLASH_KEY_CALENDAR_* name and owns the
# message text/ARIA role, mirroring that same rebinding pattern exactly.
FLASH_CALENDAR_CONNECTED = "calendar_connected"
FLASH_CALENDAR_SYNC_FAILED = "calendar_sync_failed"
FLASH_CALENDAR_DISCONNECTED = "calendar_disconnected"
FLASH_CALENDAR_SYNC_DEFERRED = "calendar_sync_deferred"


def _field_error_html(errors, field, control_id):
    """D-07 (19-07-PLAN.md Task 2): the empty string when `field` carries
    no message in `errors` (which is `None` or `{}` for every render()
    call this plan does not itself add — every existing call site keeps
    emitting nothing here), otherwise a single `role="alert"` paragraph
    rendered immediately after the offending control:
    `<p class="field-error text-label" id="{control_id}-error"
    role="alert">{escaped message}</p>`. `control_id` need not match any
    real DOM `id` already on the control — it exists solely to build a
    stable anchor id that `_field_error_attrs()` below points
    `aria-describedby` at from that SAME control, so the message is
    programmatically associated, not merely visually adjacent. The
    message is interpolated through `escape_html()`, this file's
    universal escaping choke point, matching every other dynamic string
    in this module (T-19-26: never into a script or style context).
    """
    message = errors.get(field) if errors else None
    if not message:
        return ""
    return (
        '<p class="field-error text-label" id="%s-error" role="alert">%s</p>'
    ) % (escape_html(control_id), escape_html(message))


def _describedby_attr(*ids):
    """19-11-PLAN.md Task 3 (D-12/A-30): the single builder of every
    `aria-describedby` attribute fragment this file emits. Drops every
    falsy id — so a caller can pass a hint id and an error id (which is
    often `None`/`""`) side by side with no conditional of its own — and
    joins the survivors with ONE space, in the order given (this file's
    own convention below is always hint first, then error). Returns the
    empty string when no id survives, so no control this file renders
    ever emits a bare `aria-describedby=""`.
    """
    present = [control_id for control_id in ids if control_id]
    if not present:
        return ""
    return ' aria-describedby="%s"' % escape_html(" ".join(present))


# 19-12-PLAN.md Task 3 (D-13): the suffix template appended to a
# caption's own "Applies on the next scheduled poll" clause when the
# next-wake value is known — never baked into the caption constant
# itself (D-13 says "where the value is known", so the caption must
# read exactly as it does today when it is not).
NEXT_WAKE_CAPTION_SUFFIX_TEMPLATE = " (next wake ≈ %s)"


def _with_next_wake(caption, next_wake_clock):
    """`caption` unchanged when `next_wake_clock` is falsy (D-13: no
    placeholder, no "unknown" — the caption reads exactly as it did
    before this plan); otherwise `caption` plus
    `NEXT_WAKE_CAPTION_SUFFIX_TEMPLATE % next_wake_clock`, appended at
    RENDER time. The single implementation every caption site below
    uses, so none hand-concatenates its own suffix.

    `DISPLAY_SECTION_CAPTION` deliberately never calls this: it states
    its own honest ~5-minute screen-off latency instead of the generic
    "next scheduled poll" clause (12-CONTEXT.md D-01), and appending a
    wake-interval-derived figure there would contradict that sentence —
    see `render()`'s own comment at that group for the same exception.
    """
    if not next_wake_clock:
        return caption
    return caption + (NEXT_WAKE_CAPTION_SUFFIX_TEMPLATE % next_wake_clock)


def _field_error_attrs(errors, field, control_id, hint_id=None):
    """The ARIA attribute fragment for the control `_field_error_html()`
    above just built an error anchor for, folding in an optional
    `hint_id` (19-11-PLAN.md Task 3, D-12/A-30) via `_describedby_attr()`
    above — hint first, then the error id, matching that helper's own
    documented order. `hint_id` defaults to `None` so every pre-Task-3
    call site (which never passed it) keeps emitting byte-identical
    output: with no error and no hint, this still returns `""`.

    Three shapes, depending on what's present:
      - no error, no `hint_id`: `""` (unchanged since 19-07-PLAN.md).
      - no error, a `hint_id`: ` aria-describedby="{hint_id}"` alone —
        no `aria-invalid`, since there is nothing invalid to report.
      - an error (`hint_id` present or not): ` aria-invalid="true"`
        plus a combined `aria-describedby` naming the hint (if given)
        and `{control_id}-error` (`_field_error_html()`'s own anchor
        id), in that order.

    Applied to controls that have exactly one natural DOM element to
    decorate (a text/number/time input, a checkbox, or a `<select>`);
    the three radio-group fields (theme, theme_arriving, tracked_runway)
    render their error message the same way but skip this attribute
    fragment entirely — no single native input in a same-named radio
    group is uniquely "the" control to describe, and (Task 3) their
    hint linking instead lands on the `role="radiogroup"` CONTAINER via
    a direct `_describedby_attr(hint_id)` call at each of those two call
    sites, never through this function.
    """
    has_error = bool(errors and errors.get(field))
    error_id = ("%s-error" % control_id) if has_error else None
    describedby = _describedby_attr(hint_id, error_id)
    if has_error:
        return ' aria-invalid="true"%s' % describedby
    return describedby


def _submitted_or_current(submitted, field, current):
    """This file's explicit-`is None` fallback idiom (see the
    current_wake_interval_s comment inside render() below), applied to a
    rejected save's repopulation: `submitted[field]` when `field` is
    PRESENT in `submitted` — an empty string is a meaningful submitted
    value, never treated as absent — else `current`. `submitted` is
    `None` for every render() call that is not re-rendering a rejected
    save (nothing to repopulate from, so `current` — the on-disk/ctx
    value — always wins). Never `or`.
    """
    if submitted is not None and field in submitted:
        return submitted[field]
    return current


def _submitted_checkbox_checked(submitted, field, checked_value, current_checked):
    """The rendered `checked` state for one of the absent-means-False
    checkbox fields (led_enabled/quiet_hours_enabled/display_enabled/
    theme_arriving_enabled) on a rejected save's re-render.

    When a real submission happened (`submitted is not None` — always a
    dict, even an empty one, once a POST reaches this module:
    companion/app.py's `read_form()` never returns `None`), an absent
    field means unchecked — the identical absent-means-False semantics
    `handle_post()` itself just applied to the same submission — and a
    present-but-wrong value still renders unchecked (the field's own
    error message is what reports the problem, never a bogus stuck-on
    box). `submitted is None` (every ordinary page-load render(), never
    a rejected-save re-render) falls back to `current_checked`
    untouched — this is why `render()` below must NOT collapse a `None`
    `submitted` to `{}`: doing so would make every ordinary page load
    render every checkbox in this family unchecked, since an ordinary
    load never real-submits any of them either.
    """
    if submitted is None:
        return bool(current_checked)
    return submitted.get(field) == checked_value


def _palette_hex(index):
    """`#RRGGBB`, computed from `server.panel_format.PALETTE_RGB`'s flat
    int list at palette index `index` — never a hardcoded hex literal, so
    a future re-tuning of the physical panel ink (07-01-PLAN.md's own
    real-glass Blue/Green correction precedent) automatically updates
    every swatch that calls this helper.
    """
    r, g, b = panel_format.PALETTE_RGB[index * 3: index * 3 + 3]
    return "#%02X%02X%02X" % (r, g, b)


def _theme_chip_grid_html(field_name, selected_theme_id, extra_class="", extra_attr=""):
    """Phase 15 D-05: the chip-grid renderer `theme_fieldset()` calls
    TWICE — once for the always-present departures grid
    (`field_name="theme"`, no `extra_class`/`extra_attr`, so it renders
    byte-identical to the pre-Phase-14 markup: `<div class=
    "theme-chip-grid">`), once for the revealed arrivals grid
    (`field_name="theme_arriving"`, `extra_class="theme-chip-grid--
    arrivals"`, `extra_attr=ARRIVAL_GRID_ATTR`). Factored out of
    `theme_fieldset()`'s old single inline loop so the two grids can never
    drift apart: they differ ONLY in the radio group's `name`, which chip
    is marked `checked`/`--selected`, and this grid's own wrapper class/
    attribute — everything else (the hidden-radio selectable-card idiom,
    the `/theme-preview/{id}.png` source, the `_palette_hex()` swatch
    dots, the check glyph) is one shared definition.
    """
    chips = []
    for theme_id in device_config.THEME_IDS:
        selected = theme_id == selected_theme_id
        checked = " checked" if selected else ""
        chip_class = (
            "theme-chip theme-chip--selected" if selected else "theme-chip")
        theme = device_config.THEMES[theme_id]
        label = device_config.theme_label(theme_id)
        escaped_id = escape_html(theme_id)
        departing_hex = _palette_hex(theme["departing_index"])
        arriving_hex = _palette_hex(theme["arriving_index"])
        chips.append(
            '<label class="%s">'
            '<input type="radio" name="%s" value="%s" class="visually-hidden"%s>'
            '<img class="theme-chip__preview" src="%s%s.png" alt="%s" '
            'width="320" height="120" loading="lazy" style="background:%s">'
            '<span class="theme-chip__body">'
            '<span class="theme-chip__name">%s</span>'
            '<span class="theme-chip__swatches" aria-hidden="true">'
            '<span class="theme-chip__dot" style="background:%s"></span>'
            '<span class="theme-chip__dot" style="background:%s"></span>'
            "</span>"
            "</span>"
            '<span class="theme-chip__check">%s<span class="visually-hidden">Selected</span></span>'
            "</label>"
            % (
                chip_class, escape_html(field_name), escaped_id, checked,
                THEME_PREVIEW_ROUTE_PREFIX, escaped_id,
                escape_html(THEME_PREVIEW_ALT_TEMPLATE % label),
                escape_html(departing_hex),
                escape_html(label),
                escape_html(departing_hex), escape_html(arriving_hex),
                layout.icon_html("icon-check"),
            )
        )
    grid_class = "theme-chip-grid"
    if extra_class:
        grid_class = grid_class + " " + extra_class
    attr_html = (" %s" % extra_attr) if extra_attr else ""
    return '<div class="%s"%s>%s</div>' % (grid_class, attr_html, "".join(chips))


def theme_fieldset(
        current_theme_id, current_theme_arriving=None, errors=None, submitted=None,
        next_wake_clock=None):
    """D-04: a read-only theme status block when exactly one theme is
    registered (`len(device_config.THEME_IDS) == 1`) — a one-option radio
    group has no real decision value. Falls back to the editable D-01
    chip-grid markup below the moment a second theme is registered; this
    is a `len()` check, not a hardcoded single-theme assumption.

    Both branches render the same single `THEME_SECTION_CAPTION`
    paragraph directly under the `<h2>` heading (quick task 260901-re6)
    — `caption_html` below is computed once and reused by both, rather
    than each branch carrying its own copy of the markup template.

    06.6.4.1.1-05 (D-01/D-02/D-03/D-08, sketch 004 variant B — the
    developer-confirmed winner): the multi-theme branch no longer emits a
    `<fieldset>`/`<legend>` radio list. It now emits a `.theme-status`
    card (the same wrapper Runway and Diagnostic LED already use) holding
    a `.theme-chip-grid` of one `.theme-chip` per `THEME_IDS` entry — a
    compact, wrapping card, not stacked 44px native radios. This means
    the whole rendered Settings page now emits zero `<fieldset>` and zero
    `<legend>` elements: all four groups (Theme, Runway, Diagnostic LED,
    Poll) are named by an `<h2 class="text-heading">` at one consistent
    heading level.

    Each chip reuses `.runway-card`'s own selectable-card mechanism
    verbatim: a visually-hidden native radio inside the `<label>`, so
    keyboard and no-JS selection keep working natively; a `--selected`
    modifier and the radio's `checked` attribute computed from the SAME
    server-side membership comparison (`theme_id == current_theme_id`),
    never a client-side `:has()` trick; and an always-present check glyph
    whose visibility follows the CSS modifier alone. The radio's `name`,
    `value`, and `checked` semantics are byte-for-byte unchanged from the
    retired radio-list markup, so `handle_post()`'s existing
    `device_config.THEME_IDS` membership validation keeps working
    untouched.

    Each chip additionally carries a real rendered preview (D-03/D-04):
    an `<img>` pointing at the plan-01 `/theme-preview/{id}.png` route
    (rebound above as `THEME_PREVIEW_ROUTE_PREFIX`), with
    `style="background:{departing_hex}"` as a graceful-degradation
    fallback if that theme's render ever 404s — the chip still shows that
    theme's own colour instead of a broken-image glyph. `width`/`height`
    are the real served pixel dimensions (not a CSS `aspect-ratio`, per
    UIR-07's lesson) so the browser reserves the correct box before the
    image arrives, and `loading="lazy"` keeps below-the-fold chips off
    the critical path (mirroring the Airlines gallery's own precedent).

    Phase 15 D-05: `current_theme_arriving` (an id or `None`, defaulting
    to `None` so every pre-Phase-14 call site keeps working unchanged)
    extends the multi-theme branch with a `settings-checkbox` toggle plus
    a SECOND, identical chip grid for the arrivals override — both always
    rendered in the HTML (the CSS-only `:has()` reveal in
    companion/static/style.css hides the second grid when the box is
    unchecked; a browser without `:has()` support just always shows both,
    denser but never broken). The single-theme read-only branch above is
    untouched: a one-option "choice" has no arrivals override worth
    offering either. The second grid pre-selects the EFFECTIVE arrivals
    theme — `current_theme_arriving` when set, otherwise the same
    `current_theme_id` the first grid has selected — so an operator who
    ticks the box starts from the theme already in use, not from nothing.

    19-07-PLAN.md Task 2 (D-07): `errors`/`submitted` (both fully
    defaulted, so every pre-Phase-19 call site is unaffected) let a
    rejected save re-render this group with the user's own submission.
    `theme`/`theme_arriving` are membership-test ("hostile-request
    shape") fields — a submitted id that matches nothing in
    `device_config.THEME_IDS` simply pre-selects nothing in the
    corresponding chip grid, and the field's error message renders once,
    directly after that grid. Neither radio group's individual `<input>`
    gains an `aria-invalid`/`aria-describedby` pair: no single input in
    a same-named radio group is uniquely "the" control the message
    describes. `theme_arriving_enabled` (a genuine checkbox with one
    natural control) DOES gain that pair, anchored on
    `THEME_ARRIVING_TOGGLE_ID`. The single-theme read-only branch above
    has no editable control and is therefore never passed a `theme`
    error in practice — this function does not special-case that away.

    19-11-PLAN.md Task 3 (D-12/A-30): this multi-theme branch's two chip
    grids gain the group semantics a `<fieldset>`/`<legend>` would
    otherwise supply, WITHOUT adding either element (the four pinned
    zero-`<fieldset>` checks in `companion/test_config_page.py` forbid
    it, and this file's own docstrings above already give the reason).
    `role="radiogroup"` plus `aria-labelledby` — pointing at this
    group's own `<h2>` (`THEME_GROUP_HEADING_ID`) for the first grid,
    and at the "Arrivals theme" label (`THEME_ARRIVING_GROUP_HEADING_ID`)
    for the second — is the compatible alternative D-12 itself names.
    Both grids ALSO gain `aria-describedby` pointing at the shared
    `THEME_SECTION_CAPTION_ID` hint (there is only one hint for the
    whole group, describing both grids identically), via
    `_theme_chip_grid_html()`'s existing `extra_attr` seam — the exact
    seam the arrivals grid's own `ARRIVAL_GRID_ATTR` already uses,
    reused rather than duplicated with a second seam. The single-theme
    read-only branch below has no radio group at all (a one-option
    "choice" is not one), so it gains neither attribute.
    """
    caption_html = (
        '<p class="text-label section-caption" id="%s">%s</p>'
        % (
            escape_html(THEME_SECTION_CAPTION_ID),
            escape_html(_with_next_wake(THEME_SECTION_CAPTION, next_wake_clock)),
        ))
    if len(device_config.THEME_IDS) == 1:
        theme_id = (
            current_theme_id if current_theme_id in device_config.THEMES
            else device_config.THEME_IDS[0])
        theme = device_config.THEMES[theme_id]
        departing_hex = _palette_hex(theme["departing_index"])
        arriving_hex = _palette_hex(theme["arriving_index"])
        return (
            '<div class="theme-status" %s="%s">'
            '<h2 class="text-heading">Theme</h2>'
            "%s"
            '<div class="theme-status__row">'
            '<span class="theme-swatch" aria-hidden="true">'
            '<span class="theme-swatch__chip" style="background:%s"></span>'
            '<span class="theme-swatch__chip" style="background:%s"></span>'
            "</span>"
            '<span class="text-body">%s · current</span>'
            "</div>"
            "</div>"
        ) % (
            DIRTY_SECTION_ATTR, escape_html("Theme"),
            caption_html,
            departing_hex, arriving_hex,
            escape_html(device_config.theme_label(theme_id)),
        )

    effective_theme_id = _submitted_or_current(submitted, "theme", current_theme_id)
    first_grid_attr = 'role="radiogroup" aria-labelledby="%s"%s' % (
        escape_html(THEME_GROUP_HEADING_ID), _describedby_attr(THEME_SECTION_CAPTION_ID))
    first_grid = _theme_chip_grid_html(
        "theme", effective_theme_id, extra_attr=first_grid_attr)
    theme_error_html = _field_error_html(errors, "theme", "theme")

    checkbox_checked = _submitted_checkbox_checked(
        submitted, "theme_arriving_enabled", ARRIVING_CHECKBOX_VALUE,
        current_theme_arriving is not None)
    theme_arriving_enabled_attrs = _field_error_attrs(
        errors, "theme_arriving_enabled", THEME_ARRIVING_TOGGLE_ID)
    theme_arriving_enabled_error_html = _field_error_html(
        errors, "theme_arriving_enabled", THEME_ARRIVING_TOGGLE_ID)

    submitted_theme_arriving = _submitted_or_current(
        submitted, "theme_arriving", current_theme_arriving)
    effective_arriving = (
        submitted_theme_arriving if submitted_theme_arriving is not None
        else effective_theme_id)
    second_grid_attr = 'role="radiogroup" aria-labelledby="%s"%s %s' % (
        escape_html(THEME_ARRIVING_GROUP_HEADING_ID),
        _describedby_attr(THEME_SECTION_CAPTION_ID), ARRIVAL_GRID_ATTR)
    second_grid = _theme_chip_grid_html(
        "theme_arriving", effective_arriving,
        extra_class="theme-chip-grid--arrivals", extra_attr=second_grid_attr)
    theme_arriving_error_html = _field_error_html(errors, "theme_arriving", "theme-arriving")
    # Only the revealed (second) grid gets a label: before the checkbox
    # exists there is exactly one grid and it needs no label (unchanged
    # today); once revealed, the <h2>Theme</h2> heading plus the
    # checkbox's own "...for arrivals" wording already disambiguate the
    # first grid as the default/departures one — a second "Departures"
    # label on the first grid would be an extra line of chrome that
    # wording already makes redundant (15-UI-SPEC.md Section Anatomy §1).
    # 19-11-PLAN.md Task 3 (D-12/A-30): this label also carries
    # THEME_ARRIVING_GROUP_HEADING_ID — the second grid's own
    # aria-labelledby target above.
    return (
        '<div class="theme-status" %s="%s">'
        '<h2 class="text-heading" id="%s">Theme</h2>'
        "%s"
        "%s%s"
        '<label class="settings-checkbox">'
        '<input type="checkbox" name="theme_arriving_enabled" id="%s" value="%s"%s%s> %s'
        "</label>"
        "%s"
        '<p class="text-label theme-direction-label" id="%s">%s</p>'
        "%s%s"
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html("Theme"),
        escape_html(THEME_GROUP_HEADING_ID),
        caption_html,
        first_grid, theme_error_html,
        escape_html(THEME_ARRIVING_TOGGLE_ID),
        escape_html(ARRIVING_CHECKBOX_VALUE),
        " checked" if checkbox_checked else "",
        theme_arriving_enabled_attrs,
        escape_html(THEME_ARRIVING_CHECKBOX_LABEL),
        theme_arriving_enabled_error_html,
        escape_html(THEME_ARRIVING_GROUP_HEADING_ID),
        escape_html(THEME_DIRECTION_LABEL),
        second_grid, theme_arriving_error_html,
    )


def runway_fieldset(
        current_runway_id, images_available=(), errors=None, submitted=None,
        next_wake_clock=None):
    """D-05: one selectable `.runway-card` per `device_config.RUNWAYS`
    entry (exactly three today), in registry order — the entire card
    (`<label>`) is the hit target, wrapping a visually-hidden (never
    `display:none`) native radio input so keyboard/no-JS selection still
    works natively. `current_runway_id` marks the matching card
    `runway-card--selected`, computed server-side from the same
    membership comparison the radio's own `checked` attribute uses —
    never a client-side `:has()` CSS trick.

    Each card also carries a `runway-card__check` icon-check glyph,
    present in every card's markup — CSS shows it only on the selected
    card via the `runway-card--selected` modifier, so no second
    server-side conditional is needed for the icon itself.

    When `runway_id` is a member of `images_available` (the
    `ctx["runway_images"]` set companion/app.py computes — this module
    never touches the filesystem itself), an `<img>` pointing at the
    session-gated `/runway-image/{id}.png` route is also rendered.
    `images_available` defaults to `()` — "no images available" — the
    safe D-03 fallback, which is also what every pre-06.4 single-argument
    call site still gets. The single muted `RUNWAY_SECTION_CAPTION`
    sentence (quick task 260901-re6) renders once, directly under the
    heading, before the card list.

    The whole return value is wrapped in a single `<div class="theme-status"
    data-dirty-section="Runway">` — the same wrapping idiom
    `theme_fieldset()`'s read-only branch already uses, reused verbatim
    (D-01, 06.6.4.1): the group used to return five flat top-level
    siblings (an `<h2>`, N cards, a `<p>`) with no container at all, which
    was the actual root cause of Settings' broken Runway layout once it
    sat inside a two-column grid. That grid is now deleted, but the
    wrapper stays — it is what makes this group, like Theme and the new
    LED group, a single top-level element `dirty-state.js`'s
    `data-dirty-section` walk can address as one unit, and what carries
    the caption paragraph (`RUNWAY_SECTION_CAPTION`) directly under the
    `<h2 class="text-heading">Runway</h2>` heading.
    The group is named by that `<h2>`, not a `<legend>`, because D-04/D-05
    (06.6.3) already dropped the `<fieldset>` wrapper from both the Theme
    and Runway groups, and a `<legend>` outside a `<fieldset>` is invalid
    markup with no accessible group semantics — `<h2 class="text-heading">`
    is the role the Poll section and the new LED group both use too, so
    every group in this form reads at one consistent heading level.

    The cards themselves are further wrapped in a nested `<div
    class="runway-row">` (quick task 260901-qif), sitting directly after
    the caption paragraph — only the cards go in, the `<h2>` and the `<p>`
    stay outside it. Nothing renders after the row closes (quick task
    260901-re6 retired the trailing helper paragraph that used to sit
    there — the two-paragraph shape this docstring used to describe is
    gone). The cards used to be bare siblings of the heading and both
    paragraphs inside `.theme-status`, so each block-level card took a
    full line and the group rendered as three stacked full-width bars
    instead of the validated row-of-three. The row is a layout container
    only — it carries no visual treatment of its own, and the cards keep
    theirs.

    19-07-PLAN.md Task 2 (D-07): `errors`/`submitted` (both fully
    defaulted) let a rejected save repopulate the selected card from the
    submission and render `tracked_runway`'s error message once, after
    the card row. `tracked_runway` is a membership-test field, like
    `theme` above — no single radio in the group gains
    `aria-invalid`/`aria-describedby`, for the identical reason
    `theme_fieldset()`'s own docstring already gives.

    19-11-PLAN.md Task 3 (D-12/A-30): the `.runway-row` wrapper itself
    gains `role="radiogroup"` plus `aria-labelledby` (pointing at this
    group's own `<h2>`, `RUNWAY_GROUP_HEADING_ID`) and `aria-describedby`
    (pointing at `RUNWAY_SECTION_CAPTION_ID`'s hint) — the identical
    compatible-with-zero-`<fieldset>` pattern `theme_fieldset()` applies
    to its two chip grids, for the identical reason (see that function's
    own Task 3 docstring paragraph and this file's standing
    fieldset-free-design rationale above).
    """
    effective_runway_id = _submitted_or_current(
        submitted, "tracked_runway", current_runway_id)
    cards = []
    for runway_id in device_config.RUNWAY_IDS:
        selected = runway_id == effective_runway_id
        checked = " checked" if selected else ""
        card_class = (
            "runway-card runway-card--selected" if selected else "runway-card")
        label = device_config.runway_label(runway_id)
        escaped_id = escape_html(runway_id)
        image_html = ""
        if runway_id in images_available:
            image_html = (
                '<img class="runway-card__image" src="%s%s.png" alt="%s">'
                % (
                    RUNWAY_IMAGE_ROUTE_PREFIX, escaped_id,
                    escape_html(RUNWAY_IMAGE_ALT_TEMPLATE % label),
                )
            )
        cards.append(
            '<label class="%s">'
            '<input type="radio" name="tracked_runway" value="%s" class="visually-hidden"%s>'
            '<span class="runway-card__number">%s</span>'
            "%s"
            '<span class="runway-card__check">%s<span class="visually-hidden">Selected</span></span>'
            "</label>"
            % (
                card_class, escaped_id, checked, escape_html(label),
                image_html, layout.icon_html("icon-check"),
            )
        )
    runway_error_html = _field_error_html(errors, "tracked_runway", "tracked-runway")
    row_attr = 'role="radiogroup" aria-labelledby="%s"%s' % (
        escape_html(RUNWAY_GROUP_HEADING_ID), _describedby_attr(RUNWAY_SECTION_CAPTION_ID))
    return (
        '<div class="theme-status" %s="%s">'
        '<h2 class="text-heading" id="%s">Runway</h2>'
        '<p class="text-label section-caption" id="%s">%s</p>'
        '<div class="runway-row" %s>%s</div>'
        "%s"
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html("Runway"),
        escape_html(RUNWAY_GROUP_HEADING_ID),
        escape_html(RUNWAY_SECTION_CAPTION_ID),
        escape_html(_with_next_wake(RUNWAY_SECTION_CAPTION, next_wake_clock)),
        row_attr,
        "".join(cards),
        runway_error_html,
    )


def led_group(current_led_enabled, errors=None, submitted=None, next_wake_clock=None):
    """The Diagnostic LED settings group (D-05, 06.6.4.1): a sibling of the
    Theme and Runway groups inside the single merged `<form
    action="{SETTINGS_ROUTE}">`, wrapped in the same `.theme-status`
    container idiom those two groups use — the `theme-status` class name
    is reused verbatim, not a third wrapper class invented for this group.

    Deliberately carries no `<fieldset>`/`<legend>` of its own, unlike
    the retired pre-06.6.4.1 `led_fieldset()`/`led_section()` pair
    (removed 06.6.4.1-07, D-05: their own separate `POST /config-led`
    route no longer exists either). The old `<fieldset>` existed because
    the LED control used to live in its own independently-submittable
    `<form>`, and a `<legend>` only has accessible-name semantics inside
    a `<fieldset>`. Now that this group
    is a sibling of two `<h2>`-headed groups in one single-column stack
    (Theme's and Runway's own `<fieldset>` wrappers were already dropped
    by D-04/D-05 in 06.6.3), it is named the same way they are — an `<h2
    class="text-heading">` — so all three groups read at one consistent
    heading level, matching the Poll section's own heading role.

    19-11-PLAN.md Task 3 (D-12/A-30): this checkbox has exactly one
    natural DOM element, so it needs no `role="radiogroup"` of its own
    (unlike Theme's two chip grids and the Runway row) — but the
    fieldset-free design this whole file follows stands on the same
    reasoning stated here and at `theme_fieldset()`'s/
    `runway_fieldset()`'s own Task 3 paragraphs: D-12 supplies missing
    group semantics via ARIA attributes (`aria-describedby` here,
    `role="radiogroup"` + `aria-labelledby` there) rather than ever
    reaching for a literal `<fieldset>`/`<legend>`.

    quick task 260901-re6: `LED_SECTION_CAPTION` is a single muted
    caption, styled and positioned identically to Theme's and Runway's
    own captions — directly under the heading, before the control. It
    used to render as an un-muted `<p class="text-label">` AFTER the
    `<label>` instead, which this task fixes; the docstring previously
    asserted it "already renders directly under the heading here", which
    was never true of the shipped markup and is the reason this position
    drift went unnoticed.

    The `<label>` carries `class="settings-checkbox"` (quick task
    260901-qif; a rename of this group's own original checkbox-
    normalization class, by 10-05-PLAN.md Task 2, once the Quiet hours
    group became a second consumer of the identical pattern): unclassed,
    it fell through to the global `input, select`
    rule written for text inputs and selects, painting an oversized 44x44
    filled, bordered, rounded box instead of a normal small checkbox. The
    class scopes a normalization rule that shrinks the checkbox to its
    native 16px size while relocating the 44px touch-target floor onto
    this label — the input's own `type`/`name`/`value`/`checked`
    attribute sequence is untouched.

    19-07-PLAN.md Task 2 (D-07): `errors`/`submitted` (both fully
    defaulted) let a rejected save repopulate this checkbox's `checked`
    state from the submission (absent-means-unchecked, matching
    `handle_post()`'s own resolution of this exact field) and render its
    "unexpected switch value" error, anchored on the checkbox itself.

    19-11-PLAN.md Task 3 (D-12/A-30): this checkbox — a single-control
    group, unlike Theme/Runway's radio groups above — gains
    `aria-describedby` pointing at `LED_SECTION_CAPTION_ID`'s hint
    directly, via `_field_error_attrs()`'s own `hint_id` parameter;
    combined with any error id in one space-separated value (hint
    first), never a second, competing `aria-describedby`.
    """
    checked = _submitted_checkbox_checked(
        submitted, "led_enabled", LED_CHECKBOX_VALUE, current_led_enabled)
    error_attrs = _field_error_attrs(
        errors, "led_enabled", "led-enabled", hint_id=LED_SECTION_CAPTION_ID)
    error_html = _field_error_html(errors, "led_enabled", "led-enabled")
    return (
        '<div class="theme-status" %s="%s">'
        '<h2 class="text-heading">%s</h2>'
        '<p class="text-label section-caption" id="%s">%s</p>'
        '<label class="settings-checkbox">'
        '<input type="checkbox" name="led_enabled" value="%s"%s%s> Enable diagnostic LED'
        "</label>"
        "%s"
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(LED_SECTION_HEADING),
        escape_html(LED_SECTION_HEADING),
        escape_html(LED_SECTION_CAPTION_ID),
        escape_html(_with_next_wake(LED_SECTION_CAPTION, next_wake_clock)),
        escape_html(LED_CHECKBOX_VALUE), " checked" if checked else "", error_attrs,
        error_html,
    )


def quiet_hours_group(
        current_enabled, current_start, current_end, errors=None, submitted=None,
        next_wake_clock=None):
    """The Quiet hours settings group (10-05-PLAN.md, 10-UI-SPEC.md): a
    fourth sibling of the Theme/Runway/Diagnostic LED groups inside the
    single merged `<form action="{SETTINGS_ROUTE}">`, built against
    `led_group()`'s exact structure above — same `.theme-status` wrapper
    idiom, same `<h2 class="text-heading">` naming (no `<fieldset>`/
    `<legend>`, for the identical reason `led_group()`'s own docstring
    already documents: a `<legend>` only has accessible-name semantics
    inside a `<fieldset>`, which these sibling groups deliberately do not
    have).

    Controls render in this locked order (10-UI-SPEC.md's Interaction
    Contract): the enable checkbox, then a "Start" `<input type="time">`,
    then an "End" `<input type="time">`, each its own full-width line.
    They are deliberately NOT wrapped in `.theme-status__row` or any other
    side-by-side layout — 10-UI-SPEC.md rejects that explicitly, both to
    avoid two native time pickers wrapping at a narrow (320-375px)
    viewport and to stay consistent with 06.6.4.1 (D-01)'s removal of this
    page's two-column grid.

    The checkbox's wrapping `<label>` carries `class="settings-checkbox"`
    — the generalised name Task 2 of 10-05-PLAN.md introduces, once
    `led_group()`'s own single-consumer checkbox-normalization class is
    renamed to serve both groups identically.

    Unlike an "unchecked disables the fields" pattern, this group's Start/
    End inputs are NEVER given a `disabled` attribute or a dimmed/
    `.disabled` visual treatment tied to the checkbox's state — they stay
    fully interactive and save independently of it, resolving
    10-RESEARCH.md's Open Question 2 / Assumption A1 in the affirmative: a
    user can pre-configure a window before ever turning it on.

    Every interpolated current value — the heading, the caption, the
    checkbox value, and both current times — is routed through
    `escape_html()`, matching this file's universal escaping discipline.

    19-07-PLAN.md Task 2 (D-07/A-25): `errors`/`submitted` (both fully
    defaulted) let a rejected save repopulate all three controls from the
    submission and render each field's own error message directly after
    it. Both time inputs additionally gain a `required` attribute — a
    client-side convenience only (D-07's explicit instruction); the
    server-side HH:MM gate `handle_post()` runs before this render is
    ever reached is the real control, and the inputs stay enabled
    regardless of the enable checkbox either way — the
    pre-configure-before-enabling behaviour this docstring's own
    Interaction Contract paragraph above locks is unchanged.

    19-10-PLAN.md (D-14/S-04): three `type="button"` presets (Night, Work
    day, Always on) render between the enable checkbox and the Start
    input — a CLIENT-SIDE affordance only, with NO server change. Each
    button carries `data-preset-start`/`data-preset-end`/
    `data-preset-enabled` attributes that a small addition to
    `companion/static/dirty-state.js` reads and writes into this same
    form's `quiet_hours_start`/`quiet_hours_end`/`quiet_hours_enabled`
    fields — `handle_post()`'s validation of those three fields is
    completely untouched. On a no-JS browser the three buttons are
    simply inert (they carry no `type="submit"`, so they cannot even
    accidentally submit the form); the time inputs and checkbox
    themselves remain fully usable either way, an acceptable degradation
    matching this page's established graceful-degradation convention.
    """
    checked = _submitted_checkbox_checked(
        submitted, "quiet_hours_enabled", QUIET_HOURS_CHECKBOX_VALUE, current_enabled)
    enabled_error_attrs = _field_error_attrs(errors, "quiet_hours_enabled", "quiet-hours-enabled")
    enabled_error_html = _field_error_html(errors, "quiet_hours_enabled", "quiet-hours-enabled")

    # 19-11-PLAN.md Task 3 (D-12/A-30): the group's single hint links to
    # BOTH time inputs (there is no separate per-field hint for Start vs
    # End) via `_field_error_attrs()`'s `hint_id` parameter — the enable
    # checkbox above is not in D-12's own named single-control list and
    # keeps its unlinked (error-only) attrs.
    effective_start = _submitted_or_current(submitted, "quiet_hours_start", current_start)
    start_error_attrs = _field_error_attrs(
        errors, "quiet_hours_start", "quiet-hours-start", hint_id=QUIET_HOURS_SECTION_CAPTION_ID)
    start_error_html = _field_error_html(errors, "quiet_hours_start", "quiet-hours-start")

    effective_end = _submitted_or_current(submitted, "quiet_hours_end", current_end)
    end_error_attrs = _field_error_attrs(
        errors, "quiet_hours_end", "quiet-hours-end", hint_id=QUIET_HOURS_SECTION_CAPTION_ID)
    end_error_html = _field_error_html(errors, "quiet_hours_end", "quiet-hours-end")

    # 19-10-PLAN.md (D-14/S-04): the preset row. Reuses .runway-row -
    # style.css's existing generic flex/wrap/gap row - rather than
    # declaring a new CSS rule; that class is not scoped to the runway
    # picker's markup, only to its layout shape, and nothing here asserts
    # its absence from quiet_hours_group()'s own output (unlike
    # .theme-status__row, which a pinned check requires stay absent from
    # this group specifically). The three buttons are bare `type="button"`
    # elements with no new class, inheriting the existing quiet-button
    # treatment (base `button` selector) untouched.
    preset_row_html = (
        '<div class="runway-row">'
        '<button type="button" %s data-preset-start="%s" data-preset-end="%s">%s</button>'
        '<button type="button" %s data-preset-start="%s" data-preset-end="%s">%s</button>'
        '<button type="button" %s data-preset-enabled="0">%s</button>'
        "</div>"
    ) % (
        QUIET_HOURS_PRESET_ATTR,
        escape_html(QUIET_HOURS_PRESET_NIGHT_START), escape_html(QUIET_HOURS_PRESET_NIGHT_END),
        escape_html(QUIET_HOURS_PRESET_NIGHT_LABEL),
        QUIET_HOURS_PRESET_ATTR,
        escape_html(QUIET_HOURS_PRESET_WORKDAY_START), escape_html(QUIET_HOURS_PRESET_WORKDAY_END),
        escape_html(QUIET_HOURS_PRESET_WORKDAY_LABEL),
        QUIET_HOURS_PRESET_ATTR,
        escape_html(QUIET_HOURS_PRESET_ALWAYS_ON_LABEL),
    )

    return (
        '<div class="theme-status" %s="%s">'
        '<h2 class="text-heading">%s</h2>'
        '<p class="text-label section-caption" id="%s">%s</p>'
        '<label class="settings-checkbox">'
        '<input type="checkbox" name="quiet_hours_enabled" value="%s"%s%s> Enable quiet hours'
        "</label>"
        "%s"
        "%s"
        '<label>Start <input type="time" name="quiet_hours_start" value="%s" required%s></label>'
        "%s"
        '<label>End <input type="time" name="quiet_hours_end" value="%s" required%s></label>'
        "%s"
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(QUIET_HOURS_SECTION_HEADING),
        escape_html(QUIET_HOURS_SECTION_HEADING),
        escape_html(QUIET_HOURS_SECTION_CAPTION_ID),
        escape_html(_with_next_wake(QUIET_HOURS_SECTION_CAPTION, next_wake_clock)),
        escape_html(QUIET_HOURS_CHECKBOX_VALUE), " checked" if checked else "", enabled_error_attrs,
        enabled_error_html,
        preset_row_html,
        escape_html(effective_start), start_error_attrs,
        start_error_html,
        escape_html(effective_end), end_error_attrs,
        end_error_html,
    )


def wake_interval_group(current_wake_interval_s, errors=None, submitted=None, next_wake_clock=None):
    """The Wake interval settings group (11-UI-SPEC.md, 11-RESEARCH.md
    Pattern 4): a fifth sibling of the Theme/Runway/Diagnostic LED/Quiet
    hours groups inside the single merged `<form action="{SETTINGS_ROUTE}">`,
    built against `led_group()`'s exact structure — same `.theme-status`
    wrapper idiom, same `<h2 class="text-heading">` naming (no
    `<fieldset>`/`<legend>`, for the identical reason `led_group()`'s own
    docstring already documents: a `<legend>` only has accessible-name
    semantics inside a `<fieldset>`, which these sibling groups
    deliberately do not have). Unlike `quiet_hours_group()`, this group has
    no checkbox gate — a plain `<label>` wraps a single
    `<input type="number">`, this codebase's first (D-05), not
    `class="settings-checkbox"` — that class normalises a checkbox and
    would mis-size a text-like input; the global `input, select` rule
    already supplies the 44px touch-target floor with no type-specific
    override needed, exactly like `<input type="time">`'s own precedent.

    `min`/`max` are interpolated from `device_config.WAKE_INTERVAL_MIN_S`/
    `WAKE_INTERVAL_MAX_S`, read from the module rather than re-typed as
    literals, so the two can never drift apart from `save_device_config()`'s
    own server-side re-check of the identical bounds.

    The `value` attribute is the one place this function does real work:
    it is emitted only when `current_wake_interval_s` is an `int` that is
    not a `bool` and falls within the inclusive
    `[WAKE_INTERVAL_MIN_S, WAKE_INTERVAL_MAX_S]` range; otherwise no
    `value` attribute is emitted at all, and the placeholder
    (`WAKE_INTERVAL_PLACEHOLDER_TEXT`) carries the empty state. Two
    reasons this guard is load-bearing, not decorative: a fabricated
    number would lie to the user about a setting that was never made
    (D-07), and — more sharply — an out-of-range `value` on a native
    numeric input fails HTML5 constraint validation, which blocks
    submission of the *entire* Settings form, not just this field. That is
    a live risk, not hypothetical: `deploy/skypane.env.example` currently
    sets `SKYPANE_SLEEP_S=30`, below the 60s floor, and plan 11-04 feeds
    that environment value in as the pre-fill fallback. The bool exclusion
    is mandatory for the same reason it is everywhere else in this phase —
    `isinstance(True, int)` is true in Python.

    The heading, the caption and the placeholder are routed through
    `escape_html()`, matching this file's universal escaping discipline;
    the numeric value needs no escaping because `%d` cannot emit anything
    but digits and a sign.

    19-07-PLAN.md Task 2 (D-07): when a real submission is being
    repopulated (`submitted is not None`) and it actually carries this
    field, the RAW submitted string is echoed back verbatim (escaped),
    deliberately bypassing the in-range/non-bool-int guard above — that
    guard exists only for the ordinary ctx-sourced int
    (`current_wake_interval_s`), never for a rejected save's own echoed
    input. "7" is a string, not an int, and would otherwise never get a
    `value` attribute at all, silently discarding exactly what D-07
    requires be shown back to the user. Native HTML5 min/max constraint
    validation still applies on the user's NEXT submit attempt (nothing
    here suppresses it) — that is a feature, not a bug: it is what
    prompts them to fix the value before it can be saved.
    """
    if submitted is not None and "wake_interval_s" in submitted:
        raw_submitted = submitted["wake_interval_s"]
        value_attr = ' value="%s"' % escape_html(str(raw_submitted)) if raw_submitted else ""
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
    return (
        '<div class="theme-status" %s="%s">'
        '<h2 class="text-heading">%s</h2>'
        '<p class="text-label section-caption" id="%s">%s</p>'
        "<label>Wake interval (seconds) "
        '<input type="number" name="wake_interval_s" min="%d" max="%d"'
        ' placeholder="%s"%s%s></label>'
        "%s"
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(WAKE_INTERVAL_SECTION_HEADING),
        escape_html(WAKE_INTERVAL_SECTION_HEADING),
        escape_html(WAKE_INTERVAL_SECTION_CAPTION_ID),
        escape_html(_with_next_wake(WAKE_INTERVAL_SECTION_CAPTION, next_wake_clock)),
        device_config.WAKE_INTERVAL_MIN_S, device_config.WAKE_INTERVAL_MAX_S,
        escape_html(WAKE_INTERVAL_PLACEHOLDER_TEXT),
        value_attr, error_attrs,
        error_html,
    )


def display_group(current_display_enabled, errors=None, submitted=None):
    """The Display settings group (12-UI-SPEC.md, 12-CONTEXT.md D-08/D-09):
    a sixth and last sibling of the Theme/Runway/Diagnostic LED/Quiet
    hours/Wake interval groups inside the single merged `<form
    action="{SETTINGS_ROUTE}">`, built directly against `led_group()`'s
    exact structure above — a lone checkbox with no dependent fields is
    exactly `led_group()`'s shape, not `quiet_hours_group()`'s (which has
    two dependent time inputs this group deliberately does not gain). Same
    `.theme-status` wrapper idiom, same `<h2 class="text-heading">` naming
    (no `<fieldset>`/`<legend>`, for the identical reason `led_group()`'s
    own docstring already documents).

    The developer's own framing challenge for this phase — *"pas possible
    de juste faire ON/OFF ?"* — is the reason this function must stay this
    small: exactly one `.theme-status` wrapper, one `.settings-checkbox`
    label, one checkbox input, and nothing else. No helper field, no
    schedule, no sibling control whose enabled state depends on this one.

    `DISPLAY_SECTION_CAPTION` states the ~5-minute apply latency in both
    directions (D-02) rather than the generic next-scheduled-poll clause
    every sibling caption ends on, because this is the one field on the
    page whose apply-timing is genuinely different — see the constant's
    own comment above for why.

    Every interpolated current value — the heading, the caption, and the
    checkbox value — is routed through `escape_html()`, matching this
    file's universal escaping discipline.

    19-07-PLAN.md Task 2 (D-07): `errors`/`submitted` (both fully
    defaulted) let a rejected save repopulate this checkbox's `checked`
    state from the submission (absent-means-unchecked, matching
    `handle_post()`'s own resolution of this exact field) and render its
    "unexpected switch value" error, anchored on the checkbox itself.

    19-12-PLAN.md Task 3 (D-13): deliberately takes NO `next_wake_clock`
    parameter, unlike every sibling group builder above. D-13's suffix
    is derived from `wake_interval_s`/`SKYPANE_SLEEP_S`, which this
    field's own honest ~5-minute latency sentence (above) already
    supersedes for this one group — appending a wake-interval-derived
    figure here would contradict that sentence, per 12-CONTEXT.md D-01.
    """
    checked = _submitted_checkbox_checked(
        submitted, "display_enabled", DISPLAY_CHECKBOX_VALUE, current_display_enabled)
    error_attrs = _field_error_attrs(
        errors, "display_enabled", "display-enabled", hint_id=DISPLAY_SECTION_CAPTION_ID)
    error_html = _field_error_html(errors, "display_enabled", "display-enabled")
    return (
        '<div class="theme-status" %s="%s">'
        '<h2 class="text-heading">%s</h2>'
        '<p class="text-label section-caption" id="%s">%s</p>'
        '<label class="settings-checkbox">'
        '<input type="checkbox" name="display_enabled" value="%s"%s%s> Enable display'
        "</label>"
        "%s"
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(DISPLAY_SECTION_HEADING),
        escape_html(DISPLAY_SECTION_HEADING),
        escape_html(DISPLAY_SECTION_CAPTION_ID), escape_html(DISPLAY_SECTION_CAPTION),
        escape_html(DISPLAY_CHECKBOX_VALUE), " checked" if checked else "", error_attrs,
        error_html,
    )


def calendar_group(
        configured, drift, last_synced_at, now, current_calendar_theme_id,
        current_theme_id, errors=None, submitted=None):
    """The Calendar settings group (16-UI-SPEC.md Section Anatomy): a
    seventh and last sibling inside the single merged `<form
    action="{SETTINGS_ROUTE}">`, appended after `display_group()`'s
    output — this position is 16-UI-SPEC.md's own Placement
    recommendation, taken as recommended: a pure zero-disruption append
    that leaves every existing group's relative order and DOM nesting
    untouched, where the considered alternative (directly after Theme)
    would insert into the middle of an already-verified sequence for a
    purely narrative benefit. Unlike Phase 15's Rules section, this group
    belongs INSIDE the form: it nests no form of its own (a single
    `<select>`, no add/delete actions), so it submits with the shared Save
    Settings flow exactly like Wake interval or Display.

    Card class is `.page-section`, not `.theme-status` — this is a
    distinct group that happens to contain one theme-assigning field,
    joining Poll/Quiet hours/Wake interval/Rules' card class rather than
    the Theme-specific one (16-UI-SPEC.md Section Anatomy).

    Phase 17 plan 03 widens this to an explicit four-branch decision,
    `drift` first: a permission-drifted stored link (D-02) wins over
    everything else, because `configured` is already `False` in that
    state (D-08 — `calendar_is_configured()`'s bool contract) and a
    later check would therefore never see the drift branch at all,
    making it indistinguishable from a calendar that was never connected
    — exactly what D-02 exists to prevent. Then not configured; then
    configured-with-a-usable-`last_synced_at`; then
    configured-otherwise (the pending string). "Usable" is decided with
    `layout.parse_iso()`/`layout.age_seconds()`
    directly, the same two calls `concise_timestamp_html()` makes
    internally — NOT by treating an empty return from that function as
    the unparseable signal, because `concise_timestamp_html()` only
    returns its (escaped) `fallback` for a falsy `ts`; for a truthy but
    unparseable string it instead returns a non-empty span echoing the
    raw value verbatim (its own documented degrade-gracefully contract).
    An unparseable stored value therefore falls back to the pending
    string rather than producing a fabricated or blank time — this is
    16-UI-SPEC.md Open Question 3's stated fallback.

    `concise_timestamp_html()` is a RAW-MARKUP-PRODUCING function: its
    return is interpolated verbatim into the synced branch, never
    re-escaped, while the surrounding sentence fragment is escaped
    separately — the one place in this function where the file's
    otherwise-universal escaping discipline is deliberately not applied
    uniformly.

    Phase 17 plan 03 adds the write-only feed-URL field (D-01/D-02/D-07).
    This function receives only two booleans (`configured`, `drift`) and
    two timestamps — never the URL itself — so the stored value cannot
    leak through this renderer even by accident (T-17-SECRET); the field
    always renders with no `value` attribute, no populated placeholder,
    and nothing derived from the stored URL, in every one of the four
    status states. It is `type="text"`, not `type="url"`, deliberately: a
    URL-typed input would apply its own native client-side acceptability
    rule, which could disagree with the server's own — the single
    arbiter of acceptability stays `calendar_rules._url_is_safe()` and
    the fetch itself. It is also not a masked input: write-only means the
    STORED value is never rendered back, not that what the operator is
    currently typing is hidden from them.

    19-11-PLAN.md (D-08/A-26): the in-form disconnect checkbox that used
    to render here (rendered only when `configured or drift`, always
    unchecked) is RETIRED — disconnecting is now
    `calendar_disconnect_section()`'s own standalone, confirmed form,
    rendered by `render()` as a sibling of this group on the Device page,
    never inside `<form id="settings-form">`. This function itself no
    longer renders anything disconnect-related.

    The `<select name="calendar_theme_id">` reuses `_rule_add_form_html()`'s
    exact option-building loop — one option per `device_config.THEME_IDS`
    member in order, text from `device_config.theme_label()`, no swatch —
    and marks selected the saved `calendar_theme_id` when set, otherwise
    the currently-selected base theme id (matching the arrivals grid's own
    default-selection precedent). `class="calendar-status"` is emitted as
    a bare hook; 16-UI-SPEC.md Open Question 4 is resolved in favour of no
    new CSS rule — companion/static/style.css needs no change for it.

    19-07-PLAN.md Task 2 (D-07/T-19-12): `errors`/`submitted` (both fully
    defaulted) let a rejected save repopulate `calendar_theme_id`'s
    `<select>` from the submission and render its error message. The
    write-only `calendar_url` input is the ONE field this D-07
    repopulation rule does not apply to (T-16-SECRET, 17-CONTEXT.md
    D-01/D-02): its `value` stays EMPTY on every branch, exactly as
    before this plan, even when `submitted` carries the URL the operator
    just typed — repopulating it would serve that secret back in the
    HTML. Only its error message (never its value) is added here.
    """
    # Drift first (D-02): a drifted file makes `configured` already
    # False (D-08), so checking `not configured` before `drift` would
    # make the drift state unreachable and indistinguishable from a
    # calendar that was never connected.
    if drift:
        status_html = escape_html(CALENDAR_STATUS_PERMISSION_UNSAFE)
    elif not configured:
        status_html = escape_html(CALENDAR_STATUS_NOT_CONFIGURED)
    else:
        usable = (
            bool(last_synced_at)
            and layout.parse_iso(last_synced_at) is not None
            and layout.age_seconds(last_synced_at, now) is not None)
        if usable:
            timestamp_html = layout.concise_timestamp_html(
                last_synced_at, now, fallback="")
            status_html = "%s%s." % (
                escape_html(CALENDAR_STATUS_CONFIGURED_SYNCED_PREFIX),
                timestamp_html)
        else:
            status_html = escape_html(CALENDAR_STATUS_CONFIGURED_PENDING)

    selected_calendar_theme_id = _submitted_or_current(
        submitted, "calendar_theme_id",
        current_calendar_theme_id if current_calendar_theme_id is not None
        else current_theme_id)
    theme_options = "".join(
        '<option value="%s"%s>%s</option>'
        % (
            escape_html(theme_id),
            " selected" if theme_id == selected_calendar_theme_id else "",
            escape_html(device_config.theme_label(theme_id)),
        )
        for theme_id in device_config.THEME_IDS
    )
    # 19-11-PLAN.md Task 3 (D-12/A-30): the calendar theme <select> and
    # the calendar URL <input> are both single-control fields (D-12's
    # own named list) — each gains aria-describedby pointing at its OWN
    # per-field hint (CALENDAR_THEME_HINT/CALENDAR_URL_HINT), not the
    # group-level CALENDAR_SECTION_CAPTION, via _field_error_attrs()'s
    # hint_id parameter.
    calendar_theme_error_attrs = _field_error_attrs(
        errors, "calendar_theme_id", "calendar-theme", hint_id=CALENDAR_THEME_HINT_ID)
    calendar_theme_error_html = _field_error_html(
        errors, "calendar_theme_id", "calendar-theme")
    # T-16-SECRET / T-19-12: the write-only calendar_url input's value
    # stays empty always, never repopulated from `submitted` — see the
    # docstring above. Only the error attrs/message are new here.
    calendar_url_error_attrs = _field_error_attrs(
        errors, "calendar_url", "calendar-url", hint_id=CALENDAR_URL_HINT_ID)
    calendar_url_error_html = _field_error_html(errors, "calendar_url", "calendar-url")
    return (
        '<div class="page-section" %s="%s">'
        '<h2 class="text-heading">%s</h2>'
        '<p class="text-label section-caption">%s</p>'
        '<p class="calendar-status">%s</p>'
        '<div class="rule-add-form__field">'
        '<label for="calendar-url">%s</label>'
        '<input type="text" id="calendar-url" name="calendar_url" '
        'autocomplete="off" spellcheck="false" maxlength="%s"%s>'
        '<p class="text-label section-caption" id="%s">%s</p>'
        "%s"
        "</div>"
        '<div class="rule-add-form__field">'
        '<label for="calendar-theme">%s</label>'
        '<select id="calendar-theme" name="calendar_theme_id" required%s>%s</select>'
        '<p class="text-label section-caption" id="%s">%s</p>'
        "%s"
        "</div>"
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(CALENDAR_SECTION_HEADING),
        escape_html(CALENDAR_SECTION_HEADING),
        escape_html(CALENDAR_SECTION_CAPTION),
        status_html,
        escape_html(CALENDAR_URL_FIELD_LABEL),
        CALENDAR_URL_MAX_LEN, calendar_url_error_attrs,
        escape_html(CALENDAR_URL_HINT_ID), escape_html(CALENDAR_URL_HINT),
        calendar_url_error_html,
        escape_html(CALENDAR_THEME_FIELD_LABEL),
        calendar_theme_error_attrs, theme_options,
        escape_html(CALENDAR_THEME_HINT_ID), escape_html(CALENDAR_THEME_HINT),
        calendar_theme_error_html,
    )


def calendar_disconnect_section(configured, drift):
    """19-11-PLAN.md Task 1 (D-08/A-26): the calendar disconnect action's
    own standalone, confirmed form — a sibling of `calendar_group()`'s
    `.page-section`, never a descendant of it or of
    `<form id="{SETTINGS_FORM_ID}">`. `render()` emits this only on the
    Device page, immediately after the Calendar group, and never inside
    the merged settings form — HTML forbids nesting a `<form>` inside
    another `<form>` anyway (the same structural reason
    `_rules_section_html()`'s own per-flight rule delete forms are
    siblings of that form, not descendants), and this action additionally
    needs its OWN confirmation step, which a field inside the shared
    settings form could never have.

    Rendered only when `configured or drift` is true — the identical
    condition the retired in-form checkbox used, and for the identical
    reason (D-02): a drifted file still exists and still holds a URL, so
    the promise that disconnecting removes it must not be blocked by a
    permissions problem.

    The hidden `{CALENDAR_DISCONNECT_CONFIRM_FIELD}` field carries an
    EMPTY value — a bare POST of this form therefore submits no confirm
    value at all, landing on `_handle_calendar_disconnect_post()`'s own
    server-rendered confirmation page (`calendar_disconnect_confirm_
    page()` below) rather than erasing anything. That page IS the real
    control (19-CONTEXT.md's own D-08 resolution) — the button below
    additionally carries `data-confirm`/`data-confirm-value` attributes
    `companion/static/confirm-submit.js` (Task 2) reads to show one
    native `confirm()` dialog and, on acceptance only, fill this same
    hidden field with `CALENDAR_DISCONNECT_CONFIRM_VALUE` before letting
    the submit proceed — a misclick guard layered on top, never a
    substitute for the server-side gate.
    """
    if not (configured or drift):
        return ""
    return (
        '<form method="post" action="%s" data-confirm="%s" '
        'data-confirm-value="%s">'
        '<input type="hidden" name="%s" value="" data-confirm-field>'
        '<button type="submit">%s</button>'
        "</form>"
    ) % (
        CALENDAR_DISCONNECT_ROUTE,
        escape_html(CALENDAR_DISCONNECT_CONFIRM_QUESTION),
        escape_html(CALENDAR_DISCONNECT_CONFIRM_VALUE),
        CALENDAR_DISCONNECT_CONFIRM_FIELD,
        escape_html(CALENDAR_DISCONNECT_CHECKBOX_LABEL),
    )


def calendar_disconnect_confirm_page(ctx):
    """19-11-PLAN.md Task 1 (D-08/A-26): the two-step server-rendered
    confirmation `_handle_calendar_disconnect_post()` (companion/app.py)
    renders at 200 whenever the posted confirm field is not exactly
    `CALENDAR_DISCONNECT_CONFIRM_VALUE` — including a bare POST with no
    confirm field at all. This page IS the security-relevant control: it
    holds with JavaScript disabled, with the script blocked by CSP, or
    against a hand-crafted request that skips
    `companion/static/confirm-submit.js`'s native `confirm()` entirely.

    The form posts back to the SAME route with the confirm field
    pre-filled to the accepted value and a real, plain submit button —
    the one and only way this page itself can cause a disconnect. The
    cancel path is a plain link back to the Device page, never a second
    form (nothing to submit, nothing to confirm). Every dynamic value
    passes through `escape_html()`, matching this file's universal
    escaping discipline; `ctx` is accepted (unused today) for the same
    reason `render()`'s own scoped builders all take it — so a future
    reader adding a ctx-derived detail here never has to widen this
    function's own signature to do it.
    """
    return (
        layout.page_header(CALENDAR_DISCONNECT_CONFIRM_HEADING)
        + '<p class="text-body">%s</p>'
        '<form method="post" action="%s">'
        '<input type="hidden" name="%s" value="%s">'
        '<button type="submit">%s</button>'
        "</form>"
        '<p><a class="text-label" href="%s">%s</a></p>'
    ) % (
        escape_html(CALENDAR_DISCONNECT_CONFIRM_SENTENCE),
        CALENDAR_DISCONNECT_ROUTE,
        CALENDAR_DISCONNECT_CONFIRM_FIELD, escape_html(CALENDAR_DISCONNECT_CONFIRM_VALUE),
        escape_html(CALENDAR_DISCONNECT_CONFIRM_BUTTON_TEXT),
        layout.DEVICE_ROUTE, escape_html(CALENDAR_DISCONNECT_CANCEL_TEXT),
    )


def poll_trigger_section(cooldown_remaining):
    """The CFG-07 manual-trigger control: an enabled button when
    `cooldown_remaining` is zero, or a native-disabled button plus the
    D-17 remaining-seconds copy otherwise.

    D-18/A-35 (19-04-PLAN.md): this function emits ZERO `<script>`
    elements on either branch. The D-01 live countdown and the UXA-15
    disable-on-submit affordance both moved into
    `companion/static/poll-cooldown.js`, served pre-auth from
    `companion/app.py`'s `POLL_COOLDOWN_SCRIPT_ROUTE`, so
    `companion/app.py`'s Content-Security-Policy can set
    `script-src 'self'` with no `'unsafe-inline'` and no nonce. What
    used to be Python-interpolated through the now-removed
    `_js_literal()` is instead exposed as `data-*` attributes on the
    button, every one routed through `escape_html()` here:
      `data-cooldown` — the disabled branch's server-computed remaining
        seconds (D-01: `poll_cooldown_remaining()`'s history_db-
        persisted figure, so it survives a service restart and stays
        correct across multiple tabs — never re-derived client-side
        from `POLL_COOLDOWN_S`), absent on the enabled branch;
      `data-cooldown-text-id` / `data-cooldown-template` /
        `data-cooldown-token` — the disabled branch's countdown-paragraph
        id and its `POLL_COOLDOWN_HELPER_TEXT` template plus
        substitution token, both formatted here exactly as before;
      `data-submit-pending` — the enabled branch's UXA-15
        `POLL_SUBMIT_PENDING_TEXT` label, swapped in client-side on
        submit.
    A browser with JavaScript disabled still sees exactly the same
    server-rendered copy and markup as before this change; the
    countdown/disable-on-submit affordances are UX only, never a trust
    boundary — companion/app.py's `_handle_poll_now()` independently
    re-checks the cooldown server-side, and its `_POLL_LOCK`
    independently serializes execution, before it would ever call
    `poll_loop.run_once()`.

    quick task 260901-s5o: the section's single muted caption
    (`POLL_SECTION_CAPTION`) renders first on both branches, landing
    directly under the `<h2 class="text-heading">Poll</h2>` heading that
    `render()` — not this function — emits immediately before this
    function's output. A caption emitted on only one branch would
    silently disappear for the whole cooldown window, which is why
    `caption_html` is computed once above the branch rather than inline
    in each return.
    """
    # `> 0`, not truthy: must agree with companion/static/poll-cooldown.js's
    # own `remaining > 0` guard (after its `parseInt()`/`isNaN()` gate), or
    # a negative value would take this branch (natively disabling the
    # button) while the script inertly no-ops, leaving no way to
    # re-enable it client-side.
    caption_html = (
        '<p class="text-label section-caption">%s</p>'
        % escape_html(POLL_SECTION_CAPTION))
    if cooldown_remaining > 0:
        cooldown_text = POLL_COOLDOWN_HELPER_TEXT.format(n=cooldown_remaining)
        template = POLL_COOLDOWN_HELPER_TEXT.format(n=POLL_COOLDOWN_TEMPLATE_TOKEN)
        return (
            "%s"
            '<form method="post" action="/poll-now">'
            '<button type="submit" id="%s" disabled '
            'data-cooldown="%s" data-cooldown-text-id="%s" '
            'data-cooldown-template="%s" data-cooldown-token="%s">'
            "Trigger poll now</button>"
            "</form>"
            '<p class="text-body" id="%s">%s</p>'
        ) % (
            caption_html,
            POLL_TRIGGER_BUTTON_ID,
            escape_html(str(cooldown_remaining)),
            escape_html(POLL_COOLDOWN_TEXT_ID),
            escape_html(template),
            escape_html(POLL_COOLDOWN_TEMPLATE_TOKEN),
            POLL_COOLDOWN_TEXT_ID,
            escape_html(cooldown_text),
        )
    return (
        "%s"
        '<form method="post" action="/poll-now">'
        '<button type="submit" id="%s" data-submit-pending="%s">'
        "Trigger poll now</button>"
        "</form>"
    ) % (
        caption_html,
        POLL_TRIGGER_BUTTON_ID,
        escape_html(POLL_SUBMIT_PENDING_TEXT),
    )


# ---------------------------------------------------------------------
# Phase 15 D-10/D-11 (15-05-PLAN.md): the per-flight colour-rules editor —
# an add form (its own immediate POST route) plus an always-present list
# (empty state, or a cards-then-table pairing) with a plain per-row Delete
# button (its own immediate POST route). Mirrors airlines_page.py's own
# manual-resolutions management-list decomposition one-for-one: a delete-
# action URL builder, a row/table/card-list renderer trio, and a section
# assembler.
# ---------------------------------------------------------------------


def _rule_delete_action(kind, value):
    """The delete form's `action` attribute for `(kind, value)` — the
    two-segment shape `/settings/rules/{kind}/{value}/delete` (D-09's
    store key is `(kind, value)`, so the delete action must identify
    both). Both segments are already-normalised, already-allowlisted
    uppercase alphanumerics by the time a row reaches this function
    (`colour_rules.rule_rows()`'s own contract, re-checked again at read
    time by `load_colour_rules()`), so `escape_html()` on each segment is
    the only encoding needed — mirrors `airlines_page._manual_delete_
    action()`'s own one-string-builder-for-both-renderers discipline, so
    the desktop `<tr>` and the mobile `<li>` can never diverge into
    building two different strings for the same row.
    """
    return "%s%s/%s%s" % (
        RULES_DELETE_ROUTE_PREFIX, escape_html(kind), escape_html(value),
        RULES_DELETE_ROUTE_SUFFIX,
    )


def _rule_add_form_html():
    """The add form (D-10, D-11, 15-UI-SPEC.md's Add-Form Shape): a
    `<form method="post">` targeting `RULES_ADD_ROUTE`, three
    `<div class="rule-add-form__field">` blocks in Match-by/Value/Theme
    order and a submit button — a column stack on every viewport, no
    side-by-side arrangement (a three-field inline row would be the
    page's first horizontally-arranged settings form).

    Field 1 (Match by): a native `<select name="rule_kind">` with one
    `<option>` per `colour_rules.RULE_KINDS` member using `RULE_KIND_
    LABELS` text, no blank placeholder option — the first listed option
    is the implicit default, matching every other `<select>` on this
    page.

    Field 2 (Value): a plain `<input type="text" name="rule_key"
    maxlength="8" required autocomplete="off">` with **no** `pattern`
    attribute — the server is the single source of truth for per-kind
    format validation (a single input serving three kinds cannot express
    a per-kind pattern without JavaScript, which this phase does not
    add) — followed by a `.section-caption`-styled hint line
    (`RULE_VALUE_HINT`), not a placeholder.

    Field 3 (Theme): a native `<select name="rule_theme_id">` with one
    `<option>` per `device_config.THEME_IDS` entry (18 today), no swatch
    inside the `<option>` (a native `<select>` cannot render inline
    coloured chips without JavaScript or a full custom-select rebuild).
    """
    kind_options = "".join(
        '<option value="%s">%s</option>'
        % (escape_html(kind), escape_html(RULE_KIND_LABELS[kind]))
        for kind in colour_rules.RULE_KINDS
    )
    theme_options = "".join(
        '<option value="%s">%s</option>'
        % (escape_html(theme_id), escape_html(device_config.theme_label(theme_id)))
        for theme_id in device_config.THEME_IDS
    )
    return (
        '<form method="post" action="%s" class="rule-add-form">'
        '<div class="rule-add-form__field">'
        '<label for="rule-kind">%s</label>'
        '<select id="rule-kind" name="rule_kind" required>%s</select>'
        "</div>"
        '<div class="rule-add-form__field">'
        '<label for="rule-key">%s</label>'
        '<input type="text" id="rule-key" name="rule_key" maxlength="8" '
        'required autocomplete="off">'
        '<p class="text-label section-caption">%s</p>'
        "</div>"
        '<div class="rule-add-form__field">'
        '<label for="rule-theme">%s</label>'
        '<select id="rule-theme" name="rule_theme_id" required>%s</select>'
        "</div>"
        '<button type="submit">%s</button>'
        "</form>"
    ) % (
        RULES_ADD_ROUTE,
        escape_html(RULE_KIND_FIELD_LABEL), kind_options,
        escape_html(RULE_VALUE_FIELD_LABEL),
        escape_html(RULE_VALUE_HINT),
        escape_html(RULE_THEME_FIELD_LABEL), theme_options,
        escape_html(RULE_ADD_BUTTON_TEXT),
    )


def _rule_theme_swatch_html(theme_id):
    """One `<span class="theme-swatch__chip">` followed by the theme's
    label text — reuses the existing swatch-dot class verbatim (a third
    consumer, after `theme_fieldset()`'s read-only single-theme row and
    the theme-chip-grid's own dots), computed via `_palette_hex()`, never
    a hardcoded hex literal.
    """
    theme_hex = _palette_hex(device_config.THEMES[theme_id]["departing_index"])
    return (
        '<span class="theme-swatch__chip" style="background:%s"></span>%s'
    ) % (escape_html(theme_hex), escape_html(device_config.theme_label(theme_id)))


def _rule_row_html(index, kind, value, theme_id, created_at, now):
    """One `<tr>` for the rules table: `row`/`row-alt` by index parity,
    Kind/Key/Theme/Added/Delete cells — mirrors `airlines_page._manual_
    resolution_row_html()`'s own shape. The Kind cell is plain escaped
    text from `RULE_KIND_LABELS`, never abbreviated differently from the
    add form and never colour-coded (colour is reserved for the swatch
    column only). The Key cell carries `class="mono"`, escaped verbatim,
    uppercase as stored. `created_at` renders through `layout.concise_
    timestamp_html()`, interpolated verbatim as already-safe markup —
    never re-escaped.
    """
    row_class = "row-alt" if index % 2 else "row"
    delete_form = (
        '<form method="post" action="%s">'
        '<button type="submit">%s</button>'
        "</form>"
    ) % (_rule_delete_action(kind, value), DELETE_BUTTON_TEXT)
    cells = (
        "<td>%s</td>" % escape_html(RULE_KIND_LABELS.get(kind, kind)),
        '<td class="mono">%s</td>' % escape_html(value),
        "<td>%s</td>" % _rule_theme_swatch_html(theme_id),
        "<td>%s</td>" % layout.concise_timestamp_html(created_at, now, fallback=""),
        "<td>%s</td>" % delete_form,
    )
    return '<tr class="%s">%s</tr>' % (row_class, "".join(cells))


def _rules_table_html(rows, now):
    """The desktop (`>=960px`) rules table, hand-rolled to match
    `airlines_page._manual_resolution_table_html()`'s own
    `.data-table-wrap`/`.data-table`/`thead`/`tbody` structure.
    """
    header_cells = "".join("<th>%s</th>" % escape_html(h) for h in RULE_HEADERS)
    body_rows = [
        _rule_row_html(index, kind, value, theme_id, created_at, now)
        for index, (kind, value, theme_id, created_at) in enumerate(rows)
    ]
    return (
        '<div class="data-table-wrap">'
        '<table class="data-table">'
        "<thead><tr>%s</tr></thead>"
        "<tbody>%s</tbody>"
        "</table>"
        "</div>"
    ) % (header_cells, "".join(body_rows))


def _rules_cards_html(rows, now):
    """The mobile (`<960px`) `.data-cards` representation — one
    `<li class="data-card">` per rule, no `data-filter-text`/
    `data-filter-group` attributes (this list has no filter bar, mirroring
    the manual-resolutions list's own precedent). Returns `""` for an
    empty list, matching `_rules_table_html()`'s own no-chrome-with-no-data
    rule (never called on the empty branch in practice — `_rules_section_
    html()` renders the empty state instead — but kept total for the same
    reason `_manual_resolution_cards_html()` is).
    """
    if not rows:
        return ""
    items = []
    for kind, value, theme_id, created_at in rows:
        primary = (
            '<div class="data-card__primary">'
            '<span class="cell-primary mono">%s</span>'
            '<span class="data-card__value">%s</span>'
            "</div>"
        ) % (escape_html(value), _rule_theme_swatch_html(theme_id))
        kind_secondary = (
            '<div class="data-card__secondary">'
            '<span class="data-card__label">%s</span>%s'
            "</div>"
        ) % (escape_html(RULE_HEADERS[0]), escape_html(RULE_KIND_LABELS.get(kind, kind)))
        added_secondary = (
            '<div class="data-card__secondary">'
            '<span class="data-card__label">%s</span>%s'
            "</div>"
        ) % (
            escape_html(RULE_HEADERS[3]),
            layout.concise_timestamp_html(created_at, now, fallback=""),
        )
        delete_form = (
            '<form method="post" action="%s">'
            '<button type="submit">%s</button>'
            "</form>"
        ) % (_rule_delete_action(kind, value), DELETE_BUTTON_TEXT)
        items.append(
            '<li class="data-card">%s%s%s%s</li>'
            % (primary, kind_secondary, added_secondary, delete_form))
    return '<ul class="data-cards">%s</ul>' % "".join(items)


def _rules_section_html(ctx):
    """The per-flight colour-rules editor's own `<section class=
    "page-section">` (D-10, D-11): heading, one caption, the add form,
    then either `layout.empty_state()` or the card list followed by the
    table wrapper.

    **Placement decision** (15-UI-SPEC.md Section Anatomy §2's Open
    Question 1, confirmed at plan time): this section renders immediately
    after `</form>` closes, taking the slot the Poll section used to
    occupy — Poll itself moves one slot later. HTML forbids nesting a
    `<form>` inside another `<form>`, and the add form plus each delete
    row are real `<form>` elements, so this section cannot be a
    descendant of `<form id=SETTINGS_FORM_ID>`. Every existing group's DOM
    nesting stays byte-identical; only the top-level ordering of the two
    sections after the form changes. This section carries no
    `DIRTY_SECTION_ATTR` — it is not part of the tracked settings form,
    exactly like the Poll section, whose action is likewise immediate.

    Reads the rules registry from `ctx["colour_rules"]` (Task 2 threads
    this in, read fresh per request from `colour_rules.load_colour_
    rules(state_dir)` — never the poll-cycle process cache), falling back
    to the empty registry shape when the key is absent so `render({})`
    still works.
    """
    registry = ctx.get("colour_rules")
    if not isinstance(registry, dict):
        registry = {kind: {} for kind in colour_rules.RULE_KINDS}
    now = ctx.get("now")
    rows = colour_rules.rule_rows(registry)

    heading = '<h2 class="text-heading">%s</h2>' % escape_html(RULES_SECTION_HEADING)
    caption = (
        '<p class="text-label section-caption">%s</p>'
        % escape_html(RULES_SECTION_CAPTION))
    add_form = _rule_add_form_html()

    if not rows:
        body = layout.empty_state(RULES_EMPTY_HEADING, RULES_EMPTY_BODY)
        return '<section class="page-section">%s%s%s%s</section>' % (
            heading, caption, add_form, body)

    # Cards render before the table — style.css's `.data-cards ~
    # .data-table-wrap` sibling-combinator toggle depends on this exact
    # DOM order (mirrors airlines_page._manual_resolutions_section_html()'s
    # own load-bearing warning; do not reorder these two calls).
    cards_html = _rules_cards_html(rows, now)
    table_html = _rules_table_html(rows, now)
    return '<section class="page-section">%s%s%s%s%s</section>' % (
        heading, caption, add_form, cards_html, table_html)


def render(ctx, scope=SCOPE_ALL, errors=None, submitted=None):
    """Render one settings page (SCOPE_ALL/SCOPE_DISPLAY/SCOPE_DEVICE).

    19-07-PLAN.md Task 2 (D-07/A-25): `errors` and `submitted` are both
    fully-defaulted keyword parameters placed last, so every one of the
    46 pre-Phase-19 call sites keeps producing byte-identical output.
    `companion/app.py`'s `_handle_settings_post()` is the sole caller
    that passes both, on a rejected save: `errors` is the dict
    `config_page.handle_post()` just filled, and `submitted` is the raw
    form dict, threaded straight through to every group builder via the
    `builders` dict below so each control can repopulate its own field
    and render its own error message.

    `errors` is normalised to `{}` here (harmless either way — every
    lookup below already treats `None`/`{}` identically). `submitted` is
    deliberately NOT collapsed to `{}`: `None` (every ordinary page-load
    render) and an actual dict (a real, possibly-empty submission being
    repopulated) mean different things to the absent-means-unchecked
    checkbox fields (`_submitted_checkbox_checked()`) — collapsing that
    distinction away would render every checkbox in that family
    unchecked on every ordinary page load, since an ordinary load never
    "submits" any of them either.
    """
    if errors is None:
        errors = {}
    device_cfg = ctx.get("device_config") or {}
    current_theme_id = device_cfg.get("theme", device_config.DEFAULT_THEME_ID)
    # Phase 15 D-04: an explicit `.get()` with no `or` fallback and no
    # default — `None` is a meaningful value here (no arrivals-theme
    # override, same as the departures theme), the same reasoning
    # current_wake_interval_s's own read below already carries.
    current_theme_arriving = device_cfg.get("theme_arriving")
    current_runway_id = device_cfg.get(
        "tracked_runway", device_config.DEFAULT_RUNWAY_ID)
    current_led_enabled = device_cfg.get(
        "led_enabled", device_config.DEFAULT_LED_ENABLED)
    current_quiet_enabled = device_cfg.get(
        "quiet_hours_enabled", device_config.DEFAULT_QUIET_HOURS_ENABLED)
    current_quiet_start = device_cfg.get(
        "quiet_hours_start", device_config.DEFAULT_QUIET_HOURS_START)
    current_quiet_end = device_cfg.get(
        "quiet_hours_end", device_config.DEFAULT_QUIET_HOURS_END)
    # D-07 (11-UI-SPEC.md): an explicit `is None` test, not `or` — `0` is
    # never a valid wake_interval_s (WAKE_INTERVAL_MIN_S is 60), but `or`
    # would still be the wrong idiom to reach for here even so. Falls back
    # to ctx["wake_interval_env_default"], the deployed SKYPANE_SLEEP_S
    # value plan 11-04 reads out of the companion process's own environment
    # (systemd injects it via the same EnvironmentFile=/opt/skypane/
    # skypane.env directive skypane-byos.service uses). That key is absent
    # — resolving to None, i.e. the placeholder empty state — on any local
    # or dev run without the systemd unit.
    current_wake_interval_s = device_cfg.get("wake_interval_s")
    if current_wake_interval_s is None:
        current_wake_interval_s = ctx.get("wake_interval_env_default")
    # D-09 (12-CONTEXT.md): an explicit boolean default, matching
    # current_led_enabled's/current_quiet_enabled's own precedent — a config
    # predating this field renders the box checked, not unchecked, so
    # nothing changes for an installation already in service.
    current_display_enabled = device_cfg.get(
        "display_enabled", device_config.DEFAULT_DISPLAY_ENABLED)
    # Phase 16 (16-05-PLAN.md): read fresh per request, matching every
    # other ctx-threaded value in this function. An explicit `.get()` with
    # no `or` fallback — `None` is meaningful here (no calendar theme
    # chosen yet, default to the base theme), the same reasoning
    # current_theme_arriving's own read above already carries.
    current_calendar_theme_id = device_cfg.get("calendar_theme_id")
    calendar_configured = ctx.get("calendar_configured")
    calendar_last_synced_at = ctx.get("calendar_last_synced_at")
    # Phase 17 plan 03 (D-02): plan 17-04 supplies this context key
    # (calendar_rules.calendar_secret_mode_is_unsafe(state_dir)). Until
    # then this degrades to a falsy default rather than raising, matching
    # how calendar_configured/calendar_last_synced_at above already read.
    calendar_drift = ctx.get("calendar_drift")
    cooldown_remaining = ctx.get("poll_cooldown_remaining", 0)
    # 19-12-PLAN.md Task 3 (D-13): the same wake.next_wake_at_iso() +
    # layout.local_clock_text() pipeline home_page.py's Frame tile uses,
    # computed once here and threaded into every caption site below via
    # _with_next_wake() plus rendered again in the Device header slot.
    # None when the value is unknown (no check-in yet, or no known
    # interval) — every consumer already treats a falsy value as "omit
    # the suffix/line entirely" (D-13: "where the value is known").
    next_wake_clock = None
    next_wake_iso = wake.next_wake_at_iso(ctx.get("last_checkin_ts"), device_cfg)
    if next_wake_iso:
        next_wake_parsed = layout.parse_iso(next_wake_iso)
        if next_wake_parsed is not None:
            next_wake_clock = layout.local_clock_text(
                next_wake_parsed, now_parsed=layout.parse_iso(ctx.get("now")))

    # D-05 (06.6.4.1): the LED group used to be a sibling page-section,
    # appended AFTER the Poll section, rather than a third fieldset
    # inside this form — 06.3-UI-SPEC.md line 181 locked a 2-column grid
    # over this form's fieldsets at >=960px, and a third fieldset there
    # would have become a silent 2+1 orphan row. That grid is deleted
    # outright by 06.6.4.1-01 (D-01) — the premise this comment used to
    # describe no longer exists, so the LED group (led_group(), below) is
    # now a third sibling group inside this same <form>, after Runway,
    # before the bottom Save settings button. Do not restore the
    # separate section by reading a stale rationale.
    #
    # D-03: data-dirty-form and the dirty-bar markup below are a JS-only
    # enhancement layered on top of this always-server-rendered form —
    # dirty-state.js reads these exact attributes.
    #
    # quick task 260901-re6: the dirty-bar used to be a genuine descendant
    # of this <form>, between the three groups and the always-visible
    # bottom Save settings button, submitting natively via normal DOM
    # nesting with no form= attribute needed. That premise broke the
    # bar's own `position: sticky; bottom: 0` styling: a sticky element's
    # containing block is its nearest scrolling ancestor's *box* — here
    # the short three-section form — so the bar stopped sticking at the
    # form's own bottom edge instead of the viewport's, visibly detaching
    # and stopping above the Poll section on a page much taller than the
    # form. The bar is now a sibling, emitted last on the page (after
    # both `</form>` and the Poll `</section>`), positioned `fixed`
    # instead of `sticky` at >=960px. companion/static/dirty-state.js
    # needs no change for this: its `[data-dirty-bar]` /
    # `[data-dirty-count]` / `[data-dirty-cancel]` lookups are already
    # document-wide `document.querySelector` calls, not scoped to the
    # form, and its cancel handler already calls `form.reset()` on its
    # own separately-resolved form reference. The save button's
    # `form="{SETTINGS_FORM_ID}"` attribute is what preserves native
    # submission of the merged settings form despite the bar now living
    # outside it in the DOM — narrowing any of those three JS lookups to
    # a form-scoped query would silently break the bar.
    dirty_bar_html = (
        '<div class="dirty-bar" data-dirty-bar hidden role="status">'
        "<span data-dirty-count>%s</span>"
        '<button type="submit" class="dirty-bar__save" form="%s">Save settings</button>'
        '<button type="button" class="dirty-bar__cancel" data-dirty-cancel>Cancel</button>'
        "</div>"
    ) % (escape_html(DIRTY_BAR_INITIAL_TEXT), SETTINGS_FORM_ID)

    # Phase 15 D-10 (15-05-PLAN.md, 15-UI-SPEC.md Section Anatomy §2's
    # Open Question 1, confirmed): the rules section renders immediately
    # after </form> closes, taking the slot the Poll section used to
    # occupy — Poll itself moves one slot later, below. See
    # _rules_section_html()'s own docstring for the full reasoning (HTML
    # forbids nesting a <form> inside another <form>, and the add form
    # plus each delete row are real <form> elements, so this section
    # cannot be a descendant of <form id=SETTINGS_FORM_ID>). Every
    # existing group's DOM nesting above stays byte-identical; only the
    # top-level ordering of the two sections after the form changes.
    screen_id = screens.current_screen_id(ctx)
    screen = screens.screen_type(screen_id)
    if scope not in SCOPES:
        scope = SCOPE_ALL
    groups = scope_groups(scope, screen_id)

    builders = {
        screens.GROUP_THEME: lambda: theme_fieldset(
            current_theme_id, current_theme_arriving,
            errors=errors, submitted=submitted, next_wake_clock=next_wake_clock),
        screens.GROUP_RUNWAY: lambda: runway_fieldset(
            current_runway_id, ctx.get("runway_images") or (),
            errors=errors, submitted=submitted, next_wake_clock=next_wake_clock),
        screens.GROUP_LED: lambda: led_group(
            current_led_enabled, errors=errors, submitted=submitted,
            next_wake_clock=next_wake_clock),
        screens.GROUP_QUIET_HOURS: lambda: quiet_hours_group(
            current_quiet_enabled, current_quiet_start, current_quiet_end,
            errors=errors, submitted=submitted, next_wake_clock=next_wake_clock),
        screens.GROUP_WAKE_INTERVAL: lambda: wake_interval_group(
            current_wake_interval_s, errors=errors, submitted=submitted,
            next_wake_clock=next_wake_clock),
        screens.GROUP_DISPLAY: lambda: display_group(
            current_display_enabled, errors=errors, submitted=submitted),
        screens.GROUP_CALENDAR: lambda: calendar_group(
            calendar_configured, calendar_drift, calendar_last_synced_at,
            ctx.get("now"), current_calendar_theme_id, current_theme_id,
            errors=errors, submitted=submitted),
    }
    groups_html = "".join(builders[g]() for g in groups if g in builders)

    # 19-12-PLAN.md Task 2 (D-23): the conditional selector joins the
    # screen caption in BOTH scoped headers' action_html slot — with
    # today's single-member registry it renders as "", so both headers
    # stay byte-identical to their pre-D-23 output.
    if scope == SCOPE_DISPLAY:
        header = layout.page_header(
            DISPLAY_PAGE_TITLE, purpose=DISPLAY_PAGE_PURPOSE,
            action_html=_screen_caption_html(screen) + _screen_selector_html(screen_id))
        hidden_html = _scope_fields_html(scope, layout.DISPLAY_ROUTE)
        show_rules = show_poll = show_calendar_disconnect = False
    elif scope == SCOPE_DEVICE:
        # 19-12-PLAN.md Task 2 (D-22, Device-page half): the Edit
        # artwork link is Device-only, joining the screen caption/
        # selector in the same action_html slot.
        # 19-12-PLAN.md Task 3 (D-13): "Home and Device show" — the
        # Next-wake line joins the same slot, Device-only (Display
        # instead carries the per-caption suffixes via next_wake_clock
        # threaded into the builders dict above).
        header = layout.page_header(
            DEVICE_PAGE_TITLE, purpose=DEVICE_PAGE_PURPOSE,
            action_html=(
                _screen_caption_html(screen) + _screen_selector_html(screen_id)
                + _edit_artwork_link_html()
                + _next_wake_caption_html(next_wake_clock)))
        hidden_html = _scope_fields_html(scope, layout.DEVICE_ROUTE)
        show_rules = bool(screen.get("has_colour_rules"))
        show_poll = bool(screen.get("has_manual_poll"))
        # 19-11-PLAN.md Task 1 (D-08/A-26): the standalone disconnect
        # form is Device-only, matching screens.GROUP_CALENDAR's own
        # scoping — a screen type without the Calendar group has nothing
        # to disconnect either.
        show_calendar_disconnect = screens.GROUP_CALENDAR in groups
    else:
        header = layout.page_header("Settings")
        hidden_html = ""
        show_rules = show_poll = True
        # SCOPE_ALL is the legacy whole-page render, kept byte-identical
        # to its own pre-Phase-19 output for existing harness checks
        # against the full form — never used by a live app.py route
        # (render()'s own module comment). The disconnect action's own
        # confirmed-form flow is new surface Task 1 adds only to the two
        # live scoped pages; SCOPE_ALL stays exactly as it was.
        show_calendar_disconnect = False

    rules_section_html = _rules_section_html(ctx) if show_rules else ""
    poll_section_html = (
        '<section class="page-section">'
        '<h2 class="text-heading">%s</h2>'
        "%s"
        "</section>" % (escape_html(POLL_SECTION_HEADING), poll_trigger_section(cooldown_remaining))
        if show_poll else "")
    # 19-11-PLAN.md Task 1 (D-08/A-26): a sibling of the settings <form>,
    # never a descendant — see calendar_disconnect_section()'s own
    # docstring for why. Emitted immediately after </form> closes, before
    # the rules/poll sections, so it reads right after the Calendar group
    # it acts on despite living outside the form that group is inside.
    calendar_disconnect_html = (
        calendar_disconnect_section(calendar_configured, calendar_drift)
        if show_calendar_disconnect else "")

    return (
        header
        + '<form class="config-form" id="%s" data-dirty-form method="post" action="%s">'
        "%s"
        "%s"
        '<button type="submit" %s>Save settings</button>'
        "</form>"
        "%s"
        "%s"
        "%s"
        "%s"
    ) % (
        SETTINGS_FORM_ID,
        SETTINGS_ROUTE,
        hidden_html,
        groups_html,
        STATIC_SAVE_FALLBACK_ATTR,
        calendar_disconnect_html,
        rules_section_html,
        poll_section_html,
        dirty_bar_html,
    )


def _screen_caption_html(screen):
    """The small "Screen: Plane frame" line under a scoped page's title —
    the visible end of the companion/screens.py seam. Rendered as an
    already-safe block for page_header()'s `action_html` slot.
    """
    return (
        '<p class="page-header__screen text-label">%s</p>'
        % escape_html(SCREEN_CAPTION_TEMPLATE % screen["label"]))


NEXT_WAKE_HEADER_LABEL = "Next wake"
NEXT_WAKE_HEADER_VALUE_TEMPLATE = "≈ %s"


def _next_wake_caption_html(next_wake_clock):
    """The Device page header's own "Next wake ≈ HH:MM" line (D-13/S-02:
    "Home and Device show" — this is the Device half; Home's own copy
    lives in companion/pages/home_page.py). Returns the EMPTY STRING
    when `next_wake_clock` is falsy — no placeholder, no "unknown" —
    matching `_with_next_wake()`'s identical omit-when-unknown contract
    for the per-group caption suffixes.
    """
    if not next_wake_clock:
        return ""
    return (
        '<p class="page-header__screen text-label">%s</p>'
        % escape_html(
            "%s %s" % (
                NEXT_WAKE_HEADER_LABEL,
                NEXT_WAKE_HEADER_VALUE_TEMPLATE % next_wake_clock)))


def _screen_selector_html(current_screen_id):
    """A `<select name="screen_id">` letting the operator switch which
    registered screen type this settings page edits — 19-12-PLAN.md Task
    2 (D-23)'s explicit condition: returns the EMPTY STRING when
    `len(screens.SCREEN_IDS) <= 1` (a one-option "choice" has no real
    decision value, the same reasoning `theme_fieldset()`'s single-theme
    branch already applies), so with today's single-screen registry the
    Display/Device headers stay byte-identical to their pre-D-23 output.

    Rendered inside `layout.page_header()`'s `action_html` slot — i.e.
    visually and structurally BEFORE `<form id="{SETTINGS_FORM_ID}">`
    opens — but it must still submit with that form. The
    `form="{SETTINGS_FORM_ID}"` attribute is what makes that possible,
    the same "control lives outside the form's own DOM nesting but
    submits with it anyway" idiom `render()`'s own dirty-bar Save button
    already uses (see its own comment above).

    Every option's value and label are escaped at their interpolation
    point (labels come from the fixed `screens.SCREEN_TYPES` registry,
    never request data, but this file's universal escaping discipline
    applies with no exceptions). A visually-hidden `<label for=...>`
    supplies the control's accessible name, matching this file's
    settings-checkbox `<label>` convention rather than an `aria-label`
    attribute.
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
    return (
        '<label class="visually-hidden" for="%s">%s</label>'
        '<select name="screen_id" id="%s" form="%s">%s</select>'
    ) % (
        SCREEN_SELECTOR_ID, escape_html(SCREEN_SELECTOR_LABEL_TEXT),
        SCREEN_SELECTOR_ID, SETTINGS_FORM_ID, "".join(options),
    )


def _edit_artwork_link_html():
    """The Device page's own "Edit artwork" link to `/airlines?edit=1`
    (D-22's Device-page half, 19-12-PLAN.md Task 2) — built from
    `layout.AIRLINES_ROUTE` (already duplicated there, the same
    duplicated-not-imported route this file's other cross-page
    constants use) and `EDIT_QUERY_PARAM` (imported from airlines_page,
    the deliberate exception this file's own import comment above
    documents), never a retyped "/airlines?edit=1" literal. Rendered as
    an already-safe block for `layout.page_header()`'s `action_html`
    slot, in the section-caption voice.
    """
    return (
        '<p class="page-header__screen text-label">'
        '<a class="text-label" href="%s?%s=1">%s</a></p>'
        '<p class="text-label section-caption">%s</p>'
    ) % (
        layout.AIRLINES_ROUTE, EDIT_QUERY_PARAM,
        escape_html(EDIT_ARTWORK_LINK_TEXT),
        escape_html(EDIT_ARTWORK_LINK_CAPTION),
    )


def _scope_fields_html(scope, return_route):
    return (
        '<input type="hidden" name="%s" value="%s">'
        '<input type="hidden" name="%s" value="%s">'
    ) % (
        SCOPE_FIELD_NAME, escape_html(scope),
        RETURN_TO_FIELD_NAME, escape_html(return_route),
    )


# Phase 17 plan 03 (D-07): the four outcomes of the submitted calendar
# fields' three-way resolution. Plain strings, never rendered and never
# travel in a URL. Kept as four distinct sentinels (not e.g. two bools)
# so a caller cannot mistake one outcome for another by falsy-comparing
# the wrong pair.
CALENDAR_URL_SIGNAL_CARRY_FORWARD = "carry_forward"
CALENDAR_URL_SIGNAL_SET = "set"
CALENDAR_URL_SIGNAL_CLEAR = "clear"
CALENDAR_URL_SIGNAL_INVALID = "invalid"

# D-07 (19-07-PLAN.md, A-25): handle_post()'s per-field error messages —
# one constant per rejected field, matching this file's
# constants-at-the-top convention, so the copy exists in exactly one
# place and _note_error() below never inlines a string literal. Sentence
# case, no requirement ids, no stack-trace vocabulary, matching the
# label voice every other user-facing string in this file already uses.
ERROR_INVALID_CHOICE = "That is not one of the available choices."
ERROR_UNEXPECTED_SWITCH_VALUE = "That switch sent an unexpected value."
ERROR_WAKE_INTERVAL_RANGE = "Enter a whole number of seconds between 60 and 3600."
ERROR_QUIET_HOURS_TIME_SHAPE = "Enter a time as HH:MM, for example 23:00."
# Covers both the over-length and the contradictory-submission
# (calendar_url + calendar_disconnect together) cases
# submitted_calendar_signal() folds into CALENDAR_URL_SIGNAL_INVALID —
# deliberately worded to never echo any part of the submitted URL back.
ERROR_CALENDAR_URL_INVALID = (
    "That link is too long, or conflicts with the disconnect option below.")

# A LOCAL copy of server/device_config.py's private `_HHMM_RE` (24-hour,
# zero-padded "HH:MM") — deliberately NOT an import of that name, which
# is private to that module (D-07's own read_first instruction). This is
# a UX pre-check only: save_device_config()'s own identical gate remains
# the authoritative one, and companion/test_config_page.py pins the two
# patterns against the same table of inputs so they cannot silently
# drift apart.
_QUIET_HOURS_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)\Z")


def _note_error(errors, field, message):
    """No-ops when `errors is None` — every existing caller of
    handle_post()/render() before this plan, and any future caller that
    still doesn't care about field-level errors. Otherwise sets
    `errors[field] = message` only if that field has no message yet:
    first error per field wins, so a later, more generic gate can never
    overwrite an earlier, more specific one.
    """
    if errors is None:
        return
    if field not in errors:
        errors[field] = message


def submitted_calendar_signal(form):
    """The single definition of what a submitted `calendar_url` +
    `calendar_disconnect` pair means. Both `handle_post()` below and plan
    17-04's request handler call this — never reimplement the logic — so
    the two can never drift into disagreeing about what a given
    submission meant.

    Resolution order, each a real gate a caller must clear before the
    next is even considered:

    1. A `calendar_disconnect` present with any value other than
       `CALENDAR_DISCONNECT_CHECKBOX_VALUE` is a crafted request shape,
       not a user mistake — the same treatment every other checkbox on
       this handler already gives a non-member value. Resolves invalid.
    2. A `calendar_disconnect` present together with a non-empty
       (stripped) `calendar_url` is contradictory: the operator has
       asked to disconnect and to connect in the same submission, and
       there is no defensible guess at which one they meant. Resolves
       invalid rather than picking one.
    3. A `calendar_disconnect` present (and clearing gate 2) resolves
       clear.
    4. An empty (or whitespace-only, or absent) `calendar_url` with no
       checkbox resolves carry-forward — THE branch the whole checkbox
       exists to make possible (D-07). D-01/D-02 make the field
       write-only, so it renders empty on EVERY page load regardless of
       state; an unrelated Settings save (changing a theme, say) would
       therefore submit it empty too. Treating that as a disconnect
       signal would disconnect the calendar on every save that doesn't
       touch the calendar at all — this is the exact defect D-07 exists
       to correct in D-04's original wording.
    5. A stripped `calendar_url` longer than `CALENDAR_URL_MAX_LEN`
       resolves invalid — a shape bound against an absurd paste, not a
       second definition of an acceptable URL (see CALENDAR_URL_MAX_LEN's
       own comment).
    6. Otherwise resolves set.

    Never raises, and never itself calls `calendar_rules.save_calendar_
    url()` — resolving the signal and acting on it are deliberately two
    separate steps so `handle_post()` can gate the persistence call
    behind the OTHER fields' validation first (the all-or-nothing
    contract) without this function needing to know about them.

    19-11-PLAN.md (D-08/A-26, 19-RESEARCH.md Pitfall 7): the in-form
    `calendar_disconnect` checkbox this function's gates 1-3 above were
    built to interpret is now RETIRED from `calendar_group()`'s own
    markup — disconnecting is `CALENDAR_DISCONNECT_ROUTE`'s own dedicated
    route (`companion/app.py`'s `_handle_calendar_disconnect_post()`),
    which never calls this function at all: that route always means
    "disconnect", once its own confirm gate passes, so consulting this
    resolver there would be dead weight. Gates 1-3 are DELIBERATELY LEFT
    IN PLACE rather than deleted, even though the ordinary rendered form
    can no longer produce a `calendar_disconnect` field: a hostile client
    can still craft that field directly into a `/settings` POST body, and
    `handle_post()`'s existing all-or-nothing rejection (via this
    function's `invalid` outcome) is what continues to cover that shape.
    Deleting the gates would not remove any real capability — it would
    just make a crafted request's outcome unspecified instead of
    correctly rejected.
    """
    # Phase 18: a page that never rendered the Calendar group cannot
    # have meant anything by the field's absence — carry forward before
    # any other gate is consulted.
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
    """Validate the submitted theme/runway/LED/quiet-hours/wake-interval/
    display state against `device_config`'s own registries and validators —
    server-side, before any value is used anywhere — and persist all
    eight fields in a single `save_device_config()` call (D-05, 06.6.4.1:
    this handler absorbed what the now-retired `handle_led_post()` used to
    do on its own separate `POST /config-led` route — removed outright in
    06.6.4.1-07 once this route became the sole settings-writing path;
    10-05-PLAN.md extended the same single-call contract to the three
    quiet-hours fields, 11-03-PLAN.md extended it again to
    wake_interval_s, and 12-05-PLAN.md extends it again to
    display_enabled, rather than adding a second write path).

    Deliberately does NOT call any of `device_config`'s read-path
    normalising helpers (the ones an unrecognised on-disk value silently
    degrades through to the default): those implement the *read* path's
    forgiving behaviour, whereas a *write* of an unrecognised value is a
    real client error that must be reported back to the user, not
    silently coerced — the asymmetry is deliberate (06-CONTEXT.md
    D-06/D-07, 06-RESEARCH.md's V5 threat control). Instead, each
    submitted field is checked explicitly before it is ever used as a
    dict key or passed onward: `theme`/`tracked_runway` by membership
    test against `device_config.THEME_IDS`/`RUNWAY_IDS`, `led_enabled`/
    `quiet_hours_enabled`/`display_enabled` by exact equality against
    `LED_CHECKBOX_VALUE`/`QUIET_HOURS_CHECKBOX_VALUE`/
    `DISPLAY_CHECKBOX_VALUE`. `quiet_hours_start`/`quiet_hours_end`
    are passed straight through, unchecked, to `save_device_config()`
    itself — deliberately not pre-validated here against the HH:MM
    shape-gate regex `device_config` keeps as a private module-level
    name — because that function already validates both fields strictly
    against that same regex and raises `ValueError` before it ever
    touches the file, which this handler's existing
    `except (ValueError, OSError)` below already maps to the generic
    save-failed flash. All-or-nothing rejection holds because that
    validation happens before any write.

    Three properties are load-bearing here, not incidental:

    First, the LED, quiet-hours-enable and display-enable checkboxes'
    absent-means-False semantics is deliberately different from theme's,
    runway's, and the quiet-hours times' absent-means-unchanged semantics.
    A field absent from `form` for `theme`/`tracked_runway`/
    `quiet_hours_start`/`quiet_hours_end` means "leave unchanged" and is
    passed as `None`, which `save_device_config()` carries forward from the
    current on-disk value — because a radio group, a select, and a
    text/time input always submit *some* value once one is set, absence
    there only ever means "this page didn't render that control." An HTML
    checkbox is different: an *unchecked* checkbox is omitted from the
    POST body entirely, so `led_enabled`'s, `quiet_hours_enabled`'s and
    `display_enabled`'s absence must each resolve to `False`, never to
    "leave unchanged" — carrying either forward instead would silently
    re-enable a disabled LED, a curfew the user just turned off, or a
    display the user just switched off, on every save that happens to
    leave the box unchecked. Exactly three shapes are resolved for each
    checkbox field and no others: absent -> `False`; equal to its own
    `*_CHECKBOX_VALUE` -> `True`; anything else (a crafted/hostile value)
    -> reject the whole submission.

    Second, an unchecked "Enable quiet hours" checkbox still persists any
    edited `quiet_hours_start`/`quiet_hours_end` values — this resolves
    10-RESEARCH.md's Assumption A1 / Open Question 2 in the affirmative,
    per 10-UI-SPEC.md's locked Interaction Contract: a user can
    pre-configure a window before ever turning it on. This is a decision,
    not an oversight.

    Third, rejection stays all-or-nothing across all eight fields, now more
    so than before the merge: because there is still one form and one
    `save_device_config()` call, a crafted or invalid value in ANY field
    aborts before that call, never persisting the valid remainder —
    applying only the valid half would leave the on-disk state out of
    sync with what the page would redisplay on the very next load.

    Fourth, `wake_interval_s` needs an explicit string-to-int conversion
    gate that `quiet_hours_start`/`quiet_hours_end` deliberately do not:
    those two fields are strings end-to-end and are correctly passed
    through unconverted, but `wake_interval_s` is an int end-to-end in
    `device_config.py`, so the same pass-through habit here would make
    `save_device_config()`'s type check reject every legitimate
    submission (11-RESEARCH.md Pitfall 1 — the single highest-risk
    copy-paste mistake in this phase). An absent or empty-string
    `wake_interval_s` resolves to `None`, meaning leave unchanged — a
    numeric input a user clears mid-edit is an incomplete edit, not an
    invalid one, and the all-or-nothing contract above is about invalid
    values (11-RESEARCH.md Open Question 2). Anything else is passed to
    `int()` inside a `try`, whose `ValueError` returns `FLASH_SAVE_FAILED`
    before any write; `save_device_config()`'s own range check raises
    `ValueError` for an out-of-bounds int, already mapped to the same
    generic flash by the `except (ValueError, OSError)` clause below — no
    field-specific error copy is added (11-UI-SPEC.md's Copywriting
    Contract locks reuse of the existing generic flash).

    Fifth (19-07-PLAN.md, D-07/A-25): `errors` is an optional
    caller-supplied dict, filled in place via `_note_error()` at every
    `FLASH_SAVE_FAILED` return site below, keyed on the submitted form
    field that failed. It is purely additive — the all-or-nothing
    rejection contract above is unchanged, and the return value is
    unchanged (still a bare flash-key string, never a tuple) — so every
    existing caller that does not pass `errors` behaves byte-identically
    to before this plan. Three new pre-checks join the existing gates
    below so a real user error (a malformed quiet-hours time, an
    out-of-range wake interval, an invalid calendar submission) is
    reported at that field instead of falling through to the generic
    `except (ValueError, OSError)` clause.

    On success, the frame's next scheduled poll cycle (server/poll_loop.py,
    D-06/D-28) is the first place any of the eight changes actually take
    effect — no push mechanism exists, and none is added here. `display_
    enabled` is the one exception to "next scheduled poll": D-01
    (12-CONTEXT.md) pins the off-state check-in to a fixed 300s cadence
    independent of `wake_interval_s`, which is why `DISPLAY_SECTION_CAPTION`
    states its own honest ~5-minute latency rather than reusing this
    generic clause. The caller (companion/app.py) redirects back to
    `SETTINGS_ROUTE`, whose banner then renders the D-07 confirmation copy
    the FLASH_SAVED key maps to, telling the user their change was saved
    but has not yet reached the physical frame. No quiet-hours-specific or
    display-specific flash message exists — saving reuses FLASH_SAVED/
    FLASH_SAVE_FAILED verbatim, per 10-UI-SPEC.md's/12-UI-SPEC.md's
    Copywriting Contract.

    Phase 16 (16-05-PLAN.md) adds one more form field, `calendar_theme_id`
    — a plain tracked field with no checkbox, so unlike `theme_arriving`
    it needs no clear sentinel: `None` keeps its single existing meaning,
    "not supplied, carry forward". It is validated by the identical
    membership test `theme`/`tracked_runway` already use and passed
    through as one more keyword argument on the same, still-singular
    `save_device_config()` call.

    Phase 15 D-04/D-05 add two more form fields, `theme_arriving_enabled`
    (the arrivals-override checkbox) and `theme_arriving` (the second
    grid's selected theme id), with a genuinely different resolution from
    every other checkbox above: `theme_arriving` is validated by the same
    membership test `theme` uses, then the CHECKBOX field alone (never
    `theme_arriving`'s presence) decides whether the validated id is
    persisted or the override is cleared via
    `device_config.CLEAR_THEME_ARRIVING` — see the inline comment at that
    branch for why keying off either `theme_arriving`'s presence or `None`
    would silently break the clear path. The result is passed as one more
    keyword argument on the same, still-singular persistence call below;
    the all-or-nothing rejection contract is unchanged.

    Phase 17 plan 03 (D-01/D-02/D-07) adds `calendar_url` and
    `calendar_disconnect`, resolved by `submitted_calendar_signal()`
    above into exactly one of four outcomes rather than inline here, so
    plan 17-04's request handler can share the identical resolution. An
    `invalid` outcome joins the other membership gates below and rejects
    the whole save before `save_device_config()` is ever called — same
    all-or-nothing contract. The other three outcomes are acted on only
    AFTER that call succeeds, and only `set`/`clear` ever call
    `calendar_rules.save_calendar_url()` — `carry_forward` calls it not
    at all, because every successful call to that writer erases the
    fetched calendar registry (D-04/D-05), and calling it on a save that
    never touched the calendar field would silently wipe the calendar's
    flights on every unrelated settings change.

    This checkbox's polarity is the deliberate INVERSE of
    `theme_arriving_enabled`'s just above: that one is rendered checked
    when the override is set and its ABSENCE from the submission means
    clear; `calendar_disconnect` is rendered unchecked always and its
    PRESENCE means clear. The direction is deliberately the safe one —
    doing nothing is the default — because D-01/D-02 make the calendar
    URL field write-only, so it is empty on every single page load
    regardless of state; an absent-means-clear checkbox here (copying
    `theme_arriving_enabled`'s own polarity instead of inverting it)
    would disconnect the calendar on every save that doesn't touch it.

    The device-config write goes first, unchanged from every save that
    touches no calendar field, and the secret write is layered after it
    deliberately: this leaves a narrow window in which the device config
    has been written but the secret write then fails, but the operator
    sees the generic failure flash and can simply retry, and the
    alternative — writing the secret first — would perturb the ordering
    of every save in this handler, existing or new, to close a window
    that only opens when the state directory is already failing.

    19-12-PLAN.md Task 2 (D-23) adds one more form field, `screen_id`,
    submitted only by `_screen_selector_html()`'s `<select>` (itself
    only rendered once a second screen type is registered). It follows
    the exact membership-test-before-use shape every other
    hostile-request-shape gate above already uses: a non-`None` value
    outside `screens.SCREEN_IDS` rejects the whole save via
    `FLASH_SAVE_FAILED` before `save_device_config()` is ever called,
    and the validated value is passed through as one more keyword
    argument on the SAME, still-singular `save_device_config()` call —
    never a second write path. With today's single-member registry the
    field is never actually submitted by the real form, so this gate is
    exercised only by a crafted request.
    """
    state_dir = ctx["state_dir"]
    # Phase 18: which groups were actually on the submitted page. A
    # checkbox belonging to a group that was NOT rendered is absent from
    # the body for a structural reason, not because the user unticked
    # it — so for those groups absence resolves to None (carry the
    # on-disk value forward), never to False.
    scope = submitted_scope(form)
    in_scope = set(scope_groups(scope, screens.current_screen_id(ctx)))
    submitted_theme = form.get("theme")
    submitted_theme_arriving = form.get("theme_arriving")
    submitted_theme_arriving_enabled = form.get("theme_arriving_enabled")
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
    calendar_signal = submitted_calendar_signal(form)

    if submitted_theme is not None and submitted_theme not in device_config.THEME_IDS:
        _note_error(errors, "theme", ERROR_INVALID_CHOICE)
        return FLASH_SAVE_FAILED
    # 19-12-PLAN.md Task 2 (D-23): the same membership-test-before-use
    # shape every sibling gate here already uses.
    if submitted_screen_id is not None and submitted_screen_id not in screens.SCREEN_IDS:
        _note_error(errors, "screen_id", ERROR_INVALID_CHOICE)
        return FLASH_SAVE_FAILED
    # Phase 17 plan 03 (D-07): the resolver's own `invalid` outcome joins
    # every other membership/shape gate here, before any write — a
    # crafted checkbox value, a contradictory URL+checkbox submission,
    # and an over-length URL are all rejected the identical way.
    if calendar_signal == CALENDAR_URL_SIGNAL_INVALID:
        _note_error(errors, "calendar_url", ERROR_CALENDAR_URL_INVALID)
        return FLASH_SAVE_FAILED
    # Phase 16 (16-05-PLAN.md, T-16-TAMPER's HTTP-layer half): same
    # membership-test shape as theme/theme_arriving above. A non-member
    # value is a hostile-request shape, not a genuine user mistake
    # (16-UI-SPEC.md Flash messages) — reuse the existing generic
    # save-failed flash, no new flash constant.
    if (
        submitted_calendar_theme_id is not None
        and submitted_calendar_theme_id not in device_config.THEME_IDS
    ):
        _note_error(errors, "calendar_theme_id", ERROR_INVALID_CHOICE)
        return FLASH_SAVE_FAILED
    if (
        submitted_theme_arriving is not None
        and submitted_theme_arriving not in device_config.THEME_IDS
    ):
        _note_error(errors, "theme_arriving", ERROR_INVALID_CHOICE)
        return FLASH_SAVE_FAILED
    if submitted_runway is not None and submitted_runway not in device_config.RUNWAY_IDS:
        _note_error(errors, "tracked_runway", ERROR_INVALID_CHOICE)
        return FLASH_SAVE_FAILED
    # 19-07-PLAN.md Task 1 (D-07): a PRESENT-but-invalid quiet-hours time
    # is a real user error, reported at that field rather than falling
    # through to the generic save-failed flash via
    # save_device_config()'s own exception path below. Field ABSENT
    # (`None`) still means "leave unchanged" — including the structural
    # absence a scoped page that never rendered this group produces — so
    # only a submitted-but-malformed value (the empty string counts as
    # submitted) is checked here.
    if submitted_qh_start is not None and not _QUIET_HOURS_TIME_RE.match(submitted_qh_start):
        _note_error(errors, "quiet_hours_start", ERROR_QUIET_HOURS_TIME_SHAPE)
        return FLASH_SAVE_FAILED
    if submitted_qh_end is not None and not _QUIET_HOURS_TIME_RE.match(submitted_qh_end):
        _note_error(errors, "quiet_hours_end", ERROR_QUIET_HOURS_TIME_SHAPE)
        return FLASH_SAVE_FAILED
    # Phase 15 D-05: keyed on the CHECKBOX field, never on
    # theme_arriving's presence. D-05 requires the second (arrivals) grid
    # to always be rendered for no-JS correctness, which means
    # theme_arriving is essentially ALWAYS present in a real browser
    # submission with a valid id — a branch keyed on that field's
    # presence would therefore never fire the clear path. The checkbox is
    # the only signal that distinguishes "set" from "clear". `None` is
    # not the clear value either: `None` already means "not supplied,
    # carry forward" for every parameter of this write path including
    # this one, so passing it here would make a partial-field save
    # silently wipe a previously-set override.
    if screens.GROUP_THEME not in in_scope:
        theme_arriving = None
    elif submitted_theme_arriving_enabled is None:
        theme_arriving = device_config.CLEAR_THEME_ARRIVING
    elif submitted_theme_arriving_enabled == ARRIVING_CHECKBOX_VALUE:
        theme_arriving = submitted_theme_arriving
    else:
        _note_error(errors, "theme_arriving_enabled", ERROR_UNEXPECTED_SWITCH_VALUE)
        return FLASH_SAVE_FAILED
    if screens.GROUP_LED not in in_scope:
        led_enabled = None
    elif submitted_led is None:
        led_enabled = False
    elif submitted_led == LED_CHECKBOX_VALUE:
        led_enabled = True
    else:
        _note_error(errors, "led_enabled", ERROR_UNEXPECTED_SWITCH_VALUE)
        return FLASH_SAVE_FAILED
    if screens.GROUP_QUIET_HOURS not in in_scope:
        quiet_hours_enabled = None
    elif submitted_qh_enabled is None:
        quiet_hours_enabled = False
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
        # 19-07-PLAN.md Task 1 (D-07): a syntactically valid but
        # out-of-range integer ("7") used to reach save_device_config()'s
        # own bounded-range ValueError and surface only as the generic
        # flash — reported at this field instead, before any write.
        if not (
            device_config.WAKE_INTERVAL_MIN_S
            <= wake_interval_s
            <= device_config.WAKE_INTERVAL_MAX_S
        ):
            _note_error(errors, "wake_interval_s", ERROR_WAKE_INTERVAL_RANGE)
            return FLASH_SAVE_FAILED
    if screens.GROUP_DISPLAY not in in_scope:
        display_enabled = None
    elif submitted_display is None:
        display_enabled = False
    elif submitted_display == DISPLAY_CHECKBOX_VALUE:
        display_enabled = True
    else:
        _note_error(errors, "display_enabled", ERROR_UNEXPECTED_SWITCH_VALUE)
        return FLASH_SAVE_FAILED

    try:
        device_config.save_device_config(
            state_dir, theme=submitted_theme, theme_arriving=theme_arriving,
            tracked_runway=submitted_runway,
            led_enabled=led_enabled, quiet_hours_enabled=quiet_hours_enabled,
            quiet_hours_start=submitted_qh_start, quiet_hours_end=submitted_qh_end,
            wake_interval_s=wake_interval_s, display_enabled=display_enabled,
            calendar_theme_id=submitted_calendar_theme_id,
            screen_id=submitted_screen_id)
    except (ValueError, OSError):
        return FLASH_SAVE_FAILED

    # Phase 17 plan 03 (D-01/D-02/D-04/D-05/D-07): the secret write is
    # layered AFTER the device-config write above, and only on the two
    # outcomes that actually touch the calendar URL. `carry_forward`
    # calls calendar_rules.save_calendar_url() not at all — every
    # successful call to it erases the fetched calendar registry, so
    # calling it on a save that never touched the calendar field would
    # silently wipe the calendar's flights on every unrelated settings
    # change (T-17-PRIV). This ordering leaves a narrow window in which
    # the device config has been written but this call then fails; the
    # operator sees the generic failure flash and can retry, which is
    # the cheaper trade against perturbing the ordering of every save in
    # this handler to close a window that only opens when the state
    # directory is already failing.
    if calendar_signal == CALENDAR_URL_SIGNAL_CLEAR:
        if not calendar_rules.save_calendar_url(
                state_dir, calendar_rules.CLEAR_CALENDAR_URL):
            return FLASH_SAVE_FAILED
    elif calendar_signal == CALENDAR_URL_SIGNAL_SET:
        if not calendar_rules.save_calendar_url(
                state_dir, submitted_calendar_url.strip()):
            return FLASH_SAVE_FAILED
    # calendar_signal == CALENDAR_URL_SIGNAL_CARRY_FORWARD: no call at
    # all (see docstring/comment above).

    return FLASH_SAVED
