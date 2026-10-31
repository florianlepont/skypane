"""Position mode of the Detection page over a real in-process server: the
location and radius POST with its server-side checks, the hidden-panel
rule, the minimal location form, and the owner / admin scoping of every
location read and write.
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
    InProcessAppServer, http_request, session_cookie_for_state_dir)
from server import device_config, fleet_db

PARIS = "Europe/Paris"
RADIUS_MESSAGE = "Enter a whole number of kilometres from 4 to 28."
UNAVAILABLE = "This location is not available. Choose one from the list."
OUTSIDE = "This location is outside metropolitan France. Choose a location in France."


class Rig:
    def __init__(self, state_dir, server, fleet, cookies, state_dirs):
        self.state_dir = state_dir
        self.server = server
        self.fleet = fleet
        self.cookies = cookies
        self.state_dirs = state_dirs

    def owner_dir(self):
        return self.state_dirs[self.fleet.owner_device]

    def other_dir(self):
        return self.state_dirs[self.fleet.other_device]

    def scope(self, device=None):
        return "/devices/%s" % (device or self.fleet.owner_device)

    def get(self, who, path, lang=None):
        headers = {"Accept-Language": lang} if lang else None
        status, _response, body = http_request(
            self.server.url(path), cookie=self.cookies[who], extra_headers=headers)
        return status, body.decode("utf-8", "replace")

    def post(self, who, path, form, lang=None):
        headers = {"Origin": self.server.base_url()}
        if lang:
            headers["Accept-Language"] = lang
        data = urllib.parse.urlencode(form).encode()
        status, response, body = http_request(
            self.server.url(path), method="POST", data=data,
            cookie=self.cookies[who], extra_headers=headers)
        return status, response, body.decode("utf-8", "replace")

    def config(self, state_dir):
        path = device_config.device_config_path(state_dir)
        if not os.path.exists(path):
            return {}
        with open(path, "rb") as handle:
            return json.loads(handle.read() or b"{}")

    def config_bytes(self, state_dir):
        path = device_config.device_config_path(state_dir)
        if not os.path.exists(path):
            return None
        with open(path, "rb") as handle:
            return handle.read()

    def add_location(self, owner_id, name, lat, lon):
        conn = fleet_db.connect(self.state_dir)
        try:
            return fleet_db.add_location(conn, name, lat, lon, PARIS, owner_user_id=owner_id)
        finally:
            conn.close()

    def locations(self):
        conn = fleet_db.connect(self.state_dir)
        try:
            return [dict(row) for row in fleet_db.list_locations(conn)]
        finally:
            conn.close()

    def device_location(self, device_id):
        conn = fleet_db.connect(self.state_dir)
        try:
            return fleet_db.get_device(conn, device_id)["location_id"]
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


def _position_form(location_id, radius="9", **extra):
    form = {"action": "save_detection", "mode": "position",
            "location_id": str(location_id), "radius_km": radius}
    form.update(extra)
    return form


def _location_form(name="Lyon", lat="45.76", lon="4.84", location_id="", zone=PARIS):
    return {"action": "save_location", "location_name": name, "latitude": lat,
            "longitude": lon, "timezone": zone, "location_id": location_id}


def _post_detection(rig, who, form, device=None):
    return rig.post(who, rig.scope(device) + "/detection", form)


# --- saving position --------------------------------------------------------


def test_position_save_stores_radius_and_assigns_the_location(rig):
    home = rig.add_location(rig.fleet.owner_id, "Home", 48.8566, 2.3522)
    status, response, _body = _post_detection(rig, "owner", _position_form(home))
    assert status == 303
    assert "flash=detection_saved" in response["Location"]
    assert rig.config(rig.owner_dir())["detection"] == {"mode": "position", "radius_km": 9}
    assert rig.device_location(rig.fleet.owner_device) == home


def test_position_save_summary_and_frame_text(rig):
    home = rig.add_location(rig.fleet.owner_id, "Home", 48.8566, 2.3522)
    _post_detection(rig, "owner", _position_form(home, "9"))
    _status, page = rig.get("owner", rig.scope() + "/detection")
    text = _text(page)
    assert "Aircraft within 9 km of Home" in text
    assert "NEARBY · 9 KM" in text
    assert "Watching Within 9 km" in text
    assert "No usable location" not in text


def test_position_save_accepts_the_bounds(rig):
    home = rig.add_location(rig.fleet.owner_id, "Home", 48.8566, 2.3522)
    for radius in ("4", "28"):
        status, _r, _b = _post_detection(rig, "owner", _position_form(home, radius))
        assert status == 303
        assert rig.config(rig.owner_dir())["detection"]["radius_km"] == int(radius)


def test_position_panel_lists_rounded_coordinates_only(rig):
    rig.add_location(rig.fleet.owner_id, "Home", 48.856614, 2.352222)
    _status, page = rig.get("owner", rig.scope() + "/detection")
    assert "Home — 48.86, 2.35" in _text(page)
    select = re.search(r'<select id="detection-location".*?</select>', page, re.S).group(0)
    assert "48.8566" not in select and "2.3522" not in select
    assert "Shared with data providers rounded to about 1 km." in _text(page)
    assert re.search(r'<input type="number" id="detection-radius" name="radius_km"[^>]*'
                     r'min="4" max="28" step="1"[^>]*value="9"', page)


def test_position_panel_marks_a_location_outside_france_disabled(rig):
    rig.add_location(rig.fleet.owner_id, "London", 51.5, -0.12)
    _status, page = rig.get("owner", rig.scope() + "/detection")
    assert re.search(r"<option value=\"\d+\" disabled>London — outside France</option>", page)


def test_position_panel_without_locations_shows_empty_state_and_no_radius(rig):
    _status, page = rig.get("owner", rig.scope() + "/detection")
    panel = re.search(r'<section class="detection-panel detection-panel--position".*?</section>',
                      page, re.S).group(0)
    assert "No location yet" in panel
    assert 'name="radius_km"' not in panel and "<select" not in panel
    assert "new_location=1" in panel


# --- rejections ---------------------------------------------------------------


@pytest.mark.parametrize("radius", ["3", "29", "9.5", "", "abc", "-5", "0009x", "１２"])
def test_position_rejections_radius(rig, radius):
    home = rig.add_location(rig.fleet.owner_id, "Home", 48.8566, 2.3522)
    before = rig.config_bytes(rig.owner_dir())
    status, _r, page = _post_detection(rig, "owner", _position_form(home, radius))
    assert status == 200
    assert RADIUS_MESSAGE in _text(page)
    assert rig.config_bytes(rig.owner_dir()) == before
    assert rig.device_location(rig.fleet.owner_device) is None


def test_position_rejections_missing_location(rig):
    rig.add_location(rig.fleet.owner_id, "Home", 48.8566, 2.3522)
    status, _r, page = _post_detection(
        rig, "owner", {"action": "save_detection", "mode": "position", "radius_km": "9"})
    assert status == 200
    assert "Choose a location." in _text(page)
    assert rig.config(rig.owner_dir()) == {}


@pytest.mark.parametrize("value", ["99999", "abc", "-1", "1.5", ""])
def test_position_rejections_unknown_location_ids(rig, value):
    rig.add_location(rig.fleet.owner_id, "Home", 48.8566, 2.3522)
    status, _r, page = _post_detection(rig, "owner", _position_form(value))
    assert status == 200
    assert (UNAVAILABLE in _text(page)) or ("Choose a location." in _text(page))
    assert rig.config(rig.owner_dir()) == {}


def test_position_rejections_another_users_location(rig):
    theirs = rig.add_location(rig.fleet.other_id, "Theirs", 43.3, 5.4)
    before = rig.config_bytes(rig.owner_dir())
    status, _r, page = _post_detection(rig, "owner", _position_form(theirs))
    assert status == 200
    assert UNAVAILABLE in _text(page)
    assert rig.config_bytes(rig.owner_dir()) == before
    assert rig.device_location(rig.fleet.owner_device) is None


def test_position_rejections_stored_location_outside_france(rig):
    london = rig.add_location(rig.fleet.owner_id, "London", 51.5, -0.12)
    status, _r, page = _post_detection(rig, "owner", _position_form(london))
    assert status == 200
    text = _text(page)
    assert OUTSIDE in text
    message = re.search(r'role="alert">([^<]*outside metropolitan[^<]*)<', page).group(1)
    assert not re.search(r"\d", message)
    assert rig.config(rig.owner_dir()) == {}
    assert rig.device_location(rig.fleet.owner_device) is None


def test_position_rejection_keeps_the_typed_values(rig):
    home = rig.add_location(rig.fleet.owner_id, "Home", 48.8566, 2.3522)
    _status, _r, page = _post_detection(rig, "owner", _position_form(home, "3"))
    assert re.search(r'name="radius_km"[^>]*value="3"', page)
    assert "data-dirty-carried" in page


def test_position_user_cannot_post_for_another_users_device(rig):
    home = rig.add_location(rig.fleet.owner_id, "Home", 48.8566, 2.3522)
    status, _r, _b = _post_detection(
        rig, "owner", _position_form(home), device=rig.fleet.other_device)
    assert status == 404
    assert rig.config(rig.other_dir()) == {}


# --- hidden panel ---------------------------------------------------------------


def test_hidden_panel_runway_post_ignores_location_and_radius(rig):
    status, _r, _b = _post_detection(rig, "owner", {
        "action": "save_detection", "mode": "runway", "airport": "LFPG",
        "runway": "08L/26R", "radius_km": "99", "location_id": "zz"})
    assert status == 303
    assert rig.config(rig.owner_dir())["detection"] == {
        "mode": "runway", "airport": "LFPG", "runway": "08L/26R"}


def test_hidden_panel_position_post_ignores_airport_and_runway(rig):
    home = rig.add_location(rig.fleet.owner_id, "Home", 48.8566, 2.3522)
    status, _r, _b = _post_detection(
        rig, "owner", _position_form(home, "12", airport="ZZZZ", runway="nope"))
    assert status == 303
    assert rig.config(rig.owner_dir())["detection"] == {"mode": "position", "radius_km": 12}


def test_hidden_panel_controls_carry_no_required_attribute(rig):
    rig.add_location(rig.fleet.owner_id, "Home", 48.8566, 2.3522)
    _status, page = rig.get("owner", rig.scope() + "/detection")
    without_location_form = re.sub(
        r'<details id="location-form".*?</details>', "", page, flags=re.S)
    assert not re.search(r"\brequired\b", without_location_form)
    assert re.search(r'<form method="post" id="detection-form"[^>]* novalidate>', page)


# --- location create and edit -----------------------------------------------------


def test_location_create_saves_for_the_owner_and_lists_it(rig):
    status, response, _b = _post_detection(rig, "owner", _location_form("Lyon", "45,76", "4.84"))
    assert status == 303
    assert "flash=location_saved" in response["Location"]
    rows = rig.locations()
    assert len(rows) == 1
    assert rows[0]["owner_user_id"] == rig.fleet.owner_id
    assert (rows[0]["name"], rows[0]["latitude"], rows[0]["longitude"]) == ("Lyon", 45.76, 4.84)
    assert rows[0]["timezone"] == PARIS
    _s, page = rig.get("owner", rig.scope() + "/detection")
    assert "45.76, 4.84" in _text(page)
    assert re.search(r'<option value="%d"[^>]*>Lyon — 45.76, 4.84</option>' % rows[0]["id"], page)


@pytest.mark.parametrize("fields,message", [
    ({"location_name": ""}, "Enter a name of up to 60 characters."),
    ({"location_name": "x" * 61}, "Enter a name of up to 60 characters."),
    ({"latitude": "abc"}, "Enter a number such as 48.8566."),
    ({"longitude": "1e3"}, "Enter a number such as 48.8566."),
    ({"latitude": "nan"}, "Enter a number such as 48.8566."),
    ({"latitude": "1.2.3"}, "Enter a number such as 48.8566."),
    ({"latitude": "60"}, OUTSIDE),
    ({"longitude": "20"}, OUTSIDE),
    ({"timezone": "America/Martinique"}, "Choose a time zone from the list."),
])
def test_location_create_refusals_write_nothing(rig, fields, message):
    form = _location_form()
    form.update(fields)
    status, _r, page = _post_detection(rig, "owner", form)
    assert status == 200
    assert message in _text(page)
    assert '<details id="location-form" class="detection-location-form" open>' in page
    assert rig.locations() == []


def test_location_create_markup_in_the_name_is_escaped(rig):
    _post_detection(rig, "owner", _location_form('<b onload="x">&"', "45.76", "4.84"))
    _s, page = rig.get("owner", rig.scope() + "/detection")
    assert "<b onload" not in page
    assert "&lt;b onload=&quot;x&quot;&gt;" in page


def test_location_edit_updates_a_row_the_user_owns(rig):
    home = rig.add_location(rig.fleet.owner_id, "Home", 48.8566, 2.3522)
    _s, page = rig.get("owner", rig.scope() + "/detection?location=%d" % home)
    assert 'summary>Edit location details</summary>' in page
    assert re.search(r'name="location_name" value="Home"', page)
    status, _r, _b = _post_detection(
        rig, "owner", _location_form("Maison", "48.9", "2.4", str(home)))
    assert status == 303
    rows = rig.locations()
    assert len(rows) == 1
    assert (rows[0]["name"], rows[0]["latitude"], rows[0]["longitude"]) == ("Maison", 48.9, 2.4)


def test_location_edit_link_names_the_location(rig):
    rig.add_location(rig.fleet.owner_id, "Home", 48.8566, 2.3522)
    _s, page = rig.get("owner", rig.scope() + "/detection")
    assert 'aria-label="Edit location Home"' in page
    assert "?location=" in page and "#location-form" in page


def test_location_edit_of_another_owners_row_is_refused(rig):
    theirs = rig.add_location(rig.fleet.other_id, "Theirs", 43.3, 5.4)
    status, _r, page = _post_detection(
        rig, "owner", _location_form("Hijack", "48.9", "2.4", str(theirs)))
    assert status == 200
    assert UNAVAILABLE in _text(page)
    assert [r["name"] for r in rig.locations()] == ["Theirs"]


def test_location_owner_scope_lists_only_the_subjects_rows(rig):
    rig.add_location(rig.fleet.owner_id, "Mine", 48.8, 2.3)
    rig.add_location(rig.fleet.other_id, "Theirs", 43.3, 5.4)
    _s, page = rig.get("owner", rig.scope() + "/detection")
    assert "Mine" in page and "Theirs" not in page
    assert "Your locations" in _text(page)


def test_location_owner_scope_ignores_a_forged_owner_field(rig):
    form = _location_form()
    form["owner_user_id"] = str(rig.fleet.other_id)
    _post_detection(rig, "owner", form)
    assert [r["owner_user_id"] for r in rig.locations()] == [rig.fleet.owner_id]


def test_location_owner_scope_other_user_gets_404(rig):
    status, _r, _b = _post_detection(
        rig, "other", _location_form(), device=rig.fleet.owner_device)
    assert status == 404
    assert rig.locations() == []


def test_location_post_with_a_foreign_origin_is_refused(rig):
    data = urllib.parse.urlencode(_location_form()).encode()
    status, _r, _b = http_request(
        rig.server.url(rig.scope() + "/detection"), method="POST", data=data,
        cookie=rig.cookies["owner"], extra_headers={"Origin": "https://evil.example"})
    assert status == 403
    assert rig.locations() == []


# --- admin acting for the owner -----------------------------------------------------


def test_admin_saves_for_owner_creates_a_row_owned_by_the_owner(rig):
    status, _r, _b = _post_detection(rig, "admin", _location_form("Nice", "43.7", "7.26"))
    assert status == 303
    assert [r["owner_user_id"] for r in rig.locations()] == [rig.fleet.owner_id]


def test_admin_saves_for_owner_card_wording_and_position(rig):
    home = rig.add_location(rig.fleet.owner_id, "Home", 48.8566, 2.3522)
    _s, page = rig.get("admin", rig.scope() + "/detection")
    text = _text(page)
    assert "Locations of this frame’s owner" in text
    assert "You are saving locations for this frame’s owner." in text
    assert "Home" in text
    status, _r, _b = _post_detection(rig, "admin", _position_form(home, "10"))
    assert status == 303
    assert rig.device_location(rig.fleet.owner_device) == home
    assert rig.config(rig.owner_dir())["detection"]["radius_km"] == 10


def test_admin_saves_for_owner_cannot_use_the_admins_own_location(rig):
    mine = rig.add_location(rig.fleet.admin_id, "Admin place", 48.8, 2.3)
    status, _r, page = _post_detection(rig, "admin", _position_form(mine))
    assert status == 200
    assert UNAVAILABLE in _text(page)


# --- fail-safe toast ----------------------------------------------------------------


def test_failsafe_toast_when_the_saved_location_leaves_the_box(rig):
    home = rig.add_location(rig.fleet.owner_id, "Home", 48.8566, 2.3522)
    _post_detection(rig, "owner", _position_form(home))
    conn = fleet_db.connect(rig.state_dir)
    try:
        fleet_db.update_location(conn, home, "Home", 10.0, 2.3522, PARIS)
    finally:
        conn.close()
    _s, page = rig.get("owner", rig.scope() + "/detection")
    text = _text(page)
    assert "No usable location" in text
    assert "toast--docked" in page
    assert "Runway 07/25 at Paris-Orly Airport (ORY)" in text


# --- text rules ---------------------------------------------------------------------


@pytest.mark.parametrize("lang", [None, "fr"])
def test_no_nm_text_position(rig, lang):
    home = rig.add_location(rig.fleet.owner_id, "Home", 48.8566, 2.3522)
    _post_detection(rig, "owner", _position_form(home, "9"))
    _s, page = rig.get("owner", rig.scope() + "/detection", lang=lang)
    assert not re.search(r"\bNM\b|\bnm\b|nautical", _text(page))
    assert "radius_nm" not in page


def test_position_page_in_french(rig):
    home = rig.add_location(rig.fleet.owner_id, "Home", 48.8566, 2.3522)
    _post_detection(rig, "owner", _position_form(home, "9"))
    _s, page = rig.get("owner", rig.scope() + "/detection", lang="fr")
    text = _text(page)
    assert "Avions à moins de 9 km de Home" in text
    assert "Rayon (kilomètres)" in text
    assert "Vos lieux" in text
    assert "Enregistrer le lieu" in text
    assert "NEARBY · 9 KM" in text


def test_position_save_leaves_the_location_unchanged_when_the_config_write_fails(
        rig, monkeypatch):
    old = rig.add_location(rig.fleet.owner_id, "Old", 45.76, 4.84)
    new = rig.add_location(rig.fleet.owner_id, "New", 48.8566, 2.3522)
    conn = fleet_db.connect(rig.state_dir)
    try:
        fleet_db.set_device_location_checked(
            conn, rig.fleet.owner_device, old, rig.fleet.owner_id, False)
    finally:
        conn.close()

    def refuse(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(device_config, "save_device_config", refuse)
    status, response, _body = _post_detection(rig, "owner", _position_form(new))
    assert status == 303
    assert "flash=save_failed" in response["Location"]
    assert rig.device_location(rig.fleet.owner_device) == old
