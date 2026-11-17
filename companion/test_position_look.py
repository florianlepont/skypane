"""The one look of a frame that tracks a position, over a real in-process
server: its Style page lists a single Look view in place of Departures and
Arrivals, the address of Arrivals opens it, its picture is an overhead render,
and saving stores `theme` alone. A frame that tracks a runway keeps Departures
and Arrivals.
"""
import io
import os

import pytest
from PIL import Image

from access_matrix_support import OWNER_EMAIL, seed_matrix_fleet
from companion import device_scope
from companion_app_server import (
    InProcessAppServer, http_request, session_cookie_for_state_dir, with_csrf)
from companion_markup import parse_html
from server import device_config

POSITION = {"mode": "position", "radius_km": 9}
RUNWAY = {"mode": "runway", "airport": "LFPG", "runway": "08L/26R"}


class Rig:
    def __init__(self, server, cookie, scope, state_dir):
        self.server = server
        self.cookie = cookie
        self.scope = scope
        self.state_dir = state_dir

    def get(self, path, lang=None):
        headers = {"Accept-Language": lang} if lang else None
        status, _response, body = http_request(
            self.server.url(self.scope + path), cookie=self.cookie, extra_headers=headers)
        return status, body

    def page(self, path, lang=None):
        status, body = self.get(path, lang)
        assert status == 200
        return parse_html(body.decode("utf-8"))

    def save(self, **fields):
        form = {"scope": "display", "return_to": "/display"}
        form.update(fields)
        return http_request(
            self.server.url(self.scope + "/settings"), method="POST",
            data=with_csrf(self.cookie, form), cookie=self.cookie,
            extra_headers={"Origin": self.server.base_url()})

    def stored(self):
        return device_config.load_device_config(self.state_dir)


@pytest.fixture
def rig(tmp_path):
    state_dir = str(tmp_path / "state")
    server = InProcessAppServer(state_dir)
    fleet = seed_matrix_fleet(state_dir)
    device_dir = {d.id: d.state_dir for d in device_scope.load_devices(state_dir)}[fleet.owner_device]
    os.makedirs(device_dir, exist_ok=True)
    device_config.save_device_config(
        device_dir, layout="classic", detection=POSITION, theme="white", theme_arriving="red")
    yield Rig(server, session_cookie_for_state_dir(state_dir, OWNER_EMAIL, "user"),
              "/devices/%s" % fleet.owner_device, device_dir)
    server.stop()


def _nav(root):
    return [a.text() for a in root.select("nav.personalisation-nav a")]


def _panels(root):
    return {p.attrs["data-look-panel"]: p for p in root.select("[data-look-panel]")}


def test_a_position_frame_lists_one_look_view(rig):
    assert _nav(rig.page("/display")) == ["Look", "Special looks", "Calendar"]
    assert _nav(rig.page("/display", lang="fr"))[0] == "Allure"


def test_a_runway_frame_keeps_departures_and_arrivals(rig):
    device_config.save_device_config(rig.state_dir, detection=RUNWAY)
    assert _nav(rig.page("/display")) == ["Departures", "Arrivals", "Special looks", "Calendar"]
    assert _nav(rig.page("/display/arrivals"))[1] == "Arrivals"
    assert rig.page("/display/arrivals").select_one(
        "nav.personalisation-nav a[aria-current]").text() == "Arrivals"


def test_the_arrivals_address_opens_the_one_look_on_a_position_frame(rig):
    root = rig.page("/display/arrivals")
    assert _nav(root) == ["Look", "Special looks", "Calendar"]
    assert root.select_one("nav.personalisation-nav a[aria-current]").text() == "Look"
    assert root.select('input[name="theme"]')


def test_the_look_view_explains_what_it_covers_in_english_and_french(rig):
    english = rig.page("/display").text()
    assert "applies to every aircraft" in english
    assert "labelled Overhead and shows the city it is flying to" in english
    assert "s’applique à tous les avions" in rig.page("/display", lang="fr").text()


def test_the_look_view_shows_an_overhead_picture_of_the_saved_look(rig):
    panels = _panels(rig.page("/display"))
    assert "hidden" not in panels["departures"].attrs
    image = panels["departures"].select_one("img.look-frame__image")
    assert "/frame-preview/white.png?state=overhead" in image.attrs["src"]


def test_saving_the_look_stores_theme_and_keeps_the_arrivals_look_on_disk(rig):
    status, _response, _body = rig.save(theme="blue")
    assert status == 303
    stored = rig.stored()
    assert (stored["theme"], stored["theme_arriving"]) == ("blue", "red")
    image = _panels(rig.page("/display"))["departures"].select_one("img.look-frame__image")
    assert "/frame-preview/blue.png?state=overhead" in image.attrs["src"]


def test_a_giant_layout_offers_the_pairing_cards_with_overhead_pictures(rig):
    device_config.save_device_config(rig.state_dir, layout="b", theme="blue_light")
    root = rig.page("/display")
    assert "applies to every aircraft" in root.text()
    radios = root.select('input[name="theme"]')
    assert [r.attrs["value"] for r in radios if "checked" in r.attrs] == ["blue_light"]
    assert not root.select('input[name="theme_arriving"]')
    panel = _panels(root)["departures"]
    previews = [img.attrs["src"] for img in panel.select("img.look-pick__preview")]
    assert previews and all("state=overhead" in src and "layout=b" in src for src in previews)


def test_the_overhead_picture_is_neither_the_departing_nor_the_arriving_one(rig):
    def picture(state):
        status, body = rig.get("/frame-preview/blue.png?state=%s&size=small" % state)
        assert status == 200
        return Image.open(io.BytesIO(body)).convert("RGB").tobytes()

    overhead = picture("overhead")
    assert overhead != picture("departing")
    assert overhead != picture("arriving")
