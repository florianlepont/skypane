"""Real-browser proof of the phone frame strip: a marked-off, collapsible
surface whose summary row names the active frame, compact tiles showing only
the picture and the name, the remembered open/closed choice (and its fallback
when storage is blocked), the strip open without script, and the unchanged
desktop look. Also the Console Fleet strip on a phone. Both themes."""
import pytest
from companion_app_server import session_cookie_for_state_dir
from skypane_two_device_fleet import OWNER_EMAIL

from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow)
from companion.test_device_helpers import start_fleet_app

pytestmark = pytest.mark.browser

FOLD = "details.frame-fold"
SUMMARY = "details.frame-fold > summary"
STRIP = "details.frame-fold ul.frame-tiles"
TILES = STRIP + " a.frame-tile:not(.frame-tile--add)"
STORAGE_KEY = "skypane.frameStrip"

_READY = """() => {
  if (document.readyState !== 'complete') return false;
  if (!document.getAnimations().every((a) => a.playState !== 'running'
      || a.effect.getComputedTiming().iterations === Infinity)) return false;
  const summary = document.querySelector('details.frame-fold > summary');
  const box = summary.getBoundingClientRect();
  if (box.width === 0) return true;
  const hit = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2);
  return !!hit && summary.contains(hit);
}"""

_BLOCK_STORAGE = """
Object.defineProperty(window, 'localStorage', {
  get() { throw new DOMException('blocked', 'SecurityError'); }
});
"""


@pytest.fixture(scope="module")
def app(module_app_server_factory):
    holder = start_fleet_app(module_app_server_factory)
    holder.cookie = session_cookie_for_state_dir(holder.server.state_dir, OWNER_EMAIL)
    return holder


def _open(new_context, app, path, lang="en", block_storage=False, **context_args):
    context = new_context(**context_args)
    base = app.server.base_url()
    name, value = app.cookie.split("=", 1)
    context.add_cookies([
        {"name": name, "value": value, "url": base, "httpOnly": True, "sameSite": "Strict"},
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base}])
    if block_storage:
        context.add_init_script(_BLOCK_STORAGE)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.goto(base + path)
    page.locator("main").wait_for(state="visible")
    if context_args.get("java_script_enabled", True):
        page.wait_for_function(_READY)
    page.errors = errors
    return context, page


def _live_path(app, route="/display"):
    return "/devices/%s%s" % (app.fleet.live.id, route)


def _fold_state(page):
    return page.evaluate(
        """() => ({
            open: document.querySelector('details.frame-fold').open,
            listVisible: document.querySelector('details.frame-fold ul.frame-tiles')
                .checkVisibility({contentVisibilityAuto: true}),
            stored: (() => { try { return localStorage.getItem('skypane.frameStrip'); }
                             catch (e) { return 'blocked'; } })()})""")


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_the_phone_fold_is_a_marked_surface_with_the_active_name(new_context, app, scheme):
    context, page = _open(
        new_context, app, _live_path(app), viewport=VIEWPORT_MIN_SUPPORTED,
        color_scheme=scheme)
    try:
        summary = page.locator(SUMMARY)
        box = summary.bounding_box()
        assert box["height"] >= 44 and box["width"] >= 44
        assert summary.inner_text().strip() == "Orly frame"
        fold = page.locator(FOLD).evaluate(
            """(el) => { const s = getComputedStyle(el);
                const bg = getComputedStyle(document.querySelector('main')).backgroundColor;
                const body = getComputedStyle(document.documentElement).backgroundColor;
                return {bg: s.backgroundColor, shadow: s.boxShadow, image: s.backgroundImage,
                        border: s.borderTopWidth, page: body}; }""")
        assert fold["bg"] != fold["page"], fold
        assert fold["image"] == "none" and fold["border"] == "1px", fold
        assert "inset" not in fold["shadow"], fold
        assert not _assert_no_page_overflow(page, "fold/" + scheme, 360)
        assert page.errors == []
    finally:
        context.close()


def test_phone_tiles_show_only_the_picture_and_the_name(new_context, app):
    context, page = _open(
        new_context, app, _live_path(app), viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        tiles = page.locator(TILES)
        assert tiles.count() >= 2
        for index in range(tiles.count()):
            tile = tiles.nth(index)
            box = tile.bounding_box()
            assert box["height"] >= 44 and box["width"] >= 44
            assert box["width"] < 132
            assert tile.locator(".frame-tile__name").is_visible()
            assert tile.locator(".frame-tile__pic").is_visible()
            assert tile.locator(".frame-tile__seen").is_hidden()
            assert tile.locator(".frame-tile__note").count() == 0 or tile.locator(
                ".frame-tile__note").is_hidden()
            pic = tile.locator(".frame-tile__pic").bounding_box()
            dot = tile.locator(".frame-tile__dot").bounding_box()
            assert dot["width"] <= 16 and pic["width"] <= 36
    finally:
        context.close()


def test_the_summary_collapses_the_strip_and_the_choice_is_remembered(new_context, app):
    context, page = _open(
        new_context, app, _live_path(app), viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        assert _fold_state(page)["open"] is True
        page.locator(SUMMARY).click()
        page.wait_for_function(
            "() => !document.querySelector('details.frame-fold').open"
            " && localStorage.getItem('%s') === 'closed'" % STORAGE_KEY)
        assert _fold_state(page)["listVisible"] is False
        page.goto(page.url)
        page.wait_for_function(
            "() => document.readyState === 'complete'"
            " && !document.querySelector('details.frame-fold').open")
        page.locator(SUMMARY).click()
        page.wait_for_function(
            "() => document.querySelector('details.frame-fold').open"
            " && localStorage.getItem('%s') === 'open'" % STORAGE_KEY)
        assert _fold_state(page)["listVisible"] is True
        page.goto(page.url)
        page.wait_for_function(
            "() => document.readyState === 'complete'"
            " && document.querySelector('details.frame-fold').open")
    finally:
        context.close()


def test_blocked_storage_still_lets_the_strip_open_and_close(new_context, app):
    context, page = _open(
        new_context, app, _live_path(app), viewport=VIEWPORT_MIN_SUPPORTED,
        block_storage=True)
    try:
        page.locator(SUMMARY).click()
        page.wait_for_function("() => !document.querySelector('details.frame-fold').open")
        page.locator(SUMMARY).click()
        page.wait_for_function("() => document.querySelector('details.frame-fold').open")
        assert page.errors == []
    finally:
        context.close()


def test_without_script_the_strip_is_open(new_context, app):
    context, page = _open(
        new_context, app, _live_path(app), viewport=VIEWPORT_MIN_SUPPORTED,
        java_script_enabled=False)
    try:
        assert page.locator(FOLD).get_attribute("open") is not None
        assert page.locator(STRIP).is_visible()
        assert page.locator(TILES).first.is_visible()
    finally:
        context.close()


def test_the_desktop_strip_keeps_its_look_and_ignores_a_phone_collapse(new_context, app):
    context, page = _open(
        new_context, app, _live_path(app), viewport=VIEWPORT_DESKTOP)
    try:
        page.evaluate("() => localStorage.setItem('%s', 'closed')" % STORAGE_KEY)
        page.goto(page.url)
        page.wait_for_function(_READY)
        assert page.locator(SUMMARY).is_hidden()
        assert _fold_state(page)["open"] is True
        assert page.locator(STRIP).is_visible()
        tile = page.locator(TILES).first
        assert tile.bounding_box()["width"] >= 130
        assert tile.locator(".frame-tile__seen").is_visible()
        fold = page.locator(FOLD).evaluate(
            "(el) => ({shadow: getComputedStyle(el).boxShadow,"
            " border: getComputedStyle(el).borderTopWidth})")
        assert fold["shadow"] == "none" and fold["border"] == "0px"
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_the_console_fleet_strip_uses_the_compact_tile_on_a_phone(new_context, app, scheme):
    context, page = _open(
        new_context, app, "/fleet", viewport=VIEWPORT_MIN_SUPPORTED, color_scheme=scheme)
    try:
        assert page.locator(SUMMARY).is_visible()
        assert page.locator(SUMMARY).bounding_box()["height"] >= 44
        for index in range(page.locator(TILES).count()):
            tile = page.locator(TILES).nth(index)
            assert tile.bounding_box()["width"] < 132
            assert tile.locator(".frame-tile__seen").is_hidden()
        system = page.locator("a.frame-tile--system")
        assert system.is_visible() and system.locator(".frame-tile__seen").is_hidden()
        page.locator("a.frame-tile--system").click()
        page.wait_for_function("() => location.search.indexOf('view=system') >= 0")
        assert page.locator(SUMMARY).inner_text().strip() == "System"
        assert not _assert_no_page_overflow(page, "fleet/" + scheme, 360)
    finally:
        context.close()
