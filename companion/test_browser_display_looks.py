"""Real-browser checks of the Look view's picker (/display): the colour, background and band
choices sit in the page under the Departures/Arrivals picture, swap that picture live and disable
the combinations the frame has no theme for with their reason, the dirty bar's Save persists the
new look, "Same as departures" follows departures, and nothing overflows at 1280, 390 and 360 px.
On the Calendar view the same sheet is still a labelled dialog (a bottom sheet on phones) that
traps focus, closes on Escape and returns focus to its opener; on the Special looks view "Add a
special look" becomes a dialog whose choices post a real rule."""
from urllib.parse import urlsplit

import pytest

from companion import auth, layout
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP,
    VIEWPORT_MIN_SUPPORTED,
    VIEWPORT_PHONE,
    _assert_no_page_overflow,
    _login,
    _save_via_bar,
    seed_state_dir,
)
from server import device_config
from server.plane import colour_rules

pytestmark = pytest.mark.browser

SHEET = "[data-look-sheet]"
DEPARTURES = '[data-look-usage="departures"]'
ARRIVALS = '[data-look-usage="arrivals"]'
CALENDAR_OPENER = '[data-look-usage="calendar"] button.look-frame__open'


def _seed(state_dir):
    seed_state_dir(state_dir)
    device_config.save_device_config(state_dir, theme="band_red_field")


def _open_display(new_context, base_url, viewport, lang="en", route=layout.DISPLAY_ROUTE):
    context = new_context(viewport=viewport)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
    page = context.new_page()
    _login(page, base_url)
    page.goto(base_url + route)
    if route in (layout.DISPLAY_ROUTE, layout.DISPLAY_ARRIVALS_ROUTE):
        page.locator(SHEET + "[data-look-inline]").wait_for(state="visible")
    elif route == layout.DISPLAY_CALENDAR_ROUTE:
        page.locator(CALENDAR_OPENER).wait_for(state="visible")
    else:
        page.locator(".special-add__summary").wait_for(state="visible")
    page.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
    return context, page


def _show_tab(page, usage):
    """Opens the Departures or Arrivals view through the navigation (a new page), unless it is
    the one shown, and waits for its picture and picker."""
    link = page.locator('[data-pers-view="%s"]' % usage)
    if link.get_attribute("aria-current") != "page":
        with page.expect_navigation():
            link.click()
    page.locator(SHEET + "[data-look-inline]").wait_for(state="visible")
    page.wait_for_function(
        "u => document.querySelector('[data-look-panel=\"' + u + '\"]').hidden === false"
        " && document.readyState === 'complete'", arg=usage, timeout=10000)


def _axis(axis, value):
    return '%s .look-seg__option:has(input[data-look-axis="%s"][value="%s"]), ' \
           '%s .look-dot:has(input[data-look-axis="%s"][value="%s"])' % (
               SHEET, axis, value, SHEET, axis, value)


def _picture_src(page, usage_selector):
    return page.locator(usage_selector + " img.look-frame__image").get_attribute("src")


def _checked(page, field):
    return page.evaluate(
        "f => (([...document.querySelectorAll('input')].find(e => e.name === f && e.checked))"
        " || {}).value", field)


def test_picker_choices_swap_the_picture_live(new_context, make_app_server):
    """the picker sits in the page beside the departures picture with the saved look's three
    choices checked; choosing Blue checks the band_blue_field radio, swaps the picture's src to
    that theme's full-frame preview, rewrites the read-back, raises the dirty bar, and the image
    really loads"""
    server = make_app_server(seed=_seed)
    context, page = _open_display(new_context, server.base_url(), VIEWPORT_DESKTOP)
    try:
        sheet = page.locator(SHEET)
        assert sheet.get_attribute("role") is None
        for axis, value in (("colour", "red"), ("background", "soft"), ("stripe", "solid")):
            assert page.is_checked('%s input[data-look-axis="%s"][value="%s"]' % (SHEET, axis, value))
        picture = page.locator(DEPARTURES + " .look-frame__picture").bounding_box()
        box = sheet.bounding_box()
        assert box["x"] >= picture["x"] + picture["width"] - 0.5, "expected the picker beside the picture"

        page.click(_axis("colour", "blue"))
        assert _checked(page, "theme") == "band_blue_field"
        src = _picture_src(page, DEPARTURES)
        assert src.startswith("/frame-preview/band_blue_field.png?state=departing")
        assert page.locator(DEPARTURES + " [data-look-sentence]").inner_text() == "Blue, stripe on soft"
        page.wait_for_function(
            "() => { const i = document.querySelector('%s img.look-frame__image');"
            " return i.complete && i.naturalWidth === 600; }" % DEPARTURES)
        page.locator("[data-dirty-bar]").wait_for(state="visible")
        # Arrivals follow departures until they get a look of their own.
        assert _picture_src(page, ARRIVALS).startswith("/frame-preview/band_blue_field.png?state=arriving")
    finally:
        context.close()


def test_combinations_without_a_theme_are_disabled_with_their_reason(new_context, make_app_server):
    """with a soft background both stripe options stay offered except the soft one, disabled
    with the soft-on-soft reason; yellow disables every stripe with the white-on-yellow reason;
    a full background disables every stripe; the disabled options are skipped, never hidden"""
    server = make_app_server(seed=_seed)
    context, page = _open_display(new_context, server.base_url(), VIEWPORT_DESKTOP)
    try:
        _show_tab(page, "arrivals")
        page.locator(SHEET + " button.switch").wait_for(state="visible")
        page.click(SHEET + " button.switch")
        assert page.locator(SHEET + " button.switch").get_attribute("aria-checked") == "false"
        why = page.locator(SHEET + " [data-look-why]")

        def disabled():
            return page.evaluate(
                "s => [...document.querySelectorAll(s + ' input[data-look-axis=stripe]')]"
                ".filter(e => e.disabled).map(e => e.value)", SHEET)

        assert disabled() == ["soft"] and "soft background" in why.inner_text()
        page.click(_axis("colour", "yellow"))
        assert disabled() == ["solid", "soft"] and "yellow" in why.inner_text()
        assert _checked(page, "theme_arriving") == "yellow_light"
        page.click(_axis("colour", "red"))
        page.click(_axis("background", "full"))
        assert disabled() == ["solid", "soft"] and "full background" in why.inner_text()
        assert _checked(page, "theme_arriving") == "red"
        assert page.locator(SHEET + " .look-seg__option.is-disabled").count() == 2
        assert page.locator(SHEET + " .look-seg__option.is-disabled").first.is_visible()
    finally:
        context.close()


def test_calendar_sheet_traps_focus_closes_on_escape_and_returns_focus(new_context, make_app_server):
    """on the Calendar view the look sheet is still a dialog: opened from the keyboard it takes
    focus, Tab and Shift+Tab stay inside it, Escape closes it and focus returns to the control
    that opened it; Reset restores the look that was there when it opened"""
    server = make_app_server(seed=_seed)
    context, page = _open_display(
        new_context, server.base_url(), VIEWPORT_DESKTOP, route=layout.DISPLAY_CALENDAR_ROUTE)
    try:
        page.focus(CALENDAR_OPENER)
        page.keyboard.press("Enter")
        page.locator(SHEET).wait_for(state="visible")
        assert page.locator(SHEET).get_attribute("role") == "dialog"
        inside = "() => document.querySelector('%s').contains(document.activeElement)" % SHEET
        page.wait_for_function(inside, timeout=5000)
        for _ in range(12):
            page.keyboard.press("Tab")
            page.wait_for_function(inside, timeout=5000)
        for _ in range(12):
            page.keyboard.press("Shift+Tab")
            page.wait_for_function(inside, timeout=5000)
        assert page.locator(SHEET + " button.switch").get_attribute("aria-checked") == "true"
        before = _checked(page, "calendar_theme_id")
        page.click(SHEET + " button.switch")
        page.click(_axis("colour", "green"))
        page.wait_for_function(
            "b => { const r = [...document.querySelectorAll('input')].find("
            "e => e.name === 'calendar_theme_id' && e.checked); return !!r && r.value !== b; }",
            arg=before, timeout=5000)
        page.click(SHEET + " [data-look-reset]")
        page.wait_for_function(
            "b => { const r = [...document.querySelectorAll('input')].find("
            "e => e.name === 'calendar_theme_id' && e.checked); return !!r && r.value === b; }",
            arg=before, timeout=5000)
        page.keyboard.press("Escape")
        page.locator(SHEET).wait_for(state="hidden")
        page.wait_for_function(
            "s => document.activeElement === document.querySelector(s)", arg=CALENDAR_OPENER,
            timeout=5000)
    finally:
        context.close()


def test_save_bar_persists_the_new_look_and_same_as_departures(new_context, make_app_server):
    """a look chosen in the picker is saved by the dirty bar's Save through the unchanged settings
    form, for departures and for an arrivals override, and turning "Same as departures" back on
    saves the clear signal"""
    server = make_app_server(seed=_seed)
    context, page = _open_display(new_context, server.base_url(), VIEWPORT_DESKTOP)
    try:
        page.click(_axis("colour", "green"))
        page.click(_axis("background", "paper"))
        page.click(_axis("stripe", "soft"))
        _save_via_bar(page, timeout=30000)
        assert device_config.load_device_config(server.state_dir)["theme"] == "band_green_light"
        assert urlsplit(page.url).path == layout.DISPLAY_ROUTE
        assert page.locator(DEPARTURES + " [data-look-sentence]").inner_text() == "Green, soft stripe"

        _show_tab(page, "arrivals")
        page.click(SHEET + " button.switch")
        page.click(_axis("colour", "black"))
        page.click(_axis("background", "soft"))
        _save_via_bar(page, timeout=30000)
        saved = device_config.load_device_config(server.state_dir)
        assert (saved["theme"], saved["theme_arriving"]) == ("band_green_light", "grey")
        assert urlsplit(page.url).path == layout.DISPLAY_ARRIVALS_ROUTE

        page.locator(SHEET + "[data-look-inline]").wait_for(state="visible")
        page.click(SHEET + " button.switch")
        assert page.locator(SHEET + " button.switch").get_attribute("aria-checked") == "true"
        _save_via_bar(page, timeout=30000)
        assert device_config.load_device_config(server.state_dir)["theme_arriving"] is None
    finally:
        context.close()


def test_add_a_special_look_is_a_dialog_that_posts_a_rule(new_context, make_app_server):
    """with scripts, "Add a special look" opens a modal dialog whose table gives way to the three
    choices; a suggestion fills the key, the choices pick the theme, the mini render follows,
    Escape closes it, and submitting adds the rule with that look"""
    server = make_app_server(seed=_seed)
    context, page = _open_display(
        new_context, server.base_url(), VIEWPORT_DESKTOP, route=layout.DISPLAY_SPECIAL_LOOKS_ROUTE)
    try:
        page.click(".special-add__summary")
        panel = page.locator(".special-add__panel")
        panel.wait_for(state="visible")
        assert panel.get_attribute("role") == "dialog"
        assert not page.locator("[data-look-table-host]").is_visible()
        # The panel handles Escape only while focus is inside it, and the script moves focus there
        # from the details toggle event, which the browser queues as a task after the click.
        page.wait_for_function(
            "() => document.querySelector('.special-add__panel').contains(document.activeElement)")
        page.keyboard.press("Escape")
        page.wait_for_function("() => !document.querySelector('.special-add').open")
        page.click(".special-add__summary")
        page.click('label[for="rule-kind-prefix"]')
        page.click('.rule-suggestion-chip[data-kind="prefix"]')
        assert page.input_value("#rule-key") == "AFR"
        host = "[data-look-axes-host]"
        page.click('%s .look-dot:has(input[value="blue"])' % host)
        page.click('%s .look-seg__option:has(input[data-look-axis="background"][value="paper"])' % host)
        page.click('%s .look-seg__option:has(input[data-look-axis="stripe"][value="soft"])' % host)
        assert _checked(page, "rule_theme_id") == "band_blue_light"
        assert page.locator(".special-add__preview img").get_attribute("src").startswith(
            "/frame-preview/band_blue_light.png")
        with page.expect_navigation():
            page.click('.special-add__foot button[type="submit"]')
        rows = colour_rules.rule_rows(colour_rules.load_colour_rules(server.state_dir))
        assert ("prefix", "AFR", "band_blue_light") in [row[:3] for row in rows]
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED], ids=["390", "360"])
def test_on_phones_the_calendar_sheet_is_a_bottom_sheet_and_nothing_overflows(
        new_context, make_app_server, viewport):
    """on a phone the Calendar view's sheet is pinned to the bottom of the viewport at full width
    over a dimmed page, every choice is at least 44px tall, and neither the page nor the open sheet
    scrolls sideways"""
    server = make_app_server(seed=_seed)
    context, page = _open_display(
        new_context, server.base_url(), viewport, route=layout.DISPLAY_CALENDAR_ROUTE)
    try:
        overflow = _assert_no_page_overflow(page, "calendar", viewport["width"])
        assert not overflow, overflow
        page.click(CALENDAR_OPENER)
        sheet = page.locator(SHEET)
        sheet.wait_for(state="visible")
        # The sheet slides in: measure it only once its finite animations have ended.
        page.wait_for_function(
            "() => document.getAnimations().every((a) => (a.effect && a.effect.getComputedTiming()"
            ".iterations === Infinity) || a.playState !== 'running')", timeout=10000)
        box = sheet.bounding_box()
        assert abs(box["x"]) < 1 and abs(box["width"] - viewport["width"]) < 1
        assert abs(box["y"] + box["height"] - viewport["height"]) < 1
        assert page.locator("[data-look-scrim]").is_visible()
        for selector in (SHEET + " .look-dot", SHEET + " .look-seg__option"):
            for handle in page.locator(selector).all():
                assert handle.bounding_box()["height"] >= 44
        assert page.evaluate("s => document.querySelector(s).scrollWidth <= document.querySelector(s).clientWidth", SHEET)
        overflow = _assert_no_page_overflow(page, "calendar with the sheet", viewport["width"])
        assert not overflow, overflow
        page.click("[data-look-scrim]", position={"x": 10, "y": 10})
        sheet.wait_for(state="hidden")
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED], ids=["390", "360"])
def test_on_phones_the_picker_sits_under_the_picture_and_nothing_overflows(
        new_context, make_app_server, viewport):
    """on a phone the Look view shows the small picture beside its read-back, the picker as a card
    in the page at the full content width, every choice at least 44px tall, and no sideways scroll,
    on both tabs"""
    server = make_app_server(seed=_seed)
    context, page = _open_display(new_context, server.base_url(), viewport)
    try:
        for usage in ("departures", "arrivals"):
            _show_tab(page, usage)
            overflow = _assert_no_page_overflow(page, "look " + usage, viewport["width"])
            assert not overflow, overflow
            picture = page.locator('[data-look-panel="%s"] .look-frame__picture' % usage).bounding_box()
            caption = page.locator('[data-look-panel="%s"] .look-frame__caption' % usage).bounding_box()
            assert caption["x"] >= picture["x"] + picture["width"] - 0.5, "expected the read-back beside the picture"
            sheet = page.locator(SHEET).bounding_box()
            assert sheet["y"] >= picture["y"] + picture["height"] - 0.5
            assert sheet["x"] >= 0 and sheet["x"] + sheet["width"] <= viewport["width"] + 0.5
            for selector in (SHEET + " .look-dot", SHEET + " .look-seg__option"):
                for handle in page.locator(selector).all():
                    assert handle.bounding_box()["height"] >= 44
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_desktop_layout_has_no_overflow_and_44px_targets(new_context, make_app_server, lang):
    """at 1280px a look view is two columns: the picture with its read-back on the left, the picker
    card on the right and level with it; the page does not scroll sideways, and every choice is
    at least 44px in both directions"""
    server = make_app_server(seed=_seed)
    context, page = _open_display(new_context, server.base_url(), VIEWPORT_DESKTOP, lang=lang)
    try:
        overflow = _assert_no_page_overflow(page, "display", VIEWPORT_DESKTOP["width"])
        assert not overflow, overflow
        picture = page.locator(DEPARTURES + " .look-frame__picture").bounding_box()
        sheet = page.locator(SHEET).bounding_box()
        assert picture["x"] + picture["width"] <= sheet["x"] + 0.5
        assert abs(picture["y"] - sheet["y"]) < 30
        assert not page.locator(DEPARTURES + " .look-pick__grid").is_visible()
        for selector in (
                ".personalisation-nav__link", SHEET + " .look-dot", SHEET + " .look-seg__option",
                SHEET + " .look-sheet__reset", SHEET + " .look-sheet__save"):
            for handle in page.locator(selector).all():
                box = handle.bounding_box()
                assert box["height"] >= 44 - 0.5 and box["width"] >= 44 - 0.5, (selector, box)
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED], ids=["390", "360"])
def test_the_new_special_look_sheet_has_a_big_preview_and_fits_a_phone(
        new_context, make_app_server, viewport):
    """on a phone the New special look sheet opens with its preview taking at least 40% of the
    sheet's width, the sheet stays inside the screen and scrolls inside itself, and its primary
    button is on screen without scrolling the page"""
    server = make_app_server(seed=_seed)
    context, page = _open_display(
        new_context, server.base_url(), viewport, route=layout.DISPLAY_SPECIAL_LOOKS_ROUTE)
    try:
        page.click(".special-add__summary")
        panel = page.locator(".special-add__panel")
        panel.wait_for(state="visible")
        page.wait_for_function(
            "() => document.readyState === 'complete' && document.getAnimations().every("
            "a => a.playState !== 'running')", timeout=10000)
        sheet = panel.bounding_box()
        picture = page.locator(".special-add__preview .special-row__mini").bounding_box()
        assert picture["width"] >= 0.4 * sheet["width"] - 1, (picture, sheet)
        assert sheet["y"] >= 0 and sheet["y"] + sheet["height"] <= viewport["height"] + 0.5
        add = page.locator(".special-add__foot button[type=submit]").bounding_box()
        assert add["height"] >= 44 - 0.5
        assert add["y"] >= sheet["y"] and add["y"] + add["height"] <= viewport["height"] + 0.5
        assert not _assert_no_page_overflow(page, "special look sheet", viewport["width"])
    finally:
        context.close()
