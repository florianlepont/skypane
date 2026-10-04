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
import urllib.parse
from datetime import datetime, timezone

import companion.flight_card as flight_card
import companion.i18n as i18n
from companion.layout import escape_html
import companion.layout as layout
import companion.page_context as page_context
import companion.prefs as prefs
from server import history_db
from server.plane import manual_resolutions
from server.plane import render as panel_render

# history is kept forever; this is a display limit for readability,
# not a retention policy.
HISTORY_ROW_LIMIT = 50

# The number of flights the first screen shows, before "Show more" is
# clicked. 15 is the top of the locked 10-15 band, and HISTORY_ROW_LIMIT
# (50) divides into it as 15/30/45/50, the last short by 5, which
# SHOW_MORE_TEMPLATE's remaining-count handles without overclaiming.
FLIGHTS_PAGE_SIZE = 15

# freshness.js's fetch(window.location.href) re-requests whatever URL
# the browser is on, so once a visitor clicks "?limit=30", every later
# background refresh keeps requesting that URL automatically — the
# reveal state is the URL, no script change needed to survive refresh.
FLIGHTS_LIMIT_QUERY_PARAM = "limit"

PAGE_TITLE = i18n.msg("nav.flights", "Flights")
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

# A second empty-state body, used only while a limit is in force and
# rows remain unloaded: list-filter.js filters the DOM it has, never
# the database, so a search under a limit only covers the loaded rows.
_FILTER_EMPTY_BODY_LIMITED_TEMPLATE = i18n.msg(
    "flights.try_a_different_search_this_only_searches_the",
    "Try a different search — this only searches the %d flights shown.")

# `%d` is filled with the remaining count, not the next page size, so
# the control never overclaims on the last, short page.
SHOW_MORE_TEMPLATE = i18n.msg(
    "flights.show_more_remaining", "Show more (%d remaining)")

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

# One hop to act: the resolve link goes straight to the Airlines
# resolve view for this row's prefix. Route and query-parameter names
# are duplicated, not imported (page modules cannot import each other),
# pinned by test_view_pages.py's cross-module guard.
RESOLVE_LINK_HREF_TEMPLATE = "/airlines?resolve=%s"
RESOLVE_LINK_TEXT = i18n.msg("flights.name_this_airline", "Name this airline")
UNRESOLVED_LINK_CLASS = "text-label cell-unresolved-link"

# Shared with home_page.py's own DAY_BAND_HEADING — "Today" is owned by
# companion/i18n_fr/flights.py, not home.py.
_DAY_TODAY_LABEL = i18n.msg("flights.today", "Today")
_DAY_YESTERDAY_LABEL = i18n.msg("flights.yesterday", "Yesterday")

VIEW_PICTURE_LABEL = i18n.msg("flights.view_picture", "View picture")

# The phone card's artwork, route and time pieces are shared with Home's
# recent-flight tiles through companion/flight_card.py.
ILLUSTRATION_ROUTE_PREFIX = flight_card.ILLUSTRATION_ROUTE_PREFIX
ROUTE_FALLBACK_TEXT = flight_card.ROUTE_FALLBACK_TEXT

# A missing airline gets its own fallback text, distinct from
# panel_render.ROUTE_FALLBACK_TEXT, so the same phrase doesn't appear
# twice in one unresolved row (Type+Airline cell and Route cell).
AIRLINE_FALLBACK_TEXT = i18n.msg("flights.airline_unknown", "Airline unknown")

# server/plane/runway_config.py's infer_runway_config(), the only
# writer of confirmed_state, only ever produces "departing" or
# "arriving". Any other non-empty value degrades to a title-cased,
# underscore-stripped rendering via _confirmed_state_label() below.
# "Departing"/"Arriving" are owned by companion/i18n_fr/home.py, not
# flights.py — the same ids home_page.py's own direction text uses.
_CONFIRMED_STATE_LABELS = {
    "departing": i18n.msg("home.departing", "Departing"),
    "arriving": i18n.msg("home.arriving", "Arriving"),
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
    src = "%s%s" % (_GALLERY_ROUTE_PREFIX, escape_html(name))
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


def _view_panel_icon_link_html(name, iso, row_name):
    """The phone card's picture action: the same real link and trigger
    attributes as `_view_panel_link_html()`, drawn as a 44px icon
    button. The glyph is aria-hidden, so the `aria-label` alone names it.
    """
    return '<a class="history-card__picture" %s>%s</a>' % (
        _view_panel_attrs(name, iso, row_name),
        layout.icon_html("icon-picture", 20),
    )


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
        '<dialog class="lightbox" id="%s" aria-label="%s">'
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


def history_rows(conn):
    """The most recent `HISTORY_ROW_LIMIT` `runway_events` rows, newest
    first (matches `history_db.recent_runway_events()`'s own ordering).
    """
    return history_db.recent_runway_events(conn, limit=HISTORY_ROW_LIMIT)


def flights_limit(ctx):
    """The number of flights this render should show, an int inside
    `[FLIGHTS_PAGE_SIZE, HISTORY_ROW_LIMIT]`. Reads the raw, unvalidated
    `?limit=` value from `ctx.flights_limit` and clamps rather than
    rejects an out-of-range result to `None`: a hand-edited URL should
    render a page, not an error, and `HISTORY_ROW_LIMIT` is already the
    hard ceiling `history_rows()` fetches, so clamping upward can never
    ask for a row the query would not return anyway. Total by
    construction: no input, however malformed, ever raises.
    """
    ctx = page_context.coerce(ctx)
    raw = ctx.flights_limit
    if isinstance(raw, bool):
        # bool is an int subclass; rejected explicitly before str()/int()
        # rather than relying on int(str(True)) failing by accident.
        return FLIGHTS_PAGE_SIZE
    try:
        candidate = int(str(raw).strip())
    except (TypeError, ValueError):
        return FLIGHTS_PAGE_SIZE
    if candidate < FLIGHTS_PAGE_SIZE:
        return FLIGHTS_PAGE_SIZE
    if candidate > HISTORY_ROW_LIMIT:
        return HISTORY_ROW_LIMIT
    return candidate


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
    the two values the detector writes count; anything else belongs to
    "All" alone, so a chip never claims a row it cannot name.
    """
    state = row.get("state_raw") or ""
    return state if state in _FILTER_KINDS else ""


def resolve_prefix_for_callsign(callsign):
    """The 3-letter ICAO prefix `callsign` would be filed under in the
    unresolved-prefix registry, or `None` (never raising). Uses the same
    normalisation `airlines_page.unresolved_row_for_prefix()` applies at
    the resolve view's own boundary, so a prefix this produces is
    exactly a prefix that view accepts. A bare three-character callsign
    yields `None`: the registry writer requires at least four characters
    before it ever records a prefix.
    """
    if not isinstance(callsign, str):
        return None
    normalised = callsign.strip().upper()
    if len(normalised) < 4:
        return None
    return manual_resolutions.normalise_prefix(normalised[:3])


def _resolve_link_html(prefix):
    """A one-hop link from a flight whose airline could not be named
    straight to the Airlines resolve view for that flight's prefix,
    used by both the desktop cell and the phone card. `prefix` is
    URL-quoted for the query string and then escaped for the attribute,
    both at this single point of interpolation; the resolve view
    re-validates the prefix on arrival regardless.
    """
    href = RESOLVE_LINK_HREF_TEMPLATE % urllib.parse.quote(prefix, safe="")
    return '<a class="%s" href="%s">%s</a>' % (
        escape_html(UNRESOLVED_LINK_CLASS),
        escape_html(href), escape_html(i18n.t(RESOLVE_LINK_TEXT)))


def _row_resolve_link_html(row):
    """`_resolve_link_html()` for a row whose airline could not be
    resolved, or "" for a resolved airline or one whose callsign yields
    no usable prefix. Both the desktop cell and the phone card call
    this, so the two can never disagree about whether it's present.
    """
    if row["airline_label"] != AIRLINE_FALLBACK_TEXT:
        return ""
    prefix = resolve_prefix_for_callsign(row["callsign"])
    return _resolve_link_html(prefix) if prefix else ""


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
    carries the callsign (mono); the secondary slot carries "{airline} ·
    {aircraft type}" as one plain string, so the rendered cell reads
    "AFR1234 · Air France · A320". The resolve link is appended after,
    only when this row's airline could not be resolved (the mobile card
    keeps its own identical copy of this logic).
    """
    is_unresolved = row["airline_label"] == AIRLINE_FALLBACK_TEXT
    airline_display = i18n.t(row["airline_label"]) if is_unresolved else row["airline_label"]
    secondary = "%s · %s" % (airline_display, row["aircraft_type_label"])
    html = _merged_cell(row["callsign"], secondary)
    resolve_link = _row_resolve_link_html(row)
    if resolve_link:
        html = html[:-len("</td>")] + resolve_link + "</td>"
    return html


def _filter_bar_html(visible_rows, total_available):
    """The Flights filter bar: the shared search field plus a direction
    chip group (All / Departures / Arrivals) whose counts come from the
    rows' own `state_raw`. `visible_rows` is the list this render shows;
    the live count and empty-state body read its length honestly, never
    claiming a search coverage the filter does not have when a `?limit=`
    leaves rows unloaded (list-filter.js filters the DOM it has).
    """
    shown = len(visible_rows)
    if shown < total_available:
        empty_body = i18n.t(_FILTER_EMPTY_BODY_LIMITED_TEMPLATE) % shown
    else:
        empty_body = i18n.t(_FILTER_EMPTY_BODY_TEMPLATE) % shown
    chips = (
        ("", i18n.t(_CHIP_ALL_TEXT), shown),
        ("departing", i18n.t(_CHIP_DEPARTURES_TEXT),
         sum(1 for r in visible_rows if _filter_kind_attr(r) == "departing")),
        ("arriving", i18n.t(_CHIP_ARRIVALS_TEXT),
         sum(1 for r in visible_rows if _filter_kind_attr(r) == "arriving")),
    )
    return layout.filter_bar_html(
        _FILTER_INPUT_ID, i18n.t(_FILTER_LABEL_TEXT),
        i18n.t(_FILTER_PLACEHOLDER_TEXT), i18n.t(_FILTER_COUNT_TEMPLATE),
        shown, shown, i18n.t(_FILTER_EMPTY_HEADING), empty_body,
        chips=chips, chips_legend=i18n.t(_FILTER_CHIPS_LEGEND))


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
        return layout.empty_state(i18n.t(_NO_FLIGHTS_HEADING), i18n.t(_NO_FLIGHTS_BODY))

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


def _card_identity_html(row):
    """The card header's left column: the callsign in the identifier
    voice, then the airline. A row with no callsign promotes its hex
    with the NO_CALLSIGN_NOTE_TEXT note, so the slot is never blank. An
    unresolved airline reads "Airline unknown" and carries the resolve
    link under it.
    """
    if row["callsign"]:
        ident = escape_html(row["callsign"])
    elif row["hex"]:
        ident = '%s <span class="history-card__note">%s</span>' % (
            escape_html(row["hex"]), escape_html(i18n.t(NO_CALLSIGN_NOTE_TEXT)))
    else:
        ident = ""
    is_unresolved = row["airline_label"] == AIRLINE_FALLBACK_TEXT
    if is_unresolved:
        airline_html = (
            '<span class="history-card__airline history-card__airline--unknown">%s</span>'
            % escape_html(i18n.t(AIRLINE_FALLBACK_TEXT)))
        resolve_link = _row_resolve_link_html(row)
        if resolve_link:
            airline_html += '<span class="history-card__resolve">%s</span>' % resolve_link
    else:
        airline_html = '<span class="history-card__airline">%s</span>' % escape_html(
            row["airline_label"])
    return (
        '<div class="history-card__id">'
        '<span class="history-card__callsign mono">%s</span>%s</div>'
    ) % (ident, airline_html)


def _card_stub_html(row, now):
    """The card's stub, below the tear line: the airline artwork as a
    wide plate (or a quiet dashed placeholder when there is none) and,
    on the same row, the time and age.
    """
    return flight_card.stub_html(row.get("thumb_html"), row["raw_ts"], now)


def card_day_label(day, today):
    """The phone list's slim day header: `day_label()`, plus the short
    date after "Today"/"Yesterday" so the header reads "Today · 3 Oct".
    An absolute label is already a date and gains nothing.
    """
    label = day_label(day, today)
    absolute = "%d %s" % (day.day, layout.month_abbr(day.month))
    if label == absolute:
        return label
    return "%s %s %s" % (label, CELL_SEPARATOR_TEXT, absolute)


def _history_card_html(row, index, now):
    """One boarding-pass card: header (identity + picture action), route
    line, then the stub. `data-filter-group` is the row's loop index,
    shared with the desktop `<tr>` at the same index so list-filter.js
    counts one flight once.
    """
    return (
        '<li class="history-card" data-filter-text="%s" '
        'data-filter-kind="%s" data-filter-group="%d" %s="%s">'
        '<div class="history-card__head">%s%s</div>%s%s</li>'
    ) % (_filter_text_attr(row), _filter_kind_attr(row), index,
         layout.REFRESH_ROW_ID_ATTR, escape_html(_row_identity(row)),
         _card_identity_html(row), row.get("view_panel_icon_html", ""),
         flight_card.route_html(row.get("origin"), row.get("destination"),
                                row.get("state_raw"), row["confirmed_state"]),
         _card_stub_html(row, now))


def _history_cards_html(formatted_rows, now=None):
    """Mobile boarding-pass representation, one `<li>` per row, built
    from the same `formatted_rows` list `_history_table_html()`
    consumes, with a slim day-header `<li>` wherever the Paris calendar
    day changes (the same grouping the table's separator rows use).
    Returns "" for an empty list. Must render as a DOM sibling
    immediately before the desktop table: style.css's
    `.history-cards ~ .data-table-wrap` breakpoint toggle depends on
    this order.
    """
    if not formatted_rows:
        return ""
    today = paris_day(now)
    current_day = None
    items = []
    for index, row in enumerate(formatted_rows):
        day = paris_day(row["raw_ts"])
        if day is not None and day != current_day:
            current_day = day
            items.append('<li class="history-cards__day" data-filter-day>%s</li>' % escape_html(
                card_day_label(day, today)))
        items.append(_history_card_html(row, index, now))
    return '<ul class="history-cards">%s</ul>' % "".join(items)


def _show_more_html(shown, total_available):
    """The "Show more" reveal. Returns `<nav class="flights-more">...
    </nav>`, empty once every row is on the page — the nav element is
    always rendered, even empty, since `.flights-more` is a declared
    swap target that must be findable on every render;
    `.flights-more:empty { display: none; }` keeps it from costing
    layout. The one child, when present, is a plain `<a>`, matching the
    app's no-JS control contract. The href is built entirely
    server-side from `FLIGHTS_LIMIT_QUERY_PARAM` and a clamped int,
    never from the raw query string a visitor supplied, so a crafted
    `?limit=` value can never be reflected back into this link. The
    label's `%d` is the remaining count, not the next page size, so the
    control never overclaims on the last, short page.
    """
    if shown >= total_available:
        return '<nav class="flights-more"></nav>'
    next_limit = min(shown + FLIGHTS_PAGE_SIZE, HISTORY_ROW_LIMIT)
    remaining = total_available - shown
    label = i18n.t(SHOW_MORE_TEMPLATE) % remaining
    anchor = (
        '<a class="calendar-disconnect-btn" href="%s?%s=%d">%s</a>'
    ) % (
        layout.FLIGHTS_ROUTE, FLIGHTS_LIMIT_QUERY_PARAM, next_limit,
        escape_html(label),
    )
    return '<nav class="flights-more">%s</nav>' % anchor


def render(ctx):
    ctx = page_context.coerce(ctx)
    state_dir = ctx.state_dir
    now = ctx.now or history_db.utc_now_iso()
    rows = _safe_query(state_dir, history_rows)

    # Flights stays on the self-refreshing loop without showing a
    # freshness line: freshness.js returns at its first guard on any page
    # with no [data-loaded-at], so the silent marker is what keeps it on
    # the loop.
    header = layout.page_header(
        i18n.t(PAGE_TITLE), freshness_html=layout.refresh_marker_html(now))

    # gallery_entries_list is the input to nearest_gallery_entry() below,
    # which every per-row "View panel near this time" trigger depends on.
    gallery_entries_list = ctx.gallery_entries or []

    if rows is _DB_UNAVAILABLE:
        body = '<p class="text-body">%s</p>' % escape_html(i18n.t(_HISTORY_UNAVAILABLE_TEXT))
        lightbox_html = ""
    else:
        formatted_rows = [format_event_row(row, now) for row in rows]
        # Sliced before the per-row enrichment loop below, so that loop's
        # gallery lookup and thumbnail render run only for rows this
        # render actually shows. visible_rows is the one list both
        # _history_cards_html() and _history_table_html() render from,
        # so the two can never disagree about which flights exist.
        limit = flights_limit(ctx)
        total_available = len(formatted_rows)
        visible_rows = formatted_rows[:limit]
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
            row["view_panel_icon_html"] = (
                _view_panel_icon_link_html(match[0], match[1], row_name) if match else "")
            # The phone card's artwork thumbnail, resolved once per row
            # for the same reason as the view-panel match. The desktop
            # table does not render it: no room in its width budget.
            row["thumb_html"] = flight_card.art_html(row["airline_raw"], state_dir)
        # The shared lightbox is emitted once per page, only when at
        # least one row carries a trigger button.
        has_view_panel_button = any(
            row["view_panel_html"] for row in visible_rows)
        lightbox_html = _lightbox_html() if has_view_panel_button else ""
        if not visible_rows:
            # No filter bar over nothing to filter.
            body = _history_table_html(visible_rows, now)
        else:
            # Cards render before the table: style.css's
            # `.history-cards ~ .data-table-wrap` sibling-combinator
            # toggle depends on this DOM order. Show-more renders last.
            body = (
                _filter_bar_html(visible_rows, total_available)
                + _history_cards_html(visible_rows, now)
                + _history_table_html(visible_rows, now)
                + _show_more_html(len(visible_rows), total_available))

    return header + body + lightbox_html
