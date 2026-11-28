# SPDX-License-Identifier: AGPL-3.0-only
"""Real-browser checks of Home's title block: the frame name is the page's one h1 (32px on a
phone, 44px on a desktop, also for a long name) with no rename pencil beside it,
the "i" at the end of the next-update sentence is a 44px control drawing a small round
opaque disc that stays on the sentence's last line in both languages at 360px, the state is a dot with its word, the flight card of a frame without a
picture still shows the empty picture, the blocks come in one after the other, and the phone tab
bar keeps its labels legible and uncramped in both themes."""
from datetime import datetime, timedelta, timezone

import animation_settle
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
from server import fleet_db, history_db

pytestmark = pytest.mark.browser

LONG_NAME = "Maison de campagne chez Tante Marguerite-Louise"

_SETTLED = animation_settle.SETTLED

_HERO = """() => {
  const box = (sel) => { const el = document.querySelector(sel);
    if (!el) return null; const r = el.getBoundingClientRect();
    return {left: r.left, right: r.right, top: r.top, bottom: r.bottom,
            width: r.width, height: r.height}; };
  const h1 = document.querySelector('main h1');
  return {title: box('main h1'), info: box('.home-state .info-tip__button'),
          size: parseFloat(getComputedStyle(h1).fontSize),
          h1s: document.querySelectorAll('h1').length,
          dot: !!document.querySelector('.home-state__status .home-state__dot'),
          word: document.querySelector('.home-state__title').innerText.trim()};
}"""


def _seed(fleet):
    """Seeded flights and a check-in two minutes ago, so the next-update line (and its "i") shows."""
    vp.seed_flight_card_variety(fleet.live.state_dir, False)
    with history_db.open_db(fleet.live.state_dir) as conn:
        history_db.record_device_health(
            conn, (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat(),
            battery_mv=4000, fw_version="1.0.0", boot_reason="wake", rssi="-60")


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
    (VIEWPORT_DESKTOP, 44), (VIEWPORT_PHONE, 32), (VIEWPORT_MIN_SUPPORTED, 32)],
    ids=["1280", "390", "360"])
def test_the_title_is_one_h1_with_the_state_under_it(new_context, fleet_app, viewport, size):
    page = _fleet_page(new_context, fleet_app, _live(fleet_app), viewport=viewport)
    hero = page.evaluate(_HERO)
    assert hero["h1s"] == 1 and hero["size"] == size, hero
    assert hero["dot"] and hero["word"], hero
    status = page.locator(".home-state__status").bounding_box()
    assert status["y"] >= hero["title"]["bottom"] - 1, hero
    failure = _assert_no_page_overflow(page, "Home", expected_width=viewport["width"])
    if failure:
        raise AssertionError(failure)


_LOOK = """sel => {
  const el = document.querySelector(sel);
  const s = getComputedStyle(el, '::before');
  const r = el.getBoundingClientRect();
  return {bg: s.backgroundColor, border: parseFloat(s.borderTopWidth), radius: s.borderTopLeftRadius,
          disc: parseFloat(s.width), discH: parseFloat(s.height), w: r.width, h: r.height};
}"""


@pytest.mark.parametrize("viewport", [VIEWPORT_DESKTOP, VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED],
                         ids=["1280", "390", "360"])
@pytest.mark.parametrize("app_name", ["fleet_app", "long_name_app"])
def test_there_is_no_pencil_and_the_info_ends_the_sentence(
        new_context, request, app_name, viewport):
    """the title has no rename control; the "i" is a 44px hit target drawing a 28px round opaque
    disc that starts where the next-update sentence ends and stays in view"""
    app = request.getfixturevalue(app_name)
    page = _fleet_page(new_context, app, _live(app), viewport=viewport)
    assert page.locator(".title-action .btn--icon, .title-action a").count() == 0
    assert page.locator("dialog[id^='dlg-rename-']").count() == 0
    hero = page.evaluate(_HERO)
    info = hero["info"]
    look = page.evaluate(_LOOK, ".home-state .info-tip__button")
    assert look["w"] >= 44 - 0.5 and look["h"] >= 44 - 0.5, look
    assert 24 <= look["disc"] <= 30 and look["disc"] == look["discH"], look
    assert look["radius"] in ("14px", "50%"), look
    assert look["bg"].startswith("rgb(") and look["bg"] != "rgb(0, 0, 0)", look
    assert look["border"] >= 1, look
    assert info["right"] <= viewport["width"], hero
    sentence = page.evaluate(_SENTENCE_END)
    # The glyph sits against the end of the sentence (the 44px target overlaps its padding only).
    assert info["left"] >= sentence["right"] - 12, (info, sentence)
    failure = _assert_no_page_overflow(page, "Home", expected_width=viewport["width"])
    if failure:
        raise AssertionError(failure)


_SENTENCE_END = """() => { const s = document.querySelector('.home-state__sentence');
  const r = document.createRange();
  r.setStart(s, 0); r.setEndBefore(s.querySelector('.info-tip'));
  const lines = [...r.getClientRects()].filter(b => b.width > 0);
  const last = lines[lines.length - 1];
  return {right: last.right, top: last.top, bottom: last.bottom, lines: lines.length}; }"""


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE], ids=["360", "390"])
def test_the_info_stays_on_the_last_line_of_the_sentence(new_context, fleet_app, lang, viewport):
    """the "i" never drops under the text: its centre is level with the sentence's last line"""
    page = _fleet_page(new_context, fleet_app, _live(fleet_app), lang=lang, viewport=viewport)
    info = page.evaluate(_HERO)["info"]
    sentence = page.evaluate(_SENTENCE_END)
    middle = (info["top"] + info["bottom"]) / 2
    assert sentence["top"] - 4 <= middle <= sentence["bottom"] + 4, (lang, info, sentence)
    assert info["left"] >= sentence["right"] - 12, (lang, info, sentence)


RENAME_DIALOG = "dialog[id^='dlg-rename-']"


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


def test_an_administrator_from_fleet_ends_on_fleet(new_context, rename_app):
    context = new_context(viewport=VIEWPORT_DESKTOP)
    page = context.new_page()
    _login(page, rename_app.server.base_url())
    page.goto(rename_app.server.base_url() + "/fleet?frame=%s" % rename_app.fleet.live.id)
    page.wait_for_function(_SETTLED)
    field = RENAME_DIALOG + " input[name=name]"
    page.locator(".fleet-head a.fleet-icon-button[title=\"Rename\"]").click()
    page.locator(RENAME_DIALOG).wait_for(state="visible")
    page.locator(field).fill("Changed")
    page.locator(RENAME_DIALOG + " a.modal__dismiss--button").click()
    page.locator(RENAME_DIALOG).wait_for(state="hidden")
    assert page.url.split("#")[0].endswith("/fleet") or "/fleet?" in page.url
    assert "tab=settings" not in page.url
    page.locator(".fleet-head a.fleet-icon-button[title=\"Rename\"]").click()
    page.locator(RENAME_DIALOG).wait_for(state="visible")
    page.locator(field).fill("Fleet name")
    page.locator(RENAME_DIALOG + " button[type=submit]").click()
    page.wait_for_url("**/fleet**")
    page.wait_for_function(
        "() => document.querySelector('.fleet-head__title').innerText === 'Fleet name'")
    assert "/frame/name" not in page.url


def test_the_state_is_a_dot_and_its_word(new_context, fleet_app):
    page = _fleet_page(new_context, fleet_app, _live(fleet_app))
    hero = page.evaluate(_HERO)
    assert hero["dot"] and hero["word"], hero
    assert page.locator(".home-state__status").inner_text().strip() == hero["word"]
    assert page.locator(".home-state__next").count() <= 1


def test_a_frame_without_a_picture_still_shows_the_empty_picture_in_the_flight_card(
        new_context, fleet_app):
    page = _fleet_page(new_context, fleet_app, "/devices/%s/" % fleet_app.fleet.dev_a.id)
    assert page.locator(".home-flight__picture .preview-frame--empty").count() == 1
    card = page.locator(".home-flight__picture").bounding_box()
    assert card["width"] > 0 and card["height"] > 0


def test_the_plane_on_a_trail_is_gone(new_context, fleet_app):
    page = _fleet_page(new_context, fleet_app, _live(fleet_app))
    assert page.locator(".home-trail, .home-trail__plane").count() == 0
    assert page.evaluate(
        "() => document.getAnimations().filter(a => a.animationName === 'skypane-plane-fly')"
        ".length") == 0


def test_the_home_blocks_come_in_one_after_the_other(new_context, fleet_app):
    context = new_context(viewport=VIEWPORT_DESKTOP)
    base = fleet_app.server.base_url()
    name, value = fleet_app.cookie.split("=", 1)
    context.add_cookies([{"name": name, "value": value, "url": base, "httpOnly": True,
                          "sameSite": "Strict"}])
    page = context.new_page()
    page.goto(base + _live(fleet_app))
    page.locator(".home-state").wait_for(state="attached")
    delays = page.evaluate(
        """() => ['.home-state', '.home-flight', '.home-pills', '.home-stats', '.home-strip'].map(
            sel => parseFloat(getComputedStyle(document.querySelector(sel)).animationDelay))""")
    # Each block one stagger step after the one before it, in page order.
    assert delays == sorted(delays) and len(set(delays)) == len(delays), delays
    page.wait_for_function(_SETTLED)
    settled = page.evaluate(
        """() => ['.home-state', '.home-pills'].map(sel => {
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


def test_the_round_info_button_holds_its_glyph_at_the_centre(new_context, fleet_app):
    """the glyph of the "i" sits at the centre of its button, so it is centred in the circle
    drawn behind it"""
    page = _fleet_page(new_context, fleet_app, _live(fleet_app), viewport=VIEWPORT_DESKTOP)
    centres = page.evaluate(
        "([b, g]) => { const c = (s) => { const r = document.querySelector(s).getBoundingClientRect();"
        " return [r.left + r.width / 2, r.top + r.height / 2]; }; return [c(b), c(g)]; }",
        [".home-state .info-tip__button", ".home-state .info-tip__button .icon"])
    assert abs(centres[0][0] - centres[1][0]) <= 0.5, centres
    assert abs(centres[0][1] - centres[1][1]) <= 0.5, centres
