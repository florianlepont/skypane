"""The Account page body: the caller's own frames first, then who is signed
in and the browser preferences. Pure markup: it takes the signed-in identity
and a sequence of the caller's own frame summaries as arguments and reads
nothing else, so it carries no other account's frame and no MAC, token,
firmware version or device id beyond the frame's own address and the forms of
its dialogs. A frame shows no battery or last-contact figure, only its status
dot.
"""
from typing import NamedTuple

from companion import frame_status, i18n, layout, prefs, ui_entity_list, ui_modal
from companion.pages import co_managers_card

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
_NO_FRAMES_HEADING = i18n.msg(
    "account.your_frames_will_appear_here", "Your frames will appear here")
_NO_FRAMES_BODY = i18n.msg(
    "account.once_an_administrator_pairs_a_frame",
    "Once an administrator pairs a frame to your account, you land on its "
    "Home after you sign in.")
UNNAMED_FRAME_TEXT = i18n.msg("account.unnamed_frame", "Unnamed frame")
_SHARED_BY_TEXT = i18n.msg("account.shared_by", "Shared by %s")
_LEAVE_FRAME_TEXT = i18n.msg("account.leave_frame", "Leave frame")
_LEAVE_FRAME_ARIA = i18n.msg("account.leave_frame_aria", "Leave frame: %s")
_MANAGE_ACCESS_ARIA = i18n.msg("account.manage_access_aria", "Manage access: %s")
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


def _card(heading_id, heading, inner_html):
    return (
        '<section class="page-section page-section--nested" '
        'aria-labelledby="%s"><h2 class="text-heading" id="%s">%s</h2>%s</section>'
        % (heading_id, heading_id, layout.escape_html(i18n.t(heading)), inner_html))


def _preference_row(label, hint, control_html):
    """One labelled preference: its name and a one-line hint beside a
    segmented control sized to its content."""
    return (
        '<div class="pref-row"><div class="pref-row__text">'
        '<span class="pref-row__label">%s</span>'
        '<span class="pref-row__hint">%s</span></div>%s</div>'
    ) % (layout.escape_html(i18n.t(label)), layout.escape_html(i18n.t(hint)),
         control_html)


def _pair_html(label, value):
    return (
        '<div class="data-card"><div class="data-card__primary">'
        '<span class="data-card__label">%s</span>'
        '<span class="data-card__value">%s</span>'
        "</div></div>"
    ) % (layout.escape_html(i18n.t(label)), layout.escape_html(value))


def _frame_action_html(frame):
    """The one 44px action of a frame row: Manage access on an owned frame,
    Leave frame on a shared one; nothing when an owned frame has no view."""
    if frame.shared:
        return ui_modal.trigger_html(
            co_managers_card.leave_dialog_id(frame.device_id),
            layout.escape_html(i18n.t(_LEAVE_FRAME_TEXT)), "entity-row__button",
            i18n.t(_LEAVE_FRAME_ARIA) % frame.name)
    if frame.access is None:
        return ""
    return ui_modal.trigger_html(
        co_managers_card.access_dialog_id(frame.device_id),
        layout.escape_html(i18n.t(co_managers_card.MENU_LABEL)), "entity-row__button",
        i18n.t(_MANAGE_ACCESS_ARIA) % frame.name)


def _frame_line(frame):
    """The muted second line: who shared the frame, else its hardware."""
    if frame.shared:
        return i18n.t(_SHARED_BY_TEXT) % frame.owner_email
    return frame.hardware


def _frame_row_html(frame):
    return ui_entity_list.entity_row_html(
        frame_status.status_dot_html(frame), frame.name, _frame_line(frame), "",
        _frame_action_html(frame), frame.href)


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


def _frames_card(frames, open_access):
    """The My frames card: the empty state with no frames, else one row per
    frame ordered by name, followed by the row dialogs."""
    if not frames:
        return _card("account-frames", _MY_FRAMES_TEXT, layout.empty_state(
            i18n.t(_NO_FRAMES_HEADING), i18n.t(_NO_FRAMES_BODY), compact=True))
    rows = sorted(frames, key=lambda frame: (frame.name.casefold(), frame.href))
    return _card(
        "account-frames", _MY_FRAMES_TEXT,
        ui_entity_list.entity_list_html("".join(_frame_row_html(f) for f in rows))
        + "".join(_frame_dialog_html(f, open_access) for f in rows))


def render(identity, ui_theme="auto", frames=(), open_access=""):
    """The Account page body for `identity`, listing `frames` (the caller's
    own `FrameSummary` values). `open_access` is the id of the frame whose
    Manage access dialog renders open."""
    identity_html = (
        '<div class="account-identity">%s%s</div>' % (
            _pair_html(_EMAIL_TEXT, identity.email),
            _pair_html(_ROLE_TEXT, i18n.t(_role_text(identity)))))
    resolved_theme = ui_theme if ui_theme in layout.UI_THEME_CHOICES else "auto"
    preferences_html = (
        '<div class="pref-rows">%s%s</div>' % (
            _preference_row(
                _LANGUAGE_TEXT, _LANGUAGE_HINT,
                layout._lang_form_html(prefs.current_lang())),
            _preference_row(
                _THEME_TEXT, _THEME_HINT,
                layout._theme_form_html(resolved_theme))))
    sign_out_html = (
        '<form method="post" action="/logout" class="logout-form account-sign-out">'
        '<button type="submit">%s</button></form>'
        % layout.escape_html(i18n.t(_SIGN_OUT_TEXT)))
    return (
        layout.page_header(i18n.t(ACCOUNT_TITLE), purpose=i18n.t(ACCOUNT_PURPOSE))
        + _frames_card(tuple(frames), open_access)
        + _card("account-identity", _IDENTITY_TEXT, identity_html)
        + _card("account-preferences", _PREFERENCES_TEXT, preferences_html)
        + sign_out_html)
