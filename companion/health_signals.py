"""companion/health_signals.py: the markup-free half of Health's severity
computation — every state the nav-tab dot and the full Health page banner
need, with zero HTML built.

Never imports a page module (companion/pages/health_page.py imports this
module, never the reverse — the direction is one-way, so this module can
never end up needing a markup builder to compute a verdict). Every value
returned is plain data: strings, dicts, lists, never a '<' character.
`health_page.py` re-exports every name here under its historical name, so
nothing outside this file needs to know the split happened.
"""
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone

import companion.battery_chart as battery_chart
import companion.frame_state as frame_state
import companion.i18n as i18n
import companion.layout as layout
import companion.wake as wake
from server import device_config
from server import history_db
import server.poll_loop as poll_loop

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

BATTERY_TREND_LIMIT = 20  # A display choice, not retention: bounds the
# raw-readings table, the anomaly scan and the fallback chart; the
# chart's primary series plots daily averages instead.

# The chart's primary window. Lives in companion/battery_chart.py, since
# the chart's own aria-label interpolates it directly; re-exported here
# for battery_daily_rows()'s own query window.
BATTERY_TREND_WINDOW_DAYS = battery_chart.BATTERY_TREND_WINDOW_DAYS

# 100 mV: a genuine discharge measured ~50 mV/day through the middle and
# a couple mV per reading even across the steepest final cliff
# (hardware/BATTERY-RUN.md), so crossing 100 mV between two consecutive
# readings means an anomaly, not real discharge.
BATTERY_DROP_WARN_MV = 100

_CORROBORATION_WINDOW_DAYS = 7  # A recent window; runway_events rows are
# written only on a real transition, so even a week's worth stays small.

# Maps frame_state's own three states to the Device tile's device_state
# vocabulary: due -> "ok", held -> neutral "off" (never "warn"/"error",
# so it can never light the nav dot), late -> "warn". STATE_UNKNOWN is
# absent: _device_state() falls back to the age-based staleness_status()
# path for that state instead.
_FRAME_STATE_TO_DEVICE_STATE = {
    frame_state.STATE_DUE: "ok",
    frame_state.STATE_HELD: "off",
    frame_state.STATE_LATE: "warn",
}

_DB_UNAVAILABLE = object()  # sentinel distinguishing "query raised" from
# "query succeeded and legitimately returned None/empty" (e.g. no rows
# recorded yet), which must render very differently. The one instance:
# companion/pages/health_page.py imports this exact object, never a
# second sentinel, so an `is _DB_UNAVAILABLE` check works across both
# modules.


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
    `_battery_trend_caption()` (companion/pages/health_page.py) can never
    disagree about which series is on screen. `daily_rows` may be the
    `_DB_UNAVAILABLE` sentinel: a failed read is never "usable".
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
    `_battery_section()` (companion/pages/health_page.py) uses, so the
    two can never disagree. Three cases: the daily series plotted, no
    readings at all (same 3-month framing), or a fallback of fewer than
    two days of raw readings ("Latest %d readings", the real count,
    never a fixed limit).
    """
    if _battery_daily_series_usable(daily_rows):
        return i18n.t("Last 3 months, daily average")
    if not trend_rows or trend_rows is _DB_UNAVAILABLE:
        return i18n.t("Last 3 months, daily average")
    return i18n.t("Latest %d readings") % _real_trend_reading_count(trend_rows)


def _latest_numeric_battery_reading(trend_rows):
    """The chronologically-latest reading's `(millivolts, timestamp)`
    pair: scans `trend_rows` (newest-first) for the first row with a
    genuine int `battery_mv`, the same numeric-only filter
    `battery_sparkline_svg()` (companion/battery_chart.py) applies.
    Returns `None` when no row qualifies.
    """
    for row in trend_rows:
        value = row.get("battery_mv")
        if isinstance(value, int) and not isinstance(value, bool):
            return value, row.get("ts")
    return None


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
    `collect_anomalies()` and `_offbox_section_html()`
    (companion/pages/health_page.py) so the two can never read different
    words for the same state.
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
    and `_device_section()` (companion/pages/health_page.py) key off, so
    a due/held/late/unknown verdict can never differ between the
    state-only path and the tile markup.
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


def _pipeline_never_ran(pipeline_ts, last_detection):
    """True when the flight pipeline has produced no evidence at all: no
    `META_LAST_PIPELINE_RUN` timestamp and no `META_LAST_DETECTION` ever
    recorded, as distinct from a pipeline that has run before and gone
    stale. Scoped to the pipeline signal alone: the device's own "never
    checked in" case is a different, real warning and is left untouched.
    """
    return not pipeline_ts and not last_detection


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


def _read_health_inputs(state_dir, now):
    """The reads `render()` and `compute_health_state()`
    (companion/pages/health_page.py) both need, single-sourced into one
    dict so the nav-tab dot and the page's own anomaly banner can't
    disagree. `registry_rows` uses its own narrow `(OSError, ValueError)`
    guard, a different failure mode from the SQLite reads below
    (`_safe_query()`), so a registry failure degrades only severity, not
    the other sections.
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


def health_signals(state_dir, now=None):
    """Every state the nav-tab dot and the full Health page banner need
    — severity, the anomaly list, and each section's own state — derived
    from one `_read_health_inputs()` read, with zero markup built. This
    is the snapshot `health_state_from_signals()`
    (companion/pages/health_page.py) renders from and
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
