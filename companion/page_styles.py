"""Which area stylesheets a page links after the core one.

`static/style.css` holds what every page needs; the rules only one family of
pages uses live in `static/style-<area>.css`, so a page downloads and
matches its own area and not the others. A path not named here (an error
page, an unknown route, the components gallery) links every area sheet, so a
page never lacks a rule. A document with no request path (rendered outside a
request) and the error pages (no active tab) link the core sheet alone.
"""
import re

from companion.static_files import AREA_STYLE_NAMES

_AREA_HREF = "/static/style-%s.css"
_DEVICE_PREFIX = re.compile(r"^/devices/[^/]+")

_EXACT = {
    "/": ("home",),
    "/flights": ("flights",),
    "/history": ("flights",),
    "/airlines": ("airlines",),
    "/airlines/manage": ("airlines",),
    "/detection": ("place",),
    "/settings": ("display",),
    "/fleet": ("display", "admin"),
    "/account": ("admin",),
    "/users": ("admin",),
    "/audit": ("admin",),
    "/locations": ("admin",),
    "/update": ("admin",),
    "/pair-frame": ("admin",),
    "/frame/name": ("admin",),
    "/credits": ("admin",),
}


def areas_for(path):
    """The area names `path`'s page links, in link order."""
    if not path:
        return ()
    route = _DEVICE_PREFIX.sub("", path) or "/"
    if route == "/display" or route.startswith("/display/"):
        return ("display",)
    return _EXACT.get(route, AREA_STYLE_NAMES)


def area_hrefs(path):
    """The area stylesheet addresses for `path`, as a tuple."""
    return tuple(_AREA_HREF % name for name in areas_for(path))
