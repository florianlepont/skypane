"""The Users page body: every user with role, status and actions, and the
"Invite a user" card.

Pure markup: it takes a `UsersView` and reads nothing else. A row carries
display facts only; the issuer and subject of a linked identity, session
tokens and hashes never reach this module (`has_identity` is a boolean).
The guard states are shown by absence: the signed-in administrator's own row
and the last active administrator's row get no demote or disable control.
"""
import datetime
from typing import NamedTuple

from companion import i18n, ui_time
from companion.ui_base import escape_html

USERS_PURPOSE = i18n.msg(
    "admin_users.who_can_sign_in_and_what_they_can_do",
    "Who can sign in and what they can do.")

EMAIL_FIELD = "email"
ROLE_FIELD = "role"
ROLE_USER = "user"
ROLE_ADMIN = "admin"

STATUS_ACTIVE = "active"
STATUS_DISABLED = "disabled"
STATUS_INVITED = "invited"

_USERS_TEXT = i18n.msg("admin_users.users", "Users")
_COUNT_MANY = i18n.msg("admin_users.n_users", "%d users")
_COUNT_ONE = i18n.msg("admin_users.one_user", "1 user")
_COL_EMAIL = i18n.msg("admin_users.email", "Email")
_COL_ROLE = i18n.msg("admin_users.role", "Role")
_COL_STATUS = i18n.msg("admin_users.status", "Status")
_COL_FRAMES = i18n.msg("admin_users.frames", "Frames")
_COL_ACTIONS = i18n.msg("admin_users.actions", "Actions")
_SIGNED_IN = i18n.msg("admin_users.signed_in", "Signed in")
_NEVER_SIGNED_IN = i18n.msg("admin_users.never_signed_in", "Never signed in")
_ROLE_NAME_USER = i18n.msg("admin_users.role_user", "User")
_ROLE_NAME_ADMIN = i18n.msg("admin_users.role_administrator", "Administrator")
_STATUS_ACTIVE = i18n.msg("admin_users.status_active", "Active")
_STATUS_DISABLED = i18n.msg("admin_users.status_disabled", "Disabled")
_STATUS_INVITED = i18n.msg("admin_users.status_invited", "Invited")
_THIS_IS_YOU = i18n.msg("admin_users.this_is_you", "This is you.")
_LAST_ADMIN = i18n.msg(
    "admin_users.the_last_active_administrator_cannot_be_changed",
    "The last active administrator cannot be changed.")
_ROLE_LABEL = i18n.msg("admin_users.role_select_label", "Role")

_SAVE_ROLE = i18n.msg("admin_users.save_role", "Save role")
_DEMOTE_SUMMARY = i18n.msg("admin_users.change_to_user", "Change to User")
_DEMOTE_SENTENCE = i18n.msg(
    "admin_users.they_lose_access_to_the_console_and_to_other_users_frames",
    "They lose access to the console and to other users' frames.")
_DISABLE_SUMMARY = i18n.msg("admin_users.disable", "Disable")
_DISABLE_BUTTON = i18n.msg("admin_users.disable_user", "Disable user")
_DISABLE_SENTENCE = i18n.msg(
    "admin_users.they_are_signed_out_immediately_and_cannot_sign_in",
    "They are signed out immediately and cannot sign in.")
_ENABLE = i18n.msg("admin_users.enable", "Enable")
_UNLINK_SUMMARY = i18n.msg("admin_users.unlink_identity", "Unlink identity")
_UNLINK_SENTENCE = i18n.msg(
    "admin_users.they_will_need_to_sign_in_again_and_their_identity_will_be",
    "They will need to sign in again and their identity will be re-linked on "
    "next sign-in.")
_KEEP_USER = i18n.msg("admin_users.keep_user", "Keep user")

_INVITE_TITLE = i18n.msg("admin_users.invite_a_user", "Invite a user")
_INVITE_PURPOSE = i18n.msg(
    "admin_users.they_sign_in_with_this_email_through_auth0_skypane_does",
    "They sign in with this email through Auth0. SkyPane does not send them a message.")
_INVITE_SUBMIT = i18n.msg("admin_users.send_invitation", "Send invitation")
INVITE_EMAIL_ERROR = i18n.msg(
    "admin_users.enter_a_valid_email_address", "Enter a valid email address.")
INVITE_DUPLICATE_ERROR = i18n.msg(
    "admin_users.that_email_is_already_invited", "That email is already invited.")
INVITE_ROLE_ERROR = i18n.msg("admin_users.choose_a_role", "Choose a role.")


class UserRow(NamedTuple):
    """One user as the table shows it. `last_seen` is epoch seconds or None;
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


def role_name(role):
    return i18n.t(_ROLE_NAME_ADMIN if role == ROLE_ADMIN else _ROLE_NAME_USER)


def status_of(row):
    if row.disabled:
        return STATUS_DISABLED
    return STATUS_ACTIVE if row.has_identity else STATUS_INVITED


def _ui():
    # Imported on use: this page loads while the navigation is still importing.
    from companion import ui_components
    return ui_components


def _routes():
    # Imported on use: companion.console_routes imports the route modules.
    from companion import console_routes
    return console_routes


def _esc(value):
    return escape_html(value)


def _t(message):
    return _esc(i18n.t(message))


def _badge(label_html):
    return '<span class="banner__pill">%s</span>' % label_html


def _status_badge(row):
    label = {
        STATUS_ACTIVE: _STATUS_ACTIVE, STATUS_DISABLED: _STATUS_DISABLED,
        STATUS_INVITED: _STATUS_INVITED}[status_of(row)]
    return _badge(_t(label))


def _email_cell_html(row, now):
    if row.last_seen is None:
        second = _t(_NEVER_SIGNED_IN)
    else:
        seen = datetime.datetime.fromtimestamp(row.last_seen, datetime.timezone.utc)
        second = (
            '%s <span class="time-value">%s</span><span class="cell-inline-sep">·</span>'
            '<span class="time-value__age">(%s)</span>' % (
                _t(_SIGNED_IN),
                _esc(ui_time.local_clock_text(seen, now_parsed=now)),
                ui_time.relative_time_html(seen.isoformat(), now.isoformat())))
    return (
        '<span class="cell-primary text-heading">%s</span>'
        '<span class="cell-secondary">%s</span>' % (_esc(row.email), second))


def _action_path(row, suffix):
    return "%s%d%s" % (_routes().USER_ACTION_PREFIX, row.user_id, suffix)


def _confirm_html(row, suffix, summary, button, sentence, hidden_html=""):
    """The inline two-step confirm: a `<details>` whose summary is the quiet
    action, a consequence sentence, the submit and a keep-as-is link back to
    the page. No script, no dialog."""
    return (
        '<details class="fleet-confirm"><summary>%s</summary>'
        '<form method="post" action="%s" class="fleet-confirm__form">%s%s'
        '<p class="text-body">%s%s</p>'
        '<div class="update-actions">'
        '<button type="submit" class="calendar-disconnect-btn">%s</button>'
        '<a class="text-link" href="%s">%s</a></div></form></details>' % (
            _t(summary), _esc(_action_path(row, suffix)), _ui().csrf_field(),
            hidden_html, _ui().toast_icon_html("warning"), _t(sentence), _t(button),
            _esc(_routes().USERS_ROUTE), _t(_KEEP_USER)))


def _role_options(selected):
    return "".join(
        '<option value="%s"%s>%s</option>' % (
            value, " selected" if value == selected else "", _esc(role_name(value)))
        for value in (ROLE_USER, ROLE_ADMIN))


def _role_form_html(row, uid):
    select_id = "role-" + uid
    return (
        '<form method="post" action="%s" class="fleet-form">%s'
        '<label class="visually-hidden" for="%s">%s</label>'
        '<select id="%s" name="%s">%s</select>'
        '<div class="update-actions">'
        '<button type="submit" class="calendar-disconnect-btn">%s</button></div></form>' % (
            _esc(_action_path(row, _routes().USER_ROLE_SUFFIX)), _ui().csrf_field(),
            select_id, _t(_ROLE_LABEL), select_id, ROLE_FIELD, _role_options(row.role),
            _t(_SAVE_ROLE)))


def _demote_html(row):
    hidden = '<input type="hidden" name="%s" value="%s">' % (ROLE_FIELD, ROLE_USER)
    return _confirm_html(
        row, _routes().USER_ROLE_SUFFIX, _DEMOTE_SUMMARY, _DEMOTE_SUMMARY,
        _DEMOTE_SENTENCE, hidden)


def _role_cell_html(row, uid):
    """The badge, plus the role control when the guards allow a change."""
    badge = _badge(_esc(role_name(row.role)))
    notes = ""
    if row.is_self:
        notes += '<p class="text-label">%s</p>' % _t(_THIS_IS_YOU)
    if row.is_last_admin:
        notes += '<p class="text-label">%s</p>' % _t(_LAST_ADMIN)
    if notes:
        return badge + notes
    if row.role == ROLE_ADMIN:
        return badge + _demote_html(row)
    return badge + _role_form_html(row, uid)


def _enable_html(row):
    return (
        '<form method="post" action="%s" class="fleet-form">%s'
        '<div class="update-actions">'
        '<button type="submit" class="calendar-disconnect-btn">%s</button></div></form>' % (
            _esc(_action_path(row, _routes().USER_ENABLE_SUFFIX)), _ui().csrf_field(),
            _t(_ENABLE)))


def _actions_html(row):
    parts = []
    guarded = row.is_self or row.is_last_admin
    if row.disabled:
        parts.append(_enable_html(row))
    elif not guarded:
        parts.append(_confirm_html(
            row, _routes().USER_DISABLE_SUFFIX, _DISABLE_SUMMARY, _DISABLE_BUTTON,
            _DISABLE_SENTENCE))
    if row.has_identity:
        parts.append(_confirm_html(
            row, _routes().USER_UNLINK_SUFFIX, _UNLINK_SUMMARY, _UNLINK_SUMMARY,
            _UNLINK_SENTENCE))
    return '<div class="fleet-actions">%s</div>' % "".join(parts) if parts else ""


def _table_row_html(row, view):
    uid = "t-%d" % row.user_id
    return (
        '<tr data-user="%d" data-status="%s"><td>%s</td><td>%s</td><td>%s</td>'
        '<td>%d</td><td>%s</td></tr>' % (
            row.user_id, status_of(row), _email_cell_html(row, view.now),
            _role_cell_html(row, uid), _status_badge(row), row.frame_count,
            _actions_html(row)))


def _pair_label(label, value_html):
    return (
        '<span class="data-card__label">%s</span> '
        '<span class="data-card__value">%s</span>' % (_t(label), value_html))


def _card_row_html(row, view):
    uid = "c-%d" % row.user_id
    return (
        '<li class="data-card" data-user="%d" data-status="%s">'
        '<div class="data-card__primary"><span>%s</span><span>%s</span></div>'
        '<div class="data-card__secondary">%s</div>'
        '<div class="data-card__secondary">%s</div>'
        '<div class="data-card__action">%s</div></li>' % (
            row.user_id, status_of(row), _email_cell_html(row, view.now),
            _status_badge(row), _pair_label(_COL_ROLE, _role_cell_html(row, uid)),
            _pair_label(_COL_FRAMES, str(row.frame_count)), _actions_html(row)))


def _table_html(view):
    heads = "".join("<th>%s</th>" % _t(label) for label in (
        _COL_EMAIL, _COL_ROLE, _COL_STATUS, _COL_FRAMES, _COL_ACTIONS))
    body = "".join(_table_row_html(row, view) for row in view.rows)
    cards = "".join(_card_row_html(row, view) for row in view.rows)
    # The cards come first: style.css hides the table behind
    # `.data-cards ~ .data-table-wrap` below 960px by sibling order.
    return (
        '<ul class="data-cards">%s</ul>'
        '<div class="data-table-wrap"><table class="data-table data-table--users">'
        "<thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>" % (cards, heads, body))


def _count_html(count):
    text = i18n.t(_COUNT_ONE) if count == 1 else i18n.t(_COUNT_MANY) % count
    return '<p class="filter-bar__count" role="status">%s</p>' % _esc(text)


def _card(heading_id, heading, inner_html, purpose=None):
    purpose_html = (
        '<p class="text-body section-caption">%s</p>' % _t(purpose) if purpose else "")
    return (
        '<section class="page-section page-section--nested" '
        'aria-labelledby="%s"><h2 class="text-heading" id="%s">%s</h2>%s%s</section>'
        % (heading_id, heading_id, _t(heading), purpose_html, inner_html))


def _field_error(field_id, message):
    if not message:
        return "", ""
    return (
        ' aria-invalid="true" aria-describedby="%s-error"' % field_id,
        '<p class="field-error" id="%s-error">%s</p>' % (field_id, _esc(message)))


def _invite_card(view):
    email_attrs, email_error = _field_error("invite-email", view.email_error)
    role_attrs, role_error = _field_error("invite-role", view.role_error)
    form = (
        '<form method="post" action="%s" class="fleet-form" autocomplete="off">%s'
        '<p><label for="invite-email">%s</label>'
        '<input type="email" id="invite-email" name="%s" required maxlength="254" '
        'autocomplete="off" spellcheck="false" value="%s"%s>%s</p>'
        '<p><label for="invite-role">%s</label>'
        '<select id="invite-role" name="%s"%s>%s</select>%s</p>'
        '<div class="update-actions"><button type="submit">%s</button></div></form>' % (
            _esc(_routes().USERS_INVITE_ROUTE), _ui().csrf_field(),
            _t(_COL_EMAIL), EMAIL_FIELD, _esc(view.email_value), email_attrs, email_error,
            _t(_COL_ROLE), ROLE_FIELD, role_attrs, _role_options(view.role_selected),
            role_error, _t(_INVITE_SUBMIT)))
    return _card("users-invite", _INVITE_TITLE, form, _INVITE_PURPOSE)


def _users_card(view):
    inner = _count_html(len(view.rows)) + _table_html(view)
    return _card("users-list", _USERS_TEXT, inner)


def render(view):
    """The Users page body (the shell supplies the header and sub-nav)."""
    return _users_card(view) + _invite_card(view)
