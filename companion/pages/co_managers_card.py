"""Frame co-management: the three POST route paths, the form field names, the
flash keys and their texts, and the pure markup of the Co-managers card on the
frame's Home page, so the handlers, the card and the flash registry all read
one definition.

The card takes a `CardView` and reads nothing else. It has three shapes: the
manage shape (owner or administrator: Add and per-row Remove), the read-only
shape (a co-manager: the list and a two-step Leave) and, outside this module,
no card at all. The shape follows `can_manage`, `is_admin_viewer` and
`viewer_is_member` only. The invited-user list reaches the page only through
`candidates`, which the view builder fills for an administrator alone.
"""
from typing import NamedTuple

from companion import device_scope, i18n
from companion.ui_base import escape_html

ADD_ROUTE = "/co-managers/add"
REMOVE_ROUTE = "/co-managers/remove"
LEAVE_ROUTE = "/co-managers/leave"

FIELD_EMAIL = "email"
FIELD_USER_ID = "user_id"

FLASH_ADDED = "co_manager_added"
FLASH_REMOVED = "co_manager_removed"
FLASH_LEFT = "co_manager_left"
FLASH_ADD_REFUSED = "co_manager_add_refused"
FLASH_FAILED = "co_manager_failed"
FLASH_LEAVE_NOOP = "co_manager_leave_noop"

# None of these texts carries a placeholder: the typed address, an id or a
# frame name never reaches a flash.
FLASH_ADDED_TEXT = i18n.msg(
    "co_managers.flash_added",
    "Co-manager added — they can now manage this frame.")
FLASH_REMOVED_TEXT = i18n.msg(
    "co_managers.flash_removed",
    "Co-manager removed — they no longer have access to this frame.")
FLASH_LEFT_TEXT = i18n.msg(
    "co_managers.flash_left",
    "You left the frame — it no longer appears in your account.")
FLASH_ADD_REFUSED_TEXT = i18n.msg(
    "co_managers.flash_add_refused",
    "That address can't be added — check the spelling, or ask an "
    "administrator to invite this person first.")
FLASH_FAILED_TEXT = i18n.msg(
    "co_managers.flash_failed",
    "Couldn't update co-managers — try again in a moment.")
FLASH_LEAVE_NOOP_TEXT = i18n.msg(
    "co_managers.flash_leave_noop",
    "Nothing changed — only co-managers can leave a frame.")

_HEADING = i18n.msg("co_managers.heading", "Co-managers")
_PURPOSE_MANAGE = i18n.msg(
    "co_managers.purpose_manage",
    "People who can change this frame's settings alongside the owner. They "
    "cannot retire or reassign it.")
_PURPOSE_READ_ONLY = i18n.msg(
    "co_managers.purpose_read_only",
    "These people manage this frame. Only the owner or an administrator can "
    "change the list.")
_PILL_OWNER = i18n.msg("co_managers.pill_owner", "Owner")
_PILL_YOU = i18n.msg("co_managers.pill_you", "You")
_PILL_DISABLED = i18n.msg("co_managers.pill_disabled", "Disabled")
_EMPTY_HEADING = i18n.msg("co_managers.empty_heading", "No co-managers yet")
_EMPTY_BODY_OWNER = i18n.msg(
    "co_managers.empty_body_owner",
    "Add someone by e-mail address so they can manage this frame too.")
_EMPTY_BODY_ADMIN = i18n.msg(
    "co_managers.empty_body_admin",
    "Choose an invited person to let them manage this frame too.")
_LABEL_EMAIL = i18n.msg("co_managers.label_email", "E-mail address")
_HELPER_EMAIL = i18n.msg(
    "co_managers.helper_email", "The person must already be invited to SkyPane.")
_LABEL_PERSON = i18n.msg("co_managers.label_person", "Invited person")
_CHOOSE_PERSON = i18n.msg("co_managers.choose_person", "Choose a person")
_NO_CANDIDATES = i18n.msg(
    "co_managers.no_candidates",
    "Everyone who is invited is already on this frame.")
_ADD_BUTTON = i18n.msg("co_managers.add_button", "Add co-manager")
_REMOVE_BUTTON = i18n.msg("co_managers.remove_button", "Remove")
_REMOVE_ARIA = i18n.msg("co_managers.remove_aria", "Remove %s from this frame")
_LEAVE_TEXT = i18n.msg("co_managers.leave", "Leave this frame")
_LEAVE_CONSEQUENCE = i18n.msg(
    "co_managers.leave_consequence",
    "You will lose access to this frame and its settings. The owner or an "
    "administrator can add you again.")
_LEAVE_KEEP = i18n.msg("co_managers.leave_keep", "Stay on this frame")

_EMAIL_INPUT_ID = "co-manager-email"
_PERSON_SELECT_ID = "co-manager-person"
_EMAIL_HELP_ID = "co-manager-email-help"
_MAX_EMAIL_CHARS = 254


class CardView(NamedTuple):
    """What the card shows. `members` is a tuple of (user_id, email,
    disabled); `candidates` is a tuple of e-mails, empty for anyone who is not
    an administrator."""
    owner_email: str
    members: tuple
    candidates: tuple
    can_manage: bool
    viewer_user_id: int | None
    viewer_is_member: bool
    is_admin_viewer: bool


def _esc(value):
    return escape_html(value)


def _t(message):
    return _esc(i18n.t(message))


def _csrf_field():
    # Imported on use: this module loads while the page registry is importing.
    from companion import layout
    return layout.csrf_field()


def _warning_icon():
    from companion import layout
    return layout.toast_icon_html("warning")


def _pill(message):
    return '<span class="banner__pill">%s</span>' % _t(message)


def _who_html(email, pills):
    return (
        '<div class="co-manager__who"><span class="co-manager__email text-body">%s</span>%s</div>'
        % (_esc(email), "".join(_pill(p) for p in pills)))


def _row_html(who_html, action_html=""):
    return '<li class="data-card"><div class="co-manager__row">%s%s</div></li>' % (
        who_html, action_html)


def _remove_form_html(user_id, email):
    return (
        '<form method="post" action="%s" class="co-manager__remove">%s'
        '<input type="hidden" name="%s" value="%d">'
        '<button type="submit" class="calendar-disconnect-btn" aria-label="%s">%s</button>'
        "</form>" % (
            _esc(device_scope.scoped(REMOVE_ROUTE, "POST")), _csrf_field(),
            FIELD_USER_ID, int(user_id),
            _esc(i18n.t(_REMOVE_ARIA) % email), _t(_REMOVE_BUTTON)))


def _member_row(view, member):
    user_id, email, disabled = member
    pills = []
    if view.viewer_user_id is not None and user_id == view.viewer_user_id:
        pills.append(_PILL_YOU)
    if disabled and view.can_manage:
        pills.append(_PILL_DISABLED)
    action = _remove_form_html(user_id, email) if view.can_manage else ""
    return _row_html(_who_html(email, pills), action)


def _list_html(view):
    rows = [_row_html(_who_html(view.owner_email, (_PILL_OWNER,)))]
    rows.extend(_member_row(view, member) for member in view.members)
    return '<ul class="data-cards">%s</ul>' % "".join(rows)


def _empty_html(view):
    from companion import layout
    body = _EMPTY_BODY_ADMIN if view.is_admin_viewer else _EMPTY_BODY_OWNER
    return layout.empty_state(
        i18n.t(_EMPTY_HEADING), i18n.t(body), compact=True)


def _add_form(field_html, submit_html):
    return (
        '<form method="post" action="%s" class="fleet-form" autocomplete="off">%s%s'
        '<div class="update-actions">%s</div></form>' % (
            _esc(device_scope.scoped(ADD_ROUTE, "POST")), _csrf_field(),
            field_html, submit_html))


def _typed_field_html():
    return (
        '<p><label for="%s">%s</label>'
        '<input type="email" id="%s" name="%s" autocomplete="off" '
        'autocapitalize="none" spellcheck="false" required maxlength="%d" '
        'aria-describedby="%s"></p>'
        '<p class="text-label section-caption" id="%s">%s</p>' % (
            _EMAIL_INPUT_ID, _t(_LABEL_EMAIL), _EMAIL_INPUT_ID, FIELD_EMAIL,
            _MAX_EMAIL_CHARS, _EMAIL_HELP_ID, _EMAIL_HELP_ID, _t(_HELPER_EMAIL)))


def _select_field_html(candidates):
    options = '<option value="">%s</option>' % _t(_CHOOSE_PERSON) + "".join(
        '<option value="%s">%s</option>' % (_esc(email), _esc(email))
        for email in candidates)
    return (
        '<p><label for="%s">%s</label>'
        '<select id="%s" name="%s" required>%s</select></p>' % (
            _PERSON_SELECT_ID, _t(_LABEL_PERSON), _PERSON_SELECT_ID, FIELD_EMAIL,
            options))


def _add_html(view):
    """The Add control: a typed address for an owner, a choice of the eligible
    invited people for an administrator (never decided by the list being
    empty)."""
    if view.is_admin_viewer and not view.candidates:
        return '<p class="text-label section-caption">%s</p>' % _t(_NO_CANDIDATES)
    field = (
        _select_field_html(view.candidates) if view.is_admin_viewer
        else _typed_field_html())
    submit = '<button type="submit">%s</button>' % _t(_ADD_BUTTON)
    return _add_form(field, submit)


def _leave_html():
    """The two-step Leave: a closed `<details>`. The form posts no id; the
    server acts on the caller's own membership."""
    return (
        '<details class="fleet-confirm"><summary>%s</summary>'
        '<form method="post" action="%s" class="fleet-confirm__form">%s'
        '<p class="text-body">%s%s</p>'
        '<div class="update-actions">'
        '<button type="submit" class="calendar-disconnect-btn">%s</button>'
        '<a class="text-link" href="%s">%s</a></div></form></details>' % (
            _t(_LEAVE_TEXT), _esc(device_scope.scoped(LEAVE_ROUTE, "POST")),
            _csrf_field(), _warning_icon(), _t(_LEAVE_CONSEQUENCE),
            _t(_LEAVE_TEXT), _esc(device_scope.scoped("/")), _t(_LEAVE_KEEP)))



def render(view):
    """The Co-managers card for `view`."""
    parts = [
        '<section class="page-section" aria-labelledby="home-co-managers">'
        '<h2 class="text-heading" id="home-co-managers">%s</h2>'
        '<p class="text-label section-caption">%s</p>' % (
            _t(_HEADING), _t(_PURPOSE_MANAGE if view.can_manage else _PURPOSE_READ_ONLY)),
        _list_html(view)]
    if view.can_manage:
        if not view.members:
            parts.append(_empty_html(view))
        parts.append(_add_html(view))
    elif view.viewer_is_member:
        parts.append(_leave_html())
    parts.append("</section>")
    return "".join(parts)
