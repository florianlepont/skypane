"""The page opening and the tab strips, read in a real browser.

Every page opens the same way: the shell marks <main> with data-page-open and the page header
plus the first screenful of blocks enter with Home's card entrance (a fade and a short rise),
compositor properties only. Lists, tables and rows are never animated, and a tall page animates
at most a header and five blocks. Every segmented strip marked data-tabs slides one thumb under
its current segment, and the content a strip switches replays the same entrance. Reduced motion
turns all of it into an instant change. The bottom tab bar's sliding pill is on every page,
including the ones that belong to no bar cell.
"""
import json

import pytest

import fleet_console_support as fx
import companion.test_view_pages_helpers as vp
from companion import auth
from companion.pages import history_page
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _login, seed_state_dir)
from place_map_support import SETTLED, Hosts, seed as place_seed

pytestmark = pytest.mark.browser

VIEWPORTS = (
    pytest.param(VIEWPORT_MIN_SUPPORTED, id="360"),
    pytest.param(VIEWPORT_DESKTOP, id="1280"))

# (path, tall): a tall page is one whose list or table can grow without bound; it opens with
# the header and at most five blocks. Every other page stays within eight animated elements.
PAGES = (
    ("/", False),
    ("/flights", True),
    ("/detection", False),
    ("/display", False),
    ("/display/arrivals", False),
    ("/display/special-looks", False),
    ("/display/special-looks/new", False),
    ("/display/calendar", False),
    ("/fleet", False),
    ("/fleet?view=system", False),
    ("/update", False),
    ("/users", True),
    ("/audit", True),
    ("/account", False),
    ("/airlines", True),
    ("/airlines/manage", True),
    ("/components", True),
    ("/credits", True),
    ("/not-a-page", False),
)
TALL_LIMIT = 6
PAGE_LIMIT = 8

# Elements that are rows of a list or table: none of them may ever carry an entrance.
_ROW = ("tr, tbody, thead, td, th, li, .collection-item, .entity-row, .audit-event, "
        ".history-card, .airline-group")
_FORBIDDEN = ("margin", "height", "max-height", "min-height", "filter", "backdrop-filter",
              "width", "top", "left", "right", "bottom", "inset", "padding", "font-size")

_RECORD = """
window.__anim = [];
document.addEventListener('animationstart', (e) => {
  const t = e.target;
  window.__anim.push({name: e.animationName, tag: t.tagName.toLowerCase(),
    cls: String(t.className || ''), row: !!(t.matches && t.matches(%r))});
}, true);
""" % _ROW

# The shell marks <main> for the opening and the mark leaves once the opening has played.
# Read the moment the parser adds <main>: the script may drop the mark before the document is
# fully loaded (an opening without duration is over at once).
_MARK_AT_START = """
window.__opened = null;
new MutationObserver((records, observer) => {
  const main = document.querySelector('main');
  if (main) { window.__opened = main.hasAttribute('data-page-open'); observer.disconnect(); }
}).observe(document, {childList: true, subtree: true});
"""
_OPENING_OVER = "() => !document.querySelector('main[data-page-open]')"

_SETTLED_PAGE = (
    "() => document.readyState === 'complete' && document.getAnimations().every("
    "(a) => a.playState !== 'running' || a.effect.getComputedTiming().iterations === Infinity)")

_KEYFRAME_PROPERTIES = """(names) => {
  const found = [];
  for (const sheet of document.styleSheets) {
    for (const rule of sheet.cssRules) {
      if (rule.type === CSSRule.KEYFRAMES_RULE && names.includes(rule.name)) {
        for (const frame of rule.cssRules) {
          for (const prop of frame.style) { found.push(rule.name + ':' + prop); }
        }
      }
    }
  }
  return found;
}"""


def _seed(state_dir):
    seed_state_dir(state_dir)
    fx.seed_fleet(state_dir)


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=_seed, fake_providers=True)


def _admin_context(new_context, server, viewport, **options):
    name, value = fx.admin_cookie(server.state_dir).split("=", 1)
    context = new_context(viewport=viewport, **options)
    context.add_cookies([
        {"name": name, "value": value, "url": server.base_url(),
         "httpOnly": True, "sameSite": "Strict"}])
    context.add_init_script(_RECORD)
    context.add_init_script(_MARK_AT_START)
    Hosts(context)
    return context


def _open(page, server, path):
    page.goto(server.base_url() + path)
    page.locator("main").wait_for(state="visible")
    page.wait_for_function(_SETTLED_PAGE, timeout=15000)


@pytest.mark.parametrize("viewport", VIEWPORTS)
@pytest.mark.parametrize("path,tall", PAGES, ids=[p for p, _t in PAGES])
def test_every_page_opens_with_the_shared_entrance(new_context, server, path, tall, viewport):
    """the shell marks main, the page header enters, no row or table animates, a tall page
    animates a header and at most five blocks, the entrance moves nothing but opacity and
    translate, and the mark leaves when the opening is over"""
    context = _admin_context(new_context, server, viewport, reduced_motion="no-preference")
    try:
        page = context.new_page()
        _open(page, server, path)
        assert page.evaluate("() => window.__opened") is True
        page.wait_for_function(_OPENING_OVER, timeout=10000)
        events = page.evaluate("() => window.__anim")
        entering = [e for e in events if e["name"] == "skypane-reveal-fade"]
        assert any("page-header" in e["cls"] for e in entering), (path, events)
        assert not [e for e in entering if e["row"]], (path, "a row animates", entering)
        limit = TALL_LIMIT if tall else PAGE_LIMIT
        assert len(entering) <= limit, (path, len(entering), entering)
        names = sorted({e["name"] for e in events if e["name"].startswith("skypane-reveal")})
        used = page.evaluate(_KEYFRAME_PROPERTIES, names)
        assert used, (path, "the entrance keyframes were not found")
        assert {u.split(":")[1] for u in used} <= {"opacity", "transform"}, (path, used)
        for entry in used:
            assert not any(entry.split(":")[1].startswith(f) for f in _FORBIDDEN), entry
    finally:
        context.close()


@pytest.mark.parametrize("viewport", VIEWPORTS)
@pytest.mark.parametrize("path", [p for p, _t in PAGES], ids=[p for p, _t in PAGES])
def test_under_reduced_motion_every_page_opens_at_once(new_context, server, path, viewport):
    """with prefers-reduced-motion the entrance has no duration and no delay: the page is
    already settled when it first paints"""
    context = _admin_context(new_context, server, viewport, reduced_motion="reduce")
    try:
        page = context.new_page()
        _open(page, server, path)
        assert page.evaluate("() => window.__opened") is True
        durations = page.evaluate(
            "() => [...document.querySelectorAll('main > *')].map((e) => {"
            " const s = getComputedStyle(e);"
            " return s.animationName === 'none' ? 0 : Math.max(...s.animationDuration"
            ".split(',').map(parseFloat), ...s.animationDelay.split(',').map(parseFloat)); })")
        assert max(durations) < 0.001, (path, durations)
        assert not page.evaluate("() => document.querySelector('.tabs-thumb.is-sliding')")
        assert not page.evaluate("() => document.querySelector('.reveal-replay, .reveal-appended')")
    finally:
        context.close()


# The blocks that take the entrance, in page order, read when the document is parsed: the
# delay of each, whether it rises as well as fades, and whether it sits inside another one.
_BLOCKS_AT_OPEN = """
(() => {
  // Read on every frame from the first one the browser draws: an entrance that has ended
  // is no longer listed, and a slow load can end the first ones before the document is done.
  const seen = new Map();
  const rising = new Set();
  let frames = 0;
  const publish = () => {
    const targets = [...seen.keys()];
    const blocks = targets.map((el) => {
      const box = el.getBoundingClientRect();
      return {el: el, cls: el.tagName.toLowerCase() + '.' + String(el.className),
              delay: seen.get(el), top: box.top, height: box.height, rises: rising.has(el),
              nested: targets.some((other) => other !== el && other.contains(el))};
    });
    blocks.sort((a, b) => (a.el.compareDocumentPosition(b.el) & 4 ? -1 : 1));
    window.__taking = (selector) => [...document.querySelectorAll(selector)]
      .filter((el) => el.getClientRects().length)
      .map((el) => ({fades: seen.has(el), rises: rising.has(el)}));
    window.__step = parseFloat(getComputedStyle(document.documentElement)
      .getPropertyValue('--motion-stagger'));
    window.__blocks = blocks.map((b) => { delete b.el; return b; });
  };
  const read = () => {
    for (const a of document.getAnimations()) {
      if (a.animationName === 'skypane-reveal-fade' && !seen.has(a.effect.target)) {
        seen.set(a.effect.target, a.effect.getTiming().delay);
      }
      if (a.animationName === 'skypane-reveal') { rising.add(a.effect.target); }
    }
    if (document.readyState === 'complete' && frames++ > 2) { publish(); return; }
    requestAnimationFrame(read);
  };
  requestAnimationFrame(read);
})();
"""

_STEP_PAGES = (
    "/", "/flights", "/display", "/display/arrivals", "/display/special-looks",
    "/display/calendar", "/fleet", "/fleet?view=system", "/users", "/audit", "/account",
    "/airlines", "/airlines/manage", "/credits", "/not-a-page")


@pytest.mark.parametrize("viewport", VIEWPORTS)
@pytest.mark.parametrize("path", _STEP_PAGES)
def test_the_blocks_of_a_page_enter_one_step_after_another(new_context, server, path, viewport):
    """One opening for every page: the header at once, then each block of the first screen
    one stagger step after the one before it, in page order, up to five steps. No block
    enters inside a block that is itself entering."""
    context = _admin_context(new_context, server, viewport, reduced_motion="no-preference")
    context.add_init_script(_BLOCKS_AT_OPEN)
    try:
        page = context.new_page()
        _open(page, server, path)
        page.wait_for_function("() => window.__blocks !== undefined", timeout=10000)
        blocks = page.evaluate("() => window.__blocks")
        step = page.evaluate("() => window.__step")
        assert step == 60, step
        assert blocks and "page-header" in blocks[0]["cls"] and blocks[0]["delay"] == 0, blocks
        assert not [b for b in blocks if b["nested"]], blocks
        first_screen = [b for b in blocks[1:] if b["top"] < viewport["height"] and b["height"]]
        assert first_screen, blocks
        delays = [b["delay"] for b in first_screen]
        assert delays == [min(k, 5) * step for k in range(1, len(delays) + 1)], (
            path, [(b["cls"][:44], b["delay"], round(b["top"])) for b in blocks])
    finally:
        context.close()


def test_each_fleet_tab_opens_in_the_same_order_on_a_phone(new_context, server):
    """Whatever tab a phone shows, the frame's header row, the tabs and then that tab's own
    blocks enter one step apart: blocks of the hidden tabs take no place in the count."""
    context = _admin_context(new_context, server, VIEWPORT_MIN_SUPPORTED,
                             reduced_motion="no-preference")
    context.add_init_script(_BLOCKS_AT_OPEN)
    try:
        page = context.new_page()
        _open(page, server, "/fleet")
        hrefs = page.evaluate(
            "() => [...document.querySelectorAll('[data-tabs=\"fleet\"] a')]"
            ".map((a) => a.getAttribute('href'))")
        assert len(hrefs) == 3, hrefs
        for href in hrefs:
            _open(page, server, href)
            page.wait_for_function("() => window.__blocks !== undefined", timeout=10000)
            blocks = [b for b in page.evaluate("() => window.__blocks") if b["height"]]
            delays = [b["delay"] for b in blocks]
            assert len(delays) >= 4, (href, blocks)
            assert delays == [min(k, 5) * 60 for k in range(len(delays))], (
                href, [(b["cls"][:50], b["delay"]) for b in blocks])
    finally:
        context.close()


# (path, viewport, blocks that rise and fade, lists that only fade): the parts of a first
# screen that used to stay still while the rest of the page entered.
_TAKING_PART = (
    ("/display", VIEWPORT_MIN_SUPPORTED, (".layout-card", ".personalisation-nav"), ()),
    ("/display", VIEWPORT_DESKTOP, (".layout-card", ".personalisation-nav"), ()),
    ("/fleet", VIEWPORT_MIN_SUPPORTED, (".fleet-detail-head", ".fleet-tabs"), ()),
    ("/audit", VIEWPORT_MIN_SUPPORTED, (), (".filter-bar__count", ".audit-cards")),
    ("/audit", VIEWPORT_DESKTOP, (), (".filter-bar__count", ".audit-cards")),
    ("/airlines", VIEWPORT_MIN_SUPPORTED, (), ("#collection-grid",)),
    ("/airlines", VIEWPORT_DESKTOP, (), ("#collection-grid",)),
    ("/airlines/manage", VIEWPORT_MIN_SUPPORTED, (), (".airlines-table",)),
    ("/airlines/manage", VIEWPORT_DESKTOP, (), (".airlines-table",)),
)


@pytest.mark.parametrize(
    "path,viewport,rising,fading", _TAKING_PART,
    ids=["%s@%d" % (p, v["width"]) for p, v, _r, _f in _TAKING_PART])
def test_every_block_of_the_first_screen_takes_part_in_the_opening(
        new_context, server, path, viewport, rising, fading):
    """A card, a strip or a control row rises and fades. A list, a grid or a table as tall as
    its data fades as a whole and never rises: opacity alone, one layer."""
    context = _admin_context(new_context, server, viewport, reduced_motion="no-preference")
    context.add_init_script(_BLOCKS_AT_OPEN)
    try:
        page = context.new_page()
        _open(page, server, path)
        page.wait_for_function("() => window.__blocks !== undefined", timeout=10000)
        for selector in rising:
            found = page.evaluate("(s) => window.__taking(s)", selector)
            assert found and all(f["fades"] and f["rises"] for f in found), (selector, found)
        for selector in fading:
            found = page.evaluate("(s) => window.__taking(s)", selector)
            assert found and all(f["fades"] and not f["rises"] for f in found), (selector, found)
    finally:
        context.close()


def _thumb_matches_current(page, selector):
    return page.evaluate(
        "(s) => { const strip = document.querySelector(s);"
        " const thumb = strip.querySelector('[data-tabs-thumb]').getBoundingClientRect();"
        " const cur = [...strip.children].find((c) => c.hasAttribute('aria-current')"
        " || c.querySelector('input:checked'));"
        " const face = (cur.querySelector('.filter-chip__box') || cur.querySelector('span')"
        " || cur).getBoundingClientRect();"
        " return Math.abs(thumb.left - face.left) <= 1.5 && Math.abs(thumb.top - face.top) <= 1.5"
        " && Math.abs(thumb.width - face.width) <= 1.5; }", selector)


def _wait_sliding(page, selector):
    page.wait_for_function(
        "(s) => document.querySelector(s + ' [data-tabs-thumb]').classList.contains('is-sliding')",
        arg=selector, timeout=10000)
    page.wait_for_function(_SETTLED_PAGE, timeout=10000)
    assert _thumb_matches_current(page, selector), selector


def _entered_since(page, mark):
    return page.evaluate(
        "(m) => window.__anim.slice(m).filter((e) => e.name === 'skypane-reveal-fade')", mark)


# What the page change that opened this page animated, and whether a script slid a strip's
# thumb afterwards. Kept in session storage: the probe runs before the page's own scripts.
_STRIP_PROBE = """
window.addEventListener('pagereveal', (event) => {
  const save = (value) => sessionStorage.setItem('strip-probe', JSON.stringify(value));
  if (!event.viewTransition) { save({change: 'none', strip: []}); return; }
  event.viewTransition.ready.then(() => {
    const strip = document.documentElement.getAnimations({subtree: true})
      .filter((a) => a.effect && a.effect.pseudoElement
        && a.effect.pseudoElement.indexOf('(skypane-strip)') > -1)
      .map((a) => a.effect.pseudoElement.split('(')[0]);
    save({change: 'ran', strip: strip});
  }, () => save({change: 'skipped', strip: []}));
});
new MutationObserver((records) => {
  for (const record of records) {
    if (record.target.matches && record.target.matches('.tabs-thumb.is-sliding')) {
      sessionStorage.setItem('strip-slid', location.pathname + location.search);
    }
  }
}).observe(document, {attributes: true, attributeFilter: ['class'], subtree: true});
"""
_CARRIERS = (
    "() => [...document.querySelectorAll('*')].filter("
    "(e) => getComputedStyle(e).viewTransitionName === 'skypane-strip').length")


def _strip_context(new_context, server, viewport):
    context = _admin_context(new_context, server, viewport, reduced_motion="no-preference")
    context.add_init_script(_STRIP_PROBE)
    return context


def _follow(page, selector):
    """Click a link and wait for the page it opens; the probe of that page change."""
    page.evaluate("() => { sessionStorage.removeItem('strip-probe');"
                  " sessionStorage.removeItem('strip-slid'); }")
    with page.expect_navigation():
        page.locator(selector).click()
    page.wait_for_function(_SETTLED_PAGE, timeout=10000)
    page.wait_for_function("() => sessionStorage.getItem('strip-probe') !== null", timeout=10000)
    return json.loads(page.evaluate("() => sessionStorage.getItem('strip-probe')"))


def _assert_carried(page, probe, strip):
    """The page change itself glided the selection (old, new and group all animate), the thumb
    sits under the current segment and no script slid it once the page was there."""
    assert probe["change"] == "ran", probe
    for part in ("::view-transition-group", "::view-transition-old", "::view-transition-new"):
        assert part in probe["strip"], probe
    assert _thumb_matches_current(page, strip), strip
    assert page.evaluate("() => sessionStorage.getItem('strip-slid')") is None
    assert page.evaluate(_CARRIERS) == 1


@pytest.mark.parametrize("viewport", VIEWPORTS)
def test_the_audit_chips_carry_the_selection_through_the_page_change(
        new_context, server, viewport):
    """choosing another audit category loads that page: the selected chip glides to its new
    place inside the page change, and no thumb slides afterwards"""
    context = _strip_context(new_context, server, viewport)
    try:
        page = context.new_page()
        _open(page, server, "/audit")
        strip = '[data-tabs="audit"]'
        assert _thumb_matches_current(page, strip)
        probe = _follow(page, strip + " a.filter-chip:not(.filter-chip--current) >> nth=1")
        assert "category" in page.url
        _assert_carried(page, probe, strip)
    finally:
        context.close()


def test_the_fleet_tabs_carry_the_selection_through_the_page_change(new_context, server):
    """on a phone the State, Settings and Access tabs hand the selection over like the Style
    tabs"""
    context = _strip_context(new_context, server, VIEWPORT_MIN_SUPPORTED)
    try:
        page = context.new_page()
        _open(page, server, "/fleet")
        strip = '[data-tabs="fleet"]'
        assert _thumb_matches_current(page, strip)
        probe = _follow(page, strip + " a:not([aria-current]) >> nth=0")
        assert "tab=" in page.url
        _assert_carried(page, probe, strip)
    finally:
        context.close()


@pytest.mark.parametrize("viewport", VIEWPORTS)
def test_the_style_tabs_carry_the_selection_through_the_page_change(
        new_context, server, viewport):
    context = _strip_context(new_context, server, viewport)
    try:
        page = context.new_page()
        _open(page, server, "/display")
        strip = '[data-tabs="display"]'
        assert _thumb_matches_current(page, strip)
        probe = _follow(page, strip + " a:not([aria-current]) >> nth=1")
        assert not page.url.endswith("/display")
        _assert_carried(page, probe, strip)
    finally:
        context.close()


def test_a_strip_reached_another_way_moves_nothing(new_context, server):
    """Style on Special looks, Home by the tab bar, Style again by the tab bar: the strip
    leaves and comes back with its page (a fade in place), nothing glides from one segment
    to another and the thumb does not slide."""
    context = _strip_context(new_context, server, VIEWPORT_MIN_SUPPORTED)
    try:
        page = context.new_page()
        _open(page, server, "/display/special-looks")
        home = _follow(page, ".tab-bar a.tab-bar__link >> nth=0")
        assert "::view-transition-new" not in home["strip"], home
        style = _follow(page, '.tab-bar a.tab-bar__link[href$="/display"]')
        assert style["change"] == "ran" and "::view-transition-old" not in style["strip"], style
        assert page.evaluate("() => sessionStorage.getItem('strip-slid')") is None
        assert _thumb_matches_current(page, '[data-tabs="display"]')
    finally:
        context.close()


# What moves while the page change that opened this page runs: the block entrances that
# take time, and how long and on which curve the whole-page cross-fade runs.
_ARRIVAL_PROBE = """
window.addEventListener('pagereveal', (event) => {
  const save = (value) => sessionStorage.setItem('arrival-probe', JSON.stringify(value));
  if (!event.viewTransition) { save({change: 'none'}); return; }
  event.viewTransition.ready.then(() => {
    const all = document.documentElement.getAnimations({subtree: true});
    const entrances = all.filter((a) => /^skypane-reveal/.test(a.animationName || '')
        && a.effect.getComputedTiming().activeDuration + a.effect.getComputedTiming().delay > 1)
      .map((a) => a.animationName + ' on ' + a.effect.target.className);
    const root = all.filter((a) => a.effect.pseudoElement
        && a.effect.pseudoElement.indexOf('(root)') > -1)
      .map((a) => [a.effect.pseudoElement.split('(')[0], a.effect.getTiming().duration,
                   getComputedStyle(document.documentElement, a.effect.pseudoElement)
                     .animationTimingFunction.split('), ')[0].replace(/\\)?$/, ')')]);
    save({change: 'ran', entrances: entrances, root: root,
          opening: !!document.querySelector('main[data-page-open]')});
  }, () => save({change: 'skipped'}));
});
"""


def _arrive(page, selector):
    page.evaluate("() => sessionStorage.removeItem('arrival-probe')")
    with page.expect_navigation():
        page.locator(selector).click()
    page.wait_for_function(_SETTLED_PAGE, timeout=10000)
    page.wait_for_function(
        "() => sessionStorage.getItem('arrival-probe') !== null", timeout=10000)
    return json.loads(page.evaluate("() => sessionStorage.getItem('arrival-probe')"))


@pytest.mark.parametrize("viewport", VIEWPORTS)
def test_a_page_reached_through_the_page_change_does_not_also_play_its_entrance(
        new_context, server, viewport):
    """One motion per page change: the cross-fade. A page opened by a link from another page
    is in place under it (no block rises or fades on its own); the same page opened by its
    address still plays the entrance. The cross-fade runs on the motion tokens."""
    context = _admin_context(new_context, server, viewport, reduced_motion="no-preference")
    context.add_init_script(_ARRIVAL_PROBE)
    try:
        page = context.new_page()
        _open(page, server, "/")
        assert _entered_since(page, 0), "a page opened by its address plays the entrance"
        tokens = page.evaluate(
            "() => { const s = getComputedStyle(document.documentElement);"
            " return [parseFloat(s.getPropertyValue('--motion-view-transition')),"
            " s.getPropertyValue('--ease-out').trim()]; }")
        link = (".tab-bar" if viewport["width"] < 960 else ".dashboard-sidebar")
        for href in ("/flights", "/display"):
            probe = _arrive(page, '%s a[href$="%s"] >> nth=0' % (link, href))
            assert probe["change"] == "ran", probe
            assert probe["entrances"] == [], probe
            assert probe["root"], probe
            for _part, duration, easing in probe["root"]:
                assert duration == tokens[0], probe
                assert easing.replace(" ", "") == tokens[1].replace(" ", ""), (probe, tokens)
            page.wait_for_function(_OPENING_OVER, timeout=10000)
    finally:
        context.close()


@pytest.mark.parametrize("motion", ["no-preference", "reduce"])
def test_the_more_panel_fades_in_and_leaves_at_once(new_context, server, motion):
    """One rule for what a control opens: it fades in on the fast token and leaves at once.
    The panel never changes size while it arrives (its rows are tap targets from the first
    frame). Reduced motion shows it at once."""
    context = _admin_context(new_context, server, VIEWPORT_MIN_SUPPORTED, reduced_motion=motion)
    try:
        page = context.new_page()
        _open(page, server, "/")
        mark = page.evaluate("() => window.__anim.length")
        page.locator(".tab-bar__more > summary").click()
        page.locator(".tab-bar__more-panel").wait_for(state="visible")
        style = page.evaluate(
            "() => { const s = getComputedStyle(document.querySelector('.tab-bar__more-panel'));"
            " const root = getComputedStyle(document.documentElement);"
            " return {name: s.animationName, seconds: parseFloat(s.animationDuration),"
            " iterations: s.animationIterationCount, easing: s.animationTimingFunction,"
            " fast: parseFloat(root.getPropertyValue('--motion-fast')) / 1000,"
            " curve: root.getPropertyValue('--ease-out').trim()}; }")
        assert style["name"] == "skypane-fade-in" and style["iterations"] == "1", style
        if motion == "reduce":
            assert style["seconds"] < 0.001, style
        else:
            assert style["seconds"] == style["fast"], style
            assert style["easing"].replace(" ", "") == style["curve"].replace(" ", ""), style
            page.wait_for_function(
                "(m) => window.__anim.slice(m).some((e) => e.name === 'skypane-fade-in'"
                " && e.cls.indexOf('tab-bar__more-panel') > -1)", arg=mark, timeout=5000)
        page.wait_for_function(_SETTLED_PAGE, timeout=10000)
        panel = page.evaluate(
            "() => { const p = document.querySelector('.tab-bar__more-panel');"
            " const s = getComputedStyle(p); return [s.opacity, s.transform]; }")
        assert panel == ["1", "none"], panel
        page.keyboard.press("Escape")
        page.wait_for_function(
            "() => !document.querySelector('.tab-bar__more').open", timeout=5000)
        assert page.evaluate(
            "() => document.querySelector('.tab-bar__more-panel').getClientRects().length") == 0
    finally:
        context.close()


def test_the_style_tabs_do_not_slide_under_reduced_motion(new_context, server):
    context = _admin_context(new_context, server, VIEWPORT_DESKTOP, reduced_motion="reduce")
    try:
        page = context.new_page()
        _open(page, server, "/display")
        strip = '[data-tabs="display"]'
        page.locator(strip + " a:not([aria-current])").nth(1).click()
        page.wait_for_function("() => location.pathname !== '/display'", timeout=10000)
        page.wait_for_function(_SETTLED_PAGE, timeout=10000)
        assert not page.evaluate(
            "(s) => document.querySelector(s + ' [data-tabs-thumb]').classList"
            ".contains('is-sliding')", strip)
        assert _thumb_matches_current(page, strip)
    finally:
        context.close()


def test_the_airlines_chips_slide_the_thumb_and_reload_with_the_opening(new_context, server):
    context = _admin_context(new_context, server, VIEWPORT_MIN_SUPPORTED,
                             reduced_motion="no-preference")
    try:
        page = context.new_page()
        _open(page, server, "/airlines")
        strip = '[data-tabs="airlines"]'
        assert _thumb_matches_current(page, strip)
        page.locator(strip + " label.filter-chip:not(:has(input:checked))").first.click()
        page.wait_for_function("() => location.search.indexOf('show') >= 0", timeout=10000)
        page.wait_for_function(_SETTLED_PAGE, timeout=10000)
        _wait_sliding(page, strip)
        assert _entered_since(page, 0)
    finally:
        context.close()


# --- Flights: chips swap the list in place; Load more enters only the new items ----------

LIMIT = history_page.HISTORY_ROW_LIMIT
TOTAL = LIMIT + 20


def _seed_flights(state_dir):
    vp.seed_runway_events(state_dir, [
        {"ts": "2026-09-03T%02d:%02d:00+00:00" % (hour, minute),
         "hex": "4c%04x" % (hour * 60 + minute), "callsign": "AFR%d" % (100 + hour * 60 + minute),
         "airline": "Air France", "origin": "ORY", "destination": "NCE",
         "confirmed_state": "departing" if minute % 10 == 0 else "arriving"}
        for hour in range(12) for minute in range(0, 60, 5)][:TOTAL])


@pytest.fixture(scope="module")
def flights(module_app_server_factory):
    return module_app_server_factory(seed=_seed_flights, fake_providers=True)


def _flights_page(new_context, server, viewport):
    context = new_context(viewport=viewport, reduced_motion="no-preference")
    context.add_init_script(_RECORD)
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/flights")
    page.locator("li.history-card, tr[data-flight-row]").first.wait_for(state="attached")
    page.wait_for_function(_SETTLED_PAGE, timeout=15000)
    return context, page


@pytest.mark.parametrize("viewport", VIEWPORTS)
def test_the_flights_chips_slide_the_thumb_and_the_swapped_list_enters(
        new_context, flights, viewport):
    """choosing Departures swaps the list in place (no navigation): the thumb slides to the new
    chip and the list enters again, as the first three days or the table, never row by row"""
    context, page = _flights_page(new_context, flights, viewport)
    try:
        strip = '[data-tabs="flights"]'
        assert _thumb_matches_current(page, strip)
        page.evaluate("() => { window.__same = 'document'; }")
        mark = page.evaluate("() => window.__anim.length")
        page.locator(strip + " label.filter-chip").nth(1).click()
        page.wait_for_function(
            "(m) => window.__anim.slice(m).some((e) => e.name === 'skypane-reveal-fade')",
            arg=mark, timeout=10000)
        page.wait_for_function(_SETTLED_PAGE, timeout=10000)
        assert page.evaluate("() => window.__same") == "document"
        _wait_sliding(page, strip)
        entered = _entered_since(page, mark)
        assert entered and not [e for e in entered if e["row"]], entered
        assert len(entered) <= 3
    finally:
        context.close()


_SAMPLE_FIRST_ROW = """(ms) => new Promise((resolve) => {
  const tops = [];
  const start = performance.now();
  const step = () => {
    const row = document.querySelector('.data-table-wrap tbody tr');
    if (row) { tops.push(row.getBoundingClientRect().top); }
    if (performance.now() - start < ms) { requestAnimationFrame(step); } else { resolve(tops); }
  };
  requestAnimationFrame(step);
})"""


def test_a_filter_change_on_the_desktop_table_fades_without_moving_it(new_context, flights):
    """choosing another chip swaps the desktop table in place and the new table only fades:
    its first row stays at one height from the swap until well after the fade, and no rise
    plays on the swap or once the fade is over"""
    context, page = _flights_page(new_context, flights, VIEWPORT_DESKTOP)
    try:
        page.wait_for_function(_OPENING_OVER, timeout=10000)
        mark = page.evaluate("() => window.__anim.length")
        page.locator('[data-tabs="flights"] label.filter-chip').nth(1).click()
        page.wait_for_function(
            "(m) => window.__anim.slice(m).some((e) => e.name === 'skypane-reveal-fade')",
            arg=mark, timeout=10000)
        # The fade is under half a second: 1.5 s covers it and what used to follow it.
        tops = page.evaluate(_SAMPLE_FIRST_ROW, 1500)
        assert len(tops) > 20, tops
        assert max(tops) - min(tops) <= 0.5, (min(tops), max(tops))
        page.wait_for_function(_SETTLED_PAGE, timeout=10000)
        since = page.evaluate("(m) => window.__anim.slice(m).map((e) => e.name)", mark)
        assert "skypane-reveal" not in since, since
        assert since.count("skypane-reveal-fade") == 1, since
    finally:
        context.close()


@pytest.mark.parametrize("viewport", VIEWPORTS)
def test_load_more_enters_only_the_first_new_items(new_context, flights, viewport):
    """Load more appends in place on the phone and the desktop alike and the first new items
    enter (at most three), the rest of the batch simply appears"""
    context, page = _flights_page(new_context, flights, viewport)
    try:
        mark = page.evaluate("() => window.__anim.length")
        link = page.locator("a.history-more__link:visible")
        link.scroll_into_view_if_needed()
        link.click()
        page.wait_for_function(
            "(m) => window.__anim.slice(m).some((e) => e.name === 'skypane-reveal-fade')",
            arg=mark, timeout=10000)
        page.wait_for_function(_SETTLED_PAGE, timeout=10000)
        entered = _entered_since(page, mark)
        assert 1 <= len(entered) <= 3, entered
        assert not page.evaluate("() => document.querySelector('.reveal-appended')")
    finally:
        context.close()


# --- Location: the mode switch replays the sheet ---------------------------------------------


@pytest.fixture(scope="module")
def place_server(module_app_server_factory):
    return module_app_server_factory(seed=place_seed, fake_providers=True)


@pytest.mark.parametrize("viewport", VIEWPORTS)
def test_the_location_mode_switch_replays_the_sheet(new_context, place_server, viewport):
    """My position / Airport swaps the sheet's content in place and the sheet takes the entrance
    again; the loader and the map are untouched"""
    context = new_context(viewport=viewport, reduced_motion="no-preference")
    Hosts(context)
    context.add_cookies([
        {"name": auth.UI_LANG_COOKIE_NAME, "value": "en", "url": place_server.base_url()}])
    context.add_init_script(_RECORD)
    try:
        page = context.new_page()
        _login(page, place_server.base_url())
        page.goto(place_server.base_url() + "/detection")
        page.wait_for_function(
            "() => document.documentElement.classList.contains('map-ready')", timeout=15000)
        page.wait_for_function(SETTLED, timeout=10000)
        page.wait_for_function(_SETTLED_PAGE, timeout=10000)
        mark = page.evaluate("() => window.__anim.length")
        target = "area" if page.is_checked("#place-mode-runway") else "runway"
        page.click("label.place-mode:has(#place-mode-%s)" % target)
        page.wait_for_function(
            "(m) => window.__anim.slice(m).some((e) => e.name === 'skypane-reveal-fade'"
            " && e.cls.indexOf('place-sheet') >= 0)", arg=mark, timeout=10000)
        page.wait_for_function(_SETTLED_PAGE, timeout=10000)
        assert not page.evaluate("() => document.querySelector('.reveal-replay')")
    finally:
        context.close()


# --- The opening never holds back the first screenful -----------------------------------------

_PAINT_RECORDER = """
window.__paint = {fcp: null, lcp: null, element: ''};
new PerformanceObserver((list) => {
  for (const e of list.getEntries()) {
    if (e.name === 'first-contentful-paint') { window.__paint.fcp = e.startTime; }
  }
}).observe({type: 'paint', buffered: true});
new PerformanceObserver((list) => {
  for (const e of list.getEntries()) {
    window.__paint.lcp = e.startTime;
    window.__paint.element = e.element ? e.element.tagName + '.' + e.element.className : '';
  }
}).observe({type: 'largest-contentful-paint', buffered: true});
"""
# The opening fade lasts 400 ms and more with its stagger. A largest paint this close to the
# first one means the first screenful was readable at once, not when the fade ended.
LARGEST_PAINT_AFTER_FIRST_MS = 150


@pytest.mark.parametrize("path", ["/", "/account", "/users", "/audit"])
def test_the_largest_text_is_painted_with_the_first_paint(new_context, server, path):
    """on a phone the page opens from a readable state: the largest text of the first screenful
    is painted with the first paint, not at the end of the opening fade, and the opening still
    plays (the header fades in)"""
    context = _admin_context(new_context, server, VIEWPORT_MIN_SUPPORTED,
                             reduced_motion="no-preference")
    context.add_init_script(_PAINT_RECORDER)
    try:
        page = context.new_page()
        _open(page, server, path)
        page.wait_for_function(_OPENING_OVER, timeout=10000)
        page.wait_for_function(
            "() => window.__paint.fcp !== null && window.__paint.lcp !== null", timeout=10000)
        paint = page.evaluate("() => window.__paint")
        assert paint["lcp"] - paint["fcp"] <= LARGEST_PAINT_AFTER_FIRST_MS, (path, paint)
        assert [e for e in page.evaluate("() => window.__anim")
                if e["name"] == "skypane-reveal-fade" and "page-header" in e["cls"]], path
    finally:
        context.close()


# --- Location under reduced motion: the map arriving shifts nothing ---------------------------

_SHIFT_RECORDER = """
window.__shift = 0;
window.__shifts = [];
new PerformanceObserver((list) => {
  for (const e of list.getEntries()) {
    if (!e.hadRecentInput) {
      window.__shift += e.value;
      window.__shifts.push([Math.round(e.startTime), e.value, e.sources.map(
        (x) => x.node && x.node.tagName + '.' + String(x.node.className || '')).join(',')]);
    }
  }
}).observe({type: 'layout-shift', buffered: true});
"""
# The largest cumulative layout shift a Location load may show with reduced motion: what the
# same load shows with motion allowed, with a little room.
REDUCED_MOTION_SHIFT_LIMIT = 0.03
_LAYOUT_TRANSITIONS = """() => document.getAnimations()
  .map((a) => a.transitionProperty || '')
  .filter((p) => /^(width|height|min-|max-|padding|margin|flex|top|left|right|bottom|inset|gap|grid)/
    .test(p))"""


@pytest.mark.parametrize("viewport", [
    pytest.param({"width": 768, "height": 1024}, id="768"),
    pytest.param({"width": 1280, "height": 900}, id="1280")])
def test_location_under_reduced_motion_shifts_no_layout(new_context, place_server, viewport):
    """with prefers-reduced-motion the Location page settles into its map layout in one step:
    the cumulative layout shift of the load stays at what a load with motion shows, and no
    transition ever runs on a property that lays the page out"""
    context = new_context(viewport=viewport, reduced_motion="reduce")
    Hosts(context)
    context.add_cookies([
        {"name": auth.UI_LANG_COOKIE_NAME, "value": "en", "url": place_server.base_url()}])
    try:
        page = context.new_page()
        _login(page, place_server.base_url())
        context.add_init_script(_SHIFT_RECORDER)
        context.add_init_script(
            "window.__layout = [];"
            "document.addEventListener('transitionrun', (e) => {"
            " if (/^(width|height|min-|max-|padding|margin|flex|top|left|right|bottom|inset|gap"
            "|grid)/.test(e.propertyName)) { window.__layout.push(e.propertyName); } }, true);")
        page.goto(place_server.base_url() + "/detection")
        page.wait_for_function(
            "() => document.documentElement.classList.contains('map-ready')", timeout=15000)
        page.wait_for_function(SETTLED, timeout=10000)
        page.wait_for_function(_SETTLED_PAGE, timeout=10000)
        # Two more frames, so a shift caused by the last style change is reported.
        page.evaluate("() => new Promise((done) => requestAnimationFrame("
                      "() => requestAnimationFrame(() => setTimeout(done, 200))))")
        shift = page.evaluate("() => window.__shift")
        assert shift <= REDUCED_MOTION_SHIFT_LIMIT, (shift, page.evaluate("() => window.__shifts"))
        assert page.evaluate("() => window.__layout") == []
        assert page.evaluate(_LAYOUT_TRANSITIONS) == []
    finally:
        context.close()


@pytest.mark.parametrize("motion", ["reduce", "no-preference"])
def test_location_opens_on_a_wide_screen_without_moving_anything(new_context, place_server, motion):
    """the loading state already has the page's map geometry, so when the map takes over nothing
    that was on screen moves: no layout shift at all, with or without reduced motion"""
    context = new_context(viewport={"width": 1280, "height": 900}, reduced_motion=motion)
    Hosts(context)
    context.add_cookies([
        {"name": auth.UI_LANG_COOKIE_NAME, "value": "en", "url": place_server.base_url()}])
    try:
        page = context.new_page()
        _login(page, place_server.base_url())
        context.add_init_script(_SHIFT_RECORDER)
        page.goto(place_server.base_url() + "/detection")
        page.wait_for_function(
            "() => document.documentElement.classList.contains('map-ready')", timeout=15000)
        page.wait_for_function(SETTLED, timeout=10000)
        page.wait_for_function(_SETTLED_PAGE, timeout=10000)
        page.evaluate("() => new Promise((done) => requestAnimationFrame("
                      "() => requestAnimationFrame(() => setTimeout(done, 200))))")
        assert page.evaluate("() => window.__shifts") == []
    finally:
        context.close()


def test_map_tiles_do_not_fade_in_under_reduced_motion(new_context, place_server):
    """with prefers-reduced-motion a map tile shows at once when it arrives: no opacity
    transition ever runs on a tile"""
    context = new_context(viewport={"width": 1280, "height": 900}, reduced_motion="reduce")
    Hosts(context)
    context.add_cookies([
        {"name": auth.UI_LANG_COOKIE_NAME, "value": "en", "url": place_server.base_url()}])
    try:
        page = context.new_page()
        _login(page, place_server.base_url())
        context.add_init_script(
            "window.__tileFades = 0;"
            "document.addEventListener('transitionrun', (e) => {"
            " if (e.target.classList && e.target.classList.contains('leaflet-tile')) {"
            " window.__tileFades += 1; } }, true);")
        page.goto(place_server.base_url() + "/detection")
        page.wait_for_function(
            "() => document.documentElement.classList.contains('map-ready')", timeout=15000)
        page.wait_for_function(
            "() => document.querySelectorAll('#place-map .leaflet-tile-loaded').length >= 4",
            timeout=15000)
        page.wait_for_function(_SETTLED_PAGE, timeout=10000)
        assert page.evaluate("() => window.__tileFades") == 0
        shown = page.evaluate(
            "() => Array.from(document.querySelectorAll('#place-map .leaflet-tile-loaded'))"
            ".map((t) => getComputedStyle(t).opacity)")
        assert shown and set(shown) == {"1"}, shown
    finally:
        context.close()


# --- The bottom tab bar's pill ---------------------------------------------------------------


@pytest.mark.parametrize("path", ["/credits", "/components", "/", "/account"])
def test_the_tab_bar_pill_is_on_every_page(new_context, server, path):
    """the sliding pill sits under an active cell on every page but the error pages: a page that
    belongs to no bar cell is reached through More, which carries the pill there"""
    context = _admin_context(new_context, server, VIEWPORT_MIN_SUPPORTED,
                             reduced_motion="no-preference")
    try:
        page = context.new_page()
        _open(page, server, path)
        page.wait_for_function(
            "() => document.querySelector('.tab-bar').classList.contains('tab-bar--slider')",
            timeout=10000)
        inside = page.evaluate(
            "() => { const r = (e) => e.getBoundingClientRect();"
            " const s = r(document.querySelector('.tab-bar__slider'));"
            " const l = r(document.querySelector("
            "'.tab-bar__link--active'));"
            " return s.width > 0 && s.left >= l.left - 1 && s.right <= l.right + 1"
            " && s.top >= l.top - 1 && s.bottom <= l.bottom + 1; }")
        assert inside, path
    finally:
        context.close()


@pytest.mark.parametrize("motion", ["reduce", "no-preference"])
@pytest.mark.parametrize("path", ["/display", "/display/arrivals"])
def test_the_style_page_opens_on_a_wide_screen_without_the_picture_moving(
        new_context, server, path, motion):
    """the picture column and the picker are placed once, before the entrance: the layout shift of
    a Style load stays under 0.01, with or without reduced motion"""
    context = _admin_context(
        new_context, server, {"width": 1280, "height": 900}, reduced_motion=motion)
    context.add_init_script(_SHIFT_RECORDER)
    try:
        page = context.new_page()
        page.goto(server.base_url() + path)
        page.wait_for_function(_SETTLED_PAGE, timeout=10000)
        page.evaluate("() => new Promise((done) => requestAnimationFrame("
                      "() => requestAnimationFrame(() => setTimeout(done, 400))))")
        assert page.evaluate("() => window.__shift") <= 0.01, page.evaluate("() => window.__shifts")
    finally:
        context.close()


def test_the_administrators_not_found_page_keeps_the_console_navigation_on_a_desktop(
        new_context, server):
    """with no frame in scope the Console is the administrator's only space: the sidebar lists
    its destinations and the space switch marks the Console, not 'My frame'"""
    context = _admin_context(new_context, server, {"width": 1280, "height": 900},
                             reduced_motion="no-preference")
    try:
        page = context.new_page()
        _open(page, server, "/not-a-page")
        page.wait_for_function(_SETTLED_PAGE, timeout=10000)
        links = page.locator(".sidebar-nav a").count()
        assert links >= 4, links
        assert page.locator(".sidebar-nav .sidebar-link--active").count() == 0
        current = page.locator(".space-switch [aria-current=page]")
        assert current.count() == 1 and "Console" in current.inner_text()
    finally:
        context.close()


def test_the_not_found_page_selects_no_cell_and_keeps_a_whole_bar(new_context, server):
    """an error page is in no tab: no cell wears the pill (More included) and the bar still
    offers the destinations instead of a lone More cell"""
    context = _admin_context(new_context, server, VIEWPORT_MIN_SUPPORTED,
                             reduced_motion="no-preference")
    try:
        page = context.new_page()
        _open(page, server, "/not-a-page")
        page.wait_for_function(_SETTLED_PAGE, timeout=10000)
        assert page.locator(".tab-bar__link--active").count() == 0
        assert page.locator(".tab-bar > a").count() >= 3
        assert page.locator(".tab-bar__more--alone").count() == 0
    finally:
        context.close()
