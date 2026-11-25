#!/usr/bin/env python3
"""The unidentified-prefix rows of the airline editor read `callsign · views · date time` with no
relative age ("il y a 83 j" / "83 d ago"), on a phone and a desktop, in English and French."""
import re

import animation_settle
import pytest

from companion import auth
from companion.test_browser_airline_helpers import seed_airline_editor
from companion.test_browser_ux_helpers import VIEWPORT_DESKTOP, VIEWPORT_PHONE, _login

pytestmark = pytest.mark.browser

_SETTLED = animation_settle.SETTLED
GAP_ROW = "tbody.airline-group--gap"
AGE = re.compile(r"il y a|\bago\b|\(\d+ ?(j|d|h|min)", re.I)
VIEWS = {"en": "5 views", "fr": "5 vues"}


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=seed_airline_editor, fake_providers=True)


@pytest.mark.parametrize("lang", ("en", "fr"))
@pytest.mark.parametrize("viewport", (VIEWPORT_PHONE, VIEWPORT_DESKTOP), ids=("390", "1280"))
def test_an_unidentified_row_shows_its_date_and_time_and_no_relative_age(
        new_context, server, viewport, lang):
    context = new_context(viewport=viewport)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    try:
        _login(page, server.base_url())
        page.goto(server.base_url() + "/airlines/manage")
        page.wait_for_function(_SETTLED, timeout=15000)
        row = page.locator(GAP_ROW, has_text="XYZ").first
        row.wait_for(state="visible")
        text = row.inner_text()
        assert "XYZ123" in text and VIEWS[lang] in text
        assert re.search(r"\d{1,2}:\d{2}", text) and not AGE.search(text), text
        assert row.locator("[data-relative]").count() == 0
    finally:
        context.close()
