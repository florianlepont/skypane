"""companion/ui_shell.py: the two full-HTML5-document builders — `login_shell()`
for the pre-authentication page and `page_shell()` for every authenticated
page — plus the script-ordering constants (`SHELL_SCRIPT_ORDER`,
`GLOBAL_PAGE_SCRIPTS`) they share. Both builders fill a named template
(`str.format_map()` over a dict of descriptive keys) rather than a
positional `%s` template, so a reordered slot cannot silently swap two
values. Depends on companion.ui_base for constants/escaping, companion.
ui_time for the relative-time `<body>` wordings, companion.ui_nav for
the sidebar/tab-bar/preferences renderers, and companion.ui_components
for the quick-switch failure toast; nothing here imports a page module.
"""
import companion.i18n as i18n
import companion.prefs as prefs
from companion.ui_base import (
    AIRLINE_TYPES_SCRIPT_SRC,
    CONFIRM_SUBMIT_SCRIPT_SRC,
    COPY_BUTTON_SCRIPT_SRC,
    DIRTY_STATE_SCRIPT_SRC,
    FAVICON_LINK_HTML,
    FLASH_CLEANUP_SCRIPT_SRC,
    TOAST_SCRIPT_SRC,
    FLASH_SLOT_MARKER,
    FRESHNESS_SCRIPT_SRC,
    ICON_DEFS_HTML,
    LIST_FILTER_SCRIPT_SRC,
    LOGIN_CARD_SCRIPT_SRC,
    NAV_DROPDOWN_SCRIPT_SRC,
    PANEL_LOOKUP_SCRIPT_SRC,
    POLL_COOLDOWN_SCRIPT_SRC,
    QUICK_TOAST_TEMPLATE_ATTR,
    QUICK_SWITCH_FAILED_TEXT,
    QUICK_SWITCH_SCRIPT_SRC,
    QUICK_TOAST_ATTR,
    RELATIVE_TIME_SCRIPT_SRC,
    SITE_TITLE,
    SKIP_LINK_TARGET_ID,
    SUBMIT_GUARD_SCRIPT_SRC,
    THEME_PREVIEW_SCRIPT_SRC,
    UI_THEME_CHOICES,
    VALUE_CONTROLS_SCRIPT_SRC,
    CALENDAR_SHEET_SCRIPT_SRC,
    escape_html,
)
from companion.ui_nav import (
    REFRESH_PAGE_ATTR,
    REFRESH_PAUSED_ATTR,
    REFRESH_PAUSED_TEXT,
    REFRESH_RECONNECTING_ATTR,
    REFRESH_RECONNECTING_TEXT,
    REFRESH_TOKEN_ATTR,
    TAB_BAR_BODY_CLASS,
    _lang_form_html,
    _logout_form_html,
    _mobile_nav_html,
    _tab_bar_html,
    _theme_form_html,
    sidebar_nav,
)
from companion.ui_components import TOAST_TONE_ERROR, split_toast_message, toast_html
from companion.ui_time import relative_copy_attrs

# The pre-authentication document's <title> — the one inline i18n.t()
# literal this module used to carry, hoisted to a module-level Message.
_LOGIN_TITLE_TEXT = i18n.msg("common.login", "Login")

# The pre-authentication document's own named template: no icon sprite,
# skip link, sidebar or nav-dropdown script — the body holds only the
# login card. No literal "{" or "}" appears in the skeleton below other
# than the named slots themselves.
LOGIN_SHELL_TEMPLATE = (
    "<!DOCTYPE html>\n"
    '<html lang="{lang}" data-ui-theme="{ui_theme}">\n'
    "<head>\n"
    '<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
    "<title>{title} - {site_title}</title>\n"
    '<link rel="stylesheet" href="/static/style.css">\n'
    "{favicon_link}\n"
    "</head>\n"
    "<body>\n"
    '<div class="login-shell">\n'
    '<div class="login-card">\n'
    "{body}\n"
    "</div>\n"
    "</div>\n"
    '<script src="{script_src}" defer></script>\n'
    "</body>\n"
    "</html>\n"
)


def login_shell(body, ui_theme="auto", lang=None):
    """Minimal HTML5 document for the pre-authentication login page.

    Deliberately separate from page_shell() rather than a parameterized branch:
    page_shell() always renders the full authenticated sidebar/mobile-nav/
    footer, which would visually imply the whole site's nav is usable before
    signing in. Shares page_shell()'s outer document structure (doctype, head,
    FAVICON_LINK_HTML) but the body holds only the login card: no icon sprite,
    skip link, sidebar or nav-dropdown script. Emits exactly one deferred script
    tag, the login card's own.
    """
    resolved_theme = ui_theme if ui_theme in UI_THEME_CHOICES else "auto"
    resolved_lang = lang if lang in prefs.LANG_CHOICES else prefs.current_lang()
    return LOGIN_SHELL_TEMPLATE.format_map({
        "lang": escape_html(resolved_lang),
        "ui_theme": escape_html(resolved_theme),
        # Only "Login" is translated; SITE_TITLE is a brand name and stays
        # untranslated, so the title keeps the same "<page> - <product>" shape
        # as page_shell()'s <title>.
        "title": escape_html(i18n.t(_LOGIN_TITLE_TEXT)),
        "site_title": escape_html(SITE_TITLE),
        "favicon_link": FAVICON_LINK_HTML,
        "body": body,
        "script_src": LOGIN_CARD_SCRIPT_SRC,
    })


# The shell's own 15 script srcs, in the fixed relative order they are
# emitted whenever present - the one place that order is declared.
# page_shell()'s `scripts` argument only ever widens or narrows which of
# these are present; it never reorders them.
SHELL_SCRIPT_ORDER = (
    NAV_DROPDOWN_SCRIPT_SRC,
    DIRTY_STATE_SCRIPT_SRC,
    LIST_FILTER_SCRIPT_SRC,
    COPY_BUTTON_SCRIPT_SRC,
    FRESHNESS_SCRIPT_SRC,
    PANEL_LOOKUP_SCRIPT_SRC,
    FLASH_CLEANUP_SCRIPT_SRC,
    TOAST_SCRIPT_SRC,
    POLL_COOLDOWN_SCRIPT_SRC,
    CONFIRM_SUBMIT_SCRIPT_SRC,
    THEME_PREVIEW_SCRIPT_SRC,
    AIRLINE_TYPES_SCRIPT_SRC,
    SUBMIT_GUARD_SCRIPT_SRC,
    RELATIVE_TIME_SCRIPT_SRC,
    QUICK_SWITCH_SCRIPT_SRC,
    VALUE_CONTROLS_SCRIPT_SRC,
    CALENDAR_SHEET_SCRIPT_SRC,
)

# Present on every authenticated page_shell() document regardless of its
# `scripts` argument: the hamburger (every page has the nav), a flash
# cleanup and the toast behaviour (any page can carry `?flash=`), every
# form's submit guard, and the nav status line's relative time.
GLOBAL_PAGE_SCRIPTS = (
    NAV_DROPDOWN_SCRIPT_SRC,
    FLASH_CLEANUP_SCRIPT_SRC,
    TOAST_SCRIPT_SRC,
    SUBMIT_GUARD_SCRIPT_SRC,
    RELATIVE_TIME_SCRIPT_SRC,
)


def _script_tags_html(scripts):
    """Validate `scripts` against SHELL_SCRIPT_ORDER (ValueError on a src
    outside it — failing fast on a typo rather than silently emitting
    nothing) and return the `<script defer>` tags for GLOBAL_PAGE_SCRIPTS
    plus `scripts`, each at most once, in SHELL_SCRIPT_ORDER's fixed
    relative order.
    """
    unknown_scripts = set(scripts) - set(SHELL_SCRIPT_ORDER)
    if unknown_scripts:
        raise ValueError(
            "page_shell(): scripts=%r is not in SHELL_SCRIPT_ORDER"
            % (sorted(unknown_scripts),))
    wanted_scripts = set(GLOBAL_PAGE_SCRIPTS) | set(scripts)
    return "".join(
        '<script src="%s" defer></script>\n' % src
        for src in SHELL_SCRIPT_ORDER if src in wanted_scripts)


def _body_attrs_html(active, tab_bar_html, refresh_token):
    """The `<body>` attribute string: TAB_BAR_BODY_CLASS (only when the bar
    really renders), freshness.js's paused/reconnecting wordings, the page
    key REFRESH_SWAP_SELECTORS_BY_PAGE is chosen from, the freshness token
    when given, the optimistic switch's failure sentence, and
    relative-time.js's nine wordings — in that fixed order, matching
    page_shell()'s pre-split behaviour exactly.
    """
    body_class_attr = (
        ' class="%s"' % TAB_BAR_BODY_CLASS if tab_bar_html else "")
    # freshness.js's two neutral loop-state strings, translated here and read
    # client-side; see their constants' own definitions for why they live on
    # <body>.
    body_class_attr += (
        ' %s="%s" %s="%s"' % (
            REFRESH_PAUSED_ATTR,
            escape_html(i18n.t(REFRESH_PAUSED_TEXT)),
            REFRESH_RECONNECTING_ATTR,
            escape_html(i18n.t(REFRESH_RECONNECTING_TEXT))))
    # The page key selecting this document's swap-region list. Lives on
    # <body> because it, like the other attributes here, sits beside
    # elements that are themselves swap targets, and <body> is the one
    # element no swap ever replaces. Rendered for every page; an unknown
    # key selects nothing.
    body_class_attr += ' %s="%s"' % (
        REFRESH_PAGE_ATTR, escape_html(active))
    # The freshness token itself, rendered only when the caller has one -
    # /device and /airlines (not refresh pages) and the rejected-settings-
    # save re-render never pass refresh_token, so they carry no such
    # attribute at all.
    if refresh_token is not None:
        body_class_attr += ' %s="%s"' % (
            REFRESH_TOKEN_ATTR, escape_html(refresh_token))
    # relative-time.js's nine wordings, on <body> for the same swap-safety
    # reason. Emitted unconditionally; a page with no relative time carries
    # nine inert attributes.
    for _copy_attr, _copy_text in relative_copy_attrs():
        body_class_attr += ' %s="%s"' % (_copy_attr, escape_html(_copy_text))
    return body_class_attr


def _splice_flash(body, flash_html):
    """Swap FLASH_SLOT_MARKER in `body` for `flash_html` once — a page built
    on page_header() carries the marker, every other page does not — then
    strip any leftover marker unconditionally. Returns `(body, flash_html)`,
    the second cleared once it has been spliced into `body`.
    """
    if FLASH_SLOT_MARKER in body:
        body = body.replace(FLASH_SLOT_MARKER, flash_html, 1)
        flash_html = ""
    body = body.replace(FLASH_SLOT_MARKER, "")
    return body, flash_html


def _quick_toast_html():
    """The optimistic switch's failure toast: the error tone, no role of
    its own (the live region it is cloned into announces it) and a
    script-only dismiss button. An error never hides on its own."""
    title, detail = split_toast_message(i18n.t(QUICK_SWITCH_FAILED_TEXT))
    return toast_html(
        title, detail, tone=TOAST_TONE_ERROR, role="", dismiss_href=True)


# The authenticated document's own named template. Invariants preserved
# from the pre-template version: the tab bar ({tab_bar}) sits outside
# .dashboard-shell, a sibling rather than a descendant of the scrolled
# content column, so its `position: fixed` box is not nested inside the
# shell's own stacking context — "" on a page with no bar. <aside>
# precedes <header> in source order: at desktop width, where CSS hides
# the header, a keyboard user tabs into the sidebar nav first; both nav
# copies stay in the DOM always, and only the 960px CSS media query
# decides which is visible. The skip link ({skip_link}) is the first
# focusable element in <body>, before even the icon sprite. The
# quick-toast live region is rendered empty, once per document, never
# hidden — a live region added at announce time is one screen readers
# often miss — with `role="alert"` implying `aria-live="assertive"` for a
# failure the user awaits. quick-switch.js clones the translated error
# toast held in the <template> beside it into that region. Both are the
# one script-only surface here; with no script there is no fetch, so
# nothing here can fail beyond what the server's own flash already
# reports. No literal "{" or "}" appears below other than the named
# slots themselves.
PAGE_SHELL_TEMPLATE = (
    "<!DOCTYPE html>\n"
    '<html lang="{lang}" data-ui-theme="{ui_theme}">\n'
    "<head>\n"
    '<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
    "<title>{title} - {site_title}</title>\n"
    '<link rel="stylesheet" href="/static/style.css">\n'
    "{favicon_link}\n"
    "</head>\n"
    "<body{body_attrs}>\n"
    "{skip_link}\n"
    "{icon_defs}\n"
    '<div class="dashboard-shell">\n'
    '<aside class="dashboard-sidebar">\n'
    '<span class="site-title sidebar-title">{site_title}</span>\n'
    "{sidebar}\n"
    "{sidebar_footer}\n"
    "</aside>\n"
    '<header class="site-header">\n'
    '<span class="site-title">{site_title}</span>\n'
    "{mobile_nav}\n"
    "</header>\n"
    '<main class="page-content dashboard-main" id="{main_id}" tabindex="-1">\n'
    "{flash}\n{banner}\n{body}\n"
    "</main>\n"
    "</div>\n"
    "{tab_bar}\n"
    '<div class="toast-region toast-region--live" {quick_toast_attr} role="alert"></div>\n'
    "<template {quick_toast_template_attr}>{quick_toast}</template>\n"
    "{script_tags}"
    "</body>\n"
    "</html>\n"
)


def page_shell(
        title, active, body, ui_theme="auto", flash=None, banner=None,
        health_alert=None, lang=None, device_config=None, scripts=(),
        refresh_token=None):
    """Return a complete HTML5 document wrapping `body` in the shared shell.

    `title` and nav labels are escaped here. `body`, `flash` and `banner` are
    pre-built markup strings; the caller must have already escaped their own
    dynamic parts.

    `health_alert` is `None`/`"ok"` (no dot) or `"warn"`/`"error"` (a dot),
    threaded to sidebar_nav() and _mobile_nav_html(); a caller with no request
    context (login, 404, preview-image errors) draws no dot. `lang` defaults to
    `None`, resolved through prefs.current_lang(). `device_config` defaults to
    `None`, the same no-context degrade, threaded to both nav renderers for
    their shared request context.

    `scripts` is this page's own extra `*_SCRIPT_SRC` constants, on top of
    GLOBAL_PAGE_SCRIPTS (present regardless). Emitted in SHELL_SCRIPT_ORDER's
    fixed relative order, each at most once, however many times it appears
    across the two sets. A src not present in SHELL_SCRIPT_ORDER raises
    ValueError - failing fast on a typo rather than silently emitting nothing.

    `refresh_token` (default `None`) renders as REFRESH_TOKEN_ATTR on
    `<body>`, escaped, only when given - the four refresh pages'
    companion/app.py call site passes their own freshness token; every
    other caller (including the rejected-settings-save re-render) omits
    it, so that page carries no such attribute at all.
    """
    script_tags_html = _script_tags_html(scripts)
    resolved_theme = ui_theme if ui_theme in UI_THEME_CHOICES else "auto"
    resolved_lang = lang if lang in prefs.LANG_CHOICES else prefs.current_lang()
    sidebar_html = sidebar_nav(
        active, health_alert=health_alert, device_config=device_config)
    theme_form_html = _theme_form_html(resolved_theme)
    lang_form_html = _lang_form_html(resolved_lang)
    mobile_nav_html = _mobile_nav_html(
        active, theme_form_html, health_alert=health_alert,
        lang_form_html=lang_form_html, device_config=device_config)
    tab_bar_html = _tab_bar_html(
        active, health_alert=health_alert, device_config=device_config)
    body_attrs = _body_attrs_html(active, tab_bar_html, refresh_token)
    flash_html = flash or ""
    banner_html = banner or ""
    body, flash_html = _splice_flash(body, flash_html)
    # The sidebar's theme picker and Sign out control, grouped in one footer
    # region. Order: language, theme, Sign out — this and _mobile_nav_html()'s
    # own footer_html must change together.
    sidebar_footer_html = (
        '<div class="sidebar-footer">%s%s%s</div>'
        % (lang_form_html, theme_form_html, _logout_form_html()))
    skip_link_html = (
        '<a class="skip-link" href="#%s">Skip to content</a>'
        % SKIP_LINK_TARGET_ID)
    escaped_site_title = escape_html(SITE_TITLE)
    return PAGE_SHELL_TEMPLATE.format_map({
        "lang": escape_html(resolved_lang),
        "ui_theme": escape_html(resolved_theme),
        "title": escape_html(title),
        "site_title": escaped_site_title,
        "favicon_link": FAVICON_LINK_HTML,
        "body_attrs": body_attrs,
        "skip_link": skip_link_html,
        "icon_defs": ICON_DEFS_HTML,
        "sidebar": sidebar_html,
        "sidebar_footer": sidebar_footer_html,
        "mobile_nav": mobile_nav_html,
        "main_id": SKIP_LINK_TARGET_ID,
        "flash": flash_html,
        "banner": banner_html,
        "body": body,
        "tab_bar": tab_bar_html,
        "quick_toast_attr": QUICK_TOAST_ATTR,
        "quick_toast_template_attr": QUICK_TOAST_TEMPLATE_ATTR,
        "quick_toast": _quick_toast_html(),
        "script_tags": script_tags_html,
    })
