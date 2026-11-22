"""The Users page body: every user as one table row (email, a role select that
saves on change, frame count, last sign-in, an Active switch and a "..." menu
of rare actions; a card on a phone) plus the invite dialog the header button
opens, the invitation dialog that shows a new link once and the confirmations
of a role change and a deletion.

Pure markup: it takes a `UsersView` and reads nothing else. A row carries
display facts only; the issuer and subject of a linked identity, session
tokens and hashes never reach this module (`has_identity` is a boolean).
The guard states are sentences shown in place of the role select, with the
Active switch locked, for the signed-in administrator and for the last active
administrator.
"""
import dataclasses
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
_COPIED = i18n.msg("admin_users.copied", "Copied")
_COL_EMAIL = i18n.msg("admin_users.email", "Email address")
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
    "%s is removed from SkyPane and loses access to their frames. This cannot "
    "be undone.")
_RENEW_BUTTON = i18n.msg("admin_users.send_new_invitation", "Send a new invitation")

_INVITE_BUTTON = i18n.msg("admin_users.invite_a_user_button", "+ Invite a user")
_INVITE_TITLE = i18n.msg("admin_users.invite_a_user", "Invite a user")
_CANCEL = i18n.msg("admin_users.cancel", "Cancel")
_INVITE_SUBMIT = i18n.msg("admin_users.invite_user", "Invite")
_DONE = i18n.msg("admin_users.done", "Done")
_COPY = i18n.msg("admin_users.copy", "Copy")
_READY_TITLE = i18n.msg("admin_users.invitation_ready", "Invitation ready")
_READY_SEND_TO = i18n.msg("admin_users.send_this_link_to", "Send this link to %s")
_READY_HINT = i18n.msg(
    "admin_users.invitation_hint",
    "It is shown only once. Treat it as a secret: it expires in {ttl}. They "
    "choose their password, then open {url} and sign in.")
_READY_HINT_NO_URL = i18n.msg(
    "admin_users.invitation_hint_no_url",
    "It is shown only once. Treat it as a secret: it expires in {ttl}. They "
    "choose their password, then open the app and sign in.")
_TTL_DAYS = i18n.msg("admin_users.ttl_days", "%d days")
_TTL_HOURS = i18n.msg("admin_users.ttl_hours", "%d hours")
_LINK_MESSAGE = i18n.msg(
    "admin_users.invitation_link_message",
    "Hello, you have been invited to SkyPane. Open this link to choose your "
    "password (it expires in {ttl}): {link} Then open {url} and sign in with "
    "{email}.")
_LINK_MESSAGE_NO_URL = i18n.msg(
    "admin_users.invitation_link_message_no_url",
    "Hello, you have been invited to SkyPane. Open this link to choose your "
    "password (it expires in {ttl}): {link} Then open the app and sign in "
    "with {email}.")
_FAILED_TITLE = i18n.msg(
    "admin_users.invitation_not_created", "Invitation link not created")
_FAILED_LEAD = i18n.msg(
    "admin_users.invitation_not_created_lead",
    "%s is invited, but no invitation link was created.")
_FAILED_RETRY = i18n.msg("admin_users.try_again", "Try again")
FAIL_BUSY = "busy"
FAIL_GENERIC = "generic"
FAIL_NOT_SET_UP = "not_set_up"
FAIL_CONNECTION_ID = "connection_id"
_FAILED_REASON = {
    FAIL_BUSY: i18n.msg(
        "admin_users.invitation_failed_busy",
        "The sign-in service is busy. Try again in a moment."),
    FAIL_GENERIC: i18n.msg(
        "admin_users.invitation_failed_generic",
        "The sign-in service did not accept the request. Try again; if it "
        "keeps failing, check the Auth0 settings on the server."),
    FAIL_NOT_SET_UP: i18n.msg(
        "admin_users.invitation_failed_not_set_up",
        "Automatic invitations are not set up on this server. Create their "
        "account in Auth0 by hand."),
    FAIL_CONNECTION_ID: i18n.msg(
        "admin_users.invitation_failed_connection_id",
        "A new invitation for someone who already has an Auth0 account needs "
        "the Auth0 connection id on the server (SKYPANE_AUTH0_DB_CONNECTION_ID). "
        "See the deployment guide."),
}
# Trying again changes nothing for these two: the server needs its settings
# completed first.
_NO_RETRY = (FAIL_NOT_SET_UP, FAIL_CONNECTION_ID)
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


@dataclasses.dataclass(frozen=True)
class Invitation:
    """A link just created for `email`, valid for `ttl_sec` seconds. The link
    is a one-time credential: it is rendered once into the response that
    made it and held nowhere else, and it never appears in a repr."""
    email: str
    link: str = dataclasses.field(repr=False)
    ttl_sec: int


@dataclasses.dataclass(frozen=True)
class InviteFailure:
    """A person invited locally for whom no link could be made; `kind` is
    one of the FAIL_ constants."""
    email: str
    kind: str


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
    invitation: Invitation | None = None
    invite_failure: InviteFailure | None = None


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


def _pill(text, tone, attrs=""):
    """A status or "You" badge, built by the catalogue's pill helper (the
    text is escaped there)."""
    return _ui().pill_html(text, None, "users-pill users-pill--" + tone, attrs=attrs)


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
        _pill(i18n.t(_STATUS_LABELS[enabled]), enabled,
              (" hidden" if off else "") + " data-quick-state-on" + help_attrs)
        + _pill(i18n.t(_STATUS_DISABLED), STATUS_DISABLED,
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
    """The role select, drawn as a bordered chip with a chevron, that sends
    its form on change (a Save button shows only without script) and lands on
    the confirmation dialog, or the plain role for the signed-in administrator
    and the last active administrator (their guard sentences sit in the
    person's cell, which every layout shows)."""
    if row.is_self or row.is_last_admin:
        # The explanation is a tooltip and a hidden description of the role,
        # not text in the cell: the "You" pill already marks the row.
        explained = " ".join(
            _t(note) for flag, note in (
                (row.is_self, _SELF_LOCK), (row.is_last_admin, _LAST_ADMIN)) if flag)
        return '<span class="users-role-fixed" title="%s">%s</span>' % (
            explained, _esc(role_name(row.role)))
    select_id = "role-%d" % row.user_id
    controls = (
        '<label class="visually-hidden" for="%s">%s</label>'
        '<span class="users-role-chip"><select id="%s" name="%s" data-autosubmit>%s</select>'
        '%s</span>'
        '<noscript><button type="submit" class="users-role-save">%s</button></noscript>' % (
            select_id, _esc(i18n.t(_ROLE_OF_ARIA) % row.email), select_id, ROLE_FIELD,
            _role_options(row.role), icon_html("icon-chevron-down", size=16),
            _t(_SAVE_ROLE)))
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
    body = '<p class="modal__note">%s</p>' % _esc(i18n.t(_DELETE_WHAT) % row.email)
    return ui_modal.dialog_html(
        delete_dialog_id(row), i18n.t(_DELETE_TITLE),
        _action_path(row, _routes().USER_DELETE_SUFFIX),
        _ui().csrf_field(), body, i18n.t(_DELETE_BUTTON), i18n.t(_DELETE_KEEP),
        _routes().USERS_ROUTE, destructive=True, confirm_only=True,
        variant="compact")


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
    body = '<p class="modal__note">%s</p>' % _esc(i18n.t(what) % row.email)
    return ui_modal.dialog_html(
        role_dialog_id(user_id), i18n.t(title),
        _action_path(row, _routes().USER_ROLE_SUFFIX),
        _ui().csrf_field() + fields, body, i18n.t(submit), i18n.t(keep),
        _routes().USERS_ROUTE, destructive=not promote, confirm_only=True,
        open_=True, return_on_close=True, variant="compact",
        return_focus_id="role-%d users-menu-%d" % (user_id, user_id))


# A paper plane for "Send a new invitation", drawn inline: a new sprite symbol would change
# the markup of every page.
_SEND_ICON = (
    '<svg class="icon" width="20" height="20" viewBox="0 0 20 20" aria-hidden="true" '
    'focusable="false" fill="none" stroke="currentColor" stroke-width="1.6" '
    'stroke-linecap="round" stroke-linejoin="round"><path d="M2.5 9l15-6.5-6.5 15-2-6.5z"/></svg>')


def _renew_form(row):
    """The menu item that asks for a new invitation link: the invite form
    with this person's address (the same route, no new one)."""
    return (
        '<form method="post" action="%s" class="users-menu__form">%s'
        '<input type="hidden" name="%s" value="%s">'
        '<button type="submit" class="row-menu__item">%s%s</button></form>' % (
            _esc(_routes().USERS_INVITE_ROUTE), _ui().csrf_field(), EMAIL_FIELD,
            _esc(row.email), _SEND_ICON, _t(_RENEW_BUTTON)))


def _role_menu_item(row):
    """The menu item that changes the role where the table's select is not
    shown (a phone card): it posts the other role without the confirmed mark,
    so it lands on the same confirmation dialog as the select. None for the
    two rows whose role is locked."""
    if row.is_self or row.is_last_admin:
        return ""
    promote = row.role != ROLE_ADMIN
    return _post_form(
        row, _routes().USER_ROLE_SUFFIX, "users-menu__form users-menu__role",
        '<input type="hidden" name="%s" value="%s">'
        '<button type="submit" class="row-menu__item">%s</button>' % (
            ROLE_FIELD, ROLE_ADMIN if promote else ROLE_USER,
            _t(_PROMOTE_SUBMIT if promote else _DEMOTE_SUBMIT)))


def _menu_cell(row):
    """The "..." menu: Send a new invitation to a person who has not signed
    in yet, the role change (phone cards only), Reset sign-in for one who has,
    then Delete user, which opens its confirmation. The signed-in administrator's own row offers no Delete
    (the server refuses it), and no menu at all when nothing else is left."""
    items = _renew_form(row) if status_of(row) == STATUS_INVITED else ""
    items += _role_menu_item(row)
    if row.has_identity:
        items += _post_form(
            row, _routes().USER_UNLINK_SUFFIX, "users-menu__form",
            '<button type="submit" class="row-menu__item row-menu__item--destructive" '
            'title="%s">%s</button>' % (_t(_UNLINK_HINT), _t(_UNLINK_BUTTON)))
    if not row.is_self:
        items += ui_modal.trigger_html(
            delete_dialog_id(row),
            icon_html("icon-toast-trash") + _t(_DELETE_BUTTON),
            "row-menu__item row-menu__item--destructive")
    if not items:
        return ""
    return (
        '<details class="row-menu"><summary class="row-menu__toggle" id="users-menu-%d" '
        'aria-label="%s">%s</summary><div class="row-menu__panel">%s</div></details>' % (
            row.user_id, _esc(i18n.t(_MORE_ARIA) % row.email),
            icon_html("icon-more-vertical", size=20), items))


def _breakable(email):
    """The address escaped, with a break opportunity after each "@" and ".":
    a narrow phone card wraps it there and never inside a word. Wider layouts
    keep it on one line and end it with an ellipsis; the title holds it all."""
    return _esc(email).replace("@", "@<wbr>").replace(".", ".<wbr>")


def _row_html(row, view):
    you = _pill(i18n.t(_YOU), "you") if row.is_self else ""
    return (
        '<tr class="users-row%s" id="user-%d" data-quick-region>'
        '<th scope="row" class="users-cell users-cell--user">'
        '<span class="users-avatar" aria-hidden="true">%s</span>'
        '<span class="users-who"><span class="users-email" title="%s">%s</span>'
        '<span class="users-status">%s</span>'
        '<span class="users-pills">%s</span>'
        '<span class="users-meta">%s \u00b7 %s</span>%s</span></th>'
        '<td class="users-cell users-cell--role">%s</td>'
        '<td class="users-cell users-cell--frames">%s</td>'
        '<td class="users-cell users-cell--seen">%s</td>'
        '<td class="users-cell users-cell--active">%s</td>'
        '<td class="users-cell users-cell--menu">%s</td></tr>' % (
            " users-row--menu", row.user_id,
            _initial(row.email), _esc(row.email), _breakable(row.email), _status_pill(row), you,
            _esc(role_name(row.role)), _frames_cell_html(row), _guard_html(row),
            _role_cell(row), _frames_cell_html(row),
            _last_sign_in_html(row, view.now), _active_cell(row), _menu_cell(row)))


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
        '<div class="modal__field"><label for="invite-email">%s</label>'
        '<input type="email" id="invite-email" name="%s" required maxlength="254" '
        'autocomplete="off" data-1p-ignore data-lpignore="true" data-bwignore="true" '
        'data-form-type="other" spellcheck="false" placeholder="name@example.com" '
        'value="%s"%s%s>%s</div>'
        '<div><label class="modal__check" for="invite-role">'
        '<input type="checkbox" id="invite-role" name="%s" value="%s"%s%s>'
        '<span class="modal__check-box" aria-hidden="true"></span>%s</label>%s</div>' % (
            _t(_COL_EMAIL), EMAIL_FIELD, _esc(view.email_value), email_attrs,
            ui_base.validation_attrs("email"), email_error, ROLE_FIELD, ROLE_ADMIN,
            " checked" if view.role_selected == ROLE_ADMIN else "", role_attrs,
            _t(_ROLE_NAME_ADMIN), role_error))
    return ui_modal.dialog_html(
        INVITE_DIALOG_ID, i18n.t(_INVITE_TITLE), _routes().USERS_INVITE_ROUTE,
        _ui().csrf_field(), body, i18n.t(_INVITE_SUBMIT), i18n.t(_CANCEL),
        _routes().USERS_ROUTE, open_=view.open_invite_dialog, variant="compact-top")


def ttl_text(ttl_sec):
    """A link lifetime in words: whole days from two days up, else hours."""
    if ttl_sec >= 2 * 86400 and ttl_sec % 86400 == 0:
        return i18n.t(_TTL_DAYS) % (ttl_sec // 86400)
    return i18n.t(_TTL_HOURS) % max(1, ttl_sec // 3600)


def invitation_message(invitation, app_url):
    """What the administrator sends: the link, how long it lasts, the
    address to open afterwards and the e-mail to sign in with. The link is a
    secret, so this text is built for the one response that shows it."""
    template = _LINK_MESSAGE if app_url else _LINK_MESSAGE_NO_URL
    return i18n.t(template).format(
        link=invitation.link, ttl=ttl_text(invitation.ttl_sec), url=app_url,
        email=invitation.email)


def _invitation_dialog(invitation, app_url):
    """The invitation, shown once: the link in a strip with its Copy button
    (the button copies the whole message), and how long it lasts. The link is
    text, not an anchor: opening it would use it up."""
    hint = (_READY_HINT if app_url else _READY_HINT_NO_URL)
    body = (
        '<p>%s</p><div class="modal__linkbox"><code>%s</code>'
        '<button type="button" class="btn btn--primary" data-copy-value="%s" '
        'data-copied-text="%s">%s<span class="copy-btn__label">%s</span></button>'
        '<span class="visually-hidden" role="status" data-copy-feedback></span></div>'
        '<p class="modal__note">%s</p>' % (
            _esc(i18n.t(_READY_SEND_TO)) % ("<strong>%s</strong>" % _esc(invitation.email)),
            _esc(invitation.link), _esc(invitation_message(invitation, app_url)),
            _t(_COPIED), icon_html("icon-copy"), _t(_COPY),
            _esc(i18n.t(hint).format(
                ttl=ttl_text(invitation.ttl_sec), url=app_url))))
    return ui_modal.result_dialog_html(
        "dlg-invitation-ready", i18n.t(_READY_TITLE), body, i18n.t(_DONE),
        _routes().USERS_ROUTE, once=True)


def _failure_dialog(failure):
    """No link could be made: the person stays invited, and the dialog says
    why in a sentence (never a provider message) and, where trying again can
    help, offers to."""
    body = '<p class="modal__note">%s %s</p>' % (
        _esc(i18n.t(_FAILED_LEAD) % failure.email),
        _t(_FAILED_REASON[failure.kind]))
    retry = ""
    if failure.kind not in _NO_RETRY:
        retry = (
            '<form method="post" action="%s">%s<input type="hidden" name="%s" '
            'value="%s"><button type="submit" class="btn btn--primary">%s</button></form>'
            % (_esc(_routes().USERS_INVITE_ROUTE), _ui().csrf_field(), EMAIL_FIELD,
               _esc(failure.email), _t(_FAILED_RETRY)))
    return ui_modal.result_dialog_html(
        "dlg-invitation-failed", i18n.t(_FAILED_TITLE), body, i18n.t(_DONE),
        _routes().USERS_ROUTE, retry_form_html=retry)


def _result_dialog(view):
    if view.invitation is not None:
        return _invitation_dialog(view.invitation, view.app_url)
    if view.invite_failure is not None:
        return _failure_dialog(view.invite_failure)
    return ""


def header_action_html():
    """The page header's invite trigger (opens the invite dialog): the words on
    a wide screen, a square plus button on a phone."""
    # A phone shows the plus alone in a square button; the words stay in the
    # markup as the accessible name.
    trigger = ui_modal.trigger_html(
        INVITE_DIALOG_ID,
        '<span class="page-header__action-icon" aria-hidden="true">%s</span>'
        '<span class="page-header__action-label">%s</span>' % (
            icon_html("icon-plus"), _t(_INVITE_BUTTON)),
        "page-header__action")
    return '<div class="page-header__actions">%s</div>' % trigger


def render(view):
    """The Users page body (the shell supplies the header and nav)."""
    return (
        '<section class="users-section" aria-label="%s">%s</section>' % (
            _t(_USERS_TEXT), _table_html(view))
        + _invite_dialog(view)
        + _result_dialog(view)
        + _role_dialog(view)
        + "".join(_delete_dialog(row) for row in view.rows if not row.is_self))
