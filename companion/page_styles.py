"""Which area stylesheets a page links after the core one.

`static/style.css` holds what every page needs; the rules only one family of
pages uses live in `static/style-<area>.css`, so a page downloads and
matches its own area and not the others. A path not named here (an error
page, an unknown route, the components gallery) links every area sheet, so a
page never lacks a rule. A document with no request path (rendered outside a
request) and the error pages (no active tab) link the core sheet alone.
"""
import re

from companion.static_files import AREA_STYLE_NAMES, COMPONENT_STYLE_NAMES

_AREA_HREF = "/static/style-%s.css"
_DEVICE_PREFIX = re.compile(r"^/devices/[^/]+")

_EXACT = {
    "/": ("home",),
    "/flights": ("flights",),
    "/airlines": ("airlines",),
    "/airlines/manage": ("airlines",),
    "/detection": ("place",),
    "/settings": ("display",),
    "/fleet": ("display", "admin"),
    "/account": ("admin",),
    "/users": ("admin",),
    "/audit": ("admin",),
    "/update": ("admin",),
    "/pair-frame": ("admin",),
    "/credits": ("admin",),
}


# The page families each component sheet holds rules for; a page links the
# sheet when its family is listed, before its own area sheet.
_COMPONENT_FAMILIES = {
    "c-console": ("admin", "display", "place"),
    "c-lists": ("admin", "airlines", "display", "flights"),
}


def _with_components(areas):
    """`areas` preceded by the component sheets any of them uses."""
    return tuple(
        name for name in COMPONENT_STYLE_NAMES
        if any(area in _COMPONENT_FAMILIES[name] for area in areas)) + areas


def route_of(path):
    """`path` without its frame prefix (`/devices/<id>`): the route a page is registered under."""
    return _DEVICE_PREFIX.sub("", path) or "/"


def is_known_route(path):
    """True when `path` is a page with its own, named stylesheets (not the fallback that links every area sheet)."""
    route = route_of(path)
    return route in _EXACT or route == "/display" or route.startswith("/display/")


def areas_for(path):
    """The stylesheet names `path`'s page links after the core one, in link order."""
    if not path:
        return ()
    route = route_of(path)
    if route == "/display" or route.startswith("/display/"):
        return _with_components(("display",))
    areas = _EXACT.get(route)
    return _with_components(areas) if areas else AREA_STYLE_NAMES


def area_hrefs(path):
    """The stylesheet addresses for `path`, as a tuple."""
    return tuple(_AREA_HREF % name for name in areas_for(path))
