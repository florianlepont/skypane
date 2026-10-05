#!/usr/bin/env python3
"""Real-browser checks of the resolve dialog on Health: a Resolve link opens the shared dialog in
place at 390 and 1280 px in both languages and both themes (the URL never changes, focus lands on
the name field, Escape hands focus back to the link); naming an airline continues inside the same
dialog (add artwork or skip) and ends on Health with the row gone; a refused name reopens the
dialog on Health with the field focused; and with scripts blocked the link still goes to the
Airlines page.
"""
import re

import pytest
from PIL import Image

import companion.test_status_pages_helpers as shp
from companion import auth
from companion.pages import airlines_page
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_PHONE, _assert_hit_target, _in_both_themes, _login, _no_js_page,
)

pytestmark = pytest.mark.browser

DIALOG = "#panel-lookup-dialog"
NAME_INPUT = "#" + airlines_page.MANUAL_NAME_INPUT_ID + "-dialog"
SAVE = DIALOG + ' .lightbox__actions button[type="submit"]'
CLOSE = DIALOG + " [data-view-panel-close]"
UPLOAD_ZONE = DIALOG + " .resolve-upload-zone"
VISIBLE_LINK = 'a[data-view-panel-resolve-prefix="%s"]:not([hidden]):visible'
ROW_LINKS = 'a[href="/airlines?resolve=%s"]:not([hidden])'
FOCUSED_ID = "() => document.activeElement.id"
SEEN = "2026-01-01T10:00:00+00:00"
REGISTRY = {
    "QXA": {"count": 5, "first_seen": SEEN, "last_seen": SEEN, "example_callsign": "QXA123"},
    "QXB": {"count": 2, "first_seen": SEEN, "last_seen": SEEN, "example_callsign": "QXB456"},
}
NEW_NAME = "Totally Novel Airline"


def _seed(state_dir):
    shp.seed_unresolved_prefixes(state_dir, REGISTRY)


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=_seed, fake_providers=True)


def _open_health(new_context, server, viewport, lang="en"):
    context = new_context(viewport=viewport)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/health")
    page.wait_for_load_state("load")
    page.locator(VISIBLE_LINK % "QXA").first.wait_for(state="visible")
    return context, page


SETTLED = """async () => {
  const dialog = document.querySelector('#panel-lookup-dialog');
  await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  await Promise.all(dialog.getAnimations({subtree: true}).map(a => a.finished));
}"""


def _click_resolve(page, prefix="QXA"):
    link = page.locator(VISIBLE_LINK % prefix).first
    link.wait_for(state="visible")
    link.evaluate("el => el.scrollIntoView({block: 'center'})")
    link.click()
    page.locator(DIALOG + "[open]").wait_for()
    # The dialog's entrance scales it for a moment; boxes are measured once it has stopped.
    page.evaluate(SETTLED)


def _wait_for_health(page, query):
    """Wait for the redirect back to Health with exactly `query` and for the page to load."""
    page.wait_for_url(re.compile(r"/health\?%s$" % re.escape(query)))
    page.wait_for_load_state("load")


def _png(path):
    art = Image.new("RGBA", (1200, 300), (0, 0, 0, 0))
    for x in range(200, 1000):
        for y in range(80, 220):
            art.putpixel((x, y), (200, 40, 40, 255))
    art.save(path)
    return str(path)


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_DESKTOP], ids=["390", "1280"])
def test_resolve_opens_the_dialog_in_place_with_usable_controls(new_context, server, viewport, lang):
    """clicking Resolve opens the modal without leaving /health, shows the prefix's context with
    the return target set, focuses the name field, keeps 16 px text and 44 px controls, never
    overflows (light and dark) and hands focus back to the link on Escape"""
    context, page = _open_health(new_context, server, viewport, lang)
    try:
        _click_resolve(page)
        assert page.url == server.base_url() + "/health"
        assert page.evaluate(FOCUSED_ID) == NAME_INPUT[1:]
        assert page.locator(DIALOG + " .resolve-context__prefix").inner_text() == "QXA"
        assert page.locator(DIALOG + " .resolve-context__count").inner_text() == "5"
        assert page.locator(DIALOG + " .resolve-context__callsign").inner_text() == "QXA123"
        assert page.locator(DIALOG + ' input[name="return"]').input_value() == "health"
        assert page.locator(DIALOG + ' input[name="prefix"]').input_value() == "QXA"
        english = "Resolve an unidentified flight" in page.locator(DIALOG + " .lightbox__heading").inner_text()
        assert english == (lang == "en")
        for theme in _in_both_themes(page):
            font_px = page.locator(NAME_INPUT).evaluate("e => parseFloat(getComputedStyle(e).fontSize)")
            assert font_px >= 16, (theme, font_px)
            for selector in (NAME_INPUT, SAVE, CLOSE):
                _assert_hit_target(page, selector, "health resolve (%s, %s)" % (lang, theme["theme"]))
            box = page.locator(DIALOG).bounding_box()
            assert box["x"] >= 0 and box["x"] + box["width"] <= viewport["width"], box
            assert page.locator(DIALOG).evaluate("e => e.scrollWidth - e.clientWidth") <= 0
            assert page.evaluate("() => document.documentElement.scrollWidth - innerWidth") <= 0
        page.keyboard.press("Escape")
        page.locator(DIALOG + "[open]").wait_for(state="detached")
        assert page.evaluate(
            "() => document.activeElement.getAttribute('data-view-panel-resolve-prefix')") == "QXA"
        assert page.url == server.base_url() + "/health"
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_DESKTOP], ids=["390", "1280"])
def test_naming_then_skipping_artwork_ends_on_health_with_the_row_gone(new_context, make_app_server, viewport):
    """name and save inside the dialog: Health reloads with the dialog on its artwork step (no
    leaving the page), and closing it leaves a table without that prefix"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_health(new_context, server, viewport)
    try:
        _click_resolve(page)
        page.fill(NAME_INPUT, NEW_NAME)
        page.locator(SAVE).click()
        _wait_for_health(page, "resolve=QXA&flash=manual_resolved")
        page.locator(DIALOG + "[open]").wait_for()
        page.locator(UPLOAD_ZONE).wait_for(state="visible")
        assert page.locator(DIALOG + " .lightbox__resolve-name").is_hidden()
        assert NEW_NAME in page.locator(DIALOG + " .lightbox__heading").inner_text()
        page.locator(CLOSE).click()
        page.locator(DIALOG + "[open]").wait_for(state="detached")
        assert page.url.split("?")[0] == server.base_url() + "/health"
        assert page.locator(ROW_LINKS % "QXA").count() == 0
        assert page.locator(ROW_LINKS % "QXB").count() >= 1
    finally:
        context.close()


def test_uploading_artwork_in_the_dialog_returns_to_health(new_context, make_app_server, tmp_path):
    """the artwork step posts from the dialog and the redirect lands on Health, not Airlines"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_health(new_context, server, VIEWPORT_DESKTOP)
    try:
        _click_resolve(page)
        page.fill(NAME_INPUT, NEW_NAME)
        page.locator(SAVE).click()
        _wait_for_health(page, "resolve=QXA&flash=manual_resolved")
        page.locator(UPLOAD_ZONE).wait_for(state="visible")
        page.set_input_files(UPLOAD_ZONE + ' input[type="file"]', _png(tmp_path / "art.png"))
        page.locator(UPLOAD_ZONE + ' button[type="submit"]').click()
        _wait_for_health(page, "flash=illustration_replaced")
        assert page.locator(ROW_LINKS % "QXA").count() == 0
        assert page.locator(DIALOG + "[open]").count() == 0
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_DESKTOP], ids=["390", "1280"])
def test_a_refused_name_reopens_the_dialog_on_health_with_the_field_focused(
        new_context, make_app_server, viewport):
    """a name the server cannot use comes back to Health with the dialog open on the same
    prefix, the error toast showing and the name field focused; nothing is saved"""
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open_health(new_context, server, viewport)
    try:
        _click_resolve(page)
        page.fill(NAME_INPUT, "!!!")
        page.locator(SAVE).click()
        _wait_for_health(page, "resolve=QXA&flash=manual_name_unusable")
        page.locator(DIALOG + "[open]").wait_for()
        assert page.locator(".toast").first.is_visible()
        assert page.evaluate(FOCUSED_ID) == NAME_INPUT[1:]
        assert page.locator(DIALOG + " .resolve-context__prefix").inner_text() == "QXA"
        assert page.locator(DIALOG + ' input[name="return"]').input_value() == "health"
        assert page.locator(ROW_LINKS % "QXA").count() >= 1
    finally:
        context.close()


def test_an_unknown_reopen_value_opens_nothing(new_context, server):
    """/health?resolve= with a value that is not an unresolved prefix leaves the page quiet"""
    context, page = _open_health(new_context, server, VIEWPORT_PHONE)
    try:
        page.goto(server.base_url() + "/health?resolve=ZZZ")
        page.wait_for_load_state("load")
        assert page.locator(DIALOG + "[open]").count() == 0
    finally:
        context.close()


def test_without_scripts_resolve_is_still_a_link_to_the_airlines_page(new_context, server):
    """scripts blocked: the dialog stays closed and the Resolve link goes to Airlines, where the
    in-page resolve section appears"""
    with _no_js_page(new_context, server.base_url(), "/health", viewport=VIEWPORT_DESKTOP,
                     reduced_motion="reduce") as page:
        page.wait_for_load_state("load")
        assert page.locator(DIALOG).is_hidden()
        link = page.locator(VISIBLE_LINK % "QXA").first
        link.wait_for(state="visible")
        link.click()
        page.wait_for_url(re.compile(r"/airlines\?resolve=QXA$"))
        page.wait_for_load_state("load")
        assert page.locator("[data-resolve-fallback]").is_visible()
        assert page.locator("[data-resolve-fallback] form.lightbox__resolve-name").is_visible()
