"""The Account page body: the caller's own frames first, then who is signed
in and the browser preferences. Pure markup: it takes the signed-in identity
and a sequence of the caller's own frame summaries as arguments and reads
nothing else, so it carries no other account's frame and no MAC, token,
firmware version or device id beyond the frame's own address and the forms of
its dialogs. A frame shows no battery, hardware or last-contact figure, only its status
dot and the last-seen word.
"""
import time
from typing import NamedTuple

from companion import build_info, frame_status, i18n, layout, prefs, ui_components, ui_groups, ui_modal, ui_shell
from companion.pages import co_managers_card, frame_name_page, pair_frame_page

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
_LEAVE_FRAME_ARIA = i18n.msg("account.leave_frame_aria", "Leave frame: %s")
_MANAGE_ACCESS_ARIA = i18n.msg("account.manage_access_aria", "Manage access: %s")
_RENAME_FRAME_ARIA = i18n.msg("account.rename_frame_aria", "Rename: %s")
_PILL_OWNER_TEXT = i18n.msg("account.frame_owner", "Owner")
_PILL_CO_MANAGER_TEXT = i18n.msg("account.frame_co_manager", "Co-manager")
_CO_MANAGER_OF_ONE_TEXT = i18n.msg("account.co_manager_of_one", "Co-manager of 1 frame")
_CO_MANAGER_OF_MANY_TEXT = i18n.msg("account.co_manager_of_many", "Co-manager of %d frames")
_SIGN_OUT_TEXT = i18n.msg("common.sign_out", "Sign out")
_CREDITS_TEXT = i18n.msg("credits.credits", "Credits")
_ABOUT_TEXT = i18n.msg("account.about", "About")
_CREDITS_ROW_DETAIL = i18n.msg("account.credits_detail", "Data sources and licences")
_BUILD_LINE = i18n.msg("account.build_line", "SkyPane build %s")
_BUILD_HINT = i18n.msg("account.build_hint", "Tap to copy for support")
_BUILD_COPIED = i18n.msg("account.build_copied", "Copied")
CREDITS_ROUTE = "/credits"

ROLE_USER = "user"
ROLE_ADMIN = "admin"


class Identity(NamedTuple):
    """What the page shows about the signed-in person: the email, the
    role ("user" or "admin")."""
    email: str
    role: str


class FrameSummary(NamedTuple):
    """One of the caller's own frames as the page shows it: the name, the
    hardware label (not shown), the address of its Home and the frame id the dialogs post
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
    """The actions of a frame row, 44px icon buttons named for assistive
    technology: Rename (a pencil) on a frame the person owns, then Manage
    access (a key) on an owned frame or Leave frame (a door and arrow) on a
    shared one; no access button when an owned frame has no view."""
    cls = "account-frame__action"
    if frame.shared:
        return ui_modal.trigger_html(
            co_managers_card.leave_dialog_id(frame.device_id),
            layout.icon_html("icon-sign-out", 20), cls, i18n.t(_LEAVE_FRAME_ARIA) % frame.name)
    rename = frame_name_page.opener_html(
        frame.device_id, layout.icon_html("icon-pencil", 20), cls,
        i18n.t(_RENAME_FRAME_ARIA) % frame.name)
    if frame.access is None:
        return rename
    return rename + ui_modal.trigger_html(
        co_managers_card.access_dialog_id(frame.device_id),
        layout.icon_html("icon-key", 20), cls, i18n.t(_MANAGE_ACCESS_ARIA) % frame.name)


def _frame_line(frame):
    """The muted second line: who shared the frame. The hardware model is
    shown to nobody on this page."""
    return i18n.t(_SHARED_BY_TEXT) % frame.owner_email if frame.shared else ""


def _frame_detail_html(frame, now):
    """The row's detail: who shared the frame, then the status dot with the
    last-seen word."""
    line = _frame_line(frame)
    return (
        '%s<span class="account-frame__status">%s<span>%s</span></span>' % (
            '<span class="account-frame__line">%s</span>' % layout.escape_html(line)
            if line else "",
            frame_status.status_dot_html(frame),
            layout.escape_html(ui_shell.seen_text(frame, now))))


def _frame_row_html(frame, now):
    """One frame: the drawn frame, its name with its role pill and its status,
    a chevron to the frame's Home, and its one action (Manage access or Leave
    frame) as an icon button at the right."""
    pill = i18n.t(_PILL_CO_MANAGER_TEXT if frame.shared else _PILL_OWNER_TEXT)
    action_html = _frame_action_html(frame)
    # One affordance per row: the row itself opens the frame's Home, and a row
    # that also carries an action button shows no chevron beside it.
    return ui_groups.row(
        label_html='%s %s' % (
            layout.escape_html(frame.name),
            ui_components.pill_html(pill, extra_class="account-frame__role")),
        lead_html=ui_shell.frame_pic_html("account-frame"),
        detail_html=_frame_detail_html(frame, now), href=frame.href,
        trailing_html=action_html, chevron=not action_html, extra_class="account-frame")


def _frame_dialog_html(frame, open_access):
    """The dialog behind a row's action: Manage access (reopened when
    `open_access` is this frame's id) or Leave this frame."""
    if frame.shared:
        return co_managers_card.leave_dialog_html(
            frame.device_id, frame.name, co_managers_card.RETURN_ACCOUNT)
    rename = frame_name_page.dialog_html(
        frame.device_id, frame.name, co_managers_card.RETURN_ACCOUNT)
    if frame.access is None:
        return rename
    return co_managers_card.manage_access_dialog_html(
        frame.access, frame.device_id, frame.name, co_managers_card.RETURN_ACCOUNT,
        open_=frame.device_id == open_access) + rename


def _frames_card(frames, now):
    """The My frames group: the empty state with no frames, else one row per
    frame ordered by name, then the Add a frame row. The rows' dialogs come
    from `_frame_dialogs` and sit after the page's last group."""
    if not frames:
        return ui_groups.group_panel(
            pair_frame_page.empty_state_html(), label=i18n.t(_MY_FRAMES_TEXT),
            label_id="account-frames")
    rows = sorted(frames, key=lambda frame: (frame.name.casefold(), frame.href))
    add_row = ui_groups.row(
        i18n.t(pair_frame_page.ADD_LINK_TEXT), icon="icon-plus",
        href=pair_frame_page.PAIR_FRAME_ROUTE, extra_class="account-add-frame")
    return ui_groups.group(
        "".join(_frame_row_html(f, now) for f in rows) + add_row,
        label=i18n.t(_MY_FRAMES_TEXT), label_id="account-frames")


def _frame_dialogs(frames, open_access):
    """The dialogs behind the frame rows, in the rows' order. They follow the
    page's groups, so the groups are siblings one after another."""
    rows = sorted(frames, key=lambda frame: (frame.name.casefold(), frame.href))
    return "".join(_frame_dialog_html(f, open_access) for f in rows)


def _build_line_html():
    """The quiet build caption that ends the page: the build id and a hint line.
    The button reuses the copy script, which writes the copied word into the
    `.copy-btn__label` hint line and restores it. The id is validated hex."""
    text = i18n.t(_BUILD_LINE) % build_info.build_id()
    escape = layout.escape_html
    return (
        '<p class="account-build-wrap"><button type="button" class="account-build" '
        'data-copy-value="%s" data-copied-text="%s">'
        '<span class="account-build__id">%s</span>'
        '<span class="account-build__hint copy-btn__label">%s</span></button>'
        '<span class="visually-hidden" role="status" data-copy-feedback></span></p>' % (
            escape(text), escape(i18n.t(_BUILD_COPIED)), escape(text),
            escape(i18n.t(_BUILD_HINT))))


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
    about_html = ui_groups.group(
        ui_groups.row(
            i18n.t(_CREDITS_TEXT), detail=i18n.t(_CREDITS_ROW_DETAIL),
            href=CREDITS_ROUTE, extra_class="account-credits"),
        label=i18n.t(_ABOUT_TEXT), label_id="account-about")
    sign_out_html = ui_groups.group(
        '<li class="row row--action row--danger">'
        '<form method="post" action="/logout" class="logout-form account-sign-out">%s'
        '<button type="submit" class="row__main">%s</button></form></li>'
        % (layout.csrf_field(), layout.escape_html(i18n.t(_SIGN_OUT_TEXT))),
        extra_class="account-sign-out-group")
    return (
        layout.page_header(i18n.t(ACCOUNT_TITLE), purpose=i18n.t(ACCOUNT_PURPOSE))
        + _frames_card(frames, time.time() if now is None else now)
        + ui_groups.group(
            identity_html, label=i18n.t(_IDENTITY_TEXT), label_id="account-identity",
            extra_class="account-identity")
        + ui_groups.group(
            preferences_html, label=i18n.t(_PREFERENCES_TEXT), label_id="account-preferences")
        + about_html
        + sign_out_html
        + _build_line_html()
        + _frame_dialogs(frames, open_access))
