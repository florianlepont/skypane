"""The Quiet hours settings group: the window-arithmetic helpers, the
24h dial SVG/handles/readout, and `quiet_hours_group()` itself.
"""
import collections
import re

from companion import i18n
from companion import draw
from companion.layout import escape_html
import companion.layout as layout
from companion import prefs
from server import device_config

from companion.settings.form import (
    DIRTY_SECTION_ATTR, SETTINGS_FORM_ID, _field_error_attrs,
    _field_error_html, _submitted_or_current)


# The Frame strip is the only quiet-hours on/off control; this caption
# states enable-by-schedule semantics rather than an on/off state.
QUIET_HOURS_SECTION_HEADING = i18n.msg("display.quiet_hours", "Quiet hours")
QUIET_HOURS_SECTION_CAPTION = i18n.msg(
    "display.pauses_the_frame_s_wake_poll_and_display_cycle",
    "Pauses the frame's wake, poll and display cycle during the "
    "schedule below.")
QUIET_HOURS_SECTION_CAPTION_ID = "quiet-hours-caption"
# The card's own heading id: the Frame strip's Quiet-hours switch cell
# links here as a fragment target, not a new control.
QUIET_HOURS_GROUP_HEADING_ID = "quiet-hours-group-heading"

# The Night preset's start/end are sourced from device_config's own
# shipped defaults rather than retyped literals, so the preset and the
# default can never drift apart.
QUIET_HOURS_PRESET_NIGHT_START = device_config.DEFAULT_QUIET_HOURS_START
QUIET_HOURS_PRESET_NIGHT_END = device_config.DEFAULT_QUIET_HOURS_END
QUIET_HOURS_PRESET_NIGHT_LABEL = i18n.msg("display.night", "Night")
QUIET_HOURS_PRESET_WORKDAY_START = "08:00"
QUIET_HOURS_PRESET_WORKDAY_END = "18:00"
QUIET_HOURS_PRESET_WORKDAY_LABEL = i18n.msg("display.day", "Day")
# "Always on" unchecks the enable checkbox and leaves both times
# untouched, via a distinct data-preset-enabled="0" attribute rather
# than overloading the time attributes with a sentinel value.
QUIET_HOURS_PRESET_ALWAYS_ON_LABEL = i18n.msg("display.always_on", "Always on")
QUIET_HOURS_PRESET_ATTR = "data-quiet-preset"


# The quiet window always runs forward from start, through midnight if
# necessary: 23:00 to 07:00 is eight hours going forward and sixteen
# going the other way, and an `end - start` implementation would draw
# the wrong one. The shipped default window is exactly this case.
#
# The same shape regex feeds both the text and the drawn geometry, so a
# future loosening cannot apply to one and not the other.
_HHMM_RE = re.compile(r"^\d{2}:\d{2}$")

QUIET_WINDOW_MINUTES_PER_DAY = 24 * 60

# `start_fraction`/`sweep_fraction` are turns of the ring (0 at twelve
# o'clock, growing clockwise, matching companion/draw.py's circle
# helpers); `minutes` is the same span in whole minutes, the single
# source both a card's printed duration and its drawn arc read from.
QuietWindowSpan = collections.namedtuple(
    "QuietWindowSpan", "start_fraction sweep_fraction minutes")


def quiet_window_minute_of_day(value):
    """`value` ("HH:MM") as whole minutes since local midnight, or `None`
    when it is not a real time of day. Never raises.

    `None` is the "render nothing" signal: an unset or unparseable
    stored window must draw no arc rather than a plausible-looking one
    starting at midnight. Values reaching here are already
    server-validated by `handle_post()`; this is the second gate.

    The shape regex alone is not enough: `^\\d{2}:\\d{2}$` accepts
    "99:99", which would become minute 5,999 of a 1,440-minute day.
    """
    if not value or not _HHMM_RE.match(str(value)):
        return None
    hours, minutes = (int(part) for part in str(value).split(":"))
    if hours > 23 or minutes > 59:
        return None
    return hours * 60 + minutes


def quiet_window_span(start_hm, end_hm):
    """The quiet window as a `QuietWindowSpan`, or `None` when either
    end does not parse. Never raises. Always forward from `start_hm`,
    through midnight if necessary (a modulo, not a subtraction): 23:00
    to 07:00 is 480 minutes, and 07:00 to 23:00 is its complement, 960.

    Equal start and end is a zero-length window, not a whole day,
    matching `server.device_config.seconds_until_quiet_hours_end()`'s
    contract — the largest expressible window is therefore 1439
    minutes, matching the dial's own `aria-valuemax`.
    """
    start = quiet_window_minute_of_day(start_hm)
    end = quiet_window_minute_of_day(end_hm)
    if start is None or end is None:
        return None
    minutes = (end - start) % QUIET_WINDOW_MINUTES_PER_DAY
    return QuietWindowSpan(
        start / float(QUIET_WINDOW_MINUTES_PER_DAY),
        minutes / float(QUIET_WINDOW_MINUTES_PER_DAY),
        minutes)


def _normalised_time_html(value):
    """The normalised 24h value rendered as a visible, `aria-hidden`
    sibling beside a native `<input type="time">`, since a native time
    control formats from the browser's own locale (e.g. "23:00" as
    "11:00 PM" in en-US) with no way to tell it matches a preset.

    Renders nothing for a falsy/unparseable value. The span carries
    `QUIET_NORMALISED_TIME_ATTR`, a hook `value-controls.js` reads to
    hide it on a browser that is already unambiguous.
    """
    if not value or not _HHMM_RE.match(str(value)):
        return ""
    return (
        ' <span class="text-label field-inline-value" %s aria-hidden="true">%s</span>'
    ) % (QUIET_NORMALISED_TIME_ATTR, escape_html(value))


# Class names as constants rather than literals at the emission site: a
# class that exists in Python and nowhere in style.css paints nothing,
# and a check scans emitted markup against the stylesheet for exactly
# that.
QUIET_DIAL_CLASS = "quiet-dial"
QUIET_DIAL_RING_CLASS = "quiet-dial__ring"
QUIET_DIAL_DAY_CLASS = "quiet-dial__day"
QUIET_DIAL_ARC_CLASS = "quiet-dial__arc"
QUIET_DIAL_HOUR_CLASS = "quiet-dial__hour"
QUIET_DIAL_READOUT_CLASS = "quiet-dial__readout"

QUIET_PRESET_ROW_CLASS = "quiet-preset-row"
QUIET_TIMES_ROW_CLASS = "quiet-times-row"

# The stable hook _normalised_time_html() marks its own span with, so
# value-controls.js can find and hide only it, never the wake-interval
# unit sibling that shares .field-inline-value but carries no hook.
QUIET_NORMALISED_TIME_ATTR = "data-normalised-time"

# CSS pixels, with an explicit intrinsic size so the <svg> never falls
# back to the format's own 300x150 default.
QUIET_DIAL_SIZE = 176
# 176 - 14 - 3 = 78 (SIZE // 2 - STROKE // 2 - CLEARANCE): chosen so the
# radius lands on a whole number, since a rounding tail would make every
# recomputed-from-markup check invent a tolerance to hide it.
QUIET_DIAL_STROKE = 14
# Clear space between the stroke's outer edge and the viewBox edge: a
# stroked arc extends half its stroke width past the nominal radius.
QUIET_DIAL_CLEARANCE = 3
QUIET_DIAL_RADIUS = QUIET_DIAL_SIZE // 2 - QUIET_DIAL_STROKE // 2 - QUIET_DIAL_CLEARANCE

# The three property names value-controls.js's generic pair seam reads
# or writes, decided here since every such name is a server decision.
QUIET_DIAL_PAIR_ATTR = "data-value-pair"
QUIET_DIAL_PAIR_PROPERTY_ATTR = "data-value-pair-property"

# A dict rather than three top-level string constants: a constant whose
# value begins with "--" trips test_i18n.py's untranslated-string scan
# (a leading "--" is not a valid identifier start, so the scanner's
# bare-identifier exclusion never reaches it); a dict value is scanned
# under a separate exclusion that does reach it.
QUIET_DIAL_PAIR_PROPERTIES = {
    "start": "--quiet-start-fraction",
    "end": "--quiet-end-fraction",
    "sweep": "--quiet-sweep-fraction",
}

# Four anchor hours, not twenty-four: the quarter turns are the only
# hours a reader resolves at a glance, and twenty-four labels on this
# ring is illegible at the contract's minimum width. 00 is marked
# because midnight is the case this control's arithmetic exists for.
#
# Each hour is paired with its own modifier class rather than templated
# from one "quiet-dial__hour--%d" constant: test_i18n.py strips a
# literal's format specs before checking whether it is a bare
# identifier, so the templated form would read as untranslated
# user-facing copy and fail that scan.
QUIET_DIAL_LABELLED_HOURS = (
    (0, "quiet-dial__hour--0"),
    (6, "quiet-dial__hour--6"),
    (12, "quiet-dial__hour--12"),
    (18, "quiet-dial__hour--18"),
)

# "23:00 → 07:00 · 8h". No letters of its own (the duration's unit
# comes from layout.duration_text(), which speaks both languages), so
# it needs no catalogue entry.
QUIET_DIAL_READOUT_TEMPLATE = "%s → %s · %s"

# A full turn in degrees, and the quarter turn that moves <circle>'s
# three-o'clock dash origin to twelve o'clock (the same correction
# draw.py's ring_gauge() applies, restated here since this drawing
# additionally rotates by the window's own start).
_QUIET_DIAL_FULL_TURN_DEG = 360.0
_QUIET_DIAL_TWELVE_OCLOCK_DEG = -90.0


def quiet_dial_svg(span):
    """The 24h ring as one `<svg>`: a full-circumference day, plus the
    quiet arc when `span` describes one. Never raises; server-drawn, so
    a scripts-blocked visitor still sees the saved window correctly.

    No arc for `span is None` or a zero-length window: a zero-length
    dash would render as a dot, reading as "a few minutes" rather than
    "no window". `fill="none"`/`stroke-width` are presentation
    attributes, deliberately not stylesheet declarations, since a CSS
    rule would beat them and flatten the derived geometry.
    """
    centre = QUIET_DIAL_SIZE // 2
    shapes = [draw.circle(QUIET_DIAL_DAY_CLASS, centre, centre, QUIET_DIAL_RADIUS, attrs={
        "fill": "none",
        "stroke-width": QUIET_DIAL_STROKE,
    })]
    if span is not None and span.minutes > 0:
        shapes.append(draw.circle(
            QUIET_DIAL_ARC_CLASS, centre, centre, QUIET_DIAL_RADIUS, attrs={
                "fill": "none",
                "stroke-width": QUIET_DIAL_STROKE,
                "stroke-dasharray": draw.unit_circle_dash_array(
                    span.sweep_fraction, QUIET_DIAL_RADIUS),
                # Twelve o'clock plus the window's own start, clockwise —
                # <circle>'s dash origin is three o'clock and grows
                # clockwise already.
                "transform": "rotate(%.4f %d %d)" % (
                    _QUIET_DIAL_TWELVE_OCLOCK_DEG
                    + _QUIET_DIAL_FULL_TURN_DEG * span.start_fraction,
                    centre, centre),
            }))
    return (
        '<svg class="%s" viewBox="0 0 %d %d" width="%d" height="%d" '
        'aria-hidden="true" focusable="false">%s</svg>'
    ) % (
        escape_html(QUIET_DIAL_RING_CLASS), QUIET_DIAL_SIZE, QUIET_DIAL_SIZE,
        QUIET_DIAL_SIZE, QUIET_DIAL_SIZE, "".join(shapes),
    )


def quiet_dial_html(span, handles_html=""):
    """The ring and its four anchor-hour labels, as one positioned block.
    Labels are HTML outside the `<svg>`, not `<text>` inside it, so a
    viewBox never has to contain drawn text, and they stay a constant
    CSS size. `handles_html` renders last (document order is paint
    order). This `<div>` is the pair seam's shared ancestor: the
    handles' fractions publish here, from the same `span` triple
    `quiet_dial_svg()` draws from, so the two geometries never disagree.
    """
    hours_html = "".join(
        '<span class="text-label %s %s" aria-hidden="true">%02d</span>' % (
            escape_html(QUIET_DIAL_HOUR_CLASS), escape_html(modifier_class), hour)
        for hour, modifier_class in QUIET_DIAL_LABELLED_HOURS)
    pair_attrs = ""
    if span is not None:
        end_fraction = (span.start_fraction + span.sweep_fraction) % 1.0
        pair_attrs = (
            ' %s="%s" style="%s: %.6f; %s: %.6f; %s: %.6f;"'
        ) % (
            QUIET_DIAL_PAIR_ATTR, escape_html(QUIET_DIAL_PAIR_PROPERTIES["sweep"]),
            QUIET_DIAL_PAIR_PROPERTIES["start"], span.start_fraction,
            QUIET_DIAL_PAIR_PROPERTIES["end"], end_fraction,
            QUIET_DIAL_PAIR_PROPERTIES["sweep"], span.sweep_fraction,
        )
    return '<div class="%s"%s>%s%s%s</div>' % (
        escape_html(QUIET_DIAL_CLASS), pair_attrs, quiet_dial_svg(span), hours_html, handles_html)


# Everything below renders inside the `.js` gate; the ring, the
# readout, the three presets and both time inputs all survive with
# scripts blocked, and only the dragging is hidden without script.
QUIET_DIAL_HANDLE_LAYER_CLASS = "quiet-dial__handles"
QUIET_DIAL_HANDLE_CLASS = "quiet-dial__handle"
# The box value-controls.js measures the pointer angle against: the
# ring's own square, so the angle is measured about the ring's centre.
QUIET_DIAL_HANDLE_TRACK_CLASS = "quiet-dial__handle-track"

# The steering range, in minutes since local midnight. The maximum is
# 1439, not 1440: 1440 would make 00:00 and "24:00" the same instant
# with two values, and the End key would write a time no
# <input type="time"> accepts.
QUIET_DIAL_HANDLE_MIN = 0
QUIET_DIAL_HANDLE_MAX = QUIET_WINDOW_MINUTES_PER_DAY - 1

# The native <input type="range"> keyboard model: arrows move one step,
# Page keys move ten steps, Home/End go to the two ends. Ten steps of
# 15 minutes is 10.4% of the day, matching a native range control's
# Page-key proportion rather than a fixed value — a per-control page
# size would be a second keyboard model on the second settings page.
QUIET_DIAL_HANDLE_STEP = 15

# The two ends, each with the field it steers and the accessible name
# that says WHICH end it is. aria-valuetext carries the time itself and
# nothing else (layout.VALUE_CONTROL_TEXT_TOKEN alone, no sentence around
# it): a screen reader reading "one thousand three hundred and eighty"
# instead of "23:00" is the whole reason aria-valuetext exists, and
# repeating the label on every arrow press is noise, not information.
QUIET_DIAL_START_LABEL = i18n.msg("display.quiet_hours_start", "Quiet hours start")
QUIET_DIAL_END_LABEL = i18n.msg("display.quiet_hours_end", "Quiet hours end")

# The two native <input type="time"> fields' own visible labels — a
# separate pair from the dial handles' own accessible names above.
QUIET_HOURS_START_FIELD_LABEL = i18n.msg("display.start", "Start")
QUIET_HOURS_END_FIELD_LABEL = i18n.msg("display.end", "End")


def quiet_dial_handle_fraction(minute):
    """`minute` as the 0..1 fraction of a turn the stylesheet positions
    the handle from — deliberately the same formula value-controls.js's
    `paint()` uses, `(value - min) / (max - min)`, rather than the
    `minute / 1440` the arc is drawn from. The server paints the handle
    once and the script repaints it on every step; using a formula that
    only agrees in theory would make it jump imperceptibly on the first
    arrow press and never quite line up with the arc again.
    """
    return minute / float(QUIET_DIAL_HANDLE_MAX)


def quiet_dial_handles_html(start_hm, end_hm):
    """The two drag handles, each in its own `.js`-gated wrapper: a
    real `<button type="button">` (never a bare `<div>`, and never a
    plain `<button>`, which would default to form submit on Enter).

    Driven from the two native inputs, never from state of its own, so
    the existing presets already move the handles with no code of
    their own. No handle for an end that does not parse. No minimum
    separation between the two ends (a zero-length window is a real
    state); z-order is document order, so the end handle wins a
    pointer-down where they overlap, and moving it separates the pair.
    """
    handles = []
    for value, field, label, pair_property in (
            (start_hm, "quiet_hours_start", QUIET_DIAL_START_LABEL,
             QUIET_DIAL_PAIR_PROPERTIES["start"]),
            (end_hm, "quiet_hours_end", QUIET_DIAL_END_LABEL,
             QUIET_DIAL_PAIR_PROPERTIES["end"])):
        minute = quiet_window_minute_of_day(value)
        if minute is None:
            continue
        handles.append((
            '<div class="value-control %s %s" %s %s="%s" %s="%s" %s="%d" %s="%d" %s="%d"'
            ' %s="angular" %s="%s" %s="%s" %s="%s" style="--value-fraction: %.6f">'
            '<span class="value-control__track %s" %s></span>'
            '<button type="button" class="value-control__handle control-hit-area %s" %s'
            ' role="slider" aria-valuemin="%d" aria-valuemax="%d" aria-valuenow="%d"'
            ' aria-valuetext="%s" aria-label="%s"></button>'
            "</div>"
        ) % (
            escape_html(QUIET_DIAL_HANDLE_LAYER_CLASS), escape_html(layout.JS_GATE_CLASS),
            layout.VALUE_CONTROL_ATTR,
            layout.VALUE_CONTROL_FIELD_ATTR, escape_html(field),
            layout.VALUE_CONTROL_FORM_ATTR, escape_html(SETTINGS_FORM_ID),
            layout.VALUE_CONTROL_MIN_ATTR, QUIET_DIAL_HANDLE_MIN,
            layout.VALUE_CONTROL_MAX_ATTR, QUIET_DIAL_HANDLE_MAX,
            layout.VALUE_CONTROL_STEP_ATTR, QUIET_DIAL_HANDLE_STEP,
            layout.VALUE_CONTROL_GEOMETRY_ATTR,
            layout.VALUE_CONTROL_FORMAT_ATTR, escape_html(layout.VALUE_CONTROL_FORMAT_CLOCK),
            layout.VALUE_CONTROL_TEXT_ATTR, escape_html(layout.VALUE_CONTROL_TEXT_TOKEN),
            # Names which of quiet_dial_html()'s ancestor properties
            # this handle publishes its fraction under; value-controls.js
            # finds that ancestor via ancestorWith().
            QUIET_DIAL_PAIR_PROPERTY_ATTR, escape_html(pair_property),
            quiet_dial_handle_fraction(minute),
            escape_html(QUIET_DIAL_HANDLE_TRACK_CLASS), layout.VALUE_CONTROL_TRACK_ATTR,
            escape_html(QUIET_DIAL_HANDLE_CLASS), layout.VALUE_CONTROL_HANDLE_ATTR,
            QUIET_DIAL_HANDLE_MIN, QUIET_DIAL_HANDLE_MAX, minute,
            escape_html(value), escape_html(i18n.t(label)),
        ))
    return "".join(handles)


# layout.DURATION_ATTRS' four English wordings, in the same s/m/h/d
# order, zipped against that tuple below so an attribute name and its
# translated wording are always written together.
_QUIET_DIAL_DURATION_TEXTS = (
    layout.DURATION_SECONDS_TEXT, layout.DURATION_MINUTES_TEXT,
    layout.DURATION_HOURS_TEXT, layout.DURATION_DAYS_TEXT,
)


def quiet_dial_readout_html(start_hm, end_hm, span):
    """"23:00 → 07:00 · 8h" — the window in words, or "" when `span` is
    None. `aria-hidden="true"`, not a live region: dragging fires
    continuously, and the focused handle's own `aria-valuetext` is
    already the debounced announcement path.

    The duration comes from `layout.duration_text()`, this app's one
    length-of-time ladder, coarse by construction (a 90-minute window
    reads "1h"). Three children, not one text node: the two endpoint
    spans carry the `data-value-readout` seam so `value-controls.js`
    can substitute "HH:MM" client-side; the duration span carries all
    four `layout.DURATION_ATTRS` translated wordings, so the client
    substitutes a quantity into the right bucket with no language logic
    of its own.
    """
    if span is None:
        return ""
    duration_attrs_html = "".join(
        ' %s="%s"' % (attr, escape_html(i18n.t(text)))
        for attr, text in zip(layout.DURATION_ATTRS, _QUIET_DIAL_DURATION_TEXTS))
    return (
        '<p class="time-value %s" aria-hidden="true">'
        '<span %s="quiet_hours_start" %s="%s" %s="%s">%s</span>'
        ' → '
        '<span %s="quiet_hours_end" %s="%s" %s="%s">%s</span>'
        ' · '
        '<span %s="quiet_hours_start" %s="%d"%s>%s</span>'
        "</p>"
    ) % (
        escape_html(QUIET_DIAL_READOUT_CLASS),
        layout.VALUE_CONTROL_READOUT_ATTR,
        layout.VALUE_CONTROL_READOUT_FORMAT_ATTR, escape_html(layout.VALUE_CONTROL_FORMAT_CLOCK),
        layout.VALUE_CONTROL_READOUT_TEXT_ATTR,
        escape_html(layout.VALUE_CONTROL_TEXT_TOKEN), escape_html(start_hm),
        layout.VALUE_CONTROL_READOUT_ATTR,
        layout.VALUE_CONTROL_READOUT_FORMAT_ATTR, escape_html(layout.VALUE_CONTROL_FORMAT_CLOCK),
        layout.VALUE_CONTROL_READOUT_TEXT_ATTR,
        escape_html(layout.VALUE_CONTROL_TEXT_TOKEN), escape_html(end_hm),
        layout.VALUE_CONTROL_READOUT_ATTR,
        layout.VALUE_CONTROL_READOUT_BASE_ATTR, quiet_window_minute_of_day(start_hm),
        duration_attrs_html,
        escape_html(layout.duration_text(span.minutes * 60)),
    )


def quiet_hours_group(current_start, current_end, errors=None, submitted=None):
    """The Quiet hours settings card: a sibling of the settings form,
    never a literal descendant; both time inputs submit via `form=`.

    Neither time input is ever `disabled`: they stay interactive
    whether or not Quiet hours is on, since the Frame strip is the only
    on/off control. The three presets are client-side-only
    `type="button"` elements dirty-state.js writes into the two time
    fields, inert with no script. `errors`/`submitted` repopulate both
    controls; the server-side HH:MM gate in `handle_post()` is the real
    validation.
    """
    # The group's single hint links to both time inputs (there is no
    # separate per-field hint for Start vs End).
    effective_start = _submitted_or_current(submitted, "quiet_hours_start", current_start)
    start_error_attrs = _field_error_attrs(
        errors, "quiet_hours_start", "quiet-hours-start", hint_id=QUIET_HOURS_SECTION_CAPTION_ID)
    start_error_html = _field_error_html(errors, "quiet_hours_start", "quiet-hours-start")

    effective_end = _submitted_or_current(submitted, "quiet_hours_end", current_end)
    end_error_attrs = _field_error_attrs(
        errors, "quiet_hours_end", "quiet-hours-end", hint_id=QUIET_HOURS_SECTION_CAPTION_ID)
    end_error_html = _field_error_html(errors, "quiet_hours_end", "quiet-hours-end")

    # The preset row is a segmented control with no selected state:
    # these buttons are momentary actions that write into the time
    # fields, not a persistent choice.
    preset_row_html = (
        '<div class="%s">'
        '<button type="button" %s data-preset-start="%s" data-preset-end="%s">%s</button>'
        '<button type="button" %s data-preset-start="%s" data-preset-end="%s">%s</button>'
        '<button type="button" %s data-preset-enabled="0">%s</button>'
        "</div>"
    ) % (
        QUIET_PRESET_ROW_CLASS,
        QUIET_HOURS_PRESET_ATTR,
        escape_html(QUIET_HOURS_PRESET_NIGHT_START), escape_html(QUIET_HOURS_PRESET_NIGHT_END),
        escape_html(i18n.t(QUIET_HOURS_PRESET_NIGHT_LABEL)),
        QUIET_HOURS_PRESET_ATTR,
        escape_html(QUIET_HOURS_PRESET_WORKDAY_START), escape_html(QUIET_HOURS_PRESET_WORKDAY_END),
        escape_html(i18n.t(QUIET_HOURS_PRESET_WORKDAY_LABEL)),
        QUIET_HOURS_PRESET_ATTR,
        escape_html(i18n.t(QUIET_HOURS_PRESET_ALWAYS_ON_LABEL)),
    )

    # `<html lang>` already carries the site's language, but a native
    # time control formats itself from the browser's own locale, not
    # the document's — this attribute is the standards-level request;
    # `_normalised_time_html()` is the fallback that holds when a
    # browser ignores it.
    #
    # The presets and the native time fields are the primary controls and
    # come first; the ring is a secondary picture of the saved window and
    # renders after them.
    #
    # Drawn from the same effective values the two inputs are populated
    # from, never from `current_start`/`current_end` directly, so on a
    # rejected save the arc shows what was submitted, not what is
    # stored.
    dial_span = quiet_window_span(effective_start, effective_end)
    dial_html = quiet_dial_html(
        dial_span, quiet_dial_handles_html(effective_start, effective_end))
    readout_html = quiet_dial_readout_html(effective_start, effective_end, dial_span)

    site_lang = prefs.current_lang()
    caption_html = i18n.t(QUIET_HOURS_SECTION_CAPTION)
    # Each field gets its own unclassed grid cell holding its label and
    # its own error paragraph together, so an error never displaces its
    # sibling column under the two-column grid.
    return (
        '<div class="theme-status" %s="%s">'
        '<h2 class="text-heading" id="%s">%s</h2>'
        '<p class="text-label section-caption" id="%s">%s</p>'
        "%s"
        '<div class="%s">'
        '<div><label>%s <input type="time" name="quiet_hours_start" value="%s" required'
        ' lang="%s" form="%s"%s>%s</label>%s</div>'
        '<div><label>%s <input type="time" name="quiet_hours_end" value="%s" required'
        ' lang="%s" form="%s"%s>%s</label>%s</div>'
        "</div>"
        '<div class="quiet-dial-summary">%s%s</div>'
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(i18n.t(QUIET_HOURS_SECTION_HEADING)),
        escape_html(QUIET_HOURS_GROUP_HEADING_ID),
        escape_html(i18n.t(QUIET_HOURS_SECTION_HEADING)),
        escape_html(QUIET_HOURS_SECTION_CAPTION_ID),
        escape_html(caption_html),
        preset_row_html,
        QUIET_TIMES_ROW_CLASS,
        escape_html(i18n.t(QUIET_HOURS_START_FIELD_LABEL)),
        escape_html(effective_start), escape_html(site_lang), SETTINGS_FORM_ID, start_error_attrs,
        _normalised_time_html(effective_start),
        start_error_html,
        escape_html(i18n.t(QUIET_HOURS_END_FIELD_LABEL)),
        escape_html(effective_end), escape_html(site_lang), SETTINGS_FORM_ID, end_error_attrs,
        _normalised_time_html(effective_end),
        end_error_html,
        dial_html, readout_html,
    )
