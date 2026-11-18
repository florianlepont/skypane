"""Home's statistics card: today's flights on a per-hour timeline, and the last
seven days as bars with the most seen airline.

A pure builder over the results of `server.history_db.home_day_timeline`,
`home_week_totals` and `home_airline_highlights`. Server-drawn inline SVG and
plain markup only: no script, no chart library, no inline style attribute.
The Day and Week views are native radios, so the switch works without
script; the stylesheet shows the panel of the checked radio
(`.home-stats:has(#home-stats-week:checked)`). Every colour is a design token
used through `var()` in an SVG attribute, so the card follows Light and Dark.
"""
from datetime import date

import companion.i18n as i18n
import companion.prefs as prefs
import companion.ui_segmented as ui_segmented
from companion.layout import escape_html
from server.plane import render as panel_render

PERIOD_NAME = "home-stats-period"
DAY_RADIO_ID = "home-stats-day"
WEEK_RADIO_ID = "home-stats-week"

DAY_TEXT = i18n.msg("home.stats_day", "Day")
WEEK_TEXT = i18n.msg("home.stats_week", "Week")
FLIGHTS_TODAY_MANY = i18n.msg("home.stats_flights_today", "flights today")
FLIGHTS_TODAY_ONE = i18n.msg("home.stats_flight_today", "flight today")
FLIGHTS_WEEK_MANY = i18n.msg("home.stats_flights_week", "flights in 7 days")
FLIGHTS_WEEK_ONE = i18n.msg("home.stats_flight_week", "flight in 7 days")
ARRIVALS_MANY = i18n.msg("home.stats_arrivals", "%d arrivals")
ARRIVALS_ONE = i18n.msg("home.stats_arrival", "%d arrival")
DEPARTURES_MANY = i18n.msg("home.stats_departures", "%d departures")
DEPARTURES_ONE = i18n.msg("home.stats_departure", "%d departure")
MOST_SEEN_TEXT = i18n.msg("home.stats_most_seen", "most seen · %d")
NEW_AIRLINES_MANY = i18n.msg("home.stats_new_airlines", "new airlines")
NEW_AIRLINES_ONE = i18n.msg("home.stats_new_airline", "new airline")
TIMELINE_LABEL = i18n.msg("home.stats_timeline_label", "Flights by hour of the day")
WEEKDAY_TEXTS = (
    i18n.msg("home.stats_mon", "Mon"), i18n.msg("home.stats_tue", "Tue"),
    i18n.msg("home.stats_wed", "Wed"), i18n.msg("home.stats_thu", "Thu"),
    i18n.msg("home.stats_fri", "Fri"), i18n.msg("home.stats_sat", "Sat"),
    i18n.msg("home.stats_sun", "Sun"))

# Timeline geometry in SVG units: 12 per hour, so a phone-width card draws it
# about one to one. The axis is the middle line; departures are drawn above
# it, arrivals below and lighter.
_UNITS_PER_HOUR = 12
_TIMELINE_WIDTH = 24 * _UNITS_PER_HOUR
_TIMELINE_HEIGHT = 64
_AXIS_Y = 32
_TICK_LENGTH = 20
_ARRIVAL_OPACITY = "0.55"
_HOURS_LABELS = ("0 h", "6 h", "12 h", "18 h", "24 h")
# The tallest bar, in px; the others scale to it.
_BAR_MAX_PX = 60
_BAR_MIN_PX = 2


def _plural(count, one, many):
    """`one` for a count of one (and for zero in French), else `many`."""
    singular = count == 1 or (count == 0 and prefs.current_lang() == "fr")
    return one if singular else many


def _split_html(arriving, departing):
    return "%s<br>%s" % (
        escape_html(i18n.t(_plural(arriving, ARRIVALS_ONE, ARRIVALS_MANY)) % arriving),
        escape_html(i18n.t(_plural(departing, DEPARTURES_ONE, DEPARTURES_MANY)) % departing))


def _head_html(total, caption, arriving, departing):
    return (
        '<div class="home-stats__head"><div>'
        '<div class="home-stats__big tnum">%d</div>'
        '<div class="home-stats__caption">%s</div></div>'
        '<div class="home-stats__split tnum">%s</div></div>'
    ) % (total, escape_html(caption), _split_html(arriving, departing))


def _quiet_rects(quiet_windows):
    """One band per stretch of the day inside a quiet-hours window; a window
    that crosses midnight is two bands."""
    rects = []
    for start, end in quiet_windows or ():
        spans = [(start, end)] if start < end else [(start, 24.0), (0.0, end)]
        for first, last in spans:
            if last <= first:
                continue
            rects.append(
                '<rect class="home-stats__quiet" x="%.1f" y="8" width="%.1f" height="48" '
                'rx="8" fill="var(--color-secondary)"/>' % (
                    first * _UNITS_PER_HOUR, (last - first) * _UNITS_PER_HOUR))
    return "".join(rects)


def _tick_html(tick):
    departing = tick["state"] == "departing"
    x = tick["at"] * _UNITS_PER_HOUR
    y1, y2 = ((_AXIS_Y - _TICK_LENGTH, _AXIS_Y) if departing
              else (_AXIS_Y, _AXIS_Y + _TICK_LENGTH))
    return (
        '<line class="home-stats__tick home-stats__tick--%s" x1="%.1f" x2="%.1f" y1="%d" y2="%d" '
        'stroke="var(--color-accent)" stroke-width="4" stroke-linecap="round" '
        'vector-effect="non-scaling-stroke"%s/>'
    ) % ("departing" if departing else "arriving", x, x, y1, y2,
         "" if departing else ' opacity="%s"' % _ARRIVAL_OPACITY)


def _timeline_html(ticks, now_hour, quiet_windows):
    now = ""
    if now_hour is not None and 0 <= now_hour <= 24:
        now = ('<rect class="home-stats__now" x="%.1f" y="0" width="2" height="%d" '
               'fill="var(--color-status-error)"/>' % (now_hour * _UNITS_PER_HOUR - 1, _TIMELINE_HEIGHT))
    return (
        '<svg class="home-stats__timeline" viewBox="0 0 %d %d" width="100%%" height="%d" '
        'preserveAspectRatio="none" role="img" aria-label="%s">%s'
        '<rect class="home-stats__axis" x="0" y="%d" width="%d" height="2" fill="var(--color-border)"/>'
        '%s%s</svg>'
    ) % (_TIMELINE_WIDTH, _TIMELINE_HEIGHT, _TIMELINE_HEIGHT,
         escape_html(i18n.t(TIMELINE_LABEL)), _quiet_rects(quiet_windows),
         _AXIS_Y - 1, _TIMELINE_WIDTH, "".join(_tick_html(t) for t in ticks), now)


def _hours_html():
    return '<div class="home-stats__hours tnum">%s</div>' % "".join(
        "<span>%s</span>" % label for label in _HOURS_LABELS)


def _day_panel_html(timeline, now_hour, quiet_windows):
    total = timeline["arriving"] + timeline["departing"]
    caption = i18n.t(_plural(total, FLIGHTS_TODAY_ONE, FLIGHTS_TODAY_MANY))
    return (
        '<div class="home-stats__panel home-stats__panel--day">%s%s%s</div>' % (
            _head_html(total, caption, timeline["arriving"], timeline["departing"]),
            _timeline_html(timeline["ticks"], now_hour, quiet_windows), _hours_html()))


def _bar_html(entry, tallest, is_today):
    weekday = WEEKDAY_TEXTS[date.fromisoformat(entry["day"]).weekday()]
    height = max(_BAR_MIN_PX, round(entry["total"] / tallest * _BAR_MAX_PX)) if tallest else _BAR_MIN_PX
    return (
        '<div class="home-stats__bar-col%s"><span class="home-stats__value tnum">%d</span>'
        '<svg class="home-stats__bar" width="100%%" height="%d" aria-hidden="true"></svg>'
        '%s</div>'
    ) % (" home-stats__bar-col--today" if is_today else "", entry["total"], height,
         escape_html(i18n.t(weekday)))


def _facts_html(highlights):
    """The most seen airline and, when there is any, the count of new ones."""
    most = (highlights or {}).get("most_seen")
    if not most:
        return ""
    name = panel_render.display_airline_name(most["airline"]) or most["airline"]
    facts = '<div><b>%s</b>%s</div>' % (
        escape_html(name), escape_html(i18n.t(MOST_SEEN_TEXT) % most["count"]))
    new = len(highlights.get("new_airlines") or ())
    if new:
        facts += '<div><b class="tnum">+%d</b>%s</div>' % (
            new, escape_html(i18n.t(NEW_AIRLINES_ONE if new == 1 else NEW_AIRLINES_MANY)))
    return '<div class="home-stats__facts">%s</div>' % facts


def _week_panel_html(week, highlights):
    total = sum(d["total"] for d in week)
    arriving = sum(d["arriving"] for d in week)
    departing = sum(d["departing"] for d in week)
    tallest = max((d["total"] for d in week), default=0)
    bars = "".join(
        _bar_html(entry, tallest, index == len(week) - 1) for index, entry in enumerate(week))
    return (
        '<div class="home-stats__panel home-stats__panel--week">%s'
        '<div class="home-stats__bars">%s</div>%s</div>' % (
            _head_html(total, i18n.t(_plural(total, FLIGHTS_WEEK_ONE, FLIGHTS_WEEK_MANY)),
                       arriving, departing),
            bars, _facts_html(highlights)))


def _period_switch_html():
    return ui_segmented.segmented_radios_html(
        [(DAY_RADIO_ID, PERIOD_NAME, "day", i18n.t(DAY_TEXT), "", True),
         (WEEK_RADIO_ID, PERIOD_NAME, "week", i18n.t(WEEK_TEXT), "", False)],
        extra_class="home-stats__period")


def stats_card_html(timeline, week, highlights=None, now_hour=None, quiet_windows=()):
    """The statistics card with its Day and Week switch.

    `timeline`, `week` and `highlights` are the results of the three
    `history_db.home_*` reads. `now_hour` is the local time of day as a float
    (14.5 for 14:30) for the "now" marker, `quiet_windows` a sequence of
    `(start_hour, end_hour)` floats drawn as quiet bands. No flight at all
    renders the same card at zero (an empty timeline and flat bars), with no
    airline facts."""
    return (
        '<div class="home-stats reveal">%s<div class="home-stats__card">%s%s</div></div>' % (
            _period_switch_html(), _day_panel_html(timeline, now_hour, quiet_windows),
            _week_panel_html(week, highlights)))
