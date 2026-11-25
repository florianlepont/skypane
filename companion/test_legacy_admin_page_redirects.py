"""The retired Update address still moves every signed-in role to the page that
replaced it, keeping the chosen frame (an administrator lands on the Versions
page of the frame, an owner or user on their own Home); the retired Health and
Device addresses, the frame-prefixed Update address and the old Health view
of the Fleet page are gone and answer the ordinary not-found page."""
import html

import pytest

import fleet_console_support as fx
from companion import prefs
from companion_app_server import http_request

LEGACY = ("/update",)
FLEET_TAB = {"/update": "&view=versions"}
PERSON_PAGE = {"/update": "/"}
REMOVED = ("/health", "/device")


@pytest.fixture(autouse=True)
def _english():
    prefs.set_request_prefs(lang="en")
    yield


@pytest.fixture
def fleet(app_server_in_process):
    server = app_server_in_process
    return server, fx.seed_fleet(server.state_dir)


def _get(server, cookie, path):
    status, headers, _body = http_request(server.url(path), cookie=cookie)
    return status, html.unescape(headers.get("Location") or "")


@pytest.mark.parametrize("path", LEGACY)
def test_an_administrator_lands_on_the_fleet_view_of_the_named_frame(fleet, path):
    server, seed = fleet
    admin = fx.admin_cookie(server.state_dir)
    for frame in (seed.owned_id, seed.live_id):
        assert _get(server, admin, "%s?frame=%s" % (path, frame)) == (
            303, "/fleet?frame=%s%s" % (frame, FLEET_TAB[path])), path


@pytest.mark.parametrize("path", LEGACY)
def test_the_flash_result_is_carried_to_the_fleet(fleet, path):
    server, seed = fleet
    admin = fx.admin_cookie(server.state_dir)
    status, location = _get(
        server, admin, "%s?frame=%s&flash=settings_saved" % (path, seed.owned_id))
    assert status == 303
    assert location.startswith("/fleet?frame=%s" % seed.owned_id)
    assert "flash=settings_saved" in location


@pytest.mark.parametrize("path", LEGACY)
def test_an_owner_lands_on_the_matching_page_of_the_named_own_frame(fleet, path):
    server, seed = fleet
    owner = fx.user_cookie(server.state_dir, fx.OWNER_EMAIL)
    expected = "/devices/%s%s" % (seed.owned_id, PERSON_PAGE[path])
    assert _get(server, owner, "%s?frame=%s" % (path, seed.owned_id)) == (303, expected)
    assert _get(server, owner, path) == (303, expected)


@pytest.mark.parametrize("path", LEGACY)
def test_an_owner_is_never_moved_to_somebody_elses_frame(fleet, path):
    server, seed = fleet
    owner = fx.user_cookie(server.state_dir, fx.OWNER_EMAIL)
    status, location = _get(server, owner, "%s?frame=%s" % (path, seed.live_id))
    assert status == 303
    assert seed.live_id not in location
    assert location.startswith("/devices/%s" % seed.owned_id)


@pytest.mark.parametrize("path", LEGACY)
def test_a_user_without_a_frame_lands_on_the_account_page(fleet, path):
    server, seed = fleet
    plain = fx.user_cookie(server.state_dir, fx.USER_EMAIL)
    assert _get(server, plain, "%s?frame=%s" % (path, seed.owned_id)) == (303, "/account")


@pytest.mark.parametrize("path", LEGACY)
def test_a_signed_out_visitor_is_still_sent_to_sign_in(fleet, path):
    server, _seed = fleet
    status, location = _get(server, None, path)
    assert status == 303 and location.startswith("/login")


def test_the_battery_view_is_served_directly_and_is_never_redirected(fleet):
    server, seed = fleet
    admin = fx.admin_cookie(server.state_dir)
    status, _headers, _body = http_request(
        server.url("/fleet?frame=%s&view=battery" % seed.live_id), cookie=admin)
    assert status == 200


@pytest.mark.parametrize("email", (fx.OWNER_EMAIL, fx.USER_EMAIL))
def test_a_plain_user_gets_the_fleet_refusal_for_the_battery_view(fleet, email):
    server, seed = fleet
    cookie = fx.user_cookie(server.state_dir, email)
    refusal = http_request(server.url("/fleet"), cookie=cookie)[0]
    assert refusal != 200
    for view in ("battery",):
        status, headers, _body = http_request(
            server.url("/fleet?frame=%s&view=%s" % (seed.owned_id, view)), cookie=cookie)
        assert status == refusal
        assert "view=battery" not in html.unescape(headers.get("Location") or "")


@pytest.mark.parametrize("path", REMOVED + ("/update",))
def test_a_removed_address_under_a_frame_prefix_is_the_not_found_page(fleet, path):
    server, seed = fleet
    admin = fx.admin_cookie(server.state_dir)
    owner = fx.user_cookie(server.state_dir, fx.OWNER_EMAIL)
    for cookie in (admin, owner):
        status, _headers, _body = http_request(
            server.url("/devices/%s%s" % (seed.owned_id, path)), cookie=cookie)
        assert status == 404, path


@pytest.mark.parametrize("path", REMOVED)
def test_the_removed_health_and_device_addresses_are_not_found_for_every_role(fleet, path):
    server, seed = fleet
    cookies = (
        fx.admin_cookie(server.state_dir), fx.user_cookie(server.state_dir, fx.OWNER_EMAIL),
        fx.user_cookie(server.state_dir, fx.USER_EMAIL), None)
    for cookie in cookies:
        for query in ("", "?frame=%s" % seed.owned_id):
            status, _headers, _body = http_request(server.url(path + query), cookie=cookie)
            assert status == 404, (path, query)


def test_the_old_health_view_of_the_fleet_page_is_an_ordinary_unknown_view(fleet):
    server, seed = fleet
    admin = fx.admin_cookie(server.state_dir)
    status, headers, _body = http_request(
        server.url("/fleet?frame=%s&view=health" % seed.live_id), cookie=admin)
    assert status == 200 and not headers.get("Location")
