"""Real-browser checks of the Airline editor (/airlines/manage, administrator only): it opens in the
Console chrome with no frame strip (one global list) at 360 and 1280 px, in English and French, in both themes, with
no sideways scroll and every control at least 44 px and owning its centre. It is reached from the
Console (the Airlines bar cell on a phone, the sidebar link on desktop). An airline named by hand
keeps its row with a pill and no separate list exists; "Delete my name" in its row menu removes the
name, with and without scripts. Renaming an airline works end to end.

State is always waited for (settled page, owned centres, focus), never read right after an input."""
import animation_settle
import pytest

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_hit_target, _assert_no_page_overflow,
    _in_both_themes, _login,
)
from server.plane import manual_resolutions

pytestmark = pytest.mark.browser

VIEWPORTS = (("360", VIEWPORT_MIN_SUPPORTED), ("1280", VIEWPORT_DESKTOP))
ROW = '.airlines-missing__airline:has(form[action*="manual-resolutions/"])'
DELETE_LINK = ROW + " .airlines-missing__head .row-menu__toggle"
FRANCE = "#airline-air-france"
FRANCE_NAME = FRANCE + " .airlines-name"
FRANCE_MENU = FRANCE + " .airlines-row .row-menu__toggle"
FRANCE_DIALOG = FRANCE + " dialog"
FRANCE_FIELD = FRANCE_DIALOG + ' input[name="airline_name"]'

_SETTLED = animation_settle.SETTLED
_OWNS_CENTRE = (
    "sel => { const el = document.querySelector(sel); if (!el) return false;"
    " const r = el.getBoundingClientRect();"
    " const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);"
    " return !!hit && (hit === el || el.contains(hit) || hit.contains(el)); }")


def _seed(state_dir):
    fx.seed_fleet(state_dir)
    manual_resolutions.add_entry(state_dir, "ZZZ", "Zed Air")
    manual_resolutions.add_entry(state_dir, "QQQ", "Quux Air")


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=_seed, fake_providers=True)


def _open(new_context, server, viewport, lang="en", path="/airlines/manage",
          ready=".airlines-row", **context_args):
    context = new_context(viewport=viewport, **context_args)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + path)
    _settle(page, ready)
    return context, page


def _settle(page, selector):
    page.locator(selector).first.wait_for(state="visible")
    page.wait_for_function(_SETTLED, timeout=15000)
    page.locator(selector).first.evaluate("el => el.scrollIntoView({block: 'center'})")
    page.wait_for_function(
        "sel => { const el = document.querySelector(sel);"
        " const r = el.getBoundingClientRect();"
        " const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);"
        " return !!hit && (hit === el || el.contains(hit) || hit.contains(el)); }",
        arg=selector, timeout=10000)


@pytest.mark.parametrize("lang", ("en", "fr"))
@pytest.mark.parametrize("name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_the_editor_is_a_console_page_without_a_frame_strip_and_with_usable_controls(
        new_context, server, name, viewport, lang):
    context, page = _open(new_context, server, viewport, lang)
    try:
        title = "Airline editor" if lang == "en" else "Éditeur de compagnies"
        assert page.locator("h1.page-title").inner_text() == title
        assert page.locator('a.space-switch__segment--current[href="/fleet"]').count() >= 1
        assert page.locator("details.frame-menu").count() == 0
        for _paint in _in_both_themes(page):
            page.wait_for_function(_SETTLED, timeout=15000)
            assert not _assert_no_page_overflow(page, "editor", viewport["width"])
            for selector in (FRANCE_MENU, DELETE_LINK):
                _settle(page, selector)
                _assert_hit_target(page, selector, "editor %s %s" % (name, lang))
    finally:
        context.close()


def test_the_editor_is_reached_from_the_console_bar_on_a_phone(new_context, server):
    context, page = _open(new_context, server, VIEWPORT_MIN_SUPPORTED, path="/fleet", ready="main h1")
    try:
        taps = 0
        link = page.locator('.tab-bar > a[href$="/airlines/manage"]')
        link.wait_for(state="visible")
        with page.expect_navigation():
            link.click()
        taps += 1
        page.wait_for_url("**/airlines/manage")
        assert page.locator("h1.page-title").inner_text() == "Airline editor"
        assert taps == 1
    finally:
        context.close()


def test_the_editor_is_reached_from_the_sidebar_on_desktop(new_context, server):
    # The Fleet landing has one h1, the list title.
    context, page = _open(
        new_context, server, VIEWPORT_DESKTOP, path="/fleet", ready="main h1")
    try:
        link = page.locator('nav.sidebar-nav a[href$="/airlines/manage"]')
        link.wait_for(state="visible")
        assert link.inner_text().strip() == "Editor"
        with page.expect_navigation():
            link.click()
        page.wait_for_url("**/airlines/manage")
        assert page.locator("h1.page-title").inner_text() == "Airline editor"
    finally:
        context.close()


def test_a_hand_named_airline_keeps_its_header_and_its_menu_deletes_the_name(
        new_context, make_app_server):
    """no separate manual-resolutions table: the two owner-named airlines keep a header in the missing-illustrations section, and "Delete my name" in its menu removes the name"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, VIEWPORT_DESKTOP)
    try:
        assert page.locator(".manual-resolutions").count() == 0
        assert page.locator(ROW).count() == 2
        assert "Named by hand" not in page.locator(ROW).first.inner_text()
        _settle(page, DELETE_LINK)
        page.locator(DELETE_LINK).first.click()
        item = page.locator(ROW + " .row-menu__panel button.row-menu__item").first
        item.wait_for(state="visible")
        assert item.inner_text() == "Delete my name"
        with page.expect_navigation():
            item.click()
        page.wait_for_url("**/airlines/manage")
        page.wait_for_function(_SETTLED, timeout=15000)
        page.wait_for_function(
            "() => document.querySelectorAll('%s').length === 1" % ROW, timeout=10000)
        remaining = manual_resolutions.load_manual_resolutions(server.state_dir)
        assert len(remaining) == 1
    finally:
        context.close()


def test_without_scripts_the_menu_opens_and_deleting_the_name_works(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(
        new_context, server, VIEWPORT_MIN_SUPPORTED, java_script_enabled=False,
        reduced_motion="reduce")
    try:
        page.locator(DELETE_LINK).first.click()
        item = page.locator(ROW + " .row-menu__panel button.row-menu__item").first
        item.wait_for(state="visible")
        with page.expect_navigation():
            item.click()
        page.wait_for_url("**/airlines/manage")
        page.wait_for_load_state("load")
        assert page.locator(ROW).count() == 1
    finally:
        context.close()


def test_renaming_an_airline_through_the_editor_works_end_to_end(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, VIEWPORT_MIN_SUPPORTED, path="/fleet", ready="main h1")
    try:
        taps = 0
        link = page.locator('.tab-bar > a[href$="/airlines/manage"]')
        link.wait_for(state="visible")
        with page.expect_navigation():
            link.click()
        taps += 1
        page.wait_for_url("**/airlines/manage")
        _settle(page, FRANCE_MENU)
        page.locator(FRANCE_MENU).click()
        taps += 1
        page.locator(FRANCE + " .airlines-row .row-menu__panel a.row-menu__item").click()
        taps += 1
        field = page.locator(FRANCE_FIELD)
        field.wait_for(state="visible")
        field.fill("Skyline Air")
        with page.expect_navigation():
            page.locator(FRANCE_DIALOG + " button[type=submit]").click()
        taps += 1
        page.wait_for_function(
            "() => document.body.innerText.includes('Airline name saved')", timeout=15000)
        page.wait_for_function(_SETTLED, timeout=15000)
        assert page.locator("#airline-skyline-air .airlines-name").inner_text() == "Skyline Air"
        print("STEP-COUNT A8 phone %d" % taps)
        assert taps == 4
    finally:
        context.close()


KNOWN_ROW = ".airlines-missing__item"
KNOWN_ADD = KNOWN_ROW + " .airlines-missing__add"
_CENTRED_TEXT = (
    "el => { const range = document.createRange(); range.selectNodeContents(el.querySelector('.airlines-missing__text'));"
    " const text = range.getBoundingClientRect(); const box = el.getBoundingClientRect();"
    " return Math.abs((text.top + text.height / 2) - (box.top + box.height / 2)); }")


@pytest.mark.parametrize("lang", ("en", "fr"))
@pytest.mark.parametrize("name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_missing_illustrations_are_rows_with_an_illustration_button_and_a_chip(
        new_context, server, name, viewport, lang):
    context, page = _open(new_context, server, viewport, lang, ready=KNOWN_ROW)
    try:
        rows = page.locator(KNOWN_ROW)
        assert rows.count() >= 4
        assert rows.first.locator("input:visible, form:visible").count() == 0
        for index in range(rows.count()):
            button = page.locator(KNOWN_ADD).nth(index)
            box = button.bounding_box()
            assert box["height"] >= 44 and box["width"] >= 44
            assert button.evaluate(_CENTRED_TEXT) <= 2
        chip_text = "Missing illustrations" if lang == "en" else "Illustrations manquantes"
        chips = page.locator(".filter-bar__chips")
        assert chips.evaluate("el => getComputedStyle(el).flexWrap") == "nowrap" or viewport["width"] > 500
        chip = page.locator(".filter-chip", has_text=chip_text)
        chip.click()
        page.wait_for_function(
            "n => document.querySelectorAll('.airlines-missing__item:not([hidden])').length === n",
            arg=rows.count())
        assert page.locator("tbody.airline-group:not([hidden])").count() == 0
        assert page.locator("tbody.airline-group--gap:not([hidden])").count() == 0
        assert not _assert_no_page_overflow(page, "missing", viewport["width"])
    finally:
        context.close()


def test_the_artwork_button_opens_the_shared_add_artwork_step(new_context, server):
    context, page = _open(new_context, server, VIEWPORT_DESKTOP, ready=KNOWN_ROW)
    try:
        _settle(page, KNOWN_ADD)
        page.locator(KNOWN_ADD).first.click()
        page.locator("dialog[open]").wait_for(state="visible")
        assert page.locator('dialog[open] input[type="file"]').count() >= 1
    finally:
        context.close()
