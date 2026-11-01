"""The Account page body: who is signed in, the browser preferences, and
the caller's own frames. Pure markup: it takes the signed-in identity and a
sequence of the caller's own frame summaries as arguments and reads nothing
else, so it carries no other account's frame and no MAC, token, firmware
version or device id beyond the Open link's address.
"""
import datetime
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
_YOUR_FRAMES_TEXT = i18n.msg("account.your_frames", "Your frames")
_LAST_CONTACT_TEXT = i18n.msg("account.last_contact", "Last contact")
_NO_CONTACT_TEXT = i18n.msg("account.no_contact_yet", "No contact yet")
_BATTERY_TEXT = i18n.msg("account.battery", "Battery")
UNNAMED_FRAME_TEXT = i18n.msg("account.unnamed_frame", "Unnamed frame")
_OPEN_TEXT = i18n.msg("account.open", "Open")
_OPEN_FRAME_TEXT = i18n.msg("account.open_frame", "Open %s")
_SHARED_TEXT = i18n.msg("account.shared", "Shared")
_OWNER_LINE_TEXT = i18n.msg("account.owner_s", "Owner: %s")
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
    hardware label, the epoch seconds of the last contact (None when never),
    the battery percentage (None when unknown) and the address of its Home.
    A frame the caller co-manages is `shared` and carries its owner's address
    in `owner_email`."""
    name: str
    hardware: str
    last_contact: float | None
    battery_percent: int | None
    href: str
    shared: bool = False
    owner_email: str = ""


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


def _contact_html(epoch, now):
    """The "Last contact" value: the clock as a `.time-value` and the age
    beside it, or the "no contact" words when the frame never checked in."""
    if epoch is None:
        return layout.escape_html(i18n.t(_NO_CONTACT_TEXT))
    seen = datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc)
    clock = layout.local_clock_text(seen, now_parsed=now)
    return (
        '<span class="time-value">%s</span><span class="cell-inline-sep">·</span>'
        '<span class="time-value__age">(%s)</span>' % (
            layout.escape_html(clock),
            layout.relative_time_html(seen.isoformat(), now.isoformat())))


def _shared_marks(frame):
    """The "Shared" pill and the "Owner: <address>" line of a co-managed
    frame; nothing for an owned one."""
    if not frame.shared:
        return "", ""
    pill = '<span class="banner__pill">%s</span>' % layout.escape_html(i18n.t(_SHARED_TEXT))
    owner = '<p class="text-label co-manager__email">%s</p>' % layout.escape_html(
        i18n.t(_OWNER_LINE_TEXT) % frame.owner_email)
    return pill, owner


def _frame_row_html(frame, now):
    pill_html, owner_html = _shared_marks(frame)
    battery_html = ""
    if frame.battery_percent is not None:
        battery_html = '<p class="text-label">%s %d%%</p>' % (
            layout.escape_html(i18n.t(_BATTERY_TEXT)), frame.battery_percent)
    return (
        '<li class="data-card"><div class="data-card__primary">'
        '<span class="text-heading">%s</span>'
        '<span class="text-label">%s</span>%s</div>%s'
        '<p class="text-label">%s %s</p>%s'
        '<p><a class="text-link" href="%s" aria-label="%s">%s</a></p></li>' % (
            layout.escape_html(frame.name), layout.escape_html(frame.hardware),
            pill_html, owner_html,
            layout.escape_html(i18n.t(_LAST_CONTACT_TEXT)),
            _contact_html(frame.last_contact, now), battery_html,
            layout.escape_html(frame.href),
            layout.escape_html(i18n.t(_OPEN_FRAME_TEXT) % frame.name),
            layout.escape_html(i18n.t(_OPEN_TEXT))))


def _frames_card(frames, now):
    """The Frames card: the empty state with no frames, else one row per
    frame ordered by name."""
    if not frames:
        return _card("account-frames", _FRAMES_TEXT, layout.empty_state(
            i18n.t(_NO_FRAMES_HEADING), i18n.t(_NO_FRAMES_BODY), compact=True))
    rows = sorted(frames, key=lambda frame: (frame.name.casefold(), frame.href))
    return _card(
        "account-frames", _YOUR_FRAMES_TEXT,
        '<ul class="data-cards">%s</ul>' % "".join(
            _frame_row_html(frame, now) for frame in rows))


def render(identity, ui_theme="auto", frames=(), now=None):
    """The Account page body for `identity`, listing `frames` (the caller's
    own `FrameSummary` values). `now` is an aware datetime, default the
    current instant."""
    if now is None:
        now = datetime.datetime.now(datetime.timezone.utc)
    identity_html = (
        '<div class="account-identity">%s%s</div>' % (
            _pair_html(_EMAIL_TEXT, identity.email),
            _pair_html(_ROLE_TEXT, i18n.t(_role_text(identity)))))
    resolved_theme = ui_theme if ui_theme in layout.UI_THEME_CHOICES else "auto"
    preferences_html = (
        layout._lang_form_html(prefs.current_lang())
        + layout._theme_form_html(resolved_theme))
    sign_out_html = (
        '<form method="post" action="/logout" class="logout-form account-sign-out">'
        '<button type="submit">%s</button></form>'
        % layout.escape_html(i18n.t(_SIGN_OUT_TEXT)))
    return (
        layout.page_header(i18n.t(ACCOUNT_TITLE), purpose=i18n.t(ACCOUNT_PURPOSE))
        + _card("account-identity", _IDENTITY_TEXT, identity_html)
        + _card("account-preferences", _PREFERENCES_TEXT, preferences_html)
        + _frames_card(tuple(frames), now)
        + sign_out_html)
