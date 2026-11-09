"""Real-browser checks of the visual foundations on representative pages: titles and card
titles sit on the one type scale with the system display face (no serif anywhere), no label is
tracked uppercase, every corner radius is one of the three radius tokens, the fixed bars, sheets
and header pad themselves with the device safe-area tokens, and the page-shell theme-color tags
follow the explicit theme."""
import pytest

from place_map_support import Hosts
from companion.auth import UI_THEME_COOKIE_NAME
from companion.test_browser_ux_helpers import _login, seed_state_dir

pytestmark = pytest.mark.browser

PHONE = {"width": 390, "height": 844}
DESKTOP = {"width": 1440, "height": 900}
# Home, Flights, Account, Location, Collection and Display.
PAGES = ("/", "/flights", "/account", "/detection", "/airlines", "/display")
SERIF_FACES = ("Iowan", "Georgia", "Charter", "Palatino", "Book Antiqua", "Times")

FINITE_ANIMATIONS_DONE = (
    "() => document.readyState === 'complete' && document.getAnimations().every("
    "(a) => (a.effect && a.effect.getComputedTiming().iterations === Infinity)"
    " || a.playState !== 'running')")

_TITLES = """
() => {
  const root = getComputedStyle(document.documentElement);
  const read = (el) => {
    const s = getComputedStyle(el);
    return {text: el.textContent.trim().slice(0, 30), tag: el.tagName.toLowerCase(),
            cls: String(el.className), family: s.fontFamily, size: parseFloat(s.fontSize),
            weight: s.fontWeight, tracking: s.letterSpacing,
            em: parseFloat(s.letterSpacing) / parseFloat(s.fontSize)};
  };
  const visible = (e) => e.checkVisibility();
  return {
    display: root.getPropertyValue('--font-display').trim(),
    ui: root.getPropertyValue('--font-ui').trim(),
    pageTitles: [...document.querySelectorAll('main h1.page-title')].filter(visible).map(read),
    h1Count: document.querySelectorAll('main h1').length,
    sectionTitles: [...document.querySelectorAll('main .text-heading')].filter(visible).map(read),
    headings: [...document.querySelectorAll('main h1, main h2, main h3, main legend, main .text-heading')]
      .filter(visible).map(read),
  };
}
"""

_NO_UPPERCASE = """
() => [...document.querySelectorAll('main *, header *, .tab-bar *, .dashboard-sidebar *')]
  .filter((e) => e.checkVisibility() && e.childNodes.length
    && [...e.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim()))
  .filter((e) => getComputedStyle(e).textTransform === 'uppercase'
    || parseFloat(getComputedStyle(e).letterSpacing) > 0.5)
  .map((e) => e.tagName.toLowerCase() + '.' + String(e.className).split(' ')[0])
"""

_RADII = """
() => {
  const bad = new Set();
  for (const el of document.querySelectorAll('body *')) {
    if (!el.checkVisibility()) continue;
    const s = getComputedStyle(el);
    for (const corner of [s.borderTopLeftRadius, s.borderTopRightRadius,
                          s.borderBottomRightRadius, s.borderBottomLeftRadius]) {
      if (corner === '0px' || corner.endsWith('%')) continue;
      bad.add(corner + ' ' + el.tagName.toLowerCase() + '.' + String(el.className).split(' ')[0]);
    }
  }
  return [...bad];
}
"""


def _same_stack(a, b):
    """Font stacks compare without quotes (computed style drops them where it can)."""
    return a.replace('"', "") == b.replace('"', "")


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=seed_state_dir, fake_providers=True)


def _open_page(new_context, server, route, viewport, scheme="light", hash_=""):
    context = new_context(viewport=viewport, color_scheme=scheme)
    Hosts(context)  # the map tiles and the geocoder are served locally
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + route + hash_)
    page.wait_for_load_state("load")
    page.locator("main").wait_for(state="visible")
    page.wait_for_function(FINITE_ANIMATIONS_DONE, timeout=10000)
    return context, page


@pytest.mark.parametrize("scheme", ("light", "dark"))
@pytest.mark.parametrize("viewport", (PHONE, DESKTOP), ids=("390", "1440"))
@pytest.mark.parametrize("path", PAGES)
def test_titles_are_on_the_type_scale_in_the_display_face(
        new_context, server, path, viewport, scheme):
    context, page = _open_page(new_context, server, path, viewport, scheme)
    try:
        read = page.evaluate(_TITLES)
        assert read["pageTitles"], (path, "no page title")
        assert read["h1Count"] == 1, (path, "exactly one h1 per page")
        low, high = (30, 34) if viewport["width"] < 960 else (40, 44)
        if path == "/":
            # Home's title is the frame name in the hero: 28px on a phone, 48px on a desktop.
            low, high = (28, 28) if viewport["width"] < 960 else (48, 48)
        for title in read["pageTitles"]:
            assert _same_stack(title["family"], read["display"]), title
            assert low <= title["size"] <= high, (path, viewport["width"], title)
            assert title["weight"] == "700", title
            assert abs(title["em"] - (-0.03)) < 0.002, title
        for title in read["sectionTitles"]:
            assert _same_stack(title["family"], read["display"]), title
            assert title["size"] == 22 and title["weight"] == "600", title
        for heading in read["headings"]:
            assert not any(face in heading["family"] for face in SERIF_FACES), heading
            assert any(_same_stack(heading["family"], read[k]) for k in ("display", "ui")), heading
    finally:
        context.close()


@pytest.mark.parametrize("viewport", (PHONE, DESKTOP), ids=("390", "1440"))
@pytest.mark.parametrize("path", PAGES)
def test_no_label_is_tracked_uppercase_and_every_radius_is_a_token(
        new_context, server, path, viewport):
    context, page = _open_page(new_context, server, path, viewport)
    try:
        assert page.evaluate(_NO_UPPERCASE) == [], path
        tokens = page.evaluate(
            """() => ['--radius-control', '--radius-card', '--radius-pill', '--radius-sheet'].map(
                (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim())""")
        assert tokens == ["14px", "22px", "32px", "28px"]
        # 9px is the icon chip's own radius (--radius-chip), 28px the sheets' (--radius-sheet).
        allowed = {"14px", "13px", "22px", "32px", "9px", "28px"}
        # The vendored Leaflet map controls carry their own radii and are not ours.
        stray = [item for item in page.evaluate(_RADII)
                 if item.split(" ")[0] not in allowed and ".leaflet-" not in item]
        assert stray == [], (path, stray)
    finally:
        context.close()


_PHONE_BARS = """
() => {
  const pad = (sel) => { const e = document.querySelector(sel);
    return e ? getComputedStyle(e) : null; };
  const header = pad('.site-header'), content = pad('.page-content');
  const barBox = document.querySelector('.tab-bar').getBoundingClientRect();
  return {
    headerTop: parseFloat(header.paddingTop), headerLeft: parseFloat(header.paddingLeft),
    barBottom: window.innerHeight - barBox.bottom, barRight: window.innerWidth - barBox.right,
    contentLeft: parseFloat(content.paddingLeft), contentRight: parseFloat(content.paddingRight),
    resolved: getComputedStyle(document.documentElement).getPropertyValue('--safe-bottom').trim(),
  };
}
"""

_FORCED_INSETS = ":root { --safe-top: 47px; --safe-bottom: 34px; --safe-left: 40px; --safe-right: 40px; }"


def test_fixed_bars_and_header_follow_the_safe_area_tokens(new_context, server):
    """A headless browser has no notch, so env(safe-area-inset-*) is 0 here; the tokens the
    stylesheet builds those paddings from are forced instead, which proves every bar pads itself
    with them (that the tokens ARE the env() values is checked on the stylesheet)"""
    context, page = _open_page(new_context, server, "/", PHONE)
    try:
        before = page.evaluate(_PHONE_BARS)
        assert before["barBottom"] == 6 and before["headerTop"] == 4
        page.add_style_tag(content=_FORCED_INSETS)
        page.wait_for_function(
            "() => window.innerHeight - document.querySelector('.tab-bar')"
            ".getBoundingClientRect().bottom === 6 + 34")
        after = page.evaluate(_PHONE_BARS)
        assert after["headerTop"] == 4 + 47
        assert after["headerLeft"] == 40 and after["barRight"] == 40
        assert after["barBottom"] == 6 + 34
        assert after["contentLeft"] == 40 and after["contentRight"] == 40
        top = page.evaluate("() => document.querySelector('.site-header').getBoundingClientRect().height")
        assert top >= 52 + 47
    finally:
        context.close()


def test_sheets_and_the_save_bar_clear_the_home_indicator(new_context, server):
    context, page = _open_page(new_context, server, "/", PHONE, hash_="#dlg-quiet-hours")
    page.locator("dialog[open]").wait_for(state="visible")
    try:
        page.add_style_tag(content=_FORCED_INSETS)
        page.wait_for_function(
            "() => parseFloat(getComputedStyle(document.querySelector("
            "'dialog[open] .modal__actions')).paddingBottom) === 50")
        sheet = page.evaluate(
            """() => { const s = getComputedStyle(document.querySelector('dialog[open]'));
                return {left: parseFloat(s.paddingLeft), right: parseFloat(s.paddingRight)}; }""")
        assert sheet == {"left": 40, "right": 40}
    finally:
        context.close()


@pytest.mark.parametrize("scheme,colour", (("light", "#E7EEF7"), ("dark", "#12151D")))
def test_the_theme_colour_follows_the_explicit_theme_and_the_root_paints_the_sky(
        new_context, server, scheme, colour):
    context, page = _open_page(new_context, server, "/account", PHONE, "light")
    try:
        context.add_cookies([{"name": UI_THEME_COOKIE_NAME, "value": scheme,
                              "url": server.base_url()}])
        page.reload()
        page.wait_for_function(FINITE_ANIMATIONS_DONE)
        tags = page.evaluate(
            "() => [...document.querySelectorAll('meta[name=theme-color]')].map(m => m.content)")
        assert tags == [colour, colour]
        assert page.evaluate(
            "() => document.querySelector('meta[name=viewport]').content").endswith("viewport-fit=cover")
        sky = page.evaluate(
            """() => { const s = getComputedStyle(document.documentElement);
                return {image: s.backgroundImage, colour: s.backgroundColor,
                        top: s.getPropertyValue('--sky-top').trim().toUpperCase()}; }""")
        assert sky["top"] == colour and sky["image"].startswith("linear-gradient")
    finally:
        context.close()
