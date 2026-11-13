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
from types import SimpleNamespace

import companion.device_scope as device_scope
import companion.frame_menu as frame_menu
import companion.frame_status as frame_status
import companion.i18n as i18n
import companion.prefs as prefs
import companion.page_styles as page_styles
import companion.ui_save_bar as ui_save_bar
import companion.ui_segmented as ui_segmented
import companion.ui_splash as ui_splash
from companion.ui_base import (
    AIRLINE_EDITOR_ROUTE,
    CONFIRM_SUBMIT_SCRIPT_SRC,
    COPY_BUTTON_SCRIPT_SRC,
    DIRTY_STATE_SCRIPT_SRC,
    FAVICON_LINK_HTML,
    FLASH_CLEANUP_SCRIPT_SRC,
    TOAST_SCRIPT_SRC,
    FLASH_SLOT_MARKER,
    head_meta_html,
    FRESHNESS_SCRIPT_SRC,
    ICON_DEFS_HTML,
    icon_html,
    LOGO_MARK_CLASS,
    LIST_FILTER_SCRIPT_SRC,
    NAV_DROPDOWN_SCRIPT_SRC,
    PANEL_LOOKUP_SCRIPT_SRC,
    QUICK_TOAST_TEMPLATE_ATTR,
    SESSION_EXPIRED_TEMPLATE_ATTR,
    SESSION_EXPIRED_TEXT,
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
    CALENDAR_CONNECT_SCRIPT_SRC,
    MODAL_SCRIPT_SRC,
    MOTION_SCRIPT_SRC,
    PREFETCH_SCRIPT_SRC,
    SESSION_GUARD_SCRIPT_SRC,
    SPLASH_BOOT_SCRIPT_SRC,
    SPLASH_SCRIPT_SRC,
    LEAFLET_SCRIPT_SRC,
    PLACE_SEARCH_SCRIPT_SRC,
    PLACE_START_SCRIPT_SRC,
    PLACE_MAP_SCRIPT_SRC,
    PLACE_CARD_SCRIPT_SRC,
    PLACE_AIRPORT_LIST_SCRIPT_SRC,
    AIRLINE_TYPES_SCRIPT_SRC,
    escape_html,
    nav_slug,
)
from companion.ui_nav import (
    PULL_HINT_ATTR,
    PULL_HINT_TEXT,
    SHEET_GRAB_ATTR,
    SHEET_GRAB_TEXT,
    PULL_RELEASE_ATTR,
    PULL_RELEASE_TEXT,
    REFRESH_PAGE_ATTR,
    REFRESH_PAUSED_ATTR,
    REFRESH_PAUSED_TEXT,
    REFRESH_RECONNECTING_ATTR,
    REFRESH_RECONNECTING_TEXT,
    REFRESH_TOKEN_ATTR,
    CONSOLE_SPACE,
    PERSONAL_SPACE,
    TAB_BAR_BODY_CLASS,
    TAB_BAR_END_HTML,
    TAB_BAR_END_ID,
    _logout_form_html,
    _tab_bar_html,
    is_admin_principal,
    is_user_principal,
    current_space,
    sidebar_nav,
    space_switch_html,
    user_brand_href,
)
from companion.ui_components import TOAST_TONE_ERROR, split_toast_message, toast_html
from companion.ui_time import relative_age_text, relative_copy_attrs

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
    "{head_meta}\n"
    "<title>{title} - {site_title}</title>\n"
    '<link rel="stylesheet" href="/static/style.css">\n'
    "{favicon_link}\n"
    "</head>\n"
    "<body>\n"
    '<main class="login-shell">\n'
    '<div class="login-card">\n'
    "{body}\n"
    "</div>\n"
    "</main>\n"
    "</body>\n"
    "</html>\n"
)


def login_shell(body, ui_theme="auto", lang=None):
    """Minimal HTML5 document for the pre-authentication login page.

    Deliberately separate from page_shell() rather than a parameterized branch:
    page_shell() always renders the full authenticated sidebar/tab-bar/
    footer, which would visually imply the whole site's nav is usable before
    signing in. Shares page_shell()'s outer document structure (doctype, head,
    FAVICON_LINK_HTML) but the body holds only the login card: no icon sprite,
    skip link, sidebar or nav-dropdown script. Emits no script.
    """
    resolved_theme = ui_theme if ui_theme in UI_THEME_CHOICES else "auto"
    resolved_lang = lang if lang in prefs.LANG_CHOICES else prefs.current_lang()
    return LOGIN_SHELL_TEMPLATE.format_map({
        "lang": escape_html(resolved_lang),
        "ui_theme": escape_html(resolved_theme),
        "head_meta": head_meta_html(resolved_theme),
        # Only "Login" is translated; SITE_TITLE is a brand name and stays
        # untranslated, so the title keeps the same "<page> - <product>" shape
        # as page_shell()'s <title>.
        "title": escape_html(i18n.t(_LOGIN_TITLE_TEXT)),
        "site_title": escape_html(SITE_TITLE),
        "favicon_link": FAVICON_LINK_HTML,
        "body": body,
    })


# The shell's own script srcs, in the fixed relative order they are
# emitted whenever present - the one place that order is declared.
# page_shell()'s `scripts` argument only ever widens or narrows which of
# these are present; it never reorders them.
SHELL_SCRIPT_ORDER = (
    SESSION_GUARD_SCRIPT_SRC,
    NAV_DROPDOWN_SCRIPT_SRC,
    DIRTY_STATE_SCRIPT_SRC,
    LIST_FILTER_SCRIPT_SRC,
    COPY_BUTTON_SCRIPT_SRC,
    FRESHNESS_SCRIPT_SRC,
    PANEL_LOOKUP_SCRIPT_SRC,
    FLASH_CLEANUP_SCRIPT_SRC,
    TOAST_SCRIPT_SRC,
    CONFIRM_SUBMIT_SCRIPT_SRC,
    THEME_PREVIEW_SCRIPT_SRC,
    SUBMIT_GUARD_SCRIPT_SRC,
    RELATIVE_TIME_SCRIPT_SRC,
    QUICK_SWITCH_SCRIPT_SRC,
    VALUE_CONTROLS_SCRIPT_SRC,
    CALENDAR_CONNECT_SCRIPT_SRC,
    MODAL_SCRIPT_SRC,
    MOTION_SCRIPT_SRC,
    LEAFLET_SCRIPT_SRC,
    PLACE_SEARCH_SCRIPT_SRC,
    PLACE_START_SCRIPT_SRC,
    PLACE_MAP_SCRIPT_SRC,
    PLACE_CARD_SCRIPT_SRC,
    PLACE_AIRPORT_LIST_SCRIPT_SRC,
    AIRLINE_TYPES_SCRIPT_SRC,
    PREFETCH_SCRIPT_SRC,
)

# Present on every authenticated page_shell() document regardless of its
# `scripts` argument: the hamburger (every page has the nav), a flash
# cleanup and the toast behaviour (any page can carry `?flash=`), every
# form's submit guard, the nav status line's relative time, and the
# modal/menu dismissal script (any page can hold a dialog or a menu).
GLOBAL_PAGE_SCRIPTS = (
    SESSION_GUARD_SCRIPT_SRC,
    PREFETCH_SCRIPT_SRC,
    NAV_DROPDOWN_SCRIPT_SRC,
    FLASH_CLEANUP_SCRIPT_SRC,
    TOAST_SCRIPT_SRC,
    SUBMIT_GUARD_SCRIPT_SRC,
    RELATIVE_TIME_SCRIPT_SRC,
    MODAL_SCRIPT_SRC,
    MOTION_SCRIPT_SRC,
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
    # motion.js's pull-to-refresh prompts (Flights only acts on them).
    body_class_attr += ' %s="%s" %s="%s"' % (
        PULL_HINT_ATTR, escape_html(i18n.t(PULL_HINT_TEXT)),
        PULL_RELEASE_ATTR, escape_html(i18n.t(PULL_RELEASE_TEXT)))
    body_class_attr += ' %s="%s"' % (SHEET_GRAB_ATTR, escape_html(i18n.t(SHEET_GRAB_TEXT)))
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


def _session_expired_toast_html():
    """The toast shown just before a lapsed session is sent to sign-in."""
    title, detail = split_toast_message(i18n.t(SESSION_EXPIRED_TEXT))
    return toast_html(title, detail, tone=TOAST_TONE_ERROR, role="")


# The authenticated document's own named template. Invariants preserved
# from the pre-template version: the tab bar ({tab_bar}) sits outside
# .dashboard-shell, before it in source order so the render-blocking
# expectation on its end marker waits for ~2 KB of markup rather than the
# whole page, a sibling rather than a descendant of the scrolled
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
    "{head_meta}\n"
    "<title>{title} - {site_title}</title>\n"
    '<link rel="stylesheet" href="/static/style.css">\n'
    "{extra_styles}"
    "{tab_bar_expect}{strip_expect}"
    '<script src="{splash_boot_src}" data-splash-src="{splash_src}"></script>\n'
    "{favicon_link}\n"
    "</head>\n"
    "<body{body_attrs}>\n"
    "{skip_link}\n"
    "{icon_defs}\n"
    "{splash}\n"
    "{tab_bar}\n"
    '<div class="dashboard-shell">\n'
    '<aside class="dashboard-sidebar">\n'
    '<span class="brand">{brand_inner_sidebar}</span>\n'
    "{sidebar_switch}{sidebar}\n"
    "{sidebar_footer}\n"
    "</aside>\n"
    '<header class="site-header">\n'
    '<span class="brand">{brand_inner_header}</span>\n'
    "{frame_menu}"
    "</header>\n"
    '<main class="page-content dashboard-main" id="{main_id}" tabindex="-1" data-page-open>\n'
    "{frame_notice}{flash}\n{banner}\n{body}\n"
    "</main>\n"
    "</div>\n"
    '<div class="toast-region toast-region--live" {quick_toast_attr} role="alert"></div>\n'
    "<template {quick_toast_template_attr}>{quick_toast}</template>\n"
    "<template {session_expired_template_attr}>{session_expired_toast}</template>\n"
    "{script_tags}"
    "</body>\n"
    "</html>\n"
)


# The first link of every page, visible on keyboard focus.
_SKIP_LINK_TEXT = i18n.msg("nav.skip_to_content", "Skip to content")


# The shared wordings of the frame button's rows (companion/frame_menu.py).
_DEVICE_DEFAULT_NAME_TEXT = i18n.msg("nav.device_default_name", "Orly frame")
_UNNAMED_FRAME_TEXT = i18n.msg("admin_fleet.unnamed_frame", "Unnamed frame")
_TILE_SEEN_TEXT = i18n.msg("nav.frame_tile_seen", "Seen %s")

# The strip shown to an administrator on a personal page of a frame they
# neither own nor co-manage.
_FRAME_NOTICE_VIEWING_TEXT = i18n.msg("nav.frame_notice_viewing", "Viewing %s\u2019s frame")
_FRAME_NOTICE_BACK_TEXT = i18n.msg("nav.frame_notice_back", "Back to Fleet")
FRAME_NOTICE_CLASS = "frame-notice"
_MY_FRAMES_HREF = "/account#account-frames"
_FLEET_HREF = "/fleet"


def _device_page_path(active):
    """The un-prefixed path of the device-scoped page `active` names, else None
    (the Update page, a page with no nav tab, no context, the airline editor,
    which is one global list and shows no frame in view)."""
    for route in device_scope.page_routes():
        if nav_slug(route) == active and route != AIRLINE_EDITOR_ROUTE:
            return route
    return None


def device_display_name(device):
    """The frame's name for the people looking at it: never its internal id (a
    frame that was never named reads "Unnamed frame")."""
    if device.is_live and device.name == device_scope.LIVE_NAME:
        return i18n.t(_DEVICE_DEFAULT_NAME_TEXT)
    if device.name == device.id:
        return i18n.t(_UNNAMED_FRAME_TEXT)
    return device.name


def _switcher_status_row(device, now):
    """The status inputs the shared dot resolver reads, for one frame: the
    same signals the frame's Home page derives (late, screen off, battery
    empty), so one frame shows one status word everywhere."""
    # Imported on use: console_pairing loads the Console view modules.
    import datetime
    from companion import battery, console_pairing
    from server import state_store
    millivolts = state_store.load_battery_state(device.state_dir)
    state, screen_off, critical = console_pairing.frame_signals(
        device, datetime.datetime.fromtimestamp(
            now, datetime.timezone.utc).isoformat(timespec="seconds"))
    percent = 0 if critical else (
        None if millivolts is None else battery.battery_percent(millivolts))
    status = device_scope.device_status(device, now)
    return SimpleNamespace(
        kind=frame_status.KIND_LIVE,
        offline=status == device_scope.STATUS_OFFLINE,
        last_seen=device_scope.last_check_in_epoch(device.state_dir),
        battery_percent=percent, state=state, screen_off=screen_off)


def _seen_text(row, now):
    """The last-seen word under a tile's name: "Seen 2m ago", or "Not seen
    yet" for a frame that never checked in."""
    if row.last_seen is None:
        return i18n.t(frame_status.WORD_NOT_SEEN)
    return i18n.t(_TILE_SEEN_TEXT) % relative_age_text(now - row.last_seen)


def frame_pic_html(css_class):
    """The CSS-drawn frame: a dark bezel around a white screen. Decorative."""
    return '<span class="%s__pic" aria-hidden="true"><i></i></span>' % css_class


def seen_text(row, now):
    """The last-seen word of a frame row ("Seen 2m ago" or "Not seen yet")."""
    return _seen_text(row, now)


def _severity_rank(row):
    state = frame_status.frame_status(row).dot_state
    return {frame_status.STATUS_ERROR: 0, frame_status.STATUS_WARN: 1}.get(state, 2)


def console_ordered(entries, now):
    """Console cards: problems first (error, then warn, then the rest), each
    group by name."""
    return sorted(entries, key=lambda e: (
        _severity_rank(_switcher_status_row(e.device, now)),
        device_display_name(e.device).casefold(), e.device.id))


def _sheet_entries(active, now):
    """The cards' entries: every frame on a Console page, else the personal
    list."""
    if current_space(active) == CONSOLE_SPACE:
        return console_ordered(device_scope.console_frame_entries(), now)
    return device_scope.switcher_entries()


def frame_notice_html(active, console_page=False):
    """The Viewing-owner strip with a Back to Fleet link, or "" unless an
    administrator is on a personal page (not a Console page) of a frame they
    neither own nor co-manage. The owner email is escaped; the link is the
    fixed Fleet route."""
    if console_page or _device_page_path(active) is None:
        return ""
    email = device_scope.foreign_frame_owner_email()
    if email is None:
        return ""
    return (
        '<div class="%(cls)s"><span class="%(cls)s__text">%(text)s</span>'
        '<a class="text-link %(cls)s__link" href="%(href)s">%(back)s</a></div>\n') % {
            "cls": FRAME_NOTICE_CLASS,
            "text": escape_html(i18n.t(_FRAME_NOTICE_VIEWING_TEXT) % email),
            "href": _FLEET_HREF,
            "back": escape_html(i18n.t(_FRAME_NOTICE_BACK_TEXT)),
        }


def _device_scoped_title(title, active):
    """The page title with the selected frame's name appended on a
    device-scoped page, whatever the role or frame; every other title is
    returned unchanged."""
    current = device_scope.current_device()
    if current is None or _device_page_path(active) is None:
        return title
    return "%s - %s" % (title, device_display_name(current))


def page_shell(
        title, active, body, ui_theme="auto", flash=None, banner=None,
        health_alert=None, lang=None, device_config=None, scripts=(),
        refresh_token=None, console_page=False, styles=()):
    """Return a complete HTML5 document wrapping `body` in the shared shell.

    `title` and nav labels are escaped here. `body`, `flash` and `banner` are
    pre-built markup strings; the caller must have already escaped their own
    dynamic parts.

    `health_alert` is `None`/`"ok"` (no dot) or `"warn"`/`"error"` (a dot),
    threaded to sidebar_nav() and _tab_bar_html(); a caller with no request
    context (login, 404, preview-image errors) draws no dot. `lang` defaults to
    `None`, resolved through prefs.current_lang(). `device_config` defaults to
    `None`, the same no-context degrade, threaded to the nav renderers for
    their shared request context.

    `scripts` is this page's own extra `*_SCRIPT_SRC` constants, on top of
    GLOBAL_PAGE_SCRIPTS (present regardless). Emitted in SHELL_SCRIPT_ORDER's
    fixed relative order, each at most once, however many times it appears
    across the two sets. A src not present in SHELL_SCRIPT_ORDER raises
    ValueError - failing fast on a typo rather than silently emitting nothing.

    `styles` is this page's own extra stylesheet hrefs (the map page's library
    stylesheet), linked after the shared one in the order given; the shared
    stylesheet is always the one fixed link before them.

    `refresh_token` (default `None`) renders as REFRESH_TOKEN_ATTR on
    `<body>`, escaped, only when given - the four refresh pages'
    companion/app.py call site passes their own freshness token; every
    other caller (including the rejected-settings-save re-render) omits
    it, so that page carries no such attribute at all.

    `console_page` (default `False`) marks a Console page of a frame (Health,
    Device, the Airline editor), which never carries the foreign-frame strip.
    """
    script_tags_html = _script_tags_html(scripts)
    resolved_theme = ui_theme if ui_theme in UI_THEME_CHOICES else "auto"
    resolved_lang = lang if lang in prefs.LANG_CHOICES else prefs.current_lang()
    sidebar_html = sidebar_nav(
        active, health_alert=health_alert, device_config=device_config)
    tab_bar_html = _tab_bar_html(
        active, health_alert=health_alert, device_config=device_config,
        ui_theme=resolved_theme)
    body_attrs = _body_attrs_html(active, tab_bar_html, refresh_token)
    flash_html = flash or ""
    banner_html = banner or ""
    body, flash_html = _splice_flash(body, flash_html)
    # One unsaved-changes dialog per page that has a save bar, so no page can
    # forget it and no page carries two (the Components catalogue renders its
    # own copy as the sample).
    if "dirty-bar" in body and "data-leave-dialog" not in body:
        body += ui_save_bar.leave_dialog_html()
    # The sidebar's footer holds only Sign out; language and theme are set on
    # the Account page.
    sidebar_footer_html = (
        '<div class="sidebar-footer">%s</div>' % _logout_form_html())
    skip_link_html = (
        '<a class="skip-link" href="#%s">%s</a>'
        % (SKIP_LINK_TARGET_ID, escape_html(i18n.t(_SKIP_LINK_TEXT))))
    escaped_site_title = escape_html(SITE_TITLE)
    brand_mark_html = icon_html("icon-logo", size=28, extra_class=LOGO_MARK_CLASS)
    brand_inner_sidebar = (
        '{brand_mark}<span class="site-title sidebar-title">{site_title}</span>'
    ).format(brand_mark=brand_mark_html, site_title=escaped_site_title)
    brand_inner_header = (
        '{brand_mark}<span class="site-title">{site_title}</span>'
    ).format(brand_mark=brand_mark_html, site_title=escaped_site_title)
    if is_user_principal() or (
            is_admin_principal() and current_space(active) == PERSONAL_SPACE):
        # The wordmark leads to the frame's Home when the viewer can open it,
        # else to Account; an administrator's personal pages match a user's.
        brand_link = (
            '<a class="brand__link" href="%s">%%s</a>' % escape_html(user_brand_href()))
        brand_inner_sidebar = brand_link % brand_inner_sidebar
        brand_inner_header = brand_link % brand_inner_header
    return PAGE_SHELL_TEMPLATE.format_map({
        "lang": escape_html(resolved_lang),
        "ui_theme": escape_html(resolved_theme),
        "head_meta": head_meta_html(resolved_theme),
        "title": escape_html(_device_scoped_title(title, active)),
        "site_title": escaped_site_title,
        "favicon_link": FAVICON_LINK_HTML,
        "extra_styles": "".join(
            '<link rel="stylesheet" href="%s">\n' % escape_html(href)
            for href in (page_styles.area_hrefs(prefs.current_request_path()) if active else ())
            + tuple(styles)),
        # Decorative: the adjacent site-title text stays the accessible name.
        "brand_inner_sidebar": brand_inner_sidebar,
        "brand_inner_header": brand_inner_header,
        "body_attrs": body_attrs,
        "skip_link": skip_link_html,
        "icon_defs": ICON_DEFS_HTML,
        "splash": ui_splash.splash_html(),
        "splash_boot_src": SPLASH_BOOT_SCRIPT_SRC,
        "splash_src": SPLASH_SCRIPT_SRC,
        "sidebar": sidebar_html,
        "sidebar_footer": sidebar_footer_html,
        "sidebar_switch": space_switch_html(active),
        "main_id": SKIP_LINK_TARGET_ID,
        "frame_notice": frame_notice_html(active, console_page),
        "frame_menu": frame_menu.header_menu_html(active),
        "flash": flash_html,
        "banner": banner_html,
        "body": body,
        "tab_bar": tab_bar_html + TAB_BAR_END_HTML if tab_bar_html else "",
        "tab_bar_expect": (
            '<link rel="expect" href="#%s" blocking="render">\n' % TAB_BAR_END_ID
            if tab_bar_html else ""),
        # Hold the first frame until the page's carried strip, if any, is parsed.
        "strip_expect": (
            '<link rel="expect" href="#%s" blocking="render">\n' % ui_segmented.CARRY_END_ID
            if 'id="%s"' % ui_segmented.CARRY_END_ID in body else ""),
        "quick_toast_attr": QUICK_TOAST_ATTR,
        "quick_toast_template_attr": QUICK_TOAST_TEMPLATE_ATTR,
        "quick_toast": _quick_toast_html(),
        "session_expired_template_attr": SESSION_EXPIRED_TEMPLATE_ATTR,
        "session_expired_toast": _session_expired_toast_html(),
        "script_tags": script_tags_html,
    })
