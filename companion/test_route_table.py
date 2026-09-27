"""Table-driven auth coverage for `companion/routes.py`'s ROUTES table:
every route not explicitly public is proven, by enumerating the real
table against a real running server, to answer an unauthenticated
request exactly as the pre-refactor baseline recorded.

Runtime objects and real HTTP only - never `companion/app.py`'s or
`companion/routes.py`'s source text (companion/test_suite_guards.py's
behaviour-over-source rule).
"""
import pytest

from companion import routes, static_files
from companion_app_server import http_request
import companion_render_snapshot

# One concrete sample middle per PrefixSuffix matcher in ROUTES, chosen to
# equal the exact sample companion_render_snapshot.py itself already used
# to build the committed baseline - so a fresh request built from the
# matcher's own constants lands on the identical baseline key.
_SAMPLE_MIDDLE = {
    routes.PrefixSuffix(routes.GALLERY_ROUTE_PREFIX, ""): "sample.png",
    routes.PrefixSuffix(routes.RUNWAY_IMAGE_ROUTE_PREFIX, ".png"): "09",
    routes.PrefixSuffix(routes.ILLUSTRATION_IMAGE_ROUTE_PREFIX, ".png"): "air-france",
    routes.PrefixSuffix(routes.THEME_PREVIEW_ROUTE_PREFIX, ".png"): "midnight",
    routes.PrefixSuffix(
        routes.airlines_page.MANUAL_DELETE_ROUTE_PREFIX,
        routes.airlines_page.MANUAL_DELETE_ROUTE_SUFFIX): "RYR",
    routes.PrefixSuffix(routes.RULES_DELETE_ROUTE_PREFIX, routes.RULES_DELETE_ROUTE_SUFFIX):
        "callsign/AFR",
}


def _sample_path(matcher):
    """Exact -> the path itself. PrefixSuffix -> prefix + the matcher's own
    sample middle (above) + suffix - byte for byte the same slice
    arithmetic `routes.match()` would recover the middle from.
    """
    if isinstance(matcher, routes.Exact):
        return matcher.path
    return matcher.prefix + _SAMPLE_MIDDLE[matcher] + matcher.suffix


def _matcher_matches(matcher, path):
    if isinstance(matcher, routes.Exact):
        return path == matcher.path
    return path.startswith(matcher.prefix) and path.endswith(matcher.suffix)


def _all_matches(method, path):
    return [r for r in routes.ROUTES if r.method == method and _matcher_matches(r.matcher, path)]


# The routes this test expects to be gated, built from the FIXED public
# exemption set (LOGIN_ROUTE + STATIC_ROUTES) rather than from each
# route's own `auth_required` field - so a route whose `auth_required`
# is wrongly flipped to False stays in this worklist and its real,
# observed HTTP response (not the table's own bookkeeping) is what the
# assertion below checks.
_PUBLIC_EXEMPTIONS = {
    ("GET", routes.Exact(routes.LOGIN_ROUTE)),
    ("POST", routes.Exact(routes.LOGIN_ROUTE)),
}
_PUBLIC_EXEMPTIONS |= {("GET", routes.Exact(route)) for route in static_files.STATIC_ROUTES}

_GATED_ROUTES = [r for r in routes.ROUTES if (r.method, r.matcher) not in _PUBLIC_EXEMPTIONS]
_GATED_ROUTE_IDS = [
    "%s_%s" % (r.method, _sample_path(r.matcher).strip("/").replace("/", "_"))
    for r in _GATED_ROUTES
]


def test_public_routes_are_exactly_login_and_static_assets():
    """The only routes with auth_required=False are GET/POST /login and
    one GET per companion/static_files.py STATIC_ROUTES entry - nothing
    else in the table ever grants pre-session access.
    """
    actual = {(r.method, r.matcher) for r in routes.ROUTES if not r.auth_required}
    expected = {
        ("GET", routes.Exact(routes.LOGIN_ROUTE)),
        ("POST", routes.Exact(routes.LOGIN_ROUTE)),
    }
    expected |= {("GET", routes.Exact(route)) for route in static_files.STATIC_ROUTES}
    assert actual == expected


@pytest.fixture(scope="module")
def route_table_server(module_app_server_factory):
    """A read-only-shared server: every gated route below is rejected by
    require_session() before its handler ever runs, so no parametrized
    case here can mutate state (same sharing rationale as
    companion/test_post_origin.py's origin_server fixture).
    """
    return module_app_server_factory()


@pytest.mark.parametrize("route", _GATED_ROUTES, ids=_GATED_ROUTE_IDS)
def test_every_gated_route_redirects_an_anonymous_request(route_table_server, route):
    """A sample path built from `route`'s own matcher, requested with no
    cookie (a POST carries an Origin header auth.post_origin_ok()
    accepts, so the assertion below exercises the session gate, not the
    origin gate), answers with the same status and Location the
    committed pre-refactor baseline recorded for that exact path - and
    that status is always a 303 to LOGIN_ROUTE, with `?next=` where
    require_session() adds one.
    """
    path = _sample_path(route.matcher)
    baseline = companion_render_snapshot.load_baseline()["unauthenticated"]
    key = "%s %s" % (route.method, path)
    expected = baseline[key]

    if route.method == "GET":
        status, headers, _body = http_request(route_table_server.base_url() + path)
    else:
        status, headers, _body = http_request(
            route_table_server.base_url() + path, method="POST", data=b"",
            extra_headers={"Origin": route_table_server.base_url()})

    assert status == expected["status"] == 303, (
        "%s: expected the committed baseline's 303, got %d" % (key, status))
    location = headers.get("Location")
    assert location == expected["location"], (
        "%s: Location %r does not match the committed baseline's %r"
        % (key, location, expected["location"]))
    assert location == routes.LOGIN_ROUTE or location.startswith(routes.LOGIN_ROUTE + "?next="), (
        "%s: expected a redirect to LOGIN_ROUTE, got %r" % (key, location))


def test_every_baseline_route_is_in_the_table():
    """Every 'METHOD path' the committed baseline's unauthenticated map
    records is matched by exactly one ROUTES entry - except the
    baseline's own deliberate not-a-route sample (a 404 with no
    Location), which instead proves routes.match()'s own "no match"
    fallback still 404s. No route is silently dropped, and none is
    declared twice.
    """
    baseline = companion_render_snapshot.load_baseline()["unauthenticated"]
    for key, expected in baseline.items():
        method, path = key.split(" ", 1)
        matches = _all_matches(method, path)
        if not matches:
            assert expected["status"] == 404 and expected["location"] is None, (
                "baseline route %r matched no ROUTES entry and is not the "
                "deliberate not-found sample" % (key,))
            continue
        assert len(matches) == 1, (
            "baseline route %r matched more than one ROUTES entry: %r" % (key, matches))


def test_every_handler_resolves():
    for route in routes.ROUTES:
        assert callable(route.handler), (
            "%s %r has a non-callable handler" % (route.method, route.matcher))
