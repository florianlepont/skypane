"""Airline, illustration, colour-rule and calendar actions posted under
/devices/<id>/ change that device's directory only, and every redirect stays
under the device's prefix. Real app subprocess over a seeded two-device
fleet, except the calendar connect cases, which stub the calendar transport
and so run the app in this process.
"""
import io
import os

import pytest
from PIL import Image

import companion.test_companion_app_helpers as cah
from companion import device_scope
from companion.test_device_helpers import (
    SIM_ENV, get, post, snapshot, snapshot_all, start_fleet_app)
from companion_app_server import InProcessAppServer, http_request, login
from skypane_two_device_fleet import seed_two_device_fleet
from server.plane import calendar_rules, colour_rules, manual_resolutions, name_overrides
from server.plane import illustrations
import server.state_store as state_store

PREFIX_REGISTRY = {
    "XQZ": {"count": 3, "first_seen": "t1", "last_seen": "t2", "example_callsign": "XQZ123"}}
CALENDAR_HOST = "device-actions.example"
CALENDAR_URL = "https://%s/feed.ics?token=DEVICEACTIONSTOKEN" % CALENDAR_HOST
RESOLVED_NAME = "Xqz Airways"
RESOLVED_KEY = "xqz-airways"
BUILT_IN_AIRLINE = "Air France"


def _seed_each(fleet):
    for device in (fleet.dev_a, fleet.dev_b, fleet.live):
        state_store.save_poll_state(device.state_dir, {"unresolved_prefixes": PREFIX_REGISTRY})
        manual_resolutions.add_entry(
            device.state_dir, "ABC", "Abc Air", now="2026-01-01T00:00:00+00:00")
        colour_rules.add_rule(device.state_dir, "callsign", "ZZR9999", "grey")
        calendar_rules.save_calendar_url(device.state_dir, CALENDAR_URL)


@pytest.fixture
def app(make_app_server):
    app = start_fleet_app(make_app_server, seed_extra=_seed_each)
    # The first request creates fleet.db's SQLite sidecars; snapshots follow it.
    get(app, "/devices/%s/display" % app.fleet.dev_a.id)
    get(app, "/display")
    return app


def _prefix(device):
    return "/devices/%s" % device.id


def _png_upload():
    buffer = io.BytesIO()
    Image.new("RGBA", (illustrations.ILLUSTRATION_MIN_WIDTH, 400), (200, 30, 30, 128)).save(buffer, format="PNG")
    return cah.encode_multipart(buffer.getvalue())


def _post_upload(app, path):
    body, content_type = _png_upload()
    return http_request(
        app.server.base_url() + path, method="POST", data=body, cookie=app.cookie,
        content_type=content_type)[:2]


def _others_unchanged(app, device, before):
    """`before` is snapshot_all(); every directory except `device`'s own."""
    live, dev_a, dev_b = before
    if device is not app.fleet.live:
        assert snapshot(app.server.state_dir) == live
    if device is not app.fleet.dev_a:
        assert snapshot(app.fleet.dev_a.state_dir) == dev_a
    if device is not app.fleet.dev_b:
        assert snapshot(app.fleet.dev_b.state_dir) == dev_b


# --- illustration -------------------------------------------------------------

def test_illustration_upload_writes_only_that_devices_override(app):
    fleet = app.fleet
    before = snapshot_all(app.server, fleet)
    status, headers = _post_upload(app, _prefix(fleet.dev_a) + "/illustration/air-france.png")
    assert status == 303
    assert headers["Location"].startswith(_prefix(fleet.dev_a) + "/airlines?flash=")
    assert os.path.exists(
        illustrations.override_path_for_key("air-france", fleet.dev_a.state_dir))
    _others_unchanged(app, fleet.dev_a, before)


def test_live_illustration_upload_writes_only_the_root(app):
    fleet = app.fleet
    before = snapshot_all(app.server, fleet)
    status, headers = _post_upload(app, "/illustration/air-france.png")
    assert status == 303
    assert headers["Location"].startswith("/airlines?flash=")
    assert os.path.exists(
        illustrations.override_path_for_key("air-france", app.server.state_dir))
    _others_unchanged(app, fleet.live, before)


def test_illustration_allow_list_is_computed_per_device(app):
    fleet = app.fleet
    manual_resolutions.add_entry(
        fleet.dev_b.state_dir, "XQZ", RESOLVED_NAME, now="2026-01-01T00:00:00+00:00")
    before = snapshot_all(app.server, fleet)
    path = "/illustration/%s.png" % RESOLVED_KEY
    status, _headers = _post_upload(app, _prefix(fleet.dev_a) + path)
    assert status == 404
    assert snapshot_all(app.server, fleet) == before
    status, _headers = _post_upload(app, _prefix(fleet.dev_b) + path)
    assert status == 303


# --- airline resolve, rename, delete ------------------------------------------

def test_manual_resolve_writes_only_that_devices_registry(app):
    fleet = app.fleet
    before = snapshot_all(app.server, fleet)
    status, headers, _ = post(
        app, _prefix(fleet.dev_a) + "/airlines/resolve",
        {"prefix": "XQZ", "airline_name": RESOLVED_NAME})
    assert status == 303
    assert headers["Location"].startswith(_prefix(fleet.dev_a) + "/airlines?")
    assert "XQZ" in manual_resolutions.load_manual_resolutions(fleet.dev_a.state_dir)
    _others_unchanged(app, fleet.dev_a, before)


def test_live_manual_resolve_writes_only_the_root(app):
    fleet = app.fleet
    before = snapshot_all(app.server, fleet)
    status, headers, _ = post(
        app, "/airlines/resolve", {"prefix": "XQZ", "airline_name": RESOLVED_NAME})
    assert status == 303
    assert headers["Location"].startswith("/airlines?")
    assert "XQZ" in manual_resolutions.load_manual_resolutions(app.server.state_dir)
    _others_unchanged(app, fleet.live, before)


def test_resolve_dialog_return_route_keeps_the_device_prefix(app):
    fleet = app.fleet
    status, headers, _ = post(
        app, _prefix(fleet.dev_a) + "/airlines/resolve",
        {"prefix": "NOPE", "airline_name": RESOLVED_NAME, "return": "health"})
    assert status == 303
    assert headers["Location"].startswith(_prefix(fleet.dev_a) + "/")


def test_airline_rename_writes_only_that_devices_overrides(app):
    fleet = app.fleet
    before = snapshot_all(app.server, fleet)
    status, headers, _ = post(
        app, _prefix(fleet.dev_a) + "/airlines/rename",
        {"airline": BUILT_IN_AIRLINE, "airline_name": "Renamed Air"})
    assert status == 303
    assert headers["Location"].startswith(_prefix(fleet.dev_a) + "/airlines?flash=")
    assert "AFR" in name_overrides.load_name_overrides(fleet.dev_a.state_dir)
    _others_unchanged(app, fleet.dev_a, before)


def test_airline_rename_reset_changes_only_that_devices_overrides(app):
    fleet = app.fleet
    for device in (fleet.dev_a, fleet.dev_b):
        name_overrides.set_names(device.state_dir, ["AFR"], "Renamed Air")
    before = snapshot_all(app.server, fleet)
    status, headers, _ = post(
        app, _prefix(fleet.dev_a) + "/airlines/rename/reset", {"airline": BUILT_IN_AIRLINE})
    assert status == 303
    assert headers["Location"].startswith(_prefix(fleet.dev_a) + "/airlines?flash=")
    assert "AFR" not in name_overrides.load_name_overrides(fleet.dev_a.state_dir)
    _others_unchanged(app, fleet.dev_a, before)


def test_manual_resolution_delete_changes_only_that_devices_registry(app):
    fleet = app.fleet
    before = snapshot_all(app.server, fleet)
    status, headers, _ = post(
        app, _prefix(fleet.dev_a) + "/airlines/manual-resolutions/ABC/delete")
    assert status == 303
    assert headers["Location"].startswith(_prefix(fleet.dev_a) + "/airlines")
    assert "ABC" not in manual_resolutions.load_manual_resolutions(fleet.dev_a.state_dir)
    assert "ABC" in manual_resolutions.load_manual_resolutions(fleet.dev_b.state_dir)
    _others_unchanged(app, fleet.dev_a, before)


# --- colour rules ---------------------------------------------------------------

def test_rule_add_writes_only_that_devices_rules(app):
    fleet = app.fleet
    before = snapshot_all(app.server, fleet)
    status, headers, _ = post(
        app, _prefix(fleet.dev_a) + "/settings/rules/add",
        {"rule_kind": "callsign", "rule_key": "ZZN1234", "rule_theme_id": "black"})
    assert status == 303
    assert headers["Location"].startswith(_prefix(fleet.dev_a) + "/display?flash=")
    assert "ZZN1234" in colour_rules.load_colour_rules(fleet.dev_a.state_dir)["callsign"]
    _others_unchanged(app, fleet.dev_a, before)


def test_rule_delete_changes_only_that_devices_rules(app):
    fleet = app.fleet
    before = snapshot_all(app.server, fleet)
    status, headers, _ = post(
        app, _prefix(fleet.dev_a) + "/settings/rules/callsign/ZZR9999/delete")
    assert status == 303
    assert headers["Location"].startswith(_prefix(fleet.dev_a) + "/display")
    assert "ZZR9999" not in colour_rules.load_colour_rules(fleet.dev_a.state_dir)["callsign"]
    assert "ZZR9999" in colour_rules.load_colour_rules(fleet.dev_b.state_dir)["callsign"]
    _others_unchanged(app, fleet.dev_a, before)


@pytest.mark.parametrize("middle", ["callsign", "callsign/", "/ZZR9999", ""])
def test_malformed_rule_delete_path_is_404_under_a_device(app, middle):
    fleet = app.fleet
    before = snapshot_all(app.server, fleet)
    status, _headers, _ = post(app, _prefix(fleet.dev_a) + "/settings/rules/%s/delete" % middle)
    assert status == 404
    assert snapshot_all(app.server, fleet) == before


# --- calendar -------------------------------------------------------------------

def test_calendar_disconnect_clears_only_that_devices_link(app):
    fleet = app.fleet
    before = snapshot_all(app.server, fleet)
    status, headers, _ = post(
        app, _prefix(fleet.dev_a) + "/settings/calendar/disconnect", {"confirm": "yes"})
    assert status == 303
    assert headers["Location"].startswith(_prefix(fleet.dev_a) + "/display?flash=")
    assert not calendar_rules.calendar_is_configured(fleet.dev_a.state_dir)
    assert calendar_rules.calendar_is_configured(fleet.dev_b.state_dir)
    _others_unchanged(app, fleet.dev_a, before)


class _InProcessFleet:
    """An in-process app over a seeded two-device fleet, so the calendar
    transport can be stubbed in the server's own interpreter."""

    def __init__(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SKYPANE_SIM_HARDWARE", SIM_ENV["SKYPANE_SIM_HARDWARE"])
        state_dir = str(tmp_path / "state")
        os.makedirs(state_dir)
        self.fleet = seed_two_device_fleet(state_dir)
        for device in (self.fleet.dev_a, self.fleet.dev_b, self.fleet.live):
            calendar_rules.save_calendar_url(device.state_dir, "https://old.example/x.ics")
        self.server = InProcessAppServer(state_dir)
        self.cookie = login(self.server)

    def connect(self, device, calls):
        body = cah.ics_body([("AFR1234", "ORY", "TLS", 2)])
        transport = cah.make_calendar_transport(body=body, calls=calls)
        path = ("" if device.state_dir == self.server.state_dir else "/devices/%s" % device.id)
        with cah.stubbed_calendar_transport(transport), cah.fake_public_hostname(CALENDAR_HOST):
            status, headers, _ = http_request(
                self.server.base_url() + path + "/settings/calendar/connect", method="POST",
                data=("calendar_url=" + CALENDAR_URL.replace(":", "%3A").replace("/", "%2F")
                      .replace("?", "%3F").replace("=", "%3D")).encode(),
                cookie=self.cookie)
        return status, headers


@pytest.fixture
def in_process_fleet(tmp_path, monkeypatch):
    harness = _InProcessFleet(tmp_path, monkeypatch)
    yield harness
    harness.server.stop()


def test_calendar_connect_writes_only_that_devices_link(in_process_fleet):
    harness = in_process_fleet
    fleet = harness.fleet
    live_before = snapshot(fleet.live.state_dir)
    dev_b_before = snapshot(fleet.dev_b.state_dir)
    calls = []
    status, headers = harness.connect(fleet.dev_a, calls)
    assert status == 303
    assert headers["Location"].startswith("/devices/%s/display?flash=calendar_connect_ok" % fleet.dev_a.id)
    assert calendar_rules.configured_calendar_url(fleet.dev_a.state_dir) == CALENDAR_URL
    assert len(calls) == 1
    assert len(calendar_rules.load_calendar_registry(fleet.dev_a.state_dir)["entries"]) == 1
    assert calendar_rules.configured_calendar_url(fleet.dev_b.state_dir) == "https://old.example/x.ics"
    assert snapshot(fleet.dev_b.state_dir) == dev_b_before
    assert snapshot(fleet.live.state_dir).keys() == live_before.keys()
    assert calendar_rules.configured_calendar_url(fleet.live.state_dir) == "https://old.example/x.ics"


def test_calendar_connect_for_the_live_frame_stays_unprefixed(in_process_fleet):
    harness = in_process_fleet
    fleet = harness.fleet
    dev_a_before = snapshot(fleet.dev_a.state_dir)
    status, headers = harness.connect(fleet.live, [])
    assert status == 303
    assert headers["Location"].startswith("/display?flash=calendar_connect_ok")
    assert calendar_rules.configured_calendar_url(fleet.live.state_dir) == CALENDAR_URL
    assert snapshot(fleet.dev_a.state_dir) == dev_a_before


def test_calendar_connect_ignores_another_devices_poll_lock(in_process_fleet):
    harness = in_process_fleet
    fleet = harness.fleet
    other = device_scope.poll_lock_for(fleet.dev_b.state_dir)
    assert other.acquire(blocking=False)
    try:
        status, headers = harness.connect(fleet.dev_a, [])
    finally:
        other.release()
    assert status == 303
    assert "flash=calendar_connect_ok" in headers["Location"]


def test_calendar_connect_defers_when_its_own_device_is_polling(in_process_fleet):
    harness = in_process_fleet
    fleet = harness.fleet
    own = device_scope.poll_lock_for(fleet.dev_a.state_dir)
    assert own.acquire(blocking=False)
    calls = []
    try:
        status, headers = harness.connect(fleet.dev_a, calls)
    finally:
        own.release()
    assert status == 303
    assert headers["Location"].startswith("/devices/%s/display?flash=" % fleet.dev_a.id)
    assert "calendar_sync_deferred" in headers["Location"]
    assert calls == []
    assert calendar_rules.configured_calendar_url(fleet.dev_a.state_dir) == "https://old.example/x.ics"
