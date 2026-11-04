"""Real-browser checks of the Personalisation page (/display): at 360 and
1280 px, in English and French, in both themes, nothing overflows sideways and
every control (look cards, On this page links, Customise look, the Screen
switch) is at least 44x44 and owns its own centre; tapping a look raises the
save bar naming Look and Save persists the look after a reload; the On this
page links move to their cards; the look sheet opens from Customise look and
Escape returns focus to it; and the sheet and the cards are one control."""
import pytest

from companion import auth, layout
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT,
    VIEWPORT_DESKTOP,
    VIEWPORT_MIN_SUPPORTED,
    _assert_no_page_overflow,
    _bar_text,
    _login,
    _save_via_bar,
    _set_ui_theme,
    _wait_for_bar,
    seed_state_dir,
)
from server import device_config

pytestmark = pytest.mark.browser

VIEWPORTS = (("360", VIEWPORT_MIN_SUPPORTED), ("1280", VIEWPORT_DESKTOP))
CARD_IDS = ("look", "special-looks", "calendar", "screen")
SAVED_LOOK = "band_red_field"
CHANGED_LOOK = "black"

_OWNS_CENTRE = (
    "el => { const r = el.getBoundingClientRect();"
    " const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);"
    " return !!hit && (hit === el || el.contains(hit) || hit.contains(el)); }")
_SETTLED = (
    "() => document.readyState === 'complete'"
    " && document.getAnimations().every(a => a.effect && a.effect.getTiming().iterations !== Infinity"
    " ? a.playState !== 'running' : true)")


def _seed(state_dir):
    seed_state_dir(state_dir)
    device_config.save_device_config(state_dir, theme=SAVED_LOOK)


def _open(new_context, base_url, viewport, lang="en", theme="light"):
    context = new_context(viewport=viewport)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
    page = context.new_page()
    _login(page, base_url)
    page.goto(base_url + layout.DISPLAY_ROUTE)
    page.wait_for_function(_SETTLED, timeout=15000)
    page.locator("button.look-pick__customise").wait_for(state="visible")
    _set_ui_theme(page, theme)
    return context, page


def _measure(page, selector):
    """Every match of `selector`, scrolled to the middle of the screen, as (box, owns_centre)."""
    out = []
    handles = page.locator(selector)
    for index in range(handles.count()):
        handle = handles.nth(index)
        handle.evaluate("el => el.scrollIntoView({block: 'center'})")
        page.wait_for_function(
            "el => { const r = el.getBoundingClientRect();"
            " const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);"
            " return !!hit && (hit === el || el.contains(hit) || hit.contains(el)); }",
            arg=handle.element_handle(), timeout=10000)
        out.append((handle.bounding_box(), handle.evaluate(_OWNS_CENTRE)))
    return out


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("label,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_no_overflow_and_every_control_is_44px_and_reachable(
        new_context, make_app_server, label, viewport, theme, lang):
    """the page does not scroll sideways and each look card, nav link, the Customise look
    button and the Screen switch is at least 44x44 and owns its own centre"""
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), viewport, lang=lang, theme=theme)
    try:
        overflow = _assert_no_page_overflow(page, "personalisation", viewport["width"])
        assert not overflow, overflow
        selectors = (
            ".look-pick__card", ".personalisation__link", "button.look-pick__customise",
            "#personalisation-screen button.switch")
        for selector in selectors:
            measured = _measure(page, selector)
            assert measured, selector
            for box, owns in measured:
                assert box["width"] >= 44 and box["height"] >= 44, (selector, box)
                assert owns, selector
        columns = page.evaluate(
            "() => getComputedStyle(document.querySelector('.look-pick__grid'))"
            ".gridTemplateColumns.split(' ').length")
        assert columns == (2 if viewport["width"] < 700 else 4)
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("label,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_tapping_a_look_raises_the_bar_naming_look_and_save_persists_it(
        new_context, make_app_server, label, viewport, lang):
    """one tap on a look card raises the save bar naming the Look section, Save stores that
    look and the reloaded page shows it checked"""
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), viewport, lang=lang)
    try:
        look_word = "Look" if lang == "en" else "Allure"
        card = page.locator('.look-pick__card:has(input[value="%s"])' % CHANGED_LOOK)
        card.evaluate("el => el.scrollIntoView({block: 'center'})")
        card.click()
        _wait_for_bar(page)
        page.wait_for_function(
            "w => document.querySelector('[data-dirty-count]').textContent.startsWith(w)",
            arg=look_word, timeout=5000)
        assert _bar_text(page).startswith(look_word)
        _save_via_bar(page, timeout=30000)
        assert device_config.load_device_config(server.state_dir)["theme"] == CHANGED_LOOK
        page.wait_for_function(_SETTLED, timeout=15000)
        assert page.is_checked('.look-pick__card input[value="%s"]' % CHANGED_LOOK)
        assert not page.is_checked('.look-pick__card input[value="%s"]' % SAVED_LOOK)
    finally:
        context.close()


@pytest.mark.parametrize("label,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_the_on_this_page_links_move_to_their_cards(
        new_context, make_app_server, label, viewport):
    """each On this page link lands its card in the viewport and puts the hash in the address"""
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), viewport)
    try:
        for slug in CARD_IDS:
            link = page.locator('.personalisation__link[href="#personalisation-%s"]' % slug)
            link.evaluate("el => el.scrollIntoView({block: 'center'})")
            link.click()
            page.wait_for_function(
                "slug => { const c = document.getElementById('personalisation-' + slug);"
                " const r = c.getBoundingClientRect();"
                " return location.hash === '#personalisation-' + slug"
                " && r.top < window.innerHeight && r.bottom > 0; }",
                arg=slug, timeout=10000)
    finally:
        context.close()


@pytest.mark.parametrize("label,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_customise_look_opens_the_sheet_and_escape_returns_focus(
        new_context, make_app_server, label, viewport):
    """the Customise look button opens the look sheet for the departures look, the sheet's
    choices follow the saved look, Escape closes it and focus returns to the button"""
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), viewport)
    try:
        page.focus("button.look-pick__customise")
        page.keyboard.press("Enter")
        sheet = page.locator("[data-look-sheet]")
        sheet.wait_for(state="visible")
        page.wait_for_function(
            "() => document.querySelector('[data-look-sheet]').contains(document.activeElement)",
            timeout=5000)
        for axis, value in (("colour", "red"), ("background", "soft"), ("stripe", "solid")):
            assert page.is_checked(
                '[data-look-sheet] input[data-look-axis="%s"][value="%s"]' % (axis, value))
        page.keyboard.press("Escape")
        sheet.wait_for(state="hidden")
        page.wait_for_function(
            "() => document.activeElement === document.querySelector('button.look-pick__customise')",
            timeout=5000)
    finally:
        context.close()


def test_a_look_chosen_in_the_sheet_checks_the_matching_card(new_context, make_app_server):
    """choosing Blue in the sheet checks the card of that look, so the card grid and the
    sheet are one control"""
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), VIEWPORT_DESKTOP)
    try:
        page.click("button.look-pick__customise")
        page.locator("[data-look-sheet]").wait_for(state="visible")
        page.click("[data-look-sheet] .look-dot:has(input[data-look-axis=\"colour\"][value=\"blue\"])")
        page.wait_for_function(
            "() => document.querySelector('.look-pick__card input:checked').value"
            " === 'band_blue_field'", timeout=5000)
        _wait_for_bar(page)
    finally:
        context.close()
