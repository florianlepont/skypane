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

import companion.battery as battery
import companion.draw as draw
import companion.frame_state as frame_state
import companion.i18n as i18n
import companion.layout as layout
import companion.page_context as page_context
import companion.wake as wake
from companion.layout import escape_html
from server import history_db
from server.plane import illustrations
# The same presentation-only airline alias Flights applies via
# history_page.py's panel_render.display_airline_name() call.
# illustrations.normalise_airline_key() still resolves on the raw
# stored airline string — only user-visible text is aliased.
from server.plane import render as panel_render

PAGE_TITLE = i18n.msg("nav.home", "Home")
CURRENT_FRAME_HEADING = i18n.msg("home.current_frame", "Current frame")

RECENT_FLIGHTS_LIMIT = 5
RECENT_FLIGHTS_HEADING = i18n.msg("home.recent_flights", "Recent flights")
RECENT_FLIGHTS_LINK_TEXT = i18n.msg("home.see_all_flights", "See all flights")
NO_FLIGHTS_HEADING = i18n.msg("home.no_flights_yet", "No flights yet.")
NO_FLIGHTS_BODY = i18n.msg(
    "home.the_first_aircraft_the_frame_detects_on_the",
    "The first aircraft the frame detects on the watched runway will "
    "appear here.")
FLIGHTS_ROUTE = "/flights"

# Duplicated here rather than imported from airlines_page.py — a page
# module cannot import a sibling page module.
ILLUSTRATION_ROUTE_PREFIX = "/illustration/"
THUMBNAIL_ALT_TEMPLATE = i18n.msg("home.illustration", "%s illustration")

RENDERED_CAPTION_TEMPLATE = i18n.msg("home.rendered", "Rendered %s")
NO_PANEL_HEADING = i18n.msg("home.nothing_rendered_yet", "Nothing rendered yet.")
NO_PANEL_BODY = i18n.msg(
    "home.the_server_saves_a_copy_of_each_picture_it",
    "The server saves a copy of each picture it sends to the frame; the "
    "latest one will appear here.")
PANEL_ALT_TEXT = i18n.msg(
    "home.the_picture_currently_on_the_frame",
    "The picture currently on the frame")
GALLERY_ROUTE_PREFIX = "/gallery/"

DIRECTION_DEPARTING_TEXT = i18n.msg("home.departing", "Departing")
DIRECTION_ARRIVING_TEXT = i18n.msg("home.arriving", "Arriving")

# The screen/quiet-hours switches and the next-update headline render
# once in the shared Frame strip helper (see render() below); Refresh-now
# lives on Device's own Manual refresh section instead.

STATUS_HEADING = i18n.msg("home.status", "Status")
# "Frame" is reserved for the shared Frame strip's own <h2> heading,
# rendered directly above this tile; only this tile's caption moves.
FRAME_ROW_LABEL = i18n.msg("home.check_ins", "Check-ins")
BATTERY_ROW_LABEL = i18n.msg("home.battery", "Battery")
DATA_ROW_LABEL = i18n.msg("home.flight_data", "Flight data")
HEALTH_LINK_TEXT = i18n.msg("home.see_details_on_health", "See details on Health")
BATTERY_FACT_TEMPLATE = i18n.msg("home.battery_fact", "Battery · %s")
BATTERY_FACT_EMPTY = i18n.msg("home.battery_fact_empty", "Battery · No reading yet")
ACTION_NEEDED_TEXT = i18n.msg("home.action_needed", "Something needs attention")
ACTION_NEEDED_LINK_TEXT = i18n.msg("home.review_status", "Review status")

# Stays byte-identical to health_page.DEVICE_STATE_TEXT's own values —
# see companion/i18n_fr/home.py's comment for why the two dicts must
# never be edited to differ. "off" is a held (quiet-hours) frame, a
# genuine fourth state, reusing health_page.py's own neutral wording.
# Owned by companion/i18n_fr/health.py, not home.py — the ids match
# health_page.py's own DEVICE_STATE_TEXT declarations exactly.
FRAME_STATE_TEXT = {
    "ok": i18n.msg("health.checking_in_normally", "Checking in normally"),
    "warn": i18n.msg(
        "health.has_not_checked_in_for_a_while", "Has not checked in for a while"),
    "error": i18n.msg(
        "health.has_not_checked_in_for_a_long_time",
        "Has not checked in for a long time"),
    "off": i18n.msg("health.asleep_for_quiet_hours", "Asleep for quiet hours"),
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
    "ok": i18n.msg("home.up_to_date", "Up to date"),
    "warn": i18n.msg("home.a_little_stale", "A little stale"),
    "error": i18n.msg(
        "home.stale_the_server_may_be_down", "Stale — the server may be down"),
    # Byte-identical to health_page.PIPELINE_STATE_TEXT["off"]: a
    # pipeline that has never run is the same neutral fact on both
    # pages, never Home's "A little stale" wording. Owned by
    # companion/i18n_fr/health.py, not home.py.
    "off": i18n.msg("health.no_detection_yet", "No detection yet"),
}
_BATTERY_DROPPING_QUICKLY_TEXT = i18n.msg("home.dropping_quickly", "Dropping quickly")
BATTERY_STATE_TEXT = {
    "ok": i18n.msg("home.healthy", "Healthy"),
    "warn": _BATTERY_DROPPING_QUICKLY_TEXT,
    "error": _BATTERY_DROPPING_QUICKLY_TEXT,
}
NO_READING_TEXT = i18n.msg("home.no_reading_yet", "No reading yet")

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
    ctx = page_context.coerce(ctx)
    health = ctx.health_state or {}
    pipeline_state = health.get("pipeline_state") or "warn"
    battery_state = health.get("battery_state") or "warn"

    next_wake_iso, effective_interval_s, hold_reason = wake.next_wake_status(
        ctx.last_checkin_ts, ctx.device_config)
    resolved_frame_state = frame_state.resolve_state(
        next_wake_iso, effective_interval_s, hold_reason, ctx.now)
    if resolved_frame_state == frame_state.STATE_UNKNOWN:
        device_state = health.get("device_state") or "warn"
        frame_detail = _plain_text_from_markup(health.get("device_detail_html"))
        frame_detail_class = None
    else:
        device_state = _FRAME_STATE_TO_TILE_STATE[resolved_frame_state]
        next_wake_parsed = layout.parse_iso(next_wake_iso)
        frame_detail = layout.local_clock_text(
            next_wake_parsed, now_parsed=layout.parse_iso(ctx.now))
        frame_detail_class = "time-value"
    frame_verdict = i18n.t(FRAME_STATE_TEXT.get(device_state, FRAME_STATE_TEXT["warn"]))
    frame_html = _tile_content_html(frame_verdict, frame_detail, detail_class=frame_detail_class)

    reading = _safe_query(ctx.state_dir, _latest_battery)
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
    ctx = page_context.coerce(ctx)
    entries = ctx.gallery_entries or []
    now = ctx.now
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


# Owned by companion/i18n_fr/flights.py, not home.py — the same id
# history_page.py's own clock-cell fallback uses.
_TIME_CELL_FALLBACK_TEXT = i18n.msg("flights.no_reading_yet", "no reading yet")


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


def _battery_fact_html(ctx):
    """A compact battery fact for the normal Home path.

    Home reads only the latest stored reading already owned by PageContext's
    state directory.  It deliberately does not reintroduce the old battery
    dashboard tile: the number is useful when all is well, but it should not
    compete with the image the frame last received.
    """
    reading = _safe_query(ctx.state_dir, _latest_battery)
    if not reading or not reading.get("battery_mv"):
        text = i18n.t(BATTERY_FACT_EMPTY)
    else:
        percent = battery.battery_percent(reading["battery_mv"])
        value = "≈ %d%%" % percent if percent is not None else "%s mV" % reading["battery_mv"]
        text = i18n.t(BATTERY_FACT_TEMPLATE) % value
    return '<p class="home-fact text-label">%s</p>' % escape_html(text)


def _needs_attention(ctx):
    """Whether Home should point the owner to the detailed Health page.

    Quiet-hours sleep is intentional and therefore excluded.  Every other
    warn/error state already belongs to the shared, server-derived health
    snapshot; Home only decides whether that snapshot warrants a link.
    """
    health = ctx.health_state or {}
    return any(health.get(name) in ("warn", "error") for name in (
        "device_state", "pipeline_state", "battery_state"))


def _action_needed_html(ctx):
    if not _needs_attention(ctx):
        return ""
    return (
        '<p class="home-action"><span class="dot dot--warn"></span>%s '
        '<a href="/health">%s</a></p>'
    ) % (
        escape_html(i18n.t(ACTION_NEEDED_TEXT)),
        escape_html(i18n.t(ACTION_NEEDED_LINK_TEXT)),
    )


def render(ctx):
    """Render the approved frame-signal-first Home composition.

    The generated picture and its flight line are the primary signal. Recent
    flights follow beside it on desktop and after it on a phone; battery is a
    compact fact and only an actionable shared health state adds a Health
    link.  Home does not duplicate the screen, quiet-hours, next-wake, or
    daily-activity information that belongs to configuration and Health.
    """
    ctx = page_context.coerce(ctx)
    now = ctx.now
    # One read, reused for both the hero's flight one-liner (its first
    # row is "the current flight") and the recent-flights list — never
    # two independent queries for the same data.
    rows = _safe_query(ctx.state_dir, _recent_flights)
    current_flight_row = rows[0] if rows else None
    header = layout.page_header(i18n.t(PAGE_TITLE))
    return (
        header
        + '<div class="home-columns home-picture-row home-signal-grid">'
        + '<section class="page-section home-section home-current-frame" '
        'aria-labelledby="home-current-frame">'
        + '<h2 class="text-heading" id="home-current-frame">%s</h2>'
        % escape_html(i18n.t(CURRENT_FRAME_HEADING))
        + _current_picture_html(ctx, current_flight_row)
        + '</section>'
        + _recent_flights_html(rows, now, ctx.state_dir)
        + "</div>"
        + '<div class="home-facts">'
        + _battery_fact_html(ctx)
        + _action_needed_html(ctx)
        + "</div>"
    )
