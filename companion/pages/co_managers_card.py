"""Frame co-management: the three POST route paths, the form field names, the
flash keys and their texts, and the pure markup of the Manage access and Leave
this frame dialogs, so the handlers, the dialogs and the flash registry all
read one definition.

The Manage access dialog takes a `CardView` and reads nothing else. It is for
an owner or an administrator only (`can_manage`); the invited-user list reaches
it only through `candidates`, which the view builder fills for an
administrator alone. Its forms post to the frame's own `/devices/<id>/...`
routes, so the host page (Fleet or Account) need not be device-scoped, and
carry the host page path as `return_to` so the dialog reopens after a change.
"""
from typing import NamedTuple

from companion import i18n
from companion.ui_base import escape_html

ADD_ROUTE = "/co-managers/add"
REMOVE_ROUTE = "/co-managers/remove"
LEAVE_ROUTE = "/co-managers/leave"

FIELD_EMAIL = "email"
FIELD_USER_ID = "user_id"
FIELD_RETURN_TO = "return_to"

# The only pages a co-manager form may return to: exact paths, nothing else.
RETURN_FLEET = "/fleet"
RETURN_ACCOUNT = "/account"
RETURN_PATHS = (RETURN_FLEET, RETURN_ACCOUNT)
ACCESS_QUERY = "access"

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
_DIALOG_TITLE = i18n.msg("co_managers.dialog_title", "Manage access")
MENU_LABEL = i18n.msg("co_managers.menu_label", "Manage access")
_DONE = i18n.msg("co_managers.done", "Done")
_LEAVE_TITLE = i18n.msg("co_managers.leave_title", "Leave this frame?")
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

_MAX_EMAIL_CHARS = 254


class CardView(NamedTuple):
    """What the Manage access dialog shows. `members` is a tuple of
    (user_id, email, disabled); `candidates` is a tuple of e-mails, empty for
    anyone who is not an administrator."""
    owner_email: str
    members: tuple
    candidates: tuple
    viewer_user_id: int | None
    is_admin_viewer: bool


def safe_return_to(value):
    """`value` when it is exactly one of the pages a form may return to,
    else None. No prefix, query or look-alike path passes."""
    return value if isinstance(value, str) and value in RETURN_PATHS else None


def dialog_id(prefix, device_id):
    """A dialog slug for a frame: device ids carry underscores that a dialog
    slug does not allow."""
    return "%s-%s" % (prefix, str(device_id).lower().replace("_", "-"))


def access_dialog_id(device_id):
    return dialog_id("dlg-access", device_id)


def leave_dialog_id(device_id):
    return dialog_id("dlg-leave", device_id)


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


def _frame_route(device_id, route):
    return "/devices/%s%s" % (device_id, route)


def _return_field(return_to):
    return '<input type="hidden" name="%s" value="%s">' % (
        FIELD_RETURN_TO, _esc(return_to))


def _pill(message):
    return '<span class="banner__pill">%s</span>' % _t(message)


def _who_html(email, pills):
    return (
        '<div class="co-manager__who"><span class="co-manager__email text-body">%s</span>%s</div>'
        % (_esc(email), "".join(_pill(p) for p in pills)))


def _row_html(who_html, action_html=""):
    return '<li class="data-card"><div class="co-manager__row">%s%s</div></li>' % (
        who_html, action_html)


def _remove_form_html(device_id, user_id, email, return_to):
    return (
        '<form method="post" action="%s" class="co-manager__remove">%s%s'
        '<input type="hidden" name="%s" value="%d">'
        '<button type="submit" class="calendar-disconnect-btn" aria-label="%s">%s</button>'
        "</form>" % (
            _esc(_frame_route(device_id, REMOVE_ROUTE)), _csrf_field(),
            _return_field(return_to), FIELD_USER_ID, int(user_id),
            _esc(i18n.t(_REMOVE_ARIA) % email), _t(_REMOVE_BUTTON)))


def _member_row(view, device_id, member, return_to):
    user_id, email, disabled = member
    pills = []
    if view.viewer_user_id is not None and user_id == view.viewer_user_id:
        pills.append(_PILL_YOU)
    if disabled:
        pills.append(_PILL_DISABLED)
    return _row_html(
        _who_html(email, pills), _remove_form_html(device_id, user_id, email, return_to))


def _list_html(view, device_id, return_to):
    rows = [_row_html(_who_html(view.owner_email, (_PILL_OWNER,)))]
    rows.extend(_member_row(view, device_id, member, return_to) for member in view.members)
    return '<ul class="data-cards data-cards--standalone">%s</ul>' % "".join(rows)


def _empty_html(view):
    from companion import layout
    body = _EMPTY_BODY_ADMIN if view.is_admin_viewer else _EMPTY_BODY_OWNER
    return layout.empty_state(
        i18n.t(_EMPTY_HEADING), i18n.t(body), compact=True)


def _add_form(device_id, return_to, field_html, submit_html):
    return (
        '<form method="post" action="%s" class="fleet-form" autocomplete="off">%s%s%s'
        '<div class="update-actions">%s</div></form>' % (
            _esc(_frame_route(device_id, ADD_ROUTE)), _csrf_field(),
            _return_field(return_to), field_html, submit_html))


def _field_ids(device_id, prefix="co-manager"):
    slug = dialog_id(prefix, device_id)
    return slug + "-email", slug + "-person", slug + "-email-help"


def _typed_field_html(device_id, prefix="co-manager"):
    input_id, _person_id, help_id = _field_ids(device_id, prefix)
    return (
        '<p><label for="%s">%s</label>'
        '<input type="email" id="%s" name="%s" autocomplete="off" '
        'autocapitalize="none" spellcheck="false" required maxlength="%d" '
        'aria-describedby="%s"></p>'
        '<p class="text-label section-caption" id="%s">%s</p>' % (
            input_id, _t(_LABEL_EMAIL), input_id, FIELD_EMAIL,
            _MAX_EMAIL_CHARS, help_id, help_id, _t(_HELPER_EMAIL)))


def _select_field_html(device_id, candidates, prefix="co-manager"):
    _input_id, person_id, _help_id = _field_ids(device_id, prefix)
    options = '<option value="">%s</option>' % _t(_CHOOSE_PERSON) + "".join(
        '<option value="%s">%s</option>' % (_esc(email), _esc(email))
        for email in candidates)
    return (
        '<p><label for="%s">%s</label>'
        '<select id="%s" name="%s" required>%s</select></p>' % (
            person_id, _t(_LABEL_PERSON), person_id, FIELD_EMAIL, options))


def _add_html(view, device_id, return_to, prefix="co-manager"):
    """The Add control: a typed address for an owner, a choice of the eligible
    invited people for an administrator (never decided by the list being
    empty)."""
    if view.is_admin_viewer and not view.candidates:
        return '<p class="text-label section-caption">%s</p>' % _t(_NO_CANDIDATES)
    field = (
        _select_field_html(device_id, view.candidates, prefix) if view.is_admin_viewer
        else _typed_field_html(device_id, prefix))
    submit = '<button type="submit">%s</button>' % _t(_ADD_BUTTON)
    return _add_form(device_id, return_to, field, submit)


def access_section_html(view, device_id, return_to, id_prefix="co-manager"):
    """The access content of one frame: the owner, the co-managers with a
    Remove form each, and the Add form. Shown inside the Manage access
    dialog and inline in the Console Fleet frame view."""
    parts = [
        '<section class="page-section">'
        '<h3 class="text-heading">%s</h3>'
        '<p class="text-label section-caption">%s</p>' % (
            _t(_HEADING), _t(_PURPOSE_MANAGE)),
        _list_html(view, device_id, return_to)]
    if not view.members:
        parts.append(_empty_html(view))
    parts.append(_add_html(view, device_id, return_to, id_prefix))
    parts.append("</section>")
    return "".join(parts)


def manage_access_dialog_html(view, device_id, frame_name, return_to, open_=False):
    """The Manage access dialog of one frame: the owner, the co-managers with
    a Remove form each, and the Add form. `return_to` is a whitelisted host
    page path (see `safe_return_to`); the forms send it back so the dialog
    reopens there after a change. `open_` renders it open."""
    from companion import ui_modal
    return ui_modal.sections_dialog_html(
        access_dialog_id(device_id), i18n.t(_DIALOG_TITLE), frame_name,
        access_section_html(view, device_id, return_to), i18n.t(_DONE), return_to,
        open_=open_)


def leave_dialog_html(device_id, frame_name, return_to=RETURN_ACCOUNT):
    """The confirm-only Leave this frame dialog. The form posts no id; the
    server acts on the caller's own membership."""
    from companion import ui_modal
    body = '<p class="text-body">%s%s</p>' % (_warning_icon(), _t(_LEAVE_CONSEQUENCE))
    return ui_modal.dialog_html(
        leave_dialog_id(device_id), i18n.t(_LEAVE_TITLE),
        _frame_route(device_id, LEAVE_ROUTE), _csrf_field(), body,
        i18n.t(_LEAVE_TEXT), i18n.t(_LEAVE_KEEP), return_to,
        destructive=True, confirm_only=True, subtitle=frame_name)
