"""companion/pages/airlines_page.py — CFG-04 (unresolved-prefix registry,
read-only) and CFG-08 (resolution statistics), 06-CONTEXT.md.

D-16: read-only by design. This module must never emit a form element or
a button element — there is no "mark resolved" action, now or in a later
plan; the user resolves entries manually elsewhere (the existing
quick-task runbook), and this page only makes the registry visible.

Completed by plan 06-08. Reads the registry through
`server.poll_loop.load_poll_state()` only — never opens
`poll_state.json` directly, and never re-derives any of
`server/plane/enrich.py`'s own prefix-resolution internals (its
registry-writing function or its callsign-shape validator) — D-16 scopes
this page to *displaying* an already-computed registry; duplicating its
derivation would create a second source of truth the runbook doesn't
expect.
"""
from datetime import datetime, timedelta, timezone

import sqlite3

from companion.layout import empty_state, escape_html
import companion.layout as layout
from server import history_db
import server.poll_loop as poll_loop

_NO_GAPS_HEADING = "No coverage gaps."
_NO_GAPS_BODY = (
    "No unresolved callsign prefixes — airline coverage looks complete.")

_READ_ONLY_NOTE = (
    "This list is read-only by design — resolving a prefix is a manual "
    "step done elsewhere, following the existing coverage-gap runbook.")

# 06-UI-SPEC.md documents exactly one "unavailable" copy (the Health
# page's); reused verbatim here rather than importing companion.pages
# .health_page (no cross-page-module import — each page module is
# self-contained per companion/pages/__init__.py's contract).
STATS_UNAVAILABLE_TEXT = (
    "Health history is temporarily unavailable — check the companion "
    "service logs.")

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

_DB_UNAVAILABLE = object()


def _safe_query(state_dir, fn):
    """Same rationale/shape as companion/pages/health_page.py's own
    helper: isolates one section's database access so a locked/missing/
    corrupt database degrades only that section, never the whole page.
    """
    try:
        with history_db.open_db(state_dir) as conn:
            return fn(conn)
    except (sqlite3.Error, OSError):
        return _DB_UNAVAILABLE


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


def _registry_section(rows):
    status_html = layout.status_dot(coverage_status(rows), "Coverage")
    note_html = '<p class="text-body">%s</p>' % escape_html(_READ_ONLY_NOTE)
    header_html = '<p class="text-body">%s</p>' % status_html + note_html

    if not rows:
        return header_html + empty_state(_NO_GAPS_HEADING, _NO_GAPS_BODY)

    table_html = layout.data_table(
        ["Prefix", "Count", "First seen", "Last seen", "Example callsign"],
        rows,
        mono_columns=(0, 4),
    )
    return header_html + table_html


def _resolved_headline_html(stats):
    """D-18's promoted resolved-rate headline — a bare
    `.stat-tile__value`-styled figure rendered directly under the page
    header, not wrapped in a `stat_tile()` card (it *is* the page's
    primary value, per D-18's own instruction). `stats` is
    `resolution_stats()`'s already-computed result, threaded in by
    `render()` rather than recomputed here — this function and
    `_stats_table_html()` below are the two consumers of that one
    computed dict, never a second call to `resolution_stats()`.

    Falls back to the existing no-stats empty state when there is no
    data yet (or the database is unavailable), so this promoted slot
    never renders a headline with nothing behind it.
    """
    if stats is _DB_UNAVAILABLE:
        return '<p class="text-body">%s</p>' % escape_html(STATS_UNAVAILABLE_TEXT)
    if stats["total"] == 0:
        return empty_state(_NO_STATS_HEADING, _NO_STATS_BODY)
    return (
        '<p class="stat-tile__value">%.1f%% resolved</p>'
        '<p class="text-label">over the last %d days, %d events</p>'
    ) % (stats["resolved_pct"], RESOLUTION_WINDOW_DAYS, stats["total"])


def _stats_table_html(stats):
    """The demoted resolution-statistics breakdown table only — the
    headline moved to `_resolved_headline_html()` above (D-18). Returns
    the empty string when there is nothing to show (no data yet, or the
    database is unavailable): the promoted headline slot already carries
    that message once, and this demoted tile must not repeat it — the
    caller still wraps this in a `stat_tile()` card regardless, so the
    "Resolution statistics" caption still orients the (in that case,
    empty) card.
    """
    if stats is _DB_UNAVAILABLE or stats["total"] == 0:
        return ""
    return layout.data_table(["Source", "Description", "Count"], stats["rows"])


def render(ctx):
    state_dir = ctx["state_dir"]
    rows = unresolved_rows(state_dir)
    registry_status = coverage_status(rows)

    stats = _safe_query(
        state_dir, lambda conn: resolution_stats(conn, RESOLUTION_WINDOW_DAYS))

    registry_html = layout.stat_tile(
        "Unresolved prefixes", _registry_section(rows), registry_status)
    stats_html = layout.stat_tile(
        "Resolution statistics", _stats_table_html(stats), None)

    return (
        layout.page_header(
            "Airlines",
            purpose="Route-resolution coverage and unresolved callsign prefixes.")
        + _resolved_headline_html(stats)
        + '<div class="dashboard-grid">' + registry_html + stats_html + '</div>'
    )
