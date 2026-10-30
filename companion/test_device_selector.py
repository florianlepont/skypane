"""The device selector: rendered only for several devices, on device-scoped
pages only, working without script, never leaking a secret, and switching
through a validated redirect. Real app subprocess over a seeded fleet.
"""
import re
import urllib.parse

import pytest
from companion_app_server import http_request, login
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


def _options(page):
    root = parse_html(page)
    return root, root.select("select[name='device'] option")


def test_single_device_renders_no_selector_markup(single_app):
    server, cookie = single_app
    for route in SCOPED_PAGES:
        status, _, page = _get(server, cookie, route)
        assert status == 200
        assert "device-selector" not in page
        assert 'name="device"' not in page


@pytest.mark.parametrize("route", SCOPED_PAGES)
def test_selector_on_every_device_scoped_page(fleet_app, route):
    status, _, page = _fleet_get(fleet_app, route)
    assert status == 200
    root = parse_html(page)
    group = root.select_one("div[role='group']")
    assert group is not None
    label = group.select_one("label")
    select = group.select_one("select")
    assert group.attrs["aria-labelledby"] == label.attrs["id"]
    assert label.attrs["for"] == select.attrs["id"]
    assert select.attrs["name"] == "device"
    form = group.select_one("form")
    assert form.attrs["method"] == "get"
    assert "aria-label" not in form.attrs and "aria-labelledby" not in form.attrs
    assert group.select_one("button.device-selector__go") is not None
    # Before the title, inside the main region.
    main = root.select_one("main")
    assert main.select_one("div[role='group']") is not None
    assert page.index("device-selector-label") < page.index("page-title")


@pytest.mark.parametrize("route", ["/update", "/login"])
def test_global_pages_have_no_selector(fleet_app, route):
    _, _, page = _fleet_get(fleet_app, route)
    assert "device-selector" not in page


def test_not_found_page_has_no_selector(fleet_app):
    status, _, page = _fleet_get(fleet_app, "/devices/d_00000000/flights")
    assert status == 404
    assert "device-selector" not in page


def test_options_order_value_label_and_status(fleet_app):
    fleet = fleet_app.fleet
    _, _, page = _fleet_get(fleet_app, "/flights")
    _, options = _options(page)
    values = [option.attrs["value"] for option in options]
    assert values[0] == "live"
    assert set(values[1:]) == {fleet.dev_a.id, fleet.dev_b.id, fleet.landscape.id}
    texts = {option.attrs["value"]: option.text().strip() for option in options}
    assert "—" not in texts["live"]
    assert "—" not in texts[fleet.dev_a.id]
    assert texts[fleet.dev_b.id].endswith("— offline")
    assert texts[fleet.landscape.id].endswith("— not seen yet")
    names = [texts[v].split(" — ")[0] for v in values[1:]]
    assert names == sorted(names)


def test_option_data_href_targets_the_same_page_under_each_device(fleet_app):
    fleet = fleet_app.fleet
    _, _, page = _fleet_get(fleet_app, "/devices/%s/flights" % fleet.dev_a.id)
    _, options = _options(page)
    hrefs = {option.attrs["value"]: option.attrs["data-href"] for option in options}
    assert hrefs["live"] == "/flights"
    assert hrefs[fleet.dev_a.id] == "/devices/%s/flights" % fleet.dev_a.id
    assert hrefs[fleet.dev_b.id] == "/devices/%s/flights" % fleet.dev_b.id
    selected = [o.attrs["value"] for o in options if "selected" in o.attrs]
    assert selected == [fleet.dev_a.id]


def test_live_frame_selected_by_default_and_default_name(fleet_app):
    _, _, page = _fleet_get(fleet_app, "/")
    _, options = _options(page)
    selected = [o for o in options if "selected" in o.attrs]
    assert [o.attrs["value"] for o in selected] == ["live"]
    assert selected[0].text().strip() == "Orly frame"


def test_pill_only_for_selected_non_live_device_with_a_status(fleet_app):
    fleet = fleet_app.fleet
    _, _, live_page = _fleet_get(fleet_app, "/health")
    selector_html = live_page.split("<main", 1)[1].split("page-title")[0]
    assert "banner__pill" not in selector_html
    _, _, ok_page = _fleet_get(fleet_app, "/devices/%s/flights" % fleet.dev_a.id)
    assert parse_html(ok_page).select("form.device-selector .banner__pill") == []
    _, _, off_page = _fleet_get(fleet_app, "/devices/%s/flights" % fleet.dev_b.id)
    root = parse_html(off_page)
    pill = root.select_one("form.device-selector .banner__pill")
    assert pill is not None and pill.text().strip() == "Offline"
    _, _, never_page = _fleet_get(fleet_app, "/devices/%s/flights" % fleet.landscape.id)
    pill = parse_html(never_page).select_one("form.device-selector .banner__pill")
    assert pill is not None and pill.text().strip() == "Not seen yet"


def test_no_mac_token_or_secret_in_any_page(fleet_app):
    fleet = fleet_app.fleet
    _, _, page = _fleet_get(fleet_app, "/devices/%s/flights" % fleet.dev_a.id)
    for device in (fleet.live, fleet.dev_a, fleet.dev_b, fleet.landscape):
        for secret in (device.mac, device.token, device.secret_hex[:16]):
            assert secret not in page


def test_markup_in_a_device_name_is_escaped(fleet_app):
    fleet = fleet_app.fleet
    _, _, selector_page = _fleet_get(fleet_app, "/flights")
    assert MARKUP_NAME not in selector_page
    assert "&lt;script&gt;" in selector_page
    _, _, page = _fleet_get(fleet_app, "/devices/%s/flights" % fleet.dev_b.id)
    title = re.search(r"<title>(.*?)</title>", page, re.S).group(1)
    assert "<script>" not in title and "&lt;script&gt;" in title
    assert "<script>alert" not in page


def test_document_title_names_a_non_live_device_only(fleet_app):
    fleet = fleet_app.fleet
    _, _, live_page = _fleet_get(fleet_app, "/flights")
    assert re.search(r"<title>(.*?)</title>", live_page).group(1) == "Flights - SkyPane"
    _, _, page = _fleet_get(fleet_app, "/devices/%s/flights" % fleet.dev_a.id)
    title = re.search(r"<title>(.*?)</title>", page).group(1)
    assert title == "Flights - sim-1 - SkyPane"


def test_landmark_counts_are_unchanged(fleet_app):
    _, _, page = _fleet_get(fleet_app, "/flights")
    root = parse_html(page)
    nav_names = [
        n.attrs.get("aria-label") for n in root.find_all("nav")
        if n.attrs.get("aria-label")]
    assert nav_names.count("Primary navigation") == 2
    assert len(root.find_all("main")) == 1
    assert len(root.find_all("form", attrs={"aria-label": None})) >= 1


def test_selector_is_in_french_when_the_language_is_french(fleet_app):
    _, _, page = _fleet_get(fleet_app, "/flights", lang="fr")
    root = parse_html(page)
    assert root.select_one("form.device-selector label").text().strip() == "Cadre"
    assert "Afficher le cadre" in page
    assert "pas encore vu" in page and "hors ligne" in page
    assert "Cadre d’Orly" in page


def test_switch_redirects_to_the_same_page_under_the_device(fleet_app):
    fleet = fleet_app.fleet
    status, headers, _ = _fleet_get(fleet_app, "/flights?device=%s" % fleet.dev_a.id)
    assert status == 303
    assert headers["Location"] == "/devices/%s/flights" % fleet.dev_a.id
    status, headers, _ = _fleet_get(fleet_app, "/?device=%s" % fleet.dev_b.id)
    assert (status, headers["Location"]) == (303, "/devices/%s/" % fleet.dev_b.id)


def test_switch_to_live_redirects_to_the_unprefixed_page(fleet_app):
    fleet = fleet_app.fleet
    status, headers, _ = _fleet_get(
        fleet_app, "/devices/%s/health?device=live" % fleet.dev_a.id)
    assert (status, headers["Location"]) == (303, "/health")


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
