"""The State section of a frame's page (three tiles; all but Connection carry a Details
link) and the two pages the tiles open: Battery (the level, trend and readings) and Versions (the
installed version, the update and every release), served by the real app and read as markup."""
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
    section = re.search(r'<ul class="fleet-tiles[^"]*">.*?</ul>', page, re.S).group(0)
    found = []
    for tile in re.findall(r'<(?:a|div) class="fleet-tile(?: [^"]*)?".*?</(?:a|div)>', section, re.S):
        def part(name):
            m = re.search(r'<span class="fleet-tile__%s">(.*?)</span>(?=<)' % name, tile, re.S)
            return html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else ""
        found.append((
            part("label"), part("value"), part("meta"),
            html.unescape(re.match(r'<a [^>]*href="([^"]+)"', tile).group(1)) if tile.startswith("<a ") else "",
            re.search(r'data-state="(\w+)"', tile).group(1)))
    return found


LABELS = {
    "en": ["Connection", "Battery", "Firmware"],
    "fr": ["Connexion", "Batterie", "Micrologiciel"]}
DETAILS = {"en": "Details", "fr": "Détails"}


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_state_section_is_three_tiles_two_with_a_details_link(fleet, lang):
    server, seed, cookie = fleet
    _seed_readings(server.state_dir)
    seed_two_releases(server.state_dir)
    page = _page(server, cookie, "/fleet?frame=" + seed.live_id, lang)
    tiles = _tiles(page)
    assert [t[0] for t in tiles] == LABELS[lang]
    base = "/fleet?frame=%s&view=" % seed.live_id
    # Connection holds its own story; flight data is platform data, on the System view only.
    assert [t[3] for t in tiles] == ["", base + "battery", base + "versions"]
    assert "system-topic-flight-data" not in page
    assert page.count('<span class="fleet-tile__more">%s' % DETAILS[lang]) == 2
    battery = tiles[1]
    assert re.match(r"\d+\s?% · \d+\s?mV", battery[1]), battery
    assert tiles[2][1] == "fw-v1.0.0" and tiles[2][2]
    # The battery tile draws the curve; the others carry no drawing.
    assert page.count("fleet-tile__spark") == 1
    # The three statuses of the old State block are not rows any more.
    assert "health-row" not in page


def test_a_frame_that_never_checked_in_still_has_its_three_tiles(fleet):
    server, seed, cookie = fleet
    page = _page(server, cookie, "/fleet?frame=" + seed.owned_id)
    tiles = _tiles(page)
    assert [t[0] for t in tiles] == LABELS["en"]
    assert tiles[0][1] == "No check-in yet"
    assert "fleet-tile__spark" not in page
    assert [t[3] for t in tiles][1] == "/fleet?frame=%s&view=battery" % seed.owned_id


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
    for tile in re.findall(r'<(?:a|div) class="fleet-tile" data-state="(\w+)"', page):
        assert tile in ("ok", "warn", "error", "off")
    assert re.search(r'fleet-tile__icon">.*?<span class="visually-hidden">Healthy</span>', page, re.S)


def test_the_overview_has_one_h1_and_no_list_column_change(fleet):
    server, seed, cookie = fleet
    page = _page(server, cookie, "/fleet?frame=" + seed.live_id)
    assert len(re.findall(r"<h1[ >]", page)) == 1


# ---- Battery --------------------------------------------------------------

def _rename(state_dir, device_id, name):
    conn = fleet_db.connect(state_dir)
    try:
        fleet_db.rename_device(conn, device_id, name)
    finally:
        conn.close()


def test_the_battery_page_holds_only_the_battery(fleet):
    server, seed, cookie = fleet
    _seed_readings(server.state_dir)
    page = _page(server, cookie, "/fleet?frame=%s&view=battery" % seed.live_id)
    assert 'data-fleet-mode="detail"' in page
    assert len(re.findall(r"<h1[ >]", page)) == 1 and '<h1 class="fleet-head__title">Battery</h1>' in page
    assert re.search(r'<div class="health-row" [^>]*id="health-row-battery"', page)
    # Nothing of the retired Health page: no connection row, no platform rows, no banner.
    for row in ("connection", "flight-data", "sources", "identification", "backup"):
        assert 'id="health-row-%s"' % row not in page, row
    assert "Server &amp; data" not in page and "Visible to administrators" not in page
    assert "health-anomaly" not in page
    # The battery row keeps its readout, chart and readings table.
    assert 'class="battery-readout' in page and "battery-unit" in page and "battery-readings" in page and "readings-disclosure" not in page
    # The list column is not part of this page, and the overview tiles are not either.
    assert "fleet-list" not in page and "fleet-tile" not in page


def test_the_battery_page_of_a_frame_that_never_checked_in_says_so(fleet):
    server, seed, cookie = fleet
    page = _page(server, cookie, "/fleet?frame=%s&view=battery" % seed.owned_id)
    assert "This frame has not checked in yet" in page
    assert 'id="health-row-' not in page


def test_the_battery_page_has_a_way_back_to_the_frame_and_escapes_its_name(fleet):
    server, seed, cookie = fleet
    hostile = '<img src=x onerror=alert(1)>"&'
    _rename(server.state_dir, seed.owned_id, hostile)
    for view in ("battery", "versions"):
        page = _page(server, cookie, "/fleet?frame=%s&view=%s" % (seed.owned_id, view))
        assert "<img src=x" not in page
        back = re.search(r'<a class="fleet-back" href="([^"]+)">.*?<span>(.*?)</span></a>', page, re.S)
        assert back.group(1) == "/fleet?frame=%s" % seed.owned_id
        assert html.unescape(back.group(2)) == "Back to " + hostile


@pytest.mark.parametrize("lang,back,title", [("en", "Back to Kitchen", "Battery"), ("fr", "Retour à Kitchen", "Batterie")])
def test_the_back_link_and_title_are_translated(fleet, lang, back, title):
    server, seed, cookie = fleet
    page = _page(server, cookie, "/fleet?frame=%s&view=battery" % seed.owned_id, lang)
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


# ---- A low battery level is a warning everywhere ---------------------------

def _seed_low_readings(state_dir):
    from companion import battery
    low = battery.low_display_mv()
    now = datetime.datetime.now(datetime.timezone.utc)
    with history_db.open_db(state_dir) as conn:
        for i in range(12):
            stamp = now - datetime.timedelta(hours=6 * (11 - i), seconds=20)
            history_db.record_device_health(
                conn, stamp.isoformat(timespec="seconds"), battery_mv=low - 40 - 2 * i + 22,
                fw_version="1.0.0", boot_reason="wake", rssi="-60")
    device_config.save_device_config(state_dir, wake_interval_s=600)


def _normal_and_low_pages(fleet, lang="en"):
    server, seed, cookie = fleet
    _seed_readings(server.state_dir)
    normal = _page(server, cookie, "/fleet?frame=" + seed.live_id, lang)
    _seed_low_readings(server.state_dir)
    return normal, _page(server, cookie, "/fleet?frame=" + seed.live_id, lang), server, seed, cookie


@pytest.mark.parametrize("lang,words", [("en", "Level is low"), ("fr", "Le niveau est bas")])
def test_a_low_level_turns_the_overview_battery_tile_to_warning_in_words(fleet, lang, words):
    normal, low, _server, _seed, _cookie = _normal_and_low_pages(fleet, lang)
    assert _tiles(normal)[1][4] == "ok"
    battery = _tiles(low)[1]
    assert battery[4] == "warn" and battery[2] == words, battery
    assert _tiles(low)[0][4] == "ok", "only the battery tile changes"


_NAV_DOT = re.compile(r'class="dot (dot--\w+) nav-notification"')
_BANNER = re.compile(r'class="sys-banner health-anomaly" data-severity="(\w+)"')


def test_a_low_level_lights_the_nav_dot_and_the_warnings_banner(fleet):
    normal, low, server, seed, cookie = _normal_and_low_pages(fleet)
    assert _NAV_DOT.search(normal) is None and _BANNER.search(normal) is None
    assert _NAV_DOT.search(low).group(1) == "dot--warn"
    health = _page(server, cookie, "/fleet?view=system")
    assert _BANNER.search(health).group(1) == "warn"
    assert "Battery level is low" in html.unescape(health)
    assert "Battery dropped abnormally" not in health


def test_a_low_level_is_a_warning_in_french_in_the_banner_too(fleet):
    server, seed, cookie = fleet
    _seed_low_readings(server.state_dir)
    health = _page(server, cookie, "/fleet?view=system", "fr")
    assert "Niveau de batterie bas" in html.unescape(health)


def test_the_low_mark_is_the_cards_own_mark(fleet):
    """a reading just above the mark leaves the tile, the banner and the nav dot at ok; one
    just below it turns all three: one threshold, not two"""
    from companion import battery
    server, seed, cookie = fleet
    now = datetime.datetime.now(datetime.timezone.utc)
    for offset, state in ((+1, "ok"), (-1, "warn")):
        with history_db.open_db(server.state_dir) as conn:
            conn.execute("DELETE FROM device_health")
            for i in range(3):
                history_db.record_device_health(
                    conn, (now - datetime.timedelta(minutes=3 - i)).isoformat(timespec="seconds"),
                    battery_mv=battery.low_display_mv() + offset, fw_version="1.0.0",
                    boot_reason="wake", rssi="-60")
        device_config.save_device_config(server.state_dir, wake_interval_s=600)
        page = _page(server, cookie, "/fleet?frame=" + seed.live_id)
        assert _tiles(page)[1][4] == state
        assert (_NAV_DOT.search(page) is not None) == (state == "warn")


# ---- Low level plus an abnormal drop; the error page has no device curve ---

def _seed_low_and_dropping_readings(state_dir):
    from companion import battery, health_signals
    low = battery.low_display_mv()
    now = datetime.datetime.now(datetime.timezone.utc)
    with history_db.open_db(state_dir) as conn:
        for i in range(12):
            stamp = now - datetime.timedelta(hours=6 * (11 - i), seconds=20)
            mv = low - 40 - 2 * i + 22
            if i < 6:
                mv += health_signals.BATTERY_DROP_WARN_MV + 50
            history_db.record_device_health(
                conn, stamp.isoformat(timespec="seconds"), battery_mv=mv,
                fw_version="1.0.0", boot_reason="wake", rssi="-60")
    device_config.save_device_config(state_dir, wake_interval_s=600)


@pytest.mark.parametrize("lang,low,dropped,words", [
    ("en", "Battery level is low", "Battery dropped abnormally", "Level is low"),
    ("fr", "Niveau de batterie bas", "Baisse anormale de batterie", "Le niveau est bas")])
def test_the_battery_page_says_a_low_level_in_words_and_the_system_banner_names_it(
        fleet, lang, low, dropped, words):
    server, seed, cookie = fleet
    _seed_low_and_dropping_readings(server.state_dir)
    battery = html.unescape(_page(server, cookie, "/fleet?frame=%s&view=battery" % seed.live_id, lang))
    assert words in battery and "health-anomaly" not in battery
    overview = html.unescape(_page(server, cookie, "/fleet?view=system", lang))
    assert low in overview and dropped not in overview


def _not_found(server, cookie):
    status, _headers, body = fx.get(server, cookie, "/no-such-page-here")
    assert status == 404
    return body if isinstance(body, str) else body.decode("utf-8")


def test_the_error_page_nav_dot_never_reads_a_guessed_battery_curve(fleet):
    server, seed, cookie = fleet
    _seed_low_readings(server.state_dir)
    assert _NAV_DOT.search(_page(server, cookie, "/fleet?frame=" + seed.live_id)).group(1) == "dot--warn"
    assert _NAV_DOT.search(_not_found(server, cookie)) is None


def test_the_error_page_nav_dot_keeps_the_other_signals(fleet):
    server, seed, cookie = fleet
    stale = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=4000)
    with history_db.open_db(server.state_dir) as conn:
        history_db.record_device_health(
            conn, stale.isoformat(timespec="seconds"), battery_mv=4000,
            fw_version="1.0.0", boot_reason="wake", rssi="-60")
    device_config.save_device_config(server.state_dir, wake_interval_s=600)
    assert _NAV_DOT.search(_not_found(server, cookie)) is not None
