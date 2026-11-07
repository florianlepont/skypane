"""Real-browser checks of Home's details: the title is a personal greeting that follows the
local hour (the frame name is a second line only for several frames, the page keeps its plain
accessible name), no plane animation remains, swapping the wording never moves the title past a
single line's box at 360px, the cards come in one after the other, and the phone tab bar keeps
its labels legible and uncramped in both themes."""
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
  return {title: box('h1.page-title'), frame: box('.home-greeting__frame')};
}"""


@pytest.fixture(scope="module")
def fleet_app(module_app_server_factory):
    """Two frames of one owner; the live frame has seeded flights, the others none."""
    holder = start_fleet_app(
        module_app_server_factory,
        seed_extra=lambda fleet: vp.seed_flight_card_variety(fleet.live.state_dir, False))
    holder.cookie = session_cookie_for_state_dir(holder.server.state_dir, OWNER_EMAIL)
    # An address with a separator, so the greeting can use a first name.
    holder.named_cookie = session_cookie_for_state_dir(
        holder.server.state_dir, "florian.lepont@example.com")
    return holder


@pytest.fixture(scope="module")
def admin_server(module_app_server_factory):
    return module_app_server_factory(seed=seed_state_dir, fake_providers=True)


def _fleet_page(new_context, app, path, lang="en", hour=None, named=True, **context_args):
    context = new_context(**context_args)
    base = app.server.base_url()
    name, value = (app.named_cookie if named else app.cookie).split("=", 1)
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
@pytest.mark.parametrize("hour, band", HOURS[::3], ids=["%02dh" % hour for hour, _ in HOURS[::3]])
def test_the_title_greets_by_the_local_hour(new_context, fleet_app, hour, band, lang):
    page = _fleet_page(new_context, fleet_app, _live(fleet_app), lang, hour)
    # The owner's address has a separator, so the first name is shown.
    want = "%s%s" % (GREETINGS[lang][band], ", Florian" if lang == "en" else " Florian")
    page.wait_for_function(
        "want => document.querySelector('h1.page-title').innerText === want", arg=want)
    # The visible title is the greeting; the accessible name stays the plain page name.
    assert page.locator("h1.page-title").get_attribute("aria-label") == (
        "Home" if lang == "en" else "Accueil")
    assert page.get_by_role("heading", name="Home" if lang == "en" else "Accueil").count() == 1
    assert page.title().startswith("Home" if lang == "en" else "Accueil")
    assert "@" not in page.locator("h1.page-title").inner_text()


def test_without_script_the_greeting_is_the_neutral_default(new_context, fleet_app):
    page = _fleet_page(new_context, fleet_app, _live(fleet_app), java_script_enabled=False)
    assert page.locator("h1.page-title").inner_text() == "Hello, Florian"
    assert page.locator("h1.page-title").get_attribute("aria-label") == "Home"


def test_an_address_without_a_separator_gets_the_bare_greeting(new_context, fleet_app):
    """"owner@example.com" could be a handle, not a name: never shown, in any wording"""
    plain = _fleet_page(new_context, fleet_app, _live(fleet_app), named=False,
                        java_script_enabled=False)
    assert plain.locator("h1.page-title").inner_text() == "Hello"
    page = _fleet_page(new_context, fleet_app, _live(fleet_app), hour=9, named=False)
    page.wait_for_function(
        "() => document.querySelector('h1.page-title').innerText === 'Good morning'")


def test_the_frame_name_is_a_second_line_for_several_frames(new_context, fleet_app):
    page = _fleet_page(new_context, fleet_app, _live(fleet_app), hour=9, named=False)
    name = page.locator(".frame-menu__name").inner_text()
    assert page.locator(".home-greeting__frame").inner_text() == name
    boxes = page.evaluate(_BOXES)
    assert boxes["frame"][1] >= boxes["title"][1] + boxes["title"][3] - 1


def test_a_single_frame_shows_no_frame_line(new_context, admin_server):
    context = new_context(viewport=VIEWPORT_DESKTOP)
    page = context.new_page()
    _login(page, admin_server.base_url())
    page.goto(admin_server.base_url() + "/")
    page.wait_for_function(_SETTLED)
    assert page.locator("h1.page-title").count() == 1
    assert page.locator(".home-greeting__frame").count() == 0


def test_the_plane_on_a_trail_is_gone(new_context, fleet_app):
    page = _fleet_page(new_context, fleet_app, _live(fleet_app))
    assert page.locator(".home-trail, .home-trail__plane").count() == 0
    assert page.evaluate(
        "() => document.getAnimations().filter(a => a.animationName === 'skypane-plane-fly')"
        ".length") == 0


@pytest.mark.parametrize("viewport", [VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED],
                         ids=["1280", "360"])
def test_the_greeting_swap_keeps_the_title_in_place_and_within_two_lines(
        new_context, fleet_app, viewport):
    """without script (neutral wording) and with the longest wording of the day ("Good afternoon,
    Florian"), the title keeps its top, is one line tall on a desktop and at most two at 360px
    (the swap runs from the shell script before the first paint); no sideways scroll"""
    plain = _fleet_page(new_context, fleet_app, _live(fleet_app), hour=9,
                        viewport=viewport, java_script_enabled=False)
    expected = plain.evaluate(_BOXES)["title"]
    page = _fleet_page(new_context, fleet_app, _live(fleet_app), hour=14, viewport=viewport)
    page.wait_for_function(
        "() => document.querySelector('h1.page-title').innerText === 'Good afternoon, Florian'")
    seen = page.evaluate(_BOXES)["title"]
    assert seen[1] == expected[1] and seen[0] == expected[0], (seen, expected)
    line = page.evaluate("() => parseFloat(getComputedStyle("
                         "document.querySelector('h1.page-title')).lineHeight)")
    assert seen[3] <= line * (1 if viewport is VIEWPORT_DESKTOP else 2) + 1, (seen, line)
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
        """() => ['.home-state', '.home-state__switches',
                  'section[aria-labelledby="home-flights"]'].map(
            sel => getComputedStyle(document.querySelector(sel)).animationDelay)""")
    assert delays == ["0s", "0.06s", "0.12s"], delays
    page.wait_for_function(_SETTLED)
    settled = page.evaluate(
        """() => ['.home-state', '.home-state__switches'].map(sel => {
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
              const bar = getComputedStyle(document.querySelector('.tab-bar'), '::before');
              const inactive = [...document.querySelectorAll(
                  '.tab-bar__link:not(.tab-bar__link--active) .tab-bar__label')];
              const cells = [...document.querySelectorAll('.tab-bar > :not(.tab-bar__slider)')]
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
        # The floating bar has its own fill per theme: legible over a white and a black
        # backdrop (a picture scrolling beneath it) in both.
        for backdrop in (255, 0):
            bar = "#%02X%02X%02X" % tuple(round(alpha * c + (1 - alpha) * backdrop)
                                          for c in parts[:3])
            for ink in read["inks"]:
                rgb = [int(float(p)) for p in ink[ink.index("(") + 1:-1].split(",")[:3]]
                hex_ink = "#%02X%02X%02X" % tuple(rgb)
                assert contrast_ratio(hex_ink, bar) >= WCAG_AA_NORMAL_TEXT, (
                    where, ink, bar, backdrop)
