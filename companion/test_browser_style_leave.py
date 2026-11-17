"""Leaving a Style page through an in-app link with anything unsaved asks in
the page's own dialog: Save and continue persists the change and lands on the
tapped destination, Discard leaves without saving, Stay here (and Escape)
changes nothing and gives the focus back to the tapped link. Any unsaved value
asks - the layout, a colour, a special look - and the bottom tab bar, the More
sheet and the Style sub-tabs all ask. A clean page never asks."""
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
    _wait_for_bar_hidden,
    seed_state_dir,
)
from server import device_config

pytestmark = pytest.mark.browser

DIALOG = "dialog[data-leave-dialog]"
PRIMARY = DIALOG + " [data-leave-dialog-primary]"
SECONDARY = DIALOG + " [data-leave-dialog-secondary]"
QUIET = DIALOG + " [data-leave-dialog-quiet]"
CHECKED_LAYOUT = "#personalisation-layout input[name=layout]:checked"
GREEN = '[data-look-sheet][data-look-inline] input[data-look-axis="colour"][value="green"]'
WORDS = {
    "en": ("Unsaved changes", "You have changes that are not saved. What do you want to do?",
           "Save and continue", "Discard", "Stay here"),
    "fr": ("Modifications non enregistrées",
           "Vous avez des modifications non enregistrées. Que souhaitez-vous faire\u00a0?",
           "Enregistrer et continuer", "Abandonner", "Rester ici"),
}
CASES = [(name, viewport, lang)
         for name, viewport in (("360", VIEWPORT_MIN_SUPPORTED), ("1280", VIEWPORT_DESKTOP))
         for lang in ("en", "fr")]
CASE_IDS = ["%s-%s" % (name, lang) for name, _viewport, lang in CASES]
# The bottom tab bar is the phone's navigation; the wide screen has the
# sidebar instead, so the two are exercised on their own viewport.
PHONE_CASES = [case for case in CASES if case[0] == "360"]
PHONE_IDS = ["%s-%s" % (name, lang) for name, _viewport, lang in PHONE_CASES]
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
    # has_touch: the phone fires a touch tap, the path the owner uses, and
    # Playwright refuses tap() on a context without it.
    context = new_context(viewport=viewport, has_touch=True)
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


def _pick_a_colour(page):
    """Changes one colour through the page's own look picker and waits for the
    bar to count it."""
    page.locator(GREEN + " >> xpath=..").click()
    _wait_for_bar(page)


def _wait_hittable(page, selector):
    page.wait_for_function(
        "(sel) => { const a = document.querySelector(sel); if (!a) return false;"
        " const r = a.getBoundingClientRect();"
        " const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);"
        " return !!hit && a.contains(hit); }",
        arg=selector, timeout=10000)


def _press(page, selector, how="tap"):
    """Touch tap or mouse click on a settled, hit-testable control."""
    page.locator(selector).first.scroll_into_view_if_needed()
    _wait_hittable(page, selector)
    if how == "tap":
        page.locator(selector).first.tap()
    else:
        page.locator(selector).first.click()


def _tap_tab(page, view, how="tap"):
    _press(page, '[data-tabs="display"] a[data-pers-view="%s"]' % view, how)


def _tap_bottom_tab(page, route, how="tap"):
    """A cell of the phone's bottom tab bar, the way out the owner used."""
    _press(page, '.tab-bar__link[href="%s"]' % route, how)


def _tap_sidebar_link(page, route, how="tap"):
    """The wide screen's equivalent: a link of the sidebar navigation."""
    _press(page, '.sidebar-link[href="%s"]' % route, how)


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


def _stored_theme(server):
    return device_config.load_device_config(server.state_dir).get("theme")


@pytest.mark.parametrize("name,viewport,lang", CASES, ids=CASE_IDS)
def test_tapping_a_sub_tab_with_an_unsaved_change_opens_the_dialog(
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
            "() => document.activeElement && document.activeElement.hasAttribute('data-leave-dialog-quiet')",
            timeout=5000)
        for theme in UI_THEMES_EXPLICIT:
            _set_ui_theme(page, theme)
            for selector in (PRIMARY, SECONDARY, QUIET):
                box = page.locator(selector).bounding_box()
                assert box["height"] >= 43.5 and box["width"] >= 43.5, (selector, box)
                assert box["x"] >= 0 and box["x"] + box["width"] <= viewport["width"] + 0.5, box
                assert page.eval_on_selector(
                    selector, "el => el.scrollWidth <= el.clientWidth + 1"), (selector, lang)
        _assert_no_page_overflow(page, "style leave dialog %s" % name)
    finally:
        context.close()


@pytest.mark.parametrize("name,viewport,lang", CASES[::2], ids=CASE_IDS[::2])
def test_a_clean_page_navigates_and_no_dialog_opens(
        new_context, make_app_server, name, viewport, lang):
    """with nothing changed, a sub-tab and a bottom tab-bar cell are plain links again"""
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server, viewport, lang)
    try:
        _tap_tab(page, "arrivals")
        page.wait_for_url("**" + layout.DISPLAY_ARRIVALS_ROUTE, timeout=10000)
        assert not page.evaluate("() => document.querySelector('%s').open" % DIALOG)
    finally:
        context.close()
    context, page = _open(new_context, server, viewport, lang)
    try:
        if name == "360":
            _tap_bottom_tab(page, layout.HOME_ROUTE)
        else:
            _tap_sidebar_link(page, layout.HOME_ROUTE)
        page.wait_for_url(server.base_url() + "/", timeout=10000)
    finally:
        context.close()


@pytest.mark.parametrize("how", ["tap", "click"])
@pytest.mark.parametrize("name,viewport,lang", CASES[::2], ids=CASE_IDS[::2])
def test_an_unsaved_colour_alone_opens_the_dialog(
        new_context, make_app_server, name, viewport, lang, how):
    """a colour change with the layout untouched asks too, by touch tap and by click, and the
    browser's own prompt never replaces the dialog"""
    server = make_app_server(seed=_seed_with_look)
    context, page = _open(new_context, server, viewport, lang)
    prompts = []
    page.on("dialog", lambda d: (prompts.append(d.type), d.accept()))
    try:
        start = page.url
        _pick_a_colour(page)
        _tap_tab(page, "special-looks", how)
        _wait_dialog_open(page)
        assert page.url == start
        assert prompts == []
        assert page.locator(DIALOG + " .modal__title").inner_text() == WORDS[lang][0]
    finally:
        context.close()


@pytest.mark.parametrize("name,viewport,lang", CASES[::2], ids=CASE_IDS[::2])
def test_save_and_continue_saves_a_colour_change_and_lands_on_the_tapped_view(
        new_context, make_app_server, name, viewport, lang):
    """the colour is stored and the tapped Style view is the one shown"""
    server = make_app_server(seed=_seed_with_look)
    context, page = _open(new_context, server, viewport, lang)
    try:
        _pick_a_colour(page)
        _tap_tab(page, "arrivals")
        _wait_dialog_open(page)
        with page.expect_navigation(timeout=20000):
            page.click(PRIMARY)
        page.wait_for_url("**" + layout.DISPLAY_ARRIVALS_ROUTE + "*", timeout=15000)
        page.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
        assert _stored_theme(server) != "band_red_field"
        assert "green" in _stored_theme(server)
    finally:
        context.close()


@pytest.mark.parametrize("how", ["tap", "click"])
@pytest.mark.parametrize("name,viewport,lang", PHONE_CASES, ids=PHONE_IDS)
def test_the_bottom_tab_bar_asks_before_leaving_and_saves_on_continue(
        new_context, make_app_server, name, viewport, lang, how):
    """the way out the owner used: a bottom tab-bar cell with an unsaved colour asks, and Save
    and continue stores it and lands on that tab"""
    server = make_app_server(seed=_seed_with_look)
    context, page = _open(new_context, server, viewport, lang)
    prompts = []
    page.on("dialog", lambda d: (prompts.append(d.type), d.accept()))
    try:
        start = page.url
        _pick_a_colour(page)
        _tap_bottom_tab(page, layout.HOME_ROUTE, how)
        _wait_dialog_open(page)
        assert page.url == start
        with page.expect_navigation(timeout=20000):
            page.click(PRIMARY)
        page.wait_for_url(server.base_url() + "/*", timeout=15000)
        page.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
        assert "green" in _stored_theme(server)
        assert prompts == []
    finally:
        context.close()


@pytest.mark.parametrize("name,viewport,lang", PHONE_CASES[:1], ids=PHONE_IDS[:1])
def test_the_tab_pill_stays_put_while_the_dialog_holds_the_navigation(
        new_context, make_app_server, name, viewport, lang):
    """a tab tapped with unsaved changes asks first: the pill never travels toward the tapped
    cell and back, it stays under the page the person is still on"""
    server = make_app_server(seed=_seed_with_look)
    context, page = _open(new_context, server, viewport, lang)
    try:
        _pick_a_colour(page)
        page.wait_for_function("() => !!document.querySelector('.tab-bar--slider')", timeout=10000)
        page.evaluate("""() => {
          const slider = document.querySelector('.tab-bar__slider');
          const x0 = slider.getBoundingClientRect().left;
          window.__pill = {x0: x0, far: 0, frames: 0};
          const tick = () => {
            window.__pill.far = Math.max(
              window.__pill.far, Math.abs(slider.getBoundingClientRect().left - x0));
            window.__pill.frames += 1;
            requestAnimationFrame(tick); };
          requestAnimationFrame(tick); }""")
        _tap_bottom_tab(page, layout.FLIGHTS_ROUTE)
        _wait_dialog_open(page)
        page.wait_for_function("() => window.__pill.frames > 60", timeout=10000)
        far = page.evaluate("() => window.__pill.far")
        assert far <= 1, far
    finally:
        context.close()


@pytest.mark.parametrize("name,viewport,lang", PHONE_CASES, ids=PHONE_IDS)
def test_discard_on_a_bottom_tab_leaves_without_saving(
        new_context, make_app_server, name, viewport, lang):
    """Discard goes to the tapped tab and nothing is stored"""
    server = make_app_server(seed=_seed_with_look)
    context, page = _open(new_context, server, viewport, lang)
    prompts = []
    page.on("dialog", lambda d: (prompts.append(d.type), d.accept()))
    try:
        _pick_a_colour(page)
        _tap_bottom_tab(page, layout.FLIGHTS_ROUTE)
        _wait_dialog_open(page)
        page.click(SECONDARY)
        page.wait_for_url("**" + layout.FLIGHTS_ROUTE, timeout=15000)
        assert _stored_theme(server) == "band_red_field"
        assert prompts == []
    finally:
        context.close()


@pytest.mark.parametrize("how", ["back", "history"])
def test_discard_then_the_browsers_back_shows_the_saved_values_and_no_bar(
        new_context, make_app_server, how):
    """Back after Discard returns to the Style page as it was saved: the colour the person threw
    away is not restored and the Unsaved changes bar stays hidden"""
    server = make_app_server(seed=_seed_with_look)
    context, page = _open(new_context, server, VIEWPORT_MIN_SUPPORTED, "en")
    try:
        saved = page.evaluate(
            "() => Array.from(document.querySelectorAll('form input:checked'))"
            ".map(i => i.name + '=' + i.value).sort()")
        _pick_a_colour(page)
        _tap_bottom_tab(page, layout.FLIGHTS_ROUTE)
        _wait_dialog_open(page)
        page.click(SECONDARY)
        page.wait_for_url("**" + layout.FLIGHTS_ROUTE, timeout=15000)
        page.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
        if how == "back":
            page.go_back()
        else:
            page.evaluate("() => history.back()")
        page.wait_for_url("**" + layout.DISPLAY_ROUTE, timeout=15000)
        page.wait_for_function(SETTLED, timeout=15000)
        _wait_for_bar_hidden(page)
        page.wait_for_function(
            "(saved) => JSON.stringify(Array.from(document.querySelectorAll('form input:checked'))"
            ".map(i => i.name + '=' + i.value).sort()) === JSON.stringify(saved)",
            arg=saved, timeout=5000)
    finally:
        context.close()


def test_staying_puts_the_bottom_bar_back_on_the_style_tab(new_context, make_app_server):
    """the tab bar's own highlight follows the tap and returns to Style when the person stays"""
    server = make_app_server(seed=_seed_with_look)
    context, page = _open(new_context, server, VIEWPORT_MIN_SUPPORTED, "en")
    try:
        _pick_a_colour(page)
        _tap_bottom_tab(page, layout.HOME_ROUTE)
        _wait_dialog_open(page)
        page.click(QUIET)
        _wait_dialog_closed(page)
        page.wait_for_function(
            "() => { const a = document.querySelector('.tab-bar__link--active');"
            " return !!a && a.getAttribute('href') === '%s'; }" % layout.DISPLAY_ROUTE,
            timeout=5000)
        assert _stored_theme(server) == "band_red_field"
    finally:
        context.close()


def test_the_desktop_sidebar_asks_before_leaving(new_context, make_app_server):
    """the wide screen's own navigation goes through the same question"""
    server = make_app_server(seed=_seed_with_look)
    context, page = _open(new_context, server, VIEWPORT_DESKTOP, "en")
    try:
        start = page.url
        _pick_a_colour(page)
        _tap_sidebar_link(page, layout.FLIGHTS_ROUTE)
        _wait_dialog_open(page)
        assert page.url == start
        page.click(SECONDARY)
        page.wait_for_url("**" + layout.FLIGHTS_ROUTE, timeout=15000)
        assert _stored_theme(server) == "band_red_field"
    finally:
        context.close()


def test_a_link_inside_the_open_more_sheet_asks_too(new_context, make_app_server):
    """the More sheet's own links (Account and the rest) go through the same question"""
    server = make_app_server(seed=_seed_with_look)
    context, page = _open(new_context, server, VIEWPORT_MIN_SUPPORTED, "en")
    try:
        _pick_a_colour(page)
        start = page.url
        _press(page, "details.tab-bar__more > summary")
        link = ".tab-bar__more[open] a[href]"
        page.locator(link).first.wait_for(state="visible", timeout=5000)
        _press(page, link)
        _wait_dialog_open(page)
        assert page.url == start
    finally:
        context.close()


def test_a_same_page_hash_link_is_not_intercepted(new_context, make_app_server):
    """the skip link jumps inside the page with the dialog never opening"""
    server = make_app_server(seed=_seed_with_look)
    context, page = _open(new_context, server, VIEWPORT_DESKTOP, "en")
    try:
        _pick_a_colour(page)
        page.locator('a[href^="#"]').first.evaluate("el => el.focus()")
        page.keyboard.press("Enter")
        page.wait_for_function("() => window.location.hash !== ''", timeout=5000)
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
            "() => document.activeElement && document.activeElement.hasAttribute('data-leave-dialog-quiet')",
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
