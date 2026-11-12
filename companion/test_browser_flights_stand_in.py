"""Real-browser checks of the Flights phone rows that have no archived render of their own:
the stand-in lead (the airline's illustration, else a plane icon) is a 44px non-interactive
box that never overflows the row at 360 px in both themes, its illustration really loads,
and none of it is a picture link."""
import pytest

import companion.test_view_pages_helpers as vp
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow, _in_both_themes, _login)

pytestmark = pytest.mark.browser

CARD = "li.history-card"


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    """Every card variant, no archived render at all."""
    return module_app_server_factory(
        seed=lambda d: vp.seed_flight_card_variety(d, with_gallery=False),
        fake_providers=True)


_PROBE = """() => [...document.querySelectorAll('li.history-card')].map(li => {
  const lead = li.querySelector('.history-card__thumb');
  const box = lead.getBoundingClientRect();
  const image = lead.querySelector('img');
  return {callsign: li.querySelector('.history-card__callsign').textContent,
          tag: lead.tagName, kind: lead.classList.contains('history-card__thumb--none')
              ? 'none' : 'illustration',
          width: box.width, height: box.height,
          loaded: image ? image.complete && image.naturalWidth > 0 : null,
          icon: !!lead.querySelector('svg'),
          controls: li.querySelectorAll('a, button').length};
})"""


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_stand_in_is_a_44px_non_interactive_lead_in_both_themes(new_context, server, lang):
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/flights")
    page.locator(CARD).first.wait_for(state="visible")
    page.wait_for_function(
        "() => [...document.querySelectorAll('li.history-card img')].every(i => i.complete)")
    for theme in _in_both_themes(page):
        rows = page.evaluate(_PROBE)
        assert rows
        assert {row["kind"] for row in rows} == {"none", "illustration"}, rows
        for row in rows:
            assert row["tag"] == "SPAN" and row["controls"] == 0, row
            assert row["width"] == 44 and row["height"] == 44, row
            if row["kind"] == "illustration":
                assert row["loaded"] is True, row
            else:
                assert row["icon"] is True, row
        assert not _assert_no_page_overflow(page, "Flights/%s" % theme, 360)
