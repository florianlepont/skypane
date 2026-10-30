"""Settings saved and quick switches flipped under /devices/<id>/ change only
that device's device_config.json; every redirect stays inside the device.
Real app subprocess over a seeded two-device fleet.
"""
import os
import re

import pytest

from companion import auth
from companion.test_device_helpers import get, post, snapshot, snapshot_all, start_fleet_app
from companion_app_server import http_request
from server import device_config

QUIET = {"quiet_hours_start": "22:15", "quiet_hours_end": "06:45"}


@pytest.fixture
def app(make_app_server):
    app = start_fleet_app(make_app_server)
    # The first request creates fleet.db's SQLite sidecars and initialises
    # the history databases it reads; snapshots are taken after it.
    get(app, "/devices/%s/display" % app.fleet.dev_a.id)
    get(app, "/display")
    return app


def _prefix(device):
    return "/devices/%s" % device.id


def _config(device):
    return device_config.load_device_config(device.state_dir)


def test_settings_post_changes_only_that_devices_config(app):
    fleet = app.fleet
    live, _a, dev_b = snapshot_all(app.server, fleet)
    status, headers, _ = post(app, _prefix(fleet.dev_a) + "/settings", QUIET)
    assert status == 303
    assert headers["Location"].startswith(_prefix(fleet.dev_a) + "/display?flash=")
    config = _config(fleet.dev_a)
    assert (config["quiet_hours_start"], config["quiet_hours_end"]) == ("22:15", "06:45")
    assert snapshot(fleet.dev_b.state_dir) == dev_b
    assert snapshot(app.server.state_dir) == live


def test_live_settings_post_changes_only_the_live_config(app):
    fleet = app.fleet
    _live, dev_a, dev_b = snapshot_all(app.server, fleet)
    status, headers, _ = post(app, "/settings", QUIET)
    assert status == 303
    assert headers["Location"].startswith("/display?flash=")
    assert device_config.load_device_config(app.server.state_dir)["quiet_hours_start"] == "22:15"
    assert snapshot(fleet.dev_a.state_dir) == dev_a
    assert snapshot(fleet.dev_b.state_dir) == dev_b


@pytest.mark.parametrize("route,field,state,expected", [
    ("/quick/quiet-hours", "quiet_hours_enabled", "on", True),
    ("/quick/display", "display_enabled", "off", False),
    ("/quick/led", "led_enabled", "on", True),
])
def test_each_quick_switch_changes_only_that_devices_config(app, route, field, state, expected):
    fleet = app.fleet
    live, _a, dev_b = snapshot_all(app.server, fleet)
    status, headers, _ = post(app, _prefix(fleet.dev_a) + route, {"state": state})
    assert status == 303
    assert headers["Location"].startswith(_prefix(fleet.dev_a) + "/")
    assert _config(fleet.dev_a)[field] is expected
    assert snapshot(fleet.dev_b.state_dir) == dev_b
    assert snapshot(app.server.state_dir) == live


@pytest.mark.parametrize("return_to,expected_path", [
    ("/", "/"),
    ("/display", "/display"),
    ("https://evil.example/", "/display"),
    ("//evil.example", "/display"),
    ("/flights", "/display"),
])
def test_quick_return_to_is_a_whitelisted_route_under_the_same_device(
        app, return_to, expected_path):
    prefix = _prefix(app.fleet.dev_a)
    _status, headers, _ = post(
        app, prefix + "/quick/quiet-hours", {"state": "on", "return_to": return_to})
    assert headers["Location"].startswith(prefix + expected_path + "?flash=")


def test_quick_return_to_accepts_the_same_devices_prefixed_form(app):
    prefix = _prefix(app.fleet.dev_a)
    _status, headers, _ = post(
        app, prefix + "/quick/display", {"state": "on", "return_to": prefix + "/display"})
    assert headers["Location"].startswith(prefix + "/display?flash=")


def test_quick_return_to_with_another_devices_id_falls_back(app):
    fleet = app.fleet
    _status, headers, _ = post(
        app, _prefix(fleet.dev_a) + "/quick/display",
        {"state": "on", "return_to": _prefix(fleet.dev_b) + "/"})
    assert headers["Location"].startswith(_prefix(fleet.dev_a) + "/display?flash=")


def test_live_quick_return_to_never_follows_a_device_prefix(app):
    _status, headers, _ = post(
        app, "/quick/display",
        {"state": "on", "return_to": _prefix(app.fleet.dev_a) + "/display"})
    assert headers["Location"].startswith("/display?flash=")


def test_settings_return_to_foreign_prefix_falls_back_to_the_devices_display(app):
    fleet = app.fleet
    form = dict(QUIET, return_to=_prefix(fleet.dev_b) + "/device")
    _status, headers, _ = post(app, _prefix(fleet.dev_a) + "/settings", form)
    assert headers["Location"].startswith(_prefix(fleet.dev_a) + "/display?flash=")


def test_settings_return_to_the_same_devices_page_is_kept(app):
    prefix = _prefix(app.fleet.dev_a)
    form = dict(QUIET, return_to=prefix + "/device")
    _status, headers, _ = post(app, prefix + "/settings", form)
    assert headers["Location"].startswith(prefix + "/device?flash=")


def test_invalid_input_rerenders_the_device_page_and_writes_nothing(app):
    fleet = app.fleet
    before = snapshot_all(app.server, fleet)
    status, _, page = post(
        app, _prefix(fleet.dev_a) + "/settings",
        {"quiet_hours_start": "25:99", "quiet_hours_end": "06:45"})
    assert status == 200
    assert "25:99" in page or "aria-invalid" in page
    assert snapshot_all(app.server, fleet) == before


def test_settings_post_to_an_unknown_device_is_a_404_and_writes_nothing(app):
    before = snapshot_all(app.server, app.fleet)
    status, _, _ = post(app, "/devices/d_00000000/settings", QUIET)
    assert status == 404
    assert snapshot_all(app.server, app.fleet) == before


def test_quick_switch_on_an_unknown_device_is_a_404_and_writes_nothing(app):
    before = snapshot_all(app.server, app.fleet)
    status, _, _ = post(app, "/devices/d_00000000/quick/display", {"state": "off"})
    assert status == 404
    assert snapshot_all(app.server, app.fleet) == before


def test_a_device_toast_undo_posts_back_under_the_same_device(app):
    prefix = _prefix(app.fleet.dev_a)
    _status, headers, _ = post(app, prefix + "/quick/quiet-hours", {"state": "on"})
    status, _, page = get(app, headers["Location"])
    assert status == 200
    assert 'action="%s/quick/quiet-hours"' % prefix in page


# --- time zone field --------------------------------------------------------

MARTINIQUE = {"timezone": "America/Martinique"}


def _config_bytes(device):
    path = device_config.device_config_path(device.state_dir)
    if not os.path.exists(path):
        return None
    with open(path, "rb") as fh:
        return fh.read()


def _timezone_select(page):
    found = re.search(r'<select id="quiet-hours-timezone".*?</select>', page, re.S)
    assert found, "the time zone select is missing"
    return found.group(0)


def _french(app, path):
    cookie = "%s; %s=fr" % (app.cookie, auth.UI_LANG_COOKIE_NAME)
    status, _, body = http_request(app.server.base_url() + path, cookie=cookie)
    assert status == 200
    return body.decode("utf-8")


def test_timezone_field_markup_and_card_order(app):
    _status, _, page = get(app, _prefix(app.fleet.dev_a) + "/display")
    card = page[page.index('data-dirty-section="Quiet hours"'):]
    card = card[:card.index("</select>")]
    positions = [card.index(marker) for marker in (
        "quiet-preset-row", 'name="quiet_hours_start"', 'name="quiet_hours_end"',
        "quiet-dial", "quiet-dial__readout", 'name="timezone"')]
    assert positions == sorted(positions)
    select = _timezone_select(page)
    assert 'form="settings-form"' in select
    assert re.search(r'<label for="quiet-hours-timezone">Time zone</label>', card)
    assert "Quiet hours follow this time zone." in page
    assert page.count('name="timezone"') == 1


def test_timezone_options_are_curated_with_offsets_and_paris_selected(app):
    _status, _, page = get(app, _prefix(app.fleet.dev_a) + "/display")
    options = re.findall(r'<option value="([^"]+)"( selected)?>([^<]*)</option>', _timezone_select(page))
    assert [key for key, _sel, _text in options] == [
        "Europe/Paris", "America/Martinique", "America/Guadeloupe", "America/Cayenne",
        "Indian/Reunion", "Indian/Mayotte", "America/Miquelon", "Pacific/Tahiti",
        "Pacific/Noumea", "Pacific/Wallis"]
    assert [key for key, selected, _text in options if selected] == ["Europe/Paris"]
    texts = {key: text for key, _sel, text in options}
    assert re.fullmatch(r"Metropolitan France \(Paris\) \(UTC\+[12]\)", texts["Europe/Paris"])
    assert texts["America/Martinique"] == "Martinique (UTC-4)"
    assert texts["Pacific/Noumea"] == "New Caledonia (UTC+11)"


def test_a_valid_timezone_is_saved_for_that_device_only(app):
    fleet = app.fleet
    live, _a, dev_b = snapshot_all(app.server, fleet)
    status, _, _ = post(app, _prefix(fleet.dev_a) + "/settings", dict(QUIET, **MARTINIQUE))
    assert status == 303
    assert _config(fleet.dev_a)["timezone"] == "America/Martinique"
    assert b'"timezone": "America/Martinique"' in _config_bytes(fleet.dev_a)
    assert snapshot(fleet.dev_b.state_dir) == dev_b
    assert snapshot(app.server.state_dir) == live
    _status, _, page = get(app, _prefix(fleet.dev_a) + "/display")
    assert '<option value="America/Martinique" selected>' in _timezone_select(page)
    assert "22:15" in page and "Martinique time" in page


def test_paris_or_omitted_never_adds_the_key(app):
    fleet = app.fleet
    post(app, _prefix(fleet.dev_a) + "/settings", dict(QUIET, timezone="Europe/Paris"))
    assert b"timezone" not in _config_bytes(fleet.dev_a)
    post(app, _prefix(fleet.dev_a) + "/settings", QUIET)
    assert b"timezone" not in _config_bytes(fleet.dev_a)
    post(app, _prefix(fleet.dev_a) + "/settings", MARTINIQUE)
    post(app, _prefix(fleet.dev_a) + "/settings", {"timezone": "Europe/Paris"})
    assert b"timezone" not in _config_bytes(fleet.dev_a)


def test_a_save_that_keeps_paris_leaves_the_live_files_bytes_unchanged(app):
    live_path = device_config.device_config_path(app.server.state_dir)
    status, _, _ = post(app, "/settings", dict(QUIET, timezone="Europe/Paris"))
    assert status == 303
    with open(live_path, "rb") as fh:
        first = fh.read()
    assert b"timezone" not in first
    post(app, "/settings", dict(QUIET, timezone="Europe/Paris"))
    with open(live_path, "rb") as fh:
        assert fh.read() == first


@pytest.mark.parametrize("bad", ["Asia/Tokyo", "../x", "", "Not/AZone", "Europe/Paris/../x"])
def test_an_invalid_timezone_rejects_the_whole_post_atomically(app, bad):
    fleet = app.fleet
    post(app, _prefix(fleet.dev_a) + "/settings", MARTINIQUE)
    before = snapshot_all(app.server, fleet)
    config_before = _config_bytes(fleet.dev_a)
    status, _, page = post(
        app, _prefix(fleet.dev_a) + "/settings", dict(QUIET, timezone=bad))
    assert status == 200
    assert snapshot_all(app.server, fleet) == before
    assert _config_bytes(fleet.dev_a) == config_before
    assert _config(fleet.dev_a)["quiet_hours_start"] != "22:15"
    select = _timezone_select(page)
    assert '<option value="America/Martinique" selected>' in select
    assert 'aria-invalid="true"' in select
    assert 'aria-describedby="quiet-hours-timezone-hint quiet-hours-timezone-error"' in select
    assert re.search(
        r'<p class="field-error text-label" id="quiet-hours-timezone-error" role="alert">'
        r"Pick a time zone from the list\.</p>", page)
    assert "Nothing in this save was applied." in page
    assert 'role="alert"' in page[page.index("toast-region"):]
    assert bad == "" or bad not in page.replace("&lt;", "")


def test_an_unlisted_stored_zone_is_one_extra_last_option_and_can_be_resaved(app):
    fleet = app.fleet
    device_config.save_device_config(fleet.dev_a.state_dir, timezone="Asia/Tokyo")
    _status, _, page = get(app, _prefix(fleet.dev_a) + "/display")
    options = re.findall(r'<option value="([^"]+)"( selected)?>', _timezone_select(page))
    assert options[-1] == ("Asia/Tokyo", " selected")
    assert len(options) == 11
    status, _, _ = post(
        app, _prefix(fleet.dev_a) + "/settings", dict(QUIET, timezone="Asia/Tokyo"))
    assert status == 303
    assert _config(fleet.dev_a)["timezone"] == "Asia/Tokyo"
    assert _config(fleet.dev_a)["quiet_hours_start"] == "22:15"


def test_the_readout_keeps_its_form_for_paris_and_adds_a_zone_clause_otherwise(app):
    fleet = app.fleet
    _status, _, paris = get(app, _prefix(fleet.dev_a) + "/display")
    readout = re.search(r'<p class="time-value quiet-dial__readout".*?</p>', paris, re.S).group(0)
    assert "time</p>" not in readout
    device_config.save_device_config(fleet.dev_a.state_dir, timezone="America/Martinique")
    _status, _, english = get(app, _prefix(fleet.dev_a) + "/display")
    assert re.search(r"</span> · Martinique time</p>", english)
    french = _french(app, _prefix(fleet.dev_a) + "/display")
    assert " · heure de Martinique</p>" in french


def test_every_timezone_string_renders_in_french(app):
    page = _french(app, _prefix(app.fleet.dev_a) + "/display")
    assert "Fuseau horaire" in page
    assert "Les heures calmes suivent ce fuseau horaire." in page
    assert "Métropole (Paris)" in page and "Nouvelle-Calédonie" in page
    cookie = "%s; %s=fr" % (app.cookie, auth.UI_LANG_COOKIE_NAME)
    import urllib.parse
    data = urllib.parse.urlencode(dict(QUIET, timezone="Asia/Nowhere")).encode()
    status, _, body = http_request(
        app.server.base_url() + _prefix(app.fleet.dev_a) + "/settings", method="POST",
        data=data, cookie=cookie)
    text = body.decode("utf-8")
    assert status == 200
    assert "Choisissez un fuseau horaire dans la liste." in text
    assert "Rien n’a été appliqué." in text
