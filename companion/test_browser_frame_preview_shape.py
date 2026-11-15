"""Real-browser checks that every frame picture's container follows the frame's own shape.

A landscape frame (800x480) shows its picture in a container wider than tall with no bands
around the picture: the Home picture and its empty state, the Departures look picture and its
bezel, the layout card thumbnail and the layout picker tiles. The live portrait frame keeps its
taller-than-wide containers. Phone and desktop widths, English and French, light and dark."""
import os

import pytest
from companion_app_server import session_cookie_for_state_dir
from PIL import Image
from skypane_two_device_fleet import OWNER_EMAIL

from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_PHONE, _set_ui_theme)
from companion.test_device_helpers import start_fleet_app
from server import device_config
from server.plane import colour_rules

pytestmark = pytest.mark.browser

GALLERY_NAME = "20261115T120000Z.png"
# A rendered picture may differ from its container's shape by rounding only.
SHAPE_TOLERANCE = 0.03

# Hidden lazy pictures never load; only the visible ones are waited for.
LOADED = ("() => [...document.images].filter((img) => img.getClientRects().length > 0)"
          ".every((img) => img.complete)")

# Every visible element is measured in page pixels, with the picture's natural size when it is an image.
MEASURE = """(selector) => [...document.querySelectorAll(selector)]
  .filter((el) => el.getClientRects().length > 0)
  .map((el) => {
    const box = el.getBoundingClientRect();
    return {width: box.width, height: box.height,
            naturalWidth: el.naturalWidth || 0, naturalHeight: el.naturalHeight || 0,
            complete: el.tagName !== 'IMG' || el.complete};
  })"""


def _write_gallery_picture(directory, size):
    gallery = os.path.join(directory, "gallery")
    os.makedirs(gallery, exist_ok=True)
    Image.new("RGB", size, (200, 210, 220)).save(os.path.join(gallery, GALLERY_NAME))


def _seeder(layout_id):
    def seed(fleet):
        _write_gallery_picture(fleet.landscape.state_dir, (800, 480))
        _write_gallery_picture(fleet.live.state_dir, (1200, 1600))
        for device in (fleet.landscape, fleet.live):
            device_config.save_device_config(device.state_dir, layout=layout_id)
            colour_rules.add_rule(device.state_dir, "prefix", "TVF", "white")
    return seed


# The default layout (giant lettering) offers pairing tiles; the classic one the look pictures.
@pytest.fixture(scope="module", params=["b", "classic"])
def app(request, module_app_server_factory):
    holder = start_fleet_app(module_app_server_factory, seed_extra=_seeder(request.param))
    holder.layout = request.param
    holder.cookie = session_cookie_for_state_dir(holder.server.state_dir, OWNER_EMAIL)
    return holder


def _open(new_context, app, device, route, viewport, lang, scheme):
    context = new_context(viewport=viewport, color_scheme=scheme)
    base = app.server.base_url()
    name, value = app.cookie.split("=", 1)
    context.add_cookies([
        {"name": name, "value": value, "url": base, "httpOnly": True, "sameSite": "Strict"},
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base}])
    page = context.new_page()
    page.goto("%s/devices/%s%s" % (base, device.id, route))
    page.locator("main").wait_for(state="visible")
    _set_ui_theme(page, scheme)
    page.wait_for_function(
        LOADED)
    return context, page


def _measure(page, selector):
    return page.evaluate(MEASURE, selector)


def _reveal_layout_picker(page):
    """On a phone the picker sits behind the Change button."""
    toggle = page.locator("[data-layout-toggle]")
    if toggle.count() and toggle.is_visible():
        toggle.click()
        page.wait_for_function(
            "() => document.querySelector('[data-layout-toggle]')"
            ".getAttribute('aria-expanded') === 'true'")
        page.wait_for_function(
            LOADED)


def _assert_shape(boxes, landscape, what):
    assert boxes, "%s: nothing measured" % what
    for box in boxes:
        if landscape:
            assert box["width"] > box["height"] * 1.3, "%s is not landscape: %r" % (what, box)
        else:
            assert box["height"] > box["width"] * 1.2, "%s is not portrait: %r" % (what, box)
        if box["naturalWidth"]:
            natural = box["naturalWidth"] / box["naturalHeight"]
            rendered = box["width"] / box["height"]
            assert abs(rendered - natural) / natural < SHAPE_TOLERANCE, (
                "%s has bands: box %r" % (what, box))


FRAMES = [("landscape", True), ("live", False)]
# What each page must show, by selector. The layout card shows a thumbnail on a phone and the
# open picker on a desktop.
REQUIRED = {
    "b": {
        "/": [".preview-frame__image"],
        "/display": [".look-pick__preview"],
        "/display/arrivals": [".look-pick__preview"],
        "/display/special-looks": [".special-row__image"],
    },
    "classic": {
        "/": [".preview-frame__image"],
        "/display": [".look-frame__picture", ".look-frame__image", ".look-pick__preview"],
        "/display/arrivals": [".look-frame__picture", ".look-frame__image"],
        "/display/special-looks": [".special-row__image"],
    },
}
THUMB = ".layout-card__thumb"


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_DESKTOP], ids=["phone", "desktop"])
@pytest.mark.parametrize("frame,landscape", FRAMES)
@pytest.mark.parametrize("route", list(REQUIRED["b"]))
def test_the_picture_containers_follow_the_frame_shape(
        new_context, app, route, frame, landscape, viewport, lang, scheme):
    context, page = _open(
        new_context, app, getattr(app.fleet, frame), route, viewport, lang, scheme)
    try:
        selectors = list(REQUIRED[app.layout][route])
        if route == "/display":
            if viewport is VIEWPORT_PHONE:
                selectors.append(THUMB)
            _reveal_layout_picker(page)
        for selector in selectors:
            _assert_shape(
                _measure(page, selector), landscape, "%s %s %s" % (frame, route, selector))
    finally:
        context.close()


@pytest.mark.parametrize("frame,landscape", FRAMES)
@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_DESKTOP], ids=["phone", "desktop"])
def test_the_empty_home_picture_follows_the_frame_shape(
        new_context, app, frame, landscape, viewport):
    """a frame with no picture yet shows its empty state in the frame's own shape"""
    device = getattr(app.fleet, frame)
    gallery = os.path.join(device.state_dir, "gallery", GALLERY_NAME)
    os.rename(gallery, gallery + ".hidden")
    try:
        context, page = _open(new_context, app, device, "/", viewport, "en", "light")
        try:
            _assert_shape(_measure(page, ".preview-empty"), landscape, frame + " empty home")
        finally:
            context.close()
    finally:
        os.rename(gallery + ".hidden", gallery)
