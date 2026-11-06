"""Real-browser checks of the Fleet page's phone sub-tabs (State, Settings, Access): one
segmented control that fits 360 and 390 px in English and French, each tab showing only its own
groups, a plain-link deep link that works without scripts, the full single page on a desktop, the
unsaved-changes bar on the Settings tab, and the designed empty picture on Home."""
import pytest

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT, VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _login, _set_ui_theme,
)

pytestmark = pytest.mark.browser

PHONE = {"width": 390, "height": 844}
LABELS = {"en": ["State", "Settings", "Access"], "fr": ["État", "Réglages", "Accès"]}
TABS = ("state", "settings", "access")
_SETTLED = (
    "() => document.readyState === 'complete' && document.getAnimations().every("
    "a => !a.effect || a.effect.getTiming().iterations === Infinity || a.playState !== 'running')")
_PROBE = """() => {
  const nav = document.querySelector('nav.fleet-tabs');
  const shown = (el) => el.getClientRects().length > 0;
  return {
    nav: shown(nav),
    overflow: nav.scrollWidth - nav.clientWidth,
    links: [...nav.querySelectorAll('a')].map((a) => {
      const r = a.getBoundingClientRect(); const s = a.querySelector('span');
      return {text: s.textContent, h: r.height, clipped: s.scrollWidth > s.clientWidth + 0.5,
              current: a.getAttribute('aria-current')};
    }),
    blocks: [...document.querySelectorAll('.fleet-block')].filter(shown).map(
      (b) => b.querySelector('ul.group').parentElement.className.match(/fleet-block--(\\w+)/)[1]),
    other: !!document.querySelector('.fleet-panel-access') &&
      shown(document.querySelector('.fleet-panel-access')),
    pageOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  };
}"""


def _open(new_context, server, viewport, lang, tab=None, theme="light", live_id=None):
    live_id = live_id or fx.seed_fleet(server.state_dir).live_id
    context = new_context(viewport=viewport)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/fleet?frame=%s%s" % (
        live_id, "" if tab is None else "&tab=" + tab))
    page.wait_for_function(_SETTLED, timeout=15000)
    _set_ui_theme(page, theme)
    page.wait_for_function(_SETTLED, timeout=15000)
    return context, page


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, PHONE], ids=["360", "390"])
def test_each_tab_fits_and_shows_only_its_own_groups(
        new_context, app_server_in_process, viewport, lang):
    live_id = fx.seed_fleet(app_server_in_process.state_dir).live_id
    for tab in TABS:
        context, page = _open(
            new_context, app_server_in_process, viewport, lang, tab, live_id=live_id)
        try:
            probe = page.evaluate(_PROBE)
            assert probe["nav"] and probe["overflow"] <= 0 and probe["pageOverflow"] <= 0, probe
            assert [link["text"] for link in probe["links"]] == LABELS[lang]
            assert all(link["h"] >= 44 and not link["clipped"] for link in probe["links"])
            assert [link["current"] for link in probe["links"]] == [
                "page" if name == tab else None for name in TABS]
            assert set(probe["blocks"]) == {tab}, probe
            assert probe["other"] is (tab == "access")
        finally:
            context.close()


def test_the_default_tab_is_state_and_a_link_changes_tab_without_scripts(
        new_context, app_server_in_process):
    seed = fx.seed_fleet(app_server_in_process.state_dir)
    context = new_context(viewport=PHONE, java_script_enabled=False)
    page = context.new_page()
    try:
        _login(page, app_server_in_process.base_url())
        page.goto(app_server_in_process.base_url() + "/fleet?frame=" + seed.live_id)
        assert page.locator('nav.fleet-tabs a[aria-current="page"]').inner_text() == "State"
        page.locator("nav.fleet-tabs a", has_text="Settings").click()
        page.wait_for_url("**tab=settings")
        assert page.locator("#wake-interval-s").is_visible()
        assert page.locator(".fleet-block--state").first.is_hidden()
    finally:
        context.close()


def test_a_desktop_shows_every_group_and_no_tabs(new_context, app_server_in_process):
    context, page = _open(new_context, app_server_in_process, VIEWPORT_DESKTOP, "en")
    try:
        probe = page.evaluate(_PROBE)
        assert probe["nav"] is False
        assert set(probe["blocks"]) == set(TABS)
        assert probe["other"] is True
    finally:
        context.close()


def test_the_unsaved_changes_bar_shows_on_the_settings_tab(new_context, app_server_in_process):
    context, page = _open(new_context, app_server_in_process, PHONE, "en", "settings")
    try:
        page.locator("#wake-interval-s").fill("900")
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


def test_the_other_frames_card_is_evenly_padded_and_a_pending_frame_offers_pairing(
        new_context, app_server_in_process):
    context, page = _open(new_context, app_server_in_process, PHONE, "en", "access")
    try:
        gaps = page.evaluate(
            "() => { const s = document.querySelector('.fleet-panel-access');"
            " const a = s.getBoundingClientRect();"
            " const r = s.querySelector('.fleet-other > summary').getBoundingClientRect();"
            " return [r.top - a.top, a.bottom - r.bottom]; }")
        assert abs(gaps[0] - gaps[1]) <= 2, gaps
        page.locator(".fleet-other > summary").click()
        row = page.locator(".entity-row", has_text="Waiting for pairing")
        row.locator("summary.row-menu__toggle").click()
        assert row.locator(".row-menu__list, .row-menu").get_by_text("Pair frame").count() >= 1
    finally:
        context.close()
