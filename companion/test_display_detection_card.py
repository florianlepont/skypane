"""The read-only Detection card on the Display and Device pages, the removed
Runway card, and the history pages' tolerance of the new runway ids, over a
real in-process server.
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
from server import device_config, fleet_db, history_db

PARIS = "Europe/Paris"
LINK_TEXT = "Change airport, runway or position"
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
        data = urllib.parse.urlencode(form).encode()
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


def _card(markup):
    """The Detection card's own markup: the one .theme-status block headed Detection or Détection."""
    match = re.search(
        r'<div class="theme-status detection-card">.*?</div>', markup, flags=re.S)
    assert match is not None, "no Detection card on the page"
    assert markup.count('detection-card"') == 1
    return match.group(0)


def _dirty_sections(markup):
    return re.findall(r'data-dirty-section="([^"]*)"', markup)


def _save_lfpg(rig):
    device_config.save_device_config(
        rig.owner_dir(), detection={"mode": "runway", "airport": "LFPG", "runway": "08L/26R"})


def _save_position(rig, radius="9"):
    home = rig.add_location("Home", 48.8566, 2.3522)
    status, _r, _b = rig.post("owner", rig.scope() + "/detection", {
        "action": "save_detection", "mode": "position",
        "location_id": str(home), "radius_km": radius})
    assert status == 303
    return home


# --- Display ----------------------------------------------------------------


def test_display_card_legacy_orly_on_the_live_frame_links_unprefixed(rig):
    status, page = rig.get("admin", "/display")
    assert status == 200
    card = _card(page)
    assert "<h2 class=\"text-heading\">Detection</h2>" in card
    assert "Runway 07/25 at Paris-Orly Airport (ORY)" in _text(card)
    assert re.search(r'<a [^>]*href="/detection"[^>]*>%s</a>' % LINK_TEXT, card)


def test_display_card_catalogue_runway_links_to_the_device_scoped_page(rig):
    _save_lfpg(rig)
    status, page = rig.get("owner", rig.scope() + "/display")
    assert status == 200
    card = _card(page)
    assert "Runway 08L/26R at Charles de Gaulle International Airport (CDG)" in _text(card)
    assert 'href="%s/detection"' % rig.scope() in card


def test_display_card_position_names_the_location_and_radius(rig):
    _save_position(rig, "12")
    _status, page = rig.get("owner", rig.scope() + "/display")
    assert "Aircraft within 12 km of Home" in _text(_card(page))


def test_display_card_escapes_a_hostile_location_name(rig):
    home = rig.add_location("<script>alert(1)</script>", 48.8566, 2.3522)
    rig.post("owner", rig.scope() + "/detection", {
        "action": "save_detection", "mode": "position",
        "location_id": str(home), "radius_km": "9"})
    for path in ("/display", "/device"):
        _status, page = rig.get("admin", rig.scope() + path)
        assert "<script>alert(1)" not in page
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in _card(page)


def test_display_card_takes_the_slot_of_the_runway_card(rig):
    _status, page = rig.get("owner", rig.scope() + "/display")
    card_at = page.index('detection-card"')
    assert page.index('id="display-look"') < card_at
    assert card_at < page.index('id="quiet-hours-group-heading"')
    assert page.index("</section>", page.index('id="display-look"')) < card_at


def test_display_card_french_uses_translated_strings_and_no_nautical_miles(rig):
    _save_position(rig)
    _status, page = rig.get("owner", rig.scope() + "/display", lang="fr")
    card = _card(page)
    assert "<h2 class=\"text-heading\">Détection</h2>" in card
    assert "Changer d’aéroport, de piste ou de position" in card
    assert "Avions à moins de 9 km de Home" in _text(card)
    assert not re.search(r"\bnm\b", _text(page), flags=re.I)


# --- Device -----------------------------------------------------------------


def test_device_card_comes_before_the_diagnostic_led_card(rig):
    _save_lfpg(rig)
    status, page = rig.get("admin", rig.scope() + "/device")
    assert status == 200
    card = _card(page)
    assert "Runway 08L/26R at Charles de Gaulle International Airport (CDG)" in _text(card)
    assert 'href="%s/detection"' % rig.scope() in card
    assert page.index('detection-card"') < page.index("Diagnostic LED")


def test_device_card_on_the_live_frame_links_unprefixed(rig):
    _status, page = rig.get("admin", "/device")
    assert re.search(r'href="/detection"', _card(page))


def test_device_page_stays_admin_only(rig):
    for who in ("owner", "other"):
        status, page = rig.get(who, rig.scope() + "/device")
        assert status == 404
        assert "detection-card" not in page


# --- No field, no dirty section, no runway post ----------------------------


@pytest.mark.parametrize("path", ["/display", "/device"])
def test_card_has_no_field(rig, path):
    _status, page = rig.get("admin", rig.scope() + path)
    card = _card(page)
    for control in ("<input", "<select", "<textarea", "<button"):
        assert control not in card
    assert "data-dirty-section" not in card
    assert 'name="tracked_runway"' not in page
    assert "Runway" not in _dirty_sections(page)
    assert 'id="runway-group-heading"' not in page and "runway-card" not in page


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


# --- Fail-safe ---------------------------------------------------------------


def test_failsafe_sentence(rig):
    device_config.save_device_config(
        rig.owner_dir(), detection={"mode": "position", "radius_km": 9})
    for path in ("/display", "/device"):
        _status, page = rig.get("admin", rig.scope() + path)
        text = _text(_card(page))
        assert "Runway 07/25 at Paris-Orly Airport (ORY)" in text
        assert "Aircraft within" not in text


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
