"""The Home page: answers whether the frame is alive, what it is
showing, and what it has shown recently.

Opens with one hero (the current picture beside the frame's name as the
page title with its rename pencil, a pill with one dot and word for the
frame state, and the next update), then two glass groups of rows: the
frame's two native-POST switches (screen and quiet hours) with the
battery row, and the recent flights.
The dot is the shared frame-status dot; Home links to no Health
page (Health is an administrator's Console page), and neither a user nor an
administrator sees the attention bar here. Everyone sees the battery as one
row of the Frame group; an administrator also keeps the dial in the hero. The
recent-flight rows and the current picture's flight line share one
`history_db` read.
"""

from datetime import timezone
from types import SimpleNamespace

import companion.battery as battery
import companion.device_scope as device_scope
import companion.draw as draw
import companion.flight_card as flight_card
import companion.frame_state as frame_state
import companion.frame_status as frame_status
import companion.health_signals as health_signals
import companion.i18n as i18n
import companion.layout as layout
import companion.page_context as page_context
import companion.ui_groups as ui_groups
import companion.ui_modal as ui_modal
import companion.ui_time as ui_time
import companion.user_view as user_view
import companion.wake as wake
from companion.pages import home_battery_row, home_notice, home_title
from companion.layout import escape_html
from companion.settings import quiet_hours
from server import device_config, history_db
from server.plane import name_overrides
# The same presentation-only airline alias Flights applies via
# history_page.py's panel_render.display_airline_name() call.
# illustrations.normalise_airline_key() still resolves on the raw
# stored airline string — only user-visible text is aliased.
from server.plane import render as panel_render

PAGE_TITLE = i18n.msg("nav.home", "Home")

RECENT_FLIGHTS_LIMIT = 5
# Rows read before de-duplication, so five distinct flights still show
# when a pass was stored more than once.
RECENT_FLIGHTS_FETCH = RECENT_FLIGHTS_LIMIT * 3
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

# Shown instead of the shared "Nothing rendered yet" wording for a selected
# device that has not been sent a picture yet.
DEVICE_NO_IMAGE_HEADING = i18n.msg("home.device_no_image_heading", "No picture yet")
DEVICE_NO_IMAGE_BODY = i18n.msg(
    "home.device_no_image_body",
    "The first image appears after a poll or the frame\u2019s first wake.")

DIRECTION_DEPARTING_TEXT = i18n.msg("home.departing", "Departing")
DIRECTION_ARRIVING_TEXT = i18n.msg("home.arriving", "Arriving")
DIRECTION_OVERHEAD_TEXT = i18n.msg("home.overhead", "Overhead")
# Owned by companion/i18n_fr/flights.py: the same wording the Flights
# card uses for a missing callsign or airline.
NO_CALLSIGN_NOTE_TEXT = i18n.msg("flights.no_callsign", "no callsign")
AIRLINE_UNKNOWN_TEXT = i18n.msg("flights.airline_unknown", "Airline unknown")

BATTERY_LABEL = i18n.msg("home.battery_label", "Battery")
BATTERY_ARIA_TEMPLATE = i18n.msg("home.battery_aria", "Battery about %s")
BATTERY_LOW_TEXT = i18n.msg("home.battery_low", "Low")
BATTERY_CRITICAL_TEXT = i18n.msg("home.battery_critical", "Very low")
BATTERY_FACT_EMPTY = i18n.msg("home.battery_fact_empty", "Battery · No reading yet")
ACTION_NEEDED_TEXT = i18n.msg("home.action_needed", "Something needs attention")

NO_READING_TEXT = i18n.msg("home.no_reading_yet", "No reading yet")

# The status header. The quick routes are the same two server-validated
# POST endpoints the retired Frame strip posted to.
FRAME_STATE_HEADING = i18n.msg("home.frame_state", "Frame state")
QUICK_DISPLAY_ACTION = "/quick/display"
QUICK_QUIET_HOURS_ACTION = "/quick/quiet-hours"
QUICK_QUIET_HOURS_WINDOW_ACTION = "/quick/quiet-hours/window"
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
# The ring around the picture: the frame cycle until the next update. The
# name carries the same countdown the next-update line shows.
CYCLE_RING_LABEL = i18n.msg("home.cycle_ring", "Frame cycle: next refresh %s")
SWITCHES_LABEL = i18n.msg("home.switches", "Frame controls")
FRAME_GROUP_LABEL = i18n.msg("home.group_frame", "Frame")
EDIT_QUIET_HOURS_LABEL = i18n.msg(
    "home.edit_quiet_hours", "Edit quiet hours (%s)")
CLOSE_LABEL = i18n.msg("common.close", "Close")
# Literal, like the quick-action paths above: a page module cannot import
# its sibling that owns the route.
DETECTION_PATH = "/detection"
DEFAULT_QUIET_START = "23:00"
DEFAULT_QUIET_END = "07:00"


def _safe_query(state_dir, fn):
    try:
        with history_db.open_db(state_dir) as conn:
            return fn(conn)
    except Exception:
        return None


def _recent_flights(conn, airline_names=None):
    return flight_card.fold_repeated_passes(
        history_db.recent_runway_events(
            conn, limit=RECENT_FLIGHTS_FETCH, airline_names=airline_names),
        RECENT_FLIGHTS_LIMIT)


def _latest_battery(conn):
    return history_db.latest_device_health(conn)


def _recent_battery(conn):
    # Exactly the readings charging_estimate() can use: its longest window.
    return history_db.recent_device_health(
        conn, limit=battery.CHARGE_RAMP_WINDOW_WAKES)


def _direction_text(raw):
    if raw == "departing":
        return DIRECTION_DEPARTING_TEXT
    if raw == "arriving":
        return DIRECTION_ARRIVING_TEXT
    if raw == "overhead":
        return DIRECTION_OVERHEAD_TEXT
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
        device = ctx.device
        body = (
            DEVICE_NO_IMAGE_BODY if device is not None and not device.is_live
            else NO_PANEL_BODY)
        return (
            '<figure class="preview-frame preview-frame--empty">'
            '<div class="preview-empty">%s<p class="preview-empty__heading">%s</p></div>'
            '<figcaption class="visually-hidden">%s</figcaption></figure>' % (
                layout.icon_html("icon-device", 32, "preview-empty__glyph"),
                escape_html(i18n.t(DEVICE_NO_IMAGE_HEADING)), escape_html(i18n.t(body))))

    alt = i18n.t(PANEL_ALT_TEXT)
    if current_flight_row:
        callsign = current_flight_row.get("callsign") or current_flight_row.get("hex") or "—"
        secondary = _flight_secondary_text(current_flight_row)
        flight = callsign + ((" · " + secondary) if secondary else "")
        alt = i18n.t(PANEL_FLIGHT_ALT_TEMPLATE) % flight

    return (
        '<figure class="preview-frame">'
        '<img class="preview-frame__image" src="%s" alt="%s" '
        'width="600" height="800" decoding="async" fetchpriority="high">'
        "</figure>"
    ) % (
        escape_html(device_scope.scoped(GALLERY_ROUTE_PREFIX + newest)),
        escape_html(alt))


def _cycle_ring_html(ctx, next_triple):
    """The thin ring around the picture: the share of the frame cycle (wake,
    poll, display, sleep) already elapsed, from the same next-update triple
    the "Next refresh in N min" line reads. The progress is rendered as
    attributes (no style attribute, for the CSP); relative-time.js repaints
    it from `data-ring-next` / `data-ring-interval` each second. "" without
    a known next update."""
    next_iso, interval_s, _hold = next_triple
    parsed = layout.parse_iso(next_iso) if next_iso else None
    now_parsed = layout.parse_iso(ctx.now)
    if parsed is None or now_parsed is None or not interval_s:
        return ""
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    remaining = parsed.timestamp() - now_parsed.timestamp()
    progress = min(1.0, max(0.0, 1.0 - remaining / float(interval_s)))
    if remaining > 0:
        countdown = ui_time.relative_future_text(int(remaining))
    else:
        countdown = i18n.t(ui_time.RELATIVE_WAITING_TEXT)
    template = i18n.t(CYCLE_RING_LABEL)
    rect = ('<rect class="%s" x="0" y="0" width="100%%" height="100%%" rx="19" '
            'pathLength="100"%s/>')
    return (
        '<svg class="hero__ring" role="img" aria-label="%s" data-cycle-ring '
        'data-ring-next="%s" data-ring-interval="%d" data-ring-label="%s">%s%s%s%s</svg>'
        '<span class="hero__glass" aria-hidden="true"></span>'
    ) % (
        escape_html(template % countdown),
        escape_html(parsed.astimezone(timezone.utc).isoformat(timespec="seconds")),
        int(interval_s), escape_html(template),
        rect % ("hero__ring-track", ""),
        rect % ("hero__ring-ticks", ' stroke-dasharray="0 25"'),
        rect % ("hero__ring-bar", ' stroke-dasharray="100 100" stroke-dashoffset="%.2f"' % (
            100.0 * (1.0 - progress))),
        rect % ("hero__ring-done", ""),
    )


def _recent_flight_row_html(row, now):
    """One recent flight as an informational row (no link, no chevron): a plane
    chip turned by the direction, the callsign (or hex), the clock and
    "<airline> · <route> · <direction>" beneath it, and the relative age on the
    right."""
    callsign = row.get("callsign") or row.get("hex") or "—"
    secondary = _flight_secondary_text(row)
    ts = row.get("ts")
    parsed = layout.parse_iso(ts) if ts else None
    clock = (layout.local_clock_text(parsed, now_parsed=layout.parse_iso(now))
             if parsed is not None else "")
    detail = " · ".join(part for part in (clock, secondary) if part)
    return ui_groups.row(
        label_html='<span class="mono">%s</span>' % escape_html(callsign),
        icon="icon-plane", detail=detail,
        value_html=layout.relative_time_html(ts, now) if parsed is not None else "",
        extra_class="recent-flight",
        attrs='data-filter-kind="%s"' % escape_html(row.get("confirmed_state") or ""))


def _recent_flights_html(rows, now, state_dir):
    """The recent-flights group: one informational row per flight, then the one
    link row to the whole history. With no flight yet the group holds the empty state."""
    all_row = ui_groups.row(
        i18n.t(RECENT_FLIGHTS_LINK_TEXT), icon="icon-nav-history",
        href=device_scope.scoped(FLIGHTS_ROUTE), extra_class="recent-flight-all")
    if not rows:
        empty = '<li class="row row--empty"><div class="row__main">%s</div></li>' % (
            layout.empty_state(
                i18n.t(NO_FLIGHTS_HEADING), i18n.t(NO_FLIGHTS_BODY), compact=True))
        return ui_groups.group(
            empty + all_row, label=i18n.t(RECENT_FLIGHTS_HEADING),
            label_id="home-flights", extra_class="home-section")
    items = "".join(_recent_flight_row_html(row, now) for row in rows)
    return ui_groups.group(
        items + all_row, label=i18n.t(RECENT_FLIGHTS_HEADING), label_id="home-flights",
        extra_class="home-section")


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
    every other consumer. On time it reads "Next refresh in 5 min" (a live
    countdown, no clock); a held frame names the wake clock and a countdown;
    an overdue frame reads "Update overdue · expected at HH:MM" behind a
    warning sign, with no countdown. The cadence info button follows the
    line. Returns `(html, long_overdue)`."""
    parsed = layout.parse_iso(next_iso) if next_iso else None
    if parsed is None:
        return "", False
    state = frame_state.resolve_state(next_iso, interval_s, hold_reason, now)
    template = frame_state.headline_template(state)
    before, after = i18n.t(template).split("%s", 1)
    long_overdue = frame_state.is_long_overdue(next_iso, interval_s, hold_reason, now)
    countdown = layout.relative_time_html(next_iso, now, countdown=True)
    if state == frame_state.STATE_DUE or state == frame_state.STATE_UNKNOWN:
        modifier, icon_id, tail = "", "", ""
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
            modifier,
            layout.icon_html(icon_id, 18, "home-state__next-icon") if icon_id else "",
            text, tail,
            _cadence_info_html(base_interval_s))
    ), long_overdue


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

    The row is a quick-switch region that also asks for a refresh:
    quick-switch.js flips the switch under the finger over fetch, and once
    the server confirms, one freshness refresh repaints the headline and
    the next-update line in place, with no page load. Without scripts the
    form posts natively and the browser follows the server's redirect.
    `return_to` is one of the server-side whitelist's values.
    """
    action, slug, label, icon_id = spec
    label_id = "home-switch-%s-label" % slug
    state_id = "home-switch-%s-state" % slug
    return ui_groups.row(
        i18n.t(label), icon=icon_id, label_id=label_id,
        detail_html=layout.quick_switch_state_html(
            state_id, i18n.t(layout.QUICK_ACTION_ON_TEXT),
            i18n.t(layout.QUICK_ACTION_OFF_TEXT), is_on,
            extra_class="home-switch__state") + detail_html,
        trailing_html=layout.quick_switch_html(
            action, layout.HOME_ROUTE, is_on, label_id, state_id),
        extra_class="home-switch home-switch--%s home-switch--%s" % (
            "on" if is_on else "off", slug),
        attrs="%s data-quick-refresh" % layout.QUICK_SWITCH_REGION_ATTR)


def _battery_row_html(ctx, interval_s):
    """The Battery row: the latest reading, its level word, and the
    autonomy figure only while the frame is not charging. Empty for a frame
    that never checked in."""
    percent = _battery_percent(ctx)
    if percent is None and not ctx.last_checkin_ts:
        # A frame that never contacted SkyPane has no reading to show: the
        # state above already says so, once.
        return ""
    charging = percent is not None and _charging_likely(ctx)
    autonomy = "" if percent is None or charging else home_battery_row.autonomy_text(
        ctx.state_dir, ctx.now, interval_s, page_context.device_curve(ctx.device))
    return home_battery_row.row_html(
        percent, _row_battery_level(ctx, percent), charging, autonomy)


def _switches_html(cfg, battery_html=""):
    """The Frame group: the screen, quiet-hours and battery rows."""
    screen_on = cfg.get("display_enabled") is not False
    quiet_on = cfg.get("quiet_hours_enabled") is True
    # A link beside the switch's state, outside its <button>: the window
    # opens the Quiet hours dialog. The accessible name repeats the visible
    # window so it is never out of step with it.
    window_text = _quiet_window_text(cfg)
    window = " · " + ui_modal.trigger_html(
        quiet_hours.QUIET_DIALOG_ID,
        escape_html(window_text) + layout.icon_html("icon-chevron-right", 16, "home-switch__chevron"),
        extra_class="home-switch__window time-value",
        aria_label=i18n.t(EDIT_QUIET_HOURS_LABEL) % window_text)
    rows = (
        _switch_row_html(
            (QUICK_DISPLAY_ACTION, "screen", layout.QUICK_ACTION_SCREEN_LABEL,
             "icon-nav-display"),
            screen_on, "")
        + _switch_row_html(
            (QUICK_QUIET_HOURS_ACTION, "quiet", layout.QUICK_ACTION_QUIET_LABEL,
             "icon-moon"),
            quiet_on, window)
        + battery_html)
    return ui_groups.group(
        rows, label=i18n.t(FRAME_GROUP_LABEL), label_id="home-frame-controls",
        extra_class="home-state__switches home-section")


def _row_battery_level(ctx, percent):
    """The Battery row's level from the latest reading and the page
    context's hold flag alone; unlike the hero dial it never builds the
    health state, so every user's Home stays off the health pipeline."""
    if ctx.battery_critical is True:
        return "critical"
    if percent is not None and percent <= battery.LOW_BATTERY_DISPLAY_PERCENT:
        return "low"
    return "ok"


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


def _charging_likely(ctx):
    """Whether the recent voltage trend reads as a charge, by the shared
    estimate at this page's own (hold-aware) cadence."""
    rows = _safe_query(ctx.state_dir, _recent_battery)
    return health_signals.charging_likely(
        rows, ctx.now, ctx.device_config, ctx.battery_critical)


def _battery_pill_html(ctx):
    """The battery dial: an open arc filled to the charge and coloured by
    level, the percentage and the word "Battery" in its middle, and for a
    low or critical level a word in the arc's gap as well, so the state
    never rests on colour alone. Reads only the latest stored reading from
    PageContext's state directory; the percentage is the shared piecewise
    estimate. A missing reading shows words only, never an invented dial.
    When the voltage trend reads as a charge, a hedged "Probably charging"
    pill sits under the arc (and in the accessible name): an estimate, so
    never worded as a fact. The whole block is one named image for screen
    readers."""
    reading = _safe_query(ctx.state_dir, _latest_battery)
    if not reading or not reading.get("battery_mv"):
        return '<p class="home-battery home-battery--none text-label">%s</p>' % escape_html(
            i18n.t(BATTERY_FACT_EMPTY))
    percent = battery.percent(
        reading["battery_mv"], page_context.device_curve(ctx.device))
    value = "%d%%" % percent if percent is not None else "%s mV" % reading["battery_mv"]
    level = _battery_level(ctx, percent)
    word = {"low": BATTERY_LOW_TEXT, "critical": BATTERY_CRITICAL_TEXT}.get(level)
    aria = i18n.t(BATTERY_ARIA_TEMPLATE) % (
        ("≈ " if percent is not None else "") + value)
    if word:
        aria = "%s, %s" % (aria, i18n.t(word).lower())
    charging = _charging_likely(ctx)
    if charging:
        aria = "%s, %s" % (aria, i18n.t(layout.BATTERY_CHARGING_TEXT).lower())
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
        '<span class="home-battery__label">%s</span></span>%s%s</p>'
    ) % (
        level, escape_html(aria), dial, value_html, escape_html(i18n.t(BATTERY_LABEL)),
        ('<span class="home-battery__state">%s</span>' % escape_html(i18n.t(word)))
        if word else "",
        layout.battery_charging_pill_html("home-battery__charging")
        if charging else "")


def _battery_percent(ctx):
    """The latest battery reading as a percentage, or None without one."""
    reading = _safe_query(ctx.state_dir, _latest_battery)
    if not reading or not reading.get("battery_mv"):
        return None
    return battery.percent(reading["battery_mv"], page_context.device_curve(ctx.device))


def _is_offline(ctx):
    """Whether a non-live frame has gone quiet for twice its wake interval."""
    device = ctx.device
    if device is None or getattr(device, "is_live", True):
        return False
    parsed = layout.parse_iso(ctx.now)
    now_epoch = parsed.timestamp() if parsed is not None else device_scope.now_epoch()
    return device_scope.device_status(device, now_epoch) == device_scope.STATUS_OFFLINE


def _status_row(ctx, next_triple):
    """The inputs the shared frame-status resolver reads, from the page
    context: the same words the Fleet list and the frame switcher use."""
    cfg = ctx.device_config or {}
    next_iso, interval_s, hold_reason = next_triple
    state = frame_state.resolve_state(next_iso, interval_s, hold_reason, ctx.now)
    # A battery-empty hold reads as a low battery even without a stored reading.
    percent = 0 if ctx.battery_critical is True else _battery_percent(ctx)
    return SimpleNamespace(
        kind=frame_status.KIND_LIVE, offline=_is_offline(ctx),
        last_seen=ctx.last_checkin_ts or None, battery_percent=percent,
        state=state, screen_off=cfg.get("display_enabled") is False)


def _status_dot_html(status):
    """The 14px state dot: one dot, its word carried by role, label and title
    (no visible text of its own; the headline beside it is the sentence)."""
    word = escape_html(i18n.t(status.word))
    return (
        '<span class="home-state__dot dot dot--%s%s" role="img" aria-label="%s" '
        'title="%s"></span>'
    ) % (status.dot_state, "" if status.dot_state == frame_status.STATUS_OFF
         else " home-state__dot--pulse", word, word)


def _frame_state_html(ctx, summary, status, picture_html="", say_once=False):
    """The hero, with no surface of its own: the current picture beside the
    frame's name (the page title, with its rename pencil), a pill holding one
    haloed dot and the state word (both from the shared frame-status resolver;
    a sentence follows a held state), the next update with its cadence info and, for an
    administrator, the battery dial. The dot's tone also tints the hero's
    glow; a resting dot stays still, every other one pulses a soft halo.
    `summary` is `_frame_state_summary(ctx)` and `status` the resolver's
    verdict on it, both read once by render()."""
    (_tone, _screen_title, detail), next_triple, base_interval_s = summary
    word = i18n.t(status.word)
    next_iso, interval_s, hold_reason = next_triple
    next_html, _long_overdue = _next_update_html(
        next_iso, interval_s, hold_reason, ctx.now, base_interval_s)
    if say_once:
        # The notification above already says the frame is overdue and since
        # when; the hero keeps only the word.
        next_html = ""
    detail_html = (
        '<p class="home-state__detail">%s</p>' % escape_html(detail)) if detail else ""
    user = user_view.is_personal_view()
    return ui_groups.hero(
        '%s<span class="home-state__title">%s</span>' % (
            _status_dot_html(status), escape_html(word)),
        picture_html=picture_html,
        lines_html=detail_html + next_html + ("" if user else _battery_pill_html(ctx)),
        status_class="home-state__pill",
        title_html=home_title.title_html(device_scope.current_device()),
        extra_class="home-state home-state--%s%s reveal" % (
            status.dot_state, " home-state--no-battery" if user else ""),
        attrs='aria-labelledby="home-frame-state"',
        heading_html='<h2 class="visually-hidden" id="home-frame-state">%s</h2>' % escape_html(
            i18n.t(FRAME_STATE_HEADING)))


def _attention_states():
    """The health states the attention row reads: a user's row follows
    the frame's own signals only, never the flight-data pipeline."""
    if user_view.is_personal_view():
        return ("device_state", "battery_state")
    return ("device_state", "pipeline_state", "battery_state")


def _needs_attention(ctx):
    """Whether Home should show the attention row.

    Quiet-hours sleep is intentional and therefore excluded.  Every other
    warn/error state already belongs to the shared, server-derived health
    snapshot; Home only decides whether that snapshot warrants the row.
    """
    health = ctx.health_state or {}
    return any(health.get(name) in ("warn", "error") for name in _attention_states())


def _action_needed_html(ctx):
    """The attention row as a docked toast: a persistent state, so no
    dismiss and no live-region role (it refreshes in place). Its tone
    follows the worst shared health state."""
    if not _needs_attention(ctx):
        return ""
    health = ctx.health_state or {}
    worst_is_error = any(health.get(name) == "error" for name in _attention_states())
    return layout.toast_html(
        i18n.t(ACTION_NEEDED_TEXT),
        tone=layout.TOAST_TONE_ERROR if worst_is_error else layout.TOAST_TONE_WARNING,
        role="", docked=True, extra_class="home-action")


def _notice_html(ctx, status):
    """The amber or red notification, from the very status the dot shows;
    "" for any other status. Its figures are the ones the state card reads."""
    if not home_notice.applies(status):
        return ""
    device = ctx.device
    facts = SimpleNamespace(
        frame_name=getattr(device, "name", None) or "",
        percent=0 if ctx.battery_critical is True else _battery_percent(ctx),
        charging=_charging_likely(ctx), last_seen=ctx.last_checkin_ts or None,
        now=ctx.now)
    contact = home_notice.contact_for_state_dir(ctx.root_state_dir or ctx.state_dir)
    return home_notice.notification_html(facts, status, contact)


def quiet_hours_dialog_html(ctx, errors=None, submitted=None):
    """The Quiet hours dialog, rendered open when a save was refused. It is
    a sibling of the swapped regions below, never inside one, so a
    background refresh cannot discard an open dialog or a half-typed time.
    The dialog opens on its title so no time field raises the native picker
    or the keyboard unasked."""
    cfg = ctx.device_config or {}
    return ui_modal.dialog_html(
        quiet_hours.QUIET_DIALOG_ID, i18n.t(STATE_QUIET_TEXT),
        device_scope.scoped(QUICK_QUIET_HOURS_WINDOW_ACTION, "POST"), layout.csrf_field(),
        quiet_hours.quiet_hours_dialog_body_html(
            cfg, device_scope.scoped(DETECTION_PATH) + "#details", errors, submitted),
        i18n.t(quiet_hours.QUIET_DIALOG_SAVE_LABEL), i18n.t(CLOSE_LABEL),
        device_scope.scoped(layout.HOME_ROUTE), open_=bool(errors),
        focus_title=True)


def render(ctx, quiet_errors=None, quiet_submitted=None):
    """Render Home: the hero (the current picture beside the state, next
    update and battery), then the Frame group (the screen and quiet-hours
    switches, the most used controls, kept near the top) and the Recent
    flights group. An actionable shared health state adds the attention row; daily
    activity belongs to Health. `quiet_errors`/`quiet_submitted` re-render
    the Quiet hours dialog open after a refused save.
    """
    ctx = page_context.coerce(ctx)
    now = ctx.now
    # One read, reused for both the hero's flight one-liner (its first
    # row is "the current flight") and the recent-flights list — never
    # two independent queries for the same data.
    names = name_overrides.names_by_prefix(ctx.name_overrides)
    rows = _safe_query(ctx.state_dir, lambda conn: _recent_flights(conn, names))
    current_flight_row = rows[0] if rows else None
    # The silent marker keeps Home on freshness.js's background refresh
    # without a visible freshness line.
    # The page's one h1 is the frame name inside the hero.
    header = layout.page_header(
        i18n.t(PAGE_TITLE), freshness_html=layout.refresh_marker_html(now),
        omit_title=True)
    summary = _frame_state_summary(ctx)
    status = frame_status.frame_status(_status_row(ctx, summary[1]))
    notice = _notice_html(ctx, status)
    picture = _current_picture_html(ctx, current_flight_row) + _cycle_ring_html(ctx, summary[1])
    return (
        header
        + '<div class="home-facts">'
        + (notice or ("" if user_view.is_personal_view() else _action_needed_html(ctx)))
        + "</div>"
        + _frame_state_html(
            ctx, summary, status, picture,
            say_once=bool(notice) and status.key == frame_status.KEY_OVERDUE)
        + _switches_html(ctx.device_config or {}, _battery_row_html(ctx, summary[2]))
        + _recent_flights_html(rows, now, ctx.state_dir)
        + quiet_hours_dialog_html(ctx, quiet_errors, quiet_submitted)
    )
