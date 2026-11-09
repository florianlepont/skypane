"""Real-browser checks of Home's hero: the picture sits beside the title column at every
width (also 360px), the frame name is the page's one h1 at 48/28/24px with a 44px round rename
pencil on its line (also for a long name), the state is a pill with its dot and word, an empty
picture still renders, no plane animation remains, the cards come in one after the other, and
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
from server import fleet_db

pytestmark = pytest.mark.browser

LONG_NAME = "Maison de campagne chez Tante Marguerite-Louise"

_SETTLED = """() => {
  if (document.readyState !== 'complete') return false;
  return document.getAnimations().every((a) => a.playState !== 'running'
      || a.effect.getComputedTiming().iterations === Infinity);
}"""

_HERO = """() => {
  const box = (sel) => { const el = document.querySelector(sel);
    if (!el) return null; const r = el.getBoundingClientRect();
    return {left: r.left, right: r.right, top: r.top, bottom: r.bottom,
            width: r.width, height: r.height}; };
  const h1 = document.querySelector('main h1');
  return {picture: box('.hero__picture .preview-frame'), title: box('main h1'),
          pencil: box('.title-action .btn--icon'), pill: box('.home-state__pill'),
          size: parseFloat(getComputedStyle(h1).fontSize),
          h1s: document.querySelectorAll('h1').length,
          dot: !!document.querySelector('.home-state__pill .home-state__dot'),
          word: document.querySelector('.home-state__title').innerText.trim()};
}"""


def _seed(fleet):
    vp.seed_flight_card_variety(fleet.live.state_dir, False)


@pytest.fixture(scope="module")
def fleet_app(module_app_server_factory):
    """Two frames of one owner; the live frame has seeded flights, the others none."""
    holder = start_fleet_app(module_app_server_factory, seed_extra=_seed)
    holder.cookie = session_cookie_for_state_dir(holder.server.state_dir, OWNER_EMAIL)
    return holder


@pytest.fixture(scope="module")
def long_name_app(module_app_server_factory):
    def seed(fleet):
        _seed(fleet)
        conn = fleet_db.connect(fleet.live.state_dir)
        try:
            fleet_db.rename_device(conn, fleet.live.id, LONG_NAME)
        finally:
            conn.close()
    holder = start_fleet_app(module_app_server_factory, seed_extra=seed)
    holder.cookie = session_cookie_for_state_dir(holder.server.state_dir, OWNER_EMAIL)
    return holder


@pytest.fixture(scope="module")
def admin_server(module_app_server_factory):
    return module_app_server_factory(seed=seed_state_dir, fake_providers=True)


def _fleet_page(new_context, app, path, lang="en", **context_args):
    context = new_context(**context_args)
    base = app.server.base_url()
    name, value = app.cookie.split("=", 1)
    context.add_cookies([
        {"name": name, "value": value, "url": base, "httpOnly": True, "sameSite": "Strict"},
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base}])
    page = context.new_page()
    page.goto(base + path)
    page.locator("main").wait_for(state="visible")
    page.wait_for_function(_SETTLED)
    return page


def _live(app):
    return "/devices/%s/" % app.fleet.live.id


@pytest.mark.parametrize("viewport, size", [
    (VIEWPORT_DESKTOP, 48), (VIEWPORT_PHONE, 28), (VIEWPORT_MIN_SUPPORTED, 24)],
    ids=["1280", "390", "360"])
def test_the_picture_and_the_title_column_sit_side_by_side_at_every_width(
        new_context, fleet_app, viewport, size):
    page = _fleet_page(new_context, fleet_app, _live(fleet_app), viewport=viewport)
    hero = page.evaluate(_HERO)
    assert hero["h1s"] == 1 and hero["size"] == size, hero
    # Same band, picture to the left of the title; the pill and the pencil share the column.
    assert hero["picture"]["right"] <= hero["title"]["left"] + 0.5, hero
    assert hero["picture"]["top"] <= hero["title"]["bottom"], hero
    assert hero["title"]["top"] <= hero["picture"]["bottom"], hero
    assert hero["pill"]["left"] >= hero["picture"]["right"], hero
    assert hero["pill"]["top"] >= hero["title"]["bottom"] - 1, hero
    if viewport is VIEWPORT_MIN_SUPPORTED:
        assert 90 <= hero["picture"]["width"] <= 120, hero
    failure = _assert_no_page_overflow(page, "Home", expected_width=viewport["width"])
    if failure:
        raise AssertionError(failure)


@pytest.mark.parametrize("viewport", [VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED],
                         ids=["1280", "360"])
@pytest.mark.parametrize("app_name", ["fleet_app", "long_name_app"])
def test_the_round_pencil_stays_on_the_title_line_for_a_short_and_a_long_name(
        new_context, request, app_name, viewport):
    app = request.getfixturevalue(app_name)
    page = _fleet_page(new_context, app, _live(app), viewport=viewport)
    hero = page.evaluate(_HERO)
    pencil, title = hero["pencil"], hero["title"]
    assert pencil["width"] >= 44 - 0.5 and pencil["height"] >= 44 - 0.5, hero
    assert pencil["top"] < title["bottom"] and pencil["left"] >= title["right"] - 0.5, hero
    assert pencil["right"] <= viewport["width"], hero
    assert page.locator(".title-action .btn--icon").get_attribute("aria-label") == "Rename frame"
    failure = _assert_no_page_overflow(page, "Home", expected_width=viewport["width"])
    if failure:
        raise AssertionError(failure)


def test_the_pencil_opens_the_frame_name_page(new_context, fleet_app):
    page = _fleet_page(new_context, fleet_app, _live(fleet_app))
    page.locator(".title-action .btn--icon").click()
    page.wait_for_url("**/frame/name")
    assert page.locator("main h1").inner_text() == "Rename frame"


def test_the_state_pill_holds_the_dot_and_the_state_word(new_context, fleet_app):
    page = _fleet_page(new_context, fleet_app, _live(fleet_app))
    hero = page.evaluate(_HERO)
    assert hero["dot"] and hero["word"], hero
    assert page.locator(".home-state__pill").inner_text().strip() == hero["word"]
    assert page.locator(".home-state__next-row").count() <= 1


def test_a_frame_without_a_picture_still_shows_the_empty_picture_beside_the_title(
        new_context, fleet_app):
    page = _fleet_page(new_context, fleet_app, "/devices/%s/" % fleet_app.fleet.dev_a.id)
    assert page.locator(".hero__picture .preview-frame--empty").count() == 1
    hero = page.evaluate(_HERO)
    assert hero["picture"]["right"] <= hero["title"]["left"] + 0.5, hero


def test_the_plane_on_a_trail_is_gone(new_context, fleet_app):
    page = _fleet_page(new_context, fleet_app, _live(fleet_app))
    assert page.locator(".home-trail, .home-trail__plane").count() == 0
    assert page.evaluate(
        "() => document.getAnimations().filter(a => a.animationName === 'skypane-plane-fly')"
        ".length") == 0


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
