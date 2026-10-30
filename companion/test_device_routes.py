"""Per-device routing: the route table declares which routes act on one
device, and `routes.match()` resolves those (and only those) under a
`/devices/<id>` prefix. Runtime route-table output only.
"""
import pytest

from companion import routes, static_files

DEVICE_ID = "d_1a2b3c4d"
PREFIX = "/devices/" + DEVICE_ID

# (method, exact path or (prefix, suffix)) for every device-scoped route.
EXPECTED_DEVICE_SCOPED = {
    ("GET", "/"),
    ("GET", "/display"),
    ("GET", "/device"),
    ("GET", "/flights"),
    ("GET", "/health"),
    ("GET", "/airlines"),
    ("GET", "/settings"),
    ("GET", "/history"),
    ("GET", "/preview"),
    ("GET", ("/gallery/", "")),
    ("GET", ("/illustration/", ".png")),
    ("GET", ("/theme-preview/", ".png")),
    ("GET", ("/frame-preview/", ".png")),
    ("POST", "/settings"),
    ("POST", "/poll-now"),
    ("POST", "/quick/display"),
    ("POST", "/quick/quiet-hours"),
    ("POST", "/quick/led"),
    ("POST", "/airlines/resolve"),
    ("POST", "/airlines/rename"),
    ("POST", "/airlines/rename/reset"),
    ("POST", ("/airlines/manual-resolutions/", "/delete")),
    ("POST", ("/illustration/", ".png")),
    ("POST", "/settings/rules/add"),
    ("POST", ("/settings/rules/", "/delete")),
    ("POST", "/settings/calendar/connect"),
    ("POST", "/settings/calendar/disconnect"),
}

# One concrete request path per expected entry.
SAMPLE_MIDDLE = "sample"


def _concrete(path_spec):
    if isinstance(path_spec, tuple):
        return path_spec[0] + SAMPLE_MIDDLE + path_spec[1]
    return path_spec


def _spec_of(route):
    matcher = route.matcher
    if isinstance(matcher, routes.Exact):
        return matcher.path
    return (matcher.prefix, matcher.suffix)


class TestPrefixMatching:
    def test_flagged_routes_equal_the_explicit_list(self):
        flagged = {(r.method, _spec_of(r)) for r in routes.ROUTES if r.device_scoped}
        assert len(EXPECTED_DEVICE_SCOPED) == 27
        assert flagged == EXPECTED_DEVICE_SCOPED

    @pytest.mark.parametrize("method,spec", sorted(EXPECTED_DEVICE_SCOPED, key=str))
    def test_scoped_route_resolves_under_prefix_like_unprefixed(self, method, spec):
        path = _concrete(spec)
        plain_route, plain_match = routes.match(method, path, "")
        got = routes.match(method, PREFIX + (path if path != "/" else ""), "")
        assert got is not None
        route, matched = got
        assert route is plain_route
        assert matched.device_id == DEVICE_ID
        assert plain_match.device_id is None
        assert matched.path == path
        assert matched.captured == plain_match.captured

    def test_home_resolves_with_and_without_trailing_slash(self):
        home, _ = routes.match("GET", "/", "")
        for path in (PREFIX, PREFIX + "/"):
            route, matched = routes.match("GET", path, "")
            assert route is home
            assert matched.device_id == DEVICE_ID
            assert matched.path == "/"

    def test_query_is_carried_through(self):
        _, matched = routes.match("GET", PREFIX + "/health", "a=1")
        assert matched.query == "a=1"

    @pytest.mark.parametrize("method,path", [
        ("GET", "/login"),
        ("POST", "/login"),
        ("POST", "/logout"),
        ("POST", "/ui-theme"),
        ("POST", "/ui-lang"),
        ("GET", "/update"),
        ("POST", "/update/install"),
        ("POST", "/update/cancel"),
        ("GET", "/runway-image/09.png"),
    ] + [("GET", route) for route in static_files.STATIC_ROUTES])
    def test_global_routes_do_not_match_under_prefix(self, method, path):
        assert routes.match(method, path, "") is not None
        assert routes.match(method, PREFIX + path, "") is None

    @pytest.mark.parametrize("bad_prefix", [
        "/devices/d_1a2b3c4",
        "/devices/d_1A2B3C4D",
        "/devices/d_1a2b3c4dd",
        "/devices/x_1a2b3c4d",
        "/devices/d_1a2b3c4d%2f..",
        "/devices/d_1a2b3c4d\n",
        "/devices/d_1a2b3c4d%0a",
        "/devices/",
        "/devices",
        "/devices/d_1a2b3c4d..",
    ])
    def test_malformed_ids_never_fall_through(self, bad_prefix):
        assert routes.match("GET", bad_prefix, "") is None
        assert routes.match("GET", bad_prefix + "/health", "") is None

    def test_newline_in_remainder_does_not_match(self):
        assert routes.match("GET", PREFIX + "/health\n", "") is None

    def test_unprefixed_match_has_no_device(self):
        _, matched = routes.match("GET", "/health", "")
        assert matched.device_id is None
        assert matched.device is None
