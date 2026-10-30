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
import json
from urllib.parse import quote

from companion import i18n, layout, prefs

# Literal here, byte-identical to companion/app.py's own LOGIN_ROUTE
# (and companion/routes.py's), since this module can never import
# companion.app either — the same "duplicated-not-imported" contract
# companion/routes.py's own module docstring documents.
LOGIN_ROUTE = "/login"

# The login card's one-sentence purpose text.
LOGIN_EXPLANATION_TEXT = i18n.msg(
    "common.sign_in_to_manage_this_device_s_settings",
    "Sign in to manage this device's settings.")

# A module constant beside LOGIN_EXPLANATION_TEXT because login_body()
# and the live countdown's template must both build from this one string.
LOGIN_LOCKOUT_TEXT = i18n.msg(
    "common.too_many_attempts_try_again_in_s",
    "Too many attempts — try again in %ds.")

# The substitution token the live countdown swaps for the remaining
# figure each second. "__N__" is excluded from test_i18n.py's French-
# catalogue scan as an uppercase code; a lowercase placeholder would not
# be, and would have to be translated (meaningless) or exempted.
LOGIN_LOCKOUT_TEMPLATE_TOKEN = "__N__"

# The id the login card's one message element carries (wrong-password
# and lockout share it); `aria-describedby` points at it only when a
# message is rendered.
LOGIN_MESSAGE_ID = "login-error"

# Rendered as server-escaped data-* attributes and swapped by
# companion/static/login-card.js, so that file hard-codes no English.
LOGIN_REVEAL_SHOW_LABEL = i18n.msg("common.show_password", "Show password")
LOGIN_REVEAL_HIDE_LABEL = i18n.msg("common.hide_password", "Hide password")

# Marks, not words — deliberately not translated; legible without
# relying on colour alone.
LOGIN_REVEAL_MASKED_GLYPH = "●"
LOGIN_REVEAL_SHOWN_GLYPH = "○"

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

# The 503 body when the session store cannot be read.
UNAVAILABLE_TITLE = i18n.msg("common.temporarily_unavailable", "Temporarily unavailable")
UNAVAILABLE_PURPOSE_TEXT = i18n.msg(
    "common.sign_in_data_could_not_be_read_please_try_again",
    "SkyPane could not check your session. Please try again in a moment.")

# The inline i18n.t() literals login_body()/not_found_page()/
# forbidden_page() below used to carry, hoisted to module-level
# Messages.
_BACK_TO_HOME_TEXT = i18n.msg("common.back_to_home", "Back to Home")
_PASSWORD_TEXT = i18n.msg("common.password", "Password")
_SIGN_IN_TEXT = i18n.msg("common.sign_in", "Sign in")
_NOT_FOUND_TAB_TITLE_TEXT = i18n.msg("common.not_found", "Not Found")

# The Auth0 sign-in start route. A plain GET link, never a form: a form
# POST would be blocked by the CSP `form-action 'self'` once the response
# redirects to the identity provider.
AUTH0_LOGIN_ROUTE = "/login/auth0"

LOGIN_EXPLANATION_AUTH0_TEXT = i18n.msg(
    "account.sign_in_to_manage_your_skypane_frames",
    "Sign in to manage your SkyPane frames.")
_LEGACY_SUMMARY_TEXT = i18n.msg(
    "account.use_the_shared_password_legacy",
    "Use the shared password (legacy)")
_LEGACY_BADGE_TEXT = i18n.msg("account.legacy", "Legacy")
_LEGACY_HELPER_TEXT = i18n.msg(
    "account.temporary_access_for_the_administrator_it",
    "Temporary access for the administrator. It will be removed once "
    "Auth0 sign-in is live.")
_LEGACY_SUBMIT_TEXT = i18n.msg(
    "account.sign_in_with_password", "Sign in with password")
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
SIGN_IN_ERROR_PASSWORD_OFF = "password_off"
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
    SIGN_IN_ERROR_PASSWORD_OFF: (
        i18n.msg("account.password_sign_in_is_turned_off",
                 "Password sign-in is turned off"),
        i18n.msg("account.use_the_sign_in_button_above",
                 "Use the Sign in button above.")),
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


def login_reveal_toggle_html():
    """The show-password toggle. Server-rendered `hidden`, always —
    a script-blocked browser never sees it (no-JS floor by
    construction), and the form still submits normally. Glyph swaps
    with state so appearance isn't carried by colour alone; both
    labels/glyphs are server-escaped data-* attributes so no English
    is hard-coded in the JS.
    """
    show_label = i18n.t(LOGIN_REVEAL_SHOW_LABEL)
    return (
        '<button type="button" class="copy-btn login-reveal" hidden '
        'aria-pressed="false" aria-label="%s" title="%s" '
        'data-login-reveal data-show-label="%s" data-hide-label="%s" '
        'data-show-glyph="%s" data-hide-glyph="%s">'
        '<span class="icon login-reveal__glyph" aria-hidden="true" '
        'data-login-reveal-glyph>%s</span>'
        "</button>" % (
            layout.escape_html(show_label),
            layout.escape_html(show_label),
            layout.escape_html(show_label),
            layout.escape_html(i18n.t(LOGIN_REVEAL_HIDE_LABEL)),
            layout.escape_html(LOGIN_REVEAL_MASKED_GLYPH),
            layout.escape_html(LOGIN_REVEAL_SHOWN_GLYPH),
            layout.escape_html(LOGIN_REVEAL_MASKED_GLYPH))
    )


def login_body(error=None, lockout_seconds=None, next_route=None):
    """The legacy-only login card's inner markup (the shared-password form
    under the logo, title and purpose sentence). `next_route` rides a
    hidden field so a failed login doesn't lose the destination. `error`
    is already translated by the caller; this only escapes it, so
    test_i18n.py's scanner can trace the literal at its one call site.
    """
    return _login_heading_html(LOGIN_EXPLANATION_TEXT) + login_form_html(
        error=error, lockout_seconds=lockout_seconds, next_route=next_route)


def _login_heading_html(explanation):
    return (
        # Decorative: the h1 beside it names the page.
        layout.logo_mark_html(40)
        + '<h1 class="page-title">SkyPane</h1>'
        + '<p class="text-body">%s</p>' % layout.escape_html(i18n.t(explanation)))


def login_form_html(
        error=None, lockout_seconds=None, next_route=None, autofocus=True,
        submit_text=None, quiet_submit=False):
    """The shared-password form. `aria-invalid="true"` fires only on
    wrong-password, never on lockout (the typed value isn't what's wrong).
    `autofocus` is dropped when another control owns the page's one
    autofocus; `quiet_submit` swaps the accent fill for the quiet wash
    when the password form is not the page's primary action.
    """
    # `if lockout_seconds:` (not `is not None`): a zero or absent
    # figure never renders a lockout sentence, matching
    # companion/static/login-card.js's own `remaining > 0` guard.
    locked = bool(lockout_seconds)
    if locked:
        message = i18n.t(LOGIN_LOCKOUT_TEXT) % lockout_seconds
    elif error:
        message = error
    else:
        message = None

    field_attrs = ""
    if message is not None:
        field_attrs += ' aria-describedby="%s"' % LOGIN_MESSAGE_ID
    if message is not None and not locked:
        field_attrs += ' aria-invalid="true"'
    # During a lockout both controls are natively disabled. This is
    # an affordance, never a boundary: companion/auth.py's
    # LoginThrottle is re-consulted on every POST before the
    # password is even looked at, so a visitor who re-enables these
    # two elements in devtools gains nothing at all.
    if locked:
        field_attrs += " disabled"

    # The live countdown's seed and template, server-computed and
    # serialised here — never computed from a client clock.
    form_attrs = ""
    if locked:
        form_attrs = (
            ' data-lockout-seconds="%s" data-lockout-template="%s"'
            ' data-lockout-token="%s"' % (
                layout.escape_html(json.dumps(int(lockout_seconds))),
                layout.escape_html(
                    i18n.t(LOGIN_LOCKOUT_TEXT).replace(
                        "%d", LOGIN_LOCKOUT_TEMPLATE_TOKEN)),
                layout.escape_html(LOGIN_LOCKOUT_TEMPLATE_TOKEN)))

    message_html = (
        '<p id="%s" class="field-error text-label" role="alert">%s</p>'
        % (LOGIN_MESSAGE_ID, layout.escape_html(message))
    ) if message is not None else ""

    next_field_html = (
        '<input type="hidden" name="next" value="%s">'
        % layout.escape_html(next_route)) if next_route else ""
    submit_attrs = ' class="login-form__submit--quiet"' if quiet_submit else ""
    if locked:
        submit_attrs += " disabled"
    return (
        '<form method="post" action="%s" class="login-form"%s>'
        "%s"
        '<label for="password">%s</label>'
        '<span class="login-form__field">'
        '<input type="password" id="password" name="password" '
        'class="login-form__input" '
        'autocomplete="current-password"%s required%s>'
        "%s"
        "</span>"
        "%s"
        '<button type="submit"%s>%s</button>'
        "</form>" % (
            LOGIN_ROUTE, form_attrs, next_field_html,
            layout.escape_html(i18n.t(_PASSWORD_TEXT)),
            " autofocus" if autofocus else "",
            field_attrs,
            login_reveal_toggle_html(),
            message_html,
            submit_attrs,
            layout.escape_html(i18n.t(submit_text or _SIGN_IN_TEXT)))
    )


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


def _legacy_block_html(error, lockout_seconds, next_route):
    """The collapsed shared-password disclosure shown beside Auth0. It
    opens by itself when it carries a wrong-password or lockout message
    so that message is never hidden.
    """
    is_open = " open" if (error or lockout_seconds) else ""
    return (
        '<details class="login-legacy"%s>'
        "<summary>"
        '<span class="banner__pill">%s</span>'
        '<span class="login-legacy__summary">%s</span>'
        "</summary>"
        "%s"
        '<p class="login-legacy__helper text-label section-caption">%s</p>'
        "</details>" % (
            is_open,
            layout.escape_html(i18n.t(_LEGACY_BADGE_TEXT)),
            layout.escape_html(i18n.t(_LEGACY_SUMMARY_TEXT)),
            login_form_html(
                error=error, lockout_seconds=lockout_seconds,
                next_route=next_route, autofocus=False,
                submit_text=_LEGACY_SUBMIT_TEXT, quiet_submit=True),
            layout.escape_html(i18n.t(_LEGACY_HELPER_TEXT)))
    )


def _login_card_html(
        error, lockout_seconds, next_route, auth0_enabled, legacy_enabled, notice):
    """The card body for every combination of the two sign-in methods.
    `notice` is an optional (title, detail) pair of Messages rendered as
    the page's one docked error toast above the primary action.
    """
    if not auth0_enabled and legacy_enabled and notice is None:
        return login_body(
            error=error, lockout_seconds=lockout_seconds, next_route=next_route)
    explanation = (
        LOGIN_EXPLANATION_AUTH0_TEXT if auth0_enabled else LOGIN_EXPLANATION_TEXT)
    parts = [_login_heading_html(explanation)]
    if not auth0_enabled and not legacy_enabled:
        notice = (_NOT_CONFIGURED_TEXT, None)
    if notice is not None:
        title, detail = notice
        parts.append(layout.toast_html(
            i18n.t(title), i18n.t(detail) if detail else None,
            tone=layout.TOAST_TONE_ERROR, docked=True))
    if auth0_enabled:
        parts.append(_sign_in_link_html(next_route))
        if legacy_enabled:
            parts.append(_legacy_block_html(error, lockout_seconds, next_route))
    elif legacy_enabled:
        parts.append(login_form_html(
            error=error, lockout_seconds=lockout_seconds, next_route=next_route))
    return "".join(parts)


def render_login_page(
        ui_theme, error=None, lockout_seconds=None, next_route=None, *,
        auth0_enabled=False, legacy_enabled=True, notice=None):
    body = _login_card_html(
        error, lockout_seconds, next_route, auth0_enabled, legacy_enabled, notice)
    return layout.login_shell(body, ui_theme=ui_theme)


def sign_in_error_page(
        kind, ui_theme, auth0_enabled=True, legacy_enabled=False, next_route=None):
    """The login card with one generic, fixed-wording error toast. `kind`
    is a SIGN_IN_ERROR_* value; an unknown kind reads as the incomplete
    case, so no caller-supplied text can ever reach the page.
    """
    notice = _SIGN_IN_ERROR_TEXT.get(
        kind, _SIGN_IN_ERROR_TEXT[SIGN_IN_ERROR_INCOMPLETE])
    return render_login_page(
        ui_theme, next_route=next_route, auth0_enabled=auth0_enabled,
        legacy_enabled=legacy_enabled, notice=notice)


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


def not_found_page(ui_theme, health_alert):
    """The shared 404 body, reached pre-auth from static-asset
    delegates too. `health_alert` (`None` for an unauthenticated
    caller) is the caller's own already-computed nav-dot severity,
    never markup — an error page never renders Health's own banner.
    """
    body = (
        layout.page_header(i18n.t(NOT_FOUND_TITLE), purpose=i18n.t(NOT_FOUND_PURPOSE_TEXT))
        + '<p class="text-body"><a href="%s">%s</a></p>'
        % (layout.HOME_ROUTE, layout.escape_html(i18n.t(_BACK_TO_HOME_TEXT)))
    )
    return layout.page_shell(
        # The <title> tag's own short form — distinct from
        # NOT_FOUND_TITLE above (the page heading's longer sentence) —
        # needs its own Message so the browser tab is translated too.
        title=i18n.t(_NOT_FOUND_TAB_TITLE_TEXT), active="", body=body,
        ui_theme=ui_theme, health_alert=health_alert)


def forbidden_page(ui_theme, health_alert):
    """The shared 403 body for the Origin/Sec-Fetch-Site POST gate.
    Byte-for-byte the same shape as not_found_page() above, kept as a
    separate function so a later change can relocate that gate
    independently.
    """
    body = (
        layout.page_header(i18n.t(FORBIDDEN_TITLE), purpose=i18n.t(FORBIDDEN_PURPOSE_TEXT))
        + '<p class="text-body"><a href="%s">%s</a></p>'
        % (layout.HOME_ROUTE, layout.escape_html(i18n.t(_BACK_TO_HOME_TEXT)))
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
