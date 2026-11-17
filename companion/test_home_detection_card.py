"""Home's Detection card names the mode the frame is really in (position or
airport and runway), what it follows, and links to the Location page; it
follows the frame it is rendered for, reads the same stored setting the
frame uses, escapes the place name, and is shown to the same people who can
open Home (administrator, owner, co-manager) and to nobody else."""
import html
import re

import pytest

from access_matrix_support import (
    ADMIN_EMAIL, OTHER_EMAIL, OWNER_EMAIL, seed_matrix_fleet)
from companion import device_scope
from companion_app_server import (
    InProcessAppServer, http_request, session_cookie_for_state_dir)
from server import device_config, fleet_db

CARD = re.compile(
    r'<section class="group-block home-section home-detection" aria-labelledby="home-detection">'
    r'(.*?)</section>', re.S)


class Rig:
    def __init__(self, state_dir, server, fleet, cookies, state_dirs):
        self.state_dir, self.server, self.fleet = state_dir, server, fleet
        self.cookies, self.state_dirs = cookies, state_dirs

    def home(self, who, device=None, lang=None):
        device = device or self.fleet.owner_device
        headers = {"Accept-Language": lang} if lang else None
        status, _r, body = http_request(
            self.server.url("/devices/%s/" % device), cookie=self.cookies[who],
            extra_headers=headers)
        return status, body.decode("utf-8", "replace")

    def card(self, who="owner", device=None, lang="en"):
        status, page = self.home(who, device, lang)
        assert status == 200
        found = CARD.search(page)
        assert found, "no Detection card on Home"
        return found.group(1)

    def configure(self, detection, device=None):
        device = device or self.fleet.owner_device
        device_config.save_device_config(self.state_dirs[device], detection=detection)

    def place(self, name, lat=48.7316, lon=2.4217, device=None):
        device = device or self.fleet.owner_device
        conn = fleet_db.connect(self.state_dir)
        try:
            loc = fleet_db.add_location(
                conn, name, lat, lon, "Europe/Paris", owner_user_id=self.fleet.owner_id)
            conn.execute("UPDATE devices SET location_id = ? WHERE id = ?", (loc, device))
            conn.commit()
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
    yield Rig(state_dir, server, fleet, cookies, state_dirs)
    server.stop()


def _text(markup):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", markup)).split())


def _href(card):
    return re.search(r'<a class="row__main" href="([^"]*)"', card).group(1)


def test_position_mode_names_the_place_and_the_radius(rig):
    rig.place("Maison")
    rig.configure({"mode": "position", "radius_km": 9})
    card = rig.card()
    assert "Position mode" in _text(card)
    assert "Aircraft within 9 km of Maison" in _text(card)
    assert "icon-locate" in card


def test_runway_mode_names_the_airport_and_the_runway(rig):
    rig.configure({"mode": "runway", "airport": "LFPG", "runway": "08L/26R"})
    text = _text(rig.card())
    assert "Airport & runway mode" in text
    assert "Runway 08L/26R at" in text and "(CDG)" in text


def test_a_frame_with_no_choice_shows_the_orly_runway_it_follows(rig):
    text = _text(rig.card())
    assert "Airport & runway mode" in text and "Runway 07/25 at" in text


def test_position_mode_without_a_place_says_which_runway_it_follows(rig):
    rig.configure({"mode": "position", "radius_km": 9})
    card = rig.card()
    text = _text(card)
    assert "No place set" in text and "Position mode needs a place" in text
    assert "runway 07/25" in text
    assert "icon-warning" in card


def test_a_place_outside_france_counts_as_no_place(rig):
    rig.place("New York", 40.7, -74.0)
    rig.configure({"mode": "position", "radius_km": 9})
    assert "No place set" in _text(rig.card())


def test_the_card_is_in_french_when_the_browser_asks_for_it(rig):
    rig.place("Maison")
    rig.configure({"mode": "position", "radius_km": 9})
    status, page = rig.home("owner", lang="fr")
    text = _text(CARD.search(page).group(1))
    assert status == 200
    assert "Détection" in text and "Mode position" in text
    assert "Avions à moins de 9 km de Maison" in text
    assert "Modifier la détection" in text


def test_the_card_links_to_the_location_page_of_the_same_frame(rig):
    card = rig.card()
    assert _href(card) == "/devices/%s/detection" % rig.fleet.owner_device
    assert "Edit detection" in _text(card)


def test_the_card_follows_the_frame_it_is_rendered_for(rig):
    rig.configure({"mode": "runway", "airport": "LFPG", "runway": "08L/26R"})
    owner = _text(rig.card())
    other = _text(rig.card("other", rig.fleet.other_device))
    assert "Runway 08L/26R" in owner
    assert "Runway 07/25" in other


def test_a_place_name_is_escaped(rig):
    rig.place("<b>Maison</b>")
    rig.configure({"mode": "position", "radius_km": 9})
    card = rig.card()
    assert "<b>Maison" not in card
    assert "&lt;b&gt;Maison" in card


def test_an_administrator_sees_the_owners_place(rig):
    rig.place("Maison")
    rig.configure({"mode": "position", "radius_km": 9})
    text = _text(rig.card("admin"))
    assert "Aircraft within 9 km of Maison" in text


def test_a_co_manager_sees_the_owners_place_and_the_same_link(rig):
    rig.place("Maison")
    rig.configure({"mode": "position", "radius_km": 9})
    conn = fleet_db.connect(rig.state_dir)
    try:
        fleet_db.add_co_manager(conn, rig.fleet.owner_device, rig.fleet.other_id, None)
        conn.commit()
    finally:
        conn.close()
    card = rig.card("other", rig.fleet.owner_device)
    assert "Aircraft within 9 km of Maison" in _text(card)
    assert _href(card) == "/devices/%s/detection" % rig.fleet.owner_device


def test_a_simple_user_gets_no_card_for_someone_elses_frame(rig):
    status, page = rig.home("other", rig.fleet.owner_device)
    assert status != 200
    assert "home-detection" not in page
