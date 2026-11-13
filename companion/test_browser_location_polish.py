"""Real-browser checks of the Location page details and the phone tab bar labels: the radius slider has a
name and speaks kilometres and a typed radius past the limit is pulled back to the limit, the privacy
caption gives way once something is typed, the runway cards keep the length and the surface each on
one unbroken line, and the Console tab bar labels fit inside their pills at 360 px in both languages.
Waits are on the page's own state, never fixed sleeps."""
import pytest

from companion import auth
from companion.test_browser_ux_helpers import VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _login
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


def _open_place(new_context, server, viewport, lang="en", route="/detection"):
    """The Location page with both external hosts answered by the test, settled and at rest."""
    context = new_context(viewport=viewport)
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
