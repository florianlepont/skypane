"""The Diagnostic LED settings group: the Device page's LED on/off card
plus its own Frame-strip quick-switch form, and the runway diagram route
prefix.
"""
from companion import device_scope, i18n
from companion.layout import escape_html
import companion.layout as layout

from companion.settings.form import DIRTY_SECTION_ATTR, _field_error_html


RUNWAY_IMAGE_ROUTE_PREFIX = "/runway-image/"

LED_SECTION_CAPTION = i18n.msg(
    "display.lights_briefly_while_the_frame_checks_for_flights",
    "Lights briefly while the frame checks for new flight data.")

# Stable DOM id for the hint paragraph an aria-describedby points at.
LED_SECTION_CAPTION_ID = "led-caption"

LED_SECTION_HEADING = i18n.msg("display.diagnostic_led", "Diagnostic LED")


def led_group(current_led_enabled, errors=None, submitted=None, next_wake_clock=None):
    """The Diagnostic LED settings group: a sibling of the other
    groups in the merged settings form, with no `<fieldset>`/`<legend>`
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
        '<form method="post" action="%s" id="%s" '
        'class="quick-action__form" data-quick-switch>'
        '<input type="hidden" name="state" value="%s">'
        '<input type="hidden" name="return_to" value="%s">'
        "</form>"
    ) % (
        escape_html(device_scope.scoped("/quick/led", "POST")),
        escape_html(QUICK_LED_FORM_ID),
        escape_html(next_state),
        escape_html(layout.DEVICE_ROUTE),
    )
