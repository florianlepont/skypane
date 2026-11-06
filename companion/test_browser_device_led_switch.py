#!/usr/bin/env python3
"""Browser checks for the Device page Diagnostic LED switch: no accent-coloured box around the
switch or its region at rest, while the keyboard focus ring stays visible.
"""
import pytest

from companion import auth
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT, VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED,
    _assert_no_page_overflow, _login, _set_ui_theme, seed_state_dir,
)

pytestmark = pytest.mark.browser

SWITCH = "#quick-switch-led-label ~ .settings-switch-row .switch"
REGION = "#quick-switch-led-label ~ .settings-switch-row"

# The paint of the region's box and of the switch button, read after the cascade has run.
_PAINT = """sel => {
  const el = document.querySelector(sel.region).closest('.theme-status');
  const sw = document.querySelector(sel.sw);
  const read = (e) => {
    const cs = getComputedStyle(e);
    return {
      outline: cs.outlineStyle === 'none' || parseFloat(cs.outlineWidth) === 0
        ? '' : cs.outlineColor,
      border: ['Top', 'Right', 'Bottom', 'Left'].map(
        s => parseFloat(cs['border' + s + 'Width']) > 0 ? cs['border' + s + 'Color'] : '')
        .join('|'),
      shadow: cs.boxShadow,
      background: cs.backgroundColor,
    };
  };
  const probe = document.createElement('span');
  probe.style.color = 'var(--color-accent)';
  document.body.appendChild(probe);
  const accent = getComputedStyle(probe).color;
  probe.remove();
  return {accent, region: read(el), sw: read(sw)};
}"""


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=seed_state_dir, fake_providers=True)


def _mentions(value, accent):
    return accent in value


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize(
    "viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
def test_the_led_switch_has_no_accent_box_at_rest(
        new_context, server, viewport, theme, lang):
    """Nothing hovered or focused: neither the LED region nor the switch paints an outline,
    border or shadow in the accent colour."""
    context = new_context(viewport=viewport)
    try:
        context.add_cookies([{
            "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/fleet")
        page.wait_for_selector(SWITCH)
        _set_ui_theme(page, theme)
        page.mouse.move(0, 0)
        paint = page.evaluate(_PAINT, {"region": REGION, "sw": SWITCH})
        accent = paint["accent"]
        for name in ("region", "sw"):
            for prop, value in paint[name].items():
                assert not _mentions(value, accent), (
                    "%s %s paints the accent colour %s: %s" % (name, prop, accent, value))
        assert paint["sw"]["background"] == "rgba(0, 0, 0, 0)", (
            "the switch button paints a box behind its track: %s" % paint["sw"]["background"])
        size = page.locator(SWITCH).bounding_box()
        assert size["width"] >= 44 and size["height"] >= 44
        assert _assert_no_page_overflow(page, "Device", viewport["width"]) == ""
    finally:
        context.close()


def _focus_switch_by_keyboard(page):
    for _ in range(80):
        page.keyboard.press("Tab")
        if page.evaluate("sel => document.activeElement === document.querySelector(sel)",
                         SWITCH):
            break
    page.wait_for_function(
        "sel => document.activeElement === document.querySelector(sel)", arg=SWITCH)


def test_the_switch_keeps_a_visible_focus_ring_on_keyboard_focus(new_context, server):
    """Keyboard focus draws an outline of at least 2px on the switch."""
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/fleet")
        page.wait_for_selector(SWITCH)
        _focus_switch_by_keyboard(page)
        page.wait_for_function(
            "sel => { const cs = getComputedStyle(document.querySelector(sel));"
            " return cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) >= 2; }",
            arg=SWITCH)
    finally:
        context.close()


def test_a_click_toggles_the_switch_and_leaves_no_accent_box(new_context, server):
    """A pointer click flips aria-checked and the focus it leaves behind paints no accent box."""
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/fleet")
        page.wait_for_selector(SWITCH)
        before = page.get_attribute(SWITCH, "aria-checked")
        page.click(SWITCH)
        page.wait_for_function(
            "args => document.querySelector(args.sel).getAttribute('aria-checked') !== args.v",
            arg={"sel": SWITCH, "v": before})
        page.mouse.move(0, 0)
        paint = page.evaluate(_PAINT, {"region": REGION, "sw": SWITCH})
        for name in ("region", "sw"):
            for prop, value in paint[name].items():
                assert not _mentions(value, paint["accent"]), (
                    "after a click, %s %s paints the accent colour: %s" % (name, prop, value))
    finally:
        context.close()
