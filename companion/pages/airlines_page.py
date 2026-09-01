"""companion/pages/airlines_page.py — an illustration gallery over the
panel renderer's own airline art (D-13 through D-17, 06.6.4.1-CONTEXT.md).

Presentation-only: reads exactly one public accessor,
`server.plane.illustrations.target_variants_by_airline()`, and touches no
database and no poll-state file — the gallery renders the full static
curated list from `_ILLUSTRATION_TARGETS`, never a detection-history
cross-reference (D-17: this module opens no database and reads no poll
state).

The unresolved-callsign-prefix registry (formerly CFG-04) and the
resolution-rate statistics breakdown (formerly CFG-08) that used to live
on this page moved to `companion/pages/health_page.py` in this same
phase (06.6.4.1, plan 04, D-11/D-12) — that is now the one page in the
app that renders them (D-13). A reader hunting for that content should
look there, not here.

<!-- planner-discipline-allow: history_db -->
<!-- planner-discipline-allow: poll_loop -->
<!-- planner-discipline-allow: sqlite3 -->
(Transiently still imported below, pending this phase's plan 06 Task 3,
which removes them along with the diagnostics functions that reference
them — the imports and functions above are dead code from Task 1 onward,
since render() below no longer calls into them.)
"""
import re
from datetime import datetime, timedelta, timezone

import sqlite3

from companion.layout import empty_state, escape_html
import companion.layout as layout
from server import history_db
from server.plane import illustrations
import server.poll_loop as poll_loop

# D-15: this page's illustration image route mirrors companion/app.py's
# own ILLUSTRATION_IMAGE_ROUTE_PREFIX exactly — duplicated, not imported,
# since app.py imports this module (the reverse import would be a
# cycle). Same duplicated-not-imported discipline this codebase already
# uses for its static-script route constants; pinned by a cross-module
# equality check in companion/test_status_pages.py.
ILLUSTRATION_ROUTE_PREFIX = "/illustration/"

GALLERY_PURPOSE_TEXT = (
    "Illustration reference for every airline this frame can recognize.")

CARD_IMAGE_ALT_TEMPLATE = "%s illustration"

# variant_chip_label()'s two shape-domain patterns. An alphanumeric type
# code is a letter prefix immediately followed by digits, optionally with
# a hyphenated numeric suffix ("a320", "atr72", "a330", "b737",
# "a350-1000"). Anything else is a word-form manufacturer shape
# ("embraer", "beechcraft1900d") — see variant_chip_label()'s own
# docstring for the domain-mismatch trap neither pattern may fall into.
_TYPE_CODE_RE = re.compile(r"^[a-z]+\d[\d-]*$")
_WORD_MODEL_RE = re.compile(r"^([a-z]+)(\d.*)$")


def variant_chip_label(shape):
    """Display transform for one fleet-variant chip
    (06.6.4.1-UI-SPEC.md §7.1). `shape` is a free-text filename suffix
    from `_ILLUSTRATION_TARGETS`, reached only through
    `illustrations.target_variants_by_airline()` — e.g. `"a350-1000"` —
    a DIFFERENT domain from `illustrations.SHAPE_SLUGS`' seven-member
    ICAO-type classification.

    TRAP: this function must never validate `shape` against
    `SHAPE_SLUGS` membership before deciding how (or whether) to render
    it — `"a350-1000"` is a real, live entry that such a check would
    silently drop, since it is not itself a `SHAPE_SLUGS` member (only
    its un-suffixed `"a350"` root is). The branch below is derived from
    the shape string's own form, never from that tuple.

    An alphanumeric type code upper-cases verbatim (`"a320"` ->
    `"A320"`, `"atr72"` -> `"ATR72"`, `"a330"` -> `"A330"`, `"b737"` ->
    `"B737"`, `"a350-1000"` -> `"A350-1000"`). A word-form manufacturer
    shape title-cases instead (`"embraer"` -> `"Embraer"`), splitting a
    trailing digit-led model number into its own word
    (`"beechcraft1900d"` -> `"Beechcraft 1900D"`).
    """
    if not isinstance(shape, str) or not shape:
        return ""
    if _TYPE_CODE_RE.match(shape):
        return shape.upper()
    word_match = _WORD_MODEL_RE.match(shape)
    if word_match:
        word, model = word_match.groups()
        return "%s %s" % (word.title(), model.upper())
    return shape.title()


def _airline_card_html(index, airline_name, shapes):
    """One `.airline-card` (06.6.4.1-UI-SPEC.md §7.1): an image pointing
    at the session-gated `/illustration/{key}.png` route, the airline's
    name, and one chip per fleet-type variant — the chips container is
    omitted entirely (not rendered empty) when `shapes` is empty. Every
    interpolated value — the key inside the URL, the name, each chip
    label, and the alt text — goes through `escape_html()` exactly once,
    at the point of interpolation (T-06.6.4.1-05). Returns the empty
    string (skips the card, never crashes) for an airline whose
    normalised key comes back falsy, mirroring
    `illustrations.target_filenames()`'s own documented skip discipline.

    `index` becomes the card's `data-filter-group` value (D-16/D-20):
    this page renders one representation per airline (no mobile-card
    pairing like History), but `companion/static/list-filter.js` counts
    distinct groups rather than raw elements, so every filterable card
    still needs its own group. `data-filter-text` carries the lower-cased
    airline name, escaped before interpolation into the attribute — the
    same discipline the old registry rows applied to their prefix value.
    """
    key = illustrations.normalise_airline_key(airline_name)
    if not key:
        return ""
    image_html = (
        '<img class="airline-card__image" src="%s%s.png" '
        'loading="lazy" decoding="async" alt="%s">'
    ) % (
        ILLUSTRATION_ROUTE_PREFIX, escape_html(key),
        escape_html(CARD_IMAGE_ALT_TEMPLATE % airline_name),
    )
    chips_html = ""
    if shapes:
        chips = "".join(
            '<span class="airline-card__chip">%s</span>' % escape_html(variant_chip_label(shape))
            for shape in shapes
        )
        chips_html = '<div class="airline-card__chips">%s</div>' % chips
    filter_text = escape_html(
        airline_name.lower() if isinstance(airline_name, str) else str(airline_name).lower())
    return (
        '<div class="airline-card" data-filter-text="%s" data-filter-group="%d">'
        "%s"
        '<p class="airline-card__name">%s</p>'
        "%s"
        "</div>"
    ) % (filter_text, index, image_html, escape_html(airline_name), chips_html)


def _gallery_grid_html(pairs):
    """Wrap one `_airline_card_html()` card per `(airline_name, shapes)`
    pair in the `.illustration-grid` container (06.6.4.1-UI-SPEC.md
    §7.1, companion/static/style.css from plan 01). Skips (renders
    nothing for) any pair whose card comes back empty.
    """
    cards = "".join(
        _airline_card_html(index, airline_name, shapes)
        for index, (airline_name, shapes) in enumerate(pairs))
    return '<div class="illustration-grid">%s</div>' % cards

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

# D-16 (06.6.4.1-UI-SPEC.md §7.2): the gallery's filter-bar copy, driven
# client-side by companion/static/list-filter.js's shared
# [data-filter-input]/[data-filter-count]/[data-filter-clear]/
# [data-filter-empty] attribute contract — the same script History's own
# _filter_bar_html() already consumes, no script change needed here.
# Unlike the retired diagnostics page, this gallery carries no read-only
# constraint, so the Clear control below is a real <button>, matching
# History's variant rather than the old Airlines page's anchor-link one.
_FILTER_INPUT_ID = "airlines-gallery-filter-input"
_FILTER_LABEL_TEXT = "Filter by airline name"
_FILTER_EMPTY_HEADING = "No matching airlines"
_FILTER_EMPTY_BODY_TEMPLATE = (
    "Try a different search, or Clear filter to see all %d airlines.")


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
    """D-16's filter bar over the gallery — History's `<button
    type="button" data-filter-clear>Clear</button>` variant
    (06.6.4.1-UI-SPEC.md §7.2), not the old read-only Airlines page's
    `<a href="#...">` variant: that anchor existed only because the old
    diagnostics page was forbidden any button element (D-16, retired),
    and this gallery carries no such constraint. Entirely inert without
    JS — `companion/static/list-filter.js`'s own early-return guard
    means the full unfiltered card grid underneath stays completely
    usable if the script never loads.
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
        '<button type="button" data-filter-clear>Clear</button>'
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
    # data-filter-group: this page has only one representation per row
    # (no mobile-card pairing like History), but list-filter.js counts
    # distinct groups rather than raw elements, so every filterable row
    # must still carry one.
    return '<tr class="%s" data-filter-text="%s" data-filter-group="%d">%s</tr>' % (
        row_class, filter_text, index, "".join(cells))


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
    """The Airlines gallery (D-13 through D-17): the page header, the
    D-16 filter bar, then one card per airline in
    `illustrations.target_variants_by_airline()` order. `ctx` is accepted
    for call-site parity with every other page module's `render(ctx)`
    signature but is otherwise unused — this page reads one static
    in-memory list, no database and no poll state.

    The filter bar renders only when there is at least one card — this
    codebase's consistent "no chrome with no data" rule — though with a
    static curated list that branch is unreachable today; it stays a
    genuine guard, not a claim that the list can ever be empty.
    """
    pairs = illustrations.target_variants_by_airline()
    filter_html = _filter_bar_html(len(pairs)) if pairs else ""
    return (
        layout.page_header("Airlines", purpose=GALLERY_PURPOSE_TEXT)
        + filter_html
        + _gallery_grid_html(pairs)
    )
