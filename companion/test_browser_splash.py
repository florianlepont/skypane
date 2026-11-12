"""Real-browser checks of the opening splash and the loading indicators: the splash shows once
per session on a first visit, leaves the page inert while it plays and interactive after, is
skipped on the second visit, without scripts and (as a static logo) under reduced motion, keeps
its logo small and centred from the first frame, never flashes more than the limit by
construction, and ends under the hard cap; the Location map shows its loading note until its
pictures are in, in both languages."""
import pytest

from companion import auth, layout
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP,
    VIEWPORT_PHONE,
    _login,
)
from place_map_support import Hosts, seed as _place_seed, tile_png

pytestmark = pytest.mark.browser

SPLASH_ON = (
    "() => !!document.documentElement && document.documentElement.classList.contains('splash-on')")
SPLASH_OFF = (
    "() => !!document.documentElement && !document.documentElement.classList.contains('splash-on')")
SPLASH_DONE = "() => !!window.skypaneSplash && window.skypaneSplash.state === 'done'"
# The logo's box and the viewport centre, or false while the splash is not shown yet.
LOGO_BOX = (
    "() => { const root = document.documentElement; const logo = document.querySelector("
    "'.splash__logo--ghost'); if (!root || !logo || !root.classList.contains('splash-on')) return false;"
    " const r = logo.getBoundingClientRect();"
    " return {width: r.width, height: r.height, cx: r.left + r.width / 2, cy: r.top + r.height / 2,"
    "  vw: window.innerWidth, vh: window.innerHeight,"
    "  opacity: parseFloat(getComputedStyle(logo).opacity),"
    "  shown: getComputedStyle(document.querySelector('.splash')).display !== 'none'}; }")
SHELL_INERT = (
    "() => !!document.querySelector('.dashboard-shell')"
    " && document.querySelector('.dashboard-shell').hasAttribute('inert')")
# Whether the splash covers the middle of the page (the page below is not reachable by touch).
COVERED = (
    "() => { const hit = document.elementFromPoint(window.innerWidth / 2, window.innerHeight / 2);"
    " return !!hit && !!hit.closest('.splash'); }")
RUNNING_SPLASH_ANIMATIONS = (
    "() => document.getAnimations({subtree: true}).filter((a) => a.effect && a.effect.target"
    " && a.effect.target.closest && a.effect.target.closest('.splash')"
    " && a.playState === 'running').length")


@pytest.fixture
def server(make_app_server):
    from companion.test_browser_ux_helpers import seed_state_dir
    return make_app_server(seed=seed_state_dir, fake_providers=True)


def _home(new_context, server, wait_until="commit", **context_args):
    context = new_context(splash=True, **context_args)
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + layout.HOME_ROUTE, wait_until=wait_until)
    return context, page


def test_the_splash_script_is_preloaded_and_fetched_once(new_context, server):
    """the first visit hints the splash script from the document head, so its request overlaps
    parsing, and the script is still downloaded exactly once"""
    context = new_context(splash=True, viewport=VIEWPORT_PHONE)
    page = context.new_page()
    fetched = []
    page.on("request", lambda r: fetched.append(r.url) if "/static/splash.js" in r.url else None)
    try:
        _login(page, server.base_url())
        fetched.clear()
        page.goto(server.base_url() + layout.HOME_ROUTE)
        page.wait_for_function(SPLASH_DONE, timeout=6000)
        hint = page.locator('head link[rel="preload"][as="script"]')
        assert hint.count() == 1
        assert hint.get_attribute("href") == page.locator(
            'script[src*="splash.js"]').get_attribute("src")
        assert len(fetched) == 1, fetched
    finally:
        context.close()


def test_splash_plays_once_keeps_the_page_inert_then_opens_it(new_context, server):
    """first visit: the splash covers the page, the page is inert, and when it ends the page is
    interactive; the splash was marked as seen for the session"""
    context, page = _home(new_context, server, viewport=VIEWPORT_PHONE)
    try:
        page.wait_for_function(SPLASH_ON, timeout=5000)
        page.wait_for_function(SHELL_INERT, timeout=5000)
        assert page.evaluate(SHELL_INERT) is True
        page.wait_for_function(COVERED, timeout=3000)
        page.wait_for_function(SPLASH_DONE, timeout=6000)
        page.wait_for_function(SPLASH_OFF, timeout=2000)
        assert page.evaluate(SHELL_INERT) is False
        assert page.evaluate("() => document.querySelectorAll('[inert]').length") == 0
        assert page.evaluate("() => getComputedStyle(document.querySelector('.splash')).display") == "none"
        assert page.evaluate("() => sessionStorage.getItem('skypane.splash')") == "1"
        page.locator('.tab-bar a[href$="/flights"]').click()
        page.wait_for_url("**/flights")
    finally:
        context.close()


def test_splash_ends_under_the_hard_cap(new_context, server):
    """the whole splash, opening included, ends within the cap"""
    context, page = _home(new_context, server, viewport=VIEWPORT_PHONE)
    try:
        page.wait_for_function(SPLASH_DONE, timeout=6000)
        finished = page.evaluate("() => window.skypaneSplash.finishedAt")
        cap = page.evaluate("() => window.skypaneSplash.capMs")
        assert cap <= 3000 and 0 < finished <= cap
    finally:
        context.close()


def test_second_visit_in_the_session_skips_the_splash(new_context, server):
    context, page = _home(new_context, server, viewport=VIEWPORT_PHONE)
    try:
        page.wait_for_function(SPLASH_DONE, timeout=6000)
        page.goto(server.base_url() + "/flights")
        page.wait_for_function("() => document.readyState === 'complete'")
        assert page.evaluate(SPLASH_ON) is False
        assert page.evaluate("() => !window.skypaneSplash") is True
        assert page.evaluate("() => document.querySelectorAll('[inert]').length") == 0
    finally:
        context.close()


def test_without_scripts_there_is_no_splash(new_context, server):
    context = new_context(splash=True, viewport=VIEWPORT_PHONE, java_script_enabled=False)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + layout.HOME_ROUTE)
        assert page.locator(".splash").count() == 1
        assert not page.locator(".splash").is_visible()
        assert page.locator(".dashboard-shell").is_visible()
    finally:
        context.close()


@pytest.mark.parametrize("name,viewport,low,high", [
    ("390", VIEWPORT_PHONE, 28, 32),
    ("1280", VIEWPORT_DESKTOP, 34, 38),
])
def test_logo_is_small_centred_and_present_from_the_first_frame(
        new_context, server, name, viewport, low, high):
    context, page = _home(new_context, server, viewport=viewport)
    try:
        # Polled every frame, so the box is read at the first frame the splash is shown.
        box = page.wait_for_function(LOGO_BOX, timeout=5000, polling="raf").json_value()
        assert box["shown"] and box["opacity"] > 0.2
        assert low <= box["height"] <= high and abs(box["width"] - box["height"]) < 1
        assert abs(box["cx"] - box["vw"] / 2) <= 1.5 and abs(box["cy"] - box["vh"] / 2) <= 1.5
        page.wait_for_function(SPLASH_DONE, timeout=6000)
    finally:
        context.close()


@pytest.mark.parametrize("name,viewport", [
    ("390", VIEWPORT_PHONE), ("360", {"width": 360, "height": 740}), ("1280", VIEWPORT_DESKTOP),
])
def test_the_animated_frame_is_a_small_centred_panel(new_context, server, name, viewport):
    """the frame is 60-65 % of the 300 px (or 46 % of the viewport height) it first had, keeps its
    3:4 shape and its centre, and the caption sits just under it"""
    context, page = _home(new_context, server, viewport=viewport)
    try:
        page.wait_for_function(LOGO_BOX, timeout=5000, polling="raf")
        box = page.evaluate(
            "() => { const f = document.querySelector('.splash__frame').getBoundingClientRect();"
            " const c = document.querySelector('.splash__caption').getBoundingClientRect();"
            " return {w: f.width, h: f.height, cx: f.left + f.width / 2, cy: f.top + f.height / 2,"
            "  gap: c.top - f.bottom, vw: window.innerWidth, vh: window.innerHeight}; }")
        first_design = min(0.46 * box["vh"], 300)
        assert 0.60 * first_design <= box["h"] <= 0.65 * first_design, box
        assert abs(box["w"] / box["h"] - 0.75) < 0.01, box
        assert abs(box["cx"] - box["vw"] / 2) <= 1.5 and abs(box["cy"] - box["vh"] / 2) <= 1.5, box
        assert 0 <= box["gap"] <= 48, box
        page.wait_for_function(SPLASH_DONE, timeout=6000)
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_reduced_motion_shows_a_static_logo_with_no_animation(new_context, server, scheme):
    context, page = _home(
        new_context, server, viewport=VIEWPORT_PHONE, reduced_motion="reduce", color_scheme=scheme)
    try:
        page.wait_for_function(SPLASH_ON, timeout=5000)
        page.wait_for_function("() => !!window.skypaneSplash", timeout=5000)
        assert page.evaluate("() => window.skypaneSplash.state") in ("static", "done")
        assert page.evaluate(RUNNING_SPLASH_ANIMATIONS) == 0
        assert page.evaluate("() => window.skypaneSplash.flashLog.length") == 0
        page.wait_for_function(SPLASH_DONE, timeout=4000)
        assert page.evaluate("() => window.skypaneSplash.finishedAt") < 1500
        assert page.evaluate("() => document.querySelectorAll('[inert]').length") == 0
    finally:
        context.close()


def test_flash_rate_is_bounded_by_the_sequence(new_context, server):
    """the sequence declares exactly one luminance flash, no window of one second holds more than
    three, and the flashes the run really started respect the same bound"""
    context, page = _home(new_context, server, viewport=VIEWPORT_PHONE)
    try:
        page.wait_for_function(SPLASH_DONE, timeout=6000)
        sequence = page.evaluate("() => window.skypaneSplash.sequence")
        flashes = [step for step in sequence if step["kind"] == "flash"]
        assert len(flashes) == 1
        starts = sorted(step["at"] for step in flashes)
        for start in starts:
            assert len([s for s in starts if start <= s < start + 1000]) <= 3
        logged = page.evaluate("() => window.skypaneSplash.flashLog")
        assert len(logged) == len(flashes)
        for start in logged:
            assert len([s for s in logged if start <= s < start + 1000]) <= 3
        assert sequence[-1]["at"] + sequence[-1]["duration"] <= 3000
    finally:
        context.close()


# ---- the Location map's loading note ---------------------------------------------------

LOADING_VISIBLE = "() => { const e = document.getElementById('place-loading'); return !!e && !e.hidden; }"
LOADING_HIDDEN = "() => { const e = document.getElementById('place-loading'); return !!e && e.hidden; }"


@pytest.mark.parametrize("lang,words", [
    ("en", "Loading the map"), ("fr", "Chargement de la carte")])
def test_map_shows_its_loading_note_until_the_pictures_arrive(
        new_context, make_app_server, lang, words):
    """the note (a spinner and the words) shows while the map pictures are held back, and is gone
    once they arrive; the map is never an unexplained blank"""
    server = make_app_server(seed=_place_seed, fake_providers=True)
    context = new_context(viewport=VIEWPORT_PHONE)
    held = []
    Hosts(context)
    context.route("https://tile.openstreetmap.org/**", lambda route: held.append(route))
    context.add_cookies([
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/detection", wait_until="domcontentloaded")
        page.wait_for_function("() => document.documentElement.classList.contains('map-ready')",
                               timeout=15000)
        page.wait_for_function(LOADING_VISIBLE, timeout=5000)
        assert words in page.locator("#place-loading").inner_text()
        assert page.locator("#place-loading .place-loading__spinner").is_visible()
        deadline = 50
        while not held and deadline:
            page.wait_for_timeout(100)
            deadline -= 1
        assert held, "the map asked for no pictures"
        for route in list(held):
            route.fulfill(status=200, content_type="image/png", body=tile_png())
        page.wait_for_function(LOADING_HIDDEN, timeout=10000)
    finally:
        context.close()


def test_map_loading_note_ends_when_the_pictures_cannot_load(new_context, make_app_server):
    server = make_app_server(seed=_place_seed, fake_providers=True)
    context = new_context(viewport=VIEWPORT_PHONE)
    Hosts(context, tiles="abort")
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/detection")
        page.wait_for_function(LOADING_HIDDEN, timeout=15000)
    finally:
        context.close()


# The first animation frame a script gets can carry a timestamp older than the clock the script
# read when it started (the frame began before the script ran). This hands the splash such a
# frame, and records the percentage shown after every frame.
_EARLY_FIRST_FRAME = """
(() => {
  const raf = window.requestAnimationFrame.bind(window);
  let first = true;
  window.__percents = [];
  window.requestAnimationFrame = (callback) => raf((stamp) => {
    callback(first ? stamp - 120 : stamp);
    first = false;
    const shown = document.querySelector('.splash__percent');
    if (shown && shown.textContent) window.__percents.push(shown.textContent);
  });
})();
"""


@pytest.mark.parametrize("motion", ["no-preference", "reduce"])
def test_the_percentage_never_goes_below_zero_or_backwards(new_context, server, motion):
    """whatever the first frame's timestamp, the count starts at 0, only goes up and ends at
    100: it never shows a negative value"""
    context = new_context(splash=True, viewport=VIEWPORT_PHONE, reduced_motion=motion)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        context.add_init_script(_EARLY_FIRST_FRAME)
        page.goto(server.base_url() + layout.HOME_ROUTE, wait_until="commit")
        page.wait_for_function(SPLASH_DONE, timeout=6000)
        shown = page.evaluate("() => window.__percents")
        values = [int("".join(ch for ch in text if ch.isdigit() or ch == "-")) for text in shown]
        assert values, "no percentage was shown"
        assert min(values) >= 0 and max(values) == 100, values
        assert values == sorted(values), values
    finally:
        context.close()
