"""Real-browser checks of the admin Components page: the two samples that used to clip now wrap,
and the families the catalogue was missing (`.page-section`, `.fleet-tile` and its compact form,
`.dot--off`, `.dot--hollow`) are on the page, drawn by the product stylesheet.

Run at 360 and 1280 px, English and French, Light and Dark, as an administrator."""
import animation_settle
import pytest

import fleet_console_support as fx
from companion import auth
from companion.test_browser_components_helpers import wait_until_measurable
from companion_app_server import session_cookie_for_state_dir

pytestmark = pytest.mark.browser

VIEWPORTS = {"360": {"width": 360, "height": 740}, "1280": {"width": 1280, "height": 900}}

# A canvas turns any CSS colour syntax (color-mix results included) into plain RGBA; a background
# is the stack of translucent layers up to the root.
HELPERS = """
(() => {
  const canvas = document.createElement('canvas'); canvas.width = canvas.height = 1;
  const ctx = canvas.getContext('2d', {willReadFrequently: true});
  const rgba = (css) => { ctx.clearRect(0, 0, 1, 1); ctx.fillStyle = '#000'; ctx.fillStyle = css;
    ctx.fillRect(0, 0, 1, 1); const d = ctx.getImageData(0, 0, 1, 1).data;
    return [d[0], d[1], d[2], d[3] / 255]; };
  const over = (top, under) => { const a = top[3]; return [0, 1, 2].map((i) =>
    top[i] * a + under[i] * (1 - a)).concat([1]); };
  const background = (el) => { const layers = [];
    for (let n = el; n; n = n.parentElement) { layers.push(rgba(getComputedStyle(n).backgroundColor)); }
    let out = [255, 255, 255, 1];
    if (matchMedia('(prefers-color-scheme: dark)').matches) {
      out = rgba(getComputedStyle(document.documentElement).getPropertyValue('--color-canvas') || '#000'); }
    for (let i = layers.length - 1; i >= 0; i--) { out = over(layers[i], out); } return out; };
  const lum = (c) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 :
      Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  window.__c = {rgba, over, background, ratio};
})();
"""

# The "Wake interval" card (the first group of rows of the cards family) and the docked unsaved
# changes bar: neither may cut anything off; the bar's message wraps when its words do not fit.
FIT = """() => {
  const group = document.querySelector('#components-cards ul.group');
  const gr = group.getBoundingClientRect();
  const past = [...group.querySelectorAll('*')].filter((el) => {
    const r = el.getBoundingClientRect(); return r.width > 0 && r.right > gr.right + 0.5; })
    .map((el) => el.className.toString());
  const message = document.querySelector(
    '#components-dialogs .components-save-bar:not(.components-save-bar--inline) .dirty-bar__message');
  const style = getComputedStyle(message);
  const probe = message.cloneNode(true);
  probe.style.cssText = 'position:absolute;visibility:hidden;white-space:nowrap;overflow:visible;width:auto';
  message.parentElement.appendChild(probe);
  const natural = probe.getBoundingClientRect().width; probe.remove();
  const range = document.createRange(); range.selectNodeContents(message);
  const lines = new Set([...range.getClientRects()].map((r) => Math.round(r.top))).size;
  return {
    groupScrolls: group.scrollWidth > group.clientWidth + 0.5, past,
    messageScrolls: message.scrollWidth > message.clientWidth + 0.5
      || message.scrollHeight > message.clientHeight + 1,
    ellipsis: style.textOverflow === 'ellipsis', natural, available: message.clientWidth, lines,
    pageScrolls: document.documentElement.scrollWidth > document.documentElement.clientWidth,
  };
}"""

CATALOGUE = """() => {
  const q = (sel) => [...document.querySelectorAll('.components-state ' + sel)];
  const shown = (el) => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const dot = (cls) => q('.dot.' + cls).map((el) => {
    const label = el.nextElementSibling; const box = el.getBoundingClientRect();
    return {w: box.width, h: box.height, word: label && label.classList.contains('dot-label')
      && shown(label) ? label.textContent.trim() : ''}; });
  return {
    sections: q('.page-section').length,
    sectionTones: ['ok', 'warn'].map((t) => q('.page-section.page-section--' + t).length),
    tiles: q('.fleet-tile').length, linkTiles: q('a.fleet-tile').length,
    compactTiles: q('.fleet-tiles--system .fleet-tile').length,
    tileHeights: q('.fleet-tile').filter(shown).map((el) => el.getBoundingClientRect().height),
    ok: dot('dot--ok'), off: dot('dot--off'), hollow: dot('dot--hollow'),
  };
}"""

CONTRAST = """() => {
  const c = window.__c; const out = [];
  const sel = '.components-state .page-section, .components-state .fleet-tile, '
    + '.components-state .dot-label';
  for (const root of document.querySelectorAll(sel)) {
    const leaves = root.matches('.dot-label') ? [root]
      : [...root.querySelectorAll('*')].filter((el) => el.children.length === 0
        && (el.textContent || '').trim() && !el.closest('.visually-hidden'));
    for (const el of leaves) {
      const bg = c.background(el); const fg = c.over(c.rgba(getComputedStyle(el).color), bg);
      out.push([el.className.toString(), (el.textContent || '').trim().slice(0, 24), c.ratio(fg, bg)]);
    }
  }
  return out;
}"""

RUNNING = """() => document.getAnimations()
  .filter((a) => a.playState === 'running')
  .map((a) => (a.effect && a.effect.target ? a.effect.target.className : '') + ' '
    + (a.animationName || a.transitionProperty || ''))"""


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=fx.seed_users)


def _wait_for_settled_document(page):
    page.wait_for_function(animation_settle.SETTLED, timeout=10000)


def _open(new_context, server, width, theme, lang, wait=wait_until_measurable, **context_kwargs):
    context = new_context(viewport=VIEWPORTS[width], color_scheme=theme, **context_kwargs)
    name, value = session_cookie_for_state_dir(server.state_dir, fx.ADMIN_EMAIL).split("=", 1)
    context.add_cookies([
        {"name": name, "value": value, "url": server.base_url(), "httpOnly": True,
         "sameSite": "Strict"},
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    page.goto(server.base_url() + "/components")
    wait(page)
    page.evaluate(HELPERS)
    return context, page


PARAMS = [(w, t, lang) for w in ("360", "1280") for t in ("light", "dark") for lang in ("en", "fr")]


@pytest.fixture(scope="module")
def shared_components(module_new_context, server):
    """One loaded Components page per parameter set, opened the first time a test asks for it
    and kept for the rest of the module. Every test using it only reads the page."""
    pages = {}

    def page_for(params):
        if params not in pages:
            pages[params] = _open(module_new_context, server, *params)[1]
        page = pages[params]
        page.evaluate("() => window.scrollTo(0, 0)")
        return page

    return page_for


@pytest.fixture(params=PARAMS, ids=["%s-%s-%s" % p for p in PARAMS])
def components(request, shared_components):
    return shared_components(request.param)


def test_the_wake_interval_card_and_the_unsaved_bar_show_all_their_text(components):
    found = components.evaluate(FIT)
    assert not found["groupScrolls"], "the card is wider than its box: text or a control is cut"
    assert found["past"] == [], "a part of the card sticks out of it"
    assert not found["messageScrolls"], "the unsaved bar message is cut"
    assert not found["ellipsis"], "the sample message is shortened with an ellipsis"
    if found["natural"] > found["available"] + 0.5:
        assert found["lines"] > 1, "a message wider than its box has to wrap onto a second line"
    assert not found["pageScrolls"]


def test_the_catalogue_shows_the_four_missing_families_with_a_word_beside_each_dot(components):
    found = components.evaluate(CATALOGUE)
    assert found["sections"] >= 3 and found["sectionTones"] == [1, 1]
    assert found["tiles"] >= 6 and found["linkTiles"] >= 1 and found["compactTiles"] >= 2
    assert found["ok"], "no live dot to compare with"
    for name in ("off", "hollow"):
        assert found[name], "no .dot--%s sample" % name
        for dot in found[name]:
            assert dot["w"] > 0 and dot["h"] > 0, name
            assert dot["word"], "a .dot--%s sample has no visible word beside it" % name
    assert all(height >= 44 for height in found["tileHeights"]), found["tileHeights"]


def test_the_off_and_hollow_dots_are_drawn_differently_from_the_live_dot(components):
    shots = {name: components.locator(".components-state .dot.dot--%s" % name).first.screenshot()
             for name in ("ok", "off", "hollow")}
    assert shots["off"] != shots["ok"]
    assert shots["hollow"] != shots["ok"]
    assert shots["off"] != shots["hollow"]


def test_the_new_samples_keep_text_contrast_of_four_and_a_half_to_one(components):
    found = components.evaluate(CONTRAST)
    assert found, "no new sample text to measure"
    weak = [item for item in found if item[2] < 4.5]
    assert weak == []


def test_nothing_is_animated_under_reduced_motion(new_context, server):
    for lang in ("en", "fr"):
        context, page = _open(
            new_context, server, "360", "light", lang, wait=_wait_for_settled_document,
            reduced_motion="reduce")
        try:
            assert page.evaluate(RUNNING) == []
        finally:
            context.close()
