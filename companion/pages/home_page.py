"""The Home page: answers whether the frame is alive, what it is showing, how
busy the runway has been and what it showed recently.

Top to bottom, one column: the title block (the frame's name with its rename
pencil, its state and the next update), the notification while the frame
needs help, the flight card (the picture on the frame beside its flight), the
pills (Screen switch, Quiet hours, place, battery), the statistics card (today
by hour or the week by day) and the strip of recent flights. Home links to no
Health page (Health is an administrator's Console page), and neither a user
nor an administrator sees the attention bar here. The flight card, the
statistics and the strip share one `history_db` read.
"""

from types import SimpleNamespace

import companion.battery as battery
import companion.device_scope as device_scope
import companion.flight_card as flight_card
import companion.frame_status as frame_status
import companion.health_signals as health_signals
import companion.i18n as i18n
import companion.layout as layout
import companion.page_context as page_context
import companion.ui_modal as ui_modal
import companion.user_view as user_view
from companion.pages import (
    home_battery_row, home_flight_card, home_notice, home_pills, home_recent_strip,
    home_state, home_stats)
from companion.settings import quiet_hours
from server import history_db
from server.plane import name_overrides

PAGE_TITLE = i18n.msg("nav.home", "Home")

RECENT_FLIGHTS_LIMIT = 5
# Rows read before de-duplication, so five distinct flights still show
# when a pass was stored more than once.
RECENT_FLIGHTS_FETCH = RECENT_FLIGHTS_LIMIT * 3
ACTION_NEEDED_TEXT = i18n.msg("home.action_needed", "Something needs attention")
QUICK_QUIET_HOURS_WINDOW_ACTION = "/quick/quiet-hours/window"
STATE_QUIET_TEXT = i18n.msg("home.state_title_quiet_hours", "Quiet hours")
CLOSE_LABEL = i18n.msg("common.close", "Close")
# Literal, like the quick-action paths: a page module cannot import its
# sibling that owns the route.
DETECTION_PATH = "/detection"
# The zone every window of Home's statistics is cut in.
FRAME_ZONE = "Europe/Paris"


def _safe_query(state_dir, fn):
    try:
        with history_db.open_db(state_dir) as conn:
            return fn(conn)
    except Exception:
        return None


def _quiet_windows(cfg):
    """The saved quiet window as `[(start_hour, end_hour)]` floats for the
    statistics timeline, or `[]` while the schedule is off."""
    if cfg.get("quiet_hours_enabled") is not True:
        return []
    start = quiet_hours.quiet_window_minute_of_day(
        cfg.get("quiet_hours_start") or home_pills.DEFAULT_QUIET_START)
    end = quiet_hours.quiet_window_minute_of_day(
        cfg.get("quiet_hours_end") or home_pills.DEFAULT_QUIET_END)
    if start is None or end is None or start == end:
        return []
    return [(start / 60.0, end / 60.0)]


def _read_history(ctx, names):
    """One `history_db` scope for the whole page: the recent rows (repeated
    passes folded), the three statistics reads and the latest battery
    reading. None when the database cannot be read."""
    def read(conn):
        return SimpleNamespace(
            rows=flight_card.fold_repeated_passes(
                history_db.recent_runway_events(
                    conn, limit=RECENT_FLIGHTS_FETCH, airline_names=names),
                RECENT_FLIGHTS_LIMIT),
            timeline=history_db.home_day_timeline(conn, FRAME_ZONE, ctx.now),
            week=history_db.home_week_totals(conn, FRAME_ZONE, ctx.now),
            highlights=history_db.home_airline_highlights(
                conn, FRAME_ZONE, ctx.now, airline_names=names),
            battery=history_db.latest_device_health(conn))
    return _safe_query(ctx.state_dir, read)


def _now_hour(now):
    """The local hour of day of `now` as a float (14.5 for 14:30), or None."""
    parsed = layout.parse_iso(now)
    if parsed is None:
        return None
    local = parsed.astimezone(layout.LOCAL_TZ)
    return local.hour + local.minute / 60.0


def _recent_battery(conn):
    # Exactly the readings charging_estimate() can use: its longest window.
    return history_db.recent_device_health(
        conn, limit=battery.CHARGE_RAMP_WINDOW_WAKES)


def _row_battery_level(ctx, percent):
    """The battery pill's level from the latest reading and the page
    context's hold flag alone, so every user's Home stays off the health
    pipeline."""
    if ctx.battery_critical is True:
        return "critical"
    if percent is not None and percent <= battery.LOW_BATTERY_DISPLAY_PERCENT:
        return "low"
    return "ok"


def _charging_likely(ctx):
    """Whether the recent voltage trend reads as a charge, by the shared
    estimate at this page's own (hold-aware) cadence."""
    rows = _safe_query(ctx.state_dir, _recent_battery)
    return health_signals.charging_likely(
        rows, ctx.now, ctx.device_config, ctx.battery_critical)


def _battery_percent(reading, ctx):
    """The latest battery reading as a percentage, or None without one."""
    if not reading or not reading.get("battery_mv"):
        return None
    return battery.percent(reading["battery_mv"], page_context.device_curve(ctx.device))


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


def _notice_html(ctx, status, percent):
    """The amber or red notification, from the very status the dot shows;
    "" for any other status. Its figures are the ones the state card reads."""
    if not home_notice.applies(status):
        return ""
    device = ctx.device
    facts = SimpleNamespace(
        frame_name=getattr(device, "name", None) or "",
        percent=percent,
        charging=_charging_likely(ctx), last_seen=ctx.last_checkin_ts or None,
        now=ctx.now)
    contact = home_notice.contact_for_state_dir(ctx.root_state_dir or ctx.state_dir)
    return home_notice.notification_html(facts, status, contact)


def quiet_hours_dialog_html(ctx, errors=None, submitted=None):
    """The Quiet hours dialog, rendered open when a save was refused. It is
    a sibling of the swapped regions, never inside one, so a background
    refresh cannot discard an open dialog or a half-typed time. The dialog
    opens on its title so no time field raises the native picker or the
    keyboard unasked."""
    cfg = ctx.device_config or {}
    return ui_modal.dialog_html(
        quiet_hours.QUIET_DIALOG_ID, i18n.t(STATE_QUIET_TEXT),
        device_scope.scoped(QUICK_QUIET_HOURS_WINDOW_ACTION, "POST"), layout.csrf_field(),
        quiet_hours.quiet_hours_dialog_body_html(
            cfg, device_scope.scoped(DETECTION_PATH) + "#details", errors, submitted),
        i18n.t(quiet_hours.QUIET_DIALOG_SAVE_LABEL), i18n.t(CLOSE_LABEL),
        device_scope.scoped(layout.HOME_ROUTE), open_=bool(errors),
        focus_title=True)


def render(ctx, quiet_errors=None, quiet_submitted=None, place=None):
    """Render Home. `quiet_errors`/`quiet_submitted` re-render the Quiet
    hours dialog open after a refused save. `place` is the frame's own
    position row (or None), which the place pill names in position mode."""
    ctx = page_context.coerce(ctx)
    history = _read_history(ctx, name_overrides.names_by_prefix(ctx.name_overrides))
    rows = history.rows if history else []
    cfg = ctx.device_config or {}
    next_triple, base_interval_s = home_state.summary(ctx)
    percent = 0 if ctx.battery_critical is True else _battery_percent(
        history.battery if history else None, ctx)
    status = frame_status.frame_status(home_state.status_row(ctx, next_triple, percent))
    notice = _notice_html(ctx, status, percent)
    profile = device_scope.profile_for(device_scope.current_device())
    # The silent marker keeps Home on freshness.js's background refresh
    # without a visible freshness line. The page's one h1 is the frame name.
    header = layout.page_header(
        i18n.t(PAGE_TITLE), freshness_html=layout.refresh_marker_html(ctx.now),
        omit_title=True)
    return (
        header + '<div class="home%s">' % (
            " home--offline" if status.key == frame_status.KEY_NO_CONTACT else "")
        + home_state.section_html(
            ctx, next_triple, base_interval_s, status,
            say_once=bool(notice) and status.key == frame_status.KEY_OVERDUE)
        + '<div class="home-facts">'
        + (notice or ("" if user_view.is_personal_view() else _action_needed_html(ctx)))
        + "</div>"
        + home_flight_card.card_html(ctx, rows[0] if rows else None)
        + home_pills.pills_html(
            cfg, place, device_scope.scoped(DETECTION_PATH), home_battery_row.pill_html(
                percent, _row_battery_level(ctx, percent),
                percent is not None and _charging_likely(ctx)))
        + _stats_html(history, ctx.now, cfg)
        + home_recent_strip.recent_strip_html(
            rows, ctx.now, ctx.state_dir, ctx.gallery_entries or [], landscape=profile.width > profile.height)
        + "</div>"
        + quiet_hours_dialog_html(ctx, quiet_errors, quiet_submitted)
    )


def _stats_html(history, now, cfg):
    """The statistics card; with an unreadable history it is the card at zero."""
    empty = history is None
    return home_stats.stats_card_html(
        {"arriving": 0, "departing": 0, "ticks": []} if empty else history.timeline,
        [] if empty else history.week, None if empty else history.highlights,
        now_hour=_now_hour(now), quiet_windows=_quiet_windows(cfg))
