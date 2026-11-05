"""Real-browser proof of the frame tile strip for an administrator: the page
kept across frames, the Add a frame tile and the pairing flow it opens, the
strip scrolling sideways on a phone and wrapping on a desktop, geometry at 360
and 1280 px in both languages and themes, and the personal and Console lists."""
import pytest
from companion_app_server import session_cookie_for_state_dir
from skypane_two_device_fleet import OWNER_EMAIL

from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow)
from companion.test_device_helpers import start_fleet_app

pytestmark = pytest.mark.browser

STRIP = "ul.frame-tiles"
TILES = "ul.frame-tiles a.frame-tile:not(.frame-tile--add)"
ADD = "ul.frame-tiles a.frame-tile--add"
TILE_FLOOR = 44

_READY = """() => {
  if (document.readyState !== 'complete') return false;
  if (!document.getAnimations().every((a) => a.playState !== 'running'
      || a.effect.getComputedTiming().iterations === Infinity)) return false;
  const tile = document.querySelector('ul.frame-tiles a.frame-tile');
  const box = tile.getBoundingClientRect();
  const hit = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2);
  return !!hit && tile.contains(hit);
}"""


@pytest.fixture(scope="module")
def app(module_app_server_factory):
    holder = start_fleet_app(module_app_server_factory)
    # The fleet's owner is an administrator who owns every frame, so the
    # personal strip lists all of them.
    holder.cookie = session_cookie_for_state_dir(holder.server.state_dir, OWNER_EMAIL)
    return holder


def _open(new_context, app, path, lang="en", **context_args):
    context = new_context(**context_args)
    base = app.server.base_url()
    name, value = app.cookie.split("=", 1)
    context.add_cookies([
        {"name": name, "value": value, "url": base, "httpOnly": True, "sameSite": "Strict"},
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base}])
    page = context.new_page()
    page.goto(base + path)
    page.locator("main").wait_for(state="visible")
    page.locator(STRIP).wait_for(state="visible")
    if context_args.get("java_script_enabled", True):
        page.wait_for_function(_READY)
    return context, page


def _live_path(app, route):
    return "/devices/%s%s" % (app.fleet.live.id, route)


@pytest.mark.parametrize("route", ["/display", "/flights", "/"])
def test_choosing_a_tile_keeps_the_page_for_the_other_frame(new_context, app, route):
    """on Personalisation, Flight history and Home the other frame's tile goes to the same
    page of that frame, and the current tile carries aria-current"""
    other = app.fleet.dev_a.id
    context, page = _open(
        new_context, app, _live_path(app, route), viewport=VIEWPORT_DESKTOP)
    try:
        current = page.locator('%s[aria-current="true"]' % TILES)
        assert current.count() == 1
        assert current.get_attribute("href") == _live_path(app, route)
        with page.expect_navigation():
            page.locator('%s[href="/devices/%s%s"]' % (TILES, other, route)).click()
        assert page.url.split("?")[0].endswith("/devices/%s%s" % (other, route))
        page.locator(STRIP).wait_for(state="visible")
    finally:
        context.close()


def test_the_add_tile_is_last_and_opens_the_pairing_flow(new_context, app):
    """an administrator's strip ends with a dashed Add a frame tile that leads to the Fleet
    pairing dialog"""
    context, page = _open(
        new_context, app, _live_path(app, "/display"), viewport=VIEWPORT_DESKTOP)
    try:
        last = page.locator("ul.frame-tiles > li").last.locator("a")
        assert last.get_attribute("class").split() == ["frame-tile", "frame-tile--add"]
        assert last.inner_text().strip().endswith("Add a frame")
        assert page.locator(ADD).evaluate(
            "(el) => getComputedStyle(el).borderTopStyle") == "dashed"
        with page.expect_navigation():
            page.locator(ADD).click()
        assert page.url.endswith("/fleet?pair=1")
        page.wait_for_function(
            "() => document.querySelector('dialog#dlg-add-frame').open")
    finally:
        context.close()


def test_the_strip_scrolls_sideways_on_a_phone(new_context, app):
    """at 360px the strip is a horizontal scroller that keeps tiles on one row and the page
    itself does not scroll sideways"""
    context, page = _open(
        new_context, app, _live_path(app, "/display"), viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        metrics = page.locator(STRIP).evaluate(
            """(el) => ({overflowX: getComputedStyle(el).overflowX,
                         wrap: getComputedStyle(el).flexWrap,
                         scroll: el.scrollWidth, client: el.clientWidth})""")
        assert metrics["overflowX"] == "auto" and metrics["wrap"] == "nowrap"
        assert metrics["scroll"] > metrics["client"]
        tops = {round(page.locator("ul.frame-tiles a").nth(i).bounding_box()["y"])
                for i in range(page.locator("ul.frame-tiles a").count())}
        assert len(tops) == 1
        assert not _assert_no_page_overflow(page, "strip/phone", VIEWPORT_MIN_SUPPORTED["width"])
    finally:
        context.close()


def test_the_strip_wraps_on_a_desktop(new_context, app):
    context, page = _open(
        new_context, app, _live_path(app, "/display"), viewport=VIEWPORT_DESKTOP)
    try:
        metrics = page.locator(STRIP).evaluate(
            """(el) => ({wrap: getComputedStyle(el).flexWrap,
                         scroll: el.scrollWidth, client: el.clientWidth})""")
        assert metrics["wrap"] == "wrap"
        assert metrics["scroll"] <= metrics["client"]
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP],
                         ids=["360", "1280"])
def test_geometry_and_no_overflow(new_context, app, viewport, scheme, lang):
    """every tile, the Add tile included, is at least 44px high and wide, tiles show a
    picture, and the page does not overflow horizontally"""
    context, page = _open(
        new_context, app, _live_path(app, "/display"), lang=lang, viewport=viewport,
        color_scheme=scheme)
    try:
        for selector in (TILES, ADD):
            for index in range(page.locator(selector).count()):
                box = page.locator(selector).nth(index).bounding_box()
                assert box["height"] >= TILE_FLOOR and box["width"] >= TILE_FLOOR
        pic = page.locator(TILES + " .frame-tile__pic").first.bounding_box()
        assert pic["width"] > 0 and pic["height"] > pic["width"]
        label = "Ajouter un cadre" if lang == "fr" else "Add a frame"
        assert page.locator(ADD).inner_text().strip().endswith(label)
        assert not _assert_no_page_overflow(page, "strip/%s/%s" % (scheme, lang), viewport["width"])
    finally:
        context.close()


def test_the_personal_strip_of_an_administrator_has_no_fleet_entry(new_context, app):
    context, page = _open(
        new_context, app, _live_path(app, "/display"), viewport=VIEWPORT_DESKTOP)
    try:
        assert page.locator(STRIP + ' a[href="/fleet"]').count() == 0
        assert page.locator(STRIP).get_by_text("All frames").count() == 0
    finally:
        context.close()


def test_a_console_strip_lists_every_frame_with_the_owner_email(new_context, app):
    context, page = _open(
        new_context, app, _live_path(app, "/health"), viewport=VIEWPORT_DESKTOP)
    try:
        fleet = app.fleet
        for device in (fleet.live, fleet.dev_a, fleet.dev_b, fleet.landscape):
            assert page.locator(
                '%s[href="/devices/%s/health"]' % (TILES, device.id)).count() == 1
        notes = page.locator(TILES + " .frame-tile__note").all_inner_texts()
        assert notes and all("@" in note for note in notes)
    finally:
        context.close()
