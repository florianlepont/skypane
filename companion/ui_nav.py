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
from companion import ui_segmented
from companion.ui_components import csrf_field
from companion.auth import UI_THEME_COOKIE_NAME
from companion.ui_base import (
    AIRLINES_ROUTE,
    DETECTION_ROUTE,
    DISPLAY_ROUTE,
    FLIGHTS_ROUTE,
    HEALTH_ALERT_SUFFIX_TEXT,
    HEALTH_ANOMALY_CLASS,
    HEALTH_SOURCE_FAULT_CLASS,
    HOME_ROUTE,
    NAV_ICON_IDS,
    NAV_NOTIFICATION_CLASS,
    NAV_SHORT_LABELS,
    NAV_TABS,
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

# The personal space's frame pages, in order: the sidebar lists all of them
# and the phone bar carries the same five, in its own order, before More. One
# table serves an administrator and a user alike. Health and Device are
# Console pages and never appear here.
_PERSONAL_SIDEBAR_PAGES = (
    HOME_ROUTE, FLIGHTS_ROUTE, DETECTION_ROUTE, DISPLAY_ROUTE, AIRLINES_ROUTE)
_PERSONAL_BAR_PAGES = (
    HOME_ROUTE, FLIGHTS_ROUTE, AIRLINES_ROUTE, DISPLAY_ROUTE, DETECTION_ROUTE)


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
PERSONAL_SPACE = "personal"

_AUDIT_BAR_LABEL = i18n.msg("nav.audit_short", "Audit")
_AIRLINES_BAR_LABEL = i18n.msg("nav.airlines_short", "Editor")
_USERS_BAR_LABEL = i18n.msg("nav.users_short", "Users")
_CONSOLE_BAR_LABELS = {
    "editor": _AIRLINES_BAR_LABEL, "audit": _AUDIT_BAR_LABEL, "users": _USERS_BAR_LABEL}
_PERSONAL_LABEL = i18n.msg("nav.my_frame", "My frame")
_CONSOLE_LABEL = i18n.msg("nav.console", "Console")
_SWITCH_TO_PERSONAL_TEXT = i18n.msg(
    "nav.switch_to_personal", "Switch to your own frame pages")
_SWITCH_TO_CONSOLE_TEXT = i18n.msg(
    "nav.switch_to_console", "Switch to the administration console")
_ACCOUNT_ICON_ID = "icon-person"
_CONSOLE_ICON_IDS = {
    "fleet": "icon-device",
    "users": "icon-corroboration",
    "audit": "icon-nav-history",
    "releases": "icon-nav-update",
    "health": "icon-nav-health",
    "device": "icon-nav-device",
    "editor": "icon-nav-airlines",
}
# The Console destinations that act on one frame: their hrefs carry the
# frame in view. The airline editor lists every frame's airlines, so its link
# carries none.
_CONSOLE_FRAME_KEYS = frozenset(("health", "device"))
# Health, Device and Releases no longer have navigation entries: their
# content lives in the Fleet view, so their pages mark Fleet as current.
_FLEET_FOLDED_SLUGS = frozenset(("health", "device", "update"))
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
    Console pages are the administration routes, Health, Device and the
    airline editor included; every other page is the personal space.
    """
    if is_user_principal():
        return None
    return CONSOLE_SPACE if active in _CONSOLE_SLUGS else PERSONAL_SPACE


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
        href = device_scope.scoped(path) if key in _CONSOLE_FRAME_KEYS else path
        is_active = slug == active or (key == "fleet" and active in _FLEET_FOLDED_SLUGS)
        # One full name per page (its title); the sidebar and the tab bar name
        # the editor with the same single word, so it never wraps.
        entries[key] = _Entry(
            href, _CONSOLE_BAR_LABELS.get(key, label) if key == "editor" else label, slug,
            _CONSOLE_ICON_IDS.get(key, ""), is_active)
    return entries


_SPACE_NAV_LABEL = i18n.msg("nav.space", "Space")
_SPACE_SEGMENTS = (
    (CONSOLE_SPACE, console_routes.ADMIN_TAB_ROUTE, _CONSOLE_LABEL, _SWITCH_TO_CONSOLE_TEXT, "icon-shield"),
    (PERSONAL_SPACE, HOME_ROUTE, _PERSONAL_LABEL, _SWITCH_TO_PERSONAL_TEXT,
     "icon-device"),
)


def _switch_target(space):
    """(href, label, aria-label) of the link leading out of `space`, or None
    when the destination page does not exist."""
    if space == CONSOLE_SPACE:
        return (HOME_ROUTE, _PERSONAL_LABEL, _SWITCH_TO_PERSONAL_TEXT)
    if console_routes.available_nav_entries():
        return (console_routes.ADMIN_TAB_ROUTE, _CONSOLE_LABEL, _SWITCH_TO_CONSOLE_TEXT)
    return None


def _space_segment_html(space, href, label, aria, icon_id, current):
    """One segment of the space switch: a plain GET link with the space
    glyph and, on the current one, a check glyph and aria-current."""
    css = "space-switch__segment"
    attrs = ""
    check = ""
    if current:
        css += " space-switch__segment--current"
        attrs = ' aria-current="page"'
        check = icon_html("icon-check", extra_class="space-switch__check")
    return '<a class="%s" href="%s" aria-label="%s"%s>%s%s<span>%s</span></a>' % (
        css, escape_html(href), escape_html(i18n.t(aria)), attrs, check,
        icon_html(icon_id), escape_html(i18n.t(label)))


def space_switch_html(active):
    """The admin-only two-segment switch between the Console and the
    administrator's own frame pages, or "" for every other caller. Both
    segments are fixed-destination GET links; the current space only decides
    which one is marked current."""
    if not is_admin_principal() or not console_routes.available_nav_entries():
        return ""
    # The Account page belongs to both spaces: no segment is marked current.
    space = None if active == ACCOUNT_NAV_SLUG else current_space(active)
    segments = "".join(
        _space_segment_html(
            name, href, label, aria, icon_id, name == space)
        for name, href, label, aria, icon_id in _SPACE_SEGMENTS)
    return '<nav class="space-switch" aria-label="%s">%s</nav>' % (
        escape_html(i18n.t(_SPACE_NAV_LABEL)), segments)


def _switch_row_html(space):
    """The More panel's space switch row for an administrator: a plain GET
    link to the other space, with that space's glyph and name. "" for
    everyone else and when the destination page does not exist."""
    target = _switch_target(space) if is_admin_principal() else None
    if target is None:
        return ""
    href, label, aria = target
    icon_id = "icon-device" if space == CONSOLE_SPACE else "icon-shield"
    return (
        '<a class="mobile-nav__link tab-bar__nav-link tab-bar__space-link" '
        'href="%s" aria-label="%s">%s<span>%s</span></a>' % (
            escape_html(href), escape_html(i18n.t(aria)),
            icon_html(icon_id, extra_class="tab-bar__nav-icon"),
            escape_html(i18n.t(label))))


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


def _personal_routes(pages):
    """Each of `pages` a user may open, in order. A signed-in principal sees
    them only while the request scope holds at least one frame; a render
    with no principal is a bare shell and lists them unscoped."""
    if prefs.current_principal() is not None and not device_scope.current_devices():
        return []
    return [route for route in pages if _user_can_open(route)]


def user_brand_href():
    """Where a user's wordmark leads: the request-scope frame's Home when
    the user can open it, else Account."""
    if _personal_routes((HOME_ROUTE,)):
        return device_scope.scoped(HOME_ROUTE)
    return ACCOUNT_ROUTE


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


def _group_html(links, label_html="", extra_class=""):
    """A bordered sidebar group: an optional small label above its links."""
    label = (
        '<span class="nav-group__label text-label">%s</span>' % label_html
        if label_html else "")
    return '<div class="nav-group%s">%s%s</div>' % (extra_class, label, "".join(links))


def _health_dot(health_alert):
    """The Health severity dot markup, or "" unless the frame is warn or error."""
    return _health_alert_markup(health_alert) if health_alert in ("warn", "error") else ""


def _console_sidebar_parts(active, health_alert):
    entries = _console_entries(active)
    eyebrow = escape_html(i18n.t(console_routes.ADMINISTRATION_LABEL))

    def links(*keys):
        return [
            _sidebar_link_html(
                entries[key], _health_dot(health_alert) if key == "fleet" else "")
            for key in keys if key in entries]

    parts = [_group_html(links("fleet", "users"), eyebrow, " nav-group--console")]
    parts.append(_group_html(links("editor", "audit")))
    parts.append(_group_html([_sidebar_link_html(_account_entry(active))]))
    return parts


def _personal_sidebar_parts(active):
    """The personal sidebar, identical for an administrator and a user: the
    reachable frame pages, then the Account footer group. No Health dot."""
    links = [
        _sidebar_link_html(_frame_entry(route, active))
        for route in _personal_routes(_PERSONAL_SIDEBAR_PAGES)]
    return links + [_group_html([_sidebar_link_html(_account_entry(active))])]


def sidebar_nav(active, health_alert=None, device_config=None):
    """The vertical Primary-navigation landmark shown by page_shell()'s
    dashboard sidebar column at desktop width. Its content follows the
    caller's space (see current_space()); the 960px CSS media query, not this
    function, decides whether sidebar_nav() or _mobile_nav_html() is
    visible.

    `health_alert` is `None`/`"ok"` for no dot, or `"warn"`/`"error"` to
    append _health_alert_markup() after the Console Health link's label; the
    personal sidebar never carries it. The active link's `<a>` carries
    `aria-current="page"` and the inactive ones never do.

    `device_config` remains accepted because page_shell() provides one shared
    rendering context to both navigation variants.
    """
    parts = []
    if current_space(active) == CONSOLE_SPACE:
        parts += _console_sidebar_parts(active, health_alert)
    else:
        parts += _personal_sidebar_parts(active)
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
# An empty marker right after the tab bar. The shell's head asks the browser to
# hold the first paint until it is parsed, so a page change's new snapshot always
# holds the whole bar (and its active pill) instead of a half-parsed page.
TAB_BAR_END_ID = "tab-bar-end"
TAB_BAR_END_HTML = '<span id="%s" hidden></span>' % TAB_BAR_END_ID

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

# The pull-to-refresh indicator's two prompts (motion.js reads them off
# <body>; the third state reuses the refresh pill's own "Updating…").
PULL_HINT_TEXT = i18n.msg("common.pull_to_refresh", "Pull to refresh")
PULL_RELEASE_TEXT = i18n.msg("common.release_to_refresh", "Release to refresh")
PULL_HINT_ATTR = "data-pull-text"
PULL_RELEASE_ATTR = "data-pull-release-text"

# The bottom sheets' grabber label (modal.js reads it off <body>).
SHEET_GRAB_TEXT = i18n.msg("common.sheet_grabber", "Drag down to close")
SHEET_GRAB_ATTR = "data-sheet-grab-text"


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
REFRESH_PAGE_FLIGHTS = nav_slug(FLIGHTS_ROUTE)
# The Console Fleet page refreshes its health rows and the Fleet navigation
# dot in place; it carries no freshness token (every tick is a full 200).
REFRESH_PAGE_FLEET = nav_slug(console_routes.FLEET_ROUTE)

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
        'section[aria-labelledby="home-detection"]',
        'section[aria-labelledby="home-frame-state"]',
        'section[aria-labelledby="home-frame-controls"]',
        ".home-facts",
    ),
    REFRESH_PAGE_DISPLAY: (
        ".page-header__freshness",
        ".frame-strip",
    ),
    REFRESH_PAGE_FLEET: (
        ".health-row__summary",
        "div." + HEALTH_ANOMALY_CLASS,
        "section." + HEALTH_SOURCE_FAULT_CLASS,
        'a[href$="/fleet"]',
    ),
    REFRESH_PAGE_FLIGHTS: (
        ".page-header__freshness",
        ".history-cards",
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


def _console_bar(active, health_alert):
    """(cells, sheet entries) of the Console bar: Fleet (carrying the severity
    dot), Users, the airline editor and the audit log, with Account and the
    switch back to the personal space in More."""
    entries = _console_entries(active)
    cells = [
        _tab_bar_cell_link(
            entries[key], _CONSOLE_BAR_LABELS.get(key),
            extra_html=_health_dot(health_alert) if key == "fleet" else "")
        for key in ("fleet", "users", "editor", "audit") if key in entries]
    return cells, [_account_entry(active)]


def _personal_bar(active):
    """(cells, sheet entries) of the personal bar, identical for an
    administrator and a user: Home, Flights, Airlines, Style and Place, with
    Account in More."""
    cells = [
        _tab_bar_cell_link(
            _frame_entry(route, active), NAV_SHORT_LABELS.get(nav_slug(route)))
        for route in _personal_routes(_PERSONAL_BAR_PAGES)]
    return cells, [_account_entry(active)]


def _account_sheet_link(entry):
    """The More sheet's Account row. It is a sheet link like the others; the
    signed-in e-mail rides along as a data attribute that the stylesheet shows
    under the page name, so the link's own text stays the page name."""
    css_class = "mobile-nav__link tab-bar__account"
    aria_current = ""
    if entry.is_active:
        css_class += " mobile-nav__link--active"
        aria_current = ' aria-current="page"'
    email = prefs.current_principal_email()
    detail = ' data-email="%s"' % escape_html(email) if email else ""
    return '<a class="%s" href="%s"%s%s>%s</a>' % (
        css_class, escape_html(entry.href), aria_current, detail,
        escape_html(i18n.t(entry.label)))


def _sheet_preference_html(label, form_html):
    return (
        '<div class="tab-bar__pref"><span class="tab-bar__pref-label">%s</span>%s</div>'
        % (escape_html(i18n.t(label)), form_html))


def _more_panel_html(active, sheet, ui_theme, space):
    """The More sheet, top to bottom: the Account row and, for an
    administrator, the row that switches to the other space; theme and
    language (one tap each, plain POST forms); Sign out.
    The Account page already carries all of its own controls, so there the
    sheet holds the links alone and a second Sign out never appears."""
    links = "".join(_account_sheet_link(entry) for entry in sheet) + _switch_row_html(space)
    links_html = '<div class="tab-bar__links">%s</div>' % links
    if active == ACCOUNT_NAV_SLUG:
        return links_html
    preferences = (
        _sheet_preference_html(_THEME_TEXT, _theme_form_html(ui_theme))
        + _sheet_preference_html(_LANGUAGE_TEXT, _lang_form_html(prefs.current_lang())))
    return (
        '<div class="tab-bar__settings">%s%s'
        '<form method="post" action="/logout" class="logout-form tab-bar__sign-out">%s'
        '<button type="submit">%s</button></form></div>' % (
            links_html, preferences, csrf_field(), escape_html(i18n.t(_SIGN_OUT_TEXT))))


def _tab_bar_html(active, health_alert=None, device_config=None, ui_theme="auto"):
    """Bottom tab bar shown below 960px, the sub-960px nav.

    The destination cells and a "More" overflow are chosen by the caller's
    space (see current_space()); an administrator's switch to the other space
    is a row of the overflow. The overflow uses a native <details>/<summary>
    so it works with scripts blocked. The Fleet severity dot is drawn on the
    Fleet cell, never on More.
    Returns "" when there is no session context: no device_config and no
    signed-in administrator (login pages, or a 404 before sign-in). An
    administrator's own Account page carries no device_config but still needs
    the bar to reach the rest of the app.
    """
    if not device_config and not is_admin_principal() and not is_user_principal():
        return ""
    space = current_space(active)
    if space == CONSOLE_SPACE:
        cells, sheet = _console_bar(active, health_alert)
    else:
        space = PERSONAL_SPACE
        cells, sheet = _personal_bar(active)
        if not cells and is_user_principal():
            return ""
    # A page that belongs to no bar cell (Credits, the component catalogue, an
    # error page) is reached through More, so More carries the pill there and
    # the sliding pill is on every page.
    in_bar = any("tab-bar__link--active" in cell for cell in cells)
    summary_class = (
        "tab-bar__link tab-bar__link--active"
        if not in_bar or any(entry.is_active for entry in sheet) else "tab-bar__link")
    # A bar that holds nothing else (the not-found page of a frame) marks More so the
    # stylesheet keeps it one cell wide instead of the whole bar.
    alone = " tab-bar__more--alone" if not cells else ""
    cells.append(
        '<details class="tab-bar__more%s">'
        '<summary class="%s">%s</summary>'
        '<div class="tab-bar__more-panel">%s</div>'
        "</details>"
        % (alone, summary_class,
           _tab_bar_cell_body(
               TAB_BAR_MORE_ICON_ID, escape_html(i18n.t(TAB_BAR_MORE_LABEL))),
           _more_panel_html(active, sheet, ui_theme, space)))
    return (
        '<nav class="tab-bar" aria-label="%s">%s</nav>'
    ) % (
        # Same translated landmark name as sidebar_nav(); the 960px CSS breakpoint sets
        # display: none on the losing copy, so only one is ever in the accessibility
        # tree.
        escape_html(i18n.t(_PRIMARY_NAVIGATION_TEXT)),
        "".join(cells))


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
    # An aria-label disambiguates this segmented group from its siblings below;
    # the theme ids ("Auto"/"Light"/"Dark") are identifiers, so only the group
    # label is translated. `choice` is the form's own value and stays an
    # untranslated identifier; only the rendered label text goes through i18n.t().
    buttons = []
    for choice in UI_THEME_CHOICES:
        accessible = _THEME_ACCESSIBLE_TEXT.get(choice)
        buttons.append((
            "ui_theme", choice, i18n.t(_THEME_LABEL_TEXT[choice]), choice == resolved_theme,
            (' aria-label="%s"' % escape_html(i18n.t(accessible))) if accessible else "", ""))
    return ui_segmented.segmented_buttons_html(
        'method="post" action="/ui-theme" aria-label="%s"' % escape_html(i18n.t(_THEME_TEXT)),
        buttons, hidden_html=csrf_field())


def _lang_form_html(resolved_lang):
    """The FR/EN language switch, a sibling of _theme_form_html() in shape.
    "FR"/"EN" are identifiers and are never passed through i18n.t().
    """
    buttons = [
        ("ui_lang", choice, choice.upper(), choice == resolved_lang, "", "")
        for choice in prefs.LANG_CHOICES]
    return ui_segmented.segmented_buttons_html(
        'method="post" action="/ui-lang" aria-label="%s"' % escape_html(i18n.t(_LANGUAGE_TEXT)),
        buttons, hidden_html=csrf_field())


def _logout_form_html():
    """The POST /logout control, shared verbatim by the sidebar and mobile-nav
    footers.

    The `/logout` path is hard-coded rather than imported from companion.app to
    avoid a circular import. method="post" matters: a GET logout can be
    triggered by a stray prefetch, crawler or `<img src="/logout">`, silently
    ending a session.
    """
    return (
        '<form method="post" action="/logout" class="logout-form">%s'
        '<button type="submit">%s</button>'
        "</form>"
    ) % (csrf_field(), escape_html(i18n.t(_SIGN_OUT_TEXT)))
