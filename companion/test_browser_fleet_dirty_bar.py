"""Real-browser checks of the Fleet settings save bar: once a setting changes, the bar sits at
the bottom of the viewport (above the floating tab bar on a phone, inside the content column
on a desktop), is as wide as that column, says "Unsaved changes" with Cancel and Save, keeps
44px targets, never overlaps the tab bar and, at the end of the page, never covers a card.
Also the wake interval card: one visible label, the value in minutes beside the seconds."""
import pytest

import fleet_console_support as fx
from companion import auth
from server import device_config
from companion.test_browser_ux_helpers import VIEWPORT_DESKTOP, _login

pytestmark = pytest.mark.browser

PHONE = {"width": 390, "height": 844}
WORDS = {"en": ("Unsaved changes", "Cancel", "Save"),
         "fr": ("Modifications non enregistrées", "Annuler", "Enregistrer")}
_SETTLED = (
    "() => document.readyState === 'complete' && document.getAnimations().every("
    "a => !a.effect || a.effect.getTiming().iterations === Infinity || a.playState !== 'running')")
_OWNS_CENTRE = (
    "sel => { const el = document.querySelector(sel); if (!el) return false;"
    " const r = el.getBoundingClientRect();"
    " const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);"
    " return !!hit && (hit === el || el.contains(hit) || hit.contains(el)); }")
_RECT = (
    "sel => { const r = document.querySelector(sel).getBoundingClientRect();"
    " return {top: r.top, bottom: r.bottom, left: r.left, right: r.right, width: r.width,"
    " height: r.height, vh: window.innerHeight, vw: document.documentElement.clientWidth}; }")
BAR = "[data-dirty-bar]"


def _open(new_context, server, viewport, lang):
    seed = fx.seed_fleet(server.state_dir)
    device_config.save_device_config(server.state_dir, wake_interval_s=600)
    context = new_context(viewport=viewport)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/fleet?tab=settings&frame=" + seed.live_id)
    page.locator("#wake-interval-s").wait_for(state="visible")
    page.wait_for_function(_SETTLED, timeout=15000)
    return context, page


def _make_dirty(page):
    page.locator("#wake-interval-s").fill("900")
    page.locator(BAR).wait_for(state="visible")
    page.wait_for_function(_SETTLED, timeout=15000)
    for selector in (BAR + " .dirty-bar__save", BAR + " .dirty-bar__cancel"):
        page.wait_for_function(_OWNS_CENTRE, arg=selector, timeout=10000)


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [PHONE, VIEWPORT_DESKTOP], ids=["390", "1280"])
def test_the_bar_is_docked_inside_the_viewport_and_never_overlaps_the_tab_bar(
        new_context, app_server_in_process, viewport, lang):
    context, page = _open(new_context, app_server_in_process, viewport, lang)
    try:
        assert page.locator(BAR).is_hidden()
        _make_dirty(page)
        text, cancel, save = WORDS[lang]
        assert page.locator(BAR + " [data-dirty-count]").inner_text() == text
        assert page.locator(BAR + " .dirty-bar__cancel").inner_text() == cancel
        assert page.locator(BAR + " .dirty-bar__save").inner_text() == save
        bar = page.evaluate(_RECT, BAR)
        assert bar["top"] >= 0 and bar["bottom"] <= bar["vh"], bar
        assert bar["left"] >= 0 and bar["right"] <= bar["vw"], bar
        main = page.evaluate(_RECT, "main")
        if viewport["width"] >= 960:
            assert bar["bottom"] > bar["vh"] - 48, bar
            assert bar["width"] >= 600, bar
            assert bar["left"] >= main["left"] - 1 and bar["right"] <= main["right"] + 1, (bar, main)
        else:
            tab_bar = page.evaluate(_RECT, ".tab-bar")
            assert bar["bottom"] <= tab_bar["top"], (bar, tab_bar)
            assert bar["width"] >= 300, bar
        for selector in (BAR + " .dirty-bar__save", BAR + " .dirty-bar__cancel"):
            box = page.evaluate(_RECT, selector)
            assert box["width"] >= 44 and box["height"] >= 44, (selector, box)
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [PHONE, VIEWPORT_DESKTOP], ids=["390", "1280"])
def test_at_the_end_of_the_page_the_bar_covers_no_card(
        new_context, app_server_in_process, viewport):
    context, page = _open(new_context, app_server_in_process, viewport, "en")
    try:
        _make_dirty(page)
        page.evaluate("() => window.scrollTo(0, document.documentElement.scrollHeight)")
        page.wait_for_function(
            "() => Math.ceil(window.scrollY + window.innerHeight)"
            " >= document.documentElement.scrollHeight - 1", timeout=10000)
        page.wait_for_function(_SETTLED, timeout=15000)
        bar = page.evaluate(_RECT, BAR)
        last_card_bottom = page.evaluate(
            "() => Math.max(...[...document.querySelectorAll('.fleet-blocks .group')]"
            ".map(g => g.getBoundingClientRect().bottom))")
        assert bar["top"] >= last_card_bottom - 1, (bar, last_card_bottom)
    finally:
        context.close()


def test_cancel_hides_the_bar_and_restores_the_value(new_context, app_server_in_process):
    context, page = _open(new_context, app_server_in_process, VIEWPORT_DESKTOP, "en")
    try:
        before = page.locator("#wake-interval-s").input_value()
        _make_dirty(page)
        page.locator(BAR + " .dirty-bar__cancel").click()
        page.locator(BAR).wait_for(state="hidden")
        page.wait_for_function(
            "v => document.querySelector('#wake-interval-s').value === v", arg=before)
    finally:
        context.close()


@pytest.mark.parametrize("lang,unit,minutes", [("en", "seconds", "15 min"), ("fr", "secondes", "15 mn")])
def test_the_wake_interval_card_has_one_visible_label_and_shows_minutes(
        new_context, app_server_in_process, lang, unit, minutes):
    context, page = _open(new_context, app_server_in_process, VIEWPORT_DESKTOP, lang)
    try:
        field = page.locator("#wake-interval-s")
        assert page.locator("label[for='wake-interval-s']").evaluate(
            "el => el.classList.contains('visually-hidden')")
        card = page.locator(".theme-status:has(#wake-interval-s)")
        assert card.locator("h2").count() == 1
        assert unit in card.inner_text()
        assert "10 min" in card.inner_text().replace("mn", "min")
        field.fill("900")
        page.wait_for_function(
            "m => document.querySelector('.theme-status:has(#wake-interval-s)')"
            ".innerText.includes(m)", arg=minutes, timeout=10000)
        assert field.evaluate(
            "el => getComputedStyle(el).appearance") in ("textfield", "none")
    finally:
        context.close()
