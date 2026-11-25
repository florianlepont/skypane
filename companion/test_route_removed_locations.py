"""The Locations console routes are gone: every method and principal gets the
same 404 an unknown path gets, and the places other pages keep still work."""
import pytest

import companion_app_server as cas

_PATHS = (
    ("GET", "/locations"),
    ("POST", "/locations/add"),
    ("POST", "/locations/1/edit"),
    ("POST", "/locations/1/delete"),
    ("GET", "/locations/add"),
    ("GET", "/locations/1/edit"),
)


def _request(server, method, path, cookie):
    data = None
    if method == "POST":
        data = cas.with_csrf(cookie, {"name": "Home"}) if cookie else b"name=Home"
    return cas.http_request(server.url(path), method, data=data, cookie=cookie)


@pytest.fixture
def principals(make_app_server):
    server = make_app_server()
    return server, {
        "administrator": cas.login(server),
        "user": cas.session_cookie_for_state_dir(
            server.state_dir, "someone@example.test", role="user"),
        "anonymous": None,
    }


@pytest.mark.parametrize("principal", ["administrator", "user", "anonymous"])
@pytest.mark.parametrize("method,path", _PATHS)
def test_removed_locations_routes_answer_the_standard_404(principals, principal, method, path):
    server, cookies = principals
    code, _, body = _request(server, method, path, cookies[principal])
    unknown_code, _, unknown_body = _request(
        server, method, "/no-such-page-xyz", cookies[principal])
    assert code == 404
    assert unknown_code == 404
    assert body == unknown_body


def test_place_page_still_opens_for_an_administrator(principals):
    server, cookies = principals
    code, _, _ = cas.http_request(server.url("/detection"), cookie=cookies["administrator"])
    assert code == 200
