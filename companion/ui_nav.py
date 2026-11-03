"""companion/ui_nav.py: the two navigation renderers (desktop sidebar, sub-960px
bottom tab bar and its hamburger preferences panel) plus the language/theme
switch forms and sign-out control they share, and the freshness-swap
registry (`REFRESH_*` constants, `REFRESH_SWAP_SELECTORS_BY_PAGE`) that
companion/static/freshness.js mirrors. Depends on companion.ui_base for the
route/label tables, icon lookup and escaping, plus companion.i18n/
companion.prefs and companion.auth's theme-cookie name; no import from
ui_components or ui_shell.
"""
from typing import NamedTuple

import companion.console_routes as console_routes
import companion.device_scope as device_scope
import companion.i18n as i18n
import companion.prefs as prefs
from companion.auth import UI_THEME_COOKIE_NAME
from companion.ui_base import (
    ADVANCED_GROUP_LABEL,
    AIRLINES_ROUTE,
    DEVICE_ROUTE,
    DISPLAY_ROUTE,
    FLIGHTS_ROUTE,
    HEALTH_ALERT_SUFFIX_TEXT,
    HEALTH_ANOMALY_CLASS,
    HEALTH_SOURCE_FAULT_CLASS,
    HEALTH_ROUTE,
    HOME_ROUTE,
    MOBILE_NAV_ID,
    NAV_ICON_IDS,
    NAV_NOTIFICATION_CLASS,
    NAV_TABS,
    NAV_TOGGLE_ID,
    NAV_TOGGLE_LABEL,
    UI_THEME_CHOICES,
    _DEFAULT_STATUS_DOT_CLASS,
    _STATUS_DOT_CLASSES,
    escape_html,
    icon_html,
    nav_slug,
)

# Hoisted from what used to be inline i18n.t() literals below, so every
# string this module passes to i18n.t()/i18n.t_lang() is a module-level
# Message.
_PRIMARY_NAVIGATION_TEXT = i18n.msg("nav.primary_navigation", "Primary navigation")
_THEME_TEXT = i18n.msg("nav.theme", "Theme")
_LANGUAGE_TEXT = i18n.msg("nav.language", "Language")
_SIGN_OUT_TEXT = i18n.msg("common.sign_out", "Sign out")

# The one destination a plain user can reach. The nav a user sees is built
# from this table instead of NAV_TABS, so a link exists only for a route
# that role can open.
ACCOUNT_ROUTE = "/account"
ACCOUNT_NAV_SLUG = nav_slug(ACCOUNT_ROUTE)
USER_NAV = (
    (ACCOUNT_ROUTE, i18n.msg("account.account", "Account")),
)

USER_ROLE = "user"

# A user's own locations list, linked only once its page route exists.
LOCATIONS_ROUTE = "/locations"
_LOCATIONS_LABEL = i18n.msg("nav.locations", "Locations")

# The frame pages a user's sidebar offers, in order, and the subset the
# phone tab bar carries (Account closes the bar). Health is a technical
# page: a user reaches it from the Home status card, not from navigation.
_USER_SIDEBAR_PAGES = (HOME_ROUTE, FLIGHTS_ROUTE, DISPLAY_ROUTE, AIRLINES_ROUTE)
_USER_TAB_PAGES = (HOME_ROUTE, FLIGHTS_ROUTE, DISPLAY_ROUTE)


def is_user_principal():
    """True when the request's principal is a plain user (role "user")."""
    principal = prefs.current_principal()
    return principal is not None and principal[1] == USER_ROLE


ADMIN_ROLE = "admin"


def is_admin_principal():
    """True when the request's principal is an administrator."""
    principal = prefs.current_principal()
    return principal is not None and principal[1] == ADMIN_ROLE


# The two spaces an administrator moves between. The space follows the page
# being rendered (its nav slug), never anything the request carries.
CONSOLE_SPACE = "console"
MY_VIEWS_SPACE = "my-views"

_AUDIT_BAR_LABEL = i18n.msg("nav.audit_short", "Audit")
_MY_VIEWS_LABEL = i18n.msg("nav.my_views", "My views")
_CONSOLE_LABEL = i18n.msg("nav.console", "Console")
_SWITCH_TO_MY_VIEWS_TEXT = i18n.msg(
    "nav.switch_to_my_views", "Switch to your own views")
_SWITCH_TO_CONSOLE_TEXT = i18n.msg(
    "nav.switch_to_console", "Switch to the administration console")
_ACCOUNT_ICON_ID = "icon-gear"
_CONSOLE_ICON_IDS = {
    "fleet": "icon-device",
    "users": "icon-corroboration",
    "locations": "icon-pipeline",
    "audit": "icon-nav-history",
    "releases": "icon-nav-update",
}
_CONSOLE_SLUGS = frozenset(
    nav_slug(path) for _key, path, _label in console_routes.CONSOLE_NAV_ENTRIES)


class _Entry(NamedTuple):
    """One navigation destination: a final href, a label Message (or text),
    the slug that marks it current, an icon id and its current state."""
    href: str
    label: object
    slug: str
    icon: str
    is_active: bool


def current_space(active):
    """The space the page `active` belongs to, or None for a plain user.
    Console pages are the administration routes; every other page, the
    personal ones included, is My views.
    """
    if is_user_principal():
        return None
    return CONSOLE_SPACE if active in _CONSOLE_SLUGS else MY_VIEWS_SPACE


def _frame_entry(route, active):
    labels = dict(NAV_TABS)
    slug = nav_slug(route)
    return _Entry(
        device_scope.scoped(route), labels[route], slug,
        NAV_ICON_IDS.get(slug, ""), slug == active)


def _account_entry(active):
    return _Entry(
        device_scope.scoped(ACCOUNT_ROUTE), USER_NAV[0][1], ACCOUNT_NAV_SLUG,
        _ACCOUNT_ICON_ID, ACCOUNT_NAV_SLUG == active)


def _console_entries(active):
    """The Console destinations whose GET page exists, by key."""
    entries = {}
    for key, path, label in console_routes.available_nav_entries():
        slug = nav_slug(path)
        entries[key] = _Entry(
            path, label, slug, _CONSOLE_ICON_IDS.get(key, ""), slug == active)
    return entries


def _switch_target(space):
    """(href, label, aria-label) of the link leading out of `space`, or None
    when the destination page does not exist."""
    if space == CONSOLE_SPACE:
        return (HOME_ROUTE, _MY_VIEWS_LABEL, _SWITCH_TO_MY_VIEWS_TEXT)
    if console_routes.available_nav_entries():
        return (console_routes.ADMIN_TAB_ROUTE, _CONSOLE_LABEL, _SWITCH_TO_CONSOLE_TEXT)
    return None


def space_switch_html(active, variant="header"):
    """The admin-only link between the two spaces, or "" for every other
    caller. `variant` is "header" (phone) or "sidebar" (desktop); the label
    names the destination."""
    if not is_admin_principal():
        return ""
    target = _switch_target(current_space(active))
    if target is None:
        return ""
    href, label, aria = target
    return '<a class="space-switch space-switch--%s" href="%s" aria-label="%s">%s</a>' % (
        variant, escape_html(href), escape_html(i18n.t(aria)),
        escape_html(i18n.t(label)))


def _switch_entry(space):
    """The space switch as a plain More-sheet entry, or None (not an admin,
    or no destination page)."""
    target = _switch_target(space) if is_admin_principal() else None
    if target is None:
        return None
    href, label, _aria = target
    return _Entry(href, label, "", "", False)


def ui_theme_from_cookie(cookies):
    """Return the UI theme named by `cookies`, or "auto" when the cookie is
    missing or holds a value outside UI_THEME_CHOICES.

    Membership test before use: a client-controlled cookie value is never
    trusted as-is.
    """
    if not isinstance(cookies, dict):
        return "auto"
    value = cookies.get(UI_THEME_COOKIE_NAME)
    return value if value in UI_THEME_CHOICES else "auto"


# The navigation renderers, sidebar_nav() and _tab_bar_html(), are fed by
# the same per-space entry lists, so the two can never disagree about which
# destinations a space holds. A horizontally-scrollable nav strip used to
# render here; real-device testing found it hid most tabs behind an
# undiscoverable swipe, so it was replaced rather than repaired.


def _health_alert_markup(severity):
    """The Health nav-tab notification dot plus its visually-hidden
    screen-reader suffix, built once so every nav renderer shares one
    markup source. `severity` is "warn" or "error"; the dot class comes
    from the same `_STATUS_DOT_CLASSES` dict status_dot() uses.

    Appends a visually-hidden text suffix rather than an `aria-label`:
    an `aria-label` would replace the link's accessible name, dropping
    the word "Health". The absence of this markup is the all-clear
    signal: nothing renders when everything is fine.
    """
    dot_class = _STATUS_DOT_CLASSES.get(severity, _DEFAULT_STATUS_DOT_CLASS)
    return (
        '<span class="dot %s %s"></span>'
        '<span class="visually-hidden">%s</span>'
    ) % (dot_class, NAV_NOTIFICATION_CLASS, escape_html(i18n.t(HEALTH_ALERT_SUFFIX_TEXT)))


def _user_can_open(route):
    """True when a GET route for `route` exists and a plain user may open
    it, so a link is emitted only for a page that is reachable."""
    from companion import access, routes
    found = routes.match("GET", route, "")
    if found is None:
        return False
    return access.RANK[found[0].access.min_role] <= access.RANK[access.USER]


def _user_frame_links(pages):
    """(route, label) for each of `pages` a user may open, in order, and
    only while the request scope holds at least one frame."""
    if not device_scope.current_devices():
        return []
    labels = dict(NAV_TABS)
    return [(route, labels[route]) for route in pages if _user_can_open(route)]


def user_brand_href():
    """Where a user's wordmark leads: the request-scope frame's Home when
    the user can open it, else Account."""
    if _user_frame_links((HOME_ROUTE,)):
        return device_scope.scoped(HOME_ROUTE)
    return ACCOUNT_ROUTE


def _user_sidebar_links():
    """Every (route, label) in a user's sidebar: the reachable frame pages,
    Locations once that page exists, then Account."""
    links = _user_frame_links(_USER_SIDEBAR_PAGES)
    if _user_can_open(LOCATIONS_ROUTE):
        links.append((LOCATIONS_ROUTE, _LOCATIONS_LABEL))
    return links + list(USER_NAV)


def _sidebar_link_html(entry, alert_html=""):
    css_class = (
        "sidebar-link sidebar-link--active" if entry.is_active else "sidebar-link")
    aria_current = ' aria-current="page"' if entry.is_active else ""
    return '<a class="%s" href="%s"%s>%s%s%s</a>' % (
        css_class, escape_html(entry.href), aria_current,
        icon_html(entry.icon, extra_class="sidebar-link__icon"),
        escape_html(i18n.t(entry.label)), alert_html)


def _nav_landmark_html(parts):
    # "Primary navigation" is the one nav landmark exposed to the
    # accessibility tree at any given viewport width (see this module's own
    # comment above _mobile_nav_html()).
    return '<nav class="sidebar-nav" aria-label="%s">%s</nav>' % (
        escape_html(i18n.t(_PRIMARY_NAVIGATION_TEXT)), "".join(parts))


def _user_sidebar_nav(active):
    """The sidebar for a plain user: the frame pages of the request-scope
    frame, Locations and Account, each present only when reachable. No group
    headings and no Health dot."""
    links = []
    for route, label in _user_sidebar_links():
        slug = nav_slug(route)
        links.append(_sidebar_link_html(_Entry(
            device_scope.scoped(route), label, slug, "", slug == active)))
    return _nav_landmark_html(links)


def _group_html(links, label_html="", extra_class=""):
    """A bordered sidebar group: an optional small label above its links."""
    label = (
        '<span class="nav-group__label text-label">%s</span>' % label_html
        if label_html else "")
    return '<div class="nav-group%s">%s%s</div>' % (extra_class, label, "".join(links))


def _console_sidebar_parts(active):
    entries = _console_entries(active)
    eyebrow = escape_html(i18n.t(console_routes.ADMINISTRATION_LABEL))
    links = [_sidebar_link_html(entry) for entry in entries.values()]
    return [
        _group_html(links, eyebrow, " nav-group--console"),
        _group_html([_sidebar_link_html(_account_entry(active))])]


def _my_views_sidebar_parts(active, health_alert):
    everyday = [
        _sidebar_link_html(_frame_entry(route, active))
        for route in (HOME_ROUTE, DISPLAY_ROUTE, FLIGHTS_ROUTE, AIRLINES_ROUTE)]
    alert_html = (
        _health_alert_markup(health_alert) if health_alert in ("warn", "error") else "")
    advanced = [
        _sidebar_link_html(_frame_entry(HEALTH_ROUTE, active), alert_html),
        _sidebar_link_html(_frame_entry(DEVICE_ROUTE, active))]
    return everyday + [
        _group_html(
            advanced, escape_html(i18n.t(ADVANCED_GROUP_LABEL)),
            " nav-group--advanced"),
        _group_html([_sidebar_link_html(_account_entry(active))])]


def sidebar_nav(active, health_alert=None, device_config=None):
    """The vertical Primary-navigation landmark shown by page_shell()'s
    dashboard sidebar column at desktop width. Its content follows the
    caller's space (see current_space()); the 960px CSS media query, not this
    function, decides whether sidebar_nav() or _mobile_nav_html() is
    visible.

    `health_alert` is `None`/`"ok"` for no dot, or `"warn"`/`"error"` to
    append _health_alert_markup() after the My views Health link's label.
    The active link's `<a>` carries `aria-current="page"` and the inactive
    ones never do.

    `device_config` remains accepted because page_shell() provides one shared
    rendering context to both navigation variants.
    """
    if is_user_principal():
        return _user_sidebar_nav(active)
    parts = [space_switch_html(active, "sidebar")]
    if current_space(active) == CONSOLE_SPACE:
        parts += _console_sidebar_parts(active)
    else:
        parts += _my_views_sidebar_parts(active, health_alert)
    return _nav_landmark_html(parts)


# The bottom tab bar's "More" cell label. Sentence case, and not the
# label voice — a nav destination is a destination, not a label, which
# is why companion/static/style.css's `.tab-bar__label` declares no
# uppercase and no tracking.
TAB_BAR_MORE_LABEL = i18n.msg("nav.more", "More")

# The glyph on that cell. A whitelist member (ICON_IDS above), so
# icon_html()'s own fallback contract applies unchanged.
TAB_BAR_MORE_ICON_ID = "icon-more"

# The `<body>` marker page_shell() adds only when the tab bar really
# renders. companion/static/style.css scopes the sub-960px page-foot
# clearance to it, so pages that render no bar reserve no space for
# one.
TAB_BAR_BODY_CLASS = "has-tab-bar"

# companion/static/freshness.js shows a visible neutral badge when its
# refresh loop is retrying or idle, instead of stopping dead. The badge
# is built client-side, so its two strings are server-rendered onto
# <body> and read with getAttribute().

# They live on <body> rather than on the pill: the pill's freshness
# wrapper is a swap target, and an attribute there would be replaced out
# from under the script on every refresh.

# Emitted unconditionally, like the deferred scripts below: most pages
# carry no refresh loop, and the attributes are inert there.
REFRESH_PAUSED_TEXT = i18n.msg("common.paused", "Paused")
REFRESH_RECONNECTING_TEXT = i18n.msg("common.reconnecting", "Reconnecting…")

# Must equal the attribute names companion/static/freshness.js reads.
REFRESH_PAUSED_ATTR = "data-refresh-paused-text"
REFRESH_RECONNECTING_ATTR = "data-refresh-reconnecting-text"


# freshness.js used to carry a hard-coded selector list, duplicated and
# pinned equal elsewhere — three hand-maintained copies is a shape this
# codebase has learned not to build: they drift silently after the day
# they are written.

# One mapping here, one page key rendered on <body>, and one object
# literal in the script mirroring this, pinned entry-for-entry and
# key-for-key by companion/test_status_pages.py in both directions. The
# keys are nav_slug()'s own values, never a second vocabulary.
# The freshness token: a conditional GET on the page's own URL,
# computed from its inputs without ever rendering it, rather than a new
# route or a body-hash ETag. Rendered on <body> - never on
# the freshness wrapper itself, which is a swap target - so a swap can
# never carry it out from under companion/static/freshness.js.
REFRESH_TOKEN_ATTR = "data-refresh-token"
REFRESH_PAGE_ATTR = "data-refresh-page"
REFRESH_PAGE_HOME = nav_slug(HOME_ROUTE)
REFRESH_PAGE_DISPLAY = nav_slug(DISPLAY_ROUTE)
REFRESH_PAGE_HEALTH = nav_slug(HEALTH_ROUTE)
REFRESH_PAGE_FLIGHTS = nav_slug(FLIGHTS_ROUTE)

# The two cross-file literals the new-row highlight is built on,
# duplicated into freshness.js rather than imported, and pinned equal by
# companion/test_status_pages.py.

# REFRESH_ROW_ID_ATTR carries a stable identity for the EVENT a row
# describes, not its position: a highlight keyed to position would light
# up every row below an insertion. Rendered from the runway_events row's
# own primary key.
REFRESH_ROW_ID_ATTR = "data-flight-id"
# The class freshness.js adds to a row whose identity was not in the
# set it knew before the swap. One-shot by construction: the node it
# lands on was itself just inserted, and the next swap replaces that
# node entirely.
REFRESH_NEW_ROW_CLASS = "is-new-row"

# The marker a region carries while it holds an OPTIMISTIC control whose
# server confirmation has not arrived. The swap skips it, since
# repainting with the server's older answer would make the control
# appear to bounce back. Duplicated into freshness.js, pinned by
# companion/test_status_pages.py.
REFRESH_PENDING_ATTR = "data-pending"

# The single, greppable definition of every DOM region freshness.js
# swaps wholesale, replacing each node with its fetched equivalent.
# Duplicated rather than imported — freshness.js is a static asset, not
# a Python module.

# HEALTH: swaps each row's <summary> (state icon, verdict, value) and
# nothing else inside the rows card. The row's <details> and its body are
# never replaced: a replaced <details> would close a row the visitor had
# opened, and a replaced body would leave battery-trend.js's chart
# permanently dead (it captures its DOM once). The registry card and its
# filter bar are excluded for list-filter.js's sake.

# `a[href$="/health"]`, not a ".dot" selector, is the nav-severity target
# (an ends-with match, so the prefixed link on a device page is found too):
# the severity dot only exists in the DOM for "warn"/"error", so a
# dot-only selector would have nothing to replace when severity clears.

# HOME: the regions that change between polls, plus the silent refresh
# marker. The recent-flights SECTION, not its <ul>, is the target so the
# empty-state-to-list transition is covered too. The frame-state card is
# swapped whole: its two buttons are plain POST forms with no half-typed
# value to lose. Not nested.

# FLIGHTS: both renderings of the list (phone cards, desktop table) plus
# the count and freshness line — a swap replacing only one would leave
# the other stale after a resize.

# Deliberately excluded: list-filter.js resolves four elements once at
# load and holds those references; replacing any detaches the node it
# writes to, silently killing the filter. `[data-filter-count]` is here
# since the script now looks it up fresh on every keystroke.

# The rows themselves were never captured (list-filter.js queries them
# fresh), so swapping them costs nothing; the filter's applied state
# does need list-filter.js to re-run after a swap, since the server
# renders the list unfiltered.

# DISPLAY: only the strip and freshness line — a deliberate asymmetry
# with Home. Everything else on that page is a form, and a swap must
# never touch a form: it would discard a half-typed value silently.
REFRESH_SWAP_SELECTORS_BY_PAGE = {
    REFRESH_PAGE_HOME: (
        ".page-header__freshness",
        "figure.preview-frame",
        'section[aria-labelledby="home-flights"]',
        'section[aria-labelledby="home-frame-state"]',
        ".home-facts",
    ),
    REFRESH_PAGE_DISPLAY: (
        ".page-header__freshness",
        ".frame-strip",
    ),
    REFRESH_PAGE_HEALTH: (
        ".health-row__summary",
        "div." + HEALTH_ANOMALY_CLASS,
        "section." + HEALTH_SOURCE_FAULT_CLASS,
        ".page-header__freshness",
        'a[href$="/health"]',
    ),
    REFRESH_PAGE_FLIGHTS: (
        ".page-header__freshness",
        "ul.history-cards",
        ".data-table-wrap",
        "[data-filter-count]",
    ),
}


def _tab_bar_cell_link(entry, label=None, extra_html=""):
    """One bar cell for an _Entry. `label` overrides the entry's label with
    its short bar form."""
    css_class = (
        "tab-bar__link tab-bar__link--active" if entry.is_active else "tab-bar__link")
    aria_current = ' aria-current="page"' if entry.is_active else ""
    return '<a class="%s" href="%s"%s>%s</a>' % (
        css_class, escape_html(entry.href), aria_current,
        _tab_bar_cell_body(
            entry.icon, escape_html(i18n.t(label or entry.label)), extra_html))


def _tab_bar_sheet_link(entry):
    """One More-sheet row. Reuses .mobile-nav__link, so the rows share its
    44px/16px tap-target geometry instead of duplicating the numbers.
    """
    css_class = (
        "mobile-nav__link mobile-nav__link--active"
        if entry.is_active else "mobile-nav__link")
    aria_current = ' aria-current="page"' if entry.is_active else ""
    return '<a class="%s" href="%s"%s>%s</a>' % (
        css_class, escape_html(entry.href), aria_current,
        escape_html(i18n.t(entry.label)))


def _console_bar(active):
    """(cells, sheet entries) of the Console bar: Fleet, Users, Locations and
    Audit, with Releases, My views and Account in More."""
    entries = _console_entries(active)
    cells = []
    for key in ("fleet", "users", "locations", "audit"):
        if key in entries:
            short = _AUDIT_BAR_LABEL if key == "audit" else None
            cells.append(_tab_bar_cell_link(entries[key], short))
    sheet = [entries[key] for key in ("releases",) if key in entries]
    switch = _switch_entry(CONSOLE_SPACE)
    if switch is not None:
        sheet.append(switch)
    sheet.append(_account_entry(active))
    return cells, sheet


def _my_views_bar(active, health_alert):
    """(cells, sheet entries) of the admin My views bar: Home, Display,
    Flights and Health (carrying the severity dot), with Airlines, Device,
    Account and the Console switch in More."""
    alert_html = (
        _health_alert_markup(health_alert) if health_alert in ("warn", "error") else "")
    cells = [
        _tab_bar_cell_link(
            _frame_entry(route, active),
            extra_html=alert_html if route == HEALTH_ROUTE else "")
        for route in (HOME_ROUTE, DISPLAY_ROUTE, FLIGHTS_ROUTE, HEALTH_ROUTE)]
    sheet = [_frame_entry(AIRLINES_ROUTE, active), _frame_entry(DEVICE_ROUTE, active),
             _account_entry(active)]
    switch = _switch_entry(MY_VIEWS_SPACE)
    if switch is not None:
        sheet.append(switch)
    return cells, sheet


def _tab_bar_html(active, health_alert=None, device_config=None):
    """Bottom tab bar shown below 960px, replacing the hamburger dropdown as the
    sub-960px nav.

    Four destination cells plus a "More" overflow, chosen by the caller's
    space (see current_space()). The overflow uses a native
    <details>/<summary> so it works with scripts blocked. The Health
    severity dot is drawn on the Health cell, never on More.
    Returns "" when device_config is falsy (no session context, e.g.
    login/404 pages).
    """
    if is_user_principal():
        return _user_tab_bar_html(active)
    if not device_config:
        return ""
    if current_space(active) == CONSOLE_SPACE:
        cells, sheet = _console_bar(active)
    else:
        cells, sheet = _my_views_bar(active, health_alert)
    summary_class = (
        "tab-bar__link tab-bar__link--active"
        if any(entry.is_active for entry in sheet) else "tab-bar__link")
    cells.append(
        '<details class="tab-bar__more">'
        '<summary class="%s">%s</summary>'
        '<div class="tab-bar__more-panel">%s</div>'
        "</details>"
        % (summary_class,
           _tab_bar_cell_body(
               TAB_BAR_MORE_ICON_ID, escape_html(i18n.t(TAB_BAR_MORE_LABEL))),
           "".join(_tab_bar_sheet_link(entry) for entry in sheet)))
    return (
        '<nav class="tab-bar" aria-label="%s">%s</nav>'
    ) % (
        # Same translated landmark name as sidebar_nav(); the 960px CSS breakpoint sets
        # display: none on the losing copy, so only one is ever in the accessibility
        # tree.
        escape_html(i18n.t(_PRIMARY_NAVIGATION_TEXT)),
        "".join(cells))


def _user_tab_bar_html(active):
    """A plain user's bottom tab bar: Home, Flights and Display for the
    request-scope frame, then Account. Empty without a frame, or when no
    frame page is reachable: Account alone is not navigation.
    """
    pages = _user_frame_links(_USER_TAB_PAGES)
    if not pages:
        return ""
    cells = []
    for route, label in pages + list(USER_NAV):
        slug = nav_slug(route)
        icon_id = _ACCOUNT_ICON_ID if route == ACCOUNT_ROUTE else NAV_ICON_IDS.get(slug, "")
        cells.append(_tab_bar_cell_link(_Entry(
            device_scope.scoped(route), label, slug, icon_id, slug == active)))
    return '<nav class="tab-bar" aria-label="%s">%s</nav>' % (
        escape_html(i18n.t(_PRIMARY_NAVIGATION_TEXT)), "".join(cells))


def _tab_bar_cell_body(icon_id, label, extra_html=""):
    """One tab cell's icon-above-label stack, wrapped in a pill span for the
    active/hover tint.

    The pill wraps the cell rather than replacing it, so the cell keeps its full
    78x56px tap area while the active tint is inset from the edge. `label` and
    `extra_html` arrive already escaped/safe and are interpolated verbatim.
    """
    return (
        '<span class="tab-bar__pill">%s'
        '<span class="tab-bar__label">%s</span>%s</span>'
    ) % (
        icon_html(icon_id, extra_class="tab-bar__icon"), label, extra_html)


# Longer accessible names for segments whose visible label is a short
# abbreviation; each begins with the visible text (label-in-name).
_THEME_ACCESSIBLE_TEXT = {
    "auto": i18n.msg("nav.auto_full", "Auto (follows the system)"),
}

_THEME_LABEL_TEXT = {
    "auto": i18n.msg("nav.auto", "Auto"),
    "light": i18n.msg("nav.light", "Light"),
    "dark": i18n.msg("nav.dark", "Dark"),
}


def _theme_form_html(resolved_theme):
    options = []
    for choice in UI_THEME_CHOICES:
        is_active = choice == resolved_theme
        css_class = (
            "theme-option theme-option--active"
            if is_active else "theme-option")
        accessible = _THEME_ACCESSIBLE_TEXT.get(choice)
        aria_label = (
            ' aria-label="%s"' % escape_html(i18n.t(accessible))
            if accessible else "")
        options.append(
            '<button type="submit" name="ui_theme" value="%s" class="%s" aria-pressed="%s"%s>%s</button>'
            % (escape_html(choice), css_class, "true" if is_active else "false", aria_label,
               # `choice` ("auto"/"light"/"dark") is the form's own value and stays an
               # untranslated identifier; only the rendered label text goes through i18n.t().
               escape_html(i18n.t(_THEME_LABEL_TEXT[choice]))))
    # An aria-label disambiguates this segmented group from its siblings below;
    # the theme ids ("Auto"/"Light"/"Dark") are identifiers, so only the group
    # label is translated.
    return (
        '<form class="theme-form" method="post" action="/ui-theme" aria-label="%s">%s</form>'
        % (escape_html(i18n.t(_THEME_TEXT)), "".join(options)))


def _lang_form_html(resolved_lang):
    """The FR/EN language switch, a sibling of _theme_form_html() in shape.
    "FR"/"EN" are identifiers and are never passed through i18n.t().
    """
    options = []
    for choice in prefs.LANG_CHOICES:
        is_active = choice == resolved_lang
        css_class = (
            "theme-option theme-option--active"
            if is_active else "theme-option")
        options.append(
            '<button type="submit" name="ui_lang" value="%s" class="%s" aria-pressed="%s">%s</button>'
            % (escape_html(choice), css_class, "true" if is_active else "false",
               escape_html(choice.upper())))
    return (
        '<form class="theme-form" method="post" action="/ui-lang" aria-label="%s">%s</form>'
        % (escape_html(i18n.t(_LANGUAGE_TEXT)), "".join(options)))


def _logout_form_html():
    """The POST /logout control, shared verbatim by the sidebar and mobile-nav
    footers.

    The `/logout` path is hard-coded rather than imported from companion.app to
    avoid a circular import. method="post" matters: a GET logout can be
    triggered by a stray prefetch, crawler or `<img src="/logout">`, silently
    ending a session.
    """
    return (
        '<form method="post" action="/logout" class="logout-form">'
        '<button type="submit">%s</button>'
        "</form>"
    ) % escape_html(i18n.t(_SIGN_OUT_TEXT))


def _mobile_nav_html(
        active, theme_form_html, health_alert=None, lang_form_html="",
        device_config=None):
    """The hamburger toggle and its <960px preferences panel: language/theme
    switches and Sign out. Destination links live in _tab_bar_html() instead, so
    this panel carries no navigation landmark of its own.

    The panel pushes content down in-flow (flex-basis: 100%) rather than
    overlaying it, and is always rendered closed — companion/static/
    nav-dropdown.js toggles the open class client-side, keyed off the toggle's
    aria-expanded attribute. `health_alert` is accepted but unused, kept only so
    existing call sites stay unchanged.
    """
    del health_alert
    toggle_html = (
        '<button type="button" id="%s" class="site-nav-toggle" '
        'aria-label="%s" aria-expanded="false" aria-controls="%s">%s</button>'
    ) % (
        NAV_TOGGLE_ID, escape_html(i18n.t(NAV_TOGGLE_LABEL)), MOBILE_NAV_ID,
        icon_html("icon-gear", size=24))
    # Footer order: language, theme, Sign out.
    footer_html = (
        '<div class="mobile-nav__footer">%s%s%s</div>'
        % (lang_form_html, theme_form_html, _logout_form_html()))
    # The document carries exactly two "Primary navigation" landmarks (sidebar,
    # tab bar); the 960px CSS breakpoint exposes exactly one to the accessibility
    # tree at a time.
    panel_html = (
        '<div id="%s" class="mobile-nav">'
        "%s"
        "</div>"
    ) % (
        MOBILE_NAV_ID, footer_html)
    return toggle_html + panel_html
