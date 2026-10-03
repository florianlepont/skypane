"""The Home page: answers whether the frame is alive, what it is
showing, and what it has shown recently.

Renders the current picture beside the recent flights, then one merged
frame-state card (screen / quiet hours / next update, with the two native
POST controls) and a compact battery fact and, only when attention is
needed, a link to Health. A recent-flight row gets a
thumbnail only when a real illustration file resolves for that
airline, since a recognised name with no artwork file would otherwise
404 as a broken image. The recent-flight rows and the current
picture's flight line share one `history_db` read.
"""

import companion.battery as battery
import companion.frame_state as frame_state
import companion.i18n as i18n
import companion.layout as layout
import companion.page_context as page_context
import companion.wake as wake
from companion.layout import escape_html
from server import device_config, history_db
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

BATTERY_FACT_TEMPLATE = i18n.msg("home.battery_fact", "Battery · %s")
BATTERY_FACT_EMPTY = i18n.msg("home.battery_fact_empty", "Battery · No reading yet")
ACTION_NEEDED_TEXT = i18n.msg("home.action_needed", "Something needs attention")
ACTION_NEEDED_LINK_TEXT = i18n.msg("home.review_status", "Review status")

NO_READING_TEXT = i18n.msg("home.no_reading_yet", "No reading yet")

# The merged frame-state card. The quick routes are the same two
# server-validated POST endpoints the retired Frame strip posted to.
FRAME_STATE_HEADING = i18n.msg("home.frame_state", "Frame state")
QUICK_DISPLAY_ACTION = "/quick/display"
QUICK_QUIET_HOURS_ACTION = "/quick/quiet-hours"
STATE_SCREEN_ON_TEXT = i18n.msg("home.state_screen_on", "Screen on")
STATE_SCREEN_OFF_TEXT = i18n.msg(
    "home.state_screen_off", "Screen off — the frame stays blank")
STATE_QUIET_TEXT = i18n.msg(
    "home.state_quiet_hours", "Quiet hours — the screen rests until %s")
STATE_BATTERY_TEXT = i18n.msg(
    "home.state_battery_resting",
    "Battery very low — the frame is resting until it is recharged")
QUIET_SCHEDULE_ON_TEXT = i18n.msg(
    "home.quiet_schedule_on", "Quiet hours are on, %s to %s")
QUIET_SCHEDULE_OFF_TEXT = i18n.msg(
    "home.quiet_schedule_off", "Quiet hours are turned off")
CADENCE_TEXT = i18n.msg(
    "home.cadence",
    "To save its battery, the frame sleeps between updates and wakes about "
    "every %s, so it does not refresh continuously.")
CADENCE_NO_INTERVAL_TEXT = i18n.msg(
    "home.cadence_no_interval",
    "To save its battery, the frame sleeps between updates, so it does not "
    "refresh continuously.")
SCREEN_TURN_ON_BUTTON = i18n.msg("home.turn_screen_on", "Turn screen on")
SCREEN_TURN_OFF_BUTTON = i18n.msg("home.turn_screen_off", "Turn screen off")
QUIET_TURN_ON_BUTTON = i18n.msg("home.turn_quiet_hours_on", "Turn quiet hours on")
QUIET_TURN_OFF_BUTTON = i18n.msg("home.turn_quiet_hours_off", "Turn quiet hours off")
DEFAULT_QUIET_START = "23:00"
DEFAULT_QUIET_END = "07:00"


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


# The small ring's box side, in CSS pixels — half health_page.py's own
# large ring, kept under the height of the two text lines it sits
# beside, since stat_tile()'s box is shared by three tiles and a taller
# Battery tile would make the row ragged. The shared emitter,
# draw.ring_gauge(), lives in draw.py so a change there moves both pages.
BATTERY_RING_SIZE = 36


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


def _interval_text(interval_s):
    """"15 min" / "2 h" / "1 h 30" for a wake interval in seconds. Units are
    the same in English and French, so the text itself is not translated."""
    minutes = max(1, int(round(interval_s / 60.0)))
    if minutes < 60:
        return "%d min" % minutes
    hours, rest = divmod(minutes, 60)
    return "%d h" % hours if rest == 0 else "%d h %02d" % (hours, rest)


def _frame_state_summary(ctx):
    """Everything the card shows, derived once from the page context:
    the headline `(kind, text)`, the next-update triple and the base wake
    interval. Precedence mirrors `wake.effective_wake_interval_s()`: a
    battery-empty hold beats the display switch, which beats quiet hours.
    """
    cfg = ctx.device_config or {}
    critical = ctx.battery_critical is True
    now_parsed = layout.parse_iso(ctx.now)
    quiet_remaining, quiet_end = (None, None)
    if now_parsed is not None:
        quiet_remaining, quiet_end = device_config.quiet_hours_status(
            cfg, now_parsed.timestamp())
    if critical:
        headline = ("warn", i18n.t(STATE_BATTERY_TEXT))
    elif cfg.get("display_enabled") is False:
        headline = ("off", i18n.t(STATE_SCREEN_OFF_TEXT))
    elif quiet_remaining is not None:
        headline = ("off", i18n.t(STATE_QUIET_TEXT) % quiet_end)
    else:
        headline = ("ok", i18n.t(STATE_SCREEN_ON_TEXT))
    return headline, wake.next_wake_status(
        ctx.last_checkin_ts, cfg, battery_critical=critical
    ), wake.effective_wake_interval_s(cfg, battery_critical=critical)


def _next_update_html(next_iso, interval_s, hold_reason, now):
    """The "Next update ≈ HH:MM · in 5 min" line, or "" without a check-in.
    The wording template comes from frame_state, the single due/held/late
    decision shared with every other consumer."""
    parsed = layout.parse_iso(next_iso) if next_iso else None
    if parsed is None:
        return ""
    state = frame_state.resolve_state(next_iso, interval_s, hold_reason, now)
    template = frame_state.headline_template(state)
    before, after = i18n.t(template).split("%s", 1)
    clock = layout.local_clock_text(parsed, now_parsed=layout.parse_iso(now))
    return (
        '<p class="home-state__next text-label">%s'
        '<span class="time-value">%s</span>%s · %s</p>'
    ) % (escape_html(before), escape_html(clock), escape_html(after),
         layout.relative_time_html(next_iso, now, countdown=True))


def _quiet_schedule_text(cfg):
    if cfg.get("quiet_hours_enabled") is True:
        return i18n.t(QUIET_SCHEDULE_ON_TEXT) % (
            cfg.get("quiet_hours_start") or DEFAULT_QUIET_START,
            cfg.get("quiet_hours_end") or DEFAULT_QUIET_END)
    return i18n.t(QUIET_SCHEDULE_OFF_TEXT)


def _state_form_html(action, turn_on, on_label, off_label):
    """One native POST form: the button posts the OPPOSITE of the current
    state, so it works with scripts blocked. `return_to` is one of the
    server-side whitelist's values."""
    return (
        '<form method="post" action="%s" class="home-state__form">'
        '<input type="hidden" name="%s" value="%s">'
        '<input type="hidden" name="return_to" value="%s">'
        '<button type="submit" class="home-state__button">%s</button>'
        "</form>"
    ) % (
        action, layout.QUICK_STATE_FIELD,
        layout.QUICK_STATE_ON if turn_on else layout.QUICK_STATE_OFF,
        layout.HOME_ROUTE, escape_html(i18n.t(on_label if turn_on else off_label)))


def _frame_state_html(ctx):
    """The one merged frame-state card: current state in plain language,
    the next update, one sentence on why updates are not continuous, and
    the screen / quiet-hours buttons. Everything comes from the page
    context; the buttons reuse the Frame strip's quick routes."""
    cfg = ctx.device_config or {}
    (dot, headline), (next_iso, interval_s, hold_reason), base_interval_s = (
        _frame_state_summary(ctx))
    cadence = (
        i18n.t(CADENCE_TEXT) % _interval_text(base_interval_s)
        if base_interval_s else i18n.t(CADENCE_NO_INTERVAL_TEXT))
    screen_on = cfg.get("display_enabled") is not False
    quiet_on = cfg.get("quiet_hours_enabled") is True
    return (
        '<section class="page-section home-section home-state" '
        'aria-labelledby="home-frame-state">'
        '<h2 class="text-heading" id="home-frame-state">%s</h2>'
        '<p class="home-state__headline"><span class="dot dot--%s"></span>%s</p>'
        "%s"
        '<p class="home-state__quiet text-label">%s</p>'
        '<p class="home-state__cadence text-label section-caption">%s</p>'
        '<div class="home-state__actions">%s%s</div>'
        "</section>"
    ) % (
        escape_html(i18n.t(FRAME_STATE_HEADING)), dot, escape_html(headline),
        _next_update_html(next_iso, interval_s, hold_reason, ctx.now),
        escape_html(_quiet_schedule_text(cfg)), escape_html(cadence),
        _state_form_html(
            QUICK_DISPLAY_ACTION, not screen_on, SCREEN_TURN_ON_BUTTON, SCREEN_TURN_OFF_BUTTON),
        _state_form_html(
            QUICK_QUIET_HOURS_ACTION, not quiet_on, QUIET_TURN_ON_BUTTON, QUIET_TURN_OFF_BUTTON))


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
    link.  Screen, quiet hours and the next update are ONE merged card with
    the controls beside the state they change; daily activity belongs to
    Health.
    """
    ctx = page_context.coerce(ctx)
    now = ctx.now
    # One read, reused for both the hero's flight one-liner (its first
    # row is "the current flight") and the recent-flights list — never
    # two independent queries for the same data.
    rows = _safe_query(ctx.state_dir, _recent_flights)
    current_flight_row = rows[0] if rows else None
    # The silent marker keeps Home on freshness.js's background refresh
    # without a visible freshness line.
    header = layout.page_header(
        i18n.t(PAGE_TITLE), freshness_html=layout.refresh_marker_html(now))
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
        + _frame_state_html(ctx)
        + '<div class="home-facts">'
        + _battery_fact_html(ctx)
        + _action_needed_html(ctx)
        + "</div>"
    )
