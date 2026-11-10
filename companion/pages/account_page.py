"""The Account page body: the caller's own frames first, then who is signed
in and the browser preferences. Pure markup: it takes the signed-in identity
and a sequence of the caller's own frame summaries as arguments and reads
nothing else, so it carries no other account's frame and no MAC, token,
firmware version or device id beyond the frame's own address and the forms of
its dialogs. A frame shows no battery or last-contact figure, only its status
dot.
"""
import time
from typing import NamedTuple

from companion import frame_status, i18n, layout, prefs, ui_groups, ui_modal, ui_shell
from companion.pages import co_managers_card, pair_frame_page

ACCOUNT_TITLE = i18n.msg("account.account", "Account")
ACCOUNT_PURPOSE = i18n.msg(
    "account.your_skypane_sign_in_and_preferences",
    "Your SkyPane sign-in and preferences.")
_IDENTITY_TEXT = i18n.msg("account.identity", "Identity")
_EMAIL_TEXT = i18n.msg("account.email", "Email")
_ROLE_TEXT = i18n.msg("account.role", "Role")
_ROLE_USER_TEXT = i18n.msg("account.user", "User")
_ROLE_ADMIN_TEXT = i18n.msg("account.administrator", "Administrator")
_PREFERENCES_TEXT = i18n.msg("account.preferences", "Preferences")
_LANGUAGE_TEXT = i18n.msg("account.language", "Language")
_LANGUAGE_HINT = i18n.msg(
    "account.language_hint", "The language of the companion pages.")
_THEME_TEXT = i18n.msg("account.theme", "Theme")
_THEME_HINT = i18n.msg(
    "account.theme_hint", "Light, dark, or follow the system.")
_MY_FRAMES_TEXT = i18n.msg("account.my_frames", "My frames")
UNNAMED_FRAME_TEXT = i18n.msg("account.unnamed_frame", "Unnamed frame")
_SHARED_BY_TEXT = i18n.msg("account.shared_by", "Shared by %s")
_LEAVE_FRAME_TEXT = i18n.msg("account.leave_frame", "Leave frame")
_LEAVE_FRAME_ARIA = i18n.msg("account.leave_frame_aria", "Leave frame: %s")
_MANAGE_ACCESS_ARIA = i18n.msg("account.manage_access_aria", "Manage access: %s")
_PILL_OWNER_TEXT = i18n.msg("account.frame_owner", "Owner")
_PILL_CO_MANAGER_TEXT = i18n.msg("account.frame_co_manager", "Co-manager")
_CO_MANAGER_OF_ONE_TEXT = i18n.msg("account.co_manager_of_one", "Co-manager of 1 frame")
_CO_MANAGER_OF_MANY_TEXT = i18n.msg("account.co_manager_of_many", "Co-manager of %d frames")
_SIGN_OUT_TEXT = i18n.msg("common.sign_out", "Sign out")

ROLE_USER = "user"
ROLE_ADMIN = "admin"


class Identity(NamedTuple):
    """What the page shows about the signed-in person: the email, the
    role ("user" or "admin")."""
    email: str
    role: str


class FrameSummary(NamedTuple):
    """One of the caller's own frames as the page shows it: the name, the
    hardware label, the address of its Home and the frame id the dialogs post
    to. `last_seen` (epoch seconds, None when never), `battery_percent`,
    `offline`, `state` and `screen_off` only feed the status dot. A frame the
    caller co-manages is `shared` and carries its owner's address in
    `owner_email`; an owned frame carries the Manage access dialog's view in
    `access` (None when there is nothing to offer)."""
    name: str
    hardware: str
    href: str
    device_id: str
    last_seen: float | None = None
    battery_percent: int | None = None
    offline: bool = False
    state: str | None = None
    screen_off: bool = False
    shared: bool = False
    owner_email: str = ""
    access: co_managers_card.CardView | None = None


def _role_text(identity):
    return _ROLE_ADMIN_TEXT if identity.role == ROLE_ADMIN else _ROLE_USER_TEXT


def _preference_row(label, hint, control_html):
    """One labelled preference as a row: its name and a one-line hint, then
    a segmented control sized to its content as the trailing control (it
    drops under the text when the row is too narrow for both)."""
    return ui_groups.row(
        i18n.t(label), detail=i18n.t(hint), trailing_html=control_html,
        extra_class="pref-row")


def _value_row(label, value):
    """A row that only shows a value; a long value ellipsises and keeps its
    full text as the tooltip."""
    return ui_groups.row(
        i18n.t(label),
        value_html='<span title="%s">%s</span>' % (
            layout.escape_html(value), layout.escape_html(value)))


def _role_row(identity, frames):
    """The Role row: the role, and under it how many frames the person
    co-manages when there are any (a plain User is often a co-manager)."""
    shared = sum(1 for frame in frames if frame.shared)
    detail = ""
    if shared:
        detail = i18n.t(_CO_MANAGER_OF_ONE_TEXT if shared == 1 else _CO_MANAGER_OF_MANY_TEXT)
        detail = detail % shared if shared > 1 else detail
    role = i18n.t(_role_text(identity))
    return ui_groups.row(
        i18n.t(_ROLE_TEXT), detail=detail,
        value_html='<span title="%s">%s</span>' % (
            layout.escape_html(role), layout.escape_html(role)))


def _frame_action_html(frame):
    """The one 44px action of a frame row: Manage access on an owned frame,
    Leave frame on a shared one; nothing when an owned frame has no view."""
    if frame.shared:
        return ui_modal.trigger_html(
            co_managers_card.leave_dialog_id(frame.device_id),
            layout.escape_html(i18n.t(_LEAVE_FRAME_TEXT)), "account-frame__action",
            i18n.t(_LEAVE_FRAME_ARIA) % frame.name)
    if frame.access is None:
        return ""
    return ui_modal.trigger_html(
        co_managers_card.access_dialog_id(frame.device_id),
        layout.escape_html(i18n.t(co_managers_card.MENU_LABEL)), "account-frame__action",
        i18n.t(_MANAGE_ACCESS_ARIA) % frame.name)


def _frame_line(frame, show_hardware):
    """The muted second line: who shared the frame, else its hardware (an
    administrator's detail; a person has no use for the model)."""
    if frame.shared:
        return i18n.t(_SHARED_BY_TEXT) % frame.owner_email
    return frame.hardware if show_hardware else ""


def _frame_detail_html(frame, now, show_hardware):
    """The row's detail: the hardware (or who shared the frame), then the
    status dot with the last-seen word."""
    line = _frame_line(frame, show_hardware)
    return (
        '%s<span class="account-frame__status">%s<span>%s</span></span>' % (
            '<span class="account-frame__line">%s</span>' % layout.escape_html(line)
            if line else "",
            frame_status.status_dot_html(frame),
            layout.escape_html(ui_shell.seen_text(frame, now))))


def _frame_row_html(frame, now, show_hardware):
    """One frame: the drawn frame, its name, hardware and status, a chevron to
    the frame's Home, and its one action (Manage access or Leave frame) as a
    link line under the text."""
    pill = i18n.t(_PILL_CO_MANAGER_TEXT if frame.shared else _PILL_OWNER_TEXT)
    action_html = _frame_action_html(frame)
    # One affordance per row: the row itself opens the frame's Home, and a row
    # that also carries an action link shows no chevron beside it.
    return ui_groups.row(
        label_html='%s <span class="banner__pill account-frame__role">%s</span>' % (
            layout.escape_html(frame.name), layout.escape_html(pill)),
        lead_html=ui_shell.frame_pic_html("account-frame"),
        detail_html=_frame_detail_html(frame, now, show_hardware), href=frame.href,
        trailing_html=action_html, chevron=not action_html, extra_class="account-frame")


def _frame_dialog_html(frame, open_access):
    """The dialog behind a row's action: Manage access (reopened when
    `open_access` is this frame's id) or Leave this frame."""
    if frame.shared:
        return co_managers_card.leave_dialog_html(
            frame.device_id, frame.name, co_managers_card.RETURN_ACCOUNT)
    if frame.access is None:
        return ""
    return co_managers_card.manage_access_dialog_html(
        frame.access, frame.device_id, frame.name, co_managers_card.RETURN_ACCOUNT,
        open_=frame.device_id == open_access)


def _frames_card(frames, open_access, now, show_hardware):
    """The My frames group: the empty state with no frames, else one row per
    frame ordered by name, then the Add a frame row, followed by the row
    dialogs."""
    if not frames:
        return ui_groups.group_panel(
            pair_frame_page.empty_state_html(), label=i18n.t(_MY_FRAMES_TEXT),
            label_id="account-frames")
    rows = sorted(frames, key=lambda frame: (frame.name.casefold(), frame.href))
    add_row = ui_groups.row(
        i18n.t(pair_frame_page.ADD_LINK_TEXT), icon="icon-plus",
        href=pair_frame_page.PAIR_FRAME_ROUTE, extra_class="account-add-frame")
    return ui_groups.group(
        "".join(_frame_row_html(f, now, show_hardware) for f in rows) + add_row,
        label=i18n.t(_MY_FRAMES_TEXT), label_id="account-frames"
    ) + "".join(_frame_dialog_html(f, open_access) for f in rows)


def render(identity, ui_theme="auto", frames=(), open_access="", now=None):
    """The Account page body for `identity`, listing `frames` (the caller's
    own `FrameSummary` values). `open_access` is the id of the frame whose
    Manage access dialog renders open; `now` (epoch seconds) dates the
    last-seen words."""
    frames = tuple(frames)
    identity_html = (
        _value_row(_EMAIL_TEXT, identity.email)
        + _role_row(identity, frames))
    resolved_theme = ui_theme if ui_theme in layout.UI_THEME_CHOICES else "auto"
    preferences_html = (
        _preference_row(
            _LANGUAGE_TEXT, _LANGUAGE_HINT, layout._lang_form_html(prefs.current_lang()))
        + _preference_row(
            _THEME_TEXT, _THEME_HINT, layout._theme_form_html(resolved_theme)))
    sign_out_html = ui_groups.group(
        '<li class="row row--action row--danger">'
        '<form method="post" action="/logout" class="logout-form account-sign-out">'
        '<button type="submit" class="row__main">%s</button></form></li>'
        % layout.escape_html(i18n.t(_SIGN_OUT_TEXT)),
        extra_class="account-sign-out-group")
    return (
        layout.page_header(i18n.t(ACCOUNT_TITLE), purpose=i18n.t(ACCOUNT_PURPOSE))
        + _frames_card(
            frames, open_access, time.time() if now is None else now,
            identity.role == ROLE_ADMIN)
        + ui_groups.group(
            identity_html, label=i18n.t(_IDENTITY_TEXT), label_id="account-identity",
            extra_class="account-identity")
        + ui_groups.group(
            preferences_html, label=i18n.t(_PREFERENCES_TEXT), label_id="account-preferences")
        + sign_out_html)
