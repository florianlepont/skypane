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
from companion.ui_base import validation_attrs

PAIR_FRAME_ROUTE = "/pair-frame"
CODE_FIELD = fleet_page.CODE_FIELD
# The flash key the paired frame's Home resolves (companion/flash.py).
FLASH_FRAME_PAIRED = "frame_paired"

PAIR_TITLE = i18n.msg("pair_frame.add_a_frame", "Add a frame")
PAIR_PURPOSE = i18n.msg(
    "pair_frame.enter_the_code_shown_on_your_frame_s_screen",
    "Enter the code shown on your frame's screen. The frame will be yours.")
_CODE_LABEL = i18n.msg("pair_frame.pairing_code", "Pairing code")
_CODE_HELP = i18n.msg(
    "pair_frame.the_code_stays_valid_for_about_35_minutes",
    "The code stays valid for about 35 minutes; a new one then appears on the frame.")
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


def _code_field(view):
    attrs, error = "", ""
    if view.code_error:
        error_id = "pair-code-error"
        attrs = ' aria-invalid="true" aria-describedby="%s"' % error_id
        error = '<p class="field-error" id="%s">%s</p>' % (error_id, _esc(view.code_error))
    return (
        '<div class="modal__field"><label for="pair-code">%s</label>'
        '<input type="text" id="pair-code" name="%s" class="mono" autocomplete="off" '
        'data-1p-ignore data-lpignore="true" data-bwignore="true" data-form-type="other" '
        'autocapitalize="characters" spellcheck="false" inputmode="text" '
        'maxlength="12" placeholder="XXXX-XXXX" value="%s" required%s autofocus%s>%s'
        '<p class="text-label">%s</p></div>') % (
            _t(_CODE_LABEL), CODE_FIELD, _esc(view.code_value), validation_attrs("text"), attrs, error,
            _t(_CODE_HELP))


def render(view=PairView()):
    """The Add a frame page body."""
    form = (
        '<form class="%s" method="post" action="%s">%s%s%s'
        '<div class="pair-form__actions"><button type="submit">%s</button>'
        '<a class="pair-form__cancel" href="/account">%s</a></div></form>') % (
            FORM_CLASS, PAIR_FRAME_ROUTE, ui_components.csrf_field(),
            view.toast_html, _code_field(view), _t(_SUBMIT), _t(_CANCEL))
    return (
        layout.page_header(i18n.t(PAIR_TITLE), purpose=i18n.t(PAIR_PURPOSE))
        + '<section class="page-section">%s</section>' % form)
