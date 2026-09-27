"""Health status and trend page, and the landing context for the
on-device fault icon's redirect target.

Every dynamic value reaches HTML through `escape_html()` or an escaping
component builder. The Device and Pipeline freshness signals are
independent (different failure modes and data sources), never blended
into one verdict. `_safe_query()` returns the `_DB_UNAVAILABLE` sentinel
instead of raising, so each section degrades independently.
`safe_health_state()` is this module's one public cross-page export, so no
nav renderer needs to import a page module.

The markup-free severity computation (`health_signals()` and everything
it is built from) lives in companion/health_signals.py, imported below
and re-exported under its historical names — this module owns only the
markup half (the `_x_section()` tile builders, `health_state_from_signals()`
and its `compute_health_state()`/`safe_health_state()` wrappers, which
still need those builders and so stay here).
"""
from datetime import date, datetime, timedelta, timezone
# `date` joins the three for the regularity grid's window walk, which is
# ordinal calendar arithmetic (toordinal()/fromordinal()) and carries no
# duration anywhere in it.

from companion.layout import escape_html
import companion.battery as battery
import companion.battery_chart as battery_chart
import companion.draw as draw
import companion.health_signals as health_signals_module
import companion.i18n as i18n
import companion.layout as layout
import companion.page_context as page_context
import companion.prefs as prefs  # for the resolved language directly:
# French requires a real U+00A0 before the colon (_label_colon() below),
# not merely a translated label.
import companion.wake as wake
import companion.frame_state as frame_state  # the one frame-state
# resolution — the Frame tile and the nav notification dot both consume
# resolve_state(), never re-deriving due/held/late from
# device_staleness_thresholds() alone.
from server import device_config
from server import history_db


HEALTH_UNAVAILABLE_TEXT = i18n.msg(
    "health.health_history_is_temporarily_unavailable_check",
    "Health history is temporarily unavailable — check the companion "
    "service logs.")


def _label_colon(label):
    """`label` (already translated by the caller) followed by a
    language-appropriate colon separator: a real U+00A0 non-breaking
    space before ":" in French; the plain ":" in English.
    """
    return label + (" :" if prefs.current_lang() == "fr" else ":")

# The freshness thresholds, the off-box marker constants, the battery
# query/drop constants and BATTERY_TREND_WINDOW_DAYS all live in
# companion/health_signals.py now (BATTERY_TREND_WINDOW_DAYS itself
# forwards from companion/battery_chart.py, since the chart's own
# aria-label interpolates it directly) — re-exported here under their
# historical names, since a number of tests and this module's own markup
# builders below read them as `health_page.X`.
STALE_PIPELINE_WARN_S = health_signals_module.STALE_PIPELINE_WARN_S
STALE_PIPELINE_ERROR_S = health_signals_module.STALE_PIPELINE_ERROR_S
OFFBOX_MARKER_ENV_VAR = health_signals_module.OFFBOX_MARKER_ENV_VAR
BATTERY_TREND_LIMIT = health_signals_module.BATTERY_TREND_LIMIT
BATTERY_TREND_WINDOW_DAYS = health_signals_module.BATTERY_TREND_WINDOW_DAYS
BATTERY_DROP_WARN_MV = health_signals_module.BATTERY_DROP_WARN_MV

_CORROBORATION_ROWS = (
    # (stored corroborated string, display label, status, explanation).
    # The stored key ("True"/"None"/"False") is the on-disk vocabulary
    # history_db.save_poll_state() writes and must never be renamed.
    ("True", i18n.msg("health.both_agree", "Both agree"), "ok",
     i18n.msg(
         "health.both_flight_data_sources_on_the_frame_picked",
         "Both flight-data sources on the frame picked the same aircraft.")),
    # "off", not "ok": this state means there was nothing to compare
    # against, not that agreement was confirmed — a neutral, everyday
    # state, never a problem, so never "warn" either.
    ("None", i18n.msg("health.only_one_saw_it", "Only one saw it"), "off",
     i18n.msg(
         "health.only_one_of_the_two_sources_returned_an",
         "Only one of the two sources returned an aircraft this cycle — "
         "that is not the same as a disagreement, there was simply nothing "
         "from the other source to compare it against.")),
    ("False", i18n.msg("health.they_disagree", "They disagree"), "warn",
     i18n.msg(
         "health.the_two_sources_named_different_aircraft_so",
         "The two sources named different aircraft, so nothing was shown "
         "that cycle — the display kept the previous image instead.")),
)

# Kept as a literal, human-maintained list rather than importing
# server.plane.detect: this page is presentation-only and must not reach
# into the detection/network layer. Keep in sync with
# detect.DEFAULT_PROVIDER_ORDER by hand if that list ever changes.
_ADSB_PROVIDER_NAMES = ("adsb.fi", "adsb.lol")

SOURCE_FAULT_HEADING = i18n.msg("health.ads_b_source_outage", "ADS-B source outage")
SOURCE_FAULT_BODY_TEMPLATE = i18n.msg(
    "health.the_frame_s_alert_badge_is_showing_because",
    "The frame's alert badge is showing because every configured ADS-B "
    "source (%s) failed to respond on the most recent pipeline run — "
    "this is a data-source outage, not a device problem.")
SOURCE_FAULT_BODY = SOURCE_FAULT_BODY_TEMPLATE % ", ".join(_ADSB_PROVIDER_NAMES)

# The leading "⚠ " glyph lives in _anomaly_banner_html(), not here, so
# this stays a literal substring of whatever renders.
ANOMALY_BANNER_TEXT = i18n.msg(
    "health.something_needs_attention_check_the_tiles_below",
    "Something needs attention — check the tiles below.")

_SEVERITY_BANNER_NOUNS = {
    "warn": i18n.msg("health.warning", "warning"),
    "error": i18n.msg("health.error", "error"),
}  # falls back to "issue" for any severity not in this dict.
_SEVERITY_BANNER_ISSUE_TEXT = i18n.msg("health.issue", "issue")

DEVICE_FRESHNESS_LABEL = i18n.msg("health.device_last_checked_in", "Device last checked in")
# Plain-language visible label; the technical term stays one hover away
# via `caption_title` at the tile's stat_tile() call site below.
PIPELINE_FRESHNESS_LABEL = i18n.msg(
    "health.flight_data_last_updated", "Flight data last updated")
PIPELINE_FRESHNESS_TITLE = i18n.msg(
    "health.ads_b_pipeline_last_ran", "ADS-B pipeline last ran")

CORROBORATION_TILE_LABEL = i18n.msg(
    "health.do_the_two_data_sources_agree", "Do the two data sources agree?")
CORROBORATION_TILE_TITLE = i18n.msg("health.corroboration", "Corroboration")

LAST_DETECTION_LABEL = i18n.msg("health.last_aircraft_detected", "Last aircraft detected")

# Evidence only ("since it started"), never the state name, so it is
# safe to publish verdict-free as compute_health_state()'s
# "pipeline_detail_html" key.
PIPELINE_NEVER_RAN_DETAIL_TEXT = i18n.msg(
    "health.the_frame_has_not_reported_a_flight_since_it",
    "The frame has not reported a flight since it started.")

# A short plain-sentence verdict for each stat tile whose caption names
# a signal but whose border colour alone was the only place the actual
# verdict lived (WCAG 1.4.1: colour must never be the sole means of
# conveying information). The Resolution-rate tile deliberately has no
# sibling dict here — see render()'s own comment at that tile's
# stat_tile() call.
DEVICE_STATE_TEXT = {
    "ok": i18n.msg("health.checking_in_normally", "Checking in normally"),
    "warn": i18n.msg(
        "health.has_not_checked_in_for_a_while", "Has not checked in for a while"),
    "error": i18n.msg(
        "health.has_not_checked_in_for_a_long_time",
        "Has not checked in for a long time"),
    # A genuine fourth device state, not merely "hasn't checked in for a
    # while": a frame the strip/tile both know is quiet-hours-held.
    # Reuses the "off" token the pipeline's never-ran state and the
    # strip's held dot use, a neutral state that is never a problem. A
    # held frame is routed here only when frame_state.resolve_state()
    # says STATE_HELD.
    "off": i18n.msg("health.asleep_for_quiet_hours", "Asleep for quiet hours"),
}

PIPELINE_STATE_TEXT = {
    "ok": i18n.msg("health.running_on_schedule", "Running on schedule"),
    "warn": i18n.msg("health.a_little_behind", "A little behind"),
    "error": i18n.msg("health.has_not_run_for_a_long_time", "Has not run for a long time"),
    "off": i18n.msg("health.no_detection_yet", "No detection yet"),
}
CORROBORATION_STATE_TEXT = {
    "ok": i18n.msg("health.sources_agree", "Sources agree"),
    "warn": i18n.msg("health.sources_disagreed_recently", "Sources disagreed recently"),
}

# Retired: status_dot() emitted an empty first span with no accessible
# name, so a screen reader got only the subject label, never the state.
# The battery-trend section's top edge carries the verdict instead.

# The auto-refresh pill's visible copy, English only (this app renders
# `<html lang="en">`).
REFRESH_PILL_TEXT = layout.REFRESH_PILL_TEXT

# The hook freshness.js toggles its breathing class on. Duplicated, not
# imported: freshness.js is a static asset, not a Python module.
REFRESH_LIVE_DOT_ATTR = layout.REFRESH_LIVE_DOT_ATTR

# No relative-age suffix: `now` is computed once per request and fed
# back into itself, so a "(0s ago)" suffix would always read zero.
FRESHNESS_PREFIX_TEXT = layout.FRESHNESS_PREFIX_TEXT

# freshness.js always runs unconditionally, with no client-side pause
# state to label.

# The DOM regions freshness.js swaps wholesale on this page. Lives in
# layout.py's REFRESH_SWAP_SELECTORS_BY_PAGE, the per-page registry Home
# and the Display scope also join.
REFRESH_SWAP_SELECTORS = layout.REFRESH_SWAP_SELECTORS_BY_PAGE[
    layout.REFRESH_PAGE_HEALTH]

# Looked up by battery-trend.js and styled by style.css — duplicated,
# not imported, since those are static assets. A cross-file check
# asserts both literals appear in battery-trend.js's shipped source.
BATTERY_READOUT_ID = "battery-readout"
# The chart's own class vocabulary, geometry and markup now live in
# companion/battery_chart.py (built on companion/draw.py); re-exported
# here under their historical names so nothing outside this module needs
# to know the chart moved.
SPARKLINE_HIT_CLASS = battery_chart.SPARKLINE_HIT_CLASS
SPARKLINE_DOT_CLASS = battery_chart.SPARKLINE_DOT_CLASS
SPARKLINE_LINE_CLASS = battery_chart.SPARKLINE_LINE_CLASS
SPARKLINE_AXIS_CLASS = battery_chart.SPARKLINE_AXIS_CLASS
SPARKLINE_AREA_LAYER_CLASS = battery_chart.SPARKLINE_AREA_LAYER_CLASS
SPARKLINE_AREA_CLASS = battery_chart.SPARKLINE_AREA_CLASS
SPARKLINE_MARK_CLASS = battery_chart.SPARKLINE_MARK_CLASS
SPARKLINE_THRESHOLD_CLASS = battery_chart.SPARKLINE_THRESHOLD_CLASS
SPARKLINE_LEGEND_ROW_CLASS = battery_chart.SPARKLINE_LEGEND_ROW_CLASS
SPARKLINE_LEGEND_CLASS = battery_chart.SPARKLINE_LEGEND_CLASS
SPARKLINE_LEGEND_SWATCH_CLASS = battery_chart.SPARKLINE_LEGEND_SWATCH_CLASS
# Must equal companion/app.py's SCRIPT_ROUTE — duplicated, not imported,
# since companion/pages/__init__.py forbids a page module importing
# companion.app (app.py imports pages, so the reverse would be
# circular). The test harness asserts the two stay equal.
BATTERY_TREND_SCRIPT_SRC = "/static/battery-trend.js"

# "%d" is interpolated with BATTERY_TREND_WINDOW_DAYS // 30 at the one
# call site below, never a typed literal, so the heading cannot silently
# drift from the window the chart plots. Both constants live in
# companion/battery_chart.py, since the chart's own <svg aria-label>
# interpolates the exact same two values and the two headings must never
# disagree.
BATTERY_SECTION_HEADING_TEMPLATE = battery_chart.BATTERY_SECTION_HEADING_TEMPLATE
# Contract value shared with style.css's .battery-trend-section rule,
# guarded against silent drift by a cross-file check.
BATTERY_SECTION_CLASS = "battery-trend-section"

# One icon id per Health tile signal, each a member of layout.ICON_IDS.
# The whitelist is what keeps a typo here from becoming a raw-markup
# injection: icon_html() renders nothing for an unrecognised id, so a
# separate check asserts each constant is a genuine ICON_IDS member.
ICON_DEVICE = "icon-device"
ICON_PIPELINE = "icon-pipeline"
ICON_CORROBORATION = "icon-corroboration"

# The check-in regularity grid reports what is observable — the
# regularity of the record of check-ins, not the interval the device was
# expected to keep (nowhere in history, and not even a constant, since
# wake.effective_wake_interval_s() switches by screen state and quiet
# hours) — and its caption says so. Every verdict comes from
# wake.classify_check_in_gap(), derived from the same
# wake.device_staleness_thresholds() the Frame tile consumes, so this
# grid and that tile can never disagree about "late".
CHECK_IN_SECTION_HEADING = i18n.msg("health.check_in_regularity", "Check-in regularity")

# One cell per Europe/Paris calendar day. Inside draw.regularity_grid()'s
# own bound (ten columns by six rows = 60 cells at the measured card
# width), so the window can never be what the drawing truncates.
CHECK_IN_WINDOW_DAYS = 30

CHECK_IN_GRID_CLASS = "check-in-grid"
CHECK_IN_SCALE_CLASS = "check-in-grid__scale"
CHECK_IN_KEY_CLASS = "check-in-key"
CHECK_IN_KEY_ITEM_CLASS = "check-in-key__item"
CHECK_IN_KEY_SWATCH_CLASS = "check-in-key__swatch"

# The four states' own words, keyed on the classifier's own vocabulary.
# Colour is not a reading: four squares in four colours need their four
# names in text beside them, which is what the key below the grid is.
CHECK_IN_STATE_TEXT = {
    wake.CHECK_IN_ON_CADENCE: i18n.msg("health.on_cadence", "On cadence"),
    wake.CHECK_IN_LATE: i18n.msg("health.late", "Late"),
    wake.CHECK_IN_MISSING: i18n.msg("health.missing", "Missing"),
    wake.CHECK_IN_UNKNOWN: i18n.msg("health.no_record", "No record"),
}

# The caption's clauses, one constant each: only CHECK_IN_CAPTION_OBSERVED
# renders in the card's always-visible caption; every other clause moves
# into a `<details class="readings-disclosure">` immediately after it
# (see `_check_in_regularity_section_html()`).
CHECK_IN_CAPTION_OBSERVED = i18n.msg(
    "health.each_cell_is_one_day_of_observed_check_in",
    "Each cell is one day of observed check-in regularity, oldest first.")
# The cadence actually in force on an earlier day is not recoverable
# (device_config.json is a current-state file), so naming it without
# this qualifier would be a claim about the past made from a present value.
CHECK_IN_CAPTION_CADENCE = i18n.msg(
    "health.judged_against_the_cadence_configured_now_a",
    "Judged against the cadence configured now — a check-in every %s — not "
    "necessarily the cadence in force on an earlier day.")
# When there is no cadence to name at all: device_staleness_thresholds()'
# bare floors apply, and the caption must say so rather than print an
# assumed default.
CHECK_IN_CAPTION_CADENCE_FALLBACK = i18n.msg(
    "health.this_frame_s_cadence_cannot_be_determined_so",
    "This frame's cadence cannot be determined, so the grid is judged against "
    "the fallback staleness floors rather than against a configured cadence.")
# What a gap is not: the record cannot tell a wake the frame missed from
# a log range this server lost, so a grid without this sentence would
# make a claim its own data cannot support.
CHECK_IN_CAPTION_NOT_PROOF = i18n.msg(
    "health.a_day_with_no_record_is_not_proof_the_frame_did",
    "A day with no record is not proof the frame did not wake: a log rotation "
    "this server missed leaves exactly the same gap.")
# The empty deployment: a real case, rendering an honest grid of
# no-observation cells rather than a missing section.
CHECK_IN_CAPTION_EMPTY = i18n.msg(
    "health.no_check_in_intervals_are_recorded_yet_so_every",
    "No check-in intervals are recorded yet, so every day below is a day the "
    "record says nothing about.")

# The per-cell tooltip and the grid's own accessible name. The gap is
# named as a DURATION in the app's own form (layout.duration_text()) and
# the day as a local date — every visible instant in this app is
# Europe/Paris and a raw ISO string survives only behind a copy control.
CHECK_IN_CELL_TITLE = i18n.msg(
    "health.longest_observed_gap", "%s — %s: longest observed gap %s")
# No catalogue entry: a bare "%s — %s" join has never carried
# translatable words of its own, so this stays a plain template.
CHECK_IN_CELL_TITLE_NONE = "%s — %s"
CHECK_IN_GRID_LABEL = i18n.msg(
    "health.observed_check_in_regularity_one_cell_per_day",
    "Observed check-in regularity, one cell per day over the last %d days: "
    "%d on cadence, %d late, %d missing, %d with no record.")

# The two id-anchored sections Health's body is split into.
# SERVER_DATA_SECTION_ID is a cross-page coupling: history_page.py links
# to this exact anchor (#server-data) — renaming it silently breaks that
# link.
SCREEN_SECTION_ID = "screen"
SCREEN_SECTION_HEADING = i18n.msg("health.screen", "Screen")
SERVER_DATA_SECTION_ID = "server-data"
SERVER_DATA_SECTION_HEADING = i18n.msg("health.server_data", "Server & data")
# Plain-language label; the technical term stays reachable via
# `caption_title` at this tile's stat_tile() call site below.
RESOLUTION_RATE_LABEL = i18n.msg("health.flights_we_could_name", "Flights we could name")
RESOLUTION_RATE_TITLE = i18n.msg("health.route_resolution_rate", "Route resolution rate")
UNRESOLVED_SECTION_HEADING = i18n.msg(
    "health.airlines_we_could_not_name", "Airlines we could not name")
STATS_SECTION_HEADING = i18n.msg(
    "health.how_well_we_name_flights", "How well we name flights")

# Keep the leading em-dash and the space after it on both descriptions:
# that is what makes the heading and its description read as one
# continuous phrase across the baseline-aligned `.section-intro` row.
PAGE_PURPOSE_TEXT = i18n.msg(
    "health.screen_status_and_server_data_quality_in_one",
    "Screen status and server data quality, in one place.")
SCREEN_SECTION_DESCRIPTION = i18n.msg(
    "health.the_physical_frame_is_it_checking_in_and_how_s",
    "— the physical frame: is it checking in, and how's the battery.")
SERVER_DATA_SECTION_DESCRIPTION = i18n.msg(
    "health.the_ads_b_pipeline_and_route_resolution_is_the",
    "— the ADS-B pipeline and route resolution: is the data fresh and "
    "trustworthy.")

_NO_GAPS_HEADING = i18n.msg("health.no_coverage_gaps", "No coverage gaps.")
_NO_GAPS_BODY = i18n.msg(
    "health.every_airline_we_ve_seen_recently_has_been",
    "Every airline we've seen recently has been named — nothing left to look up.")

# The genuine reference material — where resolution happens and what it
# does — lives in _READ_ONLY_NOTE_DETAIL below, rendered in a `<details
# class="readings-disclosure">` immediately after this visible sentence.
_READ_ONLY_NOTE = i18n.msg("health.this_list_is_read_only_here", "This list is read-only here.")
_READ_ONLY_NOTE_DETAIL = i18n.msg(
    "health.each_row_s_resolve_link_opens_the_airlines_page",
    "Each row's Resolve link opens the Airlines page to name that airline "
    "(and add artwork, if it needs one).")

# The heading is a %-template interpolated with RESOLUTION_WINDOW_DAYS
# at the one call site, never a literal "30", so it cannot silently
# drift from the window constant.
_NO_STATS_HEADING = i18n.msg(
    "health.no_flights_in_the_last_days", "No flights in the last %d days")
_NO_STATS_BODY = i18n.msg(
    "health.the_frame_has_not_recorded_a_detection_in_this",
    "The frame has not recorded a detection in this window. It will "
    "appear here after the next wake.")

# Only the event count varies between these templates; the day count is
# always RESOLUTION_WINDOW_DAYS, so a "1 day" singular form would be
# dead copy. Singular chosen at the call site, never a runtime "add an
# s" rule, which French cannot express (it pluralises the noun and
# needs article agreement too).
_RESOLUTION_DETAIL_TEMPLATE = i18n.msg(
    "health.over_the_last_days_events", "over the last %d days, %d events")
_RESOLUTION_DETAIL_SINGULAR_TEMPLATE = i18n.msg(
    "health.over_the_last_days_event", "over the last %d days, %d event")

RESOLUTION_WINDOW_DAYS = 30  # A month smooths over a quiet week at this
# single-airport traffic volume, while still reading as "recent".

# The four categories server/plane/enrich.py's resolve_route() documents,
# plus a fifth ("manual", an operator answering by hand at runtime from
# this companion web interface), in a fixed display order with a
# plain-English gloss so the page is readable without the source. The
# live/cache/static-table distinction is kept deliberately: collapsing
# it would hide which mechanism actually resolved the route.
_SOURCE_ROWS = (
    ("fresh_hit", i18n.msg("health.fresh_lookup", "Fresh lookup"),
     i18n.msg(
         "health.a_live_lookup_in_the_route_database_resolved_a",
         "A live lookup in the route database resolved a full route this cycle.")),
    ("cache_hit", i18n.msg("health.cached_hit", "Cached hit"),
     i18n.msg(
         "health.a_previously_cached_route_was_reused_sparing_a",
         "A previously-cached route was reused, sparing a network request.")),
    ("airline_only", i18n.msg("health.airline_only", "Airline only"),
     i18n.msg(
         "health.the_route_database_had_no_route_but_the",
         "The route database had no route, but the callsign's ICAO prefix "
         "identified the airline from the static prefix table.")),
    ("miss", i18n.msg("health.miss", "Miss"),
     i18n.msg(
         "health.neither_the_route_database_nor_the_static",
         "Neither the route database nor the static prefix table resolved "
         "anything for this callsign, so it shows up in the %s list above."
         % UNRESOLVED_SECTION_HEADING)),
    ("manual", i18n.msg("health.manual", "Manual"),
     i18n.msg(
         "health.the_operator_resolved_this_callsign_s_prefix_by",
         "The operator resolved this callsign's prefix by hand, from the "
         "companion web interface.")),
)

# A sixth, catch-all row for any route_source value outside the five
# above; folded in rather than dropped from the total. Kept out of
# _SOURCE_ROWS itself: that tuple is the fixed, ordered enumeration of
# known mechanisms, and folding an "unknown" bucket into it would
# misrepresent it as a sixth understood mechanism.
_OTHER_SOURCE_LABEL = i18n.msg("health.other", "Other")
_OTHER_SOURCE_GLOSS = i18n.msg(
    "health.a_route_source_this_page_does_not_recognise_or",
    "A route source this page does not recognise, or none was recorded "
    "at all — still counted here so the total always matches every "
    "event in the window.")

# Single-sourced so the table and the mobile card list can never
# disagree on a header word. Index 2 ("Count") is read directly by the
# card builder; "Description" has no card-side equivalent, since the
# mobile card renders the full description as stacked prose.
_STATS_HEADERS = (
    i18n.msg("health.source", "Source"),
    i18n.msg("health.description", "Description"),
    i18n.msg("health.count", "Count"),
)

# Driven client-side by list-filter.js's data-filter-* attribute
# contract. No hyphen in this value: see history_page.py's own
# `_FILTER_INPUT_ID` comment for the WebKit/Safari contacts-autofill
# explanation.
_FILTER_INPUT_ID = "airlines_filter_input"
_FILTER_LABEL_TEXT = i18n.msg("health.filter_by_prefix", "Filter by prefix")
_FILTER_EMPTY_HEADING = i18n.msg("health.no_matching_prefixes", "No matching prefixes")
_FILTER_EMPTY_BODY_TEMPLATE = i18n.msg(
    "health.try_a_different_search_or_clear_filter_to_see",
    "Try a different search, or Clear filter to see all %d prefixes.")

# Inline literals hoisted from the markup builders below, one constant
# per distinct English string. "More details" is shared by four
# disclosure summaries; "%d of %d shown" and "Clear" are also read by
# history_page.py/airlines_page.py's own filter bars (declared there
# too, with the same id — msg() is idempotent on a repeat pair).
_LATEST_READINGS_TEMPLATE = i18n.msg("health.latest_readings", "Latest %d readings")
_NO_BATTERY_READINGS_YET_TEXT = i18n.msg(
    "health.no_battery_readings_yet", "No battery readings yet.")
_NO_BATTERY_TELEMETRY_RECORDED_TEXT = i18n.msg(
    "health.no_battery_telemetry_recorded_yet_check_back",
    "No battery telemetry recorded yet — check back after the "
    "device's next poll.")
_TIMESTAMP_TEXT = i18n.msg("health.timestamp", "Timestamp")
_BATTERY_MV_TEXT = i18n.msg("health.battery_mv", "Battery (mV)")
_VIEW_READING_TEMPLATE = i18n.msg("health.view_reading", "View %d reading%s")
_MORE_DETAILS_TEXT = i18n.msg("health.more_details", "More details")
_NOTHING_TO_COMPARE_YET_TEXT = i18n.msg(
    "health.nothing_to_compare_yet", "Nothing to compare yet.")
_FILTER_COUNT_TEMPLATE = i18n.msg("health.of_shown", "%d of %d shown")
_CLEAR_TEXT = i18n.msg("health.clear", "Clear")
_RESOLVED_PCT_TEMPLATE = i18n.msg("health.1f_resolved", "%.1f%% resolved")
_OFFBOX_UP_TO_DATE_TEXT = i18n.msg(
    "health.off_box_backup_up_to_date", "Off-box backup up to date")
_OFFBOX_OVERDUE_TEXT = i18n.msg("health.off_box_backup_overdue", "Off-box backup overdue")
_LAST_OFFBOX_BACKUP_TEXT = i18n.msg("health.last_off_box_backup", "Last off-box backup")
_NEVER_TEXT = i18n.msg("health.never", "never")
_OFFBOX_BACKUP_TEXT = i18n.msg("health.off_box_backup", "Off-box backup")
# Owned by companion/i18n_fr/nav.py, not health.py — the same id the
# nav tab label uses.
_NAV_HEALTH_TEXT = i18n.msg("nav.health", "Health")

# The DB-unavailable sentinel, the safe-query/cutoff/meta-flag helpers,
# staleness_status(), offbox_backup_status() and the battery query
# functions all live in companion/health_signals.py now — re-exported
# here under their historical names. `_DB_UNAVAILABLE` in particular is
# re-exported rather than redefined: an `is _DB_UNAVAILABLE` check must
# resolve to the SAME object health_signals.py's own functions return.
_DB_UNAVAILABLE = health_signals_module._DB_UNAVAILABLE
_safe_query = health_signals_module._safe_query
_cutoff_iso = health_signals_module._cutoff_iso
_meta_flag_true = health_signals_module._meta_flag_true
staleness_status = health_signals_module.staleness_status
offbox_backup_status = health_signals_module.offbox_backup_status
battery_trend_rows = health_signals_module.battery_trend_rows
battery_daily_rows = health_signals_module.battery_daily_rows
_battery_daily_series_usable = health_signals_module._battery_daily_series_usable
_real_trend_reading_count = health_signals_module._real_trend_reading_count


# _battery_trend_caption() lives in companion/health_signals.py now
# (pure text, no markup) — re-exported here for _battery_section()'s and
# health_state_from_signals()'s own use as a bare name.
_battery_trend_caption = health_signals_module._battery_trend_caption

# The chart's geometry, size constants and markup builder all live in
# companion/battery_chart.py (built on companion/draw.py); re-exported
# here under their historical names, since a number of tests reach these
# by name as `health_page.X` and `_battery_readout_block()`/
# `_battery_section()` below call some of them as bare names.
_SPARKLINE_CANVAS_HEIGHT_PX = battery_chart._SPARKLINE_CANVAS_HEIGHT_PX
_SPARKLINE_VERTICAL_INSET_PERCENT = battery_chart._SPARKLINE_VERTICAL_INSET_PERCENT
SPARKLINE_Y_MIN_MV = battery_chart.SPARKLINE_Y_MIN_MV
SPARKLINE_Y_MAX_MV = battery_chart.SPARKLINE_Y_MAX_MV
_SPARKLINE_DOT_RADIUS_PX = battery_chart._SPARKLINE_DOT_RADIUS_PX
_SPARKLINE_HIT_RADIUS_PX = battery_chart._SPARKLINE_HIT_RADIUS_PX
_SPARKLINE_MARK_RADIUS_PX = battery_chart._SPARKLINE_MARK_RADIUS_PX
_SPARKLINE_NARROWEST_CANVAS_PX = battery_chart._SPARKLINE_NARROWEST_CANVAS_PX
_sparkline_dense_threshold = battery_chart._sparkline_dense_threshold
_SPARKLINE_DENSE_POINT_THRESHOLD = battery_chart._SPARKLINE_DENSE_POINT_THRESHOLD
_SPARKLINE_DENSE_HIT_RADIUS_PX = battery_chart._SPARKLINE_DENSE_HIT_RADIUS_PX
sparkline_point_y = battery_chart.sparkline_point_y
BATTERY_AVERAGE_WHEN_ONE_TEMPLATE = battery_chart.BATTERY_AVERAGE_WHEN_ONE_TEMPLATE
BATTERY_AVERAGE_WHEN_MANY_TEMPLATE = battery_chart.BATTERY_AVERAGE_WHEN_MANY_TEMPLATE
BATTERY_AVERAGE_WHEN_BARE_TEMPLATE = battery_chart.BATTERY_AVERAGE_WHEN_BARE_TEMPLATE
BATTERY_THRESHOLD_LABEL_TEMPLATE = battery_chart.BATTERY_THRESHOLD_LABEL_TEMPLATE
_FULL_TIMESTAMP_SENTINEL_NOW = battery_chart._FULL_TIMESTAMP_SENTINEL_NOW
_full_local_timestamp_text = battery_chart._full_local_timestamp_text
_as_paris = battery_chart._as_paris
_axis_clock_label = battery_chart._axis_clock_label
_axis_day_label = battery_chart._axis_day_label
_battery_reading_parts = battery_chart._battery_reading_parts
_daily_reading_parts = battery_chart._daily_reading_parts
battery_sparkline_svg = battery_chart.battery_sparkline_svg


# The severity/anomaly/state functions (battery_status() through
# safe_health_signals()) all live in companion/health_signals.py now —
# re-exported here under their historical names, since this module's own
# markup builders below (_device_section(), _pipeline_section(), ...)
# call several of them as bare names, and a number of tests read them as
# `health_page.X`.
battery_status = health_signals_module.battery_status
corroboration_status = health_signals_module.corroboration_status
_offbox_anomaly_text = health_signals_module._offbox_anomaly_text
collect_anomalies = health_signals_module.collect_anomalies
overall_severity = health_signals_module.overall_severity
_device_resolved_state = health_signals_module._device_resolved_state
_device_state = health_signals_module._device_state
_pipeline_never_ran = health_signals_module._pipeline_never_ran
_pipeline_state = health_signals_module._pipeline_state
_battery_state = health_signals_module._battery_state
_disagreement_warn = health_signals_module._disagreement_warn
health_signals = health_signals_module.health_signals
safe_health_signals = health_signals_module.safe_health_signals


def health_state_from_signals(signals):
    """Builds every `*_html` value and `battery_caption` from
    `signals["inputs"]` (a `health_signals()` snapshot), and returns
    exactly `compute_health_state()`'s historical key set. Every state,
    `severity` and `anomalies` value is copied straight from `signals`,
    never recomputed here — each `_x_section()` builder is still called
    (for its markup), but its own returned state is discarded in favour
    of the snapshot's, so the nav-tab dot and this page's own banner can
    never disagree.
    """
    now = signals["now"]
    inputs = signals["inputs"]
    device_html, _device_state_unused = _device_section(
        inputs["device_health"], now, warn_s=signals["warn_s"], error_s=signals["error_s"],
        next_wake_iso=signals["next_wake_iso"],
        effective_interval_s=signals["effective_interval_s"],
        hold_reason=signals["hold_reason"])
    device_detail_html = _device_timestamp_only(inputs["device_health"], now)
    pipeline_html, _pipeline_state_unused = _pipeline_section(
        inputs["pipeline_ts"], inputs["last_detection"], now)
    pipeline_detail_html = _pipeline_timestamp_only(
        inputs["pipeline_ts"], inputs["last_detection"], now)
    battery_html, _battery_state_unused = _battery_section(
        inputs["trend_rows"], inputs["daily_rows"])
    # Threaded through the returned dict rather than as a third
    # _battery_section() return value: that function's 2-tuple return is
    # directly unpacked by a pinned harness check.
    battery_caption = _battery_trend_caption(inputs["trend_rows"], inputs["daily_rows"])
    corroboration_html, _disagreement_warn_unused = _corroboration_section(
        inputs["corroboration_counts"])
    return {
        "now": now,
        "source_fault_raw": signals["source_fault_raw"],
        "registry_rows": signals["registry_rows"],
        # render() reuses this rather than reading the marker a second
        # time per request.
        "offbox": signals["offbox"],
        # The cadence the Device tile's thresholds were derived from,
        # published so render()'s regularity grid judges its cells
        # against the same value and can name it.
        "wake_interval_s": signals["wake_interval_s"],
        "device_html": device_html,
        "device_state": signals["device_state"],
        "device_detail_html": device_detail_html,
        "pipeline_html": pipeline_html,
        "pipeline_state": signals["pipeline_state"],
        "pipeline_detail_html": pipeline_detail_html,
        "battery_html": battery_html,
        "battery_state": signals["battery_state"],
        "battery_caption": battery_caption,
        "corroboration_html": corroboration_html,
        "disagreement_warn": signals["disagreement_warn"],
        "anomalies": signals["anomalies"],
        "severity": signals["severity"],
    }


def compute_health_state(state_dir, now=None):
    """The single computation both the nav-tab dot and the full Health
    page need. Running these independently against fresh DB connections
    at two different instants let a write land between them and make
    the two disagree; `build_page_context()` now calls this once per
    request and threads the result through `ctx.health_state`.

    Composed from exactly one `health_signals()` snapshot fed into
    `health_state_from_signals()`, so the severity `safe_health_signals()`
    could hand the nav dot and the banner this page renders always come
    from the same read.
    """
    return health_state_from_signals(health_signals(state_dir, now))


def safe_health_state(state_dir, now=None):
    """Fail-closed wrapper around `compute_health_state()`: `None` on any
    unanticipated exception, never a raise. Broad `except Exception`,
    unlike the narrow `(sqlite3.Error, OSError)` catches elsewhere in
    this file: this function runs on every authenticated page render, so
    a raise here would 500 every page over a decorative nav dot.
    Callers treat `None` as "ok" (fail closed — the Health page itself
    still reports the real problem in full); `render()` falls back to a
    fresh compute rather than a dict with missing keys.
    """
    try:
        return compute_health_state(state_dir, now)
    except Exception:
        return None


def _starts_with_acronym(phrase):
    """True when `phrase`'s first word carries a capital letter after its
    first character — an acronym ("ADS-B", "RER") rather than an
    ordinary sentence-initial word ("Device"). Used by
    `_anomaly_category_text()` to decide whether a phrase's leading
    letter may be safely lower-cased for mid-sentence joining.
    """
    first_word = phrase.split(" ", 1)[0]
    return any(character.isupper() for character in first_word[1:])


def _anomaly_category_text(anomalies):
    """A comma-joined, human-readable naming of `anomalies`
    (`collect_anomalies()`'s own literal strings, in order), so the
    banner names its real failing category rather than a generic
    message. Each item's trailing period is dropped, and every item
    after the first is lower-cased for mid-sentence joining — except a
    phrase whose first word is an acronym like "ADS-B", which would
    otherwise mangle into "aDS-B".
    """
    phrases = []
    for index, anomaly in enumerate(anomalies):
        phrase = anomaly.rstrip(".")
        if index > 0 and phrase and not _starts_with_acronym(phrase):
            phrase = phrase[0].lower() + phrase[1:]
        phrases.append(phrase)
    return ", ".join(phrases)


def _anomaly_category_labels(anomalies):
    """One short pill label per `anomalies` entry, the pill-shaped
    counterpart to `_anomaly_category_text()`'s comma-joined clause.
    Strips the trailing period but never lower-cases: a pill is not
    mid-sentence text, so it keeps its original, sentence-initial case.
    """
    return [anomaly.rstrip(".") for anomaly in anomalies]


def _anomaly_banner_html(severity, anomalies):
    """Builds the anomaly banner directly rather than through
    `layout.anomaly_banner()`, which escapes its message as one
    plain-text string, incompatible with a `<span class="banner__pill">`
    per failing category. Emits a count-and-noun label, one pill per
    category, and a `<span class="visually-hidden">` tail carrying the
    original comma-joined sentence, so a screen reader gets one coherent
    sentence rather than disconnected pills.
    """
    css_class = "banner--anomaly" if severity == "error" else "banner--warn"
    role = "alert" if severity == "error" else "status"
    noun = i18n.t(_SEVERITY_BANNER_NOUNS.get(severity, _SEVERITY_BANNER_ISSUE_TEXT))
    count = len(anomalies)
    plural = "" if count == 1 else "s"
    lead_html = '<span class="banner__label">%s</span>' % escape_html(
        _label_colon("%d %s%s" % (count, noun, plural)))
    pills_html = "".join(
        '<span class="banner__pill">%s</span>' % escape_html(label)
        for label in _anomaly_category_labels(anomalies)
    )
    tail_text = "%s — %s" % (_anomaly_category_text(anomalies), i18n.t(ANOMALY_BANNER_TEXT))
    tail_html = '<span class="visually-hidden">%s</span>' % escape_html(tail_text)
    return '<div class="banner %s" role="%s">%s%s%s</div>' % (
        css_class, role, lead_html, pills_html, tail_html)


def _unavailable_block():
    return '<p class="text-body">%s</p>' % escape_html(i18n.t(HEALTH_UNAVAILABLE_TEXT))


# Every .stat-tile on this page renders the same four slots, in order:
# label (stat_tile()'s own caption), verdict (Emphasis role, exactly
# once), detail (muted, carrying different information from the
# verdict), optional link. The Resolution-rate tile is the one
# exception: it makes no pass/fail judgement (status=None, no status
# function exists), so its Emphasis slot carries the figure instead of
# a verdict sentence; do not give it a .widget-verdict paragraph.
_TILE_VERDICT_CLASS = "text-body widget-verdict"
_TILE_DETAIL_CLASS = "text-label widget-detail"


def _tile_body(verdict_html, detail_html, link_html=""):
    """Assembles one Health tile's verdict/detail/link slots in the fixed
    order above. Both arguments are the caller's own already-safe
    markup, interpolated verbatim, never re-escaped. The detail is a
    `<div>`, not a `<p>`: some tiles' detail spans multiple lines or a
    `<details>` disclosure, and wrapping all of them in one element
    keeps "exactly one detail slot" a checkable property.
    """
    html = '<p class="%s">%s</p>' % (_TILE_VERDICT_CLASS, verdict_html)
    html += '<div class="%s">%s</div>' % (_TILE_DETAIL_CLASS, detail_html)
    if link_html:
        html += '<p class="stat-tile__link">%s</p>' % link_html
    return html


def _device_timestamp_only(device_health, now):
    """The timestamp-only half of `_device_section()`'s return value, no
    verdict paragraph. Published as `"device_detail_html"` on the
    health-state dict: Home's status card renders its own Frame verdict
    and takes only this fragment for its detail slot, so the verdict
    sentence is never rendered twice. `_pipeline_timestamp_only()` is
    the same pattern for the pipeline signal. `_device_section()` calls
    this helper for its own second half, so the two outputs can't drift.
    """
    if device_health is _DB_UNAVAILABLE:
        return _unavailable_block()
    ts = (device_health or {}).get("ts")
    return layout.concise_timestamp_html(ts, now)


def _device_section(
        device_health, now, warn_s=None, error_s=None,
        next_wake_iso=None, effective_interval_s=None, hold_reason=None):
    """`warn_s`/`error_s` are the device's cadence-derived staleness
    thresholds, computed once upstream and threaded through, so the
    Device tile and the anomaly banner can't disagree on "stale".
    `next_wake_iso`/`effective_interval_s`/`hold_reason` are
    `wake.next_wake_status()`'s triple; `frame_state.resolve_state()` is
    the one decision on due/held/late, with the staleness thresholds
    kept only as the `STATE_UNKNOWN` fallback. A held frame routes to
    the neutral "off" state, never lighting the nav dot, bounded since
    `resolve_state()` reverts to "late" once its grace window elapses.
    """
    if device_health is _DB_UNAVAILABLE:
        return _unavailable_block(), "ok"
    if warn_s is None or error_s is None:
        warn_s, error_s = wake.device_staleness_thresholds(None)
    resolved_state = _device_resolved_state(
        next_wake_iso, effective_interval_s, hold_reason, now)
    state = _device_state(
        device_health, now, warn_s=warn_s, error_s=error_s,
        next_wake_iso=next_wake_iso, effective_interval_s=effective_interval_s,
        hold_reason=hold_reason)
    if resolved_state == frame_state.STATE_UNKNOWN:
        detail = _device_timestamp_only(device_health, now)
    else:
        next_wake_parsed = layout.parse_iso(next_wake_iso)
        next_wake_clock = layout.local_clock_text(next_wake_parsed, now_parsed=layout.parse_iso(now))
        # The base .time-value role (not .time-value--primary, which is
        # the Emphasis shape used on the Frame strip's own headline):
        # this tile already carries a verdict in the Emphasis role above.
        detail = '<span class="time-value">%s</span>' % escape_html(next_wake_clock)
    # No status dot: stat_tile()'s own caption already names the signal
    # (DEVICE_FRESHNESS_LABEL), so a body-row dot label would repeat it.
    # The status-coloured border and icon tint still come from `state`,
    # and collect_anomalies() still names a stale device in the banner.
    #
    # The widget-verdict paragraph states the judgement on the signal;
    # the timestamp row gives the raw detail backing it — distinct
    # rungs, not a repeat of the caption.
    return _tile_body(
        escape_html(i18n.t(DEVICE_STATE_TEXT.get(state, DEVICE_STATE_TEXT["warn"]))),
        detail), state


def _pipeline_timestamp_only(pipeline_ts, last_detection, now):
    """The verdict-free half of `_pipeline_section()`'s return value,
    mirroring `_device_timestamp_only()`. Published as
    `"pipeline_detail_html"`: Home reads this instead of re-embedding
    `pipeline_html` wholesale, so the verdict sentence is never rendered
    twice. Returns `PIPELINE_NEVER_RAN_DETAIL_TEXT` when the pipeline has
    never run, rather than falling through to
    `concise_timestamp_html(None, now)`'s battery-vocabulary fallback.
    """
    if pipeline_ts is _DB_UNAVAILABLE:
        return _unavailable_block()
    if _pipeline_never_ran(pipeline_ts, last_detection):
        return escape_html(i18n.t(PIPELINE_NEVER_RAN_DETAIL_TEXT))
    return layout.concise_timestamp_html(pipeline_ts, now)


def _pipeline_section(pipeline_ts, last_detection, now):
    if pipeline_ts is _DB_UNAVAILABLE:
        return _unavailable_block(), "ok"
    # Computed once here, through the state-only sibling, so this tile
    # and the nav-dot severity path can never derive different verdicts
    # from the same inputs.
    state = _pipeline_state(pipeline_ts, last_detection, now)
    if _pipeline_never_ran(pipeline_ts, last_detection):
        # "off" is the app's existing token for a state that is not a
        # problem: no "off" entry in _STAT_TILE_BORDER_CLASSES falls
        # through to the neutral default border, and
        # collect_anomalies()/overall_severity() treat "off" like "ok".
        # The dot is hand-built rather than status_dot(): this verdict's
        # text is the paragraph's own content, not a dot-label span.
        verdict_html = (
            '<span class="dot dot--off"></span>%s'
            % escape_html(i18n.t(PIPELINE_STATE_TEXT["off"])))
        detail = _pipeline_timestamp_only(pipeline_ts, last_detection, now)
        # No second "Last aircraft detected" line: last_detection is
        # falsy by definition here, so PIPELINE_NEVER_RAN_DETAIL_TEXT
        # above already says so without repeating it.
        return _tile_body(verdict_html, detail), state
    verdict = escape_html(
        i18n.t(PIPELINE_STATE_TEXT.get(state, PIPELINE_STATE_TEXT["warn"])))
    detail = _pipeline_timestamp_only(pipeline_ts, last_detection, now)
    # last_detection is read inside the same atomic snapshot pipeline_ts
    # comes from. Rendered unconditionally here (pipeline_ts is truthy):
    # concise_timestamp_html() falls back to "no reading yet" when
    # last_detection is falsy, giving an honest line either way. Not
    # .battery-readout__detail: two regression guards assert that class
    # is absent whenever there is no battery reading, and this tile
    # renders unconditionally.
    detection_detail = layout.concise_timestamp_html(last_detection, now)
    detail_row = (
        '<p class="stat-tile__meta text-label section-caption">%s %s</p>'
        % (escape_html(_label_colon(i18n.t(LAST_DETECTION_LABEL))), detection_detail))
    # Both lines live inside the one detail slot: the tile anatomy has
    # exactly one detail slot, so line count is the slot's content, not
    # the tile's shape.
    return _tile_body(verdict, detail + detail_row), state


# _latest_numeric_battery_reading() lives in companion/health_signals.py
# now (pure data, no markup) — re-exported here for _battery_section()'s
# own use as a bare name.
_latest_numeric_battery_reading = health_signals_module._latest_numeric_battery_reading


def _battery_readout_block(latest_reading, now):
    """The reserved-height readout `battery-trend.js` writes into on
    hover/tap/keyboard reveal, seeded by default with `latest_reading`'s
    humanised `(value, when)` pair, the same helper
    `battery_sparkline_svg()` uses per-point. `role="status"` already
    implies a polite live region. Two spans, not one string, since
    `reveal()` writes the value and detail parts separately; `.time-value`
    sits on the stable wrapper span because `reveal()` overwrites
    `textContent`, never `class`.
    """
    if latest_reading is None:
        value_text, when_text = "", ""
    else:
        mv, ts = latest_reading
        value_text, when_text = _battery_reading_parts(mv, ts, now)
    return (
        '<p id="%s" class="battery-readout" role="status">'
        '<span class="battery-readout__value mono">%s</span>'
        '<span class="battery-readout__detail time-value" title="%s"> — %s</span>'
        "</p>"
    ) % (
        BATTERY_READOUT_ID, escape_html(value_text),
        escape_html(when_text), escape_html(when_text))


# The large ring's box side, in CSS pixels; the small one lives in
# home_page.py, kept separate rather than a shared "sizes" table, since
# they are independent numbers, not variants of one drawing.
# 72px against this card's 312px content width at the 360px floor still
# leaves room for the readout beside it on the same reserved line count.
BATTERY_RING_SIZE = 72


def _battery_ring_html(latest_reading, state):
    """The battery ring for `latest_reading`, or "" when there is
    nothing honest to draw (an empty ring would read as a false "0%").
    The fraction is the printed percentage divided by 100, not a second
    finer-grained estimate, so the arc can't draw 43.4% while the text
    says 43%. Colour comes from `state`, already computed for the card
    edge, never a second judgement.
    """
    if not latest_reading:
        return ""
    mv, _ts = latest_reading
    percent = battery.battery_percent(mv)
    if percent is None:
        return ""
    return draw.ring_gauge(
        percent / 100.0, BATTERY_RING_SIZE, draw.status_class(state))


def _battery_readout_row_html(latest_reading, now, state):
    """The readout, with the ring beside it when there is one. With no
    ring this returns `_battery_readout_block()`'s markup unwrapped, so
    the no-reading page renders identically to before the ring existed.
    The ring comes first in document order; `battery-trend.js` finds the
    readout by `getElementById` and never depends on its position.
    """
    readout_html = _battery_readout_block(latest_reading, now)
    ring_html = _battery_ring_html(latest_reading, state)
    if not ring_html:
        return readout_html
    return '<div class="battery-readout-row">%s%s</div>' % (ring_html, readout_html)


def _battery_trend_section_html(battery_html, state, caption=None):
    """Wraps `_battery_section()`'s already-built markup in the
    full-width `BATTERY_SECTION_CLASS` card section. `battery_html` is
    already-safe markup, interpolated verbatim with no `escape_html()`
    call. The `<h2>` carries only its short, fixed heading text; the
    caption sits in a sibling `<p>`, so the heading never carries its
    own qualification. `state` composes onto the section's class, so
    the card's top edge carries `battery_status()`'s verdict.
    """
    modifier = layout.card_status_class(BATTERY_SECTION_CLASS, state)
    section_class = BATTERY_SECTION_CLASS + ((" " + modifier) if modifier else "")
    caption_text = caption if caption is not None else (i18n.t(_LATEST_READINGS_TEMPLATE) % BATTERY_TREND_LIMIT)
    heading_text = i18n.t(BATTERY_SECTION_HEADING_TEMPLATE) % (BATTERY_TREND_WINDOW_DAYS // 30)
    return (
        '<section class="%s">'
        '<h2 class="text-heading">%s</h2>'
        '<p class="text-label section-caption">%s</p>'
        "%s"
        "</section>"
    ) % (
        section_class,
        escape_html(heading_text), escape_html(caption_text), battery_html)


def _battery_section(trend_rows, daily_rows=None):
    """Returns `(markup, state)` for the Battery trend tile. `state`
    drives both the card-edge status modifier and
    `collect_anomalies()`'s abnormal-drop signal. The chart plots
    `daily_rows` when there are enough buckets, else falls back to raw
    `trend_rows`; the anomaly scan and readout always read `trend_rows`,
    since averaging would hide the abnormal drop the scan exists to
    catch. Empty history returns `"ok"`, not `"warn"`: an absence of
    readings must not make `collect_anomalies()` assert a drop that
    never happened.
    """
    if trend_rows is _DB_UNAVAILABLE:
        return _unavailable_block(), "ok"
    if not trend_rows:
        return layout.empty_state(
            i18n.t(_NO_BATTERY_READINGS_YET_TEXT),
            i18n.t(_NO_BATTERY_TELEMETRY_RECORDED_TEXT)), "ok"
    # Through the state-only sibling, not a bare battery_status() call:
    # keeps this tile's border colour and health_signals()'s severity
    # input reading identically from the same two early-exit cases.
    state = _battery_state(trend_rows, daily_rows)
    now = history_db.utc_now_iso()
    # The Timestamp column is already-safe raw HTML (a concise
    # Europe/Paris span with the full timestamp demoted to `title`), so
    # raw_columns=(0,) tells data_table() not to re-escape it.
    table_rows = [
        (layout.concise_timestamp_html(row.get("ts"), now, fallback=""), row.get("battery_mv"))
        for row in trend_rows
    ]
    # modifier="readings" scopes the stylesheet rule that releases this
    # table from .data-table's min-width: max-content no-crop floor: at
    # 390px the floor sized this two-column table wider than its wrap.
    table_html = layout.data_table(
        [i18n.t(_TIMESTAMP_TEXT), i18n.t(_BATTERY_MV_TEXT)], table_rows,
        mono_columns=(1,), raw_columns=(0,), modifier="readings")
    # Collapsed behind a closed-by-default native <details> disclosure —
    # no custom JS toggler needed.
    disclosure_html = (
        '<details class="readings-disclosure"><summary>%s</summary>%s</details>'
        % (
            escape_html(i18n.t(_VIEW_READING_TEMPLATE) % (
                len(trend_rows), "" if len(trend_rows) == 1 else "s")),
            table_html))
    # One predicate decides both the series and the label mode passed to
    # battery_sparkline_svg(), so they can never disagree.
    plot_daily = _battery_daily_series_usable(daily_rows)
    plot_rows = daily_rows if plot_daily else trend_rows
    sparkline_html = (
        battery_sparkline_svg(plot_rows, now=now, daily=plot_daily)
        if len(plot_rows) >= 2 else "")
    # Script tag and readout emit only when a chart exists, keeping
    # "exactly one script tag, zero on the empty path" testable.
    chart_block = ""
    if sparkline_html:
        latest_reading = _latest_numeric_battery_reading(trend_rows)
        chart_block = (
            _battery_readout_row_html(latest_reading, now, state)
            + sparkline_html
            + '<script src="%s" defer></script>' % BATTERY_TREND_SCRIPT_SRC)
    # The chart, when present, comes before the collapsed table in both
    # DOM and visual order.
    return chart_block + disclosure_html, state


def _corroboration_details_html():
    """A collapsed `<details class="readings-disclosure">` block holding
    each `_CORROBORATION_ROWS` entry's full explanation, closed by
    default: the same idiom the battery readings table already uses.
    """
    dl_items = "".join(
        "<dt>%s</dt><dd>%s</dd>" % (escape_html(i18n.t(label)), escape_html(i18n.t(explanation)))
        for _key, label, _status, explanation in _CORROBORATION_ROWS
    )
    return (
        '<details class="readings-disclosure"><summary>%s</summary>'
        "<dl>%s</dl></details>" % (escape_html(i18n.t(_MORE_DETAILS_TEXT)), dl_items)
    )


def _corroboration_section(counts):
    """`(tile_body_markup, disagreement_warn)` for the Corroboration tile.
    Builds the whole tile body, verdict included, since the verdict and
    the three rows are one composition. `render()` derives the tile's
    border colour from the returned `disagreement_warn` flag, so word
    and border are keyed on one value and cannot disagree.
    """
    if counts is _DB_UNAVAILABLE:
        return _unavailable_block(), False
    counts = counts or {}
    if not any(counts.values()):
        # Compact variant: this renders inside a .stat-tile whose 12px
        # caption inverts under the default form's 22px heading. Not
        # wrapped in _tile_body() — that would add a second verdict
        # element; the compact form already emits the same
        # widget-verdict/widget-detail pair.
        return layout.empty_state(
            i18n.t(_NOTHING_TO_COMPARE_YET_TEXT),
            i18n.t(
                "This appears once the frame has recorded at least one "
                "flight."),
            compact=True), False

    statuses = corroboration_status(counts)
    rows_html = []
    for key, label, _default_state, _explanation in _CORROBORATION_ROWS:
        rows_html.append(
            '<p class="text-body">%s <span class="mono">%d</span></p>'
            % (
                layout.status_dot(statuses[key], i18n.t(label)),
                counts.get(key, 0) or 0,
            )
        )
    # Through the state-only sibling so this tile's flag and
    # health_signals()'s copy of it can never diverge.
    disagreement_warn = _disagreement_warn(counts)
    verdict_state = "warn" if disagreement_warn else "ok"
    verdict = escape_html(
        i18n.t(CORROBORATION_STATE_TEXT.get(
            verdict_state, CORROBORATION_STATE_TEXT["ok"])))
    body = _tile_body(verdict, "".join(rows_html) + _corroboration_details_html())
    return body, disagreement_warn


def _source_fault_block(source_fault_raw):
    # Not given page-section--nested: this block renders above both
    # id-anchored sections, at the same structural level as their own
    # headings, not nested inside one.
    if source_fault_raw is _DB_UNAVAILABLE:
        return ""
    if not _meta_flag_true(source_fault_raw):
        return ""
    body = i18n.t(SOURCE_FAULT_BODY_TEMPLATE) % ", ".join(_ADSB_PROVIDER_NAMES)
    return (
        '<section class="page-section banner banner--anomaly">'
        '<h2 class="text-heading">%s</h2>'
        '<p class="text-body">%s</p>'
        "</section>"
    ) % (escape_html(i18n.t(SOURCE_FAULT_HEADING)), escape_html(body))


# The unresolved-prefix registry read goes through
# state_store.load_poll_state() (filesystem/JSON failure mode), and the
# stats read goes through _safe_query() (SQLite failure mode) — render()
# calls both independently so one failing source degrades only its own
# card.


# unresolved_rows() and coverage_status() live in
# companion/health_signals.py now (read by both health_signals() and
# render()/the registry section below) — re-exported under their
# historical names.
unresolved_rows = health_signals_module.unresolved_rows
coverage_status = health_signals_module.coverage_status


def resolution_stats(conn, window_days=RESOLUTION_WINDOW_DAYS, now=None):
    """Windowed resolution-rate breakdown, mapped onto `_SOURCE_ROWS`'s
    categories. Resolved percentage is the share that produced any
    usable route (everything except `"miss"`); real traffic measured
    around 52.6%, so that region is expected, not a defect. Returns
    `{"rows": [...], "total": N, "resolved_pct": float_or_None}`;
    `resolved_pct` is `None` when `total` is zero. `total` counts every
    row in the window, folding an unrecognised `route_source` into
    `_OTHER_SOURCE_LABEL` rather than dropping it.
    """
    now_dt = now or datetime.now(timezone.utc)
    since = (now_dt - timedelta(days=window_days)).isoformat(timespec="seconds")
    counts = history_db.route_source_counts(conn, since=since)

    total = sum(counts.values())
    if total == 0:
        return {"rows": [], "total": 0, "resolved_pct": None}

    resolved = total - counts.get("miss", 0)
    resolved_pct = round((resolved / total) * 100, 1)
    # label/gloss are translated here, the one place both
    # _stats_cards_html() and _stats_table_html() read them from.
    rows = [
        (i18n.t(label), i18n.t(gloss), counts.get(source, 0))
        for source, label, gloss in _SOURCE_ROWS
    ]
    known_sources = {source for source, _label, _gloss in _SOURCE_ROWS}
    other_count = sum(
        n for source, n in counts.items() if source not in known_sources)
    if other_count:
        rows.append((
            i18n.t(_OTHER_SOURCE_LABEL), i18n.t(_OTHER_SOURCE_GLOSS), other_count))
    return {"rows": rows, "total": total, "resolved_pct": resolved_pct}


def _registry_filter_bar_html(total):
    """Filter bar over the unresolved-prefix registry, only rendered when
    there is data to filter. The count and Clear control share one
    `.filter-bar__meta` flex item, since two `nowrap` siblings in a
    `flex-wrap: wrap` container can still break apart from each other.
    The clear control is a plain link (no `<button>` on this page)
    pointing at the filter input's id, which both scrolls to and focuses
    it via fragment navigation.
    """
    count_text = i18n.t(_FILTER_COUNT_TEMPLATE) % (total, total)
    empty_body = i18n.t(_FILTER_EMPTY_BODY_TEMPLATE) % total
    return (
        '<div class="filter-bar">'
        '<label class="text-label" for="%s">%s</label>'
        '<div class="filter-bar__field">'
        "%s"
        # autocomplete/spellcheck/autocapitalize: same Safari
        # contact-autofill fix as history_page.py's _filter_bar_html().
        '<input type="search" id="%s" autocomplete="off" spellcheck="false" autocapitalize="characters" data-filter-input>'
        "</div>"
        '<div class="filter-bar__meta">'
        '<span class="filter-bar__count" data-filter-count>%s</span>'
        '<a href="#%s" data-filter-clear>%s</a>'
        "</div>"
        "</div>"
        '<div class="empty-state" data-filter-empty hidden>'
        '<p class="empty-state__heading text-heading">%s</p>'
        '<p class="empty-state__body text-body">%s</p>'
        "</div>"
    ) % (
        _FILTER_INPUT_ID, escape_html(i18n.t(_FILTER_LABEL_TEXT)),
        layout.icon_html("icon-search"),
        _FILTER_INPUT_ID,
        escape_html(count_text),
        _FILTER_INPUT_ID,
        escape_html(i18n.t(_CLEAR_TEXT)),
        escape_html(i18n.t(_FILTER_EMPTY_HEADING)),
        escape_html(empty_body),
    )


# Single-sourced so the table builder and the mobile card builder can't
# disagree on a header word. Indices 1-4 are read directly by
# _registry_cards_html() for its field labels; index 0 ("Prefix") has no
# card-side label because the prefix is the card's primary line. "Resolve"
# is always appended, never inserted, since those index lookups are
# positional. "Prefix"/"First seen"/"Last seen"/"Example callsign" are
# the same ids airlines_page.py's own RESOLVE_CONTEXT_LABELS uses.
_REGISTRY_HEADERS = (
    i18n.msg("health.prefix", "Prefix"),
    i18n.msg("health.count", "Count"),
    i18n.msg("health.first_seen", "First seen"),
    i18n.msg("health.last_seen", "Last seen"),
    i18n.msg("health.example_callsign", "Example callsign"),
    i18n.msg("health.resolve", "Resolve"),
)

# The per-row deep link to the Airlines resolve surface. Both
# representations (_registry_row_html()'s <td> and
# _registry_cards_html()'s .data-card__action block) build their anchor
# from these same constants, so href/aria-label/text can't drift apart.
RESOLVE_LINK_HREF_TEMPLATE = "/airlines?resolve=%s"
RESOLVE_LINK_ARIA_TEMPLATE = i18n.msg("health.resolve_prefix", "Resolve prefix %s")
RESOLVE_LINK_TEXT = i18n.msg("health.resolve", "Resolve")
RESOLVE_CARD_LINK_TEXT = i18n.msg("health.resolve_this_prefix", "Resolve this prefix")


def _registry_filter_text(prefix):
    """The lowercased, escaped `data-filter-text` value shared by a
    registry `<tr>` (`_registry_row_html()`) and its paired
    `<li class="data-card">` (`_registry_cards_html()`), so the two
    representations' filter text can never diverge.
    """
    return escape_html(prefix.lower() if isinstance(prefix, str) else str(prefix).lower())


# Restated rather than imported from history_page.py: page modules may
# not import each other. display: none inside this table's stacked
# cells, but kept in the DOM in case a future change un-scopes the rule.
_REGISTRY_CELL_SEPARATOR_TEXT = "·"


def _registry_seen_cell_html(raw_ts, now):
    """The First seen / Last seen cell's two stacked lines: a
    Europe/Paris local clock primary line and a relative-age secondary
    line, the same shape `history_page._when_cell_html()` builds for
    Flights' When column. Stacked because the one-line form measured too
    wide for two of six columns to fit unwrapped in French. Degrades
    like `_when_cell_html()`: a falsy timestamp renders empty, an
    unparseable one renders the raw value with no secondary line.

    The secondary line is `layout.relative_time_html()`'s own
    pre-escaped `<time data-relative>` markup, not
    `escape_html(layout.relative_age_text(age))` — interpolated verbatim,
    never re-escaped, so a ticker script can find and update it.
    """
    if not raw_ts:
        return ""
    parsed = layout.parse_iso(raw_ts)
    if parsed is None:
        return '<span class="cell-primary">%s</span>' % escape_html(raw_ts)
    clock_text = layout.local_clock_text(parsed, layout.parse_iso(now))
    age = layout.age_seconds(raw_ts, now)
    html = '<span class="cell-primary" title="%s">%s</span>' % (
        escape_html(_full_local_timestamp_text(raw_ts)), escape_html(clock_text))
    if age is not None:
        html += (
            '<span class="cell-inline-sep">%s</span>'
            '<span class="cell-secondary">%s</span>'
        ) % (
            escape_html(_REGISTRY_CELL_SEPARATOR_TEXT),
            layout.relative_time_html(raw_ts, now))
    return html


def _registry_row_html(index, prefix, count, first_seen, last_seen, example_callsign, now):
    """One `<tr>` for the unresolved-prefix registry table. First
    seen/Last seen return already-safe markup, interpolated verbatim,
    never re-escaped. Appends a sixth `<td>`: a plain `<a>` navigating
    to `/airlines?resolve={prefix}`, never a submit-type control, so
    Health stays read-only.
    """
    row_class = "row-alt" if index % 2 else "row"
    # The desktop table's timestamp cells are stacked (see
    # _registry_seen_cell_html()); the mobile card below keeps calling
    # concise_timestamp_html() directly since it has no width budget to
    # protect. Both still build from the same underlying formatters over
    # the same `now`, so they cannot disagree about what a value is.
    first_seen_html = _registry_seen_cell_html(first_seen, now)
    last_seen_html = _registry_seen_cell_html(last_seen, now)
    escaped_prefix = escape_html(prefix)
    resolve_href = RESOLVE_LINK_HREF_TEMPLATE % escaped_prefix
    resolve_aria = escape_html(i18n.t(RESOLVE_LINK_ARIA_TEMPLATE)) % escaped_prefix
    cells = (
        '<td class="mono">%s</td>' % escaped_prefix,
        "<td>%s</td>" % escape_html(count),
        "<td>%s</td>" % first_seen_html,
        "<td>%s</td>" % last_seen_html,
        '<td class="mono">%s</td>' % escape_html(example_callsign),
        '<td><a href="%s" aria-label="%s">%s</a></td>' % (
            resolve_href, resolve_aria, escape_html(i18n.t(RESOLVE_LINK_TEXT))),
    )
    filter_text = _registry_filter_text(prefix)
    # data-filter-group must match the paired mobile card's value exactly:
    # list-filter.js counts distinct groups, not raw elements, so a
    # mismatch would double "N of N shown" once a row has two DOM forms.
    return '<tr class="%s" data-filter-text="%s" data-filter-group="%d">%s</tr>' % (
        row_class, filter_text, index, "".join(cells))


def _registry_table_html(rows, now):
    """The unresolved-prefix registry table, hand-rolled rather than via
    `layout.data_table()` so each row can carry its own `data-filter-text`
    attribute (that builder has no per-row attribute hook). Matches
    `data_table()`'s CSS classes for visual consistency.
    """
    header_cells = "".join("<th>%s</th>" % escape_html(i18n.t(h)) for h in _REGISTRY_HEADERS)
    body_rows = [
        _registry_row_html(index, prefix, count, first_seen, last_seen, example_callsign, now)
        for index, (prefix, count, first_seen, last_seen, example_callsign) in enumerate(rows)
    ]
    # data-table--registry scopes the stacked-cell rule to this table,
    # additively: the base data-table class and its rules are unchanged.
    return (
        '<div class="data-table-wrap">'
        '<table class="data-table data-table--registry">'
        "<thead><tr>%s</tr></thead>"
        "<tbody>%s</tbody>"
        "</table>"
        "</div>"
    ) % (header_cells, "".join(body_rows))


def _registry_cards_html(rows, now):
    """Mobile two-line-plus-disclosure representation of the registry:
    one card per prefix (Prefix/Count and Last seen at rest, First
    seen/Example callsign in a `<details>` disclosure), since a
    horizontal scroller would break the First-seen/Last-seen comparison.
    `data-filter-text`/`data-filter-group` use the same helper and loop
    index as the paired `<tr>`, so the two can't diverge.
    """
    if not rows:
        return ""
    items = []
    for index, (prefix, count, first_seen, last_seen, example_callsign) in enumerate(rows):
        filter_text = _registry_filter_text(prefix)
        primary = (
            '<div class="data-card__primary">'
            '<span class="cell-primary mono">%s</span>'
            '<span class="data-card__value">'
            '<span class="data-card__label">%s</span> %s'
            "</span>"
            "</div>"
        ) % (escape_html(prefix), escape_html(i18n.t(_REGISTRY_HEADERS[1])), escape_html(count))
        secondary = (
            '<div class="data-card__secondary">'
            '<span class="data-card__label">%s</span>%s'
            "</div>"
        ) % (
            escape_html(i18n.t(_REGISTRY_HEADERS[3])),
            layout.concise_timestamp_html(last_seen, now, fallback=""))
        escaped_prefix = escape_html(prefix)
        resolve_href = RESOLVE_LINK_HREF_TEMPLATE % escaped_prefix
        resolve_aria = escape_html(i18n.t(RESOLVE_LINK_ARIA_TEMPLATE)) % escaped_prefix
        action = (
            '<div class="data-card__action">'
            '<a href="%s" aria-label="%s">%s</a>'
            "</div>"
        ) % (resolve_href, resolve_aria, escape_html(i18n.t(RESOLVE_CARD_LINK_TEXT)))
        details = (
            '<details class="data-card__details">'
            "<summary>%s</summary>"
            "<dl>"
            "<dt>%s</dt><dd>%s</dd>"
            '<dt>%s</dt><dd class="mono">%s</dd>'
            "</dl>"
            "</details>"
        ) % (
            escape_html(i18n.t(_MORE_DETAILS_TEXT)),
            escape_html(i18n.t(_REGISTRY_HEADERS[2])),
            layout.concise_timestamp_html(first_seen, now, fallback=""),
            escape_html(i18n.t(_REGISTRY_HEADERS[4])),
            escape_html(example_callsign),
        )
        items.append(
            '<li class="data-card" data-filter-text="%s" data-filter-group="%d">%s%s%s%s</li>'
            % (filter_text, index, primary, secondary, action, details))
    return '<ul class="data-cards">%s</ul>' % "".join(items)


def _registry_section(rows, now):
    # No status dot in the card-title row: coverage_status() paints the
    # card's own top edge instead, composed at this function's call site.
    # section-caption composes onto text-body (Body size, matching the
    # sibling prose in this region), not text-label. _READ_ONLY_NOTE is
    # the short visible sentence; _READ_ONLY_NOTE_DETAIL moves into the
    # <details> disclosure below, the same idiom the battery readings
    # table and _corroboration_details_html() use.
    header_html = (
        '<p class="text-body section-caption">%s</p>'
        '<details class="readings-disclosure"><summary>%s</summary><p>%s</p></details>'
    ) % (
        escape_html(i18n.t(_READ_ONLY_NOTE)),
        escape_html(i18n.t(_MORE_DETAILS_TEXT)),
        escape_html(i18n.t(_READ_ONLY_NOTE_DETAIL)),
    )

    if not rows:
        return header_html + layout.empty_state(i18n.t(_NO_GAPS_HEADING), i18n.t(_NO_GAPS_BODY))

    filter_html = _registry_filter_bar_html(len(rows))
    cards_html = _registry_cards_html(rows, now)
    table_html = _registry_table_html(rows, now)
    # Cards must render before the table: style.css's
    # `.data-cards ~ .data-table-wrap` sibling-combinator toggle depends
    # on this DOM order.
    return header_html + filter_html + cards_html + table_html


def _stats_cards_html(rows):
    """Mobile stacked-prose representation of the resolution-statistics
    table: one `<li class="data-card">` per `(label, gloss, count)` in
    `rows`. A column of full sentences must wrap, not scroll
    (`.data-table--prose` in style.css), so the Description sentence
    renders full and untruncated rather than behind a disclosure.
    """
    if not rows:
        return ""
    items = []
    for label, gloss, count in rows:
        primary = (
            '<div class="data-card__primary">'
            '<span class="cell-primary">%s</span>'
            '<span class="data-card__value">'
            '<span class="data-card__label">%s</span> %s'
            "</span>"
            "</div>"
        ) % (escape_html(label), escape_html(i18n.t(_STATS_HEADERS[2])), escape_html(count))
        desc = '<p class="data-card__desc">%s</p>' % escape_html(gloss)
        items.append('<li class="data-card">%s%s</li>' % (primary, desc))
    return '<ul class="data-cards">%s</ul>' % "".join(items)


def _stats_table_html(stats):
    """The resolution-statistics breakdown table, with its `.data-cards`
    mobile sibling emitted first (style.css's sibling-combinator toggle
    depends on that order — do not reorder). Empty when there is nothing
    to show: `_resolution_rate_tile_html()` already carries that message.
    The only table whose Description column holds real prose, so it is
    the only one opted into `layout.data_table()`'s `prose` keyword and
    `desc` column role.
    """
    if stats is _DB_UNAVAILABLE or stats["total"] == 0:
        return ""
    return _stats_cards_html(stats["rows"]) + layout.data_table(
        [i18n.t(header) for header in _STATS_HEADERS], stats["rows"],
        desc_columns=(1,), prose=True)


def _resolution_rate_tile_html(stats):
    """The Resolution-rate stat_tile's content: a two-line figure inside
    the tile card.
    """
    if stats is _DB_UNAVAILABLE:
        return _unavailable_block()
    if stats["total"] == 0:
        # Translate the heading first, then interpolate, so the "%d"
        # placeholder survives translation. Compact variant: this block
        # lands inside a .stat-tile, whose 12px caption inverts under the
        # default form's 22px heading. No .widget-verdict here — this
        # tile makes no pass/fail judgement (status=None, no status
        # function exists for it).
        return layout.empty_state(
            i18n.t(_NO_STATS_HEADING) % RESOLUTION_WINDOW_DAYS,
            i18n.t(_NO_STATS_BODY), compact=True)
    # The Emphasis slot holds the figure (.stat-tile__value), not a
    # verdict word, since this tile carries no pass/fail judgement.
    detail_template = (
        _RESOLUTION_DETAIL_SINGULAR_TEMPLATE if stats["total"] == 1
        else _RESOLUTION_DETAIL_TEMPLATE)
    return (
        '<p class="stat-tile__value">%s</p>'
        '<div class="%s">%s</div>'
    ) % (
        escape_html(i18n.t(_RESOLVED_PCT_TEMPLATE) % stats["resolved_pct"]),
        _TILE_DETAIL_CLASS,
        escape_html(i18n.t(detail_template) % (
            RESOLUTION_WINDOW_DAYS, stats["total"])),
    )


def _check_in_regularity_cells(gap_rows, wake_interval_s, now):
    """`(cells, counts, day_labels)` for the check-in regularity grid:
    one entry per Europe/Paris calendar day, oldest first. Every
    verdict, including a day with no record, goes through
    `wake.classify_check_in_gap()`, the same function the Frame tile
    consumes. A day is judged by its longest observed gap, not an
    average, so one long hole isn't hidden by an otherwise-ordinary day.
    Calendar arithmetic is ordinal, correct across a DST boundary where
    a fixed per-day second count is not. Never raises.
    """
    worst = {}
    for row in gap_rows or ():
        try:
            day, gap = row.get("day"), row.get("gap_s")
        except AttributeError:
            continue
        if not isinstance(day, str) or not draw.is_number(gap):
            continue
        if day not in worst or gap > worst[day]:
            worst[day] = gap

    parsed = layout.parse_iso(now)
    if parsed is None:
        parsed = datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    last = parsed.astimezone(layout.LOCAL_TZ).date().toordinal()

    cells = []
    labels = []
    counts = dict.fromkeys(CHECK_IN_STATE_TEXT, 0)
    for ordinal in range(last - CHECK_IN_WINDOW_DAYS + 1, last + 1):
        day = date.fromordinal(ordinal)
        gap = worst.get(day.isoformat())
        state = wake.classify_check_in_gap(gap, wake_interval_s)
        counts[state] = counts.get(state, 0) + 1
        day_text = "%d %s" % (day.day, layout.month_abbr(day.month))
        labels.append(day_text)
        verdict_text = i18n.t(CHECK_IN_STATE_TEXT.get(
            state, CHECK_IN_STATE_TEXT[wake.CHECK_IN_UNKNOWN]))
        if gap is None:
            title = i18n.t(CHECK_IN_CELL_TITLE_NONE) % (day_text, verdict_text)
        else:
            title = i18n.t(CHECK_IN_CELL_TITLE) % (
                day_text, verdict_text, layout.duration_text(gap))
        cells.append((state, title))
    return cells, counts, labels


def _check_in_regularity_section_html(gap_rows, wake_interval_s, now):
    """The "Check-in regularity" card: heading, visible caption plus its
    disclosure, the grid, its date labels and the four-state key.
    `wake_interval_s` of `None` degrades to
    `device_staleness_thresholds()`'s bare floors, and the caption names
    those floors rather than a cadence nobody configured. Only
    `CHECK_IN_CAPTION_OBSERVED` is visible; every other clause moves
    into a `<details>` disclosure, the same idiom `_battery_section()`
    and `_corroboration_details_html()` use.
    """
    if gap_rows is _DB_UNAVAILABLE:
        body = _unavailable_block()
    else:
        cells, counts, labels = _check_in_regularity_cells(
            gap_rows, wake_interval_s, now)
        observed = sum(
            counts.get(state, 0) for state in (
                wake.CHECK_IN_ON_CADENCE, wake.CHECK_IN_LATE, wake.CHECK_IN_MISSING))
        grid_html, dropped = draw.regularity_grid(
            cells,
            label=i18n.t(CHECK_IN_GRID_LABEL) % (
                CHECK_IN_WINDOW_DAYS,
                counts.get(wake.CHECK_IN_ON_CADENCE, 0),
                counts.get(wake.CHECK_IN_LATE, 0),
                counts.get(wake.CHECK_IN_MISSING, 0),
                counts.get(wake.CHECK_IN_UNKNOWN, 0)))
        # Read past anything the drawing dropped, so the two labels can
        # only ever name cells that are on screen.
        oldest = labels[dropped] if dropped < len(labels) else labels[-1]
        visible_caption = i18n.t(CHECK_IN_CAPTION_OBSERVED)
        disclosure_clauses = []
        if not observed:
            disclosure_clauses.append(i18n.t(CHECK_IN_CAPTION_EMPTY))
        if draw.is_number(wake_interval_s) and wake_interval_s > 0:
            disclosure_clauses.append(
                i18n.t(CHECK_IN_CAPTION_CADENCE) % layout.duration_text(wake_interval_s))
        else:
            disclosure_clauses.append(i18n.t(CHECK_IN_CAPTION_CADENCE_FALLBACK))
        disclosure_clauses.append(i18n.t(CHECK_IN_CAPTION_NOT_PROOF))
        disclosure_html = (
            '<details class="readings-disclosure"><summary>%s</summary><p>%s</p></details>'
        ) % (
            escape_html(i18n.t(_MORE_DETAILS_TEXT)),
            escape_html(" ".join(disclosure_clauses)))
        body = (
            '<p class="text-label section-caption">%s</p>'
            '%s'
            '<div class="%s">%s<div class="%s">%s%s</div></div>'
            '%s'
        ) % (
            escape_html(visible_caption),
            disclosure_html,
            escape_html(CHECK_IN_GRID_CLASS), grid_html,
            escape_html(CHECK_IN_SCALE_CLASS),
            draw.label_span(oldest, hidden=False),
            draw.label_span(labels[-1], hidden=False),
            _check_in_key_html())
    # Plain .page-section, not page-section--nested: that modifier is
    # reserved for the two cards migrated into Server & data.
    return (
        '<section class="page-section">'
        '<h2 class="text-heading">%s</h2>%s</section>'
    ) % (escape_html(i18n.t(CHECK_IN_SECTION_HEADING)), body)


def _check_in_key_html():
    """Legend for the regularity grid, in classifier order (best to worst,
    then absence). The swatch takes the cell's own class rather than a
    copied colour, so key and grid share one `currentColor` declaration
    and cannot disagree. aria-hidden: the label text is the reading.
    """
    items = []
    for state in (wake.CHECK_IN_ON_CADENCE, wake.CHECK_IN_LATE,
                  wake.CHECK_IN_MISSING, wake.CHECK_IN_UNKNOWN):
        items.append(
            '<span class="%s"><span class="%s %s" aria-hidden="true"></span>'
            '<span class="drawing-axis-label">%s</span></span>'
            % (escape_html(CHECK_IN_KEY_ITEM_CLASS),
               escape_html(CHECK_IN_KEY_SWATCH_CLASS),
               escape_html(draw.cell_class(state)),
               escape_html(i18n.t(CHECK_IN_STATE_TEXT[state]))))
    return '<div class="%s">%s</div>' % (
        escape_html(CHECK_IN_KEY_CLASS), "".join(items))


# _read_health_inputs() lives in companion/health_signals.py now (its
# one caller, health_signals(), moved there with it) — re-exported here
# since a test reads it directly as `health_page._read_health_inputs`.
_read_health_inputs = health_signals_module._read_health_inputs


def _offbox_section_html(offbox, now):
    """The "Off-box backup" nested page-section, or the empty string when
    `offbox` is `None` (SKYPANE_OFFBOX_MARKER unset). `offbox` is the
    dict `compute_health_state()` already computed via
    `offbox_backup_status()` — never re-read from the marker here.
    """
    if offbox is None:
        return ""
    state = offbox["state"]
    modifier = layout.card_status_class("page-section", state)
    card_class = "page-section page-section--nested" + (
        (" " + modifier) if modifier else "")
    label = (
        i18n.t(_OFFBOX_UP_TO_DATE_TEXT) if state == "ok"
        else i18n.t(_OFFBOX_OVERDUE_TEXT))
    # concise_timestamp_html() returns pre-escaped markup; wrapping it in
    # escape_html() again would double-encode it and print raw tags.
    last_backup_html = (
        '<p>%s %s</p>'
        % (
            escape_html(_label_colon(i18n.t(_LAST_OFFBOX_BACKUP_TEXT))),
            layout.concise_timestamp_html(
                offbox["snapshot_ts"], now, fallback=i18n.t(_NEVER_TEXT)),
        )
    )
    warn_html = ""
    anomaly_text = _offbox_anomaly_text(offbox)
    if anomaly_text:
        warn_html = '<p class="text-body">%s</p>' % escape_html(anomaly_text)
    return (
        '<section class="%s"><h2 class="text-heading">%s</h2>'
        '<p class="text-body">%s</p>%s%s</section>'
    ) % (
        card_class,
        escape_html(i18n.t(_OFFBOX_BACKUP_TEXT)),
        layout.status_dot(state, label),
        last_backup_html,
        warn_html,
    )


def _stats_section_html(stats):
    """The "How well we name flights" nested page-section, or the empty
    string when the window is genuinely empty (`stats["total"] == 0`).
    A DB-unavailable `stats` still renders: that is a different failure
    mode from an empty window.
    """
    if stats is not _DB_UNAVAILABLE and stats["total"] == 0:
        return ""
    # No status modifier: resolution_stats() returns no verdict, so this
    # card carries no pass/fail state — a neutral hairline is correct.
    return '<section class="page-section page-section--nested"><h2 class="text-heading">%s</h2>%s</section>' % (
        escape_html(i18n.t(STATS_SECTION_HEADING)), _stats_table_html(stats))


# Health refreshes itself on a named-interval, visibility-gated timer (see
# companion/static/freshness.js) rather than showing a stale-view banner:
# a page that reloads itself cannot go stale. Severity stays computed
# server-side only — the timer reveals a pill and reloads, nothing else.


def render(ctx):
    ctx = page_context.coerce(ctx)
    state_dir = ctx.state_dir
    now = ctx.now or history_db.utc_now_iso()

    # Reuse the state build_page_context() already computed, rather than
    # re-deriving it. Falls back to a fresh compute for a direct caller.
    state = ctx.health_state or compute_health_state(state_dir, now)
    source_fault_raw = state["source_fault_raw"]

    device_html, device_state = state["device_html"], state["device_state"]
    pipeline_html, pipeline_state = state["pipeline_html"], state["pipeline_state"]
    battery_html, battery_state = state["battery_html"], state["battery_state"]
    battery_caption = state["battery_caption"]
    corroboration_html, disagreement_warn = (
        state["corroboration_html"], state["disagreement_warn"])

    severity = state["severity"]
    anomalies = state["anomalies"]
    banner_html = (
        _anomaly_banner_html(severity, anomalies) if severity != "ok" else "")

    # Registry (filesystem/JSON) and stats (SQLite) stay independent
    # reads. Reuses state["registry_rows"] when already computed.
    registry_rows = state.get("registry_rows")
    if registry_rows is None:
        registry_rows = unresolved_rows(state_dir)
    stats = _safe_query(
        state_dir, lambda conn: resolution_stats(conn, RESOLUTION_WINDOW_DAYS))

    # Window is one day wider than the grid draws: `since` compares a
    # UTC-ish `ts` against Europe/Paris day buckets, and a Paris day
    # begins before the UTC one.
    regularity_rows = _safe_query(
        state_dir,
        lambda conn: history_db.check_in_gaps(
            conn, since=_cutoff_iso(now, CHECK_IN_WINDOW_DAYS + 1)))
    # Membership, not .get() with a default: None is a legitimate value
    # here (cadence cannot be determined).
    if "wake_interval_s" in state:
        wake_interval_s = state["wake_interval_s"]
    else:
        wake_interval_s = wake.effective_wake_interval_s(
            device_config.load_device_config(state_dir))

    device_tile_html = layout.stat_tile(
        i18n.t(DEVICE_FRESHNESS_LABEL), device_html, device_state, icon=ICON_DEVICE)

    # Same expression that keys the Corroboration tile's verdict text,
    # so word and border colour can't disagree.
    corroboration_state = "warn" if disagreement_warn else "ok"
    server_data_tiles_html = (
        layout.stat_tile(
            i18n.t(PIPELINE_FRESHNESS_LABEL), pipeline_html, pipeline_state,
            icon=ICON_PIPELINE, caption_title=i18n.t(PIPELINE_FRESHNESS_TITLE))
        + layout.stat_tile(
            i18n.t(CORROBORATION_TILE_LABEL), corroboration_html,
            corroboration_state, icon=ICON_CORROBORATION,
            caption_title=i18n.t(CORROBORATION_TILE_TITLE))
        # Resolution-rate tile passes status=None: no status function
        # exists for it, so it carries no pass/fail verdict.
        + layout.stat_tile(
            i18n.t(RESOLUTION_RATE_LABEL), _resolution_rate_tile_html(stats), None,
            caption_title=i18n.t(RESOLUTION_RATE_TITLE))
    )

    freshness_html = layout.freshness_line_html(now)

    # Screen wraps the Device tile in its own dashboard-grid for the
    # margin-bottom a bare stat-tile lacks. Server & data holds the
    # three-tile grid plus the migrated full-width cards.
    screen_section_html = (
        layout.section_intro_html(
            SCREEN_SECTION_ID, i18n.t(SCREEN_SECTION_HEADING), i18n.t(SCREEN_SECTION_DESCRIPTION))
        + '<div class="dashboard-grid">' + device_tile_html + '</div>'
        + _battery_trend_section_html(battery_html, battery_state, battery_caption)
        # The regularity grid belongs to Screen, not Server & data: it
        # reflects the frame's own check-ins, under the Device tile
        # whose definition of "late" it shares.
        + _check_in_regularity_section_html(regularity_rows, wake_interval_s, now)
    )
    registry_modifier = layout.card_status_class("page-section", coverage_status(registry_rows))
    registry_class = "page-section page-section--nested" + (
        (" " + registry_modifier) if registry_modifier else "")
    server_data_section_html = (
        layout.section_intro_html(
            SERVER_DATA_SECTION_ID, i18n.t(SERVER_DATA_SECTION_HEADING),
            i18n.t(SERVER_DATA_SECTION_DESCRIPTION))
        + '<div class="dashboard-grid">' + server_data_tiles_html + '</div>'
        + '<section class="%s"><h2 class="text-heading">%s</h2>%s</section>' % (
            registry_class, escape_html(i18n.t(UNRESOLVED_SECTION_HEADING)),
            _registry_section(registry_rows, now))
        + _offbox_section_html(state.get("offbox"), now)
        + _stats_section_html(stats)
    )

    return (
        layout.page_header(
            i18n.t(_NAV_HEALTH_TEXT), purpose=i18n.t(PAGE_PURPOSE_TEXT), freshness_html=freshness_html)
        + _source_fault_block(source_fault_raw)
        + banner_html
        + screen_section_html
        + server_data_section_html
    )
