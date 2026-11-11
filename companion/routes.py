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
route is decided on its own `access` with the id from the prefix (the
ownership gate for `OWNER_DEVICE`); the un-prefixed form acts on the live
frame and is always admin-only (`Handler._dispatch` via `_effective_access`).
The dispatcher applies that decision before it looks the device up.

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
import re
from urllib.parse import parse_qs, urlsplit

from companion import (
    airline_actions, co_managers, console_routes, device_scope, fleet_moves, frame_rename, user_pairing, layout, page_policy, route_types,
    static_files, theme_preview)
from companion.pages import (
    airline_collection_page, airline_types_fragment, airlines_page, co_managers_card, config_page, detection_page, place_page,
    history_page, home_page, personalisation_cards, update_page)

# Anchored on the raw path (never percent-decoded); `\Z` and the absence of
# DOTALL keep a newline from slipping into the id or the remainder.
DEVICE_PREFIX_RE = re.compile(r"\A/devices/(d_[0-9a-f]{8})(/.*)?\Z")

Exact = route_types.Exact
PrefixSuffix = route_types.PrefixSuffix
RouteMatch = route_types.RouteMatch
Access = route_types.Access
Route = route_types.Route

ANONYMOUS = route_types.ANONYMOUS
USER = route_types.USER
ADMIN = route_types.ADMIN

PUBLIC = route_types.PUBLIC
SIGNED_IN = route_types.SIGNED_IN
ADMIN_ONLY = route_types.ADMIN_ONLY
OWNER_DEVICE = route_types.OWNER_DEVICE
ADMIN_DEVICE = route_types.ADMIN_DEVICE
OWNER_ONLY_DEVICE = route_types.OWNER_ONLY_DEVICE

# Literal here, byte-identical to companion/app.py's own constants of the
# same name, since this module can never import companion.app either.
LOGIN_ROUTE = "/login"
CREDITS_ROUTE = "/credits"
AUTH0_LOGIN_ROUTE = "/login/auth0"
CALLBACK_ROUTE = "/callback"
HISTORY_LEGACY_ROUTE = "/history"
PREVIEW_PAGE_ROUTE = "/preview"
QUICK_DISPLAY_ROUTE = "/quick/display"
QUICK_QUIET_HOURS_ROUTE = "/quick/quiet-hours"
QUICK_QUIET_HOURS_WINDOW_ROUTE = "/quick/quiet-hours/window"
QUICK_LED_ROUTE = "/quick/led"
THEME_ROUTE = "/ui-theme"
LANG_ROUTE = "/ui-lang"
LOGOUT_ROUTE = "/logout"
# Answers 204 to a signed-in page that proves its own session (the page's
# anti-forgery token); session-guard.js asks it before showing a restored page.
SESSION_CHECK_ROUTE = "/session/check"
ACCOUNT_ROUTE = "/account"
EXPORT_ROUTE = "/api/export/battery-history"
GALLERY_ROUTE_PREFIX = "/gallery/"
ILLUSTRATION_IMAGE_ROUTE_PREFIX = "/illustration/"

# The seven live tabs, rebound from layout.py's own single definition site.
HOME_ROUTE = layout.HOME_ROUTE
DISPLAY_ROUTE = layout.DISPLAY_ROUTE
FLIGHTS_ROUTE = layout.FLIGHTS_ROUTE
AIRLINES_ROUTE = layout.AIRLINES_ROUTE
MANAGE_ROUTE = airlines_page.MANAGE_ROUTE
HEALTH_ROUTE = layout.HEALTH_ROUTE
DEVICE_ROUTE = layout.DEVICE_ROUTE
UPDATE_ROUTE = layout.UPDATE_ROUTE

DETECTION_ROUTE = detection_page.DETECTION_ROUTE
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


def _personalisation_get_routes():
    """One GET Route per Personalisation view (Look keeps the page's own
    address). Every view is wrapped as the Display tab."""
    def route_for(view_route):
        view = personalisation_cards.view_for_route(view_route)
        return Route(
            "GET", Exact(view_route),
            lambda h, m: h._render_tab(
                DISPLAY_ROUTE,
                lambda ctx: config_page.render(
                    ctx, scope=config_page.SCOPE_DISPLAY, view=view),
                m.device),
            OWNER_DEVICE)
    redirects = tuple(
        Route(
            "GET", Exact(retired),
            lambda h, m: h.redirect(device_scope.scoped(DISPLAY_ROUTE)), OWNER_DEVICE)
        for retired in personalisation_cards.RETIRED_VIEW_ROUTES)
    return tuple(route_for(r) for r in config_page.PERSONALISATION_ROUTES) + redirects


# GET routes, in companion/app.py's pre-table _dispatch_get() branch
# order: the login page, the 17 static assets, the six live tabs, the
# three legacy fixed redirects, then the four prefix-matched image
# routes.
_GET_ROUTES = (
    (
        Route("GET", Exact(LOGIN_ROUTE), lambda h, m: h._handle_login_get(), PUBLIC),
        Route("GET", Exact(AUTH0_LOGIN_ROUTE), lambda h, m: h._handle_login_auth0_get(), PUBLIC),
        Route("GET", Exact(CALLBACK_ROUTE), lambda h, m: h._handle_callback_get(), PUBLIC),
        Route("GET", Exact(CREDITS_ROUTE), lambda h, m: h._handle_credits_get(), PUBLIC),
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
            lambda h, m: h._render_tab(HOME_ROUTE, home_page.render, m.device),
            OWNER_DEVICE),
    )
    + _personalisation_get_routes()
    + (
        Route(
            "GET", Exact(DETECTION_ROUTE),
            lambda h, m: h._render_tab(
                DETECTION_ROUTE,
                lambda ctx: place_page.render(
                    ctx, query=detection_page.parse_query(m.query),
                    place=h._detection_place(m.device)),
                m.device, policy=page_policy.MAP_PAGE_POLICY),
            OWNER_DEVICE),
        Route(
            "GET", Exact(DEVICE_ROUTE),
            fleet_moves.retired_frame_page, ADMIN_ONLY),
        Route(
            "GET", Exact(FLIGHTS_ROUTE),
            lambda h, m: h._render_tab(FLIGHTS_ROUTE, history_page.render, m.device), OWNER_DEVICE),
        Route(
            "GET", Exact(HEALTH_ROUTE),
            fleet_moves.retired_frame_page, ADMIN_DEVICE),
        Route(
            "GET", Exact(AIRLINES_ROUTE),
            lambda h, m: airline_collection_page.get(h, m.device), OWNER_DEVICE),
        Route(
            "GET", Exact(MANAGE_ROUTE),
            lambda h, m: airline_types_fragment.get(h, m.device), ADMIN_DEVICE),
        Route(
            "GET", Exact(UPDATE_ROUTE),
            lambda h, m: fleet_moves.retired_update_page(
                h, m, lambda: h._render_tab(
                    UPDATE_ROUTE,
                    lambda ctx: update_page.render(ctx, h._requested_update_type()),
                    m.device)),
            ADMIN_ONLY),
        # The pre-refactor page routes survive as fixed 303s so a stale
        # bookmark or link still lands somewhere useful. The targets are
        # literals, never derived from any request value; under a device
        # prefix they keep that prefix.
        Route(
            "GET", Exact(SETTINGS_ROUTE),
            lambda h, m: h.redirect(device_scope.scoped(DISPLAY_ROUTE)), OWNER_DEVICE),
        Route(
            "GET", Exact(HISTORY_LEGACY_ROUTE),
            lambda h, m: h.redirect(device_scope.scoped(FLIGHTS_ROUTE)), OWNER_DEVICE),
        Route(
            "GET", Exact(PREVIEW_PAGE_ROUTE),
            lambda h, m: h.redirect(device_scope.scoped(FLIGHTS_ROUTE)), OWNER_DEVICE),
        Route(
            "GET", PrefixSuffix(GALLERY_ROUTE_PREFIX, ""),
            lambda h, m: h._serve_gallery_image(m.device, m.captured), OWNER_DEVICE),
        Route(
            "GET", PrefixSuffix(RUNWAY_IMAGE_ROUTE_PREFIX, ".png"),
            lambda h, m: h._serve_runway_image(m.captured), ADMIN_ONLY),
        Route(
            "GET", PrefixSuffix(ILLUSTRATION_IMAGE_ROUTE_PREFIX, ".png"),
            lambda h, m: h._serve_illustration_image(m.device, m.captured), OWNER_DEVICE),
        Route(
            "GET", PrefixSuffix(THEME_PREVIEW_ROUTE_PREFIX, ".png"),
            lambda h, m: h._serve_theme_preview_image(m.device, m.captured), OWNER_DEVICE),
        Route(
            "GET", PrefixSuffix(FRAME_PREVIEW_ROUTE_PREFIX, ".png"),
            lambda h, m: h._serve_frame_preview_image(m.device, m.captured), OWNER_DEVICE),
    )
)

# POST routes, in companion/app.py's pre-table _dispatch_post() branch
# order (the Origin/Sec-Fetch-Site gate runs before routes.match() is
# ever called - see Handler._dispatch() - so it is not represented here).
_POST_ROUTES = (
    Route(
        "POST", Exact(SETTINGS_ROUTE),
        lambda h, m: h._handle_settings_post(m.device), OWNER_DEVICE),
    Route(
        "POST", Exact(DETECTION_ROUTE),
        lambda h, m: h._handle_detection_post(m.device), OWNER_DEVICE),
    Route(
        "POST", Exact(QUICK_DISPLAY_ROUTE),
        lambda h, m: h._handle_quick_toggle(m.device, "display_enabled"), OWNER_DEVICE),
    Route(
        "POST", Exact(QUICK_QUIET_HOURS_ROUTE),
        lambda h, m: h._handle_quick_toggle(m.device, "quiet_hours_enabled"), OWNER_DEVICE),
    # The Quiet hours dialog on Home: writes the three quiet-hours keys only.
    Route(
        "POST", Exact(QUICK_QUIET_HOURS_WINDOW_ROUTE),
        lambda h, m: h._handle_quiet_hours_window_post(m.device), OWNER_DEVICE, csrf=True),
    # Session-checked POST with the per-session token (a quick switch's form
    # carries it and the script forwards it). return_to whitelist: /device is the LED
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
    Route("POST", Exact(SESSION_CHECK_ROUTE), lambda h, m: h.send_no_content(), SIGNED_IN),
    Route(
        "POST", Exact(airlines_page.RESOLVE_ROUTE),
        lambda h, m: h._handle_manual_resolve_post(m.device), ADMIN_DEVICE),
    Route(
        "POST", Exact(airlines_page.RENAME_ROUTE),
        lambda h, m: h._handle_airline_rename_post(m.device), ADMIN_DEVICE),
    Route(
        "POST", Exact(airlines_page.RENAME_RESET_ROUTE),
        lambda h, m: h._handle_airline_rename_reset_post(m.device), ADMIN_DEVICE),
    Route(
        "POST", Exact(airlines_page.ARTWORK_DELETE_ROUTE),
        lambda h, m: airline_actions.handle_artwork_delete(h, m), ADMIN_DEVICE, csrf=True),
    Route(
        "POST", Exact(airlines_page.DEFAULT_TYPE_ROUTE),
        lambda h, m: airline_actions.handle_default_type(h, m), ADMIN_DEVICE, csrf=True),
    Route(
        "POST",
        PrefixSuffix(airlines_page.MANUAL_DELETE_ROUTE_PREFIX, airlines_page.MANUAL_DELETE_ROUTE_SUFFIX),
        lambda h, m: h._handle_manual_resolution_delete(m.device, m.captured), ADMIN_DEVICE),
    Route(
        "POST", PrefixSuffix(ILLUSTRATION_IMAGE_ROUTE_PREFIX, ".png"),
        lambda h, m: h._handle_illustration_replace(m.device, m.captured), ADMIN_DEVICE),
    Route("POST", Exact(RULES_ADD_ROUTE), lambda h, m: h._handle_rule_add_post(m.device), OWNER_DEVICE),
    Route(
        "POST", Exact(CALENDAR_DISCONNECT_ROUTE),
        lambda h, m: h._handle_calendar_disconnect_post(m.device), OWNER_DEVICE),
    Route(
        "POST", Exact(CALENDAR_CONNECT_ROUTE),
        lambda h, m: h._handle_calendar_connect_post(m.device), OWNER_DEVICE),
    Route(
        "POST", Exact(UPDATE_INSTALL_ROUTE),
        lambda h, m: h._handle_update_install_post(), ADMIN_ONLY),
    Route(
        "POST", Exact(UPDATE_CANCEL_ROUTE),
        lambda h, m: h._handle_update_cancel_post(), ADMIN_ONLY),
    Route(
        "POST", PrefixSuffix(RULES_DELETE_ROUTE_PREFIX, RULES_DELETE_ROUTE_SUFFIX),
        lambda h, m: h._handle_rule_delete_post(m.device, m.captured), OWNER_DEVICE),
    # Managing the member list is the owner's or an administrator's; a
    # co-manager may only leave.
    Route(
        "POST", Exact(co_managers_card.ADD_ROUTE),
        lambda h, m: co_managers.handle_add(h, m), OWNER_ONLY_DEVICE, csrf=True),
    Route(
        "POST", Exact(co_managers_card.REMOVE_ROUTE),
        lambda h, m: co_managers.handle_remove(h, m), OWNER_ONLY_DEVICE, csrf=True),
    Route(
        "POST", Exact(co_managers_card.LEAVE_ROUTE),
        lambda h, m: co_managers.handle_leave(h, m), OWNER_DEVICE, csrf=True),
    Route(
        "POST", Exact(co_managers_card.REMOVE_FRAME_ROUTE),
        lambda h, m: co_managers.handle_remove_frame(h, m), OWNER_ONLY_DEVICE, csrf=True),
)

_PAGE_AND_IMAGE_KEYS = (
    ("GET", Exact(HOME_ROUTE)),
    ("GET", Exact(DISPLAY_ROUTE)),
    ("GET", Exact(personalisation_cards.VIEW_ROUTES["special-looks"])),
    ("GET", Exact(personalisation_cards.VIEW_ROUTES["calendar"])),
    ("GET", Exact(personalisation_cards.VIEW_ROUTES["special-look-new"])),
    ("GET", Exact(personalisation_cards.VIEW_ROUTES["special-look-edit"])),
    ("GET", Exact(personalisation_cards.VIEW_ROUTES["calendar-connect"])),
    ("GET", Exact(personalisation_cards.VIEW_ROUTES["calendar-look"])),
    ("GET", Exact(personalisation_cards.VIEW_ROUTES["arrivals"])),
    ("GET", Exact(personalisation_cards.RETIRED_VIEW_ROUTES[0])),
    ("GET", Exact(personalisation_cards.RETIRED_VIEW_ROUTES[1])),
    ("GET", Exact(DETECTION_ROUTE)),
    ("GET", Exact(DEVICE_ROUTE)),
    ("GET", Exact(FLIGHTS_ROUTE)),
    ("GET", Exact(HEALTH_ROUTE)),
    ("GET", Exact(AIRLINES_ROUTE)),
    ("GET", Exact(MANAGE_ROUTE)),
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
    ("POST", Exact(DETECTION_ROUTE)),
    ("POST", Exact(QUICK_DISPLAY_ROUTE)),
    ("POST", Exact(QUICK_QUIET_HOURS_ROUTE)),
    ("POST", Exact(QUICK_QUIET_HOURS_WINDOW_ROUTE)),
    ("POST", Exact(QUICK_LED_ROUTE)),
    ("POST", Exact(airlines_page.RESOLVE_ROUTE)),
    ("POST", Exact(airlines_page.RENAME_ROUTE)),
    ("POST", Exact(airlines_page.RENAME_RESET_ROUTE)),
    ("POST", Exact(airlines_page.ARTWORK_DELETE_ROUTE)),
    ("POST", Exact(airlines_page.DEFAULT_TYPE_ROUTE)),
    ("POST", PrefixSuffix(
        airlines_page.MANUAL_DELETE_ROUTE_PREFIX, airlines_page.MANUAL_DELETE_ROUTE_SUFFIX)),
    ("POST", PrefixSuffix(ILLUSTRATION_IMAGE_ROUTE_PREFIX, ".png")),
    ("POST", Exact(RULES_ADD_ROUTE)),
    ("POST", PrefixSuffix(RULES_DELETE_ROUTE_PREFIX, RULES_DELETE_ROUTE_SUFFIX)),
    ("POST", Exact(CALENDAR_CONNECT_ROUTE)),
    ("POST", Exact(CALENDAR_DISCONNECT_ROUTE)),
    ("POST", Exact(co_managers_card.ADD_ROUTE)),
    ("POST", Exact(co_managers_card.REMOVE_ROUTE)),
    ("POST", Exact(co_managers_card.LEAVE_ROUTE)),
    ("POST", Exact(co_managers_card.REMOVE_FRAME_ROUTE)),
    ("GET", Exact(frame_rename.page.RENAME_ROUTE)),
    ("POST", Exact(frame_rename.page.RENAME_ROUTE)),
)

# The routes that act on a single device.
_DEVICE_SCOPED_KEYS = frozenset(_PAGE_AND_IMAGE_KEYS + _ACTION_KEYS)

# Form field carrying the per-session anti-forgery token.
CSRF_FIELD = "csrf_token"

# Existing POST routes that need the token: the destructive actions, the
# release actions, the detection form that changes location data, the settings
# form, the quick switches and the theme and language switches. New console routes set `csrf=True` on their own Route.
CSRF_ROUTE_KEYS = frozenset((
    ("POST", Exact(RULES_ADD_ROUTE)),
    ("POST", Exact(CALENDAR_CONNECT_ROUTE)),
    ("POST", Exact(airlines_page.RESOLVE_ROUTE)),
    ("POST", Exact(airlines_page.RENAME_ROUTE)),
    ("POST", PrefixSuffix(ILLUSTRATION_IMAGE_ROUTE_PREFIX, ".png")),
    ("POST", Exact(LOGOUT_ROUTE)),
    ("POST", PrefixSuffix(RULES_DELETE_ROUTE_PREFIX, RULES_DELETE_ROUTE_SUFFIX)),
    ("POST", Exact(CALENDAR_DISCONNECT_ROUTE)),
    ("POST", PrefixSuffix(
        airlines_page.MANUAL_DELETE_ROUTE_PREFIX, airlines_page.MANUAL_DELETE_ROUTE_SUFFIX)),
    ("POST", Exact(airlines_page.RENAME_RESET_ROUTE)),
    ("POST", Exact(UPDATE_INSTALL_ROUTE)),
    ("POST", Exact(UPDATE_CANCEL_ROUTE)),
    ("POST", Exact(DETECTION_ROUTE)),
    ("POST", Exact(SETTINGS_ROUTE)),
    ("POST", Exact(QUICK_DISPLAY_ROUTE)),
    ("POST", Exact(QUICK_QUIET_HOURS_ROUTE)),
    ("POST", Exact(QUICK_LED_ROUTE)),
    ("POST", Exact(THEME_ROUTE)),
    ("POST", Exact(LANG_ROUTE)),
    ("POST", Exact(SESSION_CHECK_ROUTE)),
))

ROUTES = tuple(
    route._replace(
        device_scoped=(route.method, route.matcher) in _DEVICE_SCOPED_KEYS,
        csrf=route.csrf or (route.method, route.matcher) in CSRF_ROUTE_KEYS)
    for route in (
        _GET_ROUTES + _POST_ROUTES + user_pairing.ROUTES + frame_rename.ROUTES
        + console_routes.ROUTES)
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
    if prefixed is not None and method == "GET" and prefixed.group(2) == UPDATE_ROUTE:
        # The retired Update page keeps answering under a frame's prefix: the
        # one global route, with the id carried, so an administrator is moved
        # to that frame's Fleet view (anyone else sees the unknown-path page).
        return _match_in(ROUTES, method, UPDATE_ROUTE, query, prefixed.group(1))
    if prefixed is not None:
        scoped_routes = tuple(route for route in ROUTES if route.device_scoped)
        return _match_in(
            scoped_routes, method, prefixed.group(2) or "/", query, prefixed.group(1))
    return _match_in(ROUTES, method, path, query, None)


def submitted_csrf(handler, route):
    """The anti-forgery token a POST carries: in the form body, except for an
    illustration upload, whose multipart body the handler reads itself and
    whose action URL carries the token in its query instead."""
    if route.matcher == PrefixSuffix(ILLUSTRATION_IMAGE_ROUTE_PREFIX, ".png"):
        return parse_qs(urlsplit(handler.path).query).get(CSRF_FIELD, [None])[0]
    return handler.read_form().get(CSRF_FIELD)
