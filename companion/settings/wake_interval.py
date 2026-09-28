"""The Wake interval settings group: the freshness/battery-life gauge
text, the range slider and `wake_interval_group()` itself.
"""
from datetime import timedelta

from companion import i18n
from companion import battery
from companion.layout import escape_html
import companion.layout as layout
from server import device_config, history_db

from companion.settings.form import (
    DIRTY_SECTION_ATTR, SETTINGS_FORM_ID, _field_error_attrs, _field_error_html,
    _with_next_wake)


WAKE_INTERVAL_SECTION_HEADING = i18n.msg("display.wake_interval", "Wake interval")
WAKE_INTERVAL_SECTION_CAPTION = i18n.msg(
    "display.shorter_fresher_data_more_battery_drain",
    "Shorter: fresher data, more battery drain.")
WAKE_INTERVAL_PLACEHOLDER_TEXT = i18n.msg("display.uses_server_default", "Uses server default")
# The number input's own visible label, distinct from
# WAKE_SLIDER_LABEL below (the paired range control's own name).
WAKE_INTERVAL_INPUT_LABEL = i18n.msg(
    "display.wake_interval_seconds", "Wake interval (seconds)")
# The unit, rendered as a sibling beside the number input (never a
# placeholder, which vanishes once a value is typed). Not routed
# through i18n.t(): "s" is the SI symbol for a second, the same symbol
# in French, so it is a unit symbol, not prose. aria-hidden, since the
# field's own translated label already says "seconds".
WAKE_INTERVAL_UNIT_LABEL = "s"
WAKE_INTERVAL_INPUT_ID = "wake-interval-s"
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

WAKE_SLIDER_CLASS = "wake-slider"
WAKE_SLIDER_INPUT_CLASS = "wake-slider__input"
WAKE_SLIDER_STEP_S = 60
# Its own accessible name: the number input's label names that
# control, and two controls sharing one name loses a screen-reader
# visitor track of which they are on.
WAKE_SLIDER_LABEL = i18n.msg("display.wake_interval_slider", "Wake interval slider")


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


def wake_slider_html(interval_s):
    """The range input, inside the `.js` gate — `""` when there is no
    saved interval to start from.

    Carries no `name`: a named range would post a second value for
    `wake_interval_s`, and whichever arrived last would win silently.
    The `<input type="number">` is the only control on this card that
    posts; this one only writes into it via `value-controls.js`.

    Gated, since a range with no script drags and shows nothing; the
    gauges and number input are not gated. `min`/`max` come from
    `device_config`, never re-typed, so this control can never accept
    what `save_device_config()`'s own server-side re-check would reject.
    """
    if interval_s is None:
        return ""
    return (
        '<div class="%s %s" %s %s="%s" %s="%s" %s="%d" %s="%d" %s="%d">'
        '<input type="range" class="%s" %s value="%d" min="%d" max="%d" step="%d"'
        ' aria-label="%s" aria-describedby="%s %s">'
        "</div>"
    ) % (
        escape_html(WAKE_SLIDER_CLASS), escape_html(layout.JS_GATE_CLASS),
        layout.VALUE_CONTROL_ATTR,
        layout.VALUE_CONTROL_FIELD_ATTR, escape_html(WAKE_INTERVAL_FIELD_NAME),
        layout.VALUE_CONTROL_FORM_ATTR, SETTINGS_FORM_ID,
        layout.VALUE_CONTROL_MIN_ATTR, device_config.WAKE_INTERVAL_MIN_S,
        layout.VALUE_CONTROL_MAX_ATTR, device_config.WAKE_INTERVAL_MAX_S,
        layout.VALUE_CONTROL_STEP_ATTR, WAKE_SLIDER_STEP_S,
        escape_html(WAKE_SLIDER_INPUT_CLASS), layout.VALUE_CONTROL_INPUT_ATTR,
        interval_s,
        device_config.WAKE_INTERVAL_MIN_S, device_config.WAKE_INTERVAL_MAX_S,
        WAKE_SLIDER_STEP_S,
        escape_html(i18n.t(WAKE_SLIDER_LABEL)),
        escape_html(WAKE_GAUGE_FRESHNESS_ID), escape_html(WAKE_GAUGE_BATTERY_ID),
    )


def wake_interval_group(current_wake_interval_s, errors=None, submitted=None, next_wake_clock=None,
                        battery_rows=None):
    """The Wake interval settings group: a plain `<label>` wraps a
    single `<input type="number">` (no checkbox gate, unlike
    `quiet_hours_group()`). `min`/`max` come from `device_config`
    rather than re-typed literals.

    The `value` attribute is emitted only for an in-range, non-bool
    int; otherwise the placeholder carries the empty state — an
    out-of-range `value` fails HTML5 constraint validation and blocks
    the whole form's submission. On a rejected save the raw submitted
    string is echoed back verbatim instead, bypassing that guard so the
    user sees what they typed. `battery_rows` feeds the battery gauge,
    which appends after the error block.
    """
    if submitted is not None and "wake_interval_s" in submitted:
        raw_submitted = submitted["wake_interval_s"]
        value_attr = ' value="%s"' % escape_html(raw_submitted) if raw_submitted else ""
    else:
        value_attr = (
            ' value="%d"' % current_wake_interval_s
            if (
                isinstance(current_wake_interval_s, int)
                and not isinstance(current_wake_interval_s, bool)
                and device_config.WAKE_INTERVAL_MIN_S <= current_wake_interval_s <= device_config.WAKE_INTERVAL_MAX_S
            ) else "")
    error_attrs = _field_error_attrs(
        errors, "wake_interval_s", "wake-interval-s", hint_id=WAKE_INTERVAL_SECTION_CAPTION_ID)
    error_html = _field_error_html(errors, "wake_interval_s", "wake-interval-s")
    # One resolution of the gauges' and the slider's subject, so the
    # three can never describe different values.
    gauge_interval_s = wake_gauge_interval_s(current_wake_interval_s, submitted)
    return (
        '<div class="theme-status" %s="%s">'
        '<h2 class="text-heading">%s</h2>'
        '<p class="text-label section-caption" id="%s">%s</p>'
        # The label is its own element above the control (for=), not a
        # wrapping <label> — a wrapping label put its text and the
        # input on one line, misaligning this field against every
        # sibling field on the page.
        '<label for="%s">%s</label>'
        '<input type="number" id="%s" name="wake_interval_s" min="%d" max="%d"'
        ' placeholder="%s"%s%s>'
        # The unit as a sibling, aria-hidden: the label above already
        # names the unit, so repeating it would announce the fact twice.
        '<span class="text-label field-inline-value" aria-hidden="true">%s</span>'
        "%s"
        # The slider sits after the error message, not between it and
        # the field, so the error stays adjacent to the control it is
        # about. The gauges come last, since they describe what the
        # setting means, after the control that sets it.
        "%s%s"
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(i18n.t(WAKE_INTERVAL_SECTION_HEADING)),
        escape_html(i18n.t(WAKE_INTERVAL_SECTION_HEADING)),
        escape_html(WAKE_INTERVAL_SECTION_CAPTION_ID),
        escape_html(_with_next_wake(i18n.t(WAKE_INTERVAL_SECTION_CAPTION), next_wake_clock)),
        escape_html(WAKE_INTERVAL_INPUT_ID), escape_html(i18n.t(WAKE_INTERVAL_INPUT_LABEL)),
        escape_html(WAKE_INTERVAL_INPUT_ID),
        device_config.WAKE_INTERVAL_MIN_S, device_config.WAKE_INTERVAL_MAX_S,
        escape_html(i18n.t(WAKE_INTERVAL_PLACEHOLDER_TEXT)),
        value_attr, error_attrs,
        escape_html(WAKE_INTERVAL_UNIT_LABEL),
        error_html,
        wake_slider_html(gauge_interval_s),
        wake_gauges_html(gauge_interval_s, battery_rows),
    )
