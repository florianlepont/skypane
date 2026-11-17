"""The Flights page's query: which stored flights match a search, a direction
and a sort, how many of each direction match, and the page of them to show.

The search covers the whole history (not just the rows a page shows): the
newest `SCAN_LIMIT` stored events are read, folded the way Home folds them
(a pass stored twice reads as one flight), matched against the same words the
page prints (call sign, hex, airline as displayed, both airport codes and the
aircraft type), then ordered and cut to the requested page. Nothing is written
and the live frame's own reads are untouched.
"""
from collections import namedtuple

import companion.flight_card as flight_card
import companion.history_cache as history_cache
from server import history_db
from server.plane import render as panel_render

Q_PARAM = "q"
KIND_PARAM = "kind"
SORT_PARAM = "sort"
QUERY_MAX_CHARS = 60

KINDS = ("departing", "arriving")
SORT_NEWEST = "newest"
SORT_OLDEST = "oldest"
SORT_AIRLINE = "airline"
SORT_DIRECTION = "direction"
SORTS = (SORT_NEWEST, SORT_OLDEST, SORT_AIRLINE, SORT_DIRECTION)
DEFAULT_SORT = SORT_NEWEST

# The newest stored events read per request: a safety bound on the scan, far
# above what a frame stores in years (a few dozen flights a day).
SCAN_LIMIT = 20000

# The whole stored history folded once: `rows` newest first, and `scanned`,
# the ids of the newest SCAN_LIMIT stored events when more than that are
# stored (else None: every row is within the scan).
Folded = namedtuple("Folded", "rows scanned")
View = namedtuple("View", "q kind sort")
Result = namedtuple(
    "Result", "rows has_more matched counts total")


def parse_view(raw):
    """The validated view from the raw query values (a mapping with the
    optional keys `q`, `kind` and `sort`): the text is trimmed and capped, an
    unknown kind is every direction and an unknown sort is newest first."""
    raw = raw or {}
    text = str(raw.get(Q_PARAM) or "").strip()[:QUERY_MAX_CHARS]
    kind = str(raw.get(KIND_PARAM) or "")
    sort = str(raw.get(SORT_PARAM) or "")
    return View(
        text, kind if kind in KINDS else "", sort if sort in SORTS else DEFAULT_SORT)


def _airline_display(event):
    airline = event.get("airline")
    return panel_render.display_airline_name(airline) if airline else ""


def _haystack(event):
    aircraft_type = event.get("aircraft_type")
    type_label = ""
    if isinstance(aircraft_type, str) and aircraft_type:
        type_label = panel_render._TYPE_DISPLAY_LABELS.get(
            aircraft_type.strip().upper(), aircraft_type)
    parts = (
        event.get("callsign"), event.get("hex"), _airline_display(event),
        event.get("origin"), event.get("destination"), type_label)
    return " ".join(str(part) for part in parts if part).lower()


def _direction(event):
    state = event.get("confirmed_state")
    return state if state in KINDS else ""


def _ordered(events, sort):
    """`events` (newest first) in the requested order; ties keep newest first."""
    if sort == SORT_OLDEST:
        return list(reversed(events))
    if sort == SORT_AIRLINE:
        # Unnamed airlines close the list.
        return sorted(events, key=lambda e: (
            not _airline_display(e), _airline_display(e).casefold()))
    if sort == SORT_DIRECTION:
        rank = {"departing": 0, "arriving": 1}
        return sorted(events, key=lambda e: rank.get(_direction(e), 2))
    return events


def _filtered(flights, view):
    """`(shown, matched, counts)` of the folded `flights` for `view`."""
    words = view.q.lower().split()
    if words:
        found = []
        for event in flights:
            text = _haystack(event)
            if all(word in text for word in words):
                found.append(event)
    else:
        found = flights
    counts = {kind: 0 for kind in KINDS}
    for event in found:
        kind = _direction(event)
        if kind:
            counts[kind] += 1
    shown = [e for e in found if not view.kind or _direction(e) == view.kind]
    return _ordered(shown, view.sort), len(found), counts


def folded_history(conn):
    """Every stored event newest first with repeated passes folded away,
    under the stored airline names. Flights and the Airlines collection both
    read this one cached fold (read only), so a new flight costs one fold
    whatever pages are asked for."""
    def load():
        events = history_db.recent_runway_events(conn, limit=-1)
        scanned = (frozenset(event["id"] for event in events[:SCAN_LIMIT])
                   if len(events) > SCAN_LIMIT else None)
        return Folded(flight_card.fold_repeated_passes(events), scanned)
    return history_cache.cached(conn, ("folded", SCAN_LIMIT), load)


def _flights(conn, airline_names):
    """The folded flights the scan covers, shown under the owner's airline
    names. A renamed row is a copy: the shared fold is never written."""
    folded = folded_history(conn)
    rows = folded.rows
    if folded.scanned is not None:
        rows = [row for row in rows if row["id"] in folded.scanned]
    if not airline_names:
        return rows
    shown = []
    for row in rows:
        name = history_db.override_airline_name(row, airline_names)
        shown.append(row if name is None else dict(row, airline=name))
    return shown


def select(conn, view, pages, page_size, airline_names=None):
    """The flights page for `view`: `rows` (the first `(pages + 1) *
    page_size` matches in the view's order), `has_more`, `matched` (matches
    of the search in every direction, the "All" chip), `counts` (per
    direction) and `total` (every flight stored, whatever the search)."""
    names = tuple(sorted((airline_names or {}).items()))
    # The folded history and each filtered view of it are shared between
    # requests (read only here).
    flights = history_cache.cached(
        conn, ("flights", SCAN_LIMIT, names), lambda: _flights(conn, airline_names))
    shown, matched, counts = history_cache.cached(
        conn, ("flights-view", SCAN_LIMIT, names, view.q, view.kind, view.sort),
        lambda: _filtered(flights, view))
    limit = (pages + 1) * page_size
    return Result(
        shown[:limit], len(shown) > limit, matched, counts, len(flights))
