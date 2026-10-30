"""Settings saved and quick switches flipped under /devices/<id>/ change only
that device's device_config.json; every redirect stays inside the device.
Real app subprocess over a seeded two-device fleet.
"""
import pytest

from companion.test_device_helpers import get, post, snapshot, snapshot_all, start_fleet_app
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
