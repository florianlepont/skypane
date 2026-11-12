"""The page opening and the tab strips, read in a real browser.

Every page opens the same way: the shell marks <main> with data-page-open and the page header
plus the first screenful of blocks enter with Home's card entrance (a fade and a short rise),
compositor properties only. Lists, tables and rows are never animated, and a tall page animates
at most a header and five blocks. Every segmented strip marked data-tabs slides one thumb under
its current segment, and the content a strip switches replays the same entrance. Reduced motion
turns all of it into an instant change. The bottom tab bar's sliding pill is on every page,
including the ones that belong to no bar cell.
"""
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


@pytest.mark.parametrize("viewport", VIEWPORTS)
def test_the_audit_chips_slide_the_thumb_and_replay_the_opening(new_context, server, viewport):
    """choosing another audit category loads that page: the thumb starts under the chip that was
    left and slides to the new one, and the page opening plays again"""
    context = _admin_context(new_context, server, viewport, reduced_motion="no-preference")
    try:
        page = context.new_page()
        _open(page, server, "/audit")
        strip = '[data-tabs="audit"]'
        assert _thumb_matches_current(page, strip)
        page.locator(strip + " a.filter-chip:not(.filter-chip--current)").nth(1).click()
        page.wait_for_function("() => location.search.indexOf('category') >= 0", timeout=10000)
        page.wait_for_function(_SETTLED_PAGE, timeout=10000)
        _wait_sliding(page, strip)
        assert _entered_since(page, 0), "the new audit page did not open with the entrance"
    finally:
        context.close()


def test_the_fleet_tabs_slide_the_thumb_and_replay_their_blocks(new_context, server):
    """on a phone the State, Settings and Access tabs slide the thumb like the Style tabs and the
    blocks of the chosen tab enter"""
    context = _admin_context(new_context, server, VIEWPORT_MIN_SUPPORTED,
                             reduced_motion="no-preference")
    try:
        page = context.new_page()
        _open(page, server, "/fleet")
        strip = '[data-tabs="fleet"]'
        assert _thumb_matches_current(page, strip)
        page.locator(strip + " a:not([aria-current])").first.click()
        page.wait_for_function("() => location.search.indexOf('tab=') >= 0", timeout=10000)
        page.wait_for_function(_SETTLED_PAGE, timeout=10000)
        _wait_sliding(page, strip)
        assert [e for e in _entered_since(page, 0) if "fleet-block" in e["cls"]]
    finally:
        context.close()


def test_the_style_tabs_slide_the_thumb(new_context, server):
    context = _admin_context(new_context, server, VIEWPORT_DESKTOP,
                             reduced_motion="no-preference")
    try:
        page = context.new_page()
        _open(page, server, "/display")
        strip = '[data-tabs="display"]'
        assert _thumb_matches_current(page, strip)
        page.locator(strip + " a:not([aria-current])").nth(1).click()
        page.wait_for_function("() => location.pathname !== '/display'", timeout=10000)
        page.wait_for_function(_SETTLED_PAGE, timeout=10000)
        _wait_sliding(page, strip)
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


# --- The bottom tab bar's pill ---------------------------------------------------------------


@pytest.mark.parametrize("path", ["/credits", "/components", "/not-a-page", "/", "/account"])
def test_the_tab_bar_pill_is_on_every_page(new_context, server, path):
    """the sliding pill sits under an active cell on every page: a page that belongs to no bar
    cell is reached through More, which carries the pill there"""
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
            "'.tab-bar__link--active:not(.tab-bar__link--switch)'));"
            " return s.width > 0 && s.left >= l.left - 1 && s.right <= l.right + 1"
            " && s.top >= l.top - 1 && s.bottom <= l.bottom + 1; }")
        assert inside, path
    finally:
        context.close()
