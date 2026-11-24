"""The files every other destination of the navigation needs, listed so the
opening splash can fetch them while it plays.

Each page names its own stylesheets (companion/page_styles.py) and scripts
(`PAGE_SCRIPTS` here, the table `page_shell()` is called with); the list for
a page is built from those same tables, never from a second copy. It holds
only the destinations the viewer's own navigation links to, so an account
that cannot reach a page is never told its files. Every address carries the
`?v=` token the page itself uses, which makes the later request an
immutable cache hit.
"""
import re

from companion import layout, page_styles, static_files
from companion.pages import airlines_page, detection_page, place_page
from companion.settings import layout_picker

# Each tab's own extra scripts, on top of layout.GLOBAL_PAGE_SCRIPTS
# (present on every authenticated page regardless). One tuple per
# layout.NAV_TABS route - companion/test_page_scripts.py's hook-coverage
# test fails, naming the route, if a tab is ever added here without one.
# Each tuple is the SUPERSET over every state the page can be in,
# including a region freshness.js may swap in later with no fresh page
# load of its own (for example Flights' rows, or Display's calendar-
# disconnect confirm dialog once the calendar is connected) - never only
# what a freshly-seeded, empty state happens to render.
PAGE_SCRIPTS = {
    layout.HOME_ROUTE: (
        layout.DIRTY_STATE_SCRIPT_SRC,
        layout.FRESHNESS_SCRIPT_SRC,
        layout.QUICK_SWITCH_SCRIPT_SRC,
    ),
    layout.DISPLAY_ROUTE: (
        layout.CALENDAR_CONNECT_SCRIPT_SRC,
        layout.CONFIRM_SUBMIT_SCRIPT_SRC,
        layout.DIRTY_STATE_SCRIPT_SRC,
        layout.FRESHNESS_SCRIPT_SRC,
        layout.QUICK_SWITCH_SCRIPT_SRC,
        layout.THEME_PREVIEW_SCRIPT_SRC,
        layout.VALUE_CONTROLS_SCRIPT_SRC,
    ),
    layout.DEVICE_ROUTE: (
        layout.DIRTY_STATE_SCRIPT_SRC,
        layout.QUICK_SWITCH_SCRIPT_SRC,
        layout.VALUE_CONTROLS_SCRIPT_SRC,
    ),
    detection_page.DETECTION_ROUTE: place_page.PAGE_SCRIPTS,
    layout.FLIGHTS_ROUTE: (
        layout.FRESHNESS_SCRIPT_SRC,
        layout.LIST_FILTER_SCRIPT_SRC,
        layout.PANEL_LOOKUP_SCRIPT_SRC,
    ),
    layout.AIRLINES_ROUTE: (
        layout.LIST_FILTER_SCRIPT_SRC,
    ),
    airlines_page.MANAGE_ROUTE: (
        layout.LIST_FILTER_SCRIPT_SRC,
        layout.AIRLINE_TYPES_SCRIPT_SRC,
        layout.AIRLINE_SUGGEST_SCRIPT_SRC,
        layout.PANEL_LOOKUP_SCRIPT_SRC,
    ),
    # UPDATE_QUESTION_SCRIPT_SRC turns the per-release Install form's
    # data-confirm-* attributes into a question dialog; without it the form
    # lands on _handle_update_install_post()'s server-side confirm page.
    layout.UPDATE_ROUTE: (
        layout.UPDATE_QUESTION_SCRIPT_SRC,
    ),
}

CORE_STYLE = "/static/style.css"
_HREF = re.compile(r'<a\b[^>]*?\shref="([^"]+)"')
# A route that is not a destination: sign-out and the quick switches.
_NOT_A_PAGE = re.compile(r"^/(logout|login|quick)(/|$)")


def _console_scripts(route):
    """The scripts a Console page loads, which its handler (not the tab
    table) names. The Fleet page lists the union of its two views."""
    from companion import console_fleet_view, console_users, console_routes
    if route == console_routes.FLEET_ROUTE:
        return (console_fleet_view.page_scripts(False)
                + console_fleet_view.page_scripts(True))
    if route == console_routes.USERS_ROUTE:
        return console_users.PAGE_SCRIPTS
    return ()


def page_assets(route):
    """The static routes the page at `route` links beyond the core stylesheet
    and the scripts every page has, in link order, or () for an address that is
    not a page with its own sheets. Includes the map page's starter-loaded
    scripts (the map library and its glue)."""
    if not route or not page_styles.is_known_route(route):
        return ()
    base = page_styles.route_of(route)
    styles = page_styles.area_hrefs(base)
    scripts = PAGE_SCRIPTS.get(base) or _console_scripts(base)
    if base == detection_page.DETECTION_ROUTE:
        styles += place_page.PAGE_STYLES
        scripts += tuple(src for _name, src in place_page.STARTED_SCRIPTS)
    return styles + tuple(src for src in scripts if src not in layout.GLOBAL_PAGE_SCRIPTS)


def nav_routes(*nav_html):
    """The routes the navigation `nav_html` links to, first appearance first
    (no frame prefix, no query, no sign-out or quick switch)."""
    routes = []
    for html in nav_html:
        for href in _HREF.findall(html or ""):
            path = href.replace("&amp;", "&").partition("#")[0].partition("?")[0]
            route = page_styles.route_of(path)
            if path.startswith("/") and not _NOT_A_PAGE.match(route) and route not in routes:
                routes.append(route)
    return routes


def _versioned(route):
    version = static_files.asset_version(route)
    return "%s?v=%s" % (route, version) if version else None


def preload_urls(nav_html, current_route, device_cfg):
    """The addresses to fetch while the splash plays, for a page at
    `current_route` whose navigation is `nav_html` (a sequence of markup
    strings): the versioned stylesheets and scripts of every linked page the
    current one does not already load, then the pictures the Style page shows
    at once, then the map library (the heaviest, last)."""
    have = set(page_assets(current_route)) | {CORE_STYLE}
    routes = nav_routes(*nav_html)
    from companion import console_routes
    if console_routes.FLEET_ROUTE in routes:
        # The Console is one tap away and its own navigation lists the rest of it.
        routes += [
            route for route in nav_routes(*('<a href="%s">' % path for _key, path, _label
                                           in console_routes.available_nav_entries()))
            if route not in routes]
    ordered = []
    for route in routes:
        for asset in page_assets(route):
            if asset not in have and asset not in ordered:
                ordered.append(asset)
    heavy = [a for a in ordered if a.startswith("/static/vendor/")]
    plain = [a for a in ordered if a not in heavy]
    urls = [_versioned(asset) for asset in plain]
    if layout.DISPLAY_ROUTE in routes and page_styles.route_of(current_route) != layout.DISPLAY_ROUTE:
        urls += layout_picker.first_view_preview_srcs(device_cfg) if device_cfg else []
    urls += [_versioned(asset) for asset in heavy]
    return [url for url in urls if url]
