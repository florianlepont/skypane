"""Real-browser check of tapping a flight picture that has not loaded yet: the dialog never opens
as an empty box, the thumbnail keeps its loading placeholder meanwhile, and the dialog opens with
the picture once it has arrived (or on a second tap if the network stalls)."""
import pytest

import companion.test_view_pages_helpers as vp
from companion import auth
from companion.test_browser_ux_helpers import VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _login

pytestmark = pytest.mark.browser

DIALOG = "#panel-lookup-dialog"
THUMB = ".history-card__thumb:visible, td [data-view-panel-src]:visible"
VIEWPORTS = (("360", VIEWPORT_MIN_SUPPORTED), ("1280", VIEWPORT_DESKTOP))
IMAGE_READY = (
    "s => { const i = document.querySelector(s + ' img.lightbox__image');"
    " return !!i && i.complete && i.naturalWidth > 0; }")


@pytest.fixture(scope="module")
def flights_server(module_app_server_factory):
    return module_app_server_factory(seed=vp.seed_flight_card_variety, fake_providers=True)


def _open_flights(new_context, server, viewport):
    context = new_context(viewport=viewport)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": "en", "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/flights")
    page.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
    page.locator(THUMB).first.wait_for(state="visible")
    return context, page


@pytest.mark.parametrize("label,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_tapping_a_picture_that_is_still_loading_opens_the_dialog_only_when_it_is_ready(
        new_context, flights_server, label, viewport):
    context, page = _open_flights(new_context, flights_server, viewport)
    try:
        trigger = page.locator(THUMB).first
        src = trigger.get_attribute("data-view-panel-src")
        held = []
        # A cache-busting query makes the large picture a fresh request the test can hold back.
        page.route("**/gallery/**", lambda route: held.append(route))
        trigger.evaluate(
            "(el, s) => { el.setAttribute('data-test-held', ''); el.setAttribute('data-view-panel-src', s + (s.indexOf('?') < 0 ? '?' : '&') + 'held=1'); }",
            src)
        trigger.click()
        page.wait_for_function(
            "() => !!document.querySelector('[data-test-held].is-loading')", timeout=5000)
        assert page.evaluate("s => document.querySelector(s).open", DIALOG) is False
        page.wait_for_timeout(300)
        assert page.evaluate("s => document.querySelector(s).open", DIALOG) is False
        assert held, "the large picture was never requested"
        for route in list(held):
            route.continue_()
        page.unroute("**/gallery/**")
        page.wait_for_function("s => document.querySelector(s).open", arg=DIALOG, timeout=10000)
        page.wait_for_function(IMAGE_READY, arg=DIALOG, timeout=10000)
        page.wait_for_function("() => !document.querySelector('[data-test-held].is-loading')")
    finally:
        context.close()


def test_a_second_tap_opens_the_dialog_when_the_picture_stalls(new_context, flights_server):
    context, page = _open_flights(new_context, flights_server, VIEWPORT_DESKTOP)
    try:
        trigger = page.locator(THUMB).first
        src = trigger.get_attribute("data-view-panel-src")
        page.route("**/gallery/**", lambda route: None)
        trigger.evaluate(
            "(el, s) => { el.setAttribute('data-test-held', ''); el.setAttribute('data-view-panel-src', s + (s.indexOf('?') < 0 ? '?' : '&') + 'stalled=1'); }",
            src)
        trigger.click()
        page.wait_for_function(
            "() => !!document.querySelector('[data-test-held].is-loading')", timeout=5000)
        trigger.click()
        page.wait_for_function("s => document.querySelector(s).open", arg=DIALOG, timeout=10000)
    finally:
        context.close()
