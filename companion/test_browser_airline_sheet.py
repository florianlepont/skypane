#!/usr/bin/env python3
"""Real-browser checks of the airline sheet the pencil on an Airlines tile opens: it opens from
the pencil at 390 and 1280 px in both languages and both themes with usable (>= 44 px, 16 px)
controls and no overflow, it also opens from a type slide's pencil, renaming and resetting
round-trip through the real routes, and with scripts blocked the pencil is a link to an in-page
sheet that does the same.
"""
import pytest

from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_PHONE, _assert_hit_target, _in_both_themes, _login, _no_js_page,
)

pytestmark = pytest.mark.browser

DIALOG = "#panel-lookup-dialog"
SHEET = DIALOG + " .airline-sheet"
NAME_INPUT = SHEET + ' input[name="airline_name"]'
FRANCE_PENCIL = '.airline-card__edit[data-view-panel-sheet-key="air-france"]'


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(fake_providers=True)


def _open_airlines(new_context, server, viewport, lang="en"):
    context = new_context(viewport=viewport)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/airlines")
    page.locator(FRANCE_PENCIL).wait_for(state="visible")
    return context, page


def _chips(page):
    return page.locator(SHEET + " .airline-sheet__chips li").all_text_contents()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_DESKTOP], ids=["390", "1280"])
def test_the_pencil_opens_a_usable_sheet_in_both_themes(new_context, server, viewport, lang):
    """the pencil opens the dialog with the name pre-filled, the built-in prefix as a chip, no
    reset offered, 16 px text in the field, 44 px controls, the dialog inside the viewport and
    nothing overflowing - in light and dark"""
    context, page = _open_airlines(new_context, server, viewport, lang)
    try:
        page.locator(FRANCE_PENCIL).click()
        page.locator(DIALOG + "[open]").wait_for()
        assert page.locator(NAME_INPUT).input_value() == "Air France"
        assert _chips(page) == ["AFR"]
        assert page.locator(SHEET + " .airline-sheet__reset").is_hidden()
        assert page.locator(SHEET).is_visible()
        assert page.locator(DIALOG + " .lightbox__replace").is_visible()
        for theme in _in_both_themes(page):
            font_px = page.locator(NAME_INPUT).evaluate("e => parseFloat(getComputedStyle(e).fontSize)")
            assert font_px >= 16, (theme, font_px)
            for selector in (NAME_INPUT, SHEET + " .airline-sheet__name button",
                             DIALOG + " [data-view-panel-close]"):
                _assert_hit_target(page, selector, "airline sheet (%s, %s)" % (lang, theme["theme"]))
            box = page.locator(DIALOG).bounding_box()
            assert box["x"] >= 0 and box["x"] + box["width"] <= viewport["width"], box
            overflow = page.locator(DIALOG).evaluate("e => e.scrollWidth - e.clientWidth")
            assert overflow <= 0, overflow
        english = "Airline name" in page.locator(SHEET).inner_text()
        assert english == (lang == "en")
    finally:
        context.close()


def test_a_type_slide_pencil_opens_the_same_airline_sheet(new_context, server):
    """the pencil of an aircraft-type slide opens the sheet for its airline, with every prefix"""
    context, page = _open_airlines(new_context, server, VIEWPORT_PHONE)
    try:
        page.locator('.airline-card__edit[data-view-panel-sheet-key="transavia-france-a320"]').evaluate(
            "e => e.click()")
        page.locator(DIALOG + "[open]").wait_for()
        assert page.locator(NAME_INPUT).input_value() == "Transavia France"
        assert _chips(page) == ["TFV", "TVF"]
    finally:
        context.close()


def test_the_sheet_url_opens_the_dialog_and_hides_the_page_copy(new_context, server):
    """/airlines?sheet=air-france opens the dialog on load; the no-script copy is hidden then"""
    context, page = _open_airlines(new_context, server, VIEWPORT_PHONE)
    try:
        page.goto(server.base_url() + "/airlines?sheet=air-france")
        page.locator(DIALOG + "[open]").wait_for()
        assert page.locator("[data-sheet-fallback]").is_hidden()
        assert page.locator(NAME_INPUT).input_value() == "Air France"
    finally:
        context.close()


def test_rename_and_reset_round_trip_through_the_sheet(new_context, make_app_server):
    """saving a new name renames the tile with a Renamed badge and a confirmation toast; the
    sheet then offers the reset, which restores the built-in name"""
    server = make_app_server(fake_providers=True)
    context, page = _open_airlines(new_context, server, VIEWPORT_PHONE)
    try:
        page.locator(FRANCE_PENCIL).click()
        page.locator(DIALOG + "[open]").wait_for()
        page.fill(NAME_INPUT, "Skyline Air")
        page.click(SHEET + " .airline-sheet__name button")
        page.wait_for_url("**/airlines?flash=airline_renamed")
        assert page.locator(".toast").first.is_visible()
        tile = page.locator(".airline-card", has=page.locator('.airline-card__name:text-is("Skyline Air")'))
        assert tile.locator(".airline-card__chip", has_text="Renamed").count() == 1
        tile.locator(".airline-card__edit").first.click()
        page.locator(DIALOG + "[open]").wait_for()
        assert page.locator(NAME_INPUT).input_value() == "Skyline Air"
        assert _chips(page) == ["AFR"]
        assert page.locator(SHEET + " .airline-sheet__reset").is_visible()
        assert "Air France" in page.locator(SHEET + " .airline-sheet__reset p").inner_text()
        page.click(SHEET + " .airline-sheet__reset button")
        page.wait_for_url("**/airlines?flash=airline_rename_reset")
        assert page.locator('.airline-card__name:text-is("Air France")').count() == 1
        assert page.locator('.airline-card__name:text-is("Skyline Air")').count() == 0
    finally:
        context.close()


def test_a_refused_name_reopens_the_sheet_with_the_error(new_context, make_app_server):
    """an over-long name is refused by the server, the sheet reopens on the same airline and
    the error toast shows"""
    server = make_app_server(fake_providers=True)
    context, page = _open_airlines(new_context, server, VIEWPORT_PHONE)
    try:
        page.locator(FRANCE_PENCIL).click()
        page.locator(DIALOG + "[open]").wait_for()
        page.evaluate("() => document.querySelector('%s').removeAttribute('maxlength')" % NAME_INPUT)
        page.fill(NAME_INPUT, "x" * 101)
        page.click(SHEET + " .airline-sheet__name button")
        page.wait_for_url("**sheet=air-france**")
        page.locator(DIALOG + "[open]").wait_for()
        assert page.locator(".toast").first.is_visible()
        assert page.locator(NAME_INPUT).input_value() == "Air France"
    finally:
        context.close()


def test_without_scripts_the_pencil_is_a_link_to_an_in_page_sheet(new_context, make_app_server):
    """with scripts blocked the pencil navigates to ?sheet=, the page shows the sheet in place
    with the same fields, saving redirects back with the confirmation and the tile is renamed"""
    server = make_app_server(fake_providers=True)
    with _no_js_page(new_context, server.base_url(), "/airlines", viewport=VIEWPORT_PHONE) as page:
        page.locator(FRANCE_PENCIL).click()
        page.wait_for_url("**/airlines?sheet=air-france#airline-sheet")
        fallback = page.locator("[data-sheet-fallback]")
        assert fallback.is_visible()
        assert fallback.locator('input[name="airline_name"]').input_value() == "Air France"
        assert fallback.locator(".airline-sheet__chips li").all_text_contents() == ["AFR"]
        assert fallback.locator("form.airline-sheet__reset").count() == 0
        assert fallback.locator('form[action="/illustration/air-france.png"]').count() == 1
        fallback.locator('input[name="airline_name"]').fill("Skyline Air")
        fallback.locator(".airline-sheet__name button").click()
        page.wait_for_url("**/airlines?flash=airline_renamed")
        assert page.locator('.airline-card__name:text-is("Skyline Air")').count() == 1
        page.locator('.airline-card__edit[data-view-panel-sheet-key="skyline-air"]').click()
        page.wait_for_url("**sheet=skyline-air**")
        page.locator("[data-sheet-fallback] form.airline-sheet__reset button").evaluate("e => e.click()")
        page.wait_for_url("**/airlines?flash=airline_rename_reset")
        assert page.locator('.airline-card__name:text-is("Air France")').count() == 1
