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
    console_components, console_lifecycle, console_locations, console_pairing, console_users,
    i18n)
from companion.ui_base import (
    AIRLINE_EDITOR_LABEL, AIRLINE_EDITOR_ROUTE, DEVICE_ROUTE, HEALTH_ROUTE)

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
USER_DELETE_SUFFIX = "/delete"
USER_DELETE_SUFFIX = "/delete"

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
    + console_components.ROUTES
)

ADMINISTRATION_LABEL = i18n.msg("nav.administration", "Administration")
FLEET_LABEL = i18n.msg("nav.fleet", "Fleet")
USERS_LABEL = i18n.msg("nav.users", "Users")
# The Locations page is gone; the label still titles the page a refused
# location submission re-renders.
LOCATIONS_LABEL = i18n.msg("nav.locations", "Locations")
HEALTH_LABEL = i18n.msg("nav.health", "Health")
DEVICE_LABEL = i18n.msg("nav.device", "Device")
AUDIT_LABEL = i18n.msg("nav.audit_log", "Audit log")
RELEASES_LABEL = i18n.msg("nav.releases", "Releases")
SECTION_NAV_LABEL = i18n.msg("nav.administration_sections", "Administration sections")

# (key, path, label) in display order. A link is rendered only when a GET
# route for its path exists. Health, Device and the Airline editor are
# per-frame pages: the renderer scopes their paths to the frame in view.
CONSOLE_NAV_ENTRIES = (
    ("fleet", FLEET_ROUTE, FLEET_LABEL),
    ("users", USERS_ROUTE, USERS_LABEL),
    ("health", HEALTH_ROUTE, HEALTH_LABEL),
    ("device", DEVICE_ROUTE, DEVICE_LABEL),
    ("editor", AIRLINE_EDITOR_ROUTE, AIRLINE_EDITOR_LABEL),
    ("audit", AUDIT_ROUTE, AUDIT_LABEL),
    ("releases", UPDATE_ROUTE, RELEASES_LABEL),
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
    return routes.match("GET", path, "") is not None


def available_nav_entries():
    """The (key, path, label) entries whose GET page exists right now."""
    return [entry for entry in CONSOLE_NAV_ENTRIES if _get_route_exists(entry[1])]


def is_console_path(path):
    """True for one of the four console page paths (not Releases)."""
    return path in CONSOLE_TITLES
