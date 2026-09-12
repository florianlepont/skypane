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

from companion import i18n  # D-05, 20-07-PLAN.md Task 1: the Display page's
# three supersection headings/intros render through i18n.t() (Task 3
# widens this to every user-visible string in this file).
from companion import theme_preview
from companion.layout import escape_html
import companion.layout as layout
from companion import screens
from companion import wake
# 20-07-PLAN.md Task 3 (D-36): the former EDIT_QUERY_PARAM import (19-12-
# PLAN.md Task 2's Device-page "Edit artwork" link) is gone along with
# that link itself — 20-10 renders the replacement "Change pictures"
# button directly on airlines_page.py, which already owns
# EDIT_QUERY_PARAM; nothing here needs it any more.
#
# 20-09-PLAN.md Task 3 (D-15c): the former DELETE_BUTTON_TEXT import
# (airlines_page.py's "Delete") is gone too — the rebuilt rule row's own
# Remove button carries its own distinct copy (RULE_REMOVE_BUTTON_TEXT
# below), matching the UI-SPEC copy table's own "Remove"/"Retirer"
# wording rather than reusing the airlines gallery's "Delete".
#
# 20-09-PLAN.md Task 1 (D-15e): history_db.recent_runway_events() is the
# same call home_page._recent_flights() already makes (companion/pages/
# __init__.py forbids importing that page module directly, so this is a
# second, independent import of the same shared server-side helper, not
# a page-to-page import).
from server import device_config, history_db, panel_format
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

# 20-11-PLAN.md Task 2 (D-22..D-24, 20-UI-SPEC.md Section Anatomy H/copy
# table E): the live preview's own alt text and caption strings, and its
# `<img>` width/height — taken from the render pipeline's real served
# dimensions (theme_preview.THEME_PREVIEW_SIZE), never a CSS
# `aspect-ratio` guess (matching the chip grid's own UIR-07-informed
# discipline). The live preview shares the identical crop/size the chip
# grid's own `<img>` uses — only the rendered SCENE differs (the last
# real runway event instead of the fixed fixture).
THEME_LIVE_PREVIEW_WIDTH, THEME_LIVE_PREVIEW_HEIGHT = theme_preview.THEME_PREVIEW_SIZE
THEME_LIVE_PREVIEW_ALT_TEMPLATE = "Live preview of the %s theme"
THEME_LIVE_PREVIEW_CAPTION_WITH_FLIGHT_TEMPLATE = "Preview with your last flight: %s"
THEME_LIVE_PREVIEW_CAPTION_SAMPLE = "Preview with a sample flight"

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
# 20-07-PLAN.md Task 1 (D-12): the Display page now carries every
# everyday group (Look/What it watches/When it is on), so its purpose
# sentence widens from "how the frame looks" to the whole page's scope.
DISPLAY_PAGE_PURPOSE = "Everything about what the frame shows and when."
DEVICE_PAGE_TITLE = "Device"
DEVICE_PAGE_PURPOSE = (
    "Hardware, data and diagnostics for the frame. Nothing here needs "
    "changing day to day.")
SCREEN_CAPTION_TEMPLATE = "Screen: %s"

# 20-07-PLAN.md Task 1 (D-12, 20-UI-SPEC.md Section Anatomy C): the
# three headed supersections Display's own groups render under, in this
# locked order. Each heading/intro pair is rendered through the shared
# section-intro helper layout.py promoted from health_page.py's own
# former private copy (20-03-PLAN.md).
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
# 19-12-PLAN.md Task 2 (D-23): the conditional screen-type <select> — an
# element id (not a class) because its own <label> targets it via `for`.
SCREEN_SELECTOR_ID = "screen-id-selector"
SCREEN_SELECTOR_LABEL_TEXT = "Screen type"
# 20-07-PLAN.md Task 3 (D-36): the Device page's own artwork-editing
# link and its former builder function are deleted outright — the
# developer did not understand it. See airlines_page.py, where 20-10
# renders the replacement "Change pictures" button at the top of the
# gallery instead.


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
    # 20-11-PLAN.md Task 1 (D-26): screens.GROUP_NOTIFICATIONS joins this
    # legacy tuple too — every registered group must appear somewhere in
    # SCOPE_ALL's fixed order, since render()/handle_post()'s own tests
    # pin the invariant that the two live scopes' groups are disjoint and
    # their union equals this tuple's own set exactly.
    return (
        screens.GROUP_THEME, screens.GROUP_RUNWAY, screens.GROUP_LED,
        screens.GROUP_QUIET_HOURS, screens.GROUP_WAKE_INTERVAL,
        screens.GROUP_DISPLAY, screens.GROUP_CALENDAR,
        screens.GROUP_NOTIFICATIONS)


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
# 20-07-PLAN.md Task 3 (D-05): the %s-templated form, translated through
# i18n.t() BEFORE substitution (this codebase's established pattern,
# health_page.py's SOURCE_FAULT_BODY_TEMPLATE, 20-03-PLAN.md) — never an
# already-formatted string translated as one opaque catalogue key, which
# would bake this specific device's own configured times into the
# French entry forever.
QUIET_HOURS_PRESET_NIGHT_LABEL_TEMPLATE = "Night (%s–%s)"
QUIET_HOURS_PRESET_NIGHT_LABEL = QUIET_HOURS_PRESET_NIGHT_LABEL_TEMPLATE % (
    QUIET_HOURS_PRESET_NIGHT_START, QUIET_HOURS_PRESET_NIGHT_END)
QUIET_HOURS_PRESET_WORKDAY_START = "08:00"
QUIET_HOURS_PRESET_WORKDAY_END = "18:00"
QUIET_HOURS_PRESET_WORKDAY_LABEL_TEMPLATE = "Work day (%s–%s)"
QUIET_HOURS_PRESET_WORKDAY_LABEL = QUIET_HOURS_PRESET_WORKDAY_LABEL_TEMPLATE % (
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

# 20-11-PLAN.md Task 1 (D-26/D-28, 20-UI-SPEC.md Section Anatomy J/copy
# table G): the Notifications group's own copy — a Device-only sixth
# sibling of LED/Wake interval inside <form id="{SETTINGS_FORM_ID}">,
# built against led_group()'s exact fieldset-free idiom.
NOTIFICATIONS_SECTION_HEADING = "Notifications"
NOTIFICATIONS_SECTION_CAPTION = (
    "Get a push alert when the battery runs low or the frame stops "
    "checking in.")
NOTIFICATIONS_SECTION_CAPTION_ID = "notifications-caption"
# D-26 amended (20-CONTEXT.md's Resolutions): write-only, like the
# calendar feed URL — never rendered back, not partially masked. The
# status row reports only whether a URL is stored (T-20-12).
NOTIFICATIONS_STATUS_CONFIGURED_VERDICT = "Configured"
NOTIFICATIONS_STATUS_NOT_CONFIGURED_VERDICT = "Not configured"
NOTIFICATIONS_URL_FIELD_LABEL = "Push topic URL"
NOTIFICATIONS_URL_HINT = (
    "Paste your ntfy.sh topic URL (or a self-hosted one). Stored on "
    "the server and never shown back here — pasting a new one "
    "replaces the old.")
NOTIFICATIONS_URL_HINT_ID = "notifications-url-hint"
NOTIFICATIONS_REPLACE_URL_SUMMARY = "Replace the URL"
# A shape bound against an absurd paste, matching CALENDAR_URL_MAX_LEN's
# own established rationale exactly — the one arbiter of an acceptable
# topic URL stays server/notify.py's send-time _url_is_safe() gate, not
# a second definition here.
NOTIFICATIONS_URL_MAX_LEN = 2048
NOTIFICATIONS_BATTERY_LABEL = "Battery low"
NOTIFICATIONS_SILENT_LABEL = "Frame silent"
NOTIFICATIONS_TEST_BUTTON_TEXT = "Send a test"
# The sole accepted submitted value for each checkbox (D-01), mirroring
# LED_CHECKBOX_VALUE/QUIET_HOURS_CHECKBOX_VALUE/DISPLAY_CHECKBOX_VALUE's
# own rationale exactly: shared by notifications_group()'s markup and
# handle_post()'s validator so the two can never drift apart.
NOTIFICATIONS_BATTERY_CHECKBOX_VALUE = "on"
NOTIFICATIONS_SILENT_CHECKBOX_VALUE = "on"
# companion/app.py rebinds this rather than retyping the literal,
# mirroring CALENDAR_CONNECT_ROUTE's own rebinding convention (app.py
# imports this module, so the reverse import would be a cycle). Unlike
# the calendar Connect route, this one is a pure immediate action with
# no field of its own to validate — see _handle_notifications_test_
# post()'s own docstring in companion/app.py.
NOTIFICATIONS_TEST_ROUTE = "/settings/notifications/test"
ERROR_NOTIFICATIONS_URL_TOO_LONG = "That link is too long."

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

# 20-07-PLAN.md Task 2 (D-19): the Screen on/off and Quiet hours routes
# the strip's switches still post to. Home's own (module-private, on
# the Home page) route constants are byte-for-byte duplicates, never
# imported (a page module may never import another page module,
# companion/pages/__init__.py's own boundary). The instant-switch
# `<form>`s' own action attributes are written as literal path text,
# not a `%s` interpolation of these constants (this file's own
# acceptance gate greps the literal form-action text) — but the two
# constants stay defined here, equal to those same paths, for
# companion/test_config_page.py's own checks to reference without
# retyping either path a third time.
#
# 21-04-PLAN.md Task 1 (D-01/D-02/R-01): the eleven constants naming
# the switches' own labels/state text/button text, and the markup
# blocks that used to build each switch, both moved out of this
# module entirely — the shared strip helper in companion/layout.py is
# now their one write site, since the Screen/Quiet-hours instant switches render in the
# shared Frame strip at the top of Home and Display, not inside these
# two scheduled-controls cards any more.
QUICK_DISPLAY_ROUTE = "/quick/display"
QUICK_QUIET_HOURS_ROUTE = "/quick/quiet-hours"

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

# D-06 (20-11-PLAN.md Task 3): the five connector words
# companion/static/dirty-state.js's own updateBar() used to hardcode in
# English — now rendered, translated, as data-* attributes on the same
# `.dirty-bar` element that script already looks up
# (`document.querySelector("[data-dirty-bar]")`), the same shape
# freshness.js already uses for data-pause-text/data-resume-text. Each
# constant's own English value is also that script's documented
# fallback literal, so the two can never silently disagree about what
# "missing" degrades to.
DIRTY_CHANGED_SUFFIX = " changed"
DIRTY_AND = " and "
DIRTY_LIST_AND = ", and "
DIRTY_UNSAVED_SINGULAR = "1 unsaved change"
DIRTY_UNSAVED_PLURAL = " unsaved changes"

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

# 20-09-PLAN.md Task 3 (D-15a..e): renamed from "Per-flight colour
# rules" — heading and caption both through t() at the render site. The
# old precedence/replace-on-add sentence moves into a <details>
# disclosure (RULES_HOW_RULES_COMBINE_*, below). D-17 (21-01-PLAN.md
# Task 2): that disclosure no longer has a collapsed one-sentence
# variant — it always renders in full.
RULES_SECTION_HEADING = "Flight colours"
RULES_SECTION_CAPTION = "Give one flight, one aircraft or one airline its own theme."
RULES_HOW_RULES_COMBINE_SUMMARY = "How rules combine"
RULES_HOW_RULES_COMBINE_BODY = (
    "The most specific match wins — a flight rule beats an aircraft "
    "rule, which beats an airline rule — and adding a key that's "
    "already in use replaces the existing rule for it.")
# D-17 (21-01-PLAN.md Task 2): the one-sentence collapsed disclosure
# variant is deleted along with the display mode that selected it —
# the "How rules combine" <details> below always renders in full now.
# D-15b: the segmented "Match by" control's own visually-hidden group
# label — kept distinct from each segment's own visible text
# (RULE_KIND_LABELS) and technical title (RULE_KIND_TITLES) below.
RULE_KIND_FIELD_LABEL = "Match by"
RULE_VALUE_FIELD_LABEL = "Value"
RULE_ADD_BUTTON_TEXT = "Add rule"
# D-15b: the plain-language segment labels shown to everyone — used by
# BOTH the add form's segment text and the rule-row kind badge, so the
# two can never disagree (mirrors 15-UI-SPEC.md's own "never abbreviated
# differently in the list than in the form" rule, carried over verbatim
# for the new wording).
RULE_KIND_LABELS = {
    colour_rules.RULE_KIND_CALLSIGN: "Flight",
    colour_rules.RULE_KIND_HEX: "Aircraft",
    colour_rules.RULE_KIND_PREFIX: "Airline",
}
# D-15b: "the technical term kept as each option's title" — a SEPARATE
# mapping from RULE_KIND_LABELS above, read only for each segment's own
# `title` attribute, never shown as the visible label text. Phase 15's
# original wording, unchanged.
RULE_KIND_TITLES = {
    colour_rules.RULE_KIND_CALLSIGN: "Callsign",
    colour_rules.RULE_KIND_HEX: "ICAO24 hex",
    colour_rules.RULE_KIND_PREFIX: "Callsign prefix",
}
# D-15b: per-segment placeholders ("AFR1234"/"3944F2"/"AFR") are a
# progressive enhancement no script in this phase implements — this
# section ships no new client-side script at all (20-UI-SPEC.md
# Structural Note 5's native-radio resolution) — deliberately omitted,
# not forgotten. One static placeholder covers the always-valid default
# kind (callsign).
RULE_VALUE_PLACEHOLDER = "AFR1234"
RULES_EMPTY_HEADING = "No flight colours yet."
RULES_EMPTY_BODY = (
    "Add one above to give a flight, aircraft or airline its own theme.")
# D-15c: distinct from airlines_page.DELETE_BUTTON_TEXT ("Delete") —
# this list's own Remove button, per the UI-SPEC copy table's own
# wording, no longer the airlines gallery's "Delete".
RULE_REMOVE_BUTTON_TEXT = "Remove"
# D-15e: the suggestion chips' own label prefix — the joined callsign
# list itself is data, never translated (matches the flight one-liner
# separator's own "data, not translated" precedent, 20-UI-SPEC.md
# Copywriting Contract §A).
RULE_SUGGESTIONS_LABEL = "Recent:"
# aria-labelledby targets for the two radiogroups the add form carries —
# the segmented "Match by" control and the compact theme-chip grid.
RULE_KIND_HEADING_ID = "rule-kind-heading"
RULE_THEME_HEADING_ID = "rule-theme-heading"
# D-15c (LOCKED): the Remove form's own native-confirm question — kept
# despite 20-UI-SPEC.md's Destructive-confirmations table proposing to
# drop it as an immediately-reversible action (re-adding the same key
# restores it); D-15c's own locked text wins over that proposal. This is
# a one-line change (drop the data-confirm attribute below) if the
# developer later prefers the spec's reading.
RULE_REMOVE_CONFIRM_QUESTION = "Remove this rule?"

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
# 20-09-PLAN.md Task 1 (D-14d): the compact chip grid's own
# aria-labelledby target — the card's own <h2> already names the
# subject, so no second visually-hidden label is needed (20-UI-SPEC.md
# §E).
CALENDAR_HEADING_ID = "calendar-heading"
# D-14a: one plain sentence, no lecture — the two-sentence disclaimer
# and the "applies on the next poll" note move into the "How it works"
# disclosure below.
CALENDAR_CAPTION = "Flights from your calendar get their own colour on the frame."
CALENDAR_HOW_IT_WORKS_SUMMARY = "How it works"
CALENDAR_HOW_IT_WORKS_BODY = (
    "It can only colour a flight that happens to be on screen — it "
    "does not track or announce anything on its own. Applies on the "
    "frame's next scheduled poll, not immediately.")
# D-17 (21-01-PLAN.md Task 2): the one-sentence collapsed disclosure
# variant is deleted along with the display mode that selected it —
# the "How it works" <details> below always renders in full now.
# D-14b: the status-row verdict/detail pair replaces the old, one-piece
# CALENDAR_STATUS_* sentences this plan retires. "Not connected" covers
# both the never-configured and the permission-drifted states — a
# drifted stored link is not usably connected either (D-02).
CALENDAR_STATUS_CONNECTED_VERDICT = "Connected"
CALENDAR_STATUS_NOT_CONNECTED_VERDICT = "Not connected"
CALENDAR_STATUS_DETAIL_TEMPLATE = "%d upcoming flights · checked %s"
# D-14b/T-20-30: a fixed dict keyed on a category DERIVED from existing
# fields (last_attempt_at newer than any usable last_synced_at) — never
# the fetch's own caught exception text, which server/plane/
# calendar_rules.py does not persist anywhere this module could read it
# from in the first place.
CALENDAR_STATUS_FETCH_FAILED_DETAIL = "The feed could not be read"

# D-14c: the Connect/Replace mini-form's own copy — its own dedicated
# route (CALENDAR_CONNECT_ROUTE below) means this action never shares a
# flash key or a validation path with the settings Save button.
CALENDAR_CONNECT_BUTTON_TEXT = "Connect calendar"
CALENDAR_REPLACE_URL_SUMMARY = "Replace the feed URL"
# 20-09-PLAN.md Task 2 (D-14c): companion/app.py rebinds this rather
# than retyping the literal, mirroring CALENDAR_DISCONNECT_ROUTE's own
# rebinding convention immediately above (app.py imports this module,
# so the reverse import would be a cycle).
CALENDAR_CONNECT_ROUTE = "/settings/calendar/connect"

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
# 20-09-PLAN.md Task 2 (D-14c): the two outcomes only
# POST /settings/calendar/connect can produce — companion/app.py rebinds
# both, mirroring the four rebindings immediately above. The failure
# path reuses FLASH_CALENDAR_SYNC_FAILED itself rather than earning a
# third calendar failure message (this task's own explicit instruction:
# "the existing sync-failure flash key").
FLASH_CALENDAR_CONNECT_OK = "calendar_connect_ok"
FLASH_CALENDAR_CONNECT_INVALID = "calendar_connect_invalid"

# 20-11-PLAN.md Task 1 (D-26): the two outcomes POST /settings/
# notifications/test can produce — companion/app.py rebinds both,
# mirroring FLASH_CALENDAR_CONNECT_OK/_INVALID's own rebinding pattern
# immediately above.
FLASH_NOTIFICATIONS_TEST_OK = "notifications_test_ok"
FLASH_NOTIFICATIONS_TEST_FAILED = "notifications_test_failed"


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
    ) % (escape_html(control_id), escape_html(i18n.t(message)))


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

    20-07-PLAN.md Task 3 (D-05): `caption` is translated by the CALLER
    (every call site below passes `i18n.t(SOME_CAPTION_CONSTANT)`) — this
    function only translates its OWN suffix template, and does so BEFORE
    substituting `next_wake_clock` into it, matching this codebase's
    established "%-template translated first, formatted second" pattern
    (health_page.py's SOURCE_FAULT_BODY_TEMPLATE, 20-03-PLAN.md).
    """
    if not next_wake_clock:
        return caption
    return caption + (i18n.t(NEXT_WAKE_CAPTION_SUFFIX_TEMPLATE) % next_wake_clock)


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


def _theme_chip_grid_html(
        field_name, selected_theme_id, extra_class="", extra_attr="", chip_extra_class="",
        radio_form_id=None):
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

    20-09-PLAN.md Task 1/3 (D-14d/D-15b): `chip_extra_class` is a THIRD,
    independent seam — distinct from `extra_class` (the grid wrapper's
    own modifier) — applied to EVERY chip's own `<label>` class
    attribute. This is what actually shrinks each chip to the compact
    104px geometry (`companion/static/style.css`'s `.theme-chip--compact`
    rules key off the CHIP's own class, per 20-UI-SPEC.md §G's markup:
    "N .theme-chip.theme-chip--compact entries") — the grid-level
    `theme-chip-grid--compact` modifier alone has no chip-shrinking rule
    of its own and would silently do nothing without this.

    20-11-PLAN.md Task 2 (D-24): every chip's own `<label>` ALSO gains one
    new attribute naming the theme's own live-render path (the exact
    attribute name `companion/static/theme-preview.js`, 20-08, already
    reads off the changed radio input's parent `<label>`). Added
    additively, on every grid this function renders (the compact variant
    included, D-24's own "additive" instruction): the script's own guard
    clause returns early on any page with no `.theme-live-preview`, so a
    page that only has the compact grid (Calendar, the rules add-form)
    inherits the new attribute harmlessly. The chip's own `<img>` src is
    UNCHANGED — still the fixed, non-live preview, still lazily loaded —
    only the new attribute is added; the live theme preview's own image
    (a sibling element `theme_fieldset()` renders above the grid) is
    what that new attribute is ever read to update.

    D-12 fix (20-REVIEW.md verification gap): `radio_form_id`, when
    given, adds an explicit `form="{radio_form_id}"` attribute to every
    radio input this grid renders — the SAME `form=` idiom
    `runway_fieldset()`'s own radios and `display_group()`/
    `quiet_hours_group()`'s scheduled inputs already use (Polish fix 4,
    D-19/Pitfall 1), so this grid keeps posting through the physical
    settings form even when `render()` renders its enclosing card as a
    sibling of that form rather than a literal descendant. Defaults to
    `None` (no attribute at all, byte-identical to before this fix) —
    Theme's own two always-in-form grids and the rule-add-form's grid
    never pass it.
    """
    form_attr_html = ' form="%s"' % escape_html(radio_form_id) if radio_form_id else ""
    chips = []
    for theme_id in device_config.THEME_IDS:
        selected = theme_id == selected_theme_id
        checked = " checked" if selected else ""
        chip_class = "theme-chip"
        if selected:
            chip_class += " theme-chip--selected"
        if chip_extra_class:
            chip_class += " " + chip_extra_class
        theme = device_config.THEMES[theme_id]
        # Polish fix 5 (D-05): device_config.theme_label()'s registry
        # text ("White", "Band Blue Field", …) is translated at THIS
        # display site via i18n.t() — the ids themselves (theme_id)
        # never change, and server/device_config.py's own English
        # THEMES["label"] values stay untranslated at the source
        # (companion/i18n_fr/registry.py supplies the French entries).
        label = i18n.t(device_config.theme_label(theme_id))
        escaped_id = escape_html(theme_id)
        departing_hex = _palette_hex(theme["departing_index"])
        arriving_hex = _palette_hex(theme["arriving_index"])
        chips.append(
            '<label class="%s" data-preview-src="%s%s.png?live=1">'
            '<input type="radio" name="%s" value="%s" class="visually-hidden"%s%s>'
            '<img class="theme-chip__preview" src="%s%s.png" alt="%s" '
            'width="320" height="120" loading="lazy" style="background:%s">'
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
                chip_class, THEME_PREVIEW_ROUTE_PREFIX, escaped_id,
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
    return '<div class="%s"%s>%s</div>' % (grid_class, attr_html, "".join(chips))


def _theme_live_preview_html(current_theme_id, state_dir):
    """The `<figure class="theme-live-preview">` `theme_fieldset()`
    renders directly above the chip grid (D-22..D-24, 20-11-PLAN.md
    Task 2, 20-UI-SPEC.md Section Anatomy H/copy table E).

    The `<img src>` is `{THEME_PREVIEW_ROUTE_PREFIX}{theme_id}.png?live=1`
    for the SAVED theme (`current_theme_id`, membership-tested against
    `device_config.THEMES` before ever reaching a path component —
    T-20-14, the same discipline `theme_fieldset()`'s own single-theme
    branch already applies), eagerly loaded (the one eagerly-loaded
    image on this page — every chip's own preview stays lazily loaded)
    and explicit `width`/`height` from the render pipeline's real
    served dimensions (`theme_preview.THEME_PREVIEW_SIZE`), never a
    CSS `aspect-ratio` guess. Without JavaScript this `<img>` never
    changes — `companion/static/theme-preview.js` (20-08) is what swaps
    it on chip selection; the server-rendered `src` here IS D-24's
    documented no-JS floor.

    The caption reads the most recent runway event's callsign through
    the SAME connection helper `_rule_suggestion_chips_html()` already
    uses (`history_db.open_db()`/`recent_runway_events(limit=1)`) —
    never a second, independently-opened connection this page does not
    already make — degrading to the sample-flight wording on absolutely
    any exception (a missing/locked history.db, no rows at all), never
    raising and never a 500. This read never affects the `<img>` itself:
    the `?live=1` route resolves the event server-side on its own, so a
    failed read here only changes which caption sentence renders.
    `state_dir` may be falsy (matching every other optional-state_dir
    call site in this file, e.g. `runway_fieldset()`'s own `ctx.get(
    "runway_images")` pattern) — this degrades to the sample caption
    exactly like a genuine read failure would.
    """
    live_theme_id = (
        current_theme_id if current_theme_id in device_config.THEMES
        else device_config.DEFAULT_THEME_ID)
    # Polish fix 5 (D-05): translated at this display site, same as
    # _theme_chip_grid_html()'s own label above.
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
    return (
        '<figure class="theme-live-preview">'
        '<img class="theme-live-preview__image" src="%s%s.png?live=1" '
        'width="%d" height="%d" loading="eager" alt="%s">'
        '<figcaption class="text-label">%s</figcaption>'
        "</figure>"
    ) % (
        THEME_PREVIEW_ROUTE_PREFIX, escape_html(live_theme_id),
        THEME_LIVE_PREVIEW_WIDTH, THEME_LIVE_PREVIEW_HEIGHT,
        escape_html(i18n.t(THEME_LIVE_PREVIEW_ALT_TEMPLATE) % label),
        escape_html(caption_text),
    )


def theme_fieldset(
        current_theme_id, current_theme_arriving=None, errors=None, submitted=None,
        next_wake_clock=None, state_dir=None):
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

    20-11-PLAN.md Task 2 (D-22..D-24, 20-UI-SPEC.md Section Anatomy H/
    copy table E): the multi-theme branch gains a `<figure class=
    "theme-live-preview">` directly above the chip grid — `_theme_live_
    preview_html()` below builds it from `current_theme_id` (the SAVED
    value, never `effective_theme_id`'s own submitted/pending value:
    D-24's own no-JS floor is "the preview shows the saved theme",
    which must hold even while a rejected save is being redisplayed
    with the chip grid's own selection repopulated from the submission)
    and `state_dir` (new, optional, defaulting to `None` so every
    pre-Task-2 call site keeps rendering byte-identical output — the
    single-theme read-only branch above never had a chip grid to sit a
    preview above, and gains none here either). The chip grid itself
    (`first_grid` below) is UNCHANGED beyond the new live-render-path
    attribute each chip's own `<label>` gains
    (`_theme_chip_grid_html()`'s own Task 2 docstring paragraph) — the
    18 thumbnails still render the fixed fictional scene, still
    comparable side by side.
    """
    caption_html = (
        '<p class="text-label section-caption" id="%s">%s</p>'
        % (
            escape_html(THEME_SECTION_CAPTION_ID),
            escape_html(_with_next_wake(i18n.t(THEME_SECTION_CAPTION), next_wake_clock)),
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
            '<h2 class="text-heading">%s</h2>'
            "%s"
            '<div class="theme-status__row">'
            '<span class="theme-swatch" aria-hidden="true">'
            '<span class="theme-swatch__chip" style="background:%s"></span>'
            '<span class="theme-swatch__chip" style="background:%s"></span>'
            "</span>"
            '<span class="text-body">%s · %s</span>'
            "</div>"
            "</div>"
        ) % (
            DIRTY_SECTION_ATTR, escape_html(i18n.t("Theme")),
            escape_html(i18n.t("Theme")),
            caption_html,
            departing_hex, arriving_hex,
            # Polish fix 5 (D-05): translated at this display site — see
            # _theme_chip_grid_html()'s own comment for why the id
            # (theme_id) itself never changes.
            escape_html(i18n.t(device_config.theme_label(theme_id))),
            escape_html(i18n.t("current")),
        )

    live_preview_html = _theme_live_preview_html(current_theme_id, state_dir)
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
        '<h2 class="text-heading" id="%s">%s</h2>'
        "%s"
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
        DIRTY_SECTION_ATTR, escape_html(i18n.t("Theme")),
        escape_html(THEME_GROUP_HEADING_ID),
        escape_html(i18n.t("Theme")),
        caption_html,
        live_preview_html,
        first_grid, theme_error_html,
        escape_html(THEME_ARRIVING_TOGGLE_ID),
        escape_html(ARRIVING_CHECKBOX_VALUE),
        " checked" if checkbox_checked else "",
        theme_arriving_enabled_attrs,
        escape_html(i18n.t(THEME_ARRIVING_CHECKBOX_LABEL)),
        theme_arriving_enabled_error_html,
        escape_html(THEME_ARRIVING_GROUP_HEADING_ID),
        escape_html(i18n.t(THEME_DIRECTION_LABEL)),
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

    Polish fix 4 (D-14c): each radio now also carries an explicit
    `form="{SETTINGS_FORM_ID}"` attribute — the SAME `form=` idiom
    `display_group()`/`quiet_hours_group()` already use for their own
    scheduled inputs (D-19/Pitfall 1). On the legacy SCOPE_ALL render
    (where this group is still a literal descendant of
    `<form id="{SETTINGS_FORM_ID}">`), the attribute is a harmless
    no-op — the browser's explicit `form=` association resolves to the
    exact enclosing form either way. On the Display scope, `render()`'s
    `_display_groups_html()` now renders this group as a SIBLING of
    `<form id="{SETTINGS_FORM_ID}">` (never nested inside it), which is
    what lets `calendar_connect_section()`'s own separate `<form>` sit
    between the Calendar card and this group in document order without
    ever nesting one `<form>` inside another.
    """
    effective_runway_id = _submitted_or_current(
        submitted, "tracked_runway", current_runway_id)
    cards = []
    for runway_id in device_config.RUNWAY_IDS:
        selected = runway_id == effective_runway_id
        checked = " checked" if selected else ""
        card_class = (
            "runway-card runway-card--selected" if selected else "runway-card")
        # Polish fix 5 (D-05): device_config.runway_label()'s registry
        # text ("Runway 3 (07/25)", …) is translated at this display
        # site via i18n.t() — the id (runway_id) itself never changes;
        # companion/i18n_fr/registry.py supplies the French entries.
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
            '<label class="%s">'
            '<input type="radio" name="tracked_runway" value="%s" class="visually-hidden" '
            'form="%s"%s>'
            '<span class="runway-card__number">%s</span>'
            "%s"
            '<span class="runway-card__check">%s<span class="visually-hidden">%s</span></span>'
            "</label>"
            % (
                card_class, escaped_id, SETTINGS_FORM_ID, checked, escape_html(label),
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
        '<input type="checkbox" name="led_enabled" value="%s"%s%s> %s'
        "</label>"
        "%s"
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(i18n.t(LED_SECTION_HEADING)),
        escape_html(i18n.t(LED_SECTION_HEADING)),
        escape_html(LED_SECTION_CAPTION_ID),
        escape_html(_with_next_wake(i18n.t(LED_SECTION_CAPTION), next_wake_clock)),
        escape_html(LED_CHECKBOX_VALUE), " checked" if checked else "", error_attrs,
        escape_html(i18n.t("Enable diagnostic LED")),
        error_html,
    )


def quiet_hours_group(
        current_enabled, current_start, current_end, errors=None, submitted=None,
        next_wake_clock=None):
    """The Quiet hours settings group (10-05-PLAN.md, 10-UI-SPEC.md;
    restructured by 20-07-PLAN.md Task 2, D-19/Pitfall 1): this card is
    now a SIBLING of `<form id="{SETTINGS_FORM_ID}">`, never a literal
    descendant — see `display_group()`'s own Task 2 docstring paragraph
    for the full reasoning (its own instant switch would otherwise be a
    `<form>` nested inside `<form id="{SETTINGS_FORM_ID}">`, which HTML
    forbids). The enable checkbox and both time inputs keep submitting
    with the shared Save via a `form="{SETTINGS_FORM_ID}"` attribute on
    each, the same cross-DOM idiom `display_group()` now uses too.

    Same `.theme-status` wrapper idiom, same `<h2 class="text-heading">`
    naming as before this task (no `<fieldset>`/`<legend>`, for the
    identical reason `led_group()`'s own docstring already documents: a
    `<legend>` only has accessible-name semantics inside a `<fieldset>`,
    which these sibling groups deliberately do not have) — only the
    card's DOM position and the three controls' `form=` attribute
    change.

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
        escape_html(
            i18n.t(QUIET_HOURS_PRESET_NIGHT_LABEL_TEMPLATE)
            % (QUIET_HOURS_PRESET_NIGHT_START, QUIET_HOURS_PRESET_NIGHT_END)),
        QUIET_HOURS_PRESET_ATTR,
        escape_html(QUIET_HOURS_PRESET_WORKDAY_START), escape_html(QUIET_HOURS_PRESET_WORKDAY_END),
        escape_html(
            i18n.t(QUIET_HOURS_PRESET_WORKDAY_LABEL_TEMPLATE)
            % (QUIET_HOURS_PRESET_WORKDAY_START, QUIET_HOURS_PRESET_WORKDAY_END)),
        QUIET_HOURS_PRESET_ATTR,
        escape_html(i18n.t(QUIET_HOURS_PRESET_ALWAYS_ON_LABEL)),
    )

    # 21-04-PLAN.md Task 1 (D-01/D-02): the instant switch that used to
    # render here, above a hairline and the shared "applies on next
    # wake" sentence, is gone — it now renders once, in the shared
    # Frame strip at the top of Home and Display (the shared strip
    # helper in companion/layout.py), never a second time in this
    # card. Everything below (the scheduled checkbox, the presets, both time
    # inputs, the Save button) is unchanged.
    return (
        '<div class="theme-status" %s="%s">'
        '<h2 class="text-heading">%s</h2>'
        '<p class="text-label section-caption" id="%s">%s</p>'
        '<label class="settings-checkbox">'
        '<input type="checkbox" name="quiet_hours_enabled" value="%s"%s form="%s"%s> %s'
        "</label>"
        "%s"
        "%s"
        '<label>%s <input type="time" name="quiet_hours_start" value="%s" required form="%s"%s></label>'
        "%s"
        '<label>%s <input type="time" name="quiet_hours_end" value="%s" required form="%s"%s></label>'
        "%s"
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(i18n.t(QUIET_HOURS_SECTION_HEADING)),
        escape_html(i18n.t(QUIET_HOURS_SECTION_HEADING)),
        escape_html(QUIET_HOURS_SECTION_CAPTION_ID),
        escape_html(_with_next_wake(i18n.t(QUIET_HOURS_SECTION_CAPTION), next_wake_clock)),
        escape_html(QUIET_HOURS_CHECKBOX_VALUE), " checked" if checked else "", SETTINGS_FORM_ID,
        enabled_error_attrs,
        escape_html(i18n.t("Enable quiet hours")),
        enabled_error_html,
        preset_row_html,
        escape_html(i18n.t("Start")),
        escape_html(effective_start), SETTINGS_FORM_ID, start_error_attrs,
        start_error_html,
        escape_html(i18n.t("End")),
        escape_html(effective_end), SETTINGS_FORM_ID, end_error_attrs,
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
    return (
        '<div class="theme-status" %s="%s">'
        '<h2 class="text-heading">%s</h2>'
        '<p class="text-label section-caption" id="%s">%s</p>'
        "<label>%s "
        '<input type="number" name="wake_interval_s" min="%d" max="%d"'
        ' placeholder="%s"%s%s></label>'
        "%s"
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(i18n.t(WAKE_INTERVAL_SECTION_HEADING)),
        escape_html(i18n.t(WAKE_INTERVAL_SECTION_HEADING)),
        escape_html(WAKE_INTERVAL_SECTION_CAPTION_ID),
        escape_html(_with_next_wake(i18n.t(WAKE_INTERVAL_SECTION_CAPTION), next_wake_clock)),
        escape_html(i18n.t("Wake interval (seconds)")),
        device_config.WAKE_INTERVAL_MIN_S, device_config.WAKE_INTERVAL_MAX_S,
        escape_html(i18n.t(WAKE_INTERVAL_PLACEHOLDER_TEXT)),
        value_attr, error_attrs,
        error_html,
    )


def notifications_group(
        configured, current_battery_low, current_frame_silent,
        errors=None, submitted=None):
    """The Notifications settings group (D-26/D-28, 20-11-PLAN.md Task 1,
    20-UI-SPEC.md Section Anatomy J/copy table G): a sixth sibling of
    the LED/Wake interval groups inside `<form id="{SETTINGS_FORM_ID}">`,
    Device-only (`screens.GROUP_NOTIFICATIONS` is never a member of
    Display's `everyday_groups` or the legacy SCOPE_ALL tuple) — built
    against `led_group()`'s exact `.theme-status`/`<h2 class=
    "text-heading">` fieldset-free idiom.

    **Write-only URL, matching `calendar_connect_section()`'s established
    contract (T-20-12)**: `configured` is a bare bool — never the URL
    itself, never a masked fragment of it. `layout.status_row("",
    verdict, "", state)` reports only whether a topic URL is stored; the
    text input always renders with NO `value` attribute and nothing
    derived from the stored URL, in both states. Wrapped in
    `<details><summary>Replace the URL</summary>` while `configured` is
    true, unwrapped otherwise — the identical disclosure shape
    `calendar_connect_section()` already uses for the identical reason.

    Unlike `calendar_connect_section()`, this field is NOT a dedicated
    route: it is a plain member of the tracked settings form, waiting on
    the page-wide Save exactly like every other Device field (the
    plan's own explicit instruction — "All three controls are part of
    #settings-form and wait on Save"). Only the "Send a test" button
    (`notifications_test_section()` below) is its own immediate-POST
    form, a sibling of `#settings-form` — mirroring the Calendar Connect
    form's/the rules add-form's own reasoning for that identical shape:
    an immediate action must never wait on, or nest inside, the
    page-wide Save form (D-19/Pitfall 1).

    19-07-PLAN.md Task 2 (D-07): `errors`/`submitted` (both fully
    defaulted) let a rejected save repopulate both checkboxes from the
    submission and render each field's own error message — the topic
    URL has no repopulation (nothing to repopulate; a write-only field),
    matching `calendar_connect_section()`'s identical omission.
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
    field_html = (
        '<div class="rule-add-form__field">'
        '<label for="notifications-topic-url">%s</label>'
        '<input type="text" id="notifications-topic-url" '
        'name="notifications_topic_url" autocomplete="off" '
        'spellcheck="false" maxlength="%s"%s>'
        '<p class="text-label section-caption" id="%s">%s</p>'
        "%s"
        "</div>"
    ) % (
        escape_html(i18n.t(NOTIFICATIONS_URL_FIELD_LABEL)),
        NOTIFICATIONS_URL_MAX_LEN, url_error_attrs,
        escape_html(NOTIFICATIONS_URL_HINT_ID), escape_html(i18n.t(NOTIFICATIONS_URL_HINT)),
        url_error_html,
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
    )


def notifications_test_section():
    """The "Send a test" button (D-26, 20-11-PLAN.md Task 1): its own
    small `<form method="post" action="{NOTIFICATIONS_TEST_ROUTE}">`, a
    sibling of `<form id="{SETTINGS_FORM_ID}">` — mirroring
    `calendar_connect_section()`'s/the rules add-form's own reasoning
    for the identical shape (D-19/Pitfall 1: an immediate action's own
    `<form>` must never nest inside the settings form). `render()`
    renders this immediately after `</form>` closes, on the Device
    scope only (`screens.GROUP_NOTIFICATIONS` is never a member of
    `scope_groups(SCOPE_DISPLAY)` or the legacy SCOPE_ALL tuple, so this
    section is correctly omitted from both).

    The action attribute below is written as literal path text, not a
    `%s` interpolation of `NOTIFICATIONS_TEST_ROUTE` — matching
    `calendar_connect_section()`'s own established convention for the
    identical class of grep (this module's acceptance gate greps the
    literal form-action text).

    Carries no `data-confirm`: sending a test push is neither
    destructive nor state-changing on this side — the handler
    (`companion/app.py`'s `_handle_notifications_test_post()`) reads the
    stored URL from disk and never trusts the request body (T-20-13),
    which is the real mitigation, not a confirmation dialog.
    """
    return (
        '<form method="post" action="/settings/notifications/test" '
        'class="notifications-test-form">'
        '<button type="submit">%s</button>'
        "</form>"
    ) % escape_html(i18n.t(NOTIFICATIONS_TEST_BUTTON_TEXT))


def display_group(current_display_enabled, errors=None, submitted=None):
    """The Display settings group (12-UI-SPEC.md, 12-CONTEXT.md D-08/D-09;
    restructured by 20-07-PLAN.md Task 2, D-19/Pitfall 1): this card is
    now a SIBLING of `<form id="{SETTINGS_FORM_ID}">`, never a literal
    descendant — `render()` no longer folds this builder's output into
    `groups_html`, and calls it separately, emitting it after `</form>`
    closes (the same slot `calendar_disconnect_section()` already
    occupies). This is the required structural fix for the instant
    switch below: its own `<form method="post" action="{QUICK_DISPLAY_
    ROUTE}">` would otherwise nest inside `<form id="{SETTINGS_FORM_ID}">`,
    which HTML forbids. The `display_enabled` checkbox keeps submitting
    with the shared Save via a `form="{SETTINGS_FORM_ID}"` attribute
    instead — the exact cross-DOM submission idiom already shipped for
    the dirty-bar's Save button and the screen-type `<select>` in this
    same file.

    Same `.theme-status` wrapper idiom, same `<h2 class="text-heading">`
    naming as before this task (no `<fieldset>`/`<legend>`, for the
    identical reason `led_group()`'s own docstring already documents) —
    only the card's DOM position and the checkbox's `form=` attribute
    change; its own `name`/`value`/`checked` sequence, and every
    surrounding paragraph/label, are unchanged from before this task.

    `DISPLAY_SECTION_CAPTION` states the ~5-minute apply latency in both
    directions (D-02) rather than the generic next-scheduled-poll clause
    every sibling caption ends on, because this is the one field on the
    page whose apply-timing is genuinely different — see the constant's
    own comment above for why.

    21-04-PLAN.md Task 1 (D-01/D-02): the instant-switch slot that used
    to render here, above a hairline and the shared "Applies the next
    time the frame wakes up." sentence, at the top of this card, is
    gone — it now renders once, in the shared Frame strip at the top
    of Home and Display (the shared strip helper in companion/
    layout.py), never a second time in this card. Everything below
    (the scheduled checkbox, the
    Save button) is unchanged.

    Every interpolated current value — the heading, the caption, and
    the checkbox value — is routed through `escape_html()`, matching
    this file's universal escaping discipline.

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
        '<input type="checkbox" name="display_enabled" value="%s"%s form="%s"%s> %s'
        "</label>"
        "%s"
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(i18n.t(DISPLAY_SECTION_HEADING)),
        escape_html(i18n.t(DISPLAY_SECTION_HEADING)),
        escape_html(DISPLAY_SECTION_CAPTION_ID), escape_html(i18n.t(DISPLAY_SECTION_CAPTION)),
        escape_html(DISPLAY_CHECKBOX_VALUE), " checked" if checked else "", SETTINGS_FORM_ID,
        error_attrs,
        escape_html(i18n.t("Enable display")),
        error_html,
    )


def calendar_group(
        configured, drift, last_synced_at, last_attempt_at, now, entry_count,
        current_calendar_theme_id, current_theme_id,
        errors=None, submitted=None):
    """The Calendar card (20-09-PLAN.md Task 1, 20-UI-SPEC.md Section
    Anatomy E; D-14a..d): in the "Look" supersection, after Theme and
    Flight colours (D-12 fix, 20-REVIEW.md verification gap — see
    `render()`'s own docstring for the exact document-order change).
    It nests no form of its own: the feed-URL field and its
    Connect/Replace button moved to their own dedicated route
    (`calendar_connect_section()` below, D-14c) — a status row, one
    compact chip-grid radio group and a `<details>` disclosure, nothing
    else.

    D-12 fix: this card is now rendered by `render()` as a SIBLING of
    `<form id="settings-form">`, not a literal descendant — the
    physical form now closes right after the Theme card, before this
    card, so Flight colours' own real `<form>` elements can sit between
    them without ever nesting a `<form>` inside another. The compact
    chip-grid radio group below still IS a saved setting, so it keeps
    posting through the physical form via the `form="settings-form"`
    attribute `_theme_chip_grid_html(radio_form_id=...)` now adds to
    every one of its radios — the same idiom `runway_fieldset()`'s own
    radios and `display_group()`/`quiet_hours_group()`'s scheduled
    inputs already use.

    **D-14b — the status row.** `layout.status_row("", verdict, detail,
    state)`: label is `""` because the card's own `<h2>Calendar</h2>`
    already names the subject (a repeated "CALENDAR" label would be
    redundant chrome). Four branches, `drift` first — a permission-
    drifted stored link (D-02) wins over everything else, because
    `configured` is already `False` in that state (D-08 —
    `calendar_is_configured()`'s own bool contract) and a later check
    would therefore never see the drift branch at all, making it
    indistinguishable from a calendar that was never connected. Then not
    configured. Then configured: "usable" (a parseable, age-computable
    `last_synced_at`) renders the entry count plus the language-aware
    relative age (D-07, `layout.relative_age_text()`) as the detail, with
    a genuinely fresh verdict word ("Connected") — never the same
    sentence twice (this primitive's own documented anti-duplication
    contract, D-21). Configured but never usable branches on whether an
    attempt has ever been recorded (`last_attempt_at is not None`): at
    least one attempt with no usable sync yet is the ONE derivable
    failed-fetch category this module has fields for (T-20-30) — the
    fixed, mapped `CALENDAR_STATUS_FETCH_FAILED_DETAIL` sentence, never
    a caught exception's own text (which `server/plane/calendar_rules.py`
    does not persist anywhere this function could read it from). No
    attempt recorded yet is the ordinary "just connected" wait state.

    **D-14d — the compact chip grid.** `_theme_chip_grid_html(
    "calendar_theme_id", ..., extra_class="theme-chip-grid--compact")` —
    the third consumer of that existing builder (after Theme's own two
    grids) — replaces the retired native drop-down field outright (its
    own name, "calendar_theme_id", is unchanged); `role="radiogroup"` +
    `aria-labelledby` points at this
    card's own `<h2 id="{CALENDAR_HEADING_ID}">` rather than minting a
    second, redundant visually-hidden label. Each radio also carries an
    explicit `form="settings-form"` attribute (D-12 fix above) because
    it IS a saved setting, unlike the feed URL — it must keep posting
    through the physical form even though this card itself now renders
    as a sibling of that form, not a literal descendant.

    **D-14a — the "How it works" disclosure.** D-17 (21-01-PLAN.md
    Task 2): the collapsed one-sentence variant this used to render
    under the now-deleted display mode is gone — the full `<details>`
    always renders.

    19-07-PLAN.md Task 2 (D-07/T-19-12) precedent, carried forward:
    `errors`/`submitted` (both fully defaulted) let a rejected save
    repopulate `calendar_theme_id`'s chip-grid selection from the
    submission and render its error message.
    """
    # Drift first (D-02): a drifted file makes `configured` already
    # False (D-08), so checking `not configured` before `drift` would
    # make the drift state unreachable and indistinguishable from a
    # calendar that was never connected.
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

    selected_calendar_theme_id = _submitted_or_current(
        submitted, "calendar_theme_id",
        current_calendar_theme_id if current_calendar_theme_id is not None
        else current_theme_id)
    calendar_theme_error_html = _field_error_html(
        errors, "calendar_theme_id", "calendar-theme")
    chip_grid_html = _theme_chip_grid_html(
        "calendar_theme_id", selected_calendar_theme_id,
        extra_class="theme-chip-grid--compact", chip_extra_class="theme-chip--compact",
        extra_attr='role="radiogroup" aria-labelledby="%s"' % escape_html(CALENDAR_HEADING_ID),
        # D-12 fix (20-REVIEW.md verification gap): this card now
        # renders as a sibling of <form id="settings-form"> on the
        # Display scope (see render()'s own docstring) - the same
        # form= idiom runway_fieldset()'s radios already use keeps
        # this saved setting posting through the physical form.
        radio_form_id=SETTINGS_FORM_ID)

    how_it_works_html = (
        '<details><summary>%s</summary><p class="text-body">%s</p></details>'
    ) % (
        escape_html(i18n.t(CALENDAR_HOW_IT_WORKS_SUMMARY)),
        escape_html(i18n.t(CALENDAR_HOW_IT_WORKS_BODY)),
    )

    return (
        '<div class="page-section" %s="%s">'
        '<h2 class="text-heading" id="%s">%s</h2>'
        '<p class="text-label section-caption">%s</p>'
        "%s"
        "%s"
        "%s"
        "%s"
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(i18n.t(CALENDAR_SECTION_HEADING)),
        escape_html(CALENDAR_HEADING_ID), escape_html(i18n.t(CALENDAR_SECTION_HEADING)),
        escape_html(i18n.t(CALENDAR_CAPTION)),
        status_html,
        chip_grid_html,
        calendar_theme_error_html,
        how_it_works_html,
    )


def calendar_connect_section(configured, errors=None):
    """The feed-URL field and the "Connect calendar" button (20-09-
    PLAN.md Task 1/2, D-14c): its OWN small `<form method="post"
    action="{CALENDAR_CONNECT_ROUTE}">`, a sibling of `<form
    id="settings-form">`, rendered by `render()` immediately before
    `calendar_disconnect_section()`'s own output — never a descendant of
    the settings form (posting a URL through the scoped settings handler
    would read every absent checkbox on Display as an explicit OFF and
    silently switch off Quiet hours and the screen, T-20-11) and never
    behind the page-wide Save.

    Wrapped in `<details><summary>Replace the feed URL</summary>` while
    `configured` is true; rendered unwrapped otherwise — matching D-14c's
    own text exactly ("While connected, the URL input is hidden behind a
    'Replace the feed URL' disclosure").

    The write-only contract is preserved verbatim from the retired
    in-form field this replaces: the input always renders with no
    `value` attribute, no populated placeholder, and nothing derived
    from the stored URL, in both the connected and not-connected states
    (T-16-SECRET/T-17-SECRET/T-20-12) — `errors` (fully defaulted,
    matching this file's D-07 idiom for a field-level message) lets a
    rejected connect attempt render the field's own error message; there
    is no `submitted` parameter here at all, unlike this file's other
    D-07 call sites, because there is nothing to repopulate — the one
    field this form carries is the write-only URL itself.

    Wrapped in its own `.page-section` — a genuinely small, distinct
    card, not a bare form — so this card's own bottom edge becomes the
    `:has(+ .calendar-disconnect-form)` fused-card target
    (companion/static/style.css, 20-04-PLAN.md) when `calendar_disconnect
    _section()`'s output immediately follows it in the DOM, giving the
    two forms one continuous, visually-joined unit.
    """
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
    # The action attribute below is written as literal path text, not a
    # %s interpolation of CALENDAR_CONNECT_ROUTE — matching this file's
    # own established convention for the instant-switch forms' own
    # action attributes (see QUICK_DISPLAY_ROUTE's comment above): this
    # module's acceptance gate greps the literal form-action text, and
    # the constant itself stays defined for companion/app.py's
    # rebinding and companion/test_config_page.py's own checks to
    # reference without retyping the path a third time.
    form_html = (
        '<form method="post" action="/settings/calendar/connect" class="rule-add-form">'
        "%s"
        '<button type="submit">%s</button>'
        "</form>"
    ) % (
        field_html,
        escape_html(i18n.t(CALENDAR_CONNECT_BUTTON_TEXT)),
    )
    if configured:
        inner_html = (
            '<details class="calendar-url-disclosure"><summary>%s</summary>%s</details>'
        ) % (escape_html(i18n.t(CALENDAR_REPLACE_URL_SUMMARY)), form_html)
    else:
        inner_html = form_html
    return '<div class="page-section">%s</div>' % inner_html


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
        escape_html(i18n.t(CALENDAR_DISCONNECT_CONFIRM_QUESTION)),
        escape_html(CALENDAR_DISCONNECT_CONFIRM_VALUE),
        CALENDAR_DISCONNECT_CONFIRM_FIELD,
        escape_html(i18n.t(CALENDAR_DISCONNECT_CHECKBOX_LABEL)),
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
    cancel path is a plain link back to the Display page (20-07-PLAN.md
    Task 1, D-11: Calendar moved from Device to Display this phase, so
    this is the page the disconnect action itself now lives on), never a
    second form (nothing to submit, nothing to confirm). Every dynamic
    value passes through `escape_html()`, matching this file's universal
    escaping discipline; `ctx` is accepted (unused today) for the same
    reason `render()`'s own scoped builders all take it — so a future
    reader adding a ctx-derived detail here never has to widen this
    function's own signature to do it.
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


def _rule_kind_radio_html(kind, checked):
    """One native radio + `<label>` pair for the "Match by" segmented
    control (D-15b, 20-UI-SPEC.md Structural Note 5's own resolution:
    native radios styled as the existing `.theme-form`/`.theme-option`
    segmented control, chosen over three JS-driven `<button>`s — zero
    degraded state, which is why this section ships no new client-side
    script at all). The radio is visually hidden
    (`companion/static/style.css`'s
    `.theme-form input[type="radio"] + label` rule styles the adjacent
    `<label>` at the segmented control's own geometry); the plain-
    language word (`RULE_KIND_LABELS`) is the visible label text, and
    the technical term (`RULE_KIND_TITLES`) is the label's own `title`
    attribute — a sighted mouse user who hovers still finds the exact
    vocabulary phase 15 shipped, never conflated with the visible label.
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
    """The one-line add form (D-15b, 20-UI-SPEC.md Section Anatomy F):
    a `role="radiogroup"` of three NATIVE radio inputs styled as the
    segmented control (`_rule_kind_radio_html()` above — the THIRD
    consumer of `.theme-form`/`.theme-option`, after the UI-theme picker
    and this same phase's language switch), a value input, the compact
    theme-chip grid (`_theme_chip_grid_html()`'s `extra_class=
    "theme-chip-grid--compact"` — the SECOND consumer of that modifier,
    after Calendar's own grid) and an "Add rule" button — one `<form
    method="post">` targeting `RULES_ADD_ROUTE`, styled to read as one
    line via `.rule-add-form--inline` rather than `_rule_add_form_html()`'s
    old column-stack `.rule-add-form`.

    Per-segment placeholders ("AFR1234"/"3944F2"/"AFR") are a
    progressive enhancement this phase does not ship (D-15b) — naming
    the omission here so it stays greppable and deliberate rather than
    forgotten: no script exists to swap the placeholder on selection, so
    one static placeholder (`RULE_VALUE_PLACEHOLDER`) covers the
    always-valid default kind (callsign/"Flight"). Validation errors
    render under the field (phase 19 D-07 idiom), keeping the typed
    value — `errors`/`submitted` are both fully defaulted so the one
    live call site (`_rules_section_html()` below) keeps calling this
    with neither, unaffected by this addition.
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
    """Up to five distinct recent callsigns as suggestion chips (D-15e,
    20-UI-SPEC.md Section Anatomy F): `history_db.recent_runway_events()`
    — the SAME call `home_page._recent_flights()` already makes
    (`companion/pages/__init__.py` forbids importing that page module
    directly, so this is an independent second call to the same shared
    server-side helper, never a page-to-page import). `<button
    type="button">` elements, inert without JS — this phase ships no
    script to wire them (D-15e's own stated no-JS floor: "with no JS the
    chips are plain text", meaning the fill-on-click behaviour is inert,
    not that the markup disappears — matching the segmented control's
    own "degrades to inert, never to invisible" convention above).

    Returns "" when there are no recent events, or on any read failure —
    never raises, matching `home_page._safe_query()`'s own fail-soft
    contract for the identical class of read.
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
    """One `<li class="rule-row">` (D-15c, 20-UI-SPEC.md Section
    Anatomy F): the theme's two palette dots drawn as `.theme-chip__dot`
    spans inside a `.rule-row__swatch theme-chip__swatches` wrapper
    (reusing the exact dot markup the compact chip grid already draws,
    never a second swatch component), the key in `.mono`, a
    `.rule-row__kind` badge composing `.banner__pill` verbatim with the
    plain-language kind word (never colour-coded — colour stays reserved
    for the swatch column only, 20-UI-SPEC.md §F's own explicit
    instruction), the theme's display name, and a Remove form.

    The Remove form's `data-confirm` (D-15c, LOCKED): `companion/static/
    confirm-submit.js` already handles any `form[data-confirm]`
    generically and degrades to a plain, uneventful submit with no
    `data-confirm-field`/`data-confirm-value` present — `_handle_rule_
    delete()` (companion/app.py) requires no confirm value of its own,
    so this is a misclick guard only, matching this list's own
    "immediately reversible, re-adding the same key restores it"
    classification (20-UI-SPEC.md's Destructive-confirmations table);
    D-15c's own locked text keeps the attribute anyway. `_rule_delete_
    action()`'s URL builder is unchanged.
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
        # Polish fix 5 (D-05): translated at this display site, same as
        # _theme_chip_grid_html()'s own label above.
        escape_html(i18n.t(device_config.theme_label(theme_id))),
        delete_form,
    )


def _rule_list_html(rows):
    """`<ul class="rule-list">`, one `.rule-row` per row (D-15c) —
    replaces the retired table/card split outright: the row shape is
    already responsive at every viewport, so there is no longer a
    `>=960px`/`<960px` split to maintain. `colour_rules.rule_rows()`
    already orders `rows` most-specific first (callsign, then hex, then
    prefix) and alphabetically within each kind — no re-sort needed
    here. Returns "" for an empty list; `_rules_section_html()` renders
    the empty state instead in that case (never called on the empty
    branch in practice, kept total for the same reason its two retired
    predecessors were).
    """
    if not rows:
        return ""
    items = "".join(
        _rule_row_html(kind, value, theme_id)
        for kind, value, theme_id, _created_at in rows)
    return '<ul class="rule-list">%s</ul>' % items


def _rules_section_html(ctx):
    """The Flight colours section's own `<section class="page-section">`
    (20-09-PLAN.md Task 3, D-15a..e): heading, one caption, the one-line
    add form, the suggestion chips, then either the plain-sans empty
    state or the `.rule-list`, followed by the "How rules combine"
    disclosure.

    **Placement decision** (carried forward from 15-UI-SPEC.md Section
    Anatomy §2's Open Question 1, unaffected by this plan): this section
    renders immediately after `</form>` closes, taking the slot the Poll
    section used to occupy — Poll itself moves one slot later. HTML
    forbids nesting a `<form>` inside another `<form>`, and the add form
    plus each delete row are real `<form>` elements, so this section
    cannot be a descendant of `<form id=SETTINGS_FORM_ID>`. This section
    carries no `DIRTY_SECTION_ATTR` — it is not part of the tracked
    settings form, exactly like the Poll section, whose action is
    likewise immediate.

    Reads the rules registry from `ctx["colour_rules"]` (read fresh per
    request from `colour_rules.load_colour_rules(state_dir)` — never the
    poll-cycle process cache), falling back to the empty registry shape
    when the key is absent so `render({})` still works. D-17 (21-01-
    PLAN.md Task 2): the "How rules combine" disclosure no longer has a
    collapsed one-sentence variant (the display mode that used to
    select it is deleted, matching `calendar_group()`'s identical
    treatment of its own "How it works" disclosure) — the full
    `<details>` always renders.
    """
    registry = ctx.get("colour_rules")
    if not isinstance(registry, dict):
        registry = {kind: {} for kind in colour_rules.RULE_KINDS}
    rows = colour_rules.rule_rows(registry)

    heading = '<h2 class="text-heading">%s</h2>' % escape_html(i18n.t(RULES_SECTION_HEADING))
    caption = (
        '<p class="text-label section-caption">%s</p>'
        % escape_html(i18n.t(RULES_SECTION_CAPTION)))
    add_form = _rule_add_form_html()
    suggestions_html = _rule_suggestion_chips_html(ctx.get("state_dir"))

    how_rules_combine_html = (
        '<details><summary>%s</summary><p class="text-body">%s</p></details>'
    ) % (
        escape_html(i18n.t(RULES_HOW_RULES_COMBINE_SUMMARY)),
        escape_html(i18n.t(RULES_HOW_RULES_COMBINE_BODY)),
    )

    if not rows:
        # D-15d: the muted sans voice, never a serif heading — a plain
        # `.text-label` paragraph, not `layout.empty_state()` (that
        # helper's own `.empty-state__heading` carries `.text-heading`,
        # this app's serif role, which D-15d explicitly forbids here).
        body_html = (
            '<div class="empty-state-plain"><p class="text-label">%s %s</p></div>'
        ) % (escape_html(i18n.t(RULES_EMPTY_HEADING)), escape_html(i18n.t(RULES_EMPTY_BODY)))
        return '<section class="page-section">%s%s%s%s%s%s</section>' % (
            heading, caption, add_form, suggestions_html, body_html, how_rules_combine_html)

    list_html = _rule_list_html(rows)
    return '<section class="page-section">%s%s%s%s%s%s</section>' % (
        heading, caption, add_form, suggestions_html, list_html, how_rules_combine_html)


def _nested_wrapper_html(html_fragment, base_class, nested_class):
    """Appends the `--nested` modifier to a group builder's own outer
    wrapper class (20-07-PLAN.md Task 1, 20-UI-SPEC.md Section Anatomy
    C): a card rendered under one of Display's three supersections
    carries `theme-status--nested`/`page-section--nested` so its own
    `<h2>` renders one rung below the supersection's own heading (the
    extended `.theme-status--nested > h2`/`.page-section--nested > h2`
    selector, 20-04-PLAN.md Task 1) rather than the un-nested 22px serif
    tier Device's own groups keep. `nested_class` is passed as a literal
    string by every call site (never derived from `base_class` at
    runtime) so the modifier this function actually emits stays
    grep-visible in this file's own source, matching every sibling
    class-literal already written out in full throughout this module.

    Every group builder in this file emits its outer wrapper's class
    attribute exactly once, as the literal substring `class="{base_class}"`
    (grep-confirmed above, each function) — never as a second, inner
    occurrence — so a single, count-limited `str.replace()` is the whole
    mechanism: no builder's own signature or internals change, matching
    this task's own "relocates and re-wraps, never rebuilds" scope.
    """
    needle = 'class="%s"' % base_class
    replacement = 'class="%s %s"' % (base_class, nested_class)
    return html_fragment.replace(needle, replacement, 1)


def _display_groups_html(builders, groups):
    """The Display scope's three headed supersections (D-12, 20-UI-SPEC.md
    Section Anatomy C): "Look" over Theme, Flight colours and Calendar (in
    that order), "What it watches" over Runway, "When it is on" over
    Screen on/off and Quiet hours — each grouped card gains the `--nested`
    modifier (`_nested_wrapper_html()` above). Replaces the flat
    `"".join(builders[g]() ...)` join the Device and legacy all-scope
    paths still use unchanged (this task's own instruction: leave those
    two untouched).

    Returns a 4-tuple `(in_form_html, calendar_card_html,
    watches_supersection_html, on_supersection_html)`.

    D-12 fix (20-REVIEW.md verification gap): before this fix, the
    physical `<form id="{SETTINGS_FORM_ID}">` closed right after the
    Calendar card, which — because Flight colours' own add-form and each
    delete-row are real `<form>` elements that cannot nest inside another
    `<form>` — forced Flight colours to render after "What it watches"
    instead of between Theme and Calendar as D-12 specifies. The fix:
    `in_form_html` now holds ONLY the "Look" intro heading plus Theme, so
    `render()` can close `</form>` right after Theme — before Flight
    colours' own `<form>`s ever need to sit alongside it. `calendar_card_
    html` (Calendar's card, nested-wrapped exactly like Theme/Runway) is
    returned separately so `render()` can place it AFTER Flight colours,
    restoring D-12's locked Theme -> Flight colours -> Calendar order.
    Calendar's own compact chip-grid radios keep posting through the
    physical form via the `form="{SETTINGS_FORM_ID}"` attribute
    `calendar_group()` now adds to them (the same idiom `runway_fieldset()`'s
    radios already use) — it is still a saved setting, unlike the feed
    URL, even though its card is no longer a literal descendant of the
    form.

    20-07-PLAN.md Task 2 (D-19/Pitfall 1): Screen on/off and Quiet hours
    are no longer literal descendants of `<form id="{SETTINGS_FORM_ID}">`
    (their own instant-switch `<form>`s would otherwise nest inside it,
    which HTML forbids), so "When it is on"'s own header and both its
    cards must render as a unit AFTER `</form>` closes.

    Polish fix 4 (D-14c), still true after the D-12 fix above: "What it
    watches" (Runway) is ALSO not a literal descendant of
    `<form id="{SETTINGS_FORM_ID}">` — its own radio inputs instead carry
    an explicit `form="{SETTINGS_FORM_ID}"` attribute (`runway_fieldset()`'s
    own docstring), the same idiom Calendar's chip grid now reuses too.
    `render()` emits `in_form_html` inside the form; `calendar_card_html`,
    `watches_supersection_html` and `on_supersection_html` all after it,
    in that order (with Flight colours and the calendar connect/disconnect
    forms interleaved between `in_form_html` and `calendar_card_html`) —
    keeping the locked Look/What it watches/When it is on reading order
    across the form boundary.
    """
    theme_html = (
        _nested_wrapper_html(builders[screens.GROUP_THEME](), "theme-status", "theme-status--nested")
        if screens.GROUP_THEME in groups else "")
    calendar_card_html = (
        _nested_wrapper_html(builders[screens.GROUP_CALENDAR](), "page-section", "page-section--nested")
        if screens.GROUP_CALENDAR in groups else "")
    runway_html = (
        _nested_wrapper_html(builders[screens.GROUP_RUNWAY](), "theme-status", "theme-status--nested")
        if screens.GROUP_RUNWAY in groups else "")
    # D-12 fix: the "Look" intro heading now precedes Theme ONLY inside
    # the physical form — Flight colours and Calendar both render after
    # `</form>` closes (see render()'s own docstring for the exact
    # interleaving), but visually and structurally still read as part of
    # "Look", since no second `section_intro_html()` heading separates
    # them from Theme.
    in_form_html = (
        layout.section_intro_html(
            DISPLAY_LOOK_SECTION_ID, i18n.t(DISPLAY_LOOK_HEADING), i18n.t(DISPLAY_LOOK_INTRO))
        + theme_html
    )
    # Polish fix 4 (D-14c), unchanged by the D-12 fix above: "What it
    # watches" (Runway) renders AFTER `<form id="{SETTINGS_FORM_ID}">`
    # closes — a sibling, not a literal descendant.
    watches_supersection_html = (
        layout.section_intro_html(
            DISPLAY_WATCHES_SECTION_ID, i18n.t(DISPLAY_WATCHES_HEADING),
            i18n.t(DISPLAY_WATCHES_INTRO))
        + runway_html
    )
    # 20-07-PLAN.md Task 2: display_group()/quiet_hours_group() are
    # called here (still, exactly as before this task — the same
    # dict-of-lambdas `builders` this function has always read from),
    # but their OWN return value is now a card that carries its own
    # instant-switch <form> and scheduled inputs bound to
    # SETTINGS_FORM_ID via the form= attribute, never itself joined into
    # `in_form_html` above.
    display_html = (
        _nested_wrapper_html(builders[screens.GROUP_DISPLAY](), "theme-status", "theme-status--nested")
        if screens.GROUP_DISPLAY in groups else "")
    quiet_hours_html = (
        _nested_wrapper_html(
            builders[screens.GROUP_QUIET_HOURS](), "theme-status", "theme-status--nested")
        if screens.GROUP_QUIET_HOURS in groups else "")
    on_supersection_html = (
        layout.section_intro_html(
            DISPLAY_ON_SECTION_ID, i18n.t(DISPLAY_ON_HEADING), i18n.t(DISPLAY_ON_INTRO))
        + display_html + quiet_hours_html
    )
    return in_form_html, calendar_card_html, watches_supersection_html, on_supersection_html


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
    # 20-09-PLAN.md Task 1 (D-14b): two new context keys, read fresh per
    # request exactly like calendar_last_synced_at above (companion/
    # app.py's page_context() computes both from the SAME load_calendar_
    # registry() call already made for calendar_last_synced_at, never a
    # second read). last_attempt_at is what distinguishes "just
    # connected, no sync yet" from "has been failing" — entry_count is
    # the status row's own detail template's flight count.
    calendar_last_attempt_at = ctx.get("calendar_last_attempt_at")
    calendar_entry_count = ctx.get("calendar_entry_count") or 0
    # Phase 17 plan 03 (D-02): plan 17-04 supplies this context key
    # (calendar_rules.calendar_secret_mode_is_unsafe(state_dir)). Until
    # then this degrades to a falsy default rather than raising, matching
    # how calendar_configured/calendar_last_synced_at above already read.
    calendar_drift = ctx.get("calendar_drift")
    # 20-11-PLAN.md Task 1 (D-26/D-28): read fresh from the SAME device_cfg
    # dict already loaded above, mirroring current_led_enabled's own
    # .get()-with-a-documented-default shape — a device_config.json
    # predating this field (or a genuinely absent one) resolves through
    # server.device_config.DEFAULT_NOTIFICATIONS, never a KeyError.
    current_notifications = device_cfg.get("notifications") or device_config.DEFAULT_NOTIFICATIONS
    notifications_configured = bool(current_notifications.get("topic_url"))
    current_notifications_battery = current_notifications.get(
        "battery_low", device_config.DEFAULT_NOTIFICATIONS["battery_low"])
    current_notifications_silent = current_notifications.get(
        "frame_silent", device_config.DEFAULT_NOTIFICATIONS["frame_silent"])
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
        '<div class="dirty-bar" data-dirty-bar hidden role="status" '
        'data-dirty-changed-suffix="%s" data-dirty-and="%s" '
        'data-dirty-list-and="%s" data-dirty-unsaved-singular="%s" '
        'data-dirty-unsaved-plural="%s">'
        "<span data-dirty-count>%s</span>"
        '<button type="submit" class="dirty-bar__save" form="%s">%s</button>'
        '<button type="button" class="dirty-bar__cancel" data-dirty-cancel>%s</button>'
        "</div>"
    ) % (
        escape_html(i18n.t(DIRTY_CHANGED_SUFFIX)), escape_html(i18n.t(DIRTY_AND)),
        escape_html(i18n.t(DIRTY_LIST_AND)), escape_html(i18n.t(DIRTY_UNSAVED_SINGULAR)),
        escape_html(i18n.t(DIRTY_UNSAVED_PLURAL)),
        escape_html(i18n.t(DIRTY_BAR_INITIAL_TEXT)), SETTINGS_FORM_ID,
        escape_html(i18n.t("Save settings")), escape_html(i18n.t("Cancel")),
    )

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
            errors=errors, submitted=submitted, next_wake_clock=next_wake_clock,
            state_dir=ctx.get("state_dir")),
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
            calendar_last_attempt_at, ctx.get("now"), calendar_entry_count,
            current_calendar_theme_id, current_theme_id,
            errors=errors, submitted=submitted),
        screens.GROUP_NOTIFICATIONS: lambda: notifications_group(
            notifications_configured, current_notifications_battery,
            current_notifications_silent, errors=errors, submitted=submitted),
    }
    # 20-11-PLAN.md Task 1 (D-19/Pitfall 1): "Send a test" is its own
    # immediate-POST form and must never nest inside <form id=
    # "settings-form"> — rendered as a sibling, after </form> closes,
    # exactly like calendar_connect_html/calendar_disconnect_html below.
    # screens.GROUP_NOTIFICATIONS is never a member of scope_groups(
    # SCOPE_DISPLAY) or the legacy SCOPE_ALL tuple, so this is correctly
    # "" on both of those scopes.
    notifications_test_html = (
        notifications_test_section() if screens.GROUP_NOTIFICATIONS in groups else "")
    # 19-12-PLAN.md Task 2 (D-23): the conditional selector joins the
    # screen caption in BOTH scoped headers' action_html slot — with
    # today's single-member registry it renders as "", so both headers
    # stay byte-identical to their pre-D-23 output.
    if scope == SCOPE_DISPLAY:
        header = layout.page_header(
            i18n.t(DISPLAY_PAGE_TITLE), purpose=i18n.t(DISPLAY_PAGE_PURPOSE),
            action_html=_screen_caption_html(screen) + _screen_selector_html(screen_id, errors=errors))
        # 21-04-PLAN.md Task 1 (D-02/R-01): the shared Frame strip, once,
        # directly after the page header and before the "Look"
        # supersection's own section_intro_html() (the first thing
        # groups_html renders, below) — the exact same next_wake_iso
        # already computed above for next_wake_clock feeds it, so there
        # is no second wake.next_wake_at_iso() call for the same value.
        frame_strip_section_html = layout.frame_strip_html(
            ctx, return_to=layout.DISPLAY_ROUTE, next_wake_iso=next_wake_iso)
        hidden_html = _scope_fields_html(scope, layout.DISPLAY_ROUTE)
        # 20-07-PLAN.md Task 1 (D-10/D-11): Flight colours and the
        # calendar-disconnect form move to Display with their groups —
        # these two flags used to be Device-only (set only in the
        # elif scope == SCOPE_DEVICE: branch below); Poll (Manual
        # refresh) stays Device-only, unaffected by this move.
        show_rules = bool(screen.get("has_colour_rules"))
        show_poll = False
        show_calendar_disconnect = screens.GROUP_CALENDAR in groups
        # 20-07-PLAN.md Task 1 (D-12, 20-UI-SPEC.md Section Anatomy C),
        # restructured by the D-12 fix (20-REVIEW.md verification gap):
        # three headed supersections replace the flat join — see
        # _display_groups_html()'s own docstring for the Flight-colours/
        # Calendar placement reasoning. `groups_html` (Look intro +
        # Theme only) renders inside the form; `display_calendar_card_
        # html` renders after Flight colours, below; the third and
        # fourth elements ("What it watches"'s own header plus Runway,
        # and "When it is on"'s own header plus the Screen on/off and
        # Quiet hours cards) both render AFTER </form> closes too.
        (groups_html, display_calendar_card_html, display_watches_supersection_html,
            display_on_supersection_html) = _display_groups_html(builders, groups)
    elif scope == SCOPE_DEVICE:
        # 19-12-PLAN.md Task 3 (D-13): "Home and Device show" — the
        # Next-wake line joins the screen caption/selector in the same
        # action_html slot (Display instead carries the per-caption
        # suffixes via next_wake_clock threaded into the builders dict
        # above).
        # 20-07-PLAN.md Task 3 (D-36): the Edit-artwork link that used to
        # join this same slot is gone outright.
        header = layout.page_header(
            i18n.t(DEVICE_PAGE_TITLE), purpose=i18n.t(DEVICE_PAGE_PURPOSE),
            action_html=(
                _screen_caption_html(screen) + _screen_selector_html(screen_id, errors=errors)
                + _next_wake_caption_html(next_wake_clock)))
        hidden_html = _scope_fields_html(scope, layout.DEVICE_ROUTE)
        # 21-04-PLAN.md Task 1 (D-01/D-02): the Frame strip renders only
        # on Home and Display — never on Device.
        frame_strip_section_html = ""
        # 20-07-PLAN.md Task 1 (D-10/D-11): Flight colours and the
        # calendar-disconnect form are no longer Device concerns — both
        # groups they act on (Runway/Calendar) moved to Display's
        # everyday_groups this phase, so Device's own screens.GROUP_
        # CALENDAR-in-groups test would always be False now anyway; kept
        # explicit here rather than relying on that emptiness.
        show_rules = False
        show_poll = bool(screen.get("has_manual_poll"))
        show_calendar_disconnect = False
        # 20-07-PLAN.md Task 1 (D-10): Device's own advanced_groups no
        # longer includes GROUP_DISPLAY/GROUP_QUIET_HOURS at all (both
        # moved to Display's everyday_groups), so this flat join never
        # calls display_group()/quiet_hours_group() on this scope —
        # their own instant-switch <form> never has a chance to nest
        # inside this scope's <form id="settings-form">.
        groups_html = "".join(builders[g]() for g in groups if g in builders)
        display_calendar_card_html = ""
        display_watches_supersection_html = ""
        display_on_supersection_html = ""
    else:
        header = layout.page_header(i18n.t("Settings"))
        hidden_html = ""
        # 21-04-PLAN.md Task 1 (D-01/D-02): SCOPE_ALL is the legacy,
        # never-served whole-page render (see its own comment two lines
        # below) — it never carried the Screen/Quiet-hours instant
        # switches even before this task, so it carries no Frame strip
        # either.
        frame_strip_section_html = ""
        show_rules = show_poll = True
        # SCOPE_ALL is the legacy whole-page render, kept byte-identical
        # to its own pre-Phase-19 output for existing harness checks
        # against the full form — never used by a live app.py route
        # (render()'s own module comment). The disconnect action's own
        # confirmed-form flow is new surface Task 1 adds only to the two
        # live scoped pages; SCOPE_ALL stays exactly as it was.
        show_calendar_disconnect = False
        groups_html = "".join(builders[g]() for g in groups if g in builders)
        display_calendar_card_html = ""
        display_watches_supersection_html = ""
        display_on_supersection_html = ""

    rules_section_html = _rules_section_html(ctx) if show_rules else ""
    if rules_section_html and scope == SCOPE_DISPLAY:
        # 20-07-PLAN.md Task 1 (D-12): only the Display scope's copy of
        # Flight colours sits under a supersection heading — SCOPE_ALL's
        # legacy render (the only other scope show_rules is ever true
        # for) stays byte-identical to its own pre-Phase-19 output.
        rules_section_html = _nested_wrapper_html(
            rules_section_html, "page-section", "page-section--nested")
    poll_section_html = (
        '<section class="page-section">'
        '<h2 class="text-heading">%s</h2>'
        "%s"
        "</section>" % (escape_html(i18n.t(POLL_SECTION_HEADING)), poll_trigger_section(cooldown_remaining))
        if show_poll else "")
    # 19-11-PLAN.md Task 1 (D-08/A-26): a sibling of the settings <form>,
    # never a descendant — see calendar_disconnect_section()'s own
    # docstring for why. Emitted immediately after </form> closes.
    # 20-09-PLAN.md Task 1 (D-14c): the Connect/Replace mini-form renders
    # immediately before calendar_disconnect_html below, both siblings of
    # the settings <form> — never a descendant of it, and never behind
    # the page-wide Save (T-20-11). Guarded by the SAME flag as the
    # disconnect form: the two always co-occur (only the live Display
    # scope ever shows either), and calendar_connect_section()'s own
    # `.page-section` wrapper immediately preceding
    # `.calendar-disconnect-form` is what makes the `:has(+
    # .calendar-disconnect-form)` fused-card CSS (20-04-PLAN.md) apply.
    #
    # D-12 fix (20-REVIEW.md verification gap), superseding Polish fix
    # 4's own placement: on the Display scope, `</form>` now closes
    # right after the Theme card (see _display_groups_html()'s own
    # docstring), so calendar_connect_html/calendar_disconnect_html,
    # emitted here, land immediately after display_calendar_card_html
    # below — never after Runway. Device/SCOPE_ALL never have
    # show_calendar_disconnect True, so this reordering changes nothing
    # for either.
    calendar_connect_html = (
        calendar_connect_section(calendar_configured, errors=errors)
        if show_calendar_disconnect else "")
    calendar_disconnect_html = (
        calendar_disconnect_section(calendar_configured, calendar_drift)
        if show_calendar_disconnect else "")

    return (
        header
        # 21-04-PLAN.md Task 1 (D-02/R-01): the shared Frame strip
        # renders immediately after the page header and before the
        # form (whose own groups_html opens with the "Look"
        # supersection's own section_intro_html()) — "" on Device and
        # SCOPE_ALL.
        + frame_strip_section_html
        + '<form class="config-form" id="%s" data-dirty-form method="post" action="%s">'
        "%s"
        "%s"
        '<button type="submit" %s>%s</button>'
        "</form>"
        "%s"
        "%s"
        "%s"
        "%s"
        "%s"
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
        escape_html(i18n.t("Save settings")),
        # D-12 fix (20-REVIEW.md verification gap): Flight colours
        # (rules_section_html) now renders immediately after `</form>`
        # closes, BEFORE the Calendar card — restoring D-12's locked
        # Theme -> Flight colours -> Calendar reading order inside
        # "Look". Always "" on the Device scope (show_rules is False
        # there); on SCOPE_ALL it is never nested and this slot's
        # relative position there is new surface (SCOPE_ALL is the
        # legacy, never-served render this task leaves otherwise
        # untouched — show_rules is only True there alongside
        # show_calendar_disconnect=False, so calendar_connect_html/
        # calendar_disconnect_html/display_calendar_card_html are all ""
        # and this reordering has no visible effect on that scope).
        rules_section_html,
        # D-12 fix: the Calendar card itself, nested-wrapped exactly
        # like Theme/Runway, now renders here — after Flight colours,
        # before its own connect/disconnect forms. Always "" on
        # Device/SCOPE_ALL (computed above).
        display_calendar_card_html,
        calendar_connect_html,
        calendar_disconnect_html,
        # 20-07-PLAN.md Task 1 (D-12), restructured by the D-12 fix
        # above: "What it watches"'s own header plus the Runway card —
        # always "" on the Device/SCOPE_ALL paths (both set it to ""
        # explicitly above), so this addition changes nothing for
        # either. On Display, this now renders AFTER the calendar
        # connect/disconnect siblings above, so Runway still follows
        # Calendar in document order even though neither is any longer a
        # literal descendant of the same <form>.
        display_watches_supersection_html,
        # 20-11-PLAN.md Task 1 (D-19/Pitfall 1): "" on Display/SCOPE_ALL
        # (computed above), so this addition changes nothing for either
        # — only the Device scope's own render gains this sibling form,
        # positioned right after the Notifications card's own in-form
        # content (inside groups_html above) and before Manual refresh.
        notifications_test_html,
        # 20-07-PLAN.md Task 2 (D-19/Pitfall 1): "When it is on"'s own
        # header plus the Screen on/off and Quiet hours cards — always ""
        # on the Device/SCOPE_ALL paths (both set it to "" explicitly
        # above), so this addition changes nothing for either.
        display_on_supersection_html,
        poll_section_html,
        dirty_bar_html,
    )


def _screen_caption_html(screen):
    """The small "Screen: Plane frame" line under a scoped page's title —
    the visible end of the companion/screens.py seam. Rendered as an
    already-safe block for page_header()'s `action_html` slot.
    """
    # Polish fix 5 (D-05): screen["label"] (device_config-adjacent
    # registry text, e.g. "Plane frame") is translated at this display
    # site via i18n.t() — the screen id itself never changes;
    # companion/i18n_fr/registry.py supplies the French entry ("Cadre
    # avion").
    return (
        '<p class="page-header__screen text-label">%s</p>'
        % escape_html(i18n.t(SCREEN_CAPTION_TEMPLATE) % i18n.t(screen["label"])))


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
                i18n.t(NEXT_WAKE_HEADER_LABEL),
                i18n.t(NEXT_WAKE_HEADER_VALUE_TEMPLATE) % next_wake_clock)))


def _screen_selector_html(current_screen_id, errors=None):
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

    `errors` (D-07, WR-01 follow-up: every sibling field this plan
    touches renders its own `_field_error_html()` message; this was the
    one field that did not) carries the D-23 gate's rejected-`screen_id`
    message, if any, rendered via `_field_error_html()` immediately after
    the `<select>` — no `submitted` repopulation parameter is needed
    here, unlike the text/select fields elsewhere in this file, because
    `current_screen_id` passed in above is already resolved by the
    caller (`screens.current_screen_id(ctx)`), the same "current value
    already reflects the rejected submission" reasoning `render()`'s own
    call sites rely on for every field.
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

    20-11-PLAN.md Task 1 (D-26/D-28) adds a fourth group,
    `screens.GROUP_NOTIFICATIONS`, and three more form fields:
    `notifications_topic_url`, `notifications_battery`,
    `notifications_silent`. The two checkboxes follow the identical
    in-scope-absent-means-False resolution `led_enabled`/`quiet_hours_
    enabled`/`display_enabled` above already use — a crafted value
    rejects the whole save, same as every sibling checkbox gate. The
    topic URL is genuinely different from every scalar field above: an
    empty (stripped) submission means "leave the stored URL unchanged"
    (this codebase's established empty-numeric-input convention,
    `wake_interval_s`'s own precedent), never "clear it" — there is no
    UI affordance to clear a configured topic URL in this plan, mirroring
    the calendar feed URL's own identical write-only "replace only"
    contract. Because `save_device_config(notifications=...)` REPLACES
    the whole sub-dict rather than merging per sub-key (unlike every
    scalar field, which the write path itself carries forward when
    `None`), this handler reads the CURRENT on-disk group via
    `device_config.load_device_config(state_dir)` and builds the
    complete replacement dict itself — `lang` is written from
    `ctx["lang"]`, the session's resolved language at save time (D-28:
    there is no language-picking control for this group anywhere on the
    page, because the poll loop has no browser to ask, 20-RESEARCH.md
    Pitfall 6).
    When `screens.GROUP_NOTIFICATIONS` is not in scope (every Display
    render, and the legacy SCOPE_ALL), `notifications` stays `None` and
    `save_device_config()` carries the current on-disk group forward
    unchanged, exactly like every field this handler does not own on
    that scope.
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
    submitted_notifications_topic_url = form.get("notifications_topic_url")
    submitted_notifications_battery = form.get("notifications_battery")
    submitted_notifications_silent = form.get("notifications_silent")
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
    # 20-11-PLAN.md Task 1 (D-26): a shape bound against an absurd paste,
    # mirroring CALENDAR_URL_SIGNAL_INVALID's own over-length check above
    # — only checked when the field is actually in scope (an out-of-scope
    # submission is structural, never a real user mistake, matching every
    # other in-scope gate below).
    if (
        screens.GROUP_NOTIFICATIONS in in_scope
        and submitted_notifications_topic_url
        and len(submitted_notifications_topic_url.strip()) > NOTIFICATIONS_URL_MAX_LEN
    ):
        _note_error(errors, "notifications_topic_url", ERROR_NOTIFICATIONS_URL_TOO_LONG)
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
    # 20-11-PLAN.md Task 1 (D-26/D-28): the two checkboxes follow the
    # identical in-scope-absent-means-False resolution every sibling
    # checkbox gate above already uses. The topic URL is resolved
    # separately below, once both checkboxes have cleared this gate,
    # because building the replacement dict needs the CURRENT on-disk
    # group (save_device_config() REPLACES the whole notifications
    # sub-dict rather than merging it per key, unlike every scalar field
    # above) — see this function's own docstring paragraph on this field.
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
        # D-26: an empty (stripped) submission means "leave the stored
        # URL unchanged", never "clear it" — this codebase's established
        # empty-numeric-input convention (wake_interval_s's own
        # precedent above), read fresh from disk rather than trusted
        # from ctx, so this resolution is correct even when a caller's
        # own ctx dict carries a stale or absent "device_config" key.
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
            # D-28: written silently from the session's resolved
            # language at save time — no language-picking control for
            # this group exists anywhere on the page (the poll loop has
            # no browser to ask, 20-RESEARCH.md Pitfall 6).
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
