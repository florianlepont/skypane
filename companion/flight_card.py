"""The pieces of the phone flight card that Flights and Home both render.

Flights shows each detection as a full boarding-pass card. Home shows the
latest few as slim tiles. Both use the same artwork plate, route line
(ORY ┄✈┄ KEF with the direction under the plane) and time column, so the
two pages share one markup and one set of `history-card__*` rules in
style.css. Page modules cannot import each other, which is why these
helpers live here.
"""
import companion.i18n as i18n
import companion.layout as layout
from companion.layout import escape_html
from server.plane import illustrations
from server.plane import render as panel_render

ILLUSTRATION_ROUTE_PREFIX = "/illustration/"
# "%s illustration" is owned by companion/i18n_fr/home.py.
THUMBNAIL_ALT_TEMPLATE = i18n.msg("home.illustration", "%s illustration")
# The dashed placeholder where an airline has no artwork.
NO_ILLUSTRATION_TEXT = i18n.msg("flights.no_illustration", "No illustration")
# Held as a local literal so the French catalogue can carry it. It equals
# panel_render.ROUTE_FALLBACK_TEXT by construction, so the wording never
# drifts between the panel and the companion.
ROUTE_FALLBACK_TEXT = i18n.msg("flights.route_unavailable", "Route unavailable")
assert ROUTE_FALLBACK_TEXT == panel_render.ROUTE_FALLBACK_TEXT
CLOCK_FALLBACK_TEXT = i18n.msg("flights.no_reading_yet", "no reading yet")


def art_html(airline_raw, state_dir):
    """The artwork plate, or "" when the airline resolves to no artwork
    file on disk. The key comes from the raw stored airline, never the
    display alias. The `<img>` is never unconditional: a key with no file
    behind it would 404 and render as a broken-image icon.
    """
    key = illustrations.normalise_airline_key(airline_raw)
    if not key or illustrations.resolved_illustration_path(key, state_dir) is None:
        return ""
    alt_text = i18n.t(THUMBNAIL_ALT_TEMPLATE) % panel_render.display_airline_name(airline_raw)
    return (
        '<img class="history-card__art" loading="lazy" decoding="async" '
        'src="%s%s.png" alt="%s">'
    ) % (ILLUSTRATION_ROUTE_PREFIX, escape_html(key), escape_html(alt_text))


def art_or_placeholder_html(art):
    """`art` from `art_html()`, or the dashed "No illustration" plate."""
    return art or (
        '<span class="history-card__art history-card__art--empty">%s</span>'
        % escape_html(i18n.t(NO_ILLUSTRATION_TEXT)))


def stub_html(art, raw_ts, now, clock_now=None):
    """The card's stub, below the tear line: the artwork plate (`art`
    from `art_html()`, or the dashed placeholder when it is "") and, on
    the same row, the time column from `when_html()`."""
    return '<div class="history-card__stub">%s%s</div>' % (
        art_or_placeholder_html(art), when_html(raw_ts, now, clock_now))


def route_html(origin, destination, state_raw, direction_label):
    """The route line: origin, a dashed track carrying the plane glyph
    with the direction label under it, then destination. The home end
    (the origin of a departure, the destination of an arrival) is muted
    so the far airport reads first. With no route, the shared "Route
    unavailable" fallback takes the origin slot instead of two codes.
    `direction_label` is already translated.
    """
    if origin and destination:
        home_class = " history-card__code--home"
        codes = (
            '<span class="history-card__code history-card__code--from%s">%s</span>'
            '<span class="history-card__code history-card__code--to%s">%s</span>'
        ) % (home_class if state_raw == "departing" else "", escape_html(origin),
             home_class if state_raw == "arriving" else "", escape_html(destination))
    else:
        codes = (
            '<span class="history-card__code history-card__code--from '
            'history-card__code--none">%s</span>' % escape_html(i18n.t(ROUTE_FALLBACK_TEXT)))
    direction = (
        '<span class="history-card__dir">%s</span>' % escape_html(direction_label)
        if direction_label else "")
    return (
        '<div class="history-card__route">%s'
        '<span class="history-card__track">%s</span>%s</div>'
    ) % (codes, layout.icon_html("icon-plane", 16, "history-card__plane"), direction)


def when_html(raw_ts, now, clock_now=None):
    """The time column: the local clock time over its live relative age.
    `clock_now`, when given, lets the clock gain a date for an event on
    another day (a list with no day headers needs it); Flights leaves it
    out because its day headers carry the date. A falsy timestamp shows
    the fallback text, an unparseable one shows the raw value; never
    raises.
    """
    parsed = layout.parse_iso(raw_ts) if raw_ts else None
    if parsed is None:
        clock = raw_ts or i18n.t(CLOCK_FALLBACK_TEXT)
        return (
            '<span class="history-card__when">'
            '<span class="time-value time-value--primary">%s</span></span>'
        ) % escape_html(clock)
    age_html = ""
    if layout.age_seconds(raw_ts, now) is not None:
        age_html = '<span class="time-value time-value__age">%s</span>' % (
            layout.relative_time_html(raw_ts, now))
    now_parsed = layout.parse_iso(clock_now) if clock_now else None
    return (
        '<span class="history-card__when">'
        '<span class="time-value time-value--primary">%s</span>%s</span>'
    ) % (escape_html(layout.local_clock_text(parsed, now_parsed)), age_html)
