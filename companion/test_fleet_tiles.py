"""The State section of a frame's page (four equal tiles, each with a Details link) and the two
pages the tiles open: Health (every block of the page) and Versions (the installed version, the
update and every release), served by the real app and read as markup."""
import datetime
import html
import re

import pytest

import fleet_console_support as fx
from companion import auth, prefs
from companion.pages import update_page
from companion.test_browser_ux_helpers import seed_two_releases
from server import device_config, fleet_db, history_db


@pytest.fixture(autouse=True)
def _english():
    prefs.set_request_prefs(lang="en")
    yield


@pytest.fixture
def fleet(app_server_in_process):
    server = app_server_in_process
    seed = fx.seed_fleet(server.state_dir)
    return server, seed, fx.admin_cookie(server.state_dir)


def _seed_readings(state_dir, count=12):
    now = datetime.datetime.now(datetime.timezone.utc)
    with history_db.open_db(state_dir) as conn:
        for i in range(count):
            stamp = now - datetime.timedelta(hours=6 * (count - 1 - i), seconds=20)
            history_db.record_device_health(
                conn, stamp.isoformat(timespec="seconds"), battery_mv=4050 - 9 * i,
                fw_version="1.0.0", boot_reason="wake", rssi="-60")
    device_config.save_device_config(state_dir, wake_interval_s=600)


def _page(server, cookie, path, lang="en"):
    status, _headers, body = fx.get(server, cookie + "; %s=%s" % (auth.UI_LANG_COOKIE_NAME, lang), path)
    assert status == 200, path
    return body if isinstance(body, str) else body.decode("utf-8")


def _tiles(page):
    """(label, value, meta, href, state) of every tile of the State section."""
    section = re.search(r'<ul class="fleet-tiles">.*?</ul>', page, re.S).group(0)
    found = []
    for tile in re.findall(r'<a class="fleet-tile".*?</a>', section, re.S):
        def part(name):
            m = re.search(r'<span class="fleet-tile__%s">(.*?)</span>(?=<)' % name, tile, re.S)
            return html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else ""
        found.append((
            part("label"), part("value"), part("meta"),
            html.unescape(re.search(r'href="([^"]+)"', tile).group(1)),
            re.search(r'data-state="(\w+)"', tile).group(1)))
    return found


LABELS = {
    "en": ["Frame connection", "Battery", "Flight data", "Firmware"],
    "fr": ["Connexion du cadre", "Batterie", "Données de vol", "Micrologiciel"]}
DETAILS = {"en": "Details", "fr": "Détails"}


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_state_section_is_four_tiles_each_with_a_details_link(fleet, lang):
    server, seed, cookie = fleet
    _seed_readings(server.state_dir)
    seed_two_releases(server.state_dir)
    page = _page(server, cookie, "/fleet?frame=" + seed.live_id, lang)
    tiles = _tiles(page)
    assert [t[0] for t in tiles] == LABELS[lang]
    base = "/fleet?frame=%s&view=" % seed.live_id
    assert [t[3] for t in tiles] == [base + "health"] * 3 + [base + "versions"]
    assert page.count('<span class="fleet-tile__more">%s' % DETAILS[lang]) == 4
    battery = tiles[1]
    assert re.match(r"\d+\s?% · \d+\s?mV", battery[1]), battery
    assert tiles[3][1] == "fw-v1.0.0" and tiles[3][2]
    # The battery tile draws the curve; the others carry no drawing.
    assert page.count("fleet-tile__spark") == 1
    # The three statuses of the old State block are not rows any more.
    assert "health-row" not in page


def test_a_frame_that_never_checked_in_still_has_its_four_tiles(fleet):
    server, seed, cookie = fleet
    page = _page(server, cookie, "/fleet?frame=" + seed.owned_id)
    tiles = _tiles(page)
    assert [t[0] for t in tiles] == LABELS["en"]
    assert tiles[0][1] == "No check-in yet"
    assert "fleet-tile__spark" not in page
    assert all("/fleet?frame=%s&view=" % seed.owned_id in t[3] for t in tiles)


def test_a_battery_tile_without_readings_says_so_and_draws_nothing(fleet):
    server, seed, cookie = fleet
    with history_db.open_db(server.state_dir):
        pass
    page = _page(server, cookie, "/fleet?frame=" + seed.live_id)
    battery = _tiles(page)[1]
    assert battery[1] == "No readings yet" and battery[4] == "off"
    assert "fleet-tile__spark" not in page


def test_the_tile_state_is_spelled_out_not_only_coloured(fleet):
    server, seed, cookie = fleet
    _seed_readings(server.state_dir)
    page = _page(server, cookie, "/fleet?frame=" + seed.live_id)
    for tile in re.findall(r'<a class="fleet-tile" data-state="(\w+)".*?</a>', page, re.S):
        assert tile in ("ok", "warn", "error", "off")
    assert re.search(r'fleet-tile__icon">.*?<span class="visually-hidden">Healthy</span>', page, re.S)


def test_the_overview_has_one_h1_and_no_list_column_change(fleet):
    server, seed, cookie = fleet
    page = _page(server, cookie, "/fleet?frame=" + seed.live_id)
    assert len(re.findall(r"<h1[ >]", page)) == 1


# ---- Health ---------------------------------------------------------------

def _rename(state_dir, device_id, name):
    conn = fleet_db.connect(state_dir)
    try:
        fleet_db.rename_device(conn, device_id, name)
    finally:
        conn.close()


def test_the_health_page_keeps_every_block_and_opens_the_rows(fleet):
    server, seed, cookie = fleet
    _seed_readings(server.state_dir)
    page = _page(server, cookie, "/fleet?frame=%s&view=health" % seed.live_id)
    assert 'data-fleet-mode="detail"' in page
    assert len(re.findall(r"<h1[ >]", page)) == 1 and '<h1 class="fleet-head__title">Health</h1>' in page
    # The frame's blocks, then the platform blocks of an administrator.
    for row in ("connection", "battery", "flight-data", "sources", "identification"):
        assert re.search(r'<details class="health-row" [^>]*id="health-row-%s"[^>]* open>' % row, page), row
    assert "Server &amp; data" in page and ">Frame<" in page
    # The battery row keeps its readout, chart and readings table.
    assert 'class="battery-readout' in page and "battery-unit" in page and "readings-disclosure" in page
    # The list column is not part of this page, and the old tiles are not either.
    assert "fleet-list" not in page and "fleet-tile" not in page


def test_the_health_page_does_not_link_to_the_unresolved_airlines(fleet):
    server, seed, cookie = fleet
    _seed_readings(server.state_dir)
    page = _page(server, cookie, "/fleet?frame=%s&view=health" % seed.live_id)
    row = page.split('id="health-row-identification"')[1].split("</details>")[0]
    assert "<a " not in row and "/airlines/manage" not in row


def test_the_health_page_of_a_frame_that_never_checked_in_says_so(fleet):
    server, seed, cookie = fleet
    page = _page(server, cookie, "/fleet?frame=%s&view=health" % seed.owned_id)
    assert "This frame has not checked in yet" in page
    assert 'id="health-row-' not in page


def test_the_health_page_has_a_way_back_to_the_frame_and_escapes_its_name(fleet):
    server, seed, cookie = fleet
    hostile = '<img src=x onerror=alert(1)>"&'
    _rename(server.state_dir, seed.owned_id, hostile)
    for view in ("health", "versions"):
        page = _page(server, cookie, "/fleet?frame=%s&view=%s" % (seed.owned_id, view))
        assert "<img src=x" not in page
        back = re.search(r'<a class="fleet-back" href="([^"]+)">.*?<span>(.*?)</span></a>', page, re.S)
        assert back.group(1) == "/fleet?frame=%s" % seed.owned_id
        assert html.unescape(back.group(2)) == "Back to " + hostile


@pytest.mark.parametrize("lang,back,title", [("en", "Back to Kitchen", "Health"), ("fr", "Retour à Kitchen", "État")])
def test_the_back_link_and_title_are_translated(fleet, lang, back, title):
    server, seed, cookie = fleet
    page = _page(server, cookie, "/fleet?frame=%s&view=health" % seed.owned_id, lang)
    assert back in html.unescape(page)
    assert '<h1 class="fleet-head__title">%s</h1>' % title in page


def test_an_unknown_detail_view_shows_the_frame_page(fleet):
    server, seed, cookie = fleet
    page = _page(server, cookie, "/fleet?frame=%s&view=nope" % seed.live_id)
    assert 'data-fleet-mode="frame"' in page and "fleet-tiles" in page


# ---- Versions -------------------------------------------------------------

def test_the_versions_page_shows_the_installed_version_the_update_and_every_release(fleet):
    server, seed, cookie = fleet
    seed_two_releases(server.state_dir)
    page = _page(server, cookie, "/fleet?frame=%s&view=versions" % seed.live_id)
    assert '<h1 class="fleet-head__title">Versions</h1>' in page
    assert 'data-fleet-mode="detail"' in page
    assert "Update available" in page and "fw-v1.1.0" in page
    assert re.search(r"fw-v1\.0\.0</span>\s*<span class=\"[^\"]*pill[^\"]*\"[^>]*>Running", page)
    # Every release has its own row.
    assert page.count('class="update-item') >= 2
    assert 'action="/devices/' in page or 'action="/update/install"' in page


def test_the_install_form_of_a_release_comes_back_to_the_versions_page(fleet):
    from companion_app_server import http_request, with_csrf
    server, seed, cookie = fleet
    seed_two_releases(server.state_dir)
    status, headers, _body = http_request(
        server.base_url() + "/update/install", method="POST",
        data=with_csrf(cookie, {"version": "fw-v1.1.0", "confirm": "yes"}),
        cookie=cookie, extra_headers={"Origin": server.base_url()})
    assert status == 303
    assert headers["Location"].startswith("/fleet?frame=") and "&view=versions" in headers["Location"]
    assert update_page.INSTALL_ROUTE == "/update/install"
