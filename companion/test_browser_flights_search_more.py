#!/usr/bin/env python3
"""Browser checks of the Flights title-row search and its Load more link: tapping the search
icon turns the title row into the field in place, so the direction control and the list keep the
same top at 360 and 390 px in English and French (the field covers exactly the 44px title row);
the field closes again once empty and blurred; with more flights stored than one page shows, a
Load more link under the list appends the next flights (and says how many are shown), the link
is a plain address that works with scripts blocked, and it is absent once everything is shown.
"""
import pytest

import companion.test_view_pages_helpers as vp
from companion import auth
from companion.pages import history_page
from companion.test_browser_ux_helpers import (
    VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE, _assert_no_page_overflow, _login, _no_js_page,
)

pytestmark = pytest.mark.browser

TOTAL = history_page.HISTORY_ROW_LIMIT + 20
CARD = "li.history-card"
MORE = "a.history-more__link"
FIELD = "[data-filter-input]"
_SETTLED = (
    "() => document.readyState === 'complete' && document.getAnimations().every("
    "(a) => a.playState !== 'running' || a.effect.getComputedTiming().iterations === Infinity)")
_TOPS = (
    "() => { const top = (s) => document.querySelector(s).getBoundingClientRect().top;"
    " return {chips: top('.filter-bar--chips'), card: top('li.history-card'),"
    "  header: document.querySelector('.page-header').getBoundingClientRect().height}; }")


def _seed_many(state_dir):
    vp.seed_runway_events(state_dir, [
        {"ts": "2026-09-03T%02d:%02d:00+00:00" % (hour, minute),
         "hex": "4c%04x" % (hour * 60 + minute), "callsign": "AFR%d" % (100 + hour * 60 + minute),
         "airline": "Air France", "origin": "ORY", "destination": "NCE",
         "confirmed_state": "departing"}
        for hour in range(10) for minute in range(0, 60, 5)][:TOTAL])


@pytest.fixture(scope="module")
def many(module_app_server_factory):
    return module_app_server_factory(seed=_seed_many, fake_providers=True)


@pytest.fixture(scope="module")
def few(module_app_server_factory):
    return module_app_server_factory(seed=vp.seed_flight_card_variety, fake_providers=True)


def _open(new_context, server, viewport, lang="en", route="/flights"):
    context = new_context(viewport=viewport)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + route)
    page.wait_for_function(_SETTLED, timeout=15000)
    page.locator(CARD).first.wait_for(state="visible")
    return context, page


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE], ids=["360", "390"])
def test_search_opens_in_the_title_row_without_moving_the_list(new_context, few, viewport, lang):
    context, page = _open(new_context, few, viewport, lang)
    try:
        before = page.evaluate(_TOPS)
        icon = page.locator(FIELD).bounding_box()
        assert icon["width"] >= 44 - 0.5 and icon["height"] >= 44 - 0.5, icon
        page.click(FIELD)
        page.wait_for_function(
            "() => document.querySelector('.filter-bar--title').getBoundingClientRect().width"
            " > 200", timeout=5000)
        assert page.evaluate(_TOPS) == before
        field = page.locator(".filter-bar--title").bounding_box()
        header = page.locator(".page-header").bounding_box()
        assert abs(field["y"] - header["y"]) <= 0.5 and abs(field["height"] - 44) <= 0.5, (
            field, header)
        page.keyboard.type("tvf")
        page.wait_for_function(
            "() => document.querySelector('[data-filter-input]').value === 'tvf'", timeout=5000)
        assert page.evaluate(_TOPS) == before
        page.click(".filter-bar--title [data-filter-clear]")
        page.wait_for_function(
            "() => document.querySelector('[data-filter-input]').value === ''", timeout=5000)
        page.locator(".page-title").click(force=True)
        page.evaluate("() => document.activeElement && document.activeElement.blur()")
        page.wait_for_function(
            "() => document.querySelector('.filter-bar--title').getBoundingClientRect().width"
            " <= 48", timeout=5000)
        assert page.evaluate(_TOPS) == before
        assert not _assert_no_page_overflow(page, "flights search", viewport["width"])
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_load_more_appends_the_next_flights(new_context, many, lang):
    context, page = _open(new_context, many, VIEWPORT_MIN_SUPPORTED, lang)
    try:
        assert page.locator(CARD).count() == history_page.HISTORY_ROW_LIMIT
        shown = page.locator(".history-more__count").inner_text()
        assert str(history_page.HISTORY_ROW_LIMIT) in shown, shown
        link = page.locator(MORE)
        assert link.bounding_box()["height"] >= 44 - 0.5
        assert link.inner_text() == ("Load more" if lang == "en" else "Charger plus")
        link.click()
        page.wait_for_function(
            "(n) => document.querySelectorAll('li.history-card').length === n",
            arg=TOTAL, timeout=10000)
        assert page.locator(MORE).count() == 0
        assert page.locator("#flights-new").count() == 1
    finally:
        context.close()


def test_load_more_works_without_scripts(new_context, many):
    with _no_js_page(new_context, many.base_url(), "/flights") as page:
        assert page.locator(CARD).count() == history_page.HISTORY_ROW_LIMIT
        page.click(MORE)
        page.wait_for_url("**/flights?more=1*")
        assert page.locator(CARD).count() == TOTAL
        assert page.locator(MORE).count() == 0


def test_the_link_is_absent_when_everything_fits_on_one_page(new_context, few):
    context, page = _open(new_context, few, VIEWPORT_MIN_SUPPORTED)
    try:
        assert page.locator(MORE).count() == 0
    finally:
        context.close()


def test_an_invalid_more_value_shows_the_first_page(new_context, many):
    context, page = _open(new_context, many, VIEWPORT_MIN_SUPPORTED, route="/flights?more=-3")
    try:
        assert page.locator(CARD).count() == history_page.HISTORY_ROW_LIMIT
    finally:
        context.close()
