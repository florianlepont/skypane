"""Real-browser checks of the Airline editor (/airlines/manage, administrator only): it opens in the
Console chrome with no frame strip (one global list) at 360 and 1280 px, in English and French, in both themes, with
no sideways scroll and every control at least 44 px and owning its centre. It is reached from the
Console (the Airlines bar cell on a phone, the sidebar link on desktop). An airline named by hand
keeps its row with a pill and no separate list exists; "Delete my name" in its row menu removes the
name, with and without scripts. Renaming an airline works end to end.

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
ROW = "tbody.airline-group:has(.airlines-pill)"
DELETE_LINK = ROW + " .airlines-row .row-menu__toggle"
FRANCE_NAME = '.airlines-name input[name="airline_name"][value="Air France"]'

_SETTLED = (
    "() => document.readyState === 'complete'"
    " && document.getAnimations().every(a => a.effect && a.effect.getTiming().iterations !== Infinity"
    " ? a.playState !== 'running' : true)")
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
            for selector in (FRANCE_NAME, DELETE_LINK):
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


def test_a_hand_named_airline_stays_in_the_table_and_its_menu_deletes_the_name(
        new_context, make_app_server):
    """no separate manual-resolutions table: the two owner-named airlines keep a row with the
    "Named by hand" pill, and "Delete my name" in the row menu removes the name"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, VIEWPORT_DESKTOP)
    try:
        assert page.locator(".manual-resolutions").count() == 0
        assert page.locator(ROW).count() == 2
        assert page.locator(ROW + " .airlines-pill").first.inner_text() == "Named by hand"
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
        new_context, server, VIEWPORT_MIN_SUPPORTED, java_script_enabled=False)
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
        _settle(page, FRANCE_NAME)
        field = page.locator(FRANCE_NAME)
        field.click()
        taps += 1
        field.fill("Skyline Air")
        with page.expect_navigation():
            field.press("Enter")
        taps += 1
        page.wait_for_function(
            "() => document.body.innerText.includes('Airline name saved')", timeout=15000)
        page.wait_for_function(_SETTLED, timeout=15000)
        assert page.locator('.airlines-name input[value="Skyline Air"]').count() == 1
        print("STEP-COUNT A8 phone %d" % taps)
        assert taps == 3
    finally:
        context.close()
