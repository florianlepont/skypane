"""companion/pages/home_page.py — the Home page (phase 18, companion audit
/ UX refactor).

The page a household member lands on after signing in, answering three
questions without any technical background: is the frame alive, what is
it showing, and what has it shown recently — plus the two or three
things they might actually want to *do* (switch the screen on or off,
start or end quiet hours, refresh now). Everything is a widget: a
self-contained card that reads one slice of `ctx` and, where it acts,
posts one small form to a quick-action route in companion/app.py.

Like every page module this one imports nothing from a sibling page
module (companion/pages/__init__.py's boundary). The status verdicts it
renders come straight from `ctx["health_state"]` (already computed once
per request by companion/app.py) and the recent-flight rows from one
`history_db` read of its own, formatted here with deliberately fewer
fields than the Flights page.

Everything dynamic passes through `layout.escape_html()`.
"""
from datetime import datetime, timezone

import companion.layout as layout
from companion.layout import escape_html
from server import device_config, history_db

PAGE_TITLE = "Home"
PAGE_PURPOSE = "Your frame at a glance."

RECENT_FLIGHTS_LIMIT = 5
RECENT_FLIGHTS_HEADING = "Recent flights"
RECENT_FLIGHTS_LINK_TEXT = "See all flights"
NO_FLIGHTS_HEADING = "No flights yet."
NO_FLIGHTS_BODY = (
    "The first aircraft the frame detects on the watched runway will "
    "appear here.")

NOW_SHOWING_HEADING = "On the frame now"
NOW_SHOWING_CAPTION_PREFIX = "Rendered "
NO_PANEL_HEADING = "Nothing rendered yet."
NO_PANEL_BODY = (
    "The server saves a copy of each picture it sends to the frame; the "
    "latest one will appear here.")
PANEL_ALT_TEXT = "The picture currently on the frame"

QUICK_ACTIONS_HEADING = "Quick actions"
QUICK_ACTIONS_CAPTION = (
    "These apply on their own — no Save needed. The frame picks them up "
    "the next time it wakes up (about five minutes when it is switched "
    "off).")

# Quick-action routes: companion/app.py's POST handlers for the two
# toggles. Literal here for the same reason layout's `/logout` is —
# app.py imports this module, so the reverse import would be a cycle.
QUICK_DISPLAY_ROUTE = "/quick/display"
QUICK_QUIET_HOURS_ROUTE = "/quick/quiet-hours"
POLL_ROUTE = "/poll-now"
FLIGHTS_ROUTE = "/flights"
GALLERY_ROUTE_PREFIX = "/gallery/"

# The form field both toggles submit: the state to switch TO, never a
# bare "toggle" verb — a double-tap on a slow connection must be
# idempotent, not flip the screen twice.
QUICK_STATE_FIELD = "state"
QUICK_STATE_ON = "on"
QUICK_STATE_OFF = "off"

SCREEN_WIDGET_LABEL = "Screen"
SCREEN_ON_TEXT = "On"
SCREEN_OFF_TEXT = "Off"
SCREEN_TURN_ON_BUTTON = "Switch on"
SCREEN_TURN_OFF_BUTTON = "Switch off"
QUIET_WIDGET_LABEL = "Quiet hours"
QUIET_ON_TEMPLATE = "On — %s to %s"
QUIET_OFF_TEXT = "Off"
QUIET_TURN_ON_BUTTON = "Turn on"
QUIET_TURN_OFF_BUTTON = "Turn off"
REFRESH_WIDGET_LABEL = "Refresh"
REFRESH_BUTTON_TEXT = "Refresh now"
REFRESH_HELP_TEXT = "Look for a new aircraft right away."
REFRESH_COOLDOWN_TEMPLATE = "Just refreshed — try again in %ds."

STATUS_HEADING = "Status"
FRAME_TILE_LABEL = "Frame"
BATTERY_TILE_LABEL = "Battery"
LAST_FLIGHT_TILE_LABEL = "Last flight"
DATA_TILE_LABEL = "Flight data"
HEALTH_LINK_TEXT = "See details on Health"

FRAME_STATE_TEXT = {
    "ok": "Checking in normally",
    "warn": "Has not checked in for a while",
    "error": "Has not checked in for a long time",
}
DATA_STATE_TEXT = {
    "ok": "Up to date",
    "warn": "A little stale",
    "error": "Stale — the server may be down",
}
BATTERY_STATE_TEXT = {
    "ok": "Healthy",
    "warn": "Dropping quickly",
    "error": "Dropping quickly",
}
NO_READING_TEXT = "No reading yet"

# A rough state-of-charge estimate for a single-cell LiPo: 4.2V full,
# 3.3V empty, linear in between. It is an estimate, and labelled as one
# ("≈") — the frame's own low-battery warning still uses the exact
# millivolt thresholds in server/poll_loop.py.
BATTERY_FULL_MV = 4200
BATTERY_EMPTY_MV = 3300


def battery_percent(mv):
    """A clamped 0-100 estimate for `mv`, or None for a non-numeric or
    non-positive reading. Never raises."""
    try:
        value = float(mv)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    ratio = (value - BATTERY_EMPTY_MV) / float(BATTERY_FULL_MV - BATTERY_EMPTY_MV)
    return int(round(max(0.0, min(1.0, ratio)) * 100))


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
        return "Departing"
    if raw == "arriving":
        return "Arriving"
    return ""


def _route_text(row):
    origin = row.get("origin") or ""
    destination = row.get("destination") or ""
    if origin and destination:
        return "%s → %s" % (origin, destination)
    return ""


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


def _status_tiles_html(ctx):
    health = ctx.get("health_state") or {}
    now = ctx.get("now")
    device_state = health.get("device_state") or "warn"
    pipeline_state = health.get("pipeline_state") or "warn"
    battery_state = health.get("battery_state") or "warn"

    frame_body = '<p class="text-body widget-verdict">%s</p>' % escape_html(
        FRAME_STATE_TEXT.get(device_state, FRAME_STATE_TEXT["warn"]))
    frame_html = frame_body + (
        '<p class="text-label widget-detail">%s</p>' % health["device_html"]
        if health.get("device_html") else "")

    reading = _safe_query(ctx.get("state_dir"), _latest_battery)
    if reading and reading.get("battery_mv"):
        pct = battery_percent(reading["battery_mv"])
        pct_text = ("≈ %d%%" % pct) if pct is not None else ""
        battery_html = (
            '<p class="text-body widget-verdict">%s</p>'
            '<p class="text-label widget-detail">%s · %s mV · %s</p>'
        ) % (
            escape_html(pct_text or BATTERY_STATE_TEXT.get(battery_state, "")),
            escape_html(BATTERY_STATE_TEXT.get(battery_state, "")),
            escape_html(str(reading["battery_mv"])),
            layout.concise_timestamp_html(reading.get("ts"), now),
        )
    else:
        battery_html = '<p class="text-body widget-verdict">%s</p>' % escape_html(NO_READING_TEXT)

    data_html = '<p class="text-body widget-verdict">%s</p>' % escape_html(
        DATA_STATE_TEXT.get(pipeline_state, DATA_STATE_TEXT["warn"]))
    if health.get("pipeline_html"):
        data_html += '<p class="text-label widget-detail">%s</p>' % health["pipeline_html"]

    tiles = (
        layout.stat_tile(FRAME_TILE_LABEL, frame_html, device_state, icon="icon-device")
        + layout.stat_tile(BATTERY_TILE_LABEL, battery_html, battery_state, icon="icon-battery")
        + layout.stat_tile(DATA_TILE_LABEL, data_html, pipeline_state, icon="icon-pipeline")
    )
    return (
        '<section class="home-section" aria-labelledby="home-status">'
        '<h2 class="text-heading" id="home-status">%s</h2>'
        '<div class="dashboard-grid home-status-grid">%s</div>'
        '<p class="text-label"><a href="/health">%s</a></p>'
        "</section>"
    ) % (escape_html(STATUS_HEADING), tiles, escape_html(HEALTH_LINK_TEXT))


def _toggle_form_html(action, next_state, button_text):
    return (
        '<form method="post" action="%s" class="quick-action__form">'
        '<input type="hidden" name="%s" value="%s">'
        '<button type="submit">%s</button>'
        "</form>"
    ) % (
        escape_html(action), QUICK_STATE_FIELD, escape_html(next_state),
        escape_html(button_text))


def _quick_actions_html(ctx):
    cfg = ctx.get("device_config") or {}
    display_on = cfg.get("display_enabled", device_config.DEFAULT_DISPLAY_ENABLED) is not False
    quiet_on = cfg.get("quiet_hours_enabled", device_config.DEFAULT_QUIET_HOURS_ENABLED) is True
    quiet_start = cfg.get("quiet_hours_start", device_config.DEFAULT_QUIET_HOURS_START)
    quiet_end = cfg.get("quiet_hours_end", device_config.DEFAULT_QUIET_HOURS_END)
    cooldown = ctx.get("poll_cooldown_remaining") or 0

    screen_widget = (
        '<div class="quick-action quick-action--%s">'
        '<div class="quick-action__text">'
        '<span class="text-label quick-action__label">%s%s</span>'
        '<span class="text-body quick-action__state">%s</span>'
        "</div>%s</div>"
    ) % (
        "on" if display_on else "off",
        layout.icon_html("icon-power", size=16, extra_class="quick-action__icon"),
        escape_html(SCREEN_WIDGET_LABEL),
        escape_html(SCREEN_ON_TEXT if display_on else SCREEN_OFF_TEXT),
        _toggle_form_html(
            QUICK_DISPLAY_ROUTE,
            QUICK_STATE_OFF if display_on else QUICK_STATE_ON,
            SCREEN_TURN_OFF_BUTTON if display_on else SCREEN_TURN_ON_BUTTON),
    )
    quiet_widget = (
        '<div class="quick-action quick-action--%s">'
        '<div class="quick-action__text">'
        '<span class="text-label quick-action__label">%s%s</span>'
        '<span class="text-body quick-action__state">%s</span>'
        "</div>%s</div>"
    ) % (
        "on" if quiet_on else "off",
        layout.icon_html("icon-moon", size=16, extra_class="quick-action__icon"),
        escape_html(QUIET_WIDGET_LABEL),
        escape_html(
            QUIET_ON_TEMPLATE % (quiet_start, quiet_end) if quiet_on else QUIET_OFF_TEXT),
        _toggle_form_html(
            QUICK_QUIET_HOURS_ROUTE,
            QUICK_STATE_OFF if quiet_on else QUICK_STATE_ON,
            QUIET_TURN_OFF_BUTTON if quiet_on else QUIET_TURN_ON_BUTTON),
    )
    if cooldown > 0:
        refresh_control = (
            '<button type="submit" disabled>%s</button>' % escape_html(REFRESH_BUTTON_TEXT))
        refresh_state = REFRESH_COOLDOWN_TEMPLATE % int(cooldown)
    else:
        refresh_control = (
            '<button type="submit">%s</button>' % escape_html(REFRESH_BUTTON_TEXT))
        refresh_state = REFRESH_HELP_TEXT
    refresh_widget = (
        '<div class="quick-action quick-action--neutral">'
        '<div class="quick-action__text">'
        '<span class="text-label quick-action__label">%s%s</span>'
        '<span class="text-body quick-action__state">%s</span>'
        "</div>"
        '<form method="post" action="%s" class="quick-action__form">%s</form>'
        "</div>"
    ) % (
        layout.icon_html("icon-refresh", size=16, extra_class="quick-action__icon"),
        escape_html(REFRESH_WIDGET_LABEL),
        escape_html(refresh_state),
        POLL_ROUTE, refresh_control,
    )
    return (
        '<section class="page-section home-section" aria-labelledby="home-actions">'
        '<h2 class="text-heading" id="home-actions">%s</h2>'
        '<p class="text-label section-caption">%s</p>'
        '<div class="quick-actions">%s%s%s</div>'
        "</section>"
    ) % (
        escape_html(QUICK_ACTIONS_HEADING), escape_html(QUICK_ACTIONS_CAPTION),
        screen_widget, quiet_widget, refresh_widget)


def _now_showing_html(ctx):
    entries = ctx.get("gallery_entries") or []
    now = ctx.get("now")
    newest = entries[0] if entries else None
    if not newest:
        body = layout.empty_state(NO_PANEL_HEADING, NO_PANEL_BODY)
    else:
        iso = _gallery_name_to_iso(newest)
        caption = (
            NOW_SHOWING_CAPTION_PREFIX + layout.concise_timestamp_html(iso, now)
            if iso else "")
        body = (
            '<figure class="now-showing">'
            '<img class="now-showing__image" src="%s%s" alt="%s" '
            'width="600" height="800" decoding="async">'
            '<figcaption class="text-label now-showing__caption">%s</figcaption>'
            "</figure>"
        ) % (
            GALLERY_ROUTE_PREFIX, escape_html(newest), escape_html(PANEL_ALT_TEXT),
            caption)
    return (
        '<section class="page-section home-section" aria-labelledby="home-now">'
        '<h2 class="text-heading" id="home-now">%s</h2>%s</section>'
    ) % (escape_html(NOW_SHOWING_HEADING), body)


def _recent_flights_html(ctx):
    now = ctx.get("now")
    rows = _safe_query(ctx.get("state_dir"), _recent_flights)
    if not rows:
        body = layout.empty_state(NO_FLIGHTS_HEADING, NO_FLIGHTS_BODY)
    else:
        items = []
        for row in rows:
            callsign = row.get("callsign") or row.get("hex") or "—"
            airline = row.get("airline") or ""
            route = _route_text(row)
            direction = _direction_text(row.get("confirmed_state"))
            secondary = " · ".join(part for part in (airline, route, direction) if part)
            items.append(
                '<li class="recent-flight">'
                '<span class="recent-flight__callsign mono">%s</span>'
                '<span class="recent-flight__detail text-label">%s</span>'
                '<span class="recent-flight__time text-label">%s</span>'
                "</li>"
                % (escape_html(callsign), escape_html(secondary),
                   layout.concise_timestamp_html(row.get("ts"), now)))
        body = '<ul class="recent-flights">%s</ul>' % "".join(items)
    return (
        '<section class="page-section home-section" aria-labelledby="home-flights">'
        '<h2 class="text-heading" id="home-flights">%s</h2>%s'
        '<p class="text-label"><a href="%s">%s</a></p>'
        "</section>"
    ) % (
        escape_html(RECENT_FLIGHTS_HEADING), body,
        FLIGHTS_ROUTE, escape_html(RECENT_FLIGHTS_LINK_TEXT))


def render(ctx):
    header = layout.page_header(PAGE_TITLE, purpose=PAGE_PURPOSE)
    return (
        header
        + _status_tiles_html(ctx)
        + '<div class="home-columns">'
        + _quick_actions_html(ctx)
        + _now_showing_html(ctx)
        + "</div>"
        + _recent_flights_html(ctx)
    )
