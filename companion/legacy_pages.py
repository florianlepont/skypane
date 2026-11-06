"""Old page addresses that still arrive from bookmarks, and the page each one
moved to. Every target is a literal route path; a signed-in person is sent to it
under their own default frame, never to an administrator page. An administrator
reaching an old address is already moved to the same page of the served frame by
the route itself."""
from urllib.parse import parse_qs

from companion import layout
from companion.pages import personalisation_cards

# Un-prefixed live pages of a frame: a user or an administrator is moved to the
# same page under their default frame.
LIVE_FRAME_PAGES = frozenset((
    layout.HOME_ROUTE, "/display", "/flights", "/airlines", "/detection"))

# Old address -> the page that replaced it; moved for a non-administrator.
LEGACY_TARGETS = {
    "/settings": layout.DISPLAY_ROUTE,
    "/history": layout.FLIGHTS_ROUTE,
    "/preview": layout.FLIGHTS_ROUTE,
}
LEGACY_TARGETS.update(
    {retired: layout.DISPLAY_ROUTE for retired in personalisation_cards.RETIRED_VIEW_ROUTES})


def frame_page_target(path, is_admin):
    """The page `path` is served as under a frame for this kind of caller, or
    None when the path is not moved."""
    if path in LIVE_FRAME_PAGES:
        return path
    return None if is_admin else LEGACY_TARGETS.get(path)


# The administrator pages that now live on the Fleet page, and the page a
# person who is not an administrator is moved to instead.
RETIRED_ADMIN_PAGES = {
    layout.HEALTH_ROUTE: layout.HOME_ROUTE,
    layout.DEVICE_ROUTE: layout.DISPLAY_ROUTE,
    layout.UPDATE_ROUTE: layout.HOME_ROUTE,
}


def retired_page_target(path, query, prefix_id, own_ids, default_id):
    """Where a person who is not an administrator is moved from a retired
    administrator page: the replacement page of the frame named by the address
    prefix or `?frame=` when it is one of `own_ids`, else of `default_id`, else
    the account page. None when `path` is not a retired page."""
    page = RETIRED_ADMIN_PAGES.get(path)
    if page is None:
        return None
    if prefix_id is not None and prefix_id not in own_ids:
        return None
    wanted = prefix_id or parse_qs(query or "").get("frame", [""])[0]
    frame = wanted if wanted in own_ids else default_id
    return "/devices/%s%s" % (frame, page) if frame else "/account"
