"""The Overhead look over a real in-process server: a frame that watches a
position gets an Overhead view of its own (classic look picker and giant
pairing cards), its picture is an overhead render, it follows departures
until changed, a save stores `theme_overhead` alone, and a frame that
watches a runway is offered no Overhead view.
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
OVERHEAD_PATH = "/display/overhead"


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
        form = {"scope": "display", "return_to": OVERHEAD_PATH}
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


def test_a_position_frame_lists_the_overhead_view(rig):
    assert _nav(rig.page("/display")) == [
        "Departures", "Arrivals", "Overhead", "Special looks", "Calendar"]
    assert _nav(rig.page("/display", lang="fr"))[2] == "Au-dessus"
    links = rig.page(OVERHEAD_PATH).select("nav.personalisation-nav a")
    assert [a.attrs.get("aria-current") for a in links].index("page") == 2


def test_a_runway_frame_lists_no_overhead_view(rig):
    device_config.save_device_config(rig.state_dir, detection=RUNWAY)
    root = rig.page("/display")
    assert _nav(root) == ["Departures", "Arrivals", "Special looks", "Calendar"]
    assert not root.select('input[name="theme_overhead"]')


def test_the_overhead_view_shows_an_overhead_picture_following_departures(rig):
    root = rig.page(OVERHEAD_PATH)
    assert root.select_one("[data-look-initial]").attrs["data-look-initial"] == "overhead"
    panels = _panels(root)
    assert "hidden" not in panels["overhead"].attrs
    assert "hidden" in panels["departures"].attrs and "hidden" in panels["arrivals"].attrs
    overhead = panels["overhead"]
    assert "neither a departure nor an arrival" in overhead.text()
    image = overhead.select_one("img.look-frame__image")
    assert "/frame-preview/white.png?state=overhead" in image.attrs["src"]
    assert [r.attrs["value"] for r in overhead.select(
        'input[name="theme_overhead"][checked]')] == [""]


def test_saving_an_overhead_look_stores_it_alone_and_the_view_shows_it(rig):
    status, response, _body = rig.save(theme_overhead="blue")
    assert status == 303 and OVERHEAD_PATH in response["Location"]
    stored = rig.stored()
    assert (stored["theme"], stored["theme_arriving"], stored["theme_overhead"]) == (
        "white", "red", "blue")
    overhead = _panels(rig.page(OVERHEAD_PATH))["overhead"]
    src = overhead.select_one("img.look-frame__image").attrs["src"]
    assert "/frame-preview/blue.png?state=overhead" in src
    rig.save(theme_overhead="")
    assert rig.stored()["theme_overhead"] is None


def test_a_refused_overhead_look_redraws_the_overhead_view(rig):
    status, _response, body = rig.save(theme_overhead="not-a-theme")
    assert status == 200
    root = parse_html(body.decode("utf-8"))
    assert root.select_one("[data-look-initial]").attrs["data-look-initial"] == "overhead"
    assert rig.stored()["theme_overhead"] is None


def test_a_giant_layout_offers_the_overhead_pairing_cards(rig):
    device_config.save_device_config(rig.state_dir, layout="b", theme_overhead="blue_light")
    overhead = _panels(rig.page(OVERHEAD_PATH))["overhead"]
    radios = overhead.select('input[name="theme_overhead"]')
    assert "" in [r.attrs["value"] for r in radios]
    assert [r.attrs["value"] for r in radios if "checked" in r.attrs] == ["blue_light"]
    previews = [img.attrs["src"] for img in overhead.select("img.look-pick__preview")]
    assert previews and all("state=overhead" in src and "layout=b" in src for src in previews)


def _picture(rig, state):
    status, body = rig.get("/frame-preview/blue.png?state=%s&size=small" % state)
    assert status == 200
    return Image.open(io.BytesIO(body)).convert("RGB").tobytes()


def test_the_overhead_picture_is_neither_the_departing_nor_the_arriving_one(rig):
    overhead = _picture(rig, "overhead")
    assert overhead != _picture(rig, "departing")
    assert overhead != _picture(rig, "arriving")
