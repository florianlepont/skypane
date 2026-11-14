"""Real-browser geometry of the tab bar and the More sheet on tablet widths: both are capped
at 460px and centred instead of stretching across the screen, the dim layer still covers the
whole viewport, the pill stays inside its cell, and a phone keeps the full-width bar."""
import pytest
from companion_app_server import session_cookie_for_state_dir
from skypane_two_device_fleet import OWNER_EMAIL

from companion import auth
from companion.test_browser_ux_helpers import VIEWPORT_PHONE
from companion.test_device_helpers import start_fleet_app

pytestmark = pytest.mark.browser

CAP_PX = 460
TABLET = {"width": 768, "height": 1024}
TABLET_WIDE = {"width": 940, "height": 1000}
DESKTOP_SIDEBAR = {"width": 1024, "height": 800}

_SETTLED = """() => document.readyState === 'complete' && document.getAnimations().every(
  (a) => a.playState !== 'running' || a.effect.getComputedTiming().iterations === Infinity)"""

_MORE_OWNS_CENTRE = """() => {
  const e = document.querySelector('.tab-bar__more > summary'); if (!e) return false;
  const r = e.getBoundingClientRect();
  const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
  return hit === e || e.contains(hit); }"""

_BOXES = """() => {
  const box = (sel) => {
    const el = document.querySelector(sel);
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return {left: r.left, right: window.innerWidth - r.right, width: r.width};
  };
  const scrim = getComputedStyle(document.body, '::after');
  return {bar: box('.tab-bar'), sheet: box('.tab-bar__more-panel'),
          scrimPosition: scrim.position, scrimWidth: parseFloat(scrim.width),
          scrimHeight: parseFloat(scrim.height), innerWidth: window.innerWidth,
          innerHeight: window.innerHeight};
}"""

_PILL_IN_CELL = """() => {
  const active = document.querySelector('.tab-bar__link--active');
  const slider = document.querySelector('.tab-bar__slider');
  if (!active || !slider) return null;
  const cell = active.getBoundingClientRect();
  const pill = slider.getBoundingClientRect();
  return {cellLeft: cell.left, cellRight: cell.right, pillLeft: pill.left,
          pillRight: pill.right}; }"""


@pytest.fixture(scope="module")
def app(module_app_server_factory):
    holder = start_fleet_app(module_app_server_factory)
    holder.cookie = session_cookie_for_state_dir(holder.server.state_dir, OWNER_EMAIL)
    return holder


def _open(new_context, app, viewport, scheme="light"):
    context = new_context(viewport=viewport, color_scheme=scheme)
    base = app.server.base_url()
    name, value = app.cookie.split("=", 1)
    context.add_cookies([
        {"name": name, "value": value, "url": base, "httpOnly": True, "sameSite": "Strict"},
        {"name": auth.UI_LANG_COOKIE_NAME, "value": "en", "url": base}])
    page = context.new_page()
    page.goto(base + "/devices/%s/" % app.fleet.live.id)
    page.locator(".tab-bar").wait_for(state="visible")
    page.wait_for_function(_SETTLED)
    page.wait_for_function(_MORE_OWNS_CENTRE, timeout=10000)
    return context, page


def _open_sheet(page):
    if not page.locator(".tab-bar__more").evaluate("el => el.open"):
        page.locator(".tab-bar__more > summary").click()
    page.locator(".tab-bar__more-panel").wait_for(state="visible")
    page.wait_for_function(_SETTLED)


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("viewport", [TABLET, TABLET_WIDE], ids=["768", "940"])
def test_bar_and_sheet_are_capped_and_centred_on_a_tablet(new_context, app, viewport, scheme):
    context, page = _open(new_context, app, viewport, scheme)
    try:
        _open_sheet(page)
        boxes = page.evaluate(_BOXES)
        for name in ("bar", "sheet"):
            box = boxes[name]
            assert box["width"] <= CAP_PX + 0.5, (name, box)
            assert abs(box["left"] - box["right"]) <= 1, (name, box)
        # The dim layer still covers the whole screen.
        assert boxes["scrimPosition"] == "fixed"
        assert boxes["scrimWidth"] == pytest.approx(boxes["innerWidth"], abs=1)
        assert boxes["scrimHeight"] == pytest.approx(boxes["innerHeight"], abs=1)
    finally:
        context.close()


def test_the_pill_stays_inside_its_cell_on_a_tablet(new_context, app):
    context, page = _open(new_context, app, TABLET)
    try:
        page.wait_for_function(
            "() => document.querySelector('.tab-bar--slider') !== null", timeout=10000)
        page.wait_for_function(_SETTLED)
        geometry = page.evaluate(_PILL_IN_CELL)
        assert geometry["pillLeft"] >= geometry["cellLeft"] - 1, geometry
        assert geometry["pillRight"] <= geometry["cellRight"] + 1, geometry
    finally:
        context.close()


def test_a_phone_keeps_the_full_width_bar(new_context, app):
    context, page = _open(new_context, app, VIEWPORT_PHONE)
    try:
        _open_sheet(page)
        boxes = page.evaluate(_BOXES)
        for name in ("bar", "sheet"):
            box = boxes[name]
            assert box["left"] == pytest.approx(8, abs=1), (name, box)
            assert box["right"] == pytest.approx(8, abs=1), (name, box)
    finally:
        context.close()


def test_the_sidebar_layout_shows_no_tab_bar(new_context, app):
    context = new_context(viewport=DESKTOP_SIDEBAR)
    base = app.server.base_url()
    name, value = app.cookie.split("=", 1)
    context.add_cookies([
        {"name": name, "value": value, "url": base, "httpOnly": True, "sameSite": "Strict"}])
    page = context.new_page()
    try:
        page.goto(base + "/devices/%s/" % app.fleet.live.id)
        page.locator("main").wait_for(state="visible")
        assert not page.locator(".tab-bar").is_visible()
    finally:
        context.close()
