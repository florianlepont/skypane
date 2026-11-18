"""Home's title block: the frame's name, its state and the next update.

One section, `home-frame-state`, that `freshness.js` and the quick switches
repaint in place: the name (the page's one `<h1>`, with its rename pencil),
the shared frame-status dot beside its word, and one line with the next
update or, for a frame that has lost contact, its last contact, ending with
the "i" that explains why the frame does not refresh continuously. The
pieces are derived once from the page context by `summary()` and the shared
frame-status resolver.
"""
from types import SimpleNamespace

import companion.device_scope as device_scope
import companion.frame_state as frame_state
import companion.frame_status as frame_status
import companion.i18n as i18n
import companion.layout as layout
import companion.wake as wake
from companion.layout import escape_html
from companion.pages import home_notice, home_title

FRAME_STATE_HEADING = i18n.msg("home.frame_state", "Frame state")
# The info tooltip at the end of the next-update line. The first wording
# names the wake interval; the second is the fallback when none is known.
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


def _interval_text(interval_s):
    """"15 min" / "2 h" / "1 h 30" for a wake interval in seconds. Units are
    the same in English and French, so the text itself is not translated."""
    minutes = max(1, int(round(interval_s / 60.0)))
    if minutes < 60:
        return "%d min" % minutes
    hours, rest = divmod(minutes, 60)
    return "%d h" % hours if rest == 0 else "%d h %02d" % (hours, rest)


def summary(ctx):
    """`(next_triple, base_interval_s)`: the next-update triple and the base
    wake interval. Precedence mirrors `wake.effective_wake_interval_s()`: a
    battery-empty hold beats the display switch, which beats quiet hours."""
    cfg = ctx.device_config or {}
    critical = ctx.battery_critical is True
    return wake.next_wake_status(
        ctx.last_checkin_ts, cfg, battery_critical=critical
    ), wake.effective_wake_interval_s(cfg, battery_critical=critical)


def cadence_info_html(base_interval_s):
    """The "i" button at the end of the next-update line and the tooltip it
    describes. The button is a real focusable control, so the tooltip opens
    on hover, on keyboard focus and on a tap with no script (style.css);
    `aria-describedby` hands the same text to a screen reader."""
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


def _line_html(icon_id, text_html, base_interval_s, modifier=""):
    return (
        '<p class="home-state__next%s">%s<span class="home-state__sentence">%s%s</span></p>'
    ) % (modifier, layout.icon_html(icon_id, 18, "home-state__next-icon"),
         text_html, cadence_info_html(base_interval_s))


def next_update_html(next_iso, interval_s, hold_reason, now, base_interval_s):
    """The next-update line, or "" without a check-in. The wording template
    comes from frame_state, the single due/held/late decision shared with
    every other consumer. On time it reads "Next refresh in 5 min" (a live
    countdown); a held frame names the wake clock and a countdown; an overdue
    frame reads "Update overdue · expected at HH:MM" behind a warning sign.
    The cadence info button ends the line."""
    parsed = layout.parse_iso(next_iso) if next_iso else None
    if parsed is None:
        return ""
    state = frame_state.resolve_state(next_iso, interval_s, hold_reason, now)
    before, after = i18n.t(frame_state.headline_template(state)).split("%s", 1)
    countdown = layout.relative_time_html(next_iso, now, countdown=True)
    modifier, icon_id, tail = "", "icon-nav-history", ""
    if state == frame_state.STATE_DUE or state == frame_state.STATE_UNKNOWN:
        value = countdown
    else:
        value = '<span class="time-value">%s</span>' % escape_html(
            layout.local_clock_text(parsed, now_parsed=layout.parse_iso(now)))
        if state == frame_state.STATE_LATE:
            modifier, icon_id = " home-state__next--overdue", "icon-warning"
        else:
            tail = '<span class="home-state__countdown"> · %s</span>' % countdown
    return _line_html(
        icon_id, "%s%s%s%s" % (escape_html(before), value, escape_html(after), tail),
        base_interval_s, modifier)


def last_contact_html(last_seen, now, base_interval_s):
    """"Last contact 3h ago" for a frame that lost contact, "" without one."""
    if not last_seen:
        return ""
    return _line_html(
        "icon-nav-history",
        escape_html(i18n.t(home_notice.LINE_LAST_CONTACT)).replace(
            "%s", layout.relative_time_html(last_seen, now)),
        base_interval_s)


def _is_offline(ctx):
    """Whether a non-live frame has gone quiet for twice its wake interval."""
    device = ctx.device
    if device is None or getattr(device, "is_live", True):
        return False
    parsed = layout.parse_iso(ctx.now)
    now_epoch = parsed.timestamp() if parsed is not None else device_scope.now_epoch()
    return device_scope.device_status(device, now_epoch) == device_scope.STATUS_OFFLINE


def status_row(ctx, next_triple, battery_percent):
    """The inputs the shared frame-status resolver reads, from the page
    context: the same words the Fleet list and the frame switcher use."""
    cfg = ctx.device_config or {}
    next_iso, interval_s, hold_reason = next_triple
    state = frame_state.resolve_state(next_iso, interval_s, hold_reason, ctx.now)
    return SimpleNamespace(
        kind=frame_status.KIND_LIVE, offline=_is_offline(ctx),
        last_seen=ctx.last_checkin_ts or None, battery_percent=battery_percent,
        state=state, screen_off=cfg.get("display_enabled") is False)


def status_dot_html(status):
    """The state dot: one dot, its word carried by role, label and title (the
    visible word beside it is the sentence)."""
    word = escape_html(i18n.t(status.word))
    return (
        '<span class="home-state__dot dot dot--%s%s" role="img" aria-label="%s" '
        'title="%s"></span>'
    ) % (status.dot_state, "" if status.dot_state == frame_status.STATUS_OFF
         else " home-state__dot--pulse", word, word)


def section_html(ctx, next_triple, base_interval_s, status, say_once=False):
    """The title block. `say_once` drops the line when the notification above
    already says the frame is overdue and since when."""
    next_iso, interval_s, hold_reason = next_triple
    if status.key == frame_status.KEY_NO_CONTACT:
        line = last_contact_html(ctx.last_checkin_ts, ctx.now, base_interval_s)
    elif say_once:
        line = ""
    else:
        line = next_update_html(next_iso, interval_s, hold_reason, ctx.now, base_interval_s)
    return (
        '<section class="home-state home-state--%s reveal" aria-labelledby="home-frame-state">%s'
        '<h2 class="visually-hidden" id="home-frame-state">%s</h2>'
        '<p class="home-state__status">%s<span class="home-state__title">%s</span></p>%s'
        "</section>"
    ) % (
        status.dot_state, home_title.title_html(device_scope.current_device()),
        escape_html(i18n.t(FRAME_STATE_HEADING)),
        status_dot_html(status), escape_html(i18n.t(status.word)), line)
