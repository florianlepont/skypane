"""The Console Fleet view: the tile strip of every frame with its Add a screen
and System tiles, the four blocks of the selected frame (State, Device and
version, Settings, Access) and the System view, plus the navigation that no
longer lists Status, Version or Device."""
import re

import pytest

import fleet_console_support as fx
from companion import auth, prefs
from companion.pages import co_managers_card


@pytest.fixture(autouse=True)
def _english():
    prefs.set_request_prefs(lang="en")
    yield


@pytest.fixture
def fleet(app_server_in_process):
    server = app_server_in_process
    seed = fx.seed_fleet(server.state_dir)
    return server, seed, fx.admin_cookie(server.state_dir)


def _strip(page):
    return re.search(r'<ul class="frame-tiles".*?</ul>', page, re.S).group(0)


def _tiles(page):
    return re.findall(r'<a class="frame-tile[^"]*" href="([^"]+)"([^>]*)>', _strip(page))


def _blocks(page):
    return re.findall(r'<section class="fleet-block[^"]*"><h3 class="text-heading">([^<]*)<', page)


def test_the_strip_lists_every_frame_then_add_and_system_tiles(fleet):
    server, seed, cookie = fleet
    _status, _headers, page = fx.get(server, cookie, "/fleet")
    hrefs = [href for href, _attrs in _tiles(page)]
    assert "/fleet?frame=%s" % seed.owned_id in hrefs
    assert "/fleet?frame=%s" % seed.live_id in hrefs
    assert hrefs[-2:] == ["/fleet?pair=1", "/fleet?view=system"]
    assert page.count('aria-current="true"') == 1


def test_a_tile_selects_its_frame_and_outlines_it(fleet):
    server, seed, cookie = fleet
    _status, _headers, page = fx.get(
        server, cookie, "/fleet?frame=%s" % seed.owned_id)
    current = [href for href, attrs in _tiles(page) if 'aria-current="true"' in attrs]
    assert current == ["/fleet?frame=%s" % seed.owned_id]


def test_the_selected_frame_shows_its_four_blocks_in_order(fleet):
    server, seed, cookie = fleet
    status, _headers, page = fx.get(server, cookie, "/fleet?frame=%s" % seed.owned_id)
    assert status == 200
    assert _blocks(page) == ["State", "Device and version", "Settings", "Access"]
    # The settings form posts to the frame's own route; the wake interval is there.
    assert 'action="/devices/%s/settings"' % seed.owned_id in page
    assert "name=\"wake_interval_s\"" in page
    # The Access block carries the co-manager forms, not a dialog trigger.
    assert 'action="/devices/%s%s"' % (seed.owned_id, co_managers_card.ADD_ROUTE) in page


def test_an_unknown_frame_value_falls_back_to_the_first_frame(fleet):
    server, _seed, cookie = fleet
    status, _headers, page = fx.get(server, cookie, "/fleet?frame=nope%22%3E")
    assert status == 200
    assert "nope" not in page
    assert _blocks(page)[:1] == ["State"]


def test_the_system_tile_opens_the_platform_wide_view(fleet):
    server, _seed, cookie = fleet
    status, _headers, page = fx.get(server, cookie, "/fleet?view=system")
    assert status == 200
    assert _blocks(page) == ["System"]
    assert [a for _h, a in _tiles(page) if 'aria-current="true"' in a]
    assert "Backup" in page or "backup" in page


def test_the_console_navigation_no_longer_lists_status_version_or_device(fleet):
    server, seed, cookie = fleet
    _status, _headers, page = fx.get(server, cookie, "/fleet")
    sidebar = page[page.index('<nav class="sidebar-nav"'):]
    sidebar = sidebar[:sidebar.index("</nav>")]
    hrefs = re.findall(r'href="([^"]+)"', sidebar)
    for gone in ("/health", "/device", "/update"):
        assert not [h for h in hrefs if h.endswith(gone)], gone
    assert "/fleet" in hrefs and "/users" in hrefs


@pytest.mark.parametrize("path", ["/health", "/device", "/update"])
def test_the_old_pages_keep_working(fleet, path):
    server, _seed, cookie = fleet
    status, _headers, _page = fx.get(server, cookie, path)
    assert status == 200


def test_french_block_headings(fleet):
    server, seed, cookie = fleet
    _status, _headers, page = fx.get(
        server, cookie + "; %s=fr" % auth.UI_LANG_COOKIE_NAME,
        "/fleet?frame=%s" % seed.owned_id)
    assert _blocks(page) == ["État", "Appareil et version", "Réglages", "Accès"]
