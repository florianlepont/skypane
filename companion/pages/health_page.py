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
# 1. What the grid shows.
CHECK_IN_CAPTION_OBSERVED = (
    "Each cell is one day of observed check-in regularity, oldest first.")
# 2. What it was judged against — and that this is TODAY'S cadence. The
#    cadence actually in force on an earlier day is not recoverable
#    (device_config.json is a current-state file), so naming it without
#    this qualifier would be a claim about the past made from a value
#    read in the present.
CHECK_IN_CAPTION_CADENCE = (
    "Judged against the cadence configured now — a check-in every %s — not "
    "necessarily the cadence in force on an earlier day.")
# 2b. And when there is no cadence to name at all: a deployment with no
#     wake_interval_s and no SKYPANE_SLEEP_S gets
#     device_staleness_thresholds()' bare floors, and the caption has to
#     say THAT rather than silently print an assumed default.
CHECK_IN_CAPTION_CADENCE_FALLBACK = (
    "This frame's cadence cannot be determined, so the grid is judged against "
    "the fallback staleness floors rather than against a configured cadence.")
# 3. What a gap is NOT. KEEP THIS CLAUSE. It is the one a later editor
#    will trim as noise, and it is the difference between reporting an
#    observation and accusing the device: the record cannot tell a wake
#    the frame missed from a log range this server lost, so a grid
#    without this sentence is a picture making a claim its own data
#    cannot support (T-24-07-A).
CHECK_IN_CAPTION_NOT_PROOF = (
    "A day with no record is not proof the frame did not wake: a log rotation "
    "this server missed leaves exactly the same gap.")
# The empty deployment. A real case, and it renders as an honest grid of
# no-observation cells rather than as a missing section.
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
_READ_ONLY_NOTE = (
    "This list is read-only here — each row's Resolve link opens the Airlines page "
    "to name that airline (and add artwork, if it needs one).")

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
# — the single-cell LiPo's whole usable window (3.3-4.2V, the same span
# `companion/battery.py`'s BATTERY_EMPTY_MV/BATTERY_FULL_MV estimate
# uses), never an auto-scaled `min(values)`/`max(values)` window. Before
# this task, a flat battery series pinned to the bottom of the canvas
# (min == max, since nothing else was on screen to compare it against)
# and a real but tiny 15mV wiggle stretched to fill the WHOLE vertical
# range, reading as a cliff rather than the noise it actually was. A
# fixed range fixes both: a flat series now draws flat, a small wiggle
# now draws small, and the chart's own axis labels agree by construction
# with the percentage readout `companion/battery.py`'s estimate already
# shows beside it, since both are now measured against the same span.
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

    svg_html = (
        '<svg class="sparkline__canvas" role="group" aria-label="%s">'
        "%s%s%s%s%s"
        "</svg>"
    ) % (escape_html(i18n.t(BATTERY_SECTION_HEADING)),
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


def collect_anomalies(
    device_state, pipeline_state, battery_state, disagreement_warn,
    coverage_state="ok", source_fault=False,
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
    return anomalies


def overall_severity(
    device_state, pipeline_state, battery_state, disagreement_warn,
    coverage_state="ok", source_fault=False,
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
           "warn", the overall severity is "warn".
        4. Otherwise "ok".

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
    if "warn" in states or disagreement_warn or coverage_state == "warn":
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
    severity = overall_severity(
        device_state, pipeline_state, battery_state, disagreement_warn,
        coverage_state=coverage_state, source_fault=source_fault)
    # UXA-06/D-18: threaded through to render() so _anomaly_banner_html()
    # can name the real failing category or categories rather than
    # recomputing collect_anomalies() a second time from scratch.
    anomalies = collect_anomalies(
        device_state, pipeline_state, battery_state, disagreement_warn,
        coverage_state=coverage_state, source_fault=source_fault)
    return {
        "now": now,
        "source_fault_raw": inputs["source_fault_raw"],
        "registry_rows": inputs["registry_rows"],
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

    Emits, as flex children of the `.banner` row: one escaped
    `<span class="banner__label">` carrying the count-and-noun lead
    ("N warning(s)"/"N error(s)") — `white-space: nowrap`, so the label
    itself never breaks mid-phrase when `.banner` wraps at narrow
    viewports (UIR-03) — one `<span class="banner__pill">` per
    `_anomaly_category_labels()` entry, and finally a
    `<span class="visually-hidden">` accessible tail
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


# --- 22-12-PLAN.md Task 1 (X8, 22-UI-SPEC.md §2): ONE tile anatomy ------
#
# Every `.stat-tile` on this page renders the same four slots in the same
# fixed order, and nothing else:
#
#   label    -> layout.stat_tile()'s own `.stat-tile__caption` (12px
#               uppercase semibold, 0.06em, 70% muted) — the tile's
#               caption argument, emitted by stat_tile() itself
#   verdict  -> the Emphasis role (16px sans semibold), EXACTLY ONCE
#   detail   -> the 70% muted strength, carrying DIFFERENT information
#               from the verdict (when / how many / what value)
#   link     -> optional
#
# This is not a new rule. It is `layout.status_row()`'s own documented
# label/verdict/detail contract (D-21) applied to `.stat-tile`, and the
# "verdict and detail must carry two DIFFERENT pieces of information"
# clause is that primitive's own docstring, cited rather than restated.
# 22-AUDIT.md's "double bold verdict" was a breach of it: the Device and
# Pipeline tiles rendered the verdict paragraph at the Emphasis role AND
# the timestamp under it at `.stat-tile__value`, which is the SAME
# Emphasis role — two bold lines, one tile, so neither read as the
# answer. The detail moves to `.widget-detail` (the muted half of the
# verdict/detail pair companion/pages/home_page.py already composes), so
# exactly one element per tile carries Emphasis.
#
# The Resolution-rate tile is the one deliberate exception to the WORD
# "verdict" and not to the anatomy: D-03/A-21 established that it makes
# no pass/fail judgement (`layout.stat_tile(..., None)`, no status
# function exists for it), so inventing a verdict sentence for it would
# assert something this page does not know. Its Emphasis slot carries
# the FIGURE instead, keeping `.stat-tile__value`; the slot order, the
# one-Emphasis-element rule and the muted detail are identical. Do not
# "fix" that by giving it a `.widget-verdict` paragraph — that would
# reverse D-03/A-21, and companion/test_status_pages.py pins its absence.
_TILE_VERDICT_CLASS = "text-body widget-verdict"
_TILE_DETAIL_CLASS = "text-label widget-detail"


def _tile_body(verdict_html, detail_html, link_html=""):
    """Assemble one Health tile's verdict/detail/link slots in the fixed
    order above. Both arguments are the caller's own ALREADY-SAFE markup
    and are interpolated verbatim, never re-escaped — the same contract
    `layout.stat_tile()`'s own `content_html` parameter documents (a
    second `escape_html()` here would double-encode and print the tags).

    The detail is a `<div>`, not a `<p>`, on purpose: the Pipeline tile's
    detail is two lines (a timestamp plus "Last aircraft detected"), and
    the Corroboration tile's detail is three rows plus a `<details>`
    disclosure. Wrapping every tile's detail in one element regardless of
    how many lines it holds is what makes "exactly one detail slot, in
    third position" a machine-checkable property rather than a reading.
    """
    html = '<p class="%s">%s</p>' % (_TILE_VERDICT_CLASS, verdict_html)
    html += '<div class="%s">%s</div>' % (_TILE_DETAIL_CLASS, detail_html)
    if link_html:
        html += '<p class="stat-tile__link">%s</p>' % link_html
    return html


def _device_timestamp_only(device_health, now):
    """The timestamp-only half of `_device_section()`'s own return
    value — no verdict paragraph (D-17, 20-UI-SPEC.md Section Anatomy
    A). Published on the health-state dict as `compute_health_state()`'s
    `"device_detail_html"` key: Home's new status card (20-06) renders
    its OWN Frame verdict from `home_page.FRAME_STATE_TEXT` and takes
    only this detail-only fragment for `status_row()`'s `detail` slot,
    so `DEVICE_STATE_TEXT`'s verdict sentence is never rendered twice
    (20-RESEARCH.md Pitfall 3 — `health["device_html"]` already carries
    it once, in `_device_section()`'s own verdict paragraph below).
    Do NOT fix the duplication by editing either state-text dict's
    wording; the fix is this detail-only sibling existing at all.

    22-03-PLAN.md Task 1 (B2): `_pipeline_timestamp_only()` below is
    this exact same pattern's sibling for the pipeline signal, published
    as `"pipeline_detail_html"` — one pattern, two signals, not a device-
    only mechanism. Home reads whichever verdict-free key matches the
    tile it renders, never `device_html`/`pipeline_html` wholesale.

    `_device_section()` is refactored below to call this helper for
    its own second half, so the two outputs can never drift out of
    sync with each other.
    """
    if device_health is _DB_UNAVAILABLE:
        return _unavailable_block()
    ts = (device_health or {}).get("ts")
    return layout.concise_timestamp_html(ts, now)


def _device_section(
        device_health, now, warn_s=None, error_s=None,
        next_wake_iso=None, effective_interval_s=None, hold_reason=None):
    """D-05/A-23, 19-05-PLAN.md: `warn_s`/`error_s` are the device's own
    cadence-derived staleness thresholds (`wake.device_staleness_
    thresholds()`), computed once in `compute_health_state()` and
    threaded through here — never recomputed independently, so the
    Device tile and the anomaly banner it feeds can never disagree on
    what "stale" means for this deployment. Both default to `None` so
    every existing direct-call harness fixture (and any caller that
    predates this task) keeps working unchanged: `None` degrades to
    `wake.device_staleness_thresholds(None)`'s own bare floors, exactly
    the retired STALE_DEVICE_WARN_S/STALE_DEVICE_ERROR_S replaced.

    22-04-PLAN.md Task 3 (D-03/CFG-26, X2): `next_wake_iso`/
    `effective_interval_s`/`hold_reason` are `wake.next_wake_status()`'s
    own triple — the SAME one `companion/layout.py`'s `frame_strip_html()`
    consumes — computed once in `compute_health_state()` and threaded
    through here, never re-derived. `frame_state.resolve_state()` is the
    ONE decision about whether the frame is due, held or late; this
    function no longer makes that decision itself from raw age alone.
    `device_staleness_thresholds()` is still the right primitive for the
    underlying age arithmetic, so it is kept as the fallback used only
    when `frame_state.resolve_state()` degrades to `STATE_UNKNOWN` — no
    computed next-wake data at all (a legacy caller passing none of the
    three new keyword arguments, or a device that has genuinely never
    checked in) — exactly today's pre-this-task behaviour in that one
    case, and none of today's existing direct-call fixtures pass these
    three keywords, so they are unaffected by this change.

    A held frame is routed to the `"off"` device_state — the same
    neutral, non-anomalous token the pipeline's own never-ran state
    already uses (22-03-PLAN.md Task 1) — never `"warn"`/`"error"`, so it
    can never light the nav notification dot (T-22-12). Held is bounded:
    `frame_state.resolve_state()` itself only stays `STATE_HELD` while
    the held-aware next wake plus its own grace window has not yet
    elapsed, so a genuinely dead frame still reaches `STATE_LATE` (`"warn"`
    here) once that window passes — held cannot suppress lateness
    forever.

    When a next-wake result IS known, this tile's own detail row shows
    the SAME next-wake clock text the strip's headline shows — both
    format the SAME `next_wake_iso` through `layout.local_clock_text()` —
    rather than the raw last-check-in timestamp `_device_timestamp_only()`
    still renders for Home's own `device_detail_html` (untouched by this
    task; Home's own Frame row is plan 22-07's, not this one's).
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
        # 22-12-PLAN.md Task 1 (X8): the `time-value--primary` modifier is
        # dropped here, and only here. That modifier IS the Emphasis
        # shape (body size, semibold) — correct on the Frame strip, where
        # the next-wake clock is the cell's own headline (22-04-PLAN.md,
        # C5), and wrong inside a tile that already carries a verdict in
        # that role one line above: the two together were half of the
        # "double bold verdict" X8 measured. The base `.time-value` role
        # (label size, regular, tabular numerals) is the supporting-value
        # shape its own style.css comment names, which is exactly this
        # slot's job. The strip's own call site is untouched.
        detail = '<span class="time-value">%s</span>' % escape_html(next_wake_clock)
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
    # D-03/A-21, 19-01-PLAN.md: a `widget-verdict` paragraph now sits
    # ahead of the timestamp row, naming the verdict this tile's border
    # colour alone used to carry. This is NOT a revival of the
    # duplicated-label defect described above: the caption
    # (DEVICE_FRESHNESS_LABEL) names the SIGNAL, this verdict states the
    # JUDGEMENT on that signal, and the timestamp row gives the raw
    # detail backing the judgement — three distinct rungs, not one
    # repeated twice.
    #
    # D-09: concise_timestamp_html() already returns pre-escaped-safe
    # markup — wrapping it in escape_html() a second time would
    # double-encode it and print the raw tags as visible text.
    #
    # 20-03-PLAN.md Task 1 (D-17): the timestamp half is delegated to
    # _device_timestamp_only() rather than recomputed here, so this
    # tile's own detail row and the verdict-free "device_detail_html"
    # fragment compute_health_state() publishes for Home can never
    # drift apart.
    #
    # 22-12-PLAN.md Task 1 (X8): the verdict/detail pair is assembled by
    # `_tile_body()` now (see its own comment block for the four-slot
    # contract). The detail used to be a `<p class="stat-tile__value">`,
    # i.e. the SAME Emphasis role the verdict above it already occupies —
    # the "double bold verdict" the audit measured. It is the muted
    # `.widget-detail` slot now; nothing about WHAT it says changed.
    return _tile_body(
        escape_html(i18n.t(DEVICE_STATE_TEXT.get(state, DEVICE_STATE_TEXT["warn"]))),
        detail), state


def _pipeline_never_ran(pipeline_ts, last_detection):
    """True when the flight pipeline has produced no evidence at all —
    no `META_LAST_PIPELINE_RUN` timestamp AND no `META_LAST_DETECTION`
    ever recorded (B2, 22-03-PLAN.md Task 1) — as distinct from a
    pipeline that has run before and has since gone stale or overdue.

    Scoped to the pipeline signal alone, not promoted onto
    `staleness_status()` itself: the device path's own "never checked
    in" case is a different, real warning (a provisioned device that
    stops reporting IS a problem), so `_device_section()` above is left
    exactly as it was — only the pipeline has a second, stronger fact
    available (a corroborating "was anything ever detected, at all"
    signal) that lets it tell "never ran" apart from "overdue" before
    `staleness_status()` ever runs.
    """
    return not pipeline_ts and not last_detection


def _pipeline_timestamp_only(pipeline_ts, last_detection, now):
    """The verdict-free half of `_pipeline_section()`'s own return
    value — mirrors `_device_timestamp_only()` (D-17) for the pipeline
    signal. Published on the health-state dict as `compute_health_
    state()`'s `"pipeline_detail_html"` key (22-03-PLAN.md Task 1, B2):
    Home reads this instead of re-embedding `pipeline_html` wholesale,
    so `PIPELINE_STATE_TEXT`'s verdict sentence is never rendered twice.
    Do NOT fix any future duplication by editing `PIPELINE_STATE_TEXT`'s
    wording — the fix is this detail-only sibling existing at all,
    exactly the precedent `_device_timestamp_only()`'s own docstring
    states.

    When the pipeline has never run, this deliberately returns
    `PIPELINE_NEVER_RAN_DETAIL_TEXT` rather than falling through to
    `concise_timestamp_html(None, now)`'s own "no reading yet" fallback
    — that fallback is the battery module's borrowed vocabulary leaking
    into a tile that never mentions a reading (B2).
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
        # 22-03-PLAN.md Task 1 (B2): a pipeline that has genuinely never
        # run is a different fact from one that is merely overdue —
        # staleness_status() maps age=None to "warn", which is still
        # correct for the general "is this signal stale" utility (see
        # _pipeline_never_ran()'s own docstring for why the device path
        # is left untouched), but this branch has a stronger fact
        # available before staleness_status() ever runs. "off" is the
        # app's own existing token for a state that is genuinely not a
        # problem (companion/static/style.css's own comment on
        # `.dot--off`: "'off' is a neutral, everyday state ... never a
        # problem") — reused here rather than inventing a new status
        # token or a fifth dot colour. `_STAT_TILE_BORDER_CLASSES`
        # (companion/layout.py) has no "off" entry, so this state falls
        # through to its own documented neutral "stat-tile--accent"
        # default border, and collect_anomalies()/overall_severity()
        # below treat "off" exactly like "ok" — never a warn.
        #
        # The dot itself is hand-built (not layout.status_dot()).
        # SUPERSEDED IN ITS REASONING, NOT IN ITS OUTPUT (22-12-PLAN.md
        # Task 1): this comment used to say "status_dot()'s own
        # state->class lookup has no 'off' entry either, and its
        # documented fallback for an unrecognised state is the WARN class
        # — calling it here would print the literal 'dot--warn' token
        # this fix exists to remove". `layout._STATUS_DOT_CLASSES` DOES
        # carry an "off" entry now (added for this page's own
        # "Only one saw it" row, X8), so that hazard is gone. The markup
        # stays hand-built anyway for a different, still-current reason:
        # status_dot() always emits a second `.dot-label` span holding
        # the label text, and this verdict's text is the paragraph's own
        # content, not a dot label — routing it through status_dot() here
        # would wrap the verdict sentence in a `.dot-label` span and
        # change this tile's markup for no gain. The Corroboration rows
        # below genuinely ARE dot+label pairs, which is why they call
        # status_dot() and this does not.
        state = "off"
        verdict_html = (
            '<span class="dot dot--off"></span>%s'
            % escape_html(i18n.t(PIPELINE_STATE_TEXT["off"])))
        detail = _pipeline_timestamp_only(pipeline_ts, last_detection, now)
        # No second "Last aircraft detected" line here: last_detection
        # is falsy by this branch's own definition, and
        # concise_timestamp_html(None, now)'s fallback is the exact
        # battery-vocabulary leak (B2) this task removes — the single
        # PIPELINE_NEVER_RAN_DETAIL_TEXT sentence above already says so
        # honestly, without repeating it a second time in different
        # words.
        return _tile_body(verdict_html, detail), state
    age = layout.age_seconds(pipeline_ts, now)
    state = staleness_status(age, STALE_PIPELINE_WARN_S, STALE_PIPELINE_ERROR_S)
    # quick task 260901-tsa (finding C): same fix, same reasoning, as
    # _device_section() above — see that function's comment for the
    # full explanation of why dropping the dot is safe.
    #
    # D-03/A-21, 19-01-PLAN.md: same verdict-paragraph addition, same
    # reasoning, as _device_section() above — this is not a revival of
    # the duplicated-label defect quick task 260901-tsa's comment
    # describes; the verdict answers the tile's caption rather than
    # repeating it.
    #
    # D-09: concise_timestamp_html() already returns pre-escaped-safe
    # markup — wrapping it in escape_html() a second time would
    # double-encode it and print the raw tags as visible text.
    verdict = escape_html(
        i18n.t(PIPELINE_STATE_TEXT.get(state, PIPELINE_STATE_TEXT["warn"])))
    # 22-03-PLAN.md Task 1: delegated to _pipeline_timestamp_only() —
    # in this branch pipeline_ts is truthy, so it is byte-identical to
    # the bare layout.concise_timestamp_html(pipeline_ts, now) call this
    # replaces — so the two halves can never drift out of sync with
    # each other, the same reasoning _device_section() already applies.
    detail = _pipeline_timestamp_only(pipeline_ts, last_detection, now)
    # Quick task 260903-peo (UIR-14): a real second content line, not
    # filler — `last_detection` is history_db.META_LAST_DETECTION, read
    # inside the same atomic _read_health_inputs() snapshot pipeline_ts
    # already comes from (they feed this one section builder together).
    # Rendered unconditionally in THIS branch (pipeline_ts is truthy —
    # the pipeline has run at least once), matching _device_section()'s
    # own unconditional-render precedent above: concise_timestamp_html()
    # returns its escaped bare-string fallback ("no reading yet") when
    # last_detection is falsy, so a pipeline that has run but never
    # detected an aircraft still gets an honest line, never an empty
    # element or a dangling label. The genuinely-never-ran branch above
    # is the one deliberate exception (22-03-PLAN.md Task 1, B2): there,
    # last_detection is falsy BY DEFINITION, so this exact fallback
    # would always fire — the battery-vocabulary leak this task removes
    # — which is why that branch returns before reaching this line
    # rather than rendering it and hiding the omission. `.stat-tile__meta`
    # supplies only the spacing (no new type tier); `.section-caption` is
    # the existing "quieter second line" muted-colour tier this reuses
    # rather than inventing a new one — the same file-wide 70% color-mix
    # strength the battery heading's trailing span and the
    # Unresolved-prefixes read-only note already compose onto their own
    # sizing class (quick task 260902-gjj, ISSUE 1). `.battery-readout__
    # detail` was considered and rejected here specifically: its class
    # name embeds the literal substring `battery-readout`, which two
    # pre-existing regression guards (`_single_reading_still_no_chart_
    # no_readout_no_script`, `_empty_battery_history_stays_script_free`)
    # assert is ABSENT from the page whenever there is no battery
    # reading — this tile renders unconditionally, so that reuse would
    # fire those guards as false positives on every fresh install.
    detection_detail = layout.concise_timestamp_html(last_detection, now)
    detail_row = (
        '<p class="stat-tile__meta text-label section-caption">%s %s</p>'
        % (escape_html(_label_colon(i18n.t(LAST_DETECTION_LABEL))), detection_detail))
    # 22-12-PLAN.md Task 1 (X8): both lines live INSIDE the one detail
    # slot now, rather than the second one trailing the tile as a fourth
    # top-level element. They were always one thing — the evidence
    # backing this tile's verdict — and X8's anatomy has exactly one
    # detail slot, so "how many lines of evidence" is a question about
    # the slot's contents, never about the tile's shape. The
    # `.stat-tile__meta` spacing rule and the `.section-caption` muted
    # tier are both unchanged; `.widget-detail` declares its colour from
    # the `--color-text` token rather than from `currentColor`, so
    # nesting the two does not compound the muting.
    return _tile_body(verdict, detail + detail_row), state


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
    earlier, at the raw `(mv, ts)` pair, so the caller can build the
    humanised value and detail parts via `_battery_reading_parts()`.
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
    emphasised, the trailing detail muted).

    D-05 (22-06-PLAN.md Task 2, B4): the detail span's `title` used to
    carry the raw UTC ISO string — the one place on this page the "one
    formatter" rule (`layout.local_clock_text()`) did not reach. It now
    carries `when_text` itself: `_battery_reading_parts()` already builds
    `when` as a full Europe/Paris local timestamp
    (`_full_local_timestamp_text()`) plus the relative age, so the title
    and the visible text are the SAME string, by construction, exactly
    like each chart point's `<title>`/`aria-label`/`data-when` — one
    right value, shared everywhere, rather than a second, independently
    wrong one. The detail span also carries the `.time-value` role
    (22-04-PLAN.md, C5): `battery-trend.js`'s `reveal()` overwrites this
    span's `textContent` (never its `class` attribute) on every hover/
    tap/keyboard move, so a class on the span itself survives every
    interaction, but a NESTED child span would not — `.time-value` is
    therefore applied to this stable wrapper rather than split into a
    separate `.time-value__age` sibling for the relative-age clause;
    `.battery-readout__detail`'s own pre-existing muted-colour rule
    (identical 70% color-mix strength to `.time-value__age`) already
    covers the whole string, relative age included.

    Two spans, not one string, because `companion/static/
    battery-trend.js`'s `reveal()` writes the value and detail parts
    separately (quick task 260901-uzi reverses that file's own
    260901-tsa non-goal — see battery-trend.js's own header comment for
    why this task edits it after all): `battery-readout__value` (also
    `mono`, matching the sparkline's own monospace digits) holds the
    value part, `battery-readout__detail time-value` holds a separator
    plus the "when" part. `mono` is gone from the outer `<p>`'s own class
    list — style.css's `.mono` reach-through rule now targets
    `.battery-readout .mono` directly, so the value span alone carries it.

    Two things deliberately did NOT change with this move, and both
    matter: `role="status"` is the live region `battery-trend.js`
    announces every Left/Right/Home/End traversal through, and the
    element is still found by `getElementById` — its position in the
    document was never something that file depended on.
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


# 24-04-PLAN.md Task 2 (CFG-40): the LARGE ring's box side, in CSS
# pixels. The number lives here and the small one lives in
# home_page.py, because a single "sizes" table in draw.py would be one
# rename away from reading as two named variants of one drawing — which
# is the thing CFG-40 forbids. What must be shared is the EMITTER, and
# it is: both pages call draw.ring_gauge(), and a change inside it moves
# both rings.
#
# 72 against this card's own 312px content width at the 360px floor
# leaves roughly 190px for the readout beside it, which still fits the
# "≈ NN% · NNNN mV — D Mon HH:MM (Nx ago)" string on the same number of
# lines its reserved min-height already allows for.
BATTERY_RING_SIZE = 72


def _battery_ring_html(latest_reading, state):
    """The battery ring for `latest_reading`, or "" when there is
    nothing honest to draw.

    RETURNS "" RATHER THAN AN EMPTY RING when there is no reading, or
    when the reading is one `companion/battery.py` refuses (non-numeric,
    or non-positive — a broken sensor rather than a flat battery). An
    empty ring reads as "0%", which is a false statement about a device
    that has simply not checked in; `_status_tiles_html()` already
    avoids the identical error by rendering a "no reading" verdict
    instead of a zero.

    THE RING AND THE READOUT BESIDE IT ARE ONE NUMBER IN TWO RENDERINGS.
    The fraction handed to the emitter is the PRINTED PERCENTAGE divided
    by 100 — not a second, finer-grained estimate — so the arc cannot
    draw 43.4% while the text says 43%. `battery.battery_percent()` is
    the app's ONE battery estimator (D-01/A-19, CFG-39) and this is a
    second invocation of that same pure function on the same millivolt
    value `_battery_reading_parts()` renders, never a second estimate;
    companion/test_status_pages.py measures the two against each other
    in the rendered page rather than trusting that sentence.

    The colour comes from `state` — `battery_status()`'s verdict, which
    this section has ALREADY computed for its own card edge — through
    draw.status_class(). Never a second judgement about the same number.
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
    """The readout, with the ring beside it when there is one.

    With no ring this returns `_battery_readout_block()`'s own markup
    UNWRAPPED and therefore byte-identical to what this section rendered
    before the ring existed — the no-reading page is not a slightly
    different page, it is the same page.

    The ring comes first in document order because it is the thing the
    eye lands on; `companion/static/battery-trend.js` finds the readout
    by `getElementById` and has never depended on its position in the
    document (its own docstring records that), so wrapping it costs
    nothing there.
    """
    readout_html = _battery_readout_block(latest_reading, now)
    ring_html = _battery_ring_html(latest_reading, state)
    if not ring_html:
        return readout_html
    return '<div class="battery-readout-row">%s%s</div>' % (ring_html, readout_html)


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
    onto the sizing class, never restated — `layout.section_intro_html()`
    (promoted from this module's own former private copy by 20-03-
    PLAN.md Task 1) is the precedent this follows (its own description
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
    caption_text = caption if caption is not None else (i18n.t("Latest %d readings") % BATTERY_TREND_LIMIT)
    return (
        '<section class="%s">'
        '<h2 class="text-heading">%s<span class="text-label section-caption">'
        " — %s</span></h2>"
        "%s"
        "</section>"
    ) % (
        section_class,
        escape_html(i18n.t(BATTERY_SECTION_HEADING)), escape_html(caption_text), battery_html)


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
    `_battery_daily_series_usable(daily_rows)` holds (at least two
    Europe/Paris-day buckets), the chart plots the daily series; otherwise it falls back
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
    literal copy "Battery dropped abnormally." for any
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
            i18n.t("No battery readings yet."),
            i18n.t(
                "No battery telemetry recorded yet — check back after the "
                "device's next poll.")), "ok"
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
    # concise Europe/Paris "HH:MM (relative)" span, D-05, with a full
    # local timestamp demoted to its `title` attribute, 22-06-PLAN.md
    # Task 3) — raw_columns=(0,) tells data_table() not to
    # re-escape it (that would double-encode and print the tags as
    # visible text). mono_columns keeps only the numeric mV column
    # monospaced; concise_timestamp_html()'s own <span class="mono">
    # already carries the mono styling for column 0.
    table_rows = [
        (layout.concise_timestamp_html(row.get("ts"), now, fallback=""), row.get("battery_mv"))
        for row in trend_rows
    ]
    # Quick task 260913-cz6: `modifier="readings"` scopes the one
    # stylesheet rule that releases THIS table from `.data-table`'s
    # shared `min-width: max-content` no-crop floor. Measured cause: at
    # a 390px viewport the floor sized this two-column table to 432px
    # (FR) / 369px (EN) inside a 308px `.data-table-wrap`, because the
    # Timestamp column's one-line form wanted 302px of ink on its own —
    # so the wrap grew its own horizontal scrollbar while the PAGE stayed
    # exactly 390px wide. See the rule's own comment in style.css for why
    # releasing the floor is right for this table and was right to reject
    # for the registry (22-12).
    table_html = layout.data_table(
        [i18n.t("Timestamp"), i18n.t("Battery (mV)")], table_rows,
        mono_columns=(1,), raw_columns=(0,), modifier="readings")
    # D-08: the raw readings table is collapsed behind a closed-by-default
    # native <details> disclosure — no custom JS toggler needed.
    disclosure_html = (
        '<details class="readings-disclosure"><summary>%s</summary>%s</details>'
        % (
            escape_html(i18n.t("View %d reading%s") % (
                len(trend_rows), "" if len(trend_rows) == 1 else "s")),
            table_html))
    # 260902-l0b: the series the CHART plots — the daily series when it is
    # usable, the raw series otherwise (the day-1 fallback). Everything
    # above and below this line keeps working from trend_rows unchanged.
    # One predicate (plot_daily) decides both the series AND the label
    # mode passed to battery_sparkline_svg() below, so the two can never
    # disagree about what is on screen.
    plot_daily = _battery_daily_series_usable(daily_rows)
    plot_rows = daily_rows if plot_daily else trend_rows
    # 22-12-PLAN.md Task 1: the chart's OWN redesign is deliberately NOT
    # in this plan, and the omission is not an oversight. 22-AUDIT.md's
    # X8 row names a gradient area fill, a marked last point, a
    # 3.3-4.2 V range and a low-battery threshold line; 22-CONTEXT.md
    # scopes every one of those to D8, Phase 23 (the dynamism half),
    # and 22-UI-SPEC.md §6 lists them as out of scope here. This plan
    # therefore changes the tiles AROUND the chart and leaves the chart
    # itself byte-for-byte alone: no area fill, no point markers, no
    # threshold line, no axis-range change. A future reader comparing
    # the audit row against this file should read the gap as scheduled,
    # not missed.
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
        # 24-04-PLAN.md Task 2 (CFG-40): the readout gained the ring
        # beside it. With no drawable reading this is byte-identical to
        # the _battery_readout_block() call it replaces.
        chart_block = (
            _battery_readout_row_html(latest_reading, now, state)
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
        "<dt>%s</dt><dd>%s</dd>" % (escape_html(i18n.t(label)), escape_html(i18n.t(explanation)))
        for _key, label, _status, explanation in _CORROBORATION_ROWS
    )
    return (
        '<details class="readings-disclosure"><summary>%s</summary>'
        "<dl>%s</dl></details>" % (escape_html(i18n.t("More details")), dl_items)
    )


def _corroboration_section(counts):
    """`(tile_body_markup, disagreement_warn)` for the Corroboration tile.

    22-12-PLAN.md Task 1 (X8): this builds the WHOLE tile body now,
    verdict included, rather than returning only the rows and leaving
    `render()` to prepend a verdict paragraph of its own. The verdict and
    the three rows are one composition — the rows are the evidence the
    verdict is drawn from — and splitting them across two modules is how
    the three Health tiles drifted into three anatomies in the first
    place. `render()` still derives the tile's own border colour from the
    `disagreement_warn` flag returned here, so the word and the border
    are still keyed on one value and cannot disagree (D-03/A-21).
    """
    if counts is _DB_UNAVAILABLE:
        return _unavailable_block(), False
    counts = counts or {}
    if not any(counts.values()):
        # 22-12-PLAN.md Task 1 (C1/X8): the compact variant. This empty
        # state renders INSIDE a `.stat-tile` whose own caption is 12px,
        # and the default form's heading is a 22px serif `.text-heading`
        # — the inverted hierarchy 22-AUDIT.md measured. The compact form
        # emits the same `.widget-verdict` / `.widget-detail` pair
        # `_tile_body()` does, so an empty Corroboration tile keeps the
        # four-slot anatomy rather than becoming a fifth shape. It is
        # therefore NOT wrapped in `_tile_body()` — that would produce a
        # second verdict element.
        return layout.empty_state(
            i18n.t("Nothing to compare yet."),
            i18n.t(
                "This appears once the frame has recorded at least one "
                "flight."),
            compact=True), False

    statuses = corroboration_status(counts)
    rows_html = []
    for key, label, _default_state, _explanation in _CORROBORATION_ROWS:
        # `statuses["None"]` is "off" now (X8) — layout._STATUS_DOT_CLASSES
        # gained that entry in the same task, so status_dot() renders the
        # neutral dot plus its normal visible `.dot-label`. All three rows
        # keep the identical markup shape; only the token differs.
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
    body = i18n.t(SOURCE_FAULT_BODY_TEMPLATE) % ", ".join(_ADSB_PROVIDER_NAMES)
    return (
        '<section class="page-section banner banner--anomaly">'
        '<h2 class="text-heading">%s</h2>'
        '<p class="text-body">%s</p>'
        "</section>"
    ) % (escape_html(i18n.t(SOURCE_FAULT_HEADING)), escape_html(body))


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
    onto `_SOURCE_ROWS`'s five documented categories — four from
    `enrich.resolve_route()` plus phase 13's fifth, `"manual"`, for
    prefixes the operator named by hand via the companion web
    interface.

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

    22-03-PLAN.md Task 2 (B3): `total` now counts EVERY row `history_db.
    route_source_counts()` returns in the window, not only the five
    `_SOURCE_ROWS` values — a NULL, empty or otherwise unrecognised
    `route_source` used to vanish from both the total and the table,
    which could make a window that genuinely holds events render as
    though nothing had ever been recorded. Anything outside the five
    known keys is folded into one additional `_OTHER_SOURCE_LABEL` row
    instead (appended only when its count is non-zero, so an ordinary
    render — every row already covered by `_SOURCE_ROWS` — is
    byte-identical to before this task).
    """
    now_dt = now or datetime.now(timezone.utc)
    since = (now_dt - timedelta(days=window_days)).isoformat(timespec="seconds")
    counts = history_db.route_source_counts(conn, since=since)

    total = sum(counts.values())
    if total == 0:
        return {"rows": [], "total": 0, "resolved_pct": None}

    resolved = total - counts.get("miss", 0)
    resolved_pct = round((resolved / total) * 100, 1)
    # 20-03-PLAN.md Task 3 (D-05): label/gloss are translated here, at
    # the one place both _stats_cards_html() and _stats_table_html()
    # read them from — every pinned check comparing row[0] against a
    # literal English source string (e.g. "Manual") runs under the
    # default English request, where i18n.t() degrades to the literal
    # unchanged.
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
    """D-20's filter bar over the unresolved-prefix registry, only ever
    rendered when there is data to filter (matches `_registry_section()`'s
    own "no chrome with no data" rule, same as History's precedent).

    22-12-PLAN.md Task 3 (B11): the count and the Clear control sit
    inside ONE `.filter-bar__meta` group — the SHARED wrapper plan 22-09
    added for Flights and plan 22-11 adopted verbatim for Airlines,
    adopted here verbatim too. Health is the third and LAST of the three
    filtered pages the audit measured, and this is Phase 18's A-18
    regressing a second time: two `nowrap` siblings in a `flex-wrap:
    wrap` container do not wrap as a unit — `nowrap` stops a break inside
    each one, and nothing stopped the container breaking BETWEEN them, so
    at 390px Clear dropped alone onto its own line. One group is a single
    flex item and moves whole or not at all. No per-page variant is
    added, and this page's Clear stays converged on the existing
    `.filter-bar [data-filter-clear]` rule.

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
    count_text = i18n.t("%d of %d shown") % (total, total)
    empty_body = i18n.t(_FILTER_EMPTY_BODY_TEMPLATE) % total
    return (
        '<div class="filter-bar">'
        '<label class="text-label" for="%s">%s</label>'
        '<div class="filter-bar__field">'
        "%s"
        # Quick task 260921-n2n Task 1: same Safari contact-autofill fix as
        # `history_page.py`'s `_filter_bar_html()` — see that file for the
        # full explanation of the three attributes below.
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


# quick task 260903-ghy (UIR-11): promoted from `_registry_table_html()`'s
# own local `headers` tuple — single-sourced so the table builder and the
# mobile card builder can never disagree on a header word. Indices 1, 2, 3
# and 4 ("Count", "First seen", "Last seen", "Example callsign") are read
# directly by `_registry_cards_html()` for its field labels; index 0
# ("Prefix") has no card-side label because the prefix value itself is
# the card's primary line, exactly as it is the table's first column with
# no separate label either.
#
# Phase 13 (D-10) APPENDS a sixth entry, "Resolve" — never inserted,
# because the four index lookups above are positional and an insertion
# would silently relabel every mobile card field.
_REGISTRY_HEADERS = ("Prefix", "Count", "First seen", "Last seen", "Example callsign", "Resolve")

# Phase 13 (D-10): the per-row deep link to the Airlines resolve surface.
# Both representations (_registry_row_html()'s <td> and
# _registry_cards_html()'s .data-card__action block) build their anchor
# from these same four constants, so the href/aria-label/text can never
# drift apart between the two.
RESOLVE_LINK_HREF_TEMPLATE = "/airlines?resolve=%s"
RESOLVE_LINK_ARIA_TEMPLATE = "Resolve prefix %s"
RESOLVE_LINK_TEXT = "Resolve"
RESOLVE_CARD_LINK_TEXT = "Resolve this prefix"


def _registry_filter_text(prefix):
    """The lowercased, escaped `data-filter-text` value shared by a
    registry `<tr>` (`_registry_row_html()`) and its paired
    `<li class="data-card">` (`_registry_cards_html()`) — extracted into
    one place, used by both, so the two representations' filter text can
    never diverge.
    """
    return escape_html(prefix.lower() if isinstance(prefix, str) else str(prefix).lower())


# 22-12-PLAN.md Task 2 (B12): the inline separator between a stacked
# cell's two lines. `companion/pages/history_page.py` owns the same
# constant for the Flights table, and `companion/pages/__init__.py`
# forbids one page module importing another, so it is restated here
# rather than imported. It is `display: none` inside this table (see the
# `table.data-table--registry` rule in companion/static/style.css) for
# the identical reason it is inside Flights': the two parts sit on
# separate lines, so an inline middle dot has no role — but the markup
# stays in the DOM so a future change that un-scopes the stacking rule
# finds the separator still there.
_REGISTRY_CELL_SEPARATOR_TEXT = "·"


def _registry_seen_cell_html(raw_ts, now):
    """The First seen / Last seen cell's two STACKED lines — a
    Europe/Paris local clock primary line and a relative-age secondary
    line — built exactly the way `history_page._when_cell_html()` builds
    the Flights table's own When column (21-03-PLAN.md Task 1, D-15):
    `layout.local_clock_text()` plus `layout.relative_age_text()` over
    `layout.age_seconds()`, never `layout.concise_timestamp_html()`.

    Why this exists at all (22-12-PLAN.md Task 2, B12), decided by
    HEADLESS MEASUREMENT rather than by eye, the same discipline that
    settled the Flights table (`references/data-density.md`): at a
    1280px viewport this table's `.data-table-wrap` has a clientWidth of
    830px, and the table wanted 886px in English and 1026px in French.
    `.data-table`'s `min-width: max-content` floor sizes every column to
    its widest UNWRAPPED line, and these two columns' one-line form
    ("1 août 08:00 (il y a 42 j)") measured 251px of ink each — 564px of
    the 830px budget for two of six columns, which is why shortening the
    French headers alone was measured to be arithmetically incapable of
    fitting and the Flights stacked-cell precedent was needed here too.
    Stacking makes each column's max-content width the WIDER of its two
    lines instead of their concatenation.

    Degrades exactly as `_when_cell_html()` does, and as this cell's own
    previous `concise_timestamp_html(..., fallback="")` call did: a falsy
    timestamp renders an empty cell, and an unparseable one renders the
    raw value as a bare primary line with no secondary (a relative age is
    undefined for a value that never parsed). Never raises.

    The full day-qualified local timestamp the previous call site
    demoted to a `title` is KEPT, on the primary span — Flights could
    drop its own because D-15 moved the full timestamp into that table's
    detail row, and this table has no detail row to move it to.
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
    Last seen switch to `layout.concise_timestamp_html()` (D-09) — its
    return value is already-safe markup and is interpolated verbatim,
    never re-escaped, matching this module's single-escaping-choke-point
    discipline for every other cell. `data-filter-text` (D-20/
    T-06.6.3-12) carries the lowercased prefix, escaped before
    interpolation into the attribute.

    Phase 13 (D-10) appends a sixth `<td>`: a plain `<a>` navigating to
    `/airlines?resolve={prefix}` — never a submit-type control, so this
    stays a navigation affordance only and Health remains read-only (the
    link changes nothing on this page). The
    prefix passes through `escape_html()` once for the `href` and once
    for the `aria-label`, this module's usual single-escaping-choke-
    point discipline. `_registry_cards_html()` below builds the mobile
    equivalent from the exact same href/aria-label — the two
    representations deliberately differ only in visible link text
    (`RESOLVE_LINK_TEXT` here, `RESOLVE_CARD_LINK_TEXT` there).
    """
    row_class = "row-alt" if index % 2 else "row"
    # 22-12-PLAN.md Task 2 (B12): the desktop table's two timestamp cells
    # are stacked now (see `_registry_seen_cell_html()` for the
    # measurements that forced it). `_registry_cards_html()` below keeps
    # calling `layout.concise_timestamp_html()` unchanged: the mobile
    # card is a single-column layout with no width budget to protect, and
    # its secondary line reads better as one sentence. The two
    # representations therefore no longer share byte-identical markup for
    # these two values, but they are still built from the SAME two
    # formatters over the same `now` — `concise_timestamp_html()` is
    # literally `local_clock_text()` plus `relative_age_text()` — so they
    # cannot disagree about what either value IS, which is what that
    # byte-identity was ever standing in for. companion/
    # test_status_pages.py asserts the shared-formatter property directly.
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
    # data-filter-group (quick task 260903-ghy): this row now HAS a
    # mobile-card pairing — _registry_cards_html() below emits one
    # <li class="data-card"> per row, carrying this exact same integer.
    # list-filter.js counts DISTINCT GROUPS, not raw elements, so this
    # value must match the paired card's own data-filter-group exactly,
    # or "N of N shown" silently doubles once every row has two DOM
    # representations.
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
    header_cells = "".join("<th>%s</th>" % escape_html(i18n.t(h)) for h in _REGISTRY_HEADERS)
    body_rows = [
        _registry_row_html(index, prefix, count, first_seen, last_seen, example_callsign, now)
        for index, (prefix, count, first_seen, last_seen, example_callsign) in enumerate(rows)
    ]
    # 22-12-PLAN.md Task 2 (B12): `data-table--registry` scopes the
    # stacked-cell rule in companion/static/style.css to this one table,
    # exactly as `data-table--flights` scopes Flights' own. It is an
    # ADDITIVE modifier — the base `data-table` class and every rule
    # keyed on it (including the `min-width: max-content` no-crop floor,
    # which this table keeps) are unchanged.
    return (
        '<div class="data-table-wrap">'
        '<table class="data-table data-table--registry">'
        "<thead><tr>%s</tr></thead>"
        "<tbody>%s</tbody>"
        "</table>"
        "</div>"
    ) % (header_cells, "".join(body_rows))


def _registry_cards_html(rows, now):
    """(quick task 260903-ghy, UIR-11) Mobile two-line-plus-disclosure
    representation of the unresolved-prefix registry — one
    `<li class="data-card">` per row in the SAME `rows` list and the SAME
    `now` value `_registry_table_html()` already receives (never a
    second query, never a second `now`). Returns `""` for an empty list,
    matching `_registry_table_html()`'s own no-chrome-with-no-data rule.

    Per-table decision: this table's five columns are short comparison
    values, and First seen/Last seen are meant to be read AGAINST each
    other — a horizontal scroller that shows one of them at a time makes
    that comparison impossible at 375px. Quick task 260902-w4t's
    scroll-edge shadow on `.data-table-wrap` stays in force as this
    table's desktop safety net; it is not this table's mobile answer.
    The mobile shape is therefore a card per prefix: Prefix and Count at
    rest on the primary line, Last seen at rest on the secondary line,
    First seen and Example callsign one tap away inside a `<details>`
    disclosure (History's own two-lines-at-rest card shape, so a large
    registry does not become a many-screen page).

    `data-filter-text`/`data-filter-group` are computed with the exact
    same `_registry_filter_text()` helper and the same loop index
    `_registry_row_html()` uses for the paired `<tr>` — the two can never
    diverge. `layout.concise_timestamp_html(value, now, fallback="")` is
    called identically to the `<tr>`'s own cell for the same value, so
    the two representations' Last seen/First seen markup is
    byte-identical (D-09).

    Phase 13 (D-10): a `.data-card__action` block sits between the
    secondary line and the `<details>` disclosure — visible at rest, not
    behind a tap, since it is this card's one actionable affordance. Its
    anchor carries the identical `href`/`aria-label` the paired `<tr>`'s
    sixth `<td>` carries, built from the same `RESOLVE_LINK_HREF_TEMPLATE`/
    `RESOLVE_LINK_ARIA_TEMPLATE` constants — the two representations
    deliberately differ ONLY in visible link text (`RESOLVE_CARD_LINK_TEXT`
    here, longer/self-contained since a mobile card is read standalone,
    versus `RESOLVE_LINK_TEXT` on desktop where the row's own Prefix cell
    already supplies context).
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
    header_html = '<p class="text-body section-caption">%s</p>' % escape_html(i18n.t(_READ_ONLY_NOTE))

    if not rows:
        return header_html + layout.empty_state(i18n.t(_NO_GAPS_HEADING), i18n.t(_NO_GAPS_BODY))

    filter_html = _registry_filter_bar_html(len(rows))
    cards_html = _registry_cards_html(rows, now)
    table_html = _registry_table_html(rows, now)
    # Cards render before the table (quick task 260903-ghy) — style.css's
    # `.data-cards ~ .data-table-wrap` sibling-combinator toggle depends
    # on this exact DOM order; do not reorder these two calls.
    return header_html + filter_html + cards_html + table_html


def _stats_cards_html(rows):
    """(quick task 260903-ghy, UIR-10) Mobile stacked-prose representation
    of the Resolution-statistics table — one `<li class="data-card">` per
    `(label, gloss, count)` triple in `rows`, the SAME `stats["rows"]`
    list `_stats_table_html()` already has: no second data pass. Returns
    `""` for an empty list, matching `_stats_table_html()`'s own
    no-chrome-with-no-data rule for this card.

    Per-table decision: a horizontal scroll affordance is the wrong
    answer for THIS table specifically, not a stylistic preference —
    `.data-table--prose`'s own comment in style.css already measured
    1172px of content inside an 831px container for this exact table and
    ruled that a column of full sentences must WRAP, not scroll.
    Re-answering this table's mobile shape with a scroller would reinstate
    the exact defect that rule was written to remove. The mobile shape is
    therefore stacked: Source label and Count on the primary line, the
    FULL, untruncated Description sentence as a full-width paragraph
    beneath it — never a disclosure, never a truncation, because the
    description IS the content of this table.

    Every value goes through `escape_html()` — this module's single
    escaping choke-point discipline, no exceptions.
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
    """The resolution-statistics breakdown table, plus (quick task
    260903-ghy, UIR-10) its `.data-cards` mobile sibling emitted BEFORE
    it — style.css's `.data-cards ~ .data-table-wrap` sibling-combinator
    toggle depends on that exact document order; do not reorder these two
    calls. Returns the empty string when there is nothing to show (no
    data yet, or the database is unavailable) — `_resolution_rate_tile_html()`
    already carries that message once, and this card must not repeat it.

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
    return _stats_cards_html(stats["rows"]) + layout.data_table(
        [i18n.t(header) for header in _STATS_HEADERS], stats["rows"],
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
        # 22-03-PLAN.md Task 2 (B3): the heading is translated FIRST,
        # then interpolated — the same order _FILTER_EMPTY_BODY_TEMPLATE
        # already uses above — so the "%d" placeholder survives
        # translation and RESOLUTION_WINDOW_DAYS never appears as a
        # hard-coded literal in either language's catalogue entry.
        # 22-12-PLAN.md Task 1 (C1/X8): the compact variant, for exactly
        # the reason _corroboration_section() uses it — this block lands
        # inside a `.stat-tile`, and the default form's 22px serif
        # heading inside a 12px-captioned tile is the inverted hierarchy
        # the audit measured. Not wrapped in `_tile_body()`: the compact
        # empty state already occupies both slots itself, and this tile
        # must carry no `.widget-verdict` at all (D-03/A-21).
        return layout.empty_state(
            i18n.t(_NO_STATS_HEADING) % RESOLUTION_WINDOW_DAYS,
            i18n.t(_NO_STATS_BODY), compact=True)
    # 22-12-PLAN.md Task 1 (X8): the four-slot anatomy, with ONE
    # deliberate difference from its three siblings — the Emphasis slot
    # holds the FIGURE, in `.stat-tile__value`, not a verdict word.
    # D-03/A-21 established that this tile makes no pass/fail judgement
    # (it is the one tile passed `status=None`, and no status function
    # for it exists anywhere in this module), so a `.widget-verdict`
    # paragraph here would assert a judgement the page cannot make;
    # companion/test_status_pages.py pins its absence. Slot ORDER, the
    # one-Emphasis-element rule and the muted detail are identical to the
    # other three, which is what "one anatomy" means here.
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
    """`(cells, counts, day_labels)` for the check-in regularity grid —
    one entry per Europe/Paris calendar day of the CHECK_IN_WINDOW_DAYS
    ending on `now`'s own day, oldest first (24-07-PLAN.md Task 2).

    `gap_rows` is `history_db.check_in_gaps()`'s own output and is read,
    never recomputed. `cells` is `draw.regularity_grid()`'s own
    `(state, title)` shape.

    EVERY VERDICT IS `wake.classify_check_in_gap()`'s, INCLUDING THE
    EMPTY ONES, and that is a property rather than a convenience: a day
    the record says nothing about is passed to the classifier as a gap of
    `None`, which it answers `CHECK_IN_UNKNOWN` for — so there is no
    branch anywhere in this page that decides a day's colour, not even
    for the absent case. One function decides what "late" means for this
    deployment and it is the same one the Frame tile consumes.

    A DAY IS JUDGED BY ITS LONGEST OBSERVED GAP. The alternative — an
    average, or the newest gap — would hide exactly the event a reader
    opens this page for: forty ordinary check-ins and one six-hour hole
    is a day with a six-hour hole in it, and the cell's own title names
    that duration so the colour is checkable rather than merely asserted.
    `max()` over values the reader already computed is not a second
    interval computation; nothing here subtracts two instants.

    THE CALENDAR ARITHMETIC IS ORDINAL, and the day-offset type this
    module imports for other purposes is deliberately not used here. The
    reason is narrow: this function must contain no duration arithmetic
    at all — a check reads its own source for exactly that, and it reads
    it bluntly enough that this paragraph has to talk around the names it
    bans — and walking a window of days by `date.toordinal()` /
    `date.fromordinal()` is calendar arithmetic with no duration
    anywhere in it. It is also correct across a DST boundary for free,
    where adding a fixed number of seconds per day is not.

    Never raises: an unparseable `now` falls back to the wall clock's own
    Paris day, and a row of any other shape is skipped.
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
    """The whole "Check-in regularity" card: heading, the three-clause
    caption, the grid, its two date labels and the four-state key.

    `wake_interval_s` is `wake.effective_wake_interval_s()`'s answer for
    the config in force RIGHT NOW, and the caption says so in as many
    words. `None` — a deployment with no `wake_interval_s` and no
    `SKYPANE_SLEEP_S` — is not silently replaced with a default: the
    classifier degrades to `device_staleness_thresholds()`' bare floors
    for it, and the caption names those floors instead of naming a
    cadence nobody configured.
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
        # The oldest label is read PAST anything the drawing dropped, so
        # the two labels can only ever name cells that are on screen. The
        # window is inside the emitter's own bound today, so `dropped` is
        # 0 — this line is what keeps the labels honest if that ever
        # stops being true, rather than a caption quietly naming a day
        # the grid no longer draws.
        oldest = labels[dropped] if dropped < len(labels) else labels[-1]
        clauses = [i18n.t(CHECK_IN_CAPTION_OBSERVED)]
        if not observed:
            clauses.append(i18n.t(CHECK_IN_CAPTION_EMPTY))
        if draw.is_number(wake_interval_s) and wake_interval_s > 0:
            clauses.append(
                i18n.t(CHECK_IN_CAPTION_CADENCE) % layout.duration_text(wake_interval_s))
        else:
            clauses.append(i18n.t(CHECK_IN_CAPTION_CADENCE_FALLBACK))
        clauses.append(i18n.t(CHECK_IN_CAPTION_NOT_PROOF))
        body = (
            '<p class="text-label section-caption">%s</p>'
            '<div class="%s">%s<div class="%s">%s%s</div></div>'
            '%s'
        ) % (
            escape_html(" ".join(clauses)),
            escape_html(CHECK_IN_GRID_CLASS), grid_html,
            escape_html(CHECK_IN_SCALE_CLASS),
            draw.label_span(oldest, hidden=False),
            draw.label_span(labels[-1], hidden=False),
            _check_in_key_html())
    # A plain `.page-section` card and deliberately NOT
    # `page-section--nested`. The nested modifier is carried by exactly
    # the two cards migrated into Server & data, and three checks pin
    # that count; this card is the Screen section's SECOND full-width
    # card, and the first one (battery trend) carries its own class
    # rather than that modifier too. Following the precedent already
    # inside this section is the right call on its merits and leaves
    # those three pins measuring what they were written to measure.
    return (
        '<section class="page-section">'
        '<h2 class="text-heading">%s</h2>%s</section>'
    ) % (escape_html(i18n.t(CHECK_IN_SECTION_HEADING)), body)


def _check_in_key_html():
    """The grid's key: four swatches, four names, in the classifier's own
    order from best to worst and then absence.

    THE SWATCH TAKES THE CELL'S OWN CLASS, not a copy of its colour. The
    `.drawing-cell--*` modifiers set `color` and nothing else, so the
    same declaration paints the SVG cell (through `fill: currentColor`)
    and this HTML swatch (through `background: currentColor`) — a key
    that could disagree with the cells it explains is worse than no key.
    The swatch is aria-hidden because the word beside it IS the reading;
    a screen reader announcing a coloured box adds nothing.
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
    """The nine reads `render()` and `anomaly_active()` both need,
    single-sourced into one dict.

    `render()` and `anomaly_active()` must be looking at the same nine
    values, or the Health nav-tab dot and the page's own anomaly banner
    can disagree on screen — single-sourcing the *inputs* (not just the
    section-builder calls that consume them) is what removes that whole
    class of drift at the root, before it ever has a chance to appear.

    260902-l0b: grew from five reads to six — `daily_rows` joins
    `trend_rows` here, in the one atomic snapshot, because it is a
    battery-health read consumed by the same section builder
    (`_battery_section()`) from the same table (`device_health`) in the
    same request. Quick task 260903-peo (UIR-14) grew it again, six to
    seven: `last_detection` joins `pipeline_ts` here for the identical
    reason — it feeds the same section builder (`_pipeline_section()`),
    from the same table (`meta`), in the same request.

    D-05/A-23, 19-05-PLAN.md: grew again, seven to nine — `device_config`
    (`device_config.load_device_config()`, a never-raising config read,
    consumed by `compute_health_state()` to derive the device's own
    staleness thresholds) and `registry_rows` (the CFG-04 unresolved-
    prefix registry, now consumed by `overall_severity()`/
    `collect_anomalies()` via `coverage_status()`, in addition to its
    pre-existing consumer, `render()`'s own registry card).

    This PARTIALLY reopens D-11's original "does NOT reopen" boundary,
    and says so explicitly rather than silently contradicting it:
    `registry_rows` here is wrapped in its own narrow
    `(OSError, ValueError)` guard (T-19-23) — a DIFFERENT failure mode
    from every other key in this dict (SQLite, via `_safe_query()`) — so
    a registry read failure degrades to "no gaps" for SEVERITY purposes
    without taking down any other section, preserving the failure-mode
    isolation `render()`'s own comment demands. `render()`'s registry
    CARD still degrades independently too (see its own call site's
    comment for why this key alone is read twice, by design, rather than
    threading one value through both consumers).
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


def _stats_section_html(stats):
    """The "How well we name flights" nested page-section — heading,
    card and all — or the empty string.

    22-03-PLAN.md Task 2 (B3): omitted ENTIRELY (no heading, no
    wrapper) when there is genuinely nothing in the window
    (`stats["total"] == 0`), rather than the pre-existing bug of a
    heading rendered unconditionally over `_stats_table_html()`'s own
    empty string — a heading with no body beneath it. `stats is
    _DB_UNAVAILABLE` is deliberately NOT folded into this omission: a
    database read failure is a different, out-of-scope failure mode
    (D-11's own independent-degradation contract for this card), left
    exactly as it rendered before this task.
    """
    if stats is not _DB_UNAVAILABLE and stats["total"] == 0:
        return ""
    # quick task 260902-gjj (ISSUE 2): this card deliberately gets NO
    # status modifier — _stats_table_html() computes no verdict (it
    # returns either the empty string or a plain data_table), and
    # resolution_stats() returns counts and a percentage with no status
    # field. No status function exists for this card anywhere in this
    # module (confirmed from source, not assumed). Its neutral hairline
    # is therefore the correct signal that it carries no pass/fail
    # state — not an omission to "complete the pattern" with an accent
    # border.
    return '<section class="page-section page-section--nested"><h2 class="text-heading">%s</h2>%s</section>' % (
        escape_html(i18n.t(STATS_SECTION_HEADING)), _stats_table_html(stats))


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

    # D-11: the registry card's own read is deliberately independent of
    # the stats read below — the registry read is a filesystem/JSON
    # failure mode (poll_loop.load_poll_state(), inside
    # unresolved_rows()), the stats read is a SQLite failure mode
    # (_safe_query()); merging them would make one query's failure take
    # down a card that used to fail independently on the page it came
    # from.
    #
    # D-05/A-23, 19-05-PLAN.md: `_read_health_inputs()` now ALSO reads
    # the registry (for severity's sake — see that function's own
    # docstring), so `state["registry_rows"]` already carries this
    # exact value whenever `state` is a real compute_health_state()
    # result. Reused here rather than re-reading the registry a second
    # time per request — the same "reuse the precomputed state, fall
    # back to a fresh read" shape this function already uses for
    # `health_state` itself, so a caller that builds `ctx["health_state"]`
    # by hand (bypassing `_read_health_inputs()`) still gets a real
    # registry card rather than a missing key.
    registry_rows = state.get("registry_rows")
    if registry_rows is None:
        registry_rows = unresolved_rows(state_dir)
    stats = _safe_query(
        state_dir, lambda conn: resolution_stats(conn, RESOLUTION_WINDOW_DAYS))

    # 24-07-PLAN.md Task 2 (CFG-43): the regularity grid's own read, made
    # HERE and deliberately not in _read_health_inputs(). That dict
    # exists so render() and anomaly_active() cannot see different
    # values, and this read has no second consumer: the nav dot computes
    # no verdict from it and never will, because the grid reports an
    # observation rather than a fault. Putting it in the shared snapshot
    # would charge every authenticated page in the app for a read only
    # Health uses — the same reasoning, and the same shape, as the
    # `stats` read directly above.
    #
    # The window is one day wider than the grid draws, because `since` is
    # compared raw against a UTC-ish stored `ts` while the grid buckets
    # by EUROPE/PARIS day: a Paris day begins an hour or two before the
    # UTC one, so a cutoff exactly at the window's first day would drop
    # that day's first hours. Extra rows outside the window simply bucket
    # to days the grid does not draw.
    regularity_rows = _safe_query(
        state_dir,
        lambda conn: history_db.check_in_gaps(
            conn, since=_cutoff_iso(now, CHECK_IN_WINDOW_DAYS + 1)))
    # Reuse the cadence compute_health_state() already resolved — the
    # same "reuse the precomputed state, fall back to a fresh read" shape
    # this function already uses for `health_state` itself and for
    # `registry_rows`. Membership, not `.get()` with a default: `None` is
    # a LEGITIMATE value here (a deployment whose cadence cannot be
    # determined), and a default would turn a hand-built ctx's missing
    # key into that same honest answer by accident.
    if "wake_interval_s" in state:
        wake_interval_s = state["wake_interval_s"]
    else:
        wake_interval_s = wake.effective_wake_interval_s(
            device_config.load_device_config(state_dir))

    # 19-06-PLAN.md Task 2 (D-06): DEVICE_FRESHNESS_LABEL is already
    # plain language ("Device last checked in") — there is no genuine
    # technical term to demote to a tooltip here, so no `caption_title`
    # is passed, rather than inventing one.
    device_tile_html = layout.stat_tile(
        i18n.t(DEVICE_FRESHNESS_LABEL), device_html, device_state, icon=ICON_DEVICE)

    # battery_state is still consumed above (collect_anomalies() still
    # takes it), and (quick task 260902-gjj, ISSUE 2) it once again paints
    # a status-coloured border — no longer a stat-tile border (D-02
    # already moved this content out of .stat-tile), but the
    # battery-trend section's own card-level top edge, via
    # _battery_trend_section_html()'s new `state` argument below. A
    # different mechanism reaching the same original intent D-01's own
    # reference note expected.
    # D-03/A-21, 19-01-PLAN.md: the Corroboration tile's verdict is keyed
    # on the identical expression already passed as this tile's own
    # `status` argument below, so the word and the border colour can
    # never disagree. 22-12-PLAN.md Task 1 (X8): the verdict PARAGRAPH
    # itself moved into `_corroboration_section()` (see that function's
    # docstring) — this expression stays here because it is what paints
    # the tile's border, and it is still the same one `disagreement_warn`
    # flag on both sides, so the anti-disagreement property is unchanged.
    corroboration_state = "warn" if disagreement_warn else "ok"
    server_data_tiles_html = (
        layout.stat_tile(
            i18n.t(PIPELINE_FRESHNESS_LABEL), pipeline_html, pipeline_state,
            icon=ICON_PIPELINE, caption_title=i18n.t(PIPELINE_FRESHNESS_TITLE))
        + layout.stat_tile(
            i18n.t(CORROBORATION_TILE_LABEL), corroboration_html,
            corroboration_state, icon=ICON_CORROBORATION,
            caption_title=i18n.t(CORROBORATION_TILE_TITLE))
        # D-03/A-21: the Resolution-rate tile is the one deliberate
        # exception — it is passed status=None and carries no
        # pass/fail verdict anywhere in this module (no status function
        # for it exists), so inventing a verdict word for it here would
        # assert a judgement this page does not actually make. Its
        # rendered figure stays exactly as it was before this task.
        + layout.stat_tile(
            i18n.t(RESOLUTION_RATE_LABEL), _resolution_rate_tile_html(stats), None,
            caption_title=i18n.t(RESOLUTION_RATE_TITLE))
    )

    # 23-06-PLAN.md Task 2 (D1/CFG-35): the whole freshness line — the
    # neutral dot, the "Updated " prefix, the clock element and the
    # hidden pill carrying data-loaded-at — is now built by
    # companion/layout.py's freshness_line_html(). ONE definition site,
    # three call sites (Health, Home, the Display scope), which is the
    # same contract frame_strip_html() and sidebar_nav() already state in
    # their own docstrings. Every word of this block's reasoning moved
    # with it, unabridged: why the pill carries no ARIA role, why the dot
    # is neutral and rendered still, why the clock and not an age is what
    # the server writes, and why all of it sits in ONE block-level
    # wrapper. This page's rendered output is byte-identical to what it
    # was before the move.
    freshness_html = layout.freshness_line_html(now)

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
        layout.section_intro_html(
            SCREEN_SECTION_ID, i18n.t(SCREEN_SECTION_HEADING), i18n.t(SCREEN_SECTION_DESCRIPTION))
        + '<div class="dashboard-grid">' + device_tile_html + '</div>'
        + _battery_trend_section_html(battery_html, battery_state, battery_caption)
        # CFG-43: the regularity grid belongs to Screen and not to Server
        # & data — it is a picture of what the FRAME did, drawn from the
        # frame's own check-ins, and it sits under the Device tile whose
        # definition of "late" it shares.
        + _check_in_regularity_section_html(regularity_rows, wake_interval_s, now)
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
        layout.section_intro_html(
            SERVER_DATA_SECTION_ID, i18n.t(SERVER_DATA_SECTION_HEADING),
            i18n.t(SERVER_DATA_SECTION_DESCRIPTION))
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
            registry_class, escape_html(i18n.t(UNRESOLVED_SECTION_HEADING)),
            _registry_section(registry_rows, now))
        # 22-03-PLAN.md Task 2 (B3): the stats card is now conditionally
        # omitted entirely when empty — see _stats_section_html()'s own
        # docstring for the "no status modifier" rule (quick task
        # 260902-gjj, ISSUE 2) this preserves unchanged.
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
