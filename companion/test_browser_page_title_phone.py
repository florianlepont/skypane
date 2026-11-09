"""Real-browser checks of the page title and its spacing on phones: every page has exactly one <h1>
at every supported width (Home's is visually hidden: its visible title is the frame state headline),
and on a phone the title sits at most PHONE_TITLE_GAP_MAX below the
app bar, so the top of the page does not waste vertical space."""
import pytest

from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE, _assert_no_page_overflow,
    _login, seed_state_dir)

pytestmark = pytest.mark.browser

ROUTES = ("/", "/display", "/flights", "/airlines", "/health", "/device", "/update")
# Distance from the bottom of the app bar (or of the space strip under it) to the top of the title: 16px bar margin + 16px
# content padding.
PHONE_TITLE_GAP_MAX = 32


def _title_state(page):
    return page.evaluate(
        """() => {
            const all = document.querySelectorAll('h1');
            const h1 = all[0];
            const box = h1.getBoundingClientRect();
            const bar = document.querySelector('.site-header').getBoundingClientRect();
            const hidden = h1.classList.contains('visually-hidden');
            const shown = hidden ? document.querySelector('.home-state__title') : h1;
            const shownBox = shown.getBoundingClientRect();
            return {count: all.length, text: h1.textContent.trim(), hidden: hidden,
                    width: shownBox.width, height: shownBox.height,
                    clip: getComputedStyle(shown).clipPath,
                    gap: hidden ? 0 : box.top - bar.bottom};
        }""")


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP],
                         ids=["390", "360", "1280"])
def test_page_title_is_visible_on_every_page_and_close_to_the_app_bar(
        new_context, make_app_server, viewport, scheme, lang):
    """every page has its single non-empty h1 and shows its title at full size at 390, 360 and
    1280 (on Home it is the frame name in the hero); on a phone a visible h1 starts within
    PHONE_TITLE_GAP_MAX of the app bar; no page overflows sideways"""
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    context = new_context(viewport=viewport, color_scheme=scheme)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang,
                          "url": server.base_url()}])
    try:
        page = context.new_page()
        _login(page, server.base_url())
        phone = viewport["width"] < 960
        for route in ROUTES:
            page.goto(server.base_url() + route)
            page.locator("main").wait_for(state="visible")
            state = _title_state(page)
            assert state["count"] == 1 and state["text"], (route, state)
            assert state["width"] > 40 and state["height"] > 20, (route, state)
            assert state["clip"] == "none", (route, state)
            assert state["hidden"] is False, (route, state)
            # Home's title sits in the hero, below its notification, not under the app bar.
            if phone and route != "/":
                assert 0 <= state["gap"] <= PHONE_TITLE_GAP_MAX, (route, state)
            assert not _assert_no_page_overflow(
                page, "title/%s" % route, viewport["width"]), route
    finally:
        context.close()
