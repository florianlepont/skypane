"""Wording that must read the same everywhere: the document title carries the frame's name
for every role, and the live frame's default name is translated in the Fleet heading as it is
in the frame button."""
import re

import pytest

import fleet_console_support as fx
from companion import auth, prefs
from companion_app_server import http_request


@pytest.fixture(autouse=True)
def _english():
    prefs.set_request_prefs(lang="en")
    yield


@pytest.fixture
def fleet(app_server_in_process):
    server = app_server_in_process
    return server, fx.seed_fleet(server.state_dir)


def _page(server, cookie, path, lang="en"):
    status, _headers, body = http_request(
        server.url(path), cookie="%s; %s=%s" % (cookie, auth.UI_LANG_COOKIE_NAME, lang))
    assert status == 200, path
    return body.decode("utf-8")


def _title(page):
    return re.search(r"<title>(.*?)</title>", page).group(1)


def test_home_titles_carry_the_frame_name_for_every_role(fleet):
    server, seed = fleet
    admin = fx.admin_cookie(server.state_dir)
    owner = fx.user_cookie(server.state_dir, fx.OWNER_EMAIL)
    assert _title(_page(server, admin, "/devices/%s/" % seed.live_id)) == \
        "Home - Orly frame - SkyPane"
    assert _title(_page(server, admin, "/devices/%s/" % seed.owned_id)) == \
        "Home - Kitchen - SkyPane"
    assert _title(_page(server, owner, "/devices/%s/" % seed.owned_id)) == \
        "Home - Kitchen - SkyPane"


def test_the_live_frame_name_is_translated_in_the_title_the_heading_and_the_button(fleet):
    server, seed = fleet
    admin = fx.admin_cookie(server.state_dir)
    home = _page(server, admin, "/devices/%s/" % seed.live_id, "fr")
    assert _title(home).endswith("Cadre d’Orly - SkyPane")
    fleet_page = _page(server, admin, "/fleet?frame=%s" % seed.live_id, "fr")
    assert 'aria-label="Renommer Cadre d’Orly"' in fleet_page
    assert "Orly frame" not in fleet_page
