"""companion/pages/history_page.py — CFG-06 (flight-history log),
06-CONTEXT.md D-18.

Completed by plan 06-09. Reads `server.history_db.recent_runway_events()`
and reuses `server.plane.render`'s two presentation-only mappings
(`display_airline_name()`, `_TYPE_DISPLAY_LABELS`) so this page and the
physical panel describe the same flight with the same words — a second,
web-only copy of those mappings would drift the moment a new aircraft
type is added, defeating the point of a QA page that is supposed to show
what the panel shows.

Every database access goes through `_safe_query()` (same shape as
`companion/pages/health_page.py`'s own helper), so a missing or locked
database degrades to the health-unavailable copy instead of raising.

`layout.data_table()` cannot host the Corroboration column's
`layout.status_dot()` markup — `data_table()` escapes every cell value it
is given, and escaping status_dot()'s pre-built `<span>` markup would
print the raw tags as visible text instead of rendering the dot. This
module therefore builds its own table markup (`_history_table_html()`),
matching `data_table()`'s CSS classes exactly for visual consistency,
escaping every other cell through `companion.layout.escape_html()`.
Only the escaping had to be hand-rolled, not the scroll container: this
table is still wrapped in the same horizontal-scroll container
`data_table()` itself emits, so History's 7-column table matches
Airlines and Health's phone behaviour (D-03) — dropping that wrapper
along with the escaping, when this table was first hand-built, was the
original defect this module now closes.

Callsign+Hex and Aircraft type+Airline are each rendered as one merged,
one-line cell (`_merged_cell()`, 06.6.1 D-02/data-density.md sketch 003
Variant B) instead of two separate columns — this cut the table from 9
columns to 7 without changing row height, which is the property that
was chosen over a stacked-cell layout specifically to keep scanning many
rows fast.
"""
import sqlite3

from companion.layout import escape_html
import companion.layout as layout
from server import device_config
from server import history_db
from server.plane import render as panel_render

# D-13 keeps runway_events forever; this is a *display* limit for
# readability, not a retention policy — same distinction the Health
# page's BATTERY_TREND_LIMIT already documents for device_health.
HISTORY_ROW_LIMIT = 50

_NO_FLIGHTS_HEADING = "No flights yet."
_NO_FLIGHTS_BODY = (
    "No flights detected yet — check back after the next poll cycle.")

# Reused verbatim from companion/pages/health_page.py's own
# HEALTH_UNAVAILABLE_TEXT (companion/pages/__init__.py's contract: no
# page module imports another page module, so the string is duplicated
# here rather than imported).
_HISTORY_UNAVAILABLE_TEXT = (
    "Health history is temporarily unavailable — check the companion "
    "service logs.")

# 7 entries, left-to-right order unchanged from the previous 9-column
# table so a returning user's scanning habit still works. "Callsign" and
# "Type" are now merged columns: each carries a secondary value (hex,
# airline) rendered on the same line via _merged_cell() (06.6.1 D-02).
_HEADERS = (
    "Timestamp", "Callsign", "Type", "Route", "State", "Corroboration",
    "Runway",
)

# Class names styled by companion/static/style.css (plan 06.6.1-01, same
# wave). Duplicated here rather than imported because a page module has
# no import path to the stylesheet; companion/test_view_pages.py's
# cross-file drift guard reads style.css from disk and requires all
# three to appear there, so the two cannot silently diverge.
CELL_PRIMARY_CLASS = "cell-primary"
CELL_SECONDARY_CLASS = "cell-secondary"
CELL_SEPARATOR_CLASS = "cell-inline-sep"

# The middle-dot glyph, defined once so the separator can never be typed
# as a hyphen or a bullet at one call site and a middle dot at another.
CELL_SEPARATOR_TEXT = "·"

# history_db's stored corroborated column (the TEXT form of
# True/False/None) mapped to the same three (status, label) pairs
# companion/pages/health_page.py's own _CORROBORATION_ROWS uses (D-15) —
# so the two pages read consistently. An unrecognised/legacy value falls
# back to the warning class rather than a fabricated label.
_CORROBORATION_LABELS = {
    "True": ("ok", "Agreement"),
    "None": ("ok", "Single-source (uncorroborated)"),
    "False": ("warn", "Disagreement"),
}
_DEFAULT_CORROBORATION = ("warn", "Unknown")

_DB_UNAVAILABLE = object()  # Same sentinel discipline as health_page.py:
# distinguishes "query raised" from "query succeeded, legitimately empty".

# UXA-05/06.6.3-RESEARCH.md Pitfall 1: the audit's own evidence names
# "on_runway"/"approaching"/"departed" as the raw confirmed_state values
# leaking into this page, but server/plane/runway_config.py's
# infer_runway_config() - the only function that ever writes a
# confirmed_state value to history_db - only ever produces exactly
# "departing" or "arriving" (or leaves the prior value unchanged). Any
# other non-empty value (a future state this codebase hasn't invented
# yet, or legacy test data) degrades to a title-cased, underscore-
# stripped rendering of the raw string via _confirmed_state_label()
# below, never a bare raw value and never the literal word "None".
_CONFIRMED_STATE_LABELS = {
    "departing": "Departing",
    "arriving": "Arriving",
}


def _confirmed_state_label(raw):
    """Map a runway_events.confirmed_state raw value to its presentation
    label (UXA-05). Falsy input (None or "") renders as an empty string,
    matching the pre-existing empty-cell behaviour this replaces - never
    the literal word "None". A recognised value ("departing"/"arriving")
    maps via _CONFIRMED_STATE_LABELS; anything else falls back to a
    title-cased, underscore-stripped rendering of the raw string
    (06.6.3-RESEARCH.md Pitfall 1's documented fallback), so a future or
    unexpected state still reads as a human label instead of a raw
    machine value.
    """
    if not raw:
        return ""
    label = _CONFIRMED_STATE_LABELS.get(raw)
    if label is not None:
        return label
    return raw.replace("_", " ").title()


def _runway_label(raw):
    """Map a runway_events.tracked_runway raw id to
    server.device_config.runway_label()'s human label (UXA-05), e.g. "3"
    -> "Runway 3 (07/25)". Only ever looks the id up when it is a real
    device_config.RUNWAY_IDS member - an unrecognised id (a stale/
    foreign value on an old row) degrades to the raw id unchanged rather
    than raising, matching this module's "never raise, degrade to a
    documented fallback" discipline throughout. Falsy input renders as
    an empty string, same as before this helper existed.
    """
    if raw and raw in device_config.RUNWAY_IDS:
        return device_config.runway_label(raw)
    return raw or ""


def _safe_query(state_dir, fn):
    try:
        with history_db.open_db(state_dir) as conn:
            return fn(conn)
    except (sqlite3.Error, OSError):
        return _DB_UNAVAILABLE


def history_rows(conn):
    """The most recent `HISTORY_ROW_LIMIT` `runway_events` rows, newest
    first (matches `history_db.recent_runway_events()`'s own ordering).
    """
    return history_db.recent_runway_events(conn, limit=HISTORY_ROW_LIMIT)


def format_event_row(row, now=None):
    """Turn one `runway_events` database row into the display cells this
    page renders. Never raises: every lookup degrades to a documented
    fallback rather than an empty cell or an exception.

    `now` is the reference instant (a UTC ISO-8601 string) used to render
    the Timestamp cell's relative-age suffix; omitting it degrades to an
    absolute-only timestamp rather than raising.
    """
    aircraft_type = row.get("aircraft_type")
    if isinstance(aircraft_type, str) and aircraft_type:
        type_key = aircraft_type.strip().upper()
        aircraft_type_label = panel_render._TYPE_DISPLAY_LABELS.get(type_key, aircraft_type)
    else:
        aircraft_type_label = ""

    airline = row.get("airline")
    airline_label = (
        panel_render.display_airline_name(airline) if airline
        else panel_render.ROUTE_FALLBACK_TEXT)

    origin = row.get("origin")
    destination = row.get("destination")
    route_label = (
        "%s → %s" % (origin, destination) if origin and destination
        else panel_render.ROUTE_FALLBACK_TEXT)

    corroboration_status, corroboration_label = _CORROBORATION_LABELS.get(
        row.get("corroborated"), _DEFAULT_CORROBORATION)

    return {
        # Plain-text "ISO (Nm ago)" form, kept under its own distinct key
        # for any future plain-text-only need (mirrors
        # absolute_and_relative()'s own no-markup contract). No renderer
        # in this module uses this key for the visible Timestamp cell/
        # mobile primary-line time any more - both go through raw_ts +
        # layout.concise_timestamp_html() instead (D-09).
        "ts": layout.absolute_and_relative(row.get("ts"), now, fallback=""),
        # The raw, unformatted ISO timestamp string - the input
        # layout.concise_timestamp_html() needs (it builds its own
        # concise markup from the raw value plus a reference `now`, not
        # from absolute_and_relative()'s already-composed text).
        "raw_ts": row.get("ts") or "",
        "callsign": row.get("callsign") or "",
        "hex": row.get("hex") or "",
        "aircraft_type_label": aircraft_type_label,
        "airline_label": airline_label,
        "route_label": route_label,
        "confirmed_state": _confirmed_state_label(row.get("confirmed_state")),
        "corroboration_status": corroboration_status,
        "corroboration_label": corroboration_label,
        "tracked_runway": _runway_label(row.get("tracked_runway")),
    }


def _merged_cell(primary, secondary):
    """Build one complete `<td>` holding `primary` and, when present, a
    separator and `secondary` on the same line (06.6.1 D-02, sketch 003
    Variant B "Inline compact").

    `secondary` is only rendered when truthy: `format_event_row()`
    legitimately yields an empty string for a missing hex or a missing
    aircraft type, and rendering a separator with nothing after it would
    read as truncated data rather than as absent data. That is the whole
    reason this is a function rather than an inline format string used
    twice.

    Both arguments go through `escape_html()` here and nowhere else — do
    not pre-escape at the call site as well, or values would be
    double-encoded and print their entity forms as visible text (the
    same trap `stat_tile()`'s docstring already documents for
    `content_html`).
    """
    html = '<span class="%s">%s</span>' % (
        CELL_PRIMARY_CLASS, escape_html(primary))
    if secondary:
        html += '<span class="%s">%s</span><span class="%s">%s</span>' % (
            CELL_SEPARATOR_CLASS, escape_html(CELL_SEPARATOR_TEXT),
            CELL_SECONDARY_CLASS, escape_html(secondary))
    return "<td>%s</td>" % html


def _history_table_html(formatted_rows, now=None):
    if not formatted_rows:
        return layout.empty_state(_NO_FLIGHTS_HEADING, _NO_FLIGHTS_BODY)

    header_cells = "".join("<th>%s</th>" % escape_html(h) for h in _HEADERS)

    body_rows = []
    for index, row in enumerate(formatted_rows):
        row_class = "row-alt" if index % 2 else "row"
        # D-09: layout.concise_timestamp_html() already returns
        # already-safe <span class="mono" title="..."> markup - this
        # file hand-rolls its own <td> cells (it does not call
        # layout.data_table()), so the return value is interpolated
        # directly with no wrapping escape_html() call, matching
        # _merged_cell()'s own documented "do not double-escape
        # already-safe markup" discipline.
        cells = (
            "<td>%s</td>" % layout.concise_timestamp_html(row["raw_ts"], now),
            _merged_cell(row["callsign"], row["hex"]),
            _merged_cell(row["aircraft_type_label"], row["airline_label"]),
            "<td>%s</td>" % escape_html(row["route_label"]),
            "<td>%s</td>" % escape_html(row["confirmed_state"]),
            "<td>%s</td>" % layout.status_dot(
                row["corroboration_status"], row["corroboration_label"]),
            "<td>%s</td>" % escape_html(row["tracked_runway"]),
        )
        body_rows.append(
            '<tr class="%s">%s</tr>' % (row_class, "".join(cells)))

    return (
        '<div class="data-table-wrap">'
        '<table class="data-table">'
        "<thead><tr>%s</tr></thead>"
        "<tbody>%s</tbody>"
        "</table>"
        "</div>"
    ) % (header_cells, "".join(body_rows))


def _history_cards_html(formatted_rows, now=None):
    """Mobile compact-card representation (D-07) - one `<li>` per row,
    built from the exact same `formatted_rows` list _history_table_html()
    consumes, never a second independently-derived data pass. Returns
    the empty string for an empty list, so render() shows only the
    unchanged empty_state() block in that case, never an empty
    `<ul class="history-cards">` sitting beside it.

    companion/static/style.css's breakpoint toggle (`.history-cards ~
    .data-table-wrap`) requires this `<ul>` to render as a DOM sibling
    immediately before the desktop table - render() below preserves
    that ordering; do not move this call after _history_table_html()'s.

    Every seven-category UXA-01 acceptance requirement (callsign, time,
    route, state, aircraft/airline, corroboration, runway, hex, full
    timestamp) is reachable: the primary/secondary lines carry
    callsign/time/route/state; the nested `<details>` disclosure carries
    the rest, matching the Battery readings table's own native-disclosure
    pattern (no custom JS toggler).
    """
    if not formatted_rows:
        return ""
    items = []
    for row in formatted_rows:
        # D-09: the identical layout.concise_timestamp_html() call the
        # desktop cell uses (same raw_ts, same now) - the desktop table
        # and the mobile card always render byte-identical timestamp
        # markup for the same row. Already-safe markup, interpolated
        # verbatim, never re-escaped.
        primary = (
            '<div class="history-card__primary">'
            '<span class="cell-primary mono">%s</span>'
            '<span class="history-card__time">%s</span>'
            "</div>"
        ) % (escape_html(row["callsign"]), layout.concise_timestamp_html(row["raw_ts"], now))
        secondary = (
            '<div class="history-card__secondary">'
            "<span>%s</span>"
            "<span>%s</span>"
            "</div>"
        ) % (escape_html(row["route_label"]), escape_html(row["confirmed_state"]))
        details = (
            '<details class="history-card__details">'
            "<summary>More details</summary>"
            "<dl>"
            "<dt>Aircraft</dt><dd>%s %s %s</dd>"
            "<dt>Corroboration</dt><dd>%s</dd>"
            "<dt>Runway</dt><dd>%s</dd>"
            '<dt>Hex</dt><dd class="mono">%s</dd>'
            '<dt>Full timestamp</dt><dd class="mono">%s</dd>'
            "</dl>"
            "</details>"
        ) % (
            escape_html(row["aircraft_type_label"]),
            escape_html(CELL_SEPARATOR_TEXT),
            escape_html(row["airline_label"]),
            layout.status_dot(row["corroboration_status"], row["corroboration_label"]),
            escape_html(row["tracked_runway"]),
            escape_html(row["hex"]),
            escape_html(row["raw_ts"]),
        )
        items.append(
            '<li class="history-card">%s%s%s</li>' % (primary, secondary, details))
    return '<ul class="history-cards">%s</ul>' % "".join(items)


def render(ctx):
    state_dir = ctx["state_dir"]
    now = ctx.get("now") or history_db.utc_now_iso()
    rows = _safe_query(state_dir, history_rows)

    if rows is _DB_UNAVAILABLE:
        body = '<p class="text-body">%s</p>' % escape_html(_HISTORY_UNAVAILABLE_TEXT)
    else:
        formatted_rows = [format_event_row(row, now) for row in rows]
        # Cards render before the table - companion/static/style.css's
        # `.history-cards ~ .data-table-wrap` sibling-combinator toggle
        # (06.6.3-02) depends on this exact DOM order. When formatted_rows
        # is empty, _history_cards_html() returns "" and
        # _history_table_html() alone supplies the unchanged
        # empty_state() block - no empty <ul> alongside it.
        body = (
            _history_cards_html(formatted_rows, now)
            + _history_table_html(formatted_rows, now))

    return layout.page_header("History") + body
