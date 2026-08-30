"""companion/pages/health_page.py — CFG-03 (health status + trend) and
CFG-05's landing context (the on-device fault icon's redirect target),
06-CONTEXT.md.

Completed by plan 06-08. Imports `server.history_db`, `server.poll_loop`
(for `load_poll_state`, exposed but not currently needed on this page —
kept for parity with the module's documented import contract) and
`companion.layout` only; every dynamic value reaches HTML through
`companion.layout.escape_html()` or one of its escaping component
builders, matching the single-escaping-choke-point discipline
`companion/pages/__init__.py` documents.

Two independent freshness signals (D-12, 06-RESEARCH.md Open Question 2):
"the device last checked in" and "the ADS-B pipeline last ran" are
genuinely different signals with different failure modes and different
data sources (the Caddy access-log tailer vs. `poll_loop.py`'s own meta
writes) — this page never blends them into one verdict.

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
from datetime import timedelta

from companion.layout import escape_html
import companion.layout as layout
from server import history_db
import server.poll_loop as poll_loop  # noqa: F401 — exposed per this module's documented import contract.

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
     "that cycle (D-04: the panel is left unchanged, not blanked)."),
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

# 06.6.1-UI-SPEC.md's Copywriting Contract, verbatim. Revised from 06's
# "...see the flagged item(s) below." — 06.6.1-03 removed the bulleted
# detail-list markup this text used to point at, so the two edits (copy
# + list removal) are deliberately coupled: change one, change the other.
ANOMALY_BANNER_TEXT = "⚠ Something needs attention — check the tiles below."

DEVICE_FRESHNESS_LABEL = "Device last checked in"
PIPELINE_FRESHNESS_LABEL = "ADS-B pipeline last ran"
# Deliberately not "Battery trend" (render()'s section/tile caption for
# this same content) — reusing that string would make every substring
# assertion in the test harness ambiguous about which of the two it
# matched (D-01).
BATTERY_STATUS_LABEL = "Battery readings"

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
# Must equal companion/app.py's SCRIPT_ROUTE — duplicated, not imported,
# because companion/pages/__init__.py's contract forbids a page module
# importing companion.app (app.py imports pages, so importing back would
# be circular). The test harness asserts the two stay equal.
BATTERY_TREND_SCRIPT_SRC = "/static/battery-trend.js"
BATTERY_READOUT_PLACEHOLDER = "Tap or hover a point on the chart to see its exact reading."

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

# 06.6.1-04 (D-02): one icon id per Health signal, each a member of
# layout.ICON_IDS — the whitelist itself is what keeps a typo here from
# ever becoming a raw-markup injection: icon_html() renders nothing at
# all for an id it doesn't recognise, which is safe but invisible, so
# this module's own test harness separately asserts every one of these
# four constants is a genuine ICON_IDS member (a typo therefore fails a
# check loudly instead of silently rendering no icon).
ICON_DEVICE = "icon-device"
ICON_PIPELINE = "icon-pipeline"
ICON_CORROBORATION = "icon-corroboration"
ICON_BATTERY = "icon-battery"

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


def battery_sparkline_svg(rows):
    """A minimal, dependency-free inline SVG sparkline built server-side
    from `rows` (newest-first, `battery_trend_rows()`'s own shape) — a
    fixed viewBox, exactly one `<polyline>`, no external reference
    (`url(`, `<image`, or a script tag) of any kind, consistent with the
    zero-new-dependencies constraint (T-06-08-SC). D-02: each plotted
    point also carries a cosmetic marker plus a transparent, enlarged,
    keyboard-focusable hit target with `data-mv`/`data-ts` attributes and
    a `<title>` tooltip, so the exact reading is available on hover/tap
    with no JavaScript at all. Deliberately does **not** emit a
    script tag or the readout element itself — those are
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
    every later point's timestamp by one.
    """
    chronological = list(reversed(rows))
    pairs = [
        (row.get("battery_mv"), row.get("ts")) for row in chronological
        if isinstance(row.get("battery_mv"), int) and not isinstance(row.get("battery_mv"), bool)
    ]
    if len(pairs) < 2:
        return ""
    values = [value for value, _ts in pairs]

    width, height, padding = 300, 60, 4
    usable_w = width - 2 * padding
    usable_h = height - 2 * padding
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1
    step = usable_w / (len(values) - 1)

    points = []
    markers = []
    hit_targets = []
    for index, (value, ts) in enumerate(pairs):
        x = padding + index * step
        y = padding + usable_h - ((value - lo) / span) * usable_h
        points.append("%.1f,%.1f" % (x, y))

        markers.append(
            '<circle class="%s" cx="%.1f" cy="%.1f" r="3" aria-hidden="true"/>'
            % (SPARKLINE_DOT_CLASS, x, y))

        # "%d mV — %s" (escaped ts) — byte-identical in shape to the
        # readout string companion/static/battery-trend.js composes from
        # these same data-mv/data-ts attributes, so hover text and tap
        # readout never read differently.
        label = "%d mV — %s" % (value, escape_html(ts))
        hit_targets.append(
            '<circle class="%s" cx="%.1f" cy="%.1f" r="8" tabindex="0" '
            'role="button" data-mv="%d" data-ts="%s" aria-label="%s">'
            "<title>%s</title></circle>"
            % (SPARKLINE_HIT_CLASS, x, y, value, escape_html(ts), label, label))

    # Document order matters: SVG paints in document order and pointer
    # events go to the topmost element, so the transparent hit targets
    # must come last (after the cosmetic markers) or the cosmetic dots
    # would intercept taps meant for the hit targets underneath.
    return (
        '<svg viewBox="0 0 %d %d" width="%d" height="%d" '
        'xmlns="http://www.w3.org/2000/svg" role="group" aria-label="Battery trend">'
        '<polyline points="%s" fill="none" stroke="currentColor" stroke-width="2"/>'
        "%s%s"
        "</svg>"
    ) % (
        width, height, width, height, " ".join(points),
        "".join(markers), "".join(hit_targets),
    )


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
    what counts as an anomaly, and anomaly_active() (added the same
    plan) routes its verdict through this exact function so a future
    reader must not "clean up" these strings as dead code.
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


def anomaly_active(state_dir, now=None):
    """`True` when any of the four D-14 signals `collect_anomalies()`
    tracks is currently unhealthy for `state_dir`, `False` otherwise —
    the cross-page signal `companion/app.py`'s `page_context()` threads
    into `ctx` for every authenticated page (the "runway_images"
    precedent, Phase 06.4), so the Health nav-tab notification dot can
    be drawn without any nav renderer importing this page module
    (forbidden by `companion/pages/__init__.py`).

    Routes its verdict through `_read_health_inputs()` and the exact
    same four section builders `render()` calls, keeping only their
    state/flag return values and discarding the markup — deliberate,
    not wasteful: it is what makes it structurally impossible for the
    nav dot and the banner to disagree, since a second, cheaper
    reimplementation of the anomaly rules would be a second copy of
    them, and this module's whole D-14 design rests on there being one.

    Wrapped in a broad `except Exception` that fails closed to `False`,
    a deliberate departure from the narrow `(sqlite3.Error, OSError)`
    catches used elsewhere in this file: `_safe_query()`'s narrow catch
    protects one *section* of one page, whereas `page_context()` calls
    this function on **every** authenticated page render, so an
    unanticipated raise here would turn every page in the app into a
    500 over a decorative nav dot — exactly the reasoning
    `companion/app.py`'s `runway_images_available()` already established
    for its own never-raises contract in Phase 06.4. Failing closed is
    also the safe direction: a missing dot understates a problem the
    Health page itself will still report in full, whereas a crashed app
    reports nothing at all.
    """
    try:
        if now is None:
            now = history_db.utc_now_iso()
        inputs = _read_health_inputs(state_dir, now)
        _device_html, device_state = _device_section(inputs["device_health"], now)
        _pipeline_html, pipeline_state = _pipeline_section(inputs["pipeline_ts"], now)
        _battery_html, battery_state = _battery_section(inputs["trend_rows"])
        _corroboration_html, disagreement_warn = _corroboration_section(
            inputs["corroboration_counts"])
        return bool(collect_anomalies(
            device_state, pipeline_state, battery_state, disagreement_warn))
    except Exception:
        return False


def _unavailable_block():
    return '<p class="text-body">%s</p>' % escape_html(HEALTH_UNAVAILABLE_TEXT)


def _device_section(device_health, now):
    if device_health is _DB_UNAVAILABLE:
        return _unavailable_block(), "ok"
    ts = (device_health or {}).get("ts")
    age = layout.age_seconds(ts, now)
    state = staleness_status(age, STALE_DEVICE_WARN_S, STALE_DEVICE_ERROR_S)
    detail = escape_html(layout.absolute_and_relative(ts, now))
    row = '<p class="text-body">%s %s</p>' % (
        layout.status_dot(state, DEVICE_FRESHNESS_LABEL), detail)
    return row, state


def _pipeline_section(pipeline_ts, now):
    if pipeline_ts is _DB_UNAVAILABLE:
        return _unavailable_block(), "ok"
    age = layout.age_seconds(pipeline_ts, now)
    state = staleness_status(age, STALE_PIPELINE_WARN_S, STALE_PIPELINE_ERROR_S)
    detail = escape_html(layout.absolute_and_relative(pipeline_ts, now))
    row = '<p class="text-body">%s %s</p>' % (
        layout.status_dot(state, PIPELINE_FRESHNESS_LABEL), detail)
    return row, state


def _battery_badge_block(state):
    return '<p class="text-body">%s</p>' % layout.status_dot(state, BATTERY_STATUS_LABEL)


def _battery_readout_block():
    """The reserved-height readout line `companion/static/battery-trend.js`
    writes into on hover/tap/keyboard reveal. `role="status"` already
    implies a polite live region, so no separate `aria-live` attribute is
    added.
    """
    return (
        '<p id="%s" class="battery-readout text-label mono" role="status">%s</p>'
        % (BATTERY_READOUT_ID, escape_html(BATTERY_READOUT_PLACEHOLDER)))


def _battery_trend_section_html(battery_html):
    """Wrap `_battery_section()`'s already-built markup in the full-width
    `BATTERY_SECTION_CLASS` card section (D-02) that replaces its old
    240px-floor grid tile.

    `battery_html` is already-safe markup (badge, an already-escaped
    table, an SVG, a script tag) and is interpolated verbatim, with no
    call to `escape_html()` — the same "already-built markup passes
    through untransformed" contract `stat_tile()` and
    `_source_fault_block()` already follow; re-escaping it here would
    double-encode and print the raw tags as visible text instead of
    rendering them.

    06.6.1-04 (D-02): the battery icon sits inside this <h2>, before the
    heading text, and carries no tint class — deliberately asymmetric
    with the tile icons. This section is a page section, not a status
    tile, so there is no status modifier for a tint rule to hang off;
    the icon correctly inherits the heading's own colour through
    currentColor instead. This also resolves a wording drift in
    06.6.1-UI-SPEC.md's Layout Contract: it says "each of the 4 Overview
    tiles" gains an icon, written before plan 06.6.1-03 moved Battery
    trend out of the grid. All four Health signals still carry their
    icon — three on tiles, one here on the section heading — and the
    icon set stays at the contract's five.
    """
    return (
        '<section class="%s">'
        '<h2 class="text-heading">%s%s</h2>'
        "%s"
        "</section>"
    ) % (
        BATTERY_SECTION_CLASS, layout.icon_html(ICON_BATTERY),
        escape_html(BATTERY_SECTION_HEADING), battery_html)


def _battery_section(trend_rows):
    """Return `(markup, state)` for the Battery trend tile.

    `state` drives two independent consumers from one value: the
    `status_dot()` badge rendered by this function, and
    `collect_anomalies()`'s abnormal-drop signal in `render()`.

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
        return _battery_badge_block("ok") + layout.empty_state(
            "No battery readings yet.",
            "No battery telemetry recorded yet — check back after the "
            "device's next poll."), "ok"
    state = battery_status(trend_rows)
    table_rows = [(row.get("ts"), row.get("battery_mv")) for row in trend_rows]
    table_html = layout.data_table(
        ["Timestamp", "Battery (mV)"], table_rows, mono_columns=(0, 1))
    sparkline_html = battery_sparkline_svg(trend_rows) if len(trend_rows) >= 2 else ""
    # The script tag and readout element are emitted only when a chart
    # actually exists (sparkline_html is non-empty) — a single-reading
    # device, or one whose only rows have non-numeric millivolts, gets no
    # chart and therefore no script, keeping "exactly one script tag, and
    # zero on the empty/no-chart path" testable and true. The tag's own
    # deferred-execution attribute is what makes a DOMContentLoaded
    # wrapper unnecessary in the script.
    chart_block = ""
    if sparkline_html:
        chart_block = (
            sparkline_html + _battery_readout_block()
            + '<script src="%s" defer></script>' % BATTERY_TREND_SCRIPT_SRC)
    return _battery_badge_block(state) + table_html + chart_block, state


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
    for key, label, _default_state, explanation in _CORROBORATION_ROWS:
        rows_html.append(
            '<p class="text-body">%s <span class="mono">%d</span> — %s</p>'
            % (
                layout.status_dot(statuses[key], label),
                counts.get(key, 0) or 0,
                escape_html(explanation),
            )
        )
    return "".join(rows_html), bool(counts.get("False"))


def _source_fault_block(source_fault_raw):
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


def _read_health_inputs(state_dir, now):
    """The five `_safe_query()` reads `render()` and `anomaly_active()`
    both need, single-sourced into one dict.

    `render()` and `anomaly_active()` must be looking at the same five
    values, or the Health nav-tab dot and the page's own anomaly banner
    can disagree on screen — single-sourcing the *inputs* (not just the
    section-builder calls that consume them) is what removes that whole
    class of drift at the root, before it ever has a chance to appear.
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
        "corroboration_counts": _safe_query(
            state_dir,
            lambda conn: history_db.corroboration_counts(conn, since=cutoff)),
    }


def render(ctx):
    state_dir = ctx["state_dir"]
    now = ctx.get("now") or history_db.utc_now_iso()

    inputs = _read_health_inputs(state_dir, now)
    source_fault_raw = inputs["source_fault_raw"]

    device_html, device_state = _device_section(inputs["device_health"], now)
    pipeline_html, pipeline_state = _pipeline_section(inputs["pipeline_ts"], now)
    battery_html, battery_state = _battery_section(inputs["trend_rows"])
    corroboration_html, disagreement_warn = _corroboration_section(
        inputs["corroboration_counts"])

    anomalies = collect_anomalies(
        device_state, pipeline_state, battery_state, disagreement_warn)
    banner_html = layout.anomaly_banner(ANOMALY_BANNER_TEXT) if anomalies else ""

    # battery_state is still consumed below (collect_anomalies() still
    # takes it) — it just no longer paints a stat-tile border, since the
    # battery-trend chart moved out of this grid entirely (D-02).
    tiles_html = (
        layout.stat_tile(
            DEVICE_FRESHNESS_LABEL, device_html, device_state, icon=ICON_DEVICE)
        + layout.stat_tile(
            PIPELINE_FRESHNESS_LABEL, pipeline_html, pipeline_state, icon=ICON_PIPELINE)
        + layout.stat_tile(
            "Corroboration", corroboration_html,
            "warn" if disagreement_warn else "ok", icon=ICON_CORROBORATION)
    )

    return (
        '<h1 class="text-heading">Health</h1>'
        + _source_fault_block(source_fault_raw)
        + banner_html
        + '<h2 class="text-heading">Overview</h2>'
        + '<div class="dashboard-grid">' + tiles_html + '</div>'
        + _battery_trend_section_html(battery_html)
    )
