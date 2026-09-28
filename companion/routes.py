"""The one route table `companion/app.py`'s `Handler._dispatch()` walks:
every GET and POST route declared exactly once as `(method, matcher,
handler, auth_required)`.

Never imports `companion.app` (that would be a cycle - `app.py` imports
this module). Route constants that exist only in `app.py` today are
duplicated here as literals instead, the same "duplicated-not-imported"
contract `app.py`'s own `QUICK_*_ROUTE` constants already document for
the identical reason.

Only two matcher shapes exist: `Exact` (a fixed literal path) and
`PrefixSuffix` (a fixed prefix and, for every route but the gallery one,
a fixed suffix too) - a captured middle segment is recovered by slicing
both off, byte for byte the same arithmetic the pre-table if-chains
used. `auth_required=False` is the one place this whole app grants
pre-session access; the only routes with it are GET/POST /login and the
18 static assets in `companion/static_files.py`'s `STATIC_ROUTES`.
"""
import collections

from companion import layout, static_files, theme_preview
from companion.pages import (
    airlines_page, config_page, health_page, history_page, home_page, update_page)

Exact = collections.namedtuple("Exact", "path")
PrefixSuffix = collections.namedtuple("PrefixSuffix", "prefix suffix")
RouteMatch = collections.namedtuple("RouteMatch", "path query captured")
Route = collections.namedtuple("Route", "method matcher handler auth_required")

# Literal here, byte-identical to companion/app.py's own constants of the
# same name, since this module can never import companion.app either.
LOGIN_ROUTE = "/login"
POLL_ROUTE = "/poll-now"
HISTORY_LEGACY_ROUTE = "/history"
PREVIEW_PAGE_ROUTE = "/preview"
QUICK_DISPLAY_ROUTE = "/quick/display"
QUICK_QUIET_HOURS_ROUTE = "/quick/quiet-hours"
QUICK_LED_ROUTE = "/quick/led"
THEME_ROUTE = "/ui-theme"
LANG_ROUTE = "/ui-lang"
LOGOUT_ROUTE = "/logout"
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
NOTIFICATIONS_TEST_ROUTE = config_page.NOTIFICATIONS_TEST_ROUTE
UPDATE_INSTALL_ROUTE = update_page.INSTALL_ROUTE
UPDATE_CANCEL_ROUTE = update_page.CANCEL_ROUTE

THEME_PREVIEW_ROUTE_PREFIX = theme_preview.THEME_PREVIEW_ROUTE_PREFIX


def _static_get_routes():
    """One public GET Route per companion/static_files.py STATIC_ROUTES
    entry, in that dict's own (insertion) order. `m.path` is the request
    path, which for an Exact match always equals the route key itself -
    no closure over the loop variable needed.
    """
    return tuple(
        Route("GET", Exact(route), lambda h, m: h._serve_static_route(m.path), False)
        for route in static_files.STATIC_ROUTES
    )


# GET routes, in companion/app.py's pre-table _dispatch_get() branch
# order: the login page, the 18 static assets, the six live tabs, the
# three legacy fixed redirects, then the four prefix-matched image
# routes.
_GET_ROUTES = (
    (Route("GET", Exact(LOGIN_ROUTE), lambda h, m: h._handle_login_get(), False),)
    + _static_get_routes()
    + (
        Route(
            "GET", Exact(HOME_ROUTE),
            lambda h, m: h._render_tab(HOME_ROUTE, home_page.render), True),
        Route(
            "GET", Exact(DISPLAY_ROUTE),
            lambda h, m: h._render_tab(
                DISPLAY_ROUTE,
                lambda ctx: config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)),
            True),
        Route(
            "GET", Exact(DEVICE_ROUTE),
            lambda h, m: h._render_tab(
                DEVICE_ROUTE,
                lambda ctx: config_page.render(ctx, scope=config_page.SCOPE_DEVICE)),
            True),
        Route(
            "GET", Exact(FLIGHTS_ROUTE),
            lambda h, m: h._render_tab(FLIGHTS_ROUTE, history_page.render), True),
        Route(
            "GET", Exact(HEALTH_ROUTE),
            lambda h, m: h._render_tab(HEALTH_ROUTE, health_page.render), True),
        Route(
            "GET", Exact(AIRLINES_ROUTE),
            lambda h, m: h._render_tab(AIRLINES_ROUTE, airlines_page.render), True),
        Route(
            "GET", Exact(UPDATE_ROUTE),
            lambda h, m: h._render_tab(UPDATE_ROUTE, update_page.render), True),
        # The pre-refactor page routes survive as fixed 303s so a stale
        # bookmark or link still lands somewhere useful. The targets are
        # literals, never derived from any request value.
        Route("GET", Exact(SETTINGS_ROUTE), lambda h, m: h.redirect(DISPLAY_ROUTE), True),
        Route("GET", Exact(HISTORY_LEGACY_ROUTE), lambda h, m: h.redirect(FLIGHTS_ROUTE), True),
        Route("GET", Exact(PREVIEW_PAGE_ROUTE), lambda h, m: h.redirect(FLIGHTS_ROUTE), True),
        Route(
            "GET", PrefixSuffix(GALLERY_ROUTE_PREFIX, ""),
            lambda h, m: h._serve_gallery_image(m.captured), True),
        Route(
            "GET", PrefixSuffix(RUNWAY_IMAGE_ROUTE_PREFIX, ".png"),
            lambda h, m: h._serve_runway_image(m.captured), True),
        Route(
            "GET", PrefixSuffix(ILLUSTRATION_IMAGE_ROUTE_PREFIX, ".png"),
            lambda h, m: h._serve_illustration_image(m.captured), True),
        Route(
            "GET", PrefixSuffix(THEME_PREVIEW_ROUTE_PREFIX, ".png"),
            lambda h, m: h._serve_theme_preview_image(m.captured), True),
    )
)

# POST routes, in companion/app.py's pre-table _dispatch_post() branch
# order (the Origin/Sec-Fetch-Site gate runs before routes.match() is
# ever called - see Handler._dispatch() - so it is not represented here).
_POST_ROUTES = (
    Route("POST", Exact(LOGIN_ROUTE), lambda h, m: h._handle_login_post(), False),
    Route("POST", Exact(SETTINGS_ROUTE), lambda h, m: h._handle_settings_post(), True),
    Route("POST", Exact(POLL_ROUTE), lambda h, m: h._handle_poll_now(), True),
    Route(
        "POST", Exact(QUICK_DISPLAY_ROUTE),
        lambda h, m: h._handle_quick_toggle("display_enabled"), True),
    Route(
        "POST", Exact(QUICK_QUIET_HOURS_ROUTE),
        lambda h, m: h._handle_quick_toggle("quiet_hours_enabled"), True),
    # Session-checked POST only, no CSRF token - SameSite=Strict is the
    # only control here. return_to whitelist: /device is the LED
    # switch's only page, so it is both the sole allowed value and the
    # fallback.
    Route(
        "POST", Exact(QUICK_LED_ROUTE),
        lambda h, m: h._handle_quick_toggle(
            "led_enabled", allowed_return_to=(DEVICE_ROUTE,), fallback_return_to=DEVICE_ROUTE),
        True),
    Route("POST", Exact(THEME_ROUTE), lambda h, m: h._handle_theme_post(), True),
    Route("POST", Exact(LANG_ROUTE), lambda h, m: h._handle_lang_post(), True),
    Route("POST", Exact(LOGOUT_ROUTE), lambda h, m: h._handle_logout_post(), True),
    Route(
        "POST", Exact(airlines_page.RESOLVE_ROUTE),
        lambda h, m: h._handle_manual_resolve_post(), True),
    Route(
        "POST",
        PrefixSuffix(airlines_page.MANUAL_DELETE_ROUTE_PREFIX, airlines_page.MANUAL_DELETE_ROUTE_SUFFIX),
        lambda h, m: h._handle_manual_resolution_delete(m.captured), True),
    Route(
        "POST", PrefixSuffix(ILLUSTRATION_IMAGE_ROUTE_PREFIX, ".png"),
        lambda h, m: h._handle_illustration_replace(m.captured), True),
    Route("POST", Exact(RULES_ADD_ROUTE), lambda h, m: h._handle_rule_add_post(), True),
    Route(
        "POST", Exact(CALENDAR_DISCONNECT_ROUTE),
        lambda h, m: h._handle_calendar_disconnect_post(), True),
    Route(
        "POST", Exact(CALENDAR_CONNECT_ROUTE),
        lambda h, m: h._handle_calendar_connect_post(), True),
    Route(
        "POST", Exact(NOTIFICATIONS_TEST_ROUTE),
        lambda h, m: h._handle_notifications_test_post(), True),
    Route(
        "POST", Exact(UPDATE_INSTALL_ROUTE),
        lambda h, m: h._handle_update_install_post(), True),
    Route(
        "POST", Exact(UPDATE_CANCEL_ROUTE),
        lambda h, m: h._handle_update_cancel_post(), True),
    Route(
        "POST", PrefixSuffix(RULES_DELETE_ROUTE_PREFIX, RULES_DELETE_ROUTE_SUFFIX),
        lambda h, m: h._handle_rule_delete_post(m.captured), True),
)

ROUTES = _GET_ROUTES + _POST_ROUTES


def match(method, path, query):
    """(Route, RouteMatch) for the first ROUTES entry whose method and
    matcher agree with `method`/`path` - the same first-branch-wins order
    the pre-table if-chains evaluated - else None. `query` is carried
    through unparsed onto RouteMatch for a handler that wants it.
    """
    for route in ROUTES:
        if route.method != method:
            continue
        matcher = route.matcher
        if isinstance(matcher, Exact):
            if path == matcher.path:
                return route, RouteMatch(path, query, None)
            continue
        if path.startswith(matcher.prefix) and path.endswith(matcher.suffix):
            captured = (
                path[len(matcher.prefix):-len(matcher.suffix)] if matcher.suffix
                else path[len(matcher.prefix):])
            return route, RouteMatch(path, query, captured)
    return None
