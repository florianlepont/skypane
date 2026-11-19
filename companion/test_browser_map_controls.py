#!/usr/bin/env python3
"""Real-browser check that the round buttons over the Location map (Use my position, Show all of
France, the map credits) are real buttons: 44 px round, an opaque fill and a visible edge, so they
do not blend into the map, in the light theme, the dark theme and the automatic dark theme.

The ground they must stand out from is the map's own ground colour. The fill is read as the
computed colour (never a stylesheet value) and must have no transparency; the button must stand
out from the ground either by its fill or by its edge (WCAG 1.4.11's 3:1 for a control's boundary).
"""
import pytest

from place_map_support import Hosts, seed
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT, VIEWPORT_MIN_SUPPORTED, _login, _set_ui_theme)

pytestmark = pytest.mark.browser

BUTTONS = ("#place-locate", "#place-france", ".place-info__button")

_PAINT = """(selectors) => {
  const parse = (css) => { const m = css.match(/[\\d.]+/g).map(Number);
    return {r: m[0], g: m[1], b: m[2], a: m.length > 3 ? m[3] : 1}; };
  const ground = parse(getComputedStyle(document.querySelector('.place-map')).backgroundColor);
  return {ground, buttons: selectors.map(sel => {
    const el = document.querySelector(sel); if (!el) return {sel, missing: true};
    const style = getComputedStyle(el); const box = el.getBoundingClientRect();
    return {sel, w: box.width, h: box.height, radius: style.borderTopLeftRadius,
            bg: parse(style.backgroundColor), edge: parse(style.borderTopColor),
            edgeWidth: parseFloat(style.borderTopWidth)}; })};
}"""


def _open(new_context, server):
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    Hosts(context)
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/detection")
    page.wait_for_function(
        "() => document.documentElement.classList.contains('map-ready')", timeout=15000)
    return page


def _luminance(colour):
    def channel(value):
        value /= 255
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4
    return 0.2126 * channel(colour["r"]) + 0.7152 * channel(colour["g"]) + 0.0722 * channel(colour["b"])


def _contrast(one, two):
    high, low = sorted((_luminance(one), _luminance(two)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def _over(colour, ground):
    """`colour` painted over the opaque `ground`."""
    alpha = colour["a"]
    return {key: colour[key] * alpha + ground[key] * (1 - alpha) for key in ("r", "g", "b")}


def _check(paint, where):
    ground = paint["ground"]
    for button in paint["buttons"]:
        assert not button.get("missing"), (where, button)
        assert button["w"] >= 44 and button["h"] >= 44, (where, button)
        assert button["bg"]["a"] == 1, ("the fill is not opaque", where, button)
        fill_contrast = _contrast(button["bg"], ground)
        edge_contrast = _contrast(_over(button["edge"], button["bg"]), ground)
        assert button["edgeWidth"] >= 1 and max(fill_contrast, edge_contrast) >= 3 or fill_contrast >= 3, (
            "the button blends into the map", where, button, fill_contrast, edge_contrast)


@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
def test_the_round_map_buttons_are_opaque_and_stand_out_from_the_map(
        new_context, make_app_server, theme):
    server = make_app_server(seed=seed, fake_providers=True)
    page = _open(new_context, server)
    _set_ui_theme(page, theme)
    page.wait_for_function("() => document.getAnimations().every(a => a.playState !== 'running' "
                           "|| a.effect.getTiming().iterations === Infinity)", timeout=10000)
    paint = page.evaluate(_PAINT, list(BUTTONS))
    _check(paint, theme)
    for button in paint["buttons"][:2]:
        assert button["radius"] in ("50%", "22px", "9999px") or float(button["radius"].rstrip("px")) >= 22, button


def test_the_round_map_buttons_are_opaque_in_the_automatic_dark_theme(new_context, make_app_server):
    server = make_app_server(seed=seed, fake_providers=True)
    page = _open(new_context, server)
    page.emulate_media(color_scheme="dark")
    page.evaluate("() => document.documentElement.removeAttribute('data-ui-theme')")
    page.wait_for_function("() => getComputedStyle(document.querySelector('.place-map')).backgroundColor"
                           " !== 'rgb(242, 239, 233)'", timeout=5000)
    _check(page.evaluate(_PAINT, list(BUTTONS)), "auto-dark")
