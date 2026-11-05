"""The Display page holds none of the Location and detection controls (no
card, no location picker, no time zone select), the Location and detection
page carries them, the Device page and the removed Runway card stay absent,
saving Display never changes the stored place, zone or detection, and the
history pages tolerate the newer runway ids, over a real in-process server.
"""
import html
import json
import os
import re

import pytest

from access_matrix_support import (
    ADMIN_EMAIL, OTHER_EMAIL, OWNER_EMAIL, seed_matrix_fleet)
from companion import device_scope
from companion_app_server import (
    InProcessAppServer, http_request, session_cookie_for_state_dir, with_csrf)
from server import device_config, fleet_db, history_db

PARIS = "Europe/Paris"
HOSTILE_ID = '"><script>alert(1)</script>'


class Rig:
    def __init__(self, state_dir, server, fleet, cookies, state_dirs):
        self.state_dir = state_dir
        self.server = server
        self.fleet = fleet
        self.cookies = cookies
        self.state_dirs = state_dirs

    def owner_dir(self):
        return self.state_dirs[self.fleet.owner_device]

    def scope(self):
        return "/devices/%s" % self.fleet.owner_device

    def get(self, who, path, lang=None):
        headers = {"Accept-Language": lang} if lang else None
        status, _response, body = http_request(
            self.server.url(path), cookie=self.cookies[who], extra_headers=headers)
        return status, body.decode("utf-8", "replace")

    def post(self, who, path, form):
        data = with_csrf(self.cookies[who], form)
        status, response, body = http_request(
            self.server.url(path), method="POST", data=data, cookie=self.cookies[who],
            extra_headers={"Origin": self.server.base_url()})
        return status, response, body.decode("utf-8", "replace")

    def config(self, state_dir):
        path = device_config.device_config_path(state_dir)
        if not os.path.exists(path):
            return {}
        with open(path, "rb") as handle:
            return json.loads(handle.read() or b"{}")

    def add_location(self, name, lat, lon):
        conn = fleet_db.connect(self.state_dir)
        try:
            return fleet_db.add_location(
                conn, name, lat, lon, PARIS, owner_user_id=self.fleet.owner_id)
        finally:
            conn.close()


@pytest.fixture
def rig(tmp_path):
    state_dir = str(tmp_path / "state")
    server = InProcessAppServer(state_dir)
    fleet = seed_matrix_fleet(state_dir)
    state_dirs = {d.id: d.state_dir for d in device_scope.load_devices(state_dir)}
    cookies = {
        "owner": session_cookie_for_state_dir(state_dir, OWNER_EMAIL, "user"),
        "other": session_cookie_for_state_dir(state_dir, OTHER_EMAIL, "user"),
        "admin": session_cookie_for_state_dir(state_dir, ADMIN_EMAIL, "admin"),
    }
    for state in state_dirs.values():
        os.makedirs(state, exist_ok=True)
    yield Rig(state_dir, server, fleet, cookies, state_dirs)
    server.stop()


def _text(markup):
    stripped = re.sub(r"<(script|style)\b.*?</\1>", " ", markup, flags=re.S)
    return html.unescape(re.sub(r"<[^>]+>", " ", stripped))


def _dirty_sections(markup):
    return re.findall(r'data-dirty-section="([^"]*)"', markup)


def _save_lfpg(rig):
    device_config.save_device_config(
        rig.owner_dir(), detection={"mode": "runway", "airport": "LFPG", "runway": "08L/26R"})


def _position_row(rig):
    conn = fleet_db.connect(rig.state_dir)
    try:
        row = conn.execute(
            "SELECT d.location_id, l.latitude, l.longitude FROM devices d "
            "LEFT JOIN locations l ON l.id = d.location_id WHERE d.id = ?",
            (rig.fleet.owner_device,)).fetchone()
        return tuple(row)
    finally:
        conn.close()


def _save_position(rig, radius="9"):
    home = rig.add_location("Home", 48.8566, 2.3522)
    status, _r, _b = rig.post("owner", rig.scope() + "/detection", {
        "action": "save_detection", "mode": "position",
        "location_id": str(home), "radius_km": radius})
    assert status == 303
    return home


# --- Display ----------------------------------------------------------------


def _assert_display_has_no_place_controls(page):
    assert "detection-card" not in page
    assert 'id="location-detection' not in page
    assert "Location and detection</h2>" not in page
    assert not re.search(r"<select\b[^>]*name=\"(location_id|timezone)\"", page)
    assert 'id="location-picker"' not in page and 'id="quiet-hours-timezone"' not in page
    assert "Change airport, runway or position" not in page
    assert not {"Location", "Time zone"} & set(_dirty_sections(page))


@pytest.mark.parametrize("who", ["owner", "admin"])
def test_display_serves_none_of_the_moved_controls(rig, who):
    _save_lfpg(rig)
    rig.add_location("Home", 48.8566, 2.3522)
    status, page = rig.get(who, rig.scope() + "/display")
    assert status == 200
    _assert_display_has_no_place_controls(page)
    assert "Charles de Gaulle" not in _text(page)
    assert 'id="quiet-hours-group-heading"' not in page
    assert 'name="quiet_hours_start"' not in page


def test_display_serves_none_of_the_moved_controls_in_french(rig):
    _save_position(rig)
    status, page = rig.get("owner", rig.scope() + "/display", lang="fr")
    assert status == 200
    _assert_display_has_no_place_controls(page)
    assert "Lieu et détection</h2>" not in page and "Avions à moins de" not in _text(page)


def test_the_four_views_are_all_there_and_quiet_hours_are_not_on_display(rig):
    page = ""
    for slug, path in (
            ("look", "/display"), ("look", "/display/arrivals"),
            ("special-looks", "/display/special-looks"), ("calendar", "/display/calendar")):
        _status, view = rig.get("owner", rig.scope() + path)
        assert 'id="personalisation-%s"' % slug in view
        assert 'href="%s"' % (rig.scope() + path) in view
        page += view
    assert 'id="quiet-hours-group-heading"' not in page
    assert 'data-dirty-section="Quiet hours"' not in page


def test_the_location_page_holds_what_display_lost(rig):
    _save_lfpg(rig)
    status, page = rig.get("owner", rig.scope() + "/detection")
    assert status == 200
    assert 'id="place-map"' in page and 'name="timezone"' in page
    assert "Charles de Gaulle International Airport" in _text(page)
    checked = re.search(r'<input type="radio" name="runway" value="08L/26R"[^>]*checked', page)
    assert checked


# --- Device -----------------------------------------------------------------


@pytest.mark.parametrize("scope", [True, False])
def test_device_page_carries_no_detection_card(rig, scope):
    _save_lfpg(rig)
    path = (rig.scope() if scope else "") + "/device"
    status, page = rig.get("admin", path)
    assert status == 200
    assert "detection-card" not in page
    assert "Location and detection" not in page
    assert "Charles de Gaulle" not in _text(page)
    assert page.index("Diagnostic LED") > 0


def test_device_page_stays_admin_only(rig):
    for who in ("owner", "other"):
        status, page = rig.get(who, rig.scope() + "/device")
        assert status == 404
        assert "detection-card" not in page


# --- No field, no dirty section, no runway post ----------------------------


def test_display_save_never_posts_or_resets_the_runway(rig):
    _save_lfpg(rig)
    before = rig.config(rig.owner_dir())
    status, page = rig.get("owner", rig.scope() + "/display")
    assert status == 200 and 'name="tracked_runway"' not in page
    status, response, _body = rig.post("owner", rig.scope() + "/settings", {
        "scope": "display", "return_to": "/display", "theme": "black"})
    assert status == 303
    after = rig.config(rig.owner_dir())
    assert after["theme"] == "black"
    assert after["detection"] == before["detection"]
    assert after.get("tracked_runway") == before.get("tracked_runway")


@pytest.mark.parametrize("who", ["owner", "admin"])
def test_forged_tracked_runway_is_ignored_by_settings(rig, who):
    _save_lfpg(rig)
    before = rig.config(rig.owner_dir())
    status, _response, _body = rig.post(who, rig.scope() + "/settings", {
        "scope": "display", "return_to": "/display", "theme": "black",
        "tracked_runway": "06-24"})
    assert status == 303
    after = rig.config(rig.owner_dir())
    assert after["detection"] == before["detection"]
    assert after.get("tracked_runway") == before.get("tracked_runway") != "06-24"


def test_display_save_keeps_a_position_setting_byte_for_byte(rig):
    _save_position(rig)
    before = rig.config(rig.owner_dir())
    rig.post("owner", rig.scope() + "/settings", {
        "scope": "display", "return_to": "/display", "theme": "black"})
    after = rig.config(rig.owner_dir())
    assert after["detection"] == before["detection"] == {"mode": "position", "radius_km": 9}


# --- Saving Display leaves the place alone -----------------------------------


def test_display_save_leaves_zone_place_and_detection_unchanged(rig):
    home = _save_position(rig)
    device_config.save_device_config(rig.owner_dir(), timezone="America/Martinique")
    before = rig.config(rig.owner_dir())
    position_before = _position_row(rig)
    status, _response, _body = rig.post("owner", rig.scope() + "/settings", {
        "scope": "display", "return_to": "/display", "theme": "black"})
    assert status == 303
    after = rig.config(rig.owner_dir())
    assert after["theme"] == "black"
    assert after["timezone"] == before["timezone"] == "America/Martinique"
    assert after["detection"] == before["detection"]
    assert _position_row(rig) == position_before
    assert position_before[0] == home


def test_a_crafted_location_id_on_display_does_not_move_the_position(rig):
    home = _save_position(rig)
    other = rig.add_location("Elsewhere", 43.0, 5.0)
    position_before = _position_row(rig)
    for who in ("owner", "admin"):
        status, _response, _body = rig.post(who, rig.scope() + "/settings", {
            "scope": "display", "return_to": "/display", "theme": "black",
            "location_id": str(other)})
        assert status == 303
        assert _position_row(rig) == position_before
    assert position_before[0] == home


def test_an_invalid_zone_from_a_legacy_client_is_still_refused(rig):
    _save_position(rig)
    before = rig.config(rig.owner_dir())
    status, _response, body = rig.post("owner", rig.scope() + "/settings", {
        "scope": "display", "return_to": "/display", "theme": "black",
        "timezone": "Mars/Olympus_Mons"})
    assert status == 200
    assert "Time zone not saved" in html.unescape(body)
    assert rig.config(rig.owner_dir()) == before


# --- History -----------------------------------------------------------------


def test_history_unknown_ids_render(rig):
    ids = ("3", "LFPG:08L/26R", "position:9", "no-such-id", HOSTILE_ID)
    with history_db.open_db(rig.owner_dir()) as conn:
        for index, runway_id in enumerate(ids):
            history_db.record_runway_event(
                conn, ts="2026-01-01T10:0%d:00+00:00" % index, hex="abc%d" % index,
                callsign="TST10%d" % index, aircraft_type="A320",
                confirmed_state="departing", corroborated=True, route_source="fresh_hit",
                airline="Air France", origin="ORY", destination="NCE",
                tracked_runway=runway_id)
    for path in ("/flights", "/", "/airlines"):
        for who in ("owner", "admin"):
            status, page = rig.get(who, rig.scope() + path)
            assert status == 200, (who, path)
            assert "<script>alert(1)" not in page
    _status, page = rig.get("owner", rig.scope() + "/flights")
    for index in range(len(ids)):
        assert "TST10%d" % index in page
