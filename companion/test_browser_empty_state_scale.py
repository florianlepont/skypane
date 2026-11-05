#!/usr/bin/env python3
"""Browser checks for the compact empty state: the heading is in the Emphasis size and the UI
face (not the serif display stack, not 22 px), a page-level one keeps readable padding, and
nothing overflows, in both themes, both languages and at 360 and 1280 px."""
import pytest

from place_map_support import Hosts

from companion import auth
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT, VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED,
    _assert_no_page_overflow, _login, _set_ui_theme,
)

pytestmark = pytest.mark.browser

_MEASURE = """() => {
  const probe = document.createElement('p');
  probe.className = 'text-body';
  document.body.appendChild(probe);
  const body = getComputedStyle(probe);
  const ref = {size: body.fontSize, family: body.fontFamily};
  probe.className = 'text-heading';
  const heading = getComputedStyle(probe);
  const display = {size: heading.fontSize, family: heading.fontFamily};
  probe.remove();
  return {ref, display, blocks: [...document.querySelectorAll('main .empty-state')].map(el => {
    const h = getComputedStyle(el.querySelector('.empty-state__heading'));
    const cs = getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return {cls: el.className, size: h.fontSize, family: h.fontFamily,
            padLeft: parseFloat(cs.paddingLeft), left: rect.left, right: rect.right,
            width: document.documentElement.clientWidth};
  })};
}"""

# The Location page is not listed: with the map running it has no empty state (the map is its
# canvas); the plain page's "nothing matches" state is measured in test_empty_state_scale.py.
PAGES = ("/", "/audit", "/locations", "/update", "/flights", "/account")


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(fake_providers=True)


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize(
    "viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
def test_empty_state_headings_use_the_emphasis_scale(new_context, server, viewport, theme, lang):
    context = new_context(viewport=viewport)
    Hosts(context)
    try:
        context.add_cookies([{
            "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
        page = context.new_page()
        _login(page, server.base_url())
        for path in PAGES:
            page.goto(server.base_url() + path)
            _set_ui_theme(page, theme)
            measured = page.evaluate(_MEASURE)
            assert measured["blocks"], "%s shows no empty state" % path
            for block in measured["blocks"]:
                assert block["size"] == measured["ref"]["size"] != measured["display"]["size"], (
                    path, block)
                assert block["family"] == measured["ref"]["family"] != measured["display"]["family"], (
                    path, block)
                assert block["left"] >= 0 and block["right"] <= block["width"], (path, block)
            assert _assert_no_page_overflow(page, path, viewport["width"]) == ""
    finally:
        context.close()


def test_a_page_level_empty_state_does_not_touch_the_edge(new_context, server):
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/audit")
        block = page.evaluate(_MEASURE)["blocks"][0]
        assert block["padLeft"] >= 12, block
    finally:
        context.close()
