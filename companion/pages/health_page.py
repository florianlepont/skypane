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
markup half (one `_x_row()` builder per Health row, `health_state_from_signals()`
and its `compute_health_state()`/`safe_health_state()` wrappers, which
still need the shared fragments and so stay here). The generic row
components live in companion/health_rows.py.
"""
from companion.layout import escape_html
import companion.battery as battery
import companion.battery_chart as battery_chart
import companion.draw as draw
import companion.health_rows as health_rows
import companion.health_sections as health_sections_module
import companion.health_signals as health_signals_module
import companion.i18n as i18n
import companion.layout as layout
import companion.page_context as page_context
import companion.resolve_dialog as resolve_dialog
import companion.prefs as prefs  # for the resolved language directly:
# French requires a real U+00A0 before the colon (_label_colon() below),
# not merely a translated label.
import companion.frame_state as frame_state  # the one frame-state
# resolution — the Frame connection row and the nav notification dot both consume
# resolve_state(), never re-deriving due/held/late from
# device_staleness_thresholds() alone.
from server import history_db
from server.plane import manual_resolutions

# The registry ("Airlines we could not name"), the resolution-statistics
# breakdown ("How well we name flights") all live in companion/health_sections.py now (moved out to keep this
# file under the companion app's own file-size ceiling) — imported and
# re-exported below under their historical names, since render() and a
# number of tests still reach them as `health_page.X`.
HEALTH_UNAVAILABLE_TEXT = health_sections_module.HEALTH_UNAVAILABLE_TEXT
_unavailable_block = health_sections_module._unavailable_block
UNRESOLVED_SECTION_HEADING = health_sections_module.UNRESOLVED_SECTION_HEADING
STATS_SECTION_HEADING = health_sections_module.STATS_SECTION_HEADING
RESOLUTION_WINDOW_DAYS = health_sections_module.RESOLUTION_WINDOW_DAYS
_MORE_DETAILS_TEXT = health_sections_module._MORE_DETAILS_TEXT
_REGISTRY_HEADERS = health_sections_module._REGISTRY_HEADERS
RESOLVE_LINK_HREF_TEMPLATE = health_sections_module.RESOLVE_LINK_HREF_TEMPLATE
RESOLVE_LINK_ARIA_TEMPLATE = health_sections_module.RESOLVE_LINK_ARIA_TEMPLATE
RESOLVE_LINK_TEXT = health_sections_module.RESOLVE_LINK_TEXT
RESOLVE_CARD_LINK_TEXT = health_sections_module.RESOLVE_CARD_LINK_TEXT
_REGISTRY_CELL_SEPARATOR_TEXT = health_sections_module._REGISTRY_CELL_SEPARATOR_TEXT
_NO_GAPS_HEADING = health_sections_module._NO_GAPS_HEADING
_READ_ONLY_NOTE = health_sections_module._READ_ONLY_NOTE
_READ_ONLY_NOTE_DETAIL = health_sections_module._READ_ONLY_NOTE_DETAIL
_NO_STATS_HEADING = health_sections_module._NO_STATS_HEADING
_RESOLUTION_DETAIL_TEMPLATE = health_sections_module._RESOLUTION_DETAIL_TEMPLATE
_RESOLUTION_DETAIL_SINGULAR_TEMPLATE = health_sections_module._RESOLUTION_DETAIL_SINGULAR_TEMPLATE
_NO_STATS_BODY = health_sections_module._NO_STATS_BODY
_SOURCE_ROWS = health_sections_module._SOURCE_ROWS
_OTHER_SOURCE_LABEL = health_sections_module._OTHER_SOURCE_LABEL
_FILTER_INPUT_ID = health_sections_module._FILTER_INPUT_ID


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
    "Something needs attention — check the rows below.")

_SEVERITY_BANNER_NOUNS = {
    "warn": i18n.msg("health.warning", "warning"),
    "error": i18n.msg("health.error", "error"),
}  # falls back to "issue" for any severity not in this dict.
_SEVERITY_BANNER_ISSUE_TEXT = i18n.msg("health.issue", "issue")

DEVICE_CONNECTION_HELP_TEXT = i18n.msg(
    "health.device_connection_help",
    "This is when the frame last contacted the server.")

# One short name per row. The identification row is named by
# STATS_SECTION_HEADING and the backup row by _OFFBOX_BACKUP_TEXT, which
# already say exactly that.
ROW_CONNECTION_NAME = i18n.msg("health.row_connection", "Frame connection")
ROW_BATTERY_NAME = i18n.msg("health.row_battery", "Battery")
ROW_FLIGHT_DATA_NAME = i18n.msg("health.row_flight_data", "Flight data")
ROW_SOURCES_NAME = i18n.msg("health.row_sources", "Data sources")

LAST_DETECTION_LABEL = i18n.msg("health.last_aircraft_detected", "Last aircraft detected")

# Evidence only ("since it started"), never the state name, so it is
# safe to publish verdict-free as compute_health_state()'s
# "pipeline_detail_html" key.
PIPELINE_NEVER_RAN_DETAIL_TEXT = i18n.msg(
    "health.the_frame_has_not_reported_a_flight_since_it",
    "The frame has not reported a flight since it started.")

# A short plain-sentence verdict for each row whose state would otherwise
# live only in an icon and its colour (WCAG 1.4.1: colour must never be
# the sole means of conveying information). The identification row
# deliberately has no sibling dict here: it makes no pass/fail judgement.
DEVICE_STATE_TEXT = {
    "ok": i18n.msg("health.checking_in_normally", "Checking in normally"),
    "warn": i18n.msg(
        "health.has_not_checked_in_for_a_while", "Has not checked in for a while"),
    "error": i18n.msg(
        "health.has_not_checked_in_for_a_long_time",
        "Has not checked in for a long time"),
    # A genuine fourth device state, not merely "hasn't checked in for a
    # while": a frame the strip and the row both know is quiet-hours-held.
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

BATTERY_STATE_TEXT = {
    "ok": i18n.msg("health.row_battery_ok", "Level looks normal"),
    "warn": i18n.msg("health.row_battery_warn", "Dropping faster than expected"),
}
BACKUP_STATE_TEXT = {
    "ok": i18n.msg("health.row_backup_ok", "Up to date"),
    "warn": i18n.msg("health.row_backup_warn", "Overdue"),
}
_NO_READINGS_VERDICT_TEXT = i18n.msg("health.row_no_readings", "No readings yet")
_NO_CHECK_IN_TEXT = i18n.msg("health.row_no_check_in", "No check-in yet")
_ROW_UNAVAILABLE_TEXT = i18n.msg("health.row_unavailable", "Unavailable")
_LAST_CHECK_IN_TEXT = i18n.msg("health.row_last_check_in", "Last check-in")
_NEXT_WAKE_TEXT = i18n.msg("health.row_next_wake", "Next wake")
_LAST_RUN_TEXT = i18n.msg("health.row_last_run", "Last run")
_BATTERY_VALUE_TEMPLATE = i18n.msg("health.row_battery_value", "%d%% · %d mV")
_NO_DISAGREEMENT_TEXT = i18n.msg("health.row_no_disagreement", "No disagreement")
_ONE_DISAGREEMENT_TEXT = i18n.msg("health.row_one_disagreement", "1 disagreement")
_MANY_DISAGREEMENTS_TEMPLATE = i18n.msg(
    "health.row_n_disagreements", "%d disagreements")
_IDENTIFIED_TEMPLATE = i18n.msg(
    "health.row_identified", "%s%% of flights identified")
_TO_RESOLVE_TEMPLATE = i18n.msg("health.row_to_resolve", "%d to resolve")
_NOTHING_TO_RESOLVE_TEXT = i18n.msg(
    "health.row_nothing_to_resolve", "Nothing to resolve")

# Retired: status_dot() emitted an empty first span with no accessible
# name, so a screen reader got only the subject label, never the state.
# The battery-trend section's top edge carries the verdict instead.

# The auto-refresh pill's visible copy, English only (this app renders
# `<html lang="en">`).
REFRESH_PILL_TEXT = layout.REFRESH_PILL_TEXT

# The hook freshness.js toggles its breathing class on. Duplicated, not
# imported: freshness.js is a static asset, not a Python module.
REFRESH_LIVE_DOT_ATTR = layout.REFRESH_LIVE_DOT_ATTR

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

# The visible heading and the chart's accessible name share this text, which
# lives in companion/battery_chart.py.
BATTERY_SECTION_HEADING = battery_chart.BATTERY_SECTION_HEADING
# Contract value shared with style.css's .battery-trend-section rule,
# guarded against silent drift by a cross-file check.
BATTERY_SECTION_CLASS = "battery-trend-section"

# The two id-anchored groups the rows card is split into.
# SERVER_DATA_SECTION_ID is a cross-page coupling: other pages may link to
# this exact anchor (#server-data) — renaming it silently breaks that link.
SCREEN_SECTION_ID = "screen"
SCREEN_SECTION_HEADING = i18n.msg("health.screen", "Screen")
SERVER_DATA_SECTION_ID = "server-data"
SERVER_DATA_SECTION_HEADING = i18n.msg("health.server_data", "Server & data")
# The unresolved-prefix card's anchor: the identification row links to it.
UNRESOLVED_SECTION_ID = "unresolved-prefixes"


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
_NOTHING_TO_COMPARE_YET_TEXT = i18n.msg(
    "health.nothing_to_compare_yet", "Nothing to compare yet")
_APPEARS_ONCE_RECORDED_TEXT = i18n.msg(
    "health.this_appears_once_the_frame_has_recorded_at",
    "This appears once the frame has recorded at least one flight.")
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


def _next_wake_clock(signals):
    """The local clock text of the frame's next expected wake, or None
    when frame_state.resolve_state() cannot place one (no check-in yet,
    or an unparseable schedule)."""
    resolved_state = _device_resolved_state(
        signals["next_wake_iso"], signals["effective_interval_s"],
        signals["hold_reason"], signals["now"])
    if resolved_state == frame_state.STATE_UNKNOWN:
        return None
    parsed = layout.parse_iso(signals["next_wake_iso"])
    if parsed is None:
        return None
    return layout.local_clock_text(
        parsed, now_parsed=layout.parse_iso(signals["now"]))


def health_state_from_signals(signals):
    """Builds the markup fragments Home and the Health rows share
    (`*_detail_html`, `battery_html`, `battery_caption`) from
    `signals["inputs"]` (a `health_signals()` snapshot), and returns
    exactly `compute_health_state()`'s key set. Every state, `severity`
    and `anomalies` value is copied straight from `signals`, never
    recomputed here, so the nav-tab dot and this page's own banner can
    never disagree.
    """
    now = signals["now"]
    inputs = signals["inputs"]
    device_detail_html = _device_timestamp_only(inputs["device_health"], now)
    pipeline_detail_html = _pipeline_timestamp_only(
        inputs["pipeline_ts"], inputs["last_detection"], now)
    battery_html, _battery_state_unused = _battery_section(
        inputs["trend_rows"], inputs["daily_rows"])
    # Threaded through the returned dict rather than as a third
    # _battery_section() return value: that function's 2-tuple return is
    # directly unpacked by a pinned harness check.
    battery_caption = _battery_trend_caption(inputs["trend_rows"], inputs["daily_rows"])
    return {
        "now": now,
        "source_fault_raw": signals["source_fault_raw"],
        "registry_rows": signals["registry_rows"],
        # render() reuses this rather than reading the marker a second
        # time per request.
        "offbox": signals["offbox"],
        # The raw reads the rows render their values and evidence from,
        # so a row can never show a reading the states above were not
        # judged on.
        "inputs": inputs,
        "next_wake_clock": _next_wake_clock(signals),
        "device_state": signals["device_state"],
        "device_detail_html": device_detail_html,
        "pipeline_state": signals["pipeline_state"],
        "pipeline_detail_html": pipeline_detail_html,
        "battery_html": battery_html,
        "battery_state": signals["battery_state"],
        "battery_caption": battery_caption,
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


HEALTH_ANOMALY_CLASS = layout.HEALTH_ANOMALY_CLASS
HEALTH_SOURCE_FAULT_CLASS = layout.HEALTH_SOURCE_FAULT_CLASS


def _anomaly_banner_html(severity, anomalies):
    """The anomaly state as a docked toast (persistent, never dismissed):
    a count-and-noun title, one pill per failing category, and a
    `<span class="visually-hidden">` tail carrying the original
    comma-joined sentence, so a screen reader gets one coherent sentence
    rather than disconnected pills. The error state announces
    assertively, a warning-only state politely.
    """
    tone = layout.TOAST_TONE_ERROR if severity == "error" else layout.TOAST_TONE_WARNING
    role = "alert" if severity == "error" else "status"
    noun = i18n.t(_SEVERITY_BANNER_NOUNS.get(severity, _SEVERITY_BANNER_ISSUE_TEXT))
    count = len(anomalies)
    plural = "" if count == 1 else "s"
    title = _label_colon("%d %s%s" % (count, noun, plural))
    pills_html = "".join(
        '<span class="toast__pill">%s</span>' % escape_html(label)
        for label in _anomaly_category_labels(anomalies)
    )
    tail_text = "%s — %s" % (_anomaly_category_text(anomalies), i18n.t(ANOMALY_BANNER_TEXT))
    extra_html = '<span class="toast__pills">%s</span><span class="visually-hidden">%s</span>' % (
        pills_html, escape_html(tail_text))
    return layout.toast_html(
        title, tone=tone, role=role, extra_html=extra_html, docked=True,
        extra_class=HEALTH_ANOMALY_CLASS)




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
    detection_detail = layout.concise_timestamp_html(last_detection, now)
    return (
        '<p class="stat-tile__meta text-label section-caption">%s %s</p>'
        % (escape_html(_label_colon(i18n.t(LAST_DETECTION_LABEL))), detection_detail))


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


def _battery_body_html(battery_html):
    """The Battery row's details: `_battery_section()`'s already-built
    markup (ring, readout, chart, readings disclosure) inside the
    `BATTERY_SECTION_CLASS` wrapper the chart's rules and its script key
    off. The wrapper is modified to carry no card chrome of its own: the
    row is the container. No range caption is rendered: the chart's own
    axis labels name the span, and a caption beside them was retired.
    `battery_html` is already-safe markup, interpolated verbatim.
    """
    return '<div class="%s %s--embedded">%s</div>' % (
        BATTERY_SECTION_CLASS, BATTERY_SECTION_CLASS, battery_html)


def _battery_section(trend_rows, daily_rows=None):
    """Returns `(markup, state)` for the Battery row's details. `state`
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
        # Compact: this lands inside a row, whose own name is 12px, so the
        # full-card form's 22px serif heading would invert the hierarchy.
        return layout.empty_state(
            i18n.t(_NO_BATTERY_READINGS_YET_TEXT),
            i18n.t(_NO_BATTERY_TELEMETRY_RECORDED_TEXT), compact=True), "ok"
    # Through the state-only sibling, not a bare battery_status() call:
    # keeps this row's state and health_signals()'s severity
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
    # table from .data-table's min-width: max-content no-crop floor.
    table_html = layout.data_table(
        [i18n.t(_TIMESTAMP_TEXT), i18n.t(_BATTERY_MV_TEXT)], table_rows,
        mono_columns=(1,), raw_columns=(0,), modifier="readings")
    # Collapsed behind a closed-by-default native <details> disclosure.
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
        battery_chart.battery_unit_chart(plot_rows, now=now, daily=plot_daily)
        if len(plot_rows) >= 2 else "")
    # Script tag and readout emit only when a chart exists, keeping
    # "exactly one script tag, zero on the empty path" testable.
    latest_reading = _latest_numeric_battery_reading(trend_rows)
    chart_block = _battery_readout_row_html(latest_reading, now, state)
    if sparkline_html:
        chart_block = (
            chart_block + sparkline_html
            + '<script src="%s" defer></script>' % BATTERY_TREND_SCRIPT_SRC)
    # The chart, when present, comes before the collapsed table in both
    # DOM and visual order.
    return chart_block + disclosure_html, state


def _source_fault_block(source_fault_raw):
    # Not given page-section--nested: this block renders above both
    # id-anchored sections, at the same structural level as their own
    # headings, not nested inside one.
    if source_fault_raw is _DB_UNAVAILABLE:
        return ""
    if not _meta_flag_true(source_fault_raw):
        return ""
    # A docked error toast that is also a section with its own heading,
    # so the page outline still lists the outage.
    body = i18n.t(SOURCE_FAULT_BODY_TEMPLATE) % ", ".join(_ADSB_PROVIDER_NAMES)
    return (
        '<section class="toast toast--error toast--docked toast--section %s">'
        "%s"
        '<div class="toast__text">'
        '<h2 class="toast__title">%s</h2>'
        '<p class="toast__detail">%s</p>'
        "</div>"
        "</section>"
    ) % (HEALTH_SOURCE_FAULT_CLASS, layout.toast_icon_html(layout.TOAST_TONE_ERROR),
         escape_html(i18n.t(SOURCE_FAULT_HEADING)), escape_html(body))


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

# resolution_stats() and the registry/stats markup
# builders (_registry_section(), _stats_section_html()) all live in
# companion/health_sections.py now — re-exported here since render()
# below calls each of these as a bare name.
resolution_stats = health_sections_module.resolution_stats
_registry_section = health_sections_module._registry_section
_stats_table_html = health_sections_module._stats_table_html



# _read_health_inputs() lives in companion/health_signals.py now (its
# one caller, health_signals(), moved there with it) — re-exported here
# since a test reads it directly as `health_page._read_health_inputs`.
_read_health_inputs = health_signals_module._read_health_inputs


# One row per subsystem. Each builder returns a complete row, whose state,
# verdict and value are read from the same snapshot the nav dot and the
# anomaly toast were judged on (`state` is health_state_from_signals()'s
# dict), so no row can show a reading its own state was not computed from.

def _available(value):
    """`value`, or None when the read behind it failed (an unreadable
    history.db arrives as the `_DB_UNAVAILABLE` sentinel)."""
    return None if value is _DB_UNAVAILABLE else value


def _unavailable_row(row_id, name):
    """A neutral row for a signal whose read failed: an empty value would
    read as "nothing recorded", which is a different statement."""
    return health_rows.row_html(
        row_id, "off", name, i18n.t(_ROW_UNAVAILABLE_TEXT), "", _unavailable_block())


def _fact(label, value_html):
    return (escape_html(i18n.t(label)), value_html)


def _concise(ts, now):
    return layout.concise_timestamp_html(ts, now, fallback=i18n.t(_NEVER_TEXT))


def _age_html(ts, now, fallback=_NEVER_TEXT):
    """The row's right-hand value for a point in time: a live relative
    age that is already complete text with scripts blocked."""
    return layout.relative_time_html(ts, now, fallback=i18n.t(fallback))


def _connection_row(state, now):
    name = i18n.t(ROW_CONNECTION_NAME)
    device_health = state["inputs"]["device_health"]
    if device_health is _DB_UNAVAILABLE:
        return _unavailable_row("connection", name)
    ts = (device_health or {}).get("ts")
    device_state = state["device_state"]
    facts = [_fact(_LAST_CHECK_IN_TEXT, layout.concise_timestamp_html(
        ts, now, fallback=i18n.t(_NO_CHECK_IN_TEXT)))]
    if state["next_wake_clock"]:
        facts.append(_fact(
            _NEXT_WAKE_TEXT,
            '<span class="time-value">%s</span>' % escape_html(state["next_wake_clock"])))
    body = (
        health_rows.facts_html(facts)
        + health_rows.note_html(i18n.t(DEVICE_CONNECTION_HELP_TEXT)))
    return health_rows.row_html(
        "connection", device_state, name,
        i18n.t(DEVICE_STATE_TEXT.get(device_state, DEVICE_STATE_TEXT["warn"])),
        _age_html(ts, now, _NO_CHECK_IN_TEXT), body)


def _charging_pill_html(state, trend_rows, battery_critical):
    """The estimated "Probably charging" pill, or "" when the shared
    estimate does not say so. Judged on the same per-wake readings and the
    same `now` this row's own verdict was, at the cadence the device is
    actually on, so a stale reading shows nothing here either."""
    if not health_signals_module.charging_likely(
            trend_rows, state["now"], state["inputs"]["device_config"],
            battery_critical):
        return ""
    return layout.battery_charging_pill_html("health-row__charging")


def _battery_row(state, battery_critical=False):
    name = i18n.t(ROW_BATTERY_NAME)
    trend_rows = state["inputs"]["trend_rows"]
    if trend_rows is _DB_UNAVAILABLE:
        return _unavailable_row("battery", name)
    latest = _latest_numeric_battery_reading(trend_rows)
    if latest is None:
        # `battery_html` is the empty state when there is no history.
        return health_rows.row_html(
            "battery", "off", name, i18n.t(_NO_READINGS_VERDICT_TEXT), "",
            state["battery_html"])
    millivolts, _ts = latest
    percent = battery.battery_percent(millivolts)
    value = (
        i18n.t(_BATTERY_VALUE_TEMPLATE) % (percent, millivolts)
        if percent is not None else "%d mV" % millivolts)
    battery_state = state["battery_state"]
    return health_rows.row_html(
        "battery", battery_state, name,
        i18n.t(BATTERY_STATE_TEXT.get(battery_state, BATTERY_STATE_TEXT["warn"])),
        escape_html(value) + _charging_pill_html(state, trend_rows, battery_critical),
        _battery_body_html(state["battery_html"]))


def _flight_data_row(state, now):
    name = i18n.t(ROW_FLIGHT_DATA_NAME)
    inputs = state["inputs"]
    if inputs["pipeline_ts"] is _DB_UNAVAILABLE:
        return _unavailable_row("flight-data", name)
    pipeline_ts = inputs["pipeline_ts"]
    last_detection = _available(inputs["last_detection"])
    pipeline_state = state["pipeline_state"]
    if _pipeline_never_ran(pipeline_ts, last_detection):
        # Nothing to date: the sentence says so, where two "never" facts
        # would only repeat it.
        body = health_rows.note_html(i18n.t(PIPELINE_NEVER_RAN_DETAIL_TEXT))
    else:
        body = health_rows.facts_html([
            _fact(_LAST_RUN_TEXT, _concise(pipeline_ts, now)),
            _fact(LAST_DETECTION_LABEL, _concise(last_detection, now)),
        ])
    return health_rows.row_html(
        "flight-data", pipeline_state, name,
        i18n.t(PIPELINE_STATE_TEXT.get(pipeline_state, PIPELINE_STATE_TEXT["warn"])),
        _age_html(pipeline_ts, now), body)


def _disagreements_text(count):
    if not count:
        return i18n.t(_NO_DISAGREEMENT_TEXT)
    if count == 1:
        return i18n.t(_ONE_DISAGREEMENT_TEXT)
    return i18n.t(_MANY_DISAGREEMENTS_TEMPLATE) % count


def _corroboration_outcomes_html(counts):
    """The three outcomes a cycle can have, each with its dot, its count
    and the sentence saying what it means."""
    statuses = corroboration_status(counts)
    items = []
    for key, label, _default_state, explanation in _CORROBORATION_ROWS:
        items.append(
            '<li><p class="health-row__outcome">%s'
            '<span class="mono">%d</span></p>%s</li>' % (
                layout.status_dot(statuses[key], i18n.t(label)),
                counts.get(key, 0) or 0,
                health_rows.note_html(i18n.t(explanation))))
    return '<ul class="health-row__outcomes">%s</ul>' % "".join(items)


def _sources_row(state):
    name = i18n.t(ROW_SOURCES_NAME)
    counts = state["inputs"]["corroboration_counts"]
    if counts is _DB_UNAVAILABLE:
        return _unavailable_row("sources", name)
    counts = counts or {}
    if not any(counts.values()):
        return health_rows.row_html(
            "sources", "off", name, i18n.t(_NOTHING_TO_COMPARE_YET_TEXT), "",
            health_rows.note_html(i18n.t(_APPEARS_ONCE_RECORDED_TEXT)))
    verdict_state = "warn" if state["disagreement_warn"] else "ok"
    return health_rows.row_html(
        "sources", verdict_state, name,
        i18n.t(CORROBORATION_STATE_TEXT[verdict_state]),
        escape_html(_disagreements_text(counts.get("False", 0) or 0)),
        _corroboration_outcomes_html(counts))


def _percent_text(percent):
    """`percent` to one decimal, with the decimal comma in French."""
    text = "%.1f" % percent
    return text.replace(".", ",") if prefs.current_lang() == "fr" else text


def _identification_row(stats, unresolved_count):
    name = i18n.t(STATS_SECTION_HEADING)
    if stats is _DB_UNAVAILABLE:
        return _unavailable_row("identification", name)
    to_resolve = escape_html(
        i18n.t(_TO_RESOLVE_TEMPLATE) % unresolved_count
        if unresolved_count else i18n.t(_NOTHING_TO_RESOLVE_TEXT))
    link = '<p class="health-row__note"><a class="text-link" href="#%s">%s</a></p>' % (
        UNRESOLVED_SECTION_ID, escape_html(i18n.t(UNRESOLVED_SECTION_HEADING)))
    if stats["total"] == 0:
        return health_rows.row_html(
            "identification", "off", name,
            i18n.t(_NO_STATS_HEADING) % RESOLUTION_WINDOW_DAYS, to_resolve,
            health_rows.note_html(i18n.t(_NO_STATS_BODY)) + link)
    template = (
        _RESOLUTION_DETAIL_SINGULAR_TEMPLATE if stats["total"] == 1
        else _RESOLUTION_DETAIL_TEMPLATE)
    percent = stats["resolved_pct"]
    # The rate is a figure with no pass mark, so its row stays neutral and
    # its ring is drawn in ink, never in a status colour.
    return health_rows.row_html(
        "identification", "off", name,
        i18n.t(_IDENTIFIED_TEMPLATE) % _percent_text(percent),
        health_rows.ring_html(percent / 100.0) + to_resolve,
        health_rows.note_html(
            i18n.t(template) % (RESOLUTION_WINDOW_DAYS, stats["total"]))
        + link + _stats_table_html(stats))


def _backup_row(offbox, now):
    """The off-box backup row, or "" when no marker is configured."""
    if offbox is None:
        return ""
    backup_state = offbox["state"]
    body = health_rows.facts_html([
        _fact(_LAST_OFFBOX_BACKUP_TEXT, _concise(offbox["snapshot_ts"], now))])
    anomaly_text = _offbox_anomaly_text(offbox)
    if anomaly_text:
        body += health_rows.note_html(anomaly_text)
    return health_rows.row_html(
        "backup", backup_state, i18n.t(_OFFBOX_BACKUP_TEXT),
        i18n.t(BACKUP_STATE_TEXT.get(backup_state, BACKUP_STATE_TEXT["warn"])),
        _age_html(offbox["snapshot_ts"], now), body)


# Health refreshes itself on a named-interval, visibility-gated timer (see
# companion/static/freshness.js) rather than showing a stale-view banner:
# a page that reloads itself cannot go stale. Severity stays computed
# server-side only — the timer reveals a pill and reloads, nothing else.


def _resolve_dialog_html(ctx, registry_rows):
    """The shared resolve dialog, emitted once and only when something can
    open it: a Resolve link in the table, or the hidden step-B trigger
    that reopens it after a name was saved. `?resolve=` is acted on only
    when it names a prefix still in the table (step A, whose own link
    opens the dialog) or one just named that still lacks artwork (step
    B); any other value renders nothing extra."""
    step_b_html = (
        resolve_dialog.step_b_trigger_html(
            ctx.state_dir, ctx.resolve_prefix, resolve_dialog.RETURN_HEALTH)
        if ctx.resolve_prefix and ctx.state_dir else "")
    if not registry_rows and not step_b_html:
        return ""
    return resolve_dialog.dialog_html() + step_b_html


def render(ctx):
    ctx = page_context.coerce(ctx)
    state_dir = ctx.state_dir
    now = ctx.now or history_db.utc_now_iso()

    # Reuse the state build_page_context() already computed, rather than
    # re-deriving it. Falls back to a fresh compute for a direct caller.
    state = ctx.health_state or compute_health_state(state_dir, now)

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
    # A prefix the owner has just named leaves the table at once, rather
    # than lingering until the next poll prunes the registry.
    named_prefixes = manual_resolutions.load_manual_resolutions(state_dir) if state_dir else {}
    registry_rows = [row for row in registry_rows if row[0] not in named_prefixes]

    screen_rows = (
        _connection_row(state, now)
        + _battery_row(state, ctx.battery_critical))
    server_rows = (
        _flight_data_row(state, now) + _sources_row(state)
        + _identification_row(stats, len(registry_rows))
        + _backup_row(state.get("offbox"), now))
    rows_card_html = health_rows.card_html(
        health_rows.group_html(
            SCREEN_SECTION_ID, i18n.t(SCREEN_SECTION_HEADING), screen_rows)
        + health_rows.group_html(
            SERVER_DATA_SECTION_ID, i18n.t(SERVER_DATA_SECTION_HEADING), server_rows))
    # The registry sits below the rows card: the table is the long part
    # of the page, and the verdicts above it are what a glance is for.
    registry_html = (
        '<section id="%s" class="page-section page-section--nested">'
        '<h2 class="text-heading">%s</h2>%s</section>' % (
            UNRESOLVED_SECTION_ID, escape_html(i18n.t(UNRESOLVED_SECTION_HEADING)),
            _registry_section(registry_rows, now)))

    return (
        '<div class="status-page">'
        + layout.page_header(i18n.t(_NAV_HEALTH_TEXT))
        + _source_fault_block(state["source_fault_raw"])
        + banner_html
        + rows_card_html
        + registry_html
        + _resolve_dialog_html(ctx, registry_rows)
        + "</div>"
    )
