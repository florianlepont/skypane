"""Real-browser checks of the page title on phones: the four pages with their own cell in the
bottom tab bar (Home, Display, Flights, Airlines) keep their <h1> in the document but hide it
visually, because the tab bar already names the page; the pages reached through "More"
(Health, Device, Update) keep it visible, and every page shows it on a wide window."""
import pytest

from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE, _assert_no_page_overflow,
    _login, seed_state_dir)

pytestmark = pytest.mark.browser

TABBED = ("/", "/display", "/flights", "/airlines")
MORE = ("/health", "/device", "/update")


def _title_state(page):
    return page.evaluate(
        """() => {
            const all = document.querySelectorAll('h1');
            const h1 = all[0];
            const box = h1.getBoundingClientRect();
            const style = getComputedStyle(h1);
            return {count: all.length, text: h1.textContent.trim(),
                    width: box.width, height: box.height, clip: style.clipPath};
        }""")


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP],
                         ids=["390", "360", "1280"])
def test_page_title_is_hidden_only_on_tabbed_pages_on_a_phone(
        new_context, make_app_server, viewport, scheme, lang):
    """at phone widths the h1 of Home/Display/Flights/Airlines is 1px, clipped and still the
    page's single non-empty h1, while Health/Device/Update show it at full size; at 1280 every
    page shows it; no page overflows sideways"""
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    context = new_context(viewport=viewport, color_scheme=scheme)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang,
                          "url": server.base_url()}])
    try:
        page = context.new_page()
        _login(page, server.base_url())
        phone = viewport["width"] < 960
        for route in TABBED + MORE:
            page.goto(server.base_url() + route)
            page.locator("main").wait_for(state="visible")
            state = _title_state(page)
            assert state["count"] == 1 and state["text"], (route, state)
            hidden = phone and route in TABBED
            if hidden:
                assert state["width"] <= 1 and state["height"] <= 1, (route, state)
                assert state["clip"] != "none", (route, state)
            else:
                assert state["width"] > 40 and state["height"] > 20, (route, state)
                assert state["clip"] == "none", (route, state)
            assert not _assert_no_page_overflow(
                page, "title/%s" % route, viewport["width"]), route
    finally:
        context.close()
