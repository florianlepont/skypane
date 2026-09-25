"""The Home page: answers whether the frame is alive, what it is
showing, and what it has shown recently.

Renders the shared Frame strip, three status tiles in a
`.dashboard-grid.home-status-grid`, then a two-column row holding the
current picture beside the recent flights. A recent-flight row gets a
thumbnail only when a real illustration file resolves for that
airline, since a recognised name with no artwork file would otherwise
404 as a broken image. The recent-flight rows and the current
picture's flight line share one `history_db` read.
"""
import html
import re
from datetime import datetime, time, timedelta

import companion.battery as battery
import companion.draw as draw
import companion.frame_state as frame_state
import companion.i18n as i18n
import companion.layout as layout
import companion.wake as wake
from companion.layout import escape_html
from server import device_config, history_db
from server.plane import illustrations
# The same presentation-only airline alias Flights applies via
# history_page.py's panel_render.display_airline_name() call.
# illustrations.normalise_airline_key() still resolves on the raw
# stored airline string — only user-visible text is aliased.
from server.plane import render as panel_render

PAGE_TITLE = "Home"
PAGE_PURPOSE = "Your frame at a glance."

RECENT_FLIGHTS_LIMIT = 5
RECENT_FLIGHTS_HEADING = "Recent flights"
RECENT_FLIGHTS_LINK_TEXT = "See all flights"
NO_FLIGHTS_HEADING = "No flights yet."
NO_FLIGHTS_BODY = (
    "The first aircraft the frame detects on the watched runway will "
    "appear here.")
FLIGHTS_ROUTE = "/flights"

# The read is bounded as a correctness constraint, not a performance one:
# recent_device_health() returns the newest N rows, so a limit smaller
# than a day's check-ins would silently hand the band a few hours and
# caption them as the whole day. _day_band_html() below also detects a
# truncated read and stops the caption claiming a total.
DAY_BAND_ROW_LIMIT = 3000

DAY_BAND_HEADING = "Today"
# The canvas's accessible name; a named group rather than aria-hidden,
# since the band is the only statement of this data.
DAY_BAND_LABEL = "The frame's check-ins through the day, midnight to midnight"
DAY_BAND_HOUR_LABELS = ("00:00", "12:00", "24:00")
DAY_BAND_EMPTY_TEXT = "No check-ins recorded on %s."
DAY_BAND_ONE_TEXT = "1 check-in on %s."
DAY_BAND_COUNT_TEXT = "%s check-ins on %s."
# Appended only when draw.day_band() reports a collapse, so a reader who
# counts the marks and gets fewer is not left thinking the band lost some.
DAY_BAND_COLLAPSED_TEXT = (
    "Some marks are merged — check-ins closer together than the band can "
    "separate are drawn as one.")
DAY_BAND_QUIET_TEXT = "Shaded: quiet hours, %s to %s."

# Duplicated here rather than imported from airlines_page.py — a page
# module cannot import a sibling page module.
ILLUSTRATION_ROUTE_PREFIX = "/illustration/"
THUMBNAIL_ALT_TEMPLATE = "%s illustration"

RENDERED_CAPTION_TEMPLATE = "Rendered %s"
NO_PANEL_HEADING = "Nothing rendered yet."
NO_PANEL_BODY = (
    "The server saves a copy of each picture it sends to the frame; the "
    "latest one will appear here.")
PANEL_ALT_TEXT = "The picture currently on the frame"
GALLERY_ROUTE_PREFIX = "/gallery/"

DIRECTION_DEPARTING_TEXT = "Departing"
DIRECTION_ARRIVING_TEXT = "Arriving"

# The screen/quiet-hours switches and the next-update headline render
# once in the shared Frame strip helper (see render() below); Refresh-now
# lives on Device's own Manual refresh section instead.

STATUS_HEADING = "Status"
# "Frame" is reserved for the shared Frame strip's own <h2> heading,
# rendered directly above this tile; only this tile's caption moves.
FRAME_ROW_LABEL = "Check-ins"
BATTERY_ROW_LABEL = "Battery"
DATA_ROW_LABEL = "Flight data"
HEALTH_LINK_TEXT = "See details on Health"

# Stays byte-identical to health_page.DEVICE_STATE_TEXT's own values —
# see companion/i18n_fr/home.py's comment for why the two dicts must
# never be edited to differ. "off" is a held (quiet-hours) frame, a
# genuine fourth state, reusing health_page.py's own neutral wording.
FRAME_STATE_TEXT = {
    "ok": "Checking in normally",
    "warn": "Has not checked in for a while",
    "error": "Has not checked in for a long time",
    "off": "Asleep for quiet hours",
}
# The one mapping from frame_state's three real states to this tile's
# vocabulary — byte-identical in shape to
# health_page._FRAME_STATE_TO_DEVICE_STATE. STATE_UNKNOWN is absent
# deliberately: _status_tiles_html() falls back to the health-state
# value instead, the one case frame_state.py cannot resolve.
_FRAME_STATE_TO_TILE_STATE = {
    frame_state.STATE_DUE: "ok",
    frame_state.STATE_HELD: "off",
    frame_state.STATE_LATE: "warn",
}
DATA_STATE_TEXT = {
    "ok": "Up to date",
    "warn": "A little stale",
    "error": "Stale — the server may be down",
    # Byte-identical to health_page.PIPELINE_STATE_TEXT["off"]: a
    # pipeline that has never run is the same neutral fact on both
    # pages, never Home's "A little stale" wording.
    "off": "No detection yet",
}
BATTERY_STATE_TEXT = {
    "ok": "Healthy",
    "warn": "Dropping quickly",
    "error": "Dropping quickly",
}
NO_READING_TEXT = "No reading yet"

_TAG_RE = re.compile(r"<[^>]+>")
# health_page.py's pipeline_html fragment is two or three stacked
# <p>...</p> blocks; device_detail_html is a single bare <span> with no
# <p> wrapper. _BLOCK_RE finds each block's inner markup so
# _plain_text_from_markup() can join separate sentences with " · "
# instead of running them together with no punctuation between them.
_BLOCK_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.DOTALL)


def _plain_text_from_markup(fragment):
    """Strip tags and reverse HTML-entity escaping from a pre-built,
    already-escaped markup fragment — health_page's detail-only
    health-state fields, which produce raw markup the same way
    `layout.concise_timestamp_html()` does (callers interpolate the
    return value verbatim, never re-escape it).

    The shared status-row primitive escapes its `detail` parameter, so
    passing the fragment straight through would turn its own tags into
    visible text. Strip the tags, then reverse the entity escaping the
    fragment's own builder already applied, so the row primitive
    re-encodes the text exactly once, not twice. Two or more top-level
    `<p>` blocks are joined with " · "; a fragment with no `<p>` blocks
    falls back to the original single-block behaviour.
    """
    if not fragment:
        return ""
    blocks = _BLOCK_RE.findall(fragment)
    if not blocks:
        spaced = _TAG_RE.sub(" ", fragment)
        return " ".join(html.unescape(spaced).split())
    parts = []
    for block in blocks:
        spaced = _TAG_RE.sub(" ", block)
        text = " ".join(html.unescape(spaced).split())
        if text:
            parts.append(text)
    return " · ".join(parts)


def _safe_query(state_dir, fn):
    try:
        with history_db.open_db(state_dir) as conn:
            return fn(conn)
    except Exception:
        return None


def _recent_flights(conn):
    return history_db.recent_runway_events(conn, limit=RECENT_FLIGHTS_LIMIT)


def _latest_battery(conn):
    return history_db.latest_device_health(conn)


def _direction_text(raw):
    if raw == "departing":
        return DIRECTION_DEPARTING_TEXT
    if raw == "arriving":
        return DIRECTION_ARRIVING_TEXT
    return ""


def _route_text(row):
    origin = row.get("origin") or ""
    destination = row.get("destination") or ""
    if origin and destination:
        return "%s → %s" % (origin, destination)
    return ""


def _flight_secondary_text(row):
    """"<airline> · <route> · <direction>", skipping any empty part — the
    shared join-and-skip-empty convention both the current picture's
    flight one-liner and the recent-flights list compose. `direction` is
    translated at this call site; `airline`/`route` are data (an ADS-B/
    adsbdb-sourced airline name and ICAO airport codes) and are never
    translated.
    """
    # Resolved through the same presentation-only alias Flights applies,
    # so a row whose stored airline is an alias reads the same display
    # name on both pages.
    airline = panel_render.display_airline_name(row.get("airline")) or ""
    route = _route_text(row)
    direction_raw = _direction_text(row.get("confirmed_state"))
    direction = i18n.t(direction_raw) if direction_raw else ""
    return " · ".join(part for part in (airline, route, direction) if part)


def _gallery_name_to_iso(name):
    """Mirror of history_page's filename convention: the gallery saves
    `<iso with ':' -> '-'>.png`. Returns the ISO string or None."""
    if not isinstance(name, str) or not name.endswith(".png"):
        return None
    stem = name[:-len(".png")]
    if len(stem) < 19 or stem[10] != "T":
        return None
    date_part, time_part = stem[:10], stem[11:]
    time_part = time_part.replace("-", ":", 2)
    if len(time_part) > 8:
        # "+00-00" offset suffix -> "+00:00"
        time_part = time_part[:8] + time_part[8:].replace("-", ":")
    candidate = "%sT%s" % (date_part, time_part)
    return candidate if layout.parse_iso(candidate) is not None else None


def _tile_content_html(verdict, detail, detail_class=None):
    """The verdict-plus-detail composition every one of the three tiles
    below shares — one write site rather than three near-identical
    inline literals. `detail` is omitted entirely (no placeholder) when
    falsy.

    `detail_class` optionally wraps the escaped `detail` text in its own
    inner `<span>` — the Frame tile's next-wake clock adopts
    `.time-value` here, the one role defined for a clock/countdown value
    site-wide, without making `detail` a second raw-markup injection
    point: the text is still escaped exactly once, only the wrapping
    changes.
    """
    verdict_html = '<p class="text-body widget-verdict">%s</p>' % escape_html(verdict)
    if not detail:
        return verdict_html
    detail_text = escape_html(detail)
    if detail_class:
        detail_text = '<span class="%s">%s</span>' % (detail_class, detail_text)
    return verdict_html + '<p class="text-label widget-detail">%s</p>' % detail_text


# The small ring's box side, in CSS pixels — half health_page.py's own
# large ring, kept under the height of the two text lines it sits
# beside, since stat_tile()'s box is shared by three tiles and a taller
# Battery tile would make the row ragged. The shared emitter,
# draw.ring_gauge(), lives in draw.py so a change there moves both pages.
BATTERY_RING_SIZE = 36


def _battery_tile_content_html(verdict, detail, ring_html):
    """`_tile_content_html()`'s output with the battery ring beside it.

    With no ring, returns that markup unwrapped, so a device with no
    reading renders byte-identically to before the ring existed. The
    ring sits beside the text rather than above it: stat_tile()'s box is
    shared by three tiles in one row, and stacking the ring would push
    this tile taller than its neighbours.
    """
    content_html = _tile_content_html(verdict, detail)
    if not ring_html:
        return content_html
    return (
        '<div class="stat-tile__gauge">%s'
        '<div class="stat-tile__gauge-text">%s</div></div>'
    ) % (ring_html, content_html)


def _status_tiles_html(ctx):
    """Renders the `.dashboard-grid.home-status-grid` of three
    `stat_tile()` calls (Frame/Battery/Flight data) plus the "See
    details on Health" link below the grid. Each tile's verdict comes
    from this module's own *_STATE_TEXT dicts, and each detail is the
    health state's own verdict-free field, reduced to plain text by
    `_plain_text_from_markup()` — never the combined device-summary
    field, which would carry the Frame verdict a second time.

    The Frame tile calls `wake.next_wake_status()`/
    `frame_state.resolve_state()` fresh, against the same ctx fields the
    strip above it already used, so the two can never disagree. The
    health-state-derived value is kept only as the fallback for
    `frame_state.STATE_UNKNOWN` (no check-in recorded at all), the one
    case frame_state.py cannot resolve.

    The Flight-data tile reads `pipeline_detail_html`, the verdict-free
    sibling of `pipeline_html` — Home renders its own verdict above it,
    never Health's second copy of the same judgement.
    """
    health = ctx.get("health_state") or {}
    pipeline_state = health.get("pipeline_state") or "warn"
    battery_state = health.get("battery_state") or "warn"

    next_wake_iso, effective_interval_s, hold_reason = wake.next_wake_status(
        ctx.get("last_checkin_ts"), ctx.get("device_config"))
    resolved_frame_state = frame_state.resolve_state(
        next_wake_iso, effective_interval_s, hold_reason, ctx.get("now"))
    if resolved_frame_state == frame_state.STATE_UNKNOWN:
        device_state = health.get("device_state") or "warn"
        frame_detail = _plain_text_from_markup(health.get("device_detail_html"))
        frame_detail_class = None
    else:
        device_state = _FRAME_STATE_TO_TILE_STATE[resolved_frame_state]
        next_wake_parsed = layout.parse_iso(next_wake_iso)
        frame_detail = layout.local_clock_text(
            next_wake_parsed, now_parsed=layout.parse_iso(ctx.get("now")))
        frame_detail_class = "time-value"
    frame_verdict = i18n.t(FRAME_STATE_TEXT.get(device_state, FRAME_STATE_TEXT["warn"]))
    frame_html = _tile_content_html(frame_verdict, frame_detail, detail_class=frame_detail_class)

    reading = _safe_query(ctx.get("state_dir"), _latest_battery)
    battery_ring_html = ""
    if reading and reading.get("battery_mv"):
        pct = battery.battery_percent(reading["battery_mv"])
        pct_text = ("≈ %d%%" % pct) if pct is not None else ""
        mv_text = "%s mV" % reading["battery_mv"]
        battery_verdict = i18n.t(BATTERY_STATE_TEXT.get(battery_state, BATTERY_STATE_TEXT["warn"]))
        battery_detail = "%s · %s" % (pct_text, mv_text) if pct_text else mv_text
        if pct is not None:
            # The ring draws the same `pct` printed beside it, not a
            # second, finer-grained estimate off the same millivolt
            # value, so the picture and the number cannot round to
            # different stories.
            battery_ring_html = draw.ring_gauge(
                pct / 100.0, BATTERY_RING_SIZE, draw.status_class(battery_state))
    else:
        battery_verdict = i18n.t(NO_READING_TEXT)
        battery_detail = ""
    battery_html = _battery_tile_content_html(
        battery_verdict, battery_detail, battery_ring_html)

    data_verdict = i18n.t(DATA_STATE_TEXT.get(pipeline_state, DATA_STATE_TEXT["warn"]))
    data_detail = _plain_text_from_markup(health.get("pipeline_detail_html"))
    data_html = _tile_content_html(data_verdict, data_detail)

    tiles = (
        layout.stat_tile(i18n.t(FRAME_ROW_LABEL), frame_html, device_state, icon="icon-device")
        + layout.stat_tile(
            i18n.t(BATTERY_ROW_LABEL), battery_html, battery_state, icon="icon-battery")
        + layout.stat_tile(i18n.t(DATA_ROW_LABEL), data_html, pipeline_state, icon="icon-pipeline")
    )

    health_link_html = (
        '<p class="text-label"><a href="/health">%s</a></p>'
    ) % escape_html(i18n.t(HEALTH_LINK_TEXT))

    return (
        '<section class="home-section" aria-labelledby="home-status">'
        '<h2 class="text-heading" id="home-status">%s</h2>'
        '<div class="dashboard-grid home-status-grid">%s</div>'
        "%s"
        "</section>"
    ) % (escape_html(i18n.t(STATUS_HEADING)), tiles, health_link_html)


def _current_picture_html(ctx, current_flight_row):
    """The picture column: the current picture, its "Rendered HH:MM"
    caption and, when the current flight is known, a one-line
    "AFR1380 · Air France · ORY → TLS" reusing the same recent-flights
    query result — no second query for the current flight.
    """
    entries = ctx.get("gallery_entries") or []
    now = ctx.get("now")
    newest = entries[0] if entries else None
    if not newest:
        return layout.empty_state(i18n.t(NO_PANEL_HEADING), i18n.t(NO_PANEL_BODY))

    iso = _gallery_name_to_iso(newest)
    caption = (
        i18n.t(RENDERED_CAPTION_TEMPLATE) % layout.concise_timestamp_html(iso, now)
        if iso else "")
    flight_html = ""
    if current_flight_row:
        callsign = current_flight_row.get("callsign") or current_flight_row.get("hex") or "—"
        secondary = _flight_secondary_text(current_flight_row)
        flight_html = (
            '<span class="preview-frame__flight"><span class="mono">%s</span>%s</span>'
        ) % (
            escape_html(callsign),
            (" · " + escape_html(secondary)) if secondary else "")

    return (
        '<figure class="preview-frame">'
        '<img class="preview-frame__image" src="%s%s" alt="%s" '
        'width="600" height="800" decoding="async">'
        '<figcaption class="preview-frame__caption text-label">%s%s</figcaption>'
        "</figure>"
    ) % (
        GALLERY_ROUTE_PREFIX, escape_html(newest), escape_html(i18n.t(PANEL_ALT_TEXT)),
        caption, flight_html)


def _recent_flight_thumb_html(row, state_dir):
    """The leading thumbnail cell. The `<img>` renders only when
    `illustrations.resolved_illustration_path()` finds a real file on
    disk for the normalised key — never unconditionally.

    An airline the app recognises by name but with no artwork file at
    all used to still emit `<img src="/illustration/{key}.png">`, which
    404s as a broken-image icon. A falsy key or a key with no resolved
    file both now render the identical dashed placeholder with no
    `<img>` at all.
    """
    # The key resolves on the raw stored airline string; only the alt
    # text below, a user-visible string, is aliased.
    raw_airline = row.get("airline")
    key = illustrations.normalise_airline_key(raw_airline)
    if key and illustrations.resolved_illustration_path(key, state_dir) is not None:
        alt_text = i18n.t(THUMBNAIL_ALT_TEMPLATE) % panel_render.display_airline_name(raw_airline)
        return (
            '<img class="recent-flight__thumb" loading="lazy" decoding="async" '
            'width="40" height="40" src="%s%s.png" alt="%s">'
        ) % (ILLUSTRATION_ROUTE_PREFIX, key, escape_html(alt_text))
    return '<span class="recent-flight__thumb recent-flight__thumb--placeholder"></span>'


_TIME_CELL_FALLBACK_TEXT = "no reading yet"


def _recent_flight_time_html(ts, now):
    """The recent-flight time, one line: the clock takes the
    `.time-value` role, the relative age sits beside it as a
    `.time-value__age` sibling, joined by the `.cell-inline-sep` middle
    dot (history_page.py's own "Inline compact" convention, duplicated
    here since a page module cannot import another).

    Does not use `layout.concise_timestamp_html()`, which bundles the
    clock and the relative age into one already-escaped `<span
    class="mono">` — the single-element shape this cell exists to avoid.
    The clock and the age are built and escaped separately instead.
    Falls back to the escaped, translated "no reading yet" text when
    `ts` is falsy or fails to parse. The age half is
    `layout.relative_time_html()`'s `<time data-relative>` element so a
    ticker script can find it; its return value is raw markup,
    interpolated verbatim.
    """
    if not ts:
        return escape_html(i18n.t(_TIME_CELL_FALLBACK_TEXT))
    parsed = layout.parse_iso(ts)
    if parsed is None:
        return '<span class="time-value">%s</span>' % escape_html(ts)
    clock_text = layout.local_clock_text(parsed, now_parsed=layout.parse_iso(now))
    cell_html = '<span class="time-value">%s</span>' % escape_html(clock_text)
    age = layout.age_seconds(ts, now)
    if age is not None:
        cell_html += (
            '<span class="cell-inline-sep">·</span>'
            '<span class="time-value__age">(%s)</span>'
        ) % layout.relative_time_html(ts, now)
    return cell_html


def _recent_flights_html(rows, now, state_dir):
    if not rows:
        body = layout.empty_state(i18n.t(NO_FLIGHTS_HEADING), i18n.t(NO_FLIGHTS_BODY))
    else:
        items = []
        for row in rows:
            callsign = row.get("callsign") or row.get("hex") or "—"
            secondary = _flight_secondary_text(row)
            items.append(
                '<li class="recent-flight">%s'
                '<span class="recent-flight__callsign mono">%s</span>'
                '<span class="recent-flight__detail text-label">%s</span>'
                '<span class="recent-flight__time text-label">%s</span>'
                "</li>"
                % (_recent_flight_thumb_html(row, state_dir), escape_html(callsign),
                   escape_html(secondary), _recent_flight_time_html(row.get("ts"), now)))
        body = '<ul class="recent-flights">%s</ul>' % "".join(items)
    return (
        '<section class="page-section home-section" aria-labelledby="home-flights">'
        '<h2 class="text-heading" id="home-flights">%s</h2>%s'
        '<p class="text-label"><a href="%s">%s</a></p>'
        "</section>"
    ) % (
        escape_html(i18n.t(RECENT_FLIGHTS_HEADING)), body,
        FLIGHTS_ROUTE, escape_html(i18n.t(RECENT_FLIGHTS_LINK_TEXT)))


def _day_checkins(conn):
    return history_db.recent_device_health(conn, limit=DAY_BAND_ROW_LIMIT)


def _paris_day_bounds(now):
    """`(day, day_start_epoch, day_seconds)` for the Europe/Paris day
    `now` falls in, or None when `now` does not parse.

    `day_seconds` is measured between two real Paris midnights and never
    assumed to be 86400: a Europe/Paris day is 23 or 25 hours twice a
    year, and a band assuming 86400 would misplace midday and leave an
    hour of its own width unreachable. `layout.LOCAL_TZ` is the one
    timezone constant every timestamp on this page already formats
    through, so the band and the row beneath it cannot disagree about
    which day it is.
    """
    parsed = history_db._instant_or_none(now)
    if parsed is None:
        return None
    day = parsed.astimezone(layout.LOCAL_TZ).date()
    start = datetime.combine(day, time(0), tzinfo=layout.LOCAL_TZ)
    end = datetime.combine(day + timedelta(days=1), time(0), tzinfo=layout.LOCAL_TZ)
    return day, start.timestamp(), end.timestamp() - start.timestamp()


def _day_band_instants(rows, day):
    """The epoch seconds of every row in `rows` whose stored `ts` falls
    on the Europe/Paris calendar day `day`.

    Bucketed through `history_db._paris_day_or_none()`, the same date
    path `check_in_gaps()` and `daily_battery_averages()` use, so a mark
    on this band and a row in Health's own day-bucketed data can never
    disagree about which day a check-in belongs to. This is a real
    bucketing, not a filter: Paris is UTC+1 or UTC+2, so a check-in at
    00:30 Paris is stored as 22:30 UTC on the previous date, and
    comparing UTC dates directly would silently attribute it to the
    wrong day.
    """
    instants = []
    for row in rows or ():
        ts = row.get("ts") if isinstance(row, dict) else None
        if history_db._paris_day_or_none(ts) != day:
            continue
        parsed = history_db._instant_or_none(ts)
        if parsed is not None:
            instants.append(parsed.timestamp())
    return instants


def _quiet_hours_window(config, day_start, day_seconds):
    """`((start_epoch, end_epoch), start_hm, end_hm)` for the configured
    quiet-hours window placed on the band's own day, or `(None, None,
    None)` when quiet hours are not enabled or the config is unusable.

    The enabled test is `is True`, not truthiness, matching
    `device_config.quiet_hours_status()`; both time strings go through
    `device_config.normalise_quiet_hours_time()` so a hand-edited config
    cannot put an unvalidated string into the arithmetic.
    `quiet_hours_status()` itself answers an activity question
    (seconds remaining and when it ends), not the window's two absolute
    ends regardless of activity, so this function derives them directly
    instead. The end may precede the start for a night window;
    `draw.day_band()` is where that becomes two spans.
    """
    if not isinstance(config, dict) or config.get("quiet_hours_enabled") is not True:
        return None, None, None
    try:
        start_hm = device_config.normalise_quiet_hours_time(
            config.get("quiet_hours_start"), device_config.DEFAULT_QUIET_HOURS_START)
        end_hm = device_config.normalise_quiet_hours_time(
            config.get("quiet_hours_end"), device_config.DEFAULT_QUIET_HOURS_END)
        start = day_start + _hm_seconds(start_hm)
        end = day_start + _hm_seconds(end_hm)
    except (TypeError, ValueError):
        return None, None, None
    if start > day_start + day_seconds or end > day_start + day_seconds:
        # A DST day is 23 or 25 hours long, so an "HH:MM" offset counted
        # from midnight can land past the band's own right edge. Rather
        # than clamp — which would silently redraw the window the user
        # configured — the shading is dropped and the caption with it.
        return None, None, None
    return (start, end), start_hm, end_hm


def _hm_seconds(hm):
    """Seconds from midnight for a normalised "HH:MM" string."""
    hours, _, minutes = hm.partition(":")
    return int(hours) * 3600 + int(minutes) * 60


def _day_band_html(ctx, rows):
    """The day band's <section>, or "" when there is no day to draw.

    `rows` is the one device_health read render() makes; this function
    re-queries nothing. An unreadable history.db arrives as `rows is
    None` and renders nothing at all, since an empty band would falsely
    say "no check-ins today" for a failed read. A day that genuinely
    holds no check-ins renders the band empty instead, matching this
    page's "no chrome with no data" rule.
    """
    if rows is None:
        return ""
    bounds = _paris_day_bounds(ctx.get("now"))
    if bounds is None:
        return ""
    day, day_start, day_seconds = bounds
    instants = _day_band_instants(rows, day)
    window, start_hm, end_hm = _quiet_hours_window(
        ctx.get("device_config"), day_start, day_seconds)
    canvas, collapsed = draw.day_band(
        day_start, day_seconds, instants, window=window,
        label=i18n.t(DAY_BAND_LABEL))
    day_text = day.isoformat()

    # The caption is written from `collapsed`, not from the row count
    # alone: when the band merged anything it says so, so a reader who
    # counts the marks and gets fewer is not told the drawing lost some.
    total = len(instants)
    if not total:
        caption = i18n.t(DAY_BAND_EMPTY_TEXT) % (day_text,)
    elif total == 1:
        caption = i18n.t(DAY_BAND_ONE_TEXT) % (day_text,)
    else:
        caption = i18n.t(DAY_BAND_COUNT_TEXT) % (total, day_text)
    sentences = [escape_html(caption)]
    if collapsed or len(rows) >= DAY_BAND_ROW_LIMIT:
        sentences.append(escape_html(i18n.t(DAY_BAND_COLLAPSED_TEXT)))
    if window is not None:
        sentences.append(escape_html(i18n.t(DAY_BAND_QUIET_TEXT) % (start_hm, end_hm)))
    hours = "".join(
        "<span>%s</span>" % escape_html(label) for label in DAY_BAND_HOUR_LABELS)
    return (
        '<section class="page-section home-section day-band" '
        'aria-labelledby="home-day-band">'
        '<h2 class="text-heading" id="home-day-band">%s</h2>'
        '%s'
        '<p class="day-band__hours text-label mono">%s</p>'
        '<p class="text-label">%s</p>'
        "</section>"
    ) % (escape_html(i18n.t(DAY_BAND_HEADING)), canvas, hours, " ".join(sentences))


# The class is `home-overview`, deliberately not `home-hero`: that name
# belonged to a retired hero row, and standing checks assert that markup
# never comes back to this page.
HERO_CLASS = "home-overview"


def _hero_html(*parts):
    """Home's top as one composition — the shared Frame strip, the three
    status tiles carrying the battery ring, and the day band — wrapped in
    a single container that owns the rhythm between them.

    Assembled from calls only: every part arrives already built by the
    function that owns it, so nothing here can drift from those
    originals. A bare `<div>` with no role or name of its own — the
    three parts keep their own `<h2>`s, so a screen reader reads this
    page exactly as before the container existed. The wrapper is
    unconditional even though the hero's contents vary with the data
    (`_day_band_html()` can return `""`, the battery ring can be
    omitted), since a container that also came and went would move
    everything below it depending on whether a query happened to
    succeed.
    """
    return '<div class="%s">%s</div>' % (HERO_CLASS, "".join(parts))


def render(ctx):
    """Strip, then three tiles, then a two-column picture/recent-flights
    row. The first three are handed to `_hero_html()` as one
    composition; the DOM order, and every region
    `layout.REFRESH_SWAP_SELECTORS_BY_PAGE` declares for this page, are
    unchanged by that wrapping.
    """
    now = ctx.get("now")
    # One read, reused for both the hero's flight one-liner (its first
    # row is "the current flight") and the recent-flights list — never
    # two independent queries for the same data.
    rows = _safe_query(ctx.get("state_dir"), _recent_flights)
    current_flight_row = rows[0] if rows else None
    # The day band's own single read, made here and passed down so a
    # builder that queried for itself would not make the page's cost
    # depend on how many sections happen to want the data.
    checkin_rows = _safe_query(ctx.get("state_dir"), _day_checkins)
    header = layout.page_header(
        i18n.t(PAGE_TITLE), purpose=i18n.t(PAGE_PURPOSE),
        freshness_html=layout.freshness_line_html(now))
    # _status_tiles_html() below makes its own fresh call to the same
    # wake accessor against the same ctx fields, so the two can never
    # disagree.
    next_wake_iso = wake.next_wake_status(
        ctx.get("last_checkin_ts"), ctx.get("device_config"))[0]
    return (
        header
        + _hero_html(
            layout.frame_strip_html(
                ctx, return_to=layout.HOME_ROUTE, next_wake_iso=next_wake_iso),
            _status_tiles_html(ctx),
            _day_band_html(ctx, checkin_rows))
        + '<div class="home-columns home-picture-row">'
        + _current_picture_html(ctx, current_flight_row)
        + _recent_flights_html(rows, now, ctx.get("state_dir"))
        + "</div>"
    )
