"""The route-table vocabulary: matcher shapes, `Access` policies and the
`Route` entry. Kept apart from `companion/routes.py` so the console route
modules can declare routes without importing the table that aggregates
them. `companion/routes.py` re-exports every name here.
"""
import collections

from companion import access as _access

Exact = collections.namedtuple("Exact", "path")
PrefixSuffix = collections.namedtuple("PrefixSuffix", "prefix suffix")
# `device_id` is None for an un-prefixed match; `device` is filled in later
# by the dispatcher once the id has been looked up.
RouteMatch = collections.namedtuple(
    "RouteMatch", "path query captured device_id device", defaults=(None, None))

ANONYMOUS = _access.ANONYMOUS
USER = _access.USER
ADMIN = _access.ADMIN

# min_role: the lowest role that may reach the route. device_arg: None for a
# global route, otherwise the name of what the matcher captures (a device id)
# so the ownership gate applies.
Access = collections.namedtuple("Access", "min_role device_arg")

PUBLIC = Access(ANONYMOUS, None)
SIGNED_IN = Access(USER, None)
ADMIN_ONLY = Access(ADMIN, None)
# A user reaches a device route for a frame they own or co-manage (the
# ownership gate reads the device id from the URL prefix); an admin reaches
# every frame. The un-prefixed form of such a route acts on the live frame and
# stays admin-only.
OWNER_DEVICE = Access(USER, _access.DEVICE_ARG)
# Only the owner or an admin passes; a co-manager is refused like a stranger.
OWNER_ONLY_DEVICE = Access(USER, _access.DEVICE_OWNER_ARG)


class Route(collections.namedtuple(
        "Route", "method matcher handler access device_scoped csrf")):
    """One table entry. Refuses to exist without a valid Access, so a route
    cannot register without a policy (a bool or nothing raises at import).

    `device_scoped` routes also resolve under a `/devices/<id>` prefix and
    there are decided on `access` with the prefix id; un-prefixed they are
    admin-only. A POST route with `csrf` set also needs the per-session
    token in its form body (checked by the dispatcher after the access
    decision).
    """

    __slots__ = ()

    def __new__(cls, method, matcher, handler, access, device_scoped=False, csrf=False):
        if (
            not isinstance(access, Access)
            or access.min_role not in (ANONYMOUS, USER, ADMIN)
        ):
            raise TypeError("every route needs an explicit Access annotation")
        return super().__new__(cls, method, matcher, handler, access, device_scoped, csrf)
