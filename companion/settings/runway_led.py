"""The Runway and Diagnostic LED settings groups: the Display page's
Runway selector card, and the Device page's LED on/off card plus its
own Frame-strip quick-switch form.
"""
from companion import i18n
from companion.layout import escape_html
import companion.layout as layout
from server import device_config

from companion.settings.form import (
    CURRENT_BADGE_ATTR, CURRENT_BADGE_LABEL, DIRTY_SECTION_ATTR,
    SELECTED_LABEL, SETTINGS_FORM_ID, _describedby_attr, _field_error_html,
    _submitted_or_current)


RUNWAY_IMAGE_ROUTE_PREFIX = "/runway-image/"
RUNWAY_IMAGE_ALT_TEMPLATE = i18n.msg("display.airport_diagram_for", "Airport diagram for %s")

RUNWAY_SECTION_CAPTION = i18n.msg(
    "display.which_orly_runway_the_device_watches", "Which Orly runway the device watches.")
LED_SECTION_CAPTION = i18n.msg(
    "display.lights_briefly_while_the_frame_checks_for_flights",
    "Lights briefly while the frame checks for new flight data.")

# server.device_config.runway_label()'s registry text, wrapped as a
# stable-id Message at this display site — the SAME ids
# companion/pages/history_page.py's own `_RUNWAY_LABEL_MESSAGES` already
# declares (msg() is idempotent on a repeat (id, english) pair).
_RUNWAY_LABEL_MESSAGES = {
    "Runway 3 (07/25)": i18n.msg("registry.runway_3_07_25", "Runway 3 (07/25)"),
    "Runway 4 (06/24)": i18n.msg("registry.runway_4_06_24", "Runway 4 (06/24)"),
    "Runway 2 (02/20)": i18n.msg("registry.runway_2_02_20", "Runway 2 (02/20)"),
}

# "Runway" is used twice below: the card's own dirty-section heading and
# the radiogroup's aria-labelledby heading. Declared once so both call
# sites share the same Message.
RUNWAY_HEADING_TEXT = i18n.msg("display.runway", "Runway")

# Stable DOM ids for the group headings a radiogroup's aria-labelledby
# points at, and for each hint paragraph an aria-describedby points at.
# Only the groups that gain role="radiogroup" (the two theme chip grids
# and the runway row) get a *_GROUP_HEADING_ID; every hint gets a
# *_CAPTION_ID/*_HINT_ID regardless, since a hint can describe a
# single-control field too.
RUNWAY_SECTION_CAPTION_ID = "runway-caption"
RUNWAY_GROUP_HEADING_ID = "runway-group-heading"
LED_SECTION_CAPTION_ID = "led-caption"

LED_SECTION_HEADING = i18n.msg("display.diagnostic_led", "Diagnostic LED")


def runway_fieldset(
        current_runway_id, images_available=(), errors=None, submitted=None):
    """One selectable `.runway-card` per `device_config.RUNWAYS` entry.
    The entire card (`<label>`) is the hit target, wrapping a
    visually-hidden (never `display:none`) native radio so keyboard/
    no-JS selection still works. An `<img>` renders when `runway_id` is
    a member of `images_available`.

    Named by an `<h2>` rather than a `<legend>`, since a `<legend>`
    outside a `<fieldset>` has no accessible group semantics; the
    `.runway-row` wrapper carries `role="radiogroup"` instead.
    `errors`/`submitted` repopulate the selected card on a rejected
    save. Each radio carries an explicit `form=` attribute so the group
    keeps posting even when rendered as a form sibling.
    """
    effective_runway_id = _submitted_or_current(
        submitted, "tracked_runway", current_runway_id)
    cards = []
    for runway_id in device_config.RUNWAY_IDS:
        selected = runway_id == effective_runway_id
        checked = " checked" if selected else ""
        card_class = (
            "runway-card runway-card--selected" if selected else "runway-card")
        # Emitted only on the saved card.
        current_attr_html = (
            ' %s="%s"' % (CURRENT_BADGE_ATTR, escape_html(i18n.t(CURRENT_BADGE_LABEL)))
            if selected else "")
        raw_label = device_config.runway_label(runway_id)
        _runway_message = _RUNWAY_LABEL_MESSAGES.get(raw_label)
        label = i18n.t(_runway_message) if _runway_message is not None else raw_label
        escaped_id = escape_html(runway_id)
        image_html = ""
        if runway_id in images_available:
            image_html = (
                '<img class="runway-card__image" src="%s%s.png" alt="%s">'
                % (
                    RUNWAY_IMAGE_ROUTE_PREFIX, escaped_id,
                    escape_html(i18n.t(RUNWAY_IMAGE_ALT_TEMPLATE) % label),
                )
            )
        cards.append(
            '<label class="%s"%s>'
            '<input type="radio" name="tracked_runway" value="%s" class="visually-hidden" '
            'form="%s"%s>'
            '<span class="runway-card__number">%s</span>'
            "%s"
            '<span class="runway-card__check">%s<span class="visually-hidden">%s</span></span>'
            "</label>"
            % (
                card_class, current_attr_html,
                escaped_id, SETTINGS_FORM_ID, checked,
                escape_html(label),
                image_html, layout.icon_html("icon-check"),
                escape_html(i18n.t(SELECTED_LABEL)),
            )
        )
    runway_error_html = _field_error_html(errors, "tracked_runway", "tracked-runway")
    row_attr = 'role="radiogroup" aria-labelledby="%s"%s' % (
        escape_html(RUNWAY_GROUP_HEADING_ID), _describedby_attr(RUNWAY_SECTION_CAPTION_ID))
    return (
        '<div class="theme-status" %s="%s">'
        '<h2 class="text-heading" id="%s">%s</h2>'
        '<p class="text-label section-caption" id="%s">%s</p>'
        '<div class="runway-row" %s>%s</div>'
        "%s"
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(i18n.t(RUNWAY_HEADING_TEXT)),
        escape_html(RUNWAY_GROUP_HEADING_ID),
        escape_html(i18n.t(RUNWAY_HEADING_TEXT)),
        escape_html(RUNWAY_SECTION_CAPTION_ID),
        escape_html(i18n.t(RUNWAY_SECTION_CAPTION)),
        row_attr,
        "".join(cards),
        runway_error_html,
    )


def led_group(current_led_enabled, errors=None, submitted=None, next_wake_clock=None):
    """The Diagnostic LED settings group: a sibling of Theme and
    Runway in the merged settings form, with no `<fieldset>`/`<legend>`
    (named by an `<h2>` instead) and no `role="radiogroup"` (a single
    checkbox gets `aria-describedby` instead).

    The `<label>` carries `class="settings-checkbox"`: unclassed, it
    would fall through to the global `input, select` rule and paint an
    oversized filled box. `errors`/`submitted` repopulate this
    checkbox's `checked` state from a rejected save.
    """
    is_on = current_led_enabled is True
    error_html = _field_error_html(errors, "led_enabled", "led-enabled")
    # Hint-then-error order: the switch's own state span, then the
    # group's caption hint, then the error anchor when there is one.
    described_by = QUICK_LED_STATE_ID + " " + LED_SECTION_CAPTION_ID
    if errors and errors.get("led_enabled"):
        described_by = described_by + " led-enabled-error"
    return (
        '<div class="theme-status" %s="%s" %s>'
        '<h2 class="text-heading" id="%s">%s</h2>'
        '<p class="text-label section-caption" id="%s">%s</p>'
        '<div class="settings-switch-row">%s%s</div>'
        "%s"
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(i18n.t(LED_SECTION_HEADING)),
        layout.QUICK_SWITCH_REGION_ATTR,
        escape_html(QUICK_LED_LABEL_ID), escape_html(i18n.t(LED_SECTION_HEADING)),
        escape_html(LED_SECTION_CAPTION_ID),
        escape_html(i18n.t(LED_SECTION_CAPTION)),
        layout.quick_switch_state_html(
            QUICK_LED_STATE_ID,
            i18n.t(layout.QUICK_ACTION_ON_TEXT), i18n.t(layout.QUICK_ACTION_OFF_TEXT), is_on),
        layout.quick_switch_html(
            "", "", is_on, QUICK_LED_LABEL_ID,
            described_by, form_id=QUICK_LED_FORM_ID),
        error_html,
    )


QUICK_LED_FORM_ID = "quick-led"
QUICK_LED_LABEL_ID = "quick-switch-led-label"
QUICK_LED_STATE_ID = "quick-switch-led-state"


def quick_led_form_html(current_led_enabled):
    """The Diagnostic LED switch's own empty `<form>`, a sibling of the
    settings form: `led_group()` renders inside it, and a `<form>` can
    never nest inside another, so the button reaches this element
    across the DOM via `form="{QUICK_LED_FORM_ID}"`.

    The posted `state` is the opposite of the stored one, so a press
    with scripts blocked switches the LED rather than re-asserting its
    current state; `quick-switch.js` keeps that field inverted after an
    optimistic flip. `data-quick-switch` is the handshake both
    `dirty-state.js` and `quick-switch.js` key on.
    """
    next_state = (
        layout.QUICK_STATE_OFF if current_led_enabled is True else layout.QUICK_STATE_ON)
    return (
        '<form method="post" action="/quick/led" id="%s" '
        'class="quick-action__form" data-quick-switch>'
        '<input type="hidden" name="state" value="%s">'
        '<input type="hidden" name="return_to" value="%s">'
        "</form>"
    ) % (
        escape_html(QUICK_LED_FORM_ID),
        escape_html(next_state),
        escape_html(layout.DEVICE_ROUTE),
    )
