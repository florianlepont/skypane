"""The state behind the Fleet page's tiles, the frame's Battery page and the
System view.

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
markup half (the battery row, the tile facts, `health_state_from_signals()`
and its `compute_health_state()`/`safe_health_state()` wrappers, which
still need the shared fragments and so stay here). The generic row
components live in companion/health_rows.py and the System cards in
companion/pages/system_cards.py.
"""
from typing import NamedTuple

from companion.layout import escape_html
import companion.battery as battery
import companion.battery_card as battery_card
import companion.battery_chart as battery_chart
import companion.device_scope as device_scope
import companion.health_rows as health_rows
import companion.health_sections as health_sections_module
import companion.health_signals as health_signals_module
import companion.user_view as user_view
import companion.i18n as i18n
import companion.layout as layout
import companion.page_context as page_context
import companion.prefs as prefs  # for the resolved language directly:
# French requires a real U+00A0 before the colon (_label_colon() below),
# not merely a translated label.
import companion.frame_state as frame_state  # the one frame-state
# resolution — the Connection tile and the nav notification dot both consume
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
_NO_STATS_HEADING = health_sections_module._NO_STATS_HEADING
_NO_STATS_BODY = health_sections_module._NO_STATS_BODY
_SOURCE_ROWS = health_sections_module._SOURCE_ROWS
_OTHER_SOURCE_LABEL = health_sections_module._OTHER_SOURCE_LABEL


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
         "health.sys_both_note",
         "Both flight-data sources on the frame picked the same aircraft.")),
    # "off", not "ok": this state means there was nothing to compare
    # against, not that agreement was confirmed — a neutral, everyday
    # state, never a problem, so never "warn" either.
    ("None", i18n.msg("health.only_one_saw_it", "Only one saw it"), "off",
     i18n.msg(
         "health.sys_only_one_note",
         "Only one of the two sources returned an aircraft this cycle.")),
    ("False", i18n.msg("health.they_disagree", "They disagree"), "warn",
     i18n.msg(
         "health.sys_disagree_note", "The two sources picked different aircraft.")),
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

# The sentence the System view's warnings banner ends with.
ANOMALY_BANNER_TEXT = i18n.msg(
    "health.something_needs_attention_check_the_tiles_below",
    "Something needs attention — check the rows below.")

_SEVERITY_BANNER_NOUNS = {
    "warn": i18n.msg("health.warning", "warning"),
    "error": i18n.msg("health.error", "error"),
}  # falls back to "issue" for any severity not in this dict.
_SEVERITY_BANNER_ISSUE_TEXT = i18n.msg("health.issue", "issue")

# One short name per topic. The identification topic is named by
# STATS_SECTION_HEADING and the backup topic by _OFFBOX_BACKUP_TEXT, which
# already say exactly that.
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
DEVICE_EMPTY_HEADING = i18n.msg(
    "health.device_empty_heading", "This frame has not checked in yet")
DEVICE_EMPTY_BODY = i18n.msg(
    "health.device_empty_body",
    "Battery readings appear after its first wake. Make sure it is powered on "
    "and in range of Wi-Fi.")
DEVICE_BATTERY_EMPTY_HEADING = i18n.msg(
    "health.device_battery_empty_heading", "No battery reading")
DEVICE_BATTERY_EMPTY_BODY = i18n.msg(
    "health.device_battery_empty_body", "Shown after the first check-in.")
_ROW_UNAVAILABLE_TEXT = i18n.msg("health.row_unavailable", "Unavailable")
_LAST_CHECK_IN_TEXT = i18n.msg("health.row_last_check_in", "Last check-in")
_NEXT_WAKE_TEXT = i18n.msg("health.row_next_wake", "Next wake")
_LAST_RUN_TEXT = i18n.msg("health.row_last_run", "Last run")
_BATTERY_VALUE_TEMPLATE = i18n.msg("health.row_battery_value", "%d%% · %d mV")
_NO_DISAGREEMENT_TEXT = i18n.msg("health.row_no_disagreement", "No disagreement")
_ONE_DISAGREEMENT_TEXT = i18n.msg("health.row_one_disagreement", "1 disagreement")
_MANY_DISAGREEMENTS_TEMPLATE = i18n.msg(
    "health.row_n_disagreements", "%d disagreements")
_IDENTIFIED_SHORT_TEMPLATE = i18n.msg(
    "health.sys_identified_short", "%s\u00a0%% identified")
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
    layout.REFRESH_PAGE_FLEET]

# Looked up by battery-trend.js and styled by style.css — duplicated,
# not imported, since those are static assets. A cross-file check
# asserts both literals appear in battery-trend.js's shipped source.
BATTERY_READOUT_ID = battery_card.BATTERY_READOUT_ID
# The chart's own class vocabulary, geometry and markup now live in
# companion/battery_chart.py (built on companion/draw.py); re-exported
# here under their historical names so nothing outside this module needs
# to know the chart moved.
SPARKLINE_HIT_CLASS = battery_chart.SPARKLINE_HIT_CLASS
SPARKLINE_LINE_CLASS = battery_chart.SPARKLINE_LINE_CLASS
SPARKLINE_AXIS_CLASS = battery_chart.SPARKLINE_AXIS_CLASS
SPARKLINE_ZONE_CLASS = battery_chart.SPARKLINE_ZONE_CLASS
SPARKLINE_TEXT_CLASS = battery_chart.SPARKLINE_TEXT_CLASS
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
_NOTHING_TO_COMPARE_YET_TEXT = i18n.msg(
    "health.nothing_to_compare_yet", "Nothing to compare yet")
_APPEARS_ONCE_RECORDED_TEXT = i18n.msg(
    "health.this_appears_once_the_frame_has_recorded_at",
    "This appears once the frame has recorded at least one flight.")
_LAST_OFFBOX_BACKUP_TEXT = i18n.msg("health.last_off_box_backup", "Last off-box backup")
_NEVER_TEXT = i18n.msg("health.never", "never")
_OFFBOX_BACKUP_TEXT = i18n.msg("health.off_box_backup", "Off-box backup")

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
# by name as `health_page.X`.
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


def health_state_from_signals(signals, curve=None):
    """Builds the markup fragments Home and the Battery row share
    (`*_detail_html`, `battery_html`, `battery_caption`) from
    `signals["inputs"]` (a `health_signals()` snapshot), and returns
    exactly `compute_health_state()`'s key set. Every state, `severity`
    and `anomalies` value is copied straight from `signals`, never
    recomputed here, so the nav-tab dot and this page's own banner can
    never disagree. `curve` is the device's discharge curve (None: legacy).
    """
    now = signals["now"]
    inputs = signals["inputs"]
    device_detail_html = _device_timestamp_only(inputs["device_health"], now)
    pipeline_detail_html = _pipeline_timestamp_only(
        inputs["pipeline_ts"], inputs["last_detection"], now)
    battery_html, _battery_state_unused = _battery_section(
        inputs["trend_rows"], inputs["daily_rows"], curve)
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


def compute_health_state(state_dir, now=None, fleet_root=None, curve=None):
    """The single computation both the nav-tab dot and the full Battery
    page need. Running these independently against fresh DB connections
    at two different instants let a write land between them and make
    the two disagree; `build_page_context()` now calls this once per
    request and threads the result through `ctx.health_state`.

    Composed from exactly one `health_signals()` snapshot fed into
    `health_state_from_signals()`, so the severity `safe_health_signals()`
    could hand the nav dot and the banner this page renders always come
    from the same read.
    """
    return health_state_from_signals(
        health_signals(state_dir, now, fleet_root, curve), curve)


def safe_health_state(state_dir, now=None):
    """Fail-closed wrapper around `compute_health_state()`: `None` on any
    unanticipated exception, never a raise. Broad `except Exception`,
    unlike the narrow `(sqlite3.Error, OSError)` catches elsewhere in
    this file: this function runs on every authenticated page render, so
    a raise here would 500 every page over a decorative nav dot.
    Callers treat `None` as "ok" (fail closed — the Battery page itself
    still reports the real problem in full); `render()` falls back to a
    fresh compute rather than a dict with missing keys.
    """
    try:
        return compute_health_state(state_dir, now)
    except Exception:
        return None


def _anomaly_category_labels(anomalies):
    """One short pill label per `anomalies` entry, the pill-shaped
    counterpart to `_anomaly_category_text()`'s comma-joined clause.
    Strips the trailing period but never lower-cases: a pill is not
    mid-sentence text, so it keeps its original, sentence-initial case.
    """
    return [anomaly.rstrip(".") for anomaly in anomalies]


HEALTH_ANOMALY_CLASS = layout.HEALTH_ANOMALY_CLASS
HEALTH_SOURCE_FAULT_CLASS = layout.HEALTH_SOURCE_FAULT_CLASS


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


def _battery_verdict(state, latest, curve=None):
    """`(state, text)` of the Battery card's verdict: a reading under the
    low-battery mark says so (a warning); otherwise the drop scan's own
    verdict. The scan's state still drives the page-wide severity."""
    if latest is not None and battery.is_low(latest[0], curve):
        return "warn", i18n.t(battery_card.LOW_VERDICT_TEXT)
    return state, i18n.t(BATTERY_STATE_TEXT.get(state, BATTERY_STATE_TEXT["warn"]))


def _battery_body_html(battery_html):
    """The Battery row's details: `_battery_section()`'s already-built
    markup inside the `BATTERY_SECTION_CLASS` wrapper the chart's rules and
    its script key off. The wrapper carries no card chrome of its own: the
    row is the container. `battery_html` is already-safe markup,
    interpolated verbatim.
    """
    return '<div class="%s %s--embedded">%s</div>' % (
        BATTERY_SECTION_CLASS, BATTERY_SECTION_CLASS, battery_html)


def _battery_section(trend_rows, daily_rows=None, curve=None):
    """Returns `(markup, state)` for the Battery row's details. `state`
    drives both the card-edge status modifier and
    `collect_anomalies()`'s abnormal-drop signal. The chart plots
    `daily_rows` when there are enough buckets, else falls back to raw
    `trend_rows`; the anomaly scan and the readings always read
    `trend_rows`, since averaging would hide the abnormal drop the scan
    exists to catch. Empty history returns `"ok"`, not `"warn"`: an absence
    of readings must not make `collect_anomalies()` assert a drop that
    never happened.
    """
    if trend_rows is _DB_UNAVAILABLE:
        return _unavailable_block(), "ok"
    latest = _latest_numeric_battery_reading(trend_rows) if trend_rows else None
    if latest is None:
        # Compact: this lands inside a row, whose own name is 12px, so the
        # full-card form's 22px display-face heading would invert the hierarchy.
        return layout.empty_state(
            i18n.t(_NO_BATTERY_READINGS_YET_TEXT),
            i18n.t(_NO_BATTERY_TELEMETRY_RECORDED_TEXT), compact=True), "ok"
    # Through the state-only sibling, not a bare battery_status() call:
    # keeps this row's state and health_signals()'s severity
    # input reading identically from the same two early-exit cases.
    state = _battery_state(trend_rows, daily_rows, curve)
    now = history_db.utc_now_iso()
    # One predicate decides both the series and the caption, so they can
    # never disagree.
    plot_daily = _battery_daily_series_usable(daily_rows)
    plot_rows = daily_rows if plot_daily else trend_rows
    verdict_state, verdict = _battery_verdict(state, latest, curve)
    markup, has_chart = battery_card.body_html(
        trend_rows, plot_rows, plot_daily, _battery_trend_caption(trend_rows, daily_rows),
        health_signals_module._real_trend_reading_count(trend_rows), latest, now,
        verdict_state, verdict, curve)
    # The script emits only when a chart exists, keeping "exactly one
    # script tag, zero on the empty path" testable.
    if has_chart:
        markup += '<script src="%s" defer></script>' % BATTERY_TREND_SCRIPT_SRC
    return markup, state


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

# resolution_stats() lives in companion/health_sections.py — re-exported here
# since the System view reads it as a bare name.
resolution_stats = health_sections_module.resolution_stats



# _read_health_inputs() lives in companion/health_signals.py now (its
# one caller, health_signals(), moved there with it) — re-exported here
# since a test reads it directly as `health_page._read_health_inputs`.
_read_health_inputs = health_signals_module._read_health_inputs


# The battery row reads its state, verdict and value from the same snapshot
# the nav dot was judged on (`state` is health_state_from_signals()'s dict),
# so it can never show a reading its own state was not computed from.

def _available(value):
    """`value`, or None when the read behind it failed (an unreadable
    history.db arrives as the `_DB_UNAVAILABLE` sentinel)."""
    return None if value is _DB_UNAVAILABLE else value


def _unavailable_row(row_id, name):
    """A neutral row for a signal whose read failed: an empty value would
    read as "nothing recorded", which is a different statement."""
    return health_rows.row_html(
        row_id, "off", name, i18n.t(_ROW_UNAVAILABLE_TEXT), "", _unavailable_block())


def _age_html(ts, now, fallback=_NEVER_TEXT):
    """The row's right-hand value for a point in time: a live relative
    age that is already complete text with scripts blocked."""
    return layout.relative_time_html(ts, now, fallback=i18n.t(fallback))


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


def _battery_row(state, battery_critical=False, device=None):
    name = i18n.t(ROW_BATTERY_NAME)
    trend_rows = state["inputs"]["trend_rows"]
    if trend_rows is _DB_UNAVAILABLE:
        return _unavailable_row("battery", name)
    latest = _latest_numeric_battery_reading(trend_rows)
    if latest is None:
        # `battery_html` is the empty state when there is no history.
        empty_html = state["battery_html"]
        if device is not None and not device.is_live:
            empty_html = layout.empty_state(
                i18n.t(DEVICE_BATTERY_EMPTY_HEADING),
                i18n.t(DEVICE_BATTERY_EMPTY_BODY), compact=True)
        return health_rows.row_html(
            "battery", "off", name, i18n.t(_NO_READINGS_VERDICT_TEXT), "",
            empty_html)
    curve = page_context.device_curve(device)
    verdict_state, _verdict = _battery_verdict(state["battery_state"], latest, curve)
    # The verdict and the level live in the body (the status pill and the
    # gauge); the head carries the name and the charging pill only.
    return health_rows.row_html(
        "battery", verdict_state, name, "",
        _charging_pill_html(state, trend_rows, battery_critical),
        _battery_body_html(state["battery_html"]))


def _disagreements_text(count):
    if not count:
        return i18n.t(_NO_DISAGREEMENT_TEXT)
    if count == 1:
        return i18n.t(_ONE_DISAGREEMENT_TEXT)
    return i18n.t(_MANY_DISAGREEMENTS_TEMPLATE) % count


def _percent_text(percent):
    """`percent` to one decimal, with the decimal comma in French."""
    text = "%.1f" % percent
    return text.replace(".", ",") if prefs.current_lang() == "fr" else text


# The Fleet page refreshes itself on a named-interval, visibility-gated timer (see
# companion/static/freshness.js) rather than showing a stale-view banner:
# a page that reloads itself cannot go stale. Severity stays computed
# server-side only — the timer reveals a pill and reloads, nothing else.


def _epoch_of(iso):
    """Epoch seconds of an ISO instant, or None when it does not parse."""
    parsed = history_db.instant_or_none(iso)
    return None if parsed is None else parsed.timestamp()


def _device_status(ctx, now):
    """`device_scope`'s status for the selected device, or None for the live
    frame and for a context with no device."""
    device = ctx.device
    if device is None or device.is_live:
        return None
    return device_scope.device_status(device, _epoch_of(now) or device_scope.now_epoch())


class SystemTile(NamedTuple):
    """What one System tile shows: the topic key (the id suffix of its detail
    block), the state word (ok, warn, error, off), the sprite icon id, the
    translated label, the headline (plain text) and the muted line (already-safe
    markup, "" when there is none)."""
    key: str
    state: str
    icon: str
    label: str
    value: str
    meta_html: str


_SERVER_TILE_TEXT = i18n.msg("health.tile_server", "Server")


def _unavailable_tile(key, icon, label):
    return SystemTile(key, "off", icon, label, i18n.t(_ROW_UNAVAILABLE_TEXT), "")


def _server_tile(state, now):
    """The poll pipeline's state and the age of its last run."""
    label = i18n.t(_SERVER_TILE_TEXT)
    inputs = state["inputs"]
    if inputs["pipeline_ts"] is _DB_UNAVAILABLE:
        return _unavailable_tile("flight-data", "icon-server", label)
    pipeline_ts = inputs["pipeline_ts"]
    pipeline_state = state["pipeline_state"]
    meta = ""
    if pipeline_ts:
        meta = "%s %s" % (escape_html(i18n.t(_LAST_RUN_TEXT)), _age_html(pipeline_ts, now))
    return SystemTile(
        "flight-data", pipeline_state, "icon-server", label,
        i18n.t(PIPELINE_STATE_TEXT.get(pipeline_state, PIPELINE_STATE_TEXT["warn"])), meta)


def _sources_tile(state):
    """The corroboration verdict and the number of disagreements."""
    label = i18n.t(ROW_SOURCES_NAME)
    counts = state["inputs"]["corroboration_counts"]
    if counts is _DB_UNAVAILABLE:
        return _unavailable_tile("sources", "icon-radio", label)
    counts = counts or {}
    if not any(counts.values()):
        return SystemTile(
            "sources", "off", "icon-radio", label,
            i18n.t(_NOTHING_TO_COMPARE_YET_TEXT), "")
    verdict_state = "warn" if state["disagreement_warn"] else "ok"
    return SystemTile(
        "sources", verdict_state, "icon-radio", label,
        i18n.t(CORROBORATION_STATE_TEXT[verdict_state]),
        escape_html(_disagreements_text(counts.get("False", 0) or 0)))


def _identification_tile(stats, unresolved_count):
    """The identified rate and what is left to resolve; neutral, since the
    rate has no pass mark."""
    label = i18n.t(STATS_SECTION_HEADING)
    if stats is _DB_UNAVAILABLE:
        return _unavailable_tile("identification", "icon-nav-airlines", label)
    to_resolve = escape_html(
        i18n.t(_TO_RESOLVE_TEMPLATE) % unresolved_count if unresolved_count
        else i18n.t(_NOTHING_TO_RESOLVE_TEXT))
    if stats["total"] == 0:
        return SystemTile(
            "identification", "off", "icon-nav-airlines", label,
            i18n.t(_NO_STATS_HEADING) % RESOLUTION_WINDOW_DAYS, to_resolve)
    percent = stats["resolved_pct"]
    shown_percent = min(percent, 99.9) if unresolved_count else percent
    return SystemTile(
        "identification", "off", "icon-nav-airlines", label,
        i18n.t(_IDENTIFIED_SHORT_TEMPLATE) % _percent_text(shown_percent), to_resolve)


def _backup_tile(offbox, now):
    """The off-box backup's state and the age of the last one; None when no
    marker is configured (the block is left out too)."""
    if offbox is None:
        return None
    backup_state = offbox["state"]
    return SystemTile(
        "backup", backup_state, "icon-cloud-upload", i18n.t(_OFFBOX_BACKUP_TEXT),
        i18n.t(BACKUP_STATE_TEXT.get(backup_state, BACKUP_STATE_TEXT["warn"])),
        _age_html(offbox["snapshot_ts"], now))


def _system_tiles(state, stats, registry_rows, now, route_tiles=()):
    """The System page's tiles, one per topic block, in the blocks' order."""
    tiles = (
        _server_tile(state, now), _sources_tile(state),
        _identification_tile(stats, len(registry_rows)), *route_tiles,
        _backup_tile(state.get("offbox"), now))
    return tuple(tile for tile in tiles if tile is not None)


def _state_parts(ctx):
    """`(health state, now)` for the frame in `ctx`, computed once per request:
    the snapshot every tile, the battery view and the System cards read. None
    for a frame that never checked in."""
    now = ctx.now or history_db.utc_now_iso()
    if _device_status(ctx, now) == device_scope.STATUS_NEVER_SEEN:
        return None
    # Reuse the state build_page_context() already computed, rather than
    # re-deriving it. Falls back to a fresh compute for a direct caller.
    state = ctx.health_state or compute_health_state(
        ctx.state_dir, now, ctx.root_state_dir, page_context.device_curve(ctx.device))
    return state, now


def _platform_parts(ctx, state, now):
    """The platform-wide parts of the System view: its tiles, its cards and
    the source-fault notice. Empty for a principal who may not see the
    platform."""
    if not user_view.platform_visible():
        return {"system_tiles": (), "system_cards": [], "source_fault_html": ""}
    from companion.pages import route_sources_card, system_cards
    state_dir = ctx.state_dir
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
    route_data = _safe_query(
        state_dir, lambda conn: route_sources_card.read(conn, now))
    return {
        "system_tiles": _system_tiles(
            state, stats, registry_rows, now, route_sources_card.tiles(route_data)),
        "system_cards": system_cards.topics(
            state, stats, registry_rows, now, route_sources_card.topics(route_data, now)),
        "source_fault_html": _source_fault_block(state["source_fault_raw"])}


def _never_seen_html():
    return layout.empty_state(
        i18n.t(DEVICE_EMPTY_HEADING), i18n.t(DEVICE_EMPTY_BODY), compact=True)


class TileFacts(NamedTuple):
    """What one overview tile shows: the state word (ok, warn, error, off),
    the verdict text (plain), the value text (plain) and the muted lines under
    it (already-safe markup, "" when there are none): the age of the last run,
    or for the connection tile the last and the next connection."""
    state: str
    verdict: str
    value: str
    age_html: str


class FrameTiles(NamedTuple):
    """The two state-backed tiles of a frame (connection and battery) and the
    battery's recent percentages, oldest first."""
    connection: TileFacts
    battery: TileFacts
    battery_curve: tuple


def _connection_tile(state, now):
    """The connection verdict with the last connection and the next expected
    one as two lines, so the frame's page says it without a detail page."""
    device_health = state["inputs"]["device_health"]
    if device_health is _DB_UNAVAILABLE:
        return TileFacts("off", i18n.t(_ROW_UNAVAILABLE_TEXT), "", "")
    ts = (device_health or {}).get("ts")
    device_state = state["device_state"]
    stats = []
    if ts is not None:
        stats.append((i18n.t(_LAST_CHECK_IN_TEXT), _age_html(ts, now, _NO_CHECK_IN_TEXT)))
    if state["next_wake_clock"]:
        stats.append((i18n.t(_NEXT_WAKE_TEXT), '<span class="time-value">%s</span>' % escape_html(
            state["next_wake_clock"])))
    stats_html = "".join(
        '<span class="fleet-stat"><span class="fleet-stat__k">%s</span>'
        '<span class="fleet-stat__v">%s</span></span>' % (escape_html(label), value)
        for label, value in stats)
    return TileFacts(
        device_state,
        i18n.t(DEVICE_STATE_TEXT.get(device_state, DEVICE_STATE_TEXT["warn"])), "",
        '<span class="fleet-stats">%s</span>' % stats_html if stats_html else "")


def _battery_curve_percents(inputs, curve):
    """The battery's percentages, oldest first: one per day when the chart
    plots days, else the latest readings (the series the Battery chart draws)."""
    daily = inputs["daily_rows"]
    rows = daily if _battery_daily_series_usable(daily) else inputs["trend_rows"]
    if not isinstance(rows, list):
        return ()
    return tuple(
        battery.percent(row["battery_mv"], curve) or 0
        for row in reversed(rows) if row.get("battery_mv") is not None)


def _battery_tile(state, device):
    inputs = state["inputs"]
    trend_rows = inputs["trend_rows"]
    if trend_rows is _DB_UNAVAILABLE:
        return TileFacts("off", i18n.t(_ROW_UNAVAILABLE_TEXT), "", ""), ()
    latest = _latest_numeric_battery_reading(trend_rows)
    if latest is None:
        return TileFacts("off", i18n.t(_NO_READINGS_VERDICT_TEXT), "", ""), ()
    curve = page_context.device_curve(device)
    millivolts, _ts = latest
    percent = battery.percent(millivolts, curve)
    value = (
        i18n.t(_BATTERY_VALUE_TEMPLATE) % (percent, millivolts)
        if percent is not None else "%d mV" % millivolts)
    # The same verdict as the Battery card's status pill, so the tile and
    # the card never disagree (a low level says so in words).
    tile_state, verdict = _battery_verdict(state["battery_state"], latest, curve)
    return (
        TileFacts(tile_state, verdict, value, ""),
        _battery_curve_percents(inputs, curve))


def frame_tiles(ctx):
    """The facts of the overview's connection and battery tiles,
    built from the same snapshot as the Battery view; None for a frame that
    never checked in."""
    ctx = page_context.coerce(ctx)
    parts = _state_parts(ctx)
    if parts is None:
        return None
    state, now = parts
    battery_tile, curve = _battery_tile(state, ctx.device)
    return FrameTiles(
        _connection_tile(state, now), battery_tile, curve)


class BatteryView(NamedTuple):
    """The Battery page of one frame: the battery row (already-safe markup)
    and `empty_html`, the empty state of a frame that never checked in (the
    row is then empty)."""
    row_html: str
    empty_html: str


def battery_view(ctx):
    """The Battery page's content for `ctx`'s frame: the battery row (level,
    trend and charging estimate), or the empty state of a frame that never
    checked in."""
    ctx = page_context.coerce(ctx)
    parts = _state_parts(ctx)
    if parts is None:
        return BatteryView("", _never_seen_html())
    return BatteryView(_battery_row(parts[0], ctx.battery_critical, ctx.device), "")


def system_html(ctx):
    """The System view of the Console Fleet page: the platform-wide
    information. The source fault and anomaly banner sit above one tile per
    topic, each linking to its block; then one glass group per topic (flight
    data, ADS-B sources, identification, the route directories and backups)."""
    from companion import ui_groups
    from companion.pages import fleet_tiles, system_cards
    ctx = page_context.coerce(ctx)
    parts = _state_parts(ctx)
    if parts is None:
        return ""
    state, now = parts
    platform = _platform_parts(ctx, state, now)
    if not platform["system_cards"]:
        return ""
    groups = "".join(
        ui_groups.group(
            '<li class="fleet-group__item fleet-group__item--flush">%s</li>'
            % row,
            label=label, label_id="system-" + key,
            extra_class="fleet-block system-topic",
            attrs='id="%s%s"' % (fleet_tiles.SYSTEM_BLOCK_ID_PREFIX, key)).replace(
                '<ul class="group">', '<ul class="group fleet-group">', 1)
        for key, label, row in platform["system_cards"])
    banner = (
        system_cards.banner(state["severity"], state["anomalies"])
        if state["severity"] != "ok" else "")
    return (
        platform["source_fault_html"] + banner
        + fleet_tiles.system_tiles_html(platform["system_tiles"])
        + '<div class="system-topics">%s</div>' % groups)
