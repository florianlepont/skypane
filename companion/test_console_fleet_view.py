"""The Console Fleet view: the list of frames (live, pending, retired) with its
Add a frame control and System row, the frame switch, the four blocks of the
selected frame (State, Device and version, Settings, Access) and the System
view, plus the navigation that no longer lists Status, Version or Device."""
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


def _list(page):
    """The list panel's markup."""
    return re.search(r'<div class="fleet-list">.*?</section></div></div>(?=</div>)', page, re.S).group(0)


def _tiles(page):
    """(href, current attribute) of every row link of the list."""
    return [
        (href, current.strip()) for current, href in re.findall(
            r'<a class="row__main"( aria-current="page")? href="([^"]+)"', _list(page))]


def _main(page):
    """The main column (the frame, or the list view's first frame)."""
    main = page[page.index('class="fleet-split__main"'):]
    return main[:main.index("<dialog")] if "<dialog" in main else main


def _blocks(page):
    return re.findall(r'<section class="group-block fleet-block[^"]*"[^>]*><h2 class="section-label"[^>]*>([^<]*)<', page)


def test_no_frame_chosen_shows_the_list_of_every_frame(fleet):
    server, seed, cookie = fleet
    _status, _headers, page = fx.get(server, cookie, "/fleet")
    hrefs = [href for href, _current in _tiles(page)]
    assert "/fleet?frame=%s" % seed.owned_id in hrefs
    assert "/fleet?frame=%s" % seed.live_id in hrefs
    # Pending and retired frames are in the list, each with its own page.
    assert "/fleet?frame=%s" % seed.pending_id in hrefs
    assert "/fleet?frame=%s" % seed.retired_id in hrefs
    assert hrefs[-1] == "/fleet?view=system"
    assert 'data-fleet-mode="list"' in page
    # A phone's title is the list's h1; a wide screen's h1 is the first frame's name.
    assert re.search(r'<h1 class="fleet-list__heading fleet-list__heading--narrow">Frames</h1>', page)
    assert re.search(r'<h1 class="fleet-head__title">', _main(page))
    assert not [1 for _h, current in _tiles(page) if current]
    assert 'href="#dlg-add-frame"' in _list(page)
    groups = re.findall(r'class="section-label" id="fleet-list-[a-z]+">([^<]*)<', page)
    assert groups == ["Live \u00b7 2", "Waiting to be paired \u00b7 1", "Retired \u00b7 1"]


def test_a_tile_selects_its_frame_and_outlines_it(fleet):
    server, seed, cookie = fleet
    _status, _headers, page = fx.get(
        server, cookie, "/fleet?frame=%s" % seed.owned_id)
    current = [href for href, mark in _tiles(page) if mark]
    assert current == ["/fleet?frame=%s" % seed.owned_id]
    assert 'data-fleet-mode="frame"' in page
    assert '<h1 class="fleet-head__title">Kitchen</h1>' in page


def test_the_frame_switch_starts_with_all_frames_and_has_no_retired_or_pending_frame(fleet):
    server, seed, cookie = fleet
    _status, _headers, page = fx.get(
        server, cookie, "/fleet?frame=%s" % seed.owned_id)
    switch = re.search(r'<nav class="fleet-switch".*?</nav>', page, re.S).group(0)
    hrefs = re.findall(r'href="([^"]+)"', switch)
    assert hrefs[0] == "/fleet" and "All frames (4)" in switch
    assert sorted(hrefs[1:]) == sorted([
        "/fleet?frame=%s" % seed.owned_id, "/fleet?frame=%s" % seed.live_id])
    assert hrefs[1] == "/fleet?frame=%s" % seed.owned_id
    assert switch.count('aria-current="page"') == 1


def test_a_retired_frame_opens_its_own_page_with_only_its_action(fleet):
    server, seed, cookie = fleet
    _status, _headers, page = fx.get(
        server, cookie, "/fleet?frame=%s" % seed.retired_id)
    main = _main(page)
    assert 'data-fleet-mode="other"' in page
    assert '<h1 class="fleet-head__title">Attic</h1>' in main
    assert 'href="#dlg-reactivate-%s"' % seed.retired_id.lower().replace("_", "-") in main
    assert "Press Reset to restart it now." in main
    assert "Settings" not in main and "fleet-block" not in main


def test_a_pending_frame_opens_its_own_page_with_the_pairing_action(fleet):
    server, seed, cookie = fleet
    _status, _headers, page = fx.get(
        server, cookie, "/fleet?frame=%s" % seed.pending_id)
    main = _main(page)
    assert 'data-fleet-mode="other"' in page
    assert 'href="#dlg-add-frame"' in main and "Pair frame" in main
    assert "fleet-block" not in main


def test_retired_and_pending_frames_never_appear_on_a_frames_page(fleet):
    server, seed, cookie = fleet
    _status, _headers, page = fx.get(
        server, cookie, "/fleet?frame=%s" % seed.owned_id)
    main = _main(page)
    for text in ("Other frames", "Attic", "New frame", seed.retired_id, seed.pending_id):
        assert text not in main, text


def test_a_frame_id_that_is_not_listed_shows_the_list(fleet):
    server, seed, cookie = fleet
    _status, _headers, page = fx.get(server, cookie, "/fleet?frame=nope")
    assert 'data-fleet-mode="list"' in page


def test_the_selected_frame_shows_its_four_blocks_in_order(fleet):
    server, seed, cookie = fleet
    status, _headers, page = fx.get(server, cookie, "/fleet?frame=%s" % seed.owned_id)
    assert status == 200
    # One column of section cards: State, Device and version (the version history is inside
    # it), Settings, Access.
    assert _blocks(page) == ["State", "Device and version", "Settings", "Access"]
    # The settings form posts to the frame's own route; the wake interval is there.
    assert 'action="/devices/%s/settings"' % seed.owned_id in page
    assert "name=\"wake_interval_s\"" in page
    # The Access block carries the co-manager forms, not a dialog trigger.
    assert 'action="/devices/%s%s"' % (seed.owned_id, co_managers_card.ADD_ROUTE) in page


def test_an_unknown_frame_value_shows_the_list_and_the_first_frame(fleet):
    server, _seed, cookie = fleet
    status, _headers, page = fx.get(server, cookie, "/fleet?frame=nope%22%3E")
    assert status == 200
    assert "nope" not in page
    assert 'data-fleet-mode="list"' in page
    assert _blocks(page)[:1] == ["State"]


def test_the_system_tile_opens_the_platform_wide_view(fleet):
    server, _seed, cookie = fleet
    status, _headers, page = fx.get(server, cookie, "/fleet?view=system")
    assert status == 200
    # One glass group per topic: flight data, sources and identification.
    assert _blocks(page) == ["Flight data", "Data sources", "Flight identification"]
    assert [h for h, mark in _tiles(page) if mark] == ["/fleet?view=system"]
    assert '<h1 class="fleet-head__title">System</h1>' in page
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
        "État", "Appareil et version", "Réglages", "Accès"]


def test_the_fleet_page_refreshes_its_nav_dot_and_health_rows_in_place(fleet):
    server, seed, cookie = fleet
    _status, _headers, page = fx.get(server, cookie, "/fleet?frame=%s" % seed.owned_id)
    assert 'data-refresh-page="fleet"' in page
    assert '/static/freshness.js' in page
    _status, _headers, script = fx.get(server, cookie, "/static/freshness.js")
    assert '"fleet": [' in script and 'a[href$="/fleet"]' in script
    # The swapped nav link exists, and the list's row links do not end in /fleet.
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
    """a stale or mistyped link shows the list: the page says the frame was not found, in the
    reader's language; a real frame's address and the plain Fleet address say nothing"""
    server, seed, cookie = fleet
    cookie = "%s; %s=%s" % (cookie, auth.UI_LANG_COOKIE_NAME, lang)
    status, _headers, page = fx.get(server, cookie, "/fleet?frame=d_nope")
    assert status == 200
    notice = re.search(r'<div class="toast[^"]*toast--docked[^"]*"[^>]*role="status".*?</div>', page, re.S)
    assert notice and words in notice.group(0), page[:200]
    for path in (
            "/fleet", "/fleet?frame=%s" % seed.owned_id, "/fleet?frame=%s" % seed.retired_id,
            "/fleet?view=system"):
        assert words not in fx.get(server, cookie, path)[2], path
