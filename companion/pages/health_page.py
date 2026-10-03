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
from companion.layout import escape_html
import companion.battery as battery
import companion.battery_chart as battery_chart
import companion.draw as draw
import companion.health_sections as health_sections_module
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

# The registry ("Airlines we could not name"), the resolution-statistics
# breakdown ("How well we name flights") and the check-in regularity grid
# all live in companion/health_sections.py now (moved out to keep this
# file under the companion app's own file-size ceiling) — imported and
# re-exported below under their historical names, since render() and a
# number of tests still reach them as `health_page.X`.
HEALTH_UNAVAILABLE_TEXT = health_sections_module.HEALTH_UNAVAILABLE_TEXT
_unavailable_block = health_sections_module._unavailable_block
_TILE_DETAIL_CLASS = health_sections_module._TILE_DETAIL_CLASS
CHECK_IN_SECTION_HEADING = health_sections_module.CHECK_IN_SECTION_HEADING
CHECK_IN_WINDOW_DAYS = health_sections_module.CHECK_IN_WINDOW_DAYS
CHECK_IN_CAPTION_OBSERVED = health_sections_module.CHECK_IN_CAPTION_OBSERVED
CHECK_IN_CAPTION_CADENCE = health_sections_module.CHECK_IN_CAPTION_CADENCE
CHECK_IN_CAPTION_CADENCE_FALLBACK = health_sections_module.CHECK_IN_CAPTION_CADENCE_FALLBACK
CHECK_IN_CAPTION_NOT_PROOF = health_sections_module.CHECK_IN_CAPTION_NOT_PROOF
CHECK_IN_CAPTION_EMPTY = health_sections_module.CHECK_IN_CAPTION_EMPTY
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
    "Something needs attention — check the tiles below.")

_SEVERITY_BANNER_NOUNS = {
    "warn": i18n.msg("health.warning", "warning"),
    "error": i18n.msg("health.error", "error"),
}  # falls back to "issue" for any severity not in this dict.
_SEVERITY_BANNER_ISSUE_TEXT = i18n.msg("health.issue", "issue")

DEVICE_FRESHNESS_LABEL = i18n.msg("health.device_last_checked_in", "Device last checked in")
DEVICE_CONNECTION_HELP_TEXT = i18n.msg(
    "health.device_connection_help",
    "This is when the frame last contacted the server.")
# Plain-language visible label; the technical term stays one hover away
# via `caption_title` at the tile's stat_tile() call site below.
PIPELINE_FRESHNESS_LABEL = i18n.msg(
    "health.flight_data_last_updated", "Flight data last updated")
PIPELINE_FRESHNESS_TITLE = i18n.msg(
    "health.ads_b_pipeline_last_ran", "ADS-B pipeline last ran")

CORROBORATION_TILE_LABEL = i18n.msg(
    "health.do_the_two_data_sources_agree", "Do the two data sources agree?")
CORROBORATION_TILE_TITLE = i18n.msg("health.corroboration", "Corroboration")
CORROBORATION_HELP_TEXT = i18n.msg(
    "health.source_comparison_help", "What this result means")

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

# The visible heading and the chart's accessible name share this text, which
# lives in companion/battery_chart.py.
BATTERY_SECTION_HEADING = battery_chart.BATTERY_SECTION_HEADING
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
    "health.nothing_to_compare_yet", "Nothing to compare yet.")
_APPEARS_ONCE_RECORDED_TEXT = i18n.msg(
    "health.this_appears_once_the_frame_has_recorded_at",
    "This appears once the frame has recorded at least one flight.")
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




# Every .stat-tile on this page renders the same four slots, in order:
# label (stat_tile()'s own caption), verdict (Emphasis role, exactly
# once), detail (muted, carrying different information from the
# verdict), optional link. The Resolution-rate tile is the one
# exception: it makes no pass/fail judgement (status=None, no status
# function exists), so its Emphasis slot carries the figure instead of
# a verdict sentence; do not give it a .widget-verdict paragraph.
_TILE_VERDICT_CLASS = "text-body widget-verdict"


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
    detail += '<p class="section-caption">%s</p>' % escape_html(
        i18n.t(DEVICE_CONNECTION_HELP_TEXT))
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
    detection_detail = layout.concise_timestamp_html(last_detection, now)
    return (
        '<p class="stat-tile__meta text-label section-caption">%s %s</p>'
        % (escape_html(_label_colon(i18n.t(LAST_DETECTION_LABEL))), detection_detail))


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
    return _tile_body(verdict, detail), state


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
    heading_text = i18n.t(BATTERY_SECTION_HEADING)
    return (
        '<section class="%s">'
        '<h2 class="text-heading">%s</h2>'
        "%s"
        "</section>"
    ) % (
        section_class,
        escape_html(heading_text), battery_html)


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


def _corroboration_details_html():
    """An optional, native help control for source-comparison wording."""
    dl_items = "".join(
        "<dt>%s</dt><dd>%s</dd>" % (escape_html(i18n.t(label)), escape_html(i18n.t(explanation)))
        for _key, label, _status, explanation in _CORROBORATION_ROWS
    )
    return (
        '<details class="status-help"><summary aria-label="%s">'
        '<span aria-hidden="true">i</span><span class="visually-hidden">%s</span>'
        '</summary>'
        "<dl>%s</dl></details>" % (
            escape_html(i18n.t(CORROBORATION_HELP_TEXT)),
            escape_html(i18n.t(CORROBORATION_HELP_TEXT)),
            dl_items)
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
            i18n.t(_APPEARS_ONCE_RECORDED_TEXT),
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

# resolution_stats() and the registry/stats/check-in-regularity markup
# builders (_registry_section(), _stats_section_html(),
# _check_in_regularity_section_html() and _check_in_regularity_cells(),
# the last of which a test reads directly) all live in
# companion/health_sections.py now — re-exported here since render()
# below calls each of these as a bare name.
resolution_stats = health_sections_module.resolution_stats
_registry_section = health_sections_module._registry_section
_stats_section_html = health_sections_module._stats_section_html
_check_in_regularity_cells = health_sections_module._check_in_regularity_cells
_check_in_regularity_section_html = health_sections_module._check_in_regularity_section_html
_day_band_html = health_sections_module._day_band_html
DAY_BAND_ROW_LIMIT = health_sections_module.DAY_BAND_ROW_LIMIT
DAY_BAND_COLLAPSED_TEXT = health_sections_module.DAY_BAND_COLLAPSED_TEXT
_resolution_rate_tile_html = health_sections_module._resolution_rate_tile_html



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
    # The Today band's own bounded read: newest rows first, so a limit
    # below a day's check-ins would silently shorten the day.
    day_rows = _safe_query(
        state_dir,
        lambda conn: history_db.recent_device_health(conn, limit=DAY_BAND_ROW_LIMIT))
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

    # Screen wraps the Device tile in its own dashboard-grid for the
    # margin-bottom a bare stat-tile lacks. Server & data holds the
    # three-tile grid plus the migrated full-width cards.
    screen_section_html = (
        layout.section_intro_html(SCREEN_SECTION_ID, i18n.t(SCREEN_SECTION_HEADING), "")
        + '<div class="dashboard-grid">' + device_tile_html + '</div>'
        + _battery_trend_section_html(battery_html, battery_state, battery_caption)
        # The regularity grid belongs to Screen, not Server & data: it
        # reflects the frame's own check-ins, under the Device tile
        # whose definition of "late" it shares.
        + _check_in_regularity_section_html(regularity_rows, wake_interval_s, now)
        + _day_band_html(day_rows, now, ctx.device_config)
    )
    registry_class = "page-section page-section--nested"
    server_data_section_html = (
        layout.section_intro_html(SERVER_DATA_SECTION_ID, i18n.t(SERVER_DATA_SECTION_HEADING), "")
        + '<div class="dashboard-grid">' + server_data_tiles_html + '</div>'
        + '<section class="%s"><h2 class="text-heading">%s</h2>%s</section>' % (
            registry_class, escape_html(i18n.t(UNRESOLVED_SECTION_HEADING)),
            _registry_section(registry_rows, now))
        + _offbox_section_html(state.get("offbox"), now)
        + _stats_section_html(stats)
    )

    return (
        '<div class="status-page">'
        + layout.page_header(i18n.t(_NAV_HEALTH_TEXT))
        + _source_fault_block(source_fault_raw)
        + banner_html
        + screen_section_html
        + server_data_section_html
        + "</div>"
    )
