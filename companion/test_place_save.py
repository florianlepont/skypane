"""POST /detection with action save_place over a real in-process server: both
modes, refusals that write nothing, copy-on-write of the position row,
live-frame safety, csrf and the access outcomes for each kind of caller.
"""
import html
import json
import os
import re
import urllib.parse

import pytest

from access_matrix_support import (
    ADMIN_EMAIL, OTHER_EMAIL, OWNER_EMAIL, seed_matrix_fleet)
from companion import device_scope
from companion_app_server import (
    InProcessAppServer, http_request, session_cookie_for_state_dir, with_csrf)
import matrix_rows_place
from server import airports, detection, device_config, fleet_db, hardware

PARIS = "Europe/Paris"
TOKYO = "Indian/Reunion"
CO_MANAGER_EMAIL = "comanager@example.com"
SIBLING_MAC = "aa:bb:cc:dd:ee:99"
SIBLING_SECRET = "1" * 64
RADIUS_MESSAGE = "Enter a whole number of kilometres from 2 to 28."
OUTSIDE = "This location is outside metropolitan France. Choose a location in France."
NUMBER = "Enter a number such as 48.8566."
NAME_TOO_LONG = "Enter a name of up to 60 characters."
ZONE_MESSAGE = "Pick a time zone from the list."


class Rig:
    def __init__(self, state_dir, server, fleet, cookies, state_dirs, sibling):
        self.state_dir = state_dir
        self.server = server
        self.fleet = fleet
        self.cookies = cookies
        self.state_dirs = state_dirs
        self.sibling = sibling

    def scope(self, device=None):
        return "/devices/%s" % (device or self.fleet.owner_device)

    def owner_dir(self):
        return self.state_dirs[self.fleet.owner_device]

    def post(self, who, form, device=None, csrf=True):
        cookie = self.cookies.get(who)
        path = self.scope(device) + "/detection"
        headers = {"Origin": self.server.base_url()}
        if cookie is None:
            data = urllib.parse.urlencode(form).encode()
        elif csrf:
            data = with_csrf(cookie, form)
        else:
            data = urllib.parse.urlencode(form).encode()
        status, response, body = http_request(
            self.server.url(path), method="POST", data=data,
            cookie=cookie, extra_headers=headers)
        return status, response, body.decode("utf-8", "replace")

    def get(self, who, path):
        status, _response, body = http_request(
            self.server.url(path), cookie=self.cookies[who])
        return status, body.decode("utf-8", "replace")

    def config_bytes(self, state_dir):
        path = device_config.device_config_path(state_dir)
        if not os.path.exists(path):
            return None
        with open(path, "rb") as handle:
            return handle.read()

    def config(self, state_dir):
        raw = self.config_bytes(state_dir)
        return {} if raw is None else json.loads(raw or b"{}")

    def with_conn(self, action):
        conn = fleet_db.connect(self.state_dir)
        try:
            return action(conn)
        finally:
            conn.close()

    def position(self, device_id):
        return self.with_conn(lambda c: fleet_db.frame_position(c, device_id))

    def location_id(self, device_id):
        return self.with_conn(lambda c: fleet_db.get_device(c, device_id)["location_id"])

    def location_rows(self):
        return self.with_conn(
            lambda c: [dict(r) for r in fleet_db.list_locations(c)])

    def poll_view(self, device_id, cfg):
        conn = fleet_db.connect_readonly(self.state_dir)
        try:
            location = fleet_db.device_coordinates(conn).get(device_id)
        finally:
            conn.close()
        return location, detection.spec_for(cfg, location)


@pytest.fixture(autouse=True)
def _no_kill_switch(monkeypatch):
    monkeypatch.delenv(detection.LEGACY_GEOFENCE_ENV, raising=False)


@pytest.fixture
def rig(tmp_path):
    state_dir = str(tmp_path / "state")
    server = InProcessAppServer(state_dir)
    fleet = seed_matrix_fleet(state_dir)
    conn = fleet_db.connect(state_dir)
    try:
        sibling = fleet_db.add_device(
            conn, SIBLING_MAC, SIBLING_SECRET, hardware.LEGACY_KEY, fleet.owner_id,
            state_path="auto")
        co_manager_id = fleet_db.add_user(conn, CO_MANAGER_EMAIL, "user")
        fleet_db.add_co_manager(conn, fleet.owner_device, co_manager_id, fleet.owner_id)
    finally:
        conn.close()
    state_dirs = {d.id: d.state_dir for d in device_scope.load_devices(state_dir)}
    cookies = {
        "owner": session_cookie_for_state_dir(state_dir, OWNER_EMAIL, "user"),
        "other": session_cookie_for_state_dir(state_dir, OTHER_EMAIL, "user"),
        "admin": session_cookie_for_state_dir(state_dir, ADMIN_EMAIL, "admin"),
        "co-manager": session_cookie_for_state_dir(state_dir, CO_MANAGER_EMAIL, "user"),
    }
    for state in state_dirs.values():
        os.makedirs(state, exist_ok=True)
    yield Rig(state_dir, server, fleet, cookies, state_dirs, sibling)
    server.stop()


def _runway_form(**extra):
    form = {"action": matrix_rows_place.ACTION, "mode": "runway",
            "airport": "LFPG", "runway": "08L/26R"}
    form.update(extra)
    return form


def _position_form(**extra):
    form = {"action": matrix_rows_place.ACTION, "mode": "position",
            "latitude": "43.2965", "longitude": "5.3698", "radius_km": "9",
            "place_label": "Marseille"}
    form.update(extra)
    return form


def _text(markup):
    stripped = re.sub(r"<(script|style)\b.*?</\1>", " ", markup, flags=re.S)
    return html.unescape(re.sub(r"<[^>]+>", " ", stripped))


# --- position mode ----------------------------------------------------------


def test_position_save_stores_the_pin_the_label_and_the_radius(rig):
    status, response, _body = rig.post("owner", _position_form())
    assert status == 303
    assert response["Location"].startswith(
        rig.scope() + "/detection?flash=place_saved")
    position = rig.position(rig.fleet.owner_device)
    assert (position["name"], position["latitude"], position["longitude"]) == (
        "Marseille", 43.2965, 5.3698)
    assert position["timezone"] == PARIS
    assert rig.config(rig.owner_dir())["detection"] == {"mode": "position", "radius_km": 9}


def test_the_saved_toast_names_the_stored_place_in_both_languages(rig):
    rig.post("owner", _position_form(place_label="Vieux <Port>"))
    path = rig.scope() + "/detection?flash=place_saved&place=Injected"
    _status, page = rig.get("owner", path)
    text = _text(page)
    assert "Detection now follows the area within 9 km of Vieux <Port>." in text
    assert "Vieux <Port>" not in page and "Injected" not in text
    status, _resp, body = http_request(
        rig.server.url(path), cookie=rig.cookies["owner"],
        extra_headers={"Accept-Language": "fr"})
    assert ("La détection suit désormais la zone dans un rayon de 9 km autour de "
            "Vieux <Port>.") in _text(body.decode("utf-8"))


def _toast(rig, lang="en"):
    _status, _resp, body = http_request(
        rig.server.url(rig.scope() + "/detection?flash=place_saved"),
        cookie=rig.cookies["owner"], extra_headers={"Accept-Language": lang})
    return _text(body.decode("utf-8"))


def test_a_pin_moved_off_an_airport_in_position_mode_drops_the_airport_name(rig):
    """The label field still carries the airport picked before: the saved
    place and its toast must not name an airport the pin has left."""
    bron = airports.find_airport("LFLY")
    rig.post("owner", _runway_form(airport="LFLY", runway=bron.runways[0].designator))
    assert "Detection now follows %s." % bron.name in _toast(rig)
    status, _response, _body = rig.post("owner", _position_form(
        latitude="45.7325", longitude="4.9191", radius_km="2", place_label=bron.name))
    assert status == 303
    assert rig.position(rig.fleet.owner_device)["name"] != bron.name
    text = _toast(rig)
    assert bron.name not in text
    assert "Detection now follows the area within 2 km of 45.7325 N · 4.9191 E." in text
    assert ("La détection suit désormais la zone dans un rayon de 2 km autour de "
            "45,7325 N · 4,9191 E.") in _toast(rig, "fr")


def test_a_position_pin_left_on_the_airport_keeps_its_name(rig):
    bron = airports.find_airport("LFLY")
    rig.post("owner", _position_form(
        latitude="%.4f" % bron.lat, longitude="%.4f" % bron.lon, radius_km="5",
        place_label=bron.name))
    assert rig.position(rig.fleet.owner_device)["name"] == bron.name
    assert "the area within 5 km of %s." % bron.name in _toast(rig)


def test_the_runway_toast_names_the_saved_airport_not_a_typed_label(rig):
    rig.post("owner", _runway_form(place_label="Grandma's house"))
    text = _toast(rig)
    assert "Detection now follows %s." % airports.find_airport("LFPG").name in text
    assert "Grandma" not in text


@pytest.mark.parametrize("override, message", [
    ({"latitude": "52.0"}, OUTSIDE),
    ({"longitude": "12.0"}, OUTSIDE),
    ({"latitude": "abc"}, NUMBER),
    ({"longitude": ""}, NUMBER),
    ({"radius_km": "1"}, RADIUS_MESSAGE),
    ({"radius_km": "29"}, RADIUS_MESSAGE),
    ({"radius_km": "9.5"}, RADIUS_MESSAGE),
    ({"radius_km": ""}, RADIUS_MESSAGE),
    ({"place_label": "x" * 61}, NAME_TOO_LONG),
    ({"timezone": "Mars/Olympus"}, ZONE_MESSAGE),
])
def test_a_refused_position_save_writes_nothing_and_shows_the_error(rig, override, message):
    before_cfg = rig.config_bytes(rig.owner_dir())
    before_rows = rig.location_rows()
    status, _response, body = rig.post("owner", _position_form(**override))
    assert status == 400
    assert message in _text(body)
    assert rig.config_bytes(rig.owner_dir()) == before_cfg
    assert rig.location_rows() == before_rows
    assert rig.location_id(rig.fleet.owner_device) is None


def test_a_refused_save_escapes_what_was_entered(rig):
    payload = '"><script>alert(1)</script>'
    status, _response, body = rig.post(
        "owner", _position_form(latitude="52.0", place_label=payload))
    assert status == 400
    assert "<script>alert(1)</script>" not in body


# --- runway mode ------------------------------------------------------------


def test_runway_save_stores_the_runway_and_the_airport_position(rig):
    status, _response, _body = rig.post("owner", _runway_form())
    assert status == 303
    assert rig.config(rig.owner_dir())["detection"] == {
        "mode": "runway", "airport": "LFPG", "runway": "08L/26R"}
    position = rig.position(rig.fleet.owner_device)
    assert position["name"] == "Charles de Gaulle International Airport"
    assert (position["latitude"], position["longitude"]) == (49.0090, 2.5541)


def test_runway_save_accepts_a_catalogue_airport_outside_the_france_box(rig):
    status, _response, _body = rig.post(
        "owner", _runway_form(airport="FMCZ", runway="16/34"))
    assert status == 303
    assert rig.position(rig.fleet.owner_device)["latitude"] == -12.8093


def test_a_moved_pin_in_runway_mode_still_follows_the_runway(rig):
    rig.post("owner", _runway_form(
        latitude="48.9000", longitude="2.5000", place_label="Terrace"))
    position = rig.position(rig.fleet.owner_device)
    assert (position["name"], position["latitude"], position["longitude"]) == (
        "Terrace", 48.9, 2.5)
    cfg = device_config.load_device_config(rig.owner_dir())
    _location, spec = rig.poll_view(rig.fleet.owner_device, cfg)
    assert spec.display_id == detection.runway_display_id("LFPG", "08L/26R")


@pytest.mark.parametrize("override, message", [
    ({"airport": "ZZZZ"}, "Choose an airport."),
    ({"airport": ""}, "Choose an airport."),
    ({"runway": "99/99"}, "This runway does not exist at this airport."),
    ({"runway": ""}, "Choose a runway."),
    ({"latitude": "95", "longitude": "2"}, NUMBER),
    ({"latitude": "48.9", "longitude": ""}, NUMBER),
])
def test_a_refused_runway_save_writes_nothing(rig, override, message):
    before_cfg = rig.config_bytes(rig.owner_dir())
    status, _response, body = rig.post("owner", _runway_form(**override))
    assert status == 400
    assert message in _text(body)
    assert rig.config_bytes(rig.owner_dir()) == before_cfg
    assert rig.location_rows() == []


def test_an_unknown_mode_is_refused(rig):
    status, _response, body = rig.post("owner", _runway_form(mode="bogus"))
    assert status == 400
    assert "Choose a detection mode." in _text(body)


def test_an_empty_label_falls_back_to_the_airport_name(rig):
    rig.post("owner", _runway_form(place_label="   "))
    assert rig.position(rig.fleet.owner_device)["name"] == (
        "Charles de Gaulle International Airport")
    rig.post("owner", _position_form(place_label=""))
    assert rig.position(rig.fleet.owner_device)["name"] == "Frame position"


# --- time zone --------------------------------------------------------------


def test_a_posted_zone_is_stored_and_an_absent_zone_is_left_alone(rig):
    rig.post("owner", _position_form(timezone=TOKYO))
    assert rig.config(rig.owner_dir())["timezone"] == TOKYO
    assert rig.position(rig.fleet.owner_device)["timezone"] == TOKYO
    rig.post("owner", _position_form(place_label="Again"))
    assert rig.config(rig.owner_dir())["timezone"] == TOKYO


# --- live-frame safety ------------------------------------------------------


def test_saving_the_legacy_orly_runway_unchanged_keeps_the_config_bytes(rig):
    path = device_config.device_config_path(rig.owner_dir())
    device_config.save_device_config(rig.owner_dir(), tracked_runway="3")
    before = rig.config_bytes(rig.owner_dir())
    assert os.path.exists(path)
    status, _response, _body = rig.post(
        "owner", _runway_form(airport="LFPO", runway="07/25"))
    assert status == 303
    assert rig.config_bytes(rig.owner_dir()) == before


def test_a_place_save_writes_no_look_rule_calendar_interval_or_quiet_key(rig):
    device_config.save_device_config(
        rig.owner_dir(), theme="blue", wake_interval_s=900,
        quiet_hours_enabled=True, quiet_hours_start="23:00", quiet_hours_end="06:00")
    before = rig.config(rig.owner_dir())
    rig.post("owner", _position_form(timezone=TOKYO))
    after = rig.config(rig.owner_dir())
    changed = {k for k in set(before) | set(after) if before.get(k) != after.get(k)}
    assert changed == {"detection", "timezone"}


def test_a_save_on_a_sibling_frame_leaves_the_poll_reading_of_another_untouched(rig):
    shared = rig.with_conn(lambda c: fleet_db.add_location(
        c, "Old", 48.7262, 2.3652, PARIS, owner_user_id=rig.fleet.owner_id))
    rig.with_conn(lambda c: fleet_db.set_device_location_checked(
        c, rig.fleet.owner_device, shared, rig.fleet.owner_id, False))
    cfg = {"detection": {"mode": "position", "radius_km": 10}}
    before = rig.poll_view(rig.fleet.owner_device, cfg)
    rig.post("owner", _position_form(), device=rig.sibling)
    assert rig.poll_view(rig.fleet.owner_device, cfg) == before


# --- copy on write ----------------------------------------------------------


def test_first_save_creates_a_private_row_then_updates_it_in_place_then_repeats_quietly(rig):
    rig.post("owner", _position_form())
    first = rig.location_id(rig.fleet.owner_device)
    assert first is not None and len(rig.location_rows()) == 1
    rig.post("owner", _position_form(latitude="45.7600", longitude="4.8400"))
    assert rig.location_id(rig.fleet.owner_device) == first
    assert len(rig.location_rows()) == 1
    assert rig.position(rig.fleet.owner_device)["latitude"] == 45.76
    before = rig.location_rows()
    rig.post("owner", _position_form(latitude="45.7600", longitude="4.8400"))
    assert rig.location_rows() == before
    assert rig.location_id(rig.fleet.owner_device) == first


def test_a_row_shared_with_another_frame_is_copied_not_moved(rig):
    shared = rig.with_conn(lambda c: fleet_db.add_location(
        c, "Shared", 48.7262, 2.3652, PARIS, owner_user_id=rig.fleet.owner_id))
    for device in (rig.fleet.owner_device, rig.sibling):
        rig.with_conn(lambda c, d=device: fleet_db.set_device_location_checked(
            c, d, shared, rig.fleet.owner_id, False))
    status, _response, _body = rig.post("owner", _position_form())
    assert status == 303
    assert rig.location_id(rig.fleet.owner_device) != shared
    assert rig.location_id(rig.sibling) == shared
    sibling = rig.position(rig.sibling)
    assert (sibling["name"], sibling["latitude"], sibling["longitude"]) == (
        "Shared", 48.7262, 2.3652)


def test_a_failed_config_write_restores_the_previous_location_link(rig, monkeypatch):
    original = rig.with_conn(lambda c: fleet_db.add_location(
        c, "Before", 48.7262, 2.3652, PARIS, owner_user_id=rig.fleet.owner_id))
    rig.with_conn(lambda c: fleet_db.set_device_location_checked(
        c, rig.fleet.owner_device, original, rig.fleet.owner_id, False))
    # The row is shared, so the save inserts a new one and links it.
    rig.with_conn(lambda c: fleet_db.set_device_location_checked(
        c, rig.sibling, original, rig.fleet.owner_id, False))

    def refuse(*_args, **_kwargs):
        raise OSError("disk full")
    monkeypatch.setattr(detection, "apply_position_selection", refuse)
    status, response, _body = rig.post("owner", _position_form())
    assert status == 303
    assert "flash=save_failed" in response["Location"]
    assert rig.location_id(rig.fleet.owner_device) == original


# --- the older actions ------------------------------------------------------


def test_the_older_detection_and_location_actions_still_work(rig):
    status, _response, _body = rig.post("owner", {
        "action": "save_location", "location_name": "Lyon", "latitude": "45.76",
        "longitude": "4.84", "timezone": PARIS, "location_id": ""})
    assert status == 303
    lyon = [r for r in rig.location_rows() if r["name"] == "Lyon"][0]["id"]
    status, _response, _body = rig.post("owner", {
        "action": "save_detection", "mode": "position",
        "location_id": str(lyon), "radius_km": "9"})
    assert status == 303
    assert rig.location_id(rig.fleet.owner_device) == lyon
    status, _response, _body = rig.post("owner", {
        "action": "save_detection", "mode": "position", "location_id": "", "radius_km": "9"})
    assert status == 200


# --- csrf and access --------------------------------------------------------


def test_a_post_without_a_csrf_token_is_refused_and_writes_nothing(rig):
    status, _response, _body = rig.post("owner", _position_form(), csrf=False)
    assert status == 403
    assert rig.location_rows() == []
    assert rig.config_bytes(rig.owner_dir()) is None


@pytest.mark.parametrize("who", sorted(matrix_rows_place.EXPECTED_STATUS))
def test_each_caller_gets_the_documented_outcome(rig, who):
    status, response, _body = rig.post(who, _position_form())
    expected = matrix_rows_place.EXPECTED_STATUS[who]
    assert status == expected
    if who == "anonymous":
        assert "/login" in response["Location"]
    if expected == 303 and who != "anonymous":
        assert rig.position(rig.fleet.owner_device)["name"] == "Marseille"
    else:
        assert rig.location_rows() == []
