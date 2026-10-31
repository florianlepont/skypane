"""The one route table `companion/app.py`'s `Handler._dispatch()` walks:
every GET and POST route declared exactly once as `(method, matcher,
handler, access)`.

Never imports `companion.app` (that would be a cycle - `app.py` imports
this module). Route constants that exist only in `app.py` today are
duplicated here as literals instead, the same "duplicated-not-imported"
contract `app.py`'s own `QUICK_*_ROUTE` constants already document for
the identical reason.

Routes that act on one device carry `device_scoped=True`; only those also
resolve under a `/devices/<id>` prefix (`match()` strips the prefix and
reports the id on `RouteMatch.device_id`). Global routes (login, logout,
theme, language, static assets, runway diagrams, update) never match under
the prefix. The set is declared once in `_DEVICE_SCOPED_KEYS`. A prefixed
route carries exactly the `access` of its un-prefixed counterpart, so it is
never less protected; the dispatcher applies that decision before it looks
the device up.

Only two matcher shapes exist: `Exact` (a fixed literal path) and
`PrefixSuffix` (a fixed prefix and, for every route but the gallery one,
a fixed suffix too) - a captured middle segment is recovered by slicing
both off, byte for byte the same arithmetic the pre-table if-chains
used. `access` is a validated `Access(min_role, device_arg)`: a Route
cannot be constructed without one (default-deny). PUBLIC is the one place
this whole app grants pre-session access; the only routes with it are
GET /login, the sign-in start and callback, the bearer-token export (it checks
its own token and never reads the session cookie), and the static assets in
`companion/static_files.py`'s `STATIC_ROUTES`. SIGNED_IN needs any signed-in user; ADMIN_ONLY needs the
admin role (every global page and mutation).
"""
import collections
import re

from companion import access as _access, device_scope, layout, static_files, theme_preview
from companion.pages import (
    airlines_page, config_page, health_page, history_page, home_page, update_page)

Exact = collections.namedtuple("Exact", "path")
PrefixSuffix = collections.namedtuple("PrefixSuffix", "prefix suffix")
# `device_id` is None for an un-prefixed match; `device` is filled in later
# by the dispatcher once the id has been looked up.
RouteMatch = collections.namedtuple(
    "RouteMatch", "path query captured device_id device", defaults=(None, None))

# Anchored on the raw path (never percent-decoded); `\Z` and the absence of
# DOTALL keep a newline from slipping into the id or the remainder.
DEVICE_PREFIX_RE = re.compile(r"\A/devices/(d_[0-9a-f]{8})(/.*)?\Z")

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


class Route(collections.namedtuple(
        "Route", "method matcher handler access device_scoped")):
    """One table entry. Refuses to exist without a valid Access, so a route
    cannot register without a policy (a bool or nothing raises at import).

    `device_scoped` routes also resolve under a `/devices/<id>` prefix and
    there inherit `access` unchanged.
    """

    __slots__ = ()

    def __new__(cls, method, matcher, handler, access, device_scoped=False):
        if (
            not isinstance(access, Access)
            or access.min_role not in (ANONYMOUS, USER, ADMIN)
        ):
            raise TypeError("every route needs an explicit Access annotation")
        return super().__new__(cls, method, matcher, handler, access, device_scoped)

# Literal here, byte-identical to companion/app.py's own constants of the
# same name, since this module can never import companion.app either.
LOGIN_ROUTE = "/login"
AUTH0_LOGIN_ROUTE = "/login/auth0"
CALLBACK_ROUTE = "/callback"
HISTORY_LEGACY_ROUTE = "/history"
PREVIEW_PAGE_ROUTE = "/preview"
QUICK_DISPLAY_ROUTE = "/quick/display"
QUICK_QUIET_HOURS_ROUTE = "/quick/quiet-hours"
QUICK_LED_ROUTE = "/quick/led"
THEME_ROUTE = "/ui-theme"
LANG_ROUTE = "/ui-lang"
LOGOUT_ROUTE = "/logout"
ACCOUNT_ROUTE = "/account"
EXPORT_ROUTE = "/api/export/battery-history"
GALLERY_ROUTE_PREFIX = "/gallery/"
ILLUSTRATION_IMAGE_ROUTE_PREFIX = "/illustration/"

# The seven live tabs, rebound from layout.py's own single definition site.
HOME_ROUTE = layout.HOME_ROUTE
DISPLAY_ROUTE = layout.DISPLAY_ROUTE
FLIGHTS_ROUTE = layout.FLIGHTS_ROUTE
AIRLINES_ROUTE = layout.AIRLINES_ROUTE
HEALTH_ROUTE = layout.HEALTH_ROUTE
DEVICE_ROUTE = layout.DEVICE_ROUTE
UPDATE_ROUTE = layout.UPDATE_ROUTE

SETTINGS_ROUTE = config_page.SETTINGS_ROUTE
RUNWAY_IMAGE_ROUTE_PREFIX = config_page.RUNWAY_IMAGE_ROUTE_PREFIX
RULES_ADD_ROUTE = config_page.RULES_ADD_ROUTE
RULES_DELETE_ROUTE_PREFIX = config_page.RULES_DELETE_ROUTE_PREFIX
RULES_DELETE_ROUTE_SUFFIX = config_page.RULES_DELETE_ROUTE_SUFFIX
CALENDAR_DISCONNECT_ROUTE = config_page.CALENDAR_DISCONNECT_ROUTE
CALENDAR_CONNECT_ROUTE = config_page.CALENDAR_CONNECT_ROUTE
UPDATE_INSTALL_ROUTE = update_page.INSTALL_ROUTE
UPDATE_CANCEL_ROUTE = update_page.CANCEL_ROUTE

THEME_PREVIEW_ROUTE_PREFIX = theme_preview.THEME_PREVIEW_ROUTE_PREFIX
FRAME_PREVIEW_ROUTE_PREFIX = theme_preview.FRAME_PREVIEW_ROUTE_PREFIX


def _static_get_routes():
    """One public GET Route per companion/static_files.py STATIC_ROUTES
    entry, in that dict's own (insertion) order. `m.path` is the request
    path, which for an Exact match always equals the route key itself -
    no closure over the loop variable needed.
    """
    return tuple(
        Route("GET", Exact(route), lambda h, m: h._serve_static_route(m.path), PUBLIC)
        for route in static_files.STATIC_ROUTES
    )


# GET routes, in companion/app.py's pre-table _dispatch_get() branch
# order: the login page, the 17 static assets, the six live tabs, the
# three legacy fixed redirects, then the four prefix-matched image
# routes.
_GET_ROUTES = (
    (
        Route("GET", Exact(LOGIN_ROUTE), lambda h, m: h._handle_login_get(), PUBLIC),
        Route("GET", Exact(AUTH0_LOGIN_ROUTE), lambda h, m: h._handle_login_auth0_get(), PUBLIC),
        Route("GET", Exact(CALLBACK_ROUTE), lambda h, m: h._handle_callback_get(), PUBLIC),
        # PUBLIC only in the sense that the cookie gate does not apply: the
        # handler authenticates the bearer token itself.
        Route(
            "GET", Exact(EXPORT_ROUTE),
            lambda h, m: h._handle_export_get(m.query), PUBLIC),
    )
    + _static_get_routes()
    + (
        Route("GET", Exact(ACCOUNT_ROUTE), lambda h, m: h._handle_account_get(), SIGNED_IN),
        Route(
            "GET", Exact(HOME_ROUTE),
            lambda h, m: h._render_tab(HOME_ROUTE, home_page.render, m.device), ADMIN_ONLY),
        Route(
            "GET", Exact(DISPLAY_ROUTE),
            lambda h, m: h._render_tab(
                DISPLAY_ROUTE,
                lambda ctx: config_page.render(ctx, scope=config_page.SCOPE_DISPLAY),
                m.device),
            ADMIN_ONLY),
        Route(
            "GET", Exact(DEVICE_ROUTE),
            lambda h, m: h._render_tab(
                DEVICE_ROUTE,
                lambda ctx: config_page.render(ctx, scope=config_page.SCOPE_DEVICE),
                m.device),
            ADMIN_ONLY),
        Route(
            "GET", Exact(FLIGHTS_ROUTE),
            lambda h, m: h._render_tab(FLIGHTS_ROUTE, history_page.render, m.device), ADMIN_ONLY),
        Route(
            "GET", Exact(HEALTH_ROUTE),
            lambda h, m: h._render_tab(HEALTH_ROUTE, health_page.render, m.device), ADMIN_ONLY),
        Route(
            "GET", Exact(AIRLINES_ROUTE),
            lambda h, m: h._render_tab(AIRLINES_ROUTE, airlines_page.render, m.device), ADMIN_ONLY),
        Route(
            "GET", Exact(UPDATE_ROUTE),
            lambda h, m: h._render_tab(
                UPDATE_ROUTE,
                lambda ctx: update_page.render(ctx, h._requested_update_type()),
                m.device),
            ADMIN_ONLY),
        # The pre-refactor page routes survive as fixed 303s so a stale
        # bookmark or link still lands somewhere useful. The targets are
        # literals, never derived from any request value; under a device
        # prefix they keep that prefix.
        Route(
            "GET", Exact(SETTINGS_ROUTE),
            lambda h, m: h.redirect(device_scope.scoped(DISPLAY_ROUTE)), ADMIN_ONLY),
        Route(
            "GET", Exact(HISTORY_LEGACY_ROUTE),
            lambda h, m: h.redirect(device_scope.scoped(FLIGHTS_ROUTE)), ADMIN_ONLY),
        Route(
            "GET", Exact(PREVIEW_PAGE_ROUTE),
            lambda h, m: h.redirect(device_scope.scoped(FLIGHTS_ROUTE)), ADMIN_ONLY),
        Route(
            "GET", PrefixSuffix(GALLERY_ROUTE_PREFIX, ""),
            lambda h, m: h._serve_gallery_image(m.device, m.captured), ADMIN_ONLY),
        Route(
            "GET", PrefixSuffix(RUNWAY_IMAGE_ROUTE_PREFIX, ".png"),
            lambda h, m: h._serve_runway_image(m.captured), ADMIN_ONLY),
        Route(
            "GET", PrefixSuffix(ILLUSTRATION_IMAGE_ROUTE_PREFIX, ".png"),
            lambda h, m: h._serve_illustration_image(m.device, m.captured), ADMIN_ONLY),
        Route(
            "GET", PrefixSuffix(THEME_PREVIEW_ROUTE_PREFIX, ".png"),
            lambda h, m: h._serve_theme_preview_image(m.device, m.captured), ADMIN_ONLY),
        Route(
            "GET", PrefixSuffix(FRAME_PREVIEW_ROUTE_PREFIX, ".png"),
            lambda h, m: h._serve_frame_preview_image(m.device, m.captured), ADMIN_ONLY),
    )
)

# POST routes, in companion/app.py's pre-table _dispatch_post() branch
# order (the Origin/Sec-Fetch-Site gate runs before routes.match() is
# ever called - see Handler._dispatch() - so it is not represented here).
_POST_ROUTES = (
    Route(
        "POST", Exact(SETTINGS_ROUTE),
        lambda h, m: h._handle_settings_post(m.device), ADMIN_ONLY),
    Route(
        "POST", Exact(QUICK_DISPLAY_ROUTE),
        lambda h, m: h._handle_quick_toggle(m.device, "display_enabled"), ADMIN_ONLY),
    Route(
        "POST", Exact(QUICK_QUIET_HOURS_ROUTE),
        lambda h, m: h._handle_quick_toggle(m.device, "quiet_hours_enabled"), ADMIN_ONLY),
    # Session-checked POST only, no CSRF token - SameSite=Strict is the
    # only control here. return_to whitelist: /device is the LED
    # switch's only page, so it is both the sole allowed value and the
    # fallback.
    Route(
        "POST", Exact(QUICK_LED_ROUTE),
        lambda h, m: h._handle_quick_toggle(
            m.device, "led_enabled", allowed_return_to=(DEVICE_ROUTE,),
            fallback_return_to=DEVICE_ROUTE),
        ADMIN_ONLY),
    Route("POST", Exact(THEME_ROUTE), lambda h, m: h._handle_theme_post(), SIGNED_IN),
    Route("POST", Exact(LANG_ROUTE), lambda h, m: h._handle_lang_post(), SIGNED_IN),
    Route("POST", Exact(LOGOUT_ROUTE), lambda h, m: h._handle_logout_post(), SIGNED_IN),
    Route(
        "POST", Exact(airlines_page.RESOLVE_ROUTE),
        lambda h, m: h._handle_manual_resolve_post(m.device), ADMIN_ONLY),
    Route(
        "POST", Exact(airlines_page.RENAME_ROUTE),
        lambda h, m: h._handle_airline_rename_post(m.device), ADMIN_ONLY),
    Route(
        "POST", Exact(airlines_page.RENAME_RESET_ROUTE),
        lambda h, m: h._handle_airline_rename_reset_post(m.device), ADMIN_ONLY),
    Route(
        "POST",
        PrefixSuffix(airlines_page.MANUAL_DELETE_ROUTE_PREFIX, airlines_page.MANUAL_DELETE_ROUTE_SUFFIX),
        lambda h, m: h._handle_manual_resolution_delete(m.device, m.captured), ADMIN_ONLY),
    Route(
        "POST", PrefixSuffix(ILLUSTRATION_IMAGE_ROUTE_PREFIX, ".png"),
        lambda h, m: h._handle_illustration_replace(m.device, m.captured), ADMIN_ONLY),
    Route("POST", Exact(RULES_ADD_ROUTE), lambda h, m: h._handle_rule_add_post(m.device), ADMIN_ONLY),
    Route(
        "POST", Exact(CALENDAR_DISCONNECT_ROUTE),
        lambda h, m: h._handle_calendar_disconnect_post(m.device), ADMIN_ONLY),
    Route(
        "POST", Exact(CALENDAR_CONNECT_ROUTE),
        lambda h, m: h._handle_calendar_connect_post(m.device), ADMIN_ONLY),
    Route(
        "POST", Exact(UPDATE_INSTALL_ROUTE),
        lambda h, m: h._handle_update_install_post(), ADMIN_ONLY),
    Route(
        "POST", Exact(UPDATE_CANCEL_ROUTE),
        lambda h, m: h._handle_update_cancel_post(), ADMIN_ONLY),
    Route(
        "POST", PrefixSuffix(RULES_DELETE_ROUTE_PREFIX, RULES_DELETE_ROUTE_SUFFIX),
        lambda h, m: h._handle_rule_delete_post(m.device, m.captured), ADMIN_ONLY),
)

_PAGE_AND_IMAGE_KEYS = (
    ("GET", Exact(HOME_ROUTE)),
    ("GET", Exact(DISPLAY_ROUTE)),
    ("GET", Exact(DEVICE_ROUTE)),
    ("GET", Exact(FLIGHTS_ROUTE)),
    ("GET", Exact(HEALTH_ROUTE)),
    ("GET", Exact(AIRLINES_ROUTE)),
    ("GET", Exact(SETTINGS_ROUTE)),
    ("GET", Exact(HISTORY_LEGACY_ROUTE)),
    ("GET", Exact(PREVIEW_PAGE_ROUTE)),
    ("GET", PrefixSuffix(GALLERY_ROUTE_PREFIX, "")),
    ("GET", PrefixSuffix(ILLUSTRATION_IMAGE_ROUTE_PREFIX, ".png")),
    ("GET", PrefixSuffix(THEME_PREVIEW_ROUTE_PREFIX, ".png")),
    ("GET", PrefixSuffix(FRAME_PREVIEW_ROUTE_PREFIX, ".png")),
)

_ACTION_KEYS = (
    ("POST", Exact(SETTINGS_ROUTE)),
    ("POST", Exact(QUICK_DISPLAY_ROUTE)),
    ("POST", Exact(QUICK_QUIET_HOURS_ROUTE)),
    ("POST", Exact(QUICK_LED_ROUTE)),
    ("POST", Exact(airlines_page.RESOLVE_ROUTE)),
    ("POST", Exact(airlines_page.RENAME_ROUTE)),
    ("POST", Exact(airlines_page.RENAME_RESET_ROUTE)),
    ("POST", PrefixSuffix(
        airlines_page.MANUAL_DELETE_ROUTE_PREFIX, airlines_page.MANUAL_DELETE_ROUTE_SUFFIX)),
    ("POST", PrefixSuffix(ILLUSTRATION_IMAGE_ROUTE_PREFIX, ".png")),
    ("POST", Exact(RULES_ADD_ROUTE)),
    ("POST", PrefixSuffix(RULES_DELETE_ROUTE_PREFIX, RULES_DELETE_ROUTE_SUFFIX)),
    ("POST", Exact(CALENDAR_CONNECT_ROUTE)),
    ("POST", Exact(CALENDAR_DISCONNECT_ROUTE)),
)

# The routes that act on a single device: 13 GET and 14 POST.
_DEVICE_SCOPED_KEYS = frozenset(_PAGE_AND_IMAGE_KEYS + _ACTION_KEYS)

ROUTES = tuple(
    route._replace(device_scoped=(route.method, route.matcher) in _DEVICE_SCOPED_KEYS)
    for route in _GET_ROUTES + _POST_ROUTES
)


def _match_in(routes, method, path, query, device_id):
    for route in routes:
        if route.method != method:
            continue
        matcher = route.matcher
        if isinstance(matcher, Exact):
            if path == matcher.path:
                return route, RouteMatch(path, query, None, device_id)
            continue
        if path.startswith(matcher.prefix) and path.endswith(matcher.suffix):
            captured = (
                path[len(matcher.prefix):-len(matcher.suffix)] if matcher.suffix
                else path[len(matcher.prefix):])
            return route, RouteMatch(path, query, captured, device_id)
    return None


def match(method, path, query):
    """(Route, RouteMatch) for the first ROUTES entry whose method and
    matcher agree with `method`/`path` - the same first-branch-wins order
    the pre-table if-chains evaluated - else None. `query` is carried
    through unparsed onto RouteMatch for a handler that wants it.

    A `/devices/<id>/...` path is matched on its remainder against the
    `device_scoped` routes only, and the id is reported on the match; a
    path that merely starts with `/devices/` but is not a well-formed
    prefix goes through the plain loop and finds nothing.
    """
    prefixed = DEVICE_PREFIX_RE.match(path)
    if prefixed is not None:
        scoped_routes = tuple(route for route in ROUTES if route.device_scoped)
        return _match_in(
            scoped_routes, method, prefixed.group(2) or "/", query, prefixed.group(1))
    return _match_in(ROUTES, method, path, query, None)
