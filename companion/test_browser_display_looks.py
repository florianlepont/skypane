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
    elif route == layout.DISPLAY_CALENDAR_LOOK_ROUTE:
        page.locator(SHEET + "[data-look-inline]").wait_for(state="visible")
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
        page.wait_for_function(
            "() => document.querySelector('%s img.look-frame__image').alt.endsWith('%s')" % (
                DEPARTURES, "Blue, stripe on soft"), timeout=10000)
        page.wait_for_function(
            "() => { const i = document.querySelector('%s img.look-frame__image');"
            " return i.complete && i.naturalWidth === 600; }" % DEPARTURES)
        page.locator("[data-dirty-bar]").wait_for(state="visible")
        # Arrivals follow departures until they get a look of their own.
        assert _picture_src(page, ARRIVALS).startswith("/frame-preview/band_blue_field.png?state=arriving")
    finally:
        context.close()


def _axis_state(page, axis):
    """(value, disabled) of every option of one axis, in document order."""
    return page.evaluate(
        "a => [...document.querySelectorAll('%s input[data-look-axis=' + a + ']')]"
        ".map(e => [e.value, e.disabled])" % SHEET, axis)


def _why(page, selector):
    return page.locator(SHEET + " " + selector).inner_text().strip()


def test_combinations_without_a_theme_stay_visible_greyed_with_their_reason(
        new_context, make_app_server):
    """a stripe that would be invisible (a soft stripe on a soft background, a solid stripe on a
    full one) stays in its row, greyed and disabled, with the reason written under the row; the
    row is never removed; the new yellow looks (black text in the stripe) are reachable"""
    server = make_app_server(seed=_seed)
    context, page = _open_display(new_context, server.base_url(), VIEWPORT_DESKTOP)
    try:
        _show_tab(page, "arrivals")
        page.locator(SHEET + " button.switch").wait_for(state="visible")
        page.click(SHEET + " button.switch")
        assert page.locator(SHEET + " button.switch").get_attribute("aria-checked") == "false"

        def disabled():
            return [value for value, off in _axis_state(page, "stripe") if off]

        def stripe_row_shown():
            return page.evaluate(
                "s => [...document.querySelectorAll(s + ' input[data-look-axis=stripe]')]"
                ".every(e => e.parentNode.getClientRects().length > 0 && e.parentNode.offsetWidth > 0)",
                SHEET)

        assert disabled() == ["soft"] and stripe_row_shown()
        assert "soft background is invisible" in _why(page, "[data-look-why]")
        page.click(_axis("colour", "yellow"))
        assert _checked(page, "theme_arriving") == "band_yellow_field"
        assert disabled() == ["soft"] and stripe_row_shown()
        page.click(_axis("background", "full"))
        assert _checked(page, "theme_arriving") == "yellow"
        assert disabled() == ["solid"] and stripe_row_shown()
        assert "full background a solid stripe is invisible" in _why(page, "[data-look-why]")
        page.click(_axis("stripe", "soft"))
        assert _checked(page, "theme_arriving") == "band_yellow_on_full"
        page.click(_axis("background", "paper"))
        assert _checked(page, "theme_arriving") == "band_yellow_light"
        assert disabled() == [] and _why(page, "[data-look-why]") == ""
    finally:
        context.close()


def test_the_colour_row_is_greyed_with_a_reason_on_plain_white_paper(new_context, make_app_server):
    """on a white background with no stripe the colour changes nothing: the colour row stays
    but is disabled with its reason; choosing a background or a stripe enables it again"""
    server = make_app_server(seed=_seed)
    context, page = _open_display(new_context, server.base_url(), VIEWPORT_DESKTOP)
    try:
        def colours_disabled():
            return [off for _value, off in _axis_state(page, "colour")]

        assert not any(colours_disabled()) and _why(page, "[data-look-colour-why]") == ""
        page.click(_axis("background", "paper"))
        page.click(_axis("stripe", "none"))
        assert _checked(page, "theme") == "white"
        assert all(colours_disabled())
        assert "colour changes nothing" in _why(page, "[data-look-colour-why]")
        assert page.locator(SHEET + " .look-dot").first.is_visible()
        page.click(_axis("stripe", "solid"))
        assert not any(colours_disabled()) and _why(page, "[data-look-colour-why]") == ""
        assert _checked(page, "theme") == "band_red"
    finally:
        context.close()


def test_calendar_look_page_picker_is_in_the_page_and_works_from_the_keyboard(
        new_context, make_app_server):
    """the calendar look is a page of its own: the picker sits in the page (no dialog, no
    scrim), "Same as departures" is a switch operated from the keyboard and, once off, the
    picker's choices check a calendar theme radio; Cancel leads back to the Calendar list"""
    server = make_app_server(seed=_seed)
    context, page = _open_display(
        new_context, server.base_url(), VIEWPORT_DESKTOP, route=layout.DISPLAY_CALENDAR_LOOK_ROUTE)
    try:
        assert page.locator(SHEET).get_attribute("role") is None
        assert page.locator("dialog[open]").count() == 0
        assert page.locator("[data-look-open]:visible").count() == 0
        before = _checked(page, "calendar_theme_id")
        assert before == ""
        page.focus(SHEET + " button.switch")
        page.keyboard.press("Enter")
        page.wait_for_function(
            "s => document.querySelector(s).getAttribute('aria-checked') === 'false'",
            arg=SHEET + " button.switch", timeout=5000)
        page.click(_axis("colour", "green"))
        page.wait_for_function(
            "() => { const r = [...document.querySelectorAll('input')].find("
            "e => e.name === 'calendar_theme_id' && e.checked); return !!r && r.value !== ''; }",
            timeout=5000)
        with page.expect_navigation():
            page.click(".dirty-bar a.dirty-bar__cancel")
        assert urlsplit(page.url).path == layout.DISPLAY_CALENDAR_ROUTE
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
        page.wait_for_function(
            "() => document.querySelector('%s img.look-frame__image').alt.endsWith('%s')" % (
                DEPARTURES, "Green, soft stripe"), timeout=10000)

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
    """"New special look" opens a page (no dialog) of large look cards with no separate
    picture; a suggestion fills the key, a card picks the theme (and is the preview), and Save in
    the floating bar adds the rule with that look; Cancel returns to the list"""
    server = make_app_server(seed=_seed)
    context, page = _open_display(
        new_context, server.base_url(), VIEWPORT_DESKTOP, route=layout.DISPLAY_SPECIAL_LOOKS_ROUTE)
    cards = "form#special-look-form label.look-pick__card"
    try:
        with page.expect_navigation():
            page.click(".special-add__summary")
        assert urlsplit(page.url).path == layout.DISPLAY_SPECIAL_LOOK_NEW_ROUTE
        page.locator(cards).first.wait_for(state="visible")
        assert page.locator(
            "[data-look-axes-host], .look-frame__image, .form-page__preview").count() == 0
        assert page.locator("dialog[open]").count() == 0
        with page.expect_navigation():
            page.click(".dirty-bar a.dirty-bar__cancel")
        assert urlsplit(page.url).path == layout.DISPLAY_SPECIAL_LOOKS_ROUTE
        page.locator(".special-add__summary").wait_for(state="visible")
        with page.expect_navigation():
            page.click(".special-add__summary")
        page.locator(cards).first.wait_for(state="visible")
        page.click('label[for="rule-kind-prefix"]')
        page.click('.rule-suggestion-chip[data-kind="prefix"]')
        assert page.input_value("#rule-key") == "AFR"
        page.click(cards + ':has(input[value="band_blue_light"])')
        assert _checked(page, "rule_theme_id") == "band_blue_light"
        with page.expect_navigation():
            page.click('.dirty-bar button[type="submit"]')
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
        assert page.locator(".dirty-bar__message").inner_text() == "Edit special look"
        assert page.input_value('input[name="rule_key"]') == "TVF"
        assert _checked(page, "rule_theme_id") == "white"
        assert page.locator(
            ".form-page__preview, .form-page__caption, [data-look-axes-host], .look-frame__image"
        ).count() == 0
        page.click('form#special-look-form label.look-pick__card:has(input[value="green_light"])')
        assert _checked(page, "rule_theme_id") == "green_light"
        with page.expect_navigation():
            page.click('.dirty-bar button[type="submit"]')
        rows = [row[:3] for row in colour_rules.rule_rows(
            colour_rules.load_colour_rules(server.state_dir))]
        tvf = [row for row in rows if row[:2] == ("prefix", "TVF")]
        assert len(tvf) == 1 and tvf[0][2] == "green_light"
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED], ids=["390", "360"])
def test_on_phones_the_calendar_look_page_has_no_sheet_and_nothing_overflows(
        new_context, make_app_server, viewport):
    """on a phone the calendar look page holds its picker in the page, every choice is at least
    44px tall, the save bar floats above the tab bar, and neither the page nor the picker scrolls
    sideways"""
    server = make_app_server(seed=_seed)
    context, page = _open_display(
        new_context, server.base_url(), viewport, route=layout.DISPLAY_CALENDAR_LOOK_ROUTE)
    try:
        overflow = _assert_no_page_overflow(page, "calendar look", viewport["width"])
        assert not overflow, overflow
        assert page.locator("[data-look-scrim]").is_hidden()
        page.click(SHEET + " button.switch")
        for selector in (SHEET + " .look-dot", SHEET + " .look-seg__option"):
            for handle in page.locator(selector).all():
                if handle.is_visible():  # an option with no theme is not offered at all
                    assert handle.bounding_box()["height"] >= 44
        assert page.evaluate(
            "s => document.querySelector(s).scrollWidth <= document.querySelector(s).clientWidth",
            SHEET)
        page.locator(".dirty-bar").wait_for(state="visible")
        bar = page.locator(".dirty-bar").bounding_box()
        assert bar["y"] + bar["height"] <= viewport["height"]
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED], ids=["390", "360"])
def test_on_phones_the_picker_sits_under_the_picture_and_nothing_overflows(
        new_context, make_app_server, viewport):
    """on a phone the Look view shows the picture centred with no caption, the picker as a card
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
            assert not page.locator('[data-look-panel="%s"] .look-frame__caption' % usage).count()
            centre = picture["x"] + picture["width"] / 2
            assert abs(centre - viewport["width"] / 2) <= 2, "expected the picture centred"
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
    """on a phone the New special look page is one column of large look cards with no separate
    picture, the Save button is in a bar floating above the tab bar and on screen without
    scrolling, every card is at least 44px tall, and nothing overflows"""
    server = make_app_server(seed=_seed)
    context, page = _open_display(
        new_context, server.base_url(), viewport, route=layout.DISPLAY_SPECIAL_LOOK_NEW_ROUTE)
    try:
        page.locator("form#special-look-form label.look-pick__card").first.wait_for(state="visible")
        page.wait_for_function(
            "() => document.readyState === 'complete' && document.getAnimations().every("
            "a => a.playState !== 'running')", timeout=10000)
        assert page.locator(".form-page__preview, .form-page__caption").count() == 0
        card = page.locator(".form-page__card").bounding_box()
        first = page.locator("form#special-look-form label.look-pick__card").first.bounding_box()
        assert first["x"] >= card["x"] - 0.5 and first["x"] + first["width"] <= card["x"] + card["width"] + 0.5
        assert first["height"] >= 44 - 0.5
        bar = page.locator(".dirty-bar").bounding_box()
        tab = page.locator(".tab-bar").bounding_box()
        assert bar["y"] >= 0 and bar["y"] + bar["height"] <= tab["y"] + 0.5, (bar, tab)
        add = page.locator('.dirty-bar button[type="submit"]').bounding_box()
        assert add["height"] >= 44 - 0.5
        assert not _assert_no_page_overflow(page, "new special look page", viewport["width"])
    finally:
        context.close()
