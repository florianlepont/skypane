#!/usr/bin/env python3
"""Browser checks of the place search's feedback: while the geocoder has not answered, the
suggestion list ends in a Searching row with a small spinner (shown as soon as the visitor types,
under the airport matches), which the answer replaces by the places, by "No place found" for an
empty answer or by a short error line; one request at a time, and one per burst of typing."""
import json

import pytest

from companion import auth
from companion.test_browser_ux_helpers import VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _login
from place_map_support import RESULTS, SEARCH_PATTERN, SETTLED, Hosts, seed

pytestmark = pytest.mark.browser

READY = "() => document.documentElement.classList.contains('map-ready')"
TILES = "() => document.querySelectorAll('#place-map .leaflet-tile-loaded').length >= 1"
STATUS = "#place-results [data-status]"
OPTIONS = "#place-results button[role='option']"


class Held:
    """The geocoder's requests, held until the test answers them."""

    def __init__(self, context):
        self.routes = []
        context.route(SEARCH_PATTERN, lambda route: self.routes.append(route))

    def answer(self, body=None, status=200):
        route = self.routes.pop(0)
        route.fulfill(
            status=status, content_type="application/json",
            headers={"access-control-allow-origin": "*"},
            body=json.dumps(RESULTS if body is None else body))


def _open(new_context, server, viewport=VIEWPORT_DESKTOP, lang="en"):
    context = new_context(viewport=viewport)
    Hosts(context)
    held = Held(context)
    context.add_cookies([
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/detection")
    page.wait_for_function(READY, timeout=15000)
    page.wait_for_function(TILES, timeout=15000)
    page.wait_for_function(SETTLED, timeout=10000)
    return context, page, held


@pytest.mark.parametrize("viewport", [VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED], ids=["1280", "360"])
def test_a_searching_row_shows_while_the_geocoder_has_not_answered_then_the_places_replace_it(
        new_context, make_app_server, viewport):
    server = make_app_server(seed=seed, fake_providers=True)
    context, page, held = _open(new_context, server, viewport)
    try:
        page.fill("#place-search", "Lyon")
        row = page.locator(STATUS)
        row.wait_for(state="visible", timeout=3000)
        assert row.get_attribute("data-status") == "searching"
        assert row.inner_text().strip() == "Searching…"
        assert row.locator(".place-loading__spinner").count() == 1
        assert row.bounding_box()["height"] >= 44
        # The airport matches stay above it and the row is the list's last item.
        assert page.evaluate(
            "() => document.querySelector('#place-results li:last-child').dataset.status"
            ) == "searching"
        page.wait_for_timeout(700)
        assert len(held.routes) == 1
        held.answer()
        page.locator(OPTIONS).first.wait_for(state="visible", timeout=5000)
        page.wait_for_function("() => !document.querySelector('#place-results [data-status]')")
        assert "Lyon" in page.inner_text("#place-results")
    finally:
        context.close()


def test_an_empty_answer_says_no_place_found_and_a_failure_says_so_in_one_short_line(
        new_context, make_app_server):
    server = make_app_server(seed=seed, fake_providers=True)
    context, page, held = _open(new_context, server)
    try:
        page.fill("#place-search", "Zzzzzzzz")
        page.locator(STATUS).wait_for(state="visible", timeout=3000)
        page.wait_for_timeout(700)
        held.answer(body=[])
        page.wait_for_function(
            "() => (document.querySelector('#place-results [data-status]') || {}).dataset"
            " && document.querySelector('#place-results [data-status]').dataset.status === 'none'")
        assert page.locator(STATUS).inner_text().strip() == "No place found"
        assert page.locator(STATUS + " .place-loading__spinner").count() == 0
        page.fill("#place-search", "Yyyyyyyy")
        page.wait_for_function(
            "() => (document.querySelector('#place-results [data-status]') || {}).dataset"
            " && document.querySelector('#place-results [data-status]').dataset.status"
            " === 'searching'")
        page.wait_for_timeout(2100)
        held.answer(body=[], status=500)
        page.wait_for_function(
            "() => (document.querySelector('#place-results [data-status]') || {}).dataset"
            " && document.querySelector('#place-results [data-status]').dataset.status"
            " === 'failed'")
        assert page.locator(STATUS).inner_text().strip() == "Search unavailable right now"
    finally:
        context.close()


def test_the_rows_are_french_on_the_french_page(new_context, make_app_server):
    server = make_app_server(seed=seed, fake_providers=True)
    context, page, held = _open(new_context, server, lang="fr")
    try:
        page.fill("#place-search", "Lyon")
        page.locator(STATUS).wait_for(state="visible", timeout=3000)
        assert page.locator(STATUS).inner_text().strip() == "Recherche en cours…"
        page.wait_for_timeout(700)
        held.answer(body=[])
        page.wait_for_function(
            "() => document.querySelector('#place-results [data-status]').dataset.status"
            " === 'none'")
        assert page.locator(STATUS).inner_text().strip() == "Aucun lieu trouvé"
    finally:
        context.close()


def test_a_burst_of_typing_sends_one_request_and_never_two_at_once(
        new_context, make_app_server):
    server = make_app_server(seed=seed, fake_providers=True)
    context, page, held = _open(new_context, server)
    try:
        for value in ("Ly", "Lyo", "Lyon", "Lyon "):
            page.fill("#place-search", value)
            page.wait_for_timeout(80)
        page.wait_for_timeout(1000)
        assert len(held.routes) == 1
        page.fill("#place-search", "Marseille")
        page.wait_for_timeout(2500)
        # The first request is still unanswered: the second waits for it.
        assert len(held.routes) == 1
        held.answer()
        page.wait_for_timeout(2200)
        assert len(held.routes) == 1
        held.answer()
    finally:
        context.close()
