# SPDX-License-Identifier: AGPL-3.0-only
"""The page where a signed-in person adds their own frame in two steps (an
optional name, then the pairing code shown on the frame's screen), and the entry points to it (the
primary action of the empty My frames state and the secondary link under a
list of frames).

Pure markup: it reads nothing but its arguments. The typed code is
re-rendered only into the input of the form (a lockout response, or the next
showing after a refusal) and is
capped, as is the typed name; neither appears in a link, a flash or an attribute other than the
input's value. Only an administrator's view carries an Owner field (the
other people's page has none: their frame always belongs to them).
"""
from typing import NamedTuple

from companion import i18n, layout, ui_components
from companion.pages import fleet_page, frame_name_page
from companion.ui_base import icon_html, validation_attrs

PAIR_FRAME_ROUTE = "/pair-frame"
CODE_FIELD = fleet_page.CODE_FIELD
OWNER_FIELD = fleet_page.OWNER_FIELD
NAME_FIELD = "frame_name"
MAX_NAME_CHARS = frame_name_page.MAX_NAME_CHARS
# The flash key the paired frame's Home resolves (companion/flash.py).
FLASH_FRAME_PAIRED = "frame_paired"

PAIR_TITLE = i18n.msg("pair_frame.add_a_frame", "Add a frame")
_STEP_NAME = i18n.msg("pair_frame.step_1_name_it", "Step 1: name it")
_STEP_CODE = i18n.msg(
    "pair_frame.step_2_enter_its_pairing_code", "Step 2: enter its pairing code")
_NAME_HELP = i18n.msg(
    "pair_frame.optional_you_can_change_it_later", "Optional. You can change it later.")
_NO_CODE_TITLE = i18n.msg("pair_frame.no_code_on_screen", "No code on screen?")
_CODE_LABEL = i18n.msg("pair_frame.pairing_code", "Pairing code")
_CODE_HELP = i18n.msg(
    "pair_frame.the_code_stays_valid_for_about_35_minutes",
    "Valid for 35 minutes.")
_NO_CODE_HELP = i18n.msg(
    "pair_frame.if_your_frame_shows_no_code_press_its_reset_button",
    "Press its Reset button.")
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
    """The state of a refused submission: the (capped) typed code and name, the
    docked refusal or lockout toast, the code field's error and the name
    field's error. `owners` is
    the administrator's (id, label) Owner choices (empty: no Owner field),
    `owner_selected` the chosen id and `owner_error` the Owner field's error."""
    code_value: str = ""
    toast_html: str = ""
    code_error: str = ""
    owners: tuple = ()
    owner_selected: str = ""
    owner_error: str = ""
    name_value: str = ""
    name_error: str = ""


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


def _name_field(view):
    attrs, error = "", ""
    if view.name_error:
        attrs = ' aria-invalid="true" aria-describedby="pair-name-error"'
        error = '<p class="field-error" id="pair-name-error">%s</p>' % _esc(view.name_error)
    return (
        '<div class="modal__field"><label for="pair-name">%s</label>'
        '<input type="text" id="pair-name" name="%s" autocomplete="off" maxlength="%d" '
        'value="%s"%s>%s<p class="text-label">%s</p></div>') % (
            _t(frame_name_page.LABEL), NAME_FIELD, MAX_NAME_CHARS,
            _esc(view.name_value[:MAX_NAME_CHARS]), attrs, error, _t(_NAME_HELP))


def _step(title, body):
    return '<li class="pair-step"><h2 class="pair-step__title">%s</h2>%s</li>' % (
        _t(title), body)


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


def _owner_field(view):
    """The administrator's Owner choice; "" for everyone else."""
    if not view.owners:
        return ""
    attrs, error = "", ""
    if view.owner_error:
        attrs = ' aria-invalid="true" aria-describedby="pair-owner-error"'
        error = '<p class="field-error" id="pair-owner-error">%s</p>' % _esc(view.owner_error)
    options = "".join(
        '<option value="%s"%s>%s</option>' % (
            _esc(value), " selected" if value == view.owner_selected else "", _esc(label))
        for value, label in view.owners)
    return (
        '<div class="modal__field"><label for="pair-owner">%s</label>'
        '<select id="pair-owner" name="%s" required%s>%s</select>%s</div>') % (
            _t(fleet_page.PAIR_OWNER_LABEL), OWNER_FIELD, attrs, options, error)


def render(view=PairView()):
    """The Add a frame page body."""
    # One card: the two steps, code field with its validity line and
    # the actions, then a tinted footer carrying the Reset hint (left out after
    # a refusal: the frame did show a code, it was typed wrong).
    footer = "" if view.code_error else (
        '<div class="pair-card__help">%s<p class="text-label"><b>%s</b><br>%s</p></div>'
        % (icon_html("icon-info", size=20), _t(_NO_CODE_TITLE), _t(_NO_CODE_HELP)))
    steps = _step(_STEP_NAME, _name_field(view)) + _step(
        _STEP_CODE, view.toast_html + _code_field(view) + _owner_field(view))
    form = (
        '<form class="%s pair-card reveal" method="post" action="%s">%s'
        '<div class="pair-card__main"><ol class="pair-steps">%s</ol>'
        '<div class="pair-form__actions"><button type="submit">%s</button>'
        '<a class="pair-form__cancel" href="/account">%s</a></div></div>%s</form>') % (
            FORM_CLASS, PAIR_FRAME_ROUTE, ui_components.csrf_field(),
            steps, _t(_SUBMIT), _t(_CANCEL), footer)
    return layout.page_header(i18n.t(PAIR_TITLE)) + form
