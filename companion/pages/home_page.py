"""The Home page: answers whether the frame is alive, what it is
showing, and what it has shown recently.

Opens with one status header (frame state, next update, battery and the
two native-POST switches for screen and quiet hours), then the current
picture beside the recent flights and, only when attention is needed, a
link to Health. A recent-flight row gets a
thumbnail only when a real illustration file resolves for that
airline, since a recognised name with no artwork file would otherwise
404 as a broken image. The recent-flight rows and the current
picture's flight line share one `history_db` read.
"""

import companion.battery as battery
import companion.draw as draw
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

NO_PANEL_HEADING = i18n.msg("home.nothing_rendered_yet", "Nothing rendered yet.")
NO_PANEL_BODY = i18n.msg(
    "home.the_server_saves_a_copy_of_each_picture_it",
    "The server saves a copy of each picture it sends to the frame; the "
    "latest one will appear here.")
PANEL_ALT_TEXT = i18n.msg(
    "home.the_picture_currently_on_the_frame",
    "The picture currently on the frame")
# The alt text when the current flight is known: the picture's accessible
# name carries the flight line the page no longer prints under it.
PANEL_FLIGHT_ALT_TEMPLATE = i18n.msg(
    "home.the_picture_currently_on_the_frame_flight",
    "The picture currently on the frame: %s")
GALLERY_ROUTE_PREFIX = "/gallery/"

DIRECTION_DEPARTING_TEXT = i18n.msg("home.departing", "Departing")
DIRECTION_ARRIVING_TEXT = i18n.msg("home.arriving", "Arriving")

BATTERY_LABEL = i18n.msg("home.battery_label", "Battery")
BATTERY_ARIA_TEMPLATE = i18n.msg("home.battery_aria", "Battery about %s")
BATTERY_LOW_TEXT = i18n.msg("home.battery_low", "Low")
BATTERY_CRITICAL_TEXT = i18n.msg("home.battery_critical", "Very low")
BATTERY_FACT_EMPTY = i18n.msg("home.battery_fact_empty", "Battery · No reading yet")
ACTION_NEEDED_TEXT = i18n.msg("home.action_needed", "Something needs attention")
ACTION_NEEDED_LINK_TEXT = i18n.msg("home.review_status", "Review status")

NO_READING_TEXT = i18n.msg("home.no_reading_yet", "No reading yet")

# The status header. The quick routes are the same two server-validated
# POST endpoints the retired Frame strip posted to.
FRAME_STATE_HEADING = i18n.msg("home.frame_state", "Frame state")
QUICK_DISPLAY_ACTION = "/quick/display"
QUICK_QUIET_HOURS_ACTION = "/quick/quiet-hours"
# Each state is a short title, set in the display face, plus for the
# held states a plain sentence under it saying what the frame does.
STATE_SCREEN_ON_TEXT = i18n.msg("home.state_screen_on", "Screen on")
STATE_SCREEN_OFF_TEXT = i18n.msg("home.state_title_screen_off", "Screen off")
STATE_SCREEN_OFF_DETAIL = i18n.msg(
    "home.state_detail_screen_off", "The frame stays blank")
STATE_QUIET_TEXT = i18n.msg("home.state_title_quiet_hours", "Quiet hours")
STATE_QUIET_DETAIL = i18n.msg(
    "home.state_detail_quiet_hours", "The screen rests until %s")
STATE_BATTERY_TEXT = i18n.msg("home.state_title_battery", "Battery very low")
STATE_BATTERY_DETAIL = i18n.msg(
    "home.state_detail_battery",
    "The frame is resting until it is recharged")
# The info tooltip beside the next-update line. The first wording names
# the wake interval; the second is the fallback when none is known.
CADENCE_INFO_TEXT = i18n.msg(
    "home.cadence_info",
    "The frame sleeps between updates to save its battery; it wakes about "
    "every %s, so it does not refresh continuously.")
CADENCE_INFO_NO_INTERVAL_TEXT = i18n.msg(
    "home.cadence_no_interval",
    "To save its battery, the frame sleeps between updates, so it does not "
    "refresh continuously.")
CADENCE_INFO_LABEL = i18n.msg("home.cadence_info_label", "About updates")
CADENCE_INFO_ID = "home-cadence-info"
SEE_HEALTH_TEXT = i18n.msg("home.see_health", "See Health")
HEALTH_ROUTE = "/health"
SWITCHES_LABEL = i18n.msg("home.switches", "Frame controls")
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


# The battery dial's box side in CSS pixels. Drawn once at this size;
# style.css scales the box down on a phone, and the SVG scales with it
# because it carries a viewBox.
BATTERY_ARC_SIZE = 132


def _current_picture_html(ctx, current_flight_row):
    """The picture column: the current picture alone. When the current
    flight is known (the first recent-flights row, reused here rather than
    queried again) its one-line "AFR1380 · Air France · ORY → TLS" becomes
    part of the image's alt text, since nothing is printed under it.
    """
    ctx = page_context.coerce(ctx)
    entries = ctx.gallery_entries or []
    newest = entries[0] if entries else None
    if not newest:
        return layout.empty_state(i18n.t(NO_PANEL_HEADING), i18n.t(NO_PANEL_BODY))

    alt = i18n.t(PANEL_ALT_TEXT)
    if current_flight_row:
        callsign = current_flight_row.get("callsign") or current_flight_row.get("hex") or "—"
        secondary = _flight_secondary_text(current_flight_row)
        flight = callsign + ((" · " + secondary) if secondary else "")
        alt = i18n.t(PANEL_FLIGHT_ALT_TEMPLATE) % flight

    return (
        '<figure class="preview-frame">'
        '<img class="preview-frame__image" src="%s%s" alt="%s" '
        'width="600" height="800" decoding="async">'
        "</figure>"
    ) % (GALLERY_ROUTE_PREFIX, escape_html(newest), escape_html(alt))


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
    the headline `(kind, title, detail)`, the next-update triple and the base wake
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
        headline = ("warn", i18n.t(STATE_BATTERY_TEXT), i18n.t(STATE_BATTERY_DETAIL))
    elif cfg.get("display_enabled") is False:
        headline = ("off", i18n.t(STATE_SCREEN_OFF_TEXT), i18n.t(STATE_SCREEN_OFF_DETAIL))
    elif quiet_remaining is not None:
        headline = ("off", i18n.t(STATE_QUIET_TEXT), i18n.t(STATE_QUIET_DETAIL) % quiet_end)
    else:
        headline = ("ok", i18n.t(STATE_SCREEN_ON_TEXT), "")
    return headline, wake.next_wake_status(
        ctx.last_checkin_ts, cfg, battery_critical=critical
    ), wake.effective_wake_interval_s(cfg, battery_critical=critical)


def _cadence_info_html(base_interval_s):
    """The "i" button beside the next-update line and the tooltip it
    describes. The button is a real focusable control, so the tooltip opens
    on hover, on keyboard focus and on a tap with no script (style.css);
    `aria-describedby` hands the same text to a screen reader.
    """
    if base_interval_s:
        text = i18n.t(CADENCE_INFO_TEXT) % _interval_text(base_interval_s)
    else:
        text = i18n.t(CADENCE_INFO_NO_INTERVAL_TEXT)
    return (
        '<span class="info-tip">'
        '<button type="button" class="info-tip__button" aria-label="%s" '
        'aria-describedby="%s">%s</button>'
        '<span class="info-tip__bubble text-label" role="tooltip" id="%s">%s</span>'
        "</span>"
    ) % (
        escape_html(i18n.t(CADENCE_INFO_LABEL)), CADENCE_INFO_ID,
        layout.icon_html("icon-info", 18), CADENCE_INFO_ID, escape_html(text))


def _next_update_html(next_iso, interval_s, hold_reason, now, base_interval_s):
    """The next-update row, or "" without a check-in. The wording template
    comes from frame_state, the single due/held/late decision shared with
    every other consumer. On time it reads "Next update in 5 min" (a live
    countdown, no clock); a held frame names the wake clock and a countdown;
    an overdue frame reads "Update overdue · expected at HH:MM" behind a
    warning sign, with no countdown. The cadence info button follows the
    line. Returns `(html, long_overdue)`; a long-overdue frame also gets the
    Health link, placed by the caller."""
    parsed = layout.parse_iso(next_iso) if next_iso else None
    if parsed is None:
        return "", False
    state = frame_state.resolve_state(next_iso, interval_s, hold_reason, now)
    template = frame_state.headline_template(state)
    before, after = i18n.t(template).split("%s", 1)
    long_overdue = frame_state.is_long_overdue(next_iso, interval_s, hold_reason, now)
    countdown = layout.relative_time_html(next_iso, now, countdown=True)
    if state == frame_state.STATE_DUE or state == frame_state.STATE_UNKNOWN:
        modifier, icon_id, tail = "", "icon-nav-history", ""
        value = countdown
    else:
        value = '<span class="time-value">%s</span>' % escape_html(
            layout.local_clock_text(parsed, now_parsed=layout.parse_iso(now)))
        if state == frame_state.STATE_LATE:
            modifier, icon_id, tail = " home-state__next--overdue", "icon-warning", ""
        else:
            modifier, icon_id = "", "icon-nav-history"
            tail = '<span class="home-state__countdown"> · %s</span>' % countdown
    text = "%s%s%s" % (escape_html(before), value, escape_html(after))
    return (
        '<div class="home-state__next-row">'
        '<p class="home-state__next%s">%s<span>%s%s</span></p>%s</div>' % (
            modifier, layout.icon_html(icon_id, 18, "home-state__next-icon"), text, tail,
            _cadence_info_html(base_interval_s))
    ), long_overdue


def _health_link_html():
    """The "See Health" pill shown once the frame is long overdue."""
    return '<a class="home-state__health-link" href="%s">%s%s</a>' % (
        HEALTH_ROUTE, escape_html(i18n.t(SEE_HEALTH_TEXT)),
        layout.icon_html("icon-chevron-right", 16))


def _quiet_window_text(cfg):
    """The configured quiet window as "23:30 – 06:00", shown whether or not
    the schedule is on, so the switch's detail says what it would cover."""
    return "%s – %s" % (
        cfg.get("quiet_hours_start") or DEFAULT_QUIET_START,
        cfg.get("quiet_hours_end") or DEFAULT_QUIET_END)


def _switch_row_html(spec, is_on, detail_html):
    """One labelled switch row. The control is the shared `role="switch"`
    form from `layout.quick_switch_html()`: a native POST that works with
    scripts blocked.

    The row deliberately carries no `data-quick-region`, so quick-switch.js
    leaves the submit alone and the browser follows the server's redirect:
    flipping either switch changes the headline and the next-update line
    too, so the page must be re-rendered rather than optimistically
    patched. `return_to` is one of the server-side whitelist's values.
    """
    action, slug, label, icon_id = spec
    label_id = "home-switch-%s-label" % slug
    state_id = "home-switch-%s-state" % slug
    return (
        '<div class="home-switch home-switch--%s">'
        '<span class="home-switch__icon">%s</span>'
        '<div class="home-switch__text">'
        '<span class="home-switch__label" id="%s">%s</span>'
        '<span class="home-switch__detail text-label">%s%s</span>'
        "</div>%s</div>"
    ) % (
        "on" if is_on else "off", layout.icon_html(icon_id, 18), label_id,
        escape_html(i18n.t(label)),
        layout.quick_switch_state_html(
            state_id, i18n.t(layout.QUICK_ACTION_ON_TEXT),
            i18n.t(layout.QUICK_ACTION_OFF_TEXT), is_on, extra_class="home-switch__state"),
        detail_html,
        layout.quick_switch_html(action, layout.HOME_ROUTE, is_on, label_id, state_id))


def _switches_html(cfg):
    screen_on = cfg.get("display_enabled") is not False
    quiet_on = cfg.get("quiet_hours_enabled") is True
    window = (
        ' · <span class="home-switch__window time-value">%s</span>'
        % escape_html(_quiet_window_text(cfg)))
    return (
        '<div class="home-state__switches" role="group" aria-label="%s">%s%s</div>'
    ) % (
        escape_html(i18n.t(SWITCHES_LABEL)),
        _switch_row_html(
            (QUICK_DISPLAY_ACTION, "screen", layout.QUICK_ACTION_SCREEN_LABEL,
             "icon-nav-display"),
            screen_on, ""),
        _switch_row_html(
            (QUICK_QUIET_HOURS_ACTION, "quiet", layout.QUICK_ACTION_QUIET_LABEL,
             "icon-moon"),
            quiet_on, window))


def _battery_level(ctx, percent):
    """"critical" for the battery-empty hold or an error health state,
    "low" at or under the shared low-battery percentage or on a warning
    health state, else "ok"."""
    health = ctx.health_state or {}
    if ctx.battery_critical is True or health.get("battery_state") == "error":
        return "critical"
    if health.get("battery_state") == "warn" or (
            percent is not None and percent <= battery.LOW_BATTERY_DISPLAY_PERCENT):
        return "low"
    return "ok"


def _battery_pill_html(ctx):
    """The battery dial: an open arc filled to the charge and coloured by
    level, the percentage and the word "Battery" in its middle, and for a
    low or critical level a word in the arc's gap as well, so the state
    never rests on colour alone. Reads only the latest stored reading from
    PageContext's state directory; the percentage is the shared piecewise
    estimate. A missing reading shows words only, never an invented dial.
    The whole block is one named image for screen readers."""
    reading = _safe_query(ctx.state_dir, _latest_battery)
    if not reading or not reading.get("battery_mv"):
        return '<p class="home-battery home-battery--none text-label">%s</p>' % escape_html(
            i18n.t(BATTERY_FACT_EMPTY))
    percent = battery.battery_percent(reading["battery_mv"])
    value = "%d%%" % percent if percent is not None else "%s mV" % reading["battery_mv"]
    level = _battery_level(ctx, percent)
    word = {"low": BATTERY_LOW_TEXT, "critical": BATTERY_CRITICAL_TEXT}.get(level)
    aria = i18n.t(BATTERY_ARIA_TEMPLATE) % (
        ("≈ " if percent is not None else "") + value)
    if word:
        aria = "%s, %s" % (aria, i18n.t(word).lower())
    if percent is not None:
        value_html = '%d<span class="home-battery__unit">%%</span>' % percent
        status = {"ok": "ok", "low": "warn", "critical": "error"}[level]
        dial = draw.arc_gauge(percent / 100.0, BATTERY_ARC_SIZE, draw.status_class(status))
    else:
        value_html, dial = escape_html(value), ""
    return (
        '<p class="home-battery home-battery--%s" role="img" aria-label="%s">%s'
        '<span class="home-battery__reading">'
        '<span class="home-battery__value">%s</span>'
        '<span class="home-battery__label">%s</span></span>%s</p>'
    ) % (
        level, escape_html(aria), dial, value_html, escape_html(i18n.t(BATTERY_LABEL)),
        ('<span class="home-battery__state">%s</span>' % escape_html(i18n.t(word)))
        if word else "")


def _frame_state_html(ctx):
    """The status header: a "Frame state" label, the current state as a
    short title beside a haloed dot (plus a sentence for a held state), the
    next update (with its cadence info) and, once long overdue, a Health
    link; then the battery dial and the screen and quiet-hours switches.
    The dot's tone also tints the card (green on, amber long overdue or
    battery hold, neutral when resting); a green or amber dot pulses a soft
    halo, a resting one stays still. Everything comes from the page
    context."""
    cfg = ctx.device_config or {}
    (tone, title, detail), (next_iso, interval_s, hold_reason), base_interval_s = (
        _frame_state_summary(ctx))
    next_html, long_overdue = _next_update_html(
        next_iso, interval_s, hold_reason, ctx.now, base_interval_s)
    if long_overdue:
        tone = "warn"
    detail_html = (
        '<p class="home-state__detail">%s</p>' % escape_html(detail)) if detail else ""
    return (
        '<section class="home-state home-state--%s" aria-labelledby="home-frame-state">'
        '<div class="home-state__body"><div class="home-state__status">'
        '<h2 class="home-state__eyebrow" id="home-frame-state">%s%s</h2>'
        '<p class="home-state__headline"><span class="home-state__dot dot dot--%s%s" '
        'aria-hidden="true"></span><span class="home-state__title">%s</span></p>'
        '%s%s%s</div>%s%s</div></section>'
    ) % (
        tone, layout.icon_html("icon-nav-display", 16),
        escape_html(i18n.t(FRAME_STATE_HEADING)), tone,
        "" if tone == "off" else " home-state__dot--pulse", escape_html(title),
        detail_html, next_html,
        _health_link_html() if long_overdue else "",
        _battery_pill_html(ctx), _switches_html(cfg))


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
    """The attention row as a docked toast: a persistent state, so no
    dismiss and no live-region role (it refreshes in place). Its tone
    follows the worst shared health state."""
    if not _needs_attention(ctx):
        return ""
    health = ctx.health_state or {}
    worst_is_error = any(health.get(name) == "error" for name in (
        "device_state", "pipeline_state", "battery_state"))
    return layout.toast_html(
        i18n.t(ACTION_NEEDED_TEXT),
        tone=layout.TOAST_TONE_ERROR if worst_is_error else layout.TOAST_TONE_WARNING,
        role="", docked=True, extra_class="home-action",
        action_html=layout.toast_link_action_html(
            layout.HEALTH_ROUTE, i18n.t(ACTION_NEEDED_LINK_TEXT)))


def render(ctx):
    """Render Home: the status header (state, next update, battery and the
    two switches) first, then the generated picture and its flight line,
    with the recent flights beside it on desktop and after it on a phone.
    Only an actionable shared health state adds a Health link; daily
    activity belongs to Health.
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
        + _frame_state_html(ctx)
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
        + _action_needed_html(ctx)
        + "</div>"
    )
