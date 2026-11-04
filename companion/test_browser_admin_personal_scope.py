"""Real-browser flow of an administrator opening someone else's frame from
Fleet: the detail header's actions menu, Open personal view, the Viewing-owner strip, the personal
pages keeping the frame's address, and Back to Fleet. At 360 and 1280 px, in
English and French, light and dark, with 44px hit areas and no sideways
overflow."""
import re

import pytest

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_hit_target,
    _assert_no_page_overflow, _login, _set_ui_theme)

pytestmark = pytest.mark.browser

MIN_TAP_PX = 44

_WORDS = {
    "en": {
        "personal": "Open personal view",
        "viewing": "Viewing %s’s frame" % fx.OWNER_EMAIL,
        "back": "Back to Fleet"},
    "fr": {
        "personal": "Ouvrir la vue personnelle",
        "viewing": "Cadre de %s en consultation" % fx.OWNER_EMAIL,
        "back": "Retour à la flotte"},
}

# True once the control owns its own centre: a cross-document view transition
# is still running until then and hit-testing lands on the root element.
_OWNS_ITS_CENTRE = (
    "(selector) => { const e = document.querySelector(selector);"
    " if (!e) return false; const r = e.getBoundingClientRect();"
    " return document.elementFromPoint(r.left + r.width / 2,"
    " r.top + r.height / 2) === e; }")


def _open_fleet(new_context, server, viewport, lang, scheme):
    seed = fx.seed_fleet(server.state_dir)
    context = new_context(viewport=viewport, color_scheme=scheme)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/fleet?frame=" + seed.owned_id)
    page.locator("main").wait_for(state="visible")
    _set_ui_theme(page, scheme)
    return context, page, seed


def _open_personal_view(page, server, seed, words, viewport):
    row = page.locator(".fleet-detail-head")
    row.locator(".row-menu__toggle").click()
    item = row.locator(".row-menu__item", has_text=words["personal"])
    page.wait_for_function(
        "(el) => el.getBoundingClientRect().height > 0", arg=item.element_handle())
    assert item.bounding_box()["height"] >= MIN_TAP_PX
    for other in row.locator(".row-menu__item").all():
        assert other.bounding_box()["height"] >= MIN_TAP_PX
    assert not _assert_no_page_overflow(page, "fleet-menu", viewport["width"])
    with page.expect_navigation():
        item.click()
    page.wait_for_url(server.base_url() + "/devices/%s/" % seed.owned_id)
    page.locator(".frame-notice").wait_for(state="visible")


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize(
    "viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
def test_fleet_to_a_foreign_frame_and_back(
        new_context, app_server_in_process, viewport, lang, scheme):
    server = app_server_in_process
    words = _WORDS[lang]
    where = "scope/%d/%s/%s" % (viewport["width"], lang, scheme)
    context, page, seed = _open_fleet(new_context, server, viewport, lang, scheme)
    try:
        _open_personal_view(page, server, seed, words, viewport)
        strip = page.locator(".frame-notice")
        assert strip.inner_text().startswith(words["viewing"]), where
        assert strip.bounding_box()["height"] >= MIN_TAP_PX
        assert strip.evaluate("e => getComputedStyle(e).fontSize") == "14px"
        assert not _assert_no_page_overflow(page, where, viewport["width"])
        page.wait_for_function(_OWNS_ITS_CENTRE, arg=".frame-notice a", timeout=10000)
        _assert_hit_target(page, ".frame-notice a", where)

        # The personal pages keep the frame being viewed.
        prefix = "/devices/%s" % seed.owned_id
        nav = page.locator("nav:visible a[href$='/flights']").first
        assert nav.get_attribute("href") == prefix + "/flights"
        with page.expect_navigation():
            nav.click()
        page.wait_for_url(server.base_url() + prefix + "/flights")
        page.locator(".frame-notice").wait_for(state="visible")

        # Back to Fleet.
        page.wait_for_function(_OWNS_ITS_CENTRE, arg=".frame-notice a", timeout=10000)
        with page.expect_navigation():
            page.locator(".frame-notice a", has_text=words["back"]).click()
        page.wait_for_url(server.base_url() + "/fleet")
        assert re.search(r"/fleet$", page.url)
    finally:
        context.close()


def test_the_strip_is_absent_on_a_console_page_of_the_same_frame(
        new_context, app_server_in_process):
    server = app_server_in_process
    context, page, seed = _open_fleet(
        new_context, server, VIEWPORT_DESKTOP, "en", "light")
    try:
        page.goto(server.base_url() + "/devices/%s/health" % seed.owned_id)
        page.locator("main").wait_for(state="visible")
        assert page.locator(".frame-notice").count() == 0
        page.goto(server.base_url() + "/devices/%s/flights" % seed.owned_id)
        page.locator(".frame-notice").wait_for(state="visible")
    finally:
        context.close()
