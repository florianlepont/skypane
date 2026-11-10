"""Real-browser checks of the frame-level Layout card above the Personalisation
tabs and of the pairing picker, in English and French: the card is on every
view and is not a navigation link; picking layout C raises the save bar with
the one-section message, the Layout card being the section that carries the
change, Save persists it, and after a reload the C card is the selected one.
On a wide screen the five thumbnails are in a row; on a phone one summary row
with a "Change" button reveals the same radios, and the page does not scroll
sideways at 360 and 390 px. A frame on a giant layout shows the five pairing
cards and a picked pairing survives a save and a reload."""
import pytest

from companion import auth, layout
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP,
    VIEWPORT_MIN_SUPPORTED,
    VIEWPORT_PHONE,
    _assert_no_page_overflow,
    _bar_text,
    _login,
    _no_js_page,
    _save_via_bar,
    _wait_for_bar,
    seed_state_dir,
)
from server import device_config

pytestmark = pytest.mark.browser

LAYOUT_SECTION = {"en": "Layout", "fr": "Disposition"}
UNSAVED = {"en": "Unsaved changes", "fr": "Modifications non enregistrées"}
CHANGE_LABEL = {"en": "Change", "fr": "Modifier"}
CHECKED_LAYOUT = "#personalisation-layout input[name=layout]:checked"
CHECKED_THEME = "#personalisation-look input[name=theme]:checked"
CARD_ROUTES = (
    layout.DISPLAY_ROUTE, layout.DISPLAY_ARRIVALS_ROUTE, layout.DISPLAY_SPECIAL_LOOKS_ROUTE,
    layout.DISPLAY_CALENDAR_ROUTE)
VIEWPORT_TABLET_EDGE = {"width": 700, "height": 900}
VIEWPORTS = (
    ("desktop", VIEWPORT_DESKTOP), ("phone-390", VIEWPORT_PHONE),
    ("phone-360", VIEWPORT_MIN_SUPPORTED))


def _seed_classic(state_dir):
    seed_state_dir(state_dir)
    device_config.save_device_config(state_dir, layout="classic")


def _seed_giant(state_dir):
    seed_state_dir(state_dir)
    device_config.save_device_config(state_dir, layout="b", theme="grey")


def _open(new_context, base_url, route, lang, viewport=VIEWPORT_DESKTOP):
    context = new_context(viewport=viewport)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
    page = context.new_page()
    _login(page, base_url)
    page.goto(base_url + route)
    page.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
    page.locator("#personalisation-layout [data-layout-toggle]").wait_for(state="attached")
    return context, page


def _pick_layout_c(page, phone):
    """Click the C thumbnail; on a phone open the picker with Change first."""
    if phone:
        toggle = page.locator("#personalisation-layout [data-layout-toggle]")
        assert toggle.get_attribute("aria-expanded") == "false"
        toggle.click()
        assert toggle.get_attribute("aria-expanded") == "true"
    page.locator('#personalisation-layout label:has(input[value="c"])').click()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("name,viewport", VIEWPORTS[:2], ids=["desktop", "phone"])
def test_picking_layout_c_saves_and_is_selected_after_a_reload(
        new_context, make_app_server, lang, name, viewport):
    """clicking the C card (on a phone after Change) raises the bar with the one-section message
    from the Layout card's own wrapper, Save persists C, and the reloaded view has exactly the C
    radio checked and the frame's stored layout is c"""
    server = make_app_server(seed=_seed_classic)
    context, page = _open(new_context, server.base_url(), layout.DISPLAY_ROUTE, lang, viewport)
    try:
        assert page.locator(CHECKED_LAYOUT).get_attribute("value") == "classic"
        _pick_layout_c(page, phone=name.startswith("phone"))
        _wait_for_bar(page)
        assert _bar_text(page) == UNSAVED[lang]
        assert page.locator("#personalisation-layout").get_attribute(
            "data-dirty-section") == LAYOUT_SECTION[lang]
        _save_via_bar(page)
        page.reload()
        page.wait_for_selector(CHECKED_LAYOUT, state="attached")
        assert page.locator(CHECKED_LAYOUT).get_attribute("value") == "c"
        assert page.locator("#personalisation-layout input[name=layout]:checked").count() == 1
        assert device_config.load_device_config(server.state_dir)["layout"] == "c"
    finally:
        context.close()


@pytest.mark.parametrize("route", CARD_ROUTES)
def test_the_card_is_above_the_tabs_on_every_view_and_the_tabs_are_four(
        new_context, make_app_server, route):
    """the Layout card is one section above the navigation whichever tab is open, and the navigation has
    exactly Departures, Arrivals, Special looks and Calendar"""
    server = make_app_server(seed=_seed_classic)
    context, page = _open(new_context, server.base_url(), route, "en")
    try:
        assert page.locator("#personalisation-layout").count() == 1
        assert page.locator("#personalisation-layout input[name=layout]").count() == 5
        links = page.locator(".personalisation-nav__link")
        assert [links.nth(i).inner_text().strip() for i in range(links.count())] == [
            "Departures", "Arrivals", "Special looks", "Calendar"]
        card_bottom = page.locator("#personalisation-layout").bounding_box()
        nav_top = page.locator(".personalisation-nav").bounding_box()
        assert card_bottom["y"] + card_bottom["height"] <= nav_top["y"] + 0.5
    finally:
        context.close()


def test_on_a_wide_screen_the_five_thumbnails_are_one_row_of_about_92_by_122(
        new_context, make_app_server):
    """at desktop width the five previews sit on one line, each about 92 x 122 px, the summary row and
    Change button are not shown, and the checked one is bold"""
    server = make_app_server(seed=_seed_classic)
    context, page = _open(new_context, server.base_url(), layout.DISPLAY_ROUTE, "en")
    try:
        previews = page.locator("#personalisation-layout .look-pick__preview")
        boxes = [previews.nth(i).bounding_box() for i in range(5)]
        centres = [b["y"] + b["height"] / 2 for b in boxes]
        assert max(centres) - min(centres) <= 1, boxes
        for box in boxes:
            # The checked card is drawn 2% larger.
            assert abs(box["width"] - 92) <= 2.5 and abs(box["height"] - 122.7) <= 4, box
        assert not page.locator("#personalisation-layout [data-layout-toggle]").is_visible()
        assert not page.locator("#personalisation-layout [data-layout-thumb]").is_visible()
        weight = page.evaluate(
            "() => getComputedStyle(document.querySelector("
            "'#personalisation-layout label:has(input:checked) .look-pick__name')).fontWeight")
        assert int(weight) >= 700
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_on_a_phone_the_card_is_a_summary_row_that_opens_the_same_radios(
        new_context, make_app_server, lang):
    """below the tablet breakpoint the card shows a 44 x 58 thumbnail, the title, the layout name and
    a Change button of at least 44 px; the five radios are hidden until Change is pressed, and picking
    one updates the summary name and picture"""
    server = make_app_server(seed=_seed_classic)
    context, page = _open(
        new_context, server.base_url(), layout.DISPLAY_ROUTE, lang, VIEWPORT_PHONE)
    try:
        toggle = page.locator("#personalisation-layout [data-layout-toggle]")
        assert toggle.is_visible() and toggle.inner_text().strip() == CHANGE_LABEL[lang]
        box = toggle.bounding_box()
        assert box["width"] >= 44 - 0.5 and box["height"] >= 44 - 0.5, box
        thumb = page.locator("#personalisation-layout [data-layout-thumb]").bounding_box()
        assert abs(thumb["width"] - 44) <= 1 and abs(thumb["height"] - 58) <= 1, thumb
        assert page.locator("#personalisation-layout h2").inner_text().strip() == (
            LAYOUT_SECTION[lang])
        assert not page.locator("#personalisation-layout .look-pick__preview").first.is_visible()
        before = page.locator("#personalisation-layout [data-layout-name]").inner_text()
        toggle.click()
        page.locator("#personalisation-layout .look-pick__preview").first.wait_for(state="visible")
        assert page.locator("#personalisation-layout .look-pick__preview:visible").count() == 5
        page.locator('#personalisation-layout label:has(input[value="b"])').click()
        after = page.locator("#personalisation-layout [data-layout-name]").inner_text()
        assert after != before
        assert "layout=b" in page.locator(
            "#personalisation-layout [data-layout-thumb]").get_attribute("src")
        toggle.click()
        assert toggle.get_attribute("aria-expanded") == "false"
        assert not page.locator("#personalisation-layout .look-pick__preview").first.is_visible()
    finally:
        context.close()


@pytest.mark.parametrize("name,viewport", VIEWPORTS[1:], ids=["390", "360"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("route", CARD_ROUTES)
def test_the_phone_layout_card_does_not_scroll_sideways_closed_or_open(
        new_context, make_app_server, route, lang, name, viewport):
    """at 360 and 390 px the page has no horizontal overflow with the card closed and with the picker open"""
    server = make_app_server(seed=_seed_classic)
    context, page = _open(new_context, server.base_url(), route, lang, viewport)
    try:
        assert not _assert_no_page_overflow(page, "layout-card", viewport["width"])
        page.locator("#personalisation-layout [data-layout-toggle]").click()
        page.locator("#personalisation-layout .look-pick__preview").first.wait_for(state="visible")
        assert not _assert_no_page_overflow(page, "layout-card-open", viewport["width"])
        card = page.locator("#personalisation-layout").bounding_box()
        assert card["x"] >= -0.5 and card["x"] + card["width"] <= viewport["width"] + 0.5, card
    finally:
        context.close()


def test_without_scripts_the_phone_picker_is_open_and_saves(new_context, make_app_server):
    """with scripts blocked on a phone the Change button is absent, the five radios are shown, and
    choosing C then pressing the page's Save stores it"""
    server = make_app_server(seed=_seed_classic)
    with _no_js_page(new_context, server.base_url(), layout.DISPLAY_ROUTE,
                     viewport=VIEWPORT_PHONE) as page:
        assert not page.locator("#personalisation-layout [data-layout-toggle]").is_visible()
        assert page.locator("#personalisation-layout .look-pick__preview:visible").count() == 5
        page.locator('#personalisation-layout label:has(input[value="c"])').click()
        page.locator("button.dirty-bar__save").click()
        page.wait_for_load_state("load")
    assert device_config.load_device_config(server.state_dir)["layout"] == "c"


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_a_giant_layout_frame_picks_a_pairing_and_keeps_it_after_a_reload(
        new_context, make_app_server, lang):
    """on a frame whose layout is B the Departures view offers five pairing radios, the stored
    grey one is checked, picking light red then saving stores red_light and the reload checks it"""
    server = make_app_server(seed=_seed_giant)
    context, page = _open(new_context, server.base_url(), layout.DISPLAY_ROUTE, lang)
    try:
        radios = page.locator("#personalisation-look input[name=theme]")
        assert radios.count() == 5
        assert page.locator(CHECKED_THEME).get_attribute("value") == "grey"
        page.locator('#personalisation-look label:has(input[value="red_light"])').click()
        _wait_for_bar(page)
        _save_via_bar(page)
        page.reload()
        page.wait_for_selector(CHECKED_THEME, state="attached")
        assert page.locator(CHECKED_THEME).get_attribute("value") == "red_light"
        assert device_config.load_device_config(server.state_dir)["theme"] == "red_light"
    finally:
        context.close()
