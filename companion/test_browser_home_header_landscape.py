"""Real-browser checks of Home's title block, flight card and strip for a landscape frame on a
phone.

A landscape frame shows its picture across the full width of the flight card, above the flight's
text, and its strip tiles take the landscape shape (5:3); the name stays on one line where it
fits and the next-refresh line takes at most two lines. A portrait frame keeps the picture beside
the text and its tiles stay portrait (3:4)."""
import os
from datetime import datetime, timedelta, timezone

import pytest
from companion_app_server import session_cookie_for_state_dir
from PIL import Image
from skypane_two_device_fleet import OWNER_EMAIL

from companion import auth
from companion.test_browser_ux_helpers import VIEWPORT_PHONE, _set_ui_theme
from companion.test_device_helpers import start_fleet_app
from server import device_config, history_db

pytestmark = pytest.mark.browser

GALLERY_NAME = "20261115T120000Z.png"
LOADED = ("() => [...document.images].filter((img) => img.getClientRects().length > 0)"
          ".every((img) => img.complete)")

# Boxes of the card parts, the strip's tile and the number of text lines of the name and the
# refresh line.
MEASURE = """() => {
  const box = (sel) => {
    const el = document.querySelector(sel);
    const r = el.getBoundingClientRect();
    return {left: r.left, right: r.right, top: r.top, bottom: r.bottom, width: r.width,
            height: r.height};
  };
  const lines = (sel) => {
    const el = document.querySelector(sel);
    return Math.round(el.getBoundingClientRect().height / parseFloat(getComputedStyle(el).lineHeight));
  };
  return {
    picture: box('.home-flight__picture'), meta: box('.home-flight__meta'),
    next: box('.home-state__next'), info: box('.info-tip__button'),
    tile: box('.home-strip__frame'),
    nameLines: lines('.title-action__text'), nextLines: lines('.home-state__next'),
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  };
}"""


def _write_gallery_picture(directory, size):
    gallery = os.path.join(directory, "gallery")
    os.makedirs(gallery, exist_ok=True)
    Image.new("RGB", size, (200, 210, 220)).save(os.path.join(gallery, GALLERY_NAME))


def _seed(fleet):
    _write_gallery_picture(fleet.landscape.state_dir, (800, 480))
    _write_gallery_picture(fleet.live.state_dir, (1200, 1600))
    stamp = datetime.now(timezone.utc) - timedelta(minutes=1)
    for device in (fleet.landscape, fleet.live):
        device_config.save_device_config(
            device.state_dir, display_enabled=True, quiet_hours_enabled=False,
            wake_interval_s=300)
        with history_db.open_db(device.state_dir) as conn:
            history_db.record_device_health(
                conn, stamp.isoformat(), battery_mv=4100, fw_version="1.0.0",
                boot_reason="wake", rssi="-60")
            history_db.record_runway_event(
                conn, ts=stamp.isoformat(), hex="39a001", callsign="AFR1234",
                airline="Air France", origin="ORY", destination="TLS",
                confirmed_state="departing", gallery_name=GALLERY_NAME)


@pytest.fixture(scope="module")
def app(module_app_server_factory):
    holder = start_fleet_app(module_app_server_factory, seed_extra=_seed)
    holder.cookie = session_cookie_for_state_dir(holder.server.state_dir, OWNER_EMAIL)
    return holder


def _measure_home(new_context, app, device, lang):
    context = new_context(viewport=VIEWPORT_PHONE, color_scheme="light")
    try:
        base = app.server.base_url()
        name, value = app.cookie.split("=", 1)
        context.add_cookies([
            {"name": name, "value": value, "url": base, "httpOnly": True, "sameSite": "Strict"},
            {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base}])
        page = context.new_page()
        page.goto("%s/devices/%s/" % (base, device.id))
        page.locator("main").wait_for(state="visible")
        _set_ui_theme(page, "light")
        page.wait_for_function(LOADED)
        page.wait_for_selector(".home-state__next")
        page.wait_for_selector(".home-strip__frame")
        return page.evaluate(MEASURE)
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_landscape_frame_card_is_stacked_on_a_phone(new_context, app, lang):
    m = _measure_home(new_context, app, app.fleet.landscape, lang)
    card = m["picture"]["right"] - m["picture"]["left"]
    assert card > m["meta"]["width"] * 0.9, m
    assert m["picture"]["bottom"] <= m["meta"]["top"] + 1, "text must sit under the picture: %r" % m
    assert m["picture"]["width"] / m["picture"]["height"] > 1.5, m
    assert m["nameLines"] == 1, m
    assert m["nextLines"] <= 2, m
    assert m["scrollWidth"] <= m["clientWidth"], m
    # The info button sits level with the refresh line.
    assert m["info"]["top"] < m["next"]["bottom"] and m["info"]["bottom"] > m["next"]["top"], m
    # The strip's tiles take the frame's landscape shape.
    assert abs(m["tile"]["width"] / m["tile"]["height"] - 5 / 3) < 0.05, m


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_portrait_frame_card_stays_side_by_side_on_a_phone(new_context, app, lang):
    m = _measure_home(new_context, app, app.fleet.live, lang)
    assert m["picture"]["right"] <= m["meta"]["left"] + 1, m
    assert m["picture"]["width"] < m["meta"]["width"] * 1.5, m
    assert abs(m["tile"]["width"] / m["tile"]["height"] - 3 / 4) < 0.02, m
    assert m["scrollWidth"] <= m["clientWidth"], m


@pytest.mark.parametrize("shape", ["landscape", "live"])
def test_the_cycle_ring_wraps_the_picture_of_either_shape(new_context, app, shape):
    """the ring sits 5px outside the frame picture, landscape or portrait, and stays inside
    the flight card"""
    context = new_context(viewport=VIEWPORT_PHONE, color_scheme="light")
    try:
        base = app.server.base_url()
        name, value = app.cookie.split("=", 1)
        context.add_cookies([{"name": name, "value": value, "url": base,
                              "httpOnly": True, "sameSite": "Strict"}])
        page = context.new_page()
        page.goto("%s/devices/%s/" % (base, getattr(app.fleet, shape).id))
        page.wait_for_selector(".home-flight__picture > .home-ring")
        page.wait_for_function(LOADED)
        box = page.evaluate(
            "() => { const p = document.querySelector('.home-flight__picture .preview-frame__image')"
            ".getBoundingClientRect(); const r = document.querySelector('.home-ring')"
            ".getBoundingClientRect(); const c = document.querySelector('.home-flight')"
            ".getBoundingClientRect();"
            " return {gap: [p.left - r.left, p.top - r.top, r.right - p.right, r.bottom - p.bottom],"
            " inside: r.left >= c.left && r.right <= c.right && r.top >= c.top && r.bottom <= c.bottom}; }")
        assert all(abs(v - 5) < 1.6 for v in box["gap"]), box
        assert box["inside"], box
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [
    {"width": 844, "height": 390}, {"width": 926, "height": 428}], ids=["844x390", "926x428"])
@pytest.mark.parametrize("shape", ["landscape", "live"])
def test_the_picture_box_hugs_the_picture_when_the_text_is_taller(new_context, app, viewport, shape):
    """on a phone held sideways the text column may be taller than the picture; the picture's
    box (the cycle ring's frame) must still end where the picture ends, leaving no empty strip
    under it"""
    context = new_context(viewport=viewport, color_scheme="light")
    try:
        base = app.server.base_url()
        name, value = app.cookie.split("=", 1)
        context.add_cookies([{"name": name, "value": value, "url": base, "httpOnly": True,
                              "sameSite": "Strict"}])
        page = context.new_page()
        page.goto("%s/devices/%s/" % (base, getattr(app.fleet, shape).id))
        page.wait_for_function(LOADED)
        page.wait_for_selector(".home-ring")
        heights = page.evaluate(
            "() => ({box: document.querySelector('.home-flight__picture').getBoundingClientRect().height,"
            " image: document.querySelector('.home-flight__picture img').getBoundingClientRect().height,"
            " meta: document.querySelector('.home-flight__meta').getBoundingClientRect().height})")
        assert abs(heights["box"] - heights["image"]) <= 1, heights
        if shape == "landscape":
            assert heights["meta"] > heights["image"], heights
    finally:
        context.close()
