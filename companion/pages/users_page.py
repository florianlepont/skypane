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
# Posted by the confirmation dialog: a role change without it only asks.
CONFIRMED_FIELD = "confirmed"
CONFIRMED_VALUE = "1"
# The Users address that opens the confirmation of one user's role change.
ROLE_CHANGE_PARAM = "role_change"
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
_STATUS_ACTIVE = i18n.msg("admin_users.status_active", "Active")
_CO_MANAGER_SUFFIX = i18n.msg("admin_users.co_manager_suffix", "co-manager")
_SELF_LOCK = i18n.msg(
    "admin_users.self_lock", "You cannot disable or demote yourself.")
_COPY_INVITE = i18n.msg("admin_users.copy_invitation", "Copy invitation message")
_COPIED = i18n.msg("admin_users.copied", "Copied")
_COL_INVITATION = i18n.msg("admin_users.col_invitation", "Invitation message")
_INVITATION_MESSAGE = i18n.msg(
    "admin_users.invitation_message",
    "Hello, you have been invited to SkyPane. Open {url} and sign in with "
    "{email}.")
_INVITATION_MESSAGE_NO_URL = i18n.msg(
    "admin_users.invitation_message_no_url",
    "Hello, you have been invited to SkyPane. Open the app and sign in with "
    "{email}.")
_COL_EMAIL = i18n.msg("admin_users.email", "Email")
_COL_ROLE = i18n.msg("admin_users.role", "Role")
_ROLE_NAME_USER = i18n.msg("admin_users.role_user", "User")
_ROLE_NAME_ADMIN = i18n.msg("admin_users.role_administrator", "Administrator")
_STATUS_DISABLED = i18n.msg("admin_users.status_disabled", "Disabled")
_STATUS_INVITED = i18n.msg("admin_users.status_invited", "Invited, not signed in yet")
_STATUS_INVITED_HELP = i18n.msg(
    "admin_users.status_invited_help",
    "This person was added but has not signed in yet. The mark goes away at their first "
    "sign-in.")
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
_UNLINK_BUTTON = i18n.msg("admin_users.unlink_identity", "Reset sign-in")
_UNLINK_HINT = i18n.msg(
    "admin_users.unlink_identity_hint",
    "Signs this person out; they link their sign-in account again next time they sign in.")

_DELETE_BUTTON = i18n.msg("admin_users.delete_user", "Delete user")
_PROMOTE_TITLE = i18n.msg(
    "admin_users.promote_title", "Make this person an administrator?")
_PROMOTE_WHAT = i18n.msg(
    "admin_users.promote_what",
    "%s will be able to manage every frame, every user and every setting.")
_PROMOTE_SUBMIT = i18n.msg("admin_users.promote_submit", "Make administrator")
_PROMOTE_KEEP = i18n.msg("admin_users.promote_keep", "Keep as user")
_DEMOTE_TITLE = i18n.msg("admin_users.demote_title", "Remove administrator rights?")
_DEMOTE_WHAT = i18n.msg(
    "admin_users.demote_what",
    "%s will lose the admin console and will only see the frames they own or "
    "co-manage.")
_DEMOTE_SUBMIT = i18n.msg("admin_users.demote_submit", "Remove rights")
_DEMOTE_KEEP = i18n.msg("admin_users.demote_keep", "Keep as administrator")
_DELETE_TITLE = i18n.msg("admin_users.delete_user_title", "Delete this user?")
_DELETE_KEEP = i18n.msg("admin_users.delete_user_keep", "Keep this user")
_DELETE_WHAT = i18n.msg(
    "admin_users.delete_user_what",
    "%s is removed from SkyPane. Their sign-in sessions are closed, they lose "
    "access to the frames they co-manage and their record is deleted. The "
    "audit log keeps their address. This cannot be undone.")
_DELETE_OWNER_RULE = i18n.msg(
    "admin_users.delete_user_owner_rule",
    "Someone who owns a frame cannot be deleted: reassign or retire the "
    "frame first.")

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
    co_managed_count: int = 0


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
    app_url: str = ""
    # (user id, new role) of a role change waiting for its confirmation.
    role_change: tuple | None = None


def role_name(role):
    return i18n.t(_ROLE_NAME_ADMIN if role == ROLE_ADMIN else _ROLE_NAME_USER)


def status_of(row):
    if row.disabled:
        return STATUS_DISABLED
    # A recorded sign-in means the person has signed in, whatever the identity
    # link says: the invited mark never sits beside a last sign-in time.
    return STATUS_ACTIVE if row.has_identity or row.last_seen is not None else STATUS_INVITED


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


def _pill(label_html, tone="", attrs=""):
    css = "banner__pill users-pill"
    if tone:
        css += " users-pill--" + tone
    return '<span class="%s"%s>%s</span>' % (css, attrs, label_html)


_STATUS_LABELS = {
    STATUS_ACTIVE: _STATUS_ACTIVE, STATUS_INVITED: _STATUS_INVITED,
    STATUS_DISABLED: _STATUS_DISABLED}


def _status_pill(row):
    """The row's status marks: Active (has signed in) or Invited (has not
    yet) while the person is enabled, Disabled otherwise. Both are in the
    markup, one of them hidden, so the Active switch can flip them in place
    (the quick-switch script toggles the two `data-quick-state-*` marks)."""
    enabled = status_of(row._replace(disabled=False))
    off = row.disabled
    help_attrs = ""
    if enabled == STATUS_INVITED:
        spoken = "%s. %s" % (i18n.t(_STATUS_INVITED), i18n.t(_STATUS_INVITED_HELP))
        help_attrs = ' title="%s" aria-label="%s"' % (_esc(spoken), _esc(spoken))
    return (
        _pill(_t(_STATUS_LABELS[enabled]), enabled,
              (" hidden" if off else "") + " data-quick-state-on" + help_attrs)
        + _pill(_t(_STATUS_DISABLED), STATUS_DISABLED,
                ("" if off else " hidden") + " data-quick-state-off"))


def _frames_text(count):
    return i18n.t(_FRAMES_ONE) if count == 1 else i18n.t(_FRAMES_MANY) % count


def _frames_cell_html(row):
    """Owned plus co-managed frames; a co-manager is named as such. The count
    and the mark are two parts the table stacks and a card joins with a dot."""
    count = '<span class="users-frames__part">%s</span>' % _esc(
        _frames_text(row.frame_count + row.co_managed_count))
    if not row.co_managed_count:
        return count
    return (
        '%s<span class="users-frames__dot"> \u00b7 </span>'
        '<span class="users-frames__part">%s</span>' % (count, _t(_CO_MANAGER_SUFFIX)))


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


def _guard_ids(row):
    return ["users-guard-%d-%s" % (row.user_id, name)
            for name, on in (("self", row.is_self), ("last", row.is_last_admin)) if on]


def _guard_html(row):
    notes = ""
    if row.is_self:
        notes += (
            '<span class="users-guard visually-hidden" id="users-guard-%d-self">%s %s</span>'
            % (row.user_id, _t(_THIS_IS_YOU), _t(_SELF_LOCK)))
    if row.is_last_admin:
        notes += (
            '<span class="users-guard visually-hidden" id="users-guard-%d-last">%s</span>'
            % (row.user_id, _t(_LAST_ADMIN)))
    return notes


def _role_cell(row):
    """The role select that sends its form on change (a Save button shows
    only without script) and lands on the confirmation dialog, or the plain role and the guard sentences for the
    signed-in administrator and the last active administrator."""
    guard = _guard_html(row)
    if guard:
        # The explanation is a tooltip and a hidden description of the role,
        # not text in the cell: the "You" pill already marks the row.
        explained = " ".join(
            _t(note) for flag, note in (
                (row.is_self, _SELF_LOCK), (row.is_last_admin, _LAST_ADMIN)) if flag)
        return '<span class="users-role-fixed" title="%s">%s</span>%s' % (
            explained, _esc(role_name(row.role)), guard)
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
    explained = (
        ' aria-describedby="%s"' % " ".join(_guard_ids(row)) if locked else "")
    button = _ui().switch_button_html(
        active, ' aria-label="%s" data-quick-control%s%s' % (
            _esc(i18n.t(_ACTIVE_ARIA) % row.email), explained, " disabled" if locked else ""))
    label = '<span class="users-active-label text-label" aria-hidden="true">%s</span>' % (
        _t(_COL_ACTIVE))
    on_path = _esc(_action_path(row, _routes().USER_DISABLE_SUFFIX))
    off_path = _esc(_action_path(row, _routes().USER_ENABLE_SUFFIX))
    return (
        '<form method="post" action="%s" class="users-active-form" data-quick-switch '
        'data-quick-action-on="%s" data-quick-action-off="%s">%s%s</form>' % (
            on_path if active else off_path, on_path, off_path,
            _ui().csrf_field(), label + button))


def delete_dialog_id(row):
    return "dlg-delete-user-%d" % row.user_id


def _delete_dialog(row):
    """The confirmation the menu's Delete user item opens."""
    body = '<p class="text-body">%s</p><p class="text-label">%s</p>' % (
        _esc(i18n.t(_DELETE_WHAT) % row.email), _t(_DELETE_OWNER_RULE))
    return ui_modal.dialog_html(
        delete_dialog_id(row), i18n.t(_DELETE_TITLE),
        _action_path(row, _routes().USER_DELETE_SUFFIX),
        _ui().csrf_field(), body, i18n.t(_DELETE_BUTTON), i18n.t(_DELETE_KEEP),
        _routes().USERS_ROUTE, destructive=True, confirm_only=True,
        subtitle=row.email)


def role_dialog_id(user_id):
    return "dlg-role-user-%d" % user_id


def _role_dialog(view):
    """The confirmation a changed role select lands on, open: granting or
    removing administrator rights is never one tap. Empty when no change is
    waiting or its row is gone."""
    if view.role_change is None:
        return ""
    user_id, role = view.role_change
    row = next((r for r in view.rows if r.user_id == user_id), None)
    if row is None:
        return ""
    promote = role == ROLE_ADMIN
    title, what, submit, keep = (
        (_PROMOTE_TITLE, _PROMOTE_WHAT, _PROMOTE_SUBMIT, _PROMOTE_KEEP) if promote
        else (_DEMOTE_TITLE, _DEMOTE_WHAT, _DEMOTE_SUBMIT, _DEMOTE_KEEP))
    fields = (
        '<input type="hidden" name="%s" value="%s">'
        '<input type="hidden" name="%s" value="%s">' % (
            ROLE_FIELD, _esc(role), CONFIRMED_FIELD, CONFIRMED_VALUE))
    body = '<p class="text-body">%s</p>' % _esc(i18n.t(what) % row.email)
    return ui_modal.dialog_html(
        role_dialog_id(user_id), i18n.t(title),
        _action_path(row, _routes().USER_ROLE_SUFFIX),
        _ui().csrf_field() + fields, body, i18n.t(submit), i18n.t(keep),
        _routes().USERS_ROUTE, destructive=not promote, confirm_only=True,
        open_=True, subtitle=row.email, return_on_close=True,
        return_focus_id="role-%d" % user_id)


def _menu_cell(row):
    """The "..." menu: only the rare actions, the identity unlink of a user
    who has signed in, then Delete user, which opens its confirmation. The
    signed-in administrator's own row offers no Delete (the server refuses
    it), and no menu at all when nothing else is left."""
    unlink = ""
    if row.has_identity:
        unlink = _post_form(
            row, _routes().USER_UNLINK_SUFFIX, "users-menu__form",
            '<button type="submit" class="row-menu__item row-menu__item--destructive" '
            'title="%s">%s</button>' % (_t(_UNLINK_HINT), _t(_UNLINK_BUTTON)))
    if not row.is_self:
        unlink += ui_modal.trigger_html(
            delete_dialog_id(row), _t(_DELETE_BUTTON),
            "row-menu__item row-menu__item--destructive")
    if not unlink:
        return ""
    return (
        '<details class="row-menu"><summary class="row-menu__toggle" aria-label="%s">'
        '%s</summary><div class="row-menu__panel">%s</div></details>' % (
            _esc(i18n.t(_MORE_ARIA) % row.email), icon_html("icon-more-vertical", size=20),
            unlink))


def invitation_message(app_url, email):
    """The sentence an administrator pastes to someone they invited: where to
    go and which address to sign in with. It carries no secret."""
    if app_url:
        return i18n.t(_INVITATION_MESSAGE).format(url=app_url, email=email)
    return i18n.t(_INVITATION_MESSAGE_NO_URL).format(email=email)


def _invite_cell(row, app_url):
    """The Copy invitation message button of a person who has not signed in
    yet. The shared copy script writes the message with the Clipboard API and
    falls back to a text selection; the button is hidden without script."""
    if status_of(row) != STATUS_INVITED:
        return ""
    return (
        '<button type="button" class="users-copy" data-copy-value="%s" '
        'data-copied-text="%s">%s<span class="copy-btn__label">%s</span></button>'
        '<span class="visually-hidden" role="status" data-copy-feedback></span>' % (
            _esc(invitation_message(app_url, row.email)), _t(_COPIED),
            icon_html("icon-copy"), _t(_COPY_INVITE)))


def _breakable(email):
    """The address escaped, with a break opportunity after each "@" and ".":
    a narrow phone card wraps it there and never inside a word. Wider layouts
    keep it on one line and end it with an ellipsis; the title holds it all."""
    return _esc(email).replace("@", "@<wbr>").replace(".", ".<wbr>")


def _row_html(row, view):
    you = _pill(_t(_YOU), "you") if row.is_self else ""
    return (
        '<tr class="users-row%s" id="user-%d" data-quick-region>'
        '<th scope="row" class="users-cell users-cell--user">'
        '<span class="users-avatar" aria-hidden="true">%s</span>'
        '<span class="users-who"><span class="users-email" title="%s">%s</span>'
        '<span class="users-status">%s</span>'
        '<span class="users-pills">%s</span></span></th>'
        '<td class="users-cell users-cell--role">%s</td>'
        '<td class="users-cell users-cell--frames">%s</td>'
        '<td class="users-cell users-cell--seen">%s</td>'
        '<td class="users-cell users-cell--active">%s</td>'
        '<td class="users-cell users-cell--invite">%s</td>'
        '<td class="users-cell users-cell--menu">%s</td></tr>' % (
            " users-row--menu", row.user_id,
            _initial(row.email), _esc(row.email), _breakable(row.email), _status_pill(row), you,
            _role_cell(row), _frames_cell_html(row),
            _last_sign_in_html(row, view.now), _active_cell(row),
            _invite_cell(row, view.app_url), _menu_cell(row)))


def _table_html(view):
    head = "".join(
        '<th scope="col" class="users-col users-col--%s">%s</th>' % (
            name, _t(label) if name != "invite" else (
                '<span class="visually-hidden">%s</span>' % _t(label)))
        for name, label in (
            ("user", _COL_USER), ("role", _COL_ROLE), ("frames", _COL_FRAMES),
            ("seen", _COL_LAST_SIGN_IN), ("active", _COL_ACTIVE),
            ("invite", _COL_INVITATION)))
    return (
        '%s<table class="users-table"><caption class="visually-hidden">%s</caption>'
        '<thead><tr>%s<td class="users-col users-col--menu"></td></tr></thead>'
        '<tbody>%s</tbody></table>' % (
            ui_entity_list.count_line_html(_count_text(len(view.rows))),
            _t(_USERS_TEXT), head,
            "".join(_row_html(row, view) for row in view.rows)))



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
        'autocomplete="off" data-1p-ignore data-lpignore="true" data-bwignore="true" '
        'data-form-type="other" spellcheck="false" value="%s"%s%s>%s</div>'
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
        '<section class="users-section" aria-label="%s">%s</section>' % (
            _t(_USERS_TEXT), _table_html(view))
        + _invite_dialog(view)
        + _role_dialog(view)
        + "".join(_delete_dialog(row) for row in view.rows if not row.is_self))
