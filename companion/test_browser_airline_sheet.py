#!/usr/bin/env python3
"""Real-browser checks of the airline sheet an Airlines row opens: it opens from the row at 390
and 1280 px in both languages and both themes with one title, usable (>= 44 px, 16 px) controls
and no overflow, it switches between an airline's aircraft types in place, renaming and resetting
round-trip through the real routes, and with scripts blocked the row is a link to an in-page
sheet that does the same.
"""
import pytest

from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_PHONE, _assert_hit_target, _in_both_themes, _login, _no_js_page,
)

pytestmark = pytest.mark.browser

FOCUSED = "() => { var e = document.activeElement; return e.id || e.className || e.tagName; }"

DIALOG = "#panel-lookup-dialog"
SHEET = DIALOG + " .airline-sheet"
NAME_INPUT = SHEET + ' input[name="airline_name"]'
SAVE_NAME_IN_PAGE = "[data-sheet-fallback] .airline-sheet__name button"
FRANCE_PENCIL = '.airline-row[data-view-panel-sheet-key="air-france"]'


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


def _click_centred(page, selector):
    """Click `selector` after centring it in the viewport, so the fixed bottom tab bar (phone
    widths) can never sit over the target while the click's own scroll-into-view retries."""
    target = page.locator(selector).first
    target.wait_for(state="visible")
    target.evaluate("el => el.scrollIntoView({block: 'center'})")
    target.click()


def _open_in_page_sheet(page):
    """Scripts blocked: follow the France pencil to the in-page sheet and let the page settle."""
    _click_centred(page, FRANCE_PENCIL)
    page.wait_for_url("**/airlines?sheet=air-france#airline-sheet")
    page.wait_for_load_state("load")


def _chips(page):
    return page.locator(DIALOG + " .airline-sheet__chips li").all_text_contents()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_DESKTOP], ids=["390", "1280"])
def test_the_row_opens_a_usable_sheet_in_both_themes(new_context, server, viewport, lang):
    """the row opens the dialog with one title (the airline's name, no "Edit" line, no caption
    repeating it), the name pre-filled, the built-in prefix as a chip beside the title, no
    reset offered, 16 px text in the field, 44 px controls, the dialog inside the viewport and
    nothing overflowing - in light and dark"""
    context, page = _open_airlines(new_context, server, viewport, lang)
    try:
        page.locator(FRANCE_PENCIL).click()
        page.locator(DIALOG + "[open]").wait_for()
        assert page.locator(NAME_INPUT).input_value() == "Air France"
        assert _chips(page) == ["AFR"]
        assert page.locator(DIALOG + " .lightbox__heading").inner_text() == "Air France"
        assert page.locator(DIALOG + " .lightbox__caption").is_hidden()
        text = page.locator(DIALOG).inner_text()
        for gone in ("Modifier", "Edit Air France", "Shown on every", "Affiché sur tous",
                     "Illustration remplacée", "Replaced"):
            assert gone not in text, gone
        assert text.count("Air France") == 1, text
        assert page.locator(DIALOG + " .airline-sheet__types").is_visible()
        assert page.locator(DIALOG + " .airline-sheet__type").all_text_contents() == ["A320"]
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


def test_the_type_switcher_retargets_picture_and_upload_in_place(new_context, server):
    """a two-type airline's sheet offers one tab per type (B737 shown first, A320 second); a tab
    swaps the picture and the upload address to that type, keeps the title, the prefixes and the
    name, marks the shown tab, keeps keyboard focus on it and clears a file chosen for the
    previous type"""
    context, page = _open_airlines(new_context, server, VIEWPORT_PHONE)
    try:
        page.locator('.airline-row[data-view-panel-sheet-key="transavia-france"]').click()
        page.locator(DIALOG + "[open]").wait_for()
        tabs = page.locator(DIALOG + " a.airline-sheet__type")
        assert tabs.all_text_contents() == ["B737", "A320"]
        assert tabs.nth(0).get_attribute("aria-current") == "true"
        assert page.locator(DIALOG + " .lightbox__image").get_attribute("src").startswith(
            "/illustration/transavia-france.png")
        assert page.locator(DIALOG + " .lightbox__replace").get_attribute("action") == (
            "/illustration/transavia-france.png")
        page.set_input_files(DIALOG + " .lightbox__replace input[type=file]", {
            "name": "x.png", "mimeType": "image/png", "buffer": b"x"})
        tabs.nth(1).click()
        assert page.locator(DIALOG + " .airline-sheet__type[aria-current]").inner_text() == "A320"
        assert page.locator(DIALOG + " .lightbox__image").get_attribute("src").startswith(
            "/illustration/transavia-france-a320.png")
        assert page.locator(DIALOG + " .lightbox__replace").get_attribute("action") == (
            "/illustration/transavia-france-a320.png")
        assert page.locator(DIALOG + " .lightbox__replace input[type=file]").evaluate(
            "e => e.files.length") == 0
        assert page.locator(DIALOG + " .lightbox__heading").inner_text() == "Transavia France"
        assert _chips(page) == ["TFV", "TVF"]
        assert page.locator(NAME_INPUT).input_value() == "Transavia France"
        assert page.evaluate("() => document.activeElement.textContent") == "A320"
        assert page.locator(DIALOG + "[open]").count() == 1
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
        tile = page.locator(".airline-list__item", has=page.locator('.airline-row__name:text-is("Skyline Air")'))
        assert tile.locator(".airline-card__chip").count() == 0, "a rename shows no chip on the row"
        tile.locator(".airline-row").first.click()
        page.locator(DIALOG + "[open]").wait_for()
        assert page.locator(NAME_INPUT).input_value() == "Skyline Air"
        assert _chips(page) == ["AFR"]
        assert page.locator(SHEET + " .airline-sheet__reset").is_visible()
        assert "Air France" in page.locator(SHEET + " .airline-sheet__reset p").inner_text()
        page.click(SHEET + " .airline-sheet__reset button")
        page.wait_for_url("**/airlines?flash=airline_rename_reset")
        assert page.locator('.airline-row__name:text-is("Air France")').count() == 1
        assert page.locator('.airline-row__name:text-is("Skyline Air")').count() == 0
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
        assert page.evaluate(FOCUSED) == "airline-sheet-name-dialog"
    finally:
        context.close()


def test_without_scripts_the_row_is_a_link_to_an_in_page_sheet(new_context, make_app_server):
    """with scripts blocked the row navigates to ?sheet=, the page shows the sheet in place
    with the same fields (title, prefixes, picture, type, upload, name), saving redirects back
    with the confirmation and the row is renamed"""
    server = make_app_server(fake_providers=True)
    with _no_js_page(new_context, server.base_url(), "/airlines", viewport=VIEWPORT_PHONE, reduced_motion="reduce") as page:
        _open_in_page_sheet(page)
        fallback = page.locator("[data-sheet-fallback]")
        assert fallback.is_visible()
        assert fallback.locator('input[name="airline_name"]').input_value() == "Air France"
        assert fallback.locator(".airline-sheet__chips li").all_text_contents() == ["AFR"]
        assert fallback.locator("h2").all_text_contents() == ["Air France"]
        assert fallback.locator(".airline-sheet__type").all_text_contents() == ["A320"]
        assert fallback.locator("img.lightbox__image").get_attribute("src").startswith(
            "/illustration/air-france.png")
        assert fallback.locator("form.airline-sheet__reset").count() == 0
        assert fallback.locator('form[action="/illustration/air-france.png"]').count() == 1
        fallback.locator('input[name="airline_name"]').fill("Skyline Air")
        _click_centred(page, SAVE_NAME_IN_PAGE)
        page.wait_for_url("**/airlines?flash=airline_renamed")
        assert page.locator('.airline-row__name:text-is("Skyline Air")').count() == 1
        _click_centred(page, '.airline-row[data-view-panel-sheet-key="skyline-air"]')
        page.wait_for_url("**sheet=skyline-air**")
        _click_centred(page, "[data-sheet-fallback] form.airline-sheet__reset button")
        page.wait_for_url("**/airlines?flash=airline_rename_reset")
        assert page.locator('.airline-row__name:text-is("Air France")').count() == 1


def test_without_scripts_the_type_links_switch_the_in_page_sheet(new_context, make_app_server):
    """with scripts blocked a multi-type airline's in-page sheet offers one real link per type;
    following one shows that type's picture and upload address, marked as the shown type"""
    server = make_app_server(fake_providers=True)
    with _no_js_page(new_context, server.base_url(), "/airlines?sheet=transavia-france#airline-sheet",
                     viewport=VIEWPORT_PHONE, reduced_motion="reduce") as page:
        fallback = page.locator("[data-sheet-fallback]")
        assert fallback.locator("a.airline-sheet__type").all_text_contents() == ["B737", "A320"]
        _click_centred(page, '[data-sheet-fallback] a.airline-sheet__type:text-is("A320")')
        page.wait_for_url("**/airlines?sheet=transavia-france-a320#airline-sheet")
        page.wait_for_load_state("load")
        assert fallback.locator('a.airline-sheet__type[aria-current="true"]').inner_text() == "A320"
        assert fallback.locator("img.lightbox__image").get_attribute("src").startswith(
            "/illustration/transavia-france-a320.png")
        assert fallback.locator('form[action="/illustration/transavia-france-a320.png"]').count() == 1


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_DESKTOP], ids=["390", "1280"])
def test_opening_the_sheet_leaves_focus_off_the_name_field(new_context, server, viewport, lang):
    """opening the sheet from the row and from its URL puts focus on the
    dialog's heading, never the name field (no phone keyboard), and the first Tab then reaches a
    control inside the dialog; in light and dark"""
    context, page = _open_airlines(new_context, server, viewport, lang)
    try:
        for how in ("pencil", "url"):
            if how == "pencil":
                page.locator(FRANCE_PENCIL).click()
            else:
                page.goto(server.base_url() + "/airlines?sheet=air-france")
            page.locator(DIALOG + "[open]").wait_for()
            assert page.evaluate(FOCUSED) == "lightbox__heading", (how, page.evaluate(FOCUSED))
            assert page.locator(DIALOG + " .lightbox__heading").inner_text().strip()
            for theme in _in_both_themes(page):
                assert page.evaluate(FOCUSED) == "lightbox__heading", theme
            page.keyboard.press("Tab")
            assert page.evaluate("() => !!document.activeElement.closest('#panel-lookup-dialog')")
            assert page.evaluate(FOCUSED) != "lightbox__heading"
            page.keyboard.press("Escape")
            page.locator(DIALOG + "[open]").wait_for(state="detached")
    finally:
        context.close()


def test_a_taken_name_reopens_the_sheet_with_focus_on_the_name_field(new_context, make_app_server):
    """renaming onto another airline's name is refused with the taken toast, the sheet reopens
    on the same airline and the name field has focus so the owner can fix it"""
    server = make_app_server(fake_providers=True)
    context, page = _open_airlines(new_context, server, VIEWPORT_PHONE)
    try:
        page.locator(FRANCE_PENCIL).click()
        page.locator(DIALOG + "[open]").wait_for()
        page.fill(NAME_INPUT, "Transavia France")
        page.click(SHEET + " .airline-sheet__name button")
        page.wait_for_url("**sheet=air-france&flash=airline_rename_taken")
        page.locator(DIALOG + "[open]").wait_for()
        assert "Another airline already uses that name" in page.locator(".toast").first.inner_text()
        assert page.evaluate(FOCUSED) == "airline-sheet-name-dialog"
        assert page.locator(NAME_INPUT).input_value() == "Air France"
        assert page.locator('.airline-row__name:text-is("Air France")').count() == 1
    finally:
        context.close()


@pytest.mark.parametrize("height", [600, 700, 844])
def test_without_scripts_the_anchor_jump_leaves_save_clear_of_the_tab_bar(
        new_context, make_app_server, height):
    """following the pencil link to #airline-sheet (and landing again after a refusal) leaves
    the Save button inside the viewport and above the fixed tab bar, whatever the phone height"""
    server = make_app_server(fake_providers=True)
    viewport = {"width": VIEWPORT_PHONE["width"], "height": height}
    with _no_js_page(new_context, server.base_url(), "/airlines", viewport=viewport, reduced_motion="reduce") as page:
        page.locator(FRANCE_PENCIL).evaluate("e => e.click()")
        page.wait_for_url("**/airlines?sheet=air-france#airline-sheet")
        page.wait_for_load_state("load")
        for stage in ("pencil", "refused"):
            if stage == "refused":
                page.goto(server.base_url()
                          + "/airlines?sheet=air-france&flash=airline_rename_taken#airline-sheet")
                page.wait_for_load_state("load")
            save = page.locator(SAVE_NAME_IN_PAGE).bounding_box()
            bar = page.locator(".tab-bar").bounding_box()
            assert save["y"] >= 0, (stage, save)
            assert save["y"] + save["height"] <= bar["y"], (stage, save, bar)


def test_a_taken_name_without_scripts_focuses_the_in_page_name_field(new_context, make_app_server):
    """with scripts blocked the refusal reopens the in-page sheet with the name field focused,
    while the plain pencil link leaves it unfocused"""
    server = make_app_server(fake_providers=True)
    with _no_js_page(new_context, server.base_url(), "/airlines", viewport=VIEWPORT_PHONE, reduced_motion="reduce") as page:
        _open_in_page_sheet(page)
        field = page.locator('[data-sheet-fallback] input[name="airline_name"]')
        assert page.evaluate(FOCUSED) != "airline-sheet-name-edit"
        field.fill("Transavia France")
        _click_centred(page, SAVE_NAME_IN_PAGE)
        page.wait_for_url("**sheet=air-france&flash=airline_rename_taken")
        assert page.evaluate(FOCUSED) == "airline-sheet-name-edit"


def test_the_resolve_dialog_still_focuses_its_name_field(new_context, make_app_server):
    """the unidentified-flight dialog keeps its own name-field focus, unchanged by the sheet's"""
    from server import state_store
    server = make_app_server(
        fake_providers=True,
        seed=lambda state_dir: state_store.save_poll_state(state_dir, {"unresolved_prefixes": {
            "XYZ": {"count": 3, "first_seen": "2026-01-01T00:00:00+00:00",
                    "last_seen": "2026-01-01T00:00:00+00:00", "example_callsign": "XYZ123"}}}))
    context, page = _open_airlines(new_context, server, VIEWPORT_PHONE)
    try:
        page.locator('a.airline-card[href="/airlines?resolve=XYZ"]').click()
        page.locator(DIALOG + "[open]").wait_for()
        assert page.evaluate(FOCUSED) == "manual-airline-name-dialog"
        page.keyboard.press("Escape")
        page.locator(FRANCE_PENCIL).click()
        page.locator(DIALOG + "[open]").wait_for()
        assert page.evaluate(FOCUSED) == "lightbox__heading"
    finally:
        context.close()
