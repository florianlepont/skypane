# SPDX-License-Identifier: AGPL-3.0-only
"""Real-browser checks of the Rename frame dialog from its two entry points (the
Fleet header pencil and the pencil of a frame row on Account): a centred dialog on a
desktop and a bottom sheet on a phone with the name field focused, Save and Cancel as equal
buttons, no sideways scroll at 360 and 1280px in both languages and both themes, Escape, Cancel
and a tap on the scrim closing it and discarding the typed name, Save returning to the page the
person was on with the new name, a refused name reopening the dialog with its error, the sheet
lifted over the on-screen keyboard, and the same flows through plain hash links with scripts
blocked."""
import pytest

from co_manager_browser_support import Rig, _no_sideways_scroll, _open
from companion.test_browser_ux_helpers import VIEWPORT_MIN_SUPPORTED
from server import fleet_db

pytestmark = pytest.mark.browser

DESKTOP = {"width": 1280, "height": 900}
VIEWPORTS = (VIEWPORT_MIN_SUPPORTED, DESKTOP)
VIEWPORT_IDS = ("360", "1280")
LANGS = ("en", "fr")
ENTRIES = ("fleet", "account")
TITLE = {"en": "Rename frame", "fr": "Renommer le cadre"}
CANCEL = {"en": "Cancel", "fr": "Annuler"}
ERROR = {"en": "Enter a name of 1 to 40 characters.",
         "fr": "Saisissez un nom de 1 à 40 caractères."}
RENAME_ARIA = {"en": "Rename", "fr": "Renommer"}


class RenameRig(Rig):
    def __init__(self, server):
        super().__init__(server)
        self.slug = "dlg-rename-" + self.seed.owned_id.lower().replace("_", "-")
        self.dialog = "#" + self.slug
        self.field = "#%s-name" % self.slug

    def where(self, entry):
        """(who, page path, selector of the page's own name display)."""
        return {
            "fleet": ("admin", "/fleet?frame=%s" % self.seed.owned_id, ".fleet-head__title"),
            "account": ("owner", "/account", "li.account-frame"),
        }[entry]

    def name(self):
        conn = fleet_db.connect(self.state_dir)
        try:
            return fleet_db.get_device(conn, self.seed.owned_id)["name"]
        finally:
            conn.close()


@pytest.fixture
def rig(app_server_in_process):
    return RenameRig(app_server_in_process)


def _visit(new_context, rig, entry, lang="en", viewport=DESKTOP, theme=None, **kwargs):
    who, path, _shown = rig.where(entry)
    context, page = _open(
        new_context, rig, who, path=path, lang=lang, theme=theme, viewport=viewport, **kwargs)
    page.wait_for_function("document.readyState === 'complete'")
    return context, page


def _press_opener(page, rig, entry, lang):
    """Tap the entry point's own pencil."""
    if entry == "fleet":
        page.locator(".fleet-head a.fleet-icon-button[data-modal-open]").click()
    else:
        page.locator(
            "li.account-frame a.account-frame__action[aria-label^='%s']" % RENAME_ARIA[lang]).click()


def _open_dialog(new_context, rig, entry, lang="en", viewport=DESKTOP, theme=None, **kwargs):
    context, page = _visit(new_context, rig, entry, lang, viewport, theme, **kwargs)
    _press_opener(page, rig, entry, lang)
    return context, page


def _wait_open(page, rig):
    page.locator(rig.dialog + "[open]").wait_for(state="visible")
    page.wait_for_function(
        "(sel) => document.activeElement === document.querySelector(sel)", arg=rig.field)


def _wait_clean_address(page):
    """The closed dialog leaves the address without the refused-name query."""
    page.wait_for_function("() => location.search.indexOf('rename=') === -1")


def _shown(page, rig, entry):
    return page.locator(rig.where(entry)[2]).first.inner_text()


_GEOMETRY = """(sel) => {
  const d = document.querySelector(sel);
  const box = d.getBoundingClientRect();
  const save = d.querySelector('button[type=submit]').getBoundingClientRect();
  const cancel = d.querySelector('.modal__dismiss--button').getBoundingClientRect();
  const field = d.querySelector('input[name=name]').getBoundingClientRect();
  return {top: box.top, bottom: box.bottom, left: box.left, right: box.right,
          width: box.width, vw: innerWidth, vh: innerHeight,
          save: [save.width, save.height], cancel: [cancel.width, cancel.height],
          field: [field.left, field.right, field.height],
          inside: d.scrollWidth <= d.clientWidth + 1}; }"""


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("viewport", VIEWPORTS, ids=VIEWPORT_IDS)
@pytest.mark.parametrize("entry", ENTRIES)
def test_the_dialog_is_a_sheet_on_a_phone_and_a_card_on_a_desktop_with_the_field_focused(
        new_context, rig, entry, viewport, lang, theme):
    context, page = _open_dialog(new_context, rig, entry, lang, viewport, theme)
    try:
        _wait_open(page, rig)
        assert page.locator(rig.dialog + " h2").inner_text() == TITLE[lang]
        assert page.locator(rig.field).input_value() == "Kitchen"
        assert page.locator(rig.dialog + " .text-label, " + rig.dialog + " .modal__subtitle").count() == 0
        assert page.locator(rig.dialog + " .modal__dismiss--button").inner_text() == CANCEL[lang]
        page.wait_for_timeout(400)
        geo = page.evaluate(_GEOMETRY, rig.dialog)
        assert geo["inside"] and geo["left"] >= -0.5 and geo["right"] <= geo["vw"] + 0.5, geo
        # Save and Cancel share the row at exactly equal widths, both tall enough to tap.
        assert abs(geo["save"][0] - geo["cancel"][0]) <= 0.5, geo
        assert geo["save"][1] >= 43.5 and geo["cancel"][1] >= 43.5 and geo["field"][2] >= 43.5, geo
        assert geo["field"][0] >= geo["left"] and geo["field"][1] <= geo["right"], geo
        if viewport["width"] < 700:
            assert abs(geo["bottom"] - geo["vh"]) <= 1 and geo["width"] >= geo["vw"] - 1, geo
        else:
            assert 0 < geo["top"] and geo["bottom"] < geo["vh"] and geo["width"] < 700, geo
        assert _no_sideways_scroll(page)
    finally:
        context.close()


@pytest.mark.parametrize("entry", ENTRIES)
def test_the_sheet_is_lifted_over_the_on_screen_keyboard(new_context, rig, entry):
    context, page = _open_dialog(new_context, rig, entry, "en", VIEWPORT_MIN_SUPPORTED)
    try:
        _wait_open(page, rig)
        page.wait_for_timeout(400)
        page.evaluate(
            "(sel) => document.querySelector(sel).style.setProperty('--keyboard-inset', '300px')",
            rig.dialog)
        page.wait_for_timeout(100)
        geo = page.evaluate(_GEOMETRY, rig.dialog)
        assert abs(geo["bottom"] - (geo["vh"] - 300)) <= 1, geo
        assert geo["top"] >= 0, geo
    finally:
        context.close()


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("viewport", VIEWPORTS, ids=VIEWPORT_IDS)
@pytest.mark.parametrize("entry", ENTRIES)
def test_save_returns_to_the_page_the_person_was_on_with_the_new_name(
        new_context, rig, entry, viewport, lang):
    context, page = _open_dialog(new_context, rig, entry, lang, viewport)
    try:
        _wait_open(page, rig)
        before = page.url.split("#")[0]
        page.locator(rig.field).fill("Living room")
        page.locator(rig.dialog + " button[type=submit]").click()
        page.wait_for_function(
            "(sel) => document.querySelector(sel) && "
            "document.querySelector(sel).innerText.includes('Living room')",
            arg=rig.where(entry)[2])
        assert rig.name() == "Living room"
        assert page.url.split("#")[0].split("?")[0] == before.split("?")[0]
        assert page.locator(rig.dialog + "[open]").count() == 0
        assert _no_sideways_scroll(page)
    finally:
        context.close()


@pytest.mark.parametrize("how", ["cancel", "escape", "scrim"])
@pytest.mark.parametrize("viewport", VIEWPORTS, ids=VIEWPORT_IDS)
@pytest.mark.parametrize("entry", ENTRIES)
def test_cancel_escape_and_the_scrim_close_the_dialog_and_discard_the_typed_name(
        new_context, rig, entry, viewport, how):
    context, page = _open_dialog(new_context, rig, entry, "en", viewport)
    try:
        _wait_open(page, rig)
        page.locator(rig.field).fill("Discarded")
        if how == "cancel":
            page.locator(rig.dialog + " .modal__dismiss--button").click()
        elif how == "escape":
            page.keyboard.press("Escape")
        else:
            page.mouse.click(viewport["width"] // 2, 4)
        page.locator(rig.dialog).wait_for(state="hidden")
        assert rig.name() == "Kitchen"
        assert "Discarded" not in _shown(page, rig, entry)
        _wait_clean_address(page)
        assert "rename=" not in page.url.split("#")[0]
        page.wait_for_function("document.readyState === 'complete'")
        assert _no_sideways_scroll(page)
    finally:
        context.close()


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("viewport", VIEWPORTS, ids=VIEWPORT_IDS)
@pytest.mark.parametrize("entry", ENTRIES)
def test_a_refused_name_reopens_the_dialog_with_its_error_and_the_next_try_saves(
        new_context, rig, entry, viewport, lang):
    context, page = _open_dialog(new_context, rig, entry, lang, viewport)
    try:
        _wait_open(page, rig)
        page.locator(rig.field).fill("   ")
        page.locator(rig.dialog + " button[type=submit]").click()
        error = page.locator(rig.dialog + " .field-error")
        error.wait_for(state="visible")
        assert error.inner_text().replace("\u00a0", " ") == ERROR[lang]
        assert page.locator(rig.dialog + "[open]").is_visible()
        assert page.locator(rig.field).get_attribute("aria-invalid") == "true"
        try:
            page.wait_for_function(
                "(sel) => document.activeElement === document.querySelector(sel)",
                arg=rig.field, timeout=5000)
        except Exception:
            raise AssertionError(page.evaluate(
                "() => document.activeElement.outerHTML.slice(0, 160)"))
        assert rig.name() == "Kitchen"
        assert _no_sideways_scroll(page)
        page.locator(rig.field).fill("Study")
        page.locator(rig.dialog + " button[type=submit]").click()
        page.wait_for_function(
            "(sel) => document.querySelector(sel) && "
            "document.querySelector(sel).innerText.includes('Study')",
            arg=rig.where(entry)[2])
        assert rig.name() == "Study"
        assert page.locator(rig.dialog + " .field-error").count() == 0 or not page.locator(
            rig.dialog + "[open]").count()
    finally:
        context.close()


def test_a_refused_name_that_closes_goes_back_to_the_page_without_the_error(new_context, rig):
    context, page = _open_dialog(new_context, rig, "account", "en", DESKTOP)
    try:
        _wait_open(page, rig)
        page.locator(rig.field).fill("   ")
        page.locator(rig.dialog + " button[type=submit]").click()
        page.locator(rig.dialog + " .field-error").wait_for(state="visible")
        page.locator(rig.dialog + " .modal__dismiss--button").click()
        page.locator(rig.dialog).wait_for(state="hidden")
        _wait_clean_address(page)
        page.reload()
        page.wait_for_function("document.readyState === 'complete'")
        assert page.locator(rig.dialog + "[open]").count() == 0
        assert page.locator(rig.field).input_value() == "Kitchen"
    finally:
        context.close()


@pytest.mark.parametrize("action", ["save", "cancel"])
@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("entry", ENTRIES)
def test_without_script_the_entry_point_is_a_link_to_the_dialog_and_save_and_cancel_work(
        new_context, rig, entry, lang, action):
    context, page = _visit(
        new_context, rig, entry, lang, VIEWPORT_MIN_SUPPORTED, java_script_enabled=False)
    try:
        _press_opener(page, rig, entry, lang)
        page.locator(rig.dialog).wait_for(state="visible")
        assert page.url.endswith("#" + rig.slug)
        assert page.locator(rig.field).input_value() == "Kitchen"
        assert _no_sideways_scroll(page)
        page.locator(rig.field).fill("No script")
        target = ("button[type=submit]" if action == "save" else ".modal__dismiss--button")
        with page.expect_navigation():
            page.locator(rig.dialog + " " + target).click()
        assert page.locator(rig.dialog).is_hidden()
        expected = "No script" if action == "save" else "Kitchen"
        assert rig.name() == expected
        assert expected in _shown(page, rig, entry)
        assert "rename=" not in page.url.split("#")[0]
    finally:
        context.close()


@pytest.mark.parametrize("lang", LANGS)
def test_without_script_a_refused_name_shows_the_dialog_with_its_error(new_context, rig, lang):
    context, page = _visit(
        new_context, rig, "account", lang, VIEWPORT_MIN_SUPPORTED, java_script_enabled=False)
    try:
        _press_opener(page, rig, "account", lang)
        page.locator(rig.field).fill("   ")
        with page.expect_navigation():
            page.locator(rig.dialog + " button[type=submit]").click()
        page.locator(rig.dialog).wait_for(state="visible")
        assert page.locator(rig.dialog + " .field-error").inner_text().replace(
            "\u00a0", " ") == ERROR[lang]
        assert rig.name() == "Kitchen"
    finally:
        context.close()


@pytest.mark.parametrize("entry", ("account",))
def test_the_old_rename_address_opens_the_dialog_on_the_page_it_came_from(
        new_context, rig, entry):
    _who, path, _shown_selector = rig.where(entry)
    context, page = _visit(new_context, rig, entry)
    try:
        page.goto(rig.url("/devices/%s/frame/name?return_to=%s" % (
            rig.seed.owned_id, path.replace("/", "%2F"))))
        _wait_open(page, rig)
        assert page.url.split("#")[0].endswith(path)
        page.locator(rig.dialog + " .modal__dismiss--button").click()
        page.locator(rig.dialog).wait_for(state="hidden")
    finally:
        context.close()
