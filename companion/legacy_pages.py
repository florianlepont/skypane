"""Old page addresses that still arrive from bookmarks, and the page each one
moved to. Every target is a literal route path; a signed-in person is sent to it
under their own default frame, never to an administrator page. An administrator
reaching an old address is already moved to the same page of the served frame by
the route itself."""
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
