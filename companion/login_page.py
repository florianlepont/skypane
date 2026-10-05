"""The login card's markup, and the shared 404/403 error-page bodies,
moved out of `companion/app.py`. Every function here is pure markup: it
takes whatever request state it needs (the resolved UI theme, the
already-computed health-alert severity, an already-translated error
string) as an argument, and never reads `self`/the request itself —
`companion/app.py`'s `Handler` keeps a thin method for each (gathering
that state, e.g. `self._resolved_ui_theme()`/`self._is_authenticated()`,
and setting the request-scoped language via `prefs.set_request_prefs()`
before calling in here) so every existing call site
(`self._not_found_page()`, `self._render_login_page(...)`, etc.) is
unchanged.

Never imports `companion.app` (that would be a cycle — app.py imports
this module).
"""
import json

from companion import i18n, layout

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

# The inline i18n.t() literals login_body()/not_found_page()/
# forbidden_page() below used to carry, hoisted to module-level
# Messages.
_BACK_TO_HOME_TEXT = i18n.msg("common.back_to_home", "Back to Home")
_PASSWORD_TEXT = i18n.msg("common.password", "Password")
_SIGN_IN_TEXT = i18n.msg("common.sign_in", "Sign in")
_NOT_FOUND_TAB_TITLE_TEXT = i18n.msg("common.not_found", "Not Found")


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
    """The login card's inner markup. `next_route` rides a hidden
    field so a failed login doesn't lose the destination. `error` is
    already translated by the caller; this only escapes it, so
    test_i18n.py's scanner can trace the literal at its one call
    site. `aria-invalid="true"` fires only on wrong-password, never
    on lockout (the typed value isn't what's wrong).
    """
    parts = [
        # Decorative: the h1 beside it names the page.
        layout.logo_mark_html(40),
        '<h1 class="page-title">SkyPane</h1>',
        '<p class="text-body">%s</p>' % layout.escape_html(i18n.t(LOGIN_EXPLANATION_TEXT)),
    ]
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
    parts.append(
        '<form method="post" action="%s" class="login-form"%s>'
        "%s"
        '<label for="password">%s</label>'
        '<span class="login-form__field">'
        '<input type="password" id="password" name="password" '
        'class="login-form__input" '
        'autocomplete="current-password" autofocus required%s>'
        "%s"
        "</span>"
        "%s"
        '<button type="submit"%s>%s</button>'
        "</form>" % (
            LOGIN_ROUTE, form_attrs, next_field_html,
            layout.escape_html(i18n.t(_PASSWORD_TEXT)),
            field_attrs,
            login_reveal_toggle_html(),
            message_html,
            " disabled" if locked else "",
            layout.escape_html(i18n.t(_SIGN_IN_TEXT)))
    )
    return "".join(parts)


def render_login_page(ui_theme, error=None, lockout_seconds=None, next_route=None):
    body = login_body(error=error, lockout_seconds=lockout_seconds, next_route=next_route)
    return layout.login_shell(body, ui_theme=ui_theme)


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
