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
    _in_both_themes, _login, _no_js_page, seed_state_dir)
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
          pencil: box('.title-action .btn--icon'),
          glyph: box('.title-action .btn--icon .icon'), pill: box('.home-state__pill'),
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


_PENCIL_LOOK = """() => {
  const btn = document.querySelector('.title-action .btn--icon');
  const s = getComputedStyle(btn);
  const h1 = getComputedStyle(document.querySelector('main h1'));
  return {bg: s.backgroundColor, border: parseFloat(s.borderTopWidth), shadow: s.boxShadow,
          color: s.color, text: h1.color, lineHeight: parseFloat(h1.lineHeight)};
}"""


@pytest.mark.parametrize("viewport, glyph", [
    (VIEWPORT_DESKTOP, 20), (VIEWPORT_PHONE, 20), (VIEWPORT_MIN_SUPPORTED, 18)],
    ids=["1280", "390", "360"])
@pytest.mark.parametrize("app_name", ["fleet_app", "long_name_app"])
def test_the_quiet_pencil_stays_level_with_the_first_title_line_for_a_short_and_a_long_name(
        new_context, request, app_name, viewport, glyph):
    app = request.getfixturevalue(app_name)
    page = _fleet_page(new_context, app, _live(app), viewport=viewport)
    hero = page.evaluate(_HERO)
    pencil, title, mark = hero["pencil"], hero["title"], hero["glyph"]
    # A small glyph inside an invisible 44px hit area.
    assert abs(mark["width"] - glyph) <= 0.5 and abs(mark["height"] - glyph) <= 0.5, hero
    assert pencil["width"] >= 44 - 0.5 and pencil["height"] >= 44 - 0.5, hero
    # Centred on the first line of the title, which it never overlaps.
    line = page.evaluate(_PENCIL_LOOK)["lineHeight"]
    assert abs((mark["top"] + mark["bottom"]) / 2 - (title["top"] + line / 2)) <= 1.5, hero
    assert pencil["left"] >= title["right"] - 0.5, hero
    assert pencil["right"] <= viewport["width"], hero
    # No disc at rest; the glyph takes the muted text colour.
    look = page.evaluate(_PENCIL_LOOK)
    assert look["bg"] in ("rgba(0, 0, 0, 0)", "transparent"), look
    assert look["border"] == 0 and look["shadow"] == "none", look
    assert look["color"] != look["text"], look
    assert page.locator(".title-action .btn--icon").get_attribute("aria-label") == "Rename frame"
    failure = _assert_no_page_overflow(page, "Home", expected_width=viewport["width"])
    if failure:
        raise AssertionError(failure)


@pytest.mark.parametrize("viewport", [VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED],
                         ids=["1280", "360"])
def test_the_pencil_shows_a_light_halo_only_on_hover(
        new_context, fleet_app, viewport):
    page = _fleet_page(new_context, fleet_app, _live(fleet_app), viewport=viewport)
    pencil = page.locator(".title-action .btn--icon")
    for _theme in _in_both_themes(page):
        page.wait_for_function(_SETTLED)
        page.mouse.move(0, 0)
        rest = pencil.evaluate("el => getComputedStyle(el).backgroundColor")
        pencil.hover()
        page.wait_for_function(
            "(rest) => getComputedStyle(document.querySelector('.title-action .btn--icon'))"
            ".backgroundColor !== rest", arg=rest)
        page.wait_for_function(_SETTLED)
        halo = pencil.evaluate("el => getComputedStyle(el).backgroundColor")
        assert halo != rest and halo != "rgba(0, 0, 0, 0)", (rest, halo)


@pytest.fixture
def rename_app(module_app_server_factory):
    """A fleet of its own, so renaming never changes the name other tests read."""
    holder = start_fleet_app(module_app_server_factory, seed_extra=_seed)
    holder.cookie = session_cookie_for_state_dir(holder.server.state_dir, OWNER_EMAIL)
    conn = fleet_db.connect(holder.server.state_dir)
    try:
        fleet_db.rename_device(conn, holder.fleet.live.id, "Kitchen")
    finally:
        conn.close()
    return holder


def _on_rename_page(page):
    page.wait_for_url("**/frame/name**")
    page.wait_for_function(_SETTLED)
    assert page.locator("main h1").inner_text() == "Rename frame"


def _is_home(page, app):
    page.wait_for_url(app.server.base_url() + _live(app) + "**")
    page.wait_for_function(_SETTLED)
    assert "/frame/name" not in page.url and "/fleet" not in page.url


def test_the_pencil_opens_the_frame_name_page_for_a_return_to_home(new_context, fleet_app):
    page = _fleet_page(new_context, fleet_app, _live(fleet_app))
    href = page.locator(".title-action .btn--icon").get_attribute("href")
    assert "return_to=" in href
    page.locator(".title-action .btn--icon").click()
    _on_rename_page(page)
    assert page.locator("a.form-back").get_attribute("href") == _live(fleet_app)


@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_DESKTOP], ids=["390", "1280"])
def test_cancel_and_the_back_link_end_on_home_and_leave_the_name(
        new_context, rename_app, viewport):
    for leave in ("a.dirty-bar__cancel", "a.form-back"):
        page = _fleet_page(new_context, rename_app, _live(rename_app), viewport=viewport)
        page.locator(".title-action .btn--icon").click()
        _on_rename_page(page)
        page.locator("#frame-name").fill("Changed")
        page.locator(leave).click()
        if leave == "a.form-back":
            # The back link is an in-app link: with an unsaved name the page
            # asks first, and Discard leaves without saving it.
            page.locator("dialog[data-leave-dialog] [data-leave-dialog-secondary]").click()
        _is_home(page, rename_app)
        assert page.locator("main h1").inner_text() == "Kitchen"
        assert page.locator(".title-action .btn--icon").count() == 1


@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_DESKTOP], ids=["390", "1280"])
def test_save_ends_on_home_with_the_new_name(
        new_context, rename_app, viewport):
    page = _fleet_page(new_context, rename_app, _live(rename_app), viewport=viewport)
    page.locator(".title-action .btn--icon").click()
    _on_rename_page(page)
    page.locator("#frame-name").fill("Den")
    page.locator(".dirty-bar button.dirty-bar__save").click()
    _is_home(page, rename_app)
    page.wait_for_function("() => document.querySelector('main h1').innerText === 'Den'")
    assert page.locator(".frame-menu").inner_text().count("Den") >= 1
    assert page.locator("main h1").inner_text() == "Den"


def test_browser_back_from_the_rename_page_lands_on_home(new_context, rename_app):
    page = _fleet_page(new_context, rename_app, _live(rename_app))
    page.locator(".title-action .btn--icon").click()
    _on_rename_page(page)
    page.go_back()
    _is_home(page, rename_app)


def test_an_empty_name_keeps_the_error_and_the_way_back_to_home(new_context, rename_app):
    page = _fleet_page(new_context, rename_app, _live(rename_app))
    page.locator(".title-action .btn--icon").click()
    _on_rename_page(page)
    page.locator("#frame-name").fill("")
    page.locator(".dirty-bar button.dirty-bar__save").click()
    page.wait_for_selector("#frame-name-error")
    page.locator("a.dirty-bar__cancel").click()
    _is_home(page, rename_app)


def test_a_hostile_return_to_is_ignored_by_the_page(new_context, rename_app):
    page = _fleet_page(
        new_context, rename_app,
        "/devices/%s/frame/name?return_to=https%%3A%%2F%%2Fevil.example%%2F" % rename_app.fleet.live.id)
    back = page.locator("a.form-back").get_attribute("href")
    assert back.startswith("/") and not back.startswith("//") and "evil" not in back
    assert page.locator('input[name="return_to"]').count() == 0


def test_without_script_the_pencil_save_and_cancel_return_to_home(new_context, rename_app):
    base = rename_app.server.base_url()
    name, value = rename_app.cookie.split("=", 1)
    cookies = [{"name": name, "value": value, "url": base, "httpOnly": True,
                "sameSite": "Strict"}]
    for action in ("save", "cancel"):
        with _no_js_page(new_context, base, _live(rename_app), sign_in=False,
                         cookies=cookies, reduced_motion="reduce") as page:
            with page.expect_navigation():
                page.locator(".title-action .btn--icon").click()
            assert "return_to=" in page.url
            before = page.locator("#frame-name").input_value()
            page.locator("#frame-name").fill("No script")
            with page.expect_navigation():
                page.locator(
                    ".dirty-bar__save" if action == "save" else ".dirty-bar__cancel").click()
            assert page.url.split("?")[0] == base + _live(rename_app)
            expected = "No script" if action == "save" else before
            assert page.locator("main h1").inner_text() == expected


def test_an_administrator_from_fleet_ends_on_fleet(new_context, rename_app):
    context = new_context(viewport=VIEWPORT_DESKTOP)
    page = context.new_page()
    _login(page, rename_app.server.base_url())
    page.goto(rename_app.server.base_url() + "/fleet")
    page.wait_for_function(_SETTLED)
    page.locator(".fleet-detail-head a.row-action", has_text="Rename").click()
    page.wait_for_url("**/frame/name**")
    page.wait_for_function(_SETTLED)
    page.locator("#frame-name").fill("Changed")
    page.locator("a.dirty-bar__cancel").click()
    page.wait_for_url("**/fleet**")
    assert "tab=settings" not in page.url
    page.locator(".fleet-detail-head a.row-action", has_text="Rename").click()
    page.wait_for_url("**/frame/name**")
    page.locator("#frame-name").fill("Fleet name")
    page.locator(".dirty-bar button.dirty-bar__save").click()
    page.wait_for_url("**/fleet**")
    assert "/frame/name" not in page.url


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
        """() => ['.home-facts', '.home-state', '.home-detection', '.home-state__switches',
                  'section[aria-labelledby="home-flights"]'].map(
            sel => getComputedStyle(document.querySelector(sel)).animationDelay)""")
    # One step after the header for the facts row, then one more for each block in page order.
    assert delays == ["0.06s", "0.12s", "0.18s", "0.24s", "0.3s"], delays
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
                      narrow: cells.filter(r => r.width < 44 || r.height < 44).length};
            }""")
        assert read["inks"], where
        assert read["clipped"] == 0 and read["narrow"] == 0, (where, read)
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
