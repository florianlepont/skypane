"""The admin-only Components reference page: GET /components.

Reachable by an administrator only (anyone else gets the unknown-path 404 from
the route table's default-deny gate), absent from the navigation, linked from
the Fleet page's System view.
"""
from companion import route_types

# The same literal as companion/pages/components_page.py's COMPONENTS_ROUTE (the
# page module loads after the navigation, so it is imported on use).
COMPONENTS_PATH = "/components"


def handle_components_get(h, m):
    from companion.pages import components_page
    return h._console_page(
        COMPONENTS_PATH, components_page.TITLE, components_page.render,
        purpose_msg=components_page.PURPOSE)


ROUTES = (
    route_types.Route(
        "GET", route_types.Exact(COMPONENTS_PATH), handle_components_get,
        route_types.ADMIN_ONLY),
)
