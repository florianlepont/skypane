"""The Personalisation page (served at /display) over a real in-process
server: the title, the On this page list and the four cards in order for an
administrator and a user, the Look radio cards and their save, the Screen
switch, the absence of any Refresh card and of a user's wake interval, and
isolation: saving Personalisation never touches the place, the time zone,
the quiet hours or the detection setting, and saving those never touches the
look, the rules, the calendar look or the wake interval.
"""
import html
import json
import os
import re

import pytest

from access_matrix_support import (
    ADMIN_EMAIL, OTHER_EMAIL, OWNER_EMAIL, seed_matrix_fleet)
from companion import device_scope, theme_preview
from companion_app_server import (
    InProcessAppServer, http_request, session_cookie_for_state_dir, with_csrf)
from companion_markup import parse_html
from server import device_config, fleet_db

PARIS = "Europe/Paris"


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

SECTIONS = ("Look", "Special looks", "Calendar", "Screen")
FR_TITLES = ("Allure", "Allures spéciales", "Calendrier", "Écran")
SEEDED = {
    "quiet_hours_enabled": True, "quiet_hours_start": "21:00", "quiet_hours_end": "05:00",
    "timezone": "America/Martinique", "wake_interval_s": 900, "theme": "band_red_field",
    "calendar_theme_id": "black",
    "detection": {"mode": "runway", "airport": "LFPG", "runway": "08L/26R"},
}


def _seed(rig):
    device_config.save_device_config(rig.owner_dir(), **SEEDED)


def _display(rig, who="owner", lang=None):
    status, body = rig.get(who, rig.scope() + "/display", lang=lang)
    assert status == 200
    return body


def _text(markup):
    stripped = re.sub(r"<(script|style)\b.*?</\1>", " ", markup, flags=re.S)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", stripped)).split())


def _settings_post(rig, who, **fields):
    form = {"scope": "display", "return_to": "/display"}
    form.update(fields)
    return rig.post(who, rig.scope() + "/settings", form)


def _stored(rig):
    return device_config.load_device_config(rig.owner_dir())


@pytest.mark.parametrize("who", ["owner", "admin"])
def test_the_title_the_nav_and_the_four_cards_come_in_order(rig, who):
    _seed(rig)
    page = _display(rig, who)
    root = parse_html(page)
    assert root.select_one("h1.page-title").text() == "Personalisation"
    nav = root.select_one("nav.personalisation__nav")
    assert nav.attrs["aria-label"] == "On this page"
    assert [a.attrs["href"] for a in nav.select("a")] == [
        "#personalisation-look", "#personalisation-special-looks",
        "#personalisation-calendar", "#personalisation-screen"]
    cards = root.select("section.personalisation-card")
    assert [c.select_one("h2").text() for c in cards] == list(SECTIONS)
    assert [c.attrs["data-dirty-section"] for c in cards] == list(SECTIONS)
    currents = [c.select_one(".personalisation-card__current").text() for c in cards[:3]]
    assert currents == [
        "Current: Red, stripe on soft", "Current: No special looks yet",
        "Current: No calendar connected"]
    shown = [
        span.text() for span in cards[3].select(".personalisation-card__current span")
        if "hidden" not in span.attrs]
    assert shown == ["Current: On"]


def test_the_page_speaks_french(rig):
    page = _display(rig, lang="fr")
    root = parse_html(page)
    assert root.select_one("h1.page-title").text() == "Personnalisation"
    assert root.select_one("nav.personalisation__nav").attrs["aria-label"] == "Sur cette page"
    assert [c.select_one("h2").text() for c in root.select("section.personalisation-card")] == list(
        FR_TITLES)
    assert "Personnaliser le style" in _text(page)
    assert "Actuel : Allumé" in html.unescape(page)


def test_the_look_cards_are_native_radios_with_a_preview_and_a_selected_word(rig):
    _seed(rig)
    root = parse_html(_display(rig))
    grid = root.select_one("div.look-pick__grid")
    assert grid.attrs["role"] == "radiogroup"
    cards = grid.select("label")
    radios = [c.select_one("input") for c in cards]
    assert sorted(r.attrs["value"] for r in radios) == sorted(device_config.THEME_IDS)
    for card, radio in zip(cards, radios):
        assert radio.attrs["name"] == "theme" and radio.attrs["form"] == "settings-form"
        assert radio.attrs["type"] == "radio"
        image = card.select_one("img")
        assert (theme_preview.FRAME_PREVIEW_ROUTE_PREFIX + radio.attrs["value"] + ".png") in image.attrs["src"]
        assert image.attrs["alt"]
        assert card.select_one(".look-pick__name").text()
        assert "Selected" in card.select_one(".runway-card__check").text()
    assert [r.attrs["value"] for r in radios if "checked" in r.attrs] == ["band_red_field"]


def test_tapping_a_look_then_save_persists_it_and_the_page_names_it(rig):
    _seed(rig)
    status, response, _body = _settings_post(rig, "owner", theme="black")
    assert status == 303
    assert response["Location"].endswith("/display?flash=saved") or "/display" in response["Location"]
    assert _stored(rig)["theme"] == "black"
    assert "Current: Black, solid" in _text(_display(rig))


def test_the_screen_card_holds_the_instant_switch_with_its_state(rig):
    root = parse_html(_display(rig))
    card = root.select_one("#personalisation-screen")
    form = card.select_one("form[data-quick-switch]")
    assert form.attrs["action"].endswith("/quick/display")
    fields = {i.attrs["name"]: i.attrs["value"] for i in form.select("input")}
    assert fields["return_to"] == "/display"
    switch = card.select_one("button.switch")
    assert switch.attrs["aria-checked"] == "true"
    assert switch.attrs["aria-labelledby"] == card.select_one("h2").attrs["id"]
    device_config.save_device_config(rig.owner_dir(), display_enabled=False)
    card = parse_html(_display(rig)).select_one("#personalisation-screen")
    assert card.select_one("button.switch").attrs["aria-checked"] == "false"
    assert "Current: Off" in card.text()


@pytest.mark.parametrize("who", ["owner", "admin"])
def test_no_refresh_card_and_no_place_zone_quiet_or_led_control(rig, who):
    page = _display(rig, who)
    for absent in ("wake_interval_s", "wake-interval", "Refresh", 'name="timezone"',
                   'name="quiet_hours_start"', 'name="led_enabled"', 'name="latitude"'):
        assert absent not in page, absent


def test_a_users_posted_wake_interval_is_refused_and_the_interval_stays(rig):
    _seed(rig)
    for scope in ("display", "device", "all"):
        status, _response, _body = _settings_post(
            rig, "owner", scope=scope, wake_interval_s="60", theme="black")
        assert status == 303
        assert _stored(rig)["wake_interval_s"] == 900


def test_saving_personalisation_changes_only_the_look(rig):
    """look and screen saves leave quiet hours, the time zone, the position row and the detection
    setting identical, even with crafted fields for them in the post"""
    _seed(rig)
    before = _stored(rig)
    position = _position_row(rig)
    _settings_post(rig, "owner", theme="black", display_enabled="on")
    _settings_post(
        rig, "owner", theme="white", quiet_hours_enabled="on", quiet_hours_start="10:00",
        quiet_hours_end="11:00", timezone="Europe/Paris", location_id="1")
    rig.post("owner", rig.scope() + "/quick/display", {"state": "off", "return_to": "/display"})
    after = _stored(rig)
    changed = {k for k in set(before) | set(after) if before.get(k) != after.get(k)}
    assert changed <= {"theme", "display_enabled"}, changed
    assert _position_row(rig) == position


def test_saving_quiet_hours_or_the_place_changes_no_look_rule_calendar_or_interval(rig):
    _seed(rig)
    before = _stored(rig)
    watched = ("theme", "theme_arriving", "calendar_theme_id", "wake_interval_s", "display_enabled")
    status, _response, _body = rig.post(
        "owner", rig.scope() + "/quick/quiet-hours/window",
        {"quiet_hours_enabled": "on", "quiet_hours_start": "22:00", "quiet_hours_end": "06:00"})
    assert status == 303
    status, _response, _body = rig.post(
        "owner", rig.scope() + "/detection",
        {"action": "save_place", "mode": "runway", "airport": "LFPG", "runway": "08L/26R"})
    assert status == 303
    after = _stored(rig)
    assert after["quiet_hours_start"] == "22:00"
    for key in watched:
        assert after.get(key) == before.get(key), key



FORBIDDEN_CONTROL_NAMES = (
    "timezone", "runway", "tracked_runway", "latitude", "longitude", "location_id", "airport",
    "quiet_hours_enabled", "quiet_hours_start", "quiet_hours_end", "wake_interval_s",
    "led_enabled", "detection")
FORBIDDEN_WORDS = {
    "en": ("Time zone", "Runway", "Quiet hours", "Refresh", "Latitude", "Airport"),
    "fr": ("Fuseau horaire", "Piste", "Heures calmes", "Actualisation", "Latitude", "Aéroport"),
}


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("who", ["owner", "admin"])
def test_personalisation_holds_no_place_runway_time_zone_or_quiet_hours_control(rig, who, lang):
    """the page offers the look as radio inputs and holds no form control or card named for the
    place, the runway, the time zone, the quiet hours or the refresh interval, in either language;
    its four cards are Look, Special looks, Calendar, Screen"""
    root = parse_html(_display(rig, who, lang=lang))
    names = {
        c.attrs["name"] for tag in ("input", "select", "textarea") for c in root.select(tag)
        if "name" in c.attrs}
    assert not names & set(FORBIDDEN_CONTROL_NAMES), names & set(FORBIDDEN_CONTROL_NAMES)
    radios = root.select('#personalisation-look input[type="radio"][name="theme"]')
    assert len(radios) == len(device_config.THEME_IDS)
    cards = root.select("section.personalisation-card")
    assert [c.attrs["id"] for c in cards] == [
        "personalisation-look", "personalisation-special-looks", "personalisation-calendar",
        "personalisation-screen"]
    titles = [c.select_one("h2").text() for c in cards]
    for word in FORBIDDEN_WORDS[lang]:
        assert word not in titles, (word, titles)
        assert not [label for label in root.select("label") if label.text().strip() == word]
