"""The Location and detection page over a real in-process server: the card
order, the airport list and the data the map script reads, the controls of the
details card, and the plain no-script save (`action=save_place`) with its
refusals, in both languages, plus the policy headers every re-render sends.
"""
import html
import json
import os
import re
import unicodedata
import urllib.parse

import pytest

from access_matrix_support import (
    ADMIN_EMAIL, OTHER_EMAIL, OWNER_EMAIL, seed_matrix_fleet)
from companion import device_scope, page_policy
from companion.pages import place_page
from companion_app_server import (
    InProcessAppServer, http_request, session_cookie_for_state_dir, with_csrf)
from server import airports, detection, device_config, fleet_db

PARIS = "Europe/Paris"
MAP_POLICY = (
    page_policy.MAP_CONTENT_SECURITY_POLICY, page_policy.MAP_PERMISSIONS_POLICY)


class Rig:
    def __init__(self, state_dir, server, fleet, cookies, state_dirs):
        self.state_dir = state_dir
        self.server = server
        self.fleet = fleet
        self.cookies = cookies
        self.state_dirs = state_dirs

    def scope(self):
        return "/devices/%s" % self.fleet.owner_device

    def owner_dir(self):
        return self.state_dirs[self.fleet.owner_device]

    def get(self, who, path, lang=None):
        headers = {"Accept-Language": lang} if lang else None
        status, response, body = http_request(
            self.server.url(path), cookie=self.cookies[who], extra_headers=headers)
        return status, response, body.decode("utf-8", "replace")

    def post(self, who, form, lang=None):
        headers = {"Origin": self.server.base_url()}
        if lang:
            headers["Accept-Language"] = lang
        cookie = self.cookies[who]
        status, response, body = http_request(
            self.server.url(self.scope() + "/detection"), method="POST",
            data=with_csrf(cookie, form), cookie=cookie, extra_headers=headers)
        return status, response, body.decode("utf-8", "replace")

    def config_bytes(self):
        path = device_config.device_config_path(self.owner_dir())
        if not os.path.exists(path):
            return None
        with open(path, "rb") as handle:
            return handle.read()

    def config(self):
        raw = self.config_bytes()
        return json.loads(raw) if raw else {}

    def position(self):
        conn = fleet_db.connect(self.state_dir)
        try:
            return fleet_db.frame_position(conn, self.fleet.owner_device)
        finally:
            conn.close()

    def location_rows(self):
        conn = fleet_db.connect(self.state_dir)
        try:
            return [dict(r) for r in fleet_db.list_locations(conn)]
        finally:
            conn.close()


@pytest.fixture(autouse=True)
def _no_kill_switch(monkeypatch):
    monkeypatch.delenv(detection.LEGACY_GEOFENCE_ENV, raising=False)


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


def _fold(text):
    stripped = "".join(
        c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    return " ".join(stripped.casefold().split())


def _text(markup):
    stripped = re.sub(r"<(script|style)\b.*?</\1>", " ", markup, flags=re.S)
    return html.unescape(re.sub(r"<[^>]+>", " ", stripped))


def _attrs(tag):
    return dict(re.findall(r'([\w-]+)="([^"]*)"', tag))


def _tag(markup, pattern):
    return re.search(pattern, markup).group(0)


def _position_form(**extra):
    form = {"action": "save_place", "mode": "position", "latitude": "43.2965",
            "longitude": "5.3698", "radius_km": "9", "place_label": "Marseille",
            "timezone": PARIS}
    form.update(extra)
    return form


def _runway_form(**extra):
    form = {"action": "save_place", "mode": "runway", "airport": "LFPG",
            "runway": "08L/26R", "latitude": "", "longitude": "", "place_label": "",
            "timezone": PARIS}
    form.update(extra)
    return form


def _save_place(rig, name="Home", lat=48.8566, lon=2.3522):
    conn = fleet_db.connect(rig.state_dir)
    try:
        fleet_db.save_frame_position(
            conn, rig.fleet.owner_device, name, lat, lon, PARIS,
            rig.fleet.owner_id, False)
    finally:
        conn.close()


# --- structure ----------------------------------------------------------------


def test_the_cards_come_in_the_specified_order(rig):
    _s, _h, page = rig.get("owner", rig.scope() + "/detection")
    marks = ['id="place-map"', 'id="place-search"', 'id="place-mode-runway"',
             'id="airports-heading"', 'id="place-radius"', 'id="details"',
             'data-dirty-bar', 'id="place-info"', 'id="place-locate"']
    positions = [page.index(mark) for mark in marks]
    assert positions == sorted(positions)
    assert "<title>Location and detection" in page
    assert ">Save</button>" in page


def test_the_page_is_titled_and_labelled_in_french(rig):
    _s, _h, page = rig.get("owner", rig.scope() + "/detection", lang="fr")
    text = _text(page)
    assert "<title>Lieu et détection" in page
    for needle in ("Aéroports français", "Filtrer les aéroports", "Aéroport",
                   "Ma position", "Piste à suivre", "Rayon (km)",
                   "Coordonnées et fuseau horaire", "Nom du lieu", "Fuseau horaire",
                   "Enregistrer",
                   "Rechercher un aéroport ou une adresse", "Utiliser ma position",
                   "Retour à la carte", "contributeurs d’OpenStreetMap"):
        assert needle in text, needle
    assert 'aria-label="À propos de cette carte"' in page


def test_the_summary_line_and_the_saved_settings_disclosure_are_gone(rig):
    _save_place(rig, "Home", 48.856614, 2.352222)
    _s, _h, page = rig.get("owner", rig.scope() + "/detection")
    text = _text(page)
    for gone in ("place-derived", "place-saved", "place-more", "Saved setting",
                 "Home · 48.8566, 2.3522", "No place chosen yet"):
        assert gone not in page and gone not in text, gone
    assert 'name="place_label"' in page and 'value="Home"' in page
    assert 'name="latitude"' in page and 'value="48.8566"' in page


def test_the_catalogue_travels_once_in_list_order_and_scriptless_browsers_get_a_short_list(rig):
    _s, _h, page = rig.get("owner", rig.scope() + "/detection")
    catalogue = airports.load_catalogue()
    # The full list is filled from the map's JSON; the page itself carries
    # the first airports inside <noscript> and an empty list for the script.
    assert re.search(r'<ul class="place-airports"[^>]*data-airport-fill[^>]*></ul>', page)
    noscript = re.search(r"<noscript><ul class=\"place-airports\".*?</ul></noscript>", page, re.S)
    anchors = re.findall(r'<a class="place-airport__link"[^>]*>', noscript.group(0))
    assert len(anchors) == place_page.NOSCRIPT_AIRPORTS
    assert len(re.findall(r'<a class="place-airport__link"', page)) == len(anchors)
    rows = [_attrs(a) for a in anchors]
    # The position and name of every airport travel once, in the map's JSON.
    assert not {"data-lat", "data-lon", "data-name", "data-iata"} & set(rows[0])
    map_rows = json.loads(html.unescape(re.search(r'data-airports="([^"]*)"', page).group(1)))
    assert {row[0] for row in map_rows} == set(catalogue)
    airport = catalogue["LFPG"]
    assert ["LFPG", airport.iata, airport.name, airport.municipality,
            round(airport.lat, 4), round(airport.lon, 4)] in map_rows
    towns = [_fold(row[3]) for row in map_rows]
    assert towns == sorted(towns)
    assert [r["data-icao"] for r in rows] == [row[0] for row in map_rows[:len(rows)]]
    count = re.search(r'data-filter-count[^>]*>([^<]*)<', page).group(1)
    assert count == "%d of %d shown" % (len(rows), len(catalogue))


def test_the_filter_narrows_the_list_server_side_and_script_side_hooks_exist(rig):
    _s, _h, page = rig.get("owner", rig.scope() + "/detection?q=nimes")
    icaos = re.findall(r'data-icao="([A-Z0-9]+)"', page)
    expected = {a.icao for a in airports.search_airports("nimes", 1000)[0]}
    assert icaos and set(icaos) == expected and len(icaos) == len(expected)
    assert 'data-filter-input' in page and 'data-filter-count' in page
    assert len(re.findall(r'data-filter-text="', page)) == len(icaos)


def test_the_map_data_contract_without_a_place(rig):
    _s, _h, page = rig.get("owner", rig.scope() + "/detection")
    tag = _tag(page, r'<div id="place-map"[^>]*>')
    attrs = _attrs(tag)
    assert "place-map" in attrs["class"] and "js-gate" in attrs["class"]
    assert (attrs["data-lat"], attrs["data-lon"], attrs["data-zoom"]) == ("", "", "5")
    assert attrs["data-mode"] == "position" and attrs["data-airport"] == "LFPO"
    assert attrs["data-radius-km"] == "9"
    assert attrs["tabindex"] == "0" and attrs["role"] == "group"
    _s, _h, runway = rig.get("owner", rig.scope() + "/detection?mode=runway")
    assert _attrs(_tag(runway, r'<div id="place-map"[^>]*>'))["data-mode"] == "runway"
    assert 'id="place-status"' in page and 'aria-live="polite"' in page


def test_the_map_data_contract_with_a_saved_place_and_with_an_airport(rig):
    _save_place(rig, "Home", 48.8566, 2.3522)
    device_config.save_device_config(
        rig.owner_dir(), detection={"mode": "position", "radius_km": 12})
    _s, _h, page = rig.get("owner", rig.scope() + "/detection")
    attrs = _attrs(_tag(page, r'<div id="place-map"[^>]*>'))
    assert (attrs["data-lat"], attrs["data-lon"], attrs["data-zoom"]) == (
        "48.8566", "2.3522", "12")
    assert attrs["data-mode"] == "position" and attrs["data-radius-km"] == "12"
    _s, _h, page = rig.get("owner", rig.scope() + "/detection?airport=LFPG")
    attrs = _attrs(_tag(page, r'<div id="place-map"[^>]*>'))
    airport = airports.find_airport("LFPG")
    assert attrs["data-airport"] == "LFPG" and attrs["data-zoom"] == "12"
    assert attrs["data-lat"] == "%.4f" % airport.lat
    assert attrs["data-mode"] == "runway"


def test_the_script_only_controls_are_gated_and_the_fallback_is_present(rig):
    _s, _h, page = rig.get("owner", rig.scope() + "/detection")
    for pattern in (r'<form class="place-search js-gate"[^>]*>',
                    r'<button type="button" class="place-locate[^"]*js-gate"[^>]*>'):
        assert re.search(pattern, page), pattern
    assert "The map needs scripts and a network connection." in _text(page)
    assert re.search(r'<details id="details"[^>]* open>', page)
    assert "map-ready" not in page


def test_the_details_controls_are_always_in_the_page(rig):
    _s, _h, page = rig.get("owner", rig.scope() + "/detection")
    lat = _attrs(_tag(page, r'<input type="number" id="place-lat"[^>]*>'))
    lon = _attrs(_tag(page, r'<input type="number" id="place-lon"[^>]*>'))
    for attrs in (lat, lon):
        assert attrs["step"] == "0.0001" and attrs["inputmode"] == "decimal"
        assert attrs["form"] == "detection-form"
    label = _attrs(_tag(page, r'<input type="text" id="place-label"[^>]*>'))
    assert label["maxlength"] == "60" and label["name"] == "place_label"
    radius = _attrs(_tag(page, r'<input type="number" id="place-radius"[^>]*>'))
    assert (radius["min"], radius["max"], radius["step"]) == ("2", "28", "1")
    zone = re.search(r'<select id="place-timezone".*?</select>', page, re.S).group(0)
    assert re.findall(r'<option value="([^"]*)"', zone)[0] == PARIS
    for control in ("place-mode-runway", "place-mode-area"):
        assert 'id="%s"' % control in page


def test_one_post_form_with_the_token_and_the_action(rig):
    _s, _h, page = rig.get("owner", rig.scope() + "/detection")
    forms = [
        (opening, inner) for opening, inner in re.findall(r"(<form[^>]*>)(.*?)</form>", page, re.S)
        if 'method="post"' in opening and "/detection" in opening]
    assert len(forms) == 1
    opening, inner = forms[0]
    assert 'action="%s/detection"' % rig.scope() in opening
    assert re.findall(r'name="csrf_token" value="([^"]+)"', inner)
    assert '<input type="hidden" name="action" value="save_place">' in inner


def test_no_saved_locations_interface_remains(rig):
    _save_place(rig)
    for lang in (None, "fr"):
        _s, _h, page = rig.get("owner", rig.scope() + "/detection", lang=lang)
        text = _text(page)
        for gone in ("Your locations", "Add a location", "Vos lieux", "Ajouter un lieu",
                     "Edit location", "Modifier le lieu"):
            assert gone not in text
        for gone in ('name="location_id"', 'id="detection-location"', "location-picker",
                     'id="location-form"'):
            assert gone not in page


# --- what to follow -----------------------------------------------------------


def test_the_legacy_orly_runway_shows_as_the_matching_catalogue_runway(rig):
    _s, _h, page = rig.get("owner", rig.scope() + "/detection")
    checked = re.search(
        r'<input type="radio" name="runway" value="([^"]+)"[^>]*checked', page)
    assert checked.group(1) == "07/25"
    assert '<input type="hidden" name="airport" value="LFPO"' in page


def test_the_legacy_choice_is_posted_back_unchanged(rig):
    device_config.save_device_config(rig.owner_dir(), tracked_runway="06-24")
    status, _h, _b = rig.post("owner", _runway_form(airport="LFPO", runway="06/24"))
    assert status == 303
    stored = rig.config()
    assert stored["tracked_runway"] == "06-24" and "detection" not in stored


def test_choosing_an_airport_by_url_selects_it_and_fills_the_pin(rig):
    _s, _h, page = rig.get("owner", rig.scope() + "/detection?airport=LFPG")
    airport = airports.find_airport("LFPG")
    assert 'value="%.4f"' % airport.lat in _tag(page, r'<input type="number" id="place-lat"[^>]*>')
    assert 'value="%s"' % html.escape(airport.name) in _tag(
        page, r'<input type="text" id="place-label"[^>]*>')
    checked = re.search(r'name="runway" value="([^"]+)"[^>]*checked', page)
    assert checked.group(1) == airport.runways[0].designator
    assert re.search(r'id="place-mode-runway" value="runway"[^>]*checked', page)


def test_a_url_airport_leaves_the_stored_place_when_it_is_the_saved_airport(rig):
    _save_place(rig, "My view", 48.7, 2.4)
    device_config.save_device_config(
        rig.owner_dir(), detection={"mode": "runway", "airport": "LFPG", "runway": "09L/27R"})
    _s, _h, page = rig.get("owner", rig.scope() + "/detection?airport=LFPG")
    assert 'value="My view"' in page
    assert re.search(r'name="runway" value="09L/27R"[^>]*checked', page)


def test_hostile_text_in_the_url_is_escaped(rig):
    payload = urllib.parse.quote('"><script>alert(1)</script>')
    for query in ("q=" + payload, "airport=" + payload, "radius_km=" + payload,
                  "mode=" + payload):
        status, _h, page = rig.get("owner", rig.scope() + "/detection?" + query)
        assert status == 200
        assert "<script>alert(1)" not in page


# --- saving without a script --------------------------------------------------


def test_a_runway_save_stores_the_choice_and_the_airport_position(rig):
    status, response, _b = rig.post("owner", _runway_form())
    assert status == 303
    assert "flash=place_saved" in response["Location"]
    assert rig.config()["detection"] == {
        "mode": "runway", "airport": "LFPG", "runway": "08L/26R"}
    place = rig.position()
    airport = airports.find_airport("LFPG")
    assert (place["name"], place["latitude"], place["longitude"]) == (
        airport.name, round(airport.lat, 4), round(airport.lon, 4))


def test_a_runway_save_with_the_typed_pin_label_and_zone(rig):
    form = _runway_form(
        latitude="49.0123", longitude="2.5", place_label="Terrace", timezone="Indian/Reunion")
    status, _h, _b = rig.post("owner", form)
    assert status == 303
    place = rig.position()
    assert (place["name"], place["latitude"], place["longitude"]) == ("Terrace", 49.0123, 2.5)
    assert rig.config()["timezone"] == "Indian/Reunion"


def test_an_area_save_stores_the_pin_radius_label_and_zone(rig):
    status, _h, _b = rig.post("owner", _position_form(radius_km="14"))
    assert status == 303
    assert rig.config()["detection"] == {"mode": "position", "radius_km": 14}
    place = rig.position()
    assert (place["name"], place["latitude"], place["longitude"]) == (
        "Marseille", 43.2965, 5.3698)


def test_the_saved_toast_names_the_place_in_both_languages(rig):
    _s, response, _b = rig.post("owner", _position_form(place_label="Marseille"))
    target = response["Location"]
    _s, _h, page = rig.get("owner", target)
    assert "Location saved" in _text(page) and "Detection now follows Marseille" in _text(page)
    _s, _h, page = rig.get("owner", target, lang="fr")
    assert "Lieu enregistré" in _text(page) and "suit désormais Marseille" in _text(page)


REFUSALS = [
    (_position_form, {"latitude": "60"}, "latitude", "place-lat"),
    (_position_form, {"longitude": "20"}, "latitude", "place-lat"),
    (_position_form, {"latitude": "abc"}, "latitude", "place-lat"),
    (_position_form, {"radius_km": "1"}, "radius_km", "place-radius"),
    (_position_form, {"radius_km": "29"}, "radius_km", "place-radius"),
    (_position_form, {"radius_km": "9.5"}, "radius_km", "place-radius"),
    (_position_form, {"place_label": "x" * 61}, "place_label", "place-label"),
    (_position_form, {"timezone": "Mars/Olympus"}, "timezone", "place-timezone"),
    (_runway_form, {"runway": "99/99"}, "runway", "place-runway"),
]


@pytest.mark.parametrize("make,change,field,anchor", REFUSALS)
def test_a_refused_value_returns_400_with_the_error_beside_its_field(
        rig, make, change, field, anchor):
    before = rig.config_bytes()
    status, _h, page = rig.post("owner", make(**change))
    assert status == 400
    assert re.search(r'<p class="field-error text-label" id="%s-error" role="alert">' % anchor, page)
    assert rig.config_bytes() == before
    assert rig.position() is None and rig.location_rows() == []


@pytest.mark.parametrize("anchor,field", [
    ("place-lat", "latitude"), ("place-radius", "radius_km"), ("place-label", "place_label"),
    ("place-timezone", "timezone")])
def test_a_refused_control_is_marked_invalid_and_described(rig, anchor, field):
    bad = {"latitude": "60", "radius_km": "1", "place_label": "x" * 61,
           "timezone": "Mars/Olympus"}[field]
    _s, _h, page = rig.post("owner", _position_form(**{field: bad}))
    tag = _tag(page, r'<(?:input|select) [^>]*id="%s"[^>]*>' % anchor)
    attrs = _attrs(tag)
    assert attrs["aria-invalid"] == "true"
    assert "%s-error" % anchor in attrs["aria-describedby"].split()


def test_a_refused_save_keeps_the_entered_values_escaped(rig):
    hostile = '"><img src=x onerror=alert(1)>'
    status, _h, page = rig.post("owner", _position_form(latitude="60", place_label=hostile))
    assert status == 400
    assert "<img src=x" not in page
    assert html.escape(hostile) in page
    assert 'value="60"' in _tag(page, r'<input type="number" id="place-lat"[^>]*>')
    assert re.search(r'data-dirty-carried="%s/detection"' % rig.scope(), page)


def test_a_save_without_the_token_is_refused(rig):
    cookie = rig.cookies["owner"]
    status, _r, _b = http_request(
        rig.server.url(rig.scope() + "/detection"), method="POST",
        data=urllib.parse.urlencode(_position_form()).encode(), cookie=cookie,
        extra_headers={"Origin": rig.server.base_url()})
    assert status == 403
    assert rig.position() is None


# --- policy headers on every re-render ----------------------------------------


def _policy(response):
    return (response["Content-Security-Policy"], response["Permissions-Policy"])


def test_every_re_render_sends_the_map_policy(rig):
    status, response, _b = rig.post("owner", {"action": "save_detection", "mode": "sideways"})
    assert status == 200 and _policy(response) == MAP_POLICY
    status, response, _b = rig.post("owner", {
        "action": "save_location", "location_name": "", "latitude": "1",
        "longitude": "1", "timezone": PARIS, "location_id": ""})
    assert status == 200 and _policy(response) == MAP_POLICY
    status, response, _b = rig.post("owner", _position_form(radius_km="1"))
    assert status == 400 and _policy(response) == MAP_POLICY
    status, response, _b = rig.get("owner", rig.scope() + "/detection")
    assert status == 200 and _policy(response) == MAP_POLICY


def test_other_users_get_nothing(rig):
    assert rig.get("other", rig.scope() + "/detection")[0] == 404
    status, _r, _b = rig.post("other", _position_form())
    assert status == 404
    assert rig.position() is None
