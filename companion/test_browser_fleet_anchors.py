"""Real-browser checks of the phone sections of a frame's page: State, Settings and Access stacked
under three anchors that stay at the top while the page scrolls, each 44 px and fitting 360 and
390 px in English and French, the section in view marked current, plain links that work without
scripts, a saved-section landing, the three State tiles, the full single column on a desktop,
the unsaved-changes bar, and the designed empty picture on Home."""
import animation_settle
import pytest

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT, VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _login, _set_ui_theme,
)

pytestmark = pytest.mark.browser

PHONE = {"width": 390, "height": 844}
LABELS = {"en": ["State", "Settings", "Access"], "fr": ["État", "Réglages", "Accès"]}
SECTIONS = ("state", "settings", "access")
_SETTLED = animation_settle.SETTLED
_PROBE = """() => {
  const nav = document.querySelector('nav.fleet-anchors');
  const shown = (el) => el.getClientRects().length > 0;
  return {
    nav: shown(nav),
    overflow: nav.scrollWidth - nav.clientWidth,
    links: [...nav.querySelectorAll('a')].map((a) => {
      const r = a.getBoundingClientRect();
      return {text: a.textContent, h: r.height, clipped: a.scrollWidth > a.clientWidth + 0.5,
              current: a.getAttribute('aria-current')};
    }),
    sections: [...document.querySelectorAll('.fleet-blocks > .fleet-block')].filter(shown).map(
      (b) => ({id: b.id.replace('fleet-section-', ''), top: b.getBoundingClientRect().top + scrollY})),
    pageOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  };
}"""
_TILES = """() => [...document.querySelectorAll('#fleet-section-state .fleet-tile')].map((t) => {
  const r = t.getBoundingClientRect();
  return {x: r.left, y: r.top, w: r.width, h: r.height};
})"""


def _open(new_context, server, viewport, lang, query="", theme="light", live_id=None, **args):
    live_id = live_id or fx.seed_fleet(server.state_dir).live_id
    context = new_context(viewport=viewport, **args)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/fleet?frame=%s%s" % (live_id, query))
    if args.get("java_script_enabled", True):
        page.wait_for_function(_SETTLED, timeout=15000)
        _set_ui_theme(page, theme)
        page.wait_for_function(_SETTLED, timeout=15000)
    return context, page


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, PHONE], ids=["360", "390"])
def test_the_three_anchors_fit_and_all_three_sections_are_stacked_in_order(
        new_context, app_server_in_process, viewport, lang):
    context, page = _open(new_context, app_server_in_process, viewport, lang)
    try:
        probe = page.evaluate(_PROBE)
        assert probe["nav"] and probe["overflow"] <= 0 and probe["pageOverflow"] <= 0, probe
        assert [link["text"] for link in probe["links"]] == LABELS[lang]
        assert all(link["h"] >= 44 and not link["clipped"] for link in probe["links"])
        assert [link["current"] for link in probe["links"]] == ["true", None, None]
        assert [s["id"] for s in probe["sections"]] == list(SECTIONS), probe
        tops = [s["top"] for s in probe["sections"]]
        assert tops == sorted(tops) and len(set(tops)) == 3
        assert page.locator("nav.fleet-tabs").count() == 0
    finally:
        context.close()


@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_sticky_bar_is_solid_and_covers_the_gap_above_it_on_an_iphone(
        new_context, app_server_in_process, lang, theme):
    """with a notch (safe area) and the installed web app's drop, the bar sticks below that gap:
    its own background is opaque and the gap above it is painted too, so scrolled content never
    shows through between the screen top and the chips"""
    context, page = _open(new_context, app_server_in_process, PHONE, lang, theme=theme)
    try:
        page.evaluate(
            "() => { document.documentElement.classList.add('web-app');"
            " document.documentElement.style.setProperty('--safe-top', '47px'); }")
        page.evaluate("() => window.scrollTo(0, document.documentElement.scrollHeight)")
        page.wait_for_function(
            "() => document.querySelector('nav.fleet-anchors').getBoundingClientRect().top > 60",
            timeout=5000)
        look = page.evaluate(
            """() => {
              const nav = document.querySelector('nav.fleet-anchors');
              const alpha = (c) => { const p = c.slice(c.indexOf('(') + 1, -1).split(',');
                                     return p.length === 4 ? parseFloat(p[3]) : 1; };
              const gap = getComputedStyle(nav, '::before');
              return {top: nav.getBoundingClientRect().top, bar: alpha(getComputedStyle(nav).backgroundColor),
                      strip: alpha(gap.backgroundColor), stripHeight: parseFloat(gap.height),
                      hit: [2, 20, 40, 60].map((y) => document.elementFromPoint(195, y) === nav)};
            }""")
        assert look["bar"] == 1 and look["strip"] == 1, look
        assert abs(look["stripHeight"] - look["top"]) <= 1, look
        assert all(look["hit"]), look
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, PHONE, VIEWPORT_DESKTOP],
                         ids=["360", "390", "1440"])
def test_the_state_section_is_two_equal_tiles_over_a_full_width_firmware_tile(
        new_context, app_server_in_process, viewport, lang):
    context, page = _open(new_context, app_server_in_process, viewport, lang)
    try:
        tiles = page.evaluate(_TILES)
        assert len(tiles) == 3, tiles
        connection, battery, firmware = tiles
        # Connection and Battery side by side, equal; Firmware under both, as wide as the two
        # together and the gap between them.
        assert abs(connection["w"] - battery["w"]) < 1 and abs(connection["h"] - battery["h"]) < 1
        assert abs(connection["y"] - battery["y"]) < 1 and battery["x"] > connection["x"]
        assert abs(firmware["x"] - connection["x"]) < 1 and firmware["y"] > connection["y"]
        assert abs(firmware["x"] + firmware["w"] - (battery["x"] + battery["w"])) < 1
        assert min(t["h"] for t in tiles) >= 44
        assert page.evaluate(
            "() => document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 0
        assert [a.inner_text().split("\n")[-1].strip() for a in
                page.locator("a.fleet-tile .fleet-tile__more").all()] == [
            "Details" if lang == "en" else "Détails"] * 2
    finally:
        context.close()


def test_the_anchors_stay_at_the_top_and_mark_the_section_in_view(
        new_context, app_server_in_process):
    context, page = _open(new_context, app_server_in_process, PHONE, "en")
    try:
        nav = page.locator("nav.fleet-anchors")
        page.evaluate("() => window.scrollTo(0, document.documentElement.scrollHeight)")
        page.wait_for_function(
            "() => document.querySelector('.fleet-anchor[aria-current]').textContent === 'Access'",
            timeout=5000)
        assert nav.bounding_box()["y"] <= 1, nav.bounding_box()
        page.evaluate("() => window.scrollTo(0, 0)")
        page.wait_for_function(
            "() => document.querySelector('.fleet-anchor[aria-current]').textContent === 'State'",
            timeout=5000)
        page.locator("nav.fleet-anchors a", has_text="Settings").click()
        page.wait_for_function(
            "() => document.querySelector('.fleet-anchor[aria-current]').textContent === 'Settings'",
            timeout=5000)
        top = page.locator("#fleet-section-settings").bounding_box()["y"]
        bar = nav.bounding_box()
        assert bar["y"] + bar["height"] - 2 <= top <= bar["y"] + bar["height"] + 40, (top, bar)
        assert page.locator("#wake-interval-m").is_visible()
    finally:
        context.close()


def test_an_anchor_is_a_plain_link_that_works_without_scripts(new_context, app_server_in_process):
    seed = fx.seed_fleet(app_server_in_process.state_dir)
    context = new_context(viewport=PHONE, java_script_enabled=False)
    page = context.new_page()
    try:
        _login(page, app_server_in_process.base_url())
        page.goto(app_server_in_process.base_url() + "/fleet?frame=" + seed.live_id)
        assert page.locator('nav.fleet-anchors a[aria-current="true"]').inner_text() == "State"
        page.locator("nav.fleet-anchors a", has_text="Access").click()
        assert page.url.endswith("#fleet-section-access")
        assert page.locator("#fleet-section-access").is_visible()
        assert page.locator("#fleet-section-access").bounding_box()["y"] < PHONE["height"] - 100
    finally:
        context.close()


@pytest.mark.parametrize("section", ["settings", "access"])
def test_a_save_returns_to_its_section_on_a_phone_and_not_on_a_desktop(
        new_context, app_server_in_process, section):
    seed = fx.seed_fleet(app_server_in_process.state_dir)
    context, page = _open(
        new_context, app_server_in_process, PHONE, "en", "&tab=" + section, live_id=seed.live_id)
    try:
        page.wait_for_function(
            "(s) => { const t = document.getElementById('fleet-section-' + s)"
            ".getBoundingClientRect().top; return t > 0 && t < innerHeight - 100; }",
            arg=section, timeout=5000)
        assert page.evaluate("() => window.pageYOffset") > 0
        page.wait_for_function(
            "(s) => document.querySelector('.fleet-anchor[aria-current]').textContent === s",
            arg=section.capitalize(), timeout=5000)
    finally:
        context.close()
    context, page = _open(
        new_context, app_server_in_process, VIEWPORT_DESKTOP, "en", "&tab=" + section,
        live_id=seed.live_id)
    try:
        assert page.evaluate("() => window.pageYOffset") == 0
    finally:
        context.close()


def test_a_desktop_shows_every_section_in_one_column_and_no_anchors(
        new_context, app_server_in_process):
    context, page = _open(new_context, app_server_in_process, VIEWPORT_DESKTOP, "en")
    try:
        probe = page.evaluate(_PROBE)
        assert probe["nav"] is False
        assert [s["id"] for s in probe["sections"]] == list(SECTIONS)
    finally:
        context.close()


def test_the_unsaved_changes_bar_shows_in_the_settings_section(new_context, app_server_in_process):
    context, page = _open(new_context, app_server_in_process, PHONE, "en", "&tab=settings")
    try:
        page.locator("#wake-interval-m").fill("15")
        page.locator("[data-dirty-bar]").wait_for(state="visible")
    finally:
        context.close()


@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
def test_a_frame_with_no_picture_shows_a_designed_empty_state(
        new_context, app_server_in_process, theme):
    context = new_context(viewport=PHONE)
    page = context.new_page()
    try:
        _login(page, app_server_in_process.base_url())
        page.goto(app_server_in_process.base_url() + "/")
        page.wait_for_function(_SETTLED, timeout=15000)
        _set_ui_theme(page, theme)
        empty = page.locator(".preview-empty")
        empty.wait_for(state="visible")
        assert "No picture yet" in empty.inner_text()
        page.wait_for_function(
            "() => getComputedStyle(document.querySelector('.preview-empty')).backgroundColor"
            " !== 'rgb(255, 255, 255)'", timeout=5000)
    finally:
        context.close()


def test_a_pending_frames_page_offers_pairing_with_an_evenly_padded_centred_button(
        new_context, app_server_in_process):
    seed = fx.seed_fleet(app_server_in_process.state_dir)
    context = new_context(viewport=PHONE)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": "en", "url": app_server_in_process.base_url()}])
    page = context.new_page()
    try:
        _login(page, app_server_in_process.base_url())
        page.goto(app_server_in_process.base_url() + "/fleet?frame=" + seed.pending_id)
        page.wait_for_function(_SETTLED, timeout=15000)
        gaps = page.evaluate(
            "() => { const s = document.querySelector('.fleet-other .group');"
            " const a = s.getBoundingClientRect();"
            " const b = s.querySelector('a.fleet-action-button').getBoundingClientRect();"
            " return [b.top - a.top, a.bottom - b.bottom]; }")
        assert abs(gaps[0] - gaps[1]) <= 2, gaps
        button = page.locator(".fleet-other a.fleet-action-button")
        assert button.inner_text() == "Pair frame"
        style = button.evaluate(
            "e => { const c = getComputedStyle(e); return [c.justifyContent, c.textAlign]; }")
        assert style == ["center", "center"]
        assert button.bounding_box()["height"] >= 44
    finally:
        context.close()
