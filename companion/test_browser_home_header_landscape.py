"""Real-browser checks of the Home header (picture, frame name, state, next refresh) on a phone.

A landscape frame shows its picture across the full width, above the text; the name stays on
one line where it fits and the next-refresh line takes at most two lines. A portrait frame
keeps the picture beside the text."""
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

# Boxes of the header parts and the number of text lines of the name and the refresh line.
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
    picture: box('.hero__picture'), body: box('.hero__body'),
    status: box('.hero__status'), next: box('.home-state__next'),
    info: box('.info-tip__button'),
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
        return page.evaluate(MEASURE)
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_landscape_frame_header_is_stacked_on_a_phone(new_context, app, lang):
    m = _measure_home(new_context, app, app.fleet.landscape, lang)
    assert m["picture"]["width"] > m["body"]["width"] * 0.9, m
    assert m["picture"]["bottom"] <= m["body"]["top"] + 1, "text must sit under the picture: %r" % m
    assert m["nameLines"] == 1, m
    assert m["nextLines"] <= 2, m
    assert m["scrollWidth"] <= m["clientWidth"], m
    # The info button sits level with the refresh line.
    assert m["info"]["top"] < m["next"]["bottom"] and m["info"]["bottom"] > m["next"]["top"], m


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_portrait_frame_header_stays_side_by_side_on_a_phone(new_context, app, lang):
    m = _measure_home(new_context, app, app.fleet.live, lang)
    assert m["picture"]["right"] <= m["body"]["left"] + 1, m
    assert m["picture"]["width"] < m["body"]["width"] * 1.5, m
    assert m["scrollWidth"] <= m["clientWidth"], m
