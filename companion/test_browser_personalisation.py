"""Real-browser checks of the Personalisation page (/display and its three sibling views): at 360
and 1280 px, in English and French, in both themes, nothing overflows sideways and every control
(the section navigation, the Departures/Arrivals tabs, the picker's colour dots, background and
band segments, Reset, Save, the Screen switch) is at least 44x44 and owns its own centre. The
Look view is the picker: choosing in it raises the save bar naming Look and Save persists the
look after a reload; the tabs switch the picture and the picker between Departures and Arrivals;
Reset puts the saved look back. The navigation links are plain links, one view each, with a
highlight that slides to the current link (and does not under reduced motion); without scripts
the Look view offers the native look cards and tables."""
import pytest

from companion import auth, layout
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT,
    VIEWPORT_DESKTOP,
    VIEWPORT_MIN_SUPPORTED,
    _assert_no_page_overflow,
    _bar_text,
    _login,
    _no_js_page,
    _save_via_bar,
    _set_ui_theme,
    _wait_for_bar,
    seed_state_dir,
)
from server import device_config

pytestmark = pytest.mark.browser

VIEWPORTS = (("360", VIEWPORT_MIN_SUPPORTED), ("1280", VIEWPORT_DESKTOP))
VIEW_ROUTES = (
    ("look", layout.DISPLAY_ROUTE),
    ("special-looks", layout.DISPLAY_SPECIAL_LOOKS_ROUTE),
    ("calendar", layout.DISPLAY_CALENDAR_ROUTE),
    ("screen", layout.DISPLAY_SCREEN_ROUTE),
)
SAVED_LOOK = "band_red_field"
PICKER = "[data-look-sheet][data-look-inline]"
THUMB = "[data-pers-thumb]"

_OWNS_CENTRE = (
    "el => { const r = el.getBoundingClientRect();"
    " const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);"
    " return !!hit && (hit === el || el.contains(hit) || hit.contains(el)); }")
_SETTLED = (
    "() => document.readyState === 'complete'"
    " && document.getAnimations().every(a => a.effect && a.effect.getTiming().iterations !== Infinity"
    " ? a.playState !== 'running' : true)")


def _seed(state_dir):
    seed_state_dir(state_dir)
    device_config.save_device_config(state_dir, theme=SAVED_LOOK)


def _ready(page, route):
    """Waits for the view's own main control, then for the page to settle."""
    page.wait_for_function(_SETTLED, timeout=15000)
    page.locator(".personalisation-nav.is-enhanced").wait_for(state="visible")
    if route == layout.DISPLAY_ROUTE:
        page.locator(PICKER).wait_for(state="visible")
    page.wait_for_function(_SETTLED, timeout=15000)


def _open(new_context, base_url, viewport, lang="en", theme="light", route=layout.DISPLAY_ROUTE,
          **context_options):
    context = new_context(viewport=viewport, **context_options)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
    page = context.new_page()
    _login(page, base_url)
    page.goto(base_url + route)
    _ready(page, route)
    # Reduced motion leaves a 0.01 ms colour transition that the theme probe would read mid-way.
    if theme is not None:
        _set_ui_theme(page, theme)
    return context, page


def _measure(page, selector):
    """Every visible match of `selector`, scrolled to the middle of the screen, as (box, owns_centre)."""
    out = []
    handles = page.locator(selector)
    for index in range(handles.count()):
        handle = handles.nth(index)
        if not handle.is_visible():
            continue
        handle.evaluate("el => el.scrollIntoView({block: 'center', inline: 'center'})")
        page.wait_for_function(
            "el => { const r = el.getBoundingClientRect();"
            " const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);"
            " return !!hit && (hit === el || el.contains(hit) || hit.contains(el)); }",
            arg=handle.element_handle(), timeout=10000)
        out.append((handle.bounding_box(), handle.evaluate(_OWNS_CENTRE)))
    return out


def _checked_theme(page):
    return page.evaluate(
        "() => { const r = document.querySelector('input[name=\"theme\"]:checked');"
        " return r ? r.value : null; }")


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("label,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_no_overflow_and_every_control_is_44px_and_reachable(
        new_context, make_app_server, label, viewport, theme, lang):
    """the Look view does not scroll sideways and its nav links, tabs, colour dots, segments, Reset
    and Save are at least 44x44 and own their centre; the Screen view's switch likewise"""
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), viewport, lang=lang, theme=theme)
    try:
        overflow = _assert_no_page_overflow(page, "personalisation", viewport["width"])
        assert not overflow, overflow
        selectors = (
            ".personalisation-nav__link", ".look-tabs__tab", PICKER + " .look-dot",
            PICKER + " .look-seg__option", PICKER + " .look-sheet__reset",
            PICKER + " .look-sheet__save")
        for selector in selectors:
            measured = _measure(page, selector)
            assert measured, selector
            for box, owns in measured:
                assert box["width"] >= 44 - 0.5 and box["height"] >= 44 - 0.5, (selector, box)
                assert owns, selector
        page.goto(server.base_url() + layout.DISPLAY_SCREEN_ROUTE)
        _ready(page, layout.DISPLAY_SCREEN_ROUTE)
        for selector in (".personalisation-nav__link", "#personalisation-screen button.switch"):
            measured = _measure(page, selector)
            assert measured, selector
            for box, owns in measured:
                assert box["width"] >= 44 - 0.5 and box["height"] >= 44 - 0.5, (selector, box)
                assert owns, selector
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("label,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_every_view_fits_the_screen_in_both_languages_and_themes(
        new_context, make_app_server, label, viewport, theme, lang):
    """none of the four views scrolls sideways, and the navigation holds all four links with the
    current view marked"""
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), viewport, lang=lang, theme=theme)
    try:
        for position, (slug, route) in enumerate(VIEW_ROUTES):
            if route != layout.DISPLAY_ROUTE:
                page.goto(server.base_url() + route)
                _ready(page, route)
            overflow = _assert_no_page_overflow(page, slug, viewport["width"])
            assert not overflow, overflow
            links = page.locator(".personalisation-nav__link")
            assert links.count() == 4
            assert page.locator('.personalisation-nav__link[aria-current="page"]').count() == 1
            assert links.nth(position).get_attribute("aria-current") == "page"
    finally:
        context.close()


def test_on_a_phone_the_navigation_scrolls_sideways_inside_itself_and_shows_the_current_link(
        new_context, make_app_server):
    """at 360 px the pill bar is wider than the screen, scrolls inside itself (the page does not),
    and the current link is scrolled into view"""
    server = make_app_server(seed=_seed)
    context, page = _open(
        new_context, server.base_url(), VIEWPORT_MIN_SUPPORTED, lang="fr",
        route=layout.DISPLAY_SCREEN_ROUTE)
    try:
        assert page.evaluate(
            "() => { const n = document.querySelector('[data-pers-nav]');"
            " return n.scrollWidth > n.clientWidth && getComputedStyle(n).overflowX !== 'visible'; }")
        page.wait_for_function(
            "() => { const l = document.querySelector('.personalisation-nav__link[aria-current]');"
            " const r = l.getBoundingClientRect();"
            " return r.left >= 0 && r.right <= window.innerWidth; }", timeout=10000)
        assert not _assert_no_page_overflow(page, "navigation", VIEWPORT_MIN_SUPPORTED["width"])
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("label,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_choosing_in_the_picker_raises_the_bar_naming_look_and_save_persists_it(
        new_context, make_app_server, label, viewport, lang):
    """one tap in the picker raises the save bar naming the Look section, Save stores the look the
    picker chose and the reloaded page shows it checked and in the picture"""
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), viewport, lang=lang)
    try:
        look_word = "Look" if lang == "en" else "Allure"
        assert _checked_theme(page) == SAVED_LOOK
        dot = page.locator(PICKER + ' .look-dot:has(input[data-look-axis="colour"][value="blue"])')
        dot.evaluate("el => el.scrollIntoView({block: 'center'})")
        dot.click()
        _wait_for_bar(page)
        page.wait_for_function(
            "w => document.querySelector('[data-dirty-count]').textContent.startsWith(w)",
            arg=look_word, timeout=5000)
        assert _bar_text(page).startswith(look_word)
        chosen = _checked_theme(page)
        assert chosen and chosen != SAVED_LOOK and "blue" in chosen
        page.wait_for_function(
            "t => document.querySelector('.look-pick [data-look-image]').getAttribute('src')"
            ".indexOf(t) !== -1", arg=chosen, timeout=5000)
        _save_via_bar(page, timeout=30000)
        assert device_config.load_device_config(server.state_dir)["theme"] == chosen
        _ready(page, layout.DISPLAY_ROUTE)
        assert _checked_theme(page) == chosen
        assert page.is_checked(
            PICKER + ' input[data-look-axis="colour"][value="blue"]')
    finally:
        context.close()


def test_the_inline_save_button_saves_the_look(new_context, make_app_server):
    """the Save button in the picker card submits the settings form: the look is stored and the
    page returns to the Look view"""
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), VIEWPORT_DESKTOP)
    try:
        page.click(PICKER + ' .look-dot:has(input[data-look-axis="colour"][value="green"])')
        _wait_for_bar(page)
        chosen = _checked_theme(page)
        with page.expect_navigation(timeout=30000):
            page.click(PICKER + " button.look-sheet__save")
        _ready(page, layout.DISPLAY_ROUTE)
        assert device_config.load_device_config(server.state_dir)["theme"] == chosen
        assert page.url.split("?")[0].endswith(layout.DISPLAY_ROUTE)
    finally:
        context.close()


@pytest.mark.parametrize("label,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_the_tabs_switch_the_picture_and_the_picker_and_reset_restores_the_saved_look(
        new_context, make_app_server, label, viewport):
    """Departures is shown first; Arrivals shows its own picture and offers "Same as departures";
    a choice there changes only Arrivals; Reset puts the saved Arrivals look back"""
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), viewport)
    try:
        departures = page.locator('[data-look-panel="departures"]')
        arrivals = page.locator('[data-look-panel="arrivals"]')
        assert departures.is_visible() and not arrivals.is_visible()
        assert page.locator('[data-look-tab="departures"]').get_attribute("aria-pressed") == "true"
        assert not page.locator("[data-look-same-row]").is_visible()
        page.click('[data-look-tab="arrivals"]')
        page.wait_for_function(
            "() => document.querySelector('[data-look-panel=\"arrivals\"]').hidden === false"
            " && document.querySelector('[data-look-panel=\"departures\"]').hidden === true",
            timeout=5000)
        assert page.locator('[data-look-tab="arrivals"]').get_attribute("aria-pressed") == "true"
        page.locator("[data-look-same-row]").wait_for(state="visible")
        assert page.get_attribute("[data-look-same]", "aria-checked") == "true"
        assert page.locator(PICKER + ' input[data-look-axis="colour"][value="green"]').is_disabled()
        page.click("[data-look-same]")
        page.wait_for_function(
            "() => document.querySelector('[data-look-same]').getAttribute('aria-checked') === 'false'"
            " && !document.querySelector('[data-look-sheet] fieldset').disabled", timeout=5000)
        page.click(PICKER + ' .look-dot:has(input[data-look-axis="colour"][value="green"])')
        _wait_for_bar(page)
        page.wait_for_function(
            "() => { const r = document.querySelector('input[name=\"theme_arriving\"]:checked');"
            " return !!r && r.value.indexOf('green') !== -1; }", timeout=5000)
        assert _checked_theme(page) == SAVED_LOOK
        page.click(PICKER + " button.look-sheet__reset")
        page.wait_for_function(
            "() => { const r = document.querySelector('input[name=\"theme_arriving\"]:checked');"
            " return !!r && r.value === ''; }", timeout=5000)
        page.click('[data-look-tab="departures"]')
        page.wait_for_function(
            "() => document.querySelector('[data-look-panel=\"departures\"]').hidden === false",
            timeout=5000)
        assert page.is_checked(PICKER + ' input[data-look-axis="colour"][value="red"]')
    finally:
        context.close()


def test_the_picker_is_in_the_page_not_a_dialog(new_context, make_app_server):
    """the picker never covers the page: no scrim, no dialog role, Escape leaves it where it is
    and the page behind it stays reachable"""
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), VIEWPORT_MIN_SUPPORTED)
    try:
        assert page.get_attribute("[data-look-sheet]", "role") is None
        assert not page.locator("[data-look-scrim]").is_visible()
        position = page.evaluate("() => getComputedStyle(document.querySelector('[data-look-sheet]')).position")
        assert position == "static"
        page.focus(PICKER + ' input[data-look-axis="colour"][value="red"]')
        page.keyboard.press("Escape")
        assert page.locator(PICKER).is_visible()
        page.focus(".personalisation-nav__link")
        page.wait_for_function(
            "() => document.activeElement && document.activeElement.matches('.personalisation-nav__link')",
            timeout=5000)
    finally:
        context.close()


@pytest.mark.parametrize("label,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_the_navigation_links_are_plain_links_one_view_each(
        new_context, make_app_server, label, viewport):
    """each link opens its own view at its own address, and the current link follows"""
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), viewport, theme=None, reduced_motion="reduce")
    try:
        links = page.locator(".personalisation-nav__link")
        assert [links.nth(i).evaluate("el => el.tagName") for i in range(4)] == ["A"] * 4
        for position, (slug, route) in enumerate(VIEW_ROUTES):
            if route == layout.DISPLAY_ROUTE:
                continue
            link = page.locator('.personalisation-nav__link[href$="%s"]' % route)
            link.evaluate("el => el.scrollIntoView({block: 'center', inline: 'center'})")
            with page.expect_navigation():
                link.click()
            _ready(page, route)
            assert page.url.split("?")[0].endswith(route)
            assert page.locator("#personalisation-%s" % slug).count() == 1
            current = page.locator('.personalisation-nav__link[aria-current="page"]')
            assert current.get_attribute("href").endswith(route)
    finally:
        context.close()


def _thumb_covers_current_link(page):
    return page.evaluate(
        "() => { const t = document.querySelector('[data-pers-thumb]').getBoundingClientRect();"
        " const l = document.querySelector('.personalisation-nav__link[aria-current]')"
        ".getBoundingClientRect();"
        " return Math.abs(t.left - l.left) < 1.5 && Math.abs(t.width - l.width) < 1.5; }")


def test_the_highlight_slides_to_the_current_link(new_context, make_app_server):
    """after a click the new page starts the highlight under the link that was left and slides it
    to the current one (a transition on the thumb), ending exactly under the current link"""
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), VIEWPORT_DESKTOP, theme=None,
        reduced_motion="no-preference")
    try:
        page.wait_for_function(
            "() => !document.querySelector('[data-pers-thumb]').classList.contains('is-sliding')",
            timeout=5000)
        assert _thumb_covers_current_link(page)
        page.evaluate(
            "() => { window.__slid = false; }")
        with page.expect_navigation():
            page.click('.personalisation-nav__link[href$="%s"]' % layout.DISPLAY_CALENDAR_ROUTE)
        page.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
        page.wait_for_function(
            "() => document.querySelector('[data-pers-thumb]').classList.contains('is-sliding')",
            timeout=5000)
        assert page.evaluate(
            "() => parseFloat(getComputedStyle(document.querySelector('[data-pers-thumb]'))"
            ".transitionDuration) > 0")
        page.wait_for_function(
            "() => document.getAnimations().every(a => a.playState !== 'running'"
            " || a.effect.getTiming().iterations === Infinity)", timeout=10000)
        assert _thumb_covers_current_link(page)
    finally:
        context.close()


def test_under_reduced_motion_the_highlight_does_not_slide(new_context, make_app_server):
    """with prefers-reduced-motion the highlight sits under the current link at once: no sliding
    class, no transition time"""
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), VIEWPORT_DESKTOP, theme=None, reduced_motion="reduce")
    try:
        with page.expect_navigation():
            page.click('.personalisation-nav__link[href$="%s"]' % layout.DISPLAY_CALENDAR_ROUTE)
        _ready(page, layout.DISPLAY_CALENDAR_ROUTE)
        assert not page.evaluate(
            "() => document.querySelector('[data-pers-thumb]').classList.contains('is-sliding')")
        assert page.evaluate(
            "() => parseFloat(getComputedStyle(document.querySelector('[data-pers-thumb]'))"
            ".transitionDuration) < 0.001")
        assert _thumb_covers_current_link(page)
    finally:
        context.close()


def test_without_scripts_the_links_work_and_the_look_view_offers_the_native_cards(
        new_context, make_app_server):
    """scripts blocked: the navigation links still open each view, the current link carries the
    highlight itself, the look cards and the arrivals table are there, and the script-only tabs
    and picker are not"""
    server = make_app_server(seed=_seed)
    with _no_js_page(new_context, server.base_url(), layout.DISPLAY_ROUTE,
                     viewport=VIEWPORT_MIN_SUPPORTED, reduced_motion="reduce") as page:
        page.wait_for_load_state("load")
        page.locator(".look-pick__card").first.wait_for(state="visible")
        assert not page.locator(".look-tabs").is_visible()
        assert not page.locator(PICKER).is_visible()
        assert page.locator('input[name="theme"]:checked').get_attribute("value") == SAVED_LOOK
        background = page.evaluate(
            "() => getComputedStyle(document.querySelector('.personalisation-nav__link[aria-current]'))"
            ".backgroundColor")
        assert background not in ("rgba(0, 0, 0, 0)", "transparent")
        link = page.locator('.personalisation-nav__link[href$="%s"]' % layout.DISPLAY_SCREEN_ROUTE)
        with page.expect_navigation():
            link.click()
        page.locator("#personalisation-screen").wait_for(state="visible")
        assert page.url.split("?")[0].endswith(layout.DISPLAY_SCREEN_ROUTE)
