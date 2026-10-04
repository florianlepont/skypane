"""companion/ui_nav.py: the two navigation renderers (desktop sidebar, sub-960px
bottom tab bar and its hamburger preferences panel) plus the language/theme
switch forms and sign-out control they share, and the freshness-swap
registry (`REFRESH_*` constants, `REFRESH_SWAP_SELECTORS_BY_PAGE`) that
companion/static/freshness.js mirrors. Depends on companion.ui_base for the
route/label tables, icon lookup and escaping, plus companion.i18n/
companion.prefs and companion.auth's theme-cookie name; no import from
ui_components or ui_shell.
"""
import companion.i18n as i18n
import companion.prefs as prefs
from companion.auth import UI_THEME_COOKIE_NAME
from companion.ui_base import (
    DISPLAY_ROUTE,
    FLIGHTS_ROUTE,
    HEALTH_ALERT_SUFFIX_TEXT,
    HEALTH_ANOMALY_CLASS,
    HEALTH_SOURCE_FAULT_CLASS,
    HEALTH_NAV_SLUG,
    HEALTH_ROUTE,
    HOME_ROUTE,
    MOBILE_NAV_ID,
    NAV_GROUPS,
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


def _nav_links(active):
    """Return one (is_active, escaped_route, escaped_label, slug) tuple per
    NAV_TABS entry, in NAV_TABS order.

    The single place NAV_TABS is iterated and its route/label pair
    escaped; sidebar_nav() and _mobile_nav_html() both consume this (via
    _nav_groups() below) instead of re-implementing the same
    escaping/active-state logic twice. The unescaped `slug` lets a
    renderer identify a specific link (e.g. the Health nav-tab
    notification dot's target) without re-deriving it from an
    already-escaped route string.
    """
    links = []
    for route, label in NAV_TABS:
        slug = nav_slug(route)
        is_active = slug == active
        # The label is looked up through i18n.t() at render time — NAV_TABS/
        # NAV_GROUPS keep their English values; escape_html() still wraps the
        # result, exactly like any other t() call site.
        links.append((is_active, escape_html(route), escape_html(i18n.t(label)), slug))
    return links


def _nav_groups(active):
    """NAV_GROUPS in display order, each as (escaped_group_label, links)
    where `links` is the slice of _nav_links(active) belonging to that
    group. The one place the group structure is walked, so the sidebar
    and the dropdown can never disagree about which tab sits under the
    "Advanced" label.

    The Advanced group (Health, Device) renders on every page for every
    request; `/health` and `/device` were always reachable by URL and stay
    session-gated regardless.
    """
    links = _nav_links(active)
    groups = []
    offset = 0
    for group_label, entries in NAV_GROUPS:
        count = len(entries)
        group_links = links[offset:offset + count]
        offset += count
        # The first group's label is the empty-string sentinel "no
        # heading" (see NAV_GROUPS), never a Message — i18n.t() only
        # accepts a Message, so an empty label skips translation
        # entirely rather than being passed through it.
        label_text = i18n.t(group_label) if group_label else group_label
        groups.append((escape_html(label_text), group_links))
    return groups


# There are exactly two live nav renderers, sidebar_nav() and
# _mobile_nav_html() below, both fed by _nav_links() above. A
# horizontally-scrollable nav strip used to render here; real-device
# testing found it hid most tabs behind an undiscoverable swipe, so it
# was replaced rather than repaired.


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


def sidebar_nav(active, health_alert=None, device_config=None):
    """The vertical Primary-navigation landmark shown by page_shell()'s
    dashboard sidebar column at desktop width. Renders NAV_TABS via the
    shared _nav_links() helper; the 960px CSS media query, not this
    function, decides whether sidebar_nav() or _mobile_nav_html() is
    visible.

    `health_alert` is `None`/`"ok"` for no dot, or `"warn"`/`"error"` to
    append _health_alert_markup() after the Health link's label only,
    interpolated verbatim as already-built safe HTML. The active link's
    `<a>` carries `aria-current="page"` — never the inactive links.

    `device_config` remains accepted because page_shell() provides one shared
    rendering context to both navigation variants; the compact navigation no
    longer repeats its screen or quiet-hours state.
    """
    parts = []
    for group_label, group_links in _nav_groups(active):
        links = []
        for is_active, route, label, slug in group_links:
            if is_active:
                css_class = "sidebar-link sidebar-link--active"
                aria_current = ' aria-current="page"'
            else:
                css_class = "sidebar-link"
                aria_current = ""
            icon = icon_html(
                NAV_ICON_IDS.get(slug, ""), extra_class="sidebar-link__icon")
            alert_html = (
                _health_alert_markup(health_alert)
                if health_alert in ("warn", "error") and slug == HEALTH_NAV_SLUG else "")
            links.append(
                '<a class="%s" href="%s"%s>%s%s%s</a>'
                % (css_class, route, aria_current, icon, label, alert_html))
        # An unlabelled group renders its links bare; a labelled group
        # ("Advanced") wraps them in a .nav-group carrying a small uppercase
        # label so the split reads at a glance.
        if group_label:
            parts.append(
                '<div class="nav-group nav-group--advanced">'
                '<span class="nav-group__label text-label">%s</span>%s</div>'
                % (group_label, "".join(links)))
        else:
            parts.append("".join(links))
    return (
        '<nav class="sidebar-nav" aria-label="%s">%s</nav>'
    ) % (
        # "Primary navigation" is the one nav landmark exposed to the
        # accessibility tree at any given viewport width (see this module's own
        # comment above _mobile_nav_html()).
        escape_html(i18n.t(_PRIMARY_NAVIGATION_TEXT)),
        "".join(parts))


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

# HEALTH: excludes the sparkline, the registry card/filter bar and every
# <details> — swapping any would leave battery-trend.js's chart or
# list-filter.js's filter permanently dead (each captures its DOM once).

# `a[href="/health"]`, not a ".dot" selector, is the nav-severity target:
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
        ".dashboard-grid",
        "div." + HEALTH_ANOMALY_CLASS,
        "section." + HEALTH_SOURCE_FAULT_CLASS,
        ".page-header__freshness",
        'a[href="/health"]',
    ),
    REFRESH_PAGE_FLIGHTS: (
        ".page-header__freshness",
        "ul.history-cards",
        ".data-table-wrap",
        "[data-filter-count]",
    ),
}


def _tab_bar_html(active, health_alert=None, device_config=None):
    """Bottom tab bar shown below 960px, replacing the hamburger dropdown as the
    sub-960px nav.

    Renders NAV_GROUPS via _nav_groups()/_nav_links(), the same iteration
    sidebar_nav() and _mobile_nav_html() use, so all three renderings share one
    route list. The "More" overflow uses a native <details>/<summary> so it works
    with scripts blocked. health_alert is drawn on the More summary, not on the
    Health link inside it, since the sheet is collapsed by default.
    Returns "" when device_config is falsy (no session context, e.g.
    login/404 pages).
    """
    if not device_config:
        return ""
    cells = []
    sheet_links = []
    sheet_holds_active = False
    for group_label, group_links in _nav_groups(active):
        for is_active, route, label, slug in group_links:
            aria_current = ' aria-current="page"' if is_active else ""
            if group_label:
                sheet_holds_active = sheet_holds_active or is_active
                css_class = (
                    "mobile-nav__link mobile-nav__link--active"
                    if is_active else "mobile-nav__link")
                # Reuses .mobile-nav__link rather than a new class, so the sheet's rows share
                # its 44px/16px tap-target geometry instead of duplicating the numbers.
                sheet_links.append(
                    '<a class="%s" href="%s"%s>%s</a>'
                    % (css_class, route, aria_current, label))
                continue
            css_class = (
                "tab-bar__link tab-bar__link--active"
                if is_active else "tab-bar__link")
            cells.append(
                '<a class="%s" href="%s"%s>%s</a>'
                % (css_class, route, aria_current,
                   _tab_bar_cell_body(NAV_ICON_IDS.get(slug, ""), label)))
    summary_class = (
        "tab-bar__link tab-bar__link--active"
        if sheet_holds_active else "tab-bar__link")
    alert_html = (
        _health_alert_markup(health_alert)
        if health_alert in ("warn", "error") else "")
    cells.append(
        '<details class="tab-bar__more">'
        '<summary class="%s">%s</summary>'
        '<div class="tab-bar__more-panel">%s</div>'
        "</details>"
        % (summary_class,
           _tab_bar_cell_body(
               TAB_BAR_MORE_ICON_ID,
               escape_html(i18n.t(TAB_BAR_MORE_LABEL)),
               extra_html=alert_html),
           "".join(sheet_links)))
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
