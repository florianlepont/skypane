"""Real-browser checks of the Editor's add-illustration dialog: one short title with the airline
(and the type) as its subtitle, the aircraft type fixed as a chip when the dialog is opened from
a type row and chosen first (a select) when it is opened for an airline without artwork, one
drop zone with a compact list of constraints, an action row of Cancel and Upload (Upload waits
for a picture), and the "..." menu on the same line as the row's artwork button. English and
French, at 360 and 1280 px; without a script a type row still offers the plain upload form."""
import os

import animation_settle
import pytest

from companion import auth
from companion.test_browser_airline_helpers import seed_airline_editor as _seed
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow, _login, _no_js_page)
from server.plane import illustrations

pytestmark = pytest.mark.browser

VIEWPORTS = (("360", VIEWPORT_MIN_SUPPORTED), ("1280", VIEWPORT_DESKTOP))
TRANSAVIA = "#airline-transavia-france"
A333_ROW = TRANSAVIA + " .airlines-subrow:nth-child(5)"  # the airline row, the heading, A320, B738, then A333
_PNG = os.path.join(illustrations.ILLUSTRATION_DIR, "vueling-airlines.png")
DIALOG = "#panel-lookup-dialog"
INPUT = "#manual-illustration-input-dialog"
_SETTLED = animation_settle.SETTLED
WORDS = {
    "en": {"title": "Add an illustration", "type": "Aircraft type", "cancel": "Cancel",
           "upload": "Upload", "constraints": ["Transparent PNG", "At least 1200 px wide",
                                               "Landscape"]},
    "fr": {"title": "Ajouter une illustration", "type": "Type d’avion", "cancel": "Annuler",
           "upload": "Téléverser", "constraints": ["PNG transparent", "Au moins 1200 px de large",
                                                   "Format paysage"]},
}


def _open(new_context, server, viewport, lang, path="/airlines/manage"):
    context = new_context(viewport=viewport)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + path)
    page.wait_for_function(_SETTLED, timeout=15000)
    return context, page


def _expand_transavia(page):
    chevron = TRANSAVIA + " .airlines-expand > summary"
    page.locator(chevron).wait_for(state="visible")
    page.wait_for_function(_SETTLED, timeout=15000)
    page.locator(chevron).click()
    page.locator(A333_ROW).wait_for(state="visible")


def _open_from_type_row(page):
    _expand_transavia(page)
    page.locator(A333_ROW + " .airlines-act:visible").click()
    page.locator(DIALOG).wait_for(state="visible")
    page.wait_for_function(_SETTLED, timeout=15000)


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_from_a_type_row_the_type_is_a_fixed_chip_under_a_one_line_title(
        new_context, make_app_server, name, viewport, lang):
    words = WORDS[lang]
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, viewport, lang)
    try:
        _open_from_type_row(page)
        dialog = page.locator(DIALOG)
        heading = dialog.locator(".lightbox__heading")
        assert heading.inner_text() == words["title"]
        one_line = heading.evaluate(
            "el => el.getBoundingClientRect().height < 1.8 * parseFloat(getComputedStyle(el).lineHeight)")
        assert one_line
        assert dialog.locator(".lightbox__caption").inner_text() == "Transavia France · A333"
        assert dialog.locator(".upload-type-row__label").inner_text() == words["type"]
        assert dialog.locator("[data-upload-type-chip]").inner_text() == "Airbus A330"
        assert dialog.locator("#airline_artwork_type").is_hidden()
        assert dialog.locator(".upload-constraints li").all_inner_texts() == words["constraints"]
        assert dialog.locator("[data-upload-drop]").count() >= 1
        assert not _assert_no_page_overflow(page, "add-illustration", viewport["width"])
        box = dialog.bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= viewport["width"] + 0.5, box
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_actions_are_cancel_and_upload_and_upload_waits_for_a_picture(
        new_context, make_app_server, lang):
    words = WORDS[lang]
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, VIEWPORT_DESKTOP, lang)
    try:
        _open_from_type_row(page)
        dialog = page.locator(DIALOG)
        actions = dialog.locator(".lightbox__actions button:visible")
        assert actions.all_inner_texts() == [words["cancel"], words["upload"]]
        upload = dialog.locator(".lightbox__upload")
        assert upload.is_disabled() and upload.get_attribute("aria-disabled") == "true"
        cancel, send = (b.bounding_box() for b in (actions.nth(0), actions.nth(1)))
        assert cancel["x"] < send["x"] and min(cancel["height"], send["height"]) >= 44 - 0.5
        panel = dialog.bounding_box()
        assert send["x"] + send["width"] <= panel["x"] + panel["width"] + 0.5
        # The end of the row, not its start.
        assert send["x"] + send["width"] > panel["x"] + panel["width"] * 0.8
        dialog.locator(INPUT).set_input_files(_PNG)
        page.wait_for_function(
            "() => !document.querySelector('.lightbox__upload').disabled", timeout=10000)
        assert upload.get_attribute("aria-disabled") == "false"
        actions.nth(0).click()
        dialog.wait_for(state="hidden")
        # Reopened, the chosen picture is gone and Upload waits again.
        page.locator(A333_ROW + " .airlines-act:visible").click()
        dialog.wait_for(state="visible")
        assert page.locator(DIALOG + " .lightbox__upload").is_disabled()
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_for_an_airline_without_artwork_the_type_select_comes_first(
        new_context, make_app_server, lang):
    words = WORDS[lang]
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, VIEWPORT_DESKTOP, lang)
    try:
        page.locator(".airlines-missing__add[data-view-panel-ask-type]").first.click()
        dialog = page.locator(DIALOG)
        dialog.wait_for(state="visible")
        page.wait_for_function(_SETTLED, timeout=15000)
        assert dialog.locator(".lightbox__heading").inner_text() == words["title"]
        assert dialog.locator("[data-upload-type-chip]").is_hidden()
        select = dialog.locator("#airline_artwork_type")
        assert select.is_visible() and select.bounding_box()["height"] >= 44 - 0.5
        # The type is asked before the picture.
        assert select.bounding_box()["y"] < dialog.locator(INPUT).bounding_box()["y"]
        assert dialog.locator(".upload-type-row__label").inner_text() == words["type"]
        assert dialog.locator(".lightbox__upload").is_disabled()
    finally:
        context.close()


@pytest.mark.parametrize("name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_the_row_menu_is_beside_the_artwork_button_in_a_table_and_under_it_in_a_card(
        new_context, make_app_server, name, viewport):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, viewport, "en")
    try:
        _expand_transavia(page)
        centres = page.evaluate(
            """sel => [...document.querySelectorAll(sel + ' .airlines-subrow')].map(row => {
              const button = [...row.querySelectorAll('.airlines-act')].find(e => e.offsetParent);
              const menu = row.querySelector('.row-menu__toggle');
              const mid = (e) => { const b = e.getBoundingClientRect(); return b.top + b.height / 2; };
              const centre = (e) => { const b = e.getBoundingClientRect(); return b.left + b.width / 2; };
              if (!menu || !button) { return null; }
              return {beside: Math.abs(mid(button) - mid(menu)), under: mid(menu) - mid(button),
                      aligned: Math.abs(centre(button) - centre(menu))};
            }).filter(d => d !== null)""", TRANSAVIA)
        assert centres, "no type row carries both an artwork button and a menu"
        for found in centres:
            if viewport["width"] >= 1120:
                assert found["beside"] <= 1, found
            else:
                # In a card the menu sits under the button, on its axis.
                assert found["under"] >= 40 and found["aligned"] <= 1, found
        heights = page.evaluate(
            "sel => [...document.querySelectorAll(sel + ' .airlines-act')]"
            ".filter(e => e.offsetParent).map(e => e.getBoundingClientRect().height)", TRANSAVIA)
        assert min(heights) >= 44 - 0.5 and max(heights) - min(heights) < 1, heights
    finally:
        context.close()


def test_without_a_script_a_type_row_offers_the_plain_upload_form(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    with _no_js_page(
            new_context, server.base_url(), "/airlines/manage?types=all",
            viewport=VIEWPORT_DESKTOP) as page:
        page.locator(TRANSAVIA + " .airlines-expand > summary").click()
        row = page.locator(A333_ROW)
        row.wait_for(state="visible")
        assert row.locator("button.airlines-act").is_hidden()
        label = row.locator("label.airlines-act")
        assert label.is_visible() and label.inner_text() == "Add artwork"
        assert row.locator("form.airlines-art input[type=file]").count() == 1
