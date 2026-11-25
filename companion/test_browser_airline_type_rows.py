#!/usr/bin/env python3
"""Real-browser checks that an airline has no picture of its own, only its aircraft types do: at 360
and 1280 px, in English and French, the Editor's airline row carries no picture and lists its type
rows (one per type, the star on the default type, no "All types" row), and the user's Airlines
page shows the picture of each airline's default type."""
import animation_settle
import pytest

from companion import auth
from companion.test_browser_airline_helpers import seed_airline_editor
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow, _login, _no_js_page,
)
from server.plane import airline_default_types, illustrations, manual_resolutions

pytestmark = pytest.mark.browser

VIEWPORTS = (("360", VIEWPORT_MIN_SUPPORTED), ("1280", VIEWPORT_DESKTOP))
_SETTLED = animation_settle.SETTLED
TRANSAVIA = "#airline-transavia-france"
STAR = {"en": "Default type", "fr": "Type par défaut"}


def _seed(state_dir):
    seed_airline_editor(state_dir)
    manual_resolutions.add_entry(state_dir, "ZEP", "Zephyr Air")
    assert airline_default_types.set_default_type(
        state_dir, "transavia-france", "A320") == airline_default_types.SET_OK


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=_seed, fake_providers=True)


def _open(new_context, server, viewport, lang, path):
    context = new_context(viewport=viewport)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + path)
    page.wait_for_function(_SETTLED, timeout=15000)
    return context, page


@pytest.mark.parametrize("lang", ("en", "fr"))
@pytest.mark.parametrize("name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_the_editor_lists_type_rows_only_with_the_star_on_the_default_type(
        new_context, server, name, viewport, lang):
    context, page = _open(new_context, server, viewport, lang, "/airlines/manage")
    try:
        row = page.locator(TRANSAVIA + " .airlines-row")
        row.wait_for(state="visible")
        assert row.locator(".airlines-thumb, .airlines-thumb__image, img").count() == 0
        assert page.locator("body").inner_text().count("All types") == 0
        assert page.locator("body").inner_text().count("Tous types") == 0
        chevron = TRANSAVIA + " .airlines-expand > summary"
        page.locator(chevron).scroll_into_view_if_needed()
        page.locator(chevron).click()
        subrows = page.locator(TRANSAVIA + " .airlines-subrow")
        subrows.first.wait_for(state="visible")
        page.wait_for_function(_SETTLED, timeout=15000)
        codes = [subrows.nth(i).locator(".airlines-type").inner_text() for i in range(subrows.count())]
        assert [code.split(" · ")[0] for code in codes] == ["A320", "B738", "A333"]
        starred = page.locator(TRANSAVIA + " .airlines-pill--star")
        assert starred.count() == 1 and starred.inner_text().strip() == STAR[lang]
        assert starred.locator("xpath=ancestor::tr").locator(".airlines-type").inner_text() == "A320"
        assert not _assert_no_page_overflow(page, "editor", viewport["width"])
        # Every airline with a picture has at least one type row to carry it.
        assert page.locator("#airline-air-france .airlines-expand").count() == 1
    finally:
        context.close()


@pytest.mark.parametrize("lang", ("en", "fr"))
def test_the_add_illustration_dialog_subtitle_is_body_text_not_code(
        new_context, server, lang):
    context, page = _open(new_context, server, VIEWPORT_DESKTOP, lang, "/airlines/manage")
    try:
        page.locator(".airlines-missing__airline", has_text="Lufthansa").locator(
            ".airlines-missing__add").click()
        subtitle = page.locator("#panel-lookup-dialog .lightbox__caption")
        subtitle.wait_for(state="visible")
        assert subtitle.inner_text().strip() == "Lufthansa"
        font = subtitle.evaluate("el => getComputedStyle(el).fontFamily")
        body = page.evaluate("() => getComputedStyle(document.body).fontFamily")
        assert "mono" not in font.lower() and font == body, font
        assert subtitle.evaluate("el => getComputedStyle(el).color") != page.evaluate(
            "() => getComputedStyle(document.body).color")
    finally:
        context.close()


@pytest.mark.parametrize("lang", ("en", "fr"))
@pytest.mark.parametrize("name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_the_airlines_page_shows_the_picture_of_the_default_type(
        new_context, server, name, viewport, lang):
    context, page = _open(new_context, server, viewport, lang, "/airlines")
    try:
        card = page.locator(".collection-card", has_text="Transavia France")
        card.first.wait_for(state="visible")
        src = card.first.locator("img").first.get_attribute("src")
        assert src.startswith("/illustration/transavia-france-a320.png"), src
        other = page.locator(".collection-card", has_text="Air France").first.locator("img").first
        assert other.get_attribute("src").startswith("/illustration/air-france.png")
        assert not _assert_no_page_overflow(page, "airlines", viewport["width"])
    finally:
        context.close()


def test_without_scripts_the_first_artwork_asks_for_a_type_and_makes_it_the_default(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    png = illustrations.ILLUSTRATION_DIR + "/vueling-airlines.png"
    with _no_js_page(
            new_context, server.base_url(), "/airlines/manage?resolve=ZEP",
            viewport=VIEWPORT_DESKTOP, reduced_motion="reduce") as page:
        form = page.locator("#manual-illustration-form")
        select = form.locator("select[name=default_type]")
        select.wait_for(state="visible")
        form.locator("input[type=file]").set_input_files(png)
        # No type chosen: the browser refuses to send the form.
        form.locator("button[type=submit]").click()
        assert "resolve=ZEP" in page.url
        select.select_option("A321")
        with page.expect_navigation():
            form.locator("button[type=submit]").click()
        page.wait_for_url("**/airlines/manage?flash=illustration_replaced")
    assert airline_default_types.load_default_types(server.state_dir)["zephyr-air"] == "A321"
