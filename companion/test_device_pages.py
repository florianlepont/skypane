"""Home, Health and Flights for a selected device: each page shows only that
device's own data, the approved empty and unreachable states, and keeps its
links inside the device. Real app subprocess over a seeded two-device fleet.
"""
import os
import re
from datetime import datetime, timedelta, timezone

import pytest

from companion import auth, ui_nav
from companion.test_device_helpers import get, start_fleet_app
from companion_app_server import http_request
from server import history_db

CALLSIGN_A = "ZZA1111"
CALLSIGN_B = "ZZB2222"
CALLSIGN_LIVE = "ZZL3333"
MARKUP_CALLSIGN = "<b>XSS9</b>"
GALLERY_A = "2026-10-01T10-00-00+00-00.png"
GALLERY_B = "2026-10-01T11-00-00+00-00.png"
GALLERY_LIVE = "2026-10-01T12-00-00+00-00.png"
PNG_BYTES = b"\x89PNG\r\n\x1a\nbody"


def _iso(delta):
    return (datetime.now(timezone.utc) - delta).replace(microsecond=0).isoformat()


def _seed_flight(state_dir, callsign, mv=None, checked_in=None):
    with history_db.open_db(state_dir) as conn:
        history_db.record_runway_event(
            conn, ts=_iso(timedelta(minutes=30)), hex="abc123", callsign=callsign,
            aircraft_type="A320", confirmed_state="departing", corroborated=True,
            route_source="test", airline="Test Air", origin="ORY", destination="NCE",
            tracked_runway="3")
        if checked_in is not None:
            history_db.record_device_health(
                conn, checked_in, battery_mv=mv, fw_version="1.0.0",
                boot_reason="timer", rssi=-61)


def _seed_gallery(state_dir, name):
    gallery = os.path.join(state_dir, "gallery")
    os.makedirs(gallery, exist_ok=True)
    with open(os.path.join(gallery, name), "wb") as fh:
        fh.write(PNG_BYTES)


@pytest.fixture
def two_devices(make_app_server):
    """Device A checked in just now (online); device B's last check-in is
    weeks old (offline); both have their own flight, battery and picture."""
    def seed_extra(fleet):
        _seed_flight(
            fleet.dev_a.state_dir, CALLSIGN_A, mv=3811,
            checked_in=_iso(timedelta(minutes=5)))
        _seed_flight(
            fleet.dev_b.state_dir, CALLSIGN_B, mv=3555,
            checked_in=_iso(timedelta(days=20)))
        _seed_flight(fleet.live.state_dir, CALLSIGN_LIVE)
        _seed_gallery(fleet.dev_a.state_dir, GALLERY_A)
        _seed_gallery(fleet.dev_b.state_dir, GALLERY_B)
        _seed_gallery(fleet.live.state_dir, GALLERY_LIVE)

    return start_fleet_app(make_app_server, seed_extra=seed_extra)


@pytest.fixture
def bare_device(make_app_server):
    """Both devices are provisioned and empty: never checked in, no history,
    no picture, no battery reading."""
    return start_fleet_app(make_app_server)


def _page(app, device, page):
    status, _, body = get(app, "/devices/%s/%s" % (device.id, page))
    assert status == 200
    return body


def _french_page(app, device, page):
    cookie = "%s; %s=fr" % (app.cookie, auth.UI_LANG_COOKIE_NAME)
    status, _, body = http_request(
        app.server.base_url() + "/devices/%s/%s" % (device.id, page), cookie=cookie)
    assert status == 200
    return body.decode("utf-8", "replace")


def _main(page):
    """The page's own content, without the shell (icon sprite, templates)."""
    return re.search(r"<main.*?</main>", page, re.S).group(0)


def _hrefs(page):
    return re.findall(r'(?:href|src|action)="([^"]*)"', page)


# --- Health ---------------------------------------------------------------

def test_health_pages_show_only_their_own_device(two_devices):
    app = two_devices
    health_a = _page(app, app.fleet.dev_a, "health")
    health_b = _page(app, app.fleet.dev_b, "health")
    live = get(app, "/health")[2]
    assert "3811" in health_a and "3555" not in health_a
    assert "3555" in health_b and "3811" not in health_b
    assert "3811" not in live and "3555" not in live


def test_flights_pages_show_only_their_own_device(two_devices):
    app = two_devices
    flights_a = _page(app, app.fleet.dev_a, "flights")
    flights_b = _page(app, app.fleet.dev_b, "flights")
    live = get(app, "/flights")[2]
    assert CALLSIGN_A in flights_a
    assert CALLSIGN_B not in flights_a and CALLSIGN_LIVE not in flights_a
    assert CALLSIGN_B in flights_b
    assert CALLSIGN_A not in flights_b and CALLSIGN_LIVE not in flights_b
    assert CALLSIGN_LIVE in live
    assert CALLSIGN_A not in live and CALLSIGN_B not in live


def test_never_seen_device_gets_the_health_empty_state(bare_device):
    app = bare_device
    page = _page(app, app.fleet.dev_a, "health")
    assert "This frame has not checked in yet" in page
    assert "Health appears after its first wake." in page
    # The page is the empty state alone: no rows, no toast, no dot.
    assert "health-row" not in _main(page) and "toast" not in _main(page)


def test_never_seen_device_has_no_health_nav_dot(make_app_server):
    # Device B checked in once, weeks ago, so its stale check-in raises the
    # dot; device A never checked in and must not. This makes the absence
    # the device's own state and not a page that never draws a dot.
    def seed_extra(fleet):
        _seed_flight(
            fleet.dev_b.state_dir, CALLSIGN_B, mv=3555,
            checked_in=_iso(timedelta(days=20)))

    app = start_fleet_app(make_app_server, seed_extra=seed_extra)
    assert ui_nav.NAV_NOTIFICATION_CLASS in _page(app, app.fleet.dev_b, "flights")
    assert ui_nav.NAV_NOTIFICATION_CLASS not in _page(app, app.fleet.dev_a, "flights")
    assert ui_nav.NAV_NOTIFICATION_CLASS not in _page(app, app.fleet.dev_a, "health")


def test_health_empty_state_in_french(bare_device):
    app = bare_device
    body = _french_page(app, app.fleet.dev_a, "health")
    assert "Ce cadre ne s’est pas encore connecté" in body
    assert "L’état apparaîtra après son premier réveil." in body


def test_online_device_has_no_unreachable_toast(two_devices):
    app = two_devices
    page = _page(app, app.fleet.dev_a, "health")
    assert "No signal since" not in page


def test_silent_device_shows_the_unreachable_toast_and_its_last_data(two_devices):
    app = two_devices
    page = _page(app, app.fleet.dev_b, "health")
    assert "No signal since" in page
    assert "Showing the last known data." in page
    assert "toast--docked" in page and "toast--warning" in page
    assert "data-toast-dismiss" not in _main(page)
    # The last known data is still shown.
    assert "3555" in page


def test_live_frame_health_has_no_device_states(two_devices):
    app = two_devices
    page = get(app, "/health")[2]
    assert "No signal since" not in page
    assert "has not checked in yet" not in page


def test_battery_without_a_reading_shows_the_compact_state(make_app_server):
    def seed_extra(fleet):
        _seed_flight(
            fleet.dev_a.state_dir, CALLSIGN_A, mv=None,
            checked_in=_iso(timedelta(minutes=5)))

    app = start_fleet_app(make_app_server, seed_extra=seed_extra)
    page = _page(app, app.fleet.dev_a, "health")
    assert "No battery reading" in page
    assert "Shown after the first check-in." in page


# --- Flights ----------------------------------------------------------------

def test_device_without_history_gets_the_flights_empty_state(bare_device):
    app = bare_device
    page = _page(app, app.fleet.dev_a, "flights")
    assert "No history for this frame yet" in page
    assert "Flights and checks appear here after the first poll." in page
    assert CALLSIGN_LIVE not in page


def test_flights_empty_state_in_french(bare_device):
    app = bare_device
    page = _french_page(app, app.fleet.dev_a, "flights")
    assert "Pas encore d’historique pour ce cadre" in page


def test_live_frame_flights_keep_their_own_empty_wording(bare_device):
    app = bare_device
    page = get(app, "/flights")[2]
    assert "No history for this frame yet" not in page


def test_flights_links_stay_inside_the_device(two_devices):
    app = two_devices
    prefix = "/devices/%s" % app.fleet.dev_a.id
    page = _page(app, app.fleet.dev_a, "flights")
    gallery = [h for h in _hrefs(page) if "/gallery/" in h]
    assert gallery and all(h.startswith(prefix + "/gallery/") for h in gallery)
    assert not any(h.startswith("/gallery/") for h in _hrefs(page))


def test_markup_in_a_stored_value_is_escaped(make_app_server):
    def seed_extra(fleet):
        _seed_flight(fleet.dev_a.state_dir, MARKUP_CALLSIGN)

    app = start_fleet_app(make_app_server, seed_extra=seed_extra)
    page = _page(app, app.fleet.dev_a, "flights")
    assert MARKUP_CALLSIGN not in page
    assert "&lt;b&gt;XSS9&lt;/b&gt;" in page


def test_corrupt_history_database_does_not_break_the_pages(make_app_server):
    def seed_extra(fleet):
        path = history_db.history_db_path(fleet.dev_a.state_dir)
        with open(path, "wb") as fh:
            fh.write(b"this is not a sqlite database" * 20)

    app = start_fleet_app(make_app_server, seed_extra=seed_extra)
    for page in ("health", "flights", ""):
        status, _, _ = get(app, "/devices/%s/%s" % (app.fleet.dev_a.id, page))
        assert status == 200


# --- Home -------------------------------------------------------------------

def test_home_shows_each_devices_own_picture(two_devices):
    app = two_devices
    home_a = _page(app, app.fleet.dev_a, "")
    home_b = _page(app, app.fleet.dev_b, "")
    live = get(app, "/")[2]
    prefix_a = "/devices/%s" % app.fleet.dev_a.id
    prefix_b = "/devices/%s" % app.fleet.dev_b.id
    assert "%s/gallery/%s" % (prefix_a, GALLERY_A) in home_a
    assert GALLERY_B not in home_a and GALLERY_LIVE not in home_a
    assert "%s/gallery/%s" % (prefix_b, GALLERY_B) in home_b
    assert GALLERY_A not in home_b and GALLERY_LIVE not in home_b
    assert 'src="/gallery/%s"' % GALLERY_LIVE in live
    assert GALLERY_A not in live and GALLERY_B not in live


def test_home_without_a_picture_shows_the_compact_empty_state(bare_device):
    app = bare_device
    page = _page(app, app.fleet.dev_a, "")
    assert "No picture yet" in page
    assert "The first image appears after a poll or the frame’s first wake." in page
    assert "empty-state--compact" in page
    assert "preview-frame__image" not in page


def test_home_empty_state_in_french(bare_device):
    app = bare_device
    page = _french_page(app, app.fleet.dev_a, "")
    assert "Pas encore d’image" in page
    assert "La première image apparaîtra" in page


def test_home_never_falls_back_to_the_live_picture(make_app_server):
    def seed_extra(fleet):
        _seed_gallery(fleet.live.state_dir, GALLERY_LIVE)

    app = start_fleet_app(make_app_server, seed_extra=seed_extra)
    page = _page(app, app.fleet.dev_a, "")
    assert GALLERY_LIVE not in page
    assert "No picture yet" in page


def test_home_links_and_switches_stay_inside_the_device(two_devices):
    app = two_devices
    prefix = "/devices/%s" % app.fleet.dev_b.id
    page = _page(app, app.fleet.dev_b, "")
    links = _hrefs(page)
    for target in ("/flights", "/health", "/display"):
        owned = [h for h in links if h.split("#")[0].endswith(target)]
        assert owned, target
        assert all(h.startswith(prefix + "/") for h in owned), (target, owned)
    switches = [h for h in links if "/quick/" in h]
    assert switches and all(h.startswith(prefix + "/quick/") for h in switches)
    assert 'name="return_to" value="/"' in page


def test_live_home_links_stay_unprefixed(two_devices):
    app = two_devices
    page = get(app, "/")[2]
    links = [h for h in _hrefs(page) if h.endswith(("/flights", "/health"))]
    assert links and all(h.startswith("/") and not h.startswith("/devices/") for h in links)
