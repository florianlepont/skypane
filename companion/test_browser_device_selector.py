"""Real-browser checks of the frame tile strip: a user with two frames switches
frame from Display and stays on Display, a one-frame user sees no strip, the
strip fits at 360px and 1280px in both languages and colour schemes with 44px
targets, the current tile is outlined with the accent colour, and it works with
scripts blocked."""
import os
from types import SimpleNamespace

import pytest
from companion_app_server import session_cookie_for_state_dir
from skypane_two_device_fleet import sim_hardware_env

from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow, _hit_area)
from companion.test_device_helpers import start_fleet_app
from server import device_dirs, fleet_db, hardware

pytestmark = pytest.mark.browser

STRIP = "ul.frame-tiles"
TILES = "ul.frame-tiles a.frame-tile:not(.frame-tile--add)"
HIT_FLOOR = 44
MULTI_EMAIL = "multi@example.test"
SINGLE_EMAIL = "single@example.test"

# Waits until the page is fully loaded, every finite animation is over and the
# first tile owns its own centre (a cross-document view transition leaves the
# root element answering hit tests for a moment).
_READY = """() => {
  if (document.readyState !== 'complete') return false;
  if (!document.getAnimations().every((a) => a.playState !== 'running'
      || a.effect.getComputedTiming().iterations === Infinity)) return false;
  const tile = document.querySelector('ul.frame-tiles a.frame-tile');
  if (!tile) return true;
  const box = tile.getBoundingClientRect();
  const hit = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2);
  return !!hit && tile.contains(hit);
}"""


def _add_user_frames(state_dir, email, names):
    """A plain user owning one simulated frame per name; returns the ids."""
    ids = []
    conn = fleet_db.connect(state_dir)
    try:
        with sim_hardware_env(), fleet_db.transaction(conn):
            user_id = fleet_db.add_user(conn, email, "user")
            for index, name in enumerate(names):
                mac = "aa:bb:cc:ee:%02x:%02x" % (len(email), 0x20 + index)
                device_id = fleet_db.add_device(
                    conn, mac, "f" * 64, hardware.SIM_CLONE_KEY, user_id, name=name,
                    state_path="auto")
                profile = hardware.get_profile(hardware.SIM_CLONE_KEY, os.environ)
                device_dirs.provision_device_dir(
                    state_dir, device_id, profile.width, profile.height, fill=0)
                ids.append(device_id)
    finally:
        conn.close()
    return SimpleNamespace(ids=ids)


@pytest.fixture(scope="module")
def fleet_app(module_app_server_factory):
    holder = {}

    def seed_extra(fleet):
        root = fleet.live.state_dir
        holder["multi"] = _add_user_frames(root, MULTI_EMAIL, ["Alpha", "Bravo"])
        holder["single"] = _add_user_frames(root, SINGLE_EMAIL, ["Solo"])

    app = start_fleet_app(module_app_server_factory, seed_extra=seed_extra)
    app.multi, app.single = holder["multi"], holder["single"]
    return app


def _open(new_context, app, email, route, lang="en", role="user", **context_args):
    context = new_context(**context_args)
    base = app.server.base_url()
    pair = session_cookie_for_state_dir(app.server.state_dir, email, role)
    name, value = pair.split("=", 1)
    context.add_cookies([
        {"name": name, "value": value, "url": base, "httpOnly": True, "sameSite": "Strict"},
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base}])
    page = context.new_page()
    page.goto(base + route)
    page.locator("main").wait_for(state="visible")
    if context_args.get("java_script_enabled", True):
        page.wait_for_function(_READY)
    return context, page


def test_a_user_switches_frame_from_display_and_stays_on_display(new_context, fleet_app):
    """choosing the other frame's tile on Display lands on that frame's Display, where the
    other frame's tile is now the current one"""
    first, second = fleet_app.multi.ids
    context, page = _open(
        new_context, fleet_app, MULTI_EMAIL, "/devices/%s/display" % first,
        viewport=VIEWPORT_DESKTOP)
    try:
        assert page.locator(TILES).count() == 2
        with page.expect_navigation():
            page.locator('%s[href="/devices/%s/display"]' % (TILES, second)).click()
        assert page.url.endswith("/devices/%s/display" % second)
        page.wait_for_function(_READY)
        current = page.locator('%s[aria-current="true"]' % TILES)
        assert current.count() == 1
        assert current.get_attribute("href") == "/devices/%s/display" % second
    finally:
        context.close()


def test_a_single_frame_user_sees_no_strip(new_context, fleet_app):
    """with one frame the page carries no strip at all"""
    (solo,) = fleet_app.single.ids
    context, page = _open(
        new_context, fleet_app, SINGLE_EMAIL, "/devices/%s/display" % solo,
        viewport=VIEWPORT_DESKTOP)
    try:
        assert page.locator(STRIP).count() == 0
        assert page.locator("a.frame-tile").count() == 0
    finally:
        context.close()


def test_a_user_has_an_add_a_frame_tile_to_their_own_page(new_context, fleet_app):
    first = fleet_app.multi.ids[0]
    context, page = _open(
        new_context, fleet_app, MULTI_EMAIL, "/devices/%s/display" % first,
        viewport=VIEWPORT_DESKTOP)
    try:
        add = page.locator("a.frame-tile--add")
        assert add.count() == 1 and add.get_attribute("href") == "/pair-frame"
        with page.expect_navigation():
            add.click()
        assert page.url.endswith("/pair-frame")
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP],
                         ids=["360", "1280"])
def test_strip_fits_with_44px_targets_and_outlines_the_current_tile(
        new_context, fleet_app, viewport, scheme, lang):
    """no horizontal overflow, every tile at least 44px high and wide, the current tile
    outlined in the accent colour and the others not"""
    first = fleet_app.multi.ids[0]
    context, page = _open(
        new_context, fleet_app, MULTI_EMAIL, "/devices/%s/display" % first, lang=lang,
        viewport=viewport, color_scheme=scheme)
    try:
        assert not _assert_no_page_overflow(page, "strip", viewport["width"])
        for index in range(page.locator(TILES).count()):
            box = page.locator(TILES).nth(index).bounding_box()
            assert box["height"] >= HIT_FLOOR and box["width"] >= HIT_FLOOR
        area = _hit_area(page, TILES + '[aria-current="true"]')
        assert area["visual"][0] >= HIT_FLOOR and area["visual"][1] >= HIT_FLOOR
        colours = page.evaluate(
            """() => {
              const probe = document.createElement('i');
              probe.style.color = 'var(--color-accent)';
              document.body.appendChild(probe);
              const accent = getComputedStyle(probe).color;
              probe.remove();
              const border = (el) => getComputedStyle(el).borderTopColor;
              const tiles = [...document.querySelectorAll('ul.frame-tiles a.frame-tile')];
              return {accent,
                current: border(tiles.find((t) => t.hasAttribute('aria-current'))),
                others: tiles.filter((t) => !t.hasAttribute('aria-current')).map(border)};
            }""")
        assert colours["current"] == colours["accent"]
        assert all(other != colours["accent"] for other in colours["others"])
    finally:
        context.close()


@pytest.mark.parametrize("lang,word", [("en", "Not seen yet"), ("fr", "Pas encore vu")])
def test_tiles_carry_the_dot_word_and_the_last_seen_word(
        new_context, fleet_app, lang, word):
    """every tile has exactly one status dot with its word and the last-seen line, in the
    page language (a never-seen frame reads Not seen yet)"""
    first = fleet_app.multi.ids[0]
    context, page = _open(
        new_context, fleet_app, MULTI_EMAIL, "/devices/%s/display" % first, lang=lang,
        viewport=VIEWPORT_DESKTOP)
    try:
        dots = page.locator(TILES + " [role='img']")
        assert dots.count() == 2
        assert [dots.nth(i).get_attribute("aria-label") for i in range(2)] == [word, word]
        assert page.locator(TILES + " .frame-tile__seen").all_inner_texts() == [word, word]
    finally:
        context.close()


def test_the_strip_is_reachable_and_activated_with_the_keyboard(new_context, fleet_app):
    first, second = fleet_app.multi.ids
    context, page = _open(
        new_context, fleet_app, MULTI_EMAIL, "/devices/%s/display" % first,
        viewport=VIEWPORT_DESKTOP)
    try:
        page.locator('%s[href="/devices/%s/display"]' % (TILES, second)).focus()
        page.wait_for_function(
            "() => document.activeElement.matches('ul.frame-tiles a.frame-tile')")
        with page.expect_navigation():
            page.keyboard.press("Enter")
        assert page.url.endswith("/devices/%s/display" % second)
    finally:
        context.close()


def test_scripts_blocked_a_tile_still_navigates(new_context, fleet_app):
    """a tile is a plain link: without script it goes to the same page of the other frame"""
    first, second = fleet_app.multi.ids
    context, page = _open(
        new_context, fleet_app, MULTI_EMAIL, "/devices/%s/flights" % first,
        viewport=VIEWPORT_MIN_SUPPORTED, java_script_enabled=False)
    try:
        tile = page.locator('%s[href="/devices/%s/flights"]' % (TILES, second))
        tile.wait_for(state="visible")
        with page.expect_navigation():
            tile.click()
        assert page.url.endswith("/devices/%s/flights" % second)
    finally:
        context.close()
