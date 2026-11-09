"""Real-browser checks of the Personalisation page (/display and its three sibling views): at 360
and 1280 px, in English and French, in both themes, nothing overflows sideways and every control
(the one navigation, the picker's colour dots, background and band segments) is at
least 44x44 and owns its own centre. Departures and Arrivals are the picker: choosing in it raises
the save bar naming Look and Save persists the look after a reload; the Arrivals address shows
its own picture and the "Same as departures" switch; the save bar's Cancel puts the saved look back; from 960 px
the picture and the picker are two columns that both fit a 1280x800 screen. The navigation links
are plain links, one view each, with a highlight that slides to the current link (and does not
under reduced motion); the retired Screen address lands on Departures; without scripts the
look views offer the native look cards and tables."""
import pytest

from companion import auth, layout
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT,
    VIEWPORT_DESKTOP,
    VIEWPORT_MIN_SUPPORTED,
    _assert_hit_target,
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
    ("look", layout.DISPLAY_ARRIVALS_ROUTE),
    ("layout", layout.DISPLAY_LAYOUT_ROUTE),
    ("special-looks", layout.DISPLAY_SPECIAL_LOOKS_ROUTE),
    ("calendar", layout.DISPLAY_CALENDAR_ROUTE),
)
LOOK_ROUTES = (layout.DISPLAY_ROUTE, layout.DISPLAY_ARRIVALS_ROUTE)
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
    if route in LOOK_ROUTES:
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
@pytest.mark.parametrize("viewport", [{"width": 390, "height": 844}, {"width": 360, "height": 740}],
                         ids=["390x844", "360x740"])
def test_the_whole_look_picker_fits_one_phone_screen_above_the_tab_bar(
        new_context, make_app_server, viewport, lang):
    """after load, with no scrolling, the picture (a little over half the width), the colour swatches, the background and band
    controls are all inside the viewport and end above the floating tab bar (on a phone as short
    as 740px only the reason under a greyed choice may run below it);
    the swatches are drawn 32px inside their 44px targets"""
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), viewport, lang=lang)
    try:
        page.wait_for_function("() => window.scrollY === 0")
        geometry = page.evaluate(
            "() => { const box = (sel) => document.querySelector(sel).getBoundingClientRect();"
            " const segments = [...document.querySelectorAll('%s .look-seg')];"
            " const dot = document.querySelector('%s .look-dot__ink').getBoundingClientRect();"
            " return {tab: box('.tab-bar').top, picker: box('%s').bottom,"
            "  segments: segments.map((s) => [s.getBoundingClientRect().bottom,"
            "    s.getBoundingClientRect().height]),"
            "  picture: box('.look-frame__picture').width, ink: dot.width, scroll: window.scrollY}; }"
            % (PICKER, PICKER, PICKER))
        assert geometry["scroll"] == 0, geometry
        # The reason a choice is greyed is written under its row and may run below the tab bar
        # on the shortest phone; every control itself stays above it.
        if viewport["height"] >= 800:
            assert geometry["picker"] <= geometry["tab"], geometry
        assert len(geometry["segments"]) == 2, geometry
        for bottom, height in geometry["segments"]:
            assert bottom <= geometry["tab"] and abs(height - 40) <= 0.5, geometry
        assert 0.45 * viewport["width"] <= geometry["picture"] <= 0.6 * viewport["width"] and geometry["ink"] == 32, geometry
        _assert_hit_target(page, PICKER + " .look-dot:first-of-type", "a colour swatch")
        _assert_hit_target(page, PICKER + " .look-seg__option", "a segment")
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("label,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_no_overflow_and_every_control_is_44px_and_reachable(
        new_context, make_app_server, label, viewport, theme, lang):
    """the look views do not scroll sideways and their nav links, colour dots and segments are at
    least 44x44 and own their centre; the Arrivals view's switch likewise; the picker has no
    Save or Reset button of its own"""
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), viewport, lang=lang, theme=theme)
    try:
        overflow = _assert_no_page_overflow(page, "personalisation", viewport["width"])
        assert not overflow, overflow
        selectors = (
            ".personalisation-nav__link", PICKER + " .look-dot",
            PICKER + " .look-seg__option")
        assert page.locator(PICKER + " button.look-sheet__save, " + PICKER
                            + " button.look-sheet__reset, " + PICKER
                            + " .look-sheet__foot").count() == 0
        for selector in selectors:
            measured = _measure(page, selector)
            assert measured, selector
            for box, owns in measured:
                assert box["width"] >= 44 - 0.5 and box["height"] >= 44 - 0.5, (selector, box)
                assert owns, selector
        page.goto(server.base_url() + layout.DISPLAY_ARRIVALS_ROUTE)
        _ready(page, layout.DISPLAY_ARRIVALS_ROUTE)
        for selector in (".personalisation-nav__link", "[data-look-same]"):
            measured = _measure(page, selector)
            assert measured, selector
            for box, owns in measured:
                assert box["width"] >= 44 - 0.5 and box["height"] >= 44 - 0.5, (selector, box)
                assert owns, selector
        # Following Departures the colour controls are hidden, not dimmed; they come back
        # (at full size) once the page has its own look.
        assert not _measure(page, PICKER + " .look-dot")
        page.click("[data-look-same]")
        page.wait_for_function(
            "() => document.querySelector('[data-look-same]').getAttribute('aria-checked') === 'false'")
        measured = _measure(page, PICKER + " .look-dot")
        assert measured
        for box, owns in measured:
            assert box["width"] >= 44 - 0.5 and box["height"] >= 44 - 0.5, box
            assert owns
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("label,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_every_view_fits_the_screen_in_both_languages_and_themes(
        new_context, make_app_server, label, viewport, theme, lang):
    """none of the five views scrolls sideways, and the navigation holds all five links with the
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
            assert links.count() == 5
            assert page.locator('.personalisation-nav__link[aria-current="page"]').count() == 1
            assert links.nth(position).get_attribute("aria-current") == "page"
    finally:
        context.close()


def test_on_a_phone_the_navigation_fits_without_scrolling_and_shows_the_current_link(
        new_context, make_app_server):
    """at 360 px the segmented control fits its column in French (no sideways scroll inside it or
    in the page) and the current link sits fully on screen"""
    server = make_app_server(seed=_seed)
    context, page = _open(
        new_context, server.base_url(), VIEWPORT_MIN_SUPPORTED, lang="fr",
        route=layout.DISPLAY_CALENDAR_ROUTE)
    try:
        assert page.evaluate(
            "() => { const n = document.querySelector('[data-pers-nav]');"
            " return n.scrollWidth <= n.clientWidth; }")
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
    """one tap in the picker raises the save bar with the one message every page uses, Save stores
    the look the picker chose and the reloaded page shows it checked and in the picture"""
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), viewport, lang=lang)
    try:
        message = "Unsaved changes" if lang == "en" else "Modifications non enregistrées"
        assert _checked_theme(page) == SAVED_LOOK
        dot = page.locator(PICKER + ' .look-dot:has(input[data-look-axis="colour"][value="blue"])')
        dot.evaluate("el => el.scrollIntoView({block: 'center'})")
        dot.click()
        _wait_for_bar(page)
        page.wait_for_function(
            "w => document.querySelector('[data-dirty-count]').textContent === w",
            arg=message, timeout=5000)
        assert _bar_text(page) == message
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


def test_the_floating_save_bar_saves_the_look(new_context, make_app_server):
    """the picker card has no Save button of its own: the floating bar's Save submits the
    settings form, the look is stored and the page returns to the Look view"""
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), VIEWPORT_DESKTOP)
    try:
        page.click(PICKER + ' .look-dot:has(input[data-look-axis="colour"][value="green"])')
        _wait_for_bar(page)
        chosen = _checked_theme(page)
        with page.expect_navigation(timeout=30000):
            page.click(".dirty-bar button[type=submit]")
        _ready(page, layout.DISPLAY_ROUTE)
        assert device_config.load_device_config(server.state_dir)["theme"] == chosen
        assert page.url.split("?")[0].endswith(layout.DISPLAY_ROUTE)
    finally:
        context.close()


@pytest.mark.parametrize("label,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_the_views_show_their_own_picture_and_cancel_restores_the_saved_look(
        new_context, make_app_server, label, viewport):
    """Departures shows its picture first; the Arrivals address shows its own picture and offers
    "Same as departures"; a choice there changes only Arrivals; Cancel puts the saved Arrivals
    look back"""
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), viewport)
    try:
        departures = page.locator('[data-look-panel="departures"]')
        arrivals = page.locator('[data-look-panel="arrivals"]')
        assert departures.is_visible() and not arrivals.is_visible()
        assert not page.locator("[data-look-same-row]").is_visible()
        link = page.locator('.personalisation-nav__link[href$="%s"]' % layout.DISPLAY_ARRIVALS_ROUTE)
        link.evaluate("el => el.scrollIntoView({block: 'center', inline: 'center'})")
        with page.expect_navigation():
            link.click()
        _ready(page, layout.DISPLAY_ARRIVALS_ROUTE)
        page.wait_for_function(
            "() => document.querySelector('[data-look-panel=\"arrivals\"]').hidden === false"
            " && document.querySelector('[data-look-panel=\"departures\"]').hidden === true",
            timeout=5000)
        assert arrivals.is_visible() and not departures.is_visible()
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
        page.click(".dirty-bar [data-dirty-cancel]")
        page.wait_for_function(
            "() => { const r = document.querySelector('input[name=\"theme_arriving\"]:checked');"
            " return !!r && r.value === ''; }", timeout=5000)
    finally:
        context.close()


def test_on_desktop_the_picture_and_the_picker_are_two_columns_that_fit_the_screen(
        new_context, make_app_server):
    """at 1280x800 the picture is on the left and the picker card on the right, side by side, and
    both end inside the first screen on Departures and on Arrivals; the picture is not tiny"""
    server = make_app_server(seed=_seed)
    viewport = {"width": 1280, "height": 800}
    for route in LOOK_ROUTES:
        context, page = _open(new_context, server.base_url(), viewport, route=route)
        try:
            boxes = page.evaluate(
                "() => { const pic = document.querySelector('.look-panel:not([hidden]) .look-frame__picture')"
                ".getBoundingClientRect(); const pick = document.querySelector('[data-look-sheet]')"
                ".getBoundingClientRect(); return {pic: [pic.left, pic.right, pic.top, pic.bottom],"
                " pick: [pick.left, pick.right, pick.top, pick.bottom]}; }")
            pic, pick = boxes["pic"], boxes["pick"]
            assert pic[1] <= pick[0] + 1, boxes
            assert pic[3] <= 800 and pick[3] <= 800, boxes
            assert pic[1] - pic[0] >= 300, boxes
            assert not _assert_no_page_overflow(page, "look", 1280)
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
        assert [links.nth(i).evaluate("el => el.tagName") for i in range(5)] == ["A"] * 5
        assert [links.nth(i).inner_text().strip() for i in range(5)] == [
            "Departures", "Arrivals", "Layout", "Special looks", "Calendar"]
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
        " return Math.abs(t.left - (l.left + 3)) < 1.5 && Math.abs(t.width - (l.width - 6)) < 1.5; }")


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


def test_the_retired_screen_address_lands_on_departures(new_context, make_app_server):
    """the old Screen address still answers: it ends on Departures with its link marked"""
    server = make_app_server(seed=_seed)
    context, page = _open(
        new_context, server.base_url(), VIEWPORT_DESKTOP, route=layout.DISPLAY_SCREEN_ROUTE)
    try:
        assert page.url.split("?")[0].endswith(layout.DISPLAY_ROUTE)
        current = page.locator('.personalisation-nav__link[aria-current="page"]')
        assert current.get_attribute("href").endswith(layout.DISPLAY_ROUTE)
    finally:
        context.close()


def test_without_scripts_the_links_work_and_the_look_view_offers_the_native_cards(
        new_context, make_app_server):
    """scripts blocked: the navigation links still open each view, the current link carries the
    highlight itself, the look cards are there, and the script-only picker is not; the Arrivals
    link opens the arrivals table"""
    server = make_app_server(seed=_seed)
    with _no_js_page(new_context, server.base_url(), layout.DISPLAY_ROUTE,
                     viewport=VIEWPORT_MIN_SUPPORTED, reduced_motion="reduce") as page:
        page.wait_for_load_state("load")
        page.locator(".look-pick__card").first.wait_for(state="visible")
        assert not page.locator(PICKER).is_visible()
        assert page.locator('input[name="theme"]:checked').get_attribute("value") == SAVED_LOOK
        background = page.evaluate(
            "() => getComputedStyle(document.querySelector("
            "'.personalisation-nav__link[aria-current] > span')).backgroundColor")
        assert background not in ("rgba(0, 0, 0, 0)", "transparent")
        link = page.locator('.personalisation-nav__link[href$="%s"]' % layout.DISPLAY_ARRIVALS_ROUTE)
        with page.expect_navigation():
            link.click()
        page.locator('[data-look-panel="arrivals"]').wait_for(state="visible")
        assert page.url.split("?")[0].endswith(layout.DISPLAY_ARRIVALS_ROUTE)
        assert not page.locator('[data-look-panel="departures"]').is_visible()


@pytest.mark.parametrize("lang,label", [("en", "Save"), ("fr", "Enregistrer")])
@pytest.mark.parametrize("label_vp,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_the_floating_bar_save_button_is_the_short_word_on_one_line(
        new_context, make_app_server, label_vp, viewport, lang, label):
    """the floating bar's Save reads just "Save" / "Enregistrer": one line, 44px tall, inside the
    bar, with Cancel beside it"""
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), viewport, lang=lang)
    try:
        page.click(PICKER + ' .look-dot:has(input[data-look-axis="colour"][value="green"])')
        _wait_for_bar(page)
        save = page.locator(".dirty-bar button.dirty-bar__save")
        page.wait_for_function(
            "() => { const b = document.querySelector('.dirty-bar');"
            " return b && b.getBoundingClientRect().height > 0; }", timeout=10000)
        assert save.inner_text().strip() == label
        box = save.bounding_box()
        assert box["height"] <= 48 and box["height"] >= 43.5, box
        bar = page.locator(".dirty-bar").bounding_box()
        assert box["x"] >= bar["x"] and box["x"] + box["width"] <= bar["x"] + bar["width"] + 0.5
        line_count = save.evaluate(
            "el => { const r = document.createRange(); r.selectNodeContents(el);"
            " return r.getClientRects().length; }")
        assert line_count == 1
    finally:
        context.close()
