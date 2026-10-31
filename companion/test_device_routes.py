"""Per-device routing: the route table declares which routes act on one
device, and `routes.match()` resolves those (and only those) under a
`/devices/<id>` prefix. Runtime route-table output only.
"""
import re
import types

import pytest

from companion import routes, static_files
from companion_markup import parse_html

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
        assert len(EXPECTED_DEVICE_SCOPED) == 26
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


# --- prefix crawl -----------------------------------------------------------

CRAWL_PREFIXES = ("/devices/",)
CRAWL_PAGES = (
    "/", "/display", "/device", "/flights", "/airlines", "/health",
    "/display?sheet=manage", "/airlines?resolve=XQZ", "/airlines?resolve=ABC",
    "/display?flash=display_on", "/airlines?flash=manual_prefix_stale")
RETURN_TO_FIELD = "return_to"
# A data-* address a script follows: the method is the script's, so either counts.
ANY_METHOD = "ANY"
# Attributes that carry a local address the browser or a script follows.
_ADDRESS_ATTRS = ("href", "action", "src", "formaction")
_UNPREFIXED_PREFIX_REGISTRY = {
    "XQZ": {"count": 3, "first_seen": "t1", "last_seen": "t2", "example_callsign": "XQZ123"}}
_CALENDAR_URL = "https://crawl.example/feed.ics?token=CRAWLTOKEN"


def _seed_crawl_rows(fleet):
    from server.plane import calendar_rules, manual_resolutions
    import server.state_store as state_store
    for device in (fleet.dev_a, fleet.dev_b, fleet.live):
        state_store.save_poll_state(
            device.state_dir, {"unresolved_prefixes": _UNPREFIXED_PREFIX_REGISTRY})
        manual_resolutions.add_entry(
            device.state_dir, "ABC", "Abc Air", now="2026-01-01T00:00:00+00:00")
        calendar_rules.save_calendar_url(device.state_dir, _CALENDAR_URL)


@pytest.fixture(scope="module")
def crawl_app(module_app_server_factory):
    from companion.test_device_helpers import get, start_fleet_app
    app = start_fleet_app(module_app_server_factory, seed_extra=_seed_crawl_rows)
    get(app, "/display")
    return app


@pytest.fixture(scope="module")
def single_device_app(module_app_server_factory):
    from companion_app_server import login
    import skypane_live_state
    from server import fleet_migrate

    def seed(state_dir):
        skypane_live_state.seed_live_like_state(state_dir)
        fleet_migrate.migrate(state_dir, "owner@example.com", dry_run=False)
        _seed_single_rows(state_dir)

    server = module_app_server_factory(seed=seed)
    return types.SimpleNamespace(server=server, cookie=login(server))


def _seed_single_rows(state_dir):
    from server.plane import calendar_rules, manual_resolutions
    import server.state_store as state_store
    state_store.save_poll_state(
        state_dir, {"unresolved_prefixes": _UNPREFIXED_PREFIX_REGISTRY})
    manual_resolutions.add_entry(state_dir, "ABC", "Abc Air", now="2026-01-01T00:00:00+00:00")
    calendar_rules.save_calendar_url(state_dir, _CALENDAR_URL)


def _inside_selector(node):
    while node is not None:
        if "device-selector" in node.attrs.get("class", ""):
            return True
        node = node.parent
    return False


def _crawl_addresses(body):
    """(kind, url, in_selector) for every address a page asks the browser to
    follow: href and src (GET), form action (the form's own method), plus
    every return_to hidden value and data-* address attribute."""
    found = []
    for node in parse_html(body).find_all():
        selector = _inside_selector(node)
        for name, value in node.attrs.items():
            if not isinstance(value, str) or not value.startswith("/") or value.startswith("//"):
                continue
            if name == "action":
                method = node.attrs.get("method", "get").upper()
                found.append((method, value, selector))
            elif name in _ADDRESS_ATTRS:
                found.append(("GET", value, selector))
            elif name.startswith("data-"):
                found.append((ANY_METHOD, value, selector))
        if node.tag == "input" and node.attrs.get("name") == RETURN_TO_FIELD:
            found.append(("RETURN_TO", node.attrs.get("value", ""), selector))
    return found


def _methods(method):
    return ("GET", "POST") if method == ANY_METHOD else (method,)


def _scoped_by_table(method, url):
    path = re.split(r"[?#]", url, maxsplit=1)[0]
    for each in _methods(method):
        found = routes.match(each, path, "")
        if found is not None and found[0].device_scoped:
            return True
    return False


def _crawl(app, prefix, page):
    from companion.test_device_helpers import get
    status, _headers, body = get(app, prefix + page)
    assert status == 200, prefix + page
    return body


class TestPrefixCrawl:
    @pytest.mark.parametrize("page", CRAWL_PAGES)
    def test_every_device_scoped_address_carries_the_devices_prefix(self, crawl_app, page):
        prefix = "/devices/%s" % crawl_app.fleet.dev_a.id
        other = "/devices/%s" % crawl_app.fleet.dev_b.id
        body = _crawl(crawl_app, prefix, page if page != "/" else "/")
        addresses = _crawl_addresses(body)
        assert addresses, page
        for method, url, in_selector in addresses:
            where = "%s%s -> %s %s" % (prefix, page, method, url)
            if method == "RETURN_TO":
                assert "/devices/" not in url, where
                continue
            if in_selector:
                continue
            assert not url.startswith(other), where
            if url.startswith(prefix):
                continue
            assert not _scoped_by_table(method, url), where

    @pytest.mark.parametrize("page", CRAWL_PAGES)
    def test_global_targets_are_never_prefixed(self, crawl_app, page):
        prefix = "/devices/%s" % crawl_app.fleet.dev_a.id
        body = _crawl(crawl_app, prefix, page)
        for method, url, _selector in _crawl_addresses(body):
            if method == "RETURN_TO":
                continue
            path = re.split(r"[?#]", url, maxsplit=1)[0]
            if not path.startswith(prefix):
                continue
            remainder = path[len(prefix):] or "/"
            matches = [routes.match(each, remainder, "") for each in _methods(method)]
            assert any(m is not None and m[0].device_scoped for m in matches), (
                page, method, url)

    def test_the_six_device_pages_and_the_sheet_and_resolve_queries_are_crawled(self):
        assert {"/", "/display", "/device", "/flights", "/airlines", "/health"} <= set(CRAWL_PAGES)
        assert "/display?sheet=manage" in CRAWL_PAGES
        assert any(page.startswith("/airlines?resolve=") for page in CRAWL_PAGES)

    @pytest.mark.parametrize("page", CRAWL_PAGES)
    def test_a_single_device_fleet_never_mentions_a_device_prefix(self, single_device_app, page):
        from companion.test_device_helpers import get
        status, _headers, body = get(single_device_app, page)
        assert status == 200, page
        assert "/devices/" not in body, page
