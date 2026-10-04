#!/usr/bin/env python3
"""Browser checks for the Flights phone card (the boarding-pass layout below 960 px): no
horizontal overflow at 390 and 360 px in both themes and both languages, the icon-only picture
action at the 44px floor and operable from the keyboard into the shared lightbox, the filter
hiding cards and updating the count, the tear-line notches following the page colour, the
cards working with scripts blocked, and the desktop table unchanged at 1280 px.
"""
import pytest

import companion.test_view_pages_helpers as vp
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE,
    _assert_hit_target, _assert_no_page_overflow, _in_both_themes, _login, _no_js_page,
)

pytestmark = pytest.mark.browser

LIGHTBOX = "#panel-lookup-dialog"
CARD = "li.history-card"
FIRST_ACTION = "li.history-card .history-card__picture"


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    """A read-only server seeded with every card variant and one archived render."""
    return module_app_server_factory(seed=vp.seed_flight_card_variety, fake_providers=True)


def _open_flights(new_context, server, viewport, lang="en"):
    context = new_context(viewport=viewport)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/flights")
    page.locator(CARD).first.wait_for(state="visible")
    return context, page


_CARD_PROBE = (
    "() => [...document.querySelectorAll('li.history-card')].map(li => {"
    "  const c = li.getBoundingClientRect();"
    "  const inside = [...li.querySelectorAll('*')].every(el => {"
    "    const r = el.getBoundingClientRect();"
    "    return r.width === 0 || (r.left >= c.left - 0.5 && r.right <= c.right + 0.5);"
    "  });"
    "  const route = li.querySelector('.history-card__route').getBoundingClientRect();"
    "  const codes = [...li.querySelectorAll('.history-card__code')]"
    "    .map(el => el.getBoundingClientRect().top);"
    "  const art = li.querySelector('.history-card__art').getBoundingClientRect();"
    "  const when = li.querySelector('.history-card__when').getBoundingClientRect();"
    "  return {callsign: li.querySelector('.history-card__callsign').textContent,"
    "          inside, codesOneRow: codes.every(t => Math.abs(t - codes[0]) < 1),"
    "          routeH: route.height,"
    "          stubOneRow: art.top < when.bottom && when.top < art.bottom};"
    "})")


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED], ids=["390", "360"])
def test_cards_fit_the_phone_in_both_themes(new_context, server, viewport, lang):
    """At 390 and 360 px, in English and French, light and dark: the page never scrolls
    sideways, every card keeps its content inside its own box, the route codes sit on one row,
    and the artwork shares one row with the time."""
    context, page = _open_flights(new_context, server, viewport, lang)
    try:
        for theme in _in_both_themes(page):
            where = "Flights cards (%s, %s)" % (lang, theme["theme"])
            failure = _assert_no_page_overflow(page, where, expected_width=viewport["width"])
            if failure:
                raise AssertionError(failure)
            for card in page.evaluate(_CARD_PROBE):
                if not (card["inside"] and card["codesOneRow"] and card["stubOneRow"]):
                    raise AssertionError("%s: card %r is broken: %r" % (where, card["callsign"], card))
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED], ids=["390", "360"])
def test_picture_action_is_a_44px_keyboard_operable_lightbox_trigger(new_context, server, viewport):
    """The card's icon action hit-tests at no less than 44px on both axes, takes a visible focus
    ring from the keyboard, opens the shared lightbox with its own picture on Enter, returns
    focus on Escape, and opens it again on a tap, without leaving the page."""
    context, page = _open_flights(new_context, server, viewport)
    try:
        _assert_hit_target(page, FIRST_ACTION, "Flights card picture action")
        action = page.locator(FIRST_ACTION).first
        expected_src = action.get_attribute("data-view-panel-src")
        page.evaluate("() => document.activeElement && document.activeElement.blur()")
        for _ in range(80):
            page.keyboard.press("Tab")
            if action.evaluate("el => el === document.activeElement"):
                break
        else:
            raise AssertionError("expected Tab to reach the card's picture action")
        outline = action.evaluate(
            "el => [getComputedStyle(el).outlineStyle, parseFloat(getComputedStyle(el).outlineWidth)]")
        if outline[0] == "none" or outline[1] < 1:
            raise AssertionError("expected a visible focus ring, got %r" % (outline,))
        page.keyboard.press("Enter")
        dialog = page.locator(LIGHTBOX)
        dialog.wait_for(state="visible")
        shown = dialog.locator("img.lightbox__image").get_attribute("src")
        if shown != expected_src:
            raise AssertionError("expected the lightbox to show %r, got %r" % (expected_src, shown))
        page.keyboard.press("Escape")
        if dialog.evaluate("el => el.open"):
            raise AssertionError("expected Escape to close the lightbox")
        if not action.evaluate("el => el === document.activeElement"):
            raise AssertionError("expected focus to return to the picture action")
        page.locator(FIRST_ACTION).nth(1).click()
        if not dialog.evaluate("el => el.open") or "/gallery/" in page.url:
            raise AssertionError("expected a tap to open the lightbox in place")
    finally:
        context.close()


def test_filter_hides_cards_and_updates_the_count(new_context, server):
    """Typing in the filter hides the cards that do not match and the live count reads the
    visible flights; Clear brings every card back."""
    context, page = _open_flights(new_context, server, VIEWPORT_PHONE)
    try:
        total = page.locator(CARD).count()
        page.fill("[data-filter-input]", "obs")
        visible = page.evaluate(
            "() => [...document.querySelectorAll('li.history-card')]"
            ".filter(li => li.offsetParent).map(li =>"
            " li.querySelector('.history-card__callsign').textContent)")
        if visible != ["OBS412"]:
            raise AssertionError("expected only OBS412 to stay visible, got %r" % (visible,))
        count = page.locator("[data-filter-count]").text_content()
        if count != "1 of %d shown" % total:
            raise AssertionError("expected the count to read 1 of %d, got %r" % (total, count))
        page.click("[data-filter-clear]")
        shown = page.evaluate(
            "() => [...document.querySelectorAll('li.history-card')].filter(li => li.offsetParent).length")
        if shown != total:
            raise AssertionError("expected Clear to show all %d cards, got %d" % (total, shown))
    finally:
        context.close()


def test_tear_line_notches_follow_the_page_colour(new_context, server):
    """The stub's two notches paint in the page canvas colour in both themes, so they read as
    cut-outs rather than discs."""
    context, page = _open_flights(new_context, server, VIEWPORT_PHONE)
    try:
        for theme in _in_both_themes(page):
            paint = page.evaluate(
                "() => { const stub = document.querySelector('.history-card__stub');"
                " return [getComputedStyle(stub, '::before').backgroundColor,"
                "         getComputedStyle(stub, '::after').backgroundColor,"
                "         getComputedStyle(document.body).backgroundColor]; }")
            if paint[0] != paint[2] or paint[1] != paint[2]:
                raise AssertionError(
                    "expected both notches in the canvas colour (%s), got %r" % (theme["theme"], paint))
    finally:
        context.close()


def test_cards_render_and_link_without_scripts(new_context, server):
    """With scripts blocked the cards are server-rendered as they are with scripts, and the
    picture action is a real link that serves the archived render."""
    with _no_js_page(new_context, server.base_url(), "/flights", viewport=VIEWPORT_PHONE) as page:
        cards = page.locator(CARD)
        cards.first.wait_for(state="visible")
        if cards.count() != len(vp.FLIGHT_CARD_FLIGHTS):
            raise AssertionError("expected one card per flight, got %d" % cards.count())
        href = page.locator(FIRST_ACTION).first.get_attribute("href")
        response = page.goto(server.base_url() + href)
        if response is None or response.status != 200:
            raise AssertionError("expected the card link to serve the archived render, got %r" % (response,))


def test_desktop_keeps_the_table_and_hides_the_cards(new_context, server):
    """At 1280 px the cards are hidden and the flights table is shown, its picture links still
    reading "View picture"."""
    context = new_context(viewport=VIEWPORT_DESKTOP)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/flights")
        table = page.locator("table.data-table--flights")
        table.wait_for(state="visible")
        if page.locator("ul.history-cards").is_visible():
            raise AssertionError("expected the phone cards hidden at 1280px")
        links = table.locator("a[data-view-panel-src]")
        if links.count() != len(vp.FLIGHT_CARD_FLIGHTS):
            raise AssertionError("expected one table link per flight, got %d" % links.count())
        texts = set(links.all_text_contents())
        if texts != {"View picture"}:
            raise AssertionError("expected every table link to read View picture, got %r" % (texts,))
    finally:
        context.close()
