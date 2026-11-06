"""The retired Health, Device and Update pages (and a frame's own Health
address) move every signed-in role to the page that replaced them, keeping the
chosen frame: an administrator lands on the Fleet view of the frame, an owner
or user on the matching page of their own frame."""
import html

import pytest

import fleet_console_support as fx
from companion import prefs
from companion_app_server import http_request

LEGACY = ("/health", "/device", "/update")
PERSON_PAGE = {"/health": "/", "/device": "/display", "/update": "/"}


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
            303, "/fleet?frame=%s" % frame), path


@pytest.mark.parametrize("path", ("/health", "/device"))
def test_a_frames_own_address_lands_on_that_frame_in_the_fleet(fleet, path):
    server, seed = fleet
    admin = fx.admin_cookie(server.state_dir)
    assert _get(server, admin, "/devices/%s%s" % (seed.owned_id, path)) == (
        303, "/fleet?frame=%s" % seed.owned_id)


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


@pytest.mark.parametrize("path", ("/health", "/device"))
def test_an_owner_reaches_the_page_under_their_own_frames_address(fleet, path):
    server, seed = fleet
    owner = fx.user_cookie(server.state_dir, fx.OWNER_EMAIL)
    assert _get(server, owner, "/devices/%s%s" % (seed.owned_id, path)) == (
        303, "/devices/%s%s" % (seed.owned_id, PERSON_PAGE[path]))


@pytest.mark.parametrize("path", ("/health", "/device"))
def test_an_unknown_frame_address_stays_a_not_found_page(fleet, path):
    server, _seed = fleet
    owner = fx.user_cookie(server.state_dir, fx.OWNER_EMAIL)
    status, _headers, _body = http_request(
        server.url("/devices/d_00000000%s" % path), cookie=owner)
    assert status == 404


@pytest.mark.parametrize("path", LEGACY)
def test_a_signed_out_visitor_is_still_sent_to_sign_in(fleet, path):
    server, _seed = fleet
    status, location = _get(server, None, path)
    assert status == 303 and location.startswith("/login")
