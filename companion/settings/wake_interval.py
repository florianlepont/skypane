"""The Wake interval settings group: the freshness/battery-life gauge
text, the range slider and `wake_interval_group()` itself.
"""
from datetime import timedelta

from companion import i18n
from companion import battery
from companion.layout import escape_html
from companion.ui_base import icon_html
import companion.layout as layout
from server import device_config, history_db

from companion.settings.form import (
    DIRTY_SECTION_ATTR, _field_error_attrs, _field_error_html)


WAKE_INTERVAL_SECTION_HEADING = i18n.msg("display.wake_interval", "Wake interval")
WAKE_INTERVAL_SECTION_CAPTION = i18n.msg(
    "display.choose_how_often_the_frame_checks",
    "Choose how often the frame checks for new flight data.")
# The minutes field's own accessible name; the tile's visible label is the
# section heading.
WAKE_INTERVAL_INPUT_LABEL = i18n.msg(
    "display.wake_interval_minutes_input", "Wake interval (minutes)")
WAKE_INTERVAL_UNIT_LABEL = i18n.msg("display.wake_interval_unit_min", "min")
# The tile's headline value ("#" is the minute count, repainted by script).
WAKE_INTERVAL_MINUTES_TEXT = i18n.msg("display.wake_minutes_value", "# min")
WAKE_INTERVAL_DEFAULT_TAG = i18n.msg("display.wake_interval_default_tag", "Default")
WAKE_INTERVAL_HINT = i18n.msg(
    "display.wake_interval_range_hint", "1 to 60 min, in 1 min steps.")
WAKE_INTERVAL_HINT_DEFAULT = i18n.msg(
    "display.wake_interval_default_hint", "Default: # min.")
WAKE_INTERVAL_SHORTCUTS_LABEL = i18n.msg("display.wake_interval_shortcuts", "Shortcuts")
WAKE_INTERVAL_DECREASE_LABEL = i18n.msg(
    "display.wake_interval_decrease", "Decrease by one minute")
WAKE_INTERVAL_INCREASE_LABEL = i18n.msg(
    "display.wake_interval_increase", "Increase by one minute")
WAKE_INTERVAL_INPUT_ID = "wake-interval-m"
WAKE_INTERVAL_SECTION_CAPTION_ID = "wake-interval-caption"

# The wake interval trades off freshness against battery life. Only one
# side can be stated honestly today: freshness is true by construction
# as long as it says "at most" (the frame learns about a plane at its
# next wake, so it appears at most one interval later). Battery life
# has no first-principles formula (no per-wake energy cost is known),
# so its figure comes from `battery.battery_life_estimate()`'s own
# observed discharge slope, or the named "not enough history" state
# when it refuses to derive one — never an invented number.
WAKE_INTERVAL_FIELD_NAME = "wake_interval_s"
# The minutes field's own posted name. Script keeps the seconds field equal to
# minutes x 60; without script the server converts this one.
WAKE_INTERVAL_MINUTES_FIELD_NAME = "wake_interval_min"
WAKE_INTERVAL_MINUTES_MIN = device_config.WAKE_INTERVAL_MIN_S // 60
WAKE_INTERVAL_MINUTES_MAX = device_config.WAKE_INTERVAL_MAX_S // 60
WAKE_INTERVAL_PRESET_MINUTES = (5, 15, 30, 60)
WAKE_GAUGE_CLASS = "wake-gauge"
WAKE_GAUGE_FRESHNESS_ID = "wake-gauge-freshness"
WAKE_GAUGE_BATTERY_ID = "wake-gauge-battery"
WAKE_GAUGE_SECONDS_PER_MINUTE = 60
# Deliberately shorter than health_page's own 3-month trend window:
# this sentence says "recent", and two weeks is comfortably more than
# battery.LIFE_MIN_OBSERVED_SPAN_DAYS while staying recent.
WAKE_BATTERY_WINDOW_DAYS = 14
# The quantity's place is "#", never "%s"/"%d"/"{}": every template
# below reaches the browser as an attribute value value-controls.js
# substitutes into live, and a check scans every French render for a
# stray format artefact.
WAKE_FRESHNESS_TEXT = i18n.msg(
    "display.a_plane_reaches_the_frame_at_most_min_later",
    "A plane reaches the frame at most # min later.")
# Carries this app's own "≈" honesty marker plus the source of the
# claim, so it is never read as a datasheet number.
WAKE_BATTERY_DAY_TEXT = i18n.msg(
    "display.day_of_battery_left_from_this_frame_s_own",
    "≈ # day of battery left, from this frame's own recent readings.")
WAKE_BATTERY_DAYS_TEXT = i18n.msg(
    "display.days_of_battery_left_from_this_frame_s_own",
    "≈ # days of battery left, from this frame's own recent readings.")
WAKE_BATTERY_UNKNOWN_TEXT = i18n.msg(
    "display.not_enough_battery_history_yet_to_say_how_long",
    "Not enough battery history yet to say how long a charge lasts.")
# Neither the bound nor the battery figure applies while the screen is
# off, since DISPLAY_OFF_SLEEP_S is pinned independently of this field
# then.
WAKE_BATTERY_SCREEN_OFF_TEXT = i18n.msg(
    "display.while_the_screen_is_off_the_frame_wakes_every",
    "While the screen is off, the frame wakes every %s instead.")
# The relative half, and the only half value-controls.js may recompute
# while the slider moves: two cadences, never a ratio (which would only
# be a valid multiplier on lifetime if every joule went into waking).
# "%d" is the saved cadence (server-side, fixed for the page); "#" is
# the proposed one, the only thing the script substitutes.
WAKE_BATTERY_INSTEAD_TEXT = i18n.msg(
    "display.this_setting_wakes_the_frame_every_min_instead",
    "This setting wakes the frame every # min instead of every %d min.")


def wake_gauge_interval_s(current_wake_interval_s, submitted=None):
    """The interval the two gauges describe, as an int inside
    `[WAKE_INTERVAL_MIN_S, WAKE_INTERVAL_MAX_S]`, or `None` (nothing
    renders). On a rejected save, echoes the raw submitted string
    rather than the stored value so the gauges match the field being
    fixed — but an out-of-range echo ("7", "99999") still renders no
    gauge. Total by construction: never raises.
    """
    if submitted is not None and "wake_interval_s" in submitted:
        raw = submitted["wake_interval_s"]
        try:
            candidate = int(str(raw).strip())
        except (TypeError, ValueError):
            return None
    elif isinstance(current_wake_interval_s, int) and not isinstance(
            current_wake_interval_s, bool):
        candidate = current_wake_interval_s
    else:
        return None
    if device_config.WAKE_INTERVAL_MIN_S <= candidate <= device_config.WAKE_INTERVAL_MAX_S:
        return candidate
    return None


def _wake_minutes(interval_s):
    """`interval_s` as a whole number of minutes, rounded up.

    Both sentences are claims about a bound: a 90-second cadence bounds
    the wait at a minute and a half, and `90 // 60` would print "at
    most 1 min", which is false. The ceiling prints "at most 2 min",
    true and merely loose. This control's own step is a whole minute;
    the ceiling matters for values already on disk from before it
    existed.
    """
    return -(-int(interval_s) // WAKE_GAUGE_SECONDS_PER_MINUTE)


def wake_freshness_text(interval_s):
    """"A plane reaches the frame at most 5 min after it passes." — the
    bound, or `""` when there is no interval to bound.

    "At most" is the whole sentence: the frame learns about a plane at
    its next wake, so a plane that passes one instant after a wake
    appears one whole interval later and never later — true for every
    interval, by construction, unlike a claim about typical behaviour.
    """
    if interval_s is None:
        return ""
    return i18n.t(WAKE_FRESHNESS_TEXT).replace(
        layout.VALUE_CONTROL_TEXT_TOKEN, str(_wake_minutes(interval_s)))


def wake_battery_observed_text(interval_s, battery_rows=None):
    """The battery half: an absolute figure only when observed history
    supports one, else the named "not enough history yet" sentence;
    `""` when there is no interval. The figure is
    `battery.battery_life_estimate()`'s, never computed here — this
    only picks singular vs. plural wording. `battery_rows` defaults to
    `()`, the ordinary state of a fresh deployment.
    """
    if interval_s is None:
        return ""
    estimate = battery.battery_life_estimate(
        battery_rows or (), interval_s, interval_s)
    days = estimate["days_remaining"]
    if (estimate["trend"] == battery.LIFE_TREND_FALLING
            and isinstance(days, int) and not isinstance(days, bool)):
        template = WAKE_BATTERY_DAY_TEXT if days == 1 else WAKE_BATTERY_DAYS_TEXT
        return i18n.t(template).replace(
            layout.VALUE_CONTROL_TEXT_TOKEN, str(days))
    return i18n.t(WAKE_BATTERY_UNKNOWN_TEXT)


def wake_screen_off_text():
    """"While the screen is off the frame wakes every 5m instead,
    whatever this is set to."

    Rendered unconditionally beside the battery sentence, not gated on
    `display_enabled`: the clause is true whichever way that switch is
    set, and a qualifier shown only once the screen is off is one
    nobody reads in time.

    The cadence goes through `layout.duration_text()` since it is a
    fixed constant; the two sentences above do not, since their number
    changes as the slider moves and would need a second copy of the
    ladder in JavaScript to recompute client-side.
    """
    return i18n.t(WAKE_BATTERY_SCREEN_OFF_TEXT) % layout.duration_text(
        device_config.DISPLAY_OFF_SLEEP_S)


def wake_battery_relative_template(saved_interval_s):
    """The relative clause's template, saved cadence already written
    in and `#` standing for the proposed one — `""` with no usable
    saved cadence. "This setting wakes the frame every # min instead of
    every 10 min." — two whole cadences, not a ratio, since a ratio
    needs a decimal mark that differs between English and French.

    Routed through `battery.battery_life_estimate()`'s
    `relative_factor` for its guard: a clause built on a cadence that
    function would refuse (bool, non-numeric, non-positive) is about
    nothing.
    """
    estimate = battery.battery_life_estimate(
        (), saved_interval_s, saved_interval_s)
    if estimate["relative_factor"] is None:
        return ""
    return i18n.t(WAKE_BATTERY_INSTEAD_TEXT) % _wake_minutes(saved_interval_s)


def wake_battery_relative_text(proposed_interval_s, saved_interval_s):
    """The relative clause as the server would render it for a given
    proposal — `""` when the two cadences are equal, the case every
    real page render produces. The one definition of this sentence in
    Python; `test_browser_ux.py` compares the script's own live output
    against it. Never carries a days figure: that half stays
    server-rendered, deliberately unreachable from script.
    """
    template = wake_battery_relative_template(saved_interval_s)
    if not template:
        return ""
    estimate = battery.battery_life_estimate(
        (), saved_interval_s, proposed_interval_s)
    factor = estimate["relative_factor"]
    if factor is None or factor == 1.0:
        return ""
    return template.replace(
        layout.VALUE_CONTROL_TEXT_TOKEN, str(_wake_minutes(proposed_interval_s)))


def wake_battery_rows(state_dir, now=None):
    """`WAKE_BATTERY_WINDOW_DAYS` of daily battery averages for the
    battery sentence, or `()` on any read failure or absent state dir.
    Never raises: a settings page that 500s because a battery history
    table could not be opened would be worse than a card that says it
    has no history yet.

    Read here rather than threaded through `ctx`: this is the only card
    that needs the series, and `page_context()` runs on every
    authenticated render.
    """
    if not state_dir:
        return ()
    try:
        with history_db.open_db(state_dir) as conn:
            return history_db.daily_battery_averages(
                conn, since=_wake_battery_cutoff_iso(now))
    except Exception:
        return ()


def _wake_battery_cutoff_iso(now):
    """The `since=` bound for the read above, or `None` when `now` does
    not parse — in which case `daily_battery_averages()` degrades to an
    UNBOUNDED read, health_page's own documented choice for the one
    input it does not control: more history rather than none.
    """
    parsed = layout.parse_iso(now)
    if parsed is None:
        return None
    return (parsed - timedelta(days=WAKE_BATTERY_WINDOW_DAYS)).isoformat(
        timespec="seconds")


def wake_gauges_html(interval_s, battery_rows=None):
    """The two gauges, as two muted sentences — `""` when there is no
    interval. Server-rendered, outside the `.js` gate: a script only
    updates these, never creates them, so a failed script leaves
    correct sentences. Neither is a live region — they'd re-announce
    continuously during a drag; the range announces itself natively.
    """
    if interval_s is None:
        return ""
    # The freshness paragraph is entirely live (its whole text is
    # arithmetic on the value); the battery paragraph's figure came
    # from observed history, so only its trailing span (two cadences,
    # no days figure) may be rewritten by script.
    return (
        '<p class="text-label section-caption %s" id="%s" %s="%s" %s="%s" %s="%d">%s</p>'
        '<p class="text-label section-caption %s" id="%s">%s %s '
        '<span %s="%s" %s="%s" %s="%d" %s="%d">%s</span></p>'
    ) % (
        escape_html(WAKE_GAUGE_CLASS), escape_html(WAKE_GAUGE_FRESHNESS_ID),
        layout.VALUE_CONTROL_READOUT_ATTR, escape_html(WAKE_INTERVAL_FIELD_NAME),
        layout.VALUE_CONTROL_READOUT_TEXT_ATTR,
        escape_html(i18n.t(WAKE_FRESHNESS_TEXT)),
        layout.VALUE_CONTROL_READOUT_SCALE_ATTR, WAKE_GAUGE_SECONDS_PER_MINUTE,
        escape_html(wake_freshness_text(interval_s)),

        escape_html(WAKE_GAUGE_CLASS), escape_html(WAKE_GAUGE_BATTERY_ID),
        escape_html(wake_battery_observed_text(interval_s, battery_rows)),
        escape_html(wake_screen_off_text()),
        layout.VALUE_CONTROL_READOUT_ATTR, escape_html(WAKE_INTERVAL_FIELD_NAME),
        layout.VALUE_CONTROL_READOUT_TEXT_ATTR,
        escape_html(wake_battery_relative_template(interval_s)),
        layout.VALUE_CONTROL_READOUT_SCALE_ATTR, WAKE_GAUGE_SECONDS_PER_MINUTE,
        # The base: the readout says nothing while the proposed value
        # is still the saved one (every page load and no-JS render).
        layout.VALUE_CONTROL_READOUT_BASE_ATTR, interval_s,
        escape_html(wake_battery_relative_text(interval_s, interval_s)),
    )



def _whole_minutes(interval_s):
    """`interval_s` as whole minutes (rounded up) when it is a usable
    interval, else `None`."""
    if (isinstance(interval_s, int) and not isinstance(interval_s, bool)
            and device_config.WAKE_INTERVAL_MIN_S <= interval_s
            <= device_config.WAKE_INTERVAL_MAX_S):
        return _wake_minutes(interval_s)
    return None


def _submitted_minutes(submitted):
    """The minutes string a rejected save echoes back, or `None` when the
    submission carried neither field: the minutes field when posted, else the
    seconds field converted."""
    if submitted is None:
        return None
    if WAKE_INTERVAL_MINUTES_FIELD_NAME in submitted:
        return str(submitted[WAKE_INTERVAL_MINUTES_FIELD_NAME] or "")
    if WAKE_INTERVAL_FIELD_NAME in submitted:
        raw = str(submitted[WAKE_INTERVAL_FIELD_NAME] or "").strip()
        try:
            return str(_wake_minutes(int(raw))) if raw else ""
        except ValueError:
            return raw
    return None


def _wake_presets_html(minutes):
    buttons = "".join(
        '<button type="button" class="theme-option%s" data-minutes-preset="%d" '
        'aria-pressed="%s">%d</button>' % (
            " theme-option--active" if preset == minutes else "", preset,
            "true" if preset == minutes else "false", preset)
        for preset in WAKE_INTERVAL_PRESET_MINUTES)
    return (
        '<span class="theme-form fleet-presets %s" role="group" aria-label="%s">%s</span>' % (
            escape_html(layout.JS_GATE_CLASS),
            escape_html(i18n.t(WAKE_INTERVAL_SHORTCUTS_LABEL)), buttons))


def _wake_stepper_html(minutes_value, placeholder, error_attrs):
    def step(delta, label):
        return (
            '<button type="button" class="fleet-step" data-minutes-step="%d" '
            'aria-label="%s">%s</button>' % (
                delta, escape_html(i18n.t(label)), "−" if delta < 0 else "+"))
    return (
        '<span class="fleet-stepper" role="group">%s'
        '<label class="visually-hidden" for="%s">%s</label>'
        '<input type="number" id="%s" class="fleet-minutes" name="%s" data-minutes-input'
        ' min="%d" max="%d" step="1" inputmode="numeric" placeholder="%s"%s%s>'
        '<span class="fleet-unit" aria-hidden="true">%s</span>%s</span>' % (
            # Both buttons need script; the number field alone works without.
            step(-1, WAKE_INTERVAL_DECREASE_LABEL).replace(
                'class="fleet-step"', 'class="fleet-step js-gate"'),
            escape_html(WAKE_INTERVAL_INPUT_ID), escape_html(i18n.t(WAKE_INTERVAL_INPUT_LABEL)),
            escape_html(WAKE_INTERVAL_INPUT_ID),
            escape_html(WAKE_INTERVAL_MINUTES_FIELD_NAME),
            WAKE_INTERVAL_MINUTES_MIN, WAKE_INTERVAL_MINUTES_MAX, escape_html(placeholder),
            ' value="%s"' % escape_html(minutes_value) if minutes_value else "", error_attrs,
            escape_html(i18n.t(WAKE_INTERVAL_UNIT_LABEL)),
            step(1, WAKE_INTERVAL_INCREASE_LABEL).replace(
                'class="fleet-step"', 'class="fleet-step js-gate"')))


def wake_interval_group(current_wake_interval_s, errors=None, submitted=None, next_wake_clock=None,
                        battery_rows=None, default_interval_s=None):
    """The Wake interval tile: one control in whole minutes (1 to 60) over
    the stored seconds. The minutes field posts `wake_interval_min`; a hidden
    `wake_interval_s` carries minutes x 60 for scripts and the server
    (`form_post.resolve_wake_interval`) accepts either. The tile's value and
    its "Default" tag are repainted by `value-controls.js` as the minutes
    change. On a rejected save the submitted text is echoed back verbatim, so
    the person sees what they typed. `next_wake_clock` and `battery_rows` are
    accepted for callers built before the tile.
    """
    echoed = _submitted_minutes(submitted)
    if echoed is not None:
        minutes_value = echoed
    else:
        current = _whole_minutes(current_wake_interval_s)
        minutes_value = str(current) if current else ""
    default_minutes = _whole_minutes(default_interval_s)
    try:
        minutes = int(minutes_value)
    except ValueError:
        minutes = None
    # An interval already on disk that is not a whole minute keeps its exact
    # seconds until the minutes are changed.
    if echoed is None and _whole_minutes(current_wake_interval_s):
        seconds_value = str(current_wake_interval_s)
    else:
        seconds_value = str(minutes * 60) if minutes is not None else ""
    error_attrs = _field_error_attrs(
        errors, "wake_interval_s", WAKE_INTERVAL_INPUT_ID, hint_id=WAKE_INTERVAL_SECTION_CAPTION_ID)
    error_html = _field_error_html(errors, "wake_interval_s", WAKE_INTERVAL_INPUT_ID)
    heading = escape_html(i18n.t(WAKE_INTERVAL_SECTION_HEADING))
    shown = (i18n.t(WAKE_INTERVAL_MINUTES_TEXT).replace(
        layout.VALUE_CONTROL_TEXT_TOKEN, str(minutes))
        if minutes is not None else "—")
    is_default = default_minutes is not None and minutes == default_minutes
    default_hint = (
        " " + i18n.t(WAKE_INTERVAL_HINT_DEFAULT).replace(
            layout.VALUE_CONTROL_TEXT_TOKEN, str(default_minutes))
        if default_minutes is not None else "")
    return (
        '<div class="fleet-tile fleet-tile--wide fleet-tile--control" data-state="off" '
        '%s="%s" data-minutes-control data-minutes-default="%s" data-minutes-text="%s">'
        '<span class="fleet-tile__text">'
        '<span class="fleet-tile__head"><span class="fleet-tile__icon">%s</span>'
        '<span class="fleet-tile__label">%s</span></span>'
        '<span class="fleet-tile__value"><span data-minutes-readout>%s</span>'
        '<span class="banner__pill fleet-default"%s data-minutes-tag>%s</span></span>'
        '<span class="fleet-tile__meta" id="%s">%s</span></span>'
        '<span class="fleet-tile__ui">%s'
        '<input type="hidden" name="%s" value="%s" data-minutes-seconds>%s'
        '<span class="fleet-tile__hint" id="wake-interval-hint">%s%s</span>%s</span>'
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, heading,
        default_minutes if default_minutes is not None else "",
        escape_html(i18n.t(WAKE_INTERVAL_MINUTES_TEXT)),
        icon_html("icon-refresh", 20), heading,
        escape_html(shown),
        "" if is_default else " hidden", escape_html(i18n.t(WAKE_INTERVAL_DEFAULT_TAG)),
        escape_html(WAKE_INTERVAL_SECTION_CAPTION_ID),
        escape_html(i18n.t(WAKE_INTERVAL_SECTION_CAPTION)),
        _wake_stepper_html(
            minutes_value, str(default_minutes) if default_minutes is not None else "",
            error_attrs),
        escape_html(WAKE_INTERVAL_FIELD_NAME), escape_html(seconds_value),
        _wake_presets_html(minutes),
        escape_html(i18n.t(WAKE_INTERVAL_HINT)), escape_html(default_hint), error_html,
    )
