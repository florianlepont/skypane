"""Real-browser checks of the Display page's look picker: clicking a
picture opens the look sheet as a labelled dialog beside it (a bottom sheet
on phones), the three choices swap the big picture live and disable the
combinations the frame has no theme for with their reason, the dialog traps
focus, closes on Escape and returns focus to its opener, the dirty bar's
Save persists the new look, "Same as departures" follows departures, the
"Add a special look" form becomes a dialog whose choices post a real rule,
and nothing overflows at 1280, 390 and 360 px."""
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


def _seed(state_dir):
    seed_state_dir(state_dir)
    device_config.save_device_config(state_dir, theme="band_red_field")


def _open_display(new_context, base_url, viewport, lang="en"):
    context = new_context(viewport=viewport)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
    page = context.new_page()
    _login(page, base_url)
    page.goto(base_url + layout.DISPLAY_ROUTE)
    page.locator(DEPARTURES + " button.look-frame__open").wait_for(state="visible")
    return context, page


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


def test_picture_opens_the_sheet_and_choices_swap_the_picture_live(new_context, make_app_server):
    """clicking the departures picture opens the sheet as a visible, labelled dialog beside the
    picture with the saved look's three choices checked; choosing Blue checks the band_blue_field
    radio, swaps the picture's src to that theme's full-frame preview, rewrites the read-back,
    raises the dirty bar, and the image really loads"""
    server = make_app_server(seed=_seed)
    context, page = _open_display(new_context, server.base_url(), VIEWPORT_DESKTOP)
    try:
        page.click(DEPARTURES + " button.look-frame__open")
        sheet = page.locator(SHEET)
        sheet.wait_for(state="visible")
        assert sheet.get_attribute("role") == "dialog"
        title_id = sheet.get_attribute("aria-labelledby")
        assert page.locator("#" + title_id).inner_text() == "Departures look"
        for axis, value in (("colour", "red"), ("background", "soft"), ("stripe", "solid")):
            assert page.is_checked('%s input[data-look-axis="%s"][value="%s"]' % (SHEET, axis, value))
        picture = page.locator(DEPARTURES + " .look-frame__picture").bounding_box()
        box = sheet.bounding_box()
        assert box["x"] >= picture["x"] + picture["width"], "expected the sheet beside the picture"

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
        page.click(ARRIVALS + " button.look-frame__open")
        page.locator(SHEET).wait_for(state="visible")
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


def test_sheet_traps_focus_closes_on_escape_and_returns_focus(new_context, make_app_server):
    """opened from the keyboard, the sheet takes focus, Tab and Shift+Tab stay inside it,
    Escape closes it and focus returns to the control that opened it; Reset restores the look
    that was there when it opened"""
    server = make_app_server(seed=_seed)
    context, page = _open_display(new_context, server.base_url(), VIEWPORT_DESKTOP)
    try:
        opener = DEPARTURES + " summary.look-edit__summary"
        page.focus(opener)
        page.keyboard.press("Enter")
        page.locator(SHEET).wait_for(state="visible")
        inside = "() => document.querySelector('%s').contains(document.activeElement)" % SHEET
        assert page.evaluate(inside)
        assert not page.locator(DEPARTURES + " details.look-edit").evaluate("d => d.open")
        for _ in range(12):
            page.keyboard.press("Tab")
            assert page.evaluate(inside), "Tab left the dialog"
        for _ in range(12):
            page.keyboard.press("Shift+Tab")
            assert page.evaluate(inside), "Shift+Tab left the dialog"
        page.click(_axis("colour", "green"))
        assert _checked(page, "theme") != "band_red_field"
        page.click(SHEET + " [data-look-reset]")
        assert _checked(page, "theme") == "band_red_field"
        page.keyboard.press("Escape")
        page.locator(SHEET).wait_for(state="hidden")
        assert page.evaluate("s => document.activeElement === document.querySelector(s)", opener)
    finally:
        context.close()


def test_save_bar_persists_the_new_look_and_same_as_departures(new_context, make_app_server):
    """a look chosen in the sheet is saved by the dirty bar's Save through the unchanged settings
    form, for departures and for an arrivals override, and turning "Same as departures" back on
    saves the clear signal"""
    server = make_app_server(seed=_seed)
    context, page = _open_display(new_context, server.base_url(), VIEWPORT_DESKTOP)
    try:
        page.click(DEPARTURES + " button.look-frame__open")
        page.click(_axis("colour", "green"))
        page.click(_axis("background", "paper"))
        page.click(_axis("stripe", "soft"))
        page.click(SHEET + " [data-look-done]")
        page.click(ARRIVALS + " button.look-frame__open")
        page.click(SHEET + " button.switch")
        page.click(_axis("colour", "black"))
        page.click(_axis("background", "soft"))
        page.click(SHEET + " [data-look-done]")
        _save_via_bar(page, timeout=30000)
        saved = device_config.load_device_config(server.state_dir)
        assert (saved["theme"], saved["theme_arriving"]) == ("band_green_light", "grey")
        assert urlsplit(page.url).path == layout.DISPLAY_ROUTE
        assert page.locator(DEPARTURES + " [data-look-sentence]").inner_text() == "Green, soft stripe"

        page.click(ARRIVALS + " button.look-frame__open")
        page.click(SHEET + " button.switch")
        assert page.locator(SHEET + " button.switch").get_attribute("aria-checked") == "true"
        page.click(SHEET + " [data-look-done]")
        _save_via_bar(page, timeout=30000)
        assert device_config.load_device_config(server.state_dir)["theme_arriving"] is None
    finally:
        context.close()


def test_add_a_special_look_is_a_dialog_that_posts_a_rule(new_context, make_app_server):
    """with scripts, "Add a special look" opens a modal dialog whose table gives way to the three
    choices; a suggestion fills the key, the choices pick the theme, the mini render follows,
    Escape closes it, and submitting adds the rule with that look"""
    server = make_app_server(seed=_seed)
    context, page = _open_display(new_context, server.base_url(), VIEWPORT_DESKTOP)
    try:
        page.click(".special-add__summary")
        panel = page.locator(".special-add__panel")
        panel.wait_for(state="visible")
        assert panel.get_attribute("role") == "dialog"
        assert not page.locator("[data-look-table-host]").is_visible()
        page.keyboard.press("Escape")
        assert not page.locator(".special-add").evaluate("d => d.open")
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
def test_on_phones_the_sheet_is_a_bottom_sheet_and_nothing_overflows(new_context, make_app_server, viewport):
    """on a phone the sheet is pinned to the bottom of the viewport at full width over a dimmed
    page, every choice is at least 44px tall, and neither the page nor the open sheet scrolls
    sideways"""
    server = make_app_server(seed=_seed)
    context, page = _open_display(new_context, server.base_url(), viewport)
    try:
        overflow = _assert_no_page_overflow(page, "display", viewport["width"])
        assert not overflow, overflow
        page.click(DEPARTURES + " button.look-frame__open")
        sheet = page.locator(SHEET)
        sheet.wait_for(state="visible")
        box = sheet.bounding_box()
        assert abs(box["x"]) < 1 and abs(box["width"] - viewport["width"]) < 1
        assert abs(box["y"] + box["height"] - viewport["height"]) < 1
        assert page.locator("[data-look-scrim]").is_visible()
        for selector in (SHEET + " .look-dot", SHEET + " .look-seg__option"):
            for handle in page.locator(selector).all():
                assert handle.bounding_box()["height"] >= 44
        assert page.evaluate("s => document.querySelector(s).scrollWidth <= document.querySelector(s).clientWidth", SHEET)
        overflow = _assert_no_page_overflow(page, "display with the sheet", viewport["width"])
        assert not overflow, overflow
        page.click("[data-look-scrim]", position={"x": 10, "y": 10})
        sheet.wait_for(state="hidden")
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_desktop_layout_has_no_overflow_and_44px_targets(new_context, make_app_server, lang):
    """at 1280px the two pictures sit side by side with the special looks beside them, the page
    does not scroll sideways, and every look opener is at least 44px in both directions"""
    server = make_app_server(seed=_seed)
    context, page = _open_display(new_context, server.base_url(), VIEWPORT_DESKTOP, lang=lang)
    try:
        overflow = _assert_no_page_overflow(page, "display", VIEWPORT_DESKTOP["width"])
        assert not overflow, overflow
        departures = page.locator(DEPARTURES).bounding_box()
        arrivals = page.locator(ARRIVALS).bounding_box()
        special = page.locator(".special-looks").bounding_box()
        assert departures["x"] + departures["width"] <= arrivals["x"] <= special["x"]
        for selector in ("button.look-frame__open", "summary.look-edit__summary", ".special-add__summary"):
            for handle in page.locator(selector).all():
                box = handle.bounding_box()
                assert box["height"] >= 44 and box["width"] >= 44, (selector, box)
    finally:
        context.close()
