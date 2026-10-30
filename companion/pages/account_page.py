"""The Account page body: who is signed in, the browser preferences, and
the slot where a user's frames will be listed. Pure markup: it takes the
signed-in identity as an argument and reads nothing else about the
account, so it can carry no frame, device or health data.
"""
from typing import NamedTuple

from companion import i18n, layout, prefs

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
_FRAMES_TEXT = i18n.msg("account.frames", "Frames")
_NO_FRAMES_HEADING = i18n.msg(
    "account.your_frames_will_appear_here", "Your frames will appear here")
_NO_FRAMES_BODY = i18n.msg(
    "account.once_an_administrator_pairs_a_frame_to_your",
    "Once an administrator pairs a frame to your account it will show up "
    "on this page.")
_SIGN_OUT_TEXT = i18n.msg("common.sign_out", "Sign out")

ROLE_USER = "user"
ROLE_ADMIN = "admin"


class Identity(NamedTuple):
    """What the page shows about the signed-in person: the email, the
    role ("user" or "admin")."""
    email: str
    role: str


def _role_text(identity):
    return _ROLE_ADMIN_TEXT if identity.role == ROLE_ADMIN else _ROLE_USER_TEXT


def _card(heading_id, heading, inner_html):
    return (
        '<section class="page-section page-section--nested" '
        'aria-labelledby="%s"><h2 class="text-heading" id="%s">%s</h2>%s</section>'
        % (heading_id, heading_id, layout.escape_html(i18n.t(heading)), inner_html))


def _pair_html(label, value):
    return (
        '<div class="data-card"><div class="data-card__primary">'
        '<span class="data-card__label">%s</span>'
        '<span class="data-card__value">%s</span>'
        "</div></div>"
    ) % (layout.escape_html(i18n.t(label)), layout.escape_html(value))


def render(identity, ui_theme="auto"):
    """The Account page body for `identity`."""
    identity_html = (
        '<div class="account-identity">%s%s</div>' % (
            _pair_html(_EMAIL_TEXT, identity.email),
            _pair_html(_ROLE_TEXT, i18n.t(_role_text(identity)))))
    resolved_theme = ui_theme if ui_theme in layout.UI_THEME_CHOICES else "auto"
    preferences_html = (
        layout._lang_form_html(prefs.current_lang())
        + layout._theme_form_html(resolved_theme))
    frames_html = layout.empty_state(
        i18n.t(_NO_FRAMES_HEADING), i18n.t(_NO_FRAMES_BODY), compact=True)
    sign_out_html = (
        '<form method="post" action="/logout" class="logout-form account-sign-out">'
        '<button type="submit">%s</button></form>'
        % layout.escape_html(i18n.t(_SIGN_OUT_TEXT)))
    return (
        layout.page_header(i18n.t(ACCOUNT_TITLE), purpose=i18n.t(ACCOUNT_PURPOSE))
        + _card("account-identity", _IDENTITY_TEXT, identity_html)
        + _card("account-preferences", _PREFERENCES_TEXT, preferences_html)
        + _card("account-frames", _FRAMES_TEXT, frames_html)
        + sign_out_html)
