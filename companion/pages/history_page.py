"""The Flights page: a compact log of the latest aircraft the frame has
shown, built from `server.history_db.recent_runway_events()`, reusing
`server.plane.render`'s presentation-only mappings
(`display_airline_name()`, `_TYPE_DISPLAY_LABELS`) so this page and the
physical panel describe the same flight with the same words.

Every database access goes through `_safe_query()`, so a missing or
locked database degrades to the unavailable copy instead of raising.
`layout.data_table()` escapes every cell value and cannot host the
row-level picture link, so this module builds its own table markup,
matching `data_table()`'s CSS classes and escaping every cell through
`escape_html()`.
"""
import re
import sqlite3
from urllib.parse import urlencode
from datetime import datetime, timezone

import companion.device_scope as device_scope
import companion.flight_card as flight_card
import companion.history_query as history_query
import companion.i18n as i18n
from companion.layout import escape_html
import companion.layout as layout
import companion.page_context as page_context
import companion.prefs as prefs
import companion.ui_components as ui_components
import companion.ui_filter as ui_filter
import companion.ui_groups as ui_groups
from server import history_db
from server.plane import illustrations
from server.plane import name_overrides
from server.plane import render as panel_render

# history is kept forever; this is a display limit for readability,
# not a retention policy.
HISTORY_ROW_LIMIT = 50

# The query parameter that asks for more history: `?more=2` shows the
# newest (2 + 1) * HISTORY_ROW_LIMIT flights. A link, so it works without a
# script; bounded so a hand-edited value cannot ask for the whole table.
MORE_PARAM = "more"
MAX_MORE_PAGES = 19
# The Load more link lands on the first new row. Two links and two ids, one
# per representation: a fragment targets the first element with its id, and
# the representation the viewport hides has no box to scroll to.
_NEW_ROWS_ANCHOR = "flights-new"
_NEW_CARD_ANCHOR = "flights-new-card"
_FORM_ID = "flights_form"

PAGE_TITLE = i18n.msg("nav.flight_history", "Flight history")
LIGHTBOX_ARIA_LABEL = i18n.msg(
    "flights.picture_shown_on_the_frame", "Picture shown on the frame")

_GALLERY_ROUTE_PREFIX = "/gallery/"

# server/poll_loop.py's _save_to_gallery() names each gallery file
# `now_iso.replace(":", "-") + ".png"`, sanitising every colon, not just
# the time portion. A naive full-string reversal would also mangle the
# date portion's own hyphens, so this regex only matches the time+offset
# portion after the first "T".
_GALLERY_TIME_PATTERN = re.compile(
    r"^(\d{2})-(\d{2})-(\d{2})([+-]\d{2})-(\d{2})$")


def _gallery_name_to_iso(name):
    """Reverses `_save_to_gallery()`'s ':' -> '-' filename sanitisation,
    or returns `None` (never raising) on any name that doesn't match the
    expected shape. `matching_gallery_entry()` skips any entry it cannot
    recover a timestamp from.
    """
    stem = name[:-4] if name.endswith(".png") else name
    if "T" not in stem:
        return None
    date_part, _, time_part = stem.partition("T")
    match = _GALLERY_TIME_PATTERN.match(time_part)
    if not match:
        return None
    hh, mm, ss, tz_sign_hh, tz_mm = match.groups()
    return "%sT%s:%s:%s%s:%s" % (date_part, hh, mm, ss, tz_sign_hh, tz_mm)


# Shared with home_page.py's own NO_FLIGHTS_HEADING — the same id, since
# both pages showed the identical English heading through the old flat
# CATALOG namespace.
_NO_FLIGHTS_HEADING = i18n.msg("home.no_flights_yet", "No flights yet.")
_NO_FLIGHTS_BODY = i18n.msg(
    "flights.no_flights_detected_yet_check_back_after_the",
    "No flights detected yet — check back after the next poll cycle.")

# Duplicated from health_page.py's HEALTH_UNAVAILABLE_TEXT rather than
# imported: page modules cannot import each other.
_HISTORY_UNAVAILABLE_TEXT = i18n.msg(
    "flights.the_flight_list_is_temporarily_unavailable_try",
    "The flight list is temporarily unavailable — try again in a minute.")

# Four data columns plus a picture column. "When" and "Flight" are
# two-part cell-primary/secondary cells (_merged_cell()); the picture
# column's header is visually hidden, since the link names itself.
#
# "Flight" is owned by companion/i18n_fr/rules.py — declared here since
# this page reads it, with the id that catalogue's own migration derives
# for the same English text (msg() is idempotent on a repeat (id,
# English) pair).
_HEADER_WHEN_TEXT = i18n.msg("flights.when", "When")
_HEADER_FLIGHT_TEXT = i18n.msg("rules.flight", "Flight")
_HEADER_ROUTE_TEXT = i18n.msg("flights.route", "Route")
_HEADER_STATE_TEXT = i18n.msg("flights.state", "State")
_HEADERS = (
    _HEADER_WHEN_TEXT, _HEADER_FLIGHT_TEXT, _HEADER_ROUTE_TEXT,
    _HEADER_STATE_TEXT,
)
_TABLE_COLUMN_COUNT = len(_HEADERS) + 1

# The visually-hidden header naming the picture column.
_PICTURE_HEADER_TEXT = i18n.msg("flights.picture", "Picture")

# "%s" is the row's callsign (or fallback): a page of ~50 identical
# "View picture" links would otherwise share one accessible name.
_VIEW_PICTURE_OF_TEMPLATE = i18n.msg("flights.view_picture_of", "View picture of %s")

# Names the .data-table-wrap scroller for keyboard users: tabindex="0"
# plus this label turn the wrapper into a focusable, named region a
# keyboard user can Tab to and arrow-scroll.
SCROLLER_ARIA_LABEL = i18n.msg(
    "flights.recent_flights_table_scrollable", "Recent flights table, scrollable")

# Class names styled by style.css. Duplicated here rather than imported
# (a page module has no import path to the stylesheet); a cross-file
# drift guard reads style.css from disk and requires all three there.
CELL_PRIMARY_CLASS = "cell-primary"
CELL_SECONDARY_CLASS = "cell-secondary"
CELL_SEPARATOR_CLASS = "cell-inline-sep"

# Defined once so the separator can never be typed as a hyphen at one
# call site and a middle dot at another.
CELL_SEPARATOR_TEXT = "·"

_DB_UNAVAILABLE = object()  # Same sentinel discipline as health_page.py:
# distinguishes "query raised" from "query succeeded, legitimately empty".

# Driven client-side by list-filter.js's shared data-filter-* attribute
# contract. No hyphen in this id: WebKit/Safari renders a contacts
# autofill suggestion for a name-less search input whose id contains a
# hyphen, and ignores autocomplete="off" in that case — the underscore
# form is safe since the documented trigger is the hyphen character
# specifically.
_FILTER_INPUT_ID = "history_filter_input"
_FILTER_PLACEHOLDER_TEXT = i18n.msg(
    "flights.search_placeholder", "Callsign, airline, airport…")
_FILTER_CHIPS_LEGEND = i18n.msg("flights.filter_direction", "Filter by direction")
_CHIP_ALL_TEXT = i18n.msg("flights.chip_all", "All")
_CHIP_DEPARTURES_TEXT = i18n.msg("flights.chip_departures", "Departures")
_CHIP_ARRIVALS_TEXT = i18n.msg("flights.chip_arrivals", "Arrivals")
_FILTER_LABEL_TEXT = i18n.msg(
    "flights.filter_flights", "Filter flights")
_FILTER_EMPTY_HEADING = i18n.msg("flights.no_matching_flights", "No matching flights")
_FILTER_EMPTY_BODY_TEMPLATE = i18n.msg(
    "flights.try_a_different_search_or_clear_filter_to_see",
    "Try a different search, or Clear filter to see all %d flights.")
_SORT_LABEL = i18n.msg("flights.sort_by", "Sort by")
_SORT_TEXTS = (
    (history_query.SORT_NEWEST, i18n.msg("flights.sort_newest", "Newest first")),
    (history_query.SORT_OLDEST, i18n.msg("flights.sort_oldest", "Oldest first")),
    (history_query.SORT_AIRLINE, i18n.msg("flights.sort_airline", "Airline")),
    (history_query.SORT_DIRECTION, i18n.msg("flights.sort_direction", "Direction")),
)
_APPLY_TEXT = i18n.msg("flights.apply_filters", "Apply")
_MATCHES_TEXT = i18n.msg("flights.matches_many", "%d flights match")
_MATCH_ONE_TEXT = i18n.msg("flights.matches_one", "1 flight matches")
_NO_MATCH_TEXT = i18n.msg("flights.matches_none", "No flight matches")
_TOTAL_TEXT = i18n.msg("flights.count_many", "%d flights")
_TOTAL_ONE_TEXT = i18n.msg("flights.count_one", "1 flight")
_TOTAL_NONE_TEXT = i18n.msg("flights.count_none", "No flights")

# The presentational note shown beside a promoted hex when a row has no
# callsign: a module-level constant so the desktop cell and the mobile
# card can't drift onto two different wordings.
NO_CALLSIGN_NOTE_TEXT = i18n.msg("flights.no_callsign", "no callsign")


def _row_name(callsign, hex_value):
    """The value substituted for the `%s` in `_VIEW_PICTURE_OF_TEMPLATE`:
    the row's callsign, falling back to its hex and finally to
    `NO_CALLSIGN_NOTE_TEXT`, so a row with neither never leaves the
    accessible name with a dangling "of ".
    """
    return callsign or hex_value or i18n.t(NO_CALLSIGN_NOTE_TEXT)


# The stable identity of the event a row describes, rendered into
# layout.REFRESH_ROW_ID_ATTR on both of this page's row elements.
# `runway_events.id` is assigned once and never reused, unlike the loop
# counter, which renumbers whenever a newer
# detection arrives at the top. The `e` prefix keeps the value an
# opaque token, read back by freshness.js as an object key. Degrades,
# never raises: a row with no integer id falls back to its timestamp
# and hex, stable for the same row across renders; a collision
# suppresses a highlight rather than inventing one.
def _row_identity(row):
    event_id = row.get("event_id")
    if isinstance(event_id, int):
        return "e%d" % event_id
    return "t%s-%s" % (row.get("raw_ts") or "", row.get("hex") or "")


LIGHTBOX_DIALOG_ID = "panel-lookup-dialog"
LIGHTBOX_CAPTION_TEMPLATE = i18n.msg("flights.picture_from", "Picture from %s")
# LIGHTBOX_DIALOG_ID and the three data-view-panel-* attribute names
# below must equal panel-lookup.js's own literals exactly (duplicated,
# not imported: a page module has no import path to a static script),
# pinned by test_view_pages.py's three-file DOM-contract guard.
_VIEW_PANEL_SRC_ATTR = "data-view-panel-src"
_VIEW_PANEL_CAPTION_ATTR = "data-view-panel-caption"
_VIEW_PANEL_CLOSE_ATTR = "data-view-panel-close"

# Shared with home_page.py's own DAY_BAND_HEADING — "Today" is owned by
# companion/i18n_fr/flights.py, not home.py.
_DAY_TODAY_LABEL = i18n.msg("flights.today", "Today")
_DAY_YESTERDAY_LABEL = i18n.msg("flights.yesterday", "Yesterday")

VIEW_PICTURE_LABEL = i18n.msg("flights.view_picture", "View picture")

# Shown for a selected device that has no recorded flights yet.
DEVICE_EMPTY_HEADING = i18n.msg(
    "flights.device_empty_heading", "No history for this frame yet")
DEVICE_EMPTY_BODY = i18n.msg(
    "flights.device_empty_body",
    "Flights and checks appear here after the first poll.")

# The phone card's artwork, route and time pieces are shared with Home's
# recent-flight tiles through companion/flight_card.py.
ILLUSTRATION_ROUTE_PREFIX = flight_card.ILLUSTRATION_ROUTE_PREFIX
ROUTE_FALLBACK_TEXT = flight_card.ROUTE_FALLBACK_TEXT

# A missing airline gets its own fallback text, distinct from
# panel_render.ROUTE_FALLBACK_TEXT, so the same phrase doesn't appear
# twice in one unresolved row (Type+Airline cell and Route cell).
AIRLINE_FALLBACK_TEXT = i18n.msg("flights.airline_unknown", "Airline unknown")

# server/plane/runway_config.py is the only writer of confirmed_state: it
# produces "departing" or "arriving", and "overhead" for a level aircraft
# in position mode. Any other non-empty value degrades to a title-cased,
# underscore-stripped rendering via _confirmed_state_label() below.
# "Departing"/"Arriving" are owned by companion/i18n_fr/home.py, not
# flights.py — the same ids home_page.py's own direction text uses.
_CONFIRMED_STATE_LABELS = {
    "departing": i18n.msg("home.departing", "Departing"),
    "arriving": i18n.msg("home.arriving", "Arriving"),
    "overhead": i18n.msg("home.overhead", "Overhead"),
}


def _confirmed_state_label(raw):
    """Maps a runway_events.confirmed_state raw value to its
    presentation label, already translated for the current request.
    Falsy input renders as an empty string, never the literal word
    "None". A recognised value maps via `_CONFIRMED_STATE_LABELS` (a
    Message, translated here); anything else falls back to a
    title-cased, underscore-stripped rendering of the raw value itself
    — not a Message (its text is data-dependent, not a fixed catalogue
    entry), so it is never passed to i18n.t(), exactly as it was never
    found in the legacy catalogue either.
    """
    if not raw:
        return ""
    label = _CONFIRMED_STATE_LABELS.get(raw)
    if label is not None:
        return i18n.t(label)
    return raw.replace("_", " ").title()


# The poll cycle that records a flight is also the one that archives the
# render showing it, so a render that belongs to a flight is stamped within
# a few seconds of it. A render outside this window shows some other
# moment, however close in time it looks.
GALLERY_MATCH_BEFORE_S = 90
GALLERY_MATCH_AFTER_S = 10


def matching_gallery_entry(entries, row_ts):
    """The `(filename, iso)` pair from `entries` archived within the match
    window of `row_ts` (closest first), or `None` when no archived render
    can belong to that flight. Comparison is always between parsed
    timezone-aware `datetime` values, never raw strings: gallery filenames
    carry a local UTC offset while history timestamps are UTC-suffixed, so a
    lexicographic compare would mis-rank across an offset boundary.
    """
    if not row_ts:
        return None
    try:
        row_dt = datetime.fromisoformat(row_ts)
    except ValueError:
        return None

    best = None
    best_gap = None
    for name in entries or []:
        iso = _gallery_name_to_iso(name)
        if iso is None:
            continue
        try:
            gap = (row_dt - datetime.fromisoformat(iso)).total_seconds()
        except (ValueError, TypeError):
            continue
        if not -GALLERY_MATCH_AFTER_S <= gap <= GALLERY_MATCH_BEFORE_S:
            continue
        if best_gap is None or abs(gap) < best_gap:
            best = (name, iso)
            best_gap = abs(gap)
    return best


def lightbox_caption_text(iso):
    """The lightbox caption for a gallery entry's ISO timestamp: a
    humanised local-time form ("Picture from 3 Sep 23:38"), falling
    back to the raw ISO value when it does not parse. Plain text;
    callers escape it. The day/month prefix is built here (rather than
    through `local_clock_text()`'s own day/month branch, which never
    runs without a `now`) using the same `prefs.current_lang()`
    membership test that function applies internally.
    """
    parsed = layout.parse_iso(iso)
    if parsed is None:
        return i18n.t(LIGHTBOX_CAPTION_TEMPLATE) % iso
    local = parsed.astimezone(layout.LOCAL_TZ) if parsed.tzinfo else parsed
    month_abbr = layout._MONTH_ABBR_FR if prefs.current_lang() == "fr" else layout._MONTH_ABBR
    when = "%d %s %s" % (
        local.day, month_abbr[local.month - 1], layout.local_clock_text(parsed, None))
    return i18n.t(LIGHTBOX_CAPTION_TEMPLATE) % when


def _view_panel_attrs(name, iso, row_name):
    """The attributes both picture-link variants share: the real
    `/gallery/` href, the two `data-view-panel-*` trigger attributes
    panel-lookup.js reads, and the per-row accessible name.
    """
    src = escape_html(device_scope.scoped(_GALLERY_ROUTE_PREFIX + name))
    caption = lightbox_caption_text(iso)
    return 'href="%s" %s="%s" %s="%s" aria-label="%s"' % (
        src,
        _VIEW_PANEL_SRC_ATTR, src,
        _VIEW_PANEL_CAPTION_ATTR, escape_html(caption),
        escape_html(i18n.t(_VIEW_PICTURE_OF_TEMPLATE) % row_name),
    )


def _view_panel_link_html(name, iso, row_name):
    """The table row's "View picture" action: a real link to the archived
    render, so it works without script. panel-lookup.js, when present,
    intercepts the click and shows the same image in the shared
    lightbox instead. `name` becomes the link target and the trigger
    source attribute; `iso` is formatted through
    `LIGHTBOX_CAPTION_TEMPLATE` into the caption attribute, which
    `panel-lookup.js` copies verbatim into the lightbox caption on open.
    The visible text is contained in the accessible name, which adds the
    row's callsign.
    """
    return '<a class="btn btn--secondary flight-picture-link" %s>%s</a>' % (
        _view_panel_attrs(name, iso, row_name),
        escape_html(i18n.t(VIEW_PICTURE_LABEL)),
    )


def _view_panel_thumb_html(name, iso, row_name):
    """The phone row's lead control: the same real link and trigger attributes as
    `_view_panel_link_html()`, drawn as the archived render's 40px thumbnail. The image
    carries no text of its own, so the `aria-label` (which names the call
    sign) alone names the control.
    """
    src = escape_html(device_scope.scoped(_GALLERY_ROUTE_PREFIX + name))
    return (
        '<a class="history-card__thumb" %s>'
        '<img class="history-card__thumb-image" src="%s" alt="" width="40" height="40" '
        'loading="lazy" decoding="async" fetchpriority="low">'
        '</a>'
    ) % (_view_panel_attrs(name, iso, row_name), src)


def _stand_in_thumb_html(row, state_dir):
    """The phone row's lead when no archived render belongs to the flight:
    the airline's own illustration when it has one, else a neutral plane
    icon. Neither is a link, so nothing claims to be a picture of the flight."""
    airline = row.get("airline_raw")
    key = illustrations.normalise_airline_key(airline) if airline else None
    if key and illustrations.resolved_illustration_path(key, state_dir):
        src = escape_html(device_scope.scoped(
            flight_card.ILLUSTRATION_ROUTE_PREFIX + key + ".png"))
        return (
            '<span class="history-card__thumb history-card__thumb--illustration">'
            '<img class="history-card__thumb-image" src="%s" alt="" width="40" '
            'height="40" loading="lazy" decoding="async" fetchpriority="low"></span>'
        ) % src
    return (
        '<span class="history-card__thumb history-card__thumb--none" '
        'aria-hidden="true">%s</span>' % layout.icon_html("icon-plane", 20))


# Owned by companion/i18n_fr/airlines.py, not flights.py — the same id
# airlines_page.py's own lightbox close button uses.
_CLOSE_TEXT = i18n.msg("airlines.close", "Close")


def _lightbox_html():
    """The single shared lightbox `<dialog>`, emitted once per page by
    `render()`, only when at least one row carries a trigger button.
    Its image src/alt and caption text are written by
    `panel-lookup.js` on trigger click; this function only emits the
    empty shell and the close button.
    """
    return (
        '<dialog class="lightbox lightbox--picture" id="%s" aria-label="%s">'
        '<img class="lightbox__image" alt="">'
        '<p class="lightbox__caption text-label"></p>'
        '<button type="button" class="btn btn--secondary" %s>%s</button>'
        "</dialog>"
    ) % (LIGHTBOX_DIALOG_ID, escape_html(i18n.t(LIGHTBOX_ARIA_LABEL)),
         _VIEW_PANEL_CLOSE_ATTR, escape_html(i18n.t(_CLOSE_TEXT)))


def _safe_query(state_dir, fn):
    try:
        with history_db.open_db(state_dir) as conn:
            return fn(conn)
    except (sqlite3.Error, OSError):
        return _DB_UNAVAILABLE


def more_pages(raw):
    """The `?more=` value as a page count in [0, MAX_MORE_PAGES]; anything
    that is not a plain non-negative integer is 0."""
    text = str(raw or "").strip()
    if not text.isdigit() or len(text) > 3:
        return 0
    return min(int(text), MAX_MORE_PAGES)


def history_result(conn, view, pages, airline_names=None):
    """The page of flights for `view` (the search, direction and sort the
    address carries) and `pages` Load more steps: see `history_query.select`.
    Storage keeps every event; a pass stored twice is one flight here, as on
    Home."""
    return history_query.select(conn, view, pages, HISTORY_ROW_LIMIT, airline_names)


def view_href(view, pages=0, anchor=""):
    """The Flights address for `view` and `pages` Load more steps, under the
    current device's prefix. Defaults are left out, so the plain page keeps
    its plain address."""
    params = []
    if view.q:
        params.append((history_query.Q_PARAM, view.q))
    if view.kind:
        params.append((history_query.KIND_PARAM, view.kind))
    if view.sort != history_query.DEFAULT_SORT:
        params.append((history_query.SORT_PARAM, view.sort))
    if pages:
        params.append((MORE_PARAM, str(pages)))
    path = layout.FLIGHTS_ROUTE + ("?" + urlencode(params) if params else "")
    return device_scope.scoped(path + ("#" + anchor if anchor else ""))


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
    # Kept in English here: callers compare this against
    # AIRLINE_FALLBACK_TEXT to decide whether to append the
    # unresolved-airline link, and i18n.t() applies at their render
    # sites, so that comparison never crosses a translated string.
    airline_label = (
        panel_render.display_airline_name(airline) if airline
        else AIRLINE_FALLBACK_TEXT)

    origin = row.get("origin")
    destination = row.get("destination")
    route_label = (
        "%s → %s" % (origin, destination) if origin and destination
        else i18n.t(ROUTE_FALLBACK_TEXT))

    return {
        # The runway_events row's own integer primary key, so
        # _row_identity() can name the event rather than its position
        # in this render. .get() rather than []: this function never
        # raises on a partial row.
        "event_id": row.get("id"),
        # Plain-text "ISO (Nm ago)" form, kept for any future
        # plain-text-only need; no renderer uses this key for the
        # visible timestamp any more (both go through raw_ts instead).
        "ts": layout.absolute_and_relative(row.get("ts"), now, fallback=""),
        "raw_ts": row.get("ts") or "",
        "callsign": row.get("callsign") or "",
        "hex": row.get("hex") or "",
        "aircraft_type_label": aircraft_type_label,
        "airline_label": airline_label,
        # The raw stored airline string, kept beside the display label
        # because the phone card's thumbnail keys on it:
        # flight_card.art_html() resolves on the raw
        # value, never the aliased display name.
        "airline_raw": row.get("airline") or "",
        "route_label": route_label,
        # The two codes on their own, for the phone card's route line.
        "origin": origin or "",
        "destination": destination or "",
        "confirmed_state": _confirmed_state_label(row.get("confirmed_state")),
        # The raw stored state, so the phone card can tell which end of
        # the route is the home airport without comparing translations.
        "state_raw": row.get("confirmed_state") or "",
    }


def _merged_cell(primary, secondary):
    """Builds one complete `<td>` holding `primary` and, when present, a
    separator and `secondary` on the same line. `secondary` renders only
    when truthy: `format_event_row()` can yield an empty string for a
    missing hex or aircraft type, and a separator with nothing after it
    would read as truncated data. Both arguments go through
    `escape_html()` here and nowhere else — do not pre-escape at the
    call site too, or values would double-encode.
    """
    html = '<span class="%s">%s</span>' % (
        CELL_PRIMARY_CLASS, escape_html(primary))
    if secondary:
        html += '<span class="%s">%s</span><span class="%s">%s</span>' % (
            CELL_SEPARATOR_CLASS, escape_html(CELL_SEPARATOR_TEXT),
            CELL_SECONDARY_CLASS, escape_html(secondary))
    return "<td>%s</td>" % html


def _filter_text_attr(row):
    """The escaped, lowercased words a row answers to (call sign, hex,
    airline as displayed, both route codes, aircraft type), carried on the
    desktop `<tr>` and the phone `<li>` of the same flight. The server's own
    search matches the same words (`history_query`); the unresolved-airline
    fallback wording is never among them."""
    airline = "" if row["airline_label"] == AIRLINE_FALLBACK_TEXT else row["airline_label"]
    parts = (
        row["callsign"], row["hex"], airline, row.get("origin", ""),
        row.get("destination", ""), row["aircraft_type_label"])
    return escape_html(" ".join(p for p in parts if p).lower())


def _filter_kind_attr(row):
    """The row's `data-filter-kind`: the runway direction the detector
    confirmed. Only departing and arriving count; anything else, an overhead
    row included, belongs to "All" alone."""
    state = row.get("state_raw") or ""
    return state if state in history_query.KINDS else ""


def _row_facts(row, index):
    """The attributes both representations of one flight share: its words, its
    direction, its loop index and its stable identity."""
    return 'data-filter-text="%s" data-filter-kind="%s" data-filter-group="%d" %s="%s"' % (
        _filter_text_attr(row), _filter_kind_attr(row), index,
        layout.REFRESH_ROW_ID_ATTR, escape_html(_row_identity(row)))


def paris_day(raw_ts):
    """The Europe/Paris calendar date a stored timestamp falls on, or
    `None` (never raising) for a falsy or unparseable value.
    `layout.LOCAL_TZ` is the same zone `layout.local_clock_text()`
    converts to; a naive datetime is taken as UTC, since that's what
    `history_db.utc_now_iso()` produces.
    """
    parsed = layout.parse_iso(raw_ts)
    if parsed is None:
        return None
    try:
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(layout.LOCAL_TZ).date()
    except (ValueError, OverflowError, OSError):
        return None


def day_label(day, today):
    """The day-separator's label: "Today", "Yesterday", or an absolute
    date. The absolute form uses `layout.month_abbr()`, the same table
    `local_clock_text()`'s cross-day branch uses, never a second date
    path. `today` may be `None`, in which case every group falls to its
    absolute label rather than raising.
    """
    if today is not None:
        if day == today:
            return i18n.t(_DAY_TODAY_LABEL)
        if (today - day).days == 1:
            return i18n.t(_DAY_YESTERDAY_LABEL)
    return "%d %s" % (day.day, layout.month_abbr(day.month))


def _flight_cell_html(row):
    """The desktop Flight column's cell: `_merged_cell()`'s primary slot
    carries the airline and the secondary slot the aircraft type, so the
    rendered cell reads "Air France · A320"; the call sign is not shown (it
    stays searchable and in the picture link's name). An unresolved airline reads as plain
    unidentified wording, with no link, for every viewer.
    """
    is_unresolved = row["airline_label"] == AIRLINE_FALLBACK_TEXT
    airline_display = i18n.t(row["airline_label"]) if is_unresolved else row["airline_label"]
    cell = _merged_cell(airline_display, row["aircraft_type_label"])
    ident = _row_ident_html(row) if row["callsign"] else ""
    return cell.replace("<td>", "<td>" + ident, 1)


def _chips_html(view):
    """The direction chips: radios of the search form (`kind`), labelled only
    with the direction. The number of flights stays in the screen-reader line
    under the controls."""
    chips = (
        ("", i18n.t(_CHIP_ALL_TEXT)),
        ("departing", i18n.t(_CHIP_DEPARTURES_TEXT)),
        ("arriving", i18n.t(_CHIP_ARRIVALS_TEXT)),
    )
    parts = []
    for kind, text in chips:
        parts.append(
            '<label class="filter-chip"><input type="radio" class="visually-hidden" '
            'name="%s" value="%s" form="%s"%s data-flights-auto data-flights-key="kind-%s">'
            '<span class="filter-chip__box">'
            '<span class="filter-chip__text">%s</span></span></label>' % (
                history_query.KIND_PARAM, kind, _FORM_ID,
                " checked" if kind == view.kind else "", kind or "all",
                escape_html(text)))
    return ('<fieldset class="filter-bar__chips" data-tabs="flights"><legend class="visually-hidden">%s</legend>'
            "%s</fieldset>") % (escape_html(i18n.t(_FILTER_CHIPS_LEGEND)), "".join(parts))


def _sort_html(view):
    """The sort as the shared radio menu of the search form: it works without a
    script (the Apply button sends it) and with one it reorders in place."""
    return ui_filter.sort_menu_html(
        history_query.SORT_PARAM, _SORT_TEXTS, view.sort, _SORT_LABEL,
        ' form="%s" data-flights-auto data-flights-key="sort"' % _FORM_ID,
        ' data-flights-key="sort"')


def _matches_html(view, result):
    """How many flights the page lists in all (the chosen direction's, when
    one is chosen): "N flights match" while a search is typed, else just
    "N flights". Read out by screen readers only: the sighted reader has the
    chips carry no number, and a visible line here would push the list down
    whenever a search opens."""
    many, one, none = (
        (_MATCHES_TEXT, _MATCH_ONE_TEXT, _NO_MATCH_TEXT) if view.q
        else (_TOTAL_TEXT, _TOTAL_ONE_TEXT, _TOTAL_NONE_TEXT))
    listed = result.counts[view.kind] if view.kind else result.matched
    if listed == 0:
        text = i18n.t(none)
    elif listed == 1:
        text = i18n.t(one)
    else:
        text = i18n.t(many) % listed
    return '<p class="visually-hidden" data-filter-count data-flights-view role="status">%s</p>' % (
        escape_html(text))


def _controls_html(view, result):
    """The direction chips and the sort under the title, plus the Apply
    button that stands in for their change handler when no script runs."""
    return (
        '<div class="filter-bar filter-bar--chips history-controls" data-flights-view>%s%s'
        '<button type="submit" class="history-controls__apply" form="%s">%s</button>'
        "</div>%s"
    ) % (_chips_html(view), _sort_html(view), _FORM_ID,
         escape_html(i18n.t(_APPLY_TEXT)), _matches_html(view, result))


def _empty_html(view, result):
    """The card shown when the search or the direction matches nothing: the
    heading, the body quoting how many flights the whole history holds and a
    Clear link (a plain address, so it works without a script) that drops the
    search and the direction and keeps the sort."""
    clear = view_href(history_query.View("", "", view.sort))
    return ui_filter.filter_empty_html(
        i18n.t(_FILTER_EMPTY_HEADING), i18n.t(_FILTER_EMPTY_BODY_TEMPLATE) % result.total,
        ui_components.button_html(
            i18n.t(ui_filter.FILTER_CLEAR_TEXT), "secondary", href=clear, attrs=" data-flights-clear"),
        "data-flights-empty data-flights-view")


# Mirrors layout.concise_timestamp_html()'s own default fallback string
# exactly, so a caller can't tell the two functions apart by their
# empty-value behaviour. Owned by companion/i18n_fr/flights.py, not
# home.py — the same id home_page.py's own clock-cell fallback uses.
_CLOCK_CELL_FALLBACK = i18n.msg("flights.no_reading_yet", "no reading yet")


def _when_cell_html(raw_ts, now):
    """The desktop table's When column cell: two stacked lines via
    `_merged_cell()`, never an inline suffix. A local clock primary line
    ("HH:MM", or "D Mon HH:MM" once the row is no longer from today) and
    a relative-age secondary line. Degrades gracefully: a falsy `raw_ts` renders the fallback
    text with no secondary; an unparseable one renders the raw value the
    same way. Never raises.

    The has-age branch bypasses `_merged_cell()` (kept untouched, and
    still called for the fallback/unparseable branches above): the
    secondary half is built inline from `layout.relative_time_html()`'s
    own pre-escaped `<time data-relative>` markup, using the same span
    classes and separator `_merged_cell()` emits, so a ticker script can
    find and update it. Only the primary clock half is escaped here —
    the age half is never re-escaped, matching `home_page.
    _recent_flight_time_html()`'s build-and-concatenate precedent.
    """
    if not raw_ts:
        html = _merged_cell(i18n.t(_CLOCK_CELL_FALLBACK), "")
    else:
        parsed = layout.parse_iso(raw_ts)
        if parsed is None:
            html = _merged_cell(raw_ts, "")
        else:
            now_parsed = layout.parse_iso(now)
            clock_text = layout.local_clock_text(parsed, now_parsed)
            age = layout.age_seconds(raw_ts, now)
            if age is None:
                html = _merged_cell(clock_text, "")
            else:
                html = (
                    '<td><span class="%s">%s</span>'
                    '<span class="%s">%s</span>'
                    '<span class="%s">%s</span></td>'
                ) % (
                    CELL_PRIMARY_CLASS, escape_html(clock_text),
                    CELL_SEPARATOR_CLASS, escape_html(CELL_SEPARATOR_TEXT),
                    CELL_SECONDARY_CLASS, layout.relative_time_html(raw_ts, now))
    return html


def _day_separator_row_html(day, today):
    """One day-separator row: a real table row spanning the table as a
    `<th scope="colgroup">`, carrying the day's label. Deliberately not
    sticky: this function introduces no positioning of any kind.
    """
    return (
        '<tr class="flight-day-row" data-filter-day>'
        '<th scope="colgroup" colspan="%d" class="text-label">%s</th>'
        "</tr>"
    ) % (_TABLE_COLUMN_COUNT, escape_html(day_label(day, today)))


def _history_table_html(formatted_rows, now=None, anchor_index=None, dated=True):
    if not formatted_rows:
        return ui_groups.group_panel(layout.empty_state(
            i18n.t(_NO_FLIGHTS_HEADING), i18n.t(_NO_FLIGHTS_BODY), compact=True))

    # The last <th> is the visually-hidden "Picture" header: no data
    # column behind it, so built directly here rather than through the
    # _HEADERS/i18n.t(h) loop.
    header_cells = "".join("<th>%s</th>" % escape_html(i18n.t(h)) for h in _HEADERS)
    header_cells += '<th><span class="visually-hidden">%s</span></th>' % escape_html(
        i18n.t(_PICTURE_HEADER_TEXT))

    # `today` is the page's reference instant as a Europe/Paris calendar
    # date, so "Today"/"Yesterday" mean what a reader in Paris means.
    today = paris_day(now)
    current_day = None

    body_rows = []
    for index, row in enumerate(formatted_rows):
        # A row whose timestamp cannot be dated takes the ungrouped
        # path: no separator is emitted and the current group stays
        # open, so it never splits a real day in two.
        day = paris_day(row["raw_ts"]) if dated else None
        if day is not None and day != current_day:
            current_day = day
            body_rows.append(_day_separator_row_html(day, today))

        row_class = "row-alt" if index % 2 else "row"
        # When/Flight already return already-safe, fully-built
        # <td>...</td> markup, interpolated directly, never re-escaped.
        cells = (
            _when_cell_html(row["raw_ts"], now),
            _flight_cell_html(row),
            "<td>%s</td>" % escape_html(row["route_label"]),
            "<td>%s</td>" % escape_html(row["confirmed_state"]),
            "<td>%s</td>" % row.get("view_panel_html", ""),
        )
        # The stable event identity lets the refresh loop tell a new row from
        # one that only moved; the row at `anchor_index` is where the no-script
        # Load more link lands.
        body_rows.append(
            '<tr class="%s" data-flight-row %s%s>%s</tr>'
            % (row_class, _row_facts(row, index),
               ' id="%s"' % _NEW_ROWS_ANCHOR if index == anchor_index else "",
               "".join(cells)))

    return (
        '<div class="data-table-wrap" data-flights-view tabindex="0" role="region" '
        'aria-label="%s">'
        '<table class="data-table data-table--flights">'
        "<thead><tr>%s</tr></thead>"
        "<tbody>%s</tbody>"
        "</table>"
        "</div>"
    ) % (escape_html(i18n.t(SCROLLER_ARIA_LABEL)), header_cells, "".join(body_rows))


def _row_ident_html(row):
    """The call sign (or the hex, with the no-call-sign note) as visually
    hidden text: it is not drawn in the row, but a screen reader and the page's
    text still carry it."""
    if row["callsign"]:
        ident = escape_html(row["callsign"])
    elif row["hex"]:
        ident = '%s <span class="history-card__note">%s</span>' % (
            escape_html(row["hex"]), escape_html(i18n.t(NO_CALLSIGN_NOTE_TEXT)))
    else:
        return ""
    return '<span class="history-card__callsign mono visually-hidden">%s</span> ' % ident


def _row_label_html(row):
    """The row's title: the airline, then the route codes with the home end
    muted. The call sign is not drawn; it stays in the row's search text, as
    visually hidden text and in the picture link's accessible name."""
    airline = row["airline_label"]
    if airline == AIRLINE_FALLBACK_TEXT:
        airline = i18n.t(AIRLINE_FALLBACK_TEXT)
    return '%s<span class="history-card__airline">%s</span>%s' % (
        _row_ident_html(row), escape_html(airline), _route_codes_html(row))


def _route_codes_html(row):
    """"ORY → KEF" as two code spans; the home end (the origin of a
    departure, the destination of an arrival) is muted so the far airport
    reads first. With no route nothing is shown (the detail line carries the
    shared "Route unavailable" wording)."""
    origin, destination = row.get("origin"), row.get("destination")
    if not (origin and destination):
        return ""
    state = row.get("state_raw")
    return (
        ' <span class="history-card__route">'
        '<span class="history-card__code history-card__code--from%s">%s</span>'
        '<span class="history-card__arrow" aria-hidden="true">\u2192</span>'
        '<span class="history-card__code history-card__code--to%s">%s</span>'
        "</span>"
    ) % (" history-card__code--home" if state == "departing" else "", escape_html(origin),
         " history-card__code--home" if state == "arriving" else "", escape_html(destination))


def _row_detail_text(row):
    """"direction · aircraft type", skipping any empty part."""
    state = row["confirmed_state"] if row["state_raw"] in _CONFIRMED_STATE_LABELS else ""
    return " \u00b7 ".join(part for part in (state, row["aircraft_type_label"]) if part)


def _row_value_html(row, now, dated=True):
    """The trailing value: the live relative age over the local clock time.
    Under a day grouping the group's label carries the date, so the row shows
    the clock alone; under any other order the row dates itself."""
    parsed = layout.parse_iso(row["raw_ts"]) if row["raw_ts"] else None
    if parsed is None:
        clock = escape_html(row["raw_ts"] or i18n.t(_CLOCK_CELL_FALLBACK))
        age = ""
    else:
        reference = parsed if dated else layout.parse_iso(now)
        clock = escape_html(layout.local_clock_text(parsed, reference))
        age = ('<span class="time-value time-value__age">%s</span>'
               % layout.relative_time_html(row["raw_ts"], now)
               if layout.age_seconds(row["raw_ts"], now) is not None else "")
    return (
        '<span class="history-card__when">%s<span class="time-value time-value--primary">%s'
        "</span></span>"
    ) % (age, clock)


def _history_card_html(row, index, now, anchor_index=None, dated=True):
    """One flight as a two-line row: at the left the archived render's thumbnail
    (the control that opens it); the airline and route, "direction \u00b7 aircraft"
    beneath, and the clock over the age at the right. The row at
    `anchor_index` carries the id the Load more link scrolls to."""
    attrs = '%s%s' % (
        _row_facts(row, index),
        ' id="%s"' % _NEW_CARD_ANCHOR if index == anchor_index else "")
    return ui_groups.row(
        label_html=_row_label_html(row),
        detail=_row_detail_text(row), value_html=_row_value_html(row, now, dated),
        lead_html=row.get("view_panel_thumb_html", ""),
        extra_class="history-card", attrs=attrs)


def _card_group_key(row, sort):
    """What a phone group is named by under `sort`: the airline or the direction
    of its rows, else None (the group is named by the sort itself)."""
    if sort == history_query.SORT_AIRLINE:
        label = row["airline_label"]
        return i18n.t(AIRLINE_FALLBACK_TEXT) if label == AIRLINE_FALLBACK_TEXT else label
    if sort == history_query.SORT_DIRECTION:
        return row["confirmed_state"] or None
    return None


def _history_cards_html(formatted_rows, now=None, anchor_index=None, dated=True, group_label="",
                        sort=None):
    """The phone representation, built from the same `formatted_rows` list
    `_history_table_html()` consumes. Newest or oldest first it is one glass
    group per Paris calendar day (the day is its section label); sorted by
    airline or direction it is one group per run of rows sharing that value,
    named by it; under any other order one group named `group_label`. A row
    whose timestamp cannot be dated joins the open group. Returns "" for an
    empty list. Must render as a DOM sibling immediately before the desktop
    table: style.css's `.history-cards ~ .data-table-wrap` breakpoint toggle
    depends on this order."""
    if not formatted_rows:
        return ""
    today = paris_day(now)
    days = []
    current_day = None
    current_key = None
    for index, row in enumerate(formatted_rows):
        day = paris_day(row["raw_ts"]) if dated else None
        key = None if dated else _card_group_key(row, sort)
        if day is not None and day != current_day or not days or (
                key is not None and key != current_key):
            current_day = day if day is not None else current_day
            current_key = key
            days.append((day, key, []))
        days[-1][2].append(_history_card_html(row, index, now, anchor_index, dated))
    groups = []
    for number, (day, key, items) in enumerate(days):
        if day is not None:
            label = day_label(day, today)
        else:
            label = key or group_label or i18n.t(PAGE_TITLE)
        groups.append(ui_groups.group(
            "".join(items), label=label, label_id="history-day-%d" % number,
            extra_class="history-day", attrs="data-filter-day-group"))
    return '<div class="history-cards" data-flights-view>%s</div>' % "".join(groups)


_SHOWN_COUNT_TEXT = i18n.msg("flights.flights_shown", "%d flights shown")
_LOAD_MORE_TEXT = i18n.msg("flights.load_more", "Load more")


def _load_more_html(shown, view, pages):
    """The end-of-list block: how many flights are shown and a Load more
    link to the next page of history. A plain link (`?more=`), so it works
    without a script; it returns to the first new row. There are two links,
    one for each representation of the list (see `_NEW_ROWS_ANCHOR`); the
    stylesheet shows the one that matches the viewport."""
    text = escape_html(i18n.t(_LOAD_MORE_TEXT))
    links = "".join(
        '<a class="history-more__link history-more__link--%s" href="%s" data-flights-more>%s</a>'
        % (kind, escape_html(view_href(view, pages + 1, anchor)), text)
        for kind, anchor in (("cards", _NEW_CARD_ANCHOR), ("table", _NEW_ROWS_ANCHOR)))
    return (
        '<div class="history-more" data-history-more data-flights-view>'
        '<p class="text-label history-more__count" role="status">%s</p>%s</div>'
    ) % (escape_html(i18n.t(_SHOWN_COUNT_TEXT) % shown), links)


def _search_form_html(view):
    """The title-row search: a GET form the server answers. The direction chips
    and the sort join it by `form=`, so one Enter sends all three."""
    return layout.filter_title_search_form_html(
        _FILTER_INPUT_ID, i18n.t(_FILTER_LABEL_TEXT), i18n.t(_FILTER_PLACEHOLDER_TEXT),
        _FORM_ID, device_scope.scoped(layout.FLIGHTS_ROUTE), history_query.Q_PARAM, view.q,
        view_href(history_query.View("", view.kind, view.sort)))


def _list_html(formatted_rows, view, result, pages, now):
    """The cards, the table and the Load more block for the flights shown."""
    dated = view.sort in (history_query.SORT_NEWEST, history_query.SORT_OLDEST)
    # Cards render before the table: style.css's
    # `.history-cards ~ .data-table-wrap` sibling-combinator
    # toggle depends on this DOM order.
    anchor_index = (
        min(pages * HISTORY_ROW_LIMIT, len(formatted_rows) - 1) if pages else None)
    group_label = i18n.t(dict(_SORT_TEXTS)[view.sort])
    return (
        _history_cards_html(formatted_rows, now, anchor_index, dated, group_label, view.sort)
        + _history_table_html(formatted_rows, now, anchor_index, dated)
        + (_load_more_html(len(formatted_rows), view, pages) if result.has_more else ""))


def _attach_pictures(formatted_rows, gallery_entries, state_dir):
    """Stores each row's picture link and thumbnail. Only an archived render
    stamped within the match window of the flight counts as its picture; any
    other flight gets no link and a stand-in thumbnail (the airline's
    illustration, else a plane icon)."""
    for row in formatted_rows:
        match = matching_gallery_entry(gallery_entries, row["raw_ts"])
        row_name = _row_name(row["callsign"], row["hex"])
        row["view_panel_html"] = (
            _view_panel_link_html(match[0], match[1], row_name) if match else "")
        row["view_panel_thumb_html"] = (
            _view_panel_thumb_html(match[0], match[1], row_name) if match
            else _stand_in_thumb_html(row, state_dir))


def render(ctx):
    ctx = page_context.coerce(ctx)
    now = ctx.now or history_db.utc_now_iso()
    names = name_overrides.names_by_prefix(ctx.name_overrides)
    pages = more_pages(ctx.history_more)
    view = history_query.parse_view(ctx.history_query)
    result = _safe_query(
        ctx.state_dir, lambda conn: history_result(conn, view, pages, names))
    available = result is not _DB_UNAVAILABLE
    has_history = available and result.total > 0

    # Flights stays on the self-refreshing loop without showing a
    # freshness line: freshness.js returns at its first guard on any page
    # with no [data-loaded-at], so the silent marker is what keeps it on
    # the loop.
    header = layout.page_header(
        i18n.t(PAGE_TITLE), freshness_html=layout.refresh_marker_html(now),
        action_html=_search_form_html(view) if has_history else None)

    if not available:
        body = ui_groups.group_panel('<p class="text-body">%s</p>' % escape_html(
            i18n.t(_HISTORY_UNAVAILABLE_TEXT)))
        return header + body
    if not has_history:
        device = ctx.device
        heading, text = (
            (DEVICE_EMPTY_HEADING, DEVICE_EMPTY_BODY)
            if device is not None and not device.is_live
            else (_NO_FLIGHTS_HEADING, _NO_FLIGHTS_BODY))
        return header + ui_groups.group_panel(layout.empty_state(
            i18n.t(heading), i18n.t(text), compact=True))

    formatted_rows = [format_event_row(row, now) for row in result.rows]
    _attach_pictures(formatted_rows, ctx.gallery_entries or [], ctx.state_dir)
    inner = _controls_html(view, result)
    if formatted_rows:
        inner += _list_html(formatted_rows, view, result, pages, now)
    else:
        inner += _empty_html(view, result)
    lightbox = _lightbox_html() if any(r["view_panel_html"] for r in formatted_rows) else ""
    return header + inner + lightbox
