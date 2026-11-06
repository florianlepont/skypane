"""The frame switcher: rendered only for several frames, on device-scoped
pages only, working without script, never leaking a secret, and switching
through a validated redirect. Real app subprocess over a seeded fleet.
"""
import re
import urllib.parse

import pytest
from companion_app_server import http_request, login, session_cookie_for_state_dir
from skypane_two_device_fleet import OWNER_EMAIL
from companion_markup import parse_html
from skypane_live_state import seed_live_like_state

from companion.test_device_helpers import SIM_ENV, start_fleet_app
from companion import auth
from server import fleet_db, fleet_migrate, history_db

MARKUP_NAME = '<script>alert("x")</script> & Co'
FRESH_TS_AGE_S = 60
STALE_TS = "2026-01-01T00:00:00+00:00"
SCOPED_PAGES = ("/", "/display", "/flights", "/airlines", "/health", "/device")


def _seed(fleet):
    """dev_a checked in just now, dev_b long ago, the landscape device never."""
    with history_db.open_db(fleet.dev_a.state_dir) as conn:
        history_db.record_device_health(
            conn, history_db.utc_now_iso(), battery_mv=3900, fw_version="1.0.0",
            boot_reason="timer", rssi=-60)
    with history_db.open_db(fleet.dev_b.state_dir) as conn:
        history_db.record_device_health(
            conn, STALE_TS, battery_mv=3800, fw_version="1.0.0",
            boot_reason="timer", rssi=-60)
    conn = fleet_db.connect(fleet.live.state_dir)
    try:
        with fleet_db.transaction(conn):
            conn.execute(
                "UPDATE devices SET name = ? WHERE id = ?", (MARKUP_NAME, fleet.dev_b.id))
    finally:
        conn.close()


@pytest.fixture(scope="module")
def fleet_app(module_app_server_factory):
    app = start_fleet_app(module_app_server_factory, seed_extra=_seed)
    # The fleet's owner is an administrator who owns every frame, so the
    # switcher lists all of them.
    app.cookie = session_cookie_for_state_dir(app.server.state_dir, OWNER_EMAIL)
    return app


@pytest.fixture(scope="module")
def single_app(module_app_server_factory):
    def seed(state_dir):
        seed_live_like_state(state_dir)
        fleet_migrate.migrate(state_dir, "owner@example.com", dry_run=False)

    server = module_app_server_factory(seed=seed, env_overrides=SIM_ENV)
    return server, login(server)


def _get(app_server, cookie, path, lang=None):
    headers = None
    if lang:
        headers = {"Cookie": "%s; %s=%s" % (cookie, auth.UI_LANG_COOKIE_NAME, lang)}
    status, response_headers, body = http_request(
        app_server.base_url() + path, cookie=None if headers else cookie,
        extra_headers=headers)
    return status, response_headers, body.decode("utf-8", "replace")


def _fleet_get(app, path, lang=None):
    return _get(app.server, app.cookie, path, lang)


def _live_path(app, route):
    """`route` under the live frame's own prefix: it has a fleet row, so an
    administrator addresses it by id like every other frame."""
    return "/devices/%s%s" % (app.fleet.live.id, route)


def _live_get(app, route, lang=None):
    return _fleet_get(app, _live_path(app, route), lang)


def _switcher(page):
    root = parse_html(page)
    return root, root.select_one("ul.frame-menu__list")


def _rows(page):
    root, _switcher_node = _switcher(page)
    return root, [
        a for a in root.select("ul.frame-menu__list a.frame-row")
        if "frame-row--add" not in a.attrs.get("class", "")]


def test_single_device_lists_one_frame_and_the_add_row(single_app):
    server, cookie = single_app
    # The signed-in administrator owns no frame, so the un-prefixed page
    # moves to the account page; the frame is reached by its own id.
    status, headers, _ = _get(server, cookie, "/flights")
    assert (status, headers["Location"]) == (303, "/account")
    conn = fleet_db.connect_readonly(server.state_dir)
    try:
        prefix = "/devices/%s" % fleet_db.list_devices(conn)[0]["id"]
    finally:
        conn.close()
    for route in SCOPED_PAGES:
        status, _, page = _get(server, cookie, prefix + route)
        assert status == 200
        _root, rows = _rows(page)
        assert len(rows) == 1
        assert page.count("frame-row--add") == 1
        assert 'name="device"' not in page


@pytest.mark.parametrize("route", SCOPED_PAGES)
def test_switcher_on_every_device_scoped_page(fleet_app, route):
    status, _, page = _live_get(fleet_app, route)
    assert status == 200
    root, switcher = _switcher(page)
    assert switcher is not None
    assert switcher.attrs["aria-label"] == "Your frames"
    assert not switcher.select("form") and not switcher.select("select")
    assert not root.select("dialog.frame-sheet")
    # In the top bar, before the content and its title.
    assert root.select_one("header.site-header ul.frame-menu__list") is not None
    assert not root.select("main ul.frame-menu__list")
    assert page.index("frame-menu__list") < page.index("page-title")


@pytest.mark.parametrize("route", ["/update", "/login"])
def test_global_pages_have_no_switcher(fleet_app, route):
    _, _, page = _fleet_get(fleet_app, route)
    assert "frame-menu" not in page and "frame-row" not in page


def test_not_found_page_has_no_switcher(fleet_app):
    status, _, page = _fleet_get(fleet_app, "/devices/d_00000000/flights")
    assert status == 404
    assert "frame-menu" not in page and "frame-row" not in page


def test_rows_order_and_status_words(fleet_app):
    fleet = fleet_app.fleet
    _, _, page = _live_get(fleet_app, "/flights")
    _, rows = _rows(page)
    hrefs = [row.attrs["href"] for row in rows]
    assert hrefs[0] == "/devices/%s/flights" % fleet.live.id
    assert set(hrefs[1:]) == {
        "/devices/%s/flights" % d.id for d in (fleet.dev_a, fleet.dev_b, fleet.landscape)}
    words = {
        row.attrs["href"]: row.select_one("span[role='img']").attrs["aria-label"]
        for row in rows}
    assert words["/devices/%s/flights" % fleet.dev_b.id] == "No contact"
    assert words["/devices/%s/flights" % fleet.landscape.id] == "Not seen yet"
    assert words["/devices/%s/flights" % fleet.dev_a.id] in ("Up to date", "Low battery")
    names = [row.select_one(".frame-row__name").text().strip() for row in rows[1:]]
    assert names == sorted(names)


def test_row_links_keep_the_page_and_mark_the_current_frame(fleet_app):
    fleet = fleet_app.fleet
    _, _, page = _fleet_get(fleet_app, "/devices/%s/flights" % fleet.dev_a.id)
    _, rows = _rows(page)
    hrefs = {row.attrs["href"] for row in rows}
    assert "/devices/%s/flights" % fleet.live.id in hrefs
    assert "/devices/%s/flights" % fleet.dev_b.id in hrefs
    current = [row.attrs["href"] for row in rows if row.attrs.get("aria-current") == "true"]
    assert current == ["/devices/%s/flights" % fleet.dev_a.id]


def test_live_frame_is_current_by_default_with_its_default_name(fleet_app):
    _, _, page = _live_get(fleet_app, "/")
    _, rows = _rows(page)
    current = [row for row in rows if row.attrs.get("aria-current") == "true"]
    assert [row.attrs["href"] for row in current] == [_live_path(fleet_app, "/")]
    assert current[0].select_one(".frame-row__name").text().strip() == "Orly frame"


def test_add_tile_for_an_administrator_leads_to_the_pairing_flow(fleet_app):
    _, _, page = _live_get(fleet_app, "/health")
    _, switcher = _switcher(page)
    add = switcher.select("a.frame-row--add")
    assert [(a.attrs["href"], a.text().strip()[-12:]) for a in add] == [
        ("/fleet?pair=1", "+Add a frame")]
    assert "All frames" not in page


def test_each_tile_reads_a_last_seen_word_from_the_shared_status(fleet_app):
    fleet = fleet_app.fleet
    _, _, page = _live_get(fleet_app, "/flights")
    _, rows = _rows(page)
    seen = {
        row.attrs["href"]: row.select_one(".frame-row__seen").text().strip()
        for row in rows}
    assert seen["/devices/%s/flights" % fleet.landscape.id] == "Not seen yet"
    assert seen["/devices/%s/flights" % fleet.dev_a.id].startswith("Seen ")


def test_no_mac_token_or_secret_in_any_page(fleet_app):
    fleet = fleet_app.fleet
    _, _, page = _fleet_get(fleet_app, "/devices/%s/flights" % fleet.dev_a.id)
    for device in (fleet.live, fleet.dev_a, fleet.dev_b, fleet.landscape):
        for secret in (device.mac, device.token, device.secret_hex[:16]):
            assert secret not in page


def test_markup_in_a_device_name_is_escaped(fleet_app):
    fleet = fleet_app.fleet
    _, _, switcher_page = _live_get(fleet_app, "/flights")
    assert MARKUP_NAME not in switcher_page
    assert "&lt;script&gt;" in switcher_page
    _, _, page = _fleet_get(fleet_app, "/devices/%s/flights" % fleet.dev_b.id)
    title = re.search(r"<title>(.*?)</title>", page, re.S).group(1)
    assert "<script>" not in title and "&lt;script&gt;" in title
    assert "<script>alert" not in page


def test_document_title_names_the_frame_on_every_device_page(fleet_app):
    fleet = fleet_app.fleet
    _, _, live_page = _live_get(fleet_app, "/flights")
    assert re.search(r"<title>(.*?)</title>", live_page).group(1) == (
        "Flight history - Orly frame - SkyPane")
    _, _, page = _fleet_get(fleet_app, "/devices/%s/flights" % fleet.dev_a.id)
    title = re.search(r"<title>(.*?)</title>", page).group(1)
    assert title == "Flight history - sim-1 - SkyPane"


def test_landmark_counts_are_unchanged(fleet_app):
    _, _, page = _live_get(fleet_app, "/flights")
    root = parse_html(page)
    nav_names = [
        n.attrs.get("aria-label") for n in root.find_all("nav")
        if n.attrs.get("aria-label")]
    assert nav_names.count("Primary navigation") == 2
    assert len(root.find_all("main")) == 1


def test_switcher_is_in_french_when_the_language_is_french(fleet_app):
    _, _, page = _live_get(fleet_app, "/flights", lang="fr")
    _, switcher = _switcher(page)
    assert switcher.attrs["aria-label"] == "Vos cadres"
    assert "Ajouter un cadre" in page
    assert "Tous les cadres" not in page
    assert "Sans contact" in page and "Pas encore vu" in page
    assert "Cadre d’Orly" in page


def test_switch_redirects_to_the_same_page_under_the_device(fleet_app):
    fleet = fleet_app.fleet
    status, headers, _ = _fleet_get(fleet_app, "/flights?device=%s" % fleet.dev_a.id)
    assert status == 303
    assert headers["Location"] == "/devices/%s/flights" % fleet.dev_a.id
    status, headers, _ = _fleet_get(fleet_app, "/?device=%s" % fleet.dev_b.id)
    assert (status, headers["Location"]) == (303, "/devices/%s/" % fleet.dev_b.id)


def test_switch_to_live_redirects_to_the_live_frame_prefix(fleet_app):
    fleet = fleet_app.fleet
    status, headers, _ = _fleet_get(
        fleet_app, "/devices/%s/health?device=live" % fleet.dev_a.id)
    assert (status, headers["Location"]) == (
        303, "/devices/%s/health" % fleet.live.id)


def test_switch_keeps_other_query_parameters(fleet_app):
    fleet = fleet_app.fleet
    status, headers, _ = _fleet_get(
        fleet_app, "/flights?device=%s&q=a%%26b" % fleet.dev_a.id)
    assert status == 303
    assert headers["Location"] == "/devices/%s/flights?q=a%%26b" % fleet.dev_a.id


@pytest.mark.parametrize("value", [
    "d_00000000", "nope", "", "//evil.example", "https://evil.example/x",
    "%2F%2Fevil.example", "d_zzzzzzzz", "d_0123456789", "../x", "live%0d%0aX: y",
    "LIVE"])
def test_switch_with_an_unknown_or_malformed_value_is_a_404(fleet_app, value):
    status, headers, page = _fleet_get(
        fleet_app, "/flights?device=" + urllib.parse.quote(value, safe="%"))
    assert status == 404
    assert "Location" not in headers


def test_switch_is_behind_the_session_gate(fleet_app):
    fleet = fleet_app.fleet
    for value in (fleet.dev_a.id, "d_00000000"):
        status, headers, _ = http_request(
            fleet_app.server.base_url() + "/flights?device=" + value)
        assert status == 303
        assert headers["Location"].startswith("/login")


def test_device_parameter_on_a_global_page_is_ignored(fleet_app):
    status, headers, _ = _fleet_get(fleet_app, "/update?device=d_00000000")
    assert status == 200 and "Location" not in headers
