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
from datetime import datetime, timezone

import companion.device_scope as device_scope
import companion.flight_card as flight_card
import companion.i18n as i18n
from companion.layout import escape_html
import companion.layout as layout
import companion.page_context as page_context
import companion.prefs as prefs
import companion.ui_groups as ui_groups
from server import history_db
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
_NEW_ROWS_ANCHOR = "flights-new"

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
    expected shape. `nearest_gallery_entry()` skips any entry it cannot
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

# "Callsign" and "Clear" are owned by other catalogues; declared here
# since this page reads them.
_FILTER_COUNT_TEMPLATE = i18n.msg("health.of_shown", "%d of %d shown")

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
_FILTER_KINDS = ("departing", "arriving")
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


def nearest_gallery_entry(entries, row_ts):
    """Returns the `(filename, iso)` pair from `entries` whose
    filename-recovered timestamp is the latest one at or before
    `row_ts`, or `None`. A linear scan over the already-in-memory,
    already-ordered list, since no true per-flight render relationship
    exists to store (the panel refreshes on the device's wake/poll
    cycle, not per detected flight). Comparison is always between
    parsed timezone-aware `datetime` values, never raw strings: gallery
    filenames carry a local UTC offset while history timestamps are
    UTC-suffixed, so a lexicographic compare would mis-rank across an
    offset boundary.
    """
    if not row_ts:
        return None
    try:
        row_dt = datetime.fromisoformat(row_ts)
    except ValueError:
        return None

    best = None
    best_dt = None
    for name in entries or []:
        iso = _gallery_name_to_iso(name)
        if iso is None:
            continue
        try:
            entry_dt = datetime.fromisoformat(iso)
        except ValueError:
            continue
        if entry_dt > row_dt:
            continue
        if best_dt is None or entry_dt > best_dt:
            best = (name, iso)
            best_dt = entry_dt
    return best


def earliest_gallery_entry(entries):
    """The `(filename, iso)` pair with the earliest recoverable
    timestamp in `entries`, or `None`. The fallback for a flight older
    than every archived render, so each flight can still open a picture
    whenever the gallery holds one.
    """
    best = None
    best_dt = None
    for name in entries or []:
        iso = _gallery_name_to_iso(name)
        if iso is None:
            continue
        try:
            entry_dt = datetime.fromisoformat(iso)
        except ValueError:
            continue
        if best_dt is None or entry_dt < best_dt:
            best = (name, iso)
            best_dt = entry_dt
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
    return '<a class="calendar-disconnect-btn flight-picture-link" %s>%s</a>' % (
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
        'loading="lazy" decoding="async">'
        '</a>'
    ) % (_view_panel_attrs(name, iso, row_name), src)


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
        '<p class="lightbox__caption text-label mono"></p>'
        '<button type="button" %s>%s</button>'
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


def history_rows_page(conn, airline_names=None, pages=0):
    """`(rows, has_more)`: the most recent `(pages + 1) * HISTORY_ROW_LIMIT`
    `runway_events` rows, newest first (matches
    `history_db.recent_runway_events()`'s own ordering), with a pass stored
    twice folded into one row — the same fold Home applies, so chip counts
    and day headers count flights, not stored events. `has_more` is true
    when stored events exist beyond that limit. Storage keeps every event.
    """
    limit = (pages + 1) * HISTORY_ROW_LIMIT
    events = history_db.recent_runway_events(
        conn, limit=limit + 1, airline_names=airline_names)
    return flight_card.fold_repeated_passes(events[:limit]), len(events) > limit


def history_rows(conn, airline_names=None):
    """The most recent `HISTORY_ROW_LIMIT` flights; see `history_rows_page`."""
    return history_rows_page(conn, airline_names)[0]


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
    """The escaped, lowercased haystack for a row's `data-filter-text`
    attribute, computed once per row and reused by both the desktop
    `<tr>` and the mobile `<li>` for the same flight: callsign, hex,
    resolved airline name, both route codes and the aircraft type, so a
    search for "Transavia", "KEF" or "A320" finds the row. The
    unresolved-airline fallback wording is never searchable.
    """
    airline = "" if row["airline_label"] == AIRLINE_FALLBACK_TEXT else row["airline_label"]
    parts = (
        row["callsign"], row["hex"], airline, row.get("origin", ""),
        row.get("destination", ""), row["aircraft_type_label"])
    return escape_html(" ".join(p for p in parts if p).lower())


def _filter_kind_attr(row):
    """The row's `data-filter-kind` attribute, the dimension the chip
    group filters on: the runway direction the detector confirmed. Only
    departing and arriving count; anything else, an overhead row
    included, belongs to "All" alone, so a chip never claims a row it cannot name.
    """
    state = row.get("state_raw") or ""
    return state if state in _FILTER_KINDS else ""


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


def _filter_bar_html(rows):
    """The Flights filter bar: the shared search field plus a direction
    chip group (All / Departures / Arrivals) whose counts come from the
    rows' own `state_raw`. `rows` is every flight the page renders, so
    the live count and empty-state body read its length.
    """
    shown = len(rows)
    empty_body = i18n.t(_FILTER_EMPTY_BODY_TEMPLATE) % shown
    chips = (
        ("", i18n.t(_CHIP_ALL_TEXT), shown),
        ("departing", i18n.t(_CHIP_DEPARTURES_TEXT),
         sum(1 for r in rows if _filter_kind_attr(r) == "departing")),
        ("arriving", i18n.t(_CHIP_ARRIVALS_TEXT),
         sum(1 for r in rows if _filter_kind_attr(r) == "arriving")),
    )
    return layout.filter_bar_html(
        _FILTER_INPUT_ID, i18n.t(_FILTER_LABEL_TEXT),
        i18n.t(_FILTER_PLACEHOLDER_TEXT), i18n.t(_FILTER_COUNT_TEMPLATE),
        shown, shown, i18n.t(_FILTER_EMPTY_HEADING), empty_body,
        chips=chips, chips_legend=i18n.t(_FILTER_CHIPS_LEGEND), search_in_bar=False)


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


def _history_table_html(formatted_rows, now=None):
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
        day = paris_day(row["raw_ts"])
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
        # data-filter-group carries this row's loop index, shared with
        # the <li> at the same index in _history_cards_html(), so
        # list-filter.js counts logical rows once, not once per
        # representation; the stable event identity arrives beside it as
        # its own attribute — one renumbers when a detection lands, the
        # other must not.
        body_rows.append(
            '<tr class="%s" data-flight-row data-filter-text="%s" '
            'data-filter-kind="%s" data-filter-group="%d" %s="%s">%s</tr>'
            % (row_class, _filter_text_attr(row), _filter_kind_attr(row), index,
               layout.REFRESH_ROW_ID_ATTR, escape_html(_row_identity(row)),
               "".join(cells)))

    return (
        '<div class="data-table-wrap" tabindex="0" role="region" '
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


def _row_value_html(row, now):
    """The trailing value: the live relative age over the local clock time."""
    parsed = layout.parse_iso(row["raw_ts"]) if row["raw_ts"] else None
    if parsed is None:
        clock = escape_html(row["raw_ts"] or i18n.t(_CLOCK_CELL_FALLBACK))
        age = ""
    else:
        # The day group's label carries the date, so the row shows the clock alone.
        clock = escape_html(layout.local_clock_text(parsed, parsed))
        age = ('<span class="time-value time-value__age">%s</span>'
               % layout.relative_time_html(row["raw_ts"], now)
               if layout.age_seconds(row["raw_ts"], now) is not None else "")
    return (
        '<span class="history-card__when">%s<span class="time-value time-value--primary">%s'
        "</span></span>"
    ) % (age, clock)


def _history_card_html(row, index, now, anchor_index=None):
    """One flight as a two-line row: at the left the archived render's thumbnail
    (the control that opens it); the airline and route, "direction \u00b7 aircraft"
    beneath, and the clock over the age at the right.
    `data-filter-group` is the row's loop index, shared with the desktop
    `<tr>` at the same index so list-filter.js counts one flight once. The
    row at `anchor_index` carries the id the Load more link scrolls to."""
    attrs = (
        'data-filter-text="%s" data-filter-kind="%s" data-filter-group="%d" %s="%s"%s'
    ) % (_filter_text_attr(row), _filter_kind_attr(row), index,
         layout.REFRESH_ROW_ID_ATTR, escape_html(_row_identity(row)),
         ' id="%s"' % _NEW_ROWS_ANCHOR if index == anchor_index else "")
    return ui_groups.row(
        label_html=_row_label_html(row),
        detail=_row_detail_text(row), value_html=_row_value_html(row, now),
        lead_html=row.get("view_panel_thumb_html", ""),
        extra_class="history-card", attrs=attrs)


def _history_cards_html(formatted_rows, now=None, anchor_index=None):
    """The phone representation: one glass group per Paris calendar day
    (the day is its section label), one row per flight, built from the same
    `formatted_rows` list `_history_table_html()` consumes. A row whose
    timestamp cannot be dated joins the open group. Returns "" for an empty
    list. Must render as a DOM sibling immediately before the desktop table:
    style.css's `.history-cards ~ .data-table-wrap` breakpoint toggle depends
    on this order."""
    if not formatted_rows:
        return ""
    today = paris_day(now)
    days = []
    current_day = None
    for index, row in enumerate(formatted_rows):
        day = paris_day(row["raw_ts"])
        if day is not None and day != current_day or not days:
            current_day = day if day is not None else current_day
            days.append((day, []))
        days[-1][1].append(_history_card_html(row, index, now, anchor_index))
    groups = []
    for number, (day, items) in enumerate(days):
        label = day_label(day, today) if day is not None else i18n.t(PAGE_TITLE)
        groups.append(ui_groups.group(
            "".join(items), label=label, label_id="history-day-%d" % number,
            extra_class="history-day", attrs="data-filter-day-group"))
    return '<div class="history-cards">%s</div>' % "".join(groups)


_SHOWN_COUNT_TEXT = i18n.msg("flights.flights_shown", "%d flights shown")
_LOAD_MORE_TEXT = i18n.msg("flights.load_more", "Load more")


def _load_more_html(shown, pages):
    """The end-of-list block: how many flights are shown and a Load more
    link to the next page of history. A plain link (`?more=`), so it works
    without a script; it returns to the first new row."""
    href = device_scope.scoped(
        "%s?%s=%d#%s" % (layout.FLIGHTS_ROUTE, MORE_PARAM, pages + 1, _NEW_ROWS_ANCHOR))
    return (
        '<div class="history-more" data-history-more>'
        '<p class="text-label history-more__count">%s</p>'
        '<a class="history-more__link" href="%s">%s</a></div>'
    ) % (escape_html(i18n.t(_SHOWN_COUNT_TEXT) % shown), escape_html(href),
         escape_html(i18n.t(_LOAD_MORE_TEXT)))


def render(ctx):
    ctx = page_context.coerce(ctx)
    now = ctx.now or history_db.utc_now_iso()
    names = name_overrides.names_by_prefix(ctx.name_overrides)
    pages = more_pages(ctx.history_more)
    fetched = _safe_query(
        ctx.state_dir, lambda conn: history_rows_page(conn, names, pages))
    rows, has_more = fetched if fetched is not _DB_UNAVAILABLE else (_DB_UNAVAILABLE, False)

    # Flights stays on the self-refreshing loop without showing a
    # freshness line: freshness.js returns at its first guard on any page
    # with no [data-loaded-at], so the silent marker is what keeps it on
    # the loop.
    header = layout.page_header(
        i18n.t(PAGE_TITLE), freshness_html=layout.refresh_marker_html(now),
        action_html=layout.filter_title_search_html(
            _FILTER_INPUT_ID, i18n.t(_FILTER_LABEL_TEXT), i18n.t(_FILTER_PLACEHOLDER_TEXT))
        if rows is not _DB_UNAVAILABLE and rows else None)

    # gallery_entries_list is the input to nearest_gallery_entry() below,
    # which every per-row "View panel near this time" trigger depends on.
    gallery_entries_list = ctx.gallery_entries or []

    if rows is _DB_UNAVAILABLE:
        body = ui_groups.group_panel('<p class="text-body">%s</p>' % escape_html(
            i18n.t(_HISTORY_UNAVAILABLE_TEXT)))
        lightbox_html = ""
    else:
        formatted_rows = [format_event_row(row, now) for row in rows]
        # formatted_rows is the one list both _history_cards_html() and
        # _history_table_html() render from, so the two can never
        # disagree about which flights exist.
        visible_rows = formatted_rows
        # The nearest-render match is computed once per row and stored
        # onto the row dict both renderers share. A row with no match
        # carries the empty string, never a disabled/broken control.
        for row in visible_rows:
            match = (
                nearest_gallery_entry(gallery_entries_list, row["raw_ts"])
                or earliest_gallery_entry(gallery_entries_list))
            row_name = _row_name(row["callsign"], row["hex"])
            row["view_panel_html"] = (
                _view_panel_link_html(match[0], match[1], row_name) if match else "")
            row["view_panel_thumb_html"] = (
                _view_panel_thumb_html(match[0], match[1], row_name) if match else "")
        # The shared lightbox is emitted once per page, only when at
        # least one row carries a trigger button.
        has_view_panel_button = any(
            row["view_panel_html"] for row in visible_rows)
        lightbox_html = _lightbox_html() if has_view_panel_button else ""
        if not visible_rows:
            # No filter bar over nothing to filter.
            device = ctx.device
            if device is not None and not device.is_live:
                body = ui_groups.group_panel(layout.empty_state(
                    i18n.t(DEVICE_EMPTY_HEADING), i18n.t(DEVICE_EMPTY_BODY), compact=True))
            else:
                body = _history_table_html(visible_rows, now)
        else:
            # Cards render before the table: style.css's
            # `.history-cards ~ .data-table-wrap` sibling-combinator
            # toggle depends on this DOM order.
            anchor_index = (
                min(pages * HISTORY_ROW_LIMIT, len(visible_rows) - 1) if pages else None)
            body = (
                _filter_bar_html(visible_rows)
                + _history_cards_html(visible_rows, now, anchor_index)
                + _history_table_html(visible_rows, now)
                + (_load_more_html(len(visible_rows), pages) if has_more else ""))

    return header + body + lightbox_html
