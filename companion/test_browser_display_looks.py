"""Real-browser checks of the Look view's picker (/display): the colour, background and band
choices sit in the page under the Departures/Arrivals picture, swap that picture live and disable
the combinations the frame has no theme for with their reason, the dirty bar's Save persists the
new look, "Same as departures" follows departures, and nothing overflows at 1280, 390 and 360 px.
On the Calendar view the same sheet is still a labelled dialog (a bottom sheet on phones) that
traps focus, closes on Escape and returns focus to its opener; on the Special looks view "New
special look" is a page whose choices post a real rule, and each rule has an Edit page."""
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
    elif route == layout.DISPLAY_SPECIAL_LOOK_NEW_ROUTE:
        page.locator(".form-page__card").wait_for(state="visible")
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


def test_combinations_without_a_theme_are_not_offered(new_context, make_app_server):
    """with a soft background the soft stripe is not offered (disabled and not displayed);
    yellow and a full background leave nothing to choose, so the whole stripe group goes away"""
    server = make_app_server(seed=_seed)
    context, page = _open_display(new_context, server.base_url(), VIEWPORT_DESKTOP)
    try:
        _show_tab(page, "arrivals")
        page.locator(SHEET + " button.switch").wait_for(state="visible")
        page.click(SHEET + " button.switch")
        assert page.locator(SHEET + " button.switch").get_attribute("aria-checked") == "false"

        def disabled():
            return page.evaluate(
                "s => [...document.querySelectorAll(s + ' input[data-look-axis=stripe]')]"
                ".filter(e => e.disabled).map(e => e.value)", SHEET)

        def shown():
            return page.evaluate(
                "s => [...document.querySelectorAll(s + ' input[data-look-axis=stripe]')]"
                ".filter(e => e.parentNode.getClientRects().length > 0).map(e => e.value)", SHEET)

        def group_shown():
            return page.evaluate(
                "s => document.querySelector(s + ' [data-look-why]').parentNode"
                ".getClientRects().length > 0", SHEET)

        assert disabled() == ["soft"] and shown() == ["none", "solid"] and group_shown()
        page.click(_axis("colour", "yellow"))
        assert disabled() == ["solid", "soft"] and shown() == [] and not group_shown()
        assert _checked(page, "theme_arriving") == "yellow_light"
        page.click(_axis("colour", "red"))
        page.click(_axis("background", "full"))
        assert disabled() == ["solid", "soft"] and shown() == [] and not group_shown()
        assert _checked(page, "theme_arriving") == "red"
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


def test_add_a_special_look_is_a_page_that_posts_a_rule(new_context, make_app_server):
    """with scripts, "New special look" opens a page (no dialog) whose table gives way to the
    three choices; a suggestion fills the key, the choices pick the theme, the picture follows,
    and Create look in the floating bar adds the rule with that look; Cancel returns to the list"""
    server = make_app_server(seed=_seed)
    context, page = _open_display(
        new_context, server.base_url(), VIEWPORT_DESKTOP, route=layout.DISPLAY_SPECIAL_LOOKS_ROUTE)
    try:
        with page.expect_navigation():
            page.click(".special-add__summary")
        assert urlsplit(page.url).path == layout.DISPLAY_SPECIAL_LOOK_NEW_ROUTE
        page.locator("[data-look-axes-host]").wait_for(state="visible")
        assert not page.locator("[data-look-table-host]").is_visible()
        assert page.locator("dialog[open]").count() == 0
        with page.expect_navigation():
            page.click(".form-bar a.form-bar__cancel")
        assert urlsplit(page.url).path == layout.DISPLAY_SPECIAL_LOOKS_ROUTE
        page.locator(".special-add__summary").wait_for(state="visible")
        with page.expect_navigation():
            page.click(".special-add__summary")
        page.locator("[data-look-axes-host]").wait_for(state="visible")
        page.click('label[for="rule-kind-prefix"]')
        page.click('.rule-suggestion-chip[data-kind="prefix"]')
        assert page.input_value("#rule-key") == "AFR"
        host = "[data-look-axes-host]"
        page.click('%s .look-dot:has(input[value="blue"])' % host)
        page.click('%s .look-seg__option:has(input[data-look-axis="background"][value="paper"])' % host)
        page.click('%s .look-seg__option:has(input[data-look-axis="stripe"][value="soft"])' % host)
        assert _checked(page, "rule_theme_id") == "band_blue_light"
        page.wait_for_function(
            "() => document.querySelector('.look-frame__image').getAttribute('src')"
            ".startsWith('/frame-preview/band_blue_light.png')")
        with page.expect_navigation():
            page.click('.form-bar button[type="submit"]')
        assert urlsplit(page.url).path == layout.DISPLAY_SPECIAL_LOOKS_ROUTE
        rows = colour_rules.rule_rows(colour_rules.load_colour_rules(server.state_dir))
        assert ("prefix", "AFR", "band_blue_light") in [row[:3] for row in rows]
    finally:
        context.close()


def test_edit_a_special_look_is_a_page_that_replaces_the_rule(new_context, make_app_server):
    """each row has an Edit link to a page that keeps the key, shows the rule's own look checked,
    and saving replaces that rule's look without adding another"""
    server = make_app_server(seed=_seed)
    assert colour_rules.add_rule(
        server.state_dir, "prefix", "TVF", "white") == colour_rules.ADD_OK_NEW
    context, page = _open_display(
        new_context, server.base_url(), VIEWPORT_DESKTOP, route=layout.DISPLAY_SPECIAL_LOOKS_ROUTE)
    try:
        with page.expect_navigation():
            page.click('li.rule-row a.special-row__edit[href$="rule_key=TVF"]')
        assert urlsplit(page.url).path == layout.DISPLAY_SPECIAL_LOOK_EDIT_ROUTE
        assert page.locator(".form-page__name").inner_text() == "Edit special look"
        assert page.input_value('input[name="rule_key"]') == "TVF"
        assert _checked(page, "rule_theme_id") == "white"
        page.locator("[data-look-axes-host]").wait_for(state="visible")
        page.click('[data-look-axes-host] .look-dot:has(input[value="red"])')
        with page.expect_navigation():
            page.click('.form-bar button[type="submit"]')
        rows = [row[:3] for row in colour_rules.rule_rows(
            colour_rules.load_colour_rules(server.state_dir))]
        tvf = [row for row in rows if row[:2] == ("prefix", "TVF")]
        assert len(tvf) == 1 and tvf[0][2] != "white"
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
                if handle.is_visible():  # an option with no theme is not offered at all
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
                    if handle.is_visible():  # an option with no theme is not offered at all
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
                ".personalisation-nav__link", SHEET + " .look-dot", SHEET + " .look-seg__option"):
            for handle in page.locator(selector).all():
                if not handle.is_visible():  # an option with no theme is not offered at all
                    continue
                box = handle.bounding_box()
                assert box["height"] >= 44 - 0.5 and box["width"] >= 44 - 0.5, (selector, box)
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED], ids=["390", "360"])
def test_the_new_special_look_page_fits_a_phone(new_context, make_app_server, viewport):
    """on a phone the New special look page is one column with its picture beside its caption, the
    Create look button is in a bar floating above the tab bar and on screen without scrolling, and
    nothing overflows"""
    server = make_app_server(seed=_seed)
    context, page = _open_display(
        new_context, server.base_url(), viewport, route=layout.DISPLAY_SPECIAL_LOOK_NEW_ROUTE)
    try:
        page.locator("[data-look-axes-host]").wait_for(state="visible")
        page.wait_for_function(
            "() => document.readyState === 'complete' && document.getAnimations().every("
            "a => a.playState !== 'running')", timeout=10000)
        preview = page.locator(".form-page__preview").bounding_box()
        card = page.locator(".form-page__card").bounding_box()
        assert preview["y"] + preview["height"] <= card["y"] + 0.5, (preview, card)
        picture = page.locator(".form-page__preview .look-frame__picture").bounding_box()
        caption = page.locator(".form-page__caption").bounding_box()
        assert picture["x"] + picture["width"] <= caption["x"] + 0.5, (picture, caption)
        bar = page.locator(".dirty-bar.form-bar").bounding_box()
        tab = page.locator(".tab-bar").bounding_box()
        assert bar["y"] >= 0 and bar["y"] + bar["height"] <= tab["y"] + 0.5, (bar, tab)
        add = page.locator('.form-bar button[type="submit"]').bounding_box()
        assert add["height"] >= 44 - 0.5
        assert not _assert_no_page_overflow(page, "new special look page", viewport["width"])
    finally:
        context.close()
