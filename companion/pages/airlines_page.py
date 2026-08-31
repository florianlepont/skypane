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

# D-20: the filter bar's copy (06.6.3-UI-SPEC.md's Copywriting Contract),
# driven client-side by companion/static/list-filter.js's shared
# [data-filter-input]/[data-filter-count]/[data-filter-clear]/
# [data-filter-empty] attribute contract — this page is the second, not
# the first, consumer of that shared script (companion/pages/
# history_page.py's own _filter_bar_html() is the first); no script
# change is needed here.
_FILTER_INPUT_ID = "airlines-filter-input"
_FILTER_LABEL_TEXT = "Filter by prefix"
_FILTER_EMPTY_HEADING = "No matching prefixes"
_FILTER_EMPTY_BODY_TEMPLATE = (
    "Try a different search, or Clear filter to see all %d prefixes.")


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


def _filter_bar_html(total):
    """D-20's filter bar over the unresolved-prefix registry, only ever
    rendered when there is data to filter (matches _registry_section()'s
    own "no chrome with no data" rule, same as History's precedent).

    D-16 forbids a button element anywhere on this page (History carries
    no such constraint) — the clear control is therefore a plain link
    element pointing at the filter input's own id rather than History's
    submit-type button. `companion/static/list-filter.js`'s
    click-listener attachment (`document.querySelector
    ("[data-filter-clear]")`) does not care which element carries the
    attribute, and a fragment link to the input both scrolls to and
    (per standard browser fragment-navigation behaviour) focuses it in
    one action — a small UX bonus (ready to type the next query) that
    also needs zero new CSS beyond the already-shipped `.filter-bar`
    rules, since this page's `files_modified` scope excludes
    `companion/static/style.css`.
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
    interpolation into the attribute — the same discipline History's own
    `_filter_text_attr()` applies to its callsign+hex value.
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
    return '<tr class="%s" data-filter-text="%s">%s</tr>' % (
        row_class, filter_text, "".join(cells))


def _registry_table_html(rows, now):
    """The unresolved-prefix registry table, hand-rolled (not via
    `layout.data_table()`) so each row can carry its own `data-filter-
    text` attribute — `data_table()` has no per-row attribute hook, and
    extending it with one would touch that builder's other two call
    sites (this page's own resolution-statistics table, and Health's
    battery table) for no benefit to either. This mirrors
    `companion/pages/history_page.py::_history_table_html()`'s own
    precedent for exactly the same reason (its Corroboration column's
    `status_dot()` markup), matching `data_table()`'s CSS classes
    exactly for visual consistency.
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
    status_html = layout.status_dot(coverage_status(rows), "Coverage")
    note_html = '<p class="text-body">%s</p>' % escape_html(_READ_ONLY_NOTE)
    header_html = '<p class="text-body">%s</p>' % status_html + note_html

    if not rows:
        return header_html + empty_state(_NO_GAPS_HEADING, _NO_GAPS_BODY)

    filter_html = _filter_bar_html(len(rows))
    table_html = _registry_table_html(rows, now)
    return header_html + filter_html + table_html


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
    now = ctx.get("now")
    rows = unresolved_rows(state_dir)
    registry_status = coverage_status(rows)

    stats = _safe_query(
        state_dir, lambda conn: resolution_stats(conn, RESOLUTION_WINDOW_DAYS))

    registry_html = layout.stat_tile(
        "Unresolved prefixes", _registry_section(rows, now), registry_status)
    stats_html = layout.stat_tile(
        "Resolution statistics", _stats_table_html(stats), None)

    return (
        layout.page_header(
            "Airlines",
            purpose="Route-resolution coverage and unresolved callsign prefixes.")
        + _resolved_headline_html(stats)
        + '<div class="dashboard-grid">' + registry_html + stats_html + '</div>'
    )
