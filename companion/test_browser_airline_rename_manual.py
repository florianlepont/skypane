"""Real-browser checks of Rename on an airline the owner named by hand: the menu item and the
dialog in the missing-illustrations section and in the table, at phone and desktop sizes, English
and French, light and dark; 44 px hit areas, no horizontal overflow, a 100-character name
fits; submitting renames the row and flashes; Escape and Cancel close without a request."""
import os
import shutil

import pytest

from companion import auth
from companion.test_browser_ux_helpers import _assert_no_page_overflow, _login, seed_state_dir
from server.plane import illustrations, manual_resolutions

pytestmark = pytest.mark.browser

_PNG = os.path.join(illustrations.ILLUSTRATION_DIR, "vueling-airlines.png")
KNOWN = ".airlines-missing__airline"
TABLE_ROWS = "tbody.airline-group:not(.airline-group--gap)"
SIZES = ((390, 844), (1440, 900))
RENAME = {"en": "Rename", "fr": "Renommer"}
SAVE = {"en": "Save", "fr": "Enregistrer"}
CANCEL = {"en": "Cancel", "fr": "Annuler"}
HINT = {
    "en": "The new name applies to every frame. Flights already stored keep their name.",
    "fr": "Le nouveau nom s’applique à tous les cadres. "
          "Les vols déjà enregistrés gardent leur nom.",
}
FLASH = {"en": "Airline name saved", "fr": "Nom de compagnie enregistré"}
LONG_NAME = "Z" + "a" * 99
_SETTLED = "() => document.readyState === 'complete'"


def _seed(state_dir):
    seed_state_dir(state_dir)
    manual_resolutions.add_entry(state_dir, "ZPH", "Zephyr Air")
    manual_resolutions.add_entry(state_dir, "OCN", "Oceanic Air")
    path = illustrations.override_path_for_key("oceanic-air", state_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    shutil.copy(_PNG, path)


def _open(new_context, server, size, lang, theme):
    context = new_context(viewport={"width": size[0], "height": size[1]}, color_scheme=theme)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/airlines/manage")
    page.wait_for_function(_SETTLED, timeout=15000)
    page.wait_for_timeout(500)
    return context, page


def _row(page, where):
    return page.locator(KNOWN if where == "known" else TABLE_ROWS, has_text="Zephyr Air" if where == "known" else "Oceanic Air")


def _open_dialog(page, where, lang):
    row = _row(page, where)
    row.locator(".row-menu__toggle").click()
    item = row.locator("a.row-menu__item", has_text=RENAME[lang])
    assert item.count() == 1
    box = item.bounding_box()
    assert box["height"] >= 44 - 1
    item.click()
    dialog = page.locator("dialog[open]")
    dialog.wait_for(state="visible")
    return dialog


@pytest.mark.parametrize("where", ("known", "table"))
@pytest.mark.parametrize("lang,theme", (("en", "light"), ("fr", "dark")))
@pytest.mark.parametrize("size", SIZES)
def test_the_menu_lists_rename_first_and_the_dialog_fits(new_context, make_app_server, size, lang, theme, where):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, size, lang, theme)
    try:
        row = _row(page, where)
        row.locator(".row-menu__toggle").click()
        items = row.locator(".row-menu__panel .row-menu__item").all_inner_texts()
        assert items[0] == RENAME[lang] and len(items) >= 2
        row.locator(".row-menu__toggle").click()
        dialog = _open_dialog(page, where, lang)
        assert dialog.locator(".modal__subtitle").inner_text() == HINT[lang]
        field = dialog.locator("input[name=airline_name]")
        assert field.input_value() == ("Zephyr Air" if where == "known" else "Oceanic Air")
        field.fill(LONG_NAME)
        assert field.input_value() == LONG_NAME
        for button in (dialog.locator("button[type=submit]"), dialog.locator("[data-modal-close]").last):
            box = button.bounding_box()
            assert box["height"] >= 43
        _assert_no_page_overflow(page, "rename dialog")
    finally:
        context.close()


@pytest.mark.parametrize("where,old,new", (("known", "Zephyr Air", "Zephyr Airways"), ("table", "Oceanic Air", "Oceanic Airways")))
def test_submitting_renames_the_row_and_flashes(new_context, make_app_server, where, old, new):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, (1440, 900), "en", "light")
    try:
        dialog = _open_dialog(page, where, "en")
        dialog.locator("input[name=airline_name]").fill(new)
        with page.expect_navigation():
            dialog.locator("button[type=submit]").click()
        page.locator(".toast").first.wait_for(state="visible")
        assert FLASH["en"] in page.locator(".toast").first.inner_text()
        assert page.locator("tbody, .airlines-missing__airline", has_text=new).count() >= 1
        assert page.locator("tbody, .airlines-missing__airline", has_text=old + "<").count() == 0
    finally:
        context.close()


@pytest.mark.parametrize("how", ("escape", "cancel"))
def test_escape_and_cancel_close_without_a_request(new_context, make_app_server, how):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, (390, 844), "en", "light")
    posts = []
    page.on("request", lambda request: posts.append(request.url) if request.method == "POST" else None)
    try:
        dialog = _open_dialog(page, "known", "en")
        if how == "escape":
            page.keyboard.press("Escape")
        else:
            dialog.locator("[data-modal-close]", has_text=CANCEL["en"]).click()
        page.locator("dialog[open]").wait_for(state="detached")
        assert posts == []
        assert "Zephyr Air" in page.locator(KNOWN + " .airlines-missing__name").all_inner_texts()
    finally:
        context.close()
