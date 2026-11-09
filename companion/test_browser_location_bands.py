"""Real-browser checks of the tint the Location page gives a phone browser's bars: the page
behind the map and the edge strips take the tile ground colour, the ?bands= value picks a
variant (a, b, c, off), and wide screens and the installed web app are left alone."""
import pytest

from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _login)
from place_map_support import Hosts, SETTLED, seed
from server import airports

pytestmark = pytest.mark.browser

VIEWPORT_PHONE = {"width": 390, "height": 844}
SAFE_TOP = 59
SAFE_BOTTOM = 34
GROUND = "rgb(242, 239, 233)"
GROUND_HEX = "#f2efe9"

_INSTALLED = """(() => { const real = window.matchMedia.bind(window);
  window.matchMedia = (q) => real(q.replace('(display-mode: browser)', 'not all')); })()"""
_READ = """() => {
  const stage = document.querySelector('.place-stage');
  const strip = (which) => { const s = getComputedStyle(stage, which);
    return {content: s.content, position: s.position, top: s.top, bottom: s.bottom,
            left: s.left, right: s.right, height: s.height, background: s.backgroundColor,
            events: s.pointerEvents, z: s.zIndex}; };
  const root = document.documentElement;
  return {before: strip('::before'), after: strip('::after'),
          variant: root.getAttribute('data-bands'),
          html: getComputedStyle(root).backgroundColor,
          htmlImage: getComputedStyle(root).backgroundImage,
          body: getComputedStyle(document.body).backgroundColor,
          tags: [...document.querySelectorAll('meta[name=theme-color]')]
                  .map(m => m.content.toLowerCase())};
}"""
_BOXES = """() => {
  const box = (sel) => { const r = document.querySelector(sel).getBoundingClientRect();
    return {top: r.top, bottom: r.bottom, left: r.left, right: r.right}; };
  const centre = (sel) => { const e = document.querySelector(sel); const r = e.getBoundingClientRect();
    const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    return !!hit && (hit === e || e.contains(hit)); };
  const alpha = (sel) => { const c = getComputedStyle(document.querySelector(sel)).backgroundColor;
    const m = c.match(/[\\d.]+/g); return m.length > 3 ? parseFloat(m[3]) : 1; };
  return {map: box('#place-map'), header: box('.site-header .frame-switch, .site-header a, .site-header button'),
          search: box('.place-float'), tabs: box('.tab-bar'),
          height: window.innerHeight, width: window.innerWidth,
          hits: [centre('.place-search__row input[type=search]'), centre('.tab-bar a')],
          searchAlpha: alpha('.place-search__row'), tabsAlpha: alpha('.tab-bar')};
}"""


def _open(new_context, server, viewport, query="", scheme="light", standalone=False):
    context = new_context(viewport=viewport, color_scheme=scheme)
    Hosts(context)
    page = context.new_page()
    if standalone:
        # Chromium cannot emulate display-mode, so the page script is told it runs installed.
        page.add_init_script(_INSTALLED)
    _login(page, server.base_url())
    icao = max(airports.load_catalogue().values(), key=lambda a: len(a.runways)).icao
    page.goto(server.base_url() + "/detection?airport=" + icao + query)
    page.wait_for_function(
        "() => document.documentElement.classList.contains('map-ready')", timeout=15000)
    page.wait_for_function(SETTLED, timeout=10000)
    return context, page


def _settle(page):
    page.wait_for_function(
        "() => document.querySelector('.tab-bar a') && (() => { const e = document.querySelector("
        "'.tab-bar a'); const r = e.getBoundingClientRect(); const h = document.elementFromPoint("
        "r.left + r.width / 2, r.top + r.height / 2); return !!h && e.contains(h); })()",
        timeout=10000)


def _force_insets(page):
    page.evaluate(
        "([t, b]) => { const s = document.documentElement.style;"
        " s.setProperty('--safe-top', t + 'px'); s.setProperty('--safe-bottom', b + 'px'); }",
        [SAFE_TOP, SAFE_BOTTOM])
    page.wait_for_function(SETTLED, timeout=10000)


def _no_strips(read):
    return read["before"]["content"] == "none" and read["after"]["content"] == "none"


@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED], ids=["390", "360"])
@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("query", ["", "?bands=a"], ids=["default", "a"])
def test_variant_a_paints_the_ground_behind_the_map_and_12px_strips_at_both_edges(
        new_context, make_app_server, viewport, theme, query):
    server = make_app_server(seed=seed, fake_providers=True)
    sep = "&" if query else ""
    context, page = _open(new_context, server, viewport, query=sep + query.lstrip("?"),
                          scheme=theme)
    try:
        _settle(page)
        read = page.evaluate(_READ)
        assert read["variant"] == "a", read
        assert read["html"] == GROUND and read["body"] == GROUND, read
        assert read["htmlImage"] == "none", read
        assert read["tags"] == [GROUND_HEX, GROUND_HEX], read
        for strip, edge in ((read["before"], "top"), (read["after"], "bottom")):
            assert strip["position"] == "fixed" and strip[edge] == "0px", strip
            assert strip["left"] == "0px" and strip["right"] == "0px", strip
            assert strip["height"] == "12px", strip
            assert strip["background"] == GROUND, strip
            assert strip["events"] == "none", strip
        _force_insets(page)
        read = page.evaluate(_READ)
        assert read["before"]["height"] == "%dpx" % (SAFE_TOP + 12), read
        assert read["after"]["height"] == "%dpx" % (SAFE_BOTTOM + 12), read
        got = page.evaluate(_BOXES)
        assert got["map"]["top"] <= 0 and got["map"]["bottom"] >= got["height"], got
        assert got["map"]["left"] <= 0 and got["map"]["right"] >= got["width"], got
        assert got["header"]["top"] >= SAFE_TOP - 1, got
        assert got["search"]["top"] >= SAFE_TOP, got
        assert got["tabs"]["bottom"] <= got["height"] - SAFE_BOTTOM + 1, got
        assert got["hits"] == [True, True], got
        assert got["searchAlpha"] == 1 and got["tabsAlpha"] >= 0.8, got
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED], ids=["390", "360"])
def test_variant_b_has_the_ground_background_and_no_strips(new_context, make_app_server, viewport):
    server = make_app_server(seed=seed, fake_providers=True)
    context, page = _open(new_context, server, viewport, query="&bands=b")
    try:
        read = page.evaluate(_READ)
        assert read["variant"] == "b" and _no_strips(read), read
        assert read["html"] == GROUND and read["body"] == GROUND, read
        assert read["tags"] == [GROUND_HEX, GROUND_HEX], read
        got = page.evaluate(_BOXES)
        assert got["map"]["top"] <= 0 and got["map"]["bottom"] >= got["height"], got
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED], ids=["390", "360"])
def test_variant_c_has_1px_full_bleed_strips(new_context, make_app_server, viewport):
    server = make_app_server(seed=seed, fake_providers=True)
    context, page = _open(new_context, server, viewport, query="&bands=c")
    try:
        _force_insets(page)
        read = page.evaluate(_READ)
        assert read["variant"] == "c", read
        assert read["html"] == GROUND and read["body"] == GROUND, read
        for strip, edge in ((read["before"], "top"), (read["after"], "bottom")):
            assert strip["position"] == "fixed" and strip[edge] == "0px", strip
            assert strip["left"] == "0px" and strip["right"] == "0px", strip
            assert strip["height"] == "1px" and strip["background"] == GROUND, strip
            assert strip["events"] == "none", strip
    finally:
        context.close()


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_variant_off_keeps_the_page_theme_with_no_tint(new_context, make_app_server, theme):
    server = make_app_server(seed=seed, fake_providers=True)
    context, page = _open(new_context, server, VIEWPORT_PHONE, query="&bands=off",
                          scheme=theme)
    try:
        read = page.evaluate(_READ)
        assert read["variant"] == "off" and _no_strips(read), read
        assert read["html"] != GROUND and read["body"] != GROUND, read
        assert GROUND_HEX not in read["tags"], read
    finally:
        context.close()


@pytest.mark.parametrize("query", ["&bands=zzz", "&bands=%3Cscript%3E", "&bands=A", "&bands="])
def test_an_unknown_bands_value_is_the_default_and_is_never_reflected(
        new_context, make_app_server, query):
    server = make_app_server(seed=seed, fake_providers=True)
    context, page = _open(new_context, server, VIEWPORT_PHONE, query=query)
    try:
        read = page.evaluate(_READ)
        assert read["variant"] == "a" and read["html"] == GROUND, read
        assert "zzz" not in page.content() and "<script>" not in page.inner_html("body")
    finally:
        context.close()


def test_a_wide_screen_ignores_the_variants(new_context, make_app_server):
    server = make_app_server(seed=seed, fake_providers=True)
    context, page = _open(new_context, server, VIEWPORT_DESKTOP, query="&bands=a")
    try:
        read = page.evaluate(_READ)
        assert read["variant"] is None and _no_strips(read), read
        assert read["html"] != GROUND and GROUND_HEX not in read["tags"], read
    finally:
        context.close()


def test_the_installed_web_app_is_left_alone(new_context, make_app_server):
    server = make_app_server(seed=seed, fake_providers=True)
    context, page = _open(new_context, server, VIEWPORT_PHONE, query="&bands=a", standalone=True)
    try:
        assert not page.evaluate("() => matchMedia('(display-mode: browser)').matches")
        read = page.evaluate(_READ)
        assert read["variant"] is None and _no_strips(read), read
        assert read["html"] != GROUND and read["body"] != GROUND, read
        assert GROUND_HEX not in read["tags"], read
    finally:
        context.close()
