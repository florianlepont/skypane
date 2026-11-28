# SPDX-License-Identifier: AGPL-3.0-only
"""Real-browser check that on a phone an opened airline row never paints a square fill outside the
rounded corners of the airline card: for the first, a middle and the last airline, opened and
closed, in both themes, a pixel just outside each corner arc is the page background."""
import io

import animation_settle
import pytest
from PIL import Image

from companion import auth
from companion.test_browser_airline_helpers import seed_airline_editor
from companion.test_browser_ux_helpers import UI_THEMES_EXPLICIT, _login, _set_ui_theme

pytestmark = pytest.mark.browser

PHONE = {"width": 390, "height": 844}
TABLE = "table.airlines-table:has(#airline-air-france)"
_SETTLED = animation_settle.SETTLED
_OPEN_ROW = """(which) => {
  document.querySelectorAll('details.airlines-expand[open]').forEach((d) => { d.open = false; });
  const groups = [...document.querySelectorAll('%s tbody.airline-group')]
    .filter((g) => g.querySelector('details.airlines-expand'));
  const group = which === 'first' ? groups[0] : which === 'last' ? groups[groups.length - 1]
    : groups[Math.floor(groups.length / 2)];
  return group.id;
}""" % TABLE
_SET_OPEN = "([id, open]) => { document.querySelector('#' + id + ' details.airlines-expand').open = open; }"
_CORNERS = """() => {
  const r = document.querySelector('%s').getBoundingClientRect();
  return {left: r.left, right: r.right, top: r.top, bottom: r.bottom};
}""" % TABLE


def _rgb(page, x, y):
    png = page.screenshot(clip={"x": x, "y": y, "width": 1, "height": 1})
    return Image.open(io.BytesIO(png)).convert("RGB").getpixel((0, 0))


def _scroll_to(page, doc_y):
    page.evaluate("(y) => window.scrollTo(0, y)", doc_y)
    page.wait_for_timeout(150)


def _corner_pixels(page, hide_card):
    """The colour just outside the arc at the four corners (read at the card's own edges, with the
    corner scrolled into the middle of the screen)."""
    page.evaluate(
        "(hide) => { document.querySelector('%s').style.visibility = hide ? 'hidden' : ''; }" % TABLE,
        hide_card)
    out = []
    for edge in ("top", "bottom"):
        box = page.evaluate(_CORNERS)
        doc_y = box[edge] + page.evaluate("window.scrollY")
        _scroll_to(page, doc_y - 300)
        box = page.evaluate(_CORNERS)
        for side in ("left", "right"):
            x = box[side] + 2 if side == "left" else box[side] - 3
            y = box[edge] + 2 if edge == "top" else box[edge] - 3
            out.append(_rgb(page, x, y))
    return out


@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("which", ["first", "middle", "last"])
@pytest.mark.parametrize("opened", [True, False])
def test_an_airline_row_paints_nothing_outside_the_cards_rounded_corners(
        new_context, app_server_in_process, theme, which, opened):
    seed_airline_editor(app_server_in_process.state_dir)
    context = new_context(viewport=PHONE)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": "fr",
                          "url": app_server_in_process.base_url()}])
    page = context.new_page()
    try:
        _login(page, app_server_in_process.base_url())
        page.goto(app_server_in_process.base_url() + "/airlines/manage")
        page.locator("main").wait_for(state="visible")
        page.wait_for_function(_SETTLED, timeout=15000)
        _set_ui_theme(page, theme)
        page.wait_for_function(_SETTLED, timeout=15000)
        group = page.evaluate(_OPEN_ROW, which)
        page.evaluate(_SET_OPEN, [group, opened])
        page.wait_for_timeout(300)
        with_card = _corner_pixels(page, False)
        without_card = _corner_pixels(page, True)
        for shown, bare, corner in zip(with_card, without_card, ("tl", "tr", "bl", "br")):
            assert all(abs(a - b) <= 2 for a, b in zip(shown, bare)), (corner, shown, bare)
    finally:
        context.close()
