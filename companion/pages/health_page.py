"""companion/pages/health_page.py — CFG-03 (health status + trend) and
CFG-05's landing context (the on-device fault icon's redirect target),
06-CONTEXT.md.

Completed by plan 06-08. Imports `server.history_db`, `server.poll_loop`
(for `load_poll_state`) and `companion.layout` only; every dynamic value
reaches HTML through `companion.layout.escape_html()` or one of its
escaping component builders, matching the single-escaping-choke-point
discipline `companion/pages/__init__.py` documents.

06.6.4.1-04 (D-10/D-11/D-12): this page's body is now two id-anchored
sections, "Screen" and "Server & data" — the latter absorbing CFG-04's
unresolved-callsign-prefix registry and CFG-08's resolution-statistics
breakdown, migrated in verbatim from `companion/pages/airlines_page.py`
(that page keeps its own copy for exactly one wave; a later plan removes
it there). The migrated registry read (`poll_loop.load_poll_state()`, a
filesystem/JSON failure mode) and the migrated stats read
(`_safe_query()`, a SQLite failure mode) are deliberately kept as their
own independent calls in `render()`, never folded into
`_read_health_inputs()`'s single dict — so one failing source degrades
only its own card, exactly as it did on the page it came from.

Two independent freshness signals (D-12, 06-RESEARCH.md Open Question 2):
"the device last checked in" and "the ADS-B pipeline last ran" are
genuinely different signals with different failure modes and different
data sources (the Caddy access-log tailer vs. `poll_loop.py`'s own meta
writes) — this page never blends them into one verdict. Each still
renders its own independent ok/warn/error state (quick task
260901-tsa): since finding C removed the redundant in-body status dot
from both the Device and Pipeline tiles, that state now reads through
each tile's own `stat-tile--ok/warn/error` border/icon modifier alone,
rather than through a body dot inside the tile as well — the state is
still carried, just no longer carried twice.

D-14 anomaly flagging: `collect_anomalies()` decides whether
`layout.anomaly_banner()` appears at all; its absence *is* the all-clear
(D-21 — this is a plain utility page, not ambient art).

Every database access goes through `_safe_query()`, which returns the
`_DB_UNAVAILABLE` sentinel instead of raising on a locked/missing/corrupt
database — each of the four sections below degrades independently to
06-UI-SPEC.md's "Health data unavailable" copy rather than faulting the
whole page.

06.6.1-03: `anomaly_active()` is this module's one intentionally-public
cross-page export, consumed by `companion/app.py`'s `page_context()`
(threaded into `ctx["health_anomaly_active"]` for the nav-tab
notification dot) — it exists specifically so no nav renderer has to
import a page module, the constraint `companion/pages/__init__.py`
states.
"""
import sqlite3
from datetime import datetime, timedelta, timezone

from companion.layout import escape_html
import companion.layout as layout
from server import history_db
import server.poll_loop as poll_loop  # 06.6.4.1-04 (D-11): the migrated
# unresolved_rows() below now genuinely reads through this module's own
# load_poll_state() — the "exposed but not currently needed" note this
# import used to carry no longer applies.

HEALTH_UNAVAILABLE_TEXT = (
    "Health history is temporarily unavailable — check the companion "
    "service logs.")

# --- Freshness thresholds (D-12) -------------------------------------------
#
# ADS-B pipeline: server/poll_loop.py's POLL_INTERVAL_S is a fixed 30
# seconds (matching Phase 1's validated sampler interval), driven by a
# systemd .timer unit, not a tunable per-deployment value — so these two
# thresholds can be set tight relative to that known cadence. A gap of a
# few minutes already means the timer likely isn't firing.
STALE_PIPELINE_WARN_S = 180  # 3 minutes — 6x the 30s cadence; one missed
# cycle is ordinary jitter, six in a row is not.
STALE_PIPELINE_ERROR_S = 900  # 15 minutes — 30x the cadence; well past
# "the systemd timer is having a rough moment."

# Device check-in: unlike the pipeline, this is genuinely tunable and
# CURRENTLY a bring-up default, not a production value — deploy/
# skypane.env.example's SKYPANE_SLEEP_S is 30 seconds today (verified
# live on the OVH host, STATE.md 2026-08-26), but is explicitly expected
# to lengthen substantially once Phase 5's real battery-life measurement
# lands (05-01 Tasks 2-3, deliberately deferred to the end of the
# project). These two thresholds must therefore be generous enough that
# lengthening SKYPANE_SLEEP_S does not turn this page permanently red —
# anchored instead to flightportrait's own documented backoff ceiling
# (PROJECT.md: "exponential-backoff polling, caps at 6h"), which is the
# worst-case gap a healthy-but-struggling device can produce on its own
# before this page should call it an outage.
STALE_DEVICE_WARN_S = 3600  # 1 hour
STALE_DEVICE_ERROR_S = 21600  # 6 hours — matches the documented backoff cap.

# --- Battery trend (D-12/D-13) ----------------------------------------------

BATTERY_TREND_LIMIT = 20  # D-13 keeps history forever; this page shows only
# the most recent readings for readability — a display choice, not a
# retention policy (server/history_db.py's own module docstring makes the
# same distinction for runway_events).
#
# 260902-l0b: this constant no longer bounds the chart at all — the chart's
# primary mode plots BATTERY_TREND_WINDOW_DAYS's 90-day daily-average
# series instead. BATTERY_TREND_LIMIT now bounds three other things: the
# raw-readings disclosure table (battery_trend_rows()), the abnormal-drop
# anomaly scan (battery_status(), fed the same raw rows), and the
# fallback chart a device with fewer than two calendar days of history
# still gets (see _battery_daily_series_usable()).

BATTERY_TREND_WINDOW_DAYS = 90  # 260902-l0b: the chart's primary window,
# locked at 3 months by the developer's own explicit request (7-day and
# 30-day alternatives were raised and rejected in discussion — see this
# quick task's CONTEXT.md). D-13's keep-forever retention makes this a
# display window, exactly the distinction BATTERY_TREND_LIMIT's own
# comment already draws for the raw-readings limit above — it bounds a
# `ts >= ?` read (battery_daily_rows()), deleting nothing.

# Provisional (T-06-08-05): hardware/BATTERY-RUN.md pre-registers a
# --min-mv-drop default of 100mV, but that threshold is judged over the
# *whole multi-day run's* opening-vs-closing window mean (the "phantom
# USB power" gate), not between two consecutive device_health readings —
# a materially different granularity. Phase 5's Tasks 2/3 (the actual
# multi-day discharge run and its measured curve) have not run yet, so
# there is no measured per-reading discharge figure to anchor this on.
# 100mV is reused here only as the closest recorded, pre-registered
# figure this project has — NOT presented as a measured per-cycle value.
# Revisit once hardware/BATTERY-RUN.md's "Discharge Trend" section is
# filled in.
BATTERY_DROP_WARN_MV = 100

# --- Corroboration (D-15) ---------------------------------------------------

_CORROBORATION_WINDOW_DAYS = 7  # "a recent window" per this plan's own
# Task 1 action text — runway_events rows are written only on a real
# transition (Pitfall 1), so even a week's worth stays small.

_CORROBORATION_ROWS = (
    # (history_db's stored corroborated string, display label, status,
    # explanation sourced from detect.poll_current_aircraft()'s own
    # documented three-outcome semantics — this page performs no new
    # inference, D-15).
    ("True", "Agreement", "ok",
     "Both ADS-B sources independently selected the same aircraft."),
    ("None", "Single-source (uncorroborated)", "ok",
     "Only one source returned a result this cycle — not the same as a "
     "disagreement; no corroboration was available to check against."),
    ("False", "Disagreement", "warn",
     "The two sources named different aircraft, so nothing was selected "
     "that cycle — the panel image was kept from the previous cycle."),
)

# --- CFG-05 landing context --------------------------------------------------
#
# Kept as a literal, human-maintained list rather than importing
# server.plane.detect (this page is presentation-only, per its own
# documented import contract, and must not reach into the detection/
# network layer) — keep in sync with detect.DEFAULT_PROVIDER_ORDER by
# hand if that list ever changes. By construction (06-10's
# _classify_source_fault()), META_SOURCE_FAULT is only ever true when
# every one of these was queried and failed.
_ADSB_PROVIDER_NAMES = ("adsb.fi", "adsb.lol")

SOURCE_FAULT_HEADING = "ADS-B source outage"
SOURCE_FAULT_BODY = (
    "The frame's alert badge is showing because every configured ADS-B "
    "source (%s) failed to respond on the most recent pipeline run — "
    "this is a data-source outage, not a device problem."
    % ", ".join(_ADSB_PROVIDER_NAMES)
)

# --- D-14 anomaly banner -----------------------------------------------------

# 06.6.1-UI-SPEC.md's Copywriting Contract, verbatim except for the
# leading "⚠ " glyph. Revised from 06's "...see the flagged item(s)
# below." — 06.6.1-03 removed the bulleted detail-list markup this text
# used to point at, so the two edits (copy + list removal) are
# deliberately coupled: change one, change the other.
#
# 06.6.2-06 (UXA-14): the leading "⚠ " glyph moved out of this constant
# and into the severity-naming banner builder (06.6.4.1-04:
# _anomaly_banner_html(), superseding the since-retired
# _anomaly_banner_text()), so the rendered banner can name its real
# severity while this constant remains a literal substring of whatever
# renders — every existing `ANOMALY_BANNER_TEXT in rendered` /
# `.count(...)` check in test_status_pages.py keeps passing unmodified.
ANOMALY_BANNER_TEXT = "Something needs attention — check the tiles below."

# 06.6.2-06 (UXA-14) / 06.6.3-04 (UXA-06/D-18): the noun each severity's
# count-aware banner lead-in pluralizes ("1 warning: " / "2 warnings: ").
# Any severity not in this dict (there is none today — overall_severity()
# only ever returns "ok"/"warn"/"error", and "ok" never reaches this
# function) falls back to the generic "issue" noun.
_SEVERITY_BANNER_NOUNS = {"warn": "warning", "error": "error"}

DEVICE_FRESHNESS_LABEL = "Device last checked in"
PIPELINE_FRESHNESS_LABEL = "ADS-B pipeline last ran"

# --- quick task 260902-gjj (ISSUE 2): D-01 reversal, recorded at the
# removal site --------------------------------------------------------------
#
# RETIRED — BATTERY_STATUS_LABEL ("Battery readings", deliberately not
# "Battery trend" so harness substring assertions stayed unambiguous
# between the two, per D-01's own comment) and _battery_badge_block(),
# both gone outright, not just hidden.
#
# 06.5-CONTEXT.md's D-01 asked for "a persistent status badge next to the
# Battery Trend section heading, reusing the exact status_dot() pattern
# the Device and Pipeline sections already render." Reading status_dot()
# itself found its accessibility contract thinner than that ask implied:
# it emits an EMPTY first span (no text node, no role, no aria-label, no
# title — the state lives only in a CSS class mapped to a background
# colour) plus a label naming only the SUBJECT being measured ("Battery
# readings"), never the state itself. A screen-reader user got the word
# "Battery readings" and nothing else; removing the badge loses no
# programmatically-available state.
#
# The battery-trend section's own top edge carries the same
# battery_status() verdict instead — D-01's own reference note already
# expected "06.3's 3px top-border-by-status treatment" to apply to this
# content, before 06.6.1-03 moved it out of .stat-tile and the
# border-by-status treatment never followed. See
# _battery_trend_section_html()'s docstring and companion/static/
# style.css's .battery-trend-section comment for the fuller record.

# 260902-chc: the hidden-by-default auto-refresh pill's visible copy
# (Option B of the validated Health Auto-Refresh Sketch). The sketch's
# own label is bilingual; this app renders every page `<html lang="en">`
# and a grep of companion/ finds not one word of French anywhere, so the
# English half is the one that matches the shipped product — a
# considered choice, not a dropped requirement. A single-character
# ellipsis ("…"), matching this file's own sibling precedent for a
# short in-flight verb (companion/pages/config_page.py's
# POLL_SUBMIT_PENDING_TEXT = "Polling…"), not three periods.
REFRESH_PILL_TEXT = "Updating…"

# D-02: per-point interactive hit-target contract. BATTERY_READOUT_ID and
# SPARKLINE_HIT_CLASS are looked up by companion/static/battery-trend.js
# and styled by companion/static/style.css — the value is duplicated
# rather than imported from those files because there is nothing in this
# Python module to import from (they are static assets, not Python).
# companion/test_status_pages.py's cross-file contract check asserts
# both literals actually appear in battery-trend.js's shipped source.
BATTERY_READOUT_ID = "battery-readout"
SPARKLINE_HIT_CLASS = "sparkline-hit"
SPARKLINE_DOT_CLASS = "sparkline-dot"
# quick task 260902-ep7 (BUG 4): two more cross-file class literals,
# following the same established pattern as the two above. SPARKLINE_LINE_CLASS
# is the harness's stable marker for "a trend segment rendered", replacing
# the retired single-<polyline> marker (a percentage-coordinate <polyline>
# can't exist — percentages aren't permitted in a `points` list — so the
# line is now n-1 <line> segments, one per consecutive pair of points).
# SPARKLINE_AXIS_CLASS marks the drawn axis/tick <rect> elements this task
# adds. Neither is read by companion/static/battery-trend.js — that file
# queries SPARKLINE_HIT_CLASS only — so this pair is a test/style
# convenience, not a JS cross-file contract like the two above.
SPARKLINE_LINE_CLASS = "sparkline-line"
SPARKLINE_AXIS_CLASS = "sparkline-axis"
# Must equal companion/app.py's SCRIPT_ROUTE — duplicated, not imported,
# because companion/pages/__init__.py's contract forbids a page module
# importing companion.app (app.py imports pages, so importing back would
# be circular). The test harness asserts the two stay equal.
BATTERY_TREND_SCRIPT_SRC = "/static/battery-trend.js"

# 06.6.1-03 (D-02): the battery-trend chart moved out of the Overview
# dashboard-grid into its own full-width section, so its heading text is
# now a named constant (was a literal passed straight to stat_tile())
# rather than a tile caption — this is what lets a future plan attach an
# icon to a known heading without re-typing the literal.
BATTERY_SECTION_HEADING = "Battery trend"
# Contract value shared with companion/static/style.css's
# .battery-trend-section rule (plan 06.6.1-01, same wave); guarded
# against silent drift by a cross-file check in test_status_pages.py.
BATTERY_SECTION_CLASS = "battery-trend-section"

# 06.6.1-04 (D-02): one icon id per Health tile signal, each a member of
# layout.ICON_IDS — the whitelist itself is what keeps a typo here from
# ever becoming a raw-markup injection: icon_html() renders nothing at
# all for an id it doesn't recognise, which is safe but invisible, so
# this module's own test harness separately asserts every one of these
# three constants is a genuine ICON_IDS member (a typo therefore fails a
# check loudly instead of silently rendering no icon).
#
# SUPERSEDED (quick task 260902-j8w): a fourth constant, ICON_BATTERY =
# "icon-battery", used to live here. It was the only one of the four
# passed to layout.icon_html() directly rather than to stat_tile()'s
# `icon=` keyword — it rendered inside the Battery-trend section's own
# `<h2>`, not inside a tile caption. Removed at the developer's direct
# instruction ("supprime le logo de la batterie, car c'est inconsistant
# avec le reste") because it was the only glyph on any of Health's five
# headings; the id itself stays a `layout.ICON_IDS` / sprite member (see
# that whitelist's own comment for why pruning it is a deliberate
# non-goal), so only this module's use of it — and this comment's own
# "four" — changed.
ICON_DEVICE = "icon-device"
ICON_PIPELINE = "icon-pipeline"
ICON_CORROBORATION = "icon-corroboration"

# --- 06.6.4.1-04 (D-10): the two id-anchored sections Health's body is
# now split into. SERVER_DATA_SECTION_ID is a cross-page coupling:
# companion/pages/history_page.py links to this exact anchor (#server-data)
# for D-21 — renaming it silently breaks that link. This is the one
# cross-page coupling this phase introduces.
SCREEN_SECTION_ID = "screen"
SCREEN_SECTION_HEADING = "Screen"
SERVER_DATA_SECTION_ID = "server-data"
SERVER_DATA_SECTION_HEADING = "Server & data"
RESOLUTION_RATE_LABEL = "Resolution rate"
UNRESOLVED_SECTION_HEADING = "Unresolved prefixes"
STATS_SECTION_HEADING = "Resolution statistics"

# --- quick task 260901-tsa: page-purpose + section-intro copy ----------
#
# Verbatim from the validated "Merged Health Sketch" — this is the
# sketch's own wording, restating the split D-10 already made (the
# physical frame versus the ADS-B/route-resolution pipeline) in the
# reader's own terms rather than making any new claim. Keep the leading
# em-dash and the space after it on both descriptions: that is what
# makes the heading and its description read as one continuous phrase
# across the baseline-aligned `.section-intro` row (see
# `_section_intro_html()` below), and it is the validated copy — do not
# drop it as "redundant punctuation".
PAGE_PURPOSE_TEXT = "Screen status and server data quality, in one place."
SCREEN_SECTION_DESCRIPTION = (
    "— the physical frame: is it checking in, and how's the battery.")
SERVER_DATA_SECTION_DESCRIPTION = (
    "— the ADS-B pipeline and route resolution: is the data fresh and "
    "trustworthy.")

# --- 06.6.4.1-04 (D-11/D-12): CFG-04's unresolved-prefix registry and
# CFG-08's resolution-statistics breakdown, migrated verbatim from
# companion/pages/airlines_page.py — that page keeps its own copy for
# exactly one wave (plan 06 removes it there next), so for one wave both
# pages render this content. Every constant/function body below is
# copied unchanged in logic; only the module they live in changes.

_NO_GAPS_HEADING = "No coverage gaps."
_NO_GAPS_BODY = (
    "No unresolved callsign prefixes — airline coverage looks complete.")

_READ_ONLY_NOTE = (
    "This list is read-only by design — resolving a prefix is a manual "
    "step done elsewhere, following the existing coverage-gap runbook.")

_NO_STATS_HEADING = "No resolution data yet."
_NO_STATS_BODY = (
    "No flight events recorded yet — resolution statistics appear once "
    "the ADS-B pipeline has detected a flight.")

RESOLUTION_WINDOW_DAYS = 30  # A month is long enough to smooth over a
# quiet week at this single-airport traffic volume, while still reading
# as "recent" for a resolution-rate figure.

# The four categories server/plane/enrich.py's resolve_route() documents,
# in a fixed display order, with a plain-English gloss for each so this
# page is readable without the source code (D-05/quick-task 260827-hyy).
_SOURCE_ROWS = (
    ("fresh_hit", "Fresh lookup",
     "A live adsbdb lookup resolved a full route this cycle."),
    ("cache_hit", "Cached hit",
     "A previously-cached route was reused, sparing a network request."),
    ("airline_only", "Airline only",
     "adsbdb had no route, but the callsign's ICAO prefix identified the "
     "airline from the static prefix table."),
    ("miss", "Miss",
     "Neither adsbdb nor the static prefix table resolved anything for "
     "this callsign — this is exactly what CFG-04's registry above "
     "tracks."),
)

# D-20: the filter bar's copy (06.6.3-UI-SPEC.md's Copywriting Contract),
# driven client-side by companion/static/list-filter.js's shared
# [data-filter-input]/[data-filter-count]/[data-filter-clear]/
# [data-filter-empty] attribute contract. Kept byte-identical to
# airlines_page.py's own constants, including the "airlines-" id prefix —
# D-12 says the registry card's content and behaviour are unchanged by
# this move, and list-filter.js keys on the data-filter-* attributes, not
# on the element's id string.
_FILTER_INPUT_ID = "airlines-filter-input"
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
    stores everything as TEXT, and this project's own precedent
    (`record_runway_event()`'s `corroborated` column) is `str(bool_value)`
    — so `"True"` is the expected on-value. `"1"` is accepted as a
    defensive fallback for any other writer convention. Anything else
    (`None`, `"False"`, `"0"`, `""`) is false. Never raises.
    """
    return value in ("True", "1")


def staleness_status(age_seconds, warn_s, error_s):
    """One of `"ok"` / `"warn"` / `"error"`, per D-12's staleness rule: a
    signal older than `error_s` is an error, older than `warn_s` (but
    under `error_s`) is a warning, everything else — including "never
    seen" (`age_seconds is None`, mapped to `"warn"`, not `"error"`, since
    a freshly-provisioned deployment has no history yet) — is healthy or
    a soft warning. A negative age (clock skew) is treated as zero,
    since "the reading appears to be from the future" is not staleness.
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


def battery_trend_rows(conn):
    """The most recent `BATTERY_TREND_LIMIT` `device_health` rows, newest
    first (matches `history_db.recent_device_health()`'s own ordering).

    D-13 keeps this table's history forever — this function's LIMIT is a
    *display* choice for readability, not a retention policy; nothing is
    ever deleted here or anywhere else in this page.
    """
    return history_db.recent_device_health(conn, limit=BATTERY_TREND_LIMIT)


def battery_daily_rows(conn, now):
    """(260902-l0b) The chart's primary series: one point per UTC calendar
    day over the last `BATTERY_TREND_WINDOW_DAYS` (3 months), via
    `history_db.daily_battery_averages()`. Structurally interchangeable
    with `battery_trend_rows()`'s own rows for plotting purposes — see
    `daily_battery_averages()`'s own docstring for why its `ts` key names
    a day rather than a moment.

    `_cutoff_iso()` returns `None` when `now` fails to parse, and
    `daily_battery_averages(conn, since=None)` degrades to an UNBOUNDED
    read in that case rather than an empty one — a deliberate choice: on
    the one input this function does not control, it shows MORE history
    rather than none, and never an empty card.
    """
    return history_db.daily_battery_averages(
        conn, since=_cutoff_iso(now, BATTERY_TREND_WINDOW_DAYS))


def _battery_daily_series_usable(daily_rows):
    """(260902-l0b) True when there are at least two UTC-day buckets to
    plot as a trend — `battery_sparkline_svg()`'s own two-point minimum
    for a line, kept in exactly one place (not duplicated in
    `_battery_section()` and `_battery_trend_caption()` separately) so the
    chart's series choice and the heading caption can never disagree
    about which series is actually on screen. `daily_rows` may be the
    `_DB_UNAVAILABLE` sentinel (a failed read is never "usable").
    """
    return isinstance(daily_rows, list) and len(daily_rows) >= 2


def _battery_trend_caption(trend_rows, daily_rows):
    """(260902-l0b) The heading caption text (without its leading em
    dash), honest about which series is actually on screen — computed
    from the same `_battery_daily_series_usable()` predicate
    `_battery_section()` uses to choose what to plot, so the two can
    never disagree.

    Three cases, not two: the 90-day daily series is plotted (>= 2 day
    buckets) — the 3-month/daily-average framing; no readings exist at
    all (or the read failed) — the SAME 3-month framing, because that is
    what this page will show once data exists and there is no chart of
    any kind on screen to be honest ABOUT; otherwise a real fallback
    chart is on screen, built from fewer than two calendar days of raw
    readings — today's byte-identical "Latest %d readings" string, which
    is what this page always showed before this task and remains exactly
    true of what is actually plotted.
    """
    if _battery_daily_series_usable(daily_rows):
        return "Last 3 months, daily average"
    if not trend_rows or trend_rows is _DB_UNAVAILABLE:
        return "Last 3 months, daily average"
    return "Latest %d readings" % BATTERY_TREND_LIMIT


# quick task 260902-ep7 (BUG 4): _AXIS_LEFT_GUTTER and _AXIS_BOTTOM_STRIP
# (a hand-estimated left gutter and bottom strip reserved around the plot
# area for the axis labels — grown once already, from 34 to 44 user
# units, by quick task 260902-dng, when its own under-measurement became
# visible for the first time at true 1:1 scale) are DELETED outright, not
# just resized again. Reserving gutter space in Python was always an
# ESTIMATE of how wide a browser would actually render a given label —
# this whole class of error (estimate now, hope a browser agrees later)
# goes with them. The replacement is structural: `battery_sparkline_svg()`
# now returns a CSS-grid wrapper (`.sparkline`, style.css) whose first
# column is sized `auto` — the browser measures the REAL rendered width
# of the widest Y-axis label and reserves exactly that, every time, for
# every label string, at every font a user's system substitutes. The
# bottom strip's job is done the same way, as a second grid row sized by
# its own row's content height. Axis labels are `<span>` elements in that
# grid now, not SVG `<text>` nodes — see below.
#
# The chart's plot geometry itself no longer needs a "gutter" concept at
# all: with no viewBox, 1 SVG user unit == 1 CSS pixel, and cx is a
# PERCENTAGE of the canvas's own rendered width — the canvas IS the plot
# area, edge to edge, with nothing reserved inside it. This is also what
# makes "the chart fills its card" a structural property of the layout
# rather than a tuned number: there is no scale factor anywhere in this
# pipeline for a future edit to silently break.
#
# The chart canvas's own fixed height, in CSS pixels — declared exactly
# ONCE, here and in style.css's `.battery-trend-section svg:not(.icon)`
# rule (a harness check pins that the CSS declares it nowhere else,
# especially not inside a `@media` block: since every point coordinate
# is now a percentage of this height, a responsive height would silently
# move every point). Chosen against three criteria, all satisfied by
# 160px: at least the validated sketch's own 150px (the only height this
# chart has ever been reviewed at), no more than ~180px so the card does
# not dominate the page, and tall enough that a small millivolt spread
# still reads as a trend rather than a flat line.
_SPARKLINE_CANVAS_HEIGHT_PX = 160

# The vertical inset — the margin, top and bottom, inside the canvas the
# plotted line never crosses, as a PERCENT of the canvas height. Derived,
# not chosen by taste: it must be at least the 3-unit cosmetic-marker
# radius so no visible dot is ever clipped, and it is set here to equal
# half the axis label's own line box (as a fraction of the canvas
# height) so that `justify-content: space-between` (style.css's
# `.sparkline__y`) places each Y label's optical centre exactly on the
# level it names. A 10px label at `line-height: 1.2` is a 12px line box;
# half of that is 6px; 6 / 160 * 100 = 3.75. Re-derive this figure if
# either the label's font-size/line-height or
# _SPARKLINE_CANVAS_HEIGHT_PX above ever changes.
_SPARKLINE_VERTICAL_INSET_PERCENT = 3.75

# 260902-l0b: the cosmetic marker's and the normal hit target's radii,
# named (they were literals — `r="3"`/`r="8"` — inside the point loop
# before this task) so the density rule below can reference them instead
# of restating the numbers.
_SPARKLINE_DOT_RADIUS_PX = 3
_SPARKLINE_HIT_RADIUS_PX = 8

# The point count at which the 90-day daily chart's cosmetic dots stop
# reading as separate marks and start reading as a continuous caterpillar
# — a different visual language from the thin line the developer asked
# to keep. Derived, not chosen by taste, against the narrowest real
# canvas this file's own `.battery-trend-section svg:not(.icon)` comment
# already measured and cited (style.css: "375px viewport -> 293px (the
# narrowest real container)") — an upper bound on the canvas itself,
# since the Y-axis label column's real width is browser-measured
# (`.sparkline`'s `auto` first grid column) and cannot be known from CSS
# alone; using the wider figure is the conservative direction here; a
# canvas narrower than 293px in practice would only mean dots merge
# *before* this derived threshold, never after.
#
# `_point_x()` below spreads `point_count` points evenly across the
# canvas's full width, so consecutive points sit `293 / (point_count - 1)`
# CSS pixels apart. They stop reading as separate marks once that gap
# drops below the cosmetic dot's own diameter (2 * _SPARKLINE_DOT_RADIUS_PX
# = 6px): `293 / (point_count - 1) < 6` => `point_count > 293 / 6 + 1`
# => `point_count > 49.83`, so 50 is the first integer point count where
# suppression is warranted. Re-derive this figure if the narrowest real
# container width (293px, from style.css's own derivation) or the
# cosmetic dot radius above ever changes.
_SPARKLINE_DENSE_POINT_THRESHOLD = 50

# The reduced hit-target radius used at/above the density threshold —
# smaller than the normal 8px so heavily overlapping hit circles no
# longer nearly-fully overlap, though every point stays reachable (the
# roving-tabindex/arrow-key keyboard path below is entirely unaffected;
# only the pointer/touch hit area shrinks). The honest trade: this costs
# tap-target size and buys pointing precision among ~50+ closely-spaced
# points — real only on a real device, hence this task's own
# human-verification list.
_SPARKLINE_DENSE_HIT_RADIUS_PX = 4

# 260902-l0b: a fixed, English month-abbreviation table, deliberately NOT
# `datetime.strftime("%b")` — this app's own UI text is English
# throughout regardless of the developer's own French (see this page's
# other timestamp helpers' docstrings), and `%b` is locale-dependent: a
# server process with any other locale active would silently render a
# French/German/etc. abbreviation here. A fixed table has no such
# failure mode.
_MONTH_ABBR = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)


def _axis_clock_label(ts):
    """"HH:MM" clock text for a battery-chart X-axis label, matching
    `layout.concise_timestamp_html()`'s own clock-format convention
    (`parsed.strftime("%H:%M")`). Falls back to the raw `ts` string
    (never raising) when it fails to parse — the same graceful-
    degradation precedent `concise_timestamp_html()`'s own unparseable-
    `ts` branch already sets.
    """
    parsed = layout.parse_iso(ts)
    return parsed.strftime("%H:%M") if parsed is not None else (ts or "")


def _axis_day_label(ts):
    """(260902-l0b) "D Mon" day-of-month-plus-abbreviated-month X-axis
    label for the chart's daily mode — `_axis_clock_label()`'s sibling,
    for a series whose `ts` names a whole UTC calendar day
    (`daily_battery_averages()`'s `"YYYY-MM-DD"` shape) rather than a
    moment. A day string parses fine via `layout.parse_iso()`
    (`datetime.fromisoformat()` accepts a date-only ISO string, at
    midnight), so `_axis_clock_label()` itself would "work" here but
    print a lie — every day's label would read "00:00". This sibling
    exists specifically to avoid that.

    The day is composed from the parsed `datetime`'s own `.day` integer,
    never from `strftime`'s no-pad day-of-month directive (the
    dash-prefixed variant) — that flag is a glibc/BSD extension, not
    portable, and not guaranteed by the C standard Windows's C runtime
    implements. The month uses this module's own `_MONTH_ABBR` table,
    not `strftime`'s locale-dependent month-abbreviation directive — see
    `_MONTH_ABBR`'s own comment for why. Falls back to the raw `ts`
    string (never raising) when it fails to parse — the same
    graceful-degradation precedent `_axis_clock_label()` above sets.
    """
    parsed = layout.parse_iso(ts)
    if parsed is None:
        return ts or ""
    return "%d %s" % (parsed.day, _MONTH_ABBR[parsed.month - 1])


def _battery_reading_parts(mv, ts, now):
    """quick task 260901-uzi (finding 3): the plain-text `(value, when)`
    pair every human-facing rendering of one battery reading now shares —
    the seeded readout, each chart point's `<title>` tooltip and
    `aria-label`, and each point's `data-when` attribute.

    `value` is "{mv} mV". `when` copies `layout.concise_timestamp_html()`'s
    own visible-text shape ("HH:MM UTC (Nx ago)") without its `<span>`
    markup wrapper — a short clock time plus `layout.relative_age_text()`'s
    existing suffix — so this page's battery timestamps read in the same
    humanised format as its Device/Pipeline timestamps, instead of the
    raw ISO string this finding replaces.

    Returns PLAIN, UNESCAPED text — inheriting `layout.absolute_and_relative()`'s
    stated contract: every caller escapes at the point of interpolation.
    Returned as a TUPLE, not markup, because `companion/static/
    battery-trend.js` rewrites the readout's content through `textContent`
    on every hover/tap/keyboard move — anything the server placed there as
    markup would be destroyed on the very first interaction. The two parts
    exist separately so the script can write each into its own span and
    preserve the value/detail split, rather than flattening it back to one
    string.

    Degrades exactly like `concise_timestamp_html()`'s own unparseable-`ts`
    branch: when `ts` is missing, fails to parse, or age cannot be computed
    (a mismatched `now`), `when` falls back to the raw `ts` string (or the
    empty string, when `ts` itself is falsy) rather than raising — never
    crashing this render. This fallback is what keeps the existing
    hostile-timestamp harness check meaningful: an unparseable
    attacker-supplied timestamp still reaches the tooltip, still through
    `escape_html()`, exactly as before this task.
    """
    value = "%d mV" % mv
    parsed = layout.parse_iso(ts)
    age = layout.age_seconds(ts, now)
    if parsed is None or age is None:
        return value, (ts or "")
    clock = parsed.strftime("%H:%M")
    when = "%s UTC (%s)" % (clock, layout.relative_age_text(age))
    return value, when


def _daily_reading_parts(mv, ts, reading_count):
    """(260902-l0b) `_battery_reading_parts()`'s sibling for one point on
    the chart's daily-average series — the same plain, UNESCAPED
    `(value, when)` tuple contract (every caller escapes at the point of
    interpolation), so the existing escape-at-interpolation discipline is
    unchanged and `companion/static/battery-trend.js` keeps working with
    no edit of its own (it reads `data-when` back out through
    `textContent`, agnostic to what format the string carries).

    This is what stops the readout from lying on hover: at rest it shows
    the latest RAW reading (`_battery_reading_parts()`, unchanged), and
    hovering/tapping a chart point in daily mode replaces it with an
    AVERAGE — this label is the only thing on the page that tells the
    developer which of the two they are looking at, so it must say so
    explicitly, in the parenthetical `_battery_reading_parts()` already
    established for a detail clause ("HH:MM UTC (Nx ago)").

    `when` is "`{day label} — daily average ({N} reading(s))`", singular
    /plural handled. When `reading_count` is missing or not a real
    positive int, degrades to "`{day label} — daily average`" — a bare
    parenthetical naming zero or an unknown count of readings would be
    actively misleading, so it is omitted rather than printed empty.
    """
    value = "%d mV" % mv
    day_label = _axis_day_label(ts)
    if isinstance(reading_count, int) and not isinstance(reading_count, bool) and reading_count > 0:
        noun = "reading" if reading_count == 1 else "readings"
        when = "%s — daily average (%d %s)" % (day_label, reading_count, noun)
    else:
        when = "%s — daily average" % day_label
    return value, when


def battery_sparkline_svg(rows, now=None, daily=False):
    """A minimal, dependency-free battery-trend chart built server-side
    from `rows` (newest-first, `battery_trend_rows()`'s own shape). No
    external reference (`url(`, `<image`, or a script tag) of any kind,
    consistent with the zero-new-dependencies constraint (T-06-08-SC) —
    that goal is unchanged. D-02: each plotted point also carries a
    cosmetic marker plus a transparent, enlarged, keyboard-focusable hit
    target with `data-mv`/`data-ts` attributes and a `<title>` tooltip,
    so the exact reading is available on hover/tap with no JavaScript at
    all — also unchanged. D-09/§5.3, extended by quick task 260902-ep7:
    real drawn axis lines and tick marks now exist (not just four
    floating text labels), and the four axis labels themselves are HTML
    `<span>` elements outside the SVG, not SVG `<text>` nodes inside it.

    quick task 260902-ep7 (BUG 4): the return value is now a `<div
    class="sparkline">` wrapper (a CSS grid: an auto-sized label column
    beside the canvas, a labelled row below it — see style.css), not a
    bare `<svg>`. The `<svg>` inside it carries NO `viewBox` and NO
    `preserveAspectRatio` — the docstring's old claim of "a fixed
    viewBox, exactly one `<polyline>`" described a MECHANISM, not a
    goal, and that mechanism is exactly what changed. With no viewBox, 1
    SVG user unit == 1 CSS pixel and percentage geometry resolves
    against the canvas's own real rendered size, so every horizontal
    position emitted below is a percentage in [0, 100] and every size
    (marker radius, hit-target radius, stroke width, tick dimensions) is
    an absolute CSS pixel value at every container width, forever —
    there is no scale factor anywhere in this pipeline to bound. The
    single `<polyline>` is replaced by `n - 1` `<line class="sparkline-
    line">` segments (percentages are not permitted inside a `<polyline>`
    `points` list, so a polyline could not carry this coordinate scheme
    even if kept). Every axis label is still `aria-hidden` because the
    exact reading is already announced by each point's own
    `aria-label`/`<title>`; duplicating it as loose text would make a
    screen reader read the chart's extremes twice. Deliberately does
    **not** emit a script tag or the readout element itself — those are
    `_battery_section()`'s job — so this function's own no-external-
    reference guarantee (asserted directly against its return value by
    `companion/test_status_pages.py`) stays true unweakened.

    Returns `""` (no sparkline at all) when fewer than two rows carry a
    numeric `battery_mv` — a single point cannot show a trend. Rows with
    a missing/non-numeric `battery_mv` are dropped rather than plotted,
    which can compress the effective time axis; this is a presentational
    simplification, not a claim about even reading spacing. Each row's
    timestamp is paired with its `battery_mv` value before filtering, so
    a dropped row also drops its own timestamp — never zipping two
    independently-filtered lists, which would otherwise silently shift
    every later point's timestamp by one. The same filtered `(value, ts)`
    pairs drive both the plotted points and the X-axis oldest/newest
    labels, so a dropped row can never shift a label away from the point
    it describes.

    `now` (quick task 260901-uzi) defaults to `history_db.utc_now_iso()`
    when omitted — the same fallback every other now-dependent function in
    this module uses — so every pre-existing call site (including the
    harness's own direct calls) keeps working unchanged. Threaded through
    to `_battery_reading_parts()` for each point's humanised `(value,
    when)` label, replacing the raw-ISO label this function used to build
    inline.

    260902-l0b: `daily` is a third, defaulted parameter — every existing
    call site and every direct-call harness fixture keeps today's
    behaviour byte-for-byte when it is left `False`. `True` says the rows
    being plotted are daily aggregates (`daily_battery_averages()`'s own
    shape — `ts` names a whole UTC calendar day) rather than individual
    readings, and switches three things together, driven by one flag so
    they can never disagree: the X-axis endpoint labels use
    `_axis_day_label()` instead of `_axis_clock_label()` (a day string
    would otherwise parse fine and silently print "00:00" — see
    `_axis_day_label()`'s own docstring), each point's hover/tap label is
    built by `_daily_reading_parts()` instead of `_battery_reading_parts()`
    (naming the day and that the value is an average, never a raw
    reading), and cosmetic dots are suppressed once `point_count` reaches
    `_SPARKLINE_DENSE_POINT_THRESHOLD` (see that constant's own
    derivation) — the daily series is the only one this file ever plots
    at a point count anywhere near that threshold, but the rule itself is
    keyed on point count alone, not on `daily`, so a future caller with a
    dense non-daily series gets the same protection.
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
    values = [value for value, _ts, _count in pairs]
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1
    point_count = len(pairs)
    inset = _SPARKLINE_VERTICAL_INSET_PERCENT
    # 260902-l0b: the density rule — see _SPARKLINE_DENSE_POINT_THRESHOLD's
    # own derivation for why 50. Keyed on point_count alone (never on
    # `daily`), so the same protection would apply to any future dense
    # non-daily series too.
    dense = point_count >= _SPARKLINE_DENSE_POINT_THRESHOLD
    hit_radius = _SPARKLINE_DENSE_HIT_RADIUS_PX if dense else _SPARKLINE_HIT_RADIUS_PX

    def _point_x(index):
        # Spans the full 0-100% width, edge to edge — "the chart fills
        # its card" is a property of this formula, not a tuned margin.
        return index / (point_count - 1) * 100

    def _point_y(value):
        # `inset` on both top and bottom keeps every marker's 3-unit
        # radius fully inside the canvas (see _SPARKLINE_VERTICAL_INSET_
        # PERCENT's own derivation above); the y-axis is inverted (higher
        # mV -> smaller y%) to match SVG's top-down coordinate direction.
        return inset + (1 - (value - lo) / span) * (100 - 2 * inset)

    # Axis chrome first (paint order — see the note below the point loop
    # for why order matters at all). Filled <rect> elements, not stroked
    # <line> elements, for a real reason: an axis-aligned integer-width
    # filled rect has no stroke-centring or half-pixel-rounding to reason
    # about, and a rect can pair a percentage position with an absolute
    # size in a way no stroked line can (needed below, since every tick
    # mixes a percentage axis coordinate with an absolute pixel length).
    # `--color-border` (style.css) is this file's existing "structural
    # only, never an interactive-state signal" token — precisely what a
    # chart axis is; no new colour value is introduced.
    axis_chrome = (
        # Y axis: a full-height 1px-wide vertical rect at the left edge.
        '<rect class="%s" x="0" y="0" width="1" height="100%%" aria-hidden="true"/>'
        # X axis: a full-width 1px-tall horizontal rect at the bottom edge.
        '<rect class="%s" x="0" y="100%%" width="100%%" height="1" aria-hidden="true"/>'
        # Y ticks at the max/min levels, poking left into the label
        # column's own gap (style.css's .sparkline grid column-gap).
        '<rect class="%s" x="-4" y="%.2f%%" width="4" height="1" aria-hidden="true"/>'
        '<rect class="%s" x="-4" y="%.2f%%" width="4" height="1" aria-hidden="true"/>'
        # X ticks at the oldest/newest point positions, hanging below the
        # axis (a percentage y="100%%" paired with an absolute height).
        '<rect class="%s" x="%.2f%%" y="100%%" width="1" height="4" aria-hidden="true"/>'
        '<rect class="%s" x="%.2f%%" y="100%%" width="1" height="4" aria-hidden="true"/>'
    ) % (
        SPARKLINE_AXIS_CLASS,
        SPARKLINE_AXIS_CLASS,
        SPARKLINE_AXIS_CLASS, _point_y(hi),
        SPARKLINE_AXIS_CLASS, _point_y(lo),
        SPARKLINE_AXIS_CLASS, _point_x(0),
        SPARKLINE_AXIS_CLASS, _point_x(point_count - 1),
    )

    # Document order matters: SVG paints in document order and pointer
    # events go to the topmost element. Within each point, the cosmetic
    # marker is emitted immediately before its own hit target — unchanged
    # from before this task — so a hit target is never visually painted
    # under its own marker; `.sparkline-dot`'s own `pointer-events: none`
    # (style.css) is the actual reason a tap always reaches the
    # transparent target beneath, independent of paint order, but the
    # emission order is kept anyway to match the existing convention this
    # file's own prior comment already established here.
    line_segments = []
    circles = []
    prev_x = prev_y = None
    for index, (value, ts, reading_count) in enumerate(pairs):
        x = _point_x(index)
        y = _point_y(value)
        if prev_x is not None:
            line_segments.append(
                '<line class="%s" x1="%.2f%%" y1="%.2f%%" x2="%.2f%%" y2="%.2f%%"/>'
                % (SPARKLINE_LINE_CLASS, prev_x, prev_y, x, y))
        prev_x, prev_y = x, y

        # 260902-l0b: above the density threshold, the cosmetic marker is
        # not emitted at all (see _SPARKLINE_DENSE_POINT_THRESHOLD's own
        # derivation) — the hit target below still is, at its own reduced
        # radius, so every point stays reachable even though it is no
        # longer individually visible as a dot.
        if not dense:
            circles.append(
                '<circle class="%s" cx="%.2f%%" cy="%.2f%%" r="%d" aria-hidden="true"/>'
                % (SPARKLINE_DOT_CLASS, x, y, _SPARKLINE_DOT_RADIUS_PX))

        # quick task 260901-uzi (finding 3): the server now builds this
        # point's label from the same humanised (value, when) pair the
        # readout uses (_battery_reading_parts()) — battery-trend.js
        # reads the "when" half back out of the new data-when attribute
        # below rather than composing its own copy, which is what keeps
        # hover text and tap readout identical BY CONSTRUCTION rather
        # than by two matching format literals kept in sync by hand.
        # 260902-l0b: in daily mode, _daily_reading_parts() plays the same
        # role — the "when" half explicitly names the day and that the
        # value is a daily average, so the readout can never silently
        # mix an average with a raw reading.
        if daily:
            value_text, when_text = _daily_reading_parts(value, ts, reading_count)
        else:
            value_text, when_text = _battery_reading_parts(value, ts, now)
        escaped_when = escape_html(when_text)
        label = escape_html("%s — %s" % (value_text, when_text))
        # D-13/UXA-11: roving tabindex — only the chronologically-latest
        # (rightmost) point is a normal Tab stop; every other point is
        # removed from the natural Tab order (tabindex="-1") and instead
        # reachable via companion/static/battery-trend.js's arrow-key
        # moveFocusTo() handler. `pairs` is already in chronological
        # order and the x-coordinate math above already places the last
        # index rightmost, so this one condition identifies both
        # "latest" and "rightmost" simultaneously.
        is_latest = index == point_count - 1
        tabindex = "0" if is_latest else "-1"
        circles.append(
            '<circle class="%s" cx="%.2f%%" cy="%.2f%%" r="%d" tabindex="%s" '
            'role="button" data-mv="%d" data-ts="%s" data-when="%s" aria-label="%s">'
            "<title>%s</title></circle>"
            % (SPARKLINE_HIT_CLASS, x, y, hit_radius, tabindex, value, escape_html(ts),
               escaped_when, label, label))

    # Y-axis pair: max label first, min label second — .sparkline__y
    # (style.css) is a flex column with justify-content: space-between,
    # so document order top-to-bottom is what places max above min. X-axis
    # pair: oldest first, newest second — .sparkline__x is a flex row with
    # the same space-between, so document order left-to-right places
    # oldest before newest.
    y_labels_html = (
        '<div class="sparkline__y">'
        '<span class="sparkline-axis-label" aria-hidden="true">%d mV</span>'
        '<span class="sparkline-axis-label" aria-hidden="true">%d mV</span>'
        "</div>"
    ) % (hi, lo)
    x_labels_html = (
        '<div class="sparkline__x">'
        '<span class="sparkline-axis-label" aria-hidden="true">%s</span>'
        '<span class="sparkline-axis-label" aria-hidden="true">%s</span>'
        "</div>"
    ) % (
        escape_html(_axis_day_label(pairs[0][1]) if daily else _axis_clock_label(pairs[0][1])),
        escape_html(_axis_day_label(pairs[-1][1]) if daily else _axis_clock_label(pairs[-1][1])),
    )

    svg_html = (
        '<svg class="sparkline__canvas" role="group" aria-label="Battery trend">'
        "%s%s%s"
        "</svg>"
    ) % (axis_chrome, "".join(line_segments), "".join(circles))

    # Grid document order: the Y-label column first (grid column 1, row
    # 1), then the canvas (auto-placed into column 2, row 1 — the only
    # cell left open once the label column claims column 1), then the
    # X-label row last (explicitly column 2 in style.css, which the grid
    # auto-places into row 2, the only open cell in that column). See
    # style.css's `.sparkline` rule for the full grid contract.
    return '<div class="sparkline">%s%s%s</div>' % (y_labels_html, svg_html, x_labels_html)


def battery_status(rows):
    """`"error"` when any two chronologically-consecutive readings in
    `rows` (newest-first) drop by more than `BATTERY_DROP_WARN_MV`,
    `"ok"` otherwise (including fewer than two usable readings — nothing
    to compare, so nothing to flag). A row with a missing/non-numeric
    `battery_mv` is skipped rather than compared, never crashing the
    scan or producing a false anomaly from a bad reading.
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
            return "error"
    return "ok"


def corroboration_status(counts):
    """Map `history_db.corroboration_counts()`'s three-state dict
    (`counts`, keyed by the stored strings `"True"`/`"None"`/`"False"`)
    to a per-row status: agreement and the single-source unknown state
    are always `"ok"` (D-15: the unknown state is informational and must
    never read as a failure), and a disagreement bucket with a non-zero
    count is `"warn"` — deliberately a warning, not an error (this
    plan's own Task 1 action text), since a disagreement already
    triggers D-04's "leave the panel alone" on the render side; this
    page surfaces it for visibility without duplicating that as a second
    hard fault.
    """
    counts = counts or {}
    return {
        "True": "ok",
        "None": "ok",
        "False": "warn" if counts.get("False") else "ok",
    }


def collect_anomalies(device_state, pipeline_state, battery_state, disagreement_warn):
    """A list of short, human-readable strings — one per non-healthy
    condition among the four D-14 signals this page tracks. An empty
    list means "render no anomaly banner at all" (D-21's uncluttered
    all-clear); render() is the only caller that decides what to do with
    the result.

    Since 06.6.1-03: render() no longer renders this list's contents
    anywhere on the page (the redundant bulleted detail-list markup was
    removed — the Overview tiles already carry the same information via
    colour) — only its emptiness is consumed, to decide whether the
    banner appears at all. The four item strings below deliberately
    survive anyway: they remain the readable, greppable definition of
    what counts as an anomaly.

    Since 06.6.2-06 (UXA-14): anomaly_active()/health_severity() no
    longer route their verdict through this exact function directly —
    they route through overall_severity(), which derives a real
    "ok"/"warn"/"error" severity from the same four state/flag inputs
    this function takes. This function itself is unchanged and remains
    the readable, greppable definition of what counts as an anomaly (and
    test_status_pages.py still calls it directly) — only its role as the
    presence-gate inside render() was replaced.
    """
    anomalies = []
    if device_state != "ok":
        anomalies.append("Device check-in is stale.")
    if pipeline_state != "ok":
        anomalies.append("ADS-B pipeline run is stale.")
    if battery_state != "ok":
        anomalies.append("A battery reading shows an abnormal drop.")
    if disagreement_warn:
        anomalies.append("ADS-B sources disagreed on the selected aircraft recently.")
    return anomalies


def overall_severity(device_state, pipeline_state, battery_state, disagreement_warn):
    """Derive one "ok"/"warn"/"error" severity from the same four D-14
    signals `collect_anomalies()` tracks — the precedence table UXA-14's
    own acceptance criteria require documenting explicitly:

        1. "error" wins: if any of `device_state`/`pipeline_state`/
           `battery_state` equals "error", the overall severity is
           "error", regardless of anything else.
        2. Otherwise "warn": if any of the three states equals "warn",
           or `disagreement_warn` is true, the overall severity is
           "warn".
        3. Otherwise "ok".

    Deliberate scope boundary: `_source_fault_block()`'s own
    always-rendered-when-true section is NOT folded into this
    precedence. It is not one of the four D-14 signals
    `collect_anomalies()` tracks (source-fault is a distinct CFG-05
    signal, rendered as its own block above the Overview grid), and
    folding it in here would silently change what `anomaly_active()` has
    always meant for existing callers. If a future phase wants
    source-fault to also drive nav/banner severity, that is a new
    decision, not an oversight of this function.
    """
    states = (device_state, pipeline_state, battery_state)
    if "error" in states:
        return "error"
    if "warn" in states or disagreement_warn:
        return "warn"
    return "ok"


def compute_health_state(state_dir, now=None):
    """WR-04: the single computation both `health_severity()`'s callers
    (the nav-tab dot) and `render()`'s callers (the full Health page)
    need — one call to `_read_health_inputs()` (five `_safe_query()`/
    `open_db()` reads) plus the four section builders, packaged into one
    dict. Previously `health_severity()` and `render()` each ran this
    same sequence independently against fresh DB connections at two
    different wall-clock instants; a write landing between the two
    (e.g. the systemd poll timer firing mid-request) could make the nav
    dot and the on-page banner disagree despite this module's own
    "structurally impossible" claim, and every authenticated page paid
    for the duplicated SQLite work regardless of which page was being
    viewed. `companion/app.py`'s `page_context()` now calls this (via
    `safe_health_state()`) exactly once per request and threads the
    result through `ctx["health_state"]` for `render()` to reuse — see
    that function's docstring for the fail-closed wrapper this one does
    not itself provide.
    """
    if now is None:
        now = history_db.utc_now_iso()
    inputs = _read_health_inputs(state_dir, now)
    device_html, device_state = _device_section(inputs["device_health"], now)
    pipeline_html, pipeline_state = _pipeline_section(inputs["pipeline_ts"], now)
    battery_html, battery_state = _battery_section(inputs["trend_rows"], inputs["daily_rows"])
    # 260902-l0b: computed from the same _battery_daily_series_usable()
    # predicate _battery_section() itself used above, so the heading
    # caption can never describe a window the chart is not actually
    # showing. Threaded through the returned dict rather than as a third
    # _battery_section() return value — source_fault_raw below is the
    # existing precedent for an input passed straight through this dict —
    # because _battery_section()'s own 2-tuple return is directly
    # unpacked by a pinned harness check (test_status_pages.py's
    # `markup, state = health_page._battery_section([])`).
    battery_caption = _battery_trend_caption(inputs["trend_rows"], inputs["daily_rows"])
    corroboration_html, disagreement_warn = _corroboration_section(
        inputs["corroboration_counts"])
    severity = overall_severity(
        device_state, pipeline_state, battery_state, disagreement_warn)
    # UXA-06/D-18: threaded through to render() so _anomaly_banner_html()
    # can name the real failing category or categories rather than
    # recomputing collect_anomalies() a second time from scratch.
    anomalies = collect_anomalies(
        device_state, pipeline_state, battery_state, disagreement_warn)
    return {
        "now": now,
        "source_fault_raw": inputs["source_fault_raw"],
        "device_html": device_html,
        "device_state": device_state,
        "pipeline_html": pipeline_html,
        "pipeline_state": pipeline_state,
        "battery_html": battery_html,
        "battery_state": battery_state,
        "battery_caption": battery_caption,
        "corroboration_html": corroboration_html,
        "disagreement_warn": disagreement_warn,
        "anomalies": anomalies,
        "severity": severity,
    }


def safe_health_state(state_dir, now=None):
    """Fail-closed wrapper around `compute_health_state()` — `None` on
    any unanticipated exception, never a raise.

    Wrapped in a broad `except Exception`, a deliberate departure from
    the narrow `(sqlite3.Error, OSError)` catches used elsewhere in this
    file: `_safe_query()`'s narrow catch protects one *section* of one
    page, whereas `page_context()` calls this function on **every**
    authenticated page render, so an unanticipated raise here would turn
    every page in the app into a 500 over a decorative nav dot —
    exactly the reasoning `companion/app.py`'s
    `runway_images_available()` already established for its own
    never-raises contract in Phase 06.4. `None` (rather than a
    partially-populated dict) is deliberate too: `health_severity()`
    below treats it as "ok" (failing closed — a missing dot understates
    a problem the Health page itself will still report in full, rather
    than a crashed app reporting nothing at all), and `render()` treats
    it as "no precomputed state available", falling back to its own
    fresh `compute_health_state()` call rather than rendering from a
    dict with missing keys.
    """
    try:
        return compute_health_state(state_dir, now)
    except Exception:
        return None


def health_severity(state_dir, now=None):
    """The `ctx["health_severity"]` source of truth — "ok"/"warn"/"error"
    for `state_dir`, derived from the same four D-14 signals
    `collect_anomalies()`/`overall_severity()` track. The cross-page
    signal `companion/app.py`'s `page_context()` threads into `ctx` for
    every authenticated page (the "runway_images" precedent, Phase
    06.4), so the Health nav-tab notification dot and the anomaly banner
    can be drawn from one value without any nav renderer importing this
    page module (forbidden by `companion/pages/__init__.py`).

    Routes its verdict through `safe_health_state()` (in turn
    `compute_health_state()` and the exact same four section builders
    `render()` calls), keeping only the severity and discarding the
    markup — deliberate, not wasteful: it is what makes it structurally
    impossible for the nav dot and the banner to disagree *when fed the
    same precomputed state*, since a second, cheaper reimplementation of
    the anomaly rules would be a second copy of them, and this module's
    whole D-14 design rests on there being one. Callers that already
    hold a `compute_health_state()`/`safe_health_state()` result (i.e.
    `page_context()`) should read `state["severity"]` directly instead
    of calling this function a second time — see WR-04.
    """
    state = safe_health_state(state_dir, now)
    return state["severity"] if state else "ok"


def anomaly_active(state_dir, now=None):
    """`True` when the current severity for `state_dir` is not "ok",
    `False` otherwise — the boolean shape existing callers (including
    test_status_pages.py's direct calls) already expect. Since 06.6.2-06
    (UXA-14), this is a thin wrapper: it routes through
    `health_severity()`/`overall_severity()` rather than directly
    through `collect_anomalies()`, so this module's D-14 anomaly rules
    have exactly one implementation, not two.
    """
    return health_severity(state_dir, now) != "ok"


def _starts_with_acronym(phrase):
    """True when `phrase`'s first whitespace-delimited word carries a
    capital letter somewhere after its first character — the signature
    of an acronym or initialism ("ADS-B", "RER", "GPS") as opposed to an
    ordinary sentence-initial word ("Device", "A", "Battery").

    Used by `_anomaly_category_text()` to decide whether a phrase's
    leading letter may be safely lower-cased for mid-sentence joining.
    """
    first_word = phrase.split(" ", 1)[0]
    return any(character.isupper() for character in first_word[1:])


def _anomaly_category_text(anomalies):
    """A comma-joined, human-readable naming of `anomalies`
    (`collect_anomalies()`'s own literal strings, in order) — UXA-06's
    fix for the anomaly banner naming its real failing category or
    categories instead of a generic "check the tiles below".

    Each item's trailing period is dropped (`rstrip(".")`) so the
    phrases read as one joined clause rather than a run of complete
    sentences, and every item after the first has its leading letter
    lower-cased to match normal mid-sentence capitalisation — the
    first item keeps its original (sentence-initial) case. This is a
    light, mechanical transformation of `collect_anomalies()`'s own
    four literal strings (not an independently-maintained copy), so
    the two can never drift apart.

    The lower-casing skips any phrase whose first word is an acronym or
    other already-capitalised proper noun. Two of `collect_anomalies()`'s
    four literals begin with "ADS-B", and blindly lower-casing the first
    character rendered them as the visible nonsense "aDS-B ..." in the
    banner whenever such an item was not the first one listed. The test
    is "does the first word contain a capital letter after its first
    character" — true for "ADS-B", false for ordinary sentence-initial
    words like "Device" or "A" — which needs no hard-coded list of
    acronyms and so cannot go stale when a fifth anomaly string is
    added.
    """
    phrases = []
    for index, anomaly in enumerate(anomalies):
        phrase = anomaly.rstrip(".")
        if index > 0 and phrase and not _starts_with_acronym(phrase):
            phrase = phrase[0].lower() + phrase[1:]
        phrases.append(phrase)
    return ", ".join(phrases)


def _anomaly_category_labels(anomalies):
    """One short pill label per `anomalies` entry (`collect_anomalies()`'s
    own literal strings, in order) — the pill-shaped counterpart to
    `_anomaly_category_text()`'s comma-joined clause.

    Reuses that function's trailing-period stripping (`rstrip(".")`) so
    both derivations read the same source strings the same way, but
    never lower-cases a label's leading letter: `_anomaly_category_text()`
    only lower-cases non-first items so the joined clause reads as one
    mid-sentence run, and its `_starts_with_acronym()` guard exists
    solely to protect that lower-casing from mangling "ADS-B" into
    "aDS-B". A pill is not mid-sentence text — every label keeps its
    original, sentence-initial case, so there is nothing for that guard
    to protect here; it needs no separate call in this function.
    """
    return [anomaly.rstrip(".") for anomaly in anomalies]


def _anomaly_banner_html(severity, anomalies):
    """Build the D-07 anomaly banner directly, rather than routing
    through `layout.anomaly_banner()`: that shared helper escapes its
    whole message as one plain-text string, which is correct for a flat
    banner but structurally incompatible with emitting one
    `<span class="banner__pill">` per failing category alongside the
    lead text. This is a deliberate local builder — not a duplication to
    be "cleaned up" by re-routing through the shared helper later.

    Reproduces `layout.anomaly_banner()`'s exact class/role mapping:
    `"error"` severity renders `banner--anomaly` / `role="alert"`;
    anything else (in practice only `"warn"`) renders `banner--warn` /
    `role="status"`.

    Emits, as flex children of the `.banner` row: one escaped `<span>`
    carrying the count-and-noun lead ("N warning(s)"/"N error(s)"), one
    `<span class="banner__pill">` per `_anomaly_category_labels()` entry,
    and finally a `<span class="visually-hidden">` accessible tail
    carrying `_anomaly_category_text()`'s own comma-joined clause plus
    `ANOMALY_BANNER_TEXT` — the exact sentence this banner rendered
    before pills existed. That tail is what keeps every existing
    `ANOMALY_BANNER_TEXT in rendered` presence/count check in
    test_status_pages.py passing unmodified, and gives a screen reader
    one coherent sentence instead of a lead phrase followed by a run of
    disconnected pill labels.
    """
    css_class = "banner--anomaly" if severity == "error" else "banner--warn"
    role = "alert" if severity == "error" else "status"
    noun = _SEVERITY_BANNER_NOUNS.get(severity, "issue")
    count = len(anomalies)
    plural = "" if count == 1 else "s"
    lead_html = "<span>%s</span>" % escape_html("%d %s%s:" % (count, noun, plural))
    pills_html = "".join(
        '<span class="banner__pill">%s</span>' % escape_html(label)
        for label in _anomaly_category_labels(anomalies)
    )
    tail_text = "%s — %s" % (_anomaly_category_text(anomalies), ANOMALY_BANNER_TEXT)
    tail_html = '<span class="visually-hidden">%s</span>' % escape_html(tail_text)
    return '<div class="banner %s" role="%s">%s%s%s</div>' % (
        css_class, role, lead_html, pills_html, tail_html)


def _unavailable_block():
    return '<p class="text-body">%s</p>' % escape_html(HEALTH_UNAVAILABLE_TEXT)


def _section_intro_html(section_id, heading, description):
    """A `<div class="section-intro">` wrapping one id-anchored `<h2>`
    plus a muted one-sentence description on the same baseline (quick
    task 260901-tsa, finding B) — the wrapper exists so the description
    sits inline and baseline-aligned with its heading rather than as a
    separate stacked paragraph.

    The `<h2 id="..." class="text-heading">...</h2>` this emits is
    byte-identical to the string `render()` built directly before this
    task — same attribute order (`id` then `class`), same class value,
    same `escape_html()` call on the heading text — because
    `companion/test_status_pages.py`'s existing structural checks match
    that whole string literally and count `'<h2 id="'` occurrences; this
    builder must never drift from that shape.

    The description is classed `text-label section-caption` — the same
    pair quick task 260901-re6 already established for exactly this
    "muted one-sentence-under-a-heading" role on Settings — reused
    rather than reinvented. A second class for the same role would
    reopen the second-muted-strength defect this stylesheet's own
    comments record having fixed twice.
    """
    return (
        '<div class="section-intro">'
        '<h2 id="%s" class="text-heading">%s</h2>'
        '<p class="text-label section-caption">%s</p>'
        "</div>"
    ) % (section_id, escape_html(heading), escape_html(description))


def _device_section(device_health, now):
    if device_health is _DB_UNAVAILABLE:
        return _unavailable_block(), "ok"
    ts = (device_health or {}).get("ts")
    age = layout.age_seconds(ts, now)
    state = staleness_status(age, STALE_DEVICE_WARN_S, STALE_DEVICE_ERROR_S)
    # quick task 260901-tsa (finding C): this used to be
    # `status_dot(state, DEVICE_FRESHNESS_LABEL) + detail` — but
    # stat_tile()'s own caption already renders DEVICE_FRESHNESS_LABEL,
    # so the tile printed its own name twice, one line under the other:
    # the caption row naming the signal, then the body row naming it
    # again before the timestamp. The caption is the tile's title role
    # and stays; the body's job is to answer it, so it is now caption +
    # one `stat-tile__value` timestamp, matching the sibling
    # Resolution-rate tile's own shape. Dropping the dot loses no state
    # signal: render()'s stat_tile() call still receives this function's
    # `state` return value and still paints the tile's status-coloured
    # top border and tints its icon from it (D-12's colour carrier is
    # unchanged), and collect_anomalies() still names a stale device in
    # the anomaly banner's text. Keeping a dot while dropping only its
    # text was considered and rejected: status_dot() always emits a
    # dot-label span, so that would mean either an empty span or a
    # second copy of its state->class mapping duplicated here.
    #
    # D-09: concise_timestamp_html() already returns pre-escaped-safe
    # markup — wrapping it in escape_html() a second time would
    # double-encode it and print the raw tags as visible text.
    detail = layout.concise_timestamp_html(ts, now)
    row = '<p class="stat-tile__value">%s</p>' % detail
    return row, state


def _pipeline_section(pipeline_ts, now):
    if pipeline_ts is _DB_UNAVAILABLE:
        return _unavailable_block(), "ok"
    age = layout.age_seconds(pipeline_ts, now)
    state = staleness_status(age, STALE_PIPELINE_WARN_S, STALE_PIPELINE_ERROR_S)
    # quick task 260901-tsa (finding C): same fix, same reasoning, as
    # _device_section() above — see that function's comment for the
    # full explanation of why dropping the dot is safe.
    #
    # D-09: concise_timestamp_html() already returns pre-escaped-safe
    # markup — wrapping it in escape_html() a second time would
    # double-encode it and print the raw tags as visible text.
    detail = layout.concise_timestamp_html(pipeline_ts, now)
    row = '<p class="stat-tile__value">%s</p>' % detail
    return row, state


def _latest_numeric_battery_reading(trend_rows):
    """The chronologically-latest reading's own `(millivolts, timestamp)`
    pair, scanning `trend_rows` (newest-first, `battery_trend_rows()`'s
    own ordering) for the first row carrying a genuine int `battery_mv`
    — the same numeric-only filter `battery_sparkline_svg()` applies,
    applied here without needing that function's full chronological-
    reversal/plotting pass. Returns `None` when no row qualifies; only
    called on the branch where a chart already exists (`sparkline_html`
    non-empty), so that branch always yields a real reading here too.

    quick task 260901-uzi: this used to return a pre-formatted
    "{value} mV — {ts}" label directly
    (`_latest_numeric_battery_label()`, retired); it now stops one step
    earlier, at the raw `(mv, ts)` pair, so the caller can build both the
    humanised value and detail parts via `_battery_reading_parts()` and
    still hold the raw `ts` for the readout's `title` tooltip.
    """
    for row in trend_rows:
        value = row.get("battery_mv")
        if isinstance(value, int) and not isinstance(value, bool):
            return value, row.get("ts")
    return None


def _battery_readout_block(latest_reading, now):
    """The reserved-height readout line `companion/static/battery-trend.js`
    writes into on hover/tap/keyboard reveal. D-09/§5.3: seeded by
    default with `latest_reading`'s own humanised `(value, when)` pair
    (`_battery_reading_parts()`) — the exact same helper
    `battery_sparkline_svg()` uses per-point, so the resting text and the
    hover/tap text are built identically BY CONSTRUCTION — rather than
    the old static prompt (retired, `BATTERY_READOUT_PLACEHOLDER` no
    longer exists). `role="status"` already implies a polite live
    region, so no separate `aria-live` attribute is added.

    quick task 260901-uzi (finding 3): the readout used to print the raw
    ISO string inline — the one timestamp on this page that did not
    follow the house humanised pattern, and read (the developer's own
    words) as too bold, too big, not sober. It now reads as a scannable
    figure plus a muted trailing detail, which is this page's own
    validated sketch's `.battery-readout` treatment (the voltage
    emphasised, the trailing detail muted), and the machine-precise ISO
    moves to the detail span's `title` tooltip, exactly as
    `concise_timestamp_html()` does everywhere else on this page. The
    humanised string is strictly SHORTER than the raw-ISO one it
    replaces, so the reserved-height no-layout-jump guarantee (style.css's
    `.battery-readout` comment) is not weakened but strengthened — the
    old format was long enough to wrap at narrow widths and the new one
    is not.

    Two spans, not one string, because `companion/static/
    battery-trend.js`'s `reveal()` now writes the value and detail parts
    separately (quick task 260901-uzi reverses that file's own
    260901-tsa non-goal — see battery-trend.js's own header comment for
    why this task edits it after all): `battery-readout__value` (also
    `mono`, matching the sparkline's own monospace digits) holds the
    value part, `battery-readout__detail` (carrying the raw ISO in its
    `title` attribute) holds a separator plus the "when" part. `mono` is
    gone from the outer `<p>`'s own class list — style.css's `.mono`
    reach-through rule now targets `.battery-readout .mono` directly, so
    the value span alone carries it.

    Two things deliberately did NOT change with this move, and both
    matter: `role="status"` is the live region `battery-trend.js`
    announces every Left/Right/Home/End traversal through, and the
    element is still found by `getElementById` — its position in the
    document was never something that file depended on.
    """
    if latest_reading is None:
        value_text, when_text, raw_ts = "", "", ""
    else:
        mv, ts = latest_reading
        value_text, when_text = _battery_reading_parts(mv, ts, now)
        raw_ts = ts or ""
    return (
        '<p id="%s" class="battery-readout" role="status">'
        '<span class="battery-readout__value mono">%s</span>'
        '<span class="battery-readout__detail" title="%s"> — %s</span>'
        "</p>"
    ) % (
        BATTERY_READOUT_ID, escape_html(value_text),
        escape_html(raw_ts), escape_html(when_text))


def _battery_trend_section_html(battery_html, state, caption=None):
    """Wrap `_battery_section()`'s already-built markup in the full-width
    `BATTERY_SECTION_CLASS` card section (D-02) that replaces its old
    240px-floor grid tile.

    `battery_html` is already-safe markup (an already-escaped table, an
    SVG, a script tag) and is interpolated verbatim, with no call to
    `escape_html()` — the same "already-built markup passes through
    untransformed" contract `stat_tile()` and `_source_fault_block()`
    already follow; re-escaping it here would double-encode and print the
    raw tags as visible text instead of rendering them.

    SUPERSEDED (quick task 260902-j8w): this <h2> now emits only its
    escaped heading text plus the trailing "— Latest N readings" caption
    span — structurally identical to the `Unresolved prefixes` and
    `Resolution statistics` headings elsewhere on this page. The
    developer's own instruction was explicit: "supprime le logo de la
    batterie, car c'est inconsistant avec le reste" (remove the battery
    logo, it is inconsistent with the rest) — Health rendered exactly
    five <h2> elements and this was the only one that carried a glyph.
    This is a return to the validated Merged Health Sketch's own
    direction rather than a departure from it: the sketch's `<defs>`
    defines an `#icon-battery` glyph but its battery-trend section never
    references it via `<use>` — every `<use>` in the sketch sits inside
    a `.stat-tile__head`. The heading placement below was plan
    06.6.1-04's own reading of D-02, not something the sketch itself
    showed.

    What the paragraph below used to say, kept readable as history: the
    battery icon sat inside this <h2>, before the heading text, and
    carried no tint class — deliberately asymmetric with the tile icons;
    the icon inherited the heading's own colour through currentColor.
    That also resolved a wording drift in 06.6.1-UI-SPEC.md's Layout
    Contract (itself now further out of date): it says "each of the 4
    Overview tiles" gains an icon, written before plan 06.6.1-03 moved
    Battery trend out of the grid. All four Health signals carried their
    icon — three on tiles, one here on the section heading — and the
    icon set stayed at the contract's five. `06.6.1-VERIFICATION.md`'s
    criterion 26 ("Battery trend heading carries the battery icon —
    VERIFIED") is a completed phase's historical verification record and
    is left as written; it now describes a superseded state.

    quick task 260902-gjj (ISSUE 1): the trailing "— Latest N readings"
    span now composes `section-caption` with its existing `text-label`
    sizing class. `.text-label`/`.text-body` each supply a size and a
    weight but no colour, so an element carrying only one of them
    inherits full-strength `--color-text`; the muted strength for a
    subtitle/caption role lives in `.section-caption` and is composed
    onto the sizing class, never restated — `_section_intro_html()`
    above is the in-file precedent this follows (its own description
    paragraph pairs `text-label section-caption` for the same reason).
    `_registry_section()`'s read-only note applies the identical fix to
    its own `text-body` paragraph; see that function's own comment.

    quick task 260902-gjj (ISSUE 2): `state` is a deliberate signature
    widening — this function now composes its own `<section>` class
    attribute from `BATTERY_SECTION_CLASS` plus
    `layout.card_status_class(BATTERY_SECTION_CLASS, state)`, so the
    card's own top edge carries the same `battery_status()` verdict the
    now-retired in-body badge used to (06.5-CONTEXT D-01's original
    intent, restored — see this file's `battery-trend-section` comment
    reversal in companion/static/style.css). Unlike `_battery_section()`'s
    own single-argument call site (pinned by sibling phase 06.5's
    automated gate, per that function's own comment), a grep confirms
    nothing pins this function's arity, so the widening is safe. The
    status signal lives on the section's own edge (this modifier class),
    not on any icon — quick task 260902-j8w later removed the heading
    icon entirely, so this is no longer even a tint-class question.

    260902-l0b: `caption` is a deliberate signature widening — a third,
    defaulted parameter, so the sole call site (`render()`, below) can
    pass the mode-honest text `_battery_trend_caption()` computed, while
    any caller or check still passing only two positional arguments keeps
    working unchanged. `None` (the default) reproduces today's exact
    "Latest N readings" string byte-for-byte, in the same voice this
    function's own D-02/quick-task-260902-gjj widening used above.
    """
    modifier = layout.card_status_class(BATTERY_SECTION_CLASS, state)
    section_class = BATTERY_SECTION_CLASS + ((" " + modifier) if modifier else "")
    caption_text = caption if caption is not None else ("Latest %d readings" % BATTERY_TREND_LIMIT)
    return (
        '<section class="%s">'
        '<h2 class="text-heading">%s<span class="text-label section-caption">'
        "— %s</span></h2>"
        "%s"
        "</section>"
    ) % (
        section_class,
        escape_html(BATTERY_SECTION_HEADING), escape_html(caption_text), battery_html)


def _battery_section(trend_rows, daily_rows=None):
    """Return `(markup, state)` for the Battery trend tile.

    `state` drives two independent consumers from one value: the
    `status_dot()` badge rendered by this function, and
    `collect_anomalies()`'s abnormal-drop signal in `render()`.

    260902-l0b: `daily_rows` (the 90-day daily-average series from
    `battery_daily_rows()`) is a deliberate signature widening — a second,
    defaulted keyword parameter, chosen specifically because it cannot
    break the pinned single-argument call site
    `test_status_pages.py`'s `_battery_trend_timestamps_show_concise_format()`
    protects (06.5-02's own automated gate, retargeted onto the property
    it actually meant — see that check's own comment). When
    `_battery_daily_series_usable(daily_rows)` holds (at least two UTC-day
    buckets), the chart plots the daily series; otherwise it falls back
    to the same raw `trend_rows` series this function has always plotted.

    This fallback is NOT a reduced first version of the feature — the
    90-day daily chart is complete in this task and renders the moment
    two calendar days of history exist. It exists because the
    `if sparkline_html:` guard below gates BOTH the readout AND the
    script tag together: with only one day bucket, plotting the daily
    series would produce an empty sparkline, which without this fallback
    would mean no readout either — a page strictly worse than today's for
    a freshly-deployed device on day one. Everything else in this
    function keeps the raw `trend_rows` series unchanged regardless of
    which series the chart plots: the anomaly scan (`battery_status()`),
    the raw-readings disclosure table, its "View N readings" summary, and
    the readout (`_latest_numeric_battery_reading()`). Averaging a day's
    readings is precisely the operation that would hide the abnormal drop
    the anomaly scan exists to catch, so that one consumer must never see
    the daily series.

    The empty-history branch (`not trend_rows`) deliberately returns
    `"ok"`, not `"warn"` — unlike Device/Pipeline's never-seen state,
    which does map to `"warn"` via `staleness_status()`. Two reasons:
    (1) precedent — `corroboration_status()` already maps its own
    unknown state (`"None"`, single-source) to `"ok"`, on the rationale
    that an absence of information is not a failure; a device that has
    simply never reported a battery reading is the same shape of
    unknown, not a staleness signal like Device/Pipeline's silence.
    (2) a real coupling — `render()` passes this function's second
    return value straight into `collect_anomalies()`, which appends the
    literal copy "A battery reading shows an abnormal drop." for any
    non-`"ok"` battery state. A `"warn"` here would make a freshly
    provisioned deployment with zero readings display a banner
    asserting an abnormal drop that never happened. Keeping `"ok"`
    keeps one value honest for both consumers, so `render()` needs no
    decoupling.
    """
    if trend_rows is _DB_UNAVAILABLE:
        return _unavailable_block(), "ok"
    if not trend_rows:
        # quick task 260902-gjj (ISSUE 2): no badge here any more — the
        # card's own top edge carries this "ok" verdict instead, via
        # _battery_trend_section_html()'s `state` argument.
        return layout.empty_state(
            "No battery readings yet.",
            "No battery telemetry recorded yet — check back after the "
            "device's next poll."), "ok"
    state = battery_status(trend_rows)
    # 06.6-01 (D-02): now is computed locally, rather than threaded in as
    # a parameter, because _battery_section()'s positional-arity gate
    # (originally 06.5-02's exact single-argument pin, retargeted in
    # place by 260902-l0b onto "stays callable with exactly one
    # positional argument" once daily_rows joined this signature as a
    # second, defaulted keyword parameter) protects the call site
    # `battery_html, battery_state = _battery_section(trend_rows, ...)`.
    # history_db.utc_now_iso() is the same call render() already makes
    # for its own `now`.
    now = history_db.utc_now_iso()
    # D-09: the Timestamp column is now already-safe raw HTML (the
    # concise "HH:MM UTC (relative)" span, full ISO demoted to its
    # `title` attribute) — raw_columns=(0,) tells data_table() not to
    # re-escape it (that would double-encode and print the tags as
    # visible text). mono_columns keeps only the numeric mV column
    # monospaced; concise_timestamp_html()'s own <span class="mono">
    # already carries the mono styling for column 0.
    table_rows = [
        (layout.concise_timestamp_html(row.get("ts"), now, fallback=""), row.get("battery_mv"))
        for row in trend_rows
    ]
    table_html = layout.data_table(
        ["Timestamp", "Battery (mV)"], table_rows, mono_columns=(1,), raw_columns=(0,))
    # D-08: the raw readings table is collapsed behind a closed-by-default
    # native <details> disclosure — no custom JS toggler needed.
    disclosure_html = (
        '<details class="readings-disclosure"><summary>View %d readings</summary>%s</details>'
        % (len(trend_rows), table_html))
    # 260902-l0b: the series the CHART plots — the daily series when it is
    # usable, the raw series otherwise (the day-1 fallback). Everything
    # above and below this line keeps working from trend_rows unchanged.
    # One predicate (plot_daily) decides both the series AND the label
    # mode passed to battery_sparkline_svg() below, so the two can never
    # disagree about what is on screen.
    plot_daily = _battery_daily_series_usable(daily_rows)
    plot_rows = daily_rows if plot_daily else trend_rows
    sparkline_html = (
        battery_sparkline_svg(plot_rows, now=now, daily=plot_daily)
        if len(plot_rows) >= 2 else "")
    # The script tag and readout element are emitted only when a chart
    # actually exists (sparkline_html is non-empty) — a single-reading
    # device, or one whose only rows have non-numeric millivolts, gets no
    # chart and therefore no script, keeping "exactly one script tag, and
    # zero on the empty/no-chart path" testable and true. The tag's own
    # deferred-execution attribute is what makes a DOMContentLoaded
    # wrapper unnecessary in the script.
    chart_block = ""
    if sparkline_html:
        # quick task 260901-tsa (finding D): the readout now comes FIRST
        # — ahead of the sparkline — matching the validated sketch's
        # order (status chip, readout, chart). The script tag stays
        # last regardless, so "exactly one script tag, and zero on the
        # no-chart path" stays true unweakened.
        latest_reading = _latest_numeric_battery_reading(trend_rows)
        chart_block = (
            _battery_readout_block(latest_reading, now)
            + sparkline_html
            + '<script src="%s" defer></script>' % BATTERY_TREND_SCRIPT_SRC)
    # D-08: the chart (when present) comes before the collapsed table in
    # both DOM and visual order.
    #
    # quick task 260902-gjj (ISSUE 2): the badge that used to lead this
    # return value is retired (see the D-01 reversal record above
    # BATTERY_STATUS_LABEL's old home) — this card's status is now
    # carried entirely by _battery_trend_section_html()'s own status
    # modifier, driven by `state` below.
    return chart_block + disclosure_html, state


def _corroboration_details_html():
    """The D-08 collapsed `<details class="readings-disclosure">` block
    holding each `_CORROBORATION_ROWS` entry's full explanation — the
    three always-visible rows above keep only the dot, label, and count;
    the explanations move here, closed by default, matching the
    existing `readings-disclosure` idiom (companion/static/style.css's
    `.readings-disclosure` rule, landed for the battery readings table)
    verbatim for this second use, so no new CSS is needed.
    """
    dl_items = "".join(
        "<dt>%s</dt><dd>%s</dd>" % (escape_html(label), escape_html(explanation))
        for _key, label, _status, explanation in _CORROBORATION_ROWS
    )
    return (
        '<details class="readings-disclosure"><summary>More details</summary>'
        "<dl>%s</dl></details>" % dl_items
    )


def _corroboration_section(counts):
    if counts is _DB_UNAVAILABLE:
        return _unavailable_block(), False
    counts = counts or {}
    if not any(counts.values()):
        return layout.empty_state(
            "No corroboration data yet.",
            "Corroboration data appears once the ADS-B pipeline has "
            "recorded at least one runway event."), False

    statuses = corroboration_status(counts)
    rows_html = []
    for key, label, _default_state, _explanation in _CORROBORATION_ROWS:
        rows_html.append(
            '<p class="text-body">%s <span class="mono">%d</span></p>'
            % (
                layout.status_dot(statuses[key], label),
                counts.get(key, 0) or 0,
            )
        )
    return "".join(rows_html) + _corroboration_details_html(), bool(counts.get("False"))


def _source_fault_block(source_fault_raw):
    # quick task 260901-uzi (finding 4): deliberately NOT given the
    # `page-section--nested` modifier the two migrated cards in render()
    # carry. This block renders above both id-anchored sections, at the
    # same structural level as their own section headings, not nested
    # inside one — grouping it inside either section's nesting would
    # misrepresent the single most severe state this page can show as one
    # more subordinate card (quick task 260902-iag: the modifier itself no
    # longer changes type, only heading-to-content rhythm, but the
    # structural argument for keeping this block un-nested is unchanged).
    if source_fault_raw is _DB_UNAVAILABLE:
        return ""
    if not _meta_flag_true(source_fault_raw):
        return ""
    return (
        '<section class="page-section banner banner--anomaly">'
        '<h2 class="text-heading">%s</h2>'
        '<p class="text-body">%s</p>'
        "</section>"
    ) % (escape_html(SOURCE_FAULT_HEADING), escape_html(SOURCE_FAULT_BODY))


# --- 06.6.4.1-04 (D-11/D-12): migrated Unresolved-prefixes registry
# (CFG-04) and Resolution-statistics breakdown (CFG-08) — copied
# verbatim (in logic) from companion/pages/airlines_page.py. D-11
# explicitly warns against folding either read into
# _read_health_inputs()'s single dict: the registry read below goes
# through poll_loop.load_poll_state() (a filesystem/JSON failure mode,
# never a _safe_query() call), and the stats read goes through this
# module's own _safe_query() (a SQLite failure mode) — render() calls
# both independently so one failing source degrades only its own card.


def unresolved_rows(state_dir):
    """The CFG-04 registry as a sorted list of
    `(prefix, count, first_seen, last_seen, example_callsign)` tuples,
    read through `server.poll_loop.load_poll_state()`'s own
    `unresolved_prefixes` key — never a direct file open, never a
    re-derivation of `server/plane/enrich.py`'s own registry-writer's
    shape logic.

    Sorted by count descending, then prefix ascending, so the render
    order is deterministic regardless of dict insertion order.

    A registry entry whose value is not a dict, or whose `count` is not
    an int, is skipped rather than raising — the registry is written by
    production code but is also documented as hand-editable, so a bad
    edit must degrade gracefully, not crash the page.
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
    when it has any entries — CFG-04's summary status dot.
    """
    return "ok" if not rows else "warn"


def resolution_stats(conn, window_days=RESOLUTION_WINDOW_DAYS, now=None):
    """CFG-08's windowed resolution-rate breakdown: `history_db.
    route_source_counts()` bounded to the last `window_days`, mapped
    onto the four documented `enrich.resolve_route()` categories.

    The resolved percentage is the share of entries that produced any
    usable airline or route — i.e. everything except `"miss"` — matching
    the plan's own definition of "resolved" rather than a literal
    full-route-only figure. Phase 2 measured this at roughly 52.6% real
    traffic (server/plane/enrich.py's own docstring / 03.1 provenance),
    so a figure in that region is an expected outcome, not a defect.

    Returns `{"rows": [...], "total": N, "resolved_pct": float_or_None}`;
    `resolved_pct` is `None` (and `rows` is empty) when `total` is zero —
    guards the caller against a division by zero without it needing to
    check separately.
    """
    now_dt = now or datetime.now(timezone.utc)
    since = (now_dt - timedelta(days=window_days)).isoformat(timespec="seconds")
    counts = history_db.route_source_counts(conn, since=since)

    total = sum(counts.get(source, 0) for source, _label, _gloss in _SOURCE_ROWS)
    if total == 0:
        return {"rows": [], "total": 0, "resolved_pct": None}

    resolved = total - counts.get("miss", 0)
    resolved_pct = round((resolved / total) * 100, 1)
    rows = [
        (label, gloss, counts.get(source, 0))
        for source, label, gloss in _SOURCE_ROWS
    ]
    return {"rows": rows, "total": total, "resolved_pct": resolved_pct}


def _registry_filter_bar_html(total):
    """D-20's filter bar over the unresolved-prefix registry, only ever
    rendered when there is data to filter (matches `_registry_section()`'s
    own "no chrome with no data" rule, same as History's precedent).

    D-16 forbids a `<button>` element anywhere on the page this content
    originated from — the clear control is therefore a plain link
    element pointing at the filter input's own id rather than a
    submit-type button. `companion/static/list-filter.js`'s
    click-listener attachment (`document.querySelector
    ("[data-filter-clear]")`) does not care which element carries the
    attribute, and a fragment link to the input both scrolls to and
    (per standard browser fragment-navigation behaviour) focuses it in
    one action — a small UX bonus (ready to type the next query) that
    also needs zero new CSS beyond the already-shipped `.filter-bar`
    rules.
    """
    count_text = "%d of %d shown" % (total, total)
    empty_body = _FILTER_EMPTY_BODY_TEMPLATE % total
    return (
        '<div class="filter-bar">'
        '<label class="text-label" for="%s">%s</label>'
        '<div class="filter-bar__field">'
        "%s"
        '<input type="search" id="%s" data-filter-input>'
        "</div>"
        '<span class="filter-bar__count" data-filter-count>%s</span>'
        '<a href="#%s" data-filter-clear>Clear</a>'
        "</div>"
        '<div class="empty-state" data-filter-empty hidden>'
        '<p class="empty-state__heading text-heading">%s</p>'
        '<p class="empty-state__body text-body">%s</p>'
        "</div>"
    ) % (
        _FILTER_INPUT_ID, escape_html(_FILTER_LABEL_TEXT),
        layout.icon_html("icon-search"),
        _FILTER_INPUT_ID,
        escape_html(count_text),
        _FILTER_INPUT_ID,
        escape_html(_FILTER_EMPTY_HEADING),
        escape_html(empty_body),
    )


def _registry_row_html(index, prefix, count, first_seen, last_seen, example_callsign, now):
    """One `<tr>` for the unresolved-prefix registry table. First seen/
    Last seen switch to `layout.concise_timestamp_html()` (D-09) — its
    return value is already-safe markup and is interpolated verbatim,
    never re-escaped, matching this module's single-escaping-choke-point
    discipline for every other cell. `data-filter-text` (D-20/
    T-06.6.3-12) carries the lowercased prefix, escaped before
    interpolation into the attribute.
    """
    row_class = "row-alt" if index % 2 else "row"
    first_seen_html = layout.concise_timestamp_html(first_seen, now, fallback="")
    last_seen_html = layout.concise_timestamp_html(last_seen, now, fallback="")
    cells = (
        '<td class="mono">%s</td>' % escape_html(prefix),
        "<td>%s</td>" % escape_html(count),
        "<td>%s</td>" % first_seen_html,
        "<td>%s</td>" % last_seen_html,
        '<td class="mono">%s</td>' % escape_html(example_callsign),
    )
    filter_text = escape_html(prefix.lower() if isinstance(prefix, str) else str(prefix).lower())
    # data-filter-group: this card has only one representation per row
    # (no mobile-card pairing like History), but list-filter.js counts
    # distinct groups rather than raw elements, so every filterable row
    # must still carry one.
    return '<tr class="%s" data-filter-text="%s" data-filter-group="%d">%s</tr>' % (
        row_class, filter_text, index, "".join(cells))


def _registry_table_html(rows, now):
    """The unresolved-prefix registry table, hand-rolled (not via
    `layout.data_table()`) so each row can carry its own `data-filter-
    text` attribute — `data_table()` has no per-row attribute hook, and
    extending it with one would touch that builder's other call sites
    for no benefit to any of them. This mirrors
    `companion/pages/history_page.py::_history_table_html()`'s own
    precedent for exactly the same reason, matching `data_table()`'s CSS
    classes exactly for visual consistency.
    """
    headers = ("Prefix", "Count", "First seen", "Last seen", "Example callsign")
    header_cells = "".join("<th>%s</th>" % escape_html(h) for h in headers)
    body_rows = [
        _registry_row_html(index, prefix, count, first_seen, last_seen, example_callsign, now)
        for index, (prefix, count, first_seen, last_seen, example_callsign) in enumerate(rows)
    ]
    return (
        '<div class="data-table-wrap">'
        '<table class="data-table">'
        "<thead><tr>%s</tr></thead>"
        "<tbody>%s</tbody>"
        "</table>"
        "</div>"
    ) % (header_cells, "".join(body_rows))


def _registry_section(rows, now):
    # quick task 260902-bl2 (bug 2): the validated Merged Health Sketch
    # places this card's status dot inside its card-title row, as a
    # space-between flex pair (the sketch's `.wide-card__caption` role).
    # This function used to keep the dot as its own line below the
    # heading instead, on the finding that the developer's complaint here
    # was about spacing, not placement — the spacing is now the sketch's
    # (see the `.page-section--nested > h2` rule's retained
    # margin-bottom, style.css — quick task 260902-iag renamed what that
    # rule does; the margin itself is unchanged). That earlier rejection
    # is now partly obsolete: quick task 260902-gjj removes the dot
    # entirely (see the D-01 reversal record above BATTERY_STATUS_LABEL's
    # old home for the accessibility finding that licensed the removal
    # for both this card and Battery trend), so there is no dot left to
    # place in the card-title row either. The card's own top edge now
    # carries this coverage_status() verdict instead, composed at this
    # function's call site in render().
    #
    # quick task 260902-gjj (ISSUE 1): composes `section-caption` onto this
    # note's existing `text-body` sizing class, the same fix
    # `_battery_trend_section_html()` applies to its own trailing span —
    # see that function's docstring for the full reasoning. Deliberately
    # NOT switched to `text-label`: this is a full sentence of prose at
    # Body size, and dropping it to Label size would be an unrequested
    # size change that would also disagree with the sibling prose in this
    # same card region.
    header_html = '<p class="text-body section-caption">%s</p>' % escape_html(_READ_ONLY_NOTE)

    if not rows:
        return header_html + layout.empty_state(_NO_GAPS_HEADING, _NO_GAPS_BODY)

    filter_html = _registry_filter_bar_html(len(rows))
    table_html = _registry_table_html(rows, now)
    return header_html + filter_html + table_html


def _stats_table_html(stats):
    """The resolution-statistics breakdown table. Returns the empty
    string when there is nothing to show (no data yet, or the database
    is unavailable) — `_resolution_rate_tile_html()` already carries
    that message once, and this card must not repeat it.

    quick task 260901-uzi (finding 2): this is the only table in the app
    whose Description column carries real prose (the `_SOURCE_ROWS`
    glosses, up to full sentences), which is why it is the only one that
    opts into `layout.data_table()`'s `prose` keyword. The
    unresolved-prefix registry directly above it on the same page is
    deliberately NOT opted in: its five columns hold short values whose
    combined max-content width is bounded, and the wrapper absorbs it
    exactly as designed.

    quick task 260902-bl2 (bug 1): the same reason this is the only
    table that opts out of the no-crop floor is the reason it is the
    only one whose middle column opts into the `desc` column role — it
    is the only table in the app whose cells hold prose rather than
    values, and the validated sketch's own Resolution-statistics table
    (`td.desc`) mutes exactly that column so the Source labels and
    Counts stay the scannable part.
    """
    if stats is _DB_UNAVAILABLE or stats["total"] == 0:
        return ""
    return layout.data_table(
        ["Source", "Description", "Count"], stats["rows"],
        desc_columns=(1,), prose=True)


def _resolution_rate_tile_html(stats):
    """The Resolution-rate `stat_tile()`'s content (UI-SPEC §5.5) — the
    same two-line "figure" half the old Airlines page's promoted
    headline built (`_resolved_headline_html()`, `airlines_page.py`
    L292-313), reused verbatim rather than reworded, now living inside a
    `stat_tile()` card instead of a bare page-header slot.
    """
    if stats is _DB_UNAVAILABLE:
        return _unavailable_block()
    if stats["total"] == 0:
        return layout.empty_state(_NO_STATS_HEADING, _NO_STATS_BODY)
    return (
        '<p class="stat-tile__value">%.1f%% resolved</p>'
        '<p class="text-label">over the last %d days, %d events</p>'
    ) % (stats["resolved_pct"], RESOLUTION_WINDOW_DAYS, stats["total"])


def _read_health_inputs(state_dir, now):
    """The six `_safe_query()` reads `render()` and `anomaly_active()`
    both need, single-sourced into one dict.

    `render()` and `anomaly_active()` must be looking at the same six
    values, or the Health nav-tab dot and the page's own anomaly banner
    can disagree on screen — single-sourcing the *inputs* (not just the
    section-builder calls that consume them) is what removes that whole
    class of drift at the root, before it ever has a chance to appear.

    260902-l0b: grew from five reads to six — `daily_rows` joins
    `trend_rows` here, in the one atomic snapshot, because it is a
    battery-health read consumed by the same section builder
    (`_battery_section()`) from the same table (`device_health`) in the
    same request. This does NOT reopen D-11: the migrated registry/stats
    reads in `render()` stay their own independent calls, deliberately
    NOT folded in here, because they are a genuinely DIFFERENT failure
    mode (filesystem/JSON vs SQLite) feeding a DIFFERENT card that must
    keep failing independently of this one — see `render()`'s own comment
    at that call site for the unchanged reasoning.
    """
    cutoff = _cutoff_iso(now, _CORROBORATION_WINDOW_DAYS)
    return {
        "device_health": _safe_query(state_dir, history_db.latest_device_health),
        "pipeline_ts": _safe_query(
            state_dir,
            lambda conn: history_db.get_meta(conn, history_db.META_LAST_PIPELINE_RUN)),
        "source_fault_raw": _safe_query(
            state_dir,
            lambda conn: history_db.get_meta(conn, history_db.META_SOURCE_FAULT)),
        "trend_rows": _safe_query(state_dir, battery_trend_rows),
        "daily_rows": _safe_query(state_dir, lambda conn: battery_daily_rows(conn, now)),
        "corroboration_counts": _safe_query(
            state_dir,
            lambda conn: history_db.corroboration_counts(conn, since=cutoff)),
    }


# --- 260902-chc: D-12 reversal, recorded at the removal site ---------------
#
# SUPERSEDED — D-12 (06.6.3-CONTEXT.md) gave Health "an explicit Refresh
# action plus a stale-view warning ... no automatic background polling",
# reasoning that this "avoids new steady-state request volume and keeps
# authoritative health severity server-computed only". After living with
# that manual-refresh pattern in real use, the developer chose the
# opposite for Health specifically: this page now refreshes itself on a
# named-interval, visibility-gated timer — see companion/static/
# freshness.js's own header for the mechanism decision (with the losing
# option's genuine advantages named) and the fuller reversal record.
#
# The stale-view banner that used to render here (`_STALE_VIEW_BANNER_HTML`,
# retired outright, not just hidden more often) is gone for a reason
# beyond "the audit rule changed": its entire job was reporting that the
# page had gone stale, and a page that refreshes itself cannot go stale —
# the banner could only ever have become a lie if kept.
#
# What was actually traded away is D-12's request-volume half, and it is
# bounded: freshness.js's tab-visibility gate means a backgrounded or
# closed Health tab still produces zero requests, exactly as before.
#
# D-12's OTHER half — authoritative severity stays server-computed
# only — is NOT reversed here; it is strengthened. A whole-page reload
# regenerates every verdict server-side on every cycle, so no health
# state is ever recomputed client-side, and freshness.js still computes
# no health verdict of any kind — it only reveals a pill and reloads.


def render(ctx):
    state_dir = ctx["state_dir"]
    now = ctx.get("now") or history_db.utc_now_iso()

    # WR-04: reuse the state page_context() already computed (via
    # safe_health_state()) and threaded into ctx["health_state"] for
    # every authenticated route, rather than re-deriving it from a
    # second, non-atomic set of DB reads. Falls back to a fresh
    # compute_health_state() call when ctx carries no precomputed state
    # — e.g. a test or caller that builds ctx directly without going
    # through page_context() — preserving this function's previous
    # standalone behaviour for those callers.
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

    # D-11: the migrated registry/stats reads are their own independent
    # calls here, deliberately NOT folded into _read_health_inputs()'s
    # single dict — the registry read is a filesystem/JSON failure mode
    # (poll_loop.load_poll_state(), inside unresolved_rows()), the stats
    # read is a SQLite failure mode (_safe_query()); merging them would
    # make one query's failure take down a card that used to fail
    # independently on the page it came from.
    registry_rows = unresolved_rows(state_dir)
    stats = _safe_query(
        state_dir, lambda conn: resolution_stats(conn, RESOLUTION_WINDOW_DAYS))

    device_tile_html = layout.stat_tile(
        DEVICE_FRESHNESS_LABEL, device_html, device_state, icon=ICON_DEVICE)

    # battery_state is still consumed above (collect_anomalies() still
    # takes it), and (quick task 260902-gjj, ISSUE 2) it once again paints
    # a status-coloured border — no longer a stat-tile border (D-02
    # already moved this content out of .stat-tile), but the
    # battery-trend section's own card-level top edge, via
    # _battery_trend_section_html()'s new `state` argument below. A
    # different mechanism reaching the same original intent D-01's own
    # reference note expected.
    server_data_tiles_html = (
        layout.stat_tile(
            PIPELINE_FRESHNESS_LABEL, pipeline_html, pipeline_state, icon=ICON_PIPELINE)
        + layout.stat_tile(
            "Corroboration", corroboration_html,
            "warn" if disagreement_warn else "ok", icon=ICON_CORROBORATION)
        + layout.stat_tile(RESOLUTION_RATE_LABEL, _resolution_rate_tile_html(stats), None)
    )

    # 260902-chc: SUPERSEDED — this used to be a manual Refresh link
    # (D-12/UXA-13, see the reversal record above this function). It is
    # now the hidden-by-default "Updating…" pill companion/static/
    # freshness.js reveals just before each visibility-gated reload.
    # `data-loaded-at` survives the reversal unchanged — `now` is
    # already computed once per request by companion/app.py's
    # page_context() — and gains a second job there (a tab returning
    # from a long hidden stretch uses it to decide whether it owes an
    # immediate catch-up refresh; see freshness.js's own header).
    # escape_html() is required on `now` only: it is real, request-scoped
    # data. REFRESH_PILL_TEXT is a static module constant and needs
    # none, the same distinction the retired banner comment above drew.
    #
    # No ARIA role on the pill: a live region announces on content
    # mutation, not on a visibility change, so a role="status" pill whose
    # text never changes would announce nothing anyway — and the page
    # load this pill precedes is itself announced as a navigation by
    # every screen reader, making a second announcement redundant. The
    # real accessibility cost this mechanism carries and does not solve:
    # a reload that fires while a screen-reader user is reading with
    # focus on the document body returns their virtual cursor to the
    # top, and freshness.js's interaction-skip guard cannot detect that
    # state. Accepted in writing, not left as an omission: the lever if
    # this bites is the refresh interval, not the announcement, and a
    # live screen-reader pass is named in this task's SUMMARY.
    freshness_html = (
        '<span class="refresh-pill" data-refresh-pill data-loaded-at="%s" hidden>%s%s</span>'
        % (escape_html(now), layout.icon_html("icon-refresh"), REFRESH_PILL_TEXT))

    # §5.2 (D-10): two id-anchored sections. Screen holds the
    # Device-freshness tile wrapped in its own single-tile dashboard-grid
    # (quick task 260901-tsa, finding E) plus the battery-trend section,
    # exactly where it sat before. Screen used to skip the dashboard-grid
    # wrapper on the premise that a single-tile grid row and a bare
    # block-level tile render identically at full column width — that
    # premise is true about WIDTH and is exactly why this ever shipped,
    # but it silently omitted spacing: .dashboard-grid declares
    # `margin-bottom: var(--space-2xl)` and .stat-tile declares no
    # margin at all, so the standalone tile sat flush against the
    # battery-trend card below it with zero gap, while the Server & data
    # grid kept its 48px. The validated sketch itself wraps its own
    # single Device tile in a dashboard-grid for the same reason. Server
    # & data holds the three-tile grid, then the two migrated full-width
    # cards (D-11: .page-section, never .stat-tile/.dashboard-grid —
    # that container swap is the fix for the wide-table-in-a-240px-track
    # failure mode, a different container and still correct, untouched
    # by this edit).
    screen_section_html = (
        _section_intro_html(
            SCREEN_SECTION_ID, SCREEN_SECTION_HEADING, SCREEN_SECTION_DESCRIPTION)
        + '<div class="dashboard-grid">' + device_tile_html + '</div>'
        + _battery_trend_section_html(battery_html, battery_state, battery_caption)
    )
    # quick task 260902-gjj (ISSUE 2): the registry card's own class
    # attribute composes the same three pieces in the same order every
    # harness lookup below expects — base, then the pre-existing nested
    # modifier, then the new status modifier — so a literal-prefix lookup
    # keyed on "page-section page-section--nested" still finds this card
    # first (registry_class is built, never the stats card's literal,
    # which stays exactly "page-section page-section--nested" below).
    registry_modifier = layout.card_status_class("page-section", coverage_status(registry_rows))
    registry_class = "page-section page-section--nested" + (
        (" " + registry_modifier) if registry_modifier else "")
    server_data_section_html = (
        _section_intro_html(
            SERVER_DATA_SECTION_ID, SERVER_DATA_SECTION_HEADING,
            SERVER_DATA_SECTION_DESCRIPTION)
        + '<div class="dashboard-grid">' + server_data_tiles_html + '</div>'
        # quick task 260901-uzi (finding 4): both migrated cards carry an
        # additive `page-section--nested` modifier — they sit nested
        # inside this section's own .section-intro heading, so their own
        # <h2> is a subordinate tier, not a peer of it. SUPERSEDED by
        # quick task 260902-iag: the modifier used to also demote that
        # tier's type (style.css's `.page-section--nested > h2` rule set
        # a smaller size and a heavier weight); the developer compared
        # that demoted heading against Settings' own 20px heading and
        # asked for the Settings match, so the rule now sets no
        # typography at all — what the modifier buys today is the card's
        # own heading-to-content rhythm (its retained margin-bottom), and
        # the nesting relationship itself is expressed by the card's
        # border/surface/padding, not by type. `_source_fault_block()`
        # below is deliberately NOT given this modifier: it renders above
        # both sections, at the same structural level as the section
        # headings themselves, so grouping it inside either section's
        # nesting would misrepresent the single most severe state this
        # page can show as one more subordinate card — see that
        # function's own class list.
        + '<section class="%s"><h2 class="text-heading">%s</h2>%s</section>' % (
            registry_class, escape_html(UNRESOLVED_SECTION_HEADING),
            _registry_section(registry_rows, now))
        # quick task 260902-gjj (ISSUE 2): this card deliberately gets NO
        # status modifier — _stats_table_html() computes no verdict (it
        # returns either the empty string or a plain data_table), and
        # resolution_stats() returns counts and a percentage with no
        # status field. No status function exists for this card anywhere
        # in this module (confirmed from source, not assumed). Its
        # neutral hairline is therefore the correct signal that it
        # carries no pass/fail state — not an omission to "complete the
        # pattern" with an accent border.
        + '<section class="page-section page-section--nested"><h2 class="text-heading">%s</h2>%s</section>' % (
            escape_html(STATS_SECTION_HEADING), _stats_table_html(stats))
    )

    return (
        layout.page_header(
            "Health", purpose=PAGE_PURPOSE_TEXT, freshness_html=freshness_html)
        + _source_fault_block(source_fault_raw)
        + banner_html
        + screen_section_html
        + server_data_section_html
    )
