"""The Console Fleet view: the list of frames (live, pending, retired) with its
Add a frame control, the frame switch, the three sections of the
selected frame (State, Settings, Access) and the System
view, plus the navigation that no longer lists Status, Version or Device."""
import datetime
import re
import sqlite3

import pytest

import fleet_console_support as fx
from companion import auth, prefs
from companion.pages import co_managers_card
from server import pairing_code


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
    # The System view is not a row of the list: it has its own navigation entry.
    assert "/fleet?view=system" not in hrefs
    assert 'data-fleet-mode="list"' in page
    # A phone's title is the list's h1; a wide screen's h1 is the neutral pane's heading.
    assert re.search(r'<h1 class="fleet-list__heading fleet-list__heading--narrow">Frames</h1>', page)
    assert re.search(r'<h2 class="fleet-list__heading fleet-list__heading--wide">Frames</h2>', page)
    assert page.count("<h1") == 2
    main = _main(page)
    assert "Select a frame" in main and "fleet-head" not in main and "fleet-block" not in main
    assert not [1 for _h, current in _tiles(page) if current]
    assert 'href="/pair-frame"' in _list(page)
    groups = re.findall(r'class="section-label" id="fleet-list-[a-z]+">([^<]*)<', page)
    assert groups == ["Live \u00b7 2", "Waiting to be paired \u00b7 1", "Retired \u00b7 1"]


def test_no_frame_chosen_shows_a_neutral_pane_with_no_frame_data(fleet):
    server, seed, cookie = fleet
    _status, _headers, page = fx.get(server, cookie, "/fleet")
    main = _main(page)
    assert '<h1 class="fleet-empty__title">Select a frame</h1>' in main
    assert "Choose a frame in the list to see its status and settings." in main
    assert 'href="#icon-device"' in main
    for frame_id in (seed.owned_id, seed.live_id):
        assert frame_id not in main
    assert 'class="fleet-frame' not in main and "<form" not in main
    assert "is-selected" not in page and 'aria-current="page"' not in _list(page)


def test_the_neutral_pane_is_in_french(fleet):
    server, _seed, cookie = fleet
    _status, _headers, page = fx.get(
        server, cookie + "; %s=fr" % auth.UI_LANG_COOKIE_NAME, "/fleet")
    assert "Sélectionnez un cadre" in _main(page)
    assert "Choisissez un cadre dans la liste" in _main(page)


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
    assert 'href="/pair-frame"' in main and "Pair frame" in main
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
    # One column of sections: State (the tiles), Settings, Access.
    assert _blocks(page) == ["State", "Settings", "Access"]
    # The settings form posts to the frame's own route; the wake interval is there.
    assert 'action="/devices/%s/settings"' % seed.owned_id in page
    assert "name=\"wake_interval_s\"" in page
    # The Access block carries the co-manager forms, not a dialog trigger.
    assert 'action="/devices/%s%s"' % (seed.owned_id, co_managers_card.ADD_ROUTE) in page


def test_an_unknown_frame_value_shows_the_list_and_the_neutral_pane(fleet):
    server, _seed, cookie = fleet
    status, _headers, page = fx.get(server, cookie, "/fleet?frame=nope%22%3E")
    assert status == 200
    assert "nope" not in page
    assert 'data-fleet-mode="list"' in page
    assert _blocks(page) == [] and "Select a frame" in _main(page)


def test_the_system_view_shows_the_platform_wide_blocks(fleet):
    server, _seed, cookie = fleet
    status, _headers, page = fx.get(server, cookie, "/fleet?view=system")
    assert status == 200
    # One glass group per topic: flight data, sources, identification and the two route topics.
    assert _blocks(page) == [
        "Flight data", "Data sources", "Identification", "Route directories", "Answered by"]
    assert '<h1 class="page-title">System</h1>' in page
    # System is a page of its own: no frames list, no frame switch, no Add button.
    for absent in ("fleet-split", "fleet-list", "fleet-switch", "fleet-add-button"):
        assert absent not in page, absent


def test_the_console_navigation_no_longer_lists_status_version_or_device(fleet):
    server, seed, cookie = fleet
    _status, _headers, page = fx.get(server, cookie, "/fleet")
    sidebar = page[page.index('<nav class="sidebar-nav"'):]
    sidebar = sidebar[:sidebar.index("</nav>")]
    hrefs = re.findall(r'href="([^"]+)"', sidebar)
    for gone in ("/health", "/device", "/update"):
        assert not [h for h in hrefs if h.endswith(gone)], gone
    assert "/fleet" in hrefs and "/users" in hrefs


def test_the_update_address_moves_to_the_fleet_page(fleet):
    server, _seed, cookie = fleet
    status, headers, _page = fx.get(server, cookie, "/update")
    assert status == 303
    assert headers["Location"].startswith("/fleet?frame=")


@pytest.mark.parametrize("path", ["/health", "/device"])
def test_the_removed_health_and_device_pages_are_not_found(fleet, path):
    server, _seed, cookie = fleet
    assert fx.get(server, cookie, path)[0] == 404


def test_french_block_headings(fleet):
    server, seed, cookie = fleet
    _status, _headers, page = fx.get(
        server, cookie + "; %s=fr" % auth.UI_LANG_COOKIE_NAME,
        "/fleet?frame=%s" % seed.owned_id)
    assert _blocks(page) == ["État", "Réglages", "Accès"]


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


def _anchors(page):
    """(section name, href, current) of the three anchors above the sections."""
    nav = re.search(r'<nav class="fleet-anchors".*?</nav>', page, re.S).group(0)
    return re.findall(r'<a class="fleet-anchor" href="#fleet-section-(\w+)"( aria-current="true")?>([^<]*)<', nav)


def test_the_sections_are_stacked_under_three_anchors_and_no_segmented_tabs(fleet):
    server, seed, cookie = fleet
    _status, _headers, page = fx.get(server, cookie, "/fleet?frame=%s" % seed.owned_id)
    assert [(k, name) for k, _cur, name in _anchors(page)] == [
        ("state", "State"), ("settings", "Settings"), ("access", "Access")]
    assert [k for k, cur, _n in _anchors(page) if cur] == ["state"]
    # Each anchor points at a section of the page, and all three are in the page.
    for key in ("state", "settings", "access"):
        assert 'id="fleet-section-%s"' % key in page
    assert "fleet-tabs" not in page and "data-fleet-tab" not in page


@pytest.mark.parametrize("query,focus", [
    ("", None), ("&tab=state", None), ("&tab=settings", "settings"), ("&tab=access", "access"),
    ("&access=x", "access"), ("&tab=bogus", None), ("&tab=<script>", None)])
def test_a_section_to_bring_into_view_comes_from_the_query_and_unknown_values_mean_none(
        fleet, query, focus):
    server, seed, cookie = fleet
    _status, _headers, page = fx.get(server, cookie, "/fleet?frame=%s%s" % (seed.owned_id, query))
    found = re.search(r'<div class="fleet-blocks" data-fleet-focus="(\w+)">', page)
    assert (found.group(1) if found else None) == focus


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


def _sidebar_links(page):
    """(href, label, is current) of every link of the sidebar navigation."""
    sidebar = page[page.index('<nav class="sidebar-nav"'):]
    sidebar = sidebar[:sidebar.index("</nav>")]
    return [
        (href, re.sub(r"<[^>]+>", "", inner).strip(), bool(current.strip()))
        for href, current, inner in re.findall(
            r'<a class="sidebar-link[^"]*" href="([^"]+)"( aria-current="page")?[^>]*>(.*?)</a>',
            sidebar, re.S)]


@pytest.mark.parametrize("lang,label", [("en", "System"), ("fr", "Système")])
def test_the_system_view_is_reached_from_the_console_navigation(fleet, lang, label):
    server, seed, cookie = fleet
    cookie = "%s; %s=%s" % (cookie, auth.UI_LANG_COOKIE_NAME, lang)
    for path in ("/fleet", "/fleet?frame=%s" % seed.owned_id, "/users"):
        links = _sidebar_links(fx.get(server, cookie, path)[2])
        assert ("/fleet?view=system", label, False) in links, path
    on_system = _sidebar_links(fx.get(server, cookie, "/fleet?view=system")[2])
    assert [href for href, _label, current in on_system if current] == ["/fleet?view=system"]
    on_fleet = _sidebar_links(fx.get(server, cookie, "/fleet")[2])
    assert [href for href, _label, current in on_fleet if current] == ["/fleet"]


def test_the_system_entry_is_a_phone_bar_cell_and_marked_on_its_view(fleet):
    server, _seed, cookie = fleet
    page = fx.get(server, cookie, "/fleet?view=system")[2]
    bar = page[page.index('<nav class="tab-bar"'):]
    bar = bar[:bar.index("</nav>")]
    cells = bar[:bar.index('<details class="tab-bar__more')]
    link = re.search(r'<a class="[^"]*" href="/fleet\?view=system"([^>]*)>', cells)
    assert link and 'aria-current="page"' in link.group(1)
    fleet_cell = re.search(r'<a class="[^"]*" href="/fleet"([^>]*)>', cells)
    assert fleet_cell and "aria-current" not in fleet_cell.group(1)
    sheet = bar[bar.index('<div class="tab-bar__more-panel">'):]
    assert "/fleet?view=system" not in sheet and 'href="/audit"' in sheet


def _set_stored(server, table_column, pending_id, value):
    conn = sqlite3.connect(server.state_dir + "/fleet.db")
    try:
        conn.execute(
            "UPDATE pending_devices SET %s = ? WHERE id = ?" % table_column, (value, pending_id))
        conn.commit()
    finally:
        conn.close()


def _row_text(page, frame_id):
    """The visible text of the list row linking to `frame_id`."""
    row = re.search(
        r'<a class="row__main"[^>]* href="/fleet\?frame=%s".*?</a>' % re.escape(frame_id),
        _list(page), re.S).group(0)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", row)).strip()


def _epoch(year, month, day):
    return int(datetime.datetime(year, month, day, 12, tzinfo=datetime.timezone.utc).timestamp())


@pytest.mark.parametrize("lang,words,year", [
    ("en", "owner@example.test · Retired 12 Oct 2024", 2024),
    ("fr", "owner@example.test · Retiré le 12 oct. 2024", 2024)])
def test_a_retired_row_says_when_it_was_retired(fleet, lang, words, year):
    server, seed, cookie = fleet
    _set_stored(server, "retired_at", seed.retired_id, _epoch(year, 10, 12))
    cookie = "%s; %s=%s" % (cookie, auth.UI_LANG_COOKIE_NAME, lang)
    text = _row_text(fx.get(server, cookie, "/fleet")[2], seed.retired_id)
    assert words in text, text


def test_a_retired_row_of_this_year_has_no_year_and_one_without_a_date_keeps_the_old_wording(fleet):
    server, seed, cookie = fleet
    now = datetime.datetime.now(datetime.timezone.utc)
    _set_stored(server, "retired_at", seed.retired_id, _epoch(now.year, 1, 15))
    text = _row_text(fx.get(server, cookie, "/fleet")[2], seed.retired_id)
    assert "Retired 15 Jan" in text and "Jan %d" % now.year not in text, text
    _set_stored(server, "retired_at", seed.retired_id, None)
    text = _row_text(fx.get(server, cookie, "/fleet")[2], seed.retired_id)
    assert "Formerly owner@example.test" in text and not re.search(r"Retired \d", text), text


@pytest.mark.parametrize("lang,words", [
    ("en", "Code shown 5m ago"), ("fr", "Code affiché il y a 5 min")])
def test_a_pending_row_says_how_long_ago_its_code_was_shown(fleet, lang, words):
    server, seed, cookie = fleet
    fx.issue_code(server.state_dir, seed.pending_id, ttl_s=pairing_code.CODE_TTL_S - 300)
    cookie = "%s; %s=%s" % (cookie, auth.UI_LANG_COOKIE_NAME, lang)
    text = _row_text(fx.get(server, cookie, "/fleet")[2], seed.pending_id).replace("\u00a0", " ")
    assert words in text, text


def test_a_pending_row_with_no_code_keeps_the_waiting_wording(fleet):
    server, seed, cookie = fleet
    text = _row_text(fx.get(server, cookie, "/fleet")[2], seed.pending_id)
    assert "Waiting for pairing" in text and "Code shown" not in text, text


@pytest.mark.parametrize("lang,words", [
    ("en", "Retired · Belonged to owner@example.test"),
    ("fr", "Retiré · Appartenait à owner@example.test")])
def test_a_retired_frames_header_says_who_it_belonged_to(fleet, lang, words):
    server, seed, cookie = fleet
    cookie = "%s; %s=%s" % (cookie, auth.UI_LANG_COOKIE_NAME, lang)
    page = fx.get(server, cookie, "/fleet?frame=%s" % seed.retired_id)[2]
    state = re.search(r'<p class="fleet-head__state">(.*?)</p>', page, re.S).group(1)
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", state)).strip()
    assert words in text, text
    assert "Formerly" not in text and "Anciennement" not in text
