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
import os
import re
import sqlite3
from datetime import date, datetime, timedelta, timezone  # 24-07-PLAN.md
# Task 2: `date` joins the three for the regularity grid's own window walk,
# which is ORDINAL calendar arithmetic (date.toordinal()/fromordinal()) and
# deliberately carries no duration anywhere in it — see
# _check_in_regularity_cells()'s own docstring.
from zoneinfo import ZoneInfo

from companion.layout import escape_html
import companion.battery as battery
import companion.draw as draw
import companion.i18n as i18n  # D-05, 20-03-PLAN.md Task 3: every
# user-visible string on this page renders through i18n.t() — a
# shared, page-independent module (see its own module docstring),
# never a second copy of the lookup this module reaches for.
import companion.layout as layout
import companion.prefs as prefs  # D-09: the one place this module needs
# the resolved language directly rather than through i18n.t() — a
# label+colon join where French requires a real U+00A0 before the
# colon (_label_colon() below), not merely a translated label.
import companion.wake as wake  # D-05/A-23, 19-05-PLAN.md Task 3: the
# shared effective-wake-interval resolver and the derived device-
# staleness thresholds, replacing this module's own retired
# STALE_DEVICE_WARN_S/STALE_DEVICE_ERROR_S constants.
import companion.frame_state as frame_state  # 22-04-PLAN.md Task 3
# (D-03/CFG-26): the one frame-state resolution — the Frame tile's
# device_state/verdict/clock text and the nav notification dot all
# consume this module's resolve_state()/headline_template(), never
# re-deriving whether the frame is due, held or late from
# device_staleness_thresholds() alone (that primitive is kept, but only
# as the fallback for the degraded "no next-wake data at all" case).
from server import device_config  # D-05/A-23: read-only, for
# load_device_config() — this module already imports two sibling server
# modules below (history_db, poll_loop), so this is not a new boundary
# crossing.
from server import history_db
import server.poll_loop as poll_loop  # 06.6.4.1-04 (D-11): the migrated
# unresolved_rows() below now genuinely reads through this module's own
# load_poll_state() — the "exposed but not currently needed" note this
# import used to carry no longer applies.

HEALTH_UNAVAILABLE_TEXT = (
    "Health history is temporarily unavailable — check the companion "
    "service logs.")


def _label_colon(label):
    """`label` (already translated by the caller) followed by a
    language-appropriate colon separator — D-09 requires a real
    U+00A0 non-breaking space before ":" in French; English keeps the
    plain ":" this page has always rendered.
    """
    return label + (" :" if prefs.current_lang() == "fr" else ":")

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

# --- Off-box backup freshness (SEC-04, D-07/D-23, 37-02-PLAN.md) ----------
#
# Each successful pull of the VPS's nightly snapshot to the developer's Mac
# (deploy/backup/backup_gate.py's `ack`, plan 37-04) leaves a one-line
# marker file named by this env var. OFFBOX_MARKER_ENV_VAR is read here
# (the marker's one reader) rather than in companion/app.py, matching
# STALE_PIPELINE_WARN_S's own "the constant lives beside the code that
# uses it" placement above.
OFFBOX_MARKER_ENV_VAR = "SKYPANE_OFFBOX_MARKER"
OFFBOX_WARN_S = 3 * 86400  # D-07's 3-day threshold: one missed nightly
# pull is ordinary (the Mac was asleep, or launchd's wake catch-up has not
# fired yet), three means the Mac pull or the VPS backup job has actually
# stopped.
# The marker contract (shared with backup_gate.py's `ack`, RESEARCH.md
# §SEC-04 "The marker holds the archive name"): one archive name matching
# this pattern, plus an optional trailing newline — never a raw timestamp,
# so the same file also proves the acked archive actually exists.
_OFFBOX_MARKER_RE = re.compile(r"^skypane-state-(\d{8}T\d{6}Z)\.tar\.gz$")

# Device check-in: unlike the pipeline, this is genuinely tunable — the
# device's own effective wake cadence, which can be set on Settings or
# deployed via SKYPANE_SLEEP_S. RETIRED (D-05/A-23, 19-05-PLAN.md):
# STALE_DEVICE_WARN_S = 3600 (1 hour) / STALE_DEVICE_ERROR_S = 21600
# (6 hours, flightportrait's own documented backoff ceiling) used to be
# two fixed constants here, generous enough that a longer SKYPANE_SLEEP_S
# would not turn this page permanently red — but "generous enough for
# any cadence" is also "miscalibrated for every specific cadence": a
# healthy 30s-cadence device was called "stale" only after a full hour,
# a genuinely dead one only called an "outage" after six. D-05 replaces
# the fixed pair with `wake.device_staleness_thresholds(
# wake.effective_wake_interval_s(device_cfg))` — thresholds derived from
# the device's OWN cadence (3/12 missed wakes, floored at 5/20 minutes),
# computed in compute_health_state() and threaded into _device_section()
# below.

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

# Originally provisional (T-06-08-05): 100mV was borrowed from
# hardware/BATTERY-RUN.md's pre-registered --min-mv-drop, a whole-run
# opening-vs-closing gate rather than a per-reading one. DEVICE-05's
# completed run (BATTERY-RUN.md "Discharge Trend", 2026-09-02..14, 300 s
# cadence) now bounds the real per-reading drop: ~50 mV/day through the
# middle (well under 1 mV per reading) and, even across the final cliff,
# 3364->2960 mV over ~21 h — a couple of mV per reading on average. A
# genuine discharge therefore never drops 100mV between two consecutive
# readings, so crossing it still means an anomaly (a sampling artefact or
# a real fault), which is exactly what battery_status() flags. The value
# stays 100: the run kept only a sampled trend table, not every reading,
# so there is no measured per-reading noise floor to tighten it against.
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
    #
    # 19-06-PLAN.md Task 2 (D-06): the display label and explanation for
    # each row were rewritten from technical vocabulary (the retired
    # "Agreement"/"Disagreement" pair, and the retired "Single-source"
    # qualifier meaning "uncorroborated") into plain language a
    # household member can parse without reading the source — the
    # substance each row means is unchanged, only how it reads.
    # The stored key in each tuple's first slot ("True"/"None"/"False")
    # is the on-disk vocabulary history_db.save_poll_state() actually
    # writes and must NEVER be renamed to match the new labels — only
    # the second (label) and fourth (explanation) slots are copy.
    ("True", "Both agree", "ok",
     "Both flight-data sources on the frame picked the same aircraft."),
    # 22-12-PLAN.md Task 1 (X8, 22-UI-SPEC.md §5 contract 4): "ok" ->
    # "off". This row used to take the SAME ok token — and therefore the
    # same green dot — as "Both agree" above it, so a state that simply
    # means "there was nothing to compare against" was painted as good
    # news. `.dot--off` is defined in companion/static/style.css as "a
    # neutral, everyday state ... never a problem", which is exactly and
    # only what this row means; this is its second consumer this phase
    # (the frame's held state is the first, plan 22-04). NOT a fifth dot
    # and NOT a third colour — the whole change is which existing token
    # this row names.
    #
    # Colour is not the only signal, which is what makes the change safe
    # for a reader with no colour perception at all: the visible
    # `.dot-label` text stays "Only one saw it" and still differs from
    # "Both agree", and the detail slot carries the two counts. Read with
    # the dots removed entirely, the three rows are still three distinct
    # sentences. Do NOT "strengthen" this into `.dot--warn` — a warn dot
    # would light this page's own anomaly vocabulary for a non-problem.
    #
    # companion/pages/history_page.py's Flights table deliberately keeps
    # "ok" for the same stored key: 21-UI-SPEC/D-15 scoped the dot-only
    # treatment to that desktop table alone, and 22-UI-SPEC.md §5
    # contract 4 says Health's change does not reach it. The two pages
    # now diverge on this key's STATUS exactly as they already diverge on
    # its LABEL, and companion/test_view_pages.py pins both sides by name.
    ("None", "Only one saw it", "off",
     "Only one of the two sources returned an aircraft this cycle — "
     "that is not the same as a disagreement, there was simply nothing "
     "from the other source to compare it against."),
    ("False", "They disagree", "warn",
     "The two sources named different aircraft, so nothing was shown "
     "that cycle — the display kept the previous image instead."),
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
# 20-03-PLAN.md Task 3 (D-05): a %s-templated constant rather than the
# already-formatted sentence this used to be — the render site below
# translates the TEMPLATE through i18n.t() first, then substitutes the
# provider hostnames (identifiers, never translated, per D-05). The
# fully-formatted English sentence is kept as SOURCE_FAULT_BODY for any
# reader that still wants the plain English value.
SOURCE_FAULT_BODY_TEMPLATE = (
    "The frame's alert badge is showing because every configured ADS-B "
    "source (%s) failed to respond on the most recent pipeline run — "
    "this is a data-source outage, not a device problem.")
SOURCE_FAULT_BODY = SOURCE_FAULT_BODY_TEMPLATE % ", ".join(_ADSB_PROVIDER_NAMES)

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
# 19-06-PLAN.md Task 2 (D-06): the visible label read in plain language
# a household member can parse without hovering; the technical term
# stays available one hover away via `caption_title` at the tile's
# stat_tile() call site below.
PIPELINE_FRESHNESS_LABEL = "Flight data last updated"
PIPELINE_FRESHNESS_TITLE = "ADS-B pipeline last ran"

# 19-06-PLAN.md Task 2 (D-06): replaces the literal "Corroboration"
# string that used to be inlined straight at this tile's stat_tile()
# call site — this module's own convention is constants at the top,
# never literals at a render site. The technical term survives as this
# tile's `caption_title` tooltip.
CORROBORATION_TILE_LABEL = "Do the two data sources agree?"
CORROBORATION_TILE_TITLE = "Corroboration"

# Quick task 260903-peo (UIR-14): the pipeline tile's new second content
# line, naming the last real aircraft detection sourced from
# history_db.META_LAST_DETECTION.
LAST_DETECTION_LABEL = "Last aircraft detected"

# 22-03-PLAN.md Task 1 (B2): the pipeline-never-ran detail sentence —
# evidence only ("since it started"), never the state name, so it is
# safe to publish verdict-free as compute_health_state()'s
# "pipeline_detail_html" key (see _pipeline_timestamp_only()). Chosen
# deliberately over concise_timestamp_html(None, now)'s own "no reading
# yet" fallback, which is the battery module's borrowed vocabulary B2
# is removing from this tile.
PIPELINE_NEVER_RAN_DETAIL_TEXT = "The frame has not reported a flight since it started."

# D-03/A-21, 19-01-PLAN.md: a short plain-sentence verdict for each stat
# tile whose caption names a signal but whose border colour alone was the
# only place the actual verdict lived (WCAG 1.4.1 — colour must never be
# the sole means of conveying information). Modelled one-for-one on
# home_page.py's FRAME_STATE_TEXT/DATA_STATE_TEXT/BATTERY_STATE_TEXT: a
# dict keyed by the same "ok"/"warn"/"error" state each section builder
# already computes, rendered as a '<p class="text-body widget-verdict">'
# paragraph ahead of the tile's existing timestamp row. The Resolution-
# rate tile deliberately has no sibling dict here — see render()'s own
# comment at that tile's stat_tile() call for why.
DEVICE_STATE_TEXT = {
    "ok": "Checking in normally",
    "warn": "Has not checked in for a while",
    "error": "Has not checked in for a long time",
    # 22-04-PLAN.md Task 3 (D-03/CFG-26, X2): DEVICE_STATE_TEXT WIDENS
    # here, unlike 22-03-PLAN.md Task 1's deliberate choice not to widen
    # it for the pipeline's own never-ran distinction — this is a
    # DIFFERENT, genuine fourth device state (a frame the strip/tile
    # both know is quiet-hours-held, never merely "hasn't checked in for
    # a while"), and reuses the SAME "off" token the pipeline's never-ran
    # state and the strip's held dot both already use: "a neutral,
    # everyday state ... never a problem" (companion/static/style.css's
    # own comment on .dot--off). A held frame is never rendered through
    # this key alone — _device_section() below routes it here only when
    # frame_state.resolve_state() itself says STATE_HELD.
    "off": "Asleep for quiet hours",
}

# 22-04-PLAN.md Task 3 (D-03/CFG-26): the ONE mapping from
# frame_state's own three real states to this tile's device_state
# vocabulary — due maps to "ok", held to the neutral "off" (never
# "warn"/"error", so it can never light the nav dot), late to "warn"
# (frame_state has no fourth, "very late" tier any more; see
# _device_section()'s own docstring). `STATE_UNKNOWN` is deliberately
# absent — `_device_section()` never looks this dict up for that state,
# it falls back to the pre-existing age-based `staleness_status()` path
# instead.
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
REFRESH_PILL_TEXT = layout.REFRESH_PILL_TEXT

# 23-05-PLAN.md Task 2 (D22's remainder): the hook
# companion/static/freshness.js toggles its breathing class on.
# Duplicated rather than imported — freshness.js is a static asset, not
# a Python module — matching the BATTERY_READOUT_ID/SPARKLINE_HIT_CLASS
# cross-file contract below and REFRESH_SWAP_SELECTORS' own.
REFRESH_LIVE_DOT_ATTR = layout.REFRESH_LIVE_DOT_ATTR

# 19-09-PLAN.md (D-02, A-20): SUPERSEDED — PERSISTENT_FRESHNESS_PREFIX_TEXT
# used to read "Live — refreshed ", prefixing a
# concise_timestamp_html(now, now) timestamp. That timestamp's own
# relative-age suffix ("(0s ago)") was structurally always zero: `now`
# is computed exactly once per request by page_context() and immediately
# fed back into the very timestamp claiming to be "(Ns ago)" of itself —
# so the line asserted a liveness the render-time mechanism never
# actually measured. FRESHNESS_PREFIX_TEXT below replaces it with a
# plain, honest label; the value the line now shows is a clock-only
# rendering with no relative-age suffix at all (see freshness_html's own
# assembly in render()), and the line only ever advances again because
# companion/static/freshness.js re-renders the whole freshness wrapper
# from a fresh fetch — never a client-side clock tick.
FRESHNESS_PREFIX_TEXT = layout.FRESHNESS_PREFIX_TEXT

# 21-02-PLAN.md (D-18): the Pause/Resume control that used to live here
# is deleted — the freshness loop in companion/static/freshness.js now
# always runs, unconditionally, with no client-side pause state to label.

# 19-09-PLAN.md (D-02): the DOM regions companion/static/freshness.js
# swaps wholesale on this page, replacing each node with its own
# equivalent from a fetched copy of this same page.
#
# 23-06-PLAN.md Task 1 (D1/CFG-35): MOVED, not copied. The tuple that
# stood here is now one entry in companion/layout.py's own
# REFRESH_SWAP_SELECTORS_BY_PAGE — the per-page registry Home and the
# Display scope join — and this name resolves FROM it. The name survives
# because every existing reader and every shipped pin uses it; the
# second definition site does not, because three hand-kept tuples is the
# shape scope_groups()'s SCOPE_ALL already taught this codebase not to
# build. Every word of the reasoning that lived here — the per-entry
# comments, the deliberate exclusions, and why the whole nav link rather
# than a dot is the severity target — moved WITH the tuple and is in
# layout.py beside it, unabridged.
REFRESH_SWAP_SELECTORS = layout.REFRESH_SWAP_SELECTORS_BY_PAGE[
    layout.REFRESH_PAGE_HEALTH]

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
# 24-05-PLAN.md Task 1 (CFG-41/CFG-45): the area under the trend line,
# in two classes because it is two elements — a nested <svg> LAYER that
# owns the coordinate system, and the filled <polygon> inside it.
# `sparkline__area` follows this chart's BEM-ish element convention
# (`sparkline__canvas`, `sparkline__y`, `sparkline__x`) because it is a
# structural part of the drawing; `sparkline-area` follows the shape
# convention (`sparkline-line`, `sparkline-dot`, `sparkline-axis`)
# because it is ink. Neither name is a substring of the other, or of any
# class above — several harness checks count a class's occurrences with
# a plain `str.count()`, and `sparkline-dot--mark` (say) would have been
# counted as a `sparkline-dot`.
SPARKLINE_AREA_LAYER_CLASS = "sparkline__area"
SPARKLINE_AREA_CLASS = "sparkline-area"
# 24-05-PLAN.md Task 2 (CFG-41): the marked current reading, the drawn
# low-battery threshold, and the threshold's own legend. Same two
# conventions as above (`__` for a structural part of the grid, `-` for
# ink), and again no name is a substring of another — `sparkline-swatch`
# rather than `sparkline-legend__swatch` for exactly that reason.
#
# SPARKLINE_MARK_CLASS is NOT a modifier on SPARKLINE_DOT_CLASS, and that
# is the density rule's exception expressed as a class name: above
# `_SPARKLINE_DENSE_POINT_THRESHOLD` the cosmetic dots stop being
# emitted, and the mark must not stop with them — marking the current
# reading is the whole reason it is drawn. A `sparkline-dot
# sparkline-mark` pair would have made "suppress the dots" and "keep the
# mark" the same instruction.
SPARKLINE_MARK_CLASS = "sparkline-mark"
SPARKLINE_THRESHOLD_CLASS = "sparkline-threshold"
SPARKLINE_LEGEND_ROW_CLASS = "sparkline__legend"
SPARKLINE_LEGEND_CLASS = "sparkline-legend"
SPARKLINE_LEGEND_SWATCH_CLASS = "sparkline-swatch"
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
# 29-06-PLAN.md (CFG-84): BATTERY_SECTION_HEADING (a fixed "Battery
# trend" literal) is SUPERSEDED by this template — the 2026-09-17
# audit's P2 asked for the heading's own precision ("3 derniers mois,
# moyenne quotidienne") to move into a sibling caption, leaving the
# heading itself a short, fixed "Battery · N months" naming only the
# real window BATTERY_TREND_WINDOW_DAYS already governs. "%d" is
# interpolated with BATTERY_TREND_WINDOW_DAYS // 30 at every call
# site — never a typed "3" — so the heading cannot silently drift from
# the window the chart is actually plotting. The U+00B7 middle dot
# matches this codebase's real-Unicode punctuation convention (the en
# dash in the preset ranges is the existing precedent); translate the
# template, then substitute — this codebase's established order.
BATTERY_SECTION_HEADING_TEMPLATE = "Battery · %d months"
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

# --- 24-07-PLAN.md Task 2 (CFG-43): the check-in regularity grid -------
#
# THE NAME IS THE FIRST DECISION AND IT IS NOT A STYLE CHOICE.
# .planning/ROADMAP.md asked for a grid of how reliably the frame kept
# its wakes — naming it with a word this codebase now refuses — and flagged
# that the data might not support it. 24-03 settled that it does not:
# `device_health` rows are real check-ins, so the OBSERVED cadence is
# measurable, but the interval the device was EXPECTED to keep is nowhere
# in history — it is not even a constant (wake.effective_wake_interval_s()
# switches to DISPLAY_OFF_SLEEP_S whenever the screen is off, and quiet
# hours hold the frame on top of that), and a log range
# history_db.ingest_caddy_battery_log() missed leaves a hole
# indistinguishable from a device that did not wake. No schema change
# recovers any of it.
#
# So this section reports what IS observable — the regularity of the
# record of check-ins — and says in its own caption what it is not
# claiming. Every verdict comes from wake.classify_check_in_gap(), which
# derives from the same wake.device_staleness_thresholds() the Frame tile
# consumes, so this grid and that tile can never disagree about "late".
# Nothing here computes an interval, a threshold or a duration boundary.
CHECK_IN_SECTION_HEADING = "Check-in regularity"

# One cell per Europe/Paris calendar day. 30 is this page's existing
# "a month" window (RESOLUTION_WINDOW_DAYS above uses the same number for
# the same reason), and it is inside draw.regularity_grid()'s own bound:
# ten columns at the measured 278px card width by six rows is 60 cells,
# so the window can never be the thing the drawing truncates. If it ever
# grows past that, the emitter reports the overflow and the scale labels
# below stop being able to name the window honestly — which is why this
# constant and that bound are checked against each other rather than
# merely chosen to agree.
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

# THE CAPTION'S THREE CLAUSES, one constant each, because they are three
# separate claims and each is asserted by its own named check.
#
# 29-06-PLAN.md Task 2 (CFG-79): these four/five clauses used to be
# joined with " ".join(...) into ONE visible paragraph (roughly fifty
# words at their longest combination). Only CHECK_IN_CAPTION_OBSERVED
# still renders in the card's own visible <p class="text-label
# section-caption"> now; every other clause below MOVES, byte-
# identical in wording, into a `<details class="readings-disclosure">`
# immediately after it (see `_check_in_regularity_section_html()`).
# Moved, never cut: each clause's own comment below is extended to say
# so, and a dedicated check in test_status_pages.py asserts every
# clause that rendered before this plan still renders somewhere in the
# card, across all four observed/cadence-known combinations.
#
# 1. What the grid shows. Stays visible — this is the one clause short
#    enough (11 words) to carry alone as the card's own one-sentence
#    caption; no shortening needed.
CHECK_IN_CAPTION_OBSERVED = (
    "Each cell is one day of observed check-in regularity, oldest first.")
# 2. What it was judged against — and that this is TODAY'S cadence. The
#    cadence actually in force on an earlier day is not recoverable
#    (device_config.json is a current-state file), so naming it without
#    this qualifier would be a claim about the past made from a value
#    read in the present.
#
#    29-06-PLAN.md Task 2 (CFG-79): MOVED into the disclosure, not
#    shortened and not paraphrased. The "not necessarily the cadence in
#    force on an earlier day" qualifier is what stops this caption
#    making a claim about the past from a present-tense config file;
#    moving it one tap away costs nothing, because it still renders on
#    every request, in the same words, in the same document — it is
#    simply no longer the FIRST thing a reader sees.
CHECK_IN_CAPTION_CADENCE = (
    "Judged against the cadence configured now — a check-in every %s — not "
    "necessarily the cadence in force on an earlier day.")
# 2b. And when there is no cadence to name at all: a deployment with no
#     wake_interval_s and no SKYPANE_SLEEP_S gets
#     device_staleness_thresholds()' bare floors, and the caption has to
#     say THAT rather than silently print an assumed default.
#
#     29-06-PLAN.md Task 2 (CFG-79): MOVED into the disclosure alongside
#     CHECK_IN_CAPTION_CADENCE above, same reasoning, same guarantee
#     (still renders every request, unshortened).
CHECK_IN_CAPTION_CADENCE_FALLBACK = (
    "This frame's cadence cannot be determined, so the grid is judged against "
    "the fallback staleness floors rather than against a configured cadence.")
# 3. What a gap is NOT. KEEP THIS CLAUSE. It is the one a later editor
#    will trim as noise, and it is the difference between reporting an
#    observation and accusing the device: the record cannot tell a wake
#    the frame missed from a log range this server lost, so a grid
#    without this sentence is a picture making a claim its own data
#    cannot support (T-24-07-A).
#
#    29-06-PLAN.md Task 2 (CFG-79) moved this clause into the card's own
#    `<details class="readings-disclosure">`, one tap away from the
#    visible caption — this is NOT a weakening of the KEEP THIS CLAUSE
#    instruction above. The clause is byte-identical, still renders on
#    every request, still lives in the same document; only its
#    position moved, from the always-visible caption to a disclosure
#    that opens with one tap. A dedicated four-case check in
#    test_status_pages.py proves this sentence still renders somewhere
#    in the card for every observed/cadence-known combination — "moved,
#    not cut" is therefore an executable claim, not a promise.
CHECK_IN_CAPTION_NOT_PROOF = (
    "A day with no record is not proof the frame did not wake: a log rotation "
    "this server missed leaves exactly the same gap.")
# The empty deployment. A real case, and it renders as an honest grid of
# no-observation cells rather than as a missing section.
#
# 29-06-PLAN.md Task 2 (CFG-79): MOVED into the disclosure, same
# reasoning as CHECK_IN_CAPTION_CADENCE above.
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

# --- 06.6.4.1-04 (D-10): the two id-anchored sections Health's body is
# now split into. SERVER_DATA_SECTION_ID is a cross-page coupling:
# companion/pages/history_page.py links to this exact anchor (#server-data)
# for D-21 — renaming it silently breaks that link. This is the one
# cross-page coupling this phase introduces.
SCREEN_SECTION_ID = "screen"
SCREEN_SECTION_HEADING = "Screen"
SERVER_DATA_SECTION_ID = "server-data"
SERVER_DATA_SECTION_HEADING = "Server & data"
# 19-06-PLAN.md Task 2 (D-06): plain-language label; the technical term
# stays reachable via `caption_title` at this tile's stat_tile() call
# site below.
RESOLUTION_RATE_LABEL = "Flights we could name"
RESOLUTION_RATE_TITLE = "Route resolution rate"
# 19-06-PLAN.md Task 3: renamed into the same plain-language register —
# constant NAMEs are unchanged so no unrelated reference breaks.
UNRESOLVED_SECTION_HEADING = "Airlines we could not name"
STATS_SECTION_HEADING = "How well we name flights"

# --- quick task 260901-tsa: page-purpose + section-intro copy ----------
#
# Verbatim from the validated "Merged Health Sketch" — this is the
# sketch's own wording, restating the split D-10 already made (the
# physical frame versus the ADS-B/route-resolution pipeline) in the
# reader's own terms rather than making any new claim. Keep the leading
# em-dash and the space after it on both descriptions: that is what
# makes the heading and its description read as one continuous phrase
# across the baseline-aligned `.section-intro` row (see
# `layout.section_intro_html()`, promoted from this module's own former
# private copy by 20-03-PLAN.md Task 1), and it is the validated copy —
# do not drop it as "redundant punctuation".
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

# 19-06-PLAN.md Task 3 (D-06): no "prefix"/"ICAO"/"registry" in either
# plain sentence below — the technical vocabulary for what this card
# actually tracks (an unresolved ICAO callsign prefix registry, CFG-04)
# is demoted to this comment, not deleted; the visible copy just says
# what a household member sees: some airlines we could not name yet.
_NO_GAPS_HEADING = "No coverage gaps."
_NO_GAPS_BODY = (
    "Every airline we've seen recently has been named — nothing left to look up.")

# Phase 13 (D-10) reworded this note in place: it now names Airlines as
# the resolution surface and points at the per-row Resolve link Task 2
# below adds, instead of the old manual runbook. This does NOT reopen
# 06.6.4.1-04's D-11/D-12 — the registry here is still read-only; the
# state-changing form lives on Airlines, not here.
#
# 19-06-PLAN.md Task 3 (D-06): "that prefix's airline" reworded to
# "that airline" — no "prefix" in the visible sentence.
#
# 29-06-PLAN.md Task 2 (CFG-79): SHORTENED to one sentence (25 words ->
# 5) naming only what the list IS. The genuine reference material this
# note used to carry — WHERE resolution happens and what it does — is
# not deleted; it moves, unchanged in wording, into
# _READ_ONLY_NOTE_DETAIL below, rendered in a new `<details
# class="readings-disclosure">` immediately after this visible
# sentence (see `_registry_section()`).
_READ_ONLY_NOTE = "This list is read-only here."
_READ_ONLY_NOTE_DETAIL = (
    "Each row's Resolve link opens the Airlines page to name that airline "
    "(and add artwork, if it needs one).")

# 22-03-PLAN.md Task 2 (B3): replaces the former "No resolution data
# yet." / "No flight events recorded yet — resolution statistics
# appear once the ADS-B pipeline has detected a flight." pair, which
# never named the window this figure is actually scoped to. The
# heading is a %-template (kept unformatted here, exactly like
# `_FILTER_EMPTY_BODY_TEMPLATE` above) interpolated with
# RESOLUTION_WINDOW_DAYS at the one call site below — never a literal
# "30" in the string, so a future change to the window constant cannot
# silently leave stale copy behind.
_NO_STATS_HEADING = "No flights in the last %d days"
_NO_STATS_BODY = (
    "The frame has not recorded a detection in this window. It will "
    "appear here after the next wake.")

# 22-12-PLAN.md Task 1 (D-06/B16, CFG-29): the Resolution-rate tile's
# detail line, and the LAST plural on this page that had no singular
# form — a window holding exactly one detection read "over the last 30
# days, 1 events". Follows the shape 22-10 and 22-11 already established
# for the Calendar and Airlines plurals: a `..._SINGULAR_TEMPLATE`
# sibling constant, each with its OWN French catalogue entry, chosen at
# the call site — never a runtime "add an s" rule, which cannot be
# translated (French pluralises the noun AND would need the article
# agreed, and companion/test_i18n.py's completeness scan can only see
# whole literals).
#
# Only the EVENT count varies: the day count is RESOLUTION_WINDOW_DAYS,
# a module constant of 30, so a "1 day" form would be dead copy. Both
# templates therefore keep both placeholders in the same order, and the
# window clause is identical between them.
_RESOLUTION_DETAIL_TEMPLATE = "over the last %d days, %d events"
_RESOLUTION_DETAIL_SINGULAR_TEMPLATE = "over the last %d days, %d event"

RESOLUTION_WINDOW_DAYS = 30  # A month is long enough to smooth over a
# quiet week at this single-airport traffic volume, while still reading
# as "recent" for a resolution-rate figure.

# The four categories server/plane/enrich.py's resolve_route() documents,
# plus a fifth added by phase 13 (D-02), in a fixed display order, with a
# plain-English gloss for each so this page is readable without the
# source code (D-05/quick-task 260827-hyy). This is NOT a closed
# four-way enumeration any more — "airline_only" still means the STATIC
# prefix table answered (server/plane/enrich.py's resolve_route()), while
# "manual" (phase 13, D-02) is a distinct fifth value meaning the
# operator answered it by hand, at runtime, from this companion web
# interface. D-02 deliberately refused to fold the two together: one
# reflects a maintained static table shipped with the code, the other
# reflects an ad hoc runtime registry a human curates — collapsing them
# would hide which of the two actually did the work.
# 19-06-PLAN.md Task 3 (D-06): every "adsbdb" occurrence below is now
# "the route database" in visible prose — the developer-facing name
# survives as a source comment (this one), not in rendered text. The
# live/cache/static-table distinction between "fresh_hit"/"cache_hit"/
# "airline_only" is deliberately kept (collapsing it would hide which
# mechanism actually resolved the route, per the module comment above),
# just phrased in ordinary words. The "miss" gloss no longer says
# "CFG-04's registry" (no requirement id may appear in visible text) —
# it names the on-screen card by its own current heading instead, so a
# reader can find it without knowing the requirement id.
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

# 22-03-PLAN.md Task 2 (B3): a sixth, catch-all row for any route_source
# value outside the five above (NULL, empty, or something this page does
# not recognise) — `resolution_stats()` folds every such row in here
# instead of silently dropping it from the total, per this module's own
# rule (stated in the comment above _SOURCE_ROWS) against a
# developer-facing identifier in visible text. Kept OUT of _SOURCE_ROWS
# itself: that tuple is this page's fixed, ordered enumeration of known
# mechanisms, and folding an "unknown" bucket into it would misrepresent
# it as a sixth mechanism this page actually understands.
_OTHER_SOURCE_LABEL = "Other"
_OTHER_SOURCE_GLOSS = (
    "A route source this page does not recognise, or none was recorded "
    "at all — still counted here so the total always matches every "
    "event in the window.")

# quick task 260903-ghy (UIR-10): promoted from a literal inline the
# Resolution-statistics table's own `layout.data_table()` call used to
# carry — single-sourced so `_stats_table_html()`'s table and
# `_stats_cards_html()`'s mobile card list can never disagree on a header
# word. Index 2 ("Count") is read directly by the card builder for its
# field label; the middle header ("Description") has no card-side
# equivalent, since the mobile card renders the full description as
# stacked prose rather than a labelled field.
_STATS_HEADERS = ("Source", "Description", "Count")

# D-20: the filter bar's copy (06.6.3-UI-SPEC.md's Copywriting Contract),
# driven client-side by companion/static/list-filter.js's shared
# [data-filter-input]/[data-filter-count]/[data-filter-clear]/
# [data-filter-empty] attribute contract. This is Health's OWN
# unresolved-prefix registry filter (see `_FILTER_LABEL_TEXT` and
# `_FILTER_EMPTY_HEADING` below), not the Compagnies gallery's — the
# `airlines` prefix on this id is kept deliberately even though the two
# values now differ (quick task 260921-p2w Task 1 renamed each site
# independently): D-12 says the registry card's content and behaviour
# are unchanged by this move, so this constant's scope stays
# `airlines`-prefixed, and list-filter.js keys on the data-filter-*
# attributes, not on the element's id string, so the prefix choice
# reaches no client code either way.
#
# Quick task 260921-p2w Task 1: hyphen removed from this value — see
# history_page.py's own `_FILTER_INPUT_ID` comment for the full WebKit/
# Safari contacts-autofill explanation.
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


def offbox_backup_status(now):
    """The off-box backup freshness signal (SEC-04, D-07/D-23), read from
    `os.environ` (see this function's own body) on EVERY call — never
    resolved once and cached at import time, so a deployment that sets
    the env var after this module has already been imported (or a test
    that changes
    it between two calls) is still seen.

    Returns `None` when the env var is unset or empty — D-07's "no new
    page for a deployment that has not configured this yet" contract: the
    caller renders no card and folds no state into severity at all in
    that case (`compute_health_state()`'s own "ok" default for a `None`
    result — see its docstring).

    Otherwise returns `{"state": "ok"|"warn", "snapshot_ts": <ISO str or
    None>}`. `state` is capped at "warn" (D-23: the file gate went
    dark, not the flight-data pipeline) by passing `error_s=float("inf")`
    to `staleness_status()` above — an error_s that can never be reached.

    Never raises (T-37-07): a missing file, a path-traversal-shaped
    name, empty content, binary garbage or a file far larger than any
    real marker is a T-37-06 tampering surface, not a crash surface — any
    `OSError`/`ValueError` (the parent of `UnicodeDecodeError`) reading or
    parsing the marker degrades to `{"state": "warn", "snapshot_ts":
    None}`, the same shape as "never pulled". At most 256 bytes are ever
    read, so a 10 kB file costs one bounded read, not a full-file load.
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
    first (matches `history_db.recent_device_health()`'s own ordering).

    D-13 keeps this table's history forever — this function's LIMIT is a
    *display* choice for readability, not a retention policy; nothing is
    ever deleted here or anywhere else in this page.
    """
    return history_db.recent_device_health(conn, limit=BATTERY_TREND_LIMIT)


def battery_daily_rows(conn, now):
    """(260902-l0b; Paris days as of 22-06-PLAN.md Task 1) The chart's
    primary series: one point per Europe/Paris calendar day over the last
    `BATTERY_TREND_WINDOW_DAYS` (3 months), via
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
    """(260902-l0b; Paris days as of 22-06-PLAN.md Task 1) True when there
    are at least two Europe/Paris-day buckets to plot as a trend —
    `battery_sparkline_svg()`'s own two-point minimum
    for a line, kept in exactly one place (not duplicated in
    `_battery_section()` and `_battery_trend_caption()` separately) so the
    chart's series choice and the heading caption can never disagree
    about which series is actually on screen. `daily_rows` may be the
    `_DB_UNAVAILABLE` sentinel (a failed read is never "usable").
    """
    return isinstance(daily_rows, list) and len(daily_rows) >= 2


def _real_trend_reading_count(trend_rows):
    """(22-06-PLAN.md Task 2, B4) The number of `trend_rows`
    `battery_sparkline_svg()` will actually plot — a row with a missing
    or non-numeric `battery_mv` is silently dropped there (the same
    numeric-only filter, repeated here rather than shared, since this
    module already applies it independently in two other places:
    `battery_status()` and the plotting loop itself). `BATTERY_TREND_LIMIT`
    is a query LIMIT, not a guarantee that many rows exist — a fresh
    deployment with only 3 readings must not have its caption claim
    `BATTERY_TREND_LIMIT` (e.g. 20) readings when only 3 are on screen.
    """
    return sum(
        1 for row in trend_rows
        if isinstance(row.get("battery_mv"), int) and not isinstance(row.get("battery_mv"), bool))


def _battery_trend_caption(trend_rows, daily_rows):
    """(260902-l0b) The heading caption text (without its leading em
    dash), honest about which series is actually on screen — computed
    from the same `_battery_daily_series_usable()` predicate
    `_battery_section()` uses to choose what to plot, so the two can
    never disagree.

    Three cases, not two: the 90-day daily series is plotted (>= 2 Paris-
    day buckets) — the 3-month/daily-average framing; no readings exist at
    all (or the read failed) — the SAME 3-month framing, because that is
    what this page will show once data exists and there is no chart of
    any kind on screen to be honest ABOUT; otherwise a real fallback
    chart is on screen, built from fewer than two calendar days of raw
    readings — "Latest %d readings", where %d is the REAL count
    `_real_trend_reading_count()` computes (22-06-PLAN.md Task 2, B4),
    never the `BATTERY_TREND_LIMIT` constant this used to name regardless
    of how many readings actually exist.
    """
    if _battery_daily_series_usable(daily_rows):
        return i18n.t("Last 3 months, daily average")
    if not trend_rows or trend_rows is _DB_UNAVAILABLE:
        return i18n.t("Last 3 months, daily average")
    return i18n.t("Latest %d readings") % _real_trend_reading_count(trend_rows)


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

# D-04 (A-22), 19-05-PLAN.md: the sparkline's Y-axis is now a FIXED range
# — 3000-4200 mV, never an auto-scaled `min(values)`/`max(values)`
# window. Before this task, a flat battery series pinned to the bottom
# of the canvas (min == max, since nothing else was on screen to compare
# it against) and a real but tiny 15mV wiggle stretched to fill the
# WHOLE vertical range, reading as a cliff rather than the noise it
# actually was. A fixed range fixes both: a flat series now draws flat,
# and a small wiggle now draws small. 19-05's reasons for fixing the
# range still hold.
#
# SEED-006 (quick 260923-gaf) changed what the two no longer agree BY
# CONSTRUCTION on. The percentage printed beside this chart now comes
# from `companion/battery.py`'s BATTERY_DISCHARGE_CURVE, the DEVICE-05
# piecewise curve spanning 2946-4112 mV — flat near the top, steep near
# the bottom — while this axis stays a straight 3000-4200 mV DISPLAY
# window. Equal vertical distances on this chart are therefore NOT equal
# percentages any more: a step near the top of the canvas covers far
# more percent than the same step near the bottom. A reading below
# 3000 mV, which happens only in the final hours of a discharge, clamps
# to the chart floor rather than drawing off-canvas.
SPARKLINE_Y_MIN_MV = 3000
SPARKLINE_Y_MAX_MV = 4200
_SPARKLINE_Y_SPAN_MV = SPARKLINE_Y_MAX_MV - SPARKLINE_Y_MIN_MV  # no `or 1`
# guard needed here (unlike the retired `span = (hi - lo) or 1`): this is
# now a fixed, always-nonzero constant, never a per-render min/max that
# could collide to zero for a flat series.

# 260902-l0b: the cosmetic marker's and the normal hit target's radii,
# named (they were literals — `r="3"`/`r="8"` — inside the point loop
# before this task) so the density rule below can reference them instead
# of restating the numbers.
_SPARKLINE_DOT_RADIUS_PX = 3
_SPARKLINE_HIT_RADIUS_PX = 8

# 24-05-PLAN.md Task 2 (CFG-41): the marked current reading's own radius.
# Bounded from both sides rather than chosen: it must be strictly larger
# than `_SPARKLINE_DOT_RADIUS_PX` or the mark does not read as a mark,
# and no larger than the canvas's vertical inset in CSS pixels
# (`_SPARKLINE_VERTICAL_INSET_PERCENT` of `_SPARKLINE_CANVAS_HEIGHT_PX`
# = 6px) or a mark on a full or flat-empty battery would be clipped at
# the canvas edge — the same reasoning that derived the inset against the
# 3px dot in the first place. 5 sits inside both bounds with a pixel to
# spare; re-derive it if either the inset or the canvas height changes.
# A harness check asserts both bounds rather than the value.
_SPARKLINE_MARK_RADIUS_PX = 5

# The point count at which the 90-day daily chart's cosmetic dots stop
# reading as separate marks and start reading as a continuous caterpillar
# — a different visual language from the thin line the developer asked
# to keep. Derived twice, and the second derivation corrects the first:
#
# Planning-time estimate (293px): this file's own `.battery-trend-section
# svg:not(.icon)` comment in style.css already measured and cited "375px
# viewport -> 293px (the narrowest real container)" — but that number is
# the whole `.sparkline` GRID's content width (both columns), not the
# canvas alone, and was used here as if it were the canvas.
#
# Live-measured correction (226px), from a real Chrome instance against
# `companion/app.py` at a 375px viewport with a realistic 90-day dataset
# seeded: `.sparkline__canvas`'s own `getBoundingClientRect().width` was
# 226px, not 293px — `.sparkline__y`'s auto-sized Y-axis label column
# (43.8px, for this project's realistic 4-digit "NNNN mV" labels — a
# LiPo battery's whole usable range, ~3000-4200mV, is always 4 digits)
# plus its `column-gap` (`--space-sm`, 8px) claims the other ~52px of
# that 278px grid. The planning-time estimate ignored this because the
# label column's real width is browser-measured and was assumed
# unknowable from CSS alone — true in general, but a live measurement
# resolves it for one real, cited data point, and this task's own human-
# verification pass is exactly what surfaced the gap between the
# estimate and reality.
_SPARKLINE_NARROWEST_CANVAS_PX = 226  # the live-measured figure above —
# the narrowest canvas width this project has ever actually measured.


def _sparkline_dense_threshold(canvas_width_px):
    """(D-04, 19-05-PLAN.md) The first integer point count at which
    `_point_x()`'s evenly-spread points sit closer together than the
    cosmetic dot's own diameter, for a canvas rendered at
    `canvas_width_px` CSS pixels wide.

    `_point_x()` spreads `point_count` points evenly across the canvas's
    full width, so consecutive points sit
    `canvas_width_px / (point_count - 1)` CSS pixels apart. They stop
    reading as separate marks once that gap drops below the cosmetic
    dot's own diameter (`2 * _SPARKLINE_DOT_RADIUS_PX`):
    `canvas_width_px / (point_count - 1) < 2 * _SPARKLINE_DOT_RADIUS_PX`
    => `point_count > canvas_width_px / (2 * _SPARKLINE_DOT_RADIUS_PX) +
    1`, and this function returns the first integer above that bound.

    This promotes into code the exact points-per-pixel arithmetic the
    retired `_SPARKLINE_DENSE_POINT_THRESHOLD = 39` typed constant used
    to compute once, by hand, for one measured width — expressed this
    way, the rule re-derives itself automatically if the dot radius or
    the measured canvas width below ever changes, instead of silently
    rotting as a magic integer nobody re-checks.

    Honest limitation, not solved here: `battery_sparkline_svg()`'s
    `<svg>` carries no viewBox (see that function's own docstring for
    why), so the server genuinely cannot know a particular client's
    actual rendered canvas width. `_SPARKLINE_DENSE_POINT_THRESHOLD`
    below always calls this with `_SPARKLINE_NARROWEST_CANVAS_PX`, the
    narrowest canvas width this project has ever measured, so dots never
    overlap at any container width this project has actually observed —
    a deliberately conservative choice, not a guarantee for some
    unmeasured, still-narrower container.
    """
    spacing_ceiling_px = 2 * _SPARKLINE_DOT_RADIUS_PX
    return int(canvas_width_px / spacing_ceiling_px + 1) + 1


# Re-derive this figure (from a real running instance, not from memory)
# if the canvas's own measured width, the realistic Y-label digit count,
# or the cosmetic dot radius above ever changes.
_SPARKLINE_DENSE_POINT_THRESHOLD = _sparkline_dense_threshold(_SPARKLINE_NARROWEST_CANVAS_PX)

# The reduced hit-target radius used at/above the density threshold —
# smaller than the normal 8px so heavily overlapping hit circles no
# longer nearly-fully overlap, though every point stays reachable (the
# roving-tabindex/arrow-key keyboard path below is entirely unaffected;
# only the pointer/touch hit area shrinks). The honest trade: this costs
# tap-target size and buys pointing precision among ~50+ closely-spaced
# points — real only on a real device, hence this task's own
# human-verification list.
_SPARKLINE_DENSE_HIT_RADIUS_PX = 4


def sparkline_point_y(value):
    """The y position `value` gets on the battery chart, as a percentage
    of the canvas height.

    24-05-PLAN.md Task 1 PROMOTED this out of `battery_sparkline_svg()`'s
    own local closure, unchanged in behaviour, for one reason: the chart
    now draws things that are not readings — an area baseline and a
    low-battery threshold — and every one of them must be placed by the
    SAME function the readings are, or it will sit at a different level
    from the readings it is drawn to be compared against. A threshold
    with its own arithmetic drifts from the plotted line by exactly the
    vertical inset, which is the class of defect this promotion makes
    unavailable rather than merely unlikely. It is also what lets
    companion/test_status_pages.py compute the expected position from
    the same function rather than hard-coding a number.

    D-04 (A-22): every value is clamped into the fixed
    [SPARKLINE_Y_MIN_MV, SPARKLINE_Y_MAX_MV] range before its y position
    is computed, so an out-of-range reading draws pinned at the canvas
    edge rather than escaping it or silently rescaling the axis (there is
    no axis left to rescale — the range is a constant, not derived from
    `value` at all). `_SPARKLINE_VERTICAL_INSET_PERCENT` on both top and
    bottom keeps every marker's radius fully inside the canvas (see that
    constant's own derivation above); the y-axis is inverted (higher mV
    -> smaller y%) to match SVG's top-down coordinate direction.
    """
    inset = _SPARKLINE_VERTICAL_INSET_PERCENT
    clamped = max(SPARKLINE_Y_MIN_MV, min(SPARKLINE_Y_MAX_MV, value))
    return inset + (
        1 - (clamped - SPARKLINE_Y_MIN_MV) / _SPARKLINE_Y_SPAN_MV
    ) * (100 - 2 * inset)


# Phase 21 polish: the hover/tap readout's own text, as constants so the
# French catalogue (companion/i18n_fr/health.py) carries them.
BATTERY_AVERAGE_WHEN_ONE_TEMPLATE = "%s — daily average (%d reading)"
BATTERY_AVERAGE_WHEN_MANY_TEMPLATE = "%s — daily average (%d readings)"
BATTERY_AVERAGE_WHEN_BARE_TEMPLATE = "%s — daily average"

# 24-05-PLAN.md Task 2 (CFG-41, T-24-05-B): the drawn low-battery
# threshold's own label. It names what the line MEANS and only then what
# it is worth — a bare millivolt number floating on a chart says nothing
# about why that level is drawn, and this line is a judgement about the
# device, not a second axis tick.
#
# It prints the percentage beside the level on purpose: the level IS the
# millivolt reading at which `companion/battery.py`'s estimate returns
# that percentage (see LOW_BATTERY_DISPLAY_MV's own derivation), so the
# label ties the drawn line to the "≈ NN%" the readout and the ring
# already print above the chart, instead of introducing a number the rest
# of the section never mentions.
BATTERY_THRESHOLD_LABEL_TEMPLATE = "Low battery — %d mV (≈ %d%%)"

# Phase 21 polish: the chart's month abbreviation now comes from
# layout.month_abbr() — the same fixed, locale-independent tables
# local_clock_text() uses (English or French by the request's
# language), replacing this module's former private English-only table
# (260902-l0b) that 20-03-PLAN.md Task 2 had left out of D-07's scope.

# 22-06-PLAN.md Task 2 (D-05, B4), PROMOTED to companion/layout.py by
# 23-06-PLAN.md Task 2: the sentinel and the helper both live there now,
# because the freshness line this page shared with Home and the Display
# scope needs the same full local timestamp and a page module is not a
# place two other page modules can reach. This name survives because
# every battery `title`/`aria-label`/`data-when` on this page calls it
# and one shipped harness check names it; it is a delegate and nothing
# else, and the behaviour — including the raw-string fallback for an
# unparseable value — is unchanged.
_FULL_TIMESTAMP_SENTINEL_NOW = layout.FULL_TIMESTAMP_SENTINEL_NOW


def _full_local_timestamp_text(ts):
    """"D Mon HH:MM" in Europe/Paris — see
    `layout.full_local_timestamp_text()`, of which this is the delegate.
    """
    return layout.full_local_timestamp_text(ts)


def _as_paris(parsed):
    """A naive datetime is taken as UTC (matching `history_db.utc_now_iso()`'s
    own output and `layout.local_clock_text()`'s own naive-input
    convention), then converted to Europe/Paris. Shared by every helper
    below that renders a battery timestamp, so there is exactly one place
    a stored `ts` crosses into local wall-clock time (D-05, 22-06-PLAN.md
    Task 2 — B4: this used to be `strftime()` on the UNCONVERTED value).
    """
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo("UTC"))
    return parsed.astimezone(layout.LOCAL_TZ)


def _axis_clock_label(ts):
    """"HH:MM" Europe/Paris clock text for a battery-chart X-axis label
    (D-05, 22-06-PLAN.md Task 2 — B4: this used to print the UNCONVERTED
    UTC clock). Built through `layout.local_clock_text()` — the one
    formatter for a visible time — with no `now_parsed`, which is what
    keeps this a bare clock rather than the day-qualified form. Falls
    back to the raw `ts` string (never raising) when it fails to parse —
    the same graceful-degradation precedent `concise_timestamp_html()`'s
    own unparseable-`ts` branch already sets.
    """
    parsed = layout.parse_iso(ts)
    return layout.local_clock_text(parsed) if parsed is not None else (ts or "")


def _axis_day_label(ts):
    """(260902-l0b; Paris days as of 22-06-PLAN.md Task 1) "D Mon"
    day-of-month-plus-abbreviated-month X-axis label for the chart's
    daily mode — `_axis_clock_label()`'s sibling, for a series whose `ts`
    names a whole Europe/Paris calendar day
    (`daily_battery_averages()`'s `"YYYY-MM-DD"` shape) rather than a
    moment. A day string parses fine via `layout.parse_iso()`
    (`datetime.fromisoformat()` accepts a date-only ISO string, at
    midnight), so `_axis_clock_label()` itself would "work" here but
    print a lie — every day's label would read "00:00". This sibling
    exists specifically to avoid that.

    `_as_paris()` converts the parsed value the same way every other
    helper here does; for a bare `"YYYY-MM-DD"` bucket key this is a
    no-op on the calendar day itself (naive midnight UTC, converted
    forward to a positive Europe/Paris offset, never crosses back a day
    boundary) — kept anyway so this function is also correct if it is
    ever handed a real instant rather than a day-bucket key. The day is
    composed from the converted `datetime`'s own `.day` integer, never
    from `strftime`'s no-pad day-of-month directive (the dash-prefixed
    variant) — that flag is a glibc/BSD extension, not portable, and not
    guaranteed by the C standard Windows's C runtime implements. The
    month uses `layout.month_abbr()` (the same fixed, locale-independent
    table `local_clock_text()` itself selects between), not `strftime`'s
    locale-dependent month-abbreviation directive. Falls back to the raw
    `ts` string (never raising) when it fails to parse — the same
    graceful-degradation precedent `_axis_clock_label()` above sets.
    """
    parsed = layout.parse_iso(ts)
    if parsed is None:
        return ts or ""
    local = _as_paris(parsed)
    return "%d %s" % (local.day, layout.month_abbr(local.month))


def _battery_reading_parts(mv, ts, now):
    """quick task 260901-uzi (finding 3): the plain-text `(value, when)`
    pair every human-facing rendering of one battery reading now shares —
    the seeded readout, each chart point's `<title>` tooltip and
    `aria-label`, and each point's `data-when` attribute.

    `value` is now the estimate then the measurement (D-01/A-19,
    19-01-PLAN.md): "≈ NN% · {mv} mV" when `battery.battery_percent(mv)`
    resolves to an int, or bare "{mv} mV" when it does not (a non-numeric
    or non-positive reading). The estimate is labelled "≈" because it is a
    linear approximation — D-01 keeps this linear estimate until Phase 5's
    discharge run yields real calibration data — and it is only the
    estimate, never the underlying millivolt figure, that carries that
    label: the frame's own low-battery warning still uses the exact
    millivolt thresholds in `server/poll_loop.py`. The literal "{mv} mV"
    substring is preserved in both branches so every existing pinned check
    on the millivolt figure keeps matching. This one helper, not
    `_battery_readout_block()`, is deliberately where the estimate is
    computed — it is what makes the resting readout, each chart point's
    tooltip, aria-label and `data-when` attribute carry the same estimate
    BY CONSTRUCTION, with no change needed to `companion/static/
    battery-trend.js`.

    `when` is "D Mon HH:MM (Nx ago)" (D-05, 22-06-PLAN.md Task 2, B4): a
    full Europe/Paris local timestamp — `_full_local_timestamp_text()`,
    which is `layout.local_clock_text()` itself, D-05's one formatter,
    forced onto its own day-qualified branch — plus
    `layout.relative_age_text()`'s existing suffix. This used to read
    "HH:MM UTC (Nx ago)": a bare clock built by `strftime()` on the
    UNCONVERTED datetime, plus a literal " UTC" that was simply wrong —
    the value was never UTC-labelled correctly to begin with, since
    every other timestamp on this page (via `local_clock_text()`) was
    already Paris local. The full day-qualified form (not a bare clock)
    is deliberate here: this exact string is what `_battery_readout_
    block()` puts in its own `title` attribute AND what each chart
    point's `<title>`/`aria-label`/`data-when` all share verbatim (one
    wrong value copied into three places is this bug's own root cause,
    so one right value is now shared the same way) — the tooltip is
    where a user disambiguates, so it must be the most complete form,
    never a bare clock.

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
    pct = battery.battery_percent(mv)
    value = ("≈ %d%% · %s mV" % (pct, mv)) if pct is not None else ("%s mV" % mv)
    age = layout.age_seconds(ts, now)
    if age is None:
        return value, (ts or "")
    when = "%s (%s)" % (_full_local_timestamp_text(ts), layout.relative_age_text(age))
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
        template = (BATTERY_AVERAGE_WHEN_ONE_TEMPLATE if reading_count == 1
                    else BATTERY_AVERAGE_WHEN_MANY_TEMPLATE)
        when = i18n.t(template) % (day_label, reading_count)
    else:
        when = i18n.t(BATTERY_AVERAGE_WHEN_BARE_TEMPLATE) % day_label
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

    24-05-PLAN.md (CFG-41/CFG-45) adds three things and removes none.
    An AREA under the line, filled from the same plotted coordinates, in
    a nested `<svg>` that owns its own viewBox so the outer canvas's
    percentage scheme is untouched (see the emission site for the full
    geometry experiment and the two candidates it ruled out). A MARK on
    the newest plotted point — the same element in the same loop, one
    class and one radius different, exempt from the density rule because
    it is not a cosmetic dot. And a low-battery THRESHOLD, a filled rect
    placed by the same `_point_y()` the readings are, whose value is read
    from `companion/battery.py` and whose label is a `<span>` legend in
    the grid below the canvas rather than a fifth axis tick. All three
    derive from the SAME single-pass filtered `pairs` list the points and
    the X-axis labels already come from; none of them re-reads `rows`.

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
    shape — `ts` names a whole Europe/Paris calendar day, 22-06-PLAN.md
    Task 1) rather than individual
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
    point_count = len(pairs)
    # 260902-l0b: the density rule — see _SPARKLINE_DENSE_POINT_THRESHOLD's
    # own derivation for why 50. Keyed on point_count alone (never on
    # `daily`), so the same protection would apply to any future dense
    # non-daily series too.
    #
    # 24-05-PLAN.md Task 2 (CFG-41) — THE RULE'S ONE EXCEPTION, written
    # here beside the rule itself so the two cannot be read as
    # contradicting each other: the rule suppresses COSMETIC dots, and
    # the newest plotted point's MARK is not a cosmetic dot. It is the
    # chart's statement of the current reading, which is exactly what a
    # 90-day daily series most needs to keep — the denser the series, the
    # harder "where is it now" is to find. So the mark is emitted at
    # every density (and carries SPARKLINE_MARK_CLASS, not
    # SPARKLINE_DOT_CLASS, so "suppress the dots" and "keep the mark"
    # cannot become the same instruction).
    dense = point_count >= _SPARKLINE_DENSE_POINT_THRESHOLD
    hit_radius = _SPARKLINE_DENSE_HIT_RADIUS_PX if dense else _SPARKLINE_HIT_RADIUS_PX

    def _point_x(index):
        # Spans the full 0-100% width, edge to edge — "the chart fills
        # its card" is a property of this formula, not a tuned margin.
        return index / (point_count - 1) * 100

    # 24-05-PLAN.md Task 1: the module-level `sparkline_point_y()` IS
    # this function — promoted out of here, behaviour unchanged, so the
    # area's baseline, the low-battery threshold and the harness can all
    # place a level with the same arithmetic the readings use. See its
    # own docstring for the D-04/A-22 clamp reasoning that used to live
    # in this comment. The local name is kept because every call below
    # reads better as `_point_y(...)` beside `_point_x(...)`.
    _point_y = sparkline_point_y

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
        SPARKLINE_AXIS_CLASS, _point_y(SPARKLINE_Y_MAX_MV),
        SPARKLINE_AXIS_CLASS, _point_y(SPARKLINE_Y_MIN_MV),
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

        # D-13/UXA-11 (and 24-05's mark): `pairs` is already in
        # chronological order and _point_x() places the last index
        # rightmost, so this one condition identifies "chronologically
        # latest", "rightmost" and "the current reading" simultaneously.
        # It is computed from `pairs` — the SAME single-pass filtered
        # list every point, the area and the X-axis labels come from —
        # and never from `rows`: the newest stored row may carry no
        # battery_mv at all, and a mark derived from it would point at a
        # reading the chart never plotted.
        is_latest = index == point_count - 1

        # 260902-l0b: above the density threshold, the cosmetic marker is
        # not emitted at all (see _SPARKLINE_DENSE_POINT_THRESHOLD's own
        # derivation) — the hit target below still is, at its own reduced
        # radius, so every point stays reachable even though it is no
        # longer individually visible as a dot.
        # 24-05-PLAN.md Task 2: the latest point gets the MARK instead of
        # a cosmetic dot — a different class and a larger radius, emitted
        # at every density (see the density rule's own exception note
        # above). It is the same element in the same place in the same
        # loop, not a second circle appended afterwards: a separate
        # marker circle would double the point's ink, and any element
        # emitted after the loop would land outside the roving-tabindex
        # sequence the hit targets below establish.
        if is_latest:
            circles.append(
                '<circle class="%s" cx="%.2f%%" cy="%.2f%%" r="%d" aria-hidden="true"/>'
                % (SPARKLINE_MARK_CLASS, x, y, _SPARKLINE_MARK_RADIUS_PX))
        elif not dense:
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
            _value_text, when_text = _daily_reading_parts(value, ts, reading_count)
        else:
            _value_text, when_text = _battery_reading_parts(value, ts, now)
        # D-05 (22-06-PLAN.md Task 2, B4): the tooltip, aria-label and
        # data-when now carry the SAME string — `escaped_when` alone,
        # never a "value — when" composite. `data-mv` (above) already
        # carries the exact value machine-readably; battery-trend.js's
        # reveal() writes it into the readout independently of data-when
        # (`readoutValue.textContent = mv + " mV"`) and prepends its own
        # " — " before `when` — so a title/aria-label that duplicated the
        # value inside the SAME string `data-when` carries would print it
        # twice once JS took over, and would fail this task's own
        # one-string invariant besides.
        escaped_when = escape_html(when_text)
        # D-13/UXA-11: roving tabindex — only the chronologically-latest
        # (rightmost) point is a normal Tab stop; every other point is
        # removed from the natural Tab order (tabindex="-1") and instead
        # reachable via companion/static/battery-trend.js's arrow-key
        # moveFocusTo() handler. `is_latest` is computed once above (it
        # was computed here before 24-05-PLAN.md Task 2 needed it
        # earlier in the same iteration), so the point that is MARKED and
        # the point that is the Tab stop are the same point by
        # construction rather than by two matching expressions.
        tabindex = "0" if is_latest else "-1"
        circles.append(
            '<circle class="%s" cx="%.2f%%" cy="%.2f%%" r="%d" tabindex="%s" '
            'role="button" data-mv="%d" data-ts="%s" data-when="%s" aria-label="%s">'
            "<title>%s</title></circle>"
            % (SPARKLINE_HIT_CLASS, x, y, hit_radius, tabindex, value, escape_html(ts),
               escaped_when, escaped_when, escaped_when))

    # THE LOW-BATTERY THRESHOLD (24-05-PLAN.md Task 2, CFG-41,
    # T-24-05-A/T-24-05-B).
    #
    # The value is READ from companion/battery.py and never re-typed
    # here. That module's LOW_BATTERY_DISPLAY_MV is the COMPANION's
    # DISPLAY threshold — where this app draws a line on a chart — and it
    # is a different number from server/poll_loop.py's
    # BATTERY_LOW_THRESHOLD_MV, which is the DEVICE's own hysteretic
    # decision about when the frame warns on glass. They are two numbers
    # for two jobs; battery.py's own comment says so at length, and a
    # millivolt literal typed into this file would be the start of them
    # quietly becoming one.
    #
    # Placed by `_point_y()` — the same function every reading is placed
    # by. A threshold with its own arithmetic would sit
    # `_SPARKLINE_VERTICAL_INSET_PERCENT` away from the readings it
    # exists to be compared against, which is a chart that lies by 3.75%
    # of its own height.
    #
    # Drawn as a filled <rect>, not a stroked <line>, for the reason the
    # axis chrome above already records: an axis-aligned integer-width
    # filled rect has no stroke-centring or half-pixel rounding to reason
    # about, and a rect can pair a percentage position with an absolute
    # size. Its own class, not SPARKLINE_AXIS_CLASS: the axis is
    # structure and is painted with the structural border token; this is
    # a judgement about the device and is painted with the app's existing
    # status-warn token (style.css). Accent stays reserved.
    #
    # SUPPRESSED ENTIRELY when the value falls outside the chart's fixed
    # range. `_point_y()` clamps, so an out-of-range threshold would draw
    # pinned to the axis edge and read as "low starts at the bottom of
    # the chart", which is a false statement rather than a clipped one.
    # 24-01 chose a value strictly inside the range on purpose, so this
    # is a guard against a later change rather than a case expected
    # today — and the legend below goes with it, because a label for a
    # line that is not drawn is worse than neither.
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
        # The label is a <span> in the chart's own grid, OUTSIDE the
        # canvas, exactly as the four axis labels are — an SVG <text>
        # node inside a canvas with no viewBox is the overflow defect the
        # wrapper grid was built to remove.
        #
        # It is a LEGEND in its own full-width row, not a third entry in
        # the Y-label column, and that is a deliberate choice rather than
        # the easy one: `.sparkline__y` is a flex column with
        # `justify-content: space-between`, which can only place labels
        # at the top, the bottom and (for three) the middle — the
        # threshold sits at 59.25% of the canvas, so a third label there
        # would name a level it does not sit beside. Pinning it to its
        # real level instead would need an inline `style` attribute on a
        # drawing element, which this codebase's drawing vocabulary
        # refuses outright (companion/draw.py's REFUSED_ATTRIBUTES). A
        # legend claims no position, so it cannot claim a wrong one; the
        # swatch beside it carries the same paint as the drawn line, so
        # the connection is made by colour rather than by proximity.
        #
        # NOT aria-hidden, unlike every axis label. Those are hidden
        # because each point's own aria-label already announces its
        # value, so reading them too would say the chart's extremes
        # twice. Nothing anywhere on this page announces where "low"
        # starts — this label is the only statement of it, and hiding it
        # would be information sighted users get and screen-reader users
        # do not.
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

    # THE AREA UNDER THE LINE (24-05-PLAN.md Task 1, CFG-41/CFG-45),
    # and the geometry experiment that produced it, recorded here because
    # the obvious simplification is unavailable rather than merely worse:
    #
    # Percentages are not permitted inside a <polygon>/<polyline>
    # `points` list, or inside a <path> `d` — the SAME rule this
    # function's own docstring already records as the reason the trend
    # line is n - 1 <line> segments rather than one polyline. So the area
    # cannot be a sibling <polygon> of those segments. It cannot be a
    # stack of per-segment quadrilaterals either: nothing but <rect>
    # accepts percentage geometry, and a trapezoid is not a rect. And the
    # outer canvas's no-viewBox scheme is not available to trade away for
    # an easier area — a viewBox there would reintroduce a scale factor
    # and shrink every stroke, marker radius and hit target at 360px,
    # which is the regression the scheme exists to prevent.
    #
    # What is left, and what is used: a NESTED <svg> carrying its own
    # viewBox="0 0 100 100" and preserveAspectRatio="none". A nested svg
    # establishes its own viewport; with that viewBox and that
    # preserveAspectRatio, user unit N maps to exactly N% of the same box
    # in each axis INDEPENDENTLY — so the polygon's plain user-unit
    # vertices land on the identical coordinates the outer scheme's
    # percentage attributes produce, and the area's top edge follows the
    # line exactly. Nothing outside this element changes coordinate
    # system. Verified in Chromium at 360px before it was built on.
    #
    # The layer carries NO size attributes and NO CSS rule of its own:
    # style.css's `.battery-trend-section svg:not(.icon)` matches EVERY
    # <svg> in the section, including this one, so the layer's box comes
    # from the same single width/height declaration the canvas's does and
    # the two cannot be sized differently. A rule on
    # SPARKLINE_AREA_LAYER_CLASS would be a second size route — and at
    # (0,1,0) one that silently loses to that selector's (0,2,1) besides.
    #
    # The baseline is the SCALE's own floor — `_point_y(
    # SPARKLINE_Y_MIN_MV)`, the level the "3000 mV" label names — never
    # y=100 (the canvas edge, where the drawn X axis sits). Closing at
    # the edge would add the vertical inset to every reading as a
    # constant, so the filled height would no longer BE the value above
    # the axis minimum, which is the only thing an area under a line
    # means.
    #
    # The fill is `currentColor` at a `fill-opacity` (style.css), the
    # line's own colour reduced — so the area is correct in dark mode by
    # the same mechanism the line already is, and no colour value is
    # introduced. A <linearGradient> would have been the nicer fade and
    # is deliberately NOT used: it can only be referenced as
    # `fill="url(#id)"`, and this function's own no-external-reference
    # guarantee (asserted against its return value in
    # companion/test_status_pages.py) forbids the substring `url(`
    # outright. That guarantee is D-09's, and weakening a security-shaped
    # assertion to buy a gradient is not a trade this plan is willing to
    # make.
    #
    # Paint order: SVG paints in document order, so the area is emitted
    # FIRST — before the axis chrome, the line segments and the points —
    # and can therefore never cover any of them. (See the point loop's
    # own paint-order note above, which this extends.)
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

    # Y-axis pair: max label first, min label second — .sparkline__y
    # (style.css) is a flex column with justify-content: space-between,
    # so document order top-to-bottom is what places max above min. X-axis
    # pair: oldest first, newest second — .sparkline__x is a flex row with
    # the same space-between, so document order left-to-right places
    # oldest before newest.
    #
    # D-04 (A-22): these two labels now print the fixed
    # SPARKLINE_Y_MIN_MV/SPARKLINE_Y_MAX_MV constants, never a per-render
    # min(values)/max(values) — so the axis always reads "3000 mV"/
    # "4200 mV" regardless of what the plotted readings actually were,
    # matching the fixed range _point_y() draws against above.
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

    # 29-06-PLAN.md Task 1 (CFG-84): BATTERY_SECTION_HEADING is
    # superseded by BATTERY_SECTION_HEADING_TEMPLATE (see that
    # constant's own comment) — this accessible group name is
    # recomputed the same way the visible heading now is, so the two
    # can never disagree.
    svg_html = (
        '<svg class="sparkline__canvas" role="group" aria-label="%s">'
        "%s%s%s%s%s"
        "</svg>"
    ) % (escape_html(i18n.t(BATTERY_SECTION_HEADING_TEMPLATE) % (BATTERY_TREND_WINDOW_DAYS // 30)),
         area_layer, axis_chrome, threshold_rect,
         "".join(line_segments), "".join(circles))

    # Grid document order: the Y-label column first (grid column 1, row
    # 1), then the canvas (auto-placed into column 2, row 1 — the only
    # cell left open once the label column claims column 1), then the
    # X-label row last (explicitly column 2 in style.css, which the grid
    # auto-places into row 2, the only open cell in that column). See
    # style.css's `.sparkline` rule for the full grid contract.
    # 24-05-PLAN.md Task 2: the threshold's legend is the grid's fourth
    # and last child — `grid-column: 1 / -1` in style.css puts it in its
    # own full-width row beneath the X-label row, the only cell left. It
    # is "" when no threshold is drawn, so the row simply does not exist
    # rather than collapsing to an empty one.
    return '<div class="sparkline">%s%s%s%s</div>' % (
        y_labels_html, svg_html, x_labels_html, legend_html)


def battery_status(rows):
    """`"warn"` when any two chronologically-consecutive readings in
    `rows` (newest-first) drop by more than `BATTERY_DROP_WARN_MV`,
    `"ok"` otherwise (including fewer than two usable readings — nothing
    to compare, so nothing to flag). A row with a missing/non-numeric
    `battery_mv` is skipped rather than compared, never crashing the
    scan or producing a false anomaly from a bad reading.

    D-05/A-23, 19-05-PLAN.md: demoted from `"error"` to `"warn"` — a
    single sampling artefact (one dropped/noisy reading) must not paint
    the whole page as an outage. `BATTERY_DROP_WARN_MV`'s own name
    already said "warn"; this is the behaviour finally agreeing with the
    name. A sustained decline still shows up in the chart and in the
    percentage readout — this function's job is only to flag one
    consecutive-pair anomaly, never to hide a real trend.
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
        # 22-12-PLAN.md Task 1 (X8): "ok" -> "off", the neutral token —
        # see _CORROBORATION_ROWS' own comment above for the full
        # reasoning and for why history_page.py deliberately keeps "ok".
        # D-15's rule that the unknown state must NEVER read as a failure
        # is unchanged and, if anything, better served: "off" is the
        # app's own not-a-problem token, where "ok" was a verdict of
        # health this row cannot honestly make.
        "None": "off",
        "False": "warn" if counts.get("False") else "ok",
    }


def _offbox_anomaly_text(offbox):
    """The single anomaly sentence for a non-ok `offbox` status (SEC-04,
    D-07), or `None` when `offbox` is `None` (unset) or already `"ok"`.

    Shared by `collect_anomalies()` (decides whether the sentence
    appears in the banner) and `_offbox_section_html()` (renders the
    identical sentence inline in the warn card) so the two can never
    read different words for the same state — one definition, two
    consumers, the same discipline `PIPELINE_STATE_TEXT` already follows
    for its own verdict/anomaly pair.
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
    """A list of short, human-readable strings — one per non-healthy
    condition among the signals this page tracks. An empty list means
    "render no anomaly banner at all" (D-21's uncluttered all-clear);
    render() is the only caller that decides what to do with the result.

    Since 06.6.1-03: render() no longer renders this list's contents
    anywhere on the page (the redundant bulleted detail-list markup was
    removed — the Overview tiles already carry the same information via
    colour) — only its emptiness is consumed, to decide whether the
    banner appears at all. The item strings below deliberately survive
    anyway: they remain the readable, greppable definition of what
    counts as an anomaly.

    Since 06.6.2-06 (UXA-14): anomaly_active()/health_severity() no
    longer route their verdict through this exact function directly —
    they route through overall_severity(), which derives a real
    "ok"/"warn"/"error" severity from the same state/flag inputs this
    function takes. This function itself remains the readable, greppable
    definition of what counts as an anomaly (and test_status_pages.py
    still calls it directly) — only its role as the presence-gate inside
    render() was replaced.

    D-05/A-23, 19-05-PLAN.md: `coverage_state` (`coverage_status()`'s own
    "ok"/"warn" verdict on the CFG-04 unresolved-prefix registry) and
    `source_fault` (the truthiness of `META_SOURCE_FAULT`) are two more
    fully-defaulted parameters, so every existing 4-argument call site
    keeps working unchanged. Two more literal strings join the original
    four — this is A-23's third half: `anomaly_active()`/
    `health_severity()` now report on two more real signals than before.

    SEC-04, D-07/D-23, 37-02-PLAN.md: `offbox` (the exact dict
    `offbox_backup_status()` returns, or `None`) is a THIRD fully-
    defaulted parameter, appended after `source_fault` the same way
    `coverage_state`/`source_fault` were appended after the original
    four — every existing call site is unaffected. `None` or a
    `"state": "ok"` dict appends nothing; `_offbox_anomaly_text()`
    (shared with `_offbox_section_html()`, see its own docstring) is
    what decides the sentence.
    """
    # D-05, 20-03-PLAN.md Task 3: each literal is wrapped in i18n.t()
    # at the append site — the literal itself (what every pinned
    # `collect_anomalies(...) == [...]` equality check in
    # test_status_pages.py compares against) is unchanged, since those
    # checks run under the default English request and t() degrades to
    # the English string unchanged there (D-04).
    anomalies = []
    # 22-04-PLAN.md Task 3 (D-03/CFG-26, T-22-12): device_state can now
    # also be "off" (frame_state.STATE_HELD — quiet hours, resolved the
    # SAME way the strip's own neutral dot is) — treated identically to
    # "ok" here, never as an anomaly, the same membership-check exemption
    # 22-03-PLAN.md Task 1 already added for pipeline_state's own "off".
    if device_state not in ("ok", "off"):
        anomalies.append(i18n.t("Device check-in is stale."))
    # 22-03-PLAN.md Task 1 (B2): pipeline_state can now also be "off"
    # (the pipeline has genuinely never run) — treated identically to
    # "ok" here, never as an anomaly. A pipeline that has never run is
    # not the same fact as one that is stale, and B2's whole point is
    # that the first must never be reported as the second.
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
    """Derive one "ok"/"warn"/"error" severity from the same signals
    `collect_anomalies()` tracks — the precedence table UXA-14's own
    acceptance criteria require documenting explicitly:

        1. `source_fault` wins outright: every configured ADS-B source
           failed on the most recent pipeline run — the page's most
           severe real state — so the overall severity is "error"
           regardless of anything else.
        2. Otherwise "error": if any of `device_state`/`pipeline_state`/
           `battery_state` equals "error", the overall severity is
           "error".
        3. Otherwise "warn": if any of the three states equals "warn",
           or `disagreement_warn` is true, or `coverage_state` equals
           "warn", or `offbox_state` equals "warn", the overall
           severity is "warn".
        4. Otherwise "ok".

    SEC-04, D-07/D-23, 37-02-PLAN.md: `offbox_state` can NEVER push this
    function to "error" — it has no membership in the step-2 states
    tuple, by design (D-23: a stale/never-pulled off-box backup is a
    warning, not a page-wide error). It joins step 3 only.

    D-05/A-23, 19-05-PLAN.md: `coverage_state` and `source_fault` are two
    new, fully-defaulted keyword parameters (signature widening, never a
    return-type change — every existing 4-argument call is unaffected).
    This SUPERSEDES this function's own former "deliberate scope
    boundary" paragraph, which used to say folding `_source_fault_block()`
    ('s always-rendered-when-true section) and the CFG-04 registry's
    coverage state into this precedence would be a new decision, not
    made here. D-05 IS that decision: `anomaly_active()`/
    `health_severity()` (both routed through this function) now report
    on two more real signals than the original four D-14 states —
    intentionally, not as an oversight of an earlier boundary.

    22-03-PLAN.md Task 1 (B2): `pipeline_state` can now also be "off"
    (the pipeline has genuinely never run) — the membership checks
    above already treat it as healthy (neither "error" nor "warn"), so
    no separate branch is needed here; see `collect_anomalies()`'s own
    explicit "off" exemption for the parallel reasoning.

    22-04-PLAN.md Task 3 (D-03/CFG-26, T-22-12): `device_state` can now
    also be "off" (frame_state.STATE_HELD) — the SAME membership checks
    already treat it as healthy for the identical reason, so a held
    frame can never light the Health nav notification dot. Bounded by
    frame_state.resolve_state() itself: a genuinely overdue frame still
    resolves to "warn" (STATE_LATE) once its own grace window elapses,
    so held cannot suppress a real problem forever.
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
    # D-05/A-23, 19-05-PLAN.md: the device's own effective wake cadence
    # (screen-off cadence, else a configured wake_interval_s, else the
    # deployed SKYPANE_SLEEP_S) resolves to this device's own staleness
    # thresholds — computed once here, never independently re-derived by
    # _device_section() or any harness fixture that omits them.
    #
    # 24-07-PLAN.md Task 2 (CFG-43): the resolved cadence is now held in
    # its own local and published below, rather than being computed
    # inline as an argument here. The check-in regularity grid has to
    # judge its cells against the SAME cadence this tile's thresholds
    # come from and has to be able to NAME it in its caption — a second
    # effective_wake_interval_s() call at another instant would be two
    # reads of a file that can change between them.
    wake_interval_s = wake.effective_wake_interval_s(inputs["device_config"])
    warn_s, error_s = wake.device_staleness_thresholds(wake_interval_s)
    # 22-04-PLAN.md Task 3 (D-03/CFG-26): the SAME triple
    # companion/layout.py's frame_strip_html() consumes, computed from
    # the SAME two facts (the device's own last check-in and its device
    # config) — never a second, independent lateness computation.
    # `device_health["ts"]` is this module's own "last check-in"
    # timestamp (the same value `_device_section()`'s pre-existing age
    # arithmetic already reads), threaded through as `last_checkin_ts`.
    device_ts = None
    if inputs["device_health"] is not _DB_UNAVAILABLE:
        device_ts = (inputs["device_health"] or {}).get("ts")
    next_wake_iso, effective_interval_s, hold_reason = wake.next_wake_status(
        device_ts, inputs["device_config"])
    device_html, device_state = _device_section(
        inputs["device_health"], now, warn_s=warn_s, error_s=error_s,
        next_wake_iso=next_wake_iso, effective_interval_s=effective_interval_s,
        hold_reason=hold_reason)
    # 20-03-PLAN.md Task 1 (D-17): a verdict-free sibling of device_html,
    # published below as "device_detail_html" — Home's status card
    # (20-06) reads it off ctx["health_state"] instead of embedding
    # device_html wholesale, since companion/pages/__init__.py forbids
    # home_page.py from importing health_page.py directly.
    device_detail_html = _device_timestamp_only(inputs["device_health"], now)
    pipeline_html, pipeline_state = _pipeline_section(
        inputs["pipeline_ts"], inputs["last_detection"], now)
    # 22-03-PLAN.md Task 1 (B2): pipeline_detail_html mirrors device_
    # detail_html immediately above — see _device_timestamp_only()'s own
    # docstring, now extended to describe both keys as one pattern.
    pipeline_detail_html = _pipeline_timestamp_only(
        inputs["pipeline_ts"], inputs["last_detection"], now)
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
    # D-05/A-23: coverage_status() and the source-fault flag now feed
    # overall_severity()/collect_anomalies() too, not only render()'s own
    # registry card and _source_fault_block() — see both functions' own
    # docstrings for the precedence this adds.
    coverage_state = coverage_status(inputs["registry_rows"])
    source_fault = _meta_flag_true(inputs["source_fault_raw"])
    # SEC-04, D-07/D-23, 37-02-PLAN.md: read exactly once per request,
    # here — never inside overall_severity()/collect_anomalies()/render()
    # independently, which would risk two different reads (and therefore
    # two different verdicts) disagreeing within the same response, the
    # same "one snapshot, every consumer reuses it" discipline WR-04's
    # own docstring above states for this whole function.
    offbox = offbox_backup_status(now)
    offbox_state = offbox["state"] if offbox is not None else "ok"
    severity = overall_severity(
        device_state, pipeline_state, battery_state, disagreement_warn,
        coverage_state=coverage_state, source_fault=source_fault,
        offbox_state=offbox_state)
    # UXA-06/D-18: threaded through to render() so _anomaly_banner_html()
    # can name the real failing category or categories rather than
    # recomputing collect_anomalies() a second time from scratch.
    anomalies = collect_anomalies(
        device_state, pipeline_state, battery_state, disagreement_warn,
        coverage_state=coverage_state, source_fault=source_fault,
        offbox=offbox)
    return {
        "now": now,
        "source_fault_raw": inputs["source_fault_raw"],
        "registry_rows": inputs["registry_rows"],
        # SEC-04, D-07: the exact offbox_backup_status() result (or
        # None when SKYPANE_OFFBOX_MARKER is unset) — render() reuses
        # this to build the card rather than reading the marker a
        # second time per request (the same "os.environ.get() read once
        # here" contract offbox_backup_status()'s own docstring states).
        "offbox": offbox,
        # CFG-43: the cadence the Device tile's own thresholds were
        # derived from, published so render()'s regularity grid judges
        # its cells against that one value and can say which it was.
        # The grid's gap ROWS are deliberately NOT read here — see
        # render()'s own call site for why that read is Health's alone.
        "wake_interval_s": wake_interval_s,
        "device_html": device_html,
        "device_state": device_state,
        "device_detail_html": device_detail_html,
        "pipeline_html": pipeline_html,
        "pipeline_state": pipeline_state,
        "pipeline_detail_html": pipeline_detail_html,
        "battery_html": battery_html,
        "battery_state": battery_state,
        "battery_caption": battery_caption,
        "corroboration_html": corroboration_html,
        "disagreement_warn": disagreement_warn,
        "anomalies": anomalies,
        "severity": severity,
    }


def safe_health_state(state_dir, now=None):
    """Fail-closed wrapper around `compute_health_state()`: `None` on any
    unanticipated exception, never a raise. Broad `except Exception`,
    unlike the narrow `(sqlite3.Error, OSError)` catches elsewhere in
    this file: this function runs on every authenticated page render, so
    a raise here would 500 every page over a decorative nav dot.
    `health_severity()` treats `None` as "ok" (fail closed — the Health
    page itself still reports the real problem in full); `render()`
    falls back to a fresh compute rather than a dict with missing keys.
    """
    try:
        return compute_health_state(state_dir, now)
    except Exception:
        return None


def health_severity(state_dir, now=None):
    """The `ctx["health_severity"]` source of truth: "ok"/"warn"/"error"
    for `state_dir`. Threaded into `ctx` for every authenticated page so
    the nav-tab dot and the anomaly banner draw from one value without a
    nav renderer importing this page module. Routes through
    `safe_health_state()`, keeping only the severity, so a second
    reimplementation of the anomaly rules can never disagree with the
    banner. A caller already holding a `safe_health_state()` result
    should read `state["severity"]` directly instead.
    """
    state = safe_health_state(state_dir, now)
    return state["severity"] if state else "ok"


def anomaly_active(state_dir, now=None):
    """`True` when the current severity for `state_dir` is not "ok". Thin
    wrapper over `health_severity()` so the anomaly rules have exactly
    one implementation.
    """
    return health_severity(state_dir, now) != "ok"


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
    `layout.anomaly_banner()`: that helper escapes its whole message as
    one plain-text string, incompatible with emitting one
    `<span class="banner__pill">` per failing category.

    `"error"` severity renders `banner--anomaly`/`role="alert"`;
    anything else renders `banner--warn`/`role="status"`. Emits a
    nowrap count-and-noun label, one pill per category, and a
    `<span class="visually-hidden">` tail carrying the original
    comma-joined sentence — giving a screen reader one coherent
    sentence instead of a lead phrase followed by disconnected pills.
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
    thresholds (`wake.device_staleness_thresholds()`), computed once in
    `compute_health_state()` and threaded through here, never recomputed
    independently, so the Device tile and the anomaly banner it feeds
    can't disagree on what "stale" means. Both default to `None`,
    degrading to `wake.device_staleness_thresholds(None)`'s bare floors.

    `next_wake_iso`/`effective_interval_s`/`hold_reason` are
    `wake.next_wake_status()`'s triple, also computed once upstream.
    `frame_state.resolve_state()` is the one decision about whether the
    frame is due, held or late; `device_staleness_thresholds()` is kept
    only as the fallback when that degrades to `STATE_UNKNOWN` (no
    next-wake data at all).

    A held frame routes to the neutral `"off"` device_state, never
    `"warn"`/`"error"`, so it can't light the nav notification dot —
    bounded, since `resolve_state()` only stays `STATE_HELD` until its
    own grace window elapses, after which a dead frame reaches
    `STATE_LATE`.
    """
    if device_health is _DB_UNAVAILABLE:
        return _unavailable_block(), "ok"
    if warn_s is None or error_s is None:
        warn_s, error_s = wake.device_staleness_thresholds(None)
    ts = (device_health or {}).get("ts")
    resolved_state = frame_state.resolve_state(
        next_wake_iso, effective_interval_s, hold_reason, now)
    if resolved_state == frame_state.STATE_UNKNOWN:
        age = layout.age_seconds(ts, now)
        state = staleness_status(age, warn_s, error_s)
        detail = _device_timestamp_only(device_health, now)
    else:
        state = _FRAME_STATE_TO_DEVICE_STATE[resolved_state]
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
    if _pipeline_never_ran(pipeline_ts, last_detection):
        # "off" is the app's existing token for a state that is not a
        # problem: no "off" entry in _STAT_TILE_BORDER_CLASSES falls
        # through to the neutral default border, and
        # collect_anomalies()/overall_severity() treat "off" like "ok".
        # The dot is hand-built rather than status_dot(): this verdict's
        # text is the paragraph's own content, not a dot-label span.
        state = "off"
        verdict_html = (
            '<span class="dot dot--off"></span>%s'
            % escape_html(i18n.t(PIPELINE_STATE_TEXT["off"])))
        detail = _pipeline_timestamp_only(pipeline_ts, last_detection, now)
        # No second "Last aircraft detected" line: last_detection is
        # falsy by definition here, so PIPELINE_NEVER_RAN_DETAIL_TEXT
        # above already says so without repeating it.
        return _tile_body(verdict_html, detail), state
    age = layout.age_seconds(pipeline_ts, now)
    state = staleness_status(age, STALE_PIPELINE_WARN_S, STALE_PIPELINE_ERROR_S)
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
    """The reserved-height readout line `companion/static/battery-trend.js`
    writes into on hover/tap/keyboard reveal. Seeded by default with
    `latest_reading`'s own humanised `(value, when)` pair
    (`_battery_reading_parts()`), the same helper
    `battery_sparkline_svg()` uses per-point, so resting and hover/tap
    text are built identically. `role="status"` already implies a
    polite live region, so no separate `aria-live` attribute is added.

    The detail span's `title` carries `when_text` itself (a full local
    timestamp plus relative age), matching the visible text exactly —
    the same value shared everywhere, never a second independently
    wrong one. `.time-value` sits on this stable wrapper span rather
    than a nested child, because `reveal()` overwrites `textContent`,
    never `class`, on every interaction.

    Two spans, not one string: `battery-trend.js`'s `reveal()` writes
    the value and detail parts separately. `battery-readout__value`
    (mono, matching the sparkline's digits) holds the value;
    `battery-readout__detail time-value` holds the separator plus "when".
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
    nothing honest to draw: no reading, or one `companion/battery.py`
    refuses (non-numeric or non-positive). An empty ring would read as
    "0%", a false statement about a device that has simply not checked
    in.

    The fraction handed to the emitter is the printed percentage divided
    by 100, not a second finer-grained estimate, so the arc can't draw
    43.4% while the text says 43%. The colour comes from `state`
    (`battery_status()`'s verdict, already computed for the card edge)
    through `draw.status_class()`, never a second judgement.
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
    """Wraps `_battery_section()`'s already-built markup in the full-width
    `BATTERY_SECTION_CLASS` card section.

    `battery_html` is already-safe markup (a pre-escaped table, an SVG,
    a script tag), interpolated verbatim with no `escape_html()` call —
    re-escaping would double-encode it and print raw tags as text.

    The `<h2>` carries only its short, fixed, window-derived heading
    text; the caption `_battery_trend_caption()` computes (defaulting to
    a "Latest N readings" fallback) sits in a sibling
    `<p class="text-label section-caption">`, so the heading itself
    never carries its own qualification. `state` composes
    `layout.card_status_class()` onto the section's own class, so the
    card's top edge carries `battery_status()`'s verdict.
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
    drives two independent consumers: the status modifier
    `_battery_trend_section_html()` paints on the card edge, and
    `collect_anomalies()`'s abnormal-drop signal in `render()`.

    `daily_rows` (the 90-day daily-average series) is a defaulted
    keyword: when `_battery_daily_series_usable(daily_rows)` holds (at
    least two Europe/Paris-day buckets), the chart plots the daily
    series; otherwise it falls back to the raw `trend_rows` series, so a
    freshly-deployed device with under two days of history still gets a
    readout. The anomaly scan, the raw-readings disclosure table and the
    readout always read `trend_rows`, never the daily series: averaging
    a day's readings would hide the abnormal drop the scan exists to
    catch.

    The empty-history branch returns `"ok"`, not `"warn"`: an absence of
    readings is not a staleness signal like Device/Pipeline's silence,
    and `render()` feeds this state straight into `collect_anomalies()`,
    which would otherwise assert an abnormal drop that never happened
    for a freshly provisioned deployment.
    """
    if trend_rows is _DB_UNAVAILABLE:
        return _unavailable_block(), "ok"
    if not trend_rows:
        return layout.empty_state(
            i18n.t("No battery readings yet."),
            i18n.t(
                "No battery telemetry recorded yet — check back after the "
                "device's next poll.")), "ok"
    state = battery_status(trend_rows)
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
    disagreement_warn = bool(counts.get("False"))
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
    """Windowed resolution-rate breakdown: `history_db.
    route_source_counts()` bounded to the last `window_days`, mapped onto
    `_SOURCE_ROWS`'s five categories (four from `enrich.resolve_route()`
    plus `"manual"`, for prefixes named by hand).

    The resolved percentage is the share of entries that produced any
    usable airline or route (everything except `"miss"`). Real traffic
    measured around 52.6% (server/plane/enrich.py), so a figure in that
    region is expected, not a defect.

    Returns `{"rows": [...], "total": N, "resolved_pct": float_or_None}`;
    `resolved_pct` is `None` when `total` is zero, guarding the caller
    against a division by zero.

    `total` counts every row `history_db.route_source_counts()` returns
    in the window, not only the five `_SOURCE_ROWS` values: an
    unrecognised `route_source` is folded into one `_OTHER_SOURCE_LABEL`
    row instead, so it is not silently dropped from the total.
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
    line, built the way `history_page._when_cell_html()` builds the
    Flights table's When column.

    At a 1280px viewport this table's wrap measures 830px, and the
    one-line timestamp form measured 251px per column in French — too
    wide for two of six columns to fit unwrapped, hence stacking.

    Degrades like `_when_cell_html()`: a falsy timestamp renders empty,
    an unparseable one renders the raw value with no secondary line.
    Never raises. The full local timestamp stays on the primary span's
    `title`, since this table has no detail row to move it to.
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
    """One `<tr>` for the unresolved-prefix registry table. First seen/
    Last seen return already-safe markup from
    `layout.concise_timestamp_html()`, interpolated verbatim, never
    re-escaped. `data-filter-text` carries the lowercased, escaped
    prefix.

    Appends a sixth `<td>`: a plain `<a>` navigating to
    `/airlines?resolve={prefix}`, never a submit-type control, so Health
    stays read-only. `_registry_cards_html()` builds the mobile
    equivalent from the same href/aria-label, differing only in visible
    link text (`RESOLVE_LINK_TEXT` here, `RESOLVE_CARD_LINK_TEXT` there).
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
    """Mobile two-line-plus-disclosure representation of the
    unresolved-prefix registry: one `<li class="data-card">` per row.
    Returns `""` for an empty list.

    A horizontal scroller would show First seen/Last seen one at a time,
    breaking the comparison they're meant to support, so the mobile shape
    is a card per prefix instead: Prefix/Count and Last seen at rest,
    First seen/Example callsign inside a `<details>` disclosure.

    `data-filter-text`/`data-filter-group` use the same helper and loop
    index as the paired `<tr>`, so the two representations can't diverge.
    The action link's `href`/`aria-label` are identical to the row's own;
    only the visible text differs (`RESOLVE_CARD_LINK_TEXT` here, longer
    since a mobile card is read standalone).
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
    """`(cells, counts, day_labels)` for the check-in regularity grid: one
    entry per Europe/Paris calendar day of CHECK_IN_WINDOW_DAYS ending on
    `now`'s day, oldest first. `cells` is `draw.regularity_grid()`'s own
    `(state, title)` shape.

    Every verdict, including a day with no record (gap `None`), goes
    through `wake.classify_check_in_gap()` — the same function the Frame
    tile consumes — so no branch here decides a day's colour on its own.
    A day is judged by its longest observed gap, not an average, so a
    single long hole is not hidden by an otherwise-ordinary day.

    Calendar arithmetic is ordinal (`date.toordinal()`/`fromordinal()`),
    with no duration arithmetic anywhere in this function — correct
    across a DST boundary, where a fixed per-day second count is not.
    Never raises: an unparseable `now` falls back to the wall clock's
    Paris day, and a malformed row is skipped.
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
    disclosure, the grid, its two date labels and the four-state key.

    `wake_interval_s` is `wake.effective_wake_interval_s()`'s answer for
    the config in force now. `None` (no `wake_interval_s`, no
    `SKYPANE_SLEEP_S`) is not silently replaced: the classifier degrades
    to `device_staleness_thresholds()`'s bare floors, and the caption
    names those floors rather than a cadence nobody configured.

    Only `CHECK_IN_CAPTION_OBSERVED` is visible; every other clause moves
    into a `<details class="readings-disclosure">` immediately after it,
    the same collapsed-disclosure idiom `_battery_section()` and
    `_corroboration_details_html()` use.
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
    """The reads `render()` and `anomaly_active()` both need, single-sourced
    into one dict so the nav-tab dot and the page's own anomaly banner
    can't disagree. `registry_rows` uses its own narrow
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

    # Reuse the state page_context() already computed via
    # safe_health_state(), rather than re-deriving it from a second,
    # non-atomic set of DB reads. Falls back to a fresh compute for a
    # test or caller that builds ctx directly.
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

    # The registry read stays independent of the stats read below: the
    # registry is a filesystem/JSON failure mode (unresolved_rows(), via
    # poll_loop.load_poll_state()), stats is a SQLite failure mode
    # (_safe_query()). Reuses state["registry_rows"] when already
    # computed by _read_health_inputs(), else reads it fresh.
    registry_rows = state.get("registry_rows")
    if registry_rows is None:
        registry_rows = unresolved_rows(state_dir)
    stats = _safe_query(
        state_dir, lambda conn: resolution_stats(conn, RESOLUTION_WINDOW_DAYS))

    # Not in _read_health_inputs(): the grid reports an observation, not
    # a severity input, so it has no second consumer worth the shared read.
    # Window is one day wider than the grid draws because `since` compares
    # a UTC-ish stored `ts` against Europe/Paris day buckets: a Paris day
    # begins before the UTC one, so a tighter cutoff would drop its first
    # hours. Extra rows outside the window simply bucket to days not drawn.
    regularity_rows = _safe_query(
        state_dir,
        lambda conn: history_db.check_in_gaps(
            conn, since=_cutoff_iso(now, CHECK_IN_WINDOW_DAYS + 1)))
    # Membership, not `.get()` with a default: None is a legitimate value
    # here (cadence cannot be determined), and a default would turn a
    # hand-built ctx's missing key into that same honest answer by accident.
    if "wake_interval_s" in state:
        wake_interval_s = state["wake_interval_s"]
    else:
        wake_interval_s = wake.effective_wake_interval_s(
            device_config.load_device_config(state_dir))

    device_tile_html = layout.stat_tile(
        i18n.t(DEVICE_FRESHNESS_LABEL), device_html, device_state, icon=ICON_DEVICE)

    # battery_state now paints the battery-trend card's top edge (see
    # _battery_trend_section_html()'s `state` argument) rather than a
    # stat-tile border. corroboration_state is the same expression that
    # keys the Corroboration tile's verdict text, so word and border
    # colour can't disagree.
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

    # The freshness line (neutral dot, "Updated " prefix, clock, hidden
    # data-loaded-at pill) is built once by layout.freshness_line_html()
    # and shared with Home and the Display scope.
    freshness_html = layout.freshness_line_html(now)

    # Two id-anchored sections. Screen wraps the Device tile in its own
    # single-tile dashboard-grid for the margin-bottom a bare stat-tile
    # lacks. Server & data holds the three-tile grid plus the two
    # migrated full-width cards, wrapped in .page-section rather than
    # .stat-tile/.dashboard-grid, which fits their wide tables.
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
        # Both migrated cards carry an additive page-section--nested
        # modifier: nested inside this section's own heading, so their
        # <h2> is a subordinate tier. _source_fault_block() below is
        # deliberately not nested: it renders above both sections, at
        # the same structural level as the section headings.
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
