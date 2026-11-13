"""The Console Fleet view: the tile strip of every frame with its Add a frame
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
    return re.search(r'<ul class="frame-menu__list".*?</ul>', page, re.S).group(0)


def _tiles(page):
    return re.findall(r'<a class="frame-row[^"]*" href="([^"]+)"([^>]*)>', _strip(page))


def _blocks(page):
    return re.findall(r'<section class="group-block fleet-block[^"]*"[^>]*><h2 class="section-label"[^>]*>([^<]*)<', page)


def test_the_strip_lists_every_frame_then_system_and_add_tiles(fleet):
    server, seed, cookie = fleet
    _status, _headers, page = fx.get(server, cookie, "/fleet")
    hrefs = [href for href, _attrs in _tiles(page)]
    assert "/fleet?frame=%s" % seed.owned_id in hrefs
    assert "/fleet?frame=%s" % seed.live_id in hrefs
    assert hrefs[-2:] == ["/fleet?view=system", "#dlg-add-frame"]
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
    # One column of section cards: State, Device and version (the version history is inside
    # it), Settings, Access, then the other frames.
    assert _blocks(page) == [
        "State", "Device and version", "Settings", "Access", "Other frames (2)"]
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
    # One glass group per topic: flight data, sources and identification.
    assert _blocks(page) == ["Flight data", "Data sources", "Flight identification"]
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
def test_the_old_pages_move_to_the_fleet_page(fleet, path):
    server, _seed, cookie = fleet
    status, headers, _page = fx.get(server, cookie, path)
    assert status == 303
    assert headers["Location"].startswith("/fleet?frame=")


def test_french_block_headings(fleet):
    server, seed, cookie = fleet
    _status, _headers, page = fx.get(
        server, cookie + "; %s=fr" % auth.UI_LANG_COOKIE_NAME,
        "/fleet?frame=%s" % seed.owned_id)
    assert _blocks(page) == [
        "État", "Appareil et version", "Réglages", "Accès", "Autres cadres (2)"]


def test_the_fleet_page_refreshes_its_nav_dot_and_health_rows_in_place(fleet):
    server, seed, cookie = fleet
    _status, _headers, page = fx.get(server, cookie, "/fleet?frame=%s" % seed.owned_id)
    assert 'data-refresh-page="fleet"' in page
    assert '/static/freshness.js' in page
    _status, _headers, script = fx.get(server, cookie, "/static/freshness.js")
    assert '"fleet": [' in script and 'a[href$="/fleet"]' in script
    # The swapped nav link exists, and the tile links do not end in /fleet.
    assert 'href="/fleet"' in page
    assert all(not href.endswith("/fleet") for href, _attrs in _tiles(page))


@pytest.mark.parametrize("query,current", [
    ("", "State"), ("&tab=state", "State"), ("&tab=settings", "Settings"),
    ("&tab=access", "Access"), ("&access=x", "Access"), ("&tab=bogus", "State"),
    ("&tab=<script>", "State")])
def test_the_sub_tab_comes_from_the_query_and_unknown_values_mean_state(fleet, query, current):
    server, seed, cookie = fleet
    _status, _headers, page = fx.get(server, cookie, "/fleet?frame=%s%s" % (seed.owned_id, query))
    marked = re.findall(r'<a class="personalisation-nav__link" href="[^"]*"'
                        r' aria-current="page"><span>([^<]*)</span>', page)
    assert marked == [current]
    assert 'data-fleet-tab="%s"' % current.lower() in page


def test_a_flash_key_in_the_query_shows_its_toast_for_the_selected_frame(fleet):
    server, seed, cookie = fleet
    _status, _headers, page = fx.get(
        server, cookie, "/fleet?frame=%s&flash=saved" % seed.owned_id)
    assert 'toast' in page and "Saved" in page
    _status, _headers, quiet = fx.get(
        server, cookie, "/fleet?frame=%s&flash=not-a-key" % seed.owned_id)
    assert "Saved" not in quiet


def test_the_settings_save_returns_to_the_frames_fleet_view(fleet):
    from companion_app_server import http_request, with_csrf
    server, seed, cookie = fleet
    status, headers, _body = http_request(
        server.base_url() + "/devices/%s/settings" % seed.owned_id, method="POST",
        data=with_csrf(cookie, {"scope": "device", "return_to": "/device",
                                "quiet_hours_enabled": "on", "quiet_hours_start": "22:00",
                                "quiet_hours_end": "06:00"}),
        cookie=cookie, extra_headers={"Origin": server.base_url()})
    assert status == 303
    assert headers["Location"].startswith(
        "/fleet?frame=%s&tab=settings&flash=" % seed.owned_id)


@pytest.mark.parametrize("lang,words", [
    ("en", "That frame was not found"), ("fr", "Ce cadre est introuvable")])
def test_an_address_naming_a_frame_that_does_not_exist_says_so(fleet, lang, words):
    """a stale or mistyped link shows another frame: the page says which one, in the reader's
    language; a real frame's address and the plain Fleet address say nothing"""
    server, seed, cookie = fleet
    cookie = "%s; %s=%s" % (cookie, auth.UI_LANG_COOKIE_NAME, lang)
    status, _headers, page = fx.get(server, cookie, "/fleet?frame=d_nope")
    assert status == 200
    notice = re.search(r'<div class="toast[^"]*toast--docked[^"]*"[^>]*role="status".*?</div>', page, re.S)
    assert notice and words in notice.group(0), page[:200]
    for path in ("/fleet", "/fleet?frame=%s" % seed.owned_id, "/fleet?view=system"):
        assert words not in fx.get(server, cookie, path)[2], path
