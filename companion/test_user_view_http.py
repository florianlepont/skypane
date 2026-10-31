"""The reduced user view over the real handlers: a fleet with provisioned
device directories, no stubbed routes, real session cookies. Proves page and
derived-image access (owner, another user, admin), the identical 404, and the
live-frame and selector rules, over HTTP.
"""
import os
import re

import pytest

from companion import routes
from companion_app_server import (
    InProcessAppServer, http_request, session_cookie_for_state_dir)
from provisioned_fleet import (
    ADMIN_EMAIL, FRAMELESS_EMAIL, GALLERY_FILENAME, NAME_A1, NAME_A2, NAME_B1,
    USER_A_EMAIL, USER_B_EMAIL, provision_fleet)
from server import device_dirs

_EMAILS = {
    "a": USER_A_EMAIL, "b": USER_B_EMAIL, "admin": ADMIN_EMAIL,
    "frameless": FRAMELESS_EMAIL}

# One concrete middle per templated route; a new owner-device route without an
# entry here fails `test_every_owner_device_get_route_has_a_sample`.
SAMPLE_MIDDLE = {
    "/gallery/{}": GALLERY_FILENAME,
    "/illustration/{}.png": "air-france",
    "/theme-preview/{}.png": "black",
    "/frame-preview/{}.png": "white",
}

# The legacy page routes are fixed redirects to a current page.
LEGACY_REDIRECT = {"/settings": "/display", "/history": "/flights", "/preview": "/flights"}

UNKNOWN_ID = "d_00000000"


def _template(route):
    matcher = route.matcher
    if isinstance(matcher, routes.Exact):
        return matcher.path
    return matcher.prefix + "{}" + matcher.suffix


def _owner_get_templates():
    return [
        _template(r) for r in routes.ROUTES
        if r.method == "GET" and r.access == routes.OWNER_DEVICE]


def _sample(template):
    if "{}" not in template:
        return template
    assert template in SAMPLE_MIDDLE, "no sample path declared for " + template
    return template.replace("{}", SAMPLE_MIDDLE[template])


class Rig:
    """A running companion over one provisioned fleet, with a session cookie
    per persona."""

    def __init__(self, state_dir, live_owner="admin"):
        self.state_dir = state_dir
        self.server = InProcessAppServer(state_dir)
        self.fleet = provision_fleet(state_dir, live_owner=live_owner)
        self.cookies = {
            name: session_cookie_for_state_dir(state_dir, email)
            for name, email in _EMAILS.items()}
        self.cookies["anonymous"] = None

    def request(self, method, path, who, data=None, extra_headers=None):
        headers = dict(extra_headers or {})
        if method == "POST":
            headers["Origin"] = self.server.base_url()
        return http_request(
            self.server.url(path), method=method, data=data,
            cookie=self.cookies[who], extra_headers=headers or None)

    def get(self, path, who):
        return self.request("GET", path, who)

    def page(self, path, who):
        status, _headers, body = self.get(path, who)
        assert status == 200, (path, who, status)
        return body.decode("utf-8")

    def unknown_404(self, who):
        status, _headers, body = self.get("/no-such-page-anywhere", who)
        assert status == 404
        return body

    def assert_unknown(self, method, path, who, data=None):
        status, _headers, body = self.request(method, path, who, data=data)
        assert status == 404, (method, path, who, status)
        assert body == self.unknown_404(who), (method, path, who)

    def stop(self):
        self.server.stop()


# Function-scoped on purpose: `Handler.args` is a class attribute, so a second
# in-process server in the same interpreter would re-point a long-lived one at
# its own state directory.
@pytest.fixture
def rig(tmp_path):
    built = Rig(str(tmp_path / "state"))
    yield built
    built.stop()


@pytest.fixture
def live_rig(tmp_path):
    built = Rig(str(tmp_path / "state"), live_owner="a")
    yield built
    built.stop()


def test_the_provisioned_fleet_has_real_device_directories(rig):
    for device_id in (rig.fleet.a1, rig.fleet.a2, rig.fleet.b1):
        directory = device_dirs.resolve_state_dir(
            rig.state_dir, device_dirs.state_path_for(device_id))
        assert os.path.isfile(os.path.join(directory, "device_config.json"))
        assert os.path.isfile(os.path.join(directory, "gallery", GALLERY_FILENAME))


def test_every_owner_device_get_route_has_a_sample():
    templates = _owner_get_templates()
    assert templates
    for template in templates:
        _sample(template)


@pytest.mark.parametrize("template", _owner_get_templates())
def test_an_owner_reaches_their_frame_and_another_user_gets_the_unknown_404(
        rig, template):
    path = "/devices/%s%s" % (rig.fleet.a1, _sample(template))
    status, headers, body = rig.get(path, "a")
    if template in LEGACY_REDIRECT:
        assert status == 303
        assert headers["Location"] == "/devices/%s%s" % (
            rig.fleet.a1, LEGACY_REDIRECT[template])
    else:
        assert status == 200, path
        assert body
    rig.assert_unknown("GET", path, "b")
    admin_status, _h, _b = rig.get(path, "admin")
    assert admin_status == (303 if template in LEGACY_REDIRECT else 200)


@pytest.mark.parametrize("template", _owner_get_templates())
def test_the_unprefixed_frame_routes_are_admin_only(rig, template):
    path = _sample(template)
    for who in ("a", "b", "frameless"):
        rig.assert_unknown("GET", path, who)
    anonymous_status, headers, _b = rig.get(path, "anonymous")
    assert anonymous_status == 303 and headers["Location"].startswith("/login")


@pytest.mark.parametrize("path", ["/", "/display", "/flights", "/health", "/airlines"])
def test_an_admin_reaches_the_unprefixed_pages(rig, path):
    assert rig.get(path, "admin")[0] == 200


@pytest.mark.parametrize("path", ["/device", "/update", "/runway-image/06-24.png"])
def test_admin_only_frame_routes_are_404_for_users_in_both_forms(rig, path):
    for who in ("a", "b"):
        rig.assert_unknown("GET", path, who)
        rig.assert_unknown("GET", "/devices/%s%s" % (rig.fleet.a1, path), who)


def test_a_user_who_owns_the_live_frame_is_served_under_its_real_id(live_rig):
    live = live_rig.fleet.live
    home = live_rig.page("/devices/%s/" % live, "a")
    assert "/devices/%s/" % live in home
    live_rig.assert_unknown("GET", "/", "a")
    pages = ("/", "/display", "/flights", "/health", "/airlines")
    for path in pages:
        body = live_rig.page("/devices/%s%s" % (live, path), "a")
        links = re.findall(r'(?:data-)?href="([^"]*)"', body)
        for target in links:
            assert target not in ("/display", "/flights", "/health", "/airlines"), (
                path, target)
        assert any(t.startswith("/devices/%s" % live) for t in links), path
        assert 'value="live"' not in body


def test_the_selector_lists_only_the_users_own_frames(rig):
    body = rig.page("/devices/%s/display" % rig.fleet.a1, "a")
    for own in (rig.fleet.a1, rig.fleet.a2):
        assert 'value="%s"' % own in body
    assert NAME_A1 in body and NAME_A2 in body
    for foreign in (rig.fleet.b1, rig.fleet.live):
        assert foreign not in body
    assert NAME_B1 not in body


def test_a_selector_value_naming_a_foreign_frame_is_a_404_that_hides_existence(rig):
    base = "/devices/%s/display" % rig.fleet.a1
    # The page keeps the caller's own navigation, so it is compared with the
    # answer for an id that exists nowhere: a foreign id must be no different.
    status, _h, unknown_id_body = rig.get("%s?device=%s" % (base, UNKNOWN_ID), "a")
    assert status == 404
    for value in (rig.fleet.b1, rig.fleet.live, rig.fleet.pending, "live"):
        status, _h, body = rig.get("%s?device=%s" % (base, value), "a")
        assert status == 404, value
        assert body == unknown_id_body, value
    assert rig.fleet.b1 not in unknown_id_body.decode("utf-8")
    status, headers, _b = rig.get("%s?device=%s" % (base, rig.fleet.a2), "a")
    assert status == 303
    assert headers["Location"] == "/devices/%s/display" % rig.fleet.a2


def test_pending_and_retired_frames_do_not_exist_for_a_user(rig):
    for pending_id in (rig.fleet.pending, rig.fleet.retired):
        assert pending_id.startswith("p_")
        for who in ("a", "b", "frameless"):
            rig.assert_unknown("GET", "/devices/%s/" % pending_id, who)
            rig.assert_unknown("GET", "/devices/%s/display" % pending_id, who)
    for who in ("a", "b"):
        for body_text in (rig.page("/account", who), rig.page(
                "/devices/%s/" % (rig.fleet.a1 if who == "a" else rig.fleet.b1), who)):
            assert rig.fleet.pending not in body_text
            assert rig.fleet.retired not in body_text
