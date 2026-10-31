"""The admin console's route paths, route aggregator and navigation entries.

Each console page and action lives in its own module (`console_pairing`,
`console_lifecycle`, `console_users`, `console_locations`) exporting a
`ROUTES` tuple; `ROUTES` here is their concatenation and `companion/routes.py`
appends it to the one route table. The route modules must build their
`Route` entries from `companion.route_types`, never from `companion.routes`
(which imports this module). Every entry carries its own `Access`; a route
without a row in the access matrix fails the default-deny completeness test.

Navigation links are derived from the live route table, so a link exists
only while its GET page does.
"""
from companion import (
    console_lifecycle, console_locations, console_pairing, console_users, i18n)
from companion.ui_base import escape_html

FLEET_ROUTE = "/fleet"
FLEET_REGISTER_ROUTE = "/fleet/register"
FLEET_PAIR_ROUTE = "/fleet/pair"
FRAME_ACTION_PREFIX = "/fleet/frames/"
FRAME_RETIRE_SUFFIX = "/retire"
FRAME_REACTIVATE_SUFFIX = "/reactivate"
FRAME_REASSIGN_SUFFIX = "/reassign"

USERS_ROUTE = "/users"
USERS_INVITE_ROUTE = "/users/invite"
USER_ACTION_PREFIX = "/users/"
USER_ROLE_SUFFIX = "/role"
USER_DISABLE_SUFFIX = "/disable"
USER_ENABLE_SUFFIX = "/enable"
USER_UNLINK_SUFFIX = "/unlink"

AUDIT_ROUTE = "/audit"

LOCATIONS_ROUTE = "/locations"
LOCATIONS_ADD_ROUTE = "/locations/add"
LOCATION_ACTION_PREFIX = "/locations/"
LOCATION_EDIT_SUFFIX = "/edit"
LOCATION_DELETE_SUFFIX = "/delete"

UPDATE_ROUTE = "/update"

ROUTES = (
    console_pairing.ROUTES
    + console_lifecycle.ROUTES
    + console_users.ROUTES
    + console_locations.ROUTES
)

ADMINISTRATION_LABEL = i18n.msg("nav.administration", "Administration")
FLEET_LABEL = i18n.msg("nav.fleet", "Fleet")
USERS_LABEL = i18n.msg("nav.users", "Users")
LOCATIONS_LABEL = i18n.msg("nav.locations", "Locations")
AUDIT_LABEL = i18n.msg("nav.audit_log", "Audit log")
RELEASES_LABEL = i18n.msg("nav.releases", "Releases")
SECTION_NAV_LABEL = i18n.msg("nav.administration_sections", "Administration sections")

# (key, path, label) in display order. A link is rendered only when a GET
# route for its path exists.
CONSOLE_NAV_ENTRIES = (
    ("fleet", FLEET_ROUTE, FLEET_LABEL),
    ("users", USERS_ROUTE, USERS_LABEL),
    ("locations", LOCATIONS_ROUTE, LOCATIONS_LABEL),
    ("audit", AUDIT_ROUTE, AUDIT_LABEL),
    ("releases", UPDATE_ROUTE, RELEASES_LABEL),
)

# Page title per console page path.
CONSOLE_TITLES = {
    FLEET_ROUTE: FLEET_LABEL,
    USERS_ROUTE: USERS_LABEL,
    LOCATIONS_ROUTE: LOCATIONS_LABEL,
    AUDIT_ROUTE: AUDIT_LABEL,
}

# The Fleet entry is also the destination of the phone tab bar's Admin tab.
ADMIN_TAB_ROUTE = FLEET_ROUTE


def _get_route_exists(path):
    # Imported here: companion.routes imports this module.
    from companion import routes
    return routes.match("GET", path, "") is not None


def available_nav_entries():
    """The (key, path, label) entries whose GET page exists right now."""
    return [entry for entry in CONSOLE_NAV_ENTRIES if _get_route_exists(entry[1])]


def is_console_path(path):
    """True for one of the four console page paths (not Releases)."""
    return path in CONSOLE_TITLES


def section_subnav_html(active_path):
    """The section sub-nav: one chip link per available console page, the
    page for `active_path` marked current. "" when no page exists. Shown
    below 960px only (the sidebar carries the same links above that).
    """
    entries = available_nav_entries()
    if not entries:
        return ""
    chips = []
    for _key, path, label in entries:
        is_current = path == active_path
        chips.append(
            '<a class="filter-chip%s" href="%s"%s>'
            '<span class="filter-chip__box"><span class="filter-chip__text">%s</span></span>'
            "</a>" % (
                " filter-chip--current" if is_current else "", escape_html(path),
                ' aria-current="page"' if is_current else "",
                escape_html(i18n.t(label))))
    return (
        '<nav class="filter-bar__chips section-subnav" aria-label="%s">%s</nav>'
        % (escape_html(i18n.t(SECTION_NAV_LABEL)), "".join(chips)))
