"""Device-aware dispatch: a request under /devices/<id>/ reads that device's
directory only; an unknown id is a 404 page; the live frame's un-prefixed
URLs keep reading the root. Real app subprocess over a seeded two-device fleet.
"""
import os

import pytest

from companion.test_device_helpers import snapshot_all, start_fleet_app
from companion_app_server import http_request
from server import fleet_db, history_db

UNKNOWN_ID = "d_00000000"
CALLSIGN_A = "ZZA1111"
CALLSIGN_B = "ZZB2222"
CALLSIGN_LIVE = "ZZL3333"
FW_A = "9.1.1-devA"
BATTERY_A_TEXT = "3777 mV"


def _seed_history(state_dir, callsign, fw_version=None):
    with history_db.open_db(state_dir) as conn:
        history_db.record_runway_event(
            conn, ts="2026-10-01T10:00:00+00:00", hex="abc123", callsign=callsign,
            aircraft_type="A320", confirmed_state="departing", corroborated=True,
            route_source="test", airline="Test Air", origin="ORY", destination="NCE",
            tracked_runway="3")
        if fw_version:
            history_db.record_device_health(
                conn, "2026-10-01T10:05:00+00:00", battery_mv=3777,
                fw_version=fw_version, boot_reason="timer", rssi=-61)


@pytest.fixture
def fleet_app(make_app_server):
    def seed_extra(fleet):
        _seed_history(fleet.dev_a.state_dir, CALLSIGN_A, FW_A)
        _seed_history(fleet.dev_b.state_dir, CALLSIGN_B)
        _seed_history(fleet.live.state_dir, CALLSIGN_LIVE)
        gallery = os.path.join(fleet.dev_a.state_dir, "gallery")
        os.makedirs(gallery, exist_ok=True)
        with open(os.path.join(gallery, "only-a.png"), "wb") as fh:
            fh.write(b"\x89PNG\r\n\x1a\nonly-a")

    app = start_fleet_app(make_app_server, seed_extra=seed_extra)
    return app.server, app.fleet, app.cookie


def _get(server, path, cookie=None):
    status, headers, body = http_request(server.base_url() + path, cookie=cookie)
    return status, headers, body.decode("utf-8", "replace")


def test_device_flights_page_reads_only_that_devices_history(fleet_app):
    server, fleet, cookie = fleet_app
    status, _, page = _get(server, "/devices/%s/flights" % fleet.dev_a.id, cookie)
    assert status == 200
    assert CALLSIGN_A in page
    assert CALLSIGN_B not in page and CALLSIGN_LIVE not in page


def test_device_health_isolation(fleet_app):
    server, fleet, cookie = fleet_app
    status, _, page_a = _get(server, "/devices/%s/health" % fleet.dev_a.id, cookie)
    assert status == 200
    _, _, page_b = _get(server, "/devices/%s/health" % fleet.dev_b.id, cookie)
    _, _, page_live = _get(server, "/health", cookie)
    assert BATTERY_A_TEXT in page_a
    assert BATTERY_A_TEXT not in page_b and BATTERY_A_TEXT not in page_live


@pytest.mark.parametrize("route", ["/display", "/device", "/airlines", "/", ""])
def test_device_pages_render_for_a_known_device(fleet_app, route):
    server, fleet, cookie = fleet_app
    status, _, _ = _get(server, "/devices/%s%s" % (fleet.dev_a.id, route), cookie)
    assert status == 200


def test_live_frame_pages_still_read_the_root(fleet_app):
    server, _fleet, cookie = fleet_app
    status, _, page = _get(server, "/flights", cookie)
    assert status == 200
    assert CALLSIGN_LIVE in page
    assert CALLSIGN_A not in page and CALLSIGN_B not in page


def test_unknown_device_id_is_a_404_page_not_the_live_frame(fleet_app):
    server, _fleet, cookie = fleet_app
    for route in ("/health", "/flights", "/display", "/"):
        status, _, page = _get(server, "/devices/%s%s" % (UNKNOWN_ID, route), cookie)
        assert status == 404, route
        assert CALLSIGN_LIVE not in page


def test_login_under_a_device_prefix_is_a_404(fleet_app):
    server, fleet, cookie = fleet_app
    status, _, _ = _get(server, "/devices/%s/login" % fleet.dev_a.id, cookie)
    assert status == 404


def test_unauthenticated_device_requests_do_not_reveal_whether_the_id_exists(fleet_app):
    server, fleet, _cookie = fleet_app
    known = _get(server, "/devices/%s/health" % fleet.dev_a.id)
    unknown = _get(server, "/devices/%s/health" % UNKNOWN_ID)
    plain = _get(server, "/health")
    assert known[0] == unknown[0] == plain[0] == 303
    assert known[1].get("Location") == unknown[1].get("Location")
    assert known[1].get("Location", "").startswith("/login")


def test_gallery_file_is_served_only_under_its_own_device(fleet_app):
    server, fleet, cookie = fleet_app
    status, _, body = http_request(
        server.base_url() + "/devices/%s/gallery/only-a.png" % fleet.dev_a.id, cookie=cookie)
    assert status == 200 and body.endswith(b"only-a")
    for other in ("/devices/%s/gallery/only-a.png" % fleet.dev_b.id, "/gallery/only-a.png"):
        status, _, _ = http_request(server.base_url() + other, cookie=cookie)
        assert status == 404, other


def test_device_illustration_membership_uses_the_device_directory(fleet_app):
    server, fleet, cookie = fleet_app
    status, _, _ = http_request(
        server.base_url() + "/devices/%s/illustration/no-such-key.png" % fleet.dev_a.id,
        cookie=cookie)
    assert status == 404


def test_device_theme_and_frame_previews_are_served(fleet_app):
    server, fleet, cookie = fleet_app
    for path in ("/theme-preview/white.png", "/frame-preview/white.png"):
        status, headers, _ = http_request(
            server.base_url() + "/devices/%s%s" % (fleet.dev_a.id, path), cookie=cookie)
        assert status == 200
        assert headers.get("Content-Type") == "image/png"


@pytest.mark.parametrize("legacy,target", [
    ("/settings", "/display"), ("/history", "/flights"), ("/preview", "/flights")])
def test_legacy_redirects_keep_the_device_prefix(fleet_app, legacy, target):
    server, fleet, cookie = fleet_app
    prefix = "/devices/%s" % fleet.dev_a.id
    status, headers, _ = http_request(server.base_url() + prefix + legacy, cookie=cookie)
    assert status == 303
    assert headers.get("Location") == prefix + target
    status, headers, _ = http_request(server.base_url() + legacy, cookie=cookie)
    assert headers.get("Location") == target


def test_history_scope_is_opened_on_the_device_directory(fleet_app):
    server, fleet, cookie = fleet_app
    # The root history.db has only the live callsign; a page that showed
    # dev_a's callsign must have read dev_a's own history.db.
    assert os.path.exists(history_db.history_db_path(fleet.dev_a.state_dir))
    _, _, page = _get(server, "/devices/%s/flights" % fleet.dev_a.id, cookie)
    assert CALLSIGN_A in page and CALLSIGN_LIVE not in page


def test_reading_a_device_page_changes_no_data_file(fleet_app):
    server, fleet, cookie = fleet_app
    _get(server, "/devices/%s/health" % fleet.dev_a.id, cookie)
    before = snapshot_all(server, fleet)
    _get(server, "/devices/%s/health" % fleet.dev_a.id, cookie)
    _get(server, "/devices/%s/display" % fleet.dev_a.id, cookie)
    assert snapshot_all(server, fleet) == before


def test_fleet_status_is_read_from_the_root_for_a_device_page(fleet_app):
    server, fleet, cookie = fleet_app
    path = "/devices/%s/health" % fleet.dev_a.id
    _, _, before = _get(server, path, cookie)
    fleet_db.write_status(server.state_dir, fleet_db.STATUS_FAULT, "fleet fault marker")
    assert not os.path.exists(os.path.join(fleet.dev_a.state_dir, "fleet_status.json"))
    _, _, after = _get(server, path, cookie)
    # The global fleet status lives in the root only; a device page still
    # reflects it.
    assert after != before
