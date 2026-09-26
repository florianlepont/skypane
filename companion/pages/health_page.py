"""Health status and trend page, and the landing context for the
on-device fault icon's redirect target.

Every dynamic value reaches HTML through `escape_html()` or an escaping
component builder. The Device and Pipeline freshness signals are
independent (different failure modes and data sources), never blended
into one verdict. `_safe_query()` returns the `_DB_UNAVAILABLE` sentinel
instead of raising, so each section degrades independently.
`safe_health_state()` is this module's one public cross-page export, so no
nav renderer needs to import a page module.
"""
import os
import re
import sqlite3
from datetime import date, datetime, timedelta, timezone
# `date` joins the three for the regularity grid's window walk, which is
# ordinal calendar arithmetic (toordinal()/fromordinal()) and carries no
# duration anywhere in it.
from zoneinfo import ZoneInfo

from companion.layout import escape_html
import companion.battery as battery
import companion.draw as draw
import companion.i18n as i18n
import companion.layout as layout
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
import server.poll_loop as poll_loop

HEALTH_UNAVAILABLE_TEXT = (
    "Health history is temporarily unavailable — check the companion "
    "service logs.")


def _label_colon(label):
    """`label` (already translated by the caller) followed by a
    language-appropriate colon separator: a real U+00A0 non-breaking
    space before ":" in French; the plain ":" in English.
    """
    return label + (" :" if prefs.current_lang() == "fr" else ":")

# ADS-B pipeline freshness thresholds: server/poll_loop.py's
# POLL_INTERVAL_S is a fixed 30-second systemd timer, not a tunable
# per-deployment value, so these can be set tight relative to it.
STALE_PIPELINE_WARN_S = 180  # 6x the cadence: one missed cycle is jitter, six is not.
STALE_PIPELINE_ERROR_S = 900  # 30x the cadence: well past a timer having a rough moment.

# Off-box backup freshness. Each successful pull of the VPS's nightly
# snapshot leaves a one-line marker file named by this env var, read
# here (the marker's one reader).
OFFBOX_MARKER_ENV_VAR = "SKYPANE_OFFBOX_MARKER"
OFFBOX_WARN_S = 3 * 86400  # One missed nightly pull is ordinary (sleep,
# wake catch-up); three means the pull or backup job has stopped.
# The marker holds one archive name matching this pattern plus an
# optional trailing newline, never a raw timestamp, so the file also
# proves the acked archive exists.
_OFFBOX_MARKER_RE = re.compile(r"^skypane-state-(\d{8}T\d{6}Z)\.tar\.gz$")

# Device check-in thresholds are derived per-deployment, not fixed here:
# a fixed pair miscalibrates for any specific cadence (see
# compute_health_state()/_device_section()).

BATTERY_TREND_LIMIT = 20  # A display choice, not retention: bounds the
# raw-readings table, the anomaly scan and the fallback chart; the
# chart's primary series plots daily averages instead.

BATTERY_TREND_WINDOW_DAYS = 90  # The chart's primary window, locked at
# 3 months by explicit request. A display window only: nothing is deleted.

# 100 mV: a genuine discharge measured ~50 mV/day through the middle and
# a couple mV per reading even across the steepest final cliff
# (hardware/BATTERY-RUN.md), so crossing 100 mV between two consecutive
# readings means an anomaly, not real discharge.
BATTERY_DROP_WARN_MV = 100

_CORROBORATION_WINDOW_DAYS = 7  # A recent window; runway_events rows are
# written only on a real transition, so even a week's worth stays small.

_CORROBORATION_ROWS = (
    # (stored corroborated string, display label, status, explanation).
    # The stored key ("True"/"None"/"False") is the on-disk vocabulary
    # history_db.save_poll_state() writes and must never be renamed.
    ("True", "Both agree", "ok",
     "Both flight-data sources on the frame picked the same aircraft."),
    # "off", not "ok": this state means there was nothing to compare
    # against, not that agreement was confirmed — a neutral, everyday
    # state, never a problem, so never "warn" either.
    ("None", "Only one saw it", "off",
     "Only one of the two sources returned an aircraft this cycle — "
     "that is not the same as a disagreement, there was simply nothing "
     "from the other source to compare it against."),
    ("False", "They disagree", "warn",
     "The two sources named different aircraft, so nothing was shown "
     "that cycle — the display kept the previous image instead."),
)

# Kept as a literal, human-maintained list rather than importing
# server.plane.detect: this page is presentation-only and must not reach
# into the detection/network layer. Keep in sync with
# detect.DEFAULT_PROVIDER_ORDER by hand if that list ever changes.
_ADSB_PROVIDER_NAMES = ("adsb.fi", "adsb.lol")

SOURCE_FAULT_HEADING = "ADS-B source outage"
SOURCE_FAULT_BODY_TEMPLATE = (
    "The frame's alert badge is showing because every configured ADS-B "
    "source (%s) failed to respond on the most recent pipeline run — "
    "this is a data-source outage, not a device problem.")
SOURCE_FAULT_BODY = SOURCE_FAULT_BODY_TEMPLATE % ", ".join(_ADSB_PROVIDER_NAMES)

# The leading "⚠ " glyph lives in _anomaly_banner_html(), not here, so
# this stays a literal substring of whatever renders.
ANOMALY_BANNER_TEXT = "Something needs attention — check the tiles below."

_SEVERITY_BANNER_NOUNS = {"warn": "warning", "error": "error"}  # falls
# back to "issue" for any severity not in this dict.

DEVICE_FRESHNESS_LABEL = "Device last checked in"
# Plain-language visible label; the technical term stays one hover away
# via `caption_title` at the tile's stat_tile() call site below.
PIPELINE_FRESHNESS_LABEL = "Flight data last updated"
PIPELINE_FRESHNESS_TITLE = "ADS-B pipeline last ran"

CORROBORATION_TILE_LABEL = "Do the two data sources agree?"
CORROBORATION_TILE_TITLE = "Corroboration"

LAST_DETECTION_LABEL = "Last aircraft detected"

# Evidence only ("since it started"), never the state name, so it is
# safe to publish verdict-free as compute_health_state()'s
# "pipeline_detail_html" key.
PIPELINE_NEVER_RAN_DETAIL_TEXT = "The frame has not reported a flight since it started."

# A short plain-sentence verdict for each stat tile whose caption names
# a signal but whose border colour alone was the only place the actual
# verdict lived (WCAG 1.4.1: colour must never be the sole means of
# conveying information). The Resolution-rate tile deliberately has no
# sibling dict here — see render()'s own comment at that tile's
# stat_tile() call.
DEVICE_STATE_TEXT = {
    "ok": "Checking in normally",
    "warn": "Has not checked in for a while",
    "error": "Has not checked in for a long time",
    # A genuine fourth device state, not merely "hasn't checked in for a
    # while": a frame the strip/tile both know is quiet-hours-held.
    # Reuses the "off" token the pipeline's never-ran state and the
    # strip's held dot use, a neutral state that is never a problem. A
    # held frame is routed here only when frame_state.resolve_state()
    # says STATE_HELD.
    "off": "Asleep for quiet hours",
}

# Maps frame_state's own three states to this tile's device_state
# vocabulary: due -> "ok", held -> neutral "off" (never "warn"/"error",
# so it can never light the nav dot), late -> "warn". STATE_UNKNOWN is
# absent: _device_section() falls back to the age-based
# staleness_status() path for that state instead.
_FRAME_STATE_TO_DEVICE_STATE = {
    frame_state.STATE_DUE: "ok",
    frame_state.STATE_HELD: "off",
    frame_state.STATE_LATE: "warn",
}
PIPELINE_STATE_TEXT = {
    "ok": "Running on schedule",
    "warn": "A little behind",
    "error": "Has not run for a long time",
    "off": "No detection yet",
}
CORROBORATION_STATE_TEXT = {
    "ok": "Sources agree",
    "warn": "Sources disagreed recently",
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
SPARKLINE_HIT_CLASS = "sparkline-hit"
SPARKLINE_DOT_CLASS = "sparkline-dot"
SPARKLINE_LINE_CLASS = "sparkline-line"
SPARKLINE_AXIS_CLASS = "sparkline-axis"
# Two classes for two elements: a nested <svg> layer owning the
# coordinate system, and the filled <polygon> inside it.
SPARKLINE_AREA_LAYER_CLASS = "sparkline__area"
SPARKLINE_AREA_CLASS = "sparkline-area"
SPARKLINE_MARK_CLASS = "sparkline-mark"
SPARKLINE_THRESHOLD_CLASS = "sparkline-threshold"
SPARKLINE_LEGEND_ROW_CLASS = "sparkline__legend"
SPARKLINE_LEGEND_CLASS = "sparkline-legend"
SPARKLINE_LEGEND_SWATCH_CLASS = "sparkline-swatch"
# Must equal companion/app.py's SCRIPT_ROUTE — duplicated, not imported,
# since companion/pages/__init__.py forbids a page module importing
# companion.app (app.py imports pages, so the reverse would be
# circular). The test harness asserts the two stay equal.
BATTERY_TREND_SCRIPT_SRC = "/static/battery-trend.js"

# "%d" is interpolated with BATTERY_TREND_WINDOW_DAYS // 30 at the one
# call site, never a typed literal, so the heading cannot silently drift
# from the window the chart plots.
BATTERY_SECTION_HEADING_TEMPLATE = "Battery · %d months"
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
CHECK_IN_SECTION_HEADING = "Check-in regularity"

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
    wake.CHECK_IN_ON_CADENCE: "On cadence",
    wake.CHECK_IN_LATE: "Late",
    wake.CHECK_IN_MISSING: "Missing",
    wake.CHECK_IN_UNKNOWN: "No record",
}

# The caption's clauses, one constant each: only CHECK_IN_CAPTION_OBSERVED
# renders in the card's always-visible caption; every other clause moves
# into a `<details class="readings-disclosure">` immediately after it
# (see `_check_in_regularity_section_html()`).
CHECK_IN_CAPTION_OBSERVED = (
    "Each cell is one day of observed check-in regularity, oldest first.")
# The cadence actually in force on an earlier day is not recoverable
# (device_config.json is a current-state file), so naming it without
# this qualifier would be a claim about the past made from a present value.
CHECK_IN_CAPTION_CADENCE = (
    "Judged against the cadence configured now — a check-in every %s — not "
    "necessarily the cadence in force on an earlier day.")
# When there is no cadence to name at all: device_staleness_thresholds()'
# bare floors apply, and the caption must say so rather than print an
# assumed default.
CHECK_IN_CAPTION_CADENCE_FALLBACK = (
    "This frame's cadence cannot be determined, so the grid is judged against "
    "the fallback staleness floors rather than against a configured cadence.")
# What a gap is not: the record cannot tell a wake the frame missed from
# a log range this server lost, so a grid without this sentence would
# make a claim its own data cannot support.
CHECK_IN_CAPTION_NOT_PROOF = (
    "A day with no record is not proof the frame did not wake: a log rotation "
    "this server missed leaves exactly the same gap.")
# The empty deployment: a real case, rendering an honest grid of
# no-observation cells rather than a missing section.
CHECK_IN_CAPTION_EMPTY = (
    "No check-in intervals are recorded yet, so every day below is a day the "
    "record says nothing about.")

# The per-cell tooltip and the grid's own accessible name. The gap is
# named as a DURATION in the app's own form (layout.duration_text()) and
# the day as a local date — every visible instant in this app is
# Europe/Paris and a raw ISO string survives only behind a copy control.
CHECK_IN_CELL_TITLE = "%s — %s: longest observed gap %s"
CHECK_IN_CELL_TITLE_NONE = "%s — %s"
CHECK_IN_GRID_LABEL = (
    "Observed check-in regularity, one cell per day over the last %d days: "
    "%d on cadence, %d late, %d missing, %d with no record.")

# The two id-anchored sections Health's body is split into.
# SERVER_DATA_SECTION_ID is a cross-page coupling: history_page.py links
# to this exact anchor (#server-data) — renaming it silently breaks that
# link.
SCREEN_SECTION_ID = "screen"
SCREEN_SECTION_HEADING = "Screen"
SERVER_DATA_SECTION_ID = "server-data"
SERVER_DATA_SECTION_HEADING = "Server & data"
# Plain-language label; the technical term stays reachable via
# `caption_title` at this tile's stat_tile() call site below.
RESOLUTION_RATE_LABEL = "Flights we could name"
RESOLUTION_RATE_TITLE = "Route resolution rate"
UNRESOLVED_SECTION_HEADING = "Airlines we could not name"
STATS_SECTION_HEADING = "How well we name flights"

# Keep the leading em-dash and the space after it on both descriptions:
# that is what makes the heading and its description read as one
# continuous phrase across the baseline-aligned `.section-intro` row.
PAGE_PURPOSE_TEXT = "Screen status and server data quality, in one place."
SCREEN_SECTION_DESCRIPTION = (
    "— the physical frame: is it checking in, and how's the battery.")
SERVER_DATA_SECTION_DESCRIPTION = (
    "— the ADS-B pipeline and route resolution: is the data fresh and "
    "trustworthy.")

_NO_GAPS_HEADING = "No coverage gaps."
_NO_GAPS_BODY = (
    "Every airline we've seen recently has been named — nothing left to look up.")

# The genuine reference material — where resolution happens and what it
# does — lives in _READ_ONLY_NOTE_DETAIL below, rendered in a `<details
# class="readings-disclosure">` immediately after this visible sentence.
_READ_ONLY_NOTE = "This list is read-only here."
_READ_ONLY_NOTE_DETAIL = (
    "Each row's Resolve link opens the Airlines page to name that airline "
    "(and add artwork, if it needs one).")

# The heading is a %-template interpolated with RESOLUTION_WINDOW_DAYS
# at the one call site, never a literal "30", so it cannot silently
# drift from the window constant.
_NO_STATS_HEADING = "No flights in the last %d days"
_NO_STATS_BODY = (
    "The frame has not recorded a detection in this window. It will "
    "appear here after the next wake.")

# Only the event count varies between these templates; the day count is
# always RESOLUTION_WINDOW_DAYS, so a "1 day" singular form would be
# dead copy. Singular chosen at the call site, never a runtime "add an
# s" rule, which French cannot express (it pluralises the noun and
# needs article agreement too).
_RESOLUTION_DETAIL_TEMPLATE = "over the last %d days, %d events"
_RESOLUTION_DETAIL_SINGULAR_TEMPLATE = "over the last %d days, %d event"

RESOLUTION_WINDOW_DAYS = 30  # A month smooths over a quiet week at this
# single-airport traffic volume, while still reading as "recent".

# The four categories server/plane/enrich.py's resolve_route() documents,
# plus a fifth ("manual", an operator answering by hand at runtime from
# this companion web interface), in a fixed display order with a
# plain-English gloss so the page is readable without the source. The
# live/cache/static-table distinction is kept deliberately: collapsing
# it would hide which mechanism actually resolved the route.
_SOURCE_ROWS = (
    ("fresh_hit", "Fresh lookup",
     "A live lookup in the route database resolved a full route this cycle."),
    ("cache_hit", "Cached hit",
     "A previously-cached route was reused, sparing a network request."),
    ("airline_only", "Airline only",
     "The route database had no route, but the callsign's ICAO prefix "
     "identified the airline from the static prefix table."),
    ("miss", "Miss",
     "Neither the route database nor the static prefix table resolved "
     "anything for this callsign, so it shows up in the %s list above."
     % UNRESOLVED_SECTION_HEADING),
    ("manual", "Manual",
     "The operator resolved this callsign's prefix by hand, from the "
     "companion web interface."),
)

# A sixth, catch-all row for any route_source value outside the five
# above; folded in rather than dropped from the total. Kept out of
# _SOURCE_ROWS itself: that tuple is the fixed, ordered enumeration of
# known mechanisms, and folding an "unknown" bucket into it would
# misrepresent it as a sixth understood mechanism.
_OTHER_SOURCE_LABEL = "Other"
_OTHER_SOURCE_GLOSS = (
    "A route source this page does not recognise, or none was recorded "
    "at all — still counted here so the total always matches every "
    "event in the window.")

# Single-sourced so the table and the mobile card list can never
# disagree on a header word. Index 2 ("Count") is read directly by the
# card builder; "Description" has no card-side equivalent, since the
# mobile card renders the full description as stacked prose.
_STATS_HEADERS = ("Source", "Description", "Count")

# Driven client-side by list-filter.js's data-filter-* attribute
# contract. No hyphen in this value: see history_page.py's own
# `_FILTER_INPUT_ID` comment for the WebKit/Safari contacts-autofill
# explanation.
_FILTER_INPUT_ID = "airlines_filter_input"
_FILTER_LABEL_TEXT = "Filter by prefix"
_FILTER_EMPTY_HEADING = "No matching prefixes"
_FILTER_EMPTY_BODY_TEMPLATE = (
    "Try a different search, or Clear filter to see all %d prefixes.")

_DB_UNAVAILABLE = object()  # sentinel distinguishing "query raised" from
# "query succeeded and legitimately returned None/empty" (e.g. no rows
# recorded yet), which must render very differently.


def _safe_query(state_dir, fn):
    """Run `fn(conn)` against a fresh `history_db` connection, returning
    `_DB_UNAVAILABLE` instead of raising when the database is missing (and
    cannot be created), locked, or otherwise unreadable (sqlite3.Error /
    OSError) — so one section's data access can never fault the whole
    page render.
    """
    try:
        with history_db.open_db(state_dir) as conn:
            return fn(conn)
    except (sqlite3.Error, OSError):
        return _DB_UNAVAILABLE


def _cutoff_iso(now_ts, days):
    now_parsed = layout.parse_iso(now_ts)
    if now_parsed is None:
        return None
    return (now_parsed - timedelta(days=days)).isoformat(timespec="seconds")


def _meta_flag_true(value):
    """A defensive parse of a history_db boolean meta value: `set_meta()`
    stores everything as TEXT, and `"True"` (`str(bool_value)`) is the
    expected on-value; `"1"` is accepted as a fallback for other writer
    conventions. Anything else is false. Never raises.
    """
    return value in ("True", "1")


def staleness_status(age_seconds, warn_s, error_s):
    """One of `"ok"`/`"warn"`/`"error"`: a signal older than `error_s` is
    an error, older than `warn_s` (but under `error_s`) is a warning.
    "Never seen" (`age_seconds is None`) maps to `"warn"`, not `"error"`,
    since a freshly-provisioned deployment has no history yet. A
    negative age (clock skew) is treated as zero.
    """
    if age_seconds is None:
        return "warn"
    if age_seconds < 0:
        age_seconds = 0
    if age_seconds >= error_s:
        return "error"
    if age_seconds >= warn_s:
        return "warn"
    return "ok"


def offbox_backup_status(now):
    """The off-box backup freshness signal, read from `os.environ` on
    every call rather than resolved once at import time, so a deployment
    that sets the env var later is still seen.

    Returns `None` when the env var is unset or empty: the caller
    renders no card and folds no state into severity. Otherwise returns
    `{"state": "ok"|"warn", "snapshot_ts": <ISO str or None>}`; `state`
    is capped at "warn" (the file gate going dark is not the same fault
    as the flight-data pipeline) via `error_s=float("inf")`.

    Never raises: a missing file, path-traversal-shaped name, empty
    content, binary garbage, or an oversized file all degrade to
    `{"state": "warn", "snapshot_ts": None}`, the same shape as "never
    pulled". At most 256 bytes are ever read.
    """
    marker_path = os.environ.get(OFFBOX_MARKER_ENV_VAR)
    if not marker_path:
        return None
    try:
        with open(marker_path, "rb") as handle:
            raw = handle.read(256)
        text = raw.decode("ascii").strip()
        match = _OFFBOX_MARKER_RE.match(text)
        if not match:
            return {"state": "warn", "snapshot_ts": None}
        snapshot_dt = datetime.strptime(
            match.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    except (OSError, ValueError):
        return {"state": "warn", "snapshot_ts": None}
    snapshot_ts = snapshot_dt.isoformat()
    age = layout.age_seconds(snapshot_ts, now)
    state = staleness_status(age, OFFBOX_WARN_S, float("inf"))
    return {"state": state, "snapshot_ts": snapshot_ts}


def battery_trend_rows(conn):
    """The most recent `BATTERY_TREND_LIMIT` `device_health` rows, newest
    first. The LIMIT is a display choice for readability, not a
    retention policy: history is kept forever, nothing is deleted here.
    """
    return history_db.recent_device_health(conn, limit=BATTERY_TREND_LIMIT)


def battery_daily_rows(conn, now):
    """The chart's primary series: one point per Europe/Paris calendar
    day over the last `BATTERY_TREND_WINDOW_DAYS`, via
    `history_db.daily_battery_averages()`.

    `_cutoff_iso()` returns `None` when `now` fails to parse, and
    `daily_battery_averages(conn, since=None)` degrades to an unbounded
    read rather than an empty one, so it shows more history rather than
    an empty card on the one input this function does not control.
    """
    return history_db.daily_battery_averages(
        conn, since=_cutoff_iso(now, BATTERY_TREND_WINDOW_DAYS))


def _battery_daily_series_usable(daily_rows):
    """True when there are at least two Europe/Paris-day buckets to plot
    as a trend, kept in exactly one place so `_battery_section()` and
    `_battery_trend_caption()` can never disagree about which series is
    on screen. `daily_rows` may be the `_DB_UNAVAILABLE` sentinel: a
    failed read is never "usable".
    """
    return isinstance(daily_rows, list) and len(daily_rows) >= 2


def _real_trend_reading_count(trend_rows):
    """The number of `trend_rows` `battery_sparkline_svg()` will
    actually plot: the same numeric-only filter that function applies,
    since `BATTERY_TREND_LIMIT` is a query limit, not a guarantee that
    many rows exist — a fresh deployment with 3 readings must not have
    its caption claim the full limit.
    """
    return sum(
        1 for row in trend_rows
        if isinstance(row.get("battery_mv"), int) and not isinstance(row.get("battery_mv"), bool))


def _battery_trend_caption(trend_rows, daily_rows):
    """The heading caption text, honest about which series is on screen:
    uses `_battery_daily_series_usable()`, the same predicate
    `_battery_section()` uses, so the two can never disagree. Three
    cases: the daily series plotted, no readings at all (same 3-month
    framing), or a fallback of fewer than two days of raw readings
    ("Latest %d readings", the real count, never a fixed limit).
    """
    if _battery_daily_series_usable(daily_rows):
        return i18n.t("Last 3 months, daily average")
    if not trend_rows or trend_rows is _DB_UNAVAILABLE:
        return i18n.t("Last 3 months, daily average")
    return i18n.t("Latest %d readings") % _real_trend_reading_count(trend_rows)


# No hand-estimated gutter: the CSS-grid label column is sized `auto`,
# so the browser measures the real widest-label width. With no viewBox,
# cx is a percentage of the canvas's own rendered width, so the canvas
# is the plot area edge to edge.

# Declared once here and in style.css's `.battery-trend-section
# svg:not(.icon)` rule: every point coordinate is a percentage of this
# height, so a responsive height would silently move every point.
_SPARKLINE_CANVAS_HEIGHT_PX = 160

# Vertical margin the plotted line never crosses, as a percent of canvas
# height: at least the marker's own radius so no dot is clipped, and set
# to half the axis label's line box so labels centre on the level they name.
_SPARKLINE_VERTICAL_INSET_PERCENT = 3.75

# A fixed Y-axis range, never auto-scaled: auto-scaling pinned a flat
# series to the canvas bottom and stretched a tiny real wiggle to fill
# the whole range. The percentage beside the chart comes from a
# different, piecewise discharge curve, so equal vertical distances here
# are not equal percentages. A reading below 3000 mV clamps to the floor.
SPARKLINE_Y_MIN_MV = 3000
SPARKLINE_Y_MAX_MV = 4200
_SPARKLINE_Y_SPAN_MV = SPARKLINE_Y_MAX_MV - SPARKLINE_Y_MIN_MV

_SPARKLINE_DOT_RADIUS_PX = 3
_SPARKLINE_HIT_RADIUS_PX = 8

# Strictly larger than the dot radius so the mark reads as a mark, and
# no larger than the vertical inset so it isn't clipped at the edge.
_SPARKLINE_MARK_RADIUS_PX = 5

# The point count at which the daily chart's cosmetic dots stop reading
# as separate marks. Derived from a live-measured 226px canvas width at
# a 375px viewport with a 90-day dataset.
_SPARKLINE_NARROWEST_CANVAS_PX = 226


def _sparkline_dense_threshold(canvas_width_px):
    """The first integer point count at which evenly spread points sit
    closer together than the cosmetic dot's own diameter, for a canvas
    `canvas_width_px` CSS pixels wide. The server cannot know a client's
    actual rendered width (no viewBox), so this is always called with
    the narrowest width this project has measured — conservative, not a
    guarantee for a still-narrower container.
    """
    spacing_ceiling_px = 2 * _SPARKLINE_DOT_RADIUS_PX
    return int(canvas_width_px / spacing_ceiling_px + 1) + 1


_SPARKLINE_DENSE_POINT_THRESHOLD = _sparkline_dense_threshold(_SPARKLINE_NARROWEST_CANVAS_PX)

# The reduced hit-target radius at/above the density threshold: smaller
# than the normal 8px so heavily overlapping hit circles no longer
# nearly-fully overlap; every point stays reachable via the
# roving-tabindex/arrow-key keyboard path, which is unaffected.
_SPARKLINE_DENSE_HIT_RADIUS_PX = 4


def sparkline_point_y(value):
    """The y position `value` gets on the battery chart, as a percentage
    of canvas height. Shared by every non-reading chart element (area
    baseline, threshold line) so none can drift from the plotted line.
    Clamped into the fixed Y range, so an out-of-range value draws
    pinned at the canvas edge; inverted to match SVG's top-down axis.
    """
    inset = _SPARKLINE_VERTICAL_INSET_PERCENT
    clamped = max(SPARKLINE_Y_MIN_MV, min(SPARKLINE_Y_MAX_MV, value))
    return inset + (
        1 - (clamped - SPARKLINE_Y_MIN_MV) / _SPARKLINE_Y_SPAN_MV
    ) * (100 - 2 * inset)


# The hover/tap readout's text, as constants so the French catalogue
# (companion/i18n_fr/health.py) carries them.
BATTERY_AVERAGE_WHEN_ONE_TEMPLATE = "%s — daily average (%d reading)"
BATTERY_AVERAGE_WHEN_MANY_TEMPLATE = "%s — daily average (%d readings)"
BATTERY_AVERAGE_WHEN_BARE_TEMPLATE = "%s — daily average"

# The drawn low-battery threshold's label names what the line means, not
# just what it is worth. Prints the percentage beside the level because
# the level is the millivolt reading at which battery.py's estimate
# returns that percentage, tying the line to the same figure the readout
# and ring print above the chart.
BATTERY_THRESHOLD_LABEL_TEMPLATE = "Low battery — %d mV (≈ %d%%)"

# The sentinel and helper live in companion/layout.py, since the
# freshness line this page shares with Home and the Display scope needs
# the same full local timestamp, and a page module cannot import another.
_FULL_TIMESTAMP_SENTINEL_NOW = layout.FULL_TIMESTAMP_SENTINEL_NOW


def _full_local_timestamp_text(ts):
    """"D Mon HH:MM" in Europe/Paris — see
    `layout.full_local_timestamp_text()`, of which this is the delegate.
    """
    return layout.full_local_timestamp_text(ts)


def _as_paris(parsed):
    """A naive datetime is taken as UTC (matching
    `history_db.utc_now_iso()`'s output), then converted to
    Europe/Paris. Shared by every helper below that renders a battery
    timestamp, so there is exactly one place a stored `ts` crosses into
    local wall-clock time.
    """
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo("UTC"))
    return parsed.astimezone(layout.LOCAL_TZ)


def _axis_clock_label(ts):
    """"HH:MM" Europe/Paris clock text for a battery-chart X-axis label.
    Built through `layout.local_clock_text()` with no `now_parsed`,
    which keeps this a bare clock rather than the day-qualified form.
    Falls back to the raw `ts` string, never raising, when it fails to
    parse.
    """
    parsed = layout.parse_iso(ts)
    return layout.local_clock_text(parsed) if parsed is not None else (ts or "")


def _axis_day_label(ts):
    """"D Mon" X-axis label for the chart's daily mode, for a `ts` that
    names a whole Europe/Paris calendar day: `_axis_clock_label()` would
    parse it fine but print "00:00" for every day, hence this sibling.
    Uses `layout.month_abbr()`, not `strftime`'s locale-dependent
    directive. Falls back to the raw `ts` string when it fails to parse.
    """
    parsed = layout.parse_iso(ts)
    if parsed is None:
        return ts or ""
    local = _as_paris(parsed)
    return "%d %s" % (local.day, layout.month_abbr(local.month))


def _battery_reading_parts(mv, ts, now):
    """The plain-text `(value, when)` pair every rendering of one
    battery reading shares, computed once so they can't drift apart.
    `value` is "≈ NN% · {mv} mV" when the estimate resolves, else bare
    "{mv} mV" (the frame's own warning uses the exact mV threshold, not
    this estimate). Returns unescaped text, not markup: `battery-trend.js`
    rewrites the readout via `textContent`, which would destroy markup.
    """
    pct = battery.battery_percent(mv)
    value = ("≈ %d%% · %s mV" % (pct, mv)) if pct is not None else ("%s mV" % mv)
    age = layout.age_seconds(ts, now)
    if age is None:
        return value, (ts or "")
    when = "%s (%s)" % (_full_local_timestamp_text(ts), layout.relative_age_text(age))
    return value, when


def _daily_reading_parts(mv, ts, reading_count):
    """`_battery_reading_parts()`'s sibling for a daily-average chart
    point: names that the value is an average, not a raw reading, so a
    hovered point can't be mistaken for the resting readout. Degrades to
    a bare "daily average" phrase when `reading_count` is missing or not
    a positive int, since naming zero or an unknown count would mislead.
    """
    value = "%d mV" % mv
    day_label = _axis_day_label(ts)
    if isinstance(reading_count, int) and not isinstance(reading_count, bool) and reading_count > 0:
        template = (BATTERY_AVERAGE_WHEN_ONE_TEMPLATE if reading_count == 1
                    else BATTERY_AVERAGE_WHEN_MANY_TEMPLATE)
        when = i18n.t(template) % (day_label, reading_count)
    else:
        when = i18n.t(BATTERY_AVERAGE_WHEN_BARE_TEMPLATE) % day_label
    return value, when


def battery_sparkline_svg(rows, now=None, daily=False):
    """A minimal, dependency-free battery-trend chart built server-side
    from `rows` (newest-first). No external reference of any kind
    (`url(`, `<image`, a script tag). Each plotted point carries a
    cosmetic marker plus a transparent, enlarged, keyboard-focusable hit
    target with a `<title>` tooltip, so the reading is available on
    hover/tap with no JavaScript.

    Returns a `<div class="sparkline">` grid wrapper. The inner `<svg>`
    has no `viewBox`, so every horizontal position is a percentage and
    every size is an absolute CSS pixel at every container width; the
    trend line is `n - 1` `<line>` segments, since a `<polyline>` cannot
    take percentage coordinates. Also draws an area under the line (its
    own nested `<svg>` with a private viewBox), a mark on the newest
    point, and a low-battery threshold line read from
    `companion/battery.py`.

    Returns `""` when fewer than two rows carry a numeric `battery_mv`.
    `daily=True` plots daily aggregates instead of individual readings:
    axis and point labels switch to their day-aware siblings, and
    cosmetic dots suppress above `_SPARKLINE_DENSE_POINT_THRESHOLD`.
    """
    if now is None:
        now = history_db.utc_now_iso()
    chronological = list(reversed(rows))
    pairs = [
        (row.get("battery_mv"), row.get("ts"), row.get("reading_count"))
        for row in chronological
        if isinstance(row.get("battery_mv"), int) and not isinstance(row.get("battery_mv"), bool)
    ]
    if len(pairs) < 2:
        return ""
    point_count = len(pairs)
    # Keyed on point_count alone, not `daily`: the newest point's mark is
    # exempt from this dot-suppression rule (a different class, not a
    # cosmetic dot), so density and "keep the mark" cannot conflict.
    dense = point_count >= _SPARKLINE_DENSE_POINT_THRESHOLD
    hit_radius = _SPARKLINE_DENSE_HIT_RADIUS_PX if dense else _SPARKLINE_HIT_RADIUS_PX

    def _point_x(index):
        return index / (point_count - 1) * 100

    _point_y = sparkline_point_y

    # Filled <rect> elements, not stroked <line>: an axis-aligned
    # integer-width filled rect has no stroke-centring to reason about,
    # and can pair a percentage position with an absolute size (needed
    # since every tick mixes both).
    axis_chrome = (
        # Y axis, X axis, then Y ticks (max/min, poking into the label
        # gap) and X ticks (oldest/newest, hanging below the axis).
        '<rect class="%s" x="0" y="0" width="1" height="100%%" aria-hidden="true"/>'
        '<rect class="%s" x="0" y="100%%" width="100%%" height="1" aria-hidden="true"/>'
        '<rect class="%s" x="-4" y="%.2f%%" width="4" height="1" aria-hidden="true"/>'
        '<rect class="%s" x="-4" y="%.2f%%" width="4" height="1" aria-hidden="true"/>'
        '<rect class="%s" x="%.2f%%" y="100%%" width="1" height="4" aria-hidden="true"/>'
        '<rect class="%s" x="%.2f%%" y="100%%" width="1" height="4" aria-hidden="true"/>'
    ) % (
        SPARKLINE_AXIS_CLASS,
        SPARKLINE_AXIS_CLASS,
        SPARKLINE_AXIS_CLASS, _point_y(SPARKLINE_Y_MAX_MV),
        SPARKLINE_AXIS_CLASS, _point_y(SPARKLINE_Y_MIN_MV),
        SPARKLINE_AXIS_CLASS, _point_x(0),
        SPARKLINE_AXIS_CLASS, _point_x(point_count - 1),
    )

    # SVG paints in document order; the cosmetic marker is emitted
    # immediately before its own hit target so it is never visually
    # painted under it (`.sparkline-dot`'s `pointer-events: none` is
    # what actually lets a tap reach the target regardless of order).
    line_segments = []
    circles = []
    plotted = []
    prev_x = prev_y = None
    for index, (value, ts, reading_count) in enumerate(pairs):
        x = _point_x(index)
        y = _point_y(value)
        plotted.append((x, y))
        if prev_x is not None:
            line_segments.append(
                '<line class="%s" x1="%.2f%%" y1="%.2f%%" x2="%.2f%%" y2="%.2f%%"/>'
                % (SPARKLINE_LINE_CLASS, prev_x, prev_y, x, y))
        prev_x, prev_y = x, y

        # Computed from `pairs`, never `rows`: the newest stored row may
        # carry no battery_mv, and a mark derived from it would point at
        # a reading the chart never plotted.
        is_latest = index == point_count - 1

        # Above the density threshold, the cosmetic dot is suppressed
        # but the hit target below still emits at a reduced radius, so
        # every point stays reachable. The latest point always gets the
        # mark (a different class, emitted in the same loop rather than
        # a second circle appended afterwards, to stay inside the
        # roving-tabindex sequence the hit targets establish).
        if is_latest:
            circles.append(
                '<circle class="%s" cx="%.2f%%" cy="%.2f%%" r="%d" aria-hidden="true"/>'
                % (SPARKLINE_MARK_CLASS, x, y, _SPARKLINE_MARK_RADIUS_PX))
        elif not dense:
            circles.append(
                '<circle class="%s" cx="%.2f%%" cy="%.2f%%" r="%d" aria-hidden="true"/>'
                % (SPARKLINE_DOT_CLASS, x, y, _SPARKLINE_DOT_RADIUS_PX))

        if daily:
            _value_text, when_text = _daily_reading_parts(value, ts, reading_count)
        else:
            _value_text, when_text = _battery_reading_parts(value, ts, now)
        # Tooltip, aria-label and data-when carry the same string, never
        # a "value — when" composite: battery-trend.js's reveal() writes
        # data-mv into the readout separately and prepends its own
        # " — ", so duplicating the value here would print it twice.
        escaped_when = escape_html(when_text)
        # Roving tabindex: only the latest (rightmost) point is a normal
        # Tab stop; every other point is reachable via
        # battery-trend.js's arrow-key handler instead.
        tabindex = "0" if is_latest else "-1"
        circles.append(
            '<circle class="%s" cx="%.2f%%" cy="%.2f%%" r="%d" tabindex="%s" '
            'role="button" data-mv="%d" data-ts="%s" data-when="%s" aria-label="%s">'
            "<title>%s</title></circle>"
            % (SPARKLINE_HIT_CLASS, x, y, hit_radius, tabindex, value, escape_html(ts),
               escaped_when, escaped_when, escaped_when))

    # The low-battery threshold. Read from companion/battery.py, never
    # retyped: LOW_BATTERY_DISPLAY_MV is the companion's own display
    # threshold, a different number from server/poll_loop.py's device
    # hysteresis threshold — two numbers for two jobs.
    #
    # Placed by the same _point_y() every reading uses, so it cannot
    # drift from the readings it is compared against. Suppressed
    # entirely when the value falls outside the chart's fixed range:
    # _point_y() clamps, so an out-of-range threshold would draw pinned
    # to the axis edge and falsely read as "low starts at the bottom".
    threshold_mv = battery.LOW_BATTERY_DISPLAY_MV
    threshold_visible = (
        isinstance(threshold_mv, int) and not isinstance(threshold_mv, bool)
        and SPARKLINE_Y_MIN_MV < threshold_mv < SPARKLINE_Y_MAX_MV)
    threshold_rect = ""
    legend_html = ""
    if threshold_visible:
        threshold_rect = (
            '<rect class="%s" x="0" y="%.2f%%" width="100%%" height="1" aria-hidden="true"/>'
        ) % (SPARKLINE_THRESHOLD_CLASS, _point_y(threshold_mv))
        # A legend in its own row, not a third Y-label (the threshold
        # sits at 59.25%, not at top/bottom/middle). Not aria-hidden,
        # unlike the axis labels: nothing else announces where "low"
        # starts.
        legend_html = (
            '<div class="%s">'
            '<span class="%s"><span class="%s" aria-hidden="true"></span>%s</span>'
            "</div>"
        ) % (
            SPARKLINE_LEGEND_ROW_CLASS, SPARKLINE_LEGEND_CLASS,
            SPARKLINE_LEGEND_SWATCH_CLASS,
            escape_html(i18n.t(BATTERY_THRESHOLD_LABEL_TEMPLATE)
                        % (threshold_mv, battery.LOW_BATTERY_DISPLAY_PERCENT)),
        )

    # The area under the line: a nested <svg> with its own private
    # viewBox, since percentages aren't permitted in a <polygon> points
    # list and the outer canvas's no-viewBox scheme can't be traded away
    # (that would shrink every stroke/marker at small widths). No size
    # attributes of its own: style.css already sizes every <svg> in the
    # section. Baseline is the scale's own floor, not the canvas edge,
    # so the filled height stays the value above the axis minimum. Fill
    # is `currentColor` at reduced opacity, not a `<linearGradient>`,
    # which could only be referenced via `url(#id)` — forbidden by this
    # function's no-external-reference guarantee. Emitted first, so it
    # paints under the axis chrome, line segments and points.
    area_baseline_y = _point_y(SPARKLINE_Y_MIN_MV)
    area_points = " ".join(
        "%.2f,%.2f" % (x, y) for x, y in plotted
    ) + " %.2f,%.2f %.2f,%.2f" % (
        plotted[-1][0], area_baseline_y, plotted[0][0], area_baseline_y)
    area_layer = (
        '<svg class="%s" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">'
        '<polygon class="%s" points="%s"/>'
        "</svg>"
    ) % (SPARKLINE_AREA_LAYER_CLASS, SPARKLINE_AREA_CLASS, area_points)

    # Document order places max above min, oldest before newest (both
    # flex containers use space-between). These print the fixed
    # SPARKLINE_Y_MIN_MV/MAX_MV constants, never a per-render min/max, so
    # the axis matches the fixed range _point_y() draws against.
    y_labels_html = (
        '<div class="sparkline__y">'
        '<span class="sparkline-axis-label" aria-hidden="true">%d mV</span>'
        '<span class="sparkline-axis-label" aria-hidden="true">%d mV</span>'
        "</div>"
    ) % (SPARKLINE_Y_MAX_MV, SPARKLINE_Y_MIN_MV)
    x_labels_html = (
        '<div class="sparkline__x">'
        '<span class="sparkline-axis-label" aria-hidden="true">%s</span>'
        '<span class="sparkline-axis-label" aria-hidden="true">%s</span>'
        "</div>"
    ) % (
        escape_html(_axis_day_label(pairs[0][1]) if daily else _axis_clock_label(pairs[0][1])),
        escape_html(_axis_day_label(pairs[-1][1]) if daily else _axis_clock_label(pairs[-1][1])),
    )

    # Recomputed the same way the visible heading is, so the two can
    # never disagree.
    svg_html = (
        '<svg class="sparkline__canvas" role="group" aria-label="%s">'
        "%s%s%s%s%s"
        "</svg>"
    ) % (escape_html(i18n.t(BATTERY_SECTION_HEADING_TEMPLATE) % (BATTERY_TREND_WINDOW_DAYS // 30)),
         area_layer, axis_chrome, threshold_rect,
         "".join(line_segments), "".join(circles))

    # Grid document order: Y-label column, canvas, X-label row, then the
    # threshold legend (grid-column: 1 / -1 in style.css) — "" when no
    # threshold is drawn, so the row simply does not exist.
    return '<div class="sparkline">%s%s%s%s</div>' % (
        y_labels_html, svg_html, x_labels_html, legend_html)


def battery_status(rows):
    """`"warn"` when any two chronologically-consecutive readings in
    `rows` (newest-first) drop by more than `BATTERY_DROP_WARN_MV`,
    `"ok"` otherwise. Never `"error"`: a single sampling artefact must
    not paint the whole page as an outage — a sustained decline still
    shows up in the chart and percentage readout regardless. A row with
    a missing/non-numeric `battery_mv` is skipped rather than compared.
    """
    chronological = list(reversed(rows))
    for earlier, later in zip(chronological, chronological[1:]):
        earlier_mv = earlier.get("battery_mv")
        later_mv = later.get("battery_mv")
        if not isinstance(earlier_mv, int) or isinstance(earlier_mv, bool):
            continue
        if not isinstance(later_mv, int) or isinstance(later_mv, bool):
            continue
        if earlier_mv - later_mv >= BATTERY_DROP_WARN_MV:
            return "warn"
    return "ok"


def corroboration_status(counts):
    """Maps `history_db.corroboration_counts()`'s three-state dict to a
    per-row status: agreement and the single-source unknown state are
    always `"ok"`/`"off"` (never a failure — the unknown state is purely
    informational), and a disagreement bucket with a non-zero count is
    `"warn"`, deliberately not an error.
    """
    counts = counts or {}
    return {
        "True": "ok",
        # "off", not "ok": this row cannot honestly claim health for an
        # unknown (single-source) state, only that it is not a problem.
        "None": "off",
        "False": "warn" if counts.get("False") else "ok",
    }


def _offbox_anomaly_text(offbox):
    """The single anomaly sentence for a non-ok `offbox` status, or
    `None` when `offbox` is `None` or already `"ok"`. Shared by
    `collect_anomalies()` and `_offbox_section_html()` so the two can
    never read different words for the same state.
    """
    if offbox is None or offbox["state"] == "ok":
        return None
    if offbox["snapshot_ts"] is None:
        return i18n.t("No off-box backup has been pulled yet.")
    return i18n.t("No off-box backup in the last 3 days.")


def collect_anomalies(
    device_state, pipeline_state, battery_state, disagreement_warn,
    coverage_state="ok", source_fault=False, offbox=None,
):
    """A list of short, human-readable strings, one per non-healthy
    signal. An empty list means no anomaly banner renders; only the
    list's emptiness is consumed, and it stays the canonical, greppable
    definition of what counts as an anomaly. The nav-tab severity routes
    through `overall_severity()` instead, which derives severity from the
    same inputs.
    """
    anomalies = []
    # device_state/pipeline_state can be "off" (held frame / pipeline
    # never ran) — treated identically to "ok", never as an anomaly: a
    # held or never-run signal is not the same fact as a stale one.
    if device_state not in ("ok", "off"):
        anomalies.append(i18n.t("Device check-in is stale."))
    if pipeline_state not in ("ok", "off"):
        anomalies.append(i18n.t("Flight data is stale."))
    if battery_state != "ok":
        anomalies.append(i18n.t("Battery dropped abnormally."))
    if disagreement_warn:
        anomalies.append(i18n.t("Data sources disagreed recently."))
    if coverage_state != "ok":
        anomalies.append(i18n.t("Some airlines are unidentified."))
    if source_fault:
        anomalies.append(i18n.t("All data sources failed."))
    offbox_text = _offbox_anomaly_text(offbox)
    if offbox_text:
        anomalies.append(offbox_text)
    return anomalies


def overall_severity(
    device_state, pipeline_state, battery_state, disagreement_warn,
    coverage_state="ok", source_fault=False, offbox_state="ok",
):
    """Derives one "ok"/"warn"/"error" severity from the same signals
    `collect_anomalies()` tracks, in precedence order: (1) `source_fault`
    wins outright, every ADS-B source failed so severity is "error"
    regardless of anything else; (2) otherwise "error" if any of the
    three states equals "error"; (3) otherwise "warn" if any state is
    "warn", or `disagreement_warn`, `coverage_state`, or `offbox_state`
    is "warn"; (4) otherwise "ok". `offbox_state` can never reach
    "error" here: a stale off-box backup is a warning, not a page-wide
    error. "off" (held frame / pipeline never run) is treated as
    healthy, so it can never light the nav notification dot.
    """
    if source_fault:
        return "error"
    states = (device_state, pipeline_state, battery_state)
    if "error" in states:
        return "error"
    if (
        "warn" in states or disagreement_warn or coverage_state == "warn"
        or offbox_state == "warn"
    ):
        return "warn"
    return "ok"


def _device_resolved_state(next_wake_iso, effective_interval_s, hold_reason, now):
    """The one `frame_state.resolve_state()` call both `_device_state()`
    and `_device_section()` key off, so a due/held/late/unknown verdict
    can never differ between the state-only path and the tile markup.
    """
    return frame_state.resolve_state(next_wake_iso, effective_interval_s, hold_reason, now)


def _device_state(
        device_health, now, warn_s=None, error_s=None,
        next_wake_iso=None, effective_interval_s=None, hold_reason=None):
    """The Device tile's `"ok"`/`"warn"`/`"error"`/`"off"` verdict alone,
    with no markup built: the exact state logic `_device_section()` used
    to compute inline, now shared so `health_signals()` can read it
    without ever calling a markup builder.
    """
    if device_health is _DB_UNAVAILABLE:
        return "ok"
    if warn_s is None or error_s is None:
        warn_s, error_s = wake.device_staleness_thresholds(None)
    resolved_state = _device_resolved_state(
        next_wake_iso, effective_interval_s, hold_reason, now)
    if resolved_state == frame_state.STATE_UNKNOWN:
        ts = (device_health or {}).get("ts")
        age = layout.age_seconds(ts, now)
        return staleness_status(age, warn_s, error_s)
    return _FRAME_STATE_TO_DEVICE_STATE[resolved_state]


def _pipeline_state(pipeline_ts, last_detection, now):
    """The Pipeline tile's verdict alone, with no markup built: the exact
    state logic `_pipeline_section()` used to compute inline.
    """
    if pipeline_ts is _DB_UNAVAILABLE:
        return "ok"
    if _pipeline_never_ran(pipeline_ts, last_detection):
        return "off"
    age = layout.age_seconds(pipeline_ts, now)
    return staleness_status(age, STALE_PIPELINE_WARN_S, STALE_PIPELINE_ERROR_S)


def _battery_state(trend_rows, daily_rows=None):
    """The Battery tile's verdict alone, with no markup built.
    `battery_status()` is already pure state logic; this only restates
    the two early-exit cases (`_DB_UNAVAILABLE`, no readings yet)
    `_battery_section()` special-cases before ever reaching it, so a
    caller with no markup to build never needs that function at all.
    `daily_rows` plays no part in the verdict (only in which series the
    chart plots) but is accepted for signature symmetry with
    `_battery_section()`.
    """
    if trend_rows is _DB_UNAVAILABLE:
        return "ok"
    if not trend_rows:
        return "ok"
    return battery_status(trend_rows)


def _disagreement_warn(counts):
    """The Corroboration tile's disagreement flag alone, with no markup
    built: the exact state logic `_corroboration_section()` used to
    compute inline.
    """
    if counts is _DB_UNAVAILABLE:
        return False
    counts = counts or {}
    if not any(counts.values()):
        return False
    return bool(counts.get("False"))


def health_signals(state_dir, now=None):
    """Every state the nav-tab dot and the full Health page banner need
    — severity, the anomaly list, and each section's own state — derived
    from one `_read_health_inputs()` read, with zero markup built. This
    is the snapshot `health_state_from_signals()` renders from and
    `compute_health_state()` composes with it; nothing computed here is
    ever recomputed downstream, only rendered.

    Returns a dict carrying `now`, the raw `inputs` dict (consumed by the
    markup step), the device cadence/staleness/next-wake triple, every
    section's state, `disagreement_warn`, `coverage_state`,
    `source_fault`/`source_fault_raw`, `registry_rows`, `offbox`,
    `severity` and `anomalies`.
    """
    if now is None:
        now = history_db.utc_now_iso()
    inputs = _read_health_inputs(state_dir, now)
    # The device's effective wake cadence resolves to its staleness
    # thresholds, computed once here. The regularity grid judges its
    # cells against this same cadence and names it in its caption, so it
    # is held in a local rather than recomputed inline.
    wake_interval_s = wake.effective_wake_interval_s(inputs["device_config"])
    warn_s, error_s = wake.device_staleness_thresholds(wake_interval_s)
    # The same triple companion/layout.py's frame_strip_html() consumes,
    # computed from the same last-check-in timestamp and device config.
    device_ts = None
    if inputs["device_health"] is not _DB_UNAVAILABLE:
        device_ts = (inputs["device_health"] or {}).get("ts")
    next_wake_iso, effective_interval_s, hold_reason = wake.next_wake_status(
        device_ts, inputs["device_config"])
    device_state = _device_state(
        inputs["device_health"], now, warn_s=warn_s, error_s=error_s,
        next_wake_iso=next_wake_iso, effective_interval_s=effective_interval_s,
        hold_reason=hold_reason)
    pipeline_state = _pipeline_state(inputs["pipeline_ts"], inputs["last_detection"], now)
    battery_state = _battery_state(inputs["trend_rows"], inputs["daily_rows"])
    disagreement_warn = _disagreement_warn(inputs["corroboration_counts"])
    coverage_state = coverage_status(inputs["registry_rows"])
    source_fault = _meta_flag_true(inputs["source_fault_raw"])
    # Read exactly once per request, here — never independently inside
    # overall_severity()/collect_anomalies()/render(), which would risk
    # two reads (and two verdicts) disagreeing within one response.
    offbox = offbox_backup_status(now)
    offbox_state = offbox["state"] if offbox is not None else "ok"
    severity = overall_severity(
        device_state, pipeline_state, battery_state, disagreement_warn,
        coverage_state=coverage_state, source_fault=source_fault,
        offbox_state=offbox_state)
    anomalies = collect_anomalies(
        device_state, pipeline_state, battery_state, disagreement_warn,
        coverage_state=coverage_state, source_fault=source_fault,
        offbox=offbox)
    return {
        "now": now,
        "inputs": inputs,
        "wake_interval_s": wake_interval_s,
        "warn_s": warn_s,
        "error_s": error_s,
        # The frame-strip and freshness-token triple: published here
        # (rather than only inside the markup step) so a caller that
        # never renders markup — the freshness token, later — can still
        # read it from one snapshot.
        "next_wake_iso": next_wake_iso,
        "effective_interval_s": effective_interval_s,
        "hold_reason": hold_reason,
        "device_state": device_state,
        "pipeline_state": pipeline_state,
        "battery_state": battery_state,
        "disagreement_warn": disagreement_warn,
        "coverage_state": coverage_state,
        "source_fault": source_fault,
        "source_fault_raw": inputs["source_fault_raw"],
        "registry_rows": inputs["registry_rows"],
        "offbox": offbox,
        "severity": severity,
        "anomalies": anomalies,
    }


def safe_health_signals(state_dir, now=None):
    """Fail-closed wrapper around `health_signals()`, mirroring
    `safe_health_state()`'s broad `except Exception` and "`None` means
    ok" convention: `None` on any unanticipated exception, never a raise.
    """
    try:
        return health_signals(state_dir, now)
    except Exception:
        return None


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
    the two disagree; `page_context()` now calls this once per request
    and threads the result through `ctx["health_state"]`.

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
    noun = i18n.t(_SEVERITY_BANNER_NOUNS.get(severity, "issue"))
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


def _pipeline_never_ran(pipeline_ts, last_detection):
    """True when the flight pipeline has produced no evidence at all: no
    `META_LAST_PIPELINE_RUN` timestamp and no `META_LAST_DETECTION` ever
    recorded, as distinct from a pipeline that has run before and gone
    stale. Scoped to the pipeline signal alone: the device's own "never
    checked in" case is a different, real warning and is left untouched.
    """
    return not pipeline_ts and not last_detection


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


def _latest_numeric_battery_reading(trend_rows):
    """The chronologically-latest reading's `(millivolts, timestamp)`
    pair: scans `trend_rows` (newest-first) for the first row with a
    genuine int `battery_mv`, the same numeric-only filter
    `battery_sparkline_svg()` applies. Returns `None` when no row
    qualifies.
    """
    for row in trend_rows:
        value = row.get("battery_mv")
        if isinstance(value, int) and not isinstance(value, bool):
            return value, row.get("ts")
    return None


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
    caption_text = caption if caption is not None else (i18n.t("Latest %d readings") % BATTERY_TREND_LIMIT)
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
            i18n.t("No battery readings yet."),
            i18n.t(
                "No battery telemetry recorded yet — check back after the "
                "device's next poll.")), "ok"
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
        [i18n.t("Timestamp"), i18n.t("Battery (mV)")], table_rows,
        mono_columns=(1,), raw_columns=(0,), modifier="readings")
    # Collapsed behind a closed-by-default native <details> disclosure —
    # no custom JS toggler needed.
    disclosure_html = (
        '<details class="readings-disclosure"><summary>%s</summary>%s</details>'
        % (
            escape_html(i18n.t("View %d reading%s") % (
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
        "<dl>%s</dl></details>" % (escape_html(i18n.t("More details")), dl_items)
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
            i18n.t("Nothing to compare yet."),
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
# poll_loop.load_poll_state() (filesystem/JSON failure mode), and the
# stats read goes through _safe_query() (SQLite failure mode) — render()
# calls both independently so one failing source degrades only its own
# card.


def unresolved_rows(state_dir):
    """The unresolved-prefix registry as a sorted list of
    `(prefix, count, first_seen, last_seen, example_callsign)` tuples,
    read through `server.poll_loop.load_poll_state()`'s
    `unresolved_prefixes` key. Sorted by count descending, then prefix
    ascending, for a deterministic render order. A malformed entry
    (not a dict, or a non-int `count`) is skipped rather than raising:
    the registry is hand-editable, so a bad edit must degrade gracefully.
    """
    state = poll_loop.load_poll_state(state_dir)
    registry = state.get("unresolved_prefixes")
    if not isinstance(registry, dict):
        return []

    rows = []
    for prefix, entry in registry.items():
        if not isinstance(entry, dict):
            continue
        count = entry.get("count")
        if not isinstance(count, int) or isinstance(count, bool):
            continue
        rows.append((
            prefix,
            count,
            entry.get("first_seen") or "",
            entry.get("last_seen") or "",
            entry.get("example_callsign") or "",
        ))
    rows.sort(key=lambda row: (-row[1], row[0]))
    return rows


def coverage_status(rows):
    """`"ok"` when the registry is empty (no coverage gaps), `"warn"`
    when it has any entries.
    """
    return "ok" if not rows else "warn"


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
    count_text = i18n.t("%d of %d shown") % (total, total)
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
        escape_html(i18n.t("Clear")),
        escape_html(i18n.t(_FILTER_EMPTY_HEADING)),
        escape_html(empty_body),
    )


# Single-sourced so the table builder and the mobile card builder can't
# disagree on a header word. Indices 1-4 are read directly by
# _registry_cards_html() for its field labels; index 0 ("Prefix") has no
# card-side label because the prefix is the card's primary line. "Resolve"
# is always appended, never inserted, since those index lookups are
# positional.
_REGISTRY_HEADERS = ("Prefix", "Count", "First seen", "Last seen", "Example callsign", "Resolve")

# The per-row deep link to the Airlines resolve surface. Both
# representations (_registry_row_html()'s <td> and
# _registry_cards_html()'s .data-card__action block) build their anchor
# from these same constants, so href/aria-label/text can't drift apart.
RESOLVE_LINK_HREF_TEMPLATE = "/airlines?resolve=%s"
RESOLVE_LINK_ARIA_TEMPLATE = "Resolve prefix %s"
RESOLVE_LINK_TEXT = "Resolve"
RESOLVE_CARD_LINK_TEXT = "Resolve this prefix"


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
            escape_html(layout.relative_age_text(age)))
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
            escape_html(i18n.t("More details")),
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
        escape_html(i18n.t("More details")),
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
        escape_html(i18n.t("%.1f%% resolved") % stats["resolved_pct"]),
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
            escape_html(i18n.t("More details")),
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


def _read_health_inputs(state_dir, now):
    """The reads `render()` and `compute_health_state()` both need,
    single-sourced into one dict so the nav-tab dot and the page's own
    anomaly banner can't disagree. `registry_rows` uses its own narrow
    `(OSError, ValueError)` guard, a different failure mode from the
    SQLite reads below (`_safe_query()`), so a registry failure degrades
    only severity, not the other sections.
    """
    cutoff = _cutoff_iso(now, _CORROBORATION_WINDOW_DAYS)
    try:
        registry_rows = unresolved_rows(state_dir)
    except (OSError, ValueError):
        registry_rows = []
    return {
        "device_health": _safe_query(state_dir, history_db.latest_device_health),
        "pipeline_ts": _safe_query(
            state_dir,
            lambda conn: history_db.get_meta(conn, history_db.META_LAST_PIPELINE_RUN)),
        "last_detection": _safe_query(
            state_dir,
            lambda conn: history_db.get_meta(conn, history_db.META_LAST_DETECTION)),
        "source_fault_raw": _safe_query(
            state_dir,
            lambda conn: history_db.get_meta(conn, history_db.META_SOURCE_FAULT)),
        "trend_rows": _safe_query(state_dir, battery_trend_rows),
        "daily_rows": _safe_query(state_dir, lambda conn: battery_daily_rows(conn, now)),
        "corroboration_counts": _safe_query(
            state_dir,
            lambda conn: history_db.corroboration_counts(conn, since=cutoff)),
        "device_config": device_config.load_device_config(state_dir),
        "registry_rows": registry_rows,
    }


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
        i18n.t("Off-box backup up to date") if state == "ok"
        else i18n.t("Off-box backup overdue"))
    # concise_timestamp_html() returns pre-escaped markup; wrapping it in
    # escape_html() again would double-encode it and print raw tags.
    last_backup_html = (
        '<p>%s %s</p>'
        % (
            escape_html(_label_colon(i18n.t("Last off-box backup"))),
            layout.concise_timestamp_html(
                offbox["snapshot_ts"], now, fallback=i18n.t("never")),
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
        escape_html(i18n.t("Off-box backup")),
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
    state_dir = ctx["state_dir"]
    now = ctx.get("now") or history_db.utc_now_iso()

    # Reuse the state page_context() already computed, rather than
    # re-deriving it. Falls back to a fresh compute for a direct caller.
    state = ctx.get("health_state") or compute_health_state(state_dir, now)
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
            i18n.t("Health"), purpose=i18n.t(PAGE_PURPOSE_TEXT), freshness_html=freshness_html)
        + _source_fault_block(source_fault_raw)
        + banner_html
        + screen_section_html
        + server_data_section_html
    )
