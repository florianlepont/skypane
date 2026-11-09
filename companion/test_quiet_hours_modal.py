"""The Quiet hours dialog on Home and the route it posts to, over a real
in-process server: the served dialog markup, the save that writes only the
three quiet-hours keys, refusals that write nothing, csrf and the outcome
for each kind of caller."""
import json
import os
import urllib.parse

import pytest

from access_matrix_support import ADMIN_EMAIL, OTHER_EMAIL, OWNER_EMAIL, seed_matrix_fleet
from companion import auth, device_scope, ui_nav
from companion_app_server import (
    InProcessAppServer, http_request, session_cookie_for_state_dir, with_csrf)
from companion_markup import flash_toast_title_detail, parse_html
import matrix_rows_place
from server import device_config, fleet_db

CO_MANAGER_EMAIL = "comanager@example.com"
WINDOW_ROUTE = "/quick/quiet-hours/window"
THREE_KEYS = ("quiet_hours_enabled", "quiet_hours_start", "quiet_hours_end")
SHAPE_MESSAGE = "Enter a time as HH:MM, for example 23:00."
HOSTILE = '"><script>alert('


class Rig:
    def __init__(self, state_dir, server, fleet, cookies, owner_dir):
        self.state_dir = state_dir
        self.server = server
        self.fleet = fleet
        self.cookies = cookies
        self.owner_dir = owner_dir

    def scope(self):
        return "/devices/%s" % self.fleet.owner_device

    def post(self, who, form, csrf=True, path=WINDOW_ROUTE):
        cookie = self.cookies.get(who)
        if cookie is None or not csrf:
            data = urllib.parse.urlencode(form).encode()
        else:
            data = with_csrf(cookie, form)
        status, response, body = http_request(
            self.server.url(self.scope() + path), method="POST", data=data, cookie=cookie,
            extra_headers={"Origin": self.server.base_url()})
        return status, response, body.decode("utf-8", "replace")

    def get(self, who, path="/", lang=None):
        cookie = self.cookies[who]
        if lang:
            cookie += "; %s=%s" % (auth.UI_LANG_COOKIE_NAME, lang)
        status, _response, body = http_request(
            self.server.url(self.scope() + path), cookie=cookie)
        return status, body.decode("utf-8", "replace")

    def config(self):
        path = device_config.device_config_path(self.owner_dir)
        with open(path, "rb") as handle:
            return json.loads(handle.read() or b"{}")


@pytest.fixture
def rig(tmp_path):
    state_dir = str(tmp_path / "state")
    server = InProcessAppServer(state_dir)
    fleet = seed_matrix_fleet(state_dir)
    conn = fleet_db.connect(state_dir)
    try:
        co_manager_id = fleet_db.add_user(conn, CO_MANAGER_EMAIL, "user")
        fleet_db.add_co_manager(conn, fleet.owner_device, co_manager_id, fleet.owner_id)
    finally:
        conn.close()
    state_dirs = {d.id: d.state_dir for d in device_scope.load_devices(state_dir)}
    owner_dir = state_dirs[fleet.owner_device]
    os.makedirs(owner_dir, exist_ok=True)
    device_config.save_device_config(
        owner_dir, theme="black", led_enabled=True, wake_interval_s=600,
        display_enabled=False, quiet_hours_enabled=True, quiet_hours_start="22:00",
        quiet_hours_end="06:30", timezone="America/Martinique")
    cookies = {
        "owner": session_cookie_for_state_dir(state_dir, OWNER_EMAIL, "user"),
        "other": session_cookie_for_state_dir(state_dir, OTHER_EMAIL, "user"),
        "admin": session_cookie_for_state_dir(state_dir, ADMIN_EMAIL, "admin"),
        "co-manager": session_cookie_for_state_dir(state_dir, CO_MANAGER_EMAIL, "user"),
        "anonymous": None,
    }
    yield Rig(state_dir, server, fleet, cookies, owner_dir)
    server.stop()


def _valid(**overrides):
    form = {"quiet_hours_enabled": "on", "quiet_hours_start": "21:15", "quiet_hours_end": "05:45"}
    form.update(overrides)
    return {key: value for key, value in form.items() if value is not None}


def _dialog(body):
    return parse_html(body).select_one("dialog#dlg-quiet-hours")


# --- the served dialog -------------------------------------------------------


@pytest.mark.parametrize("who", ["owner", "admin", "co-manager"])
def test_home_serves_the_same_dialog_for_every_role(rig, who):
    status, body = rig.get(who)
    assert status == 200
    dialog = _dialog(body)
    form = dialog.select_one("form")
    assert form.attrs["action"] == "%s%s" % (rig.scope(), WINDOW_ROUTE)
    assert "open" not in dialog.attrs
    assert dialog.select_one("#quiet-window-enabled").attrs["type"] == "checkbox"
    assert "checked" in dialog.select_one("#quiet-window-enabled").attrs
    start, end = dialog.select_one("#quiet-window-start"), dialog.select_one("#quiet-window-end")
    assert (start.attrs["value"], end.attrs["value"]) == ("22:00", "06:30")
    for field in (start, end):
        assert field.attrs["type"] == "time" and field.attrs["step"] == "300"
    assert dialog.select_one('input[name="csrf_token"]') is not None
    assert dialog.select_one('button[type="submit"]').text() == "Save quiet hours"
    assert dialog.select_one(".modal__dismiss").text() == "Close"
    assert dialog.select_one("#dlg-quiet-hours-title").text() == "Quiet hours"


def test_the_presets_are_two_cards_that_fill_both_fields(rig):
    _status, body = rig.get("owner")
    presets = _dialog(body).select(".quiet-cards button[data-quiet-preset]")
    assert [b.select_one(".quiet-card__title").text() for b in presets] == [
        "Night", "Day"]
    assert [b.select_one(".quiet-card__detail").text() for b in presets] == [
        "23:00 \u2013 07:00", "08:00 \u2013 18:00"]
    assert (presets[0].attrs["data-preset-start"], presets[0].attrs["data-preset-end"]) == (
        "23:00", "07:00")
    assert (presets[1].attrs["data-preset-start"], presets[1].attrs["data-preset-end"]) == (
        "08:00", "18:00")
    assert all("data-preset-enabled" not in b.attrs for b in presets)
    assert all(b.attrs["type"] == "button" for b in presets)
    # The cards sit in the script-only gate; without a script the checkbox is the control.
    assert _dialog(body).select_one(".js-gate .quiet-cards") is not None


def test_the_card_matching_the_stored_window_is_pressed(rig):
    _status, body = rig.get("owner")
    # The rig stores 22:00-06:30 with quiet hours on: no window card matches.
    states = [b.attrs["aria-pressed"] for b in _dialog(body).select(".quiet-cards button")]
    assert states == ["false", "false"]


def test_the_start_and_end_fields_are_tiles_with_their_labels(rig):
    _status, body = rig.get("owner")
    tiles = _dialog(body).select("label.quiet-tile")
    assert [t.select_one(".quiet-tile__label").text() for t in tiles] == ["Start", "End"]
    assert [t.select_one("input").attrs["id"] for t in tiles] == [
        "quiet-window-start", "quiet-window-end"]
    assert _dialog(body).select_one(".quiet-custom__label").text() == "Or choose your hours"
    assert _dialog(body).select_one(".quiet-intro").text() == "When should the screen rest?"


def test_the_dialog_opens_on_its_title_and_no_field_asks_for_the_focus(rig):
    _status, body = rig.get("owner")
    dialog = _dialog(body)
    assert [n for n in dialog.select("*") if "autofocus" in n.attrs] == []
    assert "data-focus-title" in dialog.attrs
    assert dialog.select_one(".modal__title").attrs["tabindex"] == "-1"


def test_the_helper_names_the_zone_and_links_to_the_place_page(rig):
    _status, body = rig.get("owner")
    note = _dialog(body).select_one(".quiet-timezone-note")
    assert note.text() == "Time zone: Martinique. Change it in Location and detection."
    assert note.select_one("a").attrs["href"] == "%s/detection#details" % rig.scope()


def test_the_dialog_is_french_in_french(rig):
    _status, body = rig.get("owner", lang="fr")
    dialog = _dialog(body)
    assert dialog.select_one("#dlg-quiet-hours-title").text() == "Heures calmes"
    assert dialog.select_one('button[type="submit"]').text() == "Enregistrer les heures calmes"
    assert "Utiliser les heures calmes" in dialog.select_one("label.settings-checkbox").text()
    assert dialog.select_one(".quiet-timezone-note").text() == (
        "Fuseau : Martinique. Changer dans Lieu et détection.")
    assert [b.select_one(".quiet-card__title").text() for b in dialog.select(".quiet-cards button")
            ] == ["Nuit", "Journée"]
    assert dialog.select_one(".quiet-custom__label").text() == "Ou choisir ses heures"


def test_the_dialog_sits_outside_every_region_a_refresh_swaps(rig):
    _status, body = rig.get("owner")
    doc = parse_html(body)
    for selector in ui_nav.REFRESH_SWAP_SELECTORS_BY_PAGE[ui_nav.REFRESH_PAGE_HOME]:
        for region in doc.select(selector):
            assert not region.select("dialog"), "dialog inside %s" % selector
            assert not region.select("#dlg-quiet-hours")


def test_the_schedule_row_is_a_switch_plus_a_link_that_opens_the_dialog(rig):
    for who in ("owner", "admin"):
        _status, body = rig.get(who)
        doc = parse_html(body)
        link = doc.select_one("a.home-switch__window")
        assert link.attrs["href"] == "#dlg-quiet-hours" and "data-modal-open" in link.attrs
        assert link.text() == "22:00 – 06:30"
        switch_forms = [
            f for f in doc.select("form")
            if f.attrs.get("action", "").endswith("/quick/quiet-hours")]
        assert len(switch_forms) == 1 and switch_forms[0].select_one('button[role="switch"]')


# --- the save ----------------------------------------------------------------


@pytest.mark.parametrize("who", ["owner", "co-manager", "admin"])
def test_a_valid_save_writes_only_the_three_keys(rig, who):
    before = rig.config()
    status, response, _body = rig.post(who, _valid())
    assert status == 303
    assert response["Location"] == "%s/?flash=quiet_window_saved" % rig.scope()
    after = rig.config()
    assert (after["quiet_hours_enabled"], after["quiet_hours_start"],
            after["quiet_hours_end"]) == (True, "21:15", "05:45")
    unchanged = {k: v for k, v in before.items() if k not in THREE_KEYS}
    assert {k: v for k, v in after.items() if k not in THREE_KEYS} == unchanged


def test_an_unchecked_box_turns_quiet_hours_off(rig):
    status, _response, _body = rig.post("owner", _valid(quiet_hours_enabled=None))
    assert status == 303
    assert rig.config()["quiet_hours_enabled"] is False
    assert rig.config()["quiet_hours_start"] == "21:15"


def test_home_and_the_toast_reflect_the_saved_window(rig):
    rig.post("owner", _valid())
    status, body = rig.get("owner", "/?flash=quiet_window_saved")
    assert status == 200
    assert parse_html(body).select_one("a.home-switch__window").text() == "21:15 – 05:45"
    assert flash_toast_title_detail(body) == (
        "Quiet hours saved", "The screen will rest from 21:15 to 05:45.")
    _status, french = rig.get("owner", "/?flash=quiet_window_saved", lang="fr")
    assert flash_toast_title_detail(french) == (
        "Heures calmes enregistrées", "L’écran sera au repos de 21:15 à 05:45.")


def test_the_quick_switch_route_still_toggles_only_the_flag(rig):
    before = rig.config()
    status, _response, _body = rig.post(
        "owner", {"state": "off", "return_to": "/"}, path="/quick/quiet-hours")
    assert status == 303
    after = rig.config()
    assert after["quiet_hours_enabled"] is False
    assert {k: v for k, v in after.items() if k != "quiet_hours_enabled"} == {
        k: v for k, v in before.items() if k != "quiet_hours_enabled"}


# --- refusals ----------------------------------------------------------------


@pytest.mark.parametrize("form,field", [
    (_valid(quiet_hours_start="25:00"), "quiet_hours_start"),
    (_valid(quiet_hours_end="7pm"), "quiet_hours_end"),
    (_valid(quiet_hours_start=""), "quiet_hours_start"),
    (_valid(quiet_hours_end=None), "quiet_hours_end"),
    (_valid(quiet_hours_start=None), "quiet_hours_start"),
    (_valid(quiet_hours_start="21:15:30"), "quiet_hours_start"),
    (_valid(quiet_hours_enabled="yes"), "quiet_hours_enabled"),
])
def test_a_refused_save_writes_nothing_and_reopens_the_dialog(rig, form, field):
    before = rig.config()
    status, _response, body = rig.post("owner", form)
    assert status == 400
    assert rig.config() == before
    dialog = _dialog(body)
    assert "open" in dialog.attrs
    control_id = {
        "quiet_hours_start": "quiet-window-start", "quiet_hours_end": "quiet-window-end",
        "quiet_hours_enabled": "quiet-window-enabled"}[field]
    control = dialog.select_one("#" + control_id)
    assert control.attrs["aria-invalid"] == "true"
    assert control.attrs["aria-describedby"] == control_id + "-error"
    assert "autofocus" in control.attrs
    assert dialog.select_one("#%s-error" % control_id).text() in (
        SHAPE_MESSAGE, "That switch sent an unexpected value.")


def test_a_refused_save_echoes_what_was_typed_escaped(rig):
    status, _response, body = rig.post("owner", _valid(quiet_hours_start=HOSTILE))
    assert status == 400
    assert "<script>alert" not in body
    start = _dialog(body).select_one("#quiet-window-start")
    assert start.attrs["value"] == HOSTILE
    assert _dialog(body).select_one("#quiet-window-end").attrs["value"] == "05:45"


def test_a_post_without_a_csrf_token_is_refused_and_writes_nothing(rig):
    before = rig.config()
    status, _response, _body = rig.post("owner", _valid(), csrf=False)
    assert status == 403
    assert rig.config() == before


@pytest.mark.parametrize("who", sorted(matrix_rows_place.EXPECTED_STATUS))
def test_each_caller_gets_the_documented_outcome(rig, who):
    before = rig.config()
    status, response, _body = rig.post(who, _valid())
    assert status == matrix_rows_place.EXPECTED_STATUS[who]
    if who == "anonymous":
        assert "/login" in response["Location"]
    if status != 303 or who == "anonymous":
        assert rig.config() == before
    else:
        assert rig.config()["quiet_hours_start"] == "21:15"
