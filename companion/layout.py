"""companion/layout.py: the public facade for the companion service's page
shell and component library.

This module now holds the shell builders only (`login_shell`, `page_shell`
and the script-ordering constants they share); every other responsibility
lives in a sibling `companion/ui_*.py` module (`ui_base` for constants/
routes/icons, `ui_time` for timestamp formatting, `ui_nav` for the sidebar/
tab-bar/preferences renderers, `ui_components` for the escaped component
library). Every name any caller has ever reached through `layout.X` is
re-exported here via an explicit import list — never a star import — so
existing call sites across `companion/pages/*.py` and the test suite keep
resolving unchanged.

stdlib-free itself: `html`/`datetime`/`zoneinfo` live in `ui_base`/
`ui_time`. No import from server/, and nothing from companion.auth beyond
the UI-theme cookie name, re-exported here for the same reason.
"""
import companion.i18n as i18n
import companion.prefs as prefs
from companion.auth import UI_THEME_COOKIE_NAME

from companion.ui_base import (
    ADVANCED_GROUP_LABEL,
    AIRLINES_ROUTE,
    CONFIRM_SUBMIT_SCRIPT_SRC,
    COPY_BUTTON_SCRIPT_SRC,
    DEVICE_ROUTE,
    DIRTY_STATE_SCRIPT_SRC,
    DISPLAY_ROUTE,
    FAVICON_LINK_HTML,
    FLASH_CLEANUP_SCRIPT_SRC,
    FLASH_SLOT_MARKER,
    FLIGHTS_ROUTE,
    FLIGHT_ROWS_SCRIPT_SRC,
    FRAME_STRIP_HEADING,
    FRESHNESS_SCRIPT_SRC,
    HEALTH_ALERT_SUFFIX_TEXT,
    HEALTH_NAV_SLUG,
    HEALTH_ROUTE,
    HOME_NAV_SLUG,
    HOME_ROUTE,
    ICON_DEFS_HTML,
    ICON_IDS,
    JS_GATE_CLASS,
    LIST_FILTER_SCRIPT_SRC,
    LOCAL_TZ,
    LOGIN_CARD_SCRIPT_SRC,
    MOBILE_NAV_ID,
    MOBILE_NAV_OPEN_CLASS,
    NAV_DROPDOWN_SCRIPT_SRC,
    NAV_GROUPS,
    NAV_ICON_IDS,
    NAV_NOTIFICATION_CLASS,
    NAV_TABS,
    NAV_TOGGLE_ID,
    NAV_TOGGLE_LABEL,
    PANEL_LOOKUP_SCRIPT_SRC,
    POLL_COOLDOWN_SCRIPT_SRC,
    QUICK_ACTION_APPLIES_SENTENCE,
    QUICK_ACTION_OFF_TEXT,
    QUICK_ACTION_ON_TEXT,
    QUICK_ACTION_QUIET_LABEL,
    QUICK_ACTION_QUIET_OFF_TEXT,
    QUICK_ACTION_QUIET_ON_TEMPLATE,
    QUICK_ACTION_QUIET_TURN_OFF_BUTTON,
    QUICK_ACTION_QUIET_TURN_ON_BUTTON,
    QUICK_ACTION_SCREEN_LABEL,
    QUICK_ACTION_SWITCH_OFF_BUTTON,
    QUICK_ACTION_SWITCH_ON_BUTTON,
    QUICK_STATE_FIELD,
    QUICK_STATE_OFF,
    QUICK_STATE_OFF_ATTR,
    QUICK_STATE_ON,
    QUICK_STATE_ON_ATTR,
    QUICK_SWITCH_CONTROL_ATTR,
    QUICK_SWITCH_FAILED_ATTR,
    QUICK_SWITCH_FAILED_TEXT,
    QUICK_SWITCH_QUIET_LABEL_ID,
    QUICK_SWITCH_QUIET_STATE_ID,
    QUICK_SWITCH_REGION_ATTR,
    QUICK_SWITCH_SCREEN_LABEL_ID,
    QUICK_SWITCH_SCREEN_STATE_ID,
    QUICK_SWITCH_SCRIPT_SRC,
    QUICK_TOAST_ATTR,
    RELATIVE_TIME_SCRIPT_SRC,
    SITE_TITLE,
    SKIP_LINK_TARGET_ID,
    STAT_TILE_ICON_CLASS,
    SUBMIT_GUARD_SCRIPT_SRC,
    THEME_PREVIEW_SCRIPT_SRC,
    UI_THEME_CHOICES,
    VALUE_CONTROLS_SCRIPT_SRC,
    VALUE_CONTROL_ATTR,
    VALUE_CONTROL_FIELD_ATTR,
    VALUE_CONTROL_FORMAT_ATTR,
    VALUE_CONTROL_FORMAT_CLOCK,
    VALUE_CONTROL_FORM_ATTR,
    VALUE_CONTROL_GEOMETRY_ATTR,
    VALUE_CONTROL_HANDLE_ATTR,
    VALUE_CONTROL_INPUT_ATTR,
    VALUE_CONTROL_MAX_ATTR,
    VALUE_CONTROL_MIN_ATTR,
    VALUE_CONTROL_READOUT_ATTR,
    VALUE_CONTROL_READOUT_BASE_ATTR,
    VALUE_CONTROL_READOUT_FORMAT_ATTR,
    VALUE_CONTROL_READOUT_SCALE_ATTR,
    VALUE_CONTROL_READOUT_TEXT_ATTR,
    VALUE_CONTROL_STEP_ATTR,
    VALUE_CONTROL_TEXT_ATTR,
    VALUE_CONTROL_TEXT_TOKEN,
    VALUE_CONTROL_TRACK_ATTR,
    _CARD_STATUS_SUFFIXES,
    _DEFAULT_STATUS_DOT_CLASS,
    _DEFAULT_STAT_TILE_CLASS,
    _FRAME_DELAY_DUE_TEXT,
    _FRAME_DELAY_HELD_TEXT,
    _FRAME_DELAY_UNKNOWN_TEXT,
    _FRAME_DOT_CLASS_BY_STATE,
    _FRAME_HEADLINE_DUE_TEXT,
    _FRAME_HEADLINE_HELD_TEXT,
    _FRAME_HEADLINE_LATE_TEXT,
    _FRAME_QUIET_SCHEDULE_LINK_TEXT,
    _FRAME_QUIET_SCHEDULE_TARGET_ID,
    _MONTH_ABBR,
    _MONTH_ABBR_FR,
    _STATUS_DOT_CLASSES,
    _STAT_TILE_BORDER_CLASSES,
    escape_html,
    icon_html,
    nav_slug,
)
from companion.ui_time import (
    DURATION_ATTRS,
    DURATION_DAYS_TEXT,
    DURATION_HOURS_TEXT,
    DURATION_MINUTES_TEXT,
    DURATION_SECONDS_TEXT,
    FRESHNESS_PREFIX_TEXT,
    FULL_TIMESTAMP_SENTINEL_NOW,
    REFRESH_LIVE_DOT_ATTR,
    REFRESH_PILL_TEXT,
    RELATIVE_COUNTDOWN_ATTR,
    RELATIVE_FUTURE_ATTRS,
    RELATIVE_FUTURE_DAYS_TEXT,
    RELATIVE_FUTURE_HOURS_TEXT,
    RELATIVE_FUTURE_MINUTES_TEXT,
    RELATIVE_FUTURE_SECONDS_TEXT,
    RELATIVE_PAST_ATTRS,
    RELATIVE_PAST_DAYS_TEXT,
    RELATIVE_PAST_HOURS_TEXT,
    RELATIVE_PAST_MINUTES_TEXT,
    RELATIVE_PAST_SECONDS_TEXT,
    RELATIVE_QUANTITY_MARK,
    RELATIVE_WAITING_ATTR,
    RELATIVE_WAITING_TEXT,
    _AGE_UNIT_SUFFIX_FR,
    _FULL_TIMESTAMP_SENTINEL_NOW,
    _RELATIVE_FUTURE_TEXTS,
    _RELATIVE_PAST_TEXTS,
    _age_bucket,
    _machine_instant,
    absolute_and_relative,
    age_seconds,
    concise_timestamp_html,
    duration_text,
    freshness_line_html,
    full_local_timestamp_text,
    local_clock_text,
    month_abbr,
    parse_iso,
    relative_age_text,
    relative_copy_attrs,
    relative_future_text,
    relative_time_html,
)
from companion.ui_nav import (
    NAV_QUIET_OFF_TEXT,
    NAV_QUIET_ON_TEXT,
    NAV_SCREEN_OFF_TEXT,
    NAV_SCREEN_ON_TEXT,
    NAV_STATUS_ARIA_LABEL_TEXT,
    NAV_STATUS_SEPARATOR_TEXT,
    REFRESH_NEW_ROW_CLASS,
    REFRESH_PAGE_ATTR,
    REFRESH_PAGE_DISPLAY,
    REFRESH_PAGE_FLIGHTS,
    REFRESH_PAGE_HEALTH,
    REFRESH_PAGE_HOME,
    REFRESH_PAUSED_ATTR,
    REFRESH_PAUSED_TEXT,
    REFRESH_PENDING_ATTR,
    REFRESH_RECONNECTING_ATTR,
    REFRESH_RECONNECTING_TEXT,
    REFRESH_ROW_ID_ATTR,
    REFRESH_SWAP_SELECTORS_BY_PAGE,
    REFRESH_TOKEN_ATTR,
    TAB_BAR_BODY_CLASS,
    TAB_BAR_MORE_ICON_ID,
    TAB_BAR_MORE_LABEL,
    _health_alert_markup,
    _lang_form_html,
    _logout_form_html,
    _mobile_nav_html,
    _nav_groups,
    _nav_links,
    _tab_bar_cell_body,
    _tab_bar_html,
    _theme_form_html,
    nav_status_html,
    sidebar_nav,
    ui_theme_from_cookie,
)
from companion.ui_components import (
    _FLASH_ROLES,
    _frame_strip_cell_html,
    anomaly_banner,
    card_status_class,
    data_table,
    empty_state,
    flash_banner,
    frame_strip_html,
    page_header,
    quick_switch_html,
    quick_switch_state_html,
    section_intro_html,
    stat_tile,
    status_dot,
    status_row,
)

__all__ = (
    "ADVANCED_GROUP_LABEL",
    "AIRLINES_ROUTE",
    "CONFIRM_SUBMIT_SCRIPT_SRC",
    "COPY_BUTTON_SCRIPT_SRC",
    "DEVICE_ROUTE",
    "DIRTY_STATE_SCRIPT_SRC",
    "DISPLAY_ROUTE",
    "DURATION_ATTRS",
    "DURATION_DAYS_TEXT",
    "DURATION_HOURS_TEXT",
    "DURATION_MINUTES_TEXT",
    "DURATION_SECONDS_TEXT",
    "FAVICON_LINK_HTML",
    "FLASH_CLEANUP_SCRIPT_SRC",
    "FLASH_SLOT_MARKER",
    "FLIGHTS_ROUTE",
    "FLIGHT_ROWS_SCRIPT_SRC",
    "FRAME_STRIP_HEADING",
    "FRESHNESS_PREFIX_TEXT",
    "FRESHNESS_SCRIPT_SRC",
    "FULL_TIMESTAMP_SENTINEL_NOW",
    "HEALTH_ALERT_SUFFIX_TEXT",
    "HEALTH_NAV_SLUG",
    "HEALTH_ROUTE",
    "HOME_NAV_SLUG",
    "HOME_ROUTE",
    "ICON_DEFS_HTML",
    "ICON_IDS",
    "JS_GATE_CLASS",
    "LIST_FILTER_SCRIPT_SRC",
    "LOCAL_TZ",
    "LOGIN_CARD_SCRIPT_SRC",
    "MOBILE_NAV_ID",
    "MOBILE_NAV_OPEN_CLASS",
    "NAV_DROPDOWN_SCRIPT_SRC",
    "NAV_GROUPS",
    "NAV_ICON_IDS",
    "NAV_NOTIFICATION_CLASS",
    "NAV_QUIET_OFF_TEXT",
    "NAV_QUIET_ON_TEXT",
    "NAV_SCREEN_OFF_TEXT",
    "NAV_SCREEN_ON_TEXT",
    "NAV_STATUS_ARIA_LABEL_TEXT",
    "NAV_STATUS_SEPARATOR_TEXT",
    "NAV_TABS",
    "NAV_TOGGLE_ID",
    "NAV_TOGGLE_LABEL",
    "PANEL_LOOKUP_SCRIPT_SRC",
    "POLL_COOLDOWN_SCRIPT_SRC",
    "QUICK_ACTION_APPLIES_SENTENCE",
    "QUICK_ACTION_OFF_TEXT",
    "QUICK_ACTION_ON_TEXT",
    "QUICK_ACTION_QUIET_LABEL",
    "QUICK_ACTION_QUIET_OFF_TEXT",
    "QUICK_ACTION_QUIET_ON_TEMPLATE",
    "QUICK_ACTION_QUIET_TURN_OFF_BUTTON",
    "QUICK_ACTION_QUIET_TURN_ON_BUTTON",
    "QUICK_ACTION_SCREEN_LABEL",
    "QUICK_ACTION_SWITCH_OFF_BUTTON",
    "QUICK_ACTION_SWITCH_ON_BUTTON",
    "QUICK_STATE_FIELD",
    "QUICK_STATE_OFF",
    "QUICK_STATE_OFF_ATTR",
    "QUICK_STATE_ON",
    "QUICK_STATE_ON_ATTR",
    "QUICK_SWITCH_CONTROL_ATTR",
    "QUICK_SWITCH_FAILED_ATTR",
    "QUICK_SWITCH_FAILED_TEXT",
    "QUICK_SWITCH_QUIET_LABEL_ID",
    "QUICK_SWITCH_QUIET_STATE_ID",
    "QUICK_SWITCH_REGION_ATTR",
    "QUICK_SWITCH_SCREEN_LABEL_ID",
    "QUICK_SWITCH_SCREEN_STATE_ID",
    "QUICK_SWITCH_SCRIPT_SRC",
    "QUICK_TOAST_ATTR",
    "REFRESH_LIVE_DOT_ATTR",
    "REFRESH_NEW_ROW_CLASS",
    "REFRESH_PAGE_ATTR",
    "REFRESH_PAGE_DISPLAY",
    "REFRESH_PAGE_FLIGHTS",
    "REFRESH_PAGE_HEALTH",
    "REFRESH_PAGE_HOME",
    "REFRESH_PAUSED_ATTR",
    "REFRESH_PAUSED_TEXT",
    "REFRESH_PENDING_ATTR",
    "REFRESH_PILL_TEXT",
    "REFRESH_RECONNECTING_ATTR",
    "REFRESH_RECONNECTING_TEXT",
    "REFRESH_ROW_ID_ATTR",
    "REFRESH_SWAP_SELECTORS_BY_PAGE",
    "REFRESH_TOKEN_ATTR",
    "RELATIVE_COUNTDOWN_ATTR",
    "RELATIVE_FUTURE_ATTRS",
    "RELATIVE_FUTURE_DAYS_TEXT",
    "RELATIVE_FUTURE_HOURS_TEXT",
    "RELATIVE_FUTURE_MINUTES_TEXT",
    "RELATIVE_FUTURE_SECONDS_TEXT",
    "RELATIVE_PAST_ATTRS",
    "RELATIVE_PAST_DAYS_TEXT",
    "RELATIVE_PAST_HOURS_TEXT",
    "RELATIVE_PAST_MINUTES_TEXT",
    "RELATIVE_PAST_SECONDS_TEXT",
    "RELATIVE_QUANTITY_MARK",
    "RELATIVE_TIME_SCRIPT_SRC",
    "RELATIVE_WAITING_ATTR",
    "RELATIVE_WAITING_TEXT",
    "SITE_TITLE",
    "SKIP_LINK_TARGET_ID",
    "STAT_TILE_ICON_CLASS",
    "SUBMIT_GUARD_SCRIPT_SRC",
    "TAB_BAR_BODY_CLASS",
    "TAB_BAR_MORE_ICON_ID",
    "TAB_BAR_MORE_LABEL",
    "THEME_PREVIEW_SCRIPT_SRC",
    "UI_THEME_CHOICES",
    "UI_THEME_COOKIE_NAME",
    "VALUE_CONTROLS_SCRIPT_SRC",
    "VALUE_CONTROL_ATTR",
    "VALUE_CONTROL_FIELD_ATTR",
    "VALUE_CONTROL_FORMAT_ATTR",
    "VALUE_CONTROL_FORMAT_CLOCK",
    "VALUE_CONTROL_FORM_ATTR",
    "VALUE_CONTROL_GEOMETRY_ATTR",
    "VALUE_CONTROL_HANDLE_ATTR",
    "VALUE_CONTROL_INPUT_ATTR",
    "VALUE_CONTROL_MAX_ATTR",
    "VALUE_CONTROL_MIN_ATTR",
    "VALUE_CONTROL_READOUT_ATTR",
    "VALUE_CONTROL_READOUT_BASE_ATTR",
    "VALUE_CONTROL_READOUT_FORMAT_ATTR",
    "VALUE_CONTROL_READOUT_SCALE_ATTR",
    "VALUE_CONTROL_READOUT_TEXT_ATTR",
    "VALUE_CONTROL_STEP_ATTR",
    "VALUE_CONTROL_TEXT_ATTR",
    "VALUE_CONTROL_TEXT_TOKEN",
    "VALUE_CONTROL_TRACK_ATTR",
    "_AGE_UNIT_SUFFIX_FR",
    "_CARD_STATUS_SUFFIXES",
    "_DEFAULT_STATUS_DOT_CLASS",
    "_DEFAULT_STAT_TILE_CLASS",
    "_FLASH_ROLES",
    "_FRAME_DELAY_DUE_TEXT",
    "_FRAME_DELAY_HELD_TEXT",
    "_FRAME_DELAY_UNKNOWN_TEXT",
    "_FRAME_DOT_CLASS_BY_STATE",
    "_FRAME_HEADLINE_DUE_TEXT",
    "_FRAME_HEADLINE_HELD_TEXT",
    "_FRAME_HEADLINE_LATE_TEXT",
    "_FRAME_QUIET_SCHEDULE_LINK_TEXT",
    "_FRAME_QUIET_SCHEDULE_TARGET_ID",
    "_FULL_TIMESTAMP_SENTINEL_NOW",
    "_MONTH_ABBR",
    "_MONTH_ABBR_FR",
    "_RELATIVE_FUTURE_TEXTS",
    "_RELATIVE_PAST_TEXTS",
    "_STATUS_DOT_CLASSES",
    "_STAT_TILE_BORDER_CLASSES",
    "_age_bucket",
    "_frame_strip_cell_html",
    "_health_alert_markup",
    "_lang_form_html",
    "_logout_form_html",
    "_machine_instant",
    "_mobile_nav_html",
    "_nav_groups",
    "_nav_links",
    "_tab_bar_cell_body",
    "_tab_bar_html",
    "_theme_form_html",
    "absolute_and_relative",
    "age_seconds",
    "anomaly_banner",
    "card_status_class",
    "concise_timestamp_html",
    "data_table",
    "duration_text",
    "empty_state",
    "escape_html",
    "flash_banner",
    "frame_strip_html",
    "freshness_line_html",
    "full_local_timestamp_text",
    "icon_html",
    "local_clock_text",
    "month_abbr",
    "nav_slug",
    "nav_status_html",
    "page_header",
    "parse_iso",
    "quick_switch_html",
    "quick_switch_state_html",
    "relative_age_text",
    "relative_copy_attrs",
    "relative_future_text",
    "relative_time_html",
    "section_intro_html",
    "sidebar_nav",
    "stat_tile",
    "status_dot",
    "status_row",
    "ui_theme_from_cookie",
    "GLOBAL_PAGE_SCRIPTS",
    "SHELL_SCRIPT_ORDER",
    "login_shell",
    "page_shell",
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
    return (
        "<!DOCTYPE html>\n"
        '<html lang="%s" data-ui-theme="%s">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>%s - %s</title>\n"
        '<link rel="stylesheet" href="/static/style.css">\n'
        "%s\n"
        "</head>\n"
        "<body>\n"
        '<div class="login-shell">\n'
        '<div class="login-card">\n'
        "%s\n"
        "</div>\n"
        "</div>\n"
        '<script src="%s" defer></script>\n'
        "</body>\n"
        "</html>\n"
    ) % (
        escape_html(resolved_lang),
        escape_html(resolved_theme),
        # Only "Login" is translated; SITE_TITLE is a brand name and stays
        # untranslated, so the title keeps the same "<page> - <product>" shape as
        # page_shell()'s <title>.
        escape_html(i18n.t("Login")),
        escape_html(SITE_TITLE),
        FAVICON_LINK_HTML,
        body,
        LOGIN_CARD_SCRIPT_SRC,
    )


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
    POLL_COOLDOWN_SCRIPT_SRC,
    CONFIRM_SUBMIT_SCRIPT_SRC,
    THEME_PREVIEW_SCRIPT_SRC,
    FLIGHT_ROWS_SCRIPT_SRC,
    SUBMIT_GUARD_SCRIPT_SRC,
    RELATIVE_TIME_SCRIPT_SRC,
    QUICK_SWITCH_SCRIPT_SRC,
    VALUE_CONTROLS_SCRIPT_SRC,
)

# Present on every authenticated page_shell() document regardless of its
# `scripts` argument: the hamburger (every page has the nav), a flash
# cleanup (any page can carry `?flash=`), every form's submit guard, and
# the nav status line's relative time.
GLOBAL_PAGE_SCRIPTS = (
    NAV_DROPDOWN_SCRIPT_SRC,
    FLASH_CLEANUP_SCRIPT_SRC,
    SUBMIT_GUARD_SCRIPT_SRC,
    RELATIVE_TIME_SCRIPT_SRC,
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
    `None`, the same no-context degrade, threaded to both nav renderers via
    nav_status_html().

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
    unknown_scripts = set(scripts) - set(SHELL_SCRIPT_ORDER)
    if unknown_scripts:
        raise ValueError(
            "page_shell(): scripts=%r is not in SHELL_SCRIPT_ORDER"
            % (sorted(unknown_scripts),))
    wanted_scripts = set(GLOBAL_PAGE_SCRIPTS) | set(scripts)
    script_tags_html = "".join(
        '<script src="%s" defer></script>\n' % src
        for src in SHELL_SCRIPT_ORDER if src in wanted_scripts)
    resolved_theme = ui_theme if ui_theme in UI_THEME_CHOICES else "auto"
    resolved_lang = lang if lang in prefs.LANG_CHOICES else prefs.current_lang()
    sidebar_html = sidebar_nav(
        active, health_alert=health_alert, device_config=device_config)
    theme_form_html = _theme_form_html(resolved_theme)
    lang_form_html = _lang_form_html(resolved_lang)
    mobile_nav_html = _mobile_nav_html(
        active, theme_form_html, health_alert=health_alert,
        lang_form_html=lang_form_html, device_config=device_config)
    # "" when `device_config` is falsy (no session, e.g. 404/preview-image
    # pages), so `<body>` carries TAB_BAR_BODY_CLASS only when the bar is really
    # present — letting companion/static/style.css reserve the bar's clearance
    # only on pages that have one.
    tab_bar_html = _tab_bar_html(
        active, health_alert=health_alert, device_config=device_config)
    body_class_attr = (
        ' class="%s"' % TAB_BAR_BODY_CLASS if tab_bar_html else "")
    # freshness.js's two neutral loop-state strings, translated here and read
    # client-side; see their constants above for why they live on <body>.
    body_class_attr += (
        ' %s="%s" %s="%s"' % (
            REFRESH_PAUSED_ATTR,
            escape_html(i18n.t(REFRESH_PAUSED_TEXT)),
            REFRESH_RECONNECTING_ATTR,
            escape_html(i18n.t(REFRESH_RECONNECTING_TEXT))))
    # The page key selecting this document's swap-region list out of
    # REFRESH_SWAP_SELECTORS_BY_PAGE. Lives on <body> because it, like the other
    # attributes here, sits beside elements that are themselves swap targets, and
    # <body> is the one element no swap ever replaces. Rendered for every page; an
    # unknown key selects nothing.
    body_class_attr += ' %s="%s"' % (
        REFRESH_PAGE_ATTR, escape_html(active))
    # The freshness token itself, rendered only when the
    # caller has one - /device and /airlines (not refresh pages) and the
    # rejected-settings-save re-render never pass refresh_token, so they
    # carry no such attribute at all.
    if refresh_token is not None:
        body_class_attr += ' %s="%s"' % (
            REFRESH_TOKEN_ATTR, escape_html(refresh_token))
    # The optimistic switch's user-facing sentence, translated here and read
    # client-side, on <body> for the same swap-safety reason as the attributes
    # above — emitted unconditionally; a page with no switch carries one inert
    # attribute.
    body_class_attr += ' %s="%s"' % (
        QUICK_SWITCH_FAILED_ATTR, escape_html(i18n.t(QUICK_SWITCH_FAILED_TEXT)))
    # relative-time.js's nine wordings, on <body> for the same swap-safety
    # reason. Emitted unconditionally; a page with no relative time carries nine
    # inert attributes.
    for _copy_attr, _copy_text in relative_copy_attrs():
        body_class_attr += ' %s="%s"' % (_copy_attr, escape_html(_copy_text))
    flash_html = flash or ""
    banner_html = banner or ""

    # `body` is an opaque pre-built string, so page_header() leaves
    # FLASH_SLOT_MARKER as a literal splice point below the header. A page
    # built on page_header() gets the marker replaced and `flash_html`
    # cleared; other pages keep their old before-body slot. The second
    # replace() below strips any leftover marker unconditionally.
    if FLASH_SLOT_MARKER in body:
        body = body.replace(FLASH_SLOT_MARKER, flash_html, 1)
        flash_html = ""
    body = body.replace(FLASH_SLOT_MARKER, "")

    # The sidebar's theme picker and Sign out control, grouped in one footer
    # region. Order: language, theme, Sign out — this and _mobile_nav_html()'s
    # own footer_html must change together.
    sidebar_footer_html = (
        '<div class="sidebar-footer">%s%s%s</div>'
        % (lang_form_html, theme_form_html, _logout_form_html()))

    # The first focusable element in <body>, before even ICON_DEFS_HTML — a
    # keyboard/screen-reader user's very first tab stop on every page.
    skip_link_html = (
        '<a class="skip-link" href="#%s">Skip to content</a>'
        % SKIP_LINK_TARGET_ID)

    # <aside> precedes <header> in source order: at desktop width, where
    # CSS hides the header, a keyboard user tabs into the sidebar nav
    # first. Both nav copies stay in the DOM always; only the 960px CSS
    # media query decides which is visible, so exactly one navigation
    # landmark is ever exposed to the accessibility tree.

    # ICON_DEFS_HTML is emitted once per document, right after <body>.
    # The theme form renders once in the sidebar and once in the
    # hamburger dropdown, never a third time in the header.
    return (
        "<!DOCTYPE html>\n"
        '<html lang="%s" data-ui-theme="%s">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>%s - %s</title>\n"
        '<link rel="stylesheet" href="/static/style.css">\n'
        "%s\n"
        "</head>\n"
        "<body%s>\n"
        "%s\n"
        "%s\n"
        '<div class="dashboard-shell">\n'
        '<aside class="dashboard-sidebar">\n'
        '<span class="site-title sidebar-title">%s</span>\n'
        "%s\n"
        "%s\n"
        "</aside>\n"
        '<header class="site-header">\n'
        '<span class="site-title">%s</span>\n'
        "%s\n"
        "</header>\n"
        '<main class="page-content dashboard-main" id="%s" tabindex="-1">\n'
        "%s\n%s\n%s\n"
        "</main>\n"
        "</div>\n"
        # The tab bar sits outside .dashboard-shell, a sibling rather than
        # a descendant of the scrolled content column, so its
        # `position: fixed` box is not nested inside the shell's own
        # stacking context. `""` on a page with no bar, like the flash slot.
        "%s\n"
        # The optimistic switch's failure announcement: rendered empty,
        # once per document, never hidden — a live region added at
        # announce time is one screen readers often miss. role="alert"
        # implies aria-live="assertive" for a failure the user awaits.

        # The one script-only surface here, and additive: with no script
        # there is no fetch, so nothing here can fail beyond what the
        # server's own flash already reports.
        '<div class="quick-toast" %s role="alert"></div>\n'
        "%s"
        "</body>\n"
        "</html>\n"
    ) % (
        escape_html(resolved_lang),
        escape_html(resolved_theme),
        escape_html(title), escape_html(SITE_TITLE),
        FAVICON_LINK_HTML,
        body_class_attr,
        skip_link_html,
        ICON_DEFS_HTML,
        escape_html(SITE_TITLE),
        sidebar_html,
        sidebar_footer_html,
        escape_html(SITE_TITLE),
        mobile_nav_html,
        SKIP_LINK_TARGET_ID,
        flash_html, banner_html, body,
        tab_bar_html,
        QUICK_TOAST_ATTR,
        # GLOBAL_PAGE_SCRIPTS on every authenticated page, plus `scripts`'s
        # own additions, each emitted at most once, in SHELL_SCRIPT_ORDER's
        # fixed relative order - see script_tags_html above.
        script_tags_html,
    )
