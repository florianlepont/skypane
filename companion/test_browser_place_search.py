#!/usr/bin/env python3
"""Browser checks for the place search of the Location and detection page: a request only on a
submitted query or once the typing pauses, one at a time with a lock afterwards, the exact request the search service
gets (parameters, Referer, no credentials), result handling that never executes markup, and the
failure sentence with the rest of the page still saving.

The search host is answered by `page.route` (test-support/place_map_support.py); nothing reaches
the network. The 1.5 second lock is driven with the browser clock so no test sleeps.
"""
import urllib.parse

import pytest

from companion import auth
from companion.test_browser_ux_helpers import VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _login
from place_map_support import (
    SETTLED as _SETTLED, Hosts, open_details, saved_place, seed as _seed)

pytestmark = pytest.mark.browser

SAVE = "button.dirty-bar__save"
READY = "() => document.documentElement.classList.contains('map-ready')"
TILES_LOADED = "() => document.querySelectorAll('#place-map .leaflet-tile-loaded').length >= 1"
RESULTS_SHOWN = "() => !document.getElementById('place-results').hidden"
BUTTON_ENABLED = "() => !document.querySelector('form.place-search button').disabled"
BUTTON_DISABLED = "() => document.querySelector('form.place-search button').disabled"
SUBMIT = "() => document.querySelector('form.place-search').requestSubmit()"
NO_PLACE = "No place found in France. Try another spelling, tap the map or type an airport code."
FAILED = "Search is not available right now. Tap the map or type an airport code."
# Headers a browser adds on its own to a cross-origin fetch; anything else is a custom header.
BROWSER_HEADERS = frozenset((
    "accept", "accept-encoding", "accept-language", "origin", "referer", "user-agent",
    "sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site", "sec-ch-ua", "sec-ch-ua-mobile",
    "sec-ch-ua-platform", "connection", "host", "priority", "cache-control", "pragma"))


def _open(new_context, server, viewport=VIEWPORT_DESKTOP, lang="en", **host_kwargs):
    context = new_context(viewport=viewport)
    hosts = Hosts(context, **host_kwargs)
    context.add_cookies([
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/detection")
    page.wait_for_function(READY, timeout=15000)
    page.wait_for_function(TILES_LOADED, timeout=15000)
    page.wait_for_function(
        "() => document.getAnimations().every((a) => a.playState !== 'running'"
        " || a.effect.getComputedTiming().iterations === Infinity)", timeout=10000)
    page.wait_for_function(_SETTLED, timeout=10000)
    return context, page, hosts


def _submit_query(page, query):
    page.fill("#place-search", query)
    page.press("#place-search", "Enter")


def _results_text(page):
    return page.inner_text("#place-results")


def _advance_clock_until_search_enabled(page, step_ms=500, attempts=20):
    """Moves the paused page clock forward until the search button is enabled.

    The lock starts when the search answer arrives, which is real network
    time. A single large clock jump made before the answer is in would run
    ahead of a lock timer that is only set afterwards, so the clock moves in
    steps with a short real wait between them.
    """
    for _ in range(attempts):
        page.clock.run_for(step_ms)
        if page.evaluate("() => !document.querySelector('form.place-search button').disabled"):
            return
        page.wait_for_timeout(50)
    raise AssertionError("the search button was not enabled after %d ms of page time"
                         % (step_ms * attempts))


def _wait_for_search_requests(page, hosts, count, timeout_ms=5000):
    """Waits until the route handler has recorded `count` search requests.

    The handler runs when Playwright dispatches the request event, which can
    be after the page has already disabled its button, so a count read right
    after a page-side wait may still be behind.
    """
    waited = 0
    while len(hosts.search_requests) < count and waited < timeout_ms:
        page.wait_for_timeout(25)
        waited += 25


def test_nothing_is_requested_on_load_or_before_typing_pauses_and_a_submit_sends_one(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, hosts = _open(new_context, server)
    try:
        if hosts.search_requests:
            raise AssertionError("the page searched on load: %r" % hosts.search_requests)
        page.locator("#place-search").press_sequentially("Lyon")
        page.press("#place-search", "Enter")
        page.wait_for_function(RESULTS_SHOWN, timeout=10000)
        if len(hosts.search_requests) != 1:
            raise AssertionError("expected one request, got %r" % hosts.search_requests)
        url, headers = hosts.search_requests[0]
        parts = urllib.parse.urlsplit(url)
        query = urllib.parse.parse_qs(parts.query)
        expected = {
            "format": ["jsonv2"], "q": ["Lyon"], "countrycodes": ["fr"], "limit": ["5"],
            "accept-language": ["en"]}
        if (parts.scheme, parts.netloc, parts.path) != (
                "https", "nominatim.openstreetmap.org", "/search") or query != expected:
            raise AssertionError("the request was %r" % url)
        if headers.get("referer") != server.base_url().rstrip("/") + "/":
            raise AssertionError("Referer is %r" % headers.get("referer"))
        if "cookie" in headers or "authorization" in headers:
            raise AssertionError("credentials were sent: %r" % sorted(headers))
        custom = sorted(set(headers) - BROWSER_HEADERS)
        if custom:
            raise AssertionError("custom headers were sent: %r" % custom)
    finally:
        context.close()


@pytest.mark.parametrize("typed,icao", [
    ("CDG", "LFPG"), ("  lfpg ", "LFPG"), ("ory", "LFPO"), ("Paris-Orly Airport", "LFPO")])
def test_an_airport_code_or_name_selects_that_airport_without_asking_the_search_service(
        new_context, make_app_server, typed, icao):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, hosts = _open(new_context, server)
    try:
        with page.expect_navigation():
            _submit_query(page, typed)
        if "airport=%s" % icao not in page.url:
            raise AssertionError("landed on %s" % page.url)
        page.wait_for_function(READY, timeout=15000)
        if not page.is_checked("#place-mode-runway"):
            raise AssertionError("Airport mode is not selected")
        if not page.locator("label.runway-card").count():
            raise AssertionError("the airport's runways are not listed")
        if hosts.search_requests:
            raise AssertionError("an airport code reached the search service: %r"
                                 % hosts.search_requests)
    finally:
        context.close()


def test_other_text_is_looked_up_as_an_address(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, hosts = _open(new_context, server)
    try:
        _submit_query(page, "12 rue de Rivoli")
        page.wait_for_function(RESULTS_SHOWN, timeout=10000)
        if len(hosts.search_requests) != 1 or "/detection" not in page.url:
            raise AssertionError("the address was not looked up once: %r" % hosts.search_requests)
        if "airport=" in page.url:
            raise AssertionError("an address selected an airport")
    finally:
        context.close()


def test_the_french_page_asks_for_french_names(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, hosts = _open(new_context, server, lang="fr")
    try:
        _submit_query(page, "Marseille")
        page.wait_for_function(RESULTS_SHOWN, timeout=10000)
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(hosts.search_requests[0][0]).query)
        if query["accept-language"] != ["fr"]:
            raise AssertionError("language parameter is %r" % query["accept-language"])
    finally:
        context.close()


def test_a_query_that_is_too_short_sends_nothing(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, hosts = _open(new_context, server)
    try:
        _submit_query(page, "Ly")
        page.wait_for_function(RESULTS_SHOWN, timeout=10000)
        if _results_text(page) != "Type at least 3 characters to search.":
            raise AssertionError("shows %r" % _results_text(page))
        # A following valid search is the first and only request.
        _submit_query(page, "Lyon")
        page.wait_for_function(
            "() => document.querySelector('#place-results .place-result')", timeout=10000)
        if len(hosts.search_requests) != 1:
            raise AssertionError("requests: %r" % hosts.search_requests)
    finally:
        context.close()


def test_the_lock_holds_for_a_second_and_a_half_and_repeats_come_from_memory(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, hosts = _open(new_context, server)
    try:
        page.clock.install(time=0)
        page.clock.pause_at(1000)
        page.fill("#place-search", "Lyon")
        # Two submits in one turn: the second meets the request in flight.
        page.evaluate("() => { const f = document.querySelector('form.place-search');"
                      " f.requestSubmit(); f.requestSubmit(); }")
        page.wait_for_function(RESULTS_SHOWN, timeout=10000)
        page.wait_for_function(BUTTON_DISABLED, timeout=5000)
        page.fill("#place-search", "Nice")
        page.evaluate(SUBMIT)
        page.clock.run_for(1400)
        page.evaluate(SUBMIT)
        if not page.evaluate("() => document.querySelector('form.place-search button').disabled"):
            raise AssertionError("the button is enabled inside the lock")
        if len(hosts.search_requests) != 1:
            raise AssertionError("a request left inside the lock: %r" % hosts.search_requests)
        page.clock.run_for(200)
        page.wait_for_function(BUTTON_ENABLED, timeout=5000)
        page.evaluate(SUBMIT)
        page.wait_for_function(
            "() => document.querySelector('form.place-search button').disabled", timeout=5000)
        _wait_for_search_requests(page, hosts, 2)
        if len(hosts.search_requests) != 2:
            raise AssertionError("the unlocked search did not run once: %r" % hosts.search_requests)
        _advance_clock_until_search_enabled(page)
        page.fill("#place-search", "  lyon ")
        page.evaluate(SUBMIT)
        page.wait_for_function(
            "() => document.querySelector('#place-results .place-result__name')", timeout=5000)
        if len(hosts.search_requests) != 2:
            raise AssertionError("a repeated query went out again: %r" % hosts.search_requests)
    finally:
        context.close()


def test_tapping_a_street_result_moves_the_pin_zooms_in_and_fills_the_label(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts = _open(new_context, server)
    try:
        _submit_query(page, "rivoli")
        page.wait_for_function(
            "() => document.querySelectorAll('#place-results .place-result').length === 2",
            timeout=10000)
        rows = page.locator("#place-results .place-result")
        first = rows.nth(0)
        if first.locator(".place-result__name").inner_text() != "Rue de Rivoli":
            raise AssertionError("name reads %r" % first.inner_text())
        rest = first.locator(".place-result__rest").inner_text()
        if rest != "Paris, Île-de-France":
            raise AssertionError("the muted line reads %r" % rest)
        box = first.bounding_box()
        if box["height"] < 43.9:
            raise AssertionError("a result row is %.1f px high" % box["height"])
        first.click()
        page.wait_for_function(
            "() => document.getElementById('place-lat').value === '48.8606'", timeout=10000)
        if page.input_value("#place-lon") != "2.3376":
            raise AssertionError("longitude is %r" % page.input_value("#place-lon"))
        if page.input_value("#place-label") != "Rue de Rivoli":
            raise AssertionError("label is %r" % page.input_value("#place-label"))
        if not page.is_hidden("#place-results"):
            raise AssertionError("the list stayed open")
        page.wait_for_function(
            "() => !!document.querySelector('#place-map .place-pin')", timeout=5000)
        page.wait_for_function(
            "() => Array.from(document.querySelectorAll('#place-map .leaflet-tile-loaded'))"
            ".some((t) => t.src.indexOf('/15/') >= 0)", timeout=15000)
    finally:
        context.close()


def test_a_city_result_zooms_to_city_level_and_keeps_a_typed_label(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts = _open(new_context, server)
    try:
        open_details(page)
        page.fill("#place-label", "My own name")
        _submit_query(page, "lyon")
        page.wait_for_function(
            "() => document.querySelectorAll('#place-results .place-result').length === 2",
            timeout=10000)
        page.locator("#place-results .place-result").nth(1).click()
        page.wait_for_function(
            "() => document.getElementById('place-lat').value === '45.7578'", timeout=10000)
        page.wait_for_function(
            "() => Array.from(document.querySelectorAll('#place-map .leaflet-tile-loaded'))"
            ".some((t) => t.src.indexOf('/12/') >= 0)", timeout=15000)
        if page.input_value("#place-label") != "My own name":
            raise AssertionError("a typed label was overwritten")
    finally:
        context.close()


def test_hostile_result_text_is_shown_as_text_and_never_executes(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    hostile = (
        {"name": "<img src=x onerror=\"window.__pwned=1\">",
         "display_name": "<img src=x onerror=\"window.__pwned=1\">, <script>window.__pwned=2</script>, France",
         "lat": "48.85", "lon": "2.35", "type": "city"},
        {"name": "Out of range", "display_name": "Out of range, France", "lat": "999", "lon": "2",
         "type": "city"},
        {"name": "javascript:alert(1)", "display_name": "x, y, France", "lat": "nan", "lon": "2"},
        "not an object",
    )
    context, page, _hosts = _open(new_context, server, results=hostile)
    try:
        _submit_query(page, "hostile")
        page.wait_for_function(RESULTS_SHOWN, timeout=10000)
        if page.locator("#place-results img, #place-results script").count():
            raise AssertionError("markup from the answer reached the DOM")
        if page.evaluate("() => window.__pwned") is not None:
            raise AssertionError("script from the answer ran")
        rows = page.locator("#place-results .place-result")
        if rows.count() != 1:
            raise AssertionError("expected only the one valid row, got %d" % rows.count())
        if "<img" not in rows.first.inner_text():
            raise AssertionError("the text is not shown literally: %r" % rows.first.inner_text())
    finally:
        context.close()


def test_no_result_shows_the_no_place_sentence(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts = _open(new_context, server, results=())
    try:
        _submit_query(page, "nowhere")
        page.wait_for_function(RESULTS_SHOWN, timeout=10000)
        if _results_text(page) != NO_PLACE:
            raise AssertionError("shows %r" % _results_text(page))
    finally:
        context.close()


@pytest.mark.parametrize("failure", ["abort", 429, 503], ids=["aborted", "429", "503"])
def test_a_failed_search_shows_the_next_step_and_the_page_still_saves(
        new_context, make_app_server, failure):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, hosts = _open(new_context, server, search=failure)
    try:
        _submit_query(page, "Lyon")
        page.wait_for_function(RESULTS_SHOWN, timeout=10000)
        if _results_text(page) != FAILED:
            raise AssertionError("shows %r" % _results_text(page))
        if len(hosts.search_requests) != 1:
            raise AssertionError("retried: %r" % hosts.search_requests)
        box = page.locator("#place-map").bounding_box()
        page.mouse.click(box["x"] + box["width"] * 0.5, box["y"] + box["height"] * 0.5)
        page.wait_for_function(
            "() => !!document.querySelector('#place-map .place-pin')", timeout=5000)
        page.click("label.place-mode:has(#place-mode-area)")
        open_details(page)
        page.fill("#place-label", "Saved after failure")
        with page.expect_navigation() as info:
            page.click(SAVE)
        if info.value.status != 200:
            raise AssertionError("save ended on HTTP %d" % info.value.status)
        place = saved_place(server)
        if place is None or place["name"] != "Saved after failure":
            raise AssertionError("nothing was saved: %r" % (place,))
    finally:
        context.close()


def test_the_search_works_on_a_phone_and_the_caption_names_the_service(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts = _open(new_context, server, viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        caption = page.inner_text("#place-search-help")
        if "Nominatim" not in caption or "sent" not in caption:
            raise AssertionError("the caption does not state where the text goes: %r" % caption)
        _submit_query(page, "Lyon")
        page.wait_for_function(RESULTS_SHOWN, timeout=10000)
        width = page.evaluate("() => document.documentElement.scrollWidth")
        if width > VIEWPORT_MIN_SUPPORTED["width"]:
            raise AssertionError("the page scrolls sideways at 360 px: %d" % width)
    finally:
        context.close()
