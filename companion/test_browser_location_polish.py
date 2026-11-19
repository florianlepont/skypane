"""Real-browser checks of the Location page details and the phone tab bar labels: the radius slider has a
name and speaks kilometres and a typed radius past the limit is pulled back to the limit, the privacy
caption gives way once something is typed, the runway cards keep the length and the surface each on
one unbroken line, and the Console tab bar labels fit inside their pills at 360 px in both languages.
Waits are on the page's own state, never fixed sleeps."""
import pytest

from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow, _login, _set_ui_theme)
from nav_spaces_support import admin_page
from place_map_support import SETTLED, Hosts, seed as _seed

pytestmark = pytest.mark.browser

RADIUS_MAX = 28
READY = "() => document.documentElement.classList.contains('map-ready')"
TILES_LOADED = "() => document.querySelectorAll('#place-map .leaflet-tile-loaded').length >= 1"
# Finite animations and transitions are over; a never-ending one is not waited for.
ANIMATIONS_DONE = (
    "() => document.getAnimations().every("
    "(a) => a.playState !== 'running' || a.effect.getComputedTiming().iterations === Infinity)")


def _open_place(new_context, server, viewport, lang="en", route="/detection", scheme=None):
    """The Location page with both external hosts answered by the test, settled and at rest."""
    context = new_context(viewport=viewport, **({"color_scheme": scheme} if scheme else {}))
    Hosts(context)
    context.add_cookies([
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + route)
    page.wait_for_function(READY, timeout=15000)
    page.wait_for_function(TILES_LOADED, timeout=15000)
    page.wait_for_function(ANIMATIONS_DONE, timeout=10000)
    page.wait_for_function(SETTLED, timeout=10000)
    page.wait_for_function(ANIMATIONS_DONE, timeout=10000)
    return context, page


def test_the_radius_slider_is_named_and_a_radius_past_the_limit_is_pulled_back(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_place(new_context, server, VIEWPORT_MIN_SUPPORTED)
    try:
        slider = page.get_by_role("slider", name="Radius (km)")
        assert slider.count() == 1
        page.wait_for_function(
            "() => /^[0-9]+ km$/.test("
            "document.getElementById('place-radius-range').getAttribute('aria-valuetext'))",
            timeout=5000)
        page.fill("#place-radius", "999")
        page.press("#place-radius", "Tab")
        page.wait_for_function(
            "m => document.getElementById('place-radius').value === String(m)"
            " && document.getElementById('place-radius-range').value === String(m)",
            arg=RADIUS_MAX, timeout=5000)
        assert slider.get_attribute("aria-valuetext") == "%d km" % RADIUS_MAX
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_caption_gives_way_to_the_suggestions_once_something_is_typed(
        new_context, make_app_server, lang):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_place(new_context, server, VIEWPORT_MIN_SUPPORTED, lang)
    try:
        page.click("#place-search")
        page.wait_for_function(
            "() => getComputedStyle(document.getElementById('place-search-help')).display"
            " !== 'none'", timeout=5000)
        page.keyboard.type("Lyon")
        page.wait_for_function(
            "() => !document.getElementById('place-results').hidden", timeout=10000)
        page.wait_for_function(ANIMATIONS_DONE, timeout=10000)
        assert page.evaluate(
            "() => getComputedStyle(document.getElementById('place-search-help')).display"
        ) == "none"
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_runway_cards_keep_the_length_and_the_surface_each_on_one_line(
        new_context, make_app_server, viewport, lang):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_place(new_context, server, viewport, lang, "/detection?mode=runway")
    try:
        page.wait_for_function(
            "() => document.querySelectorAll('.place-sheet .runway-card').length > 0", timeout=10000)
        seen = page.evaluate(
            "() => [...document.querySelectorAll("
            "'.place-sheet .runway-card__length, .place-sheet .runway-card__surface')]"
            ".filter(e => e.closest('.runway-card__detail').getBoundingClientRect().width > 4)"
            ".map(e => ({text: e.textContent, lines: e.getClientRects().length,"
            " clipped: e.scrollWidth > e.clientWidth + 1}))")
        if viewport["width"] >= 700:
            assert seen, "no runway detail is shown at this width"
        for part in seen:
            assert part["lines"] == 1 and not part["clipped"], part
        assert page.evaluate(
            "() => [...document.querySelectorAll('.place-sheet .runway-card__sep')]"
            ".every(e => getComputedStyle(e).display === 'none')")
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_console_tab_bar_labels_sit_inside_their_pills_at_360(
        new_context, app_server_in_process, lang):
    context, page = admin_page(
        new_context, app_server_in_process, "/fleet", VIEWPORT_MIN_SUPPORTED, lang)
    try:
        page.wait_for_function(ANIMATIONS_DONE, timeout=10000)
        cells = page.evaluate(
            "() => [...document.querySelectorAll('.tab-bar__label')].map(l => {"
            " const p = l.closest('.tab-bar__pill').getBoundingClientRect();"
            " const range = document.createRange(); range.selectNodeContents(l);"
            " const t = range.getBoundingClientRect();"
            " return {text: l.textContent, sw: l.scrollWidth, cw: l.clientWidth,"
            " left: t.left - p.left, right: p.right - t.right}; })")
        assert len(cells) == 5, cells
        for cell in cells:
            assert cell["sw"] <= cell["cw"], cell
            assert cell["left"] >= 1.5 and cell["right"] >= 1.5, cell
    finally:
        context.close()


FRANCE_NAMES = {"en": "Show all of France", "fr": "Voir toute la France"}
FRANCE_PROBE = (
    "() => { const b = document.getElementById('place-france'); const r = b.getBoundingClientRect();"
    " const cs = getComputedStyle(b);"
    " return {w: r.width, h: r.height, name: b.getAttribute('aria-label'), text: b.innerText.trim(),"
    " radius: cs.borderTopLeftRadius, icon: !!b.querySelector('svg')}; }")


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
def test_show_all_of_france_is_a_round_icon_button_with_a_name(
        new_context, make_app_server, viewport, lang):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_place(new_context, server, viewport, lang)
    try:
        box = page.evaluate(FRANCE_PROBE)
        assert box["name"] == FRANCE_NAMES[lang]
        assert box["text"] == "" and box["icon"]
        assert box["w"] >= 44 and box["h"] >= 44 and abs(box["w"] - box["h"]) < 1
        assert box["radius"] in ("50%", "22px", "9999px") or float(box["radius"][:-2]) >= 22
        _assert_no_page_overflow(page, "location")
    finally:
        context.close()


TILE_FILTER = (
    "() => getComputedStyle(document.querySelector('#place-map .leaflet-tile-pane')).filter")
OVERLAY_CONTRAST = """() => {
  const rgb = (c) => c.match(/[\\d.]+/g).slice(0, 3).map(Number);
  const lum = (c) => { const [r, g, b] = rgb(c).map((v) => { v /= 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
  const probe = document.createElement('div'); probe.className = 'place-circle';
  const svgNS = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(svgNS, 'svg'); const path = document.createElementNS(svgNS, 'path');
  path.setAttribute('class', 'place-circle'); svg.appendChild(path);
  document.getElementById('place-map').appendChild(svg);
  const stroke = getComputedStyle(path).stroke; svg.remove();
  const ground = getComputedStyle(document.getElementById('place-map')).backgroundColor;
  const a = lum(stroke), b = lum(ground);
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05); }"""


def test_the_map_is_dark_in_dark_and_auto_dark_and_light_in_light(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_place(new_context, server, VIEWPORT_DESKTOP, scheme="light")
    try:
        _set_ui_theme(page, "light")
        assert page.evaluate(TILE_FILTER) == "none"
        _set_ui_theme(page, "dark")
        assert "invert" in page.evaluate(TILE_FILTER)
        assert page.evaluate(OVERLAY_CONTRAST) >= 3
    finally:
        context.close()
    context, page = _open_place(new_context, server, VIEWPORT_DESKTOP, scheme="dark")
    try:
        assert "invert" in page.evaluate(TILE_FILTER)
        assert page.evaluate(OVERLAY_CONTRAST) >= 3
    finally:
        context.close()
