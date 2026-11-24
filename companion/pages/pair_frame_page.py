"""The page where a signed-in person adds their own frame by typing the
pairing code shown on the frame's screen, and the entry points to it (the
primary action of the empty My frames state and the secondary link under a
list of frames).

Pure markup: it reads nothing but its arguments. The typed code is
re-rendered only into the input of the form (a lockout response, or the next
showing after a refusal) and is
capped; it never appears in a link, a flash or an attribute other than the
input's value. The page has no owner field: the frame always belongs to the
person who submits the form.
"""
from typing import NamedTuple

from companion import i18n, layout, ui_components
from companion.pages import fleet_page
from companion.ui_base import icon_html, validation_attrs

PAIR_FRAME_ROUTE = "/pair-frame"
CODE_FIELD = fleet_page.CODE_FIELD
# The flash key the paired frame's Home resolves (companion/flash.py).
FLASH_FRAME_PAIRED = "frame_paired"

PAIR_TITLE = i18n.msg("pair_frame.add_a_frame", "Add a frame")
_CARD_HEADING = i18n.msg(
    "pair_frame.enter_the_code_shown_by_the_frame", "Enter the code shown by the frame")
_CARD_INSTRUCTION = i18n.msg(
    "pair_frame.turn_the_frame_on_it_shows_an_8_character_code",
    "Turn the frame on: it shows an 8-character code.")
_NO_CODE_TITLE = i18n.msg("pair_frame.no_code_on_screen", "No code on screen?")
_CODE_LABEL = i18n.msg("pair_frame.pairing_code", "Pairing code")
_CODE_HELP = i18n.msg(
    "pair_frame.the_code_stays_valid_for_about_35_minutes",
    "The code stays valid for about 35 minutes; a new one then appears on the frame.")
_NO_CODE_HELP = i18n.msg(
    "pair_frame.if_your_frame_shows_no_code_press_its_reset_button",
    "If your frame shows no code, press its Reset button.")
_SUBMIT = i18n.msg("pair_frame.add_frame", "Add frame")
_CANCEL = i18n.msg("pair_frame.cancel", "Cancel")

FLASH_FRAME_PAIRED_TEXT = i18n.msg(
    "pair_frame.frame_added_it_shows_its_first_image_at_the_next_update",
    "Frame added — It shows its first image at the next update.")

EMPTY_HEADING = i18n.msg(
    "pair_frame.your_frames_will_appear_here", "Your frames will appear here")
_ADD_YOUR_FRAME = i18n.msg("pair_frame.add_your_frame", "Add your frame")
EMPTY_BODY = i18n.msg(
    "pair_frame.the_code_is_shown_on_your_frame_s_screen",
    "The pairing code is shown on your frame's screen.")
ADD_LINK_TEXT = i18n.msg("pair_frame.add_a_frame_link", "Add a frame")

FORM_CLASS = "pair-form"
ADD_LINK_CLASS = "pair-link"


class PairView(NamedTuple):
    """The state of a refused submission: the (capped) typed code, the
    docked refusal or lockout toast and the code field's error."""
    code_value: str = ""
    toast_html: str = ""
    code_error: str = ""


def _esc(value):
    return layout.escape_html(value)


def _t(message):
    return _esc(i18n.t(message))


def primary_link_html():
    """The one primary action of the empty state: a plain link, so it works
    without script."""
    return '<a class="%s %s--primary" href="%s">%s</a>' % (
        ADD_LINK_CLASS, ADD_LINK_CLASS, PAIR_FRAME_ROUTE, _t(_ADD_YOUR_FRAME))


def empty_state_html():
    """The calm first-sign-in state: a heading, one hint line and one
    primary action."""
    return (
        ui_components.empty_state(i18n.t(EMPTY_HEADING), i18n.t(EMPTY_BODY), compact=True)
        + '<p class="pair-actions">%s</p>' % primary_link_html())


# A circled exclamation mark: the refusal alert's own icon (the shared sprite
# has the toast cross and the plain warning triangle only).
_ALERT_ICON = (
    '<svg class="pair-alert__icon" width="20" height="20" viewBox="0 0 20 20" fill="none" '
    'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true">'
    '<circle cx="10" cy="10" r="7.5"/><path d="M10 6v5M10 13.6v.01"/></svg>')


def _refusal_html(error_id, message):
    """The refused-code alert: the sentence in bold under an error icon, the
    validity line under it, in one tinted box the field points at."""
    return (
        '<div class="pair-alert" id="%s" role="alert">%s<div class="pair-alert__text">'
        '<p class="field-error pair-alert__title">%s</p><p class="text-label">%s</p></div></div>'
    ) % (error_id, _ALERT_ICON, _esc(message), _t(_CODE_HELP))


def _code_field(view):
    attrs, below = "", '<p class="text-label">%s</p>' % _t(_CODE_HELP)
    if view.code_error:
        error_id = "pair-code-error"
        attrs = ' aria-invalid="true" aria-describedby="%s"' % error_id
        below = _refusal_html(error_id, view.code_error)
    return (
        '<div class="modal__field"><label for="pair-code">%s</label>'
        '<input type="text" id="pair-code" name="%s" class="mono" autocomplete="off" '
        'data-1p-ignore data-lpignore="true" data-bwignore="true" data-form-type="other" '
        'autocapitalize="characters" spellcheck="false" inputmode="text" '
        'maxlength="12" placeholder="XXXX-XXXX" value="%s" required%s autofocus%s>%s</div>') % (
            _t(_CODE_LABEL), CODE_FIELD, _esc(view.code_value), validation_attrs("text"), attrs, below)


def render(view=PairView()):
    """The Add a frame page body."""
    # One card: heading, instruction, code field with its validity line and
    # the actions, then a tinted footer carrying the Reset hint (left out after
    # a refusal: the frame did show a code, it was typed wrong).
    footer = "" if view.code_error else (
        '<div class="pair-card__help">%s<p class="text-label"><b>%s</b><br>%s</p></div>'
        % (icon_html("icon-info", size=20), _t(_NO_CODE_TITLE), _t(_NO_CODE_HELP)))
    form = (
        '<form class="%s pair-card" method="post" action="%s">%s'
        '<div class="pair-card__main"><h2 class="text-heading pair-card__heading">%s</h2>'
        '<p class="text-label pair-card__lead">%s</p>%s%s'
        '<div class="pair-form__actions"><button type="submit">%s</button>'
        '<a class="pair-form__cancel" href="/account">%s</a></div></div>%s</form>') % (
            FORM_CLASS, PAIR_FRAME_ROUTE, ui_components.csrf_field(),
            _t(_CARD_HEADING), _t(_CARD_INSTRUCTION), view.toast_html, _code_field(view),
            _t(_SUBMIT), _t(_CANCEL), footer)
    return (
        layout.page_header(i18n.t(PAIR_TITLE))
        + '<section class="page-section">%s</section>' % form)
