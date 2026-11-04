"""Real-browser checks of the Airline editor (/airlines/manage, administrator only): it opens in the
Console chrome with the frame chip at 360 and 1280 px, in English and French, in both themes, with
no sideways scroll and every control at least 44 px and owning its centre. It is reached from the
Console (More then Airline editor on a phone, the sidebar link on desktop). Deleting a manual
resolution confirms in a dialog whose safe dismiss "Keep resolution" takes the focus, Tab stays
inside, Escape closes it and returns the focus to the Delete link, and Delete resolution removes the
row; with scripts blocked the hash link shows the dialog and the POST works. Renaming an airline
works end to end.

State is always waited for (settled page, owned centres, focus), never read right after an input."""
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
DELETE_LINK = ".manual-resolution-row a.special-row__remove"
ROW = ".manual-resolution-row"
DIALOG = "dialog.modal[open]"
FRANCE_PENCIL = '.airline-row[data-view-panel-sheet-key="air-france"]'
NAME_INPUT = '#panel-lookup-dialog .airline-sheet input[name="airline_name"]'

_SETTLED = (
    "() => document.readyState === 'complete'"
    " && document.getAnimations().every(a => a.effect && a.effect.getTiming().iterations !== Infinity"
    " ? a.playState !== 'running' : true)")
_OWNS_CENTRE = (
    "sel => { const el = document.querySelector(sel); if (!el) return false;"
    " const r = el.getBoundingClientRect();"
    " const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);"
    " return !!hit && (hit === el || el.contains(hit) || hit.contains(el)); }")
_FOCUS_IN_DIALOG_OR_NOWHERE = (
    "() => { const a = document.activeElement; return !a || a === document.body"
    " || !!a.closest('dialog.modal[open]'); }")
_FOCUS_ON_DISMISS = "() => document.activeElement.matches('dialog.modal[open] a.modal__dismiss')"


def _seed(state_dir):
    fx.seed_fleet(state_dir)
    manual_resolutions.add_entry(state_dir, "ZZZ", "Zed Air")
    manual_resolutions.add_entry(state_dir, "QQQ", "Quux Air")


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=_seed, fake_providers=True)


def _open(new_context, server, viewport, lang="en", path="/airlines/manage",
          ready=".airline-row", **context_args):
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
def test_the_editor_is_a_console_page_with_the_frame_chip_and_usable_controls(
        new_context, server, name, viewport, lang):
    context, page = _open(new_context, server, viewport, lang)
    try:
        title = "Airline editor" if lang == "en" else "Éditeur de compagnies"
        assert page.locator("h1.page-title").inner_text() == title
        assert page.locator('a.space-switch__segment--current[href="/fleet"]').count() >= 1
        assert page.locator("a.frame-chip").first.is_visible()
        for _paint in _in_both_themes(page):
            page.wait_for_function(_SETTLED, timeout=15000)
            assert not _assert_no_page_overflow(page, "editor", viewport["width"])
            for selector in (".airline-row", DELETE_LINK, "a.frame-chip"):
                _settle(page, selector)
                _assert_hit_target(page, selector, "editor %s %s" % (name, lang))
    finally:
        context.close()


def test_the_editor_is_reached_from_the_console_more_sheet_on_a_phone(new_context, server):
    context, page = _open(new_context, server, VIEWPORT_MIN_SUPPORTED, path="/fleet", ready="main h1")
    try:
        taps = 0
        page.locator(".tab-bar__more > summary").click()
        taps += 1
        link = page.locator(".tab-bar__more-panel a", has_text="Airline editor")
        link.wait_for(state="visible")
        with page.expect_navigation():
            link.click()
        taps += 1
        page.wait_for_url("**/airlines/manage")
        assert page.locator("h1.page-title").inner_text() == "Airline editor"
        assert taps == 2
    finally:
        context.close()


def test_the_editor_is_reached_from_the_sidebar_on_desktop(new_context, server):
    context, page = _open(new_context, server, VIEWPORT_DESKTOP, path="/fleet", ready="main h1")
    try:
        link = page.locator('nav.sidebar-nav a[href$="/airlines/manage"]')
        link.wait_for(state="visible")
        assert link.inner_text().strip() == "Airline editor"
        with page.expect_navigation():
            link.click()
        page.wait_for_url("**/airlines/manage")
        assert page.locator("h1.page-title").inner_text() == "Airline editor"
    finally:
        context.close()


@pytest.mark.parametrize("name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_the_delete_dialog_names_its_safe_dismiss_and_keeps_focus_inside(
        new_context, make_app_server, name, viewport):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, viewport)
    try:
        trigger = page.locator(DELETE_LINK).first
        _settle(page, DELETE_LINK)
        trigger.click()
        page.wait_for_selector(DIALOG)
        page.wait_for_function(_FOCUS_ON_DISMISS, timeout=10000)
        dialog = page.locator(DIALOG)
        assert dialog.locator(".modal__title").inner_text() == "Delete this resolution?"
        assert dialog.locator("a.modal__dismiss").inner_text() == "Keep resolution"
        page.evaluate(
            """() => { window.__inside = [];
              document.addEventListener('focusin', (e) => window.__inside.push(
                !!e.target.closest('dialog.modal[open]'))); }""")
        for key in ["Tab"] * 8 + ["Shift+Tab"] * 3:
            page.keyboard.press(key)
            page.wait_for_function(_FOCUS_IN_DIALOG_OR_NOWHERE, timeout=5000)
        page.wait_for_function(
            "() => window.__inside.length >= 4 && window.__inside.every(Boolean)", timeout=5000)
        page.keyboard.press("Escape")
        page.wait_for_selector(DIALOG, state="detached")
        page.wait_for_function(
            "() => document.activeElement === document.querySelector('%s')" % DELETE_LINK,
            timeout=10000)
        assert page.locator(ROW).count() == 2
    finally:
        context.close()


def test_confirming_the_delete_removes_the_resolution_and_keeping_it_does_not(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, VIEWPORT_DESKTOP)
    try:
        page.locator(DELETE_LINK).first.click()
        page.wait_for_function(_FOCUS_ON_DISMISS, timeout=10000)
        page.locator(DIALOG + " a.modal__dismiss").click()
        page.wait_for_selector(DIALOG, state="detached")
        assert page.locator(ROW).count() == 2
        page.locator(DELETE_LINK).first.click()
        page.wait_for_function(_FOCUS_ON_DISMISS, timeout=10000)
        with page.expect_navigation():
            page.locator(DIALOG + " button[type=submit]").click()
        page.wait_for_url("**/airlines/manage")
        page.wait_for_function(_SETTLED, timeout=15000)
        page.wait_for_function(
            "() => document.querySelectorAll('%s').length === 1" % ROW, timeout=10000)
        remaining = manual_resolutions.load_manual_resolutions(server.state_dir)
        assert list(remaining) == ["ZZZ"]
    finally:
        context.close()


def test_without_scripts_the_hash_link_shows_the_dialog_and_the_post_works(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(
        new_context, server, VIEWPORT_MIN_SUPPORTED, java_script_enabled=False)
    try:
        page.locator(DELETE_LINK).first.click()
        dialog = page.locator("dialog.modal:target")
        dialog.wait_for(state="visible")
        with page.expect_navigation():
            dialog.locator("button[type=submit]").click()
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
        page.locator(".tab-bar__more > summary").click()
        taps += 1
        link = page.locator(".tab-bar__more-panel a", has_text="Airline editor")
        link.wait_for(state="visible")
        with page.expect_navigation():
            link.click()
        taps += 1
        page.wait_for_url("**/airlines/manage")
        _settle(page, FRANCE_PENCIL)
        page.locator(FRANCE_PENCIL).click()
        taps += 1
        field = page.locator(NAME_INPUT)
        field.wait_for(state="visible")
        field.click()
        taps += 1
        field.fill("Skyline Air")
        with page.expect_navigation():
            page.locator("#panel-lookup-dialog .airline-sheet__name button").click()
        taps += 1
        page.wait_for_function(
            "() => document.body.innerText.includes('Airline name saved')", timeout=15000)
        page.wait_for_function(_SETTLED, timeout=15000)
        assert page.locator('.airline-row__name:text-is("Skyline Air")').count() == 1
        print("STEP-COUNT A8 phone %d" % taps)
        assert taps == 5
    finally:
        context.close()
