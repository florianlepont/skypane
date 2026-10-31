"""The login card's markup, and the shared 404/403 error-page bodies,
moved out of `companion/app.py`. Every function here is pure markup: it
takes whatever request state it needs (the resolved UI theme, the
already-computed health-alert severity, an already-translated error
string) as an argument, and never reads `self`/the request itself —
`companion/app.py`'s `Handler` keeps a thin method for each (gathering
that state, e.g. `self._resolved_ui_theme()`/`self._principal()`,
and setting the request-scoped language via `prefs.set_request_prefs()`
before calling in here) so every existing call site
(`self._not_found_page()`, `self._render_login_page(...)`, etc.) is
unchanged.

Never imports `companion.app` (that would be a cycle — app.py imports
this module).
"""
from urllib.parse import quote

from companion import i18n, layout, prefs

# Literal here, byte-identical to companion/app.py's own LOGIN_ROUTE
# (and companion/routes.py's), since this module can never import
# companion.app either — the same "duplicated-not-imported" contract
# companion/routes.py's own module docstring documents.
LOGIN_ROUTE = "/login"

# `layout.page_header()` escapes both when it renders them — these are
# always plain strings, never pre-escaped markup.
NOT_FOUND_TITLE = i18n.msg("common.page_not_found", "Page not found.")
NOT_FOUND_PURPOSE_TEXT = i18n.msg(
    "common.the_page_you_requested_doesn_t_exist_or_may",
    "The page you requested doesn't exist or may have moved.")

# Handler._dispatch()'s own Origin/Sec-Fetch-Site gate's 403 body — see
# forbidden_page() below.
FORBIDDEN_TITLE = i18n.msg("common.request_refused", "Request refused")
FORBIDDEN_PURPOSE_TEXT = i18n.msg(
    "common.this_request_came_from_another_site_so_it_was",
    "This request came from another site, so it was refused. Open SkyPane "
    "directly and try again.")

# The 403 body when a protected form arrives without a valid session token.
CSRF_EXPIRED_TEXT = i18n.msg(
    "common.csrf_expired", "This page expired. Reload and try again.")

# The 503 body when the session store cannot be read.
UNAVAILABLE_TITLE = i18n.msg("common.temporarily_unavailable", "Temporarily unavailable")
UNAVAILABLE_PURPOSE_TEXT = i18n.msg(
    "common.sign_in_data_could_not_be_read_please_try_again",
    "SkyPane could not check your session. Please try again in a moment.")

# The inline i18n.t() literals login_body()/not_found_page()/
# forbidden_page() below used to carry, hoisted to module-level
# Messages.
_BACK_TO_HOME_TEXT = i18n.msg("common.back_to_home", "Back to Home")
_BACK_TO_ACCOUNT_TEXT = i18n.msg("account.back_to_account", "Back to Account")
_SIGN_IN_TEXT = i18n.msg("common.sign_in", "Sign in")
_NOT_FOUND_TAB_TITLE_TEXT = i18n.msg("common.not_found", "Not Found")
_CREDITS_LINK_TEXT = i18n.msg("credits.credits", "Credits")

# The Auth0 sign-in start route. A plain GET link, never a form: a form
# POST would be blocked by the CSP `form-action 'self'` once the response
# redirects to the identity provider.
AUTH0_LOGIN_ROUTE = "/login/auth0"

LOGIN_EXPLANATION_AUTH0_TEXT = i18n.msg(
    "account.sign_in_to_manage_your_skypane_frames",
    "Sign in to manage your SkyPane frames.")
_NOT_CONFIGURED_TEXT = i18n.msg(
    "account.sign_in_is_not_configured", "Sign-in is not configured")

_NOT_INVITED_TITLE_TEXT = i18n.msg(
    "account.no_invitation_found", "No invitation found")
_NOT_INVITED_DETAIL_TEXT = i18n.msg(
    "account.this_account_has_not_been_invited_to_skypane",
    "This account has not been invited to SkyPane. Ask the administrator "
    "for an invitation.")
_BACK_TO_SIGN_IN_TEXT = i18n.msg(
    "account.back_to_sign_in", "Back to sign in")

# The closed set of generic sign-in failures, each mapped to fixed
# wording. Nothing the identity provider returns is ever reflected.
SIGN_IN_ERROR_INCOMPLETE = "incomplete"
SIGN_IN_ERROR_EXPIRED = "expired"
SIGN_IN_ERROR_UNAVAILABLE = "unavailable"
_SIGN_IN_ERROR_TEXT = {
    SIGN_IN_ERROR_INCOMPLETE: (
        i18n.msg("account.sign_in_could_not_be_completed",
                 "Sign-in could not be completed"),
        i18n.msg("account.start_again_from_this_page_if_it_keeps",
                 "Start again from this page. If it keeps happening, "
                 "check that cookies are enabled.")),
    SIGN_IN_ERROR_EXPIRED: (
        i18n.msg("account.sign_in_took_too_long", "Sign-in took too long"),
        i18n.msg("account.start_again_from_this_page",
                 "Start again from this page.")),
    SIGN_IN_ERROR_UNAVAILABLE: (
        i18n.msg("account.sign_in_is_not_available_right_now",
                 "Sign-in is not available right now"),
        i18n.msg("account.try_again_in_a_few_minutes",
                 "Try again in a few minutes.")),
}

INTERSTITIAL_IN = "in"
INTERSTITIAL_OUT = "out"
_INTERSTITIAL_TEXT = {
    INTERSTITIAL_IN: (
        i18n.msg("account.signing_in", "Signing in"),
        i18n.msg("account.signing_you_in", "Signing you in…")),
    INTERSTITIAL_OUT: (
        i18n.msg("account.signing_out", "Signing out"),
        i18n.msg("account.signing_you_out", "Signing you out…")),
}
_CONTINUE_TO_TEXT = i18n.msg("account.continue_to_s", "Continue to %s")

# Messages a caller passes as an interstitial's fallback-link label.
CONTINUE_TARGET_ACCOUNT = i18n.msg("account.account", "Account")
CONTINUE_TARGET_HOME = i18n.msg("nav.home", "Home")
CONTINUE_TARGET_SIGN_IN = _SIGN_IN_TEXT


def _login_heading_html(explanation):
    return (
        # Decorative: the h1 beside it names the page.
        layout.logo_mark_html(40)
        + '<h1 class="page-title">SkyPane</h1>'
        + '<p class="text-body">%s</p>' % layout.escape_html(i18n.t(explanation)))


def _sign_in_link_html(next_route):
    """The Auth0 start link: a plain GET anchor carrying `next` only when
    it is a same-site relative path (the caller whitelists; this refuses
    anything else again).
    """
    href = AUTH0_LOGIN_ROUTE
    if next_route and next_route.startswith("/") and not next_route.startswith("//"):
        href += "?next=" + quote(next_route, safe="/")
    return '<a class="login-signin" href="%s" autofocus>%s</a>' % (
        layout.escape_html(href), layout.escape_html(i18n.t(_SIGN_IN_TEXT)))


def _login_card_html(next_route, auth0_enabled, notice):
    """The card body. `notice` is an optional (title, detail) pair of
    Messages rendered as the page's one docked error toast above the
    primary action. Without Auth0 the card says sign-in is not configured
    and offers no way to start a session.
    """
    parts = [_login_heading_html(LOGIN_EXPLANATION_AUTH0_TEXT)]
    if not auth0_enabled and notice is None:
        notice = (_NOT_CONFIGURED_TEXT, None)
    if notice is not None:
        title, detail = notice
        parts.append(layout.toast_html(
            i18n.t(title), i18n.t(detail) if detail else None,
            tone=layout.TOAST_TONE_ERROR, docked=True))
    if auth0_enabled:
        parts.append(_sign_in_link_html(next_route))
    return "".join(parts)


def render_login_page(ui_theme, next_route=None, *, auth0_enabled=False, notice=None):
    body = _login_card_html(next_route, auth0_enabled, notice)
    body += '<a class="text-link login-card__link" href="/credits">%s</a>' % (
        layout.escape_html(i18n.t(_CREDITS_LINK_TEXT)))
    return layout.login_shell(body, ui_theme=ui_theme)


def sign_in_error_page(kind, ui_theme, auth0_enabled=True, next_route=None):
    """The login card with one generic, fixed-wording error toast. `kind`
    is a SIGN_IN_ERROR_* value; an unknown kind reads as the incomplete
    case, so no caller-supplied text can ever reach the page.
    """
    notice = _SIGN_IN_ERROR_TEXT.get(
        kind, _SIGN_IN_ERROR_TEXT[SIGN_IN_ERROR_INCOMPLETE])
    return render_login_page(
        ui_theme, next_route=next_route, auth0_enabled=auth0_enabled, notice=notice)


def not_invited_page(ui_theme):
    """The refusal for a verified identity with no local account. Unknown,
    unverified and disabled identities all render this same page: nothing
    is echoed back, and there is nothing to retry.
    """
    body = (
        layout.logo_mark_html(40)
        + '<h1 class="page-title">SkyPane</h1>'
        + layout.toast_html(
            i18n.t(_NOT_INVITED_TITLE_TEXT), i18n.t(_NOT_INVITED_DETAIL_TEXT),
            tone=layout.TOAST_TONE_WARNING, docked=True)
        + '<a class="text-link login-card__link" href="%s">%s</a>'
        % (LOGIN_ROUTE, layout.escape_html(i18n.t(_BACK_TO_SIGN_IN_TEXT))))
    return layout.login_shell(body, ui_theme=ui_theme)


# The interstitial is a bare document with no script: the meta refresh
# does the hop, so it works under the strict CSP and with scripts blocked.
# No literal braces other than the named slots.
INTERSTITIAL_TEMPLATE = (
    "<!DOCTYPE html>\n"
    '<html lang="{lang}" data-ui-theme="{ui_theme}">\n'
    "<head>\n"
    '<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
    '<meta name="referrer" content="no-referrer">\n'
    '<meta http-equiv="refresh" content="0;url={target}">\n'
    "<title>{title} - {site_title}</title>\n"
    '<link rel="stylesheet" href="/static/style.css">\n'
    "{favicon_link}\n"
    "</head>\n"
    "<body>\n"
    '<div class="login-shell">\n'
    '<div class="login-card" role="status">\n'
    "{body}\n"
    "</div>\n"
    "</div>\n"
    "</body>\n"
    "</html>\n"
)


def interstitial_page(kind, target, target_label, ui_theme="auto"):
    """The sign-in / sign-out landing: a meta refresh to `target` plus a
    visible fallback link. `target` is supplied by server code only (a
    fixed local path or the fixed identity-provider URL) and is refused
    unless it is a same-site path or an http(s) URL; `target_label` is a
    Message naming the destination for the fallback link.
    """
    safe_target = (target.startswith("/") and not target.startswith("//")) \
        or target.startswith(("https://", "http://"))
    if not safe_target:
        raise ValueError("interstitial target must be a local path or http(s) URL")
    title, line = _INTERSTITIAL_TEXT.get(kind, _INTERSTITIAL_TEXT[INTERSTITIAL_IN])
    resolved_theme = ui_theme if ui_theme in layout.UI_THEME_CHOICES else "auto"
    escaped_target = layout.escape_html(target)
    body = (
        layout.logo_mark_html(40)
        + '<p class="text-body">%s</p>' % layout.escape_html(i18n.t(line))
        + '<a class="text-link login-card__link" href="%s">%s</a>' % (
            escaped_target,
            layout.escape_html(i18n.t(_CONTINUE_TO_TEXT) % i18n.t(target_label))))
    return INTERSTITIAL_TEMPLATE.format_map({
        "lang": layout.escape_html(prefs.current_lang()),
        "ui_theme": layout.escape_html(resolved_theme),
        "target": escaped_target,
        "title": layout.escape_html(i18n.t(title)),
        "site_title": layout.escape_html(layout.SITE_TITLE),
        "favicon_link": layout.FAVICON_LINK_HTML,
        "body": body,
    })


BACK_HOME = "home"
BACK_ACCOUNT = "account"
BACK_SIGN_IN = "sign-in"


def _back_link_html(back):
    """The error pages' one onward link: Home for an administrator, the
    Account page for a plain user, the sign-in page for a caller with no
    session. Any other value reads as Home.
    """
    if back == BACK_ACCOUNT:
        route, label = "/account", _BACK_TO_ACCOUNT_TEXT
    elif back == BACK_SIGN_IN:
        route, label = LOGIN_ROUTE, _BACK_TO_SIGN_IN_TEXT
    else:
        route, label = layout.HOME_ROUTE, _BACK_TO_HOME_TEXT
    return '<p class="text-body"><a href="%s">%s</a></p>' % (
        route, layout.escape_html(i18n.t(label)))


def not_found_page(ui_theme, health_alert, back=BACK_HOME):
    """The shared 404 body, reached pre-auth from static-asset
    delegates too. `health_alert` (`None` for an unauthenticated
    caller) is the caller's own already-computed nav-dot severity,
    never markup — an error page never renders Health's own banner.
    """
    body = (
        layout.page_header(i18n.t(NOT_FOUND_TITLE), purpose=i18n.t(NOT_FOUND_PURPOSE_TEXT))
        + _back_link_html(back)
    )
    return layout.page_shell(
        # The <title> tag's own short form — distinct from
        # NOT_FOUND_TITLE above (the page heading's longer sentence) —
        # needs its own Message so the browser tab is translated too.
        title=i18n.t(_NOT_FOUND_TAB_TITLE_TEXT), active="", body=body,
        ui_theme=ui_theme, health_alert=health_alert)


def forbidden_page(ui_theme, health_alert, back=BACK_HOME, purpose=None):
    """The shared 403 body for the Origin/Sec-Fetch-Site POST gate.
    Byte-for-byte the same shape as not_found_page() above, kept as a
    separate function so a later change can relocate that gate
    independently.
    """
    body = (
        layout.page_header(i18n.t(FORBIDDEN_TITLE), purpose=i18n.t(purpose or FORBIDDEN_PURPOSE_TEXT))
        + _back_link_html(back)
    )
    return layout.page_shell(
        title=i18n.t(FORBIDDEN_TITLE), active="", body=body,
        ui_theme=ui_theme, health_alert=health_alert)


def unavailable_page(ui_theme):
    """The generic 503 body for a request whose session could not be
    checked. Fixed wording: no error text ever reaches the page, and no
    Health state is computed.
    """
    body = layout.page_header(
        i18n.t(UNAVAILABLE_TITLE), purpose=i18n.t(UNAVAILABLE_PURPOSE_TEXT))
    return layout.page_shell(
        title=i18n.t(UNAVAILABLE_TITLE), active="", body=body,
        ui_theme=ui_theme, health_alert=None)
