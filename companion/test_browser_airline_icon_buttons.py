#!/usr/bin/env python3
"""Real-browser checks of the icon-only add and change picture buttons of the airline editor: a 44px
square named for the airline and the family, a tooltip on hover and keyboard focus, the same button in
the missing illustrations section, and a type card that is shorter on a phone than a text button made
it, in English and French, light and dark."""
from datetime import datetime, timedelta, timezone

import animation_settle
import pytest

from companion import auth
from companion.test_browser_airline_helpers import seed_airline_editor
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_PHONE, _assert_no_page_overflow, _login,
)
from server import history_db

pytestmark = pytest.mark.browser

_SETTLED = animation_settle.SETTLED
AIR_FRANCE = "#airline-air-france"
ADD = {"en": "Add artwork", "fr": "Ajouter une illustration"}
CHANGE = {"en": "Change artwork", "fr": "Changer l’illustration"}
ADD_ARIA = {
    "en": "Add an illustration for Air France, Airbus A330",
    "fr": "Ajouter une illustration pour Air France, Airbus A330",
}
CHANGE_ARIA = {
    "en": "Change the artwork of Air France, Airbus A320",
    "fr": "Changer l’illustration de Air France, Airbus A320",
}


def _seed(state_dir):
    seed_airline_editor(state_dir)
    now = datetime.now(timezone.utc)
    with history_db.open_db(state_dir) as conn:
        for index, code in enumerate(("A320", "A20N", "A333")):
            history_db.record_runway_event(
                conn, ts=(now - timedelta(hours=index + 1)).isoformat(), hex="ib%04d" % index,
                callsign="AFR9%02d" % index, aircraft_type=code, confirmed_state="departing",
                airline="Air France")


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=_seed, fake_providers=True)


def _open(new_context, server, viewport, lang="fr", theme="light"):
    context = new_context(viewport=viewport, color_scheme=theme)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/airlines/manage")
    page.wait_for_function(_SETTLED, timeout=15000)
    chevron = page.locator(AIR_FRANCE + " .airlines-expand > summary")
    chevron.scroll_into_view_if_needed()
    chevron.click()
    page.locator(AIR_FRANCE + " .airlines-subrow").first.wait_for(state="visible")
    page.wait_for_function(_SETTLED, timeout=15000)
    return context, page


def _row(page, family):
    rows = page.locator(AIR_FRANCE + " .airlines-subrow")
    for index in range(rows.count()):
        if rows.nth(index).locator(".airlines-type").inner_text() == family:
            return rows.nth(index)
    raise AssertionError("no row for %s" % family)


def _box(locator):
    return locator.evaluate(
        "el => { const r = el.getBoundingClientRect(); return {w: r.width, h: r.height}; }")


def _tip(locator):
    """The tooltip text drawn by the button's ::after, or "" when none shows."""
    return locator.evaluate(
        "el => { const c = getComputedStyle(el, '::after').content;"
        " return c === 'none' || c === 'normal' ? '' : c.slice(1, -1); }")


@pytest.mark.parametrize("theme", ("light", "dark"))
@pytest.mark.parametrize("lang", ("en", "fr"))
@pytest.mark.parametrize("viewport", (VIEWPORT_DESKTOP, VIEWPORT_PHONE), ids=("1280", "390"))
def test_the_add_and_change_buttons_are_44px_icons_named_for_airline_and_family(
        new_context, server, viewport, lang, theme):
    context, page = _open(new_context, server, viewport, lang, theme)
    try:
        add = _row(page, "Airbus A330").locator("button.airlines-act--icon")
        assert add.get_attribute("aria-label") == ADD_ARIA[lang]
        assert add.inner_text().strip() == ""
        change = _row(page, "Airbus A320").locator("label.airlines-act--icon")
        assert change.locator("span.visually-hidden").text_content() == CHANGE_ARIA[lang]
        for button in (add, change):
            box = _box(button)
            assert box["w"] >= 44 and box["h"] >= 44, box
            assert button.locator("svg").count() == 1
        assert not _assert_no_page_overflow(page, "editor", viewport["width"])
    finally:
        context.close()


@pytest.mark.parametrize("theme", ("light", "dark"))
@pytest.mark.parametrize("lang", ("en", "fr"))
def test_the_buttons_have_a_tooltip_on_hover_and_keyboard_focus_on_a_desktop(
        new_context, server, lang, theme):
    context, page = _open(new_context, server, VIEWPORT_DESKTOP, lang, theme)
    try:
        add = _row(page, "Airbus A330").locator("button.airlines-act--icon")
        change = _row(page, "Airbus A320").locator("label.airlines-act--icon")
        assert _tip(add) == "" and _tip(change) == ""
        add.hover()
        assert _tip(add) == ADD[lang]
        page.mouse.move(0, 0)
        assert _tip(add) == ""
        page.keyboard.press("Tab")
        change.locator("input[type=file]").focus()
        assert _tip(change) == CHANGE[lang]
        outline = change.evaluate("el => getComputedStyle(el).outlineStyle")
        assert outline == "solid"
    finally:
        context.close()


def test_a_type_card_without_a_picture_is_shorter_than_a_text_button_made_it(new_context, server):
    context, page = _open(new_context, server, VIEWPORT_PHONE)
    try:
        card = _row(page, "Airbus A330")
        height = _box(card)["h"]
        assert height <= 100, height
        thumb = card.locator(".airlines-thumb").first
        button = card.locator("button.airlines-act--icon")
        assert _box(button)["h"] >= 44
        # The button sits right of the thumbnail block, not on a row of its own.
        assert button.bounding_box()["x"] > thumb.bounding_box()["x"] + thumb.bounding_box()["width"]
    finally:
        context.close()


@pytest.mark.parametrize("lang", ("en", "fr"))
@pytest.mark.parametrize("viewport", (VIEWPORT_DESKTOP, VIEWPORT_PHONE), ids=("1280", "390"))
def test_the_missing_illustrations_rows_use_the_same_icon_button(
        new_context, server, viewport, lang):
    context, page = _open(new_context, server, viewport, lang)
    try:
        section = page.locator("#airlines-missing")
        section.scroll_into_view_if_needed()
        buttons = section.locator("button.airlines-act--icon")
        assert buttons.count() > 0
        first = buttons.first
        assert _box(first)["w"] >= 44 and _box(first)["h"] >= 44
        assert first.inner_text().strip() == ""
        label = first.get_attribute("aria-label")
        assert label.startswith(ADD_ARIA[lang].split(" Air France")[0]) and "," in label, label
        if viewport is VIEWPORT_DESKTOP:
            first.hover()
            assert _tip(first) == ADD[lang]
        assert "+ Illustration" not in section.inner_text()
    finally:
        context.close()
