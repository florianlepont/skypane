"""The Users page body: every user as one table row (email, a role select that
saves on change, frame count, last sign-in, an Active switch and a "..." menu
of rare actions; a card on a phone) plus the invite dialog the header button
opens.

Pure markup: it takes a `UsersView` and reads nothing else. A row carries
display facts only; the issuer and subject of a linked identity, session
tokens and hashes never reach this module (`has_identity` is a boolean).
The guard states are sentences shown in place of the role select, with the
Active switch locked, for the signed-in administrator and for the last active
administrator.
"""
import datetime
from typing import NamedTuple

from companion import i18n, ui_base, ui_entity_list, ui_modal, ui_time
from companion.ui_base import escape_html, icon_html

EMAIL_FIELD = "email"
ROLE_FIELD = "role"
ROLE_USER = "user"
ROLE_ADMIN = "admin"

STATUS_ACTIVE = "active"
STATUS_DISABLED = "disabled"
STATUS_INVITED = "invited"

INVITE_DIALOG_ID = "dlg-invite-user"

_USERS_TEXT = i18n.msg("admin_users.users", "Users")
_COUNT_MANY = i18n.msg("admin_users.n_users", "%d users")
_COUNT_ONE = i18n.msg("admin_users.one_user", "1 user")
_FRAMES_MANY = i18n.msg("admin_users.n_frames", "%d frames")
_FRAMES_ONE = i18n.msg("admin_users.one_frame", "1 frame")
_YOU = i18n.msg("admin_users.you", "You")
_COL_EMAIL = i18n.msg("admin_users.email", "Email")
_COL_ROLE = i18n.msg("admin_users.role", "Role")
_ROLE_NAME_USER = i18n.msg("admin_users.role_user", "User")
_ROLE_NAME_ADMIN = i18n.msg("admin_users.role_administrator", "Administrator")
_STATUS_DISABLED = i18n.msg("admin_users.status_disabled", "Disabled")
_STATUS_INVITED = i18n.msg("admin_users.status_invited", "Invited")
_THIS_IS_YOU = i18n.msg("admin_users.this_is_you", "This is you.")
_LAST_ADMIN = i18n.msg(
    "admin_users.the_last_active_administrator_cannot_be_changed",
    "The last active administrator cannot be changed.")

_COL_USER = i18n.msg("admin_users.col_user", "User")
_COL_FRAMES = i18n.msg("admin_users.col_frames", "Frames")
_COL_LAST_SIGN_IN = i18n.msg("admin_users.col_last_sign_in", "Last sign-in")
_COL_ACTIVE = i18n.msg("admin_users.col_active", "Active")
_NEVER_SIGNED_IN = i18n.msg("admin_users.never_signed_in", "Never signed in")
_ROLE_OF_ARIA = i18n.msg("admin_users.role_of_aria", "Role of %s")
_ACTIVE_ARIA = i18n.msg("admin_users.active_aria", "Active: %s")
_MORE_ARIA = i18n.msg("admin_users.more_actions_aria", "More actions for %s")
_SAVE_ROLE = i18n.msg("admin_users.save_role", "Save role")
_UNLINK_BUTTON = i18n.msg("admin_users.unlink_identity", "Unlink identity")

_INVITE_BUTTON = i18n.msg("admin_users.invite_a_user_button", "+ Invite a user")
_INVITE_TITLE = i18n.msg("admin_users.invite_a_user", "Invite a user")
_BACK_TO_USERS = i18n.msg("admin_users.back_to_users", "Back to Users")
_INVITE_PURPOSE = i18n.msg(
    "admin_users.they_sign_in_with_this_email_through_auth0_skypane_does",
    "They sign in with this email through Auth0. SkyPane does not send them a "
    "message, so tell them to sign in.")
_INVITE_SUBMIT = i18n.msg("admin_users.invite_user", "Invite user")
INVITE_EMAIL_ERROR = i18n.msg(
    "admin_users.enter_a_valid_email_address", "Enter a valid email address.")
INVITE_DUPLICATE_ERROR = i18n.msg(
    "admin_users.that_email_is_already_invited", "That email is already invited.")
INVITE_ROLE_ERROR = i18n.msg("admin_users.choose_a_role", "Choose a role.")


class UserRow(NamedTuple):
    """One user as the list shows it. `last_seen` is epoch seconds or None;
    `is_self` marks the signed-in administrator and `is_last_admin` the only
    active administrator."""
    user_id: int
    email: str
    role: str
    disabled: bool
    has_identity: bool
    last_seen: float | None
    frame_count: int
    is_self: bool
    is_last_admin: bool


class UsersView(NamedTuple):
    """Everything the page renders; the invite fields carry the state of a
    refused submission."""
    rows: tuple
    now: datetime.datetime
    email_value: str = ""
    role_selected: str = ROLE_USER
    email_error: str = ""
    role_error: str = ""
    open_invite_dialog: bool = False


def role_name(role):
    return i18n.t(_ROLE_NAME_ADMIN if role == ROLE_ADMIN else _ROLE_NAME_USER)


def status_of(row):
    if row.disabled:
        return STATUS_DISABLED
    return STATUS_ACTIVE if row.has_identity else STATUS_INVITED


def _routes():
    # Imported on use: companion.console_routes imports the route modules.
    from companion import console_routes
    return console_routes


def _ui():
    # Imported on use: this page loads while the navigation is still importing.
    from companion import ui_components
    return ui_components


def _esc(value):
    return escape_html(value)


def _t(message):
    return _esc(i18n.t(message))


def _pill(label_html):
    return '<span class="banner__pill">%s</span>' % label_html


def _pills_html(row):
    pills = []
    if status_of(row) == STATUS_INVITED:
        pills.append(_pill(_t(_STATUS_INVITED)))
    if row.disabled:
        pills.append(_pill(_t(_STATUS_DISABLED)))
    return "".join(pills)


def _frames_text(count):
    return i18n.t(_FRAMES_ONE) if count == 1 else i18n.t(_FRAMES_MANY) % count


def _count_text(count):
    return i18n.t(_COUNT_ONE) if count == 1 else i18n.t(_COUNT_MANY) % count


def _initial(email):
    return _esc(email[:1].upper())


def _last_sign_in_html(row, now):
    if row.last_seen is None:
        return _t(_NEVER_SIGNED_IN)
    seen = datetime.datetime.fromtimestamp(row.last_seen, datetime.timezone.utc)
    return ui_time.relative_time_html(
        seen.isoformat(), now.isoformat(), fallback=i18n.t(_NEVER_SIGNED_IN))


def _action_path(row, suffix):
    return "%s%d%s" % (_routes().USER_ACTION_PREFIX, row.user_id, suffix)


def _post_form(row, suffix, css, inner_html):
    return (
        '<form method="post" action="%s" class="%s">%s%s</form>' % (
            _esc(_action_path(row, suffix)), css, _ui().csrf_field(), inner_html))


def _guard_html(row):
    notes = ""
    if row.is_self:
        notes += '<span class="users-guard text-label">%s</span>' % _t(_THIS_IS_YOU)
    if row.is_last_admin:
        notes += '<span class="users-guard text-label">%s</span>' % _t(_LAST_ADMIN)
    return notes


def _role_cell(row):
    """The role select that saves on change (a Save button shows only
    without script), or the plain role and the guard sentences for the
    signed-in administrator and the last active administrator."""
    guard = _guard_html(row)
    if guard:
        return '<span class="users-role-fixed">%s</span>%s' % (
            _esc(role_name(row.role)), guard)
    select_id = "role-%d" % row.user_id
    controls = (
        '<label class="visually-hidden" for="%s">%s</label>'
        '<select id="%s" name="%s" data-autosubmit>%s</select>'
        '<noscript><button type="submit" class="users-role-save">%s</button></noscript>' % (
            select_id, _esc(i18n.t(_ROLE_OF_ARIA) % row.email), select_id, ROLE_FIELD,
            _role_options(row.role), _t(_SAVE_ROLE)))
    return _post_form(row, _routes().USER_ROLE_SUFFIX, "users-role-form", controls)


def _active_cell(row):
    """The Active switch: on posts to disable, off posts to enable. It is
    shown disabled where the server refuses the change anyway."""
    active = not row.disabled
    locked = active and (row.is_self or row.is_last_admin)
    button = (
        '<button type="submit" class="switch" role="switch" aria-checked="%s" '
        'aria-label="%s"%s><span class="switch__track" aria-hidden="true">'
        '<span class="switch__thumb"></span></span></button>' % (
            "true" if active else "false", _esc(i18n.t(_ACTIVE_ARIA) % row.email),
            " disabled" if locked else ""))
    label = '<span class="users-active-label text-label" aria-hidden="true">%s</span>' % (
        _t(_COL_ACTIVE))
    suffix = _routes().USER_DISABLE_SUFFIX if active else _routes().USER_ENABLE_SUFFIX
    return _post_form(row, suffix, "users-active-form", label + button)


def _menu_cell(row):
    """The "..." menu: only the rare actions, today the identity unlink of a
    user who has signed in."""
    if not row.has_identity:
        return ""
    unlink = _post_form(
        row, _routes().USER_UNLINK_SUFFIX, "users-menu__form",
        '<button type="submit" class="row-menu__item row-menu__item--destructive">'
        '%s</button>' % _t(_UNLINK_BUTTON))
    return (
        '<details class="row-menu"><summary class="row-menu__toggle" aria-label="%s">'
        '%s</summary><div class="row-menu__panel">%s</div></details>' % (
            _esc(i18n.t(_MORE_ARIA) % row.email), icon_html("icon-more-vertical", size=20),
            unlink))


def _row_html(row, now):
    you = _pill(_t(_YOU)) if row.is_self else ""
    return (
        '<tr class="users-row" id="user-%d">'
        '<th scope="row" class="users-cell users-cell--user">'
        '<span class="users-avatar" aria-hidden="true">%s</span>'
        '<span class="users-who"><span class="users-email">%s</span>'
        '<span class="users-pills">%s%s</span></span></th>'
        '<td class="users-cell users-cell--role">%s</td>'
        '<td class="users-cell users-cell--frames">%s</td>'
        '<td class="users-cell users-cell--seen">%s</td>'
        '<td class="users-cell users-cell--active">%s</td>'
        '<td class="users-cell users-cell--menu">%s</td></tr>' % (
            row.user_id, _initial(row.email), _esc(row.email), you, _pills_html(row),
            _role_cell(row), _esc(_frames_text(row.frame_count)),
            _last_sign_in_html(row, now), _active_cell(row), _menu_cell(row)))


def _table_html(view):
    head = "".join(
        '<th scope="col" class="users-col users-col--%s">%s</th>' % (name, _t(label))
        for name, label in (
            ("user", _COL_USER), ("role", _COL_ROLE), ("frames", _COL_FRAMES),
            ("seen", _COL_LAST_SIGN_IN), ("active", _COL_ACTIVE)))
    return (
        '%s<table class="users-table"><caption class="visually-hidden">%s</caption>'
        '<thead><tr>%s<td class="users-col users-col--menu"></td></tr></thead>'
        '<tbody>%s</tbody></table>' % (
            ui_entity_list.count_line_html(_count_text(len(view.rows))),
            _t(_USERS_TEXT), head,
            "".join(_row_html(row, view.now) for row in view.rows)))



def _role_options(selected):
    return "".join(
        '<option value="%s"%s>%s</option>' % (
            value, " selected" if value == selected else "", _esc(role_name(value)))
        for value in (ROLE_USER, ROLE_ADMIN))


def _field_error(field, message):
    """(attributes for the control, the error paragraph) of one invite field."""
    if not message:
        return "", ""
    return (
        ' aria-invalid="true" aria-describedby="%s"' % _esc(
            ui_modal.error_id(INVITE_DIALOG_ID, field)),
        ui_modal.field_error_html(INVITE_DIALOG_ID, field, message))


def _invite_dialog(view):
    email_attrs, email_error = _field_error("email", view.email_error)
    role_attrs, role_error = _field_error("role", view.role_error)
    body = (
        '<p class="text-body">%s</p>'
        '<div class="modal__field"><label for="invite-email">%s</label>'
        '<input type="email" id="invite-email" name="%s" required maxlength="254" '
        'autocomplete="off" spellcheck="false" value="%s"%s%s>%s</div>'
        '<div class="modal__field"><label for="invite-role">%s</label>'
        '<select id="invite-role" name="%s"%s>%s</select>%s</div>' % (
            _t(_INVITE_PURPOSE), _t(_COL_EMAIL), EMAIL_FIELD, _esc(view.email_value),
            email_attrs, ui_base.validation_attrs("email"), email_error, _t(_COL_ROLE), ROLE_FIELD, role_attrs,
            _role_options(view.role_selected), role_error))
    return ui_modal.dialog_html(
        INVITE_DIALOG_ID, i18n.t(_INVITE_TITLE), _routes().USERS_INVITE_ROUTE,
        _ui().csrf_field(), body, i18n.t(_INVITE_SUBMIT), i18n.t(_BACK_TO_USERS),
        _routes().USERS_ROUTE, open_=view.open_invite_dialog)

def header_action_html():
    """The page header's "+ Invite a user" trigger (opens the invite dialog)."""
    trigger = ui_modal.trigger_html(
        INVITE_DIALOG_ID, _t(_INVITE_BUTTON), "page-header__action")
    return '<div class="page-header__actions page-header__actions--stack">%s</div>' % trigger


def render(view):
    """The Users page body (the shell supplies the header and nav)."""
    return (
        '<section class="page-section users-section" aria-label="%s">%s</section>' % (
            _t(_USERS_TEXT), _table_html(view))
        + _invite_dialog(view))
