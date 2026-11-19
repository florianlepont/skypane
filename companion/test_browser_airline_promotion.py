"""Real-browser round trip of an airline known by name only: its Artwork button opens the shared
dialog, the uploaded picture goes through the real route, and the airline then has a row of the main
table (picture, name, prefix, views, menu) and no longer a row of the "Known by name only" block.
English and French, on a phone."""
import os

import pytest

from companion import auth
from companion.test_browser_airline_helpers import seed_airline_editor
from companion.test_browser_ux_helpers import VIEWPORT_MIN_SUPPORTED, _login
from server.plane import illustrations

pytestmark = pytest.mark.browser

_PNG = os.path.join(illustrations.ILLUSTRATION_DIR, "vueling-airlines.png")
KNOWN = "tbody.airline-group--known"
BUTTON = KNOWN + ":has-text('Finnair') a[data-modal-open], " + KNOWN + ":has-text('Finnair') button"
_SETTLED = (
    "() => document.readyState === 'complete'"
    " && document.getAnimations().every(a => a.effect && a.effect.getTiming().iterations !== Infinity"
    " ? a.playState !== 'running' : true)")


@pytest.mark.parametrize("lang,known_label", (("en", "Known by name only"), ("fr", "Connues par leur nom")))
def test_artwork_uploaded_for_a_known_by_name_airline_gives_it_a_row_of_the_table(
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
        page.locator(BUTTON).first.click()
        upload = page.locator("#manual-illustration-input-dialog")
        upload.wait_for(state="attached")
        upload.set_input_files(_PNG)
        with page.expect_navigation():
            page.locator("#manual-illustration-form-dialog button[type=submit]").click()
        page.wait_for_function(_SETTLED, timeout=15000)
        assert page.locator(KNOWN + ":has-text('Finnair')").count() == 0
        row = page.locator("#airline-finnair")
        assert row.count() == 1
        text = row.inner_text()
        assert "Finnair" in text and "FIN" in text
        assert row.locator("img").count() >= 1
        assert row.locator(".row-menu__toggle").count() == 1
        captions = page.locator("caption.airlines-label").all_inner_texts()
        assert any(c.startswith(known_label) and c.endswith("· 5") for c in captions)
    finally:
        context.close()
