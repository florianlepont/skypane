"""Real-browser checks of Home's style-A details: the greeting follows the local hour (with
the frame name as a second line only for several frames), the plane on its trail is shown only
when the frame has a flight and flies in once, nothing moves the title (greeting swap, plane
animation), reduced motion shows the plane at rest, the cards come in one after the other, and
the phone tab bar keeps its labels legible and uncramped in both themes."""
import pytest
from companion_app_server import session_cookie_for_state_dir
from skypane_contrast_check import WCAG_AA_NORMAL_TEXT, contrast_ratio
from skypane_two_device_fleet import OWNER_EMAIL

from companion import auth
import companion.test_view_pages_helpers as vp
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE, _assert_no_page_overflow,
    _in_both_themes, _login, seed_state_dir)
from companion.test_device_helpers import start_fleet_app

pytestmark = pytest.mark.browser

GREETINGS = {
    "en": {"morning": "Good morning", "afternoon": "Good afternoon", "evening": "Good evening",
           "night": "Good night"},
    "fr": {"morning": "Bonjour", "afternoon": "Bon après-midi", "evening": "Bonsoir",
           "night": "Bonne nuit"},
}
# (local hour, band) around every edge.
HOURS = ((0, "night"), (4, "night"), (5, "morning"), (11, "morning"), (12, "afternoon"),
         (16, "afternoon"), (17, "evening"), (20, "evening"), (21, "night"), (23, "night"))

_SETTLED = """() => {
  if (document.readyState !== 'complete') return false;
  return document.getAnimations().every((a) => a.playState !== 'running'
      || a.effect.getComputedTiming().iterations === Infinity);
}"""

_BOXES = """() => {
  const box = (sel) => { const el = document.querySelector(sel);
    if (!el) return null; const r = el.getBoundingClientRect();
    return [r.x, r.y, r.width, r.height].map(n => Math.round(n * 100) / 100); };
  return {title: box('h1.page-title'), trail: box('.home-trail'), greeting: box('.home-greeting')};
}"""


@pytest.fixture(scope="module")
def fleet_app(module_app_server_factory):
    """Two frames of one owner; the live frame has seeded flights, the others none."""
    holder = start_fleet_app(
        module_app_server_factory,
        seed_extra=lambda fleet: vp.seed_flight_card_variety(fleet.live.state_dir, False))
    holder.cookie = session_cookie_for_state_dir(holder.server.state_dir, OWNER_EMAIL)
    return holder


@pytest.fixture(scope="module")
def admin_server(module_app_server_factory):
    return module_app_server_factory(seed=seed_state_dir, fake_providers=True)


def _fleet_page(new_context, app, path, lang="en", hour=None, **context_args):
    context = new_context(**context_args)
    base = app.server.base_url()
    name, value = app.cookie.split("=", 1)
    context.add_cookies([
        {"name": name, "value": value, "url": base, "httpOnly": True, "sameSite": "Strict"},
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base}])
    page = context.new_page()
    if hour is not None:
        page.add_init_script("Date.prototype.getHours = function () { return %d; };" % hour)
    page.goto(base + path)
    page.locator("main").wait_for(state="visible")
    if context_args.get("java_script_enabled", True):
        page.wait_for_function(_SETTLED)
    return page


def _live(app):
    return "/devices/%s/" % app.fleet.live.id


def _quiet(app):
    return "/devices/%s/" % app.fleet.dev_a.id


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("hour, band", HOURS, ids=["%02dh" % hour for hour, _ in HOURS])
def test_greeting_follows_the_local_hour(new_context, fleet_app, hour, band, lang):
    page = _fleet_page(new_context, fleet_app, _live(fleet_app), lang, hour)
    page.wait_for_function(
        "want => document.querySelector('[data-greeting-text]').textContent === want",
        arg=GREETINGS[lang][band])
    assert page.locator("h1.page-title").inner_text() == ("Home" if lang == "en" else "Accueil")
    assert page.locator("[data-greeting]").get_attribute("aria-hidden") == "true"


def test_without_script_the_greeting_is_the_neutral_default(new_context, fleet_app):
    page = _fleet_page(new_context, fleet_app, _live(fleet_app), java_script_enabled=False)
    assert page.locator("[data-greeting-text]").inner_text() == "Hello"
    assert page.locator("h1.page-title").inner_text() == "Home"


def test_the_frame_name_is_a_second_line_for_several_frames(new_context, fleet_app):
    page = _fleet_page(new_context, fleet_app, _live(fleet_app), hour=9)
    name = page.locator(".frame-fold__name").inner_text()
    assert page.locator(".home-greeting__frame").inner_text() == name
    box = page.evaluate(_BOXES)["greeting"]
    line = page.evaluate("() => parseFloat(getComputedStyle("
                         "document.querySelector('.home-greeting')).lineHeight)")
    assert box[3] >= 2 * line - 1


def test_a_single_frame_shows_no_frame_line(new_context, admin_server):
    context = new_context(viewport=VIEWPORT_DESKTOP)
    page = context.new_page()
    _login(page, admin_server.base_url())
    page.goto(admin_server.base_url() + "/")
    page.wait_for_function(_SETTLED)
    assert page.locator(".home-greeting").count() == 1
    assert page.locator(".home-greeting__frame").count() == 0


def test_the_plane_is_shown_only_with_a_recent_flight(new_context, fleet_app):
    with_flight = _fleet_page(new_context, fleet_app, _live(fleet_app))
    assert with_flight.locator(".home-trail svg .home-trail__plane").count() == 1
    assert with_flight.locator(".home-trail").get_attribute("aria-hidden") == "true"
    without = _fleet_page(new_context, fleet_app, _quiet(fleet_app))
    assert without.locator("h1.page-title").count() == 1
    assert without.locator(".home-trail").count() == 0


def test_the_plane_flies_in_once_and_rests(new_context, fleet_app):
    context = new_context(viewport=VIEWPORT_DESKTOP)
    base = fleet_app.server.base_url()
    name, value = fleet_app.cookie.split("=", 1)
    context.add_cookies([{"name": name, "value": value, "url": base, "httpOnly": True,
                          "sameSite": "Strict"}])
    page = context.new_page()
    page.goto(base + _live(fleet_app))
    plane = page.locator(".home-trail__plane")
    plane.wait_for(state="attached")
    timing = plane.evaluate(
        "el => el.getAnimations().map(a => [a.animationName, a.effect.getComputedTiming().duration,"
        " a.effect.getComputedTiming().iterations])")
    # The animation may already be over on a fast machine; if it is still running it is the
    # one finite 1.2 s flight.
    assert timing in ([], [["skypane-plane-fly", 1200, 1]]), timing
    page.wait_for_function(_SETTLED)
    rest = plane.evaluate("el => ({t: getComputedStyle(el).transform, o: getComputedStyle(el).opacity,"
                          " n: el.getAnimations().length})")
    assert rest == {"t": "none", "o": "1", "n": 0}, rest


def test_reduced_motion_shows_the_plane_at_rest(new_context, fleet_app):
    page = _fleet_page(new_context, fleet_app, _live(fleet_app), reduced_motion="reduce")
    plane = page.locator(".home-trail__plane")
    page.wait_for_function(
        "() => [...document.querySelectorAll('.home-trail__plane')].every("
        "el => el.getAnimations().every(a => a.playState !== 'running'))")
    rest = plane.evaluate("el => ({t: getComputedStyle(el).transform, o: getComputedStyle(el).opacity,"
                          " d: getComputedStyle(el).animationDuration})")
    assert rest["t"] == "none" and rest["o"] == "1", rest
    assert float(rest["d"].rstrip("s")) <= 0.0001, rest
    assert plane.bounding_box()["width"] > 0


@pytest.mark.parametrize("viewport", [VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED],
                         ids=["1280", "360"])
def test_nothing_shifts_the_title_or_the_trail(new_context, fleet_app, viewport):
    """the title and trail boxes are the same without script (no greeting swap, no
    animation), mid-flight and settled, and the page never scrolls sideways"""
    plain = _fleet_page(new_context, fleet_app, _live(fleet_app), hour=9,
                        viewport=viewport, java_script_enabled=False)
    expected = plain.evaluate(_BOXES)
    context = new_context(viewport=viewport)
    base = fleet_app.server.base_url()
    name, value = fleet_app.cookie.split("=", 1)
    context.add_cookies([{"name": name, "value": value, "url": base, "httpOnly": True,
                          "sameSite": "Strict"}])
    page = context.new_page()
    page.add_init_script("Date.prototype.getHours = function () { return 9; };")
    page.goto(base + _live(fleet_app), wait_until="commit")
    page.locator(".home-trail").wait_for(state="attached")
    mid = page.evaluate(_BOXES)
    page.wait_for_function(_SETTLED)
    settled = page.evaluate(_BOXES)
    for seen in (mid, settled):
        assert seen["title"] == expected["title"], (seen, expected)
        assert seen["trail"] == expected["trail"], (seen, expected)
        assert seen["greeting"] == expected["greeting"], (seen, expected)
    failure = _assert_no_page_overflow(page, "Home", expected_width=viewport["width"])
    if failure:
        raise AssertionError(failure)


def test_the_home_cards_come_in_one_after_the_other(new_context, fleet_app):
    context = new_context(viewport=VIEWPORT_DESKTOP)
    base = fleet_app.server.base_url()
    name, value = fleet_app.cookie.split("=", 1)
    context.add_cookies([{"name": name, "value": value, "url": base, "httpOnly": True,
                          "sameSite": "Strict"}])
    page = context.new_page()
    page.goto(base + _live(fleet_app))
    page.locator(".home-state").wait_for(state="attached")
    delays = page.evaluate(
        """() => ['.home-state', '.home-current-frame',
                  'section[aria-labelledby="home-flights"]'].map(
            sel => getComputedStyle(document.querySelector(sel)).animationDelay)""")
    assert delays == ["0s", "0.06s", "0.12s"], delays
    page.wait_for_function(_SETTLED)
    settled = page.evaluate(
        """() => ['.home-state', '.home-current-frame'].map(sel => {
            const s = getComputedStyle(document.querySelector(sel));
            return [s.opacity, s.transform]; })""")
    assert settled == [["1", "none"], ["1", "none"]], settled


@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE], ids=["360", "390"])
def test_tab_bar_labels_are_legible_and_uncramped(new_context, admin_server, viewport):
    context = new_context(viewport=viewport)
    page = context.new_page()
    _login(page, admin_server.base_url())
    page.goto(admin_server.base_url() + "/")
    page.wait_for_function(_SETTLED)
    for theme in _in_both_themes(page):
        where = "%s %dpx" % (theme["theme"], viewport["width"])
        # The theme change starts colour transitions; read only the settled colours.
        page.wait_for_function(_SETTLED)
        read = page.evaluate(
            """() => {
              const bar = getComputedStyle(document.querySelector('.tab-bar'));
              const inactive = [...document.querySelectorAll(
                  '.tab-bar__link:not(.tab-bar__link--active) .tab-bar__label')];
              const cells = [...document.querySelectorAll('.tab-bar > *')]
                  .map(el => el.getBoundingClientRect());
              return {bar: bar.backgroundColor,
                      inks: inactive.map(el => getComputedStyle(el).color),
                      clipped: [...document.querySelectorAll('.tab-bar__label')]
                          .filter(el => el.scrollWidth > el.clientWidth + 0.5).length,
                      narrow: cells.filter(r => r.width < 44 || r.height < 44).length,
                      first: cells[0].width};
            }""")
        assert read["inks"], where
        assert read["clipped"] == 0 and read["narrow"] == 0, (where, read)
        assert read["first"] >= 68 - 0.5, (where, read)
        parts = [float(p) for p in read["bar"][read["bar"].index("(") + 1:-1].split(",")]
        alpha = parts[3] if len(parts) == 4 else 1.0
        for backdrop in (255, 0):
            bar = "#%02X%02X%02X" % tuple(round(alpha * c + (1 - alpha) * backdrop)
                                          for c in parts[:3])
            for ink in read["inks"]:
                rgb = [int(float(p)) for p in ink[ink.index("(") + 1:-1].split(",")[:3]]
                hex_ink = "#%02X%02X%02X" % tuple(rgb)
                assert contrast_ratio(hex_ink, bar) >= WCAG_AA_NORMAL_TEXT, (
                    where, ink, bar, backdrop)
