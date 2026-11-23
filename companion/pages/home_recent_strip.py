"""Home's recent-flights strip: a heading with the link to Flights, then one
portrait tile per recent flight with its callsign and "Arrival · 12 min".

A pure builder over history rows (newest first, repeated passes already
folded). A tile shows, in this order, the archived render that belongs to the
flight (the one stored with it, or for an older row one stamped inside the
Flights match window, through `history_page.matching_gallery_entry`, so both
pages agree), else the airline's own illustration, else a plane chip. Neither
fallback claims to be a picture of the flight. With no flight the strip is
the empty state.
"""
import companion.device_scope as device_scope
import companion.flight_card as flight_card
import companion.i18n as i18n
import companion.illustration_normalize as illustration_normalize
import companion.layout as layout
from companion.layout import escape_html
from companion.pages import history_page
from server.plane import illustrations

GALLERY_ROUTE_PREFIX = "/gallery/"
FLIGHTS_ROUTE = "/flights"
HEADING_ID = "home-flights"
# The tile is a portrait frame: 3 wide for 4 tall; a landscape frame's tile is
# 5 wide for 3 tall (the stylesheet's `--landscape` modifier).
TILE_WIDTH = 112
TILE_HEIGHT = 149
ILLUSTRATION_WIDTH = min(illustration_normalize.THUMBNAIL_WIDTHS)

HEADING_TEXT = i18n.msg("home.strip_heading", "Recent flights")
SEE_ALL_TEXT = i18n.msg("home.see_all_flights", "See all flights")
NO_FLIGHTS_HEADING = i18n.msg("home.no_flights_yet", "No flights yet.")
NO_FLIGHTS_BODY = i18n.msg(
    "home.the_first_aircraft_the_frame_detects_on_the",
    "The first aircraft the frame detects on the watched runway will "
    "appear here.")
ARRIVAL_TEXT = i18n.msg("home.strip_arrival", "Arrival")
DEPARTURE_TEXT = i18n.msg("home.strip_departure", "Departure")
OVERHEAD_TEXT = i18n.msg("home.overhead", "Overhead")
_DIRECTION_TEXTS = {
    "arriving": ARRIVAL_TEXT, "departing": DEPARTURE_TEXT, "overhead": OVERHEAD_TEXT}


def direction_text(state):
    """The message for a confirmed state ("Arrival", "Departure", "Overhead"),
    or None for any other."""
    return _DIRECTION_TEXTS.get(state)


def _age_text(ts, now):
    """"12 min", "3 h" or "2 d": the age is the same in both languages."""
    age = layout.age_seconds(ts, now)
    if age is None:
        return ""
    age = max(0, int(age))
    if age < 3600:
        return "%d min" % (age // 60)
    if age < 86400:
        return "%d h" % (age // 3600)
    return "%d d" % (age // 86400)


def _picture_name(row, gallery_entries):
    """The archived render's file name for this flight, or None. A row that
    stores its render names it (and has none once the gallery pruned that
    file); only a row from before the name was stored uses the time window."""
    stored = row.get("gallery_name")
    if stored is None:
        match = history_page.matching_gallery_entry(gallery_entries, row.get("ts"))
        return match[0] if match else None
    return stored if stored in (gallery_entries or ()) else None


def _illustration_src(row, state_dir):
    airline = row.get("airline")
    key = illustrations.normalise_airline_key(airline) if airline else None
    key = illustrations.display_key(key, state_dir) if key else None
    if not key:
        return None
    return device_scope.scoped(
        flight_card.ILLUSTRATION_ROUTE_PREFIX + key + ".png"
    ) + illustration_normalize.thumbnail_query(
        illustration_normalize.cache_buster(key, state_dir), ILLUSTRATION_WIDTH)


def _frame_html(row, state_dir, gallery_entries):
    name = _picture_name(row, gallery_entries)
    if name:
        return (
            '<div class="home-strip__frame home-strip__frame--render">'
            '<img src="%s" alt="" width="%d" height="%d" loading="lazy" decoding="async"></div>'
        ) % (escape_html(device_scope.scoped(GALLERY_ROUTE_PREFIX + name)),
             TILE_WIDTH, TILE_HEIGHT)
    src = _illustration_src(row, state_dir)
    if src:
        return (
            '<div class="home-strip__frame home-strip__frame--illustration">'
            '<img src="%s" alt="" width="%d" height="%d" loading="lazy" decoding="async"></div>'
        ) % (escape_html(src), TILE_WIDTH, TILE_HEIGHT)
    return (
        '<div class="home-strip__frame home-strip__frame--none" aria-hidden="true">%s</div>'
    ) % layout.icon_html("icon-plane", 32)


def _tile_html(row, now, state_dir, gallery_entries):
    callsign = row.get("callsign") or row.get("hex") or "—"
    direction = _DIRECTION_TEXTS.get(row.get("confirmed_state"))
    detail = " · ".join(part for part in (
        i18n.t(direction) if direction else "", _age_text(row.get("ts"), now)) if part)
    return (
        '<figure class="home-strip__tile">%s<figcaption>%s <span>%s</span></figcaption></figure>'
    ) % (_frame_html(row, state_dir, gallery_entries), escape_html(callsign),
         escape_html(detail))


def _head_html():
    return (
        '<div class="home-strip__head"><h2 class="home-strip__label" id="%s">%s</h2>'
        '<a class="home-strip__more" href="%s">%s%s</a></div>'
    ) % (HEADING_ID, escape_html(i18n.t(HEADING_TEXT)),
         escape_html(device_scope.scoped(FLIGHTS_ROUTE)), escape_html(i18n.t(SEE_ALL_TEXT)),
         layout.icon_html("icon-chevron-right", 16))


def recent_strip_html(rows, now, state_dir, gallery_entries=(), landscape=False):
    """The recent-flights section. `rows` are history rows, newest first;
    `now` the request's ISO time; `gallery_entries` the archived render file
    names; `landscape` draws each tile in a landscape frame's shape. No row
    renders the empty state under the same heading."""
    if rows:
        body = '<div class="home-strip__tiles">%s</div>' % "".join(
            _tile_html(row, now, state_dir, gallery_entries) for row in rows)
    else:
        body = layout.empty_state(
            i18n.t(NO_FLIGHTS_HEADING), i18n.t(NO_FLIGHTS_BODY), compact=True)
    return '<section class="home-strip%s reveal" aria-labelledby="%s">%s%s</section>' % (
        " home-strip--landscape" if landscape else "", HEADING_ID, _head_html(), body)
