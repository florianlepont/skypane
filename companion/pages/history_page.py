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
`data_table()` itself emits, so History's 9-column table matches
Airlines and Health's phone behaviour (D-03) — dropping that wrapper
along with the escaping, when this table was first hand-built, was the
original defect this module now closes.
"""
import sqlite3

from companion.layout import escape_html
import companion.layout as layout
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

_HEADERS = (
    "Timestamp", "Callsign", "Hex", "Aircraft type", "Airline", "Route",
    "State", "Corroboration", "Runway",
)

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


def format_event_row(row):
    """Turn one `runway_events` database row into the display cells this
    page renders. Never raises: every lookup degrades to a documented
    fallback rather than an empty cell or an exception.
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
        "ts": row.get("ts") or "",
        "callsign": row.get("callsign") or "",
        "hex": row.get("hex") or "",
        "aircraft_type_label": aircraft_type_label,
        "airline_label": airline_label,
        "route_label": route_label,
        "confirmed_state": row.get("confirmed_state") or "",
        "corroboration_status": corroboration_status,
        "corroboration_label": corroboration_label,
        "tracked_runway": row.get("tracked_runway") or "",
    }


def _history_table_html(formatted_rows):
    if not formatted_rows:
        return layout.empty_state(_NO_FLIGHTS_HEADING, _NO_FLIGHTS_BODY)

    header_cells = "".join("<th>%s</th>" % escape_html(h) for h in _HEADERS)

    body_rows = []
    for index, cell in enumerate(formatted_rows):
        row_class = "row-alt" if index % 2 else "row"
        cells = (
            '<td class="mono">%s</td>' % escape_html(cell["ts"]),
            '<td class="mono">%s</td>' % escape_html(cell["callsign"]),
            '<td class="mono">%s</td>' % escape_html(cell["hex"]),
            "<td>%s</td>" % escape_html(cell["aircraft_type_label"]),
            "<td>%s</td>" % escape_html(cell["airline_label"]),
            "<td>%s</td>" % escape_html(cell["route_label"]),
            "<td>%s</td>" % escape_html(cell["confirmed_state"]),
            "<td>%s</td>" % layout.status_dot(
                cell["corroboration_status"], cell["corroboration_label"]),
            "<td>%s</td>" % escape_html(cell["tracked_runway"]),
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


def render(ctx):
    state_dir = ctx["state_dir"]
    rows = _safe_query(state_dir, history_rows)

    if rows is _DB_UNAVAILABLE:
        body = '<p class="text-body">%s</p>' % escape_html(_HISTORY_UNAVAILABLE_TEXT)
    else:
        body = _history_table_html([format_event_row(row) for row in rows])

    return '<h1 class="text-heading">History</h1>' + body
