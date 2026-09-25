"""The Flights page: a flight-history log built from
`server.history_db.recent_runway_events()`, reusing
`server.plane.render`'s presentation-only mappings
(`display_airline_name()`, `_TYPE_DISPLAY_LABELS`) so this page and the
physical panel describe the same flight with the same words.

Every database access goes through `_safe_query()`, so a missing or
locked database degrades to the unavailable copy instead of raising.
`layout.data_table()` cannot host the Corroboration column's
`status_dot()` markup (it escapes every cell value), so this module
builds its own table markup, matching `data_table()`'s CSS classes for
visual consistency and escaping every other cell through
`escape_html()`.
"""
import re
import sqlite3
import urllib.parse
from datetime import datetime, timezone

import companion.i18n as i18n
from companion.layout import escape_html
import companion.layout as layout
import companion.prefs as prefs
from server import device_config
from server import history_db
from server.plane import illustrations
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

PAGE_TITLE = "Flights"
PAGE_PURPOSE_TEMPLATE = "The latest %d aircraft the frame has shown."
LIGHTBOX_ARIA_LABEL = "Picture shown on the frame"

# The render gallery's colours are nominal render-internal swatches, not
# colour-accurate against real Spectra 6 glass — without this caveat a
# user could mistake an expected render/glass mismatch for a hardware
# fault.
COLOUR_CAVEAT = (
    "Colours are nominal render-internal swatches, not colour-accurate "
    "against real Spectra 6 glass.")

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


_NO_FLIGHTS_HEADING = "No flights yet."
_NO_FLIGHTS_BODY = (
    "No flights detected yet — check back after the next poll cycle.")

# Duplicated from health_page.py's HEALTH_UNAVAILABLE_TEXT rather than
# imported: page modules cannot import each other.
_HISTORY_UNAVAILABLE_TEXT = (
    "The flight list is temporarily unavailable — try again in a minute.")

# Five columns: "When" and "Flight" are two-line cell-primary/secondary
# pairs (_merged_cell(), stacked rather than inline); the hex, full ISO
# timestamp, runway and copy buttons move into a sibling expandable
# detail <tr>. Corroboration keeps its dot but hides its label
# (status_dot(visually_hide_label=True)): a ~90px label would blow the
# column's content-width budget.
_HEADERS = (
    "When", "Flight", "Route", "State", "Corroboration",
)

# The sixth, non-data <th>: a visually-hidden "Details" label naming
# the row-toggle column for a screen-reader user, never emitted through
# the _HEADERS/i18n.t(h) loop (no column of formatted data behind it).
_DETAILS_HEADER_TEXT = "Details"

# The row toggle is icon-only: each button carries a translated
# aria-label that swaps with its state, wider than the base "Show/Hide
# flight details" wording since the panel-picture control lives inside
# that detail row too and a name saying only "details" would hide it.
_TOGGLE_SHOW_LABEL = "Show flight details and picture"
_TOGGLE_HIDE_LABEL = "Hide flight details and picture"

# A decorative glyph inside an aria-hidden span, so the button's
# accessible name is the aria-label above alone. Rendered server-side,
# not through a CSS `content:` string (not translatable) or
# layout.icon_html() (the sprite has no chevron symbol).
_TOGGLE_GLYPH = "▾"

# The two attribute names flight-rows.js reads the swapped accessible
# name from — duplicated, not imported (a page module has no import
# path to a static script), pinned against that file's source.
_TOGGLE_SHOW_LABEL_ATTR = "data-show-label"
_TOGGLE_HIDE_LABEL_ATTR = "data-hide-label"

# Names the .data-table-wrap scroller for keyboard users: tabindex="0"
# plus this label turn the wrapper into a focusable, named region a
# keyboard user can Tab to and arrow-scroll.
SCROLLER_ARIA_LABEL = "Recent flights table, scrollable"

# Class names styled by style.css. Duplicated here rather than imported
# (a page module has no import path to the stylesheet); a cross-file
# drift guard reads style.css from disk and requires all three there.
CELL_PRIMARY_CLASS = "cell-primary"
CELL_SECONDARY_CLASS = "cell-secondary"
CELL_SEPARATOR_CLASS = "cell-inline-sep"

# Defined once so the separator can never be typed as a hyphen at one
# call site and a middle dot at another.
CELL_SEPARATOR_TEXT = "·"

# history_db's stored corroborated column mapped to the same three
# (status, label) pairs health_page._CORROBORATION_ROWS uses, so the
# two pages read consistently. An unrecognised/legacy value falls back
# to the warning class rather than a fabricated label.
_CORROBORATION_LABELS = {
    "True": ("ok", "Both agree"),
    # Shortened from "Single-source (uncorroborated)": the parenthetical
    # made this column overlong. The long form survives as a tooltip via
    # _CORROBORATION_TITLES; health_page keeps the long form as its own
    # visible label — the two pages are allowed to diverge in copy.
    "None": ("ok", "Single-source"),
    "False": ("warn", "They disagree"),
}
_DEFAULT_CORROBORATION = ("warn", "Unknown")

# Keys absent from this dict resolve to no tooltip at all (True/False
# need none). Kept equal to health_page's own "None" visible label.
_CORROBORATION_TITLES = {
    "None": "Only one saw it",
}

_DB_UNAVAILABLE = object()  # Same sentinel discipline as health_page.py:
# distinguishes "query raised" from "query succeeded, legitimately empty".

# Driven client-side by list-filter.js's shared data-filter-* attribute
# contract. No hyphen in this id: WebKit/Safari renders a contacts
# autofill suggestion for a name-less search input whose id contains a
# hyphen, and ignores autocomplete="off" in that case — the underscore
# form is safe since the documented trigger is the hyphen character
# specifically.
_FILTER_INPUT_ID = "history_filter_input"
_FILTER_LABEL_TEXT = "Filter by callsign or hex"
_FILTER_EMPTY_HEADING = "No matching flights"
_FILTER_EMPTY_BODY_TEMPLATE = (
    "Try a different search, or Clear filter to see all %d flights.")

# A second empty-state body, used only while a limit is in force and
# rows remain unloaded: list-filter.js filters the DOM it has, never
# the database, so a search under a limit only covers the loaded rows.
_FILTER_EMPTY_BODY_LIMITED_TEMPLATE = (
    "Try a different search — this only searches the %d flights shown.")

# `%d` is filled with the remaining count, not the next page size, so
# the control never overclaims on the last, short page.
SHOW_MORE_TEMPLATE = "Show more (%d remaining)"

# Each is a %s template naming the row (callsign, or a hex/
# NO_CALLSIGN_NOTE_TEXT fallback via _row_copy_name()), so a page's ~50
# copy buttons don't share one identical accessible name.
_COPY_CALLSIGN_LABEL = "Copy callsign %s"
_COPY_HEX_LABEL = "Copy hex ID for %s"
_COPY_TIMESTAMP_LABEL = "Copy timestamp for %s"

# The presentational note shown beside a promoted hex when a row has no
# callsign: a module-level constant so the desktop cell and the mobile
# card can't drift onto two different wordings.
NO_CALLSIGN_NOTE_TEXT = "no callsign"


def _row_copy_name(callsign, hex_value):
    """The value substituted for the `%s` in each `_COPY_*_LABEL`
    template: the row's callsign, falling back to its hex and finally
    to `NO_CALLSIGN_NOTE_TEXT`, so a row with neither never leaves the
    accessible name with a dangling "for ".
    """
    return callsign or hex_value or i18n.t(NO_CALLSIGN_NOTE_TEXT)


# The stable identity of the event a row describes, rendered into
# layout.REFRESH_ROW_ID_ATTR on all three of this page's row elements.
# `runway_events.id` is assigned once and never reused, unlike the loop
# counter (`flight-detail-{n}`), which renumbers whenever a newer
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


VIEW_PANEL_LABEL = "View panel near this time"
LIGHTBOX_DIALOG_ID = "panel-lookup-dialog"
LIGHTBOX_CAPTION_TEMPLATE = "Picture from %s"
# LIGHTBOX_DIALOG_ID and the three data-view-panel-* attribute names
# below must equal panel-lookup.js's own literals exactly (duplicated,
# not imported: a page module has no import path to a static script),
# pinned by test_view_pages.py's three-file DOM-contract guard.
LIGHTBOX_NOTE = (
    "This is the nearest recorded render, not necessarily from this "
    "exact flight — the panel updates on its own wake/poll cycle. "
    + COLOUR_CAVEAT)
_VIEW_PANEL_SRC_ATTR = "data-view-panel-src"
_VIEW_PANEL_CAPTION_ATTR = "data-view-panel-caption"
_VIEW_PANEL_CLOSE_ATTR = "data-view-panel-close"

# One hop to act: the resolve link goes straight to the Airlines
# resolve view for this row's prefix. Route and query-parameter names
# are duplicated, not imported (page modules cannot import each other),
# pinned by test_view_pages.py's cross-module guard.
RESOLVE_LINK_HREF_TEMPLATE = "/airlines?resolve=%s"
RESOLVE_LINK_TEXT = "Name this airline"
UNRESOLVED_LINK_CLASS = "text-label cell-unresolved-link"

_DAY_TODAY_LABEL = "Today"
_DAY_YESTERDAY_LABEL = "Yesterday"

VIEW_PICTURE_LABEL = "View picture"

# Same values home_page.py's own recent-flight thumbnail holds,
# duplicated rather than imported (page modules cannot import each
# other).
ILLUSTRATION_ROUTE_PREFIX = "/illustration/"
_THUMBNAIL_ALT_TEMPLATE = "%s illustration"

# A missing airline gets its own fallback text, distinct from
# panel_render.ROUTE_FALLBACK_TEXT, so the same phrase doesn't appear
# twice in one unresolved row (Type+Airline cell and Route cell).
AIRLINE_FALLBACK_TEXT = "Airline unknown"
# Held as a local literal so the French catalogue can carry it; kept
# equal to panel_render.ROUTE_FALLBACK_TEXT by construction so the
# wording never drifts between the panel and the companion.
ROUTE_FALLBACK_TEXT = "Route unavailable"
assert ROUTE_FALLBACK_TEXT == panel_render.ROUTE_FALLBACK_TEXT

# server/plane/runway_config.py's infer_runway_config(), the only
# writer of confirmed_state, only ever produces "departing" or
# "arriving". Any other non-empty value degrades to a title-cased,
# underscore-stripped rendering via _confirmed_state_label() below.
_CONFIRMED_STATE_LABELS = {
    "departing": "Departing",
    "arriving": "Arriving",
}


def _confirmed_state_label(raw):
    """Maps a runway_events.confirmed_state raw value to its
    presentation label. Falsy input renders as an empty string, never
    the literal word "None". A recognised value maps via
    `_CONFIRMED_STATE_LABELS`; anything else falls back to a
    title-cased, underscore-stripped rendering, so an unexpected state
    still reads as a human label instead of a raw machine value.
    """
    if not raw:
        return ""
    label = _CONFIRMED_STATE_LABELS.get(raw)
    if label is not None:
        return label
    return raw.replace("_", " ").title()


def _runway_label(raw):
    """Maps a runway_events.tracked_runway raw id to
    `server.device_config.runway_label()`'s human label, e.g. "3" ->
    "Runway 3 (07/25)". Only looks the id up when it is a real
    `RUNWAY_IDS` member; an unrecognised id (a stale/foreign value on an
    old row) degrades to the raw id unchanged rather than raising.
    """
    if raw and raw in device_config.RUNWAY_IDS:
        return i18n.t(device_config.runway_label(raw))
    return raw or ""


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


def _view_panel_button_html(name, iso):
    """A "View panel near this time" trigger button, one per row that
    has a nearest render, living inside the expanded detail row beside
    the hex/timestamp/copy buttons the picture belongs with. Reuses
    `.calendar-disconnect-btn`'s small, de-emphasised secondary-action
    treatment. The visible label is the accessible name (no `aria-label`
    duplicate); `VIEW_PANEL_LABEL` survives as the `title` tooltip.
    `name` becomes the trigger source attribute; `iso` is formatted
    through `LIGHTBOX_CAPTION_TEMPLATE` into the caption attribute,
    which `panel-lookup.js` copies verbatim into the lightbox caption
    on open (no client-side templating).
    """
    src = "%s%s" % (_GALLERY_ROUTE_PREFIX, escape_html(name))
    caption = lightbox_caption_text(iso)
    return (
        '<button type="button" class="calendar-disconnect-btn" %s="%s" %s="%s" '
        'title="%s">%s</button>'
    ) % (
        _VIEW_PANEL_SRC_ATTR, src,
        _VIEW_PANEL_CAPTION_ATTR, escape_html(caption),
        escape_html(i18n.t(VIEW_PANEL_LABEL)),
        escape_html(i18n.t(VIEW_PICTURE_LABEL)),
    )


def _lightbox_html():
    """The single shared lightbox `<dialog>`, emitted once per page by
    `render()`, only when at least one row carries a trigger button.
    Its image src/alt and caption text are written by
    `panel-lookup.js` on trigger click; this function only emits the
    static note.
    """
    return (
        '<dialog class="lightbox" id="%s" aria-label="%s">'
        '<img class="lightbox__image" alt="">'
        '<p class="lightbox__caption text-label mono"></p>'
        '<p class="lightbox__note text-body">%s</p>'
        '<button type="button" %s>%s</button>'
        "</dialog>"
    ) % (LIGHTBOX_DIALOG_ID, escape_html(i18n.t(LIGHTBOX_ARIA_LABEL)),
         escape_html(i18n.t(LIGHTBOX_NOTE)), _VIEW_PANEL_CLOSE_ATTR, escape_html(i18n.t("Close")))


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
    `?limit=` value from `ctx["flights_limit"]` and clamps rather than
    rejects an out-of-range result to `None`: a hand-edited URL should
    render a page, not an error, and `HISTORY_ROW_LIMIT` is already the
    hard ceiling `history_rows()` fetches, so clamping upward can never
    ask for a row the query would not return anyway. Total by
    construction: no input, however malformed, ever raises.
    """
    raw = ctx.get("flights_limit")
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

    corroboration_status, corroboration_label = _CORROBORATION_LABELS.get(
        row.get("corroborated"), _DEFAULT_CORROBORATION)
    corroboration_label = i18n.t(corroboration_label)

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
        # illustrations.normalise_airline_key() resolves on the raw
        # value, never the aliased display name.
        "airline_raw": row.get("airline") or "",
        "route_label": route_label,
        "confirmed_state": i18n.t(_confirmed_state_label(row.get("confirmed_state"))),
        "corroboration_status": corroboration_status,
        "corroboration_label": corroboration_label,
        # The long form for the "None" (single-source) state, rendered
        # as status_dot()'s tooltip; "" for True/False, which need none.
        "corroboration_title": i18n.t(_CORROBORATION_TITLES.get(row.get("corroborated"), "")),
        "tracked_runway": _runway_label(row.get("tracked_runway")),
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
    """The escaped, lowercased "{callsign} {hex}" pair for a row's
    `data-filter-text` attribute, computed once per row and reused by
    both the desktop `<tr>` and the mobile `<li>` for the same flight.
    """
    combined = ("%s %s" % (row["callsign"], row["hex"])).strip().lower()
    return escape_html(combined)


def _copy_button_html(value, label):
    """A copy-to-clipboard button plus its `data-copy-feedback` sibling
    span, the exact shape `companion/static/copy-button.js` requires
    (the feedback element must be the button's immediate next sibling).
    The button's SVG icon sits in an `aria-hidden` span, with an empty
    label span as its sibling: copy-button.js writes the transient
    success text into that label span's `textContent` only, never into
    the button itself, which would destroy the icon. `data-copied-text`
    carries the translated success text, read at click time.
    """
    return (
        '<button type="button" class="copy-btn" data-copy-value="%s" '
        'aria-label="%s" data-copied-text="%s">'
        '<span class="copy-btn__icon" aria-hidden="true">%s</span>'
        '<span class="copy-btn__label"></span>'
        '</button>'
        '<span class="visually-hidden" data-copy-feedback role="status" '
        'aria-live="polite"></span>'
    ) % (
        escape_html(value), escape_html(label), escape_html(i18n.t("Copied")),
        layout.icon_html("icon-copy"))


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


def _filter_bar_html(shown, total_available):
    """The filter bar: a `<label>` + search input, a live
    `<span data-filter-count>`, a Clear control, and a hidden-by-default
    empty-state block. Entirely inert without JS: list-filter.js's early
    return leaves the full unfiltered list usable if the script never
    loads. `data-filter-count-template` carries the same translated
    template `count_text` is built from, unformatted, so
    list-filter.js can re-render the count on every keystroke without
    hardcoding English words. `shown` and `total_available` differ once
    a `?limit=` is in force: the live count and empty-state body read
    `shown` honestly, never claiming a search coverage the filter
    doesn't have.
    """
    count_template = i18n.t("%d of %d shown")
    count_text = count_template % (shown, shown)
    if shown < total_available:
        empty_body = i18n.t(_FILTER_EMPTY_BODY_LIMITED_TEMPLATE) % shown
    else:
        empty_body = i18n.t(_FILTER_EMPTY_BODY_TEMPLATE) % shown
    return (
        '<div class="filter-bar">'
        '<label class="text-label" for="%s">%s</label>'
        '<div class="filter-bar__field">'
        "%s"
        # autocomplete="off"/spellcheck="false" suppress Safari's
        # contact/phone-number autofill heuristic on a bare search
        # input with no name; autocapitalize="characters" matches the
        # upper-case tokens (callsigns, hex codes) this filter searches.
        # Safe for matching: list-filter.js compares lower-cased values,
        # so the keyboard's shift state never affects the result. No
        # `name` attribute: never submitted by a form, read by
        # attribute selector instead.
        '<input type="search" id="%s" autocomplete="off" spellcheck="false" autocapitalize="characters" data-filter-input>'
        "</div>"
        '<div class="filter-bar__meta">'
        '<span class="filter-bar__count" data-filter-count '
        'data-filter-count-template="%s">%s</span>'
        '<button type="button" data-filter-clear>%s</button>'
        "</div>"
        "</div>"
        '<div class="empty-state" data-filter-empty hidden>'
        '<p class="empty-state__heading text-heading">%s</p>'
        '<p class="empty-state__body text-body">%s</p>'
        "</div>"
    ) % (
        _FILTER_INPUT_ID, escape_html(i18n.t(_FILTER_LABEL_TEXT)),
        layout.icon_html("icon-search"),
        _FILTER_INPUT_ID,
        escape_html(count_template),
        escape_html(count_text),
        escape_html(i18n.t("Clear")),
        escape_html(i18n.t(_FILTER_EMPTY_HEADING)),
        escape_html(empty_body),
    )


# Mirrors layout.concise_timestamp_html()'s own default fallback string
# exactly, so a caller can't tell the two functions apart by their
# empty-value behaviour.
_CLOCK_CELL_FALLBACK = "no reading yet"


def _when_cell_html(raw_ts, now):
    """The desktop table's When column cell: two stacked lines via
    `_merged_cell()`, never an inline suffix. A local clock primary line
    ("HH:MM", or "D Mon HH:MM" once the row is no longer from today) and
    a relative-age secondary line. The full ISO timestamp lives in the
    detail row's "Full timestamp" pair instead of a `title` attribute
    here. Degrades gracefully: a falsy `raw_ts` renders the fallback
    text with no secondary; an unparseable one renders the raw value the
    same way. Never raises.
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
            secondary = layout.relative_age_text(age) if age is not None else ""
            html = _merged_cell(clock_text, secondary)
    return html


def full_local_time_text(raw_ts):
    """The visible form of a stored timestamp inside a detail row or
    card disclosure: a day-qualified Europe/Paris local clock
    ("27 Aug 10:00"), never the raw ISO string and never monospace —
    mono stays reserved for identifiers, and the raw ISO survives only
    behind the copy control's `data-copy-value`. Built from
    `layout.local_clock_text()`, forced onto its cross-day branch via
    the same sentinel `concise_timestamp_html()`'s `title` uses.
    Degrades to the raw value, unchanged, when it cannot be parsed.
    """
    parsed = layout.parse_iso(raw_ts)
    if parsed is None:
        return raw_ts
    return layout.local_clock_text(parsed, layout._FULL_TIMESTAMP_SENTINEL_NOW)


def _flight_detail_row_html(row, index):
    """The sibling detail `<tr>` immediately following the summary row
    of the same `index`. Content: Hex/Full timestamp/Runway, each
    `<dt>`/`<dd>` pair omitted when its value is absent, never a
    fabricated "—", plus a standalone copy-name button for the
    callsign (already visible on the summary row).

    No `hidden` attribute and no inline style: the no-JS floor is a
    fully visible detail row; flight-rows.js adds the collapsing class
    at load. The cell's content is wrapped in a two-element grid
    reveal because a `<tr>` cannot be a grid container (`display:
    table-row` is discrete, so nothing on the row box can animate) —
    the wrapper moves the animation into the cell instead.
    """
    row_name = _row_copy_name(row["callsign"], row["hex"])
    parts = []
    if row["hex"]:
        parts.append(
            '<div><dt class="text-label">%s</dt><dd class="mono">%s</dd>%s</div>'
            % (
                escape_html(i18n.t("Hex")), escape_html(row["hex"]),
                _copy_button_html(row["hex"], i18n.t(_COPY_HEX_LABEL) % row_name)))
    if row["raw_ts"]:
        parts.append(
            '<div><dt class="text-label">%s</dt><dd class="time-value">%s</dd>%s</div>'
            % (
                escape_html(i18n.t("Full timestamp")),
                escape_html(full_local_time_text(row["raw_ts"])),
                _copy_button_html(row["raw_ts"], i18n.t(_COPY_TIMESTAMP_LABEL) % row_name)))
    if row["tracked_runway"]:
        parts.append(
            '<div><dt class="text-label">%s</dt><dd>%s</dd></div>'
            % (escape_html(i18n.t("Runway")), escape_html(row["tracked_runway"])))
    copy_name_button = (
        _copy_button_html(row["callsign"], i18n.t(_COPY_CALLSIGN_LABEL) % row_name)
        if row["callsign"] else "")
    return (
        '<tr class="flight-detail-row" id="flight-detail-%d" data-row-detail %s="%s">'
        '<td colspan="6">'
        '<div class="flight-detail-row__reveal">'
        '<div class="flight-detail-row__reveal-inner">'
        '<dl class="flight-detail-row__grid">%s</dl>%s%s'
        "</div></div></td>"
        "</tr>"
    ) % (index, layout.REFRESH_ROW_ID_ATTR, escape_html(_row_identity(row)),
         "".join(parts), copy_name_button, row.get("view_panel_html", ""))


def _day_separator_row_html(day, today):
    """One day-separator row: a real table row spanning the table as a
    `<th scope="colgroup">`, carrying the day's label. Deliberately not
    sticky: this function introduces no positioning of any kind.
    """
    return (
        '<tr class="flight-day-row">'
        '<th scope="colgroup" colspan="6" class="text-label">%s</th>'
        "</tr>"
    ) % escape_html(day_label(day, today))


def _history_table_html(formatted_rows, now=None):
    if not formatted_rows:
        return layout.empty_state(i18n.t(_NO_FLIGHTS_HEADING), i18n.t(_NO_FLIGHTS_BODY))

    # The sixth <th> is the visually-hidden "Details" toggle-column
    # header: no data column behind it, so built directly here rather
    # than through the _HEADERS/i18n.t(h) loop.
    header_cells = "".join("<th>%s</th>" % escape_html(i18n.t(h)) for h in _HEADERS)
    header_cells += '<th><span class="visually-hidden">%s</span></th>' % escape_html(
        i18n.t(_DETAILS_HEADER_TEXT))

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
            "<td>%s</td>" % layout.status_dot(
                row["corroboration_status"], row["corroboration_label"],
                row["corroboration_title"], visually_hide_label=True),
        )
        # data-filter-group carries this row's loop index, shared with
        # the <li> at the same index in _history_cards_html(), so
        # list-filter.js counts logical rows once, not once per
        # representation. The row-toggle button matches the
        # visually-hidden "Details" header; data-row-toggle/
        # aria-controls/aria-expanded are flight-rows.js's own contract
        # (a click flips aria-expanded and the matching detail row's
        # collapsed class). The no-JS floor means the sibling detail row
        # is already fully visible without script, so this button is
        # inert chrome in that case. Icon-only: the button's accessible
        # name carries the meaning, via the two data-*-label attributes
        # flight-rows.js writes into aria-label.
        toggle_cell = (
            '<td><button type="button" class="row-toggle" data-row-toggle '
            'aria-expanded="false" aria-controls="flight-detail-%d" '
            'aria-label="%s" %s="%s" %s="%s">'
            '<span class="row-toggle__glyph" aria-hidden="true">%s</span>'
            "</button></td>"
        ) % (
            index,
            escape_html(i18n.t(_TOGGLE_SHOW_LABEL)),
            _TOGGLE_SHOW_LABEL_ATTR, escape_html(i18n.t(_TOGGLE_SHOW_LABEL)),
            _TOGGLE_HIDE_LABEL_ATTR, escape_html(i18n.t(_TOGGLE_HIDE_LABEL)),
            escape_html(_TOGGLE_GLYPH),
        )
        # data-flight-row is the hook flight-rows.js's delegated
        # whole-row click reads. data-filter-group is the loop index
        # (pairs this render's two representations); the stable event
        # identity arrives beside it as its own attribute — one
        # renumbers when a detection lands, the other must not.
        body_rows.append(
            '<tr class="%s" data-flight-row data-filter-text="%s" '
            'data-filter-group="%d" %s="%s" title="%s">%s%s</tr>'
            % (row_class, _filter_text_attr(row), index,
               layout.REFRESH_ROW_ID_ATTR, escape_html(_row_identity(row)),
               escape_html(row["tracked_runway"]), "".join(cells), toggle_cell))
        body_rows.append(_flight_detail_row_html(row, index))

    return (
        '<div class="data-table-wrap" tabindex="0" role="region" '
        'aria-label="%s">'
        '<table class="data-table data-table--flights">'
        "<thead><tr>%s</tr></thead>"
        "<tbody>%s</tbody>"
        "</table>"
        "</div>"
    ) % (escape_html(i18n.t(SCROLLER_ARIA_LABEL)), header_cells, "".join(body_rows))


def _card_thumb_html(airline_raw, state_dir):
    """The phone card's artwork thumbnail, or "" when the airline
    resolves to no artwork file on disk. The same two-call seam
    `home_page._recent_flight_thumb_html()` uses:
    `illustrations.normalise_airline_key()` for the key (resolved from
    the raw stored airline, never the display alias) and
    `illustrations.resolved_illustration_path()` for the "is there
    really a file" test. Never an unconditional `<img>`: a key with no
    file behind it would 404 and render as a broken-image icon.
    """
    key = illustrations.normalise_airline_key(airline_raw)
    if not key or illustrations.resolved_illustration_path(key, state_dir) is None:
        return ""
    alt_text = i18n.t(_THUMBNAIL_ALT_TEMPLATE) % panel_render.display_airline_name(airline_raw)
    return (
        '<img class="history-card__thumb" loading="lazy" decoding="async" '
        'src="%s%s.png" alt="%s">'
    ) % (ILLUSTRATION_ROUTE_PREFIX, escape_html(key), escape_html(alt_text))


def _history_cards_html(formatted_rows, now=None):
    """Mobile compact-card representation, one `<li>` per row, built
    from the same `formatted_rows` list `_history_table_html()`
    consumes. Returns "" for an empty list. Must render as a DOM
    sibling immediately before the desktop table: style.css's
    `.history-cards ~ .data-table-wrap` breakpoint toggle depends on
    this order. Primary/secondary lines carry callsign/time/route/
    state; a nested `<details>` disclosure carries the rest.
    """
    if not formatted_rows:
        return ""
    items = []
    for index, row in enumerate(formatted_rows):
        # Mirrors _callsign_hex_cell()'s desktop hex-only branch: when a
        # row has no callsign but has a hex, the primary slot carries
        # the hex (never blank) with a NO_CALLSIGN_NOTE_TEXT note.
        if row["callsign"]:
            primary_value_html = (
                '<span class="cell-primary mono">%s</span>'
                % escape_html(row["callsign"]))
        elif row["hex"]:
            primary_value_html = (
                '<span class="cell-primary mono">%s</span>'
                '<span class="cell-secondary">%s</span>'
            ) % (escape_html(row["hex"]), escape_html(i18n.t(NO_CALLSIGN_NOTE_TEXT)))
        else:
            primary_value_html = '<span class="cell-primary mono"></span>'
        primary = (
            '<div class="history-card__primary">'
            "%s"
            '<span class="history-card__time">%s</span>'
            "</div>"
        ) % (
            primary_value_html,
            layout.concise_timestamp_html(row["raw_ts"], now),
        )
        # The separator is the module's existing middle dot
        # (CELL_SEPARATOR_TEXT/CLASS), the same pair _merged_cell()
        # emits on the desktop side, reused rather than invented anew.
        secondary = (
            '<div class="history-card__secondary">'
            "<span>%s</span>"
            '<span class="%s">%s</span>'
            "<span>%s</span>"
            "</div>"
        ) % (
            escape_html(row["route_label"]),
            CELL_SEPARATOR_CLASS, escape_html(CELL_SEPARATOR_TEXT),
            escape_html(row["confirmed_state"]),
        )
        # All three mobile copy buttons (callsign, hex, full timestamp)
        # live inside this <details> disclosure, including the callsign
        # one already visible on the primary line, so the copy
        # affordance has a home alongside its siblings.
        is_unresolved = row["airline_label"] == AIRLINE_FALLBACK_TEXT
        airline_display = i18n.t(row["airline_label"]) if is_unresolved else row["airline_label"]
        # The airline and artwork sit on the card's own face, outside
        # the disclosure; the resolve link sits outside it too (see the
        # card assembly below), so the mobile card carries the same
        # affordances as the desktop cell.
        airline_line = (
            '<div class="history-card__airline">%s'
            '<span class="history-card__airline-name">%s</span>'
            "</div>"
        ) % (
            row.get("thumb_html", ""),
            escape_html(airline_display),
        )
        row_name = _row_copy_name(row["callsign"], row["hex"])
        details = (
            '<details class="history-card__details">'
            '<summary class="history-card__summary">'
            '<div class="history-card__face">%s%s%s</div>'
            '<span class="visually-hidden">%s</span>'
            "</summary>"
            "<dl>"
            '<dt>%s</dt><dd class="mono">%s%s</dd>'
            "<dt>%s</dt><dd>%s</dd>"
            "<dt>%s</dt><dd>%s</dd>"
            "<dt>%s</dt><dd>%s</dd>"
            '<dt>%s</dt><dd class="mono">%s%s</dd>'
            '<dt>%s</dt><dd class="time-value">%s%s</dd>'
            "</dl>%s"
            "</details>"
        ) % (
            primary, secondary, airline_line,
            escape_html(i18n.t("More details")),
            escape_html(i18n.t("Callsign")),
            escape_html(row["callsign"]),
            _copy_button_html(row["callsign"], i18n.t(_COPY_CALLSIGN_LABEL) % row_name),
            escape_html(i18n.t("Aircraft")),
            escape_html(row["aircraft_type_label"]),
            escape_html(i18n.t("Corroboration")),
            layout.status_dot(
                row["corroboration_status"], row["corroboration_label"],
                row["corroboration_title"]),
            escape_html(i18n.t("Runway")),
            escape_html(row["tracked_runway"]),
            escape_html(i18n.t("Hex")),
            escape_html(row["hex"]),
            _copy_button_html(row["hex"], i18n.t(_COPY_HEX_LABEL) % row_name),
            # The visible timestamp is the Paris local clock; the raw
            # ISO survives only in the copy control's data-copy-value.
            escape_html(i18n.t("Full timestamp")),
            escape_html(full_local_time_text(row["raw_ts"])),
            _copy_button_html(row["raw_ts"], i18n.t(_COPY_TIMESTAMP_LABEL) % row_name),
            row.get("view_panel_html", ""),
        )
        # The card's three face blocks sit inside <details> as its
        # <summary>, so a tap anywhere opens it through the native
        # disclosure, no script needed. The resolve link stays out of
        # the summary deliberately: inside it, it would join the
        # disclosure's accessible name and compete for activation. It
        # keeps a visible home on the card face, after the disclosure.
        resolve_link = _row_resolve_link_html(row)
        resolve_html = (
            '<div class="history-card__resolve">%s</div>' % resolve_link
            if resolve_link else "")
        items.append(
            '<li class="history-card" data-filter-text="%s" '
            'data-filter-group="%d" %s="%s">%s%s</li>'
            % (_filter_text_attr(row), index,
               layout.REFRESH_ROW_ID_ATTR, escape_html(_row_identity(row)),
               details, resolve_html))
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
    state_dir = ctx["state_dir"]
    now = ctx.get("now") or history_db.utc_now_iso()
    rows = _safe_query(state_dir, history_rows)

    # Flights sits on the same self-refreshing loop the other pages use:
    # freshness.js returns at its first guard on any page with no
    # [data-loaded-at], so this line is what keeps it on the loop.
    header = layout.page_header(
        i18n.t(PAGE_TITLE), purpose=i18n.t(PAGE_PURPOSE_TEMPLATE) % HISTORY_ROW_LIMIT,
        freshness_html=layout.freshness_line_html(now))

    # gallery_entries_list is the input to nearest_gallery_entry() below,
    # which every per-row "View panel near this time" trigger depends on.
    gallery_entries_list = ctx.get("gallery_entries") or []

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
            match = nearest_gallery_entry(gallery_entries_list, row["raw_ts"])
            row["view_panel_html"] = (
                _view_panel_button_html(match[0], match[1]) if match else "")
            # The phone card's artwork thumbnail, resolved once per row
            # for the same reason as the view-panel match. The desktop
            # table does not render it: no room in its width budget.
            row["thumb_html"] = _card_thumb_html(row["airline_raw"], state_dir)
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
                _filter_bar_html(len(visible_rows), total_available)
                + _history_cards_html(visible_rows, now)
                + _history_table_html(visible_rows, now)
                + _show_more_html(len(visible_rows), total_available))

    return header + body + lightbox_html
