"""Leaving a Style view with an unsaved layout asks in the page's own dialog:
Save and continue persists the layout and lands on the tapped view, Discard
leaves without saving, Stay here (and Escape) changes nothing and gives the
focus back to the tapped link. Only a layout change asks."""
import pytest

from companion import auth, layout
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT,
    VIEWPORT_DESKTOP,
    VIEWPORT_MIN_SUPPORTED,
    _assert_no_page_overflow,
    _login,
    _set_ui_theme,
    _wait_for_bar,
    seed_state_dir,
)
from server import device_config

pytestmark = pytest.mark.browser

DIALOG = "dialog[data-layout-leave]"
PRIMARY = DIALOG + " [data-layout-leave-primary]"
SECONDARY = DIALOG + " [data-layout-leave-secondary]"
QUIET = DIALOG + " [data-layout-leave-quiet]"
CHECKED_LAYOUT = "#personalisation-layout input[name=layout]:checked"
GREEN = '[data-look-sheet][data-look-inline] input[data-look-axis="colour"][value="green"]'
WORDS = {
    "en": ("Layout not saved", "You changed the layout. What do you want to do?",
           "Save and continue", "Discard", "Stay here"),
    "fr": ("Disposition non enregistrée", "Vous avez modifié la disposition. Que voulez-vous faire\u00a0?",
           "Enregistrer et continuer", "Ignorer", "Rester ici"),
}
CASES = [(name, viewport, lang)
         for name, viewport in (("360", VIEWPORT_MIN_SUPPORTED), ("1280", VIEWPORT_DESKTOP))
         for lang in ("en", "fr")]
CASE_IDS = ["%s-%s" % (name, lang) for name, _viewport, lang in CASES]
SETTLED = (
    "() => document.readyState === 'complete'"
    " && document.getAnimations().every(a => a.playState !== 'running'"
    " || a.effect.getComputedTiming().iterations === Infinity)")


def _seed(state_dir):
    seed_state_dir(state_dir)
    device_config.save_device_config(state_dir, layout="classic")


def _seed_with_look(state_dir):
    seed_state_dir(state_dir)
    device_config.save_device_config(state_dir, layout="classic", theme="band_red_field")


def _tab(page, view):
    return page.locator('[data-tabs="display"] a[data-pers-view="%s"]' % view)


def _open(new_context, server, viewport, lang, route=None):
    base = server.base_url()
    context = new_context(viewport=viewport)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base}])
    page = context.new_page()
    _login(page, base)
    page.goto(base + (route or layout.DISPLAY_ROUTE))
    page.locator("#personalisation-layout [data-layout-toggle]").wait_for(state="attached")
    page.wait_for_function(SETTLED, timeout=15000)
    return context, page


def _pick_layout_c(page):
    toggle = page.locator("#personalisation-layout [data-layout-toggle]")
    if toggle.is_visible():
        toggle.click()
    page.locator('#personalisation-layout label:has(input[value="c"])').click()
    _wait_for_bar(page)


def _tap_tab(page, view):
    _tab(page, view).scroll_into_view_if_needed()
    page.wait_for_function(
        "(sel) => { const a = document.querySelector(sel); if (!a) return false;"
        " const r = a.getBoundingClientRect();"
        " const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);"
        " return !!hit && a.contains(hit); }",
        arg='[data-tabs="display"] a[data-pers-view="%s"]' % view, timeout=10000)
    _tab(page, view).click()


def _wait_dialog_open(page):
    page.wait_for_function(
        "() => { const d = document.querySelector('%s'); return !!d && d.open; }" % DIALOG,
        timeout=5000)


def _wait_dialog_closed(page):
    page.wait_for_function(
        "() => { const d = document.querySelector('%s'); return !!d && !d.open; }" % DIALOG,
        timeout=5000)


def _stored_layout(server):
    return device_config.load_device_config(server.state_dir).get("layout")


@pytest.mark.parametrize("name,viewport,lang", CASES, ids=CASE_IDS)
def test_tapping_a_sub_tab_with_an_unsaved_layout_opens_the_dialog(
        new_context, make_app_server, name, viewport, lang):
    """the dialog opens before the page changes, with the three actions in the reader's language, on the
    safest action, no cut text, 44 px targets and no sideways scroll in both themes"""
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server, viewport, lang)
    try:
        start = page.url
        _pick_layout_c(page)
        _tap_tab(page, "arrivals")
        _wait_dialog_open(page)
        assert page.url == start
        title, text, primary, secondary, quiet = WORDS[lang]
        assert page.locator(DIALOG + " .modal__title").inner_text() == title
        assert page.locator(DIALOG + " .modal__body").inner_text() == text
        assert page.locator(PRIMARY).inner_text() == primary
        assert page.locator(SECONDARY).inner_text() == secondary
        assert page.locator(QUIET).inner_text() == quiet
        page.wait_for_function(
            "() => document.activeElement && document.activeElement.hasAttribute('data-layout-leave-quiet')",
            timeout=5000)
        for theme in UI_THEMES_EXPLICIT:
            _set_ui_theme(page, theme)
            for selector in (PRIMARY, SECONDARY, QUIET):
                box = page.locator(selector).bounding_box()
                assert box["height"] >= 43.5 and box["width"] >= 43.5, (selector, box)
                assert box["x"] >= 0 and box["x"] + box["width"] <= viewport["width"] + 0.5, box
                assert page.eval_on_selector(
                    selector, "el => el.scrollWidth <= el.clientWidth + 1"), (selector, lang)
        _assert_no_page_overflow(page, "layout leave dialog %s" % name)
    finally:
        context.close()


@pytest.mark.parametrize("name,viewport,lang", CASES[::2], ids=CASE_IDS[::2])
def test_without_a_layout_change_the_tab_navigates_and_no_dialog_opens(
        new_context, make_app_server, name, viewport, lang):
    """a clean page, and a page whose only change is a look colour, never raise the layout dialog"""
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server, viewport, lang)
    try:
        _tap_tab(page, "arrivals")
        page.wait_for_url("**" + layout.DISPLAY_ARRIVALS_ROUTE, timeout=10000)
        assert not page.evaluate("() => document.querySelector('%s').open" % DIALOG)
    finally:
        context.close()
    server = make_app_server(seed=_seed_with_look)
    context, page = _open(new_context, server, viewport, lang)
    prompts = []
    page.on("dialog", lambda d: (prompts.append(d.type), d.accept()))
    try:
        page.locator(GREEN + " >> xpath=..").click()
        _wait_for_bar(page)
        _tap_tab(page, "special-looks")
        page.wait_for_url("**" + layout.DISPLAY_SPECIAL_LOOKS_ROUTE, timeout=10000)
        assert prompts == ["beforeunload"]
        assert not page.evaluate("() => document.querySelector('%s').open" % DIALOG)
    finally:
        context.close()


@pytest.mark.parametrize("name,viewport,lang", CASES, ids=CASE_IDS)
def test_save_and_continue_saves_the_layout_then_opens_the_tapped_view(
        new_context, make_app_server, name, viewport, lang):
    """the layout is stored and the destination shows it as the selected one"""
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server, viewport, lang)
    prompts = []
    page.on("dialog", lambda d: (prompts.append(d.type), d.accept()))
    try:
        _pick_layout_c(page)
        _tap_tab(page, "calendar")
        _wait_dialog_open(page)
        with page.expect_navigation(timeout=20000):
            page.click(PRIMARY)
        page.wait_for_url("**" + layout.DISPLAY_CALENDAR_ROUTE + "*", timeout=15000)
        page.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
        assert _stored_layout(server) == "c"
        assert page.locator(CHECKED_LAYOUT).get_attribute("value") == "c"
        assert prompts == []
    finally:
        context.close()


@pytest.mark.parametrize("name,viewport,lang", CASES, ids=CASE_IDS)
def test_discard_opens_the_tapped_view_without_saving(
        new_context, make_app_server, name, viewport, lang):
    """nothing is stored, the destination shows the stored layout and the browser's own prompt never appears"""
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server, viewport, lang)
    prompts = []
    page.on("dialog", lambda d: (prompts.append(d.type), d.accept()))
    try:
        _pick_layout_c(page)
        _tap_tab(page, "special-looks")
        _wait_dialog_open(page)
        page.click(SECONDARY)
        page.wait_for_url("**" + layout.DISPLAY_SPECIAL_LOOKS_ROUTE, timeout=15000)
        page.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
        assert _stored_layout(server) == "classic"
        assert page.locator(CHECKED_LAYOUT).get_attribute("value") == "classic"
        assert prompts == []
    finally:
        context.close()


@pytest.mark.parametrize("how", ["button", "escape"])
@pytest.mark.parametrize("name,viewport,lang", CASES, ids=CASE_IDS)
def test_stay_here_and_escape_change_nothing_and_return_the_focus(
        new_context, make_app_server, name, viewport, lang, how):
    """the dialog closes, the page, the picked layout and the save bar stay, the tapped link has the focus"""
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server, viewport, lang)
    try:
        start = page.url
        _pick_layout_c(page)
        _tap_tab(page, "arrivals")
        _wait_dialog_open(page)
        page.wait_for_function(
            "() => document.activeElement && document.activeElement.hasAttribute('data-layout-leave-quiet')",
            timeout=5000)
        if how == "button":
            page.click(QUIET)
        else:
            page.keyboard.press("Escape")
        _wait_dialog_closed(page)
        page.wait_for_function(
            "() => { const a = document.activeElement; return !!a && a.matches("
            "'[data-tabs=\"display\"] a[data-pers-view=\"arrivals\"]'); }", timeout=5000)
        assert page.url == start
        assert page.locator(CHECKED_LAYOUT).get_attribute("value") == "c"
        _wait_for_bar(page)
        assert _stored_layout(server) == "classic"
    finally:
        context.close()


def test_without_script_the_tabs_are_plain_links_and_the_dialog_stays_closed(
        new_context, make_app_server):
    """scripts blocked: the link navigates and the dialog is not shown"""
    server = make_app_server(seed=_seed)
    context = new_context(viewport=VIEWPORT_DESKTOP, java_script_enabled=False)
    page = context.new_page()
    try:
        _login(page, server.base_url())
        page.goto(server.base_url() + layout.DISPLAY_ROUTE)
        assert not page.locator(DIALOG).is_visible()
        _tab(page, "arrivals").click()
        page.wait_for_url("**" + layout.DISPLAY_ARRIVALS_ROUTE, timeout=10000)
    finally:
        context.close()
