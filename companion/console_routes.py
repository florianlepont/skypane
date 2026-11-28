# SPDX-License-Identifier: AGPL-3.0-only
"""The admin console's route paths, route aggregator and navigation entries.

Each console page and action lives in its own module (`console_pairing`,
`console_lifecycle`, `console_users`) exporting a
`ROUTES` tuple; `ROUTES` here is their concatenation and `companion/routes.py`
appends it to the one route table. The route modules must build their
`Route` entries from `companion.route_types`, never from `companion.routes`
(which imports this module). Every entry carries its own `Access`; a route
without a row in the access matrix fails the default-deny completeness test.

Navigation links are derived from the live route table, so a link exists
only while its GET page does.
"""
from companion import (
    console_components, console_lifecycle, console_pairing, console_users, i18n)
from companion.ui_base import (
    AIRLINE_EDITOR_LABEL, AIRLINE_EDITOR_ROUTE)

FLEET_ROUTE = "/fleet"
FLEET_REGISTER_ROUTE = "/fleet/register"
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
USER_DELETE_SUFFIX = "/delete"
USER_DELETE_SUFFIX = "/delete"

AUDIT_ROUTE = "/audit"

UPDATE_ROUTE = "/update"

ROUTES = (
    console_pairing.ROUTES
    + console_lifecycle.ROUTES
    + console_users.ROUTES
    + console_components.ROUTES
)

ADMINISTRATION_LABEL = i18n.msg("nav.administration", "Admin")
FLEET_LABEL = i18n.msg("nav.fleet", "Fleet")
USERS_LABEL = i18n.msg("nav.users", "Users")
AUDIT_LABEL = i18n.msg("nav.audit_log", "Activity")
SYSTEM_LABEL = i18n.msg("nav.system", "System")
RELEASES_LABEL = i18n.msg("nav.releases", "Releases")
SECTION_NAV_LABEL = i18n.msg("nav.administration_sections", "Administration sections")

# The System view is a view of the Fleet page, named by a query: its entry
# path carries it, and its route (the part before the query) is the Fleet one.
SYSTEM_VIEW_QUERY = "view"
SYSTEM_VIEW_VALUE = "system"
SYSTEM_ROUTE = "%s?%s=%s" % (FLEET_ROUTE, SYSTEM_VIEW_QUERY, SYSTEM_VIEW_VALUE)

# (key, path, label) in display order. A link is rendered only when a GET
# route for its path exists.
CONSOLE_NAV_ENTRIES = (
    ("fleet", FLEET_ROUTE, FLEET_LABEL),
    ("users", USERS_ROUTE, USERS_LABEL),
    ("editor", AIRLINE_EDITOR_ROUTE, AIRLINE_EDITOR_LABEL),
    ("audit", AUDIT_ROUTE, AUDIT_LABEL),
    ("releases", UPDATE_ROUTE, RELEASES_LABEL),
    ("system", SYSTEM_ROUTE, SYSTEM_LABEL),
)

# Page title per console page path.
CONSOLE_TITLES = {
    FLEET_ROUTE: FLEET_LABEL,
    USERS_ROUTE: USERS_LABEL,
    AUDIT_ROUTE: AUDIT_LABEL,
}

# The Fleet entry is also the destination of the phone tab bar's Admin tab.
ADMIN_TAB_ROUTE = FLEET_ROUTE


def _get_route_exists(path):
    # Imported here: companion.routes imports this module.
    from companion import routes
    return routes.match("GET", path.partition("?")[0], "") is not None


def available_nav_entries():
    """The (key, path, label) entries whose GET page exists right now."""
    return [entry for entry in CONSOLE_NAV_ENTRIES if _get_route_exists(entry[1])]


def is_console_path(path):
    """True for one of the four console page paths (not Releases)."""
    return path in CONSOLE_TITLES
