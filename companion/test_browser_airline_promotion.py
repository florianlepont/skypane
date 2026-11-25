"""Real-browser round trip of an airline with no artwork: the button of its "type to choose" row in the
missing-illustrations section opens the shared dialog, the uploaded picture goes through the real
route, and the airline then has a row of the main table (picture, name, prefix, views, menu) and no
longer a header of the section, whose title count drops by its row.
English and French, on a phone."""
import os

import animation_settle
import pytest

from companion import auth
from companion.test_browser_airline_helpers import seed_airline_editor
from companion.test_browser_ux_helpers import VIEWPORT_MIN_SUPPORTED, _login
from server.plane import illustrations

pytestmark = pytest.mark.browser

_PNG = os.path.join(illustrations.ILLUSTRATION_DIR, "vueling-airlines.png")
KNOWN = ".airlines-missing__airline"
BUTTON = KNOWN + ":has-text('Finnair') .airlines-missing__add"
_SETTLED = animation_settle.SETTLED


@pytest.mark.parametrize("lang,known_label", (("en", "Missing illustrations"), ("fr", "Illustrations manquantes")))
def test_artwork_uploaded_for_an_airline_without_artwork_gives_it_a_row_of_the_table(
        new_context, make_app_server, lang, known_label):
    server = make_app_server(seed=seed_airline_editor, fake_providers=True)
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    try:
        _login(page, server.base_url())
        page.goto(server.base_url() + "/airlines/manage")
        page.wait_for_function(_SETTLED, timeout=15000)
        assert page.locator(KNOWN + ":has-text('Finnair')").count() == 1
        assert page.locator("#airline-finnair").count() == 0
        before = page.locator(".airlines-missing__item").count()
        page.locator(BUTTON).first.click()
        upload = page.locator("#manual-illustration-input-dialog")
        upload.wait_for(state="attached")
        upload.set_input_files(_PNG)
        ask = page.locator("#airline_artwork_type")
        assert ask.is_visible()
        page.wait_for_function(_SETTLED, timeout=15000)
        assert ask.bounding_box()["height"] >= 44
        # No type chosen: Upload waits for it.
        assert page.locator("#panel-lookup-dialog .lightbox__upload").is_disabled()
        assert page.locator(KNOWN + ":has-text('Finnair')").count() == 1
        ask.select_option("A333")
        with page.expect_navigation():
            page.locator("#panel-lookup-dialog .lightbox__upload").click()
        page.wait_for_function(_SETTLED, timeout=15000)
        assert page.locator(KNOWN + ":has-text('Finnair')").count() == 0
        row = page.locator("#airline-finnair")
        assert row.count() == 1
        text = row.inner_text()
        assert "Finnair" in text and "FIN" in text
        assert "A333" in text
        # The airline has no picture of its own: its A333 type row shows it.
        row.locator(".airlines-expand > summary").click()
        row.locator(".airlines-subrow").first.wait_for(state="visible")
        assert row.locator(".airlines-subrow").first.locator("th").inner_text().startswith("A333")
        assert row.locator(".airlines-subrow img").count() >= 1
        assert row.locator(".row-menu__toggle").count() == 1
        title = page.locator("#airlines-missing-title").inner_text()
        assert title == "%s · %d" % (known_label, before - 1)
        assert page.locator(".airlines-missing__item").count() == before - 1
    finally:
        context.close()
