"""The dimmed, blurred layer behind the open More sheet covers everything the window shows: the
whole window on every page, and on the Location page of an iPhone also the map that runs above and
below the page, which iOS draws under the status bar and under a tab's toolbar and which a fixed
layer sized to the window cannot reach.

Headless Chromium has no safe area, so the insets are forced the way the Location tests do."""
import pytest

from companion import auth
from companion.test_browser_ux_helpers import _login
from place_map_support import SETTLED, Hosts, seed as _seed

pytestmark = pytest.mark.browser

READY = "() => document.documentElement.classList.contains('map-ready')"
ANIMATIONS_DONE = (
    "() => document.getAnimations().every("
    "(a) => a.playState !== 'running' || a.effect.getComputedTiming().iterations === Infinity)")
SAFE = (
    "() => { const s = document.documentElement.style;"
    " s.setProperty('--safe-top', '59px'); s.setProperty('--safe-bottom', '34px'); }")
IPHONE = (
    "Object.defineProperty(Navigator.prototype, 'standalone',"
    " {get: () => false, configurable: true});")
PAGES = ["/", "/flights", "/detection"]
PHONES = [{"width": 360, "height": 740}, {"width": 390, "height": 844}]

# The fixed scrim's box, and the box and paint of the layers that dim the map above and below the
# page, in window coordinates, next to the map's own box.
COVER = """() => {
  const h = innerHeight, w = innerWidth;
  const scrim = getComputedStyle(document.body, '::after');
  const fixed = {top: 0, bottom: h, ok: scrim.position === 'fixed'
    && scrim.backdropFilter.includes('blur') && Math.abs(parseFloat(scrim.height) - h) <= 1
    && Math.abs(parseFloat(scrim.width) - w) <= 1};
  const map = document.getElementById('place-map');
  const out = {fixed, mapBox: null, layers: [], at2: document.elementFromPoint(w / 2, 2) === document.body,
               atEnd: document.elementFromPoint(w / 2, h - 2) === document.body};
  if (!map) return out;
  const m = map.getBoundingClientRect();
  out.mapBox = [m.top, m.bottom];
  const host = document.querySelector('.page-content').getBoundingClientRect();
  for (const which of ['::before', '::after']) {
    const s = getComputedStyle(document.querySelector('.page-content'), which);
    if (s.content === 'none') continue;
    const top = which === '::before' ? host.top + parseFloat(s.top) : host.bottom - parseFloat(s.bottom) - parseFloat(s.height);
    out.layers.push({which, top, bottom: top + parseFloat(s.height), blur: s.backdropFilter,
                     alpha: s.backgroundColor, position: s.position});
  }
  return out; }"""


def _open(new_context, server, path, viewport, lang, scheme, iphone):
    context = new_context(viewport=viewport, color_scheme=scheme)
    if iphone:
        context.add_init_script(IPHONE)
    Hosts(context)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + path)
    page.locator(".tab-bar").wait_for(state="visible")
    if path == "/detection":
        page.wait_for_function(READY, timeout=15000)
        page.wait_for_function(SETTLED, timeout=10000)
    page.wait_for_function(ANIMATIONS_DONE, timeout=10000)
    page.evaluate(SAFE)
    return context, page


def _uncovered(probe):
    """The stretches of the map the fixed scrim and the extra layers leave undimmed."""
    spans = [(probe["fixed"]["top"], probe["fixed"]["bottom"])]
    spans += [(layer["top"], layer["bottom"]) for layer in probe["layers"]]
    top, bottom = probe["mapBox"]
    gaps, y = [], top
    for a, b in sorted(spans):
        if a > y + 1:
            gaps.append((y, a))
        y = max(y, b)
    if y < bottom - 1:
        gaps.append((y, bottom))
    return gaps


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=_seed, fake_providers=True)


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("path", PAGES)
@pytest.mark.parametrize("viewport", PHONES, ids=["360", "390"])
def test_the_open_sheet_dims_and_blurs_the_whole_window_on_every_page(
        new_context, server, viewport, path, lang, scheme):
    """the scrim is a fixed, blurred layer exactly the window's size and the topmost thing at the
    window's first and last rows, with the status bar and the bottom toolbar insets in force"""
    context, page = _open(new_context, server, path, viewport, lang, scheme, iphone=True)
    try:
        page.locator(".tab-bar__more > summary").click()
        page.locator(".tab-bar__more-panel").wait_for(state="visible")
        probe = page.evaluate(COVER)
        assert probe["fixed"]["ok"] and probe["at2"] and probe["atEnd"], probe
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", PHONES, ids=["360", "390"])
def test_the_open_sheet_also_dims_and_blurs_the_map_above_and_below_the_location_page(
        new_context, server, viewport, lang, scheme):
    """on an iPhone the map runs past the window and iOS shows that part under the status bar and
    the toolbar, so the lead and the tail carry the same dim and blur in the page itself"""
    context, page = _open(new_context, server, "/detection", viewport, lang, scheme, iphone=True)
    try:
        page.wait_for_function(
            "() => Math.abs(window.scrollY - 80) < 1", timeout=5000)
        page.locator(".tab-bar__more > summary").click()
        page.locator(".tab-bar__more-panel").wait_for(state="visible")
        probe = page.evaluate(COVER)
        assert probe["mapBox"][0] < 0 and probe["mapBox"][1] > viewport["height"], probe
        assert _uncovered(probe) == [], probe
        assert all("blur" in layer["blur"] for layer in probe["layers"]), probe
        assert len(probe["layers"]) == 2, probe
        # Closed again, the page behind has no extra layer.
        page.keyboard.press("Escape")
        page.wait_for_function("() => !document.querySelector('.tab-bar__more').open", timeout=5000)
        assert page.evaluate(COVER)["layers"] == []
    finally:
        context.close()


@pytest.mark.parametrize("path", ["/detection", "/flights"])
def test_a_wide_window_has_no_more_sheet_and_so_no_scrim(new_context, server, path):
    context = new_context(viewport={"width": 1280, "height": 800})
    Hosts(context)
    page = context.new_page()
    _login(page, server.base_url())
    try:
        page.goto(server.base_url() + path)
        page.wait_for_function("() => document.readyState === 'complete'")
        probe = page.evaluate(COVER)
        assert probe["layers"] == [] and not probe["fixed"]["ok"], probe
    finally:
        context.close()
