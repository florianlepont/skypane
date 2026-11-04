"""Response policy headers: only the location and detection page widens the
Content-Security-Policy and allows geolocation; every other response keeps the
default pair and names neither external map host."""
import os
import urllib.parse

import pytest

from access_matrix_support import (
    ADMIN_EMAIL, OWNER_EMAIL, seed_matrix_fleet)
from companion import device_scope, routes, route_types
from companion_app_server import (
    InProcessAppServer, http_request, session_cookie_for_state_dir, with_csrf)

DEFAULT_CSP = (
    "default-src 'self'; img-src 'self' data:; "
    "style-src 'self' 'unsafe-inline'; script-src 'self'; "
    "form-action 'self'; frame-ancestors 'none'")
MAP_CSP = (
    "default-src 'self'; img-src 'self' data: https://tile.openstreetmap.org; "
    "connect-src 'self' https://nominatim.openstreetmap.org; "
    "style-src 'self' 'unsafe-inline'; script-src 'self'; "
    "form-action 'self'; frame-ancestors 'none'")
DEFAULT_PERMISSIONS = "geolocation=()"
MAP_PERMISSIONS = "geolocation=(self)"
HOSTS = ("tile.openstreetmap.org", "nominatim.openstreetmap.org")


class Rig:
    def __init__(self, server, fleet, cookies):
        self.server = server
        self.fleet = fleet
        self.cookies = cookies

    def scope(self):
        return "/devices/%s" % self.fleet.owner_device

    def get(self, who, path):
        return http_request(self.server.url(path), cookie=self.cookies[who])

    def post(self, who, path, form, csrf=True):
        cookie = self.cookies[who]
        data = with_csrf(cookie, form) if csrf else urllib.parse.urlencode(form).encode()
        return http_request(
            self.server.url(path), method="POST", data=data, cookie=cookie,
            extra_headers={"Origin": self.server.base_url()})


@pytest.fixture
def rig(tmp_path):
    state_dir = str(tmp_path / "state")
    server = InProcessAppServer(state_dir)
    fleet = seed_matrix_fleet(state_dir)
    for device in device_scope.load_devices(state_dir):
        os.makedirs(device.state_dir, exist_ok=True)
    cookies = {
        "owner": session_cookie_for_state_dir(state_dir, OWNER_EMAIL, "user"),
        "admin": session_cookie_for_state_dir(state_dir, ADMIN_EMAIL, "admin"),
        "anonymous": None,
    }
    yield Rig(server, fleet, cookies)
    server.stop()


def _assert_policy(headers, csp, permissions):
    assert headers["Content-Security-Policy"] == csp
    assert headers["Permissions-Policy"] == permissions
    assert headers["Referrer-Policy"] == "same-origin"
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"


def _assert_map_policy(headers):
    _assert_policy(headers, MAP_CSP, MAP_PERMISSIONS)


def _assert_default_policy(headers):
    _assert_policy(headers, DEFAULT_CSP, DEFAULT_PERMISSIONS)
    for value in headers.values():
        for host in HOSTS:
            assert host not in value


def test_the_map_policy_string_is_exactly_the_two_additions():
    assert "\n" not in MAP_CSP
    for forbidden in ("*", "http:", "blob:", "unsafe-eval", "frame-src"):
        assert forbidden not in MAP_CSP
    assert MAP_CSP.count("script-src") == 1
    assert MAP_CSP.replace(" https://tile.openstreetmap.org", "").replace(
        "connect-src 'self' https://nominatim.openstreetmap.org; ", "") == DEFAULT_CSP


@pytest.mark.parametrize("who", ["owner", "admin"])
def test_the_detection_page_sends_the_map_policy(rig, who):
    status, headers, _body = rig.get(who, rig.scope() + "/detection")
    assert status == 200
    _assert_map_policy(headers)


def test_the_unprefixed_detection_redirect_keeps_the_default_policy(rig):
    status, headers, _body = rig.get("admin", "/detection")
    assert status == 303
    _assert_default_policy(headers)


def test_every_refused_detection_post_sends_the_map_policy(rig):
    path = rig.scope() + "/detection"
    refused = {
        "save_place": ({"action": "save_place"}, 400),
        "save_detection": ({"action": "save_detection", "mode": "sideways"}, 200),
        "save_location": ({"action": "save_location"}, 200),
    }
    for form, expected in refused.values():
        status, headers, _body = rig.post("owner", path, form)
        assert status == expected
        _assert_map_policy(headers)


def test_a_successful_detection_post_redirect_keeps_the_default_policy(rig):
    status, headers, _body = rig.post("owner", rig.scope() + "/detection", {
        "action": "save_detection", "mode": "runway", "airport": "LFMN",
        "runway": "04L/22R"})
    assert status == 303
    _assert_default_policy(headers)


def _plain_get_paths():
    paths = []
    for route in routes.ROUTES:
        if route.method != "GET" or not isinstance(route.matcher, route_types.Exact):
            continue
        if route.matcher.path in ("/detection", "/api/export/battery-history"):
            continue
        paths.append(route.matcher.path)
    return sorted(paths)


def test_the_table_has_get_pages_and_static_files_to_check():
    paths = _plain_get_paths()
    assert "/" in paths and "/credits" in paths and "/static/style.css" in paths
    assert "/static/vendor/leaflet/leaflet.js" in paths


@pytest.mark.parametrize("who", ["admin", "anonymous"])
def test_every_other_get_route_keeps_the_default_policy(rig, who):
    for path in _plain_get_paths():
        _status, headers, _body = rig.get(who, path)
        _assert_default_policy(headers)


def test_other_responses_keep_the_default_policy(rig):
    cases = (
        rig.get("admin", "/no-such-page"),
        rig.get("owner", "/health"),
        rig.get("owner", "/devices/not-a-device/detection"),
        rig.get("anonymous", "/detection"),
        rig.get("anonymous", "/api/export/battery-history"),
        rig.post("owner", rig.scope() + "/settings", {}, csrf=False),
        rig.post("owner", "/ui-theme", {"theme": "dark"}),
    )
    for _status, headers, _body in cases:
        _assert_default_policy(headers)
