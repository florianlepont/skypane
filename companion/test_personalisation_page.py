"""The Personalisation page over a real in-process server: the title, the
one navigation and its four views (Departures at /display, then
/display/arrivals, /display/special-looks and /display/calendar, one view each)
for an administrator and a user, the Look radio cards and their save, the
retired Screen address, the absence of any Refresh card and of a user's wake interval, and
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
    # These tests cover the classic look picker; the giant layouts' pairing
    # picker has its own tests.
    device_config.save_device_config(state_dirs[fleet.owner_device], layout="classic")
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

SECTIONS = ("Departures", "Arrivals", "Layout", "Special looks", "Calendar")
SECTION_TITLES = ("Look", "Look", "Layout", "Special looks", "Calendar")
FR_TITLES = ("Départs", "Arrivées", "Disposition", "Allures spéciales", "Calendrier")
SEEDED = {
    "quiet_hours_enabled": True, "quiet_hours_start": "21:00", "quiet_hours_end": "05:00",
    "timezone": "America/Martinique", "wake_interval_s": 900, "theme": "band_red_field",
    "calendar_theme_id": "black",
    "detection": {"mode": "runway", "airport": "LFPG", "runway": "08L/26R"},
}


def _seed(rig):
    device_config.save_device_config(rig.owner_dir(), **SEEDED)


VIEW_PATHS = {
    "departures": "/display", "arrivals": "/display/arrivals", "layout": "/display/layout",
    "special-looks": "/display/special-looks", "calendar": "/display/calendar"}
VIEW_IDS = {
    "departures": "personalisation-look", "arrivals": "personalisation-look",
    "layout": "personalisation-layout", "special-looks": "personalisation-special-looks", "calendar": "personalisation-calendar"}


def _display(rig, who="owner", lang=None, view="departures"):
    status, body = rig.get(who, rig.scope() + VIEW_PATHS[view], lang=lang)
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
def test_the_title_the_nav_and_each_view_come_in_order(rig, who):
    _seed(rig)
    expected_links = [rig.scope() + VIEW_PATHS[v] for v in VIEW_PATHS]
    for position, view in enumerate(VIEW_PATHS):
        root = parse_html(_display(rig, who, view=view))
        assert root.select_one("h1.page-title").text() == "Personalisation"
        nav = root.select_one("nav.personalisation-nav")
        assert nav.attrs["aria-label"] == "Personalisation sections"
        links = nav.select("a")
        assert [a.attrs["href"] for a in links] == expected_links
        assert [a.text() for a in links] == list(SECTIONS)
        assert all(a.select_one("svg") for a in links)
        assert [i for i, a in enumerate(links) if a.attrs.get("aria-current") == "page"] == [position]
        sections = root.select("div.personalisation__view > section")
        assert [c.attrs["id"] for c in sections] == [VIEW_IDS[view]]
        assert [c.attrs["data-dirty-section"] for c in sections] == [SECTION_TITLES[position]]
        assert sections[0].select_one("h2").text() == SECTION_TITLES[position]
        assert not sections[0].select(".personalisation-card__current")


def test_the_look_view_names_the_saved_look_and_only_the_look_picker_is_on_it(rig):
    _seed(rig)
    root = parse_html(_display(rig))
    assert root.select_one(".look-pick img.look-frame__image").attrs["alt"].endswith(
        "Red, stripe on soft")
    assert not root.select(".look-frame__caption")
    assert not root.select(".look-pick__customise")
    assert root.select_one("[data-look-sheet][data-look-inline]") is not None
    assert not root.select("button[data-look-tab]")
    assert root.select_one("[data-look-initial]").attrs["data-look-initial"] == "departures"
    assert not root.select("section.personalisation-card")
    assert not root.select("[data-special-add]")
    assert not root.select('input[name="calendar_theme_id"]')


def test_the_page_speaks_french(rig):
    expected = {
        "departures": "Allure", "arrivals": "Allure", "layout": "Disposition",
        "special-looks": "Allures spéciales",
        "calendar": "Calendrier"}
    for view, title in expected.items():
        page = _display(rig, lang="fr", view=view)
        root = parse_html(page)
        assert root.select_one("h1.page-title").text() == "Personnalisation"
        nav = root.select_one("nav.personalisation-nav")
        assert nav.attrs["aria-label"] == "Sections de personnalisation"
        assert [a.text() for a in nav.select("a")] == list(FR_TITLES)
        assert root.select_one("div.personalisation__view h2").text() == title


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
    root = parse_html(_display(rig))
    assert root.select_one(".look-pick img.look-frame__image").attrs["alt"].endswith("Black, solid")
    assert [
        r.attrs["value"] for r in root.select('input[name="theme"][checked]')] == ["black"]


def test_the_retired_screen_address_redirects_to_the_departures_view(rig):
    status, response, _body = http_request(
        rig.server.url(rig.scope() + "/display/screen"), cookie=rig.cookies["owner"])
    assert status == 303
    assert response["Location"] == rig.scope() + "/display"
    status, response, _body = http_request(
        rig.server.url("/display/screen"), cookie=rig.cookies["admin"])
    assert status == 303 and response["Location"] == "/display"
    status, _body = rig.get("owner", rig.scope() + "/display/arrivals")
    assert status == 200
    _status, body = rig.get("owner", rig.scope() + "/display")
    assert "personalisation-screen" not in body and "/display/screen" not in body


def test_the_arrivals_view_shows_the_arrivals_picture_and_hides_the_departures_one(rig):
    _seed(rig)
    root = parse_html(_display(rig, view="arrivals"))
    assert root.select_one("[data-look-initial]").attrs["data-look-initial"] == "arrivals"
    panels = {p.attrs["data-look-panel"]: p for p in root.select("[data-look-panel]")}
    assert "hidden" in panels["departures"].attrs and "hidden" not in panels["arrivals"].attrs
    assert panels["arrivals"].select_one('input[value=""][name="theme_arriving"]') is not None
    fields = {i.attrs["name"] for i in root.select('input[type="radio"]') if "name" in i.attrs}
    assert {"theme", "theme_arriving"} <= fields
    departures = parse_html(_display(rig))
    panels = {p.attrs["data-look-panel"]: p for p in departures.select("[data-look-panel]")}
    assert "hidden" in panels["arrivals"].attrs and "hidden" not in panels["departures"].attrs


@pytest.mark.parametrize("who", ["owner", "admin"])
def test_no_refresh_card_and_no_place_zone_quiet_or_led_control(rig, who):
    page = "".join(_display(rig, who, view=view) for view in VIEW_PATHS)
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
    its four views are Departures, Arrivals, Special looks, Calendar"""
    roots = {view: parse_html(_display(rig, who, lang=lang, view=view)) for view in VIEW_PATHS}
    names = {
        c.attrs["name"] for root in roots.values() for tag in ("input", "select", "textarea")
        for c in root.select(tag) if "name" in c.attrs}
    assert not names & set(FORBIDDEN_CONTROL_NAMES), names & set(FORBIDDEN_CONTROL_NAMES)
    radios = roots["departures"].select('#personalisation-look input[type="radio"][name="theme"]')
    assert len(radios) == len(device_config.THEME_IDS)
    cards = [
        c for root in roots.values() for c in root.select("div.personalisation__view > section")]
    assert [c.attrs["id"] for c in cards] == [
        "personalisation-look", "personalisation-look", "personalisation-layout",
        "personalisation-special-looks", "personalisation-calendar"]
    titles = [c.select_one("h2").text() for c in cards]
    for word in FORBIDDEN_WORDS[lang]:
        assert word not in titles, (word, titles)
        assert not [
            label for root in roots.values() for label in root.select("label")
            if label.text().strip() == word]


def test_every_view_saves_back_to_its_own_address_and_a_save_changes_only_its_fields(rig):
    _seed(rig)
    for view, path in VIEW_PATHS.items():
        root = parse_html(_display(rig, view=view))
        hidden = {
            i.attrs["name"]: i.attrs["value"]
            for i in root.select('form#settings-form input[type="hidden"]')}
        assert hidden["scope"] == "display" and hidden["return_to"] == path
    status, response, _body = _settings_post(
        rig, "owner", return_to="/display/calendar", calendar_theme_id="red")
    assert status == 303
    assert response["Location"].startswith(rig.scope() + "/display/calendar")
    stored = _stored(rig)
    assert stored["calendar_theme_id"] == "red" and stored["theme"] == "band_red_field"
    status, response, _body = _settings_post(
        rig, "owner", return_to="/display/elsewhere", theme="black")
    assert response["Location"].startswith(rig.scope() + "/display?")
    assert _stored(rig)["calendar_theme_id"] == "red"


def test_a_rejected_save_redraws_the_view_it_came_from(rig):
    _seed(rig)
    status, _response, body = _settings_post(
        rig, "owner", return_to="/display/calendar", calendar_theme_id="not-a-theme")
    assert status == 200
    root = parse_html(body)
    assert root.select("div.personalisation__view > .form-view form[data-calendar-look]")
    assert _stored(rig)["calendar_theme_id"] == "black"


def test_adding_and_removing_a_special_look_return_to_the_special_looks_view(rig):
    status, response, _body = rig.post(
        "owner", rig.scope() + "/settings/rules/add",
        {"rule_kind": "callsign", "rule_key": "AFR1234", "rule_theme_id": "black"})
    assert status == 303
    assert response["Location"] == rig.scope() + "/display/special-looks?flash=rule_added"
    status, response, _body = rig.post(
        "owner", rig.scope() + "/settings/rules/callsign/AFR1234/delete", {})
    assert status == 303
    assert response["Location"] == rig.scope() + "/display/special-looks?flash=rule_deleted"


def test_a_rejected_arrivals_look_redraws_the_arrivals_view(rig):
    _seed(rig)
    status, _response, body = _settings_post(
        rig, "owner", return_to="/display/arrivals", theme_arriving="not-a-theme")
    assert status == 200
    root = parse_html(body)
    assert root.select_one("[data-look-initial]").attrs["data-look-initial"] == "arrivals"
    hidden = {
        i.attrs["name"]: i.attrs["value"]
        for i in root.select('form#settings-form input[type="hidden"]')}
    assert hidden["return_to"] == "/display/arrivals"
