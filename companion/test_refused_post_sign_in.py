"""A form posted after the session ended, over real HTTP: the person is sent to
sign in with the page the form was on as the way back and with the notice that
unsaved changes were not kept, whether the session cookie is stale or gone; an
address that is not one of the app's own pages is never carried."""
from urllib.parse import quote

import pytest

import fleet_console_support as fx
from companion import auth
from companion_app_server import http_request

STALE_COOKIE = "%s=%s" % (auth.SESSION_COOKIE_NAME, "0" * 64)


@pytest.fixture
def rig(app_server_in_process):
    server = app_server_in_process
    return server, fx.seed_fleet(server.state_dir)


def _post(server, path, referer=None, cookie=None, extra=None):
    headers = dict(extra or {})
    if referer is not None:
        headers["Referer"] = referer
    status, response, _body = http_request(
        server.base_url() + path, method="POST", data=b"layout=b", cookie=cookie,
        extra_headers=headers)
    return status, response.get("Location")


def _form_posts(seed):
    """(the posted route, the page its form is on) for a settings form and two quick switches."""
    frame = "/devices/%s" % seed.live_id
    return [
        (frame + "/settings", frame + "/display"),
        (frame + "/settings", frame + "/display/arrivals"),
        (frame + "/quick/display", frame + "/"),
        (frame + "/quick/quiet-hours", frame + "/"),
        ("/users/invite", "/users"),
    ]


@pytest.mark.parametrize("cookie", [None, STALE_COOKIE], ids=["no-cookie", "stale-cookie"])
def test_a_refused_post_goes_to_sign_in_with_its_page_and_the_notice(rig, cookie):
    server, seed = rig
    for route, page in _form_posts(seed):
        status, location = _post(server, route, referer=server.base_url() + page, cookie=cookie)
        assert status == 303, (route, status)
        assert location == "/login?next=%s&expired=1" % quote(page, safe=""), (route, location)


def test_the_way_back_keeps_a_plain_query_of_the_form_page(rig):
    server, seed = rig
    page = "/fleet?frame=%s&tab=settings" % seed.live_id
    _status, location = _post(
        server, "/devices/%s/settings" % seed.live_id, referer=server.base_url() + page)
    assert location == "/login?next=%s&expired=1" % quote(page, safe="")


@pytest.mark.parametrize("referer", [
    None,
    "https://evil.example/account",
    "//evil.example/account",
    "{base}/static/style.css",
    "{base}/login",
    "{base}/account#frag",
    "{base}//evil.example",
    "javascript:alert(1)",
    "not a url",
])
def test_an_address_that_is_not_an_own_page_is_never_carried(rig, referer):
    """the notice still shows, but sign-in then lands on the default page"""
    server, seed = rig
    if referer is not None:
        referer = referer.replace("{base}", server.base_url())
    status, location = _post(server, "/devices/%s/settings" % seed.live_id, referer=referer)
    assert status == 303 and location == "/login?expired=1", (referer, location)


def test_a_page_of_another_host_with_the_same_path_is_not_carried(rig):
    server, seed = rig
    _status, location = _post(
        server, "/devices/%s/settings" % seed.live_id, referer="http://other.example/account")
    assert location == "/login?expired=1"


def test_a_signed_out_page_visit_is_unchanged(rig):
    """a GET keeps its own address as the way back, and says nothing of an ended session unless a
    session cookie came with it"""
    server, _seed = rig
    status, headers, _body = http_request(server.base_url() + "/users")
    assert status == 303 and headers.get("Location") == "/login?next=%2Fusers"
    status, headers, _body = http_request(server.base_url() + "/users", cookie=STALE_COOKIE)
    assert status == 303 and headers.get("Location") == "/login?next=%2Fusers&expired=1"


def test_the_rename_form_still_returns_to_itself(rig):
    server, _seed = rig
    _status, location = _post(server, "/frame/name", referer=server.base_url() + "/account")
    assert location is not None and location.startswith("/login?next="), location
    assert location.endswith("&expired=1"), location


def test_a_query_with_escapes_stays_one_escaped_token(rig):
    """a percent-escaped line break in the form page's query never becomes a real one in the
    answer: the whole way back is one escaped value"""
    server, seed = rig
    referer = server.base_url() + "/account?x=%0d%0aSet-Cookie:a=b"
    _status, location = _post(server, "/devices/%s/settings" % seed.live_id, referer=referer)
    assert location == "/login?next=%s&expired=1" % quote(
        "/account?x=%0d%0aSet-Cookie:a=b", safe="")
    assert "\r" not in location and "\n" not in location and "Set-Cookie:" not in location
