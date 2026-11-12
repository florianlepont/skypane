"""The sign-in `next` destination: which same-site addresses a sign-in may
send the browser back to.

An open redirect is the risk, so the check is positive and strict: the path
must be byte-identical to one of the navigation tabs' routes or to a page
route of the route table (an Account, Users or Fleet page, or one of a
frame's pages under its `/devices/<id>` prefix), and the query
(if any) may hold only unreserved characters, the separators of a plain query
string and percent-escapes. A scheme, a host, a second slash, a backslash, a
fragment, a control character or anything else makes the whole value
unusable (`None`), and the caller falls back to the plain sign-in.
"""

import re
from urllib.parse import quote, urlsplit

LOGIN_ROUTE = "/login"
LOGOUT_ROUTE = "/logout"
MAX_NEXT_LENGTH = 200
# Page routes that only redirect elsewhere (and the retired Update page): a
# sign-in has nothing to gain from carrying them.
_RETIRED_PATHS = frozenset(("/settings", "/history", "/preview", "/update"))
_DEVICE_PREFIX = re.compile(r"\A/devices/d_[0-9a-f]{8}(?=/|\Z)")
_page_paths_cache = []
_QUERY_PATTERN = re.compile(r"(?:[A-Za-z0-9_.~=&,:+-]|%[0-9A-Fa-f]{2})*")


def _page_paths():
    """(un-prefixed page paths, device-scoped page paths): the exact GET routes
    of the route table a signed-in person reaches, less the retired ones."""
    if not _page_paths_cache:
        from companion import route_types, routes
        plain, scoped = set(), set()
        for route in routes.ROUTES:
            if (route.method != "GET" or route.access.min_role == route_types.ANONYMOUS
                    or not isinstance(route.matcher, route_types.Exact)
                    or route.matcher.path in _RETIRED_PATHS):
                continue
            plain.add(route.matcher.path)
            if route.device_scoped:
                scoped.add(route.matcher.path)
        _page_paths_cache.append((frozenset(plain), frozenset(scoped)))
    return _page_paths_cache[0]


def _is_page_path(path):
    plain, scoped = _page_paths()
    if path in plain:
        return True
    prefix = _DEVICE_PREFIX.match(path)
    return prefix is not None and (path[prefix.end():] or "/") in scoped


def validated_next_route(candidate, allowed_paths):
    """`candidate` when it is an allowed path, optionally followed by a safe
    query string, else None. `allowed_paths` is the set of exact routes
    always allowed; any other page route of the table is allowed too."""
    if not isinstance(candidate, str) or len(candidate) > MAX_NEXT_LENGTH:
        return None
    path, separator, query = candidate.partition("?")
    if path not in allowed_paths and not _is_page_path(path):
        return None
    if separator and not _QUERY_PATTERN.fullmatch(query):
        return None
    return candidate


def _own_page(referer, host):
    """The path and query of `referer` when it names a page of this very
    host and passes the same check as any `next`, else None. Only the host
    the request itself was sent to counts, and a fragment or anything that
    does not parse as an http(s) address is refused."""
    if not referer or not host or "#" in referer:
        return None
    try:
        parts = urlsplit(referer)
    except ValueError:
        return None
    if parts.scheme not in ("http", "https") or parts.netloc != host:
        return None
    return validated_next_route(
        parts.path + ("?" + parts.query if parts.query else ""), ())


def login_redirect_for(handler):
    """The sign-in address for the request `handler` is refusing. A page
    visit carries its own address. A posted form carries the page it was
    sent from (its same-host Referer, checked like any `next`) and is always
    marked `expired=1`: the person was signed in when the form was drawn, so
    sign-in says that unsaved changes were not kept and returns to the page."""
    session_ended = bool(handler._raw_session_token())
    if handler.command != "POST":
        return login_redirect(handler.path, session_ended)
    if handler.path.partition("?")[0] == LOGOUT_ROUTE:
        # Signing out when already signed out: nothing was lost.
        return LOGIN_ROUTE
    page = _own_page(handler.headers.get("Referer"), handler.headers.get("Host"))
    return login_redirect(page or handler.path, True)


def login_redirect(request_path, session_ended):
    """The sign-in address a signed-out visit of `request_path` goes to: it
    carries the page as `next` when that is an allowed destination, and
    `expired=1` when the visit came with a session that has ended."""
    target = (validated_next_route(request_path, ())
              or validated_next_route(request_path.partition("?")[0], ()))
    params = []
    if target:
        # safe="" so the value is one query token ("%2Faccount", not "/account").
        params.append("next=" + quote(target, safe=""))
    if session_ended:
        params.append("expired=1")
    return LOGIN_ROUTE + ("?" + "&".join(params) if params else "")
