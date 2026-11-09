"""Old bookmarks keep working: the retired personal pages (settings, history,
preview) land on their new page for every signed-in role, and a refusal shown to
a signed-in non-admin names the administrator-only case without telling it
apart from an unknown path."""
import html

import pytest

import fleet_console_support as fx
from companion import prefs
from companion_app_server import http_request


@pytest.fixture(autouse=True)
def _english():
    prefs.set_request_prefs(lang="en")
    yield


@pytest.fixture
def fleet(app_server_in_process):
    server = app_server_in_process
    seed = fx.seed_fleet(server.state_dir)
    return server, seed


def _get(server, cookie, path):
    status, headers, body = http_request(server.url(path), cookie=cookie)
    return status, headers.get("Location"), html.unescape(body.decode("utf-8"))


def test_old_bookmarks_reach_the_equivalent_page_for_every_signed_in_role(fleet):
    server, seed = fleet
    owner = fx.user_cookie(server.state_dir, fx.OWNER_EMAIL)
    admin = fx.admin_cookie(server.state_dir)
    for cookie, frame in ((owner, seed.owned_id), (admin, seed.live_id)):
        for path, page in (
                ("/settings", "/display"), ("/history", "/flights"), ("/preview", "/flights")):
            status, location, _body = _get(server, cookie, path)
            assert (status, location) == (303, "/devices/%s%s" % (frame, page)), path


def test_a_person_without_a_frame_is_sent_to_the_account_page(fleet):
    server, _seed = fleet
    plain = fx.user_cookie(server.state_dir, fx.USER_EMAIL)
    for path in ("/settings", "/history", "/preview"):
        status, location, _body = _get(server, plain, path)
        assert (status, location) == (303, "/account"), path


def test_a_signed_out_visitor_is_sent_to_sign_in(fleet):
    server, _seed = fleet
    for path in ("/health", "/device", "/update", "/settings"):
        status, location, _body = _get(server, None, path)
        assert status == 303 and location.startswith("/login"), path


def test_a_non_admin_is_told_the_page_may_be_reserved_and_the_refusal_stays_uniform(fleet):
    server, seed = fleet
    owner = fx.user_cookie(server.state_dir, fx.OWNER_EMAIL)
    bodies = set()
    for path in ("/users", "/audit", "/fleet", "/no-such-page",
                 "/devices/%s/" % seed.live_id):
        status, _location, body = _get(server, owner, path)
        assert status == 404, path
        assert "This page doesn’t exist, or it is reserved for administrators." in body, path
        bodies.add(body)
    assert len(bodies) == 1, "a refusal must not reveal which kind it was"


def test_an_administrator_still_gets_the_plain_not_found_sentence(fleet):
    server, _seed = fleet
    admin = fx.admin_cookie(server.state_dir)
    _status, _location, body = _get(server, admin, "/no-such-page")
    assert "The page you requested doesn’t exist or may have moved." in body
    assert "reserved for administrators" not in body


def test_the_error_page_offers_a_visible_home_button(fleet):
    server, seed = fleet
    owner = fx.user_cookie(server.state_dir, fx.OWNER_EMAIL)
    _status, _location, body = _get(server, owner, "/users")
    assert 'class="error-home-button" href="/devices/%s/"' % seed.owned_id in body
    assert "Back to Home" in body


def test_the_reserved_message_is_in_french(fleet):
    server, _seed = fleet
    owner = fx.user_cookie(server.state_dir, fx.OWNER_EMAIL)
    status, _headers, body = http_request(
        server.url("/users"), cookie=owner + "; sp_ui_lang=fr")
    assert status == 404
    assert "elle est réservée aux administrateurs." in body.decode("utf-8")
